# Compare: memory series (item 15) and macro scheduling (item 16)

Agent C-MEASURE, 2026-11-23, 17:45-17:50. Read-only study; nothing was run
except `git show` / `grep`. Upstream remote `upstream/develop`, merge base
daf4057f. Every claim below is from code or diffs unless marked
**unverified**.

---

## 15. PySide6 wrapper growth: upstream "real leak" vs our PYSIDE-WRAPPERS "harmless"

### The two explanations

**Upstream (02a280e8, 2026-10-24; follow-ups 9602a510, 66bb2477, 9fb7147b).**
Commit text: Python objects that QML instantiates "are created but then not
correctly deleted". The new `gremlin/ui/model_factory.py` docstring cites
PYSIDE-1407: "PySide6 never frees a Python object QML instantiates". The
fix: QML no longer writes `ModeListModel {}`; it calls a singleton slot,
`ModelFactory.modeListModel(_switchCombo)`, which builds the object in
Python with the QML item as its Qt parent, so Qt's parent deletion frees it.
The factory has 24 slots (ModeListModel, DeviceListModel, InputListenerModel,
VJoyDevices, Tools, AxisCalibration, the Options models, WindowGeometry and
more). 66bb2477 then reuses selection models instead of making new ones;
9fb7147b adds an `ObjectLoader` to cut spikes; d3f55d9b stops repeated calls
into leaky vJoy functions (a separate, driver-side leak).

**Ours (program map page 01, gap PYSIDE-WRAPPERS, 2026-10-10, F3-LEAKS).**
"PySide 6.11.2 keeps empty Python wrappers of QML-created objects; harmless,
upstream, nothing to fix here." The evidence behind it is
`test/unit/test_leaks.py` (`_SCRIPT.counts()`), whose comment says the
wrapper of every QML-made Python object is kept after QML deletes it "(C++
gone, no holder in Python, signals disconnected)". That test counts only
objects for which `shiboken6.isValid(obj)` is true, so it deliberately does
not count the kept wrappers at all. F3-LEAKS fixed real growth that we
could see (Options models, curve point objects, release entries) and filed
the rest as harmless.

### Where they actually disagree

Both agree on the mechanism: the Python object of a QML-instantiated Python
type outlives its C++ object. The disagreement is only about cost:

1. **"Empty" is not shown.** When the C++ side is destroyed, shiboken marks
   the wrapper invalid, but the Python instance `__dict__` is not cleared.
   Whatever the object stored on `self` (lists of rows, references to
   `Device`, profile or mode objects, timers, cached strings) stays
   reachable from the kept wrapper. Our note never measured that; the test
   that produced it filters those objects out. **Unverified either way**
   until measured.
2. **How many are made.** In our program 81 Python types registered with
   `@ta.QmlElement` are instantiated directly in QML at 115 sites in 65 QML
   files (count by script over `qml/`, `action_plugins/`, `theme/`). The
   most used: `WindowPlacement` (8 sites), `ModeListModel` (7), `EditLock`
   (6), `HardwareProfile` (6), `DriversModel` (3). Many sit inside
   delegates or editors that are made again on every page switch, row
   click, profile load or window open (for example `ModeListModel` in
   `ChangeModeAction.qml`, `EditLock` in `DeviceBindingsPage.qml`,
   `HardwareProfile` in `DeviceMapCard.qml`, `PairLiveThrottle` in
   `InputViewerCard.qml`). Upstream's set is much smaller (24 factory slots).
3. **Indirect hold.** If a kept wrapper's `__dict__` holds a profile or
   device object, the previous profile cannot be garbage-collected after a
   profile load. That would make the growth scale with profile size, not
   with a fixed wrapper size. Upstream's 9602a510 ("objects aren't released
   on profile loading") points at exactly this class of problem.

So the question that settles it is not "do wrappers stay" (both agree) but
"how many bytes, and which objects, do the kept wrappers keep alive per
repetition, and does it grow without bound".

### Tools already in the repo

- `test/unit/test_leaks.py` `_SCRIPT`: an off-screen full app
  (`joystick_gremlin.JoystickGremlinApp`, `fake_hardware.install()`,
  `GREMLIN_OFFLINE=1`, temp `USERPROFILE`), `run(code)` through
  `QtQml.QQmlExpression` on the main window (opens windows with
  `Helpers.createComponent(...)` and closes them with
  `Helpers.windowOf(...).close()`), `pump()` that also sends
  `DeferredDelete`, and `gc.get_objects()` type counts with
  `shiboken6.isValid`. Run in its own process with `test/proc_tree.py`.
