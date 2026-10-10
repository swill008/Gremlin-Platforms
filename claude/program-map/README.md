# Program map (Stage 0)

One page per subsystem: what it owns, entry points, what it talks to,
threads, rule breaks, the behaviour spec ("It should ..." statements S1..,
each with its source), questions for the user (Q1..), known gaps and test
coverage. Written read-only from the code at 4f6bdfa4 (2026-10-06); sections 2-6, 10 and 11 brought up to date 2026-10-09, with each gap's status from `claude/gap-list.md`. Counts: S and Q are the numbered statements and questions (retired ones included); Gaps is the number of gap items listed in section 10, fixed or not.

**The behaviour spec is approved (user, 2026-10-06)**: pages 06, 05 and 03
reviewed answer by answer, the rest approved as recommended. On each page,
section 8 plus the decisions in section 9 (recorded in section 12) are the
definition of correct; where they disagree, the decision wins. Journey tests
and rule checks (Stage 1) are written from them. OSC stays parked: its
decisions apply when OSC is unparked.

**Change control.** Any change to the program's behaviour goes through this
spec. Before coding, check the change against the affected page(s); if it
changes, removes or contradicts a statement or decision, tell the user first
and update the spec with their answer, then code. Where today's code differs
from the spec, that is a gap to fix (each starting as a failing test), not a
spec change. See "The plan" in `claude/system-maps.md`.

| Page | Subsystem | S | Q | Gaps | Review |
|---|---|---|---|---|---|
| [01-app-shell](01-app-shell.md) | Startup, quit, settings, Options, main window, logging, updates, threads, Help, shared pieces, control tracing, the build (two exes) | 153 | 16 | 20 | reviewed 2026-10-06 (all as recommended) |
| [02-devices-input](02-devices-input.md) | Device scan, events, hooks, keyboard, HidHide, trace taps, Gremlin Input Tester | 123 | 19 | 28 | reviewed 2026-10-06 (all as recommended) |
| [03-modules](03-modules.md) | Input/output modules, Home, Module Setup, Calibration, Output View, Delete Device | 125 | 18 | 37 | reviewed 2026-10-06 (all as recommended) |
| [04-profile-modes](04-profile-modes.md) | Profile load/save, modes, Manage Modes, auto-load, scripts, Swap Devices | 95 | 21 | 29 | reviewed 2026-10-06 (all as recommended) |
| [05-actions-editors](05-actions-editors.md) | Action plugins, Configuration page, Keyboard page | 111 | 20 | 23 | reviewed 2026-10-06 (all as recommended) |
| [06-runtime-outputs](06-runtime-outputs.md) | Run/Stop, macros, mouse, vJoy/Xbox output, Logical Device, output trace | 87 | 19 | 20 | reviewed 2026-10-06 (all as recommended) |
| [07-button-map](07-button-map.md) | Button Map editor, photos, recovery, print/export | 103 | 19 | 23 | reviewed 2026-10-06 (all as recommended) |
| [08-history-pack-automap](08-history-pack-automap.md) | History, Device Pack, Auto Mapper | 113 | 21 | 30 | reviewed 2026-10-06 (all as recommended) |
| [09-osc-sound-misc](09-osc-sound-misc.md) | OSC (picked up 2026-10-09: own module file, per-input settings; Monitor, output and Send OSC, Feedback, encoder, discovery), sound, speech, tray, theme; shared widgets and foundations | 122 | 20 | 34 | reviewed 2026-10-06 (all as recommended) |
| [10-device-library](10-device-library.md) | Device Library: every device and its saved setups; Copy, Swap, Change vJoy Output; autosaves | 59 | 1 | S1-S56 (+S20a, S53a) built; S6a (D-04-LD-FILE) building; open items: to-dos 47, 50, 51, 52 | approved 2026-10-08 |
| **Total** | | **1081** | **174** | **241** (+ page 10) | |

## Most serious findings (to confirm first)

Found by reading the code; most are not reproduced yet. Each needs a
failing test (or a hands-on check) before any fix.

1. A profile with Map to vJoy may not open on a PC with no vJoy device (05 Q2).
2. A Run that fails partway can make the next Run handle every input twice (06).
3. Quit may leave the program running with a tool window open, or File > Exit may be refused with Minimize to tray on (01; needs a real-screen check).
4. Delete Device writes the whole profile at once, skips the unfinished-actions check, can run while running, and can keep no copy (03 Q4-Q6).
5. The Button Map writes some changes before Save, and can overwrite a module file changed elsewhere while it is open (07 G1, G6-G8).
6. Load / New Profile may pick the start mode from the old profile (04).
7. Run uses unfinished actions (an unpicked Reference placeholder) (05 Q3).
8. A Device Pack import that fails partway loses inputs; Undo Import can undo later saves (08; AU-118).
9. "vJoy as input" tick restarts or stops a running profile (02 Q1).
10. Nobody owns the list of settings: some are purged at start before they register (01).

## Review order (suggested)

06 Run/Stop and 05 Actions (feed the first redesign), then 03 Modules and
08 History/Pack (redesign 2), then 04, 07, 01, 02, 09.
