# Gremlin-Platforms full functional test plan (draft)

Built from a code inventory of every screen, menu, toolbar button and right-click menu
(branch `Gremlin-Platforms`, 2026-09-30). Tick `[x]` when a test passes; write `FAIL:` and a note
when it does not.

## How tests are run

- **[A] Auto**: Claude runs it on the sandbox copy by driving the screen.
- **[U] Needs you**: needs a physical stick, keyboard press, a game, or changes the real
  HidHide/vJoy/ViGEm driver state.
- **[B] Build**: needs the release zip / exe.
- **[D]** marks a destructive test (deletes or overwrites). Sandbox data only.

Rules for every batch:

1. Sandbox only: its own USERPROFILE with a copy of the user data. Never the real profile or
   `configuration.json`.
2. After each batch: check stderr for QML/Python errors, close the app, and check for leftover
   Python processes and hung windows.
3. A failure is logged with steps and a screenshot. It is reported with problem, impact, the R16
   comparison and a proposed fix. It is not fixed until the user says "go".

Batch order: 1 Main window, 2 Home, 3 Configuration, 4 Output view, 5 Logical Device, 6 Scripts and
Profile Settings, 7 Options, 8 Button Map, 9 Viewers, 10 Calibration and Configure Module,
11 Device Pack / Modes / Swap / Auto Mapper / Hidden / Info / Help / About, 12 Action editors,
13 HiDHide, 14 Hands-on [U], 15 Build [B].

---

## 1. Main window: menus, toolbar, status bar, window

### File
- [ ] F-01 [A][D] File > New Profile (Ctrl+N): confirm dialog; Cancel changes nothing; confirm gives a blank profile and an empty title.
- [ ] F-02 [A] File > Load Profile (Ctrl+O): dialog opens in the profiles folder; loading sets the title and last-profile.
- [ ] F-02b [A] Load Profile with unsaved changes: is there a prompt? (suspected none, see S-05)
- [ ] F-03 [A] File > Recent: lists recently loaded profiles; clicking one loads it; a missing file shows an error. (suspected always empty, see S-04)
- [ ] F-04 [A][D] File > Save Profile (Ctrl+S): "Saved" popup, footer saved-line, file written.
- [ ] F-04b [A] Save on a never-saved profile opens Save As.
- [ ] F-05 [A][D] File > Save Profile As: writes a new .xml; title updates.
- [ ] F-06 [A] File > Exit with no changes: app quits cleanly.
- [ ] F-06a [A] Exit with unsaved changes > Save / Discard / Cancel each behave as labelled.

### View
- [ ] V-01 [A] View > Home returns to Home from every room.
- [ ] V-02 [A] View > Configuration opens the last-clicked card's configuration.
- [ ] V-03 [A] View > Control Display toggles the pin overlay on the focused card.
- [ ] V-04..06 [A] View > Home layout > Single list / Side by side / Stacked; each persists across restart.
- [ ] V-07 [A] View > Hidden devices opens the dialog.
- [ ] V-08 [A] View > Scripts opens the Scripts room.
- [ ] V-09 [A] View > Profile Settings opens the settings room.

### Tools, Debug, Help (open and close each window once)
- [ ] T-01..03 [A] Viewers: vJoy / Xbox / Device open; choosing again closes them.
- [ ] T-04..10 [A] Device setup: Calibration, HiDHide, Configure input module, Configure output module, Device Information, Swap Devices, Device Pack.
- [ ] T-06b [A] Configure input module with an output card last clicked (suspected wrong direction, see S-12).
- [ ] T-11..14 [A] Mapping: Logical Device, Button Map, Auto Mapper, Manage Modes.
- [ ] T-15 [A] Tools > Options.
- [ ] D-01 [A] Debug > Live Log Reader opens and shows log lines.
- [ ] H-01 [A] Help > User Guide opens.
- [ ] H-02 [A] Help > About shows Gremlin-Platforms, R1, "Based on Joystick Gremlin R15"; the link opens the browser.

### Toolbar
- [ ] TB-01 [A] Home button (and its accent colour while on Home).
- [ ] TB-02 [U] Toggle starts and stops the runner; footer shows Active / Not Running; tray icon changes.
- [ ] TB-03..07 [A] vJoy Viewer, Xbox Viewer, Button Map, Logical Device, Device buttons.
- [ ] TB-08 [A] Gear opens Options.
- [ ] TB-09 [A] Configuring mode combo: switching mode changes the edited map; footer "Executing mode" follows.
- [ ] TB-10 [A] Manage Modes button.
- [ ] TB-11 [A] The window cannot be made narrower than the toolbar.

### Status bar, window, tray, keyboard
- [ ] SB-01..03 [A] Status text, Executing mode, saved-line with its tooltip.
- [ ] W-01 [A] Window reopens where it was left (tested today; recheck in the full pass).
- [ ] W-02 [A] Title shows the profile path. New unsaved profile: is the title blank? (see S-06)
- [ ] W-03 [A] Close (X) with each unsaved state: profile, catalog display, output display, Button Map. Each prompts once, and after Save / Discard the app finishes closing. (see S-07)
- [ ] W-04..05 [A] Close to tray / Minimize to tray options hide the window.
- [ ] W-06..09 [A] Tray: left-click restores; menu Hide/Show, Activate/Deactivate, Quit.
- [ ] W-21 [A] Close to tray, then quit from the tray: is the window position saved? (see S-21)
- [ ] W-11 [A] Options > Disable Windows scaling > Restart restarts the app.
- [ ] W-12 [A] Error and notification dialogs are readable (theme).
- [ ] KB-01 [A] Ctrl+N / Ctrl+O / Ctrl+S.
- [ ] KB-03 [A] Esc on Home clears card selection.

---

## 2. Home (status cards)

- [ ] H-01..03 [A] Card click focuses it; Shift+click multi-selects; double-click opens Configuration (input) or Output View (output).
- [ ] H-04 [A] Drag a card to reorder; persists across restart.
- [ ] H-05 [A] Resize a card by edge and corner; clamps; persists.
- [ ] H-06 [A] Card x hides the device; View > Hidden devices can unhide it.
- [ ] H-07 [A] Output card "Output View" button.
- [ ] H-08 [A] Photo hover shows the Control Display overlay.
- [ ] H-09 [U] "last:" line updates on a physical press.
- [ ] H-20 [A] Compact view on/off; persists.
- [ ] H-21..22 [A] Split combo and divider drag; persists.
- [ ] H-23..25 [A] Empty-area click clears selection; right-click > Unhide all devices; empty-state message.
- [ ] H-10..19 [A] Card right-click, every item:
  - Open Configuration / Output View
  - Button Map
  - Configure module
  - Pin / Unpin Control Display
  - Auto Mapper
  - Device Viewer
  - vJoy / Xbox Viewer
  - Calibration
  - Device Information
  - Assign hardware
  - Stack selected cards
  - Unstack
  - Unstack all
  - Reset size
  - Hide device
  - Clear module settings
