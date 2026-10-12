# LEFTOVERS audit (agent LEFTOVERS, HEAD 203a74dd, read-only)

Start 06:10, end 06:16 (scan); report written right after. No repo file changed. No process running.
Helper scripts: scratchpad/audit/leftovers/ (commented_code.py, const_props.py, dup_funcs.py; raw output cc.txt).

Scope: gremlin/, qml/ (help/*.js text excluded from code scans), theme/, action_plugins/, dill/, vigem/,
joystick_gremlin.py, input_tester.py.

Counts: commented-out code 1 real block; compatibility / legacy readers 22; one-time code 5 trackers
(OT-1..OT-5) in 17 files; TODO/FIXME notes 13 (2 stale); constant flags 12 groups; duplicate helper
families 16.

---

## 1. Commented-out code (not prose)

Method: every `#` / `//` comment line was tested: Python lines with `ast.parse`, JS/QML lines with a
code-shape regex; 85 hits, checked by hand. Nearly all were prose of the form `Word: ...` or usage examples
in a file header.

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| action_plugins/response_curve/__init__.py:271-273 | commented call `# self._set_is_symmetric(True)` under a TODO | the only real commented-out statement in the program | high | Remove it with its TODO, or do the TODO |
| gremlin/profile.py:2087-2088 | formula in a comment (`input_id = extended_bit << 8 \| scan_code`) | the next line does the same thing | high (that it is redundant) | Explanation only; harmless. Could go |
| joystick_gremlin.py:362 | `# MB_OK \| MB_ICONERROR` names the 0x10 constant | explanation | n/a | Keep (it is documentation) |
| qml/confirm.js:6-7, qml/FilePicker.qml:7-16, qml/MessageLine.qml:11, qml/Pulse.qml:11, qml/DeviceMapOptionsWindow.qml:18, qml/ShortcutsWindow.qml:17 | usage examples in header comments | documentation | n/a | Not leftovers |

No `/* ... */` code blocks and no `if False:` / `if 0:` blocks in program code.

---

## 2. Compatibility shims and legacy readers (CLAUDE.md: no legacy compatibility by default)

"Decided" means a spec decision or tracker item covers it (it stays until that decision is revisited).
Everything else is a candidate for removal, which needs the user's go-ahead (some are spec statements).

| Item (file:line) | What it supports | Evidence | Confidence | Notes |
|---|---|---|---|---|
| gremlin/ui/hardware_profile.py:408-430 | 19 old module-level alias names for `gremlin.modules.store` / `registry` functions, "kept for callers that have not moved yet (GL-093)" | Program callers through hardware_profile: only `_match_pack_device` (hardware_profile.py:1411) and `_device_input_ids` (:815, :828). device_pack.py imports its own copies from store. No caller anywhere: `guid_for_module`, `_pack_file_name`, `_archive_stamp`, `prepare_imported_doc`, `module_json_path`, `_active_module_path`. Tests only: `_live_devices`, `_known_pack_devices`, `_read_json_dict`, `_filter_nodes` (and possibly `member_kind`, `_guid_text`: other modules share the name) | high | The clearest shim. Point the 2 callers and the tests at store, then delete the block |
| gremlin/osc.py:229-234 `OscDevice.Input` | "Old profile reader's row type; kept until profile.py reads the file" | no use anywhere (program or tests): searched `OscDevice.Input`, `.Input(` | high | Dead |
| gremlin/osc.py:238-279 `OscDevice.reset/create/labels_of_type/find_address` | "Thin forms of the rows' API for older callers" | no program caller (osc_device_model holds `self._osc` but never calls these); tests use them (test_batch2_b4.py, test_final_04.py, main_shared_pieces_smoke.py) | high | Tests only. Move tests to `OscDevice().rows` |
| gremlin/osc_bulk.py:19-21, 142-144 | Monkey-patches `OscDeviceManagementModel.listenForCommand/cancelListen/_on_learned` with `setattr` at import (imported for its side effect from gremlin/ui/device_names.py:8); comment line 27: "old callers none" | runtime patching of a model class from another module | high (that it is a shim) | Layering leftover: fold into osc_device_model.py |
| gremlin/profile.py:969-970 `Library.remove_unused` | "release([action], recursive): kept for callers not moved yet" | no program caller (only `remove_unused_pictures` matches); tests 11 hits | high | Tests only |
| gremlin/profile.py:1543-1546 `Profile.bind_devices` | Empty method, "kept for the Backend, which calls it" | Backend does not call it; only `Profile.__init__` (:1541, when `bind`) calls it; tests 9 hits | high | Dead body; remove with the `bind` parameter |
| gremlin/profile.py:535-538, 615-616, 684, 1159 `_copied_from` "legacy copy -> original marks" + `add_action` | `clone_action(draft=True)` marks until "every pane uses draft()" (TODO(batch1)) | `_copied_from` still read in draft_held, release | medium | Transitional; finishes when the panes move to draft() |
| gremlin/plugin_manager.py:120-130 `create_instance` | "kept for callers without an input at hand (scripts, tools)" | no program caller in gremlin/, qml/, action_plugins/; 82 test hits | high | Tests only (user scripts may call it: check the scripting spec before removing) |
| gremlin/modules/module_file.py:139-144 `start_fresh` | "New callers use store.move_aside" | no program caller; 8 test hits | high | Tests only |
| gremlin/base_classes.py:605-613 `flush_pulses` + gremlin/code_runner.py:574-579 `_flush_pulses` | "kept for callers not moved yet"; TODO(batch1) pulse releases become run_scope timers | called by code_runner through `getattr` | medium | Transitional (TODO(batch1)) |
| gremlin/code_runner.py:305-311 module `__getattr__("_run_number")` | test/conftest.py reads `code_runner._run_number` | the program never reads it | high | Test-only shim inside program code (TODO(batch1)) |
| gremlin/ui/input_pairing.py:120-135 | "Public doors (GL-093). They call the underscore names, which stay for now." | `parse_guid`, `walk_actions`, `dest_labels_for_item` used by program; the underscore originals kept beside them | medium | Rename the originals, drop the wrappers |
| gremlin/config.py:580-604 + modules/calibration.py:141-165 + config.py:477 | Calibration in settings (the old store before module files): `init_calibration` never called, `set_calibration` only in tests (test_device_forget.py:60), `get_calibration` read by `_from_config` as a fallback ("older program data is used until then"); `purge_unused` never deletes the "calibration" section | searched callers | high | Legacy reader; nothing in the program writes this store any more |
| gremlin/profile.py:208-272 `_OLD_MACRO_DELAY` | "Older profiles always saved 0.05": a saved 0.05 is read as "follow Options" | profile reader | high | Legacy read rule; also means a user who picks 0.05 gets "Options" |
| gremlin/profile.py:1516-1519, 1576-1578 `readable_versions = (14, 15, 16)` | Opens version 14/15 profiles (their Logical Device / OSC rows are not read) | D-04-LD-NOLEGACY, AD7 | decided | Reader for older versions; spec decision |
| gremlin/logical_device.py:956-968, gremlin/validate.py:291, gremlin/ui/device_pack.py:1797-1799, 1988-1992 | A Logical Device reference without uid ("saved before permanent ids", "an older pack") found by type and number | D-04-LD-NOLEGACY | decided | Spec decision |
| gremlin/osc_device_file.py:70-71, 233-236 `_OLD_SERVER_KEYS` | Drops `output_host` / `output_port` from an old OSC file | AD7 | decided | Active clean-up of an old layout; could go now (unreleased) |
| gremlin/modules/claim.py:168, 176 | "Older files stored the bare scan code; that still counts" (`ident & 0xFFFF in keys`) | claim reader | medium | Legacy match rule |
| action_plugins/map_to_xbox/__init__.py:100-105 | "A missing property (older profiles) quietly takes the default"; also swallows every exception | reader | medium | Legacy tolerance |
| qml/rig_layers.js:19-63 `normalizeStacking` / `_legacyZ` | Old `zLayer` (1-4) and `pinned` keys: sorted once, pinned becomes locked | runs on every load | high | Legacy layout reader |
| qml/rig_layers.js:748-757, 910 | `_layerFilter`: a string filter state is "the old single-choice kind" (`legacy: true`) | reader | medium | Check whether any caller still passes a string |
| qml/rig_overlays.js:175-184 | `toggleLock` deletes old "pinned" | reader | high | Same as normalizeStacking |
| qml/rig_chips.js:43-52 `memberKind` | "Files saved before members carried a kind fall back to the group" | reader | medium | Legacy reader |
| qml/rig_leaders.js:57-86, 250; qml/VkbRigEditor.qml:425 `_legacyLeader` | A chip without `leaders` gets one built from its `from`/`to`/`spines` keys | used on every chip without `leaders` | low | May be the current single-leader form, not only old files: check before removing |
| qml/rig_draw.js:74-76 | `altOff` parameter "kept for the forwarder's signature", unused | reader | high | Tiny |
| qml/DialogDeviceMappingEditor.qml:514-516 | Save payload still sends `imageWidth: 1348, imageHeight: 1380`; hardware_profile.save pops them (they are `planes_once.OLD_PHOTO_KEYS`) and stamps PAGE_SIZE | always discarded | high | Dead keys in QML; the comment "page size is stamped by Save" is right, the keys are not needed |

---

## 3. One-time code still present (for to-do 109 / OT-5 removal)

All markers `ONE-TIME (tracker OT-n)`; lines checked with grep (pycache excluded).

### OT-1: move to device folders (03 S134)
- gremlin/modules/folders_move.py (702 lines, whole file; markers on every function, lines 4-682)
- joystick_gremlin.py:277-300 `_move_to_device_folders()` (called at :1005), :912-916 `folders_move.register_setting()`
- Unmarked but OT-1 only: the `GREMLIN_TESTS` check at joystick_gremlin.py:291.

### OT-2: map saved before the planes (photo becomes the bottom background picture)
- gremlin/modules/planes_once.py (97 lines, whole file)
- gremlin/library_swap.py:367-372
- gremlin/modules/store.py:1480 (`doc.get("image")` fallback), 1545-1557 (`planes_once` in set photo), 3007-3010 (import_file)
- gremlin/ui/device_pack.py:1025-1047 `_old_photo_in_zip` (called :1021), 1599-1604
- gremlin/ui/hardware_profile.py:23 (import), 63-74 `_planes_text` (called :2064, :2082), 2115-2117, 2133-2135
- Unmarked OT-2 code (mentions "OT-2" but has no `ONE-TIME` marker): gremlin/history_modules.py:27-40 (`photo`, `image`, `imageWidth`, `imageHeight` in MAP_KEYS); gremlin/modules/store.py:1472-1473 docstring, 1758 docstring + `_layer_refs` 1772-1774 (reads top-level `image`), 2764-2767 (pops the 4 keys); qml/DialogDeviceMappingEditor.qml:411-412 comment.

### OT-3: Button Map settings move to Device Mapping Editor names
- gremlin/device_map_settings_once.py (128 lines, whole file)
- joystick_gremlin.py:128 (import), :1001 `run_if_needed()`

### OT-4: library part id "button_map" -> "device_map"
- gremlin/library_part_id_once.py (171 lines, whole file)
- joystick_gremlin.py:133 (import), :1003 `run_if_needed()`

### OT-5: temporary click trace for the dead right-click (remove after the right-click hunt, to-do 109)
- gremlin/ui/click_trace.py (510 lines, whole file; one marker at :5)
- joystick_gremlin.py:1188-1192 (install)
- gremlin/trace.py: docstring :8-9; `MOUSE` :48-50; `_CFG_MOUSE` :90-91; `_mouse_on` :110; on_change docstring :174-175; option registration :212-214; `_load` :263-264, :276; `_save` :300-301; section :387-432 (`_run_hooks`, `mouse_ticked`, `set_mouse`, `mouse_on`, `click`); reset :491. Note `_run_hooks` (:389-395) duplicates the loop inside set_enabled (:162); it is only used by `set_mouse`, so it goes too.
- gremlin/ui/trace_model.py:35-36 ("Mouse" filter), 286-290 (Mouse row), 661-665 (`setMouse` slot)
- qml/LiveLogTrace.qml:447-449 (Mouse row tick)
- qml/RigPointerArea.qml:153-159 (`_ctRight`), 205-208, 262, 289, 299, 310
- theme/Gremlin/Menus/ContextMenu.qml:134-137 (onOpened), 214-217 (onClosed), 253-254, 293
- Config key left behind after removal: section/group of trace, name "mouse" (purge_unused removes it once unregistered).

Shared duplication across OT-1/3/4: `_REAL_DATA`, `_inside`, `REFUSED`, and the "test run" check are copied three times (device_map_settings_once.py:34-62, library_part_id_once.py:34-62, folders_move.py:115-145). All go with their files.

---

## 4. TODO / FIXME / XXX / HACK (program code; none of FIXME/XXX/HACK)

| Item (file:line) | Note | Status |
|---|---|---|
| qml/rig_commands.js:565-571 | TODO(SEL) "drop the fallback once ed.cutSelection lands" | **Stale**: `cutSelection` exists (VkbRigEditor.qml:888, rig_selection.js:441). The `else` copy+delete branch is dead |
| qml/rig_commands.js:867-869 | TODO(SEL) "the guard goes once the editor has lastCommandId" | **Stale**: `property string lastCommandId` exists (VkbRigEditor.qml:278); the guard never fires |
| qml/rig_menu.js:69-70 | same pattern without a TODO: `typeof cutSelection === "function"` checks | the check is always true now |
| gremlin/code_runner.py:306 | TODO(batch1) test reads `_run_number` | open (see section 2) |
| gremlin/code_runner.py:575 | TODO(batch1) pulse releases -> run_scope timers | open |
| gremlin/profile.py:535, 684, 1159 | TODO(batch1) legacy copy marks; editors move to create() | open |
| action_plugins/response_curve/__init__.py:271 | symmetry mode in the data class (with the commented call) | open, old (upstream) |
| action_plugins/condition/condition.py:154 | check condition type and comparator compatible | open, old (upstream) |
| gremlin/input_cache.py:113 | configurable button/axis counts | open, old (upstream) |
| gremlin/audio_player.py:28 | instance not reusable after playback | open, old (upstream) |
| theme/GremlinStyle/Dialog.qml:39 | QPlatformTheme::TitleBarFont | open, old (upstream style) |
| theme/GremlinStyle/ScrollBar.qml:22 | arrows | open, old (upstream style) |

---

## 5. Flags and settings that are always on or always off

Method: every `property bool X: true|false` in qml/, theme/, action_plugins/ checked for any assignment,
binding (`X:`), string use (setProperty / Python) or change handler anywhere. Python: module constants
`= True/False`, `if True/False`, environment switches.

| Item (file:line) | Value | Evidence | Confidence | Notes |
|---|---|---|---|---|
| `useSystemFocusVisuals` in qml/CompactSwitch.qml:22, theme/GremlinStyle/{Button,CheckBox,RadioButton,RoundButton,Slider,Switch,ToolButton}.qml, theme/Gremlin/Compact/{Button,CheckBox,RoundButton}.qml (11 files) | true | never set and never read (0 mentions outside the declarations) | high | Dead property (upstream style leftover) |
| qml/DialogDeviceMappingEditor.qml:154 `fittedOldPage` | false | never read or set | high | Dead property |
| qml/DynamicItemLoader.qml:21, 28 `autoReloadOnPathChange` / `forceReloadOnIdenticalPath` | true / false | never set; read once each (:61, :62) | high | Branches at :61-62 are fixed |
| qml/HorizontalDivider.qml:11 `dividerVisible` | true | never set (9 users) | high | Loader always active |
| qml/InputConfiguration.qml:18 `isOutput` | false | never set (one user, ActionPane.qml:315) | high | `editorLocked` reduces to `_lock.locked` |
| qml/InputConfiguration.qml:20, 30 `inlineMode` / `showAccent` | false / true | never set | high | The whole inline layout (lines 42-72: accent bar, padding branches) never runs |
| theme/Gremlin/Menus/ThemedMenuItem.qml:26 `inPalette` | true | never set; commands.js:192 tests `item.inPalette === false` | high | That branch never true for menu items |
| gremlin/ui/device_map_options.py:287-289 `PRINT_AREA_SHOWN_DEFAULT` / `PROPS_SHOWN_DEFAULT` | defaults | used as option defaults | n/a | Real settings, not flags |
| Test switches inside program code: device_reset.py:308-309 `_under_test` (PYTEST_CURRENT_TEST / pytest in sys.modules); joystick_gremlin.py:291 and the three *_once modules (GREMLIN_TESTS); update_model.py:202, 261 (GREMLIN_OFFLINE) | env | by design (test guards); GREMLIN_TESTS ones go with OT-1/3/4 | n/a | Listed for completeness |

Not done here: a full sweep of registered settings that the UI never changes (another agent has settings_scan.py).

---

## 6. Duplicate implementations of the same helper

Method: AST hash of every Python function body (docstring dropped, 3+ statements) and name-family searches
(path compare, inside, JSON read/write, GUID text, picture size); JS/QML: same function name in several files,
bodies hashed.

| Family | Copies (file:line) | Differences | Confidence |
|---|---|---|---|
| Picture size from file header | gremlin/modules/store.py:1484 `picture_size`; gremlin/ui/hardware_profile.py:1179 `imageAspect` (own QImageReader); hardware_profile.py:2501 (cached size with its own validity check); gremlin/ui/device_pack.py:1037-1042 (size from zip bytes, OT-2) | imageAspect skips `isValid()`; each re-implements the check | high |
| Same file / same path | library_copy.py:147 `_same_path`; library_profiles.py:136 `_same`; ui/backend.py:196 `_same_file`; ui/history_model.py:524 `_same_file`; ui/hidhide.py:699 `_same_path`; mode_manager.py:117-129 `_path_key`/`_same_key` | 6 versions with different case handling: resolve only (3), normcase only (hidhide), resolve+normcase (history), resolve+normcase+casefold (mode_manager); on OSError some compare text, backend returns False | high |
| Path inside folder | device_library.py:639; ui/history_model.py:593 (adds normcase); device_map_settings_once.py:48; library_part_id_once.py:48; modules/folders_move.py:126 | last 3 identical (AST) | high |
| Read a JSON object file | modules/store.py:301 `_read_json` (returns {}); modules/registry.py:203 `read_doc` (None, logs damage); modules/folders_move.py:697 `_read_json`; ui/device_pack.py:505 `_read_doc` (wraps store.read_path) | different empty value and logging | high |
| Write JSON safely | modules/module_file.py:135 `write_json`; modules/store.py:896 `write_json` (+History); input_tester_link.py:289 `_write_atomic` (own temp+replace); modules/folders_move.py:693 `_write_json`; config.py:30 (temp then swap) | 2 own atomic writers outside module_file | medium |
| Device GUID as text / key | modules/ids.py:21 `guid_key`, :32 `stored_guid_key`; modules/device_zip.py:128 `guid_text` (braced upper); modules/store.py:2320 `guid_text` (same name, different result: plain str); modules/store.py:222 `_norm`; modules/auto_mapping_tool.py:14 `_norm_guid`; input_tester/devices.py:65 `normalise_guid`; diagnostics.py:127 `_guid_text`; ui/input_pairing.py:20 and ui/device_map_labels.py:44 `_guid` (to UUID) | two public `guid_text` with different output | high |
| Test-run guard | device_reset.py:308 `_under_test`; refuses_* in the 3 *_once modules | same idea, different env var | medium |
| Connected device keys | ui/viewer_devices.py:23 = ui/xbox_viewer.py:24 `_connected_keys` (identical 12 statements); also `__init__` viewer_devices.py:65 = xbox_viewer.py:235 | identical | high |
| `_ints` | library_swap.py:134 = modules/claim.py:37 | identical | high |
| Layout groups | ui/hardware_layout.py:333 `_ensure` = ui/osc_layout.py:553; hardware_layout.py:390 = osc_layout.py:613 `move_group_before`; `ensure_group` hardware_layout.py:343 = keyboard_layout.py:273 = osc_layout.py:563 | identical | high |
| `save_if_dirty` | logical_device_file.py:182 = osc_device_file.py:629 | identical | high |
| `_short` | logical_device.py:49 = osc_rows.py:221 | identical | high |
| Logical reference in pickers | ui/script.py:173/184/192 = action_plugins/macro/__init__.py:219/230/238 (`_resolve_logical`, `_store_logical_uid`, `_shown_logical`) | identical | high |
| Mode type | osc_rows.py:98 `type_of_mode` = ui/osc_device_model.py:189 `_type_for_mode` | identical | high |
| Small identical pairs | mode_manager.py:163 = ui/live_debug.py:261 `_profile_running`; hidhide_watch.py:114 = trace_watch.py:88 `_on_change`; library_copy.py:64 = library_swap.py:45 `_result`; ui/pair_live.py:87 = xbox_viewer.py:331 `_flush`; device_library.py:2365 `_file_bytes` = history.py:866 `_size`; ui/control_layout.py:391 = hardware_layout.py:531; map_to_logical_device = map_to_vjoy `_set_axis_mode/_set_axis_scaling/_set_button_inverted`; trace.py:162 loop = trace.py:389 `_run_hooks` (OT-5) | identical | high |
| QML page helpers | qml/DeviceBindingsPage.qml, LogicalPage.qml, OscPage.qml: `_sameGroup` (:486/:363/:853) and `_groupAs` (:491/:368/:858) byte-identical; KeyboardPage.qml differs slightly; `_renameRow`, `_openHistory`, `_applyFind`, `_askDeleteGroup`, `_layoutMenuModel`, `toggleAppearance`, `requestCloseDisplay`, `setMode`, `onPaneLost` exist in all 4 pages with small differences | candidates for one shared JS file | high (identical ones) |
| QML live readers | `hwAxis`/`hwButton` in DeviceMapCard.qml:78, InputViewerCard.qml:43, XboxViewerCard.qml:31 (same body, different formatting) | same | high |
| Help JS | `_good` (4 files) and `_link` (3 files) in qml/help/*.js, identical | same | high |
| ButtonStateSelector | qml/ButtonStateSelector.qml and theme/Gremlin/Compact/ButtonStateSelector.qml (differ only in base type); every user found uses `Compact.ButtonStateSelector` | qml/ copy looks unused | medium |

Not counted: Qt property getter/setter boilerplate repeated inside one class (macro/__init__.py, script.py `_set_value` x3, pairing `data`/`_set_guid`), and the rig_*.js "forwarder" pattern in VkbRigEditor.qml (by design: 07 spec).

---

## 15 most important items

1. OT-5 click trace: 9 places in 8 files plus click_trace.py (510 lines); removal list in section 3 (to-do 109).
2. hardware_profile.py:408-430: 19 alias names; 6 have no caller at all, 4 tests only, 2 used by hardware_profile itself.
3. qml/rig_commands.js:565-571 and :867-869: TODO(SEL) guards are stale (cutSelection and lastCommandId exist); dead fallback branches.
4. Calibration in settings (config.py:580-604, calibration.py:141-165): a legacy store nothing writes; still read as a fallback and kept by purge_unused.
5. osc_bulk.py: monkey-patches OscDeviceManagementModel at import (setattr), a shim with a side-effect import.
6. OscDevice.Input (osc.py:229) unused; OscDevice thin API (osc.py:238-279) tests only.
7. OT-2 code without ONE-TIME markers: history_modules.py:27-40, store.py:1472, 1758-1774, 2764-2767 (will be missed when OT-2 is removed).
8. Six different "same path" helpers with different case rules (section 6), a real consistency risk on Windows.
9. Two public `guid_text` functions with different output (store.py:2320 vs device_zip.py:128), plus 8 other GUID normalizers.
10. Picture size read in 4 places with different validity checks (store.picture_size vs hardware_profile.imageAspect and :2501).
11. Legacy layout readers in the editor: rig_layers.js normalizeStacking/_legacyZ (zLayer, pinned), rig_overlays.js pinned, rig_chips.js memberKind fallback, rig_layers.js string filter.
12. profile.py `_OLD_MACRO_DELAY`: a saved 0.05 is always read as "follow Options" (a user's real 0.05 is lost).
13. InputConfiguration.qml inline mode (`inlineMode`, `showAccent`, `isOutput`) never switched on: ~30 lines never run.
14. useSystemFocusVisuals declared in 11 style files, never read; fittedOldPage never read.
15. Profile.bind_devices (empty), Library.remove_unused, plugin_manager.create_instance, module_file.start_fresh, code_runner `_run_number`: kept for callers that no longer exist in the program (tests only).
