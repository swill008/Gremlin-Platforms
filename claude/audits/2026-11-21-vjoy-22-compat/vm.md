# vJoy 2.2.2.0 in the test machine (agent VMTEST, 2026-11-21 15:33-15:40)

Machine: the Hyper-V test machine "GremlinTest", in the state the user left
at 15:24, with no checkpoint restored. Installed there: vJoy Device Driver
2.2.2.0 (vjoy.sys 2.2.2.0), ViGEmBus 1.22.0, HidHide 1.5.230 and the Visual
C++ Runtime 14.44.35211. vJoy devices 1-4 have 8 axes, 128/127/126/125
buttons and 4 continuous hats each. The program is in
`C:\Users\gremlintest\AppData\Local\Programs\Gremlin-Platforms`.

How the checks ran: each check was a host script that called
`tools/vm-test/vm-run.ps1` (PowerShell Direct, as gremlintest, which is an
administrator in the guest). Nothing touched vJoy on the host. The app ran in
gremlintest's disconnected desktop session 2 through a scheduled task with an
interactive principal. The scripts and their transcripts are in the lead's
scratchpad `vmt\vjoy22-*.ps1` / `.log`.

## Check 1: the shipped vJoyInterface.dll against the 2.2.2.0 driver: PASS

The check loaded `_internal\vjoy\vJoyInterface.dll` (888,432 bytes; its file
version reads 0.0.0) through C# P/Invoke (`Add-Type`) in the guest. Results
(`vjoy22-c1.log`):

| Call | Result |
|---|---|
| vJoyEnabled | True |
| GetvJoyVersion | 546 = 0x222 |
| Product / Manufacturer / Serial strings | "vJoy - Virtual Joystick" / "Shaul Eizikovich" / "2.2.2.0" |
| DriverMatch | True, dll = 0x222, driver = 0x222 |
| GetVJDStatus 1-4 | 1 (FREE) for each. Buttons 128/127/126/125, 4 continuous hats, 0 discrete hats, axes 0x30-0x37 on all four |
| GetVJDStatus 5 | 3 (MISSING) |
| GetVJDAxisMin/Max (device 1, X) | 0..32767 |
| AcquireVJD 1 | True; the status then reads 0 (OWN) |
| SetAxis X=8192, Y=24576; SetBtn 1 and 128; SetContPov 1 = 9000 | all True |
| RelinquishVJD 1 | the status reads 1 (FREE) again |

How Windows saw the values:

- **Windows multimedia (winmm) joyGetPosEx** listed 4 joysticks with VID
  0x1234 and PID 0xBEAD. On joystick id 0 it read X=16384, Y=49152,
  buttons=0x1 and POV=9000. These are the set values scaled to 0-65535, so
  they arrived. Joystick ids 1-3 stayed centred. Button 1 read 0x0 again
  after SetBtn(false). winmm only reports 32 buttons, so it can't show
  button 128.
- **Raw Human Interface Device (HID) read** (`vjoy22-c1b.log`): ReadFile on
  each `HID\HIDCLASS&COL0n` collection, decoded with HidP_GetUsages and
  HidP_GetUsageValue. COL01 (report ID 1) gave buttons [1, 128], X=8192 and
  hat=9000. The other three collections had no report within 3 s, which is
  expected because devices 2-4 weren't fed. **Button 128 reaches Windows.**

Side notes (not failures):

- GetVJDAxisExist returns True for all 8 axes on device 5, which doesn't
  exist. The program's link-up didn't trip on it (check 2), but don't use it
  alone to test whether a device exists.
- The Windows.Gaming.Input RawGameController list (WinRT) showed the 4 vJoy
  devices with the right button counts, 12 axes and 0 switches. Its readings
  were all zero in this non-interactive session, so it wasn't used as
  evidence. That's a limit of how the check ran, not a vJoy result.

## Check 2: the program links all 4 vJoy devices: PASS

The first run (`vjoy22-c2.log`) used the default log level, Warning. The app
ran (pid 3528, session 2) and system.log stayed empty, so there was no
"vJoy left out: ..." error. The matching lines are debug level, so the
second run (`vjoy22-c2b.log`) did this:

1. Backed up `configuration.json`.
2. Set global/general/log-level to ALL.
3. Ran the app for 25 s (pid 1236, session 2, started 15:38:02).
4. Read system.log, which now had 49 lines.
5. Stopped the app and restored `configuration.json`. The file hash
   matched the backup afterwards.

What the log showed:

```
Added: name=vJoy Device guid=AD0B28E0-E5BF-11F1-8003-444553540000   (and 8005, 8007, 8009)
vJoy guid=...8003...: (8, 128, 4)   ...8005: (8, 127, 4)   ...8007: (8, 126, 4)   ...8009: (8, 125, 4)
vjoy id 1: (8, 128, 4) - MATCH
vjoy id 2: (8, 127, 4) - MATCH
vjoy id 3: (8, 126, 4) - MATCH
vjoy id 4: (8, 125, 4) - MATCH
Loaded: map-to-vjoy
```

There were no "can't be told apart" lines, no "isn't listed" lines, and no
ERROR, CRITICAL or Traceback lines. While the app ran with no profile active,
GetVJDStatus read FREE for devices 1-4: the app doesn't hold them until a
profile runs. No app process was left afterwards, and the scheduled task
was removed.

## Check 3: the program's own vJoy output reaching Windows: NOT RUN

This check needs a running profile and an input to feed it. The test machine
has no physical controller, and building a profile there was outside this
check's time. The DLL path the program uses for output (Acquire, SetAxis,
SetBtn, SetContPov) is the same one shown working in check 1.

## Not verified

- Output written by Gremlin-Platforms itself, through a profile, reaching
  Windows (check 3).
- Gremlin Input Tester with vJoy 2.2.2.0.
- Force feedback (FFB) with vJoy 2.2.2.0.
- Devices 2-4 were only read for status and layout, never fed.
