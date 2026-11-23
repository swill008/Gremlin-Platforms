# Published example scripts from the original authors (2026-11-23)

Research agent R-SCRIPTS, 17:20-17:27. Question: before writing our own test
scripts, did the original authors publish example or test scripts we could
reuse? Every fact below comes from a page or file fetched in this session
(GitHub API through `gh`, WebFetch, one web search). Nothing was run.

## Sources checked

| Source | Result |
|---|---|
| github.com/WhiteMagic/JoystickGremlin (branches develop, main, r13, r14) | Fetched. LICENSE is GPL v3 ("Joystick Gremlin, Copyright (c) 2015 Lionel Ott and contributors"); source files carry `SPDX-License-Identifier: GPL-3.0-only`. |
| WhiteMagic `develop`: `user_scripts/example.py`, `user_scripts/README.md` | Found. The R14 example script; ours is a copy (see below). |
| WhiteMagic `develop`: `test/unit/test_user_script.py`, `test/integration/test_e2e_user_script.py`, `test/integration/test_e2e_user_script_mode_change.py`, `test/integration/xml/e2e_user_script*.xml` | Found. These are upstream's own script tests. |
| WhiteMagic `r13`: `examples/ch stick and pedals/` (README, sc.py, profile.xml, jkb.xml, empty.xml) | Found. The only example folder upstream has ever had; it is gone on develop. |
| whitemagic.github.io/JoystickGremlin/technical/scripts | Fetched. A stub that says its content is not written yet, plus the R13 to R14 migration list and the variable constructor list. No examples. |
| whitemagic.github.io/JoystickGremlin/user_plugins and /examples (the R13 docs pages, still in search results) | **Fetch failed: HTTP 404.** The R13 docs site has been replaced by the R14 one. |
| github.com/muchimi/JoystickGremlinEx (branch develop) | Fetched. GitHub reports GPL-3.0; file headers say GPL version 3 "or (at your option) any later version" (copyright EMCS / Muchimi, with portions from Lionel Ott). |
| GremlinEx `docs/scripting.md` | Found. Explains user plugins with short code snippets and links one gist. |
| GremlinEx `scripts/` (sc.py 930 lines, msfs.py 790, osc.py 2080, util.py, configuration.py) and `examples/ch stick and pedals/sc.py` | Found. The `scripts/` files are the author's own game set-ups; they import a `hardware` module that is not in the repo. The `examples/` sc.py is the R13 example with a licence header and three renamed functions. |
| Gists (found with one web search, then fetched through `gh api gists/<id>`) | 11 gists by WhiteMagic, IslandJohn, AviiNL, Theaninova and muchimi. **None states a licence**, so they are all-rights-reserved by default: we may read them and write our own scripts that test the same behaviour, but not copy them. |

## Our scripting API (what the comparison is against)

From `gremlin/user_script.py` (1971 lines), `gremlin/modules/output.py`,
`gremlin/modules/inputs.py`, `gremlin/macro.py`:

- Import: `from gremlin import user_script` (or `from gremlin.user_script import *`).
  There is **no** `gremlin.input_devices` and **no** `gremlin.user_plugin`
  module, and no alias for either.
- Variables: `BoolVariable`, `FloatVariable`, `IntegerVariable`, `StringVariable`,
  `SelectionVariable`, `ModeVariable`, `KeyboardVariable`, `PhysicalInputVariable`,
  `VirtualInputVariable`, `LogicalDeviceVariable`, plus our own `OscInputVariable`.
  All take `(name, description, is_optional, ...)`, the R14 signature.
- `PhysicalInputVariable.decorator(mode_var)`, `.create_decorator(mode_str)`,
  `.device_guid`, `.input_type`, `.input_id`; `.value` is a
  `(guid, InputType, id)` tuple.
- `VirtualInputVariable.remap(value)`, `.vjoy_id`, `.input_id`, `.input_type`;
  `.value` always returns `None` (the R13 dict `{"device_id", "input_id"}` is gone).
- Decorators: `user_script.JoystickDecorator(name, guid_string, mode)` with
  `.axis(n)`, `.button(n)`, `.hat(n)`; `user_script.keyboard(key, mode)`;
  `user_script.periodic(seconds)`; `KeyboardVariable.decorator(mode_var)`.
- Callback parameters filled by name: `vjoy`, `joy`, `keyboard`, `osc`.
  `vjoy[n].axis(id or linear_index=)`, `.button(n).is_pressed`, `.hat(n).direction`,
  all through the output module (unclaimed outputs blocked). `joy[guid].axis(n)`,
  `.button(n)`. Subscript forms `vjoy[1].axis[AxisName.X]` / `button[1]` do not exist.
