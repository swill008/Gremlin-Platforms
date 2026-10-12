# Wave 2: audit clean-up (2026-10-12, user decisions 10a-18a in claude/todo.md "Planning answers")

Agents (phase 1 verify only, then "go edit"): W2-UI (gremlin/ui), W2-CORE (gremlin core, joystick_gremlin.py, dill), W2-QML (qml, theme), W2-ASSETS (pictures, WiX files, committed log), W2-MAP (program map); then DUP-PATH, DUP-GUID, DUP-PIC (merge risky duplicates, 17a) and OSC-TEST (test stand-in). Brief: scratchpad wave2/brief.md and dup_brief.md (temporary); audit: ../../audits/2026-10-12-code-audit/.

## Removed
- UI Python: 17 hardware_profile aliases, 9 test-only Slots (tests moved to beginEditFor/editActiveFor/peekPackDeviceById/saveAreaAsync/store.remove_unused_pictures), ProfileDeviceListModel, unused roles (actionSequenceCount, deviceIndex, indent), 16 OSC model Slots, osc_feedback_model by-id Slots, ConfigSectionModel.scope, the dead Options row last-keep-after-release, drop_logical_steps, leaves_for_item, listAppearanceChanged, vjoy_status activeCount/pinStamp, device_pack.put_gmap_wires.
- Core: 15 dead groups (util.truncate, drop_unused_actions, vjoy_owned, DILL.initialize_capi, unused Windows constants, store.remove_pictures, OscDevice thin API, code_runner.run_number shim, swap_devices.get_profile_devices, last-mode setting, device_zip put_wires), the close-to-tray carry-over (D-AUDIT-TRAY-CARRY, retires 01 S37 / 09 S68).
- QML: 5 dead components + qml/help_topics.js, 31 dead functions (9 editor forwarder pairs), ~30 dead properties, InputConfiguration inline mode, 2 dead signals, stale TODO(SEL) fallbacks.
- Assets: 140 map_to_vjoy pictures + 2 others, deploy.bat / generate_wix.py / wix_data.p, dill_debug.1.log; gfx/icon_large.png -> test/unit/fixtures/.

## Changed behaviour
- Macro delay: a saved 0.05 s stays 0.05 s (retires 04 S65; user 16a).
- Bulk OSC capture: osc_bulk is plain functions called from OscDeviceManagementModel._on_learned (no import-time patching); a bulk message no longer also runs the normal learned handler (no double commandCaptured).
- One path rule: util.path_key / same_path / is_inside (resolved + normcase) replace 8 private copies; case and slash direction no longer matter (e.g. Recent "forget" now also removes C:\P\X.xml for c:\p\x.xml).

## Merged without behaviour change
- device_zip.guid_text -> braced_guid (store.guid_text keeps the name).
- HardwareProfile.imageAspect / pictureSize read files through store.picture_size (qrc: resources keep a Qt reader).

## Kept on purpose
Old calibration store (03 S111), osc last_sender / find_address / listenForInput (tools/osc_functional_check.py), VJoyStatus.setPinned, useSystemFocusVisuals (Qt Universal focus frame), MenuModel.pick (menu sample test), fsm.py (code_runner virtual buttons), rig_* old-layout readers (07 S54), all HidHide code, device_pack OT-2 picture reader.

## Found, recorded for later
- To-do 113: Options "vjoy-tabs" change may not refresh the tab bar.
- To-do 114: OscDeviceManagementModel.updateInputSettings and the OscAddDialog edit branch are dead.
- Test-only code left: Profile.bind_devices, Library.remove_unused, plugin_manager.create_instance, module_file.start_fresh, Script.get_variable.
