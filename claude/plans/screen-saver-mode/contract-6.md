# Screen Saver Mode, batch 6: Wake PC (2026-11-16)

Spec: claude/program-map/12-screen-saver-mode.md S3 (changed), S28-S32, decision D-12-SSM-WAKE-PC
(approved by the user 2026-11-16, "a, build"). Base rules: contract.md and contract-5.md (every agent
follows them, including the HARD SAFETY RULE: never disable/enable a real device, never run pnputil,
never elevate, never start the helper, the screen saver or a power-off for real, never send input).
Glossary row "Wake PC" (claude/glossary.md) gives every on-screen word.

## Pieces and owners
| Agent | Files |
|---|---|
| SSM-CORE6 | `gremlin/screen_saver_mode.py`, `test/unit/test_ssm_core.py` |
| SSM-UI6 | `gremlin/ui/screen_saver_mode_model.py`, `qml/WindowScreenSaverMode.qml`, `gremlin/ui/option.py`, `test/unit/test_ssm_ui.py`, `test/unit/ssm_ui_fakes.py`, `test/unit/ssm_ui_smoke.py` |
| SSM-E2E6 | `test/unit/test_ssm_e2e.py` |
| SSM-DOCS6 | map page 12 sections 2-6, 10, 11 (NOT section 8 or 12: the lead wrote them), `claude/program-map/README.md` row 12, `qml/help/tools.js` |

## Core (SSM-CORE6) — `gremlin/screen_saver_mode.py`
Already in the file (uncommitted, from the lead): `physical_device(instance_id) -> str` (upper-case id of
the first ancestor that is neither HID nor a USB `&MI_` interface) and `_is_part`. Keep them; test them with
faked cfgmgr32 or leave them to the e2e/real path (they make real Windows calls; tests must not need a
specific PC).

```python
HOLD_NO_WAKE_DEVICE = "no_wake_device"     # S31; a hold like the others: both timers wait

@dataclass(frozen=True)
class InputDevice:
    physical_id: str            # physical_device() of the raw input device's instance id
    name: str                   # _device_name() of one of its parts ("" allowed)
    kinds: tuple[str, ...]      # sorted subset of ("keyboard", "mouse")

class WindowsApi:
    def input_devices(self) -> list[InputDevice]   # GetRawInputDeviceList keyboards (1) and mice (0),
        # grouped by physical id; parts with no path skipped; never raises (logs, returns [])
    def device_physical_id(self, handle: int) -> str   # physical_device(instance_id_from_path(raw_device_path(h)))

class ScreenSaverMode:
    def set_wake_devices(self, physical_ids: Iterable[str]) -> None
        # S3/S28: the ticked devices. Keyboard/mouse input whose device's physical id is not in the set does
        # not count (not the idle clock, not last-reset, not after_input). Program input (no handle) always
        # counts. Empty set while the mode is on -> hold HOLD_NO_WAKE_DEVICE (S31), checked first after
        # "locked". Called from the main thread; may be called before apply().
    def set_press_listener(self, listener: Callable[[str, str], None] | None) -> None
        # S30: while set, every key DOWN (raw keyboard, RI_KEY_BREAK clear) and mouse BUTTON DOWN (any
        # RI_MOUSE_*_BUTTON_DOWN flag; not move, not wheel) from a device is reported on the MAIN thread as
        # listener(physical_id, "keyboard" | "mouse"), from ANY device (ticked or not), at most once per
        # device per kind per second. Delivered through the existing listener->main event queue, drained by
        # tick() or a short main timer; the listener thread never calls Qt. Works while the mode is on; when
        # the mode is off the model starts listening itself via start_detection()/stop_detection().
    def start_detection(self) -> bool   # starts the InputClock listener for detection even while the mode
    def stop_detection(self) -> None    # is off (no timers run); stop_detection leaves it running when the
                                        # mode is on. Idempotent.
```
Handle -> physical id is looked up once per handle and cached, on the listener thread (never per event,
never on the main thread). Status: `hold == HOLD_NO_WAKE_DEVICE` when S31 applies. Trace (S16):
"wake devices: N ticked", "not counted: <name> (<kind>) is not ticked" once per device until it changes,
"press: <name> (<kind>)" per reported press. Tests: FakeApi gains `input_devices`, `device_physical_id`;
note_input gets the physical id through the cache; one test per rule above, each failing on the old code.

## UI (SSM-UI6)
- Setting `global/screen-saver-mode/wake-pc`: List of {"id": physical_id, "name": str, "kinds": [..],
  "ticked": bool, "how": "key" | "click" | "you" | "untick" | ""}; hidden in Options (_HIDDEN), History
  title "Wake PC list". Default []. `apply_saved()` also calls `manager().set_wake_devices(ids ticked)`.
- Model: rows = saved rows merged with `WindowsApi().input_devices()` (read on a program thread when the
  tab opens and on device change; never on the main thread), new devices unticked (S29); unplugged saved
  rows stay (shown "not connected"). Properties/slots: `wakeRows` (list of dicts name/kinds text/ticked/
  note/connected/id), `setWakeTicked(id, bool)` (how "you" / "untick"), `wakeTabOpen(bool)` (True:
  set_press_listener + start_detection; False: clear + stop_detection), press -> tick with how "key" or
  "click" and save. Status line S31 text exactly from the glossary when hold == HOLD_NO_WAKE_DEVICE.
- QML: a TabBar at the top of WindowScreenSaverMode with "Settings" (all current content, unchanged) and
  "Wake PC". objectNames: "ssmTabs", "ssmTabSettings", "ssmTabWake", "ssmWakeList", "ssmWakeHeading",
  row delegates "ssmWakeRow" with "ssmWakeTick", "ssmWakeName", "ssmWakeKinds", "ssmWakeNote", and
  "ssmWakeProgramsNote" for "Input sent by programs (RustDesk, remote desktop) always counts.".
  Window theme and widths follow the existing page; nothing else on the Settings tab changes.

## E2E (SSM-E2E6) — `test/unit/test_ssm_e2e.py`
Real path with the module's existing fakes (W dict): ticked set from the saved setting reaches the core;
input from an unticked device doesn't reset; program input does; nothing ticked -> Waiting line, no timer
fires; tab open + key press on a new device -> ticked + saved + counts; restart keeps ticks (two runs).
Add `W` keys as needed: "input_devices", "physical_ids" {handle: id}.

## Docs (SSM-DOCS6)
Page 12 sections 2-6, 10 (close SSM-WAKE-PC-NOT-BUILT as "built, pending the user's test" and open
SSM-WAKE-PC-UNTRIED), 11 (new test names/counts from the agents' reports: leave counts as TBD for the
lead), README row 12 (S count 32, gap count recomputed from section 10), `qml/help/tools.js` Screen Saver
Mode help: the Wake PC tab in the user's words.
