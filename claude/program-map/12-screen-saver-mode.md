# Screen Saver Mode

**Approved 2026-11-15; built 2026-11-15 (S1-S15); batch 2 (S5 note, S14 widened, S16 tracing) approved 2026-11-15, user: 28 a, 29 a; built 2026-11-15, pending the agents' reports (`claude/plans/screen-saver-mode/contract-2.md`).** Written from the user's decisions of
2026-11-15 (section 12) and the study `claude/plans/oled-idle-watcher-study.md`
(sections 2-6: the measurements, the HidHide test and the screen tests).

## 1. Purpose

Some devices (the VKB NXT throttle, the Maono PD200X microphone's consumer
control part, and other flight gear) send reports to Windows many times a
second even when nobody touches them. Windows counts each report as user
activity, so its idle clock never runs: the screen saver and display-off
never happen. That risks burn-in on an OLED monitor. Windows has no setting
to ignore a device for idle time, and hiding the devices with HidHide does
not help while any program (Gremlin included) reads them (study section 6).

Screen Saver Mode keeps Gremlin's own idle clock from the keyboard and mouse
only. When it runs out, Gremlin starts the screen saver or powers off the
displays, whichever the user chose. Real keyboard or mouse input ends the
screen saver or wakes the displays as usual (Windows does that itself).

## 2. Files

Built 2026-11-15 to `claude/plans/screen-saver-mode/contract.md`:
- `gremlin/screen_saver_mode.py` (new): `Settings`, `Status`, `WindowsApi` (the only place that calls Windows; tests pass a fake), `InputClock` (Raw Input on its own thread), `ScreenSaverMode` (`apply`, `settings`, `tick`, `status`, `shutdown`) and `manager()`, the one instance. Constants `ACTION_SCREEN_SAVER` ("screen_saver"), `ACTION_POWER_OFF` ("power_off").
- `gremlin/hid_report_scan.py` (new): `DeviceRate`, `scan(seconds=4.0, should_stop=None)`, the devices check (S12).
- `gremlin/power_requests.py` (new): `ProgramRequest`, `RequestsResult`, `list_requests(runner=None)` and `set_ignored(name, ignored, runner=None)`, the programs list and Ignore this program (S13, S14); `runner` is the elevation seam.
- `gremlin/ui/screen_saver_mode_model.py` (new): the window's model (QML).
- `qml/WindowScreenSaverMode.qml` (new): the window, object name `screenSaverModeWindow`.
- `qml/main_commands.js`: command `tools.screenSaverMode`, "Screen Saver Mode…", group Tools, opens the window with `openTool` (S1).
- `qml/Main.qml`: the Tools menu item in the bottom group (OSC Monitor, Screen Saver Mode…, History, Options) (S1).
- `joystick_gremlin.py`: registers the settings and applies them to `manager()` at start and on change; `manager().shutdown()` at quit (S2, S10).
- `gremlin/sendinput.py` (page 06): marks the program's own mouse input with `windows_event_hook.OWN_KEY_MARK` (S3).
- Help: `qml/help/tools.js` topics `tools-screen-saver-mode` and `tools-q-screen-stays-on`; `qml/help_links.js` allows `open:tools.screenSaverMode`. From 2026-11-15 (batch 2) `tools-trace` lists the Screen Saver Mode tick (S16).
- Batch 2 (2026-11-15, `contract-2.md`): `gremlin/trace.py` (page 01): the Screen Saver Mode tick, `trace.screen_saver_on()`, `trace.set_screen_saver(on)`, `trace.screen_saver(text)` (S16); the Trace tab's model and QML show the tick next to HidHide (page 01, files to confirm from SSM-TRACE's report). `power_requests.py`: `ProgramRequest.kind` ("PROCESS" | "DRIVER" | "SERVICE") and `detail`; `set_ignored(name, ignored, kind="PROCESS", runner=None)` (S14). `screen_saver_mode.py`, `hid_report_scan.py`, `power_requests.py` and the model write their trace lines (S16); `status()` while off carries Windows' wait (S5).

## 3. What it owns

