# Devices and raw input

Mapped against code at 4f6bdfa4 (6 Oct); sections 2-6, 10 and 11 brought up to date 9 Oct (after catch-up batches 1-3 and the Device Library). Line numbers drift; re-check them before a step starts.

## 1. Purpose

This part finds the controllers Windows reports (sticks, throttles, pedals, vJoy devices), gives each one a name and an id, and turns every button press, axis move, hat push and key press into one kind of event the rest of the program reads. It notices when a controller is plugged in or pulled out, and lets go of what an unplugged stick was holding. It also covers HidHide (hiding controllers from games), "Listen for input", and the watcher that tells auto-load which program has focus.

## 2. Files

| Path | What it holds |
|---|---|
| `dill/__init__.py` (394) | ctypes wrapper for `dill.dll` (DirectInput): `GUID`, `DeviceSummary` (name, VID/PID, axis/button/hat counts, axis map, `vjoy_id`), `InputEvent`, `DILL` static API (`init`, `get_device_count`, `get_device_information_by_index/guid`, `device_exists`, `get_axis/button/hat`, `set_input_event_callback`, `set_device_change_callback`). Fixed ids: `UUID_Keyboard`, `UUID_Virtual`, `UUID_LogicalDevice`, `UUID_Invalid`. |
| `dill/dill.dll` | Native DirectInput listener; runs its own thread and calls back into Python. |
| `gremlin/device_initialization.py` (570) | The device list: scan (`joystick_devices_initialization`), twin naming (`_name_twins`), vJoy-to-DirectInput matching and "vJoy left out" messages, list getters (`joystick_devices`, `physical_devices`, `vjoy_devices`, `input_devices`, `output_vjoy_devices`, `device_for_uuid`, `device_name`). |
| `gremlin/event_handler.py` (825) | `Event` (one input event), `EventListener` (singleton: DLL callbacks, keyboard/mouse hooks, calibration, hot-plug timer, unplug let-go, Qt signals), `EventHandler` (singleton: callback table per device/mode/input, `known_modes`, pause/resume, `process_event`, which also feeds the Input Monitor tap, `gremlin/input_monitor.py`, page 01). |
| `gremlin/input_cache.py` (581) | `DeviceDatabase` (input labels from `device_db.json` by VID/PID), `JoystickWrapper` (last value of every axis/button/hat of one stick, `let_go`), `Joystick` (singleton cache of wrappers, plus the Logical Device), `Keyboard` (pressed-key cache). |
| `gremlin/windows_event_hook.py` (479) | Low-level Windows keyboard and mouse hooks (`KeyboardHook`, `MouseHook`), each with its own thread and message loop; `enabled` switch (off in tests and off-screen). The mouse hook has a start/stop count (Listen and macro Record share it); a slow key (`SLOW_KEY_MS` 200) is noticed. |
| `gremlin/keyboard.py` (439) | `Key` (name, scan code, extended flag, virtual key), key tables (`g_name_to_key`, `g_scan_code_to_key`), `key_from_name`, `key_from_code`, `modifier_keys`, `send_key_down/up` (keybd_event). |
| `gremlin/input_refresh.py` (43) | `RefreshPhysicalInputs.refresh_axes`: re-sends cached axis values (Run start, mode change). |
| `gremlin/device_helpers.py` (157) | `JoystickInputSignificant` (is an axis move big enough to count; used by highlight and Listen), `AxisChangeSignificanceTracker` (macro recording). |
| `gremlin/process_monitor.py` (135) | `ProcessMonitor` (polls the foreground program once a second, emits its path), `list_current_processes` (WMI list for the auto-load picker). |
| `gremlin/modules/hardware.py` (48) | The UI's door to the driver: `device_info` (raises for an unplugged stick), `device_connected`. |
| `gremlin/modules/runtime.py` (first ~140 lines) | `InputModuleRuntime`: the only consumer allowed to turn raw events into profile events (claims gate). Owned by the Input modules page; listed here as the first stop after raw input. |
| `gremlin/hidhide_driver.py` (980) | HidHide driver client, split out of the screen (D-02-Q10): control device calls (IOCTLs on `\\.\HidHide`: `get/set_active`, `get/set_inverse`, black and white lists, `driver_version`, `driver_present`), the HID device list (SetupAPI, cfgmgr32, hid.dll: `list_hid_devices`, gaming-only filter, names, container grouping), program image paths, `last_error`. Does not ship or install the driver. |
| `gremlin/ui/hidhide.py` (1015) | The HidHide screen side: saved HidHide choices (games, photos, module links, hidden devices), `HidHideModel` (QML), `apply_on_start`, `apply_saved_list`. |
| `gremlin/ui/util.py` (lines 50-292, 294-435) | `InputListenerModel` ("Listen for input", Esc-hold abort), `MacroRecorder` (records raw key/mouse/stick events), `ProcessListModel` (running programs for auto-load). |
| `gremlin/ui/device.py` (lines 182-298) | `DeviceListModel` (Device Information table, device pickers). Also `DeviceAxisSeries` and `AxisCalibration` (raw axis readers, Calibration page). |
| `gremlin/device_aliases.py` (134) | The names the user gives devices (Home card name, 10 S7), kept in the setting `devices/display/aliases`; not UI. The Device Library reads and renames through it. |
| `gremlin/ui/device_names.py` (79) | `DeviceNames`: relays alias changes to QML. |
| `gremlin/ui/backend.py` (lines 240-420) | Starts `ProcessMonitor`; `_device_change` (Device change behavior: Reload / Ignore / Disable); `_active_process_changed_cb` (auto-load); `_highlight_input` (raw input highlighting). |
| `joystick_gremlin.py` | Start-up order (`_no_hooks_offscreen` 880s, `hidhide.apply_on_start` 893, `DILL.init` 902, first scan 905, `MainFailure.qml` on scan error 909-918, `announce_vjoy_problems` 943), `shutdown_cleanup` 240 (listener, hooks, process monitor), option `device-change-behavior` 667. |
| `vigem/ids.py`, `vigem/own_pads.py` | Tell Gremlin's own virtual Xbox pads from real ones so the scan and hot-plug ignore them (owned by the Xbox output page). |
| `qml/DialogHardwareHide.qml` (563) | Tools > Device Setup > HidHide window. Remove program asks the shared question (`confirmRemoveGame` :54); headings are `SectionHeading`, empty lists `EmptyState`; its choosers are `FilePicker` kinds "picture" (device photo) and "other" (program). |
| `qml/InputListener.qml` (137) | The "Listen" button used by Keyboard list and Script settings. |
| `qml/KeyboardInputList.qml` (219) | Keyboard device page; adds keys with InputListener. |
| `qml/DialogDeviceInformation.qml` (208) | Tools > Device Setup > Device Information (DeviceListModel "all"). |
| `qml/DialogInputViewer.qml` (103) | vJoy Viewer (reads the claimed feed, not raw; listed for completeness). |
| `gremlin/ui/viewer_devices.py` (228) | The vJoy Viewer's device list and pairing labels (`Gremlin.Device`); re-reads on `device_change_event`; reads vJoy through the output module. |
| `qml/InputViewerCard.qml` (320), `qml/AxesStateSeries.qml` (133) | One device card in the vJoy Viewer (axes, buttons, hats), and its scrolling axis graph. |
| `gremlin/ui/xbox_viewer.py` (413) | The Xbox Viewer's model: Gremlin's Xbox pads through the output module, their pairing and state (`xbox_maps`). |
| `qml/DialogXboxViewer.qml` (107), `qml/XboxViewerCard.qml` (243), `qml/Xbox360Face.qml` (153) | Tools > Viewers > Xbox Viewer window, one pad card, the pad picture. |
| `qml/OptionProfileAutoLoading.qml` (276) | Options > Profiles > Auto-load (program list, profiles, Keep running). |
| `qml/MainFailure.qml` | Window shown when the first device scan fails. |
| `device_db.json` | Built-in input labels per VID/PID. |
| `test/fake_hardware.py` (125), `test/fake_input.py` (47) | Fake dill.dll and vJoy queries; fake keyboard/mouse so tests never touch the PC. |
| Tests | `test_device_scan.py`, `test_twin_devices.py`, `test_device_reconnect.py` (+ `device_reconnect_smoke.py`), `test_startup_messages.py`, `test_raw_input_listeners.py`, `test_keyboard_gate.py`, `test_hidhide_group.py`, `test_hidhide_log.py`, `test_dill.py`, `test_device_fixes.py`, `test_xbox_pads_told_apart.py`, `test_threads.py`, `test_bounded_waits.py`, `test_audit3_startup.py`, `test_audit_runtime.py`, `test_audit3_run_stop.py`, `test_mode_refresh_and_add_key.py`, `test_audit2_modes.py`, `test_audit3_modes.py`, viewers: `test_viewer_pair_label.py`, `test_vjoy_viewer_reads_output_module.py`, `test_xbox_viewer_driver_check.py`. |

