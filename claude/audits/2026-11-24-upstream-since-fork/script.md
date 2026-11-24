# Upstream since the fork: scripting (study ST-SCRIPT)

Date: 2026-11-23, 17:31-17:34. Read-only study, git only. Range: merge base
`daf4057f` (2026-08-02) to `upstream/develop` (150 commits). Files compared:
`gremlin/user_script.py`, `gremlin/types.py`, `gremlin/event_handler.py`,
`gremlin/macro.py`, `gremlin/mode_manager.py`, `gremlin/code_runner.py`,
`gremlin/plugin_manager.py`, `gremlin/shared_state.py`, `user_scripts/`.
Our spec: 04 S84-S98, 06 S38 (release after a mode change), decision D-05-R16.

## 1. How upstream moved Event to types.py

It took two commits, and in between there were two `Event` classes.

- **`e0596751` (2026-10-14) "Move Event class to types.py"**, 41 files.
  - It added `class Event` at the end of `gremlin/types.py`, a copy of the old
    class with two methods left out:
    - `display_name()` was dropped. It needed `device_initialization` and
      `common`, which `types.py` cannot import.
    - `from_key()` became the private `user_script._event_from_key(key)`. It
      needed `mode_manager` (it set the current mode name).
  - The only new import in `types.py` is the standard library `uuid`. Event
    uses only `InputType`, `ScanCode` and `HatDirection`, which are already in
    `types.py`. This is how upstream avoided an import cycle: `types.py` still
    imports nothing that imports `event_handler`.
  - It changed every user of the old class to import it from `types`: all
    action plugins, `base_classes.py` (including its `TYPE_CHECKING` import),
    `code_runner`, `device_helpers`, `input_refresh`, `macro`, `mode_manager`,
    `sendinput`, `ui/backend.py`, `ui/device.py`, `ui/script.py`, `ui/util.py`
    and `user_script.py`. `user_script.py` swapped its `event_handler` import
    for `mode_manager`. `user_scripts/example.py` now annotates its callbacks
    with `types.Event` and no longer imports `event_handler`.
  - **It does not touch `gremlin/event_handler.py`**, so the old class stayed
    there until `b10b3ffc`. During those 9 days, `Event.__eq__` ran
    `assert isinstance(other, Event)` against whichever class it was defined
    in.
  - **Unrelated changes in the same commit** (these belong to the action and
    mode study, not to scripting):
    - the `refresh-axis-on-mode-change` option was removed;
    - the `ActionProperty.DisableAutoRelease` property was removed;
    - `AbstractFunctor.reset()` was added;
    - the double tap, tempo, smart toggle and map to mouse actions were
      simplified.
- **`b10b3ffc` (2026-10-23) "Refactor event handling and processing"** deleted
  the old class from `event_handler.py`. `event_handler.py` now imports
  `Event` from `gremlin.types`, so `event_handler.Event` still works, but only
  because of that import. It is not a deliberate alias. The same commit:
  - removed `event_helpers.py`;
  - added `EventGenerator`;
  - added the `InputBindingCallback` protocol to `types.py`.
- **Follow-ups:**
  - `9602a510` added `teardown()` to the callback protocol.
  - `188a44d6` renamed the protocol to `ActionSequenceCallback` and added
    `types.ModeType` (Native/Foreign). The protocol's `__call__` became
    `(event, mode_type) -> bool`.
  - No commit fixed anything about the move itself.
  - No upstream Python file still names `event_handler.Event`. 49 upstream
    files use the `types` one.

## 2-3. Changes a script writer touches

