# Steam Controller (2026) input: design

Status: design only. Not approved for building, and no code or spec has changed.
Date: 2026-11-06.

## 1. Goal

Let the user pick their Steam Controller as an input device in Gremlin-Platforms and map its controls like any other stick. Through vJoy, the Xbox pad, keyboard or mouse, it can then drive games that don't use Steam Input.

## 2. The hardware on this PC

- The controller is the **Steam Controller (2026)**. It connects through its wireless USB dongle, which Windows calls "Steam Controller Puck" (VID 28DE, PID 1304).
- The firmware was updated on 2026-11-06 at about 16:02, which is when Windows saw the bootloader PIDs 1007 and 1005.
- The dongle has these interfaces:
  - MI_00: a serial port.
  - MI_02 to MI_05: four controller slots. MI_06 is also listed.
  - Each slot has three HID collections:
    - COL01: mouse (lizard mode).
    - COL02: keyboard (lizard mode).
    - COL03: vendor-defined. The raw controller state arrives here.
- The wired and Bluetooth versions of the controller use PIDs 1302 and 1303. These are on the list but not tested, because we don't have the hardware.

## 3. Approach (recommended): a second joystick reader

Today every physical stick comes from one reader, `dill.dll`, called through `dill.DILL`. A new reader, `steam_controller`, reads the dongle over raw HID and offers the **same calls and callbacks** as `dill.DILL`. A small facade combines the two readers, and the few places that call `dill.DILL` directly call the facade instead.

The Steam Controller then reaches the program as an ordinary **external device**. Home card, Device Bindings, its own module file, input claims, calibration, Listen, Trace, live values and Device Pack all work without code written for it.

### Rejected options

- **OSC-style built-in input** (fixed id, hand-wired into Home and the lists): about 30 files refer to the OSC id by name, and this route would give no calibration, Device Bindings or claims.
- **A fake `DeviceSummary` inside DILL's list**: several places ask `dill.dll` about a device by its id (axis value, exists, info). The DLL doesn't know this device, so those calls would fail.
- **Relying on Steam Input**: Steam builds its virtual pad only for games it launches, and that pad loses the gyro, trackpads and back paddles.

### Pieces

| Piece | File(s) | Job |
|---|---|---|
| Reader | `gremlin/steam_controller.py` (new) | Finds the dongle's COL03 interfaces, reads reports on its own thread, turns lizard mode off, tracks connect and disconnect, and keeps the last value of every input. Builds `DeviceSummary`-shaped and `InputEvent`-shaped objects. |
| Report parser | inside the reader, or `gremlin/steam_controller_report.py` | Pure functions from report bytes to values (unit-testable without hardware). |
| Facade | `gremlin/joystick_readers.py` (new) | `device_count`, `info_by_index`, `info_by_guid`, `device_exists`, `get_axis`, `get_device_name`, `set_input_event_callback`, `set_device_change_callback`. Each call goes to DILL or to the Steam reader, by device id. |
| Callers switched to the facade | `device_initialization.py`, `event_handler.py` (`_run`, `terminate`, axis value), `input_cache.py`, `modules/hardware.py`, `trace_watch.py` | Replace the direct `dill.DILL` calls. |
| HidHide | `hidhide_driver.py:714` `_is_gaming` | Add 28DE:1304 (and 1302, 1303) to the gaming-device list. |
| Spec, map, Help | `claude/program-map/02-devices-input.md` (new section Q), `03-modules.md` if needed, program-map file list, Help "Home and devices" | Under change control, written and approved before code. |

### Device identity

- Each controller slot gets a stable device id derived from the dongle's serial number and the slot (a `uuid5` under a fixed namespace). The same controller in the same slot keeps its module file and calibration across restarts.
- Name: "Steam Controller". A second controller on the same dongle becomes "Steam Controller (2)", using the existing twin naming (02 S11).
- VID/PID are reported as 28DE/1304, so Device Information shows them.

## 4. Layout: what the user maps

Values use the same ranges as DILL: axes from -32768 to 32767, buttons on or off, and a hat for the D-pad.

### Axes (18)

| # | Input | Raw | Sent as |
|---|---|---|---|
| 1 | Left stick X | s16 | as is |
| 2 | Left stick Y | s16, up is + | negated (up is −, same as an Xbox pad, 02 S140) |
| 3 | Right stick X | s16 | as is |
| 4 | Right stick Y | s16, up is + | negated |
| 5 | Left trigger | 0..32767 | scaled to −32768 (rest) .. 32767 (pulled), as the Xbox pad triggers are |
| 6 | Right trigger | 0..32767 | same |
| 7 | Left pad X | s16 | as is |
| 8 | Left pad Y | s16 | negated |
| 9 | Right pad X | s16 | as is |
| 10 | Right pad Y | s16 | negated |
| 11 | Left pad pressure | u16 | scaled to −32768..32767 |
| 12 | Right pad pressure | u16 | same |
| 13–15 | Gyro X / Y / Z (turn rate) | s16 | as is |
| 16–18 | Tilt / accelerometer X / Y / Z | s16 | as is |

