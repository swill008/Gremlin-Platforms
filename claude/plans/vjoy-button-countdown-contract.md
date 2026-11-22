# Contract: vJoy button countdown and the "alike" warning (2026-11-21)

Approved by the user 2026-11-21: "1a, 2a, 3a, 4a, 5a, go".

- 1a: a new device's button count comes from its number: vJoy N gets 129 - N
  (vJoy 1 = 128, vJoy 2 = 127, ... vJoy 16 = 113).
- 2a: the preset "2 devices, full" becomes 128 and 127 (today both 128: the
  program can't tell them apart and leaves both out, a bug).
- 3a: one shared rule in setup and Tools › Drivers.
- 4a: the warning shows when the user moves on (setup: Next on the Drivers
  page; Tools › Drivers: Apply), a Yes/No box; No goes back to the rows.
- 5a: "the same" means the same number of axes, buttons and hats: exactly the
  program's own rule in `gremlin/device_initialization.py` (around line 361:
  `(axis_count, button_count, hat_count)`; alike devices are left out with
  "... have the same number of axes, buttons and hats, so they can't be told
  apart ...").
- The user may keep alike devices (the warning's Yes); nothing blocks them.

## 1. Shared rule (owner: DATA, `gremlin/drivers.py`)

- `default_buttons(vjoy_id: int) -> int`: `129 - vjoy_id`, clamped to 0-128.
- `new_device(vjoy_id: int) -> VJoyDevice`: all eight axes, `default_buttons(id)`
  buttons, 4 hats. `VJoyDevice`'s own field default stays 128 (callers that
  build a device on purpose keep their numbers).
- `PRESETS`: "1 device, full" = `[new_device(1)]`; "2 devices, full" =
  `[new_device(1), new_device(2)]` (128, 127).
- `layout_key(dev: VJoyDevice) -> tuple[int, int, int]`:
  `(len(dev.axes), dev.buttons, dev.hats)`.
- `alike_devices(devices) -> list[list[int]]`: groups (2 or more ids, each
  sorted, groups sorted by first id) of devices with the same `layout_key`.
- `alike_warning(groups) -> str`: "" when none; otherwise one sentence per
  group, e.g. "vJoy 1 and vJoy 3 have the same number of axes, buttons and
  hats, so Gremlin-Platforms can't tell them apart and won't use them." Three
  or more: "vJoy 1, vJoy 2 and vJoy 4 have ...". The caller adds the question
  ("Continue anyway?").

## 2. Tools › Drivers (owner: UI, `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`)

- `setDeviceCount(n)`: devices added get `new_device(id)` (lowest free id, as
  today); existing devices keep their numbers.
- Before Apply runs the jobs: when `alike_devices` of the devices to be set is
  not empty, the window shows a Yes/No box with `alike_warning(...)` + " Continue
  anyway?"; Yes applies, No returns to the editor. Expose it from the model
  (e.g. property/slot `alikeWarning` the QML reads before calling `apply`), so
  the QML has no rule of its own.

## 3. Setup (owner: SETUP, `installer/gremlin_platforms.iss`)

- Add device: the new row gets `129 - id` buttons (same rule; Pascal can't
  import Python: a test in `test_installer_drivers.py` checks the .iss formula
  and the presets against `gremlin.drivers.default_buttons` / `PRESETS`).
- Preset "2 devices, full": 128 and 127.
- Next on the Drivers page: when two or more rows have the same (number of
  ticked axes, buttons, hats), a Yes/No message box with the same wording as
  `alike_warning` + " Continue anyway?". No stays on the page. A silent
  install shows no page and no box.
- A label `VJoyHint` directly above the "Showing ..." line, one or two lines,
  text from the lead (the user is choosing it now). Use this placeholder until
  told: `Each device needs its own number of axes, buttons or hats, so Gremlin-Platforms can tell them apart.`
  Make room for two lines; keep 5 rows visible at 100% if possible, otherwise
  report the count (the window may grow a little via WizardSizePercent).

## 4. Tests

- E2E (`test/unit/test_drivers_e2e.py`): the "2 devices, full" preset goes
  through `write_jobs`/`read_jobs` and the helper's `vjoy_setup` with 128 and
  127; `drivers.layout_key` agrees with the `(axis_count, button_count,
  hat_count)` key `gremlin/device_initialization.py` uses (feed alike and
  unlike layouts to both, real path where possible).

## 5. Spec, map, Help, glossary

- lead: program map 01 S187 and 06 S185 statements, section 10 gap
  (VJOY-ALIKE-PRESET: the old preset made two alike devices), section 12
  decision D-01-VJOY-COUNTDOWN.
- DOCS: `qml/help/*.js` (Tools › Drivers and Getting started: the countdown and
  the warning), `claude/glossary.md` rows for the warning and hint wording.

## Owners

| Agent | Files |
|---|---|
| DATA | `gremlin/drivers.py`, `test/unit/test_drivers.py` |
| UI | `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`, `test/unit/test_drivers_model.py`, `test/unit/test_drivers_window.py`, `test/unit/drivers_window_smoke.py` |
| SETUP | `installer/gremlin_platforms.iss`, `test/unit/test_installer_drivers.py` |
| E2E | `test/unit/test_drivers_e2e.py` |
| DOCS | `qml/help/*.js`, `claude/glossary.md` |
| lead | this file, `claude/program-map/*`, `claude/plans/*`, `claude/todo.md`, `claude/timings.md`, builds, the test machine, commits |
