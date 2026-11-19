# Input thread: the UI side (PLAN-THR-UI, 2026-11-19, read-only)

Planning only. Nothing changed, built or run. Sibling: PLAN-THR-IN (input/runtime side).
Shared contract: a thread named "input thread" (started through `gremlin.threads`, own Qt
event loop); input -> UI hand-offs through Qt queued signals or a `gremlin.threads`-owned
queue drained on the main thread; UI -> input through a thread-safe command queue.

## 0. How it works today (verified)

- The listener thread ("event listener", `gremlin/event_handler.py:310`) and the dill driver
  callback emit `EventListener.joystick_event` / `keyboard_event` / `mouse_event` /
  `device_change_event` (`event_handler.py:404,419,434,542,554,564,607,648`). `EventListener`
  lives on the main thread, so every receiver that is a main-thread QObject slot gets the event
  queued onto the main thread (spec 02 section 6 row "Signals crossing threads",
  `02-devices-input.md:212`).
- `InputModuleRuntime` (`gremlin/modules/runtime.py:86-112`, a main-thread QObject singleton)
  receives them, applies the claim gate and re-emits `event` / `key_event` (`runtime.py:193,212`)
  - a direct, same-thread emit on the main thread.
- `CodeRunner._start` connects `InputModuleRuntime.event/key_event` and
  `EventListener.virtual_event` to `EventHandler.process_event` (`gremlin/code_runner.py:452-454`);
  Stop disconnects them (`code_runner.py:531`). `process_event` (`event_handler.py:864`) reads the
  mode, records Input Monitor, traces and runs every callback on the main thread.
- UI viewers subscribe to the same signals (table below), so UI and the profile get the same
  event in the same main-thread turn, in connection order.

After the move, `InputModuleRuntime` and `EventHandler` (and `ModeManager`, see 1.3) belong to the
input thread (`moveToThread` or created there). Then every UI receiver of their signals is on a
*different* thread, and the meaning of every connection changes.

## 1. Shared state and synchronous calls between UI and input path

Legend: Dir = direction. Hand-off: QS = queued signal (receiver is a main-thread QObject, or
explicit `QueuedConnection` with a context object), SNAP = immutable snapshot swapped atomically,
CMD = UI -> input command queue, LOCK = existing/new lock.

### 1.1 UI receivers of input-path signals (input -> UI)

