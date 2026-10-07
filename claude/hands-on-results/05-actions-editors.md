# Hands-on results: 05 Actions and their editors  (agent H5, 2026-10-07)

Scope: every "hands-on" row of `claude/final-test-plan/05-actions-editors.md`
(30 table rows plus the batch list under it) and gap-list "Hands-on checks
needed" item 6 (GL-164). Spec: `claude/program-map/05-actions-editors.md`.

How: the real program, built off-screen (`QT_QPA_PLATFORM=offscreen`, Windows
fonts, 1600x950), one process per check with a temp USERPROFILE under
`.agent-logs/handson/H5/home-*`, `GREMLIN_OFFLINE=1`, hang tool on, 180 s cap.
Built on `test/journeys/_harness.py`: fake joystick driver
(`test/fake_hardware.py`), fake vJoy behind the output module (nothing reached
the real vJoy device), key and mouse output kept in the process, no hooks.
The screens were driven with QTest mouse clicks on the program's own windows
(rows, OK, X, Home, check boxes, the pane grip, right-click) and the QML
functions the menus call (File > New / Open / Open Recent / Quit, File >
Save). Probe scripts: `.agent-logs/handson/H5/probe_*.py` (runner
`run_probe.py`, helpers `h5lib.py`). Each probe's RESULT is saved as
`.agent-logs/handson/H5/<probe>-<part>.json`. Live log: `.agent-logs/H5.log`.
I looked at every screenshot named below with the Read tool.

