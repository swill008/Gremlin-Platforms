# System maps (for approval, 6 Oct)

Three shared systems behind most repeat bugs. Each: today, problems, one-owner design, migration steps, verification, decisions, size. No code until approved.

Mapped against code at a1459e22 (audit 3). Line numbers drift as code changes: re-check them when a step starts.

## The plan (stages, agreed 2026-10-06)

**Stage 0 – Know the program (in progress).**
1. *Program map*: one page per subsystem in `claude/program-map/` (what it owns, entry points, data, threads, callers, where it breaks the layer or single-owner rules). Read-only; no code changes.
2. *Behaviour spec*: in the same pages, "It should ..." statements gathered from help, glossary, test plan, tracker and code; unclear or contradictory ones are questions for the user. The user reviews each subsystem's list; confirmed statements are the definition of correct.
3. *Gap list*: where the code differs from the spec, or nothing owns something. Replaces open-ended audits.

**Stage 1 – Safety net** (before any redesign): CI on every push (full suite in random order, lint, no new pyright errors against the baseline); about 10 journey tests written from the spec; `validate()` rule checks after save, load and Stop (report-only at first); `claude/decisions.md` decision record.

**Stage 2 – Redesigns, one at a time** (Run lifecycle, module files, actions; maps below): tests that lock in today's behaviour first, then the new owner with its guard test, the giant files' code moved into it, its rule checks switched from report to fail. Every bug starts as a failing test.

**Stage 3 – Ongoing**: small changes, merged only when journeys, rule checks and guard tests pass; a release checklist with the user's hands-on check; audits become "run the checks, add a journey".

## Status

| System | Map | Approved | Built | Open tracker items it closes |
|---|---|---|---|---|
| 3. Run lifecycle (do first) | below | not yet | no | AU-116, AU-117 |
| 1. Module files (second) | below | not yet | no | AU-64 (what is left of it) |
| 2. Actions (third) | below | not yet | no | AU-118, shared Merge Axis split |

## Decisions (record the user's answer here)

| # | Question | Recommended | User's answer |
|---|---|---|---|
| F1 | Device Pack import onto a damaged module file | Refuse; point to Start Fresh | |
| F2 | Home card positions keyed by device name | Keep by name | As recommended (2026-10-06, page 03 review) |
| F3 | History entry for Start Fresh | Yes | As recommended (2026-10-06, page 03 review) |
| F4 | Twin sticks always looked up by id | Yes; log when missing | As recommended (2026-10-06, page 03 review) |
| A1 | OK on a shared action | Change it for every input using it; "Shared with ..." note | As recommended (2026-10-06, page 05 review) |
| A2 | Undo / History of a shared action | Restore for every input using it | |
| A3 | Device Pack failing partway | Undo everything it did | |
| A4 | Picking a shared action in the pane | Edit a copy until OK | As recommended, incl. Merge Axis Reuse (2026-10-06, page 05 review) |
| R1 | Logical Device values at Stop | Back to neutral | As recommended (2026-10-06, page 06 review) |
| R2 | Release callbacks waiting at Stop | Drop them | As recommended (2026-10-06, page 06 review) |
| R3 | Mode at the next Run | Start mode, temporary modes cleared | As recommended (2026-10-06, page 06 review) |
| R4 | Releasing keys scripts send | Only those sent during a Run | As recommended (2026-10-06, page 06 review) |

## How we work (lessons from audits 2 and 3)

Quick patches in one place kept breaking neighbouring paths, so every step of these plans follows this:

1. **Trace first, no code.** For each function: every entry point (QML action, file load, Run, import, Undo, History), every caller (grep, not guessed), the state it reads and writes, and everything downstream (save, reload, Run, History, what the screen refreshes). Write it to a trace note.
2. **Fix at the shared root.** One owner used by every caller; every caller in the trace is covered or explained. No per-symptom patches.
3. **Tests drive the real path** (user action -> save -> reload/Run), not a helper alone. Every new test must fail on the old code (check by stashing the source, keeping the test files; never delete the untracked test files).
4. **Independent re-trace.** A different agent re-traces each fix and checks every caller of every changed function. Gaps it finds are fixed and re-traced the same way.
5. **Build in a batch, test after.** Parallel agents each own their files; agents never run git write commands. Then one combined check: old-code check, lint vs HEAD (ruff, pyright, qmllint), one full run.
6. **Full runs re-split the 6 parts each time**, so a test that leaks shared state shows up as an order-dependent failure. Read the error and find the leak; don't rerun until green. Seen so far: patching a method on the shared settings instance (patch the class), deleting a shared singleton (reset it instead), assuming a key name's case.
7. **Wait for results, not fixed times**, in tests (a fixed short wait fails on a busy PC).
8. **Behaviour changes go to the user** with a recommendation before coding.
9. **Safety:** off-screen only (now enforced by `running_offscreen()`: no hooks, no native boxes, no process kills, no HidHide off-screen); temp USERPROFILE and GREMLIN_OFFLINE=1; never the user's data folder (one check script once used it and cleared logs\logs.txt).
10. **Editing:** use the Edit/Write tools for code with backslashes (shell heredocs mangle `\n`); keep each file's line endings.

