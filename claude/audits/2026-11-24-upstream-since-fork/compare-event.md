# Compare: moving `Event` to `gremlin/types.py` (C-EVENT, 2026-11-23)

Read-only plan. It builds on `script.md` section 1 (upstream `e0596751` +
`b10b3ffc`, merge base `daf4057f`). Nothing in the program was changed.
Started 17:44, ended 17:50.

## 1. Summary

- The move is safe to do in one commit. `gremlin/types.py` imports only
  `gremlin.error` and `gremlin.axis_names`, and neither imports anything from
  the program, so nothing `types.py` imports leads back to `event_handler`. The
  move cannot create an import cycle. It can only remove edges: 15 modules
  import `event_handler` only to get `Event`.
- Nothing pickles `Event`, checks its module path or sends it to another
  process (section 6), so moving it changes no behaviour.
- No spec statement names `Event`. The commit line is
  `Spec: none (no behaviour change)`, as long as `display_name()` is kept as a
  function (question 1).
- Size: 49 program files (28 in `action_plugins/`, 21 in `gremlin/`),
  `tools/osc_functional_check.py`, `user_scripts/example.py`, 60 test files,
  11 fixture scripts plus `upstream_example.py`'s header and `scripts.json`,
  `action_plugins/AGENTS.md`, and map pages 02, 04, 06 and 09.
  - In program code: 120 uses of `event_handler.Event` (the 120 that
    `script.md` counted) plus 9 direct `from gremlin.event_handler import Event`
    lines.
  - In tests and fixtures: 227 uses.
- Blockers: none. Three small design questions are in section 12. Two traps
  for the agents are in section 10: `user_script.py` shadows the name `types`,
  and the pyright baseline group moves to another file.

## 2. Contract (all agents work to this)

1. `gremlin/types.py` gets, at its end:
   - `import uuid` (the standard library one);
   - `NO_MODE = ""`, which moves from `event_handler.py:91` together with its
     comment (see question 2);
   - `class Event`, a copy of `event_handler.py:94-246`: the same `__init__`
     with all ten arguments (`synthetic`, `osc_address`, `ld_chain`) and
     `self.t_rx`, plus `clone`, `__eq__`, `__ne__`, `__str__`, `__repr__` and
     `__hash__`.
   - It does **not** get `display_name` or `from_key`. Both need imports that
     `types.py` must not have (`common`, `device_initialization`, `osc`,
     `keyboard`, `dill`).
2. `event_handler.py`:
   - deletes `class Event` and `NO_MODE`;
   - imports `Event` and `NO_MODE` from `gremlin.types` (see question 3 on
     whether `event_handler.Event` should keep resolving);
   - gains `def event_display_name(event: Event) -> str`, which is the body of
     today's `display_name` with `self` replaced by `event`. It keeps the OSC
     branch (`OSC_DEVICE_UUID`) and the twin name from
     `device_initialization.device_name` (GL-124). Question 1 covers the
     alternatives.
3. `gremlin/user_script.py`:
   - gets `def _event_from_key(key: gremlin.keyboard.Key) -> Event`, which is
     today's `Event.from_key`. It keeps **`mode=NO_MODE`**. Upstream uses the
     current mode name here; we do not take that change.
   - Line 1912 calls `_event_from_key(resolved_key)`.
   - The import is `from gremlin.types import Event, NO_MODE` (added to the
     existing `from gremlin.types import (...)` block). It must **not** be
     `types.Event`, because line 20 is `import types` (the standard library).
   - The `event_handler` import (line 42) is removed, because it is then
     unused.
4. How each file names the class:
   - Program files and tests add `Event` to their existing
     `from gremlin.types import (...)` block, sorted, and write `Event`
     wherever they wrote `event_handler.Event`.
   - The `event_handler` import is removed where it becomes unused. It stays
     where other names are still used (the "keeps" column in section 4).
   - `from gremlin.event_handler import Event` becomes
     `from gremlin.types import Event`, in the same place (top level, inside a
     function, or `TYPE_CHECKING`). Imports inside a function that were there
     only to get `Event` can move to the top level, because `types` is a leaf
     module. Imports inside a function that also bring `EventListener` stay
     where they are.
   - **User scripts and fixture scripts** use `from gremlin import types` and
     `types.Event`, which is what upstream's `example.py` does. That is the
     style shown to script writers.
