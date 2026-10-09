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
