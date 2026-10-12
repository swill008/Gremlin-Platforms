# Find in profile (to-do 9): code facts, 2026-10-12, scout F9-CODE (read-only)

Nothing answers "who uses X" across the whole profile today. Nine places walk bindings their own way; none records where in an action a match sits or how to go back to it.

## Reusable pieces
- `profile.reachable(roots)` (profile.py:389): every action in a tree once (not macro steps or condition objects).
- `Profile.inputs` (profile.py:1519): every input of every device in every mode, including Keyboard, Logical Device, OSC. One loop: inputs -> items -> action_sequences -> reachable(root).
- `output.vjoy_targets` (output.py:1221): Map to vJoy + macro VJoyAction steps.
- `output.cant_send_bindings` (output.py:1385): result row shape (device_guid, device_name, input_type, input_id, input_label, mode, text).
- `binding_catalog.summarize_action` (binding_catalog.py:82): result text.
- Duplicate walkers: `input_pairing._walk_actions` (:27), `xbox_device_model.xbox_maps_for_item`, `module_model._profile_wire_maps`.

## Not read as data today
Map to Keyboard `.keys`; macro `KeyAction.key`, `JoystickAction`, `LogicalDeviceAction`, `OscAction`; condition objects (`VJoyCondition`, `KeyboardCondition`, `JoystickCondition`, `LogicalDeviceCondition`); Change Mode `_target_modes` + `change_type`. Mode inheritance exists only at run time (event_handler.py:795).

## What counts as a use
| Kind | As input | Action target | Macro step | Condition | Mode switch |
|---|---|---|---|---|---|
| Key | Keyboard item | Map to Keyboard | KeyAction | KeyboardCondition | - |
| vJoy control | - | Map to vJoy | VJoyAction | VJoyCondition | - |
| Xbox control | - | Map to Xbox | - | - | - |
| Mode | item.mode (+ inherited in child modes) | - | - | (none found) | Change Mode targets |
| Action type | - | any action tag | macro step class | condition tag | - |

## Going to a result
Exists: openDeviceBindingsNow, _cardForGuid, cardMap, ControlTree.showKey, openInput/openAction, Backend.setCurrentMode. Missing: one Main.goToBinding(guid, mode, input, binding index).

## Proposed design
`gremlin/usages.py` (data only): `Usage` dataclass (device, mode, input, binding index, path, role input/target/macro/condition/mode-switch/inherited, text), `iter_usages(profile)`, `find(profile, query)`; ~250-350 lines. Then UsagesModel (~150), QML window/panel (~200-300), Main.goToBinding (~40-60), tests (~300). Total ~900-1,200 lines, 3-4 parallel groups. Later: move cant_send_bindings, xbox_bindings_on_pads, vjoy_outputs_used, incoming_list onto iter_usages; drop input_pairing._walk_actions.
Big profile walk estimate ~50-200 ms (unverified): fine on Enter; index + rebuild on profile signals for live search.