- [ ] H-11b [A] Card menu viewer items when that viewer is already open (suspected closes it, see S-11).
- [ ] H-13b [A] Pin from the card menu updates the overlay at once (see S-09).
- [ ] H-19g [A][D] Delete Device, all three steps, with and without "Save a copy"; the device's windows close.

---

## 3. Configuration (Input Configuration / bindings catalog)

- [ ] C-01..03 [A] Header title, the previous / next arrows (wrap, leave gate) and the "Bound to" line.
- [ ] C-05 [A] "Move empty to Unmapped" moves empty controls; Save View Settings keeps it.
- [ ] C-06 [A] Hide / Show Editor button. With unsaved display edits, compare with the X button (see S-16).
- [ ] C-07..10 [A] Legacy device tab bar (View > Configuration with no card focused): each tab and the ‹ › arrows.
- [ ] C-07b [A] Legacy "Logical Device" tab: is the header correct? (see S-20)
- [ ] IC-01..02 [A] Type filter (every entry) and Destination filter.
- [ ] IC-03..05 [A] Parent row click, child row click, Add Action open the pane.
- [ ] IC-06 [A][D] Child Delete removes the action (no confirm, see S-14).
- [ ] IC-07 [U] Live LEDs, bars and row tint on a physical press.
- [ ] IC-08 [A] Empty-catalog message for a module with no claimed controls.
- [ ] IC-09..13 [A] Pane: X with and without changes, OK, "Close pane after OK" (persists), width grip (persists).
- [ ] IC-13b [A] While Gremlin is running, does a row click still open the pane? (see S-13)
- [ ] IC-14..25 [A] Display Editor: X gate, Open all / Close all, and every section (Screen, Shown, List, Unmapped Row, Group, Parent row, Child row, Text, Selection, Editor). Change one value per section and check the list updates.
- [ ] IC-26..28 [A] Reset View to Default, Copy View from… (every other module), Save View Settings (then restart and check).
- [ ] IC-29 [A] Leaving with unsaved display edits prompts: Home, other module, arrows, Scripts.

---

## 4. Output Module View

- [ ] OV-01 [U] Live pads, hats, meters and buttons move with vJoy output.
- [ ] OV-02..03 [A] Display Editor X gate; Open all / Close all.
- [ ] OV-04..09 [A] Sections: Screen, Layout, Pads, Meters, Buttons, Colors. One change each shows on the view.
- [ ] OV-10..12 [A] Reset View, Copy View from… (with no other output module: empty menu? see S-17), Save View Settings, restart.

---

## 5. Logical Device page

- [ ] LP-01..06 [A] Find text, Type, the three checkboxes, Clear, Hide / Show Editor, "Running" label.
- [ ] LP-10..13 [A] Group and parent carets, parent select and Shift-select, group collapse, action row opens the pane.
- [ ] LP-14..15 [A] Drag a parent within and across groups; drag a group; undo.
- [ ] LP-16..18 [A] Writer row: axis mode, scale, Invert. Needs a map-to-logical axis in the sandbox profile.
- [ ] LP-19 [A] Name hover tooltip.
- [ ] LP-20..22 [A] Add Button / Axis / Hat with a count (1, 5, 180 cap).
- [ ] LP-23 [A] Add Action, then OK and Cancel.
- [ ] LP-24 [A] Assign hardware popup: search, device tri-state, per-control boxes.
- [ ] LP-25..26 [A] Rename ("Hide system name") and Clear name.
- [ ] LP-27..28 [A] Group as (including the "Already in a group" prompt) and Move to group (hover opens it).
- [ ] LP-29 [A][D] Delete parent. With 3 selected, does it delete only the clicked row? (see S-15)
- [ ] LP-30 [A] New group.
- [ ] LP-31..33 [A] The three sort items (natural order, tested today).
- [ ] LP-34 [A] Display opens the editor, including while running.
- [ ] LP-35..37 [A][D] Group menu: Move group up / down, Rename group (look-alike refused), Delete group.
- [ ] LP-38 [A][D] Action row Delete.
- [ ] LP-40..41 [A] Undo / Redo from the menu and with Ctrl+Z / Ctrl+Y.
- [ ] LP-41b [U] Ctrl+Shift+Z redo, pressed by hand.
- [ ] LP-50..52 [A] Pane X gate, OK, "Close pane after OK", width grip.
- [ ] LP-53..56 [A] Display Editor: X gate, every section, the two indents (tested today), Reset, Save View Settings, restart.
- [ ] LP-57 [A] Leave the page with a dirty pane or display editor: is there a prompt? (see S-08)

---

## 6. Scripts and Profile Settings

- [ ] S-02 [A] Add Script (file dialog, .py).
- [ ] S-03..04 [A] Rename (pencil); configure (gear) shows variables; edit a variable.
- [ ] S-05 [A][D] Trash removes the script (no confirm).
- [ ] S-06 [A] Tooltips.
- [ ] PS-01..02 [A] Startup Mode (every entry) and Macro Default Delay; save the profile and reload.
- [ ] PS-03..04 [U] vJoy Input/Output switch and initial axis values (activate and check vJoy).
- [ ] PS-06 [A] Text reads correctly: "as an input", "device the vJoy" (see S-19).

---

## 7. Options

- [ ] OPT-01 [A] Every section opens; groups are listed in order.
- [ ] OPT-G01..G09 [A] Global > General: change each, close, reopen, check it stuck.
- [ ] OPT-G02 [A] Check for updates: at startup a notice appears only when a newer GitHub release exists.
- [ ] OPT-G04 [A] Debug level buttons change what is logged.
- [ ] OPT-F01..F08 [A] Files: Select and Reset on every folder row. Plugin dir and logs need a restart.
- [ ] OPT-U01 [A] Dark mode on/off.
- [ ] OPT-U02 [A] Windows scaling checkbox: Restart / Later / Cancel.
- [ ] OPT-U03..05 [A] Highlight source, Input highlighting and speed, Display mode.
- [ ] OPT-U06 [A] UI scale slider: disabled with Windows scaling on; live on release when off.
- [ ] OPT-A01 [A] Action list: reorder and hide; check the Add Action menu order.
- [ ] OPT-A02..A11 [A] Every action default, then create a new action and check the default applies.
- [ ] OPT-P01..P09 [A] Profile auto-loading: New entry, Select Profile, Browse / Select Executable, pencil, On/Off, remove.
- [ ] OPT-P10 [U] Auto-load switches the profile when the chosen exe gets focus. With 2+ entries, is the second ever matched? (see S-18b)
- [ ] OPT-O01..O06 [A] OSC settings save; rescan button.
- [ ] OPT-D01..D04, C01..C02, M01..M02 [A] Display, Control Display and Auto Mapper options.
- [ ] OPT-X1 [A] Selection combos really save (Display mode, Device change behaviour, Playback mode, Resolution mode, Action sequence information). See S-27.
- [ ] OPT-X2 [A] Is "action-priorities" shown or missing? (see S-26)

