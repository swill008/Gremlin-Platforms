# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Home OSC card's second line (D-09-OSC-CARD-LINE): "Listening on ...",
the last message ("From <ip>: <address> <value>") until 3 s after the last
one, at most 4 changes a second in a flood, and "Server not started:
<reason>" in the warning colour. A stand-in OscRuntime and a stepped clock;
the timers' slots are called directly instead of waiting."""

from __future__ import annotations

from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import clock
from gremlin.ui import osc_card_status as ocs
from gremlin.ui.osc_card_status import OscCardStatus


class FakeRuntime(QtCore.QObject):
    incoming = QtCore.Signal(str, object, object)
    listenChanged = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.info: dict[str, Any] = {
            "state": "listening", "host": "0.0.0.0", "port": 9000, "reason": ""
        }

    def listenInfo(self) -> dict[str, Any]:  # noqa: N802
        return dict(self.info)

    def set(self, **info: Any) -> None:  # noqa: ANN401
        self.info = {"host": "0.0.0.0", "port": 9000, "reason": "", **info}
        self.listenChanged.emit()


@pytest.fixture
def now(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    if QtCore.QCoreApplication.instance() is None:
        QtCore.QCoreApplication([])
    t = [100.0]
    monkeypatch.setattr(clock, "monotonic", lambda: t[0])
    return t


@pytest.fixture
def rt() -> FakeRuntime:
    return FakeRuntime()


def _msg(rt: FakeRuntime, address: str, *values: object) -> None:
    rt.incoming.emit(address, values, ("192.168.1.20", 53000))


def test_listening_lines(now: list[float], rt: FakeRuntime) -> None:
    s = OscCardStatus(runtime=rt)
    assert (s.text, s.warn) == ("Listening on all addresses, port 9000", False)
    rt.set(state="listening", host="192.168.1.5", port=8000)
    assert (s.text, s.warn) == ("Listening on 192.168.1.5:8000", False)


def test_failed_is_a_warning_until_it_starts(
    now: list[float], rt: FakeRuntime
) -> None:
    s = OscCardStatus(runtime=rt)
    for reason in (
        "port 9000 is in use",
        "10.0.0.9 is not an address of this PC",
        "Windows refused port 9000",
    ):
        rt.set(state="failed", reason=reason)
        assert (s.text, s.warn) == (f"Server not started: {reason}", True)
    rt.set(state="listening")
    assert (s.text, s.warn) == ("Listening on all addresses, port 9000", False)


def test_closed_lines(now: list[float], rt: FakeRuntime) -> None:
    s = OscCardStatus(runtime=rt)
    rt.set(state="closed", reason="off")
    assert (s.text, s.warn) == (
        "Not listening (Listen for OSC messages is off)", False
    )
    rt.set(state="closed", reason="")
    assert (s.text, s.warn) == ("Not listening yet", False)


def test_message_then_back_after_3s_from_last(
    now: list[float], rt: FakeRuntime
) -> None:
    s = OscCardStatus(runtime=rt)
    _msg(rt, "/fader/1", 0.5, 3)
    assert s.text == "From 192.168.1.20: /fader/1 0.5"
    assert s._back.isActive() and s._back.interval() == 3000
    _msg(rt, "/ping")  # no values: the address alone
    now[0] += 1.0
    _msg(rt, "/b", "hello")
    assert s.text == "From 192.168.1.20: /b hello"
    # The 3 s count starts again at every message (a single-shot restarted).
    assert s._back.isActive() and s._back.remainingTime() > 2900
    s._back_to_listening()  # the timer's slot
    assert s.text == "Listening on all addresses, port 9000"
    assert not s._throttle.isActive()


def test_long_value_is_cut(now: list[float], rt: FakeRuntime) -> None:
    s = OscCardStatus(runtime=rt)
    _msg(rt, "/t", "x" * 100)
    assert s.text == "From 192.168.1.20: /t " + "x" * 40 + "…"


def test_flood_is_throttled_to_250ms_showing_newest(
    now: list[float], rt: FakeRuntime
) -> None:
    s = OscCardStatus(runtime=rt)
    seen: list[str] = []
    s.changed.connect(lambda: seen.append(s.text))
    _msg(rt, "/a", 1)
    for i in range(2, 50):
        now[0] += 0.001
        _msg(rt, "/a", i)
    # Only the first shows at once; the newest waits for the throttle.
    assert seen == ["From 192.168.1.20: /a 1"]
    assert s._throttle.isActive() and s._throttle.remainingTime() <= 250
    now[0] += 0.25
    s._flush()  # the timer's slot
    assert seen[-1] == "From 192.168.1.20: /a 49"
    assert len(seen) == 2
    # After the throttle window a message shows at once again.
    now[0] += 0.3
    _msg(rt, "/a", 50)
    assert seen[-1] == "From 192.168.1.20: /a 50"


def test_failure_shows_over_a_message(now: list[float], rt: FakeRuntime) -> None:
    s = OscCardStatus(runtime=rt)
    _msg(rt, "/a", 1)
    rt.set(state="failed", reason="port 9000 is in use")
    assert (s.text, s.warn) == ("Server not started: port 9000 is in use", True)
    assert not s._back.isActive()


def test_listening_change_keeps_the_message(
    now: list[float], rt: FakeRuntime
) -> None:
    s = OscCardStatus(runtime=rt)
    _msg(rt, "/a", 1)
    rt.set(state="listening", port=9001)
    assert s.text == "From 192.168.1.20: /a 1"
    s._back_to_listening()
    assert s.text == "Listening on all addresses, port 9001"


def test_constants() -> None:
    assert ocs.BACK_MS == 3000 and ocs.THROTTLE_MS == 250
