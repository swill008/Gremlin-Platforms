# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC batch 3 runtime (spec 09 S159-S161, S164): the sender allow-list,
Invert and deadzone on axis inputs, encoder acceleration, OSC values for
conditions (input_cache.osc_state) and recorders for macro Record. No
network: messages go straight into the runtime's handler; the UDP listener
is a stand-in."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtTest

from gremlin import clock, input_cache, osc, osc_rows, shared_state
from gremlin import osc_device_file as odf
from gremlin.error import GremlinError
from gremlin.event_handler import EventListener
from gremlin.osc import OscDevice, OscRuntime
from gremlin.osc_rows import OscRows
from gremlin.types import InputType

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton
PEER = ("192.168.1.20", 9000)


class FakeListener:
    made: list[FakeListener] = []

    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback
        self.open = False

    def start(self) -> None:
        self.open = True
        FakeListener.made.append(self)

    def stop(self) -> None:
        self.open = False


class FakeState:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def set_button(self, uid: str, pressed: bool) -> None:
        self.calls.append(("button", uid, pressed))

    def set_axis(self, uid: str, value: float) -> None:
        self.calls.append(("axis", uid, round(value, 4)))

    def clear(self) -> None:
        self.calls.append(("clear",))


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> dict:
    """The saved server settings the runtime reads (clean_server applied)."""
    values: dict = {}
    monkeypatch.setattr(odf, "read_server", lambda: odf.clean_server(values))
    return values


@pytest.fixture
def run(qapp: object, server: dict, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple]:
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [object()]}),
    )
    traffic: list[tuple] = []
    mod = ModuleType("gremlin.osc_traffic")
    mod.note = lambda *a: traffic.append(a)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.osc_traffic", mod)
    state = FakeState()
    monkeypatch.setattr(input_cache, "osc_state", lambda: state)
    FakeListener.made = []
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.stop()
    state.calls.clear()
    events: list[tuple] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            if event.event_type == AXIS:
                events.append(("axis", event.identifier, round(event.value, 4)))
            else:
                events.append(("button", event.identifier, event.is_pressed))

    EventListener().joystick_event.connect(record)
    yield SimpleNamespace(
        runtime=runtime, rows=rows, events=events, traffic=traffic, state=state
    )
    EventListener().joystick_event.disconnect(record)
    for callback in list(runtime._recorders):
        runtime.remove_recorder(callback)
    for token in list(runtime._holders):
        runtime.release_open(token)
    runtime.stop()
    rows.load_dict(saved)


# -- sender allow-list (S160) --------------------------------------------------


def test_allow_senders_is_cleaned_with_an_empty_default() -> None:
    assert odf.clean_server({})["allow_senders"] == []
    assert odf.SERVER_DEFAULTS["allow_senders"] == []
    cleaned = odf.clean_server(
        {"allow_senders": [" 192.168.1.5 ", "10.0.0.7/8", "nope", "192.168.1.5", 3]}
    )
    assert cleaned["allow_senders"] == ["192.168.1.5", "10.0.0.0/8"]
    assert odf.clean_server({"allow_senders": "192.168.1.5"})["allow_senders"] == []
    assert odf.sender_entry("fe80::1") == "fe80::1"
    assert odf.sender_entry("300.1.1.1") is None


def test_sender_allowed_matches_addresses_and_cidr_ranges() -> None:
    allow = ["192.168.1.0/24", "10.1.2.3"]
    assert osc.sender_allowed("192.168.1.77", allow)
    assert osc.sender_allowed("10.1.2.3", allow)
    assert not osc.sender_allowed("10.1.2.4", allow)
    assert not osc.sender_allowed("192.168.2.1", allow)
    assert osc.sender_allowed("::ffff:192.168.1.9", allow)
    assert not osc.sender_allowed("not an ip", allow)
    # An empty list lets everyone in.
    assert osc.sender_allowed("8.8.8.8", [])


def test_blocked_sender_fires_nothing_and_shows_blocked(
    run: SimpleNamespace, server: dict
) -> None:
    server["allow_senders"] = ["10.0.0.0/8"]
    run.rows.create(BUTTON, "/b")
    run.runtime.start()
    run.runtime._on_main("/b", (1.0,), PEER)
    assert run.events == []
    assert run.traffic == [("in", "/b", (1.0,), PEER, ["blocked"])]
    run.runtime._on_main("/b", (1.0,), ("10.4.5.6", 1))
    assert run.events == [("button", 1, True)]


