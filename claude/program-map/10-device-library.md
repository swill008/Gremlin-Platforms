# Device Library

**Approved by the user 2026-10-08. S1-S56 (with S20a, S53a) built (2026-10-08 to 2026-10-09).** Written from
the design discussion of 2026-10-08 (decisions D-10-* in
`claude/decisions.md`) and the off-screen Qt prototype in
`.agent-logs/handson/DL/` (renders `dl_main.png`, `dl_menu.png`,
`dl_settings.png`, `dl_copy.png`, `dl_swap.png`, `dl_output.png`; not in
git). It replaces Swap Devices (04 S77-S83) and takes over the deleted
devices folder, which goes (03 S62, S90-S91, S98; 08 S86-S88; D-10-NO-DELETED-FOLDER).

## 1. Purpose

One place for every device the program has known: sticks plugged in now,
sticks set up here but unplugged, deleted sticks, and sticks shared by other
people that were never plugged in here. For each device it keeps **saved
setups**: stored copies of its settings and bindings, each with a name and a
description, made by the user or kept automatically (**autosaves**) before
anything replaces them. From a saved setup the user can **copy** it onto a
stick that is plugged in, **swap** two sticks' settings, or **change which
vJoy** a stick's bindings send to. Nothing is moved away from its source:
copying never changes the saved setup or the stick it came from.

Typical uses: a new stick gets an old (unplugged, broken) stick's bindings;
two sticks trade everything; two sticks trade vJoy outputs so a game sees
them the other way round; a friend's shared setup is put on your stick.

## 2. Files

On disk:

