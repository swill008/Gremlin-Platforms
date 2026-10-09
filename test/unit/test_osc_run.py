# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's runtime (D-09-OSC-INPUT, D-09-OSC-FILE 4-5, D-09-OSC-FAULTS):
per-input behaviour, auto-release timers, settings from OSC's file, binding
and Listen. No network: messages go straight into the runtime's handler and
the UDP listener is a stand-in."""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtCore, QtTest

from gremlin import osc, shared_state
from gremlin import osc_device_file as odf
from gremlin.event_handler import EventListener
from gremlin.osc import OscDevice, OscRuntime
from gremlin.types import InputType

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


class FakeListener:
    """Stands in for the UDP listener; fail_ports refuse to bind."""

    made: list[FakeListener] = []
    fail_ports: set[int] = set()

    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback
        self.open = False

    def start(self) -> None:
        if self.port in FakeListener.fail_ports:
            raise OSError("address in use")
        self.open = True
        FakeListener.made.append(self)

    def stop(self) -> None:
        self.open = False


@pytest.fixture
def run(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple]:
    server: dict[str, Any] = {}
    monkeypatch.setattr(odf, "read_server", lambda: dict(server))
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    # The open profile has a binding on an OSC input (09 Q5: the port opens
    # at Run only then).
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [object()]}),
    )
    FakeListener.made = []
    FakeListener.fail_ports = set()
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.stop()
    events: list[tuple] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            if event.event_type == AXIS:
                events.append(("axis", event.identifier, round(event.value, 4)))
            else:
                events.append(("button", event.identifier, event.is_pressed))

    EventListener().joystick_event.connect(record)
    yield runtime, rows, events, server
    EventListener().joystick_event.disconnect(record)
    runtime.stop()
    rows.load_dict(saved)


def _wait(ms: int) -> None:
    QtTest.QTest.qWait(ms)


# -- per-input behaviour -----------------------------------------------------


def test_button_value_presses_and_zero_releases_without_timer(run: tuple) -> None:
    runtime, rows, events, _ = run
    row = rows.create(BUTTON, "/b")
    runtime.start()
    runtime._on_main("/b", (1.0,))
    runtime._on_main("/b", (0,))
    assert events == [("button", row.input_id, True), ("button", row.input_id, False)]
    assert runtime._timers == {}


def test_button_source_index_picks_the_value(run: tuple) -> None:
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/b", source=1)
    runtime.start()
    runtime._on_main("/b", (1.0, 0.0))
    assert events == [("button", 1, False)]


def test_button_no_value_uses_input_delay_and_trigger(run: tuple) -> None:
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/b", delay_ms=40)
    rows.create(BUTTON, "/held", trigger=False)
    runtime.start()
    runtime._on_main("/held", ())
    runtime._on_main("/b", ())
    assert events == [("button", 2, True), ("button", 1, True)]
    _wait(150)
    assert events[-1] == ("button", 1, False)
    assert ("button", 2, False) not in events


def test_trigger_true_pulses_even_with_a_value(run: tuple) -> None:
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/t", trigger=True, delay_ms=30)
    runtime.start()
    runtime._on_main("/t", (0.0,))
    assert events == [("button", 1, True)]
    _wait(120)
    assert events == [("button", 1, True), ("button", 1, False)]


def test_new_press_restarts_the_release_timer(run: tuple) -> None:
    """The old one-shot timers released early on a repeat press."""
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/b", delay_ms=300)
    runtime.start()
    runtime._on_main("/b", ())
    _wait(200)
    runtime._on_main("/b", ())
    _wait(170)
    assert ("button", 1, False) not in events
    _wait(300)
    assert events.count(("button", 1, False)) == 1


def test_stop_releases_a_pending_auto_release_once(run: tuple) -> None:
    """The auto-release timer is cancelled; Stop sends the release itself."""
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/b", delay_ms=50)
    runtime.start()
    runtime._on_main("/b", ())
    runtime.stop()
    assert events == [("button", 1, True), ("button", 1, False)]
    _wait(150)
    assert events == [("button", 1, True), ("button", 1, False)]


def test_stop_releases_held_buttons_while_callbacks_still_run(
    run: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved 2026-10-09: at Stop every held OSC button gets one release
    before the Run's input is cut (CodeRunner's real Stop order), so the
    profile's actions see it. Released buttons and axes are left alone."""
    from unittest import mock

    from gremlin import code_runner, run_scope

    runtime, rows, events, _ = run
    held = rows.create(BUTTON, "/held")
    trig = rows.create(BUTTON, "/trig", trigger=True, delay_ms=5000)
    noarg = rows.create(BUTTON, "/noarg", delay_ms=5000)
    done = rows.create(BUTTON, "/done")
    axis = rows.create(AXIS, "/x", range_min=0.0, range_max=1.0)
    for name in ("macro", "sendinput", "mode_manager", "audio_player", "tts",
                 "output"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    seen_by_profile: list[tuple] = []
    cut = {"done": False}

    def profile_callback(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID and not cut["done"]:
            seen_by_profile.append(
                (event.identifier, event.event_type, event.is_pressed)
            )

    def cut_input() -> None:
        cut["done"] = True

    EventListener().joystick_event.connect(profile_callback)
    fake_runner = SimpleNamespace(
        _cut_input=cut_input,
        _drop_release_actions=lambda: None,
        _end_scripts=lambda: None,
        _flush_pulses=lambda: None,
        _logical_device_neutral=lambda: None,
    )
    try:
        run_scope.stop()
        run_scope.begin()
        code_runner.CodeRunner._register_stop(fake_runner)
        runtime.start()
        runtime._on_main("/held", (1.0,))
        runtime._on_main("/trig", (1.0,))
        runtime._on_main("/noarg", ())
        runtime._on_main("/done", (1.0,))
        runtime._on_main("/done", (0.0,))
        runtime._on_main("/x", (0.75,))
        events.clear()
        seen_by_profile.clear()
        run_scope.stop()
        _wait(50)
    finally:
        EventListener().joystick_event.disconnect(profile_callback)
        run_scope._reset_for_tests()
    released = sorted(e for e in events if e[0] == "button")
    assert released == sorted(
        ("button", r.input_id, False) for r in (held, trig, noarg)
    )
    assert not [e for e in events if e[0] == "axis"]
    assert ("button", done.input_id, False) not in events
    assert sorted(seen_by_profile) == sorted(
        (r.input_id, BUTTON, False) for r in (held, trig, noarg)
    )
    assert runtime._timers == {} and axis.input_id == 1
    runtime.stop()
    assert len(events) == 3


def test_axis_scales_range_and_clamps(run: tuple) -> None:
    runtime, rows, events, _ = run
    rows.create(AXIS, "/x", range_min=0.0, range_max=10.0, source=1)
    runtime.start()
    runtime._on_main("/x", ("name", 5.0))
    runtime._on_main("/x", ("name", 10.0))
    runtime._on_main("/x", ("name", 20.0))
    runtime._on_main("/x", ("name",))
    runtime._on_main("/x", ("name", "text"))
    assert events == [("axis", 1, 0.0), ("axis", 1, 1.0), ("axis", 1, 1.0)]


def test_change_mode_pulses_only_when_value_changes(run: tuple) -> None:
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/c", mode="change", delay_ms=20)
    runtime.start()
    runtime._on_main("/c", (3,))
    _wait(80)
    runtime._on_main("/c", (3.0,))
    _wait(80)
    runtime._on_main("/c", (4,))
    _wait(80)
    assert events == [("button", 1, True), ("button", 1, False)] * 2


def test_data_mode_matches_values_and_pulses(run: tuple) -> None:
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/scene", cmd_mode="data", data=["1"], delay_ms=20)
    rows.create(BUTTON, "/scene", cmd_mode="data", data=["2"], delay_ms=20)
    runtime.start()
    runtime._on_main("/SCENE", (2,))
    runtime._on_main("/scene", (9,))
    _wait(80)
    assert events == [("button", 2, True), ("button", 2, False)]


def test_messages_are_ignored_when_no_profile_runs(run: tuple) -> None:
    runtime, rows, events, _ = run
    rows.create(BUTTON, "/b")
    runtime._on_main("/b", (1,))
    assert events == []


# -- settings and binding ----------------------------------------------------


def test_settings_come_from_oscs_file_and_blank_host_binds_all(run: tuple) -> None:
    runtime, _, _, server = run
    server.update(host="", port=9100)
    runtime.start()
    assert (runtime._listener.host, runtime._listener.port) == ("0.0.0.0", 9100)


def test_default_port_is_8001(run: tuple) -> None:
    runtime, _, _, _ = run
    runtime.start()
    assert runtime._listener.port == 8001


def test_server_default_delay_used_when_input_has_none(run: tuple) -> None:
    runtime, rows, events, server = run
    server.update(autorelease_delay_ms=30)
    rows.create(BUTTON, "/b")
    runtime.start()
    runtime._on_main("/b", ())
    _wait(120)
    assert events == [("button", 1, True), ("button", 1, False)]


def test_enable_mid_run_binds_and_failed_bind_retries(run: tuple) -> None:
    from gremlin.signal import signal

    runtime, _, _, server = run
    server.update(enabled=False)
    runtime.start()
    assert runtime._listener is None
    server.update(enabled=True, port=9200)
    FakeListener.fail_ports = {9200}
    signal.oscServerSettingsChanged.emit()
    assert runtime._listener is None
    server.update(port=9201)
    signal.oscServerSettingsChanged.emit()
    assert runtime._listener is not None and runtime._listener.port == 9201
    server.update(port=9202)
    signal.oscServerSettingsChanged.emit()
    assert runtime._listener.port == 9202
    assert not FakeListener.made[0].open


def test_run_opens_port_only_when_profile_uses_osc_inputs(
    run: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.signal import signal

    runtime, _, _, _ = run
    other = SimpleNamespace(inputs={"some-joystick": [object()]})
    monkeypatch.setattr(shared_state, "current_profile", other)
    runtime.start()
    assert runtime._listener is None and FakeListener.made == []
    signal.oscServerSettingsChanged.emit()
    assert runtime._listener is None
    runtime.listen_once()
    assert runtime._listener is not None
    runtime._on_main("/new", ())
    assert runtime._listener is None
    runtime.stop()
    other.inputs[osc.OSC_DEVICE_UUID] = [object()]
    runtime.start()
    assert runtime._listener is not None


# -- Listen ------------------------------------------------------------------


def test_single_listen_ends_on_its_message_and_closes_port(run: tuple) -> None:
    runtime, _, _, _ = run
    got: list[tuple] = []
    runtime.learned.connect(lambda a, p: got.append((a, p)))
    assert runtime.listen_once()
    listener = runtime._listener
    runtime._on_main("/new", (1,))
    assert got == [("/new", (1,))]
    assert not runtime.is_listening()
    assert runtime._listener is None and not listener.open


def test_cancel_listen_closes_port_when_no_profile_runs(run: tuple) -> None:
    runtime, _, _, _ = run
    runtime.listen_once()
    runtime.cancel_listen()
    assert runtime._listener is None


def test_listen_while_running_keeps_port_open(run: tuple) -> None:
    runtime, _, _, _ = run
    runtime.start()
    runtime.listen_once()
    runtime._on_main("/new", ())
    assert runtime._listener is not None


# -- bulk capture -------------------------------------------------------------


def test_bulk_capture_passes_window_settings_to_each_new_input(
    qapp: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import osc_bulk

    monkeypatch.setattr(osc_bulk.OscRuntime(), "listen_bulk", lambda: True)

    class Model(QtCore.QObject):
        commandCaptured = QtCore.Signal(str, str)

        def __init__(self) -> None:
            super().__init__()
            self.made: list[dict] = []
            self.window: dict | None = None

        def setCaptureSettings(self, settings: dict) -> None:
            self.window = settings

        def createConfiguredInput(self, settings: dict) -> None:
            self.made.append(settings)

    model = Model()
    window = {"mode": "button", "cmd_mode": "data", "source": 0, "trigger": True,
              "delay_ms": 100}
    osc_bulk.start_bulk(model, window)
    osc_bulk.model_on_learned(model, "/a", (1, "x"))
    osc_bulk.model_on_learned(model, "/b", ())
    assert model.window == window
    assert model.made == [
        dict(window, address="/a", data=["1", "x"]),
        dict(window, address="/b", data=[]),
    ]
