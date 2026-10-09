# OSC, sound and speech, tray, look and help (and the leftovers)

Mapped read-only against the code at 4f6bdfa4 (6 Oct); sections 2, 4, 6, 10 and 11 brought up to date 9 Oct. Line numbers drift; re-check them before a step starts. **OSC was parked** (todo.md, 2 Oct) and was picked up 2026-10-09: decisions D-09-OSC-FILE (OSC's own module file, permanent ids, server settings in OSC's Module Setup), D-09-OSC-INPUT (per-input settings), D-09-OSC-FAULTS (small faults), D-09-OSC-LOCK (no Axis/button switch with actions) and D-09-OSC-STOP (held buttons released at Stop) change the OSC statements below; the batch is being built 2026-10-09. Sound and speech are mapped here only at the system level (the player and the speech engine); the Play Sound and Text to Speech editors belong to the Actions page. The last part of section 2 lists every file in `gremlin/` and `qml/` that no other page names, so nothing is unmapped.

## 1. Purpose

- **OSC**: lets a network sender (Stream Deck through Bitfocus Companion, a phone app) press buttons and move axes in the program. OSC is an internal input (03 S90b), like the Keyboard and the Logical Device: one list of OSC inputs, kept in OSC's own module file and shared by every profile; each input has its own settings (mode, message or data, value source, range, trigger). While the profile runs, a packet that matches an input fires its actions like a stick input would.
- **Sound and speech**: the Play Sound and Text to Speech actions play a file or speak text while the profile runs; Options sets how sounds overlap and which voice speaks.
- **Tray, look and help**: the tray icon lets the program run hidden and shows Running/Stopped; dark/light mode, UI scale and Windows scaling set how every window looks; the User Guide (F1) and the glossary set what the screens say.

## 2. Files

