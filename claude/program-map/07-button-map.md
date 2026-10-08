# Button Map

Mapped read-only against the code at 4f6bdfa4 (6 Oct). Line numbers drift; re-check them before a step starts. Device Packs, module-file import and Delete Device also live in `gremlin/ui/hardware_profile.py`, but they belong to the module-files page; here they appear only where they touch the Button Map.

## 1. Purpose

Button Map is a picture of one device with a chip on each control, a hotspot on the photo for each, and a leader line between them. While the profile runs, a press lights its chip, and chips can show what each control does. The user lays the map out in an editor (chips, groups, drawings, text, tables, pictures, the photo), saves it into the device's module file, and prints or exports it.

## 2. Files

**Python**
- `gremlin/ui/hardware_profile.py` (2656 lines). Button Map part, `HardwareProfile` (1511-2656): `load` / `save` / `saveUi` (2294-2391), photo (`copyImage`, `keepPhoto`, `clearImage`, `stashPhoto`, `restorePhoto`, `hasPhotoStash`, `dropPhotoStash`, `profilePhotoUrl`, `imageUrl`, `adjustedPhotoUrl`), pictures (`copyOverlay`, `importPictureFiles`, `pasteClipboardPictures`, `savePastedImage`, `imageAspect`, `_pack_assets`), recovery copies (`saveRecovery` / `loadRecovery` / `clearRecovery`, 2245-2292), templates (2119-2243), copy layout (`savedLayouts`, `layoutNodes`, 2083-2117), labels (`actionLabels`, `profileModes`, `profileLabelsChanged`), colours (`recentColours`, `noteColour`, `colorAt`), print and export (`saveArea`, `printImage`, module functions `exact_page`, `save_area`, `print_image`, `adjust_photo`), pool rows (`chips` -> `chips_for_guid` 1480).
- `gremlin/ui/button_map_labels.py` (178): `action_labels` (what each control does in a mode, with parent-mode inheritance), `mode_order`.
- `gremlin/ui/button_map_options.py` (391): Button Map Options (config section `button-map`), saved styles, `ButtonMapOptions` QML object.
- `gremlin/ui/pair_live.py` (`PairLiveThrottle`), `gremlin/ui/input_pairing.py` (`MappedButtonModel` etc.): the live press feed and wire labels the map shows (shared with the viewers; mapped there).
- `gremlin/history_modules.py`: files Button Map saves under History area "Button Map"; skips view-only (`ui`) changes.
- `gremlin/util.py` `copy_legacy_modules` (939): copies the old `qml/maps` folder into the modules folder at start (the folder is not in the repo any more).

**QML window and editor**
- `qml/DialogJoystickButtonMap.qml` (4081): the window. Device choice, Edit / Save / Cancel, dirty check, recovery offer, photo menu and Adjust Photo popup, print setup (`printSetup`, `printArea`, `exportPixels`), export and print jobs, copy layout, templates dialogs, saved-style dialog, labels mode, tool rows (`_tools`), command palette, colour picker, menus and shortcuts.
- `qml/JoystickButtonMapCard.qml` (93): one device's live feed (`PairLiveThrottle`, mapped models) and pool rows (`_inventory.chips`), wraps `VkbRigFace`.
- `qml/VkbRigFace.qml` (913): photo, zoom and pan, rulers, wire labels (`labelBtn/Axis/Hat`), loads the editor.
- `qml/VkbRigEditor.qml` (1665): the editor item. All node data (`nodes`), selection, undo history (`hist`, `pushHist`, `undo`, `redo`, `seedHist`, `replaceHistTop`), timers; one-line forwarders into the `rig_*.js` files. Also a hard-coded EVO R name list `physNames` (1006-1040).
- `qml/rig_*.js` (27 files, about 9,700 lines): `rig_coords` (page fractions to pixels), `rig_chips` (chip text, pool catalog, `addChiplet`, rename), `rig_groups` (groups, 5-way formats, `_uid`), `rig_selection` (delete, copy/paste, duplicate, nudge, return to pool), `rig_menu` (right-click menu model), `rig_leaders`, `rig_hotspot`, `rig_draw`, `rig_shapes`, `rig_path`, `rig_transform`, `rig_text`, `rig_tables`, `rig_callout`, `rig_overlays` (pictures), `rig_photo`, `rig_layers`, `rig_props`, `rig_align`, `rig_grouprot`, `rig_mirror`, `rig_find` (press to find), `rig_snap`, `rig_rulers`, `rig_print_area`, `rig_style`, `rig_styles` (saved styles), `rig_hit`, `rig_pointer`.
- `qml/Rig*.qml` (17 files): `RigChipItem`, `RigChipLabel`, `RigMiniChip`, `RigGroupItem`, `RigDrawItem`, `RigLeaderLayer`, `RigPhotoLayer`, `RigGrid`, `RigGuides`, `RigSelRing`, `RigPointerArea`, `RigPrintArea`, `RigLayersPanel`, `RigPropsPanel`, `RigOptionsPanel`, `RigRenderer` (hidden copy that draws every print, export and preview).
- `qml/PrintExportWindow.qml` (525): Print & Export window (paper, orientation, margins, background, scale, Freeform, preview, buttons).
- `qml/DialogButtonMapGuide.qml` (12), `qml/help_topics.js` `buttonMapTopics()` (the Button Map Guide), `qml/OptionButtonMapLibrary.qml` (164, styles and templates library).
- `qml/vkb_evo_l_face_map.md`, `qml/vkb_evo_r_face_map.md`: pixel notes for the EVO photos.
- Callers: `qml/Main.qml` 556-650 (open, open blank, quit check), 484-493 (Delete Device closes it); `qml/main_commands.js:92`.
- Other users of `HardwareProfile`: `DialogConfigureModule.qml` (Module Setup photo), `DialogDevicePack.qml`, `Xbox360Face.qml`, `gremlin/ui/hidhide.py:493`.

**Tests**
- Python-level: `test_button_map_templates.py` (4), `test_button_map_recovery.py` (3), `test_button_map_copy_layout.py` (2), `test_button_map_save_keeps.py` (3), `test_photo_pose.py` (3), `test_button_map_photo_look.py` (6), `test_button_map_export.py` (9), `test_button_map_colours.py` (3), `test_button_map_labels.py` (6), `test_button_map_options.py` (7), `test_paste_picture.py` (3), `test_group_member_kind.py` (4), `test_audit2_button_map.py` (1), `test_data_safety.py::test_cancel_puts_the_starting_photo_back`, `test_module_file_damage.py::test_button_map_save_is_refused`, `test_twin_devices.py::test_the_button_map_of_the_second_twin_opens_its_own_file`, `test_audit3_module_files.py` (2 renamed-stick photo tests), `test_history_recording.py` (Button Map area, view-only not kept).
- Window smokes (own process, off-screen): `button_map_window_smoke.py` / `test_button_map_window.py`, `button_map_devices_smoke.py` / `test_button_map_devices.py` (7), `button_map_fixes_smoke.py` / `test_button_map_fixes.py` (10), `button_map_lifecycle_smoke.py` / `test_button_map_lifecycle.py`, `button_map_print_area_smoke.py` / `test_button_map_print_area.py` (9), `button_map_tool_row_smoke.py` / `test_button_map_tool_row.py` (14), `button_map_options_pane_smoke.py` / `test_button_map_options_pane.py` (9), `print_export_window_smoke.py` / `test_print_export_window.py` (12), `test_audit3_screens.py::test_button_map_recovery_offer_and_device_switch`, `test_audit3_modes.py::test_button_map_labels_mode_follows_a_rename`.
- Golden: `rig_editor_harness.py` (2228) drives `VkbRigFace` + `VkbRigEditor` (not the window) through 31 scenarios; `test_rig_editor_golden.py` compares states and screenshots with `test/unit/rig_editor_golden/*.json|png` (layouts `layouts/evo_l.json`, `evo_r.json`, `legacy.json`). Also `test_rig_shapes.py` (26), `test_rig_stacking.py` (2), `test_rig_uid.py` (1).

