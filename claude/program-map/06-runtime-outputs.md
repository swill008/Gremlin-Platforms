# Run time and outputs

Mapped read-only against the code at 4f6bdfa4 (6 Oct). S88-S91 (D-06-MOUSE, D-06-START-SKIP) and S72, S86 changed added 10 Oct, with sections 2-5, 10 and 11 from the program agents' notes. Line numbers drift; re-check them before a step starts. Lifecycle parts follow `claude/system-maps.md` map 3 (rows A-R there); this page adds the outputs, the Logical Device, sound and speech, the Run/Stop UI and the gaps around them.

## 1. Purpose

Run turns the open profile into live behaviour: claimed inputs fire their actions, and the actions send to vJoy, the virtual Xbox pad, the Logical Device, the keyboard, the mouse, sound and speech. Stop must end everything a Run started and let go of every output it held. The Logical Device page is where the user builds the program's own virtual device and its actions.

## 2. Files

**Run lifecycle**
- `gremlin/run_scope.py` (438): what one Run holds and the Stop that lets go of it (map 3, GL-046, batch 1 d68f4d88). The one Run number (`number`, `alive`), `begin` / `stop`, Run timers (`timer`, cancelled at Stop or fired with at_stop="fire"), loops (`loop`), held keys and mouse buttons (`hold`, `let_go`, `release_owner`, `owning`), `on_stop` steps in Stop stages (CUT_INPUT, CANCEL, FIRE_PENDING, END_WORK, RELEASE_HELD, NEUTRAL, ...). Only `CodeRunner` calls `begin` / `stop`; `test_run_scope_only.py` guards that.
- `gremlin/code_runner.py` (716 lines; from 2026-10-10 `_refresh_on_mode_change` fires `ModeChangeActions` and `_on_active_changed` stops mouse motion on Pause, S88, S90): `CodeRunner.start/stop`, the Run number (`run_number`), `CallbackObject` (one per action sequence), `VirtualAxisButton` / `VirtualHatButton` / `VirtualButtonFunctor` (an axis range or hat directions used as a button), `_refresh_axes` (vJoy Initial Values, refresh on Run and on mode change).
- `gremlin/event_helpers.py` (294; from 2026-10-10 `ModeChangeActions`, the mode-change callbacks during a Run, S88): `ButtonReleaseActions` singleton (release callbacks run after the other callbacks of an event; auto-release of vJoy and Logical Device buttons when the mode changed in between).
- `gremlin/event_handler.py` (944), part (from 2026-10-10 `is_same_binding`, used by Map to Mouse at a mode change; restarts a Run and lets go of / reconnects a relaid device on a layout change, 02 S143): `EventHandler` (callback table per device, mode and event; `process_event`; `pause/resume/toggle_active`; `build_event_lookup` copies parent-mode callbacks into child modes).
- `gremlin/user_script.py` (1776), part: `callback_registry`, `PeriodicRegistry` (script timers, its own thread), `VJoyPlugin` (scripts' `vjoy` object).
- `gremlin/base_classes.py` (682), part: `_pending_pulses` / `flush_pulses` / `_pulse_event` (short pulses, released at Stop).
- `gremlin/shared_state.py`: `runtime_active` flag (set at Run and Stop).
- `gremlin/mode_manager.py` (368), part: `switch_to` at Run, `flush_last_modes` at Stop (Last Active startup mode).
- `gremlin/threads.py` (160), `gremlin/clock.py` (24): the thread and time helpers every loop must use.
- `joystick_gremlin.py`, `shutdown_cleanup` 240-285: Stop when the program quits.

**Outputs**
- `gremlin/modules/output.py` (896; from 2026-10-10 `first_claimed_output`, `vjoy_driver_ids`, `driver_claim`, page 05 S113, S115, S118): the output layer. vJoy firewall (`write_vjoy`, `vjoy_value`, `vjoy_state`, claims cache with 1 s TTL, open/retry of busy devices, blocked-output log once per Run), script vJoy (`ScriptVJoy`), Xbox pass-through (`write_xbox`, `xbox_state`), driver checks and wording, `reset_drivers`. From 2026-10-10 `reset_vjoy` calls `trace.rested(held ids)` after releasing outputs at rest, so the out-of-step check counts the rest value as written (S87, S17; 01 S150).
- `gremlin/trace_watch.py` (new 2026-10-09, D-01-TRACE): the out-of-step watch (S87, 01 S150): every 1 s while tracing, polls each ticked axis of devices ticked for the Out-of-step check and compares with the last RAW value; reads each written vJoy axis back (the DILL device Windows sees for that vJoy, else `output.vjoy_value`) and compares with the last written value; the 4 s "no input" info line; started and stopped by `trace.on_change`. `gremlin/modules/output.py` also calls `trace.output` at every `write_vjoy` result (S86).
- `vjoy/vjoy.py` (982), `vjoy/vjoy_interface.py` (115): vJoy driver wrapper; `VJoyProxy` (opened devices, class-level dict); the keep-alive is in `gremlin/modules/output.py` since batch 3 (GL-267).
- `vigem/xbox.py` (375): `XboxProxy` (pads 1-4, plugged in on first write, lock), `XboxPad.apply`, `snapshot`, `reset`. `vigem/own_pads.py` (125): remembers which Xbox devices are Gremlin's own pads. `vigem/ids.py`, `vigem/vigem_client.py`, `vigem/vigem_commons.py`: ids, DLL loading, driver checks.
- `gremlin/macro.py` (1333): `MacroManager` (scheduler thread, one thread per running macro, exclusive/pre-emptive, Run counter `_run`, `_held_keys`), macro steps (Joystick, Key, Logical Device, Mouse Button, Mouse Motion, Pause, vJoy), repeat modes.
- `gremlin/sendinput.py` (492 after the 2026-10-10 rework): Windows `SendInput` for the mouse; `MouseMotionManager` (owns every Map to Mouse motion piece and the "mouse motion" thread); `_held_buttons` and `release_held_buttons`. From 2026-10-10 (D-06-MOUSE) motion from several inputs adds up, each button/hat ramps on its own, speeds are delivered as set at a fixed 100 Hz; motion stops on a mode change that doesn't route to the same binding, at the first Stop stage and on Pause; a Trace OUTPUT line per change (S72, S86, S88-S90).
- `gremlin/keyboard.py` (441), part: `send_key_down/up` 217-237 (keys sent, not tracked).
- `gremlin/audio_player.py` (204): `AudioPlayer` (playback thread; Sequential / Interrupt / Overlap).
- `gremlin/tts.py` (122): `TTSManager` (Qt WinRT text-to-speech, queue).
- Action plugins that write outputs (mapped with the Actions page, listed here for the calls): `action_plugins/map_to_vjoy` (442, relative-axis thread), `map_to_xbox` (386), `map_to_logical_device` (429, relative-axis thread), `map_to_mouse`, `map_to_keyboard`, `macro`, `play_sound`, `text_to_speech`, `pause_resume`, `tempo` / `double_tap` / `smart_toggle` (timers), `condition` (reads vJoy, Logical Device, keyboard and joystick state).

**Xbox output page, viewer and driver check**
- `gremlin/ui/xbox_device_model.py` (200): `XboxDriverStatus` (ViGEm installed / ready / version, hint, Download and Game Controllers links) and `XboxDeviceModel` (the Xbox page's rows for one pad: each Xbox target and what sends to it).
- `gremlin/ui/xbox_maps.py` (41): `walk_actions`, `xbox_maps_for_item` (the Map to Xbox targets of a binding, nested actions too).
- `gremlin/ui/xbox_viewer.py` (413): Xbox viewer models (QML `Gremlin.Device`): `XboxViewerDeviceModel`, `XboxPadListModel`, `XboxMappedAxisModel` / `ButtonModel` / `HatModel` (which inputs send to each pad target).
- `qml/XboxDevice.qml` (121): the Xbox output page (Home Xbox tab). `qml/XboxDriverCheck.qml` (78): the ViGEm driver line and its links.
- `qml/DialogXboxViewer.qml` (107), `qml/XboxViewerCard.qml` (243): Tools Xbox viewer window and its card (uses `Xbox360Face.qml`).
- `gremlin/ui/vjoy_status.py` (187): `VJoyStatus` (QML `Gremlin.Device`): which vJoy devices are active, which vJoy and extra tabs (Keyboard, Logical, OSC, Xbox) are pinned on Home (settings `devices/display/vjoy-tabs`, `extra-tabs`), `xboxAvailable`. `EXTRA_ALLOWED` / `EXTRA_DEFAULT` are saved setting keys, allowed by the no-built-in-lists guard (03 S90b).

**Logical Device**
- `gremlin/logical_device.py` (618): `LogicalDevice` singleton: inputs (axis/button/hat, id, permanent `uid` (04 S2a), label, user name, group, hide system name), current values (`_value`), groups, order, `memento/restore` (for Undo); `LogicalRows.create(..., uid=None)`, `by_uid`, `uid_of`, `identifier_of_uid`, `to_dict` / `load_dict`, `dirty` / `mark_saved`; module-level `resolve_logical_reference` (the one reader of a saved reference: uid, else the v14 map, else type and number; unknown uid = missing). No file IO.
- `gremlin/logical_device_file.py` (new 2026-10-09, D-04-LD-FILE): the one owner of the Logical Device's module file (`store.path_of("logical_device")`, key `logical-device`, other keys kept): `load` (at start; missing file = empty layout), `save` / `save_if_dirty` (with File › Save Profile, through `store` so History records it), `merge_profile_rows` (version 14 profile rows → `MergeResult.uid_map`, `added`), `backup_v14`, `current_uid_map` (old (type, number) → uid while a version 14 profile loads). The file also carries the module-file identity keys (`kind`, `device`, `direction`, `boundName`, `boundGuidLocal`); a real version 14 merge saves whenever the file differs.
- `gremlin/ui/logical_layout.py` (1580): `LogicalLayoutModel` for the page: rows, filters, selection, groups, sort, Assign Hardware links (Map to Logical Device actions), the action pane (draft/commit), Undo/Redo (50 steps; each step carries a label, read by the Undo bar through `lastChange`, `undone`, `undoTip`, `redoTip`, signal `revisionChanged`), `parentCount` (rows shown, the Find count). D-04-LD-FILE: `drop_steps` / `drop_logical_steps` (S83), connected to `signal.logicalDeviceReloaded`.
- `qml/LogicalPage.qml` (2134): the page; `editorLocked` while running, menus, drag, filters, pane. Find and the Assign Hardware search are the shared `SearchBox` (`logicalFind`; "N found", ×); Undo / Redo is the shared `UndoBar` (`logicalUndoBar`); an empty list shows `EmptyState` with Clear Filters; Delete row(s), Delete Group, Clear Name and Delete action ask the shared question (`Confirm.ask`, S140).
- `qml/LogicalDeviceSelector.qml` + `gremlin/ui/device.py` `LogicalDeviceSelectorModel` (674): Logical Device pickers in action editors. `device.py` `LogicalDeviceManagementModel` (486): older model with `createInput/changeName/deleteInput` (no QML user found).

**Run/Stop UI**
- `gremlin/ui/backend.py` (704), part: `activate_gremlin` 420, `toggleActiveState` 417, `gremlinActive` 413, `gremlinPaused` 409, device-change behaviour `_device_change` 305, auto-load `_active_process_changed_cb` 357, Stop before profile load 670.
- `gremlin/ui/system_tray.py` (332): tray icon (running / idle), menu "Run Profile" / "Stop Profile" 309, Exit.
- `qml/Main.qml`: toolbar Run/Stop button 1053-1059, status bar Running / Stopped / (Paused) / (unsaved changes) 1220-1230, `deactivateThenQuit` 647. `qml/RunningNote.qml`: note shown while running. `editorLocked` in `BindingCatalog.qml`, `InputConfiguration.qml`, `KeyboardInputList.qml`, `OscDevice.qml`, `LogicalPage.qml`.

**Tests** (main ones)
- `test/unit/test_audit3_run_stop.py` (9 tests: held keys, buttons, motion, Logical loop, stuck macro step), `test_audit2_macros.py` (4), `test_audit_runtime.py` (9), `test_action_fixes.py` (Run/Stop items), `test_audit2_coverage.py` (Run flag, release after a failing action, Load Profile restart).
- `test_output_layer.py` (7), `test_vjoy_writers_use_firewall.py` (3), `test_device_fixes.py` (vJoy busy), `test_xbox_output_module.py` (9), `test_map_to_xbox.py`, `test_map_to_xbox_inputs.py`, `test_xbox_incoming_names.py` (3), `test_xbox_pads_told_apart.py` (4), `test_xbox_viewer_driver_check.py` (8), `test_one_copy_of_each_rule.py`.
- `test_run_scope_only.py` (6): only CodeRunner begins and stops a Run; nothing keeps its own Run counter.
- Tracing (S86-S87, D-01-TRACE): `test_trace_*.py` (OUTPUT written / blocked / missing lines, only for ticked controls, the out-of-step watch on a stuck vJoy and a silent stick); from 2026-10-10 `test_trace_rest_on_stop.py` (146 lines: the rest values at Stop count as written, no false OUT OF STEP).
- `test_ld_model.py` (10), `test_ld_file.py` (15+), `test_ld_refs_a.py` (7), `test_ld_refs_b.py` (8+), `test_ld_refs_c.py`, `test_ld_pack.py` (5), `test_ld_profile.py` (7), `test_ld_lib.py` (7), `test_ld_ui.py` (D-04-LD-FILE), `test_logical_device.py` (8), `test_logical_layout.py`, `test_undo_bar_labels.py` (Logical step labels, `parentCount`), `test_config_pages_shared_pieces.py::test_logical_page_search_delete_and_undo_bar`, `test_logical_events_pass_gate.py` (2), `test_audit_editing.py` (Logical Undo), `test_audit3_actions_undo.py` (Logical Undo), `test_audit2_modes.py` (Logical pane mode).
- `test_threads.py`, `test_bounded_waits.py`, `test_program_fixes.py` (sound), `test_play_sound_missing_file.py`, `test_mode_refresh_and_add_key.py`, `test_device_scan.py`, `test_device_reconnect.py`, `test_user_script.py`.
- `test/action_interaction/test_macro.py` (9), `test_pause_resume.py`, `test_tempo.py`, `test_condition.py`.

## 3. What it owns

| Data / state | Where | Who changes it |
|---|---|---|
| Run number | `code_runner._run_number` (283) | `CodeRunner.start/stop`; read by `map_to_logical_device` loop |
| Second Run number | `MacroManager._run` (macro.py:96) | `MacroManager.start/stop` |
| Third Run number | `PeriodicRegistry._generation` (user_script.py:126) | `PeriodicRegistry.start` |
| Running flag | `CodeRunner._running`; `shared_state._runtime_active`; `EventListener.gremlin_active` | `CodeRunner.start/stop` only |
| Paused flag | `EventHandler.process_callbacks` | Pause and Resume action, `EventHandler.pause` on a `VJoyError`, `resume` at Run |
| Last written value per vJoy output (for the out-of-step check), episode state of each OUT OF STEP warning | `gremlin/trace.py` (`last_written`), `trace_watch.py` | `output.write_vjoy` via `trace.output`; from 2026-10-10 also `output.reset_vjoy` via `trace.rested` (rest values at Stop or restart); the watch (only while Tracing is on) |
| Callback table | `EventHandler.callbacks`, `known_modes` | built at Run (`_setup_profile`, script callbacks), cleared at Stop; `rename_mode`/`drop_mode` from mode editing |
| Release callbacks | `ButtonReleaseActions._registry` | registered by Map to vJoy, Map to Logical Device, Change Mode, Macro, Tempo, Double Tap, Smart Toggle; cleared at Run only |
| Pending pulse releases | `base_classes._pending_pulses` | `_pulse_event`; flushed at Stop |
| Held keys (macros) | `macro._held_keys` | `KeyAction`; released by `MacroManager.stop` |
| Held mouse buttons | `sendinput._held_buttons` | `mouse_press/release`; released by `MacroManager.stop` |
| Mouse motion (every input's motion, ramps, the 100 Hz "mouse motion" thread) | `sendinput.MouseMotionManager` | Map to Mouse; stopped on a mode change not routed to the same binding, at Stop's first stage and on Pause (S72, S88-S90) |
| Mode-change callbacks during a Run | `event_helpers.ModeChangeActions` | registered by actions at Run; fired by `CodeRunner._refresh_on_mode_change` |
| Macro queue and running set | `MacroManager._queued_macros`, `_scheduled_macro`, `_executing_macro` | Macro action, `RefreshPhysicalInputs`; cleared at Run and Stop |
| vJoy claims cache | `output._vjoy_claims`, `_vjoy_names`, `_vjoy_modules`, `_xbox_modules`, `_claims_at` | re-read from module files every 1 s, forced at Run (`refresh`) and by `vjoy_modules()` |
| vJoy open/busy state | `output._vjoy_failed_at`, `_told_busy`, `_blocked` | write path; cleared at Run (`clear_blocked_log`) and in `reset_drivers` |
| Opened vJoy devices | `VJoyProxy.vjoy_devices` (class dict, no lock) | opened by the first write or read (`_open_vjoy`), emptied by `reset_vjoy`; also by `device_initialization` when the vJoy device list changes |
| Plugged Xbox pads | `XboxProxy._pads`, `_busp` (locked) | plugged on first `write_xbox`, unplugged by `reset_drivers` |
| Gremlin's own pad list | `vigem/own_pads.py` (file in the data folder) | `note_device` |
| Logical Device inputs, groups, order, names, permanent ids | `LogicalDevice` singleton, saved in its own module file by `logical_device_file` (D-04-LD-FILE; was saved in the profile) | `logical_device_file.load` at start (kept across profile loads), version 14 merge (`merge_profile_rows`), Logical page (`logical_layout`), Device Library Restore / Import (page 10), Device Pack (`device_pack.py:1476`, `1622`), `macro.LogicalDeviceAction.create` (770, creates Button 1 when empty), old `LogicalDeviceManagementModel` |
| Logical Device values | `LogicalDevice.Input._value` | Map to Logical Device (main thread and its loop thread), macro Logical Device step (macro thread), release callback; reset only when the whole device is reset at profile load |
| Logical page Undo | `LogicalLayoutModel._undo/_redo` (in memory, 50) | page actions; kept across profile loads except steps that changed the old profile's actions or links; all dropped on mode delete, Discard and `signal.logicalDeviceReloaded` (`drop_steps` / `drop_logical_steps`; S83, D-04-LD-FILE) |
| Sound queue | `AudioPlayer._play_list`, `_currently_playing` | Play Sound; cleared at Stop |
| Speech queue and engine | `TTSManager._queue`, `_engine` | Text to Speech; queue cleared at Stop, engine kept |
| Script timers | `PeriodicRegistry._registry`, thread | scripts at Run; cleared at Stop |
| Settings read | `global/general/refresh-axis-on-activation`, `refresh-axis-on-mode-change`, `device-change-behavior`; `action/macro/default-delay`; `action/play-sound/playback-mode`; `action/text-to-speech/voice`; `profile/automation/enable-auto-loading`, `remain-active-on-focus-loss`; `ui/general/input-highlighting` | Options (other subsystem) |
| Profile settings read | `vjoy_initial_values`, `vjoy_as_input`, macro delay (`effective_macro_delay`), startup mode | Profile Settings (other subsystem) |

## 4. Entry points

| Trigger | Handler | Function(s) |
|---|---|---|
| Toolbar Run / Stop button | `Main.qml:1059` | `backend.toggleActiveState` -> `activate_gremlin(not running)` -> `CodeRunner.start(profile, ui_state.currentMode)` or `stop()` |
| Tray menu "Run Profile" / "Stop Profile" | `system_tray._handle_context_menu_cb` 271 | `backend.toggleActiveState` |
| Mode change while running (2026-10-10) | `CodeRunner._refresh_on_mode_change` | `ModeChangeActions.fire` (Map to Mouse stops motion the new mode doesn't route to the same binding, S88) |
| Pause / Resume (2026-10-10) | `CodeRunner._on_active_changed` | Pause stops mouse motion (S90) |
| Map to Mouse change while tracing (2026-10-10) | `sendinput` | `trace.mouse`: one OUTPUT line per change (S86) |
| Quit (File > Exit, tray Exit, window close) while running | `Main.qml:deactivateThenQuit` 647 | `toggleActiveState`, then `Qt.quit`; then `joystick_gremlin.shutdown_cleanup` (Stop again, `reset_drivers` again, audio, TTS, OSC again) |
| Open / load a profile, New Profile | `backend._load_profile` 670, `newProfile` 503 | `activate_gremlin(False)` first |
| Load Profile action while running | `action_plugins/load_profile` -> backend load | Stop, load, Run again (`test_audit2_coverage::test_load_profile_loads_and_restarts_the_run`) |
| Tracing turned on (01 S147) | `trace.on_change` | `trace_watch` start (1 s loop); `write_vjoy` results write OUTPUT / BLOCKED lines for outputs a ticked control caused (S86); `code_runner` writes EVENT lines "Profile started" / "restarted" / "stopped" / "start failed" and "Mode changed" (`_refresh_on_mode_change`, only while a profile runs) |
| Stop or restart while tracing (2026-10-10) | `output.reset_vjoy` | releases held outputs at rest, then `trace.rested(held ids)` sets their last written value to rest (S87, S17; 01 S150) |
| Device plugged / unplugged | `EventListener.device_change_event` -> `backend._device_change` 305 | Disable: Stop; Ignore: nothing; Reload: Stop + Run. Also `InputModuleRuntime.reload`; `device_initialization` resets vJoy when the vJoy list changed |
| Auto-load (foreground program changes) | `process_monitor.process_changed` -> `_active_process_changed_cb` 357 | Stop, load, Run; Stop on focus loss unless "Keep running"; refuses over unsaved changes |
| Run start | `CodeRunner.start` 312 | `_next_run_number`, `_reset_state` (clears release callbacks), macro delay, `output.refresh`, `clear_blocked_log`, `log_once.reset`, `_setup_user_scripts`, mode placeholders, script callbacks, `_setup_profile` (a `CallbackObject` per action sequence), `build_event_lookup`, `InputModuleRuntime.reload`, connect `event`, `key_event`, `virtual_event` -> `process_event`, periodic registry, `MacroManager.start`, `AudioPlayer.start`, `TTSManager.start`, mode listening, `ModeManager.switch_to(start mode)`, `resume`, `_running=True`, `runtime_active=True`, `MouseController.start`, `OscRuntime.start`, `_refresh_axes` |
| Run stop | `CodeRunner.stop` 400 | new Run number, mode listening off, disconnect signals, `flush_last_modes`, flags off, clear callbacks, periodic stop/clear, OSC stop, `flush_pulses`, `MacroManager.stop` (ends macros, releases held keys and mouse buttons), `MouseController.stop`, `AudioPlayer.stop`, `TTSManager.stop`, `output.reset_drivers` |
| A claimed hardware event | `EventListener.joystick_event/keyboard_event` -> `InputModuleRuntime._on_hid/_on_key` (gate) -> `event/key_event` | `EventHandler.process_event` -> callbacks of the event's mode -> `ButtonReleaseActions.process_release` |
| Logical Device event | Map to Logical Device / macro step emits `joystick_event` with the Logical Device guid | passes the gate (`always_forwarded` -> `device_class.can('no_claim_needed')`, 03 S90b) -> `process_event` -> the Logical control's own actions |
| Virtual button event | `VirtualButtonFunctor` emits `EventListener.virtual_event` | `process_event` (connected only while running) |
| Pause / Resume / Toggle action | `action_plugins/pause_resume` | `EventHandler.pause/resume/toggle_active` -> `is_active` -> `backend.activityChanged` |
| vJoy error inside a callback | `process_event` 692, 706 | error box, `EventHandler.pause()` |
| Mode change while running | `ModeManager.mode_changed` | `CodeRunner._refresh_on_mode_change` (refresh axes if set), `ButtonReleaseActions._mode_changed_cb` |
| Map to vJoy / Map to Xbox / Map to Logical Device / Map to Keyboard / Map to Mouse / Macro / Play Sound / Text to Speech fire | their functors | `output.write_vjoy`, `output.write_xbox`, `LogicalDevice[...].update` + emit, `keyboard.send_key_down/up` (via macros), `sendinput.*`, `MacroManager.queue_macro`, `AudioPlayer.enqueue`, `TTSManager.enqueue` |
| Script writes `vjoy[n]...` | `output.ScriptVJoy` | `write_vjoy` / `vjoy_value` |
| Script `@periodic` | `PeriodicRegistry._thread_loop` | callbacks on the script-timer thread |
| Tempo / Double Tap / Smart Toggle time out | `run_scope.timer` (Qt main thread) | child actions (cancelled at Stop, GL-047) |
| Relative axis (Map to vJoy, Map to Logical Device) | `threads.start` loop | writes every step; ends by vJoy release (vJoy) or Run number (Logical) |
| Short pulse | `base_classes._pulse_event` 612 | release after 50 ms (`QTimer.singleShot` on main thread, `time.sleep` elsewhere); `flush_pulses` at Stop |
| Viewers / Home cards read outputs | `live_input`, `pair_live`, `xbox_viewer`, `module_model` | `output.vjoy_state`, `vjoy_held`, `xbox_state` (never open a device) |
| Program start | `joystick_gremlin.py` / `Backend` | `logical_device_file.load` (fills `LogicalDevice()` from its module file) |
| A saved Logical Device reference is read (actions, conditions, macros, scripts, rule checks) | their `from_xml` / loaders | `logical_device.resolve_logical_reference` (04 S2a) |
| File › Save Profile | `Backend.saveProfile` | `logical_device_file.save_if_dirty` (writes the module file when `LogicalDevice().dirty`; History records it) |
| Logical page: Add Buttons/Axes/Hats (count up to 180) | `LogicalPage.qml` menu -> `addMany` 836 | `_apply` -> `LogicalDevice.create_many` |
| Logical page: Rename, Hide system name | `setRowLabel` 882 / `setUserName` 873 | `set_user_label` |
| Logical page: Clear Name | `Confirm.ask` (red, "Clear the name of X?") -> `setUserName` | `set_user_label` |
| Logical page: Delete row(s) | `Confirm.ask` (red Delete Row / Delete N Rows) -> `deleteParents` | delete inputs and their links/actions |
| Logical page: Delete Group | `Confirm.ask` (rows stay, in Ungrouped) -> `removeGroup` | `delete_group` |
| Logical page: New/Rename/Delete Group, Group as, Move to, Move Group Up/Down | `addGroup`, `renameGroup`, `removeGroup`, `moveSelected`, `moveGroupUp/Down` | `ensure_group`, `rename_group`, `delete_group`, `place`, `move_group_before` |
| Logical page: drag a row or group header | `moveRow` 931, `moveParent` 982 | `place`, `move_group_before` |
| Logical page: Order menu | `sortBySystem`, `sortByName`, `sortGroupNames` | `sort_within`, `sort_groups` |
| Logical page: Find (`SearchBox` `logicalFind`) / filters; empty list Clear Filters (`EmptyState`) | `setFilter` | rebuild rows; `parentCount` gives "N found" |
| Logical page: Assign Hardware search (`SearchBox`) | `hardware` (list filter) | rows of claimed controls |
| Logical page: Assign Hardware ticks | `hardware` 1159 (list), `setLinks` 1215 | add/remove Map to Logical Device on the source input in the page's mode |
| Logical page: writer line Absolute/Relative, scale, Invert | `setAxisMode` 1106, `setAxisScale` 1117, `setInverted` 1125 | edits the source's Map to Logical Device action |
| Logical page: Add Action, open, OK, Cancel, Delete action | `beginNewAction`, `beginPane`, `commitPane`, `discardPane`, `endPane`; Delete action always asks (`Confirm.ask`) -> `deleteAction` | binding_catalog draft helpers (`_clone_binding`, `_attach_binding`, `_drop_shadow`) |
| Logical page: Undo / Redo (`UndoBar` `logicalUndoBar`, menu, Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z) | `undo`, `redo` | `_replay` (memento + input snapshots); labelled steps |
| Logical page: mode picker | `setMode` 806 | rows for that mode |
| Profile loaded / mode renamed / mode deleted | `signal.profileChanged`, `modeRenamed`, `modeDeleted` | Undo cleared; steps renamed; pane closed with a notice |
| Logical Device changed elsewhere | `signal.logicalDeviceModified` | `_on_external` rebuild; also Configuration models, `module_model` targets |
| Options saved | `backend.emitConfigChanged` | `AudioPlayer.refresh` (playback mode) |
| vJoy keep-alive | `output._arm_keep_alive` (`run_scope.timer` on the main thread, 60 s) | resets an idle held vJoy device |
| Run start / Stop (owner) | `CodeRunner.start` -> `run_scope.begin`; `CodeRunner.stop` -> `run_scope.stop` | new Run number; Stop stages in order (section 6) |
| Tools › Viewers › Xbox Viewer (`tools.xboxViewer`, toolbar button) | `openTool("DialogXboxViewer.qml")` | `XboxViewerDeviceModel`, `XboxPadListModel`, `XboxMapped*Model` reload; `output.xbox_state` |
| Home Xbox tab / Xbox output page | `XboxDevice.qml`, `XboxDriverCheck.qml` | `XboxDeviceModel` (pad rows), `XboxDriverStatus` (driver line, Download, Game Controllers) |
| Home device list: which vJoy and extra tabs show | `DeviceList.qml` 28-81 (`VJoyStatus`) | `isActive`, `isPinned`, `isExtraPinned`; pins kept in settings `devices/display/vjoy-tabs`, `extra-tabs` |

## 5. Talks to

| Other subsystem | Calls out (this -> it) | Called by (it -> this) |
|---|---|---|
| Input modules / gate (`gremlin/modules/runtime.py`, `gate.py`, `inputs.py`) | `InputModuleRuntime().reload()` and its `event`/`key_event` signals at Run | sends claimed events; conditions read through `inputs.*` |
| Tracing (`gremlin/trace.py`, page 01) | `trace.output` at every `write_vjoy` result; EVENT lines at Run/Stop/restart; the watch reads `trace.last_raw/last_written`, polls the stick through the input side and reads vJoy back, writes `trace.warn("OUT OF STEP", …)` | `trace.on_change` starts/stops `trace_watch` |
| Tracing rest (`trace.rested`, page 01; 2026-10-10) | `output.reset_vjoy` tells `trace` which outputs it put back at rest, so the out-of-step watch compares vJoy with the rest value (S87) |
| Module files / registry (`modules/registry.py`, `claim.py`) | `registry.outputs()`, `resolve_vjoy_id`, `claim_allows` (claims cache) | - |
| Wiring labels (`modules/wiring.py`) | - | reads `vjoy_claim`, `vjoy_allows`, `xbox_module` for labels |
| Event listener / devices (`event_handler.EventListener`, `device_initialization`, `input_cache`, `input_refresh`) | `_refresh_axes` reads the vJoy readback from `input_cache` and queues `RefreshPhysicalInputs`; `vjoy_devices()` | `device_change_event` -> backend Stop/Run; `device_initialization` calls `output.reset_vjoy` |
| Actions (`action_plugins/*`, `base_classes`, `plugin_manager`) | `CallbackObject` builds each root action's functor at Run | actions call output, macro, sendinput, audio, TTS, Logical Device, `ButtonReleaseActions`, `EventHandler.pause/resume`, `code_runner.run_number` |
| Modes (`mode_manager`) | `switch_to` at Run, `flush_last_modes` at Stop, `resolve_start_mode` | `mode_changed` -> refresh axes, release-mode tracking |
| Profile (`profile.py`) | reads inputs, scripts, settings, modes | Save calls `logical_device_file.save_if_dirty`; a version 14 load calls `merge_profile_rows` / `backup_v14`; references resolve by uid (`identifier_of_uid`). Profile load no longer resets `LogicalDevice` (D-04-LD-FILE) |
| Module file store (`modules/store.py`, page 03) | `logical_device_file` reads and writes the Logical Device's module file through `store.path_of` / `update_path` / `write_json` | - |
| User scripts (`user_script.py`) | `_setup_user_scripts` (retry, reload), callback and periodic registries | scripts write vJoy through `ScriptVJoy`, keys through `keyboard` |
| OSC (parked) | `OscRuntime().start/stop` at Run/Stop and again at quit | OSC emits `joystick_event` (always forwarded) |
| Viewers and Home cards (`live_input`, `pair_live`, `xbox_viewer`, `xbox_device_model`, `output_modules`, `module_model`, `vjoy_status`) | - | `vjoy_state`, `vjoy_held`, `xbox_state`, `vjoy_modules`, `vjoy_in_use_elsewhere`, driver checks; `runtime_active()` |
| Configuration page / Binding catalog | Logical page reuses its private draft helpers | `editorLocked` from `gremlinActive` |
| Device Pack (`device_pack.py`) | - | creates and deletes Logical Device inputs; driver checks |
| Auto Mapper (`modules/auto_map.py`) | - | `vjoy_modules()` |
| History / saving | The Logical Device is saved in its own module file (History records it as a module file, 08 S4, S46); its links (Map to Logical Device) are saved with the profile | - |
| Live Log Reader / input monitor | `input_monitor.record` in `process_event` | reads `gremlin_active` |
| Process monitor (auto-load) | - | `process_changed` -> Stop/Run |
| Map to Mouse and Windows mouse (`action_plugins/map_to_mouse`, `sendinput.py`) | `sendinput` calls `trace.mouse`, `gremlin.threads`, `gremlin.clock` | `map_to_mouse` calls `sendinput`, `event_helpers.ModeChangeActions`, `EventHandler.is_same_binding` |
| Run scope (`run_scope.py`) | `begin` / `stop`; actions, macros, scripts, keyboard, mouse and output register timers, loops, held keys and Stop steps | - |
| Threads (`gremlin.threads`) | every loop and timer here (macro scheduler, macros, mouse, audio, script timers, relative-axis loops, keep-alive) | `threads.shutdown` at quit |

## 6. Threads and timers

| Name (threads list) | Started by | Ends by | Clock |
|---|---|---|---|
| "macro scheduler" | `MacroManager.start` | `_is_running` False + event, `join(2.0)` | event wait |
| "macro" (one per running macro) | `_dispatch_macro` | Run number change, `_stopped` event, own flag; steps under `_step_lock` (2 s acquire timeout) | `Event.wait` (Pause steps) |
| "mouse controller" | `MouseController.start` | `_is_running` False, `join(2.0)` | `time.sleep(0.01)`, `time.time()` |
| "trace watch" (new 2026-10-09, D-01-TRACE) | `threads.start` from `trace.on_change` when Tracing turns on | Tracing off or quit (`threads.shutdown`); waits on its stop event 1 s at a time | `gremlin.clock` |
| "audio player" | `AudioPlayer.start` | `_is_ready` False, `join(2.0)` | `time.sleep(0.01)` |
| "user script timers" | `PeriodicRegistry.start` (only if callbacks exist) | `_running` False or new generation, `join(2.0)` | `time.monotonic`, `time.sleep` up to 1 s |
| "vJoy relative axis" (Map to vJoy) | `map_to_vjoy._start_loop` 139 | `vjoy_owned` False, input centred | `clock` |
| "logical device relative axis" | `map_to_logical_device._start_loop` 144 | Run number change, value changed elsewhere | `clock` |
| "vJoy N keep-alive" | `output._arm_keep_alive` | cancelled at Stop (run_scope CANCEL) and in `output.reset_vjoy` | `run_scope.timer` 60 s, `clock.monotonic()` |
| Tempo / Double Tap / Smart Toggle timers | `run_scope.timer` (Qt main thread) | fire or cancel by the action; cancelled at Stop (CANCEL stage, GL-047) | Qt timer |
| Pulse release | `base_classes._pulse_event` | 50 ms, or `flush_pulses` at Stop | `QTimer.singleShot` on main thread; `time.sleep(0.05)` off it |
| TTS engine | Qt object on the main thread | `stop()` stops speech; the engine stays | Qt |
| Event listener, device update timer | event_handler (other subsystem) | `shutdown_cleanup` | - |

Every Run timer, loop and held output registers with `run_scope`; `run_scope.stop()` lets go of them in stage order (CUT_INPUT, CANCEL, FIRE_PENDING, END_WORK, RELEASE_HELD, NEUTRAL, ...), each step once, errors logged and the rest go on. CUT_INPUT also has "OSC releases" (`OscRuntime.release_held()`, before "input off"; 09 S40a, D-09-OSC-STOP, 2026-10-09).

Event callbacks run on the main thread (queued Qt signals from the listener thread). Macro steps run on macro threads, so a vJoy or Logical Device write can come from a macro thread, a relative-axis thread, a script-timer thread and the main thread at the same time.

## 7. Rule breaks

| # | Rule | Where | What | Status |
|---|---|---|---|---|
| RB1 | Layer (output read skips the output module) | `code_runner.py:461-470` | `_refresh_axes` reads vJoy axis values from the DirectInput readback (`input_cache.Joystick()[vjoy guid]`) instead of `output.vjoy_value` | CONFIRMED |
| RB2 | Single owner (Run number) | `code_runner.py:283`, `macro.py:96`, `user_script.py:126` | three Run counters | CONFIRMED (map 3 A, E, M) |
| RB3 | Single owner (held outputs) | `macro.py:54`, `sendinput.py:441`; untracked `keyboard.py:217` | two held lists, script keys untracked | CONFIRMED (map 3 E-H) |
| RB4 | Run ends everything it started | `tempo/__init__.py:174`, `double_tap/__init__.py:191`, `smart_toggle/__init__.py:84` | timers survive Stop and write outputs, reopening vJoy or replugging the Xbox pad | CONFIRMED (AU-116) |
| RB5 | Run ends everything it started | `map_to_vjoy/__init__.py:163` | relative loop ends only when vJoy is released, not on the Run number | CONFIRMED (AU-117) |
| RB6 | Run ends everything it started | `code_runner.py:440-444` | release callbacks cleared at Run only, so a release left from the last Run fires in the next | CONFIRMED (map 3 D) |
| RB7 | Run ends everything it started | `logical_device.py:67`, `237` | Logical Device values never go back to neutral at Stop | CONFIRMED (AU-117) |
| RB8 | Stop done once | `joystick_gremlin.py:262-285` | quit stops twice and resets drivers, audio, TTS and OSC a second time | CONFIRMED (map 3 Q; harmless today) |
| RB9 | Clock rule | `sendinput.py:135`, `373`; `audio_player.py:190`; `user_script.py:208-237`; `vjoy/vjoy.py:539, 806, 828, 938`; `base_classes.py:656`; `output.py:48, 71, 151, 158`; `code_runner.py:202` | `time.time/monotonic/sleep` instead of `gremlin.clock` (AU-62 left older uses on purpose; `code_runner:202` cannot run: one value per event) | CONFIRMED |
| RB10 | Thread safety | `vjoy/vjoy.py:908-957` | `VJoyProxy.vjoy_devices` is a class dict with no lock, opened from macro, loop, script and main threads; reset swaps it while another thread may be opening | SUSPECTED |
| RB11 | Thread safety | `logical_device.py:67` | Logical Device values written from the main thread, its loop thread and macro threads, no lock | SUSPECTED |
| RB12 | Single owner (Logical Device writers) | `macro.py:770-771` | `LogicalDeviceAction.create()` creates Button 1 when the Logical Device is empty (a side effect of building a default step, no Undo) | CONFIRMED |
| RB13 | Single owner (Logical Device writers) | `ui/device.py:512-543` | `LogicalDeviceManagementModel.createInput/changeName/deleteInput` write the Logical Device with no Undo; no QML user found (`action_label.py:17` patches it) | SUSPECTED dead code |
| RB14 | Lock in one place | `logical_layout.py` (no Run check), `LogicalPage.qml:114` | the "locked while running" rule lives only in QML; an action pane already open when Run starts stays open (no `onEditorLockedChanged`) | CONFIRMED (code), effect SUSPECTED |
| RB15 | Duplicated logic | `logical_layout.py:16-38` | imports private helpers from `module_model` (`_load_module_doc`, `module_exists`) and `binding_catalog` (`_attach_binding`, `_clone_binding`, `_drop_shadow`) | CONFIRMED (map 2 covers the draft helpers) |
| RB16 | One failure, one path | `output.py:56-59` | a failed module-file read gives an empty claim list, so every vJoy output is blocked for up to 1 s | CONFIRMED in code (AU-64, not reproduced) |
| RB17 | Failed Run cleanup | `code_runner.py:368-371`, `backend.py:420-428` | a `start()` that fails after connecting leaves the signals and the callback table; the next Run press calls `start()` again (not `stop()`), connecting a second time and adding the callbacks again | SUSPECTED (ACT21 fixed only the Stop side) |
| RB18 | Failed Run UI | `backend.py:420-428`, `code_runner.py:391, 396-398` | an exception in `start()` skips `activityChanged`, leaves input highlighting suspended; `_refresh_axes` runs after `_running=True`, so a failure there leaves "Running" with no error shown in the UI | SUSPECTED |
| RB19 | Reads must not open a driver | `output.py:303-315` | `vjoy_value` opens the vJoy device (conditions, Map to vJoy relative, macro relative steps), unlike `vjoy_state` | CONFIRMED (in a Run this is mostly fine) |
| RB20 | Bounded waits on the main thread | `map_to_vjoy/__init__.py:132`, `map_to_logical_device/__init__.py:134` | `join(timeout=1.0)` on the main thread when a relative loop restarts | CONFIRMED (bounded, up to 1 s freeze) |
| RB21 | Run counters / Stop for sound and speech | `audio_player.py:153`, `tts.py:70` | no running check: a sound or speech queued after Stop (a late timer) plays at once (TTS) or at the next Run (sound) | SUSPECTED |

Keyboard and mouse output (`keyboard.py`, `sendinput.py`) go straight to Windows `SendInput`, not through an output module. The help names only vJoy and Xbox as output modules, so this is by design; see Q9.

## 8. Behaviour spec

### Run and Stop
- S1. It should start the profile with the toolbar **Run** button; while running the button reads **Stop** and uses the accent color. [help: Run and status] [glossary]
- S2. It should show **Running**, **Stopped** or **Running (Paused)** in the status bar, plus "(unsaved changes)" when the running profile has some. [help: Run and status] [glossary]
- S3. It should offer **Run Profile** / **Stop Profile** in the tray menu, with a different tray icon while running. [glossary] [user confirmed 2026-10-06; was code only for the icon]
- S4. It should send nothing to vJoy, Xbox or the Logical Device while stopped; stopped means editing only. [help: Run and status] [glossary: Run / Stop]
- S5. It should run in the mode shown on the toolbar; if that mode is not in the profile, it should use the profile's Startup Mode rule. [help: Modes] [help: Profile Settings] [user confirmed 2026-10-06; was code only for the fallback]
- S6. It should save the running mode at Stop so "Last Active" can use it. [help: Profile Settings] [user confirmed 2026-10-06; was code only for "at Stop"]
- S7. It should use the profile's own Macro Default Delay, or the Options value when the profile sets none. [tracker: B27] [test: test_profile_settings.py::test_macro_delay_follows_options_unless_set]
- S8. It should set the vJoy Initial Values of axes when the profile starts, always, through the output module; moving a physical axis then overrides them (Q7). [help: Profile Settings] [user confirmed 2026-10-06; was code only] [changed 2026-10-07: "today" note removed, fixed in batch 1]
- S91. A profile start should not fail because one device's control can't be read: that control is skipped and logged once, and the rest of the profile runs. [user decision 2026-10-10: D-06-START-SKIP (DX2, D2G2)]
- S9. It should re-send the current physical axis values at Run and at a mode change when those Options are on; an axis not moved since the program started is sent as centre (documented in help; D-02-AXIS-START). [help: Options] [test: test_mode_refresh_and_add_key.py::test_runner_refreshes_axes_on_mode_change_only_while_listening]
- S10. It should skip a script that fails to load (retrying it once at Run) and log why, and still run the rest. [user confirmed 2026-10-06; was code only]
- S11. It should skip a broken user plugin instead of failing the Run. [tracker: AU-86] [test: test_audit_runtime.py::test_a_broken_user_plugin_is_skipped]
- S12. It should show "Could not run the profile: a user plugin is missing." when a script import fails. [user confirmed 2026-10-06; was code only]
- S13. It should lock editing (Configuration, Keyboard, OSC, Logical Device; not the output pages) while running, with "Profile running: stop it to edit". [help: Logical Device] [user confirmed 2026-10-06; was code only for the other pages]
- S14. It should have the Run flag on only while a profile runs. [tracker: AU-60] [test: test_audit2_coverage.py::test_the_run_flag_is_on_only_while_a_profile_runs]
- S15. It should Stop before opening another profile or a new one. [user confirmed 2026-10-06; was code only]
- S16. It should Stop, load and Run again when a Load Profile action fires while running. [test: test_audit2_coverage.py::test_load_profile_loads_and_restarts_the_run]
- S17. It should Stop before quitting, and quitting while running should leave no vJoy device held and no Xbox pad plugged in. [user confirmed 2026-10-06; was code only] [tracker: H2] A vJoy device it lets go of (Stop or quit) is left at rest first: every button up, every hat centred, every axis centred; nothing it held stays pressed. [user decision 2026-10-07: D-06-VJOY-REST]
- S18. It should disconnect everything a failed Run connected when Stop is pressed. [tracker: ACT21] [test: test_action_fixes.py::test_stop_disconnects_after_a_failed_run]
- S19. Stop then Run should start clean: no macro queued in the last Run runs, and a macro of the last Run leaves the new Run alone. [tracker: ACT17] [test: test_action_fixes.py::test_run_starts_with_no_stale_macros] [test: test_audit2_macros.py::test_a_macro_of_the_last_run_leaves_the_new_run_alone]

### At Stop
- S20. It should end every macro at its next step, and a Pause step at once. [tracker: AU-87] [test: test_audit2_macros.py::test_a_one_shot_macro_stops_with_stop] [test: test_audit3_run_stop.py::test_stop_during_a_step_in_progress_ends_the_macro]
- S21. It should release every key a macro or Map to Keyboard still holds, last pressed first. [tracker: AU-111] [test: test_audit3_run_stop.py::test_a_key_a_macro_holds_is_released_at_stop] [test: test_audit3_run_stop.py::test_map_to_keyboard_keys_are_released_when_stop_drops_the_release]
- S22. It should release every mouse button still held, and one failing release must not stop the others. [test: test_audit3_run_stop.py::test_mouse_buttons_held_at_stop_are_released] [test: test_audit3_run_stop.py::test_a_failing_mouse_release_doesnt_cut_stop_short]
- S23. It should stop mouse motion, and the next Run should not move the pointer at the old speed. [test: test_audit3_run_stop.py::test_mouse_motion_of_the_last_run_stops_with_it]
- S24. It should send pending short-pulse releases before the drivers are released. [tracker: AU-99] [test: test_audit2_macros.py::test_a_pulse_release_waiting_at_stop_is_sent_first]
- S25. It should end the Logical Device relative-axis loop. [test: test_audit3_run_stop.py::test_the_logical_device_relative_loop_ends_with_stop]
- S26. It should end the vJoy relative-axis loop, also when Run is pressed again at once. [tracker: AU-117] [changed 2026-10-07: open-gap note removed, fixed in batch 1]
- S27. It should stop script timers, also a slow one, and the next Run should start its own timer loop. [tracker: AU-34] [test: test_audit_runtime.py::test_a_run_after_a_slow_stop_starts_its_own_loop] [test: test_audit_runtime.py::test_a_periodic_callback_with_no_interval_still_stops]
- S28. It should stop sounds and speech and empty their queues. [user confirmed 2026-10-06; was code only]
- S29. It should release every vJoy device and unplug every Xbox pad. [help: Xbox output module] [user confirmed 2026-10-06; was code only for vJoy]
- S30. It should never fire a Tempo, Double Tap or Smart Toggle timer after Stop. [tracker: AU-116] [changed 2026-10-07: open-gap note removed, fixed in batch 1]
- S31. It should release keys a script pressed during a Run. [tracker: AU-117] [user decision: R4 (Q4)] [changed 2026-10-07: open-gap note removed, fixed in batch 1]
- S32. It should finish within a bounded time even if a macro step or a driver call is stuck. [tracker: H5] [test: test_audit3_run_stop.py::test_a_step_stuck_in_a_driver_ends_the_other_macros] [test: test_bounded_waits.py::test_a_macro_stops_waiting_for_an_exclusive_one_when_stopped]

### Events while running
- S33. It should run only actions of inputs the input module claims; the Logical Device and OSC pass without a claim. [help: Input modules] [test: test_logical_events_pass_gate.py::test_logical_device_events_reach_the_wire] [test: test_logical_events_pass_gate.py::test_unclaimed_hardware_is_still_dropped]
- S34. It should run the running mode's actions, and a child mode should use its parent's actions for inputs it leaves empty. [help: Modes] [glossary: Mode]
- S35. It should run the other actions of an event, and its release actions, when one action fails. [tracker: AU-16] [test: test_audit_runtime.py::test_one_failing_action_does_not_stop_the_others] [test: test_audit2_coverage.py::test_a_failing_action_still_runs_the_release_actions]
- S36. It should, while paused, run nothing except actions marked to always run (so Resume still works), and skip script callbacks without an error. [help: Pause and Resume] [tracker: ACT10] [test: test_action_fixes.py::test_while_paused_a_script_callback_does_not_stop_the_rest] [test: action_interaction/test_pause_resume.py::test_pause_resume]
- S37. It should start each Run un-paused. [user confirmed 2026-10-06; was code only]
- S38. It should release a vJoy or Logical Device button pressed in one mode when its physical button is released after the mode changed. [user confirmed 2026-10-06; was code only]
- S39. It should treat an axis range as a button: press on entering the range (in the chosen direction), release on leaving, press and release when the axis jumps across it; an axis already inside the range at Run gives no press. [user confirmed 2026-10-06; was code only]
- S40. It should treat a set of hat directions as one button. [user confirmed 2026-10-06; was code only]
- S41. It should give a stick plugged in while running its claims (with any device-change setting). [tracker: DEV11]
- S42. It should follow Options > Device change behavior when a controller is plugged in or removed while running: Reload (Stop and Run), Ignore, Disable (Stop). [help: Run and status]
- S43. It should let go of a held button or hat of a stick that is unplugged. [test: test_device_reconnect.py::test_held_inputs_are_let_go_on_unplug]
- S44. It should not release vJoy devices when only a stick (not a vJoy device) is plugged or unplugged. [tracker: DEV5] [test: test_device_scan.py::test_plugging_in_a_stick_does_not_reset_vjoy] [test: test_device_scan.py::test_a_vjoy_change_still_resets_vjoy]
- S45. It should, with auto-load on, load and Run a program's profile when the program comes to the front, Stop on focus loss unless "Keep running" is on, never switch over unsaved changes (one notice), and Stop rather than run the wrong profile when the program's profile file is missing. [help: Options] [test: test_audit2_saving.py::test_a_missing_auto_load_profile_stops_the_open_one] [test: test_audit_saving.py::test_auto_load_with_a_missing_profile_runs_nothing_else]
- S46. It should evaluate conditions through the input modules (an unclaimed input reads as neutral), and a condition on a stick plugged in later should work. [user confirmed 2026-10-06; was code only] [test: test_audit3_run_stop.py::test_a_condition_on_a_stick_plugged_in_later_works]

### vJoy output
- S47. It should send to a vJoy output only when its output module claims it and the vJoy device has it; anything else sends nothing and is logged once per Run. [help: vJoy output modules] [test: test_output_layer.py::test_unclaimed_write_is_blocked_and_logged_once] [test: test_output_layer.py::test_claimed_output_the_driver_lacks_is_refused] [test: test_output_layer.py::test_claimed_write_reaches_the_driver]
- S48. It should read unclaimed or missing vJoy outputs as neutral (axis 0, button up, hat centre). [test: test_output_layer.py::test_reads_of_unclaimed_outputs_are_neutral]
- S49. It should let only the output module open the vJoy driver; Map to vJoy, macros, auto-release, start-up axes and scripts all go through it. [test-plan: P2b] [test: test_vjoy_writers_use_firewall.py::test_only_the_output_module_holds_the_vjoy_driver] [test: test_vjoy_writers_use_firewall.py::test_map_to_vjoy_writes_through_the_output_module]
- S50. It should give scripts a `vjoy` object that can use only claimed outputs. [help: Scripts] [test: test_vjoy_writers_use_firewall.py::test_scripts_get_the_firewalled_vjoy]
- S51. It should never open a vJoy device for a viewer or a Home card; they show values only while the profile holds the device. [test-plan: P2d] [test: test_output_layer.py::test_unopened_device_gives_nothing]
- S52. It should, when another program holds a vJoy device, show "vJoy N is in use by another program." once per Run, log once, retry every 3 s and carry on by itself when the device is free. [tracker: DEV6] [test: test_device_fixes.py::test_busy_vjoy_is_told_once_and_retried_every_few_seconds] [test: test_device_fixes.py::test_a_new_run_tells_again]
- S53. It should pick up an output module saved while running at once, the same as an input module (Q12). [user confirmed 2026-10-06; was code only] [changed 2026-10-07: "today" note removed, fixed in batch 1]
- S54. It should keep an idle vJoy device alive (re-send after 60 s of no writes) while held, and arm no new keep-alive after release. [user confirmed 2026-10-06; was code only] [test: test_batch3_C3a.py keep-alive tests]
- S55. It should say "vJoy is not installed or not running" / "Install vJoy, then restart the program." wherever the vJoy driver is checked. [user confirmed 2026-10-06; was code only] [changed 2026-10-07 to follow decision D-02-Q17 (glossary), which wins over the earlier wording "restart Gremlin-Platforms"]
- S86. While Tracing is on (01 S147), every vJoy write caused by a ticked control should write an OUTPUT line `vJoy N <axis X|Button n|Hat n> = value · written | blocked (not claimed by the vJoy N module) | failed: <why> | missing (vJoy N has no …)`; blocked and missing show as BLOCKED. Writes no ticked control caused write nothing. Each written value is kept for the out-of-step check. Run, restart, Stop and a failed start write EVENT lines, and so does a mode change while a profile runs (`CodeRunner._refresh_on_mode_change`). OUTPUT lines also cover Map to Mouse: one line per change (motion speed or direction change, button press or release), never one per motion tick. [user decision: D-01-TRACE] [changed 2026-10-10, user: D-06-MOUSE (G-c): Map to Mouse in Trace OUTPUT]
- S87. The out-of-step watch (every 1 s while tracing, devices ticked for the Out-of-step check) should warn OUT OF STEP when a ticked axis polled from the driver differs from its last RAW value by more than 0.05 for over 1 s, or when a vJoy axis read back (as Windows sees that vJoy device when it can be found, else the program's own value) differs from its last written value by more than 0.02 for over 1 s; one warning per episode, again only after it was back in step; one EVENT "no input from this stick for 4.0 s while plugged in (info only: a still stick is normal)" per quiet spell. Full wording in 01 S150. [user decision: D-01-TRACE]

### Xbox output
- S56. It should pass every control of the Xbox 360 pad straight to ViGEm, with nothing to claim; an old claim in a file is ignored. [help: Xbox output module] [user decision: Xbox output has no claims] [test: test_xbox_output_module.py::test_every_control_reaches_the_pad] [test: test_xbox_output_module.py::test_an_old_xbox_claim_in_a_file_is_ignored] [test: test_xbox_output_module.py::test_no_xbox_code_reads_a_claim]
- S57. It should plug in the pad when a Map to Xbox action first sends while running, and unplug it at Stop. [help: Xbox output module] [help: Xbox does nothing]
- S58. It should take the pad number from the module name ("Xbox 360 Controller" = pad 1, "Xbox 360 2" = pad 2); one pad for now. [test: test_xbox_output_module.py::test_pad_number_comes_from_the_name] [test-plan: to-do 16]
- S59. It should rest a trigger at 0 when its button is released; Full axis maps -1..+1 to 0..100%, Upper half maps centre..+1. [help: Map to Xbox] [tracker: DEV7] [test: test_map_to_xbox.py::test_trigger_range]
- S60. It should never plug in a pad for a viewer. [user confirmed 2026-10-06; was code only] [test: test_xbox_output_module.py::test_viewer_sees_every_control]
- S61. It should never treat a real Xbox controller as Gremlin's pad. [tracker: DEV1]
- S62. It should never plug in two pads for one pad number when two threads send at once. [tracker: DEV14]
- S63. It should log a failed Xbox write once and go on. [user confirmed 2026-10-06; was code only]
- S64. It should describe the ViGEmBus state (found with version, not installed, installed but not running, DLL missing) with one wording everywhere. [help: Xbox output module] [tracker: G-XBOXDRV]

### Macros, keyboard, mouse
- S65. It should play a macro's steps with the default delay between steps (not around Pause steps), and support Single, Count, Toggle and Hold repeat with a delay. [help: Macro] [help: Profile Settings] [test: action_interaction/test_macro.py::test_repeat]
- S66. It should make an Exclusive macro wait for running macros and then block others; a Pre-Emptive one pauses the others instead. [help: Macro] [test: action_interaction/test_macro.py::test_preemptive_exclusive_pauses_and_resumes_macro] [test: action_interaction/test_macro.py::test_non_preemptive_exclusive_waits_for_running_macro]
- S67. It should run a Hold macro's first round even if released at once, then stop. [tracker: ACT17] [test: test_action_fixes.py::test_a_hold_macro_released_at_once_stops]
- S68. It should do nothing for an empty macro. [tracker: ACT8] [test: test_crash_and_loss_fixes.py::test_an_empty_macro_does_nothing]
- S69. It should end only the failing macro when a step fails, and a step stuck in a driver should end the macros waiting behind it after 2 s. [tracker: AU-17] [test: test_audit_runtime.py::test_a_failing_macro_step_blocks_nothing] [test: test_audit3_run_stop.py::test_a_step_stuck_in_a_driver_ends_the_other_macros]
- S70. It should release a key held by a macro that ended early. [tracker: AU-117] [changed 2026-10-07: open-gap note removed, fixed in batch 1]
- S71. It should, with Map to Keyboard, hold the keys while the input is held (modifiers first) and release them on release. [help: Map to Keyboard]
- S72. It should, with Map to Mouse, click a button (wheel once per press) or move the pointer with the set speeds and direction. Motion from several inputs adds up; each button or hat ramps on its own; speeds are delivered as set. The update rate is fixed at 100 Hz (no option). [help: Map to Mouse] [changed 2026-10-10, user: D-06-MOUSE (R9, R9c): motion adds up, per-input ramps, speeds as set, no update-rate option]
- S88. A mode change should stop Map to Mouse motion that the new mode doesn't route to the same binding. [user decision 2026-10-10: D-06-MOUSE (R9)]
- S89. Stop should drop Map to Mouse motion at the first Stop stage (when input is cut). [user decision 2026-10-10: D-06-MOUSE (R9)]
- S90. Pause should stop Map to Mouse motion. [user decision 2026-10-10: D-06-MOUSE (R9b)]

### Sound and speech
- S73. It should play WAV, MP3 or OGG at the set volume, overlapping sounds as Options says (Sequential, Interrupt, Overlap). [help: Play Sound] [user confirmed 2026-10-06; was code only for the three names]
- S74. It should open a profile whose Play Sound file is missing; pressing it plays nothing; an unreadable file is logged once. [tracker: ACT11] [test: test_play_sound_missing_file.py::test_pressing_with_a_missing_file_plays_nothing] [test: test_program_fixes.py::test_a_sound_that_cannot_be_decoded_is_logged_once]
- S75. It should decode sounds off the event thread and free finished sounds. [tracker: APP6] [test: test_program_fixes.py::test_sounds_are_decoded_on_the_playback_thread] [test: test_program_fixes.py::test_finished_sounds_are_let_go]
- S76. It should speak with the voice set in Options, and Interrupt, Queue Front or Queue Back; volume shown 0-100%. [help: Text to Speech] [tracker: E2]

### Logical Device
- S77. It should be a device inside the program with buttons, axes and hats named by type and number (Button 1, Axis 1, Hat 1); its values are fed by Map to Logical Device and its controls have actions of their own. [help: Logical Device] [glossary: Logical Device]
- S78. It should add up to 180 controls at once, reuse the lowest free number, and sort names by number (Button 2 before Button 10). The number is a display name only; references use the permanent id (04 S2a); a control brought in with an id (Device Pack) whose number is taken gets the lowest free number. [changed 2026-10-09, user: D-04-LD-FILE] [help: Controls, groups, and the menu] [test: test_logical_device.py::test_create_many_caps_at_180] [test: test_logical_device.py::test_index_reuse] [test: test_logical_device.py::test_labels_sorted_naturally]
- S79. It should let the user rename a control, hide the system name, clear the name, group controls, move and sort them, and treat group names that differ only in capitals or spaces as the same group. [help: Controls, groups, and the menu] [user confirmed 2026-10-06; was code only for the group-name rule]
- S80. It should list, in Assign Hardware, claimed physical controls of the same type (keys for buttons, OSC too) and add or remove a Map to Logical Device action in the page's mode; a vJoy used as output is never a source. [help: Assign hardware and actions] [test: test_logical_layout.py::test_named_vjoy_cannot_be_a_source_module]
- S81. It should send on to Xbox or vJoy only through the control's own actions, never through Assign Hardware. [help: Sending to Xbox or vJoy]
- S82. It should lock editing while the profile runs. [help: Logical Device]
- S83. It should keep up to 50 Undo steps, keep them when another profile loads (the Logical Device is shared by every profile) except the parts that changed the old profile's actions or links, which are dropped; drop all of them when a mode is deleted, on Discard, and when its file is read again (Restore, Import, History Restore) [changed 2026-10-09, user: D-04-LD-FILE], record no step for a change to nothing, and leave everything as it was when a step can't be played. [tracker: AU-11] [tracker: AU-33] [test: test_audit_editing.py::test_logical_layout_steps_stay_when_another_profile_loads] [test: test_audit_editing.py::test_a_logical_change_to_nothing_is_no_step] [test: test_audit3_actions_undo.py::test_logical_undo_with_a_damaged_input_copy_changes_nothing]
- S84. It should close the action editor with a notice when its mode is deleted, and OK should go to the pane's own mode. [tracker: AU-89] [test: test_audit2_modes.py::test_logical_ok_goes_to_the_panes_own_mode]
- S85. It should start each Run with its values at neutral. [user decision: R1 (Q1)] [changed 2026-10-07: open-gap note removed, fixed in batch 1]

## 9. Questions for the user

- Q1. Logical Device values at Stop (decision R1): neutral or kept? **Recommend neutral** (axis 0, button up, hat centre), so S85 holds.
- Q2. Release callbacks waiting at Stop (R2): drop or fire? **Recommend drop**; held-output release and the driver reset already let go.
- Q3. Mode at the next Run (R3): always the toolbar mode with temporary modes cleared? **Recommend yes.**
- Q4. Keys scripts press (R4): release only those sent during a Run? **Recommend yes.**
- Q5. A Run that fails partway: should pressing Run again first clean up (as Stop does), and should the user always see an error and "Stopped"? Today a second press may connect everything twice (RB17) and the toolbar may say Running after a failure (RB18). **Recommend: a failed start runs Stop itself, shows one error, and the status reads Stopped.**
- Q6. The Logical Device action editor (and the Configuration pane) open when Run is pressed: close it, keep it read-only, or block Run until OK/Cancel? **Recommend: ask "Save or discard the open action first?" before Run**, the same as leaving the page.
- Q7. vJoy Initial Values are written only when the axis reads exactly 0 through the DirectInput readback (RB1). Is that wanted? **Recommend: always write them at Run through the output module**, then let the refresh of physical axes overwrite them.
- Q8. Play Sound and Text to Speech have no Run check: a sound or speech queued after Stop plays (RB21). **Recommend: ignore them when no Run is on.**
- Q9. Keyboard and mouse output go straight to Windows, not through an output module. Is that an accepted exception to the layer rule? **Recommend yes**, written down as such, with held keys and buttons tracked in one place (map 3 `run_scope`).
- Q10. A `VJoyError` inside an action pauses the whole profile with an error box. With the output layer, writes no longer raise it, so this path almost never runs. Keep auto-pause? **Recommend remove it**; the output layer's "logged once" and the busy message are the user's signal.
- Q11. Pause and Stop: a paused profile shows "Running (Paused)"; Stop then Run starts un-paused. **Recommend keep.**
- Q12. Output module changes saved while running take effect within 1 s; input module changes at once (reload on save). **Recommend: both at once** (force `output.refresh()` on save).
- Q13. An axis-range virtual button whose axis is already in range at Run gives no press until it leaves and re-enters (S39). **Recommend keep** (no surprise press at Run), but confirm.
- Q14. A macro's Joystick step pretends to be the physical stick, so it passes the input-module gate only for claimed controls. **Recommend keep**, and say so in the Macro help.
- Q15. Adding a Logical Device step to a macro (or a Logical Device condition) when the Logical Device is empty silently creates Button 1 (RB12), and a Logical Device condition indexes the first control and fails when there is none. **Recommend: no hidden create; show "Add a Logical Device control first".**
- Q16. Reads of vJoy values (conditions, relative steps) open the vJoy device (RB19). **Recommend: reads never open a device**, the same as the viewers; only writes do.
- Q17. Map to vJoy relative axis ends when vJoy is released, not when the Run ends (RB5). **Recommend: end on the Run number** like the Logical Device loop (map 3 step 4).
- Q18. `LogicalDeviceManagementModel.createInput/changeName/deleteInput` (no QML user found) is a second Logical Device writer without Undo. **Recommend remove** after a grep confirms no user.
- Q19. Help says the Xbox pad "is removed when the profile stops"; the code also unplugs it on quit and when another program's device change triggers Reload. A late timer (AU-116) plugs it back after Stop. **Recommend: no pad outside a Run, ever** (closes with AU-116).

## 10. Known gaps

Code against spec or rule:
- G1. (done, batch 1 d68f4d88, GL-047: Run timers through `run_scope.timer`) Tempo, Double Tap and Smart Toggle timers fire after Stop and write outputs, reopening vJoy or plugging the Xbox pad back in (S30, RB4). [tracker: AU-116]
- G2. (done, GL-048) Map to vJoy relative loop can carry into the next Run on a quick Stop/Run (S26, RB5). [tracker: AU-117]
- G3. (done, GL-049: `run_scope.hold`) Keys a script presses stay down after Stop (S31, RB3). [tracker: AU-117]
- G4. (done, GL-048) A macro that ends early leaves its key down until Stop (S70). [tracker: AU-117]
- G5. (done, GL-050: NEUTRAL stage) Logical Device values carry into the next Run (S85, RB7). [tracker: AU-117]
- G6. (done, GL-051) A release callback from the last Run can fire in the next (RB6). No tracker item.
- G7. (done, GL-046: one Run number in `run_scope`) Three Run counters can disagree (RB2). No tracker item.
- G8. (done, GL-054: a failed start runs Stop itself) A failed Run, then Run again: events and callbacks may be handled twice; the UI may say Running after a failure (RB17, RB18). No tracker item; ACT21 fixed only Stop.
- G9. A failed output-claims read blocks every vJoy output for up to 1 s (RB16). [tracker: AU-64]
- G10. vJoy Initial Values depend on the DirectInput readback reading 0 (S8, RB1).
- G11. Sound and speech after Stop (RB21).
- G12. Logical Device and Configuration action pane can stay open when Run starts (RB14).
- G13. Hidden Logical Device create in `LogicalDeviceAction.create()`; Logical Device condition on an empty device (RB12, Q15).
- G14. Clock rule not followed in mouse, audio, script timers, vJoy wrapper, pulses and output layer (RB9). AU-62 left them on purpose; the rule says new code only.
- G15. No lock on `VJoyProxy.vjoy_devices` or on Logical Device values, written from several threads (RB10, RB11). Suspected.
- G16. Quit runs Stop twice and resets drivers, audio, TTS and OSC twice (RB8). Harmless today.
- G17. `TTSManager.stop` leaves the engine and its signal connection alive across Runs (by design today; no `start` on a dead engine is possible).
- G19. Logical Device stand-alone (D-04-LD-FILE, 2026-10-09): own module file, permanent ids, Save covers it, Undo kept across profile loads (S78, S83; 04 S2-S2b, S25). Being built 2026-10-09 (`logical_device_file.py` new). [to-do 60 stage A]
- G18. Help "Run and status" wording matches the glossary, but the test plan rows TB-02 and W-06..09 still say "Toggle", "Active / Not Running", "Activate/Deactivate" (test-plan text only; no such words found on screen).
- D2G2. (fixed 2026-10-10, this batch: `input_refresh` skips and logs once; no other per-control reads at start in `code_runner`) A profile start aborts when one device's control can't be read (S91). [user decision: D-06-START-SKIP]
- G-c. (fixed 2026-10-10, this batch: `trace.mouse`) Map to Mouse writes no Trace OUTPUT lines (S86). [user decision: D-06-MOUSE]
- R9. (fixed 2026-10-10, this batch: `MouseMotionManager`, `ModeChangeActions`) Map to Mouse motion from several inputs overwrites instead of adding up; motion survives a mode change, Stop's first stage and Pause (S72, S88-S90). [user decision: D-06-MOUSE]
- G20. (new 2026-10-09, D-01-TRACE) Nothing showed where an input stopped between the driver and vJoy (9 Oct Star Citizen right stick, nothing in the logs). Tracing (S86-S87, 01 S146-S151) is being built 2026-10-09.
- OOS-REST. (fixed 2026-10-10, this batch: `output.reset_vjoy` calls `trace.rested`) The rest value Stop or a restart puts on a vJoy output wasn't counted as written, so the out-of-step watch warned OUT OF STEP falsely after Stop (S86, S87, S17; 01 S150). [test: test_trace_rest_on_stop.py]

From the to-do list:
- To-do 44 (done): tests never load the real vJoy driver (`test/vjoy_guard.py`); real-vJoy runs are opt-in (`run_tests.py --real-vjoy`).
- To-do 48: a vJoy loopback stand-in so the integration tests (test/integration) run on every normal run and on CI, not only with the real driver.

Open tracker items for this subsystem:
- AU-116 (open): Tempo, Double Tap, Smart Toggle timers not cancelled at Stop.
- AU-117 (open): other Run/Stop leftovers (macro key, vJoy relative loop, script keys, Logical Device values).
- AU-64 (open): suspected races; the 1 s output-claims block is in this subsystem.
- AU-119 (open): about 20 tests wait a fixed short time (Tempo, Double Tap, macro); test-only.
- APP5 (open, OSC parked): OSC listener opens a LAN port on every Run.
- AU-74 (won't fix): Run/Stop only on the toolbar and tray.

Things nothing owns:
- (Done in batch 1, GL-046) "What a Run holds" is owned by `gremlin/run_scope.py`; Stop runs its stages in order.
- The "locked while running" rule has no owner in Python; each QML page checks `gremlinActive` itself.
- Logical Device values have no reset owner (Stop puts them to neutral, GL-050; the device is no longer reset at profile load, D-04-LD-FILE).
- (Done in batch 3, GL-267) The keep-alive and the busy retry for vJoy are both in `output.py`.

## 11. Size and test coverage

Size (lines, roughly, 2026-10-09): run_scope 438, code_runner 634, event_helpers 239, macro 1257, sendinput 512, output 804, Xbox page and viewer about 1,180 (Python 654, QML 549), vjoy_status 187, audio_player 204, tts 122, logical_device 618, logical_layout 1580, LogicalPage.qml 2134, system_tray 332; vjoy 1100, vigem 720; parts of backend (~120), event_handler (~200), user_script (~200), base_classes (~120), joystick_gremlin (~45), Main.qml (~40). About 11,000 lines in all, half of it the Logical page.

Added 2026-10-10: `test_mouse_motion.py` (20: Map to Mouse adding up, ramps, mode change, Stop, Pause and Trace lines, S72, S86, S88-S90); `test_device_relaid_update.py` (a relaid device during a Run, 02 S143); `test_device_layout_change.py` (4, page 02; a start with one unreadable control, S91).
Added 2026-10-10 (OOS-REST): `test_trace_rest_on_stop.py` (146 lines; S86, S87, S17, 01 S150).

Covered well: Stop releasing held keys, mouse buttons and motion (`test_audit3_run_stop.py`); macros at Stop and stale macros (`test_audit2_macros.py`, `test_action_fixes.py`); the vJoy firewall (`test_output_layer.py`, `test_vjoy_writers_use_firewall.py`); vJoy busy (`test_device_fixes.py`); Xbox pass-through (`test_xbox_output_module.py`, `test_map_to_xbox.py`); thread start/stop (`test_threads.py`, `test_bounded_waits.py`); Logical Device data (`test_logical_device.py`) and its Undo (`test_audit_editing.py`, `test_audit3_actions_undo.py`, step labels `test_undo_bar_labels.py`); Logical page shared pieces (Find, delete questions, Undo bar: `test_config_pages_shared_pieces.py`); sound loading (`test_program_fixes.py`, `test_play_sound_missing_file.py`). The four files run off-screen today: 28 passed.

Not tested (seen in code, no test found):
- A Run that fails partway, then Run again (double connection, callbacks twice).
- `CodeRunner.start` end to end with a real profile, outputs mocked, then Stop: order of Stop steps (map 3 asks for an order test).
- Tempo/Double Tap/Smart Toggle timer firing after Stop (AU-116), vJoy relative loop across Stop/Run, script keys at Stop, Logical values at Stop (open gaps).
- `_refresh_axes` and vJoy Initial Values.
- `VirtualAxisButton` / `VirtualHatButton` edge cases (inside range at Run, jump across the range, None value).
- `ButtonReleaseActions` mode matching (DifferentMode) and release callbacks surviving Stop.
- `reset_drivers` at Stop with a plugged Xbox pad; the pad plugged in only on first write.
- `TTSManager` (no test file found), `AudioPlayer` Interrupt mode.
- Pause on `VJoyError`; status bar "(Paused)".
- Tray menu label and icon after Run/Stop (only start-up tray tests exist).
- Device change behaviour Reload/Disable while running; auto-load Stop on focus loss with "Keep running" on.
- Logical page: pane open when Run starts; `LogicalDeviceAction.create()` side effect; Logical Device condition with an empty device.
- Concurrent vJoy opens from a macro thread and the main thread.

## 12. Review (user, 2026-10-06)

All [code only] statements in section 8 confirmed (S8 and S53 changed by Q7
and Q12 as written there). Every question answered as recommended:

| Q | Decision |
|---|---|
| Q1 (R1) | Logical Device values go back to neutral at Stop |
| Q2 (R2) | Release callbacks waiting at Stop are dropped |
| Q3 (R3) | Next Run uses the toolbar mode, temporary modes cleared |
| Q4 (R4) | Script keys are released at Stop only if sent during a Run |
| Q5 | A failed start runs Stop itself, shows one error, status reads Stopped |
| Q6 | Run asks "Save or discard the open action first?" when an editor is open |
| Q7 | vJoy Initial Values always written at Run through the output module |
| Q8 | Sound and speech ignored when no Run is on |
| Q9 | Keyboard and mouse output going straight to Windows is an accepted, written exception to the layer rule; held keys and buttons tracked in one place |
| S86-S87 | 2026-10-09 (D-01-TRACE; user: "go with your recommendations, approved, go ahead"): OUTPUT trace tap and the out-of-step watch |
| S72 and S86 changed, S88-S90 | 2026-10-10 (D-06-MOUSE; user approved R9, R9b, R9c "no option", G-c): Map to Mouse motion adds up, per-input ramps, stops on mode change, Stop and Pause, fixed 100 Hz; Trace OUTPUT covers it |
| S91 | 2026-10-10 (D-06-START-SKIP; user approved DX2 / D2G2): a profile start skips and logs a control it can't read |
| Q10 | The auto-pause on a vJoy error inside an action is removed |
| Q11 | Paused shows "Running (Paused)"; Stop then Run starts un-paused (kept) |
| Q12 | Output module changes saved while running apply at once |
| Q13 | An axis already in range at Run gives no press (kept) |
| Q14 | A macro's Joystick step passes claimed controls only (kept; say so in Macro help) |
| Q15 | No hidden Button 1 on an empty Logical Device; say "Add a Logical Device control first" |
| Q16 | Reads never open a vJoy device; only writes do |
| Q17 | Map to vJoy relative axis ends with its Run |
| Q18 | Remove the unused second Logical Device writer (after a grep confirms no user) |
| Q19 | No Xbox pad outside a Run, ever |

| S78, S83 | 2026-10-09: D-04-LD-FILE (number is a display name, references use the permanent id; Undo steps kept across profile loads) |

The section 8 statements are now the definition of correct for this
subsystem; where today's code differs (section 10 and the decisions above),
that is a gap to fix, each starting as a failing test.

**Change (user, 2026-10-06), S39:** an axis-range button sends no release
without a press: if the axis was already inside the range at Run (no press,
Q13), leaving the range sends nothing. S39 now reads: "... an axis already
inside the range at Run gives no press, and leaving it then gives no
release." [user decision: 06 S39 addition]