- `test/unit/device_mapping_editor_lifecycle_smoke.py`: `memory_mb()`,
  the process private bytes (`PrivateUsage`) through
  `psapi.GetProcessMemoryInfo` with ctypes. Its 2026-10-02 note: about
  30 MB per Device Mapping Editor open, all but 1-2 MB kept by Qt after
  close, flat over later opens.
- `test/unit/smoke_exit.py` (engine object counts), `test/unit/test_tray_memory.py`
  (working-set trim).
- Python stdlib `tracemalloc` (not used anywhere in the repo yet) and
  `gc.get_referents`. No `psutil` in the repo; not needed.
- `gremlin.ui.backend.Backend.loadProfile(fpath)` (backend.py:1067) and
  `newProfile()` (:957) for profile loads in-process.

### The measurement (designed, not run)

One new probe script, run like `test_leaks.py`'s `_SCRIPT` in its own
process (off-screen, `fake_hardware`, temp `USERPROFILE`, `proc_tree.run`).
It could later become a test, but first it is a measurement.

**What to repeat (each a separate scenario, fresh process each):**

| Scenario | One repetition | Why |
|---|---|---|
| A. Profile load | `backend.loadProfile(p1)`, pump 0.5 s, `loadProfile(p2)`, pump 0.5 s (two real profiles with several devices, Change Mode and Macro actions; e.g. from `test/action_interaction/profiles/` plus one large hand-built one) | upstream 9602a510; the indirect-hold case |
| B. Page switch | Device Bindings -> Keyboard -> Logical Device -> OSC -> Status and back, through Main.qml's page selection by `QQmlExpression` | delegates with `EditLock`, `HardwareProfile`, `DeviceLiveState`, `ModeListModel` |
| C. Row click / editor open | open the action pane on a row holding Change Mode (3 `ModeListModel`s) and a Macro, close it | the busiest QML-made type |
| D. Window open/close | Options, Input Viewer, Manage Modes, Device Information, Calibration, Live Log, Device Mapping Editor (helpers.js `createComponent` / `close`) | the windows upstream changed |

**How many times:** 2 warm-up repetitions (QML compile cache, first-use
singletons), then 3 measured blocks of 25 repetitions (75 measured), with a
reading after each block. Three blocks show whether growth is linear
(leak) or levels off (cache).

**What to record at each reading (after `gc.collect()` twice and a pump
that sends `DeferredDelete`):**

1. Process private bytes (`memory_mb()` from the Device Mapping Editor
   smoke) and the Python heap: `tracemalloc.get_traced_memory()` plus a
   `tracemalloc` snapshot; the top 15 `compare_to(..., "lineno")` lines
   between block 1 and block 3.
2. Python object counts by type for the 81 QML-made types, split into
   **valid** (`shiboken6.isValid`) and **kept shells** (invalid).
3. For the kept shells: the size of what they keep alive, measured as the
   set of objects reachable from their `__dict__` (walk `gc.get_referents`,
   stop at modules, classes and valid singletons) and the sum of
   `sys.getsizeof` over it; plus whether any reachable object is a
   `gremlin.profile.Profile`, `InputItem`, `Device` or a mode tree.
4. QObject counts: the number of QObjects under the engine and windows
   (`engine.rootObjects()` recursive `findChildren(QtCore.QObject)`), to
   confirm the C++ side really is freed.
5. Counts of `gremlin.profile.Profile` objects alive (scenario A must be 1
   or 2, never growing).

**Pass / fail:**

- PYSIDE-WRAPPERS stays "harmless" only if, from block 1 to block 3:
  private bytes grow under 2 MB in total (in line with the 1-2 MB Qt
  keeps per the 2026-10-02 note), the kept shells' reachable size is under
  2 KB per shell, no kept shell reaches a `Profile`, `InputItem`, `Device`
  or mode object, live `Profile` objects stay at 2 or fewer, and the valid
  object counts and QObject counts are flat.
