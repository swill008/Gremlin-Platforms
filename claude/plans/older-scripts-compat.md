# Plan: the pieces older scripts expect (2026-11-23, planning only)

Planning agent P-OLD, 18:07-18:11, read-only. Status: **plan, not approved
to build.** Nothing in the spec, Help or code has changed.

Question from the user: plan "the pieces older scripts expect": a
`gremlin.input_devices` name, a way for scripts to switch mode, and a
`deadzone` helper, so shared or older Joystick Gremlin scripts run on ours.

Sources (all verified with git in this session; nothing from memory):
upstream tags `Release_10` ... `Release_13.3` (2019-07-16), `Release_14` /
`Release_14.3` (2026-01-17 / 2026-05-14), branches `upstream/r13`,
`upstream/r14` (an old 2022 development branch, not the R14 release),
`upstream/develop`; our `gremlin/user_script.py`, `gremlin/mode_manager.py`,
`gremlin/axis_shaping.py`, `gremlin/modules/output.py`, `gremlin/modules/inputs.py`,
`gremlin/event_handler.py`, `gremlin/types.py`, `gremlin/macro.py`; the
scripts in `claude/audits/2026-11-23-script-examples/` and our suite in
`test/fixtures/scripts/`; spec `claude/program-map/04-profile-modes.md`
S84-S98.

## 1. What upstream actually offered

### Which releases had these pieces

| Piece | R10-R13.3 (2018-2019) | upstream/r14 branch (2022) | R14 release (14.0-14.3, 2026) | upstream develop (today) |
|---|---|---|---|---|
| `gremlin/input_devices.py` (decorators, `deadzone`, `squash`) | yes | yes | **no** | no (removed in d05171cc "Refactoring to fix several cyclical import issues") |
| `gremlin/control_action.py` (`switch_mode` etc.) | yes | yes | **no** | no (removed in 447d9806 "Event type updated with mode information and mode manager updates") |
| `gremlin/user_plugin.py` (R13 variables) | R13 only | yes | **no** (replaced by `gremlin/user_script.py`, added a472bac8) | no |
| `deadzone` for scripts | `input_devices.deadzone` | same | **none** (only `user_script.clamp_value`) | none |
| Script mode switch | `control_action.switch_mode` | same | **none**; upstream's own test calls `ModeManager().switch_to(Mode(...))` | same |

So the three pieces are **R13-era** (Release_13.3 and earlier). Released R14
has none of them; our scripting already matches R14 (see the audit README).
Supporting them is compatibility with upstream R13 scripts, which the user
wants; it is not a shim for an old version of ours.

### `gremlin.input_devices` in R13 (`git show Release_13.3:gremlin/input_devices.py`, 904 lines on r13)

- `JoystickDecorator(name, device_guid, mode)`: `device_guid` is a GUID
  **string** (`"{a48e6486-...}"`), parsed by `profile.parse_guid`; a bad one
  logs "Invalid guid value" and uses `GUID_Invalid`. `.axis(n)`, `.button(n)`,
  `.hat(n)` are decorators, each also taking `always_execute=False`.
- `keyboard(key_name, mode, always_execute=False)`: key by name
  (`macro.key_from_name`).
- `periodic(interval)`.
- `callback_registry`, `periodic_registry` (module globals; `periodic_registry.stop()`
  stops the shared timer thread).
- Plugins by parameter name: `vjoy`, `joy`, `keyboard` (same as ours).
- `JoystickProxy` (`joy[guid]`), `JoystickWrapper` (`.axis(n).value`,
  `.button(n).is_pressed`, `.hat(n).direction`, `axis_count`), `Keyboard.is_pressed`.
- `squash(value, func)`: `(2 * func(value)) / abs(func(-1) - func(1))`.
- `deadzone(value, low, low_center, high_center, high)`, limits
  `-1 <= low < low_center <= 0 <= high_center < high <= 1`:
  `value >= 0`: `min(1, max(0, (value - high_center) / abs(high - high_center)))`,
  else `max(-1, min(0, (value - low_center) / abs(low - low_center)))`.
  Divides by zero when `high == high_center` or `low == low_center`.
