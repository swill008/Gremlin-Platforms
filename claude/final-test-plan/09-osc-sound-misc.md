# Final test plan: 09 OSC, sound and speech, tray, look and help

Spec: `claude/program-map/09-osc-sound-misc.md` (section 8, section 12: all
questions decided as recommended) and `claude/decisions.md` (D-09-*,
D-09-TTS-ENGINE, D-06-Q8, D-05-Q7, D-STD-HOLD). New tests:
`test/unit/test_final_09.py`. Agent P09, 2026-10-06.

OSC is parked by the user (D-STD-OSC, todo.md): S1-S48 and the OSC decisions
(Q1-Q10, Q18) are listed as `parked`; no OSC tests were written.

`U` = `test/unit/`.

| Ref | Statement (short) | Check | Status |
|---|---|---|---|
| S1 | OSC listens only while running (and during Listen); stops at Stop/quit | — | parked |
| S2 | Options → OSC → Enabled off: no socket at Run | — | parked |
| S3 | Listens on the Options input host/port; host list, rescan, typed address | — | parked |
| S4 | Enabled/host/port changed while running rebind at once | — | parked |
| S5 | Bad port falls back to the default | — | parked |
| S6 | Input and output default ports differ, shown the same everywhere (Q1: 8000 / 9000) | — | parked |
| S7 | Port can't open: profile still runs, one error "Could not bind OSC on host:port." | — | parked |
| S8 | No firewall prompt / bind error when the profile has no OSC inputs (Q5) | — | parked |
| S9 | Output address is where feedback goes (Q3: hide until something sends) | — | parked |
| S10 | OSC page lists inputs with type, number, address, action count | — | parked |
| S11 | OSC page locked while running | — | parked |
| S12 | Add creates the input, selects it, opens its actions | — | parked |
| S13 | After Add the new input is selected, also for an Axis | — | parked |
| S14 | Adding an existing address selects it | — | parked |
| S15 | Addresses match without case, stored lower case | — | parked |
| S16 | Change is its own type; Message/Trigger controls work or are hidden (Q2) | — | parked |
| S17 | Listen fills the address from the next packet and binds it | — | parked |
| S18 | Listen says when OSC is off or the port can't open | — | parked |
| S19 | Bulk capture: one input per new address; same address within 0.3 s once | — | parked |
| S20 | Cancel/close/untick Bulk ends listening and closes the port when stopped | — | parked |
| S21 | "Listening for OSC" box has a Stop button | — | parked |
| S22 | Import: one input per "/" line, skips others and existing, selects the last | — | parked |
| S23 | Import suffixes give the promised types (Q2) | — | parked |
| S24 | Editing an address keeps its actions | — | parked |
| S25 | Address never blank, starts with "/", unique; duplicate rename says why | — | parked |
| S26 | Delete removes the input and its actions in every mode (Q6: with Undo) | — | parked |
| S27 | Clear asks first, then removes all | — | parked |
| S28 | Sort orders A-Z (Q7: toggle, remembered) | — | parked |
| S29 | OSC inputs listed in Logical Device → Assign Hardware | — | parked |
| S30 | OSC page has no Appearance panel | — | parked |
| S31 | OSC card offers no Swap Device, Auto Mapper, Device Information, Calibration | — | parked |
| S32 | Input highlighting doesn't jump to OSC inputs | — | parked |
| S33 | OSC Add and Calibration each hold their own highlight pause | — | parked |
| S34 | OSC empty state talks about OSC | — | parked |
| S35 | OSC dialogs say "OK", Cancel where other dialogs put it | — | parked |
| S36 | Matching packet fires the input's actions in the current mode | (`U/test_input_module_gate.py::test_osc_passthrough` covers the gate only) | parked |
| S37 | Unknown address ignored; `/noop` always ignored | — | parked |
| S38 | Button: non-zero press, 0 release, text pressed unless numeric 0 | — | parked |
| S39 | Address-only button: Treat as 1.0 / Auto-release with delay | — | parked |
| S40 | Auto-release in the mode of the press | — | parked |
| S41 | Axis: first value limited to -1…1; none or text = 0 | — | parked |
| S42 | Listen guesses the type from the first packet | — | parked |
| S43 | Options changes apply to the next packet | — | parked |
| S44 | OSC inputs saved in the profile, connection settings in program settings | — | parked |
| S45 | Load / New replaces the OSC inputs | — | parked |
| S46 | OSC edits mark the profile unsaved | — | parked |
| S47 | History records "the OSC inputs" | — | parked |
| S48 | A damaged `<osc-device>` doesn't stop the profile opening | — | parked |
| Q1-Q10, Q18 | OSC decisions (D-09-Q1..Q10, Q18) | — | parked |
| S49 | Sounds only while running; Stop cuts playing sounds and drops queued ones (D-06-Q8) | `U/test_stage1_runtime.py::test_stop_cancels_the_sounds_and_empties_the_queue`, `::test_a_sound_queued_with_no_run_never_plays`; `U/test_batch1_run_callers.py::test_a_sound_asked_for_with_no_run_on_is_dropped`; `U/test_bounded_waits.py::test_a_sound_is_not_waited_for_once_the_player_stops` | covered |
| S50 | Sequential / Interrupt / Overlap | `U/test_stage1_runtime.py::test_sequential_sounds_wait_for_the_one_playing`, `::test_interrupt_stops_the_sound_playing`, `::test_overlap_plays_sounds_together` | covered |
| S51 | Playback mode changed in Options applies at once (via emitConfigChanged when Options closes) | `U/test_final_09.py::test_s51_a_new_playback_mode_applies_when_options_closes` | new |
| S52 | Decoded on the playback thread, freed when done | `U/test_program_fixes.py::test_sounds_are_decoded_on_the_playback_thread`, `::test_finished_sounds_are_let_go`; queue lock (R9/G2): `U/test_batch3_C2.py::test_queueing_a_sound_waits_for_the_queue_lock` | covered |
| S53 | Missing file: nothing, warn once; damaged file logged once, others go on | `U/test_play_sound_missing_file.py` (all), `U/test_program_fixes.py::test_a_sound_that_cannot_be_decoded_is_logged_once` | covered |
| S54 | Stop right after start ends the audio thread | `U/test_threads.py::test_the_audio_player_stopped_right_after_starting_ends` | covered |
| S55 | Waiting for a sound is never endless | `U/test_bounded_waits.py` | covered |
| S56 | Speech only while running; Interrupt / Queue Front / Queue Back | `U/test_stage1_runtime.py::test_speech_uses_the_options_voice_and_the_queue_modes`, `::test_speech_asked_for_with_no_run_is_ignored`; `U/test_batch1_run_callers.py::test_speech_asked_for_with_no_run_on_is_dropped`; `U/test_batch2_B5b.py::test_speech_arriving_after_stop_is_dropped` | covered |
| S57 | Stop stops speech and drops queued text | `U/test_stage1_runtime.py::test_stop_ends_speech_and_empties_its_queue` | covered |
| S58 | Options voice used by every TTS action, also changed while running | `U/test_stage1_runtime.py::test_speech_uses_the_options_voice_and_the_queue_modes` (at Run); `U/test_final_09.py::test_s58_a_voice_changed_while_running_speaks_the_next_text` | new |
| S59 | Saved voice uninstalled: the default voice speaks | `U/test_final_09.py::test_s59_a_saved_voice_no_longer_installed_speaks_with_the_default`; `U/test_batch2_B5b.py::test_choosing_default_saves_no_voice_and_speaks_with_the_default` | new |
| S60 | `${current_mode}` replaced by the current mode name | `U/test_final_09.py::test_s60_current_mode_in_the_text_is_the_current_mode_name` | new |
| S61 | (Changed by Q11 / D-09-Q11, D-05-Q7) Text to Speech is offered on keyboard keys too | `U/test_batch2_B5b.py::test_text_to_speech_is_offered_on_keyboard_keys`; help: `U/test_batch3_C1.py::test_text_to_speech_help_names_keyboard_keys`. Hands-on (B5b): add Text to Speech to a keyboard key, Run, press it: it speaks | covered |
| Q12 | Saved voice gone: Options shows "(default)" | `U/test_batch2_B5b.py::test_options_show_default_when_the_saved_voice_is_gone`. Hands-on (B5b): Options → Actions → Text to Speech with a removed voice saved: "(default)" | covered |
| Q13 | Windows speech missing: one warning in the log and the action's feedback | `U/test_batch2_B5b.py::test_missing_windows_speech_warns_once_in_the_log_and_the_action`, `::test_windows_speech_present_gives_no_warning` | covered |
| R10 / G1 | Speech asked for on a timer thread is spoken on the main thread | `U/test_batch2_B5b.py::test_speech_asked_for_on_a_timer_thread_is_spoken_on_the_main_thread`. Hands-on (B5b): Text to Speech under Tempo and in a macro speaks | covered |
| Q14 | Loops that sleep in a thread use `gremlin.clock` (audio loop) | `U/test_batch3_C2.py::test_the_sound_loop_waits_on_the_program_clock` (OSC debounce/auto-release parked) | covered |
| D-09-TTS-ENGINE | Speech engine lives for the program; only its queue belongs to a Run | `U/test_stage1_runtime.py::test_speech_asked_for_with_no_run_is_ignored` (engine kept after Stop, nothing said) | covered |
| S62 | Tray icon shows, idle/active follows Running/Stopped, tooltip "Gremlin-Platforms" | `U/test_stage1_app_profile.py::test_tray_icon_follows_run_and_stop`; `U/test_stage1_runtime.py::test_the_tray_offers_run_or_stop_and_changes_its_icon` | covered |
| S63 | Left-click shows the window as it was (windowed, maximized, full screen) | `U/test_stage1_app_profile.py::test_tray_clicks_and_menu` (windowed); `U/test_final_09.py::test_s63_a_left_click_shows_the_window_as_it_was[Maximized/FullScreen]` | new |
| S64 | Tray menu: Show/Hide Gremlin-Platforms, Run Profile / Stop Profile, Exit Gremlin-Platforms | `U/test_stage1_app_profile.py::test_tray_clicks_and_menu` | covered |
| S65 | Minimize to tray: minimize or X hides, profile keeps running; File → Exit / tray Exit quit (D-01-Q2) | `U/test_stage1_app_profile.py::test_minimize_to_tray_hides_on_minimize_and_close`; `U/test_batch2_B1.py::test_the_x_hides_to_the_tray_and_saves_the_window_place`, `::test_the_close_a_quit_makes_is_not_turned_into_a_hide`. Hands-on (B1, TRAY-ONE): Minimize to tray on, Run, X: window hides and the profile keeps running; tray icon → show: same place and size; File → Exit quits; tray Exit quits | covered |
| S66 | First X hide shows a "still running" balloon once | `U/test_stage1_app_profile.py::test_x_says_still_running_once` | covered |
| S67 | Tray Exit brings the window back first | `U/test_stage1_app_profile.py::test_tray_exit_brings_the_window_back_first` | covered |
| S68 | Old "Close to tray" on gives Minimize to tray on | `U/test_final_09.py::test_s68_close_to_tray_on_gives_minimize_to_tray_on[True/False]` | new |
| S69 | Hidden to tray: pages unload, memory given back, inputs work, unsaved edits kept; showing reloads | `U/test_tray_memory.py::test_hidden_window_unloads_and_reloads`, `::test_pages_load_only_while_needed`. Hands-on MEM-HANDS-ON: Minimize to tray on, Run, hide: Task Manager memory drops to a few MB and inputs still work; show: Home with photos returns; an unsaved display-panel edit survives; Scripts, Profile Settings and every Configuration tab still work | covered + hands-on |
| S70 | No tray icon: minimize and X behave normally | `U/test_stage1_app_profile.py::test_no_tray_icon_never_hides_the_window` | covered |
| S71 | Icon comes back after Explorer restarts | `U/test_stage1_app_profile.py::test_tray_icon_comes_back_after_explorer_restarts` | covered |
| S72 | Off-screen runs make no tray icon | `U/test_audit3_startup.py::test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray`, `::test_the_tray_icon_uses_the_shared_check`; `U/test_audit2_startup_devices.py::test_the_tray_icon_follows_the_platform_qt_started_on` | covered |
| S73 | `--start-minimized` starts minimized (to the tray with Minimize to tray on) | `U/test_final_09.py::test_s73_start_minimized_minimizes_and_goes_to_the_tray_when_on` | new |
| — | Tray Run with an edited action pane asks first (06 Q6, batch B1) | Hands-on (B1): open an action editor with a change, tray → Run Profile: the Discard/Cancel question shows | hands-on |
| S74 | Dark mode on/off applies at once to every window | `U/test_final_09.py::test_s74_s76_dark_mode_switches_at_once_and_light_mode_is_grey` (Style tokens and GremlinStyle control backgrounds switch both ways, no restart). Hands-on OPT-U01: with Options, Home, a Module Setup and the Input Viewer open, untick/tick Options → Interface → Dark mode and close Options: every open window changes at once | new + hands-on |
| S75 | Screens use Style colour tokens, not literals; photos keep their colours | `U/test_colour_tokens.py::test_no_new_colour_literals`, `::test_remaining_counts_are_current` | covered |
| S76 | Light mode is grey: no white surfaces | `U/test_final_09.py::test_s74_s76_dark_mode_switches_at_once_and_light_mode_is_grey` (surface tokens and Pane/TextField/TextArea/ToolBar/TabBar/Popup backgrounds) | new |
| S77 | Menus, dropdowns, command palette look the same everywhere | `U/test_menus.py` (all: no stock menus, dropdown rows use the menu look, shared menus work). Hands-on MENU-1/MENU-2: open the main menu bar, a right-click menu on Home, a dropdown in Options and Ctrl+K: same rows, hover and accent bar | covered + hands-on |
| S78 | Fonts only from `Style.uiFont`, `monoFont`, `iconFont` | `U/test_final_09.py::test_s78_screens_name_no_font_family_themselves` (xfail FINAL-09-1) | new (xfail) |
| S79 | Error and notification dialogs readable in both themes | Hands-on W-12: in dark and in light mode, open a profile that doesn't exist (`--profile missing.xml`) and trigger a notification (e.g. Save Profile): title, text and buttons readable | hands-on |
| S80 | Windows scaling on: follows Windows, slider disabled at 100 % | `U/test_ui_scale.py::test_windows_scaling_on_ignores_slider` | covered |
| S81 | Ignore Windows scaling on: slider 70-200 % sizes the UI on release | `U/test_ui_scale.py::test_windows_scaling_off_uses_slider`, `::test_style_follows_backend_live`, `::test_clamp_scale`, `::test_dp_rounds_half_up_like_qml`. Hands-on OPT-U06: drag the slider, release: the UI resizes without a restart | covered |
| S82 | Changing "Ignore Windows display scaling" asks Restart / Later / Cancel; Cancel undoes; Restart restarts and reads the new value | `U/test_final_09.py::test_s82_the_next_start_reads_the_new_windows_scaling_choice[True/False]`, `::test_s82_cancel_puts_the_old_choice_back`; restart path `U/test_stage1_app_profile.py::test_backend_restart_request`, `::test_restart_quits_the_usual_way_and_a_cancel_clears_it`. Hands-on OPT-U02 / W-11: tick the box: "Restart Required" with Restart / Later / Cancel; Cancel: box unticked again; tick, Restart: the program restarts with the slider enabled | new + hands-on |
| Q15 | The check box reads "Ignore Windows display scaling" | `U/test_batch3_C1.py::test_windows_scaling_box_matches_its_title` | covered |
| S83 | No window or its smallest size larger than the screen | `U/test_tool_windows_fit.py::test_the_window_and_its_smallest_size_fit_the_screen`, `U/test_main_window_fits.py` (all) | covered |
| S84 | 200 % on a small screen: contents not cut off | On hold (AU-56, D-STD-HOLD); known to fail in eight windows (G7) | gap (on hold by the user) |
| Q16 | Action summary images at 200 % and light mode checked first | Hands-on: Options → UI scale 200 % (Ignore Windows scaling on) and light mode; open a Configuration page with Map to vJoy, Map to Keyboard and a macro: the action images are readable and not white-on-grey; report if off | hands-on |
| S85 | F1 / Help → User Guide opens the User Guide; F1 in the Button Map opens only its guide | `U/test_help_guide.py::test_button_map_help_is_its_own_guide`; `U/test_menus.py::test_every_main_command_is_in_the_menu_bar`. Hands-on BMAP3-5-HANDS-ON: F1 on the main window opens the User Guide; F1 in the Button Map opens the Button Map Guide with only its topics; Help → User Guide has one Button Map topic | covered + hands-on |
| S86 | Every action has a help topic; menu paths in the help exist; removed things gone | `U/test_help_guide.py::test_every_action_plugin_has_a_topic`, `::test_menu_paths_in_the_guide_exist`, `::test_removed_or_wrong_things_are_not_in_the_help`, `::test_every_topic_has_a_section_title_and_body`; `U/test_batch3_C1.py` help tests | covered |
| S87 | On-screen text and Options descriptions use the glossary words | `U/test_glossary_words.py` (all) | covered |
| S88 | A new idea goes into the glossary before it appears on screen | A working rule for whoever writes text; `U/test_glossary_words.py` only catches the known wrong words, not new ones | gap (process rule, not program behaviour) |
| S89 | Help, About and the theme work in the built exe | `U/test_spec_hidden_imports.py::test_every_action_plugin_is_a_hidden_import`; `U/test_help_guide.py::test_about_shows_the_build_version`. Hands-on B-04: build the exe, start it, press F1 (User Guide opens with text), Help → About (version shows), dark/light switch works | covered (spec) + hands-on |
| Q17 | Test-plan rows W-04..W-09 retired for TRAY-ONE and glossary words | `U/test_batch3_C1.py::test_test_plan_rows_are_current` | covered |
| Q19 | `gremlin/fsm.py` and its test removed | Contradicted by the batch 2 gap-list correction (GL-279: fsm.py is used by double_tap, tempo, smart_toggle, hat_buttons, code_runner); `U/test_fsm.py` stays | gap (question for the user) |
| Q20 | Leftover file table accepted | Not behaviour | gap (no behaviour) |

## Hands-on checks from the batch plans (page 09)

- B1 (catchup-test-plan): Minimize to tray: Exit quits, X hides and keeps the window's place; X with the vJoy Viewer open quits; tray Run with an edited pane asks.
- B5b: Text to Speech under Tempo and in a macro speaks; Options shows "(default)" for a removed voice; Text to Speech on a keyboard key speaks.
- Batch 1 GL-058: Options opened while stopped, then a Text to Speech/Play Sound press: nothing is said or played.
- TRAY-ONE, MEM-HANDS-ON, OPT-U01, OPT-U02/W-11, OPT-U06, W-12, MENU-1/2, BMAP3-5-HANDS-ON, B-04: see the rows above.

## Counts (S1-S89)

89 statements: 48 OSC parked; of the 41 others, covered 27, new 11
(S51, S58, S59, S60, S63, S68, S73, S74, S76, S82, and S78 as an xfail),
hands-on only 1 (S79), gap 2 (S84 on hold, S88 process rule). Several covered
or new rows also carry a hands-on check (S65, S69, S74, S77, S81, S82, S85,
S89).
