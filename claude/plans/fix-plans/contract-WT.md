# Batch W + T contract (2026-11-19): window/tray fix, Window tracing, Timing probes

Approved by the user 2026-11-19: "approved as recommended" (answers 1a-9a in claude/plans/fix-plans/README.md;
plans: window-tray.md, tracing.md, thread-probes.md). Thread move NOT in this batch.

## Approved answers that shape this batch
1a Windows shows the hidden window by itself -> keep it shown, leave the tray, load the pages.
2a Tray steps go to the recent-events memory and the Window trace; system.log gets a Warning "Window: ..."
   only when a mismatch is caught and fixed, or hiding to the tray fails (system.log default level is Warning).
3a Last 200 window + Screen Saver Mode step events kept in memory always (not presses).
4a Stalls: Log When Not Responding stays as is (S112 unchanged); stall begin/end go to the memory only when
   that option is on.
5a Debug > Save Window State, and its text in the Save Diagnostics zip.

## Spec numbers (page 01; last existing is S173) - DOCS-WT writes them, others cite them
- S174 tray follows what Windows shows (Windows-shown window: leave the tray, load the pages). Decision D-01-TRAY-TRUTH.
- S175 "Window:" Warning lines in system.log only when the window and its pages disagree (fixed) or hiding to the
  tray fails, followed by the recent events.
- S176 Trace tab Window row / WINDOW point (list in tracing.md 3a; tray steps, page loads, display/sleep, stalls).
- S177 recent events: last 200, always, memory only; written out by S178, a Not responding dump, Save Diagnostics,
  and after a "Window:" warning.
- S178 Debug > Save Window State.
- S179 Trace tab Timing row / TIMING point (thread-probes.md section 2).
- Amended: S85 (hide once the minimize has finished), S87 (pages reload whenever shown, by Gremlin or Windows),
  S113 (dump adds recent events + last known window state), S132 (zip adds window-state.txt,
  recent-window-events.txt), S146/S148/S149 (Window and Timing rows/points; S149 catch-up: Screen Saver Mode filter).
  Page 12 S16 (step lines also go to recent events). Decision D-01-WINDOW-TRACE.

## Interfaces (names are fixed; code against them even before the owner lands them)

### gremlin/trace.py (owner T-CORE)
- `WINDOW = "WINDOW"`, `TIMING = "TIMING"` point names, in the points list.
- `window_ticked() -> bool`, `set_window(on: bool)`, `window_on() -> bool` (Tracing on AND ticked);
  saved under settings debug/trace key `window`, like the other area ticks; runs on_change hooks.
- `window(control: str, text: str) -> None`: WINDOW line when window_on(); any thread; never raises.
- `RECENT_MAX = 200`; `recent(control: str, text: str) -> None`: always, any thread, never raises
  (deque(maxlen)); `recent_lines() -> list[str]` formatted like trace lines ("HH:MM:SS.mmm  control  text").
- `timing_ticked()`, `set_timing(on)`, `timing_on()` (Tracing on AND ticked), key `timing`;
  `timing(text: str, warning: bool = False) -> None` TIMING line; never raises.
- The Screen Saver Mode writer gains `ring: bool = True`: when True the line also goes to `recent()`.

### gremlin/trace_timing.py (new, owner T-TIMING)
- `on: bool` module flag kept in step with `trace.timing_on()` (on_change hook); cost when off = one bool check.
- `counter` = `time.perf_counter_ns` (tests replace it).
- `stamp_rx(event, t0: int, t1: int) -> None` sets `event.t_rx = (t0, t1)`.
- `dispatch(event) -> None` at dispatch start (t2; queue wait = t2 - t1; stall line when > 50 ms, once per episode).
- `begin(event) -> None` / `end() -> None` around actions (thread-local current event).
- `output() -> None` at the first output write per event (end to end = t5 - t0).
- Summary TIMING line every 10 s while there were events (main-thread QTimer via gremlin.threads.main_timer
  or gremlin.clock; never a new thread), and at Tracing off / Stop. Format in thread-probes.md section 2
  (the line carries the date).
- `Event.t_rx: tuple[int, int] | None = None` (owner T-STAMPS adds the attribute in event_handler.py).

### gremlin/ui/window_trace.py (new, owner T-WIN)
- `note(control: str, text: str, ring: bool = True) -> None`: any thread, never raises; `trace.recent` when ring,
  `trace.window` when on. Control is "Main window" or the page name.
- `warn(text: str) -> None`: system.log WARNING "Window: <text>" then the recent lines; never raises.
- `set_tray_state_reader(fn: Callable[[], bool]) -> None`: SystemTrayIcon registers a reader of its own
  in-tray flag (for "differ" in the state text).
