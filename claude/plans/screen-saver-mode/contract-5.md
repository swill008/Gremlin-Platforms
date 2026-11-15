# Screen Saver Mode, batch 5: disabling the devices that never go quiet (2026-11-15)

Spec: claude/program-map/12-screen-saver-mode.md S21-S27 (approved by the user 2026-11-15, "build it").
Base rules: contract.md (every agent follows them). Measured: with the four always-streaming devices
disabled, one power-off stayed off 30 s (pnputil /disable-device, then /enable-device restored them, OK).

## HARD SAFETY RULE FOR EVERY AGENT
Never disable or enable a real device, never run pnputil, never elevate, never start the helper for real,
in tests or probes. Tests fake the runner, the elevation and the status reader. No exceptions.

## Pieces and owners
| Agent | Files |
|---|---|
| SSM-HELPER | new `gremlin_device_helper.py` (repo root, the helper program's entry), new `gremlin/device_helper_protocol.py` (shared message format + checks), `joystick_gremlin.spec` (a third exe "Gremlin Device Helper.exe", uac_admin=True, sharing _internal like the Input Tester), `.github/workflows/release-exe.yml` (check the third exe exists), new `test/unit/test_ssm_helper.py` |
| SSM-DISABLE | new `gremlin/device_disable.py` (journal, status reader, helper launcher and connection, disable/enable flows, recovery, retry on device arrival), new `test/unit/test_ssm_disable.py` |
| SSM-CORE5 | `gremlin/screen_saver_mode.py` (two hooks), `test/unit/test_ssm_core.py` |
| SSM-UI5 | `gremlin/ui/screen_saver_mode_model.py`, `qml/WindowScreenSaverMode.qml` (S26 message + Try again only; no other window change), `joystick_gremlin.py` (recovery at start, helper stop at quit), `gremlin/ui/option.py` (_HIDDEN row for the saved list), `test/unit/test_ssm_ui.py`, `ssm_ui_fakes.py`, `ssm_ui_smoke.py`, `test/unit/test_ssm_e2e.py` |
| SSM-DOCS5 | map pages 12 (sections 2-6, 10, 11; mark S21-S27 built pending reports), 01 (the third exe, the build), 02 if devices section lists exes, README counts, glossary, `qml/help/tools.js`, `release-notes/1.0.38.md` |

## Protocol (`gremlin/device_helper_protocol.py`, SSM-HELPER owns)
```python
PIPE_PREFIX = r"\\.\pipe\gremlin-device-helper-"
STATES = ("to be disabled", "disabled", "disable failed", "to be enabled", "enabled", "enable failed")
def valid_device_id(text: str) -> bool   # starts with "HID\", no quote, no control chars, <= 260
def make_request(op: str, ids: list[str]) -> dict   # op: "ping" | "disable" | "enable" | "quit"
def check_request(req: dict, journal: dict) -> tuple[list[str], dict[str, str]]
    # (ids allowed, {id: "refused: <why>"}): disable only ids the journal has as "to be disabled",
    # enable only ids the journal has as "to be enabled"; bad ids refused.
# Response: {"ok": bool, "results": {id: "done" | "refused: …" | "error: …"}}
```
Transport: `multiprocessing.connection` with family "AF_PIPE". Gremlin is the Listener on PIPE_PREFIX + a random
hex name, with a random authkey; Gremlin writes the authkey to `<data folder>\screen saver mode\helper.key`
(created fresh, user-only), the helper reads it then deletes it. Helper args:
`--pipe NAME --journal PATH --key PATH --parent PID`. The helper connects as Client, then serves requests until
"quit", the connection closes, or the parent process is gone (checked about once a second). The helper does the
action with `pnputil /disable-device "<id>"` / `/enable-device` (subprocess, no shell, bounded 30 s) and reports.

## Journal and flows (`gremlin/device_disable.py`, SSM-DISABLE owns)
```python
JOURNAL = "<data folder>\screen saver mode\devices.json"   # util.data_folder()
class Journal:            # load/save atomic (temp + os.replace); entries {id: {"name","state","time","result"}}
def device_status(device_id: str) -> str   # "enabled" | "disabled" | "not present"; CM_Locate_DevNodeW +
                                           # CM_Get_DevNode_Status (DN_HAS_PROBLEM + CM_PROB_DISABLED = 22); no admin
class DeviceDisabler:     # manager() singleton
    def helper_running(self) -> bool
    def start_helper(self, on_done: Callable[[bool, str], None]) -> None  # ShellExecuteExW "runas" of the helper
        # exe next to the program when frozen; from source: python.exe gremlin_device_helper.py; waits for the
        # connection up to 60 s (the user answers the confirmation) on a program thread; refused (1223) → False
    def stop_helper(self) -> None        # "quit", close
    def disable(self, devices: list[tuple[str, str]]) -> None   # (name, id); async on a program thread:
        # write each "to be disabled" (journal saved) → request → for each: device_status → "disabled" or
        # "disable failed" (reason) → saved; log INFO per device + trace (trace.screen_saver)
    def enable_pending(self) -> None     # async: every journal entry not "enabled": "to be enabled" → request →
        # status → "enabled" / "enable failed"; "not present" stays "to be enabled"
    def recover_at_start(self) -> None   # if any entry not "enabled": start_helper then enable_pending
    def on_device_arrival(self) -> None  # retry enable_pending for entries still "to be enabled" (hook from
        # EventListener().device_change_event, wired by SSM-UI5)
    def status_text(self) -> str         # "" when fine; S26 text when the helper should run but isn't
```
Only ids the journal lists are ever enabled; a device the user disabled themselves is never touched.
All Windows work on program threads (gremlin.threads), bounded waits, never the main thread.

## Core hooks (`gremlin/screen_saver_mode.py`, SSM-CORE5 owns)
`ScreenSaverMode.set_device_hooks(before_power_off: Callable[[], None] | None, after_input: Callable[[], None] | None)`.
`before_power_off` is called (exception-safe, logged) just before the Power off displays timer's first power-off;
the power-off is sent right after it (it must return fast; the disabling runs async; the keep-off re-send covers
the seconds until the devices are off). `after_input` is called once at the first counted keyboard/mouse input that
ends a keep-off (S23). Neither is called while off.

## UI wiring (SSM-UI5)
- S27: the last Refresh Devices result saved in setting `global/screen-saver-mode/devices` (List of
  {"name","instance_id"}; hidden in Options via _HIDDEN; History name "Saved Devices list") and loaded at start
  into the Devices list (the list is otherwise unchanged).
- S25: the model starts the helper (DeviceDisabler.start_helper) when Screen Saver Mode is on, Power off displays is
  on and the saved list is not empty — at start, when those settings change, after a Refresh that fills the list;
  not again after a refusal until **Try again**. Stops it at quit (joystick_gremlin shutdown).
- S21/S23 hooks: before_power_off → disable(saved list) when the helper runs; after_input → enable_pending.
- S24: joystick_gremlin start → DeviceDisabler.recover_at_start() (before the window shows; async).
- S26: text "Devices can't be disabled: the helper isn't running" + **Try again** button (objectNames
  "ssmHelperMessage", "ssmHelperTryAgain"), only when the helper should run and doesn't.
- device_change_event → DeviceDisabler.on_device_arrival.
