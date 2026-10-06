# Catch-up test plans

One section per catch-up batch (see "ONE-TIME CATCH-UP" in `claude/todo.md`).
Each line: what was fixed, how it is checked (automatic test and, where
useful, a hands-on check). The final full test plan is built from these.

## Batch 1 – the three redesigns (2026-10-06)

New owners: `gremlin/run_scope.py` (Run lifecycle), `gremlin/modules/store.py`
(module files), the `Library` in `gremlin/profile.py` (actions). Guard tests:
`test_run_scope_only`, `test_module_store_only`, `test_library_only`
(its `_WAITING` list may only shrink; left: device_pack `_apply_wires`
(GL-099, batch 2) and swap_devices (batch 2)).

### Run lifecycle (gap list section 3)

| GL | Fix | Check |
|---|---|---|
| 046 | One Run number; Stop runs the map's 7 stages in order, safe twice | `test_stop_runs_the_stages_in_the_maps_order`, `test_stop_twice_runs_each_step_once`, `test_stop_disconnects_first_and_releases_the_drivers_last` |
| 047 | Tempo / Double Tap / Smart Toggle timers are Run timers; MainTimer tracked | `test_a_timer_never_fires_after_stop[*]`, stage1 `test_a_tempo_timer_never_fires_after_stop`, journey j10, `test_main_thread_timers_are_listed_and_shut_down`. Hands-on: hold a Tempo button, Stop before the long press: nothing fires, vJoy free |
| 048 / 061 | Macro that ends early lets go of its keys; relative-axis loops end at Stop and never block the window | `test_a_macro_that_ends_early_lets_go_of_its_keys_at_once`, `test_the_vjoy_relative_loop_ends_with_stop_and_run_again`, `test_a_new_loop_does_not_wait_for_the_old_one[*]` |
| 049 / 064 | Held keys and buttons tracked in one place (run_scope), released at Stop; nothing tracked with no Run | `test_a_key_a_script_holds_is_released_at_stop`, `test_keys_sent_with_no_run_on_are_left_alone`, `test_a_mouse_button_held_at_stop_is_released`, audit3 macro key tests |
| 050 | Logical Device values back to neutral at Stop | `test_logical_device_values_go_back_to_neutral` |
| 051 | Release actions waiting at Stop are dropped | `test_release_callbacks_waiting_at_stop_are_dropped` |
| 052 | Fresh mode stack per Run; temporary modes end with Stop | `test_the_mode_stack_starts_fresh_and_temporary_modes_end_with_stop` |
| 053 | Toolbar shows the new profile's start mode after Load/New | stage1 toolbar-mode tests; hands-on HELP-BUG-HANDS-ON |
| 054 | A failed Run start stops cleanly, one error, right status | stage1 failed-start tests |
| 055 | Unfinished actions left out of the Run, one log line naming the input | `test_an_unfinished_action_is_named_when_the_run_is_built`, stage1 `test_run_skips_unfinished_actions`, Reference placeholder test |
| 056 | Initial Values always written through the output module | stage1 Initial Values tests |
| 057 | Load Profile action loads after its event; a Stop before drops it | `test_load_profile_runs_the_profile_after_its_event`, `test_a_stop_before_it_drops_the_load` |
| 058 | Sound / speech asked for with no Run are dropped | `test_a_sound_asked_for_with_no_run_on_is_dropped`, `test_speech_asked_for_with_no_run_on_is_dropped`, stage1 GL-058 tests |
| 059 | Logical Device values and the vJoy device list locked | `test_relative_steps_from_two_threads_add_up`, `test_two_threads_opening_one_vjoy_device_get_the_same_one` |
| 060 / 065 | Mode read as a snapshot; listener no longer asks the mode manager | `test_the_handler_stamps_the_current_mode_on_hardware_events`, `test_the_listener_does_not_ask_the_mode_manager` |
| 062 | Script folders off the path at Stop; old scripts forgotten on profile change | `test_script_folders_are_taken_off_the_path_at_stop` |
| 063 | Quit stops once and creates nothing just to stop it | `test_quitting_stops_once_and_makes_nothing_to_stop_it`; hands-on: quit while running, no vJoy held, no Xbox pad left |
| 084 | Output modules saved while running apply at once | `test_output_modules_saved_while_running_apply_at_once` + store side below |
| — | Options no longer turns speech on while stopped | Options opened while stopped: speech asked for is dropped |

### Module files (gap list section 4)

