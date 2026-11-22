# vJoy 2.2.2.0 compatibility: code check (agent CODE, 2026-11-21 15:33-15:38)

Question: does Gremlin-Platforms work with vJoy 2.2.2.0 (github.com/BrunnerInnovation/vJoy,
tag `v2.2.2.0`, released 2023-12-19), both with the 2.2.2.0 driver and with the user's
mixed setup (driver 2.1.9 + our shipped 2.2.2.0 `vJoyInterface.dll`)?

Sources read (at tag `v2.2.2.0` unless noted):
- `SDK/inc/vjoyinterface.h`, `SDK/inc/public.h`, `inc/public.h`, `inc/gen-versioninfo.h`
- `apps/common/vJoyInterface/vJoyInterface.cpp` (the DLL)
- `apps/vJoyConf/vJoyConfig/vJoyConfig.cpp` (the command-line tool)
- `driver/sys/rawpdo.c`, `driver/sys/hid.c` (the driver)
- `install/vJoyInstallerSigned_Brunner.iss` (where vJoyConfig.exe is installed)
- For the 2.1.9 driver: `jshafer817/vJoy` tag `v2.1.9.1`: `inc/public.h`,
  `driver/sys/rawpdo.c`, `driver/sys/hid.c`
- Our shipped `vjoy/vJoyInterface.dll`, read as bytes only (never loaded): PE32+ x64,
  57 named exports, ProductVersion `v2.2.2.0 Commit:000000 Compile:x64`, CompanyName
  `Shaul Eizikovich`, 888,432 bytes.

"Verified" = checked against the source text above. "Unverified" = reasoned, not
checked on a machine or not fully traced.

## Version numbers

| Item | Value | Source |
|---|---|---|
| `GetvJoyVersion()` | Returns the HID `VersionNumber` of the first vJoy device (VID 0x1234, PID 0xBEAD), i.e. the **driver's** `VERSION_N`, not the DLL's | vJoyInterface.cpp `GetvJoyVersion`; driver hid.c `deviceAttributes->VersionNumber = VERSION_N` |
| Driver 2.2.2.0 `VERSION_N` | `0x100*2 + 0x10*2 + 2` = **0x222** | public.h line 125, gen-versioninfo.h (2,2,2,0) |
| Driver 2.1.9.1 `VERSION_N` | `9 + 0x10*1 + 0x100*2 + 0x1000*0` = **0x219** | 2.1.9.1 inc/public.h line 78 |
| Our check `< 0x218` | Passes for both (0x219, 0x222); 0x222 fits `c_short` | vjoy/vjoy.py:492 |
| `DriverMatch` | DLL compares its own `VERSION_N` (0x222) with the driver's; FALSE with driver 2.1.9. It is only a report: no DLL function calls it internally, and Gremlin never calls it | vJoyInterface.cpp line 849 (only use); grep of our code |

## Table

