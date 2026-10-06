# Gap list (Stage 0)

Built 2026-10-06 from the nine approved subsystem pages in `claude/program-map/`.

**What this is.** Every place where the code differs from the approved spec in `claude/program-map/`, or where nothing owns something. It replaces open-ended audits. Items from different pages that describe the same problem are merged into one entry; the original item ids (page number + id, e.g. `06-G1`), spec refs and tracker refs are all kept.

**How it is used.**
- Work goes in the order of the sections below, which follows "The plan" in `claude/system-maps.md` (Stage 1 safety net, then the three redesigns, then the rest).
- Every item is fixed starting as a failing test (or, where only a real screen or PC can show it, a hands-on check; see the list at the end).
- Change control is in `.claude/CLAUDE.md` and `claude/system-maps.md`: a fix that would change the spec (a statement or a decision) goes to the user first, and the spec is updated with their answer before coding.
- When an item is done, mark it here with the commit and the test that guards it.

**Words used.** Severity: data-loss, crash-or-hang, safety, wrong-behaviour, ux, text, cleanup. Status: confirmed-in-code (seen in the code), suspected (likely, not proven), needs-hands-on (only a real screen or PC can show it). A merged entry takes the highest severity and the strongest status of its parts.

**Totals.** 366 source items from 9 pages, merged into 309 entries (GL-001 to GL-309); GL-310 and GL-311 added by Stage 1.

| Severity | Entries |
|---|---|
| data-loss | 17 |
| crash-or-hang | 14 |
| safety | 4 |
| wrong-behaviour | 100 |
| ux | 45 |
| text | 40 |
| cleanup | 89 |

| Status | Entries |
|---|---|
| confirmed-in-code | 251 |
| suspected | 44 |
| needs-hands-on | 14 |

| Section | Entries |
|---|---|
| 1. Stage 1 safety net | 25 |
| 2. Urgent standalone fixes | 20 |
| 3. Redesign 1: Run lifecycle | 21 |
| 4. Redesign 2: module files | 29 |
| 5. Redesign 3: actions | 14 |
| 6. Wrong-behaviour and UX | 92 |
| 7. Text, glossary and help | 32 |
| 8. Cleanup | 47 |
| 9. Parked (OSC) | 29 |

## 1. Stage 1 safety net (tests and what journey tests need first)

