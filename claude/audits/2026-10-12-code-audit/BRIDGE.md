# BRIDGE: Python <-> QML seam audit (agent BRIDGE, 2026-10-12, start 06:10, end 06:23)

Repo HEAD 203a74dd. Read-only: no repo file changed. Helper scripts and raw output are in `scratchpad/audit/bridge/`
(`scan.py`, `scan2.py`, `scan3.py`, `deadtable.py`, `probe_count.py`; `scan.json`, `scan2.json`, `scan2_blocks.json`,
`scan3.json`, `strict.json`, `pyonly.md`).

## What was collected and how
- Python, by abstract syntax tree (AST) parse of gremlin/, action_plugins/, dill/, vigem/, joystick_gremlin.py and
  input_tester.py: 591 Slots, 433 Properties (decorator and `QtCore.Property(...)` forms) and 241 Signals, 1,643 seam
  names on their classes; 114 `@QmlElement` classes; 10 `setContextProperty` calls (9 names); 144 model roles (`roles`
  dicts, `roleNames()`, plus the 19 ControlLayoutModel roles built from `ROW_DEFAULTS`, checked separately).
- QML/JavaScript (JS): 314 files (qml/, action_plugins/, theme/), comments stripped: 10,935 `x.name(` calls, 2,040
  `onName:` / `function onName()` handlers, all member reads, all bindings written inside a registered-type block.
- Qt's own names: 10,613 property/signal/method names from PySide6's 104 `.qmltypes` files, plus JS built-ins.
- Counted as uses: `.name` member access, `["name"]`, `onName` / `onNameChanged`, `name:` binding inside a registered
  type's block, bare-name use inside that instance's own block (checked by hand), Python `.name` and `"name"` strings
  (getattr, string connects), `notify=` targets, signal-to-signal forwarding (`x.connect(self.sig)`).
- Type-aware pass: 94 receivers whose Python class is known (context properties `backend`, `uiState`, `signal`,
  `updater`, `deviceLibrary`, `devicePhotoMaker`, `clickTrace`; ids of `@QmlElement` instances; `property <PyType> x`;
  chains through typed Properties) gave 1,172 member accesses, each checked against the class's exposed
  Slot/Property/Signal (Python base classes included) and the QAbstractItemModel invokables. 46 bindings/handlers
  written inside registered-type blocks were checked the same way.
- One PySide6-only off-screen probe (no program code, temp USERPROFILE, ended with os._exit): QML reading `.count` on a
  Python QAbstractListModel gives `undefined`, and `1 + undefined` assigned to an `int` property gives 0.

## (b) BROKEN: QML uses of names no Python type defines (high priority)

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| qml/DeviceMapCard.qml:31 `property int liveStamp: buttonStamp + axisStamp + hatStamp + _buttons.count + _axes.count + _hats.count` | read of a property the Python type does not have | `_buttons/_axes/_hats` are `MappedButtonModel/MappedAxisModel/MappedHatModel` (gremlin/ui/input_pairing.py:311-326; base `_MappedModel` :246 is a QAbstractListModel with only `guid`/`guidChanged`): no `count` Property. Probe: `m.count` is undefined; `1 + m.count` into an int is 0. | high | The sum is NaN, so `liveStamp` is always 0 and never changes. It feeds `VkbRigFace.liveStamp` (DeviceMapCard.qml:101), whose `onLiveStampChanged` pings the editor (VkbRigFace.qml:531; VkbRigEditor.qml:1425, 1964). The map card's face is therefore never told about live input or model changes through this stamp. Fix options for the lead: add a `count` Property (notify on reset/rows inserted/removed) to `_MappedModel`, or drop the counts from the sum. Spec page for the device map card should say how live input reaches the face. |

Nothing else found:
- 0 other typed member accesses to a name the class lacks.
- 0 QML calls to a Python method that exists but is not a Slot (every `.name` / `.name(` whose name is only a plain
  Python method/attribute was checked; the 8 hits are JS object keys such as `have.known`, `preview.listed`).