| # | Our call / use | file:line | 2.2.2.0 status | Source | Risk | Label |
|---|---|---|---|---|---|---|
| 1 | Bind 24 functions by name at import; a missing export raises and the whole vJoy module fails | vjoy/vjoy_interface.py:45-111 | same: all 24 are among the DLL's 57 exports | PE export table of vjoy/vJoyInterface.dll | none | verified |
| 2 | `GetvJoyVersion` -> `c_short`, check `< 0x218` | vjoy/vjoy_interface.py:46, vjoy/vjoy.py:492 | same signature (`SHORT __cdecl (void)`); returns 0x222 (driver 2.2.2.0) or 0x219 (driver 2.1.9); both pass | vjoyinterface.h:310; public.h:125; 2.1.9.1 public.h:78 | none. Note: returns 0 when no vJoy device exists, which would show "incompatible version"; `vJoyEnabled` runs first so this is unlikely | verified |
| 3 | `vJoyEnabled` -> `c_bool` | vjoy/vjoy_interface.py:47, vjoy/vjoy.py:489, gremlin/modules/output.py:707 | same (`BOOL`, true when the Raw PDO namespace exists) | vJoyInterface.cpp:1635 | none (c_bool reads the low byte of a 0/1 BOOL) | verified |
| 4 | `GetvJoyProductString` / `Manufacturer` / `SerialNumber` -> `c_wchar_p` | vjoy/vjoy_interface.py:48-50 | same (`PVOID`); bound only, never called | vjoyinterface.h:312-314 | none | verified |
| 5 | `GetVJDStatus` (Owned/Free/Bust/Missing/Unknown = 0..4) | vjoy/vjoy.py:70,87,499,505 | same enum order `VJD_STAT_OWN..UNKN`; GET_DEV_STAT IOCTL 0x91D and its reply layout (byte 0 flags, bytes 1-4 owner PID) are the same in driver 2.1.9.1 and 2.2.2.0 | vjoyinterface.h:27-31; both rawpdo.c GET_DEV_STAT | none | verified |
| 6 | `GetOwnerPid` | vjoy/vjoy.py:71,500,549,569 | same (`int (UINT)`) | vjoyinterface.h:333 | none | verified |
| 7 | `AcquireVJD` / `RelinquishVJD` | vjoy/vjoy.py:514,550,797 | same; ids 1-16; no driver-version gate inside | vJoyInterface.cpp:495-545 | none | verified |
| 8 | `GetVJDAxisExist(id, 0x30..0x37)` compared `> 0` | vjoy/vjoy.py:97,809 | changed internally: now returns `GetAxisCaps()`, which is TRUE (1) or a **negative** error code (-1..-10), not 0. Our `> 0` handles that correctly; a plain truth test would not | vJoyInterface.cpp:873-877, 4236-4293; vjoyinterface.h:35-44 | none for our code (keep `> 0`) | verified |
| 9 | `GetVJDAxisMin/Max(id, axis, c_void_p)` filled into `c_ulong` | vjoy/vjoy.py:232-235 | same (`LONG*`); range 0..0x7FFF so unsigned read is fine | vjoyinterface.h:327-328; public.h `VJOY_AXIS_MAX_VALUE 0x7FFF` | none | verified |
| 10 | `GetVJDButtonNumber`, `GetVJDContPovNumber`, `GetVJDDiscPovNumber` | vjoy/vjoy.py:122,134,149-150,824,841,849 | same signatures; now read from cached `DeviceControls` (filled from the HID descriptor) | vJoyInterface.cpp:946,1054,1120 | none | verified |
| 11 | `SetAxis(value, id, usage 0x30..0x37)` | vjoy/vjoy.py:278 | same; X..SL1 still map to wAxisX..wDial. 2.2.2.0 adds usages 0x38 (wheel), 0xB0/0xBA/0xBB, 0xC4-0xC8 which we don't use | vJoyInterface.cpp:1330-1409 | none | verified |
| 12 | `SetBtn(bool, id, 1..128)` | vjoy/vjoy.py:329 | same (`BOOL, UINT, UCHAR`), 1-128 | vJoyInterface.cpp:1411 | none | verified |
| 13 | `SetContPov(DWORD, id, 1..4)` / `SetDiscPov(int, id, 1..4)` | vjoy/vjoy.py:425,449 | same | vJoyInterface.cpp:1455,1480 | none | verified |
| 14 | `ResetVJD` | vjoy/vjoy.py:738 | same; RESET_DEV IOCTL 0x91F in both drivers | vJoyInterface.cpp:1186; both public.h | none | verified |
| 15 | `UpdateVJD`, `ResetAll`, `ResetButtons`, `ResetPovs` | vjoy/vjoy_interface.py:72-80 | present; bound only, never called by our code | export table; grep | none | verified |
| 16 | Every write (`SetAxis`/`SetBtn`/`SetContPov`) goes through the DLL's `Update()`, which sends `sizeof(JOYSTICK_POSITION)` = the **V3** struct (`USE_JOYSTICK_API_VERSION 3`) with IOCTL LOAD_POSITIONS | (inside the DLL) | changed: V3 struct is 4 LONGs longer than V2 and slots 13-16 now hold Accelerator/Brake/Clutch/Steering instead of VZ/VBRX/VBRY/VBRZ. Driver 2.2.2.0 expects V3: matches. Driver 2.1.9 only checks a **minimum** of sizeof(V2), so the larger buffer is accepted, and the fields we use (X..Dial, lButtons/Ex1-3, bHats/Ex1-3) sit at the same offsets in V2 and V3 | public.h V3 struct; 2.1.9.1 public.h V2 struct; both rawpdo.c `WdfRequestRetrieveInputBuffer(Request, sizeof(JOYSTICK_POSITION), ...)` | low with driver 2.1.9 (works today on the user's PC); none with driver 2.2.2.0. The reverse (old 2.1.x DLL with driver 2.2.2.0) would fail: driver 2.2.2.0 needs the bigger buffer. We ship the 2.2.2.0 DLL, so not our case | verified (source); mixed-driver behaviour seen working on the user's PC (per brief), not re-run here |
| 17 | Device count 1-16 | gremlin/modules/output.py:447-450, gremlin/drivers.py:551 | same (`VJOY_MAX_N_DEVICES 16`) | public.h:365 | none | verified |
| 18 | Match vJoy ids to DirectInput devices by (axes, buttons, hats) | gremlin/device_initialization.py:359-397 (layout from gremlin/modules/output.py:476-484) | changed range: 2.2.2.0 allows 16 axes (wheel, accelerator, brake, clutch, steering, throttle, rudder, aileron). Our `axis_count` counts only the 8 usages 0x30-0x37, but DirectInput counts every axis. A device given any of the 8 new axes (by the vJoyConf GUI, or by vJoyConfig without `-a`, see row 21) gets a different axis count on each side, so it is not matched and is left out with a problem note | public.h `VJOY_NUMBER_OF_AXES (16)`; vJoyConfig.cpp:30-51; vjoy/vjoy.py:47-57 | medium only for devices set up outside Gremlin with extra axes; none for devices Gremlin sets up with `-a` | verified (source); DirectInput count of the new usages unverified on a machine |
| 19 | Continuous-hats check (cont >= disc) | gremlin/device_initialization.py:390, vjoy/vjoy.py:149-152 | same | vJoyInterface.cpp:1054,1120 | none | verified |
| 20 | vJoyConfig path `%ProgramFiles%\vJoy\x64\vJoyConfig.exe` | gremlin/driver_jobs.py:257-259 | same location (`{commonpf}\vJoy\{DestSubDirX64}`), but installed only with the optional component `Apps\vJoyConf` | vJoyInstallerSigned_Brunner.iss:5,55,100 | low: if the user unticks that component, setup/read-back can't run (we show empty / fail) | verified (installer script); value of `DestSubDirX64` assumed `x64`, unverified |
| 21 | `vJoyConfig <id> -f [-a x y ...] -b N -p N [-l]` | gremlin/driver_jobs.py:308-313 | same flags: `-f` force, `-l` deferred, `-a` names `x y z rx ry rz sl0 sl1` (case-insensitive), `-b` 0-128, `-p` 0-4 continuous. Changed: when `-a` is **absent**, 2.2.2.0 turns on all **16** axes (defaults all true) | vJoyConfig.cpp:30-51,186-275 | medium for zero-axis devices: our code omits `-a` when there are no axes (the `UNVERIFIED` comment at :309). With 2.2.2.0 that creates a 16-axis device; the read-back then sees 8 axes and reports "reads back as 8 axes, asked for 0 axes", so setup fails visibly rather than silently. With 2.1.9's vJoyConfig the same omission gives 8 axes and the same failure | verified (source); not run |
| 22 | `vJoyConfig -d <ids>` | gremlin/driver_jobs.py:322-324 | same (up to 16 ids) | vJoyConfig.cpp:290-302 | none | verified |
| 23 | `vJoyConfig -t` status list `Device %d:\tStatus: %s` (OWNED/FREE/BUSY/MISSING/UNKNOWN) | gremlin/driver_jobs.py:405-415 | same | vJoyConfig.cpp:975-980,1231 | none | verified |
| 24 | `vJoyConfig -t <id>` report: `Device:`, `Buttons:`, `Continous POVs:`, `Axes:` tokens | gremlin/driver_jobs.py:366-402 | same labels; `Axes:` now prints **16** tokens (X Y Z Rx Ry Rz Sl0 Sl1 then Wheel Accelerator Brake Clutch Steering Aileron Rudder Throttle, `-` if absent). Our parser zips with the 8 names, so the extra 8 are ignored | vJoyConfig.cpp:1037-1072 | low: extra axes on a device are invisible to the read-back (ties in with row 18) | verified |
| 25 | `vJoyConfig` exit code ignored, read-back decides | gremlin/driver_jobs.py:286-292 | consistent with source (argument errors print a message, no non-zero exit traced) | vJoyConfig.cpp `PrintMessage` paths | none | unverified (exit codes not fully traced) |

## Conclusion

Gremlin-Platforms is compatible with vJoy 2.2.2.0 for everything it does today. All 24
functions we bind exist in the shipped DLL with the same signatures; the version check
passes (driver 2.2.2.0 reports 0x222, driver 2.1.9 reports 0x219); `DriverMatch` is
never called by us or inside the DLL, so a 2.2.2.0 DLL on a 2.1.9 driver only differs
in the larger position struct, which the 2.1.9 driver accepts and which keeps our axes,
buttons and hats at the same offsets.

Things to watch (none break current use):
1. Zero-axis devices (row 21): omitting `-a` means "all 16 axes" in 2.2.2.0; the
   read-back catches it and setup fails. Fix would be to pass `-a` with no names, which
   2.2.2.0's parser treats as "all axes off" (unverified: `cl_isParamExist` with no
   params after `-a` was not traced).
2. Devices with 2.2.2.0's extra axes (rows 18, 24): set up outside Gremlin, they won't
   match DirectInput by axis count and are left out with a note.
3. vJoyConfig.exe is an optional component of the vJoy installer (row 20).
