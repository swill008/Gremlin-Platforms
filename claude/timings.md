# How long things take (user 2026-10-09)

Measured times, so estimates match reality. Add a row when a step finishes:
start and end from the clock, not a guess. Use the medians here when quoting
a time to the user.

## Rules of thumb (from the rows below, 2026-10-09, 69 rows)

| Kind | Rows | Took vs estimate | Quote |
|---|---|---|---|
| Agent fix / feature / docs | 36 | about 1/4 to 1/3 | 3-8 min per agent; a batch of parallel agents ~10 min |
| Refactor | 12 | about 1/2 | 5-10 min per agent |
| Review / read-only study | 3 | about 1/10 | 5-10 min with parallel agents |
| Full test run + lint | 14 | on target | 5-6 min |
| CI on a push | 3 | on target | ~10 min |

End to end, a batch is: agents (~10 min) + lead checks and map (~5 min) +
full run (~5 min) + commit/push (~2 min) + CI (~10 min, in the background).
Not yet timed: the lead's own steps (planning, applying results, tracker and
progress updates). Log those from now on so whole-batch quotes are measured.

| Date | Task | Kind | Estimated | Took | Notes |
|---|---|---|---|---|---|
| 2026-10-09 | Full run `run_tests.py --random-order` + lint | test | ~5 min | 6 min | 6 parts ~4 min, lint ~1.5 min; part 6 stalled once under load (to-do 47) |
| 2026-10-09 | Fix 2 small test failures (colour tokens, Help loader) | fix | 5 min | ~4 min | lead alone |
| 2026-10-09 | One Button Map window smoke (`flows`) alone | test | — | 7 s | 34 s+ under full-run load |
| 2026-10-09 | CI run on a push (Gremlin-Platforms branch) | ci | 10–15 min | 10 min | 08:22–08:32 |
| 2026-10-09 | Fix + prove a flaky test (FX2 twin pack, 3 files) | fix | ~5 min | 4 min | 08:32–08:36 |
| 2026-10-09 | Full run + lint (second today) | test | ~6 min | 4 min | 08:34–08:38, all 6 parts green |
| 2026-10-09 | Help list (S138): spec, build, screenshots, 10 tests (1 agent) | feature | 25–30 min | 10 min to built + tests (08:40–08:50 incl. full run) | lead built, HL-tests 5 min |
| 2026-10-09 | Full run + lint (third today) | test | ~5 min | 4 min | 08:46–08:50, all green |
| 2026-10-09 | Help gap audit: all 10 spec pages vs Help (3 read-only agents) | research | ~10 min | 5 min | 08:53–08:58 |
| 2026-10-09 | CI run on a push | ci | ~10 min | 10 min | 08:50–09:00, green |
| 2026-10-09 | Undo Delete Mode per S46a: 9 tests, 1 gap fixed (UDM) | fix | ~25 min | 4 min | 09:09–09:13 |
| 2026-10-09 | Options reveal (SM-options) | feature | ~25 min | 4 min | 09:09–09:13 + Pulse switch |
| 2026-10-09 | Help: Getting started 3 passes, 8 new topics (HW-start) | docs | ~35 min | 5 min | 09:09–09:14 |
| 2026-10-09 | Main window reveal + Pulse (SM-main) | feature | ~30 min | 6 min | 09:09–09:15 |
| 2026-10-09 | Help: Options + Device Library 3 passes, 10 new topics (HW-options) | docs | ~35 min | ~6 min | 09:10–09:15 |
| 2026-10-09 | Help side of links + link-resolve test (SM-help) | feature | ~30 min | 6 min | 09:09–09:15 |
| 2026-10-09 | Help writers 3-5 (home, tools, config) | docs | ~35-40 min | ~6 min each | 09:09–09:15 |
| 2026-10-09 | Full run + lint (fourth today) | test | ~5 min | 4 min | 09:18–09:22, all green |
| 2026-10-09 | CI run on a push | ci | ~10 min | 12 min | 09:23–09:35, green |
| 2026-10-09 | Release workflow (build + publish) | release | ~15 min | 4 min | 09:35–09:39 |
| 2026-10-09 | MessageLine (P-message) | feature | ~15 min | 2 min | 09:47–09:48 |
| 2026-10-09 | Wording fixes to-do 56 (W56) | fix | ~15 min | 2 min | 09:47–09:48 |
| 2026-10-09 | SearchBox (P-search) | feature | ~20 min | 3 min | 09:47–09:50 |
| 2026-10-09 | SectionHeading, EmptyState, UndoBar (P-pieces) | feature | ~20 min | 4 min | 09:46–09:50 |
| 2026-10-09 | DangerButton + ConfirmDialog (P-confirm) | feature | ~20 min | 4 min | 09:46–09:50 |
| 2026-10-09 | FilePicker + folder memory (P-picker) | feature | ~20 min | 5 min | 09:47–09:52 |
| 2026-10-09 | Program map guard test (MAP-guard) | test | ~10 min | 1 min | 09:53–09:54, 96 files unmapped |
| 2026-10-09 | Profile recovery copy to-do 55 (R-copy) | feature | 30-40 min | 9 min | 09:47–09:56 |
| 2026-10-09 | Phase B tools2: 5 windows onto shared pieces (B-tools2) | refactor | ~25 min | 7 min | 09:51–09:58 |
| 2026-10-09 | Phase B opts: Options + Help onto shared pieces (B-opts) | refactor | ~25 min | 8 min | 09:51–09:59 |
| 2026-10-09 | Map catch-up pages 03-05 (MAP-2) | docs | ~15 min | 5 min | 09:55–10:00 |
| 2026-10-09 | Phase B lib: Device Library windows (B-lib) | refactor | ~25 min | 9 min | 09:51–10:00 |
| 2026-10-09 | Map catch-up pages 01, 02, 09 + README (MAP-1) | docs | ~15 min | 7 min | 09:55–10:02 |
| 2026-10-09 | Map catch-up pages 06, 07, 08, 10 (MAP-3) | docs | ~15 min | 7 min | 09:55–10:02 |
| 2026-10-09 | Phase B main: main window + Home pages (B-main) | refactor | ~25 min | 9 min | 09:56–10:05 |
| 2026-10-09 | Phase B tools1: History, Calibration, Module Setup, Device Pack (B-tools1) | refactor | ~25 min | 14 min | 09:51–10:05 |
| 2026-10-09 | Phase B config: 7 QML + 2 models step labels (B-config) | refactor | ~25 min | 15 min | 09:51–10:06 |
| 2026-10-09 | Help text update part 1 (HF-1) | docs | ~15 min | 5 min | 10:07–10:12 |
| 2026-10-09 | Help text update part 2 (HF-2) | docs | ~15 min | 2 min | 10:08–10:10 |
| 2026-10-09 | Map entries from Phase B (MAP-fin) | docs | ~15 min | 5 min | 10:08–10:14 |
| 2026-10-09 | Title bar shows version (to-do 57, lead) | feature | ~5 min | 6 min | 10:15–10:21 |
| 2026-10-09 | Phase B map: Button Map windows (B-map) | refactor | ~25 min | 27 min | 09:51–10:18 |
| 2026-10-09 | Journey j02 to shared question (J-modes) | test | ~10 min | 1 min | 10:27–10:28 |
| 2026-10-09 | Journey j05 + layers golden (J-map) | test | ~15 min | 2 min | 10:27–10:29 |
| 2026-10-09 | Final full run + lint for the batch | test | ~5 min | 5 min | 10:29–10:34, all green |
| 2026-10-09 | Full run (chipRows + View Full Help) | test | ~5 min | 6 min | 10:49–10:55, all green |
| 2026-10-09 | Device Library toolbar button (DL-tool) | feature | ~10-15 min | 4 min | 10:58–11:02 |
| 2026-10-09 | Full run (titles + toolbar), after fixing the title test crash | test | ~5 min | 5 min | 11:12–11:17, all green |
| 2026-10-09 | Plugged-in by id: shared check + Delete Device (ID-check) | fix | ~15 min | 4 min | 11:20–11:24 |
| 2026-10-09 | Plugged-in by id: Button Map cover, Module Setup (ID-map) | fix | ~15 min | 4 min | 11:22–11:26 |
| 2026-10-09 | Plugged-in by id: Device Library + copy (ID-lib) | fix | ~15 min | 8 min | 11:21–11:29 |
| 2026-10-09 | Id not name: Auto Mapper + Device Pack (ID-misc) | fix | ~12 min | 6 min | 11:24–11:30 |
| 2026-10-09 | Map entries for the id batch (MAP-id) | docs | ~8 min | 3 min | 11:30–11:33 |
| 2026-10-09 | Full run (plugged-in by id batch) | test | ~5 min | 5 min | 11:30–11:35, all green |
| 2026-10-09 | Device classes: Library callers (CLS-lib) | refactor | ~20 min | 5 min | 11:40–11:45 |
| 2026-10-09 | Device classes core + guard (CLS-core) | refactor | ~25 min | 6 min | 11:40–11:46 |
| 2026-10-09 | Twins: export by id (TW-export) | fix | ~15 min | 3 min | 11:45–11:48 |
| 2026-10-09 | Twins: device list by id (TW-list) | fix | ~15 min | 3 min | 11:45–11:48 |
| 2026-10-09 | Device classes: other callers (CLS-rest) | refactor | ~20 min | 9 min | 11:40–11:49 |
| 2026-10-09 | Twins: Device Pack window (TW-window) | fix | ~20 min | 6 min | 11:44–11:50 |
| 2026-10-09 | Map entries classes + twins (MAP-cls) | docs | ~8 min | 2 min | 11:50–11:52 |
| 2026-10-09 | Full run (classes + twins export) | test | ~5 min | 5 min | 11:50–11:55, all green |
| 2026-10-09 | Import by id: window (IM-window) | fix | ~15 min | 2 min | 11:53–11:55 |
| 2026-10-09 | Import by id: Python (IM-py) | fix | ~12 min | 6 min | 11:53–11:59 |
| 2026-10-09 | Full run (twins + import by id) | test | ~5 min | 5 min | 11:59–12:04, all green |
| 2026-10-09 | Class table tidy-up + vJoy by id (CT-table) | refactor | ~10 min | 4 min | 12:13–12:17 |
| 2026-10-09 | Class table: Copy/Swap one rule (CT-callers) | refactor | ~10 min | 3 min | 12:13–12:16 |
| 2026-10-09 | Full run (class-table tidy-up) | test | ~5 min | 5 min | 12:16–12:21, green except the 2 import test errors fixed after |
| 2026-10-09 | Tracker review AU items (TR-au) | review | ~35 min | 3 min | 12:24–12:27 |
| 2026-10-09 | Tracker review older groups (TR-review) | review | ~35 min | ~3 min | 12:24–12:27 |
| 2026-10-09 | Tracker new items since 7 Oct (TR-new) | review | ~35 min | 5 min | 12:24–12:29, 89 items |
| 2026-10-09 | Timing check and rules of thumb (lead) | docs | ~3 min | 3 min | lead alone |
| 2026-10-09 | LD design study: LIB-pattern (read-only agent) | review | ~5 min | 1 min | 12:46–12:47 (36 s) |
| 2026-10-09 | LD design study: LD-trace (read-only agent) | review | ~5 min | 1 min | 12:46–12:47 (58 s) |
| 2026-10-09 | LD design study: PACK-fit (read-only agent) | review | ~5 min | 1 min | 12:46–12:47 (51 s) |
| 2026-10-09 | Timing rule in CLAUDE.md + memory + progress page (lead) | docs | ~3 min | 3 min | 12:46–12:49 |
| 2026-10-09 | LD study review page + progress (lead) | docs | ~5 min | 4 min | 12:48–12:52; whole study 12:46–12:52 = 6 min vs my first quote of 25 |
| 2026-10-09 | LD stand-alone: permanent ids (LD-model) | feature | ~15 min | 3 min | 12:57–13:00 |
| 2026-10-09 | LD stand-alone: module file IO (LD-store) | feature | ~15 min | 3 min | 12:57–13:00 |
| 2026-10-09 | LD stand-alone: action + condition refs (LD-refs-a) | feature | ~15 min | 4 min | 12:58–13:02 |
| 2026-10-09 | LD stand-alone: macro/script/validate refs (LD-refs-b) | feature | ~15 min | 3 min | 12:58–13:01 |
| 2026-10-09 | LD stand-alone: Device Pack + Library copy (LD-pack) | feature | ~20 min | 5 min | 12:58–13:03 |
| 2026-10-09 | LD stand-alone: spec, map, Help (LD-map) | docs | ~15 min | 4 min | 12:58–13:02 |
| 2026-10-09 | LD stand-alone: profile v15 + migration (LD-profile) | feature | ~20 min | 5 min | 12:58–13:03 |
| 2026-10-09 | LD stand-alone: Library, class table, Home card (LD-lib) | feature | ~15 min | 4 min | 12:58–13:02 |
| 2026-10-09 | LD stand-alone: module file header keys (LD-store follow-up) | fix | ~5 min | 1 min | 13:03–13:04 |
| 2026-10-09 | LD stand-alone: macro action + script page refs (LD-refs-c) | feature | ~10 min | 3 min | 13:01–13:04 |
| 2026-10-09 | LD stand-alone: map/spec follow-ups (LD-map) | docs | ~6 min | 1 min | 13:03–13:04 |
| 2026-10-09 | LD stand-alone: stored uid + one resolver (LD-refs-b follow-up) | fix | ~8 min | 3 min | 13:01–13:04 |
| 2026-10-09 | LD stand-alone: page, Save/*, Undo, note (LD-ui) | feature | ~20 min | 6 min | 12:58–13:04 |
| 2026-10-09 | LD stand-alone: Library save keeps v14 rows (LD-pack follow-up) | fix | ~5 min | 2 min | 13:03–13:05 |
| 2026-10-09 | LD stand-alone: Discard reloads the file (LD-ui follow-up) | fix | ~5 min | 2 min | 13:05–13:07 |
| 2026-10-09 | LD stand-alone: merge saves when file differs (LD-store follow-up) | fix | ~5 min | 1 min | 13:06 |
| 2026-10-09 | LD stand-alone: 11 old-behaviour tests moved to new spec (LD-tests) | test | ~10 min | 4 min | 13:03–13:07 |
| 2026-10-09 | LD stand-alone: reload signal + Undo drop on restore (lead) | fix | ~5 min | 2 min | 13:06–13:08 |
| 2026-10-09 | LD: 4 full-run failures fixed + profile copies check (lead) | fix | ~10 min | 6 min | 13:14–13:20 |
| 2026-10-09 | LD: backup moved to first save + full run #3 (lead) | fix | ~8 min | 9 min | 13:21–13:30 |
| 2026-10-09 | LD stand-alone WHOLE BATCH (11 agents, 3 full runs, commit, tracker) | feature | 45-60 min | 36 min | 12:56–13:32 |
| 2026-10-09 | LD card image: spec/map/Help (IMG-doc) | docs | ~8 min | 2 min | 13:45–13:47 |
| 2026-10-09 | LD card image: Python slots (IMG-py) | feature | ~10 min | 2 min | 13:45–13:47 |
| 2026-10-09 | LD card image: carry tests, found 2 gaps (IMG-carry) | test | ~12 min | 2 min | 13:46–13:48 |
| 2026-10-09 | LD card image: menu items + page wiring (IMG-qml) | feature | ~10 min | 4 min | 13:45–13:49 |
| 2026-10-09 | LD card image: card redraw on reload (IMG-py follow-up) | fix | ~4 min | 1 min | 13:49 |
| 2026-10-09 | LD card image: end-to-end test (IMG-e2e) | test | ~12 min | 3 min | 13:46–13:49 |
| 2026-10-09 | LD card image: Library Restore for built-ins (IMG-restore) | fix | ~12 min | 5 min | 13:49–13:54 |
| 2026-10-09 | LD card image: map + Help for Restore (LIB-doc) | docs | ~6 min | 1 min | 13:56–13:57 |
| 2026-10-09 | LD card image: Library window Restore e2e (LIB-e2e) | test | ~12 min | 3 min | 13:56–13:59 |
| 2026-10-09 | LD card image: Library actions audit on built-ins (LIB-audit) | test | ~12 min | 3 min | 13:56–13:59 |
| 2026-10-09 | LD card image: one-write Restore + Import carries layout (IMG-restore follow-up) | fix | ~8 min | 6 min | 13:54–14:00 |
| 2026-10-09 | LD card image + built-in Restore: full run (lead) | test | ~5 min | 6 min | 14:01–14:07, 2 flakes not from this batch |
| 2026-10-09 | History clear flake: cause found, test fixed (FLAKE-hc) | test | ~15 min | 3 min | 14:07–14:10 |
| 2026-10-09 | Clear History reaches every Library Undo (FIX-lu) | fix | ~8 min | 2 min | 14:11–14:13 |
| 2026-10-09 | Full run (Library undo fix) (lead) | test | ~5 min | 6 min | 14:14–14:20, all green |
| 2026-10-09 | OSC audit: 3 read-only agents + Add window pictures | review | ~10-12 min | 3 min | 14:26–14:29 |
| 2026-10-09 | OSC audit report page (lead) | docs | ~5 min | 4 min | 14:30–14:34 |
| 2026-10-09 | OSC history: Add window controls (OSC-hist-ui) | review | ~12 min | 2 min | 14:33–14:35 |
| 2026-10-09 | OSC history: runtime (OSC-hist-run) | review | ~12 min | 2 min | 14:33–14:35 |
| 2026-10-09 | OSC history: upstream GremlinEx design (OSC-hist-up) | review | ~12 min | 2 min | 14:34–14:36 |
| 2026-10-09 | CI Button Map stall: known CI-only stall (CI-bmap) | review | ~15 min | 2 min | 14:33–14:35 |
| 2026-10-09 | CI unsaved-after-plug: test leak in test_validate (CI-b4) | fix | ~15 min | 7 min | 14:33–14:40 |
| 2026-10-09 | OSC: rows + per-input settings (OSC-store) | feature | ~15 min | ~5 min | 14:45–14:50 |
| 2026-10-09 | OSC: module file IO + store reload (OSC-file) | feature | ~15 min | 3 min | 14:42–14:45 |
| 2026-10-09 | OSC: signals, *, Discard, note (OSC-backend) | feature | ~15 min | 3 min | 14:43–14:45 |
| 2026-10-09 | OSC: page model, Add/Import/Listen (OSC-uimodel) | feature | ~20 min | 5 min | 14:43–14:48 |
| 2026-10-09 | OSC: server + per-input behaviour (OSC-run) | feature | ~20 min | 6 min | 14:42–14:48 |
| 2026-10-09 | OSC: windows wiring (OSC-qml) | feature | ~20 min | 7 min | 14:43–14:50 |
| 2026-10-09 | OSC: server settings in Module Setup (OSC-opts) | feature | ~20 min | 7 min | 14:43–14:50 |
| 2026-10-09 | OSC: references by id, packs, Restore (OSC-refs) | feature | ~20 min | 7 min | 14:43–14:50 |
| 2026-10-09 | OSC: profile v16 + move (OSC-profile) | feature | ~20 min | 8 min | 14:43–14:51 |
| 2026-10-09 | OSC: spec, decisions, Help, INTERNAL INPUTS (OSC-doc) | docs | ~20 min | 8 min | 14:43–14:51 |
| 2026-10-09 | OSC: Options button opens OSC Module Setup (OSC-backend follow-up) | fix | ~5 min | 1 min | 14:50–14:51 |
| 2026-10-09 | OSC: Options layout (OSC-opts follow-up) | fix | ~5 min | 2 min | 14:50–14:52 |
| 2026-10-09 | OSC: friendly names by uid (OSC-file follow-up) | fix | ~8 min | 2 min | 14:50–14:52 |
| 2026-10-09 | OSC: port only when profile uses OSC (OSC-run follow-up) | fix | ~8 min | 1 min | 14:51–14:52 |
| 2026-10-09 | OSC: profile v16 + missing bindings never fire (OSC-profile incl. follow-up) | feature | ~20 min | 11 min | 14:43–14:54 |
| 2026-10-09 | OSC: carry-through tests (OSC-carry) | test | ~15 min | 1 min | 14:51–14:52 |
| 2026-10-09 | OSC: Listen TypeError fix in osc_bulk (lead) | fix | ~3 min | 2 min | 14:55–14:57 |
| 2026-10-09 | OSC: end-to-end tests, found Listen bug (OSC-e2e) | test | ~15 min | 5 min | 14:51–14:56 |
| 2026-10-09 | OSC: Device Pack honours pending OSC rows (OSC-refs follow-up) | fix | ~5 min | 2 min | 14:54–14:56 |
| 2026-10-09 | OSC: old tests to new behaviour (OSC-oldtests) | test | ~15 min | 8 min | 14:50–14:58 |
| 2026-10-09 | OSC: ThemedMenu in OscDevice.qml (OSC-qml fix) | fix | ~4 min | 1 min | 15:04–15:05 |
| 2026-10-09 | OSC: e2e test made order-proof (OSC-e2e fix) | test | ~10 min | 2 min | 15:04–15:06 |
| 2026-10-09 | OSC: Module Setup failures traced (OSC-opts) | review | ~10 min | 1 min | 15:04–15:05 |
| 2026-10-09 | OSC: Swap/S106 test setups (FIX-swap) | test | ~10 min | 2 min | 15:04–15:06 |
| 2026-10-09 | OSC: no OSC file on fresh install (OSC-file fix) | fix | ~8 min | 1 min | 15:06–15:07 |
| 2026-10-09 | OSC: backend start test for the fresh-install rule (lead) | test | ~3 min | 3 min | 15:07–15:10 |
| 2026-10-09 | OSC: final full run (lead) | test | ~6 min | 6 min | 15:10–15:16, all green |
| 2026-10-09 | OSC WHOLE BATCH (audit+history 6 agents, build 10+3+5 agents, 2 full runs) | feature | ~60-70 min | 50 min | 14:26–15:18 (build 14:42–15:18) |
| 2026-10-09 | OSC hands-on sender tool (OSC-sender) | feature | ~8 min | 2 min | 15:15–15:17 |
| 2026-10-09 | OSC functional check: 27 real loopback checks (OSC-func) | test | ~15 min | 3 min | 15:15–15:18 |
| 2026-10-09 | OSC spec: lock + Stop release (OSC-spec) | docs | ~6 min | 1 min | 15:17–15:18 |
| 2026-10-09 | OSC: Stop releases held buttons (OSC-stop) | feature | ~12 min | 2 min | 15:17–15:19 |
| 2026-10-09 | OSC functional check: Stop checks + re-run (OSC-func follow-up) | test | ~6 min | 1 min | 15:19 |
| 2026-10-09 | OSC functional report page (lead) | docs | ~3 min | 2 min | 15:21–15:23 |
| 2026-10-09 | Full run (OSC Stop release) (lead) | test | ~6 min | 6 min | 15:20–15:26, all green |
| 2026-10-09 | OSC features: addresses on Button Map + Home (BMAP) | feature | ~15 min | 9 min | 15:31–15:40 |
| 2026-10-09 | OSC features: encoder runtime + hooks (ENC-core) | feature | ~20 min | 5 min | 15:30–15:35 |
| 2026-10-09 | OSC features: zeroconf discovery (ZC) | feature | ~20 min | 4 min | 15:31–15:35 |
| 2026-10-09 | OSC features: feedback runtime + sync (FB-run) | feature | ~25 min | 5 min | 15:30–15:35 |
| 2026-10-09 | OSC features: traffic monitor (MON) | feature | ~20 min | 6 min | 15:30–15:36 |
| 2026-10-09 | OSC features: targets, output, addresses, discovery UI (TGT) | feature | ~20 min | 7 min | 15:30–15:37 |
| 2026-10-09 | OSC features: encoder UI + Import E (ENC-ui) | feature | ~15 min | 6 min | 15:31–15:37 |
| 2026-10-09 | OSC features: feedback list UI (FB-ui) | feature | ~20 min | 8 min | 15:30–15:38 |
| 2026-10-09 | OSC features: Send OSC action + output client (OUT) | feature | ~25 min | 9 min | 15:30–15:39 |
| 2026-10-09 | OSC features: spec, decisions, glossary, Help (DOC) | docs | ~25 min | 9 min | 15:31–15:40 |
| 2026-10-09 | OSC features: carry tests, found 2 gaps (CARRY) | test | ~15 min | 3 min | 15:38–15:41 |
| 2026-10-09 | OSC features: send_osc in build/labels, wording, 2 carry fixes (lead) | fix | ~8 min | 8 min | 15:40–15:48 |
| 2026-10-09 | OSC features: E2E 66 loopback checks (E2E) | test | ~20 min | 5 min | 15:38–15:43 |
| 2026-10-09 | OSC features: sync in Monitor + feedback retry after output off (lead) | fix | ~5 min | 8 min | 15:50–15:58 |
| 2026-10-09 | OSC full functional check 66/66 + report (lead) | test | ~5 min | 3 min | 16:03–16:06 |
| 2026-10-09 | Companion v5 research overview (COMP-research) | research | ~12 min | 2 min | 15:58–16:00 |
| 2026-10-09 | Companion v5 core OSC API (COMP-recv) | research | ~10 min | 2 min | 16:00–16:02 |
| 2026-10-09 | Companion v5 Generic OSC module (COMP-send) | research | ~10 min | 2 min | 16:00–16:02 |
| 2026-10-09 | OSC features: final full run (lead) | test | ~6 min | 6 min | 16:02–16:08, all green |
| 2026-10-09 | Real OSC window screenshots (SHOT) | review | ~10 min | 2 min | 16:11–16:13 |
| 2026-10-09 | OSC look: Button Map style guide (STYLE step 1) | docs | ~6 min | 4 min | 16:18–16:22 |
| 2026-10-09 | Companion export research: not safe (CEXP) | research | ~25 min | 2 min | 16:18–16:20 |
| 2026-10-09 | OSC tabs/Companion/Help spec (DOC) | docs | ~20 min | 3 min | 16:18–16:21 |
| 2026-10-09 | OSC Monitor columns + hover + look (MON) | fix | ~15 min | 4 min | 16:18–16:22 |
| 2026-10-09 | OSC functional check: Companion-style, 88 checks (E2E) | test | ~25 min | 5 min | 16:19–16:24 |
| 2026-10-09 | OSC Help chapter, 33 topics incl. technical reference (HELP) | docs | ~25 min | 7 min | 16:18–16:25 |
| 2026-10-09 | OSC Module Setup tabs + Add Companion (TABS) | feature | ~25 min | 8 min | 16:19–16:27 |
| 2026-10-09 | OSC Companion templates, off/on values, 2 case fixes (CFB) | feature | ~25 min | 8 min | 16:19–16:27 |
| 2026-10-09 | OSC page: OSC Setup…, Copy for Companion, empty text (PAGE) | feature | ~20 min | 9 min | 16:19–16:28 |
| 2026-10-09 | OSC polish pass to Button Map look (STYLE step 2) | feature | ~20 min | 2 min | 16:29–16:31 |
| 2026-10-09 | Help vs code audit, 27 Help fixes (HELP-CHECK) | docs | ~15 min | 6 min | 16:29–16:35 |
| 2026-10-09 | 5 small OSC code fixes from the Help audit (lead) | fix | ~8 min | 6 min | 16:36–16:42 |
| 2026-10-09 | Final full runs + 2 small fixes (lead) | test | ~13 min | 20 min | 16:42–17:02 |
| 2026-10-09 | Fix your QML warnings (binding, _targetForm) + guard test (lead) | fix | ~10 min | 20 min | 17:05–17:25 |
| 2026-10-09 | Window size warnings traced: old tool-window restore gap (GEOM) | review | ~12 min | 1 min | 17:04–17:05 |
| 2026-10-09 | Tool windows: frame-aware restore, best screen (WPY) | fix | ~20 min | 2 min | 17:13–17:15 |
| 2026-10-09 | Tool windows: size set once (WQML) | fix | ~15 min | 5 min | 17:13–17:18 |
| 2026-10-09 | Tool window fit: 2 full runs (1 load stall) (lead) | test | ~6 min | 14 min | 17:18–17:32 |
| 2026-10-09 | Card resize stolen by scrolling: trace + fix (lead) | fix | ~10 min | 2 min | 20:08–20:10 |
| 2026-10-09 | Card resize real-drag test, fail-on-HEAD proof (RTEST) | test | ~15 min | 3 min | 20:09–20:12 |
| 2026-10-09 | Full run (parts ~5.5 min each under load) + 1 flake rerun (lead) | test | ~3 min | 8 min | 20:12–20:20 |
| 2026-10-09 | Uncommanded inputs: logs, History, profile diff, HidHide read (lead) | review | ~10 min | 10 min | 20:11–20:21 |
| 2026-10-09 | Uncommanded inputs: HidHide code audit (HHAUDIT) | review | ~20 min | 4 min | 20:21–20:25 |
| 2026-10-09 | Uncommanded inputs: Windows timeline (WINTL) | review | ~15 min | 4 min | 20:21–20:25 |
| 2026-10-09 | Uncommanded inputs: vJoy writers, SC files (VJAUDIT) | review | ~20 min | 5 min | 20:21–20:26 |
| 2026-10-09 | Findings page (lead) | report | ~5 min | 2 min | 20:26–20:28 |
| 2026-10-09 | Uncommanded inputs: static audit of tests and runs (STATIC) | review | ~20 min | 5 min | 20:31–20:36 |
| 2026-10-09 | Uncommanded inputs: full run with real drivers blocked (DRVTRACE) | test | ~25 min | 9 min | 20:31–20:40 |
| 2026-10-09 | Findings page v2 (lead) | report | ~5 min | 2 min | 20:40–20:42 |
| 2026-10-09 | Trace: contract + 7 agents briefed (lead) | plan | ~5 min | 2 min | 20:52–20:54 |
| 2026-10-09 | Trace: gremlin/trace.py API + 8 tests (CORE) | feature | ~12 min | 3 min | 20:53–20:56 |
| 2026-10-09 | Trace: RAW/WIRING/EVENT taps + 6 tests (TAPIN) | feature | ~15 min | 4 min | 20:53–20:57 |
| 2026-10-09 | Trace: OUTPUT tap, out-of-step watch + 9 tests (TAPOUT) | feature | ~15 min | 5 min | 20:53–20:58 |
| 2026-10-09 | Trace: spec 01/02/06, map, glossary, Help (DOC) | docs | ~15 min | 5 min | 20:54–20:59 |
| 2026-10-09 | Trace: HidHide calls, 5 s watch, hidden check + 9 tests (HHTRACE) | feature | ~15 min | 8 min | 20:53–21:01 |
| 2026-10-09 | Trace: end-to-end tests, 12 (E2E; found 3 real gaps) | test | ~18 min | 8 min | 20:54–21:02 |
| 2026-10-09 | Trace: Trace tab, menu, red mode + 8 tests (UI) | feature | ~18 min | 8 min | 20:54–21:02 |
| 2026-10-09 | Trace: lead fixes (watch start, import, ticks kept at restart) | fix | ~5 min | 8 min | 20:55–21:03 |
| 2026-10-10 | Trace: Clear Trace File, Max size, Axis lines, typed numbers, Options panel (CLR) | feature | ~10 min (+3 requests) | 11 min | 02:49–03:00 |
| 2026-10-10 | Trace options spec, 4 revisions (DOC2) | docs | ~6 min | 8 min | 02:49–02:57 |
| 2026-10-10 | Full run + lint (1 settings-history flake, passed alone) (lead) | test | ~6 min | 6 min | 03:00–03:06 |
| 2026-10-10 | Input Tester: contract + 7 agents briefed (lead) | plan | ~5 min | 3 min | 03:12–03:15 |
| 2026-10-10 | Input Tester core, model, entry (TCORE) + 2 fixes | feature | ~20 min | 9 min | 03:15–03:24 |
| 2026-10-10 | Input Tester window (TUI) | feature | ~20 min | 8 min | 03:15–03:23 |
| 2026-10-10 | Second exe build, installer, dev build ~1 min (PACK) | feature | ~20 min | 5 min | 03:15–03:20 |
| 2026-10-10 | expected.json, launch, result watch, Tools menu (LINK) | feature | ~20 min | 6 min | 03:15–03:21 |
| 2026-10-10 | HidHide page tester buttons, path checks (HHPAGE) | feature | ~20 min | 8 min | 03:15–03:23 |
| 2026-10-10 | Input Tester end-to-end tests, 10 (TE2E) | test | ~20 min | 6 min | 03:16–03:22 |
| 2026-10-10 | Input Tester spec 02 S99-S114, 01 S152, Help (TDOC) | docs | ~18 min | 6 min | 03:16–03:22 |
| 2026-10-10 | Reset Devices live check: one stick restarted, logs read (lead) | review | ~5 min | 2 min | 04:46–04:48 |
| 2026-10-10 | dill upgrade impact study (DILLUP) | review | ~15 min | 9 min | 04:22–04:31 |
| 2026-10-10 | Upstream R16 dill check (R16DILL) | review | ~12 min | 3 min | 04:41–04:44 |
| 2026-10-10 | Test-order leak fix (ORDER) | fix | ~15 min | 1 min | 04:37–04:38 |
| 2026-10-10 | dill2 Route A full run + lint (lead) | test | ~6 min | ~6 min | ended 06:35, 4,839 passed; start not logged |
| 2026-10-10 | Commit/push 4951df66 + tracker/progress (lead) | docs | — | 2 min | 06:45–06:47 |
| 2026-10-10 | R16 integration study IS1–IS5 (5 read-only agents) | review | ~15 min | 2–4 min each | 06:43–06:47 |
| 2026-10-10 | R16 integration study IS6 small items | review | ~8 min | 3 min | 06:47–06:50 |
| 2026-10-10 | R16 study report page (lead) | docs | — | ~5 min | 06:48–06:53, approx: not clocked |
| 2026-10-10 | Rebuild Input Tester with dill2 (lead) | build | — | <1 min | 07:03 |
| 2026-10-10 | dill2 hands-on log reads incl. layout-switch finding (lead) | review | — | ~9 min | 07:04–07:13 |
| 2026-10-10 | Batch "R16 + findings": KEYS (R1, R4, G-b) | fix | ~15 min | 2 min | 07:24–07:26 |
| 2026-10-10 | Batch: SMALL (R2, R3, R5, R11d) | fix | ~15 min | 2 min | 07:24–07:26 |
| 2026-10-10 | Batch: MERGE (R7 Maximum Deflection) | feature | ~15 min | 4 min | 07:25–07:29 |
| 2026-10-10 | Batch: MACROLOAD (R11a, R11c, R6 macro) | feature | ~20 min | 5 min | 07:25–07:30 |
| 2026-10-10 | Batch: DOCS (spec, decisions, glossary, Help, to-do) | docs | ~20 min | 4 min | 07:26–07:30 |
| 2026-10-10 | Batch: DEVLAYOUT (D2G1–D2G3, TX1) | fix | ~20 min | 5 min | 07:25–07:30 |
| 2026-10-10 | Batch: RESETWIN (live list, Xbox unticked) | feature | ~20 min | 6 min | 07:25–07:31 |
| 2026-10-10 | Batch: MOUSE (R9 rework, G-c) | refactor | ~30 min | 8 min | 07:25–07:33 |
| 2026-10-10 | Batch: DEFAULTS (R6, R8, R11b, G-a) | feature | ~20 min | 8 min | 07:25–07:33 |
| 2026-10-10 | Batch: 9 agents start to last report (wall clock) | batch | quoted 15–30 min | 10 min | 07:23–07:33; the rules of thumb said ~10 min |
| 2026-10-10 | Lead: hidhide.py follow-up + tests, lint + 3 type fixes | fix | — | ~5 min | 07:31–07:36 |
| 2026-10-10 | Batch: CARRY (carry-through tests, G-d and to-do 81 checks) | test | ~25 min (padded) | 10 min | 07:26–07:36; table said 3–8 min per agent |
| 2026-10-10 | Batch: DOCS follow-up (map counts, wording, gaps) | docs | 3–8 min (table) | 4 min | 07:34–07:38 |
| 2026-10-10 | Timing rule strengthened in CLAUDE.md + memory (lead) | docs | 1–2 min | 1 min | 07:40 |
| 2026-10-10 | Full run + lint, batch "R16 + findings" (lead) | test | 5–6 min (table) | 6 min | 07:38–07:44; 3 failures, all tests pinning old internals/defaults |
| 2026-10-10 | Fix 3 full-run failures (test fakes, explicit "released") (lead) | fix | — | 1 min | 07:44–07:45 |
| 2026-10-10 | Commit batch in 9 group commits (lead) | docs | ~2 min (table) | 2 min | 07:46–07:48 |
| 2026-10-10 | TTS81: release Text to Speech at exit (to-do 81) | fix | 3–8 min (table) | 1.5 min | 07:46–07:47 (91 s by the agent's run time) |
| 2026-10-10 | Final full run + lint (lead) | test | 5–6 min + lint (table) | 6 min | 07:48–07:54; all green, 4,262 passed; 2 new ruff long lines fixed after |
| 2026-10-10 | Help: HidHide off/on and Gremlin always sees devices (lead) | docs | 3–8 min (table) | 3 min | 08:04–08:07; full run deferred until Gremlin closes |
| 2026-10-10 | TWIN: twin pads by path, tester 'changed' on Refresh | fix | 3–8 min (table) | 7 min | 08:07–08:14 |
| 2026-10-10 | TESTBTN: tester buttons area fills height, scroll to pressed (S147 S148) | feature | 3–8 min (table) | 4 min | 08:14–08:18 |
| 2026-10-10 | DOCS2: map, decisions, to-do for TWIN + TESTBTN | docs | 3–8 min (table) | 2 min | 08:18–08:20 |
| 2026-10-10 | OOS1: out-of-step false alarm after Stop (rest counted as written) | fix | 3–8 min (table) | 2 min | 08:18–08:20 |
| 2026-10-10 | DOCS2: OOS1 map pass (01, 06) | docs | 3–8 min (table) | 1 min | 08:21–08:22 |
| 2026-10-10 | Full run + lint after testing fixes (lead) | test | 5–6 min + lint (table) | 8 min | 08:22–08:30; 12 F6 look tests timed out under load from the AEH agent, pass alone (12 in 6 s) |
| 2026-10-10 | Lint fix, 4 commits, push, tester rebuild (lead) | docs | ~2 min (table) | 2 min | 08:30–08:32 |
| 2026-10-10 | AEH: action matrix harness | feature | 3–8 min (table) | 8 min | 08:23–08:31 |
| 2026-10-10 | AE-MISC: matrix for 7 actions | test | ~10 min (table) | 6 min | 08:32–08:38; 0 defects |
| 2026-10-10 | AE-AXIS: matrix for 6 axis actions | test | ~10 min (table) | 7 min | 08:32–08:39; 0 defects, 2 screenshot notes |
| 2026-10-10 | AE-OUT: matrix for 6 output actions | test | ~10 min (table) | 8 min | 08:32–08:40; 0 defects, 3 observations |
| 2026-10-10 | AE-FLOW: matrix for 8 flow actions | test | ~10 min (table) | 9 min | 08:32–08:41; 1 defect (AE-reference-1) |
| 2026-10-10 | AE-REPORT: matrix report page | docs | 3–8 min (table) | 2 min | 08:46–08:48 |
| 2026-10-10 | Full run + lint with the action matrix (lead) | test | 6–7 min (table + matrix) | 7 min | 08:46–08:53; all green, 4,694 passed; slowest part 7 min |
| 2026-10-10 | O1PLAN: Logical Device self-target study | review | 5–10 min (table) | 3 min | 08:56–08:59 |
| 2026-10-10 | REFR1: Reference on keys, remove RootAction.qml | fix | 3–8 min (table) | 3 min | 08:56–08:59 |
| 2026-10-10 | LAYOUT: Dual Axis Deadzone + Send OSC editor widths | fix | 3–8 min (table) | 4 min | 08:56–09:00 |
| 2026-10-10 | AX1: name first Merge Axis / Dual Axis Deadzone instance (S120) | fix | 3–8 min (table) | 5 min | 08:56–09:01 |
| 2026-10-10 | DOCS3: map, decisions, to-do, Help for matrix fixes | docs | 3–8 min (table) | 3 min | 09:01–09:04 |
| 2026-10-10 | Full run + lint, matrix fixes (lead) | test | 6–7 min + lint (table) | 6 min | 09:05–09:11; all green, 4,708 passed |
| 2026-10-10 | SA1: Split Axis editor width | fix | 3–8 min (table) | 1 min | 09:12–09:13 (61 s) |
| 2026-10-10 | LD-DOCS: spec 06 S92-S94, decision, Help | docs | 3–8 min (table) | 2 min | 09:13–09:15 |
| 2026-10-10 | LD-PICK: Logical default + picker (S92 S93) | fix | 3–8 min (table) | 6 min | 09:12–09:18 |
| 2026-10-10 | LD-E2E: real-path loop tests (7 cases) | test | 3–8 min (table) | 6 min | 09:13–09:19; old code: 4 stack overflows + 2 runaways |
| 2026-10-10 | LD-GUARD: loop guard module (S94) | fix | 3–8 min (table) | 8 min | 09:12–09:20 |
| 2026-10-10 | LD-PICK follow-up: pass chain source to guard | fix | 3–8 min (table) | 2 min | 09:19–09:20 |
| 2026-10-10 | Lead: map row + to-do 89/90 for the loop guard | docs | ~2 min (no timing row for lead docs) | 2 min | 09:20–09:22 |
| 2026-10-10 | Full run + lint, loop guard batch (lead) | test | 6–7 min + lint (table) | 7 min | 09:20–09:27; 1 failure (test_logical_layout new action on OK), 5 pyright new |
| 2026-10-10 | LD-PICK fix: picker refresh reported as edit (regression) + 5 pyright | fix | 3–8 min (table) | 3 min | 09:28–09:30 |
| 2026-10-10 | Full run + lint after LD-PICK fix (lead) | test | 6–7 min + lint (table) | 7 min | 09:31–09:38; all green, 4,543 passed + 75 + 42 |
| 2026-10-10 | Lead: report/tracker audit (R16 study + matrix banners, DILL2-HANDS-ON, CI-B4CDACC7, progress to-do) | docs | ~5 min (no table row for lead audits) | 6 min | 09:40–09:46 |
| 2026-10-10 | HHSTAT: HidHide 'Last Status' line (HS1-HS4) | fix | 3–8 min (table) | 12 min | 09:46–09:58 (stopped 09:55 by mistake, resumed) |
| 2026-10-10 | Full run + lint, HidHide 'Last Status' (lead) | test | 6–7 min + lint (table) | 7 min | 09:58–10:05; all green |
| 2026-10-10 | NOTES: version 1.0.31 + release notes | docs | 3–8 min (table) | 1 min | 10:10–10:11 |
| 2026-10-10 | MAPCHECK: full pre-release map check | docs | 3–8 min (table) | 4 min | 10:10–10:14; 75 line counts, stale notes, README recount |
| 2026-10-10 | FLAKE: OSC Listen reached every model (real bug) + CI order leak | fix | 3–8 min (table) | 6 min | 10:10–10:16 |
| 2026-10-10 | Release full run + lint (lead) | test | 6–7 min + lint (table) | 7 min | 10:16–10:23; all green |
| 2026-10-10 | HELP-B: Help vs spec 04-06 audit | review | 5–10 min (table) | 2 min | 10:24–10:26 |
| 2026-10-10 | HELP-A: Help vs spec 01-03 audit | review | 5–10 min (table) | 2 min | 10:24–10:26 |
| 2026-10-10 | HELP-C: Help vs spec 07-10 audit | review | 5–10 min (table) | 1 min | 10:25–10:26 |
| 2026-10-10 | Release 1.0.31 build + publish (GitHub workflow) | release | rough guess 15–20 min (no row) | 4 min | 10:39–10:43; first timed release build |
| 2026-10-10 | OSCPANE: OSC page vs Logical Device page study + plan | review | 5–10 min (table) | ~4 min | 10:43–10:47 (widened twice while running) |
| 2026-10-10 | MOCKUP: OSC page pictures (4 today + 9 proposed) | review | rough guess 10–15 min (no row) | 11 min | 10:47–10:58; off-screen journey harness |
| 2026-10-10 | DS-FEED: OSC feedback rows on page + action state study | review | 5–10 min (table) | 1 min | 10:55–10:56 |
| 2026-10-10 | DS-MATCH: OSC address wildcards study | review | 5–10 min (table) | 2 min | 10:55–10:57 |
| 2026-10-10 | DS-MORE: OSC other ideas study (OX9 62/63/64/66/67/69) | review | 5–10 min (table) | 3 min | 10:55–10:58 |
| 2026-10-10 | CFG-STUDY: Configuration page in Logical Device style | review | 5–10 min (table) | 3 min | 10:58–11:01 |
| 2026-10-10 | CFG-SHOTS: Configuration page today pictures | review | rough guess 10–15 min (no row) | 3 min | 10:58–11:01 |
| 2026-10-10 | Lead: OSC batch 1 brief, contract, rules file, 7 agent briefs | planning | no timing data yet; rough guess 5 min | 3 min | 11:02–11:05 |
| 2026-10-10 | MONITOR: docked OSC Monitor panel (OP6-OP8, OP13) | feature | 3–8 min (table) | 3 min | 11:03–11:06 |
| 2026-10-10 | GAP-OP2: first action on empty input (guard test; closes via the new page) | fix | 3–8 min (table) | 4 min | 11:03–11:07 |
| 2026-10-10 | OSC-RT: OX1 live value, OX2 port holder, OX3 logging, OX5 send test | feature | 3–8 min (table) | 5 min | 11:03–11:08 |
| 2026-10-10 | E2E-TEST: OSC page end-to-end tests (xfail until wave 2) | feature | 3–8 min (table) | 6 min | 11:04–11:10 |
| 2026-10-10 | SPEC-MAP: OSC spec S129–S164 + Configuration spec batch C + map/glossary | docs | 3–8 min (table) | 7 min | 11:04–11:11 |
| 2026-10-10 | BASE-QML: ActionPane/ControlTree/ControlFindBar out of LogicalPage (pixel-identical) | refactor | 5–10 min (table) | 8 min | 11:03–11:11 |
| 2026-10-10 | BASE-PY: ControlLayoutModel out of LogicalLayoutModel (411 Logical tests pass) | refactor | 5–10 min (table) | 11 min | 11:03–11:14; incl. a 4.5 min test run |
| 2026-10-10 | CFG-STORE: module layout key, friendly-name rename, carry-through, shared Appearance setting | feature | 3–8 min (table) | 8 min | 11:07–11:15 |
| 2026-10-10 | OSC-SETUP: OX4 Companion setup check | feature | 3–8 min (table) | 4 min | 11:13–11:17 |
| 2026-10-10 | OSC-MODEL: OscLayoutModel + osc.json layout store, OX1/OX5/OX6 model | feature | 3–8 min (table) | 10 min | 11:13–11:23 |
| 2026-10-10 | OSC-PAGE: OscPage.qml, docked Monitor, multi-input Edit Settings, Main/Tools wiring, OscDevice.qml removed | feature | 3–8 min (table) | 15 min | 11:13–11:28; Main wiring + multi edit pushed it over |
| 2026-10-10 | OSC-SAVE: OSC page layout saved at File Save (D-09-OSC-FILE) | fix | 3–8 min (table) | 6 min | 11:24–11:30 |
| 2026-10-10 | MAP-APPLY: batch 1 map lines, recounts, gaps | docs | 3–8 min (table) | 6 min | 11:31–11:37 |
| 2026-10-10 | Lead: G-OSC36 Monitor height remembered (test first) + map | fix | 3–8 min (table: agent fix) | 4 min | 11:38–11:42 |
| 2026-10-10 | TEST-PIN: tests pinning old OSC page moved to the new page; found empty-list bug | test | 3–8 min + wait (table) | 30 min | 11:13–11:43; waited for page/model, slow real-app smokes |
| 2026-10-10 | Batch 1 full run + lint (lead) | test | 6–7 min + lint (table) | 7 min | 11:42–11:49; 1 fail (OSC names wiped on save), 3 lint |
| 2026-10-10 | Lead: OSC names kept on save (only page-changed names written) + test, lint fixes | fix | 3–8 min (table: agent fix) | 4 min | 11:49–11:53 |
| 2026-10-10 | Batch 1 full run + lint rerun (lead) | test | 6–7 min + lint (table) | 9 min | 11:53–12:02; 1 fail = child timeout under load (passes alone in 2.6 s) |
| 2026-10-10 | SPEED-STUDY: area A, top files, runner split multiplies 2 slow files | review | 5–10 min (table) | 3 min | 12:00–12:03 |
| 2026-10-10 | Lead: batch 1 commit + push (52a8c2f0) | commit | ~2 min (table: end-to-end batch row) | 1 min | 12:02–12:03 |
| 2026-10-10 | SPEED-APP: whole-app setup cost study | review | 5–10 min (table) | 2 min | 12:01–12:03 |
| 2026-10-10 | F1-RUNNER: setup counted once, split by test time, full runs only save times | fix | 3–8 min (table) | 2 min | 12:08–12:10 |
| 2026-10-10 | F2-PRINT: print export smokes run in parallel (36 s → 18.5 s) | fix | 3–8 min (table) | 2 min | 12:08–12:10 |
| 2026-10-10 | P-CORE: osc_pattern.py + OscRows pattern index (OX7) | feature | 3–8 min (table) | 3 min | 12:08–12:11 |
| 2026-10-10 | F3-BMAP: button map smokes in parallel + Take Theirs fix (42 s → 7.4 s) | fix | 3–8 min (table) | 3 min | 12:08–12:11 |
| 2026-10-10 | FB-REG: action_state registry, Smart Toggle/Tempo feedback_state (OX9F) | feature | 3–8 min (table) | 3 min | 12:09–12:12 |
| 2026-10-10 | Lead: shared address check in osc_device_model + stronger stage1 save asserts | fix | 3–8 min (table: agent fix) | 2 min | 12:11–12:13 |
| 2026-10-10 | SPEED-WAITS: waits/timeouts study (History writer 1 s idle per test) | review | 5–10 min (table) | 11 min | 12:01–12:12 |
| 2026-10-10 | P-RUN: OSC wildcards at run time (per-address state, osc_address, Bulk skip) | feature | 3–8 min (table) | 5 min | 12:09–12:14 |
| 2026-10-10 | FB-RT: feedback sources action_state/paused, input key, outgoing pattern refusal, page placement API | feature | 3–8 min (table) | 5 min | 12:09–12:14 |
| 2026-10-10 | W3-TESTER: tester mtime sleeps -> os.utime (26.5 -> 24.6 s) | fix | 3–8 min (table) | 2 min | 12:13–12:15 |
| 2026-10-10 | W4-TRACE: trace e2e condition waits (28.8 -> 28.2 s) | fix | 3–8 min (table) | 3 min | 12:13–12:16 |
| 2026-10-10 | Lead: RP1 Running/Paused on = Running (test first) + guard test real path | fix | 3–8 min (table: agent fix) | 2 min | 12:14–12:16 |
| 2026-10-10 | W1-CONFTEST: stop History writer at teardown (matrix outputs 65 -> 34 s, LS store 21 -> 2.2 s) | fix | 3–8 min (table) | 6 min | 12:13–12:19 |
| 2026-10-10 | OSC-W2-TEST: batch 2 e2e (4) + carry (11) tests | test | 3–8 min + wait (table) | 8 min | 12:14–12:22 |
| 2026-10-10 | W2-MATRIX: settle until outputs quiet (172 matrix tests 52.6 -> 34.0 s) | refactor | 5–10 min (table) | 10 min | 12:13–12:23; incl. an unannounced 4 min run |
| 2026-10-10 | OSC-W2-MODEL: feedback rows/editor/Undo + pattern subtitle/filter/hint, bulkSkipped | feature | 3–8 min (table) | 9 min | 12:14–12:23 |
| 2026-10-10 | Lead: base hook _rows_at_end replaces endResetModel override | refactor | 5–10 min (table) | 1 min | 12:23–12:24 |
| 2026-10-10 | FB-REMAP: pack feedback rows follow remapped action ids | fix | 3–8 min (table) | 3 min | 12:23–12:26 |
| 2026-10-10 | OSC-W2-QML: feedback rows/editor, Companion feedback menu, pattern error/hint, Feedback tab read-only, Setup tab opening | feature | 3–8 min (table) | 17 min | 12:14–12:31; also shared ControlTree/ActionPane hooks + tests |
| 2026-10-10 | MAP2: batch 2 map lines, decisions as wording, glossary | docs | 3–8 min (table) | 5 min | 12:27–12:32 |
| 2026-10-10 | Batch 2 full run + lint (lead), after speed fixes | test | 6–7 min + lint (table) | 5.5 min | 12:33–12:39; run 5:18 (was 7–9 min); 1 fail = stale Help labels |
| 2026-10-10 | Lead: Key color spelling, Help labels for removed Feedback tab editing, test line wraps | fix | 3–8 min (table: agent fix) | 1 min | 12:39–12:40 |
| 2026-10-10 | Lead: batch 2 commit + push (36bbcdb7) + tracker | commit | ~2 min (table: end-to-end batch row) | 2 min | 12:40–12:42 |
| 2026-10-10 | B3-TOSC: TouchOSC .tosc parser | feature | 3–8 min (table) | 2 min | 12:42–12:44 |
| 2026-10-10 | B3-COND: OSC inputs in conditions/scripts (OscState by uid, picker) | feature | 3–8 min (table) | 4 min | 12:42–12:46 |
| 2026-10-10 | B3-SCRIPT: OscInputVariable, osc.send to named targets, editor choice | feature | 3–8 min (table) | 5 min | 12:42–12:47 |
| 2026-10-10 | Lead: OscPlugin registered at Run + guard test narrowed to the feedback direction | fix | 3–8 min (table: agent fix) | 1 min | 12:47–12:48 |
| 2026-10-10 | RT3: allow-list, invert/deadzone, encoder accel, condition values, recorder hook | feature | 3–8 min (table) | 6 min | 12:42–12:48 |
| 2026-10-10 | Lead: Response Curve uses shared axis_shaping.deadzone; rows key list | fix | 3–8 min (table: agent fix) | 1 min | 12:48–12:49 |
| 2026-10-10 | B3-MACRO: OSC macro step + Record captures OSC | feature | 3–8 min (table) | 7 min | 12:42–12:49 |
| 2026-10-10 | B3-MODEL: Invert/deadzone/accel model, TouchOSC preview/import, allow-list + Allow this sender | feature | 3–8 min (table) | 6 min | 12:43–12:49 |
| 2026-10-10 | TOSC-RESEARCH: .tosc format checked against Hexler docs + tosclib | review | 5–10 min (table) | 3 min | 12:46–12:49 |
| 2026-10-10 | Lead: TS2 sample download (2,487 bytes, MIT) + TC1-TC4 brief | other | no timing data yet; rough guess 2 min | 1 min | 12:50–12:51 |
| 2026-10-10 | OSC-PLAY: OscRuntime.play for macro playback (synthetic, no re-shape, not recorded) | fix | 3–8 min (table) | 2 min | 12:50–12:52 |
| 2026-10-10 | B3-TEST: batch 3 e2e (7) + carry (11) | test | 3–8 min + wait (table) | 10 min | 12:43–12:53 |
| 2026-10-10 | TOSC-FIX: TouchOSC parser per Hexler docs (grid container, index, radar, pager, encoder axis) + real sample test | fix | 3–8 min (table) | 3 min | 12:50–12:53 |
| 2026-10-10 | Lead: deadzone error built only when refused (spurious ERROR log) + test | fix | 3–8 min (table: agent fix) | 1 min | 12:53–12:54 |
| 2026-10-10 | B3-QML: Invert box, Shaping/Acceleration, TouchOSC preview, Allowed senders, Monitor menu | feature | 3–8 min (table) | 11 min | 12:43–12:54 |
| 2026-10-10 | Lead: readImportText slot for Import's Choose File (.txt) + test | fix | 3–8 min (table: agent fix) | 1 min | 12:54–12:55 |
| 2026-10-10 | MAP3: batch 3 map, decisions as wording, glossary | docs | 3–8 min (table) | 4 min | 12:53–12:57 |
| 2026-10-10 | Batch 3 full run + lint (lead) | test | 6–7 min + lint (table) | 4.7 min | 12:58–13:03; run 4:41, parts balanced ~255 s; 7 fails = temp-folder race in one test's inner pytest (passes alone); 2 pyright fixed |
| 2026-10-10 | Lead: batch 3 pyright fix + commit + push (6a55f094) | commit | ~2 min (table: end-to-end batch row) | 1 min | 13:03–13:04 |
| 2026-10-10 | CFG-SAVE: Configuration layout held until File Save, Discard slot | fix | 3–8 min (table) | 2 min | 13:05–13:07 |
| 2026-10-10 | CFG-MODEL: HardwareLayoutModel (hardware_layout.py), BindingCatalogModel + catalog code removed (RB16) | refactor | 5–10 min (table) | 8 min | 13:05–13:13 |
| 2026-10-10 | Lead: 05 S36 Undo waits while the Configuration pane is open (base hook _undo_waits) + test | fix | 3–8 min (table: agent fix) | 2 min | 13:14–13:16 |
| 2026-10-10 | CFG-KEYS: KeyboardLayoutModel + KeyboardPage.qml, KeyboardPaneModel removed | feature | 3–8 min (table) | 12 min | 13:05–13:17 |
| 2026-10-10 | CFG-APPEAR: ListAppearancePanel (shared setting), live decoration + showKey + parentClicked in ControlTree | feature | 3–8 min (table) | 13 min | 13:05–13:18 |
| 2026-10-10 | Lead: removed unused WindowPlacement.logicalValue/setLogicalValue + test adjust | fix | 3–8 min (table: agent fix) | 1 min | 13:18–13:19 |
| 2026-10-10 | CFG-MODEL: QML crash fix (Property notify on a base-class signal) + child-process QML test | fix | 3–8 min (table) | 2 min | 13:18–13:20 |
| 2026-10-10 | Lead: KeyboardLayoutModel own notify signal (same QML crash pattern) + QML build test | fix | 3–8 min (table: agent fix) | 1 min | 13:20–13:21 |
| 2026-10-10 | CFG-E2E: Configuration + Keyboard e2e (10) + carry (9) | test | 3–8 min + wait (table) | 14 min | 13:07–13:21 |
| 2026-10-10 | CFG-PAGE: ConfigurationPage.qml, BindingCatalog.qml deleted | feature | 3–8 min (table) | 15 min | 13:06–13:21 |
| 2026-10-10 | AS1-REMOVE: row icon setting, icon strip, KeyboardManagerModel, KeyboardInputList/InputButton removed | fix | 3–8 min (table) | 3 min | 13:19–13:22 |
| 2026-10-10 | CFG-SHELL: Main loads ConfigurationPage/KeyboardPage, leave chain, header cleanup | feature | 3–8 min (table) | 19 min | 13:06–13:25; chased an intermittent crash |
| 2026-10-10 | Lead: AP2/AP3 routing (per-page Appearance, row alignment/width/group gap back) | planning | no timing data yet; rough guess 2 min | 1 min | 13:26–13:27 |
| 2026-10-10 | KB-BAR: Keyboard Appearance on the page bar + pageKey | fix | 3–8 min (table) | 1 min | 13:26–13:27 |
| 2026-10-10 | MAP-C: batch C map, CS1/AP2/AP3/OP5 reversal, glossary, decisions | docs | 3–8 min (table) | 7 min | 13:23–13:30 |
| 2026-10-10 | CFG-TESTS: ~29 pinned test files moved to the new pages (320 pass) | test | 3–8 min + wait (table) | 25 min | 13:06–13:31 |
| 2026-10-10 | CFG-TESTS2: journeys/matrix/smoke harnesses on the new pages | test | 3–8 min (table) | 10 min | 13:23–13:33 |
| 2026-10-10 | Lead: 4 journey files to open_input + journeys run (42 pass) | test | 3–8 min (table: agent fix) | 2 min | 13:33–13:35 |
| 2026-10-10 | AP-PANEL: per-page Appearance, Rows options, Logical/OSC page bars, OSC panel | feature | rough guess 10–15 min (no row) | 8 min | 13:27–13:35 |
| 2026-10-10 | Lead: Keyboard row options wired + store test to per-page | fix | 3–8 min (table: agent fix) | 1 min | 13:35–13:36 |
| 2026-10-10 | MAP-C touch-up: AP-PANEL names, counts, glossary | docs | 3–8 min (table) | 1 min | 13:35–13:36 |
| 2026-10-10 | Batch C full run + lint (lead) | test | 6–7 min + lint (table) | 5.5 min | 13:36–13:42; run 5:15; 11 fails = removed action images (AS1) + 2 stale Help labels |
| 2026-10-10 | Lead: removed action image provider/generator + its look tests (AS1), Help labels, lint baseline | fix | 3–8 min (table: agent fix) | 2 min | 13:42–13:44 |
| 2026-10-10 | Lead: PS1 impact analysis (compare page functions/menus across 4 pages) | review | 5–10 min (table: read-only study) | 2 min | 13:45–13:47 |
| 2026-10-10 | Lead: to-do 91 (shared page base plan + notes) + tracker | docs | no timing data yet; rough guess 5 min | 4 min | 13:48–13:52 |
| 2026-10-10 | DRIFT-FIX: OSC Appearance menu row, Keyboard requestCloseDisplay, alike test | fix | 3–8 min (table) | 1 min | 13:51–13:52 |
| 2026-10-10 | Lead: CI 6a55f094 failure (test_input_tester_link write/mtime order) found + fixed | fix | 3–8 min (table: agent fix) | 2 min | 13:52–13:54 |
| 2026-10-10 | Lead: Method B brief, contract, to-do 91 rewrite, wave 1 briefs | planning | no timing data yet; rough guess 5 min | 3 min | 14:04–14:07 |
| 2026-10-10 | SB-APPEAR: PageAppearance.qml shared part + test | refactor | 5–10 min (table) | 2 min | 14:06–14:08 |
| 2026-10-10 | SB-PANE: leave functions into ActionPane + Main _paneOf | refactor | 5–10 min (table) | 4 min | 14:05–14:09 |
| 2026-10-10 | SB-SHOTS part 1: 24 before screenshots, two runs identical | test | rough guess 8–12 min (no row) | 6 min | 14:05–14:11 |
| 2026-10-10 | Lead: wave 2 page brief + 6 briefs | planning | no timing data yet; rough guess 3 min | 2 min | 14:11–14:13 |
| 2026-10-10 | SB-MENU: control_menu.js standard menu + menus-unchanged proof | refactor | 5–10 min (table) | 6 min | 14:06–14:12 |
| 2026-10-10 | SB-LOG: Logical page on shared parts (783 -> 651 lines) | refactor | 10–17 min (today's page rows) | 2 min | 14:11–14:13 |
| 2026-10-10 | SB-CFG: Configuration page on shared parts + Clear Name (752 -> 644 lines) | refactor | 10–17 min (today's page rows) | 2 min | 14:11–14:13 |
| 2026-10-10 | SB-OSC: OSC page on shared parts (1176 -> 1069 lines) | refactor | 10–17 min (today's page rows) | 2 min | 14:12–14:14 |
| 2026-10-10 | SB-TESTS: tests retargeted to shared parts + PB2 check | test | 3–8 min (table) | 3 min | 14:12–14:15 |
| 2026-10-10 | SB-KEY: Keyboard page on shared parts (581 -> 472 lines) | refactor | 10–17 min (today's page rows) | 4 min | 14:11–14:15 |
| 2026-10-10 | SB-SHOTS part 2: after vs before, 23/24 identical, 1 = PB2 Clear Name | test | rough guess 3–5 min (no row) | 3 min | 14:15–14:17 |
| 2026-10-10 | SB-MAP: map, S132 (PB2), D-05-PAGE-PARTS, glossary | docs | 3–8 min (table) | 5 min | 14:12–14:17 |
| 2026-10-10 | Shared parts full run + lint (lead) | test | 6–7 min + lint (table) | 5.5 min | 14:17–14:23; run 5:14; 1 fail = key title 'a' vs 'A' (order-dependent) |
| 2026-10-10 | KEYNAME: key names depended on lookup order ('a' vs 'A') — fixed in keyboard.py + test | fix | 3–8 min (table) | 2 min | 14:23–14:25 |
| 2026-10-10 | To-do 91 Method B end to end (approve 14:05 -> push 14:25) | batch | 35–50 min + CI (quoted) | 20 min | 14:05–14:25; CI pending |
| 2026-10-10 | Lead: audit brief + 10 audit agent briefs | planning | no timing data yet; rough guess 5 min | 3 min | 14:29–14:32 |
| 2026-10-10 | AUD-MOD: audit 03 + 10 (gap #28 confirmed + 3 related save issues, stale map) | review | 10–15 min (brief) | 3 min | 14:30–14:33 |
| 2026-10-10 | AUD-BMH: audit 07 + 08 (Q15 already fixed; maps stale; EVO R fallback) | review | 10–15 min (brief) | 3 min | 14:30–14:33 |
| 2026-10-10 | AUD-ACT: audit 05 (2 spec gaps, stale map, dead code, listener risk) | review | 10–15 min (brief) | ~4 min | 14:30–14:34 (agent clock unreliable) |
| 2026-10-10 | AUD-RUN: audit 06 (map stale, arrow text, to-do 89/90, output guard, registry cache) | review | 10–15 min (brief) | 4 min | 14:30–14:34 |
| 2026-10-10 | AUD-DEV: audit 02 (14 findings; a test child process loads the real dill) | review | 10–15 min (brief) | ~5 min | 14:30–14:35 |
| 2026-10-10 | AUD-SHELL: audit 01 + 04 (maps stale, ColorInformation chain dead, dead slots; typo fix) | review | 10–15 min (brief) | ~5 min | 14:30–14:35 |
| 2026-10-10 | AUD-FILES: file writes + carry-through (Module Setup names overwrite, gap #28, unsafe fallback write, carry gaps) | review | 10–15 min (brief) | 4 min | 14:30–14:34 |
| 2026-10-10 | AUD-OSC: audit 09 (Listening box stale fields, tosc recursion crash, server threads, legacy compat code, ColorInformation chain) | review | 10–15 min (brief) | 4 min | 14:30–14:34 |
| 2026-10-10 | AUD-THREADS: threads sweep (exit crash = Qt clean-up at os._exit; 2 unbounded waits; History order race; tester flag race) | review | 10–15 min (brief) | ~7 min | 14:30–14:37 (agent clock unreliable) |
| 2026-10-10 | AUD-LINT: 883 type findings triaged (9 real), dead code/signals sweep | review | 10–15 min (brief) | 10 min | 14:30–14:40 |
| 2026-10-10 | Lead: DL1 dill test-safety check (verified real DLL loads at import in every test process) + brief | review | no timing data yet; rough guess 5 min | 5 min | 14:40–14:45 |
| 2026-10-10 | SHAKE-JOURNEYS: 40 random journeys (3,600 steps) + editors at 3 scales x 2 themes | test | rough guess 15–25 min (no row) | 13 min | 14:34–14:47 |
| 2026-10-10 | SHAKE-DAMAGE: 331 damaged-file cases (1 data loss in logical_device.json, History/Library/pack crashes) | test | rough guess 15–20 min (no row) | 14 min | 14:33–14:47 |
| 2026-10-10 | DILL-SAFE: dill loads on first use + child-process guard + 4 tests | fix | 3–8 min (table) | 6 min | 14:45–14:51 |
| 2026-10-10 | Lead: main test process refuses the real dill too (test/conftest.py) | fix | 3–8 min (table: agent fix) | 1 min | 14:51–14:52 |
| 2026-10-10 | SHAKE-STRESS: 6 stress scenarios (clean core; release-entry leak, Options/viewer leaks, harness qWait starves threads) | test | rough guess 15–25 min (no row) | 25 min | 14:34–14:59 |
| 2026-10-10 | Full run with dill guard (DL1 c) | test | 6–7 min + lint (table) | 5 min | 14:59–15:05; run 4:51; 0 tests reach the real dill; 1 order-dependent History test |
| 2026-10-10 | F1-SAVE: profile saved even if a side file fails; SaveIncomplete names the file | fix | 3–8 min (table) | 3 min | 15:16–15:19 |
| 2026-10-10 | F1-LD: AD1 bad Logical Device rows skipped with warning, kept at Save | fix | 3–8 min (table) | 3 min | 15:16–15:19 |
| 2026-10-10 | F1-KEY: AD4 keys with no actions kept in the Keyboard module layout | fix | 3–8 min (table) | 5 min | 15:16–15:21 |
| 2026-10-10 | F1-WRITE: no in-place fallback writes; templates + photo cache safe | fix | 3–8 min (table) | 3 min | 15:17–15:20 |
| 2026-10-10 | F1-PARSE: tester expected types + deep nesting in 9 readers | fix | 3–8 min (table) | 3 min | 15:17–15:20 |
| 2026-10-10 | F1-SETUP: AD3 Module Setup saves only changed names | fix | 3–8 min (table) | 4 min | 15:16–15:20 |
| 2026-10-10 | Lead: RecursionError gaps (module_file, hardware_profile), test_audit_saving update, routing | fix | 3–8 min (table: agent fix) | 3 min | 15:19–15:22 |
| 2026-10-10 | F1-SPEC: AD1-AD10 into spec, decisions, glossary | docs | 3–8 min (table) | 4 min | 15:17–15:21 |
| 2026-10-10 | F2-SAVEMSG: save message names the failed file; core plugin import failure stops start-up | fix | 3–8 min (table) | 2 min | 15:20–15:22 |
| 2026-10-10 | F1-STORE: held layout yields to a newer file (AD2), unclaimed names, device delete, LD/OSC reload warnings | fix | 5–10 min (table) | 6 min | 15:16–15:22 |
| 2026-10-10 | F2-OSCINFO: Listening box shows Targets + output switch | fix | 3–8 min (table) | 1 min | 15:21–15:22 |
| 2026-10-10 | F2-LDPICK: AD10 picker shows loaded self-target; loop notice arrow | fix | 3–8 min (table) | 1 min | 15:22–15:23 |
| 2026-10-10 | F2-SMALL: five small crash fixes (pause, spline NaN, macro, Auto Mapper, condition dead slot) | fix | 3–8 min (table) | ~10 min (start stamp late) | ~15:13–15:23 |
| 2026-10-10 | F1-LIBPACK: damaged library.json rows and Device Packs refused safely; 64 MB cap; names cut to 80 | fix | 5–10 min (table) | 7 min | 15:17–15:24 |
| 2026-10-10 | F3-OSCSRV: one OSC receive thread, stop returns at once | refactor | 5–10 min (table) | 2 min | 15:22–15:24 |
| 2026-10-10 | F2-TESTER: to-do 84 study (stopped: needs spec decision) | study | 3–8 min (table) | <1 min | 15:25–15:25 |
| 2026-10-10 | F3-TESTERRACE: tester link hook flag under a lock | fix | 3–8 min (table) | <1 min | 15:25–15:25 |
| 2026-10-10 | F4-AD9: Type box loses No actions; Help line; lead removed dead unmapped branches | fix | 3–8 min (table) | 1 min (+1 lead) | 15:25–15:27 |
| 2026-10-10 | F1-LDHOOK: LD/OSC load warnings shown at start; rollback and OSC keep unreadable rows | fix | 5–10 min (table) | ~7 min (end stamp doubtful) | 15:20–15:27 |
| 2026-10-10 | F2-VJOY: hat error attr, no output writes outside a Run, claim checked before open; 6 test files + baseline | fix | 5–10 min (table) | 7 min | 15:21–15:28 |
| 2026-10-10 | Lead: LD file reports any damage (not only deep nesting); OSC Undo keeps unreadable rows; LD tests 208 pass | lead fix | no timing data yet | ~3 min | 15:25–15:28 |
| 2026-10-10 | F1-HIST: History lines checked, kept copies whole, pictures put back on failure, AD6 ask, RecursionError | fix | 5–10 min (table) | 12 min | 15:17–15:29 |
| 2026-10-10 | Lead: DialogHistory asks before writing outside (AD6, glossary wording "Write Here"); History tests 67 pass | lead fix | no timing data yet | 1 min | 15:29–15:30 |
| 2026-10-10 | F-OSCUNDO: test that OSC Undo keeps unreadable rows | test | 3–8 min (table) | 1 min | 15:29–15:30 |
| 2026-10-10 | F2-REGISTRY: a module file that failed to open is read again next call | fix | 3–8 min (table) | 1 min | 15:29–15:30 |
| 2026-10-10 | F3-WAITS: bounded listener/macro waits, restart retires old thread, dead sleep, gremlin.clock | fix | 3–8 min (table) | 5 min | 15:25–15:30 |
| 2026-10-10 | F4-AD8: Button Map editor load failure shows plain error, EVO layout removed; importPack never raises | fix | 3–8 min (table) | 5 min (+2:41 golden run) | 15:25–15:30 |
| 2026-10-10 | F3-HISTORDER: History writer keeps queue order at quit | fix | 3–8 min (table) | 2 min | 15:30–15:32 |
| 2026-10-10 | F3-CLOCK: five files use gremlin.clock for timing | fix | 3–8 min (table) | 2 min | 15:31–15:33 |
| 2026-10-10 | F-HISTASK: off-screen test of the History Write Here question | test | 3–8 min (table) | 2 min | 15:30–15:32 |
| 2026-10-10 | F4-FLAKY: three flaky tests fixed (child guards path, rules collect root, log-level History entry) | test fix | 5–10 min (table) | 7 min | 15:26–15:33 |
| 2026-10-10 | F3-HIDHIDE: ctypes classes made once (STRESS-05); STRESS-06 study (stopped: visible change) | fix | 3–8 min (table) | 3 min | 15:31–15:34 |
| 2026-10-10 | F3-EXIT: AD5 quit releases Qt before exit (release_qt, 3 s guard) | refactor | 5–10 min (table) | 4 min | 15:31–15:35 |
| 2026-10-10 | Lead: second-copy check reads the lock owner (getLockInfo), test first | lead fix | no timing data yet | ~2 min | 15:33–15:35 |
| 2026-10-10 | F4-TESTGAPS: S34 guard, Keyboard/OSC carry (16), random list-page journey (5 seeds); found Keyboard names bug | test | 5–10 min (table) | 9 min | 15:26–15:35 |
| 2026-10-10 | F2-KEYNAMES: Keyboard key names travel in Device Pack / Library Restore / Import | fix | 3–8 min (table) | 1 min | 15:36–15:37 |
| 2026-10-10 | F2-PAGEROWS: list pages change rows in place (no reset, SJ-02); stale-rows cause found; lead applied Main/ConfigurationPage fix | fix | 3–8 min (table) | 4 min (+2 lead) | 15:33–15:39 |
| 2026-10-10 | F4-DEAD: 63 dead definitions + 11 dead signals removed; deferred list | refactor | 5–10 min (table) | 5 min | 15:33–15:38 |
| 2026-10-10 | F3-LEAKS: release entries spent at release (S38 bug), Options models owned, curve objects reused; Input Viewer is PySide | refactor | 5–10 min (table) | 13 min | 15:25–15:38 |
| 2026-10-10 | F4-PYPATH: child processes keep test guards (6 tests), child_env helper, guard test, settings snapshot fixture | test fix | 3–8 min (table) | 6 min | 15:34–15:40 |
| 2026-10-10 | F-SMOKEEXIT: 58 smoke scripts release Qt before exit (smoke_exit helper) | test fix | 3–8 min (table) | 5 min (+1:50 run) | 15:36–15:41 |
| 2026-10-10 | F4-DILLPROBE: dill loading test proves the path with a recorder, never loads dill.dll | test fix | 3–8 min (table) | 2 min | 15:41–15:43 |
| 2026-10-10 | T1-MATCH: tester matches Xbox pads by xinput slot | fix | 3–8 min (table) | 3 min | 15:40–15:43 |
| 2026-10-10 | T1-SLOT: ViGEm user index -> output.xbox_slot -> expected.json xinput | fix | 3–8 min (table) | 3 min | 15:40–15:43 |
| 2026-10-10 | F4-MAP: all 10 map pages refreshed + 7 approved decisions written into §8/§12 | map catch-up | 5–7 min (table: map catch-up) | 16 min | 15:27–15:43 |
| 2026-10-10 | F4-AD7: OSC legacy converters removed (osc.py, osc_device_file, profile, backend, pack, options) + tests | refactor | 3–8 min (table: agent fix) | 15 min (spread to more callers) | 15:32–15:47 |
| 2026-10-10 | F4-HARNESS: harness pump wait, deferred deletes, no real HID list, F6 theme, smoke_exit; journeys 93 s -> 55 s | test fix | 5–10 min (table) | 10 min | 15:38–15:48 |
| 2026-10-10 | F3-HIDRESET: Hardware Hide one device walk per open; SHELLEXECUTEINFOW once | fix | 3–8 min (table) | 14 min (~10 queued behind other test runs) | 15:34–15:48 |
| 2026-10-10 | Lead: 09 S48 + 04 S25/§2/§3 rewritten for AD7 | map | no timing data yet | 3 min | 15:45–15:48 |
| 2026-10-10 | F2-EDITORS: editor cut-offs at 100/150/200 % (picker, Condition, Xbox, Mouse, TTS, Tempo, Double Tap, Smart Toggle, placeholders, pane width) | fix | 15 min (brief check-in) | 28 min | 15:21–15:49 |
| 2026-10-10 | L1-CHAIN: loop guard follows each event's chain (Event.ld_chain, macro chain), 0.1 s window gone | fix | rough guess 15–25 min (no data) | 9 min | 15:40–15:49 |
| 2026-10-10 | F4-COLORINFO: dead ColorInformation chain + destFilter removed | fix | 3–8 min (table) | 3 min | 15:46–15:49 |
| 2026-10-10 | F4-MAP2: map lines for T1, AD7, harness, HidHide, editors, L1, colour chain; to-dos 84/89/90/91 done | map catch-up | 5–7 min (table) | 4 min | 15:49–15:53 |
| 2026-10-10 | Full run (random order, seed 110884): 4 failed (stale test pins: open mkstemp file, colour count, CI times, temp name) | test run | ~5 min (table) | 5:21 | 15:49–15:54 |
| 2026-10-10 | Lead: fix 4 test pins, refresh test_times.json, lint 0 new, commit e414d0b3 + push | lead commit | no timing data yet | 2 min | 15:54–15:56 |
| 2026-10-10 | O1-NAMEKEYS: old OSC name-key converter + find_target removed; claim_friendly reads osc:<uid> only | fix | 3–8 min (table) | 3 min | 15:56–15:59 |
| 2026-10-10 | A1-NARROW: Appearance panel closes when list + pane + panel don't fit | fix | 3–8 min (table) | 4 min | 15:56–16:00 |
| 2026-10-10 | HELP-Q: facts for 8 Help decisions (read-only study) | study | rough guess 3–5 min (no data) | 2 min | 16:00–16:02 |
| 2026-10-10 | LD14: version 14 Logical Device converters removed (logical_device_file, profile, backend, pack, library) | fix | 3–8 min (table) | 7 min | 15:58–16:05 |
| 2026-10-10 | D6-COLOR: key color internal ids colour -> color | fix | 3–8 min (table) | 1 min | 16:06–16:07 |
| 2026-10-10 | D8-RECOVERY: Button Map Autosave -> Recovery copies (options, window, option titles) | fix | 3–8 min (table) | 1 min | 16:06–16:07 |
| 2026-10-10 | D7-BUSY: Hardware Hide shows 'in use by another program' on err 5 | fix | 3–8 min (table) | 2 min | 16:06–16:08 |
| 2026-10-10 | H-HOME: getting_started.js install/diagnostics/start warnings/second copy | help | rough guess 10–15 min (no data) | 3 min | 16:06–16:09 |
| 2026-10-10 | H-TOOLS: tools/device_library/button_map Help (D7, D8, AD6, AD8, Auto Mapper, pack limits) | help | rough guess 10–15 min (no data) | 3 min | 16:06–16:09 |
| 2026-10-10 | H-PROFILE: logical_device.js + options_profile.js Help (AD1, L1, AD10, LD14, save names file, script OSC) | help | rough guess 10–15 min (no data) | 4 min | 16:06–16:10 |
| 2026-10-10 | SPEC: 12 decisions written into map + glossary; O1/A1/LD14/D6/D7/D8 map lines | map catch-up | 5–7 min (table) | 5 min | 16:06–16:11 |
| 2026-10-10 | H-TOOLS second pass: tester details, viewers, reset rows, out-of-step, internal input | help | 3–5 min (brief) | 2 min | 16:09–16:11 |
| 2026-10-10 | H-CFG: configuration_actions.js Help (pages, menus, Find, held layouts, K1, A1, A2, AD9, AD10, S4, HB1) | help | rough guess 10–15 min (no data) | 6 min | 16:06–16:12 |
| 2026-10-10 | F-FINDCLEAR: Find Clear studied (FC1 question), Xbox Output View Help sentence fixed | study+help | 3–8 min (table) | 1 min | 16:12–16:13 |
| 2026-10-10 | F-PANELEAVE: opening another input asks before dropping unsaved editor changes (S26 gap) | fix | 3–8 min (table) | 3 min | 16:12–16:15 |
| 2026-10-10 | H-OSC: osc.js Help rewritten (feedback rows, Companion, HC1-HC11, patterns, allow-list, scripts, TouchOSC, shaping, encoder) | help | rough guess 10–15 min (no data) | 10 min | 16:06–16:16 |
| 2026-10-10 | Full run 2 (random): action_interaction 83 failed (LD14 fixtures), 2 more (LD fixture, Help Cancel) | test run | ~5 min (table) | 5:07 | 16:16–16:21 |
| 2026-10-10 | H-CFG follow-up: Help says opening another input asks Save/Discard/Cancel | help | 3–5 min (brief) | 1 min | 16:22–16:23 |
| 2026-10-10 | LD14 follow-up: 20 fixture profiles to v16 + Logical Device set up through its API | test fix | 3–8 min (table) | 3 min | 16:22–16:25 |
| 2026-10-10 | F-LISTENPORT: Listen failure names the port holder in one message (S18 gap) | fix | 3–8 min (table) | 2 min | 16:23–16:25 |
| 2026-10-10 | MAP3: map lines for pane-leave, Listen port holder, fixtures | map catch-up | 5–7 min (table) | 1 min | 16:26–16:27 |
| 2026-10-10 | Full run 3 (seed 179731): 3 order-dependent failures (pass alone); action_interaction 75 pass | test run | ~5 min (table) | 5:26 | 16:26–16:31 |
| 2026-10-10 | FLK-OSCLAYOUT: test_osc_scripts left OscRuntime._running True; monkeypatch | test fix | 3–8 min (table) | 2 min | 16:31–16:33 |
| 2026-10-10 | FLK-SWAP: leaked Home card lists reloaded during swap test; conftest quiets them | test fix | 3–8 min (table) | 9 min | 16:32–16:41 |
| 2026-10-10 | FLK-OSCBACKEND: test_fix_X3 left a held keyboard layout; try/finally discard | test fix | 3–8 min (table) | 9 min | 16:32–16:41 |
| 2026-10-10 | Lead: module_model lambda -> bound method (card lists freed), conftest drops held layouts after each test; tests first | lead fix | no timing data yet | ~2 min | 16:40–16:42 |
| 2026-10-10 | Full run 4 (seed 179731, new split): 1 order-dependent (logger mock); fixed | test run | ~5 min (table) | 5:12 | 16:42–16:48 |
| 2026-10-10 | Lead: ST1 and FC1 decisions recorded; 02 S108 updated for Allow mode | spec | no timing data yet | 2 min | 16:50–16:52 |
| 2026-10-10 | FC1-CLEAR: Find Clear resets Type and Output (cleared signal) + Help + spec | fix | 3–8 min (table) | 2 min | 16:51–16:53 |
| 2026-10-10 | Full run 5 (random): all passed (5249 unit + 75 + 47) | test run | ~5 min (table) | 4:58 | 16:53–16:58 |
| 2026-10-10 | Lead: lint, commit 3702e630, push, tracker | lead commit | no timing data yet | 1 min | 16:58–16:59 |
| 2026-10-10 | Q15-TEST: History Configuration-row profile filter test (Q16) | test | 3–8 min (table) | 2 min | 17:10–17:12 |
| 2026-10-10 | T86-APOS: 'can t' not reproduced (real dialog draws can't) | study | 3–8 min (table) | 3 min | 17:10–17:13 |
| 2026-10-10 | ORPHAN: runner ends each part's process tree (Job Object), test_final_01 children via proc_tree | test fix | 3–8 min (table) | 3 min | 17:10–17:13 |
| 2026-10-10 | H2-OSC: osc.js gap fill (Find, Appearance, card, History, Bulk, encoder) + 11 Show me links | help | rough guess 15–25 min (no data) | 3 min (agent's clock; looks short) | 17:12–17:15 |
| 2026-10-10 | H2-TOOLS: tools/device_library/button_map gap fill + 15 Show me links | help | rough guess 15–25 min (no data) | 4 min | 17:12–17:16 |
| 2026-10-10 | H2-CFG: configuration_actions.js gap fill (Treat as, unfinished actions, recovery, macro delay) + 18 Show me links | help | rough guess 15–25 min (no data) | 3 min (agent's clock; looks short) | 17:12–17:15 |
| 2026-10-10 | H2-PROFILE: options/modes/LD Help gap fill (auto-load, mode rules topic, Undo) + ~20 Show me links | help | rough guess 15–25 min (no data) | 4 min | 17:12–17:16 |
| 2026-10-10 | DEAD-LEFT: 4 dead items removed (action_label.py, settings, signals); existing OSC input now selected (S14 gap) | fix | 3–8 min (table) | 5 min | 17:11–17:16 |
| 2026-10-10 | H2-HOME: home_devices/getting_started gap fill (cards, delete, Module Setup, pack refusals, Help window, command line) + ~15 links | help | rough guess 15–25 min (no data) | 4 min (agent's clock; doubtful) | 17:12–17:16 |
| 2026-10-10 | EW-1: 12 of 17 editors fit at pane minimum; ActionSelector label row; 5 left (ActionNode header) | refactor | 5–10 min (table) | 11 min | 17:11–17:22 |
| 2026-10-10 | EW-1 pass 2: title row, Root row, Map to Mouse button wrap; all editors fit at pane minimum | refactor | 5–10 min (table) | 7 min (whole job 19) | 17:23–17:30 |
| 2026-10-10 | MAP4: map lines for dead code, EW-1, ORPHAN, Help notes; action_label.py off the map | map catch-up | 5–7 min (table) | 2 min | 17:31–17:33 |
| 2026-10-10 | Full run 6 (seed 869523): unit-4 access violation in test_handson_G2_options_labels setup (no summary, 204 s); 1 order-dependent card-list count | test run | ~5 min (table) | 5:10 | 17:31–17:36 |
| 2026-10-10 | Q15-BM: Button Map History filter test (6), map gap 14 closed | test | 3–8 min (table) | 3 min | 17:50–17:53 |
| 2026-10-10 | T56: to-do 56 items already fixed (a3f448d2); S59 test restored | study+test | 3–8 min (table) | 1 min | 17:51–17:52 |
| 2026-10-10 | Lead: removed parked to-dos 58, 60, 70, 71, 74, 75, N22 (user); marked 62-69 done | lead | no timing data yet | 1 min | 17:52–17:53 |
| 2026-10-10 | Lead: to-do 92 won't fix (todo, map, tracker) | lead | no timing data yet | 1 min | 17:56–17:57 |
| 2026-10-10 | TR-FRAME: Trace framework study for OSC trace | study | rough guess 5–10 min (no data) | 2 min | 17:55–17:57 |
| 2026-10-10 | PROC-2: 159 test files start children via proc_tree; guard test | test fix | 3–8 min (table) | 11 min (159 files) | 17:51–18:02 |
| 2026-10-10 | Lead: OSC trace plan (studies + plan, no code) | plan | no timing data yet | ~8 min | 17:55–18:03 |
| 2026-10-10 | CRASH-G2: leaked test Backends' 60 s recovery timers likely crashed unit-4; conftest stops them (not reproduced) | crash hunt | rough guess 10–20 min (no data) | 32 min | 17:37–18:09 |
| 2026-10-10 | TR-DOCS: spec 01 S146/S148/S149 + 09 S166-S172, glossary, Help for OSC trace | docs | rough guess 10–15 min (no data) | 2 min | 18:07–18:09 |
| 2026-10-10 | TR-CORE: OSC trace API, row + 5 area ticks, rate limit, 10-then-quiet, log_limited | fix | rough guess 10–15 min (no data) | 4 min | 18:07–18:11 |
| 2026-10-10 | TR-RX: Receive/Inputs/Run trace taps, E3 (no traceback for bad incoming pattern), malformed bounded | fix | rough guess 15–20 min (no data) | 9 min | 18:07–18:16 |
| 2026-10-10 | TR-OUT: Output/Feedback trace, settings in memory (E1, E2), bounded failures (E4), Send OSC refusals (E9) | fix | rough guess 15–20 min (no data) | 12 min | 18:07–18:19 |
| 2026-10-10 | TR-SETUP: Setup/files/scripts/conditions trace; E5-E8, E10 fixed (quiet errors, bounded logs) | fix | rough guess 15–20 min (no data) | 12 min | 18:08–18:20 |
| 2026-10-10 | TR-E2E: end-to-end OSC trace test (13) over loopback; failed 8/13 before, passes now | test | rough guess 15–25 min (no data) | 12 min | 18:08–18:20 |
| 2026-10-10 | TR-POLISH: feedback names input, wildcard no double line, settings read under Setup | fix | 3–8 min (table) | 2 min | 18:21–18:23 |
| 2026-10-10 | Full run 7 (seed 382285): all passed (5566 unit + 75 + 47) | test run | ~5 min (table) | 5:15 | 18:23–18:29 |
| 2026-10-10 | MAP5: OSC trace map lines, spec built marks, Help/glossary wording matched to code | map catch-up | 5–7 min (table) | 9 min | 18:20–18:29 |
| 2026-10-10 | Lead: lint, commit 4e56e49a, push, tracker | lead commit | no timing data yet | 2 min | 18:29–18:31 |
| 2026-10-10 | INV-VJOY4: vJoy picker drops a switch to vJoy 4 when the control isn't on vJoy 4 (output_modules.py setState) | study | rough guess 10–15 min (no data) | 3 min | 18:35–18:38 |
| 2026-10-10 | INV-OSCRUN: no bug; OSC fires at Run with or without Monitor; 2 trace nits (double Monitor lines, Run using an open port not said) | study | rough guess 10–15 min (no data) | 5 min | 18:35–18:40 |
| 2026-10-10 | VJ1: vJoy picker switch really moves the binding (output_modules.py), S136 | fix | 3–8 min (table) | 3 min | 18:54–18:57 |
| 2026-10-10 | TQ1: 10-then-quiet errors only, Monitor double lines, Run uses open port | fix | 3–8 min (table) | 4 min | 18:45–18:49 |
| 2026-10-10 | OL1: OSC always listens while enabled (open_always/close_always, start-up call) | fix | rough guess 5–10 min (no data) | ~7 min | 18:49–18:56 |
| 2026-10-10 | OSC action outputs traced (vJoy/mouse writes from OSC inputs) | fix | rough guess (no data) | 2 min | 18:56–18:58 |
| 2026-10-10 | Full run 8 (seed 699739): all passed (5580 unit + 75 + 47) | test run | ~5 min (table) | 5:05 | 18:59–19:04 |
| 2026-10-10 | INV-VIEWER: vJoy Viewer drops OSC/LD wires (source-claim filter in module_pairing._module_pair_rows) | study | rough guess 5–10 min (no data) | 2 min | 19:08–19:10 |
| 2026-10-10 | INV-HILITE: OSC row highlight is off by spec (09 S32, 05 S131); options A tint / B jump | study | rough guess 5–10 min (no data) | 3 min | 19:08–19:11 |
| 2026-10-10 | VJ1b: vJoy turned off: picker marks (not available) and moves binding; write blocked, logged once; refresh works | fix | 3–8 min (table) | 8 min | 19:04–19:12 |
| 2026-10-10 | BUG-STOP: not a bug (port closed at quit, per decision); real Run/Stop test added | study+test | 3–8 min (table) | 2 min | 19:12–19:14 |
| 2026-10-10 | FIX-VIEWER: vJoy Viewer lists/lights OSC and LD wires (claim filter + OSC card name) | fix | rough guess 5–10 min (no data) | 3 min | 19:11–19:14 |
| 2026-10-10 | QML-WARN: 3 console messages fixed (Monitor release slot, Configuration page jump timer) | fix | 3–8 min (table) | 4 min | 19:12–19:16 |
| 2026-10-10 | Full run 9 (seed 55000): all passed (5593 unit + 75 + 47) | test run | ~5 min (table) | 5:05 | 19:16–19:21 |
| 2026-10-10 | Lead: lint, commit + push | lead commit | no timing data yet | 1 min | 19:21–19:22 |
| 2026-10-10 | DOCS: spec 09 S32/S141, 05 S131/S137-S139, 03 S30/S78a, glossary, Help for can't-send + OSC row | docs | rough guess 10–15 min (no data) | ~2 min (agent clock; doubtful) | 19:59–20:01 |
| 2026-10-10 | CI-TEST: test_final_09 S68 race (History writer builds its own Configuration) fixed in test | test fix | 3–8 min (table) | 4 min | 20:00–20:04 |
| 2026-10-10 | MK-CARD: source Home card red outline + line + tooltip; lead wired StatusPage | fix | rough guess 10–15 min (no data) | 5 min (+1 lead) | 19:59–20:05 |
| 2026-10-10 | MK-PICK: cant_send_text/bindings + red ⚠ in vJoy box, note removed (S53) | fix | rough guess 10–15 min (no data) | 8 min | 19:59–20:07 |
| 2026-10-10 | LOCK: singleton creation thread-safe (per-class RLock, double-checked) | fix | 3–8 min (table) | 1 min | 20:06–20:07 |
| 2026-10-10 | OSC-ROW: OSC row tint while pressed + follow while stopped (follows_press, followInput) | fix | rough guess 10–15 min (no data) | 9 min | 19:59–20:08 |
| 2026-10-10 | MK-ROWS: red ⚠ on rows + Find tick 'Can't be sent' on all four pages | fix | rough guess 10–15 min (no data) | 10 min | 19:59–20:09 |
| 2026-10-10 | NOTICE: profile-load notice naming bindings that can't be sent | fix | rough guess 5–10 min (no data) | 2 min | 20:07–20:09 |
| 2026-10-10 | XMARK: can't-send for Xbox, Logical Device, Send OSC (+ macro LD step), rows and card included | fix | rough guess 15–20 min (no data) | 5 min | 20:07–20:12 |
| 2026-10-10 | FOLLOW: LD + Keyboard tint/follow, LD axis bar, quick tap (live_follow.py) | fix | rough guess 10–15 min (no data) | 6 min | 20:09–20:15 |
| 2026-10-10 | WIRE-BARS: Configuration wire label red ⚠ + tooltip, OSC fader bars, OSC quick-tap press mark | fix | rough guess 10–15 min (no data) | ~6 min (agent clock unreliable) | 20:12–20:18 |
| 2026-10-10 | OSCNAME: Send OSC saves target name; Configuration quick tap checked (no fix needed) | fix | rough guess 10–15 min (no data) | 5 min | 20:15–20:20 |
| 2026-10-10 | MAP6: map + glossary for the can't-send batch (12 line groups + OSCNAME) | map catch-up | 5–7 min (table) | 6 min | 20:19–20:25 |
| 2026-10-10 | Full run + lint (can't-send batch, run 1): 5 failures (4 old-behaviour tests, 1 timing) | test | 5–6 min (table) | 6 min | 20:25–20:31 |
| 2026-10-10 | Full run + lint (can't-send batch, run 2): all green except unit-6 stalled in test_final_01 s12 (child app >120 s; passes alone 1.5 s) | test | 5–6 min (table) | 6 min | 20:31–20:37 |
| 2026-10-10 | Full run + lint (can't-send batch, run 3): no stall; 2 OSC page journeys fail (also alone) | test | 5–6 min (table) | 5 min | 20:39–20:44 |
| 2026-10-10 | OSCFAIL: 2 OSC journeys bound real port 8001 (stub on SingletonDecorator, not class); tests fixed | fix | 3–8 min (table) | 3 min | 20:45–20:48 |
| 2026-10-10 | HARNESS: journeys listen for OSC on 127.0.0.1 at an OS-picked port; new j12 (3) | fix | 3–8 min (table) | 3 min | 20:49–20:52 |
| 2026-10-10 | Full run + lint (can't-send batch, run 4): all green except order-dependent test_card_list_signal_release; test rewritten to warm up first | test | 5–6 min (table) | 5 min | 20:52–20:57 |
| 2026-10-10 | Full run + lint (can't-send batch, final): all green, seed 273667 | test | 5–6 min (table) | 5 min | 21:03–21:07 |
| 2026-10-11 | Lead: CI 51f5d8be triage + fix plan (Xbox width, j11 limit, LD extra release), read-only checks incl. old-vs-new j11 timing | lead | no timing data yet | 7 min | 04:33–04:40 |
| 2026-10-11 | Lead: off-screen screenshots of Map to Xbox editor, normal vs ⚠ (cut off) | lead | no timing data yet | 5 min | 04:41–04:46 |
| 2026-10-11 | JLIMIT: journey child run-time limit 100 s (harness 110 s); proof with limit 5 | fix | 3–8 min (table) | 2 min | 04:49–04:51 |
| 2026-10-11 | WIDTH: ⚠ boxes sized to shown text (4 editors), forced-⚠ width cases | fix | 3–8 min (table) | 5 min | 04:49–04:54 |
| 2026-10-11 | Lead: EW-2 plan + off-screen screenshots (Map to vJoy, Map to Logical Device at min/default pane) | lead | no timing data yet | ~3 min | 04:54–04:56 |
| 2026-10-11 | CI-LD: mechanism of extra release found (stale mode copy in ButtonReleaseActions), trigger not reproduced; no change | fix | 3–8 min (table) | 10 min | 04:49–04:59 |
| 2026-10-11 | Full run + lint (CI fixes: ⚠ width, journey limit): all green, seed 341426 | test | 5–6 min (table) | 5 min | 05:00–05:05 |
| 2026-10-11 | Lead: mock-up of option a) (narrow editors) in a throwaway worktree, 3 renders + comparison sheet | lead | no timing data yet | 9 min | 05:07–05:16 |
| 2026-10-11 | Lead: option a) mock-up re-rendered incl. red ⚠ state, sheet of 12 renders | lead | no timing data yet | 3 min | 05:16–05:19 |
| 2026-10-11 | CI on bab82917 (CI fixes) | ci | ~10 min (table) | ~13 min | 05:06–05:19 |
| 2026-10-11 | Lead: plan for to-dos 93-95 (read-only code checks) | lead | no timing data yet | 3 min | 05:23–05:26 |
| 2026-10-11 | RELMODE: release reads the live mode; extra release and skipped release proven on old code (3 tests) | fix | 3–8 min (table) | 3 min | 05:23–05:26 |
| 2026-10-11 | NARROW-LD: Map to Logical Device option a) layout (Speed overflow at default width also fixed) | fix | 3–8 min (table) | ~6 min (agent clock 05:23–05:27 too short) | 05:23–05:29 |
| 2026-10-11 | NARROW-VJ: Map to vJoy option a) layout; vJoy/control boxes size to widest text | fix | 3–8 min (table) | 5 min | 05:23–05:28 |
| 2026-10-11 | Full run + lint (editor layout + release fix): all green, seed 836712 | test | 5–6 min (table) | 6 min | 05:29–05:35 |
| 2026-10-11 | NOTICE-ROWS: rows, Find tick, Home card follow signal.cantSendChanged (4 tests) | fix | 3–8 min (table) | 2 min (agent clock) | 05:39–05:41 |
| 2026-10-11 | COND-95: ⚠ checked in Condition, macro, Script pickers (7 tests); Script page box 4 px past edge | test | 3–8 min (table) | 4 min | 05:39–05:43 |
| 2026-10-11 | LD-94: LD events synthetic + LD editor follows cantSendChanged (5 tests) | fix | 3–8 min (table) | 5 min | 05:39–05:44 |
| 2026-10-11 | NOTICE-OUT: output.notify_cant_send + sources + picker/Xbox/OSC listeners (8 tests) | fix | 3–8 min (table) | 7 min | 05:38–05:45 |
| 2026-10-11 | SCRIPT-98: Script setting name gives way, vJoy picker keeps natural width; 100/150/200 % cases | fix | 3–8 min (table) | ~3 min (agent clock) | 05:47–05:50 |
| 2026-10-11 | Full run + lint (93-95, 98): 1 failure (test_osc_run x2 alone, notice vs fake profile), 7 lint | test | 5–6 min (table) | 5 min | 05:50–05:55 |
| 2026-10-11 | OSCRUN-FIX: test_osc_run fake profile items → real InputItem (session app's card list follows the notice) | fix | 3–8 min (table) | 2 min | 05:57–05:59 |
| 2026-10-11 | Lead: test impact sweep (fake profiles vs new notice; old names) — 11 OSC test files moved to real InputItem; 20 files run targeted | lead | no timing data yet | 6 min | 05:57–06:03 |
| 2026-10-11 | Full run + lint (after sweep): 5 order-dependent failures (macro setting missing x4, osc_run fake profile get_input_item) | test | 5–6 min (table) | 5 min | 06:03–06:08 |
| 2026-10-11 | ORDER-OSC: leaked page models from test_final_05 (deleteLater never ran) followed the notice; helper deletes at once + conftest guard | fix | 3–8 min (table) | 10 min | 06:06–06:16 |
| 2026-10-11 | ORDER-MACRO: test_card_cant_send's fresh Configuration got the macro plugin's settings on first import; _settings_kept copies them back | fix | 3–8 min (table) | 18 min | 06:06–06:24 |
| 2026-10-11 | Full run + lint (93-95, 98, test isolation fixes): all green, seed 99154 | test | 5–6 min (table) | 5 min | 06:25–06:30 |
| 2026-10-11 | AUD-DEVNAMES: device name audit (3 missed updates on rename, 1 minor, spec question 10 S7) | research | 5–10 min (table) | ~2 min (agent clock) | 06:30–06:32 |
| 2026-10-11 | AUD-DRIVEN: 'Driven by' audit (4 proven stale cases, 2 by code; M5 Swap/Change vJoy send no signal) | research | 5–10 min (table) | 4 min | 06:30–06:34 |
| 2026-10-11 | AUD-CLAIMS: claims audit (vJoy sends fresh; Home output cards keep an old claim copy, probe-proven; keep 1 s poll) | research | 5–10 min (table) | 4 min | 06:30–06:34 |
| 2026-10-11 | AUD-LD: Logical Device names audit (3 views miss both signals, script variable creates a control silently) | research | 5–10 min (table) | 5 min | 06:30–06:35 |
| 2026-10-11 | WIDTH-SPLIT: width test children chunked (≤20 jobs, lazy per test); slowest child 35 s → 13.8 s | fix | 3–8 min (table) | 5 min | 06:36–06:41 |
| 2026-10-11 | Full run + lint (width split): 1 order failure test_ld_pick (also on CI a0584ac3) | test | 5–6 min (table) | 5 min | 06:42–06:47 |
| 2026-10-11 | CI on a0584ac3: failed (width test stall, fixed in tree; test_ld_pick order) | ci | ~10 min (table) | ~15 min | 06:30–06:45 |
| 2026-10-11 | ORDER-LDPICK: found program cause (Send OSC/Xbox can't-send refresh reported as action edits); stopped for user | fix | 3–8 min (table) | 4 min | 06:47–06:51 |
| 2026-10-11 | EDITFIX: display_only_signals in ActionModel; Send OSC/Map to Xbox ⚠ refresh not an edit (3 tests) | fix | 3–8 min (table) | 2 min (agent clock) | 06:59–07:01 |
| 2026-10-11 | Full run + lint (EDITFIX + width split): all green, seed 719001 | test | 5–6 min (table) | 5 min | 07:02–07:07 |
| 2026-10-11 | Lead: commit/push b96fab67, signals + contract for audit batch, 7 briefs | lead | no timing data yet | 3 min | 07:07–07:10 |
| 2026-10-11 | OSC-LD: OSC Feedback names from memory, page follows logicalDeviceModified (4 tests) | fix | 3–8 min (table) | 2 min | 07:09–07:11 |
| 2026-10-11 | NAMES: Library, device strip, InputIdentifier, DeviceNames relay follow deviceNamesChanged (4 tests) | fix | 3–8 min (table) | 3 min | 07:09–07:12 |
| 2026-10-11 | VIEWERS: 6 viewer files follow bindings/names/LD/module-files notices (21 tests) | fix | 3–8 min (table) | 4 min | 07:09–07:13 |
| 2026-10-11 | SPEC: 14 statements + 6 gaps for D-01-OWNER-NOTICES; S36 and claims-cache reworded | map catch-up | 5–7 min (table) | 5 min | 07:09–07:14 |
| 2026-10-11 | HOME: Home cards follow bindings/names/module files; user's device names on cards + page title (5 tests) | fix | 3–8 min (table) | 6 min | 07:08–07:14 |
| 2026-10-11 | Lead: start-up watcher lines (joystick_gremlin.py), Button Map poll → notice, copy-from label | lead | no timing data yet | 4 min | 07:14–07:18 |
| 2026-10-11 | NOTICES: owners send bindings/names/module-files notices, LD rows announce, gremlin/notice.py BurstNotice (17 tests) | fix | 3–8 min (table) | 8 min | 07:08–07:16 |
| 2026-10-11 | Lead: dead history hook removed; impact sweep 18 files run on their own (167 passed) | lead | no timing data yet | 3 min | 07:16–07:19 |
| 2026-10-11 | TEST-SWEEP: owner-notice end-to-end (9; 8 fail on old code) + sweep (2 found, 1 fixed) — ran a ~5 min --changed run without OK | test | 3–8 min (table) | 19 min | 07:09–07:28 |
| 2026-10-11 | Lead: Button Map profileModes binding fix, spec marked built, gaps closed, targeted 59 + map guards | lead | no timing data yet | 4 min | 07:28–07:32 |
| 2026-10-11 | Full run + lint (audit batch): 1 order failure (ld ⚠ test counted a pending notice) → settle first | test | 5–6 min (table) | 5 min | 07:30–07:35 |
| 2026-10-11 | VJ2-E2E: harness vjoy_ids + Change vJoy Output e2e (fails on old code: wire label, Driven by, Home cards) | test | 3–8 min (table) | 5 min | 07:35–07:40 |
| 2026-10-11 | Full run + lint (audit batch final): all green, seed 183838 | test | 5–6 min (table) | 5 min | 07:41–07:46 |
| 2026-10-11 | CI on b96fab67 | ci | ~10 min (table) | ~13 min | 07:08–07:21 |
| 2026-10-11 | RELNOTES: release-notes/1.0.32.md (passes release_body check) | docs | rough guess 5–10 min | 1 min | 07:48–07:49 |
| 2026-10-11 | RIG: harness sticks= + RIG preset + unplug/replug through the real device-change path (smoke 2) | test | 3–8 min (table) | 2 min (agent clock) | 07:47–07:49 |
| 2026-10-11 | J13: multi-device journey (7; 6 pass; found vJoy Viewer device list ignores the user's device name) | test | 3–8 min (table) | 4 min | 07:47–07:51 |
| 2026-10-11 | MAPCHECK: pre-release full map check (counts recounted 1249 S / 379 gaps, 96 line counts, stale tags) | map catch-up | 5–7 min (table) | 4 min | 07:48–07:52 |
| 2026-10-11 | E2E-PRESET: owner-notice e2e on the shared rig (10 pass) | test | 3–8 min (table) | 6 min (mostly waiting on RIG) | 07:47–07:53 |
| 2026-10-11 | PAIR-NAMES: vJoy Viewer device list shows/follows the user's device names (3 tests; j13 7/7) | fix | 3–8 min (table) | 2 min | 07:52–07:54 |
| 2026-10-11 | Full run + lint (release + multi-device): 2 failures (built-in table outside device_class; test_final_02 child timeout under load, passes alone) | test | 5–6 min (table) | 6 min (unit-3 425 s) | 07:55–08:01 |
| 2026-10-11 | Lead: device_class.home_key; module_pairing uses it; 75 targeted pass | lead | no timing data yet | 3 min | 08:01–08:04 |
| 2026-10-11 | CI on 4ada874f (release commit) | ci | ~10 min (table) | 16 min | 08:02–08:18 |
| 2026-10-11 | Release build 1.0.32 (release-exe workflow, publish) | release | no timing data yet; rough guess 10–20 min | 5 min | 08:18–08:23 |
| 2026-10-11 | SPEC-PKG: device-folders spec draft for review (scratch) | map catch-up | 5–7 min (table) | 2 min | 09:05–09:07 |
| 2026-10-11 | SPEC-PLANES: background/foreground spec draft for review (scratch) | map catch-up | 5–7 min (table) | 2 min | 09:05–09:07 |
| 2026-10-11 | SPEC-W07: page 07 + glossary written for both features (S106–S127) | map catch-up | 5–7 min (table) | 2 min | 09:19–09:21 |
| 2026-10-11 | SPEC-W-OTHER: pages 03/08/10 + README for both features | map catch-up | 5–7 min (table) | 3 min | 09:19–09:22 |
| 2026-10-11 | Lead: page 07 README count + cross-reference check; decisions/todo/tracker for both features | lead | no timing data yet | 6 min | 09:19–09:25 |
| 2026-10-11 | ARCH: device-folders contract (+3 scouts stopped once the contract covered callers) | research | 5–10 min (table) | 7 min | 09:27–09:34 |
| 2026-10-11 | A2 MOVE: one-time move OT-1 (folders_move.py, start-up call, 17 tests) | feature | no timing data; rough guess 25–40 min | 7 min | 09:35–09:42 |
| 2026-10-11 | A5 HISTORY: History per folder, restore by id, old entries readable (6 tests) | feature | no timing data; rough guess 25–40 min | 7 min | 09:35–09:42 |
| 2026-10-11 | A4b DEVICES: rename renames folder (refused if busy), scan sync, LD/OSC paths, auto map, diagnostics (13 tests) | feature | no timing data; rough guess 30–45 min | 8 min | 09:35–09:43 |
| 2026-10-11 | A6 EXPORT: device_zip (.gmap/.gtemplate), Device Pack on folders, DeviceExport + dialog (16 tests); fixed _module_items KeyError | feature | no timing data; rough guess 30–45 min | 8 min | 09:35–09:43 |
| 2026-10-11 | A1 STORE: store + registry + validate on device folders (30 tests) | feature | no timing data; rough guess 30–45 min | 10 min | 09:34–09:44 |
| 2026-10-11 | A4a SETUP-UI: Module Setup folder label, import from folders, Import Image, Delete Device, History filters, Export/Import Device menu items (8 tests) | feature | no timing data; rough guess 30–45 min | 9 min | 09:35–09:44 |
| 2026-10-11 | Lead: routing A1/A4a/A6 follow-ups; Calibration deviceIdOf slot + test; D-08-GMAP-IMPORT recorded | lead | no timing data yet | 5 min | 09:44–09:49 |
| 2026-10-11 | A1 follow-up: file_direction reads the file's direction; damaged message names the folder (2 tests) | fix | 3–8 min (table) | 1 min | 09:45–09:46 |
| 2026-10-11 | A7 LIBRARY: setups as .gmap, autosave whole folder, Swap/Copy pictures per folder, Remove removes folder, rename refusal (10 tests) | feature | no timing data; rough guess 30–45 min | 10 min | 09:36–09:46 |
| 2026-10-11 | A6 follow-up: .gmap import with bindings = one Undo step (3a); dialog opens from A4a props; messages name the folder | fix | 3–8 min (table) | 2 min | 09:45–09:47 |
| 2026-10-11 | Lead: D-10-GMAP-SETUPS spec wording (10 S14 S44, new S63) + decision | lead | no timing data yet | 2 min | 09:44–09:46 |
| 2026-10-11 | Lead: map rows for new files (device_zip, device_export, DialogDeviceExport, folders_move); move message box suppressed under tests + test; routing | lead | no timing data yet | 3 min | 09:46–09:49 |
| 2026-10-11 | A7 follow-up: every setup .gmap (bindings-only, damaged), device_zip no_file_ok/has_folder (2 tests + 1 strict xfail) | fix | 3–8 min (table) | 2 min | 09:48–09:50 |
| 2026-10-11 | Lead: device_pack._from_gmap restores a damaged .gmap's bindings (10 S20a); strict xfail removed; 30 pass | fix | 3–8 min (table) | 3 min | 09:50–09:53 |
| 2026-10-11 | A3 BUTTONMAP: edit temp folder, unused-picture clean-up, recovery.json, copy/template pictures, templates as folders + .gtemplate, Picture missing placeholder, rename refusal shown (13 tests) | feature | no timing data; rough guess 35–55 min | 16 min | 09:35–09:51 |
| 2026-10-11 | Lead: A3 follow-up analysis (Module Setup photo vs edit folder), SETUP-PHOTO started, test routing | lead | no timing data yet | 2 min | 09:51–09:53 |
| 2026-10-11 | Lead: device_pack._zip_readable accepts .gmap (every Library .gmap export failed read-back) | fix | 3–8 min (table) | 2 min | 09:55–09:57 |
| 2026-10-11 | SETUP-PHOTO: Module Setup Import Image waits in the setup edit; Cancel leaves the folder unchanged; Save one write (2 tests) | fix | 3–8 min (table) | 5 min | 09:52–09:57 |
| 2026-10-11 | A8a-5: history/home/handson/help tests moved to device folders (11 files; 2 tests that had been passing without testing anything now really test) | agent tests | no timing data yet | 9 min | 09:49–09:58 |
| 2026-10-11 | Lead: renameTemplate writes the name before moving the folder (a failure leaves both as they were); Help "Device folder" label; the help test checks "·" toggle rows word by word | fix | 3–8 min (table) | 3 min | 09:58–10:01 |
| 2026-10-11 | A8a-1: Device Pack / audit tests moved to device folders (13 files, 141 pass, 5 retired for removed file bindings/choices) | agent tests | no timing data yet | 13 min | 09:48–10:01 |
| 2026-10-11 | A8a-2: Library / Logical Device tests moved to device folders (64 files checked, 23 changed, 1 retired; found the twin folder bug) | agent tests | no timing data yet | 13 min | 09:48–10:01 |
| 2026-10-11 | Lead: store.device_dir finds the folder holding exactly the id and name first (an unplugged twin wrote into the other twin's folder) | fix | 3–8 min (table) | 3 min | 10:02–10:02 |
| 2026-10-11 | A8a-4: batch/final tests moved to device folders (48 files, 884 pass, 16 edited, 1 retired for removed 07 S81) | agent tests | rough guess 30 min | 14 min | 09:49–10:03 |
| 2026-10-11 | A8a-3: Button Map / configuration tests moved to device folders (48 files, 912 pass, 14 edited, none retired) | agent tests | no timing data yet | 20 min | 09:48–10:08 |
| 2026-10-11 | A8b: tests m–z, journeys, smoke scripts moved to device folders (about 60 files; 1 file and 6 tests retired for removed rules; 18 failures routed) | agent tests | rough guess 35–55 min | 37 min | 09:36–10:13 |
| 2026-10-11 | MAP-3: map pages 04, 06, 09, 10 for device folders (10 statements marked built; found 2 Library window .gmap bugs) | docs | 3–8 min (table) | 4 min | 10:09–10:13 |
| 2026-10-11 | MAP-2: map pages 07, 08 for device folders (14 statements built, 6 partly) | docs | 3–8 min (table) | 6 min | 10:09–10:15 |
| 2026-10-11 | Lead: check of A8b's failures, split into 5 fix agents | lead | no timing data yet | 5 min | 10:13–10:17 |
| 2026-10-11 | MAP-1: map pages 01, 02, 03 for device folders (16 statements marked built) | docs | 3–8 min (table) | 9 min | 10:09–10:18 |
| 2026-10-11 | FIX-STORE: second paste gets its own name; built-in lists into device_class; refused move logs a warning | fix | 3–8 min (table) | about 3 min | 10:16–10:19 |
| 2026-10-11 | FIX-OSC-T: 4 OSC carry test files read the .gmap export (39 pass) | agent tests | 3–8 min (table) | 2 min | 10:16–10:18 |
| 2026-10-11 | FIX-LIB: Library window export adds .gmap (no X.gmap.gmap), import takes .gmap (3 new tests) | fix | 3–8 min (table) | 3 min | 10:16–10:19 |
| 2026-10-11 | FIX-BM: Button Map Save refused on a damaged file copies no picture (07 S12, GL-079) | fix | 3–8 min (table) | 5 min | 10:16–10:21 |
| 2026-10-11 | Lead: the damage check moved into store.commit_edit (all callers), loop variable fix; new store test fails on the old order | fix | 3–8 min (table) | 3 min | 10:20–10:23 |
| 2026-10-11 | FIX-PACK: Device Pack writes through the store again; pack_checks.py (modules layer imports no UI); wires handed to device_zip | fix | 3–8 min (table) | 6 min | 10:16–10:22 |
| 2026-10-11 | Lead: applied FIX-PACK's 3 call-site edits, test impact sweep (--changed, ~6500 tests, 3 failures fixed), map lines + README counts, to-do | lead | sweep: no timing data yet; rough guess 3–5 min | sweep 7 min; whole step 12 min | 10:23–10:31 |
| 2026-10-11 | Full run + lint (device folders): 6449 unit + journeys + interaction; 1 order-dependent failure (test_audit_devices, seed 758199); lint 0 new | test | 5–6 min (table) | 6 min run, 1 min lint | 10:31–10:37 |
| 2026-10-11 | TRACE-ORDER: order-dependent test_audit_devices failure = a test leaving a pJoy Pro folder; fixture cleans it (test only) | fix | 3–8 min (table) | 7 min | 10:37–10:44 |
| 2026-10-11 | Lead: Export/Import Device box never opened (a Popup made as a window, "transientParent" error the user hit); StatusPage makes it on the window's overlay; new end-to-end test fails before, passes after | fix | 3–8 min (table) | 6 min | 10:46–10:46 |
| 2026-10-11 | PLAN-TESTS: step 2 test impact (about 25 files + golden images, 20–25 new tests) | review | 5–10 min (table) | 2 min | 10:46–10:48 |
| 2026-10-11 | PLAN-BUILD: step 2 build plan (trace, statement→change, data shape, split, contract, risks) | review | 5–10 min (table) | 3 min | 10:46–10:49 |
| 2026-10-11 | Confirming full run (seed 758199) + lint; commit 44ab601c; push both branches | test | 5–6 min (table) | run 6 min; commit/push 2 min | 10:45–10:52 |
| 2026-10-11 | SPEC-P: planes answers P1a–P7a into pages 07, 08, 03 (new 03 S135) | docs | 3–8 min (table) | 1 min | 10:52–10:53 |
| 2026-10-11 | Lead: decisions row D-07-PLANES-ANSWERS, todo, README count, tracker OT-2, planes contract | lead | no timing data yet | 6 min | 10:53–10:54 |
| 2026-10-11 | PD: Layers panel for planes (folded Background row with eye/lock/opacity, per-plane rows and toggles; 14 tests) | feature | rough guess 15–30 min | 6 min | 10:56–11:02 |
| 2026-10-11 | PG: print for planes (Page, Include background, 100% from the bottom picture, full resolution, views never print; 7 tests) | feature | rough guess 15–30 min | 6 min | 10:56–11:02 |
| 2026-10-11 | PA: planes Python contract (store photo helpers, planes_once OT-2, load/save, Import keeps background; 24 tests) + greyscale fix | feature | rough guess 15–30 min | 9 min + 1 min | 10:55–11:05 |
| 2026-10-11 | PE: planes menus + properties (Move to Background/Foreground, Reset Shape, Look section, 4000 px cap; 7 tests) | feature | rough guess 15–30 min | 8 min | 10:56–11:04 |
| 2026-10-11 | PC: planes editor core (planes, plane-limited stacking/hit/snap, faint foreground, chips follow, Undo nodes-only, look URLs, planeMoved; 15 tests) | feature | rough guess 15–30 min | 10 min | 10:56–11:06 |
| 2026-10-11 | PB: planes carry-through (Device Pack export/import background, Library photo, Copy carries background, Logical Device card, Swap; 9 tests) | feature | rough guess 15–30 min | 12 min | 10:55–11:07 |
| 2026-10-11 | PD follow-up: Move to Background/Foreground in the Layers row menu (16 tests) | fix | 3–8 min (table) | 2 min | 11:05–11:07 |
| 2026-10-11 | PF: planes window (Background menu, mode switch/banner/hint/Esc/Ctrl+B, plane view settings, photo special cases removed, Copy background tick, Space-drag pan, Moved-to message, look URLs; 4 tests incl. off-screen window) | feature | rough guess 15–30 min | 13 min | 10:56–11:09 |
| 2026-10-11 | CI on 44ab601c (device folders): 1 order-dependent failure (test_final_05 plugin-directory a list, seed 867771) | ci | ~10 min (table) | 17 min (parts ran ~15 min) | 10:52–11:09 |
| 2026-10-11 | PF follow-up: opacity slider value lost when entering Background mode (pending save) | fix | 3–8 min (table) | 1 min | 11:13 |
| 2026-10-11 | TRACE-CI: CI failure test_final_05 = the test made the plugin manager under its fake settings when no earlier test had; makes it first (test only) | fix | 3–8 min (table) | 5 min | 11:10–11:15 |
| 2026-10-11 | PT: existing tests moved to planes (photo fixtures → background nodes, Photo flows → Background, Layers row, look API, Help words; 1 file retired) | agent tests | rough guess 15–30 min | 19 min | 10:56–11:15 |
| 2026-10-11 | PH-HELP: "Background and foreground" Help topic, Photo wording removed (55 Help tests) | docs | 3–8 min (table) | 2 min | 11:16–11:18 |
| 2026-10-11 | PH-MAP: map pages 03, 07, 08, 10 for planes (about 45 statements marked built; gaps G26 G27 41 closed; G28, G29, BG-SHOWME opened) | docs | 3–8 min (table) | 7 min | 11:16–11:23 |
| 2026-10-11 | PF follow-up: Ctrl+Shift+B moves the selection to the other plane (G28) | fix | 3–8 min (table) | 1 min | 11:24 |
| 2026-10-11 | CARRY-T: background travels through History restore, .gmap, Library restore, Device Pack round trip (6 tests) | agent tests | 3–8 min (table) | 2 min | 11:24–11:26 |
| 2026-10-11 | GOLDEN: harness moved to background pictures; 48 golden files re-recorded and checked (1 open question: Background row under a kind filter) | agent tests | rough guess 10–20 min | 16 min | 11:16–11:32 |
| 2026-10-11 | CI on the step 1 test fix (test_final_05) | ci | ~10 min (table) | about 15 min | 11:16–11:31 |
| 2026-10-11 | Full run + lint (planes, seed 558790): 5 failures — 4 stale tests/tooltip fixed by the lead (49 pass), 1 order-dependent (TRACE-2); lint 0 new | test | 5–6 min (table) | run 6 min, fixes 4 min | 11:32–11:38 |
| 2026-10-11 | TRACE-2: test_final_03 order failure = Delete Device test left kept-stubs set; fixture restores Home card settings (test only) | fix | 3–8 min (table) | 6 min | 11:38–11:44 |
| 2026-10-11 | Confirming full run (seed 558790) green + lint 0 new; commit 2d14cc37; push | test | 5–6 min (table) | 6 min + 1 min | 11:44–11:50 |
| 2026-10-11 | Planes (step 2) end to end: user go 11:00 → commit 11:50 (8 build agents, 6 follow-ups, Help/map/golden/paths agents, 2 trace agents, 2 full runs) | feature batch | no timing data; rough guess 75–100 min | 50 min to commit | 11:00–11:50 |
| 2026-10-11 | Lead: Q2a Q3a spec wording (07 S120, 03 S88), decision D-07-PLANES-FOLLOWUP, Q1a split | lead | no timing data yet | 3 min | 11:53–11:56 |
| 2026-10-11 | CI on 2d14cc37 (planes) | ci | ~10 min (table) | about 19 min | 11:50–12:09 |
| 2026-10-11 | SHOWME-HELP: three Show me links in the Background topic (53 Help tests) | docs | 3–8 min (table) | 2 min | 12:08–12:10 |
| 2026-10-11 | SHOWME-CODE: show:buttonmap links (Main.qml handler + window revealForHelp; 3 end-to-end tests + link check) | fix | 3–8 min (table) | 3 min | 12:08–12:11 |
| 2026-10-11 | Q1a full run (seed 231591) green + lint 0 new; commit 6c6be17e; push | test | 5–6 min (table) | 6 min + 1 min | 12:12–12:19 |
| 2026-10-11 | Q1a Show me end to end: user go → commit | fix batch | 3–8 min per agent + full run (table) | 12 min | 12:07–12:19 |
| 2026-10-11 | ARG-W: unused photo argument removed from openForDevice and its callers (62 tests) | fix | 3–8 min (table) | 1 min | 12:29–12:30 |
| 2026-10-11 | SPEC-W: 9 stale spec sentences reworded (03 S62, 04 S2, 06 S95/LD3, 07 S106, 08 S85 S87, 09 S44 S168) | docs | 3–8 min (table) | 2 min | 12:28–12:30 |
| 2026-10-11 | OSC-W: OSC trace/Help text names OSC/module.json (5 tests failed before, 71 pass) | fix | 3–8 min (table) | 1 min | 12:29–12:30 |
| 2026-10-11 | EDT-T: editor tests for S94 S118 S122 in Background mode (6 pass, 1 strict xfail = leader-end snap lost on release) | agent tests | 3–8 min (table) | 4 min | 12:29–12:33 |
| 2026-10-11 | CI on 6c6be17e (Show me links) | ci | ~10 min (table) | about 18 min | 12:19–12:37 |
| 2026-10-11 | SCOUT-UNDO: Undo steps per transform/move gesture traced (cause: hover highlight pushes steps mid-drag) | review | 5–10 min (table) | 3 min | 12:37–12:40 |
| 2026-10-11 | Lead: commit 93862cc9 + push; spec S55a, S85 sentence, decision D-07-GESTURE-UNDO; memory: plain question numbers | lead | no timing data yet | 4 min | 12:43–12:47 |
| 2026-10-11 | LEADER: attachNear keeps the snap point on release, pictures not chip pins, owner's plane only (G30; 4 checks + xfail now passes) | fix | 3–8 min (table) | 3 min | 12:46–12:49 |
| 2026-10-11 | UNDO: one Undo step per drag (hover only repaints; gestureActive/beginGesture/endGesture/stopGesture; onCanceled; leader drop line) — 7→1 and 5→1 steps | fix | 3–8 min (table) | 10 min | 12:46–12:56 |
| 2026-10-11 | Lead: rulers golden re-recorded (history counts only), 31 golden pass | lead | no timing data yet | 4 min | 12:57–13:01 |
| 2026-10-11 | UNDO-T: one real drag per gesture kind counted (21 kinds, both planes): before 2–8 steps, after 1; found the ruler new-guide 2 steps | agent tests | 3–8 min (table) | 12 min | 12:47–12:59 |
| 2026-10-11 | Lead: ruler new guide one step (VkbRigFace beginGesture/endGesture/onCanceled); xfail removed; 32 pass | fix | 3–8 min (table) | 3 min | 12:59–13:02 |
| 2026-10-11 | CI on 93862cc9 (small items) | ci | ~10 min (table) | about 17 min | 12:43–13:00 |
| 2026-10-11 | Full run (seed 111279) + lint: 1 golden (rulers history counts after the ruler fix) re-recorded; commit 3130f65c; push | test | 5–6 min (table) | 6 min + 2 min | 13:00–13:07 |
| 2026-10-11 | Undo per drag + leader snap end to end: user go 12:46 → commit 13:07 | fix batch | 3–8 min per agent + full run (table) | 21 min | 12:46–13:07 |
| 2026-10-11 | CI on 3130f65c: 1 failure (Input Tester log test waited 15 s; passes locally); failed job re-run | ci | ~10 min (table) | about 18 min | 13:07–13:25 |
| 2026-10-11 | PANCUR: closed hand while panning (cursor-only overlay; the handler's cursorShape lost to the editor area); real-window test | fix | 3–8 min (table) | 4 min | 13:21–13:25 |
| 2026-10-11 | Full run (pan cursor, seed 599005): 3 failures + unit-4 stopped by the hang guard, all pass alone (load); journeys pass with the same seed | test | 5–6 min (table) | 6 min + 3 min checks | 13:26–13:35 |
| 2026-10-11 | TRACE-J20: j20 load failure = real bug G32 (commit_edit leaves the edit folder in "committing" when its removal fails) | review | 5–10 min (table) | 1 min | 13:33–13:34 |
| 2026-10-11 | Repeat full run (seed 997138) green; commit pan cursor + canvas-menu spec; push | test | 5–6 min (table) | 6 min + 1 min | 13:33–13:40 |
| 2026-10-11 | ROW: Undo/Redo + Foreground/Background row removed; Show me switch link and Help updated | fix | 3–8 min (table) | 1 min | 13:42–13:43 |
| 2026-10-11 | SAVEFIX: G32 — Save drops state.json before removing the edit folder (3 tests fail before, pass after) | fix | 3–8 min (table) | 1 min | 13:42–13:43 |
| 2026-10-11 | CANVAS: Edit Background / Exit Background Editing on the empty-space menu (6 tests fail before, pass after) | fix | 3–8 min (table) | 2 min | 13:42–13:44 |
| 2026-10-11 | ROW-T: tests moved off the removed row (Edit menu/keys, Show me banner+row only, absence checks; 21 pass) | agent tests | 3–8 min (table) | 2 min | 13:42–13:44 |
| 2026-10-11 | Canvas-menu batch full run (seed 356469): 2 goldens (new menu row) re-recorded; lint fix; commit 2062380e; push | test | 5–6 min (table) | 6 min + 2 min | 13:45–13:52 |
| 2026-10-11 | Canvas-menu batch end to end: user go 13:41 → commit 13:52 | fix batch | 3–8 min per agent + full run (table) | 11 min | 13:41–13:52 |
| 2026-10-11 | SP-DOC: Help for the side panels (new topic, tool-row topics fixed; 56/57 pass, 1 waits on WIN) | docs | 3–8 min (table) | 3 min | 14:00–14:03 |
| 2026-10-11 | SIDE: SidePanel.qml (strip, pin, fold, resize, overlay vs beside; 11 tests fail without it) | feature | rough guess 15–30 min | 4 min | 14:00–14:04 |
| 2026-10-11 | DOCK: left/right rows removed from ToolDock/ToolRow/ToolPane; sideState/setSideState + reset (4 tests fail before, pass after) | refactor | 5–10 min (table) | 4 min | 14:00–14:04 |
| 2026-10-11 | WIN: side panels in the window (Chips left, Layers right; Edit-only, Background fold, narrow-window fold, View › Chips, Show me row) | feature | rough guess 20–35 min | 10 min | 14:00–14:10 |
| 2026-10-11 | Lead: Layers panel hides its own title and × inside the side panel (showTitle); 40 tests pass | fix | 3–8 min (table) | 2 min | 14:11–14:13 |
| 2026-10-11 | SP-DOC follow-up: View › Chips in the Help (57 Help tests pass) | docs | 3–8 min (table) | 1 min | 14:10–14:11 |
| 2026-10-11 | CI on 2062380e: 1 failure, the same Input Tester log test (second time) → TRACE-TESTER | ci | ~10 min (table) | about 19 min | 13:52–14:11 |
| 2026-10-11 | SP-T: side-panel e2e (13) + tool-row and Layers smokes updated (80 pass) | agent tests | rough guess 15–30 min | 11 min | 14:00–14:11 |
| 2026-10-11 | TRACE-TESTER: Input Tester stopped logging after a refused 1 MB rotation (real bug, fixed; test fails before) | fix | 3–8 min (table) | 1 min | 14:11–14:12 |
| 2026-10-11 | Lead: restoreSides before the first Edit (timing gap); map lines | fix | 3–8 min (table) | 3 min | 14:12–14:15 |
| 2026-10-11 | Side panels full run (seed 128423): 3 real failures fixed (tooltip delay, panelWidth binding, a test asking Layers to float), 2 load flakes; commit 909bbba6; push | test | 5–6 min (table) | 6 min + 3 min fixes | 14:13–14:22 |
| 2026-10-11 | Side panels end to end: user go 13:56 → commit 14:22 | feature batch | rough guess 25–40 min (no timing data) | 26 min | 13:56–14:22 |
| 2026-10-11 | LOOK-DOC: Help for the folded bar, arrow, slide and the Chips filter row (57 Help tests) | docs | 3–8 min (table) | 1 min | 14:29–14:30 |
| 2026-10-11 | CHIPSROW: Chips filter on its own row (S132; width tests fail before, pass after) | fix | 3–8 min (table) | 4 min | 14:29–14:33 |
| 2026-10-11 | Lead: Chips minimum 180→210 so Chip only is never cut; test fails at 180, passes at 210 | fix | 3–8 min (table) | 3 min | 14:36–14:39 |
| 2026-10-11 | CI on 909bbba6 (side panels + Input Tester log fix): green | ci | ~10 min (table) | about 14 min | 14:22–14:36 |
| 2026-10-11 | LOOK: folded bar like the old side row (tab at the top: name, pin; arrow; spine shadow; hover; 120 ms slide); 11 of 15 tests fail on the old panel | feature | rough guess 10–20 min | 10 min | 14:29–14:39 |
| 2026-10-11 | SC-LIST: ShortcutList.qml (read-only key list grouped by menu, Mouse rows, search; nothing run) | feature | 3–8 min (table) | about 2 min (agent's clock) | 14:50–14:51 |
| 2026-10-11 | SC-KEYS: Command Palette removed; Shortcuts list in its tool pane; 22 keys wired with menu hints; Zoom In/Out, Select All (nothing run) | feature | 3–8 min (table) | 4 min | 14:50–14:54 |
| 2026-10-11 | WINS: ButtonMapOptionsWindow.qml + ShortcutsWindow.qml (nothing run) | feature | rough guess 15–30 min | about 2 min (agent's clock) | 15:01 |
| 2026-10-11 | PSTORE: side-panel state, props split, print-area-shown in ButtonMapOptions (nothing run) | feature | rough guess 15–30 min | 2 min | 15:00–15:02 |
| 2026-10-11 | CMD: rig_commands.js (Insert/Arrange/Format list, enabled, run; nothing run) | feature | rough guess 15–30 min | 4 min | 15:00–15:04 |
| 2026-10-11 | DOC: Button Map Help rewritten for the menu bar, windows, no tool rows; glossary rows (nothing run) | docs | 3–8 min (table) | 4 min | 15:01–15:05 |
| 2026-10-11 | CMD follow-up: 20 more commands (Align, Distribute, Crop, Edit Points, Snap Points, table deletes, callout ends) — 100 in all | feature | 3–8 min (table) | 1 min | 15:04–15:05 |
| 2026-10-11 | MENU: menu bar per S135 with Insert/Arrange/Format from rig_commands, Cut, tool rows removed, Properties under Layers, Options/Shortcuts windows, panel store (nothing run) | feature | rough guess up to 40 min | 5 min (agent's clock; checked) | 15:01–15:06 |
| 2026-10-11 | Lead: Leader menu (rig_commands list + window menu + separators), spec S134/S135, Help | fix | 3–8 min (table) | 6 min | 15:10–15:16 |
| 2026-10-11 | DRAWER: folded side panel as a drawer left ajar (7 dp edge, hover peek with name + pin, slide; nothing run) | feature | rough guess 10–20 min | 4 min | 15:04–15:08 |
| 2026-10-11 | Lead: menu order pass (Insert/Arrange/Format groups and separators, tables to Format, Text › and Picture…), sub separators, fitSides width, spec + Help | fix | no timing data yet | 8 min | 15:16–15:24 |
| 2026-10-11 | Lead: menu follow-ups (Properties shown kept, Reset View label, S93/S99/S135 wording, decision row) | fix | 3–8 min (table) | 4 min | 15:26–15:30 |
| 2026-10-11 | Lead: Background menu moved into Edit › Background › (window, Help, spec S39/S113/S135, glossary) | fix | 3–8 min (table) | 4 min | 15:31–15:35 |
| 2026-10-11 | Lead: View menu right after Edit (window, Help list, spec S135) | fix | 3–8 min (table) | 3 min | 15:36–15:39 |
| 2026-10-11 | Lead: Keyboard Shortcuts window pin; unpinned closes on a click elsewhere; pin kept; spec S100 | fix | 3–8 min (table) | 4 min | 15:40–15:44 |
| 2026-10-11 | SHOWME: one Show me per group (8 menus, Chips, Layers, Properties) + tests (6 of 10 fail before, 10 pass) | feature | rough guess 15–30 min | 6 min | 15:20–15:26 |
| 2026-10-11 | SPEC-MAP: page 07 up to date for the menu-bar batch (gaps G33–G38 found) | docs | 3–8 min (table) | 7 min | 15:20–15:27 |
| 2026-10-11 | Lead: SPEC-MAP findings — print-area lock leftovers removed, Mouse "Wheel", Reset Panels keeps print area + Shortcuts pin, Crop/ID Column ticks, S134/S99 wording | fix | 3–8 min (table) | 8 min | 15:28–15:36 |
| 2026-10-11 | SHOWME follow-up: 4 help test failures fixed (65/65 help tests) | fix | 3–8 min (table) | 3 min | 15:26–15:29 |
| 2026-10-11 | T-PANELS: drawer tests (16; 11 fail on HEAD), window/e2e tests on the panel store (28), tool-row tests retired | agent tests | rough guess 15–30 min | 11 min | 15:20–15:31 |
| 2026-10-11 | T-MENUS: menu bar, command menus, keys, Options and Keyboard Shortcuts window tests (43; found 4 program bugs) | agent tests | rough guess 15–30 min | 15 min | 15:21–15:36 |
| 2026-10-11 | Lead: T-MENUS's 4 bugs (print area while editing, keys run nothing from the child windows, unpinned Shortcuts closes, Shortcuts lists greyed menus); key guard probed off-screen; tool-row files deleted; map G34–G37 closed | fix | 3–8 min (table) | 9 min | 15:36–15:45 |
| 2026-10-11 | Full run + lint (menu-bar batch): 4 Button Map tests failed (3 read the old source layout, 1 clicked during the drawer's 120 ms slide); fixed, 34 pass targeted | test | 5–6 min (table) | 6 min + 4 min fixes | 15:46–15:56 |
| 2026-10-11 | Button Map audit: 6 read-only agents (menus, panels, edit, print/planes, spec/Help, canvas); 11 verified bugs, 0 crashes | review | 5–10 min (table) | 6 min (AUD-MENUS longest) | 15:52–15:58 |
| 2026-10-11 | FIX-PTR: Shift/Ctrl+right-click acts on the clicked item (G42) | fix | 3–8 min (table) | 3 min | 15:59–16:01 |
| 2026-10-11 | FIX-DOC: Help, glossary, map G39–G48, agent_log crash | docs | 3–8 min (table) | 2 min | 15:59–16:01 |
| 2026-10-11 | FIX-CMD: whyDisabled, Esc stops drawing, stale table rows grey (G44 G45 G47) | fix | 3–8 min (table) | 5 min | 15:59–16:04 |
| 2026-10-11 | FIX-SEL: paste plane, Backspace path point, stale table target (G41 G43 G44) | fix | 3–8 min (table) | 8 min | 15:59–16:07 |
| 2026-10-11 | FIX-WIN: recovery copy, open drag, kept pin, greyed-row tooltip, Mouse before Keys (G39 G40 G46 G47) | fix | 3–8 min (table) | 12 min (off-screen hover for the tooltip test) | 15:59–16:11 |
| 2026-10-11 | Lead: golden re-record (api_sweep), 3 tests updated, lint fix, map G39–G48 closed | fix | 3–8 min (table) | 6 min | 16:07–16:13 |
| 2026-10-11 | Full run + lint (audit fixes): 2 static-check failures (hand-set tooltip delay; Cancel's cleanup moved to endEditUnsaved), fixed, 27 pass targeted; lint 0 new | test | 5–6 min (table) | 6 min + 3 min fixes | 16:14–16:23 |
| 2026-10-11 | Right-click batch: OPTS (favourites store, count option) | feature | 3–8 min (table) | 2 min | 16:33–16:35 |
| 2026-10-11 | Right-click batch: CMD (edit ids, info, applies, Repeat) | feature | 3–8 min (table) | 3 min | 16:33–16:36 |
| 2026-10-11 | Right-click batch: SEL (Cut one step, Paste Here, Select All, editor wiring) | feature | 3–8 min (table) | 3 min | 16:33–16:36 |
| 2026-10-11 | Right-click batch: DOC (spec wording, map, Help, glossary) | docs | 3–8 min (table) | 4 min | 16:33–16:37 |
| 2026-10-11 | Right-click batch: CTX (shared menu Favourites block, ☆/★, ×) | feature | 3–8 min (table) | 6 min | 16:33–16:39 |
| 2026-10-11 | Right-click batch: TEST (end to end 14 + carry-through 5) | agent tests | ~10 min | 7 min | 16:33–16:40 |
| 2026-10-11 | Right-click batch: MENU (command tags, new rows, favourites list) | feature | 3–8 min (table) | 8 min | 16:33–16:41 |
| 2026-10-11 | Right-click batch: WIN (menu-bar ☆, Edit rows/keys through commands, Show in Layers, Properties…) | feature | 3–8 min (table) | 9 min | 16:33–16:42 |
| 2026-10-11 | Lead: contract, routing 6 agent requests, RigPointerArea point, option.py group, golden re-record (18 files), map G49/G50 + counts | lead | ~5 min | 16 min (incl. 3 min golden) | 16:31–16:47 |
| 2026-10-11 | Full run + lint (right-click batch): all program tests green; test_times.json too old for today's new files (refreshed from CI run 38176638314); 24 lint items in new test files fixed; 46 pass targeted | test | 5–6 min (table) | 6 min + 4 min fixes | 16:47–16:57 |
| 2026-10-11 | Fix list collection (13 items, record only; 2 scouts: Device Pack vs .gmap, icons rendered) | lead | — | ~35 min (user's pace) | 17:05–17:40 |
| 2026-10-11 | B1 XBOX: Xbox face picture as program art | fix | 3–8 min (table) | 2 min | 17:43–17:45 |
| 2026-10-11 | B1 DOC: spec first (07 S138 S139, 03 S136, 06 S98; S98 S100 S137 S143 S58), Help, glossary | docs | 3–8 min (table) | 5 min | 17:43–17:48 |
| 2026-10-11 | B1 MENU: Hide/Lock favourites | fix | 3–8 min (table) | 6 min | 17:42–17:48 |
| 2026-10-11 | B1 DRAG: 4 px dead zone | fix | 3–8 min (table) | 9 min | 17:42–17:51 |
| 2026-10-11 | B1 BANNER: view-only banner + link | fix | 3–8 min (table) | 11 min | 17:42–17:53 |
| 2026-10-11 | B1 OPTWIN: Options/Shortcuts ×, pin, close on click, divider | fix | 3–8 min (table) | 10 min | 17:43–17:53 |
| 2026-10-11 | B1 HOME: page bar left + Home Undo/Redo (found a Windows file-in-use bug) | feature | 3–8 min (table) | 15 min | 17:43–17:58 |
| 2026-10-11 | Lead B1: decision, briefs, 3 icons (an Edit-tool slip wrote raw glyphs, fixed), ContextMenu ☆ on toggles, Print & Export ×, lint | lead | ~5 min | 8 min | 17:40–17:48, 17:53–17:59 |
| 2026-10-11 | B2 CARD: Tools + Home routes, old export window removed | fix | ~10-15 min (rough guess) | 3 min | 18:02–18:05 |
| 2026-10-11 | B2 ZIP: .gmap made by / note / modes / output pictures; + 2 follow-up fixes (root actions, twin by id) | feature | ~10-15 min (rough guess) | 4 + 1 + 1 min | 18:02–18:06, 18:09, 18:14–18:15 |
| 2026-10-11 | B2 WIN: Export / Import Device window, target choice, openFor | feature | ~10-15 min (rough guess) | 4 min | 18:02–18:06 |
| 2026-10-11 | B2 DOC2: spec 08/03/10/01, Help, glossary, to-do 40 | docs | ~10-15 min (rough guess) | 7 min | 18:02–18:09 |
| 2026-10-11 | B2 LIB: Device Library .gmap only, 13 test files moved | feature | ~10-15 min (rough guess) | 14 min | 18:02–18:16 |
| 2026-10-11 | B2 TEST2: end to end 11 (found 3 program bugs) | agent tests | ~15 min | 15 min | 18:02–18:17 |
| 2026-10-11 | B2 TFIX: 5 old .zip test files moved to .gmap | agent tests | ~10 min | 3 min | 18:15–18:18 |
| 2026-10-11 | B2 PACK: .gmap-only export/import, two targets, Undo for both; 3 bug fixes; 8 test files moved | feature | ~15 min | 21 min | 18:02–18:23 |
| 2026-10-11 | B3 renames (Configuration page -> Device Bindings, Auto Mapper -> Auto Mapping Tool): R-QML1 1 min, R-QML2 3, R-PY1 2, R-PY2 4, R-DOC 4, R-TEST2 8, R-TEST1 10 | refactor | rough guess 10-15 min | 10 min wall | 18:26–18:36 |
| 2026-10-11 | B4 rename Button Map -> Device Mapping Editor (8 agents: E-RIG 1 min, E-SHELL 2, E-OT3 2, E-WIN 4, E-PY 5, E-TEST1 7, E-TEST2 9, E-DOC 9) + OT-4 Library part id move (3 min) | refactor | rough guess 15-20 min | 10 min wall (+3 OT-4) | 18:38–18:48 |
| 2026-10-11 | ONE full run + lint over fix-list batches 1-4 (seed 5299): 3 failures (2 tests still .zip, the store-only guard on OT-4), fixed, 7 pass targeted; lint 0 new; lint wrap 2 agents 1-4 min | test | 5–6 min (table) | 6 min + 2 min fixes | 18:54–19:02 |
| 2026-10-11 | Live test session with the user (lead watching logs, 13-item list, research on wording and history UIs) | lead | — | ~55 min (user's pace) | 19:05–19:58 |
| 2026-10-11 | Test-session list: OT4 1 min, PACKWIN 1, LOOKUP 1, PACKPY 3, HMODEL 5, DOC 5, LIB 6, HUI 9, WIN 9 (9 agents) | fix/feature | 5-10 min (table); History rough guess 15 | 9 min wall | 19:58–20:07 |
| 2026-10-11 | HTFIX: older History tests to the new design (90 pass) | agent tests | ~10 min | 6 min | 20:07–20:13 |
| 2026-10-11 | ONE full run + lint (test-session list, seed 956683): 2 tests pinned old behaviour (folded rows, Help wording) + 5 lint items; fixed, targeted green | test | 5–6 min (table) | 7 min + 4 min fixes | 20:13–20:24 |
| 2026-10-11 | Release 1.0.33 prep: NOTES (release-notes/1.0.33.md) + MAPCHECK (full map check: counts, 43 line counts, stale tags) | docs | ~8-10 min | NOTES ~8, MAPCHECK 6 | 20:24–20:31 |
| 2026-10-11 | Picture handle drift study: other picture tools (PICTOOLS, read-only probes) | research | 5-10 min | 5 min | 20:38-20:43 |
| 2026-10-11 | Web research: editor handle and modifier-key conventions (3 parallel agents RS-RESIZE, RS-XFORM, RS-SHAPE) | research | ~8 min | 2 min each | 20:47-20:49 |
| 2026-10-11 | Photoshop research + code scout (RS-PS, SCOUT, parallel) | research | 5-10 min | 1 min each | 20:53-20:54 |
| 2026-10-11 | Lead: contract, briefs, split for PS-MATCH (21 items) | lead | — | 10 min | 20:56-21:06 |
| 2026-10-11 | PS-MATCH code batch, 9 parallel agents (RESIZE, DRAWITEM, POINTER, GROUP, XFORM, PROPS, DOCS, TESTNEW, SWEEP), no test runs | feature | 3-8 min each, limit 20 | 2-9 min each (all done 21:10) | 21:01-21:10 |
| 2026-10-11 | Targeted tests PS-MATCH (9 files), two runs | test | ~4 min | 1-2 min each | 21:10-21:14 |
| 2026-10-11 | HANG: new test 'freeze' traced (50 s per-program limit), smoke split | fix | 3-8 min | 9 min | 21:14-21:23 |
| 2026-10-11 | CHIPDROP read-only trace | research | 5-10 min | 1 min | 21:18-21:19 |
| 2026-10-11 | CHIPFIX: dropped chip centred (S156), failing test first | fix | 3-8 min | 4 min | 21:21-21:25 |
| 2026-10-11 | Full run 1 (PS-MATCH) | test | 5-6 min | 7 min | 21:25-21:32 (27 failed) |
| 2026-10-11 | CARDPIC read-only trace | research | 5-10 min | 1 min | 21:30-21:31 |
| 2026-10-11 | Lead: fix window hook, wording, colours; reruns | fix | — | 12 min | 21:32-21:44 |
| 2026-10-11 | GOLDEN (10 re-recorded) and PRINT (smoke box) in parallel | fix | 3-8 min each | 5 min / 1 min | 21:44-21:49 |
| 2026-10-11 | BGPIC-PLAN contract + split + spec draft | research | 5-10 min | 6 min | 21:43-21:49 |
| 2026-10-11 | Full run 2 (PS-MATCH final) | test | 5-6 min | 9 min (user's app open; part 6 509 s) | 21:49-21:58 (2 failed, pass alone) |
| 2026-10-11 | BG-COMPOSITE card picture: plan + 8 agents (both waves together) | feature | 3-8 min each | 2-14 min each | 21:43-22:16 |
| 2026-10-11 | Fix agents after full runs (FIXMAKER, FIXRENDER, FIXTESTS, HISTFLAKE x2, RCTRACE x3, CRASH) | fix | 3-8 min each | 2-15 min each | 22:20-23:34 |
| 2026-10-11 | Read-only traces (ZOOMTEXT, RCLICK, RCLICK2, DEVIMG-PLAN) | research | 5-10 min | 1-15 min | 22:01-22:45 |
| 2026-10-11 | Click zone + grid + docs + Mouse trace + input-only (CLICKZONE, GRIDBOX, DOCS2, MOUSETRACE, INPUTONLY) | feature | 3-8 min each | 2-11 min each | 23:01-23:15 |
| 2026-10-11 | Full runs for the batch (5 runs; 4 with failures) | test | 5-6 min | 7 min each | 22:16-23:42 |
| 2026-10-12 | CI crash triage (CICRASH): reproduced 4/4 with CI's order, native cause not found | research | 3-8 min fix + ~7 min run | 42 min (not fixed) | 00:04-00:46 |
| 2026-10-12 | Old-commit reproduction (3515b8cd worktree), 2 runs | test | ~10 min | 10 min | passes 2/2: the crash comes with b4f3ff13 |
| 2026-10-12 | CI crash split + native stack (CICRASH): split runs x2 crashed, debugger caught a timer event to a deleted object | research | 30 min limit | 30 min (not fixed) | 04:37-05:07 |
| 2026-10-12 | Parallel split (SPLIT-P/Z/T, 3 worktrees side by side, 2 runs each) + 2 read-only audits | research | ~10 min | 10 min (all three still crashed) | 05:19-05:30 |
| 2026-10-12 | CICRASH: Qt warning -> GC on History thread -> HardwareProfile cycle; fix + proof 2/2 | fix | 30 min limit | 28 min | 05:07-05:35 |
| 2026-10-12 | OLDCHECK: 3515b8cd 2 runs side by side | test | ~10 min | 6 min (passed 2/2) | 05:32-05:38 |
| 2026-10-12 | PROOF3: fix proof, 3 worktrees side by side | test | ~5 min | 6 min (passed 3/3) | 05:39-05:45 |
| 2026-10-12 | GCGUARD: main-thread GC + test check | fix | 3-8 min | 10 min | 05:39-05:49 |
| 2026-10-12 | Full run with fix + guard | test | 5-6 min | 7 min (3 stall tests failed) | 05:49-05:56 |
| 2026-10-12 | STALLREAD (read-only) + stall_watch fix | fix | 3-8 min | 3 min | 05:58-06:01 |
| 2026-10-12 | Unit rerun (5 groups) + stall proof x3 | test | ~7 min | 9 min + 1 min | 05:57-06:07 |
| 2026-10-12 | Full code map + dead-code audit, 7 parallel agents (EXERCISE instrumented full run 7 min; PY-REFS, QML-REFS, BRIDGE, ASSETS, LEFTOVERS, MAPCHK read-only) | research | 5-10 min each, limit 20 | 5-35 min each (QML-REFS 35) | 06:10-06:45 |
| 2026-10-12 | SPECCHK (read-only, 3 possible missing behaviours) | research | 5-10 min | 1 min | 06:58-06:59 |
| 2026-10-12 | SMALLFIX: liveStamp bug + vjoy/theme guards | fix | 3-8 min | 3 min | 06:58-07:01 |
| 2026-10-12 | A-STORE Device Image store | feature | 3-8 min | 3 min | 06:58-07:01 |
| 2026-10-12 | A-HOME card image slots + undo | feature | 3-8 min | 6 min | 06:58-07:04 |
| 2026-10-12 | XBOX: viewer into the Xbox Output View | feature | 3-8 min | 7 min | 06:58-07:05 |
| 2026-10-12 | LIB: Library thumbnails + rows | feature | 3-8 min | 8 min | 06:58-07:06 |
| 2026-10-12 | DOCS wave 1: spec, glossary, Help | docs | 3-8 min | 8 min | 06:58-07:06 |
| 2026-10-12 | A-PACK: Device image row, Library photo lookup | feature | 3-8 min | 8 min | 06:58-07:06 |
| 2026-10-12 | A-SETUP: Module Setup image, editor save, precedence | feature | 3-8 min | 9 min | 06:58-07:07 |
| 2026-10-12 | HOMEUI: Home image menu, drag look, cards 1080x780 | feature | 3-8 min | 10 min | 06:58-07:08 |
| 2026-10-12 | T-SWEEP: 16 old-rule tests updated | fix | 3-8 min | 9 min | 07:07-07:16 |
| 2026-10-12 | DEVIMG-TESTS: Device Image e2e (12) + carry (10); found the Library thumbnail path bug | test | 3-8 min | 9 min | 07:07-07:16 |
| 2026-10-12 | Wave 1 full run + lint (all passed, 1 line auto-fixed) | full run | ~7 min | 7 min | 07:17-07:24 |
| 2026-10-12 | W2-UI / W2-CORE / W2-QML / W2-ASSETS phase 1 (verify only, 4 in parallel) | audit | no data | 3-4 min each | 07:20-07:24 |
| 2026-10-12 | W2-MAP: program map audit fixes (stale names, line refs, owners, retire 01 S37/09 S68) | docs | rough 15 min | 13 min | 07:20-07:33 |
| 2026-10-12 | W2-CORE: dead core code, close-to-tray, osc_bulk plain functions, macro 0.05, OT-2 markers, bindings-only .gmap test | removal | rough 20 min | 6 min | 07:26-07:32 |
| 2026-10-12 | W2-ASSETS: 145 unused files removed, icon_large to fixtures, WiX path gone | removal | rough 20 min | 8 min | 07:26-07:34 |
| 2026-10-12 | W2-UI: dead UI Python, test-only Slots, dead Options row, put_gmap_wires, osc_bulk wiring | removal | rough 15-20 min | 8 min | 07:26-07:34 |
| 2026-10-12 | W2-QML: 6 dead files, 31 functions, ~30 properties, inline mode, TODO(SEL) fallbacks | removal | rough 20 min | 9 min | 07:26-07:35 |
| 2026-10-12 | DUP-GUID: device_zip.guid_text -> braced_guid (rename, 6 call sites) | merge | rough 10 min | 1 min | 07:37-07:38 |
| 2026-10-12 | DUP-PIC: imageAspect/pictureSize read through store.picture_size, 2 tests | merge | rough 10 min | 1 min | 07:37-07:38 |
| 2026-10-12 | OSC-TEST: test_osc_qml stand-in matched to real Slots + drift check | test | rough 10 min | 2 min | 07:37-07:39 |
| 2026-10-12 | DUP-PATH: 8 same-file/inside checks -> util.path_key/same_path/is_inside, 14 tests | merge | rough 10 min | 3 min | 07:37-07:40 |
| 2026-10-12 | W2-MAP follow-ups: ~70 removal + merge map lines | docs | no data | 5 min | 07:37-07:42 |
| 2026-10-12 | Wave 2 full run (1 fail: test pinned removed scope) + lint (9 new test-line errors fixed) | full run | ~7 min | 7 + 3 min | 07:41-07:52 |
| 2026-10-12 | XO-TREE: ControlTree readOnly/showGroups/ownScroll/listHeight, ControlFindBar showUndo/showCantSend, 1 test file | feature | 3-8 min | 3 min | 08:04-08:07 |
| 2026-10-12 | XO-DOCS: D-XBOX-LIST spec (03 S140 new, S117, S139; 05 S121, S125; 08 S75), glossary, Help, map | docs | 3-8 min | 3 min | 08:04-08:07 |
| 2026-10-12 | XO-MODEL: XboxOutputListModel (rows, filters, live), incoming_list shared, 10 tests | feature | 3-8 min | 4 min | 08:04-08:08 |
| 2026-10-12 | OPACITY-FIX: Binding-on-value -> plain value, drag test (failed old, passes new) | fix | 3-8 min | 2 min | 08:06-08:08 |
| 2026-10-12 | XO-PAGE: XboxDevice.qml on ControlFindBar + ControlTree + PageAppearance, 3 test files | feature | 3-8 min | 4 min | 08:04-08:08 |
| 2026-10-12 | XO-E2E: Xbox list end-to-end (6 checks, 8 tests, real program off-screen) | test | 3-8 min | 4 min | 08:04-08:08 |
| 2026-10-12 | XO-CLEAN: XboxDeviceModel removed, 3 tests moved to the new model | removal | 3-8 min | 1 min | 08:08-08:09 |
| 2026-10-12 | TIP-TRACE: chip tooltip offset at zoom measured (cause: screen offsets scaled by zoom) | research | 5-10 min | 2 min | 08:08-08:10 |
| 2026-10-12 | TIP-FIX: tooltip offsets / zoom, 4-test smoke (failed old at 4x/8x, passes new) | fix | 3-8 min | 1 min | 08:10-08:11 |
| 2026-10-12 | CI on c52f7205 (waves 1+2) | ci | ~21 min | 23 min | 07:52-08:15 |
| 2026-10-12 | Full run Xbox list batch + lint: 1 load flake (double-tap, passes 3/3 alone), 15 new lint/type errors | full run | ~7 min | 7 min | 08:09-08:16 |
| 2026-10-12 | LINT-FIX: 15 new lint/type items in the Xbox list files | fix | 3-8 min | 2 min | 08:16-08:18 |
| 2026-10-12 | XS-PADS: pad modules, count, send gate, cant-send text, bindings list, 6 tests | feature | 3-8 min | 4 min | 08:31-08:35 |
| 2026-10-12 | XS-MAP: Map to Xbox pad list = pads on + own, refresh on xboxPadsChanged, 3 tests | feature | 3-8 min | 5 min | 08:31-08:36 |
| 2026-10-12 | XS-PADS follow-up: wiring pad label, Library/Pack check | fix | ~5 min | 1 min | 08:35-08:36 |
| 2026-10-12 | XS-SETUP: Xbox Setup window + model, card menu, palette, Output View link, 6 tests | feature | 3-8 min | 6 min | 08:31-08:37 |
| 2026-10-12 | XS-DOCS: D-XBOX-PADS spec (03 S39 S88 S115 S139 S140 S141-145, 05 S137 S141, 06 S58 S64 S98 S99), glossary, Help, map | docs | 3-8 min | 5 min | 08:32-08:37 |
| 2026-10-12 | CI on 03e02cd7 (Xbox list) | ci | ~23 min | 18 min | 08:19-08:37 |
| 2026-10-12 | XS-VIEW: per-pad sections, XboxPadCard, pad chips/live models, old viewer removed, 15-test smoke | feature | 3-8 min | 11 min | 08:31-08:42 |
| 2026-10-12 | XS-E2E: Xbox pads end-to-end (13 tests, two runs, real Setup window) | test | 3-8 min | 10 min | 08:32-08:42 |
| 2026-10-12 | Lead: rerun 5 Main.qml-dependent files (90 passed) | test | ~2 min | 1 min | 08:43-08:43 |
| 2026-10-12 | Full run Xbox pads batch + lint: 1 load failure (module setup photo, passes 2/2 alone, to-do 122), no new lint | full run | ~7 min | 7 min | 08:44-08:51 |
| 2026-10-12 | COMPACT-THUMB: compact card 40x40 thumb + big picture not decoded, 1 test | feature | 3-8 min | 2 min | 08:53-08:55 |
| 2026-10-12 | DOCS-B: D-07-RESET-PICTURE (07 S161), D-03-COMPACT-THUMB (03 S73), D-XBOX-PADS-LOOK (03 S139 S140), glossary, Help | docs | 3-8 min | 4 min | 08:53-08:57 |
| 2026-10-12 | PAD-HEADER: pad header Group look, framed sections, spacing, tick renamed + remembered, 68 tests | feature | 3-8 min | 6 min | 08:53-08:59 |
| 2026-10-12 | DOCS-B follow-up: D-03-HOME-BAND (03 S136 S146-S148, 01 S58a), glossary, Help | docs | ~3 min | 1 min | 08:58-08:59 |
| 2026-10-12 | PAD-HEADER follow-up: ControlFindBar filter checked key, children walk removed, 95 tests | fix | ~5 min | 1 min | 08:58-08:59 |
| 2026-10-12 | BINDSWEEP: 22 assigned ({})/([]) properties fixed in 13 files, guard test (failed old, passes new) | fix | 3-8 min | 10 min | 08:53-09:03 |
| 2026-10-12 | HOME-BAND: Undo bar removed, empty-menu Undo, bar spacing, rubber band, Hide/Reset Size of Selected, 7+12 tests | feature | 6-16 min | 8 min | 08:58-09:06 |
| 2026-10-12 | PICRESET: Reset Picture (menu, Arrange, Properties), freshPictureSize, 6 binding props, goldens, 9 tests | feature | 3-8 min | 15 min | 08:53-09:08 |
| 2026-10-12 | HOME-BAND follow-up: precise Undo of Hide Selected, 4 dead props removed | fix | 3-8 min | 3 min | 09:08-09:11 |
| 2026-10-12 | CI on 273c2bd9 (Xbox pads) | ci | ~20 min | see run | 08:52-09:16 |
| 2026-10-12 | Full run batch B + lint: 2 OSC timing flakes (pass 2/2 alone, to-do 125), no new lint | full run | ~7 min | 8 min | 09:11-09:19 |
| 2026-10-12 | CI repro: History alone 3/3 pass; CI seed 3-part rerun stopped by the 10-min part cap (History tests passed in it) | research | 5-8 min | 10 min | 09:20-09:30 |
| 2026-10-12 | C-VJTABS: 113 checked (not a gap), found 127 | research | 3-8 min | 1 min | 09:30-09:31 |
| 2026-10-12 | C-DOCS part 1: CLAUDE.md 3 rules, page 09 OSC edit path, 127 gap | docs | 3-8 min | 1 min | 09:31-09:32 |
| 2026-10-12 | C-OSCDEAD: dead OSC edit path removed, 2 test files moved to applySettings, 66 tests | removal | 3-8 min | 7 min | 09:30-09:37 |
| 2026-10-12 | C-PHOTORACE: traced (not a race), test waits for the maker, 10/10 incl. 8 under load | research+test | 5-10 + 3-8 min | 7 min | 09:30-09:37 |
| 2026-10-12 | C-DTAP: virtual timers for Tempo/Double Tap/Smart Toggle tests, OSC release tests wait on result; stall proof | fix | 3-8 min | 13 min | 09:30-09:43 |
| 2026-10-12 | Lead LOAD TEST: 4 copies of the 3 timer-test files: 4x (73+4) passed | test | ~2-3 min | 1 min | 09:44-09:45 |
| 2026-10-12 | C-TABROW: device tab row, DeviceTabBar/JGTabButton, vjoy_status.py removed; startup test handle bug fixed | removal | 3-8 min | 11 min | 09:39-09:50 |
| 2026-10-12 | C-ALIAS: DeviceNames.setAlias removed, 3 tests moved | removal | 3-8 min | 1 min | 09:51-09:52 |
| 2026-10-12 | C-DOCS: CLAUDE.md 3 rules, map lines for all batch C agents | docs | 3-8 min | 21 min (waiting on agents) | 09:31-09:52 |
| 2026-10-12 | Quick tests batch C (--changed: 3,755 tests, 6 parts) + lint: all passed, no new errors | test | 2-3 min | 6 min | 09:53-09:59 |
| 2026-10-12 | OSC-NAME: Main.qml oscFullName line + 4-test smoke | feature | 3-8 min | 2 min | 10:04-10:06 |
| 2026-10-12 | OSC-E2E: card line end-to-end (8 tests, real program, loopback) | test | 3-8 min | 3 min | 10:04-10:07 |
| 2026-10-12 | OSC-CARD: OscCardStatus + StatusCard OSC line/tooltip, 9+1 tests | feature | 3-8 min | 3 min | 10:04-10:07 |
| 2026-10-12 | DOCS-D: D-09-OSC-CARD-LINE, 09 S175-S177, 03 S73, glossary, Help topic osc-card-line, map | docs | 3-8 min | 3 min | 10:04-10:07 |
| 2026-10-12 | OSC-CORE: listenInfo + bind reasons + saved-settings closed state, 10 tests | feature | 3-8 min | 6 min | 10:04-10:10 |
| 2026-10-12 | OSC-CARD follow-up: StatusCard declares OscCardStatus (Instantiator), 2 harnesses register it | fix | ~5 min | 2 min | 10:08-10:10 |
| 2026-10-12 | DOCS-V: D-03-VJOY-VIEWER-QUICK, 03 S122, gap 33 reopened, glossary, Help | docs | 3-8 min | 1 min | 10:10-10:11 |
| 2026-10-12 | VJV-FIX: viewer cards without module file, pair_live refresh, empty text, chips fit | fix | 3-8 min | 5 min | 10:10-10:15 |
| 2026-10-12 | Quick tests OSC+viewer batch (--changed: 4,427 tests) + lint: all passed | test | ~6 min | 7 min | 10:16-10:23 |
| 2026-10-12 | E2: count line hidden on Keyboard/OSC/Logical cards, 1 test | fix | 3-8 min | 1 min | 10:24-10:25 |
| 2026-10-12 | E3: Output View 'View only' line removed, Help reworded, 1 test | fix | 3-8 min | 2 min | 10:24-10:26 |
| 2026-10-12 | E1: OSC Setup address list refresh (activation + 5 s), 5 tests | feature | 3-8 min | 2 min | 10:24-10:26 |
| 2026-10-12 | Quick tests batch E (--changed: 2,698 tests) + lint: 1 order flake (to-do 47 setting, passes 2/2 alone), no new lint | test | ~6 min | 5 min | 10:27-10:32 |
| 2026-10-12 | F-DOCS: D-05-ROW-ACTION-SUMMARY, 05 S142 + S125, glossary, Help | docs | 3-8 min | 2 min | 10:33-10:35 |
| 2026-10-12 | F-LEAK: OSC trace tick leak + s44 settings leak fixed in tests | fix | 5-10 min | 3 min | 10:33-10:36 |
| 2026-10-12 | F-SUMMARY: actionSummary role + ControlTree line + Appearance switch on 4 pages, 7 tests | feature | 8-12 min | 5 min | 10:33-10:38 |
| 2026-10-12 | Quick tests batch F (--changed: 3,460 tests) + lint: all passed | test | ~6 min | 6 min | 10:39-10:45 |
| 2026-10-12 | G-HIST: History test keeps full smoke output on failure | test | 3-8 min | 2 min | 10:54-10:56 |
| 2026-10-12 | G-KEY: GL-254 already fixed; guard test added | test | 8-12 min | 2 min | 10:54-10:56 |
| 2026-10-12 | G-RENAME: renamed stick keeps card size + stack, 2 tests | fix | 3-8 min | 3 min | 10:54-10:57 |
| 2026-10-12 | G-RAW: Calibration Raw box read-only, 1 test | fix | 3-8 min | 1 min | 10:55-10:56 |
| 2026-10-12 | G-GUARD: conftest guards the app's configChanged watchdog listener, 1 test | test | 3-8 min | 2 min | 10:54-10:56 |
| 2026-10-12 | G-LOAD: 128 cause found (stall watch injects into main thread inside QML load), repro without load 4/4 | research | 10-15 min | 8 min | 10:50-10:58 |
| 2026-10-12 | G-LIB: Library always lists Keyboard/OSC/Logical Device with empty line, Save greyed; 3 tests + 7 updated | feature | 8-12 min | 5 min | 10:55-11:00 |
| 2026-10-12 | G-SWAP: Swap autosave long path (short autosave file name + extended-length temp file), 2 tests | fix | 5-10 min | 8 min | 10:55-11:03 |
| 2026-10-12 | G-DOCS: batch G spec (10 S6), decisions, glossary, Help, map lines for 7 agents | docs | 3-8 min | 8 min | 10:55-11:03 |
| 2026-10-12 | CI on 46820406 (batch F): passed | ci | ~20 min | 23 min | 10:46-11:09 |
| 2026-10-12 | Input Tester toolbar button (lead: Main.qml, tests, spec, Help) | feature | 3-8 min | ~6 min | 11:11-11:17, 47+23 tests passed |
| 2026-10-12 | vJoy Viewer OSC trace (V-PATH, read-only) | review | 5-10 min | 1 min | 11:14-11:15 |
| 2026-10-12 | vJoy Viewer OSC chip name (V-NAME, read-only) | review | 5-10 min | 1 min | 11:14-11:15 |
| 2026-10-12 | 128 harness fix: start-up stall handling (H-STALL) | fix | 3-8 min | 5 min | 11:12-11:17 |
| 2026-10-12 | Bindings boxes: spec, glossary, Help (B-DOCS) | docs | 3-8 min | 2 min | 12:58-13:00 |
| 2026-10-12 | Bindings boxes: Appearance section + pages (B-APPEAR) | feature | 3-8 min | 5 min | 12:58-13:03 |
| 2026-10-12 | Bindings boxes: row display + roles (B-ROW) | feature | 3-8 min | 8 min | 12:58-13:06 |
| 2026-10-12 | Bindings boxes: end-to-end test (B-E2E) | test | 3-8 min | 9 min (incl. waiting) | 12:58-13:07 |
| 2026-10-12 | Quick tests batch I (--changed, 3,673 tests) + baseline | test | ~7 min | 7 min | 13:07-13:14 |
| 2026-10-12 | Appearance per device: storage (S-STORE) | feature | 3-8 min | 1 min | 13:37-13:38 |
| 2026-10-12 | Appearance per device: spec, glossary, Help (S-DOCS) | docs | 3-8 min | 1 min | 13:37-13:38 |
| 2026-10-12 | Appearance per device: panel + page (S-PANEL) | feature | 3-8 min | 4 min | 13:37-13:41 |
| 2026-10-12 | Appearance per device: end-to-end test (S-E2E) | test | 3-8 min | 5 min (incl. waiting) | 13:37-13:42 |
| 2026-10-12 | Quick tests batch J (--changed, 3,151 tests; 2 source tests updated) | test | ~7 min | 5 min + 1 | 13:42-13:48 |
| 2026-10-12 | Copy from device: spec, glossary, Help (C-DOCS) | docs | 3-8 min | 1 min | 14:31-14:32 |
| 2026-10-12 | Copy from device: panel + page (C-PANEL) | feature | 3-8 min | 5 min | 14:31-14:36 |
| 2026-10-12 | Copy from device: end-to-end test (C-E2E) | test | 3-8 min | 13 min (incl. waiting) | 14:31-14:44 |
| 2026-10-12 | Quick tests batch K + themed-menu fix (lead) | test/fix | ~7 min | 5 + 4 min | 14:45-14:59 |
| 2026-10-12 | Details: phrase renames (L-RENAME) | fix | 3-8 min | 2 min | 14:53-14:55 |
| 2026-10-12 | Details: drawing (L-TREE) | feature | 3-8 min | 5 min | 14:53-14:58 |
| 2026-10-12 | Details: Appearance sections + pages (L-APPEAR) | feature | 3-8 min | 5 min | 14:53-14:58 |
| 2026-10-12 | Details: spec, glossary, Help charts (L-DOCS) | docs | 3-8 min | 5 min | 14:53-14:58 |
| 2026-10-12 | Details: model roles (L-MODEL) | feature | 3-8 min | 6 min | 14:52-14:58 |
| 2026-10-12 | Details: e2e test written (L-E2E) + lead fixes (type order, pad name, key words) | test/fix | 3-8 min | ~10 min | 14:53-15:04 |
| 2026-10-12 | Quick tests batch L (--changed 3,975) + rule tests (35) in parallel | test | ~7 min | 8 min | 15:03-15:11 |
