# To do

What is open, in one list. Each item is done through the normal process
(`claude/system-maps.md` "How we work"; spec first, `.claude/CLAUDE.md`
change control and working standard). "Add to the to-do" means recording an
item here only; nothing else changes until the work starts.

Details for many items live in `claude/gap-list.md` (GL ids) and the spec
pages in `claude/program-map/`. Finished work is under "Done" at the end;
older text is in git history.

## Next up

1. **Limit the UI scale to 175 %** (user, 2026-10-07; replaces AU-56 /
   GL-201). 175 % is the highest scale the window tests confirm keeps every
   control in view; 200 % cuts contents off on small screens. When done
   (spec first): spec 09 S81 (slider 70–175 %) and S84 (replaced), the AU-56
   notes on spec pages 01/03/07/09, GL-201 and the tracker marked replaced,
   a decision row; code `gremlin/ui/ui_scale_option.py` SCALE_MAX 200 → 175
   (a saved 180–200 is read as 175 through the existing clamp);
   test_main_window_fits and test_tool_windows_fit check 175 instead of
   200; a test that a saved 200 becomes 175 and the slider stops at 175.

## Hands-on checks

5. **Program-run part done 2026-10-07** (e50c4ed8, results in
   `claude/hands-on-results/`, page https://claude.ai/artifact/XDkvyR895esB8smH439BWD):
   247 rows, 194 pass, 20 fail, 6 blocked, 27 need a person. Left:
   - **5a, 5b and the 10 smaller findings: DONE 2026-10-07** (commits
     27d99d8b..93e9a615; decisions b5978ec1, b86b55a5, 7860c829, c58df6f0).
     Kept below for reference.
   - **5a. Fix the 15 clear gaps** (program differs from spec), spec first
     per row: 05 S105 page jumps device on unplug; 05 S83 vJoy Relative never
     moves; 04 S80 Swap Bindings buttons off-window; 02 Q6 Device
     Information deviceType has no getter; 03 S101 Calibration wrong stick;
     03 S114 highlight on after Run/Stop; 03 S40 Module Setup switch dropped;
     01 S71 New asks order; 07 S73 chips not refreshed; 05 S44 "Off" label
     late; 03 S78 no counts without module file; 08 Diagnostic logs not in
     History; 04 Q19 / GL-153 unsaved check slow; 06 S54 keep-alive ~120 s;
     09 Q16 / GL-200 action images unscaled.
   - **5b. User decisions:** GL-122 throttle centre at Run (dill sends no
     starting values); held vJoy buttons stay pressed after Stop/quit
     (06 S17); 05 S105 vs 02 S28 (unplugged axis centre or last value);
     07 S80 template export text; 08 S97 note; 01 S44 OSC host (parked).
   - **5c. Person-only checks:** the "Needs a person" sections of each results
     file (real sticks, sound, native dialogs, network/update, fresh exe).
   - **5d.** Catch-up plan rows for pages other than 02/06 were not run.

## Improvement ideas (2026-10-07; each goes through the spec first)

Suggested order: 12 → 6 → 7 → 13 / 16 → rest.

6. Problems panel: show validate() findings in the app (unused actions,
   missing Logical controls, damaged module files, two inputs on one vJoy
   output) with Go to.
7. Profile recovery copy after a crash (GL-029, approved, deferred).
8. Test panel without the game: press a binding on screen, see what
   vJoy/Xbox gets.
9. Find in profile: every use of a key, vJoy output, mode or action.
10. Copy a mode or an input's bindings from another profile.
11. Save diagnostics: one local zip of logs, settings, device list.
12. Rule checks (validate) from report to fail (Stage 2 leftover).
13. **SHELVED by the user 2026-10-07.** Startup time: load rarely used pages on first open; a startup-time test.
    Measured before shelving (off-screen, S13; scripts in `.agent-logs/handson/S13/`): window built and drawn
    ~0.9 s after start-up begins, whole process ~2.0 s (empty profile); the user's 386 KB profile (204 inputs,
    4 sticks + 3 vJoy) ~0.92 s / ~2.1 s. Removing single parts of Main.qml changed it by less than run-to-run
    noise. Off-screen skips HidHide and the keyboard/mouse hooks (their real cost not measured).