5. No file anywhere may name `event_handler.Event`, import `Event` from
   `gremlin.event_handler`, or call `Event.from_key` or `.display_name()` on an
   event. A guard test (section 9) enforces this.

## 3. Import graph (the modules involved)

```
gremlin.types  -> gremlin.error (stdlib only), gremlin.axis_names (stdlib only)
gremlin.event_handler -> types, common, device_initialization, event_helpers,
    input_monitor, keyboard, mode_manager, osc (OSC_DEVICE_UUID), run_scope,
    threads, trace, trace_timing, tree, util, windows_event_hook, input_cache,
    clock, dill, vigem.ids; TYPE_CHECKING: code_runner
event_helpers, input_monitor, sendinput, unknown_action, device_helpers,
    base_classes, action_plugins/reference -> event_handler under
    TYPE_CHECKING or local imports only (these exist to avoid cycles);
    after the move they import Event from types and the cycle risk is gone
gremlin/__init__.py: empty (no package-level imports)
```

- After the move, `types.py` still imports nothing from the program beyond
  `error` and `axis_names`.
- Every new edge points into `types`, a leaf module, so no new cycle is
  possible.
- The guards that would catch a cycle are `test/unit/test_modules_import_alone.py`
  (each module loaded alone in a fresh process) and
  `test/unit/test_program_imports.py` (`joystick_gremlin.py` loaded alone).
  Both are in the quick tests (section 9).
- Side effect to check: `user_script.py` no longer loads `event_handler`.
  Nothing relies on that. `code_runner` and the tests import `event_handler`
  themselves, and `test_modules_import_alone` covers `user_script` loaded
  alone.

## 4. Every file and line that changes

The lines are today's lines that name `event_handler.Event`, import Event
from `event_handler`, or carry the `event_handler,` import.

### Program, `gremlin/` (lead, agent A)

| File | Lines | Keeps `event_handler` for |
|---|---|---|
| `gremlin/types.py` | append Event + NO_MODE (+~160 lines, `import uuid`) | — |
| `gremlin/event_handler.py` | 91 (NO_MODE), 94-264 (class) removed; add `event_display_name`; 43-47 import gains Event, NO_MODE | — |
| `gremlin/user_script.py` | 42 (drop import), 47-51 (add Event, NO_MODE), 108, 1912 (`_event_from_key`), 1961; new `_event_from_key` | — (drop) |
| `gremlin/base_classes.py` | 27, 51 (TYPE_CHECKING), 671, 690 | check |
| `gremlin/code_runner.py` | 137, 169, 221, 230, 236, 268, 286, 337, 826 | EventHandler, EventListener, add_callback, … (keep) |
| `gremlin/device_helpers.py` | 29 (TC), 58, 87, 98 | — (drop) |
| `gremlin/event_helpers.py` | 44 (TC), 57, 87, 88, 112, 148, 172 | — (drop) |
| `gremlin/input_monitor.py` | 26 (TC) | — |
| `gremlin/macro.py` | 615, 624, 633, 908 | EventListener (keep) |
| `gremlin/modules/runtime.py` | 13: `Event` from types; keeps `EventListener, trace_kind` | keep |
| `gremlin/osc.py` | 1280, 1342 (local imports): Event from types; EventListener stays local | keep (local) |
| `gremlin/sendinput.py` | 21 (TC) | — |
| `gremlin/unknown_action.py` | 22 (TC) | — |
| `gremlin/ui/backend.py` | 458 | EventHandler, EventListener (keep) |
| `gremlin/ui/device.py` | 609 (`@QtCore.Slot(event_handler.Event)`), 610, 1150, 1151 | EventListener (keep) |
| `gremlin/ui/live_input.py` | 341, 357, 368 | EventListener (keep) |
| `gremlin/ui/module_model.py` | 1020, 2264, 2282, 2814, 2858, 2879 | EventListener (keep) |
| `gremlin/ui/pair_live.py` | 155 | EventListener (keep) |
| `gremlin/ui/script.py` | 14, 159, 384 | — (drop) |
| `gremlin/ui/util.py` | 87, 155, 172, 186, 222, 261, 288, 371, 373, 457, 464 | EventListener (keep) |
| `gremlin/ui/xbox_viewer.py` | 217 | check |

