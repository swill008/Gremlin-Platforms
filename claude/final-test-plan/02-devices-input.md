# Final test plan: 02 Devices and raw input

Spec: `claude/program-map/02-devices-input.md` (section 8, section 12: every
question decided as recommended) and `claude/decisions.md` (D-02-Q1..Q19).
New tests: `test/unit/test_final_02.py` (F02 below). Agent P02, 2026-10-06.

`U` = `test/unit/`, `J` = `test/journeys/`, `AI` = `test/action_interaction/`.
Short names: B2a = `U/test_batch2_b2a_input_events.py`, B2b =
`U/test_batch2_b2b.py`, C1 = `U/test_batch3_C1.py`, C2 = `U/test_batch3_C2.py`,
C3b = `U/test_batch3_C3b.py`, B4 = `U/test_batch2_b4.py`, ST1 =
`U/test_stage1_app_profile.py`, SR1 = `U/test_stage1_runtime.py`,
F02 = `U/test_final_02.py`.

## Section 8 statements

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | Physical devices first by name, then vJoy by number | F02::test_s1_s19_physical_by_name_then_vjoy_by_number_linked_by_counts | new |
| S2 | Own Xbox pads never listed; a real Xbox 360 pad is a device | U/test_xbox_pads_told_apart::test_real_xbox_pad_is_a_normal_device, ::test_the_pad_gremlin_plugs_in_is_its_own_and_remembered | covered |
| S3 | Home: one card per physical device, each vJoy, the Xbox controller | Hands-on: with two sticks, two vJoy devices and ViGEm installed, Home shows a card for each stick, "vJoy 1", "vJoy 2" and the Xbox controller; no card for an own Xbox pad. (Part: U/test_twin_devices::test_each_twin_has_its_own_card) | hands-on |
| S4 | One scan at start before the main window; failure window if it fails | F02::test_s4_a_failed_first_scan_shows_the_failure_window_not_the_main_one (app built off-screen in its own process) | new |
| S5 | Never wait more than 10 s for a busy scan | U/test_bounded_waits::test_a_busy_device_scan_is_reported_not_waited_for | covered |
| S6 | Scan lock always released | U/test_device_scan::test_a_scan_error_does_not_leave_the_lock_held | covered |
| S7 | Failed hot-plug update shown in the error dialog | U/test_device_scan::test_hot_plug_error_is_shown_not_lost | covered |
| S8 | Same ids: no vJoy reset, no reload | U/test_device_scan::test_nothing_changed_resets_nothing | covered |
| S9 | Device Information lists every device Windows reports (with D-02-Q6) | B2b::test_device_information_lists_left_out_vjoy_and_own_xbox_pads | covered |
| S10 | Input labels from device_db.json by VID/PID when Options asks | F02::test_s10_input_labels_come_from_the_device_database_by_vid_pid; ST1::test_a_missing_device_database_gives_plain_names, ::test_a_damaged_device_database_gives_plain_names | new |
| S11 | Second identical device "<name> (2)", third "(3)" | U/test_twin_devices::test_the_second_identical_device_gets_its_own_name; J/test_j04_twin_sticks | covered |
| S12 | The device the "<name>" file is bound to keeps the plain name | U/test_twin_devices::test_the_device_the_file_is_bound_to_keeps_the_plain_name | covered |
| S13 | Twin names kept by device id, every session and port | B2b::test_a_matching_twin_name_is_kept_when_the_stick_is_alone, ::test_twin_names_from_the_hot_plug_thread_are_written_on_the_main_thread; J/test_j04_twin_sticks | covered |
| S14 | A device with no twin is not renamed | U/test_twin_devices::test_a_single_device_is_not_renamed | covered |
| S15 | A stored twin name kept when that stick is alone | B2b::test_a_matching_twin_name_is_kept_when_the_stick_is_alone | covered |
| S16 | Stored twin name vs a changed driver name (D-02-Q3 wins: dropped) | B2b::test_a_stale_twin_name_is_dropped | covered |
| S17 | Shown (twin) name in labels and pairing | U/test_twin_devices::test_labels_use_the_shown_name; B2b::test_one_shown_name_twin_vjoy_number_and_alias; C3b::test_input_monitor_and_pairing_show_the_shown_name | covered |
| S18 | Profiles unaffected by twin names (device ids) | J/test_j04_twin_sticks::test_run_passes_each_twins_own_checked_buttons | covered |
| S19 | vJoy number linked to its DirectInput device by counts | F02::test_s1_s19_physical_by_name_then_vjoy_by_number_linked_by_counts; U/test_startup_messages::test_a_vjoy_windows_doesnt_list_is_left_out_the_rest_work | new |
| S20 | Problem vJoy left out, the rest work | U/test_startup_messages::test_discrete_hats_leave_that_vjoy_out, ::test_a_vjoy_windows_doesnt_list_is_left_out_the_rest_work, ::test_vjoy_devices_alike_are_both_left_out, ::test_alike_but_only_one_listed_is_not_guessed | covered |
| S21 | Told once after the main window is up, again only on change | U/test_startup_messages::test_told_once_then_again_only_when_it_changes | covered |
| S22 | Each left-out vJoy logged as an error, also with logs Off | F02::test_s22_a_left_out_vjoy_is_logged_as_an_error_with_logs_off; U/test_startup_messages::test_logs_off_still_keeps_errors_in_system_log | new |
| S23 | vJoy released only at start / when vJoy set changed | U/test_device_scan::test_plugging_in_a_stick_does_not_reset_vjoy, ::test_a_vjoy_change_still_resets_vjoy | covered |
| S24 | vJoy asked only through the output module | U/test_cleanup_batch_a::test_layer_rule_no_direct_hardware_reads | covered |
| S25 | 0.2 s after the last plug event, one rescan | F02::test_s25_several_plug_events_cause_one_update_after_0_2_s | new |
| S26 | Plug events of own Xbox pads ignored | F02::test_s26_plug_events_of_the_programs_own_xbox_pads_are_ignored | new |
| S27 | "Devices changed" only when the visible list changed | F02::test_s27_devices_changed_is_said_only_when_the_list_changed | new |
| S28 | Unplug lets go of buttons and hats; axes stay | U/test_device_reconnect::test_held_inputs_are_let_go_on_unplug | covered |
| S29 | Reconnect: every screen reads the stick | U/test_device_reconnect::test_screens_set_while_unplugged_read_the_stick_when_it_connects | covered |
| S30 | Module Setup Save refused while unplugged | U/test_device_reconnect::test_unplugging_keeps_what_is_shown_and_refuses_save | covered |
| S31 | Stick plugged in during a Run gets its claims, also with Ignore | U/test_device_fixes::test_input_modules_reload_when_a_device_is_plugged_in | covered |
| S32 | Device change behavior Reload / Ignore / Disable(Stop) | SR1::test_device_change_follows_the_option | covered |
| S33 | Selected device gone: first physical device, or Logical tab | F02::test_s33_the_page_moves_off_a_device_that_disappeared | new |
| S34 | HidHide list re-reads on a device change | U/test_device_reconnect::test_hidhide_rereads_its_list; B2b::test_hidhide_stops_reloading_when_its_window_is_closed | covered |
| S35 | Auto Mapper keeps its ticks | U/test_device_reconnect::test_auto_mapper_keeps_its_ticks | covered |
| S36 | Failed update during play: error shown, old list stays | F02::test_s36_a_failed_update_is_shown_and_the_old_list_stays | new |
| S37 | Calibration applied before any action sees the axis | F02::test_s37_the_axis_calibration_is_applied_before_anything_sees_it | new |
| S38 | No calibration: default centred, logged once per axis at Info | F02::test_s38_an_axis_without_calibration_is_centred_and_logged_once | new |
| S39 | Calibration reloaded at each scan, and one axis after a save | F02::test_s39_calibration_is_reloaded_at_each_scan_and_for_one_saved_axis | new |
| S40 | Event stamped with the mode current when it arrives (D-02-Q8) | F02::test_s40_an_event_keeps_the_mode_current_when_it_arrives — **xfail FINAL-02-1** (code stamps at handling, GL-065) | new |
| S41 | Last value of every stick input kept | F02::test_s41_the_last_value_of_every_stick_input_is_kept; B2a::test_an_axis_not_yet_seen_is_read_from_the_driver | new |
| S42 | Refresh axes on Run (and mode change when on) | U/test_mode_refresh_and_add_key::test_runner_refreshes_axes_on_mode_change_only_while_listening; SR1::test_the_physical_refresh_comes_after_the_initial_values | covered |
| S43 | Unclaimed input reads neutral | U/test_input_state_claims::test_unclaimed_inputs_read_neutral | covered |
| S44 | Only the allowed listeners read raw events | U/test_raw_input_listeners::test_raw_hardware_listeners_are_only_the_allowed_ones, ::test_viewers_and_live_values_use_the_claimed_feed | covered |
| S45 | Every key seen; Windows and games get every event | ST1::test_keyboard_hook_reports_keys_and_passes_every_event_on; B2a::test_a_failing_key_callback_still_passes_the_key_on | covered |
| S46 | One press per hold, and the release | ST1::test_a_held_key_is_one_press_and_one_release; B2a::test_a_press_after_a_lost_release_is_a_new_press | covered |
| S47 | AltGr is Right Alt, not Right Alt + Ctrl | ST1::test_keyboard_hook_reports_keys_and_passes_every_event_on (AltGr's extra Ctrl dropped) | covered |
| S48 | Key bindings only for claimed keys; no saved choice = all; empty = none | U/test_keyboard_gate::test_no_saved_keyboard_claim_passes_every_key, ::test_claimed_key_passes_and_unclaimed_key_does_not; U/test_audit_devices::test_keyboard_saved_with_no_keys_passes_none | covered |
| S49 | Extended keys told apart | U/test_keyboard_gate::test_key_id_packs_the_extended_flag; ST1::test_key_tables | covered |
| S50 | Program's own keys (D-02-Q4 wins: ignored while running) | B2a::test_the_hook_marks_the_programs_own_keys, ::test_keys_the_program_sends_carry_the_mark, ::test_own_keys_are_ignored_while_a_run_is_on | covered |
| S51 | Mouse hooked only while Listen / Record ask for it | F02::test_s51_the_mouse_is_hooked_only_while_listen_asks_for_it; B2a::test_a_listen_closed_early_lets_go_of_the_mouse_hook, ::test_listen_ending_does_not_cut_off_a_mouse_recording | new |
| S52 | Mouse buttons press/release, wheel as one press | ST1::test_mouse_hook_reports_buttons_and_the_wheel | covered |
| S53 | Mouse buttons can't be bound (D-02-Q5) | Hands-on: Run a profile, click left/right/middle/back/forward and turn the wheel: no action fires, Live log shows no input. Help text: C1::test_help_says_mouse_buttons_cant_fire_actions | hands-on |
| S54 | Every action of the input runs; child mode uses parent's | F02::test_s54_a_child_mode_uses_its_parents_actions_for_empty_inputs | new |
| S55 | One failing action doesn't stop the others | U/test_audit_runtime::test_one_failing_action_does_not_stop_the_others | covered |
| S56 | vJoy error logged, no box, no pause | B2a::test_a_vjoy_error_in_an_action_does_not_pause | covered |
| S57 | While paused only "always execute" runs | U/test_action_fixes::test_while_paused_a_script_callback_does_not_stop_the_rest; AI/test_pause_resume | covered |
| S58 | Change Mode to an unknown mode ignored, logged once | U/test_audit2_modes::test_the_running_mode_list_follows | covered |
| S59 | Rename while running moves actions; delete drops them | F02::test_s59_renaming_a_running_mode_moves_its_actions_deleting_drops_them; U/test_audit2_modes::test_the_running_mode_list_follows | new |
| S60 | Stop removes every action and the running mode list | F02::test_s60_stop_removes_every_action_and_the_running_mode_list | new |
| S61 | Listen ends at first press / first release after presses | ST1::test_listen_single_input_ends_at_the_first_press, ::test_listen_several_inputs_ends_at_the_first_release | covered |
| S62 | Axis only after a big move; hat off centre; wheel at once | F02::test_s62_listen_takes_an_axis_only_after_a_big_enough_move; ST1::test_listen_ignores_logical_and_virtual_inputs_and_a_centred_hat, ::test_listen_takes_the_mouse_wheel_at_once | new |
| S63 | Listen ignores Logical Device and virtual buttons | ST1::test_listen_ignores_logical_and_virtual_inputs_and_a_centred_hat; B2a::test_listen_ignores_vjoy_and_own_xbox_pads; C3b::test_listen_ignores_events_the_program_made | covered |
| S64 | Esc held 1 s cancels Listen (D-02-Q9: tap never does) | ST1::test_holding_esc_cancels_listen; B2a::test_a_short_esc_tap_does_not_cancel_listen, ::test_holding_esc_cancels_listen_on_the_main_thread, ::test_an_esc_tap_is_the_input_when_keys_are_listened_for | covered |
| S65 | Highlighting pauses during Listen and macro recording | F02::test_s65_highlighting_pauses_while_a_macro_records; ST1::test_listen_single_input_ends_at_the_first_press | new |
| S66 | HidHide hides sticks from games; the program still sees them | Hands-on (real driver): control on, HidHide Enabled, tick a stick; Test HidHide (joy.cpl) no longer lists it; Gremlin-Platforms still reacts to it | hands-on |
| S67 | Not shipped; Get HidHide opens Nefarius releases; "HidHide is not installed" | F02::test_s67_s77_get_hidhide_and_test_hidhide_open_the_right_places. Hands-on: on a PC without HidHide the window says "HidHide is not installed" | new |
| S68 | Nothing changed until "Gremlin-Platforms controls HidHide" is on | F02::test_s68_nothing_changes_in_hidhide_until_the_program_controls_it. Hands-on: the note under the switch says why the settings can't be changed | new |
| S69 | Control off leaves HidHide as it is | F02::test_s69_turning_control_off_leaves_hidhide_as_it_is | new |
| S70 | HidHide Enabled refused: switch flips back, error shown | F02::test_s70_hidhide_enabled_flips_back_with_the_error_when_refused | new |
| S71 | Automatically Start: control on, Enabled on, saved lists written | F02::test_s71_automatically_start_takes_control_turns_on_and_writes_the_lists, ::test_s71_with_automatically_start_off_nothing_is_written | new |
| S72 | Every switch off on a new install; hides nothing | F02::test_s72_a_new_install_has_every_switch_off_and_hides_nothing | new |
| S73 | Ticking hides every interface of the USB parent | U/test_hidhide_group::test_nxt_interfaces_share_usb_parent_group, ::test_no_parent_does_not_merge_whole_vendor, ::test_different_usb_parents_stay_apart | covered |
| S74 | Hidden device dimmed and marked HIDDEN | F02::test_s74_a_device_hidden_in_the_driver_is_marked_hidden (model). Hands-on: the row is dimmed and says HIDDEN | new |
| S75 | "Gaming devices only" shortens the list | F02::test_s75_gaming_devices_only_asks_for_game_controllers | new |
| S76 | Allow list adds the program; Block list never blocks it | F02::test_s76_allow_list_adds_the_program_block_list_never_blocks_it | new |
| S77 | "Test HidHide" opens Windows Game Controllers | F02::test_s67_s77_get_hidhide_and_test_hidhide_open_the_right_places | new |
| S78 | A setting that can't be saved shows in the window | F02::test_s78_a_setting_that_cant_be_saved_shows_in_the_window | new |
| S79 | HidHide messages to the system log; missing driver = warning | U/test_hidhide_log::test_messages_reach_the_system_log, ::test_missing_driver_at_start_is_a_warning | covered |
| S80 | Off-screen run never changes HidHide | U/test_audit3_startup::test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray | covered |
| S81 | Programs sorted by name; devices by name then id | U/test_hidhide_group::test_saved_programs_load_sorted, ::test_devices_sort_by_name_then_id | covered |
| S82 | Device picture used where picked; gone = no picture | U/test_cleanup_batch_a::test_a_picked_photo_is_used_where_it_is, ::test_a_card_shows_the_pick_blank_when_gone_else_the_module | covered |
| S83 | HidHide choices in History; window size, split, links not | F02::test_s83_hidhide_choices_are_in_history_window_size_and_links_are_not; U/test_audit_saving::test_hidhide_picture_links_are_not_a_user_change | new |
| S84 | Auto-load loads and runs the program's profile | F02::test_s84_auto_load_loads_and_runs_the_programs_profile; B4::test_auto_load_hears_the_program_in_front_at_start | new |
| S85 | Non-ASCII program paths read in full | U/test_audit_runtime::test_the_program_path_is_read_in_full | covered |
| S86 | Unreadable program not announced as the previous one | F02::test_s86_a_program_that_cant_be_read_is_not_announced | new |
| S87 | Own profile's program again: no reload | U/test_audit_saving::test_auto_load_leaves_the_open_profile_alone | covered |
| S88 | Never switch over unsaved edits; said once | U/test_autoload_and_mode_prompts::test_auto_load_waits_for_unsaved_edits; B4::test_auto_load_held_by_unsaved_edits_stops_the_open_profile | covered |
| S89 | Missing profile: said once, open one stops | U/test_audit2_saving::test_a_missing_auto_load_profile_stops_the_open_one; U/test_audit_saving::test_auto_load_with_a_missing_profile_runs_nothing_else | covered |
| S90 | Program with no profile: Run stops unless Keep running | SR1::test_auto_load_stops_on_focus_loss_unless_kept_running | covered |
| S91 | Tests / off-screen never install a hook | U/test_bounded_waits::test_with_hooks_turned_off_none_is_installed; U/test_audit3_startup::test_main_turns_the_hooks_off_before_the_app_starts | covered |
| S92 | Hook stopped right after starting doesn't hang | U/test_threads::test_a_hook_stopped_right_after_starting_does_not_hang | covered |
| S93 | Exit stops hooks, hot-plug timer, DLL callbacks, process monitor | F02::test_s93_the_listener_stops_its_timer_hooks_and_driver_callbacks, ::test_s93_exit_stops_the_listener_the_run_and_the_process_monitor; U/test_audit3_run_stop::test_quitting_stops_once_and_makes_nothing_to_stop_it; C3b::test_hook_stop_waits_on_the_program_clock | new |
| S94 | "Device id" on screen (D-02-Q12: "Device ID") | C1::test_device_information_says_device_id | covered |

## Decisions that state behaviour (section 12, D-02-*)

| Ref | Decision (short) | Check | Status |
|---|---|---|---|
| Q1 | "vJoy as input" tick never stops or restarts a Run | B4::test_vjoy_behavior_switch_sends_no_device_change | covered |
| Q2 | Device change behavior shows "Stop" (stores Disable) | C2::test_device_change_behavior_shows_stop_and_stores_disable, ::test_device_change_behavior_description_names_stop; C1::test_help_says_stop_for_device_change_behavior | covered |
| Q3 | Stale twin names dropped | B2b::test_a_stale_twin_name_is_dropped | covered |
| Q4 | Program's own keys ignored while running | B2a::test_own_keys_are_ignored_while_a_run_is_on; C3b::test_macro_recording_ignores_events_the_program_made | covered |
| Q5 | Mouse is Listen/Record only; dead injected filter gone | C3b::test_mouse_events_carry_the_keyboard_uuid_and_are_never_dropped; C1::test_help_says_mouse_buttons_cant_fire_actions | covered |
| Q6 | Device Information lists left-out vJoy and own Xbox pads | B2b::test_device_information_lists_left_out_vjoy_and_own_xbox_pads | covered |
| Q7 | Unseen axis read from the driver at Run | B2a::test_an_axis_not_yet_seen_is_read_from_the_driver; hands-on (batch 2): throttle at 80% before Run | covered |
| Q8 | Event keeps the mode of its arrival | F02::test_s40_an_event_keeps_the_mode_current_when_it_arrives — xfail FINAL-02-1 | new |
| Q9 | Listen cancelled only by a 1 s Esc hold | B2a::test_a_short_esc_tap_does_not_cancel_listen | covered |
| Q10 | HidHide driver client outside the UI | C3b::test_hidhide_driver_calls_live_outside_the_ui, ::test_hidhide_driver_writes_the_block_list_through_its_control_device | covered |
| Q11 | Xbox package reads devices only through modules/hardware.py | C3b::test_xbox_package_reads_devices_through_the_hardware_door, ::test_own_pads_list_devices_through_the_hardware_door | covered |
| Q12 | "Device ID" in Device Information | C1::test_device_information_says_device_id | covered |
| Q13 | Applying lists overwrites HidHide's; the window says so | C1::test_hidhide_window_and_developer_notes | covered |
| Q14 | Device tick saved only after the driver accepts | B2b::test_a_hidhide_tick_the_driver_refuses_is_not_saved; C3b::test_a_refused_hidhide_tick_shows_the_driver_error | covered |
| Q15 | python.exe in Allow list noted for developers | C1::test_hidhide_window_and_developer_notes | covered |
| Q16 | One "Automatically Start" switch; Options points to it | U/test_batch2_B5b::test_options_no_longer_show_the_hidhide_switch_but_point_to_it | covered |
| Q17 | "Then restart the program." | C3b::test_vjoy_left_out_message_says_restart_the_program | covered |
| Q18 | Own window in front is no change for auto-load | B4::test_focusing_the_program_itself_keeps_the_run | covered |
| Q19 | Process monitor only while auto-load is on | C2::test_the_process_monitor_runs_only_while_auto_load_is_on, ::test_the_process_monitor_restarts_with_one_loop | covered |

## Hands-on checks (from the batch plans, page 02)

| From | What to do | What to see |
|---|---|---|
| B2a (GL-122, Q7) | Set a throttle at about 80 %, start the program, Run without moving it | vJoy Viewer shows the throttle at about 80 %, not centre. First confirm whether dill.dll already sends starting values |
| B2a | Keep the program busy (open a large profile) and type in another program | keys reach the other program at once |
| B2a (G17) | Hold a bound key, press Ctrl+Alt+Del, Esc back, press the key again | the binding fires on that press |
| B2a (Q4) | Map key A to send key B; bind key B to something else; Run, press A | the B binding does not fire |
| B2b | Plug and unplug a stick with the HidHide window open, then closed | the list follows while open; no delay or freeze with it closed |
| B2b (Q6) | Device Information with a left-out vJoy (discrete hats) and an own Xbox pad plugged in | both listed, marked "left out (see message)" and "Gremlin's Xbox pad" |
| B2b | Calibration on a stick whose module claims only some axes | unclaimed axes listed with "(not claimed)" |
| C3b | Listen for mouse buttons (Keyboard page / Script settings), and macro Record with mouse | each button and the wheel is caught; ending one doesn't cut off the other |
| C3b | HidHide window with the real driver: control on, Enabled, tick a stick, Allow and Block list | joy.cpl (Test HidHide) hides the stick; the program still sees it |
| C3b | Run a profile with an Xbox output so the program plugs in its pad | no device change, no reload, Steam does not flap |
| C3b | Give a stick an alias, open Live Log Reader Input Monitor, move it | the alias is shown |
| C1 | HidHide window at 100 % UI scale | no scrollbar |
| S3 | Home with sticks, vJoy devices and ViGEm | one card per device as in S3 |
| S53 | Run, click every mouse button and the wheel | nothing fires |
| S66, S67, S68, S74 | HidHide window text and look | see the rows above |