## 3. What it owns

| Data / state | Where | Who else may change it |
|---|---|---|
| The map (`nodes`), `photo` pose and look, `image`, page stamps (`kind`, `device`, `space`, `page`, `pageW`, `pageH`, `photoWell`, `imageWidth/Height`) | device's module file `modules/<slug>.json`; written by `HardwareProfile.save` (2318) | Module Setup save sets `image` from the folder's `photo.*` and defaults `pageW/pageH/photoWell/nodes` (`module_model.py:2285-2293`); Device Pack import; History Restore; Delete Device removes it |
| `ui` block: grid, snap, grid size, zoom, pan, guides, print area, print setup | same module file; `saveUi` (2367) via window `persistUi` (1691) | nobody else |
| Photo files `modules/<slug>/photo.<ext>` (and `photo_<name>.<ext>` fallback, legacy `<slug>_photo.<ext>`) | `copyImage` (2429), `clearImage` (2475), `restorePhoto` (2545), `_pack_assets` (1826) | Module Setup (`keepPhoto` / `copyImage`), Device Pack import, Delete Device, History Restore |
| Picture files `modules/<slug>/<name>`, `pasted*.png` | `copyOverlay`, `savePastedImage`, `_pack_assets` | Device Pack, Delete Device |
| Picture library `modules/library/` (a copy of every photo and picture ever chosen) | `_into_library` (1782) | nobody; never cleaned |
| Photo safety copy `modules/cache/photo-stash/<slug>/` (+ `manifest.json`) | `stashPhoto` / `restorePhoto` / `dropPhotoStash` | nobody |
| Adjusted-photo cache `modules/cache/photo-<hash>.png` (latest 12) | `adjustedPhotoUrl` (2041) | nobody |
| Recovery copies `modules/recovery/<slug>.json` | `saveRecovery` / `clearRecovery` | nobody (Delete Device leaves them) |
| Templates `modules/templates/<name>.json` | `saveTemplate`, `renameTemplate`, `deleteTemplate`, `importTemplate` | Options Library (`OptionButtonMapLibrary.qml`) renames and deletes |
| Button Map Options `button-map/<group>/<NN-key>` (chip-text, description-first, several-actions, unbound, undo-steps 80, rotate-snap 15, press-to-find, find-axes, mirror-pictures, chip-only, autosave, autosave-seconds 60, zoom-speed 100, rulers, recent-colours 10, print-area-color) | `button_map_options.py` | Options pane only |
| Saved styles `button-map/internal/styles` | `button_map_options.save_style` etc. | Options Library |
| Recent colours `global/internal/button-map-recent-colours` | `noteColour` | nobody |
| Options pane last group `global/internal/button-map-options-group`; tool rows `tool-rows`; window places (`ToolWindowMemory` "button-map", "print-export") | `button_map_options.py:268`, `window_placement.py` | nobody |
| In memory (window): `liveNodes`, `workNodes`, `liveImage`, `storedImage`, `livePhoto`, `workPhoto`, `editing`, `editBase`, `printSetup`, `printArea`, guides, grid, `labelMode` (not saved), `keptCopy` (chips copied, carried across devices) | `DialogJoystickButtonMap.qml` | nobody |
| In memory (editor): `nodes` (the same array the window passes in), selection, `hist` / `histAt` (cap from options, 80), `copiedNodes`, photo pose and look | `VkbRigEditor.qml` | the window (replaces `workNodes`, calls `seedHist`, `clearLayout`, `mirrorLayout`) |

## 4. Entry points

