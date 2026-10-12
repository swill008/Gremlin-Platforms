# To do

What is open, in one list. Each item is done through the normal process
(`claude/system-maps.md` "How we work"; spec first, `.claude/CLAUDE.md`
change control and working standard). "Add to the to-do" means recording an
item here only; nothing else changes until the work starts.

Details for many items live in `claude/gap-list.md` (GL ids) and the spec
pages in `claude/program-map/`. Finished work is under "Done" at the end;
older text is in git history.

## Next up

1. DONE (user 2026-10-12: "we fixed it by zooming out to 50% and if it runs over at higher zoom scale we will come back and fix it"; SCALE_MAX stays 200). **Limit the UI scale to 175 %** (user, 2026-10-07; replaces AU-56 /
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
7. DONE (scrub 2026-10-12: df271e84, D-04-Q14, test_profile_recovery.py). Profile recovery copy after a crash (GL-029, approved, deferred).
8. DONE (user 2026-10-12). Test panel without the game: press a binding on screen, see what
   vJoy/Xbox gets.
9. Find in profile: every use of a key, vJoy output, mode or action.
10. Copy a mode or an input's bindings from another profile.
11. DONE (scrub 2026-10-12: faf5c0ca, D-01-DIAG-ZIP, test_diagnostics_zip.py). Save diagnostics: one local zip of logs, settings, device list.
12. DONE (scrub 2026-10-12: f6417411, D-TEST-RULES-FAIL, test_rules_fail_on_damage.py). Rule checks (validate) from report to fail (Stage 2 leftover).
13. **SHELVED by the user 2026-10-07.** Startup time: load rarely used pages on first open; a startup-time test.
    Measured before shelving (off-screen, S13; scripts in `.agent-logs/handson/S13/`): window built and drawn
    ~0.9 s after start-up begins, whole process ~2.0 s (empty profile); the user's 386 KB profile (204 inputs,
    4 sticks + 3 vJoy) ~0.92 s / ~2.1 s. Removing single parts of Main.qml changed it by less than run-to-run
    noise. Off-screen skips HidHide and the keyboard/mouse hooks (their real cost not measured).
14. DONE (scrub 2026-10-12: 11f8295c, D-01-UPDATE-NOTES, test_update_notes_window.py). What's new in Check for Updates (release notes before updating).
15. Coverage report; fill the riskiest gaps.
16. PARTLY (scrub 2026-10-12: split + test-times cache done (a840239d); venv cache tried and dropped (5745aecf); compiled-QML cache not done). Faster CI: cache the venv and compiled QML (with item 2).
17. PARTLY (scrub 2026-10-12: binding_catalog.py 1147->242 done; hardware_profile.py (2477) and module_model.py (3132) have grown). Keep shrinking hardware_profile.py, module_model.py, binding_catalog.py.
18. PARTLY (scrub 2026-10-12: some windows checked at 100/150/175; no full screenshot suite; waits on item 1). Screenshot tests at several UI scales (70–175 %).

## Carried-over fixes (one at a time, spec first)

19. PARTLY (scrub 2026-10-12: models reused; viewing a key still creates an empty input). **GL-254** Viewing a key on the Keyboard page creates an empty input
    (needs a detached draft input in ui/profile.py + Library).
20. **GL-257** `qml/action_kinds.js` keeps its own action-type table.
21. **GL-260** Condition editor: data and UI (QObject) mixed — a redesign.
22. DONE (scrub 2026-10-12: e414d0b3, output._sending() gates write_vjoy/write_xbox). Idea: `output.write_vjoy` / `write_xbox` refuse writes when no Run is
    on (today it holds only because every sender stops at Stop).
23. A renamed stick keeps its card order slot but loses its saved card size
    and stack (keyed by name slug).
24. About 170 fixed `qWait` calls left in the off-screen window smoke
    scripts (print_export, button_map_*, usability_smoke); fix as those
    areas are touched (AU-119 leftover).
25. DONE (scrub 2026-10-12: device.py uses clock.monotonic, GL-265 done). Calibration's axis graph (`gremlin/ui/device.py` ~862, 881) still reads
    `time.time()`, not `gremlin.clock` (GL-265 leftover).

## Planned features (need the user's decisions)

26. DONE (user 2026-10-12). **BM41 – A bigger page for the Device Mapping Editor.** The page (32000 x 18000
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
27. PARTLY (scrub 2026-10-12: one page size done; read-on-load waits for BM41). **GL-270** Read the page size back on load (comes with BM41).
28. CLOSED 2026-10-11 (no longer needed: D-03-DEVICE-FOLDERS removes the shared picture library). **GL-274** Picture library "Remove unused" button (D-07-GL274-LATER:
    design what "unused" means first).
29. **GL-186** New draw shapes: Plus, Radial ring, Named Card.

## Test housekeeping

30. Find the test that leaves a different EventListener instance in place
    than the one InputModuleRuntime connected to (seed 572578; partner
    test_twin_devices::test_each_twin_has_its_own_card creates the
    runtime). The live-map test in test_final_07 now connects the runtime
    to the current listener itself.
31. PARTLY (scrub 2026-10-12: guarded in store/device_initialization; other test paths not checked). Log noise in tests: "No parameter with key ('global','internal',
    'twin-device-names')".
