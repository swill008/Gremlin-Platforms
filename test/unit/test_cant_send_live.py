# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The can't-be-sent notice (D-05-CANT-SEND-LIVE, 05 S137): the output layer
sends signal.cantSendChanged once per burst, on the main thread, whenever
something that decides "can't be sent" changes (claims saved, output module
files added or removed, the vJoy driver's devices, OSC's settings, the
Logical Device, the profile). Open editors re-read their red ⚠ from it
without being reopened."""

from __future__ import annotations

import json
import pathlib
import sys
import threading
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from action_plugins.root import RootData
from gremlin import device_initialization, event_handler, osc_device_file, osc_output
from gremlin.logical_device import LogicalDevice
from gremlin.modules import output, registry, store
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.signal import signal
from gremlin.types import InputType
from test.unit._device_folders import ensure_dir, module_path

B = InputType.JoystickButton


def _settle(qapp: object) -> None:  # noqa: ANN401
    """Lets the notice's zero-time timer run (bounded)."""
    for _ in range(5):
        qapp.processEvents()


def _notified(obj: QtCore.QObject, prop: str) -> list[bool]:
    """Records the notify signal of a QML property (what QML re-reads on)."""
    meta = obj.metaObject()
    notify = meta.property(meta.indexOfProperty(prop)).notifySignal()
    name = bytes(notify.name().data()).decode()
    seen: list[bool] = []
    getattr(obj, name).connect(lambda *_: seen.append(True))
    return seen


@pytest.fixture
def world(
    qapp: object,  # noqa: ANN401
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[dict]:
    """A temp modules folder (store writes, History, registry), vJoy 1 in
    the driver with 64 buttons, no Xbox driver, OSC's file in the folder."""
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    registry._cache.clear()
    state: dict = {"vjoy": [1]}

    def devices() -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                vjoy_id=i,
                device_guid=f"vjoy-{i}",
                name=f"vJoy {i}",
                axis_map=[],
                button_count=64,
                hat_count=0,
            )
            for i in state["vjoy"]
        ]

    monkeypatch.setattr(device_initialization, "vjoy_devices", devices)
    monkeypatch.setattr(device_initialization, "output_vjoy_devices", devices)
    monkeypatch.setattr(output, "vjoy_layout", lambda vid: (0, 64, 0))
    monkeypatch.setattr(output, "vjoy_axis_ids", lambda vid: set())
    monkeypatch.setattr(output, "xbox_available", lambda: False)
    monkeypatch.setattr(output, "_vjoy_off", set())
    osc_file = module_path(folder, "OSC")
    ensure_dir(folder, "OSC")
    monkeypatch.setattr(osc_device_file, "path", lambda: osc_file)
    osc_file.write_text(
        json.dumps(
            {
                "server": {"output_enabled": True},
                "targets": [
                    {"id": "t1", "name": "Mixer", "host": "127.0.0.1", "port": 9000}
                ],
            }
        ),
        encoding="utf-8",
    )
    osc_output.invalidate()
    vjoy_file = module_path(folder, "vJoy 1")
    ensure_dir(folder, "vJoy 1")
    store.write_json(vjoy_file, _vjoy_doc(range(1, 9)), "test")
    _settle(qapp)
    state.update(folder=folder, vjoy_file=vjoy_file)
    yield state
    _settle(qapp)
    registry._cache.clear()
    osc_output.reset()
    output.refresh()
    _settle(qapp)


def _vjoy_doc(buttons: range | list[int]) -> dict:
    return {
        "device": "vJoy 1",
        "direction": "dest",
        "claim": {"axes": [], "buttons": list(buttons), "hats": [], "keys": []},
    }


def _model(action: Any) -> tuple[object, Any]:  # noqa: ANN401
    from gremlin.ui.profile import InputItemBindingModel

    profile = Profile()
    item = InputItem(profile.library)
    binding = InputItemBinding(item)
    binding.root_action = RootData(B)
    binding.behavior = B
    profile.library.add_action(binding.root_action)
    profile.library.add_action(action)
    binding.root_action.insert_action(action, "children")
    model = InputItemBindingModel(binding)
    am = next(m for m in model._action_models.values() if m.action_data is action)
    return model, am


def _picker(input_id: int) -> Any:  # noqa: ANN401
    from gremlin.ui.output_modules import OutputModuleDevices

    picker: Any = OutputModuleDevices()
    picker.validTypes = ["button"]
    picker.setInitialState(1, "button", input_id)
    return picker


class _Recorder:
    sent: list[bool] = []
    threads: list[bool] = []

    @staticmethod
    def record() -> None:
        _Recorder.sent.append(True)
        _Recorder.threads.append(threading.current_thread() is threading.main_thread())


@pytest.fixture
def recorder(qapp: object) -> Iterator[type[_Recorder]]:  # noqa: ANN401
    output.watch_cant_send()
    _settle(qapp)
    _Recorder.sent, _Recorder.threads = [], []
    signal.cantSendChanged.connect(_Recorder.record)
    yield _Recorder
    signal.cantSendChanged.disconnect(_Recorder.record)


