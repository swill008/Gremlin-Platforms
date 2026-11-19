# Tests that pin tray behaviour and main-thread input behaviour (SCAN-TESTS)

Read-only scout. No code, tests or other files were changed. Clock: started 13:03, report written 13:04 (`date +%H:%M`). Rough scan, not a full read of all 174 matching files.

## Scope and counts

- Group B pattern hits (EventHandler, event_handler, process_event, dispatch, main thread, QThread, moveToThread, queued, clock patches): 689 occurrences in 174 files under `test/`. The file-level grep for direct `EventHandler`/`process_event`/`runtime.` calls hit 96 files under `test/unit/`.
- Group A pattern hits (tray names): about 60 lines in 12 files, of which 9 files hold real tray tests.

## A) Tests that pin tray behaviour

| File | Test name(s) | Line | What it pins |
|---|---|---|---|
| test/unit/test_final_09.py | test_s63_a_left_click_shows_the_window_as_it_was | 349 | Left click on tray icon restores the window in its previous visibility mode |
| test/unit/test_final_09.py | test_s73_start_minimized_minimizes_and_goes_to_the_tray_when_on | 361 | `--start-minimized` minimises, and goes to tray only when "minimize-to-tray" is on (also pins the `minimize-to-tray` key, 330, 385) |
| test/unit/test_final_09.py | fixture `tray` | 307-341 | Stubs `tray_memory.enter_tray` / `leave_tray` (325-326) and the settings key (330) |
| test/unit/test_final_09.py | comment on registration | 413 | Pins the CI failure "No parameter with key minimize-to-tray" |
| test/unit/test_stage1_app_profile.py | test_tray_icon_follows_run_and_stop | 506 | Tray icon add/modify, active vs idle icon, title "Gremlin-Platforms" |
| test/unit/test_stage1_app_profile.py | test_tray_clicks_and_menu | 518 | Tray click and menu behaviour (uses `trayed` list, 483-487) |
| test/unit/test_stage1_app_profile.py | test_minimize_to_tray_hides_on_minimize_and_close | 551 | Minimise and X hide to tray only when setting is on; `trayed == ["enter","leave"]` (575); window place saved (GL-112) |
| test/unit/test_stage1_app_profile.py | test_x_says_still_running_once | 578 | X message shown once while tray-hidden |
| test/unit/test_stage1_app_profile.py | test_tray_icon_comes_back_after_explorer_restarts | 594 | Tray re-added after Explorer restart |
| test/unit/test_stage1_app_profile.py | test_tray_exit_brings_the_window_back_first | 604 | Tray Exit restores window before quitting |
| test/unit/test_stage1_app_profile.py | test_no_tray_icon_never_hides_the_window | 614 | No tray icon means the window is never hidden |
| test/unit/test_stage1_app_profile.py | test_restart_quits_the_usual_way_and_a_cancel_clears_it | 630 | Restart path (tray-adjacent) |
| test/unit/test_stage1_app_profile.py | setting key | 431, 564, 582, 620 | Hard-coded `("global","general","minimize-to-tray")` |
| test/unit/test_stage1_runtime.py | test_the_tray_offers_run_or_stop_and_changes_its_icon | 1073 | Tray Run/Stop menu item and icon follow `gremlinActive` (patches `system_tray.win32gui`, 1079) |
| test/unit/test_batch2_B1.py | test_the_x_hides_to_the_tray_and_saves_the_window_place | 435 | X hides window to tray and saves its place (`window.hidden`, `saved == [window]`) |
| test/unit/test_batch2_B1.py | test_the_close_a_quit_makes_is_not_turned_into_a_hide | 445 | A real quit is not turned into a hide |
| test/unit/test_batch2_B1.py | (setting stub lambda) | 417-427 | `minimize-to-tray` read via lambda; `SystemTrayIcon.__new__` bypass |
| test/unit/test_quit_request.py | test_the_tray_window_handles_the_registered_quit_request | 47 | Quit-request window message maps to `_quit_request_cb` |
| test/unit/test_quit_request.py | test_the_request_is_answered_then_quits_from_the_event_loop | 55 | Installer quit request answered (returns 1) before quitting from the event loop |
| test/unit/test_quit_request.py | test_the_quit_is_the_tray_exit_path | 71 | Tray quit calls `restore_window` then `quitRequested` |
| test/unit/test_tray_memory.py | test_hidden_window_unloads_and_reloads | 70 | Hidden window unloads pages; shown again reloads (`enter_tray`/`leave_tray` in a subprocess) |
| test/unit/test_tray_memory.py | test_working_set_trim_is_safe_to_call | 87 | Working-set trim call |
| test/unit/test_tray_memory.py | test_pages_load_only_while_needed | 91 | Page load only while needed; source-text pin on `system_tray.py` (100, 117-118) |
| test/unit/test_installer_closes_program.py | (constants check) | 52-57 | Installer script uses `QUIT_REQUEST_NAME` / `QUIT_REQUEST_HANDLED` |
| test/unit/test_options_reveal.py | (UI label) | 101-103, 147 | "Minimize to tray" option card is revealed |