34. Order leak: `test_batch2_b7::test_restore_applies_logs_and_ui_scale_at_once`
    run straight before `test_history_recording::test_settings_the_user_chooses_are_kept`
    makes the latter see an extra settings entry (pre-existing; a flush in
    b7's finally did not fix it).
35. DONE (batch C, C-DTAP: test_double_tap_tempo.py on virtual timers). Timing flake: `test/action_interaction/test_double_tap_tempo.py::test_single_tap_long`
    failed once under the 6-part load, passed 3/3 alone; wait for the result
    instead of a fixed time (as cc3b49f3 did for the keyboard tests).
36. **DONE 2026-10-07 (31f05950, CI green 37687912233).** Listen / macro Record switch input highlighting directly
    (`gremlin/ui/util.py` ~199, 287, 295, 384, 419), outside the Backend's
    holder set (03 S114 fix): stopping Listen with Calibration open could turn
    highlighting back on. Move them onto the holders.
38. Local-only crash: replaying CI's unit-1 order (seed 394220, CI file set) in ONE pytest process on
    the user's PC hits "Windows fatal exception: access violation" in
    `test_device_reconnect.py::test_auto_mapping_tool_keeps_its_ticks` (#724), during pytest-qt event
    processing. Older than today's Auto Mapping Tool code (same at 870c98dc); CI passes that order; the normal
    6-part run passes. Likely a real driver on this PC plus an earlier test. Investigate when convenient.
37. Person checks from the fixes: your 1,172-action profile no longer
    stutters while idle (Q19); after a stick is re-plugged, actions read its
    last value until it moves (D-05-UNPLUG-CENTRE note).

39. PARTLY (scrub 2026-10-12: pinned <6.12 (717f5420); cause not found). PySide6 6.12.0: CI picked it up on 2026-10-08 (no poetry.lock in the repo) and 24
    tests that start the program off-screen crashed (access violation, exit 3221225477),
    plus menu differences (test_menus, test_device_mapping_editor_window), runs 37754952665.
    pyproject.toml holds PySide6 below 6.12 until we find what changed and fix it.

40. ~~Retire the Device Pack window once the Device Library is in and used
    (user, 2026-10-08): the Library saves, exports, imports and copies packs;
    decide what of Device Pack's fine-grained piece choices (map view, print
    settings) to keep. Spec change first (08 S49-S85).~~ Closed 2026-10-11
    (D-FIXLIST-B2, fix list batch 2): one Export / Import Device window, one
    .gmap format, Import As a new device / Onto an existing device, every
    piece tick kept (08 S49, S49a, S59a-S59c, S112).

42. PARTLY (scrub 2026-10-12: exit deadman + model teardown done; native cause open, EXIT_HANG_FAILS off). Test teardown hang (found 2026-10-08, HG): one pytest process running
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

43. DONE (scrub 2026-10-12: de73a665 (warning only until 42 is solved)). Exit-hang check (user go 2026-10-08, after the Device Library is committed):
    (1) test-plan.md rule: a run must end within 20 s of pytest's summary, else it is an
    EXIT HANG (reported with part and files, never passed/slow) + batch checklist line;
    (2) run_tests.py: after a part's summary wait <= 20 s, then report EXIT HANG, list
    its files, dump stacks, end it; a WARNING (summary + CI annotation) until to-do 42 is
    fixed, then a failure; (3) conftest pytest_unconfigure arms faulthandler (20 s, dump
    + exit); (4) agent contract + lead watcher report exit hangs; (5) memory note.

44. DONE (scrub 2026-10-12: de73a665, test/vjoy_guard.py). Tests must never touch the real vJoy driver (user, 2026-10-08). The PC blue-screened
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
45. DONE (user 2026-10-12). Device Mapping Editor canvas editor into the shared Rename box (parked by the user 2026-10-08,
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
    (c) device_mapping_editor_fixes_smoke.py nudge test depends on 5 nudges within 400 ms.
47. PARTLY (scrub 2026-10-12: stall part done; other order culprits open; seen again 2026-10-12 in batch E quick tests: test_final_01.py::test_s44_a_switch_is_saved_and_announced_when_changed got "No parameter with key (global, general, log-when-not-responding)", passes 2/2 alone). Test race (found 2026-10-08, full run seed 124841; passed on rerun): test_stall_detection.py's
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
48. DONE (user 2026-10-12). vJoy loopback stand-in for the integration tests (VG idea, user 2026-10-08: to-do).
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
51. DONE (user 2026-10-12). Device Library ideas (2026-10-09, not started): drag a saved setup onto a stick row to start
    Copy to Another Stick; sort the device list by name / last seen / saved setups (View, remembered);
    highlight the search match in names and descriptions.
52. PARTLY (scrub 2026-10-12: ea296dde shared pieces done; heading/empty-state not verified). AFTER THE 1.0.30 RELEASE (user 2026-10-09: remind me): streamline shared pieces. First the
    destructive pair: DangerButton (one red button) + ConfirmDialog / Confirm.ask (names what goes,
    red go button, Cancel default, Enter/Esc cancel, "History can put it back" or "can't be undone");
    move every delete/clear question onto it (Library, History Clear, Delete Device, Delete File,
    Device Mapping Editor, Manage Modes). Then 1 shared search box (from HelpSearchBar) and 2 shared message line
    (Library's, with Undo link). Later: section divider/heading, empty state, file/folder picker that
    remembers folders, shared Undo/Redo bar. Estimates: pair ~30 min (3 agents), 1+2 ~30 min.
    Sighting 2026-10-09 (CI run 37979393055, seed 759318): stage1_device_mapping_editor_smoke 'outside' part blocked in
    QMetaObject.invokeMethod(root, "deviceMappingEditorWindow") (smoke line 153), no Python frame above; passes locally (39 in 42 s).
    test_stage1_device_mapping_editor._run now keeps the whole stall report. Next if it repeats: faulthandler C-level dump.
    Sighting 2026-10-09 17:25 (local full run, unit-2): test_final_01::test_s12 child app stalled past 120 s
    under full load; passes alone in 1.5 s. Same blocked-while-loading class.
    Sighting 2026-10-09 20:3x (CI run 38012818159, seed 21247, 468e0838): setup stall in two History
    window fixtures (test_history_diff_window 6 errors, test_handson_G2_history_heading 1); CI parts
    took ~11 min each (heavy load). Change was QML card resize only; failed job rerun.

53. DONE (scrub 2026-10-12: 384891fb + 4e56e49a (pass 3 by inference)). QUEUED (user 2026-10-09: do all 3 passes, before the 1.0.30 release): Help gap fill from the
    08:53 audit (all 10 spec pages vs qml/help). Pass 1: fix 6 wrong items (mode bar not "on the
    toolbar"; auto-load on "comes to the front"; Text to Speech buttons only; Device Library menus
    "left out" not greyed; Map to Xbox offers only fitting targets; Undo Delete Mode needs a spec line,
    ask the user). Pass 2: ~12 new topics (safety net: recovery copy, unfinished actions / Save
    without them, missing files; Treat as; what Stop releases; the tray incl. memory saving (01 S87);
    Clear History + Before/After + Previous/Next change; command-line options; the Help window itself
    (S137, S138); Device Mapping Editor unplugged/damaged; Device Pack refusals; card drag/resize; mode rules).
    Pass 3: ~55 partly covered topics. 5 agents, one chapter file each; claude/help-style.md.
    Estimates: 10 + 30-40 + 30 min.
54. DONE (scrub 2026-10-12: ec5a042b, D-01-HELP-LINKS). PLANNING (user 2026-10-09): "Show me" links in Help that open or point at the thing a topic
    names (a menu, a window, a setting). Discussion in progress; no code.

55. DONE 2026-10-09 (built: gremlin/profile_recovery.py, 04 S94; Help checked in the 2026-10-10 Help pass 2). Was: AFTER THE 1.0.30 RELEASE (user 2026-10-09: build it after the release). GAP (found 2026-10-09 by HW-config): 04 S94 profile recovery copy (Q14, approved 2026-10-06:
    copy of unsaved profile edits about every minute, Restore / Discard / Not now on next open or
    after a crash, removed on Save / Discard / clean close) is not in the program. Not in Help until
    built. (09 S61 reworded to buttons and keys, user approved 2026-10-09.)
    UDM edge case: a deleted mode's own Change Mode action naming a mode renamed since comes back
    with the old name (not covered).

56. DONE (a3f448d2, 2026-10-09; S59 test restored 2026-10-10 by T56). Spec vs program, found by the Help writers 2026-10-09: 03 S46 Module Setup Save
    while unplugged says "...to save its setup..." when the stick is unplugged after opening (spec:
    "Plug in <device> to change its setup. Nothing was saved."; gremlin/ui/module_model.py ~1900,
    ~1951); 03 S103 a calibration with lowest above highest gets "...lowest and highest values are the
    same"; 08 S104 spec spells "Previous change"/"Next change", buttons say "Previous Change"/"Next
    Change" (glossary Title Case); 05 S59 "Reuse" never appears on screen; 07 S12 Device Mapping Editor status
    line on a refused save into a damaged file says only "Not written..." (check the dialog).

57. DONE 2026-10-09 (with the shared-pieces batch) (user 2026-10-09): show the program version in the main
    window title bar, e.g. "test profile.xml - Gremlin-Platforms R1 1.0.30" (spec 01 S57 to update).

59. DONE 2026-10-09 (D-04-LD-FILE; the Logical Device stands alone: own module file shared by all profiles, permanent ids, profile version 15). Open question (user 2026-10-09: decide after using it): should every built-in row (Keyboard, OSC, Logical Device) get the same Library menu, including Import? Original item: the Logical Device in the Device Library's
    Built-in inputs section, beside Keyboard and OSC: Save to Device Library, Restore, Export of its
    controls, names, groups and actions. Needs the Library's save/restore/export to handle the
    Logical Device's data (~30-40 min). Spec 10 S6 and the class table's library_builtin change.

61. QUESTION (user 2026-10-09: to-do for now, new feature, decide later): should the Device Library
    always list the built-ins (Keyboard, OSC, Logical Device), even with no module file and no saved
    setups? Today a built-in gets a row only once it has a file or a saved setup
    (gremlin/device_library.py _modules ~645, used ~832), while Home always shows the Logical Device card
    (03 S71) and built-ins are always present (03 S90a). Suggestion: always list them in Built-in
    inputs with an empty line ("Nothing saved yet. Set it up on its page, then Save to Device Library,
    or bring one in with File > Import Device Pack..."), Save greyed until there is something to save;
    display only, nothing created on disk. Spec addition to 10 S6. ~10-15 min + full run (agents:
    Library rows py, empty line QML, spec/Help, one test). Found by LIB-audit; tracker T-lib-builtin-no-file-row.

62. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC idea (user 2026-10-09: to-do): OSC in conditions and macros. Today an OSC condition always reads
    "not present" (input_cache has no OSC device); macros can't capture OSC. ~20 min.
63. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC idea (to-do): sender allow-list. Accept OSC only from chosen IP addresses (shared networks).
    Setting in OSC's Module Setup Server section; travels with packs. Small.
64. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC idea (to-do): per-input axis shaping on the OSC input itself: invert, deadzone, curve, before
    any action.
65. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC idea (to-do): address patterns. OSC wildcards (`/fader/*`, `?`, `[..]`, `{a,b}`) so one input
    covers several controls.
66. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC idea (to-do): import a TouchOSC layout (.tosc) to create all its controls as inputs with the right
    modes.
67. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC idea (to-do): OSC from user scripts. Scripts can send and receive OSC (script API).

68. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC (to-do, user 2026-10-09): feedback from action states (e.g. a toggle action's on/off) as a feedback source.
69. DONE 2026-10-10 (OSC batches 52a8c2f0/36bbcdb7/6a55f094, 09 S147-S164). OSC (to-do): encoder acceleration (bigger steps when the knob turns fast).
72. QUESTION (found 2026-10-09 by PAGE): on a device page (OSC, maybe Keyboard) an input that is
    selected but has no actions shows a blank right side with no way to add a first action there.
    Decide the text (e.g. "No actions on this input yet") and how a first action is added. Not built.

73. DONE 2026-10-09 (d90939af, 01 S145): was a question (found from your run, GEOM): "Unable to set geometry" when Module Setup (and any
    tool window with ToolWindowMemory) reopens. Old gap (window_placement.py restore_tool since
    550ce2fb): the saved size is clamped to the screen without the title bar/frame, the first screen
    showing 35% is picked (not the one showing most), and the QML width/height bindings resize it again
    when it lands on another screen. Fix proposed: use the main window's _fit_client + frame margins for
    tool windows, pick the screen with the largest overlap, size bindings only on first creation.
    Needs a new 01 spec statement ("tool windows reopen with their whole frame inside the work area of
    the screen they land on") - your OK first.

76. DONE 2026-10-10 (68096ab2, 02 S124-S133, D-02-RESET-DEVICES; hands-on of the Windows
    permission prompt left as gap RESET-HANDS-ON). Reset devices (user 2026-10-10): a button on the HidHide page that disables and
    re-enables the hidden sticks so every program (Gremlin, games, the Input Tester) opens them again
    and HidHide checks them anew. Why: HidHide only checks when a device is opened (verified, HidHide
    v1.4.181 Logic.c 160-207, scratchpad hhverify/upstream.md); it has no command to recheck open
    handles. Before building, VERIFY: needs administrator rights (Windows asks each time); Gremlin and
    any running game lose the sticks for about a second; that DirectInput programs reopen cleanly
    afterwards (standard Windows behaviour, not yet checked here). Spec change on page 02.
    PLANNING started 2026-10-10 (user: "lets plan the reset now").
    Design approved 2026-10-10 (RD1-RD10; mockup https://claude.ai/artifact/HVkxGiqVyniY9qGJfnrZdk).
    LIVE CHECK 2026-10-10 04:46 (user present, approved): pnputil /restart-device on the left stick's USB
    device USB\VID_231D&PID_3201\9&1d65ffe4&0&3 run with Start-Process -Verb RunAs: exit 0, returned in
    0.3 s. No UAC prompt on THIS PC: ConsentPromptBehaviorAdmin = 0 (elevate without prompting); other
    PCs will show the prompt. Gremlin's Trace: unplugged 04:46:50.189 -> plugged in 04:46:52.556 (~2.4 s),
    'Initializing joystick devices' twice in system.log; same instance ids came back (HID\...&39cb7826,
    USB\...\9&1d65ffe4); first RAW after return +0.022 (centred). Input Tester (on the Block list):
    '2 hidden' while gone, '3 hidden' after -> stayed hidden. Restarting the USB device is enough.
77. DONE 2026-10-10 (4951df66, D-02-DILL2, 02 S139-S142): R16's dill2.dll ships as dill.dll for both programs. Upgrade the DirectInput reader dill.dll 1.3 -> 1.5 (user 2026-10-10: on the to-do for now; impact
    research requested). Verified: v1.3 DeviceState sizes button(128)/hat(4) but indexes from 1, so
    every poll of a 128-button / 4-hat device reads and writes one slot past the end (dill.cpp
    c96571404b lines 53-57, 362-390). On this PC all three VKB sticks report 128 buttons and vJoy 1
    reports 128 buttons + 4 hats. Upstream v1.5 sizes button(129)/hat(5). Effect of the overrun: not
    verified. Gap DIRECTINPUT-128 (02). Impact study done 2026-10-10 (DILLUP, scratchpad dill_upgrade/impact.md):
    interface is a drop-in (same 10 functions and structs; 1.5 adds shutdown()); NO published 1.5 build
    (source only, master eb66aea) - we'd build it (CMake + MSVC x64); upstream Joystick Gremlin still ships
    1.3; behaviour changes: one thread + lock, 1 ms polling for non-buffered devices, init waits for the
    first scan, plug/unplug releases devices, unplugged lookups return empty summaries (input_cache.py
    188/452, device_initialization.py 176), axis detection by DirectInput (axis maps may change ->
    vJoy matching device_initialization.py 307). Plan: user go + spec, build + checksum, swap + small
    wrapper/tester changes, new tests, hands-on with the 3 VKB sticks and vJoy 1, rollback = git file.
    UPDATE 2026-10-10 (user pointed at upstream R16; R16DILL, scratchpad r16dill/findings.md): upstream
    Joystick Gremlin Release_16 (2026-09-26) ships a second library dill/dill2.dll "DILL v2.0" (SHA-256
    afa5373d...4948, 353792 bytes, exports shutdown) and loads it by default, keeping dill.dll (= ours) as a
    fallback behind a setting use-legacy-dill (commit a4bf778b0d). Strings: all v1.5 messages + XInput
    reading. Data layouts and the 10 C functions match our wrapper (+ shutdown) - should load with only
    the file name changed (not run). NOT verified: that v2.0 includes the button 128 / hat 4 fix; v2.0
    source not public. Option now: take R16's dill2.dll (prebuilt, used by upstream) instead of building 1.5.
    FEASIBILITY 2026-10-10 (D2CODE/D2LIVE/D2APP, page https://claude.ai/artifact): dill2 loads through our
    wrapper with only the file name changed; same 7 devices, counts, axis maps, readings; whole program off-screen
    identical; button 128 / hat 4 accepted (1,701 'invalid index' lines in ~6 s with 1.3, none with dill2);
    shutdown() works. Not yet: pressing button 128/hat 4, plug/unplug, Xbox pads via XInput, real vJoy matching.
    Draft patch scratchpad dill2_study/patch.diff (not applied).
78. DONE 2026-10-10 (4951df66, D-01-LICENCES, 01 S153): licences/ shipped. Licence notice for dill (found 2026-10-10, DILLUP): dill.dll is BSD-2-Clause (not GPL); the BSD
    licence asks binary redistributions to carry its notice, and licenses/ has no dill (or spdlog)
    notice today. Add licenses/dill.txt (+ spdlog) and check the installer copies licenses/. Not started.
79. CLOSED (user 2026-10-10: ship with everything included (Input Tester ships with the program); no self-test). Was SHELVED (user 2026-10-10: "keep things as they are for now"): how the Input Tester ships and a
    --self-test of the built exe (in tools/build_input_tester.py and the release workflow). Today: the
    release build makes both exes and the installer copies them; the dev script is for source runs.
80. DONE 2026-10-10 (4951df66, D-02-DILL-FOLDER, 02 S138): the reader loads only from the program folder. SECURITY (found 2026-10-10, D2CODE): dill/__init__.py 292-303 looks for dill.dll in the working folder
    (the folder the program was started from) before its own folder, and `import dill` runs before
    joystick_gremlin.py changes folder (82 vs 101) - a planted dill.dll there would be loaded. Load only from
    the program folder. Not started.
81. DONE 2026-10-10 (to-do 81; Spec: none, no behaviour change): exit took ~5 s because the Text to Speech engine
    (QTextToSpeech, WinRT) was never released. TTSManager.close() now stops and releases it in shutdown_cleanup()
    before reset_drivers(); measured os._exit to process end 0.016 s (was 5.0 s). Test: test_tts_release.py.
82. DONE 2026-10-10 (387e25e7; D-02-RESET-DEVICES addendum S5, 02 S137): Reset Devices left its
    gremlin_reset_* temp folders behind (found 2026-10-10, RFIX). They are now deleted after the results are
    read (best effort; a leftover Administrators-owned file from before is ignored).

83. DONE 2026-10-10 (G-d, answered by the CARRY check, no change needed): a script's keyboard callbacks DO go
    through the input-module claims check (user_script.py:1698-1718 -> code_runner.py:437-441; keys reach
    process_event only via InputModuleRuntime._on_key, runtime.py:185-196, claim_allows_key). As for profile
    keys, with no Keyboard claim saved every key passes (claim.py:173-174). Not verified in a live Run.
    Checking in this batch.
84. DONE 2026-10-10 (this batch; 02 S105, S106, T1) (TWIN, 2026-10-10; 02 gap TW-XBOX-SLOT): the Input Tester's Xbox rows compare Gremlin's Xbox output pad
    number with the Windows XInput slot number, which are numbered differently; match them properly. Done 2026-10-10 (this batch).
85. DONE (user 2026-10-12: "HIDHide only does HID, not what xbox uses"; Help tools-hidhide Good to know line added). (TWIN, 2026-10-10): not verified whether HidHide can hide an Xbox pad from XInput (a program reading XInput
    may still see a hidden pad). Verify read-only and say so in Help. Not started.
86. PARTLY (scrub 2026-10-12: not reproduced off-screen; waiting for the user's screenshot). NOT REPRODUCED 2026-10-10 (T86-APOS: the real dialog off-screen draws "can't"; waiting for the user's full-size screenshot and UI/Windows scale). (RW5, 2026-10-10): the Reset Devices Xbox note shows "can t" on screen (apostrophe missing; the text in the
    code has it). Check the off-screen render. Not started.
87. DONE 2026-10-10 (SA1, 2026-10-10; 05 gap SA1, found by the action editor matrix): the Split Axis editor overflows the pane: its
    label row hides the Add Action selector (matrix screenshot split-axis_axis.png). qml/LabelValueComboBox.qml's
    250 dp minimum width forces the wrapping. Done 2026-10-10 (89bb0bbb).
88. DONE 2026-10-10 (e71023a1; 06 S92-S94) (O1, 2026-10-10): Logical Device self-target / loop guard. User approved P1+P2+P3 (D-06-LD-LOOP; 06 S92-S94):
    a new Map to Logical Device never starts on its own control, the picker never offers it, loops stop after 8
    hops with one user-log warning and one notice per Run. Done 2026-10-10.

## On hold / parked (user's choice)

89. DONE 2026-10-10 (this batch; 06 S94a, L1) (LD2, 2026-10-10, found by LD-GUARD): the Logical Device loop guard only catches a macro step re-triggering its own control when the cycle is under 0.1 s; a slower macro self-loop isn't stopped, and mashing a button that runs such a macro faster than 10/s for 8 presses could be stopped by mistake. A full fix carries the chain on each event (event path). Done 2026-10-10 (this batch).
90. DONE 2026-10-10 (this batch; 06 S94, S96, AD10, F2-LDPICK) (LD1, 2026-10-10, found by LD-PICK): a Map to Logical Device loaded from a profile that already targets its own control keeps that target (defaults never change loaded data, S92) but its picker shows nothing selected; the loop guard stops it at Run. Done 2026-10-10 (this batch).
91. DONE 2026-10-10 (e2267c9b; 05 S132) (started 14:05; user: "go ahead and get it done now"; approved **Method B: shared building
    blocks**, not Method A below; PB1 Logical's version, PB2 Clear Name on Device Bindings, PB3 pixel-identical
    proof; brief scratchpad sb_brief.md). Method B: each page stays its own file; the repeated glue becomes
    three shared parts the pages use (pane/leave handling in ActionPane, a PageAppearance part, a
    standard-menu helper); page-only features stay in each page; a page that needs different behaviour
    passes an option or doesn't use that part. Method A (a base page every page inherits) was considered
    and NOT recommended: QML inheritance needs a hook for every page difference, start-up order traps,
    and it gets rigid as pages grow. Original entry (Method A) kept below for the record.
    (PS1 (a), 2026-10-10, user: "log this (a) as a future todo"; tracker PAGE-SHELL-DUP): **one shared
    page base for the four list pages** (Device Bindings, Logical Device, Keyboard, OSC). Not started; the
    user chose PS1 (b) for now (the two drift bugs fixed: OSC's missing "Appearance…" menu row, Keyboard's
    own panel-close; guard test `test/unit/test_list_pages_alike.py`).
    - **Why.** The pages already share the model base (`gremlin/ui/control_layout.py` ControlLayoutModel)
      and the QML pieces (`qml/ControlTree.qml`, `ControlFindBar.qml`, `ActionPane.qml`,
      `ListAppearancePanel.qml`), but each page file still repeats the same glue. Checked 2026-10-10
      (function bodies compared): `requestLeave`, `closePaneNow`, `savePane`, `hasUnsaved`,
      `paneHasChanges`, `closeActionPane` are word-for-word identical on all four; `toggleAppearance` /
      `requestCloseDisplay` and the 10-line `pageBar` are the same; the menu skeleton (Undo/Redo header,
      Add Action, Rename, History, Appearance…, the Group / Groups / Order sections) is the same apart
      from the "sort by system name" wording. Drift already caused two bugs (fixed in PS1 (b)). Page files
      then: DeviceBindingsPage 752, LogicalPage 783, KeyboardPage 579, OscPage 1175 lines; estimated
      100-150 lines each would move into the base (not measured).
    - **What goes in the base** (new `qml/ControlPage.qml`, the page's root item): the `layout` model
      property; the six pane/leave functions and `leaveResolved` / `_leavingPage`; `displayOpen`,
      `toggleAppearance`, `requestCloseDisplay`, the `ListAppearancePanel` with a required `pageKey`, and the
      tree bindings to it (incl. parentAlign/parentWidthPct/childAlign/childWidthPct/groupSpacing); the
      `pageBar` component (Appearance… / Hide Appearance); the `ActionPane`; the menu skeleton built with
      MenuModel/ContextMenu (header Undo/Redo; quick rows Add Action, Rename, History, Appearance…;
      sections Group, Groups, Order) with **hooks** for page items.
    - **What stays per page** (passed to the base): the model type; extra quick rows and extra sections
      (Device Bindings: Module Setup…, Delete actions…; Logical: Assign Hardware, Clear Name, Add Inputs;
      Keyboard: Clear Name, Add Key…; OSC: Add Feedback, Change Address…, Copy for Companion, Send Test,
      Companion feedback, Add/Import/TouchOSC/Listen/Clear…, the feedback-row menu); the "sort by system
      name" label (By System Name / By Key Name / By Address); Find placeholder and filter ticks; row
      extras (Device Bindings live lights/bars + jump to pressed input; Logical writer rows; OSC Invert,
      live value, feedback rows, docked Monitor); page-only dialogs.
    - **Plan (as proposed 2026-10-10).** Effort then: about 40–50 min + CI 10 min.
      1. One refactor agent builds `ControlPage.qml` from LogicalPage (the reference page), with the hook
         API written to a contract file first (5–10 min, timings.md: refactor).
      2. Four page agents in parallel, one per page file, move their page onto the base (today's page
         agents took 10–17 min each).
      3. Test-only agent: extend `test_list_pages_alike.py` to check the pages use the base; update tests
         that read page source text (e.g. `test_batch2_b5a.py`, `test_config_pages_shared_pieces.py`,
         `test_list_appearance.py`, `test_cleanup_batch_a.py`, `test_colour_tokens.py`).
      4. Proof: before/after off-screen screenshots of all four pages (page, menu, pane, Appearance open)
         must be pixel-identical (method: scratchpad scripts `bq_shots.py` / `cfa_shots.py` pattern via
         the journey harness, temp USERPROFILE, fake hardware); page tests and journeys pass; full run.
      5. Map/spec agent: page 05/06/09 section 2 counts, new file, "owns" rows. No spec statement changes
         (no behaviour change).
    - **Watch-outs found 2026-10-10.** (1) PySide crashes (access violation) when QML builds a type whose
      Property notify is a base-class signal: give each model its own signal (see hardware_layout.py
      `paneChanged`, keyboard_layout.py `keyGroupsChanged`); the same care for any Python base used from
      QML. (2) QML base/page name clashes and property-initialisation order: keep page hooks as
      properties/functions with distinct names; test each page loading off-screen. (3) Main.qml calls
      the page functions by name (`_leavePages()`, `_actionPanes()`, `deviceBindingsPane()`,
      `keyboardPane()`, `oscPane()`, `currentPageBar`) — keep those names. (4) Text-reading tests pin
      exact lines. (5) OSC feedback rows stay editable while running (`ActionPane.lockExempt`).
33. DONE (scrub 2026-10-12: OSC batches built 2026-10-09/10 (program-map 09)). **OSC** (parked 2026-10-02; **picked up 2026-10-09**: decisions D-09-OSC-FILE, D-09-OSC-INPUT, D-09-OSC-FAULTS, spec 09; being built in this batch):
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
92. WON'T FIX (user 2026-10-10). (H1, 2026-10-10, F3-HIDHIDE, SHAKE-STRESS-06) Hardware Hide opening blocks the window ~0.5 s (after the read-once fix, about half). Moving the device read onto a gremlin.threads worker would need a "Loading…" state in DialogHardwareHide.qml (list opens empty, fills in), late ticks after setCloak/setInverse/setDeviceHidden/setGremlinControl/setGamingOnly/setDevicePhoto (needs a generation guard for quick clicks), a spec statement, and test waits on deviceCount. User chose to record it only (2026-10-10). Not started.
93. DONE 2026-10-11 (D-05-CANT-SEND-LIVE; NOTICE-OUT, NOTICE-ROWS, LD-94). (CS-G1, 2026-10-10, found by MAP6; 03 gap 35, 05 CS-G1) An open action editor doesn't re-check its red ⚠ when the OSC settings or the Xbox driver change while it is open: Map to Xbox re-checks only when its pad list changes; Send OSC re-reads its target's name on oscServerSettingsChanged but other editors don't. Recorded only (user 2026-10-10: "record the open items and we will do them later"). Not started.
94. DONE 2026-10-11 (LD-94). (LD-SYN, 2026-10-10, found by FOLLOW; 05 LD-SYN) Events sent by Map to Logical Device aren't marked as program-made (synthetic), unlike keys from macros and Map to Keyboard. Harmless today: they only happen while the profile runs, and the Logical Device page doesn't follow while running. Recorded only. Not started.
95. DONE 2026-10-11 (COND-95: checked; Script settings width issue split out as 98). (CS-COND, 2026-10-10, found by MAP6) Check that the Condition editor's vJoy target shows the red ⚠ and tooltip for a control that can't be sent (taken from MK-PICK's report, not confirmed in that editor). Recorded only. Not started.
96. DONE 2026-10-11 (option a, user-approved mock-up; NARROW-VJ, NARROW-LD). (EW-2, 2026-10-11, found by WIDTH; 05 EW-2) At the action pane's minimum width, Map to vJoy's device box cuts "vJoy 1" and "Invert activation" runs past the pane in Map to vJoy (2–4 px) and Map to Logical Device (42–70 px). When fixed, remove the two tags from test_editor_widths.py DEFAULT_ONLY. Recorded only. Not started.
97. DONE (scrub 2026-10-12: items 100-103 done, D-01-OWNER-NOTICES). (AUDIT-NOTICE, 2026-10-11, user: "follow up with an audit"; runs after 93 is pushed) Read-only audit of look-alike areas where screens listen to raw signals instead of one owner notice: Logical Device names/controls (logicalDeviceModified 5 listeners vs logicalDeviceReloaded 2), Home card "Driven by" lines, vJoy claims (1 s polling cache in output.py), device names after rename/re-plug (device_change_event 22 listeners). Find real missed updates; propose an owner notice only where one is found. Report in chat. Not started.
98. DONE 2026-10-11 (option a; SCRIPT-98). (SCRIPT-CUT, 2026-10-11, found by COND-95) Script settings page: with a vJoy setting that can't be sent, the red "⚠ Button 57" box ends 4 px past the page and window edge (1604 vs 1600 at 1600 x 950, 100 %); the same row with a claimed control fits (ends 1580). Likely the ⚠ minimum width in VJoySelector.qml with nothing in the row giving way; cause not confirmed. test_vjoy_picker_cant_send_places.py::test_the_box_is_not_cut[script] is xfail(strict) until fixed. Waiting for the user's choice. Not started.
99. (ORDER-CONFIG, 2026-10-11, found by ORDER-MACRO) Order-dependent: test_config.py run before test_startup_settings_kept.py makes test_startup_registration_keeps_them and test_unused_placement_settings_are_dropped fail with PermissionError (Access is denied) renaming a temporary settings file, and a stall (~140 s). Same with or without the 2026-10-11 conftest change; each file passes alone. Not investigated. Recorded only.
100. DONE 2026-10-11 (D-01-OWNER-NOTICES). (AUD-DRIVEN, 2026-10-11, audit 97) "Driven by" / what-drives-what goes stale: proven by probe — Delete Mode/Undo Delete Mode, OSC page Undo/Redo/delete (oscDeviceModified not heard), Output View header after any profile reload (_reload never emits targetsChanged), Home cards while Home is shown (no onTargetsChanged); by code — Device Library Swap and Change vJoy Output edit the open profile with no signal at all (library_profiles.Batch._apply_open), viewer windows don't follow action edits. Proposed: one owner notice signal.bindingsChanged (input_pairing.py). Waiting for the user.
101. DONE 2026-10-11 (D-01-OWNER-NOTICES). (AUD-LD, 2026-10-11, audit 97) Logical Device names: Input Viewer paired-input labels and Xbox page 'incoming' text ignore logicalDeviceModified (probe); OSC Feedback names read the saved file, not memory (maybe intended; spec silent); a script LogicalDeviceVariable creates a control with no signal (probe); a failed profile transaction rolls rows back silently (code only). Proposed: connect the 3 views; optionally logical_device.py sends logicalDeviceModified itself. Waiting for the user.
102. DONE 2026-10-11 (D-01-OWNER-NOTICES). (AUD-DEVNAMES, 2026-10-11, audit 97) Device rename (alias) not followed by the Device Library window, Input Viewer and Xbox Viewer device lists, and input labels inside the Logical Device/Macro/Condition/Script editors (code only); device_aliases.forget() saves without telling listeners. Spec question: 10 S7 'renames it on its Home card' but Home cards and the Device Bindings page title show the raw name. Proposed: signal.deviceNamesChanged owned by device_aliases.py. Waiting for the user.
103. DONE 2026-10-11 (D-01-OWNER-NOTICES). (AUD-CLAIMS, 2026-10-11, audit 97) Home output cards keep their own claim copy (module_model._dest_targets) not refreshed by the can't-send notice; a Device Library save leaves card claim details stale (probe). Keep the 1 s claim poll (only catcher of outside edits). Open question: should a module file edited outside the program update ⚠ marks and Home cards? Waiting for the user.
104. (LONG-PATH, 2026-10-11, found by TEST-SWEEP) Device Library Swap's autosave failed with "No such file or directory" when the user folder path was long (a deep scratchpad home); fine under pytest's short temp folder. Likely the Windows 260-character path limit. Not verified; recorded only.
105. DONE 2026-10-11 (RIG, J13, E2E-PRESET; j13 found and PAIR-NAMES fixed the vJoy Viewer name bug). (user 2026-10-11: "1a, code it as the next batch after this push") (MULTI-DEVICE) Tests see one stick (pJoy Pro) and one vJoy by default; ~35 files build their own extra devices. Build: a `devices` option in the journey harness next to `vjoy_ids` (default one pJoy Pro) with a preset rig (pJoy Pro, Saitek X52, a twin pair, vJoy 1 + 2); one multi-device journey (two sticks to two vJoys, Home cards + Driven by, Swap, Change vJoy Output, twin rename, unplug/re-plug, Input Viewer); today's end-to-end tests use the preset. Test-time rule (user 2026-10-11, 1a): keep one full run; after this batch measure the full run and add a row to timings.md; if it goes over ~7 min, add a "deep" marker for heavy multi-device journeys (in the full run and CI, skipped in targeted runs).
106. PARTLY (scrub 2026-10-12: device folders built; listener dill.dll load, planes (b)-(e), spec wording left). Device folders (D-03-DEVICE-FOLDERS, with D-08-GMAP-IMPORT and D-10-GMAP-SETUPS) BUILT 2026-10-11 (this commit). Background/foreground planes (D-07-BACKGROUND-PLANES, D-07-PLANES-ANSWERS) BUILT 2026-10-11.
   - ONE-TIME code (tracker group "One-time code"): OT-1 the move to device folders, `gremlin/modules/folders_move.py` and `joystick_gremlin._move_to_device_folders` (also `folders_move.register_setting` reading the old file-bindings setting once). Remove when no install still has the old layout (the user decides; at the latest before the first public release). OT-2 (an old map's photo becomes the bottom background picture when the map opens, in memory, written at the next Save; D-07-PLANES-ANSWERS P3a), built: gremlin/modules/planes_once.py, the fallback in store.device_photo_ref, hardware_profile._planes_text, device_pack._today_layout / _old_photo_in_zip / _merge_background, library_swap._swapped_docs (all marked `# ONE-TIME (tracker OT-2)`); remove once every map has been saved in the new format.
   - OT-3 one-time settings move: remove before release with OT-1/OT-2. The Button Map's settings move to the Device Mapping Editor's names at start (section "button-map" -> "device-mapping-editor"; global/internal/button-map-<x> -> device-map-<x>): `gremlin/device_map_settings_once.py` (all marked `# ONE-TIME (tracker OT-3)`), its call in `joystick_gremlin.py` before register_config_options, test `test/unit/test_device_map_settings_once.py`.
   - OT-4 one-time move: Library part id button_map -> device_map; remove before release with OT-1/OT-2/OT-3. At start, library.json's default parts, every saved setup's holds and the last change's parts are renamed once (backup of library.json in <data folder>/backup/<date> library part id move/; no old id left = done): `gremlin/library_part_id_once.py` (all marked `# ONE-TIME (tracker OT-4)`), its call in `joystick_gremlin.py` after register_config_options, test `test/unit/test_library_part_id_once.py`.
   - To check: the device-export end-to-end test's off-screen child logged a refused load of the real dill.dll from an "event listener" thread (the harness guard caught it; the test passes). Find which import starts that thread in the off-screen Home page harness.
   - Planes, open for the user: (a) S126 Show me links into the Device Mapping Editor window (BG-SHOWME); (b) should a Layers kind filter hide the folded Background row (now it always shows); (c) 03 S88 wording says the Logical Device card photo is the file's "image" (now the bottom background picture); (d) the window's openForDevice photo argument is unused (tidy-up); (e) editor-only tests not written: Align/Distribute and zoom in Background mode, leader ends snapping to a background picture.
   - Spec wording to ask the user about (map check, 2026-10-11): 04 S2 and 09 S44 name `store.path_of(...)` (gone); 06 S95 and LD3 say `logical_device.json`; 09 S168 and the OSC trace lines say `osc.json` (gap OSC-TRACE-NAME); 03 S62 "another stick uses the file" can't happen with device folders; 07 S106 also keeps pictures the recovery copy names; 08 S85 "binds the devices again"; 08 S87 names a deleted test file.

107. FLAKY on CI (2026-10-11, run 38162521838 on 3130f65c): test_input_tester_e2e2.py::test_tester_log_rotates_at_one_megabyte waited its 15 s for "values read ok" in tester.log and failed; passes locally in 0.7 s; not touched by today's commits. If it fails again, trace why the tester writes that line late under CI load (re-run passed/failed: see timings).
108. ~~(D-TESTLIST-1 item 16, 2026-10-11) The old `history\button-map.jsonl` left by the Device Mapping Editor rename.~~ Done 2026-10-11: at the user's request the lead moved it to `backup\2026-10-11 old Button Map history\` in the user's data folder (kept, not deleted); no code change.
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
- [x] **Item 3: Device Mapping Editor exports in the background** (2026-10-07,
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

Status line, the one tracker (https://claude.ai/artifact/HpP8ef9co1whHSorPcVse8),
live agent logs (`tools/agent_log.py`, `.agent-logs/all.log`) and several
agents where work splits: see `.claude/CLAUDE.md` "Working standard".
109. (user, 2026-10-11) Remove all one-time code (tracker OT-1 device folders move, OT-2 old photo to background picture, OT-3 Button Map settings move, OT-4 Library part id move) in a new release soon after 1.0.33; 1.0.33 keeps them so the user's own data finishes moving (OT-4's covers fix runs at the next start).
110. (2026-10-11, tracker OT-5, one-time code) Temporary click trace for the dead right-click report (user: right-clicking around a background picture in the Device Mapping Editor sometimes opens no menu, several times in a row; left clicks sometimes do nothing). gremlin/ui/click_trace.py and the `ONE-TIME (tracker OT-5)` lines in RigPointerArea.qml and the context menu: remove once the cause is found and fixed.
111. CRASHED in a full run (2026-10-11 22:30, seed of full_bg2): test_tts_release.py::test_shutdown_cleanup_releases_the_speech_engine, "Fatal Python error: Aborted / access violation" in gremlin/tts.py:146 close() called from shutdown_cleanup (native QTextToSpeech release under load); ended part unit-3 early. Passes alone (3 of 3). Investigate: release on the engine's own thread / guard double close.

## D-NEXTLIST-1 (user, 2026-10-12): changes collected for the next run — record only, no code/spec/tests until the user says build
1. DONE 2026-10-12 (c52f7205, D-NEXTLIST-1). (2026-10-12) Remove the Xbox Viewer from the toolbar and bring it into the Xbox output's own Output View, as a special case: the Xbox Viewer's content (ViGEmBus driver row with Get/Test ViGEmBus, the per-input-device pad face(s) "VKBsim Gladiator EVO R -> Xbox 360 1" with the lit controls, Mapped axes / Mapped buttons chips) combined with today's Xbox 360 Controller Output View (driver row, control rows: Left Stick X ... DPad, "who targets each control"). Both keep working as they do today. User screenshots: Xbox Viewer window and Output View › Xbox 360 Controller (scratchpad nextlist_1a.png, nextlist_1b.webp).
2. DONE 2026-10-12 (c52f7205, D-NEXTLIST-1). (2026-10-12) Home screen card drag: when reordering cards (not moving between sections — user corrected "I misspoke, just reordering cards"), use the same drag behaviour as the Device Bindings rows: show the card being dragged and show where it will be placed. The Device Bindings row drag is the reference for how dragging and reordering should look and work.
3. DONE 2026-10-12 (c52f7205, D-NEXTLIST-1). (2026-10-12; user: "lets plan for a 50% increase") Home cards: raise the maximum card size by 50 % (720 x 520 -> 1080 x 780; was first asked as double) so a user who wants large pictures can enlarge a card up to the new maximum. Today: card size clamped to 220-720 wide x 140-520 tall (StatusCard.qml:389, :403); pictures decoded at most 720 x 520 x screen scale (StatusCard.qml:174, StatusPage.qml:849, :1096); the generated device picture is at most 1024 px on its longer side (store.DEVICE_PHOTO_SIDE). Impacts discussed with the user 2026-10-12: memory per card up to 4x, generated picture cap must rise or large cards look soft, very large cards must still fit the window. User note: the program already has a feature that reduces memory while minimized (tray memory) — check it releases the larger card pictures too.
4. DONE 2026-10-12 (c52f7205, D-NEXTLIST-1). (2026-10-12) Device Library window: a small picture for each device row, like the HidHide window's rows; streamline by reusing the same way it is done there (user: "reuse or implement the same way if it is already done"). Today: HidHide shows a 40 x 40 framed picture (Style.bgWell, Style.line border, radius 3, decoded at 80 px) from row.photo (DialogHardwareHide.qml:497-512); the Library rows show a joystick/keyboard icon glyph (WindowDeviceLibrary.qml:969) and only the right-hand details show the device map photo (:1210). Lead's suggestion (to confirm at planning): a shared small DeviceThumb component (frame + picture + the current icon as fallback) used by the Library rows, fed by the device's shown picture (Device Image > generated picture > bottom background picture); HidHide itself left untouched (user rule) unless the user wants it to adopt the shared component too; saved-setup rows may show their own setup's picture. Follow-up (user, 2026-10-12): the Keyboard, Logical Device and OSC rows DO have pictures, in their modules (seen read-only: modules\Keyboard\pictures\photo.jpg, modules\Logical Device\pictures\photo.png, modules\OSC\pictures\photo.jpg) — tie them in; user asks whether to change HidHide's method and do a combination (one shared picture lookup + one shared thumbnail for HidHide, Library, and anywhere else). HidHide today: its own per-row pick (setting display/hidhide/photos) else the device's picture via hardware_profile.profilePhotoUrl (hidhide.py:498-512, with a vJoy fallback). User idea (2026-10-12): just use each module's own picture (the one generated in / kept with its module) as the thumbnail source everywhere, rather than a separate image system.
5. DONE 2026-10-12 (c52f7205, D-NEXTLIST-1). (2026-10-12, from the user's code audit; record only until the user picks) Audit results to decide on: one real bug (DeviceMapCard.qml:31 liveStamp uses a `count` the Python list doesn't have -> always 0, the map card's change signal never fires); guard-test gap (vjoy/ and theme/ outside test_spec_line.py / test_program_map_covers_files.py and the CLAUDE.md list); a dead Options switch (display/status/last-keep-after-release); dead code and leftovers lists in scratchpad/audit/*.md (PY-REFS 54 dead / 96 test-only; QML-REFS 5 dead files, 31 dead functions, 30 dead properties; BRIDGE 5 dead + 38 test-only seam names, 8 unused roles; ASSETS 141 unused shipped pictures, old WiX build files, a committed log; LEFTOVERS 22 legacy shims, 16 duplicate-helper groups, OT-2 places missing markers; MAPCHK 27 stale names, ~35 stale line references, 14 files with unclear owner).
6. DONE 2026-10-12 (c52f7205, D-NEXTLIST-1). (2026-10-12) Device Library device rows: move the "N saved setups" / "No saved setups" text from the right side to below the device name, so the left/right divider can be moved further left and the view is cleaner. Open at planning: its order with the description line (e.g. "test decription." under VKBsim Gladiator EVO R), and whether the Connected / Not connected badge stays on the right. Screenshot: the Device Library window (user, 2026-10-12).
Planning answers (user, 2026-10-12): "1a, 2b, 3a, 4a, 5 leave the image generation as is, we will only increase its actual sizing shown, not increase its quality. 6a, 7a, 8a, 9a. the remainder are as you recommend." =
- Item 1 Xbox: 1a pad cards above the control rows, one card per driving device, foldable section (open by default, remembered); 2b the Tools > Viewers > Xbox Viewer menu item is removed too (and the card menu's Xbox Viewer entry).
- Item 2 Home drag: 3a other cards stay still, a line shows the drop spot (Device Bindings style), 4 px start; 4a a stacked pile's drag shows its front card.
- Item 3 cards +50 % (1080 x 780): 5 the generated device picture stays at its 1024 px cap (only the shown size grows).
- Item 4 Library thumbnails: 6a HidHide untouched; 7a no picture -> today's icon inside the frame.
- Item 6 Library rows: 8a name / description / "N saved setups" lines, row ~58 px, badge stays right; 9a the divider position is remembered, list minimum ~260 px.
- Item 5 audit: 10a fix the map-card liveStamp bug; 11a add vjoy/ and theme/ to the guard tests and vjoy/ to the CLAUDE.md program list; 12a remove the dead Options row; 13a read-only spec check of the 3 possible missing behaviours first; 14a remove the double-confirmed dead code (+ test-only code the spec doesn't need, with its tests), leave medium-confidence; 15a remove the 141 unused pictures, the WiX files and the committed log; 16a remove legacy shims not covered by decisions, add the 4 missing OT-2 markers, fix the macro 0.05 s rule; 17a merge the risky duplicate helpers; 18a fix the program map.
SPECCHK (2026-10-12, claude/audits/2026-10-12-code-audit context): none of the 3 is missing behaviour; user approved ("approved") deleting in wave 2: (1) logical_layout.drop_logical_steps + _MODELS (logicalDeviceReloaded already drops the steps); (2) option.ConfigSectionModel.scope + its signal + single-section branch, fix the two stale docstrings, update tests that set scope; (3) device_pack.put_gmap_wires + device_zip put_wires/PutWires/send_wires branches, docstrings, page 08 line 86, test_b2_zip put= cases — ONLY after checking the bindings-only .gmap (no folder) case: if it still imports its wires another way, delete; if not, keep #3 and tell the user.
User (2026-10-12, "approved"): Add Image on a Keyboard/OSC stub card with no module file is allowed (it creates the file; the card becomes a normal card); CLAUDE.md change-control list also gets theme/ (done with vjoy/).
112. (2026-10-12, found by DEVIMG-TESTS, not verified as a user bug; seen again by C-PHOTORACE 2026-10-12: with USERPROFILE under the long scratchpad path keepImage/keepPhoto silently take nothing, with a short temp home it works) Module Setup Add Image… fails silently when the edit's temporary path goes over the Windows 260-character path limit: store.begin_edit could not copy start\pictures\device-photo.png ("Device map picture not kept") and the dialog stayed empty. Normal paths work. Check long-path handling in store.begin_edit / the edit folder (\\?\ prefix or shorter temp names) and show a message instead of failing silently.
113. CLOSED (C-VJTABS 2026-10-12: not a gap; devices/display/vjoy-tabs is unexposed (vjoy_status.py:41-50 expose False), Options never shows it, VJoyStatus.setPinned is the only writer and already notifies; probe in .agent-logs/C-VJTABS.log). (2026-10-12, found by W2-UI in the audit clean-up, from reading the code, not tried in the program) Changing the "vjoy-tabs" setting in Options may not update the vJoy tab bar until refresh() or a restart: nothing tells the bar (HUB.changed) when Options writes that setting; only VJoyStatus.setPinned does. Check and fix at the owner (gremlin/ui/vjoy_status.py).
114. DONE (batch C, C-OSCDEAD 2026-10-12: updateInputSettings and the OscAddDialog edit branch removed, openForEdit renamed openWith; tests on applySettings). (2026-10-12, found by OSC-TEST in the audit clean-up, from reading the code) Dead OSC edit path: OscDeviceManagementModel.updateInputSettings (gremlin/ui/osc_device_model.py ~:838) is no longer reached from the screens, and the `editing && editUid` branch in OscAddDialog.accept() (qml/OscAddDialog.qml:501-508) is dead because openForEdit is only called with "" (OscPage.qml:151, WindowOscMonitor.qml:49). Edit Settings now goes through OscLayoutModel.applySettings (S146). Candidate for the next removal wave (tests that call updateInputSettings move to applySettings).
115. (2026-10-12, W2-CORE audit clean-up, left on purpose; KEEP — user 2026-10-12: "leave the code as is for now. keep a record, but do not remove. I have one other person testing, so I need to keep the code for him.") Test-only program code still in place, each with many test callers: Profile.bind_devices (empty, ~15 test uses, with the bind parameter), Library.remove_unused (11), plugin_manager.create_instance (82; check the scripting spec first, user scripts may call it), module_file.start_fresh (8), Script.get_variable. config.init_calibration/set_calibration stay (03 S111). Move the tests to the program paths and remove, in a later clean-up.
116. DONE (batch C, C-DTAP: virtual timers, test_matrix_flow + test_double_tap_tempo). (2026-10-12, full run of the Xbox list batch, seed in .agent-logs) Load flake: test/unit/action_matrix/test_matrix_flow.py::test_flow_action[double-tap-key-pane_keyboard] failed once under the 6-part load ({"single": [], "double": [button 4 press/release]}), passed 3 of 3 alone. Double-tap decides by a time window, so a slow machine can read two taps as one double. Make the check wait on the action's own timer (gremlin.clock) instead of wall time, or give it the same grace other timing tests use.
122. CLOSED (C-PHOTORACE 2026-10-12: not a race; the generator correctly draws the visible background ~80 ms after the test read the folder; background_key (store.py:1647) ignores deviceImage and DevicePhotoMaker.rendered re-checks before writing; test now waits for the maker). (2026-10-12, Xbox pads full run; not this batch) test_module_setup_photo_edit.py::test_save_after_import_image_names_it_in_one_write failed once under the 6-part load (an extra pictures/device-photo.png listed after Save with a new Device Image) and passed 2 of 2 alone. Possible race from the Device Image work: a generated-picture run queued before the Save may still write device-photo.png afterwards. Not verified; trace the generator queue vs store.set_device_image (03 Device Image statements) and make the test wait on the generator.
125. DONE (batch C, C-DTAP; other _wait() calls in test_osc_run.py, e.g. test_button_no_value_uses_input_delay_and_trigger, have the same weakness, not changed). (2026-10-12, batch B full run) Load flake: test_osc_run.py::test_new_press_restarts_the_release_timer and ::test_server_default_delay_used_when_input_has_none failed once under the 6-part load (the release came late: two presses, no release after 670 ms of wall-clock waits); the file passes 2 of 2 alone and was not changed today. Same kind as 116: the test waits wall-clock time for a timer; make it drive the program clock.
126. (2026-10-12, CI 38258772966 on 273c2bd9; watch) CI unit-1: history_stable_smoke.py ended without a RESULT line (all 5 test_history_window_stable setups errored); the stack showed the smoke inside settle() -> deferred_write flush -> live_debug -> util.logs_dir mkdir; output cut at 2,000 chars. Locally: passes 3/3 alone and in a CI-seed (481347) 3-part rerun. CI passed on c52f7205 and 03e02cd7. Likely CI-runner slowness; if it repeats, raise the smoke output kept on failure (more than 2,000 chars) to see why it ended.
127. DECIDED (user 2026-10-12: "remove the old feature and code related to it. I dont see a pin"; batch C, C-TABROW). (2026-10-12, found by C-VJTABS): no screen calls VJoyStatus.setPinned any more (the only one, VJoyStatusPopup from 47c3b6ac, was removed in cleanup batch A, test_cleanup_batch_a.py:71); with the default vjoy-tabs [] a user has no way to show a vJoy tab in the device bar, and extra-tabs has no editor either. Decide: restore a way to choose the tabs (where?), or drop the vJoy tabs feature (setPinned, the settings, the test test_handson_F4_tabs.py). Spec pages 06 section 10 and 01.
128. (2026-10-12, found by C-DTAP under a heavy load run: 4 copies + 16 CPU-load processes) 3 test processes crashed with an access violation while creating the QApplication (joystick_gremlin.py:1049), right after a stall-watch report, before any test ran. Not caused by the tests; cause not checked. A start-up crash under heavy load.
129. DONE (batch F, F-LEAK: test_trace_osc_setup.py traced fixture now clears the saved OSC ticks; test_trace_osc_core starts from known ticks). (2026-10-12, CI 38267023157 on e84790ac) Order leak: test_trace_osc_core.py::test_area_ticks_choose_lines_and_are_saved expected the OSC trace ticks ["receive"] but found all five areas ticked: an earlier test in the same process left trace OSC areas ticked. Passes 2 of 2 alone. Find the leaking test (CI seed in the log, unit-1) and make it restore the trace settings (or the trace test reset them first).
130. (2026-10-12, found by F-LEAK, not changed) Tests that use the qapp fixture build the real JoystickGremlinApp in-process (test/conftest.py:204 qapp_cls), whose __init__ connects watchdog.apply to configChanged (joystick_gremlin.py:1004-1005). A later test that switches to its own new settings file and sends configChanged then fails reading an unregistered setting (seen: test_final_01 s44, fixed by registering the program settings). A conftest guard (disconnect the session app's configChanged listeners for such tests, or register the program settings in the fixture) would cover the rest.