14. What's new in Check for Updates (release notes before updating).
15. Coverage report; fill the riskiest gaps.
16. Faster CI: cache the venv and compiled QML (with item 2).
17. Keep shrinking hardware_profile.py, module_model.py, binding_catalog.py.
18. Screenshot tests at several UI scales (70–175 %).

## Carried-over fixes (one at a time, spec first)

19. **GL-254** Viewing a key on the Keyboard page creates an empty input
    (needs a detached draft input in ui/profile.py + Library).
20. **GL-257** `qml/action_kinds.js` keeps its own action-type table.
21. **GL-260** Condition editor: data and UI (QObject) mixed — a redesign.
22. Idea: `output.write_vjoy` / `write_xbox` refuse writes when no Run is
    on (today it holds only because every sender stops at Stop).
23. A renamed stick keeps its card order slot but loses its saved card size
    and stack (keyed by name slug).
24. About 170 fixed `qWait` calls left in the off-screen window smoke
    scripts (print_export, button_map_*, usability_smoke); fix as those
    areas are touched (AU-119 leftover).
25. Calibration's axis graph (`gremlin/ui/device.py` ~862, 881) still reads
    `time.time()`, not `gremlin.clock` (GL-265 leftover).

## Planned features (need the user's decisions)

26. **BM41 – A bigger page for the Button Map.** The page (32000 x 18000
    page units, `worldPageW/H` in `qml/VkbRigEditor.qml`; `pageW/pageH`
    saved by `gremlin/ui/hardware_profile.py`, one `PAGE_SIZE` since batch 3)
    grows so there is more room around the photo; the photo frame (inner
    page 24000 x 13500, `innerPad*`) keeps its size, centred. Every
    position is a fraction of the page (`fx`, `fy`, `rig_coords.js`), so all
    of them change meaning. To do:
    - New page size (16:9 kept) and paddings; `photoWell` follows.
    - Zoom-in limit from 8x to about 10x (the page and photo look ~23%
      smaller at the same zoom).
    - Rulers 0-100 over the new page; grid sizes keep their page units.
    - No built-in maps or stock photos ship (07 Q12); convert only the
      layouts the tests use, and redo the golden images and layout tests.
    - Exports: the print area and Scale unaffected; a whole-page export
      just has more margin.
    - Open questions: (1) 30% per side (about 70% more area, recommended)
      or 30% more area (about 14% per side)? (2) The user's own maps: the
      program converts maps with the old page size as they load
      (recommended), the user re-places them, or a one-time conversion of
      their files (only with their go-ahead, on a backup).
27. **GL-270** Read the page size back on load (comes with BM41).
28. **GL-274** Picture library "Remove unused" button (D-07-GL274-LATER:
    design what "unused" means first).
29. **GL-186** New draw shapes: Plus, Radial ring, Named Card.

## Test housekeeping

30. Find the test that leaves a different EventListener instance in place
    than the one InputModuleRuntime connected to (seed 572578; partner
    test_twin_devices::test_each_twin_has_its_own_card creates the
    runtime). The live-map test in test_final_07 now connects the runtime
    to the current listener itself.
31. Log noise in tests: "No parameter with key ('global','internal',
    'twin-device-names')".
