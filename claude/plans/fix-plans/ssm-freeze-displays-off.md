# Main thread freeze at Screen Saver Mode's power-off (FREEZE, 2026-11-20)

Read-only study, agent FREEZE, 05:42-05:50. Installed 1.0.40 = HEAD 0fc64a7e.
Sources: `C:\Users\Stacie\Gremlin Platforms\logs\system.log`, `trace.log`,
`device_helper.log` (the user's real logs, read only); program code at HEAD.
Nothing was run, changed or built. Planning only: nothing below is approved.

## 1. The main-thread stack in each freeze (verified from the dumps)

| Freeze | system.log dump line | Main thread stack (line) | Length |
|---|---|---|---|
| 2026-11-19 17:49:11 | 6017 | 6140-6142: `joystick_gremlin.py` 1376 `main` (app.exec in that build) | 8 s |
| 2026-11-19 20:22:32 | 6418 | 6541-6543: `joystick_gremlin.py` 1376 `main` | 6 s |
| 2026-11-20 05:36:51 (test 2) | 6970 | 7093-7095: `joystick_gremlin.py` 1413 `main` | 6 s |
| 2026-11-20 05:40:08 (test 3) | 7255 | 7386-7388: `joystick_gremlin.py` 1413 `main` | 10 s |
| 2026-11-20 05:44:51 (test 4) | 7619 | 7742-7744: `joystick_gremlin.py` 1413 `main` | 7 s |

`joystick_gremlin.py:1413` is `app.exec()`. The main thread has **no Python
frame above the Qt event loop**: it is stuck in native code (Qt or Windows),
not in any of our Python code. faulthandler shows Python frames only, so the
native function it waits in is not in the dumps (unverified which).

Other threads in every dump (e.g. 7255): `Device disabler` is in
`gremlin/device_disable.py:575 _ask` (waiting on the helper's pipe, its own
thread); the input thread in `input_thread.py:97` (its Qt loop, idle);
the Screen Saver Mode listener in `screen_saver_mode.py:1296` (GetMessageW,
idle). Nothing in Python waits on the main thread.

What the main thread still does during the freeze (verified):
- It **does** run sent (non-queued) window messages: the tray window
  (`gremlin/ui/system_tray.py:304`, created on the main thread by
  `joystick_gremlin.py:1177`) handles `WM_POWERBROADCAST` in Python
  (`_power_broadcast_cb`, system_tray.py:531) and its "displays on/off"
  WINDOW lines are written inside the freeze with live times (e.g. trace.log
  05:36:49.149, 50.423, 51.949, 52.673; 05:40:04.520-11.908).
- It does **not** run posted messages or timers: the 250 ms watchdog beat
  stops, and every Screen Saver Mode trace line drained by the main timer
  (`_drain_events`, screen_saver_mode.py:1953) comes out at once when it ends.

That pattern (sent messages served, posted messages and timers not) is what a
thread shows while it is blocked inside a cross-thread or cross-process
`SendMessage`, or a modal wait that pumps only sent messages (for example a
COM call). Which one: unverified (no native stack).

## 2. Why test 1 (05:33) did not freeze

Same power-off, same three devices disabled through the helper, the displays
flicked on four times (trace.log 14297-14323), but no stall: the main timer
kept draining at 05:33:33.493 and 35.156, in the middle of the disables.
The one difference (verified):

| Test | Profile running | Devices disabled | Freeze |
|---|---|---|---|
| 05:33 test 1 | no (started only at 05:36:34, trace 14374) | Steam Controller COL03, PD200X MI_03, VKB | none |
| 05:36 test 2 | yes | same | 6 s |
| 05:40 test 3 | yes | same | 10 s |
| 05:44 test 4 | yes | same | 7 s |
| 11-19 17:49 / 20:22 | yes (Reload "Profile stopped/started" after) | same | 8 s / 6 s |

Every freeze in these logs happened **while the helper was disabling the
devices and a profile was running**, and it ends as the last device (the
VKB, the one stick the profile uses) finishes disabling:

| Test | Helper "disable ... done" (device_helper.log 169-189) | Main thread back |
|---|---|---|
| 1 | Steam 33.485, PD200X 35.015, VKB 35.216 | never stalled |
| 2 | 50.414, 52.149, **52.889** | first drain 52.770, stall ended 52.947 |
| 3 | 06.785, 09.080, **11.909** | "disabled, done" traced 11.910, stall ended 13.476 |
| 4 | 49.656, 51.976, **52.896** | first drain 52.839, stall ended 53.697 |

Disables also take longer while running (VKB 0.2 s idle vs 0.7-2.8 s running;
whole set 4.7 s vs 6.6-8.9 s), and enables never stall (about 0.1 s each,
e.g. 05:37:28 and 05:40:43 with a profile running).

Display flicking alone is not the cause here: the displays kept flicking
after each freeze ended (05:36:54-57, 05:40:13-16, 05:44:54-59) with no new
stall, and test 1 flicked without a stall.

Side finding (verified as timing, mechanism unverified): **each device
disable wakes the displays.** The helper's "done" times land on a "displays
on" line within about 10 ms: 05:33:33.485/33.494, 35.015/35.017,
05:36:50.414/50.423, 05:40:06.785/06.792, 11.909/11.908. So S21's own
disables cause most of the wakes counted in the wake count (S20) right after
the power-off; that is why "power off sent again" fires several times in the
first seconds.

## 3. Cause chain (plain words)

1. The Power off displays timer fires on the main thread; the device hook
   asks the helper to disable the three saved devices (async, its own
   thread), then the power-off is posted to the listener window.
   **Verified** (screen_saver_mode.py:1847-1879, screen_saver_mode_model.py:508-518).
2. The helper runs `pnputil /disable-device` for each device in turn.
   Windows asks every program that holds the device whether it may go
   (query-remove) and waits for them. **Unverified** (Windows behaviour, not
   in our logs).
3. While a profile runs, Gremlin's process holds the VKB (and its other
   sticks) open through a native library, and some part of that native code
   answers on, or makes Windows wait on, the main thread. The main thread
   then sits in a native wait that serves only sent messages until the VKB
   removal completes. **Unverified**: which library (candidates: dill.dll /
   DirectInput, vJoyInterface.dll opened at Run start since S106, Qt's own
   device-change handling, HidHide). The logs only prove the timing (section
   2) and the native wait (section 1).
