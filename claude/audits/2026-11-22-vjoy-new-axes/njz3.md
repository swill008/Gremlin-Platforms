# njz3 and the 8 new vJoy axes (web research, agent NJZ3, 2026-11-22)

Read-only. V = verified (source cited), U = unverified or inferred.
Start 03:05.

## 1. Who njz3 is (public project identity only)

- V: GitHub user njz3, no public bio or organisations; 50 repos, 23 followers. Work centres on arcade hardware, joystick emulation and force feedback (FFB): vJoy fork (C++, 380 stars), vJoyIOFeederWithFFB (C#), jammamia (JAMMA board firmware), a MAME fork, ArduinoJoystickWithFFBLibrary (fork), hikaruloader. https://github.com/njz3
- V: The vJoy README notes are signed "Benjamin" (compiling notes); njz3's own vJoy README names Brunner's repo as the latest signed build. https://github.com/njz3/vJoy
- V: Feeder credits: Shaul Eizikovich (vJoy with FFB), BigPanik and SailorSat (original Arduino + vJoy concept). https://github.com/njz3/vJoyIOFeederWithFFB
- U: "BackForceFeeder", "FFB arcade plugin", Boomslang and emulation-forum activity: not found in any fetched page. Not confirmed.

## 2. Why 2.2.0 added the 8 axes

- V: The axes were added on 2020-03-14 in njz3's "experimental" cleanup branch, commit 58a0277: "Add 8 more axes (mainly for driving wheels) and use 0xFFFF values for them." Touches driver (hid.c, hidReportDescSingle.h), vJoyInterface, vJoyConf/vJoyConfig, SDK headers. Follow-ups same day: "Add new axes into vJoyConf", "Add new axes to vJoy Feeder", "Add more names for new axes". https://github.com/njz3/vJoy/commit/58a0277 (also commits ef03dfd, 4bebcde, ec9ffdc, d496ff5)
- V: So the stated intent is driving wheels (steering, accelerator, brake, clutch and similar). No per-axis mapping is given in the commit text.
- V: The GitHub release notes for 2.2.0.0 and 2.2.1.1 do not mention axes at all; 2.2.0.0 says "simultaneous effects" (FFB), 2.2.1.1 lists FFB multi-device and RAM-pool fixes, FFB registry keys moved out of the .inf. https://github.com/njz3/vJoy/releases
- V: FFB work in 2.2.0: effect BlockIndex up to 100, PID state report, fixes from users (Rubikoid, ivan-kljajic). See njz3/vJoy commit list, March to June 2020.
- U: Why 8 and not fewer: no stated reason found.

## 3. njz3's own feeder and the Brunner relationship

- V: Feeder maps steering X, accelerator Y, brake Z, clutch RX, 32 buttons, one first vJoy device; says "Only 3 or 4 vJoy axes are useful." Needs vJoy 2.2.2. FFB is emulated with constant-torque commands at 200 or 100 Hz. Last commit 2025-01-12. https://github.com/njz3/vJoyIOFeederWithFFB
- V: So the feeder never uses the new axes (classic X/Y/Z/RX only). The later Windows 10/11 2.2.2.0 build keeps them regardless.
- V: Brunner (Brunner Elektronik AG, a simulation-products company) forked njz3's repo; contributors listed on BrunnerInnovation/vJoy: shauleiz 181, njz3 110, jshafer817 7, Crayon2000 3, BraINstinct0 1, lukester1975 1; Brunner itself is not a contributor. njz3 set version 2.2.2.0 (2023-08-16) and Windows 10 minimum (2023-08-17); a "null" author fixed the Inno script and WDK 22621 (2023-08-16). The 2.2.1.1 note says the Windows 11 build is Brunner's 2.2.2.0 and thanks Justin Shafer for signing. https://github.com/BrunnerInnovation/vJoy , https://github.com/njz3/vJoy/releases
- U: Whether Brunner sponsored the work or just paid for EV signing: not stated anywhere I found. Likely rebuilt and signed (the code is njz3's).

## 4. Users of the 2.2.x builds and the new axes

- V: Feeder reads outputs from MAME, Supermodel (Model 3), m2emulator, TeknoParrot (OutputBlasters). That is lamp output reading, not use of vJoy axes. Same feeder page.
- V: Issue #30 (2025-04, code-monet): fixes usage pages for the simulation axes so DirectInput types vJoy as a wheel; tested in Need for Speed Most Wanted and Hot Pursuit, Burnout and The Crew 2, which then detect vJoy as a "wheel". https://github.com/njz3/vJoy/issues/30
- V: Sim Gamer Kit guide (code-monet): enables Accelerator, Brake, Steering for wheel detection. https://code-monet.github.io/sim-gamer-kit/fffsake/vjoy_configuration/
- V: Open issues in njz3/vJoy mention FFB in iRacing (#24), Windows 11 install, MSFS2024 interaction (#29), bf6 detecting vJoy as an Xbox pad (#31), Joystick Gremlin plugin with 2.2 (#7).
- U: No Supermodel, TeknoParrot or MAME page found that uses the 8 new axes; web searches (several, incl. arcadecontrols forum hits) returned nothing tying them to vJoy axes.

## Takeaway

The new axes were made for driving wheels, by the arcade-cabinet developer, but the only confirmed real-world use is the "wheel type" trick for PC driving games. njz3's own tool does not use them.

End 03:06 (per date +%H:%M).