- It is a real leak (upstream's reading holds) if private bytes grow
  linearly over the three blocks (each block adds about the same, over
  1 MB per 25 repetitions), or any kept shell keeps a profile or device
  object alive, or `Profile` count grows with each load.
- In between (shells small, but tens of thousands after a long session):
  report the per-repetition figure and how many repetitions make 10 MB, and
  let the user decide.

**Run time:** about 5-8 min of wall time for the four scenarios in
parallel processes (each 77 repetitions; the slowest, scenario A with
real profiles, about 0.6-1.5 s per repetition: **no timing data yet; rough
guess**). Writing the probe: 3-8 min (timings.md: agent fix / feature).
Total with lead checks: about 15-20 min (rough guess, adding the table's
steps; no CI, nothing committed unless the user wants it kept as a test).

**Note for whoever builds it:** `test_leaks.py`'s comment and
`counts()` filter would have to be read again after the result; if the
shells turn out costly, both that comment and the 01 gap note are wrong
and the gap becomes a spec matter for the user (port upstream's factory
pattern, or a smaller fix: clear `__dict__` on `destroyed` in a shared base
class). That is a design choice for the user, not part of this study.

---

## 16. 2af6d18a: the 18 macro scheduling tests on our macro manager

### The two managers in short

**Upstream (2af6d18a, `gremlin/macro.py`).** No scheduler thread. One
`threading.Condition` guards `_waiting_macros` (list of `MacroExecution`)
and `_running_macros`. API: `run_macro`, `stop_macro`, `toggle_macro`,
`start`, `stop`. `stop_macro` sets `stop_requested`: the current
repetition finishes, the repeat delay (`stop_requested.wait(delay)`) ends
at once, no delay after the last repetition. A Hold macro already active
ignores another `run_macro`; a Toggle macro that is waiting or running is
stopped by `toggle_macro`. Exclusive: waits for an empty running set;
everything behind a waiting exclusive waits too; preemptive pauses others
via the condition. Profile stop: waiting dropped, running get
`STOP_GRACE_PERIOD = 1.0` s to finish their repetition, then aborted;
`code_runner` runs `MacroManager().stop()` and `VJoyProxy.reset()` on a
background thread and the next start joins it
(`wait_for_macros_to_terminate`). Threads are plain `threading.Thread`.
`MacroFunctor` uses `value.mode_type == types.ModeType.Native` and returns
a bool (paired-event protocol). `MapToKeyboardFunctor` no longer uses
macros: it calls `keyboard.send_key_down/up` directly on the event thread.

**Ours (`gremlin/macro.py:69-434`).** A "macro scheduler" thread
(`threads.start`) drains `_queued_macros` (`MacroEntry(macro, state,
chain)`); API `queue_macro(macro, chain=())`, `terminate_macro(macro)`,
`start`, `stop`. Single flags `_is_executing_exclusive` /
`_is_executing_preemptive`. Repeat delay is `self.sleep(delay)`, which
waits on `_stopped` (Stop only), not on the macro's own stop. Stop (06
END_WORK stage) ends everything at once (spec 05 S92), with `_step_lock`
so no step lands after RELEASE_HELD (06 S21, S32), run numbers
(`run_scope`), `run_scope.owning(macro)` and `release_owner` (05 S100,
06 S70), Logical Device chain continuation (06 S94a). Hold macros stop
through a `ButtonReleaseActions` release callback
(`action_plugins/macro/__init__.py:751-757`). Map to Keyboard queues a
one-step press macro and a release macro (`map_to_keyboard/__init__.py:68-70`).

### Harness difference (every test)

Upstream's `jgbot` takes input labels (`press_button("Hold pulse every 5s
[out_button_1]")`) and compares `EventSpec("out_button_1", True)`; profile
version 14 with `<label>`s. Ours (`test/action_interaction/conftest.py`)
takes input ids (`press_button(1)`), `next_event()` returns an `Event`,
profiles are version 16. Every test needs its calls rewritten to ids and
its checks to our event fields, and `macro_scheduling.xml` (964 lines)
rebuilt as a v16 profile (same macros: Logical Device buttons 21-30, pause
0.3 / 0.1 / 1.5 s, repeat delays 5 s / 0.2 s, profile macro delay 0). The
keyboard test also needs our key-send mock (upstream patched
`test/application/conftest.py`). Effort for the port of all 18 plus the
profile: 5-10 min (timings.md: refactor, one agent).

### Predictions (from code, not run)