- Hats: values are `gremlin.types.HatDirection`, not `(x, y)` tuples.
- Macros: `gremlin.macro.Macro` with `press`, `release`, `tap`, `pause`,
  `add_action`, `is_exclusive`; actions `KeyAction`, `PauseAction`, `VJoyAction`,
  `JoystickAction`, mouse actions; run with `MacroManager().queue_macro(m)`.
  There is no `Macro.run()` and no `macro.Keys`.
- Helpers: `user_script.clamp_value`, `gremlin.util.log`, `gremlin.spline.CubicSpline`.
  No `deadzone`/`squash` helpers (they were in R13 `gremlin.input_devices`).
- Mode change from a script: no script-level helper; `gremlin.control_action`
  does not exist. `mode_manager.ModeManager().switch_to(Mode)` is internal.
- Help: there is no Help topic for writing scripts. `qml/help/` only mentions
  scripts in passing (the Scripts window in getting_started.js; vJoy notes in
  device_library.js).

## Scripts found and whether they run on our program

"As-is" means the file would load and work unchanged; "small changes" lists
the edits; "no" says why.

| Script | Source URL | Licence (may we copy?) | What it does | API used | Runs on ours |
|---|---|---|---|---|---|
| example.py (R14) | https://github.com/WhiteMagic/JoystickGremlin/blob/develop/user_scripts/example.py | GPL-3.0-only, copy allowed with notice | One of every variable type; scales an axis by a float, XORs a button with a bool, passes a hat through, prints keyboard events | R14 variables, `.decorator(mode)`, `.remap()` | **Small change**: it annotates callbacks with `types.Event`; our `gremlin.types` has no `Event` (it is `event_handler.Event`). Annotations are evaluated at definition time here (no `from __future__ import annotations`), so the file raises on load until that is changed. Our `user_scripts/example.py` is this file with that change, minus upstream's `LogicalDeviceVariable` example. |
| test_user_script.py (unit) | https://github.com/WhiteMagic/JoystickGremlin/blob/develop/test/unit/test_user_script.py | GPL-3.0-only, copy allowed | Variable values, XML round trips, decorators, `swap_uuid`, periodic plugin injection, periodic reload | Script, all variables, `callback_registry`, `periodic_registry` | **Already ours**: we have the same tests, except upstream's newer `test_keyboard_variable_decorator_numpad_key` (a Numpad key registers by scan code, not by name). Our `KeyboardVariable.decorator` already passes the `Key` itself, so that test should pass here. |
| test_e2e_user_script.py + e2e_user_script.xml | https://github.com/WhiteMagic/JoystickGremlin/blob/develop/test/integration/test_e2e_user_script.py | GPL-3.0-only, copy allowed | Drives a real vJoy device through example.py: axis halved, button inverted, hat passed | integration `app_tester`, real vJoy | **Already ours** (`test/integration/test_e2e_user_script.py`). Needs real vJoy. |
| test_e2e_user_script_mode_change.py + e2e_user_script_mode_change.xml | https://github.com/WhiteMagic/JoystickGremlin/blob/develop/test/integration/test_e2e_user_script_mode_change.py | GPL-3.0-only, copy allowed | A script and a profile action share one axis; after a mode change the action output stops and the script keeps working | `ModeManager().switch_to(Mode("Other","Default"), refresh_axes=False)` | **Not in our repo.** Small changes likely: it overrides an `edited_profile` fixture from upstream's integration conftest and calls `switch_to(..., refresh_axes=False)`; both need checking against ours. Needs real vJoy. |
| sc.py, "CH stick and pedals" (R13) | https://github.com/WhiteMagic/JoystickGremlin/blob/r13/examples/ch%20stick%20and%20pedals/sc.py | GPL v3, copy allowed | Star Citizen set-up: two response curves switched while firing, hat to shield macros, flare/chaff macros, two pedals merged to one axis, keys 1-4 set throttle | `gremlin.input_devices.JoystickDecorator` with integer device ids, `keyboard`, `macro.Macro().run()`, `macro.Keys`, `vjoy[1].axis[AxisName.X]`, `gremlin.control_action.switch_mode`, hat tuples | **No.** `gremlin.input_devices` and `control_action` are missing; device ids must be GUID strings; `.run()`, `Keys` and subscript vJoy access do not exist; hats are `HatDirection`. Would need a rewrite. |
| GremlinEx docs snippets | https://github.com/muchimi/JoystickGremlinEx/blob/develop/docs/scripting.md | GPL-3.0-or-later, copy allowed | Decorators per device and mode with GUID strings; abs/negative axis to vJoy; a button queues a "C" key macro | `gremlin.input_devices.JoystickDecorator`, `vjoy[1].axis(1).value`, `Macro().tap("C")`, `MacroManager().queue_macro` | **Small change**: replace `gremlin.input_devices.JoystickDecorator` with `user_script.JoystickDecorator`; the rest matches our API. |
| GremlinEx scripts/sc.py, msfs.py, osc.py | https://github.com/muchimi/JoystickGremlinEx/tree/develop/scripts | GPL-3.0-or-later, copy allowed | The author's own Star Citizen, MSFS and TouchOSC set-ups | `gremlin.input_devices.gremlin_start/stop/state/mode`, `periodic`, `gremlin.remote`, a missing `hardware` module | **No.** GremlinEx-only API (start/stop/state/mode hooks, remote control) and a module not in the repo. Not copied. |
| kbd_mouse_osc_plugin_hook_demo.py (muchimi gist) | https://gist.github.com/muchimi/f5f0197eb96b755a9e5548c5db232eb7 | None stated: do not copy | Hooks keyboard, mouse, joystick, OSC, MIDI and state events through the event handler with no decorators | `gremlin.ui.osc_device`, `midi_device`, `state_device`, `dinput`, `gremlin.input_types` | **No.** GremlinEx internals that we do not have. |
| hats2buttons.py (WhiteMagic, 2016) | https://gist.github.com/WhiteMagic/ec169727def8eb09b44fff84f93f1496 | None stated: do not copy | Hat directions to four vJoy buttons; shows an error popup and a log line | `input_devices.JoystickDecorator(device_id=int)`, `vjoy[1].button[1]`, hat tuples, `gremlin.util.display_error` | **No.** Old R10/R11 API throughout. |
| trim.py (WhiteMagic, 2016) | https://gist.github.com/WhiteMagic/3cff4a0b44f0e18a1f161fb4a31b55a8 | None stated: do not copy | Digital and analog trim of the stick axes using `joy` reads | `input_devices.JoystickDecorator`, `joy[1].axis(1).value` | **No.** Missing module, integer device ids. |
| script_only.py (WhiteMagic, 2018) | https://gist.github.com/WhiteMagic/3509b15e8f11f7af7846189f2380b3bd | None stated: do not copy | Warthog: curve and deadzone on two axes, a button to vJoy, a button runs an "A" key macro | `input_devices.JoystickDecorator` with `common.DeviceIdentifier`, `input_devices.deadzone`, `macro.KeyAction(macro.key_from_name(...))`, `MacroManager().queue_macro` | **No as-is; medium changes**: decorator module and device id, our own deadzone, `gremlin.keyboard.key_from_name`. The macro and `vjoy[1].axis(...)` parts match ours. |
| offset_throttle.py (WhiteMagic, 2023) | https://gist.github.com/WhiteMagic/2ab62717408bbfeda32b48f3c726f8f3 | None stated: do not copy | Adds a stick axis to a throttle axis (throttle is the neutral point) into one vJoy axis | R13 `user_plugin`, `create_decorator`, `output.value["device_id"]` | **Small changes**: import `user_script`; add `is_optional` to each variable; write the output with `output.remap(...)` instead of the `.value` dict. |
| active_device_switcher.py (WhiteMagic, 2021) | https://gist.github.com/WhiteMagic/812289cb98733d445a2f3c972951ca06 | None stated: do not copy | Two physical axes feed one vJoy axis; whichever moved last by more than a threshold wins | R13 `user_plugin`, Physical/Virtual/Mode/Float variables | **Small changes**: same three as offset_throttle. |
| toggle_1x2_3pos.py (IslandJohn, 2020) | https://gist.github.com/IslandJohn/06589d5dec3c278dcd75f207cf42d099 | None stated: do not copy | ON/OFF/ON toggle switch to three vJoy buttons; sets the start state at load | R13 `user_plugin`, `joy`+`vjoy` parameters, `input_devices.JoystickPlugin.joystick` at load | **Small changes**: the R13 three plus `user_script.JoystickPlugin.joystick` / `VJoyPlugin.vjoy`, and read inputs by `joy_1.device_guid` / `.input_id`. Writing vJoy at load time may be refused before the Run starts (outputs are claimed per Run): unverified. |
| push.py (IslandJohn, 2020) | https://gist.github.com/IslandJohn/30fb66b8a3d0161ff6fe15053c9f3d01 | None stated: do not copy | Short press and long press of one button to two vJoy buttons, using `threading.Timer` | R13 `user_plugin`, IntegerVariable, `threading.Timer` | **Small changes**: the R13 three. Its raw `threading.Timer` breaks our thread rule for program code but would still run in a script. |
| encoder.py / encoder_push.py (IslandJohn, 2020) | https://gist.github.com/IslandJohn/ee13718fce203af52f13bd3c8e0e0ae2 , https://gist.github.com/IslandJohn/809fb7822b806092ee8a4a313d04a9ac | None stated: do not copy | Rotary encoder to accelerated repeated vJoy presses; the push version adds a modifier button and uses `periodic` | R13 `user_plugin`, many Integer/Float/Bool variables, `gremlin.input_devices.periodic`, `input_devices.periodic_registry.stop()` | **Small changes**: the R13 three, `user_script.periodic`. Calling `periodic_registry.stop()` from inside a periodic callback stops every script's periodic callbacks here (it is the shared registry): unverified side effect. |
| accelerated_encoder_axis.py (AviiNL, 2024) | https://gist.github.com/AviiNL/389ed3db0bfb1f0dd412bfafaf26d119 | None stated: do not copy | Encoder clicks move a vJoy axis, faster when turned quickly | R13 `user_plugin`, Physical/Virtual/Integer/Float variables | **Small changes**: the R13 three. |
| stepped_axis.py (Theaninova, 2020) | https://gist.github.com/Theaninova/5889740cffd3de5ec0cbf5cfb3800c4e | None stated: do not copy (it credits a WhiteMagic gist ff636574... that we did not fetch) | Axis past a threshold pulses a "positive", "negative" or "centre" vJoy button | R13 `user_plugin`, `macro.VJoyAction`, `PauseAction`, `macro.exclusive`, `MacroManager` | **Small changes**: the R13 three; check `VJoyAction` arguments and exclusive flag (ours uses `Macro.is_exclusive`). |

