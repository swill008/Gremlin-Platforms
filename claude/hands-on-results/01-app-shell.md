# Hands-on results: 01 App shell + gap list items 1-2 (GL-111, GL-007)  (agent H1, 2026-10-07)

Page: `claude/final-test-plan/01-app-shell.md` (every row whose status or text
says "hands-on", the batch hands-on checks at its end) and
`claude/gap-list.md` "Hands-on checks needed" items 1 and 2. Spec:
`claude/program-map/01-app-shell.md`.

How the program was run: every probe started the real app
(`JoystickGremlinApp`, or the program's own `main()` for S3/S50) in its own
process, with a temp USERPROFILE under `.agent-logs/handson/H1/home/<run>`,
`GREMLIN_OFFLINE=1`, `test/fake_hardware.py` installed (no real joysticks),
HidHide start and the keyboard/mouse hooks switched off, and the real vJoy
device never opened (`output._open_vjoy` returns nothing), so Run did not
touch vJoy. Clicks and keys were sent in-process with QTest to the
program's own windows. On the real screen, the X was a `WM_CLOSE` to the
program's own window and the tray clicks and menu choices were the messages
Windows sends to the program's own tray window. The tray popup menu was not
shown: its items were recorded as they were built. Real-screen runs held
`.agent-logs/handson/screen.lock` (`lockrun.py`). Probe scripts, JSON results
and screenshots are in `.agent-logs/handson/H1/`. Console output is in
`.agent-logs/H1.log`.

Screen of this PC: 1920x1080 at 125 % Windows scaling (Qt sees 1536x864, dpr 1.25).

| Row | What was checked | How | Result | Evidence |
|---|---|---|---|---|
| S3 | Options > Interface > Ignore Windows display scaling on > Restart: the program comes back unscaled. Off > Restart: scaled again | real screen, temp profile, the program's own `main()`. The restart (`QProcess.startDetached`) was recorded but not started, because the new copy would run without the fakes. The next probe was started in the same profile with the environment the restart would pass | PASS | `r3_first.json`: started at dpr 1.25, Restart passes QT_ENABLE_HIGHDPI_SCALING unset (the launch value). `r3_second.json`: the next start reads the setting, env "0", dpr 1.0 (1920x1080, unscaled). Unticked and Restart again, `r3_third.json`: dpr 1.25 (scaled) |
| S10 | `--enable --start-minimized` with Minimize to tray on: no window, tray icon shows running | real screen, temp profile (R1's, Minimize to tray saved on) | PASS | `r2_minimized.json`: window Hidden, in the tray, Run on. The tray icon was added with the running picture (ADD icon = active handle). Tray menu: "Show Gremlin-Platforms / Stop Profile / Exit Gremlin-Platforms" |
| S11 | Update part: with a newer release and Check for updates on, one Update window and no second one | off-screen, closest program check (offline): `updater.offerUpdate` emitted twice | PERSON | `a6.json`: one "Check for Updates" window after both offers; `a6_s11_update_window.png`. test_startup_messages::test_told_once_then_again_only_when_it_changes PASSED. A real newer GitHub release is needed |
| S43 | Search "tray" (name), "slider" (description), "Diagnostics" (group): each shows its rows. "Other" matches nothing | off-screen, typed into the search box | PASS | `a1.json` S43: tray gives General > Startup and Tray (Minimize to tray, Check for updates, HidHide). slider gives Interface > Display (UI scale, Ignore Windows display scaling). Diagnostics gives General > Diagnostics (Diagnostic logs, Log When Not Responding). Other gives none. `a1_s43_search_*.png` |
| S44 | OSC > Connection Input host: edit + Tab saves. Edit + close the window without leaving the field saves | off-screen and real screen | FAIL | Tab saves (`a1.json` S44 after_tab_value). Enter saves too. Close without leaving the field does not save: typed 127.0.0.8 and the value stayed 127.0.0.7 (`a1.json`). On the real screen, typed 127.0.0.5, closed Options with its X, and the old value was kept (`r5.json`, `r5_s44_typed.png`) |
| S46 | Folders > Profiles folder > Select: picker opens in the current folder, titled by what it does. Reset puts the default back | off-screen (Qt picker) and real screen (native Windows picker) | PASS | `a1.json` S46_C1: "Choose Profiles Folder" at .../Gremlin Platforms/profiles (`a1_s46_window0.png`). Reset turned ...\elsewhere back into ...\Gremlin Platforms\profiles (`a1_s46_after_reset.png`). Native: "Choose Logs Folder" opened at the logs folder and was closed again (`r4b_s46.json`, `r4_s46_native_picker.png`) |
| S47 | Options' History button opens History filtered to settings | off-screen, clicked | PASS | `a1.json` S47 filter {"area":"settings"}. `a1_s47_history.png` shows Show: Settings with only settings entries |
| S48 | Resize Options, close, reopen: same size. Never larger than the screen | off-screen 1920x1080 | PASS | `a1.json` S48: 1111x677 reopened as 1111x677. 5000x4000 reopened as 1920x1080 (the screen) |
| S50 | Ignore Windows scaling asks Restart / Later / Cancel. Cancel: back off, nothing kept. Later: kept, no restart. Restart: the usual quit, then it starts again | off-screen (Cancel, Later), real screen through `main()` (Restart) | PASS | `a1.json` S50: box "Restart Required" with Restart/Later/Cancel (`a1_s50_ask.png`). Cancel: unticked, value false, no restart. Later: ticked, value true, no restart, Options still open. Restart: `r3_first.json` exec returned through the normal quit, restart issued (`r3_first_ask.png`) |
| S51 | Drag the UI scale slider: the program resizes on release only | off-screen, start with Ignore Windows scaling on and UI scale 150, mouse press/drag/release | PASS | `a5.json` S51: while dragging, slider 110 but program still 150. After release, program 110 and saved 110. `a5_s51_dragging.png`, `a5_s51_after.png` |
| S52 | vJoy Viewer and Options open, flip Dark mode: all three windows change at once | off-screen, Options switch clicked | PASS | `a1.json` S52: main, viewer and Options all #000000 to #aaaaad after one 0.3 s pump, and back. `a1_s52_*_after.png` |
| S57 | Save as flight.xml: title "flight.xml - Gremlin-Platforms R1" | off-screen, the save path the Save As window calls | PASS | `a2.json` S57. `a2_s57_title_saved.png` |
| S59 | Run: the button reads Stop in the accent color. Again: Run | off-screen, toolbar button clicked | PASS | `a2.json` S59_S61. `a2_s59_running.png` (Stop in blue, Status: Running) |
| S61 | Logical Device: its button accent, Home's not | off-screen, clicked | PASS | `a2.json` after_logical home_accent false, logical_accent true. `a2_s61_logical.png` |
| S63 | New, Load, Save As: the Mode box always shows a mode | off-screen | PASS | `a2.json` S63: "Default" (index 0) after each. `a2_s63_mode.png` |
| S64 | Save, hover the save line: tooltip shows the full text | off-screen, mouse moved over the line | PASS | `a2.json` S64 tooltip text = full "Saved the profile to …\flight.xml". `a2_s64_tooltip.png` |
| S68 | Ctrl+K, "data fold", Down, Enter: the data folder opens | off-screen, keys. Explorer was replaced by a recorder (`QDesktopServices.openUrl`) | PASS | `a2.json` S68: opened file:///…/home/a2/Gremlin Platforms and the palette closed. `a2_s68_palette_down.png` (only "Open Data Folder" listed) |
| S71 | With an open Keyboard draft, Load Profile…: the draft asks first, then the profile. Same for New and Recent | off-screen. The draft's "changed" and the profile's unsaved flag were faked. Load used the Open window, then its accept | FAIL | `a3.json` S71: Load gives draft then profile (correct, `a3_s71_first.png`, `a3_s71_second.png`). Recent gives the draft first (correct). New asks the profile question first (`new_first_question` = "There are unsaved changes in the current profile…") |
| S72 | New, Ctrl+S: Save As opens in the profiles folder. A save with an unfinished action: "Unfinished Actions" asks first | off-screen, Ctrl+S. The unfinished list was faked (`backend.unfinishedActions`) | PASS | `a3.json` S72: "Save Profile As" open at …/Gremlin Platforms/profiles (`a3_s72_save_as.png`). Ctrl+S then asks "Unfinished Actions … Save without them / Cancel" (`a3_s72_unfinished.png`) |
| S75 | Unsaved Calibration + panel edit + unsaved Button Map, File > Exit: Calibration asks and the quit stops. Exit again: panel, profile, Button Map in that order | off-screen. Calibration's unsaved flag, the Keyboard draft, the profile flag and the Button Map's edit base were faked | PASS | `a3.json` S75: step 1 Calibration "Calibration is not saved…" and no quit (`a3_s75_step1_calibration.png`). Step 2 order: action editor, then profile, then Button Map "Editor changes are not saved…", then the program quit |
| S77 | Unsaved new profile, Exit > Save > close the Save As: the program stays. Ctrl+Shift+S, Save: no quit afterwards | off-screen | PASS | `a3.json` S77: after closing, quits 0, window shown, follow-up cleared. Ctrl+Shift+S opened Save As clean (afterSave null, not quitting), saved, quits 0 |
| S79 / B1 | Move/resize, X (hides to tray), Exit, start: same place | real screen | PASS | `r1_tray.json` place_saved [131,115,1500,950] at the X. Next start: `r2_place.json` geometry [131,115,1500,950] |
| S85 / Q2 / GL-111 | Minimize to tray on: File > Exit and tray Exit both end the program | real screen | PASS | `r1_file.json` exit: File > Exit, app.exec() returned (quit). `r1_tray.json` exit: tray Exit while hidden in the tray, quit within 0.8 s |
| GL-007 | Tray: minimize hides, X hides, one-time balloon, tray Exit, tray label and icon after Run/Stop | real screen | PASS | `r1_file.json`/`r1_tray.json`: Minimize hides (pages unloaded, trayed true). Left click brings it back. X hides with balloon "Gremlin-Platforms is still running" once (`r1_file_corner_balloon.png`), not on the second X, nor after a restart (`r2_place.json`). Menu: Show/Hide follows the window, "Run Profile" turns into "Stop Profile". Icon handle goes idle to active on tray Run and back on Stop, also while hidden. Tray Exit shows the window first, then quits (S89). Toolbar shows Stop while running |
| B1 | X with the vJoy Viewer open (Minimize to tray off) quits | real screen | PASS | `r1_x_off.json`: viewer open, WM_CLOSE, app.exec() returned |
| B1 | Tray Run with an edited action pane asks first | real screen, tray menu Run while hidden. The Keyboard draft's "changed" was faked | PASS | `r4_out.txt` B1_tray_run: window came forward and asked "Save or discard the open action first?" (`r4_b1_tray_run_asks.png`). Discard ran. Tray Stop asked nothing. Also off-screen through `toggleRun`: `a3.json` B1_run_with_edited_pane |
| C1 | Options > Folders pickers titled by what they do | off-screen and real screen | PASS | `a1.json` picker_titles: "Choose Data/Profiles/Modules/Scripts/Export/Logs/History/Deleted Devices/Plugins Folder". Native "Choose Logs Folder" (`r4_s46_native_picker.png`) |
| C2 | Auto-load on picks up the program in front | off-screen app, real foreground window (read only, nothing was clicked). Entry = the program in front at the time (the Claude desktop app) | PASS | `a4.json` C2: switching "Load profiles automatically" on loaded front.xml and ran it at once |
| S103 | Diagnostic logs at Warning, Run and Stop three times: no new lines in system.log | off-screen | PASS | `a2.json` S103: no new lines. A control Warning written afterwards did appear, so the check could see lines |
| S105 | Config tab: Clear Log asks first. Copy All: the same lines | off-screen, in-process clipboard (the user's clipboard was not touched) | PASS | `a4.json` S105: clipboard = logs.txt = the view (15 lines). Clear Log asks "Clear Log?" Clear/Cancel, and Cancel keeps the file (`a4_s105_clear_asks.png`). The button reads "Copy All Logs" |
| S110 | Diagnostic logs ALL: red frame on every window. DEBUG opens the Live Log Reader | off-screen | PASS | `a2.json` S110: frame on main, Options and vJoy Viewer (`a2_s110_vJoyViewer.png`). DEBUG click opened "Live Log Reader". Back at Warning, no frames |
| S117 | Installed copy one version behind: Update Now, unsaved question, installs, new version starts | none possible (network, installer) | PERSON | test_update_model.py (4 tests) PASSED in this session |
| S119 | Start Update Now, close the window mid-download: no `.part` left | none possible (network) | PERSON | test_final_01::test_s119_cancelling_a_download_deletes_the_partial_file PASSED |
| S123 | From a console, Check for Updates, wait a minute: no QSslSocket message | none possible (network) | PERSON | test_final_01::test_s123_an_update_check_closes_its_connection_with_the_reply PASSED |
| S125 | Change the Plugins folder, add a plugin there: it appears only after a restart | off-screen, two starts in one temp profile, a minimal plugin written by the probe | PASS | `a4.json` S125_run1: not loaded, and the row says "Takes effect on the next start." `a5.json` S125_run2: loaded |
| S131 | Escape in the vJoy Viewer and Calibration: they stay open (Help, About close) | off-screen, Escape key on each window | PASS | `a2.json` S131: viewer and Calibration open after Escape. User Guide and About closed |

Counts (36 rows): PASS 30, FAIL 2, BLOCKED 0, PERSON 4.

## Failures

**S44 (spec 01 S44, test-plan S44 hands-on).** Text fields should save on
leaving the field, on Enter, or when the window closes. The OSC Input host
field saves on Tab and Enter. If you type a new host and close Options while
the cursor is still in the field, the edit is lost. This happened off-screen
(`a1.json`) and on the real screen with the X (`r5.json`). Likely cause:
`qml/OptionOscInputHost.qml:36-46` saves only on `onAccepted` and on
`contentItem.editingFinished`, and there is no save when the window closes.
The ordinary text rows do have one, `Component.onDestruction: commit()` in
`qml/ConfigGroup.qml:300`. The Port field (`OptionOscInputHost.qml:~66-74`)
has the same shape, and `OptionOscOutputHost.qml` is probably the same.
Suggested fix: save `editText` (and the port text) when the item is
destroyed or the window closes, if they differ from the model. The map
lists OSC as parked, but the test plan uses this row for S44.

**S71 (spec 01 S71, test-plan F-02b).** New, Load and Recent should first
close panels with unsaved display edits (asking), then ask Save / Discard /
Cancel for the profile. Load and Recent do this. File > New asks the profile
question first and the Keyboard draft question second (`a3.json` S71
`new_first_question`). Cause: `qml/Main.qml:638-642`. `requestNewProfile()`
calls `guardUnsavedChanges(...)` and only then `leaveDisplayThen(...)`.
`loadRecent` (`Main.qml:741-751`) and the Load dialog (`Main.qml:1082-1088`)
use the other order. The map's entry-point table (01 section 4, and 04
section 4 line 73) records the code's order, but section 8 S71 is the spec.
Suggested fix: `leaveDisplayThen(function() {
guardUnsavedChanges(function() { backend.newProfile() }, false) })`.

## Blocked

None. The screen lock was busy once (H7). The first S3 attempt waited and
the hang tool stopped it. After that, real-screen probes waited for the lock
in `lockrun.py`, outside the hang tool.

## Needs a person

- **S11 (update part):** with a newer release on GitHub and Check for
  updates on, start the program once. Look for exactly one Update window and
  no second one. The program-driven check of "one window for two offers"
  passed.
- **S117:** use an installed copy one version behind. Choose Update Now,
  answer the unsaved-changes question, and let it install. Check that the
  new version starts by itself.
- **S119:** start Update Now and close the Update window during the
  download. Check that no `.part` file is left in `<data folder>\updates`.
- **S123:** run from a console, choose Help > Check for Updates and wait a
  minute. Check that no QSslSocket message appears.
- **GL-007 (look only):** the tray icon picture. The probe saw the program
  switch the icon between the idle and running pictures (Shell_NotifyIcon
  calls with the two icon handles), but the taskbar was not in its screen
  grab. Glance at the tray icon while running and while stopped.
- **S68:** with a real Explorer, check that the window opens on the data
  folder. The probe recorded the URL instead of starting Explorer.

## Notes (not failures)

- The S3/S50 restart command in the probe pointed at the probe's folder,
  because `install_path` is worked out from `sys.argv[0]` at import and the
  probe was the script. In a real start that is `joystick_gremlin.py`, so
  this is not a program fault.
- Off-screen, Qt's own Save As window did not add the default `.xml` suffix
  (the files were saved as `s72` and `s77`). The native Windows dialog adds
  it. This affects off-screen runs only.
- Spec S105 says "Copy All". The button reads "Copy All Logs".