34. Order leak: `test_batch2_b7::test_restore_applies_logs_and_ui_scale_at_once`
    run straight before `test_history_recording::test_settings_the_user_chooses_are_kept`
    makes the latter see an extra settings entry (pre-existing; a flush in
    b7's finally did not fix it).
35. Timing flake: `test/action_interaction/test_double_tap_tempo.py::test_single_tap_long`
    failed once under the 6-part load, passed 3/3 alone; wait for the result
    instead of a fixed time (as cc3b49f3 did for the keyboard tests).
36. **DONE 2026-10-07 (31f05950, CI green 37687912233).** Listen / macro Record switch input highlighting directly
    (`gremlin/ui/util.py` ~199, 287, 295, 384, 419), outside the Backend's
    holder set (03 S114 fix): stopping Listen with Calibration open could turn
    highlighting back on. Move them onto the holders.
38. Local-only crash: replaying CI's unit-1 order (seed 394220, CI file set) in ONE pytest process on
    the user's PC hits "Windows fatal exception: access violation" in
    `test_device_reconnect.py::test_auto_mapper_keeps_its_ticks` (#724), during pytest-qt event
    processing. Older than today's Auto Mapper code (same at 870c98dc); CI passes that order; the normal
    6-part run passes. Likely a real driver on this PC plus an earlier test. Investigate when convenient.
37. Person checks from the fixes: your 1,172-action profile no longer
    stutters while idle (Q19); after a stick is re-plugged, actions read its
    last value until it moves (D-05-UNPLUG-CENTRE note).

39. PySide6 6.12.0: CI picked it up on 2026-10-08 (no poetry.lock in the repo) and 24
    tests that start the program off-screen crashed (access violation, exit 3221225477),
    plus menu differences (test_menus, test_button_map_window), runs 37754952665.
    pyproject.toml holds PySide6 below 6.12 until we find what changed and fix it.

40. Retire the Device Pack window once the Device Library is in and used
    (user, 2026-10-08): the Library saves, exports, imports and copies packs;
    decide what of Device Pack's fine-grained piece choices (map view, print
    settings) to keep. Spec change first (08 S49-S85).
41. Compare two saved setups in the Device Library with History's
    before/after view (user, 2026-10-08). Design first.

42. Test teardown hang (found 2026-10-08, HG): one pytest process running
    test_data_safety.py::test_a_profile_with_an_unknown_action_type_opens_and_keeps_it
    with a Delete Device test from test_stage1_history_pack.py passes, then never
    exits (native teardown after atexit; no Python thread left). Same on the code
    before the Device Library, and EventListener().terminate() doesn't help.
    run_tests.py parts end anyway, so full runs and CI pass. Find the native cause;
    meanwhile arm a faulthandler deadman at the end of pytest_unconfigure.
    Same family: Home models (ModuleListModel) made by tests are left alive and
    refresh during later tests, hitting their stand-ins (LW swap fake 2026-10-08,
    test_diagnostics_zip on CI run 37853647126). Fixed the two fakes; the real fix is
    test fixtures that delete the models they make (or a conftest teardown).

43. Exit-hang check (user go 2026-10-08, after the Device Library is committed):
    (1) test-plan.md rule: a run must end within 20 s of pytest's summary, else it is an
    EXIT HANG (reported with part and files, never passed/slow) + batch checklist line;
    (2) run_tests.py: after a part's summary wait <= 20 s, then report EXIT HANG, list
    its files, dump stacks, end it; a WARNING (summary + CI annotation) until to-do 42 is
    fixed, then a failure; (3) conftest pytest_unconfigure arms faulthandler (20 s, dump
    + exit); (4) agent contract + lead watcher report exit hangs; (5) memory note.

44. Tests must never touch the real vJoy driver (user, 2026-10-08). The PC blue-screened
    (0x3B SYSTEM_SERVICE_EXCEPTION in vjoy.sys 2.1.9, 2019; dump analysed with WinDbg:
    AV_vjoy!unknown_function at vjoy+0x4bc3) while stuck test processes were being
    killed. Add a check at test start-up/teardown: if the real vJoy library
    (vJoyInterface.dll) is loaded or the vJoy device is opened in a test process, the
    test fails and names itself. Find and fix any test that reaches it. Look at it with
    to-do 42 (exit hang may be vJoy unloading) and 43 (exit-hang check). Until done:
    one test process per agent, no kill-and-retry loops, the hanging pair off-limits.
    The vJoy driver version itself is the user's decision.
    Decision 2026-10-08 (user): integration tests are opt-in for real vJoy. Normal runs
    (full run, CI) use the stand-in vJoy; a separate, clearly named command runs them
    against the real vJoy only when asked, one process, never killed mid-run.
45. Button Map canvas editor into the shared Rename box (parked by the user 2026-10-08,
    D-01-CANVAS-EXEMPT). Plan: RenameField gets a row limit (Shift+Enter adds a row; chips 2),
    a per-place empty rule (keep / default label / allow empty) and a plain canvas look; the
    canvas keeps placing it over the chip (chipScreenRect, rotation, font size). Text boxes and
    table cells too (user to decide). Also the Layers panel rename (kept on its own box; its empty
    name resets to the default, like chips). Add a "click on another control saves once" check.
46. DONE 2026-10-08 (RG flake fix 4c9ee389; UD one undo step per command, S55): test_rig_editor_golden flakes on CI only (histAt one short: callout, photo_look; runs
    37861168239, 37863448848). Fixed 2026-10-08 (RG): the harness ends undo runs on the
    condition (stepPauseMs/stepWaiting), no fixed waits. Next (user go 2026-10-08, S55 gaps):
    (a) a waiting nudge/photo/colour run merges into the next command's undo step if it
    comes within 400 ms: push the run's own step first (session_r, callout goldens change);
    (b) Add callout makes two undo steps (rig_callout.js addCalloutFor: addDrawFree + bump);
    (c) button_map_fixes_smoke.py nudge test depends on 5 nudges within 400 ms.
47. Test race (found 2026-10-08, full run seed 124841; passed on rerun): test_stall_detection.py's
    inner pytest runs failed at collection with FileNotFoundError on a %TEMP%\gremlin-pack-*
    folder another test removed meanwhile; test_final_01.py::test_s44 failed in the same run
    (cause not logged). Stall part DONE 2026-10-09 (inner runs get their own pytest.ini/rootdir/confcutdir). Still: find s44's cause.
    s44 again 2026-10-09 (full run, unit-3): "No parameter with key ('global', 'general',
    'log-when-not-responding') exists" - an earlier test leaves the Configuration without that
    setting registered (order-dependent; passes alone). Find the test that resets it.
    Also order-dependent 2026-10-09 (pass alone): test_device_library_FX2_fixes::
    test_a_twins_pack_lands_under_that_twin, test_handson_F6_log_level_history::
    test_diagnostic_logs_from_options_is_recorded_and_restored.
    CI-only stall 2026-10-09 (run 37926996958, seed 134804): test_stage1_modules::
    test_module_setup_cancel_puts_the_old_picture_back stalled 10 s waiting on the event
    handler thread (passes locally in 1.5 s). Watch; dig in if it repeats.
    Also (2026-10-09, DL-tool): test_final_01::test_s44_a_switch_is_saved_and_announced_when_changed fails after test_device_library_DD_menus in one process (GremlinError: no parameter ('global','general','log-when-not-responding'), gremlin/watchdog.py); passes alone. Predates today.
