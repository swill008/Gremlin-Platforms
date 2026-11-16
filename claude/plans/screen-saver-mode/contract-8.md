# Batch 8: back to listed parts, pending-restart fix, installer quit request (2026-11-16)

Spec: claude/program-map/12-screen-saver-mode.md S21 (parts again), S34 (new), D-12-SSM-PENDING-RESTART;
claude/program-map/01-app-shell.md S173 (quit request, 10 s). User 2026-11-16: "1a, go back to the parts
like we were doing. lets only disable what we did before", "2, yes also fix the installer issue we found",
"ask to close and wait 10 seconds". Base rules: contract.md, contract-5.md (HARD SAFETY RULE: never
disable/enable a real device, never run pnputil, never elevate, never start the helper/screen saver/power
off for real, never send input, never run the installer or build it). To-do 139 in claude/todo.md has the
installer facts.

## Pieces and owners
| Agent | Files |
|---|---|
| REVERT8 | `gremlin/device_disable.py`, `gremlin/device_helper_protocol.py`, `gremlin_device_helper.py`, `test/unit/test_ssm_disable.py`, `test/unit/test_ssm_helper.py` |
| UI8 | `gremlin/ui/screen_saver_mode_model.py`, `test/unit/test_ssm_ui.py`, `test/unit/ssm_ui_fakes.py`, `test/unit/test_ssm_e2e.py` |
| QUIT8 | `gremlin/ui/system_tray.py`, `joystick_gremlin.py` (only the quit-request wiring), `installer/gremlin_platforms.iss`, `test/unit/test_installer_closes_program.py`, a new `test/unit/test_quit_request.py` |
| DOCS8 | map pages 12 and 01 sections 2-6, 10, 11 (not 8/12), README rows 01/12 + batch line, `qml/help/tools.js` (remove "switched off as a whole … a microphone's sound too") |

## REVERT8 (S21 parts, S34)
- Remove the batch-7 parent targeting: `disable()` journals and disables the listed ids as they are (as
  before e4dc194c). Remove `physical_parent`, `parent_lookup`, `target()` and `set_protected` (and their
  tests). `valid_device_id` accepts `HID\` only again, refusal text back to the pre-batch-7 wording.
- Old journal entries with `USB\` ids (left by batch 7) must still be re-enabled by enable_pending and
  recover_at_start: keep enabling any id the journal lists, but the helper must accept a `USB\` id only
  for "enable" of an existing journal entry (never "disable").
- S34: `device_status()` also reads the device's ConfigFlags (CM_Get_DevNode_Registry_PropertyW,
  CM_DRP_CONFIGFLAGS = 0x0A; CONFIGFLAG_DISABLED = 0x1): set -> "disabled" even while running. A disable
  answered with pnputil exit 3010 is followed at once by an enable request for that id, and the entry is
  recorded "disable failed" with result "Windows wanted a restart, undone" (or "…, undo failed: <why>").
  enable_pending never skips an entry whose state is not "enabled" just because Windows reports it
  running: it sends enable whenever device_status says "disabled" (now including the flag) or the entry
  is "disable failed". An enable refused with "pending system reboot" stays "to be enabled" with that
  result (retried at the next start).
- Tests faking the runner/status (exit 3010, flag set while running, old USB entries) failing on old code.

## UI8
- Remove the `set_protected` call from apply_saved and its tests/fakes; remove the e2e `parent_lookup=`
  argument and the S21 protected test; keep everything else (Wake PC, in use now). Tests pass against
  REVERT8's code at the end.

## QUIT8 (01 S173)
- App: the tray's hidden native window (class `JoystickGremlinSystemTray`, gremlin/ui/system_tray.py)
  handles `RegisterWindowMessageW("GremlinPlatformsQuitRequest")`: on the main thread, show and raise the
  main window, then run the same quit path as File › Exit (its unsaved-changes question included).
- Installer: in PrepareToInstall, before moving files: if the program is running, post the registered
  message to every `JoystickGremlinSystemTray` window of that process (FindWindowEx loop); also post
  WM_CLOSE to its main window (class starting "Qt" and ending "QWindowIcon", no owner) even when hidden,
  for older versions; wait 10 s (20 x 500 ms); still running -> keep the current stop message exactly.
  Remove the visible-only filter. Keep restart-after-close, /LAUNCH=1, the Launch checkbox, the failed-
  install restart. Never TerminateProcess. ISCC `/O-` compile check only; never build or run an installer.
- Tests: .iss text tests (10 s, registered message name, hidden main window included, no visible filter)
  and a Python test that the tray window's handler calls the quit path (faked), each failing on old code.

## DOCS8
Sections 2-6, 10 (close SSM-PARENT-REVERT as built pending the user's test; INSTALLER-CLOSE-UNTRIED stays
open with the new design), 11 (TBD counts), README counts recomputed (S on 12 is now 34), help text.
