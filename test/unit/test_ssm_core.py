# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode core (program map 12, S2-S11, S15, S20): the two
timers and keeping the displays off, on a stepped clock with a fake
WindowsApi and a fake input clock; Windows' display-state reports are fed
straight to ScreenSaverMode.on_display_state. Nothing here calls Windows,
registers raw input or power notifications, or blanks a screen."""

from __future__ import annotations

import ctypes
from collections.abc import Callable
from typing import Any

import pytest

from gremlin import clock, sendinput, threads, windows_event_hook
from gremlin import screen_saver_mode as ssm

# mode, api, input clock, the stepped time, run(seconds), timers started
Env = tuple[Any, Any, Any, list[float], Callable[[int], None], list[str]]


class FakeApi(ssm.WindowsApi):
    def __init__(self) -> None:
        self.path = r"C:\Windows\System32\Mystify.scr"
        self.saver_wait = 60
        self.display_wait = 120
        self.idle = 0.5
        self.display_flag = False
        self.busy = False
        self.is_locked = False
        self.started: list[str] = []
        self.powered_off = 0
        self.foreground = ""
        self.saver_running = False
        self.names: dict[int, str] = {}
        self.name_calls: list[int] = []
        self.physical: dict[int, str] = {}
        self.physical_calls: list[int] = []
        self.own_in_front = False

    def foreground_is_own(self) -> bool:
        return self.own_in_front

    def screen_saver_path(self) -> str:
        return self.path

    def screen_saver_wait_s(self) -> int:
        return self.saver_wait if self.path else 0

    def display_off_wait_s(self) -> int:
        return self.display_wait

    def windows_idle_s(self) -> float:
        return self.idle

    def display_required(self) -> bool:
        return self.display_flag

    def fullscreen_busy(self) -> bool:
        return self.busy

    def locked(self) -> bool:
        return self.is_locked

    def start_screen_saver(self, path: str) -> bool:
        self.started.append(path)
        return True

    def power_off_displays(self) -> None:
        self.powered_off += 1

    def foreground_program(self) -> str:
        return self.foreground

    def screen_saver_running(self) -> bool:
        return self.saver_running

    def device_name(self, handle: int) -> str:
        self.name_calls.append(handle)
        return self.names.get(handle, "")

    def device_physical_id(self, handle: int) -> str:
        self.physical_calls.append(handle)
        return self.physical.get(handle, "")

    def input_devices(self) -> list[ssm.InputDevice]:
        return []

    @property
    def actions(self) -> int:
        return len(self.started) + self.powered_off


class FakeClock(ssm.InputClock):
    def __init__(self) -> None:
        super().__init__()
        self.started = 0
        self.stopped = 0
        self.ok = True
        self.armed: list[float] = []  # re-send timer delays asked for
        self.arm_ok = True
        self.polls: list[float] = []  # device-wait poll timer delays asked for

    def arm_timer(self, delay_s: float) -> bool:
        self.armed.append(delay_s)
        return self.arm_ok

    def arm_poll_timer(self, delay_s: float) -> bool:
        self.polls.append(delay_s)
        return self.arm_ok

    def start(self) -> bool:
        self.started += 1
        self._last = clock.monotonic()
        return self.ok

    def stop(self) -> None:
        self.stopped += 1

    def listening(self) -> bool:
        return self.ok and self.started > self.stopped


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> Env:
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    timers: list[str] = []

    class _T:
        def cancel(self) -> None:
            pass

    def fake_timer(
        name: str, seconds: float, function: Callable[..., Any], *args: object
    ) -> _T:
        timers.append(name)
        return _T()

    monkeypatch.setattr(threads, "main_timer", fake_timer)
    api = FakeApi()
    clk = FakeClock()
    mode = ssm.ScreenSaverMode(api=api, clock_=clk)

    def run(seconds: int) -> None:
        for _ in range(seconds):
            now[0] += 1.0
            mode.tick()

    return mode, api, clk, now, run, timers


def _on(
    saver: bool = True,
    saver_wait: int = 0,
    off: bool = True,
    off_wait: int = 0,
    hold_fullscreen: bool = True,
) -> ssm.Settings:
    return ssm.Settings(
        enabled=True,
        screen_saver_on=saver,
        screen_saver_wait_s=saver_wait,
        power_off_on=off,
        power_off_wait_s=off_wait,
        hold_fullscreen=hold_fullscreen,
    )


def _off_only(off_wait: int = 0) -> ssm.Settings:
    return _on(saver=False, off_wait=off_wait)


def test_off_starts_nothing(env: Env) -> None:
    mode, api, clk, _now, run, timers = env
    mode.apply(ssm.Settings(enabled=False))
    run(500)
    assert clk.started == 0
    assert timers == []
    assert api.actions == 0
    assert mode.status().enabled is False


def test_fires_once_per_idle_period(env: Env) -> None:
    mode, api, clk, _now, run, timers = env
    mode.apply(_off_only())
    assert clk.started == 1 and timers
    run(119)
    assert api.powered_off == 0
    assert mode.status().off_remaining_s == pytest.approx(1.0)
    run(1)
    assert api.powered_off == 1
    run(1000)
    assert api.powered_off == 1
    assert mode.status().off_fired is True
    assert api.started == []


def test_input_resets_the_countdown_and_fired(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    run(100)
    clk.note_input()
    run(100)
    assert api.powered_off == 0
    run(20)
    assert api.powered_off == 1
    clk.note_input()
    run(119)
    assert api.powered_off == 1
    run(1)
    assert api.powered_off == 2


def test_own_input_does_not_reset(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    run(100)
    clk.note_input(own=True)
    run(20)
    assert api.powered_off == 1


@pytest.mark.parametrize(
    "attr, hold",
    [
        ("is_locked", "locked"),
        ("busy", "fullscreen"),
        ("display_flag", "display_request"),
    ],
)
def test_hold_blocks_and_restarts_countdown(env: Env, attr: str, hold: str) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    run(50)
    # Both timers held: the screen saver (60 s) would have fired by now.
    setattr(api, attr, True)
    run(300)
    assert api.actions == 0
    st = mode.status()
    assert st.hold == hold
    assert st.off_remaining_s == 0 and st.saver_remaining_s == 0
    setattr(api, attr, False)
    run(59)
    assert api.actions == 0
    run(1)
    assert len(api.started) == 1 and api.powered_off == 0
    run(59)
    assert api.powered_off == 0
    run(1)
    assert api.powered_off == 1


def test_fullscreen_hold_can_be_switched_off(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on(hold_fullscreen=False))
    api.busy = True
    run(120)
    assert api.powered_off == 1


def test_screen_saver_uses_windows_wait_and_path(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on(off=False))
    st = mode.status()
    assert st.saver_wait_s == 60 and st.saver_windows_wait_s == 60
    assert st.saver_from_windows
    run(60)
    assert api.started == [api.path]
    assert api.powered_off == 0
    run(500)
    assert api.powered_off == 0


def test_override_replaces_windows_wait(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_off_only(off_wait=30))
    st = mode.status()
    assert st.off_wait_s == 30 and st.off_windows_wait_s == 120
    assert st.off_from_windows is False
    run(30)
    assert api.powered_off == 1


def test_windows_wait_read_again_when_countdown_starts(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_off_only())
    run(10)
    api.display_wait = 40
    clk.note_input()
    run(40)
    assert api.powered_off == 1


def test_windows_never_stops_only_that_row(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    api.display_wait = 0
    mode.apply(_on())
    run(5000)
    assert api.powered_off == 0
    assert api.started == [api.path]  # the screen saver row still works
    st = mode.status()
    assert st.off_problem == ssm.PROBLEM_WINDOWS_NEVER
    assert st.saver_problem == "" and st.problem == ""


def test_no_screen_saver_stops_only_that_row_even_with_a_typed_time(
    env: Env,
) -> None:
    mode, api, clk, _now, run, _t = env
    api.path = ""
    mode.apply(_on(saver_wait=10))
    run(500)
    assert api.started == []
    assert api.powered_off == 1  # power off works as usual (S8)
    st = mode.status()
    assert st.saver_problem == ssm.PROBLEM_NO_SCREEN_SAVER
    assert st.off_problem == "" and st.problem == ""


def test_not_listening_does_nothing(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    clk.ok = False
    mode.apply(_on())
    run(500)
    assert api.actions == 0
    assert mode.status().problem == ssm.PROBLEM_NOT_LISTENING
    assert mode.status().listening is False


def test_switching_off_stops_the_clock(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    mode.apply(ssm.Settings(enabled=False))
    assert clk.stopped == 1
    run(500)
    assert api.actions == 0


def test_status_idle_times(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    run(42)
    st = mode.status()
    assert st.idle_s == pytest.approx(42)
    assert st.windows_idle_s == pytest.approx(0.5)


def _raw(kind: int, extra: int) -> ssm.RAWINPUT:
    raw = ssm.RAWINPUT()
    raw.header.dwType = kind
    if kind == 0:
        raw.data.mouse.ulExtraInformation = extra
        raw.data.mouse.lLastX = 3
    else:
        raw.data.keyboard.ExtraInformation = extra
        raw.data.keyboard.VKey = 0x41
    return raw


def test_raw_input_kind() -> None:
    own = windows_event_hook.OWN_KEY_MARK
    assert ssm.raw_input_kind(_raw(0, 0)) == "input"
    assert ssm.raw_input_kind(_raw(1, 0)) == "input"
    assert ssm.raw_input_kind(_raw(1, 12345)) == "input"
    assert ssm.raw_input_kind(_raw(0, own)) == "own"
    assert ssm.raw_input_kind(_raw(1, own)) == "own"
    assert ssm.raw_input_kind(_raw(2, 0)) == ""  # HID: never counts


def test_raw_structs_match_windows_layout() -> None:
    # x64 sizes from the Windows SDK (winuser.h).
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        assert ctypes.sizeof(ssm.RAWINPUTHEADER) == 24
    assert ctypes.sizeof(ssm.RAWMOUSE) == 24
    assert ctypes.sizeof(ssm.RAWKEYBOARD) == 16
    assert ssm.RAWMOUSE.ulExtraInformation.offset == 20


def test_input_clock_never_registers_in_tests() -> None:
    assert windows_event_hook.enabled is False
    c = ssm.InputClock()
    assert c.start() is False
    assert c.listening() is False


def test_input_clock_note_input(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [5.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    c = ssm.InputClock()
    now[0] = 9.0
    c.note_input(own=True)
    assert c.last_input() == 5.0
    c.note_input()
    assert c.last_input() == 9.0


def test_own_mouse_input_is_marked() -> None:
    inp = sendinput._mouse_input(sendinput.MOUSEEVENTF_MOVE, 1, 2)
    mark = ctypes.cast(inp.union.mi.dwExtraInfo, ctypes.c_void_p).value
    assert mark == windows_event_hook.OWN_KEY_MARK


def test_manager_is_one_instance() -> None:
    assert ssm.manager() is ssm.manager()


def test_timer_rearms_while_on_and_stops_when_off(env: Env) -> None:
    mode, api, clk, now, _run, timers = env
    mode.apply(_on())
    assert len(timers) == 1
    now[0] += 1.0
    mode._on_timer()
    assert len(timers) == 2
    mode.apply(ssm.Settings(enabled=False))
    mode._on_timer()
    assert len(timers) == 2


# ---- batch 2: Windows' wait while off (S5), tracing (S16)


def test_status_off_shows_windows_wait(env: Env) -> None:
    mode, api, _clk, _now, _run, _t = env
    # Before any apply and before the first tick: Windows' 120 s, not "never".
    st = mode.status()
    assert st.enabled is False
    assert st.off_windows_wait_s == 120 and st.off_wait_s == 120
    assert st.off_from_windows is True
    mode.apply(ssm.Settings(enabled=False, power_off_wait_s=45))
    st = mode.status()
    assert st.off_windows_wait_s == 120 and st.off_wait_s == 45
    assert st.off_from_windows is False
    assert st.saver_windows_wait_s == 60 and st.saver_wait_s == 60
    assert st.saver_from_windows is True


def test_status_off_shows_both_windows_times_and_row_problems(env: Env) -> None:
    mode, api, _clk, _now, _run, _t = env
    st = mode.status()
    assert (st.saver_windows_wait_s, st.off_windows_wait_s) == (60, 120)
    mode.apply(ssm.Settings(enabled=False, screen_saver_wait_s=30))
    st = mode.status()
    assert (st.saver_wait_s, st.saver_windows_wait_s) == (30, 60)
    assert st.saver_from_windows is False and st.off_from_windows is True
    assert st.saver_problem == "" and st.off_problem == ""
    api.path = ""
    api.display_wait = 0
    mode.apply(ssm.Settings(enabled=False))
    st = mode.status()
    assert st.saver_problem == ssm.PROBLEM_NO_SCREEN_SAVER
    assert st.off_problem == ssm.PROBLEM_WINDOWS_NEVER
    assert st.saver_windows_wait_s == 0 and st.off_windows_wait_s == 0


def test_status_off_after_switching_off(env: Env) -> None:
    mode, api, _clk, _now, run, _t = env
    mode.apply(_on())
    run(5)
    mode.apply(ssm.Settings(enabled=False))
    st = mode.status()
    assert st.enabled is False and st.off_windows_wait_s == 120
    assert st.saver_windows_wait_s == 60


def test_status_off_reads_windows_at_most_once_a_second(env: Env) -> None:
    mode, api, _clk, now, _run, _t = env
    reads = [0]
    real = api.display_off_wait_s

    def counted() -> int:
        reads[0] += 1
        return real()

    api.display_off_wait_s = counted  # type: ignore[method-assign]
    for _ in range(20):
        mode.status()
    assert reads[0] == 1
    api.display_wait = 300
    assert mode.status().off_windows_wait_s == 120  # cached within the second
    now[0] += 1.0
    assert mode.status().off_windows_wait_s == 300
    assert reads[0] == 2


@pytest.fixture
def traced(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    lines: list[str] = []
    monkeypatch.setattr(
        ssm, "_trace", lambda text, ring=True, t=None: lines.append(text)
    )
    return lines


def _has(lines: list[str], text: str) -> bool:
    return any(text in line for line in lines)


def test_trace_settings_listener_and_countdown(env: Env, traced: list[str]) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    assert _has(
        traced,
        "settings applied: on, screen saver on (wait from Windows), "
        "power off displays on (wait from Windows)",
    )
    assert _has(traced, "listener started")
    assert _has(
        traced,
        "countdown started: screen saver 60 s (from Windows; Windows 60 s), "
        "power off displays 120 s (from Windows; Windows 120 s)",
    )
    traced.clear()
    mode.apply(_on(saver=False, off_wait=30))
    assert _has(traced, "screen saver off, power off displays on (wait 30 s)")
    assert _has(
        traced,
        "countdown started: screen saver off, "
        "power off displays 30 s (typed; Windows 120 s)",
    )
    mode.apply(ssm.Settings(enabled=False))
    assert _has(traced, "listener stopped")


def test_trace_listener_failed(
    env: Env,
    traced: list[str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mode, api, clk, _now, _run, _t = env
    clk.ok = False
    clk.error = "raw input not registered (Windows error 87)"
    monkeypatch.setattr(windows_event_hook, "enabled", True)
    with caplog.at_level("WARNING", logger="system"):
        mode.apply(_on())
    assert _has(traced, "listener failed: raw input not registered (Windows error 87)")
    assert "Windows error 87" in caplog.text
    assert _has(traced, "problem: not_listening")


def test_trace_hold_action_and_input(env: Env, traced: list[str]) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    run(10)
    api.busy = True
    run(3)
    api.busy = False
    run(1)
    assert _has(traced, "hold began: fullscreen")
    assert _has(traced, "hold ended: fullscreen")
    assert sum("hold began" in t for t in traced) == 1
    run(120)
    assert _has(traced, "action fired: power off displays: sent")
    traced.clear()
    clk.note_input()
    run(1)
    assert traced[0] == "input after action: countdown restarts"
    assert _has(traced, "countdown started")
    traced.clear()
    # Ordinary input in a running countdown is never traced.
    for _ in range(5):
        clk.note_input()
        run(1)
    assert traced == []


def test_trace_problem_changed(env: Env, traced: list[str]) -> None:
    mode, api, clk, _now, run, _t = env
    api.display_wait = 0
    mode.apply(_on())
    run(3)
    assert sum(t == "power off displays problem: windows_never" for t in traced) == 1
    assert not _has(traced, "screen saver problem")
    api.display_wait = 50
    mode.apply(_on(hold_fullscreen=False))
    assert _has(traced, "power off displays problem cleared")


def test_failed_screen_saver_start_is_logged(
    env: Env, traced: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    mode, api, clk, _now, run, _t = env
    api.start_screen_saver = lambda path: False  # type: ignore[method-assign]
    with caplog.at_level("WARNING", logger="system"):
        mode.apply(_on(off=False))
        run(60)
    assert _has(traced, "could not start")
    assert "could not start" in caplog.text


def test_action_exception_is_logged(
    env: Env, traced: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    mode, api, clk, _now, run, _t = env

    def boom() -> None:
        raise OSError("no displays")

    api.power_off_displays = boom  # type: ignore[method-assign]
    with caplog.at_level("ERROR", logger="system"):
        mode.apply(_off_only())
        run(120)
    assert _has(traced, "action fired: power off displays: failed (no displays)")
    assert mode.status().keeping_off is False
    assert "action failed" in caplog.text


def test_trace_helper_uses_trace_screen_saver(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import trace

    got: list[str] = []
    monkeypatch.setattr(
        trace, "screen_saver", lambda text, ring=True: got.append(text), raising=False
    )
    ssm._trace("hello")
    assert got == ["hello"]
    monkeypatch.delattr(trace, "screen_saver")
    ssm._trace("no trace function yet")  # no error


# ---- batch 3: last reset by (S18), hold program (S19), tracing (S16)

KB = 0x1001
MOUSE = 0x2002


def test_last_reset_by_device_kind_and_age(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    api.names = {KB: "Razer BlackWidow V3", MOUSE: "G502 HERO Gaming Mouse"}
    mode.apply(_on())
    st = mode.status()
    assert st.last_reset_kind == "" and st.last_reset_by == ""
    clk.note_input(source=KB, kind="keyboard")
    run(1)
    st = mode.status()
    assert st.last_reset_by == "Razer BlackWidow V3"
    assert st.last_reset_kind == "keyboard"
    assert st.last_reset_age_s == pytest.approx(1.0)
    run(4)
    assert mode.status().last_reset_age_s == pytest.approx(5.0)
    clk.note_input(source=MOUSE, kind="mouse")
    run(2)
    st = mode.status()
    assert (st.last_reset_by, st.last_reset_kind) == ("G502 HERO Gaming Mouse", "mouse")
    assert st.last_reset_age_s == pytest.approx(2.0)


def test_last_reset_by_program_input(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    clk.note_input(source=None, kind="mouse")
    run(1)
    st = mode.status()
    assert st.last_reset_kind == "program" and st.last_reset_by == ""
    assert st.program_input_per_min == 1
    assert api.name_calls == []


def test_program_input_rate_over_60_s(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.apply(_on())
    for _ in range(30):  # 30 s, 10 program inputs a second
        for _ in range(10):
            clk.note_input()
        run(1)
    assert mode.status().program_input_per_min == 300
    run(15)  # 45 s after the first: all still in the minute
    assert mode.status().program_input_per_min == 300
    run(15)  # 60 s after the first: the first second has left
    assert mode.status().program_input_per_min == 290
    run(30)  # all out of the minute
    assert mode.status().program_input_per_min == 0
    # Device input never counts as program input.
    clk.note_input(source=KB, kind="keyboard")
    run(1)
    assert mode.status().program_input_per_min == 0


def test_program_input_memory_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    c = ssm.InputClock()
    for _second in range(500):
        for _ in range(50):
            c.note_input()
        now[0] += 1.0
    assert len(c._program) <= 61
    assert c.program_input_per_min() == 59 * 50


def test_own_input_is_not_shown_or_counted(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    api.names = {KB: "Razer BlackWidow V3"}
    mode.apply(_on())
    clk.note_input(source=KB, kind="keyboard")
    run(3)
    for _ in range(20):
        clk.note_input(own=True)
    run(1)
    st = mode.status()
    assert st.last_reset_kind == "keyboard"
    assert st.last_reset_by == "Razer BlackWidow V3"
    assert st.last_reset_age_s == pytest.approx(4.0)
    assert st.program_input_per_min == 0


def test_device_name_looked_up_once_per_handle(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    api.names = {KB: "Razer BlackWidow V3", MOUSE: "G502"}
    mode.apply(_on())
    for i in range(50):
        clk.note_input(source=MOUSE, kind="mouse")
        clk.note_input(source=KB if i % 2 else MOUSE, kind="keyboard")
        run(1)
        mode.status()
    assert sorted(api.name_calls) == [KB, MOUSE]


def test_unnamed_device_is_looked_up_once_too(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    for _ in range(10):
        clk.note_input(source=KB, kind="keyboard")
        run(1)
    assert api.name_calls == [KB]
    assert mode.status().last_reset_by == ""
    assert mode.status().last_reset_kind == "keyboard"


def test_hold_program_named_for_fullscreen(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    api.busy = True
    api.foreground = "StarCitizen.exe"
    run(2)
    st = mode.status()
    assert st.hold == "fullscreen" and st.hold_program == "StarCitizen.exe"
    api.busy = False
    run(1)
    assert mode.status().hold_program == ""
    # Other holds don't name a program.
    api.display_flag = True
    run(1)
    assert mode.status().hold == "display_request"
    assert mode.status().hold_program == ""


def test_hold_program_unknown_is_empty(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    api.busy = True

    def fails() -> str:
        raise OSError("access denied")

    api.foreground_program = fails  # type: ignore[method-assign]
    run(2)
    st = mode.status()
    assert st.hold == "fullscreen" and st.hold_program == ""


def test_trace_reset_source_on_change_only(env: Env, traced: list[str]) -> None:
    mode, api, clk, _now, run, _t = env
    api.names = {KB: "Razer BlackWidow V3", MOUSE: "G502"}
    mode.apply(_on())
    traced.clear()
    for _ in range(10):
        clk.note_input(source=KB, kind="keyboard")
        run(1)
    assert traced == ["last reset by: Razer BlackWidow V3 (keyboard)"]
    for _ in range(5):
        clk.note_input()
        run(1)
    clk.note_input(source=MOUSE, kind="mouse")
    run(3)
    assert traced == [
        "last reset by: Razer BlackWidow V3 (keyboard)",
        "last reset by: input sent by a program",
        "last reset by: G502 (mouse)",
    ]


def test_trace_hold_program_when_hold_begins(env: Env, traced: list[str]) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    api.busy = True
    api.foreground = "StarCitizen.exe"
    run(5)
    assert sum("hold began: fullscreen (StarCitizen.exe)" == t for t in traced) == 1
    assert not _has(traced, "hold program:")
    api.foreground = "vlc.exe"
    run(3)
    assert sum(t == "hold program: vlc.exe" for t in traced) == 1


def test_window_proc_passes_device_and_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    c = ssm.InputClock()
    got: list[tuple[bool, Any, str, bool]] = []
    monkeypatch.setattr(
        c,
        "note_input",
        lambda own=False, source=None, kind="", press=False: got.append(
            (own, source, kind, press)
        ),
    )
    frames = [_raw(1, 0), _raw(0, 0), _raw(0, windows_event_hook.OWN_KEY_MARK)]
    frames[0].header.hDevice = KB
    frames[1].header.hDevice = None  # sent by a program

    class FakeUser32:
        def __init__(self) -> None:
            self.raw = frames[0]

        def GetRawInputData(
            self, l_param: int, cmd: int, buf: object, size: object, hs: int
        ) -> int:
            ctypes.memmove(buf, ctypes.byref(self.raw), ctypes.sizeof(self.raw))
            return ctypes.sizeof(self.raw)

        def DefWindowProcW(self, *args: object) -> int:
            return 0

    fake = FakeUser32()
    c._user32 = fake
    for raw in frames:
        fake.raw = raw
        c._window_proc(0, 0x00FF, 0, 1)
    # The keyboard frame is a key down; the mouse frames only move.
    assert got == [
        (False, KB, "keyboard", True),
        (False, None, "mouse", False),
        (True, None, "mouse", False),
    ]


def test_device_path_helpers() -> None:
    b = "\\"
    path = b * 2 + "?" + b + "HID#VID_046d&PID_C08B&MI_00#d&24e7354&0&0000#{378de44c}"
    assert ssm.instance_id_from_path(path) == (
        "HID" + b + "VID_046d&PID_C08B&MI_00" + b + "d&24e7354&0&0000"
    )
    assert ssm.vid_pid_text(path) == "VID_046D PID_C08B"
    assert ssm.vid_pid_text("ROOT#RDP_KBD#0000") == ""


# --- power off: one request, to the listener's own window (found 2026-11-15)


class _FakeUser32:
    def __init__(self) -> None:
        self.posted: list[tuple[int, int, int, int]] = []

        class _Fn:
            argtypes: object = None
            restype: object = None

            def __call__(_self, hwnd: int, msg: int, w: int, lp: int) -> int:  # noqa: N805
                self.posted.append((hwnd, msg, w, lp))
                return 1

        self.PostMessageW = _Fn()


def test_power_off_goes_to_the_listener_window_not_every_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broadcast reaches every window, Gremlin's own Qt windows too, and
    each asks Windows to power off again: on the user's PC the main thread
    froze 35 s and the screens kept going off. One post, to one window."""
    fake = _FakeUser32()
    monkeypatch.setattr(ssm.ctypes, "WinDLL", lambda *a, **k: fake)
    monkeypatch.setattr(ssm, "_power_window", 4242)
    ssm.WindowsApi().power_off_displays()
    assert fake.posted == [(4242, 0x0112, 0xF170, 2)]
    assert all(p[0] != 0xFFFF for p in fake.posted)


