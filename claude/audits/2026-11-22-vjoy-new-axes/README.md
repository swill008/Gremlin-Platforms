# vJoy 2.2's 8 new axes: planning study (2026-11-22)

Asked by the user ("lets start the new axes planning", to-do 0e). Three
read-only scouts, 02:44-02:49: `code.md` (our code), `vjoy.md` (vJoy 2.2.2.0
source), `windows.md` (Windows, DirectInput, dill, games).

## Findings

- Games: flight sims and SDL read vJoy through DirectInput, which has 8
  axis places (X Y Z Rx Ry Rz Slider0 Slider1). More than 8 axes on one device
  is not seen by them (verified: Microsoft mapping table via Wine, SDL source;
  per-sim reports widespread, not checked per title).
- vJoy puts all 16 axes on the Generic Desktop page (0x01), although
  0xB0-0xC8 are Simulation Controls numbers; only Wheel (0x38) is a real
  Generic Desktop axis (verified, vjoy.md). What Windows makes of the other
  seven is unverified; the Simulation-page mapping in windows.md (Throttle ->
  slider, Rudder/Brake -> Rz) likely does not apply because of this.
- vJoyConfig 2.2.2.0 swaps throttle and aileron in `-a` (verified, vjoy.md).
- Driver 2.1.9 (the user's PC) cannot have the new axes: 8 report slots, a
  misspelt registry value name (`HidReportDesctiptor`), its vJoyConfig
  ignores the new names (verified, vjoy.md).
- dill (our input library) keeps only the 8 classic places (verified in the
  public v1.5 source; the shipped v2.0 source is not published).
- Our code: profiles store an axis as a number 1-8, so 9-16 need no format
  change; the vJoy module raises at axis 9+, matching compares axis counts,
  setup's row has no room for 16 ticks, three separate 8-name tables
  (code.md).

## Conclusion (lead)

Sixteen axes on one vJoy device would not reach games, would not work on
driver 2.1.9, and the new names are probably not even seen as throttle /
rudder by Windows. Still unverified: what Windows 11 with driver 2.2.2.0
lists for a device with the new axes (a test-machine check).

## Web research (2026-11-22, 02:59-03:02)

Three more scouts: `users.md` (what people do), `tools.md` (other
remappers), `games.md` (which games read more than 8 axes).

- No game found that sees more than 8 axes on one vJoy device; all common
  sims read through DirectInput (8 places). X-Plane reads devices itself,
  limit not published; no report of it working with 9+ vJoy axes.
- No other remapper supports the new axes (Joystick Gremlin, GremlinEx,
  FreePIE verified: 0x30-0x37 only); nothing to copy.
- The one real use found: ticking Steering, Accelerator and Brake so
  DirectInput reports vJoy as a wheel, which some driving games require
  (code-monet sim-gamer-kit guide; Clutch didn't work; may upset non-driving
  games). Even the vJoy fork author's own feeder uses the classic places.
- Joystick Gremlin issue 811: with vJoy 2.2.2.0, Rx/Ry/Rz show as sliders in
  joy.cpl but work in a game.

Lead: the only candidate worth building is a "racing wheel" device type
(Steering/Accelerator/Brake), needing vJoy 2.2.2.0 and a test-machine check
that Windows reports it as a wheel.

## Who makes vJoy 2.2 and how they use it (2026-11-22, 03:05-03:08)

Four more scouts: `brunner-company.md`, `brunner-github.md`,
`brunner-forums.md`, `njz3.md`.

- njz3 (arcade cabinet / force-feedback developer) wrote 2.2.0-2.2.2.0,
  including the 16 axes: commit 58a0277 (2020-03-14) "Add 8 more axes
  (mainly for driving wheels)". Their own feeder uses only X/Y/Z/Rx.
- njz3/vJoy issue #30 (2025-04, code-monet): fixes the new axes' usage page
  so NFS Most Wanted/Hot Pursuit, Burnout, The Crew 2 detect vJoy as a wheel.
  So in released 2.2.2.0 the wheel detection probably does not work; whether
  the fix is merged or released: unverified.
- Brunner Elektronik AG (Swiss, force-feedback flight controls, CLS2Sim,
  NOVASIM trainers) only paid for EV/attestation signing and built the
  installer; no driver code, no reply to any issue; little maintenance
  planned, might sign a 2.2.2.1 if njz3 merges fixes.
- CLS2Sim ships vJoy 2.2.2.0 since v5.7.0 (2023-12) and uses it optionally
  for Pitch, Roll, Yaw, Collective, toe brakes (axes 5, 6) and buttons; device
  number unpublished; no new axes, no force feedback through vJoy.
- For us: Brunner owners likely already have vJoy 2.2.2.0 with a device
  CLS2Sim uses. Our setup leaves a same-version vJoy alone and shows existing
  devices as they are (01 S187); our output would need a different device
  number from CLS2Sim's.

## Follow-up checks (2026-11-22, 03:16-03:17)

- `issue30.md`: njz3/vJoy #30 is an open, unmerged pull request (2025-04,
  code-monet) changing only the vJoyConf GUI's descriptor writer (new axes on
  page 0x02); not in any release; driver, DLL and vJoyConfig untouched (the
  throttle/aileron swap stays). Exists only as a loose vJoyConf.exe in
  sim-gamer-kit. Wheel detection is the author's own report.
- `in-use.md`: a vJoy device held by another program (e.g. CLS2Sim) is
  listed like a free one; at Run we show one "vJoy N is in use by another
  program" message and retry every 3 s; only the Home card shows the state.
  Setup and Tools › Drivers don't check: a held device is changed or deleted
  like any other, and a device removed from the list (or replaced by a
  preset) is deleted, with no warning. Spec says nothing about this (gap).
  Also: `vjoy_lost` only called by tests, its docstring cites 05 S83;
  map page 03 line 534 looks stale.
