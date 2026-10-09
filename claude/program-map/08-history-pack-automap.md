# History, Device Pack and Auto Mapper

Mapped against code at 4f6bdfa4 (6 Oct). Line numbers drift; re-check them before a step starts. `claude/history-notes.md` is background only (its write-path table is out of date; map 1 in `claude/system-maps.md` replaces it).

## 1. Purpose

**History** keeps every saved change (profile saves, module files, settings) in its own files, so the user can see what changed and put an older or newer version back, also after a restart. **Device Pack** puts one device's whole setup (module file, pictures, wires and their actions, the output modules they send to) into a zip, and puts a zip back onto a device; the import replaces what is there, warns first, and has Undo Import. **Auto Mapper** makes Map to vJoy actions for whole devices in one step: each claimed control of an input module gets an action to the same number on a vJoy output module.

## 2. Files

| Path | What it holds |
|---|---|
| `gremlin/history.py` (419) | The store: `AREAS` (profile, modules, button-map, settings), `record` / `write_now` / `later` (queue), writer thread `_run`, `flush`, `close` (quit), `_append` (one JSON line, starts a new line after a cut one), `entries` / `entry` (read, newest first, damaged lines skipped), `keep_file` / `kept_file` / `restore_file` (pictures by SHA-1 in `history\files`), `prune` (days, MB, snapshots, unused pictures), limits `KEEP_DAYS` 90, `MAX_MEGABYTES` 20, `SNAPSHOTS` 20. |
| `gremlin/history_modules.py` (234) | Module-file entries: `text_before`, `note_write` (after a write), `delete_before` / `note_delete` / `deleting()` (around a delete), picture refs and keeping, `_record` (title, area Button Map vs Module files, skip view-only `ui` saves). Remembers each file's last pictures in `_last_pictures`. |
| `gremlin/history_profile.py` (262) | Profile entries: `changes()` compares two profile texts input by input (actions resolved by content, ids ignored) and by section (settings, logical-device, osc-device, modes, scripts); `record_save` queues it; `_record` writes one entry per change plus one "Saved X.xml" entry with both whole profiles packed (zlib + base64). |
| `gremlin/ui/history_model.py` (436) | `HistoryModel` (QML `Gremlin.UI`): list, filter (JSON), search, `detail`, `restore`. `describe()` makes Before/After text; `_restore_input`, `_restore_profile`, `_restore_module`, `_restore_settings`. |
| `qml/DialogHistory.qml` (326) | Tools > History window: Show (area), Search, Refresh, "Only ..." line with Show All, list, Before/After with Restore Before / Restore After behind a confirm. |
| `gremlin/config.py` (lines 97-106, 177-226, 265) | `settings_history_title`, `_settings_view` (user-facing settings only), `_record_history` (called from `save_now`). |
| `gremlin/profile.py` (lines 904-927, 1126-1180) | `to_xml` calls `history_profile.record_save` when the text changed; `put_input` (used by Restore and Undo). |
| `gremlin/modules/module_file.py` (lines 64-100, 107) | `write_text` (safe write; calls `history_modules.note_write`); `start_fresh` (no History). |
| `gremlin/ui/device_pack.py` (1893) | Export: `assemble`, `pack_modes`, `_collect_wires`, `_rewrite_images`, `_output_doc`, `_pack_label`. Read: `_read_zip`, `describe_zip`, `_stage_images` (temp folder), `_too_new`. Import: `preview_import`, `apply_zip`, `_merge_module`, `_write_pictures`, `_write_module`, `_plan_wires`, `_apply_wires`, `_ensure_modes`, vJoy moves, Logical checks, `driver_notes`. Undo: `_last_import`, `undo_import`, `drop_import_undo`, `_put_back`. |
| `gremlin/ui/hardware_profile.py` (parts) | Slots on `HardwareProfile` used by the pack window: `packDevices`, `peekPackDevice:1872`, `peekPackZip:1893`, `exportPack:1908`, `importPack:1957`, `previewPackImport:1991`, `undoPackImport:2007`, `keepPackImport:2013`, `canUndoPackImport:2020`, `showFolder`. Helpers the pack imports: `_replace_file:592` (second safe writer, calls History), `_unique_archive:1342`, `_match_pack_device:1308`, `_suggest_pack_name:1318`, `_known_pack_devices:1258`, `_read_json_dict:1238`. Deleted-devices backups: `delete_module_file:865`, `_keep_deleted_copy:908`, `_deleted_pack_path:935`, `delete_device:1099` (writes a pack with `assemble`), `_save_profile_wires:1033`. Module Setup import and its own Undo: `import_module_file:691`, `undo_last_import:661`. |
| `qml/DialogDevicePack.qml` (952) | Tools > Device Setup > Device Pack: Export tab (device, photo, size, Wires in these modes, Made by, Note, Export..., Show Folder), Import tab (Choose Zip..., notes, driver line, Put this pack on, sections with tick boxes, Open All / Close All, Import, Undo Import), Replace warning with "Create the missing Logical Device inputs". |
| `gremlin/auto_mapper.py` (257) | `AutoMapperOptions` (mode, combine, overwrite, claim outputs), `AutoMapper.generate_module_mappings`, skip report, `_source_uuid`, `_vjoy_limits`, `_get_used_vjoy_inputs`, `_create_new_mapping`. |
| `gremlin/modules/auto_map.py` (145) | Input and output modules as the Auto Mapper sees them (`input_modules` collapses one device's several files to the bound one; `output_modules` = `output.vjoy_modules`); `merge_claim_into_output` (writes the output module's claim). |
| `gremlin/ui/auto_map_modules.py` (80) | `AutoMapInputModel`, `AutoMapOutputModel` (QML `Gremlin.Device`); reload on profileChanged, configChanged, device change. |
| `gremlin/ui/tools.py` (lines 31-62) | `Tools.createMappings` (slot), `lastOverwriteUsedInputs`; remembers Overwrite (`automap/mapper/overwrite-used-inputs`). |
| `qml/DialogAutoMapper.qml` (269) | Tools > Mapping > Auto Mapper: input and output lists, Select Mode, Overwrite used inputs (asks first), Combine onto selected outputs, Also claim the matching outputs, Create 1:1 Actions, result line, help tip, RunningNote. |
| `qml/main_commands.js` (84-99) | Menu commands `tools.devicePack`, `tools.autoMapper`, `tools.history`. |
| History buttons in editors | `qml/BindingCatalog.qml:1583` (Configuration row), `qml/LogicalPage.qml:1215` (Logical control menu), `qml/DialogConfigureModule.qml:401` (Module Setup), `qml/DialogCalibration.qml:235`, `qml/DialogJoystickButtonMap.qml:2495` (File > History), `qml/DialogOptions.qml:99`. |
| `gremlin/util.py:929-937` | `history_dir()` (option `history-folder`), `deleted_devices_dir()` (option `deleted-devices-folder`), `export_dir()`. |
| `joystick_gremlin.py` | Folder options 643-660; History options `keep-days` / `max-megabytes` 726-737; quit: `threads.shutdown`, `deferred_write.flush_all`, `history.close()` 1107. |
| Tests | History: `test_history_store.py` (6), `test_history_recording.py` (8), `test_history_restore.py` (6), `test_history_window.py` (5, with `history_window_smoke.py`), parts of `test_audit_saving.py`, `test_audit2_saving.py`, `test_audit3_saving.py`, `test_audit2_coverage.py`, `test_audit3_module_files.py`. Device Pack: `test_device_pack_import.py` (24), `test_device_pack_window.py` (7, with `device_pack_window_smoke.py`), `test_audit3_modes.py::test_undo_import_deletes_a_mode_everywhere`, `test_audit3_saving.py` (Undo Import), `test_usability_fixes.py::test_device_pack_has_no_layout_loop`. Auto Mapper: `test_auto_mapper.py` (3), `test_auto_mapper_claims.py` (4), `test_profile_unused_actions.py::test_auto_mapper_overwrite_leaves_nothing_behind`, `test_audit3_module_files.py::test_calibration_and_auto_mapper_open_on_the_cards_file`. Deleted devices: `test_data_safety.py`, `test_deleted_devices_folder.py`. |

