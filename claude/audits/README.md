# Audits and investigations (index)

Standing rule (user, 2026-10-12): every audit, plan, scout finding and crash post-mortem is kept here or in `claude/plans/`, so the history of how the program is built and what was found stays with the code.

| Folder | Date | What |
|---|---|---|
| `2026-10-12-code-audit/` | 2026-10-12 | Full code map + dead-code audit (7 agents); also the CI crash post-mortem (HardwareProfile cycle, GC on the History thread) |
| `2026-10-12-pyside-612.md` | 2026-10-12 | Why PySide6 6.12 broke CI (to-do 39): menu separators (likely) and a Keyboard-page crash (candidates); stay pinned |
| `2026-10-12-deferred-qt-work.md` | 2026-10-12 | Tests that leave Qt work behind (to-do 133): test_final_06, test_sendosc_target_name, test_osc_encoder, test_device_photo_maker; proposed per-test flush |
