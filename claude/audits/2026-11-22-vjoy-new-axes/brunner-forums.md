# Brunner / community forums on vJoy (FORUMS scout, 2026-11-22, 03:05-03:06 by the clock)

Read-only web research. "Verified" = read on the cited page; "unverified" =
search-engine summary only or secondary source. No Reddit thread on this
topic was returned by any search (r/hotas etc. not indexed for these terms).
Pages that refused fetching: forum.dcs.world (HTTP 403, so the DCS threads
251148 pages 2/3/6/7 were seen only as search snippets).

## 1. How Brunner customers use vJoy with CLS2Sim

- CLS2Sim ships its own vJoy installer in a "Virtual joystick driver" folder;
  Brunner's FAQ says to use only that one and, if it hangs, wait about 2 min
  then force-close. Verified: https://helpdesk.brunner-innovation.ch/faq/single-faq/are-your-products-compatible-with/
- Purpose (a): routing the main axes (pitch, roll, yaw, collective) to a
  virtual joystick when an aircraft model fights CLS2Sim for control; needs
  "Suppressed Actions" and "Force map vJoy axes" in CLS2Sim. Same FAQ page, verified.
- Purpose (b): buttons. Staff (28 Feb 2020) said vJoy for the CLS-E yoke is
  "only used for buttons mapped in simulator"; not needed for CLS-E MKII, NG
  Yoke, Rudder, Joystick. Verified: https://forum.brunner-innovation.ch/forums/topic/1695/
  A 2024-era thread also says vJoy must be installed for yoke buttons in MSFS;
  its poster saw the installer "hang", then it worked after a restart. Verified:
  https://forum.brunner-innovation.ch/forums/topic/assign-yoke-buttons-in-msfs2020/
- Axis advice conflicts over time: 2020 staff said tick "Force map vJoy axes"
  (CLS2Sim 4.26.2+); current FAQ says do NOT map principal axes or vJoy axes
  in MSFS. Verified (the two pages above).
- Sims named: MSFS 2020/2024, X-Plane, Prepar3D, FSX, DCS, ProSim (CLS2Sim list);
  DCS and IL-2 can use a separate DirectInput FFB mode that bypasses CLS2Sim
  and vJoy. Verified (FAQ page).
- Old CLS2Sim bundles were vJoy 2.0.5 / 2.1.9.x; DCS users in 2019 needed
  APP_VJOY_FORCE_ENABLE_AXES=true in connection.stx. Unverified (DCS page 403;
  search snippet of forum.dcs.world/topic/251148).
- Nothing found saying which axes customers tick, or any use of axes 9-16.

## 2. vJoy 2.2.2.0 specifically

- Brunner's GitHub release v2.2.2.0 (19 Dec): driver and installer EV-signed,
  Microsoft attestation signing, "works on Win10 and Win11"; the only release;
  notes mention no axes. Verified: https://github.com/BrunnerInnovation/vJoy/releases
- Brunner's README: forked from njz3/vJoy; Brunner paid for the signing so
  Windows 11 users get njz3's FFB work; "does not intend to spend a lot of
  resources" maintaining it; only Windows 10 and 11 supported. Verified:
  https://github.com/BrunnerInnovation/vJoy
- Windows 11 background: njz3 issue 11 "Vjoy failed to install Win 11"
  (closed Aug 2023; only a test-signed build was possible then). njz3 issue 9:
  njz3 wrote "Issue fixed in latest source code of v2.2.2.0" (17 Aug 2023);
  others said test-signed 2.2.x installed but did nothing and went back to
  2.1.9.1. Verified: https://github.com/njz3/vJoy/issues/11 and /issues/9
- Search summaries: 2.2.1 freezes at end of install for one MSFS user; test-sign
  mode blocks iRacing; no post found reporting a 2.2.2.0 hang, BSOD, or
  Gremlin/GremlinEx/HidHide clash. Unverified (snippets; DCS 403).
- Gremlin + HidHide is the usual pairing (HidHide hides the real stick): Joystick
  Gremlin FAQ; FFFSake guide recommends Brunner's signed fork plus HidHide.
  Verified via search result text only (not fetched): treat as unverified.

## 3. Brunner staff on vJoy plans

- Dec 19 2023 and Apr 8 2024, account BrunnerInnovation (signing as Brunner
  Elektronik AG) on shauleiz/vJoy issue 57: built signed v2.2.2.0 from njz3's
  master, tested on several Win10/11 PCs "with great success"; offered another
  certification round for a v2.2.2.1 if njz3 merges fixes; dropped Windows 7
  (could not build njz3's w7_pr3 branch with old tools). Verified:
  https://www.github.com/shauleiz/vJoy/issues/57
- No statement about new axes, or any roadmap, found. Verified absent on the
  pages read; Brunner's help pages say nothing about 16 axes.

## Takeaways for the study

- Brunner's own use is buttons and routing the four principal axes: nothing
  needs axes 9-16, supporting the "no known user of the new axes" finding.
- 2.2.2.0 exists mainly to be a signed driver; the new axes come from njz3's
  code, not from a Brunner feature.
- Brunner customers get vJoy via CLS2Sim's installer (older version) unless they
  install 2.2.2.0 themselves; so a Brunner user may have vJoy 2.0.5-2.1.x
  next to our program. Unverified which version current CLS2Sim bundles.