## 3. What it owns

**Files on disk**

| Data | Where | Written by | Who else may change it |
|---|---|---|---|
| History entries, one JSON line each: `id`, `at` (clock.now), `area`, `kind` (save, delete, input, section, profile), `title`, `subject`, `before`, `after` | `<history folder>\profile.jsonl`, `modules.jsonl`, `button-map.jsonl`, `settings.jsonl` | `history._append` (writer thread, or the caller's thread in `flush`/`close`); `prune` rewrites whole files through `module_file.write_text` | Nobody else |
| Kept pictures, named `<sha1><ext>` | `<history folder>\files\` | `history.keep_file`; removed by `prune` | Nobody else |
| Whole-profile copies made by Restore | next to the profile: `<name> (history <date time> before|after>[ n].xml` | `history_model._restore_profile` | Nobody lists or cleans them |
| Module files and pictures | `<modules>\<slug>.json`, `<modules>\<slug>\` | Device Pack import and Undo (`_write_module`, `_write_pictures`, `_put_back`, `undo_import`), History Restore (`_restore_module`), Auto Mapper claim (`merge_claim_into_output`) | Owned by the module-file system (map 1); many other writers |
| Backups of replaced module files and pictures | `<modules>\imported\<stem>.<stamp>[_n].json` and `.<ext>` | Device Pack `_write_module`, `_write_pictures`; Module Setup `import_module_file` | Listed by Module Setup "Import from"; never cleaned |
| Device packs | anywhere outside the modules folder (default `<data>\export\<slug>_map.zip`) | `exportPack` | The user |
| Deleted-device backups | `<deleted devices>\<name>\<name>.<stamp>.zip` (Delete Device, "Save a copy"); `<deleted devices>\<stem> <date time>.json` (Delete File) | `delete_device`, `_keep_deleted_copy` | The user; never cleaned |
| Pack preview pictures | `%TEMP%\gremlin-pack-*` | `device_pack._stage_images`; the previous one is removed when the next pack is opened | Never removed at quit |

**In memory**

| Data | Where | Who writes | Who else may change it |
|---|---|---|---|
| History queue `_queue`, writer `_writer`, `_stop`, `_closing`, `_pruned`, `_kept_now` | `history.py:50-60` | `record`, `later`, writer, `close` | Nobody |
| Last pictures per module file `_last_pictures` | `history_modules.py:53` | `_record` (writer thread, or UI thread through `flush`) | Nobody; no lock |
| Settings view `_history_view` (last saved user-facing settings) | `Configuration` | `reload`, `_record_history` | Nobody |
| `_saved_snapshot` (last loaded/saved profile text, the "before" of the next save) | `Profile` | `from_xml`, `to_xml` | Owned by Profile |
| History window rows `_all`, `_rows`, `_filter`, `_search` | `HistoryModel` | the window | Nobody |
| Last Device Pack import `_last_import` = {files: [(path, previous bytes or None)], wires: {profile, uid, removed, added, modes, logical}} | `device_pack.py:1538` | `apply_zip`; cleared by `undo_import`, `drop_import_undo` | Holds live `InputItem` objects of the profile; the user can edit them in between |
| `_preview_dir` | `device_pack.py:733` | `_stage_images` | Nobody |
| Module Setup's own import undo `_import_undo` | `hardware_profile.py:649` | `import_module_file`, `undo_last_import` | A separate system with a same-named `drop_import_undo` |
| Auto Mapper run state (`_created_mappings`, `_num_retained_bindings`, `_skipped`) | `AutoMapper` | one run | Nobody |

**Settings keys**

| Key | Meaning | Who changes it |
|---|---|---|
| `global/history/keep-days` (90, 1-3650) | Days to keep changes | Options > General > History |
| `global/history/max-megabytes` (20, 1-500) | Largest history file (MB) | Options > General > History |
| `global/files/history-folder` | History folder | Options > Folders |
| `global/files/deleted-devices-folder` | Deleted devices folder | Options > Folders |
| `global/files/export-folder` | Where packs are saved by default | Options > Folders |
| `automap/mapper/overwrite-used-inputs`, `automap/mapper/remember-overwrite` | Auto Mapper's Overwrite switch remembered | `Tools.createMappings` |
| `global/internal/module-file-bindings` | Module-file bindings (read by the pack's file rule; not a History setting because it is internal) | Module-file system |

**Profile data changed (in memory, unsaved)**: Device Pack import (inputs of the target device in ticked modes, actions, modes, Logical Device inputs, `device_database`), Undo Import (the same back), History Restore of an input (`put_input`), Auto Mapper (input items and Map to vJoy actions in the chosen mode).

## 4. Entry points

| User action / trigger | Handler | Function(s) |
|---|---|---|
| Tools > History (menu, palette) | `main_commands.js:99` `openToolWith("DialogHistory.qml", {filter: ""})` | `HistoryModel.setFilter`, `reload` -> `history.entries()` |
| Configuration row "History" | `BindingCatalog.qml:1583` | filter `{deviceId, inputType, inputId, mode}`, label = device name |
| Logical Device control menu > History | `LogicalPage.qml:1215` `_openHistory` | filter `{device: "Logical Device", inputType, inputId, mode}` |
| Module Setup "History" | `DialogConfigureModule.qml:401` | filter `{fileName: moduleFileFor(...) + ".json"}` |
| Calibration "History" | `DialogCalibration.qml:235` | filter `{fileName}` |
| Button Map File > History | `DialogJoystickButtonMap.qml:2495` | filter `{area: "button-map", device: targetName}` |
| Options "History" | `DialogOptions.qml:99` | filter `{area: "settings"}` |
| History: Show / Search / Refresh / Show All | `DialogHistory.qml:156-193` | `setArea` -> `setFilter`; `setSearch`; `reload`; `showAll` |
| History: window comes to the front | `DialogHistory.qml:136` `onActiveChanged` | `reload` (reads every file again) |
| History: pick an entry | `pick` -> `shown` | `HistoryModel.detail` -> `describe` |
| History: Restore Before / After | `DialogHistory.qml:117` confirm (`_gate.confirmThen`) | `HistoryModel.restore` -> `history_model.restore` -> `_restore_input` / `_restore_profile` / `_restore_module` / `_restore_settings` |
| Save Profile (any path: Save, Save As, Delete Device's save) | `Profile.to_xml` (`profile.py:904`) | `history_profile.record_save` -> `history.later` -> writer `_record` -> `write_now` |
| Any module-file write | `module_file.write_text` (`module_file.py:64`), `_replace_file` (`hardware_profile.py:592`) | `history_modules.text_before` then `note_write` -> `later` |
| Module-file delete | `history_modules.deleting` around `unlink` (`hardware_profile.py:675, 883, 1083`; `device_pack.py:1584`) | `delete_before`, `note_delete` |
| Settings saved (about 1 s after a change, deferred_write QTimer; and at quit) | `Configuration.save_now` -> `_record_history` (`config.py:201, 265`) | `history.record("settings", ...)` |
| First entry of a session | writer `_run` | `_prune_once` -> `prune` |
| Quit | `joystick_gremlin.py:1107` | `history.close()` (flush, bounded join, flush) |
| Tools > Device Setup > Device Pack | `main_commands.js:85` | `DialogDevicePack.qml` `reloadDevices` -> `packDevices` -> `_known_pack_devices`; `refreshExport` -> `peekPackDevice` -> `assemble` + `pack_modes` |
| Export: choose device | `_exportDevice` change -> `refreshExport` | `peekPackDevice` (builds the whole zip to get its size) |
| Export: Export... -> file dialog OK | `DialogDevicePack.qml:353` | `exportPack` -> `assemble(name, resolve, modes, notes)` -> `dest.write_bytes` |
| Export: Show Folder | `showFolder` | `QDesktopServices.openUrl` |
| Import: Choose Zip... -> OK | `DialogDevicePack.qml:367` | `keepPackImport` (drops Undo) -> `peekPackZip` -> `describe_zip` -> `_read_zip`, `_stage_images`, `_pack_drivers` |
| Import: tick / untick, Open All / Close All, Put this pack on | QML state only (`checks`, `targets`, `folded`) | `selectionJson` |
| Import button | `askImport` | `previewPackImport` -> `preview_import` (plan, counts, left out, moves, drivers) -> Replace warning |
| Replace (in the warning) | `runImport` | `importPack` -> `apply_zip` -> `_merge_module`, `_write_pictures`, `_write_module` (per target), `_plan_wires`, `_apply_wires`, `drop_import_undo` (keeps the previous import for good), sets `_last_import`; signals configChanged, profileChanged, reloadUi |
| Undo Import | `undoImport` | `undoPackImport` -> `undo_import` |
| Close the Device Pack window | `onClosing` | `keepPackImport` -> `drop_import_undo` (replaced actions leave the profile) |
| `importPack` with an empty selection (no caller in QML) | `hardware_profile.py:1972-1987` | imports every row ticked by default |
| Home card > Delete Device, "Save a copy in deleted devices" | `StatusPage.qml:454` -> `ModuleModel.deleteDevice` | `delete_device` -> `assemble` -> `_deleted_pack_path` -> write, read back (`_zip_readable`), then `_save_profile_wires` (saves the profile), `_delete_own_module_files` |
| Module Setup > Delete File | `delete_module_file` | `_keep_deleted_copy` then delete inside `deleting()` |
| Tools > Mapping > Auto Mapper; card menu > Auto Mapper | `main_commands.js:94`; `Main.qml:1432` (`initialSlug` = the card's module) | `AutoMapInputModel` / `AutoMapOutputModel` -> `auto_map.input_modules` / `output_modules` |
| Auto Mapper: Create 1:1 Actions | `DialogAutoMapper.qml:209` (asks first when Overwrite is on) | `Tools.createMappings` -> `AutoMapper.generate_module_mappings` -> (`merge_claim_into_output`) -> `_create_new_mapping`; then profileChanged, reloadCurrentInputItem, configChanged; remembers Overwrite |
| Auto Mapper lists refresh | profileChanged, configChanged, `EventListener.device_change_event` | `_SlugListModel.reload` |

## 5. Talks to

| Other subsystem | Calls out (this -> it) | Called by (it -> this) |
|---|---|---|
| Profile and modes (04) | `put_input`, `add_inputs`, `drop_unused_actions`, `roots_of`, `actions_in_use`, `get_input_item`, `modes.add_mode/set_parent/mode_exists`, `ui.profile.delete_mode` (Undo Import), direct `profile.inputs[...] =` and `device_database.devices[...] =` | `Profile.to_xml` -> `history_profile.record_save` |
| Module files (map 1; registry, module_file, hardware_profile) | `module_file.write_text/write_json/load_for_update`, `_replace_file`, `_read_json_dict`/`read_doc`, `module_json_path`, `_match_pack_device`, `_known_pack_devices`, `resolve_module_slug` | `module_file.write_text`, `_replace_file`, Button Map writer and every delete -> `history_modules` |
| Settings (config) | `Configuration.value/set/exists`, `cfg._data` (Restore) | `Configuration.save_now` -> `history.record` |
| Output modules (06) | `output.vjoy_modules`, `vjoy_driver_problem`, `vjoy_exists`, `xbox_driver_problem` (pack driver notes) | none |
| Devices and raw input (02) | `device_initialization.physical_devices/vjoy_devices` (Auto Mapper `_source_uuid`, `_vjoy_limits`, `_get_used_vjoy_inputs`; pack `_device_limits` via `hardware_profile._live_devices`), `EventListener.device_change_event` (Auto Mapper lists) | none |
| Logical Device | `LogicalDevice().exists/create/delete`, `signal.logicalDeviceModified` | none |
| Action plugins | `PluginManager.create_instance(map-to-vjoy)`, `tag_map` (History names), `map_to_vjoy.MapToVjoyData`, `root.RootData` | none |
| Main window / signals | `signal.configChanged`, `profileChanged`, `reloadUi`, `reloadCurrentInputItem` | none |
| Threads (`gremlin.threads`), `gremlin.clock` | `threads.start("History", ..., stop=)`, `clock.now()` | `threads.shutdown` at quit stops the writer |
| Live debug trace | `trace("SAVE"/"READ", "History"/"Device Pack"/"Auto Mapper", ...)` | none |
| Options window (`gremlin/ui/option.py`) | `entry_title` (History setting names) | Options "History" button opens the window |
| Delete Device / Module Setup (card, StatusPage) | `assemble` for the backup pack | `delete_device`, `delete_module_file` |
| Configuration page Undo | shares `Profile.input_snapshot` / `put_input` with Restore | none |

## 6. Threads and timers

- **History writer**: one thread made with `threads.start("History", _run, stop=_stop.set)` (`history.py:160`) when something is queued and no writer runs. It waits with `queue.get(timeout=1.0)` (0.05 s once stop is set) and ends by itself when the queue is empty; the end is decided under `_start_lock`, the same lock `record` uses to start one, so nothing is left queued. It runs `prune` once per session, then each queued item: an entry dict (`_append`) or a callable (`history_profile._record`, `history_modules._record`), which do the comparing and picture keeping off the UI thread.
- **Other threads run the same queue**: `history.entries()` calls `flush()` (`history.py:289`) on the caller's thread (the UI thread, from the History window and Restore), so queued comparisons and picture copies can run on the UI thread while the writer runs too. `_append` takes `_write_lock`; `_last_pictures` and the order of entries are not protected (section 7).
- **Quit**: `threads.shutdown()` asks the writer to stop, then `history.close(timeout=2.0)` sets `_closing`, flushes on the main thread, joins the writer (bounded), flushes again. From then on `record`/`later` write at once on the caller's thread.
- **Clock**: entries use `clock.now()`; `prune` uses `clock.now()`. Display uses `datetime.fromtimestamp`. Restored profile copy names and archive stamps use `datetime.now()` (local time, names only).
- **Settings entries** come from `Configuration.save_now`, run by `deferred_write`'s QTimer about 1 s after the last change (main thread), and at quit.
- **Device Pack and Auto Mapper**: no threads or timers. Everything (zip building for the size preview, reading the zip, staging pictures, writing) runs on the UI thread inside slots.
- **History window**: no timer; it re-reads all files whenever it becomes the active window.
- **Off the main thread reading settings**: `history._limits()` and `util.history_dir()` call `Configuration()` from the writer thread.

## 7. Rule breaks

| # | Rule | Where | What | Status |
|---|---|---|---|---|
| R1 | Single owner (module files) | `hardware_profile.py:592` `_replace_file` and `module_file.py:64` `write_text` | Two safe writers, each calling History itself; `_replace_file` has no fallback when Windows refuses the swap. Map 1 step 7 plans one owner. | CONFIRMED |
| R2 | Single owner / damaged files never treated as empty | `device_pack.py:1793, 1835` (`_read_json_dict` returns None for a damaged file) then `_write_module:1636` | Import merges onto an empty skeleton and replaces the damaged file (a backup is kept). Every other module-file save refuses (MODULE-FILE-DAMAGE). Decision F1 open. | CONFIRMED |
| R3 | Safe writes | `device_pack.py:1162` `dest.write_bytes(data)` | Pack pictures written in place, not temp + swap; a crash leaves a half picture. | CONFIRMED |
| R4 | Safe writes | `hardware_profile.py:1943` (export zip), `:1121` (deleted-device pack) | Zips written in place. The deleted-device pack is read back before anything is deleted; the export is not. | CONFIRMED |
| R5 | Single owner (profile) | `device_pack.py:1498` `profile.inputs[uid] = kept`, `:1501` `device_database.devices[uid] = ...`, `:1606` (Undo) | The pack edits the profile's input lists and device database directly instead of through Profile methods. | CONFIRMED |
| R6 | Single owner (settings) | `history_model.py:307` `cfg._data[...]["data_type"]` | Restore reads the Configuration's private table. | CONFIRMED |
| R7 | Layer rule (wiring reads the driver only through the output module) | `auto_mapper.py:205-214` `_vjoy_limits` | Reads vJoy axis/button/hat counts from `device_initialization.vjoy_devices()`; the output module already has `output.vjoy_layout(vjoy_id)` (`output.py:188`). Also duplicated logic. | CONFIRMED (code); layer reading is SUSPECTED a break, since `device_initialization` is the device list, not the driver call |
| R8 | Layer rule (UI never touches hardware directly) | `auto_mapper.py:200, 219`; `device_pack.py:1181` `_device_limits` -> `hardware_profile._live_devices` -> `device_initialization` | Reads the raw device list instead of `gremlin.modules.hardware` (`device_info`, `device_connected`). | SUSPECTED |
| R9 | Thread rules / shared state | `history.py:289` (`entries` -> `flush`) | Queued work runs on the UI thread at the same time as on the writer; `history_modules._last_pictures` (`history_modules.py:211, 221`) has no lock, and entries can be written out of order. | SUSPECTED (seen in code, race not reproduced) |
| R10 | Thread rules | `history.py:83-84`, `util.history_dir` from the writer | `Configuration()` read off the main thread. Reads only. | SUSPECTED (low) |
| R11 | Duplicated logic | `hardware_profile.py:649-688` (`_import_undo`, `drop_import_undo`, `undo_last_import`) and `device_pack.py:1538-1633` (`_last_import`, `drop_import_undo`, `undo_import`) | Two "Undo Import" systems with the same function name and different rules. | CONFIRMED |
| R12 | History hooked in each writer, not one owner | `module_file.py:75,100`, `hardware_profile.py:598,612`, deletes at 675, 883, 1083, `device_pack.py:1584` | Gaps: `module_file.start_fresh:107` and `device_pack._put_back:1564` (unlink) make no entry. Map 1 step 7. | CONFIRMED |
| R13 | Private helpers across modules | `device_pack.py:29-45` imports 15 underscored names from `hardware_profile`; `history_model.py:221` and `device_pack.py` import `input_pairing._guid` | Hidden coupling; any change in `hardware_profile` can break the pack. | CONFIRMED |
| R14 | Production asserts | `auto_mapper.py:228` `assert isinstance(binding.root_action, root.RootData)` | A binding with another root stops the whole run with AssertionError (or is skipped silently under `-O`). | CONFIRMED |
| R15 | Glossary (UI words) | `auto_mapper.py:255-256` "Created N mappings, retained N previous bindings."; `history_model.py:116-124` shows raw JSON keys (`claim`, `nodes`, `hwId`) in Before/After | Glossary: "action" not "mapping"; D13 no internal ids on screen. The glossary guard test reads QML and Options strings, not Python result text. | CONFIRMED |
| R16 | Xbox has no claims | not broken | Auto Mapper offers vJoy outputs only; the pack's Xbox output modules carry no claim checks (`_merge_module` merges claims of any output doc it is given; the Xbox output module file has none). | CONFIRMED (no break) |

## 8. Behaviour spec

### History: what is kept

- **S1** It should keep every saved change in its own files in the data folder's history folder (profile saves, module files, Button Map, settings), never as leftovers in the profile. [help: History] [glossary: History] [test-plan: HISTORY-A]
- **S2** It should record a profile change when the profile is saved (not per edit), one entry per input whose actions were added, changed or removed, titled "Added/Changed/Removed the actions of <device> <Button 3> in <mode>". [help: History] [test-plan: HISTORY-B] [test: test_history_recording.py::test_a_profile_save_records_each_changed_input]
- **S3** It should treat an input whose actions only got new ids (an editor's OK copies them) as unchanged. [test-plan: HISTORY-B] [test: test_history_recording.py::test_new_ids_with_the_same_actions_are_no_change]
- **S4** It should record one entry for each other part of the profile that changed: Profile Settings, the Logical Device, the OSC inputs, the modes, the scripts. [help: History] [test: test_history_recording.py::test_other_parts_and_the_whole_profile]
- **S5** It should keep the whole profile before and after each save (compressed) for the newest 20 saves of each profile; older saves keep only their per-input and per-part entries. [help: History] [test-plan: HISTORY-B]
- **S6** A save whose text is the same as the last load or save should make no entry. [user confirmed 2026-10-06; was code only]
- **S7** A Save As to a new file should be recorded under the new file, with the old file's text as "before". [user confirmed 2026-10-06; was code only]
- **S8** Every save of a device's module file should be kept with the file before and after and every picture it names (the device photo and map pictures), each picture kept once by its content. [help: History] [test: test_history_recording.py::test_a_module_save_is_kept_with_its_pictures] [test: test_history_store.py::test_a_picture_is_kept_once_and_put_back]
- **S9** A save that changes only the Button Map's view (zoom, pan, grid, guides, print area) should not be kept. [help: History] [test: test_history_recording.py::test_the_maps_view_alone_is_not_kept]
- **S10** A module-file save that changes only Button Map parts should be filed under Button Map; any other under Module files. [test-plan: HISTORY-B]
- **S11** The first save of a module file should read "Created the module file of X"; later ones "Saved X: <what changed in words>". [test-plan: HISTORY-C] [user confirmed 2026-10-06; was code only for the wording list]
- **S12** Deleting a module file (Delete File, Delete Device, Undo Import of a new file, Module Setup's Undo of an import) should record "Deleted the module file of X" with the file and its pictures, and only once the delete went through. [test-plan: AUDIT3-TRACE W5] [tracker: AU-113] [test: test_audit3_saving.py::test_a_delete_that_went_through_is_recorded] [test: test_audit3_saving.py::test_a_delete_that_failed_is_no_history_entry] [test: test_audit3_saving.py::test_undo_import_of_a_locked_new_file_isnt_recorded_as_deleted]
- **S12a** The Device Library's list and saved-setup files are recorded like module files (10 S51): one entry per Library action, restorable. [D-10-IN-HISTORY]
- **S12b** Tools › History has a red **Clear History…** button (after Refresh). It asks first, naming exactly what goes: "All N changes in History are deleted, along with the X MB of kept copies used to restore them. You won't be able to restore or undo any earlier change, including the Device Library's Undo for this session. Your profiles, module files and Device Library stay as they are. This can't be undone." Cancel is the default; refused while a profile is running. It deletes every History entry and kept copy (and empties the Library's Undo/Redo steps), nothing else. It leaves one red entry, "History cleared" with the date and what was deleted; selecting it explains that nothing before it can be restored (no Restore or Previous/Next Change); History's own clean-up never removes it, and each later clearing adds another. Device Library entries are labelled "Device Library" (not "Module files"), and their restore note reads "Restoring puts back the Device Library's list and its saved setups together." [user decision 2026-10-09: D-08-CLEAR-HISTORY]
- **S13** A write that failed should leave no entry. [tracker: AU-94] [test: test_audit2_saving.py::test_a_save_that_failed_is_no_history_entry] [test: test_audit2_saving.py::test_an_import_write_that_failed_is_no_history_entry]
- **S14** Files outside the modules folder itself (imported backups, recovery copies, templates, profile copies) should not be module-file entries. [test: test_history_recording.py::test_other_files_are_not_kept]
- **S15** Only the settings the user chooses (Options, HidHide choices, OSC, folders) should be recorded; window sizes and places, internal memory and HidHide's automatic picture links should not. [help: History] [tracker: AU-54] [test: test_history_recording.py::test_settings_the_user_chooses_are_kept]
- **S16** A setting appearing for the first time should not count as a change; several changes within about a second should make one entry. [test-plan: HISTORY-B] [user confirmed 2026-10-06; was code only for the one-second grouping]
- **S17** Settings entries should be titled by the names Options shows, old entries too. [tracker: AU-103] [test-plan: AUDIT2-F-H-REST]

### History: store, limits, threads

- **S18** Entries older than "Days to keep changes" (Options > General > History, default 90) should go, and when a file is larger than "Largest history file (MB)" (default 20) its oldest entries go first. [help: History] [test: test_history_store.py::test_old_entries_and_unneeded_pictures_go] [test: test_history_store.py::test_a_file_past_its_size_loses_its_oldest_entries]
- **S19** That clean-up should run when the first entry of a session is written. [test-plan: HISTORY-A]
- **S20** Kept pictures no entry needs should be removed at clean-up, except pictures kept this session for an entry not written yet (a deleted device's photo). [tracker: AU-83] [test: test_audit2_saving.py::test_a_deleted_device_keeps_its_photo_through_the_first_clean_up]
- **S21** A damaged line (a crash mid-write, even inside a character) should be skipped and the rest still read; the next entry should start on a line of its own. [tracker: AU-40] [test: test_history_store.py::test_a_damaged_line_is_skipped] [test: test_audit_saving.py::test_history_reads_past_a_cut_character]
- **S22** A name containing a line or paragraph separator should not split or lose an entry. [tracker: AU-94]
- **S23** Recording should never slow a save: the save only queues; comparing and picture copies run on the History thread (gremlin.threads, bounded waits), which ends by itself when idle. [test-plan: HISTORY-A] [test: test_history_store.py::test_the_writer_ends_by_itself]
- **S24** At quit everything queued should be written and quit should wait for the writer only a bounded time; History should never stop quit, also when its folder can't be made. [tracker: AU-48] [tracker: AU-113] [test: test_audit_saving.py::test_history_close_writes_at_once] [test: test_audit3_saving.py::test_quit_goes_on_when_the_history_folder_cant_be_made] [test: test_audit2_coverage.py::test_quit_closes_history_between_the_two_writes]
- **S25** Only one running copy of the program should write the history (the lock file). [tracker: AU-41]
- **S26** The history folder should follow Options > Folders > History folder. [test-plan: AUDIT2-F-H-REST]
- **S27** After the history folder is moved, the old entries stay in the old folder and the window shows only the new one. [user confirmed 2026-10-06; was code only]

### History window

- **S28** Tools > History should list every saved change, newest first, each with its title, date and time, and area. [help: History] [test-plan: HISTORY-C]
- **S29** Show should narrow the list to All, Profile, Module files, Button Map or Settings; Search should find words in the title and in what it is about (device, input, file). [help: History] [test: test_history_window.py::test_it_lists_the_devices_changes]
- **S30** Picking a change should show Before and After: an input's actions as readable lines (action names and their settings), a module file's changed parts, settings by their Options names, a whole profile by its size. [test-plan: HISTORY-C] [test: test_history_window.py::test_a_change_before_and_after]
- **S31** History in an editor should open the window for just what that editor shows: the selected Configuration row (device, input, mode), a Logical Device control, Module Setup and Calibration (by the device's own module file, so twin sticks stay apart), the Button Map's File menu, and Options (settings). [help: History] [tracker: AU-107] [tracker: AU-71] [test-plan: PRESENCE-AUDIT]
- **S32** A filter should match a device id however it is written (case, braces, spaces). [test: test_history_restore.py::test_filters_match_a_device_id_however_written]
- **S33** The "Only ..." line should name what the filter is about; Show All should drop everything but the chosen area. [test: test_history_window.py::test_show_all_drops_the_device]
- **S34** Tools > History from the menu should always open on every change, not keep another window's filter. [tracker: AU-69]
- **S35** New changes should appear when the window comes back to the front, and with Refresh. [user confirmed 2026-10-06; was code only]
- **S36** With nothing to show it should say "No saved changes to show."; with nothing picked, "Pick a change to see it before and after." [user confirmed 2026-10-06; was code only]
- **S37** Picking the same change again should read it again (after a Restore). [test: test_history_window.py::test_picking_the_same_change_again_reads_it_again]

### Restore

- **S38** Restore Before and Restore After should ask first, then put that version back, and say what happened under the change. [help: History] [test-plan: HISTORY-C] [test: test_history_window.py::test_restore_before_puts_the_file_back]
- **S39** A restore of a module file or settings should itself be a new History entry at once; an input restore is recorded at the next Save Profile, and a whole-profile restore is not recorded. [glossary: Restore] [help: History] [changed 2026-10-07 to follow decision Q1, which wins over the earlier wording "A restore should itself be a new History entry"]
- **S40** An input's actions should go back into the open profile as an unsaved change, only when the entry's profile is the one open; otherwise it says "Open <profile> first." [help: History] [test: test_history_restore.py::test_an_input_goes_back_into_the_open_profile] [test: test_history_restore.py::test_an_input_needs_its_profile_open]
- **S41** An input restore that can't be read should change nothing (the input is not dropped first). [tracker: AU-02]
- **S42** An input restore into a mode deleted since should be refused with its reason, nothing changed. [user confirmed 2026-10-06; was code only]
- **S43** A module file should be put back at once, with its pictures, into today's modules folder; pictures it couldn't put back are named. [help: History] [tracker: AU-94] [tracker: AU-83] [test: test_history_restore.py::test_a_module_file_and_its_picture_go_back] [test: test_audit2_saving.py::test_restore_names_the_pictures_it_could_not_put_back] [test: test_audit2_saving.py::test_restore_writes_into_the_modules_folder_of_today]
- **S44** Settings should be put back at once; when one value can't be read nothing is applied; lists (action priorities) go back as lists. [tracker: AU-43] [test: test_history_restore.py::test_settings_go_back]
- **S45** A whole profile should be written as a copy next to the profile, named with its date, time and Before/After, never over another file, to open with File > Load Profile. [help: History] [tracker: AU-44] [test: test_history_restore.py::test_a_whole_profile_is_written_as_a_copy] [test: test_audit_saving.py::test_restored_profile_copies_never_overwrite]
- **S46** A part of the profile (modes, Logical Device, OSC, Profile Settings, scripts) can't be restored on its own; the window points to Restore on that save's entry. [user confirmed 2026-10-06; was code only]
- **S47** A version no longer kept (an older save's whole profile, a pruned entry) should say so and change nothing. [user confirmed 2026-10-06; was code only]
- **S48** "Created ..." entries have no Before and "Deleted ..." entries no After to restore; those buttons are off. [user confirmed 2026-10-06; was code only]

### Device Pack: export

- **S49** Tools > Device Setup > Device Pack should save a device's module file, its pictures, its wires (with their actions) and the output modules those wires send to into one zip. [help: Module files and Device Pack] [test-plan: G-PACKIMPORT]
- **S50** The device list should hold connected devices, devices the profile has seen and saved module files, and open on the first device with a module file. [test-plan: CLEANUP-C]
- **S51** A device without a module file can't be exported ("This device has no module file yet."). [user confirmed 2026-10-06; was code only]
- **S52** A damaged module file should be skipped and named in the log, never stop the window. [tracker: AU-93] [test: test_device_pack_import.py::test_a_damaged_module_file_is_skipped]
- **S53** Wires in these modes should list each mode where the device has actions, all ticked; unticked modes are left out. [help: Module files and Device Pack] [test: test_device_pack_import.py::test_export_can_take_some_modes] [test: test_device_pack_window.py::test_export_lists_the_modes_and_takes_notes]
- **S54** Made by and Note should go in the pack and show to whoever imports it. [help: Module files and Device Pack] [test: test_device_pack_window.py::test_import_shows_who_made_it]
- **S55** The pack should carry its format (2), the program version, the date and each mode's parent. [test-plan: G-PACKIMPORT]
- **S56** The pack should not carry this machine's device binding (bound id, bound name). [user confirmed 2026-10-06; was code only]
- **S57** A pack can't be saved inside the modules folder; a name without .zip gets .zip. [user confirmed 2026-10-06; was code only]
- **S58** Show Folder should open where the pack was saved. [help: Module files and Device Pack]

### Device Pack: import

- **S59** Opening a pack should list its pieces in sections (Input module, Button map, Map settings, Wires per mode, each output module), all ticked except Map view and Print area and print settings. [help: Module files and Device Pack] [test: test_device_pack_import.py::test_map_settings_rows_import_separately] [test: test_device_pack_import.py::test_the_rows_and_notes]
- **S60** A pack made by a newer program should be refused with "Update the program to import it." [help: Module files and Device Pack] [test: test_device_pack_import.py::test_a_newer_pack_is_refused]
- **S61** When a driver the pack's wires need is missing (vJoy, a vJoy device, ViGEmBus), it should say so as soon as the pack is opened and again in the warning, in the output module's own wording. [help: Module files and Device Pack] [test-plan: PACK-DRIVER-CHECK] [test-plan: DRIVER-WORDING-ONE-PLACE] [test: test_device_pack_import.py::test_opening_a_pack_says_the_vjoy_driver_is_missing] [test: test_device_pack_import.py::test_the_pack_and_the_xbox_viewer_say_the_same]
- **S62** Put this pack on should suggest the device with the pack's name; the text box is what is written to. [tracker: C17]
- **S63** A stick pack can't go on a vJoy, nor a vJoy pack on a stick. [user confirmed 2026-10-06; was code only]
- **S64** Before anything changes, a red Replace / Cancel warning should list the pieces, each mode's wire counts here and in the pack, outputs moved to another vJoy, controls the device doesn't have, missing Logical Device inputs (with a ticked "Create" box), driver problems, map pictures left unticked, the imported backup, and that the profile changes on disk only when saved. [help: Module files and Device Pack] [test-plan: G-PACKIMPORT] [test: test_device_pack_import.py::test_the_warning_says_what_is_replaced] [test: test_device_pack_window.py::test_the_warning_says_what_is_replaced]
- **S65** Each ticked piece should be added to what is on this machine: the pack's checked controls are added to the ones already checked, names are written one by one, and map chips replace only chips for the same controls. [help: Module files and Device Pack] [changed 2026-10-07 to follow decision Q3, which wins over the earlier wording "replace what is on this machine"]
- **S66** Controls the target device doesn't have (when it is connected) should be left out of checks and wires, and said. [help: Module files and Device Pack] [test-plan: G-PACKIMPORT]
- **S67** Friendly names should be written only for checked controls; a calibration curve that can't be used should not replace a good one. [tracker: AU-113] [user confirmed 2026-10-06; was code only for names]
- **S68** Each ticked mode should replace the device's wires and actions in that mode; other modes and other devices stay, also after save and reload. [help: Module files and Device Pack] [tracker: G-PACKWIPE] [test: test_device_pack_import.py::test_a_ticked_mode_is_replaced_and_others_stay] [test: test_device_pack_import.py::test_other_devices_keep_their_actions] [test: test_device_pack_import.py::test_adding_actions_keeps_the_ones_already_there]
- **S69** Only the actions the imported inputs use should be added; the replaced ones leave the profile when the import is kept; shared actions stay. [test-plan: G-PACKIMPORT] [test: test_device_pack_import.py::test_no_unused_actions_are_saved]
- **S70** An output put on another vJoy should take its wires with it. [help: Module files and Device Pack] [test: test_device_pack_import.py::test_wires_follow_the_output_they_were_put_on]
- **S71** Missing modes should be created under their parent from the pack; when the parent isn't here, under Default, and said. [help: Module files and Device Pack] [test: test_device_pack_import.py::test_modes_keep_their_parent]
- **S72** Missing Logical Device inputs should be created only when that box is ticked; otherwise the wires are kept and the note says they do nothing until added. [help: Module files and Device Pack] [test: test_device_pack_import.py::test_missing_logical_inputs_can_be_created]
- **S73** The previous module file should be kept in the imported folder with a dated name; a picture that is overwritten is kept there too. [help: Module files and Device Pack] [user confirmed 2026-10-06; was code only for pictures]
- **S74** The profile should change in memory only; the user saves it to keep the wires. [help: Module files and Device Pack]
- **S75** Configuration Appearance, Output View Appearance and where the photo sits should come with the pack. [test-plan: G-PACKIMPORT] [test: test_device_pack_import.py::test_configuration_appearance_comes_with_the_pack] [test: test_device_pack_import.py::test_the_photo_keeps_its_placement]
- **S76** When a module file or picture can't be written, what was written for it should be put back and nothing replaced, and the previous import stays undoable. [tracker: AU-93] [test: test_device_pack_import.py::test_a_picture_that_cannot_be_written_puts_everything_back] [test: test_device_pack_import.py::test_an_output_picture_that_cannot_be_written_is_reported]
- **S77** An import that matches or writes nothing should keep the previous Undo Import. [tracker: AU-113] [test: test_device_pack_import.py::test_an_import_that_matches_nothing_keeps_the_last_undo] [test: test_audit3_saving.py::test_an_import_that_wrote_nothing_keeps_undo_import] [test: test_device_pack_window.py::test_a_failed_import_keeps_undo_import]
- **S78** Import onto a damaged module file should be refused, pointing to Start Fresh, as every other save does. [user confirmed 2026-10-06; was code only] [changed 2026-10-07 to follow decisions Q2 and D-SYS-F1, which win over the earlier wording "replaces it and keeps the old one in imported"]
- **S79** A wire import that fails partway should undo everything it did and say so. [user decision: A3 (Q20)] [changed 2026-10-07 to follow decisions Q20 and D-SYS-A3 (pending and gap notes removed)]

### Undo Import

- **S80** Undo Import should put back the module files (old content, or remove a new file), the pictures, the device's wires in the replaced modes, and remove the modes and Logical Device inputs the import created (a mode only when empty, with the full Manage Modes delete). [help: Module files and Device Pack] [test-plan: G-PACKIMPORT] [tracker: AU-112] [test: test_device_pack_import.py::test_undo_import_puts_everything_back] [test: test_audit3_modes.py::test_undo_import_deletes_a_mode_everywhere] [test: test_device_pack_window.py::test_replace_then_undo]
- **S81** Undo Import should be offered until the next import or closing the window; after that the actions the import replaced leave the profile. [help: Module files and Device Pack]
- **S82** Opening another pack should also end Undo Import. [user confirmed 2026-10-06; was code only] (help doesn't say so: Q6)
- **S83** When another profile is open, Undo Import puts the files back but not the wires, and says so. [user confirmed 2026-10-06; was code only]
- **S84** A file Undo Import can't put back should be named. [user confirmed 2026-10-06; was code only]
- **S85** Module Setup's own "Import from" Undo puts the device's previous file back and binds the devices again. [test: test_audit2_coverage.py::test_undo_of_a_module_import_binds_the_devices_again] [tracker: AU-21]

### Deleted-device backups

- **S86** Delete Device should first keep a "stick deleted" autosave (a full pack: module file, pictures, wires in every mode) in the Device Library (10 S16-S21); if it can't be written or read back, nothing is deleted. [user confirmed 2026-10-06; was code only] [test-plan: H-19g-b for the folder] [changed 2026-10-08 to follow D-10-DELETE (Device Library, 10)]
- **S87** The Device Library folder (the deleted devices folder is removed) should be in the data folder by default and changeable in Device Library Settings (10 S36-S37). [changed 2026-10-08 to follow D-10-NO-DELETED-FOLDER] [test-plan: H-19g-b] [test: test_deleted_devices_folder.py] [changed 2026-10-08 to follow D-10-DELETED (Device Library, 10)]
- **S88** Delete File (Module Setup) should ask first and keep a "module file deleted" autosave in the Device Library; when it can't be kept nothing is deleted. [changed 2026-10-08 to follow D-10-NO-DELETED-FOLDER] [tracker: A2] [test-plan: SAFE-1] [test: test_data_safety.py]
- **S89** A deleted device's pack can be put back with Device Pack > Import, or from the Device Library with Copy to Another Stick (10 S22). [user confirmed 2026-10-06; was code only] [changed 2026-10-08 to follow D-10-COPY (Device Library, 10)]

### Auto Mapper

- **S90** Tools > Mapping > Auto Mapper (or a card's menu, which ticks that card's module) should make Map to vJoy actions: each claimed control of a ticked input module gets an action to the same number on a ticked vJoy output module, in the chosen mode. [help: Auto Mapper] [test-plan: WORKFLOW-2] [test: test_audit3_module_files.py::test_calibration_and_auto_mapper_open_on_the_cards_file]
- **S91** Inputs should be paired with outputs by list order; Combine onto selected outputs reuses the outputs in turn; input modules left without an output are named. [help: Auto Mapper] [tracker: AU-63] [test: test_auto_mapper_claims.py::test_input_modules_left_without_an_output_are_named]
- **S92** Only outputs the output module claims and the vJoy device has should be used; skipped ones are listed by range and reason. [help: Auto Mapper] [test-plan: P4c] [test: test_auto_mapper_claims.py::test_maps_only_to_claimed_outputs_and_reports_the_rest] [test: test_auto_mapper_claims.py::test_ranges]
- **S93** "Also claim the matching outputs on the output module" (off by default) should claim what the new actions need first, re-reading the output module file and refusing a damaged one. [help: Auto Mapper] [test-plan: MODULE-FILE-DAMAGE] [test: test_auto_mapper_claims.py::test_claim_option_claims_first]
- **S94** With Overwrite used inputs off, inputs that have actions should keep them, and a vJoy output already used by another input in that mode should not be used again. [help: Auto Mapper] [test: test_auto_mapper.py::test_get_used_vjoy_inputs_from_profile]
- **S95** With Overwrite used inputs on, it should ask first, then remove every action on those inputs in that mode (macros included) and leave no unused actions behind. [tracker: A13] [test-plan: SAFE-1-HANDS-ON] [test: test_profile_unused_actions.py::test_auto_mapper_overwrite_leaves_nothing_behind]
- **S96** The Overwrite choice should be remembered between openings. [test-plan: OPTIONS-TRIM]
- **S97** The new actions should be in memory only; to undo, load the profile again without saving. [user confirmed 2026-10-06; was code only] (dialog text)
- **S98** Every input in the profile, plugged in or not, and nested actions (inside Conditions, Chains, Tempo and the like) should count as using a vJoy output. [test: test_auto_mapper.py::test_get_used_vjoy_inputs_for_disconnected_device_in_profile] [changed 2026-10-07 to follow decision Q7, which wins over the earlier wording "should not count"]
- **S99** Only vJoy outputs; the Keyboard, OSC and Xbox cards have no Auto Mapper. [help: Auto Mapper] [tracker: AU-68]
- **S100** While the profile runs, the Auto Mapper, Device Pack and History windows should show a note that changes take effect the next time it starts. [test-plan: WORKFLOW-4] [changed 2026-10-07 to follow decision Q4 (Device Pack and History show the note too)]
- **S101** The lists should follow sticks being plugged in or out, keeping ticks. [user confirmed 2026-10-06; was code only]
- **S102** Esc should not close the Auto Mapper or Device Pack windows (a stick can send Esc). [test-plan: USABILITY-FIXES] [user confirmed 2026-10-06; was code only for Device Pack]
- **S103** The result line should say what was made in glossary words (actions, not mappings or bindings). [glossary] [test-plan: GLOSSARY-2] (code doesn't: Q8)
- **S104** Before and After should show what changed: changed lines get a soft tint (red on Before, green on After, from the theme so both themes read well) and a thin bar on the left edge; inside a changed line the changed words get a stronger tint; unchanged lines stay plain. The two sides line up row for row. "Previous change" / "Next change" move both sides together to the previous or next change. [user decision 2026-10-07: D-08-HISTORY-DIFF]
- **S105** After Create 1:1 Actions the Auto Mapper keeps the ticked modules ticked and selected, so Create again works on the same modules (what is shown is what Create uses). [user decision 2026-10-07: D-08-AUTOMAP-KEEP]
- **S106** Device Pack should open on the first device that can be exported; a device whose module file can't be read stays in the list marked "(file damaged)". [user decision 2026-10-07: D-08-PACK-START]
- **S107** Device Pack Export should be written in the background: the window stays usable, shows it is busy, Export is disabled until it is done (one at a time), and the result is reported when done (failures name the file, folder and reason). The device photo preview loads in the background at preview size. [user decision 2026-10-07: D-08-PACK-BG]
- **S108** The Auto Mapper's Select Mode should start on the toolbar's mode (the mode being edited), and its result should name the mode the actions went into ("Made 36 actions in Default"); when that is not the toolbar's mode it adds "The toolbar shows <mode>: switch to <chosen mode> to see them." [user decision 2026-10-07: D-08-AUTOMAP-MODE]
- **S109** When Create makes nothing for a control, the result should give the true reason: vJoy outputs another input already uses in that mode are listed as skipped ("Skipped vJoy 1 buttons 1-8: already used by another input in this mode"), not counted as inputs that kept their actions; when every output is skipped because the output module claims none, the result names the output module and points to "Also claim the matching outputs". [user decision 2026-10-07: D-08-AUTOMAP-REASON]

## 9. Questions for the user

- **Q1** The glossary and help say a Restore "is itself a new History entry". That is true for a module file and settings. An input restore only shows at the next Save Profile, and a whole-profile restore writes a copy that is never recorded. **Recommend:** change the glossary and help text to say this, rather than recording unsaved edits.
- **Q2** (F1) A Device Pack import onto a damaged module file replaces it today (a backup is kept). **Recommend:** refuse and point to Start Fresh, as every other save does.
- **Q3** Help says each ticked piece "replaces" what is here, but Checked controls are added to the ones already checked, names overwrite one by one, and map chips replace only chips for the same controls (others stay). Which do you want? **Recommend:** keep adding (safer, nothing lost), and change the help and warning to say "adds the pack's checked controls".
- **Q4** Device Pack import and History Restore change the profile and module files while the profile runs, with no note. The Auto Mapper shows "changes take effect the next time it starts". **Recommend:** show the same running note in the Device Pack and History windows.
- **Q5** Undo Import puts back the files as they were before the import, even if you saved the Button Map or Module Setup after the import, and it drops edits made to the imported inputs. **Recommend:** if a file changed since the import, ask before putting it back.
- **Q6** Opening another pack ends Undo Import, but help says only "until you import again or close the window". **Recommend:** add "or open another pack" to the help.
- **Q7** When deciding which vJoy outputs are already used, the Auto Mapper looks only at sticks that are plugged in and only at top-level Map to vJoy actions (not inside Conditions, Chains, Tempo...). So it can make two inputs send to the same vJoy output. **Recommend:** count every input in the profile and nested actions.
- **Q8** The Auto Mapper says "Created 36 mappings, retained 0 previous bindings." **Recommend:** "Made 36 actions; 0 inputs kept their actions."
- **Q9** With "Also claim" on, if the output module file is damaged or can't be written, the Auto Mapper still makes actions to the outputs it couldn't claim (they are then blocked at Run as not claimed). **Recommend:** skip those and list them as "not claimed".
- **Q10** Moving the history folder (Options > Folders) leaves the old entries behind. **Recommend:** move the history files with the folder, or say in Options that old entries stay in the old folder.
- **Q11** The size and age limits are applied only at the first entry of a session, so a long session can grow a file past its limit. **Recommend:** accept (cheap, files are trimmed at the next start), and say "checked at start" in the Options description.
- **Q12** (F3) Start Fresh and the pack's own clean-up after a failed write leave no History entry. **Recommend:** yes, record them.
- **Q13** Before and After of a module file show raw JSON (`claim`, `nodes`, `hwId`). **Recommend:** show readable lines, reusing the Device Pack's rows ("Button 3 - Fire", "Calibration: Axis 1 ...").
- **Q14** Restore of a module file writes the file by its stored name, not by the rule for which file a device uses; after a rename or a rebind the device may not use the restored file. **Recommend:** restore through the module-file owner of map 1 (`store.replace`).
- **Q15** Button Map > File > History filters by device name and Button Map only: twin sticks are mixed, and a save that also changed checks (filed under Module files) is hidden. **Recommend:** filter by the device's own file name and all areas, as Module Setup does.
- **Q16** The Configuration row's History shows that input's changes from every profile; Restore then says "Open <profile> first". **Recommend:** filter by the open profile too; Show All widens it.
- **Q17** Deleted-device packs, Delete File copies and imported backups are never cleaned up and are not in the User Guide. **Recommend:** keep them forever (the user deletes them), and add a help paragraph on where they are and how to bring a device back (Device Pack > Import).
- **Q18** Output modules in a pack are imported without checking the vJoy device's real size, so checks past its last button can be written. **Recommend:** apply the vJoy limits as for sticks and list what is left out.
- **Q19** Export of a device whose module file is damaged says "This device has no module file yet." **Recommend:** say it is damaged and point to Start Fresh.
- **Q20** (A3, AU-118) A wire import that fails partway leaves the inputs it removed gone and the modes and Logical inputs it made, with no Undo. **Recommend:** undo everything it did and say so.
- **Q21** Undo Import removes the Logical Device inputs the import made even if you added actions to them since. **Recommend:** keep a created Logical input that now has actions, and say so.

## 10. Known gaps

**Code differs from the spec or a rule**

1. Device Pack import overwrites a damaged module file (`device_pack.py:1793, 1835` -> `_write_module:1636`). Q2, F1.
2. Partial wire-import failure: `_apply_wires` (`device_pack.py:1474-1503`) creates Logical inputs (1476) and modes (1490), removes the device's inputs from the ticked modes (1498), then calls `add_inputs` (1499). An exception after 1498 returns an error without putting `removed` back, and without Undo for the modes and Logical inputs. Tracker AU-118 (open). Q20.
3. Pack pictures written in place (`device_pack.py:1162`); export zip written in place (`hardware_profile.py:1943`).
4. Two safe writers with History in each (`_replace_file` vs `module_file.write_text`); `_replace_file` lacks the refused-swap fallback. Map 1.
5. No History entry for Start Fresh (`module_file.py:107`) or `_put_back` removals (`device_pack.py:1564`). F3.
6. `history.entries()` flushes the queue on the UI thread (`history.py:289`): profile comparisons and picture copies can run on the UI thread, side by side with the writer; `_last_pictures` unlocked. SUSPECTED race (entries out of order, wrong "before" pictures).
7. First module-file save of a session: the "before" pictures are read from disk after the write (`history_modules.py:206-214`, the comment at 51-52 admits it). A picture replaced under the same name gets the new picture as its "before". SUSPECTED.
8. Restore of an input is not recorded until Save; restore of a whole profile is never recorded (`history_model.py:258` writes a non-module file). Glossary says otherwise. Q1.
9. Restore of a module file ignores the device-to-file rule (`history_model.py:271-272`). Q14.
10. Raw JSON in module Before/After (`history_model.py:116-124`). Q13.
11. Limits applied once per session (`history.py:342-346`). Q11.
12. The History window reads and parses all four files on the UI thread every time it becomes active (`DialogHistory.qml:136-143`), and Restore reads them all again (`history.entry` -> `entries`). With 20 MB per file this can freeze the window. SUSPECTED.
13. Moving the history folder leaves old entries behind (`util.history_dir`). Q10.
14. Button Map History filter by name and one area (`DialogJoystickButtonMap.qml:2495`). Q15. Configuration row filter has no profile (`BindingCatalog.qml:1583`). Q16.
15. Auto Mapper result wording "mappings / bindings" (`auto_mapper.py:255`); the glossary guard doesn't read Python result strings. Q8.
16. Auto Mapper `_vjoy_limits` duplicates `output.vjoy_layout` and reads the device list directly (`auto_mapper.py:205-214`).
17. Auto Mapper used-output check skips unplugged sticks, the Logical Device and nested actions (`auto_mapper.py:216-238`). Q7.
18. Auto Mapper "Also claim" keeps going after a refused or failed write with a claim that only exists in memory (`auto_map.py:130-141`). Q9.
19. `assert` in production (`auto_mapper.py:228`).
20. Device Pack edits `profile.inputs` and `device_database` directly (`device_pack.py:1498, 1501, 1606`).
21. Restore reads `cfg._data` (`history_model.py:307`).
22. Two Undo Import systems, same function name (`hardware_profile.py:649-688`, `device_pack.py:1538-1633`).
23. No running note or guard in the Device Pack and History windows. Q4.
24. Undo Import overwrites later edits (`device_pack.py:1578-1589` puts back old bytes without checking). Q5.
25. Output modules in a pack get no vJoy size limits (`device_pack.py:1836` calls `_merge_module` without `limits`). Q18.
26. Damaged file on export reads "no module file yet" (`device_pack.py:628-631` via `_read_json_dict`). Q19.
27. Help says pieces "replace"; checks are merged (`device_pack.py:983-989`). Q3.
28. `peekPackDevice` builds the whole zip, pictures included, on the UI thread each time the export device changes (`hardware_profile.py:1872`). SUSPECTED slow with large photos.
29. The pack's preview folder in `%TEMP%` is never removed at quit (`device_pack.py:713-733`).
30. Undo Import deletes created Logical inputs even if they have actions now (`device_pack.py:1620-1622`). Q21.

**Open tracker items for this subsystem**

- AU-118 (open): Device Pack partial failure leaves inputs, modes and Logical inputs; also OK on a shared Merge Axis (action map).
- AU-64 (open, part): photo folders follow the module file; only the pack export file name still goes by the device's own name, so a renamed or twin stick's pack file name can differ.
- AU-41 (won't fix): two running copies could lose History entries; the lock file prevents it.
- Decisions waiting in `system-maps.md`: F1 (pack onto a damaged file), F3 (Start Fresh in History), A2 (History restore of a shared action), A3 (pack failing partway).

**Things nothing owns**

- Profile copies written by Restore (next to the profile): no list, no clean-up.
- `modules\imported\` backups (module files and pictures): grow forever; Module Setup lists them as import sources.
- The deleted devices folder (packs and copies): grows forever; no help topic.
- `history\files\` is cleaned only by `prune`; a picture referenced only by an entry in a moved history folder is lost to the new one.
- The pack's `%TEMP%\gremlin-pack-*` folder.
- History of the module-file binding store (`module-file-bindings`): internal, so a Restore of a deleted module file doesn't bring back its bindings.

## 11. Size and test coverage

**Size**: about 5,000 lines in this page's own files (history 915 Python + 436 model + 326 QML; Device Pack 1,893 Python + 952 QML + about 250 lines of slots and helpers in `hardware_profile.py`; Auto Mapper 257 + 145 + 80 + 30 Python + 269 QML). Tests: about 2,100 lines in the files named below plus parts of 6 audit test files.

**Covered**: the six main test files for this page (51 tests) pass when run alone (`test/run_tests.py` on `test_history_store`, `test_history_recording`, `test_history_restore`, `test_device_pack_import`, `test_auto_mapper`, `test_auto_mapper_claims`). Off-screen window tests: `test_history_window.py`, `test_device_pack_window.py`, `test_tool_windows_fit.py`, `test_usability_fixes.py::test_device_pack_has_no_layout_loop`.

**Not covered (obvious)**

- History: two threads running the queue at once (`entries` while the writer runs); the "before" pictures of a file's first save in a session; a Save As entry; restore of an input into a deleted mode; restore of a settings key that no longer exists ("Settings put back." with nothing applied); the window's Search and the editor filters other than Module Setup (Configuration row, Logical, Button Map, Calibration, Options); a large history file (speed).
- Device Pack: `exportPack` slot itself (path checks, inside-modules refusal, .zip suffix); import onto a damaged file; failure inside `_apply_wires` (AU-118); Undo Import after the profile changed or after a later Button Map save; Undo Import's "another profile is open" path; output modules past the vJoy's size; a zip with a bad `wires.json` or `outputs/*.json`; `importPack` with an empty selection.
- Deleted devices: `delete_device(..., save_copy=True)` (pack written, read back, refused when unreadable) has no test; importing such a pack back.
- Auto Mapper: Combine onto selected outputs with more inputs than outputs (mapping result, not just the message); Overwrite on with nested actions; twin sticks (`_source_uuid` by name picks the first); "Also claim" when the output file is damaged or can't be written; the dialog's tick handling after Create (only checked by hand, test-plan AM-05).

## 12. Review (user, 2026-10-06)

Approved by the user as recommended (2026-10-06, blanket approval of the remaining pages): every [code only] statement in section 8 is confirmed, except where a question's recommendation changes it; every question in section 9 is decided as its **Recommend** says. Where a recommendation and a section 8 statement disagree, the recommendation wins.

| Q | Decision |
|---|---|
| All | As recommended in section 9 |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.
