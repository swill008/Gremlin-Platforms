# Plan: QML-made Python objects through a factory (PYSIDE-WRAPPERS fix)

Planning agent P-MEM, 2026-11-23, 18:38-18:43. Read-only study; nothing
built. Approved direction: user, 2026-11-23, answer 1a in
`claude/audits/2026-11-24-upstream-since-fork/README.md` ("Memory and viewer
gaps"). Findings: `memory.md` and `compare-measure.md` item 15 in the same
folder. Not approved to build: the questions at the end come first.

## 1. What upstream did (verified with git, remote `upstream`)

### 02a280e8 "Work around PySide6 memory leak" (2026-10-24)

- New `gremlin/ui/model_factory.py`: `class ModelFactory(QtCore.QObject)`
  with `@QtQml.QmlElement @QtQml.QmlSingleton`, `QML_IMPORT_NAME =
  "Gremlin.UI"`. Docstring: PySide6 never frees a Python object QML
  instantiates (PYSIDE-1407); "once PYSIDE-1407 is fixed the factory can be
  retired". `joystick_gremlin.py` imports it so it registers.
- **24 typed slots**, one per type, e.g.
  `@QtCore.Slot(QtCore.QObject, result=ModeListModel) def modeListModel(self,
  parent): return ModeListModel(parent)`. Two take extra arguments:
  `deviceListModel(parent, device_type: str)` (sets `deviceType` before
  returning) and `windowGeometry(parent, name, default_w, default_h, min_w,
  min_h)`. Nothing else is set in Python.
- **Ownership**: the only rule is "the QML item is the Qt parent". Qt's
  parent deletion frees the object; the QML engine never garbage-collects an
  object that has a parent. No explicit `setObjectOwnership`.
- **How QML calls it** (`import Gremlin.UI`), always as a typed read-only
  property of the owning item, with the item's id as parent:
  `readonly property InputListenerModel _listener: ModelFactory.inputListenerModel(control)`.
  Inline uses became the same: `model: ModelFactory.modeListModel(_switch_combo)`.
- **Declarative bindings** (`guid: deviceGuid`) became imperative:
  `Component.onCompleted: _axis_series.guid = deviceGuid` plus
  `onXChanged: () => { if (_model) _model.x = x }` handlers.
- **`property alias x: _model.y`** (aliases can only target ids) became a
  plain property plus a change handler (InputCaptureButton,
  LogicalDeviceSelector).
- **Signal handlers** declared on the object (`onListeningTerminated`,
  `onDeviceChanged`) became `Connections { target: root._model; function
  onX() {} }`, with unqualified names qualified (`_root._axis_series.axisCount`).
- **Order traps** they hit: LogicalDeviceSelector needs `validTypes` before
  the identifier, so a `_ready` flag gates the handlers until
  `Component.onCompleted` has set both in order. AxesStateSeries assigns
  `guid` only in `Component.onCompleted`, after the `Connections` exist,
  because the change handler builds the chart series.
- `Component.onDestruction: _listener.enabled = false` stops a listener
  before its parent goes.
- Child models made in `data()` (Options): `ConfigSectionModel` and
  `ConfigGroupModel` now cache one child per row, parented to themselves
  (we did the same in F3-LEAKS, 2026-10-10).
- Required properties and delegates: no factory object sits inside a
  delegate in that commit; `required property` is untouched (it is on QML
  delegate items, never on the Python types).

### Follow-ups

- **9602a510**: models made per `data()` call become one cached child per
  row (`OutputVJoyListModel._initial_values_models`, `deleteLater()` on
  reset); `Backend.scriptListModel` becomes one constant model fed the new
  profile; ScriptManager.qml clears a model that refers to deleted children
  on profile change.
- **66bb2477**: `reuse_or_replace_selection_model(current, labels, values,
  parent)` in `gremlin/ui/profile.py` keeps a matching `LabelValueSelectionModel`
  and `deleteLater()`s the old one (merge_axis, reference,
  dual_axis_deadzone); test `test_selection_model_reuse.py`.
- **9fb7147b**: `ObjectLoader.qml` replaces `Loader.setSource` (creates with
  `component.createObject(root, props)`, hides then `destroy()`s the old
  item); `gc.collect()` after a profile load.

### Upstream pitfalls seen

1. A factory call is a binding expression. Any argument that changes would
   re-run it and make a new object, the old one staying under the parent.
   Upstream only ever passes the id, so it runs once.
2. Live values need hand-written handlers in two places (completion and
   change); easy to miss one; order matters.
3. No guard: a new `TypeName {}` in QML brings the leak back silently.
4. `Device.inputIdentifier()` still does `InputIdentifier(..., parent=self)`
   per call upstream (the growth we measured in scenario C is there too).

### What is in ours already, what is not (checked)

- Not ported: 9602a510's `OutputVJoyListModel` cache (ours makes a new
  `OutputVJoyInitialValuesModel` per `data()` call, `gremlin/ui/profile.py:1345`);
  66bb2477's reuse (ours: `action_plugins/merge_axis/__init__.py:206`,
  `action_plugins/reference/__init__.py:119` make a new model per call);
  `ObjectLoader`. These are parent-held growth, not shells (question 8).