| # | Test | Ours | Why (our code) | Spec |
|---|---|---|---|---|
| 1 | hold_macro_restarts_after_release | **Fail** | Release during the 5 s repeat delay: `terminate_macro` sets the flag, but `sleep(delay)` waits on `_stopped` only, so the macro stays in `_scheduled_macro` for 5 s; and if release and press are both queued before the scheduler wakes, the terminate entry removes every queued entry with the same id (`macro.py:205-208`), dropping the new press | 05 S65 (repeat with delay) silent on this |
| 2 | hold_macro_finishes_repetition_before_restarting | **Fail** | The repetition does finish (first round `own_flag=False`), but then the 5 s sleep; the restart comes after 5 s or is dropped as in 1 | same |
| 3 | hold_macro_never_runs_during_exclusive_macro | Pass | Hold waits behind `_is_executing_exclusive`; the release's terminate entry removes it from the queue | S66 |
| 4 | hold_macro_runs_after_exclusive_macro | Pass | `_finish_macro` clears the flag and wakes the scheduler, the hold dispatches | S66 |
| 5 | toggle_macro_never_runs_during_exclusive_macro | **Fail** | `queue_macro` treats a Toggle as "off" only when it is in `_scheduled_macro`; a waiting toggle is not, so the second tap queues a second run and the toggle runs after the exclusive | S65 |
| 6 | toggle_macro_runs_after_exclusive_macro | Pass | queued, dispatched after | S66 |
| 7 | toggle_macro_restarts_after_toggling_off | **Fail** | Both taps during the 5 s delay find it scheduled, so both are terminates; it never restarts | S65 |
| 8 | toggle_macro_finishes_repetition_before_restarting | **Fail** | Same: off, off; the repetition finishes (False comes) but no restart | S65 |
| 9 | release_macro_runs_in_parallel_with_hold_macro | Pass | different macro ids, both non-exclusive, dispatched together | S65 |
| 10 | map_to_keyboard_runs_during_exclusive_macro | **Fail** | Map to Keyboard's press is a non-exclusive macro and waits behind the exclusive one, so K is not down after 0.05 s | 05 S85 says keys are held while the input is held: **today's code is a gap against S85** |
| 11 | hold_macro_activated_on_press_and_release_stops_on_release | Pass (timing-sensitive) | The release queues a second run, then the release callback's terminate removes it; the 0.2 s delay ends the loop. A slow release (>0.2 s after the first event) could log a second axis event | S65 |
| 12 | empty_macro_does_not_block_next_macro | Pass | `_preprocess_macro` returns on empty; the empty thread ends at once (S92 "an empty macro does nothing") | S92 |
| 13 | macro_runs_twice_when_triggered_while_running | Pass | a second entry for a scheduled id stays queued (`continue`) and runs after | S65 |
| 14 | count_macro_restarts_after_finishing | **Fail** | `_run_steps` sleeps the repeat delay after the last count too (`macro.py:376-377`), so the macro stays scheduled 5 s and the second tap waits. (Also unverified: whether our event logger records a second True on a Logical Device button already True) | S65 |
| 15 | macro_waits_for_exclusive_macro_after_preemptive_macro_ends | **Fail** | When the preemptive macro ends, `_finish_macro` sets `_is_executing_exclusive = False` although the paused exclusive is still running, so the plain macro starts before the exclusive's release: order 4 False, 8 True, 3 False instead of 4, 3, 8. A real bug in ours | S66 (exclusive blocks others): **gap against S66** |
| 16 | waiting_macro_is_dropped_on_profile_stop | **Fail** | Waiting macro is dropped (good), but our Stop ends the running exclusive at once without its release step; the Logical Device button goes back to rest silently in the NEUTRAL stage (`LogicalDevice...to_neutral`, no event), so the expected "out 3 False" never comes | 05 S92, 06 S32: ours follows its spec; upstream's expectation contradicts it |
| 17 | running_macro_finishes_on_profile_stop | **Fail** | Same as 16: we abort, upstream finishes the repetition within 1 s | contradicts S92 |
| 18 | running_macro_aborted_after_stop_grace_period | Pass | We abort at once and the neutral reset sends no event; upstream gets there after 1 s | S92 |

Summary: 9 pass, 9 fail. Of the fails, 2 are gaps against our own spec
(10: S85; 15: S66), 5 are behaviour our spec does not decide (1, 2, 5, 7,
8, 14: repeat delay not ended by the macro's own stop, delay after the last
count, toggle while waiting), and 2 (16, 17) contradict our spec S92.

### The lead's question: take 2af6d18a as-is, with the rename?

**Short answer: the concern is valid, but the rename is the small part.**
The rename itself is mechanical and touches few places; the as-is port is
not, because upstream's manager drops things our spec and Stop stages
require.

**Every caller of our macro manager API** (`queue_macro`,
`terminate_macro`, `default_delay`, `start`, `stop`):

