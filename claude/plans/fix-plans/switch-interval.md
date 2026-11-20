# sys.setswitchinterval: cost and benefit (SWITCH-MEASURE, 2026-11-19)

Question: should Gremlin call `sys.setswitchinterval(0.0005)` (default 0.005) at start?
Probe: claude/plans/fix-plans/switch_probe.py (pytest with `-p conftest`, SW_VAL / SW_SECS / SW_OUT env).
Setup: Python 3.13.15, PySide6 6.11.2, Qt offscreen, one offscreen QQuickView with an
animated QML rectangle, the real input thread, fake hardware, 60 s per cell, real
`EventListener._joystick_event_handler` fed at 1000 events/s from a Python feeder thread
(measured 1000/s every run). The four intervals ran as four parallel processes on an
8-core PC (other agents were also running), temp USERPROFILE. CPU% = time.process_time
over wall time (all threads, % of one core; psutil is not installed).

Scenarios: (a) idle app + input thread; (b) 1000 ev/s + main thread 16 ms QTimer doing 2 ms
of Python; (c) as (b) plus a 100 ms Python busy burst every second on the main thread.

## Results

| interval | (a) CPU% | (b) CPU% | (c) CPU% | (b) queue med / p95 / p99 / max ms | (c) queue med / p95 / p99 / max ms | (c) main burst throughput (M loop iter/s) |
|---|---|---|---|---|---|---|
| 5 ms (default) | 0.7 | 19.7 | 27.4 | 0.05 / 0.20 / 2.11 / 2.4 | 0.09 / 2.2 / 24.6 / 52.7 | 18.29 |
| 2 ms | 0.7 | 19.2 | 26.9 | 0.06 / 0.22 / 2.04 / 4.1 | 0.09 / 4.0 / 17.2 / 41.3 | 18.07 (-1.2%) |
| 1 ms | 1.2 | 20.8 | 26.2 | 0.07 / 0.27 / 1.83 / 3.0 | 0.07 / 3.0 / 9.0 / 23.3 | 17.87 (-2.3%) |
| 0.5 ms | 0.9 | 21.1 | 28.5 | 0.06 / 0.17 / 0.27 / 0.8 | 0.05 / 0.17 / 0.27 / 1.8 | 17.06 (-6.7%) |

Main-thread throughput over the whole run (all main-thread Python work, M iter/s): (b) 2.35 /
2.31 / 2.31 / 2.12 and (c) 3.99 / 3.93 / 3.90 / 3.63 for 5 / 2 / 1 / 0.5 ms.
The (c) timer lateness p99 is about 91 ms in every row: it is the 100 ms burst itself, not the
interval. In (b) 16 ms timer lateness p99 was 0.7-1.0 ms at every interval, max 1.5-2.0 ms.

## Reading

- CPU: no usable difference. Idle (a) 0.7-1.2% is run-to-run noise (0.5 ms is 0.9, 1 ms is 1.2).
  (b) and (c) differ by 1-2 points in no consistent direction (0.5 ms is highest in both, 1 ms lowest
  in (c)); with four processes sharing the PC the noise is about that size. No evidence of a
  CPU cost; an idle process with no contending thread has nothing to switch.
- Latency benefit: only visible when the main thread is busy in Python (c). 5 ms gives p99 24.6 /
  max 52.7 ms; 0.5 ms gives p99 0.27 / max 1.8 ms (a 90x p99 cut). With a light main thread (b)
  the p99 drops 2.1 -> 0.27 ms; the median is unchanged (0.05-0.07 ms) everywhere.
  1 ms and 2 ms are partial: 1 ms halves p99 / max, 2 ms barely helps. Only 0.5 ms removed the tail.
- Throughput cost: the main thread's own Python throughput drops in the burst (-6.7% at 0.5 ms,
  -2.3% at 1 ms) because the input thread now gets the GIL within 0.5 ms and does its work
  (the events are served instead of waiting); whole-run main throughput is -7.5% (b) and -9% (c)
  at 0.5 ms. This is a trade of main-thread speed for input latency, with the same total work done;
  it is also the expected extra GIL hand-offs, not wasted CPU (CPU% unchanged).
- Earlier QWAIT numbers (queue-wait-after-freeze.md) agree: a Run start of an empty profile with a
  busy Python thread took 1474 ms at 5 ms and 11 ms at 0.5 ms; 1 ms still 349 ms.

## Recommendation

Set `sys.setswitchinterval(0.0005)` once at program start (before the input thread starts). The
input path is the priority, and its tail latency under a busy main thread is the measured
problem (and the cause of the 585 ms Run start after the freeze). The cost is about 7% of main-thread
Python speed while it competes with the input thread; measured CPU use is unchanged. 1 ms is
the fallback if 0.5 ms shows UI cost in the real program (it still left 349 ms Run starts and
9 ms p99, so it is a weak fix). Do not pick 2 ms.

## Caveats / unverified

- Offscreen QML (software/no GPU): the real window's render thread and GPU driver threads are not
  here; Qt's render thread contends for the GIL only in QML-callbacks into Python. Whether the
  UI (real GPU window) feels any slower from the 7% is unverified; needs one real-window check.
- The main-thread load is synthetic pure Python; real UI work mixes in C++ (GIL released), which
  lowers the effect in both directions.
- Four processes ran at once; CPU% differences of 1-2 points are inside the noise. A solo repeat
  would tighten that but is not expected to change the conclusion.
- Throughput = iterations of a bare Python loop in fixed wall time, a proxy, not a UI benchmark.
- psutil was absent; CPU is process_time/wall (includes all threads, not per-thread).
- Behaviour change (new program setting in Python code): needs a spec line/decision before it is
  coded (CLAUDE.md change control); not coded here.
