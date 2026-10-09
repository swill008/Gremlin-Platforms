# How long things take (user 2026-10-09)

Measured times, so estimates match reality. Add a row when a step finishes:
start and end from the clock, not a guess. Use the medians here when quoting
a time to the user.

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
