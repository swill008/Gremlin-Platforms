# Plans, contracts and decisions (index)

| Folder / file | What |
|---|---|
| `next-run-2026-10-12/` | The next-run list's code facts (Xbox Viewer merge, Home drag, card size, Library rows / thumbnails); items and answers in `claude/todo.md` D-NEXTLIST-1 |
| `device-image/` | Device Image (Add / Change / Remove Image for input modules): contract, split, spec draft, questions, the user's decisions |
| `bg-composite/` | The generated device picture (built in b4f3ff13): contract, split, spec draft, map lines |
| `ps-match-contract.md` | Photoshop-match handles and keys (built in 3515b8cd) |
| `click-zone-contract.md` | Whole-view click zone and the 1.2x grid (built in b4f3ff13) |
| `rust-middle-path-study.md` | Read-only study 2026-11-18: keep Python, move hot paths to Rust via PyO3 - evidence, candidates, build changes, staged plan |
| `fix-plans/README.md` | 2026-11-19 merged plan: blank window (tray) fix, Window/Timing tracing, controls on their own thread; 10 helper reports |
| `driver-setup-installer.md` | Planning 2026-11-21: vJoy, ViGEmBus, HidHide tick boxes in the installer (bundled + newer-version download, vJoy layout choice, update tick box); answers 1c 2c 3b 4b 5a 6a 7a 8a 9a 10a 11a 12a 13a 14a; spec written to 01 and 06 (page 12 held) |
| `vjoy-axis-picker.md` | Plan 2026-11-21 (saved, not started): option c, tick each vJoy axis by name in setup and Tools › Drivers; spec change to 01 S187, 06 S185-S188, 12 S25a goes to the user first |
| `vjoy-update-keeps-devices.md` | Planning 2026-11-22 (not built): a vJoy update checks the devices afterwards and offers Repair Now / Repair Later; before/after logged; info prompt before; 1.1.1 waits for it |
| `help-style-guide.md` | Draft 2026-11-22 for approval: Help voice, length, words, facts, page template, look, automatic check (from the Help review) |
| `help-rewrite-brief.md` | Shared brief for the 2026-11-22 Help page writers |
| `help-fix-brief.md` | Shared brief for the 2026-11-22 Help fixes from the fresh-reader test |
| `control-api.md` | Plan 2026-11-23 (not approved to build): API in the program over a private pipe, client library, `gremlin-ctl` CLI (ships) and MCP server (dev only); user answers recorded |
| `older-scripts-compat.md` | Plan 2026-11-23 (not approved): R13 script names (`gremlin.input_devices`, `gremlin.control_action`, `deadzone`, optional `gremlin.user_plugin`) as thin modules over `user_script`; spec draft S99-S105, Help, tests, split, 5 questions |
| `memory-qml-factory.md` | Plan 2026-11-23 (not approved to build): QML-made Python objects made by a `ModelFactory` with the QML item as Qt parent (PYSIDE-WRAPPERS, upstream 02a280e8 way); six biggest holders in stage 1, the other 55 QML files in stage 2, guard test, probe re-run; split tables, 8 questions |
