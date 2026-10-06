# To do

Work that is known and parked. Each item names its tracker ref (UI issues
tracker) so the details stay in one place.

## ONE-TIME CATCH-UP (agreed with the user 2026-10-06) — read this first

A short-term exception to "How we work" in `claude/system-maps.md`, to get
a clean baseline fast. **When it ends, the proper process applies again in
full** (trace first, independent re-trace, a test that fails on the old
code for each fix, small batches, push + CI per batch).

**Scope:** fix the open gap-list entries (`claude/gap-list.md`) that are
bugs. No new features: GL-029 (profile recovery copy) and the parked OSC
items (section 9) are deferred.

**Each batch:**
1. Fix in parallel: agents each own separate files; if a fix breaks
   something it is fixed at once, in that batch.
2. At the end of the batch: a short batch test plan (what was fixed, how
   each fix is checked, from the spec) appended to
   `claude/catchup-test-plan.md`.
3. Full LOCAL test: whole suite in random order + lint baseline + the
   batch plan's checks; fix anything that fails before the batch closes.
4. Commit locally (Spec: lines as usual). **No push, no CI** during the
   catch-up.
5. Update the gap list (done marks) and the tracker's GL entries.

**Batches:** 1 = the three redesigns in parallel (Run lifecycle, module
files, actions; maps in `claude/system-maps.md`); 2 = urgent fixes +
behaviour/UX by subsystem (~8 agents); 3 = text, glossary, help and
clean-up (~3 agents).

**At the end:** one full test plan for the code base (from the batch plans
and the spec) → write the missing tests → full local run (with the user's
Gremlin closed, so the integration/vJoy tests run) → fix → push everything
once → CI → fix → **that is the baseline; back to the proper process.**

**Still in force throughout:** change control (a fix that would change the
spec goes to the user first, `.claude/CLAUDE.md`), the Spec: line on every
commit, the program thread and layer rules, off-screen/safety rules.

**User notes:** the user may use their own Gremlin during the catch-up;
integration tests skip while it is open (run them at the end with it
closed); full runs load the PC for ~3 min each.

**Status:** CI baseline fixes pushed up to 0e790f73 (hang-watch heartbeat
and enum race); that CI run's result was pending when the catch-up was
agreed. Catch-up not started yet (next: batch 1).

## Next up (updated 2026-10-06)

Stages 0-3 are written out in `claude/system-maps.md` ("The plan").

- [x] **Stage 0 – Program map and behaviour spec** (2026-10-06):
  `claude/program-map/`, approved (all decisions as recommended).
- [x] **Stage 0 – Gap list** (2026-10-06): `claude/gap-list.md`, 309
  entries GL-001..GL-309 in work order; 14 hands-on checks listed at its end.
- **Change control:** every behaviour change goes through the spec; if it
  alters a statement or decision, tell the user first and update the spec.
- [x] **Stage 1 – Safety net** (2026-10-06): CI (`.github/workflows/ci.yml`),
  random order, lint baseline (`tools/pyright_baseline.py`), `gremlin/validate.py`
  (report-only), journey tests (`test/journeys/`), gap-list section 1 tests,
  `claude/decisions.md`. Left: GL-016 hands-on checks (user).
- [ ] **NEXT: Stage 2, redesign 1 – Run lifecycle (map 3 in
  `claude/system-maps.md`)**, approved 2026-10-06; the user said to start
  it once CI is green. Closes AU-116/GL-047 and AU-117, gap-list section 3.
  Start with tests that lock in today's Run/Stop behaviour, then
  `gremlin/run_scope.py` with its guard test (see "How we work").
  Then module files (map 1), then actions (map 2).
- [x] **AU-119 / GL-001 – fixed short waits** (Stage 1). Left over: about
  170 `qWait` calls in the off-screen window smoke scripts
  (print_export, button_map_*, usability_smoke); fix them as those areas
  are touched.
- [ ] **AU-27 – Mirrored Copy Button Map takes two undos.** Not verified yet
  (hands-on check in the gap list, GL-184).

## CI (state 2026-10-06)

- `.github/workflows/ci.yml` runs on every push: lint baseline
  (`tools/pyright_baseline.py`) and the full suite in random order via
  `test/run_tests.py --random-order --parts 2` (seed printed in the log).
- First run (2026-10-06 16:08) was a false green: the temp
  USERPROFILE made `poetry run` use an empty environment, and the runner
  passed parts with no result. Fixed in 9297578c (CI uses the project's
  Python; the runner fails a part with no summary).
- Second run: 1 failure, `test_modules_import_alone` counted as stalled on
  the 4-core runner; fixed in 739ef792 (waits on its processes from the
  main thread). Third run in progress after 739ef792.
- On CI: 71 integration tests skip (no vJoy there); the rig golden pixel
  comparison skips on GitHub.
- **Open questions for the user:** every push goes to both
  `Gremlin-Platforms` and `develop`, so CI runs twice and a failure emails
  twice (could limit CI to one branch). The older "CI Tests" workflow has
  been failing since 2026-10-04 (left untouched).