| Change | Upstream commit | What it does | Ours today | Take? | Why | Effort |
|---|---|---|---|---|---|---|
| `Event` lives in `gremlin.types`; scripts annotate `types.Event` | e0596751, b10b3ffc | Move described above; example.py uses `types.Event` | `Event` in `gremlin/event_handler.py:94`; 120 uses of `event_handler.Event` in 49 program files, 71 test files, `user_scripts/example.py`, the new `test/fixtures/scripts/*`; 15 `TYPE_CHECKING` blocks import `event_handler` only for it. `test/fixtures/scripts/upstream_example.py` cannot load here because `types.Event` does not exist when its function definitions are evaluated | **Adapt** | We should move it as upstream did, and do it in one commit (no 9-day overlap). Our class has more than upstream's: `synthetic`, `osc_address`, `ld_chain`, `t_rx`, and an OSC-aware `display_name()` (it uses `gremlin.osc.OSC_DEVICE_UUID` and `device_initialization.device_name`). Those fields can move, because they are plain data. `display_name()` must come out of the class (as an `event_handler` or `common` helper), because `types.py` cannot import `osc` or `device_initialization`; its one caller is in `action_plugins/condition/condition.py:200` (needs checking). `from_key()` would move to `user_script` as upstream did. Ours uses `NO_MODE` and not the current mode, so keep our version | Refactor: 5-10 min per agent (timings.md: refactor). This is a sweep of about 120 files, best split by folder (gremlin/, action_plugins/, tests) with a shared contract. No spec statement changes. Commit line: `Spec: none (no behaviour change)` |
| Callback protocol in `types.py` (`ActionSequenceCallback`, `ModeType`) | b10b3ffc, 9602a510, 188a44d6 | Typed protocol for UI action-sequence callbacks; script callbacks remain plain `f(event)` | `CallbackObject` in `code_runner`, no protocol | **No** (for scripting) | Part of upstream's event-pipeline rewrite, which conflicts with our `event_helpers.ButtonReleaseActions`, run_scope stop stages and input thread (06). The script API does not see it | n/a |
| Scripts get the release/centre after a mode change | b10b3ffc, 188a44d6 (`EventHandler._pending_callbacks`, `_run_callback`) | A script callback that saw a press (or a hat off centre) in mode A is called again with the release in mode B, marked "foreign". A hat gets `Center`. Button callbacks stay pending while `is_pressed` | Ours: S38 releases only vJoy/Logical Device buttons from UI actions (`event_helpers.py`). As far as I can see, a script callback in mode A does not get the release after the mode changes to B (not tested) | **Adapt, needs a spec decision** | It is useful: a script that holds a vJoy button until release would no longer stick across a mode change. But it adds a new statement (04 or 06), so the user must decide first. Build it in our `event_helpers`/`EventHandler` and not by copying upstream's rewrite | Agent feature 3-8 min plus a test (timings.md: agent fix/feature), after the spec answer |
| `keyboard()` accepts a `Key`; `KeyboardVariable.decorator` passes the `Key` | e65e2968 | Numpad and extended keys resolve correctly | Already taken: D-05-R16 R1, 04 S95 (`user_script.py:1893`, `:1330`) | Done | n/a | 0 |
| `_current_script_id` walks `currentframe().f_back` and not `inspect.stack()` | 9602a510 | Faster; releases frame references | Ours already does better (`user_script.py:81`): `_top_level` first, then `sys._getframe(1)` (D-04-Q13-NOWAIT) | No | Ours is already this and more | 0 |
| `PeriodicRegistry.stop` clears `_queue` | 9602a510 | No leftover entries after Stop | Ours rebuilds `_queue` at every `start` (`user_script.py:238`) and runs each start in its own `run_scope` loop; Stop joins with a 2 s timeout (S90) | No | Already equivalent | 0 |
| SelectionVariable bad index logs to `system`, not `user_script` | e0e65272 | Shows in upstream's new log viewer | Ours logs to `user_script` (`user_script.py:1622`) | No (optional) | Depends on how our logs are routed. Whether the user's log should show it is a small detail for the lead to decide | ~1 min |
| `example.py` shows a `LogicalDeviceVariable` | a4bf778b | Example of a logical device variable (named `loggical_Var`, typo upstream) | Our `example.py` has none | **Adapt** (optional) | Good for Help/examples; fix the name. The new `test/fixtures/scripts/` set may cover it already | Agent docs 3-8 min (timings.md) |
| MacroManager API: `queue_macro`/`terminate_macro` replaced by `run_macro`/`stop_macro`/`toggle_macro`, `MacroExecution`, hold macros ignored while active, graceful stop then abort | 2af6d18a, 07eae856 | New scheduler; scripts that call the manager use new names | Ours keeps `queue_macro(macro, chain)`, `terminate_macro`, `sleep`, run_scope stop stages (06). `test/fixtures/scripts/macro_from_button.py` calls `queue_macro` | **No as-is**; look at it in the macro/action study | Rewriting would conflict with our stop stages and `ld_chain` (06 S94a). Scripts written for upstream that call `run_macro` will fail here. An alias would be compatibility code, which our rules allow only as an option the user asks for | n/a here |
| Mode-change callback registry (`is_same_binding`) | bf034739 | Lets actions see whether a mode change keeps the same binding | Already taken (D-05-R16 source list; used by Map to Mouse, 06 D-06-MOUSE) | Done | n/a | 0 |
| `refresh-axis-on-mode-change` option removed; axis refresh reworked | e0596751, 455b8dbb | Axis refresh on mode change is always done its new way | Ours: `CodeRunner._refresh_on_mode_change`, `_refresh_axes` (06) | No (out of scope) | Runtime and modes, not the script API; belongs to the mode/runtime study | n/a |
| Ruff format, `collections.abc.Callable`, generator in `all()`, `raise` not `raise (e)` | 12d061d9 | Style only | Partly taken (D-05-R16 lists 12d061d9) | No | No behaviour; our files have diverged | 0 |

