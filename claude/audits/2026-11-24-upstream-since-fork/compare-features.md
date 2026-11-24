# Upstream since the fork: three feature commits compared with ours (C-FEATURES)

Read-only study, 2026-11-23 17:45-17:49 (agent C-FEATURES). Merge base daf4057f;
`upstream` fetched. Items 12-14 of the upstream comparison (see commits-1.md,
commits-2.md). Nothing was changed except this file.

---

## 12. d6e9b053 "Improve reference action": the Reference pick list

### Upstream, side by side with ours

| Part | Upstream (d6e9b053) | Ours |
|---|---|---|
| Which actions are offered | Every library action that passes the selector (not Reference, not Root, same behaviour, no loop). Actions reachable from an input first, then **actions reachable from no input, last**, sorted by label. | `Library.pick_list` (`gremlin/profile.py:1002`): the current action, the actions of the input being edited (the pane's draft), and the actions an input uses (`in_use`). A draft copy hides its original. Deleted or replaced actions are never offered (05 S57 rule, shared with Merge Axis and Dual Axis Deadzone). Selector the same (`action_plugins/reference/__init__.py:94-121`; Root left out, 05 S60a; a key's actions are button actions, 05 S60). |
| Label | `[mode] device - input › action label`; unused ones show the bare label. | The bare `action_label` (`__init__.py:115`). |
| Order | Natural sort (numbers by value) by mode, then device name, then device GUID, then input name; inside an input, depth-first in tree order. | Order of `pick_list`: mine first, then library insertion order. |
| Each action once | Yes, under the first input it is reached from (`seen_ids`). | Yes (`ids` set in `pick_list`), but with no place shown. |
| Device / input names | New `gremlin/ui/device.py:device_and_input_names()`: "Logical Device", "Keyboard", or the DILL name; the input name from the device database mapping. | `InputIdentifier.label` (`gremlin/ui/device.py:76`) uses `device_names.shown_name()` (alias, twin name, vJoy number; GL-124) and "Button 3" style. The shared input text is `references.input_label()` (`gremlin/references.py:133`), used by `usages` and Search. |
| `natural_key` | Moved into `gremlin/common.py`, `logical_device.py` reuses it. | Three copies: `gremlin/logical_device.py:39 _natural_key` (also imported by `ui/hardware_layout.py:29`), `gremlin/ui/keyboard_layout.py:77 _natural_key` (returns a list, a different shape). |
| Buttons' tooltips | "Link Action", "Copy Action" (`ToolTip`). | `IconButton`s with no tooltip (`ReferenceAction.qml:40-56`). |
| Refresh after pick | `_replace_reference` reads `enumeration_index` before `remove_action`, then `_emit_input_item_changed_later(enumeration_index)`. | `_replace_reference` (`__init__.py:139`) calls `append_action` + `remove_action` only; no input-item-changed emit. Our `ActionModel.removeAction` (`gremlin/ui/action_model.py:355`) does emit it, but `_replace_reference` calls the binding model directly, so the row (Bindings boxes, can't-be-sent marks) may stay stale until the next refresh. **Unverified: needs a live check** (pick a Reference on the Device Bindings page and see whether the row's Bindings boxes update at once). |
| Combo popup | Kobold `ComboBox.qml`: popup 16 rows tall, scroll bar, margins. | Not applicable: our ComboBox popup is the shared `Menus.DropdownPopup` (`theme/GremlinStyle/ComboBox.qml:113`), a separate design. Leave out. |

### How it would fit our design

