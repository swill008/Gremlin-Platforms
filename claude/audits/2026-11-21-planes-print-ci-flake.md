# test_planes_print.py fails now and then in CI (2026-11-21, agent STUDY)

Question: why does `test/unit/test_planes_print.py` fail in continuous
integration (CI) on commits that don't touch printing (5200a6f9, 5dd1e046)
and pass on others (767c0ff9)?

## Conclusion

**VERIFIED: the program copies are ended by the 50-second run-time limit
that the hang trace puts on every program a test starts, not by a loop.**

- `test/conftest.py:88` sets `GREMLIN_TEST_HANG_LIMIT=50`.
  `test/hang_trace/sitecustomize.py` starts a `StallWatch` with
  `limit=50` in each program the tests start; once the program has run
  50 s, `stall_watch.py` `_check` reports "It is still running after the
  limit (50 s)" and `_stalled` ends the process (`end_process(3)`) before
  it prints its `RESULT` line.
- The test then fails at `test_planes_print.py:69` (`assert lines`: no
  RESULT line), well before its own 150 s wait (`test_planes_print.py:61`)
  and while the 60 s export wait in `planes_print_smoke.py:247` would
  still be running. The 150 s and 60 s figures can never be reached.
- The fixture's setup time (all three copies, started together) is the
  copies' run time. Every failure is just over 50 s; every pass is under
  it, two of them within 3 s of it.
- The stack in each stall report is only where the main thread happened
  to be when the 50 s ran out. It differs in each failure (a file read, an
  event filter, the can't-be-sent notice, a settings save), and in 5dd1e046
  the copy had already finished its last export and was closing. A real
  loop would show the same place each time.

The program-side code path the brief asked about (output.py's
can't-be-sent notice) shows no loop: see "The can't-be-sent path" below.

## Evidence: CI runs

Setup time of the `runs` fixture (from pytest's "slowest durations"),
GitHub Actions, repo swill008/Gremlin-Platforms:

| Run | Commit | Result of test_planes_print | Fixture setup |
|---|---|---|---|
| 44899297301 | 5dd1e046 | ERROR (all 8), dense copy ended | 50.75 s |
| 44896454347 | 767c0ff9 | passed | 32.23 s |
| 44893707237 | 61cfa426 | passed (run failed elsewhere) | 47.58 s |
| 44890170211 | 430a0f82 | passed (run failed elsewhere) | 49.23 s |
| 44833437818 | 5200a6f9 | ERROR (all 8), plain copy ended | 54.03 s |
| 44790071566 | 93a0ff78 | passed | 21.21 s |
| 44784713580 | 704b3c3a | FAILED 2 (older cause, below) | 41.46 s |
| 44775704289 | 45142de1 | ERROR (all 8), plain copy ended | 50.98 s |
| 44771101591 | 3ecba75d | ERROR (all 8), plain copy ended | 57.21 s |
| 44756900498 | 74f9692e | passed | 23.47 s |
| 44741501406 | c8eaf42d | FAILED 2 (older cause, below) | not listed |

Where the ended copy's main thread was (the stall report's last stack, CI
line numbers of that commit):

| Run | Copy | Main thread in | Smoke step |
|---|---|---|---|
| 44771101591 | plain | `gremlin/modules/store.py:302 _read_json` (from `module_model._refresh_inplace`) | export at `planes_print_smoke.py:298` (no-bg) |
| 44775704289 | plain | `gremlin/ui/leave_text.py:128 eventFilter` | export at line 288 (bg-hidden-view) |
| 44833437818 | plain | `gremlin/modules/output.py:170 _send_cant_send` | export at line 300 (no-bg) |
| 44899297301 | dense | `gremlin/config.py:349 save_now` (from `deferred_write.flush`) | line 271: the `qWait(300)` after closing, all exports done |

The report's first lines (the headline) are cut off in the CI log because
the test shows only the last 1500 characters of the copy's output
(`test_planes_print.py:69`). The headline wording "It is still running
after the limit (N s)" is VERIFIED from another run's journeys report
(44741501406, log lines 1769-1770, limit 100 s there); for the planes
copies it is VERIFIED by the timings and the 50 s limit, not read directly.

Older failures (44741501406, 44784713580): `{'missing': True}` and
`KeyError: 'box'`: the export file wasn't there when the then 10 s export
wait ended. 93a0ff78 raised that wait to 60 s (the comment at
`planes_print_smoke.py:245-247`). VERIFIED. Since then a slow copy runs
into the 50 s program limit instead.

The plain copy (six exports) is the one ended in three of four failures;
it is the longest of the three.

## Local run

`pytest -v test/unit/test_planes_print.py`, temp USERPROFILE, this PC,
2026-11-21 07:15: 8 passed, fixture setup 7.71 s, 9 s wall. VERIFIED. CI
is 3 to 7 times slower for this fixture (21-57 s), with three Qt programs
started at once while `test/run_tests.py` runs its other parts in
parallel on the same runner. That the runner's core count is the reason
is UNVERIFIED (the runner's size was not read).

## The can't-be-sent path (output.py)

- `_CantSendNotice` (`gremlin/modules/output.py:113-156`): a single-shot
  0 ms `QTimer`; `_ask` restarts it; `_send` calls `_send_cant_send`,
  which drops the claim cache and emits `signal.cantSendChanged` once.
  It listens to configChanged, profileChanged, the OSC and Logical Device
  signals and the device-change event (`listen`, lines 131-147).
- The three `cantSendChanged` handlers: `control_layout._on_cant_send`
  (rebuilds the layout, line 607), `module_model._follow_cant_send`
  (re-marks rows, emits dataChanged and its own model signal, lines
  2005-2020), `output_modules._update_choices` (rebuilds choices, line 108).
  None of them emits one of the signals the notice listens to, so a
  handler cannot restart the timer. VERIFIED from code (one level deep;
  their callees were not traced further).
- The run that showed `_send_cant_send` (44833437818) had the main thread
  in a different place in each other failure. A self-feeding loop would
  also keep the copy busy past 150 s in passing runs; passing runs finish
  in 21-49 s. So no loop: VERIFIED from logs and code.
- Why the notice fires during an export at all (the export saves the
  print area; a save leads to `output.refresh()` -> `notify_cant_send`) is
  UNVERIFIED (not traced); it is ordinary work, not a stall.

## Options to fix (efforts are guesses: timings.md has no row for this kind)

1. Give this test's copies a longer limit, as the journeys do
   (`test/journeys/_harness.py:86-87`): `_start` sets
   `GREMLIN_TEST_HANG_LIMIT` to e.g. 140 (under the test's 150 s wait) in
   the copy's environment. Smallest change; the stall checks (10 s blocked,
   30 s idle) still catch real hangs. Rough guess 5-10 min with tests.
2. Split the plain copy's work into two copies, as `test_ps_match.py:30-38`
   did for the same 50 s limit ("all of them in one take about 70 s").
   Each part stays under 50 s on CI, but a fourth Qt program at once makes
   each one slower again. Rough guess 15-25 min.
3. Start the copies one after another instead of three at once. Each runs
   faster, but the fixture takes longer in total and each copy still has
   to stay under 50 s. Rough guess 5 min; weakest of the three.
4. In any case: show the head of the copy's output too
   (`test_planes_print.py:69` shows only the last 1500 characters, which
   cut off the stall headline that names the cause). Rough guess 2-5 min.

Recommendation: 1 with 4 (the limit matches the test's own wait and the
report names the cause next time).
