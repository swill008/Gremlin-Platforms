# Contract SSM2: Screen Saver Mode batch (2026-11-20)

User: "1 a, 2 a, 3 a, 4 a, go build it" after the full window mock-up (items 1-15).
Every agent builds to these names. One owner per file (table at the end).

## Items
1. Status as a two-column table (label | value [· detail]).
2. Power off displays row shows "switching devices off…" while it waits.
3. Wake-ups row: "none this time" / "Windows turned the displays back on N times"; the
   "· a device may need Switch off (see Devices)" detail only at N >= 3.
4. vJoy rows stay shown, locked (no change).
5. New setting **Wait for devices to switch off**, 1-60 s, default 10, under Timers, below
   Power off displays; note "at most; the displays go off as soon as they're done".
6. The wait-for-devices check runs on the listener thread (Win32 timer on its window, like
   the keep-off re-send), not the main-thread tick (tick stays a fallback).
7. The full-screen hold never counts a window of Gremlin's own process.
8. State snapshot in the trace and in Save Diagnostics.
9. **Test now** button: after a 5 s countdown runs the real sequence (devices first, displays
   off, keep-off) until a counted input.
10. **Last time away** row: "Displays off 12 min 46 s · 1 wake-up · 2 devices switched off and
    back on · no freeze" (or "· window not responding N s").
11. Setting **Keep tracing on after a restart** (Live Log Reader › Trace), off at first.
12. Tray menu: "Screen Saver Mode" (checkable) and "Turn displays off now".
13. **Devices back on** row: "all back on" / "<name> is still switched off" + Try again.
14. Screen Saver Mode writes nothing to History.
15. Not in History (still saved): Diagnostic logs (log-level), Log When Not Responding,
    all of global/screen-saver-mode/*, display/hidhide/managed, the new tracing setting.
    HidHide photos stay in History.

## Names
Core `gremlin/screen_saver_mode.py` (CORE):
- `Settings.devices_wait_s: int = 10` (clamped 1-60) replaces `POWER_OFF_WAIT_S`.
- `ScreenSaverMode.start_test(delay_s: float = 5.0) -> None`, `cancel_test()`,
  `test_remaining() -> int` (whole seconds left, 0 = no test pending).
- `ScreenSaverMode.turn_off_now() -> None` (the sequence at once).
- `Status.waiting_for_devices: bool`, `Status.wake_count: int` (exists?),
  `Status.last_away: dict | None` = {"off_s": float, "wakes": int, "devices_off": int,
  "devices_back": int, "start": wall time, "end": wall time}.
- Own-process windows never count for the full-screen hold.
Model `gremlin/ui/screen_saver_mode_model.py` (MODEL), QML name `_ssm`:
- `statusRows` (list of {"label","value","detail","tone"}; tone "" | "ok" | "warn"), rows in
  order: Listener, Your idle time, Windows' idle time, Screen saver, Power off displays,
  Wake-ups, Hold, Last time away, Devices back on. Notify `statusChanged`.
- `devicesWaitS` (int) + Slot `setDevicesWaitS(int)`; config key
  `global/screen-saver-mode/devices-wait-s` (int, default 10, 1-60).
- Slot `testNow()`, Property `testCountdown` (int, 0 = none), Slot `cancelTest()`.
- Slot `retryDevices()`, Property `devicesBackRetry` (bool: show Try again).
- Module functions for the tray: `ssm_enabled() -> bool`, `set_ssm_enabled(on: bool)`,
  `turn_displays_off_now() -> None`.
- Trace "Switch off: <device name>, on|off" by name.
- Registers the Screen Saver Mode snapshot provider (below).
Trace (TRACE): `gremlin/trace.py`
- `register_snapshot(section: str, provider: Callable[[], list[str]]) -> None`
- `write_snapshot(reason: str) -> None`: one EVENT line "State (<reason>)" then one line per
  provider line, control "State", point EVENT; written when tracing turns on, at start when
  tracing is on, and on `snapshot_changed(section)`.
- `snapshot_changed(section: str) -> None`: rewrites that section's lines.
- `snapshot_text() -> str`: all sections, for Save Diagnostics (`state.txt` in the zip).
- Program-wide provider "Program": version/build, profile name and running or not,
  Log When Not Responding, Diagnostic logs level, ticked trace rows, Keep tracing on.
- Setting `global/trace/keep-on` (bool, default False, expose False) + its tick on the Trace tab.

## Owners
| Agent | Files |
|---|---|
| CORE | gremlin/screen_saver_mode.py, its core tests |
| MODEL | gremlin/ui/screen_saver_mode_model.py, gremlin/device_disable.py (if needed), model tests |
| QML | qml/WindowScreenSaverMode.qml, its window tests (ssm_ui_smoke.py, test_ssm_ui.py) |
| TRACE | gremlin/trace.py, gremlin/ui/trace_model.py, qml/LiveLogTrace.qml, gremlin/diagnostics.py, trace tests |
| TRAY | gremlin/ui/system_tray.py, tray tests |
| CONFIG | gremlin/config.py, history tests |
| DOCS | claude/program-map/*, claude/glossary.md, qml/help/*.js, claude/todo.md |
Shared file the lead keeps: joystick_gremlin.py (option registration if needed: ask the lead).
