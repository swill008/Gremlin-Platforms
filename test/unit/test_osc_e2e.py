# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC end to end (D-09-OSC-FILE, D-09-OSC-INPUT, D-09-OSC-FAULTS): the
page model's Listen / Bulk capture / Import put inputs with their settings
into OSC's file and a profile bound to them runs through the real binding
path.

No network: the UDP listener is a stand-in and messages go straight into
the runtime's main-thread handler. Module files live in a temp folder."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore, QtQml, QtTest
from qt_wait import wait_until  # pyright: ignore[reportMissingImports]  (test/)

from gremlin import code_runner, history_modules, osc, osc_bulk, shared_state
from gremlin import osc_device_file as odf
from gremlin.event_handler import EventHandler, EventListener
from gremlin.mode_manager import Mode, ModeManager
from gremlin.modules import store
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
from gremlin.profile import InputItem, Profile
from gremlin.types import InputType
from gremlin.ui.osc_device_model import OscDeviceManagementModel

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


class FakeListener:
    """Stands in for the UDP listener: nothing is bound."""

    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback
        self.open = False

    def start(self) -> None:
        self.open = True

    def stop(self) -> None:
        self.open = False


@pytest.fixture
def env(
    qapp: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Path]:
    """Temp USERPROFILE and modules folder, stand-in listener, OSC's rows
    empty; everything put back after."""
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    rows = OscDevice().rows
    kept = rows.to_dict()
    rows.load_dict({"inputs": []})
    rows.mark_saved()
    runtime = OscRuntime()
    runtime.cancel_listen()
    runtime.stop()
    yield folder
    runtime.cancel_listen()
    runtime.stop()
    rows.load_dict(kept)
    rows.mark_saved()
    odf.current_uid_map = None


def _qml(model: OscDeviceManagementModel, body: str) -> Any:  # noqa: ANN401
    """Run a JS expression in real QML with `m` = the model."""
    engine = QtQml.QQmlEngine()
    engine.rootContext().setContextProperty("m", model)
    comp = QtQml.QQmlComponent(engine)
    comp.setData(
        f"import QtQuick\nQtObject {{ property var result: {body} }}".encode(),
        QtCore.QUrl(),
    )
    obj = comp.create()
    assert obj is not None, comp.errorString()
    value = obj.property("result")
    return value.toVariant() if hasattr(value, "toVariant") else value


def _by_label() -> dict[str, Any]:
    return {r.label: r for r in OscDevice().rows.rows()}


def _settings(row: Any) -> tuple:  # noqa: ANN401
    return (
        row.input_type, row.mode, row.cmd_mode, list(row.data), row.source,
        row.range_min, row.range_max, row.trigger, row.delay_ms,
    )


def _reload_from_file() -> dict[str, Any]:
    """Forget the rows in memory and read OSC's file again."""
    OscDevice().rows.load_dict({"inputs": []})
    OscDevice().rows.mark_saved()
    odf.load()
    return _by_label()


# -- (1) page model -> OSC's file -> reload -----------------------------------


def test_listen_and_bulk_capture_settings_reach_oscs_file(env: Path) -> None:
    model = OscDeviceManagementModel()
    runtime = OscRuntime()
    captured: list[tuple[str, str]] = []
    model.commandCaptured.connect(lambda a, p: captured.append((a, p)))

    # Listen (single, add at once): the Add window's settings go on the input.
    model.setCaptureSettings({
        "mode": "axis", "cmd_mode": "message", "source": 1,
        "range_min": 0.0, "range_max": 1.0,
    })
    model.listenForInput()
    assert runtime.is_listening()
    runtime._on_main("/fader/1", ("name", 0.25))
    assert not runtime.is_listening()
    assert runtime._listener is None  # no profile runs: port closed

    # Listen from the Add window: the message fills the window, which then
    # adds the input with its settings (data mode keeps the values).
    window = {"mode": "button", "cmd_mode": "data", "source": 0,
              "trigger": None, "delay_ms": 120}
    # Called from real QML, as OscAddDialog.qml does.
    _qml(model, 'm.listenForCommand({mode: "button", cmd_mode: "data", '
                'source: 0, trigger: null, delay_ms: 120})')
    assert runtime.is_listening()
    assert model.capture_settings()["cmd_mode"] == "data"
    runtime._on_main("/scene", (2,))
    assert captured == [("/scene", "2")]
    assert model.createConfiguredInput(dict(window, address="/scene", data=["2"]))

    # Bulk capture with settings: each new address gets them.
    bulk = {"mode": "change", "cmd_mode": "message", "source": 1,
            "trigger": None, "delay_ms": 60}
    osc_bulk.start_bulk(model, bulk)
    runtime._on_main("/enc/a", (0, 5))
    runtime._on_main("/enc/b", (0, 7))
    model.cancelListen()
    assert runtime._listener is None

    before = {label: _settings(r) for label, r in _by_label().items()}
    assert before == {
        "/fader/1": (AXIS, "axis", "message", [], 1, 0.0, 1.0, None, None),
        "/scene": (BUTTON, "button", "data", ["2"], 0, 0.0, 1.0, None, 120),
        "/enc/a": (BUTTON, "change", "message", [], 1, 0.0, 1.0, None, 60),
        "/enc/b": (BUTTON, "change", "message", [], 1, 0.0, 1.0, None, 60),
    }
    uids = {label: r.uid for label, r in _by_label().items()}

    # Save (the profile's Save writes OSC's file when its rows changed).
    assert OscDevice().rows.dirty
    shared_state.current_profile.to_xml(env.parent / "p.xml")
    assert not OscDevice().rows.dirty
    assert sorted(e["label"] for e in odf.read_inputs()) == sorted(before)

    after = _reload_from_file()
    assert {label: _settings(r) for label, r in after.items()} == before
    assert {label: r.uid for label, r in after.items()} == uids


