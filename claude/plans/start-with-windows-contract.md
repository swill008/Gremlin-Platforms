# Contract: Start with Windows, and Test now ignores mouse movement (2026-11-22)

Approved by the user 2026-11-22: "lets add it" (start with Windows option in
Options and the tray's right-click menu), 1a (open minimized), 2b (don't start
Run), 3a (off by default; setup's uninstall removes the entry), 4a (this
batch); Test now: "ignore mouse movement, not clicks" (5b). Spec: 01 S194,
12 S37 (written by the lead). Decided by the lead (small details, reported):
the mouse wheel cancels the test like a click; input sent by programs is
ignored during the countdown.

## 1. Windows startup entry (owner: STARTUP)

New `gremlin/startup_entry.py` (Python code; imports only stdlib + winreg):

```python
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"   # under HKCU
VALUE_NAME = "Gremlin-Platforms"
def command(exe: str | None = None) -> str   # '"<exe>" --start-minimized'; exe = sys.executable when frozen
def is_enabled(store=None) -> bool           # value present (any command)
def set_enabled(on: bool, store=None) -> bool  # True when done; writes/deletes the value; logs failures
```
`store` is an injectable object with get/set/delete (tests use a dict fake);
the real store is winreg HKCU. Under pytest the real store refuses
(`RealRegistryBlocked`, like drivers_model's RealCallBlocked). When not frozen
(running from source) `command()` uses the source start-up (pythonw +
joystick_gremlin.py) or set_enabled refuses with a logged reason: pick the
simplest correct one and report it.

Options: a switch "Start Gremlin-Platforms when Windows starts" in Options ›
General › Startup and Tray (`gremlin/ui/option.py` _LAYOUT, setting
registered in `joystick_gremlin.py` `register_config_options` as
("global", "general", "start-with-windows"), bool). Its shown value is
`is_enabled()` (read when Options opens); changing it calls `set_enabled`. If
set_enabled fails, the switch goes back and the log says why.

## 2. Tray menu (owner: TRAY)

`gremlin/ui/system_tray.py`: a tick item "Start with Windows" (new command id)
above the separator before "Exit Gremlin-Platforms", checked from
`startup_entry.is_enabled()` each time the menu opens; clicking calls
`startup_entry.set_enabled(not on)`. Tests with a fake store.

## 3. Setup (owner: SETUP)

`installer/gremlin_platforms.iss`: uninstall deletes HKCU Run value
"Gremlin-Platforms" (e.g. `[Registry] Root: HKCU; Subkey: ...\Run;
ValueName: "Gremlin-Platforms"; Flags: uninsdeletevalue dontcreatekey` with no
value written at install, or a [Code] CurUninstallStepChanged
RegDeleteValue). Install writes nothing. Test in test_installer_drivers.py or
a new test_installer_startup.py.

## 4. Test now (owner: SSM)

`gremlin/screen_saver_mode.py`: the listener notes the last key press, mouse
button press or wheel (counted, not program-sent) separately, e.g.
`last_press()`; the test countdown (`start_test`, the check in `tick` ~line
1890) cancels only on a newer press, not on movement or program input.
Everything else (idle periods, timers, keep-off ending) unchanged. Tests in
`test/unit/test_ssm_core.py` that fail on today's code (movement during the
countdown cancels today).

## 5. Docs (owner: DOCS)

Decision rows D-01-START-WITH-WINDOWS (01 section 12) and the 12 S37 change
(D-12-SSM-TEST-PRESS), glossary rows (Options label, tray item), Help
(qml/help: Options, tray, Screen Saver Mode Test now), map sections 2/3/4/5/
10/11 for the new file and changed files, to-do entry.

## Owners

| Agent | Files |
|---|---|
| STARTUP | `gremlin/startup_entry.py` (new), `gremlin/ui/option.py`, `joystick_gremlin.py` (register_config_options only), `test/unit/test_startup_entry.py` (new), option tests it needs |
| TRAY | `gremlin/ui/system_tray.py`, its tests |
| SETUP | `installer/gremlin_platforms.iss`, an installer test |
| SSM | `gremlin/screen_saver_mode.py`, `test/unit/test_ssm_core.py` |
| DOCS | `qml/help/*.js`, `claude/glossary.md`, `claude/program-map/*` (not S194/S37 text), `claude/todo.md` |
| lead | this file, timings, build, commit |
