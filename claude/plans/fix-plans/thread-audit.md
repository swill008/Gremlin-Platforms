# Thread audit (THR-AUDIT), read-only, 2026-11-19

Checked against the working tree while the other agents' code was landing (code_runner, threads, run_scope,
base_classes, output, notice, tts, runtime, mode_manager, backend, viewers, joystick_gremlin seen; osc.py,
osc_feedback.py, system_tray.py unchanged). Session was interrupted once; this file was not written before that.
A re-check is still due after the owners finish.

## Verified facts used
- PySide6 (experiment, scratchpad): a bound method of a QObject runs on THAT object's thread (also without
  @Slot). A lambda or plain function runs on the thread of the SENDER object (EventListener, Signal, ModeManager
  once moved), and is queued only if the emit comes from another thread and that thread's loop runs.
  So plain callables on `signal.*` / `EventListener.*` run on main (safe); on ModeManager / EventHandler signals
  they run on the input thread.

## 1. .connect( on the input path
| Connect | Verdict |
|---|---|
| runtime.py:102-103 EventListener.joystick/keyboard_event -> InputModuleRuntime._on_hid/_on_key | safe (QObject slots, @Slot, moved to input thread) |
| code_runner.py:452-454 (now ~486-488) runtime.event/key_event/virtual_event -> EventHandler.process_event | safe: same thread = direct (Logical Device re-entry stays synchronous), other threads queued |
| code_runner mode_changed / is_active / configChanged -> _RunnerSlots | safe (QObject slots). Note configChanged slot runs on the input thread (receiver), reads files via output.refresh() |
| runtime.py:105-109 configChanged/profileChanged/device_change_event -> reload | safe, but reload now runs on the input thread: see R6, R7 |
| backend.py:355,360 mode_changed / is_active -> Backend | safe (explicit Queued now) |
| backend.py:362 joystick_event -> _highlight_input; ui/device.py:559,702; ui/util.py:99-109,407-419 | safe (main-thread QObject receivers, auto queued) |
| ui viewers (live_input, pair_live, xbox_viewer, keyboard_layout, logical_layout) | safe: Queued unless inline (chosen at connect time, fine) |
| ui/module_model.py:1016 event.connect(self._on_joy) | seen mid-edit; recheck it ends Queued with QObject receiver |
| osc_feedback.py:405-406 mode_changed / joystick_event -> OscFeedback slots | safe only if OscFeedback lives on the input thread (it is made lazily by osc_feedback.start(), i.e. on input thread, comment still says main) |
| profile.py:78 `lambda *_: note_edit()` on signal.* | safe (sender on main) |
| output.py _CantSendNotice / notice.py: asked.emit from input thread | safe (queued to main) |
| osc.py:700 incoming -> _on_main | safe; OSC input still takes one main-thread hop before the input thread (OSC input stalls when the window stalls: cosmetic) |
| user_script.py:700-701 notifier codeDone/limitStart | safe (queued to main) but `_end_start` also runs on the input thread from `_wait_started` (guarded by `_start_lock`), and calls note_edit / started.emit there |

## 2. Qt / main-thread assumptions on the action path
- CRASH-level, UNFIXED: `OscRuntime` (QObject on main, owns QTimer children `_timers`, `_live_timer`) has
  start() (osc.py:1013), release_held() (:1052), stop() (:1069) called from Run start / Stop stages
  (code_runner `OscRuntime().start()`, stage CUT_INPUT "OSC releases", CANCEL "OSC") which now run on the input
  thread. `_cancel_release` (:1214) does timer.stop()/deleteLater(), `_reset_state` does `_live_timer.stop()`
  (:1565): cross-thread timer calls ("Timers cannot be stopped from another thread"), plus `_held`, `_timers`,
  `_enc_*` dicts mutated from main (OSC input) and input thread without a lock.
- backend.py:565 (and :467, :538, :548): `activate_gremlin(False)` is now async but the code after it checks
  `self.gremlinActive` (= runner.is_running(), only changes on the input thread). Auto-load does
  `activate_gremlin(False); loadProfile(...); if not self.gremlinActive: activate_gremlin(True)` -> still "active",
  so the Run is not restarted, and the queued Stop ends it: wrong result.
- backend `_run_copy` was replaced by code_runner.profile_snapshot (good; the old one re-read scripts and would
  have started user script top-level code twice).
- base_classes.py pulse release: now `threads.has_event_loop()`, fixed. output keep-alive: now owned by the input
  thread via `_pass_keep_alive_on`, fixed. tts: now main_call hops (start/stop/enqueue), fixed. load_profile:
  `threads.main_call(_load_on_main ...)`, fixed (QTimer.singleShot in it runs on main, ok).