"The R13 three" = `from gremlin.user_script import *` instead of
`gremlin.user_plugin`; add the `is_optional` argument (third position) to every
variable; replace `virtual_var.value["device_id"/"input_id"]` with
`virtual_var.remap(value)` or `vjoy[virtual_var.vjoy_id].button(virtual_var.input_id)`.
These are exactly upstream's own migration notes on the technical/scripts page.

## Compatibility summary

- **R14 scripts (WhiteMagic develop)**: our scripting is the R14 API. Upstream's
  example and tests run here with one small change (the `types.Event`
  annotation). Upstream's unit tests are already in our repo.
- **R13 user plugins (most published gists)**: none runs unchanged. All need the
  same three mechanical edits that upstream lists for R14. Nothing beyond that
  for the variable-based ones (offset_throttle, active_device_switcher, push,
  toggle, encoders, accelerated encoder, stepped axis).
- **Pre-R13 decorator scripts** (`gremlin.input_devices`, integer device ids,
  `vjoy[1].button[1]`, hat tuples, `control_action`): do not run; rewrite.
- **GremlinEx scripts**: the decorator style in its docs is one rename away
  from ours; its larger scripts use GremlinEx-only hooks and do not run.
- Gaps on our side that upstream-era scripts expect: no `gremlin.input_devices`
  name, no script mode-switch helper, no `deadzone` helper, and no scripting
  Help topic. These are observations only, not proposals (spec page
  `claude/program-map/` would have to decide them).