| Data | Owner | Written by | Read by |
|---|---|---|---|
| The idle clock: the time of the last keyboard or mouse input counted (S3) | `InputClock` (`last_input()`, `gremlin.clock.monotonic()`) | the raw input thread; `note_input()` in tests | `ScreenSaverMode.tick` |
| Whether the action has fired in this idle period (S6) | `ScreenSaverMode` (`fired` in `Status`) | `tick`; reset by counted input | `tick`, `status` |
| The settings: on/off, action, typed wait time, full-screen hold-off (S2, S4, S5, S7) | `ScreenSaverMode.settings()`; saved in the program's settings, section "global", group "screen-saver-mode": "enabled" (Bool, False), "action" (String, "power_off"), "wait-override-s" (Int, 0 = use Windows' time), "hold-fullscreen" (Bool, True) | the window, through `joystick_gremlin.py` `apply` | `tick`, the window, History (S10) |
| The status shown in the window (S8, S9, S15) | `Status` (enabled, listening, idle_s, windows_idle_s, wait_s, windows_wait_s, wait_from_windows, hold, fired, problem, remaining_s) | `status()`, built on demand | the model, once a second |
| The devices list and the programs list | the model (built fresh at each press, empty until the first) | `hid_report_scan.scan`, `power_requests.list_requests` | the window |
| The ignored programs, drivers and services (S14) | Windows (`powercfg /requestsoverride`, under [PROCESS], [DRIVER] or [SERVICE]), not the program | `power_requests.set_ignored` | `list_requests` |
| The Screen Saver Mode trace tick (S16) | `gremlin/trace.py` (page 01), saved in settings `debug/trace` like the HidHide tick | the Trace tab | `trace.screen_saver` |

## 4. Entry points

| Entry | Where | What runs |
|---|---|---|
| Tools › Screen Saver Mode… (also the Command Palette) | `main_commands.js` `tools.screenSaverMode` → `openTool` (S1) | `WindowScreenSaverMode.qml` |
| Program start | `joystick_gremlin.py` reads the settings and calls `manager().apply(settings)` | while on, the raw input thread and the 1 s timer start (S2) |
| A setting changed in the window | the setting's change → `manager().apply(...)`; History records it (S10) | on/off starts or stops the clock and timer |
| Refresh Devices | the model → `threads.run_for(owner, name, scan, deliver)` | `hid_report_scan.scan` (S12) |
| Refresh Programs / Ignore this program | the model → `threads.run_for` | `power_requests.list_requests` / `set_ignored`, one elevated run each (S13, S14) |
| Quit | `joystick_gremlin.py` | `manager().shutdown()` |
| The Trace tab's **Screen Saver Mode** tick (S16) | Live Log Reader › Trace (page 01 S146) → `trace.set_screen_saver(on)` | while tracing, the listener, countdown, holds, actions and Refresh runs write trace lines |

## 5. Talks to

| Who | How | What |
|---|---|---|
| Windows Raw Input | `RegisterRawInputDevices` (usage page 0x01, usages 0x02 mouse and 0x06 keyboard, `RIDEV_INPUTSINK`) on a hidden top-level window | every keyboard and mouse event, from any program; `ExtraInformation` equal to `OWN_KEY_MARK` is the program's own and is skipped (S3) |
| Windows settings | `HKCU\Control Panel\Desktop` `ScreenSaveTimeOut` (only when `SCRNSAVE.EXE` is set); the active power scheme's display-off time (`SUB_VIDEO` `VIDEOIDLE`, AC or DC by `GetSystemPowerStatus`) | Windows' wait time (S5, S8) |
| Windows idle and hold-off state | `GetLastInputInfo`; `SHQueryUserNotificationState` (busy, full-screen Direct3D, presentation mode); `CallNtPowerInformation(SystemExecutionState)` `ES_DISPLAY_REQUIRED`; locked workstation | Windows' idle time (S9) and the hold-offs (S7, S11, S15) |
| Windows actions | the chosen screen saver file with `/s`, or `SC_MONITORPOWER` | the action (S4, S6) |
| HID devices | `SetupDi` with `HidD_GetHidGuid`, opened read-only, overlapped reads with bounded waits | Refresh Devices (S12) |
| `powercfg` | one elevated run (`ShellExecuteExW` "runas", `cmd /c powercfg /requests` and `/requestsoverride` into a temp file, bounded 60 s wait) | Refresh Programs and Ignore this program (S13, S14) |
| `gremlin/windows_event_hook.py` (02) | `OWN_KEY_MARK` | the mark on the program's own keys (`keyboard.py`) and mouse input (`sendinput.py`, 06) |
| The program's settings and History (01, 08) | `cfg.register`, section "global", group "screen-saver-mode" | saved choices and their History entries (S2, S10) |
| `gremlin.threads`, `gremlin.clock` (01) | `threads.start`, `threads.main_timer`, `threads.run_for` | the threads below |
| `gremlin/trace.py` (01) | `trace.screen_saver_on()`, `trace.screen_saver(text)` | the trace lines (S16); errors also to `logging.getLogger("system")` |

