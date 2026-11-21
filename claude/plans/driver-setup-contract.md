# Driver setup build: shared contract (2026-11-21)

Spec: 01 S187-S192 (D-01-DRIVERS), 06 S185-S188 (D-06-DRIVERS), 12 S25 changed,
S25a, S25b (D-12-HELPER-DRIVERS), 12 S16a (D-12-RESTART-SOURCE). Plan and
facts: claude/plans/driver-setup-installer.md. Build "up to the point of
testing": no real driver is installed, no installer is compiled (ISCC), nothing
downloaded; real runners are blocked under test.

## Files and owners

| Agent | Files (only these) |
|---|---|
| CORE | gremlin/drivers.py (new), gremlin/driver_jobs.py (new), test/unit/test_drivers.py, test/unit/test_driver_jobs.py |
| HELPER | gremlin_device_helper.py, test/unit/test_device_helper_jobs.py |
| UIPY | gremlin/ui/drivers_model.py (new), test/unit/test_drivers_model.py |
| QML | qml/WindowDrivers.qml (new), qml/DialogDriverPrompt.qml (new), qml/XboxDriverCheck.qml, the Home page file that shows Home notices, gremlin/modules/output.py `vjoy_driver_problem` hint text only, test/unit/test_drivers_window.py (+ smoke script) |
| ISS | installer/gremlin_platforms.iss, test/unit/test_installer_drivers.py |
| BUILD | tools/fetch_drivers.py (new), installer/build_installer.ps1, .github/workflows/release-exe.yml, .gitignore, licenses/vigembus.txt, licenses/hidhide.txt, test/unit/test_fetch_drivers.py |
| SSM | gremlin/screen_saver_mode.py (`_trace_reset` / the "input after action" line only), test/unit/test_ssm_core.py |
| E2E | test/unit/test_drivers_e2e.py |
| DOCS | qml/help/ (the chapter for installing and outputs), claude/program-map/01, 06, 12 sections 2-5, 10, 11 and README counts, claude/glossary.md check |
| lead | joystick_gremlin.py, qml/main_commands.js, qml/Main.qml, final map pass, commit |

## gremlin/drivers.py (CORE): no Qt, no program imports (the helper imports it)

```python
@dataclass(frozen=True)
class DriverInfo:
    key: str                 # "vjoy" | "vigembus" | "hidhide"
    name: str                # "vJoy" | "ViGEmBus" | "HidHide"
    bundled_version: str     # "2.2.2.0" | "1.22.0" | "1.5.230"
    bundled_file: str        # file name in {app}\drivers\
    sha256: str              # of the bundled file ("" = not known yet: ViGEmBus until downloaded)
    signer_prefix: str       # "Brunner Elektronik AG" | "Nefarius Software Solutions"
    repo: str | None         # "BrunnerInnovation/vJoy" | None (ViGEmBus retired) | "nefarius/HidHide"
    asset_regex: str | None  # e.g. r"vJoySetup_v[\d.]+_Win10_Win11\.exe" | None | r"HidHide_[\d.]+_x64\.exe"
    install_args: tuple[str, ...]
    restart_codes: tuple[int, ...]

DRIVERS: dict[str, DriverInfo]   # ordered vjoy, vigembus, hidhide
```
Bundled files and SHA-256:
- vjoy: `vJoySetup_v2.2.2.0_Win10_Win11.exe`, 5,302,312 bytes,
  `ef569a3105cd301b89580f18f60c66b339e95296acf2c0dfcaf4b4bbf8ab68fe`;
  args `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-` (+ `/LOG=<file>`);
  exit 0 ok, 8 restart; others failed.