### Program, `action_plugins/` (agent B)

Each of these files uses `event_handler` only for `Event`, so the
`event_handler,` import is dropped (line given first):

| File | Lines |
|---|---|
| `axis_delta` | 18, 54 |
| `chain` | 18, 59 |
| `change_mode` | 21, 86 |
| `condition/__init__.py` | 21, 66 |
| `condition/condition.py` | 38, 532, 749 |
| `description` | 18, 53 |
| `double_tap` | 22, 67, 103, 110, 117, 122, 129, 163, 176 |
| `dual_axis_deadzone` | 24, 68 |
| `load_profile` | 20, 59 |
| `macro` | 24, 107, 196, 490, 743 |
| `map_to_keyboard` | 18, 62, 105 |
| `map_to_vjoy` | 23, 67 |
| `map_to_xbox` | 118 (import line: check) |
| `merge_axis` | 22, 106 |
| `play_sound` | 19, 56 |
| `response_curve` | 23, 79 |
| `root` | 18, 47 |
| `run_command` | 19, 55 |
| `send_osc` | 23, 122 |
| `smart_toggle` | 19, 60, 97, 114 |
| `tempo` | 22, 61, 76, 105, 118, 127, 132, 139, 146, 154 |
| `text_to_speech` | 18, 53 |

These files keep `event_handler` for other names:

| File | Lines | Keeps |
|---|---|---|
| `hat_buttons` | 100, 108, 125, 145 | EventListener |
| `map_to_logical_device` | 79, 127, 145, 173 | EventListener |
| `map_to_mouse` | 86, 103, 121, 126, 141, 154, 181, 201, 296 | EventHandler |
| `pause_resume` | 74 | EventHandler |

These two only swap their import:

- `reference/__init__.py:38` (TYPE_CHECKING) becomes
  `from gremlin.types import Event`.
- `split_axis/__init__.py:26` becomes `from gremlin.types import Event`.

Docs: `action_plugins/AGENTS.md:48` changes to `gremlin.types.Event`, as
upstream's did.

Local variables named `types` exist at `macro/__init__.py:997`,
`send_osc/__init__.py:158`, `ui/device.py:246` (a parameter) and
`ui/util.py:280`. None of their scopes uses `Event`. Using the
`from gremlin.types import Event` style avoids any confusion with them.

### Scripts and tools (agent C)

- `user_scripts/example.py`: lines 6 (import), 107, 113, 119 and 125 change to
  `from gremlin import types` and `types.Event`. This file has no
  `from __future__ import annotations`, so the annotations are evaluated when
  the script loads. That makes this file the live proof that the move works.
- `test/fixtures/scripts/`: `axes_merge` (2), `axis_to_vjoy`, `button_to_vjoy`,
  `encoder_periodic` (2), `keyboard_reader`, `macro_from_button`,
  `mode_switch`, `osc_input`, `short_long_press`, `three_position_switch` (2)
  and `two_instances` change to `types.Event`.
- `test/fixtures/scripts/upstream_example.py`: lines 7-8 of the header
  ("Today it can't load…") change to say that it loads. Its code stays
  unchanged.
- `test/fixtures/scripts/scripts.json` (lines ~140-147), the `upstream_example`
  entry:
  - `"loads": true`;
  - `"variables"`: the 14 names mapped to their class names (Bool, Float,
    Integer, Keyboard, LogicalDevice, Mode, String, Selection,
    VirtualInput ×3, PhysicalInput ×3 …; take the exact list from a load);
  - `"configured_when_added"`: all 14 variables are `is_optional=True`, so
    this is expected to be `true`; confirm it from the load;
  - remove `expected_error_contains` and `decision_pending`;
  - rewrite `checks`.