def test_empty_allow_list_lets_every_sender_in(run: SimpleNamespace) -> None:
    run.rows.create(BUTTON, "/b")
    run.runtime.start()
    run.runtime._on_main("/b", (1.0,), PEER)
    assert run.events == [("button", 1, True)]


def test_listen_obeys_the_allow_list(run: SimpleNamespace, server: dict) -> None:
    server["allow_senders"] = ["127.0.0.1"]
    got: list[tuple] = []
    run.runtime.learned.connect(lambda a, p: got.append((a, p)))
    assert run.runtime.listen_once()
    run.runtime._on_main("/x", (1,), PEER)
    assert got == [] and run.runtime.is_listening()
    run.runtime._on_main("/y", (2,), ("127.0.0.1", 5))
    assert got == [("/y", (2,))]


# -- Invert and deadzone (S161) ------------------------------------------------


def test_shaping_settings_are_validated_and_round_trip() -> None:
    rows = OscRows()
    row = rows.create(AXIS, "/a", invert=True, deadzone=[-0.1, 0.2])
    assert row.invert is True and row.deadzone == (-0.1, 0.2)
    again = OscRows()
    again.load_dict(rows.to_dict())
    assert again.load_warnings == []
    assert again.rows()[0].deadzone == (-0.1, 0.2) and again.rows()[0].invert
    for bad in (
        {"invert": 1},
        {"deadzone": (0.1, 0.2)},
        {"deadzone": (-0.1,)},
        {"deadzone": (-1.0, 0.0)},
        {"deadzone": "small"},
        {"enc_accel": "warp"},
    ):
        with pytest.raises(GremlinError):
            osc_rows.check_settings(bad)


def test_inverted_axis_quarter_reaches_plus_half(run: SimpleNamespace) -> None:
    run.rows.create(AXIS, "/f", invert=True)
    run.runtime.start()
    run.runtime._on_main("/f", (0.25,))
    assert run.events == [("axis", 1, 0.5)]


def test_deadzone_zeroes_small_values_and_stretches_the_rest(
    run: SimpleNamespace,
) -> None:
    run.rows.create(AXIS, "/f", range_min=-1.0, range_max=1.0, deadzone=(-0.2, 0.2))
    run.runtime.start()
    for value in (0.1, -0.15, 0.6, 1.0, -1.0):
        run.runtime._on_main("/f", (value,))
    assert [e[2] for e in run.events] == [0.0, 0.0, 0.5, 1.0, -1.0]


def test_encoder_axis_output_is_shaped(run: SimpleNamespace) -> None:
    run.rows.create(AXIS, "/e", mode="encoder", enc_step=0.25, invert=True)
    run.runtime.start()
    run.runtime._on_main("/e", (1,))
    run.runtime._on_main("/e", (1,))
    assert [e[2] for e in run.events] == [-0.25, -0.5]


# -- encoder acceleration (S164) -----------------------------------------------


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    return now


def _turn(run: SimpleNamespace, now: list[float], gap: float, count: int) -> None:
    for _ in range(count):
        run.runtime._on_main("/e", (1,))
        now[0] += gap


def test_fast_turns_move_further_than_slow(
    run: SimpleNamespace, fake_clock: list[float]
) -> None:
    run.rows.create(AXIS, "/e", mode="encoder", enc_step=0.01, enc_accel="medium")
    run.runtime.start()
    _turn(run, fake_clock, 0.5, 4)
    slow = run.events[-1][2]
    assert slow == pytest.approx(0.04)
    run.runtime.stop()
    run.events.clear()
    run.runtime.start()
    _turn(run, fake_clock, 0.01, 4)
    fast = run.events[-1][2]
    # 1x, 2x, 3x, 4x the step: 0.10.
    assert fast == pytest.approx(0.10)
    assert fast > slow


