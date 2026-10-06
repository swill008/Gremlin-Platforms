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