- Ours already caches `ScriptListModel` (`gremlin/ui/backend.py:1138`) and
  the Options child models (F3-LEAKS). Our `gc_guard.py` collects every 1 s,
  so upstream's `gc.collect()` after a load is not needed.

## 2. Our design

### One owner module

`gremlin/ui/model_factory.py` (upstream's name, so later upstream merges
line up). Class `ModelFactory`, a QML singleton in `Gremlin.UI`, version 1.

### Registry, not 81 slots (recommended, question 1)

Our `ta.QmlElement` (`gremlin/ui/type_aliases.py:21`) is our own decorator
and registers 111 of the 117 types. It also records each class in
`QML_TYPES: dict[str, type]`. The factory then needs one slot:

```
@QtCore.Slot(str, QtCore.QObject, "QVariantMap", result=QtCore.QObject)
def create(self, type_name, parent, props=None) -> QObject
```

- Looks up `type_name` in `QML_TYPES`; unknown name or `parent is None`
  raises (logged with the QML file via the engine's warning).
- Builds `cls(parent)`, then sets `props` in their given order with
  `setProperty` (JavaScript object literals keep insertion order), so order
  traps like LogicalDeviceSelector's are solved by the literal's order.
- Calls `QQmlEngine.setObjectOwnership(obj, CppOwnership)`, so the
  JavaScript garbage collector can never delete it (guards against a double
  free if a parent is ever missing).
- Main thread only: asserts `QThread.currentThread()` is the app thread
  (program thread rules).
- New types need no factory edit (design-for-change rule). Types with
  constructor arguments beyond `parent` do not exist among the 81 (all have
  `__init__(self, parent=None)`, which QML already requires).

### QML call pattern (the contract all QML parts write to)

```
import Gremlin.UI
readonly property HardwareLayoutModel _layout:
    ModelFactory.create("HardwareLayoutModel", _root, { deviceType: "physical" })
```

1. Always a `readonly property <Type> <oldId>` on the item that owned the
   declaration, named as the old `id`, so unqualified uses in the file keep
   working. Inline uses (`model: ModeListModel {}`) become such a property
   on the enclosing item plus `model: _modes`.
2. Parent = the id of the item that held the declaration (for a delegate,
   the delegate's own root; for a `Window` file, the window).
3. `props` holds constants only (strings, numbers, enum values). Never a
   value that can change: it would re-run the call and make a new object.
4. A declarative binding to a changing value (`guid: _root.guid`) becomes
   `Binding { target: _live; property: "guid"; value: _root.guid }`
   (question 3; upstream uses handlers). Where the old code relied on the
   order of first assignment, set the first value in `props` and keep the
   `Binding` for changes.
5. `onX:` handlers on the object become `Connections { target: _x; function onX(...) {} }`.
6. `property alias a: _x.b` becomes `property <type> a` + `Binding` to the
   object (and back, if the alias was written from outside: the agent lists
   any two-way alias in its report). `readonly property alias layout:
   _layout` becomes `readonly property HardwareLayoutModel layout: _layout`.
7. `Component.onDestruction` stays where an object must be stopped first
   (listeners, live state).

### Lifetime rules

- The object lives exactly as long as its QML parent. Python code must not
  keep a factory-made object past that (copy the data instead). Known case:
  `backend.setCurrentInput` keeps the `InputIdentifier` it is given, which
  is why that identifier is fixed in Python, not by the factory (question 5).
- Objects that must outlive a page (Main.qml's `ConfigSectionModel` for help
  links, its `ModeListModel`, `WindowPlacement`) are parented to the Main
  window, which lives for the app.
- Delegates: the object belongs to the delegate root; with `reuseItems`
  ListViews the object is reused with the delegate and its `Binding`s update
  it (ChangeModeAction's Repeater at line 122-131 is the one stage-1 case).
- Tray unload (S87) destroys the pages; their factory objects go with them.

### Guard

- `test/unit/test_qml_factory_guard.py`: scans `qml/`, `action_plugins/`,
  `theme/` like `tools/memory_probe.py:qml_made_types()`; fails on any
  `ta.QmlElement` type written as `TypeName {` in a QML file, except a
  `PENDING` set that holds stage-2 types and may only shrink (empty after
  stage 2). Also fails when a `ModelFactory.create("Name"` string names a
  type not in `QML_TYPES`.
- Optional runtime guard (question 4): converted types are registered with
  `qmlRegisterUncreatableType`, so a `TypeName {}` fails at load with "made
  by ModelFactory". Tests that build a type in a QML string
  (`test/unit/test_hardware_layout.py:351`) then move to the factory.
- `test/unit/test_leaks.py`: `counts()` also counts invalid wrappers
  (shells) and fails when converted types leave any; its comment
  ("C++ gone, no holder in Python") is corrected.

## 3. The six biggest holders: every creating QML site

| Holder (per use) | QML file:line |
|---|---|
| `HardwareLayoutModel` (~97 KB per Device Bindings open) | `qml/DeviceBindingsPage.qml:127` (also `readonly property alias layout: _layout` at :30) |
| `ConfigSectionModel` (~27 KB per Options open) | `qml/DialogOptions.qml:42`; `qml/Main.qml:301` (`_helpOptionLabels`, app lifetime) |
| `DeviceLiveState` (~6.7 KB) | `qml/DeviceBindingsPage.qml:160` (4 bindings); `qml/OutputModuleView.qml:210` (2 bindings) |
| `Device` | `qml/DeviceBindingsPage.qml:171` (`guid` binding) |
| `AxisCalibration` (~6.5 KB per Calibration open) | `qml/DialogCalibration.qml:374` (inline `model:` of a ListView, `moduleSlug` binding) |
| `TraceView` (~7.9 KB per Live Log open) | `qml/DialogLiveLog.qml:61` |
| `ModeListModel` (holds old profiles' mode trees) | `action_plugins/change_mode/ChangeModeAction.qml:65, 131 (Repeater delegate), 178`; `qml/DialogManageModes.qml:40` (property, read from Main); `qml/DialogAutoMappingTool.qml:164` (`onModelReset` handler); `qml/ScriptConfiguration.qml:153`; `qml/Main.qml:2232` |
| `InputIdentifier` per pane open (not a QML type) | made in Python: `gremlin/ui/device.py:413` (`Device.inputIdentifier`, called from `qml/DeviceBindingsPage.qml:195` `_noteCurrentInput`); same pattern `gremlin/ui/device.py:468`, `gremlin/ui/osc_device_model.py:897` |

Stage 1 converts **every** type in those ten QML files (question 6), so no
file is opened twice: also `EditLock` and `DeviceListModel`
(DeviceBindingsPage), `ModuleClaimedInputModel` (OutputModuleView),
`CalibrationModuleModel` (DialogCalibration), `LiveLog`, `DebugLog`,
`InputMonitor` (DialogLiveLog), `ModeHierarchyModel` (ChangeModeAction,
DialogManageModes), `AutoMappingToolInputModel`, `AutoMappingToolOutputModel`,
`Tools` (DialogAutoMappingTool), and in Main.qml `WindowPlacement:140`,
`ModuleListModel:491`, `DriversModel:1023`, `TraceSwitch:1435`,
`InputTesterLink:1441`, `EditLock:1740`.

## 4. The rest (stage 2): 55 QML files, grouped

Counted by script 2026-11-23: 81 types, 115 sites, 65 files; stage 1 takes
10 files, stage 2 the other 55.

| Group | QML files (types) |
|---|---|
| A. Device maps, pairing, viewer | DeviceMapCard (PairLiveThrottle, MappedButtonModel, MappedAxisModel, MappedHatModel, HardwareProfile), DevicePhotoHost (HardwareProfile), DialogConfigureModule (HardwareProfile, DriverInputModel), DialogDeviceMappingEditor (ViewerDeviceModel, HardwareProfile, ModuleFileWatch, DeviceMapOptions, DeviceMapSpaceKey, DeviceNames), DialogDevicePack (HardwareProfile), DialogInputViewer (ModulePairDeviceModel), InputViewerCard (ModulePairAxisModel, ModulePairButtonModel, PairLiveThrottle), OptionDeviceMapLibrary (DeviceMapOptions, HardwareProfile) |
| B. OSC | OptionOscModuleSetup (OscModuleSetupLink), OscAddDialog (OscSettingsInfo, OscBulkCapture), OscFeedbackSection (OscFeedbackModel), OscMonitorPanel (OscMonitorModel), OscOutputTab (OscCompanionCheck), OscPage (EditLock, WindowPlacement, OscLayoutModel, OscDeviceManagementModel), OscSetupTabs (OscServerModel), StatusCard (OscCardStatus), WindowOscMonitor (OscDeviceManagementModel) |
| C. Options widgets | OptionActionSequenceOrdering, OptionHighlightSpeed (HighlightSpeedModel), OptionLogLevel (LogLevelModel), OptionProfileAutoLoading (ProfileAutoLoadingModel, ProcessListModel), OptionStatusCards (CardSizes), OptionTTSVoiceSelection, OptionUiScale (UiScaleModel), OptionWindowsScale (WindowsScaleModel) |
| D. Input pages and pickers | KeyboardPage (EditLock, KeyboardLayoutModel, InputListenerModel), LogicalPage (EditLock, LogicalLayoutModel), InputConfiguration (EditLock), InputListener (InputListenerModel), LogicalDeviceSelector (LogicalDeviceSelectorModel), VJoySelector (OutputModuleDevices), AxesStateSeries (DeviceAxisSeries) |
| E. Tool windows | DialogDeviceInformation (DeviceListModel), DialogHardwareHide (HidHideModel), DialogHealth (HealthModel), DialogHistory (HistoryModel), DialogResetDevices (ResetDevicesModel), DialogSaveDiagnostics (Diagnostics), DialogSearch (SearchModel), DialogXboxSetup (XboxSetupModel), WindowScreenSaverMode (ScreenSaverModeModel), WindowDrivers (DriversModel), StatusPage (DriversModel) |
| F. Shared pieces, placement | ActionPane, DialogHelp, ListAppearancePanel, PageAppearance, ToolWindowMemory (WindowPlacement), DebugFrame (DebugMode), FilePicker (FolderMemory) |
| G. Profile settings, Xbox | ProfileSettingsGeneral (ProfileSettingsModel, StartupModeModel), ProfileSettingsVJoy (VJoyInputOrOutputModel, OutputVJoyListModel), XboxDevice (XboxPadSectionsModel, XboxDriverStatus, WindowPlacement), XboxDriverCheck (XboxDriverStatus), XboxPadCard (XboxOutputListModel, XboxPadChipsModel, XboxPadLive) |

`WindowPlacement` (16 shells per page round) and `EditLock` (10) are small
each but the most numerous; F and the EditLock sites are worth doing early
in stage 2.

## 5. Split tables

Shared contract for both stages: section 2 (`ModelFactory.create(typeName,
parent, props)`, `QML_TYPES`, the seven QML rules, `PENDING` in the guard).
QML agents write to the contract at once; they can run their QML only after
S1-PY lands (about 5 min in), so they edit first and check after.

### Stage 1 (biggest holders)

| Agent | Files | Job | Why parallel / why one |
|---|---|---|---|
| S1-PY | `gremlin/ui/model_factory.py` (new), `gremlin/ui/type_aliases.py`, `joystick_gremlin.py`, `test/journeys/_harness.py` and other test engine helpers that need the import, `test/unit/test_model_factory.py` (new) | Registry in `ta.QmlElement`, singleton `ModelFactory.create`, ownership, main-thread check, registration at start; unit tests (parent set, props order, unknown name, Cpp ownership, freed with parent, no shell left) | Owns all shared Python; everyone else writes to its contract |
| S1-BIND | `qml/DeviceBindingsPage.qml` | 5 types incl. `HardwareLayoutModel`, `DeviceLiveState`, `Device`; alias `layout`; Instantiator's `DeviceListModel` | One file, biggest holder |
| S1-OUT | `qml/OutputModuleView.qml`, `qml/DialogCalibration.qml` | `DeviceLiveState`, `ModuleClaimedInputModel`; `AxisCalibration` (inline ListView model + `moduleSlug` Binding), `CalibrationModuleModel` | Own files |
| S1-LOG | `qml/DialogLiveLog.qml`, `qml/DialogOptions.qml` | `TraceView`, `LiveLog`, `DebugLog`, `InputMonitor` (colour props are constants from Style: props or Binding); `ConfigSectionModel` | Own files |
| S1-MODES | `action_plugins/change_mode/ChangeModeAction.qml`, `qml/DialogManageModes.qml`, `qml/DialogAutoMappingTool.qml`, `qml/ScriptConfiguration.qml` | Every `ModeListModel` / `ModeHierarchyModel` and the Auto Mapping models; Repeater delegate case; `onModelReset` to Connections | Own files; same pattern, one agent keeps it uniform |
| S1-MAIN | `qml/Main.qml` | 8 types (`ConfigSectionModel`, `ModeListModel`, `WindowPlacement`, `ModuleListModel`, `DriversModel`, `TraceSwitch`, `InputTesterLink`, `EditLock`) | 2672-line file, alone |
| S1-ID | `gremlin/ui/device.py`, `gremlin/ui/osc_device_model.py` | `inputIdentifier()` (device.py:413, 468; osc_device_model.py:897) stops growing per call (question 5); test on the real path (open the pane N times, `InputIdentifier` count flat) | Python files nobody else holds |
| S1-GUARD | `test/unit/test_qml_factory_guard.py` (new), `test/unit/test_leaks.py`, `test/unit/test_hardware_layout.py` and any other test pinning the old declarations (impact sweep by grep) | Guard with `PENDING` = stage-2 types; shell counting; end-to-end: Device Bindings, Options, Calibration, Live Log, Change Mode pane opened/closed N times, zero shells of converted types | Test-only, runs alongside |
| S1-MEASURE | `tools/memory_probe.py` | Optional one-window-at-a-time option for scenario D; after the batch, re-run the probe (~5 min, measured 2026-11-23) and write `memory-after-stage1.md` in the audit folder | Waits for the QML parts (staggered) |
| S1-DOCS | `claude/program-map/01-app-shell.md` (sections 2-5, 10 PYSIDE-WRAPPERS, 11), the section 2 entries of the pages that list the touched files (checked by grep: DeviceBindingsPage 01/02/05/06/08; DialogCalibration 03/08; OutputModuleView 03; DialogLiveLog 01; DialogOptions 01/04/08; ChangeModeAction 05; DialogManageModes 01/04; DialogAutoMappingTool 03/08; ScriptConfiguration 04/05/09), `claude/program-map/README.md` counts | New owner file on the map; gap text corrected (not harmless; being fixed in stages); tests listed | Docs own their files |

Left out: no Help page (nothing a user sees changes); no section 8
statement unless question 7 says so; upstream's ObjectLoader and the
9602a510 / 66bb2477 Python caches (question 8). Ten agents is the limit.

### Stage 2 (the rest)

| Agent | Files | Job | Why parallel / why one |
|---|---|---|---|
| S2-A | Group A (8 QML files) | Device map, pairing, viewer types | Own files |
| S2-B | Group B (9) | OSC types | Own files |
| S2-C | Group C (8) | Options widgets | Own files |
| S2-D | Group D (7) | Input pages, pickers, `LogicalDeviceSelector` (upstream's order trap: `validTypes` before the identifier, via props order) | Own files |
| S2-E | Group E (11) | Tool windows | Own files, small each |
| S2-F | Group F (7) | `WindowPlacement`, `DebugMode`, `FolderMemory` | Own files; most shells per round |
| S2-G | Group G (5) | Profile settings, Xbox | Own files |
| S2-GUARD | `test/unit/test_qml_factory_guard.py`, `test/unit/test_leaks.py`, tests pinning old declarations | `PENDING` emptied; uncreatable registration list complete (if question 4 a); end-to-end page and window rounds | Test-only |
| S2-MEASURE | `tools/memory_probe.py` | Re-run all scenarios A-E; `memory-after-stage2.md`; expected: no shells, private bytes flat block 1-3 | After the QML parts |
| S2-DOCS | Map pages owning the 55 files (section 2 lines), 01 gap PYSIDE-WRAPPERS closed, README counts, `claude/todo.md` | Map current, gap closed with the probe result | Docs |

Left out: a Python part, as no stage-2 type needs a factory change; if
question 8 is a, one more agent (S2-PY: `gremlin/ui/profile.py`,
`action_plugins/merge_axis/__init__.py`, `action_plugins/reference/__init__.py`,
`action_plugins/dual_axis_deadzone/__init__.py`, ported
`test_selection_model_reuse.py`) and S2-E/S2-G share no file with it, so it
can run alongside (11 agents: stagger S2-MEASURE).

## 6. Risks

1. **Binding behaviour changes.** A declarative property was applied before
   the object's first use; a `Binding` applies at completion. Where a change
   handler fires on first set (AxesStateSeries, LogicalDeviceSelector
   upstream), the first value goes in `props` or after the `Connections`.
   Each agent lists every converted binding in its report.
2. **Re-run factory calls.** A changing value inside the call makes a new
   object per change. Rule 3; reviewed by the lead's re-trace.
3. **Double free / early free.** With a parent and Cpp ownership, neither
   the JS collector nor Python frees it. Python code that stores the object
   (backend's current input) would hold a dead wrapper after the item goes:
   S1-ID and the agents grep for Python slots that keep a QObject argument.
4. **Delegates.** Parent the delegate root, never the view; a parent that
   is the view would keep one object per delegate ever made.
5. **Tests that build types in QML strings** break under the uncreatable
   registration (question 4 a); the guard agents update them.
6. **Ids used by child components** (inline `component` blocks in the same
   file) still resolve, as the property keeps the old id's name; an
   `id:` removed but referenced as `parent.x` from another file is a QML
   load error that the off-screen page tests catch.
7. **Growth outside the Python heap** (about 14-22 MB per block, cause
   unverified): only the probe after stage 1 shows whether it goes.

## 7. Effort (from `claude/timings.md`)

Per stage:

| Step | Figure | Source |
|---|---|---|
| 10 agents in parallel | ~10 min (5-10 min per agent) | timings.md: refactor, and "a batch of parallel agents ~10 min" |
| Lead checks, re-trace, map | ~5 min | timings.md end-to-end line |
| Quick tests (`--changed` + targeted + pyright baseline) | no timing row for this kind; rough guess 3-5 min | none |
| Build + silent install + live check | ~3-4 min | timings.md 2026-11-23 rows (build/test) |
| Probe re-run | ~5 min | memory.md (measured 2026-11-23); no timings.md row yet |
| Commit / push | ~2 min | timings.md end-to-end line |
| CI | ~25 min, in the background | timings.md: CI on a push (2026-11-23) |

Stage 1: about 28-31 min to pushed, plus CI ~25 min. Stage 2: the same,
about 28-31 min plus CI. Both: about 1 h of work plus two CI runs.

## 8. Questions for the user

1. **Factory shape.**
   - a) One `ModelFactory.create("TypeName", parent, props)` slot, fed by a
     registry our `ta.QmlElement` fills; a new type needs no factory edit.
     (recommended: 81 types, design-for-change rule)
   - b) One typed slot per type, as upstream (24 slots there; 81 here).
   Upstream: b.
2. **Name and place.**
   - a) `gremlin/ui/model_factory.py`, singleton `ModelFactory` in
     `Gremlin.UI`. (recommended: matches upstream)
   - b) A new name (`QmlFactory`), as not all 81 are models.
   Upstream: a.
3. **Live values from QML.**
   - a) `Binding { target; property; value }` objects; first value in
     `props` where order matters. (recommended: keeps bindings declarative)
   - b) `Component.onCompleted` plus `onXChanged` handlers.
   Upstream: b.
