# Fix plan: run input -> wiring -> output on its own "input thread" (PLAN-THR-IN)

2026-11-19, read-only planning scout PLAN-THR-IN, 13:02-13:06. Nothing changed, built or run.
Sibling: PLAN-THR-UI maps the UI-side touch points. Source study: claude/plans/rust-middle-path-study.md.
Everything below is PROPOSED; no spec statement is changed until the user answers.

Shared contract (both planners): the new thread is called **"input thread"**. Hand-offs to the UI go by
Qt queued signals or a `gremlin.threads`-owned queue drained on the main thread. Hand-offs into the
input thread go through a thread-safe command queue.

## 1. Today, end to end (traced)

| # | Step | Code | Thread today |
|---|---|---|---|
| 1 | dill.dll calls back for each stick event | `EventListener._run` registers `_joystick_event_handler` (event_handler.py:357-366) | dill's own callback thread |
| 2 | calibration, `trace._trace_raw`, `joystick_event.emit(Event)` | event_handler.py:393-434 | dill callback thread |
| 3 | keyboard / mouse hook: `_keyboard_handler` / `_mouse_handler` emit `keyboard_event` / `mouse_event` | event_handler.py:578-658; hook thread with its own message loop windows_event_hook.py:292-345 | hook threads |
| 4 | `InputModuleRuntime._on_hid` / `_on_key` (claim gate `should_forward`), re-emit `event` / `key_event` | gremlin/modules/runtime.py:102-103 (connect), :186-214 | **main thread** (QObject made on main; AutoConnection queues the cross-thread emit) |
| 5 | `EventHandler.process_event` (stamps mode, input_monitor, trace, `_run_callbacks`, `ButtonReleaseActions.process_release`) | connected at code_runner.py:452-454; event_handler.py:855-928 | **main thread** (direct, same thread as step 4) |
| 6 | `CallbackObject` -> action functors (`base_classes._process_event`) | code_runner.py:197-296, base_classes.py:669-685 | main thread |
| 7 | Map to Logical Device re-emits `EventListener.joystick_event` from inside step 6 -> steps 4-6 run again, re-entrant and synchronous | action_plugins/map_to_logical_device/__init__.py:142-155 | main thread (direct) |
| 8 | OSC input: server thread -> `incoming` (queued) -> `_emit_button`/`_emit_axis` -> `joystick_event.emit` | gremlin/osc.py:264, :1107-1201 | OSC thread, then main |
| 9 | Outputs: vJoy (`output.write_vjoy_*`, `VJoyProxy._lock`), ViGEm, SendInput keys (`run_scope.hold`), `MouseMotionManager` (own 100 Hz thread, sendinput.py:276-300), OSC send, Logical Device (`_VALUE_LOCK`) | gremlin/modules/output.py, gremlin/sendinput.py, gremlin/osc_output.py | caller's thread (main for events; macro / loop / script threads otherwise) |

Qt objects and timers on that path:

| Object / timer | Code | Thread today | Notes |
|---|---|---|---|
| `run_scope.Timer` (Tempo, Double Tap, Smart Toggle, pulse release, vJoy keep-alive, Load Profile hand-off) | run_scope.py:243-261 -> `threads.main_timer` threads.py:135-146 -> `MainTimer` (QTimer) :101-132 | main | from a non-main thread it silently becomes a `threading.Timer` (threads.py:144) |
| Tempo / Double Tap / Smart Toggle | tempo/__init__.py:188, double_tap/__init__.py:193, smart_toggle/__init__.py:90 | main | spec 05 S90, 04 S61, 01 S93 pin main |
| Pulse release | base_classes.py:687-728: `run_scope.timer` only if `currentThread() is app.thread()` (:722), else `clock.sleep(0.05)` | main | **on any other thread it blocks 50 ms** |
| vJoy keep-alive | output.py:350-406, `_KeepAliveDoor` moved to `app.thread()` (:409-421) | main (door from other threads) | |
| Can't-be-sent notice | output.py:113-206 (`QTimer` 0 ms, `asked` signal) | main | already worker-safe |
| `ModeManager` (QObject, `mode_changed`) | mode_manager.py:184-400; listeners code_runner.py:586, ui/backend.py:355 | main, no lock (04 section 6) | written by Change Mode and timer actions |
| `EventHandler.is_active` | event_handler.py:835-848; listeners code_runner.py:595, ui/backend.py:360 | main | Pause/Resume action calls it (pause_resume/__init__.py:80-84) |
| TTS engine | tts.py:152-175 (`_MainThreadDoor` to `app.thread()`) | main | Qt TTS object |
| Last-mode save | mode_manager.py:244-262 -> `deferred_write.schedule` (queued signal, deferred_write.py:30-90) | main | already worker-safe |
| Load Profile action | load_profile/__init__.py:60-90: `run_scope.timer` -> `Backend().run_profile` | main | runtime -> UI hop; must stay a main-thread hop |
| Run start / Stop | ui/backend.py:561-575 -> `CodeRunner.start` / `stop` (code_runner.py:351-487) -> `run_scope.stop` stages (run_scope.py:189) | main | builds `EventHandler.callbacks`, connects signals |
| `InputModuleRuntime.reload` | runtime.py:104-111 (configChanged, profileChanged, device_change_event) | main (queued) | |
| Device change | `threads.timer("device list update")` -> `device_change_event` event_handler.py:495-542 | timer thread, receivers queued to main | |