## 3. What it owns

**In memory**

| Data | Where | Who writes | Who else may change it |
|---|---|---|---|
| Device list `_joystick_devices` (ordered: physical by name, then vJoy by id) | `device_initialization.py:18` | `_initialize_devices` only (start-up, hot-plug timer) | Nobody (read by about 20 UI models, runtime, HidHide) |
| Left-out vJoy ids `_left_out`, problems `_vjoy_problems`, `_told`, `_window_up` | `device_initialization.py:22-25` | scan, `announce_vjoy_problems` | Nobody |
| Twin names on `DeviceSummary.name` | scan (`_name_twins`) | scan | Nobody; `JoystickWrapper.name` still reads the driver name (see section 7) |
| Calibration functions `_calibrations[(dill GUID, axis)]` | `EventListener` | `_init_joysticks` (each scan), `reload_calibration` (Calibration page, `ui/device.py:1400`) | Calibration page |
| Stick state cache `Joystick.devices` (class attribute) | `input_cache.py:477` | DLL thread (`_joystick_event_handler`), `_let_go` | Logical Device lives in the same dict; nothing removes an unplugged stick |
| Key state cache `Keyboard._keyboard_state` | `input_cache.py:515` | keyboard hook thread | Nobody |
| Key tables `g_name_to_key`, `g_scan_code_to_key` | `keyboard.py` | module import; grown at run time by `key_from_name/key_from_code` (any thread) | Nobody |
| Hook callback lists `g_keyboard_callbacks`, `g_mouse_callbacks` | `windows_event_hook.py:22-23` | `register` (once, EventListener) | Never removed |
| Hot-plug timer `_device_update_timer` | `EventListener` | DLL thread, `terminate`, `shutdown_cleanup` (`joystick_gremlin.py:246-251`) | shutdown reaches into the private field |
| Callback table `EventHandler.callbacks[device][mode][event]`, `known_modes`, `process_callbacks` | `event_handler.py:564-568` | Run (`code_runner.start` via `add_callback`, `build_event_lookup`), Stop (`clear`), mode rename/delete (`mode_manager.py:250,264`), Pause action | Pause and Resume action plugin |
| Foreground program `_current_path`, `_current_pid` | `ProcessMonitor` | its thread | Nobody |
| HidHide model state (`_present`, `_devices`, `_games`, `_last_error`) and module-level `_ioctl_error`, `_settings_error` | `ui/hidhide.py` | `HidHideModel`, driver calls | Nobody |

**Files and settings** (all in `configuration.json`, written about 1 s after a change)

| Key | Meaning | Written by |
|---|---|---|
| `global/internal/twin-device-names` | device id -> "<name> (2)" | scan (`_name_twins`), from the timer thread on hot-plug |
| `global/general/device-change-behavior` | Reload (default) / Ignore / Disable | Options |
| `global/general/hidhide-on-start` | HidHide "Automatically Start" (also shown in Options as "Turn HidHide on at start") | HidHide window, Options |
| `display/hidhide/*`: `games`, `photos`, `module-links`, `list-mode`, `hidden-devices`, `cloak`, `managed`, `gaming-only`, `window-width/height`, `split-ratio` | HidHide choices and window | HidHide window; `apply_on_start` |
| `devices/display/aliases` | user display names for devices | `DeviceNames.setAlias` (Home device list, Button Map) |
| `profile/automation/enable-auto-loading`, `remain-active-on-focus-loss`, auto-load list | auto-load | Options > Profiles |
| `ui/general/display-mode` | input names: Numerical / Label / both (DeviceDatabase) | Options |
| `own-xbox-pads` (vigem) | ids of Gremlin's own Xbox pads | Xbox output |
| Module file `boundGuidLocal` | read by `_file_bound_guid` to pick which twin keeps the plain name | Module files page |

**Outside the program**: the HidHide driver's device list, program list, inverse (Allow/Block) flag and active flag are system-wide; Gremlin overwrites them all when it applies its saved list.

## 4. Entry points

