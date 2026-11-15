# Screen Saver Mode: build contract (2026-11-15)

Spec: `claude/program-map/12-screen-saver-mode.md` S1-S15 (approved by the user 2026-11-15).
Study and measurements: `claude/plans/oled-idle-watcher-study.md`.
Mock-up: `claude/drafts/screen-saver-mode-mockup.svg`.

## Decided by lead (authorised, small details; reported to the user)
- Input source: **Raw Input** (RegisterRawInputDevices, RIDEV_INPUTSINK, usage page 0x01, usages 0x02 mouse and
  0x06 keyboard) on a hidden top-level window on its own program thread (`gremlin.threads.start`) with its own
  message loop, NOT a low-level mouse hook (a Python LL mouse hook would sit in every mouse movement of the PC;
  the existing `windows_event_hook.MouseHook` also skips WM_MOUSEMOVE). Raw input does not slow input down.
  No other part of the program registers raw input (checked). Note: RIDEV_INPUTSINK needs a real (hidden)
  window, not a message-only window.
- Gremlin's own input (S3): RAWKEYBOARD.ExtraInformation / RAWMOUSE.ulExtraInformation equal to
  `windows_event_hook.OWN_KEY_MARK` is Gremlin's own and does not count. `keyboard.py` already marks keys;
  `sendinput.py` mouse functions must mark their SendInput with the same value (dwExtraInfo).
- Default action: Power off displays. Windows' time of 0 ("never") with no typed time: no action, status says
  "Windows never turns the display off: type a time to use Screen Saver Mode" (or "…never starts the screen saver").
- Wait time from Windows: screen saver = `HKCU\Control Panel\Desktop` ScreenSaveTimeOut (seconds; only when
  SCRNSAVE.EXE is set); display off = active power scheme SUB_VIDEO VIDEOIDLE, AC or DC by GetSystemPowerStatus.
- Hold-offs, checked at each tick: locked workstation (S11), full screen (S7, SHQueryUserNotificationState
  QUNS_BUSY=2, QUNS_RUNNING_D3D_FULL_SCREEN=3, QUNS_PRESENTATION_MODE=4), display flag (S15,
  CallNtPowerInformation(SystemExecutionState=16) & ES_DISPLAY_REQUIRED). While held, the idle clock still
  runs but the action waits; when the hold ends the countdown starts again (idle counted from the end of the hold).

## Files and owners (one owner per file)
| Agent | Files |
|---|---|
| SSM-CORE | new `gremlin/screen_saver_mode.py`; `gremlin/sendinput.py` (mark own mouse input) |
| SSM-SCAN | new `gremlin/hid_report_scan.py`, new `gremlin/power_requests.py` |
| SSM-UI | new `gremlin/ui/screen_saver_mode_model.py`, new `qml/WindowScreenSaverMode.qml`, `qml/main_commands.js`, `qml/Main.qml` (Tools item only), `joystick_gremlin.py` (settings + start/stop), QML type registration where the program does it |
| SSM-TEST | new tests only: `test/unit/test_ssm_*.py` (+ a smoke script if needed); updates to existing tests that pin the Tools menu / command list / help links |
| SSM-DOCS | `claude/program-map/12-screen-saver-mode.md` (sections 2-6, 10, 11), `claude/program-map/01-app-shell.md` (Tools menu lines), `claude/program-map/02-devices-input.md` (sendinput mark), `claude/program-map/README.md` counts, `claude/glossary.md`, Help: `qml/help/tools.js` (+ `qml/help_links.js` if new link ids) |

## API: gremlin/screen_saver_mode.py (SSM-CORE)
```python
ACTION_SCREEN_SAVER = "screen_saver"; ACTION_POWER_OFF = "power_off"

@dataclass
class Settings:
    enabled: bool = False
    action: str = ACTION_POWER_OFF
    wait_override_s: int = 0          # 0 = use Windows' time
    hold_fullscreen: bool = True

@dataclass
class Status:
    enabled: bool
    listening: bool                   # raw input registered and alive
    idle_s: float                     # Gremlin's idle time
    windows_idle_s: float             # GetLastInputInfo
    wait_s: int                       # the wait in use (0 = none)
    windows_wait_s: int               # Windows' value for the chosen action (0 = never/none)
    wait_from_windows: bool
    hold: str                         # "" | "locked" | "fullscreen" | "display_request"
    hold_program: str                 # "" (the combined flag doesn't name programs)
    fired: bool                       # action done in this idle period
    problem: str                      # "" | "no_screen_saver" | "windows_never" | "not_listening"
    remaining_s: float                # until the action, 0 when none

class WindowsApi:                     # the only place that calls Windows; tests pass a fake
    def screen_saver_path(self) -> str: ...
    def screen_saver_wait_s(self) -> int: ...
    def display_off_wait_s(self) -> int: ...
    def windows_idle_s(self) -> float: ...
    def display_required(self) -> bool: ...
    def fullscreen_busy(self) -> bool: ...
    def locked(self) -> bool: ...
    def start_screen_saver(self, path: str) -> bool: ...
    def power_off_displays(self) -> None: ...

class InputClock:                     # raw input thread; tests use note_input() only
    def start(self) -> bool: ...      # False when it could not register
    def stop(self) -> None: ...
    def listening(self) -> bool: ...
    def last_input(self) -> float: ...        # gremlin.clock.monotonic() of the last counted input
    def note_input(self, own: bool = False) -> None: ...

def manager() -> "ScreenSaverMode": ...       # the one instance

class ScreenSaverMode:
    def __init__(self, api: WindowsApi | None = None, clock_: InputClock | None = None): ...
    def apply(self, settings: Settings) -> None: ...  # on/off starts/stops the InputClock and the 1 s timer
    def settings(self) -> Settings: ...
    def tick(self) -> None: ...        # once a second on the main thread (gremlin.threads.main_timer); tests call it
    def status(self) -> Status: ...    # cheap; UI polls it once a second
    def shutdown(self) -> None: ...    # at quit
```
Rules: tick() fires the action once per idle period (S6) when idle >= wait and no hold and no problem; input
after firing resets `fired`. Off (S2): no raw input registered, no timer. Tests never call the real WindowsApi.

