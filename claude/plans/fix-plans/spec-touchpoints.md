# Spec touchpoints for three planned changes (SCAN-SPEC, read-only, 2026-11-19, 13:03-13:05)

Pages read: README, 01, 02, 03 (threads parts), 04 (threads), 05 (S90), 06, 09 (tray S62-S73), 12.
Marks: WC = would change, NEW = would need a new statement, CD = constrains the design.

## (1) Tray flag stays set while shown, window blank
- 01 S87 / 09 S69: "While hidden in the tray, the pages should be unloaded ... and loaded again when shown." CD (the fix must keep it; it is the behaviour that fails). No statement says the window must not be blank after leaving the tray: NEW (suggest: "Showing the window always reloads the pages; the in-tray state ends whenever the window is visible").
- 01 S84 (left click brings window back), S85 (minimize/close hides), S89 (tray Exit shows window first), 09 S70 (no tray icon: minimize/X behave normally), S73 (--start-minimized to tray): CD, the leave-tray path must cover every way the window is shown.
- 01 S63: "Mode list ... never blank after New, Load or Save As" (a different blank, but shows blank-never is already a spec value). 01 S111 (log view never blank) same.
- 01 section 4 rows (lines 167-168): `_window_mode_changed_cb` -> `Main.enterTray`/`leaveTray`, `tray_memory.release` after 400 ms. Map text, update only.
- Section 10: K3 done (GL-112), K2 done (GL-111); line 583 "Tray in real use has no test (GL-007, needs hands-on)". 03 gap 44 (open, not verified): tray memory release vs large card pictures. No open gap for this blank-window bug: add one.

## (2) Better tracing
- 01 S146-S151 (Trace tab, Tracing switch always off at start, RAW/WIRING/OUTPUT/EVENT/HIDHIDE/OUT OF STEP/OSC/BLOCKED points, trace.log, in-memory list of last 5000 lines S149, "never raises into the code it watches" S151, bounded waits/gremlin.clock). A new Window trace area = NEW statement + new Points filter entry, (WC S146/S149 point list). Always-on tray enter/leave lines contradict S147/S148 spirit ("trace only ticked, off at start") and S149's single-file model: NEW statement needed (always-on lines go to system.log or trace.log?). S110 (red debug mode while Tracing is on): CD, always-on lines must not trigger it. In-memory ring buffer: S149 already has a 5000-line list for the tab only while Tracing; a ring buffer that runs always = WC S149 + NEW. State snapshot command: NEW (also a Debug menu item via the one command list, S65 = WC S65 list; S132 Save Diagnostics contents = WC if the snapshot goes in the zip).
- 01 S104/S109 (Live Log Reader tabs, Live catches every line), S99 (thread errors logged), S112-S113 (watchdog stack dump to system.log): CD, reuse these owners.
- 01 S90-S95 (threads via gremlin.threads, bounded waits, clock): CD for any new watcher thread.
- 02 S95/S96-S98/S114, 06 S86-S87, 12 S16 (Screen Saver Mode trace lines): CD, same line format and Points filter.
- Gaps: TRACE-HINT-OSC (open, hint text under the trace tree) relates: the hint line will change again. AU-119 (open, fixed-wait tests incl. watchdog test).
- Decision D-01-TRACE (README change table, 01 section 12): the whole tracing design was user-approved; widening it needs the user (also memory "Debug: trace per element, Live stays as is").

## (3) Input -> wiring -> output off the Qt main thread
- 02 S40 / D-02-S40-HANDLED (decision wins over Q8): "run in the mode current when the MAIN THREAD handles it". WC (must be reworded to "input thread"; the stamping point moves; mode changes become cross-thread).
- 02 section 6 + 06 section 6: "Event callbacks run on the main thread (queued Qt signals from the listener thread)". WC (stated as fact in 06 and 03 line 267: InputModuleRuntime is a main-thread QObject, `_on_hid`/`_on_key` queued).
- 02 S54-S60 (EventHandler routing, failing action does not stop others, pause, Change Mode, Stop removes actions), 06 S33-S46 (claims gate, mode inheritance, press/release across mode change S38, axis-as-button S39, conditions via modules S46): CD (behaviour must be identical on the new thread; each needs a test that fails on a cross-thread race).
- 05 S90, 04 S61, 01 S93 (Tempo/Double Tap/Smart Toggle timed-out actions and their mode changes "on the main thread"): WC / NEW (timers fire where? a Change Mode from the main thread vs the input thread).
- 01 S155 (owner notices always sent on the main thread), 06 S97 (logicalDeviceModified main thread), 03 can't-be-sent notice: CD, anything the input thread changes that the UI shows must go through these.
- 06 S86/S87 + 02 S95 trace taps: CD (they sit on the path; "off = one check per event", thread-safe lock S151 already).
- 06 run_scope.stop() stage order (CUT_INPUT, CANCEL, FIRE_PENDING ...), 06 S60/S3 Run/Stop: CD (Stop must still cut input first, now across threads). 06 section 7: "a vJoy or Logical Device write can come from a macro thread, relative-axis thread, script-timer thread and the main thread at the same time" and 06 line 481 "Concurrent vJoy opens from a macro thread and the main thread" (known edge): relates, one more writer.
- 01 S90-S92, S95 "Nothing on the main thread should wait without a limit": CD (new thread via gremlin.threads, named, stop request, bounded joins; threads.shutdown 2 s total in the quit order, section 6).
- 04 line 150: process monitor emits process_changed, handler on main thread (auto-load mode/profile change): CD / relates (profile load vs input thread).
- Layer rule memory: hardware -> input module -> wiring -> output module -> driver, no skipped layer: CD.
- 12 SSM-MAIN-THREAD-PAUSE (open, 2026-11-15): main thread stops responding 17-115 s while displays are kept off; "bindings, macros and timers wait meanwhile". This is the motivating gap; moving the path off the main thread would remove the binding part of the stall. Needs the gap text updated and a decision on whether it closes. 12 SSM listener runs on its own listener thread (S2/S6, `_power_window`) already: precedent.
- Other open gaps: 02/03 AU-64 (open: device list refilled on a timer thread while Home reads physical_devices on the main thread), K21 closed, S113 watchdog (measures the MAIN loop tick, so "Not responding" would no longer cover the input thread: NEW or WC S113).
- Needs NEW statements: where each stage runs, the single thread that owns profile/action state, how the UI reads state, ordering guarantee (events in arrival order), what happens on input-thread stall (watchdog), how Stop/mode change/profile load hand over.
