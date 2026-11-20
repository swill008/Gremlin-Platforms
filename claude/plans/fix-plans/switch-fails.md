# sys.setswitchinterval(0.0005): why four tests fail (SWITCH-FAILS, 2026-11-19)

Method: ON/OFF without editing the program. Scratch plugin outside the repo (`PYTEST_PLUGINS=swplug`,
a `sitecustomize.py` first on PYTHONPATH) turns `sys.setswitchinterval(0.0005)` into a no-op (OFF)
or substitutes another value (`SW_VAL`), in the pytest process and in the programs the tests start.
Scratch files: C:/Users/Stacie/AppData/Local/Temp/claude/906eff5ad66bc77c/f29f32c5-d945-4e62-b89f-3680504a29c8/scratchpad/ (sw/, harness3.py, driven_by_copy.py, t/test_trace_copy.py).
Machine quiet apart from SWITCH-SLOW's queued runs.

## 1. test_driven_by_follows_edits.py (8 ERRORs) - PROGRAM-SIDE (verified), not load
- Fails on a quiet PC with the setting ON: 3 of 3 runs, `subprocess.TimeoutExpired ... timed out after 120 seconds`
  in the module fixture (test_driven_by_follows_edits.py `run`, proc_tree.run). OFF: 8 passed in 2.2 s, 2 of 2.
- The child prints its `RESULT {...}` line correctly after ~1.5 s (output identical to OFF), then
  `os._exit(0)` never finishes: the process stays alive for 40 s+ (1 thread left, state Wait, CPU frozen),
  so the stdout pipe never closes and communicate() times out. faulthandler (30 s) wrote nothing:
  the hang is below Python, inside process exit.
- Reproduced without pytest (Popen, with and without the Job Object), so it is not the test harness.
- Depends on the interval value: 0.0005 hangs (6 of 6), 0.001 / 0.002 / 0.004 exit instantly (3 of 3 for 0.001), OFF exits.
- Not the input thread: with `gremlin.input_thread.start` stubbed out and only the interval set, it still hangs (2 of 2).
- Depends on the script's late part: the same script cut before the final "user's name"
  step (set_alias / deviceNamesChanged / setCurrentDevice) exits fine at 0.0005 (4 cuts, 1 run each).
- Restoring the interval to 0.005 just before `os._exit` does not help (so it is not the interval at the instant of exit).
- Cause inside the exit (which lock/DLL) is UNVERIFIED: no native debugger on the PC.
- Why it matters: the real program ends with `os._exit(0)` too (joystick_gremlin.py lines 1424, 1464). I did NOT
  test the real Quit path, so whether Gremlin itself can hang on exit at 0.5 ms is unverified, but
  this is the same call in the same kind of app state.

## 2. test_trace_osc_e2e.py::test_a_new_run_starts_the_counts_again - fails with setting ON, no load needed (cause UNVERIFIED)
- Traceback: `assert len(lines) == 1, lines` -> `AssertionError: []` (test_trace_osc_e2e.py:598).
  Fail rate ON: 1 pass then 1 fail (first run), 1 fail of 1 (3-file run), 2 of 3 (copy runs). OFF: 0 fails in 4.
- The test's own wait (`_wait_line`, 5 s) swallows its TimeoutError: after the second Run the BLOCKED
  "no target named" line for /refuse never appears; `rerun-lines` holds only "clients closed (1)" (written
  after `rerun_start` is taken). The first Run's identical refusal (15 times) is traced fine in the same process.
- Ruled out: the message being sent before the new Run is ready (added a 1.5 s wait before the send in a
  scratch copy: still failed 2 of 3); trace buffer cap (len was 83 of 5000).
- Not decided: test-side (index based `lines()[since:]`, fixed 5 s wait) versus a real program ordering
  difference (the second Run's refusal not traced). It is reproducible and timing-dependent on the interval,
  so treat it as possibly program-side until traced. Next step: print `trace.lines()` after the wait in the
  scratch copy to see whether a refusal line exists at a lower index (the "clients closed" line
  landing after `rerun_start` suggests the stop/run ordering moved).

## 3. test_osc_batch2_e2e / test_osc_batch3_e2e (two tests) - passed with ON
- test_an_exact_input_takes_its_address_from_the_pattern, test_a_sender_on_the_allow_list_fires and the rest of
  both files: 4 + 2 + 2 + 2 + 1 passed with ON on a quiet PC. Earlier failures were only in a busy run.
  Cause: load (fixed waits missed under contention), TEST-SIDE, unverified in detail (not reproduced).

## What it means for keeping the setting
- Not safe to keep as is: with 0.0005 s a test program's `os._exit` hangs deterministically (item 1) and one
  OSC journey fails reproducibly (item 2). Before keeping it, the exit hang must be explained on the real Quit path.
- 0.001 s did not hang in the same repro (3 of 3) but halves the latency tail only partly per switch-interval.md
  (p99 9 ms vs 0.27 ms at 0.5 ms). It is an option if 0.0005 can't be made safe; I did not run the OSC tests at 0.001.
- test_switch_interval.py only pins the value; it does not catch these.

## 4. Cause found (2026-11-20, agent OSCSW, 04:20-04:28) - item 2 is TEST-SIDE, fixed in the test
- Cause: the test's `_stop()` / `_run()` helpers read `runner.is_running()` right after queueing a command.
  Run and Stop are commands queued to the input thread (01 S95, Backend.activate_gremlin), and the
  OSC port close/open is then queued to the main thread (OscRuntime.stop -> `_stop_here`, start -> `_start_here`).
  `_stop()` only pumped events 3 times (settle), so the Stop was often still pending when `_run()` ran.
- Evidence (instrumented scratch copy, setting ON, 4 runs):
  - Failing run: `is_running()` before `_run()` = True (the Stop not yet done), so `_run()` did NOT press Run;
    it took the OLD listener's port (64885), then the queued Stop closed it ("Stop: 0 held inputs released",
    "clients closed (1)", "port closed" all after `rerun_start`). The /refuse that did reach a port was
    traced as Inputs BLOCKED "OSC Button 3: not running (no event)": no Run, so no Send OSC, so no
    "no target named" line. Port after the wait (61731) differed from the client's port.
  - Two more failing runs: no listener at all after the wait (no Run was started).
  - Passing run: `is_running()` before = False (Stop finished), Run pressed, same port before/after.
  - This also explains why a 1.5 s wait before the send didn't help: the Run was never started.
- Why 0.5 ms changes it: with a shorter switch interval the main thread gets back sooner after queueing the
  Stop, so it checks `is_running()` before the input thread has done the Stop.
- Not a program bug: the program's own Run/Stop path uses `_wanted_active` (not `is_running()`), keeps
  commands in order on the input thread, and the main-thread port close is queued before the next Run's open.
- Fix (test/unit/test_trace_osc_e2e.py only): `_run()` calls `activate_gremlin(True)` and waits with
  `j.await_run(True)` before taking the listener; `_stop()` calls `activate_gremlin(False)`, waits with
  `j.await_run(False)` and until `OscRuntime()._listener is None` (port closed). Both raise on timeout.
  It still catches the behaviour tested: a second Run whose refusal is not traced, or traced as "repeated",
  still fails `test_a_new_run_starts_the_counts_again`.
- Runs: fixed file, 0.5 ms (program as is): 6 of 6 passed (13 passed each, 7.5 s). Fixed file, 5 ms (SW_OFF=1
  plugin): 3 of 3 passed. Old file (HEAD copy), 0.5 ms: 2 of 3 failed. ruff and pyright clean.
- Item 1 (os._exit hang at 0.0005) is NOT affected by this and is still open.