- **"Unused last" conflicts with our list rule.** Our pick list never offers
  actions no input uses (05 S57's rule; Help: "The list shows only actions you
  added yourself"). Upstream's unused group is exactly what we hide. Take only
  the labelling and ordering, not the unused group.
- **The draft must be labelled too.** Upstream walks
  `shared_state.current_profile.inputs`; in our pane the input being edited is a
  draft (`Library.draft_of`), so its actions are not in the profile's inputs
  yet. The label owner must label "mine" with the edited input's place, then the
  in-use actions by walking the profile's inputs.
- **Shared owner.** The place text "[mode] device - input" should come from one
  helper next to `references.input_label` / `device_names.shown_name`, not a
  second `device_and_input_names`. Our Search copy line already uses " › " as
  the separator (`gremlin/ui/search_model.py:930`), so the glyph matches.
- **Glossary:** an action used by more than one input is **shared**; "linked"
  and "reference copy" are listed as words not to use (`claude/glossary.md:93`).
  So the tooltips are **Share this action** and **Duplicate this action** (Help
  already says Share / Duplicate), not "Link Action" / "Copy Action". Use our
  `PointerTip` (qml/PointerTip.qml), as elsewhere.
- **Mode inheritance:** an action reached from a child mode that inherits it
  shows under the mode where the input binds it (the walk is by
  `input_item.mode`), which matches how rows show it. No conflict.
- **Shared actions:** an action two inputs share shows once, under the first
  input in sort order. Acceptable; an option is to add "(shared)" — ask.

### Files to change

- `action_plugins/reference/__init__.py` (`_get_actions`: labels and order;
  `_replace_reference`: emit input-item changed, if the live check shows it is
  stale).
- `gremlin/profile.py` `pick_list` stays the owner of *which* actions; a new
  small helper returns `(action, place)` pairs or the labelling sits in the
  Reference model. Recommend: a `Library.pick_list_places()` or a helper in
  `gremlin/references.py` so Merge Axis / Deadzone lists could use it later.
- `gremlin/common.py` (or `gremlin/util.py`): one `natural_key`; replace the two
  `_natural_key` copies (`logical_device.py`, `ui/keyboard_layout.py` — its list
  shape must keep sorting the same) and `ui/hardware_layout.py`'s import.
- `action_plugins/reference/ReferenceAction.qml`: tooltips.
- `qml/help/device_bindings_actions.js:888` (Reference topic): say what each
  line shows and its order.

### Spec

- 05 S60 gains (or a new S60b): "The Reference list should show each action
  once as `[mode] device - input › action`, sorted by mode, device and input
  (numbers by value), actions in their order inside the input; the input being
  edited uses its draft." Needs the user's yes (change control).
- S57 unchanged (no unused group).
- New glossary rows: none needed beyond the tooltip words (use **Share** /
  **Duplicate**).

### Tests

- Pinning today: `test_audit3_actions_undo.py` (S57/S60/S60a: `:300`, `:321`,
  `:552`, `:800`, `:809`) and `action_matrix/test_matrix_flow.py::_reference_flow`
  (`:409`) check the *values* (ids) as sets, not labels or order, so they keep
  passing. `test_audit3_actions_undo.py:396/415` set `action_label` on a link
  for other checks; read them before the change.
- New: label text and order (two modes, two devices, Button 2 before Button 10),
  each action once, the pane's draft labelled with the edited input, alias name
  used, no unused actions; row refresh after Share/Duplicate (if stale); one
  `natural_key` test covering the keyboard page's old order.

### Risks

- The keyboard `_natural_key` returns a list; swapping it may change the
  Keyboard page's sort for mixed text. Keep a test on its current order.
- Large profiles: walking every input on each `actions` read. The property is
  read when the editor opens; fine, but do not bind it to a frequent signal.

### Effort

3-8 min per agent (timings.md: agent fix / feature): 2 agents in parallel
(Reference model + helper; `natural_key` merge) plus one docs agent (spec,
Help, map) ~10 min for the batch (timings.md: "a batch of parallel agents
~10 min"), then lead checks ~5 min, quick tests, build + silent install + live
check ~3 min (timings.md 2026-11-23 build/test rows), commit, CI ~25 min in the
background.

---

## 13. 2877b2e4 "Implement default profile"

### Upstream, side by side with ours

| Part | Upstream (2877b2e4) | Ours |
|---|---|---|
| Setting | `profile/automation/remain-active-on-focus-loss` (Bool) replaced by `focus-loss-behavior` (Selection: **Deactivate**, **Remain active**, **Load default**). | `remain-active-on-focus-loss` Bool (`joystick_gremlin.py:963`), shown as **Keep running when the program loses focus** (`gremlin/ui/option.py:58`, Options › Profiles group at `:85-89`). |
| Default entry | Auto-load entries get a 4th field `isDefault`; one entry at most (setting one clears the others); a Default entry needs no program (Browse / Select Executable disabled). | Entries are `[profile, program, enabled]` (`ProfileAutoLoadingModel`, `gremlin/ui/option.py:~860-940`, `qml/OptionProfileAutoLoading.qml`). |
| Matching | `get_profile` and the pattern match skip the Default entry; pattern match wrapped in `try/except re.error`; the early `return None` inside the loop (only the first pattern was ever tried) fixed. | Already fixed our way: `gremlin/config.py:646-683` — `_same_program` (case, slashes), patterns tried in order, blank entries skipped, `re.IGNORECASE`, `re.error` logged and skipped. Nothing to take here except skipping a Default entry. |
| No profile for the new program | `Deactivate` stops; `Remain active` keeps going; `Load default` loads the default profile unless Gremlin itself is in front, the file is missing (warning in the log) or the open profile has unsaved changes (silently). | `Backend._active_process_changed_cb` (`gremlin/ui/backend.py:567-620`): own window = no change (02 Q18); missing file: one notice "… was not loaded: the file is missing." and stop unless Keep running (S89); unsaved edits: stop + **Auto-load Waited** notice once (S88, 04 Q3/GL-150); no profile: stop unless Keep running (S90). |
| Recent list | Auto-loads (`_auto_load_profile`) do **not** go into Recent or last profile. | Auto-load calls `loadProfile`, which records Recent and last profile (`_record_profile_use`, `backend.py:1152`; 04 S18 "a loaded or saved profile at the top of Recent"). |
| Config migration | New `gremlin/config_migration.py` converts old settings by last-run version. | Not wanted: unreleased, no legacy compatibility (CLAUDE.md). A new setting name simply starts at its default. |
| Start-up | Unchanged (last profile). | 04 S21: `--profile` path, else the last profile; S22 Forget It / Keep. Not touched by upstream. |

### What "default profile" means here

Upstream's default profile is **not** "a profile loaded when nothing else is"
at start-up. It is the profile auto-load switches to when the program in front
has no entry. At start-up both programs open the last profile. If the user
wants a start-up default as well, that is a separate decision (see question 3).

### How it would fit our design and UI

- **Where it lives:** Options › Profiles, the same group as **Load profiles
  automatically**, **Programs and their profiles** and today's Keep running
  switch. Recommended layout (cleanest current design, no compatibility):
  - replace the Keep running switch with one choice **When a program with no
    profile comes to the front:** **Stop the profile** / **Keep running** /
    **Load the default profile** (glossary-style words; upstream's
    "Deactivate / Remain active / Load default" use words our glossary does
    not: we say **Run** and **stop**);
  - the default profile as its own row under that choice, **Default profile:**
    a file picker (`FilePicker` kind "profile"), enabled only for the third
    option — rather than upstream's "Default" tick on an entry with no program.
    A tick on a program-less row adds a special case to every entry rule
    (blank program, Browse disabled, one-at-most), and our list already skips
    blank programs on purpose (`config.py:667`, "would match every program").
    Upstream's tick is offered as option b.
- **Keep our rules on the new path:** own window = no change (Q18), unsaved
  edits = wait with the **Auto-load Waited** notice (S88; upstream skips
  silently), missing file = one notice (S89; upstream only logs).
- **Recent:** decide whether auto-loads (all of them, not only the default)
  stay in Recent. Upstream: no. Ours: yes (S18). Ask.
- **Glossary:** new rows for the choice and **Default profile**; the
  **Keep running when the program loses focus** row (if any) changes. Note the
  current label already says "loses focus" while the behaviour is "a program
  with no profile gets focus" (S90); the new wording fixes that.

### Files to change

- `joystick_gremlin.py` `register_config_options` (`:963`): the Bool replaced by
  a Selection `focus-loss-behavior` (our name could be `no-profile-behavior`),
  plus `default-profile` (Path).
- `gremlin/ui/option.py`: labels (`:58`), the Profiles group (`:85-89`); if
  option b, `ProfileAutoLoadingModel` role `isDefault`.
- `qml/OptionProfileAutoLoading.qml` (option b only) or the generic option
  rows (option a: a Selection and a Path row, probably no new QML).
- `gremlin/ui/backend.py` `_active_process_changed_cb` (`:567`): three
  branches use `remain-active-on-focus-loss` (`:586`, `:596`, `:616`); one
  helper for "no profile here" so the missing-file and unsaved branches use the
  same choice.
- `gremlin/config.py` only for option b (skip the Default entry).
- Help: `qml/help/options_profile.js` (`:239-275`, the auto-load topic and the
  Keep running line `:273`), `qml/help/getting_started.js:298`.
- `claude/glossary.md`, `claude/program-map/02-devices-input.md` (sections 2-5,
  8 K, 10, 11), page 04 if Recent changes.

### Spec

- 02 S90 changed: "When a program with no profile comes to the front, it
  should do what **When a program with no profile comes to the front** says:
  stop (default), keep running, or load the default profile."
- 02 new S90a: the default profile follows S87 (no reload when already open),
  S88 (never over unsaved edits, notice once), S89 (missing file: notice once,
  then the stop/keep rule), Q18 (own window = no change).
- 02 S89 wording: "unless Keep running is on" becomes "unless the choice is
  Keep running" (and what happens when the choice is Load the default profile
  and the program's own profile file is missing: load the default? Ask).
- 04 S18 only if auto-loads leave Recent.

### Tests pinning today's behaviour

`test_audit2_saving.py` (S89), `test_autoload_and_mode_prompts.py` (S88),
`test_audit_saving.py::test_auto_load_leaves_the_open_profile_alone` (S87),
`test_backend_commands.py`, `test_batch2_b4.py`, `test_final_02.py`,
`test_options_shared_pieces.py`, `test_option_list_saving.py`,
`test_stage1_runtime.py`, `test_write_less.py` all name
`remain-active-on-focus-loss` or `entries-auto-loading`; each needs the new key.
Upstream's `test/application/test_profile_auto_loading.py` (149 lines) is a
model for the new tests but drives Kobold QML, so not copyable.

### New tests

Each choice with a program that has no entry; default loaded, not reloaded
when open; own window no change; unsaved edits wait + notice once; missing
default notice once; pattern entries never match the default; Options row
enabled only for the third choice; the setting saved and read back; Recent
per the decision.

### Risks

- A default profile that loads whenever any unlisted program comes to the
  front (Explorer, a browser) switches profiles often; each switch stops and
  starts the Run (vJoy/Xbox outputs released). Upstream does the same; Help
  should say so.
- The missing-file branch: today it stops unless Keep running; with a third
  choice the rule needs a decision (question 2).

### Effort

Rough, from timings.md: 2 program agents (backend + settings/options;
Help/spec/glossary/map as the third) at 3-8 min each, batch ~10 min
(timings.md: agent fix / feature), test updates in the ten files above as a
fourth parallel agent (~5 min), lead checks ~5 min, quick tests, build +
silent install + live check ~3 min, CI ~25 min in the background. Option b
(tick on an entry) adds the QML list change: one more agent, same batch.

### Questions for the user (planning only)

1. **Where the default profile is set**
   - a) A **Default profile** file row under the new choice (recommended).
   - b) Upstream's **Default** tick on an auto-load entry with no program.
