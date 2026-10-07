# Final test plan: 01 App shell and settings

Spec: `claude/program-map/01-app-shell.md` (section 8, S1-S131; section 12: every
Q decided as recommended, D-01-Q1..Q16 in `claude/decisions.md`).
New tests: `test/unit/test_final_01.py` (named `test_s<n>_...`). Two of them start
the real app off-screen in their own process (`main_window` fixture and the
failure page). "file::test" below is under `test/unit/` unless it says otherwise.

Status: `covered` (existing test), `new` (written in this phase), `hands-on`,
`gap`. Where a row has an automatic part and a part only a person can see, the
status is the automatic one and the Check says what to do by hand.

## Section 8 statements

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | Ignore Windows scaling is read from the settings file before Qt | test_final_01::test_s1_s2_windows_scaling_is_read_from_the_settings_file_before_qt (real reader, file says true); also test_user_data_folder::test_startup_scaling_check_reads_the_same_folder | new |
| S2 | Missing or unreadable file: Windows scaling on | test_final_01::test_s1_s2_... (no file, bad JSON, no key, "False") | new |
| S3 | Restart gives the launch scaling environment back | test_final_01::test_s3_s78_s81_restart_after_the_usual_quit_order_with_the_launch_scaling. Hands-on: Options → Interface → Ignore Windows display scaling on → Restart: the program comes back unscaled; off → Restart: scaled again | new |
| S4 | Fixed module order; every module imports alone | test_program_imports.py, test_modules_import_alone.py | covered |
| S5 | User folder and every data sub-folder made at start | test_final_01::test_s5_the_data_folders_are_made_at_start (real app, all 8 folders) | new |
| S6 | Every setting registered before the purge | test_startup_settings_kept::test_window_and_tab_settings_survive_purge, ::test_startup_registration_keeps_them; test_batch2_B1::test_settings_registered_later_are_registered_before_the_purge | covered |
| S7 | --profile relative to the start folder | test_program_fixes::test_a_relative_profile_is_read_from_where_the_program_started | covered |
| S8 | Missing --profile: "Profile not found.", last profile opens | test_program_fixes::test_a_missing_profile_is_told_and_the_last_one_opens; test_batch3_C2::test_missing_profile_with_a_last_profile_says_it_was_opened, ::test_missing_profile_with_no_last_profile_says_a_new_one_is_open | covered |
| S9 | No --profile: last profile; failure → empty profile + Forget It / Keep | test_startup_messages::test_a_last_profile_that_wont_open_is_offered_to_forget, ::test_forget_takes_it_off_the_start_and_recent_lists | covered |
| S10 | --enable runs after load; --start-minimized minimizes (tray when on) | test_final_01::test_s10_enable_runs_after_the_profile_loads_and_start_minimized_minimizes; minimize → tray: test_stage1_app_profile::test_minimize_to_tray_hides_on_minimize_and_close. Hands-on: `gremlin_platforms.exe --enable --start-minimized` with Minimize to tray on: no window, tray icon shows running | new |
| S11 | Update check, Settings Reset, vJoy message each at most once | test_settings_file_damage::test_unreadable_file_is_kept_aside_and_announced_once; test_startup_messages::test_told_once_then_again_only_when_it_changes. Hands-on (update part): with a newer release on GitHub and Check for updates on, start once: one Update window, no second one | covered |
| S12 | Driver can't start: failure page with the reason and a button that quits | test_final_01::test_s12_a_driver_that_cannot_start_shows_the_failure_page (real app, own process). The button reads "OK" (see questions) | new |
| S13 | Broken user plugin left out, never replaces a built-in | test_audit2_startup_devices::test_a_bad_user_plugin_is_left_out_entirely; test_audit3_startup::test_a_user_plugin_cant_replace_a_built_in_qml_element | covered |
| S14 | Could-not-start box: reason, error lines, logs folder, Ctrl+C; logged; process ends | test_could_not_start::test_main_tells_the_user_and_ends_when_starting_fails, ::test_message_names_the_reason_the_error_and_the_logs | covered |
| S15 | Main window that fails to load: QML errors reported | test_could_not_start::test_broken_main_window_raises_with_the_qml_errors | covered |
| S16 | The box also covers module loading and user-folder creation | test_batch2_B1::test_a_failure_while_the_modules_load_is_shown_and_logged; test_final_01::test_s16_a_user_folder_that_cannot_be_made_is_told_with_the_box | new |
| S17 | Clean start: no process scan, no question | test_program_fixes::test_a_clean_start_runs_no_process_scan; test_second_copy_detection::test_main_alone_does_not_ask | covered |
| S18 | Second copy: Yes / No / Cancel | test_second_copy_detection::test_main_cancel_does_not_start, ::test_main_close_others_closes_then_takes_the_lock, ::test_main_continue_starts_without_closing | covered |
| S19 | Recognises both exe names and Python running the script; never itself | test_second_copy_detection::test_installed_and_older_exe_count_as_gremlin, ::test_starting_copy_never_finds_itself, ::test_python_counts_only_when_running_gremlin | covered |
| S20 | No: starts without the lock (two copies allowed) | test_second_copy_detection::test_main_continue_starts_without_closing | covered |
| S21 | Off-screen: no hooks, boxes, closing others, HidHide, tray | test_audit3_startup::test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray, ::test_off_screen_another_process_is_never_closed, ::test_off_screen_a_message_box_is_logged_and_answers_cancel | covered |
| S22 | Off-screen decided by Qt's platform / -platform / QT_QPA_PLATFORM | test_audit3_startup::test_before_qt_the_platform_argument_wins, ::test_once_qt_runs_its_platform_decides, ::test_before_qt_the_platform_part_of_the_variable_decides | covered |
| S23 | Tests and off-screen checks never reach GitHub | test_final_01::test_s23_an_offline_run_never_reaches_github (no request is made) | new |
| S24 | configuration.json stays in %USERPROFILE%\Gremlin Platforms when the data folder moves | test_final_01::test_s24_settings_stay_in_the_profile_folder_when_the_data_folder_moves | new |
| S25 | One unreadable setting falls back; others kept | test_settings_file_damage::test_bad_settings_fall_back_and_good_ones_are_kept | covered |
| S26 | Unreadable file kept as .bad-<time>, told once | test_settings_file_damage::test_unreadable_file_is_kept_aside_and_announced_once | covered |
| S27 | Empty file = no settings | test_settings_file_damage::test_empty_file_is_like_no_file | covered |
| S28 | Bad value never hangs; file read once | test_settings_file_damage::test_bad_value_does_not_hang_start_up, ::test_settings_are_read_once_before_the_application_runs | covered |
| S29 | Temp file + swap; folder made if missing | test_settings_file_damage::test_saving_creates_the_settings_folder | covered |
| S30 | One write ~1 s after the last; all flushed on quit/restart/install/re-read | test_write_less::test_many_settings_changes_make_one_write, ::test_deferred_write_runs_once_and_on_flush; test_audit2_coverage::test_quit_to_install_saves_the_pending_update_first; test_final_01::test_s3_s78_s81_... (flush after exec) | covered |
| S31 | No Qt app: written at once | test_write_less::test_without_qt_a_write_happens_at_once | covered |
| S32 | Unchanged value not written; list edited in place saved | test_write_less::test_unchanged_auto_load_list_is_not_saved; test_config::test_list_edited_in_place_is_saved | covered |
| S33 | Settings version: older keeps, same/newer removes retired | test_settings_versions::test_an_older_version_keeps_a_newer_versions_settings, ::test_the_same_or_a_newer_version_removes_retired_settings | covered |
| S34 | User-chosen settings go to History with Options names | test_audit2_options_text::test_history_names_settings_as_options_does | covered |
| S35 | First appearance is not a History change | test_batch2_B1::test_a_change_before_a_new_settings_first_save_is_a_history_entry (only the changed key, not the new one) | covered |
| S36 | Activity lines before the app runs are kept | test_settings_file_damage::test_activity_lines_before_the_application_runs_are_kept | covered |
| S37 | Old Close to tray on → Minimize to tray on; old key dropped | test_final_01::test_s37_close_to_tray_becomes_minimize_to_tray_then_is_dropped | new |
| S38 | Unwritable settings file never stops quit or install | test_audit2_saving::test_quit_to_install_carries_on_when_settings_cannot_be_saved; test_batch2_B1::test_a_settings_file_that_cannot_be_written_is_told_once | covered |
| S39 | One Options window (toolbar, menu, Button Map) | test_final_01::test_s39_s49_one_options_window_and_closing_it_announces_changes (toolbar twice + menu: 1 window). The Button Map no longer opens the program's Options (its own Button Map Options panel instead), so the "from the Button Map" part has nothing to check (question 3) | new |
| S40 | Sidebar: General, Interface, Actions, Profiles, Home, OSC, Folders | test_final_01::test_s40_options_sidebar_sections | new |
| S41 | Every setting once; Other; action-priorities hidden; Button Map apart | test_options_layout::test_every_setting_shows_once_and_button_map_is_apart | covered |
| S42 | General and Actions groups | test_options_layout::test_history_settings_have_their_own_group; test_audit2_options_text::test_action_settings_have_their_own_group | covered |
| S43 | Search by name, description, group title; "Other" matches nothing | test_audit3_screens::test_options_search_does_not_match_other. Hands-on: type "tray" (name), "slider" (description), "Diagnostics" (group): each shows its rows in every section | covered |
| S44 | Switches/numbers/drop-downs take effect at once; text fields on leave/Enter/close | test_final_01::test_s44_a_switch_is_saved_and_announced_when_changed. Hands-on: OSC → Connection, edit Input host, press Tab: saved (reopen Options); edit again and close the window without leaving the field: saved | new |
| S45 | Real row names, US group spelling | test_final_01::test_s45_rows_have_real_names_and_groups_us_spelling | new |
| S46 | Folder rows: Select opens at the current folder; Reset puts the default back | hands-on: Options → Folders → Profiles folder → Select: picker opens in the current folder, titled by what it does ("Choose Profiles Folder"); Reset: row shows the default inside the data folder | hands-on |
| S47 | Options' History button opens History filtered to settings | hands-on: Options → History: History opens showing only settings entries | hands-on |
| S48 | Escape closes Options; size remembered; never larger than the screen | test_usability_fixes::test_escape_closes_the_tool_windows (Options included); test_tool_windows_fit.py. Hands-on: resize Options, close, reopen: same size | covered |
| S49 | Closing Options says settings changed | test_final_01::test_s39_s49_... (configChanged on close, window gone) | new |
| S50 | Ignore Windows scaling asks Restart / Later / Cancel | hands-on (W-11, OPT-U02): tick it → box Restart / Later / Cancel; Cancel: switch back off, nothing saved; Later: saved, no restart; Restart: usual quit questions then the program starts again. Restart path: test_stage1_app_profile::test_restart_quits_the_usual_way_and_a_cancel_clears_it | hands-on |
| S51 | UI scale slider off while Windows scaling on; applies on release | test_ui_scale::test_windows_scaling_on_ignores_slider, ::test_windows_scaling_off_uses_slider. Hands-on (OPT-U06): drag the slider: the program resizes on release only | covered |
| S52 | Dark mode applies at once on every window | hands-on (OPT-U01): open the vJoy Viewer and Options, flip Dark mode: both windows and the main window change at once | hands-on |
| S53 | Add Action Menu: tick, drag within kind, "X of Y", Reset to Default, saved | test_options_layout::test_move_among_keeps_other_kinds_in_place; test_option_list_saving::test_action_order_move_is_saved, ::test_action_order_drops_land_where_shown | covered |
| S54 | Auto-load rows saved at once | test_option_list_saving::test_auto_loading_new_entry_and_remove_are_saved | covered |
| S55 | Diagnostic logs: one setting in Options and the Live Log Reader | test_final_01::test_s55_one_diagnostic_logs_setting_for_options_and_the_live_log_reader | new |
| S56 | Logs Off still keeps errors in system.log | test_startup_messages::test_logs_off_still_keeps_errors_in_system_log | covered |
| S57 | Title "* name - Gremlin-Platforms R1", Untitled before first save | test_final_01::test_s57_the_title_names_the_profile_and_marks_unsaved_changes (real window). Hands-on: save as flight.xml: title "flight.xml - Gremlin-Platforms R1" | new |
| S58 | Toolbar order and names | test_final_01::test_s58_s59_s61_the_toolbar | new |
| S59 | Run, and Stop (accent) while running | test_final_01::test_s58_s59_s61_the_toolbar (Run while stopped). Hands-on: press Run: the button reads Stop in the accent color; press again: Run | new |
| S60 | vJoy / Xbox Viewer buttons open or close the viewer | test_final_01::test_s60_the_vjoy_viewer_button_opens_and_closes_it (vJoy Viewer; the Xbox button uses the same toggle) | new |
| S61 | Home and Logical Device in accent while their page shows | test_final_01::test_s58_s59_s61_the_toolbar (Home at start, Logical not). Hands-on (TB-05): press Logical Device: its button turns accent, Home's doesn't | new |
| S62 | Narrow window: captions hide, then Mode list narrows, then scroll | test_main_window_fits.py (4 tests) | covered |
| S63 | Mode list = edited and running mode; follows changes; never blank | test_stage1_app_profile::test_load_puts_the_toolbar_in_the_new_profiles_startup_mode, ::test_new_puts_the_toolbar_in_default, ::test_select_mode. Hands-on (F-01b): New, Load, Save As: the Mode box always shows a mode | covered |
| S64 | Footer: Running/Stopped, (Paused), (unsaved changes); last save line with tooltip | test_stage1_runtime::test_the_status_bar_says_running_paused; test_final_01::test_s64_the_footer_while_stopped. Hands-on: save, hover the save line: tooltip shows the full text | covered |
| S65 | Menus from one command list with the listed items | test_final_01::test_s65_s66_s67_menus_come_from_the_command_list (menus as built); test_menus::test_every_main_command_is_in_the_menu_bar | new |
| S66 | Menus show only what can be used now | test_final_01::test_s65_s66_s67_... (View → Home hidden on Home, Recent hidden with no recent profile) | new |
| S67 | Shortcuts Ctrl+N/O/S/Shift+S/K, F1, shown beside commands | test_final_01::test_s65_s66_s67_... (bound shortcuts and the menu hints) | new |
| S68 | Palette lists usable commands, word search, Up/Down/Enter | test_final_01::test_s68_the_palette_lists_usable_commands_found_by_words. Hands-on (MENU-6): Ctrl+K, type "data fold", Down, Enter: Explorer opens the data folder | new |
| S69 | A shortcut for an unusable command does nothing | test_final_01::test_s69_a_command_that_cannot_be_used_does_nothing (Commands.trigger, which every shortcut calls) | new |
| S70 | Run/Stop only on the toolbar and tray | test_final_01::test_s70_run_and_stop_are_not_commands | new |
| S71 | New/Load/Recent: panels ask, then Save / Discard / Cancel | test_final_01::test_s71_new_with_unsaved_changes_asks_and_cancel_keeps_the_profile (real window, New). Hands-on (F-02b): with an open Keyboard draft, Load Profile…: the draft asks first, then the profile question | new |
| S72 | Save on a never-saved profile opens Save As in the profiles folder; unfinished actions ask | hands-on (F-04b, SAFE-1): New, Ctrl+S: Save As opens in Options → Folders → Profiles folder. Add an action with an error, Ctrl+S: "Unfinished Actions" asks first. Unfinished part: test_data_safety::test_unfinished_actions_are_named_with_their_first_error | hands-on |
| S73 | Open Program Folder / Open Data Folder | test_open_folders::test_the_actions_open_those_folders | covered |
| S74 | Error dialog wraps and copies; notices in a message box | test_usability_fixes::test_error_details_wrap_and_copy | covered |
| S75 | One quit order (tool window → panels → profile → Button Map → Run stops) | test_final_01::test_s75_s76_quit_order_and_cancel (Module Setup with unsaved work asks and the quit stops; then the profile asks); test_batch2_B1::test_main_window_shell. Hands-on (SAFE-3, W-03): with an unsaved Calibration, a Configuration panel edit and an unsaved Button Map, File → Exit: Calibration asks and the quit stops; Exit again: panel, profile, Button Map in that order | new |
| S76 | Cancel calls off the quit and any restart/install | test_final_01::test_s75_s76_quit_order_and_cancel (restart cleared); test_update_model::test_cancelled_quit_clears_the_install | new |
| S77 | Closing a quit's Save As calls off the quit; next Save As clean | hands-on (SAFE-1): unsaved new profile, File → Exit → Save → close the Save As window: program stays; Ctrl+Shift+S, Save: no quit afterwards | hands-on |
| S78 | Quit stops everything, threads 2 s, writes, History, lock | test_final_01::test_s3_s78_s81_... (order after exec); test_audit3_run_stop::test_quitting_stops_once_and_makes_nothing_to_stop_it; test_threads::test_shutdown_names_a_thread_that_will_not_stop; test_audit2_coverage::test_quit_closes_history_between_the_two_writes | covered |
| S79 | Main window place saved on close, restored at start | test_window_placement.py; test_batch2_B1::test_the_x_hides_to_the_tray_and_saves_the_window_place. Hands-on (W-01): move/resize, exit, start: same place | covered |
| S80 | X with nothing unsaved quits | test_batch2_B1::test_main_window_shell (X quits with a tool window open) | covered |
| S81 | Restart: usual quit, same arguments; cancel cancels | test_restart_command.py; test_stage1_app_profile::test_restart_quits_the_usual_way_and_a_cancel_clears_it; test_final_01::test_s3_s78_s81_... | covered |
| S82 | History never stops a quit | test_audit3_saving::test_quit_goes_on_when_the_history_folder_cant_be_made | covered |
| S83 | Tray icon follows Run/Stop | test_stage1_app_profile::test_tray_icon_follows_run_and_stop | covered |
| S84 | Tray left click / menu items | test_stage1_app_profile::test_tray_clicks_and_menu | covered |
| S85 | Minimize to tray: minimize/close hide; Exit still quits | test_stage1_app_profile::test_minimize_to_tray_hides_on_minimize_and_close; test_batch2_B1::test_the_close_a_quit_makes_is_not_turned_into_a_hide. Hands-on (batch 2 B1): Minimize to tray on, File → Exit and tray Exit both quit | covered |
| S86 | First X hide: one balloon, never again | test_stage1_app_profile::test_x_says_still_running_once | covered |
| S87 | Pages unloaded in the tray, reloaded when shown | test_tray_memory::test_hidden_window_unloads_and_reloads | covered |
| S88 | Tray icon back after Explorer restarts | test_stage1_app_profile::test_tray_icon_comes_back_after_explorer_restarts | covered |
| S89 | Tray Exit brings the window back first | test_stage1_app_profile::test_tray_exit_brings_the_window_back_first | covered |
| S90 | Threads via gremlin.threads, named, listed | test_threads::test_a_thread_is_named_and_listed_while_it_runs | covered |
| S91 | shutdown() waits one limit, names stragglers | test_threads::test_shutdown_asks_each_thread_to_stop_and_waits, ::test_shutdown_names_a_thread_that_will_not_stop | covered |
| S92 | A thread ending with an error leaves the list | test_threads::test_an_error_in_a_thread_still_takes_it_off_the_list | covered |
| S93 | Action timers run their function on the main thread | test_final_01::test_s93_a_main_thread_timer_runs_its_function_on_the_main_thread | new |
| S94 | Timed loops use gremlin.clock | test_clock.py; test_batch3_C2::test_periodic_callbacks_run_on_the_program_clock, ::test_the_sound_loop_waits_on_the_program_clock; test_batch3_C3b::test_hook_stop_waits_on_the_program_clock; test_watchdog.py (clock-driven) | covered |
| S95 | No unbounded wait on the main thread | test_bounded_waits.py | covered |
| S96 | Log files: system/user 1 MB + one backup, event new each session, qt.log, UTF-8 | test_final_01::test_s96_system_and_user_logs_rotate_at_1_mb_and_event_log_is_new_each_session; test_audit2_coverage::test_log_files_are_utf8; test_qt_log.py | new |
| S97 | Diagnostic logs default to Warning | test_final_01::test_s97_diagnostic_logs_default_to_warning | new |
| S98 | Unhandled error: system.log, dialog, console | test_error_report::test_a_top_level_error_is_logged_shown_and_passed_on | covered |
| S99 | Thread error "Error in <name>"; SystemExit is not one | test_error_report::test_an_error_in_a_thread_is_logged_with_its_name, ::test_a_thread_ending_with_system_exit_is_not_an_error | covered |
| S100 | Native crash → crash.log (appended) | test_error_report::test_the_crash_log_is_turned_on_in_the_logs_folder | covered |
| S101 | qt.log: time, console, 1 MB move, 5 MB cap | test_qt_log.py (4 tests) | covered |
| S102 | Repeating error logged once per run | test_write_less::test_repeating_errors_are_logged_once | covered |
| S103 | Routine Run status lines are Info | hands-on (LOG-WARNINGS): Diagnostic logs at Warning, Run and Stop a profile three times: no new lines in system.log | hands-on |
| S104 | Live Log Reader tabs; remembers tab/Log/Show; Find empty, Live off; not reopened | test_live_log_view::test_the_window_opens_on_the_last_choices; test_live_log_debug::test_window_has_config_debug_and_input_monitor_tabs | covered |
| S105 | Config tab: logs.txt emptied at start; Clear Log asks; Copy All | test_final_01::test_s105_the_activity_log_is_emptied_at_start_and_by_clear_log. Hands-on: Config tab → Clear Log: asks first; Copy All, paste in Notepad: the same lines | new |
| S106 | Debug tab Log/Show/Find, traceback with its entry, colors, "X of Y" | test_live_log_debug::test_levels_and_find, ::test_a_traceback_belongs_to_its_entry, ::test_all_logs_merges_every_file_by_time | covered |
| S107 | Over 512 KB: tail + Load Whole File | test_live_log_debug::test_load_whole_file | covered |
| S108 | Clear Log through the handler; not for All logs | test_live_log_debug::test_clear_empties_the_file_through_its_handler | covered |
| S109 | Live catches all; Start empty, Clear View, Save Feed…, Show Log File; stops on close | test_log_feed.py (5 tests) | covered |
| S110 | Red debug frame and DEBUG badge; badge opens the reader | test_log_feed::test_red_mode_follows_all_and_live. Hands-on: Diagnostic logs ALL: red frame on every window; click DEBUG: the Live Log Reader opens | covered |
| S111 | View never blank after a shorter log; Live adds rows; redraws wait on selection | test_live_log_view::test_a_short_log_after_a_long_one_is_drawn; test_program_fixes::test_live_adds_rows_without_drawing_the_view_again, ::test_the_view_holds_redraws_while_text_is_selected | covered |
| S112 | Log When Not Responding off by default, at once, in Diagnostics | test_watchdog::test_the_option_is_off_by_default_and_takes_effect_at_once, ::test_the_option_is_in_options_diagnostics | covered |
| S113 | 5 s freeze logged once with stacks, then recovery | test_watchdog::test_a_freeze_is_logged_once_with_the_stacks_then_the_recovery | covered |
| S114 | Help → Check for Updates opens the window and checks | test_final_01::test_s114_check_for_updates_opens_the_window_and_checks (real window; offline run reports why) | new |
| S115 | Start-up check silent unless newer and not skipped; manual says why | test_update_check::test_should_offer | covered |
| S116 | Skip This Version stops the start-up offer only | test_update_check::test_should_offer; test_stage1_app_profile::test_skip_this_version_and_the_release_page | covered |
| S117 | Installed: Update Now (verify, quit, silent install, restart); else release page | test_update_check::test_install_kind; test_update_model::test_nothing_installs_without_a_verified_download. Hands-on (UPD-APP): installed copy one version behind: Update Now, unsaved question, installs, new version starts | covered |
| S118 | Nothing unverified downloaded or run | test_update_check::test_release_without_a_verifiable_setup | covered |
| S119 | Closing the Update window mid-download cancels and deletes the part file | test_final_01::test_s119_cancelling_a_download_deletes_the_partial_file. Hands-on: start Update Now, close the window mid-download: no `.part` left in the updates folder | new |
| S120 | Disk full / rename / folder: "Could not save the download to …" | test_program_fixes::test_a_full_disk_is_reported_as_one, ::test_a_download_that_cannot_be_renamed_says_so, ::test_an_updates_folder_that_cannot_be_made_says_so | covered |
| S121 | "Updated" once; old installers deleted, logs kept; first run isn't an update | test_update_model::test_says_so_once_after_an_update, ::test_first_run_is_not_an_update | covered |
| S122 | Unfinished update: window with setup log and Try Again | test_program_fixes::test_a_failed_update_is_told_with_try_again | covered |
| S123 | Update requests close their connection | test_final_01::test_s123_an_update_check_closes_its_connection_with_the_reply. Hands-on (SSL-CONSOLE): run from a console, Check for Updates, wait a minute: no QSslSocket message | new |
| S124 | Data folder default; each folder chosen in Options → Folders | test_stage1_app_profile::test_data_and_logs_folders_follow_options_and_fall_back | covered |
| S125 | Logs and plugins folder changes take effect at the next start | test_batch2_B1::test_the_logs_folder_stays_until_the_next_start, ::test_folder_rows_say_when_they_take_effect. Hands-on (plugins): change Plugins folder, add a plugin there: it appears only after a restart | covered |
| S126 | Unreachable chosen folder falls back to the default | test_batch2_B1::test_a_missing_data_folder_uses_the_default_and_says_so_once, ::test_a_data_folder_that_cannot_be_written_never_stops_folder_lookups; test_stage1_app_profile::test_a_data_folder_that_cannot_be_made_does_not_stop_folder_lookups | covered |
| S127 | Old qml/maps device files copied once into modules | The copy (`copy_legacy_modules`) was removed in batch 3 (GL-272: nothing ships in qml/maps). Nothing left to test; the statement is stale (question 2) | gap |
| S128 | User Guide by section; Button Map has its own | test_help_guide::test_button_map_help_is_its_own_guide, ::test_every_topic_has_a_section_title_and_body | covered |
| S129 | Guide menu paths exist; every action has a topic; nothing removed | test_help_guide::test_menu_paths_in_the_guide_exist, ::test_every_action_plugin_has_a_topic, ::test_removed_or_wrong_things_are_not_in_the_help | covered |
| S130 | About shows the build's version and the repository | test_help_guide::test_about_shows_the_build_version | covered |
| S131 | Escape closes Help, About, Check for Updates; stick windows ignore it | test_usability_fixes::test_escape_closes_the_tool_windows (Help, About, Update). Hands-on: in the vJoy Viewer and Calibration, press Escape: they stay open | covered |

