# Program map (Stage 0)

One page per subsystem: what it owns, entry points, what it talks to,
threads, rule breaks, the behaviour spec ("It should ..." statements S1..,
each with its source), questions for the user (Q1..), known gaps and test
coverage. Written read-only from the code at 4f6bdfa4 (2026-10-06); sections 2-6, 10 and 11 brought up to date 2026-10-09, with each gap's status from `claude/gap-list.md`; counts for 02, 04, 05 and 06 updated 2026-10-10 (R16 + findings batch; 02 also takes in S138-S142, and S147-S148 with gaps TW-XBOX-SLOT, TW-TWIN-NAME, TW-HANDS-ON; 05 also takes in S120 and gaps AE-reference-1, R1, AX1, AX2, O2, SA1 from the action editor matrix). Full map check before release 2026-10-10 (MAPCHECK): every section 2 line count re-read with `wc -l`, every count below recounted from the pages, stale "being built" / "being fixed" notes closed against their commits. OSC rewrite batch 1 (2026-10-10, MAP-APPLY): 09 sections 2-5, 7, 10 and 11 and the matching lines on 01, 05 and 06 brought up to date (`OscPage.qml`, `osc_layout.py`, `osc_companion_check.py`, the shared base; `OscDevice.qml` removed); 09 G-OSC28-G-OSC45 closed except G-OSC36 (Monitor height not remembered); counts recounted, unchanged (fixed gaps still count; S135/S136 gained wording, no new statement). OSC rewrite batch 2 (2026-10-10, MAP2): 09 sections 2-5, 8 (lead's wording within D-09-OSC-PATTERNS / -FBROWS / -ACTSTATE on S145, S147, S151, S153, S156, S158), 10 and 11, and the matching lines on 01, 03, 05, 06 and 08 brought up to date (`osc_pattern.py`, `action_state.py`, `OscFeedbackEditor.qml`); G-OSC46-G-OSC57 closed; counts recounted, unchanged (no new statement, question or gap). Configuration rewrite batch C (2026-10-10, MAP-C): 05 sections 1-8, 10-12 and the matching lines on 01, 02, 03, 06, 08 and 09 brought up to date (`hardware_layout.py`, `keyboard_layout.py`, `ConfigurationPage.qml`, `KeyboardPage.qml`, `ListAppearancePanel.qml`; `BindingCatalog.qml`, `KeyboardInputList.qml`, `InputButton.qml` removed); 05 CF-G1-CF-G11, G11 and RB16 closed; new statements 05 S122a (CS1) and S125a (AP3), S125 and 09 S30 changed (AP2, OP5 reversed), S77 replaced by S129; new gaps 03 #28 (held layout written over a changed file, not verified) and 09 G-OSC-AP (OSC Appearance panel; fixed the same day by AP-PANEL). Shared page parts, to-do 91 Method B (2026-10-10, SB-MAP): 05 sections 2-5, 8 (new S132, PB2), 10 (PB-G1, closed), 11 and 12 (D-05-PAGE-PARTS), and the matching lines on 01 (`Main.qml` `_paneOf`), 06 (`LogicalPage.qml`) and 09 (`ActionPane.qml`, `control_menu.js`, `OscPage.qml`) brought up to date (`PageAppearance.qml`, `control_menu.js` new); counts 05 S +1, gaps +1. Counts: S is every numbered statement in section 8, letter-suffixed ones (S40a) included, retired ones included; Q is every numbered question in section 9; Gaps is the number of gap items in section 10's "code differs from the spec or a rule" list, fixed or not (tracker, to-do and "nothing owns" lists not counted).
Audit fix batches F1-F4 (2026-10-10, F4-MAP): sections 2-5, 7, 10 and 11 refreshed from the audit (`map stale` findings AUD-ACT-03, AUD-BMH-02/03, AUD-DEV-13, AUD-FILES-10, AUD-MOD-05, AUD-OSC-10, AUD-RUN-01, AUD-SHELL-01/02), each fixed item checked in the code; gap counts below take in the new closed F1-F4 entries. Section 8 additions from the user's approval of the audit questions ("Go with your recommendations", 2026-10-10): 05 S122a narrowing, S133 shared keys, new S134; 03 S125; 08 S110; 10 S57; 09 S165; 02 S105/S106 Xbox slot (built 2026-10-10, T1); 06 S94a (built 2026-10-10, L1). Otherwise status notes and [test:] tags only.
Audit fix batch F4, second map pass (2026-10-10, F4-MAP2): T1 (02, 06: Xbox pads by XInput slot; TW-XBOX-SLOT closed), L1 (06: the loop guard follows each event's chain; LD2 closed, to-do 89), F4-AD7 remainder (09: old OSC converters gone, OSC-LEGACY closed, R2 fixed), F3-HIDRESET (02: one HID walk; STRESS-06 partly), F2-EDITORS (05: SJ-03..06 fixed, new gaps A1 and EW-1; 01 AU-56 partly), F4-COLORINFO (01, 09: `ColorInformation` rows gone, R14 resolved), test set-up (F4-DILLPROBE, F-SMOKEEXIT, F4-HARNESS; 01, 02, 09); counts: 05 gaps +3, no new statement or question.
Decisions of 2026-10-10 16:05 written in (SPEC agent): 01 S132, S152; 02 S67 (HH-INUSE-1 closed, D7); 03 S88; 04 S25 (LD14: no version 14 converter, built); 05 S96, S97, new S135 (A1, built); 06 version 14 converters gone from sections 2, 5, 10, 11; 07 S32 (recovery copies, D8); 09 S44a, S97, S116, S121 (O1, D6). Each with its section 12 row.
After commit 3702e630 (2026-10-10, MAP4): `gremlin/action_label.py` deleted and removed from every page (05 Q15 done, RB5 fixed; 09 R3 now two modules); 05 EW-1 closed (editor rows wrap at the pane's minimum width); 09 S14 `inputAdded` also selects an existing input (`listenBound` gone); 01 `window_placement.py` and 02 `hidhide.py` unused settings / `downloadUrl` removed; 08 S104 button names in Title Case (to-do 56 closed). Counts recounted, unchanged (no statement, question or gap added or removed).
MAP6 (2026-10-10, before the can't-be-sent / follow commit): 03 S30, S78a built (gaps 34 closed, 35 open); 04 new S32a (load notice, D-04-CANT-SEND-NOTICE, built); 05 S131, S137-S139 built and S131/S137 widened (D-05-FOLLOW-ALL-PAGES, D-05-QUICK-TAP, D-05-CANT-SEND-ALL, D-09-SENDOSC-TARGET-NAME), new file `gremlin/ui/live_follow.py`, gaps VJ-off, CS-G0, FOLLOW-G1 closed and CS-G1, LD-SYN open; 06 VJ-OFF closed; 09 S32, S141 built, G-OSC66-68 closed, G-OSC69 open.
Owner notices (2026-10-11, SPEC, D-01-OWNER-NOTICES, audit 97, to-dos 100-103): new 01 S155 (the four owner notices), 03 S73a, S75a, S118a, S122a, S126, S127 (S36 reworded: saves apply at once), 05 S140, 06 S97 (and the vJoy claims cache line in section 3), 07 S105, 09 S173, S174, 10 S58, S59 (S7 confirmed as written), each "(not built yet)" until the code lands; new gaps 02 AUD-DEVNAMES, 03 #36 (AUD-DRIVEN) and #37 (AUD-CLAIMS), 06 AUD-LD, 09 G-OSC70, and page 10 AUD-DRIVEN / AUD-DEVNAMES; section 12 rows added. Counts: S +14, gaps +5.

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
| [01-app-shell](01-app-shell.md) | Startup, quit, settings, Options, main window, logging, updates, threads, Help, shared pieces, control tracing, the build (two exes), owner notices (S155) | 156 | 16 | 22 | reviewed 2026-10-06 (all as recommended) |
| [02-devices-input](02-devices-input.md) | Device scan, events, hooks, keyboard, HidHide, trace taps, Gremlin Input Tester, Reset Devices, DirectInput reader, changed layout | 148 | 19 | 42 | reviewed 2026-10-06 (all as recommended) |
| [03-modules](03-modules.md) | Input/output modules, Home, Module Setup, Calibration, Output View, Delete Device | 137 | 18 | 36 | reviewed 2026-10-06 (all as recommended) |
| [04-profile-modes](04-profile-modes.md) | Profile load/save, modes, Manage Modes, auto-load, scripts, Swap Devices | 99 | 21 | 23 | reviewed 2026-10-06 (all as recommended) |
| [05-actions-editors](05-actions-editors.md) | Action plugins, Configuration page, Keyboard page, R16 fixes, action editor matrix; 2026-10-10 Configuration and Keyboard pages on the shared base (S121-S131, S122a, S125a; batch C, built); to-do 91 shared page parts (S132, PB-G1, built); Appearance panel closes when narrow (S135, built) | 141 | 21 | 57 | reviewed 2026-10-06 (all as recommended) |
| [06-runtime-outputs](06-runtime-outputs.md) | Run/Stop, macros, mouse, vJoy/Xbox output, Logical Device, loop guard, output trace | 96 | 19 | 33 | reviewed 2026-10-06 (all as recommended) |
| [07-button-map](07-button-map.md) | Button Map editor, photos, recovery, print/export | 104 | 19 | 23 | reviewed 2026-10-06 (all as recommended) |
| [08-history-pack-automap](08-history-pack-automap.md) | History, Device Pack, Auto Mapper | 115 | 21 | 37 | reviewed 2026-10-06 (all as recommended) |
| [09-osc-sound-misc](09-osc-sound-misc.md) | OSC (picked up 2026-10-09: own module file, per-input settings; Monitor, output and Send OSC, Feedback, encoder, discovery; 2026-10-10 rewrite on the Logical Device page's shared base, S129-S164 in three batches, all built 2026-10-10), sound, speech, tray, theme; shared widgets and foundations | 174 | 20 | 79 | reviewed 2026-10-06 (all as recommended) |
| [10-device-library](10-device-library.md) | Device Library: every device and its saved setups; Copy, Swap, Change vJoy Output; autosaves | 62 | 1 | S1-S56 (+S20a, S53a) built; S6a (D-04-LD-FILE) built (000e35d0); open items: to-dos 47, 50, 51, 52; AUD-DRIVEN, AUD-DEVNAMES (being fixed 2026-10-11) | approved 2026-10-08 |
| **Total** | | **1232** | **175** | **352** (+ page 10) | |

## Most serious findings (to confirm first)

Found by reading the code on 6 Oct. Each needs a failing test (or a
hands-on check) before any fix. Status from the pages' section 10 (2026-10-10).

1. A profile with Map to vJoy may not open on a PC with no vJoy device (05 Q2). Fixed (05 G4).
2. A Run that fails partway can make the next Run handle every input twice (06). Fixed (06 G8, GL-054).
3. Quit may leave the program running with a tool window open, or File > Exit may be refused with Minimize to tray on (01; needs a real-screen check). Fixed (01 K1 GL-110, K2 GL-111).
4. Delete Device writes the whole profile at once, skips the unfinished-actions check, can run while running, and can keep no copy (03 Q4-Q6). Running part fixed (refused while running, 03 gap 11); the rest not re-checked.
5. The Button Map writes some changes before Save, and can overwrite a module file changed elsewhere while it is open (07 G1, G6-G8). Writes before Save fixed (07 G1, G2); G6-G8 open.
6. Load / New Profile may pick the start mode from the old profile (04). Fixed (04 gap 1, GL-053).
7. Run uses unfinished actions (an unpicked Reference placeholder) (05 Q3). Fixed (05 G6, GL-055).
8. A Device Pack import that fails partway loses inputs; Undo Import can undo later saves (08; AU-118). Fixed (08 gaps 2, 24).
9. "vJoy as input" tick restarts or stops a running profile (02 Q1). Fixed (02 G1, GL-119).
10. Nobody owns the list of settings: some are purged at start before they register (01). Fixed (01 K10, GL-117).

## Review order (suggested)

06 Run/Stop and 05 Actions (feed the first redesign), then 03 Modules and
08 History/Pack (redesign 2), then 04, 07, 01, 02, 09.
