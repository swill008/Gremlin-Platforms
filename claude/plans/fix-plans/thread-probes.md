# Thread probes: measuring input delay before and after the thread move (PLAN-PROBE, 2026-11-19)

Read-only planning scout, 13:03-13:05. Nothing in the program was changed or run. Everything below is
**proposed**; no spec statement changes until the user approves. Feeds stage 0 of
claude/plans/rust-middle-path-study.md ("Measurements missing before deciding", items 1-4). Sibling plans:
PLAN-THR-IN / PLAN-THR-UI (the thread move), PLAN-TRACE (new tracing, maybe a "Window" area).

## 1. The path today (verified)

| Hop | Thread | Where (file:line) | What happens |
|---|---|---|---|
| H0 driver callback | dill's thread | gremlin/event_handler.py:368 `_joystick_event_handler` | `dill.InputEvent(data)`; RAW trace tap at :396 |
| H1 Event built + emitted | dill's thread | gremlin/event_handler.py:404/419/434 `self.joystick_event.emit(Event(...))` | calibration, cache update, Qt signal across threads = **queued** to the main thread |
| H2 main-thread dispatch start | Qt main | gremlin/modules/runtime.py:195 `_on_hid` | claim gate `should_forward`; `self.event.emit` (direct, same thread) |
| H3 wiring start | Qt main | gremlin/event_handler.py:856 `process_event` (connected at gremlin/code_runner.py:452) | mode, `_matching_callbacks`, WIRING tap at :883-905 |
| H4 actions | Qt main | gremlin/event_handler.py:907 `_run_callbacks` | each callback |
| H5 output write | Qt main | gremlin/modules/output.py:559 `write_vjoy` -> `_write_vjoy`; OUTPUT tap :565-567 | one vJoy driver call |

The **queue wait** is H1 -> H2: the time the event sits in Qt's queue until the main thread is free. That is
the hop that grows during a main-thread stall; H2 -> H5 is the Python cost per event.

Trace stamps today: `trace._stamp` (gremlin/trace.py:571) uses `clock.now()` formatted to whole
milliseconds, taken when the line is written, not when the event happened. RAW is written on dill's thread,
WIRING/OUTPUT on the main thread, so RAW -> WIRING already approximates queue wait, but only for buttons
and hats (axes are rate limited, S148, so a RAW axis line is usually a later value than the WIRING line).
`Event` (gremlin/event_handler.py:93) has no `__slots__`, so a stamp attribute can be added.

## 2. Probe design (proposed)

**Switch:** a separate opt-in trace area **Timing**, a tick row in the Trace tab next to HidHide / Screen
Saver Mode / OSC (S146 pattern, saved like the other ticks). Only active while Tracing is on AND Timing is
ticked. It writes no per-event lines (per-event lines at 1 kHz would flood trace.log); it writes one
**TIMING** summary line per interval and stall lines. If PLAN-TRACE adds a "Window" area, Timing sits
beside it with the same tick mechanics; no new subsystem, the writer lives in gremlin/trace.py (or a small
gremlin/trace_timing.py owned with it).

**Cost when off:** one module-level bool check per hop (`if trace_timing.on:`), same pattern as
`trace.enabled()` today (S148 "Off costs one check per event"). No `perf_counter_ns` call when off.

**Stamps** (all `time.perf_counter_ns()`, monotonic, sub-microsecond on Windows; not `gremlin.clock`
because tests fake that clock; tests inject a counter function instead):

| Stamp | Set at | Carried how |
|---|---|---|
| `t0` driver receive | event_handler.py:368, first line of `_joystick_event_handler` | local, passed into `_joystick_event` |
| `t1` emitted | just before each `emit` at :404/:419/:434 | new optional `Event` attribute `t_rx = (t0, t1)`, default `None` (only set when on) |
| `t2` dispatch start | runtime.py:195 `_on_hid` entry | read `event.t_rx`, compute queue wait `t2 - t1`; stash `t2` on the event |
| `t3` wiring start / `t4` callbacks done | event_handler.py:856 entry and after `_run_callbacks` | thread-local "current timed event" (like `trace._local.current`, trace.py:720) |
| `t5` first output write | output.py:565 next to the OUTPUT tap (also ViGEm and SendInput writers) | reads the thread-local; records `t5 - t0` once per event |

