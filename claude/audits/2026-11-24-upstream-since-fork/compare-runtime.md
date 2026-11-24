# Compare: upstream runtime changes against ours (C-RUNTIME)

Agent C-RUNTIME, 2026-11-23 17:45-17:51, read-only (this file only). Remote
`upstream` fetched, merge base `daf4057f`. Items: (10) release after a mode
change, 188a44d6 + e30732f8 (with b10b3ffc and the later 748479a7 where they
matter); (3) 911444dd sound Stop from another thread; (4) d3f55d9b vJoy driver
checks once per process. Facts are verified from code unless marked
**unverified**.

## Summary

| Item | Gap in ours? | Spec change | Blockers | Effort (timings.md) |
|---|---|---|---|---|
| 10 Release after mode change | Yes, confirmed from code: Map to Keyboard, Map to Mouse buttons, Map to Xbox, vJoy/Logical Device hats, Send OSC, Chain, Condition, Hat Buttons, virtual buttons (axis range, hat direction) and script callbacks lose the release | S38 widened plus S38a-S38d (new), 2 questions for the user | Needs the user's answers on questions 1-3 below; one owner for `event_handler.py` + `base_classes.py` + `code_runner.py` | Refactor 5-10 min per agent, about 6 agents in 2 staggered rounds, about 20 min; plus lead checks ~5 min, quick tests, commit ~2 min, build-install-live test (no timing data; rough guess 10 min), CI ~25 min. About 60-70 min end to end |
| 3 Sound Stop from another thread | Yes, confirmed: `generator.close()` from another thread raises `ValueError: generator already executing` (checked with Python 3.13 in the Poetry venv); we swallow it and the sound plays on | None (S49, S50 already say Stop and Interrupt cut the sound; this fixes a gap) | None | Agent fix 3-8 min |
| 4 vJoy driver checks once | Partly: the checks run on every `VJoy()` open, which our busy retry (every 3 s, S52) repeats for a whole Run. The "leaky DLL functions" claim is upstream's; **unverified** in our vJoy 2.2 notes | None | Tests need a reset of the new flag (`test/vjoy_guard.py`) | Agent fix 3-8 min |

Items 3 and 4 are independent of item 10 and of each other (different files);
they can run as their own agents alongside item 10.

---

## Item 10: the event that ends an activation reaches the press mode

### Upstream, in order

1. **b10b3ffc** (after our fork; our base has no `EventGenerator`): deletes
   `gremlin/event_helpers.py` (`ButtonReleaseActions`) and adds
   `EventGenerator` in `event_handler.py`: it remembers the mode each
   button/hat was last sent in and **re-routes** the release (or a hat centre)
   to that mode; a hat turned to a direction bound elsewhere gets a centre in
   the old mode first; axis bindings left behind by a mode change are reset
   and their pressed virtual buttons keep getting axis events.