48. vJoy loopback stand-in for the integration tests (VG idea, user 2026-10-08: to-do).
    Today test/integration (219 tests) skips unless run_tests.py --real-vjoy, and on CI it
    always skipped (no vJoy there). A stand-in vJoy that records what the program writes
    (axes, buttons, hats per vJoy device) and feeds it back as the matching joystick input
    through test/fake_hardware.py (FakeDill events) would let them run in every normal run
    and on CI without the driver. Real-vJoy runs stay opt-in.
49. Calibration: the "Raw" value box (qml/DialogCalibration.qml ~353) accepts typing but
    saves nothing; it should be read-only (found by LT-windows 2026-10-08). Check the
    calibration spec page first.
50. Silent test-process death (2026-10-09, full run, unit-3): the part ended about 60 s in with
    no summary and no error, last at test_device_library_GC_guide.py::test_the_delete_topic_
    follows_the_states (passes alone; same-seed rerun all green). Looks like a native crash;
    see 38. If it happens again, capture the exit code and a faulthandler dump for the part.
51. Device Library ideas (2026-10-09, not started): drag a saved setup onto a stick row to start
    Copy to Another Stick; sort the device list by name / last seen / saved setups (View, remembered);
    highlight the search match in names and descriptions.
52. AFTER THE 1.0.30 RELEASE (user 2026-10-09: remind me): streamline shared pieces. First the
    destructive pair: DangerButton (one red button) + ConfirmDialog / Confirm.ask (names what goes,
    red go button, Cancel default, Enter/Esc cancel, "History can put it back" or "can't be undone");
    move every delete/clear question onto it (Library, History Clear, Delete Device, Delete File,
    Button Map, Manage Modes). Then 1 shared search box (from HelpSearchBar) and 2 shared message line
    (Library's, with Undo link). Later: section divider/heading, empty state, file/folder picker that
    remembers folders, shared Undo/Redo bar. Estimates: pair ~30 min (3 agents), 1+2 ~30 min.
    Sighting 2026-10-09 (CI run 37979393055, seed 759318): stage1_button_map_smoke 'outside' part blocked in
    QMetaObject.invokeMethod(root, "buttonMapWindow") (smoke line 153), no Python frame above; passes locally (39 in 42 s).
    test_stage1_button_map._run now keeps the whole stall report. Next if it repeats: faulthandler C-level dump.

53. QUEUED (user 2026-10-09: do all 3 passes, before the 1.0.30 release): Help gap fill from the
    08:53 audit (all 10 spec pages vs qml/help). Pass 1: fix 6 wrong items (mode bar not "on the
    toolbar"; auto-load on "comes to the front"; Text to Speech buttons only; Device Library menus
    "left out" not greyed; Map to Xbox offers only fitting targets; Undo Delete Mode needs a spec line,
    ask the user). Pass 2: ~12 new topics (safety net: recovery copy, unfinished actions / Save
    without them, missing files; Treat as; what Stop releases; the tray incl. memory saving (01 S87);
    Clear History + Before/After + Previous/Next change; command-line options; the Help window itself
    (S137, S138); Button Map unplugged/damaged; Device Pack refusals; card drag/resize; mode rules).
    Pass 3: ~55 partly covered topics. 5 agents, one chapter file each; claude/help-style.md.
    Estimates: 10 + 30-40 + 30 min.
54. PLANNING (user 2026-10-09): "Show me" links in Help that open or point at the thing a topic
    names (a menu, a window, a setting). Discussion in progress; no code.

55. AFTER THE 1.0.30 RELEASE (user 2026-10-09: build it after the release). GAP (found 2026-10-09 by HW-config): 04 S94 profile recovery copy (Q14, approved 2026-10-06:
    copy of unsaved profile edits about every minute, Restore / Discard / Not now on next open or
    after a crash, removed on Save / Discard / clean close) is not in the program. Not in Help until
    built. (09 S61 reworded to buttons and keys, user approved 2026-10-09.)
    UDM edge case: a deleted mode's own Change Mode action naming a mode renamed since comes back
    with the old name (not covered).

56. Spec vs program, found by the Help writers 2026-10-09 (small; not fixed): 03 S46 Module Setup Save
    while unplugged says "...to save its setup..." when the stick is unplugged after opening (spec:
    "Plug in <device> to change its setup. Nothing was saved."; gremlin/ui/module_model.py ~1900,
    ~1951); 03 S103 a calibration with lowest above highest gets "...lowest and highest values are the
    same"; 08 S104 spec spells "Previous change"/"Next change", buttons say "Previous Change"/"Next
    Change" (glossary Title Case); 05 S59 "Reuse" never appears on screen; 07 S12 Button Map status
    line on a refused save into a damaged file says only "Not written..." (check the dialog).

57. DONE 2026-10-09 (with the shared-pieces batch) (user 2026-10-09): show the program version in the main
    window title bar, e.g. "test profile.xml - Gremlin-Platforms R1 1.0.30" (spec 01 S57 to update).

58. Button Map Undo bar has no "Last change:" text: the editor's history steps carry no names (B-map
    2026-10-09). Name the steps where they are recorded (rig editor), then bind UndoBar.lastChange.

