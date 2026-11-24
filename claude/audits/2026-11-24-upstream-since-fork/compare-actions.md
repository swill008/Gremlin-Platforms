# Upstream since fork: action items compared in full (C-ACTIONS)

Date: 2026-11-23 (study for the 2026-11-24 upstream comparison). Read-only study; nothing in the program was changed.
Merge base daf4057f, remote `upstream` fetched. Items 2, 5, 9 and 11 from `commits-1.md` / `commits-2.md`.
The checks ran on the Poetry venv Python with a temporary USERPROFILE and `QT_QPA_PLATFORM=offscreen` (no windows). The scripts were kept in the scratchpad.

Summary:

| Item | Upstream | Bug in ours? | Spec | Profile format | Effort (timings.md) |
|---|---|---|---|---|---|
| 2 | 07eae856: a macro button step goes back to Pressed when its input or input type changes | Yes, confirmed by running it | S116 wording widened (needs the user's OK) | none | 3-8 min (agent fix) |
| 5 | 86ea050c (part): refuse moving an action into its own subtree | Yes, confirmed, plus a second bug: a refused move deletes the action | new S144 (needs the user's OK) | none | 3-8 min (agent fix) |
| 9 | a448e3f3 + d1cd7e1b: Condition remembers its branch; an axis branch change resets the old branch | Yes, confirmed: a held output gets stuck | new S145 (needs the user's OK; the item adds one), plus a behaviour change to decide | none | 5-10 min (agent fix plus the reset hook) |
| 11 | c479d342: the stored device name for an unplugged device (+ optionally "unplugged means false") | Yes (the name is shown as "Unknown Joystick") | name part: none or a small S140 note; as-is part: new S146 and an S105 amendment | none | 3-8 min per part (agent fix) |

---

## Item 2: 07eae856, macro button steps default to Released

**Upstream.** Upstream changes `value = False` to `value = True` in four places in `action_plugins/macro/__init__.py`:
- `JoystickActionModel.updateJoystick` (two branches);
- `LogicalDeviceActionModel` when the input type changes;
- `VJoyActionModel._set_input_type`.

It also changes `gremlin/macro.py LogicalDeviceAction.create` so a button step starts on True.

**Ours.** All the `create()` methods already start button steps on True (05 S116):
- `macro.py:604` Joystick;
- `:726` Key;
- `:858` Logical Device, which already has the same True-for-button rule;
- `:1024` OSC.

The gap is in the editor models, which still reset the value to False:
- `action_plugins/macro/__init__.py:126` (`updateJoystick`: picking a button input);
- `:284` (`_set_logical_input_identifier`: the type changes to a button);
- `:582` (`VJoyActionModel._set_input_type`: axis or hat changed to button).

Our first upstream branch (empty data) is already replaced by the Esc early return (`test_record_esc_abort.py`), so it needs no change.

**Confirmed by running it.** The run gave these values:
- a new Joystick step starts at `value True`;
- after `updateJoystick([button event])` it is `False`;
- a vJoy step changed from axis to button is `False`.

So a new step that the user then points at a button shows **Released**, which contradicts the intent of S116.

**Change.** Three lines in `action_plugins/macro/__init__.py`, all `False` changed to `True`. Nothing in `gremlin/macro.py`.

**Conflicts.** None found:
- Undo and History record the step's XML as before.
- The Mouse Button step is not touched by upstream. Ours already presses; check its model has no similar reset.

**Spec.** S116 says "new … steps should start on Pressed". The wording does not cover "the input or type of an existing step is changed to a button".

Suggested change (user's OK needed): append "…; a step whose input, or whose type, is changed to a button also starts on Pressed."

**Profile format.** No change. Saved steps keep their own value.

**Tests pinning the old behaviour.** None found:
- `test_record_esc_abort.py:98` keeps True on Esc, and that still holds.
- `test_new_action_defaults.py` and `test_macro_raw_steps.py` test `create()` only.

**New failing test.** Add to `test/unit/test_new_action_defaults.py` (S116):
- `updateJoystick` with a button event gives `value is True`;
- a vJoy step changed from axis to button gives True;
- a Logical Device step changed from axis to button gives True.

**Risks.** Very low.

**Effort.** 3-8 min (timings.md: agent fix).

---

## Item 5: 86ea050c, refuse dropping a container into its own subtree

**Upstream.** Only the relevant part of the large drag-and-drop commit is compared here. `gremlin/ui/profile.py` gains `InputItemBindingModel._is_descendant_of(candidate, ancestor)`, which walks `_child_lookup`, and `can_move_action(source, target)`.

`move_action` now does two things before anything is removed:
- It refuses a move when the target is the source or inside the source's subtree, with a `system` log warning.
- It checks the container and the position.

Its comment gives the reason: "insert_action raises on an unknown selector … by which point a rejected move has already dropped the source action".

The rest of the commit is not part of this item: the new position-based `move_action(source, parent, container, position)` signature, the new QML DragSession, and the macro step drag. That rest is upstream's new drag-and-drop UI.

**Ours.** `gremlin/ui/profile.py:389 move_action(source, target, container)` has no subtree check. It removes the source first (`:418`, `:434`, `:441`) and then appends it.

`gremlin/ui/action_model.py:324 dropAction` checks only `source == target`.

`_append_drop_action` (`:439`) catches `GremlinError` with the comment "A move the tree refuses leaves it as it was". That comment is false: the source has already been removed.

The QML drop areas let these drops through. `qml/ActionNode.qml:420` and `ConditionAction.qml`, `ChainAction.qml` and the other `ActionDragDropArea`s check only `type == action` and the same root.

**Confirmed by running it.** Two cases:
- Root > Chain A > Chain B. Moving A into B's container "0" is accepted. Root's children become `[]`, and B now holds A: a detached cycle in the library. Saving it either loses the actions or, through the library's references, loops. The save was not run; that last part is unverified.
- Moving an action to a container that doesn't exist raises `GremlinError` (caught by `_append_drop_action`). Root's children are `[]` afterwards: **the action was deleted** although the comment says the move was refused.

**Change.** The shared owner is `gremlin/ui/profile.py InputItemBindingModel`:
1. Add `_is_descendant_of` and `can_move_action`, as upstream has them.
2. In `move_action`, after `_edit_refused()` and before any `remove_action`:
   - refuse when `not can_move_action(source, target)`, with a bounded `system` warning;
   - when `container is not None`, refuse when the container is not one of the target's (check `target.action_data.get_actions(container)` or its container names) instead of letting `append_action` raise after the removal.
3. Optionally, `action_model.dropAction` asks `can_move_action` first and calls `sync_data()` on a refusal, the same as for `source == target`.

Upstream's new signature and QML are not taken.

**Conflicts.**
- `_edit_refused()` (the draft or Run edit gate) stays first.
- `drop_unused=False` (S47, a moved action stays in the library) is unchanged.
- Undo and History: a refused move changes nothing, so it has no entry. Check that the binding pane's draft Undo snapshot is taken only after the move succeeds (`test_audit3_actions_undo.py`).

**Spec.** New statement, suggested S144 on page 05 (user's OK needed): "Moving an action (drag and drop) onto itself or into a container inside it is refused and changes nothing; so is a move to a container the target doesn't have." S47 stays.

**Profile format.** No change.

**Tests pinning the old behaviour.** None:
- `test_action_editor_fixes.py:77` (sibling move) still passes.
- `test_sequence_reorder.py` covers the input item's sequence reorder, which is a different path.

**New failing tests.** In `test/unit/test_action_editor_fixes.py` (or a new `test_move_into_own_subtree.py`):
1. Root > Chain A > Chain B. Moving A into B "0" leaves the tree and the library unchanged.
2. A move to an unknown container leaves the source in place.
3. Through `ActionModel.dropAction`, the real slot, case 1 leaves the tree unchanged.

**Risks.** Low. The descendant walk is O(n) over `_child_lookup` and runs per drop only.

**Effort.** 3-8 min (timings.md: agent fix).

---

## Item 9: a448e3f3 + d1cd7e1b, Condition remembers its branch; an axis branch change resets

**Upstream.**

a448e3f3 changes `ConditionFunctor`:
- It keeps `_functor_cache = (functors, flag)`.
- `__call__` dispatches on `data.behavior_type`.
- **Button and key:** the press selects the branch and caches it. The release goes to the cached branch; with no cached press, the condition is evaluated. The cache is then cleared.
- **Hat:** Centre goes to the cached branch. A push whose branch differs from the cached one first sends Centre to the old branch, then runs the new branch and caches it.
- **Axis:** evaluated on every event.
- `_select_functors` returns `[]` on an error.

d1cd7e1b changes the axis case: when the selected branch changes, it calls `reset_functor_tree` on every functor of the old branch. The helper moves from `code_runner._reset_functor_tree` to `base_classes.reset_functor_tree`.

**This depends on upstream's `AbstractFunctor.reset()` hook, which we do not have.** It was added after the fork. `reset()` is "Stops outputs that persist without further input events". Map to vJoy, Map to Logical Device and Map to Mouse use it to stop relative-axis motion. Our base classes have no `reset()`, and `code_runner` has no `_reset_functor_tree`.

**Ours.** `action_plugins/condition/__init__.py:64-88` evaluates the condition on every event, press and release, and runs whichever branch is true at that moment.

**Confirmed by running it.** A recorder functor on each branch: the press (condition true) is followed by the release (condition now false). The result was `true branch got [True]` and `false branch got [False]`, so **the true branch never gets the release**. A Map to vJoy button or Map to Keyboard in the TRUE list stays held until the next press.

`test/action_interaction/test_condition.py::test_release_during` (lines 34-50) pins this bug: it asserts `OUT_BUTTON_1` is still pressed after both inputs are released.

**Change.**
- `action_plugins/condition/__init__.py ConditionFunctor`:
  - port `_process_button`, `_process_hat`, `_process_axis` and `_select_functors`;
  - keep our `except ca.MissingOscInput: return []` (bounded log, no branch) and `except GremlinError` in `_select_functors`;
  - add a `case _:` fallback (button behaviour) for any other behaviour type; upstream's `match` silently runs nothing for other types.
- Axis reset (d1cd7e1b) on our design:
  - add a default no-op `reset()` to `AbstractFunctor` (`gremlin/base_classes.py`, page 05 owns it);
  - add `reset_functor_tree(functor)` next to it;
  - `action_plugins/common.py RelativeAxisLoop` gets `reset()` = `_ask_to_stop()`, which Map to vJoy and Map to Logical Device inherit.
  - This is a new hook, so `test_references_declared`-style guard thinking applies (design-for-change). A guard is optional, because the default no-op is safe.
- Threads: the cache is written only on the input thread (D-06-INPUT-THREAD; functors are called there), so it needs no lock. Functors are rebuilt each Run, so the cache starts empty every Run. A release after Stop is not delivered (run_scope).

**Behaviour change to decide (user).** `test_current_input`: upstream changed its expectation. With a Current Input "pressed" condition, the release now goes to the TRUE list (the branch chosen at the press), not to the FALSE list. A profile written as "TRUE: press macro, FALSE: release macro" stops releasing.

Our test (`test_condition.py:52-56`) waits for `OUT_BUTTON_3` to go false after the release and would fail. This is the reason the statement must be the user's call:
- a) take upstream's rule (the release follows the press; recommended, because it stops stuck outputs and the Current Input pattern can be rebuilt with the release in the TRUE list);
- b) keep "evaluate on release" for Current Input conditions only.

**Spec (the item adds one).** Suggested S145 on page 05: "A Condition on a button or key sends the release to the list (TRUE or FALSE) it chose at the press; a release with no press seen is evaluated. On a hat, Centre goes to the list chosen at the last push, and a push that changes list first centres the old list. On an axis, every move is evaluated, and a change of list stops what the old list left running (relative axis motion)."

**Profile format.** No change. Nothing new is saved.

**Tests pinning the old behaviour (update with the change).**
- `test/action_interaction/test_condition.py::test_release_during`: three asserts flip, as upstream did.
- `::test_current_input`: flips if a) is chosen.
- `::test_condition_with_tempo`: upstream adds an `OUT_BUTTON_2` released assert.

**New failing tests.** Port upstream's four functor tests to `test/unit/test_action_condition.py`:
- `test_functor_button_release_follows_press`;
- `..._release_without_press_evaluates`;
- `..._hat_branch_change_centres_old_branch`;
- `..._axis_evaluates_every_event`.

Add:
- an axis branch-change test where a recorder with `reset()` is reset;
- a `RelativeAxisLoop.reset()` stops-the-loop test;
- the updated `test_release_during` as the end-to-end test on the real path (jgbot).

**Risks.**
- Medium (behaviour visible to users): the Current Input pattern above.
- The hat cache compares lists by identity, which is correct because the functors are fixed per Run.
- Missing OSC on the press caches `[]`, so the release runs nothing (consistent with E8).

**Effort.** 5-10 min (timings.md: agent fix is 3-8 min; the reset hook spans `base_classes` and `common.py`, which is near a refactor's 5-10 min). Two agents could split it: condition functor, and the reset hook plus RelativeAxisLoop.

---

## Item 11: c479d342, the stored device name for an unplugged device (and optionally "unplugged means false")

**Upstream.** Two parts in one commit.
- **(A) Name.** `gremlin/ui/device.py device_and_input_names` catches `KeyError` for an unplugged device and returns the name stored in `shared_state.current_profile.device_database` (`_retrieve_device_name_from_database`), else "Unknown Joystick".
  - `JoystickCondition.JoystickState.display_name` uses `device_and_input_names`.
  - `JoystickCondition.__init__` connects `EventListener().device_change_event` to emit `statesChanged`, which refreshes the labels.
- **(B) Behaviour.**
  - `JoystickState.is_connected()` = `DILL.device_exists(...)`.
  - `JoystickCondition.__call__` returns False when any state's device is not connected.
  - `get()` reads `Joystick()[uuid]` directly; `initialize_for_uuid` is removed.

**The two parts can be separated.** (A) touches only naming: `device_and_input_names`, `display_name` and the `statesChanged` refresh. (B) is the `__call__` override plus `is_connected`; the `get()` refactor is not needed for it.

**Ours.**
- The naming owner is `gremlin/ui/device_names.shown_name` (alias, then `device_initialization.shown_name`, then `device_name`, then `DILL.get_device_name`). There is no `device_and_input_names` in our `gremlin/ui/device.py`.
- `JoystickState.display_name` (`action_plugins/condition/condition.py:676`) does not use `shown_name` at all. It returns `f"Unknown Joystick - {input}"` when `self.joystick is None`, otherwise `joystick.name`, so no alias either.
- The profile's stored names already have a reader: `device_initialization._profile_names()` (`:493`).
- The macro step label `action_plugins/common.joystick_label` reads `DILL.get_device_information_by_guid` directly, which is another naming path for an unplugged device. Its result for a missing device is unverified (probably an empty name).

### Part A plan (the name)

Fix at the shared owner:
- `gremlin/device_initialization.shown_name` (or `device_name`): when the device is not in the list and the driver gives no name, return the profile's stored name (`_profile_names()`), else "".
- `JoystickState.display_name`: use `device_names.shown_name(self.device_uuid)` (aliases and twin names, as S140 already wants), with "Unknown Joystick" only when that is empty.
- Refresh: our "device names changed" notice (`signal.deviceNamesChanged`, D-01-OWNER-NOTICES, which also fires on a device scan) already drives the condition editor's names (S140). Do not add upstream's per-condition `device_change_event` connection: it is never disconnected, and it is a second notice.
- Optionally, `action_plugins/common.joystick_label` (macro step label) also uses `shown_name`.

Spec: no new statement. Optionally add to S140: "an unplugged device shows the name the profile stored for it".

Profile format: none; the stored names are already saved.

Tests:
- New `test/unit/test_device_name_stored.py`, the same three cases as upstream's `test_device.py`: connected gives the live name, unplugged gives the stored name, unknown gives empty / "Unknown Joystick".
- `JoystickState.display_name` for an unplugged stored device.
- Re-check that nothing pins the "Unknown Joystick - …" text: grep found it only at `condition.py:689`.

### Part B as-is: lead's question, is the "unplug fires the False branch" concern valid?

**When a Condition is evaluated.** Only in `ConditionFunctor.__call__` (`action_plugins/condition/__init__.py:64`). That happens only when an event for the binding's own input reaches its callback (`code_runner` CallbackObject to functor). Nothing evaluates conditions on a device change:
- upstream's new `device_change_event` slot only emits `statesChanged`, a QML label refresh;
- our `event_handler` device update (`event_handler.py:525-550`) emits `device_change_event` with no evaluation.

**What runs at the moment of unplugging.** Only `EventListener._let_go` (`event_handler.py:553`), which emits a release or Centre event for each button or hat **the unplugged stick itself** was holding (02 S28). Those events reach the bindings of that stick's own inputs:
- With item 9 in, a Condition bound to such a held button sends that release to the list chosen at the press. The False list is not newly run.
- Without item 9, the release is evaluated. Under as-is (B), a check on the unplugged stick returns False, so the FALSE list gets a release event (not a press). Today ours reads the let-go cache for that check.
- Axes send nothing at unplug.

So **nothing presses anything "mid-flight" at the moment of unplugging** in either version.

**Afterwards (the real difference).** When the user next presses a bound input on a still-connected device, the condition is evaluated:
- **Upstream as-is:** any Joystick check on the unplugged stick is False. The condition then becomes false (All) or depends on the others (Any), so the FALSE list runs, for example pressing a key.
- **Ours today:** `JoystickState.get()` → `_find_joystick()`. Our cache never removes a stick (02 map: "nothing removes an unplugged stick").
  - For a stick seen since start, it reads through `gremlin/modules/inputs`: buttons are let go, so a "pressed" check is already **False and the FALSE list already runs today**. A "released" check is True. An axis reads centred (S105), so a range check depends on the range. A hat reads Centre.
  - Only a stick never seen since start raises `GremlinError`: logged, neither list.

**Verdict.**
- The concern is **not valid** for the moment of unplugging: nothing runs then except the unplugged stick's own releases, and with item 9 those go to the press branch.
- It is **partly valid** for later presses. As-is makes "False" uniform for every check on an unplugged stick: Released, a range that includes centre and hat Centre flip from True to False, and a never-seen stick goes from neither list to the FALSE list.
- For the common "button is pressed" check, ours already runs the FALSE list today.

**Two traps in the as-is code (must not be copied literally).**
1. `is_connected` uses `DILL.device_exists` for every state. Our Joystick condition also holds **OSC inputs** (`device_uuid == ids.OSC`, 09 S159), which have no DILL device. Copied as-is, **every OSC condition would always be false**. OSC states must be left out; a missing OSC input keeps E8 (neither branch).
2. Upstream's `get()` reads `Joystick()[uuid]` directly. Ours reads through `gremlin/modules/inputs`, the claim gate (an unclaimed input reads neutral). The layer rule says nothing skips the input module. Keep `get()` as it is.
   - Use `gremlin.modules.hardware.device_connected` (the UI's door to the driver) or `inputs._unplugged`, made public, instead of DILL.

**As-is plan (B).**
- `action_plugins/condition/condition.py JoystickCondition`:
  - add `__call__`: if any non-OSC state's device is not plugged in, return False; else `super().__call__(value)`;
  - add `JoystickState.is_connected()` through the modules layer (above);
  - leave `initialize_for_uuid`, `_find_joystick` and `get()` as they are.
- Spec, page 05:
  - new S146: "A Joystick condition that checks a controller that isn't plugged in is false, whatever it checks (an OSC input follows 09: missing runs neither list)";
  - amend S105 ("…read centred", Merge/Deadzone actions): conditions no longer read the centred value but are false;
  - cross-reference 02 S28.
- Tests:
  - port `test_condition_false_for_disconnected_device`, using a fake device list rather than real DILL;
  - a Released check on an unplugged seen stick is now False (fails on the old code);
  - an OSC state is not affected;
  - end to end with jgbot: simulate the unplug through the device-list update, press a bound input on another device, and check that the FALSE output fires; with item 9, a release at unplug goes to the press branch.
- Profile format: none.
- Effort: 3-8 min (timings.md: agent fix).

---

## Blockers and decisions needed before building

1. **S116 wording (item 2).** Widen it to cover changing an existing step to a button.
2. **New S144 (item 5).** Refuse moves into the action's own subtree or to an unknown container.
3. **New S145 (item 9)** and the Current Input choice:
   - a) the release follows the press (upstream; recommended);
   - b) keep evaluating the release for Current Input.
4. **Item 9 needs a new `AbstractFunctor.reset()` hook.** It is not in our fork. It is small: a no-op default, and RelativeAxisLoop implements it.
5. **Item 11 B, take it or not.** If taken: S146, the S105 amendment, and the OSC exclusion and modules-layer read (not upstream's literal code).

No conflict was found with:
- the input thread (cache only on the input thread);
- the claim gate (kept through `gremlin/modules/inputs`);
- Undo and History (refused moves change nothing);
- the Library (S47 kept).

## Effort

| Part | Effort | Source in timings.md |
|---|---|---|
| Agents, in parallel (items 2 and 5; 9 split in two; 11 A and B) | ~10 min | a batch of parallel agents |
| Lead checks and map | ~5 min | rules of thumb |
| Quick tests and commit | ~2-5 min | rules of thumb |
| CI | ~25 min | CI on a push |
| Build, install and live test (standing rule) | no timing data yet; rough guess 10 min | none |

## Clock

Start 17:45, end 17:50 (2026-11-23).
