# Screen Saver Mode batch 7 and the installer (2026-11-16)

Spec: claude/program-map/12-screen-saver-mode.md S21 (parent device), S30 (untick rule approved),
S33 (in use now), decision D-12-SSM-PARENT-AND-IN-USE; claude/program-map/01-app-shell.md S173
(the installer closes the running program). Approved by the user 2026-11-16 ("1 a, 2 a, 3 a", "4 a,
5 a, build"). Base rules: contract.md, contract-5.md (HARD SAFETY RULE: never disable/enable a real
device, never run pnputil, never elevate, never start the helper, the screen saver or a power-off for
real, never send input, never run the installer). Glossary: "in use now" (claude/glossary.md, Wake PC row).

## Pieces and owners
| Agent | Files |
|---|---|
| SSM-PARENT7 | `gremlin/device_disable.py`, `gremlin/device_helper_protocol.py`, `gremlin_device_helper.py`, `test/unit/test_ssm_disable.py`, `test/unit/test_ssm_helper.py` |
| SSM-INPUT7 | `gremlin/screen_saver_mode.py`, `test/unit/test_ssm_core.py` |
| SSM-UI7 | `gremlin/ui/screen_saver_mode_model.py`, `qml/WindowScreenSaverMode.qml`, `test/unit/test_ssm_ui.py`, `test/unit/ssm_ui_fakes.py`, `test/unit/ssm_ui_smoke.py`, `test/unit/test_ssm_e2e.py` |
| INSTALLER7 | `installer/gremlin_platforms.iss`, and the installer assertions in `test/unit/test_input_tester_packaging.py`, `test_program_fixes.py`, `test_update_check.py` only where they pin the old close behaviour (new test file `test/unit/test_installer_closes_program.py` for the new rules) |
| DOCS7 | map page 12 sections 2-6, 10, 11 (not 8/12); page 01 sections 2-6, 10, 11 and a section-12 decision row D-01-INSTALLER-CLOSES; README rows 01 and 12 and a batch line; `qml/help/tools.js` (in use now; parent disabling, a mic's audio pauses) |

## SSM-PARENT7: disable the parent (S21)
- `DeviceDisabler.disable(devices: list[tuple[str, str]])` keeps its signature (name, listed id). For each
  listed id it uses `screen_saver_mode.physical_device(id)` (import lazily; it calls cfgmgr32, so on a
  program thread, and make it injectable for tests like `_status`) to get the parent. Several listed parts
  with one parent become one journal entry, keyed by the parent id, name = the listed name.
- Fallback to the listed id itself when: the parent is "" (unknown), or the parent is not `USB\...`, or the
  parent is in the `protected` set (below). Trace why.
- Safety: `DeviceDisabler.set_protected(physical_ids: Iterable[str])` - the physical ids of the devices
  ticked on Wake PC (the model calls it from apply_saved). Never disable a parent in that set (a ticked
  keyboard or mouse must always be able to wake the PC).
- `device_helper_protocol.valid_device_id`: accept `HID\` and `USB\` ids (same other checks); the refusal
  text becomes "refused: not a device id the helper handles". The helper and `check_request` keep the
  journal check (only ids the journal lists as "to be disabled"/"to be enabled").
- `device_status`, `enable_pending`, `recover_at_start`, `on_device_arrival` work unchanged on parent ids;
  old journal entries with HID ids still re-enable.
- Tests: parent chosen, parts deduplicated, fallbacks (unknown, non-USB, protected), USB ids accepted by the
  protocol and helper, journal round trip; each failing on the old code.

## SSM-INPUT7: activity for the highlight (S33)
`ScreenSaverMode.set_activity_listener(listener: Callable[[str], None] | None)`: while set, any keyboard or
mouse input from a device (key down/up, button, movement, wheel), ticked or not, is reported on the MAIN
thread as listener(physical_id), at most once per device per 0.5 s, through the same event queue/drain as
presses (works while the mode is off when detection is started). The press listener is unchanged. Trace
nothing per event. Tests failing on the old code.

## SSM-UI7: the highlight (S33) and protection wiring
- Each `wakeRows` row gains `"inUse": bool`. Activity for a row sets it True; it goes back False 2 s after
  that row's last activity (one main-thread timer for all rows). Set/cleared with the tab like the press
  listener. QML: the row's background in the theme's highlight colour while inUse, and the note shows
  "<note> · in use now" (just "in use now" when the note is empty). objectName "ssmWakeRowHighlight".
- `apply_saved()` also calls `device_disable.manager().set_protected(ticked ids)`.
- Tests (ui + e2e): movement lights an unticked row without ticking it; a press lights and ticks as before;
  the highlight goes after 2 s; nothing lights while the tab is closed; protected ids reach the disabler.

## INSTALLER7: close the running program (01 S173)
Investigate first (Inno Setup docs and the script): why `CloseApplications=yes` hasn't closed Gremlin
(suspected: `PrepareToInstall` tries to move the files aside before the Restart Manager runs, fails, and
stops with "still running"). Then in `PrepareToInstall`, before moving files: if gremlin_platforms.exe (in
{app}) is running, ask it to close the way File › Exit does (post WM_CLOSE to its top-level windows;
Main.qml's onClosing quits or shows its own unsaved-changes question), wait up to 15 s for the process to
end. If it is still running: return exactly "Gremlin-Platforms has unsaved changes. Save or close them,
then run the update again. Nothing was changed." Remember that it was running; after install start it
again (a [Run] entry with a Check function; keep the existing silent-update /LAUNCH=1 path and the
"Launch" checkbox). Never TerminateProcess. Tests read the .iss text (like the existing installer tests).
Compile check: run the Inno compiler (`ISCC.exe` under %LOCALAPPDATA%\Programs\Inno Setup 6) only with
`/O-` (syntax/compile check, no output) if it supports it; do NOT run installer/build_installer.ps1 or
PyInstaller, and never run the installer.
