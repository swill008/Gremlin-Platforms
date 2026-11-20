# Queue wait after a window freeze (QWAIT, 2026-11-19)

Live finding on 1.0.40 (f5fbc7d7): after Screen Saver Mode's 8 s "Not
responding" (17:49:07-17:49:15), trace.log showed
`17:49:23.493 TIMING queue wait 585 ms (events held: 3; first held at 17:49:15.387)`
and a 10 s summary with queue wait median 20.4 ms (p95 582, max 585).
Queue wait = listener emit (t1, driver thread) to `InputModuleRuntime._on_hid`
(t2, input thread).

## 1. What ran where (verified)

- Events go straight to the input thread, no main-thread hop.
  `EventListener._joystick_event` emits `joystick_event` on the driver thread
  (gremlin/event_handler.py:419/434/450). `InputModuleRuntime` connects
  `_on_hid` with an auto connection (gremlin/modules/runtime.py:112) and is
  moved to the input thread by `code_runner.adopt_runtime_objects()`
  (gremlin/code_runner.py:835-861), so Qt queues each event to the input
  thread. Probe: a main thread frozen in a GIL-releasing native wait
  (kernel32.Sleep 1 s) gives queue wait median 0.06 ms, max 0.4 ms.
- Nothing on the input path waits for the main thread: the input-thread
  callers use `threads.main_call` (no wait: output.py:206/408, tts.py:65/112/149,
  osc.py:1053/1141, notice.py:99); `main_call_wait` has no callers in gremlin/
  or action_plugins/; no BlockingQueuedConnection anywhere.
- The 585 ms stall is the Reload Run restart on the input thread. The device
  change at 17:49:14.492 (`Devices re-read: 4 connected, 0 new, 1 gone`) ran
  `Backend._device_change` "Reload" (gremlin/ui/backend.py:464-474):
  `activate_gremlin(False)` then `(True)`, both posted to the input thread
  (backend.py:199-206, 619-627). Stop ran at 17:49:14.502 ("Profile stopped").
  `RunControl.start` (code_runner.py:791) then ran the whole Run start on the
  input thread and ended at **17:49:15.972 "Profile started"**. The first held
  event was emitted at 17:49:15.387 and waited 585 ms: 15.387 + 0.585 =
  **15.972**, the same millisecond. So the events queued behind the Run start,
  which took at least 585 ms (system.log: "Gremlin start: 136 UI sequences" at
  17:49:15).
- The same restart 8 s later (17:49:23.651 stopped -> 23.688 started) took
  at most 37 ms.
- The later VKB events: RAW lines are written on the driver thread before the
  emit (event_handler.py:401-402), all six at 23.493-23.495; Axis 1 ran its
  action at 23.496 and its first vJoy write ended at 23.537 ("actions max
  44.1 ms"), so the five events behind it waited about 45 ms each. That, with
  the 3 held events, is most of the high half of the 24 samples.

## 2. Why the Run start took 585 ms instead of ~37 ms: GIL convoy

Reproduced (claude/plans/fix-plans/queue_wait_probe.py, real input thread via
`input_thread_running`, events through `EventListener._joystick_event_handler`):

Run start of an empty profile on the input thread, with another thread busy in
pure Python (stands for the main thread working through its backlog after the
freeze), Python 3.13.15, PySide6 6.11.2:

| switch interval | load | Run start | Stop | 200 flushed file writes |
|---|---|---|---|---|
| 5 ms (default) | idle | 7.7 ms | 7.6 ms | 1.0 ms |
| 5 ms (default) | busy Python thread | **1474 ms** | 96 ms | **1041 ms** |
| 1 ms | busy Python thread | 349 ms | 25 ms | 232 ms |
| 0.5 ms | busy Python thread | 11 ms | 4.5 ms | 1.7 ms |

Every call that lets go of the GIL (a file write, a ctypes call, a lock wait)
has to win it back from the busy thread, which takes up to one switch interval
(5 ms). A Run start makes hundreds of those calls, so it stretches by 100x+.

Event queue wait while the main thread is frozen in different ways (events
every 20 ms; "io" = 4 flushed log lines per event, like the trace lines):

| main thread | switch 5 ms: median / p95 / max | switch 0.5 ms |
|---|---|---|
| idle | 0.06 / 0.2 / 0.7 ms | 0.06 / 0.1 / 0.3 |
| native wait, GIL released | 0.07 / 0.2 / 0.4 | 0.06 / 0.2 / 0.3 |
| busy Python loop | **5.0 / 25.5 / 40.6** | 0.07 / 0.2 / 0.2 |
| native call holding the GIL (PyDLL Sleep 500 ms) | 0.09 / 0.2 / **500.5** | (no event emitted during it) |
| backlog of 300 x 3 ms main-thread jobs | 0.07 / 25.5 / 36.3 | 0.07 / 0.1 / 0.3 |

So a busy main thread alone costs each event about one switch interval (5 ms,
more with trace lines), not hundreds of ms; hundreds of ms come from (a) work
already running on the input thread (the Run start) stretched by the GIL
convoy, or (b) a native call that holds the GIL.

Verified: the routing, the restart timing match, the convoy mechanism and its
size. Unverified: that the main thread was busy in Python between 17:49:15.08
and 15.97 (inferred: it was clearing the backlog after the freeze; trace.log
shows main-thread lines at 15.417, 15.956, 15.963; no CPU sample for that
second). Unverified: why 0.5 ms removes the convoy almost fully rather than
by 10x (likely the Windows GIL wait rounding a sub-millisecond timeout to 0,
so the waiter asks for the GIL at once; not read in CPython source).

## 3. Fix

No routing bug in our code: nothing was changed. Options (for the user):

1. `sys.setswitchinterval(0.0005)` at program start (one line in
   joystick_gremlin.py). Measured above: Run start under load 1474 -> 11 ms,
   event queue wait under a busy main thread max 40 -> 0.2 ms. Cost: the busy
   thread hands over the GIL more often (more context switches); not measured
   on the real app yet. Not changed: needs the user's OK (interpreter-wide).
2. Fewer GIL hand-overs on the input path: trace/log writes from the input
   thread go to a writer thread (queue, no file I/O on the input thread); the
   first vJoy write after a re-plug (44 ms) looked at separately.
3. Less Python on the main thread after a freeze (coalesce the backlog,
   e.g. the displays on/off and device-change handling) and keep the
   Screen Saver Mode device disable off the main thread (unverified that it
   is on main: "to be disabled" 17:49:06.034 to "disabled, done" 14.267 lines
   up with the 8 s stall; not traced to a thread).
4. Rust study item: the input path outside the GIL.
5. Expected and by design: events wait for a Run start; Reload on device
   change restarts the Run. Could be noted in Timing as "waited for Run start".