Threads that already run outputs off the main thread (unchanged by this plan): macro scheduler + one per
macro (macro.py:114, :257), mouse motion (sendinput.py:287), relative-axis loops (`run_scope.loop`,
action_plugins/common.py), user script timers (user_script.py:136), audio player (audio_player.py:132).

Main-thread assumptions in runtime code (would misbehave if called from the input thread): 9 checks -
base_classes.py:722, output.py:182, :365, :418, tts.py:161, :175, threads.py:144, :167, notice.py:75
(device_initialization.py:119, deferred_write.py:61, osc_discovery.py:336, osc_traffic.py:61 are
already worker-safe hops to main and stay correct).

## 2. Design (proposed)

**Thread kind: a `QThread` with its own Qt event loop.** Reason: every timer on the path is a QTimer
(run_scope.Timer, pulses, keep-alive), the claim gate and EventHandler are QObjects, and Logical Device
re-entry relies on a direct (same-thread) signal call. A plain thread with our own scheduler would mean
rewriting run_scope.Timer and every signal on the path. A QThread keeps all of it; only affinity moves.

New owner `gremlin/input_thread.py` (one owner per job):
- `start()` / `stop(timeout)`: one QThread named "Gremlin-Platforms: input thread", started through a
  new `gremlin.threads.start_qt(name, ...)` so it is listed in `threads.running()` and stopped by
  `threads.shutdown()` (keeps 01 S90/S91; `QThread.quit()` + `wait(ms)` bounded).
- `call(fn, *args)`: command queue into the thread (a QObject on the input thread with a queued
  `Signal(object)`; or `QMetaObject.invokeMethod` with QueuedConnection). Fire and forget.
- `call_wait(fn, timeout)`: same, main thread waits on a `threading.Event` at most `timeout` (01 S95);
  returns the result or raises `TimeoutError` (logged, never hangs).
- `is_input_thread()`, and `inline` mode: when the input thread is not started (unit tests, no
  QApplication) `call` runs at once on the caller - keeps most of today's ~250 tests that drive
  `process_event` directly on the main thread working unchanged (see risk R5).

Objects moved to the input thread (`moveToThread` before any connection, made by `input_thread.start`):
`EventHandler`, `InputModuleRuntime`, `ModeManager`, a new QObject `RunControl` that owns
`CodeRunner.start/stop` (CodeRunner itself is not a QObject today), the keep-alive door, and a
`ThreadTimer` factory. `EventListener` stays where it is: its signals are emitted from dill / hook /
timer threads, and receivers' affinity decides delivery (AutoConnection is resolved at emit time by
receiver thread - Qt rule; for PySide6 slots that are plain Python callables, not QObject methods, the
thread they run on is **unverified**: make every runtime slot a QObject method or pass an explicit
`ConnectionType`).