| What | file:line | Dir | Proposed hand-off | Risk |
|---|---|---|---|---|
| Input highlighting (Device Bindings page follows the moved control) | `gremlin/ui/backend.py:362` (`EventListener.joystick_event -> _highlight_input`, `:383-413`) | input -> UI | Stays on `EventListener` (already queued to main); no change. Reads `Configuration()` and `shared_state.suspend_input_highlighting()` on main - fine | Low. Must not be re-pointed to `InputModuleRuntime.event` without a QS |
| Live input viewers (Live tab, pair live, Xbox viewer, Logical layout, module model) | `ui/live_input.py:93`, `ui/pair_live.py:74`, `ui/xbox_viewer.py:204`, `ui/logical_layout.py:203`, `ui/module_model.py:1016` (`InputModuleRuntime().event.connect`) | input -> UI | QS. Bound methods of main-thread QObjects become queued automatically once the emitter runs on the input thread (AutoConnection decides at emit time). Make it explicit: `connect(slot, QtCore.Qt.ConnectionType.QueuedConnection)` and add the affinity assert in each slot (section 2) | Medium: any of these that is a plain function / lambda / non-QObject method would run on the input thread (direct). Verified these five are bound methods; unverified whether each owner is a QObject (pair_live, xbox_viewer: check in batch 1) |
| Keyboard page follows key presses | `ui/keyboard_layout.py:424` (`InputModuleRuntime().key_event`) | input -> UI | QS, as above | Medium (same) |
| Raw listeners on `EventListener` (Device page model, device lists, input listening/"press a control" dialog, macro recorder, module setup) | `ui/device.py:559-560,702-703`, `ui/module_model.py:2542-2546` (already explicit `QueuedConnection`), `ui/util.py:99-109,407-419` | input(listener) -> UI | Unchanged: they already hop from the listener thread to main. Not on the input thread's path at all | Low |
| `device_change_event` subscribers (~15: `backend.py:73,361`, `device.py:172,307`, `hidhide.py:734`, `device_library_model.py:357`, `module_*`, `viewer_devices.py:74`, `hardware_layout.py:498`, `auto_mapping_tool_modules.py:44`, `device_aliases.py:175`, `modules/output.py:146`) | listed | listener -> UI | Unchanged for UI. `InputModuleRuntime.reload` (`runtime.py:109`) must now run on the input thread: its connection becomes queued to the input thread automatically once the object is moved | Medium: `reload()` reads `registry` and `shared_state.current_profile` (`runtime.py:46`) while the UI may edit; see 1.3 |
| Run/Pause state -> toolbar | `backend.py:360` (`EventHandler().is_active.connect(self.activityChanged)`), emitted from `event_handler.py:838-848` (Pause action runs on input thread) | input -> UI | QS. Signal-to-signal connection: PySide6 queues it by the receiver `backend` object's thread (verify in batch 1 test) | Medium |
| Mode change -> mode selector | `backend.py:355` (`mm.mode_changed -> _on_mode_changed`, `:441-443` writes `ui_state.setCurrentMode`) ; emitted `mode_manager.py:239,280` from Change Mode actions | input -> UI | QS | Medium: QML must never read `ModeManager().current` directly; it reads `ui_state.currentMode` only (verify grep in batch 1) |
| Notifications from actions | `action_plugins/load_profile/__init__.py:67,74`, `condition/__init__.py:159,169` (`signal.showNotification.emit`), `macro/__init__.py:952-959` | input -> UI | QS: `gremlin.signal.signal` is a main-thread QObject (`gremlin/signal.py:97`); its QML connections are queued automatically. Python receivers connected with lambdas would not be | Medium: audit every `signal.*.connect(` with a lambda (`condition` and `macro` emits at 159-169/952-959 look like editor (model) code, unverified which thread calls them) |
| Input Monitor (Live Log Reader) | write `event_handler.py:871` -> `input_monitor.record`; read `ui/live_debug.py:928-932` (`version()`/`entries()` polled) | input -> UI | Already LOCK (`input_monitor.py:36`, deque) + polling. No change | Low |
| Trace tab | writes `trace.begin_input/wiring/end_input` (`event_handler.py:875-880`, `:891-905`); reads `ui/trace_model.py:54`, `ui/debug_mode.py:46` | input -> UI | Already RLock (`trace.py:99`). `trace.on_change` hooks run from `set_enabled` (UI thread) and emit signals - fine. `trace.begin_input/end_input` per-input context must become thread-local or input-thread-only (unverified how it is stored) | Medium |
| vJoy Viewer / Xbox viewer reading output state | `ui/xbox_viewer.py:204` (event), vJoy viewer reads device values (unverified path) | output -> UI | SNAP or poll under the existing vJoy locks (RB10 FIXED `06-runtime-outputs.md:236`) | Medium (unverified) |

### 1.2 Synchronous calls from the input path into UI code (must change)