| Path | What it holds |
|---|---|
| `<library folder>\` (default `<data folder>\device library`) | The Device Library. Its own setting, `device-library-folder`; the deleted devices folder and its setting are removed. |
| `<library folder>\library.json` | The list: devices (name, description, device id when known, kind: set up here / deleted / from a pack) and their saved setups (name, description, date, origin, whether it is the user's, what it holds, which profiles and modes its bindings came from, vJoy outputs). |
| `<library folder>\<device>\<saved setup>.gmap` | From 2026-10-11 (D-03-DEVICE-FOLDERS, D-10-GMAP-SETUPS; S60, S63) each new saved setup is the device folder zip Export makes (08 S111, built by `device_zip.build_gmap`): `gmap.json`, `module.json`, `pictures/`, `bindings/wires.json`, `bindings/outputs/`; a stick with no module file here gives a bindings-only `.gmap`, a damaged module file is kept as it is (`gmap.json["damaged"]`, S20a); an autosave also holds every file of the device's folder exactly under `exact/` (S18). |

Code (built 2026-10-08/09):

- `gremlin/device_library.py` (2587 lines; from 2026-10-11 (D-FIXLIST-B2) reads and writes `.gmap` only (`_read_pack`, `GMAP_EXT`, `_export_name` adds ".gmap"); a file's Made by and Note become the setup's reason and description; store messages say "device file (.gmap)"; from 2026-10-11 (D-07-BACKGROUND-PLANES) a setup's photo is the map's bottom background picture, `store.device_photo_ref`, found in the zip by its place in the folder or by name at a pack's root; from 2026-10-11 (D-03-DEVICE-FOLDERS, D-10-GMAP-SETUPS) every new saved setup is a `.gmap` built by `device_zip.build_gmap` (`_build`, bindings-only and damaged too), an autosave adds the whole folder exactly (`_with_folder`, `EXACT_ENTRY`), `is_gmap` tells a `.gmap` from an older Device Pack, `folder_files(setup_key)` returns the files an autosave kept, `_export_name` gives an export the right extension (`.gmap`, or `.zip` for an older pack), and Remove from Library removes the device's folder through `_remove_folder` → `store.delete(name, guid, pictures=True)`; from 2026-10-10 (F1, SHAKE-DAMAGE-03) one unreadable `library.json` row is left out and the rest listed (`_readable_setup`, `_readable_record`), a list nested too deep (RecursionError) reads as damaged, and pack parts are read through `_json_part`): the library owner (`is_built_in_guid` -> `device_class.can('library_builtin', guid)`, by id only, 03 S90b; connected = `_connected`: a device with an id and `hardware.plugged_in`, 03 S90a; `_view` joins a plugged-in stick to the row / record with the same id only, never by name), the one writer of `library.json` and the packs: folder, devices, save_setup, autosave (S16-S21) and its limit, rename/describe/delete, import_pack/export_setup, tidy, size, search, settings, last change, History text and Restore for Library entries (S51). D-TESTLIST-1 (2026-10-11): `restore_history` puts back only that entry's change, a three-way merge with today's list (`_merge`, `_merge_keyed`, `_merged_list`); a device removed later comes back as it was then with only the restored setups; `_keep` returns `paths` (the autosave's written files, logged by the trace) (S51).
- `gremlin/library_copy.py` (1423; from 2026-10-11 the stick's module file is found with `store.module_file` (its own folder by id); `_put_module_back` writes into `store.ensure_device_dir` and `_put_pictures_back` puts an autosave's pictures back from `library.folder_files` (S18); `_write_current` names a `.gmap` scratch file for a device folder zip): `_connected` -> `hardware.plugged_in` (by live id). `_copy_checks` / `plan_output` / `change_output` use `is_built_in_guid`; `_special` uses `device_class.is_internal_input` (03 S90b), so a stick named "Keyboard" is a normal device. Copy to Another Stick, Restore to This Stick, Change vJoy Output (renumbers Map to vJoy, nested actions too) and undo_change/undo_last (S22-S25, S30-S33, S48). Copy targets: `_connected` -> `device_class.can("copy")` + `hardware.plugged_in` (external devices only, by live id; 03 S90a/S90b); `plan_output` / `change_output` refuse via `_copyable` -> `can("copy")`. Test `test_library_copy_targets.py` (4). Restore of a built-in (2026-10-09, S6/S6a): `restore_to_stick` sends a `library_builtin` device (Keyboard, OSC, Logical Device) to `_restore_built_in` (no stick checks): autosave "Autosave: before Restore of …", the setup back into the profiles it came from, one Undo step "Restore X to Y", one History entry.
- `gremlin/library_swap.py` (559; from 2026-10-11 (D-07-BACKGROUND-PLANES) the Device Mapping Editor keys swapped are `_MAP_KEYS = ("nodes", "ui")` (both planes are in `nodes`; `image` / `photo` are gone), and an old map is turned into layers first in memory (`_swapped_docs` → `planes_once.old_photo_to_layer`, ONE-TIME OT-2); from 2026-10-11 `_move_pictures(doc, from_dir, to_dir, added)` copies the device map pictures into the other stick's own folder through `store.copy_pictures` (S61: a picture is never shared) and `_rewrite_refs` points the map at them; a failed swap takes the copied pictures out again): Swap with Another Stick (S26-S29; `_refusal` -> `device_class.can('swap', id)`, `_refused_word` from `display_name`, the Xbox text kept "the Xbox controller", 03 S90b): module-file parts through `modules/store.py`, bindings through `swap_devices` per ticked profile; autosave of both sticks first. `_refused_word` by `device_kind`: the Xbox pad "the Xbox controller", vJoy "vJoy", the others from `display_name`.
- `gremlin/library_part_id_once.py` (171; 2026-10-11, D-FIXLIST-B4; ONE-TIME, tracker OT-4): at start, after `register_config_options()` (`run_if_needed()`), renames the Library part id `button_map` to `device_map` in `library.json` once (defaults, each setup's `holds`, the last change's `parts`), after a checked backup in `<data folder>/backup/<date> library part id move/`; holds the Library lock, no History entry, refuses the real folder under tests. Remove before release with OT-1, OT-2, OT-3. D-TESTLIST-1 (2026-10-11): renames the id anywhere it is a value, including each setup's `covers` list.
- `gremlin/library_profiles.py` (517): profiles that aren't open (S33-S34): profiles_using, read_profile, Batch (one change across several profiles; the open one changed in memory), responsive()/background() (section 6).
- `gremlin/library_undo.py` (197): Undo and Redo steps for this session's Library actions (S53); emptied by Clear History (08 S12b) through on_cleared. D-TESTLIST-1 (2026-10-11): `put_back` titles the step with `history.restore_title` and groups it with `begin_group` extra `{of, ofAll, restore}` (08 S39a).
- `gremlin/device_forget.py` (133): Remove from Library forgets the device's settings: friendly name, Home card settings (hidden, order, size, compact), calibration kept in the settings (S52, D-10-REMOVE-ALL).
- `gremlin/device_aliases.py` (316): the names the user gives devices (S7), kept in the settings; the Library renames through it, `gremlin/ui/device_names.py` relays changes to QML. From 2026-10-11 (D-03-DEVICE-FOLDERS, 03 S131) `set_alias(key, value) -> str` renames the device's folder first (`_rename_folder` → `store.rename_device_dir`) and, when that is refused, saves nothing and returns the reason (`DeviceNames.setAlias` returns it to QML); built-ins (Keyboard, OSC, Logical Device, Xbox) and vJoy devices keep their fixed folder names (`_device_id` returns None); a History put-back of the names syncs the folders (`_settings_changed` → `_sync_folders` → `store.sync_dir_name`, logged, no message).
- `gremlin/ui/device_library_model.py` (1568; from 2026-10-11 (D-FIXLIST-B2) `_SETUP_SUFFIX` ".gmap"; `importPack` refuses any other file): `DeviceLibraryModel`, the only thing the window's QML talks to (context property `deviceLibrary`, made in `joystick_gremlin.py`): rows, filters, search, selection, plans, Copy/Swap/Change/Restore, Remove/Delete/Clear Setup groups, Undo/Redo, settings, busy state; results come back as `result(map)`.
- `qml/WindowDeviceLibrary.qml` (1518; from 2026-10-11 (D-FIXLIST-B2) the choosers filter "Device files (*.gmap)" (kind "device"), `_packName()` gives "<name>.gmap", drops take `.gmap` only, File and right-click **Import Device…**, chooser title "Import Device"): the window: menu bar (File, Edit, Device, View, Settings, Help), device and saved setup list, details, right-click menus, message line with Undo link, status bar (size, last change), shortcuts (F1, F2, Ctrl+Z/Y, Delete, Menu, Ctrl+F). Built on the shared pieces: deletes, removes and Clear Setup ask the shared question (`askConfirm(title, text, action, run)`, `_lib.asking`) with red buttons; search is a `SearchBox` (×, "N found"); the message line is `MessageLine` (Undo link, S54); the status bar Undo / Redo is an `UndoBar`; empty lists show `EmptyState`; Device Pack import / export choose with `FilePicker` (`_importFile`, `_exportFile`, `_exportCurrentFile`; `exportSaved()` / `exportCurrent()` / `_packName()`).
- `qml/DialogLibraryCopy.qml` (341): Copy to Another Stick (S22-S25): From, To, what to copy, profiles and modes, what won't copy. Headings are `SectionHeading`.
- `qml/DialogLibrarySwap.qml` (244): Swap with Another Stick (S26-S29), warnings both ways. Headings are `SectionHeading`.
- `qml/DialogLibraryOutput.qml` (290): Change vJoy Output (S30-S32), one row per vJoy the stick sends to.
- `qml/DialogLibrarySettings.qml` (136): Device Library Settings (S36-S37): autosaves kept per stick, Copy/Swap default ticks, library folder (its chooser is a `FilePicker` that remembers the folder); shared headings.
- `qml/DialogLibraryTidy.qml` (135): Tidy Library (S38): what it would remove; removes only what stays ticked. Remove… asks the shared question (`askRemove()`: "Remove N item(s) from the Library?", red Remove from Library, Enter cancels).
- `qml/device_library_open.js` (27): opens the window on a device and dialog (Home, Tools, card menu); passes the row menus' Delete Device / Module Setup / Device Mapping Editor / Show on Home to `Main.qml libraryAction`.
- Help: the Device Library chapter, `qml/help/device_library.js` (page 01 owns the Help book).

Callers elsewhere: `gremlin/ui/hardware_profile.py` (`_autosave`, `_autosave_before_pack`: the Delete Device, Delete File and Device Pack import autosaves), `gremlin/modules/store.py` (reads the list's records), `gremlin/ui/history_model.py` (Library entries' text and Restore), `qml/StatusCard.qml` / `StatusPage.qml` / `Main.qml` (card menu items, Tools menu, `libraryAction`), `qml/main_commands.js` (`tools.deviceLibrary`).

Logical Device as a built-in (D-04-LD-FILE, 2026-10-09; S6, S6a): `device_class` puts it in `library_builtin`; `device_library.py` / `device_library_model.py` save, restore, export and import its layout (`LogicalRows.to_dict` / `load_dict`, written through `gremlin/logical_device_file.py`, page 06); `modules/store.py` and `registry.py` skip the plugged-in check for built-ins without hardware by class (`no_hardware_limits`); `store._reload_logical_device(path)`, called from `replace()` and `write_text()`, reloads the Logical Device after Restore, Import, Undo or a History restore of its file. `gremlin/ui/device_pack.py apply_zip` carries the Logical Device's `logical-device` layout key in the same single module-file write (Restore and Import Device Pack), and `store.replace` reloads it, so the card photo redraws (`logicalDeviceReloaded`).

Copy, Swap and Change vJoy Output change profiles only through the
profile owner, and module files only through `modules/store.py`.

## 3. What it owns

- The library list and its saved setups (files above): new ones are `.gmap` device folder zips (S60, S63); no `.zip` is written or read (D-FIXLIST-B2, 2026-10-11). `gremlin/library_copy.py` writes its scratch file as `current-N.gmap`; `gremlin/ui/folder_memory.py` kind "device" (was "device-pack").
- The autosave rules and limit (Device Library Settings).
- Device names and descriptions for devices with no module file here (deleted,
  and those that came from a pack). For devices set up here the name is the module file's friendly
  name (S6); the user's names live in `device_aliases` (settings `devices/display/aliases`).
- Restore of a built-in input (`library_copy._restore_built_in`): its autosave, Undo step and History entry.
- This session's Undo/Redo steps (`library_undo`, in memory; emptied by Clear History).
- The window's selection, open rows, filters, search and waiting plans (`DeviceLibraryModel`, in memory).

## 4. Entry points

| Where | What |
|---|---|
| Toolbar **Device Library** button (`Main.qml _deviceLibraryButton`, every page; tests `test_device_library_DD_menus.py::test_the_toolbar_has_the_device_library_button_not_home`, `test_mode_bar.py::test_the_toolbar_device_library_button_opens_the_window`); Tools › Device Setup › **Device Library…** (`tools.deviceLibrary`) | `Main.qml openDeviceLibrary` → `device_library_open.js` opens the window or brings it to the front. |
| Card menu: **Copy Setup to Another Stick…**, **Swap with Another Stick…**, **Change vJoy Output…** (`StatusCard.qml` 493-497) | Open the window on that card's device and the matching dialog (`openOn(name, guid, action)`). |
| Built-in or not, may it swap / copy (03 S90b) | `device_library.is_built_in_guid`, `library_copy._special`, `library_swap._refusal` → `device_class.can` / `is_internal_input` (by id). |
| Device plugged in / out | `device_library._connected` / `_view`, `library_copy._connected` → `hardware.plugged_in` (by id, 03 S90a); rows join by id only. |
| Window menus, right-click menus, double-click (S40), shortcuts | `DeviceLibraryModel` slots: `copy`, `swap`, `changeOutput`, `restoreToStick`, `saveToLibrary`, `rename`, `describe`, `keep`, `deleteItem` / `deleteMany`, `beginRemove` / `removeDevice` / `endRemove`, `beginClearSetup`, `deleteSavedSetups`, `importPack`, `exportSetup` / `exportCurrent`, `tidyPreview` / `tidy`, `setSettings`, `undo` / `redo`. |
| Row menu: Delete Device, Module Setup, Device Mapping Editor, Show on Home | `device_library_open.js toMain` → `Main.qml libraryAction`. |
| Row menu: Show in History (S56) | Tools › History filtered to the device. |
| Any delete / remove / Clear Setup in the window | `askConfirm(title, text, action, run)` → `Confirm.ask` (red named button; `_lib.asking` while open) → the model slot (`deleteItem` / `deleteMany`, `removeDevice`, `deleteSavedSetups`, `beginClearSetup`). Tidy: `_tidyDlg.askRemove()` → `tidy`. Restore to stick: `_restoreDlg.ask()` → `restoreToStick` → `library_copy.restore_to_stick` (a built-in → `_restore_built_in`, no plugged-in check). |
| Import Device… / Export (`.gmap` only, D-FIXLIST-B2) | `FilePicker` (kind "device"; `_importFile`, `_exportFile`, `_exportCurrentFile`) → `importPack`, `exportSaved()` / `exportCurrent()` (`_packName()` suggests the name) → `exportSetup` / `exportCurrent`. |
| Message line Undo link; status bar Undo / Redo | `MessageLine` / `UndoBar` → `undo` / `redo`. |
| Delete Device / Delete File (Home) | `hardware_profile.delete_device` / `delete_module_file` keep the "stick deleted" / "module file deleted" autosave first (S16-S21); refused when it can't be kept (S20). |
| Device Pack import onto a stick | `hardware_profile._autosave_before_pack` keeps the "before a Device Pack" autosave; a pack imported in the Library is added as a saved setup (S35). |
| Tools › History: Restore of a Library entry; Clear History | `history_model` → `device_library.restore_history`; `library_undo` on_cleared empties the steps. |

## 5. Talks to

Device Pack (export and import code; `device_pack.apply_zip` writes a built-in's
setup, the Logical Device layout key included; from 2026-10-11 `device_pack._zip_readable` reads a `.gmap` through `device_zip.read_gmap` and `_from_gmap` restores a damaged `.gmap`'s bindings, S20a), device folder zips (`modules/device_zip.py`, page 08: `build_gmap` for every saved setup and export), the device's folder (`store.module_file`, `ensure_device_dir`, `copy_pictures` for Swap, `delete(..., pictures=True)` for Remove from Library, `rename_device_dir` through `device_aliases`), module store (`modules/store.py`;
`replace` reloads the Logical Device), the
profile owner (bindings in the open profile and saved profiles, through
`library_profiles`), History (every change it saves is a History entry like
any other save; Library entries restored through `device_library`), the device
list (which sticks are plugged in), output modules (which vJoy outputs are
claimed), settings (`device_aliases`, `device_forget`), the main window
(`libraryAction`: Delete Device, Module Setup, Device Mapping Editor, Show on Home).

The device's background picture (2026-10-11, D-07-BG-COMPOSITE, S11, 07 S157): `device_library.photo()` shows `store.shown_photo_ref` (the saved setup's `pictures/device-photo.png`, else its bottom background picture); a Device Library restore changes the module files, and the module files changed notice has `DevicePhotoMaker` make the picture again.

## 6. Threads and timers

The owners run on the main thread, which owns the open profile, the device
lists, the module files' registry and the settings. Inside
`library_profiles.responsive()` their file work (reading and writing saved
profiles, building packs) runs on a program thread through `background()`
while the event loop keeps going; the window shows it is busy and user input
waits. Only the saved profiles' scan (`profilesUsing`) and the size measure
run wholly on a program thread (`threads.start`). One change at a time.

Timers: one plan timer per dialog (`_PLAN_SETTLE_MS` 150 ms: only the newest
plan runs, after the ticks settle); the Remove / Clear Setup group limit
(`_GROUP_LIMIT_MS` 60 s: a group left open is closed as one History entry).

## 7. Rule breaks

None planned. Layer rule: the window never touches devices, vJoy or ViGEm; it
works on files and the profile through their owners.

## 8. Behaviour spec

### A. The window

- **S1** The Device Library should be a separate window, like the Device Mapping Editor, with its own menu bar: **File** (Import Device…, Export Saved Setup…, Open Library Folder, Close), **Edit** (Undo, Rename… (F2), Delete…, Tidy Library…; the description is edited in place), **Device** (Save to Device Library…, Copy to Another Stick…, Swap with Another Stick…, Change vJoy Output…), **View** (Connected, Not Connected, Deleted, Autosaves, Expand All, Collapse All, Search…), **Settings** (Device Library Settings…), **Help** (Device Library Guide, F1; S42). Menus follow 01 S66 (only what can be used now). [changed 2026-10-11, user: D-FIXLIST-B2] (built 2026-10-11) [test: test_b2_lib.py, test_b2_e2e.py] (was: The Device Library should be a separate window, like the Device Mapping Editor, with its own menu bar: **File** (Import Device Pack…, Export Saved Setup…, Open Library Folder, Close), **Edit** (Undo, Rename… (F2), Delete…, Tidy Library…; the description is edited in place), **Device** (Save to Device Library…, Copy to Another Stick…, Swap with Another Stick…, Change vJoy Output…), **View** (Connected, Not Connected, Deleted, Autosaves, Expand All, Collapse All, Search…), **Settings** (Device Library Settings…), **Help** (Device Library Guide, F1; S42). Menus follow 01 S66 (only what can be used now).) [user decision: D-10-WINDOW]
- **S2** It should open from the **Device Library** toolbar button (every page; was a Device Library… button on Home until 2026-10-09) and from Tools › Device Setup › Device Library…; the card menu items (03 S88) open it on that card's device. [D-10-WINDOW]
- **S3** The left side should hold filter chips (Connected, Not connected, Deleted, Autosaves; several at once, each an outline with a tick when on), a search box and the device list; the right side the details of what is selected; a divider between them can be dragged. [D-10-WINDOW, D-10-PROTO]
- **S4** The status bar should show the number of devices and saved setups, the autosave limit, the library's size on disk (e.g. "Library: 48 MB") and the library folder. [D-10-TIDY]
- **S5** Search should match device names and descriptions, saved setup names and descriptions, what a saved setup holds (Setup, Device Map, Appearance, Calibration, Bindings), profile names, mode names, vJoy numbers and autosave reasons; Ctrl+F goes to the box, Esc clears it. [D-10-SEARCH]

### B. Devices

- **S6** There should be one row per device: plugged in now (**Connected**), set up here but unplugged (**Not connected**), or deleted (**Deleted**). A device that came only from someone else's pack is **Not connected**: it can be copied from, never to. Each row shows its name, description, state and number of saved setups. [D-10-LIBRARY] [changed 2026-10-08 to follow D-10-STREAMLINE] The program's built-in inputs (Keyboard, OSC, the Logical Device [changed 2026-10-09, user: D-04-LD-FILE]) are listed after the devices under their own heading **Built-in inputs**; for them only Save to Device Library…, Restore to This Stick… (here: Restore), Export…, Rename… and Edit Description are offered (no separate Import item: a Logical Device pack comes in with File › Import Device Pack…, which files it under the Logical Device row, then Restore puts it on), never Remove from Library, Clear Setup, Copy, Swap or Change vJoy Output, and they have no Connected / Not connected badge. The heading sits under a thin divider after the last device, in small muted capitals, not clickable or foldable; the state filters (Connected, Not connected, Deleted) don't hide them, only a search does, and the heading hides when a search leaves none of them. [2026-10-09: D-10-BUILTIN-SECTION, replaces D-10-NO-BUILTINS]
  [changed 2026-10-09, user: D-10-INTERNAL-NAME] The heading is **INTERNAL INPUTS** (glossary "Internal inputs"; was "Built-in inputs"). [changed 2026-10-09, user: D-09-OSC-FILE] OSC's saved setups hold its module file: its inputs (with permanent ids and per-input settings) and its server settings; Save, Restore, Export and Import Device Pack carry both, and Restore puts them back as one write and one History entry, reloading OSC (09 S44, S47).
- **S6a** Restore and Import Device Pack of a built-in input without hardware (Keyboard, the Logical Device) skip the plugged-in check, decided by its class through `device_class.can('no_hardware_limits')` (03 S90b), never by a list of names; the Logical Device's saved setups hold its layout (controls with their permanent ids, groups), and Restore puts it back into its module file as one History entry. [changed 2026-10-09, user: D-04-LD-FILE]
- **S7** Every device and every saved setup can be renamed and given a description. A device set up here has one name: renaming it in the Library renames it on its Home card and the other way round. [D-10-NAMES] Home cards and the Device Bindings page title show this name (03 S73a). [confirmed as written 2026-10-11, user: D-01-OWNER-NOTICES (2a)] (Home cards and the Device Bindings page title: built 2026-10-11)
- **S8** Selecting a device should show its name, description, state, what inputs it has, and when it was last seen.
- **S9** Deleted devices are the ones deleted since the Library exists (Delete Device, Delete File); files in an old deleted devices folder are not read, moved or removed. [D-10-DELETED] [changed 2026-10-08 to follow D-10-NO-DELETED-FOLDER]
- **S59** A device rename (or Forget) should send the device names notice (01 S155); the Device Library window, the vJoy Viewer and Xbox Viewer device lists and the editors' input names (05 S140) follow it at once, and so do the Home cards (03 S73a). [changed 2026-10-11, user: D-01-OWNER-NOTICES] (built 2026-10-11) [test: test_owner_notices_e2e.py, test_owner_notices_senders.py]

### C. Saved setups

- **S10** A device row should open with a caret to show its saved setups as rows under it, newest first. Saved setups the user made (or renamed or described, S13) show a save mark; autosaves show an autosave mark. [D-10-ROWS]
- **S11** A saved setup holds any of: Setup (claims, friendly names), Device Map (both planes, every layer) with its photo and pictures, Appearance, Calibration, and Bindings (from one profile, the modes saved, the vJoy outputs they send to). Selecting one should show its name (renamable), its description (editable in place), when and why it was kept, exactly what it holds, a Device map photo preview (the saved setup's background picture, 07 S157; its bottom background picture when it has none), a short **Activity** list (saved, description edited, copied to which stick and when; named Activity so it isn't confused with Tools › History) [changed 2026-10-08 to follow D-10-ACTIVITY], and the actions Copy, Swap, Change vJoy Output, Export and Delete (Delete in red). [D-10-PROTO] [changed 2026-10-11, user: D-03-DEVICE-FOLDERS] [changed 2026-10-11, user: D-07-BACKGROUND-PLANES] [changed 2026-10-11, user: D-07-BG-COMPOSITE] (built 2026-10-11) [test: test_device_photo_shown.py::test_a_saved_setup_shows_its_background_picture] (device-folders part built 2026-10-11: the setup holds the module file and the pictures of its folder; both planes and every background layer built 2026-10-11, S62) [test: test_planes_carry.py::test_a_saved_setup_shows_its_bottom_background_picture] (was: "Button Map and photo") [test: test_library_device_folders.py::test_a_saved_setup_is_a_gmap_of_the_folder]
- **S12** Device › Save to Device Library… should keep a saved setup of the selected device (the user's own): its module file now, and its bindings from the profiles the user ticks (one saved setup per profile, named after the profile by default). [D-10-SAVE]
- **S13** An autosave the user renames or describes becomes the user's own and is never removed by the autosave limit. [D-10-AUTOSAVE]
- **S14** Export Saved Setup… should write the saved setup as its device file (".gmap", 08 S111) anywhere the user picks (08 S57 rules); no `.zip` is written. [changed 2026-10-11, user: D-FIXLIST-B2] (built 2026-10-11) [test: test_b2_lib.py, test_b2_e2e.py] (was: Export Saved Setup… should write the saved setup as its device file (".gmap", 08 S111) anywhere the user picks (08 S57 rules); a setup saved before device folders exports as the Device Pack it was saved as.) [D-10-SHARE] [changed 2026-10-11, user: D-10-GMAP-SETUPS] (was: as a Device Pack) (built 2026-10-11) [test: test_device_library_LS_store.py::test_export_writes_the_pack_and_refuses_the_modules_folder]
- **S15** Deleting always asks first and names exactly what goes. On a saved setup, **Delete…** removes it. On a device the items depend on its state (S47): a **not connected** device (unplugged, deleted or from a pack) has **Remove from Library…**, which removes the device and all its saved setups, and, when it still has a module file here, removes that too as Home's Delete Device does (03 K, autosave first, refused while the profile runs); a **connected** device has **Clear Setup…** (the same as Delete Device: an autosave first, then its module file and bindings go; the stick stays plugged in with no setup) and **Delete Saved Setups…** (forgets its saved setups; the stick keeps its settings). [D-10-TIDY] [changed 2026-10-08 to follow D-10-REMOVE] [test: test_library_plugged_in.py::test_twin_sticks_one_unplugged_only_the_plugged_one_is_connected, ::test_a_name_with_double_spaces_is_connected_by_its_id]

### D. Autosaves

- **S16** The program should keep an autosave of a stick, without asking, when: the stick is deleted (Delete Device); its module file is deleted (Module Setup's Delete File: setup only, "Autosave: module file deleted"); before Copy replaces its settings; before Swap; before Change vJoy Output; before a Device Pack is put on it. They are always on (they are the way back, S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]
- **S17** An autosave's name should say why it was kept: "Autosave: stick deleted", "Autosave: before Copy from <stick>", "Autosave: before Swap with <stick>", "Autosave: before Change vJoy Output (vJoy 1 → 2)", "Autosave: before Device Pack <pack>", "Autosave: before Restore of <saved setup>" (S48) (<pack> is the pack's file name without .zip; user, 2026-10-08). [D-10-AUTOSAVE]
- **S18** An autosave should hold everything the stick has: its whole folder, and its bindings in every mode from every profile the action changes (the open profile and any ticked saved profiles). [changed 2026-10-11, user: D-03-DEVICE-FOLDERS] (built 2026-10-11) (was: "its module file and pictures, and its bindings") [test: test_library_device_folders.py::test_an_autosave_holds_the_whole_folder, ::test_undo_puts_the_folder_back_from_the_autosave]
- **S19** Only the newest N autosaves per stick are kept (N = 10 by default, set in Device Library Settings); older autosaves are removed when a new one is kept. The user's own saved setups (S12, S13) are never removed this way. [D-10-AUTOSAVE]
- **S20** If an autosave can't be written or read back, the action that needed it should not run, and say so (as Delete Device's copy does today, 03 S91). [carries 03 S91, 08 S86]
- **S20a** A stick whose module file is damaged can still be autosaved: the autosave keeps the damaged file exactly as it is, with the stick's bindings, and shows it as holding "Setup (damaged file, kept as is)". So Delete Device and Delete File always work for it. Copy and Swap never put a damaged file on another stick (only its bindings can be copied from such a setup). [D-10-DAMAGED-KEPT] (as a ".gmap" from 2026-10-11, S63: built) [test: test_library_device_folders.py::test_a_damaged_module_file_is_saved_as_a_gmap, ::test_a_damaged_gmap_setup_restores_its_bindings]
- **S21** Delete Device should always keep a "stick deleted" autosave (when that trigger is on) and no longer ask "Save a copy". [D-10-DELETE, changes 03 S90-S91, 08 S86]

### E. Copy to Another Stick

- **S22** Copy should take a saved setup (or a device's current settings) and put it on a stick plugged in now. The To list holds only connected sticks; a stick never plugged in here can be copied from, never to. [D-10-COPY]
- **S23** The dialog should show From (device › saved setup), To, What to copy (Setup, Device Map, Appearance, Bindings ticked; Calibration unticked; defaults from Settings), the profiles to put the bindings in (every profile that has bindings for the target or source, only the open profile ticked to start, Tick all), the modes, and a warning box listing what won't copy because the target lacks it (buttons, hats, axes and the bindings on them). [D-10-COPY, D-10-PROFILES]
- **S24** Copy should work like a Device Pack import onto the target (08 S64-S79): ticked modes replace the target's wires and actions in that mode, controls the target doesn't have are left out and listed, outputs keep their vJoy. The source saved setup and device are never changed. [D-10-COPY]
- **S25** Before Copy changes anything it should keep the target's autosave (S16), and Undo puts the target back from it (S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]

### F. Swap with Another Stick

- **S26** Swap should exchange the ticked parts between two sticks plugged in now: each gets the other's settings. Bindings swap with every device reference inside actions and every script variable, as Swap Devices does today (04 S77-S78). [D-10-SWAP]
- **S27** The dialog should show both sticks, What trades places (as S23), the profiles (as S23), and warnings for both directions (what each stick lacks that the other has; those bindings stay where they were). The warnings also list actions elsewhere that refer to a control of one stick the other lacks (e.g. a Condition checking Left stick Axis 3 when Right stick has no Axis 3): the reference still moves with the swap, and is listed, not changed. [D-10-SWAP, D-10-PROFILES] [changed 2026-10-08 to follow D-10-SWAP-REFS]
- **S28** It should keep an autosave of each stick first; Undo puts both back from them (S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]
- **S29** It should refuse the Keyboard, Logical Device, OSC and Xbox, and refuse a stick swapped with itself. [carries 04 S79, 04 Q20]

### G. Change vJoy Output

- **S30** Change vJoy Output should keep a stick's bindings and change only which vJoy its Map to vJoy actions send to: one row per vJoy the stick sends to ("vJoy 1 (38 inputs) → [vJoy 2]", marked "changes" or "stays"), in the profiles ticked (as S23). A tick box "Also move <other stick> from vJoy 2 to vJoy 1 (swap them)" changes the stick that used the target vJoy the other way. [D-10-OUTPUT, D-10-PROFILES]
- **S31** Its warnings should list bindings that would send to an output the target vJoy's output module doesn't claim (they would send nothing), and macros and user scripts that name a vJoy number (not changed: "check it yourself"). [D-10-OUTPUT]
- **S32** It should keep an autosave of each stick that changes first; Undo puts them back from them (S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]
- **S58** Swap and Change vJoy Output should announce their edit of the open profile the way any edit in memory does, so every page follows, and send the bindings notice (01 S155) so Driven by and the viewers follow (03 S75a, S122a). [changed 2026-10-11, user: D-01-OWNER-NOTICES] (built 2026-10-11) [test: test_owner_notices_e2e.py, test_owner_notices_senders.py]

### H. Profiles that aren't open

- **S33** Copy, Swap and Change vJoy Output should change the open profile in memory (saved with File › Save Profile, as Device Pack import does, 08 S74). A ticked saved profile that isn't open is changed and saved on disk; each such save is a History entry (the whole file can be restored from History). There is no separate backup copy: the autosave holds the stick's bindings from every profile changed, and Undo (S41) puts them back. A failure partway through one profile leaves that file as it was. [D-10-PROFILES] [changed 2026-10-08 to follow D-10-STREAMLINE]
- **S34** A saved profile that can't be read or written should be named and left unchanged; the others still change. [D-10-PROFILES]

### I. Packs from other people

- **S35** File › Import Device… (chooser title "Import Device", "Device files (*.gmap)") should add a `.gmap` device file (the only kind it opens; a `.zip` is not read) as a saved setup: under the device it was made from when that device is in the Library, otherwise under a new Not connected device named after the file. The saved setup says where it came from ("From <Made by>'s device file", or "From a device file" without a Made by) and takes the file's Note as its description; the message line says "Device file added as a saved setup." [changed 2026-10-11, user: D-FIXLIST-B2] (built 2026-10-11) [test: test_b2_lib.py, test_b2_e2e.py] (was: File › Import Device Pack… should add the pack as a saved setup: under the device it was made from when that device is in the Library, otherwise under a new Not connected device named after the pack. The saved setup says where it came from ("From <Made by>'s pack") and takes the pack's Note as its description.) [D-10-SHARE] [changed 2026-10-08 to follow D-10-STREAMLINE] [test: test_library_plugged_in.py::test_a_pack_device_not_on_this_pc_stays_not_connected]

### J. Settings and tidying

- **S36** Settings › Device Library Settings… should hold: the number of autosaves kept per stick (S19), what Copy and Swap tick by default (Setup, Device Map, Appearance, Bindings on; Calibration off), and the library folder with Move…. [D-10-SETTINGS]
- **S37** The library folder has its own setting (default `<data folder>\device library`, chosen in Device Library Settings). The deleted devices folder and its setting are removed: Options › Folders no longer lists it, and nothing is carried over from it. [D-10-DELETED, changes 01 S124, 03 S98, 08 S87] [changed 2026-10-08 to follow D-10-NO-DELETED-FOLDER]
- **S38** Edit › Tidy Library… should list what it would remove (autosaves older than a chosen number of months; deleted devices with no saved setups), and remove it only after the user confirms. Nothing in the Library is removed without asking except by the autosave limit (S19). [D-10-TIDY]

### K. Undo and shortcuts

- **S39** Dropping a `.gmap` device file on the window should import it as File › Import Device… does (S35); a dropped `.zip` is not read. [changed 2026-10-11, user: D-FIXLIST-B2] (built 2026-10-11) [test: test_b2_lib.py, test_b2_e2e.py] (was: Dropping a Device Pack (.zip) on the window should import it as File › Import Device Pack… does (S35).) [D-10-STREAMLINE]
- **S40** Double-clicking a saved setup should open Copy to Another Stick with it as From. [D-10-STREAMLINE]
- **S41** Edit › Undo should put the last Copy, Swap or Change vJoy Output back by copying the autosaves it kept onto their sticks (every part they hold, into the profiles they came from). Because it uses the autosaves, it still works after the window closes or the program restarts, until another change replaces it. Undo is itself a change and keeps its own autosave first. The Edit menu item names the change: "Undo <change>" (e.g. "Undo Copy DCS F-16 to Right stick"), and right after an Undo it reads "Redo <change>". [D-10-STREAMLINE] [D-10-REDO-LABEL]

### L. Guide

- **S42** Help › Help (F1) in the Device Library opens the one Help window on its Device Library chapter only, with View Full Help (01 S128). [changed 2026-10-09: D-01-ONE-HELP]

### M. Right-click menu and selection

- **S43** Right-clicking a row should first select it (highlighted, details shown, as a left-click does), then open its menu; the keyboard Menu key and Shift+F10 open the same menu on the selected row. Rows show a hover highlight and a pressed flash; a row that is being changed shows a small busy mark. [D-10-CONTEXT]
- **S44** A device's menu should hold, as they apply: Copy to Another Stick… (from its current settings), Swap with Another Stick… (connected), Change vJoy Output…, Save to Device Library…, Export Current Setup… (a ".gmap" device file of its current settings, 08 S111) [changed 2026-10-11, user: D-10-GMAP-SETUPS] (was: a Device Pack) (built 2026-10-11) [test: test_device_library_CL_store.py::test_export_current_writes_a_pack_and_keeps_no_saved_setup], Rename… (F2), Edit Description, Open Module Setup…, Open Device Mapping Editor, Show on Home, Expand / Collapse, and the delete items of S15. [D-10-CONTEXT]
- **S45** A saved setup's menu should hold: Copy to Another Stick…, Restore to This Stick… (S48), Export…, Rename… (F2), Edit Description, Keep This Autosave (S49, autosaves only), Delete…. [D-10-CONTEXT]
- **S46** The menu on empty space in the list should hold: Import Device…, Expand All, Collapse All, Device Library Settings…. [changed 2026-10-11, user: D-FIXLIST-B2] (built 2026-10-11) [test: test_b2_lib.py, test_b2_e2e.py] (was: The menu on empty space in the list should hold: Import Device Pack…, Expand All, Collapse All, Device Library Settings….) [D-10-CONTEXT]
- **S47** Menus show only what can be used now (01 S66); delete items are red and always ask first, naming what goes (e.g. "Remove T.16000M and its 4 saved setups from the Library?"). [D-10-CONTEXT, D-10-REMOVE] A device's menu title names its state ("Left throttle · Connected", "· Not connected", "· Deleted"), and each delete item has a tooltip (the program's usual hover tooltip, not text in the menu) saying what it does: Clear Setup… "Its settings go; the stick stays plugged in", Delete Saved Setups… "Only the saved setups go; its settings stay", Remove from Library… "Gone from the Library, with its saved setups". Remove from Library's question says "You can restore it from Tools › History." (D-10-IN-HISTORY). [D-10-DELETE-CLARITY] [D-10-MENU-TIPS] If Delete Device (run first for a device with a module file) fails, Remove stops and shows its reason; it never stops silently. [2026-10-09: D-10-REMOVE-ERROR]
- **S48** Restore to This Stick… should put a saved setup back on its own stick (which must be plugged in) as Copy does (S22-S25, autosave first, Undo), without choosing a target. [D-10-RESTORE]
- **S49** Keep This Autosave should make an autosave the user's own in one step (as renaming or describing it does, S13), so the autosave limit never removes it. [D-10-KEEP]
- **S50** Ctrl-click and Shift-click should select several saved setups (or several devices); Delete… / Remove from Library… then act on all of them after one question that lists them. Copy, Swap, Change, Restore, Rename and Export act on one row only. When a plugged-in stick is among several selected devices, the menu shows Remove from Library… greyed out (it can't be clicked) with the tooltip "Remove from Library works only on devices that aren't plugged in", instead of an empty menu. [D-10-MULTI] [D-10-MULTI-NOTE] [D-10-MENU-TIPS] [test: test_library_plugged_in.py::test_twin_sticks_one_unplugged_only_the_plugged_one_is_connected]
- **S51** Every change to the Library's own files is a Tools › History entry, like a module-file save: its list (names, descriptions, records) and its saved setups (a new one, a delete, Delete Saved Setups…, Remove from Library…, an autosave pruned past the limit). One action is one entry, named for what happened ("Removed HID Remapper ACHB from the Device Library", "Deleted saved setup X"); Restore puts back only that entry's change: the saved setups and files it removed come back and the ones it added go, merged into today's Library list, and every later change stays (an older entry does not put the whole Library back as it was then). The restore is shown as a tag on the entry and titled "Restored: <original title>" (08 S39a). Delete and Remove questions say "You can restore it from Tools › History." [user decision 2026-10-09: D-10-IN-HISTORY] [changed 2026-10-11, user: D-TESTLIST-1] (built 2026-10-11) [test: test_library_restore_one_change.py] (was: Restore puts back the files and the list as they were before it.)
- **S52** Remove from Library… removes the device entirely: its folder (settings, map, pictures, recovery copy), its saved setups and autosaves, its Library record and last-seen date, its friendly name, its Home card settings (size, place, hidden, compact) and its calibration; its bindings leave the open profile (kept only if that profile is saved). Other saved profiles and HidHide are not touched. It is ONE Tools › History entry ("Removed X from the Device Library"; several at once: "Removed N devices from the Device Library") whose Restore puts every piece back. Clear Setup… is likewise one entry, "Cleared the setup of X" (its autosave and the module-file delete together). [2026-10-09: D-10-ONE-ENTRY-TITLES] A device still plugged in is not removed (it gets Clear Setup…, and Windows keeps listing it as a plain card on Home). [user decision 2026-10-09: D-10-REMOVE-ALL] [changed 2026-10-11, user: D-03-DEVICE-FOLDERS] (built 2026-10-11) [test: test_library_device_folders.py::test_remove_from_library_removes_the_folder, ::test_remove_from_library_waits_for_delete_device] (was: "its module file and folder (pictures, Device map photo, recovery copies)"; and "every file choice that points at its file (stale old ids too, 03 S94)", gone with file bindings, 03 S94 removed)
- **S53** Undo and Redo are separate, plainly named items (the change they act on is in their tooltip and in the status bar, S53a): in Edit (Ctrl+Z, Ctrl+Y) and as small Undo / Redo buttons beside the right-click menu's title, as other right-click menus show them. They work on every Library action (each is one History entry, S51): Undo restores the newest one's "before", Redo its "after". Several steps: Undo walks back through this session's Library actions newest first, Redo forward; a new action clears Redo. Older changes stay in Tools › History. Replaces S41's single last-change Undo and D-10-REDO-LABEL. [user decision 2026-10-09: D-10-UNDO-REDO]
- **S53a** The status bar shows, after the Library size, "Last change: <title>" for the newest action Undo would take back, or "Undone: <title>" right after an Undo (what Redo puts back); nothing until a change this session; a long title is cut with "…" and shown whole in its tooltip. [user decision 2026-10-09: D-10-STATUS-LAST]
- **S54** After Remove, Delete or Clear Setup the message line ends with an **Undo** link that does the same as Edit › Undo. [D-10-UNDO-REDO]
- **S55** The Delete key on a selected row runs Delete… (a saved setup) or Remove from Library… (a device not plugged in), asking first as always; nothing for a built-in input. [D-10-UNDO-REDO]
- **S56** A row's right-click menu has **Show in History**: Tools › History filtered to that device (08 S32-S33). [D-10-UNDO-REDO]
- **S57** An unreadable `library.json` row is left out of the list with a log warning and kept in the file; folder and file names the Library builds, and device folder names (03 S130), are cut to 80 characters (the device keeps its full name in the list); a Device Pack the Library reads follows the same limits as the Device Pack window (08 S110). [changed 2026-10-10, user: D-08-PACK-LIMITS] (built: test_library_pack_robust.py) [changed 2026-10-11, user: D-03-DEVICE-FOLDERS] (built 2026-10-11) [test: test_store_folders.py::test_folder_name_is_cut_to_80_characters] (was: "folder and file names the Library builds are cut to 80 characters")

### N. Device folders and background planes
- **S60** A saved setup's device part should be the same zip as Export makes (08 S111): the device's folder as it was. (4a) [changed 2026-10-11, user: D-03-DEVICE-FOLDERS] (built 2026-10-11) [test: test_library_device_folders.py::test_a_saved_setup_is_a_gmap_of_the_folder, ::test_an_old_pack_setup_still_restores]
- **S61** Copy to Another Stick and Restore should copy the pictures the map uses into the receiving stick's folder (03 S133). [changed 2026-10-11, user: D-03-DEVICE-FOLDERS] (built 2026-10-11; Restore runs Copy's path, no test of its own) [test: test_library_device_folders.py::test_copy_puts_the_pictures_in_the_receiving_folder, ::test_swap_keeps_each_sticks_pictures_in_its_own_folder]
- **S62** Save to Device Library, Copy to Another Stick and Restore should carry every background layer and its pictures (copied into the receiving device's folder). Tested. (14) [changed 2026-10-11, user: D-07-BACKGROUND-PLANES] (built 2026-10-11) [test: test_planes_carry.py::test_copy_to_another_stick_carries_every_background_layer] [test: test_planes_carry.py::test_a_saved_setup_shows_its_bottom_background_picture] (Save to Device Library and Restore carry `nodes` and the folder's pictures as before; only Copy has a background-specific test)
- **S63** Every saved setup should be a ".gmap" device file, also for a stick with no module file (bindings only) and for a damaged module file kept as it is (S20a, marked damaged inside); `.zip` setups are neither written nor read (unreleased program: no reader for old `.zip` packs). [changed 2026-10-11, user: D-FIXLIST-B2] (built 2026-10-11) [test: test_b2_lib.py, test_b2_e2e.py] (was: Every new saved setup should be a ".gmap" device file, also for a stick with no module file (bindings only) and for a damaged module file kept as it is (S20a, marked damaged inside); saved setups from before stay readable.) [changed 2026-10-11, user: D-10-GMAP-SETUPS] (built 2026-10-11) [test: test_library_device_folders.py::test_a_stick_with_no_module_file_is_saved_as_a_bindings_only_gmap, ::test_a_damaged_module_file_is_saved_as_a_gmap, ::test_an_old_pack_setup_still_restores]

## 9. Questions for the user

- **Q1** The design had a sixth autosave trigger, "a profile with bindings for the stick is deleted". The program can't delete profiles (that happens in Explorer), so it never sees it. **Decided (user, 2026-10-08): dropped** (D-10-Q1-DROP); the other autosaves and the user's own saved setups keep bindings copies.

## 10. Known gaps

- ~~GMAP-ONLY~~ (closed 2026-10-11, built, D-FIXLIST-B2; S1, S14, S35, S39, S46, S63; [test: test_b2_lib.py (8), test_b2_e2e.py]). Was: the Library read `.zip` setups and packs, its choosers offered `*.gmap *.zip`, and an older `.zip` setup exported as `.zip`.
Built 2026-10-08/09 (S1-S56). Swap Devices (04 S77-S83), Delete Device's
"Save a copy" and the deleted devices folder are gone. Open:

- D-04-LD-FILE (2026-10-09): the Logical Device under Built-in inputs (S6, S6a), built 2026-10-09 (000e35d0; tests `test_ld_lib.py` (7), `test_ld_pack.py` (5)).
- Closed: Restore refused for built-ins (fixed 2026-10-09, IMG-restore). Restore of every Built-in inputs row (Keyboard, OSC, Logical Device) said "isn't plugged in" because `library_copy.restore_to_stick` used the stick checks; built-ins now go to `_restore_built_in`, and the Logical Device's layout and picture come back (`device_pack.apply_zip` carries the `logical-device` key). Tests `test_ld_restore_builtin.py`, `test_ld_card_image_carry.py` (7), `test_lib_builtin_actions.py`, `test_lib_restore_builtin_e2e.py`.
- AUD-DRIVEN (to-do 100; fixed 2026-10-11, 07b8d891: Library Swap and Change vJoy Output announce their edit through `bindingsChanged`; [test: test_owner_notices_e2e.py, test_owner_notices_senders.py]) S58: Swap and Change vJoy Output edit the open profile with no notice at all (`library_profiles.Batch._apply_open`; code only). Home side: 03 gap 36.
- AUD-DEVNAMES (to-do 102; fixed 2026-10-11, 07b8d891: `device_aliases` sends `deviceNamesChanged`; Home cards and the Device Bindings page title show the user's name; [test: test_owner_notices_e2e.py, test_owner_notices_senders.py]) S7, S59: a rename isn't followed by this window, the viewer device lists or the editors' input names; `device_aliases.forget()` saves without telling anyone; Home cards and the Device Bindings page title show the device's own name (code only). Device side: 02 gaps.
- DEVICE-FOLDERS (closed 2026-10-11, D-03-DEVICE-FOLDERS, D-10-GMAP-SETUPS): S11 (device-folders part), S14, S18, S20a, S44, S52, S57, S60, S61, S63: every new saved setup is a ".gmap" of the device's folder (bindings-only and damaged too), an autosave holds the whole folder and Undo puts it back, Remove from Library removes the folder, Copy and Swap copy pictures into the receiving stick's own folder, exports are ".gmap", folder names are cut to 80 characters; older ".zip" setups are still read and restored. Twin fix: `store._own_dir` makes `device_dir` first take the folder whose `device.json` holds exactly the id and the name, so an unplugged twin finds its own folder (S41). [test: test_library_device_folders.py (12), test_device_folders_devices.py (13), test_device_library_FX2_fixes.py::test_apply_zip_onto_an_unplugged_twin_writes_its_own_file, ::test_undo_on_an_unplugged_twin_never_writes_the_other_twin, ::test_a_twins_pack_lands_under_that_twin]
- GMAP-WINDOW-SUFFIX (closed 2026-10-11: `DeviceLibraryModel._export_dest` keeps ".gmap" or an older setup's ".zip" and gives a bare name ".gmap" (`_SETUP_SUFFIXES`); `test_device_library_LU_model::test_s14_export_adds_gmap`, `test_s44_export_current_adds_gmap`). Was: the window's choosers suggest "<name>.gmap" (`_packName('.gmap')`), but `DeviceLibraryModel.exportSetup` and `exportCurrent` add ".zip" to any name not ending in ".zip" ("X.gmap" becomes "X.gmap.zip"), and `device_library._export_name` then swaps only the last extension ("X.gmap.gmap"). The owner tests pass a bare name, and `test_device_library_LU_model.py::test_s14_export_adds_zip` pins the model adding ".zip". S14, S44.
- GMAP-WINDOW-IMPORT (closed 2026-10-11: `importPack` takes ".gmap" or ".zip"; `test_device_library_LU_model::test_s35_s39_import_takes_a_gmap`). Was: File › Import Device Pack… offers `*.gmap *.zip`, and `device_library.import_pack` reads both, but `DeviceLibraryModel.importPack` refuses any file not ending in ".zip" ("isn't a Device Pack (.zip)"), so a ".gmap" picked in the window is refused. S35, S39.
- ~~BACKGROUND-PLANES~~ Closed 2026-10-11 (built; D-07-BACKGROUND-PLANES): background layers are nodes, so saved setups, Copy and Restore carry them with the folder's pictures; the setup's photo is the bottom background picture; Copy to Another Stick swaps `nodes` and `ui` only. [test: test_planes_carry.py, test_planes_paths.py::test_library_restore_puts_the_background_back] Was: S11 (both planes, every layer), S62: saved setups, Copy and Restore carry the folder's pictures and the one photo, not background layers.
- To-do 52 (after 1.0.30): the Library's delete and remove questions move
  onto the shared red button and question (01 S140-S143: DangerButton,
  ConfirmDialog); Tidy already uses it.
- To-do 51 (ideas, not in the spec): drag a saved setup onto a stick row to
  start Copy; sort the list (name, last seen, saved setups); highlight the
  search match.
- Closed 2026-10-10 (F1, SHAKE-DAMAGE-03): one bad Library entry no longer hides the whole list; a deeply nested list reads as damaged (`test_library_pack_robust.py`).
- ~~Restore of one Library entry~~ Closed 2026-10-11 (built; test_library_restore_one_change.py, test_library_part_id_once.py). Was: (D-TESTLIST-1, S51) Restoring an older Library entry from Tools › History puts back the whole Library as it was then; it should put back only that entry's change, merged into today's `library.json`, titled "Restored: <original title>" (was "Put back from History: …", `device_library.py`, `library_undo.py`). The Library safety copy should be logged with its real full path. Fixed in `gremlin/device_library.py`, `gremlin/library_undo.py`, `gremlin/library_part_id_once.py` and `gremlin/ui/hardware_profile.py` (the autosave trace).
- Tests (to-do 47, 50): `test_device_library_FX2_fixes::test_a_twins_pack_lands_under_that_twin`
  fails only after some other tests (order); one full run died silently at
  `test_device_library_GC_guide.py` (passes alone).

## 11. Size and test coverage

- D-07-BG-COMPOSITE (2026-10-11): `test_device_photo_shown.py::test_a_saved_setup_shows_its_background_picture` (S11) and `test_device_photo_carry.py` (a saved setup's photo; made again after a Device Library restore).
- D-TESTLIST-1 (2026-10-11): `test_library_restore_one_change.py` (7: restoring an older delete brings back only that setup, a later save stays, Reapply deletes only that setup again, a removed device comes back with only the restored setup, the restore is titled "Restored: <original title>", library_undo names its group Restored, an autosave names its packs by full path), `test_library_part_id_once.py` (+2, 8 in all: the id renamed anywhere it is a value, including `covers`).
- Covered from 2026-10-11 (D-FIXLIST-B4, OT-4): `test_library_part_id_once.py` (6: the move, its backup, an already-moved list, no second run, the refusal; a setup holding the old id keeps that part). Part id is `device_map` everywhere (was `button_map`).
- D-FIXLIST-B2 (2026-10-11): `test_b2_lib.py` (8, helper `_gmap_pack.py`: `.gmap` only in, out and dropped; Import Device… wording; Made by and Note as reason and description); `test_library_device_folders.py` now checks that an old `.zip` setup is not read (was `::test_an_old_pack_setup_still_restores`).

Code (rechecked 2026-10-11): about 7,200 lines of Python (device_library 2500, device_library_model
1568, library_copy 1424, library_swap 553, library_profiles 517,
library_undo 193, device_aliases 316, device_forget 133) and 2,693 of QML/JS
(WindowDeviceLibrary 1520, five dialogs 1146, device_library_open.js 27).

Tests: 38 files in `test/unit` (`test_device_library_*.py`, `test_library_*.py`,
`test_rename_library.py`, `test_device_forget.py`), 316 tests (counted 2026-10-09; from 2026-10-10 also `test_library_pack_robust.py` (15: a bad `library.json` row left out and the rest listed, a deeply nested list reads as damaged, and the Device Pack checks of page 08), `test_library_device_folders.py` (12, 2026-10-11, D-03-DEVICE-FOLDERS / D-10-GMAP-SETUPS: a saved setup is a `.gmap` of the folder, an autosave holds the whole folder, an older pack setup still restores, Copy and Swap put pictures in the receiving folder, Remove removes the folder and waits for Delete Device, a refused rename shows its reason, bindings-only and damaged `.gmap` setups, a damaged `.gmap` restores its bindings, Undo puts the folder back), `test_device_folders_devices.py` (13, 2026-10-11: renaming a device renames its folder, a busy folder refuses the rename and saves no alias, built-ins keep their folder, twins get their own folders, a scan syncs folder names, the Logical Device's and OSC's files land in their folders; also on pages 01, 02, 03, 06, 08, 09), `test_builtin_layout_carry.py` (16: Keyboard and OSC layouts and names through Library Restore, Export, Device Pack, History; Keyboard names fixed 2026-10-10, page 05 KB-NAMES), `test_planes_carry.py` (9, 2026-10-11, D-07-BACKGROUND-PLANES: a saved setup shows its bottom background picture, Copy to Another Stick carries every background layer; also Device Pack and the Logical Device card, pages 08 and 03)), plus off-screen
window smokes (`device_library_*_smoke.py`, `library_*_smoke.py`,
`rename_library_smoke.py`). They drive the real path: the store (list,
autosave limit, renamed autosave kept, damaged pack: LS, CL, FD), Copy / Swap /
Change on profiles open and not open (LC, LF, LW, LP, FM_profiles), Remove
and Delete (DD, test_library_remove_error, test_device_forget), threads
(FM2_threads), History entries and Undo/Redo (test_library_in_history,
test_library_undo_redo, test_library_undo_ui, test_library_status_last), the
window and menus (LU_window, CU_menus, DD_menus, FM_window, FM2_window,
test_library_menu_refresh), the Guide (GC_guide) and built-in inputs
(test_library_builtin_section, test_library_no_builtins; Restore of a built-in
with nothing plugged in, layout and card picture carried, one Undo step and one
History entry: `test_ld_restore_builtin.py` (6), `test_lib_builtin_actions.py` (8 x 3 built-ins), `test_lib_restore_builtin_e2e.py` (1), `test_ld_card_image_carry.py` (7),
`test_lib_builtin_actions.py`, `test_lib_restore_builtin_e2e.py`). Plugged in by id
(03 S90a): `test_library_plugged_in.py` (4: twins, double-spaced name, pack
device not on this PC, Copy / Restore by live id). Device classes (03 S90b):
`test_library_device_class.py` (`::test_built_in_guid_is_keyboard_osc_and_logical_device`,
`::test_stick_named_keyboard_is_a_normal_library_device`,
`::test_copy_skips_internal_inputs_and_placeholders_only`,
`::test_swap_refuses_non_sticks_with_the_same_words`), `test_library_no_builtins.py`,
`test_device_library_LW_swap.py`. Shared pieces
(questions, red buttons, SearchBox, MessageLine, UndoBar, EmptyState, Device
Pack choosers): `test_library_shared_pieces.py` (with
`library_shared_pieces_smoke.py`), plus `test_device_library_CU_menus.py`,
`test_library_undo_ui.py`, `test_device_library_LU_window.py`.

## 12. Review

Approved by the user, 2026-10-08 (wording as drafted; Q1 dropped).

| Decision | Summary |
|---|---|
| D-10-LIBRARY | Device Library: every device, current, unplugged, deleted and shared |
| D-10-NAMES | Rename and describe every device and saved setup |
| D-10-ROWS | Saved setups under a caret, newest first; autosaves marked |
| D-10-AUTOSAVE | Autosave triggers, reason in the name, newest 10 kept, renamed ones kept |
| D-10-WINDOW | Separate window with its own menus and settings |
| D-10-DELETED | Deleted devices included; the folder setting moves into the Library |
| D-10-DELETE | Delete Device always autosaves; no "Save a copy" question |
| D-10-COPY, D-10-SWAP, D-10-OUTPUT | The three actions, replacing Swap Devices |
| D-10-PROFILES | Profiles to change: a tick list, the open profile ticked |
| D-10-SEARCH | Search covers names, descriptions, contents, profiles, modes, vJoy |
| D-10-TIDY | Size in the status bar and Tidy Library… |
| D-10-SETTINGS, D-10-SAVE, D-10-SHARE, D-10-PROTO | Settings, saving, sharing, the prototype's layout |
| D-10-Q1-DROP | No autosave trigger for a deleted profile |
| D-10-REMOVE | Remove from Library (not connected), Clear Setup and Delete Saved Setups (connected) |
| D-10-CONTEXT | Right-click menus for devices, saved setups and empty space; selection and feedback |
| D-10-RESTORE | Restore to This Stick |
| D-10-KEEP | Keep This Autosave |
| D-10-MULTI | Select several rows to delete together |
| D-10-MULTI-NOTE | Grey line when Remove can't apply to several selected devices |
| D-10-ACTIVITY | The saved setup's short list is called Activity |
| D-10-DELETE-CLARITY | State in the menu title, a grey line under each delete item, Remove's question says nothing is kept |
| D-10-MENU-TIPS | What a menu item does is a hover tooltip, never text in the menu; several devices with one plugged in: Remove greyed out with a tooltip |
| D-10-GUIDE | Device Library Guide in the window's Help menu (F1) |
| D-10-REDO-LABEL | After an Undo the Edit item reads "Redo <change>" |
| D-10-DAMAGED-KEPT | A damaged module file is autosaved as it is, so delete always works |
| D-10-SWAP-REFS | Swap warns about references to controls the other stick lacks |
| D-10-STREAMLINE | Undo puts the autosave back; autosaves always on; no profile backups (History covers whole files); Shared folded into Not connected; no Edit Description; drag-drop import and double-click to Copy |
| D-10-NO-DELETED-FOLDER | The deleted devices folder and its setting go; Delete File autosaves into the Library; nothing carried over (beta) |
| D-04-LD-FILE (2026-10-09) | The Logical Device is a built-in input (Save, Restore, Export, Rename, Edit Description; packs come in by Import Device Pack… then Restore); built-ins without hardware skip the plugged-in check, by class (S6, S6a) |
| D-09-OSC-FILE, D-10-INTERNAL-NAME (2026-10-09) | Section heading INTERNAL INPUTS; OSC's setups carry its inputs and server settings (S6) |
| D-08-PACK-LIMITS (2026-10-10) | S57: an unreadable `library.json` row is left out and kept; built names cut to 80 characters; pack limits as 08 S110 |
| D-01-OWNER-NOTICES (2026-10-11) | S7 confirmed as written (2a); S58: Swap and Change vJoy Output announce their edit (1a); S59: renames followed everywhere (3a) |
| D-03-DEVICE-FOLDERS (2026-10-11) | S11, S18, S52, S57, S60, S61: a saved setup's device part is the device folder zip (as 08 S111); autosaves hold the whole folder; Remove from Library removes the folder (no file choices any more, 03 S94 removed); device folder names cut to 80 characters; Copy and Restore copy the pictures into the receiving stick's folder. Built 2026-10-11 |
| D-10-GMAP-SETUPS (2026-10-11) | S14, S44, S63: every new saved setup and every export is a ".gmap" device file, also bindings-only and damaged; older setups stay readable. Built 2026-10-11 |
| D-FIXLIST-B2 (2026-10-11) | S1, S14, S35, S39, S46, S63: the Library's saved setups, exports and imports are `.gmap` only (one file format with Export / Import Device, 08 S49); no `.zip` written or read; no reader for old `.zip` packs (unreleased). Supersedes D-10-GMAP-SETUPS' "older setups stay readable". Library menu and right-click "Import Device Pack…" renamed "Import Device…", setup reason "From <Made by>'s device file" (S1, S35, S46). Built 2026-10-11 (test_b2_lib.py (8), test_b2_e2e.py) |
| D-07-BACKGROUND-PLANES (2026-10-11) | S11, S62: saved setups, Copy and Restore carry both planes and every background layer with its pictures. Built 2026-10-11 |
| (wording) | [changed 2026-10-11, user: D-FIXLIST-B3] wording only: the Configuration page is now **Device Bindings** (qml/DeviceBindingsPage.qml) and the Auto Mapper is now the **Auto Mapping Tool** (gremlin/auto_mapping_tool.py, gremlin/modules/auto_mapping_tool.py, gremlin/ui/auto_mapping_tool_modules.py, qml/DialogAutoMappingTool.qml); Help topic ids configuration-actions-* / tools-auto-mapper* became device-bindings-actions-* / tools-auto-mapping-tool*; no statement changed. |
| (wording) | [changed 2026-10-11, user: D-FIXLIST-B4] wording only: the Button Map is now the **Device Mapping Editor** (the window; toolbar caption **Mapping Editor**, the full name in its tooltip) and what it makes is a **device map** (**Copy Device Map from Device**; **Button Map Options** is now **Device Map Options**; Device Library part **Device Map**); files qml/DialogDeviceMappingEditor.qml, qml/DeviceMapOptionsWindow.qml, qml/DeviceMapCard.qml, qml/OptionDeviceMapLibrary.qml, gremlin/ui/device_map_options.py, gremlin/ui/device_map_labels.py, qml/help/device_mapping_editor.js; spec page 07-device-mapping-editor.md; Help chapter and topic ids button-map* became device-mapping-editor*, Show me show:buttonmap/bm* became show:devicemappingeditor/dme*; settings section button-map became device-mapping-editor (moved once at start, one-time code OT-3); no statement changed. |
| D-TESTLIST-1 (2026-10-11) | S51: restoring an older Library entry from History puts back only that entry's change (its setups and files), merged into today's Library, not the whole Library as it was then; titled "Restored: <original title>" / "Reapplied: <original title>" (08 S39a). Library safety copies are logged with their real path. OT-4 (one-time, tracker OT-4) also renames the part id in each saved setup's `covers` list. Built 2026-10-11 (test_library_restore_one_change.py, test_library_part_id_once.py). |
| S11 | 2026-10-11 (D-07-BG-COMPOSITE; user: "1a", "1.a", approved, go; 07 S157): a saved setup's Device map photo preview is its background picture (07 S157; its bottom background picture when it has none). Built 2026-10-11 (07 G64 closed) |
