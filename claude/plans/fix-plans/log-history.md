# LOG-HISTORY: Gremlin window blank on 2026-11-19

Scout run, read-only. Start 13:04, end 13:04 (clock, `date +%H:%M`). Sources: the user's logs folder (system.log, qt.log, crash.log, logs.txt, device_helper.log) and Windows event logs (System, Security, TerminalServices). Nothing was modified.

## Timeline

| Time | Event | Source |
|---|---|---|
| 11-17 01:26:19 | OSC listener stopped, Screen Saver Mode switched off, Gremlin terminated | system.log |
| 11-18 (all day) | No system.log lines at all, so no Gremlin starts or exits logged | system.log |
| 11-18 | Windows power-session transitions (Kernel-Power 566) at 04:50, 07:50, 07:51, 13:47, 15:17. No sleep, wake, boot or display events | System event log |
| 11-19 03:39:48 | HidHide starts; Screen Saver Mode device helper runs; devices enabled | system.log |
| 11-19 03:40:25 | "Terminating Gremlin", then installer for 1.0.39 starts | system.log |
| 11-19 03:40:37 | "Gremlin UI launching" (new build) | system.log |
| 11-19 03:41:08 | "Gremlin start: 136 UI sequences" | system.log |
| 11-19 04:46:02-03 | "Initializing joystick devices" and "Gremlin start" logged three times, with no matching terminate or end line | system.log |
| 11-19 04:46:03 to 06:16:49 | No log lines at all (about 1.5 h) | system.log |
| 11-19 05:10 | Config saved (logs.txt last write) | logs.txt mtime |
| 11-19 06:16:49 | Screen Saver Mode: screen saver started | system.log |
| 11-19 06:33:28, 06:36:34 | Screen saver started again | system.log |
| 11-19 06:38:34 | Screen Saver Mode: displays powered off; three devices set to be disabled | system.log |
| 11-19 06:38:39 | WARNING: "Not responding for 5 s" (main thread in joystick_gremlin.py main) | system.log |
| 11-19 06:38:43 | "Responding again after 9 s". Devices disabled, then re-enabled. "stopped keeping the displays off ... Windows turned them back on 5 times" | system.log |
| 11-19 06:38:43 | "Unplugged ... let go of buttons [14, 19, 24]" (device-state reset) | system.log |
| 11-19 06:38:43-44 | "Initializing joystick devices" and "Gremlin start" logged again | system.log |
| 11-19 06:41:56, 06:45:29, 06:53:01 | Screen saver started (last entry in system.log) | system.log |
| 11-19 after 06:53 | Nothing logged | system.log |
| 11-19 (all day) | Windows System log: no sleep, wake, boot, display or session events. Only uptime records at 12:00. Security log: no lock or unlock events (4800-4803) in range. TerminalServices: no remote-session events | Windows event logs |

## Could the main window have been minimized, hidden or shown between 05:10 and 12:55 on 11-19?

- **Yes, possible, not proven.** The 06:38:34 displays-off and 9 s stall is the only logged event that touches the window. The stall started with a display power change and a stalled main thread, and it ended with the joystick and UI sequences re-initialized (06:38:43-44). That re-init is the most likely point where pages could have been reset, but no log line says the window was hidden or its pages unloaded.
- **Gap 04:46 to 06:16 (about 1.5 h).** Nothing logged at all. The app was alive but silent, so any minimize or hide in that window cannot be seen.
- **Screen saver starts 06:16, 06:33, 06:36, 06:41, 06:45 and 06:53** all fall inside the window. They are candidates, but the logs do not record window state.
- **Qt log gap.** qt.log has no entries after 2026-10-22, so no Qt messages about screens or windows exist for 11-18 or 11-19. crash.log has no 11-19 entries.
- **Unexplained restarts at 04:46.** Three "Gremlin start" lines with no terminate between them. This may mean the UI was rebuilt. Worth checking in code before the next test.

## Summary (about 12 lines)

1. system.log has no entries for 11-18. Gremlin was not logged again from 11-17 01:26 until 11-19 03:39.
2. 11-19 03:40: the app was terminated and the 1.0.39 installer ran. It relaunched 03:40:37 and started at 03:41:08.
3. 11-19 04:46:02-03: three "Gremlin start" lines with no terminate between them, unexplained.
4. 11-19 04:46 to 06:16: no log lines (about 1.5 h). Config saved 05:10.
5. 11-19 06:16, 06:33, 06:36: screen saver started.
6. 11-19 06:38:34: displays powered off. Main thread stalled 5 s (warning 06:38:39), responded again after 9 s (06:38:43).
7. 06:38:43: devices disabled then re-enabled; "Unplugged" with buttons released; joystick and UI sequences re-initialized (06:38:43-44).
8. 06:41, 06:45, 06:53: screen saver started. Nothing logged after 06:53:01.
9. Windows event logs for 11-19: no sleep, wake, boot, display, lock or unlock, or remote-session events. Security lock events (4800-4803) are absent from the range, so lock or unlock cannot be confirmed.
10. Qt log has no entries for 11-18 or 11-19, so no Qt window or screen messages exist.
11. Nothing in the logs records a minimize, hide, show or tray action. The 06:38 display-off and stall (with re-init) is the strongest candidate; the 04:46-06:16 silent gap cannot be checked.
12. Suggested check (not run): add a log line on window show, hide and page unload, and on stall recovery, so the next occurrence is recorded.