What runs where afterwards:
| Work | Thread after |
|---|---|
| claim gate, EventHandler dispatch, actions, Logical Device re-entry, ButtonReleaseActions | input thread |
| Tempo / Double Tap / Smart Toggle / pulse / keep-alive timers (`run_scope.timer`) | input thread (QTimer owned by it) |
| Mode stack changes (Change Mode, timer actions, Run start/end) | input thread; UI toolbar pick -> `input_thread.call(ModeManager().switch_to, ...)` |
| Pause / Resume / toggle | input thread; UI asks via `call` |
| Run start (script import, callbacks, connections) and Stop stages | input thread via `RunControl`; UI gets `runStarted(ok, error)` / `runStopped` queued |
| `mode_changed`, `is_active`, input_monitor, trace, Live Input, can't-send, notices | emitted on input thread, delivered queued to UI QObjects (PLAN-THR-UI owns the receivers) |
| TTS speak, Load Profile hand-off, `Backend` calls, dialogs, `signal.display_error` | main thread (explicit hop: new `threads.main_call(fn)` = queued to app thread; kept `threads.main_timer` for UI-only timers) |
| macros, mouse motion, relative loops, script timers, audio, OSC server | unchanged (own threads) |

Timers: replace `threads.main_timer` inside `run_scope.Timer` with `threads.thread_timer(name, s, fn)`:
a QTimer created on the calling thread when that thread has a Qt event loop (main or input thread),
listed in `_main_timers` (renamed `_qt_timers`, each with its owning thread so `shutdown()` cancels it
on its own thread via a queued call). Pulse check at base_classes.py:722 becomes "thread has an event
loop" (`QThread.currentThread().eventDispatcher() is not None`, Qt API) instead of `is app.thread()`;
the `clock.sleep(0.05)` branch stays only for macro / loop threads.

User scripts and code_runner: script callbacks run on the input thread (were main). Scripts get
JoystickPlugin / VJoyPlugin / KeyboardPlugin / OscPlugin, none of which touch UI objects. A script that
touched a QWidget/QML object directly would now be cross-thread: document in Help as "script callbacks
run on the input thread". Script import (`_setup_user_scripts`) runs inside Run start on the input
thread: a slow import delays Run, not the window. `sys.path` swap (code_runner.py:646-669) is
process-wide either way.

Start / stop / activate / Stop, bounded and hang-proof:
- Run: `Backend.activate_gremlin(True)` -> `RunControl.start` via `call`; UI shows "Starting" until
  `runStarted` arrives. Errors still go through `signal.display_error` (already a signal).
- Stop: `call(run_scope.stop)`; each stage keeps `STAGE_LIMIT_S` 3.0 (run_scope.py:95).
- Quit: main thread `call_wait(RunControl.stop, timeout=STAGE_LIMIT_S*7 capped at e.g. 5 s)`, then
  `input_thread.stop(2 s)` inside `threads.shutdown`. If the input thread is stuck, quit still ends
  (os._exit already cuts off anything left) and the name is logged (01 S91).
- Load Profile action: Stop + reopen must come from the main thread (UI owns the profile):
  `threads.main_call(Backend().run_profile, path)`; the main thread then asks the input thread.
- Watchdog: optional heartbeat for the input thread (a 1 s QTimer bump read by the existing watchdog)
  so an input-thread stall is logged like a main-thread one. Not required for the fix.

gremlin.clock and tests: QTimers never used gremlin.clock (MainTimer is a QTimer today), so nothing is
lost. Tests that need the real thread use a fixture `input_thread_running` that starts the QThread,
and `input_thread.call_wait(..., timeout)` / `qt_wait` helpers to sync; all waits bounded. Time-stepped
loops keep `gremlin.clock`.

GIL: a main thread stalled inside Windows (display power, driver calls via ctypes, `app.exec()`) is in
native code. ctypes releases the GIL around foreign calls (Python docs). Whether every PySide6 call the
main thread stalls in releases the GIL is **unverified**; that existing macro / mouse-motion threads
keep running today suggests `exec()` does. A main thread stuck in pure Python (a long profile load
loop) still shares the GIL: the input thread then gets the interpreter every switch interval (5 ms
default, `sys.getswitchinterval`), so bindings slow but don't freeze. Batch 2's test measures it.

## 3. Spec impact (pages 01, 02, 03, 04, 05, 06) - all PROPOSED

Statements that pin "main thread" and would change:
| Page | Ref | Today | Proposed wording |
|---|---|---|---|
| 02 | S40 (+ Q8 / decision D-02-S40-HANDLED) | event runs in the mode current "when the main thread handles it" | "...current when the **input thread** handles it (the listener leaves the mode unset; the event handler stamps it)." |
| 05 | S90 | Tempo, Double Tap, Smart Toggle timed-out actions on the main thread | "...on the input thread, the thread that handles input." |
| 04 | S61 | mode changes from timer actions on the main thread | "...on the input thread." |
| 01 | S93 | timers started on the main thread for actions run on the main thread | "A timer an action starts runs its function on the thread that started it when that thread has an event loop (the input thread, or the main thread for UI timers); from any other thread it runs on a named timer thread." |
| 01 | S95 | nothing on the main thread waits without a limit | "Nothing on the main thread **or the input thread** should wait without a limit." |
| 06 | section 6 text (06:213-221) and 03 section 6 (03:267-268), 04 section 6 (04:142-145) | "Event callbacks run on the main thread" | map text, updated with the batch |