| Trigger | Handler | Function(s) | Thread |
|---|---|---|---|
| Program start | `JoystickGremlinApp` | `_no_hooks_offscreen` -> `hidhide.apply_on_start` (skipped off-screen) -> `DILL.init` -> `joystick_devices_initialization`; on `GremlinError` load `MainFailure.qml` | main |
| Main window up | `joystick_gremlin.py:943` | `announce_vjoy_problems` -> `display_error` once | main |
| First `EventListener()` (Backend/CodeRunner) | `EventListener.__init__` | registers hooks, `_init_joysticks`, starts keyboard hook, starts "event listener" thread which sets the two DLL callbacks | main -> threads |
| Stick moved / pressed | DLL callback `_joystick_event_handler` | calibrate axis, update `Joystick` cache, emit `joystick_event(Event)` | DLL thread |
| Stick plugged in or out | DLL callback `_joystick_device_handler` | ignore own Xbox pads; restart 0.2 s timer -> `_run_device_list_update` -> scan, `_init_joysticks`, `_let_go` for gone sticks, emit `device_change_event` if the list changed | DLL thread -> timer thread |
| Key pressed / released anywhere in Windows | `process_keyboard_event` (hook) -> `_keyboard_handler` | drop AltGr's fake Ctrl, drop auto-repeat, update `Keyboard` cache, emit `keyboard_event` | keyboard hook thread |
| Mouse button / wheel (only while hook started) | `process_mouse_event` -> `_mouse_handler` | emit `mouse_event` | mouse hook thread |
| Run | `code_runner.start` | `EventHandler.add_callback` x N, `build_event_lookup`, connect `InputModuleRuntime.event/key_event` and `virtual_event` to `process_event`, `resume`, `refresh_axes` | main |
| Stop | `code_runner.stop` | disconnect, `gremlin_active=False`, `EventHandler.clear` | main |
| Event reaches profile | `EventHandler.process_event` | `_matching_callbacks` (filter when paused), each callback, `ButtonReleaseActions.process_release`; VJoyError pauses | main (queued) |
| Pause and Resume action | `pause_resume` plugin | `EventHandler.pause/resume/toggle_active` | main |
| Mode renamed / deleted | `mode_manager.py:250,264` | `rename_mode`, `drop_mode` | main |
| Change Mode to a mode not in the running profile | `ModeManager.switch_to` | `_known_modes()` reads `EventHandler.known_modes`; ignored, logged once | main |
| `device_change_event` | Backend `_device_change` | Reload: Stop + Run; Disable: Stop; Ignore: nothing | main (queued) |
| `device_change_event` (other listeners) | `UIState._device_change`, `InputModuleRuntime.reload`, `DeviceListModel`, `Device`, `DeviceAxisSeries`, `AxisCalibration`, `ModuleModel`, `module_inputs`, `module_pairing`, `module_calibration`, `output_modules`, `auto_map_modules`, `viewer_devices`, `xbox_viewer`, `live_input`, `ui/profile.py:1361`, `HidHideModel.reload` | each re-reads the device list | main |
| Profile Settings: tick "vJoy as input" | `ui/profile.py:1162` | emits `device_change_event` itself (no device changed) | main |
| Listen button (InputListener.qml) | `InputListenerModel.enabled = true` | `_connect_listeners` (keyboard always, joystick if asked, mouse hook start if asked); first input or Esc held 1 s ends it | main; Esc abort on timer thread |
| Macro editor Record | `MacroRecorder.start/stop` | connects raw signals, starts/stops mouse hook, records on main thread via `singleShot(0)` | main |
| Calibration page, axis graph | `AxisCalibration`, `DeviceAxisSeries` | raw `joystick_event`; `reload_calibration` after save | main |
| Module Setup "press a control" | `ui/module_model.py` | raw `joystick_event` (allowed) | main |
| Input highlighting | `Backend._highlight_input` | raw `joystick_event` -> `setInputIndex` | main |
| Macro `JoystickAction`, `refresh_axes`, OSC, Hat as Buttons | `macro.py:596`, `input_refresh.py`, `osc.py:455,507`, `hat_buttons` | emit `joystick_event` / `virtual_event` themselves (synthetic events into the raw feed) | various |
| Tools > Device Setup > HidHide | `DialogHardwareHide.qml` -> `HidHideModel` | `reload`, `setGremlinControl`, `setCloak`, `setInverse`, `setDeviceHidden`, `addGame`, `removeGame`, `setGamingOnly`, `setDevicePhoto`, `openGameControllers`, `openDownload`, window size | main |
| HidHide: Remove program | `removeGame` -> `confirmRemoveGame` (`DialogHardwareHide.qml:54`) -> `Confirm.ask` (red Remove Program) | `HidHideModel.removeGame` | main |
| HidHide: Add Program / device photo choosers | `FilePicker` ("other" / "picture") | `FolderMemory`; `addGame` / `setDevicePhoto` | main |
| Options "Turn HidHide on at start" | `ui/option.py:83` | same setting as "Automatically Start" | main |
| Foreground program changes | `ProcessMonitor._update` (1 s poll) | emit `process_changed(path)` -> `Backend._active_process_changed_cb` | monitor thread -> main |
| Options auto-load "Select Executable" | `ProcessListModel.refresh` | `list_current_processes` (WMI) | main |
| Tools > Device Setup > Device Information | `DeviceListModel` ("all") | `joystick_devices()` | main |
| Exit | `shutdown_cleanup` | cancel hot-plug timer, `listener.terminate` (hooks off, DLL callbacks to no-ops), mouse hook stop, `process_monitor.stop` | main |

## 5. Talks to

| Other subsystem | Direction | How |
|---|---|---|
| Input modules (`modules/runtime.py`, `gate.py`) | called by | `InputModuleRuntime` listens to `joystick_event`, `keyboard_event`, `device_change_event`; reads `physical_devices()` |
| Output modules (`modules/output.py`) | calls out | scan asks `vjoy_ids`, `vjoy_layout`, `vjoy_hats_continuous`, `reset_vjoy` (layer rule kept) |
| Xbox output (`vigem/ids.py`, `own_pads.py`) | calls out | `is_vigem_xbox_summary` to skip own pads; vigem in turn reads `DILL` directly |
| Module files (`modules/registry.py`, `calibration.py`, `util.modules_dir`) | calls out | `_file_bound_guid` reads a module file; `values_for_device` for calibration |
| Run lifecycle (`code_runner.py`, `macro.py`, `input_refresh.py`) | called by | `EventHandler` callbacks, `gremlin_active`, `refresh_axes`, `virtual_event` |
| Modes (`mode_manager.py`) | both | `Event.mode` stamped from `ModeManager.current`; `known_modes`, `rename_mode`, `drop_mode` |
| Settings (`config.py`) | calls out | twin names, HidHide choices, aliases, device-change behaviour |
| Profile (`shared_state.current_profile.settings.vjoy_as_input`) | reads | `input_devices`, `output_vjoy_devices` |
| Home / Configuration / Calibration / Module Setup / viewers / Auto Mapper / Device Library | called by | ~17 listeners on `device_change_event`; device getters |
| Live Log Reader Input Monitor (`input_monitor.py`) | calls out | `process_event` records every event when on |
| Errors (`signal.display_error`) | calls out | vJoy left out, hot-plug failure, VJoyError |
| Logical Device | shares | `Joystick` cache holds the Logical Device under `UUID_LogicalDevice` |
| OSC (parked) | called by | OSC emits on `joystick_event` with `OSC_DEVICE_UUID` |
| Auto-load (Backend) | called by | `process_changed` |
| Windows | calls out | DirectInput (dill.dll), SetWindowsHookEx, HidHide IOCTLs and SetupAPI/hid.dll (all in `hidhide_driver.py`), `keybd_event`, `joy.cpl`, WMI |

## 6. Threads and timers

| Thread / timer | Started by | Runs | Stops |
|---|---|---|---|
| dill.dll internal thread | `DILL.init` (native, not via `gremlin.threads`) | input and device-change callbacks into Python | never; callbacks swapped to no-ops at `terminate` |
| "event listener" | `threads.start` (`event_handler.py:267`) | sets the two DLL callbacks, then waits on `_stop_event` | `_ask_to_stop` / `terminate` |
| "device list update" timer, 0.2 s, restarted per device event | `threads.timer` (`event_handler.py:414`) | scan, settings write, module file read, `reset_vjoy`, let-go events, `device_change_event` | cancelled by a newer event, `terminate`, `shutdown_cleanup` |
| "keyboard hook" | `threads.start` (`windows_event_hook.py:317`), at listener creation | message loop; every key in Windows passes through Python | WM_QUIT, `stop()` waits up to 2 s |
| "mouse hook" | only while Listen or macro Record wants mouse | message loop | when the last user stops it (start/stop count, `windows_event_hook.py` 442-473; GL-120) |
| "process monitor" | `threads.start`, from `Backend.__init__` (always, even with auto-load off) | `GetForegroundWindow` every 1 s (`_stop.wait(1.0)`) | `stop()` joins 2 s |
| "input listening abort" timer, 1 s | `threads.main_timer` (`ui/util.py:236`) on Esc press, on the main thread (GL-037) | `_abort_listening` (disconnects signals, stops mouse hook, emits) | cancelled by `_listening_done` |
| Scan lock `_joystick_init_lock` | | waits at most `SCAN_WAIT_S` = 10 s, then raises | |
| Signals crossing threads | `joystick_event`, `keyboard_event`, `mouse_event`, `device_change_event` are emitted off the main thread; receivers are QObjects on the main thread, so Qt queues them | | |

