# D-03-DEVICE-IMAGE: agent split (DEVIMG-PLAN, 2026-10-11)

Files the change touches, grouped by owner (one owner per file). Everyone
works to contract.md; A-STORE's functions are the shared contract, so the
others code against the names at once and run their tests once A-STORE
reports (A-STORE is small: expect it first).

| Agent | Files | Job | Why parallel / why one |
|---|---|---|---|
| A-STORE | gremlin/modules/store.py | `DEVICE_IMAGE_KEY`, `device_image_ref`, `device_image_name`, `IMAGE_EXT`, new precedence in `shown_photo_ref`, `named_refs` + image, `set_device_image`, `remove_device_image`; remove `set_device_photo`, `photo_files`, `remove_pictures` (no callers left). Unit tests for the store functions. | Owns the shared contract; nobody else edits store.py. |
| A-HOME | gremlin/ui/module_model.py, qml/StatusCard.qml, qml/StatusPage.qml | `setCardImage` / `removeCardImage` for every input card + Logical Device (by slug -> name, guid), `hasImage` role, menu items on `hasImage`, generic Home Undo image state (replaces `_logical_picture`, `_put_logical_picture`, `import_photo`), `saveClaim(name, direction, image, removeImage)` | Card model and its two QML files share the role/slot contract; separate files from everyone else. saveClaim lives here (same file). |
| A-SETUP | gremlin/ui/hardware_profile.py, qml/DialogConfigureModule.qml | `profilePhotoUrl` precedence (glob fallback goes), `generatedPhotoUrl`, `keepImage` (replaces keepPhoto / copyImage), `commitEditFor` photo branch goes, `peekPackDeviceById` preview, editor Save pops `deviceImage`; Module Setup "Device Image" box: Add Image… / Change Image… / Remove Image, staged remove, saveClaim call with the new arguments | The dialog calls only these slots and `_driver.saveClaim` (A-HOME's signature from the contract). |
| A-HIDHIDE | gremlin/ui/hidhide.py, qml/DialogHardwareHide.qml | `setDeviceImage` via `store.set_device_image` on the linked device; drop the `photos` setting, `_card_photo`, `photoSource`; `_module_photo` with the guid; button state for unlinked rows (Q5) | Own files; only the store contract. |
| A-PACK | gremlin/ui/device_pack.py, gremlin/library_copy.py, gremlin/device_library.py | "Device image" row `in.image` (export list, import list, `_merge_module`, `_write_pictures`), `module_text` "Device image" section, Restore's `everything` adds `in.image`, `_contents` counts the key as Setup; Q1 (Device photo row) if chosen | The three files share the one item id; Copy / Swap get no code (Q2a). |
| A-DOCS | claude/program-map/02, 03, 07, 08, 10 pages + README counts, claude/glossary.md, qml/help/home_devices.js, qml/help/logical_device.js, claude/todo.md | spec_draft.md statements in place (after the user's answers), map sections 2/3/4/5/10/11, glossary row "Device image", Help text for card menu, Module Setup, HidHide | Docs only; no program file. |
| T-E2E | test/unit/test_device_image_e2e.py (new) | Real path, off-screen: Home card menu Add Image… -> picker -> card shows the image; Change; Remove -> card shows the generated picture; Home Undo / Redo of each; Module Setup Add -> Save -> card; Remove -> Save; Discard leaves the folder as it was; editor Save while an image is set keeps it; image set does not re-make device-photo.png (3a). Must fail on the old code. | Test-only, its own file. |
| T-CARRY | test/unit/test_device_image_carry.py (new) | The image travels: History keep + restore, `.gmap` export, Import as new, Import onto existing ticked / unticked, Restore Import, Device Library save + Restore, Copy Setup and Swap leave it with its stick, Delete Device autosave holds it, HidHide button writes the device's image. | Test-only, its own file. |
| T-SWEEP | existing tests (list below) | Update tests that pin "Import Image / Add Image sets the bottom background picture" and the HidHide per-row picture; run them targeted. | Test-only; each file one owner (this agent). |

Left out: no separate agent for device_zip.py, history_model.py,
history_modules.py, library_swap.py, device_photo.py, folders_move.py,
device_library_model.py, WindowDeviceLibrary.qml — they need no change
(they go through `named_refs` / `shown_photo_ref`, verified in contract
sections 0 and 6); T-CARRY proves it. Main.qml, qml/main_commands.js and
joystick_gremlin.py: not touched. Nothing over the 8-10 limit (9 agents).

## Tests T-SWEEP updates (grep 22:40 for set_device_photo, device_photo_ref,
setCardImage, removeCardImage, import_photo, keepPhoto, copyImage,
photo_files, setDevicePhoto, _card_photo, photoSource, Import Image,
stagedPhoto, _logical_picture: 32 files)

Pinning the old behaviour (must change):
- test_planes_store.py: test_set_device_photo_adds_a_bottom_layer_fitted_to_the_frame,
  test_set_device_photo_replaces_the_picture_in_its_place,
  test_set_device_photo_empty_removes_it, test_set_device_photo_turns_an_old_map_into_layers
  (function goes: delete), test_module_setup_import_image_sets_the_bottom_picture
  (-> sets `deviceImage`, nodes unchanged)
- test_planes_carry.py: test_add_image_on_the_logical_device_card_sets_the_bottom_background_picture
  (-> sets `deviceImage`), test_the_photo_tick_takes_the_packs_photo_where_it_was_shown,
  test_the_map_tick_takes_the_packs_background_and_keeps_this_photo (only if Q1a)
- test_ld_card_image.py (5 tests), test_ld_card_image_carry.py (7), test_ld_card_image_e2e.py,
  test_ld_card_image_menu.py (2: menu now on every input card)
- test_module_setup_photo_edit.py (2), test_device_folders_setup_ui.py::test_import_image_lands_in_the_device_pictures
- test_device_photo_carry.py::test_module_setup_save_with_import_image_makes_the_picture,
  ::test_the_logical_device_cards_add_image_makes_and_remove_image_removes_it
  (an image no longer changes the background: nothing made)
- test_device_photo_shown.py: add the image-first case (or T-E2E does)
Mention only (check, change if they assert the old wording / API):
b1_home_smoke.py, stage1_device_mapping_editor_smoke.py, test_audit3_module_files.py,
test_audit3_screens.py, test_batch1_module_pages.py, test_batch2_B6.py,
test_batch3_C5.py, test_catalog_display.py, test_cleanup_batch_a.py,
test_data_safety.py, test_device_library_LW_swap.py,
test_device_mapping_editor_device_folders.py, test_device_mapping_editor_save_keeps.py,
test_device_zip.py, test_final_03.py, test_ld_restore_builtin.py,
test_lib_restore_builtin_e2e.py, test_library_device_folders.py,
test_planes_once.py, test_planes_paths.py, test_planes_window.py,
test_stage1_modules.py, test/journeys/_harness.py.

## Effort (claude/timings.md rules of thumb, 2026-10-09)

- Each agent: 3-8 min (timings.md: agent fix / feature / docs); the batch of
  9 parallel agents ~10 min (same row). T-SWEEP has ~14 files to change:
  upper end, quote 8 min.
- End to end: agents ~10 + lead checks and map ~5 + full run ~5 + commit ~2
  + CI ~10 (background) = about 32 min (timings.md: "End to end, a batch is").
- Q1a adds about 3-8 min inside A-PACK and T-SWEEP (agent fix), not a new agent.