| Where | Call | Needs, as-is |
|---|---|---|
| `action_plugins/macro/__init__.py:751-757` | `queue_macro(self.macro, chain)`; release callback `terminate_macro` | rewrite to upstream's functor (`run_macro` / `stop_macro` / `toggle_macro`), but it uses `value.mode_type` / `types.ModeType` (we have no `ModeType`: grep of `gremlin/types.py`, `base_classes.py` finds none) and returns bool (ours returns None); and it drops our Logical Device chain argument (06 S94a) |
| `action_plugins/map_to_keyboard/__init__.py:68-70` | `queue_macro(self.press/release)` | upstream sends keys directly; then the keys are no longer owned by a macro, so the Stop release path (06 S21, `test_audit3_run_stop.py::test_map_to_keyboard_keys_are_released_when_stop_drops_the_release`) must be checked (**unverified** whether `keyboard.send_key_down` is tracked by `run_scope` on our side) |
| `gremlin/input_refresh.py:55` | `queue_macro(action)` (start-up axis values, one-shot) | `run_macro(action)`; mechanical |
| `gremlin/code_runner.py:508` | `MacroManager().default_delay = settings.effective_macro_delay()` (per-profile macro delay) | upstream has no `default_delay`; it reads `Configuration().value("action", "macro", "default-delay")` at each run, so our per-profile delay (Profile Settings, `test_profile_settings.py`) would be lost unless kept |
| `gremlin/code_runner.py:571`, `:647` | `start()`; `stop()` in the END_WORK stage | upstream moves stop to a background thread with `VJoyProxy.reset()`; ours must keep it in END_WORK, before RELEASE_HELD and DRIVERS (`output.reset_drivers`, 06 S49) |
| `test/fixtures/scripts/macro_from_button.py:34` | `queue_macro(tap)` | `run_macro(tap)`; one line, plus its docstring. Its users: the script test suite (3552b222) |
| Tests calling the API | `queue_macro`/`terminate_macro` 21 calls in 8 files: `test_action_fixes.py` (4), `test_audit2_macros.py` (3), `test_audit3_run_stop.py` (5), `test_audit_runtime.py` (2), `test_batch1_run_callers.py` (2), `test_batch2_b2a_input_events.py` (1), `test_device_layout_change.py` (2), `test_final_06.py` (1) | rename is mechanical; but 10 files also reach into internals that upstream removes (`_queued_macros`, `_scheduled_macro`, `_executing_macro`, `_step_lock`, `_stopped`, `default_delay`): `action_interaction/test_macro.py`, `test_action_fixes.py`, `test_audit2_macros.py`, `test_audit3_run_stop.py`, `test_audit_runtime.py`, `test_batch1_run_callers.py`, `test_bounded_waits.py`, `test_crash_and_loss_fixes.py`, `test_final_06.py`, `test_stage1_runtime.py`; 44 `default_delay` uses in tests and program outside `macro.py` (7 test files) |
| Help (`qml/`, `theme/`) | none | no Help text names the API (grep found none) |
| Spec / map | 05 lines 140, 163, 277 (Map to Keyboard "queues a press macro"; Macro "queues the macro in MacroManager"); 06 lines 30, 84, 92-93, 96 (`_queued_macros`, `_scheduled_macro`, `_executing_macro`), 137-138, 224 ("macro scheduler" thread row) | sections 2-5 rewritten; 06 S65/S66 tests renamed |

**Where upstream's semantics clash with ours** (the reason as-is is not
mechanical):

1. **Stop.** Upstream lets a running macro finish its repetition for up
   to 1 s after Stop, in a background thread, with Pause waiting only on
   abort. Our spec 05 S92 says a macro stops with Stop and Pause and the
   repeat delay end at once; 06 S32 bounds Stop; 06 S21 and our
   `_step_lock` guarantee no step's press lands after RELEASE_HELD. Upstream
   has no step lock: a macro still finishing after our Stop returns could
   press a vJoy button or key after the releases, and after DRIVERS. Tests
   16 and 17 encode upstream's rule; taking them as-is means changing S92
   (a user decision).
2. **Threads.** Upstream starts `threading.Thread(daemon=True)` per
   execution; our rule is threads through `gremlin.threads` with bounded
   waits (memory: program thread rules; 06 line 224 thread table; the hang
   tools in `test/hang_trace/stall_watch.py` look for our names).
3. **Run ownership.** Upstream has no `run_scope.owning`, `release_owner`
   or run number check: a macro released early would not let go of what it
   holds (05 S100, 06 S70), and a macro from an earlier Run could change
   the new Run's state (our `_finish_macro` guard).