| User action / trigger | Handler | Function(s) |
|---|---|---|
| Home card menu → Button Map | `Main.openButtonMapForCard` (560) | new window, or `openForDevice(name, photo, guid)` (840) |
| Toolbar / Tools → Mapping → Button Map | `Main.openBlankButtonMap` (612), `main_commands.js:92` | `openBlank` (806) |
| Window opens | `Component.onCompleted` (888) | `loadLive` (354) → `_hw.load`, then `offerRecovery` (583) |
| File → Device → a device | `_inputDeviceItems` (177) | `openForDevice` → ask if dirty → `finishSwitch` (821) |
| Stick plugged in / out | `_devices.onModelReset` (93) | `devTick++`; reconnect → `loadLive` (not while editing) |
| File → Edit Mapping | menu (2485) | `enterEdit` (384) → `offerRecovery` or `_startEdit` (395) |
| File → Save, Ctrl+S | menu (2489), Shortcut | `saveEdit` (433) → `_hw.save` → read back `_hw.load` → `clearRecovery`, `dropPhotoStash` |
| File → Cancel | menu (2490) | `cancelEdit` (708) → `askLeave("cancel")` or `discardEdit` (677) → `restorePhoto`, `seedHist` |
| Window close (X), File → Close | `onClosing` (37) | `askLeave("close")` when dirty |
| Program quit | `Main.offerButtonMapLeaveThenQuit` (636), `Main` onClosing (1384) | `requestLeaveForAppQuit` (716) |
| Save / Discard / Cancel prompt | `_saveGate` (912) | `confirmLeaveSave` (729) / `confirmLeaveDiscard` (751) |
| Recovery prompt Restore / Discard / Not now | `_recoverGate` (893) | `restoreRecovery` (640) / `clearRecovery` + `putPhotoBack` (617) / `putOffRecovery` (626) |
| Autosave timer (every N s while editing) | `_autosaveTimer` (669) | `autosaveNow` (558) → `_hw.saveRecovery` / `clearRecovery` |
| File → History | menu (2493) | `DialogHistory.qml` for this device |
| File → Reset Layout | `_resetDlg` (918) | `resetLayout` (1088) → `pushHist`, `clearLayout` |
| File → Fit to Photo Frame | menu (2506) | `fitToPhotoFrame` (1666) → `sceneShiftList` (259) |
| File → Print & Export…, Ctrl+P | menu (2512) | `openPrintExport` (2327) → `PrintExportWindow` |
| Print & Export: paper, orientation, margins, background, scale, Freeform | `PrintExportWindow.qml` 384-471 | `host.setPrint` (1453) → `reshapePrintArea`, `persistUi` |
| Print & Export: Print… | `PrintExportWindow.qml:497` | `printNow` (1874) → `RigRenderer` job → `_hw.printImage` (QPrintDialog) |
| Print & Export: Export PDF / PNG / JPG | `openExportFile` (2335) → FileDialogs | `exportTo` (1859) → `RigRenderer` → `_hw.saveArea` |
| Print & Export preview drag / wheel | `PrintExportWindow.qml` | editor `shiftPrintArea` → `printAreaEdited` → `persistUi` |
| File → Templates → Save Layout as Template… | `_templateNameDlg` (2150) | `saveTemplateAs` (2128) → `_hw.saveTemplate` |
| File → Templates → Apply Template → name | menu (2536) | `openCopyLayout({template})` → `_copyDlg` → `copyLayoutFrom` (1945) → `_hw.templateNodes` → `_replaceLayout` (1968) |
| File → Templates → Manage Templates… (Rename, Export…, Delete, Import…) | `_templatesDlg` (2201) | `_hw.renameTemplate`, `exportTemplate`, `deleteTemplate` (asks first), `importTemplate` |
| Edit → Undo / Redo, Ctrl+Z / Ctrl+Y | menu (2561), Shortcut, right-click header | editor `undo` / `redo` (946/961) → `applySnap` |
| Edit → Duplicate / Copy / Paste, Ctrl+D/C/V | menu, Shortcuts | `rig_selection` `duplicateSelection`, `copySelection`, `pasteClipboard` |
| Edit → Paste Picture, Ctrl+Shift+V | menu (2593) | `pastePicture` (1298) → `_hw.pasteClipboardPictures` → `addPictures` |
| Drop picture files on the map | `_pictureDrop` (3107) | `dropPictures` (1328) → `_hw.importPictureFiles` (refused outside Edit) |
| Edit → Mirror Layout | menu (2599) | `mirrorNow` (1932) → `rig_mirror.mirrorLayout` |
| Edit → Delete / Group / Break Group / Lock / Unlock All | menu 2606-2633 | `deleteOrBreak` → `deleteSelected`; `groupSelection`, `ungroupSelection`, `toggleLockSelection`, `unlockAll` |
| Edit → Set Print Area / Clear Print Area; Alt+drag on empty map | menu 2637-2652, `RigPointerArea` | `rig_print_area` → `printAreaEdited` → `persistUi` |
| Edit → Copy Button Map from Device → device | menu (2655); list loaded on menu open (`_hw.savedLayouts`) | `openCopyLayout` → `_copyDlg` → `copyLayoutFrom` → `_hw.layoutNodes` → `_replaceLayout` (enters Edit first if needed) |
| Edit → Button Map Options… / Options tab | `_tools.setOpen("options")` | `ButtonMapOptions.set` → `onChanged` → `applyOptionsToEditor` (1515) |
| View → Chip Text | menu (2680) | `_opts.set("chip-text")` → `refreshActionLabels` (1588) |
| View → Labels Mode / Follow the Program | menu (2692) | `labelMode` → `labelModeNow` → `refreshActionLabels` → `_hw.actionLabels` |
| Profile edited, modes changed | `signal.profileChanged`, `signal.modesChanged` → `profileLabelsChanged` | `onProfileLabelsChanged` (1561) |
| Mode renamed / deleted | `signal.modeRenamed/modeDeleted` (1572) | `labelMode` follows / resets |
| View → Layers, Properties, Print Area, Reset Tool Rows, Command Palette (Ctrl+K) | menu 2717-2750 | `_tools.toggle`, `_palette.open` |
| View → Zoom to Fit Page (Ctrl+1), Zoom to Selection (Ctrl+2), Reset View (Ctrl+0) | menu 2754-2767 | `zoomToPage`, `zoomToSelection`, `resetViewNow` → `persistUi` |
| View → Rulers, Show Guides, Clear Guides, drag guide from ruler | menu 2771-2791, `rig_rulers` | `_opts.set("rulers")`; `rulerGuidesEdited` → `guidesFromEditor` (1505) → `persistUi` |
| View → Grid → Show / Snap / Snap to Entities / Size | menu 2793-2886 | `setGridPref` (1718) → `persistUi` |
| Photo → Choose Photo… | `_imageDialog` (1799) | `_hw.stashPhoto` → `_hw.copyImage` (writes module file `image` now) → `applyImage`, `resetPhoto` |
| Photo → Clear Photo | menu (2897) | `_hw.stashPhoto` → `_hw.clearImage` (deletes files now) → `applyImage(stockImage)` |
| Photo → Move Photo / Adjust Photo… / Reset Photo | menu 2915-2937, `_photoAdj` | `applyPhotoToEditor`, `setPhotoScale/Off/Rot`, `resetPhoto` (1254) → editor `notePhotoChange` |
| Adjust Photo look sliders | `_lookTimer` (1240, 150 ms) | `_hw.adjustedPhotoUrl` |
| Draw → Import Picture… | `_overlayDialog` (1817) | `_hw.copyOverlay` → editor `addOverlay` |
| Colour picker, Recent, Pick from Map | `_colorPop` (3700+) | editor `applyField`; `_hw.noteColour`; `takeEyedrop` → `_hw.colorAt` |
| Right-click map item | `Menus.ContextMenu` build `rig_menu.menuModel` | the `rig_*.js` action for each row |
| Pool: drag chip onto map; drag chip back onto pool; filter; Chip only | pool (3200+) | `dropPool` (1069) → `addChiplet`; `rig_selection.returnToPool`; `refreshReservoir` (1047) |
| Press a control while editing | `face.liveStamp` → editor `findTick` | `rig_find` selects the chip; `findNotPlaced` → pool filter |
| Live press (not editing) | `PairLiveThrottle` stamps → `liveStamp` | chips light (`litOf`), hotspot pulse; pool rows re-read (`_inventory.chips`) |
| Clipboard changes | `QClipboard.dataChanged` | `clipboardSerial++` (decides whether Ctrl+V pastes a picture) |
| Delete Device of the shown device | `Main.closeDeletedDevice` (484) | `map.close()` → `onClosing` (asks when dirty) |

## 5. Talks to

| Direction | Other subsystem | How |
|---|---|---|
| calls out | Module files (registry, `module_file`) | `resolve_module_slug`, `module_file.load_for_update`, `write_json`, `report_refused`, `read_doc`; private `registry._binding_store`, `_guid_for_name`, `_name_key` |
| calls out | History | indirectly: every `write_json` goes to `history_modules.note_write` (Button Map area) |
| calls out | Devices / input side | `gremlin.modules.hardware.device_info` (pool rows), `ViewerDeviceModel`, `DeviceNames` (display names), `device_has_name` |
| calls out | Live feed (input module runtime) | `PairLiveThrottle` (`InputModuleRuntime().event`), `MappedButtonModel/AxisModel/HatModel` (wire labels) |
| calls out | Output modules | `output.vjoy_state` via `PairLiveThrottle._poll_vjoy` (shown values of wired vJoy outputs) |
| calls out | Profile / actions | `shared_state.current_profile`; `input_pairing._items_for_guid`, `_dest_labels_for_item`, `_walk_actions`, `_device_name` (private); `button_map_labels.action_labels` |
| calls out | Module Setup data | `module_model._load_module_doc` (claims for the pool) |
| calls out | Settings | `Configuration` (options, recent colours, styles, tool rows, window places) |
| calls out | Run state | `backend.gremlinActive`, `backend.currentMode`, `uiState.currentMode` (labels mode); `backend.noteSave` (footer) |
| calls out | Windows / Qt | `QPrintDialog`, `QPdfWriter` (`util.save_images_as_pdf`), `QClipboard`, `QDesktopServices` |
| called by | Main window | `openButtonMapForCard`, `openBlankButtonMap`, `buttonMapNeedsLeave`, `offerButtonMapLeaveThenQuit`, `closeDeletedDevice` |
| called by | Module Setup (`DialogConfigureModule.qml`) | own `HardwareProfile`: `profilePhotoUrl`, `keepPhoto`, `copyImage`, `imagesFolderUrl` (writes the same photo) |
| called by | Device Pack (`DialogDevicePack.qml`) | own `HardwareProfile`: pack export / import (carries `nodes`, photo, pictures) |
| called by | HidHide (`hidhide.py:493`), Xbox page (`Xbox360Face.qml`) | `profilePhotoUrl` for device pictures |
| called by | Options Library (`OptionButtonMapLibrary.qml`) | templates and styles rename / delete |
| called by | History window | Restore writes the module file (map, photo, pictures); the open Button Map is not told |

## 6. Threads and timers

No Python threads in this subsystem: every slot runs on the main (GUI) thread, including file writes, PDF writing, photo adjustment (`adjust_photo` on the full photo) and `QPrintDialog.exec()` (a nested event loop). History writes go to History's own writer thread (not here).

