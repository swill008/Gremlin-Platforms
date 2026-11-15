# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode core (program map 12, S2-S11, S15): the countdown on a
stepped clock with a fake WindowsApi and a fake input clock. Nothing here
calls Windows, registers raw input or blanks a screen."""

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

    @property
    def actions(self) -> int:
        return len(self.started) + self.powered_off


class FakeClock(ssm.InputClock):
    def __init__(self) -> None:
        super().__init__()
        self.started = 0
        self.stopped = 0
        self.ok = True

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
    action: str = ssm.ACTION_POWER_OFF,
    wait_override_s: int = 0,
    hold_fullscreen: bool = True,
) -> ssm.Settings:
    return ssm.Settings(True, action, wait_override_s, hold_fullscreen)


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
    mode.apply(_on())
    assert clk.started == 1 and timers
    run(119)
    assert api.powered_off == 0
    assert mode.status().remaining_s == pytest.approx(1.0)
    run(1)
    assert api.powered_off == 1
    run(1000)
    assert api.powered_off == 1
    assert mode.status().fired is True


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
    run(110)
    setattr(api, attr, True)
    run(300)
    assert api.powered_off == 0
    assert mode.status().hold == hold
    assert mode.status().remaining_s == 0
    setattr(api, attr, False)
    run(119)
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
    mode.apply(_on(action=ssm.ACTION_SCREEN_SAVER))
    st = mode.status()
    assert st.wait_s == 60 and st.windows_wait_s == 60 and st.wait_from_windows
    run(60)
    assert api.started == [api.path]
    assert api.powered_off == 0


def test_override_replaces_windows_wait(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on(wait_override_s=30))
    st = mode.status()
    assert st.wait_s == 30 and st.windows_wait_s == 120
    assert st.wait_from_windows is False
    run(30)
    assert api.powered_off == 1


def test_windows_wait_read_again_when_countdown_starts(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    run(10)
    api.display_wait = 40
    clk.note_input()
    run(40)
    assert api.powered_off == 1


def test_windows_never_does_nothing(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    api.display_wait = 0
    mode.apply(_on())
    run(5000)
    assert api.actions == 0
    assert mode.status().problem == ssm.PROBLEM_WINDOWS_NEVER


def test_no_screen_saver_does_nothing_even_with_override(env: Env) -> None:
    mode, api, clk, _now, run, _t = env
    api.path = ""
    mode.apply(_on(action=ssm.ACTION_SCREEN_SAVER, wait_override_s=10))
    run(500)
    assert api.actions == 0
    assert mode.status().problem == ssm.PROBLEM_NO_SCREEN_SAVER


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
    assert st.windows_wait_s == 120 and st.wait_s == 120
    assert st.wait_from_windows is True
    mode.apply(ssm.Settings(enabled=False, wait_override_s=45))
    st = mode.status()
    assert st.windows_wait_s == 120 and st.wait_s == 45
    assert st.wait_from_windows is False


def test_status_off_follows_the_chosen_action(env: Env) -> None:
    mode, api, _clk, _now, _run, _t = env
    mode.apply(ssm.Settings(enabled=False, action=ssm.ACTION_POWER_OFF))
    assert mode.status().windows_wait_s == 120
    mode.apply(ssm.Settings(enabled=False, action=ssm.ACTION_SCREEN_SAVER))
    assert mode.status().windows_wait_s == 60


def test_status_off_after_switching_off(env: Env) -> None:
    mode, api, _clk, _now, run, _t = env
    mode.apply(_on())
    run(5)
    mode.apply(ssm.Settings(enabled=False))
    st = mode.status()
    assert st.enabled is False and st.windows_wait_s == 120


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
    assert mode.status().windows_wait_s == 120  # cached within the second
    now[0] += 1.0
    assert mode.status().windows_wait_s == 300
    assert reads[0] == 2


@pytest.fixture
def traced(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    lines: list[str] = []
    monkeypatch.setattr(ssm, "_trace", lines.append)
    return lines


def _has(lines: list[str], text: str) -> bool:
    return any(text in line for line in lines)


def test_trace_settings_listener_and_countdown(env: Env, traced: list[str]) -> None:
    mode, api, clk, _now, run, _t = env
    mode.apply(_on())
    assert _has(traced, "settings applied: on, power off displays")
    assert _has(traced, "listener started")
    assert _has(traced, "countdown started: wait 120 s (from Windows")
    traced.clear()
    mode.apply(_on(wait_override_s=30))
    assert _has(traced, "countdown started: wait 30 s (typed")
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
    assert sum(t == "problem: windows_never" for t in traced) == 1
    api.display_wait = 50
    mode.apply(_on(wait_override_s=0, hold_fullscreen=False))
    assert _has(traced, "problem cleared")


def test_failed_screen_saver_start_is_logged(
    env: Env, traced: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    mode, api, clk, _now, run, _t = env
    api.start_screen_saver = lambda path: False  # type: ignore[method-assign]
    with caplog.at_level("WARNING", logger="system"):
        mode.apply(_on(action=ssm.ACTION_SCREEN_SAVER))
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
        mode.apply(_on())
        run(120)
    assert _has(traced, "action fired: power off displays: failed (no displays)")
    assert "action failed" in caplog.text


def test_trace_helper_uses_trace_screen_saver(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import trace

    got: list[str] = []
    monkeypatch.setattr(trace, "screen_saver", got.append, raising=False)
    ssm._trace("hello")
    assert got == ["hello"]
    monkeypatch.delattr(trace, "screen_saver")
    ssm._trace("no trace function yet")  # no error