- vigembus: `ViGEmBus_1.22.0_x64_x86_arm64.exe`, 6,278,576 bytes,
  `89220a7865076b342892f98865f3499fb7c4cfd673159e89d352c360fd014c6a`
  (downloaded 2026-11-21 with the user's permission; signature valid, Nefarius Software Solutions e.U.); args `/exenoui /qn /norestart`
  (UNTESTED); exit 0 ok, 3010/1641 restart.
- hidhide: `HidHide_1.5.230_x64.exe`, 8,078,016 bytes,
  `f4bbbcb82e6258641b887c74bc81c4c5f66e4aa811808dfc304347687b7605f6`;
  args `/exenoui /qn /norestart` (UNTESTED); exit 0 ok, 3010/1641 restart.

Detection (read-only, `winreg`, injectable `reg` for tests):
- vjoy: HKLM `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1` `DisplayVersion`.
- vigembus: file version of `%SystemRoot%\System32\drivers\ViGEmBus.sys`
  (this PC 1.21.442.0); fallback an Uninstall entry DisplayName "ViGEm Bus Driver" DisplayVersion.
- hidhide: HKLM `SOFTWARE\Nefarius Software Solutions e.U.\HidHide` `Version`.
- HidHide uninstall: the Uninstall entry whose DisplayName starts "HidHide": `UninstallString` (an MSI product code -> `msiexec /x {code} /qn /norestart`).

Functions:
```python
def version_tuple(text: str) -> tuple[int, ...]
def compare(a: str, b: str) -> int          # -1/0/1, missing parts are 0
def installed_version(key: str, reg=None) -> str   # "" = not installed
@dataclass(frozen=True)
class DriverStatus: key: str; name: str; installed: str; bundled: str; state: str
    # state: "missing" | "older" | "same" | "newer"
def status(key: str, reg=None) -> DriverStatus
def all_status(reg=None) -> list[DriverStatus]
@dataclass(frozen=True)
class Release: version: str; url: str; name: str
def latest_release(key: str, fetch=None, timeout: float = 5.0) -> Release | None
    # GitHub /repos/{repo}/releases/latest; None for no repo, no network, error
def sha256_of(path) -> str
def check_bundled(path, info: DriverInfo) -> str      # "" ok, else why
def check_download(path, info: DriverInfo, signer=None) -> str
    # "" when the Windows signature is valid and the signer's CN starts with
    # info.signer_prefix; `signer(path) -> (valid: bool, subject: str)`;
    # the real one: PowerShell Get-AuthenticodeSignature, bounded 30 s
@dataclass
class VJoyDevice: id: int; axes: int = 8; buttons: int = 128; hats: int = 4
    # axes 1-8 = X Y Z RX RY RZ SL0 SL1 (first N); buttons 0-128; hats 0-4 continuous
PRESETS: dict[str, list[VJoyDevice]]  # "1 device, full", "2 devices, full"
@dataclass
class Job:
    op: str                   # "install" | "update" | "remove" | "vjoy_setup"
    driver: str
    files: list[dict]         # [{"path": str, "kind": "download"|"bundled"}], download first
    devices: list[VJoyDevice] # vjoy_setup only
@dataclass
class JobResult:
    state: str                # "waiting" | "running" | "done" | "failed"
    message: str = ""
    restart: bool = False
    used: str = ""            # "bundled" | "download" | ""
def write_jobs(path, jobs: list[Job]) -> None
def read_jobs(path) -> list[Job]                       # raises ValueError on bad files
def write_results(path, results: list[JobResult], finished: bool) -> None  # atomic (tmp + replace)
def read_results(path) -> tuple[list[JobResult], bool]  # ([], False) when missing/partial
def app_dir() -> Path | None          # folder of the frozen exe, else None
def pending_path(app: Path) -> Path   # app / "drivers" / "pending.json"
def read_pending(app: Path) -> dict | None
    # {"hidhide": {"version": "1.5.230", "file": "<path>", "kind": "bundled"|"download"}}
def write_pending(app: Path, data: dict) -> None
def clear_pending(app: Path) -> None
```
Job file: `{"version": 1, "jobs": [{"op", "driver", "files", "devices": [{"id","axes","buttons","hats"}]}]}`.
Results file: `{"version": 1, "finished": bool, "jobs": [{"state","message","restart","used"}]}` (same order as jobs).

## gremlin/driver_jobs.py (CORE): the work, used only by the helper

```python
Runner = Callable[[list[str], float], tuple[int, str]]   # (command, timeout) -> (exit code, output)
def real_runner(command, timeout) -> tuple[int, str]     # raises RealRunnerBlocked under pytest
def run_job(job: Job, runner: Runner, *, check_bundled=..., check_download=...) -> JobResult
    # install/update: try each file in order; a download that fails its check
    # is skipped (message says why) and the bundled copy is used; a bundled copy
    # that fails its SHA-256 is never run. Exit codes -> done / restart / failed.
    # remove (hidhide): msiexec /x {code} /qn /norestart from the Uninstall entry.
    # vjoy_setup: vjoy_setup(job.devices, runner).
def vjoyconfig_path() -> str      # %ProgramFiles%\vJoy\x64\vJoyConfig.exe
def vjoy_setup(devices, runner) -> tuple[bool, str, bool]   # (ok, message, restart)
    # per device: vJoyConfig <id> -f -a <first N of x y z rx ry rz sl0 sl1> -b <n> -p <hats>;
    # then `vJoyConfig -t <id>` read back and compared (exit code alone is never trusted)
def parse_report(text: str) -> list[VJoyDevice]   # vJoyConfig -t output
def current_vjoy_devices(runner) -> list[VJoyDevice]   # read-only (-t), for the window
```

## Gremlin Device Helper jobs mode (HELPER)

`"Gremlin Device Helper.exe" --jobs <job file> --results <results file> [--parent PID]`
(the pipe mode's `--pipe/--journal/--key/--parent` stay as they are; exactly one
mode). Reads the jobs, writes the results file with every job "waiting", then
runs them in order with `driver_jobs.run_job`, rewriting the results file at
each state change ("running", then "done"/"failed"), and `finished: true` at the
end. Logs to `<data folder>\logs\device_helper.log` when it can find it (else
`%TEMP%`). Never raises; exit 0 when the results were written, 2 bad jobs file.
The module docstring keeps "the only part with administrator rights" and now
says it may import gremlin.drivers and gremlin.driver_jobs.

## DriversModel (UIPY): QML element in Gremlin.Device (`@ta.QmlElement`, like XboxDriverStatus)

Properties (notify `changed`): `rows` (list of maps: `key, name, installed,
bundled, state, label, ticked, tickable`; label is "not installed",
"<v>", or "update available: <old> → <new>"), `presets` (list of names +
"Custom"), `vjoyPreset` (str), `vjoyDevices` (list of maps id/axes/buttons/hats,
the chosen layout), `vjoyCurrent` (same shape, what vJoy has now; empty when
unknown), `vjoyEdited` (bool), `vjoyWarning` ("Running games will lose the vJoy
devices until they restart." when vjoyEdited and vJoy has devices), `busy`,
`progress` (str, "Installing vJoy 2.2.2.0…"), `results` (list of maps
driver/state/message), `restartNeeded`, `pendingHidHide` (bool), `pendingVersion`.
Slots: `reload()`, `setTicked(key, on)`, `setPreset(name)`,
`setDeviceCount(n)`, `setDevice(index, axes, buttons, hats)`,
`describe() -> str` (the "before" prompt text: what will happen and when),
`apply() -> bool` (writes the job file in %TEMP%, starts the helper elevated
with `--jobs/--results`, polls the results file on a main-thread timer, fills
progress/results; returns False when nothing to do or it could not start),
`finishHidHide() -> bool` (step 2: install from pending.json), `restartNow()`
(Windows restart; blocked under test), `laterHidHide()`.
Signals: `finished()`.
Launch: ShellExecuteW "runas" on `<app>\Gremlin Device Helper.exe`; a
`launcher` hook for tests. Never on the real system under pytest.

## QML (QML agent)
- `qml/WindowDrivers.qml`: Tools › Drivers (06 S185): rows with tick boxes and
  labels, the vJoy section (preset ComboBox, Custom editor: device count 1-16,
  per device axes 0-8, buttons 0-128, hats 0-4; current layout shown;
  vjoyWarning), **Apply** (opens DialogDriverPrompt with `describe()` first,
  then `apply()`), progress line, results, restart buttons.
- `qml/DialogDriverPrompt.qml`: one prompt for every driver step (06 S187):
  properties `title, body, okText, cancelText`; signals `accepted, rejected`.
- Home: while `pendingHidHide`, the line "HidHide update not finished: devices
  aren't hidden" with **Finish update** (06 S186).
- `XboxDriverCheck.qml`: **Open Drivers** replaces **Get ViGEmBus**
  (signal `driversRequested()`, 06 S188). `output.vjoy_driver_problem` hint:
  "Open Tools › Drivers to install vJoy, then restart the program."
- Words exactly as the spec and glossary ("Drivers", "Open Drivers", "Apply").

## Lead
- `qml/main_commands.js`: `{ id: "tools.drivers", text: "Drivers…", group:
  "Tools › Device Setup", keywords: "vjoy vigembus hidhide driver install
  update", run: function() { openDrivers() } }`.
- `qml/Main.qml`: `openDrivers()` (Helpers.createComponent("WindowDrivers.qml")),
  wire `driversRequested`, at start: when pendingHidHide, open the step 2 prompt.

## Setup (ISS)
- A **Drivers** wizard page after the folder page: one row per driver
  (installed version / "not installed" / "update available: old → new"),
  missing ticked, older unticked, same/newer no box (01 S187). Detection with
  the same registry keys as drivers.py.
- Bundled files from `installer\drivers\` installed to `{app}\drivers\`
  (01 S188); licences `vigembus.txt`, `hidhide.txt` to `{app}\licenses`.
- For vJoy and HidHide: GitHub `/releases/latest` check; a newer one is
  downloaded with the download page (progress) to `{tmp}`; no internet or a
  failure: bundled only (01 S189). The job lists the download first, the
  bundled copy second; the helper checks both (S25).
- One admin prompt: after the files are copied, write the job file in
  `{tmp}`, start `{app}\Gremlin Device Helper.exe --jobs --results` with
  ShellExec verb "runas", show progress from the results file until
  `finished` (01 S190). A failure never stops Gremlin's install; the last page
  lists each result and offers a restart when needed (01 S191).
- HidHide update: the step 1 prompt (06 S186 words), job `remove`, then
  write `{app}\drivers\pending.json` and ask for the restart.
- Uninstall leaves drivers (01 S192).
- No ISCC compile in this batch (needs the user's approval); tests read the
  script text.

## Build (BUILD)
- `tools/fetch_drivers.py`: downloads each bundled file from its pinned
  GitHub release URL into `installer\drivers\` and checks size and SHA-256;
  refuses a driver with no SHA-256 (ViGEmBus until the user allows it);
  `--from <folder>` copies local files instead (checked the same way).
- `installer\drivers\` in .gitignore; build_installer.ps1 fails clearly when
  a bundled file is missing; release-exe.yml runs the fetch step before ISCC.
- `licenses/vigembus.txt` (BSD-3-Clause, Nefarius Software Solutions e.U.,
  with the URL), `licenses/hidhide.txt` (MIT, from the repo's LICENSE).
- Never downloads in tests (fake fetch).

## SSM (12 S16a)
The "input after action: countdown restarts" line always ends with the
source: " (by <device name> (keyboard|mouse))", " (by a device (mouse))"
when the name is unknown, or " (by input sent by a program)". The change-only
"last reset by" line stays as it is.