---

## 8. Button Map

- [ ] BM-F01 [A] File > device list switches device; asks to save if dirty.
- [ ] BM-F02..04 [A] Edit Mapping, Save (read-back message), Cancel (asks if dirty).
- [ ] BM-F05..06 [A] Reset layout (Keep map / Reset, undoable) and Fit to photo frame.
- [ ] BM-F07..08 [A][D] Choose background and Clear image. Clear then Cancel: is the image gone? (see S-24)
- [ ] BM-F09..11 [A] Export PDF / PNG / JPG (tested today; recheck).
- [ ] BM-F12 [A] Close with and without unsaved changes.
- [ ] BM-E01..05 [A] Undo, Redo (Ctrl+Z / Ctrl+Y), Duplicate, Copy, Paste.
- [ ] BM-V01..05 [A] Reset view, Show grid, Snap to grid, Snap to entities, every grid size. Do these write the module file outside edit mode? (see S-25)
- [ ] BM-P01..03 [A] Move photo, Adjust photo popup (every slider and button), Reset photo.
- [ ] BM-H01 [A] Editor help (F1). Its text says "File > Import overlay" and first-level leader items (see S-23).
- [ ] BM-K01..06 [A] Delete / Backspace, Ctrl+G / Ctrl+Shift+G, Ctrl+0, arrows / Shift+arrows, Esc, Alt-drag, Shift-draw.
- [ ] BM-Z01 [A] Wheel zoom, middle-drag pan.
- [ ] BM-Z02 [U] Pressing a physical control lights its chip.
- [ ] BM-Z03 [A] Double-click rename and text edit.
- [ ] BM-R01..05 [A] Reservoir: filter, clear, drag a chip on, resize and undock.
- [ ] BM-C01 [A] Colour picker applies live.
- [ ] CTX [A] Chip right-click, every item: top level, Chip, Hotspot, Leader End, Group, Format (all four 5-way styles, Clear Format), Align, Leader (every item), Draw (every item including Import overlay).
- [ ] TBL [A] Table right-click, every item (TBL-01..16).
- [ ] TXT [A] Text box right-click, every item (TXT-01..18).
- [ ] BM-S1 [A] After all edits: Save, close, reopen, and check the layout came back as saved.
- [ ] BM-X1 [A] Map pack Export / Import: is there a menu item? (suspected unreachable, see S-22)

---

## 9. Viewers

- [ ] DV-01..04 [A] Device Viewer: opens, pauses highlighting, fold rows, name tooltip. Esc does not close it (see S-30).
- [ ] DV-05..07 [U] Temporal, Current, and Buttons & Hats switches with a moving stick.
- [ ] VJV-01..02 [A] vJoy Viewer: cards, chips (dash rule), "Active" badge.
- [ ] VJV-03 [U] Temporal plot while moving an axis.
- [ ] XV-01..02 [A] Xbox Viewer lists Map to Xbox cards; "Activate Gremlin…" message.
- [ ] XV-03 [U] With Gremlin active the pad responds, including a hat mapped to a button (fix a) and Upper half triggers (fix e).

---

## 10. Calibration and Configure Module

- [ ] CAL-01..02 [A] Opens from Tools and from a card (preselected); module combo with the unsaved prompt.
- [ ] CAL-03..06 [A] With-center, the four spin boxes, Reset, Save ("Saved to the module file").
- [ ] CAL-07..08 [U] Calibrate center / extrema with the stick. Switch from one to the other: does the first stop? (see S-28)
- [ ] CAL-09 [A] Close with unsaved changes.
- [ ] CAL-10 [U] Raw and calibrated bars. Typing in "Raw": does it do anything? (see S-29)
- [ ] CFGM-01..03 [A] Import image, claim checkboxes, friendly names.
- [ ] CFGM-02b [U] Pressing a physical control scrolls to its row.
- [ ] CFGM-04a..f [A][D] Module file dialog: Import from, Browse (prompt when dirty? see S-31), Open folder, Delete file (no confirm), Undo import, OK.
- [ ] CFGM-05..06 [A] Cancel gate; Save module (does the window close? output direction saves the profile).

---

## 11. Other dialogs

- [ ] DP-01..03 [A] Device Pack Export: device combo, peek, Export writes a zip.
- [ ] DP-04..13 [A][D] Import: choose zip, target, name, sections, row boxes, "Picture not included" prompt, Import.
- [ ] MM-01..04 [A][D] Manage Modes: add (unique name), rename, parent, delete (no confirm).
- [ ] SW-01..03 [A][D] Swap Devices: combos, Swap Bindings.
- [ ] AM-01..07 [A] Auto Mapper: checklists, mode, switches, Create mappings.
- [ ] AM-05b [A] Click Create mappings a second time without changing boxes (suspected maps nothing, see S-32).
- [ ] HD-01..02 [A] Hidden devices: Unhide, Unhide all.
- [ ] DI-01 [A] Device Information table.
- [ ] HLP-01..02 [A] User Guide: every topic opens. Missing topics: Hat as Buttons, Chain, Tempo, Condition, Double Tap, Smart Toggle (see S-33).
- [ ] ABT-01 [A] About.
- [ ] MF-01 [A] Startup failure window (simulate a startup error in the sandbox).

---

## 12. Action editors (create each on a sandbox input, set every control, save the profile, reload, check the values came back)

