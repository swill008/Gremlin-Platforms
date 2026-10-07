# Final test plan: 03 Input and output modules

Spec: `claude/program-map/03-modules.md` (section 8, section 12: every
question decided as recommended) and `claude/decisions.md` (D-03-*,
D-SYS-F2..F4, D-03-STALEID-ONE, D-03-Q8-NOFILE, D-06-Q12). New tests:
`test/unit/test_final_03.py` (F03 below). Agent P03, 2026-10-06.

`U` = `test/unit/`, `J` = `test/journeys/`. S1 = `U/test_stage1_modules.py`,
A3 = `U/test_audit3_module_files.py`, B1M = `U/test_batch1_module_pages.py`.

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | One file rule: id, bound file, saved name, own name | U/test_module_lookup_device_first::test_saved_binding_still_wins; U/test_module_registry::test_resolve_prefers_bound_device | covered |
| S2 | A stale id never pulls in another device's file | U/test_module_lookup_device_first::test_stale_id_does_not_pull_in_another_devices_file | covered |
| S3 | Renamed stick keeps its old file everywhere | A3::test_renamed_sticks_file_counts_as_saved_and_is_the_one_deleted, ::test_delete_device_removes_a_renamed_sticks_file, ::test_renamed_sticks_photo_goes_with_the_file_its_button_map_opens; S1::test_import_into_a_renamed_stick_goes_into_the_file_it_uses | covered |
| S4 | No device match: the file named after the device | U/test_module_lookup_device_first::test_no_device_match_falls_back_to_the_name | covered |
| S5 | Twins get "<name> (2)"; the bound one keeps the plain name | U/test_twin_devices::test_the_second_identical_device_gets_its_own_name, ::test_the_device_the_file_is_bound_to_keeps_the_plain_name | covered |
| S6 | Each twin its own file/card/Button Map/calibration | U/test_twin_devices::test_each_twin_has_its_own_card, ::test_an_old_shared_choice_doesnt_hand_a_twin_the_other_twins_file, ::test_the_button_map_of_the_second_twin_opens_its_own_file; A3::test_twins_that_both_saved_into_one_file_each_get_their_own; J/test_j04_twin_sticks | covered |
| S7 | One vJoy never opens another vJoy's file | A3::test_one_vjoy_never_opens_another_vjoys_file, ::test_a_vjoy_with_no_id_does_not_open_a_file_bound_to_another_device | covered |
| S8 | Device Pack and Output View use the same rule | A3::test_device_pack_and_output_view_use_the_one_rule | covered |
| S9 | Every caller passes name and id, one stale-id filter | B1M::test_a_stale_id_does_not_send_start_fresh_to_another_devices_file, ::test_twin_cards_keep_their_own_counts_and_are_looked_up_by_id, ::test_pairing_and_module_inputs_read_the_twins_own_file; guard U/test_module_store_only | covered |
| S10 | vJoy and own Xbox always outputs; a real Xbox pad is an input | U/test_xbox_pads_told_apart; U/test_audit_devices::test_an_unplugged_xbox_pad_is_not_the_xbox_output; U/test_module_registry::test_direction_rules | covered |
| S11 | Other files are outputs only when marked dest/target/output | U/test_module_registry::test_direction_rules, ::test_scan_classifies_and_finds | covered |
| S12 | Files re-read when time or size changes | U/test_module_registry::test_changed_file_is_read_again; U/test_status_claim_cache::test_a_newer_save_is_picked_up | covered |
| S13 | Only claimed controls reach actions, viewers, Auto Mapper | U/test_input_module_gate::test_unclaimed_button_does_not_enter_wire, ::test_source_claimed_enters_wire; U/test_auto_mapper_claims | covered |
| S14 | Connected stick with no module file passes nothing | F03::test_s14_a_connected_stick_with_no_module_file_passes_nothing | new |
| S15 | OSC and Logical Device pass without a claim | U/test_input_module_gate::test_osc_passthrough; U/test_logical_events_pass_gate::test_logical_device_events_reach_the_wire | covered |
| S16 | vJoy's own events never enter; read-back vJoy passes unfiltered | U/test_input_module_gate::test_dest_vjoy_hid_never_enters_wire; F03::test_s16_a_vjoy_read_back_as_an_input_passes_unfiltered; F03::test_s16_a_vjoy_read_back_passes_whatever_its_output_module_file (xfail FINAL-03-1) | new (bug found) |
| S17 | Unknown device dropped | U/test_input_module_gate::test_unknown_device_dropped | covered |
| S18 | Claims reload on settings, profile, plug in/out | U/test_device_fixes::test_input_modules_reload_when_a_device_is_plugged_in | covered |
| S19 | Old output file bound to a stick doesn't block it | A3::test_old_output_file_bound_to_a_stick_does_not_block_it_at_run, ::test_stick_whose_file_is_an_output_gets_no_claim_from_another_file | covered |
| S20 | Run, Module Setup, Calibration use the same file | U/test_audit_devices::test_module_setup_run_and_calibration_use_the_same_file, ::test_runtime_uses_the_module_setup_file_for_a_stick | covered |
| S21 | Other-input reads of unclaimed inputs are neutral | U/test_input_state_claims::test_unclaimed_inputs_read_neutral, ::test_actions_read_other_inputs_through_the_input_modules, ::test_scripts_get_the_claim_aware_objects | covered |
| S22 | Damaged file blocks the device's inputs until fixed | F03::test_s22_a_damaged_module_file_blocks_its_devices_inputs | new |
| S23 | Keyboard is an input module: only claimed keys fire | U/test_keyboard_gate::test_claimed_key_passes_and_unclaimed_key_does_not, ::test_profile_takes_keyboard_events_from_the_input_runtime | covered |
| S24 | Never saved: every key; saved empty: none | U/test_keyboard_gate::test_no_saved_keyboard_claim_passes_every_key; U/test_audit_devices::test_keyboard_saved_with_no_keys_passes_none, ::test_keyboard_setup_shows_a_saved_empty_choice_unticked | covered |
| S25 | Bare scan codes still work | U/test_keyboard_gate::test_older_files_with_bare_scan_codes_still_work | covered |
| S26 | Typing in Windows and games never affected | Hands-on: Keyboard module claims only F; Run; type in Notepad and a game chat: every key arrives, only F fires its action | hands-on |
| S27 | Unlisted key press adds it ticked, one Undo step | U/test_audit_devices::test_keyboard_undo_still_works_after_a_new_key_row | covered |
| S28 | Each vJoy has an output module; only claimed outputs sent | U/test_output_layer::test_claimed_write_reaches_the_driver, ::test_only_claimed_outputs_are_read | covered |
| S29 | Unclaimed / missing output blocked, logged once per Run | U/test_output_layer::test_unclaimed_write_is_blocked_and_logged_once, ::test_claimed_output_the_driver_lacks_is_refused | covered |
| S30 | Wire to an unclaimed output kept, "(not claimed)" | U/test_output_picker_keeps_wire::test_saved_unclaimed_output_is_kept_and_flagged, ::test_vjoy_without_an_output_module_is_labelled; F03::test_s122_... | covered |
| S31 | Unclaimed reads neutral; viewers never open a vJoy | U/test_output_layer::test_reads_of_unclaimed_outputs_are_neutral, ::test_unopened_device_gives_nothing; U/test_batch2_b3::test_reading_a_vjoy_value_never_opens_the_device | covered |
| S32 | Xbox output has no claims | U/test_xbox_output_module::test_every_control_reaches_the_pad, ::test_an_old_xbox_claim_in_a_file_is_ignored; U/test_batch3_C3a::test_module_setup_shows_no_claim_boxes_for_the_xbox_output | covered |
| S33 | Only the output layer touches vJoy/ViGEm | U/test_xbox_output_module::test_only_the_output_module_holds_the_xbox_driver; U/test_vjoy_writers_use_firewall | covered |
| S34 | Busy vJoy told once, retried every 3 s, card "In use..." | U/test_device_fixes::test_busy_vjoy_is_told_once_and_retried_every_few_seconds, ::test_the_home_card_says_in_use; S1::test_a_busy_vjoy_card_still_says_in_use_after_a_settings_change | covered |
| S35 | Stop releases every vJoy, unplugs every Xbox pad | F03::test_s35_stop_releases_every_vjoy_and_unplugs_every_xbox_pad; U/test_stage1_runtime::test_stop_disconnects_first_and_releases_the_drivers_last | new |
| S36 | Output claims saved take effect at once | S1::test_a_module_save_reaches_the_output_claims_at_once | covered |
| S37 | Opens from card menu and Tools › Device Setup | Hands-on: card menu Module Setup… and Tools › Device Setup › Input / Output Module Setup each open the window | hands-on |
| S38 | Tools entry with other kind focused opens first of the asked kind; input never saved as output | U/test_batch2_b3::test_first_input_card_is_not_the_logical_device; U/test_audit_devices::test_an_input_module_stays_an_input_module. Hands-on: focus vJoy 1, Tools › Input Module Setup opens the first stick | covered + hands-on |
| S39 | Xbox card has no Module Setup | S1::test_card_menus_leave_out_what_does_not_apply | covered |
| S40 | Opening for another device closes the first (asks); same device to front | U/test_batch3_C2::test_module_setup_is_kept_in_the_shared_window_list. Hands-on: Module Setup for stick A, tick a box, open for stick B: asked, then a fresh window; open A twice: comes to front | hands-on |
| S41 | Input press claims, lights, scrolls; output ticked only | U/test_batch3_C3a::test_module_setup_ticks_only_on_hardware_presses; U/test_module_setup_undo. Hands-on (CFGM-02b, needs a stick): press a far button, row ticks, lights and scrolls into view; Output Module Setup text doesn't ask to press | covered + hands-on |
| S42 | Friendly name saved only for a claimed control | F03::test_s42_a_friendly_name_is_saved_only_for_a_claimed_control | new |
| S43 | Undo/Redo 100 steps until another device | U/test_module_setup_undo::test_undo_and_redo_checks_and_names, ::test_steps_are_capped, ::test_another_device_starts_without_steps | covered |
| S44 | Save writes the bound file, records id, binds | U/test_audit_devices::test_save_writes_to_the_bound_file | covered |
| S45 | A stick saved here is always an input | U/test_audit_devices::test_a_stick_marked_as_an_output_is_repaired_by_saving | covered |
| S46 | Unplugged save refused with the text; Keyboard/OSC/Xbox never | U/test_module_setup_unplugged::test_unplugged_device_save_is_refused, ::test_connected_device_saves, ::test_keyboard_and_osc_are_never_blocked | covered |
| S47 | Output save also saves the profile; unfinished actions: not saved, said | Hands-on: profile with a file, Output Module Setup › Save Module and Profile: profile file date changes; add an unfinished action, save again: window says the profile was not saved | hands-on |
| S48 | Save checked by reading back; mismatch = not saved | F03::test_s48_a_save_that_does_not_read_back_counts_as_not_saved | new |
| S49 | Cancel/close/quit with unsaved work asks | U/test_batch2_B1::test_main_window_shell (quit uses hasUnsavedWork). Hands-on: tick a box, Cancel / X / File › Exit: each asks Save / Discard | hands-on |
| S50 | Esc and Return do nothing in Module Setup | Hands-on: open Module Setup, press Esc and Return: window stays, nothing saved | hands-on |
| S51 | History button shows only this device's file | Hands-on: twins; History from the second twin's Module Setup lists only its own file | hands-on |
| S52 | Import Image… sets the picture | B1M::test_module_setup_keeps_the_photo_to_put_back_and_saves_once; S1::test_module_setup_cancel_puts_the_old_picture_back | covered |
| S53 | Empty list: "Press a key to add it." / game controller pointer | Hands-on: Keyboard Module Setup with no keys shows "Press a key to add it."; a stick reporting no controls points to Windows' game controller settings | hands-on |
| S54 | File name, "(not saved yet)", note for another-name file | A3::test_renamed_sticks_file_counts_as_saved_and_is_the_one_deleted. Hands-on: Module File dialog for a stick with no file says "(not saved yet)"; a renamed stick shows the note | covered + hands-on |
| S55 | Import copies into this device's file, chosen file left | F03::test_s55_s56_s58_import_copies_what_the_device_has_and_keeps_the_rest | new |
| S56 | Import keeps only the device's controls (named), its picture, no wire change | F03::test_s55_s56_s58_import_copies_what_the_device_has_and_keeps_the_rest | new |
| S57 | Import refusals | S1::test_import_refusals_change_nothing (6 cases) | covered |
| S58 | Previous file kept in imported | F03::test_s55_s56_s58_import_copies_what_the_device_has_and_keeps_the_rest | new |
| S59 | Undo puts back file and bindings; OK drops Undo | U/test_audit2_coverage::test_undo_of_a_module_import_binds_the_devices_again; U/test_module_setup_import_notice::test_an_undo_is_not_red; S1::test_import_undo_belongs_to_its_device_and_window | covered |
| S60 | Failed import or Undo turns the notice red | U/test_module_setup_import_notice::test_a_failed_import_is_red, ::test_a_failed_undo_turns_it_red | covered |
| S61 | Import with unsaved ticks asks first | Hands-on: tick a box, Module File › Import from: asked before the import | hands-on |
| S62 | Delete File asks, keeps a copy, refuses without copy or when shared | U/test_data_safety::test_deleting_a_module_file_keeps_a_copy, ::test_no_copy_means_no_delete; A3::test_a_file_another_stick_uses_is_not_deleted. Hands-on: the confirm appears and says pictures are kept | covered |
| S63 | Failed Delete File: no History entry | A3::test_a_delete_module_file_that_failed_is_no_history_entry | covered |
| S64 | Damaged file never empty; every save refused | U/test_module_file_damage::test_damaged_file_is_refused, ::test_module_setup_save_is_refused, ::test_layout_saves_are_refused, ::test_button_map_save_is_refused | covered |
| S65 | Card "Module file damaged – inputs blocked", Start Fresh… | U/test_module_file_damage::test_card_says_damaged_and_start_fresh_keeps_a_copy; S1::test_a_damaged_card_turns_back_after_history_restore | covered |
| S66 | Start Fresh asks, moves aside, says when it fails | U/test_module_file_damage::test_start_fresh_keeps_the_damaged_file; S1::test_start_fresh_moves_the_damaged_file_aside | covered |
| S67 | Damaged file never stops Home or Run lists | A3::test_a_module_file_that_is_not_utf8_doesnt_stop_home | covered |
| S68 | Writes atomic, no temporary file left | U/test_module_file_damage::test_write_is_safe_and_leaves_no_temporary_file | covered |
| S69 | Each successful write/delete one History entry; failed none | F03::test_s69_each_module_file_write_and_delete_is_one_history_entry; S1::test_start_fresh_is_a_history_entry; B1M::test_start_fresh_is_one_history_entry | new |
| S70 | Home: a card per physical device, vJoy, Xbox | F03::test_s70_s71_home_shows_each_device_and_the_logical_device_only_with_a_file | new |
| S71 | Also Keyboard, OSC, Logical Device (with a file) | F03::test_s70_s71_home_shows_each_device_and_the_logical_device_only_with_a_file | new |
| S72 | No file: "No module" with show-stubs; kept after Delete Device | F03::test_s72_a_device_without_a_module_shows_no_module_only_with_show_stubs; S1::test_delete_device_removes_the_devices_actions_file_and_card_layout | new |
| S73 | Card shows photo, name, status · bus, counts in words, Driven by (outputs), last | F03::test_s73_an_output_card_is_driven_by_the_devices_wired_to_it; U/test_bound_cards. Hands-on: Home cards read "1 hat"/"2 hats", "Driven by: [...]" only on vJoy/Xbox, no photo in compact view | new + hands-on |
| S74 | Last line: latest passed input / output while running; friendly name, hover | U/test_input_module_gate::test_status_last_hid_only_on_input_cards, ::test_dest_last_prefers_button_press_then_axis; U/test_batch3_C3a::test_home_last_line_shows_what_the_input_module_passed | covered |
| S75 | Driven by follows edits, full Xbox names, no extra spaces | U/test_driven_by_follows_edits; U/test_bound_cards::test_xbox_wire_uses_full_name, ::test_driven_by_drops_spaces_from_a_module_files_name; U/test_batch3_C3a::test_driven_by_tells_a_real_xbox_pad_from_the_xbox_output | covered |
| S76 | Card re-reads its file at most twice a second, only on change | U/test_status_claim_cache::test_many_events_read_the_file_once, ::test_a_newer_save_is_picked_up | covered |
| S77 | Each twin card its own counts | U/test_twin_devices::test_each_twin_has_its_own_card; B1M::test_twin_cards_keep_their_own_counts_and_are_looked_up_by_id | covered |
| S78 | Card counts are claimed counts (no file: device's own, D-03-Q8-NOFILE) | S1::test_card_counts_at_a_reload_are_the_claimed_counts, ::test_card_counts_after_a_settings_change_are_the_claimed_counts; U/test_batch2_b3::test_a_settings_change_gives_the_same_status_and_counts_as_a_reload; F03::test_s72_... | covered |
| S79 | Double-click/Enter opens Configuration or Output View; arrows move | Hands-on: double-click a stick card: Configuration; Enter on vJoy card: Output View; arrow keys move focus | hands-on |
| S80 | Right-click picks the card; selection kept | U/test_home_right_click::test_a_right_click_picks_the_card, ::test_a_right_click_in_a_selection_keeps_it | covered |
| S81 | Drag reorders; order persists; hidden/unplugged/renamed/deleted places | A3::test_a_drag_keeps_hidden_cards_places, ::test_a_renamed_stick_keeps_its_cards_place, ::test_a_file_chosen_for_a_stick_does_not_take_another_sticks_place, ::test_a_deleted_devices_place_in_the_card_order_goes | covered |
| S82 | Hide Card / Hidden Cards / Unhide All | S1::test_hide_card_and_hidden_cards_and_unhide_all | covered |
| S83 | Resize kept 220-720 × 140-520, persists; stack shares size | F03::test_s83_card_sizes_are_kept_in_their_limits_and_persist; S1::test_stacked_cards_of_one_kind_share_a_pile_and_a_size. Hands-on: drag a card corner | new |
| S84 | Stack same kind; Unstack, Unstack All; click raises | S1::test_stacked_cards_of_one_kind_share_a_pile_and_a_size, ::test_an_input_and_an_output_card_are_not_stacked, ::test_raise_unstack_and_unstack_all | covered |
| S85 | Reset Size, Reset All, Reset Card Layout; Home follows Options | F03::test_s85_reset_size_reset_all_and_reset_card_layout; U/test_card_sizes_follow::test_home_cards_follow_sizes_reset_elsewhere; U/test_batch2_b3::test_unstack_all_and_reset_card_layout_still_clear_the_stack | new |
| S86 | Compact view, Layout, divider persist | S1::test_compact_view_and_layout_persist; U/test_cleanup_batch_a::test_pane_dividers_live_with_the_window_layout | covered |
| S87 | Order/hide/sizes/stacks keyed by device name (F2) | A3::test_a_renamed_stick_keeps_its_cards_place, ::test_a_file_chosen_for_a_stick_does_not_take_another_sticks_place | covered |
| S88 | Card menu leaves out what doesn't apply | S1::test_card_menus_leave_out_what_does_not_apply, ::test_the_logical_device_card_menu, ::test_output_cards_have_no_delete_device, ::test_an_input_card_offers_delete_device | covered |
| S89 | Calibration and Auto Mapper from a card open its file | A3::test_calibration_and_auto_mapper_open_on_the_cards_file | covered |
| S90 | Delete Device: explain, red confirm, result | J/test_j09_delete_device_and_back::test_delete_device_explains_and_saves_a_copy_first; U/test_batch2_b3::test_delete_device_asks_first_when_stopped | covered |
| S91 | Save a copy writes a pack and checks it; else nothing deleted | J/test_j09_delete_device_and_back::test_delete_device_explains_and_saves_a_copy_first; U/test_stage1_history_pack::test_delete_device_is_refused_when_the_pack_cant_be_read_back | covered |
| S92 | Removes actions in every mode, file, pictures, bindings, size, stack | S1::test_delete_device_removes_the_devices_actions_file_and_card_layout; A3::test_delete_device_removes_a_renamed_sticks_file | covered |
| S93 | vJoy/Xbox keep the output file (Q18: no Delete Device there) | S1::test_delete_device_on_a_vjoy_keeps_its_output_module_file, ::test_output_cards_have_no_delete_device; U/test_batch2_b3::test_an_output_card_is_never_deleted_from_home | covered |
| S94 | A file another device uses stays | A3::test_a_file_another_stick_uses_is_not_deleted | covered |
| S95 | Profile handling (now Q4: in memory, left unsaved) | S1::test_delete_device_leaves_the_profile_unsaved; J/test_j09_delete_device_and_back::test_delete_device_leaves_the_profile_unsaved | covered |
| S96 | Plugged in keeps a card; unplugged card and place go | S1::test_delete_device_of_an_unplugged_stick; A3::test_a_deleted_devices_place_in_the_card_order_goes | covered |
| S97 | Deleted device's open windows close | U/test_batch2_B1::test_main_window_shell (closeDeletedDevice) | covered |
| S98 | Deleted devices folder default in data folder, chosen in Options | U/test_deleted_devices_folder::test_backups_default_to_the_data_folder, ::test_backups_follow_the_chosen_folder | covered |
| S99 | Calibration stored in the input module, applied before actions | F03::test_s99_s108_a_saved_axis_is_used_at_once_before_any_action_sees_it | new |
| S100 | Lists connected sticks with an input module; none: "No connected input module." | F03::test_s100_calibration_lists_only_connected_sticks_with_an_input_module; B1M::test_calibration_lists_both_sticks_that_share_a_file. Hands-on: no stick module: window says "No connected input module." | new |
| S101 | From a card shows that device; unconnected shown when it connects | Hands-on: card menu Calibration opens on that stick; open for an unplugged stick, plug it in: it appears | hands-on |
| S102 | Capture from the first value; one at a time | U/test_crash_and_loss_fixes::test_a_capture_starts_from_the_first_value_read; F03::test_s102_only_one_capture_runs_at_a_time | new |
| S103 | Save refused when low ≥ high or center outside, with reason | U/test_audit2_keyboard_calibration::test_a_center_outside_the_range_is_refused_with_the_reason, ::test_a_curve_loading_would_drop_is_not_written; U/test_crash_and_loss_fixes::test_a_calibration_with_no_range_is_refused_with_the_reason | covered |
| S104 | Hand-edited bad curve ignored | U/test_audit_devices::test_calibration_with_low_above_high_is_not_used | covered |
| S105 | Per-axis Save, Save All one write, "Not saved" | U/test_calibration_unsaved::test_back_at_the_saved_values_is_not_unsaved, ::test_a_changed_limit_is_unsaved | covered |
| S106 | Undo/Redo per axis; Undo stops a capture | U/test_calibration_undo (5 tests) | covered |
| S107 | Leaving/switching/quitting with unsaved axes asks | Hands-on: change a limit, choose another module / close / quit: each asks | hands-on |
| S108 | A saved axis is used at once, also while running | F03::test_s99_s108_a_saved_axis_is_used_at_once_before_any_action_sees_it | new |
| S109 | Changed id found by name and recorded | U/test_device_fixes::test_calibration_finds_a_stick_with_a_new_id_and_records_it, ::test_calibration_of_a_stick_found_by_id_leaves_its_binding | covered |
| S110 | Twins keep their own calibration | U/test_twin_devices::test_each_twin_keeps_its_own_calibration | covered |
| S111 | Old settings calibration used until the file has one | F03::test_s111_old_program_calibration_is_used_until_the_module_file_has_one | new |
| S112 | Damaged file refuses the save, untouched | U/test_module_file_damage::test_calibration_save_does_not_touch_it | covered |
| S113 | Calibration History shows only this module's file | Hands-on: Calibration › History lists only this module's file | hands-on |
| S114 | Input highlighting paused while Calibration is open | Hands-on: open Calibration, move a stick: Configuration page doesn't highlight; close: highlighting back | hands-on |
| S115 | Output View is read-only, moves only while running | Hands-on: Output View of vJoy 1 stopped: still; Run and press a mapped button: it moves; nothing editable | hands-on |
| S116 | Shows claimed outputs; no module: every control numbered per kind | U/test_audit2_coverage::test_output_view_numbers_buttons_and_hats_within_their_kind | covered |
| S117 | Appearance saved in the module file; copy, reset, ask on leave | F03::test_s117_output_view_appearance_is_saved_in_the_module_file; U/test_output_view_pads::test_vjoy_view_save_uses_that_devices_module_file, ::test_reset_does_not_save_and_has_width. Hands-on: change a colour, leave: asked; Copy from Xbox | new + hands-on |
| S118 | Output View header "Driven by: [...]" | Hands-on: Output View header shows "Driven by: [pJoy Pro]" for a wired vJoy | hands-on |
| S119 | Auto Mapper lists claiming inputs once per device, one output per vJoy | F03::test_s119_auto_mapper_lists_claiming_inputs_once_and_one_output_per_vjoy | new |
| S120 | Also claim reads fresh, refuses damaged | U/test_auto_mapper_claims::test_claim_option_claims_first; S1::test_auto_mapper_also_claim_on_a_damaged_output_file_makes_no_actions | covered |
| S121 | Configuration list: claimed controls the device has, friendly names | F03::test_s121_configuration_list_shows_claimed_controls_the_device_has | new |
| S122 | vJoy Viewer lists wired devices, marks "(not claimed)" | F03::test_s122_vjoy_viewer_lists_wired_devices_and_marks_unclaimed_outputs | new |
| Q1 | Running note "Saved changes work at once." | U/test_batch3_C1::test_running_note_says_module_setup_changes_work_at_once | covered |
| Q2 | Import Image: Cancel puts the old picture back | S1::test_module_setup_cancel_puts_the_old_picture_back; B1M::test_module_setup_keeps_the_photo_to_put_back_and_saves_once | covered |
| Q3 | Library copy only when the photo changed; one write | S1::test_save_module_with_the_same_photo_adds_nothing_to_the_library; B1M::test_module_setup_keeps_the_photo_to_put_back_and_saves_once | covered |
| Q4 | Delete Device in memory, profile left unsaved | S1::test_delete_device_leaves_the_profile_unsaved | covered |
| Q5 | Delete Device always keeps a JSON copy | S1::test_delete_device_without_save_a_copy_still_keeps_the_file | covered |
| Q6 | Delete Device refused while running | S1::test_delete_device_is_refused_while_running; U/test_batch2_b3::test_delete_device_is_refused_on_home_while_running | covered |
| Q7 | Logical Device card menu leaves out five items | S1::test_the_logical_device_card_menu | covered |
| Q8 | Cards show claimed counts (D-03-Q8-NOFILE: no file, own counts) | S1 card count tests; F03::test_s72_... | covered |
| Q9 | Calibration lists every axis, marks unclaimed | U/test_batch2_b2b::test_calibration_lists_every_axis_and_marks_unclaimed_ones | covered |
| Q10 | Stacks keep cards that aren't showing | S1::test_a_stack_edit_keeps_a_hidden_card_in_its_stack; U/test_batch2_b3::test_unstacking_another_card_keeps_a_hidden_card_in_its_stack, ::test_a_new_stack_keeps_a_hidden_card_in_its_old_stack | covered |
| Q11 | "Input/Output Module Setup" in the glossary | U/test_batch3_C1::test_glossary_names_module_setup_windows_and_button_map_options | covered |
| Q12 | Help Home topic lists Keyboard, OSC, Logical Device | U/test_batch3_C1::test_home_help_lists_every_card_and_what_each_leaves_out | covered |
| Q13 | Import into the file the device uses | S1::test_import_into_a_renamed_stick_goes_into_the_file_it_uses | covered |
| Q14 | Delete File keeps pictures, confirm says so | U/test_batch3_C5::test_delete_file_confirm_says_the_pictures_are_kept | covered |
| Q15 | Also claim: unwritable output skipped and listed | U/test_batch2_b3::test_also_claim_with_an_output_file_that_cant_be_written, ::test_merge_keeps_the_old_claim_when_the_write_fails | covered |
| Q16 | Keys typed in a text box not ticked | U/test_batch2_b3_typing::test_keys_typed_into_a_text_box_are_not_ticked | covered |
| Q17 | F2 / F3 / F4 | F2: A3 card-order tests; F3: S1::test_start_fresh_is_a_history_entry; F4: B1M::test_twin_cards_keep_their_own_counts_and_are_looked_up_by_id | covered |
| Q18 | No Delete Device on output cards | S1::test_output_cards_have_no_delete_device | covered |

## Batch hands-on checks for this page (from claude/catchup-test-plan.md)

| Batch | Check | Status |
|---|---|---|
| 1 (GL-075/076/090) | Load Home with sticks plugged in: no "looked up without its device id" warning in the log | hands-on |
| 1 (GL-078) | Module Setup: Import Image, then Cancel and Discard: old photo back (smoke part "setup") | covered by S1::test_module_setup_cancel_puts_the_old_picture_back |
| 2 (B3) | Type "Fire" in a Keyboard Module Setup name box: no keys ticked | hands-on (also U/test_batch2_b3_typing) |
| 2 (B3) | Run, then Delete Device on a stick card: refused ("Stop first") | hands-on |
| 2 (B2b) | Calibration: unclaimed axes marked "(not claimed)" | hands-on |
| 3 (C1) | Module Setup while running says "Saved changes work at once." | hands-on |
| 3 (C3a) | Profile Settings lists vJoy from the output module (real vJoy) | hands-on |
| 3 (C3a) | Idle vJoy during a long Run stays alive; no keep-alive after Stop | hands-on |
| 3 (C3a) | Home after Delete Device and a re-save of the device | hands-on |

## Bugs found

- FINAL-03-1 (S16): a vJoy set to be read back as an input (Profile Settings)
  passes only when its output module file records the vJoy's device id. With
  no output module file, or a file without `boundGuidLocal`, every event of
  that vJoy is dropped. `gremlin/modules/runtime.py` `reload` skips modules
  with no bound id and `_bind_live_physical` only walks `physical_devices()`.
  Test: F03::test_s16_a_vjoy_read_back_passes_whatever_its_output_module_file
  (strict xfail, 2 cases).

## Notes

- S41 "an output module is ticked only": read as Output Module Setup does not
  ask for presses (AU-58); the model still ticks a pressed control on any
  device. Left hands-on; see the question in the report.
- S73 "Driven by on output cards only" is decided in QML (`visible:
  direction === "dest"`); the model carries a target on input cards too.