Timers (all Qt timers on the main thread):
- `_autosaveTimer` (window 669): every `autosave-seconds` (default 60, never under 10) while editing and Autosave is on.
- `_lookTimer` (window 1240): 150 ms after a look slider rests, makes the adjusted photo.
- Editor: `_seedTimer` 80 ms after `nodes` changes (tidies the map; replaces the top undo step), `_photoHist` 400 ms (one undo step for a run of nudges, photo or colour changes), `_findMsgTimer` 3 s, `_hotPulseTimer` 30 ms while a press pulse runs, `_spineHold` 450 ms (hold right button to delete a spine).
- `VkbRigFace` one-shot 50 ms repaint at start.
- `PairLiveThrottle`: 50 ms axis flush and 50 ms vJoy poll (only while a wired vJoy is watched).
- `PrintExportWindow`: 400 ms, 150 ms (`_pageTimer`), 300 ms (`_sharpTimer`) preview timers; `RigRenderer` queue timer.
- Many `Qt.callLater` hops (seed history after Cancel, restore, copy layout).

Time: `datetime.now()` stamps recovery copies and templates (`savedAt`); `Date.now()` in `rig_groups._uid`, `rig_hotspot` pulses and photo reload stamps. None is a timed loop, so the `gremlin.clock` rule does not apply.

## 7. Rule breaks

| # | Rule | Where | What | Status |
|---|---|---|---|---|
| RB1 | Single owner: the device photo | `hardware_profile.py:2429-2473` (Button Map `copyImage`), `DialogConfigureModule.qml:123,221` (Module Setup `keepPhoto` / `copyImage`), `module_model.py:2289-2293` (Module Setup save sets `image` from the folder) | Two editors write the same photo files and the same `image` key; Module Setup's Import Image writes at once with no safety copy | CONFIRMED |
| RB2 | Single owner: the module file | `hardware_profile.py:2318` (`save`), `module_model.py:2285` (Module Setup), Device Pack, History Restore | Button Map Save merges onto the file on disk, but the window never re-reads a file changed elsewhere; an edit's Save writes its old `nodes` / `image` over a Restore or pack import | CONFIRMED (no reload in code); harm SUSPECTED |
| RB3 | Writes only on Save (help: "the module file is only written by Save") | `DialogJoystickButtonMap.qml:1691-1716` (`persistUi`), `:3026-3031` (print area), `:1505` (guides), `hardware_profile.py:2455-2466` (`copyImage` writes `image`) | Print area, guides, grid, view and the photo's `image` key are written in the middle of an edit; Cancel takes back the photo but not the print area or guides | CONFIRMED |
| RB4 | Duplicated logic: page size | `VkbRigEditor.qml:153-156`, `DialogJoystickButtonMap.qml:444-455`, `hardware_profile.py:2325-2331`, `module_model.py:2286-2288` | 32000 x 18000 page, 0.75 photo frame written in four places; `imageWidth 1348 / imageHeight 1380` hard-coded in the window | CONFIRMED |
| RB5 | Duplicated logic: control labels | `hardware_profile.py:1429-1477` (`_output_labels`, `_label_for`: every mode joined) vs `button_map_labels.action_labels` (one mode, inherited) | Two producers of "what this control does"; the pool search uses the first, chips the second | CONFIRMED |
| RB6 | Duplicated logic: mode inheritance | `button_map_labels.py:70-82,167-178` vs runtime `EventHandler.build_event_lookup` | Labels re-implement parent-mode inheritance on their own | CONFIRMED that it is separate; whether results can differ SUSPECTED |
| RB7 | One door per module (private helpers used from outside) | `hardware_profile.py:26-34` (`registry._binding_store`, `_guid_for_name`, `_name_key`), 1429-1510 (`input_pairing._items_for_guid`, `_dest_labels_for_item`, `_walk_actions`, `_device_name`; `module_model._load_module_doc`), `button_map_labels.py:22` (`_walk_actions`) | Reaches into other modules' private functions | CONFIRMED |
| RB8 | Main thread kept light | `JoystickButtonMapCard.qml:54-59` → `hardware_profile.chips_for_guid` (1480) | Every live press (stamp change) re-reads and parses the module file, asks the device driver and walks the profile, on the main thread | CONFIRMED in code; slowness SUSPECTED (not measured) |
| RB9 | Single owner: one file, one job | `hardware_profile.py` (2656 lines) | Button Map document, photos, pictures, print, templates, recovery, Device Pack export/import, module-file import, Delete Device in one file and one QML type | CONFIRMED |
| RB10 | Device-specific data used for every device | `VkbRigEditor.qml:1006-1040` `physNames`, used by `rig_chips.isUserFriendly` (`rig_chips.js:63-65,92-94`) | A user's chip name that equals an EVO R part name for that number (e.g. "White cap" on Button 4) is treated as no name on any device | CONFIRMED in code; seen by a user SUSPECTED |
| RB11 | Program writes outside the user's data folder | `hardware_profile.py:2596-2600` `imagesFolderUrl` | Creates `qml/images` under the install folder (Program Files when installed) to start the file dialogs there | CONFIRMED; failure when installed SUSPECTED |
| RB12 | Layer rule | live feed `pair_live.py` (input module runtime), pool rows `hardware.device_info` | Both go through the approved doors; no Button Map code touches dill, vJoy or ViGEm directly | checked: no break found |
| RB13 | Thread rules | whole subsystem | No threads started; no unbounded waits | checked: no break found |

## 8. Behaviour spec