| GL | Fix | Check |
|---|---|---|
| 067 / 068 | One store, one writer, one History hook; refused swap falls back | guard `test_module_store_only`; a save whose swap fails is written directly with one History entry |
| 069 / 094 | Delete Device always keeps a JSON copy; removes recovery and photo safety copies | stage1_modules GL-069/094 tests |
| 070 / 079 | Damaged file: Import Image and Button Map Save refused before any photo/picture is touched | stage1_modules GL-070/079 tests |
| 071 | Button Map follows outside changes; in Edit, Save asks "Module File Changed" (Keep mine / Take theirs / Cancel) | stage1_button_map GL-071 tests, smoke parts "outside" |
| 072 | Pack import onto a damaged input module refused; damaged output skipped with a note | `test_an_import_onto_a_damaged_module_file_is_refused`, `test_a_damaged_output_module_file_is_left_alone`, stage1_history_pack GL-072 |
| 073 | Pack pictures written whole or not at all | `test_a_pack_picture_is_written_whole_or_not_at_all` |
| 075 / 076 / 090 | One stale-id filter; twins looked up by id; card key from the store | `test_batch1_module_pages`, `test_twin_devices`; no "looked up without its device id" warning while Home loads |
| 077 | Import into a renamed stick writes the file it uses | stage1_modules GL-077 |
| 078 | Module Setup Import Image staged; Cancel puts the old photo back; own safety copy per window | stage1_modules GL-078, smoke part "setup" |
| 080 | Start Fresh and a failed pack import's clean-up are History entries | stage1_modules GL-080, `test_the_clean_up_of_a_failed_import_is_in_history` |
| 081 | History Restore of a module file binds its device again | `test_a_restored_module_file_is_the_one_its_device_uses_again` |
| 082 | A save's "before" pictures are read before the write | stage1_history_pack GL-082 |
| 083 | A failed claims read keeps the last good claims, logs once | stage1_modules GL-083 |
| 085 | Pictures found only where their reference points | stage1_modules GL-085 |
| 086 | Pack output key is the file the output really uses | device pack export test; old packs still match by name |
| 087 / 095 | Import Undo tied to device and window; one Undo Import per area, no name clash | stage1_modules GL-087, device pack undo tests |
| 088 | Calibration lists both sticks on one file; the second can be picked and saved | `test_calibration_lists_both_sticks_that_share_a_file`, `test_calibration_window_picks_the_second_stick_on_a_shared_file` |
| 089 | One write, one History entry per Save Module; no library duplicates | stage1_modules GL-089 |
| 091 / 092 / 093 | One binding-clear; store owns deleted devices folder; no private cross-module imports | guard tests, `store.deleted_items()` test |

### Actions (gap list section 5)

| GL | Fix | Check |
|---|---|---|
| 096 | OK on a shared action changes it for every input; editor shows "Shared with …" | audit3_actions_undo A1 tests, `test_a_shared_action_says_who_else_uses_it`. Hands-on: two axes share a Merge Axis, edit in one, OK: both changed, also after save and reload |
| 097 | Picking / reusing a shared action gives the pane a copy; Cancel changes nothing | action_editor_fixes GL-097 tests, stage1 `test_merge_axis_reused_in_the_pane_then_cancel_changes_nothing` |
| 098 (part) | OK refused when the input changed under the pane (safety net) | Library `DraftOutdated` tests; closing the pane first is batch 2 |
| 100 | Undo / History Restore put a shared action back for every input | audit3_actions_undo GL-100 |
| 101 / 102 | One removal rule (`Library.release`); new actions go into the edited input's library | guard `test_library_only`, profile unused-action tests |
| 103 | Removed Chain sequence released from the library | `test_a_removed_chain_sequence_is_released_from_the_library` |
| 104 | Save with the pane open leaves the draft alone | audit2_saving GL-104 |
| 105 | Unknown action type: profile opens, action kept and saved back, warning shown (spec 05 S69 updated to decision 04 Q7) | unknown action tests; hands-on: open a profile with a made-up action type |
| 108 | Empty Logical Device: macro step / condition say "Add a Logical Device control first.", no Button 1 | `test_a_new_macro_step_on_an_empty_logical_device_creates_nothing`, `test_a_logical_device_macro_step_on_an_empty_device_asks_for_a_control`, condition test |
| — | Pulse release is a Run "fire" timer: Stop sends it before drivers reset | audit2_macros pulse test |

### Moved to batch 2
GL-074 (Logical Device / OSC rows owned by the Profile), GL-106 (Keyboard
page pane), GL-098 rest (Auto Mapper, History Restore, Device Pack close the
action pane first, asking about changes; needs Main.qml + 3 dialogs),
GL-099 / GL-109 (Device Pack all-or-nothing), GL-066 (speech engine
ownership: decided program-wide; queue per Run, as coded).

### Glossary checks for batch 3
"Module File Changed", "Keep mine" / "Take theirs", "Shared with …",
"Add a Logical Device control first.", "Started fresh: the damaged module
file of X was kept as <file>", "This input was changed while its action
editor was open…", "Open Profile" warning text.

### Batch-end run
Full suite in random order + lint baseline: see the commit message.