# --- the editors follow each source -----------------------------------------


def test_claim_saved_without_the_control_flags_the_open_picker(
    qapp: object,
    world: dict,  # noqa: ANN401
) -> None:
    picker = _picker(5)
    assert not picker.currentUnclaimed
    seen = _notified(picker, "currentReason")
    store.update_path(
        world["vjoy_file"],
        lambda doc: doc["claim"].update(buttons=[1, 2, 3]),
        "test",
    )
    _settle(qapp)
    assert seen, "the open vJoy picker wasn't told the claim changed"
    assert picker.currentUnclaimed
    assert picker.currentReason.startswith("vJoy 1's Button 5 is not Found")
    assert picker.currentReason.endswith("has Buttons 1–3).")


def test_vjoy_gone_from_the_driver_flags_the_open_picker(
    qapp: object,
    world: dict,  # noqa: ANN401
) -> None:
    picker = _picker(5)
    assert not picker.currentUnclaimed
    seen = _notified(picker, "currentUnclaimed")
    world["vjoy"] = []  # turned off in the vJoy configuration tool
    event_handler.EventListener().device_change_event.emit()
    _settle(qapp)
    assert seen, "the open vJoy picker wasn't told the vJoy devices changed"
    assert picker.currentUnclaimed
    assert "is not Found" in picker.currentReason


def test_xbox_output_module_added_and_removed_updates_the_open_editor(
    qapp: object,
    world: dict,  # noqa: ANN401
) -> None:
    from action_plugins.map_to_xbox import MapToXboxData

    action = MapToXboxData(B)
    action.xbox_device_id = 2
    _keep, am = _model(action)
    # Pad 2 is above the pad count (pad 2's module makes it on, D-XBOX-PADS).
    assert am.cantSendText == "Xbox 360 2 is off in Xbox Setup (pad 1 on)."
    seen = _notified(am, "cantSendText")
    ensure_dir(world["folder"], "Xbox 360 2")
    pad = module_path(world["folder"], "Xbox 360 2")
    store.write_json(
        pad,
        {
            "device": "Xbox 360 2",
            "direction": "dest",
            "claim": {"axes": [], "buttons": [], "hats": [], "keys": []},
        },
        "test",
    )
    _settle(qapp)
    assert seen, "the open Map to Xbox editor wasn't told of the new module"
    assert am.cantSendText == "Xbox 360 2 is not Found."
    assert {"value": 2, "label": "Xbox 360 2"} in am.padChoices
    seen.clear()
    store.delete_path(pad, "test")
    _settle(qapp)
    assert seen, "the open Map to Xbox editor wasn't told the module went"
    assert am.cantSendText == "Xbox 360 2 is off in Xbox Setup (pad 1 on)."


def test_osc_output_turned_off_updates_the_open_editor(
    qapp: object,
    world: dict,  # noqa: ANN401
) -> None:
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    action.target = "t1"
    _keep, am = _model(action)
    assert am.cantSendText == ""
    seen = _notified(am, "cantSendText")
    server = dict(osc_device_file.read_server(), output_enabled=False)
    assert osc_device_file.write_server(server, "test")
    _settle(qapp)
    assert seen, "the open Send OSC editor wasn't told OSC output is Off"
    assert am.cantSendText == "OSC output is Off."


def test_logical_device_control_deleted_sends_the_notice(
    qapp: object,
    world: dict,
    recorder: Any,  # noqa: ANN401
) -> None:
    device = LogicalDevice()
    control = device.create(B)
    _settle(qapp)
    recorder.sent.clear()
    device.delete(control.identifier)
    # What the Logical page's model says after its change.
    signal.logicalDeviceModified.emit()
    _settle(qapp)
    assert recorder.sent == [True]


# --- the notice itself --------------------------------------------------------


def test_a_burst_sends_one_notice(qapp: object, recorder: Any) -> None:  # noqa: ANN401
    for _ in range(5):
        output.notify_cant_send()
    signal.configChanged.emit()
    signal.oscServerSettingsChanged.emit()
    signal.logicalDeviceReloaded.emit()
    event_handler.EventListener().device_change_event.emit()
    assert recorder.sent == []  # not yet: once, after the burst
    _settle(qapp)
    assert recorder.sent == [True]


def test_another_thread_s_notice_arrives_on_the_main_thread(
    qapp: object,
    recorder: Any,  # noqa: ANN401
) -> None:
    worker = threading.Thread(target=output.notify_cant_send)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive()
    _settle(qapp)
    assert recorder.sent == [True]
    assert recorder.threads == [True]


def test_the_notice_drops_the_claim_cache(
    qapp: object,
    world: dict,
    recorder: Any,  # noqa: ANN401
) -> None:
    assert output.vjoy_claim(1)["buttons"] == list(range(1, 9))
    # Written behind the store's back (the cache isn't refreshed by it).
    world["vjoy_file"].write_text(json.dumps(_vjoy_doc([1, 2])), encoding="utf-8")
    signal.configChanged.emit()
    _settle(qapp)
    assert recorder.sent == [True]
    assert output.vjoy_claim(1)["buttons"] == [1, 2]