- `tools/osc_functional_check.py:569, 1024`: change to
  `from gremlin.types import Event` (EventListener stays from `event_handler`).

### Tests (agents D1, D2)

There are 60 test files with 227 uses: `event_handler.Event` (with
`from gremlin import event_handler`) or `from gremlin.event_handler import
Event[, EventHandler, EventListener]`. In the second form, `Event` is split
out to `from gremlin.types import Event`. The files:

- `test/action_interaction/`: `conftest.py`, `waits.py`
- `test/integration/app_tester.py`
- `test/journeys/test_j08_macro_stop.py`
- `test/unit/action_matrix/`: `harness.py`, `test_ld_pick.py`,
  `test_ld_synthetic_and_notice.py`, `test_matrix_outputs.py`
- `test/unit/`: `test_action_state`, `test_audit2_coverage`,
  `test_audit2_keyboard_calibration`, `test_audit2_macros`,
  `test_audit3_run_stop`, `test_audit3_screens`, `test_audit_runtime`,
  `test_batch2_b2a_input_events`, `test_batch2_b5a_screens`,
  `test_batch2_B5b`, `test_batch3_C3b`, `test_batch3_c4`,
  `test_bounded_waits`, `test_calibration_raw_read_only`, `test_clock_use`,
  `test_config_pages_shared_pieces`, `test_final_02`, `_04`, `_05`, `_06`,
  `_07`, `_09`, `test_fix_X3`, `test_handson_F2_vjoy_output`,
  `test_input_monitor`, `test_input_thread_dispatch`,
  `test_input_thread_real_profile`, `test_input_thread_ui_blocked`,
  `test_keyboard_layout`, `test_ld_refs_a`, `test_leaks`,
  `test_logical_loop_e2e`, `test_map_to_keyboard_recording`,
  `test_mode_on_input_thread`, `test_mode_refresh_and_add_key`,
  `test_mouse_motion`, `test_osc_input_thread`, `test_osc_output`,
  `test_osc_pattern_run`, `test_osc_scripts`, `test_page_follow_ld_kb`,
  `test_record_esc_abort`, `test_release_reads_live_mode`,
  `test_script_suite`, `test_scripts_window_e2e`, `test_stage1_app_profile`,
  `test_stage1_runtime`, `test_trace_osc_actions`, `test_trace_osc_output`,
  `test_trace_taps_in`, `test_trace_timing_e2e`,
  `test_vjoy_viewer_lists_osc`

Two tests need more than an import change:

- `test/unit/test_batch2_b2a_input_events.py:655`:
  `event.display_name()` becomes `event_handler.event_display_name(event)`.
- `test/unit/test_script_suite.py:457-468`: remove the strict xfail and its
  comment, so the test asserts that upstream's example loads (section 9).

Tests that monkeypatch `X.event_handler` (`code_runner.event_handler` ×17,
`macro.event_handler` ×1) are safe, because `code_runner` and `macro` keep
their `event_handler` import. `run.event_handler` and `runner.event_handler`
are CodeRunner attributes, not module imports.

### Map pages and records (lead, agent E)

- `claude/program-map/02-devices-input.md`:
  - line 19 (the `event_handler.py` row): the line count drops by ~170, and
    "`Event` (one input event)" changes to "`Event` lives in `types.py`;
    `event_display_name`";
  - line 65: `Event.t_rx` now lives in `types.py`;
  - line 544: `Event.synthetic`.
- `claude/program-map/06-runtime-outputs.md:16`: the line count, and
  `Event.synthetic`, `ld_chain`, `osc_address` (they are now fields of
  `types.Event`).
- `claude/program-map/09-osc-sound-misc.md`:
  - line 83: `gremlin/types.py` (750 → ~910 lines; add "`Event` (one input
    event, moved from `event_handler` 2026-11-2x, upstream e0596751)",
    `NO_MODE`);
  - line 267: `event_handler.Event` → `types.Event`;
  - line 662: `event_handler.Event(osc_address=)` → `types.Event(...)`
    (historical gap text; update the name only).
- `claude/program-map/04-profile-modes.md:398`: the script suite. Drop
  "`upstream_example.py` xfail … decision pending" and say that it loads.
  Add to section 12 the decision that scripts annotate `types.Event`.
