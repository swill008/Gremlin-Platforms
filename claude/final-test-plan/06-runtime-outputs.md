# Final test plan – 06 Run time and outputs

Spec: `claude/program-map/06-runtime-outputs.md` (section 8 S1–S85, section 12
decisions Q1–Q19) plus later decisions in `claude/decisions.md`
(D-06-S39-NORELEASE, D-06-STOP-MODE). Agent P06, 2026-10-06.

New tests: `test/unit/test_final_06.py` (14 tests, all pass on the current
code, no xfail). Unit paths are `test/unit/` unless shown; `ai/` is
`test/action_interaction/` (fake vJoy, Logical Device in and out).

Real-driver cover (not run here, named only): `test/integration/test_e2e_profile_simple.py`
(axis, button, hat through real vJoy: S47, S49), `test/integration/test_e2e_macro.py::test_macro_sequence`
(S65), `test/integration/test_e2e_user_script.py` (S50).

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | Toolbar Run; while running it reads Stop, accent colour | Hands-on: open a profile, press Run: button reads **Stop** in the accent colour, status Running; press Stop: reads **Run**, normal colour | hands-on |
| S2 | Status bar Running / Stopped / Running (Paused) + "(unsaved changes)" | test_stage1_runtime.py::test_the_status_bar_says_running_paused | covered |
| S3 | Tray Run Profile / Stop Profile, other icon while running | test_stage1_runtime.py::test_the_tray_offers_run_or_stop_and_changes_its_icon; test_stage1_app_profile.py::test_tray_icon_follows_run_and_stop | covered |
| S4 | Nothing sent to vJoy/Xbox/Logical Device while stopped | test_final_06.py::test_after_stop_no_input_event_reaches_the_profile; timers/loops/macros: test_batch1_run_callers.py::test_a_timer_never_fires_after_stop, test_stage1_runtime.py::test_a_tempo_timer_never_fires_after_stop, test_batch1_run_callers.py::test_the_vjoy_relative_loop_ends_with_stop_and_run_again | new |
| S5 | Runs in the toolbar mode; a mode not in the profile uses Startup Mode | test_final_06.py::test_a_toolbar_mode_the_profile_lacks_uses_the_startup_mode; test_audit3_run_stop.py::test_the_mode_stack_starts_fresh_and_temporary_modes_end_with_stop | new |
| S6 | Running mode saved at Stop for Last Active | test_stage1_runtime.py::test_stop_disconnects_first_and_releases_the_drivers_last (flush_last_modes at Stop); test_batch2_b4.py::test_the_last_mode_is_found_by_another_spelling; test_batch2_b4.py::test_a_toolbar_pick_while_stopped_is_not_the_last_mode; test_modes.py::TestStartMode::test_last_active | covered |
| S7 | Profile Macro Default Delay, else Options | test_profile_settings.py::test_macro_delay_follows_options_unless_set | covered |
| S8 | vJoy Initial Values always written at Run via output module; physical refresh after (Q7) | test_stage1_runtime.py::test_an_initial_value_is_written_at_run_through_the_output_module, ::test_an_initial_value_is_written_whatever_the_axis_reads, ::test_the_physical_refresh_comes_after_the_initial_values | covered |
| S9 | Re-send physical axes at Run / mode change when Options on | test_mode_refresh_and_add_key.py::test_runner_refreshes_axes_on_mode_change_only_while_listening; test_stage1_runtime.py::test_the_physical_refresh_comes_after_the_initial_values | covered |
| S10 | Script failing to load: retried once at Run, skipped, logged, rest run | test_final_06.py::test_a_script_that_fails_to_load_is_skipped_and_the_rest_run; test_user_script_load_errors.py::test_fixed_script_loads_again_with_its_settings, ::test_script_broken_after_loading_is_not_run | new |
| S11 | Broken user plugin skipped | test_audit_runtime.py::test_a_broken_user_plugin_is_skipped | covered |
| S12 | "Could not run the profile: a user plugin is missing." | test_final_06.py::test_a_missing_user_plugin_says_so_and_runs_nothing | new |
| S13 | Editing locked while running (Configuration, Keyboard, OSC, Logical), "Profile running: stop it to edit" | test_batch2_b5a.py::test_the_lock_follows_the_run, ::test_every_page_reads_the_one_lock, ::test_catalog_ok_is_refused_while_running, ::test_keyboard_ok_is_refused_while_running, ::test_the_catalog_pane_has_no_ok_while_running, ::test_a_logical_pane_has_no_ok_while_running | covered |
| S14 | Run flag on only while running | test_audit2_coverage.py::test_the_run_flag_is_on_only_while_a_profile_runs; test_stage1_runtime.py::test_start_reads_outputs_then_connects_then_runs | covered |
| S15 | Stop before opening another profile or New | test_final_06.py::test_new_profile_stops_the_run_first, ::test_opening_a_profile_stops_the_run_first | new |
| S16 | Load Profile action: Stop, load, Run again | test_audit2_coverage.py::test_load_profile_loads_and_restarts_the_run; test_audit3_run_stop.py::test_load_profile_runs_the_profile_after_its_event, ::test_a_stop_before_it_drops_the_load | covered |
| S17 | Stop before quit; no vJoy held, no Xbox pad after quit | test_audit3_run_stop.py::test_quitting_stops_once_and_makes_nothing_to_stop_it; plus batch 1 hands-on (below) | covered |
| S18 | Failed Run: Stop disconnects everything | test_action_fixes.py::test_stop_disconnects_after_a_failed_run; test_stage1_runtime.py::test_a_start_failing_late_leaves_the_runner_stopped | covered |
| S19 | Stop then Run starts clean (no stale macros) | test_action_fixes.py::test_run_starts_with_no_stale_macros; test_audit2_macros.py::test_a_macro_of_the_last_run_leaves_the_new_run_alone | covered |
| S20 | Stop ends every macro at its next step, Pause at once | test_audit2_macros.py::test_a_one_shot_macro_stops_with_stop; test_audit3_run_stop.py::test_stop_during_a_step_in_progress_ends_the_macro | covered |
| S21 | Keys held by macro / Map to Keyboard released, last pressed first | test_audit3_run_stop.py::test_a_key_a_macro_holds_is_released_at_stop, ::test_map_to_keyboard_keys_are_released_when_stop_drops_the_release, ::test_held_outputs_are_released_last_pressed_first | covered |
| S22 | Mouse buttons released; one failing release doesn't stop others | test_audit3_run_stop.py::test_mouse_buttons_held_at_stop_are_released, ::test_a_failing_mouse_release_doesnt_cut_stop_short; test_batch1_run_callers.py::test_a_mouse_button_held_at_stop_is_released | covered |
| S23 | Mouse motion stops; next Run doesn't move at old speed | test_audit3_run_stop.py::test_mouse_motion_of_the_last_run_stops_with_it | covered |
| S24 | Pending pulse releases sent before drivers released | test_audit2_macros.py::test_a_pulse_release_waiting_at_stop_is_sent_first; test_audit3_run_stop.py::test_a_pulse_release_timer_fires_at_stop_before_the_drivers | covered |
| S25 | Logical Device relative loop ends | test_audit3_run_stop.py::test_the_logical_device_relative_loop_ends_with_stop | covered |
| S26 | vJoy relative loop ends, also on quick Run again (AU-117; fixed GL-048/061) | test_batch1_run_callers.py::test_the_vjoy_relative_loop_ends_with_stop_and_run_again, ::test_a_new_loop_does_not_wait_for_the_old_one | covered |
| S27 | Script timers stop; next Run its own loop | test_audit_runtime.py::test_a_run_after_a_slow_stop_starts_its_own_loop, ::test_a_periodic_callback_with_no_interval_still_stops | covered |
| S28 | Sounds and speech stop, queues emptied | test_stage1_runtime.py::test_stop_cancels_the_sounds_and_empties_the_queue, ::test_stop_ends_speech_and_empties_its_queue | covered |
| S29 | Every vJoy released, every Xbox pad unplugged | test_stage1_runtime.py::test_stop_disconnects_first_and_releases_the_drivers_last, ::test_the_xbox_pad_plugs_in_on_first_send_and_unplugs_at_stop | covered |
| S30 | No Tempo / Double Tap / Smart Toggle timer after Stop (AU-116; fixed GL-047) | test_batch1_run_callers.py::test_a_timer_never_fires_after_stop[*]; test_stage1_runtime.py::test_a_tempo_timer_never_fires_after_stop; test/journeys/test_j10_tempo_stop.py | covered |
| S31 | Script-pressed keys released (R4; fixed GL-049) | test_batch1_run_callers.py::test_a_key_a_script_holds_is_released_at_stop, ::test_keys_sent_with_no_run_on_are_left_alone | covered |
| S32 | Stop bounded even with a stuck step or driver | test_audit3_run_stop.py::test_a_step_stuck_in_a_driver_ends_the_other_macros; test_bounded_waits.py::test_a_macro_stops_waiting_for_an_exclusive_one_when_stopped | covered |
| S33 | Only claimed inputs run actions; Logical Device and OSC pass | test_logical_events_pass_gate.py::test_logical_device_events_reach_the_wire, ::test_unclaimed_hardware_is_still_dropped | covered |
| S34 | Running mode's actions; child uses parent's for empty inputs | ai/test_modes.py::test_temporary_inheritance (grandchild uses Parent's binding), ::test_temporary_no_inheritance | covered |
| S35 | Other actions and release actions run when one fails | test_audit_runtime.py::test_one_failing_action_does_not_stop_the_others; test_audit2_coverage.py::test_a_failing_action_still_runs_the_release_actions | covered |
| S36 | Paused runs only always-run actions; scripts skipped quietly | test_action_fixes.py::test_while_paused_a_script_callback_does_not_stop_the_rest; ai/test_pause_resume.py::test_pause_resume | covered |
| S37 | Each Run starts un-paused | test_stage1_runtime.py::test_each_run_starts_unpaused | covered |
| S38 | Button pressed in one mode released after a mode change | test_stage1_runtime.py::test_a_vjoy_button_pressed_before_a_mode_change_is_released, ::test_in_the_same_mode_the_action_releases_the_button_itself | covered |
| S39 | Axis range as button (enter/leave/jump/direction; in range at Run: no press, no release) | test_stage1_runtime.py::test_an_axis_entering_its_range_presses_and_leaving_releases, ::test_an_axis_already_in_its_range_at_run_gives_no_press, ::test_leaving_a_range_the_axis_started_in_sends_no_release, ::test_an_axis_jumping_across_its_range_presses_and_releases, ::test_an_axis_range_presses_only_in_the_chosen_direction; test_batch2_B5b.py::test_inside_at_run_then_leaving_sends_nothing_and_re_entering_presses | covered |
| S40 | Set of hat directions is one button | test_stage1_runtime.py::test_a_set_of_hat_directions_is_one_button | covered |
| S41 | Stick plugged in while running gets its claims (any setting) | test_device_fixes.py::test_input_modules_reload_when_a_device_is_plugged_in | covered |
| S42 | Device change: Reload / Ignore / Disable(Stop) | test_stage1_runtime.py::test_device_change_follows_the_option[*] | covered |
| S43 | Held button/hat of an unplugged stick let go | test_device_reconnect.py::test_held_inputs_are_let_go_on_unplug | covered |
| S44 | Stick plug/unplug doesn't release vJoy | test_device_scan.py::test_plugging_in_a_stick_does_not_reset_vjoy, ::test_a_vjoy_change_still_resets_vjoy | covered |
| S45 | Auto-load: load+Run, Stop on focus loss unless kept, never over unsaved, missing file Stops | test_stage1_runtime.py::test_auto_load_stops_on_focus_loss_unless_kept_running[*]; test_autoload_and_mode_prompts.py::test_auto_load_waits_for_unsaved_edits; test_batch2_b4.py::test_auto_load_held_by_unsaved_edits_stops_the_open_profile; test_audit2_saving.py::test_a_missing_auto_load_profile_stops_the_open_one; test_audit_saving.py::test_auto_load_with_a_missing_profile_runs_nothing_else | covered |
| S46 | Conditions through input modules (unclaimed neutral), stick plugged later works | test_input_state_claims.py::test_unclaimed_inputs_read_neutral; test_audit3_run_stop.py::test_a_condition_on_a_stick_plugged_in_later_works | covered |
| S47 | vJoy output only when claimed and present; else nothing, logged once per Run | test_output_layer.py::test_unclaimed_write_is_blocked_and_logged_once, ::test_claimed_output_the_driver_lacks_is_refused, ::test_claimed_write_reaches_the_driver; test_stage1_modules.py::test_a_blocked_output_is_logged_once_from_two_threads | covered |
| S48 | Unclaimed/missing vJoy reads neutral | test_output_layer.py::test_reads_of_unclaimed_outputs_are_neutral | covered |
| S49 | Only the output module opens vJoy | test_vjoy_writers_use_firewall.py::test_only_the_output_module_holds_the_vjoy_driver, ::test_map_to_vjoy_writes_through_the_output_module | covered |
| S50 | Scripts' vjoy object uses claimed outputs only | test_vjoy_writers_use_firewall.py::test_scripts_get_the_firewalled_vjoy | covered |
| S51 | Viewers/Home cards never open vJoy | test_output_layer.py::test_unopened_device_gives_nothing; test_batch2_b3.py::test_reading_a_vjoy_value_never_opens_the_device | covered |
| S52 | vJoy busy: message once per Run, log once, retry 3 s | test_device_fixes.py::test_busy_vjoy_is_told_once_and_retried_every_few_seconds, ::test_a_new_run_tells_again | covered |
| S53 | Output module saved while running applies at once (Q12) | test_audit3_run_stop.py::test_output_modules_saved_while_running_apply_at_once | covered |
| S54 | Idle held vJoy kept alive (60 s); none armed after release | test_batch3_C3a.py::test_the_output_module_keeps_a_held_vjoy_alive_and_stops_at_release, ::test_stop_ends_the_keep_alive_of_the_run, ::test_a_vjoy_written_lately_is_not_reset, ::test_a_vjoy_opened_on_another_thread_is_kept_alive_from_the_main_thread; plus batch 3 hands-on | covered |
| S55 | vJoy driver wording everywhere | test_final_06.py::test_the_vjoy_driver_check_has_one_wording; test_device_pack_import.py::test_opening_a_pack_says_the_vjoy_driver_is_missing (wording per D-02-Q17, see questions) | new |
| S56 | Xbox pass-through, no claims, old claim ignored | test_xbox_output_module.py::test_every_control_reaches_the_pad, ::test_an_old_xbox_claim_in_a_file_is_ignored, ::test_no_xbox_code_reads_a_claim | covered |
| S57 | Pad plugged on first Map to Xbox send, unplugged at Stop | test_stage1_runtime.py::test_the_xbox_pad_plugs_in_on_first_send_and_unplugs_at_stop | covered |
| S58 | Pad number from module name | test_xbox_output_module.py::test_pad_number_comes_from_the_name | covered |
| S59 | Trigger rests at 0; Full / Upper half ranges | test_map_to_xbox.py::test_trigger_range; test_map_to_xbox_inputs.py::test_button_on_a_trigger_is_full_or_nothing | covered |
| S60 | Viewer never plugs in a pad | test_final_06.py::test_a_viewer_never_plugs_in_an_xbox_pad; test_xbox_output_module.py::test_viewer_sees_every_control | new |
| S61 | Real Xbox controller never Gremlin's pad | test_xbox_pads_told_apart.py::test_real_xbox_pad_is_a_normal_device, ::test_the_pad_gremlin_plugs_in_is_its_own_and_remembered, ::test_a_device_arriving_later_is_not_taken | covered |
| S62 | No two pads for one number from two threads | test_device_fixes.py::test_two_threads_asking_for_a_pad_plug_in_one | covered |
| S63 | Failed Xbox write logged once, goes on | test_final_06.py::test_a_failed_xbox_write_is_logged_once_and_goes_on | new |
| S64 | ViGEmBus state, one wording everywhere | test_xbox_viewer_driver_check.py::test_ready, ::test_installed_but_not_running, ::test_a_missing_dll_says_so, ::test_not_installed_says_what_to_do, ::test_the_output_page_shows_the_same_check_at_its_top | covered |
| S65 | Macro default delay (not around Pause), Single/Count/Toggle/Hold | ai/test_macro.py::test_repeat, ::test_hat_count, ::test_hat_toggle, ::test_hat_hold | covered |
| S66 | Exclusive waits / blocks; Pre-Emptive pauses others | ai/test_macro.py::test_preemptive_exclusive_pauses_and_resumes_macro, ::test_non_preemptive_exclusive_waits_for_running_macro | covered |
| S67 | Hold macro released at once runs one round | test_action_fixes.py::test_a_hold_macro_released_at_once_stops | covered |
| S68 | Empty macro does nothing | test_crash_and_loss_fixes.py::test_an_empty_macro_does_nothing | covered |
| S69 | Failing step ends only its macro; stuck step ends waiters after 2 s | test_audit_runtime.py::test_a_failing_macro_step_blocks_nothing; test_audit3_run_stop.py::test_a_step_stuck_in_a_driver_ends_the_other_macros | covered |
| S70 | Key of a macro ended early released (fixed GL-048) | test_batch1_run_callers.py::test_a_macro_that_ends_early_lets_go_of_its_keys_at_once, ::test_a_macro_that_finishes_keeps_what_it_pressed_down; test_audit3_run_stop.py::test_a_macro_ending_early_lets_go_of_its_own_keys | covered |
| S71 | Map to Keyboard holds keys while held (modifiers first), releases on release | test_final_06.py::test_map_to_keyboard_puts_modifiers_first_and_releases_in_reverse; ai/test_map_to_keyboard.py::test_single_key, ::test_key_combination | new |
| S72 | Map to Mouse: click (wheel once per press) or move with speeds and direction | test_final_06.py::test_map_to_mouse_clicks_a_button_and_turns_the_wheel_once_per_press, ::test_map_to_mouse_moves_the_pointer_with_the_axis_in_its_direction; test_stage1_app_profile.py::test_map_to_mouse_from_a_hat_moves_and_stops | new |
| S73 | WAV/MP3/OGG at volume; Sequential / Interrupt / Overlap | test_stage1_runtime.py::test_sequential_sounds_wait_for_the_one_playing, ::test_interrupt_stops_the_sound_playing, ::test_overlap_plays_sounds_together. Hands-on for real decoding: one WAV, one MP3, one OGG Play Sound each, at 30% and 100%: each plays, quieter at 30% | covered |
| S74 | Missing sound file: profile opens, press plays nothing, unreadable logged once | test_play_sound_missing_file.py::test_pressing_with_a_missing_file_plays_nothing, ::test_missing_file_loads_and_is_kept; test_program_fixes.py::test_a_sound_that_cannot_be_decoded_is_logged_once | covered |
| S75 | Decoded off the event thread, finished freed | test_program_fixes.py::test_sounds_are_decoded_on_the_playback_thread, ::test_finished_sounds_are_let_go | covered |
| S76 | TTS voice from Options; Interrupt / Queue Front / Queue Back; volume 0–100% | test_stage1_runtime.py::test_speech_uses_the_options_voice_and_the_queue_modes; test_batch2_B5b.py::test_choosing_default_saves_no_voice_and_speaks_with_the_default. Hands-on for the shown volume: Text to Speech editor volume reads 0–100% | covered |
| S77 | Logical Device: Button/Axis/Hat N, fed by Map to Logical Device, own actions | test_logical_device.py::test_creation; test_logical_layout.py::test_system_name_stays_when_the_user_renames; test_logical_events_pass_gate.py::test_logical_device_events_reach_the_wire; ai/* (every action_interaction test sends through Logical inputs) | covered |
| S78 | Up to 180 at once, lowest free number, natural sort | test_logical_device.py::test_create_many_caps_at_180, ::test_index_reuse, ::test_labels_sorted_naturally | covered |
| S79 | Rename, hide system name, clear, group, move, sort; group names by capitals/spaces | test_logical_layout.py::test_system_name_stays_when_the_user_renames, ::test_hide_system_name_shows_only_the_typed_name, ::test_groups_and_order, ::test_group_as_moves_every_selected_row, ::test_drag_places_a_button_before_after_and_into_a_group, ::test_move_group_up_and_down, ::test_typed_group_name_joins_the_existing_group, ::test_rename_refuses_a_look_alike_but_allows_recasing_itself; test_logical_device.py::test_page_sorts_are_natural | covered |
| S80 | Assign Hardware: claimed controls of the same type (keys for buttons, OSC too), add/remove Map to Logical Device in the page's mode; vJoy output never a source | test_final_06.py::test_assign_hardware_lists_claimed_controls_of_the_same_type, ::test_assign_hardware_adds_and_removes_only_a_map_to_logical_device; test_logical_layout.py::test_named_vjoy_cannot_be_a_source_module | new |
| S81 | On to Xbox/vJoy only through the control's own actions, never Assign Hardware | test_final_06.py::test_assign_hardware_adds_and_removes_only_a_map_to_logical_device (only a Map to Logical Device on the source; nothing on the Logical control) | new |
| S82 | Logical page locked while running | test_batch2_b5a.py::test_logical_edits_are_refused_while_running, ::test_a_logical_pane_has_no_ok_while_running | covered |
| S83 | 50 Undo steps, dropped on profile load / mode delete, no step for nothing, failed step changes nothing | test_audit_editing.py::test_logical_steps_end_with_the_profile, ::test_a_logical_change_to_nothing_is_no_step; test_audit3_actions_undo.py::test_logical_undo_with_a_damaged_input_copy_changes_nothing | covered |
| S84 | Editor closes with notice when its mode is deleted; OK to the pane's mode | test_audit2_modes.py::test_logical_ok_goes_to_the_panes_own_mode | covered |
| S85 | Each Run starts with Logical values neutral (R1; fixed GL-050) | test_batch1_run_callers.py::test_logical_device_values_go_back_to_neutral | covered |
| Q1 | Logical values neutral at Stop | test_batch1_run_callers.py::test_logical_device_values_go_back_to_neutral | covered |
| Q2 | Release callbacks waiting at Stop dropped | test_stage1_runtime.py::test_release_callbacks_waiting_at_stop_are_dropped | covered |
| Q3 | Next Run: toolbar mode, temporary modes cleared | test_audit3_run_stop.py::test_the_mode_stack_starts_fresh_and_temporary_modes_end_with_stop | covered |
| Q4 | Script keys released only if sent during a Run | test_batch1_run_callers.py::test_a_key_a_script_holds_is_released_at_stop, ::test_keys_sent_with_no_run_on_are_left_alone; test_audit3_run_stop.py::test_keys_sent_with_no_run_are_not_tracked | covered |
| Q5 | Failed start runs Stop, one error, status Stopped | test_stage1_runtime.py::test_a_failed_start_then_run_again_handles_each_event_once, ::test_a_start_failing_late_leaves_the_runner_stopped, ::test_a_failed_run_shows_one_error_and_reads_stopped | covered |
| Q6 | Run asks "Save or discard the open action first?" with an editor open | Contract: test_batch2_b5a.py::test_each_pane_answers_close_action_panes[*]; test_batch3_C1.py::test_help_covers_run_asking_and_the_keyboard_draft. Hands-on: open an action on Configuration, Keyboard and Logical Device pages, change it, press Run (toolbar, then tray): the question shows; Save runs with the change, Discard runs without, Cancel stays stopped | hands-on |
| Q7 | Initial Values always written at Run via output module | as S8 | covered |
| Q8 | Sound and speech ignored with no Run | test_stage1_runtime.py::test_a_sound_queued_with_no_run_never_plays, ::test_speech_asked_for_with_no_run_is_ignored; test_batch1_run_callers.py::test_a_sound_asked_for_with_no_run_on_is_dropped, ::test_speech_asked_for_with_no_run_on_is_dropped; test_batch2_B5b.py::test_speech_arriving_after_stop_is_dropped | covered |
| Q9 | Keyboard/mouse straight to Windows; held tracked in one place | test_run_scope_only.py::test_send_key_down_is_keyboards_and_tracked, ::test_only_keyboard_and_sendinput_send_keys_to_windows | covered |
| Q10 | No auto-pause on a vJoy error | test_batch2_b2a_input_events.py::test_a_vjoy_error_in_an_action_does_not_pause | covered |
| Q11 | Paused shows "Running (Paused)"; Stop then Run un-paused | as S2, S37 | covered |
| Q12 | Output module changes apply at once | as S53 | covered |
| Q13 | Axis in range at Run: no press | as S39 | covered |
| Q14 | Macro Joystick step passes claimed controls only | test_batch2_B5b.py::test_a_macro_joystick_step_passes_only_claimed_controls; test_batch3_c4.py::test_a_macro_joystick_step_is_synthetic | covered |
| Q15 | No hidden Button 1; "Add a Logical Device control first" | test_batch1_run_callers.py::test_a_new_macro_step_on_an_empty_logical_device_creates_nothing; test_action_editor_fixes.py::test_a_logical_device_macro_step_on_an_empty_device_asks_for_a_control, ::test_a_logical_device_condition_on_an_empty_device_asks_for_a_control | covered |
| Q16 | Reads never open vJoy | test_batch2_b3.py::test_reading_a_vjoy_value_never_opens_the_device, ::test_reading_a_held_vjoy_gives_its_value | covered |
| Q17 | Map to vJoy relative loop ends with its Run | as S26; test_audit3_run_stop.py::test_a_loop_gets_its_run_and_ends_with_it | covered |
| Q18 | Unused second Logical Device writer removed | test_batch3_C3a.py::test_the_unused_logical_device_editing_model_is_gone | covered |
| Q19 | No Xbox pad outside a Run, ever | as S29, S30, S57; test_final_06.py::test_a_viewer_never_plugs_in_an_xbox_pad | covered |
| D-06-S39-NORELEASE | No release without a press | test_stage1_runtime.py::test_leaving_a_range_the_axis_started_in_sends_no_release; test_batch2_B5b.py::test_inside_at_run_then_leaving_sends_nothing_and_re_entering_presses | covered |
| D-06-STOP-MODE | After Stop the toolbar shows the last non-temporary mode; next Run in the toolbar mode | test_audit3_run_stop.py::test_the_mode_stack_starts_fresh_and_temporary_modes_end_with_stop | covered |

## Batch hands-on checks for this page (from `claude/catchup-test-plan.md`)

| Batch | Do | See |
|---|---|---|
| 1 (GL-047) | Map a button to Tempo (long press -> vJoy button). Hold it, press Stop before the long-press time | Nothing fires; the vJoy Viewer shows vJoy free |
| 1 (GL-063) | Run a profile that sends to vJoy and Xbox; quit (File > Exit) while running | No vJoy device held (vJoy Monitor idle), no Xbox pad left in Game Controllers |
| 2 (B1) | Edit an action in the pane, then Run from the tray | The Save / Discard question shows |
| 2 (B5a) | Open an action pane, Run | The pane shows read-only, "Profile running: stop it to edit" |
| 2 (B5b) | Text to Speech under a Tempo and inside a macro; on a keyboard key; Options voice "(default)" | Speech is heard in each case, with the chosen voice |
| 3 (C3a) | Run a profile holding vJoy, leave it idle over a minute; then Stop | vJoy stays alive while running; no keep-alive after Stop (vJoy free) |
| 3 (C4) | Relative axis on Map to vJoy and on Map to Logical Device; Stop and Run quickly | The axis moves while held; stops at Stop; the next Run starts clean |
| 3 (C1) | Module Setup while running | Says "Saved changes work at once." |

## Counts

106 rows: 85 statements (S1–S85), 19 decisions (Q1–Q19), 2 later decisions.
covered 92, new 12, hands-on 2 (S1, Q6), gap 0.
