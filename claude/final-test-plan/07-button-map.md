# Final test plan: Button Map (07)

Spec: `claude/program-map/07-button-map.md` (section 8, decided by section 12:
every Q as recommended). New tests: `test/unit/test_final_07.py`, driving the
window through `test/unit/final_07_smoke.py` (program off-screen, own process
and user folder) and the owner modules for S15 and S23.

Short names used below:
- `stage1` = `test/unit/test_stage1_button_map.py` (window smoke `stage1_button_map_smoke.py`)
- `devices` = `test/unit/test_button_map_devices.py`
- `window` = `test/unit/test_button_map_window.py::test_window_and_dialogs_open_cleanly` (key named)
- `golden[x]` = `test/unit/test_rig_editor_golden.py::test_editor_matches_golden[x]` (scenario x in `rig_editor_harness.py`)
- `final` = `test/unit/test_final_07.py`

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | One window from card menu, toolbar, Tools; another device reuses it | final::test_one_window_for_every_device_and_the_blank_page | new |
| S2 | No device: "Choose a device from the File menu."; no file written | final::test_the_blank_page_says_choose_a_device_and_writes_nothing | new |
| S3 | File → Device with a tick; switching asks when dirty; Cancel stays | devices::test_device_menu_stays_during_an_edit; test_audit3_screens.py::test_button_map_recovery_offer_and_device_switch. Hands-on: edit, move a chip, File → Device → another, Cancel: same device, still editing; the tick is on the shown device | covered + hands-on |
| S4 | No vJoy / Xbox outputs in File → Device | final::test_the_device_menu_lists_no_outputs | new |
| S5 | Unplugged: "Connect <name>…"; loads when connected | devices::test_unplugged_stick_shows_no_map, ::test_map_loads_when_the_stick_connects | covered |
| S6 | Unplugged stick still exports | devices::test_unplugged_stick_still_exports | covered |
| S7 | Outputs, Keyboard, Logical Device, OSC without a stick | devices::test_outputs_and_built_in_devices_need_no_stick | covered |
| S8 | Edit survives unplug, with the note | devices::test_an_edit_survives_device_changes | covered |
| S9 | Second twin opens its own file | test_twin_devices.py::test_the_button_map_of_the_second_twin_opens_its_own_file | covered |
| S10 | Renamed stick keeps its photo | test_audit3_module_files.py::test_renamed_sticks_photo_goes_with_the_file_its_button_map_opens | covered |
| S11 | No photo for a device without one; never another's or a stock photo | final::test_a_device_without_a_photo_shows_none; test_batch3_C5.py::test_a_stock_photo_reference_finds_nothing | new |
| S12 | Damaged file: empty map, Save refused and said | test_module_file_damage.py::test_button_map_save_is_refused; test_stage1_modules.py::test_a_refused_button_map_save_copies_no_picture | covered |
| S13 | Delete Device closes the map | stage1::test_delete_device_mid_edit_closes_without_asking, ::test_delete_device_removes_the_module_file | covered |
| S14 | Press lights a chip (not editing); hover names it; drag pans | golden[hotspots] (pressed). Hands-on: run a profile, press a claimed button: its chip lights; hover a chip: tooltip names the control; drag the map: it pans | covered + hands-on |
| S15 | Presses only from the input module feed | final::test_presses_come_only_from_the_input_module_feed | new |
| S16 | Chip shows where the wire goes, "(not claimed)" | test_wiring_labels.py::test_unclaimed_and_missing_outputs_are_flagged (the label text). Hands-on: wire a button to an unclaimed vJoy button; its chip (Action text) ends "(not claimed)" | covered + hands-on |
| S17 | Never changes actions | Hands-on: open the Configuration page of a mapped button, edit the map (move, rename, delete its chip), Save: the action is unchanged and the profile is not marked unsaved | hands-on |
| S18 | Lines are "leaders", never "wires" | Hands-on: right-click a leader and open the Layers panel of a chip: rows say Leader, nothing says Wire | hands-on |
| S19 | Edit Mapping; entering Edit is no change | devices::test_entering_edit_is_not_a_change; stage1::test_save_writes_reads_back_and_says_so; window (edit-is-clean) | covered |
| S20 | Save writes, reads back, says so; "Not written…" on failure | stage1::test_save_writes_reads_back_and_says_so. Hands-on: make the module file read-only, Save: "Not written. It is still only on this screen." | covered + hands-on |
| S21 | Text being typed is saved | window (save-while-typing, BM15) | covered |
| S22 | Keys it doesn't write are kept | test_button_map_save_keeps.py::test_save_keeps_calibration_and_other_keys | covered |
| S23 | Whole file through a temporary file | final::test_a_save_cut_short_leaves_the_old_file_whole | new |
| S24 | Compared with what was saved after Save | stage1::test_save_writes_reads_back_and_says_so (dirty-after-save); window (clean-after-save) | covered |
| S25 | Cancel asks with changes; Save there saves and leaves Edit | stage1::test_cancel_with_changes_asks_and_discard_keeps_the_file, ::test_save_in_the_cancel_question_saves_and_leaves_edit, ::test_cancel_without_changes_does_not_ask | covered |
| S26 | Cancel/Discard put the starting photo back, no undo left | test_data_safety.py::test_cancel_puts_the_starting_photo_back; test_button_map_save_keeps.py::test_cancel_puts_the_photo_back_through_the_module_file_writer; stage1::test_choose_photo_then_cancel_puts_the_starting_photo_back | covered |
| S27 | Damaged file left alone on Cancel, said | test_button_map_save_keeps.py::test_cancel_leaves_a_damaged_module_file_alone | covered |
| S28 | Close / quit with unsaved edits asks once | stage1::test_closing_with_unsaved_edits_asks_once; test_stage1_app_profile.py::test_restart_quits_the_usual_way_and_a_cancel_clears_it (stage1 smoke part "quit"). Hands-on: edit the map, quit the program: asked once; Discard quits | covered + hands-on |
| S29 | Module file written only on Save | stage1::test_choose_photo_writes_nothing_until_save, ::test_guide_change_makes_no_module_file, ::test_cancel_takes_back_print_area_and_guides; test_batch2_B6.py::test_choose_photo_writes_no_image_into_the_module_file, ::test_a_ui_change_makes_no_module_file | covered |
| S30 | New photo of the same type is a change | test_audit2_button_map.py::test_the_kept_photo_says_a_change_is_unsaved | covered |
| S31 | Nothing left behind on close | test_button_map_lifecycle.py::test_button_map_leaves_nothing_behind | covered |
| S32 | Recovery copy every N s; removed when all undone | stage1::test_recovery_copy_written_removed_when_undone_and_on_cancel; journeys/test_j05_button_map_recovery.py | covered |
| S33 | Never more often than every 10 s | stage1::test_recovery_copies_never_more_often_than_every_10_seconds | covered |
| S34 | Restore / Discard / Not now | stage1::test_recovery_offer_not_now_restore_and_discard; test_audit3_screens.py::test_button_map_recovery_offer_and_device_switch | covered |
| S35 | Offer put off when another device shows | stage1::test_an_open_offer_is_put_off_when_another_device_shows | covered |
| S36 | Crash mid photo change: saved photo back unless a copy waits | window (crash-photo); journeys/test_j05_button_map_recovery.py::test_the_first_run_leaves_a_copy_and_the_new_photo, ::test_the_restart_offers_the_edits | covered |
| S37 | Copy equal to the saved map removed quietly | stage1::test_a_copy_equal_to_the_saved_map_goes_quietly | covered |
| S38 | Damaged / non-map copy is none | test_button_map_recovery.py::test_a_broken_copy_reads_as_none, ::test_rejects_what_is_not_a_layout | covered |
| S39 | Photo menu only while editing | final::test_the_photo_menu_only_while_editing | new |
| S40 | Choose Photo copies in, keeps the old for Cancel | stage1::test_choose_photo_then_cancel_puts_the_starting_photo_back, ::test_choose_photo_then_save_is_one_history_entry | covered |
| S41 | Clear Photo leaves no photo; failure puts it back, "Clear Photo Failed" | stage1::test_clear_photo_then_cancel_brings_it_back_without_history, ::test_clear_photo_failure_keeps_the_photo_and_says_so, ::test_clear_image_fails_while_the_photo_is_open | covered |
| S42 | Move / size 25-400% / offset / turn; Reset Photo keeps the look | test_photo_pose.py::test_defaults_and_clamps; golden[api_sweep] (photo-pose). Hands-on: Adjust Photo…, change look and pose, Reset Photo: pose back, look kept | covered + hands-on |
| S43 | Brightness, Contrast, Greyscale, Fade: saved, live, exports, Undo | test_photo_pose.py::test_look_kept_clamped_and_only_when_changed; test_button_map_photo_look.py (6); golden[photo_look] | covered |
| S44 | Photo hidden / locked from Layers; saved only when on | test_photo_pose.py::test_layers_flags_kept_only_when_on | covered |
| S45 | Pool lists unplaced controls, filter | final::test_the_pool_lists_what_is_not_placed_and_filters | new |
| S46 | Pool from claims, else device, unplugged from profile | stage1::test_pool_takes_claims_first_then_what_the_device_reports, ::test_pool_of_an_unplugged_device_comes_from_the_profile | covered |
| S47 | Chip only: no leader, no hotspot | final::test_chip_only_places_no_leader_and_no_hotspot | new |
| S48 | Chip name on two rows (Shift+Enter) | golden[two_rows] | covered |
| S49 | Delete: one undo step; spine / cell alone | golden[deletes] | covered |
| S50 | Leader ends at a removed chip become free ends in place | final::test_a_leader_end_at_a_removed_chip_stays_where_it_is | new |
| S51 | Drag back to pool removes; locked stay; Undo | golden[to_pool] | covered |
| S52 | Group keeps places; Break Group leaves each chip | golden[group_keeps], golden[break_group] | covered |
| S53 | Delete on an open group's Layers row removes the group | test_button_map_fixes.py::test_deleting_an_open_group_removes_the_group | covered |
| S54 | Stacking kept; old zLayer maps sorted once | test_rig_stacking.py::test_list_order_is_kept, ::test_old_layouts_are_sorted_once_by_layer; golden[layers] | covered |
| S55 | One undo step per command | test_button_map_fixes.py::test_nudges_in_a_row_are_one_step, ::test_hide_selected_is_one_step; golden[live_color] | covered |
| S56 | Undo steps (80) deep; Undo/Redo only while editing | final::test_undo_and_redo_only_while_editing_80_by_default; final::test_undo_goes_back_as_many_steps_as_the_option (xfail FINAL-07-1) | new (bug found) |
| S57 | Undo covers map, photo, Choose/Clear Photo, print area, guides; not grid/view | stage1::test_choose_and_clear_photo_are_undo_steps, ::test_print_area_and_guides_are_undo_steps; golden[photo_look]. Hands-on (B6): Choose Photo then Undo | covered + hands-on |
| S58 | Press to find; unplaced shown in pool; no undo step | golden[find] | covered |
| S59 | Mirror Layout; pictures only with Mirror pictures; Undo | final::test_mirror_layout_flips_pictures_only_when_asked; golden[mirror] | new |
| S60 | Fit to Photo Frame once per edit; Undo makes it available | final::test_fit_to_photo_frame_once_and_undo_makes_it_available | new |
| S61 | Reset Layout asks, clears, Ctrl+Z back | final::test_reset_layout_asks_clears_and_undoes | new |
| S62 | Pictures from Import / Paste / drop, saved beside the file | test_paste_picture.py (3); window (paste-picture, drop-picture); golden[picture]. Hands-on: Import Picture…, Save, reopen: picture there, file in the device folder | covered + hands-on |
| S63 | Drop outside Edit refused with the message | final::test_a_picture_dropped_outside_edit_is_refused | new |
| S64 | Ctrl+V: picture copied after the last chip copy, else chips | window (paste-picture) | covered |
| S65 | Copied chips kept across devices | test_audit3_screens.py::test_button_map_recovery_offer_and_device_switch (carry) | covered |
| S66 | Hidden item not drawn live, not exported | golden[export], golden[hotspots] (live-map-without), golden[layers] | covered |
| S67 | Saved styles and recent colours for every device | test_button_map_colours.py::test_recent_colours_newest_first_once_at_most_ten; test_button_map_options.py::test_saved_styles_save_replace_rename_delete | covered |
| S68 | 32000 x 18000 page, 24000 x 13500 frame | test_batch3_C5.py::test_save_stamps_the_one_page_size | covered |
| S69 | Files without a frame value opened as they are, not written back | window (plain-file) | covered |
| S70 | Chip Text: Name / Action / both | golden[labels]; test_button_map_labels.py | covered |
| S71 | Text from one mode: chosen, or Follow the Program | final::test_labels_follow_the_program_or_the_chosen_mode. Hands-on: Follow the Program while running: chips change with the running mode | new + hands-on |
| S72 | Parent mode's actions inherited | test_button_map_labels.py::test_a_child_mode_inherits_unless_it_binds_the_control | covered |
| S73 | Follows edits, rename; delete → Follow the Program | test_audit3_modes.py::test_button_map_labels_mode_follows_a_rename. Hands-on: change an action while the map shows Action: the chip follows at once | covered + hands-on |
| S74 | Labels Mode forgotten when the window closes | final::test_the_labels_mode_is_forgotten_when_the_window_closes | new |
| S75 | Copy from Device lists other devices with a map | test_button_map_copy_layout.py::test_lists_other_devices_with_a_layout; stage1::test_copy_lists_other_devices_and_skips_damaged_files, ::test_saved_layouts_skip_damaged_other_files | covered |
| S76 | Copy replaces map, keeps photo, mirror tick, saves nothing | stage1::test_copy_mirror_tick_follows_device_or_template, ::test_copy_onto_fewer_controls_keeps_chips_saves_nothing_and_undoes, ::test_copy_says_how_many_chips_the_device_lacks. Hands-on: copy onto a device with a photo: its photo stays | covered + hands-on |
| S77 | Copy outside Edit starts Edit, Undo brings the old map | window (copy-undo, BM9); stage1 (copy-undo) | covered |
| S78 | Mirrored copy: one Undo | stage1::test_a_mirrored_copy_is_one_undo. Hands-on (B6): mirrored copy then one Ctrl+Z | covered + hands-on |
| S79 | Save as template; asks before replacing; refuses empty | test_button_map_templates.py::test_save_list_and_read_back, ::test_nothing_to_save. Hands-on: Save Layout as Template… with a name already used: asked before replacing | covered + hands-on |
| S80 | Rename, export, import (numbered), delete; asks; says failures | test_button_map_templates.py::test_rename_and_delete, ::test_export_and_import. Hands-on: Manage Templates → Delete asks; Export to a read-only folder says why | covered + hands-on |
| S81 | Template keeps where pictures are | test_batch2_B6.py::test_a_template_says_which_pictures_are_missing | covered |
| S82 | Print & Export settings kept with the map | test_button_map_print_area.py::test_scale_and_saving (saved-print); test_print_export_window.py | covered |
| S83 | 100% = photo's pixels; 10-800%; any screen | test_print_export_window.py::test_every_screen_scale_gives_the_same_picture; test_button_map_print_area.py::test_scale_and_saving | covered |
| S84 | Export longest side capped at 16384 | final::test_an_export_is_capped_at_16384_pixels | new |
| S85 | Only the print area; Alt+drag / Set; paper shape; Clear | test_button_map_print_area.py::test_alt_drag_sets_and_shows_the_area, ::test_an_export_takes_only_the_area, ::test_the_area_keeps_the_papers_shape, ::test_cleared_the_whole_page_again | covered |
| S86 | Frame only while editing | test_button_map_print_area.py::test_the_frame_shows_only_while_editing | covered |
| S87 | No selection, handles, guides, grid, hidden, red frame in exports | golden[export]; test_print_export_window.py::test_exports_are_the_size_given. Hands-on: red debug mode on, export PNG: no red frame | covered + hands-on |
| S88 | PDF on paper inside margins; Freeform 96 px/in | test_button_map_export.py::test_pdf_without_a_paper_is_96_pixels_an_inch, ::test_pdf_on_a_paper_is_that_page | covered |
| S89 | Light background: white page, lightness inverted, photo unchanged | test_print_export_window.py::test_light_is_a_white_page; golden[light_page]; test_rig_shapes.py::test_invert_lightness | covered |
| S90 | Windows printer dialog; Cancel prints nothing; Freeform landscape | test_button_map_export.py::test_print_draws_the_page (drawing only). Hands-on (BMAP2-15): Print…: Windows' dialog; Cancel: nothing printed; Freeform with a wide area: landscape page | hands-on |
| S91 | "Export failed." with file, folder and reason | test_batch2_B6.py::test_a_failed_export_names_the_file_and_why | covered |
| S92 | Print & Export hidden until asked for | test_print_export_window.py::test_it_stays_closed_until_asked_for | covered |
| S93 | Preview drag moves, wheel resizes; not when locked | test_print_export_window.py::test_dragging_and_zooming_the_preview_moves_the_area; test_button_map_print_area.py::test_the_handle_resizes_and_lock_keeps_it | covered |
| S94 | Zoom 50-600%, Ctrl+0/1/2 | final::test_zoom_from_50_to_600_percent_with_its_keys; test_button_map_tool_row.py::test_the_view_zooms_out_to_half; golden[zoom] | new |
| S95 | View / grid kept at once, not in History; guides / area per Q1 | test_history_recording.py::test_the_maps_view_alone_is_not_kept; stage1::test_cancel_takes_back_print_area_and_guides; test_button_map_print_area.py::test_the_area_is_saved_with_the_map | covered |
| S96 | No module file from zoom / grid outside Edit | final::test_a_device_without_a_photo_shows_none (files-same), final::test_the_blank_page_says_choose_a_device_and_writes_nothing; test_batch2_B6.py::test_a_ui_change_makes_no_module_file | covered + new |
| S97 | History lists saves under Button Map, with pictures | test_history_recording.py::test_a_module_save_is_kept_with_its_pictures; stage1::test_choose_photo_then_save_is_one_history_entry, ::test_history_restore_puts_the_file_back | covered |
| S98 | Options for every device, kept at once; last group | test_button_map_options_pane.py::test_a_change_is_kept_and_so_is_the_group; test_button_map_options.py | covered |
| S99 | Tool rows, tabs, pins kept; Reset Tool Rows | test_button_map_tool_row.py::test_rows_and_docks_are_kept_and_reset | covered |
| S100 | Command Palette lists every usable menu command | final::test_the_command_palette_lists_the_usable_menu_commands | new |