---

# 1. Module files
## Module file ownership

### 1. Today

**A. Which file belongs to a device**

| Place | What it does | Disagrees? |
|---|---|---|
| `registry.py:resolve_module_slug:233` | The rule: saved binding, then the file bound to this id, then the binding by name, then the device's own name. A blank guid is filled from `_guid_for_name`. | This is the reference |
| `registry.py:for_device:397` | Returns the `Module` at that path. Used by runtime `_bind_live_physical:128` and calibration `_source_modules:64`. | Agrees |
| `hardware_profile.py:_active_module_path:955` / `module_json_path:319` | Filters a stale guid first (`guid_for_module`). Used by delete, pack, Output View, `moduleFileFor`. | Agrees |
| `HardwareProfile._module_slug:1755` / `_file_for:1763` | Filters the guid in its own way (`_guid_for_this_device`). Used by the Button Map load, save, photo, stash and recovery. | **Different guid filter** |
| `module_model.py:_load_module_doc:378`, `_module_damage:491`, `saveClaim:2245`, `startFresh:1451`, `_source_claim_for:1505` | Call `resolve_module_slug` with the raw guid and no filter. | **A stale guid is not filtered** |
| `module_model.py:module_exists:504`, `_refresh_inplace:1343-1347`, `claimedCount:1303`, `module_pairing.py:32,39`, `module_inputs.py:147` | Look up by name only (no guid). | **Twin sticks: the name gives the first twin's id, so twin 2 reads twin 1's file** |
| `hardware_profile.py:import_module_file:700` | Writes to `_slug(name).json`, not the file the device uses. | **A renamed stick gets a second file** |
| `device_initialization.py:_file_bound_guid:51` | Uses `plain_slug(name).json`. | Own-name rule, used for twin naming at startup |
| `calibration.py:_source_modules` | Keyed by slug; a second stick on the same file is skipped. | Only partly agrees |

**B. Writers** (History is hooked into each writer separately)
- `module_file.write_text` / `write_json`. Atomic, and calls `history_modules.note_write`. Callers: `saveClaim`, `saveViewConfig:796`, `saveCatalogConfig:894`, `HardwareProfile.save:2350` / `saveUi:2383` / `copyImage:2465` / `restorePhoto:2574`, `calibration.write_axes:177`, `auto_map:137`, `history_model._restore_module:284`. It also writes profiles and config, which are not module files.
- `hardware_profile._replace_file:592`. A second atomic writer that calls History itself. Callers: import, `undo_last_import`, `device_pack._write_module:1652`, `_put_back:1566`, `undo_import:1587`, picture backups at :1160.
- `device_pack._write_pictures:1161`: `dest.write_bytes`, **not atomic**.
- `apply_zip:1794` reads the existing file with `_read_json_dict`. A damaged file comes back as None and is **overwritten** (a backup is kept). Every other writer refuses with `ModuleFileDamaged`.

**C. Deletes and moves**
- These use `history_modules.deleting`: `delete_module_file:883`, `_delete_own_module_files:1083`, `undo_last_import:675`, `device_pack.undo_import:1584`.
- **No History:** `module_file.start_fresh` (`os.replace`), `device_pack._put_back:1564` (unlink).
- Pictures are deleted directly: `_delete_own_module_files` (rmtree plus `*_photo.*`), `clearImage:2477`, `restorePhoto:2555`, `copyImage:2445`.

**D. Binding store** (config `module-file-bindings`)
- Read: `registry._binding_store`.
- Written: `hardware_profile._write_bindings` through `bind_module_file:817`, `_clear_bindings_to:617`, `_clear_device_binding:801`, `_clear_device_binding_keys:1060` (a **duplicate** of the one before it), `delete_module_file:889`, `undo_last_import`.

**Remaining direct slug and path building**
- `_slug(name)`:
  - `hardware_profile` :345, :700, :957, :1761
  - `module_model` :1432, :1585, :1660 (card keys)
  - `device_pack` :574 (pack label)
  - `module_pairing` :51
  - Fine as they are (no change needed): the export name :1864, the stock-photo checks :2629-2642, and device matching `module_model` :2081.
