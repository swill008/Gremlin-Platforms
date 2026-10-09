# How long things take (user 2026-10-09)

Measured times, so estimates match reality. Add a row when a step finishes:
start and end from the clock, not a guess. Use the medians here when quoting
a time to the user.

| Date | Task | Kind | Estimated | Took | Notes |
|---|---|---|---|---|---|
| 2026-10-09 | Full run `run_tests.py --random-order` + lint | test | ~5 min | 6 min | 6 parts ~4 min, lint ~1.5 min; part 6 stalled once under load (to-do 47) |
| 2026-10-09 | Fix 2 small test failures (colour tokens, Help loader) | fix | 5 min | ~4 min | lead alone |
| 2026-10-09 | One Button Map window smoke (`flows`) alone | test | — | 7 s | 34 s+ under full-run load |