## Follow-ups noted during Stage 1 (not yet in the gap list)

- Direct time reads still outside `gremlin.clock`: `action_plugins/chain`
  (`time.time`, tests patch it), `gremlin/user_script.py` periodic loop
  (`time.monotonic`), `gremlin/ui/device.py` axis time series (GL-265),
  `vjoy/vjoy.py` keep-alive.
- `gremlin/validate.py`: PROFILE-UNUSED-ACTION also fires for new actions
  open in a pane and for actions kept for Undo (it is a warning only);
  `after_stop()` can't see Tempo / Double Tap / Smart Toggle Qt timers
  (comes with run_scope, GL-047).
- A renamed stick keeps its card order slot but loses its saved card size
  and stack (keyed by name slug).
- `import_module_file` now says "That file could not be read." for a JSON
  file whose top level isn't an object (was "That file is not a module
  file.").
- Log noise in tests: "No parameter with key ('global','internal',
  'twin-device-names')".
- `test/integration/conftest.py` `_neutral_vjoy` resets the real vJoy
  device between modules (as the integration tests already drive vJoy;
  they skip while the user's Gremlin is open).
- Hands-on checks for the user: the list at the end of
  `claude/gap-list.md` (GL-016 and others).

## On hold (user's choice)

- **AU-56** – 200% UI scale on a small screen cuts off window contents.
- **N22** – Inconsistent controls in action editors.

## Done (kept for reference)

- [x] **Hidden Cards in the Home menu, no window** (2026-10-03).
- [x] **Audits 2 and 3** (2026-10-05/06: 6edbdcd8 .. a1459e22). Every fix
  traced end to end and re-traced independently; tracker AU-76..AU-115.

## Button Map (planned 2026-10-04)

- [ ] **BM41 – A bigger page for the Button Map.** The page (32000 x 18000
  page units, `worldPageW/H` in `qml/VkbRigEditor.qml`; `pageW/pageH` saved
  by `gremlin/ui/hardware_profile.py`) grows so there is more room around
  the photo; the photo frame (inner page 24000 x 13500, `innerPad*`) keeps
  its size, centred. Every position is a fraction of the page (`fx`, `fy`,
  `rig_coords.js`), so all of them change meaning. Backward compatibility
  is not a concern (not released). To do:
  - New page size (16:9 kept) and paddings; `photoWell` follows.
  - Zoom-in limit from 8x to about 10x (the page and photo look ~23%
    smaller at the same zoom).
  - Rulers 0-100 over the new page; grid sizes keep their page units.
  - Convert the built-in maps and templates in the repo (`qml/maps`), redo
    the golden images and layout tests.
  - Exports: the print area and Scale unaffected; a whole-page export just
    has more margin.
  - Open questions: (1) 30% per side (about 70% more area, recommended) or
    30% more area (about 14% per side)? (2) The user's own maps: the
    program converts maps with the old page size as they load
    (recommended), the user re-places them, or a one-time conversion of
    their files (only with their go-ahead, on a backup).

## Program-wide history (planned 2026-10-05)

- [x] **G-HISTORY – History across the whole program.** (built 2026-10-05: 4597e486, 20155486, 780f16b8; Undo added where it was missing: Module Setup, Calibration, Configuration page) A shared history
  in its own files (per area: input modules, output modules, action
  editor, Button Map) that the program reads and writes, so earlier
  versions can be seen and restored, also after a restart. To be fleshed
  out with the user first: notes and open questions in
  `claude/history-notes.md`.
- [x] **G-LIBLEAK – Unused actions written to the profile.** (fixed 2026-10-05: b4539968) Some edit
  paths drop an action's link without removing the action, and saving
  writes every action, so the file grows (the user's profile: 1,172
  actions, 408 used). Under discussion: fix each leak, and skip unused
  actions when writing the file (kept in memory so Undo still works).

## OSC (parked 2026-10-02: leave OSC alone for now)

- [ ] **B15 – Default ports clash and disagree.** The program listens on 8000
  when nothing is set (`gremlin/osc.py` `DEFAULT_PORT`), Options shows 8001
  (`gremlin/ui/osc_option.py` `OscInputHostModel.port_default`), and output
  also defaults to 8000 (`DEFAULT_OUTPUT_PORT`). Suggested: input 8000,
  output 9000 (the usual OSC convention), one constant used everywhere.
- [ ] **B16 – OSC Add has controls that do nothing.** "Change" is saved as
  Axis; "message vs data" and "Trigger on message" with its delay are never
  passed on (`qml/OscAddDialog.qml`, `qml/OscDevice.qml` only sends the
  address and Button/Axis). The backend has no per-input settings for these;
  auto-release and its delay exist only as global options. Choose: build
  per-input support, or hide the controls until it exists.
- [ ] **B17 – OSC import promises change and encoder types.** Import turns
  C and E suffixes into plain axes (`gremlin/ui/osc_device_model.py`
  `_parse_import_line`), while `qml/OscImportDialog.qml` says otherwise.
  Goes with B16: real types, or fix the text.