## 6. Threads and timers

| Thread or timer | Started by | Does | Ends |
|---|---|---|---|
| Raw input thread | `InputClock.start` through `gremlin.threads.start`, only while Screen Saver Mode is on | its own hidden window and message loop; each raw input message only notes the time (or skips the program's own input) | `InputClock.stop` (Screen Saver Mode off, or quit), bounded wait |
| 1 s timer on the main thread | `apply` through `gremlin.threads.main_timer`, only while on | `ScreenSaverMode.tick`: reads Windows' wait when the countdown starts, checks the hold-offs, fires the action once per idle period | `apply` with Screen Saver Mode off, `shutdown` |
| Window poll | the window, while open | reads `status()` once a second | window closed |
| Refresh Devices / Refresh Programs / Ignore this program | `threads.run_for(owner, name, work, deliver)` | the scan (about 4 s, bounded reads) or the elevated `powercfg` run (bounded 60 s wait); the result is delivered to the main thread; the buttons read "Checking… (4 s)" while busy | when the work returns, or `should_stop` |

Off (S2): no raw input registered, no thread, no timer. Tracing (S16) adds no thread: each owner writes its lines from the thread it already runs on (`trace.py` writes are thread-safe, page 01 S151).

## 7. Rule breaks

None planned. Layer rule: Screen Saver Mode reads only the keyboard and mouse through Raw Input and its own read-only HID scan; it sends no input and touches no output module or driver.

## 8. Behaviour spec

- **S1** **Tools › Screen Saver Mode…** (command `tools.screenSaverMode`) should open the Screen Saver Mode window. The item sits in the Tools menu's bottom group: OSC Monitor, **Screen Saver Mode…**, History, Options. [decided 2026-11-15, user: 17 a, 18 a]
- **S2** The window should have an on/off switch, **Screen Saver Mode**. While it is on, Gremlin keeps its idle clock whenever the program is open (a profile running or not, the window in the tray or not). Off, Gremlin does nothing at all and installs no hooks. It is off until the user switches it on, and remembers the choice. [decided 2026-11-15, user: 19 a]
- **S3** Gremlin's idle clock should restart on every keyboard key (down or up) and every mouse event (movement, buttons, wheel). Joysticks, gamepads, microphones and every other device never count. Keyboard and mouse input other programs send (for example a remote-control program) counts; input Gremlin sends itself (its bindings' keys and mouse) does not. [decided 2026-11-15, user: 2 b, 3 a]
- **S4** **Action**: one choice, **Screen saver** (start the screen saver chosen in Windows) or **Power off displays** (turn every display off). [decided 2026-11-15, user: 15]
- **S5** **Wait time**: shows Windows' current time as the default, the screen saver wait for Screen saver and the current power plan's display-off time for Power off displays, read again each time the countdown starts, so a change in Windows is followed without a restart. Windows' time is shown while Screen Saver Mode is off too (fixed 2026-11-15: it showed "never" while off, found when the user tried 1.0.38). A time the user types replaces it and is used from then on, ignoring Windows' time, until the user clears it; cleared, Windows' time is shown and used again. [decided 2026-11-15, user: 4, 16]
- **S6** When the idle clock reaches the wait time, Gremlin should do the chosen action once, then nothing more until keyboard or mouse input restarts the clock. Windows itself ends the screen saver or wakes the displays on that input. Constant device reports end neither (study section 6, tested 2026-11-15).
- **S7** **Hold off during full-screen programs** (on at first): while Windows reports a full-screen program, a game in exclusive full screen or presentation mode in front, Gremlin does not do the action; the countdown starts again when it ends. [decided 2026-11-15, user: 5 a]
- **S8** If the action is Screen saver and Windows has no screen saver chosen, Gremlin should do nothing and the window should say "No screen saver is chosen in Windows." [decided by lead (authorised): small detail]
- **S9** The window should show a status line with Gremlin's idle time and Windows' idle time side by side (Windows' stays near 0 while devices keep it awake), and say when the keyboard and mouse can't be listened to (the hooks failed), in which case nothing is done. It also says Screen Saver Mode works only while Gremlin Platforms is open.
- **S10** Changes to the Screen Saver Mode settings should go into History, named as the window shows them (as 01 S34).
- **S11** While the workstation is locked, Gremlin should do nothing (Windows handles it).
- **S12** The window should have a **Refresh Devices** button, with a short description under it ("Lists the devices that never go quiet and keep Windows thinking someone is using the PC."): it reads every HID device for about 4 seconds, read-only, and lists the ones sending reports constantly, with the device name and reports per second. The list is built fresh at each press from the devices connected then (nothing is hard-coded) and is empty until the first press. [decided 2026-11-15, user: 7, 20 "Refresh devices"; named "Refresh Devices" with a description, user 2026-11-15]

- **S13** Next to **Refresh Devices**, a **Refresh Programs** button, with a short description under it ("Lists the programs asking Windows to keep the display on. Needs administrator rights each time."), should list the programs that ask Windows to keep the display or the PC awake (what `powercfg /requests` reports). Windows gives this list only to administrators, so each press asks Windows for administrator rights; refused, the window says so and nothing else happens. [decided 2026-11-15, user: 21 b; named "Refresh Programs" with a description, user 2026-11-15]

- **S14** Each row **Refresh Programs** lists (a program, a driver or a service) should have an **Ignore this program** switch. Programs are named by their exe file name; drivers and services by the full name Windows lists (the text after "[DRIVER] " or "[SERVICE] " in `powercfg /requests`, e.g. "USB Audio 2.0 (USB\VID_0DB0&PID_CD0E&MI_00\9&9c4d365&0&0000)"), with the detail line Windows gives under it. On, Gremlin adds Windows' override for that row's display and PC requests (`powercfg /requestsoverride PROCESS|DRIVER|SERVICE "<name>" ...`); off, it removes it. Each change asks Windows for administrator rights; refused, the switch goes back and the window says so. The ignored programs are Windows' own setting, so they hold while Gremlin is closed, and the window shows what Windows has. [decided 2026-11-15, user: 24 a] [changed 2026-11-15, user: 28 a; driver form checked on the user's PC 2026-11-15; service form not verified (SSM-SERVICE-UNTESTED)] (was: programs only; drivers and services had no switch)