def test_power_off_with_no_listener_window_sends_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeUser32()
    monkeypatch.setattr(ssm.ctypes, "WinDLL", lambda *a, **k: fake)
    monkeypatch.setattr(ssm, "_power_window", 0)
    with pytest.raises(RuntimeError):
        ssm.WindowsApi().power_off_displays()
    assert fake.posted == []


# ---- batch 4: two timers (S4, S5, S8), keeping the displays off (S6, S20)


def test_settings_and_status_shapes() -> None:
    assert not hasattr(ssm, "ACTION_SCREEN_SAVER")
    assert not hasattr(ssm, "ACTION_POWER_OFF")
    s = ssm.Settings()
    assert (s.enabled, s.screen_saver_on, s.screen_saver_wait_s) == (False, True, 0)
    assert (s.power_off_on, s.power_off_wait_s, s.hold_fullscreen) == (True, 0, True)
    fields = set(ssm.Status.__dataclass_fields__)
    for name in (
        "saver_wait_s",
        "saver_windows_wait_s",
        "saver_from_windows",
        "saver_fired",
        "saver_remaining_s",
        "saver_problem",
        "off_wait_s",
        "off_windows_wait_s",
        "off_from_windows",
        "off_fired",
        "off_remaining_s",
        "off_problem",
        "keeping_off",
        "wakes",
    ):
        assert name in fields
    for gone in (
        "wait_s",
        "windows_wait_s",
        "wait_from_windows",
        "fired",
        "remaining_s",
    ):
        assert gone not in fields
    assert ssm.POWER_OFF_GAP_S == 1.0
    assert ssm.ScreenSaverMode.POWER_OFF_GAP_S == 1.0