Totals (group A): 9 files with real tray tests; about 22 named test functions and fixtures; plus 6 setting-key or constant pins.

## B) Tests that pin input path on the main thread, or drive bindings with clock patches

### B1. Immediate-assert tests (call handler/runtime directly, assert at once)

| File | Test name | Line | What it pins |
|---|---|---|---|
| test/unit/test_batch2_b2a_input_events.py | test_holding_esc_cancels_listen_on_the_main_thread | 382-399 | Calls `_kb_event_cb` directly; asserts the abort ran on `threading.main_thread()` |
| test/unit/test_batch2_b2a_input_events.py | test_listen_*, test_keys_* (about 20 tests) | 95-650 | Calls key/mouse callbacks directly; asserts immediate state |
| test/unit/test_stage1_app_profile.py | test_keyboard_hook_reports_keys_and_passes_every_event_on | 826 | Direct hook call, immediate events |
| test/unit/test_stage1_app_profile.py | test_holding_esc_cancels_listen | 996 | Direct Esc-hold cancel, immediate |
| test/unit/test_action_state.py | test_smart_toggle_reports_on_until_its_second_release | 103-121 | Calls `_press` and asserts `action_state.read` at once; `toggle.delay = 5.0` so only the synchronous quick-release path runs |
| test/unit/test_action_state.py | test_tempo_reports_its_last_press_long_on_short_off | 123 | Same pattern for tempo |
| test/unit/test_audit_runtime.py | test_a_pulse_on_the_main_thread_releases_later | 180 | Pulse functor called directly; asserts release order |
| test/unit/test_audit_runtime.py | test_a_run_after_a_slow_stop_starts_its_own_loop | 93-120 | Records `ran_on` thread |
| test/unit/test_audit3_run_stop.py | test_a_pulse_release_timer_fires_at_stop_before_the_drivers | 492 | Timer order at stop (fires synchronously in `scope.stop()`) |
| test/unit/test_audit3_run_stop.py | test_main_thread_timers_are_listed_and_shut_down | 554 | Main-thread timers listed and shut down |
| test/unit/test_audit3_run_stop.py | test_a_run_timer_fires_while_running_never_after_stop | 477 | Timer fire/stop ordering |
| test/unit/test_stage1_runtime.py | test_a_tempo_timer_fires_while_running / never_fires_after_stop | 383, 398 | Tempo timer on the runner |
| test/unit/test_stage1_runtime.py | test_release_callbacks_waiting_at_stop_are_dropped | 463 | Release callbacks dropped at stop |
| test/unit/test_action_fixes.py | test_action_timeouts_run_on_the_main_thread | 255-262 | `ran_on == [threading.main_thread()]` |
| test/unit/test_final_01.py | test_s93_a_main_thread_timer_runs_its_function_on_the_main_thread | 385-396 | `ran == [threading.main_thread()]` |
| test/unit/test_batch2_B5b.py | test_speech_asked_for_on_a_timer_thread_is_spoken_on_the_main_thread | 185 | Thread affinity for speech |
| test/unit/test_batch2_b2b.py | test_twin_names_from_the_hot_plug_thread_are_written_on_the_main_thread | 158 | Thread affinity for name writes |
| test/unit/test_cant_send_live.py | test_another_thread_s_notice_arrives_on_the_main_thread | 289 | Thread affinity for notices |
| test/unit/test_batch3_C3a.py | test_a_vjoy_opened_on_another_thread_is_kept_alive_from_the_main_thread | 309 | Thread affinity for vJoy |
| test/unit/test_device_library_FM2_threads.py | test_item7_library_changes_and_settings_run_on_the_main_thread | 256 | Thread affinity |
| test/unit/test_device_library_FM_model.py | test_gap9_..., test_gap10_a_plan_runs_on_the_main_thread | 164, 203 | Thread affinity |
| test/unit/test_export_background.py | (background export) | 97, 111 | Export on background thread, announce on main |
| test/unit/test_diagnostics_zip.py | (slow thread) | 278, 290 | Announce on main thread |
| test/unit/test_batch2_b7.py | (History thread) | 174-189 | Queued work runs on History thread |