2. **The program's own profile file is missing and the choice is Load the
   default profile**
   - a) Load the default profile (after the one notice).
   - b) Stop, as today.
3. **A start-up default as well** (open a fixed profile at start instead of the
   last one)
   - a) No; start-up stays S21 (last profile).
   - b) Yes, as a separate setting (new spec on page 04).
4. **Auto-loaded profiles in Recent**
   - a) Keep them in Recent and as the last profile (today, S18).
   - b) Leave them out, as upstream.

---

## 14. 949f562e "Improve pyinstaller file": smaller install

### Upstream, side by side with ours

| Part | Upstream (949f562e) | Ours (`joystick_gremlin.spec`) |
|---|---|---|
| Qt DLL excludes (`to_exclude`) | Unchanged in this commit. | Already the full list (`:94-200`): every DLL behind the folders below is excluded, plus the MSVC runtime (01 S193). |
| `directory_excludes` | Adds 24 `PySide6\qml\...` folders (list below). | Only `Pythonwin`, `PySide6\translations` (`:201-204`). |
| Compare | `dest.lower().startswith(directory.lower())`. | `dest.startswith(d)` in `trim()` (`:208-221`), used for all four Analyses (main, tester, helper, ctl: `:236`, `:298`, `:333`, `:369`). |
| datas / hidden imports / `debug=False` | Kobold layout (`style/qml`), its own module names, `debug=False`. | Not applicable: our datas and hidden imports differ (`test_spec_hidden_imports.py` guards ours); all our EXEs already have `debug=False`. |

