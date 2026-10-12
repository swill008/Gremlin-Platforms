# EXERCISE: which program functions ever run under the full test suite

Agent EXERCISE, 2026-10-12, repo HEAD 203a74dd. Read-only; no repo file changed.

## Method

- Recorder: `scratchpad/audit/exercise/sitecustomize.py`, Python 3.13 `sys.monitoring` (tool id 4), PY_START event, returns DISABLE after the first hit of each code object. Records co_filename, co_qualname, co_firstlineno for code under gremlin/, action_plugins/, dill/, vigem/, vjoy/, theme/, joystick_gremlin.py, input_tester.py. Writes `hits/hits-<pid>.txt` (append), flushed every second, at exit and inside a wrapped `os._exit` (test children end through os._exit).
- Loaded in every Python process: the runner started with `PYTHONPATH=<exercise dir>;test/hang_trace`. test/conftest.py only prepends test/hang_trace when it is missing, and test/child_env.python_path keeps the inherited PYTHONPATH, so the recorder stays first for pytest parts and every child/smoke; it then chains to test/hang_trace/sitecustomize.py (hang tracing, vJoy and dill guards unchanged).
- Run: `python test/run_tests.py --random-order` with GREMLIN_TEST_STATE and USERPROFILE pointed at scratch folders (the lead's timing state untouched). Off-screen as the suite always is; fake hardware.
- Processes recorded: 464 hit files (pytest parts plus every program/smoke child the tests started).
- Analysis: `scratchpad/audit/exercise/analyse.py` walks the AST of every program .py file (FunctionDef/AsyncFunctionDef, nested included; class bodies and module code not counted) and matches on (file, first line incl. decorators), falling back to a unique qualname. Reference index: every identifier in program .py/.qml/.js (qml/, theme/, gremlin/, action_plugins/ QML) and in test/*.py, strings included, so QML string names, getattr names and Connections handler names count as references.

## Run

- Instrumented run: 427 s (7 min 7 s) wall clock. A normal full run: ~7 min (lead's figure); the parts' own pytest times were 6:30-7:04 for unit parts, the same range as uninstrumented runs, so the recorder cost is within noise.
- Failures under the recorder: none. Results: unit 6673 passed, 25 skipped, 1 xfailed; action_interaction 75 passed; journeys 63 passed; integration 219 skipped (real-vJoy-only folder, skipped in every normal run, so the real vJoy/ViGEm paths it drives are not exercised).

## Totals

- Functions/methods defined in program code: 6923. Executed at least once: 6227 (89.9%). Never executed: 696.
- Never executed with NO reference anywhere else in program code: 31 (the dead-code candidates below). The other 665 are referenced by name (or nested in a never-run function) and are test-coverage gaps, not proof of dead code.
- By likely category (heuristic from path/decorators): UI model code 189, core 161, action plugin 126, Qt Slot/Property (QML may call) 126, hardware (dill/vJoy/ViGEm/HidHide) 47, dunder (implicit call) 42, Windows-only path 5.
- Limitation: a function counts as 'ran' even when only a test called it directly. 'Used only by tests' can't be told apart by this method; the static agents cover that.

## Dead-code candidates (never ran AND no reference elsewhere in program code)

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| dill/__init__.py:174 `GUID.__lt__` | method | never executed in 464 processes; no name reference; real-hardware / Windows path | medium | hardware (dill/vJoy/ViGEm/HidHide) |
| dill/__init__.py:438 `DILL.initialize_capi` | method | never executed in 464 processes; no name reference; real-hardware / Windows path | medium | hardware (dill/vJoy/ViGEm/HidHide) |
| gremlin/base_classes.py:65 `UserFeedback.__eq__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call); name in tests 1x (check: mock/assert-absent/direct call) |
| gremlin/device_library.py:1282 `is_gmap` | function | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | core |
| gremlin/event_handler.py:203 `Event.__ne__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call); name in tests 1x (check: mock/assert-absent/direct call) |
| gremlin/event_handler.py:210 `Event.__repr__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call); name in tests 2x (check: mock/assert-absent/direct call) |
| gremlin/hidhide_driver.py:593 `get_whitelist` | function | never executed in 464 processes; no name reference; real-hardware / Windows path | medium | hardware (dill/vJoy/ViGEm/HidHide); name in tests 4x (check: mock/assert-absent/direct call) |
| gremlin/modules/output.py:661 `vjoy_owned` | function | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | core; name in tests 1x (check: mock/assert-absent/direct call) |
| gremlin/osc_output.py:71 `last_sender` | function | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | core |
| gremlin/profile.py:1955 `Profile.drop_unused_actions` | method | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | core; name in tests 1x (check: mock/assert-absent/direct call) |
| gremlin/sendinput.py:96 `Vector2.__sub__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call) |
| gremlin/sendinput.py:102 `Vector2.__str__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call); name in tests 2x (check: mock/assert-absent/direct call) |
| gremlin/types.py:678 `Point2D.__add__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call) |
| gremlin/types.py:689 `Point2D.__sub__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call) |
| gremlin/ui/action_model.py:96 `SequenceIndex.__str__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call); name in tests 2x (check: mock/assert-absent/direct call) |
| gremlin/ui/backend.py:181 `UIState.__str__` | method | never executed in 464 processes; no name reference; may run implicitly (operator, str(), f-string, logging, sort) | medium | dunder (implicit call); name in tests 2x (check: mock/assert-absent/direct call) |
| gremlin/ui/binding_catalog.py:209 `leaves_for_item` | function | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | UI model code; name in tests 1x (check: mock/assert-absent/direct call) |
| gremlin/ui/hardware_profile.py:232 `_remove_failure` | function | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | UI model code |
| gremlin/ui/hardware_profile.py:403 `_maps_dir` | function | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | UI model code; name in tests 4x (check: mock/assert-absent/direct call) |
| gremlin/ui/hardware_profile.py:2381 `HardwareProfile.stashPhotoFor` | Slot | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | Qt Slot/Property (QML may call) |
| gremlin/ui/hardware_profile.py:2385 `HardwareProfile.restorePhotoFor` | Slot | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | Qt Slot/Property (QML may call) |
| gremlin/ui/hardware_profile.py:2389 `HardwareProfile.dropPhotoStashFor` | Slot | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | Qt Slot/Property (QML may call) |
| gremlin/ui/hidhide.py:830 `HidHideModel.saveWindowSize` | Slot | never executed in 464 processes; name appears nowhere else in program py/qml/js; test/unit/test_cleanup_batch_a.py:183 asserts it is NOT in qml/DialogHardwareHide.qml | high | left behind after a cleanup removed its QML caller |
| gremlin/ui/module_inputs.py:238 `ModuleClaimedInputModel.rowForDeviceIndex` | Slot | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | Qt Slot/Property (QML may call); name in tests 2x (check: mock/assert-absent/direct call) |
| gremlin/ui/option.py:464 `ConfigGroupModel.sectionName` | Qt Property | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | Qt Slot/Property (QML may call); name in tests 2x (check: mock/assert-absent/direct call) |
| gremlin/ui/osc_device_model.py:903 `OscDeviceManagementModel.clearAllInputs` | Slot | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | Qt Slot/Property (QML may call); name in tests 2x (check: mock/assert-absent/direct call) |
| gremlin/ui/osc_layout.py:1253 `OscLayoutModel.encAccelChoices` | Slot | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | Qt Slot/Property (QML may call); name in tests 1x (check: mock/assert-absent/direct call) |
| gremlin/ui/vjoy_status.py:95 `_save_extra` | function | never executed in 464 processes; no name reference; real-hardware / Windows path | medium | hardware (dill/vJoy/ViGEm/HidHide) |
| gremlin/user_script.py:894 `Script.set_variable` | method | never executed in 464 processes; name appears nowhere else in program py/qml/js (strings included) | high | core |
| gremlin/windows_event_hook.py:273 `KeyEvent.__str__` | method | never executed in 464 processes; no name reference; real-hardware / Windows path | medium | Windows-only path; name in tests 2x (check: mock/assert-absent/direct call) |
| vjoy/vjoy.py:853 `VJoy.__str__` | method | never executed in 464 processes; no name reference; real-hardware / Windows path | medium | hardware (dill/vJoy/ViGEm/HidHide); name in tests 2x (check: mock/assert-absent/direct call) |

## Checked by hand (grep of program py/qml/js and test/)

- Test mentions of candidates are not uses: `vjoy_owned` is only monkeypatched (test_batch1_run_callers.py:263); `drop_unused_actions` appears in a source-scan regex (test_library_only.py:23); `leaves_for_item` is read as source text (test_catalog_display.py:55); `clearAllInputs` is a stand-in method in test_osc_qml.py:243; `encAccelChoices` tests call the OscDeviceManagementModel copy, not this OscLayoutModel one; `rowForDeviceIndex` tests use the hardware_layout copy; `get_whitelist` is a stand-in key in test_hidhide_restart_warnings.py:341.
- gremlin/input_tester/steam.py 0%: `steam.steam_running` is the default argument of the input tester model (model.py:165) and every test injects a stand-in; the real Windows process list path never runs. Used, not dead.
- Low-percentage files (xbox_viewer 26%, click_trace 32%, ui/script 45%, macro plugin 52%, condition comparator 52%) are referenced from QML/Main.qml; they are coverage gaps (UI-only or real-device paths), not dead code, unless the static agents find otherwise.

## Per file: % executed (files with any never-run function)

| File | Ran / total | % | Never |
|---|---|---|---|
| gremlin/input_tester/steam.py | 0/2 | 0% | 2 |
| gremlin/ui/xbox_viewer.py | 12/47 | 26% | 35 |
| gremlin/ui/click_trace.py | 10/31 | 32% | 21 |
| vigem/ids.py | 2/6 | 33% | 4 |
| gremlin/ui/script.py | 30/66 | 45% | 36 |
| action_plugins/condition/comparator.py | 14/27 | 52% | 13 |
| action_plugins/macro/__init__.py | 68/130 | 52% | 62 |
| gremlin/macro_raw.py | 5/9 | 56% | 4 |
| gremlin/audio_player.py | 8/14 | 57% | 6 |
| gremlin/ui/module_inputs.py | 14/22 | 64% | 8 |
| gremlin/ui/highlight_option.py | 4/6 | 67% | 2 |
| gremlin/ui/vjoy_status.py | 10/15 | 67% | 5 |
| action_plugins/condition/condition.py | 49/73 | 67% | 24 |
| gremlin/spline.py | 29/43 | 67% | 14 |
| vjoy/vjoy.py | 36/53 | 68% | 17 |
| gremlin/ui/device.py | 61/89 | 69% | 28 |
| gremlin/device_paths.py | 5/7 | 71% | 2 |
| gremlin/error.py | 8/11 | 73% | 3 |
| action_plugins/common.py | 8/11 | 73% | 3 |
| gremlin/base_classes.py | 33/45 | 73% | 12 |
| gremlin/ui/pair_live.py | 15/20 | 75% | 5 |
| gremlin/ui/window_titles.py | 6/8 | 75% | 2 |
| gremlin/unknown_action.py | 9/12 | 75% | 3 |
| action_plugins/response_curve/__init__.py | 36/47 | 77% | 11 |
| gremlin/macro.py | 85/109 | 78% | 24 |
| gremlin/types.py | 27/34 | 79% | 7 |
| gremlin/ui/action_model.py | 36/45 | 80% | 9 |
| gremlin/ui/tray_memory.py | 4/5 | 80% | 1 |
| action_plugins/change_mode/__init__.py | 20/25 | 80% | 5 |
| vigem/vigem_client.py | 4/5 | 80% | 1 |
| gremlin/ui/xbox_device_model.py | 17/21 | 81% | 4 |
| vigem/xbox.py | 17/21 | 81% | 4 |
| gremlin/ui/input_pairing.py | 23/28 | 82% | 5 |
| action_plugins/reference/__init__.py | 14/17 | 82% | 3 |
| gremlin/windows_event_hook.py | 19/23 | 83% | 4 |
| gremlin/user_script.py | 174/209 | 83% | 35 |
| gremlin/ui/live_input.py | 25/30 | 83% | 5 |
| gremlin/ui/trace_model.py | 62/74 | 84% | 12 |
| gremlin/ui/profile.py | 94/112 | 84% | 18 |
| gremlin/ui/control_layout.py | 110/131 | 84% | 21 |
| gremlin/modules/inputs.py | 16/19 | 84% | 3 |
| gremlin/sendinput.py | 35/41 | 85% | 6 |
| gremlin/modules/output.py | 84/98 | 86% | 14 |
| action_plugins/description/__init__.py | 12/14 | 86% | 2 |
| action_plugins/map_to_keyboard/__init__.py | 12/14 | 86% | 2 |
| dill/__init__.py | 32/37 | 86% | 5 |
| action_plugins/load_profile/__init__.py | 13/15 | 87% | 2 |
| action_plugins/pause_resume/__init__.py | 13/15 | 87% | 2 |
| gremlin/osc_persist.py | 7/8 | 88% | 1 |
| gremlin/ui/auto_mapping_tool_modules.py | 7/8 | 88% | 1 |
| gremlin/ui/binding_catalog.py | 14/16 | 88% | 2 |
| gremlin/ui/folder_memory.py | 7/8 | 88% | 1 |
| gremlin/ui/windows_scale_option.py | 7/8 | 88% | 1 |
| action_plugins/play_sound/__init__.py | 14/16 | 88% | 2 |
| action_plugins/run_command/__init__.py | 14/16 | 88% | 2 |
| joystick_gremlin.py | 36/41 | 88% | 5 |
| gremlin/ui/live_debug.py | 67/76 | 88% | 9 |
| gremlin/input_tester/devices.py | 24/27 | 89% | 3 |
| gremlin/osc_bulk.py | 8/9 | 89% | 1 |
| gremlin/ui/osc_device_model.py | 65/73 | 89% | 8 |
| gremlin/ui/logical_layout.py | 42/47 | 89% | 5 |
| gremlin/input_tester/logfiles.py | 9/10 | 90% | 1 |
| gremlin/keyboard.py | 18/20 | 90% | 2 |
| action_plugins/condition/__init__.py | 19/21 | 90% | 2 |
| gremlin/ui/update_model.py | 39/43 | 91% | 4 |
| action_plugins/axis_pair.py | 10/11 | 91% | 1 |
| action_plugins/text_to_speech/__init__.py | 20/22 | 91% | 2 |
| action_plugins/hat_buttons/__init__.py | 21/23 | 91% | 2 |
| gremlin/hidhide_driver.py | 53/58 | 91% | 5 |
| gremlin/ui/keyboard_layout.py | 65/71 | 92% | 6 |
| action_plugins/root/__init__.py | 11/12 | 92% | 1 |
| action_plugins/send_osc/__init__.py | 36/39 | 92% | 3 |
| gremlin/ui/util.py | 37/40 | 92% | 3 |
| gremlin/input_cache.py | 50/54 | 93% | 4 |
| action_plugins/double_tap/__init__.py | 25/27 | 93% | 2 |
| gremlin/ui/option.py | 64/69 | 93% | 5 |
| gremlin/ui/module_pairing.py | 26/28 | 93% | 2 |
| action_plugins/axis_delta/__init__.py | 13/14 | 93% | 1 |
| action_plugins/split_axis/__init__.py | 13/14 | 93% | 1 |
| gremlin/ui/osc_monitor_model.py | 27/29 | 93% | 2 |
| gremlin/log_feed.py | 14/15 | 93% | 1 |
| action_plugins/map_to_mouse/__init__.py | 31/33 | 94% | 2 |
| action_plugins/map_to_xbox/__init__.py | 31/33 | 94% | 2 |
| action_plugins/chain/__init__.py | 16/17 | 94% | 1 |
| gremlin/trace_watch.py | 17/18 | 94% | 1 |
| action_plugins/merge_axis/__init__.py | 34/36 | 94% | 2 |
| gremlin/ui/hardware_profile.py | 154/163 | 94% | 9 |
| gremlin/input_tester/model.py | 87/92 | 95% | 5 |
| gremlin/input_tester_link.py | 38/40 | 95% | 2 |
| gremlin/ui/output_modules.py | 20/21 | 95% | 1 |
| action_plugins/smart_toggle/__init__.py | 20/21 | 95% | 1 |
| gremlin/osc_discovery.py | 21/22 | 95% | 1 |
| gremlin/ui/hardware_layout.py | 84/88 | 95% | 4 |
| gremlin/ui/osc_layout.py | 126/132 | 95% | 6 |
| gremlin/ui/osc_option.py | 42/44 | 95% | 2 |
| gremlin/ui/system_tray.py | 21/22 | 95% | 1 |
| gremlin/updater.py | 21/22 | 95% | 1 |
| gremlin/event_handler.py | 44/46 | 96% | 2 |
| action_plugins/map_to_logical_device/__init__.py | 45/47 | 96% | 2 |
| gremlin/osc_output.py | 23/24 | 96% | 1 |
| gremlin/ui/hidhide.py | 95/99 | 96% | 4 |
| gremlin/modules/registry.py | 24/25 | 96% | 1 |
| gremlin/logical_device.py | 97/101 | 96% | 4 |
| gremlin/osc.py | 104/108 | 96% | 4 |
| action_plugins/dual_axis_deadzone/__init__.py | 26/27 | 96% | 1 |
| gremlin/util.py | 54/56 | 96% | 2 |
| action_plugins/map_to_vjoy/__init__.py | 28/29 | 97% | 1 |
| gremlin/run_scope.py | 29/30 | 97% | 1 |
| action_plugins/tempo/__init__.py | 29/30 | 97% | 1 |
| gremlin/hidhide_watch.py | 30/31 | 97% | 1 |
| gremlin/profile.py | 151/156 | 97% | 5 |
| gremlin/mode_manager.py | 36/37 | 97% | 1 |
| gremlin/ui/module_model.py | 190/195 | 97% | 5 |
| gremlin/config.py | 41/42 | 98% | 1 |
| gremlin/ui/backend.py | 83/85 | 98% | 2 |
| gremlin/code_runner.py | 42/43 | 98% | 1 |
| gremlin/osc_feedback.py | 45/46 | 98% | 1 |
| gremlin/ui/osc_feedback_model.py | 51/52 | 98% | 1 |
| gremlin/modules/store.py | 189/192 | 98% | 3 |
| gremlin/ui/device_library_model.py | 116/117 | 99% | 1 |
| gremlin/ui/device_pack.py | 122/123 | 99% | 1 |
| gremlin/device_library.py | 126/127 | 99% | 1 |

95 other files: every function ran.

## Full never-executed list, by file

Columns: line, qualified name, kind, size in lines, category, references of the name elsewhere in program code / in tests, confidence of 'dead'.

### action_plugins/axis_delta/__init__.py (13/14 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 199 | `AxisDeltaData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/axis_pair.py (10/11 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 45 | `AxisRef.is_valid` | property | 2 | action plugin | 27/66 | low |

### action_plugins/chain/__init__.py (16/17 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 217 | `ChainData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/change_mode/__init__.py (20/25 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 185 | `ChangeModeModel.addTargetMode` | Slot | 5 | Qt Slot/Property (QML may call) | 1/0 | low |
| 192 | `ChangeModeModel.deleteTargetMode` | Slot | 10 | Qt Slot/Property (QML may call) | 1/0 | low |
| 204 | `ChangeModeModel.setTargetMode` | Slot | 11 | Qt Slot/Property (QML may call) | 3/0 | low |
| 347 | `ChangeModeData._get_container` | method | 2 | action plugin | 5/0 | low |
| 351 | `ChangeModeData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/common.py (8/11 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 18 | `joystick_label` | function | 13 | action plugin | 1/0 | low |
| 57 | `RelativeAxisLoop._relative_read` | method | 3 | action plugin | 3/2 | low |
| 61 | `RelativeAxisLoop._relative_write` | method | 3 | action plugin | 2/5 | low |

### action_plugins/condition/__init__.py (19/21 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 183 | `ConditionModel.removeCondition` | Slot | 7 | Qt Slot/Property (QML may call) | 1/0 | low |
| 343 | `ConditionData._handle_behavior_change` | method | 6 | action plugin | 1/0 | low |

### action_plugins/condition/comparator.py (14/27 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 88 | `RangeComparatorModel._set_lower_limit` | method | 4 | action plugin | 2/0 | low |
| 93 | `RangeComparatorModel._set_upper_limit` | method | 4 | action plugin | 2/0 | low |
| 99 | `RangeComparatorModel.lowerLimit` | Qt Property | 2 | Qt Slot/Property (QML may call) | 5/0 | low |
| 103 | `RangeComparatorModel.upperLimit` | Qt Property | 2 | Qt Slot/Property (QML may call) | 5/0 | low |
| 125 | `PressedComparatorModel._set_is_pressed` | method | 4 | action plugin | 7/0 | low |
| 155 | `DirectionComparatorModel.model` | Qt Property | 2 | Qt Slot/Property (QML may call) | 760/3944 | low |
| 163 | `AbstractComparator.from_xml` | method | 2 | action plugin | 34/186 | low |
| 167 | `AbstractComparator.to_xml` | method | 2 | action plugin | 44/212 | low |
| 171 | `AbstractComparator.__call__` | method | 2 | dunder (implicit call) | 2/22 | low |
| 194 | `RangeComparator.__call__` | method | 12 | dunder (implicit call) | 2/22 | low |
| 211 | `RangeComparator.to_xml` | method | 7 | action plugin | 44/212 | low |
| 275 | `DirectionComparator.__call__` | method | 2 | dunder (implicit call) | 2/22 | low |
| 283 | `DirectionComparator.to_xml` | method | 5 | action plugin | 44/212 | low |

### action_plugins/condition/condition.py (49/73 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 70 | `AbstractState.get` | method | 10 | action plugin | 2299/1326 | low |
| 82 | `AbstractState.display_name` | method | 7 | action plugin | 16/16 | low |
| 125 | `AbstractCondition.from_xml` | method | 9 | action plugin | 34/186 | low |
| 135 | `AbstractCondition.to_xml` | method | 9 | action plugin | 44/212 | low |
| 193 | `AbstractCondition.set_input_type` | method | 10 | action plugin | 2/0 | low |
| 204 | `AbstractCondition._update_comparator_if_needed` | method | 9 | action plugin | 2/0 | low |
| 312 | `VJoyCondition.State.get` | method | 15 | action plugin | 2299/1326 | low |
| 328 | `VJoyCondition.State.display_name` | method | 14 | action plugin | 16/16 | low |
| 377 | `VJoyCondition._update_comparator_if_needed` | method | 2 | action plugin | 2/0 | low |
| 383 | `VJoyCondition._set_vjoy_device_id` | method | 12 | action plugin | 2/0 | low |
| 399 | `VJoyCondition._set_vjoy_input_id` | method | 11 | action plugin | 2/0 | low |
| 414 | `VJoyCondition._set_vjoy_input_type` | method | 13 | action plugin | 2/0 | low |
| 460 | `KeyboardCondition.State.get` | method | 2 | action plugin | 2299/1326 | low |
| 463 | `KeyboardCondition.State.display_name` | method | 2 | action plugin | 16/16 | low |
| 487 | `KeyboardCondition.to_xml` | method | 18 | action plugin | 44/212 | low |
| 507 | `KeyboardCondition.updateFromUserInput` | Slot | 22 | Qt Slot/Property (QML may call) | 2/0 | low |
| 530 | `KeyboardCondition._update_comparator_if_needed` | method | 2 | action plugin | 2/0 | low |
| 713 | `JoystickCondition.updateFromUserInput` | Slot | 28 | Qt Slot/Property (QML may call) | 2/0 | low |
| 742 | `JoystickCondition._update_comparator_if_needed` | method | 4 | action plugin | 2/0 | low |
| 798 | `CurrentInputCondition.State.display_name` | method | 2 | action plugin | 16/16 | low |
| 813 | `CurrentInputCondition._update_comparator_if_needed` | method | 5 | action plugin | 2/0 | low |
| 913 | `LogicalDeviceCondition._update_comparator_if_needed` | method | 2 | action plugin | 2/0 | low |
| 916 | `LogicalDeviceCondition._get_logical_input_identifier` | method | 7 | action plugin | 4/0 | low |
| 924 | `LogicalDeviceCondition._set_logical_input_identifier` | method | 8 | action plugin | 5/0 | low |

### action_plugins/description/__init__.py (12/14 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 146 | `DescriptionData._get_container` | method | 2 | action plugin | 5/0 | low |
| 150 | `DescriptionData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/double_tap/__init__.py (25/27 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 160 | `DoubleTapFunctor._reset_fsm` | method | 12 | action plugin | 4/0 | low |
| 329 | `DoubleTapData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/dual_axis_deadzone/__init__.py (26/27 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 366 | `DualAxisDeadzoneData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/hat_buttons/__init__.py (21/23 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 208 | `HatButtonsModel.actionsDroppedBy` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |
| 320 | `HatButtonsData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/load_profile/__init__.py (13/15 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 191 | `LoadProfileData._get_container` | method | 2 | action plugin | 5/0 | low |
| 195 | `LoadProfileData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/macro/__init__.py (68/130 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 73 | `AbstractActionModel.actionType` | Qt Property | 2 | Qt Slot/Property (QML may call) | 3/4 | low |
| 76 | `AbstractActionModel._action_type` | method | 4 | action plugin | 7/0 | low |
| 85 | `JoystickActionModel.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 88 | `JoystickActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 92 | `JoystickActionModel.inputType` | Qt Property | 2 | Qt Slot/Property (QML may call) | 47/10 | low |
| 96 | `JoystickActionModel.label` | Qt Property | 7 | Qt Slot/Property (QML may call) | 997/780 | low |
| 105 | `JoystickActionModel.updateJoystick` | Slot | 26 | Qt Slot/Property (QML may call) | 2/0 | low |
| 132 | `JoystickActionModel._get_is_pressed` | method | 4 | action plugin | 6/1 | low |
| 137 | `JoystickActionModel._set_is_pressed` | method | 4 | action plugin | 7/0 | low |
| 142 | `JoystickActionModel._get_axis_value` | method | 4 | action plugin | 4/0 | low |
| 147 | `JoystickActionModel._set_axis_value` | method | 4 | action plugin | 4/0 | low |
| 152 | `JoystickActionModel._get_hat_direction` | method | 4 | action plugin | 3/0 | low |
| 157 | `JoystickActionModel._set_hat_direction` | method | 5 | action plugin | 3/0 | low |
| 182 | `KeyActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 259 | `LogicalDeviceActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 290 | `LogicalDeviceActionModel._get_input_type` | method | 2 | action plugin | 8/0 | low |
| 302 | `LogicalDeviceActionModel._set_is_pressed` | method | 6 | action plugin | 7/0 | low |
| 309 | `LogicalDeviceActionModel._get_axis_value` | method | 4 | action plugin | 4/0 | low |
| 314 | `LogicalDeviceActionModel._set_axis_value` | method | 6 | action plugin | 4/0 | low |
| 321 | `LogicalDeviceActionModel._get_axis_mode` | method | 2 | action plugin | 4/0 | low |
| 324 | `LogicalDeviceActionModel._set_axis_mode` | method | 5 | action plugin | 4/0 | low |
| 330 | `LogicalDeviceActionModel._get_hat_direction` | method | 4 | action plugin | 3/0 | low |
| 335 | `LogicalDeviceActionModel._set_hat_direction` | method | 7 | action plugin | 3/0 | low |
| 380 | `OscActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 398 | `OscActionModel._get_input_uid` | method | 2 | action plugin | 1/0 | low |
| 418 | `OscActionModel._get_needs_input` | method | 2 | action plugin | 1/0 | low |
| 421 | `OscActionModel._get_is_missing` | method | 2 | action plugin | 1/0 | low |
| 427 | `OscActionModel._set_is_pressed` | method | 5 | action plugin | 7/0 | low |
| 433 | `OscActionModel._get_axis_value` | method | 4 | action plugin | 4/0 | low |
| 438 | `OscActionModel._set_axis_value` | method | 5 | action plugin | 4/0 | low |
| 468 | `MouseButtonActionModel.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 471 | `MouseButtonActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 474 | `MouseButtonActionModel._get_is_pressed` | method | 2 | action plugin | 6/1 | low |
| 477 | `MouseButtonActionModel._set_is_pressed` | method | 4 | action plugin | 7/0 | low |
| 482 | `MouseButtonActionModel._get_button` | method | 6 | action plugin | 1/0 | low |
| 490 | `MouseButtonActionModel.updateButton` | Slot | 11 | Qt Slot/Property (QML may call) | 1/0 | low |
| 512 | `MouseMotionActionModel.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 515 | `MouseMotionActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 518 | `MouseMotionActionModel._get_dx` | method | 2 | action plugin | 1/0 | low |
| 521 | `MouseMotionActionModel._set_dx` | method | 4 | action plugin | 1/0 | low |
| 526 | `MouseMotionActionModel._get_dy` | method | 2 | action plugin | 1/0 | low |
| 529 | `MouseMotionActionModel._set_dy` | method | 4 | action plugin | 1/0 | low |
| 544 | `PauseActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 547 | `PauseActionModel._get_duration` | method | 2 | action plugin | 1/0 | low |
| 566 | `VJoyActionModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 572 | `VJoyActionModel._set_input_type` | method | 11 | action plugin | 2/0 | low |
| 587 | `VJoyActionModel._set_input_id` | method | 4 | action plugin | 2/0 | low |
| 595 | `VJoyActionModel._set_vjoy_id` | method | 4 | action plugin | 2/0 | low |
| 605 | `VJoyActionModel._set_is_pressed` | method | 6 | action plugin | 7/0 | low |
| 617 | `VJoyActionModel._set_axis_value` | method | 6 | action plugin | 4/0 | low |
| 627 | `VJoyActionModel._set_axis_mode` | method | 5 | action plugin | 4/0 | low |
| 638 | `VJoyActionModel._set_hat_direction` | method | 7 | action plugin | 3/0 | low |
| 676 | `RawStepModel.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 679 | `RawStepModel._action_type` | method | 2 | action plugin | 7/0 | low |
| 815 | `ActionListModel.remove` | method | 13 | action plugin | 162/117 | low |
| 829 | `ActionListModel.move_from_to` | method | 30 | action plugin | 2/0 | low |
| 961 | `MacroModel.removeStep` | Slot | 3 | Qt Slot/Property (QML may call) | 1/3 | low |
| 966 | `MacroModel.dropCallback` | Slot | 9 | Qt Slot/Property (QML may call) | 18/0 | low |
| 977 | `MacroModel.startRecording` | Slot | 4 | Qt Slot/Property (QML may call) | 1/0 | low |
| 983 | `MacroModel.stopRecording` | Slot | 4 | Qt Slot/Property (QML may call) | 1/0 | low |
| 1250 | `MacroData._get_container` | method | 2 | action plugin | 5/0 | low |
| 1254 | `MacroData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/map_to_keyboard/__init__.py (12/14 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 190 | `MapToKeyboardData._get_container` | method | 2 | action plugin | 5/0 | low |
| 194 | `MapToKeyboardData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/map_to_logical_device/__init__.py (45/47 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 581 | `MapToLogicalDeviceData._get_container` | method | 2 | action plugin | 5/0 | low |
| 585 | `MapToLogicalDeviceData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/map_to_mouse/__init__.py (31/33 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 407 | `MapToMouseData._get_container` | method | 2 | action plugin | 5/0 | low |
| 411 | `MapToMouseData._handle_behavior_change` | method | 5 | action plugin | 1/0 | low |

### action_plugins/map_to_vjoy/__init__.py (28/29 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 403 | `MapToVjoyData._get_container` | method | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 5/0 | low |

### action_plugins/map_to_xbox/__init__.py (31/33 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 398 | `MapToXboxData._get_container` | method | 2 | action plugin | 5/0 | low |
| 402 | `MapToXboxData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/merge_axis/__init__.py (34/36 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 148 | `MergeAxisFunctor._prefercenter` | method | 3 | action plugin | 1/0 | low |
| 409 | `MergeAxisData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/pause_resume/__init__.py (13/15 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 175 | `PauseResumeData._get_container` | method | 2 | action plugin | 5/0 | low |
| 179 | `PauseResumeData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/play_sound/__init__.py (14/16 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 201 | `PlaySoundData._get_container` | method | 2 | action plugin | 5/0 | low |
| 205 | `PlaySoundData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/reference/__init__.py (14/17 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 175 | `ReferenceData._from_xml` | method | 2 | action plugin | 2/11 | low |
| 203 | `ReferenceData._get_container` | method | 2 | action plugin | 5/0 | low |
| 207 | `ReferenceData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/response_curve/__init__.py (36/47 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 184 | `ControlPoint.handleLeft` | Qt Property | 2 | Qt Slot/Property (QML may call) | 2/0 | low |
| 188 | `ControlPoint.handleRight` | Qt Property | 2 | Qt Slot/Property (QML may call) | 2/0 | low |
| 196 | `ControlPoint.hasLeft` | Qt Property | 2 | Qt Slot/Property (QML may call) | 4/0 | low |
| 200 | `ControlPoint.hasRight` | Qt Property | 2 | Qt Slot/Property (QML may call) | 4/0 | low |
| 330 | `ResponseCurveModel.setControlHandle` | Slot | 32 | Qt Slot/Property (QML may call) | 3/0 | low |
| 364 | `ResponseCurveModel.updateSelectedPoint` | Slot | 5 | Qt Slot/Property (QML may call) | 2/0 | low |
| 377 | `ResponseCurveModel.invertCurve` | Slot | 5 | Qt Slot/Property (QML may call) | 1/0 | low |
| 389 | `ResponseCurveModel._move_control_center` | method | 20 | action plugin | 2/0 | low |
| 410 | `ResponseCurveModel._move_control_handle` | method | 12 | action plugin | 4/0 | low |
| 666 | `ResponseCurveData._get_container` | method | 2 | action plugin | 5/0 | low |
| 670 | `ResponseCurveData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/root/__init__.py (11/12 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 131 | `RootData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/run_command/__init__.py (14/16 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 192 | `RunCommandData._get_container` | method | 2 | action plugin | 5/0 | low |
| 196 | `RunCommandData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/send_osc/__init__.py (36/39 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 283 | `SendOscModel.removeValue` | Slot | 5 | Qt Slot/Property (QML may call) | 1/0 | low |
| 437 | `SendOscData._get_container` | method | 2 | action plugin | 5/0 | low |
| 441 | `SendOscData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/smart_toggle/__init__.py (20/21 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 213 | `SmartToggleData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/split_axis/__init__.py (13/14 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 184 | `SplitAxisData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/tempo/__init__.py (29/30 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 336 | `TempoData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### action_plugins/text_to_speech/__init__.py (20/22 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 249 | `TextToSpeechData._get_container` | method | 2 | action plugin | 5/0 | low |
| 253 | `TextToSpeechData._handle_behavior_change` | method | 4 | action plugin | 1/0 | low |

### dill/__init__.py (32/37 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 174 | `GUID.__lt__` | method | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 0/0 | medium |
| 277 | `DeviceSummary.device_uuid` | property | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 112/16 | low |
| 305 | `_load_dll` | function | 8 | hardware (dill/vJoy/ViGEm/HidHide) | 1/5 | low |
| 438 | `DILL.initialize_capi` | method | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 0/0 | medium |
| 442 | `DILL._apply_api` | method | 7 | hardware (dill/vJoy/ViGEm/HidHide) | 2/0 | low |

### gremlin/audio_player.py (8/14 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 34 | `AudioSample.__init__` | method | 24 | dunder (implicit call) | 298/320 | low |
| 60 | `AudioSample.done` | property | 3 | core | 187/756 | low |
| 64 | `AudioSample.block` | method | 6 | core | 131/111 | low |
| 71 | `AudioSample.cancel` | method | 9 | core | 75/120 | low |
| 81 | `AudioSample.play` | method | 19 | core | 37/31 | low |
| 89 | `AudioSample.play.<locals>.sample_generator` | nested method | 6 | core | 1/0 | follows parent |

### gremlin/base_classes.py (33/45 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 65 | `UserFeedback.__eq__` | method | 4 | dunder (implicit call) | 0/1 | medium |
| 70 | `UserFeedback.__hash__` | method | 2 | dunder (implicit call) | 2/0 | low |
| 332 | `AbstractActionData._from_xml` | method | 8 | core | 2/11 | low |
| 342 | `AbstractActionData._to_xml` | method | 7 | core | 5/22 | low |
| 351 | `AbstractActionData.user_feedback` | method | 10 | core | 4/17 | low |
| 448 | `AbstractActionData.clone` | method | 9 | core | 10/1 | low |
| 458 | `AbstractActionData.copy_unfinished` | method | 9 | core | 1/1 | low |
| 485 | `AbstractActionData._do_create` | method | 13 | core | 2/3 | low |
| 500 | `AbstractActionData._valid_selectors` | method | 7 | core | 8/2 | low |
| 509 | `AbstractActionData._get_container` | method | 10 | core | 5/0 | low |
| 521 | `AbstractActionData._handle_behavior_change` | method | 12 | core | 1/0 | low |
| 644 | `AbstractFunctor.__call__` | method | 12 | dunder (implicit call) | 2/22 | low |

### gremlin/code_runner.py (42/43 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 84 | `VirtualButton.__call__` | method | 10 | dunder (implicit call) | 2/22 | low |

### gremlin/config.py (41/42 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 184 | `Configuration.count` | method | 2 | core | 476/473 | low |

### gremlin/device_library.py (126/127 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 1282 | `is_gmap` | function | 8 | core | 0/0 | high |

### gremlin/device_paths.py (5/7 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 88 | `_method` | function | 4 | core | 3/0 | low |
| 94 | `_directinput` | function | 23 | core | 1/0 | low |

### gremlin/error.py (8/11 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 62 | `MouseError.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 69 | `MissingImplementationError.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 95 | `VJoyConcurrencyError.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |

### gremlin/event_handler.py (44/46 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 203 | `Event.__ne__` | method | 3 | dunder (implicit call) | 0/1 | medium |
| 210 | `Event.__repr__` | method | 10 | dunder (implicit call) | 0/2 | medium |

### gremlin/hidhide_driver.py (53/58 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 101 | `_gremlin_exe` | function | 14 | hardware (dill/vJoy/ViGEm/HidHide) | 2/6 | low |
| 117 | `_nt_image_path` | function | 37 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |
| 156 | `_full_image_name` | function | 55 | hardware (dill/vJoy/ViGEm/HidHide) | 3/6 | low |
| 566 | `set_inverse` | function | 11 | hardware (dill/vJoy/ViGEm/HidHide) | 3/9 | low |
| 593 | `get_whitelist` | function | 4 | hardware (dill/vJoy/ViGEm/HidHide) | 0/4 | medium |

### gremlin/hidhide_watch.py (30/31 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 148 | `device_changed` | function | 7 | hardware (dill/vJoy/ViGEm/HidHide) | 4/0 | low |

### gremlin/input_cache.py (50/54 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 320 | `JoystickWrapper.device_guid` | property | 7 | core | 407/426 | low |
| 340 | `JoystickWrapper.is_axis_valid` | method | 16 | core | 6/8 | low |
| 427 | `JoystickWrapper.hat_count` | property | 7 | core | 27/30 | low |
| 574 | `OscState.hat` | method | 2 | core | 266/249 | low |

### gremlin/input_tester/devices.py (24/27 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 227 | `_load_xinput` | function | 13 | core | 1/0 | low |
| 242 | `xinput_state` | function | 9 | core | 2/3 | low |
| 253 | `xinput_values` | function | 14 | core | 1/0 | low |

### gremlin/input_tester/logfiles.py (9/10 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 145 | `find` | function | 6 | core | 140/346 | low |

### gremlin/input_tester/model.py (87/92 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 92 | `_start_detached` | function | 5 | core | 1/0 | low |
| 106 | `_open_folder` | function | 2 | core | 5/0 | low |
| 825 | `InputTesterModel._get_all_shown` | method | 2 | core | 1/0 | low |
| 1065 | `InputTesterModel.copyPath` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |
| 1073 | `_set_clipboard` | function | 4 | core | 3/2 | low |

### gremlin/input_tester/steam.py (0/2 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 34 | `process_names` | function | 24 | core | 1/2 | low |
| 60 | `steam_running` | function | 2 | core | 3/10 | low |

### gremlin/input_tester_link.py (38/40 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 361 | `_default_starter` | function | 14 | core | 2/0 | low |
| 602 | `InputTesterLink.built` | Qt Property | 2 | Qt Slot/Property (QML may call) | 144/200 | low |

### gremlin/keyboard.py (18/20 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 119 | `Key.lookup_name` | property | 5 | core | 2/0 | low |
| 257 | `is_down_in_windows` | function | 4 | core | 1/1 | low |

### gremlin/log_feed.py (14/15 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 145 | `version` | function | 3 | core | 193/171 | low |

### gremlin/logical_device.py (97/101 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 205 | `LogicalRows.Input._neutral` | method | 2 | core | 3/0 | low |
| 244 | `LogicalRows.Input.key` | method | 2 | core | 3402/2070 | low |
| 259 | `LogicalRows.Input._input_type` | method | 2 | core | 34/0 | low |
| 951 | `LogicalDevice.shows` | method | 3 | core | 484/318 | low |

### gremlin/macro.py (85/109 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 117 | `MacroManager._ask_to_stop` | method | 3 | core | 11/2 | low |
| 269 | `MacroManager._ask_macro_to_stop` | method | 5 | core | 1/0 | low |
| 500 | `Macro.tap` | method | 8 | core | 30/66 | low |
| 531 | `AbstractAction.__call__` | method | 2 | dunder (implicit call) | 2/22 | low |
| 536 | `AbstractAction.create` | method | 3 | core | 102/487 | low |
| 541 | `AbstractAction.to_xml` | method | 2 | core | 44/212 | low |
| 545 | `AbstractAction.from_xml` | method | 2 | core | 34/186 | low |
| 549 | `AbstractAction.is_valid` | method | 2 | core | 27/66 | low |
| 639 | `JoystickAction.to_xml` | method | 29 | core | 44/212 | low |
| 683 | `JoystickAction.is_valid` | method | 2 | core | 27/66 | low |
| 1118 | `MouseButtonAction.is_valid` | method | 2 | core | 27/66 | low |
| 1141 | `MouseMotionAction.__call__` | method | 2 | dunder (implicit call) | 2/22 | low |
| 1144 | `MouseMotionAction.to_xml` | method | 10 | core | 44/212 | low |
| 1159 | `MouseMotionAction.is_valid` | method | 2 | core | 27/66 | low |
| 1332 | `AbstractRepeat.to_xml` | method | 10 | core | 44/212 | low |
| 1343 | `AbstractRepeat.from_xml` | method | 8 | core | 34/186 | low |
| 1353 | `AbstractRepeat._to_xml_additional` | method | 2 | core | 1/0 | low |
| 1357 | `AbstractRepeat._from_xml_additional` | method | 2 | core | 1/0 | low |
| 1374 | `CountRepeat._to_xml_additional` | method | 8 | core | 1/0 | low |
| 1383 | `CountRepeat._from_xml_additional` | method | 7 | core | 1/0 | low |
| 1404 | `ToggleRepeat._to_xml_additional` | method | 7 | core | 1/0 | low |
| 1412 | `ToggleRepeat._from_xml_additional` | method | 7 | core | 1/0 | low |
| 1433 | `HoldRepeat._to_xml_additional` | method | 7 | core | 1/0 | low |
| 1441 | `HoldRepeat._from_xml_additional` | method | 7 | core | 1/0 | low |

### gremlin/macro_raw.py (5/9 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 32 | `RawMacroStep.step_type` | property | 3 | core | 4/0 | low |
| 37 | `RawMacroStep.create` | method | 2 | core | 102/487 | low |
| 57 | `RawMacroStep.__call__` | method | 2 | dunder (implicit call) | 2/22 | low |
| 63 | `RawMacroStep.from_xml` | method | 3 | core | 34/186 | low |

### gremlin/mode_manager.py (36/37 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 257 | `ModeManager._exists` | method | 2 | core | 2/0 | low |

### gremlin/modules/inputs.py (16/19 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 95 | `_ScriptHat.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 99 | `_ScriptHat.direction` | property | 2 | core | 348/259 | low |
| 117 | `_ScriptDevice.hat` | method | 2 | core | 266/249 | low |

### gremlin/modules/output.py (84/98 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 604 | `write_vjoy_axis_linear` | function | 8 | core | 1/10 | low |
| 614 | `_linear_axis_id` | function | 9 | core | 2/0 | low |
| 625 | `release_vjoy_button` | function | 2 | core | 1/8 | low |
| 656 | `vjoy_held` | function | 3 | core | 1/0 | low |
| 661 | `vjoy_owned` | function | 7 | core | 0/1 | high |
| 822 | `_ScriptAxis.value` | property | 2 | core | 3574/2556 | low |
| 835 | `_ScriptButton.is_pressed` | property | 2 | core | 153/189 | low |
| 844 | `_ScriptHat.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 848 | `_ScriptHat.direction` | property | 2 | core | 348/259 | low |
| 852 | `_ScriptHat.direction` | Qt Property | 2 | Qt Slot/Property (QML may call) | 348/259 | low |
| 872 | `_ScriptDevice.hat` | method | 2 | core | 266/249 | low |
| 996 | `xbox_driver_installed` | function | 5 | core | 2/4 | low |
| 1003 | `xbox_driver_version` | function | 5 | core | 1/2 | low |
| 1010 | `xbox_error` | function | 5 | core | 1/3 | low |

### gremlin/modules/registry.py (24/25 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 333 | `folder` | function | 3 | core | 1058/2244 | low |

### gremlin/modules/store.py (189/192 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 1428 | `remove_pictures` | function | 18 | core | 2/0 | low |
| 1843 | `_same_bytes` | function | 7 | core | 2/0 | low |
| 2914 | `drop_file_import_undo` | function | 9 | core | 2/0 | low |

### gremlin/osc.py (104/108 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 231 | `OscDevice.Input.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 263 | `OscDevice.labels_of_type` | method | 10 | core | 2/12 | low |
| 843 | `OscRuntime.recording` | method | 2 | core | 21/10 | low |
| 1735 | `_ticks_dropped` | function | 8 | core | 2/0 | low |

### gremlin/osc_bulk.py (8/9 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 150 | `OscBulkCapture.start` | Slot | 4 | Qt Slot/Property (QML may call) | 524/1069 | low |

### gremlin/osc_discovery.py (21/22 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 237 | `_addresses` | function | 17 | core | 1/2 | low |

### gremlin/osc_feedback.py (45/46 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 693 | `resend_all` | function | 2 | core | 4/1 | low |

### gremlin/osc_output.py (23/24 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 71 | `last_sender` | function | 2 | core | 0/0 | high |

### gremlin/osc_persist.py (7/8 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 79 | `osc_linear_index` | function | 2 | core | 1/0 | low |

### gremlin/profile.py (151/156 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 113 | `AbstractVirtualButton.from_xml` | method | 7 | core | 34/186 | low |
| 122 | `AbstractVirtualButton.to_xml` | method | 7 | core | 44/212 | low |
| 494 | `Draft.original` | method | 6 | core | 35/55 | low |
| 628 | `Library.drafts` | method | 3 | core | 10/0 | low |
| 1955 | `Profile.drop_unused_actions` | method | 4 | core | 0/1 | high |

### gremlin/run_scope.py (29/30 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 166 | `Handle.drop` | method | 6 | core | 133/71 | low |

### gremlin/sendinput.py (35/41 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 96 | `Vector2.__sub__` | method | 2 | dunder (implicit call) | 0/0 | medium |
| 102 | `Vector2.__str__` | method | 2 | dunder (implicit call) | 0/2 | medium |
| 124 | `MotionSource.velocity` | method | 3 | core | 12/0 | low |
| 129 | `MotionSource.describe` | method | 2 | core | 23/99 | low |
| 475 | `mouse_wheel` | function | 3 | core | 3/3 | low |
| 486 | `_send_input` | function | 7 | core | 12/8 | low |

### gremlin/spline.py (29/43 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 38 | `AbstractCurve.control_points` | method | 7 | core | 9/0 | low |
| 47 | `AbstractCurve.add_control_point` | method | 11 | core | 1/15 | low |
| 108 | `AbstractCurve.invert` | method | 3 | core | 25/37 | low |
| 113 | `AbstractCurve.fit` | method | 4 | core | 59/68 | low |
| 119 | `AbstractCurve._enforce_symmetry` | method | 4 | core | 1/0 | low |
| 125 | `AbstractCurve._default_points` | method | 7 | core | 1/0 | low |
| 134 | `AbstractCurve._process_points` | method | 3 | core | 1/0 | low |
| 139 | `AbstractCurve.__call__` | method | 10 | dunder (implicit call) | 2/22 | low |
| 172 | `PiecewiseLinear.invert` | method | 3 | core | 25/37 | low |
| 247 | `CubicSpline.add_control_point` | method | 9 | core | 1/15 | low |
| 257 | `CubicSpline.invert` | method | 4 | core | 25/37 | low |
| 383 | `CubicBezierSpline.add_control_point` | method | 15 | core | 1/15 | low |
| 399 | `CubicBezierSpline.invert` | method | 8 | core | 25/37 | low |
| 414 | `CubicBezierSpline._enforce_symmetry` | method | 28 | core | 1/0 | low |

### gremlin/trace_watch.py (17/18 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 156 | `_axis_indices` | function | 4 | core | 1/0 | low |

### gremlin/types.py (27/34 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 97 | `AxisNames.to_enum` | method | 5 | core | 55/7 | low |
| 218 | `DeviceType.to_string` | method | 5 | core | 78/15 | low |
| 225 | `DeviceType.to_enum` | method | 5 | core | 55/7 | low |
| 257 | `ScriptVariableType.to_string` | method | 5 | core | 78/15 | low |
| 264 | `ScriptVariableType.to_enum` | method | 5 | core | 55/7 | low |
| 678 | `Point2D.__add__` | method | 10 | dunder (implicit call) | 0/0 | medium |
| 689 | `Point2D.__sub__` | method | 10 | dunder (implicit call) | 0/0 | medium |

### gremlin/ui/action_model.py (36/45 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 96 | `SequenceIndex.__str__` | method | 2 | dunder (implicit call) | 0/2 | medium |
| 159 | `ActionModel._qml_path_impl` | method | 4 | UI model code | 2/0 | low |
| 181 | `ActionModel.inputType` | Qt Property | 2 | Qt Slot/Property (QML may call) | 47/10 | low |
| 215 | `ActionModel.isValid` | Qt Property | 2 | Qt Slot/Property (QML may call) | 77/27 | low |
| 324 | `ActionModel.dropAction` | Slot | 23 | Qt Slot/Property (QML may call) | 16/3 | low |
| 349 | `ActionModel.removeAction` | Slot | 9 | Qt Slot/Property (QML may call) | 2/3 | low |
| 367 | `ActionModel._action_behavior` | method | 4 | UI model code | 5/2 | low |
| 375 | `ActionModel._set_action_label` | method | 10 | UI model code | 1/0 | low |
| 438 | `ActionModel._append_drop_action` | method | 18 | UI model code | 2/0 | low |

### gremlin/ui/auto_mapping_tool_modules.py (7/8 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 77 | `_SlugListModel.count` | Qt Property | 2 | Qt Slot/Property (QML may call) | 476/473 | low |

### gremlin/ui/backend.py (83/85 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 181 | `UIState.__str__` | method | 8 | dunder (implicit call) | 0/2 | medium |
| 623 | `Backend.setIsActionExpanded` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |

### gremlin/ui/binding_catalog.py (14/16 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 209 | `leaves_for_item` | function | 10 | UI model code | 0/1 | high |
| 249 | `EditLock.refresh` | Slot | 2 | Qt Slot/Property (QML may call) | 88/120 | low |

### gremlin/ui/click_trace.py (10/31 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 48 | `_name` | function | 10 | UI model code | 61/43 | low |
| 60 | `_window_name` | function | 7 | UI model code | 4/0 | low |
| 69 | `editor_window` | function | 13 | UI model code | 1/0 | low |
| 84 | `_chain` | function | 2 | UI model code | 2/3 | low |
| 88 | `item_chain` | function | 46 | UI model code | 1/0 | low |
| 103 | `item_chain.<locals>.walk` | nested function | 25 | UI model code | 23/247 | follows parent |
| 136 | `_rect` | function | 9 | UI model code | 7/18 | low |
| 147 | `_int` | function | 8 | UI model code | 2/0 | low |
| 157 | `_input_of` | function | 19 | UI model code | 1/0 | low |
| 178 | `hits` | function | 38 | UI model code | 31/50 | low |
| 188 | `hits.<locals>.walk` | nested function | 22 | UI model code | 23/247 | follows parent |
| 218 | `_find` | function | 12 | UI model code | 57/20 | low |
| 232 | `editor_rects` | function | 27 | UI model code | 1/0 | low |
| 261 | `_buttons` | function | 13 | UI model code | 22/43 | low |
| 342 | `ClickTrace.watched` | method | 3 | UI model code | 20/15 | low |
| 369 | `ClickTrace.eventFilter` | method | 15 | UI model code | 1/7 | low |
| 385 | `ClickTrace._mouse` | method | 38 | UI model code | 1/41 | low |
| 404 | `ClickTrace._mouse.<locals>.after` | nested method | 16 | UI model code | 641/1410 | follows parent |
| 427 | `ClickTrace.line` | Slot | 6 | Qt Slot/Property (QML may call) | 673/1154 | low |
| 435 | `ClickTrace.closingFor` | Slot | 3 | Qt Slot/Property (QML may call) | 1/2 | low |
| 440 | `ClickTrace.menu` | Slot | 26 | Qt Slot/Property (QML may call) | 539/711 | low |

### gremlin/ui/control_layout.py (110/131 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 261 | `LayoutItem.type` | property | 1 | UI model code | 957/994 | low |
| 263 | `LayoutItem.id` | property | 1 | UI model code | 3823/1497 | low |
| 265 | `LayoutItem.identifier` | property | 1 | UI model code | 349/116 | low |
| 267 | `LayoutItem.group` | property | 1 | UI model code | 764/390 | low |
| 269 | `LayoutItem.system_name` | property | 1 | UI model code | 34/11 | low |
| 271 | `LayoutItem.second_name` | property | 1 | UI model code | 28/21 | low |
| 273 | `LayoutItem.label` | property | 1 | UI model code | 997/780 | low |
| 275 | `LayoutItem.row_title` | property | 1 | UI model code | 3/5 | low |
| 277 | `LayoutItem.choice_label` | property | 1 | UI model code | 17/8 | low |
| 358 | `ControlLayoutModel._make_store` | method | 2 | UI model code | 3/1 | low |
| 361 | `ControlLayoutModel._device_guid` | method | 2 | UI model code | 54/1 | low |
| 364 | `ControlLayoutModel._identifier` | method | 2 | UI model code | 16/5 | low |
| 367 | `ControlLayoutModel._emit_store_changed` | method | 2 | UI model code | 2/1 | low |
| 379 | `ControlLayoutModel._parent_subtitle` | method | 2 | UI model code | 2/1 | low |
| 450 | `ControlLayoutModel._play_link` | method | 2 | UI model code | 2/0 | low |
| 980 | `ControlLayoutModel.moveRow.<locals>.fn` | nested method | 3 | UI model code | 124/63 | low |
| 1075 | `ControlLayoutModel.sortByName` | Slot | 6 | Qt Slot/Property (QML may call) | 2/1 | low |
| 1076 | `ControlLayoutModel.sortByName.<locals>.fn` | nested method | 3 | UI model code | 124/63 | follows parent |
| 1100 | `ControlLayoutModel.moveGroupUp.<locals>.fn` | nested method | 3 | UI model code | 124/63 | low |
| 1107 | `ControlLayoutModel.moveGroupDown` | Slot | 14 | Qt Slot/Property (QML may call) | 2/1 | low |
| 1116 | `ControlLayoutModel.moveGroupDown.<locals>.fn` | nested method | 3 | UI model code | 124/63 | follows parent |

### gremlin/ui/device.py (61/89 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 267 | `DeviceListModel.selectedIndex` | Qt Property | 2 | Qt Slot/Property (QML may call) | 5/0 | low |
| 271 | `DeviceListModel.selectedIndex` | Qt Property | 3 | Qt Slot/Property (QML may call) | 5/0 | low |
| 327 | `Device.setMode` | Slot | 5 | Qt Slot/Property (QML may call) | 23/21 | low |
| 333 | `Device._get_guid` | method | 5 | UI model code | 13/0 | low |
| 368 | `Device.data` | method | 18 | UI model code | 933/1034 | low |
| 388 | `Device.kindAt` | Slot | 9 | Qt Slot/Property (QML may call) | 12/3 | low |
| 399 | `Device.hwIdAt` | Slot | 4 | Qt Slot/Property (QML may call) | 1/1 | low |
| 424 | `Device._name` | method | 5 | UI model code | 61/43 | low |
| 443 | `Device._get_input_item` | method | 4 | UI model code | 2/0 | low |
| 448 | `Device.roleNames` | method | 2 | UI model code | 3/30 | low |
| 465 | `LogicalDeviceSelectorModel.__init__` | method | 9 | dunder (implicit call) | 298/320 | low |
| 475 | `LogicalDeviceSelectorModel.rowCount` | method | 2 | UI model code | 25/133 | low |
| 478 | `LogicalDeviceSelectorModel.data` | method | 16 | UI model code | 933/1034 | low |
| 495 | `LogicalDeviceSelectorModel.roleNames` | method | 2 | UI model code | 3/30 | low |
| 498 | `LogicalDeviceSelectorModel._set_valid_types` | method | 10 | UI model code | 2/0 | low |
| 509 | `LogicalDeviceSelectorModel._get_current_identifier` | method | 2 | UI model code | 1/0 | low |
| 512 | `LogicalDeviceSelectorModel._set_current_identifier` | method | 9 | UI model code | 1/0 | low |
| 522 | `LogicalDeviceSelectorModel._get_current_index` | method | 2 | UI model code | 2/0 | low |
| 525 | `LogicalDeviceSelectorModel._set_current_index` | method | 8 | UI model code | 7/0 | low |
| 534 | `LogicalDeviceSelectorModel._refresh_model` | method | 4 | UI model code | 1/0 | low |
| 579 | `DeviceAxisSeries._get_guid` | method | 2 | UI model code | 13/0 | low |
| 605 | `DeviceAxisSeries._get_window_size` | method | 2 | UI model code | 1/0 | low |
| 608 | `DeviceAxisSeries._set_window_size` | method | 4 | UI model code | 1/0 | low |
| 629 | `DeviceAxisSeries.axisCount` | Qt Property | 2 | Qt Slot/Property (QML may call) | 3/2 | low |
| 633 | `DeviceAxisSeries.updateSeries` | Slot | 28 | Qt Slot/Property (QML may call) | 1/0 | low |
| 663 | `DeviceAxisSeries.axisIdentifier` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |
| 1098 | `AxisCalibration._set_guid` | method | 2 | UI model code | 15/1 | low |
| 1229 | `AxisCalibration._get_module_slug` | method | 2 | UI model code | 1/0 | low |

### gremlin/ui/device_library_model.py (116/117 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 566 | `DeviceLibraryModel._get_search` | method | 2 | UI model code | 1/0 | low |

### gremlin/ui/device_pack.py (122/123 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 511 | `_pack_key` | function | 4 | UI model code | 4/0 | low |

### gremlin/ui/folder_memory.py (7/8 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 119 | `FolderMemory.kinds` | Slot | 2 | Qt Slot/Property (QML may call) | 66/124 | low |

### gremlin/ui/hardware_layout.py (84/88 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 390 | `HardwareLayoutStore.move_group_before` | method | 10 | UI model code | 4/5 | low |
| 418 | `HardwareLayoutStore.sort_groups` | method | 3 | UI model code | 2/4 | low |
| 437 | `HardwareLayoutStore.delete` | method | 3 | UI model code | 235/244 | low |
| 747 | `HardwareLayoutModel._set_device_name` | method | 2 | UI model code | 4/0 | low |

### gremlin/ui/hardware_profile.py (154/163 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 232 | `_remove_failure` | function | 7 | UI model code | 0/0 | high |
| 241 | `_missing_template` | function | 8 | UI model code | 3/0 | low |
| 403 | `_maps_dir` | function | 3 | UI model code | 0/4 | high |
| 720 | `_output_labels.<locals>.add` | nested function | 6 | UI model code | 362/232 | low |
| 1091 | `HardwareProfile.printImage` | Slot | 37 | Qt Slot/Property (QML may call) | 1/1 | low |
| 1687 | `HardwareProfile.showFolder` | Slot | 3 | Qt Slot/Property (QML may call) | 1/0 | low |
| 2381 | `HardwareProfile.stashPhotoFor` | Slot | 2 | Qt Slot/Property (QML may call) | 0/0 | high |
| 2385 | `HardwareProfile.restorePhotoFor` | Slot | 2 | Qt Slot/Property (QML may call) | 0/0 | high |
| 2389 | `HardwareProfile.dropPhotoStashFor` | Slot | 2 | Qt Slot/Property (QML may call) | 0/0 | high |

### gremlin/ui/hidhide.py (95/99 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 427 | `_save_start` | function | 6 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |
| 830 | `HidHideModel.saveWindowSize` | Slot | 5 | hardware (dill/vJoy/ViGEm/HidHide) | 0/1 | medium |
| 943 | `HidHideModel.setStartOn` | Slot | 4 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |
| 1048 | `HidHideModel.refresh` | Slot | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 88/120 | low |

### gremlin/ui/highlight_option.py (4/6 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 69 | `HighlightSpeedModel._set_speed` | method | 7 | UI model code | 2/0 | low |
| 78 | `HighlightSpeedModel.setSpeed` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |

### gremlin/ui/input_pairing.py (23/28 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 272 | `_MappedModel._get_guid` | method | 2 | UI model code | 13/0 | low |
| 283 | `_MappedModel.rowCount` | method | 2 | UI model code | 25/133 | low |
| 286 | `_MappedModel.data` | method | 6 | UI model code | 933/1034 | low |
| 293 | `_MappedModel.roleNames` | method | 2 | UI model code | 3/30 | low |
| 299 | `_MappedModel.destLabel` | Slot | 9 | Qt Slot/Property (QML may call) | 3/2 | low |

### gremlin/ui/keyboard_layout.py (65/71 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 77 | `_natural_key` | function | 2 | UI model code | 13/0 | low |
| 108 | `KeyItem.label` | property | 2 | UI model code | 997/780 | low |
| 278 | `KeyboardLayoutStore.rename_group` | method | 18 | UI model code | 2/9 | low |
| 297 | `KeyboardLayoutStore.delete_group` | method | 5 | UI model code | 2/8 | low |
| 318 | `KeyboardLayoutStore.move_group_before` | method | 10 | UI model code | 4/5 | low |
| 356 | `KeyboardLayoutStore.delete` | method | 4 | UI model code | 235/244 | low |

### gremlin/ui/live_debug.py (67/76 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 152 | `LiveLog.copyAll` | Slot | 4 | Qt Slot/Property (QML may call) | 1/0 | low |
| 588 | `DebugLog._set_start_empty` | method | 5 | UI model code | 1/0 | low |
| 636 | `DebugLog.running` | Qt Property | 3 | Qt Slot/Property (QML may call) | 364/405 | low |
| 823 | `DebugLog._shown_text` | method | 2 | UI model code | 2/0 | low |
| 827 | `DebugLog.copyShown` | Slot | 4 | Qt Slot/Property (QML may call) | 2/0 | low |
| 833 | `DebugLog.saveTo` | Slot | 8 | Qt Slot/Property (QML may call) | 3/2 | low |
| 843 | `DebugLog.openFolder` | Slot | 4 | Qt Slot/Property (QML may call) | 1/0 | low |
| 904 | `InputMonitor.running` | Qt Property | 3 | Qt Slot/Property (QML may call) | 364/405 | low |
| 945 | `InputMonitor.copyShown` | Slot | 4 | Qt Slot/Property (QML may call) | 2/0 | low |

### gremlin/ui/live_input.py (25/30 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 106 | `DeviceLiveState._get_live_while_active` | method | 2 | UI model code | 1/0 | low |
| 109 | `DeviceLiveState._get_driven` | method | 4 | UI model code | 1/0 | low |
| 130 | `DeviceLiveState._get_device_name` | method | 2 | UI model code | 4/0 | low |
| 414 | `DeviceLiveState.hatXAt` | Slot | 4 | Qt Slot/Property (QML may call) | 1/1 | low |
| 420 | `DeviceLiveState.hatYAt` | Slot | 4 | Qt Slot/Property (QML may call) | 1/1 | low |

### gremlin/ui/logical_layout.py (42/47 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 143 | `drop_logical_steps` | function | 5 | UI model code | 1/0 | low |
| 625 | `LogicalLayoutModel._action_by_id` | method | 8 | UI model code | 3/0 | low |
| 635 | `LogicalLayoutModel.setAxisMode` | Slot | 9 | Qt Slot/Property (QML may call) | 1/0 | low |
| 646 | `LogicalLayoutModel.setAxisScale` | Slot | 6 | Qt Slot/Property (QML may call) | 1/0 | low |
| 654 | `LogicalLayoutModel.setInverted` | Slot | 6 | Qt Slot/Property (QML may call) | 2/2 | low |

### gremlin/ui/module_inputs.py (14/22 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 52 | `ModuleClaimedInputModel._get_guid` | method | 2 | UI model code | 13/0 | low |
| 83 | `ModuleClaimedInputModel._get_device_name` | method | 2 | UI model code | 4/0 | low |
| 95 | `ModuleClaimedInputModel.setMode` | Slot | 6 | Qt Slot/Property (QML may call) | 23/21 | low |
| 166 | `ModuleClaimedInputModel._refresh_one` | method | 7 | UI model code | 1/0 | low |
| 174 | `ModuleClaimedInputModel._input_item` | method | 12 | UI model code | 9/7 | low |
| 190 | `ModuleClaimedInputModel.data` | method | 19 | UI model code | 933/1034 | low |
| 210 | `ModuleClaimedInputModel.roleNames` | method | 2 | UI model code | 3/30 | low |
| 238 | `ModuleClaimedInputModel.rowForDeviceIndex` | Slot | 5 | Qt Slot/Property (QML may call) | 0/2 | high |

### gremlin/ui/module_model.py (190/195 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 784 | `CardSizes.resetAll` | Slot | 2 | Qt Slot/Property (QML may call) | 1/2 | low |
| 1117 | `ModuleListModel.lastSavedPath` | Slot | 2 | Qt Slot/Property (QML may call) | 4/1 | low |
| 1959 | `ModuleListModel.mapsFolderUrl` | Slot | 3 | Qt Slot/Property (QML may call) | 1/0 | low |
| 2007 | `ModuleListModel.dropImportUndo` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |
| 2076 | `ModuleListModel.deleteModuleFile` | Slot | 6 | Qt Slot/Property (QML may call) | 1/0 | low |

### gremlin/ui/module_pairing.py (26/28 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 332 | `_ModulePairMappedModel._get_guid` | method | 2 | UI model code | 13/0 | low |
| 343 | `_ModulePairMappedModel._get_device_name` | method | 2 | UI model code | 4/0 | low |

### gremlin/ui/option.py (64/69 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 327 | `ConfigSectionModel._get_scope` | method | 2 | UI model code | 1/0 | low |
| 464 | `ConfigGroupModel.sectionName` | Qt Property | 2 | Qt Slot/Property (QML may call) | 0/2 | high |
| 636 | `ConfigEntryModel.flags` | method | 2 | UI model code | 38/39 | low |
| 648 | `BaseMetaConfigOptionWidget._qml_path` | method | 5 | UI model code | 1/1 | low |
| 710 | `ActionSequenceOrdering.roleNames` | method | 2 | UI model code | 3/30 | low |

### gremlin/ui/osc_device_model.py (65/73 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 746 | `OscDeviceManagementModel.readImportText` | Slot | 3 | Qt Slot/Property (QML may call) | 3/0 | low |
| 853 | `OscDeviceManagementModel.matchesSeen` | Slot | 4 | Qt Slot/Property (QML may call) | 3/3 | low |
| 867 | `OscDeviceManagementModel.copyText` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |
| 903 | `OscDeviceManagementModel.clearAllInputs` | Slot | 6 | Qt Slot/Property (QML may call) | 0/2 | high |
| 944 | `OscDeviceManagementModel._get_guid` | method | 2 | UI model code | 13/0 | low |
| 988 | `OscDeviceManagementModel.inputIdentifier` | Slot | 9 | Qt Slot/Property (QML may call) | 1/2 | low |
| 998 | `OscDeviceManagementModel._index_to_input` | method | 3 | UI model code | 1/0 | low |
| 1002 | `OscDeviceManagementModel.roleNames` | method | 2 | UI model code | 3/30 | low |

### gremlin/ui/osc_feedback_model.py (51/52 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 661 | `_in_library` | function | 7 | UI model code | 1/0 | low |

### gremlin/ui/osc_layout.py (126/132 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 589 | `OscLayoutStore.delete_group` | method | 8 | UI model code | 2/8 | low |
| 613 | `OscLayoutStore.move_group_before` | method | 10 | UI model code | 4/5 | low |
| 641 | `OscLayoutStore.sort_groups` | method | 3 | UI model code | 2/4 | low |
| 1120 | `OscLayoutModel.kindOf` | Slot | 5 | Qt Slot/Property (QML may call) | 9/0 | low |
| 1253 | `OscLayoutModel.encAccelChoices` | Slot | 3 | Qt Slot/Property (QML may call) | 0/1 | high |
| 1307 | `OscLayoutModel.feedbackMessage` | Qt Property | 2 | Qt Slot/Property (QML may call) | 3/0 | low |

### gremlin/ui/osc_monitor_model.py (27/29 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 248 | `OscMonitorModel._get_active` | method | 2 | UI model code | 1/2 | low |
| 291 | `OscMonitorModel._get_filter` | method | 2 | UI model code | 1/0 | low |

### gremlin/ui/osc_option.py (42/44 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 80 | `_check_rate` | function | 8 | UI model code | 1/0 | low |
| 534 | `OscModuleSetupLink.open` | Slot | 8 | Qt Slot/Property (QML may call) | 992/924 | low |

### gremlin/ui/output_modules.py (20/21 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 339 | `OutputModuleDevices._get_valid_types` | method | 2 | UI model code | 1/0 | low |

### gremlin/ui/pair_live.py (15/20 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 79 | `PairLiveThrottle._bump_axis` | method | 3 | UI model code | 4/1 | low |
| 87 | `PairLiveThrottle._flush` | method | 4 | UI model code | 3/7 | low |
| 92 | `PairLiveThrottle._get_guid` | method | 2 | UI model code | 13/0 | low |
| 188 | `PairLiveThrottle.vjoyAxisValue` | Slot | 2 | Qt Slot/Property (QML may call) | 1/0 | low |
| 199 | `PairLiveThrottle._get_stamp` | method | 2 | UI model code | 3/0 | low |

### gremlin/ui/profile.py (94/112 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 76 | `VirtualButtonModel._get_lower_limit` | method | 2 | UI model code | 1/0 | low |
| 79 | `VirtualButtonModel._set_lower_limit` | method | 4 | UI model code | 2/0 | low |
| 84 | `VirtualButtonModel._get_upper_limit` | method | 2 | UI model code | 1/0 | low |
| 87 | `VirtualButtonModel._set_upper_limit` | method | 4 | UI model code | 2/0 | low |
| 92 | `VirtualButtonModel._get_direction` | method | 2 | UI model code | 2/0 | low |
| 95 | `VirtualButtonModel._set_direction` | method | 5 | UI model code | 2/0 | low |
| 101 | `VirtualButtonModel._get_hat_state` | method | 2 | UI model code | 16/0 | low |
| 104 | `VirtualButtonModel._set_hat_state` | method | 10 | UI model code | 16/0 | low |
| 202 | `HatDirectionModel._get_hat_state` | method | 2 | UI model code | 16/0 | low |
| 205 | `HatDirectionModel._set_hat_state` | method | 10 | UI model code | 16/0 | low |
| 548 | `InputItemBindingModel.virtualButton` | Qt Property | 2 | Qt Slot/Property (QML may call) | 25/0 | low |
| 584 | `InputItemBindingModel.actionCount` | Slot | 3 | Qt Slot/Property (QML may call) | 2/0 | low |
| 1130 | `LabelValueSelectionModel._get_current_value` | method | 2 | UI model code | 1/0 | low |
| 1176 | `StartupModeModel._reset` | method | 6 | UI model code | 11/10 | low |
| 1329 | `OutputVJoyListModel._reset` | method | 5 | UI model code | 11/10 | low |
| 1382 | `OutputVJoyInitialValuesModel._reset` | method | 4 | UI model code | 11/10 | low |
| 1448 | `ProfileSettingsModel._reset` | method | 3 | UI model code | 11/10 | low |
| 1538 | `ProfileDeviceListModel.roleNames` | method | 2 | UI model code | 3/30 | low |

### gremlin/ui/script.py (30/66 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 62 | `AbstractVariableModel.evaluate_validity` | method | 2 | UI model code | 11/0 | low |
| 70 | `BoolVariableModel.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 75 | `BoolVariableModel._get_value` | method | 2 | UI model code | 10/0 | low |
| 78 | `BoolVariableModel._set_value` | method | 5 | UI model code | 10/0 | low |
| 91 | `FloatVariableModel.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 96 | `FloatVariableModel._get_value` | method | 2 | UI model code | 10/0 | low |
| 99 | `FloatVariableModel._set_value` | method | 5 | UI model code | 10/0 | low |
| 106 | `FloatVariableModel.maxValue` | Qt Property | 2 | Qt Slot/Property (QML may call) | 37/1 | low |
| 110 | `FloatVariableModel.minValue` | Qt Property | 2 | Qt Slot/Property (QML may call) | 37/0 | low |
| 125 | `IntegerVariableModel._get_value` | method | 2 | UI model code | 10/0 | low |
| 128 | `IntegerVariableModel._set_value` | method | 5 | UI model code | 10/0 | low |
| 135 | `IntegerVariableModel.maxValue` | Qt Property | 2 | Qt Slot/Property (QML may call) | 37/1 | low |
| 139 | `IntegerVariableModel.minValue` | Qt Property | 2 | Qt Slot/Property (QML may call) | 37/0 | low |
| 149 | `KeyboardVariableModel.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 155 | `KeyboardVariableModel.label` | Qt Property | 2 | Qt Slot/Property (QML may call) | 997/780 | low |
| 159 | `KeyboardVariableModel.updateKeyboard` | Slot | 12 | Qt Slot/Property (QML may call) | 1/0 | low |
| 215 | `LogicalDeviceModel.label` | Qt Property | 2 | Qt Slot/Property (QML may call) | 997/780 | low |
| 219 | `LogicalDeviceModel.validTypes` | Qt Property | 2 | Qt Slot/Property (QML may call) | 16/8 | low |
| 300 | `ModeVariableModel.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 305 | `ModeVariableModel._get_value` | method | 2 | UI model code | 10/0 | low |
| 308 | `ModeVariableModel._set_value` | method | 5 | UI model code | 10/0 | low |
| 321 | `SelectionVariableModel.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 326 | `SelectionVariableModel._get_value` | method | 2 | UI model code | 10/0 | low |
| 329 | `SelectionVariableModel._set_value` | method | 5 | UI model code | 10/0 | low |
| 336 | `SelectionVariableModel.options` | Qt Property | 2 | Qt Slot/Property (QML may call) | 203/175 | low |
| 346 | `StringVariableModel.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 351 | `StringVariableModel._get_value` | method | 2 | UI model code | 10/0 | low |
| 354 | `StringVariableModel._set_value` | method | 5 | UI model code | 10/0 | low |
| 367 | `PhysicalInputVariableModel.__init__` | method | 4 | dunder (implicit call) | 298/320 | low |
| 373 | `PhysicalInputVariableModel.label` | Qt Property | 2 | Qt Slot/Property (QML may call) | 997/780 | low |
| 377 | `PhysicalInputVariableModel.validTypes` | Qt Property | 2 | Qt Slot/Property (QML may call) | 16/8 | low |
| 381 | `PhysicalInputVariableModel.updateJoystick` | Slot | 16 | Qt Slot/Property (QML may call) | 2/0 | low |
| 409 | `VirtualInputVariableModel.label` | Qt Property | 2 | Qt Slot/Property (QML may call) | 997/780 | low |
| 419 | `VirtualInputVariableModel._set_input_type` | method | 6 | UI model code | 2/0 | low |
| 429 | `VirtualInputVariableModel._set_input_id` | method | 5 | UI model code | 2/0 | low |
| 438 | `VirtualInputVariableModel._set_vjoy_id` | method | 5 | UI model code | 2/0 | low |

### gremlin/ui/system_tray.py (21/22 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 300 | `SystemTrayIcon._destroy_system_tray_cb` | method | 5 | UI model code | 1/0 | low |

### gremlin/ui/trace_model.py (62/74 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 405 | `TraceSwitch._set_on` | method | 2 | UI model code | 3/0 | low |
| 476 | `TraceView.hidhide` | Qt Property | 2 | Qt Slot/Property (QML may call) | 88/215 | low |
| 567 | `TraceView._filter` | method | 5 | UI model code | 12/0 | low |
| 645 | `TraceView.setTick` | Slot | 5 | Qt Slot/Property (QML may call) | 1/0 | low |
| 652 | `TraceView.setOutOfStep` | Slot | 3 | Qt Slot/Property (QML may call) | 1/0 | low |
| 657 | `TraceView.setHidhide` | Slot | 3 | Qt Slot/Property (QML may call) | 1/0 | low |
| 689 | `TraceView.noticeLine` | Slot | 7 | Qt Slot/Property (QML may call) | 1/0 | low |
| 698 | `TraceView.dismissNotice` | Slot | 3 | Qt Slot/Property (QML may call) | 1/0 | low |
| 703 | `TraceView.clearView` | Slot | 4 | Qt Slot/Property (QML may call) | 3/1 | low |
| 718 | `TraceView.dismissClearError` | Slot | 3 | Qt Slot/Property (QML may call) | 1/0 | low |
| 745 | `TraceView.showFile` | Slot | 4 | Qt Slot/Property (QML may call) | 3/1 | low |
| 751 | `TraceView.copyShown` | Slot | 6 | Qt Slot/Property (QML may call) | 2/0 | low |

### gremlin/ui/tray_memory.py (4/5 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 71 | `let_hidden_window_release_graphics` | function | 7 | UI model code | 1/2 | low |

### gremlin/ui/update_model.py (39/43 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 158 | `UpdateModel.installKind` | Qt Property | 2 | Qt Slot/Property (QML may call) | 1/0 | low |
| 431 | `UpdateModel._on_progress` | method | 3 | UI model code | 1/0 | low |
| 482 | `UpdateModel._ready` | method | 4 | UI model code | 21/3 | low |
| 497 | `UpdateModel.install` | Slot | 4 | Qt Slot/Property (QML may call) | 46/204 | low |

### gremlin/ui/util.py (37/40 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 276 | `InputListenerModel._get_event_types` | method | 2 | UI model code | 1/0 | low |
| 311 | `InputListenerModel._get_multiple_inputs` | method | 2 | UI model code | 1/0 | low |
| 580 | `ProcessListModel.refresh` | Slot | 5 | Qt Slot/Property (QML may call) | 88/120 | low |

### gremlin/ui/vjoy_status.py (10/15 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 95 | `_save_extra` | function | 6 | hardware (dill/vJoy/ViGEm/HidHide) | 0/0 | medium |
| 120 | `VJoyStatus.refresh` | Slot | 11 | hardware (dill/vJoy/ViGEm/HidHide) | 88/120 | low |
| 133 | `VJoyStatus.isActive` | Slot | 4 | hardware (dill/vJoy/ViGEm/HidHide) | 11/22 | low |
| 158 | `VJoyStatus._count` | method | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 6/7 | low |
| 161 | `VJoyStatus._pin_stamp` | method | 8 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |

### gremlin/ui/window_titles.py (6/8 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 46 | `_set_native` | function | 4 | UI model code | 1/0 | low |
| 64 | `TitleBars.eventFilter` | method | 4 | UI model code | 1/7 | low |

### gremlin/ui/windows_scale_option.py (7/8 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 65 | `WindowsScaleModel._get_running_disabled` | method | 2 | Windows-only path | 1/0 | low |

### gremlin/ui/xbox_device_model.py (17/21 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 108 | `XboxDriverStatus.openDownload` | Slot | 2 | Qt Slot/Property (QML may call) | 2/1 | low |
| 112 | `XboxDriverStatus.openGameControllers` | Slot | 12 | Qt Slot/Property (QML may call) | 2/1 | low |
| 194 | `XboxDeviceModel._set_pad_id` | method | 7 | UI model code | 1/0 | low |
| 202 | `XboxDeviceModel._get_guid` | method | 2 | UI model code | 13/0 | low |

### gremlin/ui/xbox_viewer.py (12/47 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 44 | `_xbox_maps_for_item` | function | 2 | UI model code | 4/0 | low |
| 48 | `_chip` | function | 3 | UI model code | 6/44 | low |
| 53 | `_pair_label` | function | 3 | UI model code | 2/1 | low |
| 58 | `_source_label` | function | 6 | UI model code | 1/0 | low |
| 66 | `_mapped_xbox_rows` | function | 28 | UI model code | 1/0 | low |
| 130 | `_XboxMappedModel._get_guid` | method | 2 | UI model code | 13/0 | low |
| 133 | `_XboxMappedModel._set_guid` | method | 7 | UI model code | 15/1 | low |
| 141 | `_XboxMappedModel.rowCount` | method | 2 | UI model code | 25/133 | low |
| 144 | `_XboxMappedModel.data` | method | 6 | UI model code | 933/1034 | low |
| 151 | `_XboxMappedModel.roleNames` | method | 2 | UI model code | 3/30 | low |
| 159 | `XboxMappedAxisModel.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 171 | `XboxMappedHatModel.__init__` | method | 2 | dunder (implicit call) | 298/320 | low |
| 197 | `XboxPadListModel._get_guid` | method | 2 | UI model code | 13/0 | low |
| 200 | `XboxPadListModel._set_guid` | method | 7 | UI model code | 15/1 | low |
| 208 | `XboxPadListModel.rowCount` | method | 2 | UI model code | 25/133 | low |
| 211 | `XboxPadListModel.data` | method | 4 | UI model code | 933/1034 | low |
| 216 | `XboxPadListModel.roleNames` | method | 2 | UI model code | 3/30 | low |
| 219 | `XboxPadListModel._get_count` | method | 2 | UI model code | 3/0 | low |
| 273 | `XboxViewerDeviceModel.data` | method | 6 | UI model code | 933/1034 | low |
| 296 | `XboxLiveThrottle.__init__` | method | 22 | dunder (implicit call) | 298/320 | low |
| 319 | `XboxLiveThrottle._bump` | method | 3 | UI model code | 16/0 | low |
| 323 | `XboxLiveThrottle._bump_axis` | method | 3 | UI model code | 4/1 | low |
| 327 | `XboxLiveThrottle._bump_button` | method | 3 | UI model code | 4/1 | low |
| 331 | `XboxLiveThrottle._flush` | method | 4 | UI model code | 3/7 | low |
| 336 | `XboxLiveThrottle._get_guid` | method | 2 | UI model code | 13/0 | low |
| 339 | `XboxLiveThrottle._set_guid` | method | 14 | UI model code | 15/1 | low |
| 354 | `XboxLiveThrottle._on_event` | method | 23 | UI model code | 3/3 | low |
| 378 | `XboxLiveThrottle._poll_xbox` | method | 13 | UI model code | 2/0 | low |
| 393 | `XboxLiveThrottle.axisValue` | Slot | 2 | Qt Slot/Property (QML may call) | 15/0 | low |
| 397 | `XboxLiveThrottle.buttonValue` | Slot | 2 | Qt Slot/Property (QML may call) | 3/3 | low |
| 401 | `XboxLiveThrottle.xboxValue` | Slot | 3 | Qt Slot/Property (QML may call) | 3/0 | low |
| 405 | `XboxLiveThrottle._get_stamp` | method | 2 | UI model code | 3/0 | low |
| 408 | `XboxLiveThrottle._get_axis_stamp` | method | 2 | UI model code | 2/0 | low |
| 411 | `XboxLiveThrottle._get_button_stamp` | method | 2 | UI model code | 2/0 | low |
| 414 | `XboxLiveThrottle._get_xbox_stamp` | method | 2 | UI model code | 1/0 | low |

### gremlin/unknown_action.py (9/12 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 38 | `UnknownFunctor.__call__` | method | 4 | dunder (implicit call) | 2/22 | low |
| 50 | `UnknownActionModel._action_behavior` | method | 5 | core | 5/2 | low |
| 146 | `UnknownActionData._handle_behavior_change` | method | 4 | core | 1/0 | low |

### gremlin/updater.py (21/22 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 356 | `updates_dir` | function | 2 | core | 2/6 | low |

### gremlin/user_script.py (174/209 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 178 | `PeriodicRegistry._ask_to_stop` | method | 2 | core | 11/2 | low |
| 375 | `JoystickPlugin.install` | method | 15 | core | 46/204 | low |
| 404 | `KeyboardPlugin.install` | method | 12 | core | 46/204 | low |
| 513 | `ScriptVariableRegistry.clear` | method | 3 | core | 259/294 | low |
| 549 | `ScriptVariableRegistry.set` | method | 10 | core | 888/904 | low |
| 787 | `Script.load_error` | Qt Property | 2 | Qt Slot/Property (QML may call) | 9/27 | low |
| 894 | `Script.set_variable` | method | 9 | core | 0/0 | high |
| 1112 | `AbstractVariable.value` | property | 2 | core | 3574/2556 | low |
| 1117 | `AbstractVariable.value` | Qt Property | 2 | Qt Slot/Property (QML may call) | 3574/2556 | low |
| 1134 | `AbstractVariable.is_valid` | method | 2 | core | 27/66 | low |
| 1138 | `AbstractVariable._from_xml` | method | 2 | core | 2/11 | low |
| 1142 | `AbstractVariable._to_xml` | method | 2 | core | 5/22 | low |
| 1146 | `AbstractVariable._assign_value_from` | method | 2 | core | 1/0 | low |
| 1242 | `FloatVariable._assign_value_from` | method | 2 | core | 1/0 | low |
| 1304 | `KeyboardVariable.value` | property | 2 | core | 3574/2556 | low |
| 1311 | `KeyboardVariable.is_valid` | method | 2 | core | 27/66 | low |
| 1314 | `KeyboardVariable._from_xml` | method | 5 | core | 2/11 | low |
| 1320 | `KeyboardVariable._to_xml` | method | 9 | core | 5/22 | low |
| 1330 | `KeyboardVariable._assign_value_from` | method | 2 | core | 1/0 | low |
| 1389 | `LogicalDeviceVariable.decorator` | method | 14 | core | 10/8 | low |
| 1404 | `LogicalDeviceVariable.create_decorator` | method | 7 | core | 3/0 | low |
| 1464 | `LogicalDeviceVariable._assign_value_from` | method | 3 | core | 1/0 | low |
| 1509 | `OscInputVariable.value` | Qt Property | 2 | Qt Slot/Property (QML may call) | 3574/2556 | low |
| 1513 | `OscInputVariable.valid_types` | property | 2 | core | 19/6 | low |
| 1602 | `ModeVariable._assign_value_from` | method | 2 | core | 1/0 | low |
| 1659 | `SelectionVariable._assign_value_from` | method | 2 | core | 1/0 | low |
| 1722 | `PhysicalInputVariable.input_type` | property | 2 | core | 576/162 | low |
| 1726 | `PhysicalInputVariable.input_id` | property | 2 | core | 465/292 | low |
| 1787 | `PhysicalInputVariable._assign_value_from` | method | 5 | core | 1/0 | low |
| 1820 | `VirtualInputVariable.value` | property | 2 | core | 3574/2556 | low |
| 1824 | `VirtualInputVariable.value` | Qt Property | 2 | Qt Slot/Property (QML may call) | 3574/2556 | low |
| 1836 | `VirtualInputVariable.input_type` | property | 2 | core | 576/162 | low |
| 1843 | `VirtualInputVariable.remap` | method | 12 | core | 4/0 | low |
| 1880 | `VirtualInputVariable._assign_value_from` | method | 5 | core | 1/0 | low |
| 1914 | `keyboard.<locals>.wrap.<locals>.wrapper_fn` | nested function | 2 | core | 6/0 | low |

### gremlin/util.py (54/56 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 745 | `truncate` | function | 15 | core | 2/0 | low |
| 984 | `log` | function | 7 | core | 296/458 | low |

### gremlin/windows_event_hook.py (19/23 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 273 | `KeyEvent.__str__` | method | 10 | Windows-only path | 0/2 | medium |
| 309 | `_Hook._handler` | method | 2 | Windows-only path | 13/5 | low |
| 338 | `_Hook._ask_to_stop` | method | 4 | Windows-only path | 11/2 | low |
| 478 | `MouseHook.users` | property | 2 | Windows-only path | 12/8 | low |

### joystick_gremlin.py (36/41 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 435 | `_this_process_tree` | function | 44 | core | 3/4 | low |
| 481 | `_process_image_name` | function | 22 | core | 1/4 | low |
| 533 | `_gremlin_windows` | function | 28 | core | 2/1 | low |
| 542 | `_gremlin_windows.<locals>._enum` | nested function | 14 | core | 1/0 | follows parent |
| 693 | `acquire_instance_lock` | function | 8 | core | 3/7 | low |

### vigem/ids.py (2/6 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 17 | `driver_file` | function | 4 | hardware (dill/vJoy/ViGEm/HidHide) | 2/0 | low |
| 23 | `driver_installed` | function | 4 | hardware (dill/vJoy/ViGEm/HidHide) | 2/0 | low |
| 29 | `driver_version` | function | 5 | hardware (dill/vJoy/ViGEm/HidHide) | 4/6 | low |
| 36 | `vigem_client_error` | function | 7 | hardware (dill/vJoy/ViGEm/HidHide) | 2/0 | low |

### vigem/vigem_client.py (4/5 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 42 | `load_error` | function | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 9/27 | low |

### vigem/xbox.py (17/21 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 28 | `XboxError.__init__` | method | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 298/320 | low |
| 154 | `_stick_to_short` | function | 3 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |
| 159 | `_trigger_to_byte` | function | 2 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |
| 163 | `_as_hat` | function | 21 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |

### vjoy/vjoy.py (36/53 ran)

| Line | Name | Kind | Size | Category | Refs prog/tests | Dead? |
|---|---|---|---|---|---|---|
| 33 | `_error_string` | function | 12 | hardware (dill/vJoy/ViGEm/HidHide) | 13/0 | low |
| 75 | `device_exists` | function | 14 | hardware (dill/vJoy/ViGEm/HidHide) | 8/9 | low |
| 101 | `axis_count` | function | 10 | hardware (dill/vJoy/ViGEm/HidHide) | 47/31 | low |
| 113 | `button_count` | function | 10 | hardware (dill/vJoy/ViGEm/HidHide) | 49/43 | low |
| 125 | `hat_count` | function | 10 | hardware (dill/vJoy/ViGEm/HidHide) | 27/30 | low |
| 137 | `hat_configuration_valid` | function | 16 | hardware (dill/vJoy/ViGEm/HidHide) | 1/6 | low |
| 410 | `Hat._set_discrete_direction` | method | 23 | hardware (dill/vJoy/ViGEm/HidHide) | 1/0 | low |
| 562 | `VJoy.is_owned` | method | 10 | hardware (dill/vJoy/ViGEm/HidHide) | 2/1 | low |
| 574 | `VJoy.axis_count` | property | 7 | hardware (dill/vJoy/ViGEm/HidHide) | 47/31 | low |
| 583 | `VJoy.button_count` | property | 7 | hardware (dill/vJoy/ViGEm/HidHide) | 49/43 | low |
| 592 | `VJoy.hat_count` | property | 7 | hardware (dill/vJoy/ViGEm/HidHide) | 27/30 | low |
| 600 | `VJoy.axis_id` | method | 17 | hardware (dill/vJoy/ViGEm/HidHide) | 100/51 | low |
| 701 | `VJoy.is_button_valid` | method | 10 | hardware (dill/vJoy/ViGEm/HidHide) | 2/8 | low |
| 712 | `VJoy.is_hat_valid` | method | 10 | hardware (dill/vJoy/ViGEm/HidHide) | 2/7 | low |
| 759 | `VJoy.last_active` | property | 3 | hardware (dill/vJoy/ViGEm/HidHide) | 2/5 | low |
| 853 | `VJoy.__str__` | method | 9 | hardware (dill/vJoy/ViGEm/HidHide) | 0/2 | medium |
| 942 | `deadzone` | function | 23 | hardware (dill/vJoy/ViGEm/HidHide) | 96/84 | low |