**Opening and devices**
- **S1** It should open from a device card's right-click menu, the toolbar, or Tools → Mapping → Button Map, and there should be one Button Map window; opening it for another device reuses that window. [help: Tools / Button Map] [user confirmed 2026-10-06; was code only: one window, `Main.qml:572-585`]
- **S2** It should show "Choose a device from the File menu." when no device is chosen, and then write no file at all (zoom or grid changes don't create one). [tracker: AU-09] [help: File menu and export]
- **S3** It should list the devices under File → Device, with a tick on the one shown; switching asks to save when there are unsaved edits, and Cancel in that question stays on the current device. [help: File menu and export] [tracker: C25] [test-plan: BM-F01] [test: test_button_map_devices.py::test_device_menu_stays_during_an_edit]
- **S4** It should not list vJoy or Xbox outputs in File → Device (their cards still open it). [tracker: AU-75, user's choice]
- **S5** It should cover an unplugged stick's map with "Connect <name> to see its Button Map." and load the map by itself when the stick connects. [tracker: R1] [test: test_button_map_devices.py::test_unplugged_stick_shows_no_map] [test: test_button_map_devices.py::test_map_loads_when_the_stick_connects]
- **S6** It should still export an unplugged stick's map. [test: test_button_map_devices.py::test_unplugged_stick_still_exports]
- **S7** It should show outputs, Keyboard, Logical Device and OSC without any stick. [test: test_button_map_devices.py::test_outputs_and_built_in_devices_need_no_stick]
- **S8** It should keep an edit on screen when its stick is unplugged, with "<name> is disconnected. You can still save or cancel this edit." [tracker: R1] [test: test_button_map_devices.py::test_an_edit_survives_device_changes]
- **S9** It should open the second of two identical sticks from its own module file. [test: test_twin_devices.py::test_the_button_map_of_the_second_twin_opens_its_own_file] [tracker: DEV8]
- **S10** It should keep a renamed stick's photo with the module file its Button Map opens. [test: test_audit3_module_files.py::test_renamed_sticks_photo_goes_with_the_file_its_button_map_opens] [tracker: AU-64 part]
- **S11** It should show no photo for a device that has none, never another device's photo or the Gladiator photo. [tracker: B26]
- **S12** It should show a damaged module file as an empty map and refuse to save into it, saying so. [test: test_module_file_damage.py::test_button_map_save_is_refused] [test-plan: MODULE-FILE-DAMAGE]
- **S13** It should close the Button Map when its device is deleted. [user confirmed 2026-10-06; was code only: `Main.qml:489-492`]

**Live map**
- **S14** It should light a chip while its control is pressed when not editing; hovering a chip says which control it is, and dragging pans. [help: Overview] [test-plan: BM-Z02]
- **S15** It should take presses only from the input module feed (claimed inputs), never from raw hardware. [user decision: layer rule]
- **S16** It should show on a chip where the control's wire goes, and "(not claimed)" when that output is not claimed. [help: Overview] [help: Module File / claims]
- **S17** It should never change actions: moving, renaming or deleting a chip changes only the picture. [help: Overview] [glossary: Button Map]
- **S18** It should call the lines leaders, never wires. [glossary: Wire] [tracker: G-WIRELEADER]

**Edit, Save, Cancel, Close**
- **S19** It should start editing with File → Edit Mapping, and entering Edit is not a change: nothing to undo, and Cancel does not ask. [help: Overview] [tracker: BM11] [tracker: R2] [test: test_button_map_devices.py::test_entering_edit_is_not_a_change]
- **S20** It should write the layout to the device's module file on Save (Ctrl+S), read it back, and say "Saved to the module file."; when it can't, say "Not written. It is still only on this screen." [help: Overview] [test-plan: BM-F02..04]
- **S21** It should save a name or text still being typed when Save is pressed. [tracker: BM15]
- **S22** It should keep every module-file key it doesn't write (claims, names, calibration, Appearance) on Save. [tracker: G-BMCALIB] [test: test_button_map_save_keeps.py::test_save_keeps_calibration_and_other_keys]
- **S23** It should write the module file whole through a temporary file, so a crash never leaves half a file. [tracker: BM12]
- **S24** It should compare later changes with what was just saved after a Save. [tracker: AU-07]
- **S25** It should ask before Cancel when there are changes; choosing Save there saves and leaves Edit. [test-plan: BM-F02..04] [tracker: AU-26]
- **S26** It should, on Cancel or Discard, put the session's starting photo back (files and the module file's `image`), and leave no undo steps behind. [tracker: A3] [tracker: A5] [tracker: G-PHOTORAW] [test: test_data_safety.py::test_cancel_puts_the_starting_photo_back] [test: test_button_map_save_keeps.py::test_cancel_puts_the_photo_back_through_the_module_file_writer]
- **S27** It should leave a damaged module file alone on Cancel, and say so. [test: test_button_map_save_keeps.py::test_cancel_leaves_a_damaged_module_file_alone]
- **S28** It should ask once when the window closes or the program quits with unsaved edits, and finish closing after Save or Discard. [help: Overview] [test-plan: W-03] [test-plan: BM-F12]
- **S29** It should write the module file only on Save. [help: Button Map Options / Autosave] (see Q1, G1, G2: the code writes some parts earlier)
- **S30** It should count a new photo of the same file type as an unsaved change. [tracker: AU-92] [test: test_audit2_button_map.py::test_the_kept_photo_says_a_change_is_unsaved]
- **S31** It should leave nothing behind when the window closes (no leaked objects, commands removed from the shared palette). [test: test_button_map_lifecycle.py::test_button_map_leaves_nothing_behind] [user confirmed 2026-10-06; was code only: `Commands.removeOwner("buttonmap")`]

**Recovery copies**
- **S32** It should keep a recovery copy of unsaved edits (photo, pose, map) every "Seconds between recovery copies" while editing, and remove it when everything is undone. [help: Button Map Options] [test-plan: BMAP2-1]
- **S33** It should never write recovery copies more often than every 10 seconds, whatever the option says. [user confirmed 2026-10-06; was code only: `DialogJoystickButtonMap.qml:671`]
- **S34** It should offer Restore, Discard or Not now when the device opens or Edit starts and a copy exists; Restore opens the edits unsaved; Discard deletes the copy and puts the saved photo back; Not now keeps both and offers them next time. [help: Button Map Options] [tracker: AU-115] [tracker: AU-78] [test: test_audit3_screens.py::test_button_map_recovery_offer_and_device_switch]
- **S35** It should put an open offer off (never apply it to another device) when another device is shown. [tracker: AU-115]
- **S36** It should, after a crash in the middle of a photo change, bring back the saved photo unless a recovery copy is waiting. [tracker: AU-08]
- **S37** It should quietly remove a recovery copy that is the same as the saved map. [user confirmed 2026-10-06; was code only: `DialogJoystickButtonMap.qml:600-603`]
- **S38** It should treat a damaged or non-map recovery copy as none. [test: test_button_map_recovery.py::test_a_broken_copy_reads_as_none] [test: test_button_map_recovery.py::test_rejects_what_is_not_a_layout]

**Photo**
- **S39** It should offer the Photo menu only while editing. [help: File menu and export]
- **S40** It should, on Choose Photo…, copy the picture into the device's folder as its photo and keep the old one so Cancel can put it back. [help: The photo] [tracker: A3] [test-plan: WORKFLOW-4]
- **S41** It should, on Clear Photo, leave no photo (decision Q4: no stock or card photo); if the file can't be removed, put the photo back and say "Clear Photo Failed". [help: The photo] [tracker: N12] [changed 2026-10-06 to follow decision Q4]
- **S42** It should move, size (25% to 400%), offset and turn the photo with Move Photo and Adjust Photo…; Reset Photo puts the pose back and leaves the look. [help: The photo] [test: test_photo_pose.py::test_defaults_and_clamps]
- **S43** It should apply Brightness, Contrast, Greyscale and Fade, save them with the layout, show them on the live map and in exports, and step through them with Undo. [help: The photo] [test-plan: BMAP2-11] [test: test_photo_pose.py::test_look_kept_clamped_and_only_when_changed]
- **S44** It should let the photo be hidden or locked from its Layers row; the flags are saved only when on. [help: The photo] [test: test_photo_pose.py::test_layers_flags_kept_only_when_on]

**Editing the map**
- **S45** It should list in the pool the device's controls that are not on the map, filterable by name, number or output. [help: Overview] [test-plan: BM-R01..05]
- **S46** It should fill the pool from the device's claimed controls; with no claims, from what the device reports; unplugged, from what the profile uses. [user confirmed 2026-10-06; was code only: `hardware_profile.py:1491-1508`]
- **S47** It should place chips with no leader and no hotspot when Chip only is ticked. [help: Chips] [test-plan: BM-CHIP-ONLY-DBLCLICK]
- **S48** It should let a chip name have two rows (Shift+Enter). [tracker: BM30]
- **S49** It should remove every selected item as one undo step on Delete; a selected spine or table cell goes alone. [tracker: A4] [tracker: A6] [test-plan: SAFE-2]
- **S50** It should turn leader ends and callout pointers aimed at a removed chip into free ends where they are drawn. [tracker: BM7]
- **S51** It should take chips off the map when they are dragged back onto the pool; locked chips stay; Undo brings them back. [help: Chips] [test-plan: BMAP3-2]
- **S52** It should keep chips where they are when grouped, and leave each chip as it is on Break Group. [help: Groups and 5-way formats] [tracker: BM8] [test-plan: BM-GROUPS]
- **S53** It should remove a whole group when Delete is used on an open group's Layers row. [tracker: BM10] [test: test_button_map_fixes.py::test_deleting_an_open_group_removes_the_group]
- **S54** It should keep the stacking order through save and reopen; only old maps with `zLayer` are sorted once. [tracker: BM1] [test: test_rig_stacking.py::test_list_order_is_kept] [test: test_rig_stacking.py::test_old_layouts_are_sorted_once_by_layer]
- **S55** It should make one undo step per command: Hide Selected is one step, a run of arrow nudges is one step, a colour-picker drag is one step, and Undo/Redo first save a waiting step. [tracker: BM14] [tracker: BM3] [test: test_button_map_fixes.py::test_nudges_in_a_row_are_one_step] [test: test_button_map_fixes.py::test_hide_selected_is_one_step]
- **S56** It should go back as many steps as Button Map Options → Undo steps (80 by default), and offer Undo and Redo only while editing. [help: Button Map Options] [tracker: A5]
- **S57** It should undo the map and the photo's pose, flags and look, and also Choose Photo, Clear Photo, print area changes and guide changes (each one undo step); grid and view are not undo steps. [changed 2026-10-06 to follow decision Q3]
- **S58** It should select a pressed control's chip while editing (Press to find), show an unplaced one in the pool, and add no undo step or act mid-drag. [help: Selecting, undo and keys] [test-plan: BMAP2-2] [tracker: B24]
- **S59** It should mirror the whole map left to right with Edit → Mirror Layout (pictures flipped only with Mirror pictures on), and Undo puts it back. [help: Mirror layout] [test-plan: BMAP2-5]
- **S60** It should, with Fit to Photo Frame, shrink an older oversized layout once per edit, moving hotspots, callout pointers and free table cells too; Undo puts it back and makes it available again. [help: File menu and export] [tracker: BM5] [tracker: F1] [tracker: B22]
- **S61** It should, on Reset Layout, ask first, then clear chips, leaders, hotspots, drawings, text, pictures and tables; actions stay; Ctrl+Z brings the layout back. [help: File menu and export] [tracker: A7]
- **S62** It should add pictures from Import Picture…, Paste Picture (Ctrl+Shift+V, also files copied in Explorer) and files dropped on the map, and save them beside the module file. [help: Pictures] [test-plan: BM-PICTURES] [test-plan: BM-DROP-COPY] [test: test_paste_picture.py::test_dropped_files_keep_only_pictures]
- **S63** It should refuse a picture drop outside Edit with "Click Edit Mapping first, then drop the picture again." [user confirmed 2026-10-06; was code only: `DialogJoystickButtonMap.qml:1332-1335`] [help: Pictures says "while editing"]
- **S64** It should paste with Ctrl+V a picture copied after the last chip copy, and the chips otherwise. [help: Selecting, undo and keys] [test-plan: BM-PICTURES]
- **S65** It should keep chips copied with Ctrl+C when another device's map opens, so they can be pasted there. [tracker: AU-105] [user confirmed 2026-10-06; was code only: `carryCopy` 975]
- **S66** It should not draw a hidden item on the live map, and leave it out of exports. [help: Layers panel] [test-plan: BMAP-4]
- **S67** It should keep saved styles and recent colours for every device. [help: Saved styles] [help: Colors] [test: test_button_map_colours.py::test_recent_colours_newest_first_once_at_most_ten] [test: test_button_map_options.py::test_saved_styles_save_replace_rename_delete]
- **S68** It should place every position as a fraction of a 32000 x 18000 page with a 24000 x 13500 photo frame in its middle. [user confirmed 2026-10-06; was code only: `VkbRigEditor.qml:153-156`] [tracker: BM41 plans to change it]
- **S69** It should open files without a photo frame value as they are and not write them back. [tracker: B25]

**Action labels**
- **S70** It should show on chips the control's Name, Action, or Name and action (View → Chip Text, also in Options → Labels). [help: Action labels] [test-plan: BMAP2-3]
- **S71** It should take the text from one mode: the chosen Labels Mode, or with Follow the Program the running mode while running and otherwise the mode chosen in the main window. [help: Action labels]
- **S72** It should show a parent mode's actions for a control with none in the chosen mode. [help: Action labels] [test: test_button_map_labels.py::test_a_child_mode_inherits_unless_it_binds_the_control]
- **S73** It should follow profile edits at once, follow a renamed Labels Mode, and go back to Follow the Program when that mode is deleted. [help: Action labels] [tracker: AU-112] [test: test_audit3_modes.py::test_button_map_labels_mode_follows_a_rename]
- **S74** It should forget the chosen Labels Mode when the window closes. [user confirmed 2026-10-06; was code only: `labelMode` is not saved]

**Copy layout and templates**
- **S75** It should list under Edit → Copy Button Map from Device the other devices whose module file holds a map (never this one). [help: File menu and export] [tracker: F8] [test: test_button_map_copy_layout.py::test_lists_other_devices_with_a_layout]
- **S76** It should replace this map's chips, leaders and drawings with the copy, keep this device's photo, offer "Mirror left to right" (ticked for a device, unticked for a template), and save nothing until Save. [help: File menu and export] [user confirmed 2026-10-06; was code only: tick defaults `DialogJoystickButtonMap.qml:1992`]
- **S77** It should, when copying outside Edit, start Edit from the current map first, so Undo brings the old map back. [tracker: BM9]
- **S78** It should take back a mirrored copy with one Undo. [tracker: AU-27, open]
- **S79** It should save a layout as a named template, ask before replacing one of the same name, and refuse an empty layout. [help: File menu and export] [test-plan: BMAP2-6] [user confirmed 2026-10-06; was code only: the replace question, `DialogJoystickButtonMap.qml:2132-2135`] [test: test_button_map_templates.py::test_nothing_to_save]
- **S80** It should rename, export to a file, import (a taken name gets a number) and delete templates, asking before a delete and saying when rename or export fails; a failed template export or rename names the file, the folder and the reason, as in Q19. [user decision 2026-10-07: D-07-TEMPLATE-FAIL] [help: File menu and export] [tracker: C13] [tracker: N12] [test: test_button_map_templates.py::test_export_and_import] [test: test_button_map_templates.py::test_rename_and_delete]
- **S81** It should keep in a template where its pictures are, not the picture files. [help: File menu and export]

**Print and export**
- **S82** It should keep Print & Export's settings (paper, orientation, margins, background, scale, Freeform) with the map, the same for every print and export. [help: File menu and export] [tracker: BM34] [tracker: BM38]
- **S83** It should make 100% scale the photo's own pixels (no photo: the page 1920 pixels wide), from 10% to 800%, whatever the window size or screen scale. [help: File menu and export] [test: test_print_export_window.py::test_every_screen_scale_gives_the_same_picture] [test: test_button_map_print_area.py::test_scale_and_saving]
- **S84** It should cap an export's longest side at 16384 pixels. [user confirmed 2026-10-06; was code only: `DialogJoystickButtonMap.qml:1492-1500`]
- **S85** It should take only the print area for every print and export; Alt+drag or Edit → Set Print Area draws it; with a paper it keeps the paper's shape; Clear Print Area goes back to the whole page. [help: File menu and export] [tracker: BM33] [test: test_button_map_print_area.py::test_an_export_takes_only_the_area] [test: test_button_map_print_area.py::test_the_area_keeps_the_papers_shape]
- **S86** It should show the print area frame only while editing. [tracker: BM45] [test: test_button_map_print_area.py::test_the_frame_shows_only_while_editing]
- **S87** It should leave selection marks, handles, guides, grid, hidden items and the red debug frame out of every print and export, and draw lines and text at the export's size. [help: File menu and export] [help: Diagnostics / red debug mode] [tracker: BM36]
- **S88** It should write a PDF on the chosen paper inside its margins, or, with Freeform, on a page of the area's own shape at 96 pixels an inch. [help: File menu and export] [test: test_button_map_export.py::test_pdf_without_a_paper_is_96_pixels_an_inch] [test: test_button_map_export.py::test_pdf_on_a_paper_is_that_page]
- **S89** It should make the Light background a white page with every colour's lightness turned over, the photo unchanged, the screen unchanged. [help: File menu and export] [test: test_print_export_window.py::test_light_is_a_white_page]
- **S90** It should show Windows' printer dialog before printing, print nothing on Cancel, and with Freeform turn the page to landscape when the area is wider than tall. [help: File menu and export] [test-plan: BMAP2-15]
- **S91** When an export can't be written it should say "Export failed." with the file, the folder and the reason (folder missing or read-only, file read-only or open in another program), as Template export does. [changed 2026-10-06 to follow decision Q19]
- **S92** It should keep the Print & Export window hidden until asked for. [tracker: BM44] [test: test_print_export_window.py::test_it_stays_closed_until_asked_for]
- **S93** It should move the print area by dragging the preview and resize it with the wheel, not while it is locked. [help: File menu and export] [tracker: BM40] [test: test_print_export_window.py::test_dragging_and_zooming_the_preview_moves_the_area]

**View, options, History**
- **S94** It should zoom from 50% to 600%, with Ctrl+0, Ctrl+1 and Ctrl+2. [help: View, zoom and grid] [tracker: BM42]
- **S95** It should keep the view and grid with the device's map at once (outside Edit too), and not list those changes in History. Outside Edit, guides and the print area are kept at once too; in Edit they wait for Save and Cancel takes them back (decision Q1). [changed 2026-10-06 to follow decisions Q1 and 03 Q4] [help: Rulers and guides] [help: History] [test-plan: BM-V02 / S-25 "by design"] [test: test_history_recording.py::test_the_maps_view_alone_is_not_kept]
- **S96** It should not create a module file just because the user zoomed or changed the grid outside Edit. [tracker: AU-92] [user confirmed 2026-10-06; was code only: `persistUi` 1700-1703]
- **S97** It should list Button Map saves in History under Button Map, with the old map and its pictures, so they can be put back. [help: History] [tracker: G-HISTORY] [test: test_history_recording.py]
- **S98** It should apply Button Map Options to every device and keep them at once; the pane remembers its last group. [help: Button Map Options] [tracker: BM46] [test: test_button_map_options_pane.py::test_a_change_is_kept_and_so_is_the_group]
- **S99** It should keep the tool rows, tabs, pins, locks and floating panels for next time; Reset Tool Rows puts them back. [help: Overview] [test: test_button_map_tool_row.py::test_rows_and_docks_are_kept_and_reset]
- **S100** It should list every usable menu command in the Command Palette (Ctrl+K). [help: Overview]
- **S101** An export (PDF, PNG, JPG) should be written in the background: the window stays responsive while a large picture is encoded and shows that it is busy; when it is done, a failure is reported as in Q19 (file, folder, reason) and a success as before. Only one export runs at a time. [user decision 2026-10-07: D-07-EXPORT-BG]
- **S102** The Layers panel should have a **Search layers…** box, full width under its header, and below it one toggle per kind of row (**All · Chips · Groups · Hotspots · Leaders · Shapes · Lines · Pictures · Text · Tables · Photo**), replacing the old single-choice kind buttons. Any number of kinds can be on; none on means every row shows and lights **All**; **All** turns them all off again. The search filters the rows of the kinds that are on, as you type (any case, matching anywhere), on four things: the row's name, the control (Button 12, Hat 1, X Axis, even when the chip has a friendly name), what the chip shows (its action or description text), and the kind of row. A matching hotspot, leader or group member shows under its chip or group, which shows dimmed as a heading when it doesn't match itself. While a filter is on, a line says how many rows match ("12 of 148") or "No layers match". Ctrl+F in the Button Map goes to the box (opening Layers if it is closed), Esc in the box clears it, Enter selects every match on the map and brings the first into view, and the box's × clears it. Eye, lock, rename, drag and delete work on the shown rows. The kinds and the search stay while the Button Map is open (also when another device's map is shown) and go back to none and empty when the Button Map closes or the program restarts. [user decision 2026-10-07: D-07-LAYERS-SEARCH]

