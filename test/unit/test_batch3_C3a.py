# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Batch 3, modules and Home (C3a): GL-203, 245-248, 250, 253, 254, 258,
266, 267 and the shown-name follow-up (GL-124)."""

from __future__ import annotations

import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import config, shared_state
from gremlin.common import SingletonMetaclass
from gremlin.types import InputType

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def cfg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> config.Configuration:
    """A settings file of its own (the program's is put back after)."""
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    monkeypatch.delitem(
        SingletonMetaclass._instances, config.Configuration, raising=False
    )
    return config.Configuration()


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.01)
    return check()


# --- GL-203: Options text --------------------------------------------------------


def test_show_devices_without_a_module_text_uses_the_glossary_word(
    cfg: config.Configuration,
) -> None:
    from gremlin.ui import module_model

    module_model._ensure_display_options()
    text = cfg.description("display", "status", "show-stubs")
    assert "stub" not in text.lower()
    assert "device without a module" in text


# --- GL-246: Driven by uses the registry rules -------------------------------------

_STICK = "{0000000A-0000-0000-0000-000000000000}"


def test_driven_by_reads_the_vjoy_number_by_the_one_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules.ids import guid_key
    from gremlin.ui import module_model

    # A stick wired to vJoy 1; the vJoy card is named "vJoy 1 (2)" (joining
    # every digit read it as vJoy 12).
    monkeypatch.setattr(
        module_model, "_profile_wire_maps", lambda: [(guid_key(_STICK), "vjoy", 1)]
    )
    stick = types.SimpleNamespace(
        direction="source", name="Stick", tab="physical", guid=_STICK, target=""
    )
    vjoy = types.SimpleNamespace(
        direction="dest", name="vJoy 1 (2)", tab="physical", guid="", target=""
    )
    module_model.apply_bound_targets([stick, vjoy])
    assert vjoy.target == "Stick"
    assert stick.target == "vJoy 1 (2)"


def test_driven_by_tells_a_real_xbox_pad_from_the_xbox_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules.ids import guid_key
    from gremlin.ui import module_model

    monkeypatch.setattr(
        module_model, "_profile_wire_maps", lambda: [(guid_key(_STICK), "xbox", 1)]
    )
    stick = types.SimpleNamespace(
        direction="source", name="Stick", tab="physical", guid=_STICK, target=""
    )
    # An output file named after a real pad is not Gremlin's Xbox output.
    other = types.SimpleNamespace(
        direction="dest", name="Xbox Wireless Controller", tab="", guid="", target=""
    )
    pad = types.SimpleNamespace(
        direction="dest", name="Xbox 360 Controller", tab="xbox", guid="", target=""
    )
    module_model.apply_bound_targets([stick, other, pad])
    assert pad.target == "Stick"
    assert other.target == ""


# --- GL-247: the Home last line trusts the input module ----------------------------


def test_home_last_line_shows_what_the_input_module_passed() -> None:
    from gremlin.ui import module_model

    row = types.SimpleNamespace(guid="{AAA}", direction="source", slug="stick")
    shown: list[tuple[str, int]] = []
    fake = types.SimpleNamespace(
        _rows=[row],
        # The card's cached claim is older than the save that claimed button 2.
        _source_claim=lambda _row: {"buttons": [1], "axes": [], "hats": []},
        _set_last=lambda _row, kind, hid, _claim: shown.append((kind, hid)),
    )
    event = types.SimpleNamespace(
        device_guid="{AAA}", event_type=InputType.JoystickButton, identifier=2
    )
    module_model.ModuleListModel._on_joy(fake, event)  # type: ignore[arg-type]
    assert shown == [("button", 2)]


# --- GL-248: dead Xbox claim code and registry.find --------------------------------


def test_module_setup_shows_no_claim_boxes_for_the_xbox_output() -> None:
    from gremlin.modules import registry
    from gremlin.ui.module_model import XBOX_GUID, DriverInputModel

    assert not hasattr(registry, "find")
    assert not hasattr(DriverInputModel, "_load_xbox_dest")
    model = DriverInputModel()
    try:
        model.loadDevice(XBOX_GUID, "Xbox 360 Controller")
        assert model.rowCount() == 0
    finally:
        model.deleteLater()


# --- GL-250: Home writes settings only after reading, and only on change -----------


def _fake_stick(name: str, number: int) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        name=name,
        device_guid=f"{{0000000{number}-0000-0000-0000-000000000000}}",
        vendor_id=number,
        product_id=number,
        button_count=4,
        axis_count=2,
        hat_count=0,
    )


