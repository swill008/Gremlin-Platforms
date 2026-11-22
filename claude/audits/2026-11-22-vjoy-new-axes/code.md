# vJoy 2.2.2.0 new axes: where our code assumes 8 axes (agent CODE, 2026-11-22, 02:44-02:50)

Read-only study. "verified" = read in our code this session; "unverified" = needs a
test-machine run or the native DLL (dill source is not published). Line numbers are
as of the working tree on 2026-11-22.

## Storage-format answer (verified)

An axis is identified by a **small integer index 1-8** everywhere inside the program
(1 = X ... 8 = SL1), never by HID usage. Module-file claims store `"axes": [ints]`
(`gremlin/modules/store.py:970,2830`; read by `claim_ids` in output.py), wiring and
bindings carry the int, and `write_vjoy(vjoy_id, "axis", axis_id, value)` /
`dev.axis(axis_id)` take it. The usage (0x30-0x37) exists only inside `vjoy/vjoy.py`
(`AxisCode`, `VJoyStateCache.axis_lookup`, `VJoy.axis_equivalence`, `Axis.axis_id`).
The driver side (vJoyConfig `-a`, installer job file, `VJoyDevice.axes`) uses lower-case
**names** ("x".."sl1"), not indexes.

So 16 axes fit with **no change to the claim/module/profile format**: indexes 9-16 are
simply new integers. The one decision: fix an order for 9-16 (vJoyConfig's `-t`
prints Wheel Accelerator Brake Clutch Steering Aileron Rudder Throttle after Sl1,
audit code.md row 24; that order matches usages 0x38, 0xC4, 0xC5, 0xC6, 0xC8, 0xB0,
0xBA, 0xBB as listed by the user: confirm the exact order on the test machine). Nothing
may ever be renumbered once saved, since saved files hold the ints.

## Where the 8-axis assumption sits, by subsystem

### A. vJoy library (vjoy/)

| File:line | Assumes | Change | Risk |
|---|---|---|---|
| vjoy/vjoy.py:47-57 `AxisCode` | 8 usages 0x30-0x37 | add WHEEL 0x38, ACCELERATOR 0xC4, BRAKE 0xC5, CLUTCH 0xC6, STEERING 0xC8, AILERON 0xB0, RUDDER 0xBA, THROTTLE 0xBB in the chosen index order. Order of the enum drives everything below (all loops use `enumerate(AxisCode)`) | medium: the enum order IS the index mapping, so it must be settled first |
| vjoy/vjoy.py:91-98 `axis_ids` | `i + 1` over `AxisCode`, `GetVJDAxisExist(id, usage) > 0` | works unchanged once the enum grows (2.2.2.0 returns >0 or negative error codes; `> 0` is right, audit row 8) | low |
| vjoy/vjoy.py:101-110 `axis_count` | len(axis_ids) | unchanged | low |
| vjoy/vjoy.py:158-167 `VJoyStateCache.axis_lookup` | hard-coded dict 1-8 -> usage | derive from `AxisCode` instead of writing 16 lines; `get_axis(index)` raises KeyError for 9+ today | medium: KeyError in the keep-alive/rest path |
| vjoy/vjoy.py:462-471 `VJoy.axis_equivalence` | hard-coded AxisCode -> 1-8 | same, derive from the enum | low |
| vjoy/vjoy.py:808-813 `_init_axes` | `AxisNames.to_string(AxisNames(i + 1))` | `AxisNames(9)` raises **ValueError** (not GremlinError) -> device would fail to open as soon as a new axis exists. Must extend `AxisNames` (or use one name table) | **high**: crashes opening any 2.2.2.0 device that has a new axis |
| vjoy/vjoy.py:214-290 `Axis` | per-usage min/max read, `SetAxis(value, id, usage)` | generic; 2.2.2.0 SetAxis accepts the new usages (audit row 11, verified from source, not run) | low |
| vjoy/vjoy.py:743-744, 773 | loops `for i in self._axis` | generic | low |
| vjoy/vjoy_interface.py:54-83 | ctypes prototypes only, no axis list | none | none |
| vjoy/vjoy_interface.py (DLL struct) | 2.2.2 uses JOYSTICK_POSITION_V3 inside the DLL (audit row 16) | none on our side | n/a |

### B. Shared name tables (one owner each; today three parallel 8-entry tables)