New statements (proposed, page 06 "Threads and time", page 01 for the thread owner):
- 06 S-new-1 "Input reaches the profile on its own thread, the input thread: the input modules' claim
  check, the bindings, their actions and Run timers run there, so a busy or frozen window never delays
  or stops a binding."
- 06 S-new-2 "The window learns of runtime changes (mode, pause, Run started / stopped, live values)
  through queued notices; the runtime never waits for the window."
- 06 S-new-3 "Run, Stop, a mode picked in the toolbar and Pause from the window are asked of the input
  thread through its command queue; quitting waits for Stop at most a fixed limit."
- 01 S-new "The input thread is a program thread like the others: named, listed, and stopped by
  `shutdown()` within its limit."
- 06 S-new-4 "User script callbacks run on the input thread."

Decision row (proposed, page 06 section 12):
| D-06-INPUT-THREAD | 2026-11-?? (user: pending): input -> wiring -> output runs on a dedicated Qt thread ("input thread") with its own event loop; Run timers live there; UI hand-offs are queued; supersedes the "main thread" wording of 02 S40/Q8, 04 S61, 05 S90, 01 S93 |

Questions for the user (to settle before building):
1. Tests: a) existing tests run the wiring inline on the test's thread, and new tests start the real
   input thread (recommended: ~250 tests keep working); b) every test runs the real input thread.
2. TTS speech stays on the main thread (speech pauses while the window is frozen): a) accept
   (recommended); b) also move the speech engine (unverified that Qt TTS works off the GUI thread).
3. Input-thread heartbeat in the not-responding watchdog: a) yes; b) later.

## 4. Batches (ordered; each testable on its own)

Every batch: Spec line, map sections 2/3/4/5/6/10/11 updated, impact sweep of tests first.

| Batch | What | Files (owner) | Tests that fail on the old code |
|---|---|---|---|
| 0 | Probe (no behaviour change): log binding delay while the main thread is busy | `trace.py` or a test-only harness | n/a (measurement; Rust study stage 0 item 3) |
| 1 | Thread owner: `threads.start_qt`, `threads.thread_timer`, `threads.main_call`; new `gremlin/input_thread.py` (`start/stop/call/call_wait/is_input_thread`, inline mode) | threads.py, input_thread.py (new), joystick_gremlin.py start/quit order (lead, shared) | `test_input_thread.py`: thread listed in `running()`, `shutdown()` stops it within limit, `call` ordered FIFO, `call_wait` times out instead of hanging, timer made on input thread fires on it |
| 2 | Move the path: `EventHandler`, `InputModuleRuntime`, `RunControl` (wraps CodeRunner start/stop) to the input thread; Backend Run/Stop async | event_handler.py, modules/runtime.py, code_runner.py; ui/backend.py `activate_gremlin`/`run_profile` (**shared with PLAN-THR-UI**: one owner, stagger) | end-to-end: fake dill event -> fake vJoy write arrives within 100 ms while a main-thread slot blocks 2 s (fails today: nothing until the slot returns); Logical Device re-entry still synchronous; claim gate still drops unclaimed |
| 3 | Timers: `run_scope.Timer` -> `thread_timer`; pulse check (base_classes.py:722); keep-alive door to input thread (output.py:365, :418) | run_scope.py, base_classes.py, modules/output.py | Tempo long press fires while main blocked; pulse release on input thread does not sleep 50 ms (input thread not blocked); keep-alive armed on input thread; Stop still cancels / fires timers on the right thread |
| 4 | Mode / pause / profile hand-off: `ModeManager` to input thread; toolbar pick and Pause via `call`; `mode_changed` / `is_active` queued to UI; Load Profile -> `threads.main_call` | mode_manager.py, event_handler.py pause API, action_plugins/load_profile, pause_resume, change_mode (functors only) | Change Mode action while main blocked: next event uses new mode; UI receives `mode_changed` after unblocking; Load Profile still reaches Backend on main |
| 5 | Stop / quit bounded: quit `call_wait` Stop then stop thread; watchdog heartbeat (if Q3 a) | code_runner.py, run_scope.py, joystick_gremlin.py (lead), watchdog.py | quit while input thread busy ends within limit and names it; Stop with pending timers on input thread |
| D | Spec, map, Help (parallel with 2-5) | claude/program-map/01,02,03,04,05,06, Help "scripts run on the input thread" | `test_program_map_covers_files.py` (input_thread.py on map), `test_spec_line.py` |