2. **188a44d6** replaces `EventGenerator` with **pending callbacks**:
   - `types.ModeType` (`Native`, `Foreign`); `Value(raw, mode_type)`, `Value.clone()`.
   - Every functor `__call__` returns `bool`: "I want this input's next
     event". `AbstractFunctor.waiting_for_event()` (default: any child waits),
     `_requires_paired_event(value, inverted)` (Both activation, start value,
     not an axis), `_sequence_value()` (a continuing event takes the press's
     mode type), `_process_event` returns `any(...)`.
   - `_should_execute(value, inverted)`: a **Foreign** value runs only for
     activation **Both**, only the end value (release, or press when
     inverted, or hat centre), never axes.
   - `EventHandler._pending_callbacks[input] = [callback, ...]`;
     `process_event` runs pending callbacks the current mode doesn't bind as
     Foreign first, then the current mode's as Native; `_set_pending` keeps or
     drops each by its answer. Script callbacks (plain functions) are pending
     while the button is down / hat off centre, and get a centre in place of a
     direction when Foreign. `_mode_changed_cb` resets axis bindings the new
     mode doesn't route the same way.
   - `CallbackObject.__call__(event, mode_type) -> bool`;
     `VirtualButtonFunctor` stays pending while its virtual button is pressed
     or its own callbacks are pending, and stamps `event.mode` on the virtual
     event.
   - Plugins: Map to Keyboard, Mouse, vJoy (inverted button waits for the
     next press via `waiting_for_event`), Logical Device, Macro (Hold needs the
     release), Chain (release advances, foreign press doesn't), Tempo,
     Smart Toggle, Double Tap, Condition, Change Mode, Hat Buttons, Split Axis
     and the rest return their answer.
3. **e30732f8**: `any(generator)` stopped at the first True, so later actions
   in a list never ran; now `any([list])` runs every child first. **Any port
   of the bool protocol must not short-circuit.**
4. **748479a7** (later, not in this item): "virtual button as action"
   rewrites the virtual-button path again and touches every plugin. If the
   user also wants that, plan it together with this item or the plugins are
   edited twice.

Note: upstream gives the end event to **both** the press mode's bindings
(Foreign) and the current mode's (Native); its pending set is a Python `set`,
so the order of foreign callbacks is not fixed.

### Ours today (verified)

- `EventHandler.process_event` (`gremlin/event_handler.py` 865-895) stamps
  the **current** mode on an event with none (every hardware/keyboard event:
  `NO_MODE = ""`), and `_matching_callbacks` (944-967) looks up only that
  mode. Nothing remembers the press mode.
- The only release path across modes is `event_helpers.ButtonReleaseActions`,
  run after the callbacks (`_run_callbacks` 936-942), with registrations by:
  | Registrant | Entry | Covers |
  |---|---|---|
  | `map_to_vjoy` 99 | `DifferentMode` auto-release (OnPress when inverted) | vJoy **buttons** only (S38) |
  | `map_to_logical_device` 114 | same | Logical Device **buttons** only (S38) |
  | `macro` 755 | `IgnoreMode` `terminate_macro` | Hold macros |
  | `change_mode` 121 | `IgnoreMode` | leaving a Temporary mode |
  | `double_tap` 84, `smart_toggle` 102, `tempo` 93 | `IgnoreMode` `_release_cb(Value(False))` | the container's own release |
- `ModeChangeActions` (event_helpers 236-288, fired by
  `CodeRunner._refresh_on_mode_change`, code_runner 763-771) stops Map to Mouse
  **motion** (S88) only.
- No functor `reset()` exists in ours; `_should_execute` (base_classes 730-753)
  knows nothing of modes.
- Virtual buttons: `VirtualButtonFunctor` (code_runner 228-240) emits a
  virtual event carrying the binding's own mode; but the **axis/hat** events
  that drive it go to the current mode only, so a range or hat-direction
  button pressed before a mode change is never released.

**Loses the release after a mode change (confirmed from code):** Map to
Keyboard (keys stay down until Stop's `run_scope.release_held`), Map to Mouse
**buttons** (same), Map to Xbox buttons/hat/triggers, Map to vJoy **hat** and
Logical Device **hat** (stay off centre), Send OSC (no release message),
Chain (doesn't advance), Condition (its true/false children don't get the
release), Hat Buttons (its virtual buttons stay pressed), axis-range and
hat-direction virtual buttons, any action under those, and **user script
callbacks** registered in the press mode. vJoy/LD buttons under Smart Toggle
(`DisableAutoRelease`) rely on Smart Toggle's own release.

### Our design (our runtime, not upstream's rewrite)

Principles from our rules: one owner per job (the event handler owns
routing), the layer rule (hardware -> input module -> wiring -> output module
-> driver: outputs still go only through `gremlin/modules/output.py`, and a
foreign release is just another call into the same action, so the claim gate
in the output module applies unchanged), input thread only (all state below
is touched only on the input thread, `threads.assert_input`; no lock, no
wait, so no new hang or deadlock path), no legacy shim (ButtonReleaseActions'
cross-mode entries go; one mechanism).

**Recommended: "pending bindings" kept by the event handler, asked of the
functors, not returned by them.** Same idea as upstream 188a44d6, but the
functors answer a query (`waits_for_end()`) instead of every `__call__`
changing its return type, so leaf plugins that use `_should_execute` need no
edit at all.

| File | Function | Change |
|---|---|---|
| `gremlin/types.py` | new `ModeType` enum (`Native`, `Foreign`) | as upstream |
| `gremlin/base_classes.py` | `Value.__init__(raw, mode_type=ModeType.Native)`, `Value.clone()` | carry the mode type |
| | `AbstractFunctor._should_execute(value, inverted=False)` | Foreign: only activation Both, only the end value (False, or True when inverted, or `HatDirection.Center`), never a float. On a Native run that returns True, set `self._awaiting_end = _starts_pair(value, inverted)` |
| | new `AbstractFunctor.waits_for_end() -> bool` | `self._awaiting_end` or any child waits (children from `self.functors`); containers override |
| | `_process_event` | runs every child (no short-circuit, e30732f8) |
| | `_pulse_event` | the release value keeps the press's mode type |
| `gremlin/code_runner.py` | `CallbackObject.__call__(event, mode_type=Native)`, `_generate_values` | build `Value(..., mode_type)`; a Foreign hat value is `Center` |
| | new `CallbackObject.waits_for_end()` | root functor's answer; a `VirtualButtonFunctor` waits while its virtual button is pressed |
| | `VirtualButtonFunctor.__call__` | no change to the emitted mode (already the binding's mode) |
| | `CodeRunner.start/stop` | clear the pending table (with the existing `ButtonReleaseActions().reset()` calls at 685, 715) |
| `gremlin/event_handler.py` | `EventHandler._pending: dict[Event, list[callback]]` | per input, in press order (a list, not a set: fixed order) |
| | `process_event` / `_run_callbacks` | for the input: run pending callbacks not in the current mode's list as Foreign (first), then the current mode's as Native (as today). After each run, keep or drop the callback by `waits_for_end()` (CallbackObject) or, for a script callback, by "button still down / hat off centre". `clear()`, `drop_mode()` and `rename_mode()` clear or follow the table |
| | script callbacks (plain functions) | Foreign call gets the event with a hat direction turned to `Center`; called once with the release |
| | hat turned to a direction while the current mode binds the hat elsewhere | the pending old-mode callbacks get a Foreign centre first (S38c) |
| | axis: on a mode change that routes the axis elsewhere (`is_same_binding` false), the old binding's pressed virtual buttons stay pending so the axis keeps reaching them as Foreign until they release (S38d) | from `CodeRunner._refresh_on_mode_change` via `ModeChangeActions` or a direct `EventHandler.mode_changed_to(old, new)` called there |
| `gremlin/event_helpers.py` | `ButtonReleaseActions` | remove `register_vjoy_button_release`, `register_logical_button_release` and the `DifferentMode` path (would release twice). Keep or retire the `IgnoreMode` path: see "Per plugin" |

**Per plugin (which need their own release path):**

| Plugin | Needs a change? | What |
|---|---|---|
| Map to Keyboard, Map to Mouse (buttons), Map to Xbox, Send OSC, Play Sound, Text to Speech, Run Command, Load Profile, Pause/Resume | No | `_should_execute` sets `_awaiting_end` and gates Foreign. Mouse motion stays under S88 |
| Map to vJoy, Map to Logical Device | Yes | drop the `ButtonReleaseActions` registration; inverted button: `waits_for_end()` true while the inverted output is on (read through `output`, never `VJoyProxy` directly, layer rule); hats/buttons otherwise from the base |
| Macro | Yes | Hold: drop `register_callback`; `waits_for_end()` true while its Hold macro runs; Foreign release terminates it |
| Change Mode | Yes | Temporary: drop `register_callback`; Foreign release unwinds only when the current mode is its temporary mode (upstream test `test_temporary_mode_change_ignores_release_in_non_temporary_other_mode`) |
| Double Tap, Smart Toggle, Tempo | Yes | replace the `IgnoreMode` registration with the Foreign path; a Foreign press must not start a new sequence; a continuing event uses the press's mode type (`_sequence_value`) |
| Chain | Yes | release advances the step also when Foreign; a Foreign press doesn't |
| Condition | Yes | Foreign release goes to the branch that ran the press (upstream reworked this heavily; check against ours) |
| Hat Buttons | Yes | Foreign centre releases its pressed direction buttons |
| Axis-only plugins (Response Curve, Split Axis, Merge Axis, Axis Delta, Dual Axis Deadzone) | No | never Foreign for axes; Split Axis drives children by range: check its pending answer |
| Root, Description, Reference | No | default: any child waits |

**Alternative (not recommended): b10b3ffc-style re-routing** of the release
to the press mode only. Smaller (event handler only, no plugin edits), but
release-only actions in the old mode would fire, the new mode's binding no
longer sees the release (today it does), and axis-driven virtual buttons stay
uncovered. Upstream itself moved away from it within a week.

### Spec (06) statements: proposed, need the user's yes (change control 2)

- **S38 (changed):** "After a mode change, the event that ends an activation
  (a button release, a hat back to centre) should also go to the bindings of
  the mode where the press happened, so every action and script callback that
  acted on the press lets go: Map to vJoy, Map to Logical Device, Map to
  Keyboard, Map to Mouse, Map to Xbox, Send OSC, Hold macros, Chain, Tempo,
  Smart Toggle, Double Tap, Condition, Hat Buttons and buttons made from an
  axis range or hat directions." (was: vJoy and Logical Device buttons only)
- **S38a (new):** "From that event only the ending part runs in the old mode:
  actions set to act on press only or release only don't run, and axis values
  are never sent to the old mode."
- **S38b (new):** "A script callback in the press mode gets the release (a
  hat: a centre) once."
- **S38c (new):** "A hat turned to a direction the new mode binds elsewhere
  centres the old mode's binding first."
- **S38d (new):** "A button made from an axis range (S39) pressed before a
  mode change releases when the axis leaves the range, though the axis now
  goes to the new mode."
- S88 (Map to Mouse motion stops on a mode change) is unchanged and stays a
  separate owner (`ModeChangeActions`). Section 2/3/10/11 of page 06 and the
  map lines for `event_helpers.py` change with the code (change control 6).

### Questions for the user (before any code)

1. **Should the new mode's binding still get the release too?**
   Today it does (it gets every event in the current mode). Upstream keeps
   that (Foreign to the old, Native to the new).
   - a) Yes, both get it (recommended: no change for the new mode; matches upstream).
   - b) No, only the press mode gets it.