### Each excluded folder, checked against our code

Checked: every `import` line in `qml/`, `theme/`, `action_plugins/`, `gremlin/`
QML (our QML imports: QtQuick, QtQuick.Controls, .Controls.Universal (+impl),
.Controls.impl, .Templates, .Layouts, .Window, .Dialogs, .Shapes, QtQml,
QtQml.Models, QtQml.StateMachine, QtCore, QtCharts, Qt.labs.qmlmodels), every
PySide6 import in `gremlin/`, `action_plugins/`, `gremlin_ctl/`,
`joystick_gremlin.py`, `input_tester.py` (QtCore, QtGui, QtQml, QtQuick,
QtPrintSupport, QtTextToSpeech), no `Qt.createQmlObject`, and the style:
`QT_QUICK_CONTROLS_STYLE=GremlinStyle` (`joystick_gremlin.py:106`,
`input_tester.py:65`), whose `theme/GremlinStyle/qmldir` imports only
`QtQuick.Controls.Universal`. Sizes from today's `dist/gremlin_platforms`.

| Folder | We use it? | Its DLL already excluded | Size in dist |
|---|---|---|---|
| Qt3D | no | Qt63D*.dll | 826 KB |
| QtDataVisualization | no | Qt6DataVisualization(Qml) | 284 KB |
| QtGraphs | no | Qt6Graphs | 486 KB |
| QtLocation | no | Qt6Location | 153 KB |
| QtPositioning | no | Qt6Positioning(Quick) | 117 KB |
| QtQuick3D | no | Qt6Quick3D* | 3241 KB |
| QtQuick\Controls\FluentWinUI3 | no (style is GremlinStyle → Universal) | Qt6QuickControls2FluentWinUI3StyleImpl | 6547 KB |
| QtQuick\Controls\Fusion | no | Qt6QuickControls2Fusion(StyleImpl) | 369 KB |
| QtQuick\Controls\Imagine | no | Qt6QuickControls2Imagine(StyleImpl) | 351 KB |
| QtQuick\Controls\Material | no | Qt6QuickControls2Material(StyleImpl) | 438 KB |
| QtQuick\Controls\Windows | no | Qt6QuickControls2WindowsStyleImpl | 867 KB |
| QtQuick\LocalStorage | no | Qt6Sql | 37 KB |
| QtQuick\Pdf | no | Qt6Pdf, Qt6PdfQuick | 146 KB |
| QtQuick\Scene2D | no | Qt63DQuickScene2D | 37 KB |
| QtQuick\Scene3D | no | Qt63DQuickScene3D | 41 KB |
| QtQuick\Timeline | no | Qt6QuickTimeline* | 78 KB |
| QtQuick\VectorImage | no | Qt6QuickVectorImage* | 78 KB |
| QtRemoteObjects | no | Qt6RemoteObjects(Qml) | 41 KB |
| QtScxml | no | Qt6Scxml(Qml) | 49 KB |
| QtSensors | no | Qt6Sensors(Quick) | 73 KB |
| QtWebChannel | no | Qt6WebChannel(Quick) | 37 KB |
| QtWebEngine | no | Qt6WebEngine* | 254 KB |
| QtWebSockets | no (the control API does not use Qt WebSockets) | Qt6WebSockets | 89 KB |
| QtWebView | no | Qt6WebView(Quick) | 45 KB |