- Hat event values are `(x, y)` tuples (`event_handler.py` on r13:
  "hat position as a unit tuple (x, y)"); vJoy hats take tuples.
- The r14 branch only added type hints, `button_count`/`hat_count` and
  `format_input` (git diff r13..r14: 233 lines, no signature changes to the
  above).

### `gremlin.control_action` in R13 (`Release_13.3`, 89 lines)

- `switch_mode(mode)`: `EventHandler().change_mode(mode)` (mode is a name).
- `switch_to_previous_mode()`: `change_mode(eh.previous_mode)`.
- `cycle_modes(mode_list)` with `ModeList(modes)`: `ModeList.next()` starts at
  index 0 and returns index 1 first (the docstring's "first mode if the
  current one is not in the list" is not what the code does).
- `pause()`, `resume()`, `toggle_pause_resume()`: `EventHandler().pause/resume/toggle_active`.

### What the found scripts use (audit README table)

| Old API | Used by | In R13.3 itself? |
|---|---|---|
| `gremlin.input_devices.JoystickDecorator` with GUID string | GremlinEx docs, script_only.py, trim.py | yes |
| `JoystickDecorator` with **integer** device ids | r13 example sc.py (2016, never updated), hats2buttons.py, trim.py | **no**: R13's own changelog says integer ids stopped working in R13 |
| `input_devices.deadzone` | script_only.py | yes |
| `input_devices.keyboard`, `input_devices.periodic` | sc.py, encoder_push.py | yes |
| `input_devices.periodic_registry.stop()` | encoder_push.py | yes |
| `gremlin.control_action.switch_mode` | sc.py | yes |
| `from gremlin.user_plugin import *`, R13 argument order (is_optional last), `var.value["device_id"]` | offset_throttle, active_device_switcher, push, toggle, encoders, accelerated encoder, stepped axis (7 of the 11 gists) | yes |
| `input_devices.JoystickPlugin.joystick` / `VJoyPlugin.vjoy` at load | toggle_1x2_3pos.py | yes |
| hat tuples `event.value == (0, 1)` | sc.py, hats2buttons.py | yes |
| `vjoy[1].axis[AxisName.X]` (subscript), `from vjoy.vjoy import AxisName` | sc.py, hats2buttons.py (`button[1]`) | **no**: R13 `VJoy.axis()` is a method |
| `macro.Keys`, `Macro.run()` | sc.py | **no**: not in Release_10 through Release_13 macro.py (gone before R10) |
| `gremlin.util.display_error` | hats2buttons.py | R10-era; not checked further |
| GremlinEx `gremlin_start/stop/state/mode`, `gremlin.remote`, `hardware` | GremlinEx scripts | GremlinEx only |

## 2. How we would offer them (cleanest design first)

One owner: `gremlin/user_script.py` stays the only script API. The upstream
names are **thin modules that re-export or wrap it**, with no state of their
own, so nothing can drift and S89 (vJoy/joy/keyboard only through the
modules) holds by construction: they hand out the same `VJoyPlugin.vjoy`,
`JoystickPlugin.joystick`, `KeyboardPlugin.keyboard` objects.

### Piece 1: `gremlin/input_devices.py` (new, thin)

- Re-exports from `user_script`: `JoystickDecorator`, `keyboard`, `periodic`,
  `callback_registry`, `periodic_registry`, `VJoyPlugin`, `JoystickPlugin`,
  `KeyboardPlugin`, plus `deadzone` and `squash` (piece 3).
- Real changes in the owner, `user_script.py` (useful to R14-style scripts too):
  - `always_execute=False` on `JoystickDecorator.axis/button/hat`,
    `keyboard(...)` and `PhysicalInputVariable.decorator(...)`: sets
    `wrapper_fn.always_execute = True`; `event_handler.py:963-965` already
    honours that attribute while paused. Without it an R13 script that pauses
    can never resume itself (pause stops its callbacks).
  - `JoystickDecorator` already accepts `"{...}"` GUID strings (`uuid.UUID`
    takes braces). Integer ids: a clear load error instead of a silent
    "Invalid guid" log: "Joystick Gremlin R12 device numbers no longer work:
    use the device's id from the Device Library" (wording via the glossary).
- Hat tuples (R13 behaviour) only through the `input_devices` decorators:
  `input_devices.JoystickDecorator.hat` hands the callback an event whose
  `value` is the `(x, y)` tuple of the `HatDirection`; `user_script`
  decorators keep `HatDirection` (R14). The output module's hat write
  (`modules/output.py` `write_vjoy`, kind "hat") also accepts a tuple through
  `HatDirection.to_enum` (already takes tuples, `types.py:400`). Question 2.
- Not offered: `JoystickProxy`/`JoystickWrapper` class names (scripts get
  `joy` by parameter, which already works); `format_input`.

### Piece 2: switching mode from a script

- Owner: new functions in `user_script.py` (script API), calling the same
  `ModeManager` methods the Change Mode action uses
  (`action_plugins/change_mode/__init__.py:106-120`), always on the input
  thread (where the mode stack lives since D-06-INPUT-THREAD) through
  `mode_manager._on_input_thread` (promoted to a public name), so a call from
  the periodic "user script timers" thread or a macro thread is safe and
  never waits (thread rules: `input_thread.call`, no blocking):
  - `switch_mode(name)`: `switch_to(Mode(name, current))`; a mode not in the
    profile logs once and changes nothing (existing `switch_to` behaviour).
  - `previous_mode()`: `ModeManager.previous()`.
  - `cycle_modes(names)`: `ModeManager.cycle(ModeSequence(names))` (ours goes
    to the mode after the current one; R13's counter-based `ModeList` did not).
  - `pause()`, `resume()`, `toggle_pause()`: `EventHandler` on the input thread.
- `gremlin/control_action.py` (new, thin): the R13 names `switch_mode`,
  `switch_to_previous_mode`, `cycle_modes`, `pause`, `resume`,
  `toggle_pause_resume` and `ModeList` (a `ModeSequence` with R13's
  constructor) calling the functions above. Question 1 decides whether this
  module exists or only the `user_script` names.

### Piece 3: `deadzone` (and `squash`)

- Owner already exists: `gremlin/axis_shaping.py:deadzone`, the same formula
  as R13 plus a 0.01 floor on the divisor (no divide-by-zero). Re-export it as
  `user_script.deadzone` and `input_devices.deadzone`. Results equal R13's for
  every valid limit set; only the zero-width case differs (R13 raised
  ZeroDivisionError). Add `squash` next to it (pure maths, R13 formula).

### Commonly needed alongside: feasible or not

| Old API | Feasible? | Recommendation |
|---|---|---|
| `gremlin.user_plugin` with R13 argument order and `.value` dicts (7 of 11 gists) | Yes: thin subclasses in a new `gremlin/user_plugin.py` that take R13's order (is_optional last, keyword) and give `VirtualInputVariable.value` / `PhysicalInputVariable.value` as R13's dicts (`device_id`, `input_id`, `input_type`, `device_name`) read-only, saving exactly like ours | Biggest win for shared scripts; question 3 |
| `input_devices.JoystickPlugin.joystick` / `VJoyPlugin.vjoy` at load | Yes (re-exports) | Included in piece 1. Writing vJoy at load (before Run claims outputs) may be refused: unverified, test it |
| `periodic_registry.stop()` from a script | Already "works" but stops every script's timers (shared registry) | Question 4 |
| Integer device ids (pre-R13) | **No**: R13 itself dropped them; there is no mapping from the old number to a GUID | Clear load error only |
| `vjoy[1].axis[AxisName.X]`, `button[1]` subscripts, `vjoy.vjoy.AxisName` | Technically yes (index objects on `_ScriptDevice`), but pre-R13 and `vjoy.vjoy` is the driver package (layer rule: scripts don't import it) | No; Help shows the rewrite |
| `macro.Keys`, `Macro.run()` | `run()` = `MacroManager().queue_macro(self)` is trivial; `Keys` is a large table; both pre-R10 | No; Help shows `Macro().tap("KP5")` + `queue_macro` (our `Macro.action` takes key names) |
| `gremlin.util.display_error` | Would need a UI call from a script thread | No |
| `types.Event` annotation (upstream R14 example.py) | Yes (alias to `event_handler.Event`) | Already a pending decision (suite fixture `upstream_example.py` xfail); not part of this plan |
| GremlinEx hooks (`gremlin_start/stop/state/mode`, `gremlin.remote`) | No (GremlinEx-only design) | No |

## 3. Spec statements to add (draft, page 04; next free number is S99)

- S99. It should accept scripts written for Joystick Gremlin R13's script
  modules: `gremlin.input_devices` (`JoystickDecorator` with a device id
  string, `keyboard`, `periodic`, `deadzone`, `squash`, the `vjoy`, `joy` and
  `keyboard` plugins) and `gremlin.control_action` (`switch_mode`,
  `switch_to_previous_mode`, `cycle_modes` with `ModeList`, `pause`,
  `resume`, `toggle_pause_resume`). These names are the same objects as
  `gremlin.user_script`'s, so S89 applies to them unchanged.
- S100. A script's decorators should take `always_execute`; such a callback
  runs while paused (S91).
- S101. A script should be able to change the mode with
  `user_script.switch_mode(name)`, `previous_mode()`, `cycle_modes(names)`,
  and pause or resume with `pause()`, `resume()`, `toggle_pause()`, from any
  of its callbacks or periodic functions; the change happens on the input
  thread like the Change Mode action, and a mode the profile does not have
  changes nothing and is logged once.
- S102. `user_script.deadzone` and `squash` should give R13's results for
  valid limits; a zero-width zone gives no error.
- S103. (if question 2 a) Callbacks made with `gremlin.input_devices`
  decorators get hat values as R13's `(x, y)` tuples; vJoy hats accept a
  tuple or a `HatDirection`.
- S104. (if question 3 a) `gremlin.user_plugin` should accept R13 user
  plugins unchanged: R13's variable argument order and the `value`
  dictionaries of Virtual and Physical input variables.
- S105. A script that names a device by a pre-R13 number should fail to load
  with a message saying to use the device's id from the Device Library.

Map updates in the same batch: page 04 section 2 (new files
`gremlin/input_devices.py`, `gremlin/control_action.py`, maybe
`gremlin/user_plugin.py`), 3 owns, 4 entry points (the script-facing names),
5 talks to (mode_manager, event_handler, axis_shaping, input_thread),
6 threads (script mode calls go through `input_thread.call`), 10 gaps
(close the audit's three gaps), 11 tests, README counts.
`test_program_map_covers_files.py` fails until the new files are listed.

## 4. Help (to-do 146: no topic on writing scripts)

New topic in `qml/help/options_profile.js`, after `options-profile-scripts`:
`options-profile-scripts-writing` "Writing a script" (variables, decorators,
`vjoy`/`joy`/`keyboard` by parameter name, claimed outputs only (S89),
switch mode, deadzone), and `options-profile-scripts-older`
"Scripts from Joystick Gremlin R13 and earlier": what runs unchanged
(S99-S104), what to edit (integer device ids, `vjoy[1].axis[...]`,
`macro.Keys`, `Macro.run()`), each with the one-line replacement. Follow
`claude/plans/help-style-guide.md` and the glossary; `test_help_links_resolve.py`
covers the links.

## 5. Tests (suite style: `test/fixtures/scripts/` + `scripts.json` + `test_script_suite.py`)

Fixtures written by us (gists have no licence; R13 example is GPL v3 but
uses pre-R13 APIs):
1. `r13_input_devices.py`: `gremlin.input_devices.JoystickDecorator` with a
   `"{GUID}"` string, button to vJoy button, axis through `deadzone` to a vJoy
   axis, `keyboard("F1", "Default")`, a `periodic` counter.
2. `r13_control_action.py`: button calls `gremlin.control_action.switch_mode`,
   another `cycle_modes(ModeList([...]))`, a third pauses and an
   `always_execute=True` one resumes.
3. `r13_hat_tuples.py` (if q2 a): `if event.value == (0, 1)` presses a vJoy
   button; `vjoy[1].hat(1).direction = (1, 0)`.
4. `r13_user_plugin_unchanged.py` (if q3 a): `from gremlin.user_plugin import *`,
   R13 argument order, `virtual.value["device_id"]`.
5. `r12_integer_device_id.py`: must fail to load with the S105 message.
6. Periodic `switch_mode`: called from the timers thread, the mode change is
   seen on the input thread (`input_thread.is_input_thread()` inside the
   switched callback) and never blocks.

Unit tests: `deadzone` equals Release_13.3's formula on a grid of valid
limits (formula copied into the test with its GPL credit); `squash`; an
identity guard (`input_devices.X is user_script.X` for every re-export,
so a second owner fails the test); S89 through the old names (unclaimed
vJoy output still blocked via `input_devices`); unknown mode logged once.
End to end: `test_scripts_window_e2e.py` gets fixtures 1-2 (Run drives the
vJoy stand-in and the mode). Then the standing build, silent install and
live `gremlin-ctl` check before push.

## 6. Risks

- `always_execute` lets a script keep acting while the user paused: it is
  the user's own script, and R13 had it; Help says so.
- Two hat value types in one program (tuple via `input_devices`, `HatDirection`
  via `user_script`): confined to the old decorators; documented.
- `control_action` names a module that sounds like an action plugin; it is
  script-only (map page 04, not 05).
- `ModeList` behaviour differs from R13 (from the current mode, not a
  counter): the first press of an R13 cycle may land on a different mode.
- `user_plugin` `.value` dicts must stay read-only views; a script writing
  `var.value = {...}` would not save (R13 set values through its UI only).
- Import cycles: upstream removed `input_devices` to fix cyclical imports
  (d05171cc); our thin modules import only `user_script` and
  `axis_shaping`, never the reverse.

## 7. Split into agents (file ownership)

| Agent | Files | Job | Why parallel / why one |
|---|---|---|---|
| OWN | `gremlin/user_script.py`, `gremlin/mode_manager.py` (public `on_input_thread`) | `always_execute`, `switch_mode`/`previous_mode`/`cycle_modes`/`pause`/`resume`/`toggle_pause`, `deadzone`/`squash` re-export, integer-id load error | The owner; others code to the contract below |
| OLD | `gremlin/input_devices.py`, `gremlin/control_action.py` (new) | Thin modules, hat-tuple wrapping | New files only; works to the contract at once |
| OUT | `gremlin/modules/output.py`, `gremlin/axis_shaping.py` | Hat write accepts tuples (q2), `squash` | Separate files |
| PLUG (if q3 a) | `gremlin/user_plugin.py` (new) | R13 variable order and `.value` dicts | New file |
| SUITE | `test/fixtures/scripts/r13_*.py`, `r12_*.py`, `scripts.json`, `test/unit/test_script_suite.py` | Fixtures 1-6 | Test-only |
| UNIT | `test/unit/test_script_compat.py` (new) | Deadzone parity, identity guard, S89 via old names, thread routing | Test-only |
| E2E | `test/.../test_scripts_window_e2e.py` | Fixtures 1-2 in the real program | Test-only, real path |
| DOCS | `claude/program-map/04-profile-modes.md`, map README, `qml/help/options_profile.js`, `claude/todo.md` (146) | Spec S99-S105 (after the user's answers), map sections, Help topics | Own files |

Left out: nothing else; `event_handler.py` needs no change (already reads
`always_execute`). Contract: `user_script.switch_mode(name: str) -> None`,
`previous_mode() -> None`, `cycle_modes(names: list[str]) -> None`,
`pause()/resume()/toggle_pause() -> None`, `deadzone(value, low, low_center,
high_center, high) -> float`, `squash(value, func) -> float`, decorators take
`always_execute: bool = False`; `mode_manager.on_input_thread(fn, *args)`.
7 agents (8 with PLUG).

## 8. Effort (claude/timings.md)

- Agents in parallel: ~10 min (timings.md: agent fix / feature, "a batch of
  parallel agents ~10 min").
- Lead checks and map: ~5 min (timings.md end-to-end line).
- Quick tests `--changed` + pyright: ~9-12 min (timings.md 2026-11-23 rows).
- Build, silent install, live check: ~2-6 min (timings.md build/test rows).
- Commit and push: ~2 min; CI ~25 min in the background (timings.md: CI on a push).
- Total to a push: about 30-35 min, CI ~25 min after. Without `user_plugin`
  (q3 b): about the same (one fewer parallel agent).

## 9. Questions for the user

1. **Mode switching: R13's module name, ours, or both?**
   a) Both: native `user_script.switch_mode` etc. plus a thin `gremlin.control_action`
   with R13's names (recommended: old scripts run unchanged, new ones use ours).
   b) Only `user_script` names (old scripts edit one import).
   c) Only `gremlin.control_action`.
2. **Hat values in old-style callbacks.**
   a) `input_devices` decorators give R13's `(x, y)` tuples and vJoy hats
   accept tuples (recommended: sc.py-style hat code runs unchanged).
   b) Always `HatDirection`; Help shows `HatDirection.to_enum(...)`.
3. **R13 user plugins (`gremlin.user_plugin`, 7 of the 11 shared gists).**
   a) Add it: R13 argument order and `.value` dictionaries (recommended:
   the largest group of shared scripts then runs unchanged).
   b) Not now: Help lists the three edits.