- `tools/pyright_baseline.json`: the `reportIndexIssue` group
  (`"__getitem__" method not defined on type "int"`, file
  `gremlin/event_handler.py`, around line 1293) is `Event.__hash__`'s
  `self.identifier[0]`. It moves to `gremlin/types.py`, so
  `tools/pyright_baseline.py` will report one new error and one fixed error.
  Either run `--update` in the commit, or (cleaner) fix it in place with a
  `ScanCode` narrowing (`assert isinstance(self.identifier, tuple)` in the
  keyboard branch). Check the other `event_handler.py` groups after the move,
  because their file stays the same.
- `doc/source/gremlin/event_handler.rst` is Sphinx automodule, an old upstream
  file, excluded from ruff. It needs no change. Optional: add a `types.rst`.
- Help (`qml/help/*.js`): no Help text mentions `Event`, `event_handler` or
  callback annotations (grep checked), so **no Help change** is needed.
- `claude/todo.md`: nothing about this move found. Add or close a line if the
  lead tracks it there.

## 5. `display_name()` and `from_key()`

- **`display_name()`**: no program code calls it.
  - `action_plugins/condition/condition.py:200` calls
    `AbstractState.display_name()`, a different class.
  - The only caller is the test `test_batch2_b2a_input_events.py:655` (GL-124,
    twin name).
  - Scripts could call `event.display_name()`, but Help does not document it,
    and upstream dropped it in `e0596751`.
  - Plan: `event_handler.event_display_name(event)` (question 1).
- **`from_key()`**: one caller, `user_script.py:1912` (the `@keyboard`
  decorator). It moves to `user_script._event_from_key` with `NO_MODE`.
  - Ours stamps `NO_MODE`; upstream stamps the current mode name. With ours,
    `EventHandler.process_event` stamps the mode on the input thread (GL-065).
    `CallbackRegistry.add` gets the decorator's `mode` separately, so the
    event's mode is not used as a key (the hash ignores `mode`).
  - Keeping `NO_MODE` keeps today's behaviour exactly.

## 6. Serialisation, pickling and module-path checks

Each of these was grepped in `gremlin/`, `action_plugins/` and `gremlin_ctl/`:

- `pickle`, `copyreg`, `__reduce__`, `__getstate__`: none on Event.
- `dill`: the `dill` here is the input DLL wrapper (DILL), not the pickling
  library.
- `multiprocessing.connection`:
  - `device_disable.py` and `gremlin_device_helper.py` pickle
    `protocol.make_request(...)` dicts and lists only, not Events;
  - `control_api.py` and `gremlin_ctl/client.py` use `send_bytes` with JSON.
- `__module__` checks:
  - `plugin_manager.py:309` covers QObject subclasses only;
  - `swap_devices.py:66` checks a value's module with
    `startswith(("gremlin", "action_plugins"))`, which `gremlin.types` still
    passes;
  - `ui/health_model.py:105` and `ui/search_model.py:117` compare with
    `"builtins"` only.
  - None of them cares whether Event lives in `event_handler` or `types`.
- `isinstance(..., Event)`: only `Event.__eq__` and `__ne__`, which move with
  the class. There is one class, so there is no split-class problem like
  upstream's 9-day window.
- Qt: `QtCore.Signal(Event)` and `Slot(Event)` (`event_handler.py:274-280,
  864`; `modules/runtime.py:102-103, 232, 247`; `ui/device.py:609`) use a
  Python type. PySide carries these as Python objects whatever module they
  come from. No change is needed except for the name.
- OSC and remote: `osc.py` builds Events from received messages, and
  `OscRuntime` sets `osc_address`. Events never cross the network or a process
  boundary.

## 7. Spec statements

- No section 8 statement and no section 12 decision names `Event`,
  `event_handler.Event`, `display_name` or `from_key` (grepped across
  `claude/program-map/*.md`). The map mentions it only in section 2, 3 and 10
  texts (section 4).
