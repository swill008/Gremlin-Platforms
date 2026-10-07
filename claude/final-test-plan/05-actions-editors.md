# Final test plan: 05 Actions and their editors

Spec: `claude/program-map/05-actions-editors.md` (section 8 S1-S108; section
12: every question decided as recommended, S78 replaced by Q5, S80's Split
Axis part by Q10) and `claude/decisions.md` (D-05-*, D-SYS-A1/A4,
D-05-DRAFT-OUTDATED, D-05-S69-Q7, D-STD-LAYER-KBM, D-STD-XBOX). New tests:
`test/unit/test_final_05.py`. Agent P05, 2026-10-06.

`U` = `test/unit/`, `AI` = `test/action_interaction/`, `J` = `test/journeys/`.

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | Every built-in plugin loads; a broken one stops start-up | U/test_audit2_startup_devices.py::test_a_bad_core_plugin_still_raises; U/test_stage1_app_profile.py::test_every_built_in_action_is_registered_without_vjoy | covered |
| S2 | A user plugin that fails is skipped and logged | U/test_audit2_startup_devices.py::test_a_bad_user_plugin_is_left_out_entirely; U/test_audit_runtime.py::test_a_broken_user_plugin_is_skipped | covered |
| S3 | User plugin clashing tag/name/QML type or bad input types refused | U/test_audit2_startup_devices.py::test_a_user_plugin_cant_replace_a_built_in_action, ::test_a_bad_user_plugin_is_left_out_entirely (input types cases); U/test_audit3_startup.py::test_a_user_plugin_cant_replace_a_built_in_qml_element | covered |
| S4 | Add Action lists only actions that suit axis/button/hat/key | U/test_final_05.py::test_s4_add_action_lists_only_actions_that_suit_the_input | new |
| S5 | A key, or axis/hat treated as a button, gets the button actions | U/test_final_05.py::test_s5_keys_and_inputs_treated_as_buttons_get_the_button_actions | new |
| S6 | Add Action follows Options order/hiding; Root never listed | U/test_option_list_saving.py::test_action_order_move_is_saved; U/test_batch2_B5b.py::test_hidden_actions_stay_hidden_with_others_missing, ::test_damaged_action_order_settings_never_empty_the_add_action_list; U/test_final_05.py::test_s6_root_is_never_offered | covered + new |
| S7 | New plugin added to the list (shown); missing one leaves it | U/test_final_05.py::test_s7_new_plugins_join_the_list_shown_and_gone_ones_leave | new |
| S8 | Right-click: first three as quick adds, rest under Map to / Axis and Hat / Logic and Timing / Other | U/test_batch3_c4.py::test_action_kinds_name_real_actions (kind names). Hands-on: right-click an action header in the pane: the first three Options actions are listed as quick adds, the rest under the four kind headings, in the same order as Options > Actions > Add Action Menu | hands-on |
| S9 | Map to vJoy offered only with a vJoy output | U/test_stage1_app_profile.py::test_add_action_does_not_offer_map_to_vjoy_without_vjoy, ::test_add_action_offers_map_to_vjoy_with_vjoy | covered |
| S10 | Text to Speech offered for buttons and keys | U/test_batch2_B5b.py::test_text_to_speech_is_offered_on_keyboard_keys; U/test_final_05.py::test_s5_… (TTS in the key's list) | covered + new |
| S11 | Every action has a Help topic | U/test_help_guide.py::test_every_action_plugin_has_a_topic | covered |
| S12 | List: claimed inputs of one device, with actions of the toolbar mode | U/test_final_05.py::test_s12_the_list_shows_claimed_inputs_in_the_toolbars_mode | new |
| S13 | No claimed inputs: says so, points to Module Setup; filters hide all: "No inputs match the current filters." + Clear Filters | Hands-on: open Configuration for a device with no module file / no claims: the empty text names Module Setup; set Type = Macro on a device with no macros: "No inputs match the current filters." and Clear Filters brings the rows back | hands-on |
| S14 | Input with no actions shows **No actions** | U/test_batch3_c4.py::test_the_configuration_list_says_no_actions; U/test_final_05.py::test_s15_… (row summary) | covered + new |
| S15 | "Move inputs with no actions to the end" lists them under a No actions heading | U/test_final_05.py::test_s15_inputs_with_no_actions_go_together_under_no_actions | new |
| S16 | Child row names type and destination | U/test_catalog_actions.py::test_summarize_covers_every_plugin_tag; U/test_labels_and_limits.py::test_catalog_names_the_file_or_program, ::test_catalog_motion_mouse_is_not_a_button | covered |
| S17 | Containers show their inside; empty container = empty sequence | U/test_catalog_actions.py::test_wrapper_with_child_shows_the_child, ::test_wrapper_without_child_is_an_empty_sequence; U/test_batch3_c4.py::test_an_empty_wrapper_shows_its_name_and_no_actions | covered |
| S18 | Type filter entries; Output filter lists destinations in use | U/test_batch3_c4.py::test_type_names_are_the_plugins_names, ::test_the_type_box_reads_its_names_from_the_model; U/test_batch2_b5a.py::test_the_output_filter_shows_without_vjoy | covered |
| S19 | Live LEDs/bars when Appearance on, never while editing locked | Hands-on: turn on row LEDs in Appearance, move a stick: rows light; Run: LEDs/bars stop while locked | hands-on |
| S20 | Parent opens all the input's actions, child only that one | U/test_final_05.py::test_s20_a_parent_opens_every_action_a_child_only_its_own. Hands-on IC-03..05: click parent, child and Add Action rows | new |
| S21 | Pane edits don't change the input until OK | U/test_pane_draft.py::test_draft_does_not_change_the_parent_until_ok; J/test_j01_edit_save_run.py::test_the_pane_edits_a_draft_until_ok | covered |
| S22 | OK writes, profile stays unsaved, pane stays open on a fresh copy | U/test_final_05.py::test_s22_ok_writes_keeps_the_profile_unsaved_and_the_pane_on_a_new_copy. Hands-on IC-11: tick "Close pane after OK", OK closes the pane | new + hands-on |
| S23 | "Close pane after OK" and pane width remembered | U/test_final_05.py::test_s23_close_after_ok_and_the_pane_width_are_remembered. Hands-on IC-09..13: drag the pane grip, restart: same width | new |
| S24 | OK with nothing changed does nothing (no Undo step) | U/test_final_05.py::test_s24_ok_with_nothing_changed_makes_no_undo_step | new |
| S25 | Remove every action then OK clears the input, as an Undo step | U/test_audit_editing.py::test_removing_every_action_in_the_pane_then_ok_clears_the_input | covered |
| S26 | X / other input / leave / Load / New / Quit with changes asks Save/Discard/Cancel | U/test_batch2_b5a.py::test_each_pane_answers_close_action_panes (pane functions exist). Hands-on IC-09 / F-05: edit in the pane, then each of X, another row, another page, File > Open, File > New, Quit: the Save / Discard / Cancel box shows; Cancel keeps the edit, Discard drops it | hands-on |
| S27 | Discard/X leaves the profile exactly as before (unfinished included) | U/test_audit3_actions_undo.py::test_cancel_leaves_an_unfinished_merge_axis_as_it_was; U/test_action_editor_fixes.py::test_reusing_a_shared_merge_axis_then_cancel_changes_nothing | covered |
| S28 | Mode change closes a clean pane; dirty pane stays, OK to its own mode "(in <mode>)" | U/test_audit_editing.py::test_ok_after_a_mode_change_stays_on_its_input_and_undoes. Hands-on: edit, change toolbar mode: title says "(in Default)" | covered + hands-on |
| S29 | Mode rename keeps the pane; delete closes it with the message | U/test_audit2_modes.py::test_ok_after_the_panes_mode_is_renamed_writes_to_the_new_name, ::test_the_pane_of_a_deleted_mode_closes; U/test_audit_editing.py::test_steps_follow_a_mode_rename_and_go_with_a_deleted_mode | covered |
| S30 | Loading another profile closes an open pane | QML only (Main.qml onProfileChanged). Hands-on F-05: open a pane (no changes), File > Open another profile: the pane is closed | hands-on |
| S31 | List Delete hidden/refused for the input open in the pane | U/test_audit_editing.py::test_the_list_delete_waits_while_the_pane_edits_that_input | covered |
| S32 | Editing locked while running | U/test_batch2_b5a.py::test_the_lock_follows_the_run, ::test_catalog_ok_is_refused_while_running, ::test_catalog_delete_and_undo_are_refused_while_running, ::test_the_catalog_pane_has_no_ok_while_running | covered |
| S33 | A draft never makes the profile look unsaved | U/test_profile_unused_actions.py::test_an_open_draft_is_not_unsaved_work | covered |
| S34 | Save with the pane open leaves the draft, writes only used actions | U/test_audit2_saving.py::test_a_save_with_the_pane_open_leaves_the_draft_alone; U/test_stage1_app_profile.py::test_save_with_the_pane_open_leaves_the_draft_alone | covered |
| S35 | Undo/Redo through each OK and Delete, 50 steps | U/test_catalog_undo.py::test_ok_undoes_and_redoes, ::test_a_delete_undoes_and_redoes; U/test_final_05.py::test_s35_undo_keeps_the_last_fifty_steps | covered + new |
| S36 | Undo waits while the pane is open and while running | U/test_final_05.py::test_s36_undo_waits_while_an_action_is_open_in_the_pane; U/test_batch2_b5a.py::test_catalog_delete_and_undo_are_refused_while_running | covered + new |
| S37 | Another device or profile starts with no steps | U/test_catalog_undo.py::test_another_profile_starts_without_steps; U/test_final_05.py::test_s37_another_device_starts_with_no_steps | covered + new |
| S38 | Steps follow a mode rename; dropped with a deleted mode | U/test_audit_editing.py::test_steps_follow_a_mode_rename_and_go_with_a_deleted_mode | covered |
| S39 | Unplayable step stays and says "That change couldn't be put back." | U/test_audit2_undo.py::test_configuration_undo_that_cant_be_played_keeps_its_step | covered |
| S40 | Undo never makes the profile unloadable (unfinished left out) | U/test_audit2_undo.py::test_a_snapshot_of_an_unfinished_merge_axis_works, ::test_a_snapshot_with_a_reference_placeholder_reads_back | covered |
| S41 | Undo keeps a shared action shared | U/test_audit2_undo.py::test_a_shared_action_stays_shared_after_undo; U/test_audit3_actions_undo.py::test_undo_of_ok_on_a_shared_action_puts_both_back | covered |
| S42 | Label field; blank stays blank after save/reload | U/test_action_xml_round_trip.py::test_blank_action_label_stays_blank | covered |
| S43 | The Note (root label) shows on the input's row | U/test_final_05.py::test_s43_the_note_shows_on_the_inputs_row (xfail FINAL-05-1) | new (xfail) |
| S44 | Press/release switches; both off shows "Off: never runs" | U/test_final_05.py::test_s44_both_switches_off_is_saved_and_never_runs. Hands-on: untick both on a button action: "Off: never runs" shows | new + hands-on |
| S45 | Problem icon with reason; errors left out by Save after asking | U/test_action_warnings.py (all); U/test_data_safety.py::test_unfinished_actions_are_named_with_their_first_error | covered |
| S46 | "Treat as" asks when actions, removes them on yes | U/test_input_item_binding_model.py::test_behavior_switch_clears_children, ::test_behavior_switch_noop_keeps_children. Hands-on: the question shows | covered + hands-on |
| S47 | Delete removes action + children unless shared; move keeps | U/test_action_editor_fixes.py::test_a_deleted_action_leaves_the_library, ::test_a_moved_action_stays_in_the_library, ::test_an_action_used_elsewhere_stays_when_deleted_here | covered |
| S48 | Removing a binding with actions asks first | Hands-on: header trash on a binding with actions: a question shows; No keeps it | hands-on |
| S49 | Hat as Buttons 8 -> 4 way asks before dropping a direction with actions | U/test_data_safety.py::test_hat_switch_keeps_the_shared_directions (model). Hands-on SAFE-3: put an action on NE, switch to 4 way: asked; No keeps 8 way | hands-on |
| S50 | Curve type change keeps points and Symmetric | U/test_crash_and_loss_fixes.py::test_changing_the_curve_type_keeps_the_points | covered |
| S51 | Editors state units and ranges | U/test_action_editor_fixes.py::test_editors_say_their_units_and_count_from_one | covered |
| S52 | Map to Xbox offers only fitting targets; saved odd target stays | U/test_map_to_xbox_inputs.py::test_targets_offered_for_each_input, ::test_a_saved_target_outside_the_list_stays_listed | covered |
| S53 | Map to vJoy shows "Output not claimed" for an unclaimed output | U/test_output_picker_keeps_wire.py::test_saved_unclaimed_output_is_kept_and_flagged; U/test_vjoy_selector_loads.py::test_the_vjoy_selector_loads_without_errors. Hands-on: pick an unclaimed vJoy button: the note shows | covered + hands-on |
| S54 | Map to Xbox: no claims, only a ViGEmBus warning | U/test_xbox_output_module.py::test_no_xbox_code_reads_a_claim; U/test_batch3_c4.py::test_no_claim_comment_on_xbox; U/test_batch3_C3a.py::test_module_setup_shows_no_claim_boxes_for_the_xbox_output | covered |
| S55 | Empty text fields reload empty, not "None" | U/test_final_05.py::test_s55_an_empty_text_field_reloads_empty[*] | new |
| S56 | Chain's empty sequences and order survive save/reload | U/test_action_chain_sequences.py::test_empty_sequence_in_the_middle_keeps_its_place, ::test_new_chain_keeps_its_empty_sequence | covered |
| S57 | Merge/Deadzone lists: edited one, new one, used ones; pane copy hides original | U/test_audit3_actions_undo.py::test_merge_axis_list_shows_the_one_being_edited, ::test_deadzone_list_shows_the_one_being_edited_and_new_is_selected, ::test_reference_list_offers_the_pane_copy_not_the_original | covered |
| S58 | "+" makes, selects, leaves a shared one finished | U/test_audit3_actions_undo.py::test_new_merge_axis_leaves_a_shared_one_finished, ::test_new_merge_axis_is_selected_and_listed; U/test_action_editor_fixes.py::test_a_new_merge_axis_gets_the_next_free_name | covered |
| S59 | Merge Axis Reuse keeps the shared action's name | U/test_batch3_c4.py::test_merge_axis_reuse_goes_through_the_library; U/test_audit2_undo.py::test_reuse_offers_only_merge_axes_an_input_uses | covered |
| S60 | Reference: share or Duplicate (deep copy) | U/test_audit3_actions_undo.py::test_reference_duplicate_copies_every_nested_action, ::test_configuration_pane_reference_cancel_and_pick_list | covered |
| S61 | Reference picked + Cancel loadable; + OK replaces placeholder | U/test_audit3_actions_undo.py::test_reference_picked_in_the_pane_then_cancel_keeps_the_profile_loadable, ::test_reference_picked_in_the_pane_then_ok_replaces_the_placeholder | covered |
| S62 | OK on a shared action changes it for both (Q1) | U/test_audit3_actions_undo.py::test_ok_on_a_shared_action_changes_it_for_both; U/test_action_editor_fixes.py::test_a_shared_action_says_who_else_uses_it. Hands-on (batch 1, GL-096): two axes share a Merge Axis, edit in one, OK: both changed, also after save and reload | covered + hands-on |
| S63 | A picked shared action is a copy until OK (Q1, A4) | U/test_audit3_actions_undo.py::test_a_picked_shared_action_is_a_copy_until_ok, ::test_reuse_in_a_pane_makes_a_copy; U/test_stage1_app_profile.py::test_merge_axis_reused_in_the_pane_then_cancel_changes_nothing | covered |
| S64 | Every action survives save/load for every input type | U/test_action_xml_round_trip.py::test_default_action_survives_save_and_load[*] | covered |
| S65 | Save writes only used actions | U/test_profile_unused_actions.py::test_the_file_gets_only_what_inputs_use | covered |
| S66 | Save asks before leaving out unfinished actions | U/test_data_safety.py::test_unfinished_actions_are_named_with_their_first_error. Hands-on SAFE-1: add an empty Merge Axis, File > Save: "Save without them" / Cancel | covered + hands-on |
| S67 | Missing child action: opens, child dropped on save | U/test_profile_missing_child_action.py::test_load_finishes_when_a_child_action_is_missing; U/test_audit3_actions_undo.py::test_a_save_drops_a_child_missing_from_the_library | covered |
| S68 | Missing sound/profile file: opens, kept, warns, does nothing | U/test_play_sound_missing_file.py (all); U/test_audit_profile.py::test_a_missing_load_profile_file_still_loads; U/test_audit2_coverage.py::test_load_profile_skips_a_missing_file | covered |
| S69 | Unknown action type: opens, kept and saved back, warning names it | U/test_data_safety.py::test_a_profile_with_an_unknown_action_type_opens_and_keeps_it. Hands-on (batch 1, GL-105): open a profile with a made-up action type | covered + hands-on |
| S70 | Response Curve Symmetric saved | U/test_crash_and_loss_fixes.py::test_symmetric_is_saved_and_read_back | covered |
| S71 | Mode rename updates Change Mode actions | J/test_j02_modes_while_running.py::test_the_renamed_cycle_is_saved, ::test_a_rename_while_running_moves_the_cycle | covered |
| S72 | Keyboard page lists each key once with the mode's actions | U/test_mode_refresh_and_add_key.py::test_a_key_in_two_modes_is_listed_once_with_the_shown_modes_actions | covered |
| S73 | Add Key adds to the viewed mode and selects it | U/test_mode_refresh_and_add_key.py::test_add_key_goes_into_the_given_mode; J/test_j07_keyboard_page.py::test_add_key_lists_and_selects_the_pressed_key | covered |
| S74 | Selected key shows its actions, actions can be added (Q4) | U/test_batch2_b5a.py::test_a_new_key_shows_one_empty_binding; U/test_stage1_app_profile.py::test_a_new_key_can_get_its_first_action; J/test_j07_keyboard_page.py::test_the_key_gets_an_action_that_is_saved. Hands-on (B5a): Add Key then first action + OK | covered + hands-on |
| S75 | Delete asks, removes only this mode's actions, shown only where it applies | U/test_audit2_keyboard_calibration.py::test_a_key_only_in_another_mode_is_not_in_this_one. Hands-on: Delete Key asks first | covered + hands-on |
| S76 | Deleting the last key lets the editor go | U/test_audit2_keyboard_calibration.py::test_deleting_the_last_key_lets_the_editor_go_of_it | covered |
| S77 | Rename gives the key an input name saved in the profile | U/test_batch3_L3.py::test_the_input_name_is_part_of_input_item_not_patched_in, ::test_an_input_without_a_name_writes_no_action_name. Hands-on (C3a): Rename on Keyboard rows | covered + hands-on |
| S78 / Q5 | Keyboard page uses the pane: draft, OK, Undo; asks before Remove | U/test_batch2_b5a.py::test_keyboard_edits_wait_for_ok_and_undo, ::test_keyboard_remove_and_cancel_change_nothing, ::test_the_keyboard_page_uses_the_draft, ::test_keyboard_ok_is_refused_while_running; U/test_batch2_b5a_screens.py::test_the_keyboard_page_edits_a_draft. Hands-on (B5a): switch keys with changes asks | covered + hands-on |
| S79 | Only claimed keys fire | U/test_keyboard_gate.py::test_claimed_key_passes_and_unclaimed_key_does_not, ::test_no_saved_keyboard_claim_passes_every_key | covered |
| S80 / Q10 | Actions run in order; later actions see Response Curve's value; Split's change stays inside its lists | U/test_final_05.py::test_s80_later_actions_see_the_value_response_curve_made; U/test_batch2_B5b.py::test_split_axis_does_not_change_the_value_for_later_actions | covered + new |
| S81 | One failing action doesn't stop the others or releases | U/test_audit_runtime.py::test_one_failing_action_does_not_stop_the_others; U/test_audit2_coverage.py::test_a_failing_action_still_runs_the_release_actions | covered |
| S82 | vJoy writes only claimed outputs; unclaimed blocked, logged once | U/test_output_layer.py::test_unclaimed_write_is_blocked_and_logged_once; U/test_vjoy_writers_use_firewall.py::test_map_to_vjoy_writes_through_the_output_module; U/test_stage1_modules.py::test_a_blocked_output_is_logged_once_from_two_threads | covered |
| S83 | Relative moves at Speed while off-centre; stops on outside change or 1 s rest | U/test_final_05.py::test_s83_relative_moves_at_speed_and_stops_a_second_after_the_input_rests; U/test_batch3_c4.py::test_the_relative_loop_stops_when_the_axis_is_moved_elsewhere. Hands-on (C4): relative axis on vJoy and Logical Device | new + hands-on |
| S84 | Xbox: button on a trigger full/0; hat moves a stick | U/test_map_to_xbox_inputs.py::test_button_on_a_trigger_is_full_or_nothing, ::test_a_hat_moves_a_stick | covered |
| S85 | Map to Keyboard holds keys, modifiers first, releases | AI/test_map_to_keyboard.py (all) | covered |
| S86 | Mouse wheel sends once per press | U/test_final_05.py::test_s86_the_mouse_wheel_turns_once_per_press | new |
| S87 | Merge/Deadzone read axes through input modules; unclaimed = centre | U/test_input_state_claims.py::test_actions_read_other_inputs_through_the_input_modules, ::test_unclaimed_inputs_read_neutral | covered |
| S88 | Split Axis: side left gets -1; any split value incl. 1.0 | U/test_action_fixes.py::test_split_axis_puts_the_half_it_leaves_at_rest; U/test_crash_and_loss_fixes.py::test_split_axis_at_the_end_handles_full_deflection | covered |
| S89 | Chain: timeout on press only; releases the pressed step; no sequences = nothing | U/test_action_fixes.py::test_chain_held_past_the_timeout_releases_the_pressed_step; U/test_crash_and_loss_fixes.py::test_a_chain_with_no_sequences_does_nothing; AI/test_chain.py (all) | covered |
| S90 | Tempo/Double Tap/Smart Toggle timeouts run on the main thread | U/test_action_fixes.py::test_action_timeouts_run_on_the_main_thread | covered |
| S91 | Those timers cancelled at Stop | U/test_stage1_runtime.py::test_a_tempo_timer_never_fires_after_stop; J/test_j10_tempo_stop.py::test_nothing_fires_after_stop. Hands-on (batch 1, GL-047): hold a Tempo button, Stop before the long press: nothing fires, vJoy free | covered + hands-on |
| S92 | Macro stops with Stop; empty macro does nothing | U/test_audit2_macros.py::test_a_one_shot_macro_stops_with_stop, ::test_a_macro_paused_behind_a_preempting_one_stops; U/test_crash_and_loss_fixes.py::test_an_empty_macro_does_nothing; J/test_j08_macro_stop.py (all) | covered |
| S93 | Change Mode to a missing mode ignored; Cycle's first press moves; empty does nothing | AI/test_modes.py::test_switching_to_a_mode_the_profile_does_not_have_is_ignored; U/test_action_fixes.py::test_cycle_goes_to_the_mode_after_the_current_one; U/test_crash_and_loss_fixes.py::test_a_mode_change_with_no_mode_does_nothing[*] | covered |
| S94 | Load Profile won't load over unsaved changes, says why | U/test_audit2_coverage.py::test_load_profile_waits_over_unsaved_changes | covered |
| S95 | Pause stops all but Pause and Resume | AI/test_pause_resume.py (all); U/test_action_fixes.py::test_while_paused_a_script_callback_does_not_stop_the_rest | covered |
| S96 | Play Sound queues at volume; overlap per Options | U/test_stage1_runtime.py::test_sequential_sounds_wait_for_the_one_playing, ::test_interrupt_stops_the_sound_playing, ::test_overlap_plays_sounds_together | covered |
| S97 | Run Command starts the program; arguments split, quotes kept | U/test_action_run_command.py::test_functor_launches_with_split_arguments | covered |
| S98 | Description does nothing when fired | U/test_final_05.py::test_s98_description_does_nothing_when_the_input_fires | new |
| S99 / Q3 | Run skips unfinished actions, one line each | U/test_audit3_actions_undo.py::test_run_leaves_out_unfinished_actions_with_a_line_each; U/test_stage1_app_profile.py::test_run_skips_unfinished_actions; U/test_audit3_run_stop.py::test_an_unfinished_action_is_named_when_the_run_is_built; U/test_action_editor_fixes.py::test_a_reference_placeholder_does_nothing_at_run | covered |
| S100 | Held keys/buttons released at Stop | U/test_audit3_run_stop.py::test_a_key_a_macro_holds_is_released_at_stop, ::test_map_to_keyboard_keys_are_released_when_stop_drops_the_release; U/test_batch1_run_callers.py::test_a_macro_that_ends_early_lets_go_of_its_keys_at_once | covered |
| S101 | Edits while stopped apply at next Run; nothing edited while running | U/test_batch2_b5a.py::test_the_lock_follows_the_run, ::test_every_page_reads_the_one_lock; J/test_j01_edit_save_run.py::test_run_sends_the_button_to_vjoy | covered |
| S102 | Input with no actions shows No actions and runs nothing | U/test_final_05.py::test_s15_… (shows). Hands-on: Run, press a claimed input with no actions: Input Monitor lists no actions, no output moves | new + hands-on |
| S103 | Map to Xbox without ViGEmBus warns but stays | U/test_final_05.py::test_s103_map_to_xbox_without_vigem_warns_and_stays_in_the_profile | new |
| S104 / Q2 | Profile with Map to vJoy opens without vJoy, keeps them | U/test_stage1_app_profile.py::test_a_profile_with_map_to_vjoy_opens_without_vjoy, ::test_options_action_list_keeps_map_to_vjoy_without_vjoy, ::test_map_to_vjoy_at_run_with_no_vjoy_device_does_nothing. Hands-on (D-05-Q2): open such a profile on a PC/VM with no vJoy device | covered + hands-on |
| S105 | Unplugged: actions stay; Merge/Deadzone axes read centred | U/test_input_state_claims.py::test_unclaimed_inputs_read_neutral; U/test_audit3_run_stop.py::test_a_condition_on_a_stick_plugged_in_later_works. Hands-on P3c: unplug a stick, its rows/actions stay, Merge Axis reads centre | covered + hands-on |
| S106 | Renamed / twin device keeps its own actions | U/test_twin_devices.py (all); J/test_j04_twin_sticks.py::test_run_passes_each_twins_own_checked_buttons | covered |
| S107 | Broken action reference opens; unreadable Undo step kept and reported | U/test_profile_missing_child_action.py::test_load_finishes_when_a_child_action_is_missing; U/test_audit2_undo.py::test_configuration_undo_that_cant_be_played_keeps_its_step | covered |
| S108 | OK'd unsaved edits lost on a crash (no recovery copy) | An accepted limitation (GL-029 deferred): nothing to check but the absence of a feature | gap |
| Q1 | Shared action: OK changes all, edited as a copy until OK | see S62, S63 | covered |
| Q6 | Catalog text: No actions, 1/N actions, Title Case names; glossary test covers binding_catalog.py | U/test_glossary_words.py::test_configuration_list_text_uses_the_glossary_words, ::test_configuration_list_type_names_are_the_action_names; U/test_batch3_c4.py::test_the_action_count_reads_actions. Hands-on (C4): Type box and "No actions" | covered + hands-on |
| Q7 | Text to Speech lists Keyboard | see S10 | covered |
| Q8 | History Restore, Auto Mapper, Device Pack close the pane first; OK refused if input changed | U/test_batch2_b7.py::test_an_input_restore_closes_the_action_panes_first; U/test_audit3_actions_undo.py::test_ok_after_the_input_changed_under_the_pane_writes_nothing. Hands-on (B7): each tool with an unsaved pane asks Discard/Cancel | covered + hands-on |
| Q9 | Axis Delta uses the shaped value; 0 is a value | U/test_batch2_B5b.py::test_axis_delta_uses_the_value_shaped_by_earlier_actions, ::test_axis_delta_treats_zero_as_a_value | covered |
| Q11 | While running the pane opens read-only, no OK | U/test_batch2_b5a.py::test_the_catalog_pane_has_no_ok_while_running, ::test_a_logical_pane_has_no_ok_while_running. Hands-on (B5a): Run with a pane open shows read-only, "Stop to edit" | covered + hands-on |
| Q12 | Removed Chain sequence released via the one removal rule | U/test_batch1_run_callers.py::test_a_removed_chain_sequence_is_released_from_the_library | covered |
| Q13 | Load Profile action handed to the Run owner, after the event | U/test_audit3_run_stop.py::test_load_profile_runs_the_profile_after_its_event; U/test_stage1_app_profile.py::test_load_profile_action_end_to_end | covered |
| Q14 | New Deadzones numbered like Merge Axis | U/test_batch2_B5b.py::test_new_dual_axis_deadzones_are_numbered | covered |
| Q15 | Input name is an InputItem field; no import-time patches | U/test_batch3_L3.py::test_the_input_name_is_part_of_input_item_not_patched_in | covered |
| Q16 | KB/mouse straight to Windows accepted; XboxTarget from the output module | U/test_final_05.py::test_q16_map_to_xbox_takes_its_types_from_the_output_module; U/test_run_scope_only.py::test_only_keyboard_and_sendinput_send_keys_to_windows | new + covered |
| Q17 | Macro Joystick step goes through the input module's claims | U/test_batch2_B5b.py::test_a_macro_joystick_step_passes_only_claimed_controls; U/test_batch3_c4.py::test_a_macro_joystick_step_is_synthetic | covered |
| Q18 | Unused code removed | U/test_batch3_c4.py::test_the_quick_editor_is_gone; U/test_final_05.py::test_q18_the_unused_editor_code_is_gone (xfail FINAL-05-3: newActionSequence, ActionPriorityListModel remain; GL-261 rest carried) | covered + new (xfail) |
| Q19 | Chain on gremlin.clock; UI rate limit stays | U/test_final_05.py::test_q19_chain_times_out_on_the_program_clock (xfail FINAL-05-2) | new (xfail) |
| Q20 | Catalog Delete asks | Hands-on: child row Delete asks before removing | hands-on |

## Batch hands-on checks for this page (from claude/catchup-test-plan.md)

- Batch 1 GL-096: two axes share a Merge Axis, edit it in one, OK: both change, also after save and reload.
- Batch 1 GL-105: open a profile with a made-up action type: it opens, a warning names the type, Save writes it back unchanged.
- Batch 1 GL-047: hold a Tempo button, Stop before the long press: nothing fires, vJoy free.
- Batch 2 B5a: Keyboard page Add Key, then first action + OK; switching keys with changes asks; Run with a pane open shows it read-only.
- Batch 2 B5b: Text to Speech under Tempo / macro speaks; TTS on a keyboard key.
- Batch 3 C4: Configuration Type box and "No actions"; Merge Axis / Deadzone record, switch, "+", save/reload; relative axis on vJoy and Logical Device.

## Counts

108 statements (S1-S108; S78 and S80 read with Q5/Q10) plus 15 decision rows
(Q1, Q6-Q9, Q11-Q20). Statements: covered 63, covered + hands-on 13,
covered + new 7, new 12, new + hands-on 4, new (xfail) 1, hands-on 7, gap 1.
Decision rows: covered 8, covered + hands-on 3, new + covered 1,
covered + new (xfail) 1, new (xfail) 1, hands-on 1.
New tests in test/unit/test_final_05.py: 28 (25 pass, 3 strict xfail:
FINAL-05-1 S43, FINAL-05-2 Q19, FINAL-05-3 Q18).