2. **Pending answer: functors answer a query (`waits_for_end()`), or every
   action returns a bool like upstream?**
   - a) Query (recommended: leaf plugins need no edit; fewer signatures change).
   - b) Bool return, as upstream (closer to upstream for later merges; ~25 `__call__` signatures change).
3. **Do this together with upstream 748479a7 (virtual button as action)?**
   - a) Separately, this first (recommended if 748479a7 isn't wanted).
   - b) Together, if the user wants 748479a7 too (otherwise every plugin is edited twice).

### Existing tests that pin today's behaviour (update in the same batch)

- `test/unit/test_release_reads_live_mode.py` (3 tests, `ButtonReleaseActions` registry and the live-mode read, REL-MODE).
- `test/unit/test_leaks.py::test_presses_in_one_mode_keep_no_release_entries`, `::test_a_release_after_a_mode_change_still_lets_go_once` (LEAK-REL): move to the pending table ("no pending entry left after a same-mode release").
- `test/unit/test_stage1_runtime.py` (around 110, `ButtonReleaseActions`).
- `test/unit/test_audit2_coverage.py` (126-137, `register_callback`).
- `test/unit/test_vjoy_writers_use_firewall.py` (52-53, mocks `register_vjoy_button_release`): rewrite to assert the Foreign release goes through `output.write_vjoy`.
- `test/unit/test_mouse_motion.py` (S88, `is_same_binding`, `ModeChangeActions`): should stay green unchanged.
- Sweep `test/unit/action_matrix/` and plugin tests for `ButtonReleaseActions`, `Value(` with one argument, and `_should_execute` (`update-tests-before-full-run`).

