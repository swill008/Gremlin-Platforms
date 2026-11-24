# Upstream since our fork (study, 2026-11-23)

User: "do a study on theirs first to see how they did it, and see if the
changes they implemented we can use." We forked from WhiteMagic/JoystickGremlin
develop at daf4057f (2026-08-02); upstream has 150 commits since. Read from
git only (remote `upstream`).

- script.md (ST-SCRIPT): the script interface; how upstream moved Event to
  types.py (e0596751 + b10b3ffc) and what a script writer notices.
- commits-1.md (ST-UP1): commits 1-75 (to 2026-09-25).
- commits-2.md (ST-UP2): commits 76-150 (to 2026-11-23).

## Combined list (put to the user 2026-11-23)

Fixes with no spec change (gaps): F13-F24 key codes (30151b96); macro
button steps start Released, gap vs 05 S116 (07eae856); sound Stop from
another thread (911444dd); vJoy driver checks once per process (d3f55d9b);
no drop of an action into its own child (86ea050c); two write-only Qt
properties (855eb31c, 2a773013); InputIdentifier.label names (32eebedc,
check where shown); Event moved to gremlin/types.py in one commit.

Need a decision (spec): Condition remembers the press branch (a448e3f3,
d1cd7e1b); releases after a mode change for keyboard/mouse/scripts
(188a44d6 idea, check live first); Condition with an unplugged device
(c479d342); Reference pick list (d6e9b053, 05 S60); default profile
(2877b2e4); smaller install (949f562e).

Measure first: PySide6 wrapper memory (02a280e8 vs our PYSIDE-WRAPPERS);
upstream's 18 macro scheduling tests (2af6d18a) as a checklist.

Not for us: the "Kobold style" UI series, config_registry.py, the
virtual-button / Reference-removal profile format, backup on migration,
the event-handler rewrite, upstream process commits. Python 3.14 is a
separate decision.

## User, 2026-11-23

"I think we should look at all of what they have and compare it to ours to
make sure we can implement these changes ... I would like to incorporate all
of these if we can." Six comparison agents (compare-*.md). The lead's two
concerns (c479d342 False branch on an unplugged device; 2af6d18a macro
rename) are checked as-is against the code too (user: "lets look at using
theirs as is, see if your concerns are still valid"). The older-script
pieces (input_devices, mode helper, deadzone) wait with the other open
questions.

## Comparison results (compare-*.md, 2026-11-23 17:44-17:51)

No code blockers. Lead's concerns checked as-is: c479d342 (unplugged ->
False) does not fire anything at unplug; only later presses change; take it
minus two traps (OSC always false; reading past the claim gate). 2af6d18a:
the rename is mechanical, but the manager as-is drops eight spec guarantees
(05 S92, S100, 06 S21/S32/S70/S94a, thread rules, per-profile delay):
rebuild ours on upstream's design instead (compare-measure.md option a).

Proposed batches: B1 no spec change (F13-F24, write-only props, sound stop,
vJoy checks once, smaller install, Event move); B2 actions (macro steps,
drop into child, Condition branch + reset hook, unplugged device, input
names); B3 releases after a mode change (live test first); B4 macro
manager rebuild + upstream's 18 tests; B5 Reference list, default profile;
memory measurement any time. Questions put to the user in the chat.

## Answers (user, 2026-11-23 18:0x: "all recommended; also lets plan 25. 26 and 27 can be added to the todo")

Questions 1-24 as recommended:
1a display_name() a function in event_handler; 2a NO_MODE in types.py;
3a event_handler.Event removed entirely; 4a 02 S10 example "X Axis";
5a Options > Input names refreshes open editors; 6a S116 covers changed
steps; 7a new S144 (no move into own child; missing container keeps the
action); 8a new S145 release follows the press; 9a c479d342 taken (minus the
OSC and claim-gate traps), new S146, S105 amended; 10a S38 widened +
S38a-S38d after the live test; 11a both modes get the release; 12a
waits_for_end(); 13a 748479a7 not taken; 14a macro manager rebuilt on
upstream's design keeping the eight guarantees, 18 tests ported (two Stop
tests to our rule); 15a run_macro / stop_macro / toggle_macro; 16a
Reference list labels and order under S60, without unused-last; 17a a
Default profile file row; 18a missing own profile -> load the default after
the notice; 19a no start-up default; 20a auto-loaded stay in Recent; 21a
memory measurement alongside B1; 22a "closest-to-center" name; 23a input
viewer 100 ms + redraw limit in B1; 24a example.py Logical Device variable
+ selection warning to the system log in B1.
25: plan the older-script pieces (input_devices, mode-switch helper,
deadzone) now. 26 (Python 3.14 / PySide6 6.11.2) and 27 (dill2.dll) go to
claude/todo.md. Spec statements are written when each batch's build starts.

## Memory and viewer gaps (user, 2026-11-23: "approved as recommended")

1a memory: upstream's way (02a280e8 and follow-ups): a Python factory makes
each QML-created type with the QML item as its Qt parent; biggest holders
first (HardwareLayoutModel, ConfigSectionModel, DeviceLiveState / Device /
AxisCalibration, TraceView, ModeListModel, the InputIdentifier per pane
open), the rest in stages; a guard test fails on a new type made directly in
QML; the probe (tools/memory_probe.py) re-run after. Fix the stale note on
page 01 (PYSIDE-WRAPPERS) and the test_leaks.py comment. Results:
memory.md.
2a UP-VIEWER-OUTPUT-POLL stays a known gap. 3a XboxPadCard.qml gets the
100 ms hold (UP-XBOX-PAD-HOLD).
