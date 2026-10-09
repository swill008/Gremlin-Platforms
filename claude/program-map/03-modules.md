# Input and output modules

Mapped read-only against the code on 6 Oct 2026 (after 4f6bdfa4). Line numbers drift; re-check them before a step starts. "CONFIRMED" below means seen in the code (not run in the app) unless a test is named.

## 1. Purpose

Every device has a module file that says which of its controls the program may use (its claims), their friendly names, its picture, calibration and page Appearance. Input modules decide what reaches your actions; output modules (one per vJoy) decide what reaches the driver; the Xbox output passes everything. This subsystem is also Home (the device cards), Module Setup, Calibration, the Output View, Delete Device, Start Fresh and module import.

## 2. Files

**Core (gremlin/modules/)**
- `gremlin/modules/__init__.py`: package note naming the layers.
- `gremlin/modules/ids.py`: built-in device ids (Keyboard, OSC, Xbox, Logical Device) and `guid_key` / `stored_guid_key`, the two ways ids are compared and stored.
- `gremlin/modules/claim.py`: what a claim is (`buttons`, `axes`, `hats`, `keys`, `friendly`, `keysChosen`), reading it clean, and the "is this control claimed" checks, including the Keyboard rules.
- `gremlin/modules/registry.py`: reads every `modules\*.json` once (re-read when its time or size changes), classifies input/output, and holds THE file rule `resolve_module_slug`; also `for_device`, vJoy id rules, `_binding_store` (reads the `module-file-bindings` setting).
- `gremlin/modules/module_file.py`: safe write (temp file then swap, History hook), `load_for_update` (refuses a damaged file), `start_fresh` (moves a damaged file aside), refused-save message.
- `gremlin/modules/gate.py`: `should_forward`, the one rule for whether a hardware event may enter the wire; helpers for the card "last:" line.
- `gremlin/modules/runtime.py`: `InputModuleRuntime` singleton: takes raw stick and key events, passes only claimed ones on (`event`, `key_event`); reloads claims on config, profile and device changes.
- `gremlin/modules/inputs.py`: claimed reads of other inputs for Merge Axis, Dual Axis Deadzone, Condition and the script `joy` / `keyboard` objects (unclaimed reads neutral).
- `gremlin/modules/hardware.py`: device info by id for the UI (`device_info`, `device_connected`), so the UI does not call the device library.
- `gremlin/modules/output.py`: the only code that writes to vJoy and ViGEm: claimed vJoy reads and writes, busy-vJoy retry, Xbox pass-through, driver checks, `reset_drivers` at Stop. Caches output claims for 1 s.
- `gremlin/modules/calibration.py`: calibration curves stored in the input module; which connected sticks have one (`_source_modules`); `write_axes`.
- `gremlin/modules/auto_map.py`: input and output module lists for the Auto Mapper; `merge_claim_into_output` ("Also claim the matching outputs").
- `gremlin/modules/wiring.py`: destination labels ("vJoy 3 · Button 5 (Fire)", "(not claimed)"). Wiring is its own subsystem; listed because it reads output claims.

