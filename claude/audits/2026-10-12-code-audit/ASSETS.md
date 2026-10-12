# ASSETS: unused non-code things (settings, Help, image/data files, modules)

Agent ASSETS, repo HEAD 203a74dd, read-only. Start 06:10, end 06:16.
Helper scripts: scratchpad/audit/assets/cfg_scan.py, help_scan.py, help_book_scan.py, reach_scan.py (outputs in cfg_out.txt).

Counts: 85 settings keys registered statically + about 40 more registered in loops (all resolved by hand);
285 Help topics in 10 chapters; 159 tracked image/font/data files outside test/docs; 200+ program modules.

## 1. Settings (gremlin.config) keys

How checked: AST scan of every `register`/`value`/`set`/`exists`/`get` call in gremlin/, action_plugins/, joystick_gremlin.py,
input_tester.py, with module and class string constants resolved (`_CFG_SECTION`, `*_KEY` tuples); then by hand every
loop-registered key (window_placement `_ensure`, vjoy_status `_ensure`, module_model `_reg`, trace `_ensure_options`,
shell_option `ensure_shell_options`, device_map_options `OPTIONS`/`VIEW_SETTINGS` read generically through `values`,
live_debug `_choice_key`), plus grep of QML/JS for each key name. MetaConfigOption rows (Options widgets: action-list,
auto-loading, voice-selection, hidhide-start, debug, module-setup, reset-card-sizes, saved-styles-and-templates) are
Options-page widgets, not stored values, and are all in option.py `_LAYOUT` or the Device Mapping Editor window: used.

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| `global/internal/last-mode` (joystick_gremlin.py:706) | setting registered, never read or written | Only occurrence of the key string is the register call. Mode memory uses `last-mode-per-profile` (mode_manager.py:114). `"last-mode"` elsewhere is only a deferred_write job name (mode_manager.py:279). Tests reference only `last-mode-per-profile`. | high | Stored in every user's configuration.json for nothing. |
| `display/status/last-keep-after-release` (gremlin/ui/shell_option.py:34) | setting shown in Options (Home > Cards, option.py:141, label option.py:52) but its value is never read | Grep of py/qml/js for the key, `keepAfter`, `keep_after`, `lastKeep`: only the register, the label and the layout row. | high | A switch the user can flip that does nothing. Spec question for the lead (remove the row, or wire it up). |
| `global/general/close-to-tray` (joystick_gremlin.py:831-832) | read but never registered | `exists`+`value` only, to carry an old setting into `minimize-to-tray`. No register anywhere. | high | Old-layout reader in an unreleased program, with no `# ONE-TIME (tracker ...)` comment, tracker issue or todo line (CLAUDE.md one-time code rule). Also purge_unused deletes it on first start, so after one start it is dead code. |
| `global/internal/settings-version` (gremlin/config.py:458) | registered, no `value()` call | Read directly via `self._data.get(self._VERSION_KEY)` in purge_unused (config.py:455). | n/a (USED) | Listed so the lead doesn't count it. |
| All other 120+ keys | used | each has a `value()` reader (static or through a loop/generic accessor). | high | Exposed options not in `_LAYOUT` (macro axis-minimum-change-amount, axis-minimum-time-interval) appear as unplaced rows: used. |