Total about 14.7 MB (most of it FluentWinUI3, 6.5 MB, and QtQuick3D, 3.2 MB).
Every one of these QML plugins could not load anyway, because the DLL behind
it is already left out, so removing the folders changes nothing at Run.

Not in upstream's list but also unused by us (found while checking; optional,
verify before adding): `QtMultimedia` (Play Sound uses miniaudio), `QtTest`,
`QtQuick\VirtualKeyboard`, `Qt5Compat`, `QtQuick\Particles`,
`QtQuick\Effects`. **Keep** `QtQuick\NativeStyle`, `QtQuick\Dialogs`
(10 QML files import QtQuick.Dialogs: FileDialog, FolderDialog, ColorDialog,
MessageDialog), `QtCharts`, `QtTextToSpeech`, `QtQml\StateMachine`,
`Qt\labs\qmlmodels`, `QtQuick\Controls\Basic` and `Universal`.

### Files to change

- `joystick_gremlin.spec` only: the 24 folders in `directory_excludes`; the
  compare in `trim()` made case-insensitive (`dest.lower().startswith(d.lower())`,
  both list comprehensions). Shared by all four exes, so one owner.

### Spec / Help / glossary

- 01 section 2 (the `joystick_gremlin.spec` line, `01-app-shell.md:81`) notes
  the QML folders left out. No behaviour statement changes; commit line
  `Spec: none (no behaviour change)` is not required (the spec file is not in
  the program-code list) but the map line should be updated. No Help or
  glossary change.