## Decisions that state behaviour (section 12)

| Ref | Decision (short) | Check | Status |
|---|---|---|---|
| Q1 | Print area / guides part of the edit; view and grid instant | stage1::test_cancel_takes_back_print_area_and_guides, ::test_print_area_and_guides_are_undo_steps (S95) | covered |
| Q2 | Choose Photo waits for Save; one History entry per Save | stage1::test_choose_photo_writes_nothing_until_save, ::test_the_photo_history_entry_comes_with_save; test_batch2_B6.py::test_choose_photo_writes_no_image_into_the_module_file | covered |
| Q3 | Choose / Clear Photo, print area, guides are undo steps | stage1::test_choose_and_clear_photo_are_undo_steps, ::test_print_area_and_guides_are_undo_steps (S57) | covered |
| Q4 | Clear Photo leaves no photo | stage1::test_clear_photo_then_cancel_brings_it_back_without_history (shown ["", ""]). Hands-on (C5): Clear Photo then Save, reopen: no photo | covered + hands-on |
| Q5 | Module Setup's photo waits for its Save, can be cancelled | test_stage1_modules.py::test_module_setup_cancel_puts_the_old_picture_back | covered |
| Q6 | Outside Edit reload; in Edit warn on Save (Keep mine / Take theirs) | stage1::test_the_map_follows_a_history_restore_outside_edit, ::test_save_does_not_write_over_module_setup_photo, ::test_save_does_not_write_over_a_pack_import. Hands-on (batch 1 GL-071): History Restore during an edit, Save: "Module File Changed" with Keep mine / Take theirs / Cancel | covered + hands-on |
| Q7 | Delete Device mid-edit closes without saving, with a note | stage1::test_delete_device_mid_edit_closes_without_asking | covered |
| Q8 | Chips for missing controls kept; count said | stage1::test_copy_says_how_many_chips_the_device_lacks | covered |
| Q9 | Labels Mode per session only | final::test_the_labels_mode_is_forgotten_when_the_window_closes (S74) | new |
| Q10 | A typed name is always the user's (no EVO R list) | test_batch2_B6.py::test_a_name_equal_to_an_evo_r_part_is_kept; test_batch3_C5.py::test_chip_full_names_have_no_evo_r_part_names, ::test_the_editor_has_no_evo_r_part_list | covered |
| Q11 | Unused pictures removed at Save/Cancel; Delete Device removes recovery and safety copies; library "Remove unused" | test_batch3_C5.py::test_unused_pictures_go_when_an_edit_ends, ::test_the_window_drops_unused_pictures_when_an_edit_ends; test_stage1_modules.py::test_delete_device_removes_its_recovery_and_photo_safety_copies. Hands-on (C5): Import Picture then Cancel: file gone. Library "Remove unused": not built (GL-274 waits for the user) | covered + gap |
| Q12 | No stock photos / legacy maps copy | test_batch3_C5.py::test_a_stock_photo_reference_finds_nothing | covered |
| Q13 | Picture dialogs open in Pictures or last folder | test_batch2_B6.py::test_the_picture_dialogs_open_where_the_last_picture_came_from; stage1::test_picture_folder_is_not_made_in_the_install_folder, ::test_picture_folder_with_a_read_only_install_folder | covered |
| Q14 | One page-size constant, read on load | test_batch3_C5.py::test_save_stamps_the_one_page_size (written). Read on load: not built (GL-270 waits for BM41) | covered + gap |
| Q15 | Copy equal to saved map deleted quietly | = S37 | covered |
| Q16 | Recovery option minimum 10 | stage1::test_recovery_copies_never_more_often_than_every_10_seconds; option min 10 in `button_map_options.py` (shown by test_button_map_options.py::test_every_option_is_registered_and_shown_in_options). Hands-on: Options → Button Map → Seconds between recovery copies won't go below 10 | covered + hands-on |
| Q17 | Glossary row: Button Map Options is a tool-row pane | Hands-on: claude/glossary.md Button Map Options row says it is a pane on the tool row | hands-on |
| Q18 | Print & Export outside Edit writes at once | test_button_map_print_area.py::test_scale_and_saving (saved-print) | covered |
| Q19 | Failed export says file and why | = S91 | covered |

## Batch hands-on checks for this page (claude/catchup-test-plan.md)

- Batch 1 GL-071: the Button Map follows an outside change (History Restore) outside Edit; in Edit, Save asks "Module File Changed" (Keep mine / Take theirs / Cancel).
- Batch 2 B6: a mirrored Copy Button Map, then one Ctrl+Z puts the old map back; Device Pack preview with a large photo stays responsive; Choose Photo then Undo brings the old photo back.
- Batch 3 C5: Clear Photo then Save: no photo after reopening; Import Picture then Cancel: the picture file is gone; export of a damaged device says so.

## Counts

100 statements (S1-S100): covered 77 (14 of them with an extra hands-on step; S96 also gained new checks), new 20 (S71 with a hands-on step), hands-on only 3 (S17, S18, S90), gap 0.
Decisions: 19 rows; Q11 and Q14 each have a part not built (gap, waiting on GL-274 and GL-270/BM41).

## Bugs found

- FINAL-07-1 (S56): Undo steps N lets the user go back only N-1 steps. `VkbRigEditor.qml` `pushHist` caps `hist` (kept states, the start included) at `histCap`, so with 3 there are 3 states and 2 undos. Test: final::test_undo_goes_back_as_many_steps_as_the_option (xfail strict).