## 7. Rule breaks

| # | Rule | Where | What | Status |
|---|---|---|---|---|
| RB1 | Thread rules: time via `gremlin.clock` | `windows_event_hook.py:288-289` | `_Hook.stop` loops on `time.monotonic()` | CONFIRMED |
| RB2 | Thread rules: time via `gremlin.clock` | `vigem/own_pads.py` (`before_plug`) | `time.monotonic()` for the own-pad window | CONFIRMED (Xbox page owns it) |
| RB3 | Layer rule (nothing reads hardware except the input side) | `vigem/ids.py:61`, `vigem/own_pads.py:79-80` | the driver package calls `dill.DILL` directly to recognise its own pads | CONFIRMED in code; whether this counts as a break is a question (Q11) |
| RB4 | Layer rule: UI never touches hardware directly | `ui/hidhide.py:631-1260` | HidHide IOCTLs, SetupAPI, hid.dll, CreateFileW on every HID device all live in a `gremlin/ui` module | CONFIRMED in code; HidHide is not on the input path, so Q10 |
| RB5 | Single owner of the device list | `device_initialization.py:270-272` | list cleared and refilled on the timer thread while the main and DLL threads iterate it (`joystick_devices()`); AU-64 still lists this | SUSPECTED (race not reproduced) |
| RB6 | Single owner of `device_change_event` | `ui/profile.py:1162` | Profile Settings emits "a device changed" when only the vJoy-as-input tick changed; Backend then Stops (Disable) or restarts (Reload) a Run | CONFIRMED |
| RB7 | Single owner of the mouse hook | `ui/util.py:113`, `ui/util.py:370` | Listen and macro Record each start and stop the one shared hook with no count; one stopping cuts the other off | CONFIRMED |
| RB8 | Single owner of the hot-plug timer | `joystick_gremlin.py:246-251` | `shutdown_cleanup` cancels `listener._device_update_timer` itself, then `terminate()` does it again | CONFIRMED (harmless duplicate) |
| RB9 | Duplicated logic: device names | `device_initialization.device_name`, `input_cache.JoystickWrapper.name` (`input_cache.py:304`), `ui/device_names.py` aliases, `DeviceListModel` ("name N" for vJoy) | four ways to name a device; the wrapper returns the driver's name, not the twin name | CONFIRMED |
| RB10 | Duplicated setting control | `ui/option.py:83` and `DialogHardwareHide.qml:185` | one setting, two switches (test-plan S-38) | CONFIRMED |
| RB11 | Thread rules: Qt objects from worker threads | `ui/util.py:122-125` via timer `ui/util.py:200` | Esc-abort disconnects signals and stops the mouse hook from the timer thread | CONFIRMED that it runs there; harm SUSPECTED |
| RB12 | Thread rules: settings written off the main thread | `device_initialization.py:90` (`_name_twins`), `vigem/own_pads._save` | `Configuration().set` from the hot-plug timer thread | SUSPECTED (depends on Configuration being thread-safe) |
| RB13 | Threads only via `gremlin.threads` | dill.dll callbacks | native thread outside the registry | CONFIRMED, accepted exception (N24 note: "event_handler's driver callbacks stay") |
| RB14 | Main thread blocking | `HidHideModel.reload` (`ui/hidhide.py:1451`) on every `device_change_event` | opens every HID device and makes several driver calls on the main thread | SUSPECTED slow, not measured |
| RB15 | Dead filter | `windows_event_hook.py:207` vs `event_handler.py:504` | mouse events are always built with `is_injected=False`, so "Ignore events we created via the macro system" never ignores anything | CONFIRMED |
| RB16 | Id type mix | `event_handler.py:508` | mouse events carry `dill.GUID_Keyboard` (a GUID object); keyboard events carry `dill.UUID_Keyboard` (a UUID) | CONFIRMED; harm SUSPECTED (no profile binds mouse inputs today) |

## 8. Behaviour spec

### A. Device list and scan

- **S1** It should list every controller Windows reports, physical ones first sorted by name, then vJoy devices sorted by vJoy number. [user confirmed 2026-10-06; was code only]
- **S2** It should never list Gremlin's own virtual Xbox pads as devices, but a real wired or wireless Xbox 360 pad should be a normal device. [tracker: DEV2] [test: test_xbox_pads_told_apart.py::test_real_xbox_pad_is_a_normal_device]
- **S3** It should show Home with one card per device: physical devices, each vJoy device, and the Xbox controller. [help: Home]
- **S4** It should scan devices once at start, before the main window loads; if that scan fails it should show the failure window instead of the main window. [user confirmed 2026-10-06; was code only]
- **S5** It should never wait more than 10 s for a device scan that is still busy; it should report it instead. [test: test_bounded_waits.py::test_a_busy_device_scan_is_reported_not_waited_for]
- **S6** It should always release the scan lock, so a failed scan never stops later hot-plug updates. [tracker: DEV4] [test-plan: DEVICE-SCAN-FIXES] [test: test_device_scan.py::test_a_scan_error_does_not_leave_the_lock_held]
- **S7** It should show a failed hot-plug update in the error dialog ("The device list could not be updated."), not lose it on a background thread. [test: test_device_scan.py::test_hot_plug_error_is_shown_not_lost]
- **S8** It should do nothing when a scan finds the same device ids as before (no vJoy reset, no reload). [test: test_device_scan.py::test_nothing_changed_resets_nothing]
- **S9** It should list in Device Information every device Windows reports: Name, Axes, Buttons, Hats, VID, PID, Joystick ID and Device ID, including left-out vJoy devices (marked "left out (see message)") and this program's own Xbox pads (marked "this program's Xbox pad"). [help: Device Information] [changed 2026-10-07 to follow decisions Q6, D-02-Q6-WORDING and Q12, which win over the earlier wording "Device GUID" and the Q6 note]
- **S10** It should label inputs from `device_db.json` by VID/PID when Options > Input names asks for labels, and fall back to "Axis 3" style names otherwise. [user confirmed 2026-10-06; was code only]

### B. Identical devices (twins)

- **S11** It should name the second of two identical devices "<name> (2)", a third "(3)", so each has its own module file, card, Button Map and calibration. [tracker: DEV8] [test-plan: TWIN-DEVICES] [test: test_twin_devices.py::test_the_second_identical_device_gets_its_own_name]
- **S12** It should give the plain name to the device the existing "<name>" module file is bound to. [test: test_twin_devices.py::test_the_device_the_file_is_bound_to_keeps_the_plain_name]
- **S13** It should keep each twin's name by device id, the same every session and port. [test-plan: TWIN-DEVICES]
- **S14** It should not rename a device that has no twin. [test: test_twin_devices.py::test_a_single_device_is_not_renamed]
- **S15** It should keep a stored twin name even when that device is later the only one plugged in (the "(2)" stick alone is still "(2)"). [user confirmed 2026-10-06; was code only]
- **S16** It should use a stored twin name only while the driver's name for that device id still matches the twin's base name; entries for names no longer used are dropped. [user confirmed 2026-10-06; was code only] [changed 2026-10-07 to follow decision Q3, which wins over the earlier wording "keep a stored twin name even if the driver later reports a different name"]
- **S17** It should use the shown (twin) name in labels and input pairing, not the driver's name. [test: test_twin_devices.py::test_labels_use_the_shown_name]
- **S18** Profiles should be unaffected by twin names (they use device ids). [test-plan: TWIN-DEVICES]

