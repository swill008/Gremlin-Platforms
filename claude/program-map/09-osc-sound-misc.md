# OSC, sound and speech, tray, look and help (and the leftovers)

Mapped read-only against the code at 4f6bdfa4 (6 Oct); sections 2, 4, 6, 10 and 11 brought up to date 9 Oct. Line numbers drift; re-check them before a step starts. **OSC was parked** (todo.md, 2 Oct) and was picked up 2026-10-09: decisions D-09-OSC-FILE (OSC's own module file, permanent ids, server settings in OSC's Module Setup), D-09-OSC-INPUT (per-input settings), D-09-OSC-FAULTS (small faults), D-09-OSC-LOCK (no Axis/button switch with actions) and D-09-OSC-STOP (held buttons released at Stop) change the OSC statements below; the batch was built 2026-10-09 (d7eaa746, aceb9267). A second batch the same day adds D-09-OSC-MONITOR (OSC Monitor), D-09-OSC-OUTPUT (targets and the Send OSC action), D-09-OSC-FEEDBACK (Feedback section, sync address), D-09-OSC-ENCODER (encoder mode), D-09-OSC-DISCOVERY (zeroconf Announce/Find) and D-09-OSC-ADDRESSES (addresses shown on labels): S90-S115, built 2026-10-09 (31676b11). A third batch the same day adds D-09-OSC-TABS (Module Setup tabs, OSC Setup… button, screenshot fixes), D-09-OSC-COMPANION (Add Companion, Companion templates, off/on values, Copy for Companion; Export Companion Page… not built: format not safe), D-09-OSC-LOOK (the Button Map's look) and D-01-HELP-OSC (Help chapter OSC): S116-S128, built 2026-10-09 (5c1dc480). Sound and speech are mapped here only at the system level (the player and the speech engine); the Play Sound and Text to Speech editors belong to the Actions page. A fourth set, decided 2026-10-10 (D-09-OSC-PAGE, D-09-OSC-DOCK, D-09-OSC-TOOLS, D-09-OSC-PATTERNS, D-09-OSC-FBROWS, D-09-OSC-ACTSTATE, D-09-OSC-EXTRAS; user: "go with your recommendations, approved"), rebuilds the OSC page on the Logical Device page's shared base and adds S129-S164, built in three batches (section 10, G-OSC28-G-OSC63); batch 1 (S129-S146) built 2026-10-10 (`osc_layout.py`, `OscPage.qml`, `OscMonitorPanel.qml`, `osc_companion_check.py` on the shared base; `OscDevice.qml` removed). The last part of section 2 lists every file in `gremlin/` and `qml/` that no other page names, so nothing is unmapped.

## 1. Purpose

- **OSC**: lets a network sender (Stream Deck through Bitfocus Companion, a phone app) press buttons and move axes in the program. OSC is an internal input (03 S90b), like the Keyboard and the Logical Device: one list of OSC inputs, kept in OSC's own module file and shared by every profile; each input has its own settings (mode, message or data, value source, range, trigger). While the profile runs, a packet that matches an input fires its actions like a stick input would. OSC also sends (D-09-OSC-OUTPUT, D-09-OSC-FEEDBACK): the Send OSC action and Feedback rows send to named targets (or back to the sender), so a Stream Deck or phone can show the program's state; the OSC Monitor shows every message in and out.
- **Sound and speech**: the Play Sound and Text to Speech actions play a file or speak text while the profile runs; Options sets how sounds overlap and which voice speaks.
- **Tray, look and help**: the tray icon lets the program run hidden and shows Running/Stopped; dark/light mode, UI scale and Windows scaling set how every window looks; the User Guide (F1) and the glossary set what the screens say.

## 2. Files

**OSC (about 10,000 lines in 26 files, recounted 2026-10-10; picked up 2026-10-09)**
- `gremlin/osc.py` (1032, changed 2026-10-09, 2026-10-10): `OscDevice` singleton, keeping its public name, now delegates to one shared `OscRows` (`OscDevice().rows`); `OscListener` (UDP server from python-osc); `OscRuntime` (start/stop, Listen, packet -> event, per-input auto-release timers; from the 2026-10-09 second batch also `hold_open` / `release_open` / `is_open` for the Monitor; the `incoming` signal carries the sender (host, port); per packet, in order: `osc_feedback.handle_incoming` (sync consumed), `osc_output.note_sender` / `note_received_type`, matching (also without a Run, so the Monitor names the inputs; inputs fire only during a Run), `osc_traffic.note`; and the encoder runtime (Auto format, axis step and clamp, pulses queued up to 32), D-09-OSC-ENCODER); parse helpers (`parse_port`, `parse_delay_ms`, `is_pressed`, `axis_value`, `guess_input_type`); `local_ipv4_addresses`, `default_bind_host`; from 2026-10-10 (D-09-OSC-TOOLS, batch 1): live value and last seen per input (`live`, `live_all`, `reset_live`, signal `liveChanged(uid)` throttled to 0.1 s per input; OX1, S141), `send_test(uid, kind, value)` (OX5, S145), `port_holder` / `bind_error_detail` (name the program holding the port through ctypes, Windows iphlpapi/kernel32; OX2, S142), `report_malformed` and python-osc server/dispatcher subclasses that log a malformed packet once per sender (OX3, S143), `OscListener.bound_port()`; a hook that patches `Configuration.set` (265-286; the server settings move to OSC's file, D-09-OSC-FILE).
- `gremlin/osc_rows.py` (412, new 2026-10-09, D-09-OSC-FILE / D-09-OSC-INPUT): the OSC input list, pure (no IO, no Qt). From 2026-10-10 (batch 1) it also holds the OSC page's `layout` (groups and order) and `names` (your names by uid): `set_layout(layout, names)` (no change, no dirty) and `mark_dirty()`, so a page change waits for Save like an input edit (`*`). `OscRow` (uid, input type, number, address label, mode, cmd_mode, data, source, range_min/max, trigger, delay_ms); `OscRows` (create, delete, set_label, update, by_uid, by_number, uid_of, identifier_of_uid, `matches(address, args)`, rows, to_dict/load_dict, dirty/mark_saved); `check_address`, `check_settings`, `type_of_mode`; `MODES` (button, axis, change; encoder added by D-09-OSC-ENCODER with `enc_format`, `enc_step`, `enc_output`; `type_of_mode(mode, enc_output)`), `CMD_MODES` (message, data).
- `gremlin/osc_device_file.py` (745, new 2026-10-09, D-09-OSC-FILE; from 2026-10-10 `load` reads and `save` writes the page's `layout` key and your names as the claim's `osc:<uid>` friendly names in the same one write as the inputs (`_put_layout`, `convert_friendly_keys`), batch 1): OSC's own module file (`store.path_of("osc")`, `osc.json`: `inputs` and `server`, other keys kept; writes through `gremlin.modules.store`, so module-file History records them). `path`, `load`, `save`, `save_if_dirty`, `read_server` / `write_server` / `clean_server`, `merge_profile_rows` (older profiles' rows into the file; `MergeResult` uid map, `current_uid_map` while such a profile loads), `backup_old` (`<name>.xml.v15.bak` / `.v14.bak`), `migrate_settings_from_config` (old `osc/connection/*` copied once). Second batch 2026-10-09: the new `server` keys (output, reply, discovery, feedback switches, sync, rate), `read_targets` / `write_targets` ("Default" made from `output_host` / `output_port` on first load) and `read_feedback` / `write_feedback`.
- `gremlin/osc_traffic.py` (new 2026-10-09, D-09-OSC-MONITOR): the OSC traffic log, last 200 messages in and out (`note(direction, address, args, peer, matched)`, `add_listener` / `remove_listener`, `recent`, `clear`); thread-safe, listeners called on the main thread. Fed by `OscRuntime` (in) and `osc_output` (out).
- `gremlin/osc_output.py` (247, new 2026-10-09, D-09-OSC-OUTPUT): sending; from 2026-10-10 a send failure also goes to the user log, once per address and target until the next Run (OX3, S143). `send`, `note_sender`, `note_received_type`, `resolve_target`, `reset`, `close_all` (clients closed at Stop via run_scope DRIVERS), `convert`, `received_type`, `last_sender`. `send(target_id, address, values, types=None)` (skips when OSC output is off or no Run, unless forced; python-osc `SimpleUDPClient`; notes "out" traffic), `resolve_target` (a target id, or "reply" = the last sender), `note_sender`, `note_received_type` (for type Auto).
- `gremlin/osc_feedback.py` (new 2026-10-09, D-09-OSC-FEEDBACK): Feedback at run time. `start(profile_path)` (end of `CodeRunner._start`) / `stop` (first in CUT_INPUT), `instance`; a main-thread 10 ms timer reads the sources and sends on change (mode; vJoy through `modules.output.vjoy_value`; Logical Device by uid or label; OSC input echo through `EventListener.joystick_event`); per-address rate limit that coalesces to the latest value; resends on `ModeManager.mode_changed` and when the profile path differs; `resend_all(reason)` (Run start, mode change, profile switch, sync), `handle_incoming(address, args, peer)` (True = the sync address, consumed before any input sees it).
- `gremlin/osc_discovery.py` (new 2026-10-09, D-09-OSC-DISCOVERY): zeroconf (`zeroconf` 0.147.0 with `ifaddr` 0.2.0, pinned in pyproject). `start`, `apply_settings`, `set_announce(on, port)` (advertise `_osc._udp`), `set_find(on)` (browse), `found()` (this PC's own announcement left out), `available`, `service_name`, `shutdown()`; one worker thread through `gremlin.threads`; `oscDevicesFound` queued to the main thread. `joystick_gremlin.py` calls `start()` before `app.exec` and `shutdown()` in `shutdown_cleanup`, and imports `osc_feedback_model` / `osc_monitor_model`; never blocks the main thread.
- `gremlin/ui/osc_monitor_model.py` (new 2026-10-09, D-09-OSC-MONITOR): `OscMonitorModel` (QML module Gremlin.Device): rows from `osc_traffic`, Pause, Clear, filter, Show outgoing, `addSettings(row)` for "Add as Input…"; while `active`, holds the port open (`OscRuntime.hold_open` / `release_open`). From 2026-10-10 the OSC page `qml/OscPage.qml` has the page bar's Monitor button (`toggleMonitor`, `showMonitor()`) and `openAddWith(settings)` (`qml/OscDevice.qml` removed); `main_commands.js` `tools.oscMonitor` and the Tools menu entry above History in `Main.qml` (01 S144).
- `gremlin/ui/osc_feedback_model.py` (new 2026-10-09, D-09-OSC-FEEDBACK): `OscFeedbackModel` (QML module Gremlin.Config; `DialogConfigureModule.qml` loads the section through `oscFeedbackLoader` inside `oscSectionsScroll`), the Feedback section's model (master switch, resend switches, sync address, rate, rows: add, edit, remove; sources and targets to pick from); writes OSC's file (`write_feedback`, `write_server`).
- `qml/WindowOscMonitor.qml` (66, new 2026-10-09, D-09-OSC-MONITOR; changed 2026-10-10, D-09-OSC-DOCK): the Pop out window only (OP7, S138), wrapping `OscMonitorPanel.qml`.
- `qml/OscFeedbackSection.qml` (new 2026-10-09, D-09-OSC-FEEDBACK): the **Feedback** section of OSC's Module Setup, under Server (03 S53b).
- `action_plugins/send_osc/` (new 2026-10-09, D-09-OSC-OUTPUT): the **Send OSC** action (functor calls `osc_output.send`; press/release uses the action's existing activation setting) and its editor `SendOscAction.qml` (05 S109-S111).
- `gremlin/osc_bulk.py` (110): Bulk capture in the Add dialog. Replaces three methods of `OscDeviceManagementModel` at import (20-22, 62-64); `OscBulkCapture` QML element.
- `gremlin/osc_persist.py` (48+): `osc_address(input_type, input_id)` / `osc_addresses()` give an input's address for labels (D-09-OSC-ADDRESSES: Button Map chips and rig labels, 07 S103; Home's last-pressed line through `module_model._osc_address`, 03 S53c). Replaces `InputIdentifier.label` and `linear_index` for every identifier so OSC inputs show as "OSC - <address>" (116-121). References to OSC inputs are stored by the input's uid (D-09-OSC-FILE): `resolve_osc_reference`, `osc_label`, `osc_linear_index`, `osc_rows`. Other uid users: `gremlin/validate.py` (rule check PROFILE-OSC-MISSING: a reference to an id OSC's file doesn't have), `gremlin/ui/device_pack.py` (the `in.osc` item, `missingOsc`, wires carry `<osc-uid>`), `gremlin/library_copy.py` (`_OSC_ITEM`), `gremlin/ui/logical_layout.py` (Assign Hardware lists OSC addresses).
- `gremlin/ui/osc_device_model.py` (769): `OscDeviceManagementModel`: from 2026-10-10 no longer the OSC page's list (that is `OscLayoutModel`); kept for the Add window, Import, Listen and Bulk capture on OSC's list (`createMappedInput`, `importInputs`, `inputAdded(uid)` so the page selects the new row, `inputSettings` / `updateInputSettings`), used by `OscPage.qml` and the Pop out `WindowOscMonitor.qml`; `OscInputIdentifier`; `_parse_import_line`.
- `gremlin/ui/osc_option.py` (487): the OSC host/port/auto-release editors (from 2026-10-09 `OscServerModel` also: targets add/edit/remove, found devices and Add as Target, `pcAddresses` with Copy, `discoveryAvailable`, Announce/Find through `osc_discovery`); with D-09-OSC-FILE they edit OSC's file (`server`) from OSC's Module Setup (03 S53a), and Options keeps one line with a button to it (01 S40a).
- `gremlin/ui/osc_settings_info.py` (34): `OscSettingsInfo.summary()`, the text in the "Listening for OSC" box.
- `qml/OscPage.qml` (790, new 2026-10-10, D-09-OSC-PAGE, batch 1): the OSC page on the shared pieces (`ControlFindBar` with "Address, your name, or group", All types / Buttons / Axes, page-bar buttons **OSC Setup…** and **Monitor**; `ControlTree` with the live value and last seen per row; `ActionPane`), its right-click menu (S135: Undo/Redo header; quick rows Add Action, Rename, Change Address…, Edit Settings… (several inputs: "Edit Settings of N Inputs…"), Copy for Companion, Send Test Press / Send Test Value, History; sections Row, Group, Add Inputs (Add…, Import…, Listen, Clear…), Groups, Order (By Address, By Your Name, Group Names A to Z)), the docked `OscMonitorPanel` with its grip and Pop out, and the Add / Import / address windows; Ctrl+Z / Ctrl+Y on `OscLayoutModel`. No footer. Replaces `qml/OscDevice.qml` (354, removed 2026-10-10: the old list with the Clear / Sort / Add / Import footer and the live `InputConfiguration` editor).
- `qml/OscAddDialog.qml` (819; from 2026-10-10 `openForKeys(keys, shared)` edits several inputs at once, blank = differs, OK applies only changed fields, S146; `startListen()` for Add Inputs › Listen): "OSC Input Mapper": Cmd, Change/Button/Axis (and Encoder from D-09-OSC-ENCODER: format, output, step, release delay; the Axis/button lock covers encoder axis vs pulses), Message only / Message + data, Trigger on message + delay, Listen, Bulk capture.
- `qml/OscImportDialog.qml` (98): paste addresses, one per line, with type suffixes.
- `qml/OscServerSection.qml` (157, new 2026-10-09, D-09-OSC-FILE): the **Server** section of OSC's Module Setup (Enabled, host, port, auto-release and its delay, pad args; from D-09-OSC-OUTPUT / D-09-OSC-DISCOVERY also OSC output, Reply to sender, Targets, this PC's addresses with Copy, Announce this PC, Find OSC devices with "Add as Target"); each change is checked and written to OSC's file at once (03 S53a).
- `qml/OscSetupTabs.qml` (new 2026-10-09, D-09-OSC-TABS): the tab bar **Server** · **Output** · **Feedback** · **Discovery** of OSC's Module Setup, loaded by `DialogConfigureModule.qml` for OSC (03 S53d, S116). Tab bodies: `qml/OscServerTab.qml` (Enabled, host, port, auto-release, delay, pad args), `qml/OscOutputTab.qml` (OSC output, Reply to sender, Targets with **Add Companion** via `OscServerModel.addCompanionTarget()`, this PC's addresses with Copy, 0.0.0.0 left out), `qml/OscFeedbackSection.qml` (Feedback, with Companion templates and off/on values), `qml/OscDiscoveryTab.qml` (Announce this PC, Find OSC devices). They take over from `OscServerSection.qml`'s single scrolling column.
- Companion helpers (D-09-OSC-COMPANION): `OscServerModel.addCompanionTarget()` (`gremlin/ui/osc_option.py`); `OscFeedbackModel.addTemplateRow(kind, params)` and row keys `off_value`, `on_value`, `template` (`gremlin/ui/osc_feedback_model.py`, `gremlin/osc_feedback.py`, `gremlin/osc_device_file.py`); `OscDeviceManagementModel.companionText(uid)` for **Copy for Companion** (`gremlin/ui/osc_device_model.py`, and from 2026-10-10 `OscLayoutModel.copyForCompanion(key)`, row menu in `qml/OscPage.qml`, whose page bar also has **OSC Setup…**, `signal.openOscModuleSetup`). **Export Companion Page…** is not built (format not safe, S123, G-OSC26); no export files.
- **Shared base (new 2026-10-10, D-09-OSC-PAGE, batch 1)**: `gremlin/ui/control_layout.py` (1292; `ControlLayoutModel`, the list model the Logical Device page and the OSC page share: rows, groups, order, selection, Find, the action pane draft/commit and page Undo; `LogicalLayoutModel` (06) becomes a subclass with no behaviour change), `qml/ActionPane.qml` (201; the action pane: title, ×, Close pane after OK, OK, width grip, running lock, unsaved prompt), `qml/ControlTree.qml` (575; group / parent / child rows, carets, multi-select, drag order, title + settings line), `qml/ControlFindBar.qml` (162; Find box, type box, Clear, filter ticks, extra-buttons slot, Undo bar); each takes the model as `layout`. Extracted from `gremlin/ui/logical_layout.py` and `qml/LogicalPage.qml`; mapped here and named on 06.
- `qml/OscMonitorPanel.qml` (405, new 2026-10-10, D-09-OSC-DOCK, batch 1): the OSC Monitor as a panel docked at the bottom of the OSC page (folded by default, drag grip, Pop out), also the body of the Pop out window. It holds the port only while visible, unfolded and its page is open; Add as Input… is hidden while a profile runs and emits `addAsInputRequested` to the page's Add window (S137-S140). Test: `test_osc_monitor_panel.py` (1).
- `gremlin/ui/osc_layout.py` (701, new 2026-10-10, D-09-OSC-PAGE, batch 1): `OscLayoutModel` (QML module Gremlin.Device), the OSC page's subclass of `ControlLayoutModel`: one parent per OSC input (title = address, your name beside it, no Hide system name), its actions as child rows, the settings line (`settings_line`, S134), live value and last seen (`live_fields`, `last_seen_text`, `lastSeenText`, follows `osc.liveChanged`; S141); slots `keyOfUid`, `uidOf`, `addressOf`, `kindOf`, `sendTest` (S145), `changeAddress` (one Undo step), `editSettingsFor` / `applySettings` (several inputs, S146), `copyForCompanion` (S122), `clearAll` (one Undo step). `OscLayoutStore` keeps groups, order and your names on the shared `OscRows` (`set_layout`), never the file itself; `osc_device_file` writes them at Save. `qml/OscPage.qml` (above) is the page.
- `gremlin/osc_companion_check.py` (149, new 2026-10-10, D-09-OSC-TOOLS, batch 1): the Companion setup check (S144): `check(...)` lists, line by line, OSC enabled and the port open (the holder named), OSC output on, a Companion target, its port against Companion's 12321 (a warning, not a fault), Feedback on when there are rows; each OK or what to change; reads only. `OscCompanionCheck` (QML module Gremlin.Device, `run()`, `lines`) behind the Output tab's **Check Companion setup** button (`qml/OscOutputTab.qml`).
- `qml/help/osc.js` (new 2026-10-09, D-01-HELP-OSC): the Help chapter **OSC** (page 01 S128 owns the Help book).
- `qml/OptionOscModuleSetup.qml` (41, new 2026-10-09, D-09-OSC-FILE): the one Options row, "OSC settings are in OSC › Module Setup", with its button (01 S40a).
- `qml/OptionOscInputHost.qml`, `OptionOscOutputHost.qml`, `OptionOscAutorelease.qml`: removed 2026-10-09 (D-09-OSC-FILE); the server rows are `qml/OscServerSection.qml` in OSC's Module Setup, and Options' OSC section (group Server, key `osc/connection/module-setup`) is one line, `qml/OptionOscModuleSetup.qml`.
- Elsewhere, OSC parts: `joystick_gremlin.py` 570-809 (registers the seven old `osc/connection/*` settings, read once by `migrate_settings_from_config`), `gremlin/profile.py` (version 16: reads `<osc-device>` of version 14/15 profiles into OSC's file, writes none), `gremlin/modules/store.py` (reloads OSC after a write of its file, like `_reload_logical_device`), `gremlin/code_runner.py` 390/428 (start/stop at Run/Stop), `gremlin/modules/runtime.py` 22-27 (OSC always forwarded, no claims), `gremlin/event_handler.py` 104 (display name), `gremlin/ui/backend.py` 277 (no highlighting for OSC; Save, `*` and Discard cover OSC's file), `gremlin/action_label.py` 166 (patches the model's `data`), `gremlin/ui/module_model.py` 1654, 1896-1925 (OSC card and its Module Setup rows, friendly names by uid, Server section), `gremlin/history_profile.py` 35, `gremlin/swap_devices.py` 21 (OSC left out), `gremlin/ui/device_pack.py`, `gremlin/library_copy.py`, `gremlin/ui/logical_layout.py`, `gremlin/validate.py` (references by uid), `qml/DeviceList.qml` 221-255 (the OSC tab), `qml/Main.qml` (`_oscPageLoader` → `OscPage.qml`, `oscPane()`, `openOscMonitor()`, mode).
- `tools_osc/` (outside `gremlin/`): the standalone tester used before the OSC page existed (`osc_listener.py`, `osc_send_test.py`, README, PATH_B.md, WIRE.md, a patch). Its README still says "Tools → Options → osc … port 9000" and "Activate the profile".

**Sound and speech (system level)**
- `gremlin/audio_player.py` (222): `AudioSample` (decode with miniaudio, volume, play, cancel, bounded `block`); `AudioPlayer` singleton (queue, playback thread, Sequential / Interrupt / Overlap); registers `action/play-sound/playback-mode`.
- `gremlin/tts.py` (242): `TTSManager` singleton (Qt WinRT `QTextToSpeech`, queue: Queue Back / Queue Front / Interrupt, voice); registers `action/text-to-speech/voice`. From 2026-10-10 (to-do 81) `TTSManager.close()` stops and releases the engine at exit, called by `joystick_gremlin.shutdown_cleanup()`; with the engine left alive the process took 5.0 s to end after `os._exit`, now 0.02 s.
- Callers: `action_plugins/play_sound/__init__.py` 51-75 (`AudioPlayer().enqueue`), `action_plugins/text_to_speech/__init__.py` 47-67 (`TTSManager().enqueue`, `${current_mode}`), `gremlin/code_runner.py` 376-377 / 435-436 (start/stop), `joystick_gremlin.py` 277-283 (stop at quit), `gremlin/ui/backend.py` 355 (`emitConfigChanged` re-reads the playback mode), `gremlin/ui/option.py` 709-760 (`TTSVoiceSelectionModel`), `qml/OptionTTSVoiceSelection.qml` (30).

**Tray**
- `gremlin/ui/system_tray.py` (344): `SystemTrayIcon` (Win32 tray icon and hidden helper window, idle/active icon, menu: Show/Hide Gremlin-Platforms, Run Profile/Stop Profile, Exit Gremlin-Platforms; minimize/close to tray; one-time balloon; re-adds the icon when Explorer restarts).
- `gremlin/ui/tray_memory.py` (77): gives memory back while hidden (`enter_tray`, `leave_tray`, `release`, `trim_working_set`).
- `qml/Main.qml` 86-98 (`trayed`, `enterTray`, `leaveTray`), `joystick_gremlin.py` 689-710 (settings `minimize-to-tray`, `tray-notice-shown`, old `close-to-tray` carried over), 967-971 (icon made unless off-screen), 1000-1001 (`--start-minimized`).

**Look: theme, colours, UI scale, Windows scaling**
- `qml/Style.qml` (227): the `Gremlin.Style` singleton: dark and light colour tokens, `dp()`, `fitWidth/fitHeight`, fonts, menu tokens.
- `qml/ColorInformation.qml` (19) + `gremlin/ui/util.py` 466-499 `ColorInformation`: hands the Universal accent/background/foreground to Python (used by `gremlin/ui/action_image_generator.py` `_ink`, 78-82).
- `theme/GremlinStyle/` (33 control files + `impl/`): the Qt Quick Controls style the whole program uses (Universal, sized by `Style.dp`). `theme/Gremlin/Base`, `theme/Gremlin/Compact`: custom and compact controls. `theme/Gremlin/Menus`: one menu look, context menus, command palette, `commands.js`, `menu_model.js`. 64 QML/JS files, about 4,900 lines. `theme/Gremlin/AGENTS.md`, `Compact/AGENT.md`: rules for extending them.
- `gremlin/ui/ui_scale_option.py` (117): `ui/general/ui-scale` 70-200 %, `active_scale()` (100 when Windows scaling is on), Python `dp()`, `UiScaleModel`. `qml/OptionUiScale.qml` (50).
- `gremlin/ui/windows_scale_option.py` (75): `ui/general/disable-windows-scaling`, `WindowsScaleModel` (`runningDisabled`). `qml/OptionWindowsScale.qml` (66): check box + Restart / Later / Cancel.
- `joystick_gremlin.py` 20-42 (reads `configuration.json` itself before Qt loads and sets `QT_ENABLE_HIGHDPI_SCALING=0`), 63-69 (`QT_QUICK_CONTROLS_STYLE=GremlinStyle`), 674-688 (registers dark-mode, ui-scale, disable-windows-scaling), 945-977 (colour refresh timer, `bumpThemeRevision`), 1012-1024 (app font `dp(15)`, theme import path, Style singleton), 1125-1130 (puts the variable back before a restart).
- `gremlin/ui/backend.py` 489-495 (`useDarkMode`, `uiScale`); `qml/Main.qml` 100-103 and 1345-1351 (set `Style.isDarkMode` at start and on `configChanged`).

**Help and glossary**
- The Help book and the Help window moved to page 01 (one Help, 01 S128-S139, 9 Oct): `qml/help/` (10 chapter files), `DialogHelp.qml`, `help_search.js`, `HelpSearchBar.qml`, `help_links.js`, `Pulse.qml`. `qml/help_topics.js` (24) is now only the old entry points over the book; `DialogButtonMapGuide.qml` is gone.
- `claude/glossary.md` (108): the approved words (2 Oct, added to since). Kept by `test/unit/test_glossary_words.py`.

**Shared QML widgets (no other page owns them; mapped here)**. The shared pieces built 9 Oct (DangerButton, ConfirmDialog/`confirm.js`, SearchBox, MessageLine, SectionHeading, EmptyState, UndoBar, FilePicker, RenameField; 01 S135, S140-S143) are on page 01.
- Dialogs: `DismissibleDialog.qml` (265, 23 users: confirm/cancel popup), `TextInputDialog.qml` (147, 6 users: one-line text with `allowBlank`, validator), `ErrorDialog.qml` (98).
- Small controls: `IconButton.qml`, `IconCheckBox.qml`, `InputButton.qml` (279: the row button of the Keyboard list; the OSC page used it until 2026-10-10), `JGListView.qml`, `JGSpinBox.qml`, `JGTabButton.qml`, `JGText.qml`, `JGTextField.qml`, `JGToolButton.qml` (toolbar button, icon-only when narrow), `LabelValueComboBox.qml`, `CompactSwitch.qml` + `CompactSwitchIndicator.qml`, `BetterProgressBar.qml`, `HorizontalDivider.qml`, `LayoutHorizontalSpacer.qml`, `LayoutVerticalSpacer.qml`, `Triangle.qml`, `DragDropArea.qml`, `DropMarker.qml`.
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
| OSC inputs (uid, type, number, address, per-input settings) | one shared `OscRows` (`gremlin/osc_rows.py`), reached through `OscDevice().rows`; kept in OSC's module file (D-09-OSC-FILE) | `OscLayoutModel` (from 2026-10-10: Change Address, Edit Settings, delete, clear, each a page Undo step); `OscDeviceManagementModel` (Add, Import, Listen); `osc_bulk.model_on_learned`; `osc_device_file.load` / `merge_profile_rows`; Device Library Restore, Device Pack Import, History restore (through `store`) |
| OSC input last value | `OscDevice.Input.value` | `OscRuntime._emit_button`, `_on_main` |
| OSC inputs on disk | OSC's module file `osc.json` key `inputs` (`osc_device_file.save`); version 14/15 profiles' `<osc-device>` is read once and merged | `osc_device_file`; module-file History records it (D-09-OSC-FILE) |
| OSC page groups, order and your names (2026-10-10, batch 1) | in memory on the shared `OscRows` (`layout`, `names`; `set_layout`, `mark_dirty`); on disk in `osc.json` key `layout` and the claim's `osc:<uid>` friendly names, written with the inputs in one write at Save | `OscLayoutStore` (through `OscRows`, never the file); `osc_device_file.load` / `save`; Discard reads the file again |
| OSC page Undo / Redo (2026-10-10) | `ControlLayoutModel._undo/_redo` in `OscLayoutModel` (in memory, 50 steps) | page edits; dropped when OSC's file is read again (S131) |
| Live value and last seen per input (2026-10-10) | `osc.py` `live` (memory only) | `OscRuntime` on each matched message, `send_test`; `OscLayoutModel` shows it |
| Actions on OSC inputs | profile `inputs[OSC GUID]` | Configuration panel (Actions page); `_drop_profile_mappings` on delete/clear (osc_device_model.py 234-246) |
| OSC server settings | OSC's module file key `server`: `enabled` (true), `host` ("" = every address on this PC), `port` (8001), `output_host` ("127.0.0.1"), `output_port` (8000), `autorelease_no_arg` (true), `autorelease_delay_ms` (250), `pad_args`; copied once from `configuration.json` `osc/connection/*` (D-09-OSC-FILE) | OSC's Module Setup Server section; `OscRuntime` reads them at start and when they change (`oscServerSettingsChanged`) |
| OSC targets | OSC's module file key `targets`: `[{id, name, host, port}]`; first load makes "Default" from `output_host` / `output_port` (D-09-OSC-OUTPUT) | Server section (Targets list, Find's "Add as Target"); Send OSC actions and Feedback rows refer to a target by id, or "reply" |
| OSC feedback rows and switches | OSC's module file key `feedback` (rows: id, enabled, source {kind, device, input}, target, address, min, max, type) and `server` keys `feedback_enabled`, `resend_run`, `resend_mode`, `resend_profile`, `sync_enabled`, `sync_address` ("/gremlin/sync"), `feedback_rate` (50) (D-09-OSC-FEEDBACK) | Feedback section (`osc_feedback_model`); `osc_feedback` reads them |
| OSC output and discovery switches | `server` keys `output_enabled` (true), `reply_to_sender` (true), `announce` (false), `find_devices` (false) | Server section; `osc_output`, `osc_discovery` |
| Encoder settings | each input's `enc_format` ("auto"), `enc_step` (0.05), `enc_output` ("axis") in `inputs` (D-09-OSC-ENCODER) | Add window, Edit Settings, Import (E) |
| OSC traffic log | `osc_traffic` (last 200, in memory only) | `OscRuntime` (in), `osc_output` (out); Clear in the Monitor |
| Last sender, last type per address | `osc_output` (memory only) | `OscRuntime` on every incoming packet |
| Found OSC devices | `osc_discovery.found()` (memory only) | zeroconf browser |
| OSC settings copy at first start | Only `osc/connection/*` values that differ from the defaults are copied into OSC's file (`migrate_settings_from_config`); with none, nothing is written and a fresh install has no OSC file until the first real save (keeps Home's first selected card on the stick). [2026-10-09, D-09-OSC-FILE (4)] |
| Listener and Listen state | `OscRuntime._listener`, `_learn`, `_hold_learn`, cached behaviour flags, output host/port | `CodeRunner.start/stop`, Add dialog (Listen, Bulk), the patched `Configuration.set` (`sync_bind`) |
| Page-only OSC state | `OscLayoutModel` selection, open parents, filters, the pane draft; `OscDeviceManagementModel._mode`, `_capture_only`, `_bulk*`; `OscPage.qml` Monitor shown / folded and height | Main.qml (mode); lost when the page unloads; the Monitor height is kept in program settings (`toolRowState("oscPage")`, S137) |
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
| Home → OSC tab (or OSC card) | `DeviceList.qml` 221-245 `uiState.setCurrentTab("osc")` | `Main.qml` `_oscPageLoader` loads `OscPage.qml` (2026-10-10; was `OscDevice.qml`), `setMode(currentMode)` |
| Click a row / an action row | `ControlTree.qml` on `OscPage.qml` | `OscLayoutModel` selection (multi-select, drag order); an action row opens the shared `ActionPane` (draft, OK, Close pane after OK); quick row **Add Action** opens a new draft (S129, S130) |
| Right-click › Rename / Clear Name (your name) | `OscPage._renameRow`, `_askClearName` | `OscLayoutModel.setUserName` → `OscLayoutStore.set_user_label` → `OscRows.set_layout` (names); one page Undo step |
| Right-click › Change Address… | `OscPage._askChangeAddress` → `TextInputDialog` | `OscLayoutModel.changeAddress(key, address)`: one Undo step; a refusal shows on the page's message line |
| Right-click › Edit Settings… (one or several inputs) | `OscPage.editSettings(keys)` → `OscAddDialog.openForKeys` | `editSettingsFor(keys)` / `applySettings(keys, changed)`: only changed fields, S16a-locked inputs named; one Undo step (S146) |
| Right-click › Copy for Companion | `OscPage.copyForCompanion` | `OscLayoutModel.copyForCompanion(key)` (S122) |
| Right-click › Send Test Press / Send Test Value | `OscPage.sendTestPress` / `sendTestValue` | `OscLayoutModel.sendTest(key, kind, value)` → `osc.send_test` (S145) |
| Right-click › Row › Delete… | `OscPage._askDeleteRows` → `Confirm.ask` | `deleteParents(keys)`: inputs and their actions, one Undo step (S26) |
| Right-click › Add Inputs › Clear… | `OscPage.askClear` → `Confirm.ask` ("Clear OSC inputs?", Clear OSC Inputs) | `OscLayoutModel.clearAll()`: one Undo step (S27) |
| Right-click › Order › By Address / By Your Name / Group Names A to Z; Group, Groups sections | `OscPage._layoutMenuModel` | `sortBySystem` / `sortByName` / `sortGroupNames`; `addGroup`, `moveSelected`, `removeGroup`; kept in OSC's file at Save (S28, S133) |
| Undo / Redo (Ctrl+Z / Ctrl+Y, menu header, Undo bar) | `OscPage` shortcuts, `ControlFindBar` Undo bar | `ControlLayoutModel.undo` / `redo` (50 steps, S131) |
| Find, type filter, Ungrouped / No actions in this mode | `ControlFindBar` on `OscPage` ("Address, your name, or group"; All types / Buttons / Axes) | `OscLayoutModel.setFilter` (S136) |
| Page bar **OSC Setup…** | `OscPage.openSetup` | `signal.openOscModuleSetup` (S117) |
| Add Inputs › Add… → OK | `OscPage.openAdd` → `OscAddDialog` | `OscDeviceManagementModel.createMappedInput`; `inputAdded(uid)` → the page selects the new row (S12, S13); an address that exists only selects that row |
| Add Inputs › Listen (one message) | `OscPage.listen` → `OscAddDialog.startListen` | `listenForCommand()` → `OscRuntime.listen_once()` (starts the listener even when not running; the Listen belongs to this window, S20) → first packet → `learned` → `commandCaptured` → dialog binds and closes |
| Add → Listen with Bulk capture | OscAddDialog | `OscBulkCapture.start` → `start_bulk` → `listen_bulk`; each packet → `model_on_learned` → `createMappedInput` (same address within 0.3 s ignored); keeps listening |
| Add → Listen again / Cancel / close / untick Bulk | OscAddDialog | `cancelListen()` → `OscRuntime.cancel_listen()`; the port closes when nothing else needs it (S20) |
| Add dialog opens Listen | OscAddDialog | `backend.pauseInputHighlighting("osc-add")` / resume on close |
| Add Inputs › Import… → OK | `OscPage.openImport` → `OscImportDialog` | `importInputs(text)`: one address per line, must start with "/"; suffixes as S23; existing addresses skipped |
| OSC page edits → Save | `OscRows.set_layout` / `mark_dirty` (`*`) | File › Save Profile → `osc_device_file.save_if_dirty`: inputs, layout and your names in one write (2026-10-10) |
| Output tab › **Check Companion setup** | `qml/OscOutputTab.qml` | `OscCompanionCheck.run()` → `osc_companion_check.check` (reads only; S144) |
| OSC Module Setup → Server: host, port, output host/port, Enabled, auto-release, delay | Server section (03 S53a; D-09-OSC-FILE) | `osc_device_file.write_server` → `oscServerSettingsChanged` → `OscRuntime` rebinds, starts or stops at once |
| Options → OSC | one line + button "OSC settings are in OSC › Module Setup" (01 S40a) | opens OSC's Module Setup |
| Run | `CodeRunner.start` (code_runner.py 390) | `OscRuntime.start()`: reads settings, binds UDP, or shows an error |
| Stop / quit | `CodeRunner.stop` 428; `shutdown_cleanup` (joystick_gremlin.py 284) | CUT_INPUT "OSC releases": `OscRuntime.release_held()` (held buttons released while actions still run, S40a), then `OscRuntime.stop()` |
| UDP packet arrives | python-osc thread → `OscListener._on_message` → `_from_thread` | `incoming` signal (queued to main) → `_on_main`: Listen capture; matched address → `EventListener.joystick_event` |
| Address-only button packet (auto-release on) | `_on_main` 495-501 | `QTimer.singleShot(delay)` → `_release_button` with the mode at press time |
| Profile load / New profile | `Profile.from_xml` / `__init__` | OSC inputs stay (one shared list); a version 14/15 profile's `<osc-device>` → `osc_device_file.merge_profile_rows` (one-time note, references follow the uid map) |
| Save | File › Save Profile | `osc_device_file.save_if_dirty` (OSC's file when changed); the profile (version 16) has no `<osc-device>` |
| Device Library Save/Restore/Export, Device Pack Import, History restore of OSC's file | `store.replace` / `write_text` | one write, one History entry; OSC reloads (`oscDeviceReloaded`) |
| Mode change | Main.qml → `OscPage.mode` | `OscLayoutModel.setMode(mode)`, `OscDeviceManagementModel.setMode`: rows show that mode's actions |
| OSC page bar "Monitor" (`OscPage.toggleMonitor`) / Tools › OSC Monitor (`Main.openOscMonitor` → `OscPage.showMonitor`, the page with the panel unfolded) | `qml/OscMonitorPanel.qml` docked on the OSC page, or the Pop out window `qml/WindowOscMonitor.qml` (D-09-OSC-DOCK) | `OscMonitorModel`: `osc_traffic.add_listener`; `OscRuntime.hold_open` while visible, unfolded and its page open, `release_open` when folded, hidden or left |
| Monitor "Add as Input…" on a "no input" row (hidden while running) | `OscMonitorPanel.qml` | emits `addAsInputRequested`; `OscPage.openAddWith(settings)` opens its Add window with the address and values filled in |
| Send OSC fires | `action_plugins/send_osc` functor | `osc_output.send(target, address, values, types)` |
| A Feedback source changes (mode, vJoy, Logical Device, OSC input) | `osc_feedback` hooks | rate-limited `osc_output.send` per row |
| Run start / mode change / profile switch or auto-load | `CodeRunner.start`, mode and profile hooks | `osc_feedback.resend_all(reason)` when that switch is on |
| A message arrives on the sync address | `OscRuntime` → `osc_feedback.handle_incoming` | full resend; consumed (never reaches an input) |
| Server section: Announce this PC / Find OSC devices | `OscServerSection.qml` | `osc_discovery.set_announce` / `set_find`; found list → "Add as Target" → `write_targets` |
| Quit | `joystick_gremlin.py` shutdown | `osc_discovery.shutdown()` |

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
| Logical Device | Feedback reads Logical Device controls (D-09-OSC-FEEDBACK) | Assign Hardware lists OSC inputs (`logical_layout.py`) |
| Shared control page base (2026-10-10, D-09-OSC-PAGE) | `OscLayoutModel` subclasses `control_layout.ControlLayoutModel` (rows, groups, order, Find, selection, the action pane draft/commit, page Undo, the Run lock `_refused`); `OscPage.qml` uses `ControlFindBar.qml`, `ControlTree.qml`, `ActionPane.qml`, shared with the Logical Device page (06) | — |
| OSC runtime from the page (2026-10-10) | `osc_layout` reads `osc.live` / `liveChanged` (live value, last seen) and calls `osc.send_test`; `osc_companion_check` reads OSC's file and the runtime (`port_holder`) | `liveChanged` refreshes the row |
| OSC's file from the page (2026-10-10) | `OscLayoutStore` writes groups, order and your names to `OscRows.set_layout` only; `osc_device_file.load` / `save` read and write them (key `layout`, the claim's `osc:<uid>` friendly names) with the inputs in one write | `oscDeviceReloaded` / file read again → the page rebuilds and drops its Undo steps |
| Window placement (01) | `qml/ActionPane.qml` reads and saves `WindowPlacement.actionPaneWidth` / `closePaneAfterOk` | — |
| vJoy output, mode manager, profile switch | Feedback watches vJoy buttons and axes, the current mode and profile switches (D-09-OSC-FEEDBACK) | — |
| Actions (Send OSC) | — | `send_osc` calls `osc_output.send` (05 S109-S111) |
| Clock, logs, Windows (2026-10-10, D-09-OSC-TOOLS) | `osc.py` uses `gremlin.clock` (last seen, throttle), `gremlin.log_once` and the user logger (OX3), and Windows iphlpapi/kernel32 through ctypes to name a port's holder (OX2) | — |
| Network (UDP out, zeroconf) | `osc_output` sends with python-osc; `osc_discovery` announces and browses `_osc._udp` with `zeroconf` | incoming packets via `OscListener` |
| Button Map, Home OSC card | — | OSC labels and last-pressed show the address (D-09-OSC-ADDRESSES, 07 S103) |
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
| zeroconf announce / browse | `osc_discovery` (one worker through `gremlin.threads`, plus zeroconf's own threads) | `set_announce(False)` / `set_find(False)`; `shutdown()` at quit | Found devices reach the UI through `oscDevicesFound` on the main thread; the main thread never waits on the network (D-09-OSC-DISCOVERY). |
| OSC traffic delivery | `osc_traffic.note` from the OSC thread | — | Listeners are called on the main thread (queued). |
| Encoder pulses | `OscRuntime` (main thread) | Stop | Each tick a press and a release after the delay; at most 32 queued. |
| Feedback poll and rate limit | `osc_feedback.start` (main-thread 10 ms timer) | `stop()` first in CUT_INPUT at Stop | Reads the sources and sends on change; at most `feedback_rate` messages a second per address, coalesced to the latest value. Signals `oscFeedbackChanged`, `oscTraffic`, `oscDevicesFound` (gremlin/signal.py). |
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
| R6 | Duplicated logic | `qml/OscDevice.qml` 35 | The OSC GUID typed as a literal instead of read from the model (`guid`) or `ids.OSC`. | CLOSED 2026-10-10: `OscDevice.qml` removed; `OscPage.qml` reads the device from `OscLayoutModel` |
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
- **S1** It should listen for OSC only while the profile runs (and during Add → Listen, and while the OSC Monitor panel is unfolded on the OSC page or popped out, S139), and stop listening at Stop and at quit. [changed 2026-10-10, user: D-09-OSC-DOCK] (was: while the OSC Monitor window is open) [changed 2026-10-09, user: D-09-OSC-MONITOR] [user confirmed 2026-10-06; was code only] [test-plan: TB-02 lists only the toolbar; system-maps: map 3 rows B, C, R]
- **S2** It should be possible to turn OSC off in OSC's Module Setup → Server → Enabled; off means no socket is opened at Run. [help: OSC] [changed 2026-10-09, user: D-09-OSC-FILE] (was: Options → OSC → Connection → Enabled)
- **S3** It should listen on the host and port set in OSC's Module Setup → Server. A blank host (the default) means every address on this PC (binds 0.0.0.0), so a LAN address that changes (DHCP) never breaks it; a typed host must be an IP address or a name and is checked before it is saved. The settings are kept in OSC's module file and travel with Device Library, Export and Device Pack. [help: OSC] [changed 2026-10-09, user: D-09-OSC-FILE] [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: Options; the saved LAN address of this PC)
- **S4** Changing any server setting should take effect at once, also while running: turning Enabled on starts the listener, host or port rebinds it, off stops it; a failed bind is tried again when the settings change. [changed 2026-10-09, user: D-09-OSC-FILE] (was: Enabled, host and port only; turning Enabled on while running did nothing, G-OSC11)
- **S5** A port that is blank, not a number or outside 1-65535 should fall back to the default. [user confirmed 2026-10-06; was code only]
- **S6** The default input port should be 8001 (intended; the user can change it) and the default output port 8000, one value each, shown the same everywhere (Module Setup, the Listening box, the listener); a blank or bad input port falls back to 8001. [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: an open question; B15 suggested 8000 and 9000)
- **S7** If the port cannot be opened (in use, address gone), Run should still run the rest of the profile and show one error titled "Could not bind OSC on host:port.", whose detail names the program holding the port when it is in use ("Port N is in use by <name> (PID n)." or "…in use by another program.", S142), and log it to the user log and the program log (S143). [changed 2026-10-10, user: D-09-OSC-TOOLS] (was: the error only) [user confirmed 2026-10-06; was code only] [tracker: D16 titled "Error"]
- **S8** OSC on by default should not give a bind error on every Run: the default host is every address on this PC, not a saved LAN address. [changed 2026-10-09, user: D-09-OSC-FILE] (was: also not bound to the LAN address; opening only when there are OSC inputs (Q5) is not part of this decision, see G-OSC7)
- **S9** The old output host and port (127.0.0.1:8000) should become the first target, "Default", in the Targets list (S96); Send OSC and Feedback send to targets. [changed 2026-10-09, user: D-09-OSC-FILE] [changed 2026-10-09, user: D-09-OSC-OUTPUT] (was: shown as "used once OSC output is built"; before that Q3 hide until something sends)

### OSC inputs (the OSC page)
- **S10** The OSC page should list every OSC input (one list shared by every profile, kept in OSC's module file) as a row titled by its address (and your name for it, when given), with its settings line (S134), live value and last seen (S141), and its actions for the current mode as child rows, like the Logical Device page (S129). [changed 2026-10-10, user: D-09-OSC-PAGE] (was: "Button n - /address" or "Axis n - /address" with an action count) [changed 2026-10-09, user: D-09-OSC-FILE] (was: the loaded profile's OSC inputs)
- **S11** It should be locked (greyed, no clicks) while the profile runs, except feedback rows (S155). [changed 2026-10-10, user: D-09-OSC-FBROWS, batch 2] [user confirmed 2026-10-06; was code only] [test-plan: system-maps editorLocked list]
- **S12** Add… (right-click menu › Add Inputs, S135) should create an input with the typed address and the chosen mode (Button, Axis or Change) and settings (S16), select it, and open it in the shared action pane (S129, S130); Axis mode makes an axis input, the others a button input. The new input gets a permanent id and the lowest free number. [changed 2026-10-10, user: D-09-OSC-PAGE] (was: the Add button in the footer; actions on the right) [changed 2026-10-09, user: D-09-OSC-INPUT] (was: Button or Axis only)
- **S13** After Add or Import, the row added should be the one selected, also for an Axis and after Sort. [tracker: APP4] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S14** Adding an input that already exists (same address, and in Message + data the same values) should select the existing input, not make a second one; several inputs may share an address when their data or value source differ. [changed 2026-10-09, user: D-09-OSC-INPUT] (was: one input per address)
- **S15** Addresses should match without regard to case (`/Deck/1` = `/deck/1`) and are stored in lower case. [user confirmed 2026-10-06; was code only]
- **S16** Each input should keep its own settings, set in the Add window and saved in OSC's file: mode (Button, Axis, Change, Encoder (S108-S111)), Message only / Message + data (with the values captured or typed), value source (P1..Pn, P1 first), axis range (default 0 to 1), Trigger on message and its delay (left blank = the server default). They work at run time as S38-S39d say. [changed 2026-10-09, user: D-09-OSC-INPUT] [changed 2026-10-09, user: D-09-OSC-ENCODER] (was: work per input or be hidden; Q2)
- **S16a** An OSC input that has actions (in the open profile, any mode) should not switch between Axis and the button modes (Button, Change, Message + data); the change is refused with "Remove this input's actions first: an axis and a button use different actions." Switching among the button modes is allowed (as GremlinEx). [changed 2026-10-09, user: D-09-OSC-LOCK]
- **S17** Listen (single capture) should fill the address from the next message that arrives, offer its values as sources (P1..Pn), bind it with the window's settings and close the dialog; it ends on that message by design. [changed 2026-10-09, user: D-09-OSC-INPUT] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S18** Listen should tell the user if OSC is off or the port can't be opened ("Could not start OSC listener."), naming the program that holds the port when it is in use (S142), and log it (S143). [changed 2026-10-10, user: D-09-OSC-TOOLS] [user confirmed 2026-10-06; was code only]
- **S19** Bulk capture should add one input per new address, each with the window's settings, until Bulk capture is unticked; the same address twice within 0.3 s counts once. [OscAddDialog tip: "intended for simple devices such as the Stream Deck"] [changed 2026-10-09, user: D-09-OSC-INPUT]
- **S20** Cancel, closing the Add dialog, Stop in the Listening box, unticking Bulk capture, or a single capture ending should end listening for the window that is listening (another window's Listen is left running) and, when no profile runs and the OSC Monitor panel is folded (or the OSC page left, S139), close the port. [changed 2026-10-10, user: D-09-OSC-DOCK] (was: the OSC Monitor window closed) [tracker: APP13] [changed 2026-10-09, user: D-09-OSC-FAULTS] [changed 2026-10-09, user: D-09-OSC-MONITOR] [changed 2026-10-10, user FL-S20: a Listen is owned by the window that started it; only that window handles the capture or can cancel it, which also fixes S17/S19 when the OSC page and the OSC Monitor are both open]
- **S21** The "Listening for OSC" box's button should be Stop, and it stops listening (not only hides the box). [tracker: APP17] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S22** Import should add one input per line that starts with "/", skip lines that don't and inputs that exist, select the row it added (also after Sort), and say how many were added and skipped. [changed 2026-10-09, user: D-09-OSC-INPUT] [changed 2026-10-09, user: D-09-OSC-FAULTS]
- **S23** Import suffixes, after a space or a comma (`/a B`, `/a, B`): A axis, B button, BNP button with Trigger on message, C change, E an encoder axis with format Auto (S108); an unknown suffix gives a button and a note naming the line. [tracker: B17] [changed 2026-10-09, user: D-09-OSC-INPUT] [changed 2026-10-09, user: D-09-OSC-ENCODER] (was: E a button with the note "encoder not supported yet")
- **S24** Editing an address should keep the input's actions, friendly name and every reference (same permanent id). [changed 2026-10-09, user: D-09-OSC-FILE]
- **S25** An address should never be blank, should start with "/" and be unique (with its data and source, S14); a refused edit says why in the shared message line. [tracker: APP11] [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: duplicate refused silently)
- **S26** Delete should ask the shared question (Confirm, "You can restore it from Tools › History.") and then remove the input and its actions in every mode, as one page Undo step (S131). [changed 2026-10-10, user: D-09-OSC-PAGE] [tracker: G-LIBLEAK note: OSC Delete leak closed] [changed 2026-10-09, user: D-09-OSC-FAULTS] (was: no question; Q6 Undo)
- **S27** Clear… (right-click menu, S135; no footer, S136) should ask first with the shared question and then remove all inputs and their actions, as one page Undo step (S131). [changed 2026-10-10, user: D-09-OSC-PAGE] (was: a red Clear button in the footer; text "in the current profile") [user confirmed 2026-10-06; was code only]
- **S28** Order › **By Address** (right-click menu, S135) should order the inputs A-Z by address within each group, as Logical's Order › By System Name does; dragging rows sets your own order, and the order is kept in OSC's file. [changed 2026-10-10, user: D-09-OSC-PAGE] (was: a one-way Sort button) [user confirmed 2026-10-06; was code only]
- **S29** OSC inputs should be listed in Logical Device → Assign Hardware for a button. [help: Assign hardware and actions]
- **S30** The OSC page should have no Appearance panel. [help: Appearance] [tracker: AU-52] [confirmed 2026-10-10, user: D-09-OSC-PAGE (OP5: not now)]
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

### OSC Monitor
- **S90** The OSC Monitor (the panel at the bottom of the OSC page, S137: the page bar's **Monitor** button, or Tools › OSC Monitor) should list the last 200 OSC messages in and out: time, In/Out, address, values, sender (in) or target (out), and the inputs it matched, or "no input". [changed 2026-10-10, user: D-09-OSC-DOCK] (was: a separate window) [changed 2026-10-09, user: D-09-OSC-MONITOR]
- **S91** It should have **Pause**, **Clear** (no question: the list is temporary and kept only in memory), a filter on the address, and a **Show outgoing** switch; columns **In** / **Out**, **From** / **To**, **Input**. The headers never overlap, and the address column is wide enough for a typical address; a longer one is cut with … and shows in full on hover (as do values, From / To and Input). [changed 2026-10-09, user: D-09-OSC-MONITOR] [changed 2026-10-09, user: D-09-OSC-TABS]
- **S92** On a "no input" row, **Add as Input…** should open the Add window with that address and its values filled in; it is hidden while the profile runs (S140). [changed 2026-10-10, user: D-09-OSC-DOCK] [changed 2026-10-09, user: D-09-OSC-MONITOR]
- **S93** While the Monitor panel is unfolded on the OSC page (or popped out) the listening port should be held open, also with no Run; folding it or leaving the page closes the port unless a Run or Listen still needs it (S1, S20, S139). [changed 2026-10-10, user: D-09-OSC-DOCK] (was: while the Monitor window is open) [changed 2026-10-09, user: D-09-OSC-MONITOR]

### OSC output (Server section)
- **S94** **OSC output** (on by default) should be the master switch for everything OSC sends: off, Send OSC and Feedback send nothing. [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S95** **Reply to sender** (on by default): the target "Reply to sender" means the host and port of the last message received; off, sends to it are skipped. [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S96** The **Targets** list should hold named targets (name, host, port), added, edited and removed in the Server section; the host is checked like the listening host. The first load makes "Default" (a fixed id) from the old output host and port (127.0.0.1:8000); the old Output host / Output port fields leave the Server section. Removing a target asks the shared question (01 S140). Send OSC and Feedback rows refer to a target by its permanent id, so renaming it keeps them. [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S97** The Output tab (S116) should show this PC's addresses and the listening port, each with **Copy** (display only; nothing is saved). 0.0.0.0 ("every address") is never listed as an address, since a sender can't send to it. [changed 2026-10-09, user: D-09-OSC-OUTPUT] [changed 2026-10-09, user: D-09-OSC-TABS] (was: in the Server section; 0.0.0.0 could be listed)

### Send OSC action
- **S98** The Send OSC action should send one message: a target (or Reply to sender), an address (starts with "/"), and values, either a fixed list or the input's value (a button 1/0; an axis scaled from -1..1 to Min..Max). [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S99** Each value should have a type: **Auto** (the type last received on that address, else Float), **Int**, **Float**, **Bool** or **Text**. [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S100** It should send on press, on release, or both (chosen in the action). [changed 2026-10-09, user: D-09-OSC-OUTPUT]
- **S101** It should send only while the profile runs and OSC output is on, and every send shows in the Monitor as Out. [changed 2026-10-09, user: D-09-OSC-OUTPUT]

### Feedback
- **S102** OSC's Module Setup should have a **Feedback** section (03 S53b): a master switch (on by default; it does nothing until there are rows) and rows, each with on/off, source, target, address, Min, Max and type. From batch 2 the rows are added and edited on the OSC page (S153-S156); the Feedback tab keeps the switches and a read-only list (S154). [changed 2026-10-10, user: D-09-OSC-FBROWS, batch 2] [changed 2026-10-09, user: D-09-OSC-FEEDBACK]
- **S103** A row's source should be one of: the current mode's name, a vJoy button, a vJoy axis, a Logical Device control, an OSC input's own value (echo), or an action's state (S157, batch 2) [changed 2026-10-10, user: D-09-OSC-ACTSTATE, batch 2]; a value is sent within the row's Min..Max. [changed 2026-10-09, user: D-09-OSC-FEEDBACK]
- **S104** While the profile runs (and OSC output is on), a row should send when its source changes, at most 50 messages a second per address (the rate is a setting). [changed 2026-10-09, user: D-09-OSC-FEEDBACK]
- **S105** Every row should be sent again at Run start, at a mode change and at a profile switch or auto-load, each with its own switch (all on by default). [changed 2026-10-09, user: D-09-OSC-FEEDBACK]
- **S106** **Sync address** (on by default, "/gremlin/sync"): a message on it should send every row again (rows whose target is Reply to sender go to the one who sent the sync); a sync message never reaches an input. [changed 2026-10-09, user: D-09-OSC-FEEDBACK]
- **S107** All of these settings (output and reply switches, targets, feedback rows and switches, discovery switches, encoder settings) should be kept in OSC's module file and travel with Device Library Save/Restore/Export, History and Device Pack; an edit in the OSC page or OSC's Module Setup marks OSC's file changed (`*`) and History records it (S44, S46, S47). [changed 2026-10-09, user: D-09-OSC-OUTPUT] [changed 2026-10-09, user: D-09-OSC-FEEDBACK]

### Encoder
- **S108** Encoder mode should be offered. Its format: **Auto** (default: only 0 and 1 seen means the direction format; the first other value, such as a negative, makes it the signed format until Stop), **1 = clockwise, 0 = counter-clockwise**, or **+n and −n** (+n clockwise, −n counter-clockwise). [changed 2026-10-09, user: D-09-OSC-ENCODER]
- **S109** Output **Axis** (default): the input is an axis that moves by **Step size** x direction for each tick (0.05 unless changed), kept within -1..1. [changed 2026-10-09, user: D-09-OSC-ENCODER]
- **S110** Output **Pulses clockwise** / **Pulses counter-clockwise**: the input is a button that, for each tick in that direction, presses and releases after **Release after … ms**. [changed 2026-10-09, user: D-09-OSC-ENCODER]
- **S111** The Add window and Edit Settings should show the encoder's Format, Output, Step size and Release after … ms; Import's E suffix makes an encoder axis with Auto (S23). [changed 2026-10-09, user: D-09-OSC-ENCODER]

### Discovery (zeroconf)
- **S112** **Announce this PC** (off by default) should advertise `_osc._udp` on the listening port so senders can find the program. [changed 2026-10-09, user: D-09-OSC-DISCOVERY]
- **S113** **Find OSC devices** (off by default) should list the `_osc._udp` devices found on the network, each with **Add as Target** (adds it to the Targets list). [changed 2026-10-09, user: D-09-OSC-DISCOVERY]
- **S114** Discovery should never block the window, and should stop cleanly at quit. [changed 2026-10-09, user: D-09-OSC-DISCOVERY]

### OSC addresses on labels
- **S115** Button Map chips and rig labels, and the Home OSC card's last-pressed line, should show an OSC input by its address (e.g. "/fire") instead of "OSC Button 1" (07 S103). [changed 2026-10-09, user: D-09-OSC-ADDRESSES]

### OSC setup tabs and the OSC page
- **S116** OSC's Module Setup should show its settings in four tabs, **Server** · **Output** · **Feedback** · **Discovery** (03 S53d): Server = Enabled, host, port, auto-release and its delay, pad args (S2-S6); Output = OSC output, Reply to sender, Targets with **Add Companion**, this PC's addresses and port with Copy (S94-S97, S119); Feedback = S102-S107 with Companion templates and off/on values (S120, S121); Discovery = Announce this PC and Find OSC devices (S112-S114). No tab needs a long half-page scroll, and nothing shows behind the window's bottom buttons. [changed 2026-10-09, user: D-09-OSC-TABS] (was: Server and Feedback sections one under the other in one scrolling area)
- **S117** The OSC page should have an **OSC Setup…** button (in the page bar, 01 S58a; S136) that opens OSC's Module Setup (the same window as the OSC card's Module Setup…). [changed 2026-10-10, user: D-09-OSC-PAGE] [changed 2026-10-09, user: D-09-OSC-TABS]
- **S118** With no OSC input selected, the OSC page should show no action pane, as the Logical Device page (the pane opens on a row, S129); nothing stands empty. [changed 2026-10-10, user: D-09-OSC-PAGE] (was: the right side says "Select an input to see its actions") [changed 2026-10-09, user: D-09-OSC-TABS]

### General OSC first; Companion helpers
- **S119** OSC should stay general: every setting works with any OSC sender or receiver, and the Companion helpers below only fill in those generic settings (a target, Feedback rows, plain text); nothing in the program depends on Companion. **Add Companion** (Output tab) adds the target "Companion" = 127.0.0.1:12321 (Companion's OSC listener), or updates it if it exists, and says which it did. [changed 2026-10-09, user: D-09-OSC-COMPANION]
- **S120** **Companion templates** (Feedback tab) should add a ready Feedback row to the Companion target: **Custom variable** (`/custom-variable/<name>/value`, default name `gremlin_mode`, type Text, source the current mode), **Key text** (`/location/<page>/<row>/<col>/style/text`) and **Key colour** (`/location/<page>/<row>/<col>/style/bgcolor`, with an off value and an on value). The row is an ordinary Feedback row afterwards and can be edited like any other. From batch 2 the Feedback tab keeps only Custom variable (a mode row, tied to no input); Key text and Key colour are added from an input's feedback on the OSC page (S154). [changed 2026-10-10, user: D-09-OSC-FBROWS, batch 2] [changed 2026-10-09, user: D-09-OSC-COMPANION]
- **S121** Every Feedback row may have an **off value** and an **on value**: when set, an on/off source (a vJoy button, an OSC button) sends them instead of Min/Max, e.g. two colours "#333333" / "#2a7a46"; a value written "r g b" is sent as three integers (0-255). Left blank, Min/Max are sent as before. [changed 2026-10-09, user: D-09-OSC-COMPANION]
- **S122** **Copy for Companion** (an OSC input's right-click menu on the OSC page, S135) should copy, as plain text, the settings for a Companion Generic OSC connection (this PC's address, the listening port, UDP) and the key's press and release actions for that input (e.g. Send integer `/sd/fire` 1 on press, 0 on release). [changed 2026-10-09, user: D-09-OSC-COMPANION]
- **S123** **Export Companion Page…** is not offered: the Companion v5 page format can't be written safely (Companion v5.0.7's import doesn't validate buttons or actions; a wrong shape imports silently with empty values; the format is undocumented). Copy for Companion (S122) is the supported route; to-do 71 keeps the export idea (G-OSC26). [changed 2026-10-09, user: D-09-OSC-COMPANION] (was: built only if the format proved safe)
- **S124** Everything the program sends to Companion should use Companion's current OSC API only: `/location/<page>/<row>/<col>/...` and `/custom-variable/<name>/value`; never the legacy bank commands (`/press/bank/...`, `/style/.../bank/...`). [changed 2026-10-09, user: D-09-OSC-COMPANION]
- **S125** Text the program gives for Companion's Generic OSC module (Copy for Companion, Help) should work for module versions 2.8.2 and 3.0.0 alike. [changed 2026-10-09, user: D-09-OSC-COMPANION]
- **S126** Messages as Companion's Generic OSC module sends them should all reach inputs correctly: integers, floats, text, several values, T/F booleans and messages with no value (a no-value press needs Trigger on message). [changed 2026-10-09, user: D-09-OSC-COMPANION]

### OSC look and Help
- **S127** The OSC windows (OSC page, OSC Module Setup tabs, Add and Import windows, OSC Monitor) should follow the Button Map's visual theme: its Style tokens, section headings, spacing, tab bar, list rows and the shared pieces (01 S140-S143). [changed 2026-10-09, user: D-09-OSC-LOOK]
- **S128** Help should have an **OSC** chapter (01 S128) right after Logical Device, covering the OSC page, the setup tabs, the Monitor, Feedback, Discovery and **Use with Companion** (step by step, both directions), with a link to the Send OSC topic (which stays in Configuration and actions with the other actions); topics moved into it keep their ids so links still work. [changed 2026-10-09, user: D-01-HELP-OSC]

### OSC page on the shared base (2026-10-10, batch 1)
- **S129** The OSC page should work as the Logical Device page does (06 S79-S84), on the same shared pieces (`control_layout.py`, `ActionPane.qml`, `ControlTree.qml`, `ControlFindBar.qml`): a row per input with its actions as child rows, groups, your own order by drag, Find, multi-select, the right-click menu (S135) and the shared action pane (draft, OK, Close pane after OK, width, unsaved prompt, locked while running); it differs only where OSC needs it (S132, S135, S136). The pane is the OSC page's only action editor: the old live editor (`OscDevice.qml` and its live `InputConfiguration` path) is removed. [changed 2026-10-10, user: D-09-OSC-PAGE (OP1, OP10)]
- **S130** A new OSC input with no actions should show **No actions** and **Add Action** (row, menu and pane), so its first action can be added; Add, Import, Listen and Bulk capture inputs included. [changed 2026-10-10, user: D-09-OSC-PAGE (OP2); gap vs S12, 05 Q4/G10: today a new input shows nothing (`backend.getInputItem`, `profile.py` ~2086-2093)]
- **S131** The OSC page should have its own Undo / Redo (50 steps, the shared Undo bar) for every page change: add, import, address change, settings edits, your names, groups, order, delete, clear and pane OK, with the rules of 06 S83 (no step for a change to nothing; steps dropped when OSC's file is read again); History records OSC's file as before (S47). [changed 2026-10-10, user: D-09-OSC-PAGE (OP3)] (was: no page Undo, G-OSC16)
- **S132** The OSC page should not offer **Hide system name**: the address is the input's identity and always shows; your name for an input shows beside it. [changed 2026-10-10, user: D-09-OSC-PAGE (OP4)]
- **S133** A group on the OSC page may hold buttons and axes together. [changed 2026-10-10, user: D-09-OSC-PAGE (OP11)]
- **S134** Under each input's title a settings line should say its type and settings, e.g. "Axis · Source value: P1 · Min: 0 · Max: 1" or "Button · Trigger on message · 250 ms", in the words of the Add window (glossary). [changed 2026-10-10, user: D-09-OSC-PAGE (OP12)]
- **S135** The right-click menu should be the Logical Device page's, with OSC's rows: quick rows **Change Address…** (in place of Assign Hardware), **Edit Settings…**, **Copy for Companion** (S122), **Send Test Press** / **Send Test Value** (S145), **Add Action**, **History**; then the sections **Row**, **Group**, **Add Inputs** (**Add…**, **Import…**, **Listen**), **Groups**, **Order** (**By Address** in place of By System Name). **Clear…** is in the menu (S27). [changed 2026-10-10, user: D-09-OSC-PAGE (OP14, row menu)] **Clear…** sits in the **Add Inputs** section, after Listen (red, asks first). [changed 2026-10-10, lead: placement within D-09-OSC-PAGE]
- **S136** The Find bar should be the shared one (01 S141): placeholder "Address, your name, or group", type filter **All** / **Buttons** / **Axes** (no Hats), no "No hardware writer" filter. The page bar (01 S58a) holds **OSC Setup…** (S117) and **Monitor** (S137). The page has no footer: Clear…, Add… and Import… are in the right-click menu (S135). [changed 2026-10-10, user: D-09-OSC-PAGE (OP14, Find)] (was: footer with Clear / Sort / Add / Import) The main window's **Move inputs with no actions to the end** tick is hidden on the OSC page (the Find bar has the **No actions in this mode** filter instead). [changed 2026-10-10, lead: placement within D-09-OSC-PAGE]

### OSC Monitor panel (2026-10-10, batch 1)
- **S137** The OSC Monitor should be a panel docked at the bottom of the OSC page, folded by default, unfolded and folded by the page bar's **Monitor** button or its own heading, with a drag grip to set its height (remembered). It keeps everything of S90-S92. [changed 2026-10-10, user: D-09-OSC-DOCK (OP6)]
- **S138** There should be no separate OSC Monitor window of its own (`WindowOscMonitor.qml` becomes only the Pop out window, wrapping the panel); the panel's **Pop out** shows it in a window of its own while wanted, and closing that window puts it back in the page. Tools › OSC Monitor opens the OSC page with the panel unfolded (01 S144). [changed 2026-10-10, user: D-09-OSC-DOCK (OP7)] (was: a Monitor window from Tools and the OSC page)
- **S139** The panel should hold the port only while it is unfolded on the OSC page or popped out; folding it or leaving the OSC page releases it, unless a Run or Listen still needs it (S1, S20, S93). [changed 2026-10-10, user: D-09-OSC-DOCK (OP8)]
- **S140** **Add as Input…** should be hidden while the profile runs (the page is locked, S11). [changed 2026-10-10, user: D-09-OSC-DOCK (OP13)]

### OSC tools (2026-10-10, batch 1)
- **S141** Each input's row should show its live value (a button's pressed state, an axis's value) and when a message last reached it ("last seen 3 s ago", "never"), also with no Run while the port is open; display only, nothing saved. [changed 2026-10-10, user: D-09-OSC-TOOLS (OX1)]
- **S142** When the port can't be opened because it is in use, the error (titled "Could not bind OSC on host:port.", S7) should add in its detail the program holding it, as Windows reports the port's owner: "Port N is in use by <name> (PID n).", or "Port N is in use by another program." when Windows can't tell. [changed 2026-10-10, user: D-09-OSC-TOOLS (OX2)]
- **S143** OSC errors should be logged with the system's own message: a bind failure to the user log and the program log (e.g. WinError 10048, which was not logged); a send failure to the user log once per address and target until the next Run; a packet that can't be read once per sender. [changed 2026-10-10, user: D-09-OSC-TOOLS (OX3)]
- **S144** A **Companion setup check** (OSC's Module Setup, Output tab, beside Add Companion) should check, line by line, what Companion needs: OSC enabled and the port open, OSC output on, a Companion target, the target's port matching Companion's OSC listen port (12321 by default; a different port is a warning, not a fault, since the user may change it in Companion), and, when there are Feedback rows, Feedback on; a port held by another program is named. Each line says OK or what to change. It only reads and reports. [changed 2026-10-10, user: D-09-OSC-TOOLS (OX4)]
- **S145** **Send Test Press** (a button input) and **Send Test Value** (an axis input) in the right-click menu should hand that input a message as if it had come from the network (a press then a release after the input's delay; an axis value typed in), so its actions can be tried without the sender; it fires actions only while the profile runs, updates the live value (S141) with or without a Run, and is not shown in the Monitor (it is not network traffic). [changed 2026-10-10, user: D-09-OSC-TOOLS (OX5)]
- **S146** **Edit Settings…** on several selected inputs should edit them together: a field that differs between them shows blank and is left as it is unless changed; OK applies the changed fields to each, refusing (and naming) any input S16a locks; one page Undo step. [changed 2026-10-10, user: D-09-OSC-TOOLS (OX6)]

### OSC address patterns (2026-10-10, batch 2)
- **S147** An input's address may be an OSC pattern (`*`, `?`, `[..]`, `{a,b}`): one input answers every matching address and keeps its state per address: a button is pressed while any of its addresses is pressed (OR), an axis takes the last value received, and Change and encoder inputs keep their last value per address. [changed 2026-10-10, user: D-09-OSC-PATTERNS (OX7 Q1 A)]
- **S148** An incoming message whose address is itself a pattern should reach the exact-address inputs it matches, never pattern inputs. When an exact input and pattern inputs both match a message, the exact input gets it and the patterns don't; overlapping pattern inputs all fire. Replaces S39d for patterns. [changed 2026-10-10, user: D-09-OSC-PATTERNS (OX7 Q2, Q3)]
- **S149** Outgoing addresses (Send OSC, Feedback rows) should refuse patterns, saying why. [changed 2026-10-10, user: D-09-OSC-PATTERNS (OX7 Q4)]
- **S150** The event an OSC input fires should carry the address that was received (`Event.osc_address`), so scripts and conditions can tell which address of a pattern input sent it. [changed 2026-10-10, user: D-09-OSC-PATTERNS (OX7 Q5)]
- **S151** Bulk capture should skip an address an existing input (exact or pattern) already answers. [changed 2026-10-10, user: D-09-OSC-PATTERNS (OX7 Q6)]
- **S152** Change Address… should show why an address is refused on an error line inside the dialog (the shared one-line text dialog gains an optional error line), not after it closes. [changed 2026-10-10, user: D-09-OSC-PATTERNS (OX7 Q7)]

### Feedback rows on the OSC page (2026-10-10, batch 2)
- **S153** Feedback rows should be shown and edited on the OSC page: a row whose source is an OSC input shows under that input, as may any row with **Show under this input** set (key `input`); every other row is in the group **Feedback not tied to an input**. [changed 2026-10-10, user: D-09-OSC-FBROWS (OX8 Q1)]
- **S154** Feedback rows are added and edited only on the OSC page. OSC's Module Setup Feedback tab keeps the master and resend switches, the sync address, the rate, the Custom variable template and a read-only list of the rows (S102, S120). [changed 2026-10-10, user: D-09-OSC-FBROWS (OX8 Q2)]
- **S155** Feedback rows may be edited while the profile runs, and an edit takes effect at once. [changed 2026-10-10, user: D-09-OSC-FBROWS (OX8 Q3)]
- **S156** Under an input its actions come first, then its feedback rows; adding, editing or removing a feedback row is a page Undo step (S131). [changed 2026-10-10, user: D-09-OSC-FBROWS (OX8 Q4, Q5)]

### Feedback from action states (2026-10-10, batch 2)
- **S157** A Feedback row's source may be an action's state: a Smart Toggle's on/off, a Tempo's last press (long = on, short = off), or the profile's Running / Paused. Actions report their state to one registry, read by the existing 10 ms Feedback poll (no new timer). [changed 2026-10-10, user: D-09-OSC-ACTSTATE (OX9F Q1, Q2)]
- **S158** When an action is used in several places, the state is on if any of them is on. A row whose action isn't in the current profile sends nothing and says "not in the current profile". [changed 2026-10-10, user: D-09-OSC-ACTSTATE (OX9F Q3, Q4)]

### OSC extras (2026-10-10, batch 3)
- **S159** Conditions and macros should read OSC inputs like stick inputs (by permanent id; the last value kept, 02 S41); a macro's Record opens the port while it records. [changed 2026-10-10, user: D-09-OSC-EXTRAS (to-do 62)]
- **S160** A **sender allow-list** (Server tab; empty = everyone) should accept OSC only from the IP addresses and ranges listed (CIDR, e.g. 192.168.1.0/24); Listen and Bulk capture obey it; it travels with OSC's file (S107). [changed 2026-10-10, user: D-09-OSC-EXTRAS (to-do 63)]
- **S161** An axis input should have **Invert** and a **deadzone**, applied before any action; a curve may come later. [changed 2026-10-10, user: D-09-OSC-EXTRAS (to-do 64)]
- **S162** **Import TouchOSC Layout…** should read a `.tosc` file and add an input per control: an XY pad as two axes, a radio or grid as Change, the others by their kind; it adds no target. [changed 2026-10-10, user: D-09-OSC-EXTRAS (to-do 66)]
- **S163** Scripts should be able to use OSC inputs (like stick inputs) and send OSC only to named targets (no raw host and port). [changed 2026-10-10, user: D-09-OSC-EXTRAS (to-do 67)]
- **S164** An encoder input should offer acceleration presets (Off by default): turning fast multiplies the axis step or the pulses, up to a cap. [changed 2026-10-10, user: D-09-OSC-EXTRAS (to-do 69)]

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

- **OSC-LAYOUT-SAVE** (fixed 2026-10-10, batch 1): the OSC page's groups, order and your names were written to OSC's file at once, apart from the inputs. Now they sit on `OscRows` (`set_layout`, `mark_dirty`) and wait for Save (`*`), written with the inputs in one write; Discard drops them. Tests: `test_osc_layout_save.py` (3).
- **OSC-LISTEN-OWNER** (fixed 2026-10-10): a Listen in one window was handled by every open OSC window (page and OSC Monitor), adding the input twice with each window's settings (S17/S19). Now `OscRuntime` keeps the window that started the Listen (`_learn_owner`, `listens_for`); found as a CI order-dependent failure of `test_osc_e2e.py`. Test: `test_listen_reaches_only_the_model_that_started_it`.

**Code differs from spec or rule (OSC; picked up 2026-10-09)**
- **G-OSC1** Three input-port defaults (8000 / 8001 / 8000 for blank) and input = output 8000 when unset. (S6, R5) [tracker: B15] Fixed by D-09-OSC-FAULTS (built 2026-10-09).
- **G-OSC2** Output host/port are stored and logged but no code sends OSC. (S9, Q3) Resolved by D-09-OSC-OUTPUT and D-09-OSC-FEEDBACK (S94-S107): Send OSC and Feedback send to targets (built 2026-10-09, 31676b11).
- **G-OSC3** Add → OK after an Axis selects the wrong row: `listenBound.emit(rowCount() - 1)` (osc_device_model.py 137) while the list sorts Axis before Button (checked: `['/a', '/b']`); also wrong after Sort. Actions then go to another input. (S13) [tracker: APP4] Fixed by D-09-OSC-FAULTS (built 2026-10-09).
- **G-OSC4** Rename accepts a blank address (checked: `set_label('/b', '')` → `''`) and one without "/"; the dialog lacks `allowBlank: false` (OscDevice.qml 40-55); a duplicate is refused silently. (S25) [tracker: APP11] Fixed by D-09-OSC-FAULTS (built 2026-10-09).
- **G-OSC5** Cancel/close after Listen leaves the UDP port open until the next Run/Stop (`cancel_listen` 336-342 does not stop the listener). (S20) [tracker: APP13] Fixed by D-09-OSC-FAULTS (built 2026-10-09).
- **G-OSC6** "Listening for OSC" box has only OK, which hides the box but keeps listening. (S21) [tracker: APP17 note] Fixed by D-09-OSC-FAULTS (built 2026-10-09).
- **G-OSC7** OSC starts on every Run (enabled by default, LAN IP), with an error each time the bind fails. (S8) [tracker: APP5] Fixed by D-09-OSC-FILE in part (blank host, no saved LAN address); opening only when there are OSC inputs (Q5) was left for later. Rest built 2026-10-09 (Q5 answer): at Run the port opens only when the profile has OSC inputs (`osc.profile_uses_osc()`); Listen/Bulk open it on demand and close it after.
- **G-OSC8** Change saved as Axis; Message + data, Trigger on message and delay never passed on (OscAddDialog.qml 65-70, 88-91/260). (S16) [tracker: B16] Fixed by D-09-OSC-INPUT (built 2026-10-09).
- **G-OSC9** Import: C and E become plain axes, BNP and B both plain buttons (checked). (S23) [tracker: B17] Fixed by D-09-OSC-INPUT (built 2026-10-09).
- **G-OSC10** One raw thread per packet; settings read per packet. (R7, S43) [tracker: AU-67]
- **G-OSC11** Turning Enabled on while running does not start the listener (`sync_bind` returns early when no listener, osc.py 432); only host/port/enabled are watched, other keys are read per packet. Fixed by D-09-OSC-FILE (built 2026-10-09).
- **G-OSC12** Auto-release timers are not cancelled at Stop or by a new press: a release from an earlier press can land during a later hold. (S39) Fixed by D-09-OSC-INPUT (built 2026-10-09).
- **G-OSC13** OSC empty-state text talks about sticks. [tracker: AU-58 (in progress, OSC part left)]
- **G-OSC14** "Ok" before "Cancel" in both OSC dialogs (OscAddDialog.qml 257, OscImportDialog.qml 72). [tracker: E1 note] Fixed by D-09-OSC-FAULTS (built 2026-10-09).
- **G-OSC15** OSC model `dataChanged` ranges: `createIndex(self.rowCount(), 0)` one past the end (osc_device_model.py 134, 228, 257). [tracker: AU-65 note: "left with OSC"] 2026-10-10: the OSC page's list is now `OscLayoutModel`; `OscDeviceManagementModel` is no longer shown as a list, so this matters only if it is again (not re-checked).
- **G-OSC16** No Undo for OSC add/rename/delete/clear (Undo exists on Logical Device, Module Setup, Calibration, Configuration). (Q6) Fixed by D-09-OSC-FILE / D-09-OSC-FAULTS in part (Delete asks; OSC's file is restorable from History); no page Undo (built 2026-10-09). Page Undo decided 2026-10-10 (D-09-OSC-PAGE, S131) and built 2026-10-10 (G-OSC30): fixed.
- **G-OSC17** `tools_osc/README.md` describes the old flow (lower-case "osc" section, port 9000, "Activate the profile").
- **G-OSC18** OSC Module Setup claims are read for the card but ignored at run time. (R1, Q4)
- **G-OSC19** OSC inputs were kept in each profile and the server settings in program settings, with references by number. (S44, S44a, S48) Fixed by D-09-OSC-FILE (built 2026-10-09).
- **G-OSC20** An OSC input with actions can be switched between Axis and a button mode in Edit Settings. (S16a) Fixed 2026-10-09 (D-09-OSC-LOCK): built in d7eaa746 (`osc_device_model.updateInputSettings` refuses; `inputSettings` "locked" greys the other type; test_osc_uimodel::test_type_change_refused_while_the_input_has_actions).
- **G-OSC22** Encoder mode was reserved, not offered; Import E made a button with a note. (S16, S23, S108-S111) Resolved by D-09-OSC-ENCODER (built 2026-10-09).
- **G-OSC23** No way to see what a sender sends, nothing sends feedback, and senders can't find the program. (S90-S107, S112-S114) Resolved by D-09-OSC-MONITOR, D-09-OSC-FEEDBACK and D-09-OSC-DISCOVERY (built 2026-10-09).
- **G-OSC24** Feedback sources are polled every 10 ms (main-thread timer) rather than pushed by their owners. (S104) [FB-run note, 2026-10-09] Open.
- **G-OSC25** A Feedback row whose source is the mode name and whose type is numeric (Int/Float/Bool) still sends text. (S103) [FB-run note, 2026-10-09] Open.
- **G-OSC26** Export Companion Page… (S123): not built: format not safe (v5 import doesn't validate buttons or actions; checked against Companion v5.0.7 source, 2026-10-09). Copy for Companion is the supported route; to-do 71 keeps it. Parked.
- **G-OSC27** Screenshot faults: Monitor headers overlap and addresses are cut, 0.0.0.0 listed as an address, stray "Re…" text behind Module Setup's bottom buttons, half-page scrolling in Module Setup, an empty right side on the OSC page. (S91, S97, S116, S118) Being fixed by D-09-OSC-TABS (2026-10-09).
- **G-OSC21** At Stop, an OSC button still held was not released; Stop only cancelled the auto-release timers. (S40a) Fixed 2026-10-09 (D-09-OSC-STOP): `OscRuntime.release_held()` runs in the CUT_INPUT stage before "input off" (code_runner), so actions see each release once; `stop()` calls it too (test_osc_run::test_stop_releases_held_buttons_while_callbacks_still_run).

**OSC rewrite (decided 2026-10-10; open until built)**
- **G-OSC28** (batch 1, fixed 2026-10-10) S129: The OSC page had its own list, footer and live editor, not the Logical Device page's shared pieces. Now `qml/OscPage.qml` on `ControlFindBar` / `ControlTree` / `ActionPane` with `OscLayoutModel` (`gremlin/ui/osc_layout.py`); `qml/OscDevice.qml` and its live `InputConfiguration` path removed. Tests: `test_osc_layout.py`, `test_osc_page_e2e.py`, `test_control_layout_base.py`.
- **G-OSC29** (batch 1, fixed 2026-10-10) S130: A new OSC input with no actions shows nothing, so its first action can't be added (`backend.getInputItem`, `profile.py` ~2086-2093). Fix first, failing test first. 2026-10-10 (GAP-OP2): still open on today's live `getInputItem` path (S12); `test_first_action_empty_input.py` shows `Library.draft` gives any empty input its first action, so it closes with S129 (OP1, OP10), when the OSC page uses the shared pane and the live editor is removed. 04 S68 unchanged (an input with no actions is not written). Closed with G-OSC28: the OSC page uses the shared pane (`test_osc_layout.py::test_a_new_input_with_no_actions_takes_its_first_action`, `test_osc_page_e2e.py::test_map_to_vjoy_in_the_shared_pane_binds_it_with_undo_and_redo`); S12 holds.
- **G-OSC30** (batch 1, fixed 2026-10-10) S131: No page Undo on the OSC page. Now `ControlLayoutModel` Undo / Redo (50) on `OscLayoutModel`; Add window, Change Address, Edit Settings, delete, clear, groups and order are steps (`test_osc_layout.py`).
- **G-OSC31** (batch 1, fixed 2026-10-10) S132: the OSC page's Rename has no Hide system name; your name shows beside the address (`test_osc_layout.py::test_your_name_shows_beside_the_address_and_never_hides_it`).
- **G-OSC32** (batch 1, fixed 2026-10-10) S133: No groups on the OSC page. Now groups (any input type), kept in OSC's file (`test_osc_layout.py::test_groups_order_and_names_are_kept_in_osc_json`, `test_osc_page_e2e.py::test_groups_and_order_are_kept_in_osc_json_across_a_reload`).
- **G-OSC33** (batch 1, fixed 2026-10-10) S134: No settings line under an input's title. Now `osc_layout.settings_line` (`test_osc_layout.py::test_settings_line_words`).
- **G-OSC34** (batch 1, fixed 2026-10-10) S135: The row menu lacked the Logical sections and Change Address…, Edit Settings…, Send Test, Order › By Address. Now `OscPage._layoutMenuModel` has them; Clear… in Add Inputs (`test_osc_layout.py::test_order_by_address`, `::test_change_address_checks_and_undoes`).
- **G-OSC35** (batch 1, fixed 2026-10-10) S136: Footer Clear / Sort / Add / Import; no shared Find bar or type filter. Now no footer, the shared Find bar (All types / Buttons / Axes), OSC Setup… and Monitor in the page bar; the main window's "Move inputs with no actions to the end" tick hidden on the OSC page (`Main.qml`) (`test_osc_layout.py::test_filters_type_and_search`).
- **G-OSC36** (batch 1, fixed 2026-10-10) S137: The Monitor was a separate window. Now the docked, folded-by-default `OscMonitorPanel` with a drag grip on `OscPage.qml`. The height is remembered in program settings (`WindowPlacement.toolRowState("oscPage")`, saved when the grip is let go). Test: `test_osc_monitor_height.py`.
- **G-OSC37** (batch 1, fixed 2026-10-10) S138: `WindowOscMonitor.qml` (66) is now only the Pop out window wrapping the panel (`OscPage.popOutMonitor`); Tools › OSC Monitor → `Main.openOscMonitor` → `OscPage.showMonitor`.
- **G-OSC38** (batch 1, fixed 2026-10-10) S139: The port was held while the Monitor window was open. Now only while the panel is unfolded on the page or popped out (`test_osc_page_e2e.py::test_docked_monitor_holds_the_port_only_while_unfolded_on_the_page`, `test_osc_monitor_panel.py`).
- **G-OSC39** (batch 1, fixed 2026-10-10) S140: Add as Input… showed while running. Now hidden while `backend.gremlinActive` (`OscMonitorPanel.qml`, `test_osc_monitor_panel.py`).
- **G-OSC40** (batch 1, fixed 2026-10-10) S141: No live value or last seen on a row. Backend (OSC-RT: `osc.live`/`liveChanged`, `test_osc_rt_ox.py`); row display `OscPage` `_liveValue` from `osc_layout.live_fields` / `lastSeenText` (`test_osc_layout.py::test_live_value_and_send_test_update_only_that_row`).
- **G-OSC41** (batch 1, fixed 2026-10-10) S142: A port-in-use error didn't name the holder. Now `port_holder`, `bind_error_detail` in the bind error's detail (`osc.py` 654; `test_osc_rt_ox.py`).
- **G-OSC42** (batch 1, fixed) S143: OSC errors not all logged (WinError 10048 on bind was not). Fixed 2026-10-10 (OSC-RT: bind, send and malformed-packet errors logged; `test_osc_rt_ox.py`); the gap "bind error shown on screen but never logged" is closed.
- **G-OSC43** (batch 1, fixed 2026-10-10) S144: No Companion setup check. Now `gremlin/osc_companion_check.py` behind the Output tab's **Check Companion setup** (`test_osc_companion_check.py`, 11).
- **G-OSC44** (batch 1, fixed 2026-10-10) S145: No Send Test Press / Value. Backend `osc.send_test` (`test_osc_rt_ox.py`); menu items on the OSC page → `OscLayoutModel.sendTest` (`test_osc_layout.py::test_live_value_and_send_test_update_only_that_row`).
- **G-OSC45** (batch 1, fixed 2026-10-10) S146: Edit Settings worked on one input only. Now `OscAddDialog.openForKeys` with `editSettingsFor` / `applySettings`, one Undo step (`test_osc_layout.py::test_edit_settings_for_shows_shared_values_and_blanks_differences`, `::test_apply_settings_changes_only_the_given_fields_in_one_step`).
- **G-OSC46** (batch 2, open) S147: No address patterns.
- **G-OSC47** (batch 2, open) S148: Pattern matching rules not built.
- **G-OSC48** (batch 2, open) S149: Outgoing addresses don't refuse patterns.
- **G-OSC49** (batch 2, open) S150: No `Event.osc_address`.
- **G-OSC50** (batch 2, open) S151: Bulk capture doesn't skip addresses a pattern input answers.
- **G-OSC51** (batch 2, open) S152: TextInputDialog has no error line.
- **G-OSC52** (batch 2, open) S153: Feedback rows live only in Module Setup.
- **G-OSC53** (batch 2, open) S154: Feedback rows are edited in the Feedback tab.
- **G-OSC54** (batch 2, open) S155: Feedback rows locked while running.
- **G-OSC55** (batch 2, open) S156: Feedback rows not under inputs, not in page Undo.
- **G-OSC56** (batch 2, open) S157: No action-state feedback sources.
- **G-OSC57** (batch 2, open) S158: No any-on rule or "not in the current profile" note.
- **G-OSC58** (batch 3, open) S159: An OSC condition reads "not present"; macros can't record OSC (to-do 62).
- **G-OSC59** (batch 3, open) S160: No sender allow-list (to-do 63).
- **G-OSC60** (batch 3, open) S161: No Invert or deadzone on OSC axis inputs (to-do 64).
- **G-OSC61** (batch 3, open) S162: No TouchOSC import (to-do 66).
- **G-OSC62** (batch 3, open) S163: Scripts can't use OSC (to-do 67).
- **G-OSC63** (batch 3, open) S164: No encoder acceleration (to-do 69).

**Sound, speech, tray, look** (status 9 Oct, from claude/gap-list.md)
- **G1** Text to Speech engine may be called off the main thread when a timer-run action speaks. (R10) Done (GL-042, batch 2).
- **G2** `_play_list` shared between threads without a lock. (R9) Done (GL-278, batch 3).
- **G3** Options voice list shows the first voice when the saved voice is missing. (Q12) Done (GL-198, batch 2).
- **G4** No message when WinRT speech is unavailable. (Q13) Done (GL-199, batch 2).
- **G5** Windows-scaling check box wording differs from its title and help. (Q15) Done (GL-233, batch 3).
- **G6** Action images ignore UI scale and the light theme's grey. (R14, Q16) Needs a hands-on check (GL-200).
- **G7** 200 % on a small screen still cuts off contents in eight windows. Open, on hold (GL-201). [tracker: AU-56]
- **G8** The test plan's tray rows (W-04..W-09, TB-02) use the old words and the old two settings. (Q17) Done (GL-220, batch 3).
- **G9** The User Guide has no OSC topic. 2026-10-09: Fixed 2026-10-09 (5c1dc480): a whole OSC chapter (D-01-HELP-OSC, S128). the "Set up OSC" topic covers the OSC page, Monitor, output and targets, Feedback, sync, encoder, discovery and this PC's addresses; the actions chapter has Send OSC.

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
| OSC | 26 files (`gremlin/osc*.py`, `gremlin/ui/osc*.py`, `qml/Osc*.qml`, `qml/WindowOscMonitor.qml`) and `action_plugins/send_osc/` (second batch 2026-10-09 added 8 files and the plugin; batch 1 of 2026-10-10 added `osc_layout.py`, `osc_companion_check.py`, `OscPage.qml`, `OscMonitorPanel.qml` and removed `OscDevice.qml`; 10057 lines in `gremlin/osc*.py`, `gremlin/ui/osc*.py` and `qml/Osc*.qml`, 556 in the plugin, recounted 2026-10-10) (+ `tools_osc/`) | the 2026-10-09 batch's `test_osc_rows.py` (10), `test_osc_file.py` (16), `test_osc_run.py` (18), `test_osc_profile.py`, `test_osc_refs.py`, `test_osc_uimodel.py` (10), `test_osc_qml.py`, `test_osc_options.py` (4), `test_osc_backend.py` (9) (more to come: end to end, carry, older tests); `test_input_module_gate.py::test_osc_passthrough` (gate only); `test_audit3_run_stop.py`, `test_action_fixes.py`, `test_audit2_coverage.py` replace `OscRuntime` with a stand-in; `test_program_imports.py` (import order); `test_startup_settings_kept.py` (OSC tab setting); `test_main_shared_pieces.py::test_osc_clear_is_red_and_asks` | Second batch 2026-10-09 (D-09-OSC-MONITOR … -ADDRESSES): one test file per area (`test_osc_<area>.py`; so far `test_osc_encoder.py` (24), `test_osc_discovery.py` (10), `test_osc_addresses_shown.py` (6), `test_osc_feedback.py` (13), `test_osc_monitor.py` (4), `test_osc_targets.py` (7), `test_osc_encoder_ui.py` (5), `test_osc_output.py` (10) + `send_osc_editor_smoke.py`, `test_osc_feedback_ui.py` (3)), `test_osc_features_carry.py` (settings travel), `tools/osc_functional_check.py` (loopback); 30 `test_osc_*.py` files in all (recounted 2026-10-10), adding `test_osc_carry.py`, `test_osc_companion_feedback.py`, `test_osc_e2e.py`, `test_osc_page_companion.py`, `test_osc_tabs.py`, and in batch 1 `test_osc_layout.py`, `test_osc_layout_save.py`, `test_osc_page_e2e.py`, `test_osc_monitor_panel.py`, `test_osc_rt_ox.py`, `test_osc_companion_check.py` |
| OSC rewrite (2026-10-10) | shared base `control_layout.py` 1292, `ActionPane.qml` 201, `ControlTree.qml` 575, `ControlFindBar.qml` 162 (2230 lines); OSC `osc_layout.py` 701, `osc_companion_check.py` 149, `OscPage.qml` 790, `OscMonitorPanel.qml` 405 | batch 1 (S129-S146, built): `test_control_layout_base.py` (5; the shared base with a stand-in device), `test_osc_layout.py` (16; rows, settings line, first action, your names, filters, groups/order/names in OSC's file, By Address, Undo, delete, clear, Change Address, Edit Settings on several, live value and Send Test, Copy for Companion), `test_osc_layout_save.py` (3; layout waits for Save, one write, Discard), `test_osc_page_e2e.py` (5; the real page off-screen: new input row, Map to vJoy in the shared pane with Undo/Redo, groups kept across a reload, a loopback packet fires while running, the docked Monitor holds the port only while unfolded), `test_osc_monitor_panel.py` (1; S137-S140), `test_osc_rt_ox.py` (10; S141-S143, S145 backend), `test_osc_companion_check.py` (11; S144), `test_first_action_empty_input.py` (2; S130), `test_osc_monitor_height.py` (1; S137) | batch 2 and 3 (S147-S164) not built |
| Sound | `audio_player.py` 222 | `test_program_fixes.py` (3 sound tests), `test_bounded_waits.py::test_a_sound_is_not_waited_for_once_the_player_stops`, `test_threads.py::test_the_audio_player_stopped_right_after_starting_ends`, `test_play_sound_missing_file.py` (5) | Interrupt and Overlap modes, mode change while running, Stop during Sequential with a long queue |
| Speech | `tts.py` 242 | `test_action_tts.py` (8: the action's data and feedback only), `test_tts_release.py` (2: released at exit) | `TTSManager` queue modes, Stop, voice missing, WinRT missing, off-main-thread call |
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
| S1, S9, S16, S20, S23, S90-S115 | 2026-10-09 (D-09-OSC-MONITOR, D-09-OSC-OUTPUT, D-09-OSC-FEEDBACK, D-09-OSC-ENCODER, D-09-OSC-DISCOVERY, D-09-OSC-ADDRESSES; user: "go with your recommendations, approved, go ahead"): OSC Monitor, targets and Send OSC, Feedback with sync address, encoder, zeroconf discovery (off by default), addresses on labels |
| S91, S97, S116-S128 | 2026-10-09 (D-09-OSC-TABS, D-09-OSC-COMPANION, D-09-OSC-LOOK, D-01-HELP-OSC; user: "B with tabs"; "a general nature for compatibility with all OSC capable devices; a specific Add Companion to make this easier; build 1-6"; "I want the theme to look visually better and to follow the theme of the button mapper; go with your recommendations, approved, go ahead"): setup tabs, OSC Setup… button, Companion helpers on top of general OSC, Button Map look, Help chapter |

| S1, S7, S10-S12, S18, S20, S26-S28, S30, S90, S92, S93, S117, S118, S122, S129-S146 | 2026-10-10 (D-09-OSC-PAGE, D-09-OSC-DOCK, D-09-OSC-TOOLS; user: "go with your recommendations, approved"; design rule: the OSC page "as close as possible to the logical device theme"): the OSC page on the Logical Device page's shared base (rows, groups, order, Find, right-click menu, shared action pane, page Undo), no Hide system name, no Appearance panel now, settings line, no footer; OSC Monitor docked at the bottom (folded, Pop out, port released when folded or left), Add as Input… hidden while running; live value and last seen, port holder named, OSC errors logged, Companion setup check, Send Test Press / Value, Edit Settings on several inputs. Not in this rewrite: the Button Map and Keyboard panes on the shared pane (OP9) |
| S11, S102, S103, S120, S147-S158 | 2026-10-10 (D-09-OSC-PATTERNS, D-09-OSC-FBROWS, D-09-OSC-ACTSTATE; same approval; batch 2): address patterns (one input, per-address state; exact wins; outgoing refuse patterns; `Event.osc_address`; Bulk skips; error line), feedback rows on the OSC page (placed by source or Show under this input, else "Feedback not tied to an input"; edited only on the page; editable while running; actions then feedback; page Undo), feedback from action states (registry + existing poll; Smart Toggle, Tempo, Running/Paused; on if any; "not in the current profile") |
| S159-S164 | 2026-10-10 (D-09-OSC-EXTRAS; same approval; batch 3): conditions and macros read OSC, sender allow-list (CIDR), Invert + deadzone on axis inputs, TouchOSC import, scripts (inputs, named targets), encoder acceleration presets |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.