def test_home_reload_writes_settings_after_the_cards_are_read(
    cfg: config.Configuration, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import device_initialization
    from gremlin.ui import module_model

    plugged = [_fake_stick("Throttle", 1)]
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: plugged)
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(module_model, "_show_stubs", lambda: False)
    monkeypatch.setattr(module_model, "apply_bound_targets", lambda _rows: None)
    monkeypatch.setattr(module_model.ModuleListModel, "_stacks", lambda _self: [])
    monkeypatch.setattr(module_model, "_module_damage", lambda *_a: False)
    monkeypatch.setattr(module_model, "_load_module_doc", lambda *_a: {})
    saved = {"throttle"}
    monkeypatch.setattr(
        module_model,
        "module_exists",
        lambda name, _guid="": module_model.store.card_key(name) in saved,
    )
    model = module_model.ModuleListModel()
    # Throttle was kept as a card without a module after Delete Device; it
    # has a module again.
    module_model._set_kept_stubs({"throttle"})

    writes: list[tuple[str, list[str]]] = []
    real_write = module_model._write_status

    def write(name: str, value: object) -> None:
        writes.append((name, [r.slug for r in model._rows]))
        real_write(name, value)

    monkeypatch.setattr(module_model, "_write_status", write)
    model._rows = []
    model._reload()
    # Every write came after the new cards were in place, not in the read.
    assert writes, "the kept card should be released"
    assert all("throttle" in rows for _name, rows in writes)
    assert module_model._kept_stubs() == set()

    writes.clear()
    model._reload()
    assert writes == []  # nothing changed: nothing written


# --- GL-245: test_stage1_modules::test_a_blocked_output_is_logged_once_from_two_threads
# (its strict xfail removed).


# --- GL-267: the vJoy keep-alive belongs to the output module ----------------------


class _FakeDevice:
    def __init__(self) -> None:
        self.last_active = -1e9  # idle for ages
        self.resets = 0

    def reset(self) -> None:
        self.resets += 1


def _fake_proxy(devices: dict[int, _FakeDevice]) -> type:
    class Proxy:
        vjoy_devices: dict[int, _FakeDevice] = {}

        def __getitem__(self, vid: int) -> _FakeDevice:
            device = devices.setdefault(vid, _FakeDevice())
            Proxy.vjoy_devices = {**Proxy.vjoy_devices, vid: device}
            return device

        @classmethod
        def reset(cls) -> None:
            cls.vjoy_devices = {}

    return Proxy


