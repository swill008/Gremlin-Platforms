# Upstream since the fork, part 1: first 75 commits (ST-UP1)

Study agent ST-UP1, 2026-11-23, 17:31-17:37. Read-only study; nothing in the
program was changed.

Range: the first 75 commits of
`git log --reverse $(git merge-base HEAD upstream/develop)..upstream/develop`
(merge base daf4057f), from 379bcdb5 (2026-09-07) to 381ff687 (2026-09-25).
Some commits are dated July and August 2026 because they were on upstream's
"Kobold style" branch, which was merged after our fork. Part 2 (the rest) is
ST-UP2's; the script interface in depth is ST-SCRIPT's.

Every "ours" entry was checked against our files with grep or by reading the
code (paths given). "Likely gap" means the code differs and the bug looks real,
but no failing test was run. Change control applies before anything is taken:
start with a failing test, and ask the user first if it changes a spec
statement.

## Summary

- **Most of upstream's bug fixes in this range are already in our code.**
  Several were taken earlier, word for word or near it: spline drift
  (123ab4f2), keyboard script variable (e65e2968), natural sort (58499ab9),
  the 437451b6 action fixes, mouse motion and mode-change registry (8db9d0f9,
  bf034739), startup mode (381ff687), Merge Axis operations. Others we fixed in
  our own way: keeping the input callbacks alive (78e2bc60), the deferred
  `inputItemChanged` (78e2bc60), the Hat Buttons count (7a928a63), and the
  first unused vJoy output (0d93b7e7).
- **Bug fixes we lack (3, all small):**
  1. Dragging an action onto its own child. Upstream's 86ea050c refuses to move
     a container into its own subtree (`can_move_action` /
     `_is_descendant_of`). Our `InputItemBindingModel.move_action`
     (`gremlin/ui/profile.py:389`) has no such check. `ActionModel.dropAction`
     (`gremlin/ui/action_model.py:324`) only rejects source == target. This is
     a likely gap: dropping a Chain or Condition onto one of its own children
     could detach or loop the tree.
  2. Qt properties without a getter (855eb31c, 2a773013): we still have two
     write-only properties. One is `LogicalDeviceSelectorModel.validTypes`
     (`gremlin/ui/device.py:535`), which QML reads through
     `property alias validTypes` in `qml/LogicalDeviceSelector.qml:22`. The
     other is `AxisCalibration.guid` (`gremlin/ui/device.py:1268`).
  3. Input names in `InputIdentifier.label` (32eebedc, carried on in
     d6e9b053): upstream uses `common.input_to_ui_string` and the device map's
     input name. Ours (`gremlin/ui/device.py:76-91`) builds
     "Type N" from the raw id, so a keyboard input would show its raw scan
     code, and named device inputs show as "Button 3". This is unverified:
     check where this label is shown before calling it a bug.
- **Features worth considering:**
  - The Reference action's pick list (d6e9b053). Each entry reads
    "[mode] device - input › action". Entries are sorted by mode, device and
    input, each action is listed once, and unbound actions come last. Ours
    shows only the action label (`action_plugins/reference/__init__.py:77-123`).
    This changes 05 S60's list, so it needs the user's approval.
  - Installer size (949f562e): upstream leaves out unused PySide6 QML modules
    (Qt3D, QtGraphs, QtWebEngine, Material, Fusion and others) and compares
    paths without regard to capitals. Our `joystick_gremlin.spec:201-220`
    leaves out only `Pythonwin` and `PySide6\translations`, and its
    comparison is case-sensitive. We import none of the modules upstream
    removes; QtCharts is not on their list, and we use it.
- **Not for us:** the Kobold style series, about 40 commits that build
  upstream's new UI under `style/qml/Kobold`. Our UI is a separate redesign
  (`qml/`, `theme/Gremlin`). Also not for us: upstream's central
  `config_registry.py` (it conflicts with our design-for-change rule that each
  piece declares its own options), the Python 3.14 / PySide6 6.11.2 move (a
  separate upgrade decision), and repo housekeeping (ruff, agent documents,
  webpage).

## Commit table

