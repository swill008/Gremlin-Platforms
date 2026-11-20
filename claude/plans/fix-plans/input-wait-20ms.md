# "Queue wait" median ~20 ms on 1.0.40 (WAIT20, 2026-11-19)

Question: on the user's PC (installed 1.0.40, thread move f5fbc7d7) the Timing summaries show
"queue wait" (listener emit on dill's driver thread, t1 -> `InputModuleRuntime._on_hid` on the input
thread, t2) at median ~20 ms (18:01: 21 events, median 20.6, p95 22.8, max 22.9; 17:57: 3 events,
median 10.5; 17:49: 24 events, median 20.4). Before the move the same hop looked like ~1 ms.

All measurements below use Python's default 5 ms switch interval (the installed 1.0.40 has no
`sys.setswitchinterval`; the harness sets 0.005 after starting the input thread and asserts it),
except the one row marked 0.5 ms.

## Answer (verified)

The 20 ms is **not** a slow wake-up of the input thread. It is events of one burst waiting in line
behind the **first vJoy write of a Run**, which opens the vJoy device and takes 18-142 ms. Every
"queue wait" summary with a high median is a 10 s window holding exactly such a burst (a stick
plugged in again after Screen Saver Mode turned it back on, right after a Run start).

1. **Isolated events are fast.** From the user's trace.log after the 1.0.40 start (17:41 on), RAW ->
   WIRING of the same input (ms resolution), events with no other RAW in the 100 ms before:
   n 30, median 0.5 ms, p95 4 ms. Before the move (older lines of the same file): n 42, median 1 ms,
   p95 3 ms. No change.
