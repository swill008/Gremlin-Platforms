# Hands-on results: 04 Profile and modes + gap-list item 7 (GL-053, GL-016)  (agent H4, 2026-10-07)

Scope: every "hands-on" row of `claude/final-test-plan/04-profile-modes.md` (section 8,
decisions, batch table) and the `claude/test-plan.md` rows HELP-BUG-HANDS-ON,
SAFE-4-HANDS-ON, MACRO-DELAY-HANDS-ON, WORKFLOW-HANDS-ON, PS-02..04, SW-01..03.

How: the real program (`joystick_gremlin.JoystickGremlinApp`, real QML, real Backend)
off-screen (`QT_QPA_PLATFORM=offscreen`, 1920x1080 screen file), temp USERPROFILE under
`.agent-logs/handson/H4/home/<probe>`, `GREMLIN_OFFLINE=1`, hang tool on, 170 s cap.
Fake hardware (`test/fake_hardware.py` rig: T.16000M, TWCS Throttle, vJoy 1). vJoy: the
vJoy DLL is replaced by a recording stand-in (`FakeVJoyDll` in `h4boot.py`), so the real
vJoy device was never acquired or written. Driven in-process only: QTest mouse/key events
on the program's own windows, QML expressions, Backend slots. No OS-level input, no real
screen, nothing of the user's data. Harness: `.agent-logs/handson/H4/h4boot.py`,
`run.sh`; each probe's full output is `.agent-logs/handson/H4/<probe>.out.txt`
(lines `CHECK PASS|FAIL <row> <detail>`). Every screenshot named below was looked at.