## 9. Questions for the user

- **Q1** Help says "the module file is only written by Save", but the print area, guides, grid and view are written the moment they change, also in the middle of an edit, and Cancel does not take back a print area or guide change. Which is right? *Recommend:* view, zoom and grid stay instant (they are not the map); the print area, print setup and guides become part of the edit (written by Save, taken back by Cancel, undoable). Help then says so.
- **Q2** Choose Photo writes the photo into the module file at once (`copyImage`), so History lists "Saved <device>: Button Map photo" for a change the user never saved, and Cancel adds a second entry. *Recommend:* the new photo waits beside the old one until Save; only Save writes `image`; History sees one entry per Save.
- **Q3** Undo covers the map and the photo's pose and look, but not Choose Photo, Clear Photo, the print area or guides. *Recommend:* Choose Photo and Clear Photo become undo steps (the kept copy already exists); print area and guides too if Q1 makes them part of the edit.
- **Q4** Help says Clear Photo "goes back to the module's picture". The code deletes the photo files and shows the card's photo (for EVO and Gladiator names, a stock photo that is not in the repo, so in practice no photo). What should Clear Photo leave? *Recommend:* "no photo", and help says "Clear Photo removes the photo".
- **Q5** Module Setup also changes the device photo (Import Image writes it at once, with no kept copy, and its Save sets `image`). *Recommend:* one owner for the device photo; Module Setup's photo waits for its Save and can be cancelled, as in the Button Map.
- **Q6** When the module file changes elsewhere while the Button Map is open (History Restore, Device Pack import, Module Setup photo), the Button Map keeps showing its old copy, and Save in an edit writes the old map and photo back over the change. *Recommend:* outside Edit, reload; in Edit, warn on Save ("the module file changed since you started editing") with Keep mine / Take theirs.
- **Q7** Delete Device while that device's map is being edited: the window closes, but first asks Save / Discard; Save would write a new module file for the deleted device. *Recommend:* close without saving, with a short note that the device was deleted.
- **Q8** A template, or another device's layout, can hold chips for controls this device does not have (Button 30 on a 20-button stick). They are copied as they are. *Recommend:* keep them, and say after the copy "3 chips are for controls this device does not have" so the user can remove them.
- **Q9** The Labels Mode choice is forgotten when the window closes. *Recommend:* keep it per device for the session only (as now); confirm.
- **Q10** A chip name equal to an EVO R part name for that number (for example "White cap" on Button 4) is treated as "no name" on every device, because of a hard-coded EVO R list. *Recommend:* drop that check; a typed name is always the user's.
- **Q11** Pictures added during an edit stay in the device folder after Cancel, and every photo or picture ever chosen is also copied into `modules/library` and never removed. Recovery copies and photo safety copies survive Delete Device. Who cleans these? *Recommend:* Save and Cancel remove the device folder's pictures no map uses; Delete Device removes its recovery copy and photo safety copy; the library gets a "Remove unused" button in Options → Library.
- **Q12** The code knows stock photos (`qml/images/vkb_gladiator_rig.jpg`, `vkb_gladiator_evo_l.jpg`) and copies an old `qml/maps` folder at start, but neither is in the repo; the BM41 plan speaks of "built-in maps in qml/maps". Are there built-in maps or photos to ship? *Recommend:* if not, remove the stock-photo and legacy-copy code and fix the BM41 note; if yes, add them to the repo and the installer.
- **Q13** Choose Photo and Import Picture open in `qml/images` inside the program folder, creating it there (Program Files when installed). *Recommend:* open in the user's Pictures folder, or last folder used.
- **Q14** The page size (32000 x 18000, photo frame 0.75) is written into every map but never read back, so BM41 cannot tell old maps from new. *Recommend:* one constant, read on load; BM41's conversion uses it.
- **Q15** A recovery copy that equals the saved map is deleted without asking (S37). *Recommend:* keep as is.
- **Q16** Recovery copies are never written more often than every 10 seconds, whatever the option says (S33). *Recommend:* keep, and give the option a minimum of 10 so the screen agrees.
- **Q17** The glossary calls Button Map Options "its own window, not in the main Options"; it is now a pane on the tool row (BM46, help). *Recommend:* update the glossary row.
- **Q18** Print & Export works outside Edit, and changing the paper or scale there writes the module file at once (when one exists). *Recommend:* keep; it is a setting of the map's prints, like the view.
- **Q19** A failed export only says "Export failed." with no reason or path. *Recommend:* say which file and why (folder read-only, file open elsewhere), as Template export does.