Keys read but not registered: only `close-to-tray` above (the rest of the scanner's list are loop-registered, checked by hand).

## 2. Help topics (qml/help/*.js)

How checked: loaded the real book through the QML engine (test/unit/help_book.py, no window) and checked every
`topic:` link and `related` id against the 285 topic ids; `open:` ids against help_links.js `_allowedOpen` and
qml/main_commands.js; ran the program's own live resolver for every Open/Show me link:
`pytest -v test/unit/test_help_links_resolve.py test/unit/test_help_showme_device_mapping_editor.py` off-screen,
temp USERPROFILE: 10 passed (8.8 s).

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| Broken `topic:` / `related` links | none | 0 of all links point at a missing id. | high | |
| Broken Show me / Open targets (menu/, toolbar/, option/, modebar/, devicemappingeditor/) | none | live resolver: every link resolves (test_every_link_resolves PASSED). | high | |
| `qml/help_topics.js` (whole file, 24 lines) | JS module never imported by program QML/JS | grep of qml/, theme/, action_plugins/, gremlin/: no import. Imported only by test/unit/test_help_topics_script.py, test_help_guide.py, test_layers_search_window.py. Its own header says "Old entry points". | high | Used only by tests. Program map 01 lists it (01-app-shell.md:71). |
| `DialogHelp.topicId` property (qml/DialogHelp.qml:45, handlers :182, :200) | input nobody sets | Every opener passes only `chapter` (main_commands.js:128, DialogDeviceMappingEditor.qml:1100, WindowDeviceLibrary.qml:584); no `topicId:` anywhere else, tests included. | high | Dead feature path ("open Help at a topic"); F1 opens a chapter, never a topic. |
| help_links.js `_allowedOpen` ids `view.deviceBindings`, `tools.manageModes` | allowed but no Help link uses them | help_scan.py: no `open:view.deviceBindings` / `open:tools.manageModes` in the book. | medium | Harmless allow-list entries; Help reaches those via `show:` instead. |
| 57 topics with no inbound link (mostly the "Questions" topics, e.g. getting-started-q-*, tools-q-*, modes-q-*, plus getting-started-install, home-devices-record-input, osc-good-to-know, options-profile-add-action-menu) | not linked from other topics | help_book_scan.py inbound count 0. | low (NOT dead) | All are in the book's contents list and search, so reachable. Informational only. |
| F1 mapping | only 3 openers: main window F1 (whole book), Device Mapping Editor F1 (its chapter), Device Library F1 (its chapter) | grep `F1`, `DialogHelp.qml`. | info | The other 7 chapters are reached only through the whole book. |

## 3. Image / icon / font / data files

How checked: `git ls-files` for png/svg/jpg/ico/otf/ttf/json outside test/claude/doc/gh_page/release-notes; for each,
grep of its file name (and its qrc alias) in program code, QML/JS, resources.qrc, joystick_gremlin.spec,
installer/*.iss/*.ps1, deploy.bat, generate_wix.py, .github/workflows. Dynamic names checked: no code builds
`icon_axis_` / `icon_button_` / `icon_hat_` names; action plugins' `icon` is a font glyph (`""`).

| Item (file:line) | Kind | Evidence it is unused | Confidence | Notes |
|---|---|---|---|---|
| `action_plugins/map_to_vjoy/gfx/*.png` (140 files: icon_axis_001-008, icon_button_001-128, icon_hat_001-004) | images never loaded | no reference to the folder or any name pattern; MapToVjoy uses glyph `` (map_to_vjoy/__init__.py:278). Last touched by "Rename remap action to map to vjoy" (upstream era). | high | Shipped: joystick_gremlin.spec copies every file under action_plugins into the exe (spec:5-21). |
| `action_plugins/description/icon.png` | image never loaded | no reference; plugin uses glyph `` (description/__init__.py:103). | high | Shipped the same way. |
| `gfx/icon_large.png` | image never loaded | no reference in code, qrc, spec, installer, workflows. | high | Shipped (spec copies all of gfx/). |
| `action_plugins/response_curve/grid.png` | image referenced only by dead JS | only `render_helpers.js:19` `draw_background()`, which nothing calls (RH.* calls are clamp/x2u/y2v/u2x/v2y only). | high | The live view uses grid.svg / grid_dark.svg (ResponseCurveAction.qml:178). |
| `render_helpers.js` `draw_background` (:17) and `draw_curve` (:4) | JS functions never called | grep `draw_` / `RH.draw` in action_plugins and qml: no caller. | high | Code, but they are why grid.png looks used. |
| `dill_debug.1.log` (repo root, tracked) | stray log file in git | not read by anything; rotated DirectInput log committed by b14b2d15. | high | Should be untracked / .gitignore'd. |
| `deploy.bat`, `generate_wix.py`, `wix_data.p` | old WiX (MSI) build path | no workflow or doc calls them; release-exe.yml uses pyinstaller + installer/build_installer.ps1 (Inno Setup, gremlin_platforms.iss). generate_wix.py is excluded from lint (pyproject.toml:43). | high | Superseded packaging, upstream era. |
| `gfx/icon.ico`, `icon_active.ico`, `icon.png`, `icon_joystick_physical.svg` (qrc alias physical_joystick), `bootstrap-icons.otf` (qrc BootstrapIcons), `xbox360_two_panel.jpg`, `grid.svg`, `grid_dark.svg`, `device_db.json`, `version.json` | used | system_tray.py:123-124; joystick_gremlin.py:1125, :1138; ConditionAction.qml:202, MacroAction.qml:262; Main.qml:2016; Xbox360Face.qml:40; ResponseCurveAction.qml:178; input_cache.py:120; util.py:1107. | high | |
| Theme `arrow.png`/`downarrow.png`/`checkmark.png` sources | used (Qt built-in qrc:/qt-project.org/... Universal images) | not repo files. | n/a | Not broken. |
| `tools_osc/`, `user_scripts/example.py`, `tools/pyright_baseline.json`, `.qmllint.ini` | developer/sample files, not program assets | not loaded by the program by design. | info | Out of scope; listed so they are not counted as dead. |
| `User_Data/` | untracked local test data (commit ce901af1 stopped tracking it) | not in git. | info | |

## 4. Python modules never imported

How checked: import graph (AST `import`/`from`, relative imports resolved, plus string module names such as
importlib targets) walked from the entry points joystick_gremlin.py and input_tester.py and from every
action_plugins/<name> package (loaded by folder in plugin_manager). Importing a.b.c counts a and a.b.

| Item (file:line) | Kind | Evidence | Confidence | Notes |
|---|---|---|---|---|
| `gremlin/validate.py` | module not reachable from the program | no program module imports it (mentions in base_classes.py, profile.py, modules/output.py are comments). Imported by test/conftest.py:535/570/592 and test/unit/test_validate.py, test_macro_raw_steps.py. | high | Used only by tests, by design (its docstring: the tests run its checks after every test). Not dead; keep. |
| every other module under gremlin/, action_plugins/, vigem/, vjoy/, dill/ | reachable | reach_scan.py: 0 others unreachable. | high | One-time modules (device_map_settings_once, library_part_id_once, modules/planes_once, modules/folders_move) are reached and carry ONE-TIME tracker comments. |

## Not verified
- Whether QML type files (theme/qmldir entries, qml/*.qml components) are instantiated: code-level, left to the QML agents.
- The 57 unlinked Help topics are judged reachable from the contents list; not opened one by one.