| File:line | Table | Change | Risk |
|---|---|---|---|
| gremlin/types.py:77-122 `AxisNames` enum + two lookup dicts | 1-8 -> "X Axis"... "Dial" | extend to 16 (names per glossary); also used for real DirectInput devices | medium; `AxisNames(n)` ValueError path (see below) |
| gremlin/common.py:83 `input_to_ui_string` | `AxisNames(input_id)`, catches GremlinError only | ValueError for id 9+ escapes (only GremlinError caught) | medium |
| action_plugins/common.py:24 `joystick_label` | `AxisNames.to_string(AxisNames(input_id))` | same ValueError for 9+; no catch at all | medium |
| gremlin/axis_names.py:11 `AXIS_SHORT` | 1-8 -> X Y Z Rx Ry Rz S1 S2 | add 9-16 short names; used by wiring.py:62, trace_watch.py:105,228, input_tester/devices.py:23, model.py:990, ui/input_pairing.py:186, ui/module_pairing.py:104 | low-medium: trace_watch.py:228 loops `AXIS_SHORT` so the vJoy read-back check grows with the table (fine); other users just get names |
| gremlin/modules/output.py:1152-1160 `AXIS_WORDS` (drop-down words "X Axis"..."Dial") | 1-8 | add 9-16; fallback is "Axis N" so nothing breaks, but words would be wrong/plain | low |

Proposal for the plan: make these three tables derive from one table (design-for-change
rule) before adding names.

### C. DirectInput / DILL side (the main unknown)

| File:line | Assumes | Risk |
|---|---|---|
| dill/__init__.py:120 `("axis_map", _AxisMap * 8)` and :261 `for i in range(8)` | the native `DeviceSummary` struct has exactly 8 axis_map entries (struct of dill2.dll, source unpublished, SHA pinned in dill/PROVENANCE.md; `test_dill_provenance`) | **high, unverified**: we cannot grow it; a device with 9-16 axes may be truncated or mis-sized, and `dev.axis_count` may report >8 while only 8 map entries exist. The VM check (vm.md) shows Windows lists vJoy devices with 12 axes via WinRT for 8 vJoy axes + 4 hats mapped as axes, so DirectInput counts need a test-machine read |
| gremlin/input_cache.py:224,347-352,443 | loops `range(info.axis_count)` over `axis_map[i]` | IndexError risk if axis_count > 8 while map has 8 entries (verified loop shape; effect unverified) |
| gremlin/input_tester/devices.py:131, gremlin/ui/live_input.py:196-212, ui/device.py:124-127,594,1106,1166, ui/profile.py:1223-1417, ui/trace_model.py:165, modules/store.py:2932-2943, modules/output.py:742 | read DILL `axis_count` / `axis_map[:count]` / `axis_lookup` for the input (hardware) side of a vJoy device | they only matter for vJoy shown as an INPUT device (viewers, input pages); if DILL is capped at 8, new axes would be absent there but outputs would still work |
| DirectInput/HID reality | DirectInput exposes at most 8 axes (X Y Z Rx Ry Rz + 2 sliders); the new usages (Wheel, Accelerator, Brake, Clutch, Steering, Aileron, Rudder, Throttle) may appear as extra axes or not at all | unverified: needs a test-machine read of `dill` summary for a 16-axis vJoy |

### D. Matching vJoy ids to DirectInput devices (gremlin/device_initialization.py)

- :361 `hash_value = (dev.axis_count, dev.button_count, dev.hat_count)` (DirectInput
  side) vs :381-382 `output.vjoy_layout(i)` = `(vjoy.axis_count(id), buttons, hats)`
  (output.py:481, driver side). `vjoy.axis_count` counts the new usages after the
  `AxisCode` change, DirectInput may not: **a device with any new axis could then fail
  to match and be left out** ("Windows doesn't list it as a game controller",
  :401-405). Already recorded as audit row 18 for devices made outside our setup.
  Risk **high** for this plan (verified from code; DirectInput count unverified).
- Fix options (not decided): compare on min(axis_count, DirectInput limit); or match on
  buttons+hats (+axes only where equal) ; or add the HID/serial-based match. The
  "different layout per device" rule (drivers.py `layout_key`, installer alike check)
  also counts axes and would still hold if the count differs per device.
- output.py:724-750 `vjoy_driver_ids`: asks the driver first (`vjoy_axis_ids`), falls
  back to `device.axis_map` indexes only when the driver cannot be read. Fine; the
  fallback would see only 8.

