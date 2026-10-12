# QML-REFS: unused QML/JS components, functions, properties, signals, ids

Agent QML-REFS, 2026-10-12, start 06:10, end 06:45. Repo HEAD 203a74dd. Read-only: no repo file changed; nothing run but two static scanners (no program code, no Qt).

Scope: every .qml/.js under qml/ (incl. qml/tester, qml/help) and theme/ (Gremlin/Base, Gremlin/Compact, Gremlin/Menus, GremlinStyle): 232 QML + 52 JS files.
Users searched: qml/, theme/ (incl. qmldir), action_plugins/ (.qml/.py), gremlin/, joystick_gremlin.py, input_tester.py. test/ (.py/.qml/.js) counted separately as "test-only".
Comments were blanked before matching (strings kept, so JS strings, Python `invokeMethod`/`property("x")` strings and smoke-test `w.js("...")` strings count as uses).

Scripts (scratchpad/audit/qml-refs/): `scan.py` (components, functions, first property/signal/id pass), `refine.py` (second pass: global member reads `.x`, `Style.x`, `bsi.icons.x`, `onXChanged`, Python `"x"` strings, binding vs ternary colon, alias writes). Raw outputs: components.txt, functions.txt, props2.json, signals2.json, ids.txt.

## How uses were counted

- **Component use**: unqualified `Type {` (a qualified `Compact.Type {` counts only for the module type, not a same-named qml/ file), `property Type x`, attached `Type.x:`, `"Type.qml"` strings (Helpers.createComponent, Qt.createComponent, Loader `source`, Registry/windowOf keys), Python `resource_path("qml/Type.qml")`, qmldir registration plus a real use through the import alias (`import Gremlin.Compact as Compact` then `Compact.Type {`), and same-directory implicit use inside a module folder. GremlinStyle files count as used when the Controls type is instantiated anywhere (QT_QUICK_CONTROLS_STYLE=GremlinStyle, joystick_gremlin.py:106, input_tester.py:65).
- **Function use**: any `name` occurrence that is not its `function name(` definition and not the forwarder line itself (`function x() { return RigX.x() }`), searched first in the file's scope (itself, its users, its JS code-behind), then globally (bare `x(`, `ed.x(`, `face.x(`, `host.x(`, `"x"` strings). Names starting `onX` were skipped (Connections handlers, called by Qt).
- **Property read**: own-file read (incl. `_root.x`), any `.x` read in QML/JS (not `.x =` / `.x: value` binding), `onXChanged`, a Python `"x"` string; `Style.x` for the Style singleton; `bsi.icons.x` for BootstrapIconsNames. Writes through a `property alias` count as a use; `default property` skipped.
- **Signal**: emitted = `x(`/`.x(` other than its declaration; handled = `onX`, `.x.connect`, or `signal: obj.x` (DSM.SignalTransition).
- **id**: referenced anywhere else in its own file or in a JS code-behind file it imports.

Limits: same-named members (e.g. `describe`, `pick`, `open`) can hide a dead one (the scan is name-based, not type-aware), so the lists below are a floor, not a ceiling. Nothing was executed; the EXERCISE agent's run is the dynamic check.

## Counts

| Kind | Dead (no program or test use) | Used only by tests |
|---|---|---|
| QML component files | 5 (+6 GremlinStyle controls never instantiated, medium) | 0 |
| JS files | 0 | 1 (qml/help_topics.js) |
| Functions | 31 (11 editor forwarder + JS body pairs = 22 defs, 9 others) | 29 (incl. 3 forwarder + JS pairs) |
| Properties | 30 | 7 |
| Signals | 2 | 0 |
| ids (unreferenced in own file) | 71 | 23 (+38 whose name only appears in other files, low) |