### C. vJoy devices at scan

- **S19** It should link each vJoy number to its DirectInput device by its count of axes, buttons and hats. [user confirmed 2026-10-06; was code only]
- **S20** It should leave out (and keep running without) a vJoy device that has discrete hats, one Windows doesn't list, or two set up alike; the rest should work. [user decision: start without a problem vJoy] [test-plan: STARTUP-MESSAGES] [test: test_startup_messages.py::test_vjoy_devices_alike_are_both_left_out]
- **S21** It should say once, after the main window is up, which vJoy devices were left out, why, and how to fix each; again only when that changes (e.g. on a hot-plug). [test-plan: STARTUP-MESSAGES]
- **S22** It should log each left-out vJoy as an error, also with Diagnostic logs Off. [test-plan: STARTUP-MESSAGES]
- **S23** It should release the vJoy devices it is not using only at start and when the set of vJoy devices changed, never because a stick was plugged in mid-play. [tracker: DEV5 via DEVICE-SCAN-FIXES] [test: test_device_scan.py::test_plugging_in_a_stick_does_not_reset_vjoy]
- **S24** It should ask vJoy about its devices only through the output module. [tracker: N24] [test-plan: N24-LAYER-RULE]

### D. Plug, unplug, reconnect

- **S25** It should wait 0.2 s after the last plug/unplug event and then rescan once, so several devices arriving together cause one update. [user confirmed 2026-10-06; was code only]
- **S26** It should ignore plug events from Gremlin's own Xbox pads (re-scanning on them unplugged the pad again and made Steam flap). [user confirmed 2026-10-06; was code only] [tracker: DEV2]
- **S27** It should tell the rest of the program "devices changed" only when the visible list actually changed. [user confirmed 2026-10-06; was code only]
- **S28** It should let go of every button held and centre every hat of a stick that is unplugged, as the stick's own events would; axes stay where they were (a throttle has no rest) in what the stick reports, but every action that reads an unplugged stick's axis reads it centred (05 S105). [user decision 2026-10-07: D-05-UNPLUG-CENTRE] [user decision: agreed 'release held inputs'] [tracker: R3] [test: test_device_reconnect.py::test_held_inputs_are_let_go_on_unplug]
- **S29** On a reconnect it should load what every screen shows for that stick (Input Configuration list, axis graph, live values, claimed inputs, Module Setup, Calibration). [user decision: agreed with the user] [test: test_device_reconnect.py::test_screens_set_while_unplugged_read_the_stick_when_it_connects]
- **S30** It should refuse Module Setup Save while its stick is unplugged and keep the work on screen. [tracker: DEV10] [test: test_device_reconnect.py::test_unplugging_keeps_what_is_shown_and_refuses_save]
- **S31** It should give a stick plugged in during a Run its input module claims, also with Device change behavior set to Ignore. [tracker: DEV11] [test: test_device_fixes.py::test_input_modules_reload_when_a_device_is_plugged_in]
- **S32** While a profile runs, it should follow Options > Device change behavior when a controller is plugged in or removed: Reload (default) stops and runs again, Ignore does nothing, Stop stops (shown as "Stop"; the stored value stays "Disable"). [help: Run and status] [help: Options] [changed 2026-10-07 to follow decision Q2, which wins over the earlier wording "Disable"]
- **S33** When the selected physical device disappears it should move the page to the first physical device, or to the Logical tab when none is left. [user confirmed 2026-10-06; was code only] (`UIState._device_change`)
- **S34** HidHide's device list should re-read itself on a device change. [test: test_device_reconnect.py::test_hidhide_rereads_its_list]
- **S35** Auto Mapper should keep its ticks when the device list is rebuilt. [test: test_device_reconnect.py::test_auto_mapper_keeps_its_ticks]
- **S36** A failed device update during play should not be the only thing that breaks: the error is shown and the old list stays. [user confirmed 2026-10-06; was code only]

### E. Stick events, calibration, cached state

- **S37** It should apply each axis's calibration before any action sees it. [help: Calibration]
- **S38** It should use a default centred calibration for an axis with no calibration data and log that once per axis at Info level. [tracker: F9] [user confirmed 2026-10-06; was code only for the once-per-axis part]
- **S39** It should reload calibration for every stick on each scan, and for one axis right after Calibration saves it. [user confirmed 2026-10-06; was code only]
- **S40** Each hardware event should run in the mode that is current when the main thread handles it (the listener leaves the mode unset; the event handler stamps it). [user confirmed 2026-10-06; was code only] [changed 2026-10-07 to follow decision D-02-S40-HANDLED, which wins over Q8 and the earlier wording "when the hardware event arrives"]
- **S41** It should keep the last value of every stick input so scripts, conditions and "refresh axes" can read it. [user confirmed 2026-10-06; was code only]
- **S42** On Run (and on mode change, when that option is on) it should re-send every input device's current axis values. An axis that has not moved since the program started is sent as centre (the joystick library reports a position only after a move); this is documented in help, not worked around. [user decision 2026-10-07: D-02-AXIS-START] [help: Options (refresh axes on activation and mode change)] [test: test_mode_refresh_and_add_key.py::test_runner_refreshes_axes_on_mode_change_only_while_listening]
- **S43** An unclaimed input should read neutral to actions and scripts. [test: test_input_state_claims.py::test_unclaimed_inputs_read_neutral]
- **S44** Only the input module runtime, Module Setup, Calibration/axis graph, input highlighting, Listen and macro recording may listen to raw stick and key events; viewers and live values use the claimed feed. [user decision: P3 'highlighting and Listen stay as they are'] [test: test_raw_input_listeners.py::test_raw_hardware_listeners_are_only_the_allowed_ones]

### F. Keyboard

- **S45** It should see every key press and release in Windows without blocking or changing what Windows and games get. [help: Input modules ("Typing in Windows and games is never affected")]
- **S46** It should report one press per key hold (no auto-repeat), and the release. [user confirmed 2026-10-06; was code only]
- **S47** It should treat AltGr as Right Alt, not Right Alt plus Ctrl. [user confirmed 2026-10-06; was code only]
- **S48** Key bindings should fire only for keys the Keyboard input module claims; with no saved keyboard choice every key is claimed; saved with no keys, none pass. [help: Input modules] [tracker: AU-23] [test: test_keyboard_gate.py::test_no_saved_keyboard_claim_passes_every_key] [test: test_audit_devices.py::test_keyboard_saved_with_no_keys_passes_none]
- **S49** It should tell an extended key (Right Ctrl, arrows, Numpad Enter) from its plain twin. [test: test_keyboard_gate.py::test_key_id_packs_the_extended_flag]
- **S50** Keys the program itself sends (Map to Keyboard, macros) should be ignored by the hook while a Run is on (bindings and macro recording); outside a Run they come through like real keys. [user confirmed 2026-10-06; was code only] [changed 2026-10-07 to follow decision Q4, which wins over the earlier wording "come back through the hook as key events like real ones"]

### G. Mouse

