# Driver setup in the installer (planning, 2026-11-21)

Status: planning only. No spec, code or build until the user says build.
Background: claude/audits/2026-11-20-yajb-code-comparison.md (how YAJB does it).

## User's idea

Tick boxes in our installer for vJoy, ViGEmBus and HidHide; download and
install each with a percentage indicator; scripts set them up the way we
expect.

## Proposed shape (agreed in discussion, not yet spec)

- One setup page listing vJoy, ViGEmBus, HidHide: installed (version) or not;
  missing ones ticked by default; installed ones left alone.
- Each driver installer checked against a fixed SHA-256 before it runs.
- Our installer stays per-user (PrivilegesRequired=lowest); one elevated helper
  script installs all ticked drivers, so one admin prompt.
- Restart offered at the end if a driver asks for it.
- A failed driver step never stops Gremlin's own install; setup says which
  driver is missing and the app's existing checks point to it.
- Uninstalling Gremlin leaves the drivers installed.
- Per-driver setup: vJoy needs vJoyConfig (see 2c); ViGEmBus needs none (pads
  made at runtime); HidHide needs none (gremlin/ui/hidhide.py set_whitelist
  adds Gremlin and games; hiding is done in the app).

## User's answers (2026-11-21)

1. c) Bundle the driver installers AND download only if a newer version is
   listed.
2. c) vJoy: a choice in setup (number of devices and their layout).
3. b) A driver that is installed but older than ours: offer an update tick box.
4. b) Newer versions: setup asks each driver's own GitHub releases page. No
   fingerprint is known in advance, so a downloaded file runs only if its
   Windows digital signature is valid and the signer is the expected one
   (vJoy: Brunner Elektronik AG; ViGEmBus and HidHide: Nefarius Software
   Solutions e.U.). Otherwise setup uses the bundled copy. Bundled copies keep
   their fixed SHA-256 check.
5. a) vJoy page: presets "1 device, full" (8 axes, 128 buttons, 4 hats;
   default), "2 devices, full", and Custom (number of devices, each one's axes,
   buttons, hats). Existing devices are shown as they are and changed only if
   the user edits them, with a warning that running games lose the sticks.
6. a) Update box for an older driver starts unticked, labelled
   "update available: old -> new".
7. a) The same page also lives in the app as Tools > Drivers (status, update
   boxes, vJoy presets), using the same admin helper script.
8. a) HidHide update in two halves: setup uninstalls the old HidHide and asks
   for a restart; Gremlin installs the new one on its next start and asks for
   the second restart. User's condition: setup AND Gremlin show a prompt
   telling the user what is being done and when, before each step (draft
   wording in the chat 2026-11-21, approved as 9a).
9. a) Prompt wording approved as drafted:
   Setup: "HidHide update, step 1 of 2" (removes old, explains the restart and
   that devices aren't hidden until done) [Continue] [Skip HidHide update];
   progress "Removing HidHide <old>..."; "Restart needed to continue the
   HidHide update" [Restart now] [Restart later].
   Gremlin next start: "Finish the HidHide update, step 2 of 2" (installs new,
   Windows asks for admin) [Install now] [Later]; progress "Installing HidHide
   <new>..."; "HidHide is installed: one more restart" [Restart now]
   [Restart later]. Choosing Later leaves a Home line "HidHide update not
   finished: devices aren't hidden" with [Finish update] until done.
10. a) Same pattern for every driver step (vJoy, ViGEmBus, HidHide installs and
   updates, vJoy device setup): say what and when before, progress during,
   result and any restart after.

## Facts checked

- YAJB bundles vJoySetup 2.2.2.0 (5.3 MB, signed Brunner Elektronik AG, MIT,
  Shaul Eizikovich) and HidHide 1.5.230 x64 (8.1 MB, signed Nefarius Software
  Solutions e.U., MIT). Not ViGEmBus.
- Our installer installs no drivers today; ships vjoy/vJoyInterface.dll and
  vigem/ViGEmClient.dll only.

11. a) Driver tests run in a Hyper-V virtual machine on the user's PC (user
   turns Hyper-V on; Windows 11 guest; checkpoints to reset to clean).

12. a) Gremlin Device Helper (page 12 S25, "the only part of Gremlin with
   administrator rights") gets the driver jobs; the installer and Tools >
   Drivers both use it. No separate admin script or program.

13. a) Spec statements approved: written 2026-11-21 into 01 S187-S192
   (D-01-DRIVERS), 06 S185-S188 (D-06-DRIVERS), glossary "Drivers", map README
   counts. Page 12 S25 (helper driver jobs, job/result file for setup,
   vJoyConfig read-back) was held, then written 2026-11-21 (15a) as S25
   changed, S25a, S25b (D-12-HELPER-DRIVERS). It was held because page 12 holds the
   uncommitted S41 Screen Saver Mode changes, which stay untouched until the
   user decides on them. Text to write then: S25 keeps "the only part with
   administrator rights" and gains install/update a driver from a file
   (re-checks the fingerprint or signature itself), remove HidHide (first half
   of its update), set up vJoy devices; reports progress, result and restart;
   S25a setup passes a job file and reads a result file (Gremlin keeps the
   pipe); S25b vJoy setup reads the device back and fails with a message on a
   mismatch.
14. a) Driver-missing messages (vJoy missing, ViGEmBus line in Xbox Setup) get
   an Open Drivers link to Tools > Drivers, replacing the Download link
   (06 S188).

## Follow-up answers 2026-11-21 (after the build)

