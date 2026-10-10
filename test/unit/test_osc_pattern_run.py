# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC address patterns at run time (spec 09 S147, S148, S150, S151; OX7):
messages go through the runtime's real main-thread handler (_on_main ->
_handle -> _apply -> EventListener). A pattern input keeps its state per
address: a button is pressed while any address holds it (OR), an axis
takes the last value, Change and encoder keep a value per address. Events
carry the received address; the Monitor names the pattern; Bulk capture
skips addresses an input already answers.

No network: the UDP listener is a stand-in. Module files live in a temp
folder."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtTest

from gremlin import clock, history_modules, osc, osc_bulk, osc_traffic, shared_state
from gremlin import osc_device_file as odf
from gremlin.event_handler import Event, EventListener
from gremlin.modules import store
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui.osc_device_model import OscDeviceManagementModel

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


class FakeListener:
    """Stands in for the UDP listener: nothing is bound."""

    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture
def rt(
    qapp: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[SimpleNamespace]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    monkeypatch.setattr(odf, "read_server", lambda: {"host": "127.0.0.1"})
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [object()]}),
    )
    traffic: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        osc_traffic,
        "note",
        lambda direction, address, args=(), peer=None, matched=None: traffic.append(
            (address, list(matched or []))
        ),
    )
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.cancel_listen()
    runtime.stop()
    runtime.reset_live()
    events: list[Event] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            events.append(event)

    EventListener().joystick_event.connect(record)
    yield SimpleNamespace(runtime=runtime, rows=rows, events=events, traffic=traffic)
    EventListener().joystick_event.disconnect(record)
    runtime.cancel_listen()
    runtime.stop()
    runtime.reset_live()
    rows.load_dict(saved)
    rows.mark_saved()
    odf.current_uid_map = None


def _send(rt: SimpleNamespace, address: str, *args: object) -> None:
    rt.runtime._on_main(address, tuple(args), None)


def _wait_for(done: Callable[[], bool], limit_s: float = 2.0) -> bool:
    """Runs Qt events until done() or limit_s passes (bounded)."""
    end = clock.monotonic() + limit_s
    while not done() and clock.monotonic() < end:
        QtTest.QTest.qWait(5)
    return done()


def _buttons(rt: SimpleNamespace) -> list[tuple[int, bool, str | None]]:
    return [
        (e.identifier, e.is_pressed, e.osc_address)
        for e in rt.events
        if e.event_type == BUTTON
    ]


def _axes(rt: SimpleNamespace) -> list[tuple[int, float, str | None]]:
    return [
        (e.identifier, round(e.value, 4), e.osc_address)
        for e in rt.events
        if e.event_type == AXIS
    ]


def test_a_pattern_button_is_pressed_while_any_address_holds_it(
    rt: SimpleNamespace,
) -> None:
    """S147 OR: the input presses on the first address, stays pressed while
    another still holds it, and releases when the last one lets go."""
    row = rt.rows.create(BUTTON, "/key/*")
    rt.runtime.start()
    _send(rt, "/key/a", 1.0)
    _send(rt, "/key/b", 1.0)
    _send(rt, "/key/a", 0.0)
    assert _buttons(rt) == [(row.input_id, True, "/key/a")]
    _send(rt, "/key/b", 0.0)
    assert _buttons(rt) == [
        (row.input_id, True, "/key/a"),
        (row.input_id, False, "/key/b"),
    ]
    assert rt.runtime.last_address(row.uid) == "/key/b"


def test_stop_releases_a_pattern_button_once(rt: SimpleNamespace) -> None:
    row = rt.rows.create(BUTTON, "/key/*")
    rt.runtime.start()
    _send(rt, "/key/a", 1.0)
    _send(rt, "/key/b", 1.0)
    rt.runtime.stop()
    assert [p for _i, p, _a in _buttons(rt)] == [True, False]
    assert _buttons(rt)[-1][0] == row.input_id


