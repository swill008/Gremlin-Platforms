# Brunner Elektronik AG, CLS2Sim and their vJoy fork (web scout, 2026-11-22)

Scout BRUNNER-CO, read-only web research, 03:05-03:08. Summaries in my own
words; quotes kept under 15 words. "Verified" means read on the cited page
today; "unverified" means forum talk, search-tool summaries or my inference.

## 1. The company

- Swiss, family-owned, based in Hittnau; does development, production and
  support in-house; sells controls, drives and components besides its
  simulation products. Verified: https://www.brunner-innovation.swiss/
- Simulation products listed today: FFB-G Joystick, FFB-G Rudder (and a
  bundle), CLS-P Linear Throttle, CLS-B Collective Base, a Bell 206 collective
  grip, the Simux and CLS2Sim software, and NOVASIM mixed-reality simulators
  (F35, DA42). The CLS-E NG yoke/joystick/rudder line is not on the current
  home page (it appears on third-party listings and in older forums).
  Verified (home page). CLS-E's current status: unverified.
- Markets: home flight-sim users (CLS-E, FFB-G; FFB-G Rudder about EUR 717 on a
  hardware-database listing, unverified) and professional training: drop-in
  control loading for mid-fidelity trainers, CLS-P up to full-flight-simulator
  Level D, the NOVASIM MR DA42 qualified as an EASA FNPT II and used by
  Lufthansa Aviation Training. Search-summary of the CLS-P fact sheet (scribd)
  and news; unverified beyond the home page's "Flight Training Solutions"
  section. No military customers found stated (unverified either way).
- Founding year differs by source (1968 vs 1985); the home page says over 40
  years. Unverified.

## 2. CLS2Sim and vJoy

- CLS2Sim connects Brunner force-feedback devices to sims: force by
  deflection, speed-dependent force, trim, autopilot driving the controls,
  vibration effects; up to 20 axes on the CAN network. Direct support for
  Prepar3D, MSFS and X-Plane (plugins / SimConnect); other software through
  a TCP/UDP remote interface. Verified:
  https://shop.brunner-simulation.ch/product/cls2sim/ and FAQ 265
  (https://helpdesk.brunner-innovation.ch/faq/?Display_FAQ=265: X-Plane,
  P3D, MSFS 2020, FSX, DCS, ProSim, plus a DirectX interface).
- Current version 5.9.0 (13 Mar 2026). Verified:
  https://helpdesk.brunner-innovation.ch/all-downloads/
- vJoy is an optional output: CLS2Sim can "simulating a USB HID Gamepad
  using the third-party software vJoy" (FAQ 1832). Only Pitch/Elevator,
  Roll/Aileron, Yaw/Rudder and Collective can be routed to vJoy; you install
  the vJoy that ships in CLS2Sim's folder (other builds not supported), tick
  "Force map vJoy axes" and "Suppressed Actions", then map the vJoy axes in
  the sim like any USB axis. Verified:
  https://helpdesk.brunner-innovation.ch/faq/?Display_FAQ=1832 and
  https://helpdesk.brunner-innovation.ch/faq/?Display_FAQ=3222
- Which vJoy axis each goes to and which device number: not published on the
  FAQ pages. The changelog says toe brakes go to vJoy axes 5 and 6 (v4.31.3,
  2022), and unassigned buttons go out as vJoy buttons (v2.7, 2014). Verified:
  https://helpdesk.brunner-innovation.ch/wp-content/downloads/software/cls2sim/CLS2Sim_changelog.txt
- New 2.2 axis types (Rudder, Throttle, Aileron, Brake...): no sign that
  CLS2Sim uses them. The FAQ talks of "vJoy axes" mapped as plain USB axes,
  and toe brakes on axis numbers 5/6 point to the classic places. Inference,
  unverified; CLS2Sim's code is closed.
- Force feedback through vJoy: not used by CLS2Sim per its docs. For
  DirectInput-FFB sims (DCS, IL-2) Brunner offers a DirectX FFB mode on some
  devices, set with its USB config tool, which "bypasses CLS2Sim completely"
  (FAQ 3222). Verified. Older forum posts (2018-2023) describe DCS users
  binding vJoy axes and getting unreliable or no FFB; unverified (DCS forum
  refuses automated reads).
- vJoy version history in CLS2Sim (changelog, verified): 2.0.5 (2015, for
  Windows 10), 2.1.9 (2019), 2.2.1.1 then reverted to 2.1.9.1 (June 2023),
  2.2.2.0 (v5.7.0, 18 Dec 2023, "vJoy requires Windows 10 or newer"), a fix
  so the default vJoy config sets the right button/axis count (v5.8.12, July
  2025).
- For MSFS, Brunner tells users not to map vJoy axes at all (axes go by
  SimConnect). Verified:
  https://helpdesk.brunner-innovation.ch/faq/?Display_FAQ=2969

## 3. Why they forked and signed vJoy 2.2.2.0

- Stated reason: njz3's (Benjamin's) 2.2.x FFB work could not be installed on
  Windows 10/11 because of driver signing; vJoy "has proven to be a valuable
  tool for us", so Brunner sponsored signing. Release notes: driver and
  installer EV-signed and attestation-signed via Microsoft's partner program;
  Windows 10 and 11 only. Verified: https://github.com/BrunnerInnovation/vJoy
  and its releases page.
- Brunner's own commits (Michael Menzi, 14-19 Dec 2023) are build scripts, a
  ".NET 4.8" bump, an installer Windows 10 minimum and the readme; the driver
  changes (FFB fixes, 16 axes) are njz3's. Verified (commit list); Menzi's
  employer is my inference from the repo owner.
- Timing matches CLS2Sim 5.7.0 (18 Dec 2023) shipping vJoy 2.2.2.0, so their
  customers were the reason in practice. Inference, unverified.
- Future: Brunner does "not intend to spend a lot of resources" on it; it
  "might" sign again for important fixes. Verified (README). Only one release
  exists.
- The UCR (another remapper) failure on 2.2.x was blamed on its old
  vJoyInterface DLL, since FFB fixes changed the driver API. Search summary
  of a njz3 issue; unverified (not found on issues 9 and 11 when read).

## 4. CLS2Sim + vJoy + other remappers

- Brunner's FAQ names no remapper (no Joystick Gremlin, UCR etc.); its own
  answer to unsupported sims is plain USB, CLS2Sim's vJoy routing, or the
  DirectX FFB mode. Verified (FAQ index https://helpdesk.brunner-innovation.ch/faq/).
- Community: BrunnerDX (jmriego) talks to CLS2Sim and uses an Arduino to
  appear as a DirectX FFB joystick, avoiding vJoy; it reads X/Y only.
  Verified: https://github.com/jmriego/brunnerdx
- No report found of Brunner owners running Joystick Gremlin on CLS2Sim's
  vJoy device. Users with several vJoy feeders hit device/version clashes
  (CLS2Sim pins its bundled vJoy build). Unverified.

## Relevance for us (scout's view)

- A CLS2Sim user has a vJoy device fed by CLS2Sim; if we also feed vJoy, the
  two must use different devices (CLS2Sim's device number is not published).
- CLS2Sim ships and installs vJoy 2.2.2.0 itself, so Brunner owners are likely
  to be on 2.2.2.0, but nothing shows CLS2Sim using the 8 new axes.