4. **Logical Device chain** (06 S94a, `logical_loop.continuing(chain)`) is
   missing upstream.
5. **Input thread** (05 S90, D-06-INPUT-THREAD, 2026-11-19): upstream's
   commands run under a `Condition` on the event thread and start threads
   from there; that fits our input thread, but Map to Keyboard sending keys
   directly on the input thread is a behaviour change for S85 (good: it
   fixes test 10) that needs the Stop-release check above.
6. **Per-profile macro delay** (code_runner.py:508) lost, as above.
7. **Failing step** (our `_execute_macro` logs and ends only that macro,
   `test_audit_runtime.py`): upstream's `_execute` has try/finally only, so
   an exception ends the thread with a traceback (**unverified** how our
   `threads` would report it).
8. **Stuck driver step** (06 S32, `test_a_step_stuck_in_a_driver_ends_the_other_macros`):
   upstream has no bounded step lock.

Upstream's semantics that agree with or improve on ours: one owner of
bookkeeping under one lock (no scheduler thread), per-execution stop flags
(fixes 1, 2, 7, 8, 14), a waiting toggle counts as active (fixes 5),
exclusive rule computed from the running set instead of single flags
(fixes 15, our S66 gap), Map to Keyboard off the macro queue (fixes 10, our
S85 gap).

**Is the concern valid?** Yes. "It breaks our macro example script and
every caller" is true but understates it: the script and the program
callers are 6 one-line renames; the real breakage is that upstream's
manager removes behaviour our spec requires (S92 Stop, 06 S21/S32 step
lock, S100/S70 ownership, S94a chain, per-profile delay, thread rule) and
10 test files that pin it.

### Options

- a) **Port the design, keep our guarantees (recommended).** Rewrite our
  `MacroManager` on upstream's model (one `Condition`, `MacroExecution`
  with stop/abort flags, waiting list, exclusive rule from the running
  set), keeping `threads.start`, `run_scope` ownership and run numbers,
  the chain, `_step_lock`, the per-profile delay, and our immediate Stop.
  Rename to `run_macro` / `stop_macro` / `toggle_macro` at the same time
  if the user wants it (the clean design: no shim). Port the 18 tests;
  16 and 17 change to our Stop rule (the running macro ends at once, its
  button goes to rest) unless the user changes S92. Map to Keyboard sends
  keys directly, with a test that Stop still releases them.
  Spec: 05 S65/S66 get the new statements (repeat delay ends on the
  macro's own stop; no delay after the last count; a waiting Toggle counts
  as on; exclusive waits stay correct after a preemptive ends); S85 gap
  closed; 05/06 sections 2-5 and the 06 thread row updated.
  Effort: 2-3 agents in parallel (manager; functors + input_refresh +
  script + code_runner; tests incl. the 10 internal-state files) 5-10 min
  each (timings.md: refactor), plus spec/map agent 3-8 min (timings.md:
  agent fix / docs), lead checks ~5 min, quick tests, commit ~2 min, CI
  ~25 min (timings.md: CI on a push). About 45 min end to end, most of it
  CI.
- b) **Take 2af6d18a as-is.** Files: `gremlin/macro.py`,
  `action_plugins/macro/__init__.py`, `action_plugins/map_to_keyboard/__init__.py`,
  `gremlin/code_runner.py`, the test conftests, the 18 tests and profile,
  plus every caller above. It does not apply: `macro.py` has diverged by
  +671/-169 lines since the merge base and the functor by +345, and it
  needs upstream's `ModeType`. Making it run means re-adding items 1-8
  above anyway, or changing spec S92, 06 S21, S32, S49, S70, S94a, S100
  and the thread rule (user decisions each). Effort: no timing data for a
  conflicted cherry-pick of this size; rough guess 30-60 min before the
  spec decisions, then as a).
- c) **Fix only our gaps, keep our design and names.** Make `sleep(delay)`
  also end on the macro's own stop, no delay after the last count,
  waiting Toggle counts as on, fix the preemptive-ends flag (15), Map to
  Keyboard off the queue (10), terminate removes only entries queued
  before it (1). Port the 18 tests adapted to our names. Effort: 1 agent
  for `macro.py` + 1 for the functors + 1 for tests, 3-8 min each
  (timings.md: agent fix), plus spec 3-8 min, lead ~5 min, CI ~25 min;
  about 40 min end to end.

The rename question stays the user's: under a) or c) it is a mechanical
change of 6 program/script lines, 21 test calls in 8 files, and the map
pages 05/06.
