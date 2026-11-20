# Main thread stuck in NtUserPeekMessage while the displays flick (PEEKSTUDY, 2026-11-20)

Read-only study + web research, agent PEEKSTUDY, 06:28-06:33. Nothing run
against the program, nothing changed. Planning only: nothing below is approved.
Sources: Qt source `qtbase/src/corelib/kernel/qeventdispatcher_win.cpp` at
branch 6.11 and tag v6.11.0 (fetched from GitHub qt/qtbase; the two differ only
in a `saturate_cast` rename), the same file at 6.8 for comparison;
`C:\Users\Stacie\Gremlin Platforms\logs\system.log` 9068-9460 and
`trace.log` 18268-18400 (read only); program code at HEAD 264ffc6c;
`powercfg /availablesleepstates` (this PC: S3, no Modern Standby / S0 Low Power
Idle, so the Desktop Activity Moderator is not involved).

## 1. What Qt 6.11's loop does at that spot (verified from source)

`QEventDispatcherWin32::processEvents` (file lines 474-571 at 6.11):

1. `sendPostedEvents()` once, at the top (line 484; "To prevent livelocks,
   send posted events once per iteration").
2. Inner `while (!interrupt)` loop:
   `PeekMessage(&msg, 0, 0, 0, PM_REMOVE)` (line 503; no `PM_QS_*` filter, no
   `PM_NOYIELD`). If it returns a message it is dispatched and the loop goes
   round again. If not, `MsgWaitForMultipleObjectsEx(0, ..., 0, QS_ALLINPUT,
   MWMO_ALERTABLE)` (zero timeout); only when that also says "nothing" does
   the loop `break`.
3. After the inner loop, if nothing was processed it blocks in
   `MsgWaitForMultipleObjectsEx(INFINITE, QS_ALLINPUT, MWMO_INPUTAVAILABLE)`
   (line 565). The stack is **not** there: it is in the PeekMessage of step 2.

How Qt's work reaches the thread:
- Posted Qt events (queued signal calls from other threads,
  `QTimer.singleShot(0)`, every "fast" timer) are delivered **only** by the
  `sendPostedEvents()` at the top of step 1. `wakeUp()` (line 833) posts one
  `WM_QT_SENDPOSTEDEVENTS` at a time; inside the inner loop that message only
  calls `startPostedEventsTimer()` (line 525: `SetTimer(USER_TIMER_MINIMUM)`)
  and the loop goes on; the resulting `WM_TIMER` for that timer is **skipped**
  inside Qt's own loop (line 533, "intended for use inside foreign loop").
  So posted events wait until the inner loop exits.
- Qt timers: `PreciseTimer` and Coarse timers <= 20 ms use `timeSetEvent`
  (multimedia timer thread, `qt_fast_timer_proc` line 82), which **posts** a
  `QTimerEvent` (so they starve with posted events). Coarse timers > 20 ms
  (our 250 ms watchdog beat, the 1 s Screen Saver Mode tick) use
  `SetCoalescableTimer` -> `WM_TIMER`, dispatched to `qt_internal_proc` ->
  `sendTimerEvent` (line 195-198) inside the inner loop.
- Windows makes `WM_TIMER` (and `WM_PAINT`) only when no sent, posted or
  input message is waiting (documented GetMessage priority order).

Starvation: yes, by design. As long as every `PeekMessage(PM_REMOVE)` finds a
posted or input message, the inner loop never exits, so posted Qt events never
run, and `WM_TIMER` is never made, so timers > 20 ms never run either. A
stream of one `WM_QT_SENDPOSTEDEVENTS` re-posted from another thread
faster than the loop turns round is enough on its own (each one re-arms
`wakeUps`). Sent messages (cross-thread `SendMessage`, `WM_POWERBROADCAST`,
`WM_DISPLAYCHANGE`, `WM_SETTINGCHANGE`, `WM_DEVICECHANGE` broadcasts) do not
keep the loop in: they are delivered inside `NtUserPeekMessage` through a
kernel callback (`KiUserCallbackDispatcher` -> `__fnDWORD`/`DispatchClientMessage`
-> the window procedure would show **above** `NtUserPeekMessage`) and
PeekMessage then returns FALSE if nothing is posted.

The loop is the same in 6.8 and 6.11 (diff: timer interval types only), so
the "since Qt 6.9" report in section 2 is not this function.

What the two samples say (verified from the dump, system.log 9413-9460): both
are inside the kernel part of `NtUserPeekMessage` with **no** callback
frames above it, 0.3 s apart. If the thread were spinning through a message
stream (starvation above), most samples would land in `DispatchMessage`, our
Python window procedure or Qt code, not twice in the syscall. So the samples
favour "the thread spends the freeze inside one (or a few) long
NtUserPeekMessage calls" over "a busy message storm". Between samples it
does come out to user mode for sent messages: the tray's `WM_POWERBROADCAST`
handler (Python, `gremlin/ui/system_tray.py:531`) wrote every "displays on/off"
WINDOW line with live times during the freeze (trace.log 18298-18347). The
wait chain "Running" (WCT) only says it is not in a wait WCT tracks (mutex,
critical section, SendMessage, ALPC, COM); a kernel wait inside win32k is not
one of those, so "Running" does not prove CPU use. **Unverified** which:
MSGMEASURE's CPU-time measure settles it (kernel time rising ~1 s/s = busy in
win32k; flat = waiting inside win32k; user time rising = message storm).