Effort figures come from claude/timings.md, kind "Agent fix / feature / docs" (3-8 min of
agent time per small fix, plus the batch's quick tests and commit). "n/a" means
nothing to take.

| Commit | Date | What | Ours | Take? | Why | Effort |
|---|---|---|---|---|---|---|
| 379bcdb5 | 09-07 | Minimize to system tray (new `gremlin/ui/system_tray.py`, win32) | Have: `gremlin/ui/system_tray.py` (own win32 tray, installer quit request 01 S173, X hides / Exit quits 01 Q2) | Already have | Ours goes further | n/a |
| f499984a | 09-08 | Tray: exception handling, duplicate events, one quit path (`quitGremlin`, `quitRequested`) | Have: tray exit and File > Exit share the quit path (`system_tray.py:237-239`) | Already have | — | n/a |
| d9b54c06 | 09-08 | Fixes to the tray merge; PySide6 >=6.11 | Tray: have. PySide pin: ours `>=6.8,<6.12` | No | Version pin is our own choice | n/a |
| b6bca1f9 | 09-08 | gh_pages workflow update | Own `.github/workflows/gh_pages.yml` | No | Webpage housekeeping | n/a |
| e722182a | 09-08 | Spelling fixes in gh_page changelog and docs | Not taken | Optional | Docs only; harmless | ~2 min |
| 144c6b5d, 582be92c, cc42ab4b, f129b75e, c2bef960 | 07-22 to 09-17 | Kobold style design documents and agent rules (added, then removed again in c2bef960) | n/a | No | Upstream planning documents; we have our own | n/a |
| d3fb588e, b8ebdc2c, e205b9ab, 5f4c8999, 27233050, 0a7bd6a6, 8efc3c5f, 067c68f9, 74ee0506, fe0b4d34, ca3ac081 | 07-22 to 08-02 | Kobold style phases 1-8: theme manager, icon provider, IBM Plex fonts, playground, left pane, shell, action tree, plugin QML rewrite, token renaming | Our UI is our own redesign (`qml/`, `theme/Gremlin`, glossary-driven text) | No | Would replace our UI; conflicts with every UI decision on the program map | n/a |
| 4dae898e | 07-23 | Proof of concept of the Map to vJoy QML in the new style | Own Map to vJoy editor through the output module | No | Kobold UI; layer rule | n/a |
| b2ce2258 | 08-02 | Saves window positions and sizes (`window_geometry.py`) | Have: `gremlin/ui/window_placement.py` | Already have | — | n/a |
| 2a773013 | 08-02 | Fixes sizes in the new style; adds getters to `deviceType` and `guid` | `deviceType` has a getter (`device.py:279`); `AxisCalibration.guid` (`device.py:1268`) is still write-only | Take the getter part | Qt warns about properties without a getter; QML can't read the value | 3-8 min (timings.md: agent fix / feature / docs), together with 855eb31c |
| 855eb31c | 08-03 | Qt properties missing required parameters: `constant=True` on `guid`, a getter for `validTypes` | `LogicalDeviceSelectorModel.validTypes` (`device.py:535`) is still write-only and is read through an alias in `LogicalDeviceSelector.qml:22` | **Take** (bug) | Same fix; ours lacks it | (with above) |
| 80634aa0, f0080aa1, df347773, b77230ff, dd66f997, 9a8d349a, 4210d58a, a4ac9c1a, ebe7f914, 6bb2eab6 | 08-03 to 09-16 | Kobold views: input capture button, Input Configuration, Options dialog, spacing, regenerated `resources.py`/qrc, gallery, theme schema rename | n/a | No | Kobold UI | n/a |
| e32ea926 | 08-03 | Fold state moved from `backend.isActionExpanded` to an `ActionModel.expanded` property (class-level dict) | We use `backend.isActionExpanded` (`qml/ActionNode.qml:151`) | No | Same behaviour; only a refactor | n/a |
| 6d80ea42 | 08-04 | Options: Action Sequence Ordering move uses row signals and bounds checks; ScrollColumn | Ours fixed differently (`gremlin/ui/option.py:798`: index correction, copy before edit, early return) | Already have | — | n/a |
| ac0ac996 | 08-04 | Text input dialog in Merge Axis and Deadzone; Enter accepts | Own rename flow (05 S120) | No | Kobold UI | n/a |
| 5fc3dd3b | 08-04 | Temporary fix for Response Curve QML warnings | Own Response Curve editor | No | Their QML | n/a |
| d6e3897e | 08-05 | Reworks a test (`test_action_icons.py`) | n/a | No | Their icon set | n/a |
| 18cccfd6 | 08-05 | Theme dropdown, zenburn theme | Own theme system (`theme/`) | No | Kobold themes | n/a |
| 9796b3c3 | 08-08 | UI refinements: per-action `chip_label`, `InputType.to_letter` | Our rows show bindings boxes (`bindingTargets`, 05 S142) | No | Our own design covers this | n/a |
| 86ea050c | 08-11 | Drag and drop in the main UI; `move_action(source, parent, container, position)`; refuses a move into the source's own subtree; fixes a C++ crash from a signal race | Ours has drag and drop (05 section 4) and a deferred `inputItemChanged`; **no subtree check** in `move_action` (`gremlin/ui/profile.py:389`) or `dropAction` (`action_model.py:324`) | **Adapt** the subtree check (likely bug) | Dropping a container onto its own child can detach or loop the tree; write a failing test first | 3-8 min (timings.md: agent fix / feature / docs) plus the test |
| 48d4ffba | 09-06 | Input viewer fix (HatView drawn with Shapes) | Own viewer | No | Kobold UI | n/a |
| 5aec37d3 | 09-16 | Python 3.14, PySide6 >=6.11.2, poetry.lock | Ours: Python 3.13, PySide6 >=6.8,<6.12, own lock file | No (for now) | A separate upgrade decision for the user | no timing data yet |
| 6e8804d1, 12d061d9 | 09-17, 09-18 | Code cleanup; ruff format over 153 files | n/a | No | Formatting only; would conflict everywhere | n/a |
| 949f562e | 09-18 | PyInstaller: drops unused PySide6 QML modules, compares paths without regard to capitals, debug off | Ours `joystick_gremlin.spec:201-220` drops only `Pythonwin` and `translations`, case-sensitive; debug is already off | **Adapt** | A smaller install; no feature loss (we import none of the dropped modules); check with a build | 3-8 min (timings.md: agent fix / feature / docs) plus a build and install check |
| 0e6be537 | 09-18 | `codecs.open` replaced by `open(..., encoding)` in profile save; test fixes | No `codecs` in `gremlin/profile.py` | Already have | — | n/a |
| ebda0ead, b7fe633b, 567a432b | 09-18, 09-19 | GitHub Actions: nightly build, manual dispatch, node v24, action-gh-release v3 | Own `ci.yml`, `release-exe.yml` (has `workflow_dispatch`) | No | Our CI is separate; the action version bump could be checked on its own | n/a |
| fff48e70 | 09-19 | Moves every config option into one `gremlin/config_registry.py` | Options are registered where they are owned | No | Conflicts with design-for-change (each piece declares its own) | n/a |
| a4d95f8f | 09-19 | QML fixes (Condition, Macro, Response Curve, Kobold controls) | Own editors | No | Kobold UI | n/a |
| 0d93b7e7 | 09-19 | A new Map to vJoy starts on the first unused vJoy input; `Profile.bound_actions_by_type` | Have: first claimed output not used in the mode, through the output module (05 S113, `action_plugins/map_to_vjoy/__init__.py:318`) | Already have | Ours follows the layer rule | n/a |
| 78e2bc60 | 09-19 | C++ crash fixes: DILL callbacks registered once as permanent stubs; `inputItemChanged` emitted after returning to the event loop | Equivalent: retired callbacks kept alive (`dill/__init__.py:391-402`, `_retired_callbacks`); deferred emit (`action_model.py:61`) | Already have (equivalent) | Ours keeps every old callback alive instead of one stub; same safety | n/a |
| 446a9600 | 09-19 | Chips list nested actions, not only root ones | Our rows list every leaf target (`bindingTargets`, 05 S142) | Already have (own design) | — | n/a |
| 20fef6f9 | 09-20 | Object-lifetime crash: `expansionChanged` connected through a lambda, not a bound method; removes a Kobold header | We have no `expansionChanged` connection | No | Not applicable | n/a |
| 8db9d0f9 | 09-20 | One mouse motion manager (`sendinput` MotionKey / velocity sources) | Have: `gremlin/sendinput.py:115-222` (`MotionSource`, `MouseMotionManager.set_velocity`) | Already have | — | n/a |
| bf034739 | 09-20 | Callback registry for mode changes (`ModeChangeActions`, `is_same_binding`): stops mouse motion when a mode change moves the input elsewhere | Have: `gremlin/event_helpers.py:243`, `event_handler.py:829`, `map_to_mouse/__init__.py:81,149` | Already have | — | n/a |
| 123ab4f2 | 09-21 | Mouse drift: rest threshold 1e-3; spline divides by a guarded segment width, not `+eps` | Have: `gremlin/spline.py:234-341`, `map_to_mouse/__init__.py:165` | Already have | — | n/a |
| 04246ee6, 0761d7fc, 68844d52, 9bcee826 | 08-02 to 09-21 | Merge Axis: Prefer Extreme / Prefer Center added, then renamed Maximum Deflection (`maximum-deflection`) and Closest to Center (`closest-to-center`); display names; docs; tests | Have Maximum Deflection (`maximum-deflection`) and Prefer Center (`prefercenter`), per 05 S114 | Already have | Note: upstream stores Closest to Center as `closest-to-center` and ours as `prefercenter`, so that one operation doesn't load across the two programs. S114 keeps our name | n/a |
| 32eebedc | 09-21 | `InputIdentifier.label` uses the device map's input name and `input_to_ui_string`; QML input-assign button | Ours: `device.py:76-91` builds "Type N" from the raw id | **Check**, then adapt | Keyboard ids and named device inputs may show raw; unverified where it shows | 3-8 min (timings.md: agent fix / feature / docs) if confirmed |
| 7a928a63 | 09-22 | Hat Buttons: radio buttons act only when checked; switching 4/8 keeps the shared directions; syncs the binding | Have, better: keeps shared directions and asks before dropping diagonals (`hat_buttons/__init__.py:253-270`) | Already have | — | n/a |
| 437451b6 | 09-23 | Action fixes: a new Pressed comparator defaults to pressed; the direction list is no longer a shared default; vJoy condition resolved per call and starts on the first usable output; new macro steps press; Win keys count as modifiers; macro load errors logged; "Unable to add" errors shown | Have all: `comparator.py:225,273`; `condition.py:322-362` (through the output module); `macro.py:606,727,1132,1286`; `keyboard.py:337-338` | Already have | Ours through the output module (layer rule) | n/a |
| e65e2968 | 09-24 | Script keyboard variable passes the `Key` itself (lookup by name failed) | Have: `user_script.py:1330,1893` (05 S95) | Already have | Script interface: see ST-SCRIPT | n/a |
| 7d139c56 | 09-24 | Mouse wheel moves the numeric range slider | Our `qml/NumericalRangeSlider.qml` has no wheel; several of our pages block the wheel on purpose (`onWheel: w.accepted = true`) | No (ask if wanted) | A behaviour change; our pages deliberately stop the wheel changing values | n/a |
| e0e65272 | 09-24 | Log viewer dialog (`log_viewer.py`, `DialogLogViewer.qml`) | Have the log in the Live feed (`qml/LiveLogTrace.qml`) | No | Memory rule: Live stays as it is | n/a |
| eda04f0b | 09-24 | Recent profiles menu | Have (`backend.py:867` `recentProfiles`, Recent, Forget) | Already have | — | n/a |
| 58499ab9 | 09-24 | Natural sort for Logical Device inputs (regex key) | Have: `logical_device.py:39` `_natural_key` | Already have | — | n/a |
| d6e9b053 | 09-25 | Reference pick list: "[mode] device - input › action", sorted, each action once, unbound last; `common.natural_key`; `device_and_input_names`; deferred emit on replace | Ours lists the action label only (`reference/__init__.py:113-123`); Root is already excluded (S60a) | **Adapt** (feature; spec change to 05 S60) | Makes shared actions far easier to find; ask the user first | 3-8 min (timings.md: agent fix / feature / docs) plus the spec line and Help |
| 381ff687 | 09-25 | Startup mode: Last Active per profile path, `resolve_start_mode`, rename/delete follow | Have, further: `mode_manager.py:114-352`, `profile.py:235-261`, 04 S44, S46, S52 (no Use Heuristic) | Already have | — | n/a |

## Recommended to take (ranked)

1. **Refuse dropping an action into its own subtree** (from 86ea050c). This is a
   likely bug: `InputItemBindingModel.move_action` (`gremlin/ui/profile.py:389`)
   has no descendant check. Port upstream's `can_move_action` /
   `_is_descendant_of`, and call it from `ActionModel.dropAction` before the
   move. Start with a failing test that drags a Chain onto its own child.
   Effort: 3-8 min (timings.md: agent fix / feature / docs) plus the test.
2. **Getters for write-only Qt properties** (855eb31c, 2a773013):
   `LogicalDeviceSelectorModel.validTypes` (`gremlin/ui/device.py:535`) and
   `AxisCalibration.guid` (`gremlin/ui/device.py:1268`). This is a bug fix with
   no behaviour change. Effort: 3-8 min (timings.md: agent fix / feature / docs).
3. **Check `InputIdentifier.label`** (32eebedc) for keyboard inputs and named
   device inputs; if it shows raw ids, use `common.input_to_ui_string` and the
   device map's input name. Effort: 3-8 min (timings.md: agent fix / feature / docs) once
   confirmed.
4. **Smaller install** (949f562e): add upstream's PySide6 QML module excludes
   and make the path comparison ignore capitals in `joystick_gremlin.spec`.
   Then build, install and start it (standing rule) to prove nothing is
   missing. Effort: 3-8 min (timings.md: agent fix / feature / docs) plus the build and install
   check.
5. **Reference pick list with where each action is used** (d6e9b053). This
   changes 05 S60, so ask the user first. Effort: 3-8 min (timings.md: agent
   fix) plus the spec, map and Help updates.

Not recommended: the Kobold style series, the central config registry, the
Python 3.14 move (only as its own decision), the wheel-driven slider (ask
first), and the log viewer (the Live feed covers it).
