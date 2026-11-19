# Window fix, better tracing, controls on their own thread: merged plan (2026-11-19, planning only)

User 2026-11-19: "lets do it all, so lets do a plan for the window fix, better tracing and the thread fix."
Trigger: the installed 1.0.39 main window was found visible with every page unloaded (Main.qml `trayed`
stuck true; Home click stayed black). Ten read-only helpers, 13:02-13:09; nothing changed, built or run.
Nothing below is approved: spec wording is proposed only.

| Report | Helper (model) | What |
|---|---|---|
| window-tray.md | PLAN-WIN (Opus) | causes ranked, fix, tests |
| tracing.md | PLAN-TRACE (Opus) | Window trace area, memory buffer, Save Window State |
| thread-probes.md | PLAN-PROBE (Opus) | Timing trace area, stall numbers from the logs |
| thread-input.md | PLAN-THR-IN (Opus) | input thread design, batches |
| thread-ui.md | PLAN-THR-UI (Opus) | window-side touch points, guards |
| qt-research.md | QT-RESEARCH (Sonnet) | Qt visibility flag, QTBUG-124177, QThread |
| spec-touchpoints.md | SCAN-SPEC (Sonnet) | statements each change touches |
| tests-pinning.md | SCAN-TESTS (Haiku) | tests pinning tray / same-thread |
| log-history.md | LOG-HISTORY (Haiku) | 11-18/19 timeline |
| help-words.md | SCAN-HELP (Haiku) | glossary and Help words |

## Order
1. Batch W (window fix), owner of system_tray.py / tray_memory.py / Main.qml tray code.
2. Batch T (Window trace area + memory buffer + Save Window State + Timing probes); after W because it
   shares system_tray.py and Main.qml; one owner for trace.py, trace_model.py, LiveLogTrace.qml.
3. The user runs probe scenarios A-C (before numbers).
4. Thread batches 1-5 (+ D spec/map/Help alongside), then scenario D (after numbers).

## Spec numbers (page 01, last is S173)
W: S174 tray follows what Windows shows, S175 tray steps recorded; S87 and S85 amended; D-01-TRAY-TRUTH.
T: S176 Window area, S177 window memory buffer, S178 Save Window State, S179 stall lines, S180 Timing;
S146/S148/S149/S113/S132 amended; 12 S16.
Thread: 02 S40 (+Q8, D-02-S40-HANDLED), 05 S90, 04 S61, 01 S93/S95 change; new statements on page 06
with D-06-INPUT-THREAD; gap SSM-MAIN-THREAD-PAUSE text updated.

## Conflicts resolved in the merge
- PLAN-WIN wanted every tray step in system.log; PLAN-TRACE found system.log defaults to Warning
  (S97), so Info lines are dropped. Merged proposal: tray steps go to the memory buffer and Window trace;
  system.log gets a Warning only when a mismatch is caught and fixed. (Question 2.)
- PLAN-TRACE and PLAN-PROBE both numbered S174: renumbered above.
- ui/backend.py shared by PLAN-THR-IN and PLAN-THR-UI: one owner, staggered.

## Change to the order (user, 2026-11-19 16:4x)
Step 3 ("before" measurement runs) skipped: user answered "b) No: skip before". The thread move is judged by its tests (output reaches vJoy while the main thread is blocked 2 s; fails on the old code); the user's "after" runs only confirm it feels right.