Parallel shape: 1 first (contract). Then 2, 3 and D in parallel (separate files; 3 works to the
`thread_timer` contract). 4 after 2 (needs ModeManager connection rules from 2). 5 last. A test-only
agent can write the end-to-end "main thread blocked" harness alongside 1.

## 5. Risks

| # | Risk | Count / evidence | Mitigation |
|---|---|---|---|
| R1 | Qt affinity crashes: a QTimer started/stopped or a QObject child made from the wrong thread ("Timers cannot be started from another thread", parent in other thread) | 9 main-thread checks in runtime code (section 1); every `QtCore.QTimer(self)` on moved objects | create timers on owning thread only; `moveToThread` before connect; a test that fails on Qt warnings (qt_log) during the e2e test |
| R2 | Deadlock: main thread `call_wait` while input thread waits on main (e.g. a `BlockingQueuedConnection`, or Stop stage waiting on a UI hop) | Stop stages: TTS stop, OSC feedback, audio (run_scope stages NEUTRAL) | never use BlockingQueued; every `call_wait` bounded; stages that touch main-only objects post and don't wait |
| R3 | Data races on state today guarded by "all on main": `ModeManager` (no lock, 04 section 6), `EventHandler.callbacks`, `InputModuleRuntime._claims` swapped by `reload` | 3 objects | all writers moved to the input thread; UI reads immutable snapshots (`ModeManager._publish`, mode_manager.py:208) |
| R4 | GIL: input thread only as fast as the GIL allows while main runs Python | unverified for PySide6 calls | batch 0/2 measurement; Rust study stages 2-5 only if it matters |
| R5 | Tests pinning internals | `process_event` 22 files / 62 lines; `InputModuleRuntime` 29 / 60; `EventListener()` 44 / 76; `ModeManager()` 24 / 42; `main_timer`/`MainTimer` 9 / 24; `main_thread()` 21 / 30; `run_scope.timer`/`pending_timers` 8 / 13; `_pulse_event`/`flush_pulses` 6 / 7; `processEvents`/`qtbot.wait` 130 / 249 | inline mode (Q1 a) keeps most; impact sweep per batch updates the rest before any full run |
| R6 | User scripts touching UI objects from callbacks now cross threads | unknown (user content) | Help note; log a warning on cross-thread Qt warnings |
| R7 | Queued backlog to a frozen UI (Live Input, input_monitor, trace) grows during a long stall (e.g. 4 sticks x 1 kHz x 9 s = 36,000 events) | PLAN-THR-UI's side | coalesce on the UI side (latest value per input) |
| R8 | PySide6 plain-callable slots: which thread they run on | unverified | only QObject methods or explicit ConnectionType on the path |

## 6. Effort (claude/timings.md rules of thumb, 2026-10-09)

| Batch | Kind (timings.md) | Quote |
|---|---|---|
| 0 probe | agent fix / feature | 3-8 min per agent |
| 1 thread owner | refactor | 5-10 min per agent (1-2 agents) |
| 2 move the path | refactor | 5-10 min per agent (2-3 agents) + full run 5-6 min (very complex batch: threading change justifies the full run) |
| 3 timers | refactor | 5-10 min per agent |
| 4 mode / pause | refactor | 5-10 min per agent |
| 5 stop / quit | agent fix | 3-8 min per agent |
| D spec / map / Help | agent docs | 3-8 min per agent |
| test updates for R5 | no timing data for a thread-model change of this size; rough guess 10-20 min per batch | |
| each batch end to end | timings.md: agents ~10 + lead checks/map ~5 + tests ~5 + commit ~2 + CI ~10 (background) | ~30 min per batch, 6 batches |

Not verified: PySide6 GIL release per call; plain-callable slot thread in PySide6; Qt TTS off the GUI
thread; whether `QEventLoop` would also work in a `threading.Thread` (the plan avoids relying on it by
using `QThread`).