4. When the VKB is gone, the main thread is released, works off the
   backlog, sees "1 gone" and Reloads the profile. **Verified** (trace
   05:44:52.931 unplugged, 53.132 re-read, 53.141 Profile stopped).
5. Keep-off: the re-sends themselves are **not** on the main thread
   (verified: `on_display_state` runs in the listener's window procedure,
   screen_saver_mode.py:1221-1227 -> 1883-1904, and `_post_resend` posts
   straight to the listener's window, 1914-1918). Only two parts are on the
   main thread: the re-send held back by the 1 s gap (`_retry_keep_off`,
   called from `tick`, line 1783 -> 1920) and the trace/log lines
   (`_drain_events`). So during a freeze an ON inside the gap waits for the
   freeze to end, and all the "power off sent again (#n)" lines appear at
   once even though most re-sends went out on time (#n is counted when sent,
   `_note_resend` 1906). **Verified** from code; whether every re-send in a
   freeze went out on time: unverified (the lines carry the drain time, not
   the send time).
6. Screens stay on mostly because the disables themselves keep waking them
   (side finding above) until the last device is gone, plus the gap-held
   re-send waiting for the frozen main thread. **Partly verified** (timing).

## 4. The slow Reload right after the freeze (lead's question)

Stop -> start: test 2 53.170 -> 54.783 (1.6 s), test 3 13.619 -> 16.746
(3.1 s), test 4 53.141 -> 54.845 (1.7 s), against about 130 ms for the
Reload after the wake (05:40:43.987 -> 44.120, 05:45:17.543 -> 17.675).

Verified from code and logs:
- The Reload is started on the main thread but runs on the input thread:
  device change on a timer thread (`event_handler.py:500-550`, "Devices
  re-read") -> `device_change_event` -> `Backend._device_change`
  (`ui/backend.py:464-474`, "Reload") -> `activate_gremlin(False/True)`, which
  only posts Stop and Run to the input thread (`backend.py:603-634`, no wait).
- The input thread does not wait on the main thread: no
  `BlockingQueuedConnection` or main-thread wait anywhere in `gremlin/`
  (grep; matches queue-wait-after-freeze.md section 1).
- The main thread is alive during the slow start: it drained "power off sent
  again (#5)" at 05:44:54.719, inside 53.141-54.845.
- The 941 ms queue wait ("waited for Run start", trace 05:44:57.463) is
  events held behind that Run start; the Timing line in that window shows
  "process 33 %" against 5 % in the normal restart (05:45:17.471).
- The difference from the fast Reload: the slow one restarts the Run right
  after a device was **removed** (and two others are still mid-removal in
  PnP terms), with the main thread working off 6-10 s of backlog; the fast
  one restarts after an **arrival** with an idle main thread.

Unverified (no timing marks inside `CodeRunner._start`): which step takes the
1.5-3 s. Candidates, in order of likelihood:
1. `output.open_claimed_vjoy()` (code_runner.py:461, S106): vJoyInterface's
   existence check / acquire enumerates HID devices through SetupAPI, which
   can wait on Windows' device manager lock while removals settle.
2. GIL hand-overs against the main thread's backlog (the convoy measured in
   queue-wait-after-freeze.md). The 0.5 ms switch interval is in this build
   (`joystick_gremlin.py:469`), which measured Run start under load at 11 ms,
   so the GIL alone should not give 1.5 s; it can add to (1).
3. dill re-reading devices for the new Run.
How to verify: Timing-trace marks around each step of `_start` (one line per
step with its ms), then one more test on the user's PC.

## 5. Fix options (recommended first)

1. **Measure first: native wait chain in the freeze dump.** (Recommended.)
   On a freeze, the watchdog also asks Windows what the main thread waits on
   (`GetThreadWaitChain`, Wait Chain Traversal, advapi32; no administrator
   rights for our own process): it names "SendMessage to thread X of process
   Y", a COM call, a lock, etc. Optionally one minidump of the process per
   freeze (`MiniDumpWriteDump`) for the native stack. Plus Timing marks in
   `CodeRunner._start` (section 4). For the user: nothing changes except a
   few more lines in system.log after a freeze. Files: `gremlin/watchdog.py`,
   `gremlin/code_runner.py`, a test each. Spec: page 01 S113/S179 describe
   the freeze dump and stall lines; adding the wait chain is an addition to
   S113's content, so it needs the user's OK and a spec line. Effort: 3-8 min
   per agent (timings.md: agent fix), 2 agents in parallel, then a test on the
   user's PC.
2. **Quick A/B on the user's PC (no code).** Run the same test with a profile
   running and (a) the VKB taken off the saved Devices list, (b) the helper
   not running (no disables). If (a) has no freeze, the stick the Run holds
   is the trigger; if (b) has none, the disables are. For the user: three
   one-minute tests. Spec: none. Effort: no timing data yet; rough guess
   5 min of the user's time.
3. **Release the profile's devices before disabling them (if 1/2 confirm).**
   At the power-off, when a device on the saved list is one the Run holds,
   stop holding it before the helper disables it (or skip disabling sticks
   the running profile uses). For the user: no freeze; the VKB is not
   disabled while a profile runs (or is let go first). Files:
   `gremlin/ui/screen_saver_mode_model.py`, `gremlin/device_disable.py`,
   maybe `gremlin/code_runner.py`. Spec: **changes 12 S21** ("Gremlin
   disables every device in that list") and possibly 06 (Run holding
   devices); needs the user's decision. Effort: 3-8 min per agent
   (timings.md: agent fix), after the cause is known.
4. **Disable the devices before the power-off and wait for them (bounded),
   then power off.** S21 already says "disables every device in that list,
   then turns the displays off"; today the power-off is posted at once while
   the disables run (screen_saver_mode.py:1868-1871). Doing them in that
   order (power-off sent from the disabler thread when the helper answers,
   bounded wait) means the disable wakes (section 2 side finding) happen
   before the displays go off, so far fewer re-sends. Does not by itself
   fix the freeze. For the user: displays go off 5-9 s later but stay off.
   Files: `gremlin/screen_saver_mode.py`, `gremlin/ui/screen_saver_mode_model.py`,
   `gremlin/device_disable.py`. Spec: matches S21's wording ("then"); the
   timing of "then" should be written into S21 with the user's OK. Effort:
   3-8 min per agent (timings.md: agent fix).
5. **Move the gap-held re-send and the keep-off lines off the main thread**
   (see 6). Small; removes the keep-off's last dependence on the main loop.

## 6. Should the keep-off logic move off the main thread?

The keep-off is already mostly off it (section 3, point 5): the display-ON
answer and the power-off post run on the listener thread. What still needs
the main thread: (a) `_retry_keep_off` (the re-send held back by the 1 s gap)
runs from the 1 s main tick, and (b) the trace/log lines. Recommendation:
yes for (a): arm the retry on the listener thread (a Win32 `SetTimer` on the
listener window, fired in its own message loop), so a frozen main thread no
longer delays any re-send; leave (b) on the main thread but stamp each event
with its own time when queued so the lines show when the re-send really
happened. Spec: 12 S6 already says "at most once a second"; the
section 7 threads table (line 137) says the listener answers a display-ON
"at most once a second (no new thread)", which still holds (a timer on the
same thread). No statement changes; the map's section 7/10 entries would be
updated. Gap SSM-MAIN-THREAD-PAUSE (page 12 line 210) is related but is about
continuous switching; this freeze is a separate, device-disable-bound case
and should be its own gap.