- `install(window, engine) -> None` (main thread, start-up): Qt signal taps of tracing.md 3a (visibility,
  state, move settle 500 ms, screen changed/added/removed/primary, active rate-limited 1/s) and the QML context
  property `windowTrace` with slot `page(name: str, what: str)`.
- `state_text() -> str` (main thread, no waits): the Save Window State block (tracing.md 3c), reads Main.qml
  `trayed` with QQmlProperty; marks "<-- differ" when it disagrees with the tray reader.
- `save_state() -> None` (slot `saveWindowState` for QML): writes state_text() to system.log at WARNING and a
  WINDOW line when on.
- `last_known() -> dict` (any thread): plain values kept by the taps, for the watchdog.

### gremlin/ui/system_tray.py + tray_memory.py (owner W-CODE)
- One truth: `SystemTrayIcon._sync_tray(reason: str)` decides from IsWindowVisible/IsIconic of the main window;
  `tray_memory.enter_tray/leave_tray` return bool (the isVisible early return moves to _sync_tray).
- Native event filter on the main window's HWND (WM_SHOWWINDOW wParam=1, WM_WINDOWPOSCHANGED+SWP_SHOWWINDOW):
  native visible while Qt says hidden -> queued (QTimer.singleShot 0) setVisibility to the native state, so
  the visibility signal fires and the pages load; `window_trace.warn("shown by Windows while hidden to the
  tray; showing it and loading its pages")`. Expose backstop in the existing eventFilter.
- Minimized -> deferred hide (`QTimer.singleShot(0, ...)`, re-checks still Minimized); never hide() inside
  the visibility signal.
- Notes via `window_trace.note("Main window", "tray: entered (minimize|X|tray menu)" / "tray: left (tray click|
  tray menu|Windows showed it|...)" / "tray: enter skipped (window visible)" / "tray: release done|skipped")`.
- WM_POWERBROADCAST on the tray's own window + RegisterPowerSettingNotification(GUID_CONSOLE_DISPLAY_STATE),
  decoder `screen_saver_mode.display_state_on`: notes "displays off|on|dimmed", "sleeping", "resumed".
  Unregister on destroy. Records only.
- `window_trace.set_tray_state_reader(lambda: self._trayed)`.

### Main.qml / PageLoader.qml / main_commands.js (owner T-WIN)
- New `qml/PageLoader.qml`: Loader with `property string traceName`; reports active changes, loaded, and status
  Error to `windowTrace.page(traceName, what)` ("loaded", "unloaded", "failed to load").
- Main.qml's nine page Loaders become PageLoaders with glossary page names. Guard test: every page Loader in
  Main.qml has a traceName.
- Command `debug.saveWindowState` "Save Window State" in the Debug menu (main_commands.js + Main.qml menu).

## Rules for every agent (from .claude/CLAUDE.md; pass on)
- Change control: the spec is claude/program-map/ (section 8 + section 12 decisions). Read the page for your
  files. This contract is the user-approved change; anything beyond it -> stop and report to the lead.
- One owner per file (table in the lead's message). Need a change in someone else's file -> report it to the
  lead, don't edit it. Shared: test/conftest.py and gremlin/threads.py are lead-held.
- No commits, no pushes, no builds (program or installer), no installs. Never touch the running Gremlin
  process or its windows, never send real input, never touch real devices/pnputil/helper.
- Program-code runs and tests: temp USERPROFILE (never the real Gremlin Platforms folder), offscreen Qt
  unless a test needs a real window; real windows go off the main screen (secondary monitor or off-screen
  position, opacity 0) and never steal focus.
- Live output: `PYTHONUNBUFFERED=1 <command> 2>&1 | python tools/agent_log.py <AGENT>` for EVERY shell command.
- Multi-core testing (user 2026-11-19): run tests only through `python test/run_tests.py <your test files>`
  (it spreads them over the cores, 6 parts); never a bare multi-file pytest. The runner lets one run at a time
  on the PC, so keep runs targeted (your files only), never the full run. Prove each new test fails on the old
  code (git stash of your own change, or reasoning shown) and passes on the new; then stop proof runs.
- Before a command expected over 3 min, log `AGENT: <step>, expect ~N min, why`.
- New code: threads only via gremlin.threads, bounded waits, gremlin.clock; never raise from trace writers.
- Lint your files: `python -m ruff check <files>` and `python tools/pyright_baseline.py` (or the repo's pyright
  check) must not get worse.
- Report: start/end clock (`date +%H:%M`), files changed, tests added (fail-old/pass-new proof), test command
  results, anything needed from other owners, map entries for your files (section 2 files / 3 owns / 4 entry
  points / 5 talks to / 11 tests) for DOCS-WT.
