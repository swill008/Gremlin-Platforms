# Hands-on results: 08 History / Device Pack / Auto Mapper, 09 OSC / sound / tray / look / help, gap list items 9, 10, 13  (agent H7, 2026-10-07)

Everything ran in a temp USERPROFILE under `.agent-logs/handson/H7/home/<probe>`,
with `GREMLIN_OFFLINE=1`, the fake joystick driver (`test/fake_hardware.py`),
the fake vJoy (`test/journeys/_harness.py` FakeVJoy) and key output kept in the
process (`test/fake_input.py`). Probes: `.agent-logs/handson/H7/probe_*.py`, run by
`.agent-logs/handson/H7/run.py` (bounded, 170 s; hang tool on); RESULT json next to
each probe (`probe_*.json`). Off-screen unless "real screen" is said. The one
real-screen probe (`probe_tray.py`) ran under the screen lock with HidHide, the
keyboard/mouse hooks and "close the other copy" switched off in-process, no
balloon shown (recorded instead); tray clicks and tray menu commands are the
icon's own callbacks, the X is a WM_CLOSE posted to the program's own window.
Every screenshot named below was looked at.

Unit tests run as the closest checks (all pass): `test_batch2_B5b`, `test_batch1_run_callers`,
`test_tray_memory`, `test_stage1_app_profile`, `test_batch2_B1`, `test_final_09`,
`test_spec_hidden_imports`, `test_help_guide` (127 passed, 1 xfailed);
`test_history_window`, `test_device_pack_window`, `test_final_08`, `test_batch2_b7`,
`test_usability_fixes` (64 passed). Log: `.agent-logs/H7.log`.