- 1a: setup's Drivers page gets the vJoy device choice too (01 S187 changed).
- 3a: vJoy setup uses -l so the driver restarts once (12 S25b).
- 4a: devices above the new count are deleted with -d (12 S25b).
- 5a: removing HidHide always asks for the restart (06 S186).
- 2a: the program's own silent update runs no driver jobs (01 S187).
- 6a: Tools › Drivers keeps the job file; the private channel stays SSM-only (12 S25a).
- Go 2026-11-21 04:25: build 1a, 3a, 4a, 5a.
- 27a (2026-11-21 07:25, after test 6 showed vJoy devices survive an update): vJoy older than 2.2.2.0 stays an optional, unticked "update available" (6a unchanged); Gremlin keeps accepting vJoy from 2.1.8. No spec change.

## Build batch (built 2026-11-21 up to testing; contract driver-setup-contract.md)

1. Driver setup in the installer: 01 S187-S192 (DRV-1).
2. Tools > Drivers, the HidHide two-half update, Open Drivers links:
   06 S185-S188 (DRV-2).
3. Gremlin Device Helper driver jobs: 12 S25 changed, S25a, S25b (DRV-3).
4. Screen Saver Mode trace: the restart line names its source, 12 S16a
   (SSM-RESTART-SOURCE; user 2026-11-21: 19 "add it to the changes batch we
   are about to begin").
Tests in the Hyper-V virtual machine (11a) for items 1-3.

## Facts checked 2026-11-21 (3 research helpers + lead)

Inno Setup (lead, local): 6.7.3 at %LOCALAPPDATA%\Programs\Inno Setup 6 (found
by installer/build_installer.ps1). CreateDownloadPage gives a download page with
progress (Examples\CodeDownloadFiles.iss); [Files] has a download flag. Inno's
own signature check (ISSig) is not Authenticode, so the signer check goes in the
admin helper script (PowerShell Get-AuthenticodeSignature).

vJoy:
- Maintained build: github.com/BrunnerInnovation/vJoy, newest v2.2.2.0
  (2023-12-19), asset vJoySetup_v2.2.2.0_Win10_Win11.exe (5,302,312 bytes);
  /releases/latest API works. Signer Brunner Elektronik AG (checked locally on
  YAJB's copy). Brunner says it won't invest heavily in maintenance.
- Inno Setup installer: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /LOG=.
  Exit 0 ok; 8 = restart needed (custom); 109 = driver check failed (from the
  script, untested). May finish after a restart via RunOnce "Phase 2".
- Upgrades in place: silently runs the old uninstaller first.
- Limits (SDK public.h): 16 devices, 16 axis names, 128 buttons, 4 hats
  (continuous or discrete). Our vjoy/ wrapper uses the 8 axes X..SL1, so the
  "full" preset stays 8 axes.
- vJoyConfig: `vJoyConfig <id> [-f] -a x y z rx ry rz sl0 sl1 -b 128 -p 4`,
  `-d <id>` delete, `-t` report, `enable on|off`. Exit code is 0 even on bad
  arguments, so the script must read the result back (-t) to know it worked.
  At C:\Program Files\vJoy\x64\vJoyConfig.exe on this PC.
- Installed version: HKLM ...\Uninstall\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1
  DisplayVersion (this PC: 2.1.9.1, older than 2.2.2.0, so the update box
  would show here). Publisher says Shaul Eizikovich, so it is no signer check.

ViGEmBus:
- Retired: repo archived 2023-11-02 (trademark conflict over "ViGEm"); last
  release v1.22.0, asset ViGEmBus_1.22.0_x64_x86_arm64.exe (6,278,576 bytes).
  The newer-version download (answer 4) never finds anything; bundle 1.22.0.
- BSD-3-Clause: bundling allowed; ship its licence text.
- Update over an older version: release notes say run setup twice.
- Silent switches not documented officially; others report /exenoui /qn
  /norestart (MSI wrapper); exit 0/3010/1641. Must test.
- This PC: service ViGEmBus running, ViGEmBus.sys 1.21.442.0 (Microsoft
  hardware-compatibility signature on the .sys), Programs entry "ViGEm Bus
  Driver" (MSI {966606F3-2745-49E9-BF15-5C3EAA4E9077}).

HidHide:
- MIT; github.com/nefarius/HidHide not archived but "no capacity for major
  works"; newest v1.5.230.0 (2024-05-11), asset HidHide_1.5.230_x64.exe
  (8,078,016 bytes); /releases/latest API works. Signer Nefarius Software
  Solutions e.U. (checked locally); future builds may say "Nefarius Software
  Solutions", so match the start of the name.
- Advanced Installer (MSI in an exe); master has moved to WiX, so switches may
  change. Likely /exenoui /qn /norestart (untested). Forces a restart on
  upgrade.
- Official update steps: uninstall, restart, install, restart.
- The installer doesn't touch the allowed-apps or hidden-device lists. Whether
  the lists survive uninstall + reinstall: untested.
- Installed version: HKLM\SOFTWARE\Nefarius Software Solutions e.U.\HidHide
  Version (this PC: 1.5.230). Service HidHide, plus a HidHideWatchdog service
  and an updater (nefarius_HidHide_Updater.exe) whose behaviour is unchecked.

## Still to test (on a test machine, never this PC)

- Silent install and the exit codes of all three installers.
- vJoy 2.1.9.1 -> 2.2.2.0 upgrade, with and without a restart.
- ViGEmBus "run twice" update; HidHide uninstall/reinstall keeping the lists.
- vJoyConfig create and read-back on 2.2.2.0, including 128 buttons.
- What the HidHide updater does.
