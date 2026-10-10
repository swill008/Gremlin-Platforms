# Actions and their editors

Mapped against code at 4f6bdfa4 (6 Oct). S60a, S112-S119 (D-05-R16, Joystick Gremlin R16 fixes and findings) and S85, S97 changed added 10 Oct, with sections 2-5, 10 and 11 from the program agents' notes. Line numbers drift; re-check them before a step starts. The ownership side (drafts, removal rules, Undo snapshots, shared actions) is in `claude/system-maps.md` map 2; this page points to it rather than repeating it.

## 1. Purpose

Actions are what an input does: send to vJoy or Xbox, press keys, run a macro, change mode, reshape an axis, and so on. This part finds the action plugins, lists the ones that suit an input in **Add Action**, shows each action's editor, and keeps edits in a draft until **OK** on the Configuration page (Keyboard page edits go straight in). At Run each action's runtime part (its "functor") does the work.

## 2. Files

| Path | What it holds |
|---|---|
| `gremlin/plugin_manager.py` (320) | `PluginManager` (singleton): finds plugins in `action_plugins/` and the user plugin folder, checks them (`_check_plugin`), registers each model as a QML type in `Gremlin.ActionPlugins`, lookup tables by name, tag and input type; `create_instance` (the one "new action" call, adds to `current_profile.library`). |
| `gremlin/base_classes.py` (737) | `AbstractActionData` (id, label, press/release mode, `from_xml`/`to_xml`, `is_valid` from `user_feedback`, containers, `clone`, `copy_unfinished`), `AbstractFunctor` (builds child functors, `_process_event`, `_pulse_event` 50 ms pulses, `_should_execute`), `flush_pulses` (Stop). |
| `gremlin/profile.py` (3063 from 2026-10-10, was 2722; `vjoy_outputs_used(mode)`, the "used" rule for S115 and 08 S94/S109; `Library` 337-771, `InputItem` 1328, `InputItemBinding` 1415, `Profile` 844-1326) | The library of action objects, `clone_action` (drafts), `pick_list`, `remove_unused`, `drop_unused_actions`, `input_snapshot`/`put_input` (Undo), `drop_invalid_actions`/`unfinished_actions` (Save). Owned by the Profile page; map 2 covers it. |
| `gremlin/ui/action_model.py` (478) | `ActionModel` (QML base for every action editor: label, press/release, `compatibleActions`, `appendAction` (from 2026-10-10 calls the new action's `start_new` for its starting output, S115), `removeAction`, `dropAction`), `SequenceIndex`, unused `ActionPriorityListModel`. |
| `gremlin/ui/profile.py` (lines 55-770) | `VirtualButtonModel` (axis/hat used as a button), `HatDirectionModel`, `InputItemBindingModel` (one binding: action tree models, move/remove/append, Treat as), `InputItemModel` (an input's bindings; delete, reorder). |
| `gremlin/ui/binding_catalog.py` (1208) | `BindingCatalogModel`: Configuration page rows (parent per input, child per binding), Type/Output filters, the action pane draft (`beginPane`, `paneDirty`, `commitPane`, `discardPane`, `endPane`), list Delete (`removeSequence`), Undo/Redo (50 steps; each step carries a label, read by the Undo bar through `lastChange`, `undone`, `undoTip`, `redoTip`, signal `undoChanged`). Row text helpers `summarize_action`, `collect_leaves`, `_TYPE_LABELS`. |
| `gremlin/ui/device.py` (lines 48-97, 773-958) | `KeyboardManagerModel` (Keyboard page list: keys once, this mode's actions, Add Key, Delete), row icon text `_generate_action_sequence_descriptor`. |
| `gremlin/action_label.py` (119) | Input names ("Rename" on Keyboard/OSC/Logical rows): monkey-patches `InputItem.__init__/from_xml/to_xml` and the `data()` of `Device`, `KeyboardManagerModel`, OSC and Logical models; `ActionNames` QML helper. |
| `gremlin/action_analysis.py` (183) | Binding-level warnings (Map to Mouse/vJoy followed by more actions; Response Curve plus Dual Axis Deadzone). |
| `gremlin/code_runner.py` (lines 174-260, 502-527) | Run side: `CallbackObject` builds the root functor of each binding; `_setup_profile`. Owned by Run lifecycle. |
| `gremlin/ui/backend.py` (451-487) | `getInputItem` (editor model for the selected input, used by the Keyboard page), action fold state `isActionExpanded`/`setIsActionExpanded`. |
| `gremlin/ui/option.py` (504-620) | `ActionSequenceOrdering`: Options > Actions > Add Action Menu (order and shown/hidden). |
| `gremlin/ui/window_placement.py` (27-28, 435-450) | Pane settings `close-pane-after-ok`, `action-pane-width`. |
| `gremlin/ui/util.py` (715 lines in all; 294-435) | `MacroRecorder` (Macro editor Record); from 2026-10-10 the `InputListenerModel` recorder keeps a key combination's press order, modifiers first (S119). |
| `gremlin/keyboard.py` (441; owned by page 02) | `modifier_keys()` includes the Win keys from 2026-10-10 (S85). |
| `gremlin/macro_raw.py` (68; new 2026-10-10, D-05-R16) | `RawMacroStep` (`unknown_type`, `unreadable`): a macro step that can't be read or is of an unknown type. Keeps the original XML element; `to_xml()` returns a copy of it unchanged; does nothing at Run; `problem` text for the editor ("Unknown step type 'X': kept as it was, does nothing.", "This key step can't be read (…): kept as it was, does nothing.") and the rule checks (S117). |
| `gremlin/validate.py` (568; owned by page 01) | from 2026-10-10 `_check_macros`: PROFILE-MACRO-STEP-UNREADABLE, a warning per unreadable macro step (S117). |
| `gremlin/ui/output_modules.py` (310; owned by page 03) | Map to vJoy output picker; from 2026-10-10 offers only claimed ids the vJoy device really has (S118, same check as the Auto Mapper). |
| `gremlin/macro.py` (1333; owned by page 06) | Macro steps; from 2026-10-10 new button steps start on Pressed and a new vJoy step on `first_claimed_output` (S113, S116); `create()` stays load-safe. |
| `gremlin/modules/output.py` (892; `first_claimed_output`, `vjoy_driver_ids`, `driver_claim`, new 2026-10-10; owned by page 03/06) | `first_claimed_output(kinds, exclude)` → (vJoy id, kind, input id) or None: the first output a vJoy output module claims (vJoy number order, kinds in the order given, ids ascending; only output vJoy devices; only ids the driver has). Used by new Condition vJoy checks, Map to vJoy and the macro editor's new vJoy step (S113, S115). |
| `joystick_gremlin.py` (663-666, 840-862, 924-926) | Registers `action-priorities`; `update_action_priorities` at start; plugin manager start. |
| `qml/BindingCatalog.qml` (2225) | Configuration page: filters, Undo/Redo (the shared `UndoBar` `catalogUndoBar`: "Last change" / "Undone", named steps), rows, Delete (red `DangerButton` `catalogDelete`, asks the shared question "Delete Action")/History/Add Action buttons, picture chooser `FilePicker` kind "picture", pane (title, X, OK, "Close pane after OK", width grip), leave/discard prompts, Appearance panel (owned by the Configuration Appearance page). |
| `qml/InputConfiguration.qml` (301) | Shows an `InputItemModel`: list of `InputItemBinding` (pane, Keyboard page) or inline mode. |
| `qml/InputItemBinding.qml` (120), `qml/InputItemBindingConfigurationHeader.qml` (269) | One binding: Note field (root action label), ActionSelector, warnings icon, Remove binding (shared question, red Remove Binding), axis/hat-as-button settings, "Activate on". |
| `qml/InputBehavior.qml` (92) | "Treat as" Button/Axis/Hat (asks the shared question when actions would go: "Change and Remove", "This can't be undone."). |
| `qml/ActionSelector.qml` (60) | Combo of `compatibleActions` + **Add Action** button. |
| `qml/ActionNode.qml` (387), `qml/RootActionNode.qml` (60), `qml/ActionDragDropArea.qml` (10), `qml/TriggerMode.qml` | One action: fold, icon, label field, press/release, "Off: never runs", warnings, Remove, right-click menu (quick adds, Add by kind, Delete), drag and drop; loads the plugin's editor QML. |
| `qml/action_kinds.js` (28) | Kinds for the right-click Add sections and Options list (map / axis / logic / other). |
| `qml/OptionActionSequenceOrdering.qml` (224) | Options list of actions by kind, drag to reorder, tick to show. |
| `qml/KeyboardInputList.qml` (223) | Keyboard page list: rows, Rename, Delete Key (asks the shared question, red Delete Key), Add Key (Listen). |
| `qml/Main.qml` (1868-1892) | Loads `KeyboardInputList` and the full-height `InputConfiguration` for the Keyboard (and OSC) tab. |
| `qml/VJoySelector.qml`, `qml/HatDirectionSelector*.qml`, `qml/LogicalDeviceSelector.qml` | Shared pickers used by editors ("Output not claimed" note). |
| `action_plugins/AGENTS.md` | How a plugin is built (data class, model class, functor). |
| `action_plugins/common.py` (160) | Shared helpers: `joystick_label`, `RelativeAxisLoop` (the Relative axis loop of Map to vJoy and Map to Logical Device, registered with `run_scope`). |
| `action_plugins/axis_pair.py` (143) | What Merge Axis and Dual Axis Deadzone share: the two axes kept as plain values (RB7) and the editor's instance pick list, "+" and switching (RB14). |
| `gremlin/unknown_action.py` (149), `qml/UnknownAction.qml` (28) | An action of a type this program doesn't have (user plugin removed or failed): kept as the file had it, saved back, does nothing at Run (04 Q7). |
| `gremlin/spline.py` (559) | Curve maths for Response Curve: piecewise linear, cubic spline, cubic Bezier. From 2026-10-10 a Cubic Spline passes through its control points (S112). |
| `qml/ButtonStateSelector.qml` (14), `qml/NumericalRangeSlider.qml` (149) | Shared editor pieces: press/release picker (Macro, Condition); two-handle range slider (Response Curve deadzone, binding header). |
| `action_plugins/<name>/__init__.py` + `<Name>Action.qml` | 26 plugin folders (25 actions + Root), listed below and in section 3 table B. |
| `qml/help/configuration_actions.js` | Help chapter: adding actions, choosing an action, one topic per action (the Help book is on page 01). |
| Tests | see section 11. |

**Plugin folders** (lines: Python + QML/JS)
- `action_plugins/map_to_vjoy/` (499; `__init__.py` 407 from 2026-10-10): send an axis, button or hat to a vJoy output; Relative axis mode. A new one starts on the first claimed output not used in this mode (S115).
- `action_plugins/map_to_xbox/` (477): send to a button, trigger, stick or D-pad of an Xbox 360 output.
- `action_plugins/map_to_logical_device/` (467): send to a Logical Device input; Relative axis mode.
- `action_plugins/map_to_keyboard/` (252): press keys while the input is held.
- `action_plugins/map_to_mouse/` (693; `__init__.py` 418 from 2026-10-10): mouse button, wheel or motion; motion through `MouseMotionManager` (page 06, S72, S88-S90).
- `action_plugins/response_curve/` (1259): reshape an axis with a curve and deadzones (curve editor, handle and point controls).
- `action_plugins/split_axis/` (339): send each half of an axis to its own action list.
- `action_plugins/merge_axis/` (671; `__init__.py` 411 from 2026-10-10, `MergeAxisAction.qml` unchanged): combine two axes into one (shared, Reuse by default). The `_NAMES` table is the one source of stored and shown operation names (`MergeOperation.to_display`); Maximum Deflection added (S114).
- `action_plugins/dual_axis_deadzone/` (652): round inner / square outer deadzone over two axes.
- `action_plugins/axis_delta/` (358): run Positive or Negative actions each time an axis moves by a step.
- `action_plugins/hat_buttons/` (443): each hat direction runs its own action list (4 or 8 way).
- `action_plugins/condition/` (1963; from 2026-10-10 `__init__.py` 388, `comparator.py` 287, `condition.py` 845; new button/key checks start on Pressed, a new vJoy check on `first_claimed_output` via `ConditionModel.addCondition`, S113, S116): run the TRUE or FALSE list by the state of inputs, keys, vJoy or Logical Device.
- `action_plugins/chain/` (337): each press runs the next sequence; timeout back to the first.
- `action_plugins/double_tap/` (514; `__init__.py` 347 from 2026-10-10): single tap and double tap run different lists.
- `action_plugins/tempo/` (506): short press and long press run different lists.
- `action_plugins/smart_toggle/` (293): quick press latches, hold acts while held.
- `action_plugins/macro/` (1948; from 2026-10-10 `__init__.py` 1218, `MacroAction.qml` 855: "Unreadable step" rows, `MacroData.unreadable_steps()`, `MacroModel.removeStep`, S113, S117): play a recorded or built sequence of keys, buttons, axes, mouse and pauses.
- `action_plugins/change_mode/` (563): switch, cycle, go back or hold a mode.
- `action_plugins/reference/` (267; `__init__.py` 209 from 2026-10-10): placeholder that picks an existing action to share or duplicate; never runs or saves; never offers an input's Root (S60a).
- `action_plugins/load_profile/` (261): open another profile and run it.
- `action_plugins/pause_resume/` (239): pause, resume or toggle the running profile.
- `action_plugins/play_sound/` (287): play a sound file.
- `action_plugins/text_to_speech/` (383): speak a text.
- `action_plugins/send_osc/` (new 2026-10-09, D-09-OSC-OUTPUT): Send OSC, send one OSC message to a target (09 S98-S101); the functor calls `gremlin/osc_output.send`. Spec here: S109-S111.
- `action_plugins/run_command/` (295; `__init__.py` 202 from 2026-10-10): start a program with arguments; a program that can't be started is reported once in the user log through `gremlin.log_once` (S97).
- `action_plugins/description/` (202): a note; does nothing.
- `action_plugins/root/` (175): internal top of every binding; runs its children in order.

## 3. What it owns

**A. Data and state**

| Data | Where | Who writes | Who else may change it |
|---|---|---|---|
| Plugin registry (`_plugins`, name/tag/type maps) | `PluginManager` | start-up discovery only | Nobody |
| Action objects (all fields of every action) | `profile.library._actions` | editors through their model setters; `create_instance`; `Library.from_xml` (load, Device Pack); `clone_action` (drafts) | Undo/History (`put_input`), Device Pack, Auto Mapper, Logical Device page, Swap Devices (`swap_uuid`), mode rename (Change Mode targets), Save (`drop_invalid_actions`). Map 2. |
| Draft copy map `Library._copied_from` | `profile.py:353` | `clone_action(draft=True)`, `pick_list` (deletes entries inside a getter), `delete_action`, `_remove_unused` | map 2 |
| Pane draft (`_pane_shadow`, `_pane_real`, `_pane_seq`, `_pane_hid`, `_pane_input`, `_pane_base`, `_pane_whole`, `_pane_model`) | `BindingCatalogModel` | `beginPane`, `commitPane`, `discardPane`, `endPane`, `_on_mode_renamed`, `_on_mode_deleted` | Nobody else |
| Configuration Undo/Redo steps (input XML before/after, 50 max) | `BindingCatalogModel._undo/_redo` | `_step` (OK, Delete), `undo`, `redo` | cleared by profile change, device change; follow mode rename; dropped with a deleted mode |
| Catalog rows, filters, "move inputs with no actions to the end" | `BindingCatalogModel` | `_rebuild`, `refreshOpenRow`, `noteOpenRow`; filter setters | page QML |
| Action fold state (open/closed per action id) | `Backend._action_state` (memory only) | `setIsActionExpanded` | Nobody |
| Input names (`InputItem.action_name`, saved as `<action-name>`) | `action_label.py` patches | `apply_action_name` (Rename) | Undo snapshots carry it (via patched `to_xml`) |
| Running state of each functor (Chain step, Tempo/Double Tap/Smart Toggle FSM and timer, Split side, Axis Delta last value, relative-axis loops, Macro object) | functor instances | Run only (`CallbackObject`) | Stop (Run lifecycle map) |
| Pending pulse releases `_pending_pulses` | `base_classes.py:546` | `_pulse_event` | `flush_pulses` at Stop |

**Settings keys**

| Key | Meaning | Written by |
|---|---|---|
| `action/general/action-priorities` | order and shown flag of each action in Add Action | `update_action_priorities` (start), Options list (`ActionSequenceOrdering`) |
| `action/macro/axis-minimum-change-amount`, `axis-minimum-time-interval`, `record-event-types`, `record-timings` | macro recording | Options, Macro editor (record types, timings) |
| `action/double-tap/duration`, `action/tempo/duration`, `action/smart-toggle/duration`, `action/axis-delta/threshold` | defaults for new actions | Options |
| `action/play-sound/playback-mode`, `action/text-to-speech/voice`, `action/change-mode/resolution-mode` | runtime options of those actions | Options (registered in `audio_player.py`, `tts.py`, `mode_manager.py`) |
| `global/files/plugin-directory` | user plugin folder | Options > Folders |
| `global/general/action-sequence-information` | Keyboard/OSC row icon mode | Options |
| window placement `close-pane-after-ok`, `action-pane-width` | pane | pane checkbox and grip |

**Files**: actions are saved in the profile XML (`<library>` + `<action-configuration>` per binding) only by File > Save; nothing in this part writes files itself.

**B. The action plugins** (25; Root is internal). "Saves" is what `_to_xml` writes; every action also writes its label and press/release mode. All editors write straight into the action object; in the Configuration pane that object is a draft copy, on the Keyboard page it is the live one.

*Send somewhere (outputs)*

| Action (tag) | Inputs | At Run | Options in the editor | Editor QML | Saves |
|---|---|---|---|---|---|
| Map to vJoy (`map-to-vjoy`) | axis, button, hat, key | `output.write_vjoy` (blocked and logged once if not claimed); button press registers auto-release; Relative axis starts a loop thread (`threads.start`) | vJoy device and output (VJoySelector, "Output not claimed"), Absolute/Relative + Speed, Invert activation | `MapToVjoyAction.qml` | device id, input id, input type, axis mode + scaling (axis), inverted (button) |
| Map to Xbox (`map-to-xbox`) | all four | `output.write_xbox` by target kind (button, trigger range, stick, D-pad); errors logged | pad (Xbox output modules by name), target (only the ones that fit the input), trigger Full/Upper half, Invert activation | `MapToXboxAction.qml` | pad id, target, inverted, trigger range |
| Map to Logical Device (`map-to-logical-device`) | all four | updates the Logical Device input, emits a Logical event; Relative axis loop thread; button auto-release | logical control, Absolute/Relative + Speed, Invert | `MapToLogicalDeviceAction.qml` | logical input id/type, axis mode/scaling, inverted |
| Map to Keyboard (`map-to-keyboard`) | button, key | queues a press macro on press, release macro on release (`MacroManager`) | Record Keys (modifiers first) | `MapToKeyboardAction.qml` | key list |
| Map to Mouse (`map-to-mouse`) | all four | `sendinput` press/release/wheel, or motion through `MouseController` | Button or Motion; speeds, time to max, direction / axis | `MapToMouseAction.qml` | mode, button, direction, speeds, time |

*Axis and hat tools*

| Action | Inputs | At Run | Options | Editor QML | Saves |
|---|---|---|---|---|---|
| Response Curve | axis | applies deadzone then curve to the value; later actions see the new value | curve type (points kept on change), points, X/Y, Invert, Symmetric, 4 deadzone values | `ResponseCurveAction.qml` (+ `HandleControl`, `PointControl`, `render_helpers.js`, grid images) | curve type, points, symmetric, deadzone |
| Split Axis | axis | sends the rescaled value to the lower or upper list; on crossing, the side left gets -1 | split value, two lists | `SplitAxisAction.qml` | split value, two child lists |
| Merge Axis (Reuse by default) | axis | reads both axes through `inputs.axis_value` (unclaimed = centre), combines (Average, Min, Max, Sum, Bidirectional, Prefer Center), runs children | instance (pick list, "+" new "Merge Axis N", rename), first/second axis, operation | `MergeAxisAction.qml` | label, both axes, operation, children |
| Dual Axis Deadzone | axis | reads both axes through input modules, inner circle/outer square, sends X to first list, Y to second | instance (pick list, "+" new), axes, inner/outer | `DualAxisDeadzoneAction.qml` | label, axes, inner, outer, two lists |
| Axis Delta | axis | pulses Positive/Negative lists each time the axis moved by the threshold | threshold, two lists | `AxisDeltaAction.qml` | threshold, two lists |
| Hat as Buttons | hat | each direction button runs its list | 4 way / 8 way (asks before dropping a direction with actions), lists | `HatButtonsAction.qml` | count, one list per direction |

*Logic and timing (containers)*

| Action | Inputs | At Run | Options | Editor QML | Saves |
|---|---|---|---|---|---|
| Condition | all four | evaluates conditions (Joystick, Keyboard, Current Input, vJoy via output module, Logical Device), runs TRUE or FALSE list | Any/All, Add Condition, comparators | `ConditionAction.qml`, `Comparator.qml`, `condition.py`, `comparator.py` | operator, conditions, two lists |
| Chain | button, key | each press runs the next sequence; timeout resets to the first (checked on press) | Timeout (sec, 0 = never), add/remove sequences | `ChainAction.qml` | timeout, chain-N lists (empty ones kept) |
| Double Tap | button, key | state machine; timer via `threads.main_timer` | threshold, exclusive/combined, two lists | `DoubleTapAction.qml` | threshold, activate-on, lists |
| Tempo | button, key | short/long press state machine; `threads.main_timer` | threshold, press/release, two lists | `TempoAction.qml` | threshold, activate-on, lists |
| Smart Toggle | button, key | quick press latches until next press; hold acts while held; `threads.main_timer` | Hold time (sec, max 10), list | `SmartToggleAction.qml` | delay, list |
| Macro | button, key | queues the macro in `MacroManager` (its own thread); Hold stops on release | steps (Joystick, Keyboard, Logical Device, Mouse Button, Mouse Motion, Pause, vJoy), Record, repeat Single/Count/Toggle/Hold + delay, Exclusive, Pre-Emptive | `MacroAction.qml` | steps, exclusive, preemptive, repeat mode/count/delay |
| Change Mode | button, key | Switch, Previous, Unwind, Cycle, Temporary (unwinds on release) | type, target modes | `ChangeModeAction.qml` | type, targets |
| Reference | all four | none (`functor = None`); always invalid, never saved | pick an action of the same input type: share it or Duplicate | `ReferenceAction.qml` | nothing (empty element) |

*Program actions and notes*

| Action | Inputs | At Run | Options | Editor QML | Saves |
|---|---|---|---|---|---|
| Load Profile | button, key | refuses with unsaved changes or missing file (notification); else `Backend.loadProfile`, Stop, Run | file, Select File | `LoadProfileAction.qml` | file name |
| Pause and Resume | button, key | `EventHandler` pause/resume/toggle | operation | `PauseResumeAction.qml` | operation |
| Play Sound | button, key | `AudioPlayer().enqueue` (own thread); missing file logged once | file, volume | `PlaySoundAction.qml` | file, volume |
| Text to Speech | button (key in practice, see Q7) | `TTSManager().enqueue` with `${current_mode}` | text, queue mode, volume, rate, pitch | `TextToSpeechAction.qml` | text, queue mode, volume, rate, pitch |
| Run Command | button, key | `QProcess.startDetached` | executable, arguments | `RunCommandAction.qml` | executable, arguments |
| Description | all four | nothing | text | `DescriptionAction.qml` | text |
| Root (internal) | all four | runs its children in order | none (top of every binding) | `RootAction.qml` | child ids |

## 4. Entry points

| Trigger | Handler | Function(s) |
|---|---|---|
| Program start | `JoystickGremlinApp.__init__` (`joystick_gremlin.py:924-926`) | `PluginManager()` (discovery, `_check_plugin`, `qmlRegisterType`), `update_action_priorities` |
| Configuration page opens / device changes | `BindingCatalog.qml` `BindingCatalogModel { guid }` | `_set_guid` (forgets Undo steps), `_rebuild` |
| Toolbar Mode changes | `BindingCatalog.qml:246` | closes a clean pane; `setMode` -> `_rebuild` |
| Type / Output filter, "Clear Filters" | `BindingCatalog.qml:1263-1284, 1634` | `_set_type_filter`, `_set_dest_filter` -> `_rebuild` |
| Click a parent row, child row, or **Add Action** on a row | `requestPane(hid, seq)` (`BindingCatalog.qml:954`) | asks if the open pane is dirty (`_paneLeave`), then `startPane` -> `beginPane` (`binding_catalog.py:1138`): `_clone_binding` -> `Library.clone_action(draft=True)`; new `InputItemModel(shadow)` |
| Pick an action and **Add Action** in the pane (ActionSelector) | `InputItemBindingConfigurationHeader.qml:131` | `ActionModel.appendAction` -> `PluginManager.create_instance` (Merge Axis: Reuse returns an in-use one) -> `insert_action` -> `sync_data`; `inputItemChanged` later |
| Right-click an action header: quick add / Add by kind / Delete | `ActionNode.qml:291-317` | `appendAction`, `removeAction` / `deleteActionSequnce` |
| Remove action (trash icon) | `ActionNode.qml:246` | `InputItemBindingModel.remove_action` -> `Library.remove_unused` (no confirm) |
| Remove binding (header trash, asks if it has actions) | `InputItemBindingConfigurationHeader.qml` -> `Confirm.ask` (red Remove Binding) | `InputItemModel.deleteActionSequnce` -> `Profile.drop_unused_actions` |
| Drag an action onto another | `ActionNode.qml:370`, `RootActionNode.qml:56` | `ActionModel.dropAction` -> `move_action` (no library removal) |
| Drag a binding onto another | `InputItemBinding.qml:104` | `InputItemModel.dropAction` |
| Edit an action label, Note, press/release | header text fields, TriggerMode | `ActionModel.actionLabel`, `activateOnPress/Release` (root label change emits `inputItemChanged`) |
| Treat as Button/Axis/Hat | `InputBehavior.qml` (asks if actions: `Confirm.ask`, "Change and Remove") | `InputItemBindingModel._set_behavior`: removes all children, `remove_unused`, new virtual button |
| Any editor field | plugin QML -> plugin model setter | writes the action object (draft in pane, live on Keyboard page) |
| Merge Axis / Deadzone pick list, "+", Reference pick/Duplicate | plugin models | `_set_merge_action:236`, `newMergeAxis:289`, `_set_deadzone:178`, `newDeadzone:133`, `referenceAction`, `duplicateAction:111` (map 2) |
| Macro Record / Stop | Macro editor | `MacroRecorder.start/stop` (raw `EventListener` key/mouse/joystick signals) |
| **OK** | `acceptPane` (`BindingCatalog.qml:978`) | `paneDirty` -> `commitPane` (`binding_catalog.py:1187`): `_snapshot`, `_replace_sequences` (whole) or `_attach_binding` (one), `_retarget_draft` (new draft), `_step`, `inputItemChanged`; closes if "Close pane after OK" |
| Pane **X** | `requestClosePane` | dirty: Save / Discard / Cancel prompt (`_paneLeave`); then `endPane` (`_drop_shadow` -> `remove_unused`) |
| Leaving the page, Load, New, Quit with a dirty pane | `requestLeave` (`BindingCatalog.qml:748`), Main | same prompt, then continues |
| Mode renamed / deleted (Manage Modes) | `signal.modeRenamed/modeDeleted` | `_on_mode_renamed` (steps and pane follow), `_on_mode_deleted` (steps dropped; pane closed with a notification, `paneLost`) |
| Another profile loaded | `signal.profileChanged` | `reload`, `_forget_steps` |
| Child row **Delete** (red `catalogDelete`, asks with `Confirm.ask` "Delete Action") | `BindingCatalog.qml` | `removeSequence` (`binding_catalog.py`): refused for the input open in the pane; `remove_item_binding`, `drop_unused_actions`, `_step` (labelled) |
| **Undo / Redo** (`UndoBar` `catalogUndoBar`), Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z | `BindingCatalog.qml` | `undo`/`redo` -> `_play` -> `Profile.put_input`; waits while the pane is open or the profile runs. The bar reads `lastChange`, `undone`, `undoTip`, `redoTip` (`undoChanged`); each step carries a label (model step labels) |
| Row **History** | `BindingCatalog.qml:1579` | opens `DialogHistory.qml` filtered to this input and mode (History page) |
| Keyboard page: **Add Key** | `KeyboardInputList.qml` InputListener | `KeyboardManagerModel.addKey` -> `get_input_item(create)`; row selected |
| Keyboard page: select a key | `onCurrentIndexChanged` -> `uiState.setCurrentInput` | Main `InputConfiguration` -> `backend.getInputItem` (creates the input if missing) -> live `InputItemModel` |
| Keyboard page: **Delete** key | `deleteKey` -> `Confirm.ask` (red Delete Key) | `KeyboardManagerModel.deleteInput` -> `Profile.drop_inputs` (this mode only) |
| Keyboard page: **Rename** | `_renameDialog` | `ActionNames.setOnModel` -> `action_label.apply_action_name` |
| Options > Actions > Add Action Menu | `OptionActionSequenceOrdering.qml` | `ActionSequenceOrdering.move/moveAmong/setShown` -> `action-priorities` |
| File > Save | Main `saveProfileChecked` | asks if `unfinished_actions()` is not empty; `Profile.to_xml` -> `drop_invalid_actions` -> `Library.to_xml(used)` |
| Profile load | `Profile.from_xml` | `Library.from_xml` (unknown tag = ProfileError), each plugin `_from_xml` |
| **Run** | `Backend.activate_gremlin(True)` -> `code_runner.start` -> `_setup_profile` | `CallbackObject` -> `root_action.functor(root)` -> each `AbstractFunctor.__init__` builds children (`base_classes.py:577`) |
| Input event while running | `EventHandler.process_event` -> `CallbackObject.__call__` | root functor -> each action's `__call__` |
| **Stop** | `code_runner.stop` | `flush_pulses`; timers/loops: Run lifecycle map (AU-116, AU-117) |
| Signals into editors | `signal.inputItemChanged` | `InputItemBindingModel._check_user_feedback` (rate limited), `KeyboardManagerModel.refreshInput`, catalog `onInputItemChanged` |
| | `signal.reloadCurrentInputItem` | Main `InputConfiguration` refetches its model (pane holds its own) |
| | `signal.logicalDeviceModified` | emitted by every new Map to Logical Device editor model (`map_to_logical_device/__init__.py:226`) |
| Timers | `_emit_input_item_changed_later` (0 ms), `_revealTimer` (0 ms) | see section 6 |

## 5. Talks to

| Other part | Direction | What |
|---|---|---|
| Profile / Library (`gremlin/profile.py`) | calls out | all action storage, drafts, removal, snapshots, save filter (map 2) |
| Input modules / claims (`ModuleClaimedInputModel`, `gremlin/modules/inputs`) | calls out | catalog rows are claimed inputs; Merge Axis, Dual Axis Deadzone, Condition read axes/buttons through input modules |
| Output modules (`gremlin/modules/output`) | calls out | Map to vJoy, Map to Xbox, macro vJoy steps, Condition vJoy state, pad list, `xbox_available`, `vjoy_module_name` |
| Wiring (`gremlin/modules/wiring.dest_label`) | calls out | catalog destination text for vJoy/Xbox |
| Device list (`device_initialization.output_vjoy_devices`) | calls out | Map to vJoy `can_create` and default device; catalog `vjoyDevices` (unused) |
| Logical Device (`gremlin/logical_device`, `ui/logical_layout.py`) | both | Map to Logical Device writes it; Logical page reuses `InputConfiguration`, `InputItemModel`, `clone_action` drafts with its own copy of the pane code |
| Macro engine (`gremlin/macro.py`) | calls out | Macro, Map to Keyboard |
| Output layer (`gremlin/modules/output.py`) | calls out | `first_claimed_output` (macro plugin, Condition, Map to vJoy, S113, S115); the picker's driver-id check (S118) |
| Unreadable macro steps (`gremlin/macro_raw.py`) | calls out | the macro plugin imports it; `validate._check_macros` reports them (S117) |
| Logging (`gremlin.log_once`) | calls out | Run Command's "can't be started" line, once, in the user log (no longer the system log) (S97) |
| Windows input (`gremlin/sendinput.py`, `keyboard.py`) | calls out | Map to Mouse; macro key/mouse steps; no output module in between |
| Event system (`event_handler`) | both | Macro Joystick step and Map to Logical Device emit events; Pause and Resume; macro recording listens raw |
| Mode manager | calls out | Change Mode, TTS `${current_mode}`, Logical events stamped with mode |
| Run lifecycle (`code_runner`, `Backend.activate_gremlin`) | called by / calls out | Run builds functors; Load Profile action calls `Backend.loadProfile` and Stop/Run |
| Event helpers (`ButtonReleaseActions`) | calls out | auto-release for vJoy/Logical buttons, Hold macros, Temporary mode, Tempo/Double Tap/Smart Toggle release |
| Threads (`gremlin.threads`) | calls out | relative-axis loops (`start`), timers (`main_timer`) |
| Audio / TTS (`audio_player.py`, `tts.py`) | calls out | Play Sound, Text to Speech |
| History (`DialogHistory.qml`, `history_model`) | calls out | row History button; History Restore also calls `put_input` on the same inputs |
| Device Pack, Auto Mapper | call in | add actions and inputs into the library (map 2) |
| Options | both | priorities list, action defaults |
| Help (`help_topics.js`) | text | one topic per action (guarded by `test_help_guide`) |
| UIState (`uiState.currentInput/currentMode`) | called by | selection drives Keyboard editor; pane keeps its own mode |

## 6. Threads and timers

| What | Kind | Started by | Ended by | Notes |
|---|---|---|---|---|
| Relative axis loop (Map to vJoy) | `threads.start("vJoy relative axis")` | functor on first relative event | loop ends itself (axis back to rest 1 s, driver lost, value changed by someone else) or `_ask_to_stop` | `_start_loop` joins the previous loop for up to 1 s on the event thread (bounded) |
| Relative axis loop (Map to Logical Device) | `threads.start` | same | same | same pattern, second copy of the code |
| Tempo, Double Tap, Smart Toggle timeouts | `threads.main_timer` (Qt timer, main thread) | functor | fire once; **not cancelled at Stop** (AU-116, open) | |
| Pulse release (Tempo, Double Tap, Axis Delta) | `QTimer.singleShot(50)` on the main thread; `time.sleep(0.05)` off it | `_pulse_event` | fire, or `flush_pulses` at Stop | `base_classes.py:656` uses `time.sleep` |
| Macro playback | `MacroManager` thread (macro.py) | Macro, Map to Keyboard | Stop (AUDIT2-D) | key held after a stuck driver: AU-117 |
| Mouse motion | `MouseController` thread (sendinput) | Map to Mouse motion | Stop (AU-111) | |
| Sound, speech | `AudioPlayer`, `TTSManager` threads | Play Sound, TTS | program exit | |
| Chain timeout | wall clock `time.time()` | functor | n/a | not `gremlin.clock` (AU-62 note: left as is) |
| Binding warning refresh | rate limit with `time.time()` (0.1 s) | `inputItemChanged` | n/a | `ui/profile.py:565` |
| Deferred `inputItemChanged` | `QTimer.singleShot(0)` | `appendAction`, `dropAction`, `removeAction`, root label | n/a | so a rebuild doesn't free the model in its own slot |
| Catalog reveal | QML `Timer` 0 ms, up to 8 retries | row reveal | n/a | quick-editor path is dead code |
| Macro recording | Qt signals from `EventListener` | Record | Stop Recording | raw input (by decision P3b) |

## 7. Rule breaks

| # | Rule | Where | What | Status |
|---|---|---|---|---|
| RB1 | Single owner (library tied to its profile) | `plugin_manager.py:148` | `create_instance` always adds to `shared_state.current_profile.library`, not the library of the input being edited; `InputItem.add_item_binding` (`profile.py:1395`) goes through it for the Root | CONFIRMED (map 2) |
| RB2 | Single owner (drafts never hold live actions) | `merge_axis/__init__.py:451-459`, `plugin_manager.py:145-148` | Add Action -> Merge Axis uses Reuse: it returns the first Merge Axis an input already uses and puts that live object into the pane draft (and logs "already exists" when re-added to the library) | CONFIRMED in code; edits-before-OK reaching the other input SUSPECTED (same as map 2's pick-list case) |
| RB3 | Single owner (one removal rule) | `ui/profile.py:448-482` (`remove_unused`) vs `ui/profile.py:695-707`, `binding_catalog.py:940` (`drop_unused_actions`) | removing an action vs a binding in the same pane use different rules | CONFIRMED (map 2) |
| RB4 | Single owner (library cleanup) | `chain/__init__.py:117-124` | Chain "remove sequence" drops the list without releasing its actions from the library | CONFIRMED; harmless on disk (save filter) |
| RB5 | Hidden owner / duplicated logic | `action_label.py:162-168` | input names are added by monkey-patching `InputItem` and four models' `data()` at import time (imported from `ui/device_names.py:8`); `device.py:_description_from_item` for keyboard is overridden and never used | CONFIRMED |
| RB6 | Layer rule (runtime does not call the UI) | `load_profile/__init__.py:61-80` | the Load Profile functor calls `Backend()` (UI), loads a profile and calls `activate_gremlin(False/True)` from inside an event | CONFIRMED; Run lifecycle map should own it |
| RB7 | Layer rule (data layer free of UI types) | `merge_axis/__init__.py:353`, `dual_axis_deadzone`, `condition/condition.py:86`, `map_to_logical_device` | action data classes hold `gremlin.ui.device.InputIdentifier` (a QObject) and Condition data classes are QObjects | CONFIRMED |
| RB8 | Layer rule (UI never touches ViGEm) | `map_to_xbox/__init__.py:29` | the plugin imports `XboxTarget`, `XboxError` from the driver package `vigem.xbox` (types only; writes go through `output.write_xbox`) | CONFIRMED import; whether types count: Q16 |
| RB9 | Layer rule (output module before driver) | `map_to_mouse`, `map_to_keyboard` via `macro`, `macro.py` key/mouse steps | keyboard and mouse go straight to `sendinput`/`keybd_event`, no output module | CONFIRMED; may be an accepted exception (Q16) |
| RB10 | Layer rule (inputs through input modules) | `macro.py:564-620` (JoystickAction), `ui/util.py:294` (MacroRecorder) | a macro Joystick step emits a fake hardware event into `EventListener`; recording reads raw events | CONFIRMED; recording raw is by decision (P3b); the Joystick step SUSPECTED (Q17) |
| RB11 | Thread rules: time via `gremlin.clock` | `chain/__init__.py:70-77`, `ui/profile.py:565-566`, `base_classes.py:656` | `time.time()` and `time.sleep(0.05)` | CONFIRMED; AU-62 left `time.time()` uses in older code on purpose |
| RB12 | Duplicated logic | `binding_catalog.py:157-185` vs plugin `name`s; `BindingCatalog.qml:1265` | catalog type labels and filter lists are a second copy of the plugin names, in sentence case ("Map to keyboard", "Hat buttons", "Pause / resume") | CONFIRMED |
| RB13 | Duplicated logic | `macro/__init__.py:710` and `:976` | the macro step type table is written twice (model and `_from_xml`) | CONFIRMED |
| RB14 | Duplicated logic | `merge_axis` 206-302 vs `dual_axis_deadzone` 133-195 | pick list, "+", switch-instance code copied; they already differ (numbered names vs fixed "Dual Axis Deadzone") | CONFIRMED |
| RB15 | Duplicated logic | `map_to_vjoy` 51-193 vs `map_to_logical_device` 52-208 | two copies of the relative-axis loop | CONFIRMED |
| RB16 | Duplicated logic | `binding_catalog.py` pane vs `logical_layout.py` `_begin_pane`/`_replace_sequences`/`_snapshot` | two pane/draft/Undo implementations | CONFIRMED (map 2) |
| RB17 | Duplicated logic | `qml/action_kinds.js` | kinds per action name kept in JS, apart from the plugins | CONFIRMED (small) |
| RB18 | Memory / ownership of models | `backend.py:465`, `ui/profile.py:760-765` | `getInputItem` makes a new `InputItemModel` parented to Backend on every selection (never freed); `InputItemModel.data` makes a new `InputItemBindingModel` on each call, each connected to the global `inputItemChanged` | CONFIRMED in code; growth SUSPECTED (not measured) |
| RB19 | Run uses unfinished actions | `code_runner.py:205`, `base_classes.py:577`, `reference/__init__.py:141` | Run builds functors from the in-memory profile, unfinished actions included; a Reference has `functor = None`, so an input whose OK'd draft still holds a Reference placeholder makes `AbstractFunctor.__init__` raise and Run fail | CONFIRMED `functor = None` and no filter; failure SUSPECTED (not run) |
| RB20 | Plugin registration depends on drivers | `plugin_manager.py:203`, `map_to_vjoy/__init__.py:361` | a plugin whose `can_create()` is false at start is not registered at all; Map to vJoy's is false with no vJoy device, so `Library.from_xml` raises "Unknown type 'map-to-vjoy'" and such profiles won't open | CONFIRMED in code; SUSPECTED in practice (needs a PC without vJoy) |
| RB21 | Signals from model constructors | `map_to_logical_device/__init__.py:226` | every Map to Logical Device editor model emits `logicalDeviceModified`, which refreshes Logical models and `logical_layout._on_external`; models are rebuilt on each `sync_data` | CONFIRMED; cost SUSPECTED |

## 8. Behaviour spec

### A. Which actions exist and which are offered

- **S1** It should load every built-in action plugin at start; a broken built-in plugin is a bug and stops start-up. [user confirmed 2026-10-06; was code only]
- **S2** It should skip (and log) a user plugin that fails to load, instead of stopping the program. [tracker: AU-35] [test: test_audit2_startup_devices.py]
- **S3** It should refuse a user plugin whose tag, name or QML type clashes with a built-in or earlier plugin, or whose input types aren't axis/button/hat/key. [user confirmed 2026-10-06; was code only] [test: test_audit3_startup.py::test_a_user_plugin_cant_replace_a_built_in_qml_element]
- **S4** Add Action should list only actions that suit the input's behaviour (axis, button, hat, key). [help: Choosing an action]
- **S5** A key, and an axis or hat treated as a button, should be offered the button actions. [user confirmed 2026-10-06; was code only] (`InputItemBindingModel._get_behavior` maps Keyboard to "button")
- **S6** Add Action should follow the order and hiding set in Options > Actions > Add Action Menu; Root is never listed. [help: Choosing an action] [test: test_option_list_saving.py::test_action_order_move_is_saved]
- **S7** A new plugin found at start should be added to that list (shown), and a plugin no longer present should leave it. [user confirmed 2026-10-06; was code only] (`update_action_priorities`)
- **S8** The action's right-click menu should offer the first three actions of that order as quick adds and the rest under Map to / Axis and Hat / Logic and Timing / Other, matching the Options list. [user confirmed 2026-10-06; was code only] (`ActionNode.qml:287-317`, `action_kinds.js`)
- **S9** Map to vJoy should be offered only when at least one vJoy device can be an output. [user confirmed 2026-10-06; was code only]
- **S10** Text to Speech should be offered for buttons and keys. [test-plan: AE-09b asks] (see Q7)
- **S11** Every action should have a Help topic. [test-plan: HELP-B] [test: test_help_guide.py]

### B. Configuration page list

- **S12** It should list the claimed inputs of one device, each with its actions, in the mode shown on the toolbar. [help: Adding actions] [glossary: Claim]
- **S13** With no claimed inputs it should say so and point to Module Setup; when filters hide everything it should say "No inputs match the current filters." with Clear Filters. [user confirmed 2026-10-06; was code only]
- **S14** An input with no actions should show **No actions**. [glossary] [test-plan: GLOSSARY-2]
- **S15** "Move inputs with no actions to the end" should list them together under a **No actions** heading. [help: Adding actions] (today the heading reads "Unmapped": G5)
- **S16** Each child row should name the action type and where it goes (vJoy output label, keys, mouse button or "Motion", profile/program/sound file name, mode). [tracker: B5/B6 via BUGS-1] [test: test_catalog_actions.py::test_summarize_covers_every_plugin_tag]
- **S17** Containers (Chain, Tempo, Condition, Double Tap, Smart Toggle, Description, Reference) should show the actions inside them; an empty container shows as an empty sequence. [test: test_catalog_actions.py::test_wrapper_with_child_shows_the_child] [test: test_catalog_actions.py::test_wrapper_without_child_is_an_empty_sequence]
- **S18** The Type filter should offer All, Map to vJoy, keyboard, mouse, Xbox, Macro, Change Mode, Other, No actions; the Output filter lists the destinations in use. [test-plan: IC-01]
- **S19** Rows should show live LEDs/bars when Appearance turns them on, but never while editing is locked. [user confirmed 2026-10-06; was code only]

### C. The action pane (draft, OK, Cancel)

- **S20** Clicking a parent row, a child row or Add Action should open the action editor beside the list; a parent opens all the input's actions, a child only that one. [help: Adding actions] [test-plan: IC-03..05]
- **S21** Edits in the pane should not change the input until OK. [test: test_pane_draft.py::test_draft_does_not_change_the_parent_until_ok]
- **S22** OK should write the pane's actions onto the input, keep the profile unsaved until File > Save, and keep the pane open on a fresh copy unless "Close pane after OK" is ticked. [help: Adding actions] [test-plan: IC-11]
- **S23** "Close pane after OK" and the pane width should be remembered between sessions. [test-plan: IC-09..13]
- **S24** OK with nothing changed should do nothing (no Undo step). [user confirmed 2026-10-06; was code only] (`commitPane` checks `paneDirty`)
- **S25** Removing every action in the pane then OK should clear the input, as an Undo step. [tracker: AU-30] [test: test_audit_editing.py::test_removing_every_action_in_the_pane_then_ok_clears_the_input]
- **S26** Closing the pane (X), opening another input, leaving the page, Load, New or Quit with unsaved pane changes should ask Save / Discard / Cancel; Cancel keeps the edit, Discard drops it. [help: Adding actions] [test-plan: IC-09] [test-plan: F-05]
- **S27** Discard (or X with no changes) should leave the profile exactly as before the pane opened, unfinished actions included. [test: test_audit3_actions_undo.py::test_cancel_leaves_an_unfinished_merge_axis_as_it_was] [tracker: AU-110]
- **S28** Changing the toolbar Mode should close a pane with no changes; a pane with changes stays and OK writes to its own input and mode, named "(in <mode>)". [tracker: AU-12] [test: test_audit_editing.py::test_ok_after_a_mode_change_stays_on_its_input_and_undoes]
- **S29** Renaming the pane's mode should keep the pane on the renamed mode; deleting it should close the pane and say "The mode X was deleted, so its action editor closed." [test-plan: AUDIT2-C-MODES] [test: test_audit_editing.py::test_steps_follow_a_mode_rename_and_go_with_a_deleted_mode]
- **S30** Loading another profile should close an open pane. [test-plan: F-05]
- **S31** The list's Delete should be hidden and refused for the input open in the pane. [tracker: AU-28, AU-29] [test: test_audit_editing.py::test_the_list_delete_waits_while_the_pane_edits_that_input]
- **S32** While the profile runs, editing should be locked (pane contents greyed, Undo/Redo off). [help: Adding actions] [user confirmed 2026-10-06; was code only for the pane opening at all: Q11]
- **S33** A draft should never make the profile look unsaved. [tracker: G-LIBLEAK] [test: test_profile_unused_actions.py::test_an_open_draft_is_not_unsaved_work]
- **S34** Saving with the pane open should leave the draft untouched and write only actions inputs use. [user decision: map 2 verification list] (not tested: G9)

### D. Undo and Redo (Configuration page)

- **S35** Undo/Redo should step back and forward through each OK and each Delete, 50 steps. [help: Adding actions] [test: test_catalog_undo.py::test_ok_undoes_and_redoes] [test: test_catalog_undo.py::test_a_delete_undoes_and_redoes]
- **S36** Undo/Redo should wait while an action is open in the pane, and while the profile runs. [help: Adding actions] [test-plan: UNDO-CONFIGURATION]
- **S37** Opening another device or profile should start with no steps. [help: Adding actions] [test: test_catalog_undo.py::test_another_profile_starts_without_steps]
- **S38** A step whose mode was renamed should follow the rename; a step for a deleted mode should be dropped. [tracker: AU-13, AU-79]
- **S39** A step that can't be played should stay and say "That change couldn't be put back." [test: test_audit2_undo.py::test_configuration_undo_that_cant_be_played_keeps_its_step]
- **S40** Undo should never make the profile unloadable; an unfinished Merge Axis, Deadzone or Reference placeholder is left out of the step. [test-plan: AUDIT2-B-UNDO] [test: test_audit2_undo.py::test_a_snapshot_of_an_unfinished_merge_axis_works]
- **S41** Undo should keep a shared action shared (the same object for both inputs). [test: test_audit2_undo.py::test_a_shared_action_stays_shared_after_undo] (its old settings are not put back: map 2, decision A2)

### E. Editing inside an action

- **S42** Each action should have a label field; a blank label stays blank after save and reload. [test: test_action_xml_round_trip.py::test_blank_action_label_stays_blank]
- **S43** The binding's free text is the **Note** (root action label); it shows on the Configuration list's input row and on the Keyboard page's key row. [glossary: Note] [changed 2026-10-07 to follow decision D-05-S43-BOTHROWS]
- **S44** Button actions that allow it should have press/release switches; both off shows "Off: never runs". [tracker: WORKFLOW-HANDS-ON] [user confirmed 2026-10-06; was code only for the save]
- **S45** An action with a problem should show a warning or error icon with the reason on hover; an error means Save will leave it out and asks first ("Save without them"). [test-plan: SAFE-1] [test: test_action_warnings.py]
- **S46** Changing "Treat as" should ask first when the binding has actions, and remove them on yes. [tracker: A8] [test: test_input_item_binding_model.py::test_behavior_switch_clears_children]
- **S47** Deleting an action in an editor should remove it and its children from the profile unless another input uses it; moving it keeps it. [tracker: ACT16] [test: test_action_editor_fixes.py::test_a_deleted_action_leaves_the_library] [test: test_action_editor_fixes.py::test_a_moved_action_stays_in_the_library]
- **S48** Removing a binding with actions should ask first. [user confirmed 2026-10-06; was code only] (`InputItemBindingConfigurationHeader.qml:161-172`)
- **S49** Hat as Buttons 8 way -> 4 way should ask before dropping a direction that has actions. [test-plan: SAFE-3-HANDS-ON]
- **S50** Changing the Response Curve type should keep the points and Symmetric. [tracker: ACT14] [test-plan: CRASH-AND-LOSS-FIXES]
- **S51** Editors should state units and ranges (sec, px/s, %, Times, counted from 1). [tracker: ACT23] [test: test_action_editor_fixes.py::test_editors_say_their_units_and_count_from_one]
- **S52** Map to Xbox should offer only targets that fit the input; a saved target outside the list stays listed and works. [tracker: DEV7] [test-plan: MAP-TO-XBOX-INPUTS]
- **S53** Map to vJoy should show "Output not claimed" for an output its vJoy module doesn't claim. [help: Map to vJoy]
- **S54** Map to Xbox should have no claims, claim labels or claim warnings; only a "ViGEmBus not available" warning. [user decision: Xbox output has no claims] [test-plan: XB-FIX]
- **S55** An empty text field (Description, Run Command, Text to Speech) should reload empty, not as "None". [test-plan: AE-XML-NONE]
- **S56** Chain's empty sequences and their order should survive save and reload. [test-plan: AE-XML-CHAIN]

### F. Shared actions (Merge Axis, Dual Axis Deadzone, Reference)

- **S57** The Merge Axis and Deadzone lists should offer the one being edited, the new one from "+", and those an input uses; never deleted or replaced ones; a pane copy hides its original. [tracker: AU-110] [test: test_audit3_actions_undo.py::test_merge_axis_list_shows_the_one_being_edited] [test: test_audit3_actions_undo.py::test_reference_list_offers_the_pane_copy_not_the_original]
- **S58** "+" should make a new instance, select it, and leave a shared one finished. [test: test_audit3_actions_undo.py::test_new_merge_axis_leaves_a_shared_one_finished] [test: test_action_editor_fixes.py::test_a_new_merge_axis_gets_the_next_free_name]
- **S59** Merge Axis (and Deadzone): choosing an existing one to share it should keep the shared action's own name. [reworded 2026-10-09, user approved: "Reuse" never appears on screen] [tracker: ACT18] [test: test_action_editor_fixes.py::test_reuse_keeps_the_shared_actions_name]
- **S60a** The Reference list should never offer an input's Root (the hidden action that holds an input's actions). [user decision 2026-10-10: D-05-R16 (R5)]
- **S60** Reference should let you share an existing action of the same input type (both inputs use the same action) or Duplicate it (an independent copy of it and everything inside). [help: Reference] [test: test_audit3_actions_undo.py::test_reference_duplicate_copies_every_nested_action]
- **S61** Reference picked then Cancel should keep the profile loadable; picked then OK replaces the placeholder. [tracker: AU-110] [test: test_audit3_actions_undo.py::test_reference_picked_in_the_pane_then_ok_replaces_the_placeholder]
- **S62** OK on an action two inputs share should change it for both. [user decision: pending A1, recommended] (today it splits them: AU-118, `test_audit3_actions_undo.py:478-498` asserts the split)
- **S63** Picking a shared action in the pane should edit a copy until OK. [user decision: pending A4, recommended]

### G. Saving and loading

- **S64** Every action should survive save and load for every input type it supports. [test-plan: AE-XML] [test: test_action_xml_round_trip.py::test_default_action_survives_save_and_load]
- **S65** Save should write only actions an input uses (deleted, replaced and draft ones stay in memory for Undo). [tracker: G-LIBLEAK] [test: test_profile_unused_actions.py::test_the_file_gets_only_what_inputs_use]
- **S66** Save should ask before leaving out unfinished actions (Save without them / Cancel). [test-plan: SAFE-1]
- **S67** A profile naming a missing child action should open (no hang); the missing child is dropped on save. [tracker: ACT1] [test: test_profile_missing_child_action.py] [test: test_audit3_actions_undo.py::test_a_save_drops_a_child_missing_from_the_library]
- **S68** A Play Sound or Load Profile whose file is missing should not stop the profile opening; the action is kept, warns, and does nothing when pressed. [tracker: ACT11, AU-14] [test: test_play_sound_missing_file.py]
- **S69** A profile with an action type this program doesn't have should open; the unknown action is kept unchanged (saved back as it was, does nothing at Run, its editor shows a note) and the program warns, naming the type. [changed 2026-10-06 to follow decision 04 Q7 (open and keep), which wins over the earlier wording "fail to open"] [tracker: ACT15]
- **S70** Response Curve Symmetric should be saved. [tracker: ACT13]
- **S71** Changing a mode's name should update Change Mode actions that name it. [tracker: AU-20]

### H. Keyboard page

- **S72** It should list each added key once, with the actions of the mode shown. [tracker: AU-32] [test: test_mode_refresh_and_add_key.py::test_a_key_in_two_modes_is_listed_once_with_the_shown_modes_actions]
- **S73** Add Key should add the pressed key to the mode being viewed and select it. [test: test_mode_refresh_and_add_key.py::test_add_key_goes_into_the_given_mode]
- **S74** A selected key should show its actions in the editor, where actions can be added. [user confirmed 2026-10-06; was code only] (see Q4: a new key has no binding to add to)
- **S75** Delete should ask, remove only this mode's actions for that key, and show only on keys that have actions in this mode (or none in any mode). [tracker: AU-31, AU-90, AU-100] [test: test_audit2_keyboard_calibration.py::test_a_key_only_in_another_mode_is_not_in_this_one]
- **S76** Deleting the last key should let the editor go of it. [test: test_audit2_keyboard_calibration.py::test_deleting_the_last_key_lets_the_editor_go_of_it]
- **S77** Rename should give the key an input name saved in the profile. [user confirmed 2026-10-06; was code only]
- **S78** Keyboard page edits should take effect at once (no OK, no Undo). [user confirmed 2026-10-06; was code only] (doubtful: Q5)
- **S79** Only keys the Keyboard module claims should fire; once a keyboard choice is saved, unclaimed keys do nothing. [help: A key binding does not fire] [tracker: AU-23]

### I. At Run: each action

- **S80** Each binding should run its actions in order; a value changed by Response Curve (and Split Axis) is what later actions see. [help: Response Curve] [user confirmed 2026-10-06; was code only for Split Axis: Q10]
- **S81** One failing action should not stop the other actions or release handling for that input. [tracker: AU-16]
- **S82** Map to vJoy should write only claimed outputs; an unclaimed one is blocked and logged once per Run. [test-plan: P2b] [help: Map to vJoy]
- **S83** Map to vJoy Relative should move the axis while the input is off-centre, at Speed; it stops when someone else changes that axis or the input rests for 1 s. [help: Map to vJoy] [user confirmed 2026-10-06; was code only for the stop rules]
- **S84** Map to Xbox: buttons/keys/hats on a trigger give full when pressed and 0 when released; a hat moves a stick in its direction. [tracker: DEV7]
- **S85** Map to Keyboard should hold the keys while the input is held and release them on release; modifiers (Shift, Ctrl, Alt, Win) are pressed first, then the other keys. [help: Map to Keyboard] [test: action_interaction/test_map_to_keyboard.py] [changed 2026-10-10, user: D-05-R16 (R4): the Win key counts as a modifier]
- **S86** Map to Mouse wheel should send once per press. [help: Map to Mouse]
- **S87** Merge Axis and Dual Axis Deadzone should read their axes through the input modules; an unclaimed axis reads centred. [test-plan: P3c]
- **S88** Split Axis should send the side it leaves its rest value (-1) and work at any split value, 1.0 included. [tracker: ACT4, ACT5]
- **S89** Chain should check its timeout on a press only and release the step that was pressed; with no sequences it does nothing. [tracker: ACT6, ACT7]
- **S90** Tempo, Double Tap and Smart Toggle should run their timed-out actions on the main thread. [tracker: ACT20]
- **S91** Tempo, Double Tap and Smart Toggle timers should be cancelled at Stop. [tracker: AU-116, open]
- **S92** A macro should stop with Stop (every step checks; Pause and repeat delay end at once); an empty macro does nothing. [test-plan: AUDIT2-D-MACROS] [tracker: ACT8]
- **S93** Change Mode to a mode the running profile doesn't have should be ignored and logged once; Cycle's first press moves; empty Switch/Cycle/Temporary do nothing. [tracker: ACT2, ACT3, ACT9]
- **S94** Load Profile should not load over unsaved changes, and should say why. [tracker: AU-15]
- **S95** Pause should stop all actions except Pause and Resume itself (it always runs). [help: Pause and Resume] [user confirmed 2026-10-06; was code only for "itself"]
- **S96** Play Sound should queue the file and play it at the volume; overlapping sounds follow Options > Actions > Play Sound. [help: Play Sound] [tracker: APP6]
- **S97** Run Command should start the program with your own permissions; arguments split on spaces with quotes kept together. A program that can't be started is reported once in the user log; nothing else happens. [help: Run Command] [changed 2026-10-10, user: D-05-R16 (R2): the failure is reported once, nothing else happens]
- **S98** Description should do nothing when the input fires. [help: Description]
- **S99** Run should not run unfinished actions. [user confirmed 2026-10-06; was code only: today it does, RB19, Q3]
- **S100** Keys and buttons held by Map to Keyboard, Map to Mouse and macros should be released at Stop. [tracker: AU-111] (macro stuck-driver case still open: AU-117)
- **S101** Edits made while stopped take effect at the next Run; nothing is edited while running. [user confirmed 2026-10-06; was code only]

### J. Edge cases

- **S102** Empty: an input with no actions shows No actions and runs nothing. [glossary]
- **S103** Missing driver: Map to Xbox without ViGEmBus shows a warning but stays in the profile. [user confirmed 2026-10-06; was code only] (`map_to_xbox` user_feedback is a Warning on purpose)
- **S104** Missing driver: a profile with Map to vJoy should open on a PC without vJoy and keep those actions. [user confirmed 2026-10-06; was code only] (today it can't: RB20, Q2)
- **S105** Unplugged: actions of an unplugged stick stay in the profile; Merge/Deadzone axes of an unplugged stick read centred. [test-plan: P3c] [user confirmed 2026-10-06; was code only for "stay"] [user decision 2026-10-07: D-05-UNPLUG-CENTRE: centred wins over 02 S28's "axes stay" for every action read]
- **S106** Renamed / twin: actions are keyed by device id, so a renamed or second identical stick keeps its own actions. [test-plan: TWIN-DEVICES]
- **S107** Damaged: a profile with a broken action reference opens; a Undo step that can't be read is kept and reported. [tracker: ACT1] [test-plan: AUDIT2-B-UNDO]
- **S108** Crash: OK'd edits not saved are lost on a crash (no recovery copy for profiles). [user confirmed 2026-10-06; was code only]

### L. Joystick Gremlin R16 fixes and findings (D-05-R16, 2026-10-10)

Fixes taken over from upstream Joystick Gremlin R16 (R1-R11) and findings of this batch (G-a, G-b).

- **S112** A Cubic Spline curve should pass through its control points. [user decision 2026-10-10: D-05-R16 (R3)]
- **S113** A new vJoy macro step or a new vJoy condition should start on the first output a vJoy output module claims (`first_claimed_output`). With none claimed, each editor keeps its own way: the macro editor adds the step with a notice; the condition editor refuses with a notice. [user decision 2026-10-10: D-05-R16 (R6)]
- **S114** Merge Axis should have a **Maximum Deflection** operation: the axis furthest from centre wins; a tie goes to axis 2. "Prefer Center" keeps its name. Stored name `maximum-deflection`; existing stored names (`prefercenter` etc.) are unchanged. [user decision 2026-10-10: D-05-R16 (R7)] [glossary: Maximum Deflection]
- **S115** A new Map to vJoy should start on the first claimed output not used in this mode (the same "used" rule as the Auto Mapper, 08 S94, S109); when all are used, the first claimed output; with none claimed, the default doesn't change. [user decision 2026-10-10: D-05-R16 (R8)]
- **S116** New Condition button and key checks, and new macro Joystick, Keyboard, Logical Device, Mouse Button and vJoy button steps, should start on **Pressed**. [user decision 2026-10-10: D-05-R16 (R11b)]
- **S117** A macro step that can't be read, or is of an unknown type, should not stop the profile opening: it is kept unchanged (saved back as it was), does nothing at Run, and the macro editor and the rule checks say so. Save should keep a Logical Device step whose control is missing; only steps that were never filled in are dropped. [user decision 2026-10-10: D-05-R16 (R11c)]
- **S118** The vJoy output picker should only offer claimed ids the vJoy device really has (the same check as the Auto Mapper). [user decision 2026-10-10: D-05-R16 (G-a)]
- **S119** A recorded key combination should keep the order the keys were pressed in, with modifiers still first (S85). [user decision 2026-10-10: D-05-R16 (G-b)]
- R11a and R11d: no behaviour change. [user decision 2026-10-10: D-05-R16]

### K. Send OSC

- **S109** Send OSC should be offered on buttons, keys and axes. [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S110** Its editor should have: **Target** (OSC's Targets list, or **Reply to sender**), **Address** (starts with "/"), **Values** (**Fixed**, a list built with **Add Value**, or **Input value**: a button 1/0, an axis scaled from -1..1 to **Min**..**Max**), a type per value (**Auto**, **Int**, **Float**, **Bool**, **Text**; Auto = the type last received on that address, else Float), and send on press, release or both (the action's usual activation setting). (09 S98-S100) [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S111** At Run it should send only while the profile runs and OSC output is on; each send shows in the OSC Monitor as Out. (09 S94, S101) [changed 2026-10-09, user: D-09-OSC-OUTPUT]

## 9. Questions for the user

- **Q1** OK on an action two inputs share (Merge Axis, Dual Axis Deadzone, a shared Reference) splits them today. Map 2 decisions A1 (OK changes it for both) and A4 (picking a shared action edits a copy until OK) are still open. *Recommend:* A1 (a) and A4 as in map 2; add Add Action -> Merge Axis "Reuse" to A4's scope, since it also puts the live shared object into the draft (RB2).
- **Q2** Map to vJoy is not registered at all when no vJoy device exists at start, so any profile with a Map to vJoy action fails to open ("Unknown type 'map-to-vjoy'"), and the action leaves the Options list. *Recommend:* always register every built-in plugin; `can_create()` should only decide whether Add Action offers it. Needs a hands-on check on a PC (or VM) without vJoy first.
- **Q3** Run builds the profile as it is in memory, unfinished actions included. An OK'd Reference placeholder has no runtime part and should make Run fail; an unfinished Merge Axis or Map to Keyboard with no keys runs anyway. *Recommend:* Run skips unfinished actions and logs one line per action ("not finished: <action> on <input>"), matching what Save leaves out.
- **Q4** The Keyboard page shows a key's bindings, but a key added with Add Key has none, and the "New Action Sequence" footer was removed (94ae5cc2; C9 kept that). Can a new key get an action at all? *Recommend:* check by hand; if not, a key with no binding should show one empty binding (as the Configuration pane does).
- **Q5** The Keyboard page edits the live profile: no draft, no OK, no Undo, and the action trash icon removes at once without asking. The Configuration page drafts everything. Should keys work like the Configuration page? *Recommend:* yes, use the same pane (draft, OK, Undo) for Keyboard; until then, ask before Remove action there.
- **Q6** Catalog text breaks the glossary: the heading "Unmapped" with "N controls — click to add", "N assignments — ...", "Sequence"/"Empty" for wrapper rows, and type labels in sentence case ("Map to keyboard", "Hat buttons", "Pause / resume"). The glossary guard only reads QML and Options text, not these Python strings. *Recommend:* heading "No actions"; "1 action" / "N actions"; take type labels from the plugin names (Title Case); extend `test_glossary_words.py` to `binding_catalog.py`.
- **Q7** Text to Speech lists only "button" as its input type, yet keys are offered it (keys use the button list). Test plan S-34/AE-09b says it isn't offered. *Recommend:* add Keyboard to its input types so the intent is written down, and close S-34.
- **Q8** Pane OK while History Restore, Auto Mapper or a Device Pack import changed the same input after the pane opened: OK writes over the new actions (whole input) or into whatever binding now has that number. *Recommend:* those tools close the pane first (asking if it has changes).
- **Q9** Axis Delta reads the raw event value (a Response Curve before it is ignored) and skips any event whose value is exactly 0. *Recommend:* use the value as shaped by earlier actions and treat 0 as a value.
- **Q10** Split Axis changes the value in place, so actions after the Split Axis in the same list get the half-axis value, not the original. Intended? *Recommend:* Split's change stays inside its two lists; actions after it see the input's value.
- **Q11** A row click opens the pane while the profile runs (S-13); its contents are greyed but OK is live. *Recommend:* open read-only with "Stop to edit" and no OK.
- **Q12** Chain's "remove sequence" leaves that sequence's actions in the library (not on disk). *Recommend:* release them through the one removal rule (map 2 step 2).
- **Q13** The Load Profile action loads a profile and stops and restarts Run from inside an event, through the UI's Backend. *Recommend:* hand the request to the Run lifecycle owner (map 3) to do after the event.
- **Q14** New Dual Axis Deadzones are all named "Dual Axis Deadzone"; new Merge Axes are "Merge Axis N". *Recommend:* number Deadzones the same way.
- **Q15** Input names (Rename on Keyboard/OSC/Logical rows) live in `action_label.py`, which rewrites `InputItem` and four list models at import. *Recommend:* move the field into `InputItem` and the `description` role into each model; delete the patches.
- **Q16** Keyboard and mouse output (Map to Keyboard, Map to Mouse, macro steps) go straight to Windows, and the Xbox plugin imports types from `vigem.xbox`. Are these allowed under the layer rule? *Recommend:* record keyboard/mouse as an accepted exception (no driver to own) in `claude/decisions.md`; move `XboxTarget` to the output module so plugins import it from there.
- **Q17** A macro "Joystick" step emits a made-up event as if from a stick. Does it go through the input module's claims (it's sent where raw events are)? *Recommend:* send it through the input module like a real event, so an unclaimed control does nothing, as everywhere else.
- **Q18** Unused code: catalog quick editor (`openSequence`, `editingHid`, `quickHid`; test-plan S-03), `addSequence` (writes with no Undo step), `vjoyDevices`, `InputItemModel.newActionSequence` (C9), `ActionPriorityListModel`, `device._description_from_item` for keys. *Recommend:* remove in one clean-up commit.
- **Q19** `time.time()` remains in Chain and in the binding-warning rate limit (AU-62 left older uses). *Recommend:* Chain moves to `gremlin.clock` (it is runtime and tests would like to step it); leave the UI rate limit.
- **Q20** Test plan IC-06 says catalog Delete has no confirmation; WORKFLOW-3 (C8) says it asks, and the code asks. *Recommend:* mark IC-06 superseded.

## 10. Known gaps

**Code differs from the spec or a rule**

| # | Gap | Where |
|---|---|---|
| G1 | OK on a shared action splits it (AU-118, S62) | `binding_catalog.py:138, 1125`; `test_audit3_actions_undo.py:478-498` |
| G2 | Add Action -> Merge Axis puts a live shared action into the draft (RB2, Q1) | `merge_axis/__init__.py:451-459` |
| G3 | Pick list / "+" / Reference put live library actions into the draft (map 2) | `merge_axis:236`, `dual_axis_deadzone:178`, `reference:119` |
| G4 | Map to vJoy not registered without vJoy; its profiles won't open (RB20, Q2). Fixed in code: built-in actions always register, Add Action leaves them out | `plugin_manager.py:203` |
| G5 | "Unmapped", "assignments", "Sequence"/"Empty", sentence-case type labels on screen (Q6) | `binding_catalog.py:157-185, 280-283, 304-311, 601-602`; `BindingCatalog.qml:1265` |
| G6 | Run runs unfinished actions; Reference has no functor (RB19, Q3) | `code_runner.py:205`, `reference/__init__.py:141` |
| G7 | Tempo/Double Tap/Smart Toggle timers outlive Stop (AU-116, S91) | `tempo:174`, `double_tap:191`, `smart_toggle:84` |
| G8 | Macro stuck-driver key held; relative-axis loop may survive a quick Stop/Run (AU-117) | `macro.py`, `map_to_vjoy:139`, `map_to_logical_device:144` |
| G9 | Save with the pane open: `drop_invalid_actions` edits every library action, drafts included (map 2; not tested) | `profile.py:702, 914` |
| G10 | Keyboard page: possibly no way to add an action to a new key (Q4) | `InputConfiguration.qml`, `KeyboardManagerModel.addKey` |
| G11 | Keyboard page has no draft, no Undo, and action Remove doesn't ask (Q5) | Main `InputConfiguration`, `ActionNode.qml:246` |
| G12 | Pane OK can overwrite changes made by History Restore / Auto Mapper / Device Pack while it was open (Q8) | `binding_catalog.py:1187-1217` |
| G13 | `getInputItem` creates an empty input for every key or input viewed, and a model per selection that is never freed (RB18) | `backend.py:458-465` |
| G14 | Chain sequence removal leaves actions in memory (RB4, Q12) | `chain/__init__.py:117-124` |
| G15 | Load Profile runtime calls the UI and Stop/Run (RB6, Q13) | `load_profile/__init__.py:61-80` |
| G16 | Every Map to Logical Device editor model refreshes the Logical page (RB21) | `map_to_logical_device/__init__.py:226` |
| G17 | Stale comment says the Xbox output module "passes only the controls it claims" (Xbox has no claims) | `map_to_xbox/__init__.py:121` |
| G18 | Output filter hides itself ("No output module claimed") when no vJoy device is valid, even if Xbox or keyboard destinations exist | `BindingCatalog.qml:1275-1290` |
| G19 | `compatibleActions` sorts with `list.index`: an action missing from `action-priorities` (settings damaged after start) raises and the combo is empty | `action_model.py:200-206` |
| G20 | Profile-level unknown action type aborts the whole load (no "open, keep the rest" like ACT11/ACT12). Fixed in code: `gremlin/unknown_action.py` keeps it (04 Q7; `test_data_safety.py`) | `profile.py:642-646` |
| G21 | Help says Merge Axis operation "Prefercenter"; the editor shows "Prefer Center". Fixed: the Help book says "Prefer Center" | `help_topics.js:143`, `merge_axis:198` |
| G22 | Binding warnings use `time.time()` (RB11, Q19); Chain no longer does | `ui/profile.py:570` |
| G23 | "Reuse" (S59) never appears on screen (to-do 56) | `merge_axis`, `MergeAxisAction.qml` |
| R11c | Save drops a macro Logical Device step whose control is missing; a step that can't be read stops the profile opening (S117). Fixed 2026-10-10 (this batch). Not verified: a device swap doesn't update a raw Joystick step | `gremlin/macro.py`, `gremlin/macro_raw.py`, `action_plugins/macro/` |
| R5 | The Reference list offers an input's Root (S60a). Fixed 2026-10-10 (this batch) | `action_plugins/reference/` |
| G-a | The vJoy output picker offers claimed ids the vJoy device doesn't have (S118). Fixed 2026-10-10 (this batch) | `gremlin/ui/output_modules.py`, `gremlin/modules/output.py` |
| G-b | A recorded key combination loses the order the keys were pressed in (S119). Fixed 2026-10-10 (this batch) | `gremlin/ui/util.py`, `gremlin/keyboard.py` |

**Open tracker items for this part**

| Ref | One line |
|---|---|
| AU-118 | OK on a shared Merge Axis splits it (Device Pack half is map 2 / Device Pack) |
| AU-116 | Tempo, Double Tap, Smart Toggle timers not cancelled at Stop |
| AU-117 | Macro held key after a stuck driver; relative-axis loop over a quick Stop/Run |
| AU-119 | About 20 tests (Tempo, Double Tap, macro) wait a fixed short time |
| N22 | Editor controls inconsistent (on hold): Deadzone has no Rec button, Condition's Add before its drop-down, label widths, "Map to v." truncation, Play Sound Volume without %, Response Curve number clipped |
| C9 | (won't fix) no second binding per input; the slot remains (Q18) |
| test-plan S-03, S-13, S-34 | quick editor dead code; pane opens while running; TTS on keys |

**Things nothing owns**

- Who may add or remove actions: five callers add directly, two removal rules (map 2 plan).
- The list of action names and kinds: plugin `name`, `action_kinds.js`, catalog `_TYPE_LABELS`, Type filter list in QML, Options list (four copies, already out of step).
- The Logical Device page's copy of the pane, draft and Undo code (map 2 step 3/5 should cover both).
- Editor models' lifetime (`InputItemModel`/`InputItemBindingModel` creation on every read).
- Input names (patched in from `action_label.py`).

## 11. Size and test coverage

**Size** (lines, roughly): plugins about 14,600 Python + QML/JS in 26 folders plus `common.py` 160 and `axis_pair.py` 143 (largest: Condition 1,963, Macro 1,948, Response Curve 1,259); core of this part about 6,300 (`binding_catalog.py` 1,208, `BindingCatalog.qml` 2,225, `action_model.py` 473, `plugin_manager.py` 320, `ui/profile.py` binding/item models 490, `KeyboardManagerModel` 190, `action_label.py` 119, editor QML about 1,100). Shares `Library` (435) and `Profile` snapshot code with map 2.

**Tests that cover it**

- Plugin loading: `test_audit2_startup_devices.py`, `test_audit3_startup.py` (user plugins, clashes, QML names).
- Every plugin round trip: `test_action_xml_round_trip.py` (15 cases skipped: new action not valid until set up).
- Per action (unit): `test_action_axis_delta`, `_chain_sequences`, `_condition`, `_description`, `_dual_axis_deadzone`, `_macro`, `_map_to_vjoy`, `_merge`, `_root`, `_run_command`, `_tempo`, `_tts`, `_warnings`, `test_map_to_xbox`, `test_map_to_xbox_inputs`, `test_play_sound_missing_file`, `test_action_fixes`, `test_action_editor_fixes`, `test_audit2_macros`.
- Per action at Run (`test/action_interaction/`, 2,300 lines): axis delta, auto-release, chain, condition, double tap, tempo, hat to buttons, macro, map to keyboard, merge axis, modes, pause/resume, smart toggle, split axis, treat as button.
- Configuration page: `test_binding_catalog`, `test_catalog_actions`, `test_catalog_display`, `test_catalog_undo`, `test_undo_bar_labels` (catalog step labels), `test_config_pages_shared_pieces` (Keyboard Delete Key asks the shared question), `test_pane_draft`, `test_audit_editing`, `test_audit2_undo`, `test_audit3_actions_undo`, `test_profile_unused_actions`, `test_library_invalid_children`, `test_profile_missing_child_action`.
- Editing models: `test_input_item_binding_model` (Treat as), `test_vjoy_selector_loads`.
- Keyboard page: `test_mode_refresh_and_add_key`, `test_audit2_keyboard_calibration`, `test_keyboard_gate`.
- R16 fixes and findings (S60a, S85, S97, S112-S119; 2026-10-10): `test_splines` (3 new: control points), `test_action_merge` (round trip, stored name), `action_interaction/test_merge_axis.py::test_maximum_deflection` (its fixture's axis 1 / axis 2 swap fixed), `test_action_editor_fixes` (operation names and list), `test_action_run_command` (2 new), `test_map_to_keyboard_recording.py` (new: S85, S119), `test_core_plugins_paths.py` (new, 42 lines), `test_audit3_actions_undo` (2 new: Reference never offers Root), `test_macro_raw_steps.py` (new, 388 lines: S117, S113 macro part), `test_new_action_defaults.py` (new, 18: S113 condition part, S115, S116, S118).
- Unknown action type kept: `test_data_safety`; curves: `test_splines`; Merge Axis fit: `test_handson_G2_merge_axis_fit`.
- Options list: `test_option_list_saving`, `test_options_layout`; text: `test_glossary_words`, `test_help_guide`.

**Obvious untested paths**

- Profile with Map to vJoy on a PC with no vJoy device (RB20).
- Run with an unfinished action in an input (Reference placeholder, Merge Axis with one axis) (RB19).
- Add Action -> Merge Axis (Reuse) in the pane, edit, Cancel (RB2).
- Save with the pane open (G9).
- Keyboard page: add a key, then add its first action (G10); any Keyboard edit through the UI.
- History Restore / Auto Mapper / Device Pack while the pane is open (G12).
- Map to Mouse motion from a hat; Map to Logical Device relative loop; Load Profile action end to end; Play Sound / TTS at Run (only unit-level).
- Right-click menu quick adds and drag-and-drop of actions and bindings (QML only, no test).
- Every editor QML opening without warnings is checked by hand only (test-plan AE-BTN/AE-AXIS), not by a test.

## 12. Review (user, 2026-10-06)

All [code only] statements in section 8 confirmed, except that S78 and S80
are replaced by Q5 and Q10 below. Every question answered as recommended:

| Q | Decision |
|---|---|
| Q1 | OK on a shared action changes it for every input using it; a shared action is edited as a copy until OK (map 2 A1 (a), A4), including Add Action -> Merge Axis "Reuse" |
| Q2 | Every built-in action plugin is always loaded; can_create() only decides what Add Action offers (hands-on check on a PC without vJoy first) |
| Q3 | Run skips unfinished actions and logs one line each |
| Q4 | Check by hand that a new key can get its first action; if not, show one empty binding |
| Q5 | The Keyboard page uses the same pane as the Configuration page (draft, OK, Undo); until then, ask before removing an action (replaces S78) |
| Q6 | "No actions", "1 action" / "N actions", Title Case type names from the plugins; glossary test covers binding_catalog.py |
| Q7 | Text to Speech lists Keyboard as an input type; close test-plan S-34 |
| Q8 | History Restore, Auto Mapper and Device Pack import close the pane first (asking if it has changes) |
| Q9 | Axis Delta uses the value shaped by earlier actions and treats 0 as a value |
| Q10 | Split Axis's change stays inside its two lists; actions after it see the input's value (replaces S80's Split Axis part) |
| Q11 | While running, the pane opens read-only with "Stop to edit" and no OK |
| Q12 | Chain's removed sequence releases its actions through the one removal rule |
| Q13 | The Load Profile action hands its request to the Run lifecycle owner, done after the event |
| Q14 | New Dual Axis Deadzones are numbered like Merge Axis |
| Q15 | The input name becomes a field of InputItem; the import-time patches in action_label.py go |
| Q16 | Keyboard/mouse output: accepted exception (as page 06 Q9); XboxTarget moves to the output module |
| Q17 | A macro Joystick step goes through the input module's claims like a real event (matches page 06 Q14) |
| Q18 | Remove the unused code listed in Q18 in one clean-up commit |
| Q19 | Chain moves to gremlin.clock; the UI rate limit stays |
| Q20 | Catalog Delete asks (as the code does); test-plan IC-06 marked superseded |
| S43 | 2026-10-07 (D-05-S43-BOTHROWS): the Note shows on the Configuration list's input row and the Keyboard page's key row |
| S60a, S112-S119, S85 and S97 changed | 2026-10-10 (D-05-R16; user approved R1-R11 and G-a, G-b): R16 fixes and findings (section 8 L) |
| S109-S111 | 2026-10-09 (D-09-OSC-OUTPUT; user: "go with your recommendations, approved, go ahead"): the Send OSC action |

The section 8 statements (with the replacements above) are now the
definition of correct for this subsystem.