def test_listen_reaches_only_the_model_that_started_it(env: Path) -> None:
    """09 S17/S19: Listen binds with the listening window's settings only.
    The OSC page and the OSC Monitor each have their own page model; a
    message captured for one must not also add an input through the other
    (it did: every model connected to OscRuntime.learned added one)."""
    page = OscDeviceManagementModel()
    monitor = OscDeviceManagementModel()
    monitor.setCaptureSettings({"mode": "axis", "cmd_mode": "data", "source": 1})
    captured: list[tuple[str, str]] = []
    other: list[tuple[str, str]] = []
    page.commandCaptured.connect(lambda a, p: captured.append((a, p)))
    monitor.commandCaptured.connect(lambda a, p: other.append((a, p)))
    runtime = OscRuntime()

    page.listenForCommand({"mode": "button", "cmd_mode": "data", "source": 0})
    runtime._on_main("/scene", (2,))
    assert captured == [("/scene", "2")]
    assert other == []
    assert _by_label() == {}  # the Add window binds it, nothing else

    page.listenForInput()
    runtime._on_main("/fader/1", (0.25,))
    assert [r.label for r in OscDevice().rows.rows()] == ["/fader/1"]

    osc_bulk.start_bulk(page, {"mode": "change", "cmd_mode": "message"})
    monitor.cancelListen()  # the other window closing doesn't stop it
    assert runtime.is_listening()
    runtime._on_main("/enc/a", (0, 5))
    page.cancelListen()
    assert not runtime.is_listening()
    assert sorted(r.label for r in OscDevice().rows.rows()) == ["/enc/a", "/fader/1"]
    assert other == []


# -- (2) a profile bound to those inputs runs ---------------------------------


class _Recorder:
    """Stands in for CodeRunner's CallbackObject: records what reached the
    binding (the real event lookup decides which one runs)."""

    seen: list[tuple] = []

    def __init__(self, binding: Any) -> None:  # noqa: ANN401
        self.item = binding.input_item

    def __call__(self, event: Any) -> None:  # noqa: ANN401
        if event.event_type == AXIS:
            _Recorder.seen.append((self.item.osc_uid, round(event.value, 4)))
        else:
            _Recorder.seen.append((self.item.osc_uid, event.is_pressed))


def _bound_profile(path: Path, uids: list[str]) -> Profile:
    """A profile with one binding on each OSC input (by uid), saved and
    opened again from its file."""
    made = Profile()
    # The profile's own mode, never whatever mode an earlier test left.
    mode = made.modes.first_mode
    items = []
    for uid in uids:
        row = OscDevice().rows.by_uid(uid)
        item = InputItem(made.library)
        item.device_id = OSC_DEVICE_UUID
        item.input_type = row.input_type
        item.input_id = row.input_id
        item.osc_uid = uid
        item.mode = mode
        item.add_item_binding()
        items.append(item)
    made.inputs[OSC_DEVICE_UUID] = items
    made.to_xml(path)
    opened = Profile()
    opened.from_xml(path)
    return opened