## 1. Components never instantiated or loaded

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| qml/ButtonStateSelector.qml:1 | QML component | No unqualified `ButtonStateSelector {`, no `"ButtonStateSelector.qml"`; all 7 uses are `Compact.ButtonStateSelector` (Comparator.qml:31, MacroAction.qml:280..659), which resolves to theme/Gremlin/Compact/ButtonStateSelector.qml | high | Older copy of the Compact one (differs only by `ComboBox` vs `Compact.ComboBox`). Last touched 3e190be0 |
| qml/HatDirectionSelectorV2.qml:1 | QML component | Only use is `Compact.HatDirectionSelectorV2` (Comparator.qml:86) → theme/Gremlin/Compact copy | high | Older copy (uses IconCheckBox instead of Compact.CheckBox). IconCheckBox stays used by qml/HatDirectionSelector.qml |
| theme/Gremlin/Base/RecordButton.qml:1 | QML component (qmldir `Gremlin.Base`) | Every RecordButton use is `Compact.RecordButton` (InputListener.qml:87, MacroAction.qml:167/172, MergeAxisAction.qml:187/209); no unqualified `RecordButton {` in any of the 19 files that `import Gremlin.Base` unqualified | high | Drop its qmldir line with it |
| theme/Gremlin/Compact/Button.qml:1 | QML component (qmldir) | No `Compact.Button {` anywhere (only in theme/Gremlin/Compact/AGENT.md:102 as an example); no sibling use | high | Docs example only |
| theme/Gremlin/Compact/ItemDelegate.qml:1 | QML component (qmldir) | No `Compact.ItemDelegate`, no sibling use | high | |
| theme/GremlinStyle/Menu.qml, MenuBar.qml, MenuBarItem.qml, MenuItem.qml, MenuSeparator.qml | Style controls | No plain `Menu {`/`MenuItem {`/`MenuBar {`/`MenuSeparator {` in qml/, theme/Gremlin, action_plugins; test/unit/test_menus.py:21 forbids them (all menus are Gremlin.Menus Themed*); text fields' context menus are replaced with Menus.TextEditMenu (GremlinStyle TextField/TextArea/SpinBox/ComboBox) | medium | Qt 6.11 may still build its own default menus from the style in a place not overridden; check before removing. Remove their qmldir lines too |
| theme/GremlinStyle/ScrollIndicator.qml | Style control | No `ScrollIndicator` anywhere in program QML | medium | Universal fallback would be used if ever needed |