- trace_timing.py:214,284: `_arm()` only arms its summary timer when called on the main thread; dispatch() now runs
  on the input thread, so it never arms from there (it still arms from set-on at :278 on main): cosmetic.
- code_runner `_on_active_changed` -> MouseMotionManager().reset() waits up to 0.2 s (sendinput.py:277) on the
  input thread at each Pause: bounded, cosmetic.
- threads.QtTimer: `cancel()` from another thread posts the stop to the creating thread's poster; if that thread
  has already ended the QTimer is destroyed from the wrong thread when the handle is dropped: low risk, wrong-thread
  delete warning at quit.
- macros, mouse motion, relative loops, audio, script timers: own threads, no Qt objects touched (verified by grep
  for QTimer/QObject in those paths).

## 3. Shared mutable state without a lock (UI vs input path)
- ModeManager public methods: only rename_mode/drop_mode go through `_on_input_thread`. `reset()` (called by
  backend.py:424 on main during profile load) writes `_mode_stack` on main while the input thread may run
  Stop's end_run(): race on the stack (wrong current mode, cosmetic/wrong result).
- `shared_state.current_profile` is the UI's profile, read on the input thread by ModeManager (`_known_modes`
  fallback, `_store_last_mode` fpath, resolve_start_mode), runtime.reload (`_vjoy_as_input_ids` iterates
  `settings.vjoy_as_input` dict) and output.py:1333/1360. Answer 6a says the Run uses a copy, but these read the
  live one: a dict mutated by the UI during iteration raises in a try/except that returns an empty set -> claims
  silently dropped (rare, wrong result); last mode may be stored under the profile opened AFTER Stop was queued.
- runtime.py reload: `_claims`, `_dest_guids`, `_passthrough` assigned as three attributes; `allows()` (called
  from UI via modules/inputs.py:26) can read a torn mix. `_bind_live_physical` iterates `device_initialization
  ._joystick_devices` values (mutated on main at device change): exception swallowed -> live physical claims
  missing (rare, wrong result).
- Configuration (RLock), trace (RLock), input_monitor (Lock), run_scope (Lock), registry (RLock), logical_device
  `_VALUE_LOCK`, event_helpers (Lock): fine.
- EventHandler.process_callbacks / known_modes read from main as plain bool/set replaced whole: benign.

## Ranked remaining risks (as of this snapshot)
1. CRASH: OscRuntime start/release_held/stop on the input thread (above). Fix: osc.py owner: run these bodies on
   the main thread (`threads.main_call`), and keep ordering for Stop by firing the held-button releases through
   the queue before the CUT_INPUT stage disconnects (needs a bounded `main_call_wait(fn, timeout)` helper in
   threads.py, never unbounded). Or move OscRuntime's timer-owning state to a lock-free hand-off.
2. WRONG RESULT: `gremlinActive` after async Stop (auto-load does not re-run; also :467 Reload, :538/:548).
   Fix (backend.py): keep a main-thread `_wanted_active` set synchronously in activate_gremlin and use it for
   those decisions; leave `gremlinActive` (runner state) for display only.
3. WRONG RESULT/race: ModeManager.reset() on main; route through `_on_input_thread` like rename_mode (mode_manager.py).
4. WRONG RESULT (rare): runtime.reload reading UI dicts: snapshot `vjoy_as_input` and `_joystick_devices` with
   `list(...)`/`dict(...)` copies made under retry, and publish the three claim fields as one tuple (runtime.py).
5. WRONG RESULT: shared_state.current_profile reads on the input thread: give RunControl/ModeManager the Run's
   snapshot (e.g. `shared_state.running_profile` set at Run start) and use it in mode_manager/output/runtime.
6. COSMETIC: trace_timing `_arm` from input thread (use threads.main_call to arm); OSC input still hops via main;
   QtTimer dropped after its thread ended; osc_feedback.py comment "made on the main thread" is now wrong.
7. WATCH: `reload()` and `output.refresh()` do file reads on the input thread after each configChanged (latency,
   bounded by the registry cache); user script import at Run start blocks the input thread (by design).

---

# Re-check after the owners finished (2026-11-19, working tree, tests still changing)