- **S51** It should hook the mouse only while Listen or macro Record asks for mouse input, and unhook afterwards. [user confirmed 2026-10-06; was code only]
- **S52** It should report left, right, middle, back and forward buttons with press and release, and wheel up/down as a single press. [user confirmed 2026-10-06; was code only]
- **S53** Mouse buttons are not inputs a profile can bind (no mouse events reach a running profile). [user confirmed 2026-10-06; was code only] (Q5)

### H. Routing to the profile (EventHandler)

- **S54** It should run every action registered for an input in the current mode, and a child mode should use its parent's actions for inputs it leaves empty. [glossary: Mode] [user confirmed 2026-10-06; was code only for the copy at Run]
- **S55** One failing action should not stop the others or the release handling. [test: test_audit_runtime.py::test_one_failing_action_does_not_stop_the_others]
- **S56** A vJoy error during an action should be logged like any other action failure; it shows no error box and does not pause the profile, and the other actions still run. [changed 2026-10-06 to follow decision 06 Q10 (auto-pause removed), which wins over the earlier wording]
- **S57** While paused, only actions marked "always execute" (Pause and Resume) should run; a script callback should not stop the rest. [test: test_action_fixes.py::test_while_paused_a_script_callback_does_not_stop_the_rest] [test: test_pause_resume.py::test_pause_resume]
- **S58** A Change Mode to a mode the running profile does not have should be ignored and logged once. [test: test_audit2_modes.py::test_the_running_mode_list_follows]
- **S59** Renaming a mode while running should move its actions to the new name; deleting a mode should drop its actions. [tracker: AU-99 group] [user confirmed 2026-10-06; was code only for the running case]
- **S60** Stop should remove every registered action and the running mode list. [user confirmed 2026-10-06; was code only]

### I. Listen for input

- **S61** Listen should end at the first press (single input), or at the first release after one or more presses (several inputs). [user confirmed 2026-10-06; was code only]
- **S62** An axis should count only after a big enough move; a hat only when pushed off centre; the mouse wheel at once. [user confirmed 2026-10-06; was code only]
- **S63** Listen should ignore events from the Logical Device and virtual buttons. [user confirmed 2026-10-06; was code only]
- **S64** Holding Esc for 1 s should cancel Listen and return nothing, in every case; a short Esc tap does not cancel. [user confirmed 2026-10-06; was code only] [changed 2026-10-07 to follow decision Q9, which wins over the earlier short-tap note]
- **S65** Input highlighting should pause while Listen runs and while a macro records. [user confirmed 2026-10-06; was code only]

### J. HidHide

- **S66** HidHide should hide physical controllers from games so they only see vJoy or Xbox; Gremlin-Platforms always sees them. [help: HidHide]
- **S67** It should not ship or install the HidHide driver; "Get HidHide" opens the Nefarius releases page; without the driver it says "HidHide is not installed". [help: HidHide] [user confirmed 2026-10-06; was code only for the text]
- **S68** It should change nothing in HidHide until "Gremlin-Platforms controls HidHide" is on; until then the settings show but can't be changed, with a note saying why. [help: HidHide] [tracker: C16] [glossary: program's name]
- **S69** Turning that control off should leave HidHide as it is (devices may stay hidden). [user decision: DEV12 wont-fix]
- **S70** "HidHide Enabled" should turn hiding on or off; if the driver refuses, the switch flips back and the error shows. [tracker: B18]
- **S71** "Automatically Start" should, at each start, turn on Gremlin control and HidHide Enabled and write the saved lists. [help: HidHide]
- **S72** Every switch should be off on a new install; a new install hides nothing. [help: HidHide] [user confirmed 2026-10-06; was code only for "hides nothing"]
- **S73** Ticking a device should hide every interface of that physical device (grouped by USB parent, not by vendor). [test: test_hidhide_group.py::test_nxt_interfaces_share_usb_parent_group] [test: test_hidhide_group.py::test_no_parent_does_not_merge_whole_vendor]
- **S74** A hidden device should be dimmed and marked HIDDEN. [help: HidHide]
- **S75** "Gaming devices only" should shorten the list to game controllers. [help: HidHide]
- **S76** Allow list: only listed programs (and Gremlin-Platforms itself) see hidden devices; Block list: listed programs don't (Gremlin-Platforms is never blocked). [help: HidHide] [user confirmed 2026-10-06; was code only for the Gremlin part]
- **S77** "Test HidHide" should open Windows Game Controllers. [help: HidHide]
- **S78** A setting that can't be saved should be shown in the window. [tracker: N12]
- **S79** HidHide messages should go to the system log; a missing driver at start is a warning. [test: test_hidhide_log.py::test_missing_driver_at_start_is_a_warning]
- **S80** An off-screen run should never change HidHide. [tracker: AU-114] [test: test_audit3_startup.py::test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray]
- **S81** Saved programs should load sorted by name; devices sorted by name then id. [test: test_hidhide_group.py::test_saved_programs_load_sorted]
- **S82** A device picture is used where it was picked (not copied); if moved or deleted the card shows no picture until another is picked. [user confirmed 2026-10-06; was code only] [tracker: B19]
- **S83** HidHide choices are program settings (saved ~1 s after a change) and appear in History, but window size, split and automatic picture links do not. [help: What is saved where] [tracker: AU-54]

### K. Foreground program and auto-load

- **S84** With "Load profiles automatically" on, it should load and run the profile chosen for a program when that program gets focus. [help: Profiles] [help: Options]
- **S85** It should read program paths with non-ASCII characters in full. [tracker: AU-37] [test: test_audit_runtime.py::test_the_program_path_is_read_in_full]
- **S86** A program it can't read (run as administrator) should not be announced as if it were the previous one. [tracker: AU-37] [user confirmed 2026-10-06; was code only]
- **S87** It should not reload the open profile when its own program gets focus again. [tracker: AU-38] [test: test_audit_saving.py::test_auto_load_leaves_the_open_profile_alone]
- **S88** It should never switch over unsaved edits; it says so once per profile. [tracker: A11] [test: test_autoload_and_mode_prompts.py::test_auto_load_waits_for_unsaved_edits]
- **S89** If the chosen profile file is missing it should say so once and stop the open one (unless Keep running is on). [tracker: AU-95] [test: test_audit2_saving.py::test_a_missing_auto_load_profile_stops_the_open_one]
- **S90** When a program with no profile gets focus, it should stop the Run unless "Keep running when the program loses focus" is on. [help: Options] [user confirmed 2026-10-06; was code only for the exact rule]

### L. Safety, start and exit

- **S91** Tests and off-screen runs should never install a keyboard or mouse hook on the PC. [tracker: H4] [tracker: AU-114] [test: test_bounded_waits.py::test_with_hooks_turned_off_none_is_installed]
- **S92** A hook stopped right after starting should not hang. [test: test_threads.py::test_a_hook_stopped_right_after_starting_does_not_hang]
- **S93** On exit it should stop the hooks, the hot-plug timer, the DLL callbacks and the process monitor, within bounded waits. [user confirmed 2026-10-06; was code only]
- **S94** "Device ID" is the word on screen for the device's GUID (Device Information included). [glossary: Internal words] [changed 2026-10-07 to follow decision Q12 (Device Information shows "Device ID")]

## 9. Questions for the user