Hops recorded per event: **driver->emit** (t1-t0), **queue wait** (t2-t1), **gate->wiring** (t3-t2),
**actions** (t4-t3), **end to end** (t5-t0, only for events that wrote an output). Kept in a fixed-size
in-memory accumulator per hop (a bounded list of up to N samples per interval, or HDR-style buckets
0.01 ms to 10 s, log-scaled; no allocation per event beyond the append). Events and their counts per input
kind (axis/button/hat) and per device.

**Summary line** every 10 s while there were events (and at Tracing off / Stop):
`HH:MM:SS.mmm  Timing  TIMING  10 s: 9,812 events (4 devices) · queue wait median 0.04 ms p95 0.21 p99 0.9 max 3.1 · actions median 0.06 p95 0.12 p99 0.4 max 1.8 · end to end median 0.15 p95 0.5 p99 1.6 max 4.9 · CPU main 7 % · process 11 %`

**Stall lines:** when one event's queue wait exceeds 50 ms, one TIMING warning line per stall episode:
`Timing  TIMING  queue wait 2,340 ms (events held: 1,204; first held at 04:32:23.118)`. This is the
binding-delay-while-busy number (study item 3). Correlation with the watchdog: the watchdog
(gremlin/watchdog.py:98-108) only reports stalls over 5 s, at 1 s resolution; the TIMING stall line gives
the true length of every stall over 50 ms. Proposed small addition: when Timing is on, the watchdog's
"Not responding" and "Responding again" texts also go to trace.log as EVENT lines, so both sit on one
time line. Optional (needs the user, it is a behaviour change on watchdog wording): log stalls of 0.5-5 s
as one INFO line.