59. DONE 2026-10-09 (D-04-LD-FILE; the Logical Device stands alone: own module file shared by all profiles, permanent ids, profile version 15). Open question (user 2026-10-09: decide after using it): should every built-in row (Keyboard, OSC, Logical Device) get the same Library menu, including Import? Original item: the Logical Device in the Device Library's
    Built-in inputs section, beside Keyboard and OSC: Save to Device Library, Restore, Export of its
    controls, names, groups and actions. Needs the Library's save/restore/export to handle the
    Logical Device's data (~30-40 min). Spec 10 S6 and the class table's library_builtin change.

60. FUTURE REDESIGN (user 2026-10-09: to-do for now, a full future redesign): "the pack is the new
    profile". Every device, internal and external, is a modular item with its own files: input/setup,
    actions, and wiring as separate items. A pack (manifest) picks the items plus the glue (modes,
    startup mode, game/auto-load, scripts) and replaces the profile. Import and export of items and
    packs are the in/out path. Open questions: modes owned by the pack (missing-mode fix), shared item
    vs copy ("used by N packs"), clashes on the same input, History/Undo per item and pack, lossless
    migration of existing profiles. Staged: A Logical Device own file (DONE 2026-10-09 with to-do 59), B device actions as
    items, C wiring as items, D pack manifest + migration. Several days.