def test_acceleration_is_capped(run: SimpleNamespace, fake_clock: list[float]) -> None:
    run.rows.create(AXIS, "/e", mode="encoder", enc_step=0.01, enc_accel="high")
    run.runtime.start()
    _turn(run, fake_clock, 0.001, 10)
    steps = [
        b - a
        for a, b in zip([0.0] + [e[2] for e in run.events], [e[2] for e in run.events])
    ]
    assert max(steps) == pytest.approx(osc.ENC_ACCEL_MAX * 0.01)


def test_acceleration_off_is_unchanged(
    run: SimpleNamespace, fake_clock: list[float]
) -> None:
    run.rows.create(AXIS, "/e", mode="encoder", enc_step=0.01)
    assert run.rows.rows()[0].enc_accel == "off"
    run.runtime.start()
    _turn(run, fake_clock, 0.001, 4)
    assert [e[2] for e in run.events] == [0.01, 0.02, 0.03, 0.04]


def test_acceleration_multiplies_pulses(
    run: SimpleNamespace, fake_clock: list[float]
) -> None:
    row = run.rows.create(
        BUTTON,
        "/e",
        mode="encoder",
        enc_output="pulse_cw",
        enc_format="direction",
        enc_accel="high",
        delay_ms=5,
    )
    run.runtime.start()
    run.runtime._on_main("/e", (1,))  # 1 pulse
    fake_clock[0] += 0.01
    run.runtime._on_main("/e", (1,))  # 2 ticks in the window: x3
    pending = run.runtime._enc_pending[(row.uid, "")]
    # The first pulse is under way: 1 queued earlier (0) + 3 now.
    assert pending == 3


# -- OSC values for conditions (S159) ------------------------------------------


def test_osc_state_is_written_and_cleared_at_stop(run: SimpleNamespace) -> None:
    axis = run.rows.create(AXIS, "/f", invert=True)
    button = run.rows.create(BUTTON, "/b")
    run.runtime.start()
    run.runtime._on_main("/f", (0.25,))
    run.runtime._on_main("/b", (1.0,))
    run.runtime.stop()
    assert run.state.calls == [
        ("axis", axis.uid, 0.5),
        ("button", button.uid, True),
        ("button", button.uid, False),  # the held button released at Stop
        ("clear",),
    ]


# -- recorders (S159) ----------------------------------------------------------


def test_recorder_gets_events_without_a_run_and_holds_the_port(
    run: SimpleNamespace,
) -> None:
    axis = run.rows.create(AXIS, "/f")
    button = run.rows.create(BUTTON, "/b")
    got: list[tuple] = []

    def recorder(uid: str, kind: str, value: Any) -> None:  # noqa: ANN401
        got.append((uid, kind, round(value, 4) if kind == "axis" else value))

    assert run.runtime.add_recorder(recorder)
    assert run.runtime.is_open()
    run.runtime._on_main("/f", (0.75,))
    run.runtime._on_main("/b", (1.0,))
    run.runtime._on_main("/b", (0.0,))
    assert got == [
        (axis.uid, "axis", 0.5),
        (button.uid, "button", True),
        (button.uid, "button", False),
    ]
    # No Run: nothing reached the profile or the condition state.
    assert run.events == [] and run.state.calls == []
    run.runtime.remove_recorder(recorder)
    assert not run.runtime.is_open()
    run.runtime._on_main("/b", (1.0,))
    assert len(got) == 3


def test_recorder_sees_auto_release_pulses_without_a_run(
    run: SimpleNamespace,
) -> None:
    button = run.rows.create(BUTTON, "/t", trigger=True, delay_ms=10)
    got: list[tuple] = []
    run.runtime.add_recorder(lambda u, k, v: got.append((u, k, v)))
    run.runtime._on_main("/t", ())
    QtTest.QTest.qWait(80)
    assert got == [(button.uid, "button", True), (button.uid, "button", False)]


def test_a_valid_deadzone_logs_no_error(caplog: pytest.LogCaptureFixture) -> None:
    from gremlin import osc_rows

    with caplog.at_level("ERROR"):
        assert osc_rows._deadzone([0.0, 0.0]) == (0.0, 0.0)
        assert osc_rows._deadzone([-0.2, 0.2]) == (-0.2, 0.2)
    assert "Invalid OSC deadzone" not in caplog.text