- `plain_slug` used to build paths or compare bindings:
  - `device_initialization` :51
  - `hardware_profile` :577, :619, :855, :891
  - `auto_map` :51
- `_maps_dir()/f"{slug}.json"` or `/slug`:
  - `module_model` :380, :492, :505, :875, :1452, :1505, :2287
  - `hardware_profile` :701, :957, :1074-1093, :1764, :1767, :2440, :2457, :2479-2486, :2511-2563, :2617
  - `device_pack` :1138
  - `registry` :399
  - `history_model` :272

### 2. Problems this causes
- Twin sticks: after `notifyClaims`, twin 2's Home card can show twin 1's counts. The same happens in module pairing and module inputs. This is a suspected bug; a test will confirm it. It is the same family as the twin fixes in audit 3 W1 and `test_twin_devices`.
- A stale guid sends Module Setup Save (`saveClaim`) and Start Fresh to a different file than Delete or the Device Pack. This is AU-04 and AU-22 coming back by another route.
- Import into a renamed stick writes a new own-name file; the old bound file stays. This is the AU-04 pattern.
- A Device Pack import silently replaces a damaged module file. Every other save refuses, so this breaks the AU-03 rule ("never treat a damaged file as empty").
- Start Fresh and a failed import's rollback leave no History entry. This is a gap in the AU-21 and W5 History fixes.
- A crash mid-write can leave a half-written picture (`_write_pictures`).
- Every audit has had to fix the same rule in 3 to 6 places (AU-04, AU-22, AU-08, W1).

### 3. Proposed design
**One owner:** `gremlin/modules/store.py`. `registry.py` stays the read-only index of module files and the home of `resolve_module_slug`. `module_file.py` stays the generic atomic writer, without History.

| API | Meaning |
|---|---|
| `slug_for(name, guid="") -> str` | The rule: `guid_for_module` filter, then `resolve_module_slug`, else `"device"`. |
| `path_for(name, guid="") -> Path` | `<modules>/<slug>.json` |
| `pictures_dir(name, guid="") -> Path` | `<modules>/<slug>/` |
| `read(name, guid="") -> dict` | `{}` when the file is missing or damaged. |
| `damage(name, guid="") -> str` | Why the file can't be read, or `""`. |
| `update(name, guid, change: Callable[[dict], None], who: str) -> bool` | `load_for_update`, refuse a damaged file and report it, run `change`, `write_json`, trace. |
| `replace(path: Path, data: bytes, who) -> None` | Whole-file write for import, pack, undo and restore. Refuses a damaged target unless `force=True`. |
| `put_picture(name, guid, src: Path\|bytes, as_name) -> str` | Atomic picture write; returns the ref. |
| `remove_pictures(name, guid, pattern="photo.*") -> bool` | Deletes matching pictures (`photo.*` by default). |
| `delete(name, guid, keep_copy=True) -> str` | Copies to deleted devices, deletes the file, pictures and legacy photos, and clears bindings. Refuses when the file is shared. |
| `move_aside(name, guid) -> Path` | Start Fresh. |
| `bind(name, guid, slug)` / `unbind(name, guid)` / `unbind_file(slug)` | The binding store. |

**Rules it enforces:**
- One lookup rule.
- A guid is never used without the filter.
- Name-only lookups are allowed only for vJoy, Keyboard and OSC.
- Damaged files are always refused.
- Every write and delete is atomic.
- History is hooked here only: `_write` calls `note_write`, `_delete` and `move_aside` go through `deleting`. `module_file.write_text` and `_replace_file` lose their History calls.

**What callers do:** they pass `(name, guid)` and never build paths. Module Setup, the Button Map, calibration and auto_map use `update`. Import, Pack, Undo and History Restore use `replace`. Delete File, Delete Device and Start Fresh use `delete` or `move_aside`. Runtime keeps `registry.for_device`, which becomes `registry.find_path(store.path_for(...))`.

### 4. Migration list (each step leaves the program working)
1. Add `store.py` with the lookup functions only, plus tests. No callers change.
2. Readers move to the store:
   - `_load_module_doc`, `_module_damage`, `module_exists` (now taking a guid)
   - `_refresh_inplace`, `claimedCount`, `_source_claim_for`, `_dest_target`
   - `module_json_path` and `_active_module_path` become aliases
   - `HardwareProfile._module_slug` / `_file_for` / `_profile_dir` / `_photo_files` / `_stash_dir` / `_recovery_file`
   - `module_pairing`, `module_inputs`, `logical_layout`, `chips_for_guid`, `registry.for_device`