- [ ] AE-01 [A] Map to vJoy: device, type, id, Absolute/Relative, Scaling, Invert.
- [ ] AE-02 [A] Map to Keyboard: Record Keys.
- [ ] AE-03 [A] Map to Mouse: Button / Motion, speeds, direction.
- [ ] AE-04 [A] Map to Xbox: pad, target, trigger range, Invert (tested today).
- [ ] AE-05 [A] Map to Logical Device: selector, mode, scaling, invert.
- [ ] AE-06 [A] Macro: repeat modes, delay, count, Exclusive / Pre-emptive, add each step type, remove, reorder.
- [ ] AE-06b [U] Macro Start / Stop Recording.
- [ ] AE-07 [A] Change Mode: each type (Switch, Previous, Unwind, Cycle rows, Temporary).
- [ ] AE-08 [A] Load Profile: field and Select File.
- [ ] AE-09 [A] Text to Speech: text, queue mode, volume, rate, pitch.
- [ ] AE-09b [A] Text to Speech is offered on a keyboard key? (suspected not, see S-34)
- [ ] AE-10 [A] Run Command: executable, arguments.
- [ ] AE-11 [A] Play Sound: file, volume.
- [ ] AE-12 [A] Response Curve: each curve type, Invert, Symmetric, add / drag / delete a point, X/Y boxes, deadzone sliders.
- [ ] AE-13 [A] Merge Axis: instance, new, rename, operation, first / second axis, container.
- [ ] AE-14 [A] Split Axis: split value, both containers.
- [ ] AE-15 [A] Axis Delta: threshold, both containers.
- [ ] AE-16 [A] Dual Axis Deadzone: instance, new, rename, inner / outer, axes, containers.
- [ ] AE-17 [A] Hat as Buttons: 4 / 8 way, direction containers.
- [ ] AE-18 [A] Pause and Resume: the three operations.
- [ ] AE-19 [A] Chain: timeout, add and remove sequences.
- [ ] AE-20 [A] Tempo: threshold, press / release, both containers.
- [ ] AE-21 [A] Condition: All / Any, every condition type, comparators, remove, TRUE / FALSE containers.
- [ ] AE-22 [A] Double Tap: threshold, exclusive / combined, containers.
- [ ] AE-23 [A] Smart Toggle: delay, container.
- [ ] AE-24 [A] Description: text.
- [ ] AE-25 [A] Reference: link and duplicate.
- [ ] AE-R [U] With Gremlin active, each action type does its job for real (vJoy, keyboard, mouse, Xbox, macro, mode change, sound, speech, command).

---

## 13. HiDHide (changes the real driver: each step confirmed with you first)

- [ ] HH-00..03 [A] Open / close (size and splitter kept), driver status row, Get HiDHide link, Test HiDHide opens Game Controllers.
- [ ] HH-07..08 [A] Gaming devices only; Add / Change image.
- [ ] HH-04..06 [U] Gremlin control, HiDHide Enabled, Automatically Start (restart to verify).
- [ ] HH-05b [U] Driver refuses HiDHide Enabled: does the switch flip back? (see S-35)
- [ ] HH-09 [U] Hide / unhide a device; check Game Controllers (Allow list).
- [ ] HH-10..12 [U] Add Program, Remove, Allow / Block list.

---

## 14. Hands-on checklist for you [U]

Physical input and real output. One sitting, about 30 minutes:

1. Toggle runner on and off (TB-02). Footer and tray follow.
2. Home "last:" updates on a press (H-09).
3. Catalog live LEDs, bars and tint (IC-07).
4. Output View live (OV-01).
5. Button Map chip lights on a press (BM-Z02).
6. Device Viewer switches (DV-05..07).
7. vJoy Viewer temporal plot (VJV-03).
8. Xbox Viewer with a hat mapped to an Xbox button, and Upper half triggers (XV-03).
9. Calibration center and extrema (CAL-07..10).
10. Configure Module press-to-scroll (CFGM-02b).
11. Macro recording (AE-06b).
12. Every action type for real (AE-R).
13. Logical Device Ctrl+Shift+Z (LP-41b).
14. Profile auto-load by exe focus (OPT-P10).
15. vJoy initial values and Input/Output switch (PS-03..04).
16. HiDHide section 13.

---

## 15. Build [B]

- [ ] B-01 The zip unpacks and `gremlin_platforms.exe` starts (sandbox USERPROFILE).
- [ ] B-02 `ViGEmClient.dll` is in the build; Xbox Viewer shows the pad; Map to Xbox is in the action list.
- [ ] B-03 Every action plugin appears in the exe's Add Action list.
- [ ] B-04 Help, About and theme work in the exe (resources bundled).

---

## Suspected issues to confirm (from reading the code, not yet seen in the app)

Main window:
- S-01 VJoyStatusPopup is never opened (dead code). Main.qml:587
- S-02 Old LogicalDevice.qml tab list can never show. Main.qml:1626
- S-03 Catalog inline sequence editor is never used (dead code). BindingCatalog.qml:728
- S-04 File > Recent is never written, so it is always empty. backend.py:436
- S-05 No unsaved-changes prompt before Load / Recent; a failed load still sets last-profile. Main.qml:631, backend.py:495
- S-06 New unsaved profile gives a blank window title. backend.py:514
- S-07 Close with unsaved catalog or output display: after Save / Discard the app does not finish closing. Main.qml:1180
- S-08 Leaving the Logical Device page drops a dirty pane or display editor without asking. LogicalPage.qml:123
- S-09 Pin changes may not update the card overlay at once. StatusPage.qml:477
- S-10 "Clear module settings" only clears card size and stack; the label suggests more. module_model.py:1021
- S-11 Card menu viewer items close an already-open viewer; Auto Mapper / Device Info / Assign hardware ignore the card. Main.qml:1249
- S-12 Tools > Configure input module can open with an output card. Main.qml:321
- S-13 Catalog pane opens while Gremlin is running. BindingCatalog.qml:1403
- S-14 Deletes without confirmation: catalog action, logical parent / group / action, script, mode, program, module file.
- S-15 Logical Delete acts on the clicked row only, while Group as / Move to group act on the whole selection.
- S-16 Hide Editor buttons skip the unsaved-display gate.
- S-17 Output "Copy View from…" can open empty.
- S-19 Profile Settings typos: "as aninput", "devicethe vJoy". ProfileSettings.qml:140
- S-20 Legacy Logical Device tab shows the Input Configuration header.
- S-21 Close to tray skips saving the window position.

