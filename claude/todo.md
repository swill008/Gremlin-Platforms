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

## Answered by the user (2026-10-07) — to do

2. **CI on one branch only** (user: yes). Run `.github/workflows/ci.yml` on
   pushes to `Gremlin-Platforms` only (not `develop`), so each push runs CI
   once and a failure emails once. Pairs with item 16 (faster CI).
3. **Encode big Button Map exports off the main thread** (user: yes). Today
   `hardware_profile._save_image` encodes the PNG/JPG on the main thread, so
   a large export freezes the window (seen on CI, develop run
   37607816152: Print & Export stalled > 30 s). Spec first (07, export),
   then encode on a worker via `gremlin.threads` with the window showing
   it's busy; the Print & Export tests wait for the result.
4. **Remove the old "CI Tests" workflow** (user: yes). It has been failing
   since 2026-10-04 and is replaced by `ci.yml`; find its file in
   `.github/workflows/` (python-test.yml or pylint.yml) and check nothing
   else uses it before removing.

## Hands-on checks (user)

5. **Try 1.0.25 by hand:** `claude/catchup-test-plan.md` (batch checks),
   `claude/final-test-plan/` (per spec page), and the list at the end of
   `claude/gap-list.md` (GL-016 and others).

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
13. Startup time: load rarely used pages on first open; a startup-time test.
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

## On hold / parked (user's choice)

32. **N22** – Inconsistent controls in action editors (on hold).
33. **OSC** (parked 2026-10-02: leave OSC alone for now):
    - **B15 – Default ports clash and disagree.** The program listens on
      8000 when nothing is set (`gremlin/osc.py` `DEFAULT_PORT`), Options
      shows 8001 (`gremlin/ui/osc_option.py` `OscInputHostModel.port_default`),
      and output also defaults to 8000 (`DEFAULT_OUTPUT_PORT`). Suggested:
      input 8000, output 9000 (the usual OSC convention), one constant used
      everywhere.
    - **B16 – OSC Add has controls that do nothing.** "Change" is saved as
      Axis; "message vs data" and "Trigger on message" with its delay are
      never passed on (`qml/OscAddDialog.qml`, `qml/OscDevice.qml` only
      sends the address and Button/Axis). The backend has no per-input
      settings for these; auto-release and its delay exist only as global
      options. Choose: build per-input support, or hide the controls until
      it exists.
    - **B17 – OSC import promises change and encoder types.** Import turns
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
