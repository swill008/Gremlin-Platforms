# How people use vJoy 2.2's new axes (web study, agent USERS, 2026-11-22)

Read-only web search, about 8 min. Result: public evidence is thin. No source
found describes anyone using Wheel/Accelerator/Brake/Clutch/Steering/Aileron/
Rudder/Throttle as separate axes beyond the first 8. Labels: V = verified by
a fetched page, U = unverified / inferred.

## Who uses them, for what

- V: The njz3 arcade feeder (vJoyIOFeederWithFFB, Arduino board for racing
  cabinets) targets vJoy 2.2.2. It maps steering to X, accelerator to Y, brake
  to Z, clutch to RX, and says only 3 or 4 vJoy axes are useful. So even the
  fork author's own tool uses classic axis places, not the new names.
  https://github.com/njz3/vJoyIOFeederWithFFB
- V: Its cabinet targets are Sega Model 2/3 style clones, Naomi/Lindbergh
  (Outrun 2, Initial D), Teknoparrot, MAME/Supermodel lamp outputs. Force
  feedback is sent as constant torque. Same page.
- U (inferred): njz3 added the driving-named axes so the device looks like a
  wheel to arcade/racing software. No page found states his reason; the
  njz3/vJoy README and the Brunner 2.2.2.0 release page say nothing about
  the new axes (V: https://github.com/njz3/vJoy,
  https://github.com/BrunnerInnovation/vJoy/releases).
- V: A sim-racing guide (Sim Gamer Kit) uses a patched vJoyConf that enables
  Accelerator, Brake and Steering so DirectInput detects vJoy as a wheel, which
  some driving games require. It says to switch those three off if non-driving
  games misbehave. Clutch is left out of every layout because it did not work
  with DirectInput. It says Joystick Gremlin does not support its ideal
  layout (steering X, brake Y, accelerator Rz).
  https://code-monet.github.io/sim-gamer-kit/fffsake/vjoy_configuration/

## What works

- V: Games read the first 8 axes; the guide says to map one of those in-game
  as accelerator/brake/clutch/steering. Extra axes are ignored by
  DirectInput (a DirectInput limit, not HID). Same Sim Gamer Kit page.
- V: Wheel-detection trick above (enabling the driving-named axes) is the
  one concrete benefit people report.
- U: Tools that talk to vJoy through its own API (feeders, UCR, Gremlin)
  can address all 16; no page checked per tool.

## What does not work / complaints

- V: Axes beyond 8 are invisible to games (Sim Gamer Kit page above). A DCS
  forum post reportedly says flight sims did not see a second set of 8 axes
  on a second stick, while a test app did (seen only as a search summary, the
  page itself returned 403: U for details).
- V: Clutch (as a named axis) did not work with DirectInput (Sim Gamer Kit).
- V: Open njz3 / Brunner issues are about install, BSOD, driver/DLL version
  mismatch (Brunner #11 "driver 222 does not match DLL 218"), Xbox-style
  detection in MSFS 2024 (#29, #31). None is about the new axes, joy.cpl, or
  axis visibility. https://github.com/BrunnerInnovation/vJoy/issues
- V (one 2.2.1.1 report): vJoy Monitor showed 8 axes; names/directions of
  axes have no consensus. https://blekenbleu.github.io/Windows/HID/vJoy
- U: Windows 11 reports that 2.2.1 would not load the driver while 2.1.9.1
  worked (search snippet of njz3 issue 11; not fetched).
- Not found: any Reddit, SourceForge forum or SimHub/x360ce thread about the
  new axes (search engine returned none; Reddit not fetchable).

## Workarounds seen

- V: tick all 8 classic axes even if fewer are used (some guides);
  only ticked axes are visible to Gremlin.
- V: for apps needing a "wheel", use the Sim Gamer Kit vJoyConf layout.
- V: if axes cannot be mapped in-game, hide the real device with HidHide and
  map only the needed axes through Gremlin to vJoy.

## Meaning for Gremlin-Platforms (U, lead to judge)

Real-world use is: arcade wheel feeders using X/Y/Z/RX, and a "look like a
wheel" trick using the named axes. No evidence anyone needs 9-16 as
separate, game-visible axes. Supports the lead's conclusion that 16 axes per
device would not reach games.