## Recommended for our suite (SUITE owns test/fixtures/scripts/)

1. Port upstream's `test_keyboard_variable_decorator_numpad_key` into our
   `test/unit/test_user_script.py` (copy allowed, GPL-3.0-only; keep the
   upstream credit). Copy in `found/jg_develop_test_user_script.py.txt`.
2. Add upstream's mode-change end-to-end test (`found/jg_develop_test_e2e_user_script_mode_change.py.txt`
   and `found/jg_develop_e2e_user_script_mode_change.xml`): script keeps working
   across a mode change while a profile action on the same axis stops. Real vJoy only.
3. A fixture that is upstream `example.py` byte for byte (`found/jg_develop_example.py.txt`)
   with a test that it loads: documents the `types.Event` difference and fails
   if we break R14 compatibility further. Decide first whether we want to
   accept `types.Event` (that is a spec question).
4. Our own fixtures (not copies; the gists have no licence) that cover the
   behaviours the popular gists rely on: two-axis merge into one vJoy axis
   (offset_throttle idea), short/long press to two buttons (push idea), encoder
   with `periodic` (encoder_push idea), a macro queued from a button
   (script_only / GremlinEx docs idea), and a three-position switch that sets
   its start state at load.
5. One R13-migrated fixture written by us that uses the three edits above, as a
   compatibility check for people bringing old plugins.

## Files copied (found/)

All under GPL v3 from the upstream repos; each has a header with source URL,
author and licence. None of the gists was copied.

- `found/jg_develop_example.py.txt`
- `found/jg_develop_test_user_script.py.txt`
- `found/jg_develop_test_e2e_user_script_mode_change.py.txt`
- `found/jg_develop_e2e_user_script_mode_change.xml` (header comment placed after the XML declaration; parses)
- `found/jg_r13_ch_stick_and_pedals_sc.py.txt`