Tool windows and editors:
- S-18b Profile auto-load regex stops after the first non-matching entry. config.py:~345
- S-22 Button Map map-pack Export / Import cannot be reached (help and labels mention it). DialogJoystickButtonMap.qml:1358
- S-23 Button Map help text disagrees with the menus (Import overlay, leader items). :836, :852
- S-24 Button Map Clear image deletes the file at once; Cancel cannot bring it back. hardware_profile.py:1894
- S-25 Grid / snap / view settings write the module file even outside edit mode; Ctrl+0 does not. :1263
- S-26 "action-priorities" option has no widget in Options.
- S-27 Selection combos in Options may not save. ConfigGroup.qml:263
- S-28 Calibration: switching center / extrema may leave the other mode running. DialogCalibration.qml:367
- S-29 Calibration "Raw" field is editable but does nothing. :206
- S-30 Most tool windows cannot be closed with Esc.
- S-31 Configure Module: Save closes the window; Browse imports without the unsaved prompt; Delete file has no confirm.
- S-32 Auto Mapper: second "Create mappings" maps nothing while boxes still look checked. DialogAutoMapper.qml:187
- S-33 User Guide is missing six action topics.
- S-34 Text to Speech is not offered for keyboard keys. text_to_speech/__init__.py:181
- S-35 HiDHide Enabled switch stays flipped when the driver refuses. hidhide.py:1693
- S-36 HiDHide photo file names change every run and leave orphans. hidhide.py:1771 (already on the back burner)
- S-37 Button Map _groupMenu / _leadMenu are dead code. DialogJoystickButtonMap.qml:1276
- S-38 HiDHide "Automatically Start" and Options "Hidhide on start" are the same setting (two controls).

---

# Results

Legend: PASS, FAIL, DEFERRED (needs you), NOTE (not a bug, or observation).

