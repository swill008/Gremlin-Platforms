# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Tracing additions from the 2026-11-22 display-wake gaps
(claude/plans/control-api.md, "Same batch: tracing additions"):

- a vJoy keep-alive reset writes an OUTPUT trace line (06);
- output.last_write_age_s(): seconds since the last vJoy / Xbox write;
- "Profile started (<name>)" / "Profile stopped (<name>)" in the system log;
- a date line when tracing turns on and before the first line after midnight;
- the keep-off wake line names the last input Windows saw and the time since
  the last vJoy / Xbox write (12).

The keep-alive runs the real open path (output._open_vjoy) on a fake vJoy
proxy with a stepped gremlin.clock and the Run timers fired by the test, as
test_vjoy_keep_alive_option.py does. No real vJoy, ViGEm or Windows calls.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

from gremlin import clock, run_scope, trace
from gremlin.config import Configuration
from gremlin.modules import output

_KEEP_ALIVE = ("global", "vjoy", "keep-alive")


# --- helpers -----------------------------------------------------------------


def _texts(start: int = 0) -> list[str]:
    """The trace lines (control, point, detail) written since index start."""
    with trace._LOCK:  # noqa: SLF001
        lines = list(trace._lines)[start:]  # noqa: SLF001
    return [f"{c} | {p} | {d}" for _stamp, c, p, d, _w in lines]


def _line_count() -> int:
    with trace._LOCK:  # noqa: SLF001
        return len(trace._lines)  # noqa: SLF001


class _Device:
    def __init__(self, now: list[float]) -> None:
        self._now = now
        self.last_active = now[0]
        self.resets: list[float] = []

    def reset(self) -> None:
        self.resets.append(self._now[0])
        self.last_active = self._now[0]


class _Driver:
    """A stepped clock (monotonic), a fake vJoy proxy and the keep-alive's
    Run timers, fired by run_until."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.now = [1000.0]
        self.timers: list[list[Any]] = []
        self.devices: dict[int, _Device] = {}
        driver = self

        class Timer:
            def __init__(self, entry: list[Any]) -> None:
                self.entry = entry

            def is_alive(self) -> bool:
                return self.entry in driver.timers

            def cancel(self) -> None:
                if self.entry in driver.timers:
                    driver.timers.remove(self.entry)

        def timer(_name: str, seconds: float, fn: Any, *args: object) -> Timer:  # noqa: ANN401
            entry = [driver.now[0] + seconds, fn, args]
            driver.timers.append(entry)
            return Timer(entry)

        class Proxy:
            vjoy_devices: dict[int, _Device] = {}

            def __getitem__(self, vid: int) -> _Device:
                device = _Device(driver.now)
                driver.devices[vid] = device
                Proxy.vjoy_devices = {**Proxy.vjoy_devices, vid: device}
                return device

            @classmethod
            def reset(cls) -> None:
                cls.vjoy_devices = {}

        monkeypatch.setattr(clock, "monotonic", lambda: driver.now[0])
        monkeypatch.setattr(output.run_scope, "timer", timer)
        monkeypatch.setattr(output, "_vjoy_proxy", lambda: Proxy)
        monkeypatch.setattr(output, "_keep_alive", {})
        monkeypatch.setattr(output, "_last_write_at", None, raising=False)

    def run_until(self, end: float) -> None:
        for _ in range(100):
            due = [t for t in self.timers if t[0] <= end]
            if not due:
                break
            entry = min(due, key=lambda t: t[0])
            self.timers.remove(entry)
            self.now[0] = entry[0]
            entry[1](*entry[2])
        self.now[0] = end


@pytest.fixture
def driver(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Driver]:
    before = Configuration().value(*_KEEP_ALIVE)
    run_scope._reset_for_tests()  # noqa: SLF001
    run_scope.begin()
    fake = _Driver(monkeypatch)
    try:
        yield fake
    finally:
        output.reset_vjoy()
        run_scope.stop()
        run_scope._reset_for_tests()  # noqa: SLF001
        Configuration().set(*_KEEP_ALIVE, before)
        trace.set_enabled(False)


# --- vJoy keep-alive reset trace line ---------------------------------------


def test_a_keep_alive_reset_writes_an_output_trace_line(driver: _Driver) -> None:
    Configuration().set(*_KEEP_ALIVE, True)
    trace.set_enabled(True)
    start = _line_count()
    opened = driver.now[0]
    output._open_vjoy(2)  # noqa: SLF001
    driver.run_until(opened + 61.0)
    assert driver.devices[2].resets == [pytest.approx(opened + 60.0)]
    resets = [t for t in _texts(start) if "keep-alive reset" in t]
    assert resets == [f"vjoy 2 | {trace.OUTPUT} | vJoy 2 keep-alive reset (idle 60 s)"]


def test_no_keep_alive_line_while_tracing_is_off(driver: _Driver) -> None:
    Configuration().set(*_KEEP_ALIVE, True)
    start = _line_count()
    opened = driver.now[0]
    output._open_vjoy(2)  # noqa: SLF001
    driver.run_until(opened + 61.0)
    assert len(driver.devices[2].resets) == 1
    assert not [t for t in _texts(start) if "keep-alive" in t]


# --- output.last_write_age_s() ----------------------------------------------


def test_last_write_age_is_none_before_any_write(driver: _Driver) -> None:
    assert output.last_write_age_s() is None


def test_last_write_age_counts_from_the_keep_alive_reset(driver: _Driver) -> None:
    Configuration().set(*_KEEP_ALIVE, True)
    opened = driver.now[0]
    output._open_vjoy(2)  # noqa: SLF001
    driver.run_until(opened + 60.0)  # the reset fires at +60
    driver.now[0] = opened + 65.0
    assert output.last_write_age_s() == pytest.approx(5.0)


def test_last_write_age_counts_from_an_xbox_write(
    driver: _Driver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real write_xbox call, ViGEm replaced by a stand-in module."""
    applied: list[tuple[object, object]] = []

    class Pad:
        def apply(self, target: object, value: object) -> None:
            applied.append((target, value))

    class XboxProxy:
        def __getitem__(self, _pad: int) -> Pad:
            return Pad()

    monkeypatch.setitem(sys.modules, "vigem.xbox", SimpleNamespace(XboxProxy=XboxProxy))
    monkeypatch.setattr(output, "xbox_pads_on", lambda: [1])
    assert output.write_xbox(1, "A", True) is True
    assert applied == [("A", True)]
    driver.now[0] += 2.5
    assert output.last_write_age_s() == pytest.approx(2.5)


