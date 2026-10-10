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
| 2026-10-09 | OSC: carry-through tests (OSC-carry) | test | ~15 min | 2 min | 14:52–14:54 |
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