- **S15** While any program asks Windows to keep the display on (Windows' combined display flag, read without administrator rights, as a video playing in a window or full screen does), Gremlin should not do the action; the countdown starts again when the flag goes off. Programs ignored with S14 don't set the flag. The status line says "On hold: a program is keeping the display on". [decided 2026-11-15, user: 22, 25 a; checked 2026-11-15: the flag on with a video playing in a window, off when paused]

- **S16** The Live Log Reader's Trace tab should have a **Screen Saver Mode** tick (next to HidHide's, page 01 S146; saved like the other ticks). While tracing is on and it is ticked, Screen Saver Mode writes trace lines (control "Screen Saver Mode"): the keyboard and mouse listener started, stopped or failed (with Windows' error); the countdown started (the wait and whether it came from Windows or was typed); each hold beginning and ending, with its reason; each action fired (which, and the result); a problem shown or cleared; settings applied; each Refresh Devices run (the devices found, each one's rate); each Refresh Programs and Ignore this program run: the exact `powercfg` command line, its exit code, refused or timed out, Windows' raw output (cut to 4 KB), the rows read from it and the check result; and the window's button presses and the message shown. Off, or with the tick off, nothing is written and it costs one check. Errors (exceptions, refusals, failed checks) always also go to the normal log, with tracing off too, so a failure is never silent. [decided 2026-11-15, user: "we need to add tracing to this portion of the program for debugging"; 29 a] [glossary: Trace]

## 9. Questions for the user

None open (Q1 off at first, Q2 "Refresh devices": answered 2026-11-15).

## 10. Known gaps