## 10. Known gaps

**Code against spec or rules**
- **G1** Print area, guides, grid and view are written during an edit and not taken back by Cancel; help says only Save writes (RB3, Q1). `DialogJoystickButtonMap.qml:1691-1716, 3026-3031, 1505-1513`.
- **G2** Choose Photo writes `image` into the module file at once; History records an entry for an unsaved photo, and another when Cancel puts it back (RB3, Q2). `hardware_profile.py:2455-2466` → `module_file.write_json` → `history_modules._record`.
- **G3** Save copies the photo and pictures into the device folder (`_pack_assets`, `hardware_profile.py:2333`) before it checks for a damaged module file (2335); a refused Save still changes files. CONFIRMED in code.
- **G4** `save` assumes the text is a JSON object; a list or number raises at `payload["kind"]` (`hardware_profile.py:2325`) instead of returning False. QML always sends an object, so SUSPECTED harmless.
- **G5** `saveUi` on a device with no module file calls the full `save` (2376): in an edit, a print area or guide change creates the module file with the saved (old) map and copies the photo. CONFIRMED.
- **G6** No reload when another part of the program changes the module file; an edit's Save writes over it (RB2, Q6).
- **G7** Delete Device during an edit asks Save, which would recreate the deleted file (Q7). `Main.qml:489-492`.
- **G8** Three writers of the device photo: Button Map, Module Setup, Device Pack (RB1, Q5).
- **G9** Undo does not cover Choose / Clear Photo, print area, guides (Q3).
- **G10** Chip names equal to EVO R part names are dropped on every device (RB10, Q10).
- **G11** Every live press re-reads the module file and the profile on the main thread to rebuild the pool rows (RB8). `JoystickButtonMapCard.qml:54-59`.
- **G12** Two producers of control labels and a second copy of mode inheritance (RB5, RB6).
- **G13** Page size in four places, never read on load (RB4, Q14).
- **G14** `hardware_profile.py` reaches into private helpers of `registry`, `input_pairing` and `module_model` (RB7).
- **G15** `imagesFolderUrl` creates a folder in the install folder (RB11, Q13).
- **G16** `profilePhotoUrl` calls `self.load()` (2621), so asking for a photo also changes that object's `path` / `text` and emits `documentChanged`. Only Module Setup, HidHide and Xbox objects call it, not the Button Map's own; SUSPECTED harmless.
- **G17** Stock-photo code and the legacy `qml/maps` copy point to files not in the repo (Q12).
- **G18** `_resolve_existing` (1791-1824) falls back to any file of the same name in `modules/`, `overlays/` or `library/`; a stored picture that is missing can be replaced by another device's picture with the same name. SUSPECTED.