3. Updates move to `store.update`:
   - `saveClaim`, `saveViewConfig`, `saveCatalogConfig`
   - Button Map `save` / `saveUi` / `copyImage` / `restorePhoto`
   - `calibration.write_axes`, `auto_map.merge_claim_into_output`
4. Whole-file writes move to `store.replace` and `put_picture`:
   - `import_module_file` (dest becomes `path_for`), `undo_last_import`
   - `device_pack._write_module` / `_write_pictures` / `_put_back` / `undo_import`
   - `history_model._restore_module`
5. Deletes move to the store:
   - `delete_module_file`, `_delete_own_module_files`, `delete_device`
   - `startFresh`, `clearImage`
6. Bindings move to the store: `bind_module_file`, `_clear_*` (the duplicate is removed), `_write_bindings`.
7. History is hooked into the store only. Remove the History calls from `module_file.write_text` and `_replace_file`.

### 5. How it will be verified
- **Save paths** (Module Setup Save, Button Map Save/Photo/Cancel, Output View Appearance, Calibrate, Auto Mapper): user action, then the file at `store.path_for`, then a History entry, then Run claims (`ModuleGate.reload`). Run each for a normal stick, a **renamed stick**, **twins**, a **stale guid** and a vJoy.
- Import and Device Pack, each with Undo: the same file is written, the backup is in `imported`, a damaged target is refused, and the file and its History entries are restored.
- Delete File, Delete Device, Start Fresh: the copy is kept, the pictures are gone, the bindings are cleared, and there is one History entry.
- Twin card counts survive `notifyClaims`.
- **Guard test** `test_module_store_only.py`: greps `gremlin/` outside `store.py`, `registry.py` and an allow-list (export name, stock photo) for:
  - `plain_slug(`, `_slug(`, `modules_dir() / f"`, `_maps_dir() / f"`
  - `history_modules.note_write`, `deleting(`
  - `module_file.write_` used on module paths

  It fails if any appear.
- Run `test_twin_devices`, `test_audit3_module_files`, `test_module_lookup_device_first`, `test_device_pack_import`, then the full `test/run_tests.py`.

### 6. Decisions for you
1. **A Device Pack import into a damaged file:** refuse it and point to Start Fresh, or replace it as today (a backup is kept)? **I recommend refusing**, the same as every other save.
2. **Card key** (card order, hidden, sizes) stays the device's own name slug, separate from the file slug. **I recommend keeping it**: changing it would reset everyone's card layout. It would get its own named function, `store.card_key(name)`.
3. **Start Fresh in History:** should it get an entry? **I recommend yes.**
4. **Name-only lookups:** should twin sticks be required to pass a guid, with a logged error when one is missing? **I recommend yes.**

### 7. Size
- About 13 files and 55 to 60 call sites; `hardware_profile.py` and `module_model.py` hold about 70% of them.
- One new module (about 200 lines) and two new tests.
- Risk is medium. The lookup rule itself doesn't change; the risk is in the import, pack and undo byte paths, and in the History hook moving (entries could be doubled or missed). Steps 4 and 7 need the most care.

---

# 2. Actions
## Who owns an action object

## 1. Today

**Making copies (pane drafts)**
| Where | Reads / writes | Called by |
|---|---|---|
| `profile.py:Library.clone_action:378` | copies the action and every action inside it under new ids; adds them to the library; `draft=True` records copy→original in `_copied_from` | `binding_catalog._clone_action:41` → `_clone_binding:51` (catalog `beginPane:1138`, `_retarget_draft:1106`; logical `_begin_pane:1295`, `_show_saved:1425`); `reference.duplicateAction:114` |
| `Library.pick_list:422` | lists drafts and in-use actions, hides originals | Merge Axis, Deadzone and Reference lists |
| `merge_axis._set_merge_action:236`, `dual_axis._set_deadzone:178`, `reference._replace_reference:119` | put the picked **live** library action into the draft | the pick lists |

- ✗ `clone_action` also copies an action another input uses. OK then gives this input the copy, and the shared original stays on the other input.
- ✗ `pick_list` changes `_copied_from` from inside a list getter.
- ✗ Picking a shared action in the pane puts the live object into the draft. Edits then reach the profile before OK, and Cancel does not undo them. This is likely; a test still has to confirm it.

**Writing a draft back (OK)**
- `binding_catalog._attach_binding:138` and `_replace_sequences:1125`, plus the logical copy `logical_layout._replace_sequences:1343`, move the draft bindings onto the real input and call `remove_unused` on the old roots.