| Row | What was checked | How | Result | Evidence |
|---|---|---|---|---|
| S3 | File menu shows New Profile Ctrl+N, Load Profile… Ctrl+O, Recent, Save Profile Ctrl+S, Save Profile As… Ctrl+Shift+S; Ctrl+N makes a new profile; Ctrl+O opens "Open Profile"; Ctrl+S on a saved profile saves (note + footer); Ctrl+Shift+S opens "Save Profile As" | off-screen, QTest key clicks on the main window | PASS | p_file.out.txt; s3_file_menu.png |
| S4 | New / Load Profile… (through the file dialog's own Open button) / Recent / closing the window: nothing changed → no question; with an edit → "Unsaved Changes" Save/Discard/Cancel; Cancel keeps profile and edit (`*` stays); Discard goes on and the file is byte-identical | off-screen, QTest clicks on the dialog buttons | PASS | p_file.out.txt; s4_ask_new.png, s4_ask_recent.png, s4_ask_close.png, s4_open_dialog_window.png |
| S7 | Loaded: title "alpha.xml - Gremlin-Platforms R1"; edit → "* alpha.xml …" within 2.1 s; Ctrl+S → `*` gone | off-screen (window title read) | PASS | p_file.out.txt "S7 …" |
| S10 | New profile, add an action, Ctrl+S → Save Profile As dialog opens, folder = profiles folder | off-screen | PASS | p_file.out.txt; s10_save_goes_to_saveas.png |
| S16 | Ctrl+S → "Saved / Saved to the profile." note; footer "Saved the profile to …\profiles\alpha.xml"; the footer's hover tip carries the same full path | off-screen | PASS | s16_saved_note.png; p_file.out.txt |
| S20 | Open Profile and Save Profile As dialogs: currentFolder = `<data folder>\profiles`, filter "Profile files (*.xml)" | off-screen (Qt Quick dialog; the native Windows look is a person check, below) | PASS | p_file.out.txt "S20 …"; s4_open_dialog_window.png |
| S32 | Stick with an input module, Configuration open, action pane open on X Axis (paneHid 0); load another profile → pane closed (paneHid -1) | off-screen | PASS | p_misc.out.txt; s70_axis_pane.png, s32_after_load.png |
| S45 | Manage Modes trash on "Alpha" (2 bindings): asks 'Delete Mode "Alpha"?' / "Its 2 bindings will be deleted too. Modes under it move up one level."; Delete Mode deletes it | off-screen, QTest click | PASS | s45_delete_mode_asks.png; p_modes.out.txt |
| S49 | Running: Manage Modes shows the running note; rename Alpha → "Alpha Renamed" while running: still running, running mode and toolbar follow the new name. Note: the note text is the generic "Changes here take effect the next time it starts." although a rename applies at once (see Observations) | off-screen | PASS | s49_manage_modes_running.png; p_modes.out.txt |
| S52 | Named Startup Mode "Alpha", save, load another, reload → toolbar Alpha; Last Active: run in Bravo, stop, reload → Bravo; a toolbar pick while stopped does not count (Q2); Use Heuristic with modes apple / Default / Zulu → "apple" (capitals ignored, D-04-ALPHA-CASEFOLD) | off-screen, Startup Mode set through the Profile Settings combo's model | PASS | helpbug_named_startup.png; p_modes.out.txt |
| S64 | "Use the Options default" ticked: box greyed, shows the Options value; untick (real click) keeps 0.2 as the profile's own, box enabled | off-screen | PASS | macro_default_greyed.png, macro_follows_options_0_2.png; p_settings.out.txt |
| S70 | Axis binding with a Description action, pane open, click Treat as "Button": asks "Treat as Button?" / "Changing how this input is treated removes its action."; Cancel keeps the binding as Axis with its action | off-screen, QTest click on the real RadioButton | PASS | s70_treat_as_asks.png; p_misc.out.txt |
| S80 | Swap Bindings asks first; text says nothing is saved yet and undo = load again without saving; Cancel changes nothing; no Undo command anywhere after the swap. **But the question's buttons (Cancel, Swap bindings) are drawn below the bottom of the Swap Devices window and cannot be seen or clicked** | off-screen, geometry measured | FAIL | s80_swap_asks.png; p_swap.out.txt "s80-geometry": window 800x146, buttons at y 161-193 |
| S82 | Card right-click › Device › Swap Device… (real right-click and menu clicks) on TWCS Throttle: "To connected device" = TWCS Throttle : its id | off-screen, fake sticks | PASS | s82_card_menu.png, s82_card_menu_device.png, s82_swap_from_card.png |
| S85 | Scripts page trash asks "Remove Script?" ("…The script file itself is not deleted."); Cancel keeps it; Remove removes it | off-screen | PASS | s85_remove_asks.png; p_scripts.out.txt |
| Q1 | Load / New lands in the new profile's Startup Mode (same run as HELP-BUG; the real Backend signal order) | off-screen | PASS | p_modes.out.txt |
| Q6 / B4 Undo Delete Mode | Delete "Alpha" (2 bindings), Undo Delete Mode → mode and both bindings back; button disabled again afterwards | off-screen | PASS | q6_after_undo_delete.png; p_modes.out.txt |
| Q7 / GL-105 | Profile with action type "made-up-action": opens; notice "Unknown Action … made-up-action. They are kept as they are and saved with the profile, but do nothing."; Save As and reopen: the action is still in the file | off-screen | PASS | q7_warning_window.png; p_misc.out.txt |
| Q12 / B4 vJoy Behavior | Running (Device change behavior = Reload), flip vJoy 1 to Input: notice "This change takes effect at the next Run."; CodeRunner start/stop not called, still running | off-screen | PASS | q12_note_window.png, q12_vjoy_behavior_while_running.png |
| Q13 / C2 script time limit | Add a script whose top level loops: after 5.0 s the Scripts page shows "Can't load: Its top-level code did not finish within 5 s …"; same when loading a profile that has it; the program carries on afterwards. Note: the main thread is blocked for the 5 s (see Observations) | off-screen | PASS | q13_add_looping_script.png, q13_load_looping_script.png; p_scripts.out.txt |
| Q19 | Synthetic profile, 790 bindings / 1,580 actions (1.15 MB; not the user's 1,172-action profile): `has_unsaved_changes` 76-115 ms (avg 96 ms) on the main thread, every 1.5 s while the window is active; worst main-thread gaps over 20 s: 124, 122, 120 ms | off-screen, timer probe | FAIL | p_q19.out.txt |
| HELP-BUG-HANDS-ON (GL-053) | Named Startup Mode → toolbar shows it after reload and Run runs in it; Last Active → toolbar shows the mode last run in; change toolbar mode → Run runs in the toolbar mode | off-screen, Run with vJoy DLL stand-in | PASS | p_modes.out.txt; helpbug_named_startup.png |
| B4 auto-load | Auto-load on, game.exe → game.xml: the game's profile loads and runs; then Gremlin's own program comes to the front: the Run keeps going (process monitor not started; its signal emitted with made-up paths) | off-screen | PASS | b4_autoload_running.png; p_autoload.out.txt |
| SAFE-4-HANDS-ON (04 parts) | S45 count (above), S70 Treat as (above); auto-load with unsaved edits: not switched, "Auto-load Waited" shown once, not again on the next focus | off-screen | PASS | safe4_autoload_waited.png; p_autoload.out.txt |
| SAFE-4-HANDS-ON (Logical Device row by mouse) | Change mode, scale and Invert on a Logical Device row with the mouse | not run | BLOCKED | Logical Device page subsystem, not attempted in this pass |
| SAFE-4-HANDS-ON (Update download) | Start a download, close with X, part file gone | not run | BLOCKED | needs the network; contract: offline only |
| MACRO-DELAY-HANDS-ON / PS-02 | Box greyed + ticked; Options default 0.2 (set, Options window closed) → greyed box shows 0.2; Run: MacroManager default delay 0.2; untick, 0.5, Ctrl+S, reopen → 0.5, unticked (file has `<macro-default-delay>0.5`) | off-screen | PASS | macro_own_0_5_reopened.png; p_settings.out.txt |
| WORKFLOW-HANDS-ON (S4, S7, S82, rename, card menus) | S4/S7/S82 as above; rename a mode: the name opens selected; card menu Device Information / Auto Mapper / Module Setup open on that card's device | off-screen | PASS | workflow_rename_selected.png, workflow_card_*.png; p_workflow.out.txt |
| WORKFLOW-HANDS-ON (other pages' items) | "Off: never runs", empty Chain/Tempo warning icon, Calibration Save all, Options at 200 % | not run | BLOCKED | pages 05 / 03 / 01 items, not attempted by H4 |
| PS-03 (S66) | vJoy 1 switched to Input: it leaves vJoy Initial Values and is listed with the physical devices (`input_devices()`); switched back: offered again | off-screen, fake vJoy | PASS | ps03_vjoy_as_input.png; p_settings.out.txt |
| PS-04 (S67) | Initial Value X = 0.5, Run: `output.write_vjoy_axis_linear(1, 1, 0.5)`, DLL stand-in got SetAxis(24576, vJoy 1, X). The claim gate was opened for vJoy 1 in the probe (no output module in the temp data) | off-screen, vJoy DLL stand-in | PASS | ps04_initial_values.png; p_settings.out.txt "s67-writes" |
| SW-01..03 (S77, S81) | Combos: "T.16000M - 2 actions", "TWCS Throttle - 1 action"; connected list T.16000M, TWCS Throttle, vJoy Device 1; Swap Bindings moves both ways (3 inputs), list counts refresh, profile `*` and file unchanged until saved (S83); reload undoes it | off-screen, fake sticks | PASS | s80_after_swap.png; p_swap.out.txt |
| PS-03/04 with real vJoy | Initial values seen on the real vJoy device | — | PERSON | see below |
| SW-01..03 with two real sticks | — | — | PERSON | see below |
| MACRO-DELAY: older build | Open the 0.5-delay profile in an older Gremlin build | — | PERSON | see below |
| Q19 feel | The 1,172-action profile, window in front a minute, moving an axis: stutter? | — | PERSON | see below |
| S10/S20 native dialog | The real Windows file dialogs | — | PERSON | see below |

Counts (table rows): PASS 27, FAIL 2, BLOCKED 3, PERSON 5. Rows that share a check
are merged (Q6 = B4 Undo Delete Mode, Q7 = GL-105, Q12 = B4 vJoy Behavior, Q13 = C2,
S64 = MACRO-DELAY = PS-02).

## Failures

**S80 (04 S80, C11; also SW-01..03): the Swap Bindings question can't be answered.**
Tools › Swap Devices (or a card's Swap Device…), click Swap Bindings: the question opens
inside the Swap Devices window, which is only as tall as its own controls (800x146 at
100 % scale). The question's title and text show, but its Cancel and Swap bindings
buttons sit at y 161-193, below the window's bottom edge: not visible, not clickable (the
window also swallows Esc and Return with empty Shortcuts, `DialogSwapDevices.qml:29-31`).
The user can only finish by dragging the window taller. Likely cause:
`qml/DialogSwapDevices.qml:20-22` (`height` / `minimumHeight` = content + 30) with the
`DismissibleDialog` (`:160-163`) parented to that window's overlay
(`qml/DismissibleDialog.qml:124`). Suggested fix: make the window at least as tall as the
open question (grow it while `_swapGate` is open, or give it a minimum height that fits the
dialog), and add a test that the gate's buttons lie inside the window. Seen off-screen by
geometry; a person can confirm on the real screen in 10 s.

**Q19 (04 Q19, decided "measure; mark dirty on edit instead if it is slow"; GL-153).**
Measured on a synthetic profile of 1,580 actions (790 bindings, 1.15 MB): each unsaved
check (`Profile.has_unsaved_changes`, `gremlin/profile.py:1788`, rebuilding the whole XML)
takes 76-115 ms on the main thread, and runs every 1.5 s while the window is in front
(`qml/Main.qml:36-41`). Result: a ~120 ms main-thread stall every 1.5 s (worst gaps 124,
122, 120 ms in 20 s). By any UI frame budget that is slow, so by the decision the check
should become "mark dirty on edit". Recorded as FAIL so the lead can decide; the
threshold (100 ms / 150 ms) is H4's, not the spec's. The user's own 1,172-action profile
was not used (contract), and this PC may be faster or slower than the user's.

## Blocked

- SAFE-4-HANDS-ON, "Logical Device row: change mode, scale and Invert with the mouse":
  not attempted by H4 (Logical Device page; needs its own probe on that page).
- SAFE-4-HANDS-ON, "Update: start a download, close with X, the part file is gone":
  needs the network; the contract runs every probe offline.
- WORKFLOW-HANDS-ON items that belong to other pages ("Off: never runs", empty
  Chain/Tempo warning icon, Calibration Save all, Options at 200 % UI scale): not run by
  H4; see the 05 / 03 / 01 results.

## Needs a person

1. PS-03/PS-04 with real vJoy: Profile Settings › vJoy Initial Values, set vJoy 1 X Axis
   to 0.5, Run, look in the vJoy Viewer (or vJoy Monitor): X sits at 75 %. Flip vJoy 1 to
   Input: it appears with the sticks (Home / Configuration) and leaves Initial Values.
2. SW-01..03 with two real sticks: Tools › Device Setup › Swap Devices, From = stick A,
   To = stick B, Swap Bindings (drag the window taller first, see the S80 failure): the
   bindings move both ways; press a button on stick B: it does what stick A's did.
3. MACRO-DELAY: open the profile saved with an own delay of 0.5 in an older Gremlin build:
   it opens.
4. Q19: open your 1,172-action profile, keep the main window in front for a minute while
   moving an axis: any stutter in the window or the vJoy Viewer?
5. S10/S20: File › Load Profile… and Save Profile As… on the real screen: the Windows
   dialogs open in `<data folder>\profiles` with "Profile files (*.xml)", titled
   "Open Profile" / "Save Profile As" (glossary gap 20 asks which case wins).

## Observations (not failures)

- S49: Manage Modes' running note says "The profile is running. Changes here take effect
  the next time it starts." but a rename applies to the running profile at once (S44,
  S49). The note may mislead; `qml/DialogManageModes.qml:73` uses the default
  `RunningNote` text.
- Q13 / C2: the 5 s limit holds, but the main thread waits the whole 5 s (event loop not
  running: max gap 5.01 s on add and on load), so the window freezes 5 s per looping
  script (`gremlin/user_script.py:530`). The decision's reason says "rules out the program
  freezing"; the lead may want the wait off the main thread.
- The final test plan's note "F04::test_s52_use_heuristic_is_alphabetical_whatever_the_capitals
  (xfail FINAL-04-2)" is out of date: the test passes plainly and the hands-on check agrees.
- Probe exits sometimes report code 139 inside `os._exit` after all checks ran (Qt
  threads at teardown); no effect on results.
