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

- [x] ~~DV-01..04 [A] Device Viewer: opens, pauses highlighting, fold rows, name tooltip. Esc does not close it (see S-30).~~ Removed (legacy Device Viewer).
- [x] ~~DV-05..07 [U] Temporal, Current, and Buttons & Hats switches with a moving stick.~~ Removed (legacy Device Viewer).
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
6. ~~Device Viewer switches (DV-05..07).~~ Removed (legacy Device Viewer).
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
| MENU-CLIP | FIXED | A card menu opened low on the page is cut off at the window bottom (Delete Device half hidden). |
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
| IC-17b | FIXED (compact spacing when child rows are hidden) | Hidden child rows leave blank gaps between the parent rows. |
| IC-29 | PASS | Leaving with unsaved display (Home) asks; Cancel stays; Discard leaves. |
| IC-26 | PASS | Reset View to Default restores defaults; toast "Options have been reset". |
| IC-27 | PASS | Copy View from… lists the header and the other input modules; applies the chosen view. |
| IC-28 | PASS | Save View Settings: "Saved to the module file." and the footer names the module file. |
| C-06 | FIXED | Hide Editor with unsaved display closes without asking (S-16); the leave gate still asks later, so nothing is lost silently. |
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
| LP-24b | FIXED | The small expand arrow next to a device does not respond; clicking the device name does. |
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
| S-05b | FIXED | After removing the script, the variables panel still shows its variables. |
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
| OPT-U01b | FIXED | Colour tokens in Style (dark = the old palette, light = same roles); Home, input page, Logical Device, output view, dialogs, viewers and Button Map chrome follow Dark mode. Display Editor colours never changed by the user follow the mode (saved values equal to the old dark defaults count as unchanged); each picker has Default. Device photos and what is drawn on them (Button Map rig, Xbox face) keep their colours. Guard: test_colour_tokens.py. Sandbox: light and dark checked on each screen. |
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
| BM-CARD-TRAY | FIXED | Button Map opened from a Home card (window not yet open) showed no chips in Edit Mapping: the other devices' panels turned the face off while the list filled in. Now only the panel in use does. Sandbox: card path, menu path, switching devices all show chips. |
| LD-DRAG-STUCK | FIXED | Item drag used Windows' drag, which could start after release and swallow the next click. Now an in-app drag (as R16's action editor): ghost follows the pointer, drop on release. Group drag no longer logs ReferenceError (moves run after the handlers). Sandbox: quick and slow drags, before / into group, release outside, group drag. |
| stderr | PASS | No QML errors. |

