# Batch 2 rules for every agent (one-time catch-up)

Repo: E:\Users\Stacie\Documents\GitHub\Gremlin-Platforms (branch Gremlin-Platforms). PySide6/QML joystick mapper.
Read first: `claude/todo.md` ("ONE-TIME CATCH-UP"), your GL rows in `claude/gap-list.md` (sections 2, 5 and 6; the Fix column says what to do), the spec page(s) they cite in `claude/program-map/` (section 8 statements + section 12 decisions; decisions win), `claude/decisions.md` (latest decisions at the end), `AGENTS.md`, `.claude/CLAUDE.md`.

Batch 1 (d68f4d88) added three owners. Use them, never bypass them (guard tests fail otherwise):
- `gremlin/run_scope.py`: everything a Run starts (timers `run_scope.timer`, loops, held keys/buttons) and the Stop stages.
- `gremlin/modules/store.py`: every module file read/write/path/picture (by device name + guid).
- the `Library` in `gremlin/profile.py`: action drafts, commit, release (the one removal rule), snapshot/restore, `with library.change():`.

## Ownership (strict)
- 9 agents work at the same time in the same checkout. Edit ONLY your files (table below) plus new files your prompt names (new test files: `test/unit/test_batch2_<your id>*.py`). Never edit another agent's file, `test/conftest.py` or anything in `claude/`.
- Tests that already exist for your area: you may edit a test file only if it mainly tests your files; if unsure, ask the lead via your report.
- Need a change in someone else's file? Don't make it. Describe it exactly (file, function, what, why) under "Requests for other owners". If it blocks you, leave a `TODO(batch2)` note and say so.
- Never run `git checkout`, `git stash`, `git reset`, `git add` or `git commit`. The lead commits.

| Agent | Files |
|---|---|
| B1 shell & settings | joystick_gremlin.py, gremlin/util.py, gremlin/config.py, gremlin/deferred_write.py, gremlin/error_report.py, gremlin/ui/system_tray.py, gremlin/ui/live_debug.py, gremlin/ui/log_option.py, gremlin/ui/ui_scale_option.py, qml/Main.qml, qml/helpers.js, qml/DialogLiveLog.qml, qml/DialogOptions.qml |
| B2a input events | gremlin/event_handler.py, gremlin/input_cache.py, gremlin/input_refresh.py, gremlin/windows_event_hook.py, gremlin/keyboard.py, gremlin/ui/util.py |
| B2b devices & HidHide | gremlin/device_initialization.py, gremlin/ui/device_names.py, gremlin/ui/hidhide.py, gremlin/ui/device.py, qml/DialogHardwareHide.qml, qml/DialogDeviceInformation.qml, qml/DialogCalibration.qml |
| B3 modules & Home cards | gremlin/ui/module_model.py, gremlin/modules/registry.py, gremlin/modules/output.py, gremlin/modules/auto_map.py, qml/StatusCard.qml, qml/StatusPage.qml |
| B4 profiles, modes, scripts | gremlin/profile.py, gremlin/mode_manager.py, gremlin/ui/backend.py, gremlin/ui/profile.py, gremlin/swap_devices.py, gremlin/ui/tools.py, gremlin/ui/script.py, gremlin/user_script.py, qml/DialogManageModes.qml, gremlin/logical_device.py |
| B5a action pane & locking | gremlin/ui/binding_catalog.py, gremlin/ui/logical_layout.py, qml/BindingCatalog.qml, qml/InputConfiguration.qml, qml/KeyboardInputList.qml, qml/ActionNode.qml, qml/LogicalPage.qml |
| B5b action logic & speech | gremlin/code_runner.py, gremlin/macro.py, gremlin/tts.py, gremlin/ui/option.py, gremlin/ui/action_model.py, action_plugins/* (all plugin folders) |
| B6 Button Map | gremlin/ui/hardware_profile.py, gremlin/ui/button_map_labels.py, qml/DialogJoystickButtonMap.qml, qml/VkbRigEditor.qml, qml/JoystickButtonMapCard.qml, qml/rig_*.js |
| B7 History, Device Pack, Auto Mapper | gremlin/ui/device_pack.py, gremlin/ui/history_model.py, gremlin/history.py, gremlin/history_modules.py, gremlin/auto_mapper.py, qml/DialogDevicePack.qml, qml/DialogHistory.qml, qml/DialogAutoMapper.qml |

Files not listed (e.g. gremlin/modules/store.py, run_scope.py, other QML): ask the lead first.

## Shared contracts (write these first if you own them)
- B1 writes in `qml/Main.qml`, at once: `function closeActionPanes(then)` — closes the action panes (catalog pane and Logical Device pane); if one has unsaved changes it asks with the existing leave/discard dialog ("The action editor has changes that are not saved." Discard / Cancel), then calls `then()` on Discard or when nothing changed. It uses `paneHasChanges()` from the pages (B5a adds `function paneHasChanges()` to LogicalPage.qml and the catalog). B7 wraps Auto Mapper Create, History Restore and Device Pack import / Undo Import in it (GL-098 rest, decision D-05-DRAFT-OUTDATED). B5a also exposes one "locked while running" property for GL-171; B1 uses it in Main.qml.

## What to fix
- Bug fixes only, as the spec says. No new features. Not in this batch: GL-029 (feature), GL-168 and GL-201 (on hold by the user), GL-185 and GL-186 (planned features), OSC (parked). For `needs-hands-on` rows: fix what the code clearly shows, add a test where you can, and list the hands-on check in your report.
- If a fix would add, change or contradict a spec statement or decision, don't do it: list it under "Spec questions".
- Fix at the owner, not with patches at call sites. Program rules: threads only via `gremlin.threads`, bounded waits, time via `gremlin.clock` (only where a test steps the clock or the rule needs it; don't move unrelated loops), layer rule hardware → input module → wiring → output module → driver (UI never touches vJoy/ViGEm or hardware directly). New on-screen text follows `claude/glossary.md`; list new texts in your report.
- Each fix gets a test that fails on the old code (check by temporarily restoring the old code, or say why not possible). Strict xfail tests for your GL ids: when your fix makes one pass, remove its mark (tell the lead if the test file isn't yours).

## Testing (keep the PC load low)
- Python: C:/Users/Stacie/AppData/Local/pypoetry/Cache/virtualenvs/joystickgremlin-4UY8FelE-py3.13/Scripts/python.exe
- Run only your own and directly related test files: `python test/run_tests.py <path> ...` or pytest on single files. Do NOT run the full suite.
- Lint: `python tools/pyright_baseline.py` must show no new errors in your files.
- Safety: never launch the real app on screen (off-screen only: QT_QPA_PLATFORM=offscreen, temp USERPROFILE, GREMLIN_OFFLINE=1, QT_QPA_FONTDIR=C:/Windows/Fonts); never touch the user's data (C:\Users\Stacie\Gremlin Platforms); never send keys/mouse to the PC; never change HidHide, vJoy or ViGEm state; no network. Use the Edit tool for strings containing \n (not sed/heredocs).

## Final report (short, plain)
1. GL ids fixed (one line each: what changed, spec ref).
2. GL ids not done and why (and hands-on checks needed).
3. Files changed.
4. Tests run and results (which new tests fail on the old code).
5. Requests for other owners.
6. Spec questions; new on-screen texts.
7. Batch test plan lines: how each fix is checked.