**UI models (gremlin/ui/)**
- `gremlin/ui/module_model.py`: `ModuleListModel` (Home cards: rows, status, counts, last line, Driven by, focus, hide, order, stacks, sizes, compact, split; Output View and Configuration Appearance load/save; Delete Device, Start Fresh, import wrappers), `DriverInputModel` (Module Setup's control list, press-to-claim, Undo/Redo, `saveClaim`), `CardSizes` (Options reset).
- `gremlin/ui/hardware_profile.py` (lines ~275-1181 only; the rest is the Button Map): module path helpers (`_maps_dir`, `_slug`, `guid_for_module`, `module_json_path`), binding store writes, `import_module_file` / `undo_last_import`, `delete_module_file`, `delete_device`, `delete_preview`, deleted devices folder. Also `copyImage` / `keepPhoto` / `profilePhotoUrl` used by Module Setup and the cards.
- `gremlin/ui/module_inputs.py`: `ModuleClaimedInputModel`, the Configuration page's left list (claimed controls only); also used by the Output View.
- `gremlin/ui/module_pairing.py`: vJoy Viewer pair models (source modules with vJoy wires, per-axis/button rows).
- `gremlin/ui/module_calibration.py`: `CalibrationModuleModel`, the Calibration window's device drop-down.
- `gremlin/ui/device.py` (lines 1076-1641 only): `AxisCalibration`, the Calibration window's per-axis model (capture, Undo/Redo, Save, Save All).
- `gremlin/ui/output_modules.py`: Map to vJoy output picker (claimed outputs, "(not claimed)").
- `gremlin/ui/auto_map_modules.py`: Auto Mapper's input/output lists.
- `gremlin/ui/live_input.py`: `DeviceLiveState`, live values for the Output View (reads vJoy through `output.vjoy_state`).

**QML / JS**
- `qml/StatusPage.qml`: Home page: card flow, drag, Shift-select, stacks, empty-space menu, Hidden Cards, Delete Device (3 steps) and Start Fresh dialogs.
- `qml/StatusCard.qml`: one card: photo, name, status, counts, Driven by, last line, Output View button, resize grips, right-click menu.
- `qml/DialogConfigureModule.qml`: Module Setup window (control list, Import Image, Module File dialog with Import / Browse / Open Modules Folder / Delete File, import notice with Undo, Undo/Redo, History, Save).
- `qml/DialogCalibration.qml`: Calibration window.
- `qml/OutputModuleView.qml`: Output View page and its Appearance panel.
- `qml/RunningNote.qml`: "The profile is running..." note shown in Module Setup.
- `qml/Main.qml`: opens the windows (`openConfigureModule` ~387-450, card signal handlers ~1414-1462).
- `qml/main_commands.js`: Tools › Device Setup › Input/Output Module Setup, Calibration, Device Pack; View › Home Layout.
- `qml/help_topics.js`: Help topics "Home", "Input modules", "vJoy output modules", "Xbox output module", "Module files and Device Pack", "Hidden cards", "Calibration", "What is saved where".

**Tests (main ones)**
- `test/unit/test_module_claim.py`, `test_module_ids.py`, `test_module_registry.py`, `test_modules_layer.py`, `test_one_copy_of_each_rule.py`: claim/id/registry basics and layer guards.
- `test_input_module_gate.py`, `test_keyboard_gate.py`, `test_logical_events_pass_gate.py`, `test_raw_input_listeners.py`: the input gate.
- `test_output_layer.py`, `test_vjoy_writers_use_firewall.py`, `test_vjoy_viewer_reads_output_module.py`, `test_xbox_output_module.py`, `test_xbox_pads_told_apart.py`: output modules.
- `test_module_lookup_device_first.py`, `test_twin_devices.py`, `test_audit_devices.py`, `test_audit3_module_files.py`: the file rule, renamed sticks, twins, card order, delete.
- `test_module_file_damage.py`, `test_data_safety.py`, `test_write_less.py`: damaged files, Start Fresh, Delete File copy.
- `test_module_setup_undo.py`, `test_module_setup_unplugged.py`, `test_module_setup_import_notice.py`, `test_audit2_coverage.py`: Module Setup.
- `test_calibration_undo.py`, `test_calibration_unsaved.py`, `test_audit2_keyboard_calibration.py`, `test_device_fixes.py`: Calibration, busy vJoy, plug-in reload.
- `test_bound_cards.py`, `test_driven_by_follows_edits.py`, `test_status_claim_cache.py`, `test_card_sizes_follow.py`: Home cards.
- `test_output_view_pads.py`, `test_catalog_display.py`, `test_dest_live_guid.py`: Output View / Appearance.
- `test_auto_mapper_claims.py`: Auto Mapper claim merge.

## 3. What it owns

**Files (data folder)**
- `modules\<slug>.json`: one module file per device. Keys this subsystem writes: `kind`, `device`, `direction` (`source`/`dest`), `boundName`, `boundGuidLocal`, `claim`, `image`, `calibration` (per axis id: low, centerLow, centerHigh, high, withCenter), `view` (Output View Appearance), `catalog` (Configuration Appearance), and defaults `space`, `pageW`, `pageH`, `photoWell`, `nodes`. The Button Map also writes this file (`nodes`, `ui`, `image`).
  - Writers in this subsystem: `saveClaim` (module_model.py:2238), `saveViewConfig` (:765), `saveCatalogConfig` (:865), `calibration.write_axes` (calibration.py:145), `auto_map.merge_claim_into_output` (auto_map.py:97), `import_module_file` / `undo_last_import` (hardware_profile.py:691 / :661), `copyImage` via Module Setup's Import Image and Save (hardware_profile.py:2429).
  - Other writers (other subsystems): Button Map save / saveUi / restorePhoto, Device Pack, History Restore.
- `modules\<slug>\photo.*`: the device picture. `modules\library\`: every picture ever chosen (copied by `copyImage`).
- `modules\imported\<slug>.<stamp>.json`: the previous file kept by an import; also the folder the "Import from" list reads.
- `modules\<slug>.json.bad-<date>`: a damaged file moved aside by Start Fresh.
- Deleted devices folder (`util.deleted_devices_dir`, setting `deleted-devices-folder`, default `deleted devices` in the data folder): `<stem> <date time>.json` from Delete File; `<name>\<name>.<stamp>.zip` packs from Delete Device.

**Settings (configuration.json)**
- `global/internal/module-file-bindings`: JSON map, device id (upper case, no dashes) or `name:<slug>` -> module slug. Read by `registry._binding_store`; written only by `hardware_profile._write_bindings` (via `bind_module_file`, `_clear_bindings_to`, `_clear_device_binding`, `_clear_device_binding_keys`, `delete_module_file`, `undo_last_import`).
- `display/status/*` (Home): `hidden-slugs`, `card-order`, `show-stubs` (shown in Options), `compact-view` (shown in Options), `split-mode`, `split-ratio` (old place; now kept by `window_placement` "home"), `card-stacks`, `card-sizes`, `kept-stubs`. Only module_model.py writes them. Options' "Reset all card sizes" goes through `CardSizes`.
- `global/internal/twin-device-names`: written by device start-up (device_initialization), read here indirectly through device names.
- Legacy calibration in program settings (`Configuration().get_calibration`): read only, used until the module file has a curve.

**In memory**
- `registry._cache` (path -> Module, by file time and size).
- `InputModuleRuntime._claims`, `_dest_guids`, `_passthrough` (replaced whole on each reload).
- `output._vjoy_claims`, `_vjoy_names`, `_vjoy_modules`, `_xbox_modules` (1 s cache, under `_lock`); `_blocked`, `_vjoy_failed_at`, `_told_busy` (no lock).
- `hardware_profile._import_undo`: the one Undo record for the last Module Setup import (program-wide, not per device).
- `ModuleListModel`: rows, focus, last line per card, hidden names, claim cache per card (0.5 s), vJoy target cache, output snapshot.
- `DriverInputModel`: the open device's rows, Undo/Redo (100 steps), "not connected" reason.
- `AxisCalibration`: per-axis limits, capture state, Undo/Redo (100 steps, merged within 1 s).

**Who else may change them**: the Button Map, Device Pack and History Restore write module files directly (see system-maps map 1, part B). Nothing else writes the Home settings or the binding store.

## 4. Entry points

**Home page (StatusPage.qml / StatusCard.qml -> Main.qml -> ModuleListModel)**

| User action / trigger | Handler | Function it reaches |
|---|---|---|
| Click a card | `StatusCard` `cardFocused` -> `StatusPage.bindCard` | `model.raiseSlug`, `Main` `_moduleModel.setFocus` |
| Double-click / Enter on a card | `openConfiguration` | `Main.openConfigurationForCard` (Output View for output cards) |
| "Output View" button on an output card | `openOutputView` | `Main.openOutputViewForCard` -> Configuration room in output mode |
| Arrow keys on a card | `StatusCard._focusNextCard` | focus only |
| Shift-click | `shiftToggled` -> `StatusPage.toggleSelect` | page selection only |
| Drag a card | `dragStarted` / `dragMovedAt` / `dropAt` -> `StatusPage.handleDrop` | `model.unstackSlug`, `model.moveSlugBefore` -> `_set_order(_merged_order(...))` |
| Drag a card edge or corner | `sizeChanged` | `model.setPileSize` (divided by UI scale) |
| Menu: Open Configuration / Output View | `MenuModel.action` | as double-click |
| Menu: Button Map | `openButtonMap` | `Main.openButtonMapForCard` (Button Map subsystem) |
| Menu: Hide Card | `ignoreDevice` | `Main` -> `model.ignoreSlug` |
| Menu: Module Setup… (not Xbox) | `configureModule` | `Main.openConfigureModule(direction, card)` |
| Menu: Auto Mapper (not Keyboard/OSC/Xbox) | `autoMap` | `DialogAutoMapper.qml` with `initialSlug = model.moduleFileFor(...)` |
| Menu: Calibration (not output/Keyboard/OSC) | `openCalibration` | `DialogCalibration.qml` with `initialSlug = model.moduleFileFor(...)` |
| Menu: vJoy Viewer / Xbox Viewer | `openPairing` | `Main.pairingForCard` (viewer subsystem) |
| Menu: Device Information (not Keyboard/OSC/Xbox) | `openDeviceInformation` | `DialogDeviceInformation.qml` |
| Menu: Stack Selected Cards / Unstack / Unstack All | `stackSelectedCards` / `unstackCard` / `unstackAllCards` | `model.stackSelected` / `unstackSlug` / `unstackAll` |
| Menu: Reset Size / Reset All Card Sizes | `resetSize` / `resetAllSizes` | `model.resetCardSize` / `model.resetAllCardSizes` -> `reset_all_card_sizes` |
| Menu: Start Fresh… (only when damaged) | `startFresh` -> `StatusPage.askStartFresh` (confirm) | `model.startFresh` -> `module_file.start_fresh` |
| Menu: Swap Device… (not output/Keyboard/OSC) | `assignHardware` | `DialogSwapDevices.qml` (other subsystem) |
| Menu: Reset Card Layout | `clearSettings` | `model.clearCardSettings` (size + unstack) |
| Menu: Delete Device | `StatusPage.askDelete` -> explain popup -> confirm popup -> `runDelete` | `model.deletePreview`, `model.deleteDevice` -> `hardware_profile.delete_device`; then `Main.closeDeletedDevice` |
| Empty space menu: Unhide All Cards / Hidden Cards row / Reset All Card Sizes / Layout | `StatusPage._emptyMenu` | `model.unignoreAll` / `unignoreSlug` / `resetAllCardSizes` / commands `view.layout.*` -> `setSplitMode` |
| Esc on Home | `StatusPage` Keys | deselect |
| Split divider drag | `_splitView` timer (150 ms) | `model.setSplitRatio` -> `window_placement.save_split` |
| Compact view (View menu / Options) | command | `model.setCompactView` |

**Module Setup (DialogConfigureModule.qml -> DriverInputModel / ModuleListModel)**

| User action / trigger | Handler | Function it reaches |
|---|---|---|
| Card menu or Tools › Device Setup › Input / Output Module Setup | `Main.openConfigureModule` (picks first card of the asked kind; refuses Xbox; closes an open window for another device) | window created with direction, name, guid |
| Window opens | `Component.onCompleted` | `_hw.setDeviceGuid`, `DriverInputModel.loadDevice`, `_hw.profilePhotoUrl` |
| Tick / untick a control | CheckBox `onClicked` | `setClaimed` (Undo step) |
| Type a friendly name | TextField `onEditingFinished` | `setFriendly` (Undo step) |
| Press a control on the stick | `EventListener.joystick_event` (queued, raw) | `DriverInputModel._on_joy` -> `markPressed` (ticks it, lights the row, scrolls) |
| Press a key (Keyboard module) | `EventListener.keyboard_event` (queued, raw) | `_on_key` (adds an unlisted key ticked) -> `markPressed` |
| Undo / Redo buttons, Ctrl+Z / Ctrl+Y | `undoEdit` / `redoEdit` | `DriverInputModel.undo` / `redo` |
| Import Image… | `_imageDialog.onAccepted` | `_hw.copyImage` (writes picture and module file at once) |
| Save Module (or "Save Module and Profile" for an output with a profile file) | `commitModule` | `_hw.keepPhoto`, `saveClaim` -> `bind_module_file`, `configChanged`; for output: `backend.unfinishedActions`, `backend.saveProfile`; `model.notifyClaims`; `backend.noteSave` |
| Cancel / window close with unsaved work | `onClosing` -> `_saveGate.ask` | Save -> `commitModule`; Discard -> close |
| History | button | `DialogHistory.qml` filtered by `moduleFileFor(...).json` |
| Module File button | dialog | `refreshModuleFileLabel` (`moduleFileFor`, `moduleFileExists`, `moduleFileNames`, `foreignModuleFile`) |
| Import from (drop-down of `imported\*.json`) | `_moduleFilePick.onActivated` (asks first when unsaved) | `model.importModuleFile` -> `import_module_file`, then `showImportResult` |
| Browse for File | `_moduleLoadDialog` | `model.importModuleFile` |
| Import notice: Undo / OK | `_importNotice` buttons | `model.undoLastImport` / `model.dropImportUndo` |
| Open Modules Folder | button | `Qt.openUrlExternally(model.mapsFolderUrl())` |
| Delete File | `_deleteGate.confirmThen` | `model.deleteModuleFile` -> `delete_module_file` |
| Stick plugged / unplugged while open | `EventListener.device_change_event` | `DriverInputModel._device_list_changed` (sets / clears the "Plug in" reason, or loads controls) |
| Quit with Module Setup open | `Main` quit check | `hasUnsavedWork()` |

**Calibration (DialogCalibration.qml -> CalibrationModuleModel / AxisCalibration)**

| User action / trigger | Handler | Function it reaches |
|---|---|---|
| Tools › Device Setup › Calibration, or card menu | `openTool` / `Main` | window; `chooseModule(initialSlug)`; `backend.pauseInputHighlighting` |
| Choose input module | ComboBox `onActivated` -> `chooseModule` (asks when unsaved) | `AxisCalibration.moduleSlug` -> `_set_module_slug` |
| Move the stick | `EventListener.joystick_event` (raw) | `_event_callback` (raw and calibrated bars; capture) |
| Calibrate Center / Calibrate Extrema | buttons | `calibrateCenter` / `calibrateExtrema` |
| Type a limit, With center | delegate | `setData` (Undo step, merged within 1 s) |
| Reset | button | `reset` |
| Save (per axis) | button | `save` -> `calibration.write_axis` -> `_saved` -> `EventListener.reload_calibration` |
| Save All | button | `saveAllRefusedReason`, `saveAll` -> `write_axes` |
| Undo / Redo | buttons, shortcuts | `undo` / `redo` (stops a capture) |
| History | button | `DialogHistory.qml` filtered by `<slug>.json` |
| Close / switch with unsaved | `onClosing` / `chooseModule` | `_saveGate` |
| Stick plugged / unplugged | `device_change_event` | `CalibrationModuleModel.reload`, `AxisCalibration._device_list_changed` |

**Output View (OutputModuleView.qml -> ModuleListModel / ModuleClaimedInputModel / DeviceLiveState)**

| User action / trigger | Handler | Function it reaches |
|---|---|---|
| Opens (card double-click / Output View button) | `Component.onCompleted`, `onGuidChanged` | `reloadView` -> `moduleModel.viewConfigJson`, `rebuild` (claimed outputs, or every live control when none) |
| Appearance sections (Screen, Layout, Pads, Meters, Buttons, Colors) | controls | page properties only |
| Save | `saveView` | `moduleModel.saveViewConfig` -> module file `view` |
| Copy from another output | `copyViewFrom` | `otherDestViews`, `viewConfigJson` |
| Reset | `resetView` | defaults |
| Leave with unsaved Appearance | `requestLeave` / `requestClose` | ask |
| Claims saved elsewhere | `onClaimsChanged` | `_claimed.reload`, `rebuild` |
| While running | `DeviceLiveState` 33 ms poll | `output.vjoy_state` |

**Files, Run/Stop, signals, timers**

| Trigger | Where | What it does |
|---|---|---|
| Program start | `ModuleListModel.__init__`, `InputModuleRuntime()` | builds cards; first claims load |
| Any hardware event | `EventListener.joystick_event` / `keyboard_event` -> `InputModuleRuntime._on_hid` / `_on_key` | gate; emits `event` / `key_event` to the profile, viewers, Home last line |
| `signal.configChanged` | runtime `reload`; `ModuleListModel._schedule_refresh` (50 ms) and `_follow_card_sizes`; `ModuleClaimedInputModel.reload`; pairing models `reload` | claims and cards re-read |
| `signal.profileChanged` | runtime `reload`; `ModuleListModel._schedule_reload` (200 ms); `ModuleClaimedInputModel.reload` | |
| `device_change_event` (from a timer thread) | runtime `reload`; `_schedule_reload`; Module Setup / Calibration / Configuration list / pairing | |
| `inputItemChanged`, `actionsChanged`, `logicalDeviceModified` | `_targets_timer` (200 ms) -> `_refresh_targets` | Driven by |
| Run | `code_runner.py:361/406` (InputModuleRuntime), `output.refresh()` (code_runner.py:326) | output claims re-read |
| Stop | `output.reset_drivers()` (code_runner.py:438) | vJoy released, Xbox pads unplugged, blocked-log cleared |
| Calibration saved | `EventListener.reload_calibration` -> `calibration.values_for_device` | new curve used at once |
| Profile load | `profileChanged` | cards reload, Driven by |

## 5. Talks to

| Other subsystem | Calls out (this -> it) | Called by (it -> this) |
|---|---|---|
| Device start-up / device list (`device_initialization`, `event_handler`) | `physical_devices`, `vjoy_devices`, `joystick_devices`, `output_vjoy_devices`, `input_devices`; `EventListener` signals; `reload_calibration` | `event_handler.reload_calibration` -> `calibration.values_for_device`; `device_change_event` -> reloads |
| Device library (dill) | only via `modules/hardware.py` | — |
| vJoy / ViGEm drivers | only via `modules/output.py` (`VJoyProxy`, `XboxProxy`, `vjoy.vjoy`, `vigem.ids`) | — |
| Run lifecycle (`code_runner`) | — | `output.refresh`, `output.reset_drivers`, `InputModuleRuntime().event/key_event` connected at Run |
| Actions (Map to vJoy, Map to Xbox, Merge Axis, Dual Axis Deadzone, Condition, macro) | — | `output.write_vjoy`, `write_xbox`, `vjoy_value`; `inputs.axis_value` etc. |
| Scripts (`user_script.py`) | — | `output.ScriptVJoy`, `inputs.ScriptJoystick`, `ScriptKeyboard` |
| Wiring (`modules/wiring.py`, Configuration page labels, Button Map chips) | — | `output.vjoy_module_name`, `vjoy_allows`, `vjoy_claim`, `xbox_module` |
| Button Map (`hardware_profile.HardwareProfile`) | Module Setup uses `copyImage`, `keepPhoto`, `profilePhotoUrl`, `setDeviceGuid`; cards use `profilePhotoUrl` | Button Map uses `resolve_module_slug`, `module_file`, claims for chips |
| Device Pack (`device_pack.py`) | Delete Device calls `device_pack.assemble` | Device Pack uses `module_json_path`, bindings, `_replace_file` |
| History (`history_modules`, `history_model`) | `module_file.write_text` and `_replace_file` call `note_write`; deletes use `deleting` | Restore writes module files; History windows filtered by `moduleFileFor` |
| Configuration page (`binding_catalog`, `module_inputs`) | — | `ModuleClaimedInputModel`, `catalogConfigJson` / `saveCatalogConfig`, `boundLine` |
| Viewers (`pair_live`, `xbox_viewer`, `live_input`, `module_pairing`) | — | `InputModuleRuntime().event`, `output.vjoy_state`, `xbox_state`, pairing models |
| Auto Mapper (`auto_mapper.py`, `DialogAutoMapper.qml`) | — | `auto_map.input_modules`, `output_modules`, `merge_claim_into_output` |
| Profile (`shared_state.current_profile`) | Driven by reads `profile.inputs`; Delete Device drops inputs and calls `profile.to_xml`; `vjoy_as_input` setting | — |
| Main window / backend | `backend.saveProfile`, `unfinishedActions`, `noteSave`, `profilePath`, `pause/resumeInputHighlighting` | `Main.openConfigureModule`, card signal handlers, `closeDeletedDevice` |
| Settings (`config.Configuration`) | Home keys, binding store, legacy calibration | `configChanged` drives reloads |
| Live debug log (`ui/live_debug.trace`) | `registry.trace` on every module read and save | — |
| Options | — | `CardSizes.resetAll`, `show-stubs`, `compact-view`, deleted devices folder |
| OSC (parked) | `DriverInputModel._load_osc` lists OSC addresses; runtime always passes OSC | — |

## 6. Threads and timers

- No threads are started in this subsystem.
- Events: stick events come from the DILL callback thread and key events from the keyboard hook. `InputModuleRuntime` is a QObject on the main thread, so its `_on_hid` / `_on_key` run there (queued). Module Setup connects raw events with `QueuedConnection` explicitly (module_model.py:1758-1764).
- `device_change_event` is emitted on the "device list update" timer thread (event_handler.py:388-419); every receiver here is a QObject method, so it runs queued on the main thread.
- `output.py` is called from whichever thread runs an action (event thread, macro and timer threads). Its claim cache is under `_lock`; its blocked-log and busy-vJoy state are not.
- Qt timers (main thread): `ModuleListModel._reload_timer` 200 ms single shot; `_refresh_timer` 50 ms single shot; `_targets_timer` 200 ms single shot; `_dest_timer` 50 ms repeating, always on (does nothing while stopped); `StatusPage` split timer 150 ms; `DeviceLiveState` 33 ms timers (Output View).
- Time: `output.py` (`time.monotonic` for the 1 s claim cache and 3 s vJoy retry), `module_model.py:1500` (0.5 s claim cache), `device.py:1242` (1 s Undo merge), `module_file.start_fresh` and `hardware_profile` stamps (`time.strftime`, `datetime.now`). None go through `gremlin.clock` (which has no monotonic clock).

## 7. Rule breaks

**Layer rule**
1. CONFIRMED, allowed by decision: Module Setup (`module_model.py:1757-1763`) and Calibration (`device.py:1106-1108`) listen to raw hardware, skipping the input module. Decision in test-plan Phase 3 ("Configure Input Module, calibration and the axis graph keep raw hardware access"); guarded by `test_raw_input_listeners::test_raw_hardware_listeners_are_only_the_allowed_ones`.
2. SUSPECTED: UI files read the device list directly instead of through `modules/hardware.py`: `module_model.py:1583, 1658, 2078`; `module_pairing.py:150, 155`; `hardware_profile.py:835-836, 979-985`; `calibration.py:14` (core, fine). Whether `device_initialization` counts as "the input side" is undecided.
3. CONFIRMED: core module-file logic lives in a UI file: binding store writes, import, delete, path rules (`hardware_profile.py:296-1180`), and `module_model.py` imports them. The core (`gremlin/modules`) cannot do a delete or an import without the UI package.

**Single owner**
4. CONFIRMED: module file paths are built in many places instead of one owner: `module_model.py:380, 492, 505, 875, 1452, 1505, 1693, 2246, 2290`; `hardware_profile.py:701, 957, 1078-1093, 2439-2456`. (Full list in system-maps map 1.)
5. CONFIRMED: three guid filters for one rule: none (`module_model.py:379, 491, 1451, 1505, 2245` pass the raw id), `guid_for_module` (`hardware_profile.py:300-309, 956`), and `HardwareProfile._guid_for_this_device` (`hardware_profile.py:1744-1761`).
6. CONFIRMED: name-only lookups (no id): `module_exists` (`module_model.py:504-506`), `_refresh_inplace` (`:1343, 1347`), `claimedCount` (`:1303`), `module_pairing.py:32, 39`, `module_inputs.py:147`.
7. CONFIRMED: the card key is `_slug(device name)` (`module_model.py:1432, 1585, 1660`) while the file is `resolve_module_slug`; nothing names this as a separate key (system-maps decision F2).

**Duplicated logic**
8. CONFIRMED: `_clear_device_binding` (`hardware_profile.py:802-814`) and `_clear_device_binding_keys` (`:1060-1072`) are the same function.
9. CONFIRMED: vJoy number from a card name by joining every digit (`module_model.py:265-267, 280-281`), not `registry.vjoy_id_from_name` (first run of digits). "vJoy 1 (2)" reads as 12 here; P1c fixed exactly this elsewhere. Harmless today because vJoy cards are named "vJoy N".
10. CONFIRMED: Xbox output found by `"xbox" in name.lower()` in Driven by (`module_model.py:262, 277`), not `registry.is_gremlin_xbox_name`. Only dest rows are checked, so a real Xbox pad is not affected today.
11. CONFIRMED: Home's last line re-checks the claim (`module_model.py:1489-1491`) after `InputModuleRuntime` already gated the event, with a different empty-claim rule (empty passes here, nothing passes at the gate).
12. CONFIRMED: `DriverInputModel._is_keyboard` / `_is_osc` decide by the name "keyboard" / "osc" as well as the id (`module_model.py:1892-1898`); a physical device named "Keyboard" would be treated as the Keyboard module.

**Thread / time rules**
13. SUSPECTED: `output.py` module state `_blocked`, `_vjoy_failed_at`, `_told_busy` (`output.py:35-40, 120-131, 150-177`) is changed from several threads with no lock. Worst case: a message logged twice.
14. SUSPECTED: `registry._cache` (`registry.py:293, 346-360`) is changed by `modules()` on the main thread and on action threads (via `output._refresh_claims`, which holds `output._lock`, not a registry lock). A "dictionary changed size during iteration" at `registry.py:359` is possible.
15. SUSPECTED (minor): time read with `time.monotonic` directly (`output.py:48, 71, 151, 158`; `module_model.py:1500`; `device.py:1242`) instead of `gremlin.clock`.

**Other**
16. CONFIRMED: dead code: `DriverInputModel._load_xbox_dest` (`module_model.py:2030-2068`) shows claim boxes for the Xbox output, but Main.qml:396 never opens Module Setup for Xbox. If it were reached it would break "Xbox output has no claims". `registry.find` (`registry.py:372`) has no caller outside tests.

## 8. Behaviour spec

### A. Which module file a device uses
- S1. It should use one rule everywhere: the file saved for this device id, then a file bound to this exact device, then the file saved for this device name, then the file named after the device. [test-plan: P3d, AUDIT2-A-FILE-RULE] [help: Module files and Device Pack] [test: test_module_lookup_device_first::test_saved_binding_still_wins]
- S2. A stale device id should never pull in another device's file. [test-plan: P3d] [test: test_module_lookup_device_first::test_stale_id_does_not_pull_in_another_devices_file]
- S3. A renamed stick should keep using its old file everywhere: Module Setup, Button Map, Run, Calibration, Auto Mapper, photo, Delete File, Delete Device, the "not saved yet" label. [tracker: AU-04, AU-109] [test: test_audit3_module_files::test_renamed_sticks_file_counts_as_saved_and_is_the_one_deleted, test_delete_device_removes_a_renamed_sticks_file]
- S4. When no device matches, it should fall back to the file named after the device. [test: test_module_lookup_device_first::test_no_device_match_falls_back_to_the_name]
- S5. Twin sticks should get their own names ("<name> (2)"), kept by device id across sessions and ports; the device the existing file is bound to keeps the plain name. [test-plan: TWIN-DEVICES] [tracker: DEV8, AU-76] [test: test_twin_devices::test_the_second_identical_device_gets_its_own_name, test_the_device_the_file_is_bound_to_keeps_the_plain_name]
- S6. Each twin should have its own file, card, Button Map and calibration; an old shared choice should not hand one twin the other's file. [test: test_twin_devices::test_each_twin_has_its_own_card, test_an_old_shared_choice_doesnt_hand_a_twin_the_other_twins_file, test_audit3_module_files::test_twins_that_both_saved_into_one_file_each_get_their_own]
- S7. One vJoy should never open another vJoy's file; a vJoy with no id is found by "vJoy <n>" and never opens a file bound to another device. [test: test_audit3_module_files::test_one_vjoy_never_opens_another_vjoys_file, test_a_vjoy_with_no_id_does_not_open_a_file_bound_to_another_device]
- S8. Device Pack and Output View should use the same rule. [test: test_audit3_module_files::test_device_pack_and_output_view_use_the_one_rule]
- S9. Every caller should pass the device's name and id and filter a stale id the same way; name-only lookups only for vJoy, Keyboard and OSC. [system-maps: map 1 proposed rules (not yet approved)]
- S10. vJoy and the program's own Xbox modules should always be outputs whatever the file says; a real Xbox pad (Windows' own names) is an input. [tracker: DEV1] [test: test_xbox_pads_told_apart] [test: test_audit_devices::test_an_unplugged_xbox_pad_is_not_the_xbox_output]
- S11. Any other file is an output only when marked dest / target / output. [user confirmed 2026-10-06; was code only]
- S12. Module files should be re-read when their time or size changes, so every reader sees the last save. [user confirmed 2026-10-06; was code only]

### B. Claims and the input gate (Run)
- S13. Only controls an input module claims should reach actions, the viewers and the Auto Mapper; anything not claimed does not exist for the rest of the pipeline. [help: Input modules] [glossary: Claim] [test: test_input_module_gate::test_unclaimed_button_does_not_enter_wire, test_source_claimed_enters_wire]
- S14. A connected stick with no module file should pass nothing. [help: Overview ("An input that is not claimed is ignored")] [code: runtime.py:119-121]
- S15. OSC and Logical Device events should pass without a claim. [test-plan: P0.7] [test: test_input_module_gate::test_osc_passthrough, test_logical_events_pass_gate::test_logical_device_events_reach_the_wire]
- S16. A vJoy's own hardware events should never enter the wire, except a vJoy set to be read back as an input (Profile Settings), which passes unfiltered. [test: test_input_module_gate::test_dest_vjoy_hid_never_enters_wire] [user confirmed 2026-10-06; was code only: the read-back part, runtime.py:98-100]
- S17. Events from an unknown device should be dropped. [test: test_input_module_gate::test_unknown_device_dropped]
- S18. Claims should reload on a settings change, a profile change and a device plugged in or out, so a stick plugged in during a Run gets its claims. [tracker: DEV11] [test: test_device_fixes::test_input_modules_reload_when_a_device_is_plugged_in]
- S19. An old output file bound to a stick should not block the stick at Run, and a stick whose file is an output gets no claim from another file. [test: test_audit3_module_files::test_old_output_file_bound_to_a_stick_does_not_block_it_at_run, test_stick_whose_file_is_an_output_gets_no_claim_from_another_file]
- S20. Run, Module Setup and Calibration should use the same file for a stick. [tracker: AU-22, AU-77] [test: test_audit_devices::test_module_setup_run_and_calibration_use_the_same_file]
- S21. Merge Axis, Dual Axis Deadzone, Condition and the script joy / keyboard objects should read an unclaimed input as neutral (axis centred, button up, hat centred, key up). [test-plan: P3c]
- S22. A damaged module file should block its device's inputs until it is restored, fixed or Start Fresh is chosen. [test-plan: MODULE-FILE-DAMAGE] [code: module_file.refused_message]

### C. Keyboard module
- S23. Keyboard should be an input module: key bindings fire only for claimed keys. [help: Input modules] [test-plan: P3a]
- S24. Never saved: every key should pass and show ticked. Saved with no key ticked: no key passes and none shows ticked. [help: Input modules] [test: test_keyboard_gate::test_no_saved_keyboard_claim_passes_every_key, test_audit_devices::test_keyboard_saved_with_no_keys_passes_none, test_keyboard_setup_shows_a_saved_empty_choice_unticked]
- S25. Older files with bare scan codes should still work. [test: test_keyboard_gate::test_older_files_with_bare_scan_codes_still_work]
- S26. Typing in Windows and games should never be affected. [help: Input modules]
- S27. Pressing a key that is not listed should add it, ticked, as one Undo step. [tracker: AU-24] [test: test_audit_devices::test_keyboard_undo_still_works_after_a_new_key_row]

### D. Output modules
- S28. Each vJoy should have an output module; only outputs it claims are sent. [help: vJoy output modules] [test: test_output_layer::test_claimed_write_reaches_the_driver]
- S29. A write to an unclaimed output, or to one the vJoy device lacks, should be blocked and logged once per Run. [help: Troubleshooting "Nothing reaches vJoy"] [test: test_output_layer::test_unclaimed_write_is_blocked_and_logged_once, test_claimed_output_the_driver_lacks_is_refused]
- S30. A wire to an unclaimed output should be kept and shown "(not claimed)". [help: vJoy output modules] [test-plan: P0.4]
- S31. Reads of unclaimed outputs should be neutral, and viewers should never open a vJoy device themselves. [test: test_output_layer::test_reads_of_unclaimed_outputs_are_neutral, test_unopened_device_gives_nothing]
- S32. The Xbox output should have no claims: every control goes to ViGEm, and an old Xbox claim in a file is ignored. [help: Xbox output module] [user decision: memory "Xbox output has no claims"] [test: test_xbox_output_module::test_every_control_reaches_the_pad, test_an_old_xbox_claim_in_a_file_is_ignored]
- S33. Only the output layer should touch the vJoy and ViGEm drivers. [user decision: layer rule] [test: test_xbox_output_module::test_only_the_output_module_holds_the_xbox_driver, test_vjoy_writers_use_firewall]
- S34. A vJoy held by another program should be told once per Run, retried every 3 s, and its card should say "In use by another program". [tracker: DEV6] [test: test_device_fixes::test_busy_vjoy_is_told_once_and_retried_every_few_seconds, test_the_home_card_says_in_use]
- S35. At Stop every vJoy should be released and every Xbox pad unplugged. [code: output.reset_drivers; Run lifecycle map]
- S36. Output claims saved in Module Setup should take effect at once, also while running (page 06 Q12); today within about 1 second. [user confirmed 2026-10-06; was code only: output._CLAIM_TTL]

### E. Module Setup
- S37. It should open from the card menu (Module Setup…) and Tools › Device Setup › Input / Output Module Setup. [help: Input modules, vJoy output modules] [glossary: Module Setup]
- S38. Tools › Output (Input) Module Setup with a card of the other kind focused should open the first device of the asked kind; an input module is never saved as an output. [tracker: AU-06]
- S39. The Xbox card should have no Module Setup. [help: Home] [tracker: AU-49]
- S40. Opening it for another device while it is open should close the first (asking about unsaved changes) and open a fresh one; the same device just comes to the front. [tracker: A1] [code: Main.qml:407-425]
- S41. For an input module, pressing a control should claim it, light its row and scroll to it; in Output Module Setup, pressing the vJoy's controls ticks them and lights the row. [help: Input modules] [tracker: AU-58] [test-plan: CFGM-02b] [changed 2026-10-07 to follow decision D-03-S41-PRESSES, which wins over the earlier wording "an output module is ticked only"]
- S42. A friendly name should be saved only for a claimed control. [user confirmed 2026-10-06; was code only: module_model.py:2259-2261]
- S43. Undo / Redo should step back through ticks, presses that tick, and names, 100 steps, until another device is opened. [help: Input modules] [test: test_module_setup_undo::test_undo_and_redo_checks_and_names, test_steps_are_capped, test_another_device_starts_without_steps]
- S44. Save Module should write the file the window opened (the device's bound file), record the device id, and bind that file to the device. [tracker: AU-04] [test: test_audit_devices::test_save_writes_to_the_bound_file]
- S45. A physical stick saved here should always be an input module (repairs an old "dest" file). [test: test_audit_devices::test_a_stick_marked_as_an_output_is_repaired_by_saving]
- S46. Save for a device that is not plugged in should be refused: "Plug in <device> to change its setup. Nothing was saved."; when it is plugged back in, Save works with the work on screen kept. Keyboard, OSC and Xbox are never blocked. [test-plan: MODULE-SETUP-UNPLUGGED] [tracker: DEV10] [test: test_module_setup_unplugged::test_unplugged_device_save_is_refused, test_keyboard_and_osc_are_never_blocked]
- S47. Saving an output module should also save the profile when the profile has a file; if the profile has unfinished actions, it is not saved and the window says so. [help: What is saved where] [tracker: A12]
- S48. A save should be checked by reading the file back; a mismatch counts as not saved. [user confirmed 2026-10-06; was code only: module_model.py:2310-2325]
- S49. Cancel, closing the window, or quitting the program with unsaved ticks, names or picture should ask first. [tracker: N4] [code: DialogConfigureModule.qml:201-208]
- S50. Esc and Return should do nothing in this window (sticks send them). [tracker: C19] [code: DialogConfigureModule.qml:97-104]
- S51. Its History button should show only this device's own file (twins share a name). [tracker: AU-107]
- S52. Import Image… should set the device picture. [help: Module files and Device Pack]
- S53. With no controls reported it should say "Press a key to add it." (Keyboard) or point to Windows' game controller settings (stick). [user confirmed 2026-10-06; was code only: DialogConfigureModule.qml:362-364]

### F. Module File dialog: import, Undo Import, Delete File
- S54. It should show the current file name, "(not saved yet)" when it is missing, and a note when the stick still opens a file of another name. [help: Module files and Device Pack] [code: DialogConfigureModule.qml:49-76]
- S55. Import should copy the chosen file into this device's file and leave the chosen file where it is. [help: Module files and Device Pack] [code: hardware_profile.py:691-799]
- S56. Import should keep only the controls this device has (and name the ones left out), keep this device's existing picture, and not change profile wires. [user confirmed 2026-10-06; was code only: hardware_profile.py:458-555, 759-779]
- S57. Import should be refused for: a file that can't be read, a file that is not a module file, a vJoy file onto a stick or a stick file onto a vJoy, a device that isn't connected, and a current file that can't be read. [user confirmed 2026-10-06; was code only: hardware_profile.py:694-736]
- S58. The previous file should be kept in the imported folder. [help: Module files and Device Pack]
- S59. Undo in the import notice should put the previous file back (or remove a new one) and bind again the devices the import unbound; OK drops the Undo. [tracker: AU-21, AU-113] [test: test_audit2_coverage::test_undo_of_a_module_import_binds_the_devices_again, test_module_setup_import_notice::test_an_undo_is_not_red]
- S60. A failed import or Undo should turn the notice red. [tracker: AU-104] [test: test_module_setup_import_notice::test_a_failed_import_is_red, test_a_failed_undo_turns_it_red]
- S61. Importing with unsaved ticks should ask first. [code: DialogConfigureModule.qml:478-484] [test-plan: CFGM-04 (S-31)]
- S62. Delete File should ask first, keep a "module file deleted" autosave in the Device Library (10 S16, S20), and refuse when the autosave can't be kept or another stick uses the file. [changed 2026-10-08 to follow D-10-NO-DELETED-FOLDER] [tracker: A2] [test: test_data_safety::test_deleting_a_module_file_keeps_a_copy, test_no_copy_means_no_delete, test_audit3_module_files::test_a_file_another_stick_uses_is_not_deleted]
- S63. A Delete File that failed should leave no History entry. [test: test_audit3_module_files::test_a_delete_module_file_that_failed_is_no_history_entry]

### G. Damaged files and Start Fresh
- S64. A module file that can't be read (bad JSON, not UTF-8, not an object) should never be treated as empty: every save into it is refused with "Nothing was saved: the module file ... is damaged ...". [test-plan: MODULE-FILE-DAMAGE] [tracker: DEV3] [test: test_module_file_damage::test_damaged_file_is_refused, test_module_setup_save_is_refused, test_layout_saves_are_refused, test_button_map_save_is_refused]
- S65. Its card should read "Module file damaged – inputs blocked" in red and its menu offer Start Fresh…. [tracker: DEV15] [test: test_module_file_damage::test_card_says_damaged_and_start_fresh_keeps_a_copy]
- S66. Start Fresh should ask first, move the file aside as `<name>.json.bad-<date>` (nothing deleted) and let the device be set up again; if the move fails it says so. [test-plan: MODULE-FILE-DAMAGE] [test: test_module_file_damage::test_start_fresh_keeps_the_damaged_file]
- S67. A damaged file should never stop Home, the Run lists or card polling. [test: test_audit3_module_files::test_a_module_file_that_is_not_utf8_doesnt_stop_home]
- S68. Writes should be atomic: a temporary file, then a swap; a failed write leaves the old file whole and no temporary file. [tracker: AU-03, BM12] [test: test_module_file_damage::test_write_is_safe_and_leaves_no_temporary_file]
- S69. Every successful module file write and delete should be one History entry; a failed one none. [help: History] [tracker: AU-94, AU-113]

### H. Home cards: what a card shows
- S70. Home should show one card per physical device, each vJoy device and the Xbox controller. [help: Home]
- S71. Home should always show cards for Keyboard and OSC (not only with a module file or show-stubs on), and a card for the Logical Device when it has a module file. [user confirmed 2026-10-06; was code only: module_model.py:1653-1695] [changed 2026-10-07 to follow decision D-03-S71-ALWAYS]
- S72. A device with no module file should show "No module" (when Options' show-stubs is on); after Delete Device a device still plugged in keeps a card without a module even with it off. [glossary: Internal words ("device without a module")] [tracker: UI12] [code: module_model.py:153-185]
- S73. A card should show its photo (not in compact view), name, status · bus, claimed counts in words ("1 hat", "2 hats"), "Driven by: [...]" on output cards only, and "last: ...". [help: Home] [glossary: Driven by] [tracker: AU-57]
- S74. The last line should show the latest input the input module passed (input cards) or the latest output sent (output cards, only while running), using the friendly name, with the hardware name on hover. [help: Home] [test: test_input_module_gate::test_status_last_hid_only_on_input_cards, test_dest_last_prefers_button_press_then_axis] [user confirmed 2026-10-06; was code only: friendly name and hover]
- S75. Driven by should follow action edits within a moment, show full Xbox names, and drop extra spaces from a module file's name. [tracker: G-DRIVENBY] [test: test_driven_by_follows_edits, test_bound_cards::test_xbox_wire_uses_full_name, test_driven_by_drops_spaces_from_a_module_files_name]
- S76. A card should re-read its module file at most twice a second, and only when the file changed. [test: test_status_claim_cache::test_many_events_read_the_file_once, test_a_newer_save_is_picked_up]
- S77. Each twin card should show its own counts, also after a save elsewhere. [test: test_twin_devices::test_each_twin_has_its_own_card] [system-maps: map 1 part 2 (suspected)]
- S78. Card counts should be the claimed counts. [glossary: Claim] — see Q8: today the code shows the device's own counts when nothing of a kind is claimed.

### I. Home layout
- S79. Double-click or Enter should open Configuration (input) or Output View (output); arrow keys move between cards. [help: Home] [tracker: UI7]
- S80. Right-click should pick the card first; a card in a Shift selection keeps the selection. [help: Home] [tracker: G-RCLICK]
- S81. Dragging should reorder cards; the order persists across restarts; unplugged and hidden cards keep their places; a renamed stick takes its old card's place; a file chosen for a stick does not take another stick's place; a deleted device's place goes. [test-plan: H-04] [tracker: AU-106] [test: test_audit3_module_files::test_a_drag_keeps_hidden_cards_places, test_a_renamed_stick_keeps_its_cards_place, test_a_file_chosen_for_a_stick_does_not_take_another_sticks_place, test_a_deleted_devices_place_in_the_card_order_goes]
- S82. Hide Card should only take the card off Home; Hidden Cards (empty-space menu) lists each by name and unhides it; Unhide All Cards brings them all back. [help: Hidden cards] [glossary: Hide Card / Hidden Cards]
- S83. Cards should resize by edge or corner, kept between 220-720 by 140-520, and the size persists; cards in a stack share a size. [test-plan: H-05] [code: module_model.py:366-370, 1098-1105]
- S84. Shift-click then Stack Selected Cards should stack cards of the same kind (input with input, output with output); Unstack and Unstack All undo it; clicking a stacked card brings it to the top. [help: Home] [code: module_model.py:1131-1215]
- S85. Reset Size, Reset All Card Sizes (also in Options) and Reset Card Layout (size and stacking) should work, and Home follows a reset made in Options at once. [help: Home] [tracker: N9] [test: test_card_sizes_follow::test_home_cards_follow_sizes_reset_elsewhere]
- S86. Compact view and Layout (Single list / Side by side / Stacked) and the divider position should persist. [help: Home] [glossary: Home layout] [test-plan: H-20..22]
- S87. Card order, hiding, sizes and stacks should be kept by the device's own name, not by its file. [system-maps: decision F2 (pending)]

### J. Card menu
- S88. The card menu should leave out what doesn't apply: Xbox has no Module Setup; output, Keyboard and OSC cards have no Calibration; Keyboard, OSC and Xbox have no Auto Mapper or Device Information; output, Keyboard, OSC, Logical Device and Xbox have no Copy Setup to Another Stick…, Swap with Another Stick… or Change vJoy Output… (they replace Swap Device…, which goes); Start Fresh… shows only for a damaged file. [help: Home] [tracker: AU-68, AU-58] [changed 2026-10-08 to follow D-10-COPY, D-10-SWAP, D-10-OUTPUT (Device Library, 10)]
- S89. Calibration and Auto Mapper opened from a card should open on that card's module file. [tracker: C5] [test: test_audit3_module_files::test_calibration_and_auto_mapper_open_on_the_cards_file]

### K. Delete Device
- S90. Delete Device should take three steps: an explanation (saying an autosave is kept in the Device Library, when that trigger is on), a red confirm, then a result. There is no "Save a copy" question. [test-plan: H-19g] [changed 2026-10-08 to follow D-10-DELETE (Device Library, 10)]
- S91. It should keep a "stick deleted" autosave in the Device Library (10 S16-S21) and check it reads back; if it can't, nothing is deleted. [test-plan: H-19g-b] [code: hardware_profile.py:1107-1135] [changed 2026-10-08 to follow D-10-DELETE (Device Library, 10)]
- S92. It should remove the device's actions in every mode, its module file and pictures, its file bindings, and the card's size and stack. [code: StatusPage.qml:401] [test: test_audit3_module_files::test_delete_device_removes_a_renamed_sticks_file]
- S93. For a vJoy or Xbox card it should keep the output module file and remove only actions stored on that device. [user confirmed 2026-10-06; was code only: hardware_profile.py:1148-1151, StatusPage.qml:394-395]
- S94. A file another device uses should stay. "Another device" means one plugged in now, or one the Device Library knows as a separate device (its own record and id); a file choice left by an id that is neither (an old id of the same stick, e.g. a HID Remapper that came back with a new id) does not count, and Delete Device / Delete File clear such stale choices along with the file. [changed 2026-10-09: D-03-STALE-CHOICES] [test: test_audit3_module_files::test_a_file_another_stick_uses_is_not_deleted]
- S94a. Delete Device on Home is one Tools › History entry, "Deleted X", holding its "stick deleted" autosave and the module-file delete; Restore puts both back. [2026-10-09: D-10-ONE-ENTRY-TITLES]
- S95. The profile should be written to disk at once when it has a file; if that fails, the module file and the pack are kept and the user is told to reload the profile. [history-notes: "Delete Device, which saves at once"] [code: hardware_profile.py:1033-1057, 1136-1143]
- S96. A device still plugged in should keep a card without a module; an unplugged one's card and its place in the order go. [code: module_model.py:1431-1444] [test: test_audit3_module_files::test_a_deleted_devices_place_in_the_card_order_goes]
- S97. The deleted device's open windows should close. [test-plan: H-19g]
- S98. Deleted devices are kept in the Device Library; its folder is in the data folder by default and is chosen in Device Library Settings (10 S36-S37), not Options. [test-plan: H-19g-b fix] [changed 2026-10-08 to follow D-10-DELETED (Device Library, 10)]

### L. Calibration
- S99. Calibration should be stored in the device's input module and applied before any action sees the axis. [help: Calibration]
- S100. It should list connected sticks that have an input module (not Keyboard, OSC or outputs); with none it says "No connected input module." [code: calibration.py:54-90] [tracker: AU-58]
- S101. Opened from a card, it should show that device; a device not connected yet is shown when it connects. [help: Calibration] [code: DialogCalibration.qml:69-95, 148-167]
- S102. Calibrate Center and Calibrate Extrema should capture from the first value read, and only one capture runs at a time per axis (another axis can capture at the same time). [tracker: DEV13, N3] [changed 2026-10-07 to follow decision D-03-S102-PERAXIS]
- S103. Saving should be refused when low is not below high, or the center is outside them, with the reason. [tracker: DEV13, AU-99] [test: test_audit2_keyboard_calibration::test_a_center_outside_the_range_is_refused_with_the_reason, test_a_curve_loading_would_drop_is_not_written]
- S104. A hand-edited bad curve in a file should be ignored (the default is used). [tracker: AU-61] [test: test_audit_devices::test_calibration_with_low_above_high_is_not_used]
- S105. Each axis should have its own Save; Save All writes every unsaved axis in one file write; an axis shows "Not saved" until saved, and back at the saved values it is not unsaved. [help: Calibration] [tracker: C15] [test: test_calibration_unsaved::test_back_at_the_saved_values_is_not_unsaved, test_a_changed_limit_is_unsaved]
- S106. Undo / Redo should step back through each axis's changes until another module is chosen; Undo during a capture stops it and its button goes up. [help: Calibration] [tracker: AU-25] [test: test_calibration_undo]
- S107. Leaving, switching module or quitting with unsaved axes should ask first. [help: Calibration] [tracker: N4]
- S108. A saved axis should be used at once, also while running. [user confirmed 2026-10-06; was code only: device.py:1395-1403]
- S109. A stick whose id changed should be found by its name, and saving records the new id; a stick found by id leaves its binding alone. [tracker: DEV9] [test: test_device_fixes::test_calibration_finds_a_stick_with_a_new_id_and_records_it, test_calibration_of_a_stick_found_by_id_leaves_its_binding]
- S110. Twins should each keep their own calibration. [test: test_twin_devices::test_each_twin_keeps_its_own_calibration]
- S111. Calibration kept in the old program settings should be used until the module file has its own. [user confirmed 2026-10-06; was code only: calibration.py:111-135]
- S112. A damaged module file should refuse the save and stay untouched. [test: test_module_file_damage::test_calibration_save_does_not_touch_it]
- S113. Its History button should show only this module's file. [tracker: AU-71, AU-107]
- S114. Input highlighting should pause while Calibration is open and resume when it closes. [tracker: N11] [code: DialogCalibration.qml:131, 138]

### M. Output View
- S115. The Output View should be the read-only page of an output device: what its output module sends, moving only while the profile runs. [glossary: Output View] [help: Home]
- S116. It should show the claimed outputs; with no output module it shows every control of the vJoy, numbered within each kind. [tracker: AU-50] [test: test_audit2_coverage::test_output_view_numbers_buttons_and_hats_within_their_kind]
- S117. Its Appearance (Screen, Layout, Pads, Meters, Buttons, Colors) should be saved in the module file; Copy from another output, Reset, and asking before leaving with unsaved Appearance. [glossary: Appearance] [help: What is saved where] [test-plan: OV-02..12]
- S118. Its header should show "Driven by: [...]". [tracker: G-DRIVENBY]

### N. Auto Mapper (module side)
- S119. The Auto Mapper should list input modules that claim at least one axis, button or hat, one per device (the file the device uses; no file deleted), and one vJoy output module per vJoy. [help: Auto Mapper] [code: auto_map.py:44-94]
- S120. "Also claim the matching outputs" should add the needed claims to the output module, reading the file fresh first and refusing a damaged one. [help: Auto Mapper] [test-plan: MODULE-FILE-DAMAGE] [test: test_auto_mapper_claims]

### O. Other readers of claims
- S121. The Configuration page's list should show only claimed controls the device has, named by their friendly names. [help: Input modules] [code: module_inputs.py:143-171]
- S122. The vJoy Viewer should list devices whose module has vJoy wires and mark an unclaimed destination "(not claimed)". [help: Viewers] [code: module_pairing.py:73-116]

## 9. Questions for the user

- Q1. **Module Setup's running note is wrong.** While running, Module Setup says "Changes here take effect the next time it starts" (RunningNote.qml:18), but a saved claim works at once (runtime reloads on configChanged, runtime.py:74; module_model.py:2327) and output claims within 1 s. Calibration also applies at once. Recommendation: keep the live behaviour and change the note to "Saved changes work at once."
- Q2. **Import Image… in Module Setup saves at once.** It copies the picture and writes the module file's `image` immediately (hardware_profile.py:2429-2465), but Cancel says "the picture on this screen ... will be lost" and nothing puts the old picture back. Recommendation: do as the Button Map does (stash the starting photo, put it back on Cancel).
- Q3. **Every Save Module adds a picture to the library.** Save calls `keepPhoto` with the device's own photo (DialogConfigureModule.qml:122-123), which copies it into `modules\library` under a new name (photo_1, photo_2, ...) each time (hardware_profile.py:1782-1789). It also writes the module file once more before the claim save (two History entries per Save). Recommendation: copy only when the picture changed.
- Q4. **Delete Device saves the whole profile at once.** It writes the profile to disk directly (hardware_profile.py:1045-1049), including any other unsaved edits, and skips the "unfinished actions" check the normal Save has. Device Pack, by contrast, leaves the profile unsaved. Recommendation: remove the device's actions in memory and leave the profile unsaved (the result already says "Save the profile to keep the removal" when it has no file).
- Q5. **Delete Device without "Save a copy" keeps no copy of the module file**, while Delete File always keeps one (hardware_profile.py:875-879 vs 1150-1151). History keeps the JSON text, not the pictures. Recommendation: always keep the JSON copy in deleted devices, like Delete File.
- Q6. **Nothing stops Delete Device, Start Fresh, import or Delete File while running.** Recommendation: allow Module Setup Save (it works live), but refuse Delete Device while running ("Stop first") because it changes the running profile.
- Q7. **The Logical Device card offers things that don't work.** Its menu shows Module Setup (Save is always refused: "Plug in Logical Device", module_model.py:1845-1849), Calibration, Auto Mapper, Device Information and Swap Device. Recommendation: leave these out on the Logical Device card, as on Keyboard and OSC.
- Q8. **Card counts disagree.** At a reload, a module with nothing of a kind claimed shows the device's own count ("32 buttons", module_model.py:1612-1614, 1682-1684); after any setting change the same card shows 0 (module_model.py:1349-1351). Recommendation: always show claimed counts.
- Q9. **Calibration lists every axis of the stick, claimed or not** (device.py:1501), while Help says only claimed controls exist. Recommendation: keep every axis (calibration is about the hardware), and mark unclaimed axes "not claimed".
- Q10. **Stacks forget cards that aren't showing.** Any stack edit rewrites the stacks from the cards on screen (module_model.py:977-991), so an unplugged or hidden card drops out of its stack, unlike card order, which keeps them. Recommendation: keep them, as card order does.
- Q11. **Names.** The glossary says "Module Setup"; the window titles and Tools say "Input Module Setup" / "Output Module Setup" (DialogConfigureModule.qml:91, main_commands.js:76-78), as does Help. Recommendation: keep the two Tools entries (they pick the kind), and add them to the glossary.
- Q12. **Help's Home topic** lists physical, vJoy and Xbox cards only; Home also shows Keyboard, OSC and the Logical Device. Recommendation: add them to Help.
- Q13. **Import into a renamed stick** writes a new file under the stick's new name (hardware_profile.py:700-701); the old bound file stays. Recommendation: import into the file the device uses (system-maps map 1).
- Q14. **Delete File removes only the .json**; the device's picture folder stays (hardware_profile.py:865-899), while Delete Device removes pictures. Recommendation: Delete File keeps the pictures (they come back if the copy is imported); say so in its confirm text.
- Q15. **Auto Mapper "Also claim" when the output file can't be written** (damaged or a write error) carries on as if the outputs were claimed (auto_map.py:130-141), so actions may be made for outputs that stay unclaimed. Recommendation: stop that output and list it as skipped.
- Q16. **Keyboard Module Setup and typing a friendly name.** The keyboard hook is global and Module Setup ticks every key pressed (module_model.py:1991-2028), so typing "Fire" in a name box may tick F, I, R, E. SUSPECTED; needs an off-screen check. Recommendation: ignore key presses while a text box has focus.
- Q17. **Pending decisions from system-maps map 1** that decide parts of this spec: F2 (cards keyed by device name: recommended keep), F3 (Start Fresh gets a History entry: recommended yes), F4 (twins always looked up by id, logged when missing: recommended yes). Recommendation: as in system-maps.
- Q18. **Delete Device of a vJoy card** removes "actions stored on this device" (inputs whose device id is the vJoy's), but keeps the module file and card. Is that what you want from Delete Device on an output card, or should the item be left out there? Recommendation: leave Delete Device out of output cards; output module files are not deleted anyway.

## 10. Known gaps

**Where code differs from the spec or a rule**
1. A stale id is not filtered in `saveClaim`, `startFresh`, `_load_module_doc`, `_module_damage`, `_source_claim` (module_model.py:2245, 1451, 379, 491, 1505), but is filtered for Delete, Device Pack and Output View (`guid_for_module`, hardware_profile.py:956). Save and Start Fresh can reach a different file from Delete. [S9; system-maps map 1]
2. Name-only lookups: `module_exists`, `_refresh_inplace`, `claimedCount`, module_pairing, module_inputs (see 7.6). Twin naming makes a wrong file unlikely; SUSPECTED, no test. [S6, S77]
3. Import writes the own-name file, not the bound file (hardware_profile.py:700-701). [Q13]
4. Start Fresh leaves no History entry (module_file.py:107-113, module_model.py:1456). [S69, Q17]
5. Running note says "next time it starts" but changes are live. [Q1]
6. Module Setup Import Image writes at once; Cancel does not put the picture back. [Q2]
7. Save Module grows `modules\library` by one picture per save and writes the module file twice. [Q3]
8. `_refresh_inplace` (every settings change): sets vJoy status back to "Virtual" over "In use by another program" (module_model.py:1352-1353); does not refresh the damaged flag (a file fixed by History Restore keeps its red status until the next full reload; SUSPECTED); counts differ from `_reload` (Q8).
9. Stacks drop cards not on screen (module_model.py:981-985, 1151-1157). [Q10]
10. Logical Device card menu offers Module Setup (always refused), Calibration, Auto Mapper, Device Information, Swap Device (StatusCard.qml:451-486). [Q7]
11. Delete Device writes the whole profile, skips the unfinished-actions check, no Run check (hardware_profile.py:1033-1057). [Q4, Q6]
12. Delete Device without a pack keeps no copy of the module file (hardware_profile.py:1150-1151). [Q5]
13. Delete File leaves the picture folder (hardware_profile.py:865-899). [Q14]
14. Duplicate `_clear_device_binding` / `_clear_device_binding_keys` (hardware_profile.py:802, 1060).
15. Auto Mapper merge carries on after a refused or failed write (auto_map.py:130-141). [Q15]
16. Dead code: `_load_xbox_dest` (module_model.py:2030) would show Xbox claim boxes if reached; `registry.find` unused outside tests.
17. `copyImage` deletes the old `photo.*` files before it checks whether the module file is damaged (hardware_profile.py:2442-2465): on a damaged file the picture changes but the file does not.
18. Driven by reads a vJoy number by joining all digits (module_model.py:265, 280), a second copy of the vJoy-number rule (7.9).
19. Options text for show-stubs is "Show stub cards for detected hardware with no saved module." (module_model.py:103), against glossary D13 ("device without a module"). SUSPECTED that Options shows this text.
20. `output.py` thread state and `registry._cache` have no lock (7.13, 7.14). SUSPECTED.
21. Keyboard Module Setup may tick keys typed into a name box (Q16). SUSPECTED.
22. OSC (parked, mapped only): Module Setup lists OSC addresses with claim boxes (module_model.py:1900-1931), but Run passes every OSC event without a claim (runtime.py:22-27), so OSC claims do nothing at Run.
23. `calibration._source_modules` skips a second stick on the same file (calibration.py:72-73); only matters for twins from before twin naming.
24. Home `_reload` writes settings while reading (card order at module_model.py:1710-1711, kept stubs at :183); each write is a settings change. It settles after one pass; noted for the Stage 1 rule checks.

**Open tracker items for this subsystem**
- AU-64 (open): what is left: only the Device Pack export file name still goes by the device's own name (photo folders follow the module file); device list cleared and refilled while read (device update runs on a timer thread, event_handler.py:388-419, while Home reads `physical_devices` on the main thread); a failed output-claims refresh blocks vJoy outputs for 1 s. Unverified.
- AU-58 (in progress): only the OSC empty-state text in Module Setup is left (OSC parked).
- AU-56 (on hold): at 200% on a small screen, Save Module and Save All are cut off.
- AU-116 / AU-117 (open, Run lifecycle map): timers and loops that write to vJoy after Stop go around `output.reset_drivers`.
- System-maps map 1 (Module files): not approved; decisions F1-F4 open.

**Things nothing owns**
- The module file store (paths, guid filter, writes, deletes, pictures, bindings): spread over `module_model.py`, `hardware_profile.py`, `device_pack.py`, `calibration.py`, `auto_map.py` (system-maps map 1 proposes `gremlin/modules/store.py`).
- The card key (device's own name slug) has no named owner or function.
- The binding store is read in the core (`registry`) but only written from a UI file (`hardware_profile`).
- The deleted devices folder holds two formats (Delete File's `.json`, Delete Device's `.zip` packs) written by two functions; nothing lists or prunes it.
- The one Module Setup import Undo record is program-wide (`_import_undo`), not tied to a device or window.

## 11. Size and test coverage

**Size (lines, roughly)**
- Core `gremlin/modules/*`: about 2,200 (output.py 585, registry.py 403).
- UI models: module_model.py 2,334; module-file part of hardware_profile.py about 900; device.py calibration part about 570; module_inputs 264; module_pairing 323; output_modules 302; live_input 446; module_calibration 72; auto_map_modules 80. About 5,300.
- QML: StatusPage 1,226; OutputModuleView 1,284; DialogConfigureModule 659; DialogCalibration 573; StatusCard 495; RunningNote 19. About 4,250.
- Total about 11,800 lines in about 25 files.

**Covered by tests** (see section 2 list): the gate and Keyboard rules, output firewall and Xbox pass-through, the file rule (renamed, twins, stale id, vJoy), damaged files and Start Fresh (model level), Module Setup Undo / unplugged / import notice, Calibration Undo / unsaved / bad curves / new id, Delete File copy, Delete Device of a renamed or shared file, card order with hidden / renamed / deleted cards, Driven by, card-size follow, claim cache, Output View numbering.

**Obvious untested paths**
- Stacks: `stackSelected`, `unstackSlug`, `unstackAll`, `raiseSlug` (no unit test found beyond option-text checks), and stacks with hidden or unplugged cards.
- Hide / unhide (`ignoreSlug`, `unignoreSlug`, `unignoreAll`, `hiddenCards`), compact view and split mode setters.
- `_refresh_inplace` status and counts (vJoy "In use" overwrite, damaged flag, count fallback).
- Module Setup Import Image + Cancel; `keepPhoto` on Save (library growth).
- Delete Device without "Save a copy", for a vJoy card, for an unplugged device, while running, and with other unsaved profile edits.
- Start Fresh History entry; Start Fresh through the QML confirm.
- Import refusals (vJoy onto stick, not connected, damaged current file) and import into a renamed stick.
- Logical Device card: Module Setup, Calibration, Auto Mapper from its menu.
- Keyboard Module Setup with typing in a friendly-name box.
- Auto Mapper "Also claim" on a damaged or read-only output file.
- `output.py` and `registry` from several threads at once.
- QML-level journeys (card menu -> window -> save -> card refresh) are mostly checked off-screen by hand, not by tests.

## 12. Review (user, 2026-10-06)

All [code only] statements in section 8 confirmed; S36 now says "at once" (page 06 Q12) and S93 follows Q18. Every question answered as recommended:

| Q | Decision |
|---|---|
| Q1 | Running note changed to "Saved changes work at once."; live behaviour kept |
| Q2 | Import Image works like the Button Map: the old picture is put back on Cancel |
| Q3 | Save Module copies the photo to the library only when it changed (one write, one History entry) |
| Q4 | Delete Device removes the device's actions in memory and leaves the profile unsaved |
| Q5 | Delete Device always keeps a copy of the module file in deleted devices |
| Q6 | Delete Device is refused while running ("Stop first"); Module Setup Save stays allowed |
| Q7 | Logical Device card: no Module Setup, Calibration, Auto Mapper, Device Information or Swap Device |
| Q8 | Cards always show claimed counts |
| Q9 | Calibration lists every axis; unclaimed ones marked "not claimed" |
| Q10 | Stacks keep cards that aren't showing, as card order does |
| Q11 | "Input Module Setup" / "Output Module Setup" kept and added to the glossary |
| Q12 | Help's Home topic lists Keyboard, OSC and Logical Device cards |
| Q13 | Import goes into the file the device uses (map 1) |
| Q14 | Delete File keeps the pictures and says so in its confirm text |
| Q15 | Auto Mapper Also claim: an output file that can't be written is skipped and listed |
| Q16 | Key presses are ignored while a text box has focus (check off-screen first) |
| Q17 | F2 keep card keys by device name; F3 Start Fresh gets a History entry; F4 twins always by id, logged when missing |
| Q18 | Delete Device is left out of output (vJoy, Xbox) cards |
| S41 | 2026-10-07 (D-03-S41-PRESSES): in Output Module Setup, presses still tick the control and light the row |
| S71 | 2026-10-07 (D-03-S71-ALWAYS): Keyboard and OSC cards always show |
| S102 | 2026-10-07 (D-03-S102-PERAXIS): one Calibration capture at a time per axis |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.
