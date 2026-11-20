# Why test_main_window_fits slows down with the 0.5 ms switch interval (SWITCH-SLOW, 2026-11-19)

Question: with the uncommitted `sys.setswitchinterval(0.0005)` in
`joystick_gremlin._start_input_thread()`,
`test/unit/test_main_window_fits.py::test_captions_hide_before_anything_goes_off_the_window`
fails and the file takes ~124 s instead of ~3 s. Why?

## Answer: it is a hang at process exit, not a slowdown

The test's child program (the `_CODE` script, run with `proc_tree.run(..., timeout=120)`)
does all its work in ~2 s and prints `RESULT`, then **hangs forever inside `os._exit(0)`**.
The test fails on the 120 s timeout. The other three tests in the file pass (2.3 s each),
so the file is ~124 s.

### Cause (verified by a native stack of the hung process)

Native stack of the only thread left in a hung child (external dump with dbghelp
StackWalk64; names are the nearest exported symbol, so approximate inside each DLL):

```
os._exit -> ucrtbase exit -> RtlExitUserProcess -> LdrShutdownProcess   (all other threads already killed)
 -> Qt6Core DLL unload: a global static's destructor -> ~QObject (qoffscreen plugin object)
 -> QObjectPrivate::setParent_helper -> QCoreApplication::notifyInternal2 (ChildRemoved event)
 -> PySide QtWidgets wrapper -> QApplication::notify -> sendThroughApplicationEventFilters
 -> PySide QtCore -> PyObject_Call -> _PyEval_EvalFrameDefault (a Python application event filter)
 -> _Py_HandlePending -> SleepConditionVariableSRW   <- waits forever
```

1. `os._exit` -> `ExitProcess` first terminates every other thread, then unloads the DLLs.
2. While the QApplication still exists, Qt's DLL-unload clean-up deletes a QObject; the
   ChildRemoved event goes through `QApplication::notify` and into our **Python
   application event filters** (installed with `app.installEventFilter`:
   `gremlin/ui/leave_text.py:187`, `gremlin/ui/window_titles.py:62`,
   `gremlin/ui/device_map_options.py:852`), so Python code runs during process exit.
3. That Python code finds a pending "drop the GIL" request (`_Py_HandlePending`). Another
   thread (input thread, event listener, History, stall-watch, hang-trace) had asked for the
   GIL while the main thread held it inside `os._exit`; it asks after waiting one switch
   interval. The main thread drops the GIL and, by CPython's forced switching, waits until
   the requesting thread has taken it. That thread was killed in step 1, so the wait never
   ends. (The forced-switch wait is CPython's `drop_gil` behaviour in `ceval_gil.c`; read
   from the stack shape and CPython's design, **not stepped through with symbols** here.)
4. Why 0.5 ms makes it likely: the request is set only after a waiting thread has waited one
   interval. With 5 ms the main thread usually reaches `ExitProcess` before any request is
   set; with 0.5 ms one is almost always set.

## Numbers (fresh temp USERPROFILE, off-screen, PYTHONPATH=test/hang_trace, limit 50)

| experiment | runs | hung at exit | notes |
|---|---|---|---|
| pytest `test_main_window_fits.py`, 0.5 ms (uncommitted code) | 1 | 1 | 120.01 s timeout; other 3 tests 2.28 s |
| exact `_CODE`, 0.5 ms | 5 | 4 | the run that ended took 2 s |
| exact `_CODE`, 0.5 ms (second batch) | 6 | 6 | |
| exact `_CODE`, 5 ms | 5 | 0 | 2-3 s each |
| `_CODE` + thread listing and prints before `os._exit` (A), 0.5 ms / 5 ms | 8 / 8 | 0 / 0 | the extra work changes the timing; shows the hang is a race at exit |
| as above + `setswitchinterval(0.005)` / input thread stop / `threads.shutdown()` before exit | 1 each | 0 | single runs, timing-changed script: **not conclusive** |
| **the program's own quit order**: `gremlin.threads.shutdown()` + `joystick_gremlin.release_qt(app)` then `os._exit` (E), 0.5 ms | 6 | **0** | 2-3 s each |
| `release_qt(app)` only, threads still running (F), 0.5 ms | 6 | 0 | but every run ended with exit code 127 and no output: **not investigated** |
| Main-thread work itself (setProperty width + qWait 300 ms), 0.5 vs 5 ms | 1 / 1 | - | identical: 0.30 s per step, main CPU 0.02 s. No measurable slowdown, no spinning thread |

Threads alive at exit in the test child: MainThread, hang-trace (daemon), stall-watch
(daemon), input thread (daemon), event listener, History (History only with a fresh home).
13 OS threads. No thread was found busy-polling; the GIL contention is not CPU starvation.

## Does the real program have this?

- Normal quit (`main()` after `app.exec()`): stops the program threads, then `release_qt`
  (`app.shutdown()` deletes the QApplication, so no Python filter runs at DLL unload), then
  `os._exit(0)`. Measured: 0/6 hangs (experiment E). **Safe as measured.**
- Paths that call `os._exit` while Qt and threads may still be alive, **same risk, not
  measured**: `_release_timed_out` (the quit-guard timer when Qt clean-up takes over 3 s,
  joystick_gremlin.py:1464; it runs on its own thread while the main thread is busy, so a
  GIL request is likely), and `os._exit(1)` at joystick_gremlin.py:1343 and :1363.
  A hang there would leave a process that never ends (the quit-guard is the safety net).
- Tests: 56 test files start the app in a child that ends with `os._exit` with threads
  running; each is exposed to the same exit hang at 0.5 ms (only this one was seen failing
  in one run; the others' odds are unmeasured).

## Options for the lead

1. **Keep 0.5 ms; end processes without DLL unload where Qt may still be alive.**
   Test side, one file: `test/hang_trace/sitecustomize.py` (loaded in every child the tests
   start) replaces `os._exit` with "flush stdout/stderr, `TerminateProcess(self, code)`"
   (`stall_watch.end_process` already does this). Covers all 56 child scripts at once.
   Program side: the emergency `os._exit` calls (quit-guard, start failures) end through the
   same kind of helper after flushing logs. Behaviour change to exit paths: needs a spec
   check (01 S154 / D-01-QUIT-CLOSE) before coding. **Recommended.**
2. Keep 0.5 ms and remove Python application event filters before any `os._exit`. More
   places to keep in step (three filters today, any new one re-opens it). Not recommended.
3. Use 1 ms. Lowers the odds, does not remove them (unmeasured); the switch-interval study
   showed 1 ms is a weak latency fix. Not recommended.
4. Set 0.5 ms only while a Run is on. Tests and idle quits get 5 ms, but a quit-guard exit
   during a Run keeps the risk. Not recommended alone.
5. Drop the setting. The hang becomes rare again (0/13 at 5 ms) but stays possible in
   principle, and the input-latency gain is lost.

Recommendation: option 1, then re-run `test_main_window_fits.py` and the child-process tests
at 0.5 ms.

Scratch probes (not kept in the repo): fits_si.py / fits_var.py / fits_rel.py (exact
`_CODE` with an interval override and exit variants) and stacks.py / nearest.py (external
native stack dump, nearest-export names) in the SWITCH-SLOW scratchpad.