## API: gremlin/hid_report_scan.py, gremlin/power_requests.py (SSM-SCAN)
```python
@dataclass
class DeviceRate:
    name: str; instance_id: str; usage_page: int; usage: int; reports_per_s: float
def scan(seconds: float = 4.0, should_stop: Callable[[], bool] | None = None) -> list[DeviceRate]
    # every HID interface (SetupDi, HidD_GetHidGuid), opened read-only (GENERIC_READ, share read|write), reads
    # input reports with overlapped I/O for `seconds`, bounded waits; keyboards/mice that refuse open are skipped;
    # returns those with reports_per_s >= 2, highest first. Runs on the caller's thread.

@dataclass
class ProgramRequest:
    name: str; path: str; kinds: list[str]; ignored: bool    # kinds: "Display", "System", "Awaymode", "Execution"
@dataclass
class RequestsResult:
    ok: bool; error: str; programs: list[ProgramRequest]
def list_requests(runner: Callable | None = None) -> RequestsResult
    # ONE elevated run (ShellExecuteExW "runas", cmd /c powercfg /requests and powercfg /requestsoverride into a temp
    # file, wait bounded 60 s); parses both; overridden programs are listed with ignored=True even when not asking now.
    # Refused: ok False, error "Administrator rights were refused."
def set_ignored(name: str, ignored: bool, runner: Callable | None = None) -> tuple[bool, str]
    # elevated `powercfg /requestsoverride PROCESS <name> DISPLAY SYSTEM AWAYMODE` (on) or with no types (off).
```
`runner` is the elevation seam: tests pass a fake; no test elevates or runs powercfg.

## UI (SSM-UI)
- Command `tools.screenSaverMode`, text "Screen Saver Mode…", group "Tools"; Main.qml Tools menu bottom group:
  OSC Monitor, Screen Saver Mode…, History, Options. Opens `WindowScreenSaverMode.qml` with `openTool`.
- Settings (cfg.register, shown names as the window shows them, so History names them; S10):
  section "global", group "screen-saver-mode": "enabled" Bool False, "action" String "power_off",
  "wait-override-s" Int 0, "hold-fullscreen" Bool True. joystick_gremlin applies them to `manager()` at start and
  on change; `manager().shutdown()` at quit.
- objectNames: window "screenSaverModeWindow"; "ssmEnabled", "ssmActionScreenSaver", "ssmActionPowerOff",
  "ssmWaitBox", "ssmWaitClear", "ssmWindowsWait", "ssmHoldFullscreen", "ssmListening", "ssmIdleText",
  "ssmWindowsIdleText", "ssmHoldText", "ssmProblemText", "ssmRefreshDevices", "ssmRefreshPrograms",
  "ssmDeviceList", "ssmProgramList", row switch "ssmIgnoreSwitch", "ssmProgramsMessage".
- Texts: as the spec and mock-up; descriptions under the buttons: "Lists the devices that never go quiet and keep
  Windows thinking someone is using the PC." / "Lists the programs asking Windows to keep the display on. Needs
  administrator rights each time."
- Scans run through `threads.run_for(owner, name, work, deliver)`; buttons show "Checking… (4 s)" while busy.

## Rules for every agent
- Repo E:\Users\Stacie\Documents\GitHub\Gremlin-Platforms. Venv python
  C:\Users\Stacie\AppData\Local\pypoetry\Cache\virtualenvs\joystickgremlin-4UY8FelE-py3.13\Scripts\python.exe.
- Pipe every command: `PYTHONUNBUFFERED=1 <cmd> 2>&1 | <venv python> tools/agent_log.py <AGENT>`; pytest -v.
- Only your files. No git commit/push/stash/checkout/reset. Don't touch untracked files you didn't make
  (tools/scan_selftest.py, claude/plans/steam-controller-design.md belong to another session).
- Never: start the screen saver, power off displays, run powercfg, elevate, change HidHide, send keyboard/mouse
  input, or run the real program on screen. Program-code runs use a temp USERPROFILE and offscreen Qt.
  Tests use fakes (WindowsApi, InputClock.note_input, runner). No network.
- Threads via gremlin.threads, bounded waits, gremlin.clock (program thread rules).
- Run only your tests while working; before reporting: `python test/run_tests.py <your test files>` and
  `tools/pyright_baseline.py`, ruff on your files.
- Report: start/end (date +%H:%M), files, results, map lines for the docs agent, anything not verified.