- 0 Connections handlers (typed targets) or in-block handlers for a signal the class lacks (`onModelReset` on
  ModeListModel / CalibrationModuleModel is Qt's own QAbstractItemModel signal).
- Untyped `.name(` calls whose name is defined nowhere: 128, all Canvas 2D context calls (`ctx.lineTo`, ...),
  `Number.fromLocaleString`, `String.fromCodePoint`, and `Style.helpLinks.reveal` (set in Main.qml:171). None broken.
- Limit (NOT VERIFIED): receivers declared `property var`, `modelData`, or function results are untyped; their member
  names were only checked as "defined somewhere" (weak). The typed pass covers the context properties and every
  `@QmlElement` id.

## (b2) Python signals QML depends on that Python never emits

Signals with a QML listener, or the `notify` of a Property QML reads, with no `.emit(`, no string use and no
signal-to-signal forward anywhere in program Python (17 candidates; 12 dropped after checking forwards such as
`_notifier().changed.connect(self.levelChanged)` and the Deadzone index dict):

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| gremlin/ui/device.py:146 `DeviceListModel.selectedIndexChanged` | notify never emitted | setter :270-272 sets `_selected_index` without emitting | medium | Any QML binding to `selectedIndex` never updates; no QML read of `DeviceListModel.selectedIndex` found, so latent. |
| action_plugins/condition/condition.py:304 `VJoyCondition.vjoyConditionChanged` | notify of vjoyDeviceId/InputId/InputType never emitted | setters :383-424 emit only `statesChanged`/`comparatorChanged` (via `_update_states`) | medium | ConditionAction.qml:322-326 reads them once in `Component.onCompleted`, so no visible stale value today. |
| gremlin/ui/profile.py:283 `InputItemBindingModel.virtualButtonChanged` | notify never emitted | the object is made once | low | Constant in practice; could be `constant=True`. |
| action_plugins/condition/comparator.py:48 `AbstractComparatorModel.typeChanged` | notify never emitted | `typeName` returns a class attribute | low | Constant; could be `constant=True`. |
| action_plugins/response_curve/__init__.py:245 `ResponseCurveModel.deadzoneChanged` | notify never emitted | `deadzone` is made lazily once | low | Constant in practice. |

The QML-emitted relays `signal.openOscPage` / `signal.openOscModuleSetupAt` (gremlin/signal.py:70,73) are emitted by
QML (OscFeedbackSection.qml:38, OscPage.qml:194) and handled in Main.qml:2134,2143: fine.

## (a) Dead seam: Slots / Properties / Signals with no use from QML or program Python

Rule: no `.name` / `["name"]` / handler / in-block binding in QML/JS, and no `.name` or `"name"` in program Python
besides its definition. Bare-name uses inside the instance's own block were then checked by hand, which removed
`DeviceAxisSeries.axisIdentifier` (AxesStateSeries.qml:36), `OscServerModel.messageFailed` (OscSetupTabs.qml:39) and
`AbstractCondition.conditionType` (DelegateChooser role, ConditionAction.qml:179). 43 remain: 5 dead, 38 used only by
tests. All 241 signals are used (each either has a listener/emit in Python or QML); no signal is in this table.

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| gremlin/input_tester/model.py:637 `InputTesterModel.reloadLog` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) | input tester log reload; tester QML never calls it |
| gremlin/ui/control_layout.py:1396 `ControlLayoutModel.selectionCount` | property | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) | listed in the module docstring (control_layout.py:16) only |
| gremlin/ui/hardware_layout.py:779 `HardwareLayoutModel.canRemoveRows` | property | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/hardware_layout.py:842 `HardwareLayoutModel.rowForDeviceIndex` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/hardware_layout.py:856 `HardwareLayoutModel.paneMode` | property | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) | paneKey is read by QML; paneMode only in a comment |
| gremlin/ui/hardware_profile.py:1009 `HardwareProfile.saveArea` | slot | no QML member/handler/binding use; no program-Python use; test refs 4 -> used only by tests | high (test-only) | QML uses saveAreaAsync (DialogDeviceMappingEditor.qml:2719); the sync Slot is test-only |
| gremlin/ui/hardware_profile.py:1391 `HardwareProfile.peekPackDevice` | slot | no QML member/handler/binding use; no program-Python use; test refs 4 -> used only by tests | high (test-only) |  |
| gremlin/ui/hardware_profile.py:2262 `HardwareProfile.removeUnusedPictures` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/hardware_profile.py:2271 `HardwareProfile.pictureMissing` | slot | no QML member/handler/binding use; no program-Python use; test refs 5 -> used only by tests | high (test-only) | 07 S108 placeholder is decided in RigDrawItem.qml:482 by its own `missing` binding; the Slot is test-only |
| gremlin/ui/hardware_profile.py:2297 `HardwareProfile.beginEdit` | slot | no QML member/handler/binding use; no program-Python use; test refs 12 -> used only by tests | high (test-only) |  |
| gremlin/ui/hardware_profile.py:2313 `HardwareProfile.editActive` | slot | no QML member/handler/binding use; no program-Python use; test refs 13 -> used only by tests | high (test-only) |  |
| gremlin/ui/hardware_profile.py:2381 `HardwareProfile.stashPhotoFor` | slot | no QML member/handler/binding use; no program-Python use; test refs 0 -> dead (no test use either) | high | Comment: Module Setup's names 'until that window uses them' - wrappers of beginEditFor/cancelEditFor/commitEditFor, never wired |
| gremlin/ui/hardware_profile.py:2385 `HardwareProfile.restorePhotoFor` | slot | no QML member/handler/binding use; no program-Python use; test refs 0 -> dead (no test use either) | high | same wrapper set, never wired |
| gremlin/ui/hardware_profile.py:2389 `HardwareProfile.dropPhotoStashFor` | slot | no QML member/handler/binding use; no program-Python use; test refs 0 -> dead (no test use either) | high | same wrapper set, never wired |
| gremlin/ui/hidhide.py:830 `HidHideModel.saveWindowSize` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/history_model.py:1167 `HistoryModel.rowOf` | slot | no QML member/handler/binding use; no program-Python use; test refs 3 -> used only by tests | high (test-only) |  |
| gremlin/ui/module_calibration.py:86 `CalibrationModuleModel.indexOfSlug` | slot | no QML member/handler/binding use; no program-Python use; test refs 3 -> used only by tests | high (test-only) |  |
| gremlin/ui/module_inputs.py:238 `ModuleClaimedInputModel.rowForDeviceIndex` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/module_model.py:1178 `ModuleListModel.moveSlugBefore` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/module_model.py:1378 `ModuleListModel.stepCount` | property | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/module_model.py:1872 `ModuleListModel.claimedCount` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/option.py:338 `ConfigSectionModel.scope` | property | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) | ConfigSectionModel instances (DialogOptions.qml:42, Main.qml:278) never set scope; its docstring (option.py:309) says the Device Mapping Editor shows a section by scope - check spec: gap or dead |
| gremlin/ui/option.py:464 `ConfigGroupModel.sectionName` | property | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:741 `OscDeviceManagementModel.encAccelChoices` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:780 `OscDeviceManagementModel.listenForInput` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:861 `OscDeviceManagementModel.companionText` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:871 `OscDeviceManagementModel.inputSettings` | slot | no QML member/handler/binding use; no program-Python use; test refs 9 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:894 `OscDeviceManagementModel.changeName` | slot | no QML member/handler/binding use; no program-Python use; test refs 5 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:903 `OscDeviceManagementModel.clearAllInputs` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:911 `OscDeviceManagementModel.sortInputs` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_device_model.py:917 `OscDeviceManagementModel.deleteInput` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_feedback_model.py:449 `OscFeedbackModel.rowById` | slot | no QML member/handler/binding use; no program-Python use; test refs 3 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_feedback_model.py:457 `OscFeedbackModel.setRowEnabled` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_feedback_model.py:461 `OscFeedbackModel.setRowValueById` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_feedback_model.py:465 `OscFeedbackModel.removeRowById` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_feedback_model.py:469 `OscFeedbackModel.duplicateRow` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_feedback_model.py:483 `OscFeedbackModel.addRowFor` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_feedback_model.py:501 `OscFeedbackModel.actionMissing` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/osc_layout.py:1253 `OscLayoutModel.encAccelChoices` | slot | no QML member/handler/binding use; no program-Python use; test refs 1 -> used only by tests | high (test-only) |  |
| gremlin/ui/profile.py:1070 `ModeHierarchyModel.modeStringList` | slot | no QML member/handler/binding use; no program-Python use; test refs 2 -> used only by tests | high (test-only) |  |
| gremlin/ui/vjoy_status.py:143 `VJoyStatus.setPinned` | slot | no QML member/handler/binding use; no program-Python use; test refs 3 -> used only by tests | high (test-only) |  |
| gremlin/ui/vjoy_status.py:170 `VJoyStatus.activeCount` | property | no QML member/handler/binding use; no program-Python use; test refs 0 -> dead (no test use either) | high | no use anywhere, tests included |
| gremlin/ui/vjoy_status.py:171 `VJoyStatus.pinStamp` | property | no QML member/handler/binding use; no program-Python use; test refs 0 -> dead (no test use either) | high | no use anywhere, tests included |