## Batch 9: Viewers (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| VJV-01..02 | PASS (earlier) | vJoy Viewer cards and chips (see #22: all 56 NXT chips numbered). |
| XV-01 | PASS | Xbox Viewer lists the Map to Xbox source; "Activate Gremlin to plug the virtual pad and light this face." |
| XV-01b | FIXED (also Button Map device list) | The card title is the raw Logical Device ID "f0af472f-8e17-493b-a1eb-7333ee8543f2" instead of "Logical Device". |
| XV-IMG | FAIL (back burner #9) | "Xbox face image missing". |
| DV-01 | PASS (batch 1) | Device Viewer lists the devices. |
| DV-05..07 | REMOVED | Legacy Device Viewer removed (Tools menu, toolbar Device button, card menu, its QML and state models). |
| VJV-03, XV-03 | DEFERRED | Need physical input / Gremlin active. |
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
| AE-XML-CHAIN | FIXED | Empty sequences (and their order) survive save and reload; a middle empty one used to shift the rest. |
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
| B-SPEC-IMPORTS | FIXED | Both added to `hidden_imports` (as in R16); guard test `test_spec_hidden_imports.py` fails if any plugin folder is missing from the list. Local build: both are in the exe's module archive. |
| B-01 (local build) | PASS | Local `pyinstaller` build (no zip) starts with sandbox USERPROFILE, opens the sandbox profile, quits cleanly. |
| B-03 (log) | PASS / [U] | No errors in system.log for the exe run, so no plugin failed to load. Add Action list not checked on screen (display was off): confirm Axis Delta and Run Command by hand. |
| B-02, B-04 | DEFERRED [U] | Xbox Viewer, Help, About and theme in the exe: hands-on. |
| B-SPEC-STALE | NOTE | Build log: hidden import `gremlin.ui.profile_devices_model` not found (module no longer exists). Harmless; can be removed from the spec. |

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
12. ~~B-SPEC-IMPORTS~~ fixed: axis_delta / run_command added to spec hidden imports.
13. Minor/cosmetic: F-01b, HD-01b, PS-06, MENU-CLIP, IC-01b, IC-17b, C-06, LP-24b, S-05b, OPT-X1b, OPT-U01b, OPT-F08b, CAL-05b, MM-01b, AE-XML-CHAIN, AE-NARROW, HH-08 note.
14. ~~Back burner: XB-IMG / XV-IMG (#9)~~ fixed: Xbox face loads xbox360_two_panel.jpg from the data folder's modules/library; picture labels corrected (only LB / RB on the bumpers kept).
15. To do: [Stock Images] Code still looks for the stock pictures in `qml/images`, which "moved user data" (a4f743fc) emptied; the pictures are now in `User_Data/images` and `User_Data/modules/library`. Points at the old path: `imagesFolderUrl()` (hardware_profile.py, creates an empty `qml/images` next to the exe), `_stock_photo()` / `_stock_photo_l()`, the relative-path fallback in hardware_profile.py, Button Map `stockImage`, VkbRigFace / VkbRigEditor (`images/vkb_gladiator_rig.jpg`), Xbox360Face (done: now uses the modules library lookup). Decide where stock pictures live for other users (bundled read-only vs copied into the data folder), then point all of these at one place.
16. To do: [Xbox Pads] Only one Xbox pad for now ("Xbox 360 Controller" = pad 1). Later: a way to add Xbox output modules for pads 2-4 ("Xbox 360 N", nothing claimed), listed in Map to Xbox and the viewers. The output layer already maps "Xbox 360 N" to pad N (output.xbox_pad_of).

### Noted while fixing #10 (2026-09-30)

| ID | Result | Notes |
|---|---|---|
| F-04 | NOTE (by design: Startup Mode "Use Heuristic" picks the first parentless mode) | After loading a profile the Configuring mode switches to Test Mode (not Default), so rows show Not bound. |
| F-05 | FIXED (panes close after a profile change; edited configuration panes now ask before leave, Load, New and Quit) | An open action pane stays open showing the previous profile's action after Load. |
| F-06 | FIXED | Cause was the older file format (no trigger-range), not the page: the unsaved check compared a fresh write against the file on disk. It now compares against the profile as loaded or last saved. Sandbox: older file, open NXT, quit: no prompt; delete a mapping: prompt; save, relaunch, quit: no prompt. |
| W-03b | FIXED | When quitting, the display-options prompt says "Leave this device and they will be lost" (wording from the leave path). |
| OPT-RS | FIXED (plus Reset all card sizes in the card and background right-click menus) | Options > Display > Reset all card sizes clears the saved sizes, but Home keeps showing the old sizes until restart (Options uses its own model copy). |
| CAL-11 | FIXED | The arrows always worked: showing "Not saved" made the axis block taller, so the spin boxes moved down and the next click landed above them. The label now keeps its space. |

## Phase 0 (architecture review, 2026-10-01)

Pipeline: hardware -> input module -> wiring -> output module -> driver. Decisions: block unclaimed outputs (firewall), flag unclaimed wires, profiles keep vJoy numbers (2A), keyboard gated by claim (3A).

| ID | Result | Notes |
|---|---|---|
| P0.1 | FIXED 6e5903bb | Home vJoy card "last:" reads only claimed outputs via output_modules.vjoy_output_state; no blind 1..128 probe, no log flood; polls only while a profile runs. |
| P0.2 | FIXED 04b47030 | Options > Reset all card sizes uses CardSizes; no second Home model. |
| P0.3 | FIXED 6228041d | Button Map group members keep their kind (axis/hat/button); no duplicates in the tray; ungroup restores kinds. |
| P0.4 | FIXED 7856814d | Output picker keeps a saved unclaimed output, flags it "(not claimed)", writes nothing back. |
| P0.5 | FIXED 1f5123ca | Map to vJoy behaviour change updates vjoy_input_type (typo, also in R16); Change Mode stray line removed. |
| P0.6 | FIXED c896cd0c | Xbox pads labelled "Xbox 360 N", not "vJoy Device N" (label not displayed yet). |
| P0.7 | FIXED (this commit) | Logical Device events were dropped by the input gate (no claim), so Logical Device -> vJoy/Xbox never ran; Logical Device is now always forwarded like OSC. |
| P0-HANDS-ON | [U] | With Gremlin active: Home vJoy card last line updates and system.log has no "Invalid button index"; a Logical Device input wired to vJoy fires; a mixed Button Map group lights on the right inputs. |
| P0-DATA | NOTE | Your profile has 70 wires from NXT buttons 57-126 to vJoy 3 buttons 57-126: neither the NXT input module nor vjoy_3 claims them. Left as is (flagged by design). |

## Phase 1 (module layer, 2026-10-01)

| ID | Result | Notes |
|---|---|---|
| P1a-P1b | DONE 613d21a5, 465ad1e3 | One GUID key and one claim API (gremlin/modules/ids.py, claim.py). |
| P1c | DONE add3c7bc | One module registry and vJoy-id resolver; "vJoy 1 (2)" is vJoy 1 (the runtime read it as 12). |
| P1d | DONE 506775f2 | Gate, runtime, calibration lookup and Auto Mapper lists live in gremlin/modules; core no longer imports the UI for module logic. |

## Phase 2 (output modules are the firewall, 2026-10-01)

Decisions: Xbox starts with nothing claimed (1A); scripts go through the firewall (2A); the vJoy Viewer shows what the output module sent (3A).

| ID | Result | Notes |
|---|---|---|
| P2a | DONE b0709d34 | gremlin/modules/output.py: claimed reads/writes, driver status and resets. Home, live view, condition, status and Xbox pages read through it. |
| P2b | DONE 6afb1c15 | Map to vJoy, macro, auto-release, start-up axes and scripts write through it. Unclaimed vJoy outputs are blocked and logged once per run. |
| P2c | REVERTED (XB-FIX) 6d691023 | Xbox output module: claim per control on the Xbox page; Map to Xbox lists claimed controls and flags an unclaimed saved one; Xbox Viewer shows claimed controls. |
| P2d | DONE (this commit) | vJoy Viewer cards read the vJoy output module (claimed outputs, only while Gremlin runs) instead of DirectInput readback. |
| P2-HANDS-ON | [U] | With Gremlin active: a claimed vJoy button fires; an unclaimed one (vJoy 3 button 57+) does nothing and system.log shows one "Output blocked" line for it; claim Left Trigger on the Xbox page and Map to Xbox drives it; the vJoy Viewer card moves with the stick. |
| P2-DATA | NOTE | The 70 NXT 57-126 -> vJoy 3 57-126 wires stop reaching vJoy until vJoy 3 claims buttons 57-126. (Xbox needs no claim, see XB-FIX.) |

## Phase 3 (input modules are the only way in, 2026-10-01)

Decisions: input highlighting and "Listen for input" stay as they are (no status note, no one-click claim); Configure Input Module, calibration and the axis graph keep raw hardware access.

| ID | Result | Notes |
|---|---|---|
| P3a | DONE 3339c788 | Keyboard bindings take events from the input runtime; only keys the Keyboard module claims reach the profile. No saved keyboard claim = every key (matches the Configure dialog). Typing in Windows is never affected. |
| P3b | DONE e423428d | Configuration page live values and both viewers' hardware side use the claimed feed. Macro recording stays raw (it records what a macro sends). |
| P3c | DONE 3ff17f7e | Merge Axis, Dual Axis Deadzone, Condition and script joy/keyboard read through the input modules; unclaimed inputs read neutral. |
| P3d | DONE (this commit) | Module file lookup: saved link, then the file bound to this exact device, then name. A renamed device keeps its file; a stale id never pulls in another device's file. |
| P3-HANDS-ON | [U] | With Gremlin active: a keyboard binding on a claimed key fires; untick that key in Configure Input Module (Keyboard), save, re-activate: it no longer fires, and typing in Notepad still works. |

## Phase 4 (wiring speaks in output modules, 2026-10-01)

Decisions: Auto Mapper claim switch, off by default (1A); one Xbox pad for now (to-do 16); output names shown in brackets in long labels (3A).

| ID | Result | Notes |
|---|---|---|
| P4a | DONE d2ccb0a8 | One destination label (gremlin/modules/wiring.py): "vJoy 3 · Button 5 (Fire)", chips "vJoy 3 B5"; "(not claimed)" / "(no output module)" flags. Configuration page, Button Map chips, Device Pack export, Xbox Viewer, Condition. |
| P4b | DONE 8842c54e | Map to Xbox lists Xbox output modules by name; a saved pad without one stays listed, marked. Xbox page shows its module and pad (no Pad box). |
| P4c | DONE (this commit) | Auto Mapper maps only to claimed outputs (and ones the vJoy device has), reports skips ("Skipped vJoy 3 buttons 57-58: not claimed by the output module."); "Also claim the matching outputs" switch, off by default. Sandbox: NXT -> vJoy 3 made 59 mappings, nothing skipped. |
| P4-HANDS-ON | [U] | Your profile: the NXT 57-126 -> vJoy 3 wires show "(not claimed)" on the Button Map chips / card hints. |

## Phase 5 (cleanup, 2026-10-01)

| ID | Result | Notes |
|---|---|---|
| P5a | DONE fb2c6e75 | Dead code removed (1,487 lines): VJoyDevices, PairDeviceModel / PairLiveState / InputPairing, ModulePairHatModel, the pre-module Auto Mapper path, 14 unused slots, 6 unused QML files (DeviceInputList + R16 leftovers). Guard: test_no_dead_qml. |
| P5b | DONE cf17e9a3 | One copy of each rule: vJoy output-module list (output layer), axis names (wiring), destination label in the vJoy Viewer pair rows, vJoy resolver in live_input, output rule (registry). Guard: test_one_copy_of_each_rule. |
| P5c | DONE (this commit) | Full suite and lint (no new lint since 1.0.1 in the 72 changed Python files), local PyInstaller build (no missing imports) and the built exe starts and loads the profile; sandbox tour: Home, input/output pages, Logical Device, both viewers, Button Map, Map to vJoy / Map to Xbox, Auto Mapper, Calibration, Device Pack, Manage Modes, Options. |

## XB-FIX: Xbox output is a pass-through (2026-10-01)

| ID | Result | Notes |
|---|---|---|
| XB-FIX | FIXED (this commit) | 1.0.2 put a claim gate on Xbox (P2c), so every Map to Xbox action was blocked. The Xbox output module is a pass-through to ViGEm, as in GremlinEx (Map to GamePad: any control, any pad, no claim). Removed: Xbox claims, Claimed boxes / Claim all, "(not claimed)" Xbox labels and warnings, the claim filter on the Xbox Viewer. Map to Xbox lists all 22 controls; saved pads 2-4 still send. The output layer stays the only code touching ViGEm. |
| XB-HANDS-ON | [U] | With Gremlin active: a Map to Xbox action drives the pad (e.g. Logical Device input -> Left Trigger), and the Xbox Viewer shows it. |

## HELP: User Guide rewrite (2026-10-01)

| ID | Result | Notes |
|---|---|---|
| HELP-A | DONE 101a0a16 | Getting Started (pipeline, First setup, Toggle and status, Profiles, What is saved where), Devices and Modules, Troubleshooting. |
| HELP-B | DONE 602b87a8 | Configuration, Actions (one topic per action, six were missing), Logical Device (9 -> 4 topics), Modes. |
| HELP-C | DONE 2352a3d0 | Tools, Options and Profile, Button Map F1 help rewritten (zoom 75-600%, real right-click menu), About shows the version and this repo, orphan button_map_editor_help.md removed. Guard: test_help_guide (menu paths exist, every action has a topic, no removed features). |
| HELP-BUG | FIXED be7a9ec6 | Decided (option c, compared with upstream R16): Startup Mode picks the mode when the profile is loaded (ModeManager.reset uses mode_manager.resolve_start_mode, so Load, New and auto-load land in it); Toggle keeps starting in the toolbar mode (83078f83). R16 instead always starts Toggle in Startup Mode, but its toolbar is only the editing mode. Profile Settings text and the User Guide topic updated; unit tests in test_modes.py. |
| HELP-BUG-HANDS-ON | [U] | Set Startup Mode to a named mode, save, reload: the toolbar shows that mode and Toggle runs in it. Last Active: run in a mode, stop, reload: toolbar shows that mode. Change the toolbar mode, Toggle: runs in the toolbar mode. |

## INTEG: integration test suite (2026-10-01)

| ID | Result | Notes |
|---|---|---|
| INTEG-SPLINE | FIXED ecaf6812 | Real bug: 0c339239 left a use of the removed eps in CubicSpline.fit, so a Cubic Spline curve with 3+ points raised NameError (adding a point, loading the profile). Unit test in test_splines.py. |
| INTEG-MODULES | FIXED 2c805655 | Tests ran with an empty temp modules folder, so the layer rule dropped the vJoy test inputs and blocked every vJoy output. device_modules fixture writes an input module bound to the vJoy DI GUID and an unbound "vJoy N" output module, both claiming everything. |
| INTEG-SCRIPTS | FIXED 2c805655 | Relative script paths resolve against the user scripts folder (empty temp folder in tests). _bundled_user_scripts copies user_scripts/*.py there. |
| INTEG-PROCESS | FIXED 2c805655 | test/unit + test/integration in one process: test_sequence_reorder.py makes a plain QCoreApplication at collection, so JoystickGremlinApp/Backend(engine) is never created. Run the suites separately; _own_process fails with that message. Making the unit test use qapp instead launched a real app window in the unit run and hung, so it stays. |
| INTEG-RESULT | PASS | test/unit 519 passed, 15 skipped; test/integration 219 passed, 222 subtests (was 147 passed, 109 failed, 23 errors). |
| INTEG-GUID-NOISE | OPEN | Integration runs print a ValueError traceback from DeviceModel._set_guid (gremlin/ui/device.py:359): a QML binding sets an empty/invalid GUID. Not a test failure; present before these fixes. |

## UPD: installer and in-app updater (2026-10-01)

| ID | Result | Notes |
|---|---|---|
| UPD-ISS | DONE | installer/gremlin_platforms.iss replaces the R15 script: new AppId, per-user (PrivilegesRequired=lowest), folder page prefilled with {autopf}\Gremlin-Platforms and remembered, refuses a folder that needs admin, removes the old _internal, license page, Start menu + optional desktop shortcut, /LAUNCH=1 restarts after a silent update. |
| UPD-WORKFLOW | DONE | release-exe.yml takes the version from version.json and publishes Setup.exe and the zip; publish=false builds only (workflow artifact). GitHub's windows-latest image has Inno Setup 6.7.1. |
| UPD-APP | DONE 7ee80135 | gremlin/updater.py + gremlin/ui/update_model.py + DialogUpdate.qml: Help -> Check for Updates, startup check (on by default for new configs), Update now / Skip / Later, download with progress, size + SHA-256 check against GitHub's digest, installer runs after Gremlin shut down through the normal quit path. Portable and source copies only link to the release page. "Updated" notice once after an update. User Guide topic "Installing and updating". |
| UPD-UNIT | PASS | test_update_check.py (asset choice, digest rules, offer/skip, install kind, feed URL, installer/workflow names agree), test_update_model.py (no install without a verified download, cancelled quit clears it, post-update notice). |
| UPD-NET | PASS | Local http server feed via the hidden update-feed-url: check -> available -> download -> verified -> installRequested; a tampered file is rejected and deleted. |
| UPD-DIALOG | PASS | DialogUpdate.qml loaded offscreen: text and buttons right for checking, upToDate, available, downloading, ready, error; no QML warnings. |
| UPD-BUILD | PASS (local, 1.0.3) | Inno Setup 6.7.3 (per-user) built Gremlin-Platforms-R1-1.0.3-Setup.exe (46.5 MB). Silent tests: default install to %LOCALAPPDATA%\Programs\Gremlin-Platforms (Apps entry name/version/publisher right, Start menu folder), install over it removes stale _internal files and keeps the user's own files, custom /DIR remembered by the next update, uninstall removes folder/Apps entry/Start menu, user data folder untouched (135 files). Not run here: /LAUNCH=1 relaunch (would start a second Gremlin) and clicking through the wizard. Paths: Qt's deepest file is 146 chars below the install folder, so an install folder longer than ~110 chars fails (exit 5), like the zip would. |
| UPD-HANDS-ON | [U] | Install 1.0.2 from the Setup, point update-feed-url at a local 1.0.3 release, Help -> Check for Updates -> Update now: Gremlin closes, installs without a UAC prompt, starts 1.0.3, says "Updated", profiles/settings kept. Uninstall leaves the user's Gremlin Platforms folder untouched. |
| UPD-EXISTING-CONFIG | NOTE | Check for updates defaults to on only where it was never saved; a configuration.json that stored False (as on the dev machine) keeps it off until ticked in Options -> Global. |

## BMAP: Button Map editor expansion (started 2026-10-02)

Decisions (user): every element can be locked and hidden from a Layers panel (the pin goes); hidden = hidden in the editor and the live map, left out of image/PDF export, kept but still hidden in a Device Pack; locked = ignores canvas clicks (click through), edited via the Layers panel; locking a chip or group locks its hotspot, leaders and members; a locked leader's attached end still follows its chip. Arrows are high priority. All extras are in.

| ID | Result | Notes |
|---|---|---|
| BMAP-0 | DONE eef8a60e | Safety net: test/unit/rig_editor_harness.py drives VkbRigFace + VkbRigEditor off-screen (own process) through load_l and session_r (click, drag, nudge, draw ellipse/rect/text/table, resize, move, style, draw-around, group/ungroup, Ctrl+D/C/V, Delete, forward/back, locked drag, band select, Ctrl+Z, redo). test_rig_editor_golden.py compares every step's state (ids renumbered) and 6 screenshots with rig_editor_golden/. Verified it catches a 1px nudge change (data) and a half-drawn ellipse (518 px). RIG_GOLDEN_UPDATE=1 rewrites the goldens. |
| BMAP-1 | DONE 83c49fd4..0cb16fee | VkbRigEditor.qml 7697 -> 2230 lines (1226 are the menus BMAP-3 replaces). Delegates, canvases, photo and pointer handling to Rig*.qml components; 271 functions to rig_*.js code-behind files by topic with one-line forwarders, so no caller changed. Goldens (now also right-click menus and an api_sweep scenario) were made on the pre-split code and match. |
| BMAP-2 | DONE 67ccc293 | Block arrow shapes arrow/arrow2 (filled or hollow); Line and Arrow tools draw shape "line" (ends stored as fractions of a box with margin for heads; headStart/headEnd none|solid|hollow; Shift = 15 degree steps; two end handles; click must be near the line); Outline Solid/Dashed/Dotted (dash key, dash lengths fixed in px); Line ends menu with Swap heads; width changes re-fit a line's box. New keys only, so old layouts and goldens are unchanged. rig_shapes.js (.pragma library) tested by test_rig_shapes.py; golden scenario arrows. |
| BMAP-2-HANDS-ON | [U] | In the Button Map editor: Draw -> Free drag -> Arrow shape / Double arrow shape / Line / Arrow; drag a line's end handles; Line ends Solid/Hollow at either end; Outline Dashed/Dotted; Stroke 6 keeps the heads whole; save, reopen, and check the live map shows them. |
| BMAP-3 | DONE aedea2d1 | RigContextMenu.qml + rig_menu.js replace _ctx, _textCtx and _tableCtx (editor 2230 -> 1063 lines). Target kinds chip, group, leader, shape, line, image, text, table, multi, canvas; only what applies is listed. Opens compact (title with Undo/Redo, quick actions, collapsed sections); one section open at a time, remembered per kind for the session; value rows (sizes, widths, opacity) apply at once and stay open, actions close; flips at window edges, scrolls when too tall; keys Up/Down/Enter/Right/Left/Esc. Golden scenario menu (mouse header clicks, keyboard value steps, remembered section, canvas tool, small window); other goldens unchanged except the recorded menu text. F1 help and the User Guide describe it. |
| BMAP-3-HANDS-ON | [U] | Right-click a chip, group, leader, shape, line, picture, text box, table, several items and empty canvas: only relevant sections, opens small, sections open/close, last section remembered, value rows apply live, dark mode colours, near the window edges it stays on screen. |
| BMAP-4 | DONE 6405497b | rig_layers.js + RigLayersPanel.qml (View > Layers, right of the map, on by default). Stacking is the nodes list order (last on top) for drawing and clicks; old layouts are sorted once by zLayer (drawings 2, chips 3 by default) and pinned becomes locked, so they look the same. New drawings go on top of the drawings under the chips, text boxes on top. hidden/locked on every node, hotHidden/hotLocked for a chip's hotspot, hidden/locked per leader; locking/hiding a chip or group covers its parts. Hidden: not drawn (live map too), not clicked, left out of exports (grab of the view). Locked: clicks pass through, not moved, nudged, deleted or band-selected. Photo hidden/locked saved in the photo pose (Python _photo_pose keeps them). Panel: eye and lock per row, chip rows open to hotspot and leaders, drag to restack, double-click renames a drawing, Show all, Unlock all, filter. Ctrl+L / Ctrl+Shift+L. Arrange section: Bring to front, forward, back, Send to back, Lock, Hide. Pin icon removed. Goldens: new layers scenario (legacy fixture with zLayer and pinned); other images only differ by the pin icon, real stacking, and the menu's Arrange row; harness now sets the app font (fallback font varied between runs). |
| BMAP-4-HANDS-ON | [U] | Open an existing layout: it looks as before. Layers panel: hide and lock chips, drawings, a chip's leader and hotspot, the photo; clicks pass through locked items; drag rows to restack; save, reopen: flags and order kept; live map hides hidden items; Export PNG leaves them out; a Device Pack keeps them hidden. |
| BMAP-5 | DONE 36b364f4 | Rotate handle above a selected shape or picture (drag; Shift = 15 degree steps); a turned box resizes along its own axes with the opposite side fixed (Shapes.rotatedResize, unturned boxes keep the old path); Rotate and flip menu section with a typed angle (new number row), quarter turns, +/-15, Flip horizontally/vertically (flipH/flipV on shapes and pictures; a line's ends move); pictures keep proportions from a corner unless Shift, shapes the other way; Shift on a handle no longer deselects (it made Shift+drag do nothing before); photo transform now scale, rotate, then move (an offset photo no longer swings round the frame centre); photo pose and Layers flags are in undo steps (sliders grouped into one step, sliders follow undo); Reset photo keeps hidden/locked. Text boxes and tables stay level. Tests: 25 rotated-resize cases in test_rig_shapes.py, golden scenario transform. |
| BMAP-5-HANDS-ON | [U] | Turn a shape and a picture with the handle and Shift; resize them turned; type an angle; flip; a picture keeps its shape from a corner; Photo > Adjust photo with an offset and rotation turns about the photo's centre; Ctrl+Z undoes a photo change and the sliders follow. |
| BMAP-6 | DONE 28cbab07 | rig_props.js + RigPropsPanel.qml (View > Properties, top left while something is selected). Drawings: X/Y/Width/Height (% of page), Angle, fill, colours, line width, outline, opacity, font for text; lines: start and end points, colour, width, outline, heads; chips: X/Y, hotspot X/Y, font and chip size, colours; several items: style only, applied to all. Numbers by typing + Enter, values by click, colours open the colour picker; locked items read-only. Golden scenario props. Harness: sets the window's Universal theme as the Button Map window does, parks the mouse and focus after typing, and reseeds undo after loading (all three varied between runs). |
| BMAP-6-HANDS-ON | [U] | Select a shape, a line, a chip, two shapes and a locked item; type values and check the map; colours open the picker; dark mode looks right. |
| BMAP-7 | DONE a7594070 | rig_align.js: Align and distribute section in the several-items menu (Across: Left/Centre/Right, Down: Top/Middle/Bottom, Space out: Across/Down for 3+); measured by node boxes, moved through moveNodeBy, the per-item move split out of nudge (nudge unchanged: all goldens identical). Locked items neither move nor count. Golden scenario align. |
| BMAP-7-HANDS-ON | [U] | Select shapes and chips, right-click one: align each way and space out; a locked item stays. |
| BMAP-8 | DONE 20aa25de | Crop: picture menu Crop (crop mode, handles shown in the accent colour cut instead of scale) and Reset crop; Properties Crop left/top/right/bottom; n.crop {l,t,r,b}; Shapes.cropBox/cropFromDrag keep what stays visible in place (also turned); drawn as the whole picture shifted inside a clipping box (sourceClipRect fed back on itself). Esc or another selection ends crop mode. Paste picture: HardwareProfile.clipboardHasImage / pasteClipboardImage / savePastedImage (pasted.png, pasted_1.png... in the device folder and library), Edit > Paste picture, Ctrl+Shift+V, canvas Draw section. Fixed: cancelAllActions (Esc) still closed the removed _tableCtx/_textCtx menus and stopped with a ReferenceError. Tests: crop maths in test_rig_shapes, test_paste_picture, golden scenario picture. |
| BMAP-8-HANDS-ON | [U] | Crop a picture with the handles and in Properties, turned too; Reset crop; copy a picture (screenshot) and Paste picture / Ctrl+Shift+V; save and reopen. |
| BMAP-9 | DONE (this commit) | Colour picker: Recent row (HardwareProfile.recentColours/noteColour, config global/internal/button-map-recent-colours, newest first, 10, all devices; noted when the picker closes after a change) and Pick from map (eyedropper: closes the picker, the next click in the window takes the colour there via HardwareProfile.colorAt, which grabs the window; right-click or Esc cancels; then reopens the picker on it). Tests: test_button_map_colours (recent rules; colorAt in its own process on a real window). |
| BMAP-9-HANDS-ON | [U] | Change colours a few times: Recent fills, newest first, shared between devices; Pick from map takes a photo or chip colour; Esc cancels. |
| BMAP-10 | DONE (this commit) | Export PDF/PNG/JPG saves the whole page whatever the zoom, without selection rings, handles, guides or the grid (editor `exporting` / `showChrome`), hidden items left out, at File → Export size 1×/2× (default)/3×: the editor is drawn that much larger (grabToImage target size), HardwareProfile.savePageImage crops the page and puts it on the window background; a PDF page keeps the 1× size in points. Tests: test_button_map_export (crop, background, JPG, PDF page size, bad rect); golden scenario `export` (3200×1800 page, no marks, hidden chip absent, editor restored). |
| BMAP-10-HANDS-ON | [U] | Zoom in, select a chip, turn the grid on, hide something; Export PNG at 2× and PDF at 3×: whole page, sharp, no marks, hidden item missing; the editor looks the same afterwards. |
| BMAP-HELP | DONE (this commit) | Button Map help is the User Guide's own "Button Map" section (19 topics: overview, File menu and export, view and grid, photo, chips, hotspots and leaders, groups and 5-way, right-click menu, shapes, lines and arrows, rotate/flip/resize, text boxes, tables, pictures, Layers, Properties, align, colours, keys) in the main guide window. Button Map Help → Button Map guide and F1 open it at that section (heading at the top of the contents); Help → User Guide opens the guide. The old in-window help popup is gone. Tests: test_help_guide (section exists, menu and F1 use it, 40+ feature names covered, menu paths real). |
| BMAP-HELP-HANDS-ON | [U] | In Button Map press F1 and use Help → Button Map guide: the User Guide opens at Button Map, same look as Help → User Guide in the main window; click through the topics. |
| BMAP2-0 | DONE (this commit) | Editor options: Configuration section `button-map` (gremlin/ui/button_map_options.py, registered before purge_unused), shown in Options as "Button Map" (groups in a fixed order) and opened from Button Map Edit → Editor options… (DialogOptions.showSection). First options: Undo steps (editor histCap), Rotate snap (Shift steps for the rotate handle, line drawing and the menu's ± steps), Export size (also File → Export size), Recent colours. Tests: test_button_map_options. |
| BMAP2-0-HANDS-ON | [U] | Edit → Editor options… opens Options on Button Map; change Rotate snap to 45 and turn a shape with Shift; set Export size 3x and see File → Export size follow; Options from the main window shows the same section. |
| BMAP2-1 | DONE (this commit) | Autosave and recovery: while editing with unsaved changes, a timer (Options → Button Map → Autosave, Autosave seconds, default on / 60 s) writes {image, photo, nodes} to modules/recovery/<slug>.json (HardwareProfile.saveRecovery/loadRecovery/clearRecovery; never the module file). Save and Discard remove it; undoing everything removes it at the next tick. Opening a device with a copy that differs from the saved layout asks Restore (enters editing with it), Discard, or Not now. Tests: test_button_map_recovery. |
| BMAP2-1-HANDS-ON | [U] | Set Autosave seconds to 10, edit a map, wait, end Gremlin from Task Manager; restart and open the device: the prompt offers the edits; Restore shows them in edit mode; Save keeps them. Discard instead removes them. |
| BMAP2-2 | DONE (this commit) | Press to find (qml/rig_find.js): while editing, the rising edge of a button or hat press (axis past 60%, released below 30%, only with Find axes) selects its chip, or its group, and pans it into view without zooming (VkbRigFace.showEditorRect); a control without a chip sets the pool filter to its name; a hidden one says so. Options → Button Map → Editing: Press to find (on), Find axes (off). Golden scenario `find` with a stand-in device. |
| BMAP2-2-HANDS-ON | [U] | Edit Mapping, press a few buttons and a hat on the stick: each selects its chip, scrolling when zoomed in; press one that is still in the pool: the pool filters to it. Turn Press to find off: presses only light chips. |
| BMAP2-3 | DONE (this commit) | Action labels: gremlin/ui/button_map_labels.py turns each input's actions in a mode (with parent-mode inheritance; an item without actions inherits) into short text (Description, keys, vJoy/Xbox output, Change Mode target, TTS text, fixed words; containers give their children's text, curves none); HardwareProfile.actionLabels/profileModes, profileLabelsChanged on profile or mode changes. Chips show Name / Action / Name and action (editor chipText; RigChipItem, RigMiniChip). View → Chip text, View → Labels mode (Follow the program = running mode while active, else the main window's mode). Options → Labels: Chip text, Description first, Several actions (First/All), Unbound (Name/Blank/Dash). Tests: test_button_map_labels; golden `labels`. |
| BMAP2-3-HANDS-ON | [U] | With a real profile: View → Chip text → Action; buttons with Map to Keyboard, Description, Map to vJoy, Change Mode show those; switch Labels mode to a child mode; edit an action in the main window and see the chip follow; run the profile and change mode: Follow the program follows. |
| BMAP2-4 | DONE (this commit) | Export modes: File → Export modes… picks modes (all ticked), PDF / PNG / JPG; for each mode the editor shows that mode's action labels (Action if chips show names) and its name at the top (editor exportTitle, Options → Export → Mode title), the page is grabbed at the export size and kept (HardwareProfile.beginExportPages/addExportPage/finishExportPages), then written as one PDF with a page per mode (util.save_images_as_pdf) or one image per mode ("<name> - <mode>.png"). Tests: test_button_map_export (pages, names, slots); golden `labels` step export-page-title. |
| BMAP2-4-HANDS-ON | [U] | With a profile of two or more modes: File → Export modes…, PDF: one page per mode, chips show that mode's actions, mode name at the top; PNG: one file per mode. Chips go back to how they were afterwards. |
| BMAP2-5 | DONE (this commit) | Mirror layout (qml/rig_mirror.js): every top-level box mirrored across the page via moveNodeBy (around-shapes and table-packed items follow their owners; locked items too), hotspots, spines and free leader ends mirrored once each (a chip's first leader shares them), pins left/right swapped, shapes flipH toggled and turned the other way, lines' ends mirrored, text/tables/group insides kept, pictures flipped only with Options → Editing → Mirror pictures. Edit → Mirror layout; File → Copy layout from → device (HardwareProfile.savedLayouts/layoutNodes) asks, optionally mirrors, enters editing; Undo restores. Tests: test_button_map_copy_layout; golden `mirror` (mirror twice = start). |
| BMAP2-5-HANDS-ON | [U] | Open the EVO L, File → Copy layout from → EVO R with Mirror ticked: chips land on the mirrored side with leaders to mirrored hotspots; adjust to the L photo; Save. Edit → Mirror layout twice returns the map. |
| BMAP2-6 | DONE (this commit) | Layout templates: modules/templates/<name>.json {kind button-map-template, name, device, savedAt, nodes} (HardwareProfile templates/templateExists/saveTemplate/templateNodes/renameTemplate/deleteTemplate/exportTemplate/importTemplate; imports number a taken name). File → Templates: Save layout as template… (name; asks before replacing), Apply template (the Copy dialog, not mirrored by default), Manage templates… (rename, export, delete, import). New window smoke test (test_button_map_window: loads the real window off-screen and opens the new dialogs; any QML warning fails). Tests: test_button_map_templates. |
| BMAP2-6-HANDS-ON | [U] | Save a layout as a template; open another device, apply it; Manage: rename, export to a file, delete, import the file back. |
| BMAP2-7 | DONE (this commit) | Rotation: text boxes are rotatable (handle, Rotate section, Properties angle; the typing field turns with the box). Several items (qml/rig_grouprot.js): with 2+ selected, a dashed frame and one handle above it (per-item rotate handles hidden); dragging turns them about the average of their middles (turn-invariant, so there and back is exact): rotatable drawings turn, lines' ends rotate, chips/groups/tables move upright, hotspots stay, locked and following items skipped; moves are unclamped. Multi menu → Turn together (−/+ snap step, ±90°, 180°). Golden `turn`; goldens for session_r/api_sweep/align updated (new menu sections, frame). |
| BMAP2-7-HANDS-ON | [U] | Select a shape, a line and two chips; drag the frame's handle: they swing round together, the angle shows; Shift snaps; Turn together +90 then −90 returns them. Turn a text box with its handle and type in it. |
| BMAP2-8 | DONE (this commit) | Callouts (qml/rig_callout.js): text boxes with tail {fx, fy} or {to: chipId} (tip on the chip box's edge nearest the callout, following it); box + pointer painted as one outline (rig_shapes.calloutOutline, tested) in a Canvas that reaches past the box, honouring theme/colours/opacity and rotation; tip handle (filled when attached), drag = draw-tail, drop on a chip attaches. Draw → Box → Callout; chip menu Add callout; text box Pointer section (Detach from chip, Remove pointer / Add pointer). Mirror and Turn together carry free tips. Golden `callout`; test_rig_shapes callout tests. |
| BMAP2-8-HANDS-ON | [U] | Draw a callout, drag its tip onto a chip, move the chip: the pointer follows; Add callout from a chip menu; turn a callout; export: callouts print without handles. |
| BMAP2-9 | DONE (this commit) | Paths (qml/rig_path.js): shape "path" with pts as box fractions, closed, smooth, heads, fill when closed; Path tool (click points, close on the first, Enter / double-click / right-click finish, Shift angle steps, stays on), Freehand tool (press-drag, simplified by rig_shapes.simplifyPath 1.5 px, smooth); point handles (draw-ptN) re-fit the box and bake turn/flips into the points; hit = near the path or inside when closed and filled; menu Path (Closed, Smooth), Line, Arrowheads or Fill; a wider stroke re-fits. Pure maths tested (simplifyPath, pathBox, distToPath, insidePolygon); golden `paths`. |
| BMAP2-9-HANDS-ON | [U] | Draw an open path, finish with double-click; draw a closed one and fill it; freehand a curve; drag points; turn and flip a path; give an open path arrowheads. |
| BMAP2-10 | DONE (this commit) | Saved styles (qml/rig_styles.js; gremlin/ui/button_map_options.py styles/save_style/rename_style/delete_style in button-map/internal/styles; ButtonMapOptions.styles/saveStyle/renameStyle/deleteStyle): kinds chip (chip, pressed, hotspot, leader fields), shape, line (lines and paths, re-fitted), text (textFormatKeys). Right-click → Saved styles: Save this style… (name dialog in the window), Apply <name> for that kind (all selected of the kind, one undo step). Options → Button Map → Library (OptionButtonMapLibrary.qml, a MetaConfigOption): rename and delete styles and templates. Tests: test_button_map_options (styles, library listed); window smoke opens the name dialog and the Library widget; golden `styles`. |
| BMAP2-10-HANDS-ON | [U] | Save a chip's style, apply it to other chips (and on another device); save a line style with arrowheads, apply to a path; Options → Button Map → Library: rename and delete a style and a template. |
| BMAP2-11 | DONE (this commit) | Photo look: Photo → Adjust photo → Look (Brightness, Contrast, Greyscale, Fade, Reset look). Editor photoBright/Contrast/Grey/Fade in the photo bag (written only when set; Python _photo_pose clamps and keeps them; undo snapshots restore them). Fade is the photo's opacity; the rest is an adjusted copy made by HardwareProfile.adjustedPhotoUrl (adjust_photo: QPainter greyscale blend, overlay / mid-grey contrast, white / black wash; cached in modules/cache, latest 12) — no shaders, since ShaderEffect/MultiEffect drew nothing off-screen. Tests: test_button_map_photo_look, test_photo_pose look; golden `photo_look`; smoke opens Adjust photo. |
| BMAP2-11-HANDS-ON | [U] | Adjust photo: greyscale and fade the photo, brighten it, raise and lower contrast; Save; reopen: the look is kept; Undo steps back; export shows the look. |
| BMAP2-12 | DONE (this commit) | Light page for printing: Options → Export → Light page (also File → Light page for printing). While exporting (both Export and Export modes) the editor's printLight routes every chip, mini-chip, group, leader, hotspot, shape, line, path, text box, table and callout colour through ink() = rig_shapes.invertLightness (HSL lightness turned over, hue/saturation/alpha kept; tested), the mode title is black, and the page is flattened on white. The photo is untouched; on screen nothing changes. Golden `light_page`. |
| BMAP2-12-HANDS-ON | [U] | Turn on File → Light page for printing, Export PDF and Export modes: white page, light chips with dark text, dark leaders, the photo as it is; print one. |
| BMAP2-13 | DONE (this commit) | Zoom: View → Zoom to fit page (Ctrl+1, VkbRigFace.zoomToPage) and Zoom to selection (Ctrl+2, editor zoomToSelection → face.fitEditorRect with a 25% margin, clamped to zoomMin..zoomMax); both persist the view. Options → View → Zoom speed (25–300%) scales the wheel factor in the face and the editor's pointer area. Golden `zoom`; smoke runs both. |
| BMAP2-13-HANDS-ON | [U] | Select a group, Ctrl+2: it fills the view; Ctrl+1: whole page; set Zoom speed 200%: the wheel zooms faster. |
| BMAP2-14 | DONE (this commit) | Rulers and guides: VkbRigFace Ruler canvases (top and left, percent ticks, guide marks; visible while editing with Options → View → Rulers / View → Rulers); dragging out of a ruler adds a guide (qml/rig_rulers.js: rulerGuidesX/Y page fractions), dragging a guide in the page moves it, dropping on its ruler or off the page removes it; guides drawn by RigGuides (Style.accent), saved per device in the ui bag, View → Show guides / Clear guides. Snapping: guides rank first in updateMoveGuides and join snapEnt's targets (also when Snap to entities is off). Note: properties declared after the root's Binding lines in VkbRigFace were dropped at runtime, so they sit with the other properties. Golden `rulers`. |
| BMAP2-14-HANDS-ON | [U] | View → Rulers; drag a guide down from the top ruler, move a chip and a shape to it (they snap); drag the guide back onto the ruler; reopen the device: guides kept; export: no guides. |
| BMAP2-15 | DONE (this commit) | Print: File → Print… (Ctrl+P) renders the page like Export (light page unless Options → Export → Print light is off) and calls HardwareProfile.printPage: crop, QPrintDialog, then print_image draws it as large as fits, centred, landscape when wider. QtPrintSupport added to the PyInstaller hidden imports. Also fixed: Export's light page was switched off before the grab (if without braces); the window smoke test now exports a light page through the real flow and checks the page is white. Tests: test_button_map_export (print_image in its own QApplication process). |
| BMAP2-15-HANDS-ON | [U] | File → Print…: the Windows print dialog opens; print to a printer and to Microsoft Print to PDF: the page fills the paper, landscape, light colours. Cancel prints nothing. In the installed build too (QtPrintSupport bundled). |
| BMAP3-1 | DONE (this commit) | Menus compact: compactMenu() on each menu's aboutToShow hides items that are not enabled (height 0, no gap) and separators with nothing visible on one side; the File menu sizes to the items showing; Edit Mapping and exports need a device; Photo menu greyed until editing; Copy layout from only with other layouts. Smoke test checks the File menu with and without a device. |
| BMAP3-2 | DONE (this commit) | Drag chips back onto the pool: while a chip or member drag is over the pool (window's poolHit), the pool lights with "Let go to take it off the map"; dropping calls returnToPool: selected chips and groups (or the dragged one), a whole group, or the dragged member in group edit; locked stay; one undo step. Golden `to_pool` (stand-in pool strip). |
| BMAP3-HANDS-ON | [U] | No device chosen: File shows devices and Close only; choose one: exports show; Edit Mapping: editing items appear. Drag a chip, a group, two selected chips onto the pool: the pool lights, they leave the map and show in the pool; Undo. |
| BMAP3-3 | DONE (this commit) | Right-click menu hover feedback: new Style token bgHover (dark #2F4B6B, light #8FA6C4; bgSelected was nearly the menu's own colour in dark) on the row under the pointer or keyboard, an accent bar on hovered rows, value buttons outlined in accent with a hand cursor; one row lights at a time (a real pointer move takes the keyboard's row; rows sliding under a still pointer do not). Goldens updated. |
| BMAP3-4 | DONE (this commit) | Button Map Guide: Help → Button Map guide and F1 open DialogButtonMapGuide.qml (DialogHelp guide="buttonmap", own window size) with only help_topics.buttonMapTopics(): five sections (Getting started, The map, Chips, Drawing, Panels), trimmed of other screens (no Device Pack, Tools, main window Options). The User Guide keeps one Tools → Button Map topic pointing to it; the Button Map's Help menu no longer has User Guide. test_help_guide checks both. |
| BMAP3-5-HANDS-ON | [U] | Dark theme: hover rows and value buttons in the right-click menu: clear highlight, one row at a time; arrow keys continue from the hovered row. F1 in the Button Map: the Button Map Guide with only its topics; Help → User Guide in the main window: one Button Map topic. |
