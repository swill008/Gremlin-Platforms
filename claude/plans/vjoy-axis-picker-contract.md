# Contract: vJoy axes by name, newest runtime box, prompt in front (2026-11-21)

Batch approved by the user 2026-11-21 ("1a, 2a, 3b, 4a, 5a", "6a, go").
Plan: `claude/plans/vjoy-axis-picker.md`. Every agent works to this file.

## Facts verified in the test machine (11:09, vJoy 2.2.2.0)

- `vJoyConfig 1 -f -l -a x y sl0 -b 8 -p 0` and `vJoyConfig 2 -f -a rx sl1 -b 4 -p 1`
  both work. `vJoyConfig -t 1` prints `Axes: X Y - - - - Sl0 - - - - - - - - -`
  (one token per position, `-` for a missing axis; positions 1-8 are
  X Y Z Rx Ry Rz Sl0 Sl1, then 8 more we ignore).
- `https://aka.ms/vs/17/release/vc_redist.x64.exe` redirects to
  `https://download.visualstudio.microsoft.com/download/pr/<guid>/<SHA-256 upper case>/VC_redist.x64.exe`.
  Today the SHA-256 in that path is the bundled one (`CC0FF0EB…713B`), so a
  HEAD request (no download) tells whether Microsoft's newest differs from the
  bundled copy. This path pattern is observed, not documented: when the path
  has no 64-hex part, fall back to downloading and comparing the file version.

## 1. Data shape (owner: DATA, `gremlin/drivers.py`)

- `VJOY_AXES = ("x", "y", "z", "rx", "ry", "rz", "sl0", "sl1")` (unchanged).
- `VJoyDevice.axes: tuple[str, ...] = VJOY_AXES` — the ticked axis names,
  always lower case, always in `VJOY_AXES` order, no duplicates. Constructor
  callers pass a tuple/list; `__post_init__` normalises to a sorted tuple
  (order of `VJOY_AXES`). `problem()` names an unknown axis name.
- New `axis_label(name) -> str`: "X", "Y", "Z", "RX", "RY", "RZ", "SL0", "SL1".
- Job file (version stays 1; unreleased, no old reader): each device is
  `{"id": 1, "axes": ["x", "y", "sl0"], "buttons": 8, "hats": 0}`.
  `read_jobs`: `axes` must be a list of known names (a number or unknown name
  is a ValueError); missing `axes` means all eight.
- Presets unchanged in meaning: "full" = all eight axes, 128 buttons, 4 hats.

## 2. Helper (owner: DATA, `gremlin/driver_jobs.py`)

- `vjoy_setup`: `-a` followed by exactly the device's names, in order. Zero
  axes: no `-a` (still UNVERIFIED).
- `parse_report`: `axes` = the names whose position (1-8) is not `-`.
- Read-back compares the axis tuples, buttons and hats.
- `describe_device`: "3 axes (X, Y, SL0), 8 buttons, 0 hats"; one axis
  "1 axis (X)"; none "0 axes"; all eight "8 axes (X-SL1)". Singular only
  for exactly one, as today.

## 3. Tools › Drivers (owner: UI, `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`)

- Each device dict the model exposes has `"axes": [names]` (a list).
- Slots: `setDevice(index, axes: list, buttons, hats)` (axes a list of names;
  unknown names dropped) and `setAxis(index, name, on: bool)`.
- `WindowDrivers.qml`: each device row shows eight tick boxes labelled
  X Y Z RX RY RZ SL0 SL1 (from the model, not a QML list of its own if the
  model can provide it: expose `axisNames` / labels), then Buttons and Hats as
  today. Editing still switches the preset box to Custom. Summary text uses
  the same wording as `describe_device`.

## 4. Setup (owner: SETUP, `installer/gremlin_platforms.iss`)

a) **vJoy rows (2a).** Replace the Custom memo with a scrolling list of device
   rows: "vJoy N", eight tick boxes (X … SL1), a Buttons drop-down (0-128), a
   Hats drop-down (0-4), a remove button; **Add device** at the bottom (lowest
   free id, up to 16). The preset box stays above; a preset fills the rows,
   any edit switches it to Custom. Store axes as a bit mask internally
   (bit k = `VJOY_AXES[k]`); the job JSON writes the names list (section 1);
   reading the current layout from `vJoyConfig -t` uses positions (facts
   above). Check which VCL classes Inno 6.7.3's Pascal Script really has
   (e.g. `TScrollBox`/`TNewStaticText`/`TNewCheckBox`/`TNewComboBox`/
   `TNewButton`) before relying on one.
b) **Newest runtime box (6a).** An unticked tick box on the Drivers page,
   "Get Microsoft's newest Visual C++ Runtime", shown on every install. When
   ticked: ask Microsoft's link (HEAD, follow redirects, read the final URL);
   if the SHA-256 in the path equals the bundled one, log "Microsoft's newest
   is the copy setup carries" and download nothing; otherwise download it,
   check its signature (valid, signer CN=Microsoft Corporation, the same
   PowerShell check as the bundled copy), read its file version, and run it
   when it is newer than both the bundled copy and the installed runtime.
   Any failure: log it, and fall back to the bundled copy when the runtime is
   missing (unchanged path). The last page says which copy was used.
c) **Prompt in front (4a).** Start the helper's "runas" from setup's own
   window so Windows' administrator prompt opens in front: `ShellExecuteExW`
   with `hwnd = WizardForm.Handle` (or the documented Inno equivalent), and
   bring the wizard forward first. The lead checks it in the test machine.

## 5. Spec, map, Help, glossary (owner: DOCS)

- 01: the setup Drivers page statement(s) for the vJoy layout (rows, tick
  boxes by name, scrolling, Add device); S193 gains the newest-runtime box
  (6a); S190 (the one administrator prompt) gains "opens in front of setup"
  (4a). Each with `[changed 2026-11-21, user: 1a, 2a, 4a, 6a]` as fits.
- 06 S185: "each one's axes (tick X, Y, Z, RX, RY, RZ, SL0, SL1), buttons and hats".
- 12 S25a: device `axes` is a list of names.
- Program map sections 2/3/5/10/11 and README counts for the pages touched;
  section 12 decision rows; glossary row for the axis tick boxes and the
  runtime box wording; `qml/help/*.js` text for Tools › Drivers.

## Owners

| Agent | Files |
|---|---|
| DATA | `gremlin/drivers.py`, `gremlin/driver_jobs.py`, `test/unit/test_drivers.py`, `test/unit/test_driver_jobs.py`, `test/unit/test_device_helper_jobs.py` |
| UI | `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`, `test/unit/test_drivers_model.py`, `test/unit/test_drivers_window.py`, `test/unit/drivers_window_smoke.py` |
| SETUP | `installer/gremlin_platforms.iss`, `test/unit/test_installer_drivers.py` |
| E2E | `test/unit/test_drivers_e2e.py` |
| DOCS | `claude/program-map/*`, `claude/glossary.md`, `qml/help/*.js` |
| lead | this file, `claude/todo.md`, `claude/timings.md`, commits, builds, the test machine |

Any other file: ask the lead. Find other tests that build `VJoyDevice(axes=<int>)`
or read `"axes": <int>` and tell the lead (don't edit files you don't own).
