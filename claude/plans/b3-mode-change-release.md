# B3: releases after a mode change (plan, 2026-11-23)

Source: claude/audits/2026-11-24-upstream-since-fork/compare-runtime.md item 10
(upstream 188a44d6 + its fix e30732f8; our own design, not upstream's rewrite).
User answers already given (README "Answers"): 10a widen 06 S38 + S38a-S38d
after the live test; 11a the new mode's binding still gets the release too;
12a functors answer `waits_for_end()`; 13a upstream 748479a7 not taken.

## Live test first (shows the gap on the installed program)
Temporary profile (a copy, the user's profile restored after): Keyboard F13 in
Default -> Map to Keyboard F16 (a key nothing reads); F14 in Default -> Change
Mode Switch to B; F13 unbound in B. Run start; outside SendInput F13 down;
GetAsyncKeyState(F16) held; F14 down/up -> mode B; F13 up; wait 200 ms; read
F16. Today expected: F16 still held until Stop. After the fix: released.
Then Run stop, load the user's profile back, Run start, tracing on.

## Contract (agents start together)
ModeType (Native / Foreign) in gremlin.types; Value(raw, mode_type=Native),
Value.mode_type, Value.clone(); AbstractFunctor._should_execute(value,
inverted=False) gates Foreign (only activation Both, only the end value,
never axis floats) and sets self._awaiting_end on a Native start;
AbstractFunctor.waits_for_end() -> bool; AbstractFunctor._sequence_value(value,
press_value); EventHandler keeps pending callbacks per input (input thread
only, no locks or waits), runs pending old-mode callbacks as Foreign first,
then the current mode's as Native; cleared at Run start/Stop/clear/drop_mode.
ButtonReleaseActions' cross-mode entries and IgnoreMode registrations are
removed in the same batch (no double releases).

## Split
| Agent | Files | Job |
|---|---|---|
| B3-CORE | gremlin/types.py, base_classes.py, event_handler.py, code_runner.py, event_helpers.py | pending table, Foreign gate, CallbackObject, virtual buttons, script callbacks (S38b), hat centre (S38c), axis-range buttons (S38d) |
| B3-OUT | map_to_vjoy, map_to_logical_device, macro, change_mode | drop registrations, waits_for_end |
| B3-CONT | chain, tempo, smart_toggle, double_tap, condition (on top of B2's S145 branch memory), hat_buttons, split_axis | container Foreign paths |
| B3-TEST | new test_mode_change_release.py + the pinned tests (test_release_reads_live_mode, test_leaks x2, test_stage1_runtime, test_audit2_coverage, test_vjoy_writers_use_firewall) | 11 new failing-first tests, guard against double releases and stuck entries |
| B3-DOC | page 06 (S38, S38a-d text already proposed; sections 2/3/10/11), Help | spec + map + Help |
Lead: the live test before and after, build, install, commit.