### New failing tests (fail on today's code, drive the real path)

New file `test/unit/test_mode_change_release.py`, through
`EventHandler.process_event` with a real `CallbackObject` and `ModeManager`
switch (no real vJoy; vJoy guard on):
1. `test_a_key_held_across_a_mode_change_is_released`: mode A F13 -> Map to Keyboard X; switch to B; release F13; X's release is queued once (patch `keyboard.send_key_up`/MacroManager). Fails today.
2. `test_a_mouse_button_held_across_a_mode_change_is_released` (Map to Mouse Left).
3. `test_an_xbox_button_held_across_a_mode_change_is_released`.
4. `test_a_vjoy_hat_centres_after_a_mode_change` and `..._logical_device_hat_...`.
5. `test_a_script_callback_gets_the_release_in_its_mode` (a decorator callback in A; one release call).
6. `test_a_release_only_action_in_the_old_mode_does_not_run` (S38a).
7. `test_a_vjoy_button_is_released_once` (no double release once `DifferentMode` entries go).
8. `test_a_hat_turned_in_the_new_mode_centres_the_old_first` (S38c).
9. `test_an_axis_range_button_releases_after_a_mode_change` (S38d).
10. `test_every_action_in_a_list_gets_the_release` (e30732f8 guard).
11. `test_a_temporary_mode_still_unwinds_on_release`, chain/tempo/smart toggle/double tap/condition one each.