def test_a_pattern_axis_takes_the_last_value_and_names_its_address(
    rt: SimpleNamespace,
) -> None:
    row = rt.rows.create(AXIS, "/fader/?", range_min=0.0, range_max=1.0)
    rt.runtime.start()
    _send(rt, "/fader/1", 1.0)
    _send(rt, "/fader/2", 0.5)
    assert _axes(rt) == [
        (row.input_id, 1.0, "/fader/1"),
        (row.input_id, 0.0, "/fader/2"),
    ]
    assert rt.runtime.last_address(row.uid) == "/fader/2"


def test_change_keeps_its_last_value_per_address(rt: SimpleNamespace) -> None:
    """S147: the same value from a second address is a change there."""
    row = rt.rows.create(BUTTON, "/enc/*", mode="change", delay_ms=1)
    rt.runtime.start()
    _send(rt, "/enc/a", 5)
    assert _wait_for(lambda: len(_buttons(rt)) == 2)
    _send(rt, "/enc/b", 5)
    assert _wait_for(lambda: len(_buttons(rt)) == 4)
    assert _buttons(rt) == [
        (row.input_id, True, "/enc/a"),
        (row.input_id, False, "/enc/a"),
        (row.input_id, True, "/enc/b"),
        (row.input_id, False, "/enc/b"),
    ]


def test_an_encoder_keeps_its_position_per_address(rt: SimpleNamespace) -> None:
    row = rt.rows.create(
        AXIS,
        "/knob/*",
        mode="encoder",
        enc_output="axis",
        enc_format="signed",
        enc_step=0.1,
    )
    rt.runtime.start()
    _send(rt, "/knob/a", 3)
    _send(rt, "/knob/b", 1)
    _send(rt, "/knob/a", 1)
    assert _axes(rt) == [
        (row.input_id, 0.3, "/knob/a"),
        (row.input_id, 0.1, "/knob/b"),
        (row.input_id, 0.4, "/knob/a"),
    ]


def test_an_exact_input_wins_over_a_pattern(rt: SimpleNamespace) -> None:
    """S148: exact beats pattern; another address reaches the pattern. The
    Monitor names the pattern input with its pattern; an exact event carries
    its address too (S150)."""
    pattern = rt.rows.create(BUTTON, "/btn/*")
    exact = rt.rows.create(BUTTON, "/btn/1")
    rt.runtime.start()
    _send(rt, "/btn/1", 1.0)
    _send(rt, "/btn/2", 1.0)
    assert _buttons(rt) == [
        (exact.input_id, True, "/btn/1"),
        (pattern.input_id, True, "/btn/2"),
    ]
    assert rt.traffic == [
        ("/btn/1", [f"OSC Button {exact.input_id}"]),
        ("/btn/2", [f"OSC Button {pattern.input_id} (/btn/*)"]),
    ]


def test_an_incoming_pattern_reaches_exact_inputs_only(rt: SimpleNamespace) -> None:
    pattern = rt.rows.create(BUTTON, "/pad/*")
    one = rt.rows.create(BUTTON, "/pad/1")
    two = rt.rows.create(BUTTON, "/pad/2")
    rt.runtime.start()
    _send(rt, "/pad/[12]", 1.0)
    pressed = sorted(i for i, p, _a in _buttons(rt) if p)
    assert pressed == sorted([one.input_id, two.input_id])
    assert rt.runtime.last_address(pattern.uid) is None


def test_bulk_capture_skips_addresses_an_input_answers(
    rt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S151: an address an exact or pattern input already answers is not
    added again; the capture counts it as skipped."""
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    rt.rows.create(BUTTON, "/deck/*")
    rt.rows.create(BUTTON, "/solo")
    model = OscDeviceManagementModel()
    osc_bulk.start_bulk(model, {"mode": "button", "cmd_mode": "message"})
    _send(rt, "/deck/3")
    _send(rt, "/solo", 1)
    _send(rt, "/new", 1)
    model.cancelListen()
    assert sorted(r.label for r in rt.rows.rows()) == ["/deck/*", "/new", "/solo"]
    assert osc_bulk.bulk_skipped(model) == 2