No other changes in this range affect script writers. The variable types, the
decorators, the `joy`/`vjoy`/`keyboard` plugins and `periodic` are unchanged
apart from the rows above.

## Recommendation

1. **Move `Event` to `gremlin/types.py`, the way upstream did, in one batch.**
   Scripts written for upstream R14+ (and its own `example.py`) annotate
   `types.Event` without `from __future__ import annotations`. Today those
   scripts fail to load here with an `AttributeError`, which is the
   `upstream_example.py` fixture's problem. Moving the class also removes
   `event_handler` imports from about 15 `TYPE_CHECKING` blocks and many
   runtime imports. Contract:
   - `gremlin.types.Event` has our full field set (`synthetic`, `osc_address`,
     `ld_chain`, `t_rx`), plus `clone`, eq/hash, str and repr.
   - `display_name()` becomes a function outside `types.py`, for example
     `event_handler.event_display_name(event)`, and its caller is updated.
   - `Event.from_key` becomes `user_script._event_from_key`, which keeps
     `NO_MODE`.
   - `event_handler.py` imports `Event` from `types`.
   - Every program file, test, `user_scripts/example.py`, the Help text and the
     map pages (06, 09) switch to `types.Event`.

   Whether `event_handler.Event` should keep working on purpose is the user's
   call. Our rule is no legacy compatibility by default, so the clean design is
   that `types.Event` is the only documented name. The name still resolves
   anyway, because `event_handler.py` imports it. No spec statement changes,
   so the commit line is `Spec: none (no behaviour change)`.

   Effort: 5-10 min per agent (timings.md: refactor), with 3 agents (gremlin/,
   action_plugins/ with ui/, tests). The lead adds checks and the map (~5 min),
   then quick tests, build/install/live test and CI (~25 min, timings.md: CI
   on a push).
2. **Ask the user about the script release after a mode change** (the third
   row of the table). It is the one upstream behaviour change that matters to
   script writers, and it would be a new spec statement. Effort after a yes:
   3-8 min (timings.md: agent fix/feature).
3. **Leave the macro scheduler rework and the event pipeline rewrite** to the
   macro/runtime studies. Do not copy them into scripting.
