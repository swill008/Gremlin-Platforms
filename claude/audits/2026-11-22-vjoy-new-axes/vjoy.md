# vJoy 2.2.2.0 new axes: source facts (agent VJOY, 2026-11-22 02:44-02:49)

Planning only. Read with `gh api .../contents/<path>?ref=<tag>`; nothing downloaded to
run, nothing executed. Background: `claude/audits/2026-11-21-vjoy-22-compat/notes.md`,
`code.md` (not repeated here).

"Verified" = read in the source at the cited place. "Unverified" = reasoned, not seen.
New = BrunnerInnovation/vJoy tag `v2.2.2.0`; old = jshafer817/vJoy tag `v2.1.9.1`.

## 1. Usage values for the DLL calls (verified)

| Axis | Usage our ctypes code passes | Constant (new `inc/public.h` 458-474) | Position-struct field (V3) |
|---|---|---|---|
| X Y Z | 0x30 0x31 0x32 | HID_USAGE_X/Y/Z | wAxisX/Y/Z |
| Rx Ry Rz | 0x33 0x34 0x35 | HID_USAGE_RX/RY/RZ | wAxisXRot/YRot/ZRot |
| Slider, Dial | 0x36 0x37 | HID_USAGE_SL0/SL1 | wSlider, wDial |
| Wheel | 0x38 | HID_USAGE_WHL | wWheel |
| Accelerator | 0xC4 | HID_USAGE_ACCELERATOR | wAccelerator |
| Brake | 0xC5 | HID_USAGE_BRAKE | wBrake |
| Clutch | 0xC6 | HID_USAGE_CLUTCH | wClutch |
| Steering | 0xC8 | HID_USAGE_STEERING | wSteering |
| Aileron | 0xB0 | HID_USAGE_AILERON | wAileron |
| Rudder | 0xBA | HID_USAGE_RUDDER | wRudder |
| Throttle | 0xBB | HID_USAGE_THROTTLE | wThrottle |

- `SetAxis(value, id, usage)` handles all 16 and sends the whole position with
  `UpdateVJD` itself (new `vJoyInterface.cpp` 1330-1409). No separate `UpdateVJD`
  call is needed; an unknown usage returns FALSE. (verified)
- `GetVJDAxisExist` / `GetVJDAxisMin` / `GetVJDAxisMax` all go through `GetAxisCaps`,
  which looks the usage up in the device's HID value caps by **usage number only**
  (the usage page is not compared) (new `vJoyInterface.cpp` 873-882, 925-943,
  4236-4293). So the 16 values above work for all three. Axis range is 0..0x7FFF
  (`VJOY_AXIS_MAX_VALUE`, written as LOGICAL_MAXIMUM by vJoyConfig 600-601). (verified)
- The usage numbers 0xB0-0xC8 are the Simulation Controls page (0x02) numbers from the
  HID Usage Tables (Aileron 0xB0, Rudder 0xBA, Throttle 0xBB, Accelerator 0xC4,
  Brake 0xC5, Clutch 0xC6, Steering 0xC8). That vJoy uses the Simulation numbers is
  verified by name; that they match the HID Usage Tables is from memory (unverified
  against the tables here).

## 2. HID report descriptor: order and page (verified)

The descriptor is built in user mode by vJoyConfig / vJoyConf (`CreateHidReportDesc`,
new `vJoyConfig.cpp` 534-720) and written to the registry; the driver only reads it
(new `hid.c` ~1587).

- One usage page for all axes: `05 01` Generic Desktop, set once before the axes
  (vJoyConfig.cpp 590-591). **No switch to Simulation Controls (0x02).** So Windows
  sees usages 0xB0, 0xBA, 0xBB, 0xC4, 0xC5, 0xC6, 0xC8 on the Generic Desktop page,
  where those numbers do not mean throttle/rudder/pedals (in recent HID Usage Tables
  that range on page 0x01 holds system-display / wireless-radio controls: unverified).
  Wheel 0x38 on page 0x01 is the real Generic Desktop "Wheel". (page: verified)
- Order: 16 fixed 32-bit slots, always all 16 present; an absent axis becomes a
  constant 32-bit pad (`81 01`) (vJoyConfig.cpp 608-622):
  X, Y, Z, Rx, Ry, Rz, Sl0, Sl1, Wheel, Accelerator, Brake, Clutch, Steering,
  **Aileron, Rudder, Throttle** (`AxesHID[]`, 555-571).
- The driver's input report matches that order: `HID_INPUT_REPORT_V3` = X..Dial, Wheel,
  Accelerator, Brake, Clutch, Steering, Aileron, Rudder, Throttle, 4 hat DWORDs,
  4 button DWORDs (new `driver/sys/vjoy.h` 1216-1244; filled in new `driver.c` 816-846).