**Removing actions: two rules**
| Where | Rule |
|---|---|
| `Library.remove_unused:498` / `_remove_unused:547` | keeps an action if an input uses it, or if **any** library action holds it, even a dead or draft one |
| `Profile.drop_unused_actions:1201`, `drop_inputs:1174` | keeps an action only if an input uses it |

Callers of `remove_unused`:
- `_drop_shadow:71`
- both `_replace_sequences`, `_attach_binding`
- `logical._remove_link:536/539`, `_detach_links:554/560`
- `ui/profile.remove_action:478`, `_set_behavior:631`
- `reference._replace_reference:126`
- `hardware_profile._drop_binding_tree:1009`

Callers of `drop_unused_actions`:
- `catalog.removeSequence:940`
- `logical.deleteAction:826`
- `ui/profile.deleteActionSequnce:704`
- `auto_mapper:149`
- `device_pack.drop_import_undo:1556`, `undo_import:1607`
- `drop_inputs` (Delete Mode, Keyboard, OSC)

- ✗ The two rules give different answers for the same action.
- ✗ `hardware_profile._drop_inputs:1014` writes its own loop and skips `drop_inputs`.

**What "in use" means**
- `Profile.actions_in_use:1183` walks the profile's inputs.
- `Library.used_elsewhere:508`, `_used_by_inputs:538`, `actions_in_use_by_type:726` and `pick_list` instead look up `shared_state.current_profile`.
- ✗ For a library that isn't the open profile's, "in use" is empty, so actions an input uses can be removed.

**Creating actions**
- `plugin_manager.create_instance:148` always adds to `current_profile.library`, not to the library of the input being edited.
- `newMergeAxis:301` and `newDeadzone:139` call `add_action` directly.

**Undo / Redo / History**
- `Profile.input_snapshot:1091` writes the input as XML.
- `put_input:1126` checks the copy with `_check_snapshot:1509`, then calls `drop_inputs` and `add_inputs(remap=False)`.
- Callers: catalog `_snapshot:961`, `_step:968`, `_play:1026`; logical `_snapshot:279`, `_play:283`, `_replay:303`; `history_model._restore_input:219`.
- ✗ `put_input` skips an action another input still uses, so the shared action's saved content is never put back.

**Device Pack**
- `device_pack._apply_wires:1441` takes the device's inputs out of the profile, then calls `add_inputs:1058` (`Library.from_xml` + inputs). It also creates modes and Logical Device inputs before that.
- ✗ It isn't all-or-nothing (details in section 2).

**Save / load**
- `Profile.to_xml:904` calls `drop_invalid_actions:702`, which edits every library action, drafts included.
- `_xml_text` → `Library.to_xml(used):739` writes only the actions an input uses.
- `from_xml:862` loads the file.
- ✗ Saving with the pane open may strip an unfinished child out of the open draft. Possible; not tested.

## 2. Problems this causes
| Failure the user sees | Item |
|---|---|
| OK on a Merge Axis or Deadzone used by two axes splits them: one axis gets the edited copy, the other keeps the old settings, and both drive the output differently. `test_audit3_actions_undo.py:493` asserts the split today | open issue |
| Undo or History Restore of a shared action doesn't bring its old settings back | follows from `put_input` |
| Device Pack failing during `add_inputs`: the device's old inputs have already left the profile, the new modes, Logical Device inputs and part of the actions stay, and Undo Import has nothing to undo | AU-118 |
| Picking a shared action in the pane, editing it, then Cancel: the edit stays | likely |
| Unused actions stay in memory because a dead action still holds them (the save filter hides it) | follows from `remove_unused` |
| Device Delete on the module page skips the shared removal rule | `hardware_profile` |

## 3. Proposed design
The **profile's `Library`** becomes the one owner. It is tied to its own profile (`Library(profile)`), so "in use" is always worked out from its own inputs.

| API | Meaning |
|---|---|
| `in_use() -> set[UUID]` | actions reachable from the profile's inputs (moved from `Profile`) |
| `users(action) -> list[InputItem]` | the inputs that use this action |
| `create(name, behavior) -> Action` | the only way a new action is added |
| `draft(item, index=None) -> Draft` | pane copy; `Draft` holds the copy→original map (replaces `_copied_from`) |
| `Draft.adopt(action) -> Action` | a picked live action enters the pane as a copy |
| `commit(draft, real, index=None) -> int` | writes the draft onto the input; a **shared** original gets the copy's content in place and keeps its id |
| `discard(draft)` | throws the draft away |
| `release(roots)` | the one removal: anything no input uses and no used action holds |
| `snapshot(item) / restore(key, snap)` | Undo and History (moved from `Profile`); a shared action is put back in place |
| `with change() as c:` | all-or-nothing change: records added actions, inputs, modes and Logical Device inputs; puts them all back on an error |
| `prune_for_save()` | `drop_invalid_actions`, limited to `in_use()` and never touching drafts |

