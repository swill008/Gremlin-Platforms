# vJoy layout: pick each axis by name (plan, 2026-11-21)

Status: **plan only, saved for later** (user, 2026-11-21: "lets do c, but save
the plan for now"). No spec, code or tests changed yet. Before building, the
spec change below goes to the user (CLAUDE.md change control rule 2).

## Why

The user disliked setup's Custom box (a text box of "axes, buttons, hats"
lines, e.g. `8, 128, 4`). Four options were drawn in the chat on 2026-11-21:
a) one row per device with drop-downs, b) presets only in setup, c) tick each
axis by name, d) a compact table of typed numbers. The user chose **c**.

## What c means

Each vJoy device row has eight tick boxes, X Y Z RX RY RZ SL0 SL1, instead of
an axis count, plus a Buttons choice (0-128) and a Hats choice (0-4).

```
vJoy 1  [x]X [x]Y [x]Z [x]RX [ ]RY [ ]RZ [x]SL0 [ ]SL1   Buttons [128 v]  Hats [4 v]   (x)
vJoy 2  [x]X [x]Y [ ]Z ...                                 Buttons [32 v]   Hats [1 v]   (x)
[+ Add device]                          Preset: [Custom v]
```

- Picking a preset fills the rows; changing any tick or list switches the
  preset box to Custom (same as today).
- Today's rule: a device has "the first N axes" in vJoyConfig order
  (`VJOY_AXES[:axes]` in `gremlin/driver_jobs.py`). With c, any set of axes
  is allowed, and vJoyConfig gets `-a` with exactly the ticked names.

## Spec change to put to the user first

- 01 S187 (setup Drivers page, vJoy layout): "axes" becomes a set of named
  axes, not a count; the Custom text box is replaced by the per-device rows.
- 06 S185-S188 (Tools › Drivers): the same axis set in its editor, so both
  places match (one owner: the data shape in `gremlin/drivers.py`).
- 12 S25a (helper jobs file): the device entry carries `axes` as a list of
  names (e.g. `["x","y","z","rx","sl0"]`), not a number. The job file
  version stays 1, because nothing is released (no legacy reader, CLAUDE.md
  "no legacy compatibility").

## Files it touches (for the split table when building)

| Group | Files |
|---|---|
| Data shape and helper | `gremlin/drivers.py` (`VJoyDevice.axes` → tuple of names), `gremlin/driver_jobs.py` (`vjoy_setup` passes the ticked names; read-back compares sets; `describe_device` wording, e.g. "5 axes (X, Y, Z, RX, SL0)") |
| Tools › Drivers | `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml` (tick boxes per device) |
| Setup | `installer/gremlin_platforms.iss` (`TVJoyDevices.Axes` → a set or bit mask; new per-device rows of `TNewCheckBox` + two `TNewComboBox`; Add/remove device; the job file writes the names; reading current devices from vJoyConfig `-t` gives the names) |
| Tests | `test_drivers.py`, `test_driver_jobs.py`, `test_drivers_model.py`, `test_drivers_e2e.py`, `test_drivers_window.py`, `test_installer_drivers.py` |
| Spec, map, Help | program-map 01, 06, 12 (sections 8, 10, 11, 12), `qml/help/*.js` for Tools › Drivers |

## Open points to check when the work starts

1. Setup page room: 16 devices × 8 tick boxes may need a scrolling area or
   one device shown at a time; check the page size in the test machine.
2. Verify, don't guess: confirm vJoyConfig accepts any axis set (e.g. X, Y,
   SL0 with no Z) and that `-t` reports which axes a device has, on the test
   machine before relying on it. The current code marks zero axes as
   UNVERIFIED (`driver_jobs.py` line 242).
3. Whether Gremlin's own vJoy output pages already show axes by name
   (`gremlin/ui/control_layout.py`, `qml/StatusPage.qml`) so the words match
   the glossary.

## Effort

No timing data for a setup-page rework. Rough guess 30-45 min end to end
(agents for setup, helper/data, Tools › Drivers, tests, docs in parallel;
build ~2 min per timings.md "local build"; a screen check in the test
machine).

## Answers (user, 2026-11-21)

1. 1a: change the spec as described (01 S187, 06 S185-S188, 12 S25a: axes by name).
2. 2a: setup shows a scrolling list of device rows, Add device at the bottom.

Related setup findings answered the same day (go in the same batch):

3. 3b: vJoyConfig error boxes when vJoy is present but the C++ runtime is
   missing: leave it.
4. 4a: make setup bring the drivers' administrator prompt to the front by
   starting the helper from setup's own window; verify in the test machine.
5. 5a: the runtime progress bar was seen moving in the user's run; closed.
6. 6a: an unticked "Get Microsoft's newest Visual C++ Runtime" box; setup still carries its own copy.
7. 6a+b (scrolling): keep the scroll bar and make the mouse wheel over the rows scroll the list too.
8. 7b: the host PC's vJoy 2.1.9 is not updated now (it blue-screened on an agent's `find /`; the rule against whole-disk searches stops the trigger).
9. 1a (feedback round): drop the paragraph under the runtime box; the box reads "Check for an updated Microsoft Visual C++ Runtime"; the vJoy section moves up, the box height stays. Scroll look (question 2): research first.