def _wait_with_events(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    """_wait_for, letting the main thread's timers run meanwhile."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return check()


@pytest.fixture
def held_vjoy(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[int, _FakeDevice]]:
    """The output module on a fake driver with a quick keep-alive."""
    from gremlin import run_scope
    from gremlin.modules import output

    devices: dict[int, _FakeDevice] = {}
    proxy = _fake_proxy(devices)
    monkeypatch.setattr(output, "_vjoy_proxy", lambda: proxy)
    monkeypatch.setattr(output, "_KEEP_ALIVE_S", 0.01)
    monkeypatch.setattr(output, "_keep_alive", {})
    run_scope._reset_for_tests()
    try:
        yield devices
    finally:
        output.reset_vjoy()
        run_scope.stop()
        run_scope._reset_for_tests()


def _keep_alive_threads(name: str) -> list[str]:
    import threading

    return [t.name for t in threading.enumerate() if t.name == name]


def test_the_output_module_keeps_a_held_vjoy_alive_and_stops_at_release(
    held_vjoy: dict[int, _FakeDevice],
) -> None:
    from gremlin import threads
    from gremlin.modules import output
    from vjoy import vjoy

    # The driver wrapper holds no timer of its own any more.
    assert not hasattr(vjoy.VJoy, "_arm_keep_alive")
    name = threads.PREFIX + "vJoy 7 keep-alive"
    output._open_vjoy(7)
    output._open_vjoy(7)  # still one keep-alive per device
    assert _wait_with_events(lambda: held_vjoy[7].resets >= 3)
    assert threads.running().count(name) == 1
    # A main-thread timer, not a thread of its own (a test, or a Run's
    # caller, never finds it left running as a thread).
    assert _keep_alive_threads(name) == []
    output.reset_vjoy()
    # Released: the last check ends and none is armed after it.
    assert name not in threads.running()
    count = held_vjoy[7].resets
    _wait_with_events(lambda: False, 0.05)
    assert held_vjoy[7].resets == count
    assert output._keep_alive == {}


def test_a_vjoy_opened_on_another_thread_is_kept_alive_from_the_main_thread(
    held_vjoy: dict[int, _FakeDevice],
) -> None:
    import threading

    from gremlin import threads
    from gremlin.modules import output

    name = threads.PREFIX + "vJoy 5 keep-alive"
    opener = threading.Thread(target=output._open_vjoy, args=(5,))
    opener.start()
    opener.join(2.0)
    assert _wait_with_events(lambda: held_vjoy[5].resets >= 2)
    assert _keep_alive_threads(name) == []
    assert threads.running().count(name) == 1


def test_stop_ends_the_keep_alive_of_the_run(
    held_vjoy: dict[int, _FakeDevice], monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import run_scope, threads
    from gremlin.modules import output

    # A Run timer: Stop cancels it (stage CANCEL), not only reset_vjoy.
    monkeypatch.setattr(output, "_KEEP_ALIVE_S", 0.2)
    run_scope.begin()
    output._open_vjoy(4)
    assert [t.name for t in run_scope.pending_timers()] == ["vJoy 4 keep-alive"]
    run_scope.stop()
    assert run_scope.pending_timers() == []
    assert threads.PREFIX + "vJoy 4 keep-alive" not in threads.running()
    _wait_with_events(lambda: False, 0.3)
    assert held_vjoy[4].resets == 0


def test_a_vjoy_written_lately_is_not_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import clock
    from gremlin.modules import output

    devices: dict[int, _FakeDevice] = {}
    proxy = _fake_proxy(devices)
    monkeypatch.setattr(output, "_vjoy_proxy", lambda: proxy)
    monkeypatch.setattr(output, "_keep_alive", {})
    device = proxy()[3]
    device.last_active = clock.monotonic()
    token = object()
    output._keep_alive[3] = (token, types.SimpleNamespace(cancel=lambda: None))
    try:
        output._keep_alive_check(3, token)
        assert device.resets == 0
    finally:
        output.reset_vjoy()


# --- GL-253: Profile Settings lists vJoy devices from the output module ------------


@pytest.fixture
def profile() -> Iterator[Any]:
    from gremlin.profile import Profile

    before = shared_state.current_profile
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = before


def test_profile_settings_lists_vjoy_from_the_output_module(
    profile: Any, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> None:
    from gremlin import device_initialization
    from gremlin.modules import output
    from gremlin.signal import signal
    from gremlin.ui import profile as profile_ui

    def not_here() -> list:
        raise AssertionError("the input side's device list was read")

    monkeypatch.setattr(device_initialization, "vjoy_devices", not_here)
    monkeypatch.setattr(output, "vjoy_axes", lambda: {2: [1, 2, 7], 1: [1]})
    profile.settings.vjoy_as_input[1] = True
    behavior = profile_ui.VJoyInputOrOutputModel()
    initial = profile_ui.OutputVJoyListModel()
    try:
        vid_role = QtCore.Qt.ItemDataRole.UserRole + 1
        assert [
            behavior.data(behavior.index(i, 0), vid_role)
            for i in range(behavior.rowCount())
        ] == [1, 2]
        # vJoy 1 is read as an input: no Initial Values for it.
        assert initial.rowCount() == 1
        values = initial.data(
            initial.index(0, 0), QtCore.Qt.ItemDataRole.UserRole + 2
        )
        assert values.rowCount() == 3
        label_role = QtCore.Qt.ItemDataRole.UserRole + 1
        assert values.data(values.index(2, 0), label_role)
        values.setData(values.index(2, 0), 0.5, QtCore.Qt.ItemDataRole.UserRole + 2)
        assert profile.settings.get_initial_vjoy_axis_value(2, 7) == 0.5
    finally:
        for model in (behavior, initial):
            signal.profileChanged.disconnect(model._reset)


# --- GL-254: one binding model per action sequence --------------------------------


def test_input_item_model_reuses_one_binding_model_per_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.signal import signal
    from gremlin.ui import profile as profile_ui

    made: list[Any] = []

    class FakeBindingModel(QtCore.QObject):
        def __init__(self, binding: Any, parent: Any = None) -> None:  # noqa: ANN401
            super().__init__(parent)
            self.binding = binding
            signal.inputItemChanged.connect(self._check_user_feedback)
            made.append(self)

        def _check_user_feedback(self, _index: int) -> None:
            pass

    monkeypatch.setattr(profile_ui, "InputItemBindingModel", FakeBindingModel)
    first = types.SimpleNamespace(root_action=object())
    second = types.SimpleNamespace(root_action=object())
    item = types.SimpleNamespace(action_sequences=[first, second])
    model = profile_ui.InputItemModel(item, 0)  # type: ignore[arg-type]
    try:
        a = model.data(model.index(0, 0))
        assert model.data(model.index(0, 0)) is a
        b = model.data(model.index(1, 0))
        assert b is not a and len(made) == 2
        # Its root action replaced: a new model, the old one stops listening.
        first.root_action = object()
        c = model.data(model.index(0, 0))
        assert c is not a and len(made) == 3
        # A sequence that went lets go of its model.
        item.action_sequences.remove(second)
        model.data(model.index(0, 0))
        first.root_action = object()
        model.data(model.index(0, 0))
        assert id(second) not in model._binding_models
    finally:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for fake in made:
                try:
                    signal.inputItemChanged.disconnect(fake._check_user_feedback)
                except (RuntimeError, TypeError):
                    pass
        model.deleteLater()


# --- GL-258 / GL-266: input names without import-time patches ---------------------


def test_input_lists_give_the_input_name_without_patches() -> None:
    import gremlin.action_label  # noqa: F401  (imported by the app at start)
    from gremlin.ui import device

    for cls in (device.Device, device.KeyboardManagerModel):
        assert cls.data.__module__ == "gremlin.ui.device"
    item = types.SimpleNamespace(action_name="Fire", action_sequences=[1, 2])
    assert device._description_from_item(item) == "Fire"
    assert device._description_from_item(None) == ""


def test_the_unused_logical_device_editing_model_is_gone() -> None:
    import gremlin.action_label as action_label
    from gremlin.ui import device

    assert not hasattr(device, "LogicalDeviceManagementModel")
    assert "LogicalDeviceManagementModel" not in vars(action_label)


# --- GL-124 follow-up: one shown name for a device --------------------------------


def test_an_input_label_uses_the_shown_device_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import uuid

    from gremlin.ui import device, device_names

    monkeypatch.setattr(device_names, "shown_name", lambda _guid: "My Stick")
    ident = device.InputIdentifier()
    try:
        ident.device_guid = uuid.UUID("00000001-0000-0000-0000-000000000000")
        ident.input_type = InputType.JoystickButton
        ident.input_id = 3
        assert ident.label == "My Stick - Button 3"
    finally:
        ident.deleteLater()


# --- GL-244 (C3b request): hardware-only listeners skip program-made events --------


@pytest.mark.parametrize("synthetic", [False, True])
def test_module_setup_ticks_only_on_hardware_presses(synthetic: bool) -> None:
    from gremlin.ui.module_model import DriverInputModel

    pressed: list[tuple[str, int]] = []
    fake = types.SimpleNamespace(
        _rows=[{"kind": "button", "hwId": 2}],
        _same_device=lambda _event: True,
        markPressed=lambda kind, hid: pressed.append((kind, hid)),
    )
    event = types.SimpleNamespace(
        event_type=InputType.JoystickButton,
        is_pressed=True,
        identifier=2,
        synthetic=synthetic,
    )
    DriverInputModel._on_joy(fake, event)  # type: ignore[arg-type]
    assert pressed == ([] if synthetic else [("button", 2)])


def test_calibration_ignores_program_made_axis_events() -> None:
    from gremlin.ui import device

    # Any look at the device would raise: the event must stop before it.
    fake = types.SimpleNamespace(_device_uuid="X", _device=object(), _state=[])
    event = types.SimpleNamespace(
        device_guid="X",
        event_type=InputType.JoystickAxis,
        identifier=1,
        raw_value=100,
        synthetic=True,
    )
    device.AxisCalibration._event_callback(fake, event)  # type: ignore[arg-type]


# --- C5 requests: GL-275 vJoy axis ids from the output module; GL-270 page size ---


def test_the_output_module_gives_a_vjoys_sparse_axis_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import output
    from vjoy import vjoy

    present = {1: 1, 2: 1, 6: 1}  # X, Y, RZ
    codes = list(vjoy.AxisCode)
    monkeypatch.setattr(
        vjoy.VJoyInterface,
        "GetVJDAxisExist",
        lambda _vid, value: present.get(codes.index(vjoy.AxisCode(value)) + 1, 0),
        raising=False,
    )
    assert output.vjoy_axis_ids(3) == {1, 2, 6}


def test_module_setup_save_uses_the_one_page_size() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "gremlin/ui/module_model.py"
    ).read_text(encoding="utf-8")
    assert "32000" not in source and "18000" not in source
