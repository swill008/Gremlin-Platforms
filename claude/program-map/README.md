# Program map (Stage 0)

One page per subsystem: what it owns, entry points, what it talks to,
threads, rule breaks, the behaviour spec ("It should ..." statements S1..,
each with its source), questions for the user (Q1..), known gaps and test
coverage. Written read-only from the code at 4f6bdfa4 (2026-10-06).

The behaviour spec is a **draft** until the user reviews it. Statements
marked [code only] come from the code alone and need the user's yes or no.
Confirmed statements become the definition of correct (journey tests and
rule checks in Stage 1 are written from them). See "The plan" in
`claude/system-maps.md`.

| Page | Subsystem | S | Q | Gaps | Review |
|---|---|---|---|---|---|
| [01-app-shell](01-app-shell.md) | Startup, quit, settings, Options, main window, logging, updates, threads | 131 | 16 | 20 | not yet |
| [02-devices-input](02-devices-input.md) | Device scan, events, hooks, keyboard, HidHide | 94 | 19 | 24 | not yet |
| [03-modules](03-modules.md) | Input/output modules, Home, Module Setup, Calibration, Output View, Delete Device | 122 | 18 | 34 | not yet |
| [04-profile-modes](04-profile-modes.md) | Profile load/save, modes, Manage Modes, auto-load, scripts, Swap Devices | 93 | 21 | 27 | not yet |
| [05-actions-editors](05-actions-editors.md) | Action plugins, Configuration page, Keyboard page | 108 | 20 | 22 | reviewed 2026-10-06 (all as recommended) |
| [06-runtime-outputs](06-runtime-outputs.md) | Run/Stop, macros, mouse, vJoy/Xbox output, Logical Device | 85 | 19 | 18 | reviewed 2026-10-06 (all as recommended) |
| [07-button-map](07-button-map.md) | Button Map editor, photos, recovery, print/export | 100 | 19 | 23 | not yet |
| [08-history-pack-automap](08-history-pack-automap.md) | History, Device Pack, Auto Mapper | 103 | 21 | 30 | not yet |
| [09-osc-sound-misc](09-osc-sound-misc.md) | OSC (parked), sound, speech, tray, theme, help; leftover files | 89 | 20 | 27 | not yet |
| **Total** | | **925** | **173** | **225** | |

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
