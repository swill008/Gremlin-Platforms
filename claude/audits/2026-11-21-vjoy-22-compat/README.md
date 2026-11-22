# vJoy 2.2.2.0 compatibility study (2026-11-21)

Asked by the user ("have we done a study to see if 2.2.0 is compatible with my
program? are the two programs the same?"), answer 12a. Three parts run in
parallel: `notes.md` (what changed, from GitHub), `code.md` (every vJoy use in
our code against the 2.2.2.0 source), `vm.md` (the test machine with vJoy
2.2.2.0 installed by our setup).

## Answer

**Compatible.** Gremlin-Platforms works with vJoy 2.2.2.0 for everything it
does today, and with the mix on the user's PC (driver 2.1.9, our shipped
library 2.2.2.0).

- Same program: 2.2.2.0 is Shaul Eizikovich's vJoy carried on (forks
  shauleiz -> jshafer817 -> njz3 -> BrunnerInnovation); same driver, library
  and config code; 2.2.0/2.2.1 fixed force feedback, 2.2.2.0 is a Windows
  10/11 rebuild signed by Brunner Elektronik AG (x64 only). Verified (notes).
- Limits unchanged: 16 devices, 128 buttons, 4 hats. New axis types added
  (wheel, throttle, brake, ...). Verified (notes).
- Our 24 library functions exist with the same parameters; the version check
  passes (0x222 for 2.2.2.0, 0x219 for 2.1.9; we need 0x218); the
  library/driver match check is never called. Verified (code).
- In the test machine: our shipped library drove vJoy 1 (axes, buttons 1 and
  128, hat) and Windows read the values back, including button 128; the
  program found all four devices (128/127/126/125 buttons) and linked them
  all ("MATCH"), no errors. Verified (vm).

## The blue screen

vJoy issue #12 (BrunnerInnovation/vJoy, open, filed 2026-11-08): bugcheck
0x3B in `vJoy_EvtDeviceFileCreate` when the device is opened without a device
name, on **both 2.1.9 and 2.2.2.0**; the trigger named is MSYS2/Git `find /`,
exactly our crash. Updating vJoy would not have prevented it; the "no
whole-disk search" rule (memory `no-whole-disk-find`) does. No newer vJoy
release exists.

## Follow-ups found (not fixed; for the user to decide)

1. A device with no axes ticked: `gremlin/driver_jobs.py` leaves out `-a`,
   vJoyConfig then gives all axes, the read-back fails visibly (medium; the
   new tick boxes make it possible). Fix unverified.
2. Devices made outside Gremlin-Platforms with 2.2's new axis types aren't
   matched by the program (left out with a note) (medium).
3. vJoyConfig.exe is an optional part of vJoy's installer and can be missing
   (low).
4. 2.2.2.0's own open issues: installer hangs on some Windows 11 PCs (#1, #9,
   #10), `DllX64Location` registry value not written (#7), all devices share
   one GUID (#4).

## Not verified

The program's own output through a profile in the test machine (no physical
controller there); force feedback; vJoy devices 2-4 fed with values.