**OSC (about 2,800 lines; picked up 2026-10-09)**
- `gremlin/osc.py` (516, being changed 2026-10-09): `OscDevice` singleton, keeping its public name, now delegates to one shared `OscRows` (`OscDevice().rows`); `OscListener` (UDP server from python-osc); `OscRuntime` (start/stop, Listen, packet -> event, per-input auto-release timers); parse helpers (`parse_port`, `parse_delay_ms`, `is_pressed`, `axis_value`, `guess_input_type`); `local_ipv4_addresses`, `default_bind_host`; a hook that patches `Configuration.set` (265-286; the server settings move to OSC's file, D-09-OSC-FILE).
- `gremlin/osc_rows.py` (345, new 2026-10-09, D-09-OSC-FILE / D-09-OSC-INPUT): the OSC input list, pure (no IO, no Qt). `OscRow` (uid, input type, number, address label, mode, cmd_mode, data, source, range_min/max, trigger, delay_ms); `OscRows` (create, delete, set_label, update, by_uid, by_number, uid_of, identifier_of_uid, `matches(address, args)`, rows, to_dict/load_dict, dirty/mark_saved); `check_address`, `check_settings`, `type_of_mode`; `MODES` (button, axis, change), `CMD_MODES` (message, data).
- `gremlin/osc_device_file.py` (398, new 2026-10-09, D-09-OSC-FILE): OSC's own module file (`store.path_of("osc")`, `osc.json`: `inputs` and `server`, other keys kept; writes through `gremlin.modules.store`, so module-file History records them). `path`, `load`, `save`, `save_if_dirty`, `read_server` / `write_server` / `clean_server`, `merge_profile_rows` (older profiles' rows into the file; `MergeResult` uid map, `current_uid_map` while such a profile loads), `backup_old` (`<name>.xml.v15.bak` / `.v14.bak`), `migrate_settings_from_config` (old `osc/connection/*` copied once).
- `gremlin/osc_bulk.py` (73): Bulk capture in the Add dialog. Replaces three methods of `OscDeviceManagementModel` at import (20-22, 62-64); `OscBulkCapture` QML element.
- `gremlin/osc_persist.py` (48+): replaces `InputIdentifier.label` and `linear_index` for every identifier so OSC inputs show as "OSC - <address>" (116-121). References to OSC inputs are stored by the input's uid (D-09-OSC-FILE): `resolve_osc_reference`, `osc_label`, `osc_linear_index`, `osc_rows`. Other uid users: `gremlin/validate.py` (rule check PROFILE-OSC-MISSING: a reference to an id OSC's file doesn't have), `gremlin/ui/device_pack.py` (the `in.osc` item, `missingOsc`, wires carry `<osc-uid>`), `gremlin/library_copy.py` (`_OSC_ITEM`), `gremlin/ui/logical_layout.py` (Assign Hardware lists OSC addresses).
- `gremlin/ui/osc_device_model.py` (343): `OscDeviceManagementModel` (the OSC page's list: add, import, Listen, rename address, delete, clear, sort, mode, row data); `OscInputIdentifier`; `_parse_import_line`.
- `gremlin/ui/osc_option.py` (212): the OSC host/port/auto-release editors; with D-09-OSC-FILE they edit OSC's file (`server`) from OSC's Module Setup (03 S53a), and Options keeps one line with a button to it (01 S40a).
- `gremlin/ui/osc_settings_info.py` (43): `OscSettingsInfo.summary()`, the text in the "Listening for OSC" box.
- `qml/OscDevice.qml` (227): the OSC page (list of inputs, Clear / Sort / Add / Import, rename and delete per row, locked while running). Clear is a red `DangerButton` that asks the shared question (`askClear`, `Confirm.ask`, red Clear OSC Inputs).
- `qml/OscAddDialog.qml` (277): "OSC Input Mapper": Cmd, Change/Button/Axis, Message only / Message + data, Trigger on message + delay, Listen, Bulk capture.
- `qml/OscImportDialog.qml` (84): paste addresses, one per line, with type suffixes.
- `qml/OscServerSection.qml` (157, new 2026-10-09, D-09-OSC-FILE): the **Server** section of OSC's Module Setup (Enabled, host, port, output host/port, auto-release and its delay, pad args); each change is checked and written to OSC's file at once (03 S53a).
- `qml/OptionOscModuleSetup.qml` (41, new 2026-10-09, D-09-OSC-FILE): the one Options row, "OSC settings are in OSC › Module Setup", with its button (01 S40a).
- `qml/OptionOscInputHost.qml`, `OptionOscOutputHost.qml`, `OptionOscAutorelease.qml`: removed 2026-10-09 (D-09-OSC-FILE); the server rows are `qml/OscServerSection.qml` in OSC's Module Setup, and Options' OSC section (group Server, key `osc/connection/module-setup`) is one line, `qml/OptionOscModuleSetup.qml`.
- Elsewhere, OSC parts: `joystick_gremlin.py` 570-809 (registers the seven old `osc/connection/*` settings, read once by `migrate_settings_from_config`), `gremlin/profile.py` (version 16: reads `<osc-device>` of version 14/15 profiles into OSC's file, writes none), `gremlin/modules/store.py` (reloads OSC after a write of its file, like `_reload_logical_device`), `gremlin/code_runner.py` 390/428 (start/stop at Run/Stop), `gremlin/modules/runtime.py` 22-27 (OSC always forwarded, no claims), `gremlin/event_handler.py` 104 (display name), `gremlin/ui/backend.py` 277 (no highlighting for OSC; Save, `*` and Discard cover OSC's file), `gremlin/action_label.py` 166 (patches the model's `data`), `gremlin/ui/module_model.py` 1654, 1896-1925 (OSC card and its Module Setup rows, friendly names by uid, Server section), `gremlin/history_profile.py` 35, `gremlin/swap_devices.py` 21 (OSC left out), `gremlin/ui/device_pack.py`, `gremlin/library_copy.py`, `gremlin/ui/logical_layout.py`, `gremlin/validate.py` (references by uid), `qml/DeviceList.qml` 221-255 (the OSC tab), `qml/Main.qml` 1285, 1844-1856 (page loader, mode).
- `tools_osc/` (outside `gremlin/`): the standalone tester used before the OSC page existed (`osc_listener.py`, `osc_send_test.py`, README, PATH_B.md, WIRE.md, a patch). Its README still says "Tools → Options → osc … port 9000" and "Activate the profile".

**Sound and speech (system level)**
- `gremlin/audio_player.py` (222): `AudioSample` (decode with miniaudio, volume, play, cancel, bounded `block`); `AudioPlayer` singleton (queue, playback thread, Sequential / Interrupt / Overlap); registers `action/play-sound/playback-mode`.
- `gremlin/tts.py` (224): `TTSManager` singleton (Qt WinRT `QTextToSpeech`, queue: Queue Back / Queue Front / Interrupt, voice); registers `action/text-to-speech/voice`.
- Callers: `action_plugins/play_sound/__init__.py` 51-75 (`AudioPlayer().enqueue`), `action_plugins/text_to_speech/__init__.py` 47-67 (`TTSManager().enqueue`, `${current_mode}`), `gremlin/code_runner.py` 376-377 / 435-436 (start/stop), `joystick_gremlin.py` 277-283 (stop at quit), `gremlin/ui/backend.py` 355 (`emitConfigChanged` re-reads the playback mode), `gremlin/ui/option.py` 709-760 (`TTSVoiceSelectionModel`), `qml/OptionTTSVoiceSelection.qml` (30).

**Tray**
- `gremlin/ui/system_tray.py` (344): `SystemTrayIcon` (Win32 tray icon and hidden helper window, idle/active icon, menu: Show/Hide Gremlin-Platforms, Run Profile/Stop Profile, Exit Gremlin-Platforms; minimize/close to tray; one-time balloon; re-adds the icon when Explorer restarts).
- `gremlin/ui/tray_memory.py` (77): gives memory back while hidden (`enter_tray`, `leave_tray`, `release`, `trim_working_set`).
- `qml/Main.qml` 86-98 (`trayed`, `enterTray`, `leaveTray`), `joystick_gremlin.py` 689-710 (settings `minimize-to-tray`, `tray-notice-shown`, old `close-to-tray` carried over), 967-971 (icon made unless off-screen), 1000-1001 (`--start-minimized`).

**Look: theme, colours, UI scale, Windows scaling**
- `qml/Style.qml` (227): the `Gremlin.Style` singleton: dark and light colour tokens, `dp()`, `fitWidth/fitHeight`, fonts, menu tokens.
- `qml/ColorInformation.qml` (19) + `gremlin/ui/util.py` 466-499 `ColorInformation`: hands the Universal accent/background/foreground to Python (used by `gremlin/ui/action_image_generator.py` `_ink`, 78-82).
- `theme/GremlinStyle/` (33 control files + `impl/`): the Qt Quick Controls style the whole program uses (Universal, sized by `Style.dp`). `theme/Gremlin/Base`, `theme/Gremlin/Compact`: custom and compact controls. `theme/Gremlin/Menus`: one menu look, context menus, command palette, `commands.js`, `menu_model.js`. 64 QML/JS files, about 4,900 lines. `theme/Gremlin/AGENTS.md`, `Compact/AGENT.md`: rules for extending them.
- `gremlin/ui/ui_scale_option.py` (108): `ui/general/ui-scale` 70-200 %, `active_scale()` (100 when Windows scaling is on), Python `dp()`, `UiScaleModel`. `qml/OptionUiScale.qml` (50).
- `gremlin/ui/windows_scale_option.py` (68): `ui/general/disable-windows-scaling`, `WindowsScaleModel` (`runningDisabled`). `qml/OptionWindowsScale.qml` (66): check box + Restart / Later / Cancel.
- `joystick_gremlin.py` 20-42 (reads `configuration.json` itself before Qt loads and sets `QT_ENABLE_HIGHDPI_SCALING=0`), 63-69 (`QT_QUICK_CONTROLS_STYLE=GremlinStyle`), 674-688 (registers dark-mode, ui-scale, disable-windows-scaling), 945-977 (colour refresh timer, `bumpThemeRevision`), 1012-1024 (app font `dp(15)`, theme import path, Style singleton), 1125-1130 (puts the variable back before a restart).
- `gremlin/ui/backend.py` 489-495 (`useDarkMode`, `uiScale`); `qml/Main.qml` 100-103 and 1345-1351 (set `Style.isDarkMode` at start and on `configChanged`).

**Help and glossary**
- The Help book and the Help window moved to page 01 (one Help, 01 S128-S139, 9 Oct): `qml/help/` (10 chapter files), `DialogHelp.qml`, `help_search.js`, `HelpSearchBar.qml`, `help_links.js`, `Pulse.qml`. `qml/help_topics.js` (24) is now only the old entry points over the book; `DialogButtonMapGuide.qml` is gone.
- `claude/glossary.md` (76): the approved words (2 Oct, added to since). Kept by `test/unit/test_glossary_words.py`.

**Shared QML widgets (no other page owns them; mapped here)**. The shared pieces built 9 Oct (DangerButton, ConfirmDialog/`confirm.js`, SearchBox, MessageLine, SectionHeading, EmptyState, UndoBar, FilePicker, RenameField; 01 S135, S140-S143) are on page 01.
- Dialogs: `DismissibleDialog.qml` (265, 23 users: confirm/cancel popup), `TextInputDialog.qml` (147, 6 users: one-line text with `allowBlank`, validator), `ErrorDialog.qml` (98).
- Small controls: `IconButton.qml`, `IconCheckBox.qml`, `InputButton.qml` (279: the row button of the Keyboard and OSC lists), `JGListView.qml`, `JGSpinBox.qml`, `JGTabButton.qml`, `JGText.qml`, `JGTextField.qml`, `JGToolButton.qml` (toolbar button, icon-only when narrow), `LabelValueComboBox.qml`, `CompactSwitch.qml` + `CompactSwitchIndicator.qml`, `BetterProgressBar.qml`, `HorizontalDivider.qml`, `LayoutHorizontalSpacer.qml`, `LayoutVerticalSpacer.qml`, `Triangle.qml`, `DragDropArea.qml`, `DropMarker.qml`.
- Tips and icons: `PointerTip.qml` (14 users), `HintsTooltip.qml`, `BootstrapIcons.qml`, `BootstrapIconsNames.qml` (icon font names).

**Shared Python foundations (no other page owns them; mapped here)**
- `gremlin/common.py` (93: singletons, small helpers), `gremlin/error.py` (85: `GremlinError` and subclasses), `gremlin/types.py` (761: `InputType`, `PropertyType`, axis names and other enums), `gremlin/ui/type_aliases.py` (38: `QmlElement`, type aliases).
- `gremlin/fsm.py` (121): a small state machine. Only `test/unit/test_fsm.py` uses it; no program code imports it.

**Leftovers: files no page names yet.** The 6 Oct table gave every leftover file a likely page; by 9 Oct those pages name them in their section 2 (01 app shell and settings, 02 viewers, 03 pairing and Output View, 05 actions, 06 Xbox page, 07 Button Map, 08 History and Device Pack), and `test/unit/test_program_map_covers_files.py` keeps every program file on a page. Only build output is left:

| Files | Most likely page |
|---|---|
| `dist/` (a built copy of the program, including `action_plugins`) | build output; not mapped |

## 3. What it owns

| Data / state | Where | Who else changes it |
|---|---|---|
| OSC inputs (uid, type, number, address, per-input settings) | one shared `OscRows` (`gremlin/osc_rows.py`), reached through `OscDevice().rows`; kept in OSC's module file (D-09-OSC-FILE) | `OscDeviceManagementModel` (add, import, Listen, rename, delete, clear); `osc_bulk.model_on_learned`; `osc_device_file.load` / `merge_profile_rows`; Device Library Restore, Device Pack Import, History restore (through `store`) |
| OSC input last value | `OscDevice.Input.value` | `OscRuntime._emit_button`, `_on_main` |
| OSC inputs on disk | OSC's module file `osc.json` key `inputs` (`osc_device_file.save`); version 14/15 profiles' `<osc-device>` is read once and merged | `osc_device_file`; module-file History records it (D-09-OSC-FILE) |
| Actions on OSC inputs | profile `inputs[OSC GUID]` | Configuration panel (Actions page); `_drop_profile_mappings` on delete/clear (osc_device_model.py 234-246) |
| OSC server settings | OSC's module file key `server`: `enabled` (true), `host` ("" = every address on this PC), `port` (8001), `output_host` ("127.0.0.1"), `output_port` (8000), `autorelease_no_arg` (true), `autorelease_delay_ms` (250), `pad_args`; copied once from `configuration.json` `osc/connection/*` (D-09-OSC-FILE) | OSC's Module Setup Server section; `OscRuntime` reads them at start and when they change (`oscServerSettingsChanged`) |
| OSC settings copy at first start | Only `osc/connection/*` values that differ from the defaults are copied into OSC's file (`migrate_settings_from_config`); with none, nothing is written and a fresh install has no OSC file until the first real save (keeps Home's first selected card on the stick). [2026-10-09, D-09-OSC-FILE (4)] |
| Listener and Listen state | `OscRuntime._listener`, `_learn`, `_hold_learn`, cached behaviour flags, output host/port | `CodeRunner.start/stop`, Add dialog (Listen, Bulk), the patched `Configuration.set` (`sync_bind`) |
| Page-only OSC state | `OscDeviceManagementModel._mode`, `_capture_only`, `_sort_alpha`, `_bulk*` | Main.qml (mode); lost when the page unloads |
| Sound queue | `AudioPlayer._play_list`, `_currently_playing`, `_is_ready`, `_playback_mode` | Play Sound functors (enqueue, event thread); playback thread (pop); `stop` |
| Playback mode | `action/play-sound/playback-mode` (Sequential) | Options → Actions → Play Sound; read at creation and on `emitConfigChanged` |
| Speech queue and engine | `TTSManager._queue`, `_engine` (created once, never destroyed) | Text to Speech functors; `start/stop` from the runner; Options voice list |
| Voice | `action/text-to-speech/voice` ("" = system default) | Options → Actions → Text to Speech (`TTSVoiceSelectionModel`) |
| Tray icon state | `SystemTrayIcon._icon_present`, `_trayed`, `_last_window_mode`, icons, helper window | itself; `Backend.activityChanged` (icon) |
| Tray settings | `global/general/minimize-to-tray` (False), `global/internal/tray-notice-shown` (False); `close-to-tray` carried over then dropped | Options → General → Startup and Tray; the tray (notice) |
| Main window "trayed" | `Main.qml trayed`, `_keepConfigInTray` | `tray_memory` via `enterTray/leaveTray` |
| Dark mode | `ui/general/dark-mode` (True); `Style.isDarkMode` in QML | Options → Interface → Display; Main.qml copies it on start and on `configChanged` |
| UI scale | `ui/general/ui-scale` (100, 70-200) | Options slider (only when Windows scaling is off); `Style.uiScale` follows `backend.uiScale` live |
| Windows scaling | `ui/general/disable-windows-scaling` (False); env `QT_ENABLE_HIGHDPI_SCALING` for the whole run | Options check box; `joystick_gremlin.py` reads the JSON file itself before Qt starts |
| Colours for Python drawing | `ColorInformation` singleton (util.py 466) | `JoystickGremlinApp` on start and when Universal colours change |
| Help text | `help_topics.js` (in code) | developers only |

## 4. Entry points

**OSC**

| Trigger | Handler | Function(s) |
|---|---|---|
| Home → OSC tab (or OSC card) | `DeviceList.qml` 221-245 `uiState.setCurrentTab("osc")` | `Main.qml` `_oscLoader` loads `OscDevice.qml`, `setMode(currentMode)` |
| Click a row | `OscDevice.qml` 118, 172 | `inputIdentifier(index)` → `uiState.setCurrentInput` → Configuration panel on the right |
| Row rename (name) | `InputButton.onRenameRequested` (OscDevice.qml 123) | `ActionNames.setOnModel` (the input's friendly name, not its address) |
| Row edit (pencil) | OscDevice.qml 135-151 → `TextInputDialog` | `changeName(old, new)` → `OscDevice.set_label` (blank allowed; duplicates silently ignored) |
| Row delete (x) | OscDevice.qml 153-164 | `deleteInput(label)`: drops the input's actions in every mode, then the row; no confirmation, no Undo |
| Clear (red) | `OscDevice.askClear` → `Confirm.ask` ("Clear OSC inputs?", Clear OSC Inputs / Cancel; replaces `_clearDialog`) | `clearAllInputs()` |
| Sort | OscDevice.qml 203-206 | `sortInputs()`: A-Z until the page reloads; no way back |
| Add → OK | OscAddDialog 256-262 → OscDevice.qml 88-91 | `createMappedInput(mode, cmd)`; mode is "Axis" for Axis or Change, else "Button"; an address that exists only selects that row |
| Add → Listen (one message) | OscAddDialog 221-238 | `listenForCommand()` → `OscRuntime.listen_once()` (starts the listener even when not running) → first packet → `learned` → `commandCaptured` → dialog binds and closes |
| Add → Listen with Bulk capture | OscAddDialog 233-234 | `OscBulkCapture.start` → `start_bulk` → `listen_bulk`; each packet → `model_on_learned` → `createMappedInput` (same address within 0.3 s ignored); keeps listening |
| Add → Listen again / Cancel / close / untick Bulk | OscAddDialog 225-227, 249-253, 271-276 | `cancelListen()` → `OscRuntime.cancel_listen()` (stops listening mode, not the UDP socket) |
| Add dialog opens Listen | OscAddDialog 72-82 | `backend.pauseInputHighlighting("osc-add")` / resume on close |
| Import → OK | OscImportDialog 72-76 → OscDevice.qml 76-79 | `importInputs(text)`: one address per line, must start with "/"; suffix A, C, E → Axis, anything else → Button; existing addresses skipped |
| OSC Module Setup → Server: host, port, output host/port, Enabled, auto-release, delay | Server section (03 S53a; D-09-OSC-FILE) | `osc_device_file.write_server` → `oscServerSettingsChanged` → `OscRuntime` rebinds, starts or stops at once |
| Options → OSC | one line + button "OSC settings are in OSC › Module Setup" (01 S40a) | opens OSC's Module Setup |
| Run | `CodeRunner.start` (code_runner.py 390) | `OscRuntime.start()`: reads settings, binds UDP, or shows an error |
| Stop / quit | `CodeRunner.stop` 428; `shutdown_cleanup` (joystick_gremlin.py 284) | CUT_INPUT "OSC releases": `OscRuntime.release_held()` (held buttons released while actions still run, S40a), then `OscRuntime.stop()` |
| UDP packet arrives | python-osc thread → `OscListener._on_message` → `_from_thread` | `incoming` signal (queued to main) → `_on_main`: Listen capture; matched address → `EventListener.joystick_event` |
| Address-only button packet (auto-release on) | `_on_main` 495-501 | `QTimer.singleShot(delay)` → `_release_button` with the mode at press time |
| Profile load / New profile | `Profile.from_xml` / `__init__` | OSC inputs stay (one shared list); a version 14/15 profile's `<osc-device>` → `osc_device_file.merge_profile_rows` (one-time note, references follow the uid map) |
| Save | File › Save Profile | `osc_device_file.save_if_dirty` (OSC's file when changed); the profile (version 16) has no `<osc-device>` |
| Device Library Save/Restore/Export, Device Pack Import, History restore of OSC's file | `store.replace` / `write_text` | one write, one History entry; OSC reloads (`oscDeviceReloaded`) |
| Mode change | Main.qml 1285 | `setMode(mode)`: rows show that mode's actions |

**Sound and speech**

| Trigger | Handler | Function(s) |
|---|---|---|
| Run | `CodeRunner.start` 376-377 | `AudioPlayer().start()` (playback thread), `TTSManager().start()` (engine, voice) |
| Play Sound fires | `PlaySoundFunctor.__call__` | missing file: warn once, nothing played; else `AudioPlayer().enqueue(file, volume)` |
| Text to Speech fires | `TextToSpeechFunctor.__call__` | `TTSManager().enqueue(TTSRequest, mode)` with `${current_mode}` filled in |
| Engine ready again | `QTextToSpeech.stateChanged` | `_on_state_changed` → `_speak_next` |
| Stop / quit | `CodeRunner.stop` 435-436; `shutdown_cleanup` 277-283 | `AudioPlayer().stop()` (cancel, join 2 s), `TTSManager().stop()` |
| Options → Play Sound mode | Options; then `backend.emitConfigChanged` | `AudioPlayer().refresh()` |
| Options → Text to Speech voice opens / changes | `TTSVoiceSelectionModel.__init__` / `_set_current_index` | `TTSManager().start()` (engine made even when not running), `update_voice` |

**Tray**

| Trigger | Handler | Function(s) |
|---|---|---|
| Program start (not off-screen) | `joystick_gremlin.py` 969-971 | `SystemTrayIcon(main_window)`; `release_resources` at quit |
| Run / Stop anywhere | `Backend.activityChanged` | `_gremlin_status_change_cb`: active or idle icon |
| Left-click icon | `_system_tray_event_cb` WM_LBUTTONUP | `restore_window` |
| Right-click icon | WM_RBUTTONUP → `_show_menu` | menu: Show/Hide Gremlin-Platforms, Run Profile/Stop Profile, Exit Gremlin-Platforms |
| Menu: Show/Hide | `_toggle_visibility` | hide or restore |
| Menu: Run/Stop Profile | `_handle_context_menu_cb` | `Backend.toggleActiveState()` |
| Menu: Exit | `_quit_gremlin` | restore window, `quitRequested` (normal quit path with its save question) |
| Minimize (setting on) | `_window_mode_changed_cb` | `window.hide()` |
| X / close (setting on, icon present) | `eventFilter` Close | ignore, hide, `_tell_once_still_running` (balloon once) |
| Window becomes Hidden | `_window_mode_changed_cb` | `tray_memory.enter_tray` → `Main.enterTray` → after 400 ms `release` |
| Window shown again | same | `tray_memory.leave_tray` → `Main.leaveTray` |
| Explorer restarts | `TaskbarCreated` message | `_taskbar_created_cb`: re-add icon |
| `--start-minimized` | `process_cmd_args` 1000 | `backend.minimize()` |

**Look and help**

| Trigger | Handler | Function(s) |
|---|---|---|
| Program start | `joystick_gremlin.py` 20-42, 63-69, 1012-1024 | Windows scaling from the JSON file; GremlinStyle; app font; Style singleton |
| Options → Dark mode | Options row → `emitConfigChanged` → `signal.configChanged` | Main.qml 1345-1351 `Style.isDarkMode = backend.useDarkMode` |
| Universal colours change | colour properties of `ColorInformation.qml` | `_theme_refresh_timer` → `ColorInformation().update_colors`, `bumpThemeRevision` (action images reload, `InputButton.qml` 215) |
| Options → UI scale (release slider) | `OptionUiScale.qml` `onPressedChanged` | `UiScaleModel.setScale` → `signal.uiScaleChanged` → `backend.uiScaleChanged` → `Style.uiScale` |
| Options → Ignore Windows display scaling | `OptionWindowsScale.qml` 26-41 | `setDisabled`; if it differs from the running state: Restart / Later / Cancel; Restart → `backend.requestRestart()` |
| Help (F1) anywhere | see page 01 (one Help) | `DialogHelp.qml` with a chapter (`""` main window, `button-map`, `device-library`) |

## 5. Talks to

| Subsystem | Calls out (this → it) | Called by (it → this) |
|---|---|---|
| Run lifecycle (`code_runner`) | — | `OscRuntime.start/stop`, `AudioPlayer.start/stop`, `TTSManager.start/stop` |
| Input pipeline (`EventListener`, `InputModuleRuntime`) | OSC emits `joystick_event` with the OSC GUID; passes the input-module gate unfiltered (`always_forwarded`) | — |
| Mode manager | `ModeManager().current.name` per OSC packet; TTS `${current_mode}` | — |
| Profile | `drop_inputs` on delete/clear; `get_input_item` for row data; older profiles' rows merged into OSC's file | `Profile.from_xml` (version 14/15 `<osc-device>`) |
| Configuration (settings) | reads `osc/*`, `action/play-sound/*`, `action/text-to-speech/voice`, tray and UI keys; OSC patches `Configuration.set` | Options pages through the models above |
| Configuration panel / Actions | `uiState.setCurrentInput` with an OSC identifier | Play Sound and TTS functors call `enqueue`; `action_label.py` patches the OSC model's `data` |
| Backend / UI state | `pauseInputHighlighting`, `toggleActiveState`, `quitRequested`, `requestRestart`, `uiScale`, `useDarkMode`, `gremlinActive` | `activityChanged` → tray icon; `uiScaleChanged` |
| Modules (Home card, Module Setup, store) | writes OSC's file through `gremlin.modules.store` | `module_model._load_osc` reads the rows and friendly names by uid; Server section edits `server` |
| History | OSC's file is recorded as a module file (OSC) | Restore of OSC's file reloads it |
| Logical Device | — | Assign Hardware lists OSC inputs (`logical_layout.py` 89) |
| Swap Devices, Calibration, Auto Mapper, Device Information | — | OSC left out (`swap_devices.py` 21, `calibration.py` 19, AU-68) |
| Error / notification UI | `signal.showError` (bind failed, python-osc missing, cannot start), `signal.showNotification` ("Bound OSC input …") | — |
| Threads | `gremlin.threads.start` for the OSC listener and the audio thread | `threads.shutdown` asks them to stop |
| Windows | Win32 tray (`Shell_NotifyIcon`), `SetProcessWorkingSetSize`; WinRT speech; miniaudio output device | — |

## 6. Threads and timers

| Thread / timer | Started by | Stopped by | Notes |
|---|---|---|---|
| "OSC listener" (`serve_forever`) | `OscListener.start` via `gremlin.threads.start` (osc.py 243) | `OscListener.stop` → `shutdown()` + `server_close()`; also listed for `threads.shutdown` | `shutdown()` waits for the server's next poll (0.5 s at most). Called on the main thread. |
| One thread per UDP packet | python-osc `ThreadingOSCUDPServer` (osc.py 241) | ends by itself | Not made through `gremlin.threads`; not listed (AU-67). Only emits a Qt signal, handled on the main thread. |
| OSC auto-release | one timer per input on the main thread | a new press restarts it; Stop cancels all (D-09-OSC-INPUT) | Fires a release event with the mode from press time. |
| Bulk debounce | `time.monotonic()` (osc_bulk.py 46) | — | Not `gremlin.clock` (OSC parked; the rest moved to `gremlin.clock`, GL-265). |
| "audio player" | `AudioPlayer.start` via `gremlin.threads.start` | `_ask_to_stop` (flag, clear queue, cancel samples); `stop` joins 2 s | Loop sleeps 10 ms with `clock.sleep` (208); queue under a lock (GL-278); Sequential waits in 0.5 s steps re-checking the flag (68-70). |
| miniaudio playback | `miniaudio.PlaybackDevice.start` | sample generator ends or `cancel` | Native thread inside miniaudio. |
| Speech | Qt WinRT engine (main thread object) | `TTSManager.stop` → `engine.stop()` | Queue driven by `stateChanged`; `enqueue` from another thread is passed to the main thread (GL-042). |
| Tray helper window | Win32 window procedure on the main thread's message loop | `release_resources` at quit | — |
| Tray memory clean-up | `QTimer.singleShot(400)` (tray_memory.py 33) | skips itself if the window is visible or the app is closing | — |
| Theme refresh | `_theme_refresh_timer` 0 ms single shot (joystick_gremlin.py 956) | — | Coalesces three colour signals. |

## 7. Rule breaks

| # | Rule | Where | What | Status |
|---|---|---|---|---|
| R1 | Layer rule | `osc.py` 455, 507; `modules/runtime.py` 22-27 | OSC has no input module: packets go straight into `EventListener.joystick_event` and pass the input gate unfiltered by design ("always forwarded", like the Logical Device). The OSC card still offers Module Setup with claims (`module_model.py` 1896-1925) that the gate never reads. | CONFIRMED (by design; see Q4) |
| R2 | Single owner | `osc.py` 265-286 | OSC replaces `Configuration.set` for the whole program at first `OscRuntime()` to watch three keys. | CONFIRMED |
| R3 | Single owner | `osc_bulk.py` 20-22, 62-64; `action_label.py` 166; `osc_persist.py` 116-121 | Three modules replace methods of `OscDeviceManagementModel` and of `InputIdentifier` (for all devices) at import. Import order matters (it broke start-up once: PROGRAM-STARTS-1019). | CONFIRMED |
| R4 | Duplicated logic | `osc_device_model.py` 53-70 and `osc_persist.py` 94-113 | The "OSC - <address>" label and linear index are written twice. | CONFIRMED |
| R5 | Duplicated logic | `osc.py` 29 `DEFAULT_PORT = 8000`; `osc_option.py` 148 `port_default = 8001`; `joystick_gremlin.py` 780 registered "8001"; `parse_port('')` → 8000 | Three defaults for the input port (B15). | CONFIRMED |
| R6 | Duplicated logic | `qml/OscDevice.qml` 35 | The OSC GUID typed as a literal instead of read from the model (`guid`) or `ids.OSC`. | CONFIRMED |
| R7 | Thread rules | `osc.py` 241 | One raw thread per packet from python-osc, outside `gremlin.threads` (AU-67). | CONFIRMED |
| R8 | Time via gremlin.clock | `osc_bulk.py` 46 (`time.monotonic`), `audio_player.py` 190 (`time.sleep`) | Direct `time` calls. The clock rule was written for the relative-axis loops; whether it covers these is a question (Q14). | CONFIRMED (scope unclear) |
| R9 | Thread rules | `audio_player.py` 156, 163 | `_play_list` is appended on the event thread and popped on the playback thread with no lock (safe in CPython for single append/pop; `_ask_to_stop` replaces the list). | SUSPECTED |
| R10 | Thread rules | `tts.py` 270-314 | `TTSManager.enqueue` touches a Qt object; if a Text to Speech action runs from a `threads.timer` fallback thread (Tempo, Double Tap, macro), it calls the engine off the main thread. | SUSPECTED |
| R11 | Bounded waits | `osc.py` 251 | `server.shutdown()` waits on an event with no limit; if `serve_forever` never ran, it would wait forever. | SUSPECTED |
| R12 | Main thread kept free | `osc.py` 40-60 (`getaddrinfo(gethostname)`) | Run at start-up registration, every Options OSC page open, and when the host is unset at Run; a slow name lookup blocks the main thread. | SUSPECTED |
| R13 | Duplicated logic | `joystick_gremlin.py` 20-34 | The settings folder and file name are rebuilt by hand before Qt loads (the comment says why). | CONFIRMED (known) |
| R14 | Duplicated logic | `ColorInformation.qml` 15-18 vs `Style.qml` 19-20 | Python drawing reads Universal background/foreground; the screens use Style tokens (light mode background is `#AAAAAD`, not Universal's). Action images may not match the light theme. | SUSPECTED |
| R15 | Dead code | `gremlin/fsm.py`; `OscDeviceManagementModel.listenForInput`, `createInput` (no QML caller) | Kept but unused. | CONFIRMED |

## 8. Behaviour spec

### OSC connection (server settings in OSC's Module Setup)
- **S1** It should listen for OSC only while the profile runs (and during Add → Listen), and stop listening at Stop and at quit. [user confirmed 2026-10-06; was code only] [test-plan: TB-02 lists only the toolbar; system-maps: map 3 rows B, C, R]
- **S2** It should be possible to turn OSC off in OSC's Module Setup → Server → Enabled; off means no socket is opened at Run. [help: OSC] [changed 2026-10-09, user: D-09-OSC-FILE] (was: Options → OSC → Connection → Enabled)
- **S3** It should listen on the host and port set in OSC's Module Setup → Server. A blank host (the default) means every address on this PC (binds 0.0.0.0), so a LAN address that changes (DHCP) never breaks it; a typed host must be an IP address or a name and is checked before it is saved. The settings are kept in OSC's module file and travel with Device Library, Export and Device Pack. [help: OSC] [changed 2026-10-09, user: D-09-OSC-FILE] [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: Options; the saved LAN address of this PC)
- **S4** Changing any server setting should take effect at once, also while running: turning Enabled on starts the listener, host or port rebinds it, off stops it; a failed bind is tried again when the settings change. [changed 2026-10-09, user: D-09-OSC-FILE] (was: Enabled, host and port only; turning Enabled on while running did nothing, G-OSC11)
- **S5** A port that is blank, not a number or outside 1-65535 should fall back to the default. [user confirmed 2026-10-06; was code only]
- **S6** The default input port should be 8001 (intended; the user can change it) and the default output port 8000, one value each, shown the same everywhere (Module Setup, the Listening box, the listener); a blank or bad input port falls back to 8001. [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: an open question; B15 suggested 8000 and 9000)
- **S7** If the port cannot be opened (in use, address gone), Run should still run the rest of the profile and show one error "Could not bind OSC on host:port." [user confirmed 2026-10-06; was code only] [tracker: D16 titled "Error"]
- **S8** OSC on by default should not give a bind error on every Run: the default host is every address on this PC, not a saved LAN address. [changed 2026-10-09, user: D-09-OSC-FILE] (was: also not bound to the LAN address; opening only when there are OSC inputs (Q5) is not part of this decision, see G-OSC7)
- **S9** The output host and port (127.0.0.1:8000) should be where OSC feedback goes; nothing sends yet, so Module Setup shows them as "used once OSC output is built". [changed 2026-10-09, user: D-09-OSC-FILE] (was: Q3 hide until something sends)

### OSC inputs (the OSC page)
- **S10** The OSC page should list every OSC input (one list shared by every profile, kept in OSC's module file) as "Button n - /address" or "Axis n - /address", with its action count for the current mode. [changed 2026-10-09, user: D-09-OSC-FILE] (was: the loaded profile's OSC inputs)
- **S11** It should be locked (greyed, no clicks) while the profile runs. [user confirmed 2026-10-06; was code only] [test-plan: system-maps editorLocked list]
- **S12** Add should create an input with the typed address and the chosen mode (Button, Axis or Change) and settings (S16), select it, and open its actions on the right; Axis mode makes an axis input, the others a button input. The new input gets a permanent id and the lowest free number. [changed 2026-10-09, user: D-09-OSC-INPUT] (was: Button or Axis only)
- **S13** After Add or Import, the row added should be the one selected, also for an Axis and after Sort. [tracker: APP4] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S14** Adding an input that already exists (same address, and in Message + data the same values) should select the existing input, not make a second one; several inputs may share an address when their data or value source differ. [changed 2026-10-09, user: D-09-OSC-INPUT] (was: one input per address)
- **S15** Addresses should match without regard to case (`/Deck/1` = `/deck/1`) and are stored in lower case. [user confirmed 2026-10-06; was code only]
- **S16** Each input should keep its own settings, set in the Add window and saved in OSC's file: mode (Button, Axis, Change; Encoder reserved, not offered), Message only / Message + data (with the values captured or typed), value source (P1..Pn, P1 first), axis range (default 0 to 1), Trigger on message and its delay (left blank = the server default). They work at run time as S38-S39d say. [changed 2026-10-09, user: D-09-OSC-INPUT] (was: work per input or be hidden; Q2)
- **S16a** An OSC input that has actions (in the open profile, any mode) should not switch between Axis and the button modes (Button, Change, Message + data); the change is refused with "Remove this input's actions first: an axis and a button use different actions." Switching among the button modes is allowed (as GremlinEx). [changed 2026-10-09, user: D-09-OSC-LOCK]
- **S17** Listen (single capture) should fill the address from the next message that arrives, offer its values as sources (P1..Pn), bind it with the window's settings and close the dialog; it ends on that message by design. [changed 2026-10-09, user: D-09-OSC-INPUT] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S18** Listen should tell the user if OSC is off or the port can't be opened ("Could not start OSC listener."). [user confirmed 2026-10-06; was code only]
- **S19** Bulk capture should add one input per new address, each with the window's settings, until Bulk capture is unticked; the same address twice within 0.3 s counts once. [OscAddDialog tip: "intended for simple devices such as the Stream Deck"] [changed 2026-10-09, user: D-09-OSC-INPUT]
- **S20** Cancel, closing the Add dialog, Stop in the Listening box, unticking Bulk capture, or a single capture ending should end listening and, when no profile runs, close the port. [tracker: APP13] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S21** The "Listening for OSC" box's button should be Stop, and it stops listening (not only hides the box). [tracker: APP17] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S22** Import should add one input per line that starts with "/", skip lines that don't and inputs that exist, select the row it added (also after Sort), and say how many were added and skipped. [changed 2026-10-09, user: D-09-OSC-INPUT] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S23** Import suffixes, after a space or a comma (`/a B`, `/a, B`): A axis, B button, BNP button with Trigger on message, C change, E a button with the note "encoder not supported yet"; an unknown suffix gives a button and a note naming the line. [tracker: B17] [changed 2026-10-09, user: D-09-OSC-INPUT] (was: E encoder)
- **S24** Editing an address should keep the input's actions, friendly name and every reference (same permanent id). [changed 2026-10-09, user: D-09-OSC-FILE]
- **S25** An address should never be blank, should start with "/" and be unique (with its data and source, S14); a refused edit says why in the shared message line. [tracker: APP11] [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: duplicate refused silently)
- **S26** Delete should ask the shared question (Confirm, "You can restore it from Tools › History.") and then remove the input and its actions in every mode. [tracker: G-LIBLEAK note: OSC Delete leak closed] [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: no question; Q6 Undo)
- **S27** Clear should ask first ("This will remove every OSC input in the current profile.") and then remove all inputs and their actions. [user confirmed 2026-10-06; was code only]
- **S28** Sort should order the list A-Z by address. [user confirmed 2026-10-06; was code only]
- **S29** OSC inputs should be listed in Logical Device → Assign Hardware for a button. [help: Assign hardware and actions]
- **S30** The OSC page should have no Appearance panel. [help: Appearance] [tracker: AU-52]
- **S31** The OSC card should not offer Copy Setup to Another Stick, Swap with Another Stick, Change vJoy Output (which replace Swap Device), Auto Mapper, Device Information or Calibration. [changed 2026-10-08 to follow D-10-SWAP (Device Library, 10)] [tracker: AU-68, AU-58, AU-91]
- **S32** Input highlighting should not jump to OSC inputs. [user confirmed 2026-10-06; was code only] (backend.py 277)
- **S33** OSC Add and Calibration should each hold their own highlight pause; closing one does not resume while the other is open. [tracker: N11]
- **S34** The OSC page's empty state should talk about OSC, not sticks. [tracker: AU-58 (left: OSC parked)]
- **S35** OSC dialogs should say "OK" (not "Ok") and put Cancel where other dialogs do. [glossary: Title Case] [tracker: E1 (left: OSC parked)]

### OSC at run time
- **S36** A packet whose address matches an OSC input should fire that input's actions in the current mode, like a stick input. [user confirmed 2026-10-06; was code only] [test: test_input_module_gate.py::test_osc_passthrough]
- **S37** A packet whose address matches nothing should be ignored (logged at debug); `/noop` is always ignored. [user confirmed 2026-10-06; was code only]
- **S38** Button: the value at the input's source (P1 by default) not 0 = press, 0 = release; a text value counts as pressed unless it reads as a number 0. [changed 2026-10-09, user: D-09-OSC-INPUT] (was: the first value)
- **S39** Button with no value at its source: press, then release after the delay when Trigger on message is on for the input (or, left blank, the server's "auto-release address-only messages", on by default); the delay is the input's or the server's (250 ms, 0-10000). With Trigger on message on, any message presses then releases after the delay. Pad args works as before. [changed 2026-10-09, user: D-09-OSC-INPUT]
- **S39a** Change: when the value at the source differs from this input's last value (the first message counts), press, then release after the delay. [changed 2026-10-09, user: D-09-OSC-INPUT]
- **S39b** Each input should have its own auto-release timer: a new press restarts it (a release from an earlier press never lands during a later hold), and Stop cancels all of them. [changed 2026-10-09, user: D-09-OSC-INPUT] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S39c** Message + data: a message whose address and values equal the input's data (numbers compared as numbers, else as text) presses, then releases after the delay. [changed 2026-10-09, user: D-09-OSC-INPUT]
- **S39d** A message should go to every input that matches it (address in any case; data and source as above). [changed 2026-10-09, user: D-09-OSC-INPUT]
- **S40** The auto-release should release in the mode the press happened in. [user confirmed 2026-10-06; was code only]
- **S40a** At Stop, every OSC button still held should be released (in the mode it was pressed in) before the run's actions stop, like the Logical Device's neutral at Stop; then the auto-release timers are cancelled (S39b). [changed 2026-10-09, user: D-09-OSC-STOP]
- **S41** Axis: the number at the input's source, scaled from its range (default 0 to 1; axes from older profiles -1 to 1, so they behave as before) to -1.0 … 1.0 and limited to it; no value or text is ignored. [changed 2026-10-09, user: D-09-OSC-INPUT] (was: the first value limited to -1..1; no value gives 0.0)
- **S42** Listen may suggest a type from the first message (no value, 0, 1 or beyond ±1 → Button; anything else → Axis); the mode chosen in the window is what is saved. [changed 2026-10-09, user: D-09-OSC-INPUT]
- **S43** Server settings changed in OSC's Module Setup should apply at once, also while running, without a new Run (S4). [changed 2026-10-09, user: D-09-OSC-FILE] (was: Options, read per packet)

### OSC saving (OSC's own module file)
- **S44** OSC inputs and the server settings should be saved in OSC's own module file (`store.path_of("osc")`, keys `inputs` and `server`), one list shared by every profile, as the Keyboard's and the Logical Device's are; profiles hold no OSC rows. [changed 2026-10-09, user: D-09-OSC-FILE] (was: OSC inputs in the profile `<osc-device>`, connection settings in program settings)
- **S44a** Every OSC input should have a permanent random id (32 hex characters), given once and never changed; the number is a display name only (lowest free). Bindings, Assign Hardware links, friendly names and Device Pack wires store the id; a reference to an id OSC's file doesn't have is flagged as missing and never moved to another input. [changed 2026-10-09, user: D-09-OSC-FILE]
- **S45** Loading another profile or New Profile should keep the OSC inputs (one shared list). [changed 2026-10-09, user: D-09-OSC-FILE] (was: replaced by that profile's, none for New)
- **S46** Adding, editing, deleting or clearing OSC inputs should show `*` in the title; File › Save Profile (Ctrl+S) saves OSC's file when it changed, and Discard throws the OSC edits away (the file is read again). [changed 2026-10-09, user: D-09-OSC-FILE] (was: the profile's `<osc-device>` section)
- **S47** History should record OSC's file as a module file (OSC); Device Library Save, Restore and Export and Device Pack carry it, and Restore or Import is one write, one History entry, and reloads OSC. [changed 2026-10-09, user: D-09-OSC-FILE] (was: History "the OSC inputs" of the profile)
- **S48** Profiles are version 16 (reads 14, 15 and 16). An older profile's OSC rows are added to OSC's file on its first load: the same type, number and address reuses that input; any other gets the next free number and a new id, and the profile's references follow. A one-time note says what was added; the first save over the original keeps it as `<name>.xml.v15.bak` (or `.v14.bak`); opening alone (or a read that doesn't bind) changes nothing. A duplicate address in an old profile is skipped with a load warning and never stops the profile from opening. [changed 2026-10-09, user: D-09-OSC-FILE] (was: a damaged `<osc-device>` should not stop the profile opening)

### Sound (system level)
- **S49** Sounds should play only while the profile runs; Stop should cut off playing sounds and drop queued ones. [user confirmed 2026-10-06; was code only] [test: test_bounded_waits.py::test_a_sound_is_not_waited_for_once_the_player_stops]
- **S50** Sequential plays sounds one after another; Interrupt stops what plays and plays the new one; Overlap plays them together. [help: Play Sound] [Options description]
- **S51** Changing the playback mode in Options should apply from the next sound the player starts (sounds already queued behind a playing one keep waiting). [user confirmed 2026-10-06; was code only] (via `emitConfigChanged`) [changed 2026-10-07 to follow decision D-09-S51-NEXTSOUND, which wins over the earlier wording "at once"]
- **S52** A sound file should be decoded on the playback thread, not the event thread, and freed when it ends. [tracker: APP6] [test-plan: PROGRAM-FIXES] [test: test_program_fixes.py::test_sounds_are_decoded_on_the_playback_thread, ::test_finished_sounds_are_let_go]
- **S53** A missing file should play nothing and warn once; a damaged or unsupported file should be logged once and not stop other sounds. [tracker: ACT11] [test: test_play_sound_missing_file.py::test_pressing_with_a_missing_file_plays_nothing, ::test_pressing_with_an_unreadable_file_does_not_raise] [test: test_program_fixes.py::test_a_sound_that_cannot_be_decoded_is_logged_once]
- **S54** Stopping right after starting should end the audio thread. [test: test_threads.py::test_the_audio_player_stopped_right_after_starting_ends]
- **S55** Waiting for a sound should never be endless. [tracker: H5] [test: test_bounded_waits.py]

### Speech (system level)
- **S56** Text to Speech should speak only while the profile runs, with Interrupt (stop and speak now), Queue Front, Queue Back. [help: Text to Speech]
- **S57** Stop should stop speech and drop queued text. [user confirmed 2026-10-06; was code only]
- **S58** The voice chosen in Options → Actions → Text to Speech should be used by every Text to Speech action, also when changed while running. [help: Text to Speech] [user confirmed 2026-10-06; was code only]
- **S59** If the saved voice is no longer installed, the system's default voice should speak. [user confirmed 2026-10-06; was code only]
- **S60** `${current_mode}` in the text should be replaced by the current mode name. [user confirmed 2026-10-06; was code only]
- **S61** Text to Speech is offered on joystick buttons and keyboard keys. [changed 2026-10-09 to match D-09-Q11 / D-05-Q7 (user approved); was "joystick buttons only"] [test-plan: S-34 closed]

### Tray
- **S62** The tray icon should show while the program runs, idle or active to match Running/Stopped, with the tooltip "Gremlin-Platforms". [glossary: program name in the tray] [test-plan: TB-02]
- **S63** Left-click on the icon should show the window as it was (windowed, maximized or full screen). [test-plan: W-06..09]
- **S64** The tray menu should read Show/Hide Gremlin-Platforms, Run Profile / Stop Profile, Exit Gremlin-Platforms. [glossary: D1, D12] [test-plan: GLOSSARY-1]
- **S65** With Minimize to tray on, minimizing or closing (X) should hide the window and keep the profile running; File → Exit or the tray's Exit quits. [help: Options] [test-plan: TRAY-ONE]
- **S66** The first time the X hides the window, a balloon should say the program is still running; never again. [test-plan: TRAY-ONE]
- **S67** Exit from the tray should bring the window back first, so a save question can be answered. [user confirmed 2026-10-06; was code only]
- **S68** Whoever had the old "Close to tray" on should get Minimize to tray on. [test-plan: TRAY-ONE]
- **S69** While hidden to the tray, the pages should unload and memory be given back, inputs keep working, and unsaved Appearance or Logical Device edits are kept; showing the window reloads the pages. [test-plan: MEM-2, MEM-HANDS-ON] [test: test_tray_memory.py::test_hidden_window_unloads_and_reloads, ::test_pages_load_only_while_needed]
- **S70** If the tray icon can't be made, minimize and X should behave normally (no hidden window with no way back). [user confirmed 2026-10-06; was code only]
- **S71** The icon should come back after Explorer restarts. [user confirmed 2026-10-06; was code only]
- **S72** Off-screen runs (tests, checks) should make no tray icon. [tracker: AU-73, AU-98] [test: test_audit3_startup.py::test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray, test_audit2_startup_devices.py::test_the_tray_icon_follows_the_platform_qt_started_on]
- **S73** `--start-minimized` should start minimized (to the tray when Minimize to tray is on). [user confirmed 2026-10-06; was code only]

### Look: dark/light, colours
- **S74** Dark mode on/off should apply at once to every window. [test-plan: OPT-U01 PASS]
- **S75** Every screen should use Style colour tokens, not colour literals; device photos and what is drawn on them keep their own colours. [test-plan: OPT-U01b] [tracker: E5, E6] [test: test_colour_tokens.py::test_no_new_colour_literals]
- **S76** Light mode is a grey mode: no white surfaces. [user confirmed 2026-10-06; was code only] (Style.qml 48-49 comment)
- **S77** Menus, dropdowns and the command palette should look the same everywhere (the Button Map's look). [test-plan: MENU-1, MENU-2]
- **S78** Fonts should come from `Style.uiFont`, `monoFont`, `iconFont` only. [tracker: E6]
- **S79** Error and notification dialogs should be readable in both themes. [test-plan: W-12]

### Look: UI scale and Windows scaling
- **S80** With Windows scaling on (default), the program follows Windows' display scale and the UI scale slider is disabled at 100 %. [help: Options] [test-plan: OPT-U06] [test: test_ui_scale.py::test_windows_scaling_on_ignores_slider]
- **S81** With "Ignore Windows display scaling" on, the slider (70-200 %, steps of 5) sizes the whole UI when the slider is released, without a restart. [test-plan: OPT-U06] [test: test_ui_scale.py::test_windows_scaling_off_uses_slider, ::test_style_follows_backend_live, ::test_clamp_scale]
- **S82** Changing "Ignore Windows display scaling" should ask Restart / Later / Cancel; Cancel undoes the change; Restart restarts and the new start reads the new value. [test-plan: OPT-U02, W-11]
- **S83** No window or its smallest size should be larger than the screen at any scale. [tracker: UI1, UI3, C20] [test-plan: UI3-TOOL-WINDOWS-FIT] [test: test_tool_windows_fit, test_main_window_fits]
- **S84** At 200 % on a small screen, window contents should not be cut off. [tracker: AU-56 (open, on hold)]

### Help and glossary
- **S85** F1 (or Help → User Guide) opens the User Guide; F1 in the Button Map opens the Button Map Guide with only its topics. [test-plan: BMAP3-5-HANDS-ON] [test: test_help_guide.py::test_button_map_help_is_its_own_guide]
- **S86** Every action should have a help topic; every menu path the help names should exist; removed things should not be in the help. [test: test_help_guide.py::test_every_action_plugin_has_a_topic, ::test_menu_paths_in_the_guide_exist, ::test_removed_or_wrong_things_are_not_in_the_help]
- **S87** On-screen text and Options descriptions should use the glossary words (Run/Stop, Running/Stopped, Gremlin-Platforms, US spelling, Title Case for buttons and titles). [glossary] [test: test_glossary_words.py::test_on_screen_text_uses_the_glossary_words, ::test_options_descriptions_use_the_glossary_words]
- **S88** A new idea should be added to the glossary before it appears on screen. [glossary: Core terms]
- **S89** Help, About and the theme should work in the built exe (resources bundled). [test-plan: B-04, B-SPEC-DLL]

## 9. Questions for the user

- **Q1 (OSC)** Input and output default ports (B15). **Decided 2026-10-09 (D-09-OSC-FAULTS): input 8001 (intended, adjustable), output 8000** (S6).
- **Q2 (OSC)** Add dialog's Change, Message + data, Trigger on message and delay (B16) and import suffixes (B17). **Decided 2026-10-09 (D-09-OSC-INPUT): built per input** (S16, S23, S38-S41); supersedes the 2026-10-06 recommendation to hide them.
- **Q3 (OSC)** Output address: nothing sends OSC. **Decided 2026-10-09 (D-09-OSC-FILE): kept, shown as "used once OSC output is built"** (S9); supersedes "hide it".
- **Q4 (OSC)** OSC has no input module and passes the input gate unfiltered, yet the OSC card offers Module Setup with claims that the gate ignores. Which is right: OSC stays outside the module system (remove claims from its Module Setup), or OSC inputs get claimed like any device? Recommendation: keep OSC outside, show only friendly names in its Module Setup.
- **Q5 (OSC)** Should the listener open only when the profile has OSC inputs, bound to 127.0.0.1 by default (APP5)? Recommendation: yes; it removes firewall prompts and bind errors for people who don't use OSC.
- **Q6 (OSC)** Delete on an OSC row removes the input with no question. **Decided 2026-10-09 (D-09-OSC-FAULTS): the shared question, restorable from Tools › History** (S26); supersedes the Undo recommendation.
- **Q7 (OSC)** Sort is one-way (A-Z until the page reloads) and is not remembered. Toggle and remember it, or drop the button? Recommendation: toggle A-Z / by type and number, remembered per program.
- **Q8 (OSC)** Each OSC row has two names: the address (pencil) and a friendly name (rename). Is the friendly name wanted for OSC? [code only] Recommendation: keep; it shows on chips and in History.
- **Q9 (OSC)** The error "OSC requires python-osc. In the repo folder run: poetry add python-osc" is developer text shown to users. Recommendation: say "OSC is not available in this build" and log the detail.
- **Q10 (OSC)** OSC packets that arrive while the profile is stopped but the port is open (after Listen) still go into the input pipeline (they do nothing because no actions are connected). Fine, or drop them unless running or listening? Recommendation: drop them; it matters only with APP13.
- **Q11 (speech)** Text to Speech only on joystick buttons, not keyboard keys (test-plan S-34). Intended? Play Sound allows keys. Recommendation: allow keys like Play Sound.
- **Q12 (speech)** If the saved voice is uninstalled, the default voice speaks but Options shows the first voice in the list as chosen. Show "(default)" instead? Recommendation: yes.
- **Q13 (speech)** If Windows speech (WinRT) is not available, nothing is said and no message shows. Recommendation: one warning in the log and in the action's feedback.
- **Q14 (rules)** Does the "time via gremlin.clock" rule cover every timed wait (audio loop sleep, OSC bulk debounce, auto-release timer), or only the action loops? Recommendation: all loops that sleep in a thread; Qt timers on the main thread stay as they are.
- **Q15 (look)** The Options check box says "Disable Windows scaling", its title and the help say "Ignore Windows display scaling". Recommendation: "Ignore Windows display scaling" on the box too.
- **Q16 (look)** Action summary images are drawn in Python with fixed 9-11 px fonts and Universal colours, so they don't follow UI scale or the grey light theme. Fix with Style values, or leave? Recommendation: check one off-screen at 200 % and light mode first; fix if visibly off.
- **Q17 (tray)** Tray and Minimize to tray: the old test-plan rows W-04..W-09 still say Close to tray, Activate/Deactivate, Quit. Retire those rows in favour of TRAY-ONE and the glossary words? Recommendation: yes.
- **Q18 (OSC Options text)** "Listen for OSC packets while a profile is active" and "Must match Companion Target Port": glossary says Running, and Companion is one sender among many. Recommendation: "while the profile runs"; "the port your OSC sender sends to".
- **Q19 (leftovers)** `gremlin/fsm.py` is used only by its own test. Remove both? Recommendation: yes, after the leftover list is agreed. [superseded 2026-10-07 by D-09-Q19-SUPERSEDED: fsm.py is used (double_tap, tempo, smart_toggle, hat_buttons, code_runner) and stays]
- **Q20 (leftovers)** The leftover table in section 2 assigns files to pages 01, 05, 07, 08. Confirm or move them. Recommendation: accept, and let those pages' authors confirm.

## 10. Known gaps

**Code differs from spec or rule (OSC; picked up 2026-10-09)**
- **G-OSC1** Three input-port defaults (8000 / 8001 / 8000 for blank) and input = output 8000 when unset. (S6, R5) [tracker: B15] Fixed by D-09-OSC-FAULTS (being built 2026-10-09).
- **G-OSC2** Output host/port are stored and logged but no code sends OSC. (S9, Q3) Fixed by D-09-OSC-FILE (shown as "used once OSC output is built"; sending is still not built) (being built 2026-10-09).
- **G-OSC3** Add → OK after an Axis selects the wrong row: `listenBound.emit(rowCount() - 1)` (osc_device_model.py 137) while the list sorts Axis before Button (checked: `['/a', '/b']`); also wrong after Sort. Actions then go to another input. (S13) [tracker: APP4] Fixed by D-09-OSC-FAULTS (being built 2026-10-09).
- **G-OSC4** Rename accepts a blank address (checked: `set_label('/b', '')` → `''`) and one without "/"; the dialog lacks `allowBlank: false` (OscDevice.qml 40-55); a duplicate is refused silently. (S25) [tracker: APP11] Fixed by D-09-OSC-FAULTS (being built 2026-10-09).
- **G-OSC5** Cancel/close after Listen leaves the UDP port open until the next Run/Stop (`cancel_listen` 336-342 does not stop the listener). (S20) [tracker: APP13] Fixed by D-09-OSC-FAULTS (being built 2026-10-09).
- **G-OSC6** "Listening for OSC" box has only OK, which hides the box but keeps listening. (S21) [tracker: APP17 note] Fixed by D-09-OSC-FAULTS (being built 2026-10-09).
- **G-OSC7** OSC starts on every Run (enabled by default, LAN IP), with an error each time the bind fails. (S8) [tracker: APP5] Fixed by D-09-OSC-FILE in part (blank host, no saved LAN address); opening only when there are OSC inputs (Q5) stays open (being built 2026-10-09). Rest built 2026-10-09 (Q5 answer): at Run the port opens only when the profile has OSC inputs (`osc.profile_uses_osc()`); Listen/Bulk open it on demand and close it after.
- **G-OSC8** Change saved as Axis; Message + data, Trigger on message and delay never passed on (OscAddDialog.qml 65-70, 88-91/260). (S16) [tracker: B16] Fixed by D-09-OSC-INPUT (being built 2026-10-09).
- **G-OSC9** Import: C and E become plain axes, BNP and B both plain buttons (checked). (S23) [tracker: B17] Fixed by D-09-OSC-INPUT (being built 2026-10-09).
- **G-OSC10** One raw thread per packet; settings read per packet. (R7, S43) [tracker: AU-67]
- **G-OSC11** Turning Enabled on while running does not start the listener (`sync_bind` returns early when no listener, osc.py 432); only host/port/enabled are watched, other keys are read per packet. Fixed by D-09-OSC-FILE (being built 2026-10-09).
- **G-OSC12** Auto-release timers are not cancelled at Stop or by a new press: a release from an earlier press can land during a later hold. (S39) Fixed by D-09-OSC-INPUT (being built 2026-10-09).
- **G-OSC13** OSC empty-state text talks about sticks. [tracker: AU-58 (in progress, OSC part left)]
- **G-OSC14** "Ok" before "Cancel" in both OSC dialogs (OscAddDialog.qml 257, OscImportDialog.qml 72). [tracker: E1 note] Fixed by D-09-OSC-FAULTS (being built 2026-10-09).
- **G-OSC15** OSC model `dataChanged` ranges: `createIndex(self.rowCount(), 0)` one past the end (osc_device_model.py 134, 228, 257). [tracker: AU-65 note: "left with OSC"]
- **G-OSC16** No Undo for OSC add/rename/delete/clear (Undo exists on Logical Device, Module Setup, Calibration, Configuration). (Q6) Fixed by D-09-OSC-FILE / D-09-OSC-FAULTS in part (Delete asks; OSC's file is restorable from History); no page Undo (being built 2026-10-09).
- **G-OSC17** `tools_osc/README.md` describes the old flow (lower-case "osc" section, port 9000, "Activate the profile").
- **G-OSC18** OSC Module Setup claims are read for the card but ignored at run time. (R1, Q4)
- **G-OSC19** OSC inputs were kept in each profile and the server settings in program settings, with references by number. (S44, S44a, S48) Fixed by D-09-OSC-FILE (being built 2026-10-09).
- **G-OSC20** An OSC input with actions can be switched between Axis and a button mode in Edit Settings. (S16a) Fixed 2026-10-09 (D-09-OSC-LOCK): built in d7eaa746 (`osc_device_model.updateInputSettings` refuses; `inputSettings` "locked" greys the other type; test_osc_uimodel::test_type_change_refused_while_the_input_has_actions).
- **G-OSC21** At Stop, an OSC button still held was not released; Stop only cancelled the auto-release timers. (S40a) Fixed 2026-10-09 (D-09-OSC-STOP): `OscRuntime.release_held()` runs in the CUT_INPUT stage before "input off" (code_runner), so actions see each release once; `stop()` calls it too (test_osc_run::test_stop_releases_held_buttons_while_callbacks_still_run).

**Sound, speech, tray, look** (status 9 Oct, from claude/gap-list.md)
- **G1** Text to Speech engine may be called off the main thread when a timer-run action speaks. (R10) Done (GL-042, batch 2).
- **G2** `_play_list` shared between threads without a lock. (R9) Done (GL-278, batch 3).
- **G3** Options voice list shows the first voice when the saved voice is missing. (Q12) Done (GL-198, batch 2).
- **G4** No message when WinRT speech is unavailable. (Q13) Done (GL-199, batch 2).
- **G5** Windows-scaling check box wording differs from its title and help. (Q15) Done (GL-233, batch 3).
- **G6** Action images ignore UI scale and the light theme's grey. (R14, Q16) Needs a hands-on check (GL-200).
- **G7** 200 % on a small screen still cuts off contents in eight windows. Open, on hold (GL-201). [tracker: AU-56]
- **G8** The test plan's tray rows (W-04..W-09, TB-02) use the old words and the old two settings. (Q17) Done (GL-220, batch 3).
- **G9** The User Guide has no OSC topic. Partly done: Help has search (01 S137) and an "OSC options" topic; there is still no topic for the OSC page itself (OSC parked).

**Open tracker items for this page**
- B15: OSC input port clashes with output port when unset. Resolved 2026-10-09 (D-09-OSC-FAULTS: 8001 / 8000).
- B16: OSC Add: Change saved as Axis; message/trigger/delay do nothing. Resolved 2026-10-09 (D-09-OSC-INPUT).
- B17: OSC import: C and E become plain axes. Resolved 2026-10-09 (D-09-OSC-INPUT).
- APP4 (open): OSC Add selects the wrong input after adding an Axis.
- APP5 (open): OSC listener opens a LAN port on every Run, even with no OSC inputs.
- APP11 (open): OSC rename accepts a blank or slash-less address.
- APP13 (open): OSC listener stays open after Add > Listen when no profile runs.
- AU-67 (open): OSC server threading (parked).
- AU-58 (in progress): OSC empty-state text left.
- AU-56 (open, on hold): 200 % UI scale on a small screen cuts off contents.
- AU-116 / AU-117 (open, Run lifecycle page): timers and leftovers at Stop; OSC auto-release timer and the OSC listener stop belong to the same Stop list (system-maps map 3 row R).

**Things nothing owns**
- `Configuration.set` is patched by OSC; nobody owns "who may watch a setting" (R2).
- `InputIdentifier.label/linear_index` replaced for all devices by `osc_persist` (R3).
- The shared QML widgets and the Python foundations (section 2) have no page other than this one. Owner (GL-280, catch-up batch 3): this page; `TextInputDialog` and `DismissibleDialog` now have direct tests (`test/unit/test_batch3_C1.py`).
- `listenForInput`/`createInput` in the OSC model (no caller; GL-279). `gremlin/fsm.py` is used (D-09-Q19-SUPERSEDED).
- The leftover table in section 2: accepted (Q20); by 9 Oct the pages named their files and the table holds only what is still waiting.

## 11. Size and test coverage

| Part | Files / lines (rough) | Tests that cover it | Obvious untested paths |
|---|---|---|---|
| OSC | 13 files, about 2,900 lines (+ `tools_osc/`) | the 2026-10-09 batch's `test_osc_rows.py` (10), `test_osc_file.py` (16), `test_osc_run.py` (18), `test_osc_profile.py`, `test_osc_refs.py`, `test_osc_uimodel.py` (10), `test_osc_qml.py`, `test_osc_options.py` (4), `test_osc_backend.py` (9) (more to come: end to end, carry, older tests); `test_input_module_gate.py::test_osc_passthrough` (gate only); `test_audit3_run_stop.py`, `test_action_fixes.py`, `test_audit2_coverage.py` replace `OscRuntime` with a stand-in; `test_program_imports.py` (import order); `test_startup_settings_kept.py` (OSC tab setting); `test_main_shared_pieces.py::test_osc_clear_is_red_and_asks` | Output sending (not built); encoder mode (reserved) |
| Sound | `audio_player.py` 222 | `test_program_fixes.py` (3 sound tests), `test_bounded_waits.py::test_a_sound_is_not_waited_for_once_the_player_stops`, `test_threads.py::test_the_audio_player_stopped_right_after_starting_ends`, `test_play_sound_missing_file.py` (5) | Interrupt and Overlap modes, mode change while running, Stop during Sequential with a long queue |
| Speech | `tts.py` 224 | `test_action_tts.py` (8: the action's data and feedback only) | `TTSManager` queue modes, Stop, voice missing, WinRT missing, off-main-thread call |
| Tray | `system_tray.py` 344, `tray_memory.py` 77 | `test_tray_memory.py` (3), `test_audit3_startup.py::test_the_tray_icon_uses_the_shared_check`, `::test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray`, `test_audit2_startup_devices.py::test_the_tray_icon_follows_the_platform_qt_started_on`; TRAY-ONE checked off-screen by hand | Tray menu commands, close-to-tray event filter, one-time balloon, Explorer restart, `--start-minimized` |
| Look | `Style.qml` 227, `ColorInformation.qml` 19, `ui_scale_option.py` 108, `windows_scale_option.py` 68, two option QML 116, `theme/` 64 files ~4,900 | `test_ui_scale.py` (6), `test_colour_tokens.py` (2), `test_button_map_colours.py`, `test_tool_windows_fit`, `test_main_window_fits`, `test_pages_fit.py`, menu tests | Restart path of the Windows-scaling box, dark-mode switch while windows are open, Python drawing colours |
| Help / glossary | Help moved to page 01 (9 Oct); `glossary.md` 76 | `test_glossary_words.py` (3); Help tests are listed on page 01 | — |
| Shared widgets / foundations | ~25 QML files (~1,600 lines); `common.py`, `error.py`, `types.py`, `type_aliases.py` (~980) | Only through screens and unit tests that import them; `test_fsm.py`; `test_batch3_C1.py` (`TextInputDialog`, `DismissibleDialog`) | — |

Checked for this page: the eight test files above (`test_ui_scale`, `test_tray_memory`, `test_help_guide`, `test_glossary_words`, `test_input_module_gate`, `test_colour_tokens`, `test_action_tts`, `test_play_sound_missing_file`) run off-screen: 45 passed. OSC helpers run directly: `parse_port('')` = 8000, blank rename accepted, Axis sorts before Button, import C/E → Axis.

## 12. Review (user, 2026-10-06)

Approved by the user as recommended (2026-10-06, blanket approval of the remaining pages): every [code only] statement in section 8 is confirmed, except where a question's recommendation changes it; every question in section 9 is decided as its **Recommend** says. Where a recommendation and a section 8 statement disagree, the recommendation wins.

| Q | Decision |
|---|---|
| All | As recommended in section 9 |
| S51 | 2026-10-07 (D-09-S51-NEXTSOUND): a playback mode change applies from the next sound the player starts |
| Q19 | 2026-10-07 (D-09-Q19-SUPERSEDED): fsm.py is used and stays |
| S2-S4, S6, S8-S10, S12-S14, S16, S17, S19-S26, S38-S48, Q1-Q3, Q6 | 2026-10-09 (D-09-OSC-FILE, D-09-OSC-INPUT, D-09-OSC-FAULTS): OSC's own module file shared by every profile, permanent ids, server settings in OSC's Module Setup, per-input settings, small faults fixed |
| S16a, S40a | 2026-10-09 (D-09-OSC-LOCK, D-09-OSC-STOP): an input with actions can't switch between Axis and a button mode; held OSC buttons are released at Stop |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.