**Rules it enforces:**
1. Only the library adds or removes actions.
2. Drafts never count as users and never hold a live action.
3. OK keeps shared actions shared.
4. There is one removal rule.
5. Multi-step changes are all-or-nothing.

**What each caller does instead:**
- Panes call `draft`, `commit` and `discard`.
- Removers call `release`.
- Undo and History call `snapshot` and `restore`.
- The Device Pack and `add_inputs` run inside `change()`.

## 4. Migration (each step leaves the program working)
1. **Tie the library to its profile.** Add `in_use`/`users`. Change `pick_list`, `used_elsewhere`, `_used_by_inputs`, `actions_in_use_by_type` and `Profile.actions_in_use` to use them.
2. **One removal rule.** Add `release`, and make `remove_unused` and `drop_unused_actions` call it. Move every caller listed in section 1 over, then delete the old two.
3. **Drafts.** `draft`, `discard` and `adopt` go into catalog `beginPane`/`_retarget_draft`/`discardPane`/`endPane` and logical `_begin_pane`/`_show_saved`/`discardPane`/`endPane`, plus `merge_axis`, `dual_axis` and `reference`. Delete `_clone_action`, `_clone_binding`, `_drop_shadow` and `_copied_from`.
4. **`commit`, with shared actions kept shared.** It replaces `_attach_binding` and both `_replace_sequences`. Update test line 493.
5. **Undo and History.** `snapshot`/`restore` replace `input_snapshot`/`put_input`/`_check_snapshot` in catalog `_snapshot`/`_step`/`_play`, logical `_snapshot`/`_play`/`_replay` and `history_model._restore_input`.
6. **All-or-nothing changes.** `change()` goes into `add_inputs` and `device_pack._apply_wires` (fixes AU-118).
7. **Creating actions.** `create` replaces `plugin_manager.create_instance:148`, `newMergeAxis` and `newDeadzone`.
8. **Save.** `prune_for_save` replaces the call in `Profile.to_xml`.
9. **Guard test** (section 5).

## 5. Verification
- Edit a shared Merge Axis in input A's pane, then OK → B uses the same action with the new settings → save and reload → Run: both axes drive one merge.
- Same edit, then Undo → both inputs back to the old settings. Repeat through Tools > History Restore Before.
- Pick a shared action in the pane, edit it, Cancel → the profile is unchanged.
- Device Pack with `add_inputs` forced to fail → inputs, modes, Logical Device inputs and library are as before, and the earlier Undo Import is kept.
- Delete on the catalog, Logical Device, Keyboard, OSC and Device Delete → nothing still used is removed, and no orphan is left in memory.
- Save with the pane open → the draft is untouched and the file holds only used actions.
- Run all existing `test_audit*`, `test_catalog_undo`, `test_logical_layout`, `test_profile_unused_actions` and `test_device_pack_import` tests.
- **Guard test:** greps the code outside the library for `add_action(`, `delete_action(`, `remove_unused(`, `drop_unused_actions(`, `clone_action(`, `_copied_from`, `.inputs[...] =` and `library.from_xml(`, and fails on any hit.

## 6. Decisions for you
1. **OK on a shared action:** (a) change it for every input that uses it, (b) ask each time, or (c) keep the split. I recommend **(a)**, with a "Shared with …" note in the pane. Reference > Duplicate already makes a separate copy when you want one.
2. **Undo or History of a shared action:** put its old settings back for every input (recommended, so it matches OK), or only for this input.
3. **Device Pack failure:** undo everything it did (recommended), or keep the partial result and offer Undo Import for it.
4. **Picking a shared action in the pane:** edit a copy until OK (recommended).

## 7. Size
About 14 files and 45 functions: profile, base_classes, plugin_manager, binding_catalog, logical_layout, ui/profile, merge_axis, dual_axis, reference, history_model, device_pack, hardware_profile, auto_mapper, plus about 6 tests. Risk is medium to high: this is the core of the profile data. The order above keeps steps 1–2 safe on their own; steps 3–4 carry the risk.


---

# 3. Run lifecycle
## What a Run starts and Stop must release

## 1. Today

