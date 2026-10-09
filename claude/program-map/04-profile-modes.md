# Profile and modes

Mapped against the code at 4f6bdfa4 (6 Oct). Line numbers drift; re-check them before a step starts.

## 1. Purpose

The profile is the file you open and save: the modes, the actions on every input, the profile settings and the list of scripts. Modes let one button do different things; a mode can inherit what it leaves empty from its parent, and the Change Mode action switches modes while the profile runs. This subsystem also covers New / Load / Save / Save As / Recent / auto-load, the unsaved-changes guard, Swap Devices and user scripts.

## 2. Files

Python
- `gremlin/profile.py` (1913 lines): `Profile` (load, save, unsaved check, input snapshots for Undo/History), `Settings` (startup mode, macro delay, vJoy as input, vJoy initial values), `Library` (every action by id; clone, pick lists, drop unused/invalid), `InputItem` / `InputItemBinding` (an input in a mode and its root actions), virtual buttons, `DeviceDatabase` (device names by id), `ModeHierarchy` (mode tree: add, rename, delete, parent), `ScriptManager` (the profile's script list).
- `gremlin/base_classes.py` (682): `AbstractActionData` (id, label, activation mode, children per selector, to_xml/from_xml, `is_valid` from Error feedback), `AbstractFunctor` (runtime side, pulse helper), `UserFeedback`, `Value`.
- `gremlin/tree.py` (250): `TreeNode`, the generic tree under the mode hierarchy (parent/children, cycle check, depth-first walks).
- `gremlin/mode_manager.py` (368): run-time mode stack (`ModeManager`: switch, previous, unwind, cycle, temporary, rename, drop), `ModeSequence` (Cycle), `resolve_start_mode`, last mode per profile (kept in memory while running, `flush_last_modes`), option `action/change-mode/resolution-mode`.
- `gremlin/ui/profile.py` (1399): QML models: `InputItemModel` and `InputItemBindingModel` (bindings on the Configuration page), `ModeListModel`, `ModeHierarchyModel` (Manage Modes), `rename_mode` / `delete_mode` (the one path every rename/delete uses), `StartupModeModel`, `ProfileSettingsModel` (macro delay), `VJoyInputOrOutputModel`, `OutputVJoyListModel`, `OutputVJoyInitialValuesModel`, `ProfileDeviceListModel` (Swap Devices list).
- `gremlin/ui/backend.py` (704): `Backend` (new, load, save, save as, recent, forget, last profile at start, auto-load, unsaved flag, Run/Stop entry, toolbar mode pick), `UIState` (the mode, device, input, tab and room shown).
- `gremlin/swap_devices.py` (162): moves every binding, action reference and script variable from one device id to another.
- `gremlin/ui/tools.py` (89; `swapDevices` 64-89): the QML slot for Swap Bindings.
- `gremlin/user_script.py` (1426): `Script` (loads the .py, its variables, load errors), variable types, callback and periodic registries, decorators, plugins giving scripts `joy` / `vjoy` / `keyboard`.
- `gremlin/ui/script.py` (451): `ScriptListModel` (add, remove, rename) and one QML model per variable type.
- `gremlin/config.py` (`get_profile`, `get_profile_with_regex` 516-551): auto-load program-to-profile matching.
- `gremlin/process_monitor.py` (131): the thread that reports the focused program (feeds auto-load).
- `joystick_gremlin.py` (`process_cmd_args` 978-1001; settings registered 594-598, 750): `--profile` or last profile at start.
- `action_plugins/load_profile/__init__.py` (Load Profile action, 50-80): loads another profile from a running profile.

QML / JS
- `qml/Main.qml`: File menu, unsaved guard (`guardUnsavedChanges` 706), `saveProfileChecked` 528 (asks about unfinished actions), Save As / Open file dialogs 817-885, Recent 901-920, toolbar Mode box and Manage Modes button 1140-1202, `*` in the title (1.5 s timer, 27-45), footer status, `onClosing` 1366, "Last profile didn't open" 1300.
- `qml/main_commands.js`: menu/shortcut entries (file.new/load/save/saveAs/exit, tools.swapDevices, Manage Modes).
- `qml/DialogManageModes.qml` (249): add, rename, Inherits from, delete (asks with binding count).
- `qml/ProfileSettings.qml` (256): Startup Mode, Macro Default Delay, vJoy Behavior, vJoy Initial Values.
- `qml/ScriptManager.qml` (248), `qml/ScriptConfiguration.qml` (374): Scripts page and a script's variables.
- ~~`qml/DialogSwapDevices.qml` (164): Swap Devices window.~~ Removed 2026-10-08 (D-10-SWAP); the Device Library replaces it (10).
- `qml/OptionProfileAutoLoading.qml` (237): Options › Profiles › Auto-load list.
- `qml/help_topics.js`: topics Profiles, What is saved where, Run and status, Modes, Change Mode, Load Profile, Profile Settings, Scripts, History (Swap Devices replaced by the Device Library topic, 2026-10-08).

Tests (main ones)
- `test/unit/test_profile.py`, `test_tree.py`, `test_modes.py`, `test_mode_hierarchy_model.py`, `test_profile_settings.py`, `test_profile_unsaved.py`, `test_profile_save_safe.py`, `test_profile_unused_actions.py`, `test_profile_missing_child_action.py`, `test_library_invalid_children.py`, `test_recent_profiles.py`, `test_load_and_rename_safety.py`, `test_autoload_and_mode_prompts.py`, `test_audit_profile.py`, `test_audit2_modes.py`, `test_audit3_modes.py`, `test_audit_saving.py`, `test_audit2_saving.py`, `test_audit2_coverage.py`, `test_startup_messages.py`, `test_write_less.py`, `test_mode_refresh_and_add_key.py`, `test_swap_devices.py`, `test_audit3_screens.py` (Swap list), `test_user_script.py`, `test_user_script_load_errors.py`, `test_data_safety.py`.
- `test/action_interaction/test_modes.py` (mode stack at run time), `test/integration/test_e2e_user_script.py`, `test_e2e_profile_simple.py`.

## 3. What it owns

In memory
- `Backend.profile`: the one open `Profile`. Mirrored in `shared_state.current_profile`, which every other part reads (set at `backend.py:239` and `:300` only).
- Inside the profile: `inputs` (device id → list of `InputItem`, one per input per mode), `library` (action id → action, plus `_copied_from` for editor drafts), `settings`, `modes` (tree with a hidden root `""`), `scripts`, `device_database`, `fpath`, `_saved_snapshot` (the XML text as of the last load or save; the unsaved check compares against it).
- Not in the profile object but saved with it: the Logical Device and OSC device rows (singletons `LogicalDevice()` / `OscDevice()`, reset by every `Profile()` constructor, `profile.py:859-860`).
- `ModeManager._mode_stack` (singleton): the run-time mode history. Also changed by the toolbar Mode box while stopped.
- `mode_manager._pending_last`: last mode per profile, kept in memory while running.
- `UIState._current_mode`: the mode shown in the toolbar and edited.
- User script globals: `callback_registry`, `periodic_registry`, `Script.variable_registry`, and the script modules themselves.
- `Backend._autoload_held` (auto-load target held back by unsaved edits), `Backend._action_state` (expanded/collapsed panes).

Files
- The profile XML (`profiles\<name>.xml`, version 14, UTF-8 with BOM), written only by `Profile.to_xml` through `module_file.write_text` (temp file then swap). Each save with a change also records a History entry (`history_profile.record_save`).

Settings keys (program settings, not the profile)
- `global/internal/last-profile`, `global/internal/recent-profiles` (max 5): written by `Backend._record_profile_use` (load and save) and `forgetProfile`.
- `global/internal/last-mode-per-profile` (profile path → mode): written by `ModeManager._store_last_mode`, `_rewrite_stored_name`, `flush_last_modes`.
- `action/change-mode/resolution-mode` (Oldest / Newest): registered in `mode_manager.py:356`.
- Read only here: `profile/automation/enable-auto-loading`, `entries-auto-loading`, `remain-active-on-focus-loss`; `global/general/device-change-behavior`; `action/macro/default-delay`.

Who else changes profile data (not single-owner)
- Configuration page / binding catalog, Logical Device page, Keyboard page, OSC page: edit `inputs` and `library` directly.
- Auto Mapper (`gremlin/ui/tools.py:createMappings`), Device Pack import (adds inputs, actions, modes, Logical Device rows), History Restore (`put_input`), Undo stacks (`input_snapshot` / `put_input`).
- `hardware_profile` (Delete Device saves the profile at once; output module save also saves the profile).
- `device_initialization`, `modules/runtime.py`, `ui/logical_layout.py` read `settings.vjoy_as_input`.
- `code_runner` reads modes, settings, scripts at Run and writes vJoy initial values.

## 4. Entry points

| User action / trigger | QML / caller | Handler | Python function |
|---|---|---|---|
| File › New Profile (Ctrl+N) | `Main.qml:499 requestNewProfile` | `guardUnsavedChanges` → `leaveDisplayThen` | `Backend.newProfile` 502: Stop, new `Profile()`, `mark_clean`, `profileChanged` |
| File › Load Profile… (Ctrl+O) | `_loadProfileFileDialog` 868 | `guardUnsavedChanges` | `Backend.loadProfile` 570 → `_load_profile` 659 → `_read_profile` 643 → `Profile.from_xml` 862 |
| File › Recent › file | `Main.qml:599 loadRecent` | same guard | `Backend.loadProfile` |
| File › Save Profile (Ctrl+S) | `saveCurrentProfile` 505 | no path → Save As; else `saveProfileChecked` (asks if unfinished actions) | `Backend.unfinishedActions` 512, `Backend.saveProfile` 522 → `Profile.to_xml` 904 |
| File › Save Profile As… | `openSaveAs` 518, `_saveProfileFileDialog` 817 | `saveProfileChecked` | `Backend.saveProfile` (sets `fpath` only after the write) |
| Quit / close window / restart / install update | `quitGremlin` 686, `onClosing` 1366 | tool windows, panes, then `guardUnsavedChanges(..., true)` | `deactivateThenQuit` → Stop → `Qt.quit`; `flush_last_modes` on Stop |
| Program start | `joystick_gremlin.py:process_cmd_args` 978 | `--profile` path, else last profile | `Backend.loadProfile` or `Backend.openLastProfile` 577 (failure → `lastProfileFailed` → "Forget It" → `forgetProfile` 590) |
| Focused program changes (auto-load) | `ProcessMonitor.process_changed` | `Backend._active_process_changed_cb` 357 | `config.get_profile_with_regex`, `loadProfile`, `activate_gremlin` |
| Load Profile action fires while running | action functor | `load_profile/__init__.py:55` | waits if unsaved, skips missing file, `Backend.loadProfile`, Stop, Run |
| Title `*` | Timer 1.5 s while window active, and after load/save | `refreshProfileDirty` | `Profile.has_unsaved_changes` 1216 (rebuilds the full XML) |
| Toolbar Mode box | `Main.qml:1162` | `backend.selectMode` | `Backend.selectMode` 322 → `UIState.setCurrentMode`, `ModeManager.switch_to` (also while stopped) |
| Manage Modes: Add Mode | `DialogManageModes.qml:142` | `nameTaken` check | `ModeHierarchyModel.newMode` 909 → `ModeHierarchy.add_mode` 1604 |
| Manage Modes: rename (pencil) | `:183` | `nameTaken(value, name)` | `ModeHierarchyModel.renameMode` 917 → `ui/profile.rename_mode` 841 → `ModeHierarchy.rename_mode` 1658, `ModeManager.rename_mode` 235, `EventHandler.rename_mode`, `signal.modeRenamed`, `modesChanged` |
| Manage Modes: Inherits from | `:213` | | `ModeHierarchyModel.setParent` 936 → `ModeHierarchy.set_parent` 1706 |
| Manage Modes: delete (trash, asks with binding count) | `:245`, `confirmDelete` 39 | `bindingCount` | `ModeHierarchyModel.deleteMode` 928 → `ui/profile.delete_mode` 857 → `ModeHierarchy.delete_mode` 1625, `ModeManager.drop_mode` 252, `EventHandler.drop_mode`, `signal.modeDeleted` |
| Profile Settings › Startup Mode | `ProfileSettings.qml:58` | | `StartupModeModel.currentSelectionIndex` setter 1094 |
| Profile Settings › Macro Default Delay / Use the Options default | `:93`, `:113` | | `ProfileSettingsModel.macroDefaultDelay` / `macroDelayFromOptions` 1312-1341 |
| Profile Settings › vJoy Behavior switch | `:145` | | `VJoyInputOrOutputModel.setData` 1151: sets `vjoy_as_input`, emits `signal.profileChanged` and `EventListener.device_change_event` |
| Profile Settings › vJoy Initial Values | `:251` | | `OutputVJoyInitialValuesModel.setData` 1269 → `Settings.set_initial_vjoy_axis_value` |
| Configuration page: add / delete / reorder binding | catalog / `InputItemModel` | | `newActionSequence` 688, `deleteActionSequnce` 695 (+ `drop_unused_actions`), `dropAction` 710 |
| Configuration page: edit actions in a binding | `InputItemBindingModel` | | `move_action` 392, `remove_action` 448 (+ `Library.remove_unused`), `append_action` 484, `_set_behavior` 587 |
| Configuration page: open an input | `backend.getInputItem` 451 | | `Profile.get_input_item(..., create_if_missing=True)` 993 (empty items are not saved) |
| Undo / Redo, History Restore, Device Pack | other subsystems | | `Profile.input_snapshot` 1091, `put_input` 1126, `add_inputs` 1058, `drop_inputs` 1174 |
| ~~Tools › Swap Devices… / card "Swap Device…"~~ (removed 2026-10-08, D-10-SWAP) | Device Library › Swap with Another Stick… (10 S26) | `deviceLibrary` model | `library_swap.swap` → `swap_devices.swap_devices` (with limits); `library_profiles.Batch` |
| Scripts › Add Script | `ScriptManager.qml:37` | | `ScriptListModel.addScript` 406 → `ScriptManager.add_script` 1816 → `Script()` (runs the script file) |
| Scripts › rename / remove (asks) / configure variables | `ScriptManager.qml:205`, `:231`; `ScriptConfiguration.qml` | | `renameScript` 419, `removeScript` 412, variable models' setters |
| Run | toolbar / tray | `Backend.toggleActiveState` 417 → `activate_gremlin(True)` | `CodeRunner.start(profile, ui_state.currentMode)`: scripts reloaded (`_setup_user_scripts`), mode lookup built, `ModeManager.switch_to(start mode)`, vJoy initial values written |
| Stop | toolbar / tray / load / new / auto-load | `activate_gremlin(False)` | `CodeRunner.stop` (flushes last mode) |
| Change Mode action, Cycle, Temporary, Previous, Unwind | running action | | `ModeManager.switch_to` 295, `cycle` 266, `temporary` 345 / `leave_temporary` 349, `previous` 276, `unwind` 287 |
| Mode changed (signal) | `ModeManager.mode_changed` | `Backend._on_mode_changed` 317 | toolbar follows; `CodeRunner._refresh_on_mode_change` (axis refresh option) |
| Profile changed (Backend signal) | load, new | `ModeManager.reset`, `UIState.setCurrentMode`, `_profile_change_handler` (in that order, 257-261) | `shared_state.current_profile` set last |
| Profile changed (global `signal.profileChanged`) | swap, Auto Mapper, vJoy Behavior switch, backend | models reset: `ModeListModel`, `StartupModeModel`, `ProfileSettingsModel`, `ProfileDeviceListModel`, vJoy models; `UIState.clearKeyboardInput` | |
| Hourly safety flush | `deferred_write.schedule("last-mode", ...)` | | `flush_last_modes` |

## 5. Talks to

| Other subsystem | Calls out (this → it) | Called by (it → this) |
|---|---|---|
| Run lifecycle (`code_runner`, `event_handler`) | `activate_gremlin`, `ModeManager.rename_mode/drop_mode` → `EventHandler.rename_mode/drop_mode`; `_profile_running` reads `EventListener.gremlin_active`; `_known_modes` reads `EventHandler.known_modes` | `CodeRunner.start` reads modes, settings, scripts, calls `resolve_start_mode`, `switch_to`, `flush_last_modes`; `EventListener` / `EventHandler` / `macro` / `osc` / `map_to_logical_device` / `text_to_speech` read `ModeManager().current.name` |
| Actions (`action_plugins/*`) | `PluginManager.tag_map` to build actions on load; `rename_mode` renames Change Mode `_target_modes` in place | Change Mode calls `ModeManager`; Load Profile calls `Backend.loadProfile` / `activate_gremlin`; every action is an `AbstractActionData` |
| Configuration page / binding catalog, Logical Device page, Keyboard, OSC | `signal.modeRenamed` / `modeDeleted` / `modesChanged` / `profileChanged` | edit `inputs` / `library`, `input_snapshot` / `put_input`, `drop_inputs`, `clone_action`, `pick_list` |
| History | `history_profile.record_save` on every changed save | `history_model._restore_input` → `put_input` |
| Device Pack (`device_pack`) | | `add_inputs`, `remap_action_ids`, `rename_mode` / `delete_mode` for Undo Import, `Library.from_xml` |
| Auto Mapper | | `Tools.createMappings` edits the open profile, emits `profileChanged` |
| Module files (`modules/module_file`, `hardware_profile`) | `module_file.write_text` (atomic save) | Delete Device and output-module save call `Profile.to_xml` |
| Output layer (`gremlin.modules.output`) | scripts' `vjoy` = `output.ScriptVJoy`; `VirtualInputVariable.remap` → `output.write_vjoy` | `code_runner._refresh_axes` writes initial values via `output.write_vjoy_axis_linear` |
| Input layer (`gremlin.modules.inputs`) | scripts' `joy` / `keyboard` = `inputs.ScriptJoystick` / `ScriptKeyboard` | |
| Devices (`device_initialization`) | `DeviceDatabase.update_for_uuids` (`device_for_uuid`), vJoy lists for Profile Settings, `physical_devices` for `UIState` | `device_initialization.input_devices/output_vjoy_devices` read `vjoy_as_input` |
| Logical Device / OSC singletons | reset in `Profile()`, filled in `from_xml`, written in `_xml_text` | |
| Settings (`config.Configuration`, `deferred_write`) | last profile, recent, last mode, resolution mode, auto-load | Options window edits auto-load and resolution mode |
| Process monitor | | `process_changed` → auto-load |
| Main window (QML) | `profileChanged`, `windowTitleChanged`, `recentProfilesChanged`, `lastProfileFailed`, `saveNoted`, `reloadUi`, `reloadCurrentInputItem` | all slots in section 4 |
| Logging / notices | `display_error`, `showNotification`, `log_once`, `persist_log`, `live_debug.trace` | |

## 6. Threads and timers

- All profile, mode-tree, Manage Modes, Profile Settings, Scripts-page and save/load work runs on the main (Qt) thread.
- `ModeManager` has no lock. Writers are on the main thread (UI, Change Mode, timer actions since ACT20). Readers on other threads: `EventListener` tags events with `ModeManager().current.name` from its own thread (`event_handler.py:209`, `:330`-`:510`), macro threads (`macro.py:604-620`, `:804`).
- `user_script.PeriodicRegistry`: one "user script timers" thread per Run via `threads.start` (`user_script.py:136`); stop asks with a flag and waits at most 2 s (`:150`). Its loop uses `time.monotonic()` and `time.sleep()` directly (`:208`, `:218`, `:229`, `:237`), not `gremlin.clock`.
- `AbstractFunctor._pulse_event` (`base_classes.py:612-657`): on the main thread a 50 ms `QTimer.singleShot` (`flush_pulses` sends pending ones at Stop); off the main thread `time.sleep(0.05)`.
- Last mode while running: `deferred_write.schedule("last-mode", flush_last_modes, 3_600_000)` (one hour safety net); saved for real on Stop and quit.
- Settings writes (`Configuration.set`) are deferred about 1 s by `deferred_write`.
- `Main.qml:35` Timer, 1.5 s, while the window is active: calls `profileContainsUnsavedChanges`, which rebuilds the whole profile XML on the main thread.
- Process monitor thread (owned by the process-monitor code) emits `process_changed`; the handler runs on the main thread.
- Loading a profile and adding a script run the script's top-level Python code on the main thread (`user_script.py:454-456`, `:683`), with no time limit. [out of date: since batch 2 (GL-040, D-04-Q13-TIMELIMIT) it runs on a worker thread with a time limit]

## 7. Rule breaks

| # | Rule | Where | What | Status |
|---|---|---|---|---|
| R1 | Single owner | `ui/backend.py:257-261` vs `:300` | `ModeManager.reset` and `setCurrentMode` are connected before `_profile_change_handler`, so on Load / New they run while `shared_state.current_profile` still points at the old profile. The start mode is worked out from the old profile. | SUSPECTED (Qt calls same-thread slots in connection order; not run) |
| R2 | Single owner | `profile.py:450-456`, `:513-516`, `:540-545`, `:730-737` | `Library` decides "in use" by looking up `shared_state.current_profile` instead of its own profile (also in `system-maps.md` § 2). | CONFIRMED |
| R3 | Single owner | `profile.py:859-860`, `:1248-1325` | Logical Device and OSC rows are saved in the profile but live in global singletons; any `Profile()` (also a throwaway one) wipes them. | CONFIRMED |
| R4 | Duplicated logic | `profile.py:498-565` (`Library.remove_unused`) and `:1201-1214` (`Profile.drop_unused_actions`) | Two "remove actions nothing uses" paths; `InputItemBindingModel.remove_action` uses the first (`ui/profile.py:478`), `deleteActionSequnce` the second (`:704`). | CONFIRMED |
| R5 | Duplicated logic | `ModeHierarchy.add_mode` 1610 (exact match) vs `ModeHierarchyModel.nameTaken` `ui/profile.py:897` (ignores case and spacing) | Name rule lives in the UI model only; Device Pack, tests and scripts adding modes skip it. | CONFIRMED |
| R6 | Thread rules (time via `gremlin.clock`) | `user_script.py:208`, `:218`, `:229`, `:237` | Periodic loop reads and sleeps on `time` directly. | CONFIRMED |
| R7 | Thread rules (time via `gremlin.clock`) | `base_classes.py:656` | `time.sleep(0.05)` for an off-main-thread pulse (already item I in `system-maps.md` § 3). | CONFIRMED |
| R8 | Hang-proof (bounded work on main thread) | `user_script.py:454-456`, `:683`; `profile.py:1885` | A script's top-level code runs on the main thread when a profile loads or a script is added; an endless loop there freezes the program. | SUSPECTED |
| R9 | Thread safety | `event_handler.py:209`, `:330`; `macro.py:604-620` | `ModeManager._mode_stack` read from listener/macro threads, written on the main thread, no lock. | SUSPECTED (low risk) |
| R10 | Layer rule | `event_handler.py:240`, `:330` | The hardware listener (bottom layer) asks the mode manager (profile layer) for the mode to stamp on events. | SUSPECTED (design question) |
| R11 | Layer rule | `action_plugins/load_profile/__init__.py:61-80` | An action running inside the event pipeline calls the UI `Backend` to load a profile and Stop/Run the runner that is running it. | SUSPECTED |
| R12 | Layer rule | `ui/profile.py:1162` | The Profile Settings vJoy switch emits `EventListener.device_change_event`, a hardware signal, from the UI. With Device change behavior Disable or Reload this stops or restarts a running profile. | CONFIRMED (code); effect SUSPECTED |
| R13 | Layer rule | `ui/profile.py:1121`, `:1127`, `:1220` | Profile Settings lists vJoy devices from `device_initialization` (the input side's device cache), not the vJoy output modules. | SUSPECTED |
| R14 | Side effect in a check | `profile.py:954` | `_xml_text` (used by the unsaved check every 1.5 s) calls `device_database.update_for_uuids`, which reads connected devices and changes the profile. | CONFIRMED |
| R15 | Dead code | `ui/backend.py:648`, `:656-657` | `profile_was_converted = new_profile.from_xml(...)`; `from_xml` returns None, so the re-save never runs. Tracker AU-65 lists a dead "converted" branch as fixed. | CONFIRMED |
| R16 | Leftover debug output | `base_classes.py:287` | `print(...)` for an invalid node. | CONFIRMED |

## 8. Behaviour spec

### Profile file: New, Load, Save, Save As, Recent

- S1. It should hold the modes, the actions on every input, the Profile Settings and the list of scripts, and save them only on Save / Save As. [help: Profiles] [help: What is saved where] [glossary: Profile]
- S2. It should save the Logical Device and OSC rows and the device names list in the same file. [user confirmed 2026-10-06; was code only]
- S3. It should open File › New Profile, Load Profile…, Recent, Save Profile and Save Profile As… with Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Shift+S. [help: Profiles]
- S4. It should ask Save / Discard / Cancel before New, Load, Recent and quit only when there are unsaved changes; with nothing changed it asks nothing. [help: Profiles] [test-plan: F-06a, WORKFLOW-HANDS-ON] [tracker: C1]
- S5. It should stop a running profile before New or Load. [user confirmed 2026-10-06; was code only]
- S6. It should give a new profile the title "Untitled" and one mode, "Default", and count it as having nothing to lose. [tracker: C2] [test: test_profile_unsaved.py::test_a_new_profile_marked_clean_has_nothing_to_lose]
- S7. It should show `*` in the window title while there are unsaved changes, and the file name (not the full path) otherwise. [test-plan: WORKFLOW-HANDS-ON] [tracker: C2]
- S8. It should count only real edits as unsaved: a file saved by an older build that loads with new default values is not unsaved. [test-plan: F-06] [test: test_profile_unsaved.py::test_freshly_loaded_older_file_is_not_unsaved]
- S9. It should not count an open editor draft as unsaved work. [test-plan: G-LIBLEAK] [test: test_profile_unused_actions.py::test_an_open_draft_is_not_unsaved_work]
- S10. It should send Save on a never-saved profile to Save As. [test-plan: F-04b]
- S11. It should, before a save, list unfinished actions (with their first error) and let the user cancel or "Save without them"; a save leaves them out of the file and out of the open profile. [tracker: N1] [test: test_data_safety.py::test_unfinished_actions_are_named_with_their_first_error] [test: test_library_invalid_children.py::test_library_save_removes_every_invalid_child]
- S12. It should never delete unfinished actions when it only checks for unsaved changes. [test: test_library_invalid_children.py::test_library_check_does_not_drop_unfinished_actions]
- S13. It should write the file safely (temporary file, then swap), so a crash mid-save leaves the old file whole, byte-for-byte as before (UTF-8 with BOM). [test-plan: G-PROFATOMIC] [test: test_profile_save_safe.py::test_a_failed_save_leaves_the_old_profile_whole]
- S14. It should write only the actions an input uses; deleted, replaced and draft actions stay in memory (for Undo) but not in the file. [test-plan: G-LIBLEAK] [test: test_profile_unused_actions.py::test_the_file_gets_only_what_inputs_use]
- S15. It should leave the profile on its old file when Save As fails (title and next Ctrl+S unchanged), say "Not written", and add no History entry. [tracker: AU-46] [test: test_audit_saving.py::test_a_failed_save_as_keeps_the_profile_on_its_file] [test: test_audit2_saving.py::test_a_save_that_failed_is_no_history_entry]
- S16. It should show "Saved to the profile." after every successful save and name the written file in the footer. [help: What is saved where] [tracker: C3]
- S17. It should record a History entry for every save that changed something. [help: History] [help: What is saved where]
- S18. It should put a loaded or saved profile at the top of Recent (max 5, one entry per file whatever the case or slashes) and remember it as the last profile. [test-plan: F-03] [test: test_recent_profiles.py]
- S19. It should, when a Recent file is missing, say so and keep the open profile. [test-plan: F-03] [user confirmed 2026-10-06; was code only for "keep the entry"]
- S20. It should open the file dialogs in the profiles folder, filtered to `*.xml`. [user confirmed 2026-10-06; was code only]

### Loading: start-up, damaged and missing files

- S21. It should open the last profile at start; a `--profile` path wins and is read relative to the folder the program was started from. [tracker: APP10] [user confirmed 2026-10-06; was code only for the order]
- S22. It should, when the last profile won't open at start, say why once and offer Forget It (off the start-up and Recent lists; the file stays) or Keep. [tracker: APP17] [test: test_startup_messages.py]
- S23. It should, when any load fails (bad XML, wrong version, unknown action type, missing child action, broken input), show the reason and reopen the profile that was open; only if that fails, open a new empty one and say so. [tracker: B11, ACT15] [test: test_load_and_rename_safety.py::test_failed_load_reopens_the_profile_that_was_open]
- S24. It should not add a profile that failed to load to Recent or make it the last profile. [tracker: ACT15] [test-plan: S-05]
- S25. It should read only profile version 14 and refuse others with a message. [user confirmed 2026-10-06; was code only]
- S26. It should finish loading (refuse with a message, never hang) when an action names a child action that is missing. [test-plan: PROFILE-LOAD-NO-HANG] [test: test_profile_missing_child_action.py]
- S27. It should keep a mode whose parent is unknown, or whose parents loop, as a top-level mode. [test-plan: AUDIT-A-PROFILE, AUDIT2-F-H-REST] [test: test_audit_profile.py::test_a_mode_with_an_unknown_parent_is_kept]
- S28. It should open a profile whose Play Sound or Load Profile file is missing, keep the action with a warning. [tracker: ACT11, AU-14] [test: test_audit_profile.py::test_a_missing_load_profile_file_still_loads]
- S29. It should open a profile whose script can't load (missing file, syntax error, settings that no longer match), keep the script and its saved settings, and show the reason on the Scripts page. [test-plan: SCRIPTS-THAT-CANT-LOAD] [tracker: ACT12] [test: test_user_script_load_errors.py]
- S30. It should add the profile's folder to Python's import path once, in front, keeping the rest in order. [tracker: ACT19]
- S31. It should keep the action order of the file in memory, and keep actions already in the library (Device Pack) before them. [test: test_profile.py::test_library_preserves_action_order] [tracker: G-PACKWIPE]
- S32. It should clear the Keyboard page's selected key and close open action panes when another profile loads. [tracker: AU-90] [test-plan: F-05]

### Auto-load and the Load Profile action

- S33. It should, with Options › Profiles › Auto-load on, load the profile chosen for the program that comes to the front and run it; an exact path match wins, then each ticked pattern (case ignored); blank or invalid patterns match nothing. [help: Options] [test-plan: SAFE-4] [tracker: B1, B2] [test: test_autoload_and_mode_prompts.py]
- S34. It should not reload or restart the profile that is already open when its program comes back to the front. [tracker: AU-38]
- S35. It should never switch over unsaved edits; it says "Auto-load Waited" once per profile. [test-plan: SAFE-4] [tracker: A11] [test: test_autoload_and_mode_prompts.py::test_auto_load_waits_for_unsaved_edits]
- S36. It should, when the matched profile file is missing, say so once and stop the running profile unless Keep running is on. [tracker: AU-95] [test: test_audit2_saving.py::test_a_missing_auto_load_profile_stops_the_open_one]
- S37. It should stop the running profile when a program with no profile comes to the front, unless Keep running when the program loses focus is on. [help: Options] [user confirmed 2026-10-06; was code only]
- S38. It should make the Load Profile action wait (with a notice) over unsaved changes, skip a missing file, otherwise load and run the new profile. [tracker: AU-15] [test: test_audit2_coverage.py::test_load_profile_loads_and_restarts_the_run]

### Modes: the tree and Manage Modes

- S39. It should have at least one mode; the last mode can't be deleted (Delete is disabled). [tracker: AU-19] [test: test_audit_profile.py::test_the_last_mode_stays]
- S40. It should refuse a blank mode name and any name that matches another ignoring capitals and spacing; a mode may change the capitals of its own name. [test-plan: MM-01b] [tracker: B14] [test: test_mode_hierarchy_model.py::test_mode_names_refuse_blank_and_look_alikes]
- S41. It should list modes alphabetically, ignoring capitals (alpha, Bravo, Default). [test-plan: MM-01] [changed 2026-10-07 to follow decision D-04-ALPHA-CASEFOLD]
- S42. It should let a mode inherit from any mode that is not itself or below it; "(none)" makes it top-level. [help: Modes] [user confirmed 2026-10-06; was code only for the allowed list]
- S43. It should use a parent's actions for every input the child mode leaves empty, through any number of levels. [help: Modes] [glossary: Mode]
- S44. It should, on rename, move everything that names the mode: inputs, Change Mode targets (also a running Cycle), script mode settings (also of scripts that failed to load), Startup Mode, the stored last mode, the running mode stack and lookup, the toolbar, Configuration and Logical Device panes and Undo steps, the Button Map labels mode. [test-plan: AUDIT-A-PROFILE, AUDIT2-C-MODES, AUDIT3-TRACE] [tracker: AU-20, AU-82, AU-88, AU-112] [test: test_audit2_modes.py] [test: test_audit3_modes.py]
- S45. It should, before delete, ask and say how many bindings go with the mode. [test-plan: SAFE-4] [tracker: A9] [test: test_autoload_and_mode_prompts.py::test_mode_delete_counts_the_bindings_it_removes]
- S46. It should, on delete, move every child mode up one level, delete the mode's inputs and the actions only they used, set Startup Mode back to Last Active if it named the mode, drop it from the stored last mode, the running stack and lookup, close its panes and Undo steps, and move the toolbar to the first mode. [test-plan: AUDIT-A-PROFILE, AUDIT2-C-MODES] [tracker: AU-01] [test: test_audit_profile.py::test_deleting_a_mode_keeps_every_child] [test: test_profile_unused_actions.py::test_delete_mode_takes_the_actions_with_it] [test: test_modes.py::test_startup_mode_follows_rename_and_delete] [changed 2026-10-09: D-04-LAST-ACTIVE]
- S46a. Manage Modes has **Undo Delete Mode**: while the same profile is open, it brings back the mode deleted last (then the one before), with its bindings, its place in the tree, the child modes that moved up, and Startup Mode if it named it. If it can't, a notice says why. [user decision 2026-10-09: D-04-UNDO-DELETE-MODE; was code only] [test: test_undo_delete_mode.py]
- S47. It should send every rename and delete (Manage Modes, Device Pack Undo Import) through one path. [test-plan: AUDIT3-TRACE] [test: test_audit3_modes.py::test_undo_import_deletes_a_mode_everywhere]
- S48. It should never put an input back (Undo, History Restore) into a mode that no longer exists; it says the mode isn't in the profile. [test-plan: AUDIT2-C-MODES] [test: test_audit2_modes.py::test_nothing_is_put_into_a_deleted_mode]
- S49. It should allow mode edits while running, show the running note, and keep the running profile working with the new names. [test-plan: AUDIT2-C-MODES] [tracker: N18, AU-88]
- S50. It should keep a closed Manage Modes window from reacting to later profile changes. [test-plan: AM-08] [test: test_mode_hierarchy_model.py::test_closed_manage_modes_model_ignores_later_profile_changes]

### Modes at run time

- S51. It should have one Mode box, on the bar under the toolbar (01 S58a; was on the toolbar until D-01-MODE-BAR): the mode you edit is the mode that runs; while running it shows the running mode. [help: Modes] [help: Run and status] [glossary: D10]
- S52. It should, when a profile is loaded (Load, New, auto-load, start-up), put the toolbar in the Startup Mode: a named mode as itself; Last Active as the mode the profile last ran in (only modes used while running count, GL-149), if that mode still exists; with no such record (a new, moved or renamed profile, or one never run) the top row in Manage Modes (alphabetical, ignoring capitals, child modes included). There is no Use Heuristic: a file that says Use Heuristic, or any unknown value, loads as Last Active, and new profiles start on Last Active. [help: Profile Settings] [test-plan: HELP-BUG] [changed 2026-10-09: D-04-LAST-ACTIVE; was Use Heuristic = alphabetically first parentless mode]
- S53. It should start Run in the mode shown on the toolbar (not the Startup Mode). [help: Profile Settings] [test-plan: HELP-BUG]
- S54. It should let the toolbar Mode box switch the running mode while running. [user confirmed 2026-10-06; was code only]
- S55. It should keep the last mode per profile in memory while running and save it on Stop, quit, or at most hourly. [test-plan: WRITE-LESS] [test: test_write_less.py]
- S56. It should switch to a named mode (Switch), swap back to the one before (Previous), step back one (Unwind), go to the next in a list (Cycle) or stay in a mode only while held (Temporary). [help: Change Mode] [test: action_interaction/test_modes.py]
- S57. It should, on Cycle, go to the mode after the current one (the first if the current one isn't in the list), skip deleted modes, and stay put when only the current mode is left; an empty Cycle does nothing. [tracker: ACT3, ACT9, AU-112] [test: test_audit3_modes.py::test_cycle_steps_over_a_deleted_mode]
- S58. It should ignore (and log once) a switch to a mode the profile doesn't have. [tracker: ACT2] [test: action_interaction/test_modes.py::test_switching_to_a_mode_the_profile_does_not_have_is_ignored]
- S59. It should resolve a loop in the mode history by Options › Change Mode resolution (Oldest or Newest), including loops made by temporary modes. [user confirmed 2026-10-06; was code only] [test: test_modes.py::test_cycling] [test: test_modes.py::test_temporaries]
- S60. It should refresh axes on a mode change only while running and only when the option is on. [test: test_mode_refresh_and_add_key.py::test_runner_refreshes_axes_on_mode_change_only_while_listening]
- S61. It should run mode changes from timer actions (Tempo, Double Tap, Smart Toggle) on the main thread. [tracker: ACT20]

### Profile Settings

- S62. It should store Startup Mode, Macro Default Delay, vJoy Behavior and vJoy Initial Values in the profile; they need a save to stick. [help: Profile Settings]
- S63. It should offer Last Active and every mode by name as Startup Mode (no Use Heuristic). [test-plan: PS-01] [changed 2026-10-09: D-04-LAST-ACTIVE]
- S64. It should use Options › Action › Macro › Default delay while "Use the Options default" is ticked (box greyed, showing the Options value); unticking keeps today's value as the profile's own. [test-plan: MACRO-DELAY] [tracker: B27] [test: test_profile_settings.py::test_settings_model_switches_between_options_and_own]
- S65. It should read old profiles' delay of 0.05 as "follow Options". [test: test_profile_settings.py::test_macro_delay_follows_options_unless_set] [user confirmed 2026-10-06; was code only for the 0.05 rule]
- S66. It should treat each vJoy device as an output by default; one switched to input is listed with the physical devices and not offered for Initial Values. [help: Profile Settings] [user confirmed 2026-10-06; was code only for the lists]
- S67. It should set each vJoy axis to its Initial Value when the profile starts (values clamped to -1..1 on load). [help: Profile Settings] [user confirmed 2026-10-06; was code only for the clamp]

### Bindings, inputs and the action library

- S68. It should keep one input item per device, input and mode; an input with no actions is not written to the file. [user confirmed 2026-10-06; was code only]
- S69. It should keep each binding's root action and behaviour ("Treat as"); an axis or hat treated as a button needs its virtual button settings or the profile is refused. [test-plan: AUDIT-A-PROFILE] [user confirmed 2026-10-06; was code only for the refusal]
- S70. It should ask before changing "Treat as" on a binding that has actions. [test-plan: SAFE-4]
- S71. It should remove a deleted action and its children from the library unless another input uses them; a shared action stays. [tracker: ACT16] [test: test_profile_unused_actions.py::test_a_shared_action_stays_while_an_input_uses_it]
- S72. It should give actions added twice (Device Pack, History) new ids so they never clash. [user confirmed 2026-10-06; was code only] [test-plan: UNDO-CONFIGURATION]
- S73. It should take a snapshot of any input (unfinished actions left out of the snapshot and of their parents), and refuse a snapshot it can't read before changing anything. [test-plan: AUDIT2-B-UNDO] [test: test_audit_profile.py::test_a_snapshot_that_cannot_be_read_changes_nothing]
- S74. It should, when restoring into the same profile, keep an action another input still uses (shared stays shared) and keep ids. [test-plan: AUDIT2-B-UNDO]
- S75. It should offer in pick lists and Reuse only actions an input uses, plus the one being edited, and show a draft copy instead of its original. [test-plan: AUDIT2-B-UNDO, AUDIT3-TRACE]
- S76. It should let bindings on one input be reordered by drag. [user confirmed 2026-10-06; was code only]

### Swap Devices

**Replaced (2026-10-08, D-10-SWAP):** Swap Devices (Tools menu and the card's Swap Device…) goes. Swap with Another Stick, Copy Setup to Another Stick and Change vJoy Output in the Device Library (10 S22-S34) replace it; S77-S79 carry over as 10 S26 and S29, Q20 as 10 S29. S77-S83 below describe today's code until it is removed.

- S77. It should move every binding, every device reference inside actions and every script variable from the chosen profile device to the chosen connected device, and the connected device's bindings the other way (a swap, not a copy). [help: Swap Devices] [tracker: AU-36]
- S78. It should move inputs with no actions with their device too. [tracker: AU-36]
- S79. It should leave out and refuse the Keyboard, Logical Device, OSC and Xbox. [tracker: AU-91] [test-plan: AUDIT2-F-H-REST]
- S80. It should ask first, say nothing is saved yet and that undo means reloading without saving; there is no Undo. [tracker: C11] [user confirmed 2026-10-06; was code only for "no Undo"]
- S81. It should list each profile device with its action count, and "Unknown device (short id)" when its name isn't known; the list refreshes after a swap, a load or a device change. [test-plan: AUDIT3-TRACE] [test: test_audit3_screens.py]
- S82. It should start with the card's device as the connected device when opened from a card. [tracker: C5] [glossary: D5]
- S83. It should need a profile save afterwards to keep the swap. [help: Swap Devices]

### User scripts

- S84. It should add a .py file from the scripts folder as a script instance named "Instance N"; one file may be added more than once under different names. [help: Scripts] [user confirmed 2026-10-06; was code only for naming]
- S85. It should let a script be renamed (unique per file), configured (its variables), and removed after asking. [help: Scripts] [tracker: C14]
- S86. It should save scripts and their variable values with the profile; a script inside the scripts folder is saved with a path relative to that folder; others keep the full path. [help: Scripts] [test-plan: INTEG-SCRIPTS] [changed 2026-10-07 to follow decision D-04-S86-RELATIVE, which wins over the earlier wording "may be saved relative"]
- S87. It should run only scripts whose required variables are set, reload each script fresh at every Run, and retry a script that failed to load. [test-plan: SCRIPTS-THAT-CANT-LOAD] [user confirmed 2026-10-06; was code only for "required set"]
- S88. It should keep the saved settings of a script that can't load and write them back unchanged on save. [test: test_user_script_load_errors.py::test_syntax_error_keeps_the_script_and_its_settings]
- S89. It should give scripts `joy`, `keyboard` and `vjoy` only through the input and output modules: a script's vJoy can use only claimed outputs; unclaimed inputs read neutral. [help: Scripts] [test-plan: P2b, P3c]
- S90. It should run periodic callbacks no faster than every 0.01 s, log a failing callback without stopping the others, and stop them all at Stop. [tracker: AU-34] [test: test_user_script.py::test_periodic_callback_exception_is_logged_and_does_not_stop_other_callbacks]
- S91. It should let script callbacks run while paused without raising, so Resume still works. [tracker: ACT10]

### Undo and History (where they meet the profile)

- S92. It should let History Restore put an input's actions back into the open profile as an unsaved change, and write a whole profile as a copy next to it (never overwriting). [help: History] [tracker: AU-44]
- S93. It should keep Undo working after a save. [test: test_profile_unused_actions.py::test_undo_after_a_save_keeps_the_action]

## 9. Questions for the user

- Q1. Load / New and the start mode (R1). The code picks the start mode while the old profile is still the "current" one, so after a load the toolbar can show the old profile's start mode (or a mode the new profile doesn't have). Help says the toolbar lands in the new profile's Startup Mode. Recommend: confirm with the HELP-BUG-HANDS-ON check (still [U]); if it fails, set the open profile first, then work out the mode.
- Q2. Last Active means what? Help: "the mode the profile was using the last time it ran". Code: any toolbar pick while stopped also saves it as the last mode (`mode_manager.py:208-212`), so it is "last shown". Recommend: only modes used while running count (matches help). **Answered (GL-149, confirmed 2026-10-09 D-04-LAST-ACTIVE): only modes used while running count, as the help says.**
- Q3. Auto-load over unsaved edits: the new profile isn't loaded (S35), but the old profile keeps running for the new program (`backend.py:378-388`), unlike the missing-file case (S36), which stops it. Recommend: stop the running profile in the same way unless Keep running is on.
- Q4. Mode at the next Run: the mode stack is never reset at Stop or Run; Run adds the start mode on top of whatever was there (Previous can go back to a mode from before Run). Same as decision R3 in `system-maps.md`. Recommend: start mode, temporary modes cleared (as recommended there).
- Q5. Toolbar Mode while running: picking a mode switches the running profile (S54). Help only says the box shows the running mode. Recommend: keep (it is useful), and say so in help.
- Q6. Mode edits have no Undo: Add, Rename, Inherits from and Delete (which deletes bindings) can only be undone by reloading without saving. Recommend: ask; at least Delete Mode should be undoable, since it removes bindings.
- Q7. A profile that names an action type the program doesn't know (for example a user plugin that was removed or failed to load) is refused completely. Scripts and Play Sound files instead "open and keep" (ACT11, ACT12). Recommend: open the profile, keep the unknown action as-is and warn.
- Q8. Inputs saved in a mode that isn't in the mode list (a hand-edited or damaged file) load, never show, never run, and are saved again forever. Recommend: on load, move them into a "Recovered" mode or warn and list them.
- Q9. A profile file with no modes at all loads with no modes; the program then uses a "Default" that doesn't exist. Two modes with the same name load as one. Recommend: on load, add "Default" when the list is empty and warn about duplicates.
- Q10. A Startup Mode in the file that is neither a mode nor Use Heuristic / Last Active (damaged or hand-edited) makes the Startup Mode box fail (`ui/profile.py:1092`, `list.index` raises). Recommend: treat it as Use Heuristic on load.
- Q11. vJoy Initial Values: help says "set when the profile starts"; code writes a value only when it isn't 0 and the vJoy axis reads exactly 0 at that moment (`code_runner.py:477`). Recommend: always set them at Run.
- Q12. The vJoy Behavior switch (input/output) acts like a device being plugged in: with Device change behavior Disable it stops a running profile, with Reload it restarts it. Recommend: switching it while running should say "takes effect at the next Run" and not touch the run.
- Q13. A script's top-level code runs when the profile loads and when it is added, on the main thread; a slow or endless script freezes the program. Recommend: read the variables without running the whole script at load, or run it under a time limit (needs a design). [decided 2026-10-07: D-04-Q13-TIMELIMIT (top-level code runs on a worker thread with a time limit of about 5 s; a script that doesn't finish is marked failed with a message) and D-04-Q13-RUNLIMIT (the same limit applies when Run reloads scripts; the rest runs)] [user decision 2026-10-07: D-04-Q13-NOWAIT: at load and add the window does not wait for the script: loading or adding finishes at once, the script keeps its time limit on the worker, and a script that doesn't finish is marked failed with its message when the limit passes; Run still waits (D-04-Q13-RUNLIMIT)]
- Q14. The profile has no recovery copy: a crash loses every unsaved edit (the Button Map has Autosave). Recommend: ask whether profiles should get the same recovery copy.
- Q15. A missing Recent file shows an error and stays in Recent; only the start-up path offers Forget It. Recommend: offer Forget It there too.
- Q16. `--profile` with a missing file says "The last profile used was opened instead." even when there is no last profile. Recommend: say "A new profile is open" in that case.
- Q17. The last-mode store is keyed by the exact path text; opening the same file by another spelling, Save As, or a renamed file loses it. Recommend: key by the resolved, case-folded path (as Recent does).
- Q18. Plugging in a stick the profile uses, without any edit, can make the profile look unsaved (`*`), because the unsaved check updates the stored device names (R14). Recommend: fill device names only at save, not in the check.
- Q19. The unsaved check rebuilds the whole profile XML every 1.5 s while the window is in front (large profiles: your 1,172-action one). Recommend: measure; mark dirty on edit instead if it is slow.
- Q20. Swap Devices from a profile device to the same device, or to a twin of the same model, has no special message. Recommend: refuse "From" and "To" being the same id.
- Q21. Mode names are checked for look-alikes only in Manage Modes (R5); Device Pack import and scripts can add "test mode" next to "Test Mode". Recommend: move the rule into `ModeHierarchy.add_mode`.

## 10. Known gaps

Code differs from the spec or a rule
1. Load / New work out the start mode from the old profile (R1, Q1). `backend.py:257-261`, `:300`. Not covered by any test that uses the real Backend signal wiring.
2. "Last Active" is updated by toolbar picks while stopped (Q2). `mode_manager.py:208-212`, `backend.py:327-329`.
3. Auto-load over unsaved edits leaves the old profile running for the new program (Q3). `backend.py:378-388`.
4. The mode stack is not reset at Stop or Run (Q4; `system-maps.md` § 3 item P).
5. vJoy Initial Values are only written when the axis reads exactly 0 (Q11). `code_runner.py:475-478`.
6. The vJoy Behavior switch fires a fake device change (R12, Q12).
7. The unsaved check changes the profile (device names) and is heavy (R14, Q18, Q19).
8. Dead "converted" re-save branch still in `backend.py:648`, `:656-657`, though tracker AU-65 says a dead "converted" branch was fixed (R15).
9. Time and sleep outside `gremlin.clock` in the script timer loop and the pulse helper (R6, R7).
10. A script's top-level code runs unbounded on the main thread at load/add (R8, Q13).
11. Startup Mode box raises on a startup mode it doesn't list (Q10). `ui/profile.py:1092`.
12. Profiles with no modes, duplicate mode names, or inputs in unlisted modes load without a word (Q8, Q9). `profile.py:1737-1767`, `:1235-1246`.
13. `mode_exists("")` is True (the hidden root is named ""); `put_input` and `set_parent` accept "" (`profile.py:1735`, `:1714`). Blank names are blocked only in the UI.
14. Unknown action type refuses the whole profile (Q7). `profile.py:642-646`.
15. Script removal does not remove its variables from `Script.variable_registry` (`profile.py:1825-1834`); `ScriptListModel.renameScript` signals rows 0..rowCount (one past the end, `ui/script.py:421-423`; AU-65 left Scripts dataChanged "not reproduced").
16. `Settings.set_initial_vjoy_axis_value` does not clamp (load does). `profile.py:294-304`.
17. Two "drop unused actions" paths (R4) and the Library looking up the current profile (R2); covered by the Actions redesign in `system-maps.md` § 2.
18. Logical Device / OSC rows live in global singletons that any `Profile()` resets (R3).
19. The Load Profile action reaches into the UI Backend from the event pipeline (R11) and runs the new profile even if the load failed and a blank profile is open (`load_profile/__init__.py:79-80`).
20. Glossary N20 lists file-picker titles in sentence case ("Open profile", "Save profile as"); the dialogs say "Open Profile" / "Save Profile As" (GLOSSARY-4 Title Case later). Minor; confirm which wins.

Open tracker items touching this subsystem
- AU-118 (open): OK on a shared Merge Axis splits it; a Device Pack import that fails partway leaves the modes and Logical Device inputs it created, with no Undo (Actions map, decision A3).
- AU-117 (open): Run/Stop leftovers, including keys sent directly by scripts not released at Stop (Run lifecycle map, decision R4).
- AU-116 (open): timer actions firing after Stop (they can change mode after Stop).
- AU-64 (open, part): suspected races in device lists that the Swap Devices list and `DeviceDatabase` read.
- AU-58 (in progress): card menus offering things that don't apply (Swap Devices minimum size done).
- Decision R3 (`system-maps.md`): mode at the next Run, unanswered.
- HELP-BUG-HANDS-ON, SAFE-4-HANDS-ON, MACRO-DELAY-HANDS-ON, WORKFLOW-HANDS-ON: hands-on checks still marked [U]; PS-02 (Macro Default Delay) and PS-03/PS-04 (vJoy switch, initial values) NOT RUN / DEFERRED; SW-01..03 NOT RUN.

Things nothing owns
- The mode name rule (only a QML model holds it, R5).
- Which profile is "current": `Backend.profile` and `shared_state.current_profile` are two copies set at different times (R1).
- The mode stack's life across Stop/Run (no owner resets it).
- Script globals (`callback_registry`, `periodic_registry`, `variable_registry`, `sys.path`) shared by every profile and Run.
- A recovery copy of unsaved profile edits (none exists, Q14).
- Undo for Manage Modes and Swap Devices (none exists, Q6, S80).

## 11. Size and test coverage

Size: about 9,000 lines. Python about 7,300 (`profile.py` 1913, `user_script.py` 1426, `ui/profile.py` 1399, `backend.py` 704, `base_classes.py` 682, `ui/script.py` 451, `mode_manager.py` 368, `tree.py` 250, `swap_devices.py` 162, plus parts of `tools.py`, `config.py`, `process_monitor.py`, `joystick_gremlin.py`). QML/JS about 1,700 (Manage Modes 249, Scripts 248 + 374, Profile Settings 256, Auto-load option 237, Swap Devices 164, the profile parts of `Main.qml` about 300, `main_commands.js` 119).

Covered well
- Mode tree and run-time stack: `test_tree.py`, `test_modes.py` (15), `action_interaction/test_modes.py` (7), `test_audit_profile.py`, `test_audit2_modes.py`, `test_audit3_modes.py`.
- Saving: `test_profile_save_safe.py`, `test_profile_unused_actions.py`, `test_profile_unsaved.py`, `test_library_invalid_children.py`, `test_audit*_saving.py`.
- Load failures: `test_load_and_rename_safety.py`, `test_profile_missing_child_action.py`, `test_startup_messages.py`.
- Auto-load and the Load Profile action: `test_autoload_and_mode_prompts.py`, `test_audit_saving.py`, `test_audit2_saving.py`, `test_audit2_coverage.py` (all with a fake Backend).
- Scripts: `test_user_script.py` (21), `test_user_script_load_errors.py` (5), `integration/test_e2e_user_script.py`.
- Settings: `test_profile_settings.py` (6), `test_write_less.py` (last mode).

Thin or untested
- The real Backend wiring on Load / New: the order of `ModeManager.reset`, `setCurrentMode` and `shared_state` (gap 1). Tests replace Backend with fakes.
- `Backend.selectMode`, `newProfile`, `saveProfile` success path with Recent, `windowTitle`.
- `StartupModeModel` with an unknown value; `VJoyInputOrOutputModel.setData` side effects; `OutputVJoyInitialValuesModel`; vJoy Initial Values at Run.
- Unsaved check after a device is plugged in; its cost on a large profile.
- Profiles with no modes, duplicate mode names, inputs in unlisted modes, an unknown startup mode.
- `ModeManager.previous` / `unwind` beyond the action-interaction cases; resolution mode with renamed/deleted modes.
- Swap Devices: one data test (`test_swap_devices.py`), plus refusal and list-refresh tests; no test of a swap onto a device that already has bindings, of script variables in both directions through the UI slot, or of the device names list after a swap.
- Script add running top-level code; script removal leaving its variables registered.
- Manage Modes window itself (rename/delete flow) beyond the name check and the closed-window test.

## 12. Review (user, 2026-10-06)

Approved by the user as recommended (2026-10-06, blanket approval of the remaining pages): every [code only] statement in section 8 is confirmed, except where a question's recommendation changes it; every question in section 9 is decided as its **Recommend** says. Where a recommendation and a section 8 statement disagree, the recommendation wins.

| Q | Decision |
|---|---|
| All | As recommended in section 9 |
| Q13 | 2026-10-07: D-04-Q13-TIMELIMIT and D-04-Q13-RUNLIMIT (time limit at load, add and Run) |
| S41, S52 | 2026-10-07: D-04-ALPHA-CASEFOLD (alphabetical ignores capitals) |
| S86 | 2026-10-07: D-04-S86-RELATIVE |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.

**Change (user, 2026-10-06), Q14:** yes, profiles get a recovery copy. While
a profile has unsaved changes, a recovery copy is kept about every minute;
on the next open of that profile (or at start after a crash) the program
offers Restore / Discard / Not now, the same as the Button Map's Autosave.
Save, Discard and a clean close remove the copy. This adds statement S94:
"It should keep a recovery copy of unsaved profile edits and offer it after
a crash" [user decision: 04 Q14].
