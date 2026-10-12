# Full code map and dead-code audit (2026-10-12, at commit 203a74dd)

User request (2026-10-12): "do a full code mapping and a full code audit. exercise the full program as much as possible. lets see if we have dead code or functions laying around we do not use."

Seven agents, 06:10-06:45, read-only (no repo file changed). Brief: `brief.md`. Each report below has its method, a table of findings with file:line, confidence, and what was NOT verified.

| Report | What it covers | Headline |
|---|---|---|
| `EXERCISE.md` | The whole test suite (unit, action, journeys) run with a `sys.monitoring` recorder of which program functions run | 6,923 functions, 6,227 ran (89.9 %), 696 never ran; 31 never ran AND have no reference anywhere (dead candidates); the rest are coverage gaps (hardware-only, on-screen only, untested) |
| `PY-REFS.md` | Python definitions nothing references (code, QML, strings) | 54 dead, 96 used only by tests, 4 only by tools / the user-script example |
| `QML-REFS.md` | QML / JS files, functions, properties, signals, ids nothing uses | 5 dead files (+6 medium-confidence style controls), 31 dead functions (9 editor forwarder+body pairs), 30 dead properties, 2 dead signals |
| `BRIDGE.md` | The Python <-> QML seam (Slots, Properties, Signals, roles, context properties) | 1 real bug (below), 5 dead + 38 test-only exposed names, 8 unused roles, notify signals never emitted |
| `ASSETS.md` | Settings, Help topics, pictures / data files, modules | 3 dead settings (one is a visible Options switch that does nothing), 141 unused pictures that ship in the installer, old WiX build files, a committed log |
| `LEFTOVERS.md` | Legacy shims, one-time code, TODOs, commented code, duplicate helpers | 22 legacy shims, OT-1..OT-5 file lists (4 OT-2 places missing their marker), 2 stale TODOs, 16 duplicate-helper groups |
| `MAPCHK.md` | The code (544 files, 182,122 lines) vs `claude/program-map` | vjoy/ and theme/ outside both guard tests; 27 stale names, ~35 stale line references, 14 files with unclear owner |

## Findings that matter most

1. **Real bug:** `qml/DeviceMapCard.qml:31` `liveStamp` sums `_buttons.count + _axes.count + _hats.count`, but the Python `_MappedModel` (`gremlin/ui/input_pairing.py:246`) has no `count`, so it is always 0 and the map card's change signal never fires (`VkbRigFace.qml:531`, `VkbRigEditor.qml:1425`, `:1964`). Effect on screen not verified.
2. **Guard-test gap:** `vjoy/` and `theme/` are outside `test_spec_line.py` and `test_program_map_covers_files.py`; `vjoy/` is missing from the `.claude/CLAUDE.md` program-code list.
3. **Dead visible switch:** Options > Home > Cards `display/status/last-keep-after-release` is read by nothing.
4. **Possible missing behaviours (check against the spec before removing):** `logical_layout.drop_logical_steps` (Logical Device undo on Discard / Restore) never called; `ConfigSectionModel.scope` described for the editor but unused; `device_zip` wire import (`device_zip.py:626-695`) only runs in tests.
5. **Risky duplicates:** six "same file?" path checks with different case rules; two public `guid_text` functions with different output (`store.py:2320`, `device_zip.py:128`); four picture-size readers.

## Decisions (user, 2026-10-12)

Recorded in `claude/todo.md` under D-NEXTLIST-1 (item 5 and "Planning answers"): fix the bug, close the guard gap (incl. the CLAUDE.md line), remove the dead Options row, check the 3 possible missing behaviours first (read-only), remove double-confirmed dead code (+ test-only code the spec doesn't need, with its tests), remove the shipped leftovers, remove legacy shims not covered by decisions and add the OT-2 markers, merge the risky duplicates, fix the program map.

## Related: the CI crash of 2026-10-12

Not part of this audit, found the same night: a `HardwareProfile` (owning a timer) held in a reference cycle by a self-calling `walk()` in `_own_refs` (since 44ab601c) was freed by the garbage collector on the History thread -> "Timers cannot be stopped from another thread" -> access violation. Fixed in 203a74dd (loop instead of recursion) plus `gremlin/gc_guard.py` (collection only on the main thread) and a test check for cross-thread timer warnings. Tracker CI-CRASH-GC-1.
