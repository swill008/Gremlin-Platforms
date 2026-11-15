# Screen Saver Mode, batch 3: Devices / Programs / System sections, "last reset by", hold program (2026-11-15)

User (2026-11-15, after trying 1.0.38): "we need three buttons: Devices, Programs and System, so it's clear for
users"; answers 1 a (last reset by), 2 a (full-screen hold names the program), 3 a (Programs and System each run
their own check and administrator prompt), 4 a (a caller asking display AND PC goes in Programs only, marked "also
keeps the PC awake", one switch), 5 (three rows, grouped in sections, stacked). Mock-up approved:
claude/drafts/screen-saver-mode-mockup.svg. Base rules: contract.md (every agent follows them).

## Behaviour
- **Sections**, stacked under "What keeps the PC awake", each a framed box: title, its button on the right, a
  one-line description, its list:
  - **Devices** / **Refresh Devices**: "Devices that never go quiet and keep Windows' idle time at 0. Screen Saver
    Mode ignores them." No switch.
  - **Programs** / **Refresh Programs** (🛡): "Programs keeping the display on. These hold Screen Saver Mode off until
    they stop. Needs administrator rights." Rows: every caller (process, driver, service) whose kinds include
    Display; "also keeps the PC awake" under the name when it also asks System, Awaymode or Execution; detail line;
    "(driver)"/"(service)"; Ignore switch.
  - **System** / **Refresh System** (🛡): "Programs, drivers and services keeping the PC awake. They stop sleep, not
    the screens. Needs administrator rights." Rows: callers WITHOUT Display that ask System, Awaymode or Execution;
    ignored callers with no current request go to the list matching their override types (DISPLAY → Programs, else
    System). Ignore switch.
  - Each Refresh button runs its own elevated check (one prompt each) and fills only its own list.
  - Messages: Programs rows "… is ignored: it no longer keeps the display on." / System rows "… is ignored: it no
    longer keeps the PC awake." (and "… is no longer ignored." for off).
- **Last reset by** (status): next to "Your idle time", "last reset by: <device name> (keyboard|mouse), just now /
  N s ago" or "last reset by: input sent by a program, N times a minute" (input with no device handle = sent by a
  program; Gremlin's own still doesn't count). Device names from GetRawInputDeviceInfoW(RIDI_DEVICENAME) and the
  device's friendly name (SetupDi / CM_Get_DevNode_Property or the HID product string), looked up once per device
  handle and cached (never per event). Rate = counted inputs from programs in the last 60 s.
- **Hold program**: the full-screen hold line names the foreground program's file name when Windows gives it
  (GetForegroundWindow → GetWindowThreadProcessId → QueryFullProcessImageNameW): "On hold: a full-screen program is
  in front (StarCitizen.exe)"; plain text when unknown.
- Tracing (S16): the reset source when it CHANGES (not per event), the hold program, each section's run.

## API changes
- core (`gremlin/screen_saver_mode.py`): `Status` gains `last_reset_by: str` (device name or "" ), `last_reset_kind:
  str` ("keyboard" | "mouse" | "program" | ""), `last_reset_age_s: float`, `program_input_per_min: int`;
  `hold_program: str` filled for the full-screen hold. `InputClock.note_input(own=False, source=None)` where source
  is an opaque device key or None for program input; `WindowsApi.foreground_program() -> str`.
- power requests (`gremlin/power_requests.py`): `split(programs) -> tuple[list[ProgramRequest], list[ProgramRequest]]`
  (display rows, system rows) per the rules above; `ProgramRequest.also_awake: bool` (Display plus another kind);
  `list_requests()` unchanged (each button calls it and keeps its own half).

## Owners
| Agent | Files |
|---|---|
| SSM-CORE3 | gremlin/screen_saver_mode.py, test/unit/test_ssm_core.py |
| SSM-SCAN3 | gremlin/power_requests.py, test/unit/test_ssm_scan.py |
| SSM-UI3 | gremlin/ui/screen_saver_mode_model.py, qml/WindowScreenSaverMode.qml, test/unit/test_ssm_ui.py, ssm_ui_fakes.py, ssm_ui_smoke.py, test/unit/test_ssm_e2e.py |
| SSM-DOCS3 | claude/program-map/12-screen-saver-mode.md (S13/S14 rewritten, new S17 System section, S18 last reset by, S19 hold program; sections 2-6, 10, 11, 12), 01 if Tools/Trace lines change, README counts, claude/glossary.md (Refresh System, System, last reset by), qml/help/tools.js |
New objectNames (UI): "ssmSectionDevices", "ssmSectionPrograms", "ssmSectionSystem", "ssmRefreshSystem",
"ssmSystemList", "ssmSystemMessage", "ssmLastReset", "ssmAlsoAwake" (row text); existing names kept.
