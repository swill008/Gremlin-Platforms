# vJoy 2.2.2 new axes: who can see more than 8 axes? (scout WINDOWS)

Date 2026-11-22, read-only study (web docs and source reading). Agent WINDOWS, 02:45-02:48.

Labels: **verified** = read in the cited source; **verified (Wine)** = read in
Wine's DirectInput re-implementation, which copies Windows' behaviour but is not
Windows itself; **unverified** = not confirmed from a primary source.

## 1. DirectInput: how a HID axis gets a DirectInput slot

- **Verified.** DirectInput gives every HID axis a type GUID from its usage, and
  `SetDataFormat` matches the app's data format to device objects by those GUIDs.
  Microsoft's table (archived page "Axis Selection",
  https://learn.microsoft.com/en-us/previous-versions/windows/hardware/hid/axis-selection):

  | HID usage | DirectInput GUID (slot in DIJOYSTATE2) |
  |---|---|
  | X 0x30 / Y 0x31 / Z 0x32 | GUID_XAxis / GUID_YAxis / GUID_ZAxis |
  | Wheel 0x38 | GUID_ZAxis (same slot as Z) |
  | Rx 0x33 / Ry 0x34 / Rz 0x35 | GUID_RxAxis / GUID_RyAxis / GUID_RzAxis |
  | Slider 0x36, Dial 0x37 | GUID_Slider (rglSlider[0..1]) |
  | Steering 0xC8 | GUID_XAxis (same slot as X) |
  | Accelerator 0xC4 | GUID_YAxis (same slot as Y) |
  | Brake 0xC5 | GUID_RzAxis (same slot as Rz) |
  | Rudder 0xBA | GUID_RzAxis (same slot as Rz) |
  | Throttle 0xBB | GUID_Slider (a slider, **not** Z) |
  | Clutch 0xC6, Aileron 0xB0 | not in the table: GUID_Unknown |

  The page is labelled for the DirectX 7 era. Wine's current DirectInput uses
  the same table (`object_usage_to_guid`, dlls/dinput/joystick_hid.c lines
  498-531, https://gitlab.winehq.org/wine/wine/-/raw/master/dlls/dinput/joystick_hid.c),
  and adds Clutch only as a name ("Clutch"), type GUID_Unknown (lines 668-673, 851-854).
- **Verified.** `c_dfDIJoystick2` has exactly 8 position slots: X, Y, Z, Rx, Ry,
  Rz, Slider(0), Slider(1), each asking for one GUID (Wine data_formats.c,
  `dfDIJoystick2[]`; struct layout DIJOYSTATE2,
  https://learn.microsoft.com/en-us/windows/win32/api/dinput/ns-dinput-dijoystate2).
  Each device object fills at most one slot; the first object (in enumeration
  order) with the matching GUID wins (Wine device.c `match_device_object`, lines 229-256).
- **What happens to the rest:**
  - GUID_Unknown axes (Clutch, Aileron, any unmapped usage): no `c_dfDIJoystick2`
    entry asks for GUID_Unknown, so they get no slot and are **dropped** for any app
    using the standard format. **Verified (Wine)**; an app that enumerates objects
    and builds its own data format could still read them (unverified for any real game).
  - A second axis on an already-taken GUID (X + Steering, Y + Accelerator, Z + Wheel,
    Rz + Brake + Rudder) or a third+ slider (Sl0 + Sl1 + Throttle): Wine's matcher
    does not check the position/velocity aspect flag, so the spare object can land
    in the matching *velocity/acceleration/force* slot (lVX, lVRz, rglVSlider...).
    Games read those slots almost never. **Verified (Wine) only; what real Windows
    does with them is unverified.** In practice: dropped or hidden.
- Bottom line for DirectInput: **at most 8 axes reach a normal game**, and the
  new usages mostly *collide* with the classic 8 instead of adding to them.

## 2. dill (our input reader)

- Shipped dill is DILL v2.0 with no published source (dill/PROVENANCE.md line 14);
  the public WhiteMagic/dill source (master `eb66aea`, 2026-07-20) is the reference.
- **Verified (public source).** `src/dill.cpp` `enumerate_axis_objects` (lines 837-875)
  calls `EnumObjects(DIDFT_AXIS)` and keeps an axis only if its guidType is
  X/Y/Z/Rx/Ry/Rz (`g_axis_guid_lookup`, lines 98-106) or GUID_Slider (first two
  only; more are logged "More than two sliders detected, ignoring"). It reads state
  through `c_dfDIJoystick2` (line 936). `axis_mapping.cpp` `g_axis_di_offset_lookup`
  has a fixed 8 entries; `build_axis_map` gives each slot at most once.
  It logs an error when `capabilities.dwAxes > 8` (lines 1044-1051).
- **Verified (our side).** The ABI is fixed at 8 too: `_DeviceSummary.axis_map`
  is `_AxisMap * 8` (dill/__init__.py line 120) and `DeviceSummary` reads 8
  entries (line 261).
- So dill **never sees a 9th-16th axis**; GUID_Unknown axes (Clutch, Aileron)
  are ignored; collided axes (Steering on X, Brake/Rudder on Rz) count once.
- **Matching risk (verified from code, effect inferred).**
  `gremlin/device_initialization.py` lines 357-404 matches vJoy ids to dill devices by
  `(axis_count, button_count, hat_count)`. The vJoy side counts only the classic 8
  usages (`vjoy/vjoy.py` `AxisCode` lines 46-57, `axis_ids` lines 92-98). A device
  with new axes would give different counts on each side, e.g. X, Y + Throttle:
  vJoy side 2, dill side 3 (X, Y, Slider 0); the device would not be matched and
  would get the "Windows doesn't list it as a game controller" problem. If the
  vJoy side were widened to count all 16, the mismatch goes the other way (16 vs ≤8).

## 3. Windows' own views

- **joy.cpl (Game Controllers panel):** shows the DirectInput view, so at most
  X/Y/Z/Rx/Ry/Rz + 2 sliders. **Unverified** (no Microsoft page found; matches the
  community statement that the 8-axis limit comes from DirectInput, not HID:
  https://code-monet.github.io/sim-gamer-kit/fffsake/vjoy_configuration/).
- **Raw HID (HidP_GetValueCaps):** sees every value cap in the descriptor, so all
  16. **Verified** by mechanism (SDL2's raw-input code counts every non-range value
  cap as an axis, SDL2 src/joystick/windows/SDL_rawinputjoystick.c lines 1352-1373).
- **Windows.Gaming.Input RawGameController:** `AxisCount` is "the number of axes"
  with no stated limit or usage list
  (https://learn.microsoft.com/en-us/uwp/api/windows.gaming.input.rawgamecontroller.axiscount).
  Whether it reports >8 for vJoy is **unverified**.

## 4. Games and engines

- **SDL (SDL2 and SDL3) on Windows, non-Xbox devices:** read through DirectInput.
  SDL3 `SDL_dinputjoystick.c` `EnumDevObjectsCallback` (lines 440-525, main branch)
  keeps only X/Y/Z/Rx/Ry/Rz/Slider GUIDs ("not an axis we can grok" otherwise) and
  uses its own copy of `c_dfDIJoystick2` (lines 79-255, 1085). SDL2's raw-input backend,
  which would see all axes, only takes XInput devices ("IG_" in the device name,
  SDL_rawinputjoystick.c line 881), so not vJoy. **Verified.** Duplicated GUIDs
  (two Rz-type axes) both read the one Rz slot in SDL (inferred from the same code).
- **DCS, IL-2, MSFS, X-Plane, most flight/racing sims:** use DirectInput, so 8 axes.
  **Unverified** per title (widely reported; e.g. a DCS forum thread on Joystick
  Gremlin "more axis" answers by using more vJoy devices,
  https://forum.dcs.world/topic/313300-joystick-gremlin-i-want-to-add-more-axis-please-help).
- **Unity Input System** reads HID descriptors directly on Windows, **Unreal's**
  RawInput plugin reads raw HID with configurable axes: both could see >8 in
  principle. **Unverified**; neither is what common sims use for joysticks.

## 5. Bottom line

- "16 axes on one vJoy device" is **not useful for DirectInput games** (nearly every
  sim): they get at most 8, and several new usages fall into the *same* 8 slots.
  More vJoy devices remain the way to get more axes. It also does not work with our
  own reader (dill is fixed at 8) and would break vJoy-to-device matching unless
  the counting is changed on both sides.
- **Yes, naming changes the slot (verified, section 1 table).** Throttle (0xBB)
  lands in a **Slider**, not Z; Rudder and Brake land in **Rz**; Steering in **X**;
  Accelerator in **Y**; Wheel in **Z**; Clutch and Aileron land **nowhere**. A device
  that has both X and Steering, or Rz and Rudder, loses one of them for games.
  So "proper names" are not just labels: a named axis is the same DirectInput slot
  as its classic twin, or a lost axis. If names are wanted on screen, the safe form
  is a display label over the classic usage (the game still sees Slider 0 / Rz),
  not a change of HID usage. (Recommendation is the scout's reading; not decided.)
- Open check (unverified, worth a live read later): what real Windows 11 does with
  a collided or GUID_Unknown axis (velocity slot or dropped), and what joy.cpl shows
  for a vJoy 2.2.2 device with Throttle/Rudder set.