## Batch 1: Main window (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| F-01 | PASS | Confirm dialog; Cancel keeps profile; Create gives a blank profile. |
| F-01b | FIXED | After New Profile (and after Save As) the "Configuring mode" box is blank until opened; the list holds "Default". |
| F-02 | PASS | Load from the profiles folder; title, bindings and mode restored. |
| F-02b | FIXED (Load and Recent ask) | Ctrl+O with unsaved changes gives no warning (S-05 confirmed). |
| F-03 | FIXED | File > Recent is always empty; `recent-profiles` is never written (S-04 confirmed). |
| F-04b | PASS | Ctrl+S on a new profile opens Save As in the profiles folder; "Saved" popup; footer line. |
| F-06a | PASS | Exit with unsaved profile shows Save / Discard / Cancel; Cancel stays. |
| F-06b | PASS | Discard quits cleanly. |
| KB-01 | PASS | Ctrl+N, Ctrl+O, Ctrl+S. |
| V-01, V-02 | PASS | Home; Configuration opens the last clicked card. |
| V-03 | DEFERRED to batch 2 | Needs Compact view off. |
| V-04..06 | PASS | Single list / Side by side / Stacked. The Split box uses other names (None / Vertical / Horizontal). |
| V-07, HD-01, HD-02 | PASS | Hidden devices, Unhide, Unhide all ("No hidden devices."). |
| HD-01b | FIXED | stderr on Unhide: `DialogHiddenDevices.qml:58 ReferenceError: _win is not defined` (the row is destroyed while its click runs). |
| V-08, V-09 | PASS | Scripts room; Profile Settings room. |
| PS-06 | FIXED | Typos confirmed: "aninput", "devicethe", "a vJoy devices are" (S-19). |
| T-01..T-15 | PASS | Every Tools item opens its window (Viewers x3, Device setup x7, Mapping x4, Options). |
| D-01 | PASS | Live Log Reader shows the log (new Gremlin Platforms paths). |
| H-01, H-02 | PASS | User Guide; About text. Link not clicked (opens the browser). |
| TB-03 | PASS | vJoy Viewer toggles open and closed. |
| TB-04, TB-07 | PASS (open) | Close-toggle uses the same code as TB-03. |
| TB-05, TB-06, TB-08, TB-10 | PASS | Button Map, Logical Device (icon accent), Options, Manage Modes. |
| TB-02 | DEFERRED | Runner on/off drives real vJoy output. |
| TB-09 | DEFERRED to batch 11 | Needs a second mode (Manage Modes batch). |
| TB-11 | PASS | Width cannot go below 1346 px. |
| SB-03 | PASS | Footer saved-line. |
| W-02 | PASS | New profile title is "Gremlin-Platforms R1" (S-06 ruled out). |
| W-03 | FIXED | Close with unsaved catalog display: after Discard only the panel closes; the app stays open and never asks about the unsaved profile (S-07 confirmed). |
| W-12 | PASS | Dialogs readable in the dark theme. |
| LP-20 | PASS | Add Button from the empty-area menu. |
| NOTE | not a bug | The Add Button menu stays open after adding; an Undo line appears, and a stray click on it undid the add. |
| XB-IMG | FAIL (back burner #9) | stderr: `qml/images/xbox360_two_panel.jpg` missing (removed in "moved user data"). Xbox Viewer has no picture. |
| DP-LOOP | NOTE | stderr: `DialogDevicePack.qml:381 recursive rearrange` layout warning when Device Pack opens. |

## Batch 2: Home (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| H-20 | PASS | Compact view off shows photos; persists across restart. |
| H-07, H-08 | PASS | Output View button on output cards; hover shows the "Control Display" overlay. |
| H-13 / V-03 | RESOLVED (pin feature removed) | Pin from the card menu: the card does not show "pinned" and the menu still says "Pin" until another click refreshes the page. stderr: `Overwriting binding on StatusPage::pinSlug at Main.qml:1247` (the handler assigns the page's pinSlug and breaks its binding to Main). Pins are not saved across restart (by design). |
| H-06 | PASS | Card x hides the device. |
| H-24 | PASS | Empty-area right-click > Unhide all devices. |
| H-04 | PASS | Drag reorder with ghost and slot; order persists across restart. |
| H-05 | PASS | Corner-grip resize. |
| H-19d | FIXED (card stays bound to its pile size) | Reset size: the card keeps its enlarged drawing while the flow reflows as normal size, so the next card is drawn on top of it. Stays wrong until a reflow (stacking) or restart. |
| H-10..H-12 | PASS | Open Configuration, Button Map (title names the card), Configure input module (targets the card). |
| H-14..H-16, H-18 | PASS | Auto Mapper, Device Viewer, vJoy Viewer, Device Information open. |
| H-17 | FIXED (it showed the card's axes under another device's name) | Calibration from the NXT card opens with EVO OT L selected; NXT is in the list but not preselected. |
| H-19 | PASS / NOTE | "Assign hardware…" opens a window titled "Swap Devices" (name mismatch). |
| H-19a | PASS / NOTE | Stack selected cards works; the right-clicked card (NXT) is not the one on top. |
| H-19c | PASS | Unstack all. |
| H-19g | PASS | Delete Device: three steps (explain with "Save a copy", red confirm, result); card becomes a stub. |
| H-19g-b | FIXED (bc4ebe27) | The "deleted devices" backup is written next to the program (`_install_root()`, hardware_profile.py:747), not in the user data folder. From source that is the repo; in the exe it is the program folder. Date in the file name reads `2026-30-SEP`. |
| MENU-CLIP | FAIL (minor) | A card menu opened low on the page is cut off at the window bottom (Delete Device half hidden). |
| MENU-ESC | NOTE | Escape does not close the card menu. |

## Batch 3: Configuration / bindings catalog (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| H-03 | PASS | Double-click an input card opens Input Configuration. |
| C-02 | PASS | Previous / next arrows step through input modules and wrap; tooltips. |
| IC-01 | PASS | Type filter (all 9 entries listed); Map to keyboard / Unmapped filter the list. |
| IC-01b | FIXED | When a filter leaves no rows, the list shows "This window only shows what the input module passes. Right-click the card → Configure input module…", which is the wrong advice. |
| IC-03 | PASS | Parent row click opens the action pane. |
| IC-09 | PASS | Pane X with changes: Cancel keeps the edit; Discard drops it (reopen shows the old value). |
| IC-11 | PASS | OK commits; pane stays with "Close pane after OK" off; X then closes with no prompt. |
| IC-06 | PASS / NOTE | Child Delete removes at once with no confirmation (S-14); leaves a blank gap until the list rebuilds. |
| IC-05 | PASS | Add Action opens "New action"; Add + OK gives "1 assignment" (new action defaults to vJoy 1 X Axis). |
| IC-17 | PASS | Shown > Show child rows hides them. |
| IC-17b | FAIL (cosmetic) | Hidden child rows leave blank gaps between the parent rows. |
| IC-29 | PASS | Leaving with unsaved display (Home) asks; Cancel stays; Discard leaves. |
| IC-26 | PASS | Reset View to Default restores defaults; toast "Options have been reset". |
| IC-27 | PASS | Copy View from… lists the header and the other input modules; applies the chosen view. |
| IC-28 | PASS | Save View Settings: "Saved to the module file." and the footer names the module file. |
| C-06 | FAIL (minor) | Hide Editor with unsaved display closes without asking (S-16); the leave gate still asks later, so nothing is lost silently. |
| IC-13b | DEFERRED | Needs Gremlin running (Toggle). |
| IC-07 | DEFERRED | Live LEDs / bars need a physical press. |
| C-05, C-07..C-10, IC-02, IC-12, IC-13, IC-15..IC-25 (each section in detail) | NOT RUN | Remaining catalog detail; the display mechanism is proven by Shown, Reset, Copy View and Save. |
| stderr | PASS | No QML errors in this batch. |

## Batch 4: Output Module View (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| H-03-dest | FIXED (cards count double-clicks themselves) | Double-clicking an output card (vJoy 1) does nothing; the input card double-click works. The card menu "Output View" works. |
| H-10-dest | PASS | Output card menu: Output View, Button Map, Configure output module, Auto Mapper, vJoy Viewer, Device Information, Reset size, Hide device, Clear module settings, Delete Device. |
| OV-08b | FIXED (Columns is a maximum; the grid wraps to fit) | Default button grid is 12 columns with no wrap or scroll: with the Display Editor open only columns 1-5 show (6-12 hidden under the panel); with it hidden, 11-12 are cut at the edge. |
| OV-08 | PASS | Columns = 5 shows all 29 buttons. |
| OV-05 | PASS | Layout > Show pads off: the hat display takes the space; meters show axis labels. |
| OV-11 | PASS / NOTE | Copy View from… lists vJoy 2, vJoy 3, Xbox 360 Controller and applies; no header line, unlike the catalog (S-17, cosmetic). |
| OV-12 | PASS | Save View Settings: "Saved to the module file."; footer names modules\vjoy_1.json. |
| C-02-dest | PASS | Arrows step vJoy 1 → vJoy 2 → vJoy 3 → Xbox 360 Controller. |
| C-10 | PASS | Xbox output view: "ViGEmBus ready…", Pad picker, target list with bindings. |
| OV-01 | DEFERRED | Live pads / meters need output while running. |
| OV-02..04, OV-06, OV-07, OV-09, OV-10 | NOT RUN | Remaining section detail. |
| stderr | PASS | No QML errors. |

## Batch 5: Logical Device page (2026-09-30)

Indents (#21), natural sorting and Ctrl+Z / Ctrl+Y (#26) were tested earlier today.

| ID | Result | Notes |
|---|---|---|
| LP-01 | PASS | Find "axis" shows only Axis 1. |
| LP-03, LP-04 | PASS | "No actions in this mode" filter; Clear resets. |
| LP-19 | PASS | Name hover shows the system name. |
| LP-25 | PASS | Rename ("Your name", Hide system name option) → "Button 2  Rudder 10". |
| LP-26 | PASS (present) | "Clear name" appears for a named row. |
| LP-29 | FIXED | With 2 rows selected, Delete removes only the right-clicked row (S-15 confirmed); Group as / Move to group act on the whole selection. |
| LP-40 | PASS | Ctrl+Z restored the deleted row and the deleted group. |
| LP-35 | PASS | Move group up. |
| LP-36 | PASS | Rename group to a look-alike ("TEST 21") refused: "A group named 'test 21' already exists". |
| LP-37 | PASS / NOTE | Delete group moves its rows to Ungrouped; no confirmation (S-14). |
| LP-24 | PASS | Assign hardware: search box, devices with tri-state boxes; ticking EVO R Button 5 adds "Written by VKBsim Gladiator EVO R · Button 5" with an Invert box. |
| LP-24b | FAIL (minor) | The small expand arrow next to a device does not respond; clicking the device name does. |
| LP-57 | FIXED | Leaving the page (Home) with an unsaved action pane edit gives no warning and the edit is silently discarded (S-08 confirmed). |
| LP-16..18, LP-23, LP-27..28, LP-30, LP-38, LP-50..56 | NOT RUN / earlier | Group as, Move to group, pane and display editor were tested with #21 and #26. |
| stderr | PASS | No QML errors. |

## Batch 6: Scripts and Profile Settings (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| S-02 | PASS | Add Script: dialog opens in the data scripts folder (.py filter); a full path is accepted. |
| S-04 | PASS | Gear shows every variable type of example.py; unset ones marked red. |
| S-03 | PASS | Pencil renames the instance ("Instance A"). |
| S-05 | PASS / NOTE | Trash removes at once (no confirm, S-14). |
| S-05b | FAIL (minor) | After removing the script, the variables panel still shows its variables. |
| PS-01 | PASS | Startup Mode lists Use Heuristic / Last Active / Default / Test Mode; "Last Active" is saved to the profile XML. |
| PS-06 | FAIL (cosmetic) | Typos (see batch 1). |
| PS-02 | NOT RUN | Macro Default Delay. |
| PS-03, PS-04 | DEFERRED | vJoy Input/Output switch and initial values need Gremlin active. |

## Batch 7: Options (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| OPT-X1 | PASS | Selection combos save and load (Device change behavior Reload → Ignore survives reopen). S-27 ruled out. |
| OPT-X1b | FIXED | When a combo list opens, it highlights the first entry (Disable), not the current value. |
| OPT-X2 | PASS / NOTE | "action-priorities" is simply not shown (no blank row). S-26 ruled out. |
| OPT-A01 | NOTE | Action list includes "Root" (internal) and "Map to Xbox" sits last, out of order; group headers show raw names ("Axis-Delta", "Change-Mode"). |
| OPT-A01b | FIXED | `move()` reorders the live config list in place, so `set()` sees no change and never writes the file; reordering may not survive a restart. |
| OPT-U06 | PASS | UI scale slider is disabled while Windows scaling is on. |
| OPT-U01 | PASS | Dark mode off/on applies immediately. |
| OPT-U01b | FAIL | Light mode is only partial: Logical Device rows and editor stay dark on a white page; group headers light-on-light; Home cards stay dark. Many colours are fixed for dark mode. |
| OPT-F | PASS | Files rows all point inside the data folder; Select opens a folder picker at the current folder; Reset keeps the default. |
| OPT-F08b | FIXED | stderr after Reset: `Overwriting binding on JGTextField::text at ConfigGroup.qml:188`; the field stops following later changes. |
| OPT-P01 | FIXED | New Entry shows a row, but the entry is never written to configuration.json (the list is edited in place, so `set()` sees no change). It is lost on restart. |
| OPT-P04 | PASS | Select Executable lists running programs; Cancel closes. |
| OPT-P07 | FIXED | The row's × does not remove the entry; no error logged. |
| OPT-G.., OPT-O.., OPT-D.., OPT-C.., OPT-M.. | NOT RUN | Remaining switches (same widget as the tested ones). |
| OPT-U02 | PASS (earlier) | Windows scaling restart popup was tested when it was built. |

## Batch 8: Button Map (2026-09-30)

Exports (#11), chip context menu, Delete / Ctrl+Z, Align, Save and reopen (#20) were tested earlier today.

| ID | Result | Notes |
|---|---|---|
| BM-V02 / S-25 | NOTE (by design) | Show grid outside edit mode writes the module file immediately (`ui` block only). The editor help says "Grid / snap writes only ui", so this is intended. |
| BM-X1 / S-22 | RESOLVED | No "Export map…" / "Import map…" in the File menu; the code (openExport / openImport) has no caller. |
| BM-H01 / S-23 | PASS / FAIL | Editor help opens (F1 / Help). Its File section lists "Export map…" and "Import map…", which do not exist. |
| BM-F08 / S-24 | NOT RUN | Clear image (destructive to the module picture). |
| BM-E03..05, BM-P01..03, TBL, TXT | NOT RUN | Remaining editor menus. |
| stderr | PASS | No QML errors. |

## Batch 9: Viewers (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| VJV-01..02 | PASS (earlier) | vJoy Viewer cards and chips (see #22: all 56 NXT chips numbered). |
| XV-01 | PASS | Xbox Viewer lists the Map to Xbox source; "Activate Gremlin to plug the virtual pad and light this face." |
| XV-01b | FIXED (also Button Map device list) | The card title is the raw Logical Device ID "f0af472f-8e17-493b-a1eb-7333ee8543f2" instead of "Logical Device". |
| XV-IMG | FAIL (back burner #9) | "Xbox face image missing". |
| DV-01 | PASS (batch 1) | Device Viewer lists the devices. |
| DV-05..07, VJV-03, XV-03 | DEFERRED | Need physical input / Gremlin active. |
| DV-02 / S-30 | NOTE | Viewers ignore Esc (by design in code). |

## Batch 10: Calibration and Configure Module (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| CAL-01 | PASS | Opens from Tools (first module selected). From a card it does not preselect that card (H-17). |
| CAL-04 | PASS | Changing a limit shows "Not saved" and a gold save icon. |
| CAL-05b | FIXED | Reset (↻) restores the value but "Not saved" and the gold icon stay. |
| CAL-09 | FIXED | Closing the window (its X, or a close request) with a real unsaved change (High 32,767 → 32,766) closes without asking and the change is lost. The close gate calls `_calib.hasUnsaved()`, which returns false while the row says "Not saved". |
| CFGM-02, CFGM-03 | PASS | Untick a claim; type a friendly name. |
| CFGM-05 | PASS | Cancel with changes asks: "Checks, names, and the picture on this screen are not saved…" (Cancel / Discard / Save). |
| CFGM-06 | PASS | Save writes the module: Button 9 unclaimed (55 buttons), friendly `button:1 = Fire`; "Saved to the module file." |
| S-31 | NOT VERIFIED | The window closed after saving through the Cancel prompt (expected); the plain Save module button was not tried separately. |
| CAL-07, CAL-08, CAL-10, CFGM-02b | DEFERRED | Need a physical stick. |
| CFGM-04a..f | NOT RUN | Module file dialog (import, browse, delete file). |

## Batch 11: Other dialogs (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| MM-01 | PASS | Add Mode: duplicate "Test Mode" refused (red border, OK disabled); "Flight" added and sorted. |
| MM-01b | FIXED | "test mode" (a case look-alike of "Test Mode") is accepted, unlike group names. |
| TB-09 | PASS | Configuring mode → Flight; footer "Executing mode: Flight". |
| MM-04 | PASS / NOTE | Deleting the current mode (no confirm, S-14) falls back to Default in the box and the footer. |
| AM-05 | PASS | Create 1:1 mappings: "Created 36 mappings, retained 0 previous bindings."; boxes clear afterwards (S-32 ruled out). |
| AM-03 | NOTE | "Overwrite used inputs" is on by default, so existing bindings are replaced without warning. |
| AM-08 | FIXED | Closing the Auto Mapper after creating mappings shows "A fatal error occurred: RuntimeError: Signal source has been deleted" (reproduced twice; the app keeps running). |
| DP-02 | PASS | Device Pack opens alone: device preview, pack size, Export… |
| DP-03..13, SW-01..03, HLP topics, DI-01 | NOT RUN | Remaining dialog detail. |

## Batch 12: Action editors (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| AE-BTN | PASS | All 19 button actions added to NXT Button 1 in one pane; each editor drew its controls. |
| AE-AXIS | PASS | All axis actions added to X Axis (Response Curve, Axis Delta, Condition, Dual Axis Deadzone, Merge Axis, Split Axis, Map to Xbox). The deadzone/curve warning icon explains itself on hover. |
| AE-MOUSE | FIXED (20722eed) | Map to Mouse shows only its title row. The editor does not load: "MapToMouseAction.qml:193:17 / 202:17: Property value set multiple times". Each radio button sets `autoExclusive: false` twice (added by b4c70f9e). A scan of every QML file found no other duplicate property. |
| AE-XBOX-TRIG | PASS | Map to Xbox → Left Trigger shows the new Full axis / Upper half picker (#23d). |
| AE-HAT | NOT RUN (UI) | The NXT has no hat. Hat as Buttons is covered by the save/load test below. |
| AE-NARROW | NOTE | At this window size some right-hand controls are cut off (Double Tap's Add button, Condition's "Add Con…", Response Curve deadzone boxes overlap). |
| AE-XML | NEW TEST | `test_action_xml_round_trip.py` saves and reloads every action plugin for each input type it supports (42 pass, 15 skipped because a new action is not valid until set up). |
| AE-XML-NONE | FIXED | An empty text field reloads as the word "None": Description, Run Command (executable/arguments), Text to Speech. `_property_from_string[String]` is `str`, so `str(None)`. The next save writes "None". Marked xfail. |
| AE-XML-CHAIN | FAIL (minor) | A new Chain's empty "Sequence 0" is gone after save and reload. Marked xfail. |
| AE-LABEL | PASS | A blank action label stays blank after save and reload. |
| AE-SET-ALL | DEFERRED | Setting every control and reloading in the app needs Save on the sandbox profile plus physical input for Record buttons. |

## Batch 13: HiDHide, no driver changes (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| HH-00 | PASS | Opens from Tools → Device setup → HiDHide; window size and place kept after close/reopen. |
| HH-00b | FIXED | The splitter is not restored. Dragged to show 5 rows, saved `split-ratio` 710; reopened showing 2 rows, and the reopen saved 332 over it. `DialogHardwareHide.qml:250/392` use the thousandths value as a pixel `preferredHeight`, and both panes have `fillHeight`. |
| HH-01 | PASS | "HiDHide driver found 1.4.191.0", green dot. |
| HH-02 | PASS | Test HiDHide opens Game Controllers (joy.cpl); closed by script. |
| HH-03 | NOT RUN | Get HiDHide opens a web page (external). |
| HH-07 | PASS | Gaming devices only: on = vJoy ×3 + both Gladiators (HIDDEN, real driver state); off = every HID device, sorted by name. |
| HH-08 | PASS / NOTE | Change image opens a "Device image" picker (images filter); cancelled. It starts in the repo's `user_scripts` folder, left over from another dialog. |
| HH-04..06, HH-05b, HH-09..12 | DEFERRED [U] | Change the real driver. |
| stderr | PASS | No QML errors. |

## Batch 15: Build, code checks only (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| B-SPEC-DLL | PASS | Spec bundles vJoyInterface.dll, dill.dll, ViGEmClient.dll; datas include gfx, qml, theme, device_db.json, version.json and every action_plugins file. |
| B-SPEC-IMPORTS | SUSPECT | `action_plugins.axis_delta` and `action_plugins.run_command` are not in `hidden_imports` (all other plugins are). Their .py files ship as data and load via importlib, so they may still work. Check in the exe: Axis Delta (axis input) and Run Command (button) in Add Action. |
| B-01..04 | DEFERRED | Need the 76.6 MB release zip downloaded (your permission) or a local pyinstaller build. The current R1 zip predates the "Gremlin Platforms" data folder change. |

## Failure summary, ranked (2026-09-30)

Data loss or broken feature first. IDs point to the batch rows above.

1. ~~AE-MOUSE~~ fixed 20722eed. Also fixed: radio buttons could be clicked off (#33, 154ed217).
2. ~~AM-08~~ fixed: the cause was a closed Manage Modes model (ModeHierarchyModel) still wired to profileChanged; also in R16. Also fixed #34: old Map to Xbox actions no longer log a trigger-range ERROR.
3. ~~LP-57, CAL-09, W-03, F-02b~~ fixed (#10 parts A-D). CAL-09 cause: helpers.js destroyed every tool window on close even when it asked to stay open (also Button Map, Configure Module).
4. ~~OPT-P01, OPT-P07, OPT-A01b~~ fixed (in-place list edits save; auto-load row fits so × is clickable).
5. ~~AE-XML-NONE~~ fixed (empty text loads as "").
6. ~~LP-29~~ fixed (Delete acts on the selection).
7. ~~F-03~~ fixed (R16 recent-profiles code restored).
8. ~~H-19g-b~~ fixed bc4ebe27: backups go to the data folder; Deleted devices folder picker in Options.
9. ~~HH-00b~~ fixed (HiDHide splitter).
10. ~~BM-X1 / S-22~~ resolved: moved to Device Pack on purpose (bbf22b58); stale help fixed, dead Button Map pack code removed. Note: Button Map's File menu also lists the Logical Device by raw ID (see XV-01b).
11. H-03-dest, H-19d, H-17, H-13, OV-08b, XV-01b: Home and viewer behavior.
12. B-SPEC-IMPORTS (suspect): axis_delta / run_command missing from spec hidden imports.
13. Minor/cosmetic: F-01b, HD-01b, PS-06, MENU-CLIP, IC-01b, IC-17b, C-06, LP-24b, S-05b, OPT-X1b, OPT-U01b, OPT-F08b, CAL-05b, MM-01b, AE-XML-CHAIN, AE-NARROW, HH-08 note.
14. Back burner: XB-IMG / XV-IMG (#9).

### Noted while fixing #10 (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| F-04 | NOTE (by design: Startup Mode "Use Heuristic" picks the first parentless mode) | After loading a profile the Configuring mode switches to Test Mode (not Default), so rows show Not bound. |
| F-05 | FAIL (minor) | An open action pane stays open showing the previous profile's action after Load. |
| F-06 | FAIL (minor) | Opening a device page (NXT) marks the profile as unsaved with no mapping changes, so quitting asks about the profile. |
| W-03b | NOTE | When quitting, the display-options prompt says "Leave this device and they will be lost" (wording from the leave path). |
| OPT-RS | FIXED (plus Reset all card sizes in the card and background right-click menus) | Options > Display > Reset all card sizes clears the saved sizes, but Home keeps showing the old sizes until restart (Options uses its own model copy). |
| CAL-11 | FIXED | The arrows always worked: showing "Not saved" made the axis block taller, so the spin boxes moved down and the next click landed above them. The label now keeps its space. |
