# Batch 3 rules for every agent (one-time catch-up)

Repo: E:\Users\Stacie\Documents\GitHub\Gremlin-Platforms (branch Gremlin-Platforms). PySide6/QML joystick mapper.
Read first: `claude/todo.md` ("ONE-TIME CATCH-UP"), your GL rows in `claude/gap-list.md` (sections 7 and 8; the Fix column says what to do), the batch 3 notes at the end of `claude/catchup-test-plan.md`, the spec page(s) they cite in `claude/program-map/` (section 8 statements + section 12 decisions; decisions win), `claude/decisions.md` (latest decisions at the end), `AGENTS.md`, `.claude/CLAUDE.md`.

Batches 1 (d68f4d88) and 2 (31861922) are done. Batch 1 added three owners. Use them, never bypass them (guard tests fail otherwise):
- `gremlin/run_scope.py`: everything a Run starts (timers `run_scope.timer`, loops, held keys/buttons) and the Stop stages.
- `gremlin/modules/store.py`: every module file read/write/path/picture (by device name + guid).
- the `Library` in `gremlin/profile.py`: action drafts, commit, release (the one removal rule), snapshot/restore, `with library.change():`.

## Ownership (strict)
- 6 agents work at the same time in the same checkout. Edit ONLY your files (table below) plus new test files `test/unit/test_batch3_<your id>*.py`. Never edit another agent's file or `test/conftest.py`. Only C1 edits files in `claude/`.
- Tests that already exist for your area: you may edit a test file only if it mainly tests your files; if unsure, ask the lead via your report.
- Need a change in someone else's file (including a text change)? Don't make it. Describe it exactly under "Requests for other owners". If it blocks you, leave a `TODO(batch3)` note and say so.
- Never run `git checkout`, `git stash`, `git reset`, `git add` or `git commit`. The lead commits.

| Agent | Files |
|---|---|
| C1 help, glossary, docs, small dialogs | qml/help_topics.js, claude/glossary.md, claude/test-plan.md, developer notes (docs/ or README files on HidHide), qml/OptionWindowsScale.qml, qml/ConfigGroup.qml, gremlin/ui/shell_option.py, qml/RunningNote.qml, qml/DialogDeviceInformation.qml, qml/DialogHardwareHide.qml, qml/TextInputDialog.qml, qml/DismissibleDialog.qml |
| C2 shell, settings, scripts | joystick_gremlin.py, gremlin/config.py, gremlin/ui/option.py, gremlin/ui/ui_scale_option.py, gremlin/ui/windows_scale_option.py, gremlin/history.py, gremlin/process_monitor.py, gremlin/ui/backend.py, qml/Main.qml, qml/window_registry.js, gremlin/user_script.py, gremlin/base_classes.py, gremlin/fsm.py (+ test/unit/test_fsm.py), gremlin/audio_player.py |
| C3a modules & Home | gremlin/ui/module_model.py, gremlin/ui/module_pairing.py, gremlin/modules/registry.py, gremlin/modules/output.py, vjoy/vjoy.py, gremlin/ui/profile.py, gremlin/ui/device.py, gremlin/ui/action_label.py, gremlin/action_label.py |
| C3b devices & input | gremlin/device_initialization.py, gremlin/ui/device_names.py, gremlin/input_cache.py, gremlin/event_handler.py, gremlin/windows_event_hook.py, gremlin/input_refresh.py, gremlin/ui/hidhide.py, vigem/*, hat-buttons code, gremlin/ui/input_monitor.py, gremlin/ui/input_pairing.py |
| C4 actions | gremlin/ui/binding_catalog.py, qml/BindingCatalog.qml, qml/action_kinds.js, gremlin/macro.py, action_plugins/* |
| C5 Button Map, History, Device Pack, Auto Mapper | gremlin/ui/hardware_profile.py, gremlin/ui/button_map_labels.py, qml/DialogJoystickButtonMap.qml, qml/VkbRigEditor.qml, qml/rig_*.js, qml/DialogConfigureModule.qml, gremlin/ui/device_pack.py, qml/DialogDevicePack.qml, gremlin/ui/history_model.py, gremlin/auto_mapper.py |

Files not listed: ask the lead first. OSC stays parked (gremlin/osc.py, gremlin/ui/osc_*.py): leave the OSC parts of GL-244 and GL-279.

## Text rules
- On-screen words follow `claude/glossary.md` (sentence case for titles and buttons as the glossary says). C1 owns the glossary: other agents list any word they need added under "Requests for other owners".
- Help text describes the program as it is now (after batches 1 and 2); read the code, not old help.

## What to fix
- Bug fixes only, as the spec says. No new features. Not in this batch: GL-029 (feature), GL-168 and GL-201 (on hold by the user), GL-185 and GL-186 (planned features), OSC (parked). Clean-up must not change behaviour (Spec: none) unless the row says so; keep each removal small and checked by the existing tests. For `needs-hands-on` rows: fix what the code clearly shows, add a test where you can, and list the hands-on check in your report.
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
