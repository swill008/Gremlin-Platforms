# 2026-11-20: Gremlin-Platforms R2 1.1.0 stopped without a trace

Found 16:47 (user: "did it crash?"). Read-only study 16:47-16:52.

## Facts (verified)
- Last system.log line 14:08:36 "Run start took 1414 ms" (after SSM disabled
  Steam Controller, PD200X, VKB and powered the displays off at 14:08:33).
- No "Terminating Gremlin" (written right after app.exec() returns, before
  any clean-up; X, File > Exit and the installer all write it).
- No crash.log entry (faulthandler; last entry Nov 1), no freeze report,
  no WER/Application Error/Hang event for gremlin_platforms.exe, no
  Resource-Exhaustion event, no reboot (up since 11/19 13:42), no
  RestartManager/MSI/Windows Update install near the time (only Defender
  definitions 13:52).
- Device helper (elevated, started 08:49:43 for pid 25644) also has no
  "Ended:" line; it logs "Ended: quit/closed/parent gone" on every normal end.
  Neither process is running now.
- The three devices are still disabled (Get-PnpDevice Status Error).
- In-program abrupt exits (_end_at_once, os._exit, _terminate_other_gremlin)
  all log first or need the user's choice in a dialog.
- No other Claude session was active after 04:42.
- WER events at 14:11:32 are old queued reports being sent (BSOD 0x3B of
  11/19 13:30, minidump 111926-15421-01.dmp; GPU watchdog 141/193 from
  Sept-Nov), not new crashes.

## Not known
- When between 14:08:36 and 16:44 it ended, what ended it, and why the
  elevated helper ended at the same time without its line.

## Next (offered to the user)
- Windows process-termination auditing (user sets it; records exit time and
  status for both processes).
- Program logging: a "still running" line while the displays are kept off;
  the helper records the parent's exit code when it sees it gone.
