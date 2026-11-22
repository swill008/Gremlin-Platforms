# vJoy 2.1.9.1 vs 2.2.2.0 (agent NOTES, 2026-11-21)

Method: `gh api` reads of the GitHub repos (no downloads, nothing run). "V" = verified in the cited source, "U" = unverified or inferred.

## 1. Same program or a rewrite? (V: same code continued)
- Fork chain: shauleiz/vJoy -> jshafer817/vJoy -> njz3/vJoy -> BrunnerInnovation/vJoy. https://github.com/BrunnerInnovation/vJoy , https://github.com/njz3/vJoy (parent jshafer817), https://github.com/jshafer817/vJoy (parent shauleiz).
- compare shauleiz master...Brunner master: 140 commits ahead, 154 files, status "diverged" (shauleiz last pushed 2023-08-17; last real commit 2019). https://api.github.com/repos/shauleiz/vJoy/compare/master...BrunnerInnovation:vJoy:master
- Same C driver (driver/sys/*.c, hidmapper), same vJoyInterface.dll, vJoyConf/vJoyConfig/vJoyFeeder, same VID_1234&PID_BEAD. Not a rewrite. Brunner's own 12 commits (2023-12-14..19) only add build scripts, .NET 4.8, installer MinVersion Win10, README disclaimer. Brunner says it does not intend to spend many resources on maintenance. https://github.com/BrunnerInnovation/vJoy#readme
- 2.1.9.1 is jshafer817's signed build (2019-07; commits "Now cross signed and EV signed for Windows 7 SP1 to Windows 10"; njz3 commit 2020-01-10 "match latest 2.1.9.1 version of driver"). shauleiz's own GitHub tags stop at v2.1.8.39 (2018-05-27). https://api.github.com/repos/shauleiz/vJoy/tags . Whether the 2.1.9.x binaries come from jshafer817 only: U (I did not read the jshafer817 releases page).

## 2. Changes by version (V, from njz3 release notes and the commit list)
- 2.2.0.0 (2020-05-23, njz3): FFB simultaneous effects (effect BlockIndex fix, PID state report, 100 effect slots). https://github.com/njz3/vJoy/releases
- 2.2.1.1 (2020-07-18): multi-device FFB bug fix, RAM-pool report fix, FFB registry keys moved out of the .inf into AddvJoyFFB.reg / RemvJoyFFB.reg, C++/C# sample fixes. Same page.
- 2.2.2.0 (2023-12-19 release; code version set 2023-08-16): builds with VS2022/WDK 10.0.22621, x64 only, installer min OS Windows 10 1607, signed with an EV certificate via Microsoft attestation (Win10 and Win11). https://github.com/BrunnerInnovation/vJoy/releases/tag/v2.2.2.0
- Windows 7 / 32-bit: installer was min Win7 SP1 in 2.2.0; 2.2.2.0 is x64 and Win10+ only. (V: commit 2023-08-16 "SDK for x64 only", 2023-08-17 min OS 10.0.14393.)

## 3. HID report / position struct
- Both versions: max 16 devices, 128 buttons, 4 hats (continuous 16-bit or discrete) in the position struct (`VJOY_MAX_N_DEVICES 16`, `VJOY_NUMBER_OF_BUTTONS 128`, `VJOY_NUMBER_OF_HAT 4`). Old: https://github.com/shauleiz/vJoy/blob/master/inc/public.h (JOYSTICK_POSITION_V2 already has lButtonsEx1..3); new: https://github.com/BrunnerInnovation/vJoy/blob/master/inc/public.h (V)
- NEW axes: 2.2.x adds Accelerator, Brake, Clutch, Steering (HID usages 0xC4, 0xC5, 0xC6, 0xC8) plus Aileron, Rudder, Throttle selectable in vJoyConfig; `VJOY_NUMBER_OF_AXES 16`. Commit 2020-03-14 "Add 8 more axes (mainly for driving wheels)". (V, public.h + vJoyConfig.cpp)
- Struct layout CHANGED: old JOYSTICK_POSITION_V2 order ... Wheel, VX, VY, VZ, VBRX, VBRY, VBRZ, lButtons ...; new `JOYSTICK_POSITION_V3` (now the typedef JOYSTICK_POSITION) inserts wAccelerator/wBrake/wClutch/wSteering after wWheel and moves VZ, VBRX, VBRY, VBRZ to the tail. A client that fills its own struct (pyvjoy-style ctypes, C# wrapper) built for the old layout writes wrong offsets against the 2.2.x DLL unless it uses the V3 layout. Commits 2020-03-17/18 mention "struct alignment ... backward compatible" and were reverted/re-done, so whether the old layout still works: U. (layout difference itself V.)
- Driver FFB descriptor: PID state report moved to the end of the HID descriptor; direction range 0..0xFF -> 0..0x7FFF (commit 2020-04-03). Only matters if FFB is used.
- Device-count limit unchanged at 16 (V).

## 4. vJoyInterface.dll API (V, vjoyinterface.h both repos)
- Still present with same names and `__cdecl`: GetvJoyVersion(), vJoyEnabled(), GetvJoyProductString(), DriverMatch(WORD*, WORD*), GetVJDButtonNumber, GetVJDDiscPovNumber, GetVJDContPovNumber, GetVJDAxisExist, AcquireVJD, UpdateVJD, ResetAll, SetBtn, etc. https://github.com/BrunnerInnovation/vJoy/blob/master/SDK/inc/vjoyinterface.h
- Signature changes: `UpdateVJD(UINT, PVOID)` -> `UpdateVJD(UINT, JOYSTICK_POSITION*)`; Ffb_h_* take `UINT*` instead of `int*`; Ffb_h_EBI, Ffb_h_Eff_Const, Ffb_h_EffNew marked deprecated; new Ffb_h_EffectBlockIndex, Ffb_h_CreateNewEffect. C# wrapper calling convention set to cdecl (commit 2020-12-12). Binary ABI of plain functions unchanged for ctypes callers except the struct layout in section 3.
- Version check: VERSION_N = 0x100*X + 0x10*H + M, so 2.2.2.0 -> 0x222, 2.1.8 -> 0x218 (code: public.h lines ~121-128). DriverMatch compares DLL and driver versions. Consequence (V): a vJoyInterface.dll from 2.1.8/2.1.9 with a 2.2.2.0 driver (or the reverse) reports a mismatch. Issue #11 "vJoy version of Driver (222) does NOT match DLL Version (218)" (FreePIE) is exactly this, open, no answer. https://github.com/BrunnerInnovation/vJoy/issues/11 . What the 2.1.9.1 DLL reports (0x218 or 0x219): U.
- The DLL is not a drop-in: apps that bundle their own old vJoyInterface.dll will fail DriverMatch against 2.2.2.0; our program must ship/load the matching DLL. (inference from the above, U for our code)

## 5. vJoyConfig command line (V, vJoyConfig.cpp)
- Same flags in new: `vJoyConfig <id> -f -a <axes> -b <n> -s <discrete povs> -p <continuous povs> -e <ffb effects>`, plus `-d` (delete), `-r` (reset), `-v` (version). New: the `-a` list accepts Wheel, Accelerator, Brake, Clutch, Steering, Aileron, Rudder, Throttle in addition to X Y Z Rx Ry Rz Sl0 Sl1. I did not diff the old usage text (not located in the old file): so "old flags unchanged" is U.

## 6. Signing / Windows support (V)
- 2.2.2.0: EV certificate + Microsoft Partner attestation, Win10 and Win11 only (release body). https://github.com/BrunnerInnovation/vJoy/releases/tag/v2.2.2.0
- 2.1.9.1: signed by jshafer817 for Win7 SP1..Win10 (commit text). Win11 / Secure Boot behaviour of 2.1.9.x: U (njz3 README says Win11 users need 2.2.2.0 for signing reasons: https://github.com/njz3/vJoy#readme "latest Windows 10 and Windows 11 signed version").
- No ARM64 (issue #6).

## 7. Known problems in 2.2.2.0 (Brunner issues tab, 11 issues, all but #1 open) (V that they are filed; V text quoted lightly)
- #12 (2026-11-08) BSOD 0x3B in vJoy_EvtDeviceFileCreate (driver/sys/rawpdo.c ~line 1124): opening the raw PDO with no `\Device_NNN` reference string (empty file name) makes the driver read a NULL buffer. Present in 2.1.9 (vjoy+0x4bc3) AND 2.2.2.0 (vjoy+0x6093). Trigger in the report: Git-for-Windows/MSYS2 `find /` (stats /proc/sys/Device/...). A suggested NULL/length check is in the issue. https://github.com/BrunnerInnovation/vJoy/issues/12
  - This matches our PC's crash (file search opened the device). Fixed in 2.2.x? VERIFIED NOT FIXED: the issue is open and states 2.2.2.0 crashes the same way; no later Brunner tag exists (only v2.2.2.0, last push 2024-06-07). Also a local unprivileged DoS (device openable by standard users).
- #1 (closed 2024) installer hangs on Win11 at Exec_vJoyInstall; comments say still hangs for fresh installs; reporter fixed theirs by removing old driver with pnputil. https://github.com/BrunnerInnovation/vJoy/issues/1
- #9, #10 install fails / not completing (2026); #7 installer no longer writes DllX64Location registry value (software that looks for it can fail); #5 uses USB vendor ID 0x1234 (belongs to another vendor); #4 all vJoy devices share the same GUID/device id so games cannot tell them apart persistently. Detail not read for #9/#10: U.
- #3 asks about a single repository; the sourceforge page was not read (U).

## 8. Open questions (U)
- Exact differences between the 2.1.9.1 binaries and shauleiz master (jshafer817 changes) not diffed.
- Was a real-hardware test of Win11 + Secure Boot done? No; only release text and issues read.
- Raw-PDO crash: no fix exists in any release; options are a patched/self-signed driver (not possible with Secure Boot without signing) or avoiding anything that opens the device (whole-disk searches, Cygwin/MSYS2 tools).