**CPU / GIL share (study item 2):** per interval, `time.thread_time()` sampled on the main thread (a
10 s QTimer) vs `time.process_time()` gives main-thread share and whole-process share. GIL contention
itself is not directly observable from Python; proxy = driver->emit hop (t1-t0) growing at high input
rates while main-thread CPU is high (dill's thread waits for the GIL to build the Event). A py-spy
`--gil` recording is the direct measure but needs the user's OK (study, item 2).

**After the move (study item 4):** the same stamps survive the move because they ride on the Event and a
thread-local: when PLAN-THR-IN moves H2-H5 to an input thread, `t2` becomes "input thread picks it up"
and queue wait measures that thread's queue instead of Qt's. PLAN-THR-IN must keep `_on_hid` (or its
successor) as the stamp point; that is the only contract with the move.

Keyboard (`_keyboard_handler`, event_handler.py:578), OSC and virtual events: phase 2, same stamps; the
first round covers joysticks only (the path the study names).

## 3. Repeatable scenario and summary tool (describe only)

**Scenario A, baseline (5 min):** profile with Map to vJoy on 2-4 axes and 4 buttons of one stick
(Gladiator EVO R or the NXT throttle), Run. Tracing on, tick Timing only (no per-control ticks, so RAW /
WIRING / OUTPUT lines don't add their own cost). Move the stick continuously in circles for 60 s, then
press buttons for 30 s, then leave still for 30 s.
**Scenario B, high rate (3 min):** same, all four connected sticks moved at once (two hands, then feet on
pedals if any) for 60 s.
**Scenario C, busy UI (5 min):** while repeating scenario A's stick circles: open the Device Library and
browse 3 devices; load a large profile twice (File › Load Profile); open Help; run Screen Saver Mode's
power-off once (the known 5-300 s stall source). Write down the clock time of each step.
**Scenario D:** A-C again after the thread move.
Then Save Diagnostics (includes trace.log, S132) or send trace.log.

**tools/latency_report.py** (new, read-only, stdlib only): reads trace.log (+ .1), finds TIMING summary
and stall lines and EVENT lines (Tracing on/off, Run/Stop, watchdog), and prints per session: a table per
hop (median / p95 / p99 / max, weighted by event count), the stall list (start, length, events held) next
to the watchdog stalls from system.log in the same window, and with `--compare before.log after.log`
the two side by side. It also has a `--legacy` mode doing what section 4 did by hand: pair button RAW ->
WIRING and WIRING -> OUTPUT lines at ms resolution for logs made before Timing exists. trace.log lines
carry no date; the tool dates sessions from system.log (Tracing on/off is not in system.log today, so it
anchors on Run/Stop/Screen Saver lines; proposal: the TIMING summary line carries the date).

## 4. What the user's logs already say (read-only, 2026-11-19)

Source: C:\Users\Stacie\Gremlin Platforms\logs\system.log (2026-10-10 to 2026-11-19; system.log.1 ends
2026-10-01, before the watchdog existed: 0 dumps) and trace.log (9,154 lines; lines 7424-7498 = 2026-11-15
11:14-12:29, lines 7499-9154 = 2026-11-16 02:33-13:41, dated by matching Screen Saver Mode lines in
system.log; earlier lines are from undated sessions).

**Watchdog stalls ("Not responding", over 5 s):** 38 episodes, 36 with a "Responding again" line (2 never
recovered in the log: 2026-11-16 02:59:25 and 03:40:11, both ending in a quit). By day: 10-12: 2,
10-13: 2, 11-15: 25, 11-16: 8, 11-19: 1. Lengths (closed episodes): median 12 s, 90th percentile 85 s,
max 331 s, total 1,482 s (about 25 min frozen). 10 lasted 30 s or more, 5 lasted 60 s or more (208 s on
11-15 11:56; 309 s, 76 s, 331 s back to back on 11-16 04:27-04:39). The long ones are all Screen Saver
Mode sessions (study: SSM-MAIN-THREAD-PAUSE).

**Per-event delay from existing trace lines (ms resolution, all sessions):**
- WIRING -> OUTPUT (main thread, actions + vJoy write): 2,874 pairs, median 0 ms, p95 1, p99 1, max
  93 ms (matches the study).
- Button RAW -> WIRING (dill thread -> main thread = queue wait proxy): only 24 pairs, median 1 ms,
  p95 3, p99 8, max 8 ms. Too few to trust, and all outside stalls.

**Trace activity during stalls (11-15 and 11-16, the dated days):** 6 of 33 stalls have trace lines inside
them, and **none has a WIRING or OUTPUT line**: no ticked control was moved while the main thread was
frozen, so the logs cannot show binding delay during a stall. What they do show:
- 2026-11-16 04:32:23-04:33:39 (76 s stall): 267 SCREEN SAVER lines written inside it; the last batch
  ("power off sent again" #217-#223) all carry the same stamp 04:33:38.877, i.e. work held and released
  at once when the main thread came back. That is the queue-wait effect, seen on Screen Saver Mode work,
  not on bindings.
- 2026-11-16 05:10:12-05:10:18 (6 s stall): one RAW line (NXT Axis 2, 05:10:16.178) was written on dill's
  thread during the stall, with no WIRING line after it (the device was then disabled by Screen Saver
  Mode at 05:10:17.9). So input does keep arriving while the main thread is frozen; whether its binding
  ran late or was dropped can't be told from this log.
- The 331 s stall (04:33:44-04:39:10) has zero trace lines.

Conclusion: today's logs confirm stalls are frequent and long during Screen Saver Mode use and that
input keeps arriving during them, but they hold no measurement of binding delay under a stall. Scenario C
with the Timing probe is needed to get one.

## 5. Spec wording proposal (page 01, PROPOSED, needs the user's approval)

- **S174 (new, next free number; or S151a next to tracing)** The Trace tab has a **Timing** row (after
  the OSC row) with one tick, saved like the others. While Tracing is on and Timing is ticked, the
  program measures, for every joystick input event, the time from the device driver's call to the event
  being handled (**queue wait**), the time its actions took, and the time to its first output write, at
  sub-millisecond resolution, and writes one **TIMING** line every 10 s with events counted and the
  median, 95th, 99th percentile and maximum of each, plus the main thread's and the program's CPU share.
  A queue wait over 50 ms writes one TIMING warning per episode with its length and the events held.
  Off costs one check per event; no per-event lines are written. [proposed 2026-11-19, PLAN-PROBE]
- **S148 change:** the Points list and the Points filter (S149) gain **TIMING**.
- **S151 unchanged** (threads via gremlin.threads, never raises) and applies to Timing.
- Optional, page 01 watchdog statement (the "Log When Not Responding" option): while Timing is on, the
  "Not responding" / "Responding again" lines are also written to trace.log as EVENT lines.
- Glossary: **Queue wait**, **Timing** (claude/glossary.md, UI words).

## 6. Tests that fail on the old code (proposed)

- `test/unit/test_trace_timing.py`
  - off: no `perf_counter_ns` call and no TIMING line when Timing is unticked or Tracing is off (patch the
    counter, assert not called) - fails today because no Timing exists (import error).
  - stamps travel: drive a fake `dill.InputEvent` through `EventListener._joystick_event_handler` ->
    queued signal -> `InputModuleRuntime._on_hid` -> `EventHandler.process_event` -> `write_vjoy`
    (vJoy faked, as test_trace_taps_in.py does), with an injected counter; assert the TIMING summary has
    1 event and the expected hop values.
  - stall: hold the main thread (block the queue) for a fake 200 ms between emit and dispatch; assert one
    TIMING warning "queue wait 200 ms (events held: N)".
  - percentiles: 1,000 synthetic samples -> exact median / p95 / p99 / max.
  - never raises: counter or writer raising leaves the binding result unchanged (S151).
- `test/unit/test_trace_tab.py::test_timing_row_ticks_and_saves` (Trace tab row, saved tick).
- `test/unit/test_latency_report.py`: fixture trace.log + system.log -> expected table and stall
  correlation; `--legacy` pairing on a fixture of today's format.
- End to end (off-screen, existing test_trace_e2e.py pattern): Run, 500 axis events, TIMING line present
  with 500 events.

## 7. Files and owners

| File | Change | Owner (map page) |
|---|---|---|
| gremlin/trace.py (or new gremlin/trace_timing.py) | Timing tick, accumulator, TIMING writer | page 01 (trace) |
| gremlin/event_handler.py | t0/t1 at :368/:404/:419/:434; t3/t4 in `process_event` | page 02 |
| gremlin/modules/runtime.py | t2 + queue wait at `_on_hid` :195 | page 03 |
| gremlin/modules/output.py (+ ViGEm / SendInput writers) | t5 at the OUTPUT tap :565 | page 06 |
| gremlin/watchdog.py | optional EVENT copy to trace.log | page 01 |
| qml/LiveLogTrace.qml | Timing row | page 01 |
| tools/latency_report.py | new summary tool | tools (not program code) |
| claude/program-map/01-app-shell.md, 02, 03, 06, claude/glossary.md, Help | spec, map sections 2/3/11, glossary, Help | docs agent |

Contract for parallel agents: `trace_timing.on: bool`; `trace_timing.stamp_rx(event, t0, t1)`;
`trace_timing.dispatch(event)`; `trace_timing.begin(event)` / `end()`; `trace_timing.output()`;
`Event.t_rx: tuple[int, int] | None`. Clash with PLAN-THR-IN on event_handler.py and runtime.py: stamp
edits are a few lines and should land in the same batch as, or before, the thread move.

## 8. Effort (from claude/timings.md, rules of thumb 2026-10-09)

- Probe code: 4 agents in parallel (trace core + tab, taps in event_handler/runtime/output, latency_report
  tool, spec/map/Help) - "Agent fix / feature / docs": 3-8 min per agent, a batch ~10 min; plus lead
  checks and map ~5 min, quick tests + commit ~2 min, CI ~10 min in the background. About 17 min to
  committed, ~27 min with CI.
- User scenarios A-C: no timing data yet; rough guess 15 min of the user's time (A 5 + B 3 + C 5 + send).
- Reading the results with latency_report.py: "Review / read-only study": 5-10 min.
- py-spy GIL recording: no timing data; needs the user's OK first.
