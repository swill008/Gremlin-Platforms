# Contract: a vJoy update keeps the devices (2026-11-22, user: "build it")

Plan: `claude/plans/vjoy-update-keeps-devices.md`. Spec: 01 S187, 06 S185,
12 S25b (D-01-VJOY-UPDATE-KEEPS). Wording in the spec is exact; use it.

## 1. Helper and data (owner: HELPER: `gremlin/drivers.py`, `gremlin/driver_jobs.py`, their tests)

- Job file: the "update" job for driver "vjoy" may carry `devices` = the
  devices read before the update (same shape as vjoy_setup devices). Empty
  list = "couldn't be read" (no comparison).
- New op `"vjoy_restore"` (driver "vjoy", devices = the ones to put back):
  sets up exactly those devices with vJoyConfig (`-f`, read back like
  vjoy_setup), never deletes any other device. `read_jobs` accepts it.
- Around `update vjoy`: log "vJoy devices before the update: ..." (from the
  job's devices and/or `current_vjoy_devices`), run the update, read
  `current_vjoy_devices` again, log "vJoy devices after the update: ...",
  compare by id: **lost** = before devices missing after, or present with a
  different layout (axes/buttons/hats); **added** = ids present after but not
  before. Logging/comparing never fails the job (catch everything).
- Results: the job result gets `"lost": [device dicts]` and `"added": [ids]`
  (empty lists when none). `drivers.read_results` returns them (extend the
  result shape; keep old keys).
- Lost store: `vjoy_lost.json` in the program's data folder (the folder that
  holds configuration.json; find the existing helper for it) =
  `{"version": 1, "devices": [ ... ]}`. The helper writes it when lost is not
  empty (replacing older entries for the same ids); `vjoy_restore` removes the
  restored ids on success. Functions in drivers.py:
  `read_lost() -> list[VJoyDevice]`, `write_lost(devices)`, `clear_lost(ids)`.
- `drivers.lost_text(devices) -> str` and `drivers.added_text(ids) -> str` for
  the prompts/results (exact spec wording; one device "vJoy 4 (8 axes, 32
  buttons, 0 hats) is missing", several joined "vJoy 2 (...) and vJoy 4
  (...) are missing").
- `drivers.update_info_text(devices) -> str` (prompt 1, both versions).

## 2. Tools › Drivers (owner: UI: `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`, their tests)

- Before Apply runs a vJoy update: the update job carries the devices shown;
  the information box (title "vJoy update and your devices", text
  `drivers.update_info_text`, OK only) shows first (after the "what will
  happen" prompt and the Run prompt).
- After results: if the vJoy update's `lost` is not empty: box "The vJoy
  update lost a device" with the spec text, buttons **Repair Now** /
  **Repair Later**; Repair Now runs a second Apply with one `vjoy_restore`
  job; Repair Later closes it. `added` ids are named in the results line
  ("vJoy 1 was added by the vJoy update").
- Lost rows: `drivers.read_lost()` devices not present now show as rows
  marked "lost in the vJoy update" with a **Repair** button (runs a
  `vjoy_restore` job for that device). Use Style colours; no literals.

## 3. Setup (owner: SETUP: `installer/gremlin_platforms.iss`, `test/unit/test_installer_drivers.py`)

- When vJoy's op is 'update' (not silent): at Next on the Drivers page (or
  where the other prompts are), show the information box (MsgBox OK) with the
  same text as `drivers.update_info_text` (test compares). The update job's
  `devices` = `VJoyCurrent` (empty when not read).
- After the helper's results: if the vJoy update result has `lost`, show the
  task dialog/MsgBox "The vJoy update lost a device" with the spec text and
  buttons Repair Now / Repair Later (Inno: TaskDialogMsgBox with custom button
  captions, or a CreateCustomForm; pick the simplest that shows those exact
  captions). Repair Now: run the helper again (elevated, same way) with one
  `vjoy_restore` job; show its result. Repair Later: nothing (the helper
  already wrote vjoy_lost.json). Results line names `added` ids.

## 4. Tests (owner: E2E: `test/unit/test_drivers_e2e.py`)

Real path with the fake runner: before = vJoy 2 (x y z, 32, 0); the update
makes the fake vJoyConfig report vJoy 1 (default) and no vJoy 2 -> results
lost = [vJoy 2], added = [1]; vjoy_lost.json written; Tools › Drivers model
shows the lost row; Repair (vjoy_restore) sets up vJoy 2 only, deletes
nothing (vJoy 1 stays), clears vjoy_lost.json; nothing lost -> no prompt
data, no file.

## 5. Docs (owner: DOCS: `qml/help/*.js`, `claude/glossary.md`, `claude/program-map/*` except the new S187/S185/S25b text, `release-notes/1.1.1.md`, `claude/todo.md` 0m)

## Owners

| Agent | Files |
|---|---|
| HELPER | `gremlin/drivers.py`, `gremlin/driver_jobs.py`, `test/unit/test_drivers.py`, `test/unit/test_driver_jobs.py`, `test/unit/test_device_helper_jobs.py` |
| UI | `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`, `test/unit/test_drivers_model.py`, `test/unit/test_drivers_window.py`, `test/unit/drivers_window_smoke.py` |
| SETUP | `installer/gremlin_platforms.iss`, `test/unit/test_installer_drivers.py` |
| E2E | `test/unit/test_drivers_e2e.py` |
| DOCS | as above |
| lead | contract, plan, timings, build, test machine, commit, release |

## 6. Follow-up (2026-11-22, user 1a, 2a; found in the test machine)

The user added a device and updated vJoy in one setup run: the check ran
after the update but before the vjoy_setup job, reported vJoy 2 lost, then
vjoy_setup put it back. Fix:

- HELPER2 (`gremlin/drivers.py`, `gremlin/driver_jobs.py`, their tests): when
  a job file holds `update vjoy` followed by `vjoy_setup`, the comparison runs
  after the vjoy_setup job: before = the update job's devices, after = the
  devices read at the end; devices the vjoy_setup job doesn't list (removed on
  purpose) don't count as lost; lost/added are reported on the **last vJoy
  job of the run** (the vjoy_setup result) and the update result carries
  none. `drivers.prune_lost(current: list[VJoyDevice], path=None)` removes
  remembered devices present again with the same layout; the helper calls it
  at the end of every vJoy job (update, vjoy_setup, vjoy_restore).
- UI2 (`gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`, tests): read
  lost/added from whichever vJoy result carries them (the last one); call
  `drivers.prune_lost(current)` when the current devices are read.
- SETUP2 (`installer/gremlin_platforms.iss`, test): read lost/added from the
  last vJoy job's result (the vjoy_setup one when present).
- E2E2 (`test/unit/test_drivers_e2e.py`): update + edited set-up in one run ->
  no lost when the set-up lists the device; a device the set-up doesn't list
  (removed on purpose) isn't lost; a device the set-up lists but that is still
  missing at the end is lost; prune clears a present device.