- DirectInput consequence: **unverified**. With the Simulation usages on the wrong page,
  DirectInput (and Windows' joy.cpl) will not treat them as throttle/rudder/pedals; at
  best they are reported as extra unnamed axes or sliders, possibly not at all. Needs a
  machine (VM) check of what DirectInput enumerates and in which order.

## 3. vJoyConfig command line (verified, new `vJoyConfig.cpp`)

- `-a` names (case-insensitive, `cl_isParamExist`): `x y z rx ry rz sl0 sl1 wheel
  accelerator brake clutch steering throttle rudder aileron` (201-219).
- **Bug: throttle and aileron are swapped.** `WriteHidReportDescriptor` puts
  `Axes[13] = g_isAxisThrottle` and `Axes[15] = g_isAxisAileron` (779-781), but slot 13
  is Aileron (0xB0) and slot 15 is Throttle (0xBB) in `AxesHID[]` and in the driver
  report. Result: `-a throttle` creates an **Aileron** (0xB0) axis and `-a aileron`
  creates a **Throttle** (0xBB) axis. The device itself is consistent (descriptor usage,
  report slot and `SetAxis` usage agree), only the command-line name is wrong. To get a
  Throttle we must pass `aileron`, and vice versa. Rudder is correct. The GUI vJoyConf
  maps them correctly (`vJoyConf.cpp` 926-933: `AxisArr[13]` = Aileron box,
  `AxisArr[15]` = Throttle box).
- No `-a` at all: all 16 axes on (defaults `true`, 34-51).
- `-t <id>` prints `Axes:` then 16 space-separated tokens in this order, `-` when absent:
  `X Y Z Rx Ry Rz Sl0 Sl1 Wheel Accelerator Brake Clutch Steering Aileron Rudder
  Throttle` (1037-1072). These names come from `GetVJDAxisExist` on the real usages, so
  they are correct (a device made with `-a throttle` reads back `Aileron`).
- Limit: 16 axes per device, no lower limit (`VJOY_NUMBER_OF_AXES 16`, public.h 366;
  loop 609). Buttons 0-128, POVs 0-4, devices 1-16 (unchanged).
- Registry: key `HKLM\SYSTEM\CurrentControlSet\services\vjoy\Parameters\DeviceNN`
  (`%02d`, vJoyConfig.cpp 487-489; `declarations.h` 60), value names
  **`HidReportDescriptor` / `HidReportDescriptorSize`** (new `declarations.h` 62-63,
  new `driver/sys/vjoy.h` 77-78). The descriptor grows (16 slots instead of 8).

## 4. Driver 2.1.9 with the new axes (verified unless noted)

- **Registry value name differs.** Old driver and old vJoyConfig use the misspelt
  `HidReportDesctiptor` / `HidReportDesctiptorSize` (old `driver/sys/vjoy.h` 77-78, old
  `apps/vJoyConf/declarations.h` 53-54). The old driver skips a DeviceNN key without
  that value (old `hid.c` 1459-1467, `continue`). So a device written by the 2.2.2.0
  vJoyConfig is **ignored** by a 2.1.9 driver (no device, or the stale old-spelling
  value is used if one is still there). Not rejected with an error, just not seen.
- Even with the right value name, the old driver would not deliver the new axes: its
  input report is `HID_INPUT_REPORT_V2` with only 8 axis slots (old `vjoy.h` 1142-1168,
  sent as `sizeof(HID_INPUT_REPORT_V2)`, old `driver.c` 793), and it copies only
  X..Dial from the DLL position (old `hid.c` 1293-1312). A 16-slot descriptor with an
  8-slot report would put hats/buttons at the wrong offsets (effect on Windows:
  unverified). The old driver only checks the report id in the descriptor
  (`ParseIdInDescriptor`, old `hid.c` 2156-2178), nothing else.
- Old vJoyConfig (2.1.9.1) parses only `x y z rx ry rz sl0 sl1` (old `vJoyConfig.cpp`
  196-207); other `-a` names are silently ignored, no error, and its descriptor has
  8 slots (loop `i<8`, 586-592). `-t` prints 8 axis tokens.
- On the user's PC (driver 2.1.9 + vJoyConfig 2.1.9 + our 2.2.2.0 DLL): the new axes
  cannot be created or fed. `GetVJDAxisExist(0xC4 ...)` returns a negative code
  (`NO_SUCH_AXIS`), `SetAxis` on them changes a struct field the old driver never reads.
  Support for the new axes needs driver 2.2.2.0 and its vJoyConfig.

## 5. vJoyConf GUI names (verified, new `apps/vJoyConf/vJoyConf.rc` 46-86)

Checkbox labels: `X`, `Y`, `Z`, `Rx`, `Ry`, `Rz`, `Slider`, `Dial/Slider2`, `Wheel`,
`Accelerator`, `Brake`, `Clutch`, `Steering`, `Aileron`, `Rudder`, `Throttle`
(X, Rx, Slider, Dial/Slider2 and the eight new ones read directly; Y/Z/Ry/Rz assumed
from the same block, unverified).

## Open (unverified)

1. What DirectInput enumerates for the seven Simulation-numbered usages on page 0x01,
   and in which order (needs a VM with driver 2.2.2.0).
2. Exact HID Usage Tables meaning of 0xB0-0xC8 on the Generic Desktop page.
3. Whether the vJoy 2.2.2.0 installer converts old `HidReportDesctiptor` values when
   upgrading from 2.1.9 (installer not read).