| Row | What was checked | How (off-screen / real screen / fake hardware) | Result | Evidence |
|---|---|---|---|---|
| 08 S35 | Tools > History open; Options opened in front (History not active); a setting changed (Days to keep changes 90 -> 45); History brought back to the front: the new "Changed Days to keep changes" is at the top without Refresh (9 rows while in the back, 11 after coming to the front) | off-screen, real window and its activation | PASS | `.agent-logs/handson/H7/s35-after-front.png`; probe_history.json `s35-*` |
| 08 S36 | Search "zzzz": 0 rows and "No saved changes to show."; Search cleared, nothing picked: "Pick a change to see it before and after." | off-screen | PASS | `s36-search-zzzz.png`, `s36-pick-nothing.png` |
| 08 S38 | Restore Before on "Saved pJoy Pro: checked controls and names": "Restore?" asks ("Put back the version before this change? Saved at once, with its pictures."); Cancel: file byte-for-byte the same, no message; Restore: file back to buttons [1], "Put back pjoy_pro.json." under the change | off-screen, the dialog's own buttons | PASS | `s38-restore-asks.png`, `s38-restore-done.png`; probe_history.json `s38-*` |
| 08 S48 | "Created the module file of History New" picked: Restore Before greyed out, Restore After on | off-screen | PASS | `s48-created-entry.png` |
| 08 S50 | Device Pack with a connected stick that has no module file listed first ("Aardvark Stick"): the Export tab opens on "pJoy Pro", the first with a module file | off-screen, fake sticks | PASS (see note O2) | `s50-export-opens.png`; gl196-4032x3024.json `s50-*` |
| 08 S58 | Export a pack (the save dialog's answer), Show Folder appears; clicking it opens the folder that holds the new zip (the call to Windows was recorded, not opened) | off-screen | PASS | `s58-after-export.png`; `s58-opened-is-zip-folder: true` |
| 08 S62 | A pjoy_pro pack opened: "Put this pack on" suggests pJoy Pro; "Second Stick" typed in the text box; the warning names Second Stick; Import writes second_stick.json and leaves pjoy_pro.json unchanged | off-screen | PASS | `s62-warning-typed-device.png`, `s62-after-import.png` |
| 08 S81 | Import (Undo Import offered), close Device Pack, reopen: no Undo Import (button hidden, `canUndoPackImport` false) | off-screen | PASS | `s81-reopened-import-tab.png` |
| 08 S82 / Q6 | Import, then Choose Zip... another pack: Undo Import gone | off-screen | PASS | `s82-after-choose-zip.png` |
| 08 S95 | Overwrite used inputs on, Create 1:1 Actions: "Replace Existing Actions" asks first (Cancel / Replace them) | off-screen | PASS | `s95-overwrite-asks.png` |
| 08 S97 | After Create 1:1 Actions (Overwrite off) the window says nothing about the actions being in memory only; only the Overwrite confirm says "Nothing is saved yet: to undo, load the profile again without saving." (behaviour itself holds: profile unsaved) | off-screen | FAIL (test-plan check) | `s97-after-create.png`; probe_automap.json `s97-*` |
| 08 S100 / Q4 | Profile running: Auto Mapper, Device Pack and Tools > History each show "The profile is running. Changes here take effect the next time it starts." | off-screen | PASS | `s100-automap-running.png`, `s100-pack-running.png`, `s100-history-running.png` |
| 08 S102 | Esc (QTest key on the window, window active): Auto Mapper and Device Pack stay open; History (control) closes | off-screen | PASS | probe_automap.json / probe_pack.json `s102-*` |
| 08 D-05-Q8 + B7 | With an unsaved action pane (Button 1 edited, not OK'd): History Restore of an input, Device Pack Import, Device Pack Undo Import and Auto Mapper Create 1:1 Actions all show "Unsaved Changes" (Cancel / Discard) first; Cancel keeps the pane and does nothing | off-screen | PASS | `q8-history-restore-asks-main.png`, `q8-pack-import-asks-main.png`, `q8-automap-asks-main.png` |
| 08 B7 / gap item 9 (GL-041) | Large history files made by the program's own recorders: 15 MB per area (45 MB, 16,367 entries) and 20 MB per area (60 MB, 21,801 entries). Main-thread stall (5 ms timer): open 0.31 s / 0.45 s; back to the front 12-372 ms; pick a whole-profile save 0.15-0.32 s; Restore ask 1 ms, Restore done 14-333 ms; Refresh 12 ms. No freeze | off-screen | PASS | `gl041-15mb.json`, `gl041-20mb.json`, `gl041-big-profile-picked.png`, `gl041-after-restore.png` |
| 08 B7 | Import a pack, save the module file again (as a Button Map save does), Undo Import: "Undo Import?" names second_stick.json and asks; Cancel keeps Undo offered | off-screen | PASS | `b7-undo-asks.png` |
| 08 B7 (UI scale) | Slider set to 150 % (Ignore Windows scaling on), History Restore Before of "Changed UI scale": Style.dp(100) 150 -> 100 at once, "Settings put back." | off-screen | PASS | probe_history.json `b7-ui/general/ui-scale-*` |
| 08 B7 (Diagnostic logs level) | Diagnostic logs set to Error through Options' own model (LogLevelModel.setLevel): no History entry is made, so it can never be restored | off-screen | FAIL | probe_history.json `entry-log-level: false`, `diag-log-*` (expose false) |
| 08 B6 / gap item 10 (GL-196) | Device Pack with a large photo. 4032 x 3024 (23 MB JPEG): open 0.27 s stall, each export-device change ~0.2 s, Export 0.7 s, opening the 22 MB pack 0.4 s. 8000 x 6000 (93 MB): each device change ~0.77 s, open 0.85 s, Export 2.7 s, opening the 87 MB pack 1.4 s. `peekPackDevice` itself 5 ms; the stall is the export page's Image decoding the photo on the UI thread | off-screen | PASS (no freeze; see note O3) | `gl196-4032x3024.json`, `gl196-8000x6000.json`, `gl196-export-big-photo.png` |
| 08 C5 (temp) | `%TEMP%\gremlin-pack-*` (TEMP pointed into the temp profile) exists while a pack is open, gone after Device Pack closes | off-screen | PASS | `c5-temp-while-open`, `c5-temp-after-close: []` |
| 08 C5 (damaged) | Export of a device whose module file is damaged: "...is damaged (...), so it can't be exported. Choose Start Fresh on the device's card first (the damaged file is kept)." Export greyed | off-screen, fake stick | PASS | `c5-damaged-export.png` |
| 08 C5 (sparse axes) | vJoy with axes X, Y, Slider 0 (ids 1, 2, 6, the output module's driver answers faked): stick axes go to vJoy axes 1, 2, 6 only; "Skipped vJoy 1 axes 3-5, 7-8: not on the vJoy device." | off-screen, fake driver answers | PASS | `s97-after-create.png`; probe_automap.json `c5-axis-pairs-stick-to-vjoy` |
| 09 S1-S48, Q1-Q10, Q18 | OSC | — | BLOCKED | OSC parked by the user |
| 09 S61 | Text to Speech on keyboard key F, Run, F pressed (hook callback): the speech engine is asked to say "key said" on the main thread | off-screen, engine replaced by a recorder | PERSON | probe_tts.json `running-said`; test_batch2_B5b passes |
| 09 Q12 | Saved voice "Removed Voice 123" (not installed): Options' voice model shows row 0 "(default)" | off-screen, Options' TTSVoiceSelectionModel | PASS | probe_misc.json `q12-*` |
| 09 R10 / G1 | Text to Speech under a Tempo (short press) on stick button 1: said on the main thread | off-screen, recorder, fake stick | PERSON | probe_tts.json `running-said` ["tempo said", true] |
| 09 GL-058 (B5b batch) | Options opened and closed while stopped, then F pressed: nothing said | off-screen, recorder | PERSON | probe_tts.json `stopped-said: []` |
| 09 S65 / S66 / S67 (TRAY-ONE, B1) | Minimize to tray on, Run, X: window hidden, profile still running, one "still running" balloon; tray left-click: back at the same place and size (261,185 1097x714); second X: no second balloon; minimize: hidden to the tray; File > Exit and tray Exit (from hidden) bring the window back with the save question, Discard, the program quits (exec returns 0 in ~3 s) | REAL SCREEN, temp profile, fake hardware | PASS | `tray-fileexit.json`, `tray-trayexit.json`, `tray-shown-again.png`, `tray-exit-save-question-trayexit.png` |
| 09 S69 (MEM-HANDS-ON) | Hidden to the tray while running: working set 323 MB -> 17 MB; a stick press while hidden still holds vJoy button 5 and lets go; shown again: 94 MB, Home back | REAL SCREEN, fake hardware | PASS | `tray-*.json` `mem-*`, `hidden-press-held: [5]`; test_tray_memory passes |
| 09 tray Run, edited pane (06 Q6, B1) | Button 1 edited in the pane, tray "Run Profile": "Unsaved Changes - Save or discard the open action first?" (Cancel / Discard / Save); Cancel: not running, pane keeps its change | REAL SCREEN | PASS | `tray-run-with-edited-pane.png` |
| 09 B1 (X with a tool window open quits) | Minimize to tray off: the X quits with a tool window open | off-screen (unit test) | PASS | test_batch2_B1.py::test_main_window_shell |
| 09 S74 (OPT-U01) | Options, Home, Input Module Setup and vJoy Viewer open; Dark mode off, Options closed: all three other windows #000000 -> #aaaaad at once; on again: all back to #000000 | off-screen 1600x1000 | PASS | `s74-light-*.png`, `s74-dark-*.png`; probe_misc.json `s74-*` |
| 09 S77 (MENU-1/2) | File menu, Home card right-click menu, Options dropdown and Ctrl+K palette: same row look, accent bar on the current row | off-screen | PASS (hover: person) | `s77-file-menu.png`, `s77-home-card-menu.png`, `s77-options-dropdown.png`, `s77-command-palette.png` |
| 09 S79 (W-12) | Dark and light: "Recent Profile Didn't Open" for a missing profile and the Error box (with details) are readable (title, text, buttons) | off-screen | PASS (native notification box: person) | `s79-dark-missing-profile.png`, `s79-light-missing-profile.png`, `s79-dark-error.png`, `s79-light-error.png` |
| 09 S81 (OPT-U06) | Ignore Windows scaling on: slider set to 150 and released (its own `_commit`): Style.dp(100) 100 -> 150, menu bar 32 -> 49 px, no restart. (Windows scaling on: slider disabled, S80) | off-screen | PASS | `s81-main-after-150.png`; misc-ignore-scaling.json, misc-default-scaling.json |
| 09 S82 (OPT-U02 / W-11) | Tick "Ignore Windows display scaling": "Restart Required" with Cancel / Later / Restart; Cancel: box and saved value unticked; Later: kept, no restart asked of the program. Restart itself: unit tests | off-screen + unit tests | PASS | `s82-restart-asks.png`; test_final_09 s82 tests, test_stage1_app_profile restart tests |
| 09 Q16 / gap item 13 (GL-200) | Keyboard page keys with Map to vJoy, Map to Keyboard, Macro, all three, Map to Xbox, Tempo, at 175 % (light and dark) and 100 % on 1600x1000. Colours are fine in both themes (black ink on grey, near-white on dark). Size is off: the images stay 21 px tall with 9-11 px text at 175 % while the row text is 26 px; the "4"/"12" over "BTN" crowd each other | off-screen | FAIL | `q16-keyboard-175-light.png`, `q16-keyboard-175-light-crop.png`, `q16-keyboard-175-dark-crop.png`, `q16-keyboard-100-light.png` |
| 09 S85 (BMAP3-5) | F1 on the main window opens "User Guide" (64 topics, one Button Map topic "Tools / Button Map"); F1 in the Button Map opens "Button Map Guide" with only its 27 topics | off-screen, QTest key on the program's windows | PASS | `s85-user-guide.png`, `s85-button-map-guide.png` |
| 09 S89 (B-04) | Built exe: `dist/gremlin_platforms` (built 2026-10-05, older than today's code) holds DialogHelp.qml, help_topics.js, DialogAbout.qml; hidden-imports and About-version tests pass | file check + unit tests | PERSON | test_spec_hidden_imports, test_help_guide |

Gap list item 14 (GL-308, OSC) skipped as asked (OSC parked).

Counts: PASS 31, FAIL 3, BLOCKED 1, PERSON 4 (39 rows).

## Failures (one paragraph each: row, spec ref, what happened, file:line of the likely cause, suggested fix)

**08 S97 (test-plan check "the dialog says so under Create 1:1 Actions").** With Overwrite used inputs off, Create 1:1 Actions makes the actions in memory (profile unsaved, as S97 says) but nothing in the window tells the user they are not saved or how to undo; the result line reads only "Made 67 actions; 2 inputs kept their actions. Skipped ...". The "Nothing is saved yet: to undo, load the profile again without saving." text exists only in the Overwrite confirm. Likely cause: `gremlin/auto_mapper.py:286-291` (`_create_mappings_report`) and `qml/DialogAutoMapper.qml:249` (start text). Suggested fix: add the sentence to the result line (or as a fixed line under the button). If the lead reads S97's "(dialog text)" as the Overwrite confirm only, this becomes a test-plan wording fix instead.

**08 B7 / S15 / S44 (History Restore of the Diagnostic logs level).** Changing Options > General > Diagnostics > Diagnostic logs (LogLevelModel, key `global/general/log-level`) makes no History entry at all, so the "restore of the log level applies at once" path can never be reached from the program; S15 says the settings the user chooses in Options are recorded. Cause: the key is registered with expose False at `joystick_gremlin.py:771-774`, and History records only exposed settings (`gremlin/config.py:260`, `_view_entry`); Options shows it through the "debug" row (`gremlin/ui/log_option.py:126-132`, `gremlin/ui/option.py:96`). `test_batch2_b7.py::test_restore_applies_logs_and_ui_scale_at_once` registers the key itself with expose, so it doesn't see this. Suggested fix: let History's settings view include `global/general/log-level` (an Options choice), and add a test through LogLevelModel.setLevel that expects a settings entry.

**09 Q16 / G6, gap list item 13 (GL-200).** At 175 % the action summary images on the Keyboard page (the only list that shows them, InputButton) stay at their 100 % size: 21 px tall, fonts 9 px (badge), 11 px (vJoy number), 15/19 px (glyphs), next to 26 px row text, so they are hard to read; the input number over "BTN" crowds. Colours are fine in both themes (no white-on-grey). Per D-09-Q16 ("fix with Style values only if visibly off") this is visibly off. Cause: fixed pixel sizes in `gremlin/ui/action_image_generator.py:58-75` (and `_glyph_height` 21), shown unscaled by `qml/InputButton.qml:213-226` (`fillMode: Image.Pad`, `height: sourceSize.height`). Suggested fix: scale the fonts and glyph height by `ui_scale_option.active_scale()` (include the scale in the image id so the cache and `themeRevision` refresh it), or pass the requested size from QML.

## Blocked (why)

- 09 S1-S48, Q1-Q10, Q18 (and gap list item 14, GL-308): OSC is parked by the user (D-STD-OSC); not tested.

## Needs a person (what exactly to do and what to look for)

- 09 S61: add Text to Speech ("hello") to a keyboard key, Run, press the key: you hear "hello". (Program check passed: the engine is asked to say it, on the main thread.)
- 09 R10 / G1: Text to Speech under a Tempo (short press) and inside a macro: press: you hear it. (Tempo checked by the program; macro not, the macro has no Text to Speech step in this check.)
- 09 GL-058: with the profile stopped, open and close Options, press a key that has Text to Speech or Play Sound: nothing is heard. (Program check passed for speech.)
- 09 S89 (B-04): build the exe again (the one in `dist/` is from 2026-10-05, older than today's code), start it, press F1 (User Guide opens with text), Help > About (version shows), switch Dark mode off and on (the windows change).
- 09 S79 (part): the Save notification uses a native Windows message box (`qml/Main.qml:907` MessageDialog); in both themes check its title, text and OK are readable (Windows draws it, not the program).
- 09 S77 (part): hover over rows of the File menu, a Home card's right-click menu, an Options dropdown and Ctrl+K: the hover look is the same in all four.
- 09 S65 (part): look that the tray icon itself changes between idle and running and that its tooltip reads "Gremlin-Platforms" (the program check used the icon's own callbacks, not the mouse).

## Other things seen (not rows of this page; for the lead to decide)

- O1 Auto Mapper ticks after Create (AM-05, spec 08 section 11 "only checked by hand"): after Create 1:1 Actions the input list still shows pJoy Pro ticked, but `selectedInputModules` is `{}`; a second Create without re-ticking makes nothing for it. Cause: `qml/DialogAutoMapper.qml:221-222` clears the maps while the check boxes' `checked` falls back to `initialSlug` (94-96) and `onCheckedChanged` doesn't fire. Evidence: probe_automap.json `obs-*`.
- O2 S50 with a damaged module file: Device Pack opens on a device whose module file is damaged (it counts as "has a file"), where Export is refused; the first device with a usable file would be friendlier (`qml/DialogDevicePack.qml:84-95`, `hasFile`). Evidence: a run with "Broken Stick" (`c5-damaged-export.png`, `s50-opens-on: Broken Stick`).
- O3 GL-196 remainder: the export page's photo `Image` (`qml/DialogDevicePack.qml:553-559`, also the import photo at 692) loads synchronously at full size; `asynchronous: true` and a `sourceSize` would remove the 0.2 s (12 MP) to 0.8 s (48 MP) hitch per device change. Export (2.7 s for an 87 MB pack) and opening a big pack (1.4 s) also run on the UI thread.
- O4 A settings History entry "Changed Actions offered" (action priorities `[]` -> the full list) appears early in a fresh profile with no user change (08 S16 says a setting appearing is no change). The probe harness also turns OSC off at start, which fell into the same entry, so this needs a clean confirmation. Evidence: probe_options_entry.json.
- O5 At 150 % the History window's "Before" heading touches the "Restore Before" button (`s48-created-entry.png`); cosmetic.
- O6 During the real-screen run the vJoy 1 card read "In use by another program" (another agent's integration run may hold the real vJoy; this probe used the fake vJoy only).