Grouped reading of the table:
- OscDeviceManagementModel (osc_device_model.py:741-917, 8 Slots) and OscFeedbackModel (osc_feedback_model.py:449-501,
  7 Slots): a whole older editing surface (rename, delete, sort, clear, settings, feedback-row editing) that the OSC
  page no longer calls; only tests drive it. Likely superseded by OscLayoutModel. Medium-size removal candidate.
- HardwareProfile: `stashPhotoFor` / `restorePhotoFor` / `dropPhotoStashFor` (:2381-2391) are dead with no tests;
  `beginEdit`, `editActive`, `saveArea`, `peekPackDevice`, `removeUnusedPictures`, `pictureMissing` are test-only.
- VJoyStatus `activeCount` / `pinStamp` (vjoy_status.py:170-171): dead, no tests. `setPinned` test-only.
- ConfigSectionModel.scope (option.py:338): test-only, but its docstring describes a Device Mapping Editor use; treat as
  a possible spec gap, not just dead code (lead to check the Options spec page).

Signals note: no Signal is unreferenced by this seam scan, but "referenced" includes `notify=`. Signals that are never
emitted and never listened to on the Python side are in `scratchpad/audit/signals.txt` (another agent); not repeated.

## (c) Model roles never used in any delegate

Searched every role name as a word in all QML/JS (comments stripped), which covers `model.role`, bare `role` in
delegates, `required property <type> role`, and `role: "name"` strings.

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| gremlin/ui/device.py:289 `Device` role `actionSequenceCount` | role | 0 QML/JS uses | high | Test refs 2. Same role also on the two models below. |
| gremlin/ui/module_inputs.py:24 `ModuleClaimedInputModel` role `actionSequenceCount` | role | 0 QML/JS uses | high | Test refs 2. |
| gremlin/ui/osc_device_model.py:623 `OscDeviceManagementModel` role `actionSequenceCount` | role | 0 QML/JS uses | high | Test refs 2. |
| gremlin/ui/module_inputs.py:28 `ModuleClaimedInputModel` role `deviceIndex` | role | 0 QML/JS uses | high | Test refs 8; pairs with the test-only Slot `rowForDeviceIndex`. |
| gremlin/ui/profile.py:673 `InputItemModel` role `fake` | role | 0 QML/JS uses | high | Placeholder role name; data() likely ignores it. |
| gremlin/ui/profile.py:1490 `ProfileDeviceListModel` roles `nameAndActions`, `uuid` | role | 0 QML/JS uses | high | The whole class is unused, see (e). |
| gremlin/ui/control_layout.py:296 `ControlLayoutModel` role `indent` (from `ROW_DEFAULTS`) | role | 0 QML/JS uses (the `indent` in ContextMenu.qml:371 is a JS object key) | high | 18 of the 19 ROW_DEFAULTS roles are used; why QML does not read `indent` was not checked. |