Timing detail (verified, trace.log 18293-18298): power off sent 06:24:51.153,
stall began (no tick for 5 s) at 06:24:52, but the first "displays off" line
is 06:24:59.823: for the first ~8 s not even the sent `WM_POWERBROADCAST` was
served (or Windows sent it late; unverified which). The stall ended
06:25:50.151 ("after 58 s") and all 40 held re-send lines drained at once.

## 2. Web findings

- Qt interest list, 2026-03-16 (A. Dyagilev): a QML `Timer` does not fire
  while the monitor is off; the dialog appears with its countdown running
  when the monitor is turned back on; worked in Qt 6.8.2, broken in 6.9.3;
  no reply, no bug number. [users] Closest match; same "resumes on wake"
  pattern as gap SSM-MAIN-THREAD-PAUSE (page 12 line 212: "recovers at the
  next keyboard or mouse input"; any Qt program stalls while any program
  keeps the displays switching). Since the dispatcher loop did not change
  6.8 -> 6.9+ (section 1), a 6.9 change, if real, is elsewhere (QPA screen
  handling or the Quick render loop). [unverified]
  https://lists.qt-project.org/pipermail/interest/2026-March/040450.html
- QTBUG-83158: `WM_QT_SENDPOSTEDEVENTS` keeps the queue populated so a host
  loop's idle never runs (MFC). QTBUG-77464: system event processing starved
  by timer events (5.14 regression). QTBUG-82701 / QTBUG-83151: the 5.14/5.15
  livelock fix that introduced the posted-events timer used today.
  QTBUG-85981: queued connections not delivered in nested loops after that
  change. [bug titles from search snippets only; the Jira pages are
  script-rendered and could not be read]
  https://bugreports.qt.io/browse/QTBUG-83158 ,
  https://bugreports.qt.io/browse/QTBUG-77464 ,
  https://bugreports.qt.io/browse/QTBUG-85981
- Windows 11 24H2/25H2 display-off hangs and flicker: forum reports only
  (DWM vs driver Multi-Plane Overlay flicker; hangs on display-off resume on
  Modern Standby laptops). None mention NtUserPeekMessage; this PC has no
  Modern Standby. [users]
  https://learn.microsoft.com/en-us/answers/questions/5749171/error-screen-flickering-and-black-screen-issue-on ,
  https://elevenforum.com/t/windows-modern-standby-causing-asus-ux461-to-hang-ltt-video.15332
- NOT found: any report of a thread held for seconds inside NtUserPeekMessage
  during monitor power changes, or a QTBUG for exactly this. [unverified]

## 3. What lives on the main thread (verified from code)

| Thing | Thread | Starts with Run? | Source |
|---|---|---|---|
| WH_KEYBOARD_LL hook | own thread "keyboard hook" (0x64e0 in the dump, in `GetMessageW`) | no: program start | `gremlin/windows_event_hook.py:377-408`, `event_handler.py:287-288` |
| WH_MOUSE_LL hook | own thread "mouse hook"; only while a "record" UI holds it (`acquire`/`release`) | no; not in this dump | `windows_event_hook.py:431`, `ui/util.py:107,409` |
| Raw input (RIDEV_INPUTSINK, mouse + keyboard), `RegisterPowerSettingNotification`, power-off window | Screen Saver Mode listener thread (0x5dcc, `screen_saver_mode.py:1296` GetMessageW) | no: when Screen Saver Mode is on | `screen_saver_mode.py:1232-1296` |
| Tray hidden window + `RegisterPowerSettingNotification` (GUID_CONSOLE_DISPLAY_STATE) -> `WM_POWERBROADCAST` (sent) | **main** | no: program start | `ui/system_tray.py:295-316, 91-110, 531-541` |
| Qt's own windows (the hidden QQuickWindow, Qt's internal message window, QWindowsContext) | **main** | no | Qt |
| SendInput (mouse motion) | own thread "mouse motion" (`sendinput.py:333`, idle wait) | no | |
| HidHide watch, macro scheduler, OSC listener, zeroconf, event listener, input thread | own threads, all idle in waits in the dump | | system.log 9302-9411 |
| dill input callback -> `EventListener.joystick_event` -> `Backend._highlight_input` | emitted on dill's native thread, **queued to main** (one posted event per axis/button/hat change; the slot returns early when highlighting is off or the page is not open, but the post happens anyway) | no (dill callback set at start, `event_handler.py:364-365`, emits `:419/434/450`; connection `ui/backend.py:395`) | |