### Buttons (26) and hat (1)

- Buttons 1–10 follow the Xbox pad order already in the program (02 S140): 1 A, 2 B, 3 X, 4 Y, 5 LB, 6 RB, 7 View, 8 Menu, 9 L3, 10 R3.
- Buttons 11–26: 11 Steam, 12 Quick Access (…), 13 L4, 14 L5, 15 R4, 16 R5, 17 LT full click, 18 RT full click, 19 left pad click, 20 right pad click, 21 left pad touch, 22 right pad touch, 23 left stick touch, 24 right stick touch, 25 left grip touch, 26 right grip touch.
- Hat 1: the D-pad.

## 5. Behaviour (draft spec statements for 02 section Q)

- **Q-S1.** The program should read a Steam Controller (2026) through its dongle (28DE:1304) without Steam. It should list each connected controller as a physical device named "Steam Controller", with the layout in section 4.
- **Q-S2.** While it reads a controller, it should keep the controller out of mouse-and-keyboard mode. It does this by sending the "lizard mode off" setting when it opens the controller, then again at least every 3 s.
- **Q-S3.** It should treat the dongle's "controller connected" and "controller disconnected" messages as plug-in and unplug (02 S25–S29). A controller that turns off is unplugged, and its held buttons are let go. Plugging the dongle in or out does the same for every controller on it.
- **Q-S4.** When Steam is running, the program should still read the controller. Help should say Steam reads it too, and to turn off Steam Input for the controller (or close Steam) so the two don't both act on it.
- **Q-S5.** If the dongle can't be opened (for example, another program holds it exclusively), the program should log that once and carry on without it.
- **Q-S6.** It should stop reading and release the dongle when the program exits, so the controller goes back to Steam or lizard mode.
- **Q-S7.** The Input Tester is a separate program. It is left out for now (see section 9).

## 6. Threads and timing

- One reader thread per opened slot interface. The thread uses an overlapped `ReadFile` with a short timeout, so it can stop quickly.
- Input arrives at about 250 Hz.
- To keep event traffic down, an event is sent only when a value changes, as DILL does.
  - Gyro and accelerometer change on almost every report, so they would send up to 250 events per second for each of 6 axes.
  - To be decided at build time: a small change threshold, or a 125 Hz limit, for axes 13–18. A test checks that event handling keeps up.
- Callbacks run on the reader thread, as DILL's do. The existing code already moves work to the main thread (02 S40).

## 7. Testing

- **Unit tests, no hardware:**
  - The parser, using recorded report bytes: every button bit, axis scaling, Y negation, trigger scaling.
  - The facade, which sends each call to the right reader by id.
  - Connect and disconnect messages turn into device-change callbacks.
- **Integration, with a fake reader:**
  - A fake Steam reader feeds events through `EventListener` to a claimed input and an action, along the real path.
- **Hands-on, with the user:**
  1. Run a probe script first that prints the live reports, and check the byte layout against section 4. The layout comes from a community source, not Valve.
  2. Then map a stick and a button to vJoy and check in a game.

## 8. Risks

- **Unverified layout.** The source is [konikvranik/steam-puck-bridge](https://github.com/konikvranik/steam-puck-bridge) `docs/protocol.md`, which takes its layout from SDL3 `SDL_hidapi_steam_triton.c`. The probe step comes first because of this.
- **More than 8 axes.** DILL devices have at most 8 axes, and some code may assume that limit. Before building, find every place that reads `axis_map` and check it with 18 axes. A first look found about 25 uses, all of which loop over `axis_count` or the list.
- **Steam running at the same time.** Both programs read the same reports, and that is allowed. Steam may turn lizard mode back on, or remap the controller.
- **Steam Input actions.** If Steam Input is on for a game, Steam's own output and Gremlin's output could both reach that game. Help covers this (Q-S4).
- **Battery and rumble.** Not covered. Possible later work: show battery, and send rumble from the Xbox pad's rumble.

## 9. Left out (possible follow-ups)

- Input Tester support (spec M), which uses its own scan.
- Wired USB (1302) and Bluetooth (1303), which can't be tested without the hardware.
- The original 2015 Steam Controller (1102/1142). It uses a different report format.
- Gyro as mouse-style aiming. That would map axes 13–15 through `map_to_mouse` or `axis_delta`, which may need its own rate-to-motion setting.

## 10. Questions for the user

1. D-pad as hat 1 (recommended, same as the Xbox pad) or as 4 buttons?
2. Gyro and accelerometer: include them now, as axes 13–18 (recommended), or leave them for a later step?
3. Steam open: should Gremlin warn when Steam is running while a Steam Controller is in use, or only explain it in Help (recommended)?

## 11. Effort (timings.md)

- Probe script: 3–8 min (agent fix/feature), plus hands-on time with the controller.
- Build: about 30 min end to end (batch: agents ~10, lead checks and map ~5, tests ~5, commit ~2, CI ~10).
- The table has no rows for a new hardware reader, so this is a rough figure.