- **Q1** Profile Settings' "vJoy as input" tick sends the "device changed" signal. With Device change behavior = Reload (the default) a tick while running restarts the Run; with Disable it stops it. Should ticking it restart the Run? *Recommend:* no. Give the vJoy-as-input change its own signal that refreshes device lists and input claims but never stops or restarts a Run.
- **Q2** Device change behavior "Disable" means Stop. Should the option read Reload / Ignore / Stop to match the glossary (Run / Stop)? *Recommend:* rename to "Stop" on screen; keep the stored value.
- **Q3** A stored twin name ("T.16000M (2)") wins even if the driver later reports a different name for that device id (e.g. after a firmware change), and stored names are never removed. Keep? *Recommend:* use the stored name only while the driver's name still matches the base name; drop entries for names no longer used.
- **Q4** Keys the program sends itself (Map to Keyboard, macros) come back through the keyboard hook like real presses (the filter is commented out at `event_handler.py:467-469`). So a key sent by one binding can fire another binding, and macro Record or Listen can capture the program's own keys. Should the program's own keys be ignored? *Recommend:* ignore injected keys while a Run is active (bindings and recording), keep them visible to Listen only if you want chained bindings; decide once.
- **Q5** Mouse buttons can be recorded in macros and listened for, but no running profile receives mouse events (the hook is not started at Run and `mouse_event` is not connected). Is that intended? *Recommend:* yes, keep mouse as macro/Listen only and say so in Help; remove the dead "injected" mouse filter.
- **Q6** Device Information says "every device Windows reports", but it leaves out left-out vJoy devices and Gremlin's own Xbox pads. *Recommend:* list them too, marked "left out (see message)" / "Gremlin's Xbox pad", since this window is used to tell devices apart.
- **Q7** "Refresh axes" at Run sends the cached axis values. Until a stick's axis has moved since the program started, its cached value is 0 (centre), so a throttle at 80% is sent as centre at the first Run (FIXME at `input_cache.py:241-243`). *Recommend:* read the real position from the driver for any axis not yet seen (through the input side), then cache it. Needs a hands-on check first: confirm dill.dll does not already send starting values. **Answered 2026-10-07 (D-02-AXIS-START):** the hands-on check confirmed dill.dll sends no starting values; the user chose to document the behaviour in help and add no start-of-Run read.
- **Q8** [superseded 2026-10-07 by D-02-S40-HANDLED: the mode current when the main thread handles the event] Each event is stamped with the mode current when the hardware event arrives, not when it is processed. A press arriving just before a mode change runs in the old mode. *Recommend:* keep (it matches what the user pressed); write it down as intended.
- **Q9** Listen: a short Esc tap cancels listening after 1 s when keys are not being listened for, but must be held 1 s otherwise. *Recommend:* cancel only on a 1 s hold in both cases; Help names it.
- **Q10** HidHide's driver calls and HID enumeration live in a UI file (`gremlin/ui/hidhide.py`, 1800 lines). It is not on the input path, so the layer rule may not apply. *Recommend:* treat HidHide as a driver of its own: move the driver client and enumeration to a non-UI module and keep `HidHideModel` as the screen; low priority.
- **Q11** The Xbox driver package reads `dill.DILL` directly to recognise its own pads. Allowed? *Recommend:* allowed only through `gremlin/modules/hardware.py` (one door to the device driver), so the guard can check it.
- **Q12** Device Information shows "Device GUID"; the glossary says "device id". *Recommend:* "Device ID".
- **Q13** When Gremlin applies its HidHide lists (Automatically Start, or any change), it overwrites HidHide's whole program list and device list, removing anything added with HidHide's own Configuration Client. *Recommend:* keep (Gremlin is in control once the user turns control on), but say so under "Gremlin-Platforms controls HidHide".
- **Q14** Ticking a device in HidHide saves the choice even when the driver refuses it, so the saved list and the driver differ until the next apply (the HidHide Enabled switch saves only on success). *Recommend:* save only after the driver accepts, like HidHide Enabled.
- **Q15** In Allow list mode the program adds its own exe. Run from source that exe is `python.exe`, so every Python program sees hidden devices. *Recommend:* accept for source runs; mention in the developer notes only.
- **Q16** "Turn HidHide on at start" (Options) and "Automatically Start" (HidHide window) are the same setting with two switches (test-plan S-38). *Recommend:* keep only the HidHide window's switch and point to it from Options.
- **Q17** The vJoy message ends "Then restart Gremlin-Platforms."; the glossary says "the program" in sentences. *Recommend:* "Then restart the program."
- **Q18** With auto-load on and Keep running off, clicking into Gremlin-Platforms' own window (no profile chosen for it) stops the Run. *Recommend:* treat the program's own window as "no change".
- **Q19** The process monitor polls once a second even when auto-load is off. *Recommend:* start it only while auto-load is on.

## 10. Known gaps

**Code differs from the spec or a rule** (the 6 Oct list; catch-up batches 1-3 fixed all but G6 and G13, see Status)

