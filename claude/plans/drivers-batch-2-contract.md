# Contract: Drivers pages batch 2 (2026-11-22)

Approved by the user 2026-11-22: to-do 0c (14a: at least one axis), 0h (1a:
devices in use), 0i (2a: one axis-name table, Set B), 0j (Tools › Drivers in
setup's style, drawing in the chat; 1b grow-then-scroll in Tools › Drivers
only, 2a keep the ✕ per row, 3b setup keeps Add device), "4a go", "5b commit
together after". Spec: 06 S185 and 01 S187 (written by the lead 2026-11-22).

Open (lead will message UI): what Tools › Drivers does with devices held by
Gremlin-Platforms' own Run. Until then treat only vJoyConfig's BUSY/OWNED.

## 1. One axis-name table (owner: NAMES)

`gremlin/axis_names.py` (imports nothing; the Input Tester uses it):

```python
@dataclass(frozen=True)
class AxisName:
    number: int        # 1-8, what profiles store
    long: str          # "X Axis" ... "Slider 1", "Slider 2"
    short: str         # "X" "Y" "Z" "Rx" "Ry" "Rz" "S1" "S2"
    vjoy_config: str   # "x" "y" "z" "rx" "ry" "rz" "sl0" "sl1" (vJoyConfig -a / -t)
    usage: int         # 0x30 ... 0x37
AXES: tuple[AxisName, ...]          # in number order
def long_name(number: int) -> str   # unknown -> f"Axis {number}"
def short_name(number: int) -> str  # unknown -> f"A{number}"
```

Long: X Axis, Y Axis, Z Axis, X Rotation, Y Rotation, Z Rotation, Slider 1,
Slider 2. Every reader uses it: `gremlin/types.py` AxisNames.to_string,
`gremlin/modules/output.py` (AXIS_WORDS goes), the short-name readers
(Input Tester, wiring, trace_watch, input_pairing, module_pairing,
xbox_viewer), `vjoy/vjoy.py` (AxisCode values from `usage`),
`qml/OutputModuleView.qml` if it has its own words. `AXIS_SHORT` goes (no
compatibility alias). `AxisNames.to_enum` goes if nothing calls it.

## 2. Data and helper (owner: DATA)

`gremlin/drivers.py`:
- `VJOY_AXES = tuple(a.vjoy_config for a in axis_names.AXES)` (same values).
- `VJOY_AXIS_LABELS = tuple(a.short for a in axis_names.AXES)`.
- `can_untick_axis(dev: VJoyDevice, name: str) -> bool`: False when `name` is
  the device's only ticked axis.
- `in_use_warning(ids: list[int]) -> str`: "" for none; one: "vJoy 4 is in use
  by another program. Changing it can stop that program's controls working
  until it restarts. Change it anyway?"; several: "vJoy 1 and vJoy 4 are in
  use by another program. Changing them can stop that program's controls
  working until it restarts. Change them anyway?" (three+: "vJoy 1, vJoy 2 and
  vJoy 4 are ...").
`gremlin/driver_jobs.py`:
- `parse_status(text) -> dict[int, str]` (id -> upper-case status word, all
  listed devices). `parse_status_list` stays, built on it.
- `busy_vjoy_devices(runner) -> list[int]`: ids whose status is BUSY or OWNED
  (vJoyConfig is its own process, so both mean another process holds it).
- `vjoy_setup` refuses a job with an axis-less device? No: the UI/setup stop
  it; the helper keeps the read-back check.

## 3. Tools › Drivers (owner: UI)

`gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml` per 06 S185 (layout,
grow-then-scroll, ✕ per row, Devices box, rows always shown, short labels
from `drivers.VJOY_AXIS_LABELS`, last axis can't be unticked, busy rows from
`driver_jobs.busy_vjoy_devices` read with the device layout off the main
thread, the Yes/No warning before Apply when a busy device is changed or
removed: model slot `inUseWarning()` -> `drivers.in_use_warning(...)`, QML has
no rule of its own; order with the alike warning: in-use first, then alike).

## 4. Setup (owner: SETUP)

`installer/gremlin_platforms.iss` per 01 S187: headings S1, S2 (vJoyConfig
still gets sl0/sl1); last ticked axis can't be unticked; busy rows from the
`vJoyConfig -t` status lines ("in use by another program" on the row); at
Next, the same in-use Yes/No wording before the alike warning; silent install
unchanged. A test in `test/unit/test_installer_drivers.py` checks the .iss
headings and the in-use wording against `axis_names` / `drivers`.

## 5. Tests (owner: E2E)

`test/unit/test_drivers_e2e.py`: a fake runner whose `-t` lists vJoy 2 BUSY
-> `busy_vjoy_devices` -> Tools › Drivers model marks it and `inUseWarning`
names it when it's edited or removed, not when untouched; the last axis can't
be unticked through the model; the job's `-a` names stay sl0/sl1 while labels
are S1/S2.

## 6. Docs (owner: DOCS)

`qml/help/*.js`, `claude/glossary.md` (axis names row, Set B; in-use wording;
Tools › Drivers layout words), `claude/program-map/*` except the S185/S187
text the lead wrote: section 12 decisions D-06-DRIVERS-LAYOUT,
D-01-VJOY-ONE-AXIS, D-01-VJOY-IN-USE, D-AXIS-NAMES (page 02 or 09, where axis
names live), every other spec statement naming Slider/Dial/SL0/S1 words,
sections 2/3/10/11 for the touched files, the to-do lines 0c/0h/0i/0j.

## Owners

| Agent | Files |
|---|---|
| NAMES | `gremlin/axis_names.py`, `gremlin/types.py`, `gremlin/modules/output.py`, `gremlin/common.py`, `gremlin/input_cache.py`, `action_plugins/common.py`, `vjoy/vjoy.py`, `gremlin/input_tester/devices.py`, `gremlin/modules/wiring.py`, `gremlin/trace_watch.py`, `gremlin/ui/input_pairing.py`, `gremlin/ui/module_pairing.py`, `gremlin/ui/xbox_viewer.py`, `qml/OutputModuleView.qml`, tests pinning their words |
| DATA | `gremlin/drivers.py`, `gremlin/driver_jobs.py`, `test/unit/test_drivers.py`, `test/unit/test_driver_jobs.py`, `test/unit/test_device_helper_jobs.py` |
| UI | `gremlin/ui/drivers_model.py`, `qml/WindowDrivers.qml`, `test/unit/test_drivers_model.py`, `test/unit/test_drivers_window.py`, `test/unit/drivers_window_smoke.py` |
| SETUP | `installer/gremlin_platforms.iss`, `test/unit/test_installer_drivers.py` |
| E2E | `test/unit/test_drivers_e2e.py` |
| DOCS | `qml/help/*.js`, `claude/glossary.md`, `claude/program-map/*`, `claude/todo.md` lines 0c/0h/0i/0j |
| lead | this file, plans, timings, builds, the commit |