The other roles each have at least one QML/JS use (144 literal roles scanned, plus the 19 ControlLayoutModel roles
built from `ROW_DEFAULTS`, control_layout.py:281/309, checked separately).

## (d) Context properties

| Name | Set at | QML uses | Verdict |
|---|---|---|---|
| backend | joystick_gremlin.py:1167; input_tester.py:55 (set to None) | 164 words | used |
| uiState | joystick_gremlin.py:1168 | 186 | used |
| signal | joystick_gremlin.py:1169 | 170 | used |
| updater | joystick_gremlin.py:1171 | 44 | used |
| deviceLibrary | joystick_gremlin.py:1176 | 8 | used |
| devicePhotoMaker | joystick_gremlin.py:1184 | 2 | used |
| clickTrace | gremlin/ui/click_trace.py:507 | 20 | used (ONE-TIME code, tracker OT-5) |
| errorString | joystick_gremlin.py:1047 | 6 (MainFailure.qml) | used |
| tester | input_tester.py:56 | 129 | used |

Set but never used: none. Used but never set: none found. Method: every lower-case identifier used as a member
receiver (`x.`) in QML/JS that is not an id, a declared property/function/var/parameter, an import alias, a Qt or JS
global was listed (212 names); after removing words inside strings (help text) and JS function parameters
(e.g. `anchorItem`, `userFeedback`, `cp_handle`, `evt`, `hooks`), only the 9 names above remain.