- `upstream_example.py` loading is a new capability, not a changed statement:
  scripts written for upstream R14 load here. The user is already deciding it
  in `script.md`. Once they say yes, record it as a decision in 04 section 12
  (the "decision pending" in `test_script_suite.py` and `scripts.json`).

## 8. Existing tests that pin it

These are the only pins that are more than an import name:

- `test_script_suite.py::test_upstream_example_loads_unchanged` (strict xfail).
  It turns into an XPASS failure once the move works, which is the intended
  flip.
- `test_script_suite.py::test_script_loads_as_the_manifest_says[upstream_example.py]`
  expects the load to fail until `scripts.json` changes.
- `test_scripts_window_e2e.py::test_scripts_that_cant_load_say_why_and_cant_be_configured`
  takes `upstream_example` from `_entries(False)` today. After the manifest
  change it moves to `_entries(True)` (no error, configure on).
  `test_configured_when_added_matches_the_manifest` then also checks it.
- `test_batch2_b2a_input_events.py:655` calls `event.display_name()`.

## 9. New tests (proof)

1. **Flip**: remove the strict xfail on `test_upstream_example_loads_unchanged`.
   On the old code it fails (`AttributeError: module 'gremlin.types' has no
   attribute 'Event'`), and on the new code it passes.
2. **Manifest**: `test_script_loads_as_the_manifest_says[upstream_example.py]`
   checks the 14 variable types and `configured_when_added`.
3. **Real path**: `test_scripts_window_e2e.py` (the real program, Scripts
   window). `upstream_example` gets no error and configure is on.
4. **Guard (new, `test/unit/test_event_lives_in_types.py`)**:
   - an AST scan of `gremlin/`, `action_plugins/`, `user_scripts/`, `test/`
     and `tools/`: no `event_handler.Event` attribute, no
     `from gremlin.event_handler import Event`, no `.from_key(`;
   - `gremlin.types.Event` has `synthetic`, `osc_address`, `ld_chain` and
     `t_rx`, and `clone()` copies the first three;
   - `user_script._event_from_key(key).mode == NO_MODE`;
   - `event_display_name` gives "OSC - …" for `OSC_DEVICE_UUID`;
   - if question 3 picks b), `not hasattr(event_handler, "Event")`.
5. **Cycles**: run `test_modules_import_alone.py` and `test_program_imports.py`.
6. **Live** (build, install and test before continuous integration (CI), a
   standing rule):
   - install the build;
   - add `upstream_example.py` in the Scripts window: it shows no error;
   - press a key bound by a script: `@keyboard` still fires.

Quick tests before the commit: `python test/run_tests.py --changed`,
`tools/pyright_baseline.py`, `ruff check`, and the tests in points 1-5. Note:
`--changed` on a batch touching `types.py`, `event_handler.py` and
`base_classes.py` selects nearly the whole suite. The 2026-11-23 rows for a
near-full `--changed` took 10-12 min.

## 10. Risks

1. **`user_script.py` shadows `types`** (line 20, `import types` from the
   standard library). Writing `types.Event` there would be an `AttributeError`
   at decorator time. Use `from gremlin.types import Event` (contract 3).
2. **The pyright baseline group moves file** (section 4). Without an update or
   a fix, `pyright_baseline.py` fails the commit.
3. **Removing an import that is still used**:
   - Agents must keep `event_handler` where the "Keeps" column says so.
   - ruff F401 catches an unused import, and the import-alone test catches a
     missing one.
   - `base_classes.py`, `xbox_viewer.py` and `map_to_xbox` are marked "check":
     the import form differs, so the agent should read those lines.
4. **Merge conflicts with in-flight work**:
   - The touched files are spread widely, so any open branch or worktree that
     edits action plugins or `ui/util.py` will conflict on import lines.
     Worktree `.claude/worktrees/zen-mclaren-4f3271` exists.
   - The current branch, `feature/steam-controller`, has an uncommitted
     design that names no Event today.
   - Do the move first, or rebase the other work onto it.
5. **Built copy**: `dist/` holds a built copy. It is rebuilt, so do not edit
   it. Grep tools must exclude `dist`, `.claude` and `.agent-logs` (old probe
   scripts there still import `event_handler.Event`; they are not run).
