# PY-REFS: static reference audit of the Python program code

Agent PY-REFS, 2026-10-12, start 06:10, end 06:18. Repo HEAD 203a74dd. Read-only: no repo file changed. No process left running.

Scope: gremlin/, action_plugins/, dill/, vigem/, vjoy/ (tracked, imported by the program, so included), joystick_gremlin.py, input_tester.py.
Corpus searched: every tracked text file (program .py, qml/ and theme/ .qml/.js, action_plugins .qml, test/, tools/, tools_osc/, .github, pyproject, json, docs).

## Method (scripts in scratchpad/audit/py-refs/)

| Pass | Script | What it does | Output |
|---|---|---|---|
| 1 | scan.py | ast inventory of 10,094 definitions (modules, module functions, classes, methods, class attrs/Signals/Properties, module constants); word-token counts in all text, minus every def/class token in every file (so overrides elsewhere don't count as uses); QML `onFooBar` adds a use of `fooBar` | refs.tsv |
| 2 | scan2.py | scope-aware pass for module-level names: own-module Name loads, `from M import N`, `alias.N` where alias is bound to M (relative imports, `import a.b as c`), whole-string constants (getattr/monkeypatch/setattr), QML/JS tokens; and modules no program file imports | refs2.tsv |
| 3 | scan3.py | for pass-2 candidates: Python NAME tokens in program code with comments and strings excluded (tokenize), plus QML/JS tokens | refs3.tsv |
| 4 | scan4.py | methods, Slots, Properties, Signals, class attrs: program NAME tokens (no comments/docstrings), QML/JS tokens with `onX`, program string constants (getattr, invokeMethod, `fget=` by name); Qt overrides and dunders skipped | refs4.tsv |
| 5 | scan5.py | Signals emitted but never listened to (no `.connect`, `notify=`, QML token/`onX`, string use) | signals.tsv |

Dynamic uses checked by hand for every candidate below: QML string/Slot/Property names (zero QML tokens in all .qml/.js), `onX` handlers, getattr/setattr strings in program code (`getattr(model, "createConfiguredInput")` style, all caught by pass 4), plugin discovery (action_plugins are imported by their `__init__`; no candidate is a plugin entry), decorators (`@QmlElement`, `@QtCore.Slot`, user-script `decorator`), callbacks passed by name (`self.api.library.save_setup` style, which made pass 2 over-report; resolved in pass 3), module `__getattr__`, `global` writes.

Known limits: a method whose name is shared with any other used name (e.g. `update`, `clear`) is counted as used, so methods are under-reported (false negatives only). Dunder methods are implicit protocol and are not judged (list at the end).

## Counts

| Class | Count |
|---|---|
| Dead (no use anywhere outside its definition) | 54 (incl. 10 ViGEm error-code enum members, low value) |
| Used only by tests (incl. test seams by design) | 96 |
| Used only by tools/ or user-script example | 4 (+ user-script API) |
| Modules not imported by the program | 1 (gremlin/validate.py, test-support by design) |
| Signals emitted but never listened to | 1 |

## The 15 most important

| # | Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|---|
| 1 | gremlin/ui/hardware_profile.py:408-429 alias block | 19 constants (compat aliases) | 13 have no use anywhere: `guid_for_module` 411, `_live_devices` 412, `_guid_text` 413, `_pack_file_name` 414, `_archive_stamp` 415, `_unique_archive` 416, `_doc_direction` 417, `_target_direction` 418, `_suggest_pack_name` 421, `_safe_name` 422, `prepare_imported_doc` 427, `module_json_path` 428, `_active_module_path` 429. device_pack.py imports these from gremlin.modules.store directly (lines 40-45); diagnostics/hidhide `_guid_text` are their own functions. Test-only: `_known_pack_devices` 419, `_read_json_dict` 423 (test_device_pack_import.py:568-570), `_filter_nodes` 425, `member_kind` 426 (test_group_member_kind.py:8). Used: `_match_pack_device` 420, `_device_input_ids` 424 | high | Comment says "Old names ... kept for callers that have not moved (GL-093)": a legacy shim, against the "unreleased: no legacy compatibility" rule. Tests importing the old names should import from store |
| 2 | gremlin/ui/hardware_profile.py:2381, 2385, 2389 `stashPhotoFor`, `restorePhotoFor`, `dropPhotoStashFor` | Slots | 0 tokens in any .qml/.js, 0 in program/test code | high | Comment: "Module Setup's names ... until that window uses them" (forwarders to beginEditFor/cancelEditFor/commitEditFor) |
| 3 | gremlin/ui/logical_layout.py:143 `drop_logical_steps` (+ `_MODELS` WeakSet 140, add at 204) | function + registry | No caller anywhere (program, QML, tests); `_MODELS` only feeds it | high (dead) | Possible behaviour gap, not just dead code: docstring says Discard/Restore of the Logical Device must drop its Undo/Redo steps; nothing calls it. Check against the spec before deleting |
| 4 | gremlin/osc_feedback.py:693 `resend_all` (module function) | function | Only `self.resend_all` / `instance().resend_all` (the method) are called; test test_osc_feedback_sources.py:120 calls the method | high | |
| 5 | gremlin/device_library.py:1282 `is_gmap` | function | 0 code tokens anywhere (one doc mention) | high | |
| 6 | gremlin/ui/device_pack.py:2571 `put_gmap_wires`; gremlin/modules/device_zip.py:584 `import_device(put_wires=...)` path | function + parameter | The only program call (device_pack.py:3167) passes `None`; `put_gmap_wires` used only by test_device_zip.py:443,471 | high | The wires-into-profile branch of import_device (device_zip.py:626-695) is test-only in practice |
| 7 | gremlin/ui/vjoy_status.py:170-171 `activeCount`, `pinStamp` (+ getters `_count` 158, `_pin_stamp` 161); :95 `_save_extra` | Properties, function | 0 QML tokens; getters only referenced by `fget=`; `_save_extra` no caller | high | |
| 8 | gremlin/hidhide_driver.py:75 `_WALK_STATS` | module global | Written 5 times (`global`, lines 791-980), never read anywhere | high | Write-only diagnostics state |
| 9 | gremlin/ui/hardware_profile.py:232 `_remove_failure` | function | No caller | high | Sibling `_write_failure` is used |
| 10 | gremlin/ui/binding_catalog.py:209 `leaves_for_item` | function | No program caller; test_catalog_display.py:55 only reads its source text | high | |
| 11 | gremlin/ui/profile.py:1485 `ProfileDeviceListModel` | class (`@QmlElement`) | 0 QML tokens; only test_audit3_screens.py:128 | high (test-only) | Registered QML type nobody uses |
| 12 | gremlin/code_runner.py:299 `run_number`, :305 module `__getattr__` | function, shim | `run_number` test-only (test_audit3_run_stop.py); `__getattr__` serves only `code_runner._run_number` for test/conftest.py (TODO(batch1) at the code) | high | Test-only shim |
| 13 | gremlin/util.py:745 `truncate`, :33 `g_loaded_modules` | function, constant | 0 code tokens (live_debug.py:808 is `stream.truncate()`) | high | |
| 14 | gremlin/ui/window_placement.py:443 `WindowPlacement.listAppearanceChanged` | Signal | Emitted once, never connected/notify/QML; 2 test mentions | medium | |
| 15 | dill/__init__.py:438 `DILL.initialize_capi`; gremlin/user_script.py:894 `Script.set_variable` | methods | 0 tokens anywhere outside the def | high / medium | `set_variable` is on the user-script `Script` class: check it isn't meant as user-script API |

## Other dead items (no use anywhere)

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| gremlin/hidhide_driver.py:640 `SP_DEVINFO_DATA` | ctypes struct | 0 tokens outside def | high | |
| gremlin/hidhide_driver.py:68 `DEVPROP_TYPE_EMPTY`, :73 `CM_LOCATE_DEVNODE_NORMAL` | constants | 0 code tokens (device_reset.py:246 mention is a comment) | high | Win32 constant mirrors |
| gremlin/keyboard.py:46 `_get_keyboard_state` | ctypes binding | 0 tokens | high | |
| gremlin/sendinput.py:31, 32, 34, 41, 52 `MOUSEEVENTF_ABSOLUTE`, `MOUSEEVENTF_HWHEEL`, `MOUSEEVENTF_MOVE_NOCOALESCE`, `MOUSEEVENTF_VIRTUALDESK`, `INPUT_KEYBOARD` | constants | 0 tokens | high | Win32 mirrors; low value |
| gremlin/windows_event_hook.py:98 `WM_MOUSEHWHEEL` | constant | 0 tokens | high | Win32 mirror |
| gremlin/action_analysis.py:18 `AnalysisFunction` | type alias | 0 tokens | high | |
| gremlin/input_tester/compare.py:35 `SECTION_HID` | constant | 0 tokens | high | |
| gremlin/modules/registry.py:26 `_INPUT_WORDS` | constant | 0 tokens | high | |
| gremlin/modules/store.py:117 `_NUMBERED` | regex | 0 tokens | high | |
| gremlin/ui/device_pack.py:3234 `too_new` | public alias of `_too_new` | 0 tokens; device_library.py:2489 uses `_too_new` | high | "Public names for the Device Library store" comment; `collect_wires` alias (3233) is used |
| gremlin/ui/osc_feedback_model.py:184 `COMPANION_VARIABLE` | constant | 0 tokens | high | |
| gremlin/logical_device_file.py:30 `SLUG`, gremlin/osc_device_file.py:33 `SLUG` | constants | Only each other's definition | high | |
| gremlin/modules/runtime.py:20 `syslog` | logger | Never used in runtime.py; no import of it | high | |
| gremlin/ui/module_model.py:1378 `ModuleListModel.stepCount` | Property | 0 QML/program tokens; only test/unit/b1_home_smoke.py | high (test-only) | |
| vigem/vigem_commons.py:43-52 `VIGEM_ERRORS.*` (10 error codes) | IntEnum members | Only `VIGEM_ERROR_NONE` is used (xbox.py:23) | low | Mirror of the ViGEm C API; keeping is reasonable |

## Used only by tests

Test seams by design (keep; listed so the lead can confirm): `_reset_for_tests` in input_tester_link.py:574, osc_discovery.py:342, run_scope.py:425, trace.py:481; device_reset.py:94 `set_runner`, :101 `set_enumerator`, :107 `set_presence`; input_tester/model.py:120 `set_quitter`; ui/keyboard_layout.py:382 `keyboard_store`; gremlin/validate.py (whole module: conftest's rule checks, incl. `after_stop` 450, `is_warning` 65); vigem/own_pads.py:119 `forget_all`; gc_guard.py:94 `uninstall`.

Test-only program API (no program, QML or tools caller; evidence: zero program code/QML tokens, tests named):

| Item (file:line) | Kind | Test users |
|---|---|---|
| device_library.py:1090 `find_device` | function | device_library tests |
| library_profiles.py:226 `is_open_path`, :276 `profiles_using` | functions | test_device_library_FM_profiles.py |
| history.py:735 `restore_file` | function | test_history_store.py, test_history_robust.py |
| input_tester/compare.py:122 `load_expected`; input_tester/devices.py:341 `last_hid_skips` | functions | input tester tests |
| modules/claim.py:179 `claim_is_empty` | function | test_module_claim.py |
| modules/device_class.py:149 `is_internal`, :161 `is_internal_output` | functions | test_device_class.py |
| modules/device_zip.py:368 `export_device` | function | test_device_zip.py, test_b2_zip.py |
| modules/module_file.py:139 `start_fresh` | function | test_module_file_damage.py |
| modules/output.py:661 `vjoy_owned` | function | test_batch1_run_callers.py (string) |
| modules/store.py:433 `names_for_new`, :1045 `set_friendly_name`, :1128 `set_pending_name` | functions | store/layout tests |
| osc_output.py:179 `resolve_target` | function | test_osc_output.py |
| shared_state.py:82 `set_suspend_input_highlighting` | function | 10 tests |
| hidhide_driver.py:593 `get_whitelist` | function | device reset / hidhide smokes |
| ui/binding_catalog.py:202 `assignment_summary` | function | test_catalog_display.py, test_batch3_c4.py |
| ui/hardware_profile.py:403 `_maps_dir` | function | 3 tests (monkeypatch string) |
| ui/module_model.py:711 `cant_send_line` | function | test_cant_send_all.py |
| ui/util.py:687 `save_image_as_pdf` | function | 1 test |
| types.py:704 `ValueRange` | class | test_value_range.py |
| base_classes.py:210 `AbstractActionData.set_behavior_type` | method | test_action_map_to_vjoy.py |
| config.py:580 `init_calibration`, :601 `set_calibration` | methods | test_device_forget.py |
| device_reset.py:56 `ResetDevice.vid_pid_text` | property | test_device_reset_core.py |
| logical_device.py:740 `LogicalRows.set_member_group` | method | test_ld_model.py |
| osc.py:1518 `OscRuntime.last_address`, :1532 `reset_live` | methods | OSC tests (23 uses of reset_live) |
| plugin_manager.py:119 `PluginManager.create_instance` | method | 82 test uses (action plugin tests) |
| profile.py:968 `Library.remove_unused`, :1167 `delete_action`, :1348 `drop_invalid_actions`, :1955 `Profile.drop_unused_actions` | methods | library/profile tests |
| tree.py:47 `append_sibling`, :59 `insert_sibling_after`, :72 `insert_sibling_before`, :149 `node_count`, :199 `depth_first_index` | methods | test_tree.py |
| user_script.py:904 `Script.get_variable` | method | user script tests |
| types.py:641 `DataCreationMode.Reuse`; vjoy/vjoy_interface.py:16 `VJoyState.Owned` | enum members | tests |
| QML-facing Slots/Properties never used by QML: input_tester/model.py:637 `reloadLog`; ui/control_layout.py:1396 `selectionCount`; ui/hardware_layout.py:779 `canRemoveRows`, :842 `rowForDeviceIndex`, :856 `paneMode`; ui/hardware_profile.py:1009 `saveArea`, :1391 `peekPackDevice`, :2262 `removeUnusedPictures`, :2297 `beginEdit`, :2313 `editActive`; ui/hidhide.py:830 `saveWindowSize`; ui/history_model.py:1167 `rowOf`; ui/module_calibration.py:86 `indexOfSlug`; ui/module_inputs.py:238 `rowForDeviceIndex`; ui/module_model.py:1178 `moveSlugBefore`, :1872 `claimedCount`; ui/option.py:464 `sectionName`; ui/osc_device_model.py:741 `encAccelChoices`, :861 `companionText`, :894 `changeName`, :903 `clearAllInputs`, :911 `sortInputs`, :917 `deleteInput`; ui/osc_feedback_model.py:449 `rowById`, :457 `setRowEnabled`, :461 `setRowValueById`, :465 `removeRowById`, :469 `duplicateRow`, :483 `addRowFor`, :501 `actionMissing`; ui/osc_layout.py:1253 `encAccelChoices`; ui/profile.py:1070 `modeStringList`; ui/vjoy_status.py:143 `setPinned` | Slots / Properties | Zero tokens in all .qml/.js (incl. `onX`) and in program code; tests call them directly. Some are probably test conveniences, some are UI that was removed (e.g. OSC feedback row-by-id API, `beginEdit`/`editActive` vs the `...For` variants) |

## Used only by tools/ (not the program)

| Item | Kind | Users |
|---|---|---|
| osc_output.py:71 `last_sender` | function | tools/osc_functional_check.py:684,692 |
| osc.py:274 `OscDevice.find_address` | method | tools/osc_functional_check.py + 36 test uses |
| ui/osc_device_model.py:780 `listenForInput` | Slot | tools/osc_functional_check.py:446 + tests; no QML |

## Not dead: user-script API and implicit protocol

- User-script API (used by user scripts, user_scripts/example.py:106-124): `user_script.py` `KeyboardVariable.decorator` 1333, `LogicalDeviceVariable.decorator` 1389, `OscInputVariable.decorator` 1534, `PhysicalInputVariable.decorator` 1743, `periodic` 1930.
- Dunder methods (no name references by design; not judged): `__eq__/__ne__/__lt__/__str__/__repr__/__add__/__sub__/__mul__/__len__/__enter__/__exit__/__getattr__` in action_plugins/axis_pair.py:48, dill/__init__.py:166-174, base_classes.py:65, error.py:39, event_handler.py:199-210, hidhide_driver.py:363-367, keyboard.py:131-134, mode_manager.py:60, modules/inputs.py:120, osc_rows.py:306, osc_tosc.py:65, sendinput.py:93-102 (`__mul__` is used: map_to_mouse `* speed`), types.py:678-689, ui/action_model.py:96, ui/backend.py:181, ui/device.py:134, windows_event_hook.py:273, vjoy/vjoy.py:853.

## Side note

Test files (not program code) give `SyntaxWarning: invalid escape sequence '\m'` under Python 3.13: test/unit/test_audit3_saving.py and test/unit/test_store_folders.py (probably a Windows path in a non-raw string). No program file warns.