**Done 2026-10-06 (Stage 1 commit), except GL-016 (the user's hands-on checks).** GL-001, GL-002 and GL-003 are fixed; GL-004 to GL-025 now have tests (behaviour the spec agrees with is locked in; known gaps are strict xfails named by their GL id, so each fails the suite once fixed until its mark is removed). Plus: CI on every push, random test order, the lint baseline, `gremlin/validate.py` rule checks (report-only), journey tests in `test/journeys/`, `claude/decisions.md`.

Do these before any redesign. GL-002 comes before GL-001. GL-003 is here because CI and journey tests run on a PC without vJoy.

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-001 (01-T1, 05-T2, 06-T4, 07-T1) | About 20 tests wait a fixed short time and fail on a busy PC | cleanup | confirmed-in-code | 01 S94, 01 S113; program thread rules; 06 section 10; 07 section 11; AU-119 | test/test_watchdog.py; test/action_interaction/test_tempo.py, test_double_tap.py, test_macro.py; test/unit/button_map_*_smoke.py | Wait on conditions (bounded) or step time through gremlin.clock instead of fixed sleeps. |
| GL-002 (01-G6, 03-G23) | gremlin.clock has no monotonic time, so watchdog, config and output read time directly | cleanup | confirmed-in-code | 01 S94; 03 7.15; program thread rules | gremlin/watchdog.py:54,68,83,89; gremlin/config.py:175,503; joystick_gremlin.py:525; gremlin/modules/output.py:48,71,151,158; gremlin/ui/module_model.py:1500; gremlin/ui/device.py:1242 | Add a monotonic time to gremlin.clock and use it in these files (the pre-Qt sleep may stay if justified). Needed by GL-001. |
| GL-003 (05-G4) | Profiles with Map to vJoy won't open on a PC without vJoy | data-loss | needs-hands-on | 05 S1, 05 S104, 05 S9, 05 Q2 | gremlin/plugin_manager.py:203; action_plugins/map_to_vjoy/__init__.py:361 | Always register every built-in plugin; can_create() only decides whether Add Action offers it. Check by hand on a PC/VM without vJoy first. |
| GL-004 (06-T1) | No tests for a failed Run, Stop order, or Run leftovers | cleanup | confirmed-in-code | 06 section 11, 06 S18, S26, S30, S31, S85; AU-116, AU-117 | test/unit/test_audit3_run_stop.py; test/unit/test_action_fixes.py | Failing tests: failed start then Run again; CodeRunner start-to-stop order; timers after Stop; vJoy loop across Stop/Run; script keys; Logical values; release callbacks surviving Stop. These lock in Redesign 1. |
| GL-005 (06-T2) | Untested: axis/hat virtual buttons, release after mode change, Initial Values | cleanup | confirmed-in-code | 06 S8, S38, S39, S40 | gremlin/code_runner.py (VirtualAxisButton, VirtualHatButton, _refresh_axes); gremlin/event_helpers.py | Unit tests for inside range at Run, jump across range, mode-changed release, Initial Values. |
| GL-006 (06-T3) | Untested: Xbox unplug at Stop, sound/speech modes, Paused status, tray label, device change | cleanup | confirmed-in-code | 06 S2, S3, S29, S42, S45, S57, S73, S76 | gremlin/modules/output.py reset_drivers; gremlin/tts.py; gremlin/audio_player.py; gremlin/ui/system_tray.py; gremlin/ui/backend.py:305,357 | A test for each. |
| GL-007 (01-T2) | Tray behaviour has no test | cleanup | needs-hands-on | 01 S83-S89 | gremlin/ui/system_tray.py | Tests that drive the tray logic without a real icon (off-screen runs make none), plus a hands-on check list. |
| GL-008 (01-T3) | Restart, folder changes and update skip have no tests | cleanup | confirmed-in-code | 01 S81, S116, S124, S126, S127 | joystick_gremlin.py:1119-1120; gremlin/util.py:855-895 (ensure_data_folders, copy_legacy_modules); gremlin/ui/update_model.py (skipVersion, openReleasePage) | Unit tests for restart after quit, data/logs folder change and fallback, legacy copy, Skip This Version, release page. |
| GL-009 (02-T1) | Keyboard/mouse hooks, key tables and Listen have no direct tests | cleanup | confirmed-in-code | 02 section 11 | gremlin/windows_event_hook.py; gremlin/keyboard.py; gremlin/ui/util.py (InputListenerModel, MacroRecorder); gremlin/process_monitor.py; gremlin/input_cache.py (DeviceDatabase) | Tests for process_keyboard_event/process_mouse_event, key tables, InputListenerModel, MacroRecorder with Listen, ProcessMonitor timing, missing device_db.json, parallel scan/read. |
| GL-010 (03-T1) | Stacks, hide/unhide, compact view and split mode have no tests | cleanup | confirmed-in-code | 03 S82, S84, S86 | gremlin/ui/module_model.py (stackSelected, unstackSlug, unstackAll, raiseSlug, ignoreSlug, unignoreAll, setCompactView, setSplitMode) | Unit tests, including stacks with hidden/unplugged cards. |
| GL-011 (03-T2) | Delete Device edge paths untested | cleanup | confirmed-in-code | 03 S90-S97, Q4, Q5, Q6, Q18 | gremlin/ui/hardware_profile.py:1099-1160 | Tests for no copy, vJoy card, unplugged device, while running, other unsaved edits. |
| GL-012 (03-T3) | Import refusals, Import Image Cancel, keepPhoto and Start Fresh History untested | cleanup | confirmed-in-code | 03 S57, S66, Q2, Q3, Q13, Q17 | gremlin/ui/hardware_profile.py:691-799, 2425-2465; gremlin/modules/module_file.py:107 | Tests for each refusal, rename import, Cancel restore, library growth, Start Fresh History. Locks in Redesign 2. |
| GL-013 (03-T4) | Card refresh status/counts, Logical Device menu, Auto Mapper damaged output untested | cleanup | confirmed-in-code | 03 S34, S65, S78, S88, S120 | gremlin/ui/module_model.py:1322-1356; qml/StatusCard.qml:446-487; gremlin/modules/auto_map.py:125-141 | Tests that catch GL-139, GL-140, GL-141, GL-146, GL-143. |
| GL-014 (03-T5) | output.py and registry not tested from several threads | cleanup | confirmed-in-code | 03 7.13, 7.14 | gremlin/modules/output.py; gremlin/modules/registry.py | A concurrent-access test (proves or clears GL-038, GL-245). |
| GL-015 (04-G41) | No tests for the real Backend wiring on Load/New and several thin areas | cleanup | confirmed-in-code | 04 S52, S63, S67, S77 | test/unit (fake Backend used) | Tests: real Backend signal order, selectMode/newProfile/save success, unknown startup mode, vJoy switch and Initial Values, swap onto a device with bindings, script removal. |
| GL-016 (04-G40) | Hands-on checks for start mode, prompts, macro delay, vJoy, Swap not run | ux | needs-hands-on | 04 S4, S7, S52, S64, S66, S67, S77; test plan HELP-BUG-HANDS-ON, SAFE-4-HANDS-ON, MACRO-DELAY-HANDS-ON, WORKFLOW-HANDS-ON, PS-02..04, SW-01..03 | claude/test-plan.md | Run the listed hands-on checks (user). |
| GL-017 (05-T3) | Risky action paths have no tests | cleanup | confirmed-in-code | 05 S34, S99, S104, S63, S74, S8 | test/ (missing) | Tests: no-vJoy profile, Run with unfinished action, Merge Axis Reuse + Cancel, save with pane open, new key first action, tools while pane open, Map to Mouse from hat, Logical relative loop, Load Profile end to end, right-click quick adds/drag-drop, editor QML opens without warnings. Locks in Redesign 3. |
| GL-018 (05-T1) | Glossary test doesn't check Configuration list text | text | suspected | 05 Q6 | test/unit/test_glossary_words.py:65-86 | Extend the glossary test to binding_catalog.py display strings (and Python result strings, see GL-228). |
| GL-019 (07-T2) | Button Map Save, Cancel, leave prompts, recovery and copy layout untested through the window | cleanup | confirmed-in-code | 07 S20-S28, S32-S37, S75-S80 | test/unit/rig_editor_harness.py (drives editor only) | Window-level tests, including Cancel after print area/guide change and History entries from Choose/Clear Photo. |
| GL-020 (07-T3) | No tests for outside module-file changes or Delete Device during a Button Map edit | cleanup | confirmed-in-code | 07 Q6, Q7, Q8 | test/unit (none) | Tests for Restore/Pack/Module Setup while open, Delete Device mid-edit, copy onto a device with fewer controls. |
| GL-021 (07-T4) | Button Map edge paths untested | cleanup | confirmed-in-code | 07 S41, S46, S75 | gremlin/ui/hardware_profile.py clearImage, imagesFolderUrl, chips_for_guid, savedLayouts, colorAt, profilePhotoUrl | Unit tests for Clear Photo failure, read-only install, unplugged pool, damaged other file. |
| GL-022 (08-T1) | History paths without tests | cleanup | confirmed-in-code | 08 S7, S23, S29, S31, S42, S44 | test/test_history_*.py | Tests: entries() while the writer runs, first-save before pictures, Save As entry, restore into deleted mode, missing settings key, Search and each editor filter, large file speed. |
| GL-023 (08-T2) | Device Pack paths without tests | cleanup | confirmed-in-code | 08 S57, S78, S79, S83, Q5, Q18; AU-118 | test/test_device_pack_import.py; test/test_device_pack_window.py | Tests: exportPack checks, import onto damaged file, _apply_wires failure, Undo after later saves/other profile, vJoy size, bad wires.json/outputs json, empty selection. |
| GL-024 (08-T3) | Delete Device "Save a copy" backup pack has no test | cleanup | confirmed-in-code | 08 S86, S89 | gremlin/ui/hardware_profile.py:1099 delete_device; test/test_data_safety.py | Test pack written, read back, refusal when unreadable, importing it back. |
| GL-025 (08-T4) | Auto Mapper paths without tests | cleanup | confirmed-in-code | 08 S91, S93, S95, Q7, Q9 | test/test_auto_mapper.py; test/test_auto_mapper_claims.py | Tests: Combine with more inputs than outputs, Overwrite with nested actions, twin sticks, Also claim with damaged/unwritable output file, ticks after Create. |

## 2. Urgent standalone fixes (data-loss, crash-or-hang, safety; not covered by a redesign)

Each starts as a failing test, except GL-041 (hands-on check first). GL-029 was approved by the user (2026-10-06).

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-026 (01-Q6) | A settings file that can't be written fails silently | data-loss | confirmed-in-code | 01 S38, 01 Q6 | gremlin/deferred_write.py:95-105 | One notice per session: "Settings could not be saved: <reason>" (never stopping a quit or install). |
| GL-027 (04-G6) | Deleting a mode (and its bindings) cannot be undone | data-loss | confirmed-in-code | 04 Q6, S46 | gremlin/ui/profile.py:857 (delete_mode); qml/DialogManageModes.qml | Make at least Delete Mode undoable (Add/Rename/Inherits optional). |
| GL-028 (04-G8) | Bindings in a mode missing from the mode list load silently and never show | data-loss | suspected | 04 Q8 | gremlin/profile.py:1235-1246 | On load move them into a "Recovered" mode, or warn and list them. |
| GL-029 (04-G14) | No recovery copy of unsaved profile edits after a crash | data-loss | confirmed-in-code | 04 Q14 | gremlin/profile.py; gremlin/ui/backend.py | User said yes (2026-10-06, 04 Q14 / S94): build a profile recovery copy like Button Map Autosave (about every minute while unsaved; Restore / Discard / Not now on next open). |
| GL-030 (08-G4) | Exported pack and deleted-device pack zips are written in place | data-loss | confirmed-in-code | 08 R4, S49, S86 | gremlin/ui/hardware_profile.py:1943 (exportPack), :1121 (delete_device pack) | Write zips to a temp file and swap; read the export back as the deleted-device pack is. |
| GL-031 (08-G28) | Undo Import overwrites file edits made after the import without asking | data-loss | confirmed-in-code | 08 Q5, S80 | gremlin/ui/device_pack.py:1578-1589 | If a file changed since the import, ask before putting it back. |
| GL-032 (08-G29) | Undo Import deletes created Logical Device inputs even if they now have actions | data-loss | confirmed-in-code | 08 Q21, S80 | gremlin/ui/device_pack.py:1620-1622 | Keep a created Logical input that now has actions, and say so. |
| GL-033 (01-G1) | A data folder that can't be written can stop folder lookups with an error | crash-or-hang | confirmed-in-code | 01 S126, S5 | gremlin/util.py:890-891 (_configured_child fallback mkdir) | Guard the fallback mkdir and fall back to the default folder as S126 says. |
| GL-034 (01-Q8) | Failures while modules load or the user folder is made show no message | crash-or-hang | confirmed-in-code | 01 S14, S16, Q8; APP3 | joystick_gremlin.py:44-125 (imports, setup_userprofile at :74, before main()'s guard at :1084) | The could-not-start box and logging cover every start-up failure. |
| GL-035 (02-G2, 03-G10, 04-G38) | Device list is cleared and refilled while Home, Swap Devices and the input runtime read it | crash-or-hang | suspected | 02 RB5, G2; 03 S67; 04 S81; program thread rules; AU-64 | gremlin/device_initialization.py:270-272; gremlin/event_handler.py:388-419; gremlin/ui/profile.py ProfileDeviceListModel | Build the new list aside and swap it in one step (single owner, readers get a snapshot); test that scans and reads in parallel. |
| GL-036 (02-G11) | Missing device_db.json makes later input-label lookups crash | crash-or-hang | confirmed-in-code | 02 G10, S10 | gremlin/input_cache.py:116-122 | Set the empty database before the early return; open the file with a with-block. |
| GL-037 (02-G15) | Esc-hold cancel of Listen does Qt work and a hook wait on a timer thread | crash-or-hang | confirmed-in-code | 02 RB11, G14 | gremlin/ui/util.py:122-125, 200-202 | Use a main-thread timer (threads.main_timer) for the Esc abort. |
| GL-038 (03-G8) | Possible crash when the module cache is read on two threads at once | crash-or-hang | suspected | 03 7.14; program thread rules | gremlin/modules/registry.py:293, 346-360; gremlin/modules/output.py (_refresh_claims) | Guard registry._cache with its own lock. |
| GL-039 (04-G10) | Unknown Startup Mode in the file breaks the Startup Mode box | crash-or-hang | confirmed-in-code | 04 Q10, S63 | gremlin/ui/profile.py:1092 (list.index raises) | Treat an unknown startup mode as Use Heuristic on load. |
| GL-040 (04-G13) | A script's top-level code can freeze the program when loading or adding it | crash-or-hang | suspected | 04 Q13, R8 | gremlin/user_script.py:454-456, :683; gremlin/profile.py:1885 | Read variables without running the script, or run it under a time limit (needs a design; ask the user). |
| GL-041 (08-G13) | History window rereads and parses all history files on the UI thread each time it activates | crash-or-hang | needs-hands-on | 08 S35, S23 | qml/DialogHistory.qml:136-143; gremlin/history.py entries/entry | Read incrementally or off the UI thread; don't reread everything on each activation and in Restore. |
| GL-042 (09-G29) | Text to Speech may call the speech engine off the main thread | crash-or-hang | suspected | 09 R10, S56 | gremlin/tts.py:66-80, 99-115 | Marshal enqueue to the main thread (queued signal). |
| GL-043 (03-Q6) | Delete Device is allowed while the profile is running | safety | confirmed-in-code | 03 Q6 | gremlin/ui/hardware_profile.py:1099; qml/StatusPage.qml:369 | Refuse Delete Device while running with "Stop first"; Module Setup Save stays allowed. |
| GL-044 (05-G11a) | Keyboard page removes an action at once without asking | safety | confirmed-in-code | 05 Q5 | qml/ActionNode.qml:244-246 | Ask before removing (interim until GL-106 moves the page onto the action pane). |
| GL-045 (01-G8, 02-G17, 08-G26) | Settings are read and written off the main thread with no lock (twin names from the hot-plug timer, History writer limits) | safety | suspected | 01 section 7 single owner; 02 RB12, G16; 08 R10 | gremlin/config.py (set/register); gremlin/device_initialization.py:89-90; vigem/own_pads._save; gremlin/history.py:83-84; gremlin/util.py history_dir | Guard set/register with a lock or assert main-thread use; hand twin-name writes to the main thread; read History limits/folder on the main thread and pass them in. |

## 3. Redesign 1: Run lifecycle (map 3, `gremlin/run_scope.py`)

**Done in catch-up batch 1 (d68f4d88), 2026-10-06:** GL-046 to GL-065. GL-066 decided (no change). Owner: `gremlin/run_scope.py`; guard test `test_run_scope_only`.

GL-004 locks in today's behaviour first. GL-046 is the owner; most items below become "registered with run_scope and released at Stop". Closes AU-116 and AU-117.

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-046 (06-N1, 06-G7) | Nothing owns what a Run holds; Stop lists each part by hand and three Run counters can disagree | wrong-behaviour | done (batch 1, d68f4d88) | 06 section 10, 06 S4, 06 RB2 | gremlin/code_runner.py:283, 400-435; gremlin/macro.py:96; gremlin/user_script.py:126 | gremlin/run_scope.py owns timers, loops, held outputs and values for one Run, and the one Run number that macros, script timers and loops read (map 3). |
| GL-047 (01-Q10, 03-G13, 04-G35, 05-G7, 06-G1) | Tempo, Double Tap and Smart Toggle timers still fire after Stop and during quit (reopen vJoy, plug the Xbox pad back in, hold a mouse button, change mode) | wrong-behaviour | done (batch 1, d68f4d88) | 01 S90, S91, S78, Q10; 03 S35; 04 S61, S55; 05 S91; 06 S30, S4, RB4, Q19; AU-116, AU-117 | gremlin/threads.py:93-126 (MainTimer not in _live); action_plugins/tempo/__init__.py:174; action_plugins/double_tap/__init__.py:191; action_plugins/smart_toggle/__init__.py:84; gremlin/code_runner.py:400; gremlin/modules/output.py reset_drivers | List main-thread timers in gremlin.threads; Run owns them and cancels every one at Stop, before reset_drivers. No vJoy or Xbox output outside a Run. |
| GL-048 (05-G8, 06-G2, 06-G4) | Macro key stays held when a macro ends early; Map to vJoy relative-axis loop survives a quick Stop/Run | wrong-behaviour | done (batch 1, d68f4d88) | 05 S100, S83, S92; 06 S26, S70, RB5, Q17; AU-117 | gremlin/macro.py:54 (_held_keys); action_plugins/map_to_vjoy/__init__.py:139, 157-180; action_plugins/map_to_logical_device/__init__.py:144 | Release a macro's held keys when that macro ends; end the vJoy loop on the Run number like the Logical Device loop; Stop ends both before the next Run. |
| GL-049 (04-G36, 06-G3) | Keys a script pressed stay down after Stop | wrong-behaviour | done (batch 1, d68f4d88) | 04 S90; 06 S31, RB3, Q4; decision R4; AU-117 | gremlin/keyboard.py:217-237; gremlin/macro.py:54; gremlin/user_script.py; gremlin/code_runner.py stop | Track keys scripts send during a Run and release only those at Stop. |
| GL-050 (06-G5) | Logical Device values carry over into the next Run | wrong-behaviour | done (batch 1, d68f4d88) | 06 S85, RB7, Q1; decision R1; AU-117 | gremlin/logical_device.py:67, 237; gremlin/code_runner.py:400 | Set every Logical Device value to neutral (axis 0, button up, hat centre) at Stop. |
| GL-051 (06-G6) | Release actions waiting at Stop are not dropped | wrong-behaviour | done (batch 1, d68f4d88) | 06 RB6, Q2; decision R2 | gremlin/code_runner.py:440-444; gremlin/event_helpers.py | Drop all waiting release callbacks at Stop. |
| GL-052 (04-G4, 06-G17) | Run starts on top of the old mode history; temporary modes can survive Stop | wrong-behaviour | done (batch 1, d68f4d88) | 04 Q4, S53; 06 Q3, S5; decision R3 | gremlin/mode_manager.py:174-184, 295; gremlin/code_runner.py:312-385 | Each Run starts in the toolbar mode with the mode stack and temporary modes cleared. |
| GL-053 (04-G1) | After Load or New the toolbar can show the old profile's start mode | wrong-behaviour | done (batch 1, d68f4d88) | 04 S52, Q1, R1 | gremlin/ui/backend.py:257-261, :300; gremlin/mode_manager.py:181-184 | Set the open profile (shared_state) first, then reset the mode stack and toolbar; confirm with HELP-BUG-HANDS-ON. |
| GL-054 (06-G8) | A Run that fails partway can double every event and leave a wrong status | wrong-behaviour | done (batch 1, d68f4d88) | 06 Q5, RB17, RB18, S18 | gremlin/code_runner.py:312-398; gremlin/ui/backend.py:420-428 | A failed start runs Stop itself, shows one error, and the status reads Stopped. |
| GL-055 (05-G6) | Run uses unfinished actions; an OK'd Reference placeholder can make Run fail | crash-or-hang | done (batch 1, d68f4d88) | 05 S99, Q3, RB19 | gremlin/code_runner.py:205; gremlin/base_classes.py:577; action_plugins/reference/__init__.py:141 | Run skips unfinished actions and logs one line each ("not finished: <action> on <input>"). |
| GL-056 (04-G11, 06-G10) | vJoy Initial Values only applied when the axis happens to read exactly 0 | wrong-behaviour | done (batch 1, d68f4d88) | 04 Q11, S67; 06 S8, Q7, RB1 | gremlin/code_runner.py:461-478 | Always write every Initial Value at Run through the output module, then let the physical-axis refresh overwrite them. |
| GL-057 (04-G29, 05-G15) | Load Profile action reloads and restarts Run from inside an event via the UI, even when loading failed | wrong-behaviour | done (batch 1, d68f4d88) | 04 S38, S23, R11; 05 Q13, RB6 | action_plugins/load_profile/__init__.py:61-80 | Hand the request to the Run lifecycle owner, done after the event; only Stop/Run when the load succeeded. |
| GL-058 (06-G11) | Sounds and speech queued after Stop still play | wrong-behaviour | done (batch 1, d68f4d88) | 06 Q8, RB21, S4, S28 | gremlin/audio_player.py:146-156; gremlin/tts.py:70-84 | Ignore Play Sound and Text to Speech requests when no Run is on. |
| GL-059 (06-G21) | vJoy device list and Logical Device values written from several threads unlocked | crash-or-hang | done (batch 1, d68f4d88) | 06 RB10, RB11; AU-64 | vjoy/vjoy.py:908-957 (VJoyProxy.vjoy_devices); gremlin/logical_device.py:67 | Guard VJoyProxy.vjoy_devices and Logical Device values with a lock. |
| GL-060 (04-G32) | Mode stack read from listener and macro threads without a lock | wrong-behaviour | done (batch 1, d68f4d88) | 04 R9 | gremlin/event_handler.py:209, :330; gremlin/macro.py:604-620 | Publish the current mode safely (lock or immutable snapshot). |
| GL-061 (06-G22) | Restarting a relative axis can freeze the window up to 1 s | ux | done (batch 1, d68f4d88) | 06 RB20 | action_plugins/map_to_vjoy/__init__.py:132; action_plugins/map_to_logical_device/__init__.py:134 | Don't join on the main thread; the old loop ends by Run number/flag and the new one starts without waiting. |
| GL-062 (04-G39) | Script globals shared across profiles and Runs have no owner | wrong-behaviour | done (batch 1, d68f4d88) | 04 S87, S30 | gremlin/user_script.py (callback_registry, periodic_registry, variable_registry); sys.path | Give script globals an owner cleared at Run/Stop and profile load. |
| GL-063 (01-Q11, 06-G23, 02-C1) | Quit runs Stop and shutdown cleanup twice and may create things just to stop them; hot-plug timer cancelled twice | wrong-behaviour | done (batch 1, d68f4d88) | 01 S78, Q11; 06 RB8, S17; 02 RB8 | joystick_gremlin.py:240-285 (shutdown_cleanup), :973, :1097; qml/Main.qml:647 | Run shutdown once, only stop what already exists, skip what Stop already did; listener.terminate() owns the hot-plug timer cancel. |
| GL-064 (06-G18, 05-Q16b) | Keyboard/mouse output going straight to Windows is an unwritten exception; held keys and buttons tracked in two places | cleanup | done (batch 1, d68f4d88) | 06 Q9, RB3; 05 Q16, RB9 | gremlin/macro.py:54; gremlin/sendinput.py:441; gremlin/keyboard.py:217; action_plugins/map_to_mouse, map_to_keyboard; claude/decisions.md | Record the exception in claude/decisions.md and the layer rule; track held keys and buttons in one place (run_scope). |
| GL-065 (04-G33) | Hardware listener asks the mode manager for the mode (layer break) | cleanup | done (batch 1, d68f4d88) | 04 R10 | gremlin/event_handler.py:240, :330 | Stamp the mode above the input layer (decide in the run-lifecycle design). |
| GL-066 (06-G26) | Speech engine and its signal stay alive across Runs | cleanup | decided (batch 1): speech engine program-wide, queue per Run; no change | 06 G17 | gremlin/tts.py:70-74 | Decide ownership when run_scope lands; no change required now. |

## 4. Redesign 2: module files (map 1, `gremlin/modules/store.py`)

**Done in catch-up batch 1 (d68f4d88), 2026-10-06:** GL-067 to GL-095 except GL-074 (moved to batch 2). Owner: `gremlin/modules/store.py`; guard test `test_module_store_only`.

GL-012 locks in today's behaviour first. GL-067 is the owner; most items below become "goes through the store". Closes what is left of AU-64.

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-067 (03-G14, 03-G15, 03-G16, 07-G34) | The module file store has no single owner: core logic in a UI file, paths built in many places, hardware_profile.py does everything | cleanup | done (batch 1, d68f4d88) | 03 7.3, 7.4, S9, section 10; 07 RB9; layer rule | gremlin/ui/hardware_profile.py:296-1180 (2656 lines); gremlin/ui/module_model.py:380, 492, 505, 875, 1452, 1505, 1693, 2246, 2290; gremlin/modules/registry.py (_binding_store); device_pack.py; gremlin/modules/calibration.py; gremlin/modules/auto_map.py | gremlin/modules/store.py per map 1: one path owner, guid filter, writes, deletes, pictures and bindings; split Device Pack, import and Delete Device out of hardware_profile.py. |
| GL-068 (08-G5) | Two safe file writers, each with its own History hook; one lacks the refused-swap fallback | wrong-behaviour | done (batch 1, d68f4d88) | 08 R1, R12, S8, S13 | gremlin/ui/hardware_profile.py:592 (_replace_file); gremlin/modules/module_file.py:64 (write_text) | One writer in the store; History hooked there only (map 1 step 7). |
| GL-069 (03-Q5) | Delete Device without "Save a copy" keeps no copy of the module file | data-loss | done (batch 1, d68f4d88) | 03 Q5, S91, S62 | gremlin/ui/hardware_profile.py:1150-1151 vs 875-879 | Always keep the JSON copy in the deleted devices folder, like Delete File. |
| GL-070 (03-G5) | Import Image deletes old photo files even when the damaged-file check then refuses the save | data-loss | done (batch 1, d68f4d88) | 03 S64 | gremlin/ui/hardware_profile.py:2442-2465 | Check the module file first; touch pictures only when the save will go ahead. |
| GL-071 (07-G6) | Button Map ignores module-file changes made elsewhere; Save writes over them | data-loss | done (batch 1, d68f4d88) | 07 Q6, RB2 | qml/DialogJoystickButtonMap.qml (no reload hook); gremlin/ui/hardware_profile.py:2318 save | Outside Edit reload on change; in Edit warn on Save ("the module file changed since you started editing") with Keep mine / Take theirs. |
| GL-072 (08-G1) | Device Pack import silently replaces a damaged module file instead of refusing | data-loss | done (batch 1, d68f4d88) | 08 Q2, S78, R2; decision F1 | gremlin/ui/device_pack.py:1793, 1835, _write_module:1636 | Refuse and point to Start Fresh (store.replace refuses unless forced). |
| GL-073 (08-G3) | Pack pictures are written in place; a crash can leave a half picture | data-loss | done (batch 1, d68f4d88) | 08 R3, S76 | gremlin/ui/device_pack.py:1162 (_write_pictures) | Write pictures through the safe writer (temp + swap) in the store. |
| GL-074 (04-G28) | Logical Device and OSC rows are wiped by any new Profile object | data-loss | batch 2 | 04 R3, S2 | gremlin/profile.py:859-860, :1248-1325 | Move these rows into the Profile object instead of global singletons. |
| GL-075 (03-G1) | Save and Start Fresh can reach a different file than Delete for a stale device id | wrong-behaviour | done (batch 1, d68f4d88) | 03 S9, S2, S20; AU-04, AU-22 | gremlin/ui/module_model.py:379, 491, 1451, 1505, 2245; gremlin/ui/hardware_profile.py:300-309, 956, 1744-1761 | One guid filter used by every caller, through the store. |
| GL-076 (03-G2) | Twin cards may show the other twin's counts after a save (name-only lookups) | wrong-behaviour | done (batch 1, d68f4d88) | 03 S77, S6, S9, Q17; decision F4 | gremlin/ui/module_model.py:504-506, 1303, 1343, 1347; gremlin/ui/module_pairing.py:32, 39; gremlin/ui/module_inputs.py:147 | Look twins up by id always and log when the id is missing; add a test. |
| GL-077 (03-Q13) | Import into a renamed stick writes a new file instead of the one it uses | wrong-behaviour | done (batch 1, d68f4d88) | 03 Q13, S3, S55; AU-04 | gremlin/ui/hardware_profile.py:700-701 | Import into the file the device uses (resolve_module_slug), via the store. |
| GL-078 (03-Q2, 07-G8) | Module Setup's Import Image saves the photo at once and Cancel does not put it back; three places write the device photo | wrong-behaviour | done (batch 1, d68f4d88) | 03 Q2, S49, S52; 07 Q5, RB1 | gremlin/ui/hardware_profile.py:2429-2465; qml/DialogConfigureModule.qml:123, 206, 221, 224; gremlin/module_model.py:2289-2293; Device Pack import | One owner for the device photo; Module Setup's photo waits for its Save and Cancel puts the old one back, as in the Button Map. |
| GL-079 (07-G3) | A refused Button Map Save on a damaged module file still copies photo and pictures | wrong-behaviour | done (batch 1, d68f4d88) | 07 S12, S20 | gremlin/ui/hardware_profile.py:2333 (_pack_assets) before 2335 (damage check) | Check for damage before copying any picture (store.update refuses first). |
| GL-080 (03-Q17, 08-G6) | Start Fresh and a failed pack import's clean-up make no History entry | wrong-behaviour | done (batch 1, d68f4d88) | 03 Q17, S69, S66; 08 Q12, S12, R12; decision F3 | gremlin/modules/module_file.py:107-113; gremlin/ui/module_model.py:1456; gremlin/ui/device_pack.py:1564 (_put_back) | Record both in History through the store's delete/move_aside. |
| GL-081 (08-G10, 08-G40) | History Restore of a module file ignores which file the device uses and does not bring back its binding | wrong-behaviour | done (batch 1, d68f4d88) | 08 Q14, S43, section 10 | gremlin/ui/history_model.py:271-272 (_restore_module); global/internal/module-file-bindings | Restore through store.replace and rebind, as Module Setup Undo does (S85). |
| GL-082 (08-G8) | First module save of a session can record the new picture as the "before" picture | wrong-behaviour | done (batch 1, d68f4d88) | 08 S8 | gremlin/history_modules.py:51-52, 206-214 | Read the before pictures before the write (store hook). |
| GL-083 (03-G11, 06-G9) | A failed output-claims read blocks all vJoy output for a second | wrong-behaviour | done (batch 1, d68f4d88) | 03 S28, S36; 06 RB16, S47; AU-64 | gremlin/modules/output.py:27, 48-71 (except -> outputs = []) | Keep the last good claims on a failed read, log once, retry. |
| GL-084 (03-G12, 06-G16) | Output claims saved while running take up to 1 s to apply | wrong-behaviour | done (batch 1, d68f4d88) | 03 S36; 06 Q12, S53 | gremlin/modules/output.py:27 (_CLAIM_TTL), 48-52, 74; gremlin/code_runner.py:326 | Call output.refresh() when a module file is saved (configChanged). |
| GL-085 (07-G18) | A missing picture can be replaced by another device's picture with the same name | wrong-behaviour | done (batch 1, d68f4d88) | 07 S11 | gremlin/ui/hardware_profile.py:1791-1824 (_resolve_existing) | Resolve pictures only in the device's own folder; show missing pictures as missing. |
| GL-086 (08-G38) | Photo folders and pack export names still use the device's own-name slug | wrong-behaviour | done (batch 1, d68f4d88) | 08 section 10; AU-64 | gremlin/ui/device_pack.py _slug in _pack_label (:574), _output_doc | Use the store's slug. |
| GL-087 (03-G26) | Import Undo is program-wide, not tied to a device or window | wrong-behaviour | done (batch 1, d68f4d88) | 03 S59 | gremlin/ui/hardware_profile.py (_import_undo), 661 | Tie the Undo record to the device and window that made it. |
| GL-088 (03-G24) | Calibration skips a second stick that shares one file | ux | done (batch 1, d68f4d88) | 03 S110, S100 | gremlin/modules/calibration.py:72-73 | List by device id, not by file. |
| GL-089 (03-Q3) | Every Save Module adds another copy of the photo to the library and writes twice | cleanup | done (batch 1, d68f4d88) | 03 Q3, S69 | qml/DialogConfigureModule.qml:122-123; gremlin/ui/hardware_profile.py:1782-1789, 2425 | Copy to the library only when the photo changed; one write and one History entry per Save. |
| GL-090 (03-G17) | Card key (device name slug) has no named owner | cleanup | done (batch 1, d68f4d88) | 03 7.7, S87, Q17; decision F2 | gremlin/ui/module_model.py:1432, 1585, 1660 | Keep cards keyed by device name through one named function. |
| GL-091 (03-G18) | Duplicate binding-clear functions | cleanup | done (batch 1, d68f4d88) | 03 7.8 | gremlin/ui/hardware_profile.py:802-814, 1060-1072 | Keep one. |
| GL-092 (03-G27) | Deleted devices folder holds two formats and nothing lists or prunes it | cleanup | done (batch 1, d68f4d88) | 03 S62, S91, S98 | gremlin/ui/hardware_profile.py:865-899, 1099-1160 | The store owns the folder, writes both formats and can list them. |
| GL-093 (07-G14, 08-G25) | Button Map, Device Pack and History import other modules' private helpers | cleanup | done (batch 1, d68f4d88) | 07 RB7; 08 R13 | gremlin/ui/hardware_profile.py:26-34, 1429-1510; gremlin/ui/button_map_labels.py:22; gremlin/ui/device_pack.py:29-45; gremlin/ui/history_model.py:221 | Expose public doors (store, registry, input_pairing) and import those. |
| GL-094 (07-G20) | Delete Device leaves its recovery copy and photo safety copy behind | cleanup | done (batch 1, d68f4d88) | 07 Q11 | gremlin/ui/hardware_profile.py:2245-2292, _stash_dir; delete_device | Delete Device removes both. |
| GL-095 (08-G24) | Two "Undo Import" systems with the same function name and different rules | cleanup | done (batch 1, d68f4d88) | 08 R11, S80, S85 | gremlin/ui/hardware_profile.py:649-688; gremlin/ui/device_pack.py:1538-1633 | One undo path through store.replace; distinct names meanwhile. |

## 5. Redesign 3: actions (map 2)

**Catch-up batch 1 (d68f4d88), 2026-10-06:** done GL-096, 097, 100-105, 107, 108; GL-098 part done; GL-074, GL-106, GL-099, GL-109 and the rest of GL-098 moved to batch 2. Owner: the `Library` in `gremlin/profile.py`; guard test `test_library_only`.

GL-017 locks in today's behaviour first. Closes AU-118 and the shared Merge Axis split.

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-096 (05-G1) | OK on an action two inputs share splits it instead of changing both | wrong-behaviour | done (batch 1, d68f4d88) | 05 S62, Q1; decision A1; AU-118 | gremlin/ui/binding_catalog.py:138, :1125; test/test_audit3_actions_undo.py:478-498 | OK writes the edited copy back into the one shared action; "Shared with ..." note; change the test that asserts the split. |
| GL-097 (05-G2) | Picking or reusing a shared action puts the live one into the pane draft | wrong-behaviour | done (batch 1, d68f4d88) | 05 S63, S21, S27, Q1; decision A4 | action_plugins/merge_axis/__init__.py:236, :451-459; action_plugins/dual_axis_deadzone/__init__.py:178; action_plugins/reference/__init__.py:119; gremlin/plugin_manager.py:145-148 | A shared action picked in the pane (pick list, "+", Reference, Merge Axis Reuse) is edited as a copy until OK. |
| GL-098 (05-G12) | Pane OK can overwrite changes from History Restore, Auto Mapper or Device Pack | data-loss | part done (batch 1: OK refused when the input changed); closing the pane first is batch 2 | 05 Q8 | gremlin/ui/binding_catalog.py:1187-1217 | Those tools close the pane first, asking if it has changes. |
| GL-099 (04-G37, 08-G2) | A Device Pack import failing partway leaves inputs removed and new modes/Logical inputs, with nothing to undo | data-loss | batch 2 | 04 S47; 08 Q20, S79, S76; decision A3; AU-118 | gremlin/ui/device_pack.py:1474-1503 (_apply_wires) | Run the wire import all-or-nothing (map 2 change()); undo everything on failure and say so. |
| GL-100 (08-G35) | History Restore of an input doesn't bring back a shared action's old settings | wrong-behaviour | done (batch 1, d68f4d88) | 08 S40; decision A2 | gremlin/profile.py:1126 (put_input); gremlin/ui/history_model.py:219 | Restore the shared action for every input using it (map 2 snapshot/restore). |
| GL-101 (04-G27, 05-RB3) | Two "remove unused actions" rules; removing an action and a binding clean up differently; the library checks the wrong profile | wrong-behaviour | done (batch 1, d68f4d88) | 04 R2, R4, S71; 05 RB3, S47 | gremlin/profile.py:450-456, :498-565, :1201-1214; gremlin/ui/profile.py:448-482, 478, 695-707, 704; gremlin/ui/binding_catalog.py:940 | One removal rule owned by the profile's own library (map 2 step 2). |
| GL-102 (05-RB1) | New actions always go into the current profile's library, not the edited input's | wrong-behaviour | done (batch 1, d68f4d88) | 05 RB1 | gremlin/plugin_manager.py:148; gremlin/profile.py:1395 | Create actions through the one owner that adds them to the library of the input being edited. |
| GL-103 (05-G14) | Removing a Chain sequence leaves its actions in memory | cleanup | done (batch 1, d68f4d88) | 05 Q12, RB4, S47 | action_plugins/chain/__init__.py:117-124 | Release the sequence's actions through the one removal rule. |
| GL-104 (05-G9) | Saving with the pane open may change the unsaved draft | wrong-behaviour | done (batch 1, d68f4d88) | 05 S34 | gremlin/profile.py:702, :914 | Save cleans only actions inputs use and leaves drafts alone; test save with the pane open. |
| GL-105 (04-G7, 05-G20) | A profile with an unknown action type will not open at all | wrong-behaviour | done (batch 1, d68f4d88) | 04 Q7, S23; 05 S69; ACT15 | gremlin/profile.py:638-646 | Open the profile, keep the unknown action as-is (written back on save) and warn naming the type. |
| GL-106 (05-G11b) | Keyboard page edits the live profile with no draft, OK or Undo | ux | batch 2 | 05 Q5 (replaces S78), S21, S35 | qml/InputConfiguration.qml; gremlin/ui/binding_catalog.py | The Keyboard page uses the same action pane as Configuration. |
| GL-107 (05-RB16, 06-G25) | Logical Device page has its own copy of pane, draft and Undo, reusing other models' private helpers | cleanup | done (batch 1, d68f4d88) | 05 RB16; 06 RB15 | gremlin/ui/logical_layout.py:16-38 (_begin_pane, _replace_sequences, _snapshot); gremlin/ui/binding_catalog.py | One pane/draft/Undo owner used by both pages (map 2 steps 3/5). |
| GL-108 (06-G13) | Empty Logical Device: a macro step silently creates Button 1; a condition errors | wrong-behaviour | done (batch 1, d68f4d88) | 06 Q15, RB12 | gremlin/macro.py:770-773; action_plugins/condition/condition.py:753 | No hidden create; show "Add a Logical Device control first" in both editors. |
| GL-109 (08-G22) | Device Pack edits the profile's input lists and device database directly | cleanup | batch 2 | 08 R5 | gremlin/ui/device_pack.py:1498, 1501, 1606 | Go through Profile methods inside map 2's change(). |

## 6. Wrong-behaviour and UX fixes (standalone, by subsystem)

### 01 Program, windows and settings

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-110 (01-Q1) | Closing the main window can leave the program running with only a tool window | wrong-behaviour | suspected | 01 S80, Q1 | qml/Main.qml:1366-1388; qml/helpers.js:47 | The main window's X always quits (after the usual questions), same as File > Exit. |
| GL-111 (01-Q2) | Exit may only hide the window when Minimize to tray is on | wrong-behaviour | needs-hands-on | 01 S85, S75, Q2 | gremlin/ui/system_tray.py:80-92 | Check once on a real screen; then the close filter lets closes made by a quit pass. |
| GL-112 (01-Q3) | Window place and size not saved when X hides it to the tray | ux | confirmed-in-code | 01 S79, Q3; test plan W-21 / S-21 | qml/Main.qml:90, 1371; gremlin/ui/system_tray.py:80-92 | Save the window place whenever it hides to the tray. |
| GL-113 (01-Q4) | Changing the Logs or data folder mid-session splits log writers and readers | wrong-behaviour | confirmed-in-code | 01 S125, Q4 | joystick_gremlin.py:633-645, 821-836, 1079; gremlin/error_report.py install; gremlin/ui/live_debug.py:36, 351-356 | Folder rows say "Takes effect on the next start"; writers and readers stay on the start-up folder. |
| GL-114 (01-Q5) | A missing chosen data folder is silently replaced by the default | wrong-behaviour | confirmed-in-code | 01 S126, Q5 | gremlin/util.py:855-872 | Use the default folder and say so once per session. |
| GL-115 (01-Q7) | History Restore of Diagnostic logs or UI scale doesn't take effect | wrong-behaviour | suspected | 01 S34, S55, Q7 | gremlin/ui/history_model.py:294-316; gremlin/ui/log_option.py:46, 108; gremlin/ui/ui_scale_option.py:77 | Restore applies such settings at once, as the Options control does. |
| GL-116 (01-Q9) | Second copy: if the other copy can't be closed, it starts silently without the lock | wrong-behaviour | confirmed-in-code | 01 S18, Q9 | joystick_gremlin.py:1060-1067 | Say "The other copy could not be closed" and offer No / Cancel again. |
| GL-117 (01-G2) | No single owner of the settings list; settings registered late are deleted at start | wrong-behaviour | confirmed-in-code | 01 S6, section 7; AU-47 | joystick_gremlin.py:571-818; gremlin/config.py:338 (purge_unused); gremlin/ui/live_debug.py:209, 561; gremlin/ui/update_model.py:42 | One owner of keys, defaults and writers, registered before purge_unused runs. |
| GL-118 (01-G9) | Live Log Reader refresh does file and folder work on the main thread | ux | suspected | 01 S95, S111 | gremlin/ui/live_debug.py:36, 351-356; qml/DialogLiveLog.qml:65 | Measure first; resolve the logs folder once and avoid large reads per tick. |

### 02 Input devices, keyboard, Listen, HidHide, auto-load

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-119 (02-G1, 04-G12) | Ticking "vJoy as input" / the vJoy Behavior switch in Profile Settings stops or restarts a running profile | wrong-behaviour | confirmed-in-code | 02 Q1, RB6, G1; 04 Q12, R12, S66 | gremlin/ui/profile.py:1155-1162; gremlin/ui/backend.py:305-315 | Own signal that refreshes device lists and claims but never stops or restarts a Run; scan is the only sender of device_change_event; while running say "takes effect at the next Run". |
| GL-120 (02-G3) | Listen and macro Record share the mouse hook; one stopping cuts the other off | wrong-behaviour | confirmed-in-code | 02 RB7, G3, S51 | gremlin/ui/util.py:113-124, 370-371 | One owner of the mouse hook with a start/stop count. |
| GL-121 (02-G6) | Keys the program sends come back as input and can trigger other bindings | wrong-behaviour | confirmed-in-code | 02 Q4, S50, G5 | gremlin/event_handler.py:467-469 | Ignore injected keys while a Run is active (bindings and recording); decide whether Listen sees them. |
| GL-122 (02-G7) | First Run sends centre for axes not moved since start (throttle at 80% reads centre) | wrong-behaviour | needs-hands-on | 02 Q7, S42, G6 | gremlin/input_cache.py:237-244; gremlin/input_refresh.py:26-35 | First confirm dill.dll does not already send starting values; then read the real position for unseen axes and cache it. |
| GL-123 (02-G8) | Unplugged stick stays in the input cache; a changed layout on return loses events silently | wrong-behaviour | confirmed-in-code | 02 G7, S41 | gremlin/input_cache.py:477-507; gremlin/event_handler.py:321, 336, 351 | Drop or rebuild the cached stick on unplug/reconnect; log an event for an unknown input. |
| GL-124 (02-G9, 02-G10) | Four ways to name a device; scripts and the input cache see the driver name, not the "(2)" twin name | wrong-behaviour | confirmed-in-code | 02 RB9, G8, G9, S17 | gremlin/input_cache.py:283, 298-304; gremlin/device_initialization.py device_name; gremlin/ui/device_names.py; gremlin/ui/device.py (DeviceListModel) | One shown-name function (driver name, twin name, alias) used by every screen and the cache. |
| GL-125 (02-G18) | A key whose release Windows lost is ignored once on its next press | wrong-behaviour | confirmed-in-code | 02 G17, S46 | gremlin/event_handler.py:473-477 | Clear the key cache when the lost release is detectable, or check real key state first. |
| GL-126 (02-G19) | Windows can silently remove a slow keyboard hook and nothing reinstalls it | wrong-behaviour | needs-hands-on | 02 G18, S45 | gremlin/windows_event_hook.py:133-167, 305-322 | Detect the lost hook (watchdog) and reinstall it; keep the callback minimal. |
| GL-127 (02-G20) | An error in a hook callback stops the key reaching other programs' hooks | wrong-behaviour | confirmed-in-code | 02 G19, S45 | gremlin/windows_event_hook.py:155-167 | try/except (log) so CallNextHookEx always runs. |
| GL-128 (02-G21) | Numpad Enter is sent as the Separator key | wrong-behaviour | confirmed-in-code | 02 G20, S49 | gremlin/keyboard.py:359 | VK_RETURN with the extended flag. |
| GL-129 (02-G22) | Auto-load can miss the first program in focus at start | wrong-behaviour | confirmed-in-code | 02 G21, S84 | gremlin/ui/backend.py:252-253 vs 262 | Connect process_changed before starting the process monitor. |
| GL-130 (02-Q18) | Clicking into the program's own window stops the Run when auto-load is on | wrong-behaviour | confirmed-in-code | 02 Q18, S90 | gremlin/ui/backend.py:357-398 | Treat the program's own window as "no change". |
| GL-131 (02-G23) | Listen can catch vJoy or Xbox output instead of the stick while a profile runs | wrong-behaviour | confirmed-in-code | 02 G22, S63 | gremlin/ui/util.py:158-166 | Ignore events from vJoy and Gremlin's own Xbox devices in Listen. |
| GL-132 (02-Q3) | Stored twin name wins even if the driver's name changes; old names never removed | wrong-behaviour | confirmed-in-code | 02 Q3, S16 | gremlin/device_initialization.py:60-90 | Use the stored name only while the driver's base name matches; drop unused entries. |
| GL-133 (02-G13) | HidHide device tick is saved even when the driver refuses it | wrong-behaviour | confirmed-in-code | 02 Q14, G12 | gremlin/ui/hidhide.py:1667-1673 | Save the hidden list only after the driver accepts it. |
| GL-134 (02-G14) | HidHide rescans every HID device on the main thread at each device change | ux | suspected | 02 RB14, G13 | gremlin/ui/hidhide.py:1449-1485 | Measure; move enumeration off the main thread or reload only while the HidHide window is open. |
| GL-135 (02-G24) | Two switches for one HidHide setting (Options and HidHide window) | ux | confirmed-in-code | 02 Q16, RB10, G23; test plan S-38 | gremlin/ui/option.py:83; qml/DialogHardwareHide.qml:185; qml/help_topics.js:272 | Keep only the HidHide window's Automatically Start switch; Options points to it; update Help. |
| GL-136 (02-G12) | Device Information leaves out left-out vJoy devices and Gremlin's Xbox pads | ux | confirmed-in-code | 02 Q6, S9, G11 | gremlin/ui/device.py:262-272; qml/DialogDeviceInformation.qml | List them, marked "left out (see message)" and "Gremlin's Xbox pad". |
| GL-137 (02-Q9) | A short Esc tap cancels Listen when keys are not being listened for | ux | confirmed-in-code | 02 Q9, S64 | gremlin/ui/util.py:195-207 | Cancel only on a 1 s Esc hold in both cases; Help names it. |

### 03 Modules and Home cards

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-138 (03-Q4) | Delete Device saves the whole profile to disk, skipping the unfinished-actions check | wrong-behaviour | confirmed-in-code | 03 Q4, S95 | gremlin/ui/hardware_profile.py:1033-1057 (to_xml at :1048) | Remove the device's actions in memory and leave the profile unsaved; update S95 wording and the result text. |
| GL-139 (03-Q8) | Card counts show the device's own counts when nothing of a kind is claimed | wrong-behaviour | confirmed-in-code | 03 Q8, S78, S73 | gremlin/ui/module_model.py:1612-1614, 1682-1684 vs 1349-1351 | Always show claimed counts in both _reload and _refresh_inplace. |
| GL-140 (03-G3) | vJoy card loses "In use by another program" after any settings change | wrong-behaviour | confirmed-in-code | 03 S34; DEV6 | gremlin/ui/module_model.py:1352-1353 | _refresh_inplace keeps the busy status. |
| GL-141 (03-G4) | Damaged card stays red after the file is fixed by History Restore | ux | suspected | 03 S65 | gremlin/ui/module_model.py:1322-1356 | _refresh_inplace re-checks the damaged flag. |
| GL-142 (03-Q10) | Stacks forget hidden or unplugged cards on any stack edit | wrong-behaviour | confirmed-in-code | 03 Q10, S84, S81 | gremlin/ui/module_model.py:977-991, 1151-1157 | Keep cards that aren't showing in their stacks. |
| GL-143 (03-Q15, 08-G19) | Auto Mapper "Also claim" still makes actions for outputs it could not claim | wrong-behaviour | confirmed-in-code | 03 Q15, S120; 08 Q9, S93 | gremlin/modules/auto_map.py:125-141 | Skip those outputs and list them as "not claimed" in the skip report. |
| GL-144 (03-Q16) | Typing a friendly name in Keyboard Module Setup may tick the typed keys | wrong-behaviour | needs-hands-on | 03 Q16, S27 | gremlin/ui/module_model.py:1991-2028 | Check off-screen first; then ignore key presses while a text box has focus. |
| GL-145 (03-G7) | A physical device named Keyboard or OSC is treated as the Keyboard/OSC module | wrong-behaviour | suspected | 03 7.12, S23 | gremlin/ui/module_model.py:1892-1898 | Decide Keyboard/OSC by built-in id only (gremlin/modules/ids.py). |
| GL-146 (03-Q7) | Logical Device card menu offers Module Setup, Calibration and others that don't work | ux | confirmed-in-code | 03 Q7, S88 | qml/StatusCard.qml:446-487; gremlin/ui/module_model.py:1845-1849 | Leave Module Setup, Calibration, Auto Mapper, Device Information and Swap Device out of that menu. |
| GL-147 (03-Q18) | Delete Device is offered on vJoy and Xbox output cards | ux | confirmed-in-code | 03 Q18, S93, S88 | qml/StatusCard.qml:486; qml/StatusPage.qml:394-395; gremlin/ui/hardware_profile.py:1148-1151 | Leave it out of output card menus; update Help's card menu list. |
| GL-148 (03-Q9) | Calibration does not mark unclaimed axes | ux | confirmed-in-code | 03 Q9, S13 | gremlin/ui/device.py:1501; qml/DialogCalibration.qml | Keep every axis listed; mark unclaimed ones "not claimed". |

### 04 Profiles, modes and scripts

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-149 (04-G2) | Last Active remembers toolbar picks made while stopped, not the mode last run | wrong-behaviour | confirmed-in-code | 04 Q2, S52, S55 | gremlin/mode_manager.py:189-212; gremlin/ui/backend.py:322-329 | Store the last mode only for modes used while running. |
| GL-150 (04-G3) | Auto-load held back by unsaved edits leaves the old profile running | wrong-behaviour | confirmed-in-code | 04 Q3, S35, S36 | gremlin/ui/backend.py:378-392 | Stop the running profile (unless Keep running is on), as the missing-file case does. |
| GL-151 (04-G9) | A file with no modes or duplicate mode names loads without a warning | wrong-behaviour | suspected | 04 Q9, S39 | gremlin/profile.py:1737-1767 | Add "Default" when the list is empty; warn about duplicates. |
| GL-152 (04-G17) | Last mode is forgotten when the same file is opened by another path spelling | wrong-behaviour | confirmed-in-code | 04 Q17, S52, S55 | gremlin/mode_manager.py:149, :189-212 | Key the store by the resolved, case-folded path (as Recent does). |
| GL-153 (04-G18) | Plugging in a used device can mark the profile unsaved; the check is heavy | wrong-behaviour | confirmed-in-code | 04 Q18, Q19, R14, S7, S8 | gremlin/profile.py:954; qml/Main.qml:27-45 | Fill device names only at save; measure the check and mark dirty on edit if slow. |
| GL-154 (04-G20, 04-G21) | Mode name rules (blank, look-alike) only enforced in Manage Modes; the hidden root counts as a mode | wrong-behaviour | confirmed-in-code | 04 Q21, R5, S40, S48 | gremlin/profile.py:1604-1615, 1714, 1735; gremlin/ui/profile.py:897 | Move the rules into ModeHierarchy.add_mode/rename; mode_exists("") is False; refuse blank names in the model layer. |
| GL-155 (04-G24) | Removed script's variables stay registered | wrong-behaviour | suspected | 04 S85 | gremlin/profile.py:1825-1834 | Remove them from Script.variable_registry on removal. |
| GL-156 (04-G26) | vJoy Initial Value set in the UI isn't clamped to -1..1 | wrong-behaviour | confirmed-in-code | 04 S67 | gremlin/profile.py:294-304 | Clamp in Settings.set_initial_vjoy_axis_value as load does. |
| GL-157 (04-G15) | Missing Recent file shows an error but offers no Forget It | ux | confirmed-in-code | 04 Q15, S19 | qml/Main.qml:599-604; gremlin/ui/backend.py loadProfile | Offer Forget It, as at start-up. |
| GL-158 (04-G19) | Swap Devices allows From and To to be the same device | ux | confirmed-in-code | 04 Q20, S77 | gremlin/swap_devices.py:130; gremlin/ui/tools.py:64-89 | Refuse a swap where From and To are the same id. |
| GL-159 (04-G25) | Script rename refreshes one row past the end of the list | ux | confirmed-in-code | 04 S85; AU-65 | gremlin/ui/script.py:421-423 | dataChanged for 0..rowCount-1 (or just the renamed row). |

### 05 Actions and editors

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-160 (05-Q11) | Action pane opens while running with OK still live | wrong-behaviour | confirmed-in-code | 05 Q11, S32, S101; test plan S-13 | qml/BindingCatalog.qml (pane open/OK) | While running the pane opens read-only with "Stop to edit" and no OK. |
| GL-161 (05-Q9) | Axis Delta ignores earlier shaping and skips value 0 | wrong-behaviour | confirmed-in-code | 05 Q9, S80 | action_plugins/axis_delta/__init__.py:57-64 | Use the value shaped by earlier actions; treat 0 as a value. |
| GL-162 (05-Q10) | Split Axis changes the value seen by later actions in the same list | wrong-behaviour | suspected | 05 Q10 (replaces S80 Split part) | action_plugins/split_axis/__init__.py | Split's change stays inside its two lists. |
| GL-163 (05-Q17, 06-G19) | Macro Joystick step may bypass input-module claims; Macro help doesn't say | wrong-behaviour | suspected | 05 Q17, RB10; 06 Q14 | gremlin/macro.py:564-620; Macro help text | Send the step through the input module like a real event (unclaimed controls do nothing); Macro help says so. |
| GL-164 (05-G10) | A key added on the Keyboard page may have no way to get its first action | wrong-behaviour | needs-hands-on | 05 S74, Q4 | qml/InputConfiguration.qml; KeyboardManagerModel.addKey | Check by hand; if not possible, a key with no binding shows one empty binding. |
| GL-165 (05-G19) | Add Action list can come up empty if action order settings are damaged | wrong-behaviour | suspected | 05 S6, S7 | gremlin/ui/action_model.py:200-206 | Sort missing actions to the end instead of list.index raising. |
| GL-166 (05-G18) | Output filter hides itself when no vJoy device exists, even with other outputs | ux | confirmed-in-code | 05 S18 | qml/BindingCatalog.qml:1275-1290 | List every destination in use regardless of vJoy. |
| GL-167 (05-Q14) | New Dual Axis Deadzones all get the same name | ux | confirmed-in-code | 05 Q14 | action_plugins/dual_axis_deadzone/__init__.py:137 | Number them like Merge Axis ("Dual Axis Deadzone N"). |
| GL-168 (05-N22) | Editor controls look inconsistent across actions (on hold) | ux | confirmed-in-code | 05 S51; N22 | qml/ActionSelector.qml:39-55; MergeAxisAction.qml:146-168; DualAxisDeadzoneAction.qml:167-171 | Align editor controls when the user takes it off hold. |

### 06 Run/Stop and outputs

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-169 (06-G12) | An open action editor stays open and editable when Run starts | wrong-behaviour | confirmed-in-code | 06 Q6, RB14, S13, S82 | qml/LogicalPage.qml:114; qml/InputConfiguration.qml:36; gremlin/ui/logical_layout.py; qml/Main.qml:1059 | Before Run, ask "Save or discard the open action first?" when an editor is open. |
| GL-170 (06-G15) | Reading a vJoy value opens the vJoy device | wrong-behaviour | confirmed-in-code | 06 Q16, RB19, S51 | gremlin/modules/output.py:303-315 | Reads never open a device (return neutral); only writes open it. |
| GL-171 (06-N2) | Locked-while-running rule lives only in each QML page | ux | confirmed-in-code | 06 S13, S82, RB14 | qml/LogicalPage.qml:114; qml/InputConfiguration.qml:36; BindingCatalog.qml; KeyboardInputList.qml; OscDevice.qml; gremlin/ui/logical_layout.py | One Python-side owner of the edit lock that models check too. |
| GL-172 (06-G14) | A vJoy error inside an action pauses the whole profile with an error box | ux | confirmed-in-code | 06 Q10 | gremlin/event_handler.py:691-694, 705-708 | Remove the auto-pause and error box on VJoyError. |

### 07 Button Map

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-173 (07-G1) | Print area, print setup and guides change the saved file mid-edit; Cancel keeps them | wrong-behaviour | confirmed-in-code | 07 S29, S57, S95, Q1, Q3, RB3 | qml/DialogJoystickButtonMap.qml:1505-1513, 1691-1716, 3026-3031 | Make them part of the edit (Save writes, Cancel takes back, undoable); view, zoom and grid stay instant. |
| GL-174 (07-G2) | Choose Photo saves the photo at once; History lists an unsaved photo and the Cancel | wrong-behaviour | confirmed-in-code | 07 S29, S40, Q2, RB3 | gremlin/ui/hardware_profile.py:2429-2473 | New photo waits beside the old one until Save; one History entry per Save. |
| GL-175 (07-G5) | A guide or print-area change in an edit creates the module file with the old map | wrong-behaviour | confirmed-in-code | 07 S29, S96 | gremlin/ui/hardware_profile.py:2376-2377 | saveUi never calls save; with no module file keep the ui block in memory until Save. |
| GL-176 (07-G7) | Delete Device during an edit offers Save, which recreates the deleted file | wrong-behaviour | confirmed-in-code | 07 S13, Q7 | qml/Main.qml:484-493 | Close without saving and show a short note that the device was deleted. |
| GL-177 (07-G10) | A chip name matching an EVO R part name is treated as no name on every device | wrong-behaviour | confirmed-in-code | 07 Q10, RB10 | qml/VkbRigEditor.qml:1007-1040; qml/rig_chips.js:63-65, 92-94 | Drop the EVO R name check; a typed name is always the user's. |
| GL-178 (07-G15) | Choose Photo and Import Picture create a folder inside the program folder | wrong-behaviour | confirmed-in-code | 07 Q13, RB11 | gremlin/ui/hardware_profile.py:2596-2600 | Open in Pictures or the last folder used; never create folders in the install folder. |
| GL-179 (07-G9) | Undo does not cover Choose Photo, Clear Photo, print area or guides | ux | confirmed-in-code | 07 S57, Q3 | qml/VkbRigEditor.qml:852-858 | Make them undo steps (with GL-173). |
| GL-180 (07-G11) | Every live press re-reads the module file and profile to rebuild pool rows | ux | suspected | 07 RB8, S14 | qml/JoystickButtonMapCard.qml:54-59; gremlin/ui/hardware_profile.py:1480 | Re-read only when the module file, profile or device list changes. |
| GL-181 (07-G22) | Templates whose pictures were moved or deleted give no warning | ux | suspected | 07 S81 | gremlin/ui/hardware_profile.py templateNodes (2119-2243) | Check picture paths on apply and say which are missing. |
| GL-182 (07-G23) | Copied layout may hold chips for controls this device lacks, with no notice | ux | confirmed-in-code | 07 Q8, S76 | qml/DialogJoystickButtonMap.qml:1945-1985 | Keep them and say "N chips are for controls this device does not have". |
| GL-183 (07-G26) | Export failure says only "Export failed." | ux | confirmed-in-code | 07 S91, Q19 | qml/DialogJoystickButtonMap.qml:1864-1867; gremlin/ui/hardware_profile.py saveArea | Say which file and why, as Template export does. |
| GL-184 (07-G30) | A mirrored Copy Button Map may need two Undos | ux | needs-hands-on | 07 S78; AU-27 | qml/DialogJoystickButtonMap.qml:1968-1985 | Record copy and mirror as one undo step. |
| GL-185 (07-G31) | Bigger page around the photo is planned but not built | ux | confirmed-in-code | 07 S68, Q14; BM41 | qml/VkbRigEditor.qml:153-156 | Build BM41 on the single page-size constant (GL-270), converting existing maps. |
| GL-186 (07-G32) | Draw shapes Plus, Radial ring and Named Card are planned but not built | ux | confirmed-in-code | 07 tracker; SH1, SH2, SH3 | qml/rig_shapes.js; qml/rig_menu.js:311 | Add the three shapes as described in SH1-SH3. |

### 08 History, Device Pack, Auto Mapper

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-187 (08-G7) | Opening History can run queued history work on the UI thread alongside the writer | wrong-behaviour | suspected | 08 R9, S23 | gremlin/history.py:289; gremlin/history_modules.py:53, 211, 221 | flush waits for the writer (bounded), or lock _last_pictures and keep order. |
| GL-188 (08-G15) | Button Map File > History mixes twin sticks and hides saves filed under Module files | wrong-behaviour | confirmed-in-code | 08 Q15, S31 | qml/DialogJoystickButtonMap.qml:2495 | Filter by the device's module file name and all areas, as Module Setup does. |
| GL-189 (08-G18) | Auto Mapper may send two inputs to the same vJoy output | wrong-behaviour | confirmed-in-code | 08 Q7, S94, S98 | gremlin/auto_mapper.py:216-238 | Count every input in the profile and nested Map to vJoy actions (S98 is replaced). |
| GL-190 (08-G20) | Auto Mapper stops with an AssertionError on an unusual binding root | wrong-behaviour | confirmed-in-code | 08 R14 | gremlin/auto_mapper.py:228 | Replace the assert with a check that skips and reports that binding. |
| GL-191 (08-G30) | Pack output modules are imported without the vJoy device's real size | wrong-behaviour | confirmed-in-code | 08 Q18, S66 | gremlin/ui/device_pack.py:1834-1836 | Apply the vJoy limits and list what was left out. |
| GL-192 (08-G11) | Module file Before/After shows raw JSON keys | ux | confirmed-in-code | 08 Q13, S30, R15 | gremlin/ui/history_model.py:116-124 | Readable lines reusing the Device Pack rows. |
| GL-193 (08-G14) | Moving the history folder leaves old entries behind with no warning | ux | confirmed-in-code | 08 Q10, S27 | gremlin/util.py:929-937; joystick_gremlin.py:649 | Move the files with the folder, or say in Options that old entries stay. |
| GL-194 (08-G16) | Configuration row History lists the input's changes from every profile | ux | confirmed-in-code | 08 Q16, S31, S40 | qml/BindingCatalog.qml:1583 | Add the open profile to the filter; Show All widens it. |
| GL-195 (08-G27) | No running note in Device Pack and History windows | ux | confirmed-in-code | 08 Q4, S100 | qml/DialogDevicePack.qml; qml/DialogHistory.qml | Show the same RunningNote as the Auto Mapper. |
| GL-196 (08-G36) | Building the export preview zips the whole device on the UI thread at each device change | ux | needs-hands-on | 08 S49 | gremlin/ui/hardware_profile.py:1872 (peekPackDevice) | Estimate size without building the zip, or build it off the UI thread. |

### 09 Sound, speech, Options and scaling

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-197 (05-Q7, 09-G33) | Text to Speech can't be put on keyboard keys, and its input types don't list keys | ux | confirmed-in-code | 05 S10, Q7; 09 Q11, S61; test plan S-34 | action_plugins/text_to_speech/__init__.py:181 | Allow keyboard keys like Play Sound; close test-plan S-34. |
| GL-198 (09-G31) | Options shows the first voice when the saved voice is gone | ux | confirmed-in-code | 09 Q12, S59 | gremlin/ui/option.py:742-746 | Show "(default)" when the saved voice is missing or none is set. |
| GL-199 (09-G32) | No message when Windows speech is unavailable | ux | confirmed-in-code | 09 Q13 | gremlin/tts.py:47-58 | One warning in the log and in the action's feedback. |
| GL-200 (09-G36) | Action images may ignore UI scale and the grey light theme | ux | needs-hands-on | 09 Q16, R14, S75 | gremlin/ui/action_image_generator.py:78-82; qml/ColorInformation.qml:15-18; qml/Style.qml:19-20 | Check off-screen at 200% and light mode; switch to Style values if visibly off. |
| GL-201 (01-G12, 03-G28, 07-G33, 09-G37) | At 200% UI scale on a small screen, toolbar, Options, Module Setup, Calibration, Button Map, Clear Log, Auto Mapper and Device Pack cut off contents (on hold) | ux | needs-hands-on | 01 S62, S48; 03 S37, S105; 07 S99; 09 S84; AU-56 | qml/Main.qml toolbar; qml/DialogOptions.qml; qml/DialogConfigureModule.qml; qml/DialogCalibration.qml; qml/DialogJoystickButtonMap.qml; Clear Log, Auto Mapper, Device Pack windows | Make those windows fit, scroll or reflow at 200% on small screens when the user takes AU-56 off hold. |
| GL-310 (Stage 1 finding) | An axis that jumps across its range in one step sends no press or release | wrong-behaviour | confirmed-in-code | 06 S39 | gremlin/code_runner.py VirtualAxisButton.__call__ (~123-138: the release branch overwrites the forced [True, False]) | Send press then release on a jump across the range; test test_stage1_runtime.py::test_an_axis_jumping_across_its_range_presses_and_releases (xfail GL-310). |
| GL-311 (Stage 1 finding) | A setting changed within about a second of other setting writes on a first run left no History entry | wrong-behaviour | suspected | 08 S16 | gremlin/config.py History grouping; seen by journey J6 | Check against 08 S16 (several changes within about a second make one entry; a first appearance is not a change); fix if an actual change is dropped. |
| GL-312 (user, 2026-10-06) | An axis already in its range at Run sends a release when it leaves, with no press before | wrong-behaviour | confirmed-in-code | 06 S39 (user decision) | gremlin/code_runner.py VirtualAxisButton | Send no release without a press; add a test next to the GL-310 one. |
| GL-313 (Stage 1 re-check) | Auto Mapper crashes when a vJoy device is set to be read back as an input | crash-or-hang | confirmed-in-code | 08 Q7, Q9; 06 S9 | gremlin/auto_mapper.py:205-214 (_vjoy_limits uses vjoy_devices()), :243-247 (create_instance returns None) | Build the limits from output_vjoy_devices() and skip with "vJoy N is used as an input" when create_instance returns None; related GL-275. |

## 7. Text, glossary and help (one batch)

GL-018 (glossary test) goes first so the batch is guarded.

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-202 (01-Q13) | User Guide's Options topic is out of date | text | confirmed-in-code | 01 S129, S42, Q13 | qml/help_topics.js:268-279 | Match the Options layout (_LAYOUT), including all folders. |
| GL-203 (01-Q14, 03-G6) | Options text says "stub cards", "Keep the last: value..." and pickers titled "Select a File/Folder" | text | confirmed-in-code | 01 S45, Q14; 03 S72; glossary D13 | gremlin/ui/shell_option.py:29, 37; gremlin/ui/module_model.py:103; qml/ConfigGroup.qml:245, 257 | "device without a module", fix the stray colon, title pickers by what they do. |
| GL-204 (02-G5) | Help does not say mouse buttons are for macros and Listen only | text | confirmed-in-code | 02 Q5, S53 | qml/help_topics.js | Say so in Help. |
| GL-205 (02-Q2) | Device change behavior says "Disable" where it means Stop | text | confirmed-in-code | 02 Q2, S32 | joystick_gremlin.py:667-671; gremlin/ui/option.py:86; qml/help_topics.js:39, 272 | Show "Stop" on screen and in Help; keep the stored value "Disable". |
| GL-206 (02-Q12) | Device Information says "Device GUID" instead of "Device ID" | text | confirmed-in-code | 02 Q12, S94, G24 | qml/DialogDeviceInformation.qml:95; qml/help_topics.js:227 | Rename in the window and Help. |
| GL-207 (02-Q13) | No warning that HidHide control overwrites HidHide's own lists | text | confirmed-in-code | 02 Q13 | qml/DialogHardwareHide.qml:166-213 | Say that turning it on replaces HidHide's program and device lists. |
| GL-208 (02-Q15) | Developer notes don't mention python.exe gets HidHide access in source runs | text | suspected | 02 Q15 | gremlin/ui/hidhide.py (whitelist build); developer notes | Accept the behaviour; one line in the developer notes. |
| GL-209 (02-Q17) | vJoy message says "restart Gremlin-Platforms" | text | confirmed-in-code | 02 Q17, G24 | gremlin/device_initialization.py:309 | "Then restart the program." |
| GL-210 (03-Q1) | Module Setup says changes work next Run, but saved changes work at once | text | confirmed-in-code | 03 Q1, S36, S108 | qml/RunningNote.qml:18 | "Saved changes work at once." |
| GL-211 (03-Q11) | Glossary lacks Input Module Setup / Output Module Setup names | text | confirmed-in-code | 03 Q11, S37 | claude/glossary.md:13; qml/DialogConfigureModule.qml:91; qml/main_commands.js:76-78 | Add both names to the glossary (replace "Configure input module"). |
| GL-212 (03-Q12) | Help's Home topic doesn't mention Keyboard, OSC and Logical Device cards | text | confirmed-in-code | 03 Q12, S71 | qml/help_topics.js:67 | Add them. |
| GL-213 (03-Q14) | Delete File confirm doesn't say the pictures are kept | text | confirmed-in-code | 03 Q14, S62 | gremlin/ui/hardware_profile.py:865-899; qml/DialogConfigureModule.qml:507 | Say so in the confirm text. |
| GL-214 (04-G5) | Help does not say the toolbar Mode box switches the running mode | text | confirmed-in-code | 04 Q5, S54 | qml/help_topics.js:38, :210 | Add it. |
| GL-215 (04-G16) | --profile not found says the last profile opened even when there is none | text | confirmed-in-code | 04 Q16, S21 | joystick_gremlin.py:979-990 | "A new profile is open" when there is no last profile. |
| GL-216 (04-G30) | File dialog titles: Title Case vs glossary sentence case | text | confirmed-in-code | 04 gap 20; glossary N20 | qml/Main.qml:819, :870 | Confirm which wins (GLOSSARY-4 Title Case) and align. |
| GL-217 (05-G5) | Configuration list shows "Unmapped", "assignments", "Sequence"/"Empty" and sentence-case type names | text | confirmed-in-code | 05 S14, S15, Q6 | gremlin/ui/binding_catalog.py:157-185, 280-283, 304-311, 601; qml/BindingCatalog.qml:1265-1267 | "No actions"; "1 action"/"N actions"; Title Case type names from the plugins. |
| GL-218 (05-G21) | Help says "Prefercenter" but the editor shows "Prefer Center" | text | confirmed-in-code | 05 S11 | qml/help_topics.js:144; action_plugins/merge_axis/__init__.py:198 | Help reads "Prefer Center". |
| GL-219 (05-Q20) | Test plan IC-06 still says catalog Delete doesn't ask | text | confirmed-in-code | 05 Q20 | claude/test-plan.md IC-06 | Mark IC-06 superseded. |
| GL-220 (06-X1, 09-G38) | Test plan still uses Toggle / Active / Activate, Close to tray and Quit | text | confirmed-in-code | 06 G18, S1, S2; 09 Q17, S64 | claude/test-plan.md TB-02, W-04..W-09 | Reword to Run / Stop / Running / Stopped; retire tray rows in favour of TRAY-ONE. |
| GL-221 (07-G24) | Clear Photo should leave no photo; help still says "the module's picture" | text | confirmed-in-code | 07 S41, Q4 | qml/help_topics.js:332, 365; gremlin/ui/hardware_profile.py clearImage (2475); qml/DialogJoystickButtonMap.qml applyImage | Clear Photo leaves no photo; help says "Clear Photo removes the photo". |
| GL-222 (07-G25) | Help says the module file is only written by Save, but view, zoom and grid save at once | text | confirmed-in-code | 07 S29, S95, Q1 | qml/help_topics.js:349 | Say which parts are kept at once and which only on Save (after GL-173). |
| GL-223 (07-G27) | Glossary still calls Button Map Options its own window | text | confirmed-in-code | 07 Q17, S98; BM46 | claude/glossary.md:14 | Update to the tool-row pane. |
| GL-224 (07-G28) | Tracker AU-64 note says photo folders still go by the device's own name | text | confirmed-in-code | 07 S10; AU-64 | gremlin/ui/hardware_profile.py:1755, 1864, 2629-2642 | Update AU-64: only the stock-photo choice and pack export name go by name (until GL-086). |
| GL-225 (07-G29) | Test plan rows describe Button Map features that no longer exist | text | confirmed-in-code | 07 G23 | claude/test-plan.md BM-F07..08, S-24, S-22, BM-X1, BMAP2-4, BMAP2-12, BMAP2-15 | Rewrite or remove to match Print & Export and A3. |
| GL-226 (08-G9) | Glossary and help say every Restore is a new History entry | text | confirmed-in-code | 08 Q1, S39 | claude/glossary.md:58; qml/help_topics.js (History); gremlin/ui/history_model.py:258 | Input restores show at the next Save Profile; whole-profile restores write a copy. |
| GL-227 (08-G12) | History size/age limits apply only at session start; Options doesn't say so | text | confirmed-in-code | 08 Q11, S18, S19 | gremlin/history.py:342-346; joystick_gremlin.py:726-737 | Add "checked at start" to both descriptions. |
| GL-228 (08-G17) | Auto Mapper result says "mappings" and "bindings" | text | confirmed-in-code | 08 Q8, S103, R15 | gremlin/auto_mapper.py:252-257 | "Made 36 actions; 0 inputs kept their actions."; extend the glossary guard to Python result strings (GL-018). |
| GL-229 (08-G31) | Export of a device with a damaged module file says "no module file yet" | text | confirmed-in-code | 08 Q19, S51, S52 | gremlin/ui/device_pack.py:626-632 | Say it is damaged and point to Start Fresh. |
| GL-230 (08-G32) | Help and import warning say pieces "replace", but checked controls are added | text | confirmed-in-code | 08 Q3, S65 | qml/help_topics.js:92; qml/DialogDevicePack.qml:289-293, 393-397; gremlin/ui/device_pack.py:983-989 | "adds the pack's checked controls". |
| GL-231 (08-G33) | Help doesn't say opening another pack ends Undo Import | text | confirmed-in-code | 08 Q6, S81, S82 | qml/help_topics.js:94; qml/DialogDevicePack.qml:323 | Add "or open another pack". |
| GL-232 (08-G34) | No help on deleted-device backups, Delete File copies and imported backups | text | confirmed-in-code | 08 Q17, S86-S89 | qml/help_topics.js | Help paragraph on where they are and restoring via Device Pack > Import. |
| GL-233 (09-G35) | Windows scaling check box wording differs from its title and help | text | confirmed-in-code | 09 Q15, S87 | qml/OptionWindowsScale.qml:28 | "Ignore Windows display scaling". |

## 8. Cleanup (dead code, duplicates, layer and owner tidying)

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-234 (01-G3) | Same settings defined in two places | cleanup | confirmed-in-code | 01 section 7 | joystick_gremlin.py:678, 684, 704; gremlin/ui/ui_scale_option.py:21, 104; gremlin/ui/windows_scale_option.py:18; gremlin/ui/live_debug.py:562 | Define each key once (with GL-117). |
| GL-235 (01-G4, 08-G23) | History Restore reads the Configuration's private table | cleanup | confirmed-in-code | 01 section 7; 08 R6, S44 | gremlin/ui/history_model.py:307 (cfg._data) | Public Configuration accessor for a key's data type. |
| GL-236 (01-G5) | Settings core depends on UI and module code | cleanup | confirmed-in-code | 01 section 7 dependency direction | gremlin/config.py:22, 101, 261 | Inject trace, title lookup and safe write so config.py imports no UI/module code. |
| GL-237 (01-G7) | Two near-identical window scans in the second-copy check | cleanup | confirmed-in-code | 01 section 7 | joystick_gremlin.py:388, 418 | Merge into one scan. |
| GL-238 (01-G11) | Module Setup window kept outside the shared window list | cleanup | confirmed-in-code | 01 S39, section 10 | qml/Main.qml:165; qml/window_registry.js | Track it in window_registry. |
| GL-239 (02-G4) | Dead mouse "ignore our own events" filter; mixed device id type for mouse | cleanup | confirmed-in-code | 02 Q5, RB15, RB16, G4 | gremlin/windows_event_hook.py:207; gremlin/event_handler.py:504-508 | Remove the filter; mouse events use the keyboard's id type. |
| GL-240 (02-Q10) | HidHide driver calls and enumeration live in a UI file | cleanup | confirmed-in-code | 02 Q10, RB4 | gremlin/ui/hidhide.py:631-1260 | Move to a non-UI module (low priority). |
| GL-241 (02-Q11) | Xbox driver package reads DirectInput directly | cleanup | confirmed-in-code | 02 Q11, RB3 | vigem/ids.py:55-61; vigem/own_pads.py:76-80 | Route through gremlin/modules/hardware.py. |
| GL-242 (02-Q19) | Foreground-program monitor polls every second even with auto-load off | cleanup | confirmed-in-code | 02 Q19 | gremlin/ui/backend.py:252-253; gremlin/process_monitor.py | Run it only while auto-load is on. |
| GL-243 (02-N1) | Twin names, aliases, cached sticks and HidHide photo links are never cleaned up | cleanup | confirmed-in-code | 02 section 10 | gremlin/device_initialization.py; gremlin/ui/device_names.py; gremlin/input_cache.py:477; gremlin/ui/hidhide.py | Owners that prune entries for devices no longer known (with GL-132). |
| GL-244 (02-N2) | Macro, refresh-axes and Hat-as-Buttons events look like real stick input | cleanup | confirmed-in-code | 02 section 10, S44 | gremlin/macro.py:596; gremlin/input_refresh.py; hat_buttons; gremlin/osc.py:455, 507 | Mark synthetic events; hardware-only listeners ignore them. |
| GL-245 (03-G9) | Output blocked/busy log state changed from several threads without a lock | cleanup | suspected | 03 7.13, S29, S34 | gremlin/modules/output.py:35-40, 120-131, 150-177 | Put them under output._lock. |
| GL-246 (03-G19) | "Driven by" reads vJoy number and Xbox output by its own rules | cleanup | confirmed-in-code | 03 7.9, 7.10, S75 | gremlin/ui/module_model.py:262-281 | Use registry.vjoy_id_from_name and registry.is_gremlin_xbox_name. |
| GL-247 (03-G20) | Home last line re-checks claims with a different empty-claim rule | cleanup | confirmed-in-code | 03 7.11, S74 | gremlin/ui/module_model.py:1489-1491 | Drop the re-check. |
| GL-248 (03-G21) | Dead code: Xbox claim boxes in Module Setup and unused registry.find | cleanup | confirmed-in-code | 03 7.16, S32 | gremlin/ui/module_model.py:1841, 2030-2068; gremlin/modules/registry.py:372 | Remove _load_xbox_dest and registry.find. |
| GL-249 (03-G22) | UI files read the device list directly, not through modules/hardware.py | cleanup | suspected | 03 7.2; layer rule | gremlin/ui/module_model.py:1583, 1658, 2078; gremlin/ui/module_pairing.py:150, 155; gremlin/ui/hardware_profile.py:835-836, 979-985 | Decide whether device_initialization counts as input side, then route. |
| GL-250 (03-G25) | Home writes settings while loading cards | cleanup | confirmed-in-code | 03 section 10 item 24 | gremlin/ui/module_model.py:183, 1710-1711 | Write only when values change, outside the read. |
| GL-251 (04-G22) | Dead "converted" re-save branch in profile loading | cleanup | confirmed-in-code | 04 R15; AU-65 | gremlin/ui/backend.py:648, 656-657 | Remove it. |
| GL-252 (04-G31) | Leftover debug print for an invalid action node | cleanup | confirmed-in-code | 04 R16 | gremlin/base_classes.py:287 | Use logging. |
| GL-253 (04-G34) | Profile Settings lists vJoy devices from the input device cache | cleanup | suspected | 04 R13, S66 | gremlin/ui/profile.py:1121, 1127, 1220 | Get vJoy lists from the vJoy output module. |
| GL-254 (05-G13) | Selecting inputs creates editor models and empty inputs that are never freed | cleanup | suspected | 05 RB18 | gremlin/ui/backend.py:458-465; gremlin/ui/profile.py:760-765 | Give editor models an owner and lifetime; viewing does not create an input. |
| GL-255 (05-G16) | Each Map to Logical Device editor refreshes the whole Logical page | cleanup | suspected | 05 RB21 | action_plugins/map_to_logical_device/__init__.py:226 | Don't emit logicalDeviceModified from the constructor. |
| GL-256 (05-G17) | Stale comment says Xbox output passes only claimed controls | cleanup | confirmed-in-code | 05 S54 | action_plugins/map_to_xbox/__init__.py:121 | Fix or remove it. |
| GL-257 (05-RB12) | Action names and kinds kept in four copies | cleanup | confirmed-in-code | 05 RB12, RB17, S8 | gremlin/ui/binding_catalog.py:157-185; qml/BindingCatalog.qml:1267; qml/action_kinds.js | Take them from the plugins in one place (with GL-217). |
| GL-258 (05-Q15) | Input names are patched into models at import time | cleanup | confirmed-in-code | 05 Q15, RB5, S77 | gremlin/ui/action_label.py:162-168; gremlin/ui/device_names.py:8; gremlin/ui/device.py:87 | Input name as an InputItem field and model role; delete the patches. |
| GL-259 (05-Q16a) | Map to Xbox imports types straight from the ViGEm driver | cleanup | confirmed-in-code | 05 Q16, RB8 | action_plugins/map_to_xbox/__init__.py:29 | Move XboxTarget to the output module. |
| GL-260 (05-RB7) | Action and Condition data hold UI (QObject) types | cleanup | confirmed-in-code | 05 RB7 | action_plugins/merge_axis/__init__.py:353; action_plugins/dual_axis_deadzone; action_plugins/condition/condition.py:86; action_plugins/map_to_logical_device | Plain identifiers in data classes. |
| GL-261 (05-Q18) | Unused editor and catalog code still present | cleanup | confirmed-in-code | 05 Q18; C9, test plan S-03 | qml/BindingCatalog.qml:27-29, 784-889; gremlin/ui/binding_catalog.py:861, 871; gremlin/ui/profile.py:688; gremlin/ui/action_model.py:392; gremlin/ui/device.py:87 | Remove quick editor, addSequence, vjoyDevices, newActionSequence, ActionPriorityListModel, keyboard _description_from_item in one commit. |
| GL-262 (05-RB13) | Macro step type table written twice | cleanup | confirmed-in-code | 05 RB13 | action_plugins/macro/__init__.py:710, 976 | One shared table. |
| GL-263 (05-RB14) | Merge Axis and Deadzone pick-list code copied and already differs | cleanup | confirmed-in-code | 05 RB14 | action_plugins/merge_axis/__init__.py:206-302; action_plugins/dual_axis_deadzone/__init__.py:133-195 | One shared pick list. |
| GL-264 (05-RB15) | Relative-axis loop duplicated in Map to vJoy and Map to Logical Device | cleanup | confirmed-in-code | 05 RB15 | action_plugins/map_to_vjoy/__init__.py:51-193; action_plugins/map_to_logical_device/__init__.py:52-208 | One shared loop (best done with GL-048). |
| GL-265 (02-G16, 04-G23, 05-G22, 06-G24, 09-G34) | Remaining timing code uses time.monotonic/time/sleep instead of gremlin.clock | cleanup | confirmed-in-code | 02 RB1, RB2, G15; 04 R6, R7, S90; 05 Q19, RB11; 06 RB9; 09 Q14, R8; AU-62 | gremlin/windows_event_hook.py:288-289; vigem/own_pads.py (before_plug); gremlin/user_script.py:208-237; gremlin/base_classes.py:656; action_plugins/chain/__init__.py:70-77; gremlin/sendinput.py:135, 373; gremlin/audio_player.py:190; vjoy/vjoy.py:539, 806, 828, 938 | Move to gremlin.clock (after GL-002): Chain timeout and the audio loop now (user decisions); the rest when next touched. |
| GL-266 (06-G20) | Unused second Logical Device editing model | cleanup | suspected | 06 Q18, RB13 | gremlin/ui/device.py:486-543; gremlin/action_label.py:17, 31, 167 | Confirm no user by grep, then remove it and its patch. |
| GL-267 (06-N3) | vJoy keep-alive and busy retry split across two files | cleanup | confirmed-in-code | 06 S52, S54 | vjoy/vjoy.py; gremlin/modules/output.py | Move both under the output module. |
| GL-268 (07-G4) | Button Map Save raises instead of refusing when given text that is not an object | cleanup | suspected | 07 S20 | gremlin/ui/hardware_profile.py:2322-2325 | Return False when the parsed text is not a dict. |
| GL-269 (07-G12) | Two producers of "what this control does" and a second copy of mode inheritance | cleanup | confirmed-in-code | 07 RB5, RB6, S72 | gremlin/ui/hardware_profile.py:1429-1477; gremlin/ui/button_map_labels.py:70-82, 167-178 | One label producer using the runtime's mode-inheritance lookup. |
| GL-270 (07-G13) | Page size written in four places and never read back on load | cleanup | confirmed-in-code | 07 S68, Q14, RB4; BM41 | qml/VkbRigEditor.qml:153-156; qml/DialogJoystickButtonMap.qml:444-455; gremlin/ui/hardware_profile.py:2325-2331; gremlin/module_model.py:2286-2288 | One page-size constant, read on load (needed by GL-185). |
| GL-271 (07-G16) | Asking a device's photo also reloads that object's document | cleanup | suspected | 07 S11 | gremlin/ui/hardware_profile.py:2621 | Read the module file without changing the object's state. |
| GL-272 (07-G17) | Stock photos and the old qml/maps copy point to files not in the repo | cleanup | confirmed-in-code | 07 Q12; BM41 | gremlin/ui/hardware_profile.py:2629-2642; gremlin/util.py:939 | If nothing ships, remove the code and fix the BM41 note; otherwise add files to repo and installer. |
| GL-273 (07-G19) | Pictures added in a cancelled edit or removed from the map stay in the device folder | cleanup | confirmed-in-code | 07 Q11 | gremlin/ui/hardware_profile.py copyOverlay, savePastedImage, importPictureFiles; qml/DialogJoystickButtonMap.qml cancelEdit/saveEdit | Save and Cancel remove device-folder pictures no map uses. |
| GL-274 (07-G21) | Picture library keeps every photo and picture ever chosen | cleanup | confirmed-in-code | 07 Q11 | gremlin/ui/hardware_profile.py:1782; qml/OptionButtonMapLibrary.qml | "Remove unused" button in Options > Library. |
| GL-275 (08-G21) | Auto Mapper reads vJoy sizes and sticks from the raw device list | cleanup | confirmed-in-code | 08 R7, R8 | gremlin/auto_mapper.py:200, 205-214, 219; gremlin/ui/device_pack.py:1181; gremlin/output.py:188 | Use output.vjoy_layout and gremlin.modules.hardware. |
| GL-276 (08-G37) | Pack preview pictures folder in %TEMP% is never removed | cleanup | confirmed-in-code | 08 section 10 gap 29 | gremlin/ui/device_pack.py:713-733 | Remove it when the window closes and at quit. |
| GL-277 (08-G39) | Whole-profile copies written by Restore are never listed or cleaned | cleanup | confirmed-in-code | 08 section 10, S45 | gremlin/ui/history_model.py _restore_profile | Give them an owner: mention in help or list/clean them. |
| GL-278 (09-G30) | Sound queue shared between threads without a lock | cleanup | suspected | 09 R9, S49 | gremlin/audio_player.py:156, 163 | Lock _play_list or use a thread-safe queue. |
| GL-279 (09-G40) | Unused state machine file and unused OSC model methods | cleanup | confirmed-in-code | 09 Q19, R15 | gremlin/fsm.py; test/unit/test_fsm.py; gremlin/ui/osc_device_model.py:112, 183 | Remove fsm.py and its test now; the OSC methods with OSC work. |
| GL-280 (09-G41) | Shared dialogs and widgets have no owner or direct tests | cleanup | confirmed-in-code | 09 section 10, Q20 | qml/TextInputDialog.qml; qml/DismissibleDialog.qml | Accept the leftover table; add direct TextInputDialog tests. |

## 9. Parked (OSC)

Not worked on until the user picks OSC up. GL-281 is the first to take when that happens.

| ID(s) | Title | Severity | Status | Spec / tracker | Files | Fix |
|---|---|---|---|---|---|---|
| GL-281 (02-P1, 06-OSC1, 09-G7, 09-G5) | OSC opens a LAN port on every Run even with no OSC inputs, and stays open after Listen is cancelled | safety | confirmed-in-code | 02 section 10; 06 section 10; 09 S8, S20, S1, Q5, Q10; APP5, APP13 | gremlin/osc.py:40-75, 62-66, 312-343; gremlin/code_runner.py:362, 390 | Start OSC only when OSC inputs exist; default 127.0.0.1; one notice on failure; cancel_listen stops the listener when no Run; drop packets unless running or listening. |
| GL-282 (01-G10) | Warning logged at every start when the PC's IP list changes | ux | confirmed-in-code | 01 S103 | joystick_gremlin.py:775-789; gremlin/config.py:300-305 | Decide when OSC is picked up. |
| GL-283 (02-P2, 03-G30, 09-G13) | OSC card menu, Module Setup and page empty-state text talks about sticks | text | confirmed-in-code | 02 section 10; 03 S53; 09 S34; AU-58 | qml/DialogConfigureModule.qml:359-364; qml/OscDevice.qml; OSC card menus | OSC-specific empty-state text (add an address or Listen). |
| GL-284 (03-G29, 09-G18) | OSC claims in Module Setup do nothing at Run | wrong-behaviour | confirmed-in-code | 03 S15; 09 Q4, R1 | gremlin/ui/module_model.py:1896-1931; gremlin/modules/runtime.py:22-27 | Keep OSC outside the module system; Module Setup shows only friendly names, no claim boxes. |
| GL-285 (09-G1) | OSC input port has three different defaults and clashes with the output port | wrong-behaviour | confirmed-in-code | 09 S6, S5, R5, Q1; B15 | gremlin/osc.py:29; gremlin/ui/osc_option.py:148; joystick_gremlin.py:780 | One constant each: input 8000, output 9000. |
| GL-286 (09-G2) | OSC Output address is a setting nothing uses | ux | confirmed-in-code | 09 S9, Q3 | gremlin/ui/osc_option.py; qml/OptionOscOutputHost.qml; joystick_gremlin.py:570-809 | Hide it (and its help) until something sends OSC. |
| GL-287 (09-G3) | After adding an OSC axis the wrong input is selected and gets the actions | wrong-behaviour | confirmed-in-code | 09 S13, S12; APP4 | gremlin/ui/osc_device_model.py:124, 137, 179, 213 | Select the new input by its own index. |
| GL-288 (09-G4) | OSC address edit accepts blank and slash-less; refuses duplicates silently | wrong-behaviour | confirmed-in-code | 09 S25; APP11 | qml/OscDevice.qml:40-55, 135-151; gremlin/osc.py:173-185 | allowBlank false, leading "/", unique; say why a duplicate is refused. |
| GL-289 (09-G6) | Listening for OSC box has no Stop button | ux | confirmed-in-code | 09 S21; APP17 | qml/OscAddDialog.qml; gremlin/ui/osc_settings_info.py | Add a Stop button. |
| GL-290 (09-G8) | OSC Add dialog Change, Message + data and Trigger delay do nothing | wrong-behaviour | confirmed-in-code | 09 S16, Q2; B16 | qml/OscAddDialog.qml:58-70, 88-91, 162-180, 260; qml/OscDevice.qml:88-90 | Hide the controls that are not built. |
| GL-291 (09-G9) | OSC import suffixes C, E, B, BNP don't give the promised types | text | confirmed-in-code | 09 S23, Q2; B17 | gremlin/ui/osc_device_model.py:48-50; qml/OscImportDialog.qml:65 | Dialog text matches what import does (A axis, else button). |
| GL-292 (09-G10) | OSC starts a raw thread per packet and reads settings per packet | cleanup | confirmed-in-code | 09 R7, S43; AU-67 | gremlin/osc.py:236-243 | Single-threaded server via gremlin.threads; cache flags. |
| GL-293 (09-G11) | Turning OSC Enabled on while running does not start listening | wrong-behaviour | confirmed-in-code | 09 S4 | gremlin/osc.py:430-433 | sync_bind starts the listener when enabled while running. |
| GL-294 (09-G12) | OSC auto-release timers survive Stop and later presses | wrong-behaviour | confirmed-in-code | 09 S39, S40, S1; AU-116 | gremlin/osc.py:495-501 | Cancellable timers per input; cancel on new press and at Stop (map 3). |
| GL-295 (09-G14) | OSC dialogs say "Ok" and put it before Cancel | text | confirmed-in-code | 09 S35, S87; E1 | qml/OscAddDialog.qml:257; qml/OscImportDialog.qml:72 | "OK", same order as other dialogs. |
| GL-296 (09-G15) | OSC list change signals point one row past the end | cleanup | confirmed-in-code | 09 S10; AU-65 | gremlin/ui/osc_device_model.py:134, 228, 257 | Use rowCount()-1 (or reset the model). |
| GL-297 (09-G16) | Deleting an OSC row removes it and its actions with no Undo | data-loss | confirmed-in-code | 09 Q6, S26, S27 | qml/OscDevice.qml:153-164; gremlin/ui/osc_device_model.py:234-246 | Undo for OSC add/rename/delete/clear like the Logical Device page. |
| GL-298 (09-G17) | OSC tester README describes the old setup | text | confirmed-in-code | 09 S87 | tools_osc/README.md | Update or retire it. |
| GL-299 (09-G19) | OSC Sort is one-way and forgotten | ux | confirmed-in-code | 09 Q7, S28 | gremlin/ui/osc_device_model.py; qml/OscDevice.qml:203-206 | Toggle A-Z / by type and number, remembered. |
| GL-300 (09-G20) | Missing python-osc error shows developer instructions to users | text | confirmed-in-code | 09 Q9 | gremlin/osc.py:411 | "OSC is not available in this build"; log the detail. |
| GL-301 (09-G21) | OSC Options descriptions use old words and name Companion only | text | confirmed-in-code | 09 Q18, S87 | joystick_gremlin.py:772, 782 | "while the profile runs"; "the port your OSC sender sends to". |
| GL-302 (09-G22) | OSC replaces the program-wide settings setter to watch three keys | cleanup | confirmed-in-code | 09 R2 | gremlin/osc.py:265-286 | Subscribe to a settings-changed signal instead. |
| GL-303 (09-G23) | OSC modules patch other classes' methods at import time | cleanup | confirmed-in-code | 09 R3, R4 | gremlin/osc_bulk.py:20-22, 62-64; gremlin/action_label.py:166; gremlin/osc_persist.py:94-121; gremlin/ui/osc_device_model.py:53-70 | Fold the patches into the classes; one label/index implementation. |
| GL-304 (09-G24) | OSC page hard-codes the OSC device id | cleanup | confirmed-in-code | 09 R6 | qml/OscDevice.qml:35 | Read the guid from the model. |
| GL-305 (09-G25) | OSC listener stop can wait forever if the server never started | crash-or-hang | suspected | 09 R11, S1 | gremlin/osc.py:251 | Bounded shutdown, only when serving. |
| GL-306 (09-G26) | OSC host lookup can freeze the screen on slow networks | ux | suspected | 09 R12 | gremlin/osc.py:40-60 | Off the main thread or with a timeout and cache. |
| GL-307 (09-G27) | No OSC tests beyond the input gate | cleanup | confirmed-in-code | 09 S36-S48 | test/unit | Tests for S36-S48 when OSC is picked up. |
| GL-308 (09-G28) | Damaged OSC section might stop a profile from opening | crash-or-hang | needs-hands-on | 09 S48 | gremlin/profile.py:1306-1324; gremlin/osc.py (OscDevice.create) | Skip/log duplicate addresses on load instead of raising. |
| GL-309 (09-G39) | User Guide has no OSC topic | text | confirmed-in-code | 09 S86 | qml/help_topics.js | Add one when OSC is picked up. |

## Hands-on checks needed

Things only the user can check on a real screen or PC. Items marked "off-screen first" can be tried with the off-screen UI check before asking the user.

1. GL-111: with Minimize to tray on, does File > Exit or tray Exit quit, or only hide the window?
2. GL-007: tray behaviour (Minimize to tray, X hiding, the one-time balloon, tray Exit, tray label/icon after Run/Stop).
3. GL-122: with a throttle resting at about 80%, press Run without moving it. Does vJoy show centre until it moves? (Shows whether dill.dll already sends starting values.)
4. GL-126: keep the program busy (e.g. a large profile load) while pressing bound keys. Do key bindings stop until restart?
5. GL-003: on a PC or VM without vJoy, open a profile that uses Map to vJoy.
6. GL-164: add a key on the Keyboard page and try to give it its first action.
7. GL-053 and GL-016: the test-plan hands-on rows HELP-BUG-HANDS-ON, SAFE-4-HANDS-ON, MACRO-DELAY-HANDS-ON, WORKFLOW-HANDS-ON, PS-02..04, SW-01..03.
8. GL-184: Copy Button Map with mirror, then one Undo. Back to the old map, or an unmirrored copy?
9. GL-041: with large history files, focus the History window and Restore. Does the program freeze?
10. GL-196: in Device Pack, choose a device with large photos. Does the window stall?
11. GL-201: 200% UI scale on a small screen: toolbar, Options search, Module Setup Save, Calibration Save All, Button Map, Clear Log, Auto Mapper, Device Pack (on hold, AU-56).
12. GL-144 (off-screen first): type a friendly name such as "Fire" in Keyboard Module Setup. Do F, I, R, E get ticked?
13. GL-200 (off-screen first): action summary images at 200% and in the light theme.
14. GL-308 (parked, OSC): a profile with two OSC inputs sharing one address.
