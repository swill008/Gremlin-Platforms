## T-E2E (22:00-22:02)
- s11: test_device_photo_e2e.py + device_photo_e2e_smoke.py: real path for S157/S127: editor Save makes the device's background picture (size <=1024, transparent ground, hidden layer and chips left out, key current, profilePhotoUrl shows it); a foreground-only Save makes nothing; no background removes the file. Rerun after host + wiring.
## A-STORE (21:59-22:03)
- s2: test/unit/test_device_photo_store.py.
- s3: store owns the device's background picture rules: DEVICE_PHOTO, DEVICE_PHOTO_SIDE, DEVICE_PHOTO_KEY, RENDER_VERSION, visible_background, background_key, device_photo_path, device_photo_key, device_photo_current, write_device_photo (no History), remove_device_photo, shown_photo_ref; reserved name in put_picture and _free_picture_name; named_refs names the file; copy_pictures / stage_copied leave it out (the destination's maker makes its own).
- s4: store.shown_photo_ref is the entry point for every place that shows the device's photo.
- s5: write_device_photo -> module_file.write_bytes, registry.trace; device_photo_key -> QImageReader.
- s11: test_device_photo_store.py (18) covers S157/S127.
- 08 s3/s11: named_refs carries the file (08 S8, S113).
## T-SWEEP (21:59-22:03)
- tags: 07 S83 -> test_planes_print.py::test_100_percent_is_the_most_detailed_background_picture; S127 -> test_planes_store.py::test_profile_photo_is_the_bottom_background_picture_without_the_background_picture_file and ::test_profile_photo_is_the_background_picture_file_once_made; S157 -> test_planes_store.py::test_named_refs_counts_background_pictures.
## LEAD: history_model.py restore: a missing kept copy of device-photo.png is not reported (it is made again). DialogDeviceMappingEditor.qml: _renderer.sizeOf = _hw.pictureSize (07 S83).
## T-CARRY (21:59-22:04)
- 08 s11 (also 07, 10): test/unit/test_device_photo_carry.py: the device's background picture travels through Export, the Device Library saved-setup photo, Import as new / onto existing (taken or kept with the background tick) and Restore Import, and is made again after a History restore, a Device Library restore, Module Setup's Save with Import Image and the Logical Device card's Add / Remove Image (07 S157, 08 S75 / S111-S113, 10 S11, 03 S52 / S88).
- not covered: Import Image through HardwareProfile.keepPhoto / store.commit_edit.
## A-PYCALLERS (22:00-22:05)
- 07 s3: hardware_profile.profilePhotoUrl shows store.shown_photo_ref (S127, S157) and asks for a new picture when missing/stale/no background left (_want_device_photo).
- 07 s4: HardwareProfile.pictureSize(url) -> {w, h} (S83), cached by path and modification time.
- 07 s5: hardware_profile -> gremlin.ui.device_photo.want.
- 07 s11: test_device_photo_shown.py.
- 08 s3: device_pack._take_device_photo (pack's picture taken only when its key matches the background the import leaves; recorded for Restore Import); Export/Import previews use shown_photo_ref; _zip_pictures skips DEVICE_PHOTO. s11: test_device_photo_shown.py.
- 10 S11: device_library.photo() uses shown_photo_ref; test test_device_photo_shown.py::test_a_saved_setup_shows_its_background_picture.
- s10 gaps: an output module's device-photo.png may be hidden behind the input's (key check prevents a wrong write; untested); Restore Import may list a re-made device-photo.png as changed after import.
## A-MAKER (21:59-22:11)
- s2: gremlin/ui/device_photo.py makes the device's background picture (S157).
- s3: owns when that picture is made again, one job at a time, the 10 s timeout and one retry.
- s4: DevicePhotoMaker.request, check_all, rendered, hostReady; want().
- s5: store (background_key, device_photo_key, write_device_photo, remove_device_photo, notify_module_files), signal.moduleFilesChanged, threads.main_timer, DevicePhotoHost.qml through renderWanted.
- s11: test_device_photo_maker.py.
## LEAD: joystick_gremlin.py context property devicePhotoMaker (+ close on aboutToQuit).
## A-RENDER (21:59-22:13)
- s2: qml/DevicePhotoHost.qml (new): hidden renderer that draws the device's background picture (S157), two grabs (black and white ground) combined by the maker into a transparent picture.
- s3: RigRenderer owns snapshotOf, backgroundArea, detail, the new exportFactor maths (S83) and the two-ground transparent jobs; PrintExportWindow label "Scale (100% = the most detailed background picture's own size)".
- s4: DevicePhotoHost answers devicePhotoMaker.renderWanted.
- s5: DevicePhotoHost -> devicePhotoMaker (rendered, hostReady), HardwareProfile (adjustedPhotoUrl, pictureSize), RigRenderer.
- s11: test_device_photo_render.py + device_photo_render_smoke.py (S157, S83); S83 tag test_device_photo_render.py::test_100_percent_is_the_most_detailed_background_picture.
- s10: lines/paths/text boxes in backgroundArea untested; screen scale above 100% untested.
## LEAD: Main.qml DevicePhotoHost {}.
## HISTFLAKE (22:20-22:26)
- 08 history_model.py row: _thing folds module-file entries by file (module|<deviceId or fileName>), whichever area (Module files / Device Mapping Editor) each save is in (S28). Test test_history_stable_list.py::test_repeated_changes_fold_and_open (own device; fails on old code every time).
- 07 s2 device_photo.py: its start-up and job timers are single-shot QTimers the maker owns, not Run timers: a Run's Stop doesn't touch them.