**Things nothing owns**
- **G19** Unused pictures in `modules/<slug>/` after Cancel or delete of a picture; `modules/library/` grows with every photo and picture ever chosen; recovery copies and photo safety copies of deleted devices (Q11).
- **G20** Templates whose pictures were moved or deleted: nothing checks or says so (template keeps paths only, S81).
- **G21** Chips for controls the device lacks after a copy or template (Q8).

**Stale notes**
- **G22** Tracker AU-64's note says Button Map photo folders still use the device's own name; the code now uses the module-file rule for the photo, pictures, recovery and safety copy (`_module_slug`, 1755). Only the stock-photo choice (2629-2642) and the Device Pack export file name (1864) go by name.
- **G23** Test plan rows BM-F07..08 / S-24 (Clear image can't be undone, fixed by A3), S-22 / BM-X1 (map pack export, removed), BMAP2-4 (Export modes, removed by BM37), BMAP2-12 and BMAP2-15 (Options → Export → Light page / Print light, replaced by Print & Export Background) describe things that are no longer there.

**Open tracker items for this subsystem**
- **AU-27** (open): a mirrored Copy Button Map may take two undos; not verified (S78).
- **AU-64** (open, part): photo folders follow the module file; only the Device Pack export file name still goes by the device's own name (see G22).
- **BM41** (planned): bigger page; open questions on size and converting the user's maps (S68, Q14).
- **SH1** (planned): Draw → Plus shape with snap points.
- **SH2** (planned): Draw → Radial ring with snap points.
- **SH3** (planned): Draw → Named Card shape.
- **AU-119** (open, tests): window smokes for the Button Map wait fixed times.
- **AU-56** (on hold): Button Map contents cut off at 200% on a small screen.

## 11. Size and test coverage

**Size, roughly:** about 21,000 lines. Python: `hardware_profile.py` 2656 (Button Map part about 1,100), `button_map_labels.py` 178, `button_map_options.py` 391. QML: window 4081, editor 1665, face 913, `Rig*.qml` about 3,900, Print & Export 525, card 93. JavaScript: 27 `rig_*.js` files, about 9,700.

**Covered well:** the editor's drawing and selection behaviour (31 golden scenarios plus `test_rig_shapes.py`); print area, Print & Export window and export sizes; templates, recovery store, copy-layout listing, photo pose and look, recent colours, options and styles; labels text and mode inheritance; window devices (unplugged, reconnect, edit survives, entering Edit is not a change); tool rows and Options pane; Save keeps other keys; Cancel puts the photo back; damaged file refused; twin and renamed sticks.

**Thin or untested paths:**
- Golden tests drive the editor alone, not the window: Save, Cancel, the leave prompts, recovery offer, copy layout and templates through the window are covered only by a few smokes.
- Nothing tests that print area, guides or grid changes during an edit are or are not taken back by Cancel (G1).
- Nothing tests History entries from Choose Photo / Clear Photo / Cancel (G2).
- Nothing tests the Button Map open while History Restore, Device Pack import or Module Setup changes the same file (G6), or Delete Device during an edit (G7).
- Apply Template / Copy from Device onto a device with different controls (G21); mirrored copy undo count (AU-27).
- `clearImage` failure path (file locked), `imagesFolderUrl` when the install folder is read-only, `colorAt` beyond one test, `profilePhotoUrl` stock branches.
- `printImage` (the real printer dialog can't run off-screen); only `print_image` drawing is tested.
- Pool rows for an unplugged device (`chips_for_guid` falling back to profile ids) and the per-press cost (G11).
- `savedLayouts` with a damaged other-device file (skipped quietly; no test).

## 12. Review (user, 2026-10-06)

Approved by the user as recommended (2026-10-06, blanket approval of the remaining pages): every [code only] statement in section 8 is confirmed, except where a question's recommendation changes it; every question in section 9 is decided as its **Recommend** says. Where a recommendation and a section 8 statement disagree, the recommendation wins.

| Q | Decision |
|---|---|
| All | As recommended in section 9 |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.
