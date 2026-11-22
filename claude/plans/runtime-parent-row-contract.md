# Contract: the runtime as a required parent row, layout b (2026-11-21)

> **2026-11-22 note:** decision 10a (this contract's Tools › Drivers rows, the runtime download and the helper's vcredist update) was reversed by the user on 2026-11-22 (1b: "only the installer needs the code and update for c++"). Only setup's rows and runtime step stay; the Tools › Drivers, `gremlin/drivers.py`, `driver_jobs.py` and helper parts below were built and then removed. See 01 D-01-RUNTIME-ROW.

Approved by the user 2026-11-21 ("Make Microsoft visual c++ in the driver
selection as a parent but greyed out and checked as required ... then as a
child without a default check ... Then option b", then "8a, 9b, 10a, go").
Picture: the user's screenshot edited (scratchpad option-b-parent.png).

- The drivers box's first row: **Microsoft Visual C++ Runtime**, ticked and
  greyed (required, can't be unticked), no explanation in brackets; on the
  right its status like the drivers: "not installed" or the installed version
  (8a: shown on every install / every time the window opens).
- Indented child row under it, unticked by default:
  **Check and download an updated Visual C++ Runtime** (9b). Replaces the old
  separate tick box "Check for an updated Microsoft Visual C++ Runtime" below
  the box (removed).
- 10a: Tools › Drivers gets the same parent and child rows.
- Layout b (setup's Drivers page): a thin line, then a bold **vJoy devices**
  heading with "Preset" and its box on the right of the same line; the column
  headings (X ... Hats) inside the list box in a light grey band; rows padded
  from the left border; below the box the hint ("Each device needs its own
  number of axes, buttons or hats, so Gremlin-Platforms can tell them
  apart."), then one line with **Add device** on the left and "Showing ..."
  on the right.

## 1. Data and helper (owner: DATA, `gremlin/drivers.py`, `gremlin/driver_jobs.py`)

- `RUNTIME` stays outside `DRIVERS`; its comment changes: Tools › Drivers and
  the helper now handle the update (10a).
- `RUNTIME_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"`.
- Job: `Job(op="update", driver="vcredist", files=[{"kind": "download", ...}])`
  using the same file-entry shape the driver downloads use. `read_jobs`
  accepts driver "vcredist" for op "update" only.
- Helper (`driver_jobs.run_job`): for driver "vcredist": check the file
  (`check_download`-style: valid signature, signer "Microsoft Corporation"),
  read its file version; if not newer than `runtime_version()` -> result done
  with "the installed runtime is already this version or newer" (nothing
  run); else run it with `RUNTIME.install_args`; exit codes
  `RUNTIME_DONE_CODES` are done, 3010 sets restart needed; others failed with
  the code. Bounded timeout like the drivers.
- A download helper for the model, e.g. `fetch_runtime(dest_dir, fetch=...)
  -> path` (follows redirects; tests use a fake fetch; never the network).

## 2. Tools › Drivers (owner: UI, `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`)

- Rows list starts with the runtime parent row: name, status (installed
  version from `drivers.runtime_version()`, or "not installed"), ticked,
  greyed, not clickable. Then the child row (indented, unticked) with the 9b
  wording. Then vJoy, ViGEmBus, HidHide as today.
- Ticking the child adds the "vcredist" update job on Apply (the download is
  done the same way driver downloads are done today; the helper does the
  check and run). Results line names it like the drivers.

## 3. Setup (owner: SETUP, `installer/gremlin_platforms.iss`)

- Drivers box: parent row (greyed, ticked; status "not installed" or the
  installed version) and the indented child row (unticked, 9b wording) in the
  box; the old tick box below the box and its caption constant go; the
  child keeps the existing newest-runtime logic (HEAD, SHA, signature,
  version, fallback). When the runtime is missing, setup still installs its
  carried copy as today (the parent row's tick means that).
- Layout b as above. Keep 5 rows visible at 100% if possible (the window may
  grow via the second WizardSizePercent figure); report the count.
- Ready page memo wording follows the new caption.

## 4. Tests

- E2E (`test/unit/test_drivers_e2e.py`): Tools › Drivers with the child ticked
  -> job file -> helper with a fake runtime file: newer -> run with
  `/install /quiet /norestart`, 3010 -> restart needed; same or older -> not
  run, done; bad signature -> failed, nothing run.

## 5. Docs

- lead: program map 01 S187/S193 and 06 S185 (+ section 2/3/5/10/12 as
  touched), glossary rows.
- DOCS: `qml/help/tools.js` and `qml/help/getting_started.js`.

## Owners

| Agent | Files |
|---|---|
| DATA | `gremlin/drivers.py`, `gremlin/driver_jobs.py`, `test/unit/test_drivers.py`, `test/unit/test_driver_jobs.py`, `test/unit/test_device_helper_jobs.py` |
| UI | `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`, `test/unit/test_drivers_model.py`, `test/unit/test_drivers_window.py`, `test/unit/drivers_window_smoke.py` |
| SETUP | `installer/gremlin_platforms.iss`, `test/unit/test_installer_drivers.py` |
| E2E | `test/unit/test_drivers_e2e.py` |
| DOCS | `qml/help/*.js` |
| lead | this file, `claude/program-map/*`, `claude/glossary.md`, plans, todo, timings, builds, the test machine |