### E. Output module (gremlin/modules/output.py)

- :454-471 `vjoy_axes`, `vjoy_axis_ids`: generic over `vjoy.axis_ids` (low).
- :476-484 `vjoy_layout`: count only (see D).
- :520-521, 584-585, 597-615, 642-643, 682-685: validate via `dev.is_axis_valid(axis_id=...)`,
  generic (low). `VJoy.axis()` maps through `axis_equivalence` (A) so an AxisCode value
  or an index both work.
- :1152-1177 `AXIS_WORDS`/`control_label` (B).
- gremlin/modules/store.py:2932-2943: when the hardware side has no axis_map it builds
  `range(1, axis_count + 1)`; generic.
- gremlin/ui/module_model.py:2429,2489,2665 and ui/device_pack.py:1737 show counts
  from `axis_count`; generic, but counts would differ between input and output side
  (C/D).
- gremlin/trace_watch.py:226-228 loops `AXIS_SHORT` over 16 vJoys (B).
- action_plugins: no action has its own axis list (grep: none use `axis_ids`,
  `AxisNames` only in common.py:24). Map-to-vJoy drop-downs are built from the
  output module's `vjoy_driver_ids` + `control_label` (low once names exist). Verified
  by grep; the QML drop-down for the vJoy axis picker was not opened (unverified).

### F. Drivers helper (gremlin/drivers.py, gremlin/driver_jobs.py)

| File:line | Assumes | Change | Risk |
|---|---|---|---|
| gremlin/drivers.py:550 `VJOY_AXES` | 8 names, also "known names" check (:567-576 `__post_init__` order + `problem()` rejects unknown) and `_axes()` loader :699-703 | extend to 16 names in vJoyConfig order (x y z rx ry rz sl0 sl1 wheel accelerator brake clutch steering aileron rudder throttle; exact `-a` spelling per 2.2.2.0 vJoyConfig.cpp must be checked, notes.md line 31 says "Wheel, Accelerator, Brake, Clutch, Steering, Aileron, ...") | low; saved names stay valid |
| drivers.py:593-605 `new_device`, `PRESETS`, `layout_key` | new_device = all `VJOY_AXES`; layout_key = len(axes) | **decision**: should "full" mean 8 or 16 axes? Changing `new_device` to 16 changes presets and Help ("8 axes"); layout_key len() still works | medium: a product decision, and spec statements say 8 |
| driver_jobs.py:266-271 `_describe_axes` | `len(axes) == len(VJOY_AXES)` -> "8 axes (X-SL1)" | becomes "16 axes (X-THROTTLE)" or a better wording; tests pin text | low |
| driver_jobs.py:305-310 | `-a` only when axes ticked; omitted `-a` = all 16 in 2.2.2.0 (audit row 21) | still a gap: zero axes -> 16-axis device, read-back mismatch (visible failure) | medium (already known) |
| driver_jobs.py:371-402 `parse_report` | `zip(VJOY_AXES, tokens)` keeps tokens that are not "-" | automatically right once VJOY_AXES has 16 names IN THE SAME ORDER as vJoyConfig's printed tokens; if the order differs the read-back misnames axes. Today with 2.2.2.0 the 16-token report is silently truncated at 8 by `zip` | **medium/high until order verified** (unverified: `-t` not run on 2.2.2.0 yet) |
| driver_jobs.py:338-340 read-back | compares ticked names vs read names | fine with 16 | low |

### G. Tools > Drivers UI and setup