## (e) Registered types (`@QmlElement`) never named in QML

114 `@QmlElement` classes; 26 never appear by name in QML/JS. Most are created in Python and handed to QML (the
registration only gives QML their type info), so they are not dead:
- Created in Python, used in QML as values (not dead): `UIState` (context property), `InputIdentifier`,
  `OutputVJoyInitialValuesModel` (profile.py:1350), the 13 script variable models (gremlin/ui/script.py:30-400),
  `StatusResetModel` (shell_option.py:88 option table), the comparator models (condition/comparator.py:69-136) and the
  condition classes (condition/condition.py:301-821).

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| gremlin/ui/profile.py:1485 `ProfileDeviceListModel` | QML-registered class | 0 QML/JS uses, 0 program-Python uses besides the class line; only test refs (2) and a stale build copy `dist/.../qml/DialogSwapDevices.qml:56` (that QML file no longer exists in qml/) | high | Dead class (Swap Devices dialog was removed). The program map still lists it: claude/program-map/04-profile-modes.md:16 ("ProfileDeviceListModel (Swap Devices list)") and :108 (models reset on profile change) - stale map lines for the lead/SPEC agent. |

## Appendix: Slots/Properties used only from Python (not dead; the Slot/Property decorator is not needed for QML)

78 entries (68 Slots, 10 Properties) with no QML use but with program-Python uses; most are cross-thread queued
Slots (`_deliver`, `_send`, `process_event`), which do need `@Slot`. Full list: `scratchpad/audit/bridge/pyonly.md`.
Not a defect; listed so the lead can decide whether any Property is QML-facing by mistake.

## Not verified
- Untyped receivers (`property var`, `modelData`, function results): member names checked only against "defined
  somewhere".
- Python classes not registered with `@QmlElement` but passed to QML as `QObject` values: their members were checked
  only when reached through a typed Property chain.
- Plugin QML registered at run time by `plugin_manager.py:210` (`qmlRegisterType`): plugin classes were scanned like the
  rest, but the run-time registered names were not resolved.