6. **Scripts written for our earlier builds** that annotate
   `event_handler.Event` fail to load if question 3 is b). This is an
   unreleased program, so there are no users to protect, but the user's
   second person may have scripts. Worth one line in the release notes.
7. **Ordering**:
   - Agents B, C and D cannot import-test until agent A's `types.Event` exists.
     Stagger them: A writes `types.py` and `event_handler.py` first (~2 min),
     then the others start.
   - Or give B, C and D the contract and let them edit blind, testing only
     after A lands. Edits are mechanical, so blind editing is fine.

## 11. Split (for the lead's table)

| Agent | Files | Job | Why parallel / why one |
|---|---|---|---|
| A (core) | `gremlin/types.py`, `event_handler.py`, `user_script.py`, `base_classes.py`, `code_runner.py`, `device_helpers.py`, `event_helpers.py`, `input_monitor.py`, `macro.py`, `modules/runtime.py`, `osc.py`, `sendinput.py`, `unknown_action.py` | Move the class, NO_MODE, `event_display_name`, `_event_from_key`; switch `gremlin/` users | Owns the contract's source; starts first |
| B (plugins) | 28 `action_plugins/*` files + `action_plugins/AGENTS.md` | Mechanical switch | Own folder; edits blind to the contract |
| C (ui + scripts) | `gremlin/ui/` (9 files), `user_scripts/example.py`, `tools/osc_functional_check.py`, the 11 fixtures, `upstream_example.py` header, `scripts.json` | Switch; manifest entry from a real load | Own files; manifest needs A landed |
| D1 (tests a-m) | 30 test files `action_interaction` … `test_mode_*` | Switch imports | Test-only |
| D2 (tests n-z + new) | 30 test files `test_mouse_motion` … `test_vjoy_*`, `test_script_suite.py` xfail removal, new `test_event_lives_in_types.py` | Switch; flip; guard | Test-only; guard written to the contract |
| E (map) | map 02, 04, 06, 09; `pyright_baseline.json` (or the fix in A's `__hash__`) | Map sections 2, 3, 10, 12; baseline | Docs alone |

Left out: an end-to-end agent. The real path is already the existing
`test_scripts_window_e2e.py` plus the lead's live install check, so a separate
agent would duplicate it. Carry-through (Library, Export, Restore, History,
Device Pack) does not apply: Event is never saved to a file. That gives six
agents, within the ~8-10 limit.

## 12. Questions for the user (before building)

1. **Where should `display_name()` go?** No program code calls it; a script
   could, but Help doesn't document it.
   - a) A function, `event_handler.event_display_name(event)`, which keeps our
     OSC and twin-name logic (recommended).
   - b) A method on `types.Event` that imports `device_initialization` and
     `osc` inside the method, so scripts keep `event.display_name()`. This
     breaks the rule that `types.py` is a leaf module.
   - c) Drop it, as upstream did, and rewrite the one test.
2. **Where should `NO_MODE` live?**
   - a) In `types.py` beside Event (recommended): it describes an Event field,
     and `user_script` then needs no `event_handler` import.
   - b) Stay in `event_handler`, so `user_script` keeps importing it.
3. **Should `event_handler.Event` still resolve?**
   - a) Yes, as a side effect of `from gremlin.types import Event` inside
     `event_handler.py` (upstream's state). The guard test bans its use.
   - b) No. `event_handler.py` uses `types.Event` itself, and the guard
     asserts `not hasattr(event_handler, "Event")`: the old name is truly gone
     (cleanest under the unreleased rule; ~30 extra name edits inside
     `event_handler.py`).

## 13. Effort

Quoted from `claude/timings.md`:

| Step | Kind in timings.md | Time |
|---|---|---|
| Six parallel agents | refactor, 5-10 min per agent | ~10 min |
| Lead checks and map | — | ~5 min |
| Quick tests | 2026-11-23 rows for a near-full `--changed` | 10-12 min |
| Build, silent install and live check | 2026-11-23 rows | 2-3 min |
| Commit and push | — | ~2 min |
| CI | ~25 min | in the background |

That comes to about 30-35 min of active work, then CI.
