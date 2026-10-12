# MAPCHK: full code map check (agent MAPCHK, 2026-10-12, 06:10 to 06:25)

Read-only. Repo HEAD 203a74dd. Nothing in the repo was changed (`claude/program-map/` included). Method: `audit/mapchk/mapchk.py` (pure file reading: Python `ast`, regex for QML/JS, `wc -l`-style counts) builds the inventory and compares it with sections 2-5 of `claude/program-map/01..10`; `own.py` lists files with a section 2 entry on two or more pages; every finding in the tables below was then checked by hand (grep / read at the cited line). Raw data: `audit/mapchk/data.json`, `own.txt`.

Scope: gremlin/, qml/ (with help/, tester/), theme/, action_plugins/, dill/, vigem/, **vjoy/** (found during the check; program code, see A1), joystick_gremlin.py, input_tester.py. 544 files, 182,122 lines.

Summary: (a) 1 program folder outside both guards (vjoy/, and theme/ is outside them too), about 20 major classes / functions with no mention on their page; (b) 27 stale names or file references, plus about 35 stale line references (Main.qml, backend.py, profile.py, joystick_gremlin.py, ui/device.py, ui/util.py, module_model.py); (c) 6 line counts off by more than 10 % (2 plugin folders, 1 inline duplicate count, theme and Help file counts), all section 2 single-file counts otherwise within 10 %; (d) 14 files described in full on two or three pages with no "owned by" / "part" marker.

## (a) Program code on no page, or major symbols not mentioned on their page

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| `vjoy/` (vjoy.py 964, vjoy_interface.py 115, __init__.py 3) | program folder outside the guards | Mapped on 06 section 2 line 26 (counts right), but `test_program_map_covers_files.py` `_program_units()` has no `vjoy/` unit and `test_spec_line.py` `_PROGRAM = ("gremlin/", "qml/", "action_plugins/", "dill/", "vigem/")` leaves it out; `.claude/CLAUDE.md` change-control list also omits it. Imported by `gremlin/modules/output.py:460-498` (`from vjoy import vjoy`). | high | A commit changing vjoy/ needs no `Spec:` line and the map guard would not notice the file going off the map. |
| `theme/` (66 QML/JS files, 5,150 lines) | program folder outside the guards | Covered on 09 line 65 only by folder names; neither guard test lists `theme/`. Brief counts theme/ as program code. | high | Same consequence as vjoy/. |
| `vjoy/vjoy.py` `VJoy` (403 lines), `vjoy/vjoy_interface.py` `VJoyInterface` | class not on page | 06 line 26 names only `VJoyProxy`. | high | Main vJoy device class. |
| `gremlin/signal.py` `Signal` (70) | class not on page | Owners 01, 09; class name absent (the `signal` singleton is mentioned). | medium | The program-wide signal hub. |
| `gremlin/osc_feedback.py` `OscFeedback` (347) | class not on page | Owners 01, 09; not named. | high | Biggest OSC runtime class without a mention. |
| `gremlin/ui/trace_model.py` `TraceView` (341), `TraceTree` (177) | classes not on page | Owner 01; not named. | high | Control tracing UI models. |
| `gremlin/ui/output_modules.py` `OutputModuleDevices` (330) | class not on page | Owners 03, 05; the page describes behaviour only. | high | |
| `gremlin/ui/click_trace.py` `ClickTrace` (190) | class not on page | Owners 01, 07 (one-time OT-5 code). | medium | |
| `gremlin/spline.py` `CubicBezierSpline`, `CubicSpline`, `AbstractCurve`, `PiecewiseLinear` | classes not on page | Owner 05; none named. | medium | Response Curve maths. |
| `gremlin/ui/xbox_viewer.py` `XboxLiveThrottle` (132); `XboxMappedButtonModel` / `XboxMappedHatModel` | class not on page / shortened | 06 line 38 writes `ButtonModel` / `HatModel` (no such names). | medium | |
| `gremlin/fsm.py` `FiniteStateMachine` (82) | class not on page | Owner 09. | medium | |
| `gremlin/ui/profile.py` `LabelValueSelectionModel` (80), `StartupModeModel`, `VJoyInputOrOutputModel`, `OutputVJoyListModel`, `OutputVJoyInitialValuesModel` | classes not on page | Owners 04, 05, 06. | medium | |
| `gremlin/ui/module_model.py` `ModuleRow` (60) | class not on page | Owners 02, 03, 07, 09. | low | |
| `gremlin/unknown_action.py` `UnknownActionData` (88) | class not on page | Owner 05. | low | |
| `gremlin/user_script.py` `LogicalDeviceVariable`, `PhysicalInputVariable`, `ScriptVariableRegistry` | classes not on page | Owners 03, 04, 06, 09. | medium | Script API objects. |
| `action_plugins/condition/condition.py` `AbstractCondition`, `JoystickCondition`, `VJoyCondition`, `LogicalDeviceCondition`, `KeyboardCondition` | classes not on page | Owners 05, 09. | low | |
| `gremlin/input_tester_link.py` `build_expected()` (95 lines) | function not on page | Owner 02. | medium | |
| `gremlin/modules/store.py` `prepare_imported_doc()` (83 lines) | function not on page | Named on no page at all. | medium | |
| `gremlin/ui/osc_layout.py` `set_field()` (69 lines) | function not on page | Owner 09. | low | |
| Action plugin `*Data` / `*Model` / `*Functor` classes (about 190) | convention | Page 05 line 52-59 describes the data / model / functor pattern per folder instead of naming classes. | n/a | Not counted as gaps; full list at the end. |

## (b) Stale map entries (names, files or line numbers that no longer exist)

| Item (page:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| 02:157, 02:158 `DeviceResetModel` | stale class name | Class is `ResetDevicesModel` (`gremlin/ui/device_reset_model.py:112`). | high | |
| 02:136 `ModuleModel` | stale class name | No class of that name; nearest `ModuleListModel` / `CalibrationModuleModel`. | high | |
| 03:13 `test_no_builtin_lists` | name form | Test file `test/unit/test_no_builtin_lists.py` exists; fine. | n/a | Not stale (listed to clear the raw hit). |
| 03:16 `device_pack._today_layout` | stale function | Not in program code (`_planes_text`, `_old_photo_in_zip` exist). | high | Also on 07 section 2? (only 03 found). |
| 03:127 `autoMap` | stale handler | Not in program code. | medium | Card menu now names `autoMappingTool`. |
| 03:211 `_targets_timer` | stale attribute | Not in program code. | high | |
| 03:231, 07:195, 08:136 `resolve_module_slug`; 07:195 `registry._binding_store` | stale functions | Removed 2026-10-11 (03 line 18 says so); found only in tests/tools. | high | Section 5 rows of 07 and 08 still list them as calls. |
| 04:96 `newActionSequence` 688, `deleteActionSequnce` 695, `dropAction` 710 | stale slot | `newActionSequence` only in tests/tools. | medium | |
| 05:100 `_remove_unused` | stale function | Not in program code (`remove_unused_pictures` only). | high | |
| 05:141, 06:116, 06:117 `MouseController`, `.start`, `.stop` | stale class | Now `MouseMotionManager` (`gremlin/sendinput.py:208`). | high | 06 section 2 line 29 already says `MouseMotionManager`. |
| 06:29 `release_held_buttons` | stale function | Not in program code; `_held_buttons` and `release_held` exist elsewhere. | high | |
| 06:41 `xboxAvailable` | stale property | Not in program code. | high | |
| 06:49, 06:148 `logicalUndoBar`; 06:49, 06:143 `logicalFind` | stale ids | Not in program code (`logicalFind` only in tests). | high | |
| 06:91 `merge_profile_rows`, old `LogicalDeviceManagementModel` | stale names | Only in tests/tools (version 14 converter gone, D-04 LD14). | high | |
| 06:116 `_next_run_number` | stale function | Only in tests/tools. | high | |
| 07:29 `_tools`; 07:31 `shortDest()` ("Dead `shortDest()` left") | stale | Neither exists any more; the "dead left" note is out of date. | high | |
| 08:24 `_rewrite_images` | stale function | Not in program code. | high | |
| 08:113 `outputs_problem(zf)` | stale function | Not in program code (`wires_problem` exists in `pack_checks.py:40`). | high | |
| 09:14 `live_all`; 09:28 `OscInputIdentifier`, `_parse_import_line`; 09:39 `uidOf`; 09:22 `oscFeedbackLoader`, `oscSectionsScroll`; 09:176 `_release_button` | stale names | None in program code. | high | OSC rewrite leftovers. |
| 10:96 `device_pack._zip_readable`, `_from_gmap` | stale functions | Not in program code (`device_zip.read_gmap` exists). | high | |
| 04:49 `profile.logical_migration_note` | stale | Only in tests/tools. | medium | |
| 05:262 `test_help_guide` | name form | `test/unit/test_help_guide.py` exists; fine. | n/a | |
| 09:72 "`qml/help/` (10 chapter files)" | stale count | 11 files (01 line 67 says 11). | high | |
| 09:65 "`theme/GremlinStyle/` (33 control files + `impl/`) ... 64 QML/JS files, about 4,900 lines" | stale counts | 32 control files + 3 in impl/; 66 QML/JS files, 5,150 lines. | high | |
| 03:39 `gremlin/ui/device.py` "lines 1076-1641 only" | stale line range | File has 1284 lines; `AxisCalibration` is at 674. | high | |
| 02:75 `ui/device.py:1400` | stale line ref | Beyond the end (1284 lines). | high | |
| 08:33, 08:92 `LogicalPage.qml:1215` | stale line ref | File has 665 lines. | high | |
| 08 section 2 `gremlin/profile.py` "lines 904-927, 1126-1180" (`to_xml`, `record_save`, `put_input`) | stale line range | `Profile.to_xml` 1666, `record_save` 1695, `put_input` 1885. | high | |
| 08 section 2 `gremlin/modules/module_file.py` "lines 64-100, 107" | stale line range | `write_text` 117, `start_fresh` 139. | high | |
| 02:32 `gremlin/ui/util.py` "lines 50-292, 294-435"; 05:27 "294-435" | stale line range | `InputListenerModel` 59, `MacroRecorder` 355, `ProcessListModel` 571. | high | |
| 05:15 `gremlin/profile.py` `Profile` 844-1326, `InputItem` 1328, `InputItemBinding` 1415 | stale line refs | Now 1513, 2029, 2156. | high | |
| 03:32 `module_model.py` `loadDevice` ~1954, `saveClaim` ~2336 | stale line refs | Now 2419, 2844. | high | |
| 01:14 `release_qt` (:1264); 02:37 `shutdown_cleanup` 240, `_no_hooks_offscreen` 880; 06:21 `shutdown_cleanup` 240-285; 01:191 `joystick_gremlin.py:900` | stale line refs | `release_qt` 1326, `shutdown_cleanup` 371, `_no_hooks_offscreen` 260 (called 996, 1245), `configChanged.connect` 1018. | high | |
| 09:235 `joystick_gremlin.py` 20-42, 63-69, 1012-1024 vs 09:68 22-45, 105-106 | stale / inconsistent | `QT_QUICK_CONTROLS_STYLE` is at 106; section 4 still has the older numbers. | high | |
| 04:23 `get_profile_with_regex` 516-551 | stale line ref | Now 645. | high | |
| 06:54 `gremlin/ui/backend.py` `gremlinPaused` 409, `gremlinActive` 413, `toggleActiveState` 417, `activate_gremlin` 420, `_device_change` 305, `_active_process_changed_cb` 357 | stale line refs | Now 561, 565, 569, 572, 79, 499. | high | 09:69 `backend.py` 489-495 (`useDarkMode`, `uiScale`) now 627-631. |
| `qml/Main.qml` line refs: 03:52 `openConfigureModule` 387-450 (now 867), card handlers ~1414-1462 (now ~2228); 04:29 `guardUnsavedChanges` 706 (1331), `saveProfileChecked` 528 (1058), `onClosing` 1366 (2152); 06:56 Run/Stop 1053-1059 (now ~1740), `deactivateThenQuit` 647 (1268); 01:143 `:1300`, 01:144/04:77 `requestNewProfile` `:499` (1029), 04:79 `loadRecent` `:599` (1204), 01:160 `Shortcut` `:994` (1677), 01:180 / 04:87 mode box ~1772 / `:1162` (`_modeSelector` 1846), 01:191-196 `:1325-1347` (`onConfigChanged` 2106), 06:104 `:1059`, 08:126 `:1432` (2228), 09:69 / 09:236 100-103, 1345-1351 | stale line refs | Checked by grep at HEAD; nearly every Main.qml number in sections 2-5 is out of date (Main.qml grew to 2634 lines). | high | Suggest dropping Main.qml line numbers in favour of function names. |
| 03:32 inline "(2678 lines.)" | stale duplicate count | Same bullet opens with 2969 (correct). | high | |

Raw-hit false positives cleared by hand: `spdlog.txt`, `ifaddr` (a dependency), `evo_r.json`, `foreign`, `device_export` (old name in a "was" sentence), `NOT_SWAPPABLE` ("replaces the old" sentence), `test_*` names whose files exist, `KeyboardManagerModel` ("Replaces"), `UIState.themeRevision` / `bumpThemeRevision` (removed sentence), `sideState` etc. on the struck-through ToolDock line, `import_module_file` / `undo_last_import` ("were" sentence), value hits (`SLOW_KEY_MS` 200, `KEEP_DAYS` 90 and so on).

## (c) Line counts off by more than 10 %

Every single-file count in sections 2 (350 compared) is within 10 % except the false hits (page numbers in brackets). Folder and aggregate counts checked by hand:

| Item (page:line) | Map | Actual | Off | Notes |
|---|---|---|---|---|
| 05:88 `action_plugins/run_command/` | 295 | 339 | +15 % | |
| 05:85 `action_plugins/play_sound/` | 287 | 319 | +11 % | |
| 03:32 `module_model.py` inline "(2678 lines.)" | 2678 | 2969 | +11 % | header count 2969 is right |
| 09:65 theme "64 QML/JS files, about 4,900 lines" | 64 / 4,900 | 66 / 5,150 | +3 % files, +5 % lines | under 10 % but file counts wrong |
| 09:72 `qml/help/` "10 chapter files" | 10 | 11 | +10 % | |
| 05:68 `map_to_mouse/` 693, 05:64 `map_to_vjoy/` 499 (`__init__.py` 407 → 413) | | 750, 538 | +8 % | under 10 %, listed for the next pass |

Also: 04:25 `joystick_gremlin.py` 1363 vs 1367 (01:14 has 1367; 4 lines from 203a74dd, under 10 %). 07:12 `hardware_profile.py` 2512 vs 2515 (under 10 %).

## (d) Files described on two or more pages without a clear owner

Files with a full section 2 entry on two or more pages where neither entry says "part", "owned by page NN", "mapped on page NN" or gives a line range:

| File | Pages (section 2 line) | Conflict | Suggested owner |
|---|---|---|---|
| `gremlin/audio_player.py` | 06:31, 09:53 | both full entries | 09 (sound), 06 "part" |
| `gremlin/tts.py` | 06:32, 09:54 | both full entries | 09, 06 "part" |
| `gremlin/ui/system_tray.py` | 01:38, 06:55, 09:58 | three full entries | 09 (tray) or 01; others "part" |
| `gremlin/ui/tray_memory.py` | 01:39, 09:59 | both full | one owner |
| `gremlin/ui/ui_scale_option.py` | 01:29, 09:66 | both full | one owner |
| `gremlin/ui/vjoy_status.py` | 01:46, 06:41 | both full | one owner |
| `gremlin/modules/output.py` | 03:25, 06:24 (05:33 says "owned by page 03/06") | both full; 05 names two owners | 03 (modules), 06 "part" |
| `gremlin/device_aliases.py` | 02:34, 10:46 | both full | 02, 10 "part" |
| `gremlin/history_modules.py` | 07:23, 08:14 | 07 has no "page 08" marker | 08 |
| `gremlin/modules/auto_mapping_tool.py` | 03:27, 08:28 | both full | one owner |
| `gremlin/process_monitor.py` | 02:25, 04:24 | both full | one owner |
| `gremlin/profile.py` | 04:12, 05:15 (full count, no "part"), 08 (lines) | 04 and 05 both full | 04, 05 "part" |
| `gremlin/ui/xbox_viewer.py`, `qml/DialogXboxViewer.qml`, `qml/XboxViewerCard.qml` | 02:46-47, 06:38-40 | both full | one owner |
| `qml/OptionProfileAutoLoading.qml` | 02:49, 04:35 | both full | 04 |
| `gremlin/ui/util.py` | 02:32 (lines 50-292, 294-435), 05:27 (294-435) | both claim `MacroRecorder`'s lines | 02 or 05, and the ranges are stale |

Minor (one page owns, others list their part without saying "part"): `qml/Main.qml` (03:52, 04:29, 06:56, 09:60 beside 01:50), `qml/main_commands.js` (03:54, 04:30 beside 01:52), `joystick_gremlin.py` (04:25, 06:21, 09:68 beside 01:14), `gremlin/config.py` (04:23 beside 01:15), `gremlin/ui/backend.py` (04:17 full; 06:54 part; 09:69 lines), `gremlin/base_classes.py` (04:13 full; 06:17 part), `gremlin/user_script.py`, `gremlin/mode_manager.py` (04 full; 06 part).


## Inventory (every program file, HEAD 203a74dd)

Pages: every page whose sections 2-5 name the file (section 2 pages first, with `*`); `-` = on no page by path; theme/ files are covered on page 09 by folder (`theme/GremlinStyle/`, `theme/Gremlin/Base`, `/Compact`, `/Menus`) and plugin folders on page 05 by folder. Top symbols: public top-level classes then functions (Python); root type, signals and public functions (QML/JS); at most 5.

| File | Lines | Pages | Top symbols |
|---|---|---|---|
| gremlin/__init__.py | 3 | 05* 06* 09* |  |
| gremlin/action_analysis.py | 183 | 05* | action_sequence_feedback() |
| gremlin/action_state.py | 132 | 05* 06* 09* | register(), clear(), read(), read_text(), paused_state() (+1) |
| gremlin/audio_player.py | 222 | 06* 09* 05 | AudioSample, AudioPlayer |
| gremlin/auto_mapping_tool.py | 316 | 03* 08* | AutoMappingToolOptions, AutoMappingTool |
| gremlin/axis_names.py | 11 | 03* |  |
| gremlin/axis_shaping.py | 45 | 09* | deadzone(), shape() |
| gremlin/base_classes.py | 742 | 04* 05* 06* 09* | UserFeedback, Value, AbstractActionData, AbstractFunctor, building_for() (+3) |
| gremlin/clock.py | 31 | 01* 06* | now(), monotonic(), sleep() |
| gremlin/code_runner.py | 722 | 01* 05* 06* 09* 02 | VirtualButton, VirtualAxisButton, VirtualHatButton, VirtualButtonFunctor, CallbackObject (+2) |
| gremlin/common.py | 90 | 09* | SingletonDecorator, SingletonMetaclass, input_to_ui_string() |
| gremlin/config.py | 674 | 01* 04* 08* 02 | Configuration, use(), announce_damaged_settings(), settings_history_title(), get_profile() (+1) |
| gremlin/deferred_write.py | 121 | 01* | schedule(), pending(), flush(), flush_all() |
| gremlin/device_aliases.py | 316 | 02* 10* | display_name(), watch_names(), notify_names(), set_alias(), forget() |
| gremlin/device_forget.py | 133 | 10* | forget_device() |
| gremlin/device_helpers.py | 145 | 02* | JoystickInputSignificant, AxisChangeSignificanceTracker |
| gremlin/device_initialization.py | 655 | 02* | stored_twins(), device_name(), shown_name(), information_devices(), joystick_devices_initialization() (+8) |
| gremlin/device_library.py | 2589 | 10* | LibraryDamaged, folder(), history_text(), restore_history(), settings() (+38) |
| gremlin/device_map_settings_once.py | 128 | 07* | refuses_real_settings(), new_key(), plan(), run(), run_if_needed() |
| gremlin/device_paths.py | 173 | 02* | instance_id(), hid_instance() |
| gremlin/device_reset.py | 454 | 02* | Cancelled, RealRunnerBlocked, ResetDevice, ResetResult, set_runner() (+5) |
| gremlin/device_reset_log.py | 90 | 02* | outcome_text(), report(), report_back() |
| gremlin/diagnostics.py | 351 | 01* 02 | Plan, user_names(), scrub(), scrub_name(), default_name() (+7) |
| gremlin/edits.py | 52 | 04* | EditNoted, note_edit(), edit_count() |
| gremlin/error.py | 103 | 09* 01 | GremlinError, ProfileError, KeyboardError, MouseError, MissingImplementationError (+5) |
| gremlin/error_report.py | 76 | 01* | thread_exception_hook(), pass_on(), enable_crash_log(), install() |
| gremlin/event_handler.py | 970 | 01* 02* 06* 09* 05 | Event, EventListener, EventHandler, trace_kind(), trace_ticked() |
| gremlin/event_helpers.py | 288 | 06* | ModeMatch, ReleaseMode, ButtonReleaseEntry, RegistryKey, ButtonReleaseActions (+1) |
| gremlin/fsm.py | 111 | 09* | Transition, FiniteStateMachine |
| gremlin/gc_guard.py | 115 | 01* | collect(), installed(), install(), uninstall() |
| gremlin/hidhide_driver.py | 1174 | 01* 02* | quiet, GUID, SP_DEVINFO_DATA, SP_DEVICE_INTERFACE_DATA, HIDD_ATTRIBUTES (+22) |
| gremlin/hidhide_watch.py | 487 | 01* 02* | running(), last_state(), start(), stop(), install() (+3) |
| gremlin/history.py | 958 | 08* 01 | folder(), files_folder(), record(), write_now(), later() (+21) |
| gremlin/history_modules.py | 310 | 07* 08* | is_module_file(), text_before(), before_change(), note_write(), delete_before() (+3) |
| gremlin/history_profile.py | 258 | 08* 09* | pack_text(), unpack_text(), changes(), record_save() |
| gremlin/input_cache.py | 671 | 02* 09* | DeviceMapping, DeviceDatabase, JoystickWrapper, OscState, Joystick (+3) |
| gremlin/input_monitor.py | 163 | 01* 02* | enabled(), set_enabled(), clear(), version(), entries() (+5) |
| gremlin/input_refresh.py | 55 | 02* | RefreshPhysicalInputs |
| gremlin/input_tester/__init__.py | 11 | 02* 05* 06* 09* |  |
| gremlin/input_tester/compare.py | 610 | 02* | Row, Verdict, load_expected(), read_expected(), steam_state() (+7) |
| gremlin/input_tester/devices.py | 587 | 02* | SeenDevice, LiveValues, OpenResult, XINPUT_GAMEPAD, XINPUT_STATE (+15) |
| gremlin/input_tester/log.py | 101 | 02* | TesterLog, stamp(), log_path() |
| gremlin/input_tester/logfiles.py | 158 | 02* | LogSource, Tail, Follower, sources(), read_tail() (+5) |
| gremlin/input_tester/model.py | 1076 | 02* | InputTesterModel, restart_args(), set_starter(), set_quitter() |
| gremlin/input_tester/result.py | 62 | 02* | result_data(), write_result() |
| gremlin/input_tester/steam.py | 61 | 02* | process_names(), steam_running() |
| gremlin/input_tester_link.py | 611 | 02* | InputTesterLink, tester_path(), gremlin_dir(), tester_dir(), expected_file() (+16) |
| gremlin/keyboard.py | 441 | 02* 05* 06* | Key, send_key_down(), send_key_up(), is_down_in_windows(), key_from_name() (+2) |
| gremlin/library_copy.py | 1423 | 04* 09* 10* | plan_copy(), copy(), restore_to_stick(), plan_output(), change_output() (+3) |
| gremlin/library_part_id_once.py | 171 | 10* | refuses_real_library(), migrate(), run(), run_if_needed() |
| gremlin/library_profiles.py | 517 | 10* | Batch, responsive(), background(), is_open_path(), open_profile_row() (+4) |
| gremlin/library_swap.py | 559 | 04* 10* | plan_swap(), swap() |
| gremlin/library_undo.py | 197 | 10* | Steps, started(), recorded_since(), put_back() |
| gremlin/log_feed.py | 165 | 01* | Entry, last_seq(), entries_after(), active(), start() (+6) |
| gremlin/log_once.py | 36 | 01* | log_once(), reset() |
| gremlin/logical_device.py | 973 | 06* 04 | LogicalRows, LogicalDevice, notify_rows(), resolve_logical_reference() |
| gremlin/logical_device_file.py | 187 | 06* 10* 04 | path(), read_layout(), load(), save(), save_if_dirty() |
| gremlin/logical_loop.py | 146 | 06* | chain_of(), continuing(), guarded(), reset() |
| gremlin/macro.py | 1461 | 05* 06* 09* 02 | MacroManager, Macro, AbstractAction, JoystickAction, KeyAction (+10) |
| gremlin/macro_raw.py | 68 | 05* | RawMacroStep |
| gremlin/mode_manager.py | 429 | 04* 06* 02 05 | Mode, ModeSequence, ModeManager, flush_last_modes(), resolve_start_mode() |
| gremlin/modules/__init__.py | 6 | 03* 05* 06* 09* |  |
| gremlin/modules/auto_mapping_tool.py | 147 | 03* 08* 06 | input_modules(), output_modules(), merge_claim_into_output() |
| gremlin/modules/calibration.py | 207 | 03* 02 09 | curve_problem(), as_tuple(), module_for_slug(), values_for_device(), values_for_module() (+2) |
| gremlin/modules/claim.py | 181 | 03* 06 | empty_claim(), read_claim(), kind_of(), type_of(), claim_ids() (+6) |
| gremlin/modules/device_class.py | 246 | 03* | DeviceClass, device_kind(), class_of_kind(), device_class(), is_internal() (+9) |
| gremlin/modules/device_zip.py | 819 | 07* 08* 10 | replace_strings(), guid_text(), guid_like(), only_modes(), build_gmap() (+6) |
| gremlin/modules/folders_move.py | 702 | 01* 03* | MoveError, register_setting(), old_bindings(), is_done(), refuses_real_data() (+2) |
| gremlin/modules/gate.py | 74 | 03* 02 06 | should_forward(), status_last_from_hid(), dest_last_change() |
| gremlin/modules/hardware.py | 65 | 02* 03* | device_info(), device_connected(), plugged_in(), devices() |
| gremlin/modules/ids.py | 36 | 03* | guid_key(), stored_guid_key() |
| gremlin/modules/inputs.py | 135 | 03* 06 | ScriptJoystick, ScriptKeyboard, axis_value(), button_pressed(), hat_direction() (+1) |
| gremlin/modules/module_file.py | 170 | 03* 08* 01 | ModuleFileDamaged, damage_reason(), load_for_update(), write_bytes(), encode() (+5) |
| gremlin/modules/output.py | 1360 | 01* 03* 05* 06* 02 | ScriptVJoy, refresh(), watch_cant_send(), notify_cant_send(), vjoy_claim() (+53) |
| gremlin/modules/pack_checks.py | 79 | 08* | too_big(), wires_problem() |
| gremlin/modules/planes_once.py | 97 | 03* 07* | old_photo_to_layer() |
| gremlin/modules/registry.py | 335 | 03* 10* 02 06 | Module, plain_slug(), is_gremlin_xbox_name(), is_output_name(), module_direction() (+14) |
| gremlin/modules/runtime.py | 218 | 02* 03* 09* 04 06 | InputModuleRuntime, always_forwarded() |
| gremlin/modules/store.py | 3077 | 03* 07* 08* 09* 10* 02 05 06 | folder(), card_key(), guid_filter(), id_key(), folder_name_for() (+112) |
| gremlin/modules/wiring.py | 141 | 03* 06 | vjoy_dest(), xbox_dest(), dest_label() |
| gremlin/notice.py | 97 | 01* | NoticeTimer, BurstNotice |
| gremlin/osc.py | 1812 | 01* 09* | OscDevice, OscListener, OscRuntime, local_ipv4_addresses(), sender_allowed() (+18) |
| gremlin/osc_bulk.py | 153 | 01* 09* | OscBulkCapture, model_listen_for_command(), start_bulk(), bulk_skipped(), model_cancel_listen() (+1) |
| gremlin/osc_companion_check.py | 171 | 09* | OscCompanionCheck, check() |
| gremlin/osc_device_file.py | 672 | 01* 09* 04 | path(), clean_server(), sender_entry(), clean_senders(), new_id() (+15) |
| gremlin/osc_discovery.py | 350 | 09* | available(), service_name(), set_announce(), set_find(), found() (+3) |
| gremlin/osc_feedback.py | 716 | 01* 09* | OscFeedback, settings(), source_text(), instance(), start() (+3) |
| gremlin/osc_output.py | 392 | 01* 09* | note_sender(), last_sender(), note_received_type(), received_type(), reset() (+6) |
| gremlin/osc_pattern.py | 151 | 09* | is_pattern(), check(), compile(), matches() |
| gremlin/osc_persist.py | 104 | 07* 09* | osc_rows(), resolve_osc_reference(), osc_label(), osc_address(), osc_addresses() (+1) |
| gremlin/osc_rows.py | 545 | 09* | OscRow, OscRows, type_of_mode(), check_address(), check_settings() |
| gremlin/osc_tosc.py | 274 | 01* 09* | ToscRefused, parse() |
| gremlin/osc_traffic.py | 163 | 01* 09* | note(), add_listener(), remove_listener(), recent(), clear() |
| gremlin/plugin_manager.py | 312 | 05* | PluginManager, core_qml_names() |
| gremlin/process_monitor.py | 135 | 02* 04* | ProcessMonitor, list_current_processes() |
| gremlin/process_paths.py | 215 | 02* | running_images(), running_programs(), game_path_problems(), old_tester_entry(), tester_path_problem() (+2) |
| gremlin/profile.py | 2781 | 04* 05* 08* 09* 06 | AbstractVirtualButton, VirtualAxisButton, VirtualHatButton, Settings, DraftOutdated (+16) |
| gremlin/profile_recovery.py | 200 | 04* | ProfileRecovery, default_folder(), profile_key() |
| gremlin/qt_log.py | 153 | 01* | install() |
| gremlin/run_scope.py | 438 | 06* | Stage, Handle, Timer, number(), running() (+15) |
| gremlin/sendinput.py | 492 | 06* 05 | Vector2, MotionSource, ConstantVelocity, IncreasingVelocity, MouseMotionManager (+4) |
| gremlin/shared_state.py | 102 | 06* | suspend_input_highlighting(), hold_input_highlighting(), release_input_highlighting(), set_suspend_input_highlighting(), runtime_active() (+1) |
| gremlin/signal.py | 94 | 01* 09 | Signal, display_error() |
| gremlin/spline.py | 562 | 05* | AbstractCurve, PiecewiseLinear, CubicSpline, CubicBezierSpline |
| gremlin/swap_devices.py | 265 | 04* 09* | SameDevice, ProfileDeviceInfo, SwapDevicesResult, not_swappable(), get_profile_devices() (+3) |
| gremlin/text_diff.py | 124 | 08* | word_spans(), rows(), blocks() |
| gremlin/threads.py | 193 | 01* 06* | MainTimer, start(), timer(), main_timer(), running() (+1) |
| gremlin/trace.py | 1158 | 01* 02* 06 09 | enabled(), set_enabled(), since(), on_change(), ticked() (+46) |
| gremlin/trace_watch.py | 266 | 01* 06* | running(), start(), stop(), install(), check() |
| gremlin/tree.py | 218 | 04* | TreeNode |
| gremlin/tts.py | 242 | 06* 09* 05 | TTSQueueMode, TTSRequest, TTSManager |
| gremlin/types.py | 750 | 09* | InputType, VjoyInput, AxisNames, AxisButtonDirection, MouseButton (+13) |
| gremlin/ui/__init__.py | 3 | 05* 06* 09* |  |
| gremlin/ui/action_model.py | 475 | 05* | SequenceIndex, ActionModel, input_name() |
| gremlin/ui/auto_mapping_tool_modules.py | 90 | 03* 08* | AutoMappingToolInputModel, AutoMappingToolOutputModel |
| gremlin/ui/backend.py | 989 | 02* 04* 05* 06* 09* 01 | UIState, Backend |
| gremlin/ui/binding_catalog.py | 254 | 05* | EditLock, action_name(), type_filter_names(), summarize_action(), collect_leaves() (+7) |
| gremlin/ui/click_trace.py | 510 | 01* 07* | ClickTrace, editor_window(), item_chain(), hits(), editor_rects() (+3) |
| gremlin/ui/control_layout.py | 1436 | 05* 06* 09* 03 | LayoutItem, ControlLayoutModel, kind_word(), parse_parent(), parent_key() (+4) |
| gremlin/ui/debug_mode.py | 155 | 01* | DebugMode, is_active(), install(), hidden_frames() |
| gremlin/ui/device.py | 1284 | 02* 03* 05* 06* | InputIdentifier, DeviceListModel, Device, LogicalDeviceSelectorModel, DeviceAxisSeries (+1) |
| gremlin/ui/device_library_model.py | 1568 | 10* | DeviceLibraryModel, size_text(), inputs_text(), also_move_text() |
| gremlin/ui/device_map_labels.py | 179 | 07* | mode_order(), action_text(), action_labels() |
| gremlin/ui/device_map_options.py | 869 | 07* | DeviceMapLibraryOption, DeviceMapOptions, DeviceMapSpaceKey, key_of(), register() (+21) |
| gremlin/ui/device_names.py | 63 | 02* 10* | DeviceNames, shown_name() |
| gremlin/ui/device_pack.py | 3234 | 03* 08* 09* 06 | size_text(), module_text(), pack_modes(), export_refusal(), pack_devices() (+19) |
| gremlin/ui/device_photo.py | 347 | 01* 07* | DevicePhotoMaker, want(), white_path(), matte() |
| gremlin/ui/device_reset_model.py | 357 | 02* | ResetDevicesModel, game_line(), profile_device_names() |
| gremlin/ui/diagnostics.py | 106 | 01* | Diagnostics |
| gremlin/ui/folder_memory.py | 120 | 01* 10 | FolderMemory, ensure(), last_folder(), remember() |
| gremlin/ui/hardware_layout.py | 873 | 03* 05* 09* | HardwareLayoutItem, HardwareLayoutStore, HardwareLayoutModel |
| gremlin/ui/hardware_profile.py | 2515 | 03* 07* 08* 10* | HardwareProfile, persist_log(), exact_page(), save_area(), export_failure() (+8) |
| gremlin/ui/hidhide.py | 1336 | 02* | HidHideModel, forget_devices(), apply_on_start(), apply_saved_list() |
| gremlin/ui/highlight_option.py | 84 | 01* | HighlightSpeedModel, normalize_speed(), ensure_registered() |
| gremlin/ui/history_model.py | 1259 | 08* 10* 01 | HistoryModel, describe(), restore() |
| gremlin/ui/input_pairing.py | 326 | 07* | MappedAxisModel, MappedButtonModel, MappedHatModel, parse_guid(), walk_actions() (+6) |
| gremlin/ui/keyboard_layout.py | 683 | 05* 09* 03 | KeyItem, KeyboardLayoutStore, KeyboardLayoutModel, key_name(), key_row() (+2) |
| gremlin/ui/leave_text.py | 188 | 01* | LeaveTextFilter, install() |
| gremlin/ui/live_debug.py | 948 | 01* | LiveLog, DebugLog, InputMonitor, log_path(), start() (+7) |
| gremlin/ui/live_follow.py | 71 | 05* | LiveInputs, may_follow(), follows() |
| gremlin/ui/live_input.py | 446 | 03* | DeviceLiveState |
| gremlin/ui/log_option.py | 132 | 01* | LogLevelModel, normalize_level(), apply_log_level() |
| gremlin/ui/logical_layout.py | 824 | 05* 06* 09* 04 | LogicalLayoutModel, drop_logical_steps(), keyboard_guid() |
| gremlin/ui/module_calibration.py | 92 | 03* | CalibrationModuleModel |
| gremlin/ui/module_inputs.py | 251 | 03* | ModuleClaimedInputModel |
| gremlin/ui/module_model.py | 2969 | 03* 07* 09* 02 | ModuleRow, CardSizes, ModuleFileWatch, ModuleListModel, DriverInputModel (+10) |
| gremlin/ui/module_pairing.py | 391 | 03* | ModulePairDeviceModel, ModulePairAxisModel, ModulePairButtonModel |
| gremlin/ui/option.py | 1033 | 01* 05* 09* 08 | ConfigSectionModel, ConfigGroupModel, ConfigEntryModel, BaseMetaConfigOptionWidget, ActionSequenceOrdering (+9) |
| gremlin/ui/osc_device_model.py | 1009 | 09* | OscDeviceManagementModel, parse_import_line(), normalize_settings(), deadzone_error(), row_fields() (+20) |
| gremlin/ui/osc_feedback_model.py | 690 | 09* | OscFeedbackModel, check_address(), action_inputs(), placement(), rows_for_page() (+3) |
| gremlin/ui/osc_layout.py | 1574 | 09* | OscLayoutItem, OscLayoutStore, OscLayoutModel, settings_line(), last_seen_text() (+11) |
| gremlin/ui/osc_monitor_model.py | 349 | 09* | OscMonitorModel, is_blocked(), peer_host(), values_text(), time_text() (+2) |
| gremlin/ui/osc_option.py | 553 | 09* | OscServerModel, OscModuleSetupLink, check_host(), check_target(), add_sender() (+1) |
| gremlin/ui/osc_settings_info.py | 38 | 09* | OscSettingsInfo |
| gremlin/ui/output_modules.py | 374 | 03* 05* | OutputModuleDevices |
| gremlin/ui/pair_live.py | 215 | 07* | PairLiveThrottle |
| gremlin/ui/profile.py | 1539 | 04* 05* 06 | VirtualButtonModel, HatDirectionModel, InputItemBindingModel, InputItemModel, ModeListModel (+11) |
| gremlin/ui/script.py | 547 | 04* 09* | AbstractVariableModel, BoolVariableModel, FloatVariableModel, IntegerVariableModel, KeyboardVariableModel (+8) |
| gremlin/ui/shell_option.py | 89 | 01* | StatusResetModel, ensure_shell_options() |
| gremlin/ui/system_tray.py | 344 | 01* 06* 09* | SystemTrayIcon |
| gremlin/ui/tools.py | 66 | 08* | Tools |
| gremlin/ui/trace_model.py | 756 | 01* | TraceTree, TraceLines, TraceSwitch, TraceView, signals() (+2) |
| gremlin/ui/tray_memory.py | 77 | 01* 09* | enter_tray(), leave_tray(), release(), trim_working_set(), let_hidden_window_release_graphics() |
| gremlin/ui/type_aliases.py | 38 | 09* | QmlElement() |
| gremlin/ui/ui_scale_option.py | 117 | 01* 09* | UiScaleModel, register(), clamp_scale(), saved_scale(), windows_scaling_active() (+2) |
| gremlin/ui/update_model.py | 591 | 01* | UpdateModel |
| gremlin/ui/util.py | 746 | 02* 05* 09* | InputListenerModel, MacroRecorder, ProcessListModel, to_local_path(), updated_recent_profiles() (+4) |
| gremlin/ui/viewer_devices.py | 170 | 02* 03* 07* | ViewerDeviceModel |
| gremlin/ui/vjoy_status.py | 171 | 01* 06* | VJoyStatus, register_options() |
| gremlin/ui/window_placement.py | 529 | 01* 05* 07 | WindowPlacement, display_panel_open(), set_display_panel_open(), restore_window(), save_window() (+8) |
| gremlin/ui/window_titles.py | 88 | 01* | TitleBars, program_title(), format_title(), install() |
| gremlin/ui/windows_scale_option.py | 75 | 01* 09* | WindowsScaleModel, register(), saved_disabled() |
| gremlin/ui/xbox_device_model.py | 212 | 06* | XboxDriverStatus, XboxDeviceModel |
| gremlin/ui/xbox_maps.py | 41 | 06* | walk_actions(), xbox_maps_for_item() |
| gremlin/ui/xbox_viewer.py | 421 | 02* 06* | XboxMappedAxisModel, XboxMappedButtonModel, XboxMappedHatModel, XboxPadListModel, XboxViewerDeviceModel (+1) |
| gremlin/unknown_action.py | 149 | 05* | UnknownFunctor, UnknownActionModel, UnknownActionData, unknown_note() |
| gremlin/updater.py | 357 | 01* | Asset, Release, setup_name(), parse_release(), safe_notes() (+11) |
| gremlin/user_script.py | 1981 | 04* 06* 09* 03 | CallbackRegistry, PeriodicRegistry, JoystickDecorator, VJoyPlugin, JoystickPlugin (+23) |
| gremlin/util.py | 1163 | 01* 07* | parse_id_or_uuid(), parse_bool(), safe_read(), safe_format(), property_from_string() (+46) |
| gremlin/validate.py | 562 | 01* 05* 09* 03 | code_of(), is_warning(), profile(), modules(), after_stop() |
| gremlin/watchdog.py | 116 | 01* | Watchdog, thread_stacks(), apply() |
| gremlin/windows_event_hook.py | 479 | 02* | KBDLLHOOKSTRUCT, MSLLHOOKSTRUCT, KeyEvent, MouseEvent, KeyboardHook (+3) |
| qml/action_kinds.js | 28 | 05* | kindOf() |
| qml/ActionDragDropArea.qml | 10 | 05* | DragDropArea root |
| qml/ActionNode.qml | 430 | 05* | Item root, onActionChanged(), loadDynamicItem(), finishCreation(), destroyDynamicItem() |
| qml/ActionPane.qml | 383 | 01* 05* 06* 09* | RowLayout root, leaveDone (signal), leaveResolved (signal), hasUnsaved(), save() (+13) |
| qml/ActionSelector.qml | 102 | 05* | Item root, onActionChanged() |
| qml/AxesStateSeries.qml | 133 | 02* | Item root |
| qml/BetterProgressBar.qml | 50 | 09* | ProgressBar root |
| qml/BootstrapIcons.qml | 23 | 09* | Item root |
| qml/BootstrapIconsNames.qml | 51 | 09* | QtObject root |
| qml/ButtonStateSelector.qml | 14 | 05* | ComboBox root, stateModified (signal) |
| qml/CompactSwitch.qml | 41 | 09* | T.Switch root |
| qml/CompactSwitchIndicator.qml | 54 | 09* | Item root |
| qml/ConfigGroup.qml | 339 | 01* | ColumnLayout root, matches(), commit() |
| qml/ConfigSection.qml | 128 | 01* | ScrollView root, hasMatch(), anyMatch() |
| qml/ConfigSectionButton.qml | 55 | 01* | AbstractButton root |
| qml/confirm.js | 82 | 01* 07* 09* | isOpen(), ask() |
| qml/ConfirmDialog.qml | 123 | 01* | Popup root, confirmed (signal), cancelled (signal), accept(), cancel() |
| qml/control_menu.js | 159 | 05* 06* 09* | state(), standardMenu(), actionMenu() |
| qml/ControlFindBar.qml | 185 | 05* 06* 09* | ColumnLayout root, changed (signal), cleared (signal), isChecked(), clear() |
| qml/ControlTree.qml | 739 | 05* 06* 09* | Item root, parentMenu (signal), groupMenu (signal), toggleOpen(), toggleGroup() (+12) |
| qml/DangerButton.qml | 37 | 01* | Button root |
| qml/DebugFrame.qml | 97 | 01* | Item root |
| qml/device_library_open.js | 27 | 10* | openDeviceLibrary(), toMain() |
| qml/DeviceBindingsPage.qml | 666 | 01* 05* 06* 08* | Item root, moduleSetupRequested (signal), toggleAppearance(), requestCloseDisplay(), setMode() (+14) |
| qml/DeviceList.qml | 302 | 01* 02* 03* 09* 06 | Item root, rename(), nextTab(), previousTab(), isVjoyTab() (+4) |
| qml/DeviceMapCard.qml | 110 | 07* | Item root, resetView(), clampPan(), refreshChipRows(), hwAxis() (+2) |
| qml/DeviceMapOptionsWindow.qml | 130 | 07* | Window root, colorRequested (signal), openFor(), onActiveFocusChanged() |
| qml/DevicePhotoHost.qml | 141 | 07* | Item root, srcUrlOf(), hydrate(), localPath(), whitePathOf() (+3) |
| qml/DeviceTabBar.qml | 75 | 01* | T.TabBar root |
| qml/DialogAbout.qml | 57 | 01* | ApplicationWindow root |
| qml/DialogAutoMappingTool.qml | 298 | 08* 03 | ApplicationWindow root, showChosen() |
| qml/DialogCalibration.qml | 683 | 03* 08 | ApplicationWindow root, refreshUnsaved(), axisName(), noteChange(), forgetChanges() (+12) |
| qml/DialogConfigureModule.qml | 756 | 03* 07* 09* 01 08 | ApplicationWindow root, hasUnsavedWork(), refreshModuleFileLabel(), reloadModuleControls(), onUserEdited() (+18) |
| qml/DialogDeviceInformation.qml | 208 | 02* 03 | ApplicationWindow root, clean() |
| qml/DialogDeviceMappingEditor.qml | 5244 | 07* 08 | ApplicationWindow root, filePartsNow(), ownFileChange(), askLeave(), onModelReset() (+203) |
| qml/DialogDevicePack.qml | 1247 | 03* 07* 08* | ApplicationWindow root, onPackExported(), say(), rowKey(), reloadDevices() (+26) |
| qml/DialogHardwareHide.qml | 722 | 02* | ApplicationWindow root, titleOf(), openResetDevices(), confirmRemoveGame(), applyRatio() (+1) |
| qml/DialogHelp.qml | 919 | 01* 09* 07 | ApplicationWindow root, setListWidth(), resetListWidth(), isFolded(), toggleChapter() (+9) |
| qml/DialogHistory.qml | 749 | 08* 01 03 05 07 | ApplicationWindow root, wanted(), aboutText(), applyFilter(), setArea() (+13) |
| qml/DialogInputViewer.qml | 103 | 02* | ApplicationWindow root |
| qml/DialogLibraryCopy.qml | 341 | 10* | Dialog root, openFor(), askProfiles(), chosenParts(), chosenProfiles() (+4) |
| qml/DialogLibraryOutput.qml | 290 | 10* | Dialog root, openFor(), chosenProfiles(), replan(), choices() (+2) |
| qml/DialogLibrarySettings.qml | 136 | 10* | Dialog root, openNow() |
| qml/DialogLibrarySwap.qml | 244 | 10* | Dialog root, openFor(), askProfiles(), chosenParts(), chosenProfiles() (+2) |
| qml/DialogLibraryTidy.qml | 135 | 10* | Dialog root, openNow(), preview(), sizeText() |
| qml/DialogLiveLog.qml | 736 | 01* | ApplicationWindow root, onTextChanged(), onChanged(), onAppended(), onChanged() (+4) |
| qml/DialogManageModes.qml | 288 | 04* 01 | ApplicationWindow root, confirmDelete() |
| qml/DialogOptions.qml | 254 | 01* | ApplicationWindow root, settingLabels(), revealSetting() |
| qml/DialogResetDevices.qml | 340 | 02* | ApplicationWindow root, openWith(), resultColor() |
| qml/DialogSaveDiagnostics.qml | 121 | 01* | ApplicationWindow root, saveTo() |
| qml/DialogUpdate.qml | 250 | 01* | ApplicationWindow root, notesStyle(), message() |
| qml/DialogXboxViewer.qml | 107 | 02* 06* | ApplicationWindow root, pairTitle() |
| qml/DismissibleDialog.qml | 265 | 09* | Popup root, confirmed (signal), cancelled (signal), ask(), confirm() (+3) |
| qml/DragDropArea.qml | 39 | 09* | DropArea root |
| qml/DropMarker.qml | 21 | 09* | Rectangle root |
| qml/DynamicItemLoader.qml | 113 | 01* | Item root, loaded (signal), loadError (signal), reload() |
| qml/EmptyState.qml | 48 | 01* | Item root, action (signal) |
| qml/ErrorDialog.qml | 98 | 09* | Popup root, accepted (signal), rejected (signal) |
| qml/EscapeCloses.qml | 14 | 01* | Shortcut root |
| qml/FilePicker.qml | 130 | 01* | Item root, picked (signal), cancelled (signal), startFolder(), dialog() (+2) |
| qml/HatDirectionSelector.qml | 80 | 05* | Item root |
| qml/HatDirectionSelectorV2.qml | 77 | 05* | Item root |
| qml/HatView.qml | 75 | 03* | Item root |
| qml/help/device_bindings_actions.js | 738 | 01* 05* | topics() |
| qml/help/device_library.js | 481 | 01* 10* | topics(), t() |
| qml/help/device_mapping_editor.js | 649 | 01* 07* | topics(), t() |
| qml/help/getting_started.js | 399 | 01* | topics() |
| qml/help/home_devices.js | 443 | 01* 03* | topics() |
| qml/help/index.js | 91 | 01* | chapters(), topics(), find() |
| qml/help/logical_device.js | 292 | 01* | topics() |
| qml/help/modes.js | 163 | 01* | topics() |
| qml/help/options_profile.js | 266 | 01* | topics() |
| qml/help/osc.js | 833 | 01* 09* | topics() |
| qml/help/tools.js | 492 | 01* | topics() |
| qml/help_links.js | 93 | 01* 09* | allowedOpen(), isAllowedOpen(), parse(), isProgramLink(), allLinks() (+2) |
| qml/help_search.js | 202 | 01* 09* | words(), plain(), countIn(), filter(), highlight() |
| qml/help_topics.js | 24 | 01* 09* 05 | topics(), deviceMappingEditorTopics(), deviceLibraryTopics(), topic() |
| qml/helpers.js | 193 | 01* | createComponent(), toggleComponent(), windowOf(), setMainWindow(), mainWindow() (+10) |
| qml/HelpSearchBar.qml | 201 | 01* 09* | Item root, resultsChanged (signal), next (signal), focusField(), clear() |
| qml/HintsTooltip.qml | 62 | 09* | Popup root |
| qml/HorizontalDivider.qml | 31 | 09* | Rectangle root |
| qml/IconButton.qml | 32 | 09* | Button root |
| qml/IconCheckBox.qml | 14 | 09* | CheckBox root |
| qml/InputBehavior.qml | 92 | 05* | Item root, treatAs() |
| qml/InputConfiguration.qml | 140 | 01* 05* 06* | Item root |
| qml/InputItemBinding.qml | 120 | 05* | Item root, onReloadCurrentInputItem() |
| qml/InputItemBindingConfigurationHeader.qml | 301 | 05* | Item root |
| qml/InputListener.qml | 137 | 02* | Item root, listenFinished (signal) |
| qml/InputViewerCard.qml | 320 | 02* | ColumnLayout root, hwAxis(), vjAxis(), hwButton(), vjButton() |
| qml/JGListView.qml | 20 | 09* | ListView root |
| qml/JGSpinBox.qml | 10 | 09* | SpinBox root |
| qml/JGTabButton.qml | 26 | 09* | TabButton root |
| qml/JGText.qml | 13 | 09* | Text root |
| qml/JGTextField.qml | 22 | 09* | TextField root |
| qml/JGToolButton.qml | 75 | 09* | ToolButton root |
| qml/KeyboardPage.qml | 487 | 01* 02* 05* 06* | Item root, toggleAppearance(), requestCloseDisplay(), setMode(), openInput() (+7) |
| qml/LabelValueComboBox.qml | 85 | 05* 09* | Item root, selectionChanged (signal) |
| qml/LayoutHorizontalSpacer.qml | 9 | 09* | Rectangle root |
| qml/LayoutVerticalSpacer.qml | 9 | 09* | Rectangle root |
| qml/ListAppearancePanel.qml | 932 | 05* 06* | Rectangle root, closed (signal), toggled (signal), pick(), numVal() (+12) |
| qml/LiveLogTrace.qml | 743 | 01* | ColumnLayout root, clicked (signal), apply (signal), onLinesAdded() |
| qml/LogicalDeviceSelector.qml | 67 | 05* 06* | Item root, onActivated() |
| qml/LogicalPage.qml | 665 | 06* 09* | Item root, toggleAppearance(), requestCloseDisplay(), setMode(), onPaneLost() (+4) |
| qml/Main.qml | 2634 | 01* 03* 04* 05* 06* 07* 09* 10* 02 | ApplicationWindow root, refreshProfileDirty(), onWindowTitleChanged(), onProfileChanged(), onUnsavedChanged() (+101) |
| qml/main_commands.js | 141 | 01* 03* 04* 08* 09* 10* 02 | commandList() |
| qml/MainFailure.qml | 55 | 01* 02* | ApplicationWindow root |
| qml/MessageLine.qml | 89 | 01* | Rectangle root, show(), clear() |
| qml/NumericalRangeSlider.qml | 149 | 05* | Item root, firstEdited (signal), secondEdited (signal), textFromValue(), valueFromText() |
| qml/OptionActionSequenceOrdering.qml | 224 | 01* 05* | Item root, onLayoutChanged(), onModelReset(), onDataChanged(), nameAt() (+2) |
| qml/OptionDeviceMapLibrary.qml | 183 | 01* 07* | Item root, refreshTemplates() |
| qml/OptionEntryCard.qml | 74 | 01* | Item root |
| qml/OptionHighlightSpeed.qml | 46 | 01* | Item root |
| qml/OptionLogLevel.qml | 48 | 01* | Item root |
| qml/OptionOscModuleSetup.qml | 41 | 01* 09* | Item root |
| qml/OptionProfileAutoLoading.qml | 276 | 01* 02* 04* | Item root, askRemove() |
| qml/OptionStatusCards.qml | 30 | 01* | Item root |
| qml/OptionTTSVoiceSelection.qml | 30 | 01* 09* | Item root |
| qml/OptionUiScale.qml | 50 | 01* 09* | Item root |
| qml/OptionWindowsScale.qml | 66 | 01* 09* | Item root |
| qml/OscAddDialog.qml | 990 | 09* | Popup root, accepted (signal), picked (signal), resetFields(), openForEdit() (+22) |
| qml/OscDiscoveryTab.qml | 133 | 09* | Flickable root |
| qml/OscFeedbackEditor.qml | 240 | 09* | Item root |
| qml/OscFeedbackSection.qml | 280 | 03* 09* | Item root, openOscPage(), commit(), save(), ask() (+1) |
| qml/OscImportDialog.qml | 359 | 09* | Popup root, accepted (signal), touchOscAccepted (signal), resetFields(), chooseFile() (+5) |
| qml/OscMonitorPanel.qml | 473 | 01* 09* | Rectangle root, popOutRequested (signal), closeRequested (signal), addAsInput(), allowSender() (+1) |
| qml/OscOutputTab.qml | 323 | 09* | Flickable root, clicked (signal), edit(), reset(), submit() |
| qml/OscPage.qml | 1083 | 01* 06* 09* | Item root, toggleAppearance(), requestCloseDisplay(), setMode(), showMonitor() (+25) |
| qml/OscServerTab.qml | 315 | 09* | Flickable root, clicked (signal), commit(), save(), submit() |
| qml/OscSetupTabs.qml | 156 | 03* 09* | ColumnLayout root, showTab(), commit() |
| qml/OutputModuleView.qml | 1286 | 03* | Item root, closePanel (signal), userSet (signal), pick(), pick() (+26) |
| qml/PageAppearance.qml | 100 | 05* 06* 09 | ListAppearancePanel root, toggleAppearance(), requestCloseDisplay() |
| qml/PointerTip.qml | 31 | 09* | Item root |
| qml/PrintExportWindow.qml | 561 | 07* | Window root, indexOfValue(), pageInches(), dpi(), marginInches() (+13) |
| qml/ProfileSettings.qml | 258 | 04* | Item root |
| qml/Pulse.qml | 36 | 01* 09* | Rectangle root |
| qml/RenameField.qml | 64 | 01* | JGTextField root, renamed (signal), ended (signal), start() |
| qml/rig_align.js | 101 | 07* | canAlign(), canDistribute(), alignSelection(), distributeSelection() |
| qml/rig_callout.js | 171 | 07* | isCallout(), calloutTip(), calloutTipLocal(), paintCallout(), onCalloutTip() (+6) |
| qml/rig_chips.js | 631 | 07* | nodeAt(), nodeIndex(), destOf(), memberKind(), leafKind() (+38) |
| qml/rig_commands.js | 885 | 07* | checked(), list(), enabled(), whyDisabled(), run() (+6) |
| qml/rig_coords.js | 79 | 07* | spaceRect(), innerPageRect(), clamp01(), worldToX(), worldToY() (+8) |
| qml/rig_draw.js | 691 | 07* | isDraw(), isTable(), isText(), drawGeom(), applyDrawResize() (+28) |
| qml/rig_find.js | 97 | 07* | findTick(), findControl(), showFindMessage() |
| qml/rig_grouprot.js | 398 | 07* | canTurnTogether(), selectionBounds(), onTurnHandle(), turnPivot(), beginTurn() (+11) |
| qml/rig_groups.js | 823 | 07* | groupAlignH(), setAlignH(), bakeAlignToFree(), memberIndexOf(), stackPitch() (+44) |
| qml/rig_hit.js | 416 | 07* | hitTest(), handleHit(), hitDraw(), shapeHit(), memberHit() (+4) |
| qml/rig_hotspot.js | 230 | 07* | hotPressed(), hotShown(), paintHotspot(), hotPulseTick(), hotPulsing() |
| qml/rig_layers.js | 960 | 07* | normalizeStacking(), isBackground(), canHoldBackground(), backgroundRefusal(), planeOf() (+42) |
| qml/rig_leaders.js | 718 | 07* | hotPt(), fromEnd(), toEnd(), endPt(), leaderList() (+29) |
| qml/rig_menu.js | 1042 | 07* | menuKind(), menuTitle(), all(), flip(), pick() (+4) |
| qml/rig_mirror.js | 130 | 07* | mirrorLayout() |
| qml/rig_overlays.js | 347 | 07* | isOverlay(), isPinnable(), isLocked(), pinLocal(), hitOverlayPin() (+16) |
| qml/rig_path.js | 306 | 07* | isPath(), isPathTool(), pathLocal(), pathPointsAt(), setPathPoints() (+14) |
| qml/rig_pointer.js | 185 | 07* | applyPointer() |
| qml/rig_print_area.js | 184 | 07* | printAreaRect(), beginPrintArea(), movePrintArea(), drawnPrintRect(), endPrintArea() (+4) |
| qml/rig_props.js | 270 | 07* | pct(), propsModel(), setProp() |
| qml/rig_rulers.js | 104 | 07* | addRulerGuide(), moveRulerGuide(), removeRulerGuide(), clearRulerGuides(), rulerGuideAt() (+3) |
| qml/rig_selection.js | 601 | 07* | deleteSelection(), freeEndsAimedAt(), fix(), deleteChip(), deleteSelected() (+17) |
| qml/rig_shapes.js | 676 | 07* | blockArrow(), dashFor(), lineEnds(), lineBox(), lineMargin() (+36) |
| qml/rig_snap.js | 258 | 07* | snapWorld(), snapPx(), nodeBox(), clearMoveGuides(), guideSkipTarget() (+9) |
| qml/rig_style.js | 136 | 07* | ink(), isStyleKey(), targetMember(), styleVal(), applyField() (+7) |
| qml/rig_styles.js | 91 | 07* | styleKindOf(), styleFieldsOf(), saveStyleOf(), applySavedStyle(), stylesFor() |
| qml/rig_tables.js | 806 | 07* | emptyTableRow(), ensureTable(), tableMinW(), tableMinH(), fitTableRow() (+45) |
| qml/rig_text.js | 167 | 07* | textThemeStyle(), textFormatKeys(), copyTextFormat(), applyTextFormat(), clearTextFormat() (+6) |
| qml/rig_transform.js | 394 | 07* | transformModesFor(), setTransformMode(), canEditPoints(), hasShaping(), skewMatrix() (+9) |
| qml/RigChipItem.qml | 61 | 07* | Rectangle root |
| qml/RigChipLabel.qml | 90 | 07* | Item root |
| qml/RigDrawItem.qml | 643 | 07* | Item root, onTickChanged(), onTickChanged(), hasLook(), screenCopySize() (+1) |
| qml/RigGrid.qml | 75 | 07* | Canvas root |
| qml/RigGroupItem.qml | 78 | 07* | Item root |
| qml/RigGuides.qml | 67 | 07* | Canvas root, onGuideXChanged(), onGuideYChanged(), onRulerGuidesXChanged(), onRulerGuidesYChanged() (+2) |
| qml/RigLayersPanel.qml | 859 | 07* | Rectangle root, closeRequested (signal), planeItems(), deleteRow(), toggleKind() (+31) |
| qml/RigLeaderLayer.qml | 72 | 07* | Canvas root |
| qml/RigMiniChip.qml | 91 | 07* | Rectangle root |
| qml/RigOptionsPanel.qml | 286 | 07* | Item root, colorRequested (signal) |
| qml/RigPointerArea.qml | 922 | 07* | MouseArea root, isMoveDrag(), inDeadZone(), menuSelectionPlus(), shiftLock() (+7) |
| qml/RigPrintArea.qml | 193 | 07* | Item root, onInkChanged() |
| qml/RigPropsPanel.qml | 273 | 07* | Rectangle root, closeRequested (signal), describe(), fieldRect() |
| qml/RigRenderer.qml | 500 | 07* | Item root, snapshot(), snapshotOf(), isVisibleBackground(), jobNodes() (+5) |
| qml/RigSelRing.qml | 25 | 07* | Rectangle root |
| qml/RootActionNode.qml | 60 | 05* | Item root |
| qml/RunningNote.qml | 30 | 03* 06* | Label root |
| qml/ScriptConfiguration.qml | 406 | 04* 09* | JGListView root |
| qml/ScriptManager.qml | 252 | 04* | Item root |
| qml/SearchBox.qml | 118 | 01* | Item root, accepted (signal), cleared (signal), focusField(), clear() |
| qml/SectionHeading.qml | 36 | 01* | ColumnLayout root |
| qml/ShortcutList.qml | 218 | 07* | Item root, refresh(), search(), focusSearch(), describe() |
| qml/ShortcutsWindow.qml | 109 | 07* | Window root, openFor() |
| qml/SidePanel.qml | 361 | 07* | Item root, changed (signal), stripClicked (signal), unfold(), fold() (+2) |
| qml/StatusCard.qml | 566 | 03* 10* 08 | Rectangle root, cardFocused (signal), openDeviceBindings (signal), isSecondClick(), menuModel() |
| qml/StatusPage.qml | 1296 | 03* 10* 08 | Item root, focusSlug (signal), openDeviceBindings (signal), undo(), redo() (+49) |
| qml/Style.qml | 229 | 09* | Item root, removeAlpha(), alpha(), dp(), fitWidth() (+1) |
| qml/tester/AxisBar.qml | 67 | 02* | RowLayout root |
| qml/tester/CompactCard.qml | 98 | 02* | Rectangle root, clicked (signal) |
| qml/tester/DeviceRow.qml | 124 | 02* | Rectangle root, clicked (signal) |
| qml/tester/HatCompass.qml | 47 | 02* | Rectangle root |
| qml/tester/InputTester.qml | 865 | 02* | Window root, onInputFollowed(), findRow(), selectRow(), showButton() (+1) |
| qml/tester/LogsView.qml | 295 | 02* | Rectangle root, showLine(), onLogChanged() |
| qml/tester/TesterButton.qml | 43 | 02* | Rectangle root, clicked (signal) |
| qml/tester/TesterCombo.qml | 105 | 02* | Rectangle root, picked (signal) |
| qml/tester/TesterSwitch.qml | 57 | 02* | Item root, toggled (signal) |
| qml/tester/TesterTag.qml | 38 | 02* | Rectangle root |
| qml/TextInputDialog.qml | 186 | 09* | Popup root, accepted (signal), edited (signal), seedText() |
| qml/ToolWindowMemory.qml | 43 | 01* | Item root, restore(), save(), onClosing(), onWidthChanged() (+1) |
| qml/Triangle.qml | 25 | 09* | Shape root |
| qml/TriggerMode.qml | 45 | 05* | Item root |
| qml/UndoBar.qml | 78 | 01* | RowLayout root, undo (signal), redo (signal) |
| qml/UnknownAction.qml | 28 | 05* | Item root |
| qml/VJoySelector.qml | 165 | 05* | Item root, selectionChanged (signal), initialize(), textWidth(), updateState() (+2) |
| qml/VkbRigEditor.qml | 2054 | 07* | Item root, pastePictureRequested (signal), planeMoved (signal), paintLeaders(), fixPx() (+497) |
| qml/VkbRigFace.qml | 574 | 07* | Item root, viewX(), viewY(), editorX(), editorY() (+30) |
| qml/window_registry.js | 17 | 01* | track() |
| qml/WindowDeviceLibrary.qml | 1518 | 10* | ApplicationWindow root, openOn(), showMessage(), askConfirm(), undo() (+37) |
| qml/WindowOscMonitor.qml | 66 | 09* | ApplicationWindow root |
| qml/Xbox360Face.qml | 152 | 02* 06* | Item root, v(), on(), px(), py() (+2) |
| qml/XboxDevice.qml | 121 | 06* | Item root |
| qml/XboxDriverCheck.qml | 78 | 06* | Rectangle root, reload() |
| qml/XboxViewerCard.qml | 243 | 02* 06* | ColumnLayout root, hwAxis(), hwButton(), xb(), destAxis() |
| theme/Gremlin/Base/FloatSpinBox.qml | 126 | - | Item root, valueModified (signal), toFloat(), toInt() |
| theme/Gremlin/Base/qmldir | 5 | - |  |
| theme/Gremlin/Base/RecordButton.qml | 29 | - | RoundButton root |
| theme/Gremlin/Base/SpinBox.qml | 8 | - | SpinBox root |
| theme/Gremlin/Base/TooltipComboBox.qml | 43 | - | ComboBox root |
| theme/Gremlin/Base/WrappingTooltip.qml | 10 | 01* | ToolTip root |
| theme/Gremlin/Compact/Button.qml | 59 | - | T.Button root |
| theme/Gremlin/Compact/ButtonStateSelector.qml | 14 | - | Compact.ComboBox root, stateModified (signal) |
| theme/Gremlin/Compact/CheckBox.qml | 43 | - | T.CheckBox root |
| theme/Gremlin/Compact/ComboBox.qml | 111 | - | T.ComboBox root |
| theme/Gremlin/Compact/FloatSpinBox.qml | 9 | - | Base.FloatSpinBox root |
| theme/Gremlin/Compact/HatDirectionSelectorV2.qml | 94 | - | Item root |
| theme/Gremlin/Compact/ItemDelegate.qml | 59 | - | T.ItemDelegate root |
| theme/Gremlin/Compact/Label.qml | 18 | - | T.Label root |
| theme/Gremlin/Compact/qmldir | 13 | - |  |
| theme/Gremlin/Compact/RecordButton.qml | 28 | - | RoundButton root |
| theme/Gremlin/Compact/RoundButton.qml | 62 | - | T.RoundButton root |
| theme/Gremlin/Compact/SpinBox.qml | 119 | - | T.SpinBox root |
| theme/Gremlin/Compact/TooltipComboBox.qml | 45 | - | Compact.ComboBox root |
| theme/Gremlin/Menus/CommandPalette.qml | 176 | 01* | T.Popup root, search(), runPick(), describe() |
| theme/Gremlin/Menus/commands.js | 235 | 01* 09* | define(), defineAll(), removeOwner(), clear(), get() (+14) |
| theme/Gremlin/Menus/ContextMenu.qml | 1190 | 07* | Popup root, favouriteToggled (signal), favouriteRemoved (signal), hoverRow(), onHeightChanged() (+18) |
| theme/Gremlin/Menus/DropdownPopup.qml | 184 | - | T.Popup root |
| theme/Gremlin/Menus/DropdownRow.qml | 67 | - | T.ItemDelegate root |
| theme/Gremlin/Menus/menu_model.js | 120 | 09* | menu(), section(), action(), toggle(), pick() (+5) |
| theme/Gremlin/Menus/MenuRowBackground.qml | 26 | - | Rectangle root |
| theme/Gremlin/Menus/MenuSurface.qml | 14 | - | Rectangle root |
| theme/Gremlin/Menus/qmldir | 17 | - |  |
| theme/Gremlin/Menus/TextEditMenu.qml | 63 | - | ThemedMenu root |
| theme/Gremlin/Menus/ThemedMenu.qml | 128 | - | T.Menu root, hasShown(), describe(), compactNow() |
| theme/Gremlin/Menus/ThemedMenuBar.qml | 37 | - | T.MenuBar root |
| theme/Gremlin/Menus/ThemedMenuBarItem.qml | 46 | - | T.MenuBarItem root |
| theme/Gremlin/Menus/ThemedMenuItem.qml | 93 | - | T.MenuItem root, refresh() |
| theme/Gremlin/Menus/ThemedMenuSeparator.qml | 26 | - | T.MenuSeparator root |
| theme/GremlinStyle/Button.qml | 59 | - | T.Button root |
| theme/GremlinStyle/CheckBox.qml | 44 | - | T.CheckBox root |
| theme/GremlinStyle/ComboBox.qml | 116 | - | T.ComboBox root |
| theme/GremlinStyle/Dialog.qml | 60 | - | T.Dialog root |
| theme/GremlinStyle/DialogButtonBox.qml | 46 | - | T.DialogButtonBox root |
| theme/GremlinStyle/Frame.qml | 25 | - | T.Frame root |
| theme/GremlinStyle/impl/CheckIndicator.qml | 53 | - | Rectangle root |
| theme/GremlinStyle/impl/RadioIndicator.qml | 50 | - | Rectangle root |
| theme/GremlinStyle/impl/SwitchIndicator.qml | 51 | - | Item root |
| theme/GremlinStyle/ItemDelegate.qml | 56 | - | T.ItemDelegate root |
| theme/GremlinStyle/Menu.qml | 52 | - | T.Menu root |
| theme/GremlinStyle/MenuBar.qml | 38 | - | T.MenuBar root |
| theme/GremlinStyle/MenuBarItem.qml | 60 | - | T.MenuBarItem root |
| theme/GremlinStyle/MenuItem.qml | 88 | - | T.MenuItem root |
| theme/GremlinStyle/MenuSeparator.qml | 32 | - | T.MenuSeparator root |
| theme/GremlinStyle/Pane.qml | 24 | - | T.Pane root |
| theme/GremlinStyle/Popup.qml | 34 | - | T.Popup root |
| theme/GremlinStyle/ProgressBar.qml | 37 | - | T.ProgressBar root |
| theme/GremlinStyle/qmldir | 36 | - |  |
| theme/GremlinStyle/RadioButton.qml | 44 | - | T.RadioButton root |
| theme/GremlinStyle/RangeSlider.qml | 79 | - | T.RangeSlider root |
| theme/GremlinStyle/RoundButton.qml | 60 | - | T.RoundButton root |
| theme/GremlinStyle/ScrollBar.qml | 64 | - | T.ScrollBar root |
| theme/GremlinStyle/ScrollIndicator.qml | 48 | - | T.ScrollIndicator root |
| theme/GremlinStyle/ScrollView.qml | 34 | - | T.ScrollView root |
| theme/GremlinStyle/Slider.qml | 66 | - | T.Slider root |
| theme/GremlinStyle/SpinBox.qml | 127 | - | T.SpinBox root |
| theme/GremlinStyle/SplitView.qml | 25 | - | T.SplitView root |
| theme/GremlinStyle/Switch.qml | 44 | - | T.Switch root |
| theme/GremlinStyle/TabBar.qml | 40 | - | T.TabBar root |
| theme/GremlinStyle/TabButton.qml | 39 | - | T.TabButton root |
| theme/GremlinStyle/TextArea.qml | 69 | - | T.TextArea root |
| theme/GremlinStyle/TextField.qml | 69 | - | T.TextField root |
| theme/GremlinStyle/ToolBar.qml | 28 | - | T.ToolBar root |
| theme/GremlinStyle/ToolButton.qml | 53 | - | T.ToolButton root |
| theme/GremlinStyle/ToolTip.qml | 54 | 01* | T.ToolTip root |
| action_plugins/__init__.py | 3 | 05* 06* 09* |  |
| action_plugins/axis_delta/__init__.py | 216 | 05* 06* 09* | AxisDeltaFunctor, AxisDeltaModel, AxisDeltaData |
| action_plugins/axis_delta/AxisDeltaAction.qml | 130 | 05 | Item root |
| action_plugins/axis_pair.py | 159 | 05* | AxisRef, AxisView, is_set(), pick_list(), new_instance() (+3) |
| action_plugins/chain/__init__.py | 223 | 05* 06* 09* | ChainFunctor, ChainModel, ChainData |
| action_plugins/chain/ChainAction.qml | 114 | 05 | Item root |
| action_plugins/change_mode/__init__.py | 357 | 05* 06* 09* | ChangeType, ChangeModeFunctor, ChangeModeModel, ChangeModeData |
| action_plugins/change_mode/ChangeModeAction.qml | 206 | 05 | Item root, onActivated(), onActivated() |
| action_plugins/common.py | 160 | 05* | RelativeAxisLoop, joystick_label() |
| action_plugins/condition/__init__.py | 359 | 05* 06* 09* | ConditionFunctor, ConditionModel, ConditionData |
| action_plugins/condition/comparator.py | 287 | 05* | AbstractComparatorModel, RangeComparatorModel, PressedComparatorModel, DirectionComparatorModel, AbstractComparator (+3) |
| action_plugins/condition/Comparator.qml | 91 | 05 | Item root |
| action_plugins/condition/condition.py | 938 | 05* 09* | AbstractState, AbstractCondition, VJoyCondition, KeyboardCondition, MissingOscInput (+3) |
| action_plugins/condition/ConditionAction.qml | 426 | 05* 09* | Item root, toUnorderedList() |
| action_plugins/description/__init__.py | 156 | 05* 06* 09* | DescriptionFunctor, DescriptionModel, DescriptionData |
| action_plugins/description/DescriptionAction.qml | 46 | 05 | Item root |
| action_plugins/double_tap/__init__.py | 347 | 05* 06* 09* | DoubleTapFunctor, DoubleTapModel, DoubleTapData |
| action_plugins/double_tap/DoubleTapAction.qml | 163 | 05 | Item root |
| action_plugins/dual_axis_deadzone/__init__.py | 372 | 05* 06* 09* | DualAxisDeadzoneFunctor, DualAxisDeadzoneModel, DualAxisDeadzoneData |
| action_plugins/dual_axis_deadzone/DualAxisDeadzoneAction.qml | 301 | 05* | Item root, onModelChanged() |
| action_plugins/hat_buttons/__init__.py | 326 | 05* 06* 09* | DirectionalButton, HatButtonsFunctor, HatButtonsModel, HatButtonsData |
| action_plugins/hat_buttons/HatButtonsAction.qml | 109 | 05 | Item root |
| action_plugins/load_profile/__init__.py | 201 | 04* 05* 06* 09* | LoadProfileFunctor, LoadProfileModel, LoadProfileData |
| action_plugins/load_profile/LoadProfileAction.qml | 60 | 05 | Item root |
| action_plugins/macro/__init__.py | 1323 | 05* 06* 09* | AbstractActionModel, JoystickActionModel, KeyActionModel, LogicalDeviceActionModel, OscActionModel (+11) |
| action_plugins/macro/MacroAction.qml | 922 | 05* 09* | Item root, onActionAdded() |
| action_plugins/map_to_keyboard/__init__.py | 200 | 05* 06* 09* | MapToKeyboardFunctor, MapToKeyboardModel, MapToKeyboardData |
| action_plugins/map_to_keyboard/MapToKeyboardAction.qml | 52 | 05 | Item root |
| action_plugins/map_to_logical_device/__init__.py | 591 | 05* 06* 09* | MapToLogicalDeviceFunctor, MapToLogicalDeviceModel, ControlPicker, MapToLogicalDeviceData |
| action_plugins/map_to_logical_device/MapToLogicalDeviceAction.qml | 143 | 05* 06* | Item root |
| action_plugins/map_to_mouse/__init__.py | 418 | 05* 06* 09* | MapToMouseMode, MapToMouseFunctor, MapToMouseModel, MapToMouseData |
| action_plugins/map_to_mouse/MapToMouseAction.qml | 332 | 05 | Item root |
| action_plugins/map_to_vjoy/__init__.py | 413 | 05* 06* 09* | MapToVjoyFunctor, MapToVjoyModel, MapToVjoyData |
| action_plugins/map_to_vjoy/MapToVjoyAction.qml | 125 | 05 | Item root |
| action_plugins/map_to_xbox/__init__.py | 408 | 05* 06* 09* | MapToXboxFunctor, MapToXboxModel, MapToXboxData, targets_for() |
| action_plugins/map_to_xbox/MapToXboxAction.qml | 129 | 05* | Item root |
| action_plugins/merge_axis/__init__.py | 415 | 05* 06* 09* | MergeOperation, MergeAxisFunctor, MergeAxisModel, MergeAxisData |
| action_plugins/merge_axis/MergeAxisAction.qml | 257 | 05* | Item root, onModelChanged() |
| action_plugins/pause_resume/__init__.py | 185 | 05* 06* 09* | PauseResumeType, PauseResumeFunctor, PauseResumeModel, PauseResumeData |
| action_plugins/pause_resume/PauseResumeAction.qml | 60 | 05 | Item root |
| action_plugins/play_sound/__init__.py | 211 | 05* 06* 09* | PlaySoundFunctor, PlaySoundModel, PlaySoundData |
| action_plugins/play_sound/PlaySoundAction.qml | 108 | 05 | Item root |
| action_plugins/reference/__init__.py | 213 | 05* 06* 09* | ReferenceFunctor, ReferenceModel, ReferenceData |
| action_plugins/reference/ReferenceAction.qml | 58 | 05 | Item root |
| action_plugins/response_curve/__init__.py | 676 | 05* 06* 09* | DeadzoneIndex, ResponseCurveFunctor, Deadzone, ControlPoint, ResponseCurveModel (+2) |
| action_plugins/response_curve/HandleControl.qml | 174 | - | Rectangle root, updateHandle() |
| action_plugins/response_curve/PointControl.qml | 43 | - | Rectangle root |
| action_plugins/response_curve/render_helpers.js | 42 | 05 | draw_curve(), draw_background(), clamp(), x2u(), y2v() (+2) |
| action_plugins/response_curve/ResponseCurveAction.qml | 344 | 05 | Item root, map2u(), map2v(), map2x(), map2y() (+1) |
| action_plugins/root/__init__.py | 137 | 05* 06* 09* | RootFunctor, RootModel, RootData |
| action_plugins/run_command/__init__.py | 202 | 05* 06* 09* | RunCommandFunctor, RunCommandModel, RunCommandData |
| action_plugins/run_command/RunCommandAction.qml | 137 | 05 | Item root |
| action_plugins/send_osc/__init__.py | 447 | 05* 06* 09* | SendOscFunctor, SendOscModel, SendOscData, clean_values(), address_error() |
| action_plugins/send_osc/SendOscAction.qml | 248 | 05* 09* | Item root |
| action_plugins/smart_toggle/__init__.py | 231 | 05* 06* 09* | SmartToggleFunctor, SmartToggleModel, SmartToggleData |
| action_plugins/smart_toggle/SmartToggleAction.qml | 71 | 05 | Item root |
| action_plugins/split_axis/__init__.py | 190 | 05* 06* 09* | SplitAxisFunctor, SplitAxisModel, SplitAxisData |
| action_plugins/split_axis/SplitAxisAction.qml | 139 | 05 | Item root |
| action_plugins/tempo/__init__.py | 353 | 05* 06* 09* | TempoFunctor, TempoModel, TempoData |
| action_plugins/tempo/TempoAction.qml | 156 | 05 | Item root |
| action_plugins/text_to_speech/__init__.py | 259 | 05* 06* 09* | TextToSpeechFunctor, TextToSpeechModel, TextToSpeechData |
| action_plugins/text_to_speech/TextToSpeechAction.qml | 129 | 05 | Item root |
| dill/__init__.py | 449 | 02* 05* 06* 09* | DILLError, GUID, InputType, DeviceActionType, InputEvent (+4) |
| vigem/__init__.py | 3 | 05* 06* 09* |  |
| vigem/ids.py | 64 | 02* 03* 06* | driver_file(), driver_installed(), driver_version(), vigem_client_error(), is_vigem_xbox_summary() (+1) |
| vigem/own_pads.py | 125 | 02* 06* | has_xbox_id(), before_plug(), note_device(), is_own_pad(), forget_all() |
| vigem/vigem_client.py | 98 | 06* | dll_path(), load_error(), client() |
| vigem/vigem_commons.py | 52 | 06* | XUSB_BUTTON, XUSB_REPORT, VIGEM_ERRORS |
| vigem/xbox.py | 395 | 06* | XboxError, XboxTarget, XboxPad, XboxProxy |
| vjoy/__init__.py | 3 | 05* 06* 09* |  |
| vjoy/vjoy.py | 964 | 06* | AxisCode, HatType, VJoyStateCache, Axis, Button (+11) |
| vjoy/vjoy_interface.py | 115 | 06* | VJoyState, VJoyInterface |
| joystick_gremlin.py | 1367 | 01* 02* 03* 04* 05* 06* 07* 08* 09* 10* | StartupError, JoystickGremlinApp, configure_logger(), exception_hook(), running_offscreen() (+8) |
| input_tester.py | 84 | 01* 02* | resource_root(), parse_args(), build_engine(), main() |

Totals: 544 files, 182122 lines (wc -l style newline count).

## Raw automatic lists (before hand checks)

Section 2 line counts compared: 350; over 10 % off (raw, includes false hits on page numbers such as "(06)"): 5.
Backticked identifiers in sections 2-5 that occur nowhere in program code: 166 (of which 127 sit in a removed/renamed sentence).
Public classes not named on any page that maps their file: 269; public top-level functions of 25+ lines in files of 150+ lines not named: 39.

All public classes not named on their owning page (file: class (lines) [pages]; `+` = named on some other page):

- action_plugins/axis_delta/__init__.py: AxisDeltaData (80), AxisDeltaFunctor (43), AxisDeltaModel (33)
- action_plugins/axis_pair.py: AxisRef (28), AxisView (18)
- action_plugins/chain/__init__.py: ChainData (71), ChainFunctor (45), ChainModel (58)
- action_plugins/change_mode/__init__.py: ChangeModeData (130), ChangeModeFunctor (71), ChangeModeModel (79), ChangeType (22)
- action_plugins/condition/__init__.py: ConditionData (125), ConditionFunctor (51)
- action_plugins/condition/comparator.py: AbstractComparator (14), AbstractComparatorModel (26), DirectionComparator (29), DirectionComparatorModel (21), PressedComparator (37), PressedComparatorModel (25), RangeComparator (43), RangeComparatorModel (36)
- action_plugins/condition/condition.py: AbstractCondition (207), AbstractState (27), CurrentInputCondition (30), JoystickCondition (241), KeyboardCondition (83), LogicalDeviceCondition (118), VJoyCondition (145)
- action_plugins/description/__init__.py: DescriptionData (57), DescriptionFunctor (14), DescriptionModel (37)
- action_plugins/double_tap/__init__.py: DoubleTapData (89), DoubleTapFunctor (141), DoubleTapModel (46)
- action_plugins/dual_axis_deadzone/__init__.py: DualAxisDeadzoneData (152), DualAxisDeadzoneFunctor (49), DualAxisDeadzoneModel (108)
- action_plugins/hat_buttons/__init__.py: DirectionalButton (80), HatButtonsData (108), HatButtonsFunctor (18), HatButtonsModel (62)
- action_plugins/load_profile/__init__.py: LoadProfileData (70), LoadProfileFunctor (37), LoadProfileModel (36)
- action_plugins/macro/__init__.py: AbstractActionModel (13), ActionListModel (112), JoystickActionModel (92), KeyActionModel (41), LogicalDeviceActionModel (118), MacroFunctor (42), MacroRepeatData (4), MacroRepeatModes (19), MouseButtonActionModel (42), MouseMotionActionModel (27), PauseActionModel (20), RawStepModel (12), VJoyActionModel (111)
- action_plugins/map_to_keyboard/__init__.py: MapToKeyboardData (72), MapToKeyboardFunctor (25), MapToKeyboardModel (53)
- action_plugins/map_to_logical_device/__init__.py: MapToLogicalDeviceData (197), MapToLogicalDeviceFunctor (128), MapToLogicalDeviceModel (133)
- action_plugins/map_to_mouse/__init__.py: MapToMouseData (91), MapToMouseFunctor (155), MapToMouseMode (13), MapToMouseModel (100)
- action_plugins/map_to_vjoy/__init__.py: MapToVjoyData (141)+, MapToVjoyFunctor (83), MapToVjoyModel (123)
- action_plugins/map_to_xbox/__init__.py: MapToXboxData (108), MapToXboxFunctor (32), MapToXboxModel (154)
- action_plugins/merge_axis/__init__.py: MergeAxisData (129), MergeAxisFunctor (69), MergeAxisModel (114)
- action_plugins/pause_resume/__init__.py: PauseResumeData (60), PauseResumeFunctor (18), PauseResumeModel (36), PauseResumeType (19)
- action_plugins/play_sound/__init__.py: PlaySoundData (78), PlaySoundModel (51)
- action_plugins/reference/__init__.py: ReferenceData (59), ReferenceFunctor (9), ReferenceModel (99)
- action_plugins/response_curve/__init__.py: ControlPoint (50), DeadzoneIndex (8), ResponseCurveData (134), ResponseCurveFunctor (21), ResponseCurveModel (295)
- action_plugins/root/__init__.py: RootData (62)+, RootFunctor (13), RootModel (18)
- action_plugins/run_command/__init__.py: RunCommandData (67), RunCommandFunctor (31), RunCommandModel (54)
- action_plugins/send_osc/__init__.py: SendOscFunctor (65), SendOscModel (159)
- action_plugins/smart_toggle/__init__.py: SmartToggleData (63), SmartToggleFunctor (73), SmartToggleModel (33)
- action_plugins/split_axis/__init__.py: SplitAxisData (73), SplitAxisFunctor (35), SplitAxisModel (35)
- action_plugins/tempo/__init__.py: TempoData (85), TempoFunctor (153), TempoModel (45)
- action_plugins/text_to_speech/__init__.py: TextToSpeechData (86), TextToSpeechModel (99)
- dill/__init__.py: AxisMap (4), DeviceActionType (12)
- gremlin/code_runner.py: VirtualButton (40)
- gremlin/device_library.py: LibraryDamaged (2)
- gremlin/diagnostics.py: Plan (15)
- gremlin/error.py: KeyboardError (5), MissingImplementationError (5), MouseError (5), PluginError (5), ProfileError (7)+, VJoyBusyError (10), VJoyConcurrencyError (5), VJoyError (5)+
- gremlin/event_helpers.py: ButtonReleaseEntry (5), ModeMatch (6), RegistryKey (19), ReleaseMode (5)
- gremlin/fsm.py: FiniteStateMachine (82), Transition (13)
- gremlin/hidhide_driver.py: DEVPROPKEY (2), HIDD_ATTRIBUTES (7), HIDP_CAPS (19), SP_DEVICE_INTERFACE_DATA (7), SP_DEVINFO_DATA (7)
- gremlin/input_cache.py: DeviceMapping (35)
- gremlin/input_tester/compare.py: Row (50)+, Verdict (7)
- gremlin/input_tester/devices.py: HidDevice (5), LiveValues (11), OpenResult (10), SeenDevice (22), XINPUT_GAMEPAD (10), XINPUT_STATE (2)
- gremlin/input_tester/logfiles.py: Follower (13), LogSource (8), Tail (5)
- gremlin/library_undo.py: Steps (112)+
- gremlin/macro.py: AbstractAction (41), AbstractRepeat (38), CountRepeat (29), HoldRepeat (27), MouseButtonAction (52), MouseMotionAction (39), PauseAction (33), ToggleRepeat (27), VJoyAction (104)
- gremlin/modules/device_class.py: DeviceClass (4)
- gremlin/modules/folders_move.py: MoveError (2)
- gremlin/modules/module_file.py: ModuleFileDamaged (7)
- gremlin/notice.py: NoticeTimer (31)
- gremlin/osc_feedback.py: OscFeedback (347)
- gremlin/profile.py: AbstractVirtualButton (24), DeviceInfo (25), DraftOutdated (4)
- gremlin/run_scope.py: Handle (14)+, Stage (10)+, Timer (65)+
- gremlin/sendinput.py: ConstantVelocity (14), IncreasingVelocity (39), MotionSource (11), Vector2 (49)
- gremlin/signal.py: Signal (70)
- gremlin/spline.py: AbstractCurve (132), CubicBezierSpline (207), CubicSpline (127), PiecewiseLinear (74)
- gremlin/swap_devices.py: ProfileDeviceInfo (4), SameDevice (2), SwapDevicesResult (10)
- gremlin/tts.py: TTSQueueMode (4)
- gremlin/types.py: ActionActivationMode (40), ActionProperty (14), AxisButtonDirection (24), AxisMode (17), AxisNames (25), ConditionType (56), DataCreationMode (5), DataInsertionMode (5), DeviceType (20), HatDirection (29), LogicalOperator (35), MouseButton (24), Point2D (55), ScriptVariableType (25), ValueRange (47), VjoyInput (7)
- gremlin/ui/click_trace.py: ClickTrace (190)
- gremlin/ui/control_layout.py: LayoutItem (21)
- gremlin/ui/debug_mode.py: DebugMode (12)
- gremlin/ui/device_map_options.py: DeviceMapLibraryOption (9)
- gremlin/ui/hardware_layout.py: HardwareLayoutItem (29)
- gremlin/ui/highlight_option.py: HighlightSpeedModel (26)
- gremlin/ui/input_pairing.py: MappedAxisModel (3), MappedHatModel (3)
- gremlin/ui/keyboard_layout.py: KeyItem (31)
- gremlin/ui/module_model.py: ModuleRow (60)
- gremlin/ui/module_pairing.py: ModulePairAxisModel (3), ModulePairButtonModel (3), ModulePairDeviceModel (121)+
- gremlin/ui/option.py: BaseMetaConfigOptionWidget (10), OptionPointer (6)
- gremlin/ui/osc_layout.py: OscLayoutItem (31)
- gremlin/ui/osc_option.py: OscModuleSetupLink (19)
- gremlin/ui/output_modules.py: OutputModuleDevices (330)
- gremlin/ui/profile.py: LabelValueSelectionModel (80)
- gremlin/ui/script.py: AbstractVariableModel (34), BoolVariableModel (18), FloatVariableModel (26), IntegerVariableModel (26), KeyboardVariableModel (25), LogicalDeviceModel (45), ModeVariableModel (18), PhysicalInputVariableModel (33), SelectionVariableModel (22), StringVariableModel (18), VirtualInputVariableModel (53)
- gremlin/ui/shell_option.py: StatusResetModel (3)
- gremlin/ui/trace_model.py: TraceLines (46), TraceSwitch (18), TraceTree (177), TraceView (341)
- gremlin/ui/window_titles.py: TitleBars (30)
- gremlin/ui/xbox_viewer.py: XboxLiveThrottle (132), XboxMappedButtonModel (3), XboxMappedHatModel (3)
- gremlin/unknown_action.py: UnknownActionData (88), UnknownActionModel (16), UnknownFunctor (8)
- gremlin/updater.py: Asset (5)
- gremlin/user_script.py: AbstractVariable (59), BoolVariable (30), CallbackRegistry (40), FloatVariable (52), IntegerVariable (46), JoystickDecorator (42), JoystickPlugin (27), KeyboardPlugin (24), LogicalDeviceVariable (124), ModeVariable (28), PhysicalInputVariable (102), ScriptVariableRegistry (64), SelectionVariable (55), StringVariable (32)
- gremlin/windows_event_hook.py: KBDLLHOOKSTRUCT (10), KeyEvent (26), MSLLHOOKSTRUCT (10), MouseEvent (5)
- joystick_gremlin.py: StartupError (6)
- vigem/vigem_commons.py: VIGEM_ERRORS (12), XUSB_BUTTON (16), XUSB_REPORT (10)
- vigem/xbox.py: XboxError (3)+, XboxTarget (45)+
- vjoy/vjoy.py: AxisCode (11), HatType (5), VJoy (403), VJoyStateCache (57)
- vjoy/vjoy_interface.py: VJoyInterface (89), VJoyState (8)