61. QUESTION (user 2026-10-09: to-do for now, new feature, decide later): should the Device Library
    always list the built-ins (Keyboard, OSC, Logical Device), even with no module file and no saved
    setups? Today a built-in gets a row only once it has a file or a saved setup
    (gremlin/device_library.py _modules ~645, used ~832), while Home always shows the Logical Device card
    (03 S71) and built-ins are always present (03 S90a). Suggestion: always list them in Built-in
    inputs with an empty line ("Nothing saved yet. Set it up on its page, then Save to Device Library,
    or bring one in with File > Import Device Pack..."), Save greyed until there is something to save;
    display only, nothing created on disk. Spec addition to 10 S6. ~10-15 min + full run (agents:
    Library rows py, empty line QML, spec/Help, one test). Found by LIB-audit; tracker T-lib-builtin-no-file-row.

62. OSC idea (user 2026-10-09: to-do): OSC in conditions and macros. Today an OSC condition always reads
    "not present" (input_cache has no OSC device); macros can't capture OSC. ~20 min.
63. OSC idea (to-do): sender allow-list. Accept OSC only from chosen IP addresses (shared networks).
    Setting in OSC's Module Setup Server section; travels with packs. Small.
64. OSC idea (to-do): per-input axis shaping on the OSC input itself: invert, deadzone, curve, before
    any action.
65. OSC idea (to-do): address patterns. OSC wildcards (`/fader/*`, `?`, `[..]`, `{a,b}`) so one input
    covers several controls.
66. OSC idea (to-do): import a TouchOSC layout (.tosc) to create all its controls as inputs with the right
    modes.
67. OSC idea (to-do): OSC from user scripts. Scripts can send and receive OSC (script API).

68. OSC (to-do, user 2026-10-09): feedback from action states (e.g. a toggle action's on/off) as a feedback source.
69. OSC (to-do): encoder acceleration (bigger steps when the knob turns fast).
70. OSC (to-do): OSC inputs in the live Input Viewer, like stick inputs.

## On hold / parked (user's choice)

32. **N22** – Inconsistent controls in action editors (on hold).
33. **OSC** (parked 2026-10-02; **picked up 2026-10-09**: decisions D-09-OSC-FILE, D-09-OSC-INPUT, D-09-OSC-FAULTS, spec 09; being built in this batch):
    - **B15 – SUPERSEDED 2026-10-09 (D-09-OSC-FAULTS): input 8001 (intended, adjustable), output 8000, one value each (09 S6).** Default ports clash and disagree. The program listens on
      8000 when nothing is set (`gremlin/osc.py` `DEFAULT_PORT`), Options
      shows 8001 (`gremlin/ui/osc_option.py` `OscInputHostModel.port_default`),
      and output also defaults to 8000 (`DEFAULT_OUTPUT_PORT`). Suggested:
      input 8000, output 9000 (the usual OSC convention), one constant used
      everywhere.
    - **B16 – DONE in the 2026-10-09 batch (D-09-OSC-INPUT): per-input settings built (09 S16, S38-S41).** OSC Add has controls that do nothing. "Change" is saved as
      Axis; "message vs data" and "Trigger on message" with its delay are
      never passed on (`qml/OscAddDialog.qml`, `qml/OscDevice.qml` only
      sends the address and Button/Axis). The backend has no per-input
      settings for these; auto-release and its delay exist only as global
      options. Choose: build per-input support, or hide the controls until
      it exists.
    - **B17 – DONE in the 2026-10-09 batch (D-09-OSC-INPUT): real suffix types, E = button with a note (09 S23).** OSC import promises change and encoder types. Import turns
      C and E suffixes into plain axes (`gremlin/ui/osc_device_model.py`
      `_parse_import_line`), while `qml/OscImportDialog.qml` says otherwise.
      Goes with B16: real types, or fix the text.

## Notes kept for reference

- `test/integration/conftest.py` `_neutral_vjoy` resets the real vJoy device
  between modules (the integration tests already drive vJoy; they skip while
  the user's Gremlin is open). On CI 71 integration tests skip (no vJoy) and
  the rig golden pixel comparison skips.
- `gremlin/validate.py` PROFILE-UNUSED-ACTION also fires for new actions open
  in a pane and for actions kept for Undo (a warning only; matters for
  item 12).
- `import_module_file` says "That file could not be read." for a JSON file
  whose top level isn't an object.

## Done

- [x] **Item 2: CI on one branch only** (2026-10-07, c3743f47): `ci.yml`
  runs on pushes and pull requests to `Gremlin-Platforms` only.
- [x] **Item 3: Button Map exports in the background** (2026-10-07,
  8cf783dd; spec 07 S101, D-07-EXPORT-BG): `saveAreaAsync` on a
  `gremlin.threads` worker, `areaSaved` on the main thread, Export buttons
  disabled with "Exporting…" while one runs.
- [x] **Item 4: Old "CI Tests" workflow removed** (2026-10-07, c3743f47:
  `python-test.yml`).
- [x] **History Before/After highlights the deltas** (2026-10-07, f505f776;
  spec 08 S104, D-08-HISTORY-DIFF, D-08-HISTORY-SELECT). CI green.
- [x] **Signed installer** — won't fix (D-REL-UNSIGNED, 2026-10-07).
- [x] **AU-56** (200 % cuts contents off) — to be replaced by item 1.
- [x] **One-time catch-up** (2026-10-06/07): Stages 0–1, batches 1–3 (238
  GL items) and the final phase (full test plan in `claude/final-test-plan/`,
  ~250 new tests, fixes). Baseline: CI green (run 37557433600), release
  1.0.25. Batch plans and checks: `claude/catchup-test-plan.md`; rules:
  `claude/catchup-batch2-rules.md`, `claude/catchup-batch3-rules.md`,
  `claude/final-phase-rules.md`, `claude/final-fix-rules.md`; commits
  d68f4d88 (batch 1), 31861922 (batch 2), ae635492 (batch 3), a7fdaf0b
  (final phase). Included: Stage 2 Run lifecycle (run_scope), module files
  (store) and actions (Library); AU-27 / GL-184 (mirrored copy one undo);
  direct time reads in Chain, the script loop and the vJoy keep-alive.
- [x] **Stage 0** – program map, spec and gap list (2026-10-06).
- [x] **Stage 1** – safety net: CI, random order, lint baseline, validate
  (report-only), journeys, decisions.md (2026-10-06).
- [x] **G-HISTORY** – History across the whole program (2026-10-05:
  4597e486, 20155486, 780f16b8); notes in `claude/history-notes.md`.
- [x] **G-LIBLEAK** – Unused actions written to the profile (2026-10-05:
  b4539968).
- [x] **Hidden Cards in the Home menu, no window** (2026-10-03).
- [x] **Audits 2 and 3** (2026-10-05/06: 6edbdcd8 .. a1459e22); tracker
  AU-76..AU-115.

## Working standard (pointer)

Status line, progress page (https://claude.ai/artifact/NQJw6xzumYopoJn5NXJxqR),
live agent logs (`tools/agent_log.py`, `.agent-logs/all.log`) and several
agents where work splits: see `.claude/CLAUDE.md` "Working standard".
