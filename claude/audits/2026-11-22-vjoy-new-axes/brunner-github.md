# Brunner Elektronik AG on GitHub (BRUNNER-GH, 2026-11-22, 03:05-03:12)

Source: `gh api` (worked, 4936 calls left) and WebFetch of github.com. "V" = verified
from the cited page/API; "U" = unverified.

## 1. Accounts and repos
- V: github.com/BrunnerInnovation (User account, created 2019-03-15, 4 followers; description "Development,
  production and customer services at the highest level. Innovative and strong simulation product portfolio").
  Only 3 repos: `vJoy` (fork of njz3/vJoy), `mfs2020_simconnect_axis_set_bug` (2020-09, minimal C# demo of a
  SimConnect AILERON_SET bug with a USB rudder pedal; no vJoy use), `RealTimeGraphX` (fork of royben/RealTimeGraphX, WPF graphs).
- V: github.com/Brunner-Elektronik-AG is a separate Organization ("Brunner Elektronik AG"), 0 public repos.
- V: no SDK, no CLS2Sim plugin, no sample or tool using vJoy besides the vJoy fork itself. Members of both are not listed publicly (API 404).
- U: whether Brunner's CLS2Sim software uses vJoy; nothing on GitHub says so.

## 2. BrunnerInnovation/vJoy (https://github.com/BrunnerInnovation/vJoy)
- V: fork of njz3/vJoy, 325 commits on master, 230 stars, 12 forks, GitHub Discussions off, last push 2024-06-07.
- V README: Brunner sponsored driver signing so Windows 10/11 users get the FFB features njz3 added; "Brunner does
  not intend to spend a lot of resources maintaining and improving this project"; Windows 10/11 only; build notes (VS2022, WDK, Inno Setup 6, EV cert).
- V Releases: one only, v2.2.2.0 (2023-12-19, by BrunnerInnovation): "Driver and installer are signed with an EV certificate and
  went through the attestation signing process in the Microsoft Partner program. Works on Win10 and Win11."
- V Brunner-authored commits: only "Michael Menzi" (9 commits, 2023-12-14 to 12-19: build scripts, Brunner setup
  build script, .NET 4.8 target, solution/project configs, gitignore, installer MinVersion Win10, README disclaimer + release link).
  No driver, axis, HID descriptor or FFB code changed by Brunner; all of that (2.2.2.0, 16 axes) is njz3's (2023-08-16, "Set version to 2.2.2.0").
  Menzi is a commit author name only; whether he is a Brunner employee is U (not checked, no personal details recorded).
- V Issues: 12 issues (11 open, #1 closed) and 1 PR (#2, rthery, FeederDemoCS compile fix, open since 2024-06-07).
  Titles: #1 install hangs Win11; #3 update SourceForge / single repo; #4 identical GUID/DeviceID; #5 use a real USB vendor ID;
  #6 Windows on ARM; #7 missing registry values; #8 Joy and opentrack; #9/#10 install fails; #11 driver 222 vs DLL 218; #12 BSOD.
- V: Brunner staff replied to NONE. Every comment is from users or njz3 (#3, 2025-01-20: 2.1.9.1 came via Justin Shafer, not him).
  author_association of all commenters is NONE. So no Brunner statement exists on the new axes, FFB, signing plans or DIJOYSTATE/axis visibility
  beyond the README sentence above. No Discussions.
- V Issue #12 (davevan2, opened 2026-11-08, no comments): BSOD 0x3B in `vJoy_EvtDeviceFileCreate` (driver/sys/rawpdo.c) when the raw PDO is opened
  with no `\Device_NNN` name; affects 2.1.9 and 2.2.2.0; trigger in 4 dumps was Git-for-Windows/MSYS2 `find.exe` doing `find /`
  (stats /proc/sys/Device/...); also reachable by any standard user (local DoS). Suggested fix: NULL/length check on the file name and bound id to 1..max.
  This matches our own `find /` blue screens (memory: no-whole-disk-find). Repro not executed by the reporter. Issue #1 (hang) closed by reporter, 2024-03-17.
- V: nothing found in issues about the throttle/aileron swap in vJoyConfig, nor new axes.

## 3. Forks
- V: of 12 forks, active ones: uitcis/vJoy (pushed 2026-08-16; merges upstream, adds Chinese README and "generic device auto-management" to avoid
  conflicts with other game controllers; 17 commits ahead of Brunner master; no releases). Marmalade118 (2025-02-23, 0 ahead), wcde (2024-11-29, 0 ahead),
  Tathanito/io4_to_vJoy (2024-12-12, an IO4 feeder, not checked). The rest last pushed 2024-06-07 (= Brunner's push).
- V: no fork has releases; none touches the BSOD (#12) per the commit list read for uitcis (only its top 8 commits read, so U for the full diff) or the swap.
- U: other forks of njz3/vJoy or other vJoy lines (e.g. jshafer817's 2.1.9.1) were not surveyed here.

## 4. People (usernames only)
- Org/repo owners: BrunnerInnovation, Brunner-Elektronik-AG. Commit author name "Michael Menzi" (no GitHub login linked).
- Upstream: njz3 (author of 2.2.x), shauleiz (original), jshafer817 (2.1.9.1). Issue authors: davevan2, SaiMorphX, SolarSupremacy, Lazyboy38, Tpaelo,
  psouza4, shyakocat, fredemmott, SciFi-Bob, TinkerTob, rthery, uhansla.

## Conclusion
Brunner is only a signing sponsor and release publisher of njz3's code; it has never answered an issue and says it will not maintain it. Questions about the
new axes must be answered from njz3's source (vjoy.md), not from Brunner. Issue #12 is worth reading for our own crash. 
