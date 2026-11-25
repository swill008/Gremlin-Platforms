# Contract: device counts of the last time away (2026-11-25)

Gap SSM-API-DEVICES-BACK, page 12 S38, D-12-DEVICE-COUNTS (user: "1a, 2a, build it").
One owner: `DeviceDisabler` counts what Windows confirmed. No compatibility with
the old `(count, probe)` tuple.

## gremlin/device_disable.py (DIS)

`class SwitchRecord`: one time away's switching; thread-safe (own small lock);
no file or Windows reads.
- `SwitchRecord(asked: int, busy: Callable[[], bool])`; attribute `asked: int`
- `busy() -> bool`: cheap, never blocks
- `note_off(device_id)`; `note_back(device_id)` (counts only an id noted off; repeats count once)
- `counts() -> tuple[int, int]`: (off, back)

`DeviceDisabler.disable(devices) -> SwitchRecord` (asked = len(devices); busy =
`not self.wait_idle(0)`). The record becomes the current one when its job
STARTS on the worker (an enable job queued earlier belongs to the older record).
- `note_off`: Windows read DISABLED after the helper's answer, or the device is
  ours and already disabled. Not: failed, skipped, undone (S34), disabled by someone else.
- `note_back`: in `_enable`, wherever the journal is set to ENABLED for it
  (also "was already enabled").
- A device plugged in later counts then (same `_enable`). The next record never
  changes an older one; leftovers from an older time away never count.

## gremlin/screen_saver_mode.py (CORE)

`PowerOffWait`: a typing.Protocol with `asked`, `busy()`, `counts()` (the core
still imports nothing from device_disable). The hook returns it or None.
The core keeps the record with the power-off, and with last_away when keep-off
ends by input; `status().last_away` fills "devices_off"/"devices_back" from
`counts()` at each read (0, 0 without a record), in both places that build it.
A raising `busy()`/`counts()` is logged and gives not busy / (0, 0).
`_devices_off` and the placeholder 0 go. Keys of last_away unchanged.

## gremlin/ui/screen_saver_mode_model.py (CORE)

`_before_power_off` returns `disabler.disable(devices)`. `_last_away_text(away)`
loses `pending` and reads both counts from away. The Devices back on row (S39) is unchanged.

## gremlin/control_api.py: no change (passes last_away through).