No hook and no raw-input registration is on the main thread. With a profile
running, nothing new is put on the main thread by Gremlin's code that I
could find; what a Run adds is traffic: the input thread and vJoy outputs
(vJoy devices are also DirectInput devices dill may report, so a Run can add
`joystick_event` posts to main; **unverified** whether dill reports vJoy
devices). The one main-thread notification that fires during the flicking
is the tray's `WM_POWERBROADCAST` (Python, sent).

## 4. Cause chain and fix options

Cause chain:
1. Screen Saver Mode powers the displays off; Windows keeps turning them on;
   the listener re-sends (S6) 40 times in 58 s. **Verified** (trace 18293-18347,
   the 40 drained lines).
2. During that, the main thread sits in Qt's inner loop inside
   `NtUserPeekMessage`; posted Qt events and timers do not run; sent messages
   (tray power notes) do. **Verified** (dump + trace).
3. Qt's loop starves posted events and timers whenever PeekMessage keeps
   returning or keeps the thread. **Verified from source.**
4. Why PeekMessage keeps the thread: either (a) win32k holds it inside
   the call (kernel wait or kernel work tied to the display power
   transitions; both samples in the syscall, no callbacks) or (b) a steady
   posted/input stream keeps the inner loop going (e.g. `joystick_event`
   posts during a Run). **Unverified**; (a) fits the samples better, (b) fits
   "only with a profile running". The earlier finding that any Qt program
   stalls while displays flick (page 12 SSM-MAIN-THREAD-PAUSE) points at (a)
   as the base cause, with Run traffic possibly lengthening it.
5. It ends at the next real keyboard/mouse input or when the flicking stops.
   **Verified** for this program earlier (gap entry); mechanism unverified.

Fix options (recommended first):

1. **Finish the measurement (MSGMEASURE, running now).** Main-thread
   kernel/user CPU time across the freeze (`GetThreadTimes`), plus a count of
   messages by type seen by a Qt native event filter
   (`installNativeEventFilter`, main thread) per second, written in the
   freeze dump. Decides 4(a) vs 4(b). Files: `gremlin/watchdog.py` (MSGMEASURE
   owns it). Spec: 01 S113/S179 (freeze dump content) gain lines; needs the
   user's OK like the wait chain did. Effort: in progress.
2. **Make Screen Saver Mode's keep-off independent of the main thread.**
   Only `_retry_keep_off` (the re-send held by the 1 s gap, called from the
   main 1 s tick, `screen_saver_mode.py:1783 -> 1920`) still needs it; arm it
   as a Win32 `SetTimer` on the listener window. Then the displays stay off
   regardless of 4, and the flicking (the trigger) gets shorter. Stamp each
   queued trace event with its own time. Files: `gremlin/screen_saver_mode.py`,
   test in `test/unit/test_ssm_core.py`. Spec: 12 S6 ("at most once a second")
   unchanged; page 12 section 7 thread table row (line 139) and gap
   SSM-MAIN-THREAD-PAUSE updated. Effort: 3-8 min (timings.md: agent fix).
3. **Reduce the flicking (to-do 142).** Fewer wakes = shorter freeze whatever
   the cause: order the disables before the power-off (12 S21 "then turns the
   displays off"), per ssm-freeze-displays-off.md option 4. Spec: S21 timing
   written in with the user's OK. Effort: 3-8 min per agent (timings.md: agent
   fix).
4. **If 4(b) is confirmed: stop per-event posts to the main thread.** Gate
   `joystick_event -> Backend._highlight_input` on the emitting side (a
   thread-safe "highlight wanted" flag set by the main thread when the
   Device page is open with highlighting on), or coalesce to one post per
   frame. Files: `gremlin/ui/backend.py`, `gremlin/event_handler.py`. Spec:
   no behaviour change (highlighting still works when shown); page 01/02 map
   sections 3/5. Effort: 3-8 min (timings.md: agent fix).
5. **If 4(a) is confirmed: keep the main thread out of the long call.** Qt
   offers no switch for this; options are the user-visible parts staying
   off the main thread (done for bindings, 06 S100) and option 2 for the
   keep-off. A Qt-side workaround (own `QAbstractNativeEventFilter` or a
   custom dispatcher using `PM_QS_POSTMESSAGE`) cannot help if win32k holds
   the thread inside the call. Worth a one-off check with a Qt 6.8.2 build
   against the Qt interest report (no timing data yet; rough guess 30 min).
6. Move the tray's `WM_POWERBROADCAST` registration to the listener thread:
   **not recommended**; it is a sent message served in microseconds and is
   our only live signal that the thread is alive during the freeze.
