# Thread batches 2-5 contract (2026-11-19): input -> wiring -> output on the input thread

Approved by the user 2026-11-19 ("approved as recommended" + "you have been approved for all batches ... finish
the build and testing without my intervention"). Plans: thread-input.md (design, sections 2 and 4),
thread-ui.md (sections 1-3). Batch 1 (gremlin/input_thread.py, threads.start_qt, guards) is built.
Approved answers: 6a the running profile is a copy taken at Run (edits apply at the next Run); 7a text-to-speech
stays on the main thread (explicit hop); 8a the not-responding watchdog also watches the input thread;
tests: existing tests run the wiring inline on their own thread, new end-to-end tests use the real thread.

## What runs where afterwards
| Work | Thread |
|---|---|
| claim gate (InputModuleRuntime), EventHandler dispatch, actions, Logical Device re-entry, ButtonReleaseActions | input thread |
| run_scope timers: Tempo, Double Tap, Smart Toggle, pulse release, vJoy keep-alive | input thread (QTimer owned by it) |
| ModeManager stack changes (Change Mode, timer actions, Run start/end, toolbar pick) | input thread |
| Pause / Resume / toggle | input thread |
| Run start (script import, callbacks, connections) and Stop stages | input thread via RunControl |
| TTS speak, Load Profile hand-off, Backend calls, dialogs, notifications to QML | main thread (explicit hop) |
| macros, mouse motion, relative loops, script timers, audio, OSC server | unchanged (own threads) |

## Interfaces (fixed names)

### gremlin/threads.py (owner THR-TIMERS)
- `thread_timer(name: str, seconds: float, fn: Callable[[], None]) -> handle` with `.cancel()` and `.is_alive()`:
  a QTimer created on the CALLING thread when that thread has a Qt event loop
  (`QtCore.QThread.currentThread().eventDispatcher() is not None`; main or input thread), else a named
  threading timer (today's fallback). Listed so `shutdown()` cancels it on its own thread (queued call).
  `main_timer` stays for UI-only timers.
- `main_call(fn: Callable[..., None], *args) -> None`: queued to the app (main) thread; fire and forget;
  inline when already on main.
- `has_event_loop() -> bool` helper (the eventDispatcher check).

### gremlin/code_runner.py (owner THR-RUNTIME)
- `class RunControl(QtCore.QObject)` living on the input thread; slots `start(profile_snapshot, mode: str)`,
  `stop()`; signals `runStarted(bool, str)` (ok, error text), `runStopped()`; accessor `run_control()`.
- Profile snapshot at Run (answer 6a): the Run uses a copy of the profile taken when Run starts
  (e.g. serialise/deserialise, or the Profile's own copy if one exists); edits during a Run don't reach it.
- `adopt_runtime_objects()`: called once after `input_thread.start()`; `moveToThread(input thread)` for
  EventHandler, InputModuleRuntime, ModeManager, RunControl (before their connections are made for the Run).
  Uses `input_thread.call_wait` where it must run on the input thread.
- Every runtime slot on the path is a QObject method or connected with an explicit ConnectionType (R8).

### gremlin/event_handler.py, gremlin/modules/runtime.py (owner THR-RUNTIME)
- EventHandler / InputModuleRuntime on the input thread; `is_active` emitted there (queued to the UI).
- Pause API callable through `input_thread.call(EventHandler().pause|resume|toggle_active ...)` (use the
  existing method names; report them).
- Timing stamps (trace_timing) stay where they are: `_on_hid` is still the dispatch stamp point.

### joystick_gremlin.py (owner THR-RUNTIME)
- Start: `input_thread.start()` right after the QApplication exists and before the EventListener starts
  delivering; then `code_runner.adopt_runtime_objects()`.
- Quit: `input_thread.call_wait(run_control().stop, timeout=5.0)` (bounded), then `threads.shutdown()`
  stops the input thread (start_qt). If stuck: log the name, quit continues.

### gremlin/mode_manager.py, action_plugins/load_profile, pause_resume, change_mode (owner THR-MODE)
- ModeManager lives on the input thread; `mode_changed` delivered queued to UI QObjects; UI reads only
  `ui_state.currentMode` (verify no QML/UI reads ModeManager().current directly; report any).
- Readers on other threads get an immutable snapshot (existing `_publish` if present).
- Load Profile action: the whole hand-off goes `threads.main_call(fn, path)`; the unsaved-changes check,
  notification and `Backend().run_profile` run on main.
- Pause/Resume and Change Mode functors: no UI calls from the input thread.

### gremlin/run_scope.py, gremlin/base_classes.py, gremlin/modules/output.py keep-alive (owner THR-TIMERS)
- `run_scope.Timer` uses `threads.thread_timer`; Stop's CANCEL stage cancels on the owning thread.
- Pulse release (base_classes.py ~722): "thread has an event loop" instead of "is app.thread()"; the
  clock.sleep(0.05) branch only for macro / loop threads.
- vJoy keep-alive door (output.py ~365, ~418): owned by the input thread when Running.
- TTS (`tts.py` `_MainThreadDoor`) stays a main-thread hop (answer 7a) - verify it still works when called
  from the input thread.

### gremlin/ui/backend.py, gremlin/ui/system_tray.py (owner THR-UI)
- `activate_gremlin(True)`: takes the profile snapshot on main, `input_thread.call(run_control().start, ...)`;
  UI shows Starting until `runStarted` arrives (queued). Stop -> `input_thread.call(run_control().stop)`.
  No unbounded waits on main (S95).
- `selectMode` -> `input_thread.call(ModeManager().switch_to ...)` (report the real method name).
- Pause/Resume from toolbar and tray -> `input_thread.call(...)`.
- `threads.assert_main(...)` at the top of `run_profile`, `activate_gremlin`, `selectMode`, `_on_mode_changed`,
  `_highlight_input`.

### gremlin/ui viewers (owner THR-VIEWERS)
- `ui/live_input.py:93`, `ui/pair_live.py:74`, `ui/xbox_viewer.py:204`, `ui/logical_layout.py:203`,
  `ui/module_model.py:1016`, `ui/keyboard_layout.py:424`: connect to InputModuleRuntime signals with
  `QtCore.Qt.ConnectionType.QueuedConnection` and a QObject receiver (never a lambda/plain function);
  `threads.assert_main` at the top of each slot. Coalesce bursts where a slot does heavy work (R7).

### gremlin/watchdog.py (owner THR-WATCH)
- Watches the input thread too (answer 8a): reads `input_thread.silent_for()`; past the limit writes the same
  kind of "Input thread not responding for N s" dump (with that thread's stack) and "responding again".

### test/conftest.py (lead)
- autouse: `input_thread.set_inline(True)`, `threads.guards_raise = True`; fixture `input_thread_running`.

## Rules (same as contract-WT.md "Rules for every agent", plus)
- Tools: `PYTHONUNBUFFERED=1 poetry run python test/run_tests.py <files> 2>&1 | python tools/agent_log.py <AGENT>`;
  `poetry run ruff check <files>`; `poetry run python tools/pyright_baseline.py`. Never git stash/checkout/restore.
- One owner per file. Need a change elsewhere -> report to the lead.
- Every new test that should fail on old code: prove it (run before your change or reason it), then stop proof runs.
- Impact sweep: grep tests that pin what you changed; run them; list the ones that break and why (fix them only
  if they are yours; otherwise report).
- Never touch real devices, the running program, the user's Gremlin Platforms folder. Temp USERPROFILE for
  program code; Qt offscreen unless a test needs a real window (off main screen).
