# Screen Saver Mode: vJoy wake lines and the profile restart (2026-11-24)

Source: the user's Turn displays off now test at 04:24 on the installed build (2fe32018), trace.log.

## What the trace showed
- 04:24:39.5 keep off started; 04:24:40.1 "Devices re-read: 3 connected, 1 gone"; 04:24:41.75 Profile stopped; 04:24:42.56 Profile started.
- Wakes #1-#3: last input "vJoy - Virtual Joystick (game controller) 0.0 s before"; last vJoy/Xbox write 0.0 s, 1.6 s, 3.1 s ago. Wake #4: Steam Controller (mouse) 0.8 s before.
- 04:25:08.6 keep off ended on the G502; devices re-enabled; 04:25:09.6 a second Profile stopped/started.

## Verified (code)
- The restart: S21 switches devices off before the power-off, the device list changes, `EventListener` emits `device_change_event` (gremlin/event_handler.py:387-396), and `Backend._device_change` (gremlin/ui/backend.py:535) with the user's Device change behavior = Reload (default) stops and starts the profile. Same again when the devices come back.
- The vJoy name: Gremlin marks only its own keyboard and mouse input as "own" (`note_input(own=...)`); game controller HID reports are noted as SEEN_CONTROLLER with the device's name (gremlin/screen_saver_mode.py:1405-1440). vJoy and ViGEm devices are not recognised as Gremlin's own output.
- The write age: `reset_vjoy()` (gremlin/modules/output.py:1181) releases vJoy at Stop without setting `_last_write_at`, so a release (and acquire at start) is not counted as a write.

## Unverified
- That vJoy reports from the stop/start actually woke the displays (timing correlation only).
- Wake #3's vJoy report (3.1 s after the last counted write): source not found.
- What turned the screens off on the night of 2026-11-23 (the display reports work, so not Windows).

## Upstream
- develop: the same setting (`global/behavior/device-change-behavior`, default Reload) and the same stop+start in `Backend._device_change`.
- v13.1: any device change always stops the profile (`_device_change_cb`).
- Neither has Screen Saver Mode switching devices off, or wake tracing.