### Notes for batch 3 (collected during batch 2)
- help_topics.js Macro topic (~135): "A Joystick step acts like the stick itself: it only does something for controls the stick's input module claims." (GL-163, D-06-Q14)
- help_topics.js Options topic (~272): drop "Turn HidHide on at start"; point to Tools → Device Setup → HidHide (Automatically Start) (GL-135).
- help_topics.js Text to Speech topic: works on keyboard keys too (GL-197).
- Screens that build device names themselves move onto gremlin.ui.device_names.shown_name(guid): input_monitor.device_name, input_pairing.device_label, QML displayName helpers (GL-124 follow-up).
- Glossary check for batch 2 texts: "(default)", "Windows speech is not available, so nothing is said.", the Options HidHide pointer, "HidHide Automatically Start", "left out (see message)", "Gremlin's Xbox pad", "(not claimed)".
- help_topics.js Home topic: Delete Device is not on vJoy/Xbox cards; the Logical Device card has no Module Setup, Calibration, Auto Mapper, Device Information or Swap Device (GL-146, GL-147).
- Open question for the user (B3): cards with no module file still show the device's own counts; 03 Q8 "always claimed counts" could mean they should show 0.
- Open question for the user (B4, GL-040): a script's top-level code can still freeze the program when loading or adding it. Decision D-04-Q13 says it needs a design (read variables without running the script, or a time limit). Not fixed in batch 2.
- Open question for the user (B1, GL-116): if the other copy can't be closed, the same Yes / No / Cancel box asks again starting "The other copy could not be closed." (Yes tries again).

## Batch 2 – urgent fixes and behaviour/UX by subsystem (2026-10-06)

9 agents, file owners in `claude/catchup-batch2-rules.md`. New test files:
`test/unit/test_batch2_*.py`. Each agent checked its new tests fail on the old code.
Spec text aligned with decisions: 02 S56 (06 Q10), 07 S57 (Q3), S91 (Q19), S95 (Q1).

| Area | GL | Check (automatic) | Hands-on |
|---|---|---|---|
| B1 shell & settings | 026, 033, 034, 045, 110-114, 116-118, 157, 176, 193, 311, 098/169/171 (Main side) | test_batch2_B1, test_stage1_app_profile (tray tests now use a spontaneous close) | Minimize to tray: Exit quits, X hides and keeps the place; X with the vJoy Viewer open quits; tray Run with an edited pane asks |
| B2a input events | 035, 036, 037, 120-128, 131, 137, 172 | test_batch2_b2a_input_events | throttle at 80% before Run; keys keep working while busy; key after Ctrl+Alt+Del; a sent key doesn't fire another binding |
| B2b devices & HidHide | 035, 045, 124, 132, 133, 134, 136, 148 | test_batch2_b2b | HidHide reload timing on plug/unplug; Device Information with a left-out vJoy and an own Xbox pad; Calibration "(not claimed)" |
| B3 modules & Home | 038, 043, 139-147, 170 | test_batch2_b3, test_batch2_b3_typing, test_stage1_modules | type "Fire" in Keyboard Module Setup: no keys ticked; Run then Delete Device: refused |
| B4 profiles, modes, scripts | 027, 028, 039, 074, 119, 129, 130, 149-159, 171 (models) | test_batch2_b4 | auto-load: clicking into Gremlin keeps the Run; Undo Delete Mode; vJoy Behavior switch while running shows the note |
| B5a action pane & locking | 044, 098, 106, 160, 164, 166, 169, 171, 194 | test_batch2_b5a, test_batch2_b5a_screens | Keyboard page: Add Key then first action + OK; switch keys with changes asks; Run with a pane open shows read-only |
| B5b action logic & speech | 042, 135, 161-163, 165, 167, 197-199, 310, 312 | test_batch2_B5b, test_stage1_runtime | TTS under Tempo/macro speaks; Options "(default)" voice; HidHide pointer row; TTS on a keyboard key |
| B6 Button Map | 030, 043, 138, 173-175, 177-184, 188, 196 | test_batch2_B6, test_stage1_button_map, rig golden, j09 | mirrored copy then one Ctrl+Z; Device Pack preview with a large photo; Choose Photo then Undo |
| B7 History, Device Pack, Auto Mapper | 031, 032, 041, 098 (dialogs), 099, 109, 115, 187, 189-192, 195, 313 | test_batch2_b7, test_stage1_history_pack, test_auto_mapper, test_history_window | large history files: no freeze; tools ask Discard/Cancel with an unsaved pane; import, save Button Map, Undo Import asks; restore log level / UI scale applies at once |

Guard tests: `test_library_only` `_WAITING` is now empty.

Not done in batch 2: GL-040 (script top-level code can freeze: needs a design, user question), GL-153 measuring part, GL-045 History-limits-on-main-thread note (safe through the config lock), GL-029/168/185/186/201 (features / on hold).

Open questions for the user at batch end: GL-040 design; GL-116 re-ask box; cards with no module file (03 Q8); `rig_chips.fullNameOf` adds EVO R part names to hover text on every device (07 RB10 remainder) — drop it?