### B2. Tests that patch queues or timers (white-box, not real path)

| File | Test name | Line | What it pins |
|---|---|---|---|
| test/unit/test_batch2_b2a_input_events.py | (queue_macro patched to list) | 526-538 | Macro queue captured, not run |
| test/unit/test_device_layout_change.py | (queue_macro patched) | 100-105, 153-159 | Same |
| test/unit/test_batch3_C3b.py | (QTimer.singleShot patched to list) | 286-294 | Queued callback captured |
| test/unit/test_action_fixes.py | macros._queued_macros mutated directly | 206-219 | Internal queue state |
| test/unit/test_bounded_waits.py | (manager._queued_macros set) | 107-108 | Internal queue state |

### B3. Tests that patch gremlin.clock while driving bindings or waits

| File | Test name | Line | What it pins |
|---|---|---|---|
| test/unit/test_bounded_waits.py | test_axis_significance_uses_the_program_clock | 134-150 | Patches `clock.monotonic`; axis 5 s reset |
| test/unit/test_bounded_waits.py | test_axis_change_tracker_uses_the_program_clock | 151 | Same |
| test/unit/test_bounded_waits.py | test_event_listener_waits_with_a_timeout / test_macro_scheduler_waits_with_a_timeout | 65, 104 | Bounded waits |
| test/unit/test_bounded_waits.py | test_callback_has_no_sleep_on_the_event_thread | 119 | No sleep on event thread |
| test/unit/test_batch3_C3b.py | test_hook_stop_waits_on_the_program_clock | 81-95 | Patches `clock.monotonic` |
| test/unit/test_batch3_C3b.py | test_own_pad_window_runs_on_the_program_clock | 98 | Same |
| test/unit/test_batch3_C3b.py | test_macro_recording_ignores_events_the_program_made | 281 | Macro recording on clock |
| test/unit/test_batch3_C2.py | (clock.monotonic, clock.sleep patched) | 114-147 | Stepped clock |
| test/unit/test_clock_use.py | test_feedback_cache_expires_on_the_clock / test_input_monitor_axis_throttle_steps_on_the_clock | 83, 104 | Clock steps |
| test/unit/test_clock.py | (clock tests) | 7-50 | `clock.monotonic` stepped by hand |
| test/unit/test_audit_saving.py | (clock.sleep patched) | 60 | Sleep patched |
| test/unit/test_batch3_c4.py | (clock.sleep patched) | 303 | Sleep patched |
| test/action_interaction/test_macro.py | test_preemptive_exclusive_pauses_and_resumes_macro / test_non_preemptive... | 188, 225 | Real runtime, but timing-sensitive |
| test/action_interaction/test_double_tap_tempo.py | test_double_tap_short / test_double_tap_long | 77, 88 | Real runtime with jgbot fixture (not clock-patched) |
| test/action_interaction/test_condition.py | test_condition_with_tempo | 62 | Tempo timing |
| test/unit/test_action_state.py | smart toggle, tempo | 103, 123 | Synchronous path, no clock patch (see B1) |
| test/journeys/test_j08_macro_stop.py | test_stop_mid_macro_releases_the_held_key_at_once | 106 | Real path, timing |
| test/journeys/test_j10_tempo_stop.py | test_the_tempo_is_made_in_the_pane_and_saved | 102 | Real path |

Totals (group B): about 40 named tests in B1, 5 white-box queue patches in B2, and about 18 clock-patch tests in B3 (plus about 50 `clock.monotonic` loops in smoke files that only poll, not pin behaviour).

## Notes for the lead

- Tray tests in test_stage1_app_profile.py and test_final_09.py stub the same `tray_memory.enter_tray` / `leave_tray` names. Renaming or moving those functions breaks several tests at once.
- test_tray_memory.py asserts source text in `gremlin/ui/system_tray.py` (lines 117-118). A refactor that renames the calls breaks it even if behaviour is right.
- The main-thread tests (`ran_on == [threading.main_thread()]`) pin thread location, so a move to a worker thread fails them on purpose.
- Smart toggle and tempo tests in test_action_state.py (103, 123) assert immediately after `_press`; a change to a deferred or queued model fails them.
- Left out: full read of every file in the 174 matches; tests under test/unit/action_matrix and the smoke files, which mostly poll clock.monotonic.
