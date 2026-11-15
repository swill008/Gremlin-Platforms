# Screen Saver Mode

**Approved 2026-11-15; built 2026-11-15 (S1-S15); batch 2 (S5 note, S14 widened, S16 tracing) approved 2026-11-15, user: 28 a, 29 a; built 2026-11-15 (`claude/plans/screen-saver-mode/contract-2.md`); batch 3 (Devices / Programs / System sections S12-S14, S17; last reset by S18; hold program S19) approved 2026-11-15, user: 1 a, 2 a, 3 a, 4 a, 5 "three rows grouped in sections", mock-up `claude/drafts/screen-saver-mode-mockup.svg`; built 2026-11-15, pending the agents' reports (`claude/plans/screen-saver-mode/contract-3.md`).** Written from the user's decisions of
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
- Batch 3 (2026-11-15, `contract-3.md`; to confirm from the agents' reports): `screen_saver_mode.py`: `Status.last_reset_by`, `last_reset_kind` ("keyboard" | "mouse" | "program" | ""), `last_reset_age_s`, `program_input_per_min`, `hold_program`; `InputClock.note_input(own=False, source=None)` (source: an opaque device key, None for input sent by a program); device names looked up once per device handle and cached; `WindowsApi.foreground_program()` (S18, S19). `power_requests.py`: `split(programs)` → (Programs rows, System rows) and `ProgramRequest.also_awake` (S13, S17). The model and `WindowScreenSaverMode.qml`: the three sections, object names `ssmSectionDevices`, `ssmSectionPrograms`, `ssmSectionSystem`, `ssmRefreshSystem`, `ssmSystemList`, `ssmSystemMessage`, `ssmLastReset`, `ssmAlsoAwake` (S12-S14, S17, S18).

## 3. What it owns

| Data | Owner | Written by | Read by |
|---|---|---|---|
| The idle clock: the time of the last keyboard or mouse input counted (S3) | `InputClock` (`last_input()`, `gremlin.clock.monotonic()`) | the raw input thread; `note_input()` in tests | `ScreenSaverMode.tick` |
| Whether the action has fired in this idle period (S6) | `ScreenSaverMode` (`fired` in `Status`) | `tick`; reset by counted input | `tick`, `status` |
| The settings: on/off, action, typed wait time, full-screen hold-off (S2, S4, S5, S7) | `ScreenSaverMode.settings()`; saved in the program's settings, section "global", group "screen-saver-mode": "enabled" (Bool, False), "action" (String, "power_off"), "wait-override-s" (Int, 0 = use Windows' time), "hold-fullscreen" (Bool, True) | the window, through `joystick_gremlin.py` `apply` | `tick`, the window, History (S10) |
| The status shown in the window (S8, S9, S15, S18, S19) | `Status` (enabled, listening, idle_s, windows_idle_s, wait_s, windows_wait_s, wait_from_windows, hold, fired, problem, remaining_s; batch 3: last_reset_by, last_reset_kind, last_reset_age_s, program_input_per_min, hold_program) | `status()`, built on demand | the model, once a second |
| The Devices, Programs and System lists (S12, S13, S17) | the model, one list per section (each built fresh at its own button's press, empty until the first) | `hid_report_scan.scan`; `power_requests.list_requests` then `split` (each Refresh keeps its own half) | the window |
| The last reset source and the program-input count (S18) | `InputClock` (the last counted input's source; a cache of device names by device handle; counted inputs from programs in the last 60 s) | the raw input thread | `status()` |
| The ignored programs, drivers and services (S14) | Windows (`powercfg /requestsoverride`, under [PROCESS], [DRIVER] or [SERVICE]), not the program | `power_requests.set_ignored` | `list_requests` |
| The Screen Saver Mode trace tick (S16) | `gremlin/trace.py` (page 01), saved in settings `debug/trace` like the HidHide tick | the Trace tab | `trace.screen_saver` |

## 4. Entry points

| Entry | Where | What runs |
|---|---|---|
| Tools › Screen Saver Mode… (also the Command Palette) | `main_commands.js` `tools.screenSaverMode` → `openTool` (S1) | `WindowScreenSaverMode.qml` |
| Program start | `joystick_gremlin.py` reads the settings and calls `manager().apply(settings)` | while on, the raw input thread and the 1 s timer start (S2) |
| A setting changed in the window | the setting's change → `manager().apply(...)`; History records it (S10) | on/off starts or stops the clock and timer |
| Refresh Devices | the model → `threads.run_for(owner, name, scan, deliver)` | `hid_report_scan.scan` (S12) |
| Refresh Programs / Refresh System / Ignore (a row's switch) | the model → `threads.run_for` | `power_requests.list_requests` then `split`, keeping its own half / `set_ignored`; one elevated run each (S13, S14, S17) |
| Quit | `joystick_gremlin.py` | `manager().shutdown()` |
| The Trace tab's **Screen Saver Mode** tick (S16) | Live Log Reader › Trace (page 01 S146) → `trace.set_screen_saver(on)` | while tracing, the listener, countdown, holds, actions and Refresh runs write trace lines |

## 5. Talks to

| Who | How | What |
|---|---|---|
| Windows Raw Input | `RegisterRawInputDevices` (usage page 0x01, usages 0x02 mouse and 0x06 keyboard, `RIDEV_INPUTSINK`) on a hidden top-level window | every keyboard and mouse event, from any program; `ExtraInformation` equal to `OWN_KEY_MARK` is the program's own and is skipped (S3); the device handle (none: sent by a program) and, once per handle, `GetRawInputDeviceInfoW(RIDI_DEVICENAME)` with the device's friendly name (SetupDi / `CM_Get_DevNode_Property` or the HID product string) (S18) |
| Windows settings | `HKCU\Control Panel\Desktop` `ScreenSaveTimeOut` (only when `SCRNSAVE.EXE` is set); the active power scheme's display-off time (`SUB_VIDEO` `VIDEOIDLE`, AC or DC by `GetSystemPowerStatus`) | Windows' wait time (S5, S8) |
| Windows idle and hold-off state | `GetLastInputInfo`; `SHQueryUserNotificationState` (busy, full-screen Direct3D, presentation mode); `CallNtPowerInformation(SystemExecutionState)` `ES_DISPLAY_REQUIRED`; locked workstation; `GetForegroundWindow` → `GetWindowThreadProcessId` → `QueryFullProcessImageNameW` | Windows' idle time (S9), the hold-offs (S7, S11, S15) and the full-screen program's name (S19) |
| Windows actions | the chosen screen saver file with `/s`, or `SC_MONITORPOWER` | the action (S4, S6) |
| HID devices | `SetupDi` with `HidD_GetHidGuid`, opened read-only, overlapped reads with bounded waits | Refresh Devices (S12) |
| `powercfg` | one elevated run (`ShellExecuteExW` "runas", `cmd /c powercfg /requests` and `/requestsoverride` into a temp file, bounded 60 s wait) | Refresh Programs, Refresh System and Ignore (S13, S14, S17) |
| `gremlin/windows_event_hook.py` (02) | `OWN_KEY_MARK` | the mark on the program's own keys (`keyboard.py`) and mouse input (`sendinput.py`, 06) |
| The program's settings and History (01, 08) | `cfg.register`, section "global", group "screen-saver-mode" | saved choices and their History entries (S2, S10) |
| `gremlin.threads`, `gremlin.clock` (01) | `threads.start`, `threads.main_timer`, `threads.run_for` | the threads below |
| `gremlin/trace.py` (01) | `trace.screen_saver_on()`, `trace.screen_saver(text)` | the trace lines (S16); errors also to `logging.getLogger("system")` |

## 6. Threads and timers

| Thread or timer | Started by | Does | Ends |
|---|---|---|---|
| Raw input thread | `InputClock.start` through `gremlin.threads.start`, only while Screen Saver Mode is on | its own hidden window and message loop; each raw input message only notes the time and its source (or skips the program's own input); a device's name is looked up once per device handle and cached, never per event (S18) | `InputClock.stop` (Screen Saver Mode off, or quit), bounded wait |
| 1 s timer on the main thread | `apply` through `gremlin.threads.main_timer`, only while on | `ScreenSaverMode.tick`: reads Windows' wait when the countdown starts, checks the hold-offs, fires the action once per idle period | `apply` with Screen Saver Mode off, `shutdown` |
| Window poll | the window, while open | reads `status()` once a second | window closed |
| Refresh Devices / Refresh Programs / Refresh System / Ignore | `threads.run_for(owner, name, work, deliver)` | the scan (about 4 s, bounded reads) or the elevated `powercfg` run (bounded 60 s wait); the result is delivered to the main thread; the buttons read "Checking… (4 s)" while busy | when the work returns, or `should_stop` |

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
- **S12** Under **What keeps the PC awake** the window should show three sections, stacked, each a framed box with its title, its button on the right, a one-line description and its list. The first, **Devices**, has a **Refresh Devices** button and the description "Devices that never go quiet and keep Windows' idle time at 0. Screen Saver Mode ignores them.": it reads every HID device for about 4 seconds, read-only, and lists the ones sending reports constantly, with the device name and reports per second. Its rows have no switch. The list is built fresh at each press from the devices connected then (nothing is hard-coded) and is empty until the first press. [decided 2026-11-15, user: 7, 20 "Refresh devices"; named "Refresh Devices" with a description, user 2026-11-15] [changed 2026-11-15, user: 5 "three rows grouped in sections"; batch 3, built 2026-11-15] (was: a Refresh Devices button with the description "Lists the devices that never go quiet and keep Windows thinking someone is using the PC.")

- **S13** The second section, **Programs**, has a **Refresh Programs** button (with the administrator shield) and the description "Programs keeping the display on. These hold Screen Saver Mode off until they stop. Needs administrator rights." It lists every caller in `powercfg /requests` (a program, a driver or a service) whose requests include Display. A caller that also asks to keep the PC awake (System, Awaymode or Execution) is listed here only, once, with "also keeps the PC awake" under its name and one switch. Windows gives this list only to administrators, so each press runs its own check with its own administrator prompt and fills only this list; refused, the section says so and nothing else happens. [decided 2026-11-15, user: 21 b; named "Refresh Programs" with a description, user 2026-11-15] [changed 2026-11-15, user: 3 a, 4 a, 5; batch 3, built 2026-11-15] (was: one Refresh Programs list of every program asking to keep the display or the PC awake, with the description "Lists the programs asking Windows to keep the display on. Needs administrator rights each time.")

- **S14** Each row in **Programs** and **System** (a program, a driver or a service) should have an **Ignore** switch. Programs are named by their exe file name; drivers and services by the full name Windows lists (the text after "[DRIVER] " or "[SERVICE] " in `powercfg /requests`, e.g. "USB Audio 2.0 (USB\VID_0DB0&PID_CD0E&MI_00\9&9c4d365&0&0000)"), marked "(driver)" or "(service)", with the detail line Windows gives under it. On, Gremlin adds Windows' override for that row's display and PC requests (`powercfg /requestsoverride PROCESS|DRIVER|SERVICE "<name>" ...`); off, it removes it. Each change asks Windows for administrator rights; refused, the switch goes back and the section says so. The message is per section: a Programs row "<name> is ignored: it no longer keeps the display on.", a System row "<name> is ignored: it no longer keeps the PC awake.", and switched off "<name> is no longer ignored." The ignored callers are Windows' own setting, so they hold while Gremlin is closed, and the window shows what Windows has. [decided 2026-11-15, user: 24 a] [changed 2026-11-15, user: 28 a; driver form checked on the user's PC 2026-11-15; service form not verified (SSM-SERVICE-UNTESTED)] (was: programs only; drivers and services had no switch) [changed 2026-11-15, user: 5; batch 3, built 2026-11-15] (was: an **Ignore this program** switch on each row of the one Refresh Programs list, with one message for every row)

- **S15** While any program asks Windows to keep the display on (Windows' combined display flag, read without administrator rights, as a video playing in a window or full screen does), Gremlin should not do the action; the countdown starts again when the flag goes off. Programs ignored with S14 don't set the flag. The status line says "On hold: a program is keeping the display on". [decided 2026-11-15, user: 22, 25 a; checked 2026-11-15: the flag on with a video playing in a window, off when paused]

- **S16** The Live Log Reader's Trace tab should have a **Screen Saver Mode** tick (next to HidHide's, page 01 S146; saved like the other ticks). While tracing is on and it is ticked, Screen Saver Mode writes trace lines (control "Screen Saver Mode"): the keyboard and mouse listener started, stopped or failed (with Windows' error); the countdown started (the wait and whether it came from Windows or was typed); each hold beginning and ending, with its reason; each action fired (which, and the result); a problem shown or cleared; settings applied; each Refresh Devices run (the devices found, each one's rate); each Refresh Programs and Ignore this program run: the exact `powercfg` command line, its exit code, refused or timed out, Windows' raw output (cut to 4 KB), the rows read from it and the check result; and the window's button presses and the message shown. Off, or with the tick off, nothing is written and it costs one check. Errors (exceptions, refusals, failed checks) always also go to the normal log, with tracing off too, so a failure is never silent. [decided 2026-11-15, user: "we need to add tracing to this portion of the program for debugging"; 29 a] [glossary: Trace]

- **S17** The third section, **System**, has a **Refresh System** button (with the administrator shield) and the description "Programs, drivers and services keeping the PC awake. They stop sleep, not the screens. Needs administrator rights." It lists the callers in `powercfg /requests` whose requests do not include Display and do include System, Awaymode or Execution. A caller already ignored (S14) with no current request is listed in the section matching its override's types in `powercfg /requestsoverride`: one with DISPLAY in Programs, any other in System. Each press runs its own check with its own administrator prompt and fills only this list; refused, the section says so. [decided 2026-11-15, user: "we need three buttons: Devices, Programs and System, so it's clear for users"; 3 a, 4 a, 5; batch 3, built 2026-11-15] [glossary: System, Refresh System]

- **S18** Next to "Your idle time" the status should say what last reset Gremlin's idle clock: "last reset by: <device name> (keyboard)" or "(mouse)" with "just now" or "N s ago", or "last reset by: input sent by a program, N times a minute" when the input came with no device (sent by a program, such as a remote-control program; N counts such inputs in the last 60 s). Gremlin's own input still doesn't count (S3). Device names come from Windows (the device path, then its friendly name or HID product string), looked up once per device and kept, never per event. This shows a jittery mouse or a program sending input as the reason the screen never rests. [decided 2026-11-15, user: 1 a; batch 3, built 2026-11-15] [glossary: last reset by]

- **S19** While the full-screen hold (S7) is on, the status should name the program in front when Windows gives its file name: "On hold: a full-screen program is in front (StarCitizen.exe)"; when Windows doesn't give it, the line is the plain one without a name. Tracing (S16) writes the reset source when it changes (not per event), the hold program, and each section's Refresh run. [decided 2026-11-15, user: 2 a; batch 3, built 2026-11-15]

## 9. Questions for the user

None open (Q1 off at first, Q2 "Refresh devices": answered 2026-11-15).

## 10. Known gaps

- ~~SSM-POWER-OFF-BROADCAST~~ (found and fixed 2026-11-15, user tried 1.0.38: the displays would not come back on until after a while; the main thread was stuck 35 s in Qt's message handling, system.log 11:01:26): power-off was broadcast (HWND_BROADCAST) to every window, this program's own Qt windows included, and each asked Windows to power off again, some after the user had woken the screens. Now ONE PostMessage to the input listener's own hidden window (`_power_window`), handled on the listener thread; a second power-off is held back 10 s (`POWER_OFF_GAP_S`) and retried; "displays powered off" / "screen saver started" are written to the normal log every time (S6). Tests: `test_ssm_core.py::test_power_off_goes_to_the_listener_window_not_every_window`, `::test_power_off_with_no_listener_window_sends_nothing`, `::test_power_off_is_logged_and_never_sent_twice_within_the_gap` (all three fail on the old code).

- ~~SSM-NOT-BUILT~~ (closed 2026-11-15: S1-S15 built; tests below; raw input checked on the user's PC: 2,071 keyboard and mouse messages in 20 s, all counted).
- SSM-HARDWARE (open, 2026-11-15): not yet tried from the installed program on the user's PC: the two actions fired by the countdown (S6; the screen saver and display off were tested by script, study section 6), the elevated Refresh Programs and Ignore this program (S13, S14; never run, parsers built from sample output), the full-screen hold (S7). Checked with the user after installing 1.0.38.
- SSM-SERVICE-UNTESTED (open, 2026-11-15): Ignore this program for a service row ([SERVICE] in `powercfg /requests`, S14) is built the same way as for drivers but not verified: the user's PC had no service request to try it on.
- ~~SSM-NEVER-WHILE-OFF~~ (found and fixed 2026-11-15, S5): with Screen Saver Mode off the window showed Windows' wait as "never" (Windows' display-off time was 300 s), because the status was filled only by the 1 s tick, which doesn't run while off; found when the user tried 1.0.38. `status()` now reads Windows' wait while off too.
- SSM-UAC-HOLD (open, small, 2026-11-15): the lock check treats any input desktop other than "Default" as locked, so a User Account Control prompt also holds the countdown while it is open.
- SSM-BATCH3-UNCONFIRMED (open, 2026-11-15): S12-S14 and S17-S19 (batch 3) are written as built pending the build agents' reports (SSM-CORE3, SSM-SCAN3, SSM-UI3); the friendly device name source (S18) and the foreground program name (S19) not yet checked on the user's PC.
- Robustness review, seen by the user 2026-11-15 (notes, no fix decided):
  - SSM-TV-IGNORES-OFF (open, note): some screens ignore Windows' power-off (`SC_MONITORPOWER`), for example HDMI TVs that stay on or wake themselves; Power off displays then does nothing visible. The Screen saver action still works on them.
  - SSM-CLOSED (open, note): Screen Saver Mode works only while Gremlin Platforms is open (S2, S9); closed or crashed, nothing protects the screen (Windows' own timers stay stopped by the devices).
  - SSM-STUCK-PRESENTATION (open, note): Windows' full-screen or presentation state can stay on after the program that set it is gone or in the background, holding the countdown (S7) indefinitely; S19 now names the program Windows reports, so the user can see what holds it.
  - SSM-PROGRAM-INPUT (open, note): a jittery mouse or a program sending keyboard or mouse input (S3: it counts) keeps Gremlin's own clock at 0 too; S18 now shows the device or "input sent by a program, N times a minute" as the reason.

## 11. Size and test coverage

Tests (2026-11-15): `test/unit/test_ssm_core.py` (23), `test/unit/test_ssm_scan.py` (33), `test/unit/test_ssm_ui.py` (24, with `ssm_ui_smoke.py`, `ssm_ui_fakes.py`), `test/unit/test_ssm_e2e.py` (33, two runs: the restart carries the settings). Earlier plan: `test/unit/test_ssm_*.py`: the clock counts keyboard and mouse only and skips the program's own input (`InputClock.note_input(own=True)`); the wait time follows Windows and the typed time (fake `WindowsApi`); the action fires once per idle period, and holds off while locked, in full screen and while the display flag is on (fake clock and fake `WindowsApi`; tests never start the screen saver or turn displays off); off registers nothing and starts no timer; the scans parse their results with a fake `runner` (no test elevates or runs `powercfg`); the Tools item opens the window; the window off-screen. Help: `test_help_guide.py`, `test_help_links.py`, `test_help_links_resolve.py`. Batch 2 (2026-11-15, counts to confirm from the agents' reports): `test/unit/test_ssm_trace.py` (new: the tick, the lines while ticked, nothing while off, errors in the normal log), `test_ssm_core.py` (status while off carries Windows' wait; trace lines), `test_ssm_scan.py` (driver and service rows, kind, name checks, the quoted command, trace lines), `test_ssm_ui.py` and `test_ssm_e2e.py` (driver rows get the switch). Batch 3 (2026-11-15, counts to confirm from the agents' reports): `test_ssm_core.py` (the last reset source and age, program input per minute, Gremlin's own input not counted, the device name looked up once per handle, the hold program from a fake `foreground_program()`), `test_ssm_scan.py` (`split`: Display rows, System rows, `also_awake`, ignored callers placed by override types), `test_ssm_ui.py` and `test_ssm_e2e.py` (the three sections and their object names, each Refresh fills only its own list with its own run, the per-section messages, last reset by and the hold program on the status line). Help: `test_help_*.py`; glossary: `test_glossary_words.py`.

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
| D-12-SSM-SECTIONS (2026-11-15, user: "we need three buttons: Devices, Programs and System, so it's clear for users"; 5 "three rows grouped in sections"; mock-up approved) | Three stacked sections under What keeps the PC awake, each a framed box with title, button, description and list: Devices (Refresh Devices), Programs (Refresh Programs), System (Refresh System) (S12-S14, S17) |
| D-12-SSM-LAST-RESET (2026-11-15, user: 1 a) | The status says what last reset Gremlin's idle clock: the device name and kind, or "input sent by a program, N times a minute"; Gremlin's own excluded (S18) |
| D-12-SSM-HOLD-PROGRAM (2026-11-15, user: 2 a) | The full-screen hold names the foreground program's file name when Windows gives it (S19) |
| D-12-SSM-OWN-PROMPTS (2026-11-15, user: 3 a) | Refresh Programs and Refresh System each run their own check with their own administrator prompt and fill only their own list (S13, S17) |
| D-12-SSM-BOTH-KINDS (2026-11-15, user: 4 a) | A caller asking for the display and the PC is listed in Programs only, marked "also keeps the PC awake", with one switch (S13) |