4. **Stopping new `TypeName {}`.**
   - a) Guard test plus converted types registered as uncreatable in QML,
     so the mistake fails at load. (recommended)
   - b) Guard test only.
   Upstream: neither.
5. **`InputIdentifier` per pane open** (`gremlin/ui/device.py:413`).
   - a) `Device` keeps one identifier per input index, dropped with
     `deleteLater()` when the device changes. (recommended: fixed number)
   - b) Keep `parent=self` per call, as upstream (grows per open).
   - c) No parent, JavaScript-owned (unsafe: the backend keeps it).
   Upstream: b.
6. **Stage 1 scope.**
   - a) Convert every type in the ten files that hold the big holders, so
     no file is touched twice. (recommended)
   - b) Only the six holders; the rest of those files in stage 2.
   Upstream: one commit for its 24.
7. **Spec.**
   - a) No section 8 statement; page 01 gap PYSIDE-WRAPPERS rewritten now,
     closed after stage 2 and the probe. (recommended: nothing a user sees
     changes)
   - b) Add a page 01 statement ("opening pages and windows again and again
     does not grow memory") with the probe-style test.
   Upstream: no spec.
8. **The other upstream memory fixes** (parent-held growth, not shells).
   - a) Port 9602a510's `OutputVJoyListModel` cache and 66bb2477's
     selection-model reuse in stage 2 (one extra agent). (recommended)
   - b) Leave them for later (to-do).
   - c) Also port `ObjectLoader` (9fb7147b).
   Upstream: all three.