### Live test that shows the gap (build, install, gremlin-ctl)

Profile: Keyboard **F13** in mode Default -> Map to Keyboard **X**; Keyboard
**F14** in Default -> Change Mode Switch to **B**; mode B: F13 unbound.
1. `gremlin_run_start`; `gremlin_state` shows mode Default.
2. From a separate Python process, `SendInput` F13 down (no Gremlin mark in
   `dwExtraInfo`, so `_keyboard_handler` takes it as input; Gremlin's own
   keys are ignored only when marked `OWN_KEY_MARK`).
3. `GetAsyncKeyState(VK_X) & 0x8000` is set (X held).
4. `SendInput` F14 down/up; `gremlin_state` shows mode B.
5. `SendInput` F13 up; wait 200 ms; read `GetAsyncKeyState(VK_X)`.
   **Today: X still down** (until Stop's `release_held`). After the fix: up.
6. With `gremlin_trace_on` the Trace shows no OUTPUT key-up line today; one
   after the fix. Then `gremlin_run_stop`.
The control API has no input injection (commands: hello, help, run.start/stop,
profile.load/save, option.get/set, options.list, trace.on/off/status, window
calls), hence the outside `SendInput`. Use a key no game reads (F13/F14) and
the test window off the main screen.

### Risks

- **Double releases** if any `ButtonReleaseActions` cross-mode entry or
  `IgnoreMode` registration stays beside the Foreign path. Remove them in the
  same batch; test 7 guards it.
- **Short-circuit** (e30732f8): any `any(generator)` over children skips
  actions.
- **Stuck pending entries** (a callback that never answers False): cleared at
  Run start, Stop, `clear()`, `drop_mode`; a test that same-mode presses leave
  none (the LEAK-REL lesson).
- **Profile reload inside a callback** (Load Profile): stop processing when
  `self.callbacks` is replaced (upstream does; ours runs on). Check our Load
  Profile path (input thread, D-06-INPUT-THREAD).
- Hangs/deadlocks: none new; everything is on the input thread, no locks or
  waits are added. Pulse (`_pulse_event`) already sleeps 50 ms on the input
  thread today (unchanged).
- Pause: Foreign releases must follow `process_callbacks` like any call
  (upstream `_may_run`); a release during Pause of a press made before Pause is
  a behaviour question already covered by today's rule (only `always_execute`).

---

## Item 3: sound Stop from another thread (911444dd)

**Upstream:** `cancel()` only sets `_cancel_requested`; the generator (run by
miniaudio's audio thread) checks it each callback and ends; a per-sample
`threading.Thread(_close_when_done)` waits (unbounded) for the stream to end,
then `device.close()`; `buffersize_msec=50` bounds the drain to ~50 ms; the
player drops samples with `is_done()`.

**Ours** (`gremlin/audio_player.py` 74-82, 84-100): `cancel()` calls
`self._generator.close()` from the caller's thread (Stop's `_ask_to_stop`, or
the playback thread for Interrupt). While miniaudio's thread is inside
`send()`, CPython raises `ValueError: generator already executing`
(**verified** here, Python 3.13 Poetry venv, a two-thread check); we log it at
debug and the sound **plays on**: S49 (Stop cuts off playing sounds) and S50
(Interrupt stops what plays) fail intermittently. When the stream ends
naturally, the `finally` runs `device.close()` **inside** miniaudio's audio
callback thread; upstream moved the close out of it. That this can hang
miniaudio is **unverified** (it is upstream's reason, not reproduced here).

**Our way:**
- `AudioSample`: keep the samples array, a generator that yields
  `frame_count` slices and stops when `self._cancel` (a `threading.Event`) is
  set; `_stream_done` event set in its `finally`; no `device.close()` inside
  the generator; `buffersize_msec=50`.
- Close on **our** playback thread (no raw `threading.Thread`; program thread
  rules): `AudioPlayer._playback` already prunes finished samples every 10 ms;
  it calls `sample.close_if_done()` there, and on loop exit closes every
  sample (bounded: `_stream_done.wait(0.5)` then close anyway).
- `block(still_wanted)` stays bounded (S55); `done` means "closed".
- No spec change (S49, S50, S52, S54, S55 already require this).

**Tests pinning today:** `test_program_fixes.py` (3 sound tests, a fake
`_Sample`), `test_final_09.py` 85, `test_stage1_runtime.py` 778,
`test_bounded_waits.py::test_a_sound_is_not_waited_for_once_the_player_stops`,
`test_threads.py::test_the_audio_player_stopped_right_after_starting_ends`,
`test_play_sound_missing_file.py`. They fake `AudioSample` whole, so they keep
passing; check the fakes still have `done`/`cancel` and add `close_if_done`.

**New failing test:** `test_audio_cancel_while_playing.py::test_cancel_while_the_audio_thread_is_inside_the_generator_stops_it`:
patch `miniaudio.PlaybackDevice` with a fake whose `start(gen)` runs a feeder
thread calling `gen.send(n)`, and make the stream block inside `send` on an
event the test controls; call `cancel()` while it is inside; release the
event; assert the generator finishes within 0.5 s and `close()` ran on a
thread other than the feeder. Today: `ValueError` swallowed, never finishes.
Second test: `test_a_sound_that_ends_is_closed_off_the_audio_thread`.

**Risks:** a sound plays up to ~50 ms past Stop (the buffer); a missed close
leaves a device open until quit (covered by the loop-exit close).

**Effort:** agent fix 3-8 min (timings.md: agent fix), one agent, one file plus one test file.

---

## Item 4: vJoy driver checks once per process (d3f55d9b)

**Upstream:** class flag `VJoy._driver_verified`; `vJoyEnabled()` and
`GetvJoyVersion() < 0x218` run only until they pass once; the per-device
`GetVJDStatus`/`AcquireVJD` checks still run every open. Reason given:
"leaky vjoy functions".

**Ours** (`vjoy/vjoy.py` 472-480): both checks on every `VJoy(id)`. Callers:
`VJoyProxy.__getitem__` (884) on every open; a device busy in another program
is retried every 3 s for the whole Run (`gremlin/modules/output.py`
`_VJOY_RETRY = 3.0`, S52), so a long Run can call them thousands of times.
`output.vjoy_driver_found()` (756-765, used at 339 and 1145) calls
`vJoyEnabled` on its own and is not covered by the flag.

**Against our vJoy 2.2 notes**
(`claude/audits/2026-11-21-vjoy-22-compat/code.md` rows 2-3, `vm.md`):
`GetvJoyVersion` returns the driver's `VERSION_N` (0x222 for 2.2.2.0, 0x219
for 2.1.9) and both pass `< 0x218`; `vJoyEnabled` is a plain BOOL. Caching
the pass is safe for both drivers. Our notes do not record a leak in either
function: the leak is upstream's claim, **unverified** for us. Caching the
check changes no behaviour a user can see: the driver can't appear while
running anyway (S55 says to restart after installing), and a driver that
goes away later still fails at `GetVJDStatus`/`AcquireVJD` with a VJoyError.

**Our way:** same as upstream (a `ClassVar[bool]` set only after both checks
pass; written under `VJoyProxy._lock`, which every `VJoy()` call already
holds). Optionally cache `output.vjoy_driver_found()` the same way (only once
True; False is re-checked).

**Spec:** none (S55 unchanged; no behaviour change). Commit line
`Spec: none (no behaviour change)`.

**Tests:** `test/vjoy_guard.py` answers `vJoyEnabled: False`,
`GetvJoyVersion: 0`; `test_device_fixes.py` 47-48 and
`test_handson_F7_vjoy_rest.py` 81-82 patch them True/0x219. With a
process-wide flag, a test that passes the check would make a later "vJoy not
running" test pass the check too: reset `VJoy._driver_verified = False` in the
vJoy guard fixture (each test). New test
`test_vjoy_driver_checked_once.py::test_opening_devices_checks_the_driver_once`
(count calls with the guard's call counter: today 2 opens = 2 calls each;
after: 1) and `::test_a_failed_check_is_tried_again`.

**Risk:** none at runtime; the only trap is the test-order leak above.

**Effort:** agent fix 3-8 min (timings.md: agent fix).

---

## Suggested split when the user says build (for the lead's table)

| Agent | Files | Job |
|---|---|---|
| R-CORE | `gremlin/types.py`, `gremlin/base_classes.py`, `gremlin/event_handler.py`, `gremlin/code_runner.py`, `gremlin/event_helpers.py` | pending table, Foreign gate, CallbackObject, virtual buttons (one owner: shared routing) |
| R-OUT | `map_to_vjoy`, `map_to_logical_device`, `macro`, `change_mode` | drop registrations, `waits_for_end` (after R-CORE's contract) |
| R-CONT | `chain`, `tempo`, `smart_toggle`, `double_tap`, `condition`, `hat_buttons`, `split_axis` | container Foreign paths |
| R-TEST | new `test_mode_change_release.py` + pinned-test updates | tests only |
| R-DOC | `claude/program-map/06-runtime-outputs.md`, Help | S38-S38d, sections 2/3/10/11 |
| SND | `gremlin/audio_player.py` + test | item 3 |
| VJ | `vjoy/vjoy.py`, `test/vjoy_guard.py` + test | item 4 |

Contract for R-OUT/R-CONT to start alongside R-CORE: `ModeType` in
`gremlin.types`; `Value(raw, mode_type=ModeType.Native)`, `Value.mode_type`,
`Value.clone()`; `AbstractFunctor._should_execute(value, inverted=False)`,
`AbstractFunctor.waits_for_end() -> bool`, `self._awaiting_end`,
`AbstractFunctor._sequence_value(value, press_value)`.