## Section 12 decisions that state behaviour

| Ref | Decision (short) | Check | Status |
|---|---|---|---|
| Q1 | The X quits even with a tool window open | test_batch2_B1::test_main_window_shell (About open, X → quit) | covered |
| Q2 | Exit always ends the program with Minimize to tray on | test_batch2_B1::test_the_close_a_quit_makes_is_not_turned_into_a_hide. Hands-on (real screen, batch 2 B1): Minimize to tray on, File → Exit and tray Exit: the process ends | covered |
| Q3 | Window place saved when it hides to the tray | test_batch2_B1::test_the_x_hides_to_the_tray_and_saves_the_window_place | covered |
| Q4 | Logs/data folder change takes effect at next start; rows say so | test_batch2_B1::test_the_logs_folder_stays_until_the_next_start, ::test_folder_rows_say_when_they_take_effect; test_batch2_B1::test_the_live_log_reader_finds_its_folder_once_and_reads_changed_files_only | covered |
| Q5 | Missing chosen data folder: default, told once | test_batch2_B1::test_a_missing_data_folder_uses_the_default_and_says_so_once | covered |
| Q6 | Unwritable configuration.json: one notice per session | test_batch2_B1::test_a_settings_file_that_cannot_be_written_is_told_once | covered |
| Q7 | History Restore of log level / UI scale applies at once | test_batch2_b7::test_restore_applies_logs_and_ui_scale_at_once | covered |
| Q8 | Box covers every start-up failure | see S16 | new |
| Q9 | Other copy not closed: say so and ask again | test_batch2_B1::test_a_second_copy_that_could_not_be_closed_is_said_and_asked_again, ::test_the_not_closed_box_says_so | covered |
| Q10 | Main-thread action timers listed and cancelled | test_audit3_run_stop::test_main_thread_timers_are_listed_and_shut_down | covered |
| Q11 | shutdown_cleanup once; stops only what exists | test_audit3_run_stop::test_quitting_stops_once_and_makes_nothing_to_stop_it | covered |
| Q12 | Keep one "settings changed" signal | No behaviour change; S49 shows it is sent | covered |
| Q13 | Options help topic matches the layout | test_batch3_C1::test_options_help_names_every_section_and_group | covered |
| Q14 | Option text and pickers in glossary words | test_batch3_C1::test_options_text_and_pickers_use_the_glossary | covered |
| Q15 | Diagnostic logs default Warning | see S97 | new |
| Q16 | No stays in the second-copy box | see S20 | covered |

## Batch hands-on checks for this page (claude/catchup-test-plan.md)

- Batch 2 B1: with Minimize to tray on, File → Exit quits and tray Exit quits; the X hides the window and the next start opens it in the same place; the X with the vJoy Viewer open quits the program; tray Run/Stop with an edited action pane asks first.
- Batch 3 C1: Options → Folders pickers are titled by what they do ("Choose Logs Folder", etc.).
- Batch 3 C2 (shell part): auto-load on picks up the program in front.

## Counts

Section 8: 131 statements (S1-S131). Covered 86, new 37, hands-on 7, gap 1 (many covered/new rows also carry a hands-on step for the part only a person can see).
Decisions with behaviour: 16 (Q1-Q16): covered 14, new 2 (Q8, Q15, through S16 and S97).