def test_run_bound_profile_with_per_input_settings(
    env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    odf.write_server({"autorelease_delay_ms": 400, "autorelease_no_arg": True})
    model = OscDeviceManagementModel()
    add = model.createConfiguredInput
    assert add({"address": "/btn", "mode": "button"})
    assert add({"address": "/trig", "mode": "button", "trigger": True,
                "delay_ms": 40})
    assert add({"address": "/axis", "mode": "axis", "source": 1,
                "range_min": 0.0, "range_max": 1.0})
    assert add({"address": "/chg", "mode": "change", "delay_ms": 30})
    assert add({"address": "/scene", "mode": "button", "cmd_mode": "data",
                "data": ["1"], "delay_ms": 30})
    assert add({"address": "/p2", "mode": "button", "source": 1})
    rows = _by_label()
    uid = {label: r.uid for label, r in rows.items()}
    profile = _bound_profile(env.parent / "run.xml", list(uid.values()))
    assert {i.osc_uid for i in profile.inputs[OSC_DEVICE_UUID]} == set(uid.values())
    monkeypatch.setattr(shared_state, "current_profile", profile)
    # The running mode is the profile's (an earlier test may leave the
    # mode manager on "Invalid" or another profile's mode).
    monkeypatch.setattr(
        ModeManager(), "_current", Mode(profile.modes.first_mode, None)
    )

    # Run: CodeRunner's own binding setup on a real EventHandler fed by the
    # real listener signal.
    monkeypatch.setattr(code_runner, "CallbackObject", _Recorder)
    _Recorder.seen = []
    runner = code_runner.CodeRunner.__new__(code_runner.CodeRunner)
    runner._profile = profile
    runner.event_handler = EventHandler()
    assert runner._setup_profile() == len(uid)
    EventListener().joystick_event.connect(runner.event_handler.process_event)
    runtime = OscRuntime()
    try:
        runtime.start()
        assert runtime._listener is not None
        seen = _Recorder.seen

        runtime._on_main("/btn", (1.0,))
        runtime._on_main("/btn", (0.0,))
        assert seen == [(uid["/btn"], True), (uid["/btn"], False)]

        seen.clear()
        runtime._on_main("/trig", ())  # own delay 40, not the server's 400
        assert seen == [(uid["/trig"], True)]
        wait_until(lambda: len(seen) >= 2, "the /trig release")
        assert seen == [(uid["/trig"], True), (uid["/trig"], False)]

        seen.clear()
        runtime._on_main("/axis", ("x", 0.0))
        runtime._on_main("/axis", ("x", 0.5))
        runtime._on_main("/axis", ("x", 1.0))
        assert seen == [(uid["/axis"], -1.0), (uid["/axis"], 0.0),
                        (uid["/axis"], 1.0)]

        seen.clear()
        runtime._on_main("/chg", (3,))
        wait_until(lambda: len(seen) >= 2, "the /chg release")
        runtime._on_main("/chg", (3,))
        QtTest.QTest.qWait(100)  # kept: the same value must NOT pulse
        assert seen == [(uid["/chg"], True), (uid["/chg"], False)]

        seen.clear()
        runtime._on_main("/scene", (2,))
        runtime._on_main("/SCENE", (1,))
        wait_until(lambda: len(seen) >= 2, "the /scene release")
        assert seen == [(uid["/scene"], True), (uid["/scene"], False)]

        seen.clear()
        runtime._on_main("/p2", (1.0, 0.0))
        runtime._on_main("/p2", (0.0, 1.0))
        assert seen == [(uid["/p2"], False), (uid["/p2"], True)]

        seen.clear()
        runtime._on_main("/unknown", (1.0,))
        assert seen == []
    finally:
        EventListener().joystick_event.disconnect(runner.event_handler.process_event)
        runtime.stop()


# -- (4) Import ---------------------------------------------------------------


def test_import_text_with_suffixes_saves_settings(env: Path) -> None:
    model = OscDeviceManagementModel()
    text = "/a A\n/b, B\n/c BNP\n/d,C\n/e E\n/f X\n/a A\nnope"
    result = model.importInputs(text)
    lines = result.splitlines()
    assert lines[0] == "Added 6, skipped 2"
    assert not any("/e E" in line for line in lines[1:])
    assert any("/f X" in line for line in lines[1:])
    assert any("nope" in line for line in lines[1:])

    shared_state.current_profile.to_xml(env.parent / "p.xml")
    rows = _reload_from_file()
    got = {label: (r.input_type, r.mode, r.trigger) for label, r in rows.items()}
    assert got == {
        "/a": (AXIS, "axis", None),
        "/b": (BUTTON, "button", None),
        "/c": (BUTTON, "button", True),
        "/d": (BUTTON, "change", None),
        "/e": (AXIS, "encoder", None),  # D-09-OSC-ENCODER: encoder axis
        "/f": (BUTTON, "button", None),
    }
    assert (rows["/e"].enc_format, rows["/e"].enc_output) == ("auto", "axis")