| # | Where | Reads / writes | Called by |
|---|---|---|---|
| A | `code_runner.py:_next_run_number` 291, `run_number` 286 | global `_run_number`, increased at start and stop | `CodeRunner.start` 313, `stop` 402, `map_to_logical_device._start_loop` 147 |
| B | `code_runner.py:CodeRunner.start` 312 | connects input signals, then starts periodic_registry, MacroManager, Audio, TTS, MouseController, OSC (each one's own `start()`) | `ui/backend.py:activate_gremlin` 420 |
| C | `code_runner.py:CodeRunner.stop` 400 | stops in a fixed order: number, disconnect, runtime_active, scripts, OSC, `flush_pulses`, macros, mouse, audio, TTS, `reset_drivers` | backend 425, `joystick_gremlin.py:shutdown_cleanup` 266 |
| D | `code_runner.py:_reset_state` 440 | `ButtonReleaseActions().reset()`. **Disagrees:** runs at start only, so release callbacks waiting at Stop survive until the next Run | start |
| E | `macro.py:MacroManager` 73 | has its own `_run` counter (**disagrees with A**: a second number), `_stopped`, `_step_lock`; `stop` 130 → `_release_held` 152 → `release_held_keys` 61 + `sendinput.release_held_buttons` | C |
| F | `macro.py:KeyAction` 709-716 | records keys in `_held_keys`. **Disagrees:** a macro that ends early (`_steps` returns False) leaves its key down until Stop | macro threads |
| G | `sendinput.py:_note_button`/`release_held_buttons` 441-460 | `_held_buttons` (a second held-output list) | `mouse_press`/`mouse_release`, E |
| H | `keyboard.py:send_key_down/up` 217 | sends keys with no tracking. **Disagrees:** keys a script sends are never released at Stop | macro, user scripts |
| I | `base_classes.py:_pending_pulses`/`flush_pulses` 546, `_pulse_event` 612 | uses `QTimer.singleShot(50)` directly, with its own list. Off the main thread it uses `time.sleep(0.05)` (**breaks the gremlin.clock rule**) | Tempo short pulse, others |
| J | `threads.main_timer` users: `tempo:_start_timer` 172, `double_tap:_start_timer` 189, `smart_toggle:_start_timer` 82 | `self.timer`. **Disagrees:** never cancelled at Stop; it fires after Stop and writes output (reopens vJoy) | FSM press |
| K | `map_to_vjoy:relative_axis_thread` 158 | stops only when `vjoy_owned` is False. **Disagrees with L:** no Run check | `_start_loop` 129 |
| L | `map_to_logical_device:relative_axis_thread` 169 | checks `code_runner.run_number()` (correct) | `_start_loop` 130 |
| M | `user_script.py:PeriodicRegistry` 128-175 | its own `_generation` (a third Run counter) | B, C |
| N | `sendinput.MouseController.stop` 356, `AudioPlayer.stop`, `TTSManager.stop`, `OscRuntime.stop` | each stops itself | C, and again in `shutdown_cleanup` |
| O | `logical_device.py` Input `_value` | **Disagrees:** never set back to neutral at Stop (`reset()` 237 clears the whole device, called only by profile load) | — |
| P | `mode_manager.ModeManager._mode_stack` | not reset at Stop; start just calls `switch_to` | B |
| Q | `joystick_gremlin.py:shutdown_cleanup` 240 | calls `runner.stop()`, then calls `reset_drivers`, audio, TTS and OSC a second time | aboutToQuit, main |
| R | OSC runtime (parked) | `OscRuntime.start/stop`, `osc.py:496 singleShot` | listed only |

## 2. Problems this causes

| What the user sees | Cause | Item |
|---|---|---|
| A Tempo long press, Double Tap or Smart Toggle fires after Stop, and the vJoy device shows as taken again | J | AU-116 |
| A key stays down after a Hold or Count macro ends early, until Stop | F | AU-117 |
| Stop then Run quickly: the relative axis keeps moving in the new Run | K | AU-117 |
| A key a script pressed stays down after Stop | H | AU-117 |
| Logical Device axes and buttons start the next Run at their old values | O | AU-117 |
| A button release from the previous Run fires in the new one | D | — |
| Three separate Run counters (A, E, M) can disagree | — | — |

## 3. Proposed design

There is one owner: a new **`gremlin/run_scope.py`** (module functions, main thread, locks with timeouts). It replaces A and absorbs the held-output lists in E and G.

```python
number() -> int                         # the current Run (replaces code_runner.run_number)
alive(run: int) -> bool                 # False once that Run has stopped
on_stop(stage: Stage, name: str, fn) -> Handle   # fn runs at Stop; Handle.drop() removes it
timer(name, seconds, fn, *args, at_stop="cancel"|"fire") -> Handle
                                        # threads.main_timer; at Stop it is cancelled or fired now
loop(name, fn, *args) -> Thread         # threads.start; fn gets run and checks alive(run)
hold(owner, kind, ident, release_fn)    # an output is now held (key, mouse button)
let_go(owner, kind, ident)              # it was released normally
release_owner(owner)                    # release what one macro or script still holds
begin() / stop()                        # only CodeRunner calls these; stop() can be called twice safely
```

**Stop order** (`Stage` enum). Each stage runs everything registered in it, catches errors, and has a time limit.
1. **CUT_INPUT**: new number, disconnect input, mode listening off, `runtime_active` False, flush last modes.
2. **CANCEL**: cancel timers, clear ButtonReleaseActions, stop the periodic registry and OSC.
3. **FIRE_PENDING**: fire the `at_stop="fire"` timers (the pulse releases).
4. **END_WORK**: MacroManager.stop (no key release in it), MouseController.stop, loops end through `alive`.
5. **RELEASE_HELD**: release everything still held, last pressed first.
6. **NEUTRAL**: Logical Device values back to neutral, mode stack reset, audio and TTS stop.
7. **DRIVERS**: `output.reset_drivers()`.

**Rules:** nothing that belongs to a Run starts without registering; nothing runs after its Run has stopped; Stop is the same whether it comes from the button or from quitting.

## 4. Migration (the program works after each step)

1. Add `run_scope.py` with `number`, `alive`, `begin`, `stop`, `on_stop` and the stages. `CodeRunner.start/stop` call it, and `code_runner.run_number` forwards to it. No change in behaviour.
2. Move the existing `CodeRunner.stop` steps into `on_stop` registrations in `CodeRunner.start` (same order). `shutdown_cleanup` keeps only the work outside a Run (listener, process monitor), plus a final `reset_drivers`.
3. Timers: `tempo`, `double_tap` and `smart_toggle` `_start_timer` use `run_scope.timer` (fixes AU-116). `base_classes._pulse_event` uses `timer(at_stop="fire")`; remove `_pending_pulses`/`flush_pulses` and replace the `time.sleep` with `clock.sleep`.
4. Loops: `map_to_vjoy` and `map_to_logical_device` use `run_scope.loop` and `alive(run)`.
5. Held outputs: `macro.KeyAction`, `sendinput._note_button` and `keyboard.send_key_down/up` call `hold`/`let_go`. `MacroManager._finish_macro` calls `release_owner(macro)` when the macro ended early. Remove `_held_keys` and `_held_buttons`.
6. Counters: `MacroManager._run` and `PeriodicRegistry._generation` read `run_scope.number()`.
7. NEUTRAL stage: add `LogicalDevice.reset_values()`, `ButtonReleaseActions.reset()` at Stop, and `ModeManager` stack reset.

## 5. Verification

- One test per path: press → Stop before the timer → no output and vJoy free (Tempo, Double Tap, Smart Toggle). Hold macro released partway → key up. Script `send_key_down` → Stop → key up. Relative axis, then Stop and Run within 5 ms → loop gone. Logical axis 0.7 → Stop and Run → 0. Pulse pending at Stop → release sent before the drivers are reset. Quit while running → each `on_stop` runs exactly once.
- Order test: record the stage order and compare it with the list above.
- Bypass test (a grep test): outside `run_scope.py`, no `threads.main_timer(`, no `QTimer.singleShot` in `base_classes`/`action_plugins`, no `_next_run_number`, no `threads.start(` in `action_plugins`, and `send_key_down` only in `keyboard.py`/`run_scope.py`.
- Existing tests: `test_audit3_run_stop.py`, `test_audit2_macros.py`, then the full `run_tests.py`.

## 6. Decisions for you

1. **Logical Device values at Stop**: set to neutral (axis 0, button up, hat centre), or keep them? I recommend **neutral**.
2. **Release callbacks waiting at Stop**: drop them, or fire them? I recommend **drop**, since the held-output release and `reset_drivers` already let go of what they pressed.
3. **Mode at the next Run**: always the start mode with the temporary-mode stack cleared? I recommend **yes**.
4. **Script keys**: track all of them, or only while a Run is on? I recommend **only during a Run**.

## 7. Size

About 16 files and 35 functions: run_scope (new), code_runner, macro, sendinput, keyboard, base_classes, tempo, double_tap, smart_toggle, map_to_vjoy, map_to_logical_device, logical_device, event_helpers, user_script, mode_manager, joystick_gremlin, plus 1 new test file. Risk is medium. Steps 2 and 5 carry most of it, because they change the Stop order and the key release that macros rely on.