| File:line | Assumes | Change | Risk |
|---|---|---|---|
| gremlin/ui/drivers_model.py:324-358 `setDevice`/`setAxis`/`deviceSummary`, :831-867 `vjoyAxes` property (from `VJOY_AXES`) | generic over `VJOY_AXES` | none beyond the list | low |
| qml/WindowDrivers.qml:341-360 | `Repeater` over `_drv.vjoyAxes`, one tick box per name | 16 tick boxes per device row: row layout/width must wrap (two rows of 8, or a flow); off-screen scale check needed | medium (layout) |
| installer/gremlin_platforms.iss:161-165,233,647-649 | `Axes` is an Integer **bit mask**, `VJoyAllAxes = 255`, `VJoyAxisNames` string of 8 names, `VJoyRowAxes` array sized `VJoyMaxDevices * 8`, tag = row*8+axis (:1964-1976, 2120, 2140-2144), `AxesFromReport` ignores tokens past 8 (:1429-1433), `AxesText` "X-SL1" (:1610-1628), headings X..SL1 in columns of `BoxW` (:2299-2357), AlikeCount compares `AxesCountOf` (:1698), device row visible/enabled loops `R * 8 + K` (:1878-1935), job-file `AxesJson` (:1448-1460) | bit mask 255 -> 65535 (still fits Integer); every `8` becomes the axis count; **setup page width**: 16 tick columns + Buttons + Hats + remove button will not fit one row; needs a second row per device or a different control (e.g. a count + "Choose axes..." box) | **high effort/medium risk**: largest single piece, Inno Setup Pascal, no unit tests except `test_installer_drivers.py` text checks |
| qml/help/getting_started.js:71, qml/help/tools.js:148,151 | prose lists the eight names and "8 axes (X, Y, Z, RX, RY, RZ, SL0, SL1)" | update text | low |

### H. The approved plan claude/plans/vjoy-axis-picker.md

It is built (01 S187, 06 S185, 12 S25a, D-01/06/12-VJOY-AXES 2026-11-21: tick boxes by
name, bit mask, names in the job file). It already stores **names**, which is exactly
what extends: its "eight tick boxes" wording becomes sixteen. Its open point 1 (setup
page room: 16 devices x 8 boxes) doubles in this plan (16 x 16). Its open point 2
(vJoyConfig accepts any axis set; `-t` shows which) is still partly unverified and now
also decides order of tokens 9-16.

### I. Tests, spec, glossary (will need updating or extending)

- Tests that pin 8 axes or the names (grep, verified by file name list; contents not all
  read): test_drivers.py, test_driver_jobs.py, test_drivers_model.py, test_drivers_window.py,
  test_drivers_e2e.py, drivers_window_smoke.py, test_installer_drivers.py,
  test_handson_AX_fake_vjoy_axes.py, test_handson_F7_vjoy_rest.py, test_vjoy_turned_off.py,
  test_output_guards.py, test_cant_send*.py (3), test_new_action_defaults.py,
  test_device_layout_change.py, test_device_relaid_update.py, test_input_tester_*.py (4),
  test_batch3_C3a/C5.py, test_crash_and_loss_fixes.py, test_spec_wording_56.py, plus
  test/fake_hardware.py:112 (fake vJoy device: 6 axes through raw_device's axis map).
- Spec statements to review (change control: user must be told first): 01 S187 and the
  D-01-VJOY-AXES decision (:112, :564, :659 "8 axes" preset/alike text), 06 S185/S188 and
  D-06-VJOY-AXES (:74, :395, :580), 12 S25a and D-12-VJOY-AXES (:66, :208), and 02/03/06
  statements about vJoy viewers and counts if present (not all read).
- claude/glossary.md:36 lists the eight tick-box names (X..SL1); needs the new names.
- Program map section 2/3/11 entries for any new file; section 10 gap for the DILL 8-cap.

## Biggest items, in order

1. DILL (dill2.dll) is built for 8 axes; DirectInput/HID may show fewer than 16 for a
   16-axis vJoy. Everything on the input/hardware side and the vJoy-to-DirectInput
   matching (device_initialization.py:359-413) depends on what the test machine shows
   for a device made with the new axes. Verify first.
2. `AxisCode` + `VJoyStateCache.axis_lookup` + `VJoy.axis_equivalence` + `AxisNames`
   (vjoy.py, types.py): without the extension a device with a new axis cannot even open
   (`AxisNames(9)` ValueError at vjoy.py:811).
3. Layout-matching rule: counting new axes on the driver side but not on DirectInput
   makes the device "not listed as a game controller".
4. Installer page: bit mask and 8-wide loops/columns; no room for 16 columns.
5. vJoyConfig `-a` spelling and `-t` token order for the new names (verify on the
   test machine before fixing the order of indexes 9-16).
6. Name tables (types.py, axis_names.py, output.py AXIS_WORDS): unify to one.
7. Preset decision: does "full" stay 8 axes or become 16 (affects spec text, Help,
   tests, and the 2-device alike counts).

Format answer repeated: index (1-8 today, 9-16 new) in profile/module claims; names in
the driver job; usage only inside vjoy/vjoy.py. No profile/module format change needed.