4. **`periodic_registry.stop()` from a script stops every script's timers.**
   a) Keep R13's behaviour (it was shared there too) and say so in Help
   (recommended).
   b) Make it stop only the calling script's timers.
5. **`always_execute`.**
   a) Add it to our decorators (recommended: R13 had it; without it a script
   that pauses can't resume).
   b) Accept the argument but ignore it.

## Upstream comparison per question (lead, 2026-11-23, checked with git on upstream/develop)

User: "when you give me the recommendations, give me also how upstream is
dealing with it, give me a comparison."

| Question | Upstream R13 (2019) | Upstream today (R14 / develop) | Ours today | Recommended |
|---|---|---|---|---|
| 1 mode switch | `gremlin.control_action.switch_mode` etc. | none for scripts (control_action removed in 447d9806; its own test calls `ModeManager().switch_to`) | none | both names, through the Change Mode path |
| 2 hat values | `(x, y)` tuples | `HatDirection` | `HatDirection` | tuples only via old `input_devices` decorators |
| 3 user plugins | `gremlin.user_plugin` | none (replaced by `user_script`, a472bac8; 3 migration edits documented) | none | add `gremlin.user_plugin` wrappers |
| 4 `periodic_registry.stop()` | shared: stops all | shared: `PeriodicRegistry.stop()` stops the one thread for all scripts | shared | keep shared, say so in Help |
| 5 `always_execute` | on script decorators | not on script decorators (only on action sequences, event_handler.py:525) | event_handler honours the attribute; decorators lack the argument | add to our decorators |

## Decision (user, 2026-11-23)

"if upstream drop it, then we will drop it as well. I dont see the need to
maintain compatablity if we can just convert old scripts" and "we wont add a
converter for now, put that as a todo." So: no R13 support (no
input_devices, control_action, user_plugin, hat pairs or always_execute);
we follow upstream today. The converter is to-do 151. This plan stays as
history. Still open: a mode switch for scripts as a feature of our own.