| # | Earlier risk | Status | Evidence |
|---|---|---|---|
| 1 | OscRuntime start/release_held/stop on input thread (crash) | RESOLVED | osc.py: `_state_lock` RLock around `_held/_timers/_enc_*`; start/stop queue port work with `threads.main_call(_start_here/_stop_here)`; auto-release QTimer is unparented and made on the Run's thread; `_cancel_release` stops a foreign-thread timer through a queued `stop` and `deleteLater`; release_held sends releases synchronously on the Run's thread (ordering kept); `_record` hops to main; packets go straight to the input thread via `input_thread.call(_on_input)` while `_input_here`. osc_feedback now made on the Run's thread (`instance()` replaces one made elsewhere), connections explicit Direct/Auto. |
| 2 | gremlinActive stale after async Stop | RESOLVED | backend.py: `_wanted_active` set synchronously (:616, :626), used at :472, :543, :553, :570, :601; reset on failed start in `_on_run_started`. |
| 3 | ModeManager.reset() race | RESOLVED | mode_manager.py:242-253 resolves the name on main, replaces the stack through `_on_input_thread(_set_stack)`; returns the name. |
| 4 | runtime.reload torn read / swallowed errors | MOSTLY RESOLVED | runtime.py: one `_gate` tuple; `reload` keeps old claims on failure and logs; `registry.modules()` and `vjoy_as_input` are copied. Left: `_bind_live_physical` still does `list(physical_devices())` over a dict the main thread mutates at device change and on error silently returns with fewer claims (below, N3). |
| 5 | input thread reads the UI's live profile | RESOLVED for mode_manager/runtime (`shared_state.profile_for_runtime()`, running_profile set at code_runner.py:409, cleared :528). mode_manager.py:249 (`_rewrite_stored_name`) still uses current_profile: it runs from rename_mode on the input thread (`_rename_mode`) and intentionally edits the OPEN profile's stored last mode: acceptable, see N2. |
| output.py current_profile reads (1325, 1356) | CONFIRMED UI-only | callers are backend.py:254, ui/module_model.py:821, ui/xbox_setup.py:44, ui/control_layout.py (all main). Not on the input path. |
| trace_timing `_arm` | RESOLVED | now `threads.has_event_loop()` and thread-time is per calling thread (:212-216). |

## New risks from the landed code (ranked)

Crash: none found in the code read.

Wrong result:
- N1 `OscRuntime._on_input` (input thread) and `_on_main` (main) both reach `_apply` for different packets? No: `_on_main` returns the rows without applying while `_input_here and _running` (osc.py ~1625), so the Run's state has one writer. Verified. But the `_input_here` flag is set in `start()` under the lock and read unlocked in `_on_main`/`incoming` emit: a packet arriving between `start()` and the flag, or between Stop clearing it, can be applied on main or dropped. Bounded to the packets at Run start/Stop edges. Owner osc.py: acceptable; if it matters, read the flag once per packet under `_state_lock`.
- N2 ModeManager._rewrite_stored_name (mode_manager.py:249) reads shared_state.current_profile on the input thread while the window may be swapping profiles (profile load/new): the stored last-mode may be rewritten for the wrong fpath, rare. Fix (mode_manager.py): do the rename on main (`threads.main_call`) or capture fpath on main in `rename_mode` before queuing.
- N3 runtime._bind_live_physical (runtime.py:185-190): the dict iteration in `device_initialization.physical_devices()` can race a device change and the except returns silently, so a reload drops the live-physical claims until the next reload (events of those sticks are then blocked). Fix (runtime.py): retry once on RuntimeError and keep the previous gate when it fails (raise out of `_read_gate` so `reload` keeps the old claims).
- N4 Stop ordering: `_on_run_stopped` is ignored while `_starting`; if Run is pressed, Stop, Run in quick succession the first runStarted clears `_starting` for a Run that a later queued Stop ends: UI state follows runner.is_running() via the final signals, so it self-corrects; cosmetic flicker only.

Cosmetic / watch:
- N5 `OscFeedback.reload` and `output.refresh()` run file reads on the input thread after each config change (input latency for the duration of the read, bounded by caches).
- N6 `threads.QtTimer` dropped after its owning thread ended still destroys the QTimer on the wrong thread (low risk, quit only).
- N7 User script import (`script.reload()` in `_setup_user_scripts`) and `Script._end_start` (note_edit, `started.emit`) now run on the input thread at Run start: slow imports delay Run start by design, not the window; `note_edit` is lock-safe (verified no UI object touched, unverified for every listener).
- N8 Quick Stop/Start via `_to_input` is FIFO; Backend actions that run on main right after `activate_gremlin(False)` (profile swap) now overlap the Stop stages on the input thread; Stop uses the snapshot, so only items in N2 touch the open profile.

Unverified: whether PySide6 releases the GIL in every call the main thread can stall in; behaviour under a real frozen window (needs the end-to-end test THR-SWEEP is writing).