| # | Gap | Where | Status (9 Oct, claude/gap-list.md) |
|---|---|---|---|
| G1 | "vJoy as input" tick fakes a device change; can stop or restart a Run (RB6, Q1) | `ui/profile.py:1162` -> `ui/backend.py:305-315` | done GL-119 |
| G2 | Device list cleared and refilled while other threads read it (AU-64, RB5) | `device_initialization.py:270-272` | done GL-035 |
| G3 | Mouse hook has no owner count: Listen stopping it cuts off a macro recording of mouse and the other way round (RB7) | `ui/util.py:113`, `ui/util.py:370` | done GL-120 |
| G4 | Mouse "injected" filter is dead (RB15); mouse events carry a GUID object instead of the keyboard UUID (RB16) | `windows_event_hook.py:207`, `event_handler.py:504-508` | done GL-239 |
| G5 | Program's own keys come back as input (Q4) | `event_handler.py:467-469` | done GL-121 |
| G6 | Refresh axes sends 0 for axes not moved since start (Q7) | `input_cache.py:237-244`, `input_refresh.py:26-35` | won't fix GL-122 (D-02-AXIS-START) |
| G7 | `Joystick.devices` never drops an unplugged stick; a stick that comes back with a different layout (same id) keeps the old wrapper, and an event for an input it doesn't know raises inside the DLL callback and is lost without a log line | `input_cache.py:477-507`, `event_handler.py:321,336,351` | done GL-123 |
| G8 | `JoystickWrapper.name` returns the driver's name, not the twin name (RB9) | `input_cache.py:298-304` | done GL-124 |
| G9 | Four separate naming paths (driver, twin, aliases, vJoy "name N") (RB9) | see RB9 | done GL-124 |
| G10 | `DeviceDatabase` returns early without `_device_db` when `device_db.json` is missing, so any later lookup raises AttributeError; it also opens the file without closing it | `input_cache.py:116-122` | done GL-036 |
| G11 | Device Information leaves out left-out vJoy devices and own Xbox pads (Q6) | `ui/device.py:262-272` | done GL-136 |
| G12 | HidHide device tick is saved even when the driver refuses (Q14) | `ui/hidhide.py:1668-1673` | done GL-133 |
| G13 | HidHide full list scan and driver calls on the main thread at every device change (RB14) | `ui/hidhide.py:1449-1485` | checked GL-134: no change needed; hands-on timing check left |
| G14 | Esc-abort of Listen runs Qt disconnects and a 2 s mouse-hook wait on a timer thread (RB11) | `ui/util.py:200-202`, `122-125` | done GL-037 |
| G15 | `time.monotonic` instead of `gremlin.clock` (RB1, RB2) | `windows_event_hook.py:288`, `vigem/own_pads.py` | done GL-265 |
| G16 | Twin names written to settings from the hot-plug timer thread (RB12) | `device_initialization.py:90` | done GL-045 |
| G17 | A key release lost by Windows (e.g. Ctrl+Alt+Del, a hook timeout) leaves the key "pressed" in the cache, so its next press is treated as a repeat and dropped once | `event_handler.py:473-477` | done GL-125 |
| G18 | The keyboard hook runs Python for every key in Windows the whole time the program is open; if the main thread holds Python too long, Windows silently removes a slow low-level hook and nothing notices or reinstalls it | `windows_event_hook.py:133-167`, `305-322` | done GL-126 |
| G19 | An exception in a hook callback skips `CallNextHookEx` for that key (other programs' hooks miss it) | `windows_event_hook.py:161-167` | done GL-127 |
| G20 | Numpad Enter is sent with `VK_SEPARATOR`, not `VK_RETURN` with the extended flag | `keyboard.py:359` | done GL-128 |
| G21 | `ProcessMonitor` starts before `process_changed` is connected; the first foreground program can be missed | `ui/backend.py:253` vs `262` | done GL-129 |
| G22 | Listen does not ignore vJoy or Xbox echo events (only Logical/virtual), so while a profile runs it may catch the output of the press instead of the stick | `ui/util.py:158-166` | done GL-131 |
| G23 | Two switches for one HidHide setting (Q16) | `ui/option.py:83`, `DialogHardwareHide.qml:185` | done GL-135 |
| G24 | Glossary: "Device GUID" in Device Information, "restart Gremlin-Platforms" in a sentence (Q12, Q17) | `DialogDeviceInformation.qml`, `device_initialization.py:309` | done GL-206, GL-209 |

**Open tracker items for this subsystem**

- AU-64: the device-list race (G2) is fixed (GL-035: the new list is built aside and swapped in one step).
- AU-58 (in progress): card menus offering things that don't apply; only OSC empty-state text left (OSC parked).
- DEV12 (wont-fix): HidHide may leave devices hidden after control is turned off or the program is uninstalled; user decision, kept as S69.
- APP5, APP13 (open): OSC listener port; OSC is parked, mapped only.

**Things nothing owns**

- (owned now) The mouse hook has a start/stop count (GL-120); only the scan emits `device_change_event` (GL-119); one shown name per device (GL-124, `device_aliases.py`); a device with no module file that isn't plugged in is forgotten (GL-243, D-02-GL243-FORGET), and Remove from Library forgets its settings (`gremlin/device_forget.py`, page 10).
- Stale entries: HidHide photo links of devices never seen again are still kept.
- Synthetic events: macros, OSC, refresh axes and Hat as Buttons all emit on the raw `joystick_event`/`virtual_event`; nothing marks them as synthetic.

## 11. Size and test coverage

**Size** (9 Oct): about 9,000 lines of Python and QML in the files above (largest: `ui/hidhide.py` 1,015 and `hidhide_driver.py` 980, once one 1,808-line file; `event_handler.py` 825; `input_cache.py` 581; `device_initialization.py` 570; `DialogHardwareHide.qml` 563; the viewers about 1,600), plus the native `dill.dll`.

**Covered by tests** (37 pass in the files run for this map: `test_device_scan`, `test_twin_devices`, `test_raw_input_listeners`, `test_hidhide_group`, `test_hidhide_log`, `test_keyboard_gate`, `test_dill`, `test_startup_messages`):

- Scan lock, no-change scan, vJoy reset only on vJoy change, hot-plug error shown: `test_device_scan.py`.
- Twin naming, bound file keeps plain name, separate cards and calibration: `test_twin_devices.py`.
- vJoy left out: `test_startup_messages.py`.
- Reconnect, let-go on unplug, Module Setup refuses Save, HidHide re-read, Auto Mapper ticks: `test_device_reconnect.py` (an off-screen program run with a fake stick).
- Plug-in during Run reloads claims: `test_device_fixes.py`.
- Own Xbox pads told apart: `test_xbox_pads_told_apart.py`.
- Raw-listener guard: `test_raw_input_listeners.py`. Layer guard for modules: `test_modules_layer.py`.
- Keyboard claim gate: `test_keyboard_gate.py`, `test_audit_devices.py`.
- Hooks off in tests and off-screen; hook stop does not hang: `test_bounded_waits.py`, `test_threads.py`, `test_audit3_startup.py`.
- Process path read: `test_audit_runtime.py::test_the_program_path_is_read_in_full`. Auto-load: `test_audit_saving.py`, `test_audit2_saving.py`, `test_autoload_and_mode_prompts.py`.
- Modes known/renamed: `test_audit2_modes.py`, `test_modes.py`, `test_audit3_modes.py`.
- Catch-up batch 2 fixes (hook keeps passing keys on, hook put back, own keys marked and ignored, lost release, Numpad Enter, missing `device_db.json`, Esc-hold Listen on the main thread, mouse hook count, Listen ignores vJoy/own pads, stick back with more buttons, unknown input logged, shown name in the cache): `test_batch2_b2a_input_events.py` (21), `test_batch2_b2b.py`, `test_batch2_b4.py`, `test_stage1_app_profile.py`.
- Viewers: `test_viewer_pair_label.py`, `test_vjoy_viewer_reads_output_module.py`, `test_xbox_viewer_driver_check.py`. Highlight holders (Listen, Record): `test_handson_T36_highlight_holders.py`.
- HidHide window shared pieces (Remove program question, SectionHeading, EmptyState, choosers): `test_tools2_shared_pieces.py`; it fits: `test_pages_fit.py`.

**Obvious untested paths**

- `windows_event_hook.process_mouse_event`, AltGr and the repeat filter of `process_keyboard_event` (the batch 2 tests drive the injected mark, the failing callback and the put-back; GL-009 is still open for the rest).
- `keyboard.key_from_code`, key table correctness (Right Shift twins); Numpad Enter is now tested.
- `EventListener._joystick_event_handler` and `_apply_calibration` on real DLL data; `JoystickWrapper` bounds; an event for an unknown device.
- `InputListenerModel`: several inputs, mouse wheel (Esc hold/tap and the vJoy/own-pad filter are now tested).
- HidHide: `apply_saved_list`, `apply_on_start` with the driver present, `setDeviceHidden` failure path, whitelist building, Allow/Block switch. All need the real driver (test-plan section 13 is [U]).
- `ProcessMonitor._update` loop and signal timing (G21); WMI `list_current_processes`.
- `DeviceDatabase` with a damaged `device_db.json` (missing is tested).
- `EventHandler.build_event_lookup` (parent-mode copy) directly; covered only through action tests.
- Device-list race under hot-plug (G2 fixed by swapping the list in one step).
- Real twin sticks and real DirectInput: only the fake driver is tested (test-plan TWIN-DEVICES says so).

## 12. Review (user, 2026-10-06)

Approved by the user as recommended (2026-10-06, blanket approval of the remaining pages): every [code only] statement in section 8 is confirmed, except where a question's recommendation changes it; every question in section 9 is decided as its **Recommend** says. Where a recommendation and a section 8 statement disagree, the recommendation wins.

| Q | Decision |
|---|---|
| All | As recommended in section 9 |
| Q8 | Superseded 2026-10-07 (D-02-S40-HANDLED): an event runs in the mode current when the main thread handles it |
| Q6 | Wording 2026-10-07 (D-02-Q6-WORDING): "this program's Xbox pad" |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.