| Row | What was checked | How (off-screen / real screen / fake hardware) | Result | Evidence |
|---|---|---|---|---|
| S8 | Right-click the Map to vJoy action header in the pane: title, the 3 quick adds "Add Map to vJoy / Add Macro / Add Chain" (the first 3 button actions in Options order), then "Add: Map to", "Add: Logic and Timing", "Add: Other", "Remove". Axis and Hat is left out because it is empty for a button. Each section's actions are in Options > Actions order (Map to: Keyboard, Logical Device, Mouse, Xbox; Logic: Change Mode, Condition, Double Tap, Reference, Smart Toggle, Tempo; Other: Description, Load Profile, Pause and Resume, Play Sound, Run Command, Text to Speech) | off-screen, real right-click | PASS | s8_menu.png, s8_menu_timing.png, s8_menu_other.png; probe_pane-s8.json (sections, options_order) |
| S13 | A stick whose module claims nothing: no rows; text "This window only shows what the input module passes. Right-click the card → Module → Module Setup…, …". On pJoy, Type = Macro: no rows, "No inputs match the current filters." and Clear Filters. A click on Clear Filters brings the 72 rows back, and the Type box returns to All types | off-screen | PASS | s13_no_claims.png, s13_filter_macro.png, s13_cleared.png; probe_list-s13.json |
| S19 | Appearance LEDs and bars on (the default). Stick button 1 pressed: Button 1's LED is on (green). X axis moved: its bar value is 1.0. With Run on and the button pressed: LED off, value 0 (vJoy button 1 still held, so the input did fire) | off-screen, fake hardware | PASS | s19_led_on.png, s19_axis_bar.png, s19_running.png; probe_list-s19.json |
| S20 | Click on parent row Button 1 (2 bindings): pane shows 2 bindings. Click on child row (seq 1): pane shows that 1 binding. Add Action on Button 3 (no actions): pane opens, "New action" | off-screen, real clicks | PASS | s20_parent.png, s20_child.png, s20_add_action.png; probe_pane-s20.json |
| S22 | Edit in the pane, then click OK: the profile changes (3→9) and is unsaved (profileContainsUnsavedChanges = true); the pane stays open on a clean copy. Close pane after OK ticked, edit, OK: written (11) and the pane closes | off-screen, real clicks | PASS | s22_after_ok.png, s22_closed_after_ok.png; probe_pane-s22.json |
| S23 | Close pane after OK ticked, pane grip dragged (paneUnits 560→710), then a restart with the same profile folder: paneUnits 710 and the box is still ticked | off-screen, real drag, restart | PASS | s23_dragged.png, s23_restart.png; probe_pane-s23a.json, probe_pane-s23b.json |
| S26 | With unsaved pane edits, each of these asks "Unsaved Changes / This control has changes that are not saved." with Save / Discard / Cancel: X, another row, Home toolbar, File > Open (dialog accepted), Open Recent, Quit. File > New asks for the profile first and then for the pane. Cancel keeps the edit (draft still dirty, profile unchanged, still on the page). Discard drops it. Save writes it. | off-screen, real clicks + menu functions | PASS | s26_x_dialog.png, s26_row_dialog.png, s26_home_dialog.png, s26_open_dialog.png, s26_quit_dialog.png; probe_pane-s26.json |
| S28 | A clean pane closes when the toolbar mode changes. A pane with changes stays open, and its title reads "Button 2 (in Default)" while the mode shown is Combat. OK writes to Default; Combat is untouched | off-screen | PASS | s28_in_default.png; probe_pane-s28.json |
| S30 | A clean pane is open; File > Open loads another profile: no question, and the pane is closed | off-screen | PASS | s30_after_load.png; probe_pane-s30.json |
| S44 | Press and Release both clicked off on a button's Map to vJoy: the draft holds both off, but "Off: never runs" does not show until OK or the pane is opened again | off-screen, real clicks | FAIL | s44_off_never_runs.png (both off, no label), s44_after_ok.png (label shows); probe_editors-s44.json |
| S46 | X Axis with a Map to vJoy, Treat as Button clicked: "Treat as Button? Changing how this input is treated removes its action." with Change and remove / Cancel. Cancel keeps the action. Yes removes it and the behaviour is button | off-screen, real clicks | PASS | s46_treat_as_asks.png, s46_after_yes.png; probe_editors-s46.json |
| S48 | Binding header trash: "Remove Binding? Remove this binding and its action?" with Remove / Cancel. Cancel keeps it. Remove removes it from the draft; the profile is untouched until OK | off-screen, real clicks | PASS | s48_remove_binding_asks.png; probe_editors-s48.json |
| S49 | Hat as Buttons in 8 way with an action on North-East, 4 way clicked: "Switch to 4 Way — 1 action on the diagonal directions … will be removed". Cancel keeps 8 way and the action | off-screen, real clicks | PASS | s49_hat_8way.png, s49_4way_asks.png; probe_editors-s49.json |
| S53 | vJoy module claims buttons 1-10. A saved Map to vJoy to button 20 shows "Output not claimed" in the pane and keeps 20. A claimed target (3) shows no note. The picker offers only the 10 claimed buttons | off-screen | PASS | s53_output_not_claimed.png; probe_editors-s53.json |
| S62 / GL-096 | X and Y axes share one Merge Axis. The pane says "Shared with pJoy Pro Y Axis (Default). OK changes it for every input that uses it." Operation set to Maximum: the profile is unchanged until OK. After OK both inputs use the same id with maximum, and they still do after save and reload | off-screen | PASS | s62_shared_merge.png; probe_editors-s62.json |
| S66 | Add an empty Merge Axis in the pane, OK, then File > Save: "Unfinished Actions — 1 action is not finished… • Merge Axis: Both axes have to be assigned." with Save without them / Cancel. Cancel writes nothing. Save without them writes the profile without the merge-axis | off-screen | PASS | s66_empty_merge_in_pane.png, s66_save_asks.png; probe_editors-s66.json |
| S69 / GL-105 | Profile whose Map to vJoy type was changed to "frobnicator-9000": it opens. An "Open Profile" box says "This profile has actions of a type this program doesn't have: frobnicator-9000…", and system.log has the same warning. The list shows "Unknown Action". Its editor says "This program has no 'frobnicator-9000' action. It is kept as it is…". Save writes the action block back unchanged. At Run a press does nothing (no vJoy write) | off-screen | PASS | s69_notice_window.png, s69_pane_note.png; probe_editors-s69.json |
| S74 / Q4 (B5a) | Same as GL-164 (below): a new key shows one empty binding, the first action is added through the editor's own Add Action, OK writes it, and it is still there after save and reload | off-screen, Add Key via the hook callback | PASS | gl164_new_key.png, gl164_action_added.png, gl164_after_ok.png; probe_keyboard-gl164.json |
| S75 | Keyboard Delete Key (row ×): "Delete Key? Delete F and its actions in this mode?" with Delete / Cancel. Cancel keeps F and its action | off-screen, real clicks | PASS | s75_delete_key_asks.png; probe_keyboard-s78.json |
| S77 | Rename on the F row ("Fire Key"): the name shows under F on the row and is in the saved profile file | off-screen | PASS | s77_renamed.png; probe_keyboard-s78.json (name_in_file true) |
| S78 / Q5 (B5a) | Keyboard page draft: an action added to G and not OK'd. A click on the F row asks "Unsaved Changes — The action editor has changes that are not saved." with Discard / Cancel. Cancel stays on G with the draft. Discard goes to F, and the profile is unchanged | off-screen, real clicks | PASS | s78_switch_key_asks.png; probe_keyboard-s78.json |
| S83 (C4 relative) | Map to vJoy Relative on the X axis, with nothing else writing to vJoy 1 in that Run: the axis never moves. The loop checks `vjoy_owned()`, which is False because the device is opened only by a write, so it ends at once (writes: none, vJoy 1 never opened). Map to Logical Device Relative works: about 0.1/s at Speed 1.0 while held off-centre, and it stops when centred | off-screen, fake hardware + fake vJoy | FAIL | probe_run-s83_vjoy.json (calls: `_relative_ok` False, `vjoy_opened_by_relative_alone` []), probe_run-s83_logical.json |
| S91 / GL-047 | Tempo (long 1 s) on button 1, Run, button held, Stop after 0.3 s: Gremlin holds no vJoy device, and nothing is written in the next 1.5 s or on release | off-screen, fake hardware + fake vJoy | PASS | probe_run-s91.json |
| S102 | Button 3 with no actions shows "No actions". At Run, pressing it writes nothing to vJoy, while button 1 still works | off-screen, fake hardware | PASS | s102_no_actions.png; probe_list-s102.json |
| S104 / Q2 | No vJoy device (fake driver with no vJoy ids): a profile with Map to vJoy opens with no error, and the action is kept ("vJoy 1 · Button 1 (no output module)"). It opens in the pane. Options still lists Map to vJoy, and Add Action does not offer it. Save keeps map-to-vjoy in the file. Run then a press: no writes, no errors | off-screen, fake "no vJoy" | PASS | s104_no_vjoy.png; probe_run-s104.json |
| S105 | Stick unplugged (fake driver loses it, device-list update run): the profile keeps its actions, also after save and reload. But (1) the open Configuration page still titled "pJoy Pro" switches to the other stick (Throttle), so Button 1 reads "No actions" and the Throttle's Merge Axis shows on "X Axis"; (2) a Merge Axis reading the unplugged stick's axis still uses its last value (0.5 = avg(1.0, 0)) instead of centre (0.0) | off-screen, fake hardware + fake vJoy | FAIL | s105_after_unplug.png; probe_list-s105.json (current_device_after_unplug, title_name_after_unplug, merged_plugged 0.5, merged_unplugged 0.5) |
| Q6 (C4) | Type box: All types, Map to vJoy, Map to Keyboard, Map to Mouse, Map to Xbox, Macro, Change Mode, Other, No actions. "1 action — …", "2 actions — …". With "Move inputs with no actions to the end" on, the heading is "No actions" ("70 controls — click to add") and the rows read "No actions" | off-screen | PASS | q6_type_box.png, q6_no_actions_heading.png, q6_list_top.png; probe_list-q6.json |
| Q8 (B7) | Unsaved pane, then each tool: History Restore ("Restore?" in History, then the main window asks "Unsaved Changes … Discard / Cancel"), Auto Mapper "Create 1:1 Actions" and Device Pack import all ask first. Cancel keeps the pane edit and runs nothing (History: Button 1 still 7). Discard closes the pane and the tool goes on | off-screen | PASS | q8_history_asks.png, q8_automapper_asks.png, q8_devicepack_asks.png; probe_tools-q8.json |
| Q11 (B5a) | Pane open, then Run (toolbar click): the pane closes. A row click while running opens it read-only: "Profile running: stop it to edit", no OK, no "Close pane after OK", and the remove buttons are disabled. Keyboard page while running: same text, no OK | off-screen, real clicks | PASS | q11_running_pane.png, q11_keyboard_running.png; probe_pane-q11.json, probe_keyboard-s78.json |
| Q20 | Child row Delete: "Delete Action? Delete Map to vJoy → vJoy 1 · Button 2 from this binding?" with Delete / Cancel. Cancel keeps it. Delete removes only that one. The row open in the pane has no Delete (S31) | off-screen, real clicks | PASS | q20_delete_asks.png; probe_pane-q20.json |
| B5b | Text to Speech is offered on a key and added there through the editor. At Run a key press queues "hello from F". A Tempo short press and a long press (timer) queue "tempo short" / "tempo long", all on the main thread (the speech engine's input was recorded, not spoken) | off-screen, fake hardware | PASS | b5b_tts_on_key.png; probe_keyboard-tts.json |
| C4 Merge Axis / Deadzone | Merge Axis and Dual Axis Deadzone: Rec / replace sets an axis from the selected input (X, then Y selected with the pane kept). "+" makes a new, selected instance ("Merge Axis 1", "Dual Axis Deadzone 1"). Switching to the instance another input uses shows its axes (3, 4). OK, save and reload keep it | off-screen, real clicks | PASS | c4_merge_recorded_wide.png, c4_merge_plus.png, c4_deadzone_recorded.png, c4_deadzone_plus.png; probe_c4-merge.json, probe_c4-deadzone.json |
| GL-164 (gap list item 6) | Keyboard page: Add Key, then F. F is listed and shown with one empty binding and OK. Map to vJoy is picked in the binding's drop-down and added with Add Action: not in the profile until OK, written by OK, kept after save and reload | off-screen, Add Key via the hook callback | PASS | gl164_new_key.png, gl164_action_added.png, gl164_after_ok.png; probe_keyboard-gl164.json |
| S104 real PC | A profile with Map to vJoy on a PC or VM with no vJoy driver installed | — | PERSON | probe_run-s104.json (the fake check passed) |
| B5b audio | Speech is actually heard (voice, volume, rate) | — | PERSON | probe_keyboard-tts.json (queued correctly) |
| S83 feel | Relative axis on a real stick: speed feels right, stops when centred | — | PERSON | probe_run-s83_logical.json |
| S19 real stick | LEDs and bars follow a real stick | — | PERSON | s19_led_on.png |
| S105 real unplug | Pull a real stick's USB while its Configuration page is open | — | PERSON | s105_after_unplug.png |

Counts: PASS 30, FAIL 3, BLOCKED 0, PERSON 5. The batch items GL-096,
GL-105, GL-047, B5a, B7 and C4 Type box/relative are in the rows named above.

## Failures

**S44 "Off: never runs" only shows after OK** (spec 05 S44). In the pane,
switching Press and Release both off on a button's Map to vJoy leaves the
draft at both-off (`activateOnPress`/`activateOnRelease` read False), but the
label stays hidden (`visible: false`) until OK rebuilds the pane, or the pane
is opened again. Likely cause: `gremlin/ui/action_model.py:365-376`. The
`_set_activate_on_press` / `_set_activate_on_release` setters change the data
but never emit `actionChanged`, which is the NOTIFY of both properties
(`action_model.py:434-446`). So `ActionNode.qml:204-209` never re-reads them.
Suggested fix: emit `self.actionChanged.emit()` in both setters when the value
changed. Test: set both off on an ActionModel and check that the signal fired
(or that the label shows off-screen).

**S83 Map to vJoy Relative never moves the axis on its own** (spec 05 S83;
C4 "relative axis on vJoy"). `RelativeAxisLoop.relative_axis_thread`
(`action_plugins/common.py:127-134`) calls `_relative_ok()` before its first
write. For Map to vJoy that is `output.vjoy_owned(id)`
(`action_plugins/map_to_vjoy/__init__.py:128-130`). It is True only when
Gremlin already holds the device, and the device is opened only by a write
(`gremlin/modules/output.py:371-383, 460-488`, "a read never opens one, only
writes do"). In a Run where nothing else has written to that vJoy device
(no vJoy Initial Values, no absolute axis or button mapped to it), every loop
ends at once. Probe: `_relative_ok` False on each loop, no writes, vJoy 1
never opened. The Logical Device version (no ownership check) works. Suggested
fix: let the loop's first `_relative_write` open the device (for example, treat
"not opened yet" as OK until a write has failed), or open the claimed device
when the relative input starts. Test: Run with only a relative Map to vJoy,
deflect the stick, and check that the vJoy axis moves. Note: after the device
was opened by a button, the fake vJoy (`test/journeys/_harness.py`
FakeVJoyControl) returned None for an axis that was never written, and the
loop thread raised `float(None)`. That is a harness limit (a real vJoy returns
a number), not a program bug, so speed on vJoy was checked on the Logical
Device only.

**S105 unplugged stick: the open page shows another stick, and Merge Axis
does not read centre** (spec 05 S105). (1) With pJoy Pro's Configuration
page open, pJoy was unplugged (fake driver, then
`EventListener()._run_device_list_update()` as the device thread does).
`uiState.currentDevice` switched to the Throttle, but the title still says
"pJoy Pro". So the page lists the Throttle's actions under pJoy's name
(Button 1 "No actions", the Throttle's Merge Axis on "X Axis"), and an edit
there would go to the Throttle. Cause: `gremlin/ui/backend.py:84-100`
(`UIState._device_change` picks `devices[0]` when the shown device is gone,
and `Main.configTitleName` is not updated). Suggested fix: when the shown
device goes away, keep the page on it (empty or read-only, "not plugged in"),
or close it the way `closeDeletedDevice` does; never switch the device under
the title. The profile itself keeps the actions, also after save and reload:
that part passes. (2) A Merge Axis on the Throttle reading pJoy axis 1 (last
value +1.0) and Throttle axis 1 (0) gave 0.5 before the unplug and still 0.5
after it. S105 says an unplugged stick's axes read centred. Cause:
`gremlin/modules/inputs.py:28-31` reads `input_cache.Joystick()[guid]` for
an unplugged stick: the claim still allows it, and the cache keeps the last
value (02 G7: `Joystick.devices` never drops an unplugged stick). Watch out:
02 S28 says "axes stay where they were" for the let-go on unplug. The lead
should confirm with the spec that the S105 "read centred" rule applies to
action reads (Merge Axis/Deadzone) before fixing, for example by returning
0.0 in `axis_value` when `hardware.device_connected(guid)` is False.

## Blocked

None. The real vJoy device was never used: all vJoy rows used the fake vJoy
of `test/journeys/_harness.py`, so the user's vJoy and HidHide setup were not
touched.

## Needs a person

- **S104 / Q2 on a real PC without vJoy**: on a PC or VM with no vJoy driver,
  open a profile that has Map to vJoy actions. It should open with no error,
  the rows should show "(no output module)", and File > Save should keep them
  (check that the .xml still has `type="map-to-vjoy"`).
- **B5b speech**: give a key a Text to Speech action ("hello"), Run and press
  the key: the voice should be heard once. Do the same on a Tempo long press.
- **S83 relative axis feel**: with a real stick, set Map to Logical Device
  Relative (Speed 1.0). Hold the stick off-centre: the Logical Device axis
  should move at a steady speed and stop when you let go. Repeat with Map to
  vJoy Relative and watch the vJoy Viewer. Today it should not move unless
  something else writes to that vJoy device in the same Run (FAIL above).
- **S19 real stick**: with Appearance LEDs on, press and move a real stick:
  the row LEDs and bars should follow, and nothing should light while
  running.
- **S105 real unplug**: with a stick's Configuration page open, pull its USB
  cable. Look at whether the page title and the rows still belong to that
  stick (today the rows switch to another stick: FAIL above).

## Notes (not failures)

- The default pane width (560 units at 1600x950) clips the Merge Axis
  editor's row: the "Second axis" Rec button and the child Add Action are
  off the right edge (`c4_merge_recorded.png`). They work once the pane is
  widened (`c4_merge_recorded_wide.png`). This is N22 (editor control layout,
  on hold).
- Add Action → Merge Axis on X reused the Merge Axis that Y already had
  (ReuseByDefault, S59/Q1), with the "Shared with…" note. That is as
  specified.
- After save and reload of a profile with a second mode, the toolbar showed
  "Combat", not "Default" (`probe_pane-s28.json` mode_at_start). That is page
  04 (startup mode "Use Heuristic"), not checked here.
- The Home card for vJoy 1 sometimes read "In use by another program"
  (`s69_opened_warning.png`). That is the real vJoy status query on this PC
  (another process may hold vJoy 1), not this page. The probes never opened
  the real device.