## Answers (user, 2026-11-23: "all recommended, build stage 1")

1a one create("TypeName", parent, props) slot fed by the QmlElement
registry; 2a gremlin/ui/model_factory.py, ModelFactory (upstream's name);
3a Binding objects, first value in props where order matters; 4a guard test
+ converted types registered uncreatable in QML; 5a Device keeps one
InputIdentifier per input; 6a stage 1 converts every type in its 10 files;
7a no section 8 statement: PYSIDE-WRAPPERS gap text corrected now, closed
after stage 2 + probe; 8a port 9602a510 and 66bb2477 caches in stage 2.
CI only at the end of the whole run (user).

## Contract change for stage 2 (user, 2026-11-23: "Yes, and write it into the stage 2 contract.")

Rule 4 (changing values) is now two-way:
- Use a QML `Binding` object when the Python property is set only from QML
  and its notify signal fires only when that property changes.
- Use upstream's way instead — set the value in `Component.onCompleted` and
  again from the source's change handler (`onXChanged` / `Connections`) —
  when the Python object sends its own change signal for that property
  (a shared notify signal such as `changed` or `guidChanged`, a value it
  normalises or looks up again, a value that also follows program state).
  A `Binding` there logs "The target property of the Binding element … was
  changed from elsewhere" and fails test_qml_teardown_warnings.py.
- Where the cause is a shared notify signal in our Python, prefer fixing it
  at the cause (give the property its own signal, as FIX-LIVE did for
  DeviceLiveState.deviceName) and then use `Binding`.
Stage 1 examples: DeviceBindingsPage (DeviceLiveState, Device: handlers),
DialogLiveLog (theme colours: handlers), OutputModuleView (Binding, after
the deviceName signal fix).

## Stage 2 go (user, 2026-11-23: "a, build stage 2")

Split as in section 5 stage 2 plus S2-PY (caches, answer 8a) and S2-NATIVE
(read-only investigation of the growth outside the Python heap, answer a);
S2-MEASURE staggered after the QML parts. Stage 1 probe numbers: memory.md
"After stage 1" (Device Mapping Editor worst: 24 shells per open; most
numerous: WindowPlacement, DebugMode, FolderMemory, EditLock).

## Reference pick box (user, 2026-11-23: "approved as recommended")
With upstream's selection-model reuse (66bb2477, S2-PY), the Reference
editor's pick box keeps the picked entry when the editor's data changes
(before: it jumped back to the first entry). Kept, as upstream. No spec
statement covered the old behaviour (05 S57, S60, S60a).

## LogicalDeviceSelector pick (user, 2026-11-23: "approved as recommended")
Upstream's way: the selector emits logicalInputSelected(identifier) and never
writes its own logicalInputIdentifier, so outside bindings stay; Script,
Condition and Macro editors listen to the signal (agent FIX-LDS).

## Release batch (user, 2026-11-23: "approved as recommended", twice)
- S199 / D-01-RELEASE-UNUSED: release_unused(engine) after page unload /
  window close / tray hide (native-growth.md).
- Also fix the three small Python growths S2-MEASURE found (memory.md
  "After stage 2"): HardwareLayoutModel store listeners (hardware_layout.py
  444-492), the start-up qml_errors list (joystick_gremlin.py:1155, and which
  warnings they are), action_analysis._feedback_cache stale entries.
