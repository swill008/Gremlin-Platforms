# Better tracing: window, tray, pages, display and stalls (PLAN-TRACE)

Read-only plan, 2026-11-19, scout PLAN-TRACE (13:02 to 13:05 by `date +%H:%M`).
Nothing here is approved. Spec wording below is PROPOSED only.
Companion plan: PLAN-WIN (the tray fix itself). The interface between the two
is the "Window:" line format and the `window_trace` calls named in section 4.

## 1. Why

The user saw a blank main window: the pages were unloaded because Main.qml's
`trayed` (qml/Main.qml:148) stayed true while the window was showing. Nothing
recorded tray enter/leave, page load/unload or window show/hide/move, so the
cause could not be proven. Two facts make today's tools unable to answer it:

1. Every trace kind is off until Tracing is switched on, and Tracing is never
   saved on (spec 01 S147; gremlin/trace.py:17 "Tracing is always off at
   start"). A problem that happens before anyone switches it on leaves nothing.
2. system.log is at Warning by default (01 S97; option `log-level` default
   "Warning", joystick_gremlin.py:869; level applied to logger and handler,
   joystick_gremlin.py:197, :207). Routine lines are Info (01 S103), so an
   "always-on" Info line about the tray **would not be written** with default
   settings. Any always-on line must either be Warning (only for something
   wrong) or go to an in-memory ring that is written out when needed.

## 2. What exists today (verified)

| What | Where written | On when | Code |
|---|---|---|---|
| Trace points RAW, WIRING, OUTPUT, BLOCKED, EVENT, HIDHIDE, SCREEN SAVER, OSC, OUT OF STEP, MOUSE (ONE-TIME OT-5) | 5000-line in-memory list for the Trace tab + `logs/trace.log` (rotating, Max size 1-1000 MB, one backup) | only while Tracing is on and the row is ticked | gremlin/trace.py:41-53 (points), :576 `_add`, :1198 logger at INFO |
| Points filter on the Trace tab | — | — | gremlin/ui/trace_model.py:27-38 `POINTS`; qml/LiveLogTrace.qml:217 |
| Trace tab rows: devices, Out-of-step, HidHide, Screen Saver Mode, Mouse, OSC areas | saved ticks (settings `debug/trace`) | — | gremlin/ui/trace_model.py:251-305 |
| Screen Saver Mode trace (page 12 S16) | SCREEN SAVER lines, control "Screen Saver Mode" | Tracing on + its tick | gremlin/screen_saver_mode.py:66 `_trace`, about 41 call sites (:1440-:1988): listener start/stop, wake devices, holds, actions fired, keep-off start/end/re-send, presses |
| Log When Not Responding (01 S112-S113) | system.log, Warning: "Not responding for N s" + every thread's stack, then "Responding again after N s" | option, off by default | gremlin/watchdog.py:85-99 |
| system.log, user.log, event.log, qt.log, crash.log (01 S96-S101) | logs folder | always (level per option) | joystick_gremlin.py:195-215 |
| Save Diagnostics zip (01 S132) | logs incl. trace.log, settings, devices, versions | on demand | gremlin/diagnostics.py |

Gaps that matter for the blank-window case (verified by reading the code):

- `SystemTray._window_mode_changed_cb` (gremlin/ui/system_tray.py:243-267)
  flips `self._trayed` and calls `tray_memory.enter_tray` / `leave_tray` with
  no log line. `tray_memory.enter_tray` returns early, silently, when the
  window is already visible (gremlin/ui/tray_memory.py:29-30), and calls QML
  `enterTray` through `invokeMethod` without checking the result (:31, :37).
- Main.qml `enterTray` / `leaveTray` (qml/Main.qml:152-160) and the nine page
  Loaders (`_statusLoader` :2427 `active: !_root.trayed`, `_outputLoader`
  :2632, ... `_settingsLoader` :2777, all gated by `_configLive` or `trayed`)
  write nothing.
- No window move, screen change, minimize/restore or activation is recorded
  anywhere (gremlin/ui/window_placement.py only saves/restores the place).
- Display power: Screen Saver Mode receives Windows' display state
  (`GUID_CONSOLE_DISPLAY_STATE`, gremlin/screen_saver_mode.py:802-803, :981,
  :1220) **only while Screen Saver Mode is on**, and `on_display_state`
  (:1882) writes no trace line for an ordinary on/off report (only re-sends
  and waits are traced). With Screen Saver Mode off nothing sees display power
  or sleep/resume.
- The watchdog's dump has the main thread's stack but not the window, tray or
  page state, and it is off by default.

## 3. Proposal

### 3a. A new trace area "Window" (trace-only, ticked)

A new Trace tab row **Window** (next to HidHide and Screen Saver Mode) with a
new point **WINDOW** and control column "Main window" (or the page name for
page lines). While Tracing is on and Window is ticked it writes:

| Line (detail column) | Source (proposed) |
|---|---|
| `shown (Windowed)` / `hidden` / `minimized` / `maximized` / `restored` / `full screen` | `QWindow.visibilityChanged`, `windowStateChanged` |
| `moved to 120,80 1400x900 on DISPLAY2 (scale 150%)`, once after the move settles (500 ms quiet) | `xChanged`/`yChanged`/`widthChanged`/`heightChanged` + one main-thread QTimer |
| `screen changed: DISPLAY1 → DISPLAY2` | `QWindow.screenChanged` |
| `screen added DISPLAY3 2560x1440 at 2560,0` / `screen removed DISPLAY3` / `primary screen now DISPLAY1` | `QGuiApplication.screenAdded/screenRemoved/primaryScreenChanged` |
| `active` / `inactive` | `QWindow.activeChanged` (rate limited: at most 1 line a second, with "(N changes between)") |
| `tray: entered (pages unloading; Device Bindings kept: unsaved edits)` / `tray: left (pages loading)` / `tray: enter skipped (window visible)` | system_tray.py `_window_mode_changed_cb` and tray_memory.py `enter_tray` / `leave_tray` |
| `tray: release done` / `release skipped (window visible)` | tray_memory.py `release` |
| page lines, control = page name: `Home loaded` / `Home unloaded` / `Device Bindings: Loader active but item null (status Error)` | each page Loader (see 3e) |
| `displays off` / `displays on` / `displays dimmed`, `sleeping` / `resumed` | tray's own window procedure (see 3d) |
| `stall began: no main-loop tick for 5 s` / `stall ended after 7 s` | watchdog (see 3c) |

Cost: every source is a Qt signal on the main thread or a rare Windows
message; each tap is one bool check when off (as trace.py's other writers,
trace.py:409-418 pattern). Window lines are never per input event.

### 3b. Always-on in-memory ring ("Recent window events")

**Recommended: yes.** A small ring, `trace.recent`, of the last 200 Window and
Screen Saver Mode step lines, kept **whether or not Tracing is on**. It is
never written to a file on its own. It is written out:

1. by the new **Save Window State** command (3c),
2. with the watchdog's "Not responding" dump (as a block after the stacks),
3. into the Save Diagnostics zip as `recent-window-events.txt`,
4. to system.log at Warning when the program itself detects the blank-window
   state (window visible while pages are unloaded; PLAN-WIN's check), so the
   lead-up is in the log next to the warning.

Why it is worth it: today's question ("what happened before the window went
blank?") is only answerable from events that happened before anyone thought
to switch Tracing on. The 5000-line `_lines` list already exists but only
fills while Tracing is on (trace.py:99-101, `_add` called only behind
`_enabled` checks).

Cost: one `collections.deque(maxlen=200).append((time, control, text))` per
event, no file, no lock beyond deque's own atomic append; about 40 KB worst
case. Window events are a few per minute; Screen Saver Mode step lines are
per step, not per input event, **except** `press:` / `not counted:`
(screen_saver_mode.py:1986-1988), which may be per counted press (unverified
frequency); those stay trace-only and are kept out of the ring.

Which events go to the ring: everything in the 3a table except `active` /
`inactive` and page lines for room/tab switching that are not tray related
(keep the ring for the rare, telling events). Screen Saver Mode: listener
start/stop/failed, keep-off start/end/re-send, action fired, hold began/ended.

### 3c. "Save Window State" command (snapshot; changes nothing)

A Debug menu item **Save Window State** (from the one command list, 01 S65,
qml/main_commands.js near :135 `debug.tracing`) and a button on Help ›
Save Diagnostics' Debug tab. It writes one block to system.log at Warning
(so it is kept at the default level), and the same block to trace.log as a
WINDOW line when Tracing is on:

```
Window state (asked for):
  window: visible yes, visibility Windowed, state normal, 120,80 1400x900, screen DISPLAY2 (150%), active yes
  tray: icon shown yes, tray says hidden-to-tray no, page says trayed YES  <-- differ
  pages: room configuration, tab physical; loaded: Device Bindings (Ready); unloaded: Home, Scripts, Profile Settings
  displays: on (last report 12:40:03), last sleep/resume: none this session
  Screen Saver Mode: on, keeping displays off no
  Recent window events (last 200): ...
```

The "differ" mark compares `SystemTray._trayed` (Python) with Main.qml
`trayed` (read with `QQmlProperty`), which is exactly today's question. The
command reads on the main thread, takes no locks held elsewhere and has no
waits. It also goes into the Save Diagnostics zip as `window-state.txt`.

Watchdog: on "Not responding" the main thread is stuck, so the snapshot
cannot be read there. Instead the watchdog appends the ring (3b) and the
**last known** state, kept as plain Python values updated by the Window taps
(no Qt calls from the watchdog thread). Stall begin/end also go into the
ring and, when ticked, the trace as WINDOW lines. The watchdog stays off by
default (01 S112 unchanged); see question 2.

### 3d. Display power and sleep/resume without Screen Saver Mode

The tray's own window is a real top-level window (`CreateWindowEx` with
`WS_OVERLAPPED`, system_tray.py:146-159), not a message-only window, so it
receives `WM_POWERBROADCAST` broadcasts. Proposal: add `WM_POWERBROADCAST` to
its window procedure dict (system_tray.py:136-142) and register
`GUID_CONSOLE_DISPLAY_STATE` for that window with
`RegisterPowerSettingNotification` (reusing the decoder
`screen_saver_mode.display_state_on`, :981). This only records; it does not
change Screen Saver Mode's own listener. Lines: `displays off/on/dimmed`,
`sleeping` (PBT_APMSUSPEND), `resumed` (PBT_APMRESUMEAUTOMATIC). These are
rare and go to the ring always. Unverified: whether Windows delivers display
state to two registrations in one process (it should; one registration per
window handle), to check in the build.

### 3e. Page Loaders: one traced Loader type

Design for change: rather than nine hand-written handlers, a small QML type
`PageLoader.qml` (a Loader with `property string traceName`) reports
`onActiveChanged`, `onLoaded` and `onStatusChanged` (Error) to one Python
slot `windowTrace.page(name, what)`. Main.qml's nine page Loaders
(:2427-:2782) become PageLoaders with names "Home", "Output", "Logical
Device", "OSC", "Device Bindings", "Keyboard", "Xbox", "Scripts", "Profile
Settings" (glossary page names to confirm). A guard test fails when a page
Loader in Main.qml is a plain Loader without a trace name.

### 3f. Always-on system.log lines (minimal, shared with PLAN-WIN)

Only at Warning and only when something is wrong (S103 keeps routine lines
Info, which the default level drops):

- `Window: shown while its pages are unloaded (tray state out of step); loading them` — PLAN-WIN's detection/fix; followed by the ring.
- `Window: hiding to the tray failed: <why>` (invokeMethod returned false, or an exception in enter/leave).

Routine `Window: hidden to the tray` / `Window: shown from the tray` lines go
to the ring and, when ticked, the trace; at Info they would be dropped at the
default level anyway. If PLAN-WIN proposes Info lines, they should use the
same `Window: ` prefix so Find catches both.

## 4. Interface (contract for the build)

`gremlin/ui/window_trace.py` (new, owner of window tracing):

- `install(window: QQuickWindow, engine) -> None` (main thread, start-up):
  connects the Qt signals in 3a, the move-settle timer.
- `note(control: str, text: str, ring: bool = True) -> None` (any thread,
  never raises): to the ring when `ring`, to trace as WINDOW when on+ticked.
- `page(name: str, what: str)` slot exposed to QML as context property
  `windowTrace`.
- `state_text() -> str` (main thread): the snapshot of 3c.
- `last_known() -> dict` (any thread): plain values for the watchdog.

`gremlin/trace.py` additions: `WINDOW = "WINDOW"`, `window_ticked()`,
`set_window(on)`, `window_on()`, `window(control, text)`; `RECENT_MAX = 200`,
`recent(control, text)` (always), `recent_lines() -> list[str]`; settings key
`debug/trace/window`. `screen_saver(text)` also calls `recent()` for the step
lines listed in 3b (screen_saver_mode.py passes `ring=False` for presses).

## 5. Proposed spec wording (not written)

Page 01, Trace section, new statements:

- **S174** (proposed) The Trace tab should have a **Window** row next to HidHide and Screen Saver Mode (saved like the other ticks). While Tracing is on and it is ticked, the program writes WINDOW lines (control "Main window", or the page's name): the main window shown, hidden, minimized, maximized, restored and full screen; moved or resized (one line after it settles, with its place, size and screen); its screen changed; screens added or removed and the primary screen changed; active or inactive (at most one line a second); hidden to the tray and shown from it (which pages unload and which stay, and why), and each step that is skipped; each page loaded and unloaded, and a page that fails to load; the displays off, on or dimmed; the PC going to sleep and resuming; and the start and end of a main-loop stall seen by Log When Not Responding. None of these is written per input event.
- **S175** (proposed) Whether Tracing is on or not, the program should keep the last 200 window and Screen Saver Mode step events (S174, 12 S16, not keyboard or mouse presses) in memory only. They are written out by Save Window State (S176), after a "Not responding" dump (S113), into the Save Diagnostics zip (S132) and after a "Window:" warning in system.log. Keeping them costs no file and no thread.
- **S176** (proposed) Debug › **Save Window State** should write the main window's state to system.log (kept at the default Warning level) without changing anything: visible, visibility and place; screen and scale; whether the tray and the window agree that it is hidden to the tray; the open room and tab and which pages are loaded; the last display and sleep reports; Screen Saver Mode on or off; and the recent events (S175). The same text goes into the Save Diagnostics zip as window-state.txt.
- **S177** (proposed) The program should write a Warning line beginning "Window:" to system.log only when the window and its pages disagree (shown while its pages are unloaded) or hiding to the tray fails, followed by the recent events (S175). [shared with PLAN-WIN]

Changed (proposed):
- **S146** add "A **Window** row next to Screen Saver Mode has its own tick (S174)".
- **S149** Points filter list adds **Window** (and Screen Saver Mode, which the code already has, trace_model.py:33, but S149's list omits; this is a spec catch-up).
- **S113** add "followed by the recent events (S175) and the last known window state".
- **S132** add `window-state.txt` and `recent-window-events.txt` to the zip.

Page 12: **S16** add "Its step lines (not presses) are also kept in the recent events (01 S175) whether or not Tracing is on." No other change.

Glossary (claude/glossary.md, new row): Window tracing (01 S174-S177): the
**Window** row and point **WINDOW**; **Save Window State** (Debug menu);
**recent events** (the last 200 kept in memory). Avoid: "window log",
"snapshot dump", "flight recorder", "black box".

## 6. Tests that fail on today's code

All drive the real path (QQuickWindow from the real Main.qml where noted).

1. `test_window_trace.py::test_hiding_to_the_tray_writes_window_lines` — tick Window, Tracing on, hide the window with the tray present: WINDOW lines "tray: entered" and "Home unloaded"; show it: "tray: left", "Home loaded". Fails today: no WINDOW point.
2. `::test_recent_events_are_kept_with_tracing_off` — Tracing off, hide and show: `trace.recent_lines()` holds both; trace.log not created. Fails: no ring.
3. `::test_save_window_state_marks_tray_and_page_out_of_step` — set QML `trayed` true with the window visible: the block says the two differ; written at Warning with default level. Fails: no command.
4. `::test_enter_tray_skipped_is_recorded` — `enter_tray` on a visible window writes "enter skipped". Fails: silent return (tray_memory.py:29-30).
5. `::test_move_writes_one_line_after_it_settles` — 20 x/y changes then the settle time via gremlin.clock: one "moved to" line.
6. `::test_screen_added_and_removed_are_recorded` — fake QScreen signals.
7. `::test_display_off_on_and_resume_are_recorded_without_screen_saver_mode` — post WM_POWERBROADCAST to the tray's window procedure.
8. `test_watchdog.py::test_a_freeze_dump_includes_the_recent_events` — fails today.
9. `test_diagnostics_zip.py::test_the_zip_has_window_state_and_recent_events`.
10. `test_page_loaders_traced.py::test_every_page_loader_has_a_trace_name` (guard, design for change).
11. `test_trace_tab.py::test_window_row_and_point` (row, tick saved, Points filter).
12. `test_ssm_trace.py::test_step_lines_go_to_recent_presses_do_not`.

## 7. Files and owners (proposed split)

| Group | Files | Owner page |
|---|---|---|
| A. trace core | gremlin/trace.py (WINDOW, tick, ring) | 01 |
| B. window taps | new gremlin/ui/window_trace.py; gremlin/ui/tray_memory.py; gremlin/ui/system_tray.py (power messages, notes) — **shared with PLAN-WIN**, sequence after or merge into one owner | 01 |
| C. QML | new qml/PageLoader.qml; qml/Main.qml (9 Loaders); qml/main_commands.js (Save Window State) — Main.qml **shared with PLAN-WIN** | 01 |
| D. Trace tab | gremlin/ui/trace_model.py, qml/LiveLogTrace.qml | 01 |
| E. watchdog + diagnostics | gremlin/watchdog.py, gremlin/diagnostics.py | 01 |
| F. Screen Saver Mode ring | gremlin/screen_saver_mode.py (`_trace` passes ring flag) | 12 |
| G. tests (above) | test/unit/... | — |
| H. spec, map, glossary, Help | claude/program-map/01, 12, glossary.md, qml/help/tools.js `tools-trace` | — |

joystick_gremlin.py gets one `window_trace.install(...)` call (lead-held).

## 8. Risks

- Hang-proofing (01 S90-S95): no new thread; the move-settle and rate limits
  use a main-thread QTimer and `gremlin.clock`. The watchdog only reads plain
  values (no Qt calls off the main thread). Snapshot does no waits.
- Writing trace.log from the main thread is synchronous file I/O; acceptable
  because Window lines are rare (same as existing EVENT lines).
- `active`/`inactive` and move events can be bursty (dragging): rate limit
  and settle timer are required, test 5.
- Two power-setting registrations in one process: unverified, check in build.
- Main.qml and system_tray.py overlap with PLAN-WIN: one owner per file, so
  either the tray fix lands first and this batch builds on it, or both go to
  one agent per file.
- MOUSE / click_trace (ONE-TIME OT-5) is unrelated; do not extend it.

## 9. Effort (timings.md)

Kinds from claude/timings.md "Rules of thumb": Agent fix / feature / docs
"3-8 min per agent; a batch of parallel agents ~10 min"; end to end "agents
(~10 min) + lead checks and map (~5 min) + full run (~5 min) + commit/push
(~2 min) + CI (~10 min, in the background)". With about 7 agents (groups
A-H, B and C after PLAN-WIN's files): about 10 min of agents + 5 min lead
checks and map + quick tests (no timing kind for quick tests yet; rough
guess 2 min) + 2 min commit = about 20 min, plus about 10 min CI in the
background. If staggered behind PLAN-WIN's batch, add that batch's time.

## 10. Questions for the user

1. **Keep recent window events always in memory?**
   The ring (3b) is what would have answered today's question; it costs no
   file or thread.
   - a) Yes, last 200 events (recommended).
   - b) No, trace only when Tracing is on (today's model).
2. **Should a short stall line be always on?**
   Log When Not Responding is off by default (S112), so stalls are not seen
   unless it is switched on.
   - a) Keep it as is; the ring records stalls only when the option is on (recommended; no spec reversal).
   - b) Always record stall begin/end in the ring (no stacks) even with the option off; changes S112's meaning.
3. **Where does Save Window State live?**
   - a) Debug menu item + inside Save Diagnostics (recommended).
   - b) Only inside Save Diagnostics.
