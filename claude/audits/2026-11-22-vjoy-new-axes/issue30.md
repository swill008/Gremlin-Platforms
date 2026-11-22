# njz3/vJoy #30 and the new axes' usage page (agent FIX30, 2026-11-22)

Read-only; `gh api` and WebFetch only, nothing downloaded or run. Start 03:16, end 03:16 (clock did not tick over; about 4 min real).
V = verified (source cited), U = unverified.

## 1. What #30 is

- V: #30 is a pull request, not an issue: "Fix the usage pages for simulation usages", by code-monet, opened 2025-04-20, ready for review 2025-04-21, branch code-monet:usage_pages -> njz3:master, last force-push 2025-05-17. State: OPEN, not merged, no reviews, no maintainer comment, mergeable cleanly (ahead 5, behind 0). https://github.com/njz3/vJoy/pull/30
- V: It is the only open PR on njz3/vJoy (6 closed: #1, #2, #27, #28 merged; #3, #26 closed unmerged; none about axes). https://github.com/njz3/vJoy/pulls
- V: 5 commits, 11 files (+195 -214): apps/vJoyConf/vJoyConf.cpp, Monitor app (Joystick.cpp/.rc/resource.h), pyvjoy (vjoymodern.cpp/.h, vcxproj, Readme, vJoyPyClient.py, a rebuilt pyvjoy.pyd). https://api.github.com/repos/njz3/vJoy/pulls/30/files
- V: The descriptor change is in `CreateHidReportDesc` in the GUI vJoyConf.cpp: `AxesHID[]` becomes pairs {page, usage}: X..Wheel stay on 0x01 Generic Desktop; Accelerator, Brake, Clutch, Steering, Aileron, Rudder, Throttle move to 0x02 Simulation Controls. The single `05 01` before the report ID is removed; before each axis it now emits `05 <page> 09 <usage>`, and `05 01` again before each hat (both hat loops). Axis order, 32-bit slots and sizes unchanged.
- V: Not touched: the driver (no .sys/hid.c change), vJoyInterface.dll, and the command-line tool `apps/vJoyConf/vJoyConfig/vJoyConfig.cpp` (the one our setup uses). So the CLI still writes the old descriptor, and the throttle/aileron swap in vJoyConfig `-a` is not fixed by #30. (File list above; the existing path of vJoyConfig.cpp from the repo tree.)
- V: Author says (comment 2025-04-21) NFS Most Wanted, Hot Pursuit, Burnout and The Crew 2 now detect vJoy as a "wheel"; a screenshot shows the "driving 2 pedals" type. Author-reported only; no independent test.
- U: Which exact byte sequence DirectInput needs for the "wheel" type (the PR body says it is the page/usage combination); not checked against Microsoft sources here.

## 2. Merged? Released? Signed?

- V: Not merged into njz3/vJoy master (PR open). njz3 latest release is v2.2.1.1 (2020-07-18); no release contains it. BrunnerInnovation/vJoy has one release, v2.2.2.0 (2023-12-19), earlier than the PR, so it cannot contain it. https://github.com/njz3/vJoy/releases , https://github.com/BrunnerInnovation/vJoy/releases
- V: code-monet/vJoy has no releases and two branches (master, usage_pages).
- V: The only binary is code-monet's sim-gamer-kit: `vjoy/bin/vJoyConf.exe` (1,000,448 bytes), a patched GUI to copy over the installed `vJoyConf.exe` (usually `C:\Program Files\vJoy\x64`). It says it needs elevation, "does not require signing to work", and no new vJoy release is expected. https://github.com/code-monet/sim-gamer-kit/blob/main/vjoy/index.md (read via the contents API). The kit has many tagged releases (0.2a .. 2.0) with no attached assets listed.
- V (by design): because only user-mode vJoyConf changed, the signed 2.2.2.0 driver stays untouched, so Secure Boot is not an issue for the driver. The patched exe is itself an unsigned file replacing a signed one (U: whether SmartScreen/Defender warns; U: whether the exe is signed at all - not checked, binary not downloaded).
- U: CLS2Sim's bundled vJoy and any sim-gamer-kit release assets: CLS2Sim ships Brunner's 2.2.2.0 (from earlier study); not re-checked here, cannot contain #30.
- U: How the sim-gamer-kit page tells the user to get the wheel setting: the guide says the patched vJoyConf.exe (sim-gamer-kit/vjoy/bin) is needed. The vjoy_configuration page does not name a vJoy version or discuss signing/Secure Boot.

## 3. Other open PRs touching the axes

- V: njz3/vJoy: only #30 (above).
- V: BrunnerInnovation/vJoy: one open PR, #2 "Fix FeederDemoCS compilation errors" (rthery, 2024-06-07), touches only SDK/c#/FeederDemoCS (csproj, app.config). Not axes.
- V: No open PR on either repo fixes the throttle/aileron swap in vJoyConfig.

## What it means for us

- Setup can keep installing signed 2.2.2.0; the fix would be a user-mode descriptor change. Our setup writes the device through vJoyConfig (CLI), which #30 does not patch, so using the fix would mean either our own descriptor writer (registry `HidReportDescriptor`), or shipping/replacing vJoyConf.exe from an unreviewed fork build. Both are decisions for the user, not made here.
- The wheel type is still only reported by the PR author; a Windows 11 test-machine check is still needed.