def test_last_write_age_counts_from_a_vjoy_write(
    driver: _Driver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real write_vjoy path (claim check, _write_vjoy) on a stand-in
    vJoy device: a value written sets the age."""
    axis = SimpleNamespace(value=0.0)
    dev = SimpleNamespace(
        is_axis_valid=lambda axis_id=None, linear_index=None: axis_id == 1,
        is_button_valid=lambda index: False,
        is_hat_valid=lambda index: False,
        axis=lambda axis_id: axis,
    )
    claim = {"buttons": [], "axes": [1], "hats": [], "keys": [], "friendly": {}}
    monkeypatch.setattr(output, "_open_vjoy", lambda vid: dev)
    monkeypatch.setattr(output, "vjoy_claim", lambda vid: claim)
    output.clear_blocked_log()
    try:
        assert output.write_vjoy(3, "axis", 1, 0.5) is True
    finally:
        output.clear_blocked_log()
    assert axis.value == pytest.approx(0.5)
    driver.now[0] += 1.25
    assert output.last_write_age_s() == pytest.approx(1.25)


def test_last_write_age_never_goes_negative(driver: _Driver) -> None:
    monkeypatch_at = driver.now[0]
    output._last_write_at = monkeypatch_at + 10.0  # noqa: SLF001 - clock stepped back
    assert output.last_write_age_s() == 0.0


# --- date line ---------------------------------------------------------------


def _local(y: int, mo: int, d: int, h: int, mi: int, s: int) -> float:
    return time.mktime((y, mo, d, h, mi, s, 0, 0, -1))


@pytest.fixture
def wall(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[float]]:
    """clock.now() on a stepped wall clock; tracing off again after."""
    now = [_local(2026, 11, 23, 23, 59, 58)]
    monkeypatch.setattr(clock, "now", lambda: now[0])
    trace.set_enabled(False)
    try:
        yield now
    finally:
        trace.set_enabled(False)


def test_tracing_on_starts_with_a_date_line(wall: list[float]) -> None:
    start = _line_count()
    trace.set_enabled(True)
    lines = _texts(start)
    assert lines[0] == f" | {trace.EVENT} | --- 2026-11-23 ---"
    assert lines[1] == f" | {trace.EVENT} | Tracing on"


def test_trace_log_starts_with_the_bare_date_line(wall: list[float]) -> None:
    trace.set_enabled(True)
    path = trace.file_path()
    for handler in list(trace._logger.handlers if trace._logger else []):  # noqa: SLF001
        handler.flush()
    text = path.read_text(encoding="utf-8").splitlines()
    dates = [i for i, t in enumerate(text) if t == "--- 2026-11-23 ---"]
    assert dates, text[-5:]
    # The date line is bare; the next is the stamped "Tracing on".
    assert text[dates[-1] + 1].endswith("Tracing on")


def test_the_first_line_after_midnight_gets_a_date_line(wall: list[float]) -> None:
    trace.set_enabled(True)
    trace.event("before midnight")
    start = _line_count()
    wall[0] = _local(2026, 11, 24, 0, 0, 1)
    trace.event("after midnight")
    trace.event("same day again")
    lines = _texts(start)
    assert [t for t in lines if "---" in t] == [
        f" | {trace.EVENT} | --- 2026-11-24 ---"
    ]
    assert lines.index(f" | {trace.EVENT} | --- 2026-11-24 ---") < next(
        i for i, t in enumerate(lines) if "after midnight" in t
    )


def test_no_date_line_within_the_same_day(wall: list[float]) -> None:
    trace.set_enabled(True)
    start = _line_count()
    wall[0] += 1.0
    trace.event("one")
    trace.event("two")
    assert not [t for t in _texts(start) if t.endswith("---")]


def test_tracing_on_again_writes_the_date_again(wall: list[float]) -> None:
    trace.set_enabled(True)
    trace.set_enabled(False)
    start = _line_count()
    trace.set_enabled(True)
    assert _texts(start)[0].endswith("--- 2026-11-23 ---")


# --- Profile started / stopped in the system log ----------------------------


@pytest.fixture
def runner(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """A real CodeRunner start/stop; vJoy, devices, sound and network are
    stand-ins (as in test_run_start_marks.py). The session's app (qapp),
    never a bare QCoreApplication: a later test's QApplication would crash."""
    from gremlin import code_runner, shared_state

    for name in ("OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    monkeypatch.setattr(output, "refresh", lambda: None)
    monkeypatch.setattr(output, "vjoy_modules", lambda: [])
    monkeypatch.setattr(output, "vjoy_driver_found", lambda: True)
    monkeypatch.setattr(output, "open_claimed_vjoy", lambda: [])
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    try:
        yield run
    finally:
        run.stop()
        shared_state.set_runtime_active(False)
        output.clear_blocked_log()


def _profile(tmp_path: Any) -> Any:  # noqa: ANN401
    from gremlin.profile import Profile

    p = Profile()
    p.fpath = str(tmp_path / "Night Flight.xml")
    return p


def test_profile_start_and_stop_are_in_the_system_log(
    runner: Any,  # noqa: ANN401
    tmp_path: Any,  # noqa: ANN401
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="system"):
        runner.start(_profile(tmp_path), "Default")
        assert runner.is_running()
        runner.stop()
    messages = [r.getMessage() for r in caplog.records if r.name == "system"]
    started = [m for m in messages if re.match(r"Profile started \(.*\)", m)]
    stopped = [m for m in messages if re.match(r"Profile stopped \(.*\)", m)]
    assert len(started) == 1, messages
    assert len(stopped) == 1, messages
    assert started[0] == "Profile started (Night Flight)"
    assert stopped[0] == "Profile stopped (Night Flight)"
    assert messages.index(started[0]) < messages.index(stopped[0])


# --- keep-off wake line: the last input before it and the last write -------


class _SsmApi:
    """Only what keeping the displays off asks Windows; nothing real."""

    def __init__(self) -> None:
        self.powered_off = 0
        self.names: dict[int, str] = {}
        self.parts: dict[int, str] = {}

    def foreground_is_own(self) -> bool:
        return False

    def screen_saver_path(self) -> str:
        return ""

    def screen_saver_wait_s(self) -> int:
        return 0

    def display_off_wait_s(self) -> int:
        return 120

    def windows_idle_s(self) -> float:
        return 0.5

    def display_required(self) -> bool:
        return False

    def fullscreen_busy(self) -> bool:
        return False

    def locked(self) -> bool:
        return False

    def start_screen_saver(self, path: str) -> bool:
        return True

    def power_off_displays(self) -> None:
        self.powered_off += 1

    def foreground_program(self) -> str:
        return ""

    def screen_saver_running(self) -> bool:
        return False

    def device_name(self, handle: int) -> str:
        return self.names.get(handle, "")

    def device_part(self, handle: int) -> str:
        return self.parts.get(handle, "")

    def device_physical_id(self, handle: int) -> str:
        return f"phys-{handle}"

    def input_devices(self) -> list[Any]:
        return []


@pytest.fixture
def keep_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """Screen Saver Mode keeping the displays off (power off fired at
    t = 1120) on a stepped clock, a fake Windows and a fake input clock;
    _trace collected; the output module's last write age faked."""
    from gremlin import screen_saver_mode as ssm
    from gremlin import threads

    mono = [1000.0]
    wall = [50_000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: mono[0])
    monkeypatch.setattr(clock, "now", lambda: wall[0])

    class _T:
        def cancel(self) -> None:
            pass

    monkeypatch.setattr(threads, "main_timer", lambda *_a, **_k: _T())
    lines: list[str] = []
    monkeypatch.setattr(
        ssm, "_trace", lambda text, ring=True, t=None: lines.append(text)
    )

    class _Clock(ssm.InputClock):
        def arm_timer(self, delay_s: float) -> bool:
            return True

        def arm_poll_timer(self, delay_s: float) -> bool:
            return True

        def start(self) -> bool:
            self._last = clock.monotonic()
            return True

        def stop(self) -> None:
            pass

        def listening(self) -> bool:
            return True

        def watch_controllers(self, on: bool) -> bool:
            watched.append(on)
            return True

    watched: list[bool] = []
    age: list[float | None] = [None]
    monkeypatch.setattr(output, "last_write_age_s", lambda: age[0])
    api = _SsmApi()
    clk = _Clock()
    mode = ssm.ScreenSaverMode(api=api, clock_=clk)
    mode.apply(
        ssm.Settings(
            enabled=True,
            screen_saver_on=False,
            screen_saver_wait_s=0,
            power_off_on=True,
            power_off_wait_s=0,
            hold_fullscreen=True,
        )
    )
    for _ in range(120):
        mono[0] += 1.0
        wall[0] += 1.0
        mode.tick()
    assert api.powered_off == 1
    assert mode.status().keeping_off is True
    try:
        yield SimpleNamespace(
            mode=mode,
            api=api,
            clk=clk,
            mono=mono,
            wall=wall,
            lines=lines,
            age=age,
            watched=watched,
        )
    finally:
        mode.apply(ssm.Settings(enabled=False))


def _wake(k: SimpleNamespace) -> str:
    """Windows turns the displays back on; the main thread drains the line."""
    k.mode.on_display_state(False)
    k.mono[0] += 5.0
    k.wall[0] += 5.0
    k.lines.clear()
    k.mode.on_display_state(True)
    k.mode.tick()
    woke = [t for t in k.lines if "power off sent again (#1)" in t]
    assert len(woke) == 1, k.lines
    return woke[0]


def test_the_wake_line_names_an_uncounted_device_and_the_last_write(
    keep_off: SimpleNamespace,
) -> None:
    k = keep_off
    k.api.names[7] = "Logitech G502"
    k.clk._seen = (7, "mouse", False, k.mono[0] + 3.0)  # noqa: SLF001 - 2 s before the wake
    k.age[0] = 14.0
    line = _wake(k)
    assert line.endswith(
        "power off sent again (#1): last input Logitech G502 (mouse) 2.0 s "
        "before, not counted; last vJoy/Xbox write 14 s ago"
    ), line


def test_the_wake_line_names_the_hid_part_of_a_game_controller(
    keep_off: SimpleNamespace,
) -> None:
    from gremlin import screen_saver_mode as ssm

    k = keep_off
    k.api.names[9] = "VKB Gladiator"
    k.api.parts[9] = "Col02"
    k.clk._seen = (9, ssm.SEEN_CONTROLLER, False, k.mono[0] + 4.5)  # noqa: SLF001
    k.age[0] = None
    line = _wake(k)
    assert line.endswith(
        "last input VKB Gladiator (game controller, Col02) 0.5 s before, "
        "not counted; no vJoy/Xbox write yet"
    ), line


def test_the_wake_line_names_gremlins_own_input_from_the_real_input_path(
    keep_off: SimpleNamespace,
) -> None:
    k = keep_off
    k.mono[0] += 1.0
    k.clk.note_input(own=True)  # the real path: own input is never counted
    k.age[0] = 0.8
    line = _wake(k)
    assert "last input Gremlin's own input 5.0 s before, not counted" in line, line
    assert line.endswith("last vJoy/Xbox write 0.8 s ago"), line


def test_the_wake_line_says_when_no_input_was_seen(keep_off: SimpleNamespace) -> None:
    k = keep_off
    k.clk._seen = None  # noqa: SLF001
    line = _wake(k)
    assert "(#1): no input seen before it;" in line, line


def test_game_controllers_are_heard_only_while_keeping_off(
    keep_off: SimpleNamespace,
) -> None:
    k = keep_off
    assert k.watched == [True]  # keep-off started
    k.mono[0] += 1.0
    k.clk.note_input(source=None, kind="keyboard")  # counted input ends it
    k.mode.tick()
    assert k.mode.status().keeping_off is False
    assert k.watched == [True, False]


def test_a_restart_logs_the_old_profile_stopped_then_the_new_started(
    runner: Any,  # noqa: ANN401
    tmp_path: Any,  # noqa: ANN401
    caplog: pytest.LogCaptureFixture,
) -> None:
    from gremlin.profile import Profile

    old = _profile(tmp_path)
    new = Profile()
    new.fpath = str(tmp_path / "Day Flight.xml")
    with caplog.at_level(logging.INFO, logger="system"):
        runner.start(old, "Default")
        caplog.clear()
        runner.start(new, "Default")  # started while running: a restart
        assert runner.is_running()
    messages = [
        r.getMessage()
        for r in caplog.records
        if r.name == "system" and r.getMessage().startswith("Profile ")
    ]
    assert messages == [
        "Profile stopped (Night Flight)",
        "Profile started (Day Flight)",
    ]


# --- the switchable categories (control API, design for change) ---------------


def test_categories_name_every_on_off_row_of_the_trace_tab() -> None:
    """trace.categories() owns the rows another program may switch: one per
    on/off row saved in debug/trace, plus osc/<area> for each OSC area."""
    names = [c.name for c in trace.categories()]
    assert names[:5] == ["hidhide", "screen-saver-mode", "window", "timing", "osc"]
    assert names[5:] == [f"osc/{area}" for area in trace.OSC_AREAS]


def test_every_trace_switch_setting_is_a_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: each setting trace.py registers under debug/trace is either a
    category (so the control API offers it) or named in NOT_CATEGORIES. A
    new Trace tab row with its own setting fails here until it is listed."""
    from gremlin import config

    registered: list[str] = []

    class _Cfg:
        def register(self, section: str, group: str, name: str, *_a: object) -> None:
            registered.append(name)

    monkeypatch.setattr(config, "Configuration", _Cfg)
    trace._ensure_options()  # noqa: SLF001
    assert registered
    owned = {c.config_key for c in trace.categories()}
    assert set(registered) - set(trace.NOT_CATEGORIES) == owned


def test_a_category_switch_sets_its_row() -> None:
    found = {c.name: c for c in trace.categories()}
    before = trace.window_ticked()
    try:
        found["window"].set(not before)
        assert trace.window_ticked() is (not before)
        assert found["window"].ticked() is (not before)
        found["osc/receive"].set(True)
        assert "receive" in trace.osc_ticked()
        found["osc/receive"].set(False)
        assert "receive" not in trace.osc_ticked()
    finally:
        trace.set_window(before)
