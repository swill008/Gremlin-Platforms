# Final test plan: 04 Profile and modes

Spec: `claude/program-map/04-profile-modes.md` (section 8, section 12: every
question decided as recommended, plus the Q14 change adding S94) and
`claude/decisions.md` (D-04-Q1..Q21, D-04-Q13-TIMELIMIT, D-SYS-R3,
D-06-STOP-MODE, D-02-Q1). New tests: `test/unit/test_final_04.py` (F04
below). Agent P04, 2026-10-06.

`U` = `test/unit/`, `J` = `test/journeys/`, `AI` = `test/action_interaction/`.
Short names: B4 = `U/test_batch2_b4.py`, C2 = `U/test_batch3_C2.py`,
S1A = `U/test_stage1_app_profile.py`, S1R = `U/test_stage1_runtime.py`,
A3RS = `U/test_audit3_run_stop.py`, F04 = `U/test_final_04.py`.

Hands-on checks run the real program (the user's PC, not off-screen).
Each says what to do and what to see.

## Section 8 statements

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | Profile holds modes, actions, settings, scripts; written only on Save / Save As | F04::test_s1_s62_profile_settings_stay_in_memory_until_saved; C2::test_opening_a_profile_never_writes_it | new |
| S2 | Logical Device / OSC rows and device names saved in the same file | F04::test_s2_logical_osc_rows_and_device_names_are_in_the_profile_file; B4::test_a_new_profile_object_keeps_another_profiles_rows | new |
| S3 | File menu entries with Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S | U/test_menus::test_every_main_command_is_in_the_menu_bar (entries). Hands-on: with the main window in front press Ctrl+N (New Profile runs), Ctrl+O (Open Profile dialog opens), Ctrl+S on a saved profile (footer names the file), Ctrl+Shift+S (Save Profile As dialog opens); the File menu shows New Profile, Load Profile…, Recent, Save Profile, Save Profile As… with those shortcuts | hands-on |
| S4 | Save / Discard / Cancel before New, Load, Recent, quit only with unsaved changes | Hands-on (WORKFLOW-HANDS-ON, F-06a): open a profile, change nothing, File › New Profile: no question. Add an action, File › New Profile: asks Save / Discard / Cancel; Cancel keeps the profile and the edit. Repeat with Load Profile…, a Recent entry and closing the window: each asks; Discard goes on without saving | hands-on |
| S5 | Stop a running profile before New or Load | F04::test_s5_new_and_load_stop_the_running_profile_first | new |
| S6 | New profile: "Untitled", one mode "Default", nothing to lose | U/test_profile_unsaved::test_a_new_profile_marked_clean_has_nothing_to_lose; S1A::test_new_profile_replaces_the_open_one; S1A::test_new_puts_the_toolbar_in_default | covered |
| S7 | `*` in the title while unsaved; file name (not path) otherwise | S1A::test_load_signal_order_and_the_open_profile, ::test_save_writes_the_file_and_records_it (file name, no path). Hands-on (WORKFLOW-HANDS-ON): open a saved profile: title "name.xml - Gremlin-Platforms R1"; add an action: within 2 s the title starts with "* "; Save: the `*` goes | hands-on |
| S8 | Only real edits count; an older file loaded with new defaults is not unsaved | U/test_profile_unsaved::test_freshly_loaded_older_file_is_not_unsaved, ::test_an_edit_is_unsaved_until_saved | covered |
| S9 | An open editor draft is not unsaved work | U/test_profile_unused_actions::test_an_open_draft_is_not_unsaved_work | covered |
| S10 | Save on a never-saved profile goes to Save As | Hands-on (F-04b): File › New Profile, add an action, press Ctrl+S: the Save Profile As dialog opens in the profiles folder | hands-on |
| S11 | Unfinished actions listed before save; "Save without them" leaves them out | U/test_data_safety::test_unfinished_actions_are_named_with_their_first_error; U/test_library_invalid_children::test_library_save_removes_every_invalid_child | covered |
| S12 | The unsaved check never deletes unfinished actions | U/test_library_invalid_children::test_library_check_does_not_drop_unfinished_actions | covered |
| S13 | Safe write (temp then swap); crash mid-save leaves old file byte-for-byte | U/test_profile_save_safe::test_a_failed_save_leaves_the_old_profile_whole, ::test_the_file_is_as_before | covered |
| S14 | Only actions an input uses go in the file | U/test_profile_unused_actions::test_the_file_gets_only_what_inputs_use; U/test_validate::test_an_unused_action_is_a_warning | covered |
| S15 | Failed Save As keeps the old file, says "Not written", no History entry | U/test_audit_saving::test_a_failed_save_as_keeps_the_profile_on_its_file; U/test_audit2_saving::test_a_save_that_failed_is_no_history_entry | covered |
| S16 | "Saved to the profile." after a save; footer names the file | Hands-on: edit, Ctrl+S: the note "Saved to the profile." shows and the footer names the written file; hover the footer: last-saved tooltip | hands-on |
| S17 | A History entry for every save that changed something | F04::test_s17_every_save_that_changed_something_is_a_history_entry | new |
| S18 | Loaded / saved profile to top of Recent (max 5, one per file), last profile | U/test_recent_profiles (6 tests); S1A::test_load_signal_order_and_the_open_profile, ::test_save_writes_the_file_and_records_it | covered |
| S19 | Missing Recent file: say so, keep the open profile (Forget It, Q15) | B4::test_a_missing_recent_profile_offers_forget_it | covered |
| S20 | File dialogs open in the profiles folder, `*.xml` | Hands-on: File › Load Profile…: the dialog opens in `<data folder>\profiles` with filter "Profile files (*.xml)"; same for Save Profile As… | hands-on |
| S21 | Last profile at start; `--profile` wins, read relative to the start folder | U/test_program_fixes::test_a_relative_profile_is_read_from_where_the_program_started, ::test_a_missing_profile_is_told_and_the_last_one_opens | covered |
| S22 | Last profile won't open at start: reason once, Forget It / Keep | U/test_startup_messages::test_a_last_profile_that_wont_open_is_offered_to_forget, ::test_forget_takes_it_off_the_start_and_recent_lists | covered |
| S23 | Any load failure: reason shown, previous profile reopened (else new one) | U/test_load_and_rename_safety::test_failed_load_reopens_the_profile_that_was_open, ::test_failed_load_with_nothing_to_reopen_says_so | covered |
| S24 | A failed load is not added to Recent or made the last profile | F04::test_s24_a_profile_that_failed_to_load_is_not_recent_or_last | new |
| S25 | Only version 14; others refused with a message | U/test_crash_and_loss_fixes::test_a_profile_of_another_version_raises (+ S23 for the message) | covered |
| S26 | Missing child action: load finishes (refused), never hangs | U/test_profile_missing_child_action::test_load_finishes_when_a_child_action_is_missing | covered |
| S27 | Unknown or looping parent: kept as top-level | U/test_audit_profile::test_a_mode_with_an_unknown_parent_is_kept; U/test_validate::test_a_loop_in_the_mode_tree | covered |
| S28 | Missing Play Sound / Load Profile file: opens, action kept with warning | U/test_audit_profile::test_a_missing_load_profile_file_still_loads; U/test_play_sound_missing_file | covered |
| S29 | Script that can't load: kept with settings, reason on Scripts page | U/test_user_script_load_errors (5 tests) | covered |
| S30 | Profile folder on the import path once, in front | U/test_audit2_coverage::test_a_script_folder_goes_on_the_import_path_once; U/test_action_fixes::test_loading_a_profile_keeps_the_search_path_in_order | covered |
| S31 | Action order of the file kept; Device Pack actions before | U/test_profile::test_library_preserves_action_order | covered |
| S32 | Another profile clears the Keyboard selected key and closes panes | F04::test_s32_another_profile_clears_the_selected_key (key). Panes: hands-on (F-05) open an action pane, load another profile: the pane is closed | new |
| S33 | Auto-load: exact path wins, then ticked patterns, blank/invalid match nothing | U/test_autoload_and_mode_prompts::test_typed_path_matches_whatever_the_slashes_and_case, ::test_every_ticked_pattern_is_tried, ::test_blank_and_broken_patterns_match_nothing | covered |
| S34 | No reload when the open profile's program comes back | U/test_audit_saving::test_auto_load_leaves_the_open_profile_alone; B4::test_focusing_the_program_itself_keeps_the_run | covered |
| S35 | Never switch over unsaved edits; "Auto-load Waited" once | U/test_autoload_and_mode_prompts::test_auto_load_waits_for_unsaved_edits | covered |
| S36 | Matched file missing: say once, stop unless Keep running | U/test_audit2_saving::test_a_missing_auto_load_profile_stops_the_open_one; U/test_audit_saving::test_auto_load_with_a_missing_profile_runs_nothing_else | covered |
| S37 | Program with no profile in front: stop unless Keep running | S1R::test_auto_load_stops_on_focus_loss_unless_kept_running | covered |
| S38 | Load Profile action: waits over unsaved, skips missing, else loads and runs | U/test_audit2_coverage::test_load_profile_loads_and_restarts_the_run, ::test_load_profile_waits_over_unsaved_changes, ::test_load_profile_skips_a_missing_file; A3RS::test_load_profile_runs_the_profile_after_its_event; S1A::test_load_profile_action_end_to_end | covered |
| S39 | At least one mode; the last can't be deleted | U/test_audit_profile::test_the_last_mode_stays | covered |
| S40 | Blank and look-alike names refused; own capitals may change | U/test_mode_hierarchy_model::test_mode_names_refuse_blank_and_look_alikes; B4::test_the_mode_tree_refuses_blank_and_look_alike_names | covered |
| S41 | Modes listed alphabetically | F04::test_s41_modes_are_listed_in_name_order; F04::test_s41_modes_are_listed_alphabetically_whatever_the_capitals (xfail FINAL-04-1) | new |
| S42 | Inherit from any mode not itself or below; "(none)" = top-level | F04::test_s42_a_mode_inherits_from_any_mode_not_itself_or_below | new |
| S43 | Parent's actions used for every empty input, any number of levels | F04::test_s43_a_child_mode_uses_its_parents_actions_through_every_level; AI/test_modes::test_simple, ::test_temporary_inheritance | new |
| S44 | Rename moves everything that names the mode | U/test_audit2_modes (7 tests); U/test_audit3_modes::test_a_script_that_failed_to_load_keeps_the_renamed_mode, ::test_manage_modes_rename_moves_the_main_window, ::test_button_map_labels_mode_follows_a_rename; U/test_modes::test_startup_mode_follows_rename_and_delete; U/test_audit_editing::test_steps_follow_a_mode_rename_and_go_with_a_deleted_mode; B4::test_the_last_mode_is_found_by_another_spelling; J/test_j02_modes_while_running | covered |
| S45 | Delete asks with the binding count | U/test_autoload_and_mode_prompts::test_mode_delete_counts_the_bindings_it_removes (count). Prompt: SAFE-4-HANDS-ON (Manage Modes trash asks with the count) | covered |
| S46 | Delete: children up, inputs and their actions gone, Startup Mode reset, stack, panes, toolbar | U/test_audit_profile::test_deleting_a_mode_keeps_every_child; U/test_profile_unused_actions::test_delete_mode_takes_the_actions_with_it; U/test_modes::test_startup_mode_follows_rename_and_delete; U/test_audit2_modes::test_the_pane_of_a_deleted_mode_closes, ::test_the_running_mode_list_follows | covered |
| S47 | One path for every rename and delete | U/test_audit3_modes::test_undo_import_deletes_a_mode_everywhere | covered |
| S48 | Nothing put back into a deleted mode | U/test_audit2_modes::test_nothing_is_put_into_a_deleted_mode | covered |
| S49 | Mode edits while running; running note; run keeps working | J/test_j02_modes_while_running (4 tests). Note: hands-on, open Manage Modes while running: the running note shows | covered |
| S50 | Closed Manage Modes ignores later profile changes | U/test_mode_hierarchy_model::test_closed_manage_modes_model_ignores_later_profile_changes | covered |
| S51 | One toolbar Mode; while running it shows the running mode | F04::test_s51_the_toolbar_follows_the_running_mode | new |
| S52 | Load / New lands in the Startup Mode (named, Last Active, Heuristic) | U/test_modes::test_heuristic_is_first_parentless_mode, ::test_named_mode, ::test_last_active, ::test_last_active_deleted_mode_falls_back, ::test_reset_uses_startup_mode; S1A::test_load_puts_the_toolbar_in_the_new_profiles_startup_mode, ::test_new_puts_the_toolbar_in_default; F04::test_s52_use_heuristic_is_alphabetical_whatever_the_capitals (xfail FINAL-04-2). Hands-on: HELP-BUG-HANDS-ON | covered |
| S53 | Run starts in the toolbar mode, not the Startup Mode | F04::test_s53_run_starts_in_the_toolbar_mode_not_the_startup_mode; A3RS::test_the_mode_stack_starts_fresh_and_temporary_modes_end_with_stop | new |
| S54 | Toolbar Mode box switches the running mode | S1A::test_select_mode (same path running or stopped) | covered |
| S55 | Last mode in memory while running; saved on Stop, quit, hourly | U/test_write_less::test_last_mode_waits_while_running | covered |
| S56 | Switch, Previous, Unwind, Cycle, Temporary | AI/test_modes::test_simple (switch, unwind), ::test_previous, ::test_cycling, ::test_temporary_inheritance, ::test_temporary_no_inheritance, ::test_temporary_tricky | covered |
| S57 | Cycle: next after current, skips deleted, stays put, empty does nothing | U/test_audit3_modes::test_cycle_steps_over_a_deleted_mode, ::test_cycle_with_only_the_current_mode_left_stays_put, ::test_a_sequence_without_known_modes_is_unchanged; U/test_action_fixes::test_cycle_goes_to_the_mode_after_the_current_one; U/test_crash_and_loss_fixes::test_cycling_through_no_modes_does_nothing | covered |
| S58 | Switch to an unknown mode ignored, logged once | AI/test_modes::test_switching_to_a_mode_the_profile_does_not_have_is_ignored | covered |
| S59 | Mode-history loops resolved by Oldest / Newest, also temporary | U/test_modes::test_cycling, ::test_temporaries | covered |
| S60 | Axis refresh on mode change only while running and option on | U/test_mode_refresh_and_add_key::test_runner_refreshes_axes_on_mode_change_only_while_listening | covered |
| S61 | Timer actions change mode on the main thread | U/test_action_fixes::test_action_timeouts_run_on_the_main_thread | covered |
| S62 | Settings stored in the profile; need a save | F04::test_s1_s62_profile_settings_stay_in_memory_until_saved; U/test_profile_settings::test_settings_modifications_roundtrip | new |
| S63 | Startup Mode offers Use Heuristic, Last Active, every mode | F04::test_s63_startup_mode_offers_heuristic_last_active_and_every_mode | new |
| S64 | "Use the Options default" follows Options; untick keeps today's value | U/test_profile_settings::test_settings_model_switches_between_options_and_own. Hands-on: MACRO-DELAY-HANDS-ON | covered |
| S65 | Old 0.05 delay reads as "follow Options" | U/test_profile_settings::test_macro_delay_follows_options_unless_set | covered |
| S66 | vJoy is output by default; one switched to input listed with physical devices, no Initial Values | F04::test_s66_a_vjoy_switched_to_input_is_listed_with_the_physical_devices; U/test_batch3_C3a::test_profile_settings_lists_vjoy_from_the_output_module | new |
| S67 | Initial Values set at Run; clamped to -1..1 on load | F04::test_s67_initial_values_are_clamped_when_the_profile_loads; S1R::test_an_initial_value_is_written_at_run_through_the_output_module, ::test_an_initial_value_is_written_whatever_the_axis_reads; B4::test_initial_values_set_in_the_ui_are_clamped | new |
| S68 | One input item per device / input / mode; empty ones not written | F04::test_s68_one_input_item_per_input_and_mode_and_empty_ones_are_not_saved | new |
| S69 | Root action and "Treat as" kept; axis/hat as button needs virtual button or refused | F04::test_s69_treat_as_button_keeps_its_settings_and_is_refused_without | new |
| S70 | Ask before changing "Treat as" on a binding with actions | Hands-on (SAFE-4-HANDS-ON): an axis binding with an action, click Treat as Button: asks; Cancel keeps the binding and its action | hands-on |
| S71 | Deleted action removed unless another input uses it | U/test_profile_unused_actions::test_a_shared_action_stays_while_an_input_uses_it; U/test_audit3_actions_undo::test_one_removal_rule_frees_what_only_a_dead_action_held | covered |
| S72 | Actions added twice get new ids | F04::test_s72_actions_added_twice_get_new_ids | new |
| S73 | Snapshot of any input; unreadable snapshot changes nothing | U/test_audit_profile::test_snapshot_puts_back_an_unfinished_action, ::test_a_snapshot_that_cannot_be_read_changes_nothing; U/test_audit2_undo::test_a_snapshot_of_an_unfinished_merge_axis_works | covered |
| S74 | Restore into the same profile keeps shared actions shared and ids | U/test_audit2_undo::test_a_shared_action_stays_shared_after_undo; U/test_audit3_actions_undo::test_undo_of_ok_on_a_shared_action_puts_both_back | covered |
| S75 | Pick lists / Reuse: only used actions plus the edited one; draft copy shown | U/test_audit2_undo::test_reuse_offers_only_merge_axes_an_input_uses; U/test_audit3_actions_undo::test_merge_axis_list_shows_the_one_being_edited, ::test_reference_list_offers_the_pane_copy_not_the_original | covered |
| S76 | Bindings on one input reordered by drag | U/test_sequence_reorder (3 tests) | covered |
| S77 | Swap moves bindings, action references, script variables both ways | U/test_swap_devices::test_swap_devices_from_data_xml; S1A::test_swap_onto_a_device_with_bindings_swaps_both_ways; U/test_audit_runtime::test_swap_devices_moves_references_both_ways; U/test_audit2_coverage::test_swap_devices_moves_script_variables_both_ways | covered |
| S78 | Inputs with no actions move with their device | F04::test_s78_inputs_with_no_actions_move_with_their_device; B4::test_swap_moves_inputs_through_the_profile | new |
| S79 | Keyboard, Logical Device, OSC, Xbox left out and refused | U/test_audit2_startup_devices::test_swap_devices_lists_only_sticks, ::test_swap_devices_refuses_what_isnt_a_stick | covered |
| S80 | Asks first; says nothing saved, undo = reload without saving; no Undo | Hands-on: Tools › Swap Devices…, pick both devices, Swap: a question says nothing is saved yet and that undo means reloading without saving; Cancel changes nothing; there is no Undo entry after the swap | hands-on |
| S81 | Device list with counts, "Unknown device (short id)", refreshes | U/test_audit3_screens::test_the_swap_list_follows_a_swap_and_another_profile, ::test_swap_list_selection_after_a_swap | covered |
| S82 | Opened from a card: card's device is the connected device | Hands-on (WORKFLOW-HANDS-ON): right-click a stick card › Swap Device…: the connected-device box shows that stick | hands-on |
| S83 | A swap needs a save to stick | F04::test_s83_a_swap_needs_a_save_to_stick | new |
| S84 | Added script named "Instance N"; one file more than once | F04::test_s84_a_script_file_added_twice_gets_its_own_instance_names; U/test_profile::test_script_manager | new |
| S85 | Rename (unique per file), configure, remove after asking | F04::test_s85_a_script_name_is_unique_per_file; U/test_profile::test_script_manager (remove); B4::test_a_removed_script_leaves_no_settings_behind. Asking: hands-on, Scripts page trash: asks before removing | new |
| S86 | Scripts and values saved; path in the scripts folder may be relative | F04::test_s86_a_script_saved_with_a_path_in_the_scripts_folder_loads; U/test_user_script (xml transforms) | new |
| S87 | Run only configured scripts, fresh at every Run, retry failed ones | F04::test_s87_only_configured_scripts_run_and_each_run_reloads_them; U/test_user_script_load_errors::test_fixed_script_loads_again_with_its_settings, ::test_script_broken_after_loading_is_not_run | new |
| S88 | Settings of a script that can't load written back unchanged | U/test_user_script_load_errors::test_syntax_error_keeps_the_script_and_its_settings, ::test_missing_file_is_kept_not_dropped | covered |
| S89 | Scripts' joy / keyboard / vjoy through the modules; claims apply | U/test_input_state_claims::test_scripts_get_the_claim_aware_objects, ::test_unclaimed_inputs_read_neutral; U/test_vjoy_writers_use_firewall::test_scripts_get_the_firewalled_vjoy | covered |
| S90 | Periodic callbacks no faster than 0.01 s, failure logged, all stop at Stop | U/test_user_script::test_periodic_callback_exception_is_logged_and_does_not_stop_other_callbacks, ::test_periodic_reload_replaces_instead_of_duplicating; U/test_audit_runtime::test_a_periodic_callback_with_no_interval_still_stops; C2::test_periodic_callbacks_run_on_the_program_clock | covered |
| S91 | Script callbacks while paused don't raise; Resume works | U/test_action_fixes::test_while_paused_a_script_callback_does_not_stop_the_rest; AI/test_pause_resume | covered |
| S92 | History Restore: input back as unsaved change; whole profile as a copy | U/test_history_restore::test_an_input_goes_back_into_the_open_profile, ::test_a_whole_profile_is_written_as_a_copy; U/test_audit_saving::test_restored_profile_copies_never_overwrite | covered |
| S93 | Undo works after a save | U/test_profile_unused_actions::test_undo_after_a_save_keeps_the_action | covered |
| S94 | Recovery copy of unsaved profile edits, offered after a crash | None: the feature is not built (GL-029, deferred from the catch-up as a new feature). A test needs its interface first | gap |

## Decisions (section 9 questions, all as recommended; Q14 changed)

| Ref | Decision (short) | Check | Status |
|---|---|---|---|
| Q1 | Load / New lands in the new profile's Startup Mode | S1A::test_load_signal_order_and_the_open_profile, ::test_load_puts_the_toolbar_in_the_new_profiles_startup_mode, ::test_new_puts_the_toolbar_in_default. Hands-on: HELP-BUG-HANDS-ON | covered |
| Q2 | Last Active = last mode used while running | B4::test_a_toolbar_pick_while_stopped_is_not_the_last_mode | covered |
| Q3 | Auto-load over unsaved edits stops the run unless Keep running | B4::test_auto_load_held_by_unsaved_edits_stops_the_open_profile | covered |
| Q4 | Next Run: start mode, temporary modes cleared | A3RS::test_the_mode_stack_starts_fresh_and_temporary_modes_end_with_stop | covered |
| Q5 | Toolbar Mode while running switches the run | S1A::test_select_mode (S54) | covered |
| Q6 | Delete Mode can be undone | B4::test_undo_delete_mode_brings_back_the_mode_and_its_bindings, ::test_undo_delete_mode_refuses_a_name_taken_since. Hands-on (batch 2 B4): delete a mode with bindings, Undo Delete: mode and bindings back | covered |
| Q7 | Unknown action type: opens, kept, warning | U/test_data_safety::test_a_profile_with_an_unknown_action_type_opens_and_keeps_it. Hands-on (batch 1 GL-105): open a profile with a made-up action type: it opens with a warning; save and reopen: the action is still in the file | covered |
| Q8 | Inputs in an unlisted mode named at load | B4::test_bindings_in_an_unlisted_mode_are_named_at_load | covered |
| Q9 | No modes: "Default" added; duplicate names warned | B4::test_a_profile_without_modes_gets_default, ::test_a_mode_listed_twice_is_warned_about | covered |
| Q10 | Unknown Startup Mode = Use Heuristic | B4::test_an_unknown_startup_mode_loads_as_use_heuristic; S1A::test_unknown_startup_mode_resolves_like_use_heuristic, ::test_unknown_startup_mode_shows_as_use_heuristic | covered |
| Q11 | Initial Values always set at Run | S1R::test_an_initial_value_is_written_whatever_the_axis_reads | covered |
| Q12 | vJoy Behavior while running: note, Run untouched | B4::test_vjoy_behavior_switch_sends_no_device_change. Hands-on (batch 2 B4): Run, switch a vJoy's Behavior: "This change takes effect at the next Run." shows; the Run keeps going | covered |
| Q13 | Script top-level code runs under a time limit (D-04-Q13-TIMELIMIT) | C2::test_a_script_that_waits_at_load_does_not_freeze_the_program, ::test_a_script_loads_on_a_worker_thread, ::test_a_script_error_at_load_is_still_reported. Hands-on (batch 3 C2): add a script whose top level loops: after about 5 s the Scripts page shows the reason, the program stays responsive | covered |
| Q14 | Recovery copy (S94) | See S94 | gap |
| Q15 | Missing Recent file offers Forget It | B4::test_a_missing_recent_profile_offers_forget_it | covered |
| Q16 | `--profile` missing, no last profile: "A new profile is open" | C2::test_missing_profile_with_no_last_profile_says_a_new_one_is_open, ::test_missing_profile_with_a_last_profile_says_it_was_opened | covered |
| Q17 | Last-mode store keyed by resolved, case-folded path | B4::test_the_last_mode_is_found_by_another_spelling | covered |
| Q18 | Device names filled only at save | B4::test_plugging_in_a_used_stick_is_not_an_unsaved_change | covered |
| Q19 | Measure the 1.5 s unsaved check on large profiles | Hands-on: open the 1,172-action profile, keep the main window in front for a minute while moving an axis: no stutter; the measuring part of GL-153 is still open (no timing test) | hands-on |
| Q20 | Swap refuses From = To | B4::test_swap_devices_refuses_the_same_device | covered |
| Q21 | Look-alike name rule in `ModeHierarchy.add_mode` | B4::test_the_mode_tree_refuses_blank_and_look_alike_names | covered |

## Batch hands-on checks for this page (from `claude/catchup-test-plan.md`)

| Ref | What to do | What to see |
|---|---|---|
| HELP-BUG-HANDS-ON (batch 1, GL-053) | Set Startup Mode to a named mode, save, reload. Last Active: run in a mode, stop, reload. Change the toolbar mode, Run | Toolbar shows the named mode and Run runs in it; after reload the toolbar shows the last mode run in; Run runs in the toolbar mode |
| GL-105 (batch 1) | Open a profile with a made-up action type | It opens, a warning names the type, the action is saved back |
| B4 auto-load (batch 2) | Auto-load on, a profile matched to a program; run it from that program, then click into Gremlin | The Run keeps going |
| B4 Undo Delete Mode (batch 2) | Manage Modes: delete a mode with bindings, then Undo Delete | The mode and its bindings come back |
| B4 vJoy Behavior (batch 2) | Run, then switch a vJoy's Behavior in Profile Settings | Note "This change takes effect at the next Run."; the Run is not stopped or restarted |
| C2 script time limit (batch 3, GL-040) | Add a script whose top-level code loops; load a profile that has it | After about 5 s the reason shows on the Scripts page; the program stays responsive |
| SAFE-4-HANDS-ON | See S45, S70; auto-load with unsaved edits | Asks with the binding count; Treat as asks; "Auto-load Waited" once |
| MACRO-DELAY-HANDS-ON | See S64 | Greyed box follows Options; unticked value kept after save and reopen |
| WORKFLOW-HANDS-ON | See S4, S7, S82 | No question with nothing changed; `*` after an edit; card's device preset in Swap Device |
| PS-02..04, SW-01..03 (old test plan) | Profile Settings macro delay, vJoy switch, Initial Values with real vJoy; Swap Devices with two real sticks | As S64, S66, S67, S77-S83 |

## Counts

Section 8: 94 statements (S1-S94). covered 60, new 24, hands-on 9, gap 1.
Decisions Q1-Q21: covered 19, hands-on 1 (Q19), gap 1 (Q14 = S94).
New tests: 25 in F04 (23 pass, 2 xfail strict: FINAL-04-1, FINAL-04-2).