def test_both_timers_fire_in_order_once_per_idle_period(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    st = mode.status()
    assert st.saver_remaining_s == pytest.approx(60)
    assert st.off_remaining_s == pytest.approx(120)
    run(59)
    assert api.actions == 0
    run(1)
    assert api.started == [api.path] and api.powered_off == 0
    st = mode.status()
    assert st.saver_fired and not st.off_fired
    assert st.saver_remaining_s == 0 and st.off_remaining_s == pytest.approx(60)
    run(59)
    assert api.powered_off == 0
    run(1)
    assert api.powered_off == 1
    run(1000)
    assert len(api.started) == 1 and api.powered_off == 1
    st = mode.status()
    assert st.saver_fired and st.off_fired
    clk.note_input()
    run(60)
    assert len(api.started) == 2 and api.powered_off == 1
    run(60)
    assert api.powered_off == 2


def test_each_timer_has_its_own_typed_or_windows_wait(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on(saver_wait=10))
    st = mode.status()
    assert (st.saver_wait_s, st.saver_windows_wait_s, st.saver_from_windows) == (
        10,
        60,
        False,
    )
    assert (st.off_wait_s, st.off_windows_wait_s, st.off_from_windows) == (
        120,
        120,
        True,
    )
    run(10)
    assert len(api.started) == 1
    # Windows' screen saver wait changes: only the typed row ignores it.
    api.saver_wait = 600
    api.display_wait = 30
    clk.note_input()
    run(1)
    st = mode.status()
    assert (st.saver_wait_s, st.saver_windows_wait_s) == (10, 600)
    assert (st.off_wait_s, st.off_windows_wait_s) == (30, 30)
    # Cleared: Windows' time again.
    mode.apply(_on(off_wait=5))
    st = mode.status()
    assert st.saver_wait_s == 600 and st.saver_from_windows
    assert st.off_wait_s == 5 and not st.off_from_windows


def test_windows_never_on_the_screen_saver_row(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    api.saver_wait = 0
    mode.apply(_on())
    run(200)
    assert api.started == [] and api.powered_off == 1
    assert mode.status().saver_problem == ssm.PROBLEM_WINDOWS_NEVER
    mode.apply(_on(saver_wait=15))  # a typed time fixes it
    assert mode.status().saver_problem == ""


def test_a_switched_off_timer_never_fires(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on(saver=False))
    run(500)
    assert api.started == [] and api.powered_off == 1
    assert mode.status().saver_remaining_s == 0
    mode.apply(_on(off=False))
    clk.note_input()
    run(500)
    assert len(api.started) == 1 and api.powered_off == 1
    assert mode.status().off_remaining_s == 0


def _keep_off(env: Env) -> None:
    """Power off fired, keep-off started (t = 1120)."""
    mode, api, _clk, _now, run, _t = env
    mode.apply(_off_only())
    run(120)
    assert api.powered_off == 1
    assert mode.status().keeping_off is True


def test_keep_off_answers_display_on_with_one_power_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    mode.on_display_state(False)  # Windows: off
    now[0] += 1.5
    mode.on_display_state(True)  # woken without input
    assert api.powered_off == 2
    assert mode.status().wakes == 1
    mode.on_display_state(False)
    now[0] += 2.0
    mode.on_display_state(True)
    assert api.powered_off == 3
    st = mode.status()
    assert st.wakes == 2 and st.keeping_off


def test_keep_off_respects_the_gap_and_retries_after_it(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    # Woken 0.2 s after the power-off: inside the 1 s gap, nothing now.
    now[0] += 0.2
    mode.on_display_state(True)
    now[0] += 0.1
    mode.on_display_state(True)
    assert api.powered_off == 1
    assert mode.status().wakes == 0
    # The tick after the gap sends exactly one.
    now[0] += 0.8
    mode.tick()
    assert api.powered_off == 2
    assert mode.status().wakes == 1
    now[0] += 1.0
    mode.tick()
    assert api.powered_off == 2  # no ON report since: nothing more


def test_held_back_resend_goes_out_from_the_timer_without_a_tick(
    env: Env,
) -> None:
    """The main thread is stuck (tick never runs): the re-send held back by
    the gap still goes out, from the listener thread's timer (S6, S20)."""
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    now[0] += 0.2
    mode.on_display_state(True)  # inside the gap: a timer is asked for
    assert len(clk.armed) == 1 and clk.armed[0] == pytest.approx(0.8)
    now[0] += 0.1
    mode.on_display_state(True)  # a second report: no second timer
    assert len(clk.armed) == 1
    # The timer fires early: nothing sent, asks for the rest of the wait.
    assert mode.on_retry_timer() == pytest.approx(0.7)
    assert api.powered_off == 1
    now[0] += 0.7
    assert mode.on_retry_timer() is None  # gap ended: sent, no tick
    assert api.powered_off == 2
    assert mode.status().wakes == 1
    assert mode.on_retry_timer() is None  # nothing pending: nothing more
    assert api.powered_off == 2


def test_timer_resend_is_at_most_once_a_second(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    now[0] += 0.2
    mode.on_display_state(True)
    now[0] += 0.8
    mode.on_retry_timer()
    assert api.powered_off == 2
    now[0] += 0.3  # another report 0.3 s after the re-send: held back again
    mode.on_display_state(True)
    assert api.powered_off == 2 and len(clk.armed) == 2
    now[0] += 0.7
    mode.on_retry_timer()
    assert api.powered_off == 3 and mode.status().wakes == 2


def test_timer_resend_dropped_on_input_or_display_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    now[0] += 0.2
    mode.on_display_state(True)
    clk.note_input()  # a person woke it
    now[0] += 0.9
    assert mode.on_retry_timer() is None
    assert api.powered_off == 1 and mode.status().wakes == 0


def test_timer_resend_trace_carries_the_send_time(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode, api, clk, now, run, _t = env
    seen: list[tuple[str, float | None]] = []
    monkeypatch.setattr(
        ssm, "_trace", lambda text, ring=True, t=None: seen.append((text, t))
    )
    wall = [5000.0]
    monkeypatch.setattr(clock, "now", lambda: wall[0])
    _keep_off(env)
    now[0] += 0.2
    wall[0] = 5000.2
    mode.on_display_state(True)
    now[0] += 0.8
    wall[0] = 5001.0
    mode.on_retry_timer()  # the send happens here, on the "listener"
    wall[0] = 5030.0  # the main thread drains much later
    seen.clear()
    mode.tick()
    sent = [t for text, t in seen if "power off sent again (#1)" in text]
    waited = [t for text, t in seen if "sent again when the gap ends" in text]
    assert sent == [5001.0]
    assert waited == [5000.2]


def test_window_proc_timer_kills_it_and_sends(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    now[0] += 0.2
    mode.on_display_state(True)
    killed: list[int] = []

    class _U:
        def KillTimer(self, hwnd: int, ident: int) -> bool:
            killed.append(ident)
            return True

    clk._user32 = _U()
    now[0] += 0.8
    assert clk._window_proc(1, ssm._WM_TIMER, ssm._RETRY_TIMER_ID, 0) == 0
    assert killed == [ssm._RETRY_TIMER_ID]
    assert api.powered_off == 2


def test_keep_off_retry_dropped_when_windows_reports_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    now[0] += 0.2
    mode.on_display_state(True)
    now[0] += 0.1
    mode.on_display_state(False)  # went off by itself
    run(3)
    assert api.powered_off == 1 and mode.status().wakes == 0


def test_keep_off_stops_on_input(env: Env, caplog: pytest.LogCaptureFixture) -> None:
    mode, api, clk, now, run, _t = env
    caplog.set_level("INFO", logger="system")
    _keep_off(env)
    now[0] += 2.0
    mode.on_display_state(True)
    assert api.powered_off == 2
    clk.note_input(source=0x1001, kind="keyboard")
    # Before the tick sees the input: the display a person woke stays on.
    now[0] += 2.0
    mode.on_display_state(True)
    assert api.powered_off == 2
    run(1)
    st = mode.status()
    assert st.keeping_off is False
    assert st.wakes == 1  # the last idle period's count stays shown (S20)
    msgs = [r.getMessage() for r in caplog.records]
    assert sum("stopped keeping the displays off" in m for m in msgs) == 1
    assert any("back on 1 times" in m for m in msgs)
    now[0] += 5.0
    mode.on_display_state(True)
    run(5)
    assert api.powered_off == 2


def test_keep_off_ignores_gremlins_own_input(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    for _ in range(10):
        clk.note_input(own=True)
    run(2)
    assert mode.status().keeping_off is True
    mode.on_display_state(True)
    assert api.powered_off == 2


def test_keep_off_stops_when_switched_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    mode.apply(ssm.Settings(enabled=False))
    now[0] += 5.0
    mode.on_display_state(True)
    assert api.powered_off == 1
    assert mode.status().keeping_off is False


def test_keep_off_stops_when_power_off_row_switched_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    mode.apply(_on(off=False))
    now[0] += 5.0
    mode.on_display_state(True)
    assert api.powered_off == 1
    assert mode.status().keeping_off is False


def test_display_on_without_keep_off_does_nothing(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.apply(_off_only())
    run(10)
    mode.on_display_state(True)
    mode.on_display_state(False)
    mode.on_display_state(True)
    run(1)
    assert api.powered_off == 0
    st = mode.status()
    assert st.keeping_off is False and st.wakes == 0


def test_screen_saver_alone_does_not_keep_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.apply(_on(off=False))
    run(60)
    assert len(api.started) == 1
    now[0] += 2.0
    mode.on_display_state(True)
    assert api.powered_off == 0 and mode.status().keeping_off is False


def test_wakes_restart_with_the_next_keep_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    for _ in range(3):
        now[0] += 1.5
        mode.on_display_state(True)
    assert mode.status().wakes == 3
    clk.note_input()
    run(119)
    assert mode.status().wakes == 3  # last idle period's, until the next
    run(1)
    st = mode.status()
    assert st.keeping_off is True and st.wakes == 0


def test_timer_power_off_also_respects_the_gap(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.apply(_off_only(off_wait=5))
    run(4)
    mode._last_power_off = now[0] + 0.5  # a re-send moments before the wait ends
    run(1)
    assert api.powered_off == 0 and mode.status().off_fired is False
    run(1)
    assert api.powered_off == 1 and mode.status().off_fired is True


def test_power_off_is_logged(env: Env, caplog: pytest.LogCaptureFixture) -> None:
    mode, api, clk, _now, run, _t = env
    caplog.set_level("INFO", logger="system")
    _keep_off(env)
    assert any("displays powered off" in r.getMessage() for r in caplog.records)


def test_trace_each_resend_and_the_end(env: Env, traced: list[str]) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)
    assert _has(traced, "keep off started")
    traced.clear()
    now[0] += 0.3
    mode.on_display_state(True)  # inside the gap
    assert traced == []  # nothing traced on the listener thread
    run(1)
    assert _has(traced, "sent again when the gap ends")
    assert _has(traced, "power off sent again (#1)")
    now[0] += 1.5
    mode.on_display_state(True)
    run(1)
    assert _has(traced, "power off sent again (#2)")
    clk.note_input()
    run(1)
    assert _has(traced, "keep off ended: keyboard or mouse input; 2 wakes")


def test_failed_resend_is_logged(
    env: Env, traced: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    mode, api, clk, now, run, _t = env
    _keep_off(env)

    def boom() -> None:
        raise OSError("no window")

    api.power_off_displays = boom  # type: ignore[method-assign]
    now[0] += 2.0
    with caplog.at_level("WARNING", logger="system"):
        mode.on_display_state(True)
        run(1)
    assert "keep off power off #1 failed (no window)" in caplog.text
    assert _has(traced, "keep off: power off #1 failed")


def test_notify_failure_is_reported(
    env: Env, traced: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    mode, api, clk, _now, run, _t = env
    clk.notify_error = "display state notification not registered (Windows error 5)"
    with caplog.at_level("WARNING", logger="system"):
        mode.apply(_on())
    assert "the displays can't be kept off" in caplog.text
    assert _has(traced, "Windows error 5")


def test_clock_hands_display_state_to_the_mode(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    assert clk.display_state_handler == mode.on_display_state


def _setting(guid: str, value: int) -> ssm.POWERBROADCAST_SETTING:
    s = ssm.POWERBROADCAST_SETTING()
    s.PowerSetting = ssm._GUID.parse(guid)
    s.DataLength = 4
    s.Data[0] = value
    return s


def test_window_proc_hands_the_display_state_on() -> None:
    c = ssm.InputClock()
    got: list[bool] = []
    c.display_state_handler = got.append

    class FakeUser32:
        def DefWindowProcW(self, *args: object) -> int:
            return 1

    c._user32 = FakeUser32()
    display = "6FE69556-704A-47A0-8F24-C28D936FDA47"
    for value in (1, 0, 2):
        s = _setting(display, value)
        c._window_proc(0, 0x0218, 0x8013, ctypes.addressof(s))
    other = _setting("7516b95f-f776-4464-8c53-06167f40cc99", 1)
    c._window_proc(0, 0x0218, 0x8013, ctypes.addressof(other))
    c._window_proc(0, 0x0218, 0x000A, ctypes.addressof(_setting(display, 1)))
    assert got == [True, False, True]  # dimmed counts as on


def test_input_clock_never_registers_power_notifications_in_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []
    monkeypatch.setattr(ssm, "_user32", lambda: called.append("user32"))
    c = ssm.InputClock()
    assert c.start() is False
    assert called == []


def test_screen_saver_in_front_does_not_hold_the_power_off_timer(env: Env) -> None:
    """Found on the user's PC (2026-11-15): with the screen saver running,
    Windows reports "busy" (a full-screen program) and the screen saver is in
    front; the power-off timer must still fire behind it (S6, S7)."""
    mode, api, _clk, _now, run, _t = env
    mode.apply(ssm.Settings(True))  # both timers: screen saver 60 s, power off 120 s
    run(60)
    assert api.started  # the screen saver started
    api.busy = True
    api.foreground = "scrnsave.scr"
    run(61)
    assert api.powered_off == 1
    assert mode.status().hold == ""


def test_screen_saver_behind_another_window_does_not_hold_the_power_off(
    env: Env,
) -> None:
    """Found on the user's PC (2026-11-16, a TV as a second display): the
    screen saver runs, Windows reports "busy", but the program in front stays
    claude.exe; the power-off timer must still fire (S6, S7)."""
    mode, api, _clk, _now, run, _t = env
    mode.apply(ssm.Settings(True))  # both timers: screen saver 60 s, power off 120 s
    run(60)
    assert api.started
    api.busy = True
    api.saver_running = True
    api.foreground = "claude.exe"
    run(61)
    assert api.powered_off == 1
    assert mode.status().hold == ""


def test_a_failing_screen_saver_check_falls_back_to_the_window_in_front(
    env: Env,
) -> None:
    mode, api, _clk, _now, run, _t = env

    def fails() -> bool:
        raise OSError("no answer")

    api.screen_saver_running = fails  # type: ignore[method-assign]
    mode.apply(ssm.Settings(True))
    api.busy = True
    api.foreground = "StarCitizen.exe"
    run(200)
    assert api.powered_off == 0
    assert mode.status().hold == ssm.HOLD_FULLSCREEN


def test_a_real_full_screen_program_still_holds_the_power_off(env: Env) -> None:
    mode, api, _clk, _now, run, _t = env
    mode.apply(ssm.Settings(True))
    api.busy = True
    api.foreground = "StarCitizen.exe"
    run(200)
    assert api.powered_off == 0 and not api.started
    assert mode.status().hold == ssm.HOLD_FULLSCREEN


# ----- device hooks (S21, S23; contract-5 "Core hooks")


def _hooks(mode: ssm.ScreenSaverMode, api: FakeApi) -> list[str]:
    """Records each hook call and the power-offs sent before it."""
    calls: list[str] = []
    mode.set_device_hooks(
        lambda: calls.append(f"before:{api.powered_off}"),
        lambda: calls.append(f"after:{api.powered_off}"),
    )
    return calls


def test_before_power_off_runs_just_before_the_first_power_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    calls = _hooks(mode, api)
    mode.apply(_off_only())
    run(119)
    assert calls == []
    run(1)
    # Called with no power-off sent yet; the power-off follows at once.
    assert calls == ["before:0"] and api.powered_off == 1


def test_before_power_off_once_per_idle_period_not_for_resends(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    calls = _hooks(mode, api)
    mode.apply(_off_only())
    run(120)
    for _ in range(3):
        now[0] += 1.5
        mode.on_display_state(True)
    now[0] += 0.2
    mode.on_display_state(True)  # inside the gap: retried by the tick
    run(5)
    assert api.powered_off == 5
    assert calls == ["before:0"]
    clk.note_input(source=0x1001, kind="mouse")
    run(120)
    assert calls == ["before:0", "after:5", "before:5"]


def test_after_input_once_at_the_input_that_ends_keep_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    calls = _hooks(mode, api)
    mode.apply(_off_only())
    run(120)
    clk.note_input(source=0x1001, kind="keyboard")
    run(1)
    assert calls == ["before:0", "after:1"]
    assert mode.status().keeping_off is False
    for _ in range(5):
        clk.note_input(source=0x1001, kind="keyboard")
        run(1)
    assert calls == ["before:0", "after:1"]


def test_after_input_not_for_gremlins_own_input(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    calls = _hooks(mode, api)
    mode.apply(_off_only())
    run(120)
    for _ in range(10):
        clk.note_input(own=True)
        run(1)
    assert calls == ["before:0"]
    assert mode.status().keeping_off is True


def test_hooks_not_called_without_the_power_off_timer(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    calls = _hooks(mode, api)
    # Input before the wait, the screen saver alone, then the mode off.
    mode.apply(_off_only())
    run(60)
    clk.note_input(source=0x1001, kind="mouse")
    run(60)
    mode.apply(_on(off=False))
    run(200)
    clk.note_input(source=0x1001, kind="mouse")
    run(1)
    assert len(api.started) == 1
    mode.apply(ssm.Settings(enabled=False))
    run(500)
    mode.tick()
    assert calls == [] and api.powered_off == 0


def test_hooks_not_called_while_the_mode_is_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    calls = _hooks(mode, api)
    mode.apply(_off_only())
    run(120)
    mode.apply(ssm.Settings(enabled=False))
    clk.note_input(source=0x1001, kind="mouse")
    run(300)
    assert calls == ["before:0"]


def test_hook_held_back_by_the_gap_runs_with_the_power_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    calls = _hooks(mode, api)
    mode.apply(_off_only(off_wait=5))
    run(4)
    mode._last_power_off = now[0] + 0.5
    run(1)
    assert calls == [] and api.powered_off == 0
    run(1)
    assert calls == ["before:0"] and api.powered_off == 1


def test_hook_exceptions_are_logged_and_the_power_off_still_sent(
    env: Env, caplog: pytest.LogCaptureFixture
) -> None:
    mode, api, clk, now, run, _t = env
    caplog.set_level("INFO", logger="system")

    def boom() -> None:
        raise RuntimeError("helper gone")

    mode.set_device_hooks(boom, boom)
    mode.apply(_off_only())
    run(120)
    assert api.powered_off == 1 and mode.status().keeping_off is True
    clk.note_input(source=0x1001, kind="keyboard")
    run(1)
    assert mode.status().keeping_off is False
    failed = [
        r
        for r in caplog.records
        if r.name == "system" and "device hook" in r.getMessage()
    ]
    assert len(failed) == 2 and all(r.exc_info for r in failed)


def test_none_hooks_are_fine(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.set_device_hooks(None, None)
    mode.apply(_off_only())
    run(120)
    clk.note_input(source=0x1001, kind="keyboard")
    run(120)
    assert api.powered_off == 2


def test_hooks_are_traced(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    mode, api, clk, now, run, _t = env
    lines: list[str] = []
    monkeypatch.setattr(
        ssm.trace,
        "screen_saver",
        lambda text, ring=True: lines.append(text),
        raising=False,
    )
    _hooks(mode, api)
    mode.apply(_off_only())
    run(120)
    clk.note_input(source=0x1001, kind="keyboard")
    run(1)
    hook_lines = [x for x in lines if "device hook" in x]
    assert hook_lines == ["device hook: before power off", "device hook: after input"]
    assert lines.index("device hook: before power off") < lines.index(
        "action fired: power off displays: sent"
    )


# ----- S21: the devices are switched off first, the power-off waits for them


class _Devices:
    """A fake disabler: busy until done() (the hook's probe reads it)."""

    def __init__(self, count: int = 2) -> None:
        self.count = count
        self.busy = True
        self.starts = 0

    def hook(self) -> tuple[int, Callable[[], bool]]:
        self.starts += 1
        return self.count, lambda: self.busy


def _traced(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    lines: list[str] = []
    monkeypatch.setattr(
        ssm.trace,
        "screen_saver",
        lambda text, ring=True, t=None: lines.append(text),
        raising=False,
    )
    return lines


def test_s21_power_off_waits_until_the_devices_are_done(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode, api, clk, now, run, _t = env
    lines = _traced(monkeypatch)
    dev = _Devices(2)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(_off_only())
    run(120)
    assert dev.starts == 1 and api.powered_off == 0
    assert "switching devices off first (2)" in lines
    assert not mode.status().keeping_off
    run(5)
    assert api.powered_off == 0
    dev.busy = False
    run(1)
    assert api.powered_off == 1 and mode.status().keeping_off
    assert any(x.startswith("devices switched off in ") for x in lines)
    assert lines.index("switching devices off first (2)") < lines.index(
        "action fired: power off displays: sent"
    )
    run(30)
    assert api.powered_off == 1 and dev.starts == 1


def test_s21_power_off_sent_after_ten_seconds_when_never_done(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode, api, clk, now, run, _t = env
    lines = _traced(monkeypatch)
    dev = _Devices(1)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(_off_only())
    run(120)
    run(9)
    assert api.powered_off == 0
    run(1)
    assert api.powered_off == 1
    assert (
        "devices still being switched off after 10 s: power off sent" in lines
    )


def test_s21_input_during_the_wait_cancels_the_power_off(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode, api, clk, now, run, _t = env
    _traced(monkeypatch)
    dev = _Devices(1)
    calls: list[str] = []
    mode.set_device_hooks(dev.hook, lambda: calls.append("after"))
    mode.apply(_off_only())
    run(120)
    clk.note_input(source=0x1001, kind="keyboard")
    run(1)
    assert calls == ["after"]  # S23: the devices are enabled again
    dev.busy = False
    run(15)
    assert api.powered_off == 0 and not mode.status().keeping_off


def test_s21_nothing_to_wait_for_powers_off_at_once(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.set_device_hooks(lambda: None, None)  # no devices / no helper
    mode.apply(_off_only())
    run(120)
    assert api.powered_off == 1
    mode2_done = _Devices(1)
    mode2_done.busy = False  # already done when asked
    mode.set_device_hooks(mode2_done.hook, None)
    clk.note_input(source=0x1001, kind="keyboard")
    run(120)
    assert api.powered_off == 2


# --- Wake PC (S3, S28-S31): only ticked keyboards and mice count


KB_ID = "USB\\VID_1532&PID_024E\\5&1"
MOUSE_ID = "USB\\VID_046D&PID_C08B\\6&2"


def _wake_env(env: Env) -> Env:
    _mode, api, _clk, _now, _run, _t = env
    api.physical = {KB: KB_ID, MOUSE: MOUSE_ID}
    api.names = {KB: "Razer BlackWidow V3", MOUSE: "G502 HERO Gaming Mouse"}
    return env


def test_unticked_device_input_does_not_count(env: Env) -> None:
    mode, api, clk, _now, run, _t = _wake_env(env)
    mode.set_wake_devices([KB_ID.lower()])  # ids compare upper-case
    mode.apply(_on(saver_wait=30, off=False))
    run(20)
    clk.note_input(source=MOUSE, kind="mouse")
    run(1)
    st = mode.status()
    assert st.idle_s == pytest.approx(21)
    assert st.last_reset_kind == ""
    run(9)
    assert api.started  # the mouse never restarted the countdown
    clk.note_input(source=KB, kind="keyboard")
    run(1)
    st = mode.status()
    assert st.idle_s == pytest.approx(1)
    assert (st.last_reset_by, st.last_reset_kind) == ("Razer BlackWidow V3", "keyboard")


def test_program_input_always_counts_with_a_wake_list(env: Env) -> None:
    mode, _api, clk, _now, run, _t = _wake_env(env)
    mode.set_wake_devices([KB_ID])
    mode.apply(_on())
    run(20)
    clk.note_input(source=None, kind="mouse")
    run(1)
    st = mode.status()
    assert st.idle_s == pytest.approx(1)
    assert st.last_reset_kind == "program"


def test_unticked_input_does_not_end_keep_off_or_call_after_input(env: Env) -> None:
    mode, api, clk, _now, run, _t = _wake_env(env)
    calls: list[str] = []
    mode.set_device_hooks(lambda: calls.append("before"), lambda: calls.append("after"))
    mode.set_wake_devices([KB_ID])
    mode.apply(_off_only())
    run(120)
    assert api.powered_off == 1 and mode.status().keeping_off
    clk.note_input(source=MOUSE, kind="mouse")
    run(2)
    assert calls == ["before"]
    assert mode.status().keeping_off
    clk.note_input(source=KB, kind="keyboard")
    run(1)
    assert calls == ["before", "after"]
    assert not mode.status().keeping_off


def test_nothing_ticked_holds_both_timers(env: Env) -> None:
    mode, api, clk, _now, run, _t = _wake_env(env)
    mode.set_wake_devices([])
    mode.apply(_on())
    run(300)
    assert api.actions == 0
    st = mode.status()
    assert st.hold == ssm.HOLD_NO_WAKE_DEVICE
    assert st.saver_remaining_s == 0 and st.off_remaining_s == 0
    # Locked is checked first.
    api.is_locked = True
    run(1)
    assert mode.status().hold == ssm.HOLD_LOCKED
    api.is_locked = False
    mode.set_wake_devices([KB_ID])
    run(1)
    assert mode.status().hold == ""
    run(60)
    assert api.started


def test_no_wake_list_yet_counts_every_device(env: Env) -> None:
    mode, api, clk, _now, run, _t = _wake_env(env)
    mode.apply(_on())
    run(20)
    clk.note_input(source=MOUSE, kind="mouse")
    run(1)
    assert mode.status().idle_s == pytest.approx(1)
    assert mode.status().hold == ""
    assert api.physical_calls == []  # no list, no listener: no lookup


def test_physical_id_looked_up_once_per_handle(env: Env) -> None:
    mode, api, clk, _now, run, _t = _wake_env(env)
    mode.set_wake_devices([KB_ID])
    mode.apply(_on())
    for _ in range(50):
        clk.note_input(source=KB, kind="keyboard")
        clk.note_input(source=MOUSE, kind="mouse")
    clk.note_input(source=None, kind="mouse")
    assert api.physical_calls == [KB, MOUSE]


def test_physical_id_lookup_failure_is_not_counted(env: Env) -> None:
    mode, api, clk, _now, run, _t = _wake_env(env)

    def broken(handle: int) -> str:
        raise OSError("gone")

    clk.physical_id_of = broken
    mode.set_wake_devices([KB_ID])
    mode.apply(_on())
    run(20)
    clk.note_input(source=KB, kind="keyboard")
    run(1)
    assert mode.status().idle_s == pytest.approx(21)


def test_presses_reach_the_listener_on_the_main_thread(env: Env) -> None:
    mode, _api, clk, _now, _run, timers = _wake_env(env)
    got: list[tuple[str, str]] = []
    mode.set_press_listener(lambda i, k: got.append((i, k)))
    assert mode.start_detection() is True
    assert clk.started == 1
    assert "screen saver mode presses" in timers
    clk.note_input(source=KB, kind="keyboard", press=True)
    clk.note_input(source=MOUSE, kind="mouse", press=True)
    assert got == []  # never called on the listener thread
    mode._on_drain_timer()
    assert got == [(KB_ID, "keyboard"), (MOUSE_ID, "mouse")]


def test_moves_wheel_and_key_up_are_not_presses(env: Env) -> None:
    mode, _api, clk, _now, _run, _t = _wake_env(env)
    got: list[tuple[str, str]] = []
    mode.set_press_listener(lambda i, k: got.append((i, k)))
    mode.start_detection()
    clk.note_input(source=MOUSE, kind="mouse")
    clk.note_input(source=KB, kind="keyboard")
    clk.note_input(source=None, kind="keyboard", press=True)  # a program
    mode._on_drain_timer()
    assert got == []


def test_presses_reported_once_a_second_per_device_and_kind(env: Env) -> None:
    mode, _api, clk, now, _run, _t = _wake_env(env)
    got: list[tuple[str, str]] = []
    mode.set_press_listener(lambda i, k: got.append((i, k)))
    mode.start_detection()
    for _ in range(5):
        clk.note_input(source=KB, kind="keyboard", press=True)
    clk.note_input(source=KB, kind="mouse", press=True)
    now[0] += 0.5
    clk.note_input(source=KB, kind="keyboard", press=True)
    now[0] += 0.5
    clk.note_input(source=KB, kind="keyboard", press=True)
    mode._on_drain_timer()
    assert got == [(KB_ID, "keyboard"), (KB_ID, "mouse"), (KB_ID, "keyboard")]


def test_press_from_an_unticked_device_is_reported_but_not_counted(env: Env) -> None:
    mode, _api, clk, _now, run, _t = _wake_env(env)
    got: list[tuple[str, str]] = []
    mode.set_wake_devices([])
    mode.set_press_listener(lambda i, k: got.append((i, k)))
    mode.apply(_on())
    run(20)
    clk.note_input(source=MOUSE, kind="mouse", press=True)
    run(1)  # the tick drains while the mode is on
    assert got == [(MOUSE_ID, "mouse")]
    assert mode.status().idle_s == pytest.approx(21)


def test_no_press_listener_reports_nothing(env: Env) -> None:
    mode, api, clk, _now, _run, timers = _wake_env(env)
    got: list[tuple[str, str]] = []
    mode.set_press_listener(lambda i, k: got.append((i, k)))
    mode.set_press_listener(None)
    mode.start_detection()
    clk.note_input(source=KB, kind="keyboard", press=True)
    mode._on_drain_timer()
    assert got == []
    assert api.physical_calls == []


def test_activity_reaches_the_listener_on_the_main_thread(env: Env) -> None:
    mode, _api, clk, _now, _run, timers = _wake_env(env)
    got: list[str] = []
    mode.set_activity_listener(got.append)
    assert mode.start_detection() is True
    assert "screen saver mode presses" in timers  # drained while off
    clk.note_input(source=MOUSE, kind="mouse")  # movement, no press
    clk.note_input(source=KB, kind="keyboard")  # key up
    assert got == []  # never called on the listener thread
    mode._on_drain_timer()
    assert got == [MOUSE_ID, KB_ID]


def test_activity_from_ticked_and_unticked_devices(env: Env) -> None:
    mode, _api, clk, _now, run, _t = _wake_env(env)
    got: list[str] = []
    mode.set_wake_devices([KB_ID])
    mode.set_activity_listener(got.append)
    mode.apply(_on())
    run(20)
    clk.note_input(source=MOUSE, kind="mouse")
    clk.note_input(source=KB, kind="keyboard", press=True)
    run(1)  # the tick drains while the mode is on
    assert got == [MOUSE_ID, KB_ID]


def test_activity_once_per_device_every_half_second(env: Env) -> None:
    mode, _api, clk, now, _run, _t = _wake_env(env)
    got: list[str] = []
    mode.set_activity_listener(got.append)
    mode.start_detection()
    for _ in range(5):
        clk.note_input(source=KB, kind="keyboard")
    clk.note_input(source=KB, kind="mouse")  # same device, other kind
    clk.note_input(source=MOUSE, kind="mouse")
    now[0] += 0.4
    clk.note_input(source=KB, kind="keyboard")
    now[0] += 0.1
    clk.note_input(source=KB, kind="keyboard")
    mode._on_drain_timer()
    assert got == [KB_ID, MOUSE_ID, KB_ID]


def test_activity_skips_program_and_own_input(env: Env) -> None:
    mode, _api, clk, _now, _run, _t = _wake_env(env)
    got: list[str] = []
    mode.set_activity_listener(got.append)
    mode.start_detection()
    clk.note_input(source=None, kind="keyboard", press=True)
    clk.note_input(own=True, source=KB, kind="keyboard")
    mode._on_drain_timer()
    assert got == []


def test_activity_and_press_listeners_side_by_side(env: Env) -> None:
    mode, api, clk, _now, _run, _t = _wake_env(env)
    acts: list[str] = []
    presses: list[tuple[str, str]] = []
    mode.set_activity_listener(acts.append)
    mode.set_press_listener(lambda i, k: presses.append((i, k)))
    mode.start_detection()
    for _ in range(3):
        clk.note_input(source=KB, kind="keyboard", press=True)
        clk.note_input(source=MOUSE, kind="mouse")
    mode._on_drain_timer()
    assert acts == [KB_ID, MOUSE_ID]
    assert presses == [(KB_ID, "keyboard")]
    assert api.physical_calls == [KB, MOUSE]  # cached per handle


def test_no_activity_listener_reports_nothing(env: Env) -> None:
    mode, api, clk, _now, _run, timers = _wake_env(env)
    got: list[str] = []
    mode.set_activity_listener(got.append)
    mode.set_activity_listener(None)
    mode.start_detection()
    clk.note_input(source=KB, kind="keyboard")
    mode._on_drain_timer()
    assert got == []
    assert api.physical_calls == []


def test_activity_is_not_traced(env: Env, traced: list[str]) -> None:
    mode, _api, clk, _now, _run, _t = _wake_env(env)
    mode.set_activity_listener(lambda i: None)
    mode.start_detection()
    before = list(traced)
    clk.note_input(source=KB, kind="keyboard")
    clk.note_input(source=MOUSE, kind="mouse")
    mode._on_drain_timer()
    assert traced == before


def test_detection_starts_and_stops_the_listener_while_off(env: Env) -> None:
    mode, _api, clk, _now, _run, _t = env
    assert mode.start_detection() is True
    assert mode.start_detection() is True
    assert clk.started == 1
    mode.stop_detection()
    mode.stop_detection()
    assert clk.stopped == 1


def test_detection_leaves_the_listener_to_the_mode(env: Env) -> None:
    mode, _api, clk, _now, _run, _t = env
    mode.apply(_on())
    mode.start_detection()
    mode.stop_detection()
    assert clk.stopped == 0  # the mode is on: it keeps listening
    mode.start_detection()
    mode.apply(ssm.Settings(enabled=False))
    assert clk.stopped == 0  # Wake PC is still detecting
    mode.stop_detection()
    assert clk.stopped == 1


def test_raw_input_press_flags() -> None:
    key = _raw(1, 0)
    assert ssm.raw_input_press(key) is True
    key.data.keyboard.Flags = 0x01  # RI_KEY_BREAK: key up
    assert ssm.raw_input_press(key) is False
    key.data.keyboard.Flags = 0x02  # RI_KEY_E0, down
    assert ssm.raw_input_press(key) is True
    mouse = _raw(0, 0)
    assert ssm.raw_input_press(mouse) is False  # movement
    for down in (0x0001, 0x0004, 0x0010, 0x0040, 0x0100):
        mouse.data.mouse.u.buttons.usButtonFlags = down
        assert ssm.raw_input_press(mouse) is True
    for other in (0x0002, 0x0008, 0x0020, 0x0080, 0x0200, 0x0400, 0x0800):
        mouse.data.mouse.u.buttons.usButtonFlags = other  # ups, wheels
        assert ssm.raw_input_press(mouse) is False
    assert ssm.raw_input_press(_raw(2, 0)) is False


def test_trace_wake_devices_not_counted_and_press(env: Env, traced: list[str]) -> None:
    mode, _api, clk, _now, run, _t = _wake_env(env)
    mode.set_wake_devices([KB_ID])
    assert "wake devices: 1 ticked" in traced
    mode.set_press_listener(lambda i, k: None)
    mode.apply(_on())
    for _ in range(5):
        clk.note_input(source=MOUSE, kind="mouse")
    run(1)
    line = "not counted: G502 HERO Gaming Mouse (mouse) is not ticked"
    assert traced.count(line) == 1
    clk.note_input(source=KB, kind="keyboard", press=True)
    run(1)
    assert "press: Razer BlackWidow V3 (keyboard)" in traced
    mode.set_wake_devices([KB_ID])  # the list changed: reported again
    clk.note_input(source=MOUSE, kind="mouse")
    run(1)
    assert traced.count(line) == 2


def test_group_input_devices_one_row_per_physical_device() -> None:
    rows = ssm.group_input_devices(
        [
            ("USB\\SC", "", "mouse"),
            ("USB\\SC", "Steam Controller", "keyboard"),
            ("USB\\SC", "Other name", "mouse"),
            ("USB\\KB", "Keyboard", "keyboard"),
            ("", "Unknown", "mouse"),
        ]
    )
    assert rows == [
        ssm.InputDevice("USB\\SC", "Steam Controller", ("keyboard", "mouse")),
        ssm.InputDevice("USB\\KB", "Keyboard", ("keyboard",)),
    ]


def test_input_devices_groups_parts_and_skips_pathless(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ssm,
        "_raw_input_device_list",
        lambda: [(1, "mouse"), (2, "keyboard"), (3, "mouse"), (4, "keyboard")],
    )
    paths = {1: "\\\\?\\HID#SC&Col01#1#{g}", 2: "\\\\?\\HID#SC&Col02#1#{g}", 4: ""}
    monkeypatch.setattr(ssm, "raw_device_path", lambda h: paths.get(h, "x#y"))
    monkeypatch.setattr(
        ssm, "physical_device", lambda i: "USB\\SC" if "SC" in i else "USB\\OTHER"
    )
    monkeypatch.setattr(
        ssm, "_device_name", lambda h: {2: "Steam Controller"}.get(h, "")
    )
    assert ssm.WindowsApi().input_devices() == [
        ssm.InputDevice("USB\\SC", "Steam Controller", ("keyboard", "mouse")),
        ssm.InputDevice("USB\\OTHER", "", ("mouse",)),
    ]


def test_input_devices_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> list[tuple[int, str]]:
        raise OSError("no list")

    monkeypatch.setattr(ssm, "_raw_input_device_list", broken)
    assert ssm.WindowsApi().input_devices() == []


def test_device_physical_id_from_the_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssm, "raw_device_path", lambda h: "\\\\?\\HID#A&Col01#1#{g}")
    seen: list[str] = []

    def physical(instance_id: str) -> str:
        seen.append(instance_id)
        return "USB\\A"

    monkeypatch.setattr(ssm, "physical_device", physical)
    assert ssm.WindowsApi().device_physical_id(7) == "USB\\A"
    assert seen == ["HID\\A&Col01\\1"]
    monkeypatch.setattr(ssm, "raw_device_path", lambda h: 1 / 0)
    assert ssm.WindowsApi().device_physical_id(7) == ""


def test_is_part_hid_collections_and_usb_interfaces() -> None:
    assert ssm._is_part("HID\\VID_28DE&PID_1142&MI_01&COL01\\8&1")
    assert ssm._is_part("USB\\VID_28DE&PID_1142&MI_01\\7&2")
    assert not ssm._is_part("USB\\VID_28DE&PID_1142\\5&3")
    assert ssm.physical_device("") == ""


# ----- the screen saver this program started (found on the user's PC 2026-11-16)


class _Process:
    def __init__(self) -> None:
        self.running = True

    def poll(self) -> int | None:
        return None if self.running else 0


def test_started_screen_saver_counts_as_running_while_windows_says_no(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows' flag stayed 0 while the screen saver this program started ran
    (busy, firefox.exe in front): the started process is what says it runs."""
    process = _Process()
    monkeypatch.setattr(ssm, "_spi_screen_saver_running", lambda: False)
    monkeypatch.setattr(ssm.subprocess, "Popen", lambda *a, **k: process)
    api = ssm.WindowsApi()
    assert not api.screen_saver_running()
    assert api.start_screen_saver(r"C:\Windows\system32\scrnsave.scr")
    assert api.screen_saver_running()
    process.running = False
    assert not api.screen_saver_running()


def test_windows_flag_still_counts_without_a_started_screen_saver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ssm, "_spi_screen_saver_running", lambda: True)
    assert ssm.WindowsApi().screen_saver_running()


# --- SSM2 batch (contract-SSM2: items 5, 6, 7, 9, 10)


def test_ssm2_devices_wait_setting_is_the_limit(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode, api, clk, now, run, _t = env
    lines = _traced(monkeypatch)
    dev = _Devices(1)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(ssm.Settings(**{**_off_only().__dict__, "devices_wait_s": 3}))
    run(120)
    assert mode.status().waiting_for_devices
    run(2)
    assert api.powered_off == 0
    run(1)
    assert api.powered_off == 1 and not mode.status().waiting_for_devices
    assert "devices still being switched off after 3 s: power off sent" in lines


def test_ssm2_devices_wait_is_clamped_and_defaults_to_10() -> None:
    assert ssm.Settings().devices_wait_s == 10
    mode = ssm.ScreenSaverMode(api=FakeApi(), clock_=FakeClock())
    mode.apply(ssm.Settings(devices_wait_s=0))
    assert mode.settings().devices_wait_s == 1
    mode.apply(ssm.Settings(devices_wait_s=500))
    assert mode.settings().devices_wait_s == 60
    assert not hasattr(ssm, "POWER_OFF_WAIT_S")


def test_ssm2_listener_poll_sends_the_power_off_without_a_tick(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    dev = _Devices(2)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(_off_only())
    run(120)
    assert clk.polls and api.powered_off == 0
    # Still busy: the poll asks for more time.
    now[0] += 0.1
    assert mode.on_power_wait_timer() is not None
    dev.busy = False
    now[0] += 0.1
    assert mode.on_power_wait_timer() is None  # no tick in between
    assert api.powered_off == 1 and mode.status().keeping_off
    run(3)
    assert api.powered_off == 1


def test_ssm2_listener_poll_sends_at_the_limit(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.set_device_hooks(_Devices(1).hook, None)
    mode.apply(_off_only())
    run(120)
    now[0] += 10.0
    assert mode.on_power_wait_timer() is None
    assert api.powered_off == 1


def test_ssm2_listener_poll_never_sends_after_input(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    dev = _Devices(1)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(_off_only())
    run(120)
    clk.note_input(source=0x1001, kind="keyboard")
    dev.busy = False
    now[0] += 0.1
    assert mode.on_power_wait_timer() is None
    assert api.powered_off == 0


def test_ssm2_window_proc_poll_timer_kills_it_and_polls(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    dev = _Devices(1)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(_off_only())
    run(120)
    dev.busy = False
    killed: list[int] = []

    class _U:
        def KillTimer(self, hwnd: int, ident: int) -> bool:
            killed.append(ident)
            return True

    clk._user32 = _U()
    assert clk._window_proc(1, ssm._WM_TIMER, ssm._POLL_TIMER_ID, 0) == 0
    assert killed == [ssm._POLL_TIMER_ID] and api.powered_off == 1


def test_ssm2_own_window_never_holds(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.apply(_off_only())
    api.busy = True
    api.own_in_front = True
    run(120)
    assert api.powered_off == 1 and mode.status().hold == ""


def test_ssm2_foreground_is_own_compares_the_process_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    monkeypatch.setattr(ssm, "_foreground_pid", lambda: os.getpid())
    assert ssm.WindowsApi().foreground_is_own()
    monkeypatch.setattr(ssm, "_foreground_pid", lambda: os.getpid() + 1)
    assert not ssm.WindowsApi().foreground_is_own()
    monkeypatch.setattr(ssm, "_foreground_pid", lambda: 0)
    assert not ssm.WindowsApi().foreground_is_own()


def test_ssm2_test_now_counts_down_then_runs_the_sequence(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode, api, clk, now, run, _t = env
    lines = _traced(monkeypatch)
    dev = _Devices(1)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(_on(saver_wait=3600, off_wait=7200))  # long timers
    run(2)
    mode.start_test()
    assert "Test now: starting in 5 s" in lines
    assert mode.test_remaining() == 5
    run(4)
    assert mode.test_remaining() == 1 and dev.starts == 0
    run(1)
    assert mode.test_remaining() == 0
    assert "Test now: sequence started" in lines
    assert dev.starts == 1 and api.powered_off == 0  # devices first
    dev.busy = False
    run(1)
    assert api.powered_off == 1 and mode.status().keeping_off
    assert api.started == []  # no screen saver in the test
    run(30)
    assert api.powered_off == 1
    clk.note_input(source=0x1001, kind="mouse")
    run(1)
    assert not mode.status().keeping_off


def test_ssm2_input_during_the_countdown_cancels(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode, api, clk, now, run, _t = env
    lines = _traced(monkeypatch)
    mode.apply(_on(saver_wait=3600, off_wait=7200))
    mode.start_test(delay_s=5.0)
    run(2)
    clk.note_input(source=0x1001, kind="keyboard")
    run(1)
    assert "Test now: cancelled" in lines and mode.test_remaining() == 0
    run(10)
    assert api.powered_off == 0


def test_ssm2_cancel_test(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    mode, api, clk, now, run, _t = env
    lines = _traced(monkeypatch)
    mode.apply(_on(saver_wait=3600, off_wait=7200))
    mode.start_test()
    mode.cancel_test()
    assert "Test now: cancelled" in lines and mode.test_remaining() == 0
    run(10)
    assert api.powered_off == 0


def test_ssm2_turn_off_now_is_immediate(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    mode.apply(_on(saver_wait=3600, off_wait=7200))
    run(2)
    mode.turn_off_now()
    assert api.powered_off == 1 and mode.status().keeping_off
    run(5)
    assert api.powered_off == 1


def test_ssm2_last_away_filled_when_input_ends_keep_off(env: Env) -> None:
    mode, api, clk, now, run, _t = env
    dev = _Devices(2)
    mode.set_device_hooks(dev.hook, None)
    mode.apply(_off_only())
    assert mode.status().last_away is None
    run(120)
    dev.busy = False
    run(1)
    now[0] += 1.5
    mode.on_display_state(True)  # one wake
    run(60)
    clk.note_input(source=0x1001, kind="mouse")
    run(1)
    away = mode.status().last_away
    assert away is not None
    assert away["wakes"] == 1 and away["devices_off"] == 2
    assert 61.0 <= away["off_s"] <= 63.0
    assert away["end"] >= away["start"]
    assert mode.status().wake_count == mode.status().wakes