### Tests

- Existing: `test_spec_hidden_imports.py`, `test_input_tester_packaging.py`,
  `test_licences_shipped.py`, `test_installer_drivers.py`, `test_ssm_helper.py`,
  `test_b1_xbox.py` read the spec; none pins `directory_excludes`.
- New (cheap): a unit test that parses the spec and checks that every QML
  folder in `directory_excludes` is not imported by any `.qml`/`.py` file
  (guard against a later QML import of an excluded module), and that the
  compare is case-insensitive.

### The build check needed

Build, silent install, then live: start the program and the Input Tester;
open every window through the control API (`gremlin-ctl` windows list → open
each), including a ColorDialog (Device Mapping Editor colours), a FileDialog,
Options, Help, the Device Bindings page with a chart (QtCharts); grep
`system.log` and the tester's log for `module "..." is not installed` /
`Cannot load library` / `qrc` QML errors; compare the `dist` size before and
after (expect about -14.7 MB). Also run Text to Speech and Print once.

### Risks

- Low. The only real risk is a QML file somewhere importing one of these
  modules indirectly; the grep found none, and each plugin's DLL is already
  missing, so it would fail today too.
- Case-insensitive compare also matches `PySide6\Translations` etc.; intended.

### Effort

3-8 min for one agent (timings.md: agent fix) + build + silent install + live
check ~3 min (timings.md: build/test rows 2026-11-23, 1-6 min) + commit,
CI ~25 min in the background. One agent: a single file.

---

## Blockers before any change

- 12: the user's yes on the S60 label/order statement; the stale-row
  question needs a live check first.
- 13: questions 1-4 above; change of 02 S89/S90 needs approval.
- 14: none; only the build check.
