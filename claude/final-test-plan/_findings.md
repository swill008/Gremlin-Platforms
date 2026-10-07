**All fixed in the final-phase fix round (see the commit after 5980fde5); questions answered 2026-10-07 (claude/decisions.md).**

# Final phase: bugs found and questions (collected by the lead)

## Bugs to fix (strict xfails in test/unit/test_final_*.py)
| Id | Spec | What is wrong | Likely owner file |
|---|---|---|---|
| FINAL-03-1 | 03 S16 | a vJoy read back as an input is dropped when its output module file is missing or has no boundGuidLocal (runtime.reload skips modules without a bound id; _bind_live_physical uses physical_devices only) | gremlin/modules/runtime.py |
| FINAL-05-1 | 05 S43 | the binding's Note (root action label) shows on no row (catalog rows have no root label; Keyboard row shows the input name) — needs user answer on which row | gremlin/ui/binding_catalog.py |
| FINAL-05-2 | 05 Q19 / D-05-Q19 | Chain times out on time.time(), not gremlin.clock (GL-265 marked done but Chain wasn't moved; test_action_fixes patches chain.time.time) | action_plugins/chain/__init__.py |
| FINAL-05-3 | 05 Q18 | unused InputItemModel.newActionSequence (ui/profile.py) and ActionPriorityListModel (ui/action_model.py) still present (GL-261 rest) | gremlin/ui/profile.py, gremlin/ui/action_model.py |
| FINAL-07-1 | 07 S56 | Undo steps N gives only N-1 undos (pushHist caps saved states at histCap, start state included) | qml/VkbRigEditor.qml |
| FINAL-07-2 (no xfail) | 07 S20/S23 | HardwareProfile.save lets the store's OSError escape the Qt slot instead of returning False ("Not written" shows only by accident) | gremlin/ui/hardware_profile.py |
| FINAL-02-1 | 02 S40 / D-02-Q8 | an event takes the mode current when the main thread handles it (GL-065 design), not when it arrived — user question first | gremlin/event_handler.py |
| FINAL-02-2 (order) | — | test_audit3_run_stop::test_a_step_stuck_in_a_driver_ends_the_other_macros and ::test_stop_during_a_step_in_progress_ends_the_macro fail after test_device_scan, test_batch2_b2b, test_twin_devices, test_startup_messages, test_batch2_b2a_input_events, test_hidhide_group, test_xbox_pads_told_apart, test_stage1_app_profile in one process | test isolation |
| FINAL-09-1 | 09 S78 | IconCheckBox.qml names the font family itself instead of Style.iconFont | qml/IconCheckBox.qml |

## Small fixes found (no xfail)
- 09 Q15 / D-09-Q15: the stored Options description in gremlin/ui/windows_scale_option.py starts "Disable Windows display scaling…"; should be "Ignore Windows display scaling…" (the check box already says Ignore).

## Spec text to bring up to date (lead, no behaviour change)
- 06 S55: "restart Gremlin-Platforms" → "restart the program" (D-02-Q17, glossary D12).
- 06 S8, S26, S30, S31, S53, S70, S85: remove "open gap" / "today …" notes; fixed in batch 1.

- 08 S98 (→Q7), S65 (→Q3), S78 (→Q2/F1), S79 (→Q20/A3), S100 (→Q4), S39 (→Q1): reword section 8 lines to the decisions (code and tests follow the decisions).

- 02 S9 (→Q6), S16 (→Q3), S32 (→Q2), S50 (→Q4), S64 (→Q9), S94 (→Device ID): reword to the decisions.

- 01 S12: the start-up failure page button reads "OK" (glossary), not "Quit". 01 S127 and the copy_legacy_modules line in section 2: retire (GL-272 removed it; nothing ships). 01 S39: drop "also when opened from the Button Map" (Button Map has its own Options pane, 07 Q17).

## Ideas for the proper process (not bugs)
- 06 Q19/S4 (P06): output.write_vjoy / write_xbox don't check for a Run themselves; the rule holds because every sender stops at Stop. A guard in the output module could make it explicit (check Output View test writes first).

## Questions for the user
- 09 S51 (P09): a new sound playback mode applies to the next sound taken after Options closes; sounds already queued behind a playing one in Sequential still wait. Is that "at once" enough?

## Decision corrections (no question needed)
- D-09-Q19 (remove gremlin/fsm.py): moot — fsm.py is used (double_tap, tempo, smart_toggle, hat_buttons, code_runner; GL-279 corrected in batch 3). Record the decision as superseded.
- 03 S41 (P03): presses on a vJoy while its Output Module Setup is open still tick the control and light the row. Should output modules ignore presses there?
- 03 S71 (P03): Keyboard and OSC cards show only with a module file or show-stubs on (same as sticks). Or always shown?
- 03 S102 (P03): one Calibration capture at a time is per axis (Extrema stops Center on the same axis, not on another axis). Per axis meant?
- 05 S43 (P05): the binding's Note (its root action label) shows on no row today. Which row should show it: the Configuration list's input row, the Keyboard row, both — or drop S43?
- 02 S40 vs GL-065 (P02): should a hardware event run in the mode that was current when it ARRIVED (D-02-Q8) or when the main thread handles it (batch 1 GL-065, the listener no longer asks the mode manager)? Differs only when a mode change and a press race.
