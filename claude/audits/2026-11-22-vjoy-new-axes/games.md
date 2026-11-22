# vJoy 2.2's new axes: which games, engines and APIs can see them? (scout GAMES)

Date 2026-11-22, read-only web study. Agent GAMES, 02:59-03:01. Builds on
`windows.md` (DirectInput table, dill, SDL source); not repeated here.

Labels: **verified** = read in the cited source (quote or line given);
**unverified** = forum claim, inference, or nothing found. No game's own source
or developer statement was found that names a per-device axis count, so most
per-title rows are inference from "it uses DirectInput".

## 1. Summary table

| Game / engine / API | Input path on Windows | Max axes per device | Sees the new usages? | Label |
|---|---|---|---|---|
| DirectInput, `c_dfDIJoystick2` | DirectInput | 8 (X Y Z Rx Ry Rz Sl0 Sl1) | Only as one of the 8 classic slots (Steering->X, Accel->Y, Wheel->Z, Brake/Rudder->Rz, Throttle->Slider); Clutch, Aileron dropped | verified (windows.md; Wine dev: "most games use c_dfDIJoystick2 which can support up to 8 absolute axes", https://list.winehq.org/archives/list/wine-gitlab@list.winehq.org/thread/BBDAWH5CFLEACY2AK3VECO6KGPAUKA2Z) |
| DirectInput, custom data format | DirectInput, app builds its own format from EnumObjects | more than 8 possible in principle | GUID_Unknown objects readable only by such an app | unverified (no game found that does this) |
| X-Plane 10.10+ / 11 / 12 | own low-level reader: "talk directly to the devices" (https://developer.x-plane.com/?p=4404) | not stated | not stated | path verified; count and usages unverified |
| MSFS 2020 / 2024 | DirectInput (community) | 8 | no (as DirectInput) | unverified; MSFS 2024 forum: vJoy split "will only work as long as 8 axes ... are sufficient" (https://forums.flightsimulator.com/t/msfs2024-control-binding-interface-is-confused-by-multiple-devices/675067) |
| DCS World | DirectInput | 8 | no | unverified; DCS forum answer "more than 8 ... create more Vjoy" (https://forum.dcs.world/topic/313300-joystick-gremlin-i-want-to-add-more-axis-please-help); old thread "why not update the direct x axis limit" (https://forum.dcs.world/topic/49975-why-not-update-the-direct-x-axis-limit/) |
| IL-2 Great Battles | DirectInput | 8 | no | unverified (forum threads on device limits only) |
| Falcon BMS | DirectInput | 8 | no | unverified (BMS forum: user claims "up to 8 axis and 128 DX buttons per device", https://forum.falcon-bms.com/post/20700) |
| Star Citizen | DirectInput (community) | 8 assumed | no | unverified (nothing per-axis found; only a 50-button claim) |
| Elite Dangerous | DirectInput | 8 assumed | no | unverified (nothing found) |
| iRacing, AC / ACC, rFactor 2 / LMU, BeamNG, ETS2, AMS2 | DirectInput (common knowledge for wheels) | 8 assumed | no | unverified (no title-specific source found) |
| SDL2 / SDL3 (non-Xbox devices) | DirectInput | 8 | only via classic GUIDs; others "not an axis we can grok" | verified (windows.md, SDL source) |
| Godot 4.5+ | SDL3 | as SDL3: 8 | as SDL3 | path verified: "Since Godot 4.5, the engine relies on SDL 3" (https://docs.godotengine.org/en/4.5/tutorials/inputs/controllers_gamepads_joysticks.html); count inferred |
| Unity Input System | own HID reader (Windows, macOS, UWP) | no limit stated: "any number of Controls as reported by the Device's HID descriptor" | "adds Controls for all further HID axis ... elements"; mislabelled Generic-Desktop 0xB0-0xC8 handling not documented | verified (https://docs.unity3d.com/Packages/com.unity.inputsystem@1.8/manual/HID.html); usage handling unverified |
| Unreal RawInput plugin | Raw Input + HID parser | key set Axis1..Axis24 | unknown | key set verified (https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/RawInput/FRawInputKeys); a 2025 user sees only 3 axes work (https://forums.unrealengine.com/t/unreal-engine-raw-input-arduino-hid-joystick-only-detects-3-axes/2714689) |
| Windows.Gaming.Input RawGameController | HID | `AxisCount` with no stated limit | unknown | unverified (https://learn.microsoft.com/en-us/uwp/api/windows.gaming.input.rawgamecontroller.axiscount); a Jan 2026 Wine commit "Enforce axis usage mapping for HID devices" suggests WGI maps by usage, details not readable (bot wall) |
| Raw HID (HidP_GetValueCaps) | HID | all 16 | yes, as raw page/usage numbers | verified by mechanism (windows.md) |

## 2. Generic-Desktop 0xB0-0xC8 (undefined on that page)

- **Unverified, nothing found.** No report, doc or forum post was found about
  what Windows, joy.cpl or any game does with usages 0xB0-0xC8 declared on the
  Generic Desktop page. The Microsoft "Axis Selection" table (windows.md) keys
  Steering/Accelerator/Brake/Rudder/Throttle on the Simulation page, so with
  vJoy's page 0x01 they would most likely be GUID_Unknown in DirectInput
  (inference, needs a live read on the test machine).
- **Related, verified.** The sim-gamer-kit guide for a patched vJoyConf that
  adds Steering/Accelerator/Brake says "DirectInput ignores the additional
  axes" beyond 8, that the setup "allows vJoy to be detected as a wheel by
  DirectInput", and "I couldn't get the "clutch" to work with DirectInput"
  (tested on "DirectInput8 games on Windows 10 and 11";
  https://code-monet.github.io/sim-gamer-kit/fffsake/vjoy_configuration/).
  Which vJoy build and which usage page it used is not stated.

## 3. vJoy devices with more than 8 axes read successfully

- **Nothing found.** No report of X-Plane or any other game reading a 9th-16th
  axis from one vJoy device. Every forum answer found (DCS, MSFS, BMS, IL-2)
  says to use more vJoy devices instead. Unverified as a negative.

## 4. Bottom line

All flight and racing sims checked read joysticks through DirectInput (per
community reports; no developer statement found), so they get at most 8 axes
and the new usages either fall onto a classic slot or disappear. Only engines
with their own HID reader (Unity Input System, Unreal RawInput, raw HID, maybe
X-Plane and RawGameController) could see more than 8, and none is documented to
understand vJoy's Generic-Desktop 0xB0-0xC8 numbers. Nothing found changes the
README conclusion: more vJoy devices stay the way to get more axes. Worth a
live check later on the test machine: X-Plane 12 and joy.cpl with a vJoy 2.2.2
device that has 9+ axes.