2. **Every high median window is one burst behind the first vJoy write.** 18:01:04 (trace.log 13949-
   13966): six RAW lines at 04.398-04.400, Axis 1 WIRING at 04.402, its OUTPUT ("vJoy 3 axis X ...
   written") at **04.420 (18 ms)**, the other five dispatched at 04.421-04.423, i.e. 21-23 ms after
   their emit: exactly the summary's median 20.6 / p95 22.8 / max 22.9. 17:49:23: Axis 1 WIRING
   23.496 -> OUTPUT 23.537 (41 ms), the rest dispatched at 23.539-23.542 (the "about 45 ms" already
   noted in queue-wait-after-freeze.md), plus the 3 events held 585 ms behind that Run start.
3. **Only the first write of a Run is slow.** In the post-move log, the first OUTPUT after each
   "Profile started" took 142, 41, 27, 18, 27 ms (WIRING -> OUTPUT); all other 2,168 writes took
   0-1 ms (max 1). The pre-move part of the log has the same pattern (first write after a Run start
   93 ms at 19:18:39, the "max 93 ms" in thread-probes.md section 4). Cause in code:
   `reset_vjoy()` releases vJoy at every Run stop (gremlin/modules/output.py:1099), and the next
   write opens it again through `_open_vjoy` (output.py:286, vJoy acquire + driver reads).
4. **Why it looked new:** before the move there was no "queue wait" step; the pre-move ~1 ms figure
   is a RAW -> WIRING proxy over 24 isolated button presses with none of these plug-in bursts in it.
   The before/after numbers measure different things. The same burst would have queued the same way
   on the main thread before the move (one thread runs the events in order either way).

17:57:26 (3 events, median 10.5, max 19.8): the three "Unknown device" button releases after the
VKB unplug, dispatched together at 26.304-26.305, 3 ms after "Devices re-read" (26.301). Their
waits are spread 0-20 ms, so the input thread was busy for ~20 ms before 26.304, most likely with
`InputModuleRuntime.reload` from `device_change_event` (runtime.py:119, queued to the input thread
ahead of them). **Unverified** (no trace line marks that reload).

## Hypotheses ruled out (harness, verified)

Harness: `%TEMP%\wait20\harness.py` (outside the repo). Real `gremlin.input_thread` (QThread with
exec and its 0.5 s heartbeat timer), a receiver QObject moved onto it, auto connection as in
runtime.py:112, events emitted from a plain Python thread (like dill's callback thread), a second
receiver on the main thread for the pre-move path, real main event loop (`app.exec`), Windows
platform plugin (QGuiApplication, no window shown). t1/t2 with `time.perf_counter_ns`. Python 3.13,
PySide6 6.11, temp USERPROFILE.

| case | input thread (now) med / p95 / max ms | main thread (pre-move) med / p95 / max ms |
|---|---|---|
| 10 ev/s | 0.11 / 0.23 / 0.39 | 0.12 / 0.20 / 0.35 |
| 100 ev/s | 0.11 / 0.22 / 0.37 | 0.12 / 0.26 / 0.45 |
| 1000 ev/s | 0.08 / 0.17 / 1.22 | 0.09 / 0.19 / 1.27 |
| 100 ev/s, main busy 8 ms Python every 16 ms | 0.12 / 2.56 / 8.04 | 0.13 / 2.62 / 8.23 |
| same four with timeBeginPeriod(1) | 0.08-0.11 median, max <= 8.1 | 0.09-0.13 median, max <= 8.3 |
| burst of 6, action ~1.6 ms each | wait med 4.7 / p95 8.8 / max 9.9 (= the events ahead x action time) | - |
| same, main busy 50 ms Python, 5 ms / 0.5 ms switch | max 18.5 / 10.9 | - |

- (1) Input thread's event loop waking late / only at the 15.6 ms timer tick: **no**. Wake-up is
  ~0.1 ms at 10, 100 and 1000 events/s, same as the main thread; the heartbeat timer changes nothing.
- (2) Delivery through the main thread first: **no**. `EventListener.joystick_event` is emitted on
  the driver thread and `InputModuleRuntime` lives on the input thread after
  `code_runner.adopt_runtime_objects()`, so Qt posts straight to the input thread (also verified in
  queue-wait-after-freeze.md section 1).
- (3) GIL wait behind the main thread: adds up to one switch interval (~5-8 ms max) when the main
  thread is busy in Python; it does not make a steady 20 ms median. It does lengthen bursts (max
  18.5 ms vs 10.9 ms at 0.5 ms) and Run starts (queue-wait-after-freeze.md section 2).
- (4) Windows timer resolution: **no** measurable effect on the hop (medians equal with and without
  timeBeginPeriod(1)).

## Fix options (recommendation first)

1. **Recommended: keep vJoy open across a Reload Run restart, or open it at Run start (before the
   first event is taken), not on the first write.** The burst after a plug-in / Screen Saver wake
   then runs at ~1 ms per event instead of waiting 18-142 ms behind the open. For the user: the first
   stick movement after a Run start or a stick coming back reaches the game ~20-140 ms sooner; no
   other change. Behaviour change in the output module (when vJoy is acquired/released), so it needs
   the 06 output spec page checked first. Effort: no timing data for this kind yet; rough guess
   15-30 min agent fix + tests.
2. **Make the Timing summary honest:** split "queue wait" into "waited behind earlier events" and
   "wake-up" (t2 minus the end of the previous event's dispatch on the input thread), so a burst
   behind a slow action no longer reads as a slow hop. For the user: the Timing line stops
   suggesting a 20 ms input delay that isn't there. Tracing-only change. Effort: rough guess 10-20 min
   (no timing data for this kind).
3. **Keep the 0.5 ms switch interval (already in the working tree).** Cuts the GIL part of the tail
   (burst max 18.5 -> 10.9 ms here; Run start 1474 -> 11 ms in queue-wait-after-freeze.md). It does
   not remove the vJoy-open wait. Already measured in switch-interval.md; its exit-hang side effect is
   in switch-slowdown.md.
4. Not recommended: anything on the input thread's event loop or timer resolution; the harness shows
   no wake-up delay to remove.

Evidence scripts (outside the repo): `%TEMP%\wait20\pairs.py` (RAW -> WIRING pairs from trace.log),
`%TEMP%\wait20\harness.py` (wake-up / burst harness). Times: start 19:40, end 19:47.
