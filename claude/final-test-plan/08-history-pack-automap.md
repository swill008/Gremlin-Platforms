# Final test plan: 08 History, Device Pack and Auto Mapper

Spec: `claude/program-map/08-history-pack-automap.md` (section 8; section 12 decisions win, all Q as recommended; `claude/decisions.md` D-08-*, D-SYS-F1/F3/A3, D-03-Q15, D-05-Q8, D-01-Q7).
New tests: `test/unit/test_final_08.py` (30 tests, all pass; random order checked with `test/run_tests.py --random-order`).
Abbreviations: `stage1` = `test/unit/test_stage1_history_pack.py`, `dpi` = `test/unit/test_device_pack_import.py`, `final` = `test/unit/test_final_08.py`; other files are under `test/unit/`.

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | Changes kept in the history folder's own files, never in the profile | final::test_s1_changes_are_kept_in_the_history_folder_not_the_profile | new |
| S2 | One entry per changed input at Save, "Added/Changed/Removed the actions of ..." | test_history_recording.py::test_a_profile_save_records_each_changed_input | covered |
| S3 | New ids, same actions = no change | test_history_recording.py::test_new_ids_with_the_same_actions_are_no_change | covered |
| S4 | One entry per other changed part (settings, Logical, OSC, modes, scripts) | test_history_recording.py::test_other_parts_and_the_whole_profile | covered |
| S5 | Whole profile kept for the newest 20 saves per profile | final::test_s5_only_the_newest_20_saves_keep_the_whole_profile | new |
| S6 | A save with the same text as the last load/save makes no entry | final::test_s6_a_save_with_the_same_text_makes_no_entry | new |
| S7 | Save As recorded under the new file, old text as before | stage1::test_save_as_is_recorded_under_the_new_file | covered |
| S8 | Module save kept with before/after and its pictures, once by content | test_history_recording.py::test_a_module_save_is_kept_with_its_pictures; test_history_store.py::test_a_picture_is_kept_once_and_put_back; stage1::test_a_saves_before_picture_is_the_picture_it_had | covered |
| S9 | Button Map view-only save not kept | test_history_recording.py::test_the_maps_view_alone_is_not_kept | covered |
| S10 | Button Map-only changes filed under Button Map, others Module files | test_history_recording.py::test_a_module_save_is_kept_with_its_pictures | covered |
| S11 | "Created the module file of X" first, then "Saved X: <words>" | test_stage1_modules.py::test_a_damaged_card_turns_back_after_history_restore; test_history_recording.py::test_a_module_save_is_kept_with_its_pictures | covered |
| S12 | Module-file delete recorded once it went through | test_audit3_saving.py::test_a_delete_that_went_through_is_recorded, ::test_a_delete_that_failed_is_no_history_entry, ::test_undo_import_of_a_locked_new_file_isnt_recorded_as_deleted; test_history_recording.py::test_a_delete_keeps_the_file_and_its_pictures | covered |
| S13 | A failed write leaves no entry | test_audit2_saving.py::test_a_save_that_failed_is_no_history_entry, ::test_an_import_write_that_failed_is_no_history_entry | covered |
| S14 | Files outside the modules folder are not module entries | test_history_recording.py::test_other_files_are_not_kept | covered |
| S15 | Only user-chosen settings recorded | test_history_recording.py::test_settings_the_user_chooses_are_kept | covered |
| S16 | A setting appearing is no change; changes within ~1 s make one entry | final::test_s16_a_setting_appearing_is_not_a_change, final::test_s16_changes_within_a_second_make_one_entry | new |
| S17 | Settings entries titled by Options names, old entries too | test_audit2_options_text.py::test_history_names_settings_as_options_does; test_audit3_saving.py::test_an_old_settings_entry_reads_as_a_new_one, ::test_a_repeated_setting_name_says_its_group | covered |
| S18 | Day and size limits | test_history_store.py::test_old_entries_and_unneeded_pictures_go, ::test_a_file_past_its_size_loses_its_oldest_entries; test_audit_saving.py::test_prune_drops_the_oldest_until_the_file_fits | covered |
| S19 | Clean-up runs at the first entry of a session | final::test_s19_the_clean_up_runs_at_the_first_entry_of_a_session | new |
| S20 | Unneeded kept pictures removed, except this session's | test_audit2_saving.py::test_a_deleted_device_keeps_its_photo_through_the_first_clean_up | covered |
| S21 | Damaged line skipped; next entry on its own line | test_history_store.py::test_a_damaged_line_is_skipped; test_audit_saving.py::test_history_reads_past_a_cut_character; test_batch2_b7.py::test_a_file_rewritten_or_cut_is_read_right | covered |
| S22 | Line/paragraph separator in a name keeps the entry | test_audit2_saving.py::test_a_line_separator_in_a_name_keeps_the_entry | covered |
| S23 | Save only queues; work on the History thread, which ends when idle | test_history_store.py::test_the_writer_ends_by_itself; stage1::test_reading_history_while_the_writer_works_keeps_its_work_on_the_writer; test_batch2_b7.py::test_reading_waits_for_the_writer_instead_of_doing_its_work | covered |
| S24 | Quit writes everything, bounded wait, never stopped by History | test_audit_saving.py::test_history_close_writes_at_once; test_audit3_saving.py::test_quit_goes_on_when_the_history_folder_cant_be_made; test_audit2_coverage.py::test_quit_closes_history_between_the_two_writes | covered |
| S25 | Only one running copy writes (lock file) | test_audit3_startup.py::test_off_screen_a_second_copy_quits_and_closes_nothing | covered |
| S26 | History folder follows Options > Folders | final::test_s26_the_history_folder_follows_the_option | new |
| S27 / Q10 | After a move, old entries stay in the old folder; Options says so | final::test_s27_after_a_move_old_entries_stay_in_the_old_folder; test_batch2_B1.py::test_folder_rows_say_when_they_take_effect | new |
| S28 | Tools > History lists every change, newest first, title, date/time, area | final::test_s28_every_change_newest_first_with_title_date_and_area | new |
| S29 | Show narrows by area; Search in title and subject | stage1::test_show_and_search; test_history_window.py::test_it_lists_the_devices_changes | covered |
| S30 / Q13 | Before/After readable (actions, module parts in words, settings names, profile size) | test_history_window.py::test_a_change_before_and_after; test_batch2_b7.py::test_module_text_reads_like_the_pack_rows; test_batch3_C5.py::test_history_shows_the_device_change_choice_as_options_does | covered |
| S31 / Q15 / Q16 | Editors open History filtered for what they show | stage1::test_the_editors_filters, ::test_button_map_history_is_by_its_own_file_in_every_area, ::test_configuration_row_history_is_for_the_open_profile, ::test_tools_history_opens_on_every_change; test_batch2_b7.py::test_a_profile_filter_matches_the_path_however_written | covered |
| S32 | Filter matches a device id however written | test_history_restore.py::test_filters_match_a_device_id_however_written | covered |
| S33 | "Only ..." line; Show All keeps only the area | test_history_window.py::test_show_all_drops_the_device, ::test_it_lists_the_devices_changes | covered |
| S34 | Tools > History from the menu opens on every change | stage1::test_tools_history_opens_on_every_change | covered |
| S35 | New changes appear when the window comes to the front and with Refresh | final::test_s35_refresh_shows_new_changes (model). Hands-on: open Tools > History, change an option in Options, click back on History: the new "Changed ..." entry is at the top without pressing Refresh | new + hands-on |
| S36 | Empty texts "No saved changes to show." / "Pick a change to see it before and after." | Hands-on: Tools > History, Search "zzzz": the list says "No saved changes to show."; clear Search, pick nothing: the right side says "Pick a change to see it before and after." | hands-on |
| S37 | Picking the same change again reads it again | test_history_window.py::test_picking_the_same_change_again_reads_it_again | covered |
| S38 | Restore Before/After ask first, put back, say what happened | test_history_window.py::test_restore_before_puts_the_file_back. Hands-on: click Restore Before: a confirm asks first; Cancel changes nothing; OK shows the message under the change | covered + hands-on |
| S39 / Q1 | A module-file or settings restore is a new entry (input at next Save; whole profile not recorded) | final::test_s39_a_module_file_restore_is_a_new_entry, final::test_s39_a_settings_restore_is_a_new_entry; help text test_batch3_C1.py::test_history_help_says_when_a_restore_shows | new |
| S40 | Input goes back into the open profile, unsaved; else "Open <profile> first." | test_history_restore.py::test_an_input_goes_back_into_the_open_profile, ::test_an_input_needs_its_profile_open | covered |
| S41 | An input restore that can't be read changes nothing | final::test_s41_an_input_restore_that_cant_be_read_changes_nothing | new |
| S42 | Restore into a deleted mode refused, nothing changed | stage1::test_an_input_restore_into_a_deleted_mode_is_refused | covered |
| S43 / Q14 | Module file put back with pictures into today's folder; missing pictures named; device uses it again | test_history_restore.py::test_a_module_file_and_its_picture_go_back; test_audit2_saving.py::test_restore_names_the_pictures_it_could_not_put_back, ::test_restore_writes_into_the_modules_folder_of_today; test_twin_devices.py::test_a_restored_module_file_is_the_one_its_device_uses_again | covered |
| S44 | Settings back at once; all or nothing; lists as lists; log level / UI scale apply at once | test_history_restore.py::test_settings_go_back; test_audit_saving.py::test_a_list_setting_is_put_back; stage1::test_a_setting_that_no_longer_exists_is_skipped; test_batch2_b7.py::test_restore_applies_logs_and_ui_scale_at_once | covered |
| S45 / Q17 | Whole profile written as a dated copy, never over a file, kept until deleted | test_history_restore.py::test_a_whole_profile_is_written_as_a_copy; test_audit_saving.py::test_restored_profile_copies_never_overwrite; test_batch3_C5.py::test_a_restored_profile_copy_says_where_it_stays | covered |
| S46 | A profile part can't be restored alone; points to the save's entry | final::test_s46_a_part_of_the_profile_cant_be_restored_on_its_own | new |
| S47 | A version no longer kept says so, changes nothing | final::test_s47_a_version_no_longer_kept_says_so | new |
| S48 | "Created" has no Before, "Deleted" no After | final::test_s48_created_has_no_before_and_deleted_no_after. Hands-on: pick a "Created the module file of ..." entry: Restore Before is greyed out | new |
| D-05-Q8 | History Restore of an input closes the action panes first, asking | test_batch2_b7.py::test_an_input_restore_closes_the_action_panes_first | covered |
| S49 | A pack holds module file, pictures, wires with actions, output modules | final::test_s49_s55_a_pack_holds_the_file_pictures_wires_and_outputs | new |
| S50 | Device list: connected, seen by the profile, saved files; opens on the first with a file | final::test_s50_the_device_list_holds_connected_seen_and_saved_devices (list). Hands-on: open Device Pack with a stick that has no module file listed first: the Export tab opens on the first device that has one | new + hands-on |
| S51 / Q19 | No module file: "This device has no module file yet."; damaged says damaged | stage1::test_export_pack_checks_the_place_and_the_name; test_batch3_C5.py::test_export_without_a_module_file_still_says_none_yet, ::test_export_of_a_damaged_module_file_says_so | covered |
| S52 | A damaged module file skipped and logged, window goes on | dpi::test_a_damaged_module_file_is_skipped | covered |
| S53 | Wires in these modes: each mode with actions, all ticked | dpi::test_export_can_take_some_modes; test_device_pack_window.py::test_export_lists_the_modes_and_takes_notes | covered |
| S54 | Made by and Note in the pack and shown on import | test_device_pack_window.py::test_import_shows_who_made_it; dpi::test_the_rows_and_notes | covered |
| S55 | Format 2, program version, date, each mode's parent | final::test_s49_s55_a_pack_holds_the_file_pictures_wires_and_outputs | new |
| S56 | No device binding in the pack | stage1::test_export_pack_checks_the_place_and_the_name | covered |
| S57 | Not inside the modules folder; .zip added | stage1::test_export_pack_checks_the_place_and_the_name | covered |
| S58 | Show Folder opens where the pack was saved | Hands-on: Export a pack, click Show Folder: Explorer opens the folder holding the new zip | hands-on |
| S59 | Sections, all ticked except Map view and Print area | dpi::test_map_settings_rows_import_separately, ::test_the_rows_and_notes | covered |
| S60 | Newer pack refused, "Update the program to import it." | dpi::test_a_newer_pack_is_refused | covered |
| S61 | Missing driver said on open and in the warning, output module's wording | dpi::test_opening_a_pack_says_the_vjoy_driver_is_missing, ::test_the_warning_names_a_vjoy_device_that_is_not_set_up, ::test_the_xbox_driver_is_checked_when_wires_send_to_xbox, ::test_the_pack_and_the_xbox_viewer_say_the_same; test_device_pack_window.py::test_a_missing_driver_is_told_before_import | covered |
| S62 | Put this pack on suggests the device of the pack's name; the text box is written to | final::test_s62_the_pack_suggests_the_device_of_its_name. Hands-on: open a pack, type another device name in Put this pack on, Import: the warning and the import name the typed device | new + hands-on |
| S63 | Stick pack not on a vJoy, vJoy pack not on a stick | final::test_s63_a_stick_pack_cant_go_on_a_vjoy_nor_the_other_way | new |
| S64 | Red Replace/Cancel warning lists everything first | dpi::test_the_warning_says_what_is_replaced; test_device_pack_window.py::test_the_warning_says_what_is_replaced | covered |
| S65 / Q3 | Ticked pieces replace; checked controls are added | final::test_s65_q3_checked_controls_are_added; test_batch3_C5.py::test_checked_controls_are_not_listed_as_replaced | new |
| S66 | Controls the connected device lacks left out of checks and wires, and said | final::test_s66_controls_the_device_doesnt_have_are_left_out_and_said; dpi::test_the_warning_says_what_is_replaced, ::test_a_ticked_mode_is_replaced_and_others_stay | new |
| S67 | Names only for checked controls; unusable curve doesn't replace a good one | final::test_s67_names_are_written_only_for_checked_controls; test_audit3_saving.py::test_a_curve_that_cant_be_used_doesnt_replace_a_good_one | new |
| S68 | Ticked mode replaced, others stay, also after save and reload | dpi::test_a_ticked_mode_is_replaced_and_others_stay, ::test_other_devices_keep_their_actions, ::test_adding_actions_keeps_the_ones_already_there | covered |
| S69 | Only used actions added; replaced ones leave when kept | dpi::test_no_unused_actions_are_saved | covered |
| S70 | Output moved to another vJoy takes its wires | dpi::test_wires_follow_the_output_they_were_put_on | covered |
| S71 | Missing modes under their parent, else Default | dpi::test_modes_keep_their_parent; test_batch2_b7.py::test_a_pack_mode_goes_into_the_look_alike_mode_here | covered |
| S72 | Logical inputs created only when ticked | dpi::test_missing_logical_inputs_can_be_created | covered |
| S73 | Previous file and overwritten picture kept in imported with a dated name | final::test_s73_the_previous_file_and_an_overwritten_picture_are_kept_in_imported | new |
| S74 | Profile changes in memory only | final::test_s74_the_profile_changes_in_memory_only | new |
| S75 | Configuration Appearance, Output View Appearance, photo placement come with it | dpi::test_configuration_appearance_comes_with_the_pack, ::test_the_photo_keeps_its_placement | covered |
| S76 | A write that fails puts back what was written; previous import stays undoable | dpi::test_a_picture_that_cannot_be_written_puts_everything_back, ::test_an_output_picture_that_cannot_be_written_is_reported, ::test_a_failed_import_leaves_the_last_one_undoable, ::test_a_pack_picture_is_written_whole_or_not_at_all; stage1::test_a_pack_with_a_bad_part_changes_nothing | covered |
| S77 | An import that matches or writes nothing keeps Undo | dpi::test_an_import_that_matches_nothing_keeps_the_last_undo; test_audit3_saving.py::test_an_import_that_wrote_nothing_keeps_undo_import; test_device_pack_window.py::test_a_failed_import_keeps_undo_import | covered |
| S78 / Q2 (F1) | Import onto a damaged module file refused, points to Start Fresh | stage1::test_a_pack_import_onto_a_damaged_module_file_is_refused; dpi::test_an_import_onto_a_damaged_module_file_is_refused, ::test_a_damaged_output_module_file_is_left_alone | covered |
| S79 / Q20 (A3) | A wire import failing partway undoes everything | stage1::test_a_wire_import_that_fails_partway_puts_everything_back; test_batch2_b7.py::test_a_wire_import_failing_partway_changes_nothing | covered |
| Q12 (F3) | Start Fresh and a failed import's clean-up are History entries | test_batch1_module_pages.py::test_start_fresh_is_one_history_entry; test_stage1_modules.py::test_start_fresh_is_a_history_entry; dpi::test_the_clean_up_of_a_failed_import_is_in_history | covered |
| Q18 | Pack output modules kept within the vJoy's size | stage1::test_a_pack_output_module_keeps_to_the_vjoys_size; test_batch2_b7.py::test_an_output_module_stays_within_the_vjoy, ::test_a_vjoy_read_back_as_an_input_is_skipped_and_said | covered |
| S80 | Undo Import puts back files, pictures, wires; removes created modes and Logical inputs | dpi::test_undo_import_puts_everything_back; test_audit3_modes.py::test_undo_import_deletes_a_mode_everywhere; test_device_pack_window.py::test_replace_then_undo | covered |
| S81 | Undo offered until the next import or close; then replaced actions leave | final::test_s81_keeping_the_import_ends_undo_and_drops_the_replaced_actions; dpi::test_no_unused_actions_are_saved. Hands-on: Import, close Device Pack, reopen: no Undo Import | new + hands-on |
| S82 / Q6 | Opening another pack ends Undo Import (help says so) | Slot: final::test_s81_... (keepPackImport). Help: test_batch3_C1.py::test_device_pack_and_backup_help. Hands-on: Import a pack, then Choose Zip... another pack: Undo Import is gone | hands-on |
| S83 | Another profile open: files back, wires not, said | stage1::test_undo_import_with_another_profile_open_puts_back_only_the_files | covered |
| S84 | A file Undo can't put back is named | test_audit3_saving.py::test_undo_import_of_a_locked_new_file_isnt_recorded_as_deleted | covered |
| Q5 | Undo asks before putting back a file changed since | stage1::test_undo_import_keeps_a_later_save; test_batch2_b7.py::test_undo_import_asks_before_losing_a_later_save, ::test_undo_import_without_later_saves_does_not_ask | covered |
| Q21 | Undo keeps a created Logical input that now has actions | test_batch2_b7.py::test_undo_import_keeps_a_logical_input_that_has_actions | covered |
| S85 | Module Setup's import Undo puts the file back and binds again | test_audit2_coverage.py::test_undo_of_a_module_import_binds_the_devices_again | covered |
| S86 | Delete Device "Save a copy" writes a full pack per device folder; refused if it can't be written/read back | stage1::test_delete_device_saves_a_pack_that_can_be_imported_back, ::test_delete_device_is_refused_when_the_pack_cant_be_read_back, ::test_delete_device_is_refused_when_the_pack_cant_be_written, ::test_save_a_copy_needs_a_module_file | covered |
| S87 | Deleted devices folder default in data folder, changeable | test_deleted_devices_folder.py::test_option_is_a_folder_picker_like_the_others, ::test_backups_default_to_the_data_folder, ::test_backups_follow_the_chosen_folder | covered |
| S88 | Delete File asks, copies "<name> <date time>.json"; no copy, no delete | test_data_safety.py::test_deleting_a_module_file_keeps_a_copy, ::test_no_copy_means_no_delete; test_batch3_C5.py::test_delete_file_confirm_says_the_pictures_are_kept | covered |
| S89 | A deleted device's pack imports back | stage1::test_delete_device_saves_a_pack_that_can_be_imported_back | covered |
| S90 | Auto Mapper: each claimed control to the same number on vJoy, in the chosen mode; card menu ticks the card | final::test_s90_actions_go_in_the_chosen_mode; test_auto_mapper_claims.py::test_maps_only_to_claimed_outputs_and_reports_the_rest; test_audit3_module_files.py::test_calibration_and_auto_mapper_open_on_the_cards_file | new |
| S91 | Paired by list order; Combine reuses outputs; leftover inputs named | test_auto_mapper_claims.py::test_input_modules_left_without_an_output_are_named; stage1::test_combine_with_more_inputs_than_outputs_uses_each_output_once, ::test_without_combine_the_extra_input_module_is_named | covered |
| S92 | Only claimed outputs the vJoy has; skipped listed by range and reason | test_auto_mapper_claims.py::test_maps_only_to_claimed_outputs_and_reports_the_rest, ::test_ranges; test_batch3_C5.py::test_auto_mapper_reads_vjoy_sizes_through_the_output_module, ::test_auto_mapper_falls_back_to_the_device_list_without_the_driver | covered |
| S93 / Q9 | Also claim: claims first, re-reads, refuses damaged; unclaimable outputs skipped and listed | test_auto_mapper_claims.py::test_claim_option_claims_first; stage1::test_also_claim_with_an_output_file_that_cant_be_written | covered |
| S94 | Overwrite off: used inputs keep actions, used outputs not reused | test_auto_mapper.py::test_get_used_vjoy_inputs_from_profile, ::test_get_used_vjoy_inputs_from_empty_mode; stage1::test_combine_with_more_inputs_than_outputs_uses_each_output_once | covered |
| S95 | Overwrite on: asks, removes every action incl. nested, nothing left behind | test_profile_unused_actions.py::test_auto_mapper_overwrite_leaves_nothing_behind; stage1::test_overwrite_removes_nested_actions_and_leaves_nothing_behind. Hands-on: tick Overwrite used inputs, Create 1:1 Actions: it asks first | covered + hands-on |
| S96 | Overwrite choice remembered | final::test_s96_the_overwrite_choice_is_remembered | new |
| S97 | New actions in memory only; undo = load again without saving | final::test_s97_the_new_actions_are_in_memory_only. Hands-on: the dialog says so under Create 1:1 Actions | new + hands-on |
| S98 / Q7 | Every input (unplugged sticks, nested actions) counts as using a vJoy output | stage1::test_an_output_an_unplugged_stick_uses_is_not_used_again, ::test_an_output_a_nested_action_uses_is_not_used_again; test_batch2_b7.py::test_every_input_and_nested_action_counts_as_used; test_auto_mapper.py::test_get_used_vjoy_inputs_for_disconnected_device_in_profile | covered |
| S99 | Only vJoy outputs; Keyboard, OSC, Xbox cards have no Auto Mapper | final::test_s99_only_vjoy_outputs; test_stage1_modules.py::test_card_menus_leave_out_what_does_not_apply; test_menus.py (kb-module menu) | new |
| S100 / Q4 | Running note in Auto Mapper (and, Q4, Device Pack and History) | test_batch3_C1.py::test_running_note_says_module_setup_changes_work_at_once (the note's texts). Hands-on: Run a profile, open Auto Mapper, Device Pack and Tools > History: each shows "The profile is running. Changes here take effect the next time it starts." | hands-on |
| S101 | Lists follow sticks plugged in/out, keeping ticks | test_device_reconnect.py::test_auto_mapper_keeps_its_ticks | covered |
| S102 | Esc doesn't close Auto Mapper or Device Pack | Hands-on: open each window, press Esc: it stays open (other tool windows close on Esc: test_usability_fixes.py::test_escape_closes_the_tool_windows) | hands-on |
| S103 / Q8 | Result line in glossary words | test_batch3_C5.py::test_auto_mapper_result_says_actions | covered |
| Q11 | Limits checked at start; Options says so | test_batch3_C2.py::test_history_limits_say_they_are_checked_at_start | covered |
| D-05-Q8 | Auto Mapper and Device Pack close the action pane first, asking | Hands-on (batch 2 B7): with an unsaved action pane open, Create 1:1 Actions / Import / Restore ask Discard or Cancel first | hands-on |

## Batch hands-on checks for this page (from `claude/catchup-test-plan.md`)

- B7: large history files (several MB each): Tools > History opens and comes back to the front without freezing.
- B7: with an unsaved action pane, Auto Mapper, Device Pack Import and History Restore ask Discard / Cancel first.
- B7: Import a pack, save the Button Map, then Undo Import: it asks before putting back the changed file.
- B7: History Restore of Diagnostic logs level or UI scale applies at once.
- B6: Device Pack export preview with a large photo stays quick.
- C5: close Device Pack: the `%TEMP%\gremlin-pack-*` folder is gone.
- C5: export a device whose module file is damaged: it says damaged and points to Start Fresh.
- C5: Auto Mapper on a vJoy with sparse axes: only the axes the vJoy has are used; the rest listed.

## Counts

103 statements (S1-S103), plus decisions stating behaviour (Q1-Q21, D-05-Q8) mapped onto them or listed on their own rows.
Status of the 103 S statements: covered 69, new 29 (30 tests), hands-on only 5 (S36, S58, S82, S100, S102), gap 0; several covered/new rows also have a hands-on part (S35, S38, S48, S50, S62, S81, S95, S97).