| What | file:line | Dir | Proposed hand-off | Risk |
|---|---|---|---|---|
| Load Profile action reads the UI's open profile and starts a Run | `action_plugins/load_profile/__init__.py:64-65` (`backend.Backend()`, `be.profile.has_unsaved_changes()`), `:84-90` (`run_scope.timer(... _run_profile)` -> `Backend().run_profile`) | input -> UI | The whole action body posts one QS ("load profile request", path) to the main thread; the unsaved-changes check, the notification and `run_profile` run there. Run/Stop then talks to the input thread through CMD | **High**: `Backend` is a main-thread QObject; calling it from the input thread touches QML-bound properties = crash/undefined. Also `run_scope.timer` today means "Qt main thread" (`06-runtime-outputs.md:133`) |
| `map_to_vjoy` / `map_to_xbox` `inputItemChanged.emit` | `map_to_vjoy/__init__.py:175-200`, `map_to_xbox/__init__.py:185` | UI -> UI | Verified: these are in editor model setters (`_set_vjoy_device_id`, `:170-175`), not the functor. No change | Low |
| Short pulse release timer | `base_classes._pulse_event`: `QTimer.singleShot` on main thread, `time.sleep` elsewhere (`06-runtime-outputs.md:135,215`) | input | PLAN-THR-IN owns; the UI side only needs it never to fall into the `time.sleep` branch on the input thread (would block input) | Medium |
| `threads.main_timer` / `run_scope.timer` used by actions (Tempo, Double Tap, Smart Toggle, keep-alive) | `gremlin/threads.py:134-145` (falls back to a `threading.Timer` off the main thread), `run_scope.py:302-315` ("on the main thread") | input | PLAN-THR-IN owns: becomes "on the input thread" (a QTimer owned by the input thread's loop). UI side: Help and spec wording (section 4) | High for behaviour, not UI |

### 1.3 Shared objects (both sides read/write)

| What | file:line | Dir | Proposed hand-off | Risk |
|---|---|---|---|---|
| `ModeManager` (mode stack) | read `event_handler.py:866` every event; written by Change Mode actions (input) and by `backend.selectMode` (`backend.py:446-451`, UI) | both | Input thread owns the stack. UI `selectMode` -> CMD ("switch mode X"); `mode_changed` -> QS back. UI keeps its own `ui_state.currentMode` copy | **High**: today both writers are on one thread, so no lock exists |
| `EventHandler.process_callbacks` / pause | `event_handler.py:825-838`; UI Pause/Resume (toolbar, tray) | both | UI Pause/Resume -> CMD; `is_active` -> QS | Medium |
| Run / Stop | `backend.activate_gremlin` `backend.py:561-577` -> `CodeRunner.start/stop` (connects/disconnects `process_event`, `code_runner.py:452-454,531`) | UI -> input | CMD: "start(profile snapshot, mode)" / "stop"; the input thread does the connects. UI waits on a bounded reply (S95: no unbounded wait on main) and updates status from a QS "run state" | **High**: disconnecting a queued connection while events are queued on another thread lets queued events still arrive after Stop (verify `run_scope` generation check covers it) |
| Running profile | `code_runner.py:372-397` keeps the live `Profile` object (no copy, verified); `shared_state.current_profile` read by `runtime.py:46`, `mode_manager.py:178-304`, `change_mode/__init__.py:189` | both | SNAP: Run hands the input thread a frozen view (mode list, start mode, claims); edits during a Run don't touch it. If the user wants edits to apply live, that needs a spec decision | **High** (spec question, see 4) |
| `InputModuleRuntime._claims` / `_passthrough` | `runtime.py:99-140`; `reload` from `configChanged`, `profileChanged` (UI thread emits) and `device_change_event` | UI -> input | Reload runs on the input thread (queued, automatic after `moveToThread`); build the new dicts then swap in one assignment (SNAP) | Medium |
| `Configuration()` | no lock, `01-app-shell.md:282` | both | Input path should only read; any write from the input thread goes through `deferred_write` (main). Add a lock or read-only snapshot for values the input path reads per event (calibration, highlighting flag) | Medium (existing known gap) |
| `shared_state.runtime_active`, `hold_input_highlighting` | `code_runner.py:475,542`, `backend.py:567,576` | both | Plain bool writes; set them on the thread that owns Run (input) and mirror to UI by QS. Low unless read-modify-write | Low |
| HidHide, Wake PC detection, Screen Saver Mode | `hidhide.py:734` (device-change only); SSM raw input is a separate main-thread window proc (`screen_saver_mode.py ~1195-1217`, from the study), not on the input path (grep of `event_handler.py`, `windows_event_hook.py`, `runtime.py`: no SSM calls) | none | No change. Note: while SSM's main-thread display waits (SSM-MAIN-THREAD-PAUSE) the input thread keeps running - the goal | Low |
| System tray | `gremlin/ui/system_tray.py` - Run/Stop/Pause items | UI -> input | Same CMD as the toolbar | Low |
| Input Tester | separate program (`input_tester.py`, `02-devices-input.md:150-205`) | none | Not affected | None |

## 2. Qt affinity violations to guard

Objects that would be touched from the wrong thread after the move:
1. `Backend` and every `QAbstractListModel` / QML-exposed `QObject` in `gremlin/ui/` - must only be
   touched on main. Known path from the input side: Load Profile (1.2).
2. `ui_state` properties (`setCurrentMode`) - main only (reached today via `_on_mode_changed`).
3. QTimers created by actions: a QTimer created on the input thread belongs to it; `MainTimer`
   (`threads.py:98-131`) creates its `QTimer()` with no parent on the calling thread. Started and
   stopped from different threads = Qt warning "Timers cannot be stopped from another thread" and
   no stop. Stop's CANCEL stage (`run_scope`) must run on the input thread.
4. `user_script.py:709` `QTimer(self)` and `osc.py:660,681,1230` timers: parent QObject's thread
   must match the thread that starts them (unverified which thread calls them after the move).
5. `gremlin.signal.signal` (main) - safe to `emit` from any thread, but Python lambda receivers
   run directly on the emitting thread.
6. Lambdas / plain functions connected to signals emitted on the input thread (no context
   object) run on the input thread. Rule: always pass a receiver QObject or `QueuedConnection`.

Guards (proposed):
- `gremlin.threads.assert_main(what)` and `assert_input(what)`: compare `QThread.currentThread()`
  with the app's / input thread; in tests and debug builds raise, in release log once to
  system.log (owner: `gremlin/threads.py`, shared file - lead or PLAN-THR-IN). Call it at the top
  of every UI slot that receives input-path signals (the ~8 slots in 1.1) and of `Backend.run_profile`,
  `activate_gremlin`, `selectMode`.
- A Qt message handler hook in tests (`qInstallMessageHandler`) that turns Qt's own
  "QObject: Cannot create children for a parent that is in a different thread" / "Timers cannot be
  started from another thread" warnings into test failures (test/conftest.py).
- Guard test (design for change): scan `gremlin/ui/**.py` for `.connect(` on
  `InputModuleRuntime()`, `EventHandler()`, `ModeManager()` signals whose target is a `lambda`
  or has no `QueuedConnection` -> fail, so a new viewer can't add a direct cross-thread link.

## 3. Tests

Counted by grep (verified counts, 886 entries in `test/unit`):
- 16 files call `process_event(` directly; 13 emit `joystick_event`/`keyboard_event` or call
  `_on_hid`/`_on_key` (list: `test/action_interaction/conftest.py`, `action_matrix/test_ld_pick.py`,
  `action_matrix/test_ld_synthetic_and_notice.py`, `test_audit3_run_stop.py`, `test_audit_devices.py`,
  `test_batch2_b3.py`, `test_batch2_b3_typing.py`, `test_batch2_B5b.py`,
  `test_calibration_raw_read_only.py`, `test_final_07.py`, `test_logical_loop_e2e.py`,
  `test_page_follow_ld_kb.py`, `test_vjoy_viewer_lists_osc.py`).
- 15 files drive input AND check a `gremlin.ui` model in the same call (most likely to break):
  `action_interaction/conftest.py`, `action_matrix/harness.py`, `action_matrix/test_ld_synthetic_and_notice.py`,
  `action_matrix/test_matrix_flow.py`, `test_audit2_coverage.py`, `test_audit3_run_stop.py`,
  `test_batch2_b2a_input_events.py`, `test_calibration_raw_read_only.py`, `test_final_02.py`,
  `test_final_07.py`, `test_input_monitor.py`, `test_leaks.py`, `test_page_follow_ld_kb.py`,
  `test_stage1_runtime.py`, `test_vjoy_viewer_lists_osc.py`.
- Highlighting: `test_batch3_C2.py`, `test_device_bindings_page_e2e.py`, `test_device_bindings_quick_tap.py`.
- 32 files reference `main_timer` / `MainTimer` / `main_thread` (timers that assume main =
  action thread), e.g. `test_run_scope_only.py`, `test_stage1_runtime.py`, `test_batch3_C3a.py`,
  `test_ssm_core.py`, `test_action_fixes.py`, `action_interaction/virtual_timers.py`, `test/conftest.py`.

How to update: tests that call `process_event` directly keep working as unit tests of the handler
(they call it on the test thread). Tests that emit a signal and expect a UI model to change in the
same call need a shared helper `drain_input_then_ui()` (process the input thread's queue, then
`QCoreApplication.processEvents()` on main) - or a test mode where the "input thread" is the test's
own thread (`threads.input_inline=True`) so most of the ~15 keep running unchanged. Recommend the
inline test mode for unit tests and the real thread for a small set of end-to-end tests.

Proposed tests that fail on today's code:
1. `test_input_thread_ui_blocked.py::test_output_written_while_main_thread_blocked`: start a Run with
   a Map to vJoy binding (fake vJoy), block the main thread (a slot that sleeps 2 s via
   `gremlin.clock`-stepped wait), emit a button press from the listener side, assert the vJoy write
   happened before the main thread unblocked. Fails today (output waits for the main thread).
2. `::test_highlight_arrives_by_queued_signal`: emit an event; assert `_highlight_input` and the
   Live viewers' slots ran on the main thread (record `QThread.currentThread()`) and the action ran
   on the input thread. Fails today (action thread == main).
3. `::test_load_profile_action_runs_backend_on_main`: trigger Load Profile from the input thread;
   assert `Backend.run_profile` ran on main. Fails today trivially (no input thread); with a naive
   move it would crash - this is the regression guard.
4. `::test_stop_drops_queued_events`: queue 100 events, Stop from the UI command queue, assert no
   callback runs after Stop returns.
5. `::test_ui_mode_select_goes_through_command_queue`: `selectMode` from main, assert
   `ModeManager` changed on the input thread and `ui_state.currentMode` followed via `mode_changed`.
6. Guard test from section 2 (no lambda / direct connects to input-thread signals).

## 4. Spec pages that say "main thread" (proposed wording only, user must approve)

| Page:line | Today | Proposed |
|---|---|---|
| `06-runtime-outputs.md:221` | "Event callbacks run on the main thread (queued Qt signals from the listener thread)." | "Event callbacks run on the input thread (queued Qt signals from the listener thread). The window (main thread) gets what it shows through queued signals and never runs an action." |
| `06-runtime-outputs.md:133,214` | Tempo / Double Tap / Smart Toggle: `run_scope.timer` (Qt main thread) | "... (input thread)" |
| `06-runtime-outputs.md:135,215` | Pulse release `QTimer.singleShot` on main thread | "on the input thread" |
| `06-runtime-outputs.md:159` | vJoy keep-alive `run_scope.timer` on the main thread | "on the input thread" |
| `01-app-shell.md:411` S93 | "Timers started on the main thread for actions should run their function on the main thread." | "Timers started by actions should run their function on the input thread, where actions run." |
| `01-app-shell.md:413` S95 | "Nothing on the main thread should wait without a limit." | add: "Nothing on the input thread should wait without a limit, and the UI never waits on the input thread without a limit." |
| `02-devices-input.md:212` | listener signals queue to main-thread receivers | add: "`InputModuleRuntime` and `EventHandler` live on the input thread; the window's viewers receive their signals queued." |
| new statement (page 01 "Threads and time") | - | "Controls keep working (bindings, macros, timers) while the window is busy or not responding." |
| new statement (page 01) | - | "The window only reads input-side state through queued signals or snapshots; Run, Stop, Pause and mode selection reach the input thread as commands." |
| Open question for the user | - | Edits made to the profile during a Run: today the Run uses the live object (`code_runner.py:372`); with a thread, the cleanest design is a snapshot at Run (edits apply at the next Run). Needs a decision. |

`12-screen-saver-mode.md`, `05-actions-editors.md`: no "main thread" statements found by grep.
Help pages mentioning timing: not checked (unverified).

## 5. Ordered batches (UI side), matching the likely input-side order

Effort: `claude/timings.md` rules of thumb: "Agent fix / feature / docs: 3-8 min per agent; a batch
of parallel agents ~10 min", "Refactor: 5-10 min per agent", end to end per batch ~22 min + CI ~10
min in the background. No timing data for threading work specifically; these figures are the
table's kinds, so treat them as lower bounds.

| Batch | UI-side work | Files (owner) | Kind / effort |
|---|---|---|---|
| 1 Infrastructure + affinity guards | `assert_main/assert_input` helpers; Qt warning -> test failure hook; guard test for connects; explicit `QueuedConnection` on the ~8 UI receivers; inline test mode helper | `gremlin/threads.py` (lead/PLAN-THR-IN, shared); `test/conftest.py` (lead); `ui/live_input.py`, `pair_live.py`, `xbox_viewer.py`, `logical_layout.py`, `module_model.py`, `keyboard_layout.py`, `backend.py` (UI agent A); new guard test (test agent) | feature + refactor: 2-3 agents, ~10 min + lead ~5 min |
| 2 Move dispatch | Run/Stop/Pause/mode select become commands; `is_active`, `mode_changed`, run state come back as queued signals; Load Profile action hands off to main; snapshot at Run (after the user's decision); tests 1-5; update the ~15 input+UI tests to the inline mode or drain helper | `ui/backend.py`, `ui/system_tray.py` (UI agent A); `action_plugins/load_profile/__init__.py` (UI agent B); `code_runner.py`, `mode_manager.py`, `event_handler.py`, `modules/runtime.py` (PLAN-THR-IN side); tests split over 2 test agents by folder (`action_matrix`/`action_interaction` vs `test_*` files) | refactor: 4-5 agents ~10 min each, parallel; full run justified (very complex) 5-6 min |
| 3 Timers / macros | UI side only: Help and spec text for timers; check `MainTimer` users in UI code (`ui/util.py:236` input-listening abort stays a main timer); the 32 timer tests reviewed for "main thread" assumptions | `ui/util.py` (UI agent A, check only), tests (test agent), spec/Help (docs agent) | fix/docs: 2 agents, ~10 min |
| 4 Cleanup | Remove the inline-mode shortcuts tests no longer need; map pages (sections 2-6, 10, 11, README counts); full map check | `claude/program-map/01,02,06` (docs agent), tests (test agent) | docs: ~10 min |

Left out of parallel: `gremlin/threads.py` and `test/conftest.py` are shared by both sides (lead
keeps them); `backend.py` is one file, so one owner across batches 1-2.

## Not verified
- Whether `pair_live`, `xbox_viewer` slot owners are QObjects; how vJoy Viewer reads values.
- How `trace.begin_input`/`end_input` hold the current input (global vs thread-local).
- Whether `condition`/`macro` `showNotification` emits run in editor code only (looks like it).
- PySide6 signal-to-signal (`is_active -> activityChanged`) queuing by receiver thread: to prove in
  batch 1 test 2.