Kept (looked dead, are used): Compact/Label.qml and Compact/RoundButton.qml (used unqualified by Compact/RecordButton.qml, which imports no Controls); Menus/ThemedMenuBarItem.qml (delegate in ThemedMenuBar.qml:18); GremlinStyle/impl/*Indicator.qml (CheckBox/RadioButton/Switch).

### JS files

| Item | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| qml/help_topics.js:1 | JS file | No `import "help_topics.js"` or string anywhere in program code; header says "Old entry points over the Help book" | high (dead in program) | **Test-only**: test/unit/test_help_topics_script.py loads it; test_help_guide.py:185 names it. Remove with that test |

## 2. Functions never called

### Dead: no program or test use

Rig editor forwarder + code-behind pairs (both the VkbRigEditor.qml forwarder and the rig_*.js body are unused; no `ed.x(`, `_ed.x(`, bare `x(` in any rig_*.js, no string):

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| qml/VkbRigEditor.qml:337 innerPageRect + qml/rig_coords.js:23 | forwarder + JS | word search: only def + forwarder line | high | |
| qml/VkbRigEditor.qml:434 pathPts + qml/rig_leaders.js:185 | forwarder + JS | same | high | |
| qml/VkbRigEditor.qml:504 themeCell + qml/rig_groups.js:388 | forwarder + JS | same | high | |
| qml/VkbRigEditor.qml:507 resetFiveWayFormat + qml/rig_groups.js:422 | forwarder + JS | same | high | |
| qml/VkbRigEditor.qml:520 setGroupKind + qml/rig_groups.js:817 | forwarder + JS | same | high | |
| qml/VkbRigEditor.qml:614 shapeOutlinePts + qml/rig_draw.js:294 | forwarder + JS | same | high | |
| qml/VkbRigEditor.qml:665 leaderHidden + qml/rig_layers.js:501 | forwarder + JS | same | high | |
| qml/VkbRigEditor.qml:667 layerFlagInherited + qml/rig_layers.js:532 | forwarder + JS | same | high | |
| qml/VkbRigEditor.qml:738 isPathTool + qml/rig_path.js:18 | forwarder + JS | same | high | |

Other functions:

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| qml/VkbRigEditor.qml:1363 ctxHasSpines | function | only its definition in repo (incl. tests, rig_menu.js strings) | high | context-menu helper left over |
| qml/VkbRigEditor.qml:1388 ctxSpineCurved | function | same | high | |
| qml/VkbRigEditor.qml:1413 ctxIsLeader | function | same | high | |
| qml/VkbRigEditor.qml:1417 ctxHasMapItem | function | same | high | |
| qml/VkbRigFace.qml:84 viewOffScreen | function | same | high | |
| qml/ConfigSection.qml:115 anyMatch | function | same | high | |
| qml/DialogDeviceMappingEditor.qml:68 ownFileChange | function | same | high | |
| qml/Style.qml:10 removeAlpha | function (singleton) | no `Style.removeAlpha` / `removeAlpha` anywhere | high | |
| theme/Gremlin/Menus/commands.js:219 defineFromMenuBar | JS function | no `Commands.defineFromMenuBar` / word anywhere | high | |
| qml/LogicalPage.qml:67/69/71/77 _toggleOpen, _toggleGroup, _select, _closePane | forwarders to `_tree`/`_pane` | only their definitions | high | siblings _openPane/_openNewPane/_finishClose are used |
| theme/Gremlin/Menus/menu_model.js:68 pick | JS function | no `MenuModel.pick(`; every other `pick(` in qml/ is a different local function (DialogHistory, ListAppearancePanel, OutputModuleView, _choosePictureDialog) | medium-high | name collision hid it from the first pass |

### Used only by tests (test smokes call them by JS string)

| Item (file:line) | Kind | Test users | Notes |
|---|---|---|---|
| qml/VkbRigEditor.qml:366 snapPx + rig_snap.js:16 | forwarder + JS | ps_match_smoke.py | |
| qml/VkbRigEditor.qml:745 cancelPath + rig_path.js:127 | forwarder + JS | dme_audit_fix_sel_smoke.py | |
| qml/VkbRigEditor.qml:831 _chipsItem | forwarder | chip_drop_centre_smoke.py, device_mapping_editor_fixes_smoke.py, planes_editor_smoke.py | |
| qml/VkbRigEditor.qml:828 menuLines, 832 menuRowRect, 833 menuBox | test probes | rc_e2e_smoke.py, rig_editor_harness.py | probe helpers by design |
| qml/RigLayersPanel.qml:186 revealedRow, 780 kindButton, 786 clearButton, 788 rowMenuLines, 789 rowMenuRect, 801 flagButton, 805 litKinds, 812 searchFieldText, 813 searchHasFocus, 814 searchSelected, 815 rowLook, 824 clippedParts | test probes | layers_panel_search_smoke.py, planes_layers_panel_smoke.py, rc_*_smoke.py, device_mapping_editor_shared_pieces_smoke.py | 12 probe functions |
| qml/RigPropsPanel.qml:247 describe, 262 fieldRect | test probes | rig_editor_harness.py | |
| qml/ShortcutList.qml:124 describe | test probe | device_mapping_editor_menubar_smoke.py | |
| theme/Gremlin/Menus/CommandPalette.qml:61 describe | test probe | menus_smoke.py | |
| theme/Gremlin/Menus/ContextMenu.qml:447 activate | test probe | device_library_CU_menus_smoke.py (`_rowMenu.activate(...)`) | |
| qml/RigDrawItem.qml:469 pictureInfo | test probe | device_mapping_editor_testlist_smoke.py, planes_menus_props_smoke.py | |
| qml/DialogDeviceMappingEditor.qml:2568 selectAllNow | function | side_panels_window_smoke.py | |
| qml/ConfigGroup.qml:186 _child | function | test_batch2_b3_typing.py and 2 more | |
| qml/help_links.js:24 allowedOpen | JS function | test_help_links.py | |
| qml/help_topics.js:14 deviceMappingEditorTopics, 18 deviceLibraryTopics (and the whole file) | JS | test_help_topics_script.py | see section 1 |
| theme/Gremlin/Menus/commands.js:46 removeOwner, 228 countOwner | JS | test_final_01.py, device_mapping_editor_lifecycle_smoke.py | |

## 3. Properties and signals

### Properties never read (dead)

"w" = number of writes (`x: value` binding or `x = ...`) found; w>0 means write-only state.

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| qml/StatusPage.qml:81 stackCandidate, :84 pendingStackW, :85 pendingStackH, :88 stackTravel | property (w=1-2) | only reset/assigned (343-384, 331); never read | high | leftover stack-gesture state |
| qml/VkbRigEditor.qml:188 armRenameId, :189 armRenameMember | property (w=2+) | assigned in RigPointerArea.qml:894-905, rig_selection.js:594, VkbRigEditor.qml:1327; never read | high | write-only |
| qml/VkbRigEditor.qml:209 lineArm | property (w=2+) | set in RigPointerArea.qml (414, 594, 681, 780) and 1202; never read | high | write-only (lineArmX/Y are read) |
| qml/VkbRigEditor.qml:184 worldSpace | readonly property | no reads anywhere | high | |
| qml/DialogDeviceMappingEditor.qml:154 fittedOldPage | property | declaration only | high | |
| qml/DialogDeviceMappingEditor.qml:160 selectedNode | property (w=4) | only `selectedNode = ...` (470, 755, 906, 1221) | high | write-only |
| qml/DialogDeviceMappingEditor.qml:3073 _templateMsg | property | declaration only | high | |
| qml/DialogConfigureModule.qml:38 moduleFileError | property (w=1) | set at 315, never read | high | |
| qml/Main.qml:2189 onConfig | property | declaration only (sibling onStatus is read) | high | |
| qml/TextInputDialog.qml:37 _committed | property (w=2) | set 67/90, never read | high | |
| qml/HelpSearchBar.qml:39 topicCount | readonly property | no reads | high | |
| qml/InputConfiguration.qml:17 inputIndex, :31 editorPad | property | declaration only | high | editorPadRight/Bottom are read |
| qml/InputConfiguration.qml:19 holdModel | property (w=1) | set `holdModel: true` at ActionPane.qml:319, never read | high | write-only |
| qml/InputItemBinding.qml:24 headerWidget | property | declaration only | high | |
| qml/InputItemBindingConfigurationHeader.qml:22 dragHandleArea | property | declaration only | high | |
| qml/OutputModuleView.qml:173 btnCellW | readonly property | declaration only | high | |
| qml/OscPage.qml:33 addWindow | readonly alias | no reads (WindowOscMonitor.qml:28 has its own addWindow, also never read) | high | WindowOscMonitor.addWindow (w=1) same |
| qml/DeviceBindingsPage.qml:39 _collapsed, qml/LogicalPage.qml:40 _collapsed | alias | declaration only (the `_collapsed` hits in gremlin/device_library.py are a different Python function) | high | |
| qml/IconButton.qml:10 backgroundColor | alias | no IconButton sets/reads it (AxesStateSeries.qml:102 `backgroundColor:` is a ChartView's own property, checked) | high | |
| qml/Style.qml:164 decimalsStandard | singleton property | no `Style.decimalsStandard` | high | decimalsPrecise is used |
| qml/BootstrapIconsNames.qml:28 bullet_point, :51 hat_c | icon names | no `icons.bullet_point` / `icons.hat_c` | high | `chart` (:22) appears only in test_clock_use.py text (unrelated word) - also dead |
| theme/Gremlin/Compact/CheckBox.qml:23 useSystemFocusVisuals | property (w=1) | never read inside Compact/CheckBox | medium | copied from Qt Universal; other style copies read theirs |

### Properties read only by tests

| Item (file:line) | Test users | Notes |
|---|---|---|
| qml/KeyboardPage.qml:32 layoutModel | test_audit3_screens.py, test_batch2_b5a_screens.py | |
| qml/OscMonitorPanel.qml:71 rowMenu | test_osc_batch3_qml.py | |
| qml/OscPage.qml:32 monitorPanel | osc_page_companion_smoke.py | |
| qml/VkbRigEditor.qml:1122 stepWaiting | device_mapping_editor_fixes_smoke.py, rig_editor_harness.py | |
| qml/WindowDeviceLibrary.qml:43 messageBad | device_library_CU_menus_smoke.py, library_remove_error_smoke.py | |
| qml/DialogLibraryCopy.qml:34 planned (w=3) | device_library_LU_window_smoke.py, test_device_library_FM2_threads.py | program only writes it |
| qml/StatusPage.qml:530 _deleteCanPack (w=1) | test_batch2_b3.py | program only writes it |

### Signals

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| qml/DeviceBindingsPage.qml:112 moduleSetupRequested | signal | emitted at 115; no `onModuleSetupRequested`, no `.connect`, no Python/test reference | high | openModuleSetup() then opens Module Setup itself through the window, so the signal is a no-op |
| qml/ErrorDialog.qml:19 rejected | signal | never emitted; no handler on an ErrorDialog (Main.qml:1385 instance has none; FilePicker.qml's onRejected is a FileDialog's) | high | `accepted` (:18) is emitted and used |

All other declared signals have an emitter and a handler (Connections `function onX`, `onX:`, `.connect`, or `signal: obj.x` in InputListener.qml's state machine). VkbRigEditor's 17 request signals are emitted in rig_*.js and handled in DialogDeviceMappingEditor.qml.

## 4. ids never referenced in their own file

Harmless (an unused `id:` costs nothing), but they are noise; listed for the clean-up batch. "No use" = no reference in own file, its imported JS, any other program file, or tests.

**No use anywhere (71):** ActionNode.qml:186 _headerLabel; ConfigGroup.qml:216 _pathVariable, :269 _stringField; DebugFrame.qml:71 _badge; DeviceList.qml:112 _physicalInputs; DialogCalibration.qml:456 _progressRaw, :466 _progressCalibrated; DialogDeviceInformation.qml:115 _outer; DialogDeviceMappingEditor.qml:3366 _templateMenu, :3991 _poolSearch, :4401 _poolCatch, :4849 _poolGhost; DialogDevicePack.qml:750 _exportRow; DialogHardwareHide.qml:202 controlSwitch, :211 cloakSwitch, :222 startSwitch, :368 _gamingOnly, :454 _noDevices, :552 hideSwitch, :622 allowList, :633 blockList, :654 _games, :709 _noPrograms; DialogHelp.qml:533 _full, :559 _listPane; DialogHistory.qml:473 _newBar; DialogLibraryTidy.qml:127 _remove; DialogLiveLog.qml:411 _liveButton, :586 _clearDebug, :650 _monitorFind; DialogUpdate.qml:131 _notesView; HelpSearchBar.qml:182 _scopeLoader; InputConfiguration.qml:76 _inlineRepeater, :104 _listView; InputItemBinding.qml:67 _action_node, :87 _sequenceDrop; InputItemBindingConfigurationHeader.qml:35 _treatRow, :215 _behaviorAxisButton; InputListener.qml:39 _stateMachine; InputViewerCard.qml:307 _vjHover; Main.qml:1693 _toolbar, :1823 _modeBar, :1917 _modeBarDivider, :1996 _savedHover, :2184 _columnLayout; OptionProfileAutoLoading.qml:97 _dialogContent; OscMonitorPanel.qml:179 _filter; PrintExportWindow.qml:248 _paper, :321 _pan, :383 _paperBox, :412 _marginBox, :474 _scaleBox; RigDrawItem.qml:57 _tableFace; RigLayersPanel.qml:379 _kindFlow; ScriptConfiguration.qml:375 _marker; StatusCard.qml:238 _boundHover, :406 _east, :425 _south; StatusPage.qml:937 _piles, :1021 _memberCards, :1076 _float; VkbRigFace.qml:463 _spacePan; WindowDeviceLibrary.qml:779 _settingsMenu, :1311 _deleteButton, :1365 _lastChange; XboxViewerCard.qml:101 _faces, :217 _xbHover; tester/InputTester.qml:712 _buttonsLabel; theme/Gremlin/Menus/CommandPalette.qml:77 _fieldBox; theme/GremlinStyle/impl/RadioIndicator.qml:25 checkOuterEllipse, :38 checkGlyph (all paths under qml/ unless shown).

**Referenced only by tests (23)** (smokes reach ids through `w.js("...")`): ConfirmDialog.qml:105 _go; DialogDeviceMappingEditor.qml:716 _recoveryTimer, :3485 _bgMenu, :3914 _leftSlot, :4419 _rightSlot, :4533 _statusLine; DialogHardwareHide.qml:463 _devs; DialogHelp.qml:540 _only, :750 _handle; DialogLiveLog.qml:385 _clearConfig, :478 _debugFind, :621 _saveDiagnostics; DialogSaveDiagnostics.qml:90 _result; Main.qml:1962 _footer, :2325 _configTitle; PrintExportWindow.qml:292 _crop, :305 _preview; StatusCard.qml:444 _corner; UndoBar.qml:34 _undo, :50 _redo; WindowDeviceLibrary.qml:718 _undoItem, :729 _redoItem, :1078 _nameLabel. Keep these: the tests need them.

**Low confidence (38)**: not referenced in their own file, but the same name appears in another file (often a different id with the same name, sometimes a child reaching it through QML's dynamic scope). Full list in scratchpad/audit/qml-refs/ids.txt (rows with a non-empty 4th field), e.g. DialogConfigureModule.qml:567 _undoBar, WindowDeviceLibrary.qml:692-784 menu ids, SidePanel.qml:259 _grip.

## Fifteen most important items

1. qml/ButtonStateSelector.qml - whole file dead, shadowed by Compact.ButtonStateSelector (high).
2. qml/HatDirectionSelectorV2.qml - whole file dead, shadowed by Compact.HatDirectionSelectorV2 (high).
3. theme/Gremlin/Base/RecordButton.qml + its qmldir line - dead (high).
4. theme/Gremlin/Compact/Button.qml and ItemDelegate.qml + qmldir lines - dead (high).
5. theme/GremlinStyle Menu/MenuBar/MenuBarItem/MenuItem/MenuSeparator/ScrollIndicator - never instantiated (medium; confirm Qt default context menus don't need them).
6. qml/help_topics.js - dead in the program, kept alive only by test_help_topics_script.py.
7. Nine VkbRigEditor forwarder + rig_*.js body pairs never called (innerPageRect, pathPts, themeCell, resetFiveWayFormat, setGroupKind, shapeOutlinePts, leaderHidden, layerFlagInherited, isPathTool).
8. VkbRigEditor ctxHasSpines / ctxSpineCurved / ctxIsLeader / ctxHasMapItem - dead context-menu helpers.
9. LogicalPage _toggleOpen / _toggleGroup / _select / _closePane - dead forwarders.
10. ConfigSection.anyMatch, DialogDeviceMappingEditor.ownFileChange, VkbRigFace.viewOffScreen, Style.removeAlpha, commands.js defineFromMenuBar, menu_model.js pick - dead.
11. Write-only state in StatusPage (stackCandidate, pendingStackW/H, stackTravel) and VkbRigEditor (armRenameId, armRenameMember, lineArm) - set, never read.
12. DialogDeviceMappingEditor selectedNode / fittedOldPage / _templateMsg, DialogConfigureModule moduleFileError, Main onConfig - dead properties.
13. DeviceBindingsPage.moduleSetupRequested - emitted, nobody listens; ErrorDialog.rejected - never emitted.
14. snapPx and cancelPath (forwarder + JS) - used only by smoke tests.
15. 71 ids with no reference anywhere (DialogHardwareHide alone has 10).

No process of mine is running (only two short static Python scans, both finished).