- ~~SSM-NOT-BUILT~~ (closed 2026-11-15: S1-S15 built; tests below; raw input checked on the user's PC: 2,071 keyboard and mouse messages in 20 s, all counted).
- SSM-HARDWARE (open, 2026-11-15): not yet tried from the installed program on the user's PC: the two actions fired by the countdown (S6; the screen saver and display off were tested by script, study section 6), the elevated Refresh Programs and Ignore this program (S13, S14; never run, parsers built from sample output), the full-screen hold (S7). Checked with the user after installing 1.0.38.
- SSM-SERVICE-UNTESTED (open, 2026-11-15): Ignore this program for a service row ([SERVICE] in `powercfg /requests`, S14) is built the same way as for drivers but not verified: the user's PC had no service request to try it on.
- ~~SSM-NEVER-WHILE-OFF~~ (found and fixed 2026-11-15, S5): with Screen Saver Mode off the window showed Windows' wait as "never" (Windows' display-off time was 300 s), because the status was filled only by the 1 s tick, which doesn't run while off; found when the user tried 1.0.38. `status()` now reads Windows' wait while off too.
- SSM-UAC-HOLD (open, small, 2026-11-15): the lock check treats any input desktop other than "Default" as locked, so a User Account Control prompt also holds the countdown while it is open.

## 11. Size and test coverage

Tests (2026-11-15): `test/unit/test_ssm_core.py` (23), `test/unit/test_ssm_scan.py` (33), `test/unit/test_ssm_ui.py` (24, with `ssm_ui_smoke.py`, `ssm_ui_fakes.py`), `test/unit/test_ssm_e2e.py` (33, two runs: the restart carries the settings). Earlier plan: `test/unit/test_ssm_*.py`: the clock counts keyboard and mouse only and skips the program's own input (`InputClock.note_input(own=True)`); the wait time follows Windows and the typed time (fake `WindowsApi`); the action fires once per idle period, and holds off while locked, in full screen and while the display flag is on (fake clock and fake `WindowsApi`; tests never start the screen saver or turn displays off); off registers nothing and starts no timer; the scans parse their results with a fake `runner` (no test elevates or runs `powercfg`); the Tools item opens the window; the window off-screen. Help: `test_help_guide.py`, `test_help_links.py`, `test_help_links_resolve.py`. Batch 2 (2026-11-15, counts to confirm from the agents' reports): `test/unit/test_ssm_trace.py` (new: the tick, the lines while ticked, nothing while off, errors in the normal log), `test_ssm_core.py` (status while off carries Windows' wait; trace lines), `test_ssm_scan.py` (driver and service rows, kind, name checks, the quoted command, trace lines), `test_ssm_ui.py` and `test_ssm_e2e.py` (driver rows get the switch).

## 12. Review

| Decision | Summary |
|---|---|
| D-12-SSM (2026-11-15, user) | Gremlin keeps its own idle clock from keyboard and mouse only; HidHide "man in the middle" ruled out by test |
| D-12-SSM-ACTION (2026-11-15, user: 15) | One action, chosen: Screen saver or Power off displays |
| D-12-SSM-TIME (2026-11-15, user: 4, 16) | Windows' time shown and used by default, followed live; a typed time overrides until cleared |
| D-12-SSM-INPUT (2026-11-15, user: 2 b, 3 a) | Keyboard and mouse only; other programs' input counts, Gremlin's own does not |
| D-12-SSM-FULLSCREEN (2026-11-15, user: 5 a) | Hold off during full-screen programs, on at first |
| D-12-SSM-DEFAULTS (2026-11-15, user: 19 a, 20) | Off until switched on; the devices check button is "Refresh devices" |
| D-12-SSM-REQUESTS (2026-11-15, user: 21 b) | A second button lists the programs keeping the display on, asking for administrator rights at each press |
| D-12-SSM-IGNORE (2026-11-15, user: 24 a) | Ignore this program switch per program, changing Windows' request override with administrator rights |
| D-12-SSM-DISPLAY-FLAG (2026-11-15, user: 22, 25 a) | Hold off while any program keeps the display on (Windows' combined flag, no admin); tested with a video |
| D-12-SSM-PLACE (2026-11-15, user: 1 a, 17 a, 18 a) | Its own map page; named Screen Saver Mode; Tools menu bottom group above History |
| D-12-SSM-DRIVERS (2026-11-15, user: 28 a) | Ignore this program works for drivers and services too, named by the full name Windows lists (S14); service form not verified |
| D-12-SSM-TRACE (2026-11-15, user: "we need to add tracing to this portion of the program for debugging"; 29 a) | A Screen Saver Mode tick on the Trace tab; the listener, countdown, holds, actions and each Refresh run with the exact powercfg commands, exit codes and raw output; errors always in the normal log (S16); with the "never" fix (S5) |
