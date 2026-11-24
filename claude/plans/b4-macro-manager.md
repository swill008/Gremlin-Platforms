# B4: macro manager rebuilt on upstream's design (plan, 2026-11-23)

Source: claude/audits/2026-11-24-upstream-since-fork/compare-measure.md item
16 (upstream 2af6d18a). User answers: 14a rebuild ours on upstream's model,
keeping our eight guarantees; port the 18 tests (16 and 17 to our Stop rule,
05 S92); 15a rename to run_macro / stop_macro / toggle_macro (no old names).
Builds after B3 is merged (B3 changes the macro plugin's Hold release and
adds ModeType, which upstream's functor also uses).

## Keep (our eight guarantees)
05 S92 Stop ends macros at once; 06 S21/S32 _step_lock (no step after
RELEASE_HELD); 05 S100 / 06 S70 run_scope ownership + release_owner; run
numbers; 06 S94a Logical Device chain; threads via gremlin.threads (bounded
waits); the per-profile macro delay (code_runner.py ~508); a failing step
ends only its macro.

## Take from upstream
One threading.Condition; MacroExecution with stop/abort flags; a waiting
list; the exclusive rule worked out from the running set (fixes our bug:
a preemptive macro ending forgot a running exclusive, 05 S66 gap); the
repeat delay ends on the macro's own stop; no delay after the last count; a
waiting Toggle counts as on (a second tap switches it off); a release then a
press during the repeat delay restarts a Hold macro; Map to Keyboard sends
keys directly, not through the macro queue (05 S85 gap), with a test that
Stop still releases them.

## New spec statements (written when the build starts; 05 S65/S66 area)
- A Hold or Toggle macro's repeat delay ends as soon as it is released /
  toggled off; a Count macro has no delay after its last repetition.
- A second tap on a Toggle macro that is waiting to run switches it off.
- While an exclusive macro runs, other macros wait, also after a
  preemptive macro that interrupted it has ended.
- Map to Keyboard presses and releases keys at once, even while an
  exclusive macro runs (closes the S85 gap).

## Split
| Agent | Files | Job |
|---|---|---|
| B4-CORE | gremlin/macro.py | manager rebuild + rename (run_macro, stop_macro, toggle_macro, start, stop), keeping the eight guarantees |
| B4-CALLERS | action_plugins/macro/__init__.py, gremlin/input_refresh.py, test/fixtures/scripts/macro_from_button.py (+ scripts.json text), code_runner.py call sites | callers on the new API; Hold via B3's waits_for_end |
| B4-KBD | action_plugins/map_to_keyboard/ | keys sent directly; Stop still releases them |
| B4-PORT | test/action_interaction (new macro scheduling tests + v16 profile) | port upstream's 18 tests; 16, 17 to our Stop rule |
| B4-TESTS | the ~10 test files that reach into removed internals + 21 calls in 8 files | update to the new manager |
| B4-DOC | 05/06 map sections, Help (macro topic) | map + Help |
Lead: spec statements first, merge, full run, build, live check.
