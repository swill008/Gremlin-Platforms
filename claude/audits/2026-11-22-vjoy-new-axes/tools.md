# vJoy 2.2 new axes: how other programs handle them (agent TOOLS, 2026-11-22 02:59-03:05)

Read-only web study (GitHub API and raw files). Nothing downloaded or run. The GitHub
API rate limit was hit midway, so SimHub, MobiFlight, Mojo, vXboxInterface and the
njz3 feeder were not checked (unverified, not reached). "Verified" = read at the cited
place. Branch names: Gremlin and GremlinEx `develop`, others `master`.

## Summary table

| Program | Supports new 8 axes? | How |
|---|---|---|
| JoystickGremlin (WhiteMagic) | No (verified) | `AxisName` enum has 8 usages 0x30-0x37 only |
| GremlinEx (muchimi) | No (verified) | same 8-value `AxisName`; `axis_count` counts only those 8 |
| FreePIE | No (verified) | plugin uses only X Y Z Rx Ry Rz SL0 SL1; loops the bundled wrapper's enum |
| vJoySerialFeeder | Not seen (unverified) | axis dropdown is `Enum.GetNames(VJoyBase.Axes)`; that enum's file was not found |
| UCR | n/a (verified) | its vJoy output goes via vGen (`SetDevAxis`), not the vJoy DLL's usages |
| pyvjoy | Unverified | thin ctypes binding; no constants file found (404) |
| SimHub, MobiFlight, Mojo, njz3 feeder, vXboxInterface | Not checked | rate limit |

## Details

1. **JoystickGremlin R15-line (`develop`), `vjoy/vjoy.py` lines 47-54 (verified)**:
   `X=0x30 ... SL1=0x37` only. Line 96 `axis_count()` and ~818 name table
   (`AxisNames.to_string(AxisNames(i+1))`) assume numbers 1-8. No Wheel (0x38) even.
   https://github.com/WhiteMagic/JoystickGremlin/blob/develop/vjoy/vjoy.py
2. **GremlinEx (`develop`), `vjoy/vjoy.py` lines 65-74 (verified)**: same 8 values;
   `axis_count()` (121-130) loops that enum calling `GetVJDAxisExist`, so a device
   with only new axes counts as 0 axes. `axis_equivalence` (vjoy_interface.py 644-652)
   maps the same 8 to 1-8. DLL minimum version check "2.1.9.1".
   https://github.com/muchimi/JoystickGremlinEx/blob/develop/vjoy/vjoy.py
3. **Brunner 2.2.2.0 and the two Gremlins**:
   - GremlinEx issue 363 (verified): author says only 2.1.9.1 is tested; a Brunner-DLL
     user got actions that would not create. Author: "Any fork compatible with this
     should work", no mention of new axes. https://github.com/muchimi/JoystickGremlinEx/issues/363
   - Gremlin issue 811 (verified): R15 + vJoy 2.2.2.0 on Win11 25H2; the user says
     Y/Z "remap" to X in joy.cpl, and Rx/Ry/Rz show "funkily as sliders in joy.cpl but
     work in a game". WhiteMagic: Brunner fork "is also supported" (used for FFB), no
     support statement for the new axes; recommends 2.1.9.1. Cause of the joy.cpl
     display is not established (unverified); it is a user report, possibly a
     different axis-enable set. https://github.com/WhiteMagic/JoystickGremlin/issues/811
   - No issue or PR found in either repo asking for the new axes (searches
     "vJoy 2.2", "BrunnerInnovation", "Accelerator axis": only the two above).
4. **FreePIE `FreePIE.Core.Plugins/VJoyPlugin.cs` (verified)**: lines 129-131 build
   `enabledAxis` for every value of `HID_USAGES` from the bundled wrapper
   (`Lib/VJoy/vJoyInterfaceWrap.dll`, an old build); the plugin source references only
   HID_USAGE_X/Y/Z/RX/RY/RZ/SL0/SL1. Axes are exposed as named script properties
   (x, y, z, ...), range -axisMax..axisMax, `SetAxis` throws if the axis is not enabled
   (167-168). New names would need a new wrapper and new properties (unverified).
5. **vJoySerialFeeder**: axis stored as `int Axis` = dropdown index (`AxisMapping.cs`
   105, 211, 244, verified); the list is `Enum.GetNames(VJoyBase.Axes)`. Its content
   was not read (unverified). It stores an index into the enum, i.e. the same style as
   our 1-based number.
6. **UCR `Classes/GuiControls/IOClasses/vGen.ahk` (verified)**: calls
   `SetDevAxis(hDev, axisNumber, float)` of the vGen library; no vJoy usage ids.
   Not a source of precedent.
7. **Naming/order precedent**: no surveyed program names or orders the new 8 axes.
   The only source for names/order is vJoy itself (vjoy.md table; descriptor order is
   vJoyConfig's). Verified negative: neither Gremlin line has them.
8. **Game visibility**: no program notes on it. Only the user report in Gremlin issue
   811 (a game, X-Wing Alliance Upgrade, accepted the Rx/Ry/Rz output). Nothing found
   for the new axes specifically.
9. **DirectInput matching by axis counts**: neither Gremlin line nor GremlinEx matches
   vJoy to DirectInput by axis count with the new usages; both call
   `GetVJDAxisExist` only for the 8 classic usages (items 1-2), so a device that
   enables only new axes would be seen with fewer axes than it has. Our program's
   count comparison (code.md) is therefore no worse than the references, but also no
   precedent exists to copy.

## Conclusion

Nothing in the surveyed programs supports the new axes; the upstream Gremlins
(source and issues) neither support nor discuss them, so we would be first and must
define names, order, storage and matching ourselves (from vjoy.md). Not reached:
SimHub, MobiFlight, Mojo, njz3 feeder (could be checked after the rate limit resets).
