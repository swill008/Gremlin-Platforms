# App shell and settings

Mapped read-only against the code at 4f6bdfa4 (6 Oct). Line numbers drift: re-check them before a step starts.

## 1. Purpose

This is the frame around everything else. It starts the program (and stops a second copy), keeps the program settings (`configuration.json`) and shows them in Options. It also draws the main window's menus, toolbar, Mode box and status bar, and quits cleanly, with the tray, updates, logs, crash and freeze records, the Live Log Reader and the User Guide.

## 2. Files

Python
- `joystick_gremlin.py` (1138 lines): start-up (`main`, `JoystickGremlinApp`), the Windows-scaling check before Qt loads, second-copy check and `gremlin.lock`, the "could not start" box, `running_offscreen()`, registration of about 60 settings (`register_config_options`), loggers, `--profile/--enable/--start-minimized`, `shutdown_cleanup`, restart and install-on-exit.
- `gremlin/config.py` (551): `Configuration` singleton: loads, checks, saves `configuration.json`, handles a damaged file, settings version, removes unused settings, History records for settings, and auto-load profile lookup (`get_profile`, `get_profile_with_regex`).
- `gremlin/deferred_write.py` (121): "write once, a second after the last change" for settings and the activity log; flushes on quit and atexit.
- `gremlin/threads.py` (160): the only way to start threads and timers. Each one is named and listed, and has a stop request. `shutdown()` stops them all, and `main_timer` runs a timer's function on the main thread.
- `gremlin/clock.py` (24): `now()` / `sleep()` for timed loops, so tests can step time.
- `gremlin/qt_log.py` (153): Qt's own messages and stderr go to `logs/qt.log` through a pipe and a copy thread.
- `gremlin/error_report.py` (76): thread errors go to system.log, top-level errors are passed on to a console, and a hard crash writes `crash.log`.
- `gremlin/watchdog.py` (117): Log When Not Responding (main-loop tick every 250 ms, a watch thread, 5 s limit).
- `gremlin/updater.py` (165): release parsing, version compare, install kind, SHA-256 check, setup arguments, feed URL rules.
- `gremlin/ui/update_model.py` (449): `UpdateModel` (`updater` in QML): check, download, verify, install on exit, failed-update note.
- `gremlin/util.py` (folder part, lines 813-1003 and 1155-1210): `userprofile_path`, `data_folder`, the `*_dir()` helpers, `ensure_data_folders`, `program_folder`, `resource_path`, `restart_command`, version helpers.
- `gremlin/ui/option.py` (856): Options models (`ConfigSectionModel`, `ConfigGroupModel`, `ConfigEntryModel`), the Options layout `_LAYOUT`, titles (`entry_title`), `MetaConfigOption` registry for custom option widgets, the Add Action Menu list, auto-load list and TTS voice models.
- `gremlin/ui/log_option.py` (132): Diagnostic logs level (`apply_log_level`, `LogLevelModel`, the shared notifier).
- `gremlin/ui/ui_scale_option.py` (108), `gremlin/ui/windows_scale_option.py` (68): UI scale and "Ignore Windows display scaling".
- `gremlin/ui/shell_option.py` (89): Home card options and the Auto Mapper's remembered checkbox (registered when the module loads).
- `gremlin/ui/live_debug.py` (916): activity log `logs.txt` (`trace`), the Live Log Reader models `LiveLog` (Config tab), `DebugLog` (Debug tab) and `InputMonitor`.
- `gremlin/log_feed.py` (165), `gremlin/log_once.py` (36): the Live feed handler and "log once per run".
- `gremlin/ui/debug_mode.py` (153): red debug mode frame on every window.
- `gremlin/ui/system_tray.py` (332): Win32 tray icon, its menu, minimize/close to tray, the one-time balloon.
- `gremlin/ui/tray_memory.py` (77): unload pages and trim memory while hidden in the tray.
- `gremlin/ui/window_placement.py` (519): window and tool window size/place memory (`WindowPlacement`, `ToolWindowMemory`).
- `gremlin/signal.py` (58): the program-wide signals the shell listens to (`configChanged`, `showError`, `showNotification`, `uiScaleChanged`).

QML / JS
- `qml/Main.qml` (1898): main window: title, toolbar, Mode box, footer, menu bar, shortcuts, palette, dialogs (error, notice, save-before-continue, Save As, Open), quit chain (`quitGremlin`, `guardUnsavedChanges`, `deactivateThenQuit`, `onClosing`), tray hooks `enterTray/leaveTray`, page loaders.
- `qml/main_commands.js` (119): the main window's command list (id, text, group, shortcut, keywords, enabled, run).
- `theme/Gremlin/Menus/commands.js` (235), `theme/Gremlin/Menus/CommandPalette.qml` (174): the shared command registry, `trigger`, search, palette.
- `qml/helpers.js` (167), `qml/window_registry.js` (7): one open-window list for the whole program (`createComponent`, `toggleComponent`, `windowOf`).
- `qml/DialogOptions.qml` (143), `ConfigSection.qml` (101), `ConfigSectionButton.qml` (55), `ConfigGroup.qml` (348), `OptionEntryCard.qml` (74), and the `Option*.qml` custom rows (log level, UI scale, Windows scaling, auto-load, Add Action Menu, TTS voice, highlight speed, status cards).
- `qml/DialogUpdate.qml` (154), `qml/DialogHelp.qml` (160), `qml/DialogAbout.qml` (57), `qml/DialogLiveLog.qml` (690), `qml/MainFailure.qml` (55), `qml/EscapeCloses.qml`, `qml/ToolWindowMemory.qml`, `qml/DebugFrame.qml`.
- `qml/help_topics.js` (509): User Guide topics (`topics()`), and the Button Map's own guide (`buttonMapTopics()`).

Tests (unit unless noted)
- Start-up: `test_could_not_start.py`, `test_second_copy_detection.py`, `test_audit3_startup.py`, `test_audit2_startup_devices.py`, `test_program_imports.py`, `test_modules_import_alone.py`, `test_startup_messages.py`, `test_startup_settings_kept.py`, `test_restart_command.py`, `test_user_data_folder.py`, `test_open_folders.py`, `test_program_fixes.py` (part).
- Settings: `test_config.py`, `test_settings_file_damage.py`, `test_settings_versions.py`, `test_write_less.py`, `test_meta_config_option.py`.
- Options: `test_options_layout.py`, `test_option_list_saving.py`, `test_audit2_options_text.py`, `test_watchdog.py` (its Options row).
- Threads and errors: `test_threads.py`, `test_bounded_waits.py`, `test_error_report.py`, `test_watchdog.py`, `test_qt_log.py`.
- Logs: `test_live_log_debug.py`, `test_live_log_view.py`, `test_log_feed.py`, `test_input_monitor.py`.
- Updates: `test_update_check.py`, `test_update_model.py`, `test_program_fixes.py` (update part).
- Main window: `test_menus.py`, `test_main_window_fits.py`, `test_tool_windows_fit.py`, `test_tray_memory.py`, `test_usability_fixes.py`, `test_data_safety.py`, `test_help_guide.py`, `test_glossary_words.py`.

## 3. What it owns

In memory
- `Configuration._data`: every setting, `(section, group, name) -> {value, data_type, properties, expose, description, is_registered}` (`config.py:114`). Only `Configuration` should change it. **Others also do:** `history_model._restore_settings` reads `_data` directly (`gremlin/ui/history_model.py:307`).
- `MetaConfigOption._options`: custom Options rows (`option.py:763`).
- `deferred_write._pending` + one QTimer per key (`deferred_write.py:26,36`).
- `threads._live`: running threads/timers and their stop requests (`threads.py:30`). Main-thread timers (`MainTimer`) are **not** in it.
- `live_debug._buffer`: activity lines waiting for `logs.txt`.
- `UpdateModel` state (`idle/checking/upToDate/available/downloading/ready/error/failed`), the release, ready installer path, install-on-exit flag.
- `Backend.restart_on_exit` (owned by Backend, set by the shell's quit chain).
- Main.qml: `profileDirty`, `trayed`, `_quitPending`, `lastSaveText`, `shortcutCommands`, the pending action of the save-before-continue dialog.
- `window_registry.openWindows`: open tool windows by file name (Module Setup is separate: `Main.configureWin`).
- `_scan_cache` (second-copy scan, only during `main`).

Files
- `%USERPROFILE%\Gremlin Platforms\configuration.json` (always here, even when the data folder is moved); `configuration.json.bad-<date-time>` (damaged copy).
- `<data folder>\gremlin.lock` (instance lock).
- Logs folder: `system.log` (+`.1`, 1 MB rotate), `user.log` (+`.1`), `event.log` (new each session), `qt.log` (+`.1` over 1 MB at start, 5 MB per session cap), `crash.log` (appended), `logs.txt` (activity log, emptied at each start).
- `<data folder>\updates\`: downloaded `Gremlin-Platforms-R1-X.Y.Z-Setup.exe`, `.part` while downloading, setup `.log` files.
- Folders it creates at start: data folder, modules, logs, profiles, scripts, export, history, deleted devices, plugins.

Settings keys this subsystem registers or uses (others register their own; see Gaps)
- global/general: `check-for-updates`, `minimize-to-tray`, `log-level` (shown as "debug" / Diagnostic logs), `log-when-not-responding`, `device-change-behavior`, `refresh-axis-on-activation`, `refresh-axis-on-mode-change`.
- global/internal: `last-mode`, `last-mode-per-profile`, `last-profile`, `recent-profiles`, `skipped-update-version`, `last-run-version`, `update-feed-url` (testing only), `update-pending-version`, `update-pending-setup`, `settings-version`, `tray-notice-shown`, `live-start-empty`, `live-log-tab/-file/-level`, `twin-device-names`, `own-xbox-pads`, `button-map-recent-colours`.
- global/files: `data-folder`, `plugin-directory`, `modules-/logs-/profiles-/scripts-/export-/history-/deleted-devices-folder`.
- global/history: `keep-days`, `max-megabytes`.
- ui/general: `dark-mode`, `ui-scale`, `disable-windows-scaling`, `input-highlighting`.
- action/general: `action-priorities` (Add Action Menu order and choice).
- profile/automation: `enable-auto-loading`, `remain-active-on-focus-loss`, `entries-auto-loading`.
- devices/display: `aliases`; osc/connection: the OSC keys (OSC parked: mapped, not judged).
- Who else changes settings: every subsystem through `Configuration().set` (mode manager, window placement, HidHide, Home cards, Button Map options, OSC, Live Log Reader, update model), and History Restore.

## 4. Entry points

| Trigger | Handler | Function it ends in |
|---|---|---|
| Program start (`gremlin_platforms.exe` / `python joystick_gremlin.py`) | module level `joystick_gremlin.py:21-125` | `_windows_scaling_disabled` (reads configuration.json by hand), `setup_userprofile`, module imports in fixed order |
| | `main()` `:1072` | `_check_second_copy` → `qt_log.install` → `JoystickGremlinApp()` → `app.exec()` → shutdown sequence |
| App build | `JoystickGremlinApp.__init__` `:867` | `configure_loggers`, `live_debug.start`, `register_config_options`, `apply_log_level`, `hidhide.apply_on_start` (not off-screen), `error_report.install`, `watchdog.apply`, `device_initialization`, `initialize_qt` (Backend, UpdateModel), `PluginManager`, `purge_unused`, `update_action_priorities`, load `Main.qml`, `process_cmd_args`, `updater.startup`, `announce_damaged_settings`, `announce_vjoy_problems`, tray icon |
| Joystick driver can't start | `__init__` `:911` | loads `MainFailure.qml` (OK button → `Qt.quit()`) |
| Start fails anywhere in app build | `main()` `:1084` | `tell_could_not_start` (Windows box), `flush_all`, `threads.shutdown(1.0)`, `os._exit(1)` |
| Second copy found | `_check_second_copy` `:1048` | `_confirm_second_instance` (Yes/No/Cancel box) → `_terminate_other_gremlin` |
| `--profile X` / none | `process_cmd_args` `:979` | `backend.loadProfile` or `backend.openLastProfile`; missing → "Profile not found." |
| `--enable`, `--start-minimized` | `process_cmd_args` | `backend.activate_gremlin(True)`, `backend.minimize()` |
| Last profile failed at start | `backend.lastProfileFailed` → `Main.qml:1300` | Forget It → `backend.forgetProfile` / Keep |
| File → New Profile, Ctrl+N | `main_commands.js:30` → `requestNewProfile` `Main.qml:499` | `guardUnsavedChanges` → `leaveDisplayThen` → `backend.newProfile` |
| File → Load Profile…, Ctrl+O | `_loadProfileFileDialog` `:868` | `leaveDisplayThen` → `guardUnsavedChanges` → `backend.loadProfile` |
| File → Recent → item | `loadRecent` `:599` | same as Load |
| File → Save Profile, Ctrl+S | `saveCurrentProfile` `:505` | `saveProfileChecked` (asks about unfinished actions) → `backend.saveProfile` → `showSaveResult` |
| File → Save Profile As…, Ctrl+Shift+S | `openSaveAs` `:518` | `_saveProfileFileDialog` → `saveProfileChecked` |
| File → Open Program Folder / Open Data Folder | `backend.openProgramFolder/openDataFolder` | `util.program_folder` / `util.data_folder` in Explorer |
| File → Exit | `quitGremlin()` `:686` | `stopQuitForToolWindow` → `leaveDisplayThen` → `guardUnsavedChanges` → `deactivateThenQuit` → `Qt.quit()` |
| Main window X | `onClosing` `:1366` | saves window place; unsaved → `quitGremlin(false)`; Button Map dirty → its leave prompt; else the window closes |
| Main window X with Minimize to tray on | `SystemTrayIcon.eventFilter` `system_tray.py:76` | hides the window, one-time balloon; `onClosing` does not run |
| Minimize with Minimize to tray on | `_window_mode_changed_cb` `system_tray.py:247` | hides; `tray_memory.enter_tray` |
| Window hidden / shown | `_window_mode_changed_cb` | `Main.enterTray` / `leaveTray` (unload/reload pages), `tray_memory.release` after 400 ms |
| Tray left-click | `_system_tray_event_cb` | `restore_window` |
| Tray menu Show/Hide, Run Profile/Stop Profile, Exit Gremlin-Platforms | `_handle_context_menu_cb` | `_toggle_visibility`, `backend.toggleActiveState`, `restore_window` + `backend.quitRequested` → `Main.quitGremlin()` |
| Explorer restarts | `TaskbarCreated` message | `_add_icon` again |
| View → Home / Configuration / Home Layout / Scripts / Profile Settings | `main_commands.js:47-63` | `closeWorkRoom`, `openConfigurationForFocus`, `_moduleModel.setSplitMode`, `_openRoom` |
| View → Command Palette…, Ctrl+K | `_commandPalette.open()` | `Commands.search` / `Commands.trigger` (owners: "main") |
| Any shortcut | `Shortcut` per command `Main.qml:994` | `Commands.trigger(id)` (does nothing if the command isn't available now) |
| Tools → … (viewers, device setup, mapping, History, Options) | `openTool` / `openToolWith` / `openConfigureModule` / `openLogicalDevice` / `openBlankButtonMap` | `Helpers.createComponent` (one window per file, shared registry) |
| Debug → Live Log Reader | `openTool("DialogLiveLog.qml")` | `LiveLog`, `DebugLog`, `InputMonitor`; 400 ms refresh timer |
| Help → User Guide, F1 | `openTool("DialogHelp.qml")` | `help_topics.js topics()` |
| Help → Check for Updates | `main_commands.js:110` | opens DialogUpdate; `updater.check(true)` unless downloading/ready |
| Help → About | `DialogAbout.qml` | `backend.gremlinVersion` |
| Toolbar Home | `_homeButton` `:1038` | `closeWorkRoom` |
| Toolbar Run/Stop | `_toggleButton` `:1048` | `backend.toggleActiveState` → `activate_gremlin` → runner start/stop |
| Toolbar vJoy Viewer / Xbox Viewer | `:1064`, `:1076` | `Helpers.toggleComponent` (open or close) |
| Toolbar Button Map / Logical Device / Options | `:1088-1120` | `openBlankButtonMap`, `openLogicalDevice`, `createComponent("DialogOptions.qml")` |
| Toolbar Mode box | `_modeSelector.onActivated` `:1162` | `backend.selectMode(name)` (edit mode = running mode) |
| Toolbar Manage Modes | `:1195` | `DialogManageModes.qml` |
| Mode changed elsewhere | `uiState.modeChanged` `:1276` | updates device model, Logical pane, OSC list, Mode box |
| Window gets focus | `profileDirty` Timer 1.5 s while active `:35` | `backend.profileContainsUnsavedChanges` → title `*`, footer "(unsaved changes)" |
| Options: switch / number / combo / folder Select or Reset | `ConfigGroup.qml` delegates | `ConfigEntryModel.setData` → `Configuration.set` → `signal.configChanged` |
| Options: text field | `ConfigGroup.qml:286` | saved on leaving the field, Enter, or window close |
| Options: custom rows | `MetaConfigOption` widgets | `LogLevelModel.setLevel` (applies at once, tells every copy), `UiScaleModel.setScale` (`uiScaleChanged`), `WindowsScaleModel.setDisabled` (Restart/Later/Cancel → `backend.requestRestart`), `ActionSequenceOrdering.moveAmong/setShown/resetDefaults`, `ProfileAutoLoadingModel.newEntry/removeEntry/setData`, `TTSVoiceSelectionModel.currentIndex` |
| Options: search box | `ConfigSection`/`ConfigGroup.matches` | filters rows by group title, name, description |
| Options: History button | `DialogOptions.qml:94` | `DialogHistory.qml` filtered to settings |
| Options closes | `DialogOptions.qml:38` | `backend.emitConfigChanged` (+ audio player refresh) |
| `signal.configChanged` | `joystick_gremlin.py:900`, `Main.qml:1347` | `watchdog.apply`; dark mode; also module runtime claims, Home model, profile settings, pairing, output choices reload |
| `signal.showError` / `showNotification` | `Main.qml:1353-1363` | error dialog / message box |
| `updater.offerUpdate` | `Main.qml:1336` | opens DialogUpdate |
| `updater.installRequested` (download verified) | `Main.qml:1340` | `quitGremlin(false, true)` |
| Update window buttons | `DialogUpdate.qml:104-151` | `download`, `openReleasePage`, `skipVersion`, `install`, `cancel`, `check(true)`, `retryUpdate`; closing mid-download → `cancel` |
| `backend.restartRequested` | `Main.qml:1325` | `quitGremlin(true)` |
| App `aboutToQuit` | `joystick_gremlin.py:920,971,973`, `deferred_write.py:64` | `shutdown_cleanup`, tray `release_resources`, `deferred_write.flush_all` |
| After `app.exec()` | `main()` `:1095-1134` | `shutdown_cleanup` (again), `threads.shutdown`, `flush_all`, `history.close`, `flush_all`, unlock, `start_pending_install` or restart via `QProcess.startDetached`, `os._exit(0)` |
| Python exit | `atexit` `deferred_write.py:121` | `flush_all` |
| Unhandled error (main thread) | `sys.excepthook = exception_hook` `:896` | system.log + error dialog + console |
| Error in a thread | `threading.excepthook` `error_report.py:72` | system.log "Error in <name>" |
| Native crash | `faulthandler` `error_report.py:66` | `crash.log` |
| Main loop stuck 5 s (option on) | watchdog thread `watchdog.py:85` | system.log "Not responding…" + stacks; "Responding again…" |
| Live Log Reader controls | `DialogLiveLog.qml` | `LiveLog.refresh/clear/copyAll`, `DebugLog` setters, `loadWhole`, `clear`, `clearView`, `saveTo`, `openFolder`, `live`, `InputMonitor` |
| Theme colours change | `colorInformation.*Changed` → 0 ms timer `:956` | `ColorInformation.update_colors`, `ui_state.bumpThemeRevision` |

## 5. Talks to

| Other subsystem | The shell calls it | It calls the shell |
|---|---|---|
| Backend / UI state (`gremlin/ui/backend.py`) | creates it; `loadProfile`, `openLastProfile`, `newProfile`, `saveProfile`, `activate_gremlin`, `toggleActiveState`, `minimize`, `selectMode`, `setRestartOnExit`, `noteSave`, `unfinishedActions`, `profilesFolderUrl` | `quitRequested`, `restartRequested`, `lastProfileFailed`, `saveNoted`, `profileChanged`, `windowTitleChanged`, `emitConfigChanged`, reads `Configuration` |
| Run lifecycle (runner, EventListener, hooks) | `shutdown_cleanup` stops listener, device timer, mouse hook, runner, process monitor | auto-load reads `config.get_profile_with_regex`; threads go through `gremlin.threads` |
| Output modules / drivers | `gremlin.modules.output.reset_drivers()` at shutdown (through the output module, not the driver) | none |
| Device initialization (DILL, vJoy, ViGEm) | `joystick_devices_initialization`, `announce_vjoy_problems` | errors shown via `signal.showNotification` |
| Profile / modes | `last-profile`, `recent-profiles`, `last-mode-per-profile` keys | `mode_manager.flush_last_modes` schedules a deferred write (1 h safety net) |
| History (`gremlin/history.py`, `history_model.py`) | `Configuration.save_now` → `history.record("settings", …)`; `main` calls `history.close()` | History Restore writes settings with `Configuration.set` and reads `Configuration._data` |
| Module files (`gremlin/modules/module_file.py`) | `Configuration.save_now` uses `module_file.write_text` (safe write) | Home/module models listen to `configChanged` |
| Home cards, Configuration pages, Logical Device, Button Map, OSC, HidHide, viewers | Main.qml loads their pages and opens their windows; registers their options before purge | they register settings (some on import, some lazily) and call `Configuration.set` |
| Plugin manager | `PluginManager()` at start; `update_action_priorities` | action list for Options |
| Audio / TTS / OSC runtime | stopped in `shutdown_cleanup`; TTS voices for Options | none |
| Window placement | `WindowPlacement.restore/save` in Main.qml | none |
| Logging (`logging` system/user/event) | configured at start, level from Options | every subsystem logs into it; `log_feed` for Live |
| GitHub (network) | `UpdateModel.check/download` via QNetworkAccessManager | none |
| Windows | message boxes, process scan (PowerShell, Toolhelp), `TerminateProcess`, tray (Shell_NotifyIcon), Explorer, installer via `QProcess.startDetached` | tray messages |

## 6. Threads and timers

- Threads (all through `gremlin.threads`): "Qt log" copy thread (`qt_log.py:152`, stopped by giving stderr back); "not-responding watchdog" (`watchdog.py:71`, only while the option is on, waits 1 s at a time).
- Main-thread Qt timers: Watchdog tick 250 ms; one single-shot timer per deferred-write key (1 s; last mode 1 h); `profileDirty` refresh 1.5 s while the window is active (`Main.qml:35`); theme refresh 0 ms single shot; tray memory release 400 ms after hiding; Live Log Reader refresh 400 ms and a 60 ms redraw (`DialogLiveLog.qml:65,211`); `MainTimer` single shots for action timers (`threads.py:93`).
- Network: QNetworkAccessManager (no thread of ours); check timeout 10 s, download stall 30 s.
- Bounded waits in the shell: PowerShell process scan 4 s (before Qt), taskkill 3 s, `time.sleep(0.4)` after closing the other copy (before Qt), `QLockFile.tryLock(100 ms)`, stale lock 30 s, `threads.shutdown` 2 s total (1 s after a start failure), `Watchdog.stop` join 2 s.
- Order at quit: `aboutToQuit` → `shutdown_cleanup` + deferred flush; then after `exec`: `shutdown_cleanup` again → `threads.shutdown()` → `flush_all` → `history.close()` → `flush_all` → unlock → installer or restart → `os._exit(0)`. `os._exit` skips atexit on purpose; anything not stopped by then is cut off.
- `MainTimer`s are not in the thread list, so `threads.shutdown()` and `threads.running()` don't see them.

## 7. Rule breaks

Layer rule (hardware → input module → wiring → output module → driver)
- None in the shell. Shutdown releases vJoy/Xbox through `gremlin.modules.output.reset_drivers()` (`joystick_gremlin.py:271-273`); the tray and toolbar go through Backend. CONFIRMED (no break).
- Dependency direction: the core settings module imports UI and module code: `from gremlin.ui.live_debug import trace` (`config.py:22`), `from gremlin.ui.option import entry_title` (`config.py:101`), `from gremlin.modules import module_file` (`config.py:261`). This is not the hardware layer rule, but settings, the lowest layer, sit on the UI. CONFIRMED.

Single owner
- History Restore reads `Configuration._data` directly (`gremlin/ui/history_model.py:307`). CONFIRMED.
- Nobody owns the list of settings keys. They are registered in `register_config_options` (`joystick_gremlin.py:571-818`), when modules load (`shell_option.py:74`, `option.py:829-853`, `log_option.py:126`, `ui_scale_option.py`, `windows_scale_option.py`, `osc_option`), by start-up hooks (`module_model`, `hardware_profile`, `hidhide`, `window_placement`, `vjoy_status`, `button_map_options`, `live_debug.register_options`), and on first use (`live_debug.py:209,561`, `update_model.py:42`). `purge_unused` (`config.py:338`) deletes whatever isn't registered by then. AU-47 was this kind of bug. CONFIRMED.
- The same key is defined twice: `ui-scale` and `disable-windows-scaling` (`joystick_gremlin.py:677-688`, and again as custom rows in `ui_scale_option.py`/`windows_scale_option.py` with copied descriptions); `live-start-empty` (`joystick_gremlin.py:703`, `live_debug.py:561`). CONFIRMED.
- `Configuration` has no lock. `_data` is changed by `set`/`register` from whoever calls them. `deferred_write` moves the file write to the main thread, but the dict change is unguarded. No non-main-thread caller was found. SUSPECTED.

Thread and time rules
- `threads.MainTimer` is never put in `_live` (`threads.py:93-126`), so main-thread action timers (Tempo, Double Tap, Smart Toggle) can't be listed or stopped by `shutdown`. This ties to open AU-116. CONFIRMED.
- Time not through `gremlin.clock`: `watchdog.py:54,68,83,89` (`time.monotonic`; `clock` has no monotonic time), `config.py:175,503` (`time.time`), `joystick_gremlin.py:525` (`time.sleep(0.4)`, before Qt). AU-62's note left older `time.time` uses as they are. CONFIRMED.
- Untimed `wait()` in worker threads: `event_handler.py:307`, `macro.py:194`. Each is woken by its stop request, so they end. Not shell code; listed only because `threads.py` is the rule's owner. CONFIRMED, not a break.

Duplicated logic
- The settings file path and its parse are read by hand before Qt (`joystick_gremlin.py:21-35`), copying `util.USER_DATA_FOLDER` and `windows_scale_option.saved_disabled`. This is needed (Qt isn't loaded yet), and `test_user_data_folder.py::test_startup_scaling_check_reads_the_same_folder` guards it. CONFIRMED (justified).
- Two near-identical `EnumWindows` scans: `_gremlin_window_titles` (`joystick_gremlin.py:388`) and `_window_process_ids` (`:418`). CONFIRMED.
- `shutdown_cleanup` runs twice per quit (`aboutToQuit` at `joystick_gremlin.py:973`, and again at `:1097`). CONFIRMED. It calls `EventListener()`, `Backend()`, `AudioPlayer()`, `TTSManager()`, `OscRuntime()`, which build the singleton when it doesn't exist yet (for example `EventListener()` would hook the keyboard). SUSPECTED; it only matters on paths where they were never made.

## 8. Behaviour spec

### Start-up
- S1 It should read "Ignore Windows display scaling" from the program's own settings file before Qt starts, and run without Windows scaling when it is on. [help: Options] [test: test_user_data_folder.py::test_startup_scaling_check_reads_the_same_folder]
- S2 It should start with Windows scaling on when the settings file is missing or can't be read. [user confirmed 2026-10-06; was code only]
- S3 It should give the original scaling environment back before a restart, so the new copy reads the setting afresh. [user confirmed 2026-10-06; was code only]
- S4 It should load its modules in the fixed order in `joystick_gremlin.py` (never re-sorted), and every gremlin module should also import on its own. [test-plan: PROGRAM-STARTS-1019, NO-IMPORT-LOOPS] [test: test_program_imports.py, test_modules_import_alone.py]
- S5 It should create the Gremlin Platforms folder in the user's profile and every data sub-folder at start. [help: What is saved where] [test: test_user_data_folder.py::test_user_data_lives_in_gremlin_platforms]
- S6 It should register every setting before it removes unused ones, so remembered choices (Live Log Reader tab, window sizes) survive a start. [tracker: AU-47] [test: test_startup_settings_kept.py::test_window_and_tab_settings_survive_purge]
- S7 It should open the profile given with `--profile`, with a relative path read from the folder the program was started in. [tracker: APP10] [test: test_program_fixes.py::test_a_relative_profile_is_read_from_where_the_program_started]
- S8 A `--profile` file that doesn't exist: it should say "Profile not found." and open the last profile instead. [user decision: APP10 message, then last profile] [test: test_program_fixes.py::test_a_missing_profile_is_told_and_the_last_one_opens]
- S9 Without `--profile` it should open the last profile used. If that fails, it should show a new empty profile and ask Forget It / Keep (Forget It takes it off start-up and Recent; the file stays). [test-plan: STARTUP-MESSAGES] [tracker: APP17]
- S10 `--enable` should start Run once the profile is loaded; `--start-minimized` should start minimized, and in the tray when Minimize to tray is on. [user confirmed 2026-10-06; was code only]
- S11 Once the main window is up, the update check, the Settings Reset notice and the vJoy set-up message should each come at most once. [test-plan: SETTINGS-FILE-DAMAGE, STARTUP-MESSAGES]
- S12 If the joystick driver can't start, it should show the start-up failure page with the reason and an OK button (which ends the program) instead of the main window. [user confirmed 2026-10-06; was code only] [changed 2026-10-07 to follow the glossary (button text "OK"), which wins over the earlier wording "Quit"]
- S13 A broken user plugin should be left out and logged, never stop the start, and never replace a built-in action or QML type. [tracker: AU-35, AU-86] [test: test_audit2_startup_devices.py::test_a_bad_user_plugin_is_left_out_entirely, test_audit3_startup.py::test_a_user_plugin_cant_replace_a_built_in_qml_element]

### Could not start
- S14 Any failure while the program starts should show a Windows box "Gremlin-Platforms could not start." with the reason, the last lines of the error, the logs folder and "Press Ctrl+C to copy this message". It should log the failure and end the process so no thread keeps it alive. [user decision: APP3 show a message box] [test: test_could_not_start.py::test_main_tells_the_user_and_ends_when_starting_fails, ::test_message_names_the_reason_the_error_and_the_logs]
- S15 A main window that fails to load should be reported with its QML errors. [test: test_could_not_start.py::test_broken_main_window_raises_with_the_qml_errors]
- S16 The same box should cover a failure while modules load and while the user folder is made (the 1.0.18 kind of failure). [tracker: APP3] (the code doesn't: see Gaps)

### Second copy
- S17 A clean start (lock taken, no other Gremlin-Platforms window) should run no process scan and ask nothing. [tracker: APP9] [test: test_program_fixes.py::test_a_clean_start_runs_no_process_scan, test_second_copy_detection.py::test_main_alone_does_not_ask]
- S18 Otherwise it should scan once and ask: Yes = close the other copies (their unsaved changes are lost) and start; No = start anyway (vJoy may not respond); Cancel = don't start. [test-plan: SECOND-COPY-EXE-NAME, STARTUP-MESSAGES] [test: test_second_copy_detection.py::test_main_cancel_does_not_start, ::test_main_close_others_closes_then_takes_the_lock, ::test_main_continue_starts_without_closing]
- S19 It should recognise `gremlin_platforms.exe`, `joystick_gremlin.exe` and Python running `joystick_gremlin.py`, and never count itself or the program that launched it. [tracker: F6] [test: test_second_copy_detection.py::test_installed_and_older_exe_count_as_gremlin, ::test_starting_copy_never_finds_itself, ::test_python_counts_only_when_running_gremlin]
- S20 With No, the second copy runs without the lock. Two copies are then allowed, and History may lose lines. [tracker: AU-41 wont-fix "the lock lets only one copy run"] [user confirmed 2026-10-06; was code only]

### Off-screen runs
- S21 Off-screen (tests, checks), it should install no keyboard or mouse hooks, show no Windows boxes (it logs them and answers Cancel), close no other process, skip HidHide, and make no tray icon. [test-plan: AUDIT3-TRACE W6] [tracker: AU-73, AU-98] [test: test_audit3_startup.py::test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray, ::test_off_screen_another_process_is_never_closed]
- S22 "Off-screen" should be decided by the platform Qt started on, and before Qt by `-platform` or the first entry of `QT_QPA_PLATFORM`. [test: test_audit3_startup.py::test_before_qt_the_platform_argument_wins, ::test_once_qt_runs_its_platform_decides]
- S23 Tests and off-screen checks should never reach GitHub (`GREMLIN_OFFLINE`). [test-plan: AUDIT-G-SCREENS AU-66]

### Settings file
- S24 Settings should live in `configuration.json` in `%USERPROFILE%\Gremlin Platforms`, even when the data folder is moved, so the moved folder can be found. [user confirmed 2026-10-06; was code only]
- S25 A single setting that can't be read should fall back to its default; every other setting is kept. [user decision: APP1/APP2 keep good settings] [test: test_settings_file_damage.py::test_bad_settings_fall_back_and_good_ones_are_kept]
- S26 A file that can't be read at all should be kept as `configuration.json.bad-<date-time>`. The program starts with defaults and says so once ("Settings Reset" with the copy's path) when the main window is up. [user decision: APP2 back up, tell once] [test: test_settings_file_damage.py::test_unreadable_file_is_kept_aside_and_announced_once]
- S27 An empty file should count as no settings (nothing kept aside). [test: test_settings_file_damage.py::test_empty_file_is_like_no_file]
- S28 A bad value should never hang the start; the file is read once at start. [tracker: APP1] [test: test_settings_file_damage.py::test_bad_value_does_not_hang_start_up, ::test_settings_are_read_once_before_the_application_runs]
- S29 Saving should write a temporary file and swap it in, so a crash can't leave a broken file. It should create the folder if it is missing. [test-plan: WRITE-LESS] [test: test_settings_file_damage.py::test_saving_creates_the_settings_folder]
- S30 Many quick changes should make one write about 1 s after the last. Every waiting write should go to disk on quit, before a restart, before an install, and before the file is read again. [test-plan: WRITE-LESS] [tracker: AU-45] [test: test_write_less.py::test_many_settings_changes_make_one_write, ::test_deferred_write_runs_once_and_on_flush]
- S31 With no Qt application running (tools, tests), a change should be written at once. [test: test_write_less.py::test_without_qt_a_write_happens_at_once]
- S32 An unchanged value or list should not be written. A list edited in place should still be saved. [test-plan: WRITE-LESS (4)] [test: test_write_less.py::test_unchanged_auto_load_list_is_not_saved, test_config.py::test_list_edited_in_place_is_saved]
- S33 The settings should record the newest program version that used them. An older version keeps settings it doesn't know; the same or a newer version removes retired ones with an Info line. [test-plan: LOG-WARNINGS] [test: test_settings_versions.py::test_an_older_version_keeps_a_newer_versions_settings, ::test_the_same_or_a_newer_version_removes_retired_settings]
- S34 Every saved change to a setting the user chooses should go into History, titled with the names Options shows. Window places and other things the program remembers for itself should not. [glossary: History] [tracker: AU-103] [test: test_audit2_options_text.py::test_history_names_settings_as_options_does]
- S35 A setting that appears for the first time should not count as a History change. [user confirmed 2026-10-06; was code only]
- S36 Activity lines made before the application runs should be held and kept, not written early. [test: test_settings_file_damage.py::test_activity_lines_before_the_application_runs_are_kept]
- S37 Whoever had the old Close to tray on should get Minimize to tray on, after which the old key is dropped. [test-plan: TRAY-ONE]
- S38 A settings file that can't be written should not stop a quit or an update install; it is logged. [tracker: AU-96] [test-plan: AUDIT2-F-H-REST]

### Options window
- S39 Tools → Options and the toolbar's Options button should open one Options window. Only one can be open. [help: Options] [changed 2026-10-07 to follow decision 07 Q17 (the Button Map has its own Options pane), which wins over the earlier wording "also when opened from the Button Map"] [tracker: N5, N16]
- S40 The sidebar should show General, Interface, Actions, Profiles, Home, OSC and Folders. Each group is a card of rows (name, description, control on the right). [test-plan: OPTIONS-LOOK] [help: Options]
- S41 Every registered setting should show exactly once. One that isn't placed shows under "Other" in its section. `action-priorities` never shows. The Button Map's settings are only in Button Map Options. [glossary: Button Map Options] [test: test_options_layout.py::test_every_setting_shows_once_and_button_map_is_apart]
- S42 General should hold Startup and Tray, Devices, Diagnostics (Diagnostic logs, Log When Not Responding) and History. Actions should hold the Add Action Menu, Macro, Change Mode, Double Tap, Smart Toggle, Tempo, Axis Delta, Play Sound and Text to Speech. [tracker: AU-71, AU-102] [test: test_options_layout.py::test_history_settings_have_their_own_group, test_audit2_options_text.py::test_action_settings_have_their_own_group]
- S43 Search should find settings by name, description or group title in every section; the word "Other" matches nothing. [test-plan: OPTIONS-LOOK, AUDIT3-TRACE W7]
- S44 Switches, number boxes and drop-downs should take effect when changed. Text fields save on leaving the field, on Enter, or when the window closes. [test-plan: WRITE-LESS (3)]
- S45 Rows should be titled with real names, not keys ("UI scale", "Plugins folder", "Diagnostic logs"), and group titles in US spelling. [tracker: D14] [glossary: Spelling]
- S46 Folder rows: Select should open a folder picker at the current folder; Reset should put the default back. [test-plan: Batch 7 OPT-F]
- S47 Options' History button should open History filtered to settings. [user confirmed 2026-10-06; was code only]
- S48 Escape should close Options. Options remembers its size and is never larger than the screen. [tracker: UI6, C20]
- S49 Closing Options should tell the program that settings changed. [user confirmed 2026-10-06; was code only]
- S50 Ignore Windows display scaling should ask Restart / Later / Cancel. Restart quits the usual way and starts again; Cancel undoes the change. [test-plan: W-11, OPT-U02]
- S51 The UI scale slider should be off while Windows scaling is on, and resize the program when released while it is off. [test-plan: OPT-U06] [help: Options]
- S52 Dark mode should apply at once on every window. [test-plan: OPT-U01]
- S53 Add Action Menu: tick to offer an action, drag by its handle to reorder within its kind (other actions keep their places), "X of Y offered", and Reset to Default (Map to vJoy, Macro, Response Curve first, the rest by name, all offered). Every change is saved. [test-plan: OPTIONS-LOOK] [tracker: B28] [test: test_options_layout.py::test_move_among_keeps_other_kinds_in_place, test_option_list_saving.py::test_action_order_move_is_saved]
- S54 Auto-load rows (New Entry, remove, edits) should be saved at once. [test: test_option_list_saving.py::test_auto_loading_new_entry_and_remove_are_saved]
- S55 Diagnostic logs in Options and in the Live Log Reader should be one setting; a change in either shows in both at once. [glossary: Diagnostic logs] [test-plan: LIVE-LOG-LEVELS]
- S56 Diagnostic logs Off should still keep errors in system.log. [user decision: APP17 logs Off still keeps errors]

### Main window
- S57 The title should read "* name - Gremlin-Platforms R1", with * while there are unsaved changes and "Untitled" before the first save. [tracker: C2] [glossary: program's name]
- S58 The toolbar, left to right: Home, Run, vJoy Viewer, Xbox Viewer, Button Map, Logical Device, Options, then Mode and its list, and Manage Modes. [glossary: Run / Stop, Mode] [tracker: N16]
- S59 The Run button should read Run, and Stop (accent color) while the profile runs. [glossary: Run / Stop] [help: Run and status]
- S60 vJoy Viewer and Xbox Viewer should open the viewer, or close it when it is open. [test-plan: TB-03]
- S61 Home and Logical Device should use the accent color while their page is shown. [test-plan: TB-01, TB-05]
- S62 In a narrow window the captions should hide first (icons only, tooltips still name them), then the Mode list narrows to its minimum. If even the icons don't fit, the toolbar scrolls sideways. The window's minimum size is never larger than the screen. [user decision: UI1 hide captions, keep icons] [test: test_main_window_fits.py]
- S63 The Mode list should set the mode you edit, which is also the mode that runs. It follows mode changes made elsewhere, and is never blank after New, Load or Save As. [glossary: Mode] [help: Run and status] [test-plan: F-01b]
- S64 The footer should show "Status: Running" or "Stopped", plus "(Paused)", plus "(unsaved changes)" while it runs with unsaved edits. Beside it is the last save line, with a tooltip. [help: Run and status] [tracker: N18] [glossary: Mode (no footer duplicate)]
- S65 Menus, shortcuts and the palette should come from one command list. File: New Profile, Load Profile…, Recent, Save Profile, Save Profile As…, Open Program Folder, Open Data Folder, Exit. View: Home, Configuration, Home Layout, Scripts, Profile Settings, Command Palette…. Tools: Viewers, Device Setup, Mapping, History, Options. Debug: Live Log Reader. Help: User Guide, Check for Updates, Save Diagnostics…, About. [test-plan: MENU-2, FM1-OPEN-FOLDERS, TOOLS-HISTORY-MENU] [test: test_menus.py::test_every_main_command_is_in_the_menu_bar]
- S66 Menus should show only what can be used now; nothing is greyed out. [help: Menus and the command palette] [tracker: C4 wont-fix, deliberate]
- S67 Shortcuts: Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Shift+S, Ctrl+K, F1, shown beside their commands. [help: Menus and the command palette]
- S68 The Command Palette (Ctrl+K) should list the main window's commands that can be used now, searched by words, with Up/Down/Enter. [help: Menus and the command palette] [test-plan: MENU-2, MENU-6]
- S69 A shortcut for a command that can't be used now should do nothing. [user confirmed 2026-10-06; was code only]
- S70 Run/Stop should be only on the toolbar and the tray: no menu, palette or shortcut. [user decision: AU-74 not done]
- S71 New, Load and Recent should first close panels with unsaved display edits (asking), then ask Save / Discard / Cancel when the profile has unsaved changes. [help: Profiles] [test-plan: F-02b] [tracker: AU-15]
- S72 Save on a never-saved profile should open Save As in the profiles folder. A save that would leave out unfinished actions asks first. [test-plan: F-04b, SAFE-1]
- S73 Open Program Folder should open the program's folder (the source folder when run from source); Open Data Folder opens the data folder chosen in Options. [test-plan: FM1-OPEN-FOLDERS] [test: test_open_folders.py::test_the_actions_open_those_folders]
- S74 Errors should show in an error dialog whose details wrap and can be copied; notices show in a message box. [tracker: UI9, D16]

### Quitting, closing, restarting
- S75 File → Exit, tray Exit and the X should follow one order. First a Module Setup or Calibration window with unsaved work asks, and the quit stops there. Then open panels and the Logical pane ask, then the profile (Save / Discard / Cancel), then the Button Map's own leave prompt. Then Run stops and the program quits. [test-plan: SAFE-3 N4, W-03, F-06a] [tracker: N4]
- S76 Cancel at any step should call off the quit and any restart or update install that waited on it. [tracker: A10] [test: test_update_model.py::test_cancelled_quit_clears_the_install]
- S77 Closing a Save As window that the quit's Save opened should call off the quit; the next Save As starts clean. [tracker: A10] [test-plan: SAFE-1]
- S78 On quit it should stop Run, the listener and hooks, release vJoy and Xbox through the output modules, and stop sound, speech and OSC. It asks every program thread to stop (2 s in all, naming any that won't in system.log), writes every waiting settings and activity write, closes History without cutting a line, and gives up the lock. [test-plan: THREAD-OWNER, WRITE-LESS] [tracker: AU-48]
- S79 The main window's place and size should be saved when it closes and restored at start. [test-plan: W-01]
- S80 Closing the main window with nothing unsaved (Minimize to tray off) should quit the program. [user confirmed 2026-10-06; was code only] (see Q1)
- S81 A restart should quit the usual way and start the program again with the same arguments; a cancelled quit cancels the restart. [test-plan: W-11] [test: test_restart_command.py]
- S82 History should never be able to stop a quit. [test-plan: AUDIT3-TRACE W5]

### Tray
- S83 The tray icon should show one picture while stopped and another while running, and follow Run/Stop. [test-plan: TB-02]
- S84 A left click should bring the window back. The right-click menu has Show/Hide Gremlin-Platforms, Run Profile/Stop Profile, and Exit Gremlin-Platforms. [glossary: Run / Stop (tray), program's name] [test-plan: W-06..09]
- S85 Minimize to tray (off by default): minimizing or closing should hide the window to the tray while the profile keeps running. File → Exit and the tray's Exit still quit. [help: Options] [test-plan: TRAY-ONE]
- S86 The first time the X hides the window, a tray balloon should say the program is still running, and never again. [test-plan: TRAY-ONE]
- S87 While hidden in the tray, the pages should be unloaded (Configuration stays while it has unsaved display edits) and loaded again when shown. The profile keeps running throughout. [test-plan: MEM-2] [test: test_tray_memory.py::test_hidden_window_unloads_and_reloads]
- S88 The tray icon should come back after Explorer restarts. [user confirmed 2026-10-06; was code only]
- S89 Tray Exit should bring the window back first, so the unsaved-changes questions can be seen. [user confirmed 2026-10-06; was code only]

### Threads and time
- S90 Every program thread should start through `gremlin.threads` with a readable name and a stop request, and be listed while it runs. [test-plan: THREAD-OWNER] [user decision: project rule] [test: test_threads.py::test_a_thread_is_named_and_listed_while_it_runs]
- S91 `shutdown()` should ask each thread to stop and wait at most one time limit in all, naming those still running in system.log. [test: test_threads.py::test_shutdown_asks_each_thread_to_stop_and_waits, ::test_shutdown_names_a_thread_that_will_not_stop]
- S92 A thread that ends with an error should still leave the list. [test: test_threads.py::test_an_error_in_a_thread_still_takes_it_off_the_list]
- S93 Timers started on the main thread for actions should run their function on the main thread. [tracker: ACT20] [code: threads.py:115]
- S94 Timed loops should read the time and sleep through `gremlin.clock`, so tests can step time. [test-plan: TEST-HOOKS] [user decision: project rule]
- S95 Nothing on the main thread should wait without a limit. [test-plan: TEST-HOOKS] [user decision: project rule] [test: test_bounded_waits.py]

### Logs and errors
- S96 The logs folder should hold system.log and user.log (1 MB, one backup each), event.log (new each session) and qt.log, all written as UTF-8. [help: Live Log Reader] [tracker: AU-39]
- S97 Diagnostic logs should default to Warning. [user confirmed 2026-10-06; was code only]
- S98 An unhandled error should be logged to system.log, shown in an error dialog ("An unhandled exception occurred."), and passed to a console when there is one. [tracker: APP16] [test: test_error_report.py::test_a_top_level_error_is_logged_shown_and_passed_on]
- S99 An error inside a program thread should be logged as "Error in <thread name>" with its traceback. A thread ending with SystemExit is not an error. [user decision: H3 thread errors logged only] [test: test_error_report.py::test_an_error_in_a_thread_is_logged_with_its_name]
- S100 A hard crash in native code should write every thread's stack to crash.log in the logs folder, appending so an earlier crash is kept. [user decision: crash.log in the logs folder] [test: test_error_report.py::test_the_crash_log_is_turned_on_in_the_logs_folder]
- S101 Qt's own messages should go to qt.log with the time, and to the console when there is one. qt.log moves to qt.log.1 at start once over 1 MB; one session writes at most 5 MB, then one line saying so. [test-plan: QT-LOG] [help: Live Log Reader] [test: test_qt_log.py]
- S102 A repeating error should be logged once per run. [test-plan: WRITE-LESS (8)] [test: test_write_less.py::test_repeating_errors_are_logged_once]
- S103 Routine status lines (each Run) should be Info, so the default Warning log stays quiet. [test-plan: LOG-WARNINGS]

### Live Log Reader
- S104 Debug → Live Log Reader should have the tabs Config, Debug and Input Monitor. It remembers the tab, the Log choice and the Show level; Find starts empty, Live starts off, and it doesn't reopen at start. [glossary: Live Log Reader] [user decision: LIVE-LOG-CHOICES-KEPT] [test: test_live_log_view.py]
- S105 Config should show the activity log (logs.txt: which files were read and saved), emptied at each start. Clear Log asks first; Copy All copies it. [help: Live Log Reader] [tracker: C12]
- S106 Debug should offer Log = All logs, System, Scripts, Events, Qt; Show = All, Info, Warning, Error; and Find. A traceback stays with its entry, warnings show amber and errors red, with "X of Y entries". [help: Live Log Reader] [test: test_live_log_debug.py::test_levels_and_find, ::test_a_traceback_belongs_to_its_entry, ::test_all_logs_merges_every_file_by_time]
- S107 For a file over 512 KB it should show the last 512 KB with a note and Load Whole File. [help: Live Log Reader] [test: test_live_log_debug.py::test_load_whole_file]
- S108 Clear Log should empty the shown file through the program's own handler (so later lines start at the top), after asking. It is not offered for All logs. [test: test_live_log_debug.py::test_clear_empties_the_file_through_its_handler] [test-plan: DEBUG-ALL-LOGS]
- S109 Live should catch every line at full detail whatever the level, while the files keep their level. It has Start empty, Clear View (never a file), Save Feed… and Show Log File. Live and the Input Monitor stop when the window closes. [help: Live Log Reader] [glossary: Live] [test: test_log_feed.py]
- S110 Red debug mode: every window should have a red frame and a DEBUG badge while Diagnostic logs is ALL or Live runs; the badge opens the Live Log Reader. [glossary: red debug mode] [test-plan: LOG-READER-BATCH]
- S111 The view should never stay blank after switching to a shorter log. Live adds rows without redrawing everything, and redraws wait while text is selected. [test-plan: LOG-VIEW-BLANK] [tracker: APP14] [test: test_live_log_view.py, test_program_fixes.py::test_live_adds_rows_without_drawing_the_view_again]

### Log When Not Responding
- S112 Log When Not Responding (Options › General › Diagnostics) should be off by default and take effect at once when changed. [glossary] [test: test_watchdog.py::test_the_option_is_off_by_default_and_takes_effect_at_once, ::test_the_option_is_in_options_diagnostics]
- S113 After 5 s with no main-loop tick it should write "Not responding for N s" and every thread's stack to system.log once per freeze, then "Responding again after N s". [user decision: H7 name, 5 s, off by default] [test: test_watchdog.py::test_a_freeze_is_logged_once_with_the_stacks_then_the_recovery]

### Updates
- S114 Help → Check for Updates should open the Update window and check, unless a download is running or ready. [help: Installing and updating]
- S115 With Check for updates on (the default for new settings), the start-up check should stay silent unless a newer version exists that wasn't skipped. A start-up check that fails stays silent; a check you asked for says why. [help: Installing and updating] [test-plan: UPD-APP, UPD-EXISTING-CONFIG] [test: test_update_check.py::test_should_offer]
- S116 Skip This Version should stop the start-up check from offering that version; a check you ask for still shows it. [help: Installing and updating] [test: test_update_check.py::test_should_offer]
- S117 An installed copy (uninstaller next to the program) should offer Update Now. It downloads the installer, checks its size and SHA-256 against GitHub, quits the usual way (asking about unsaved changes), installs silently and starts the new version. A portable or source copy only links to the release page. [help: Installing and updating] [test: test_update_check.py::test_install_kind, test_update_model.py::test_nothing_installs_without_a_verified_download]
- S118 Nothing unverified should be downloaded or run. The installer must have an https URL, a size and a SHA-256 digest; a download that doesn't match is deleted. [test-plan: UPD-NET] [test: test_update_check.py::test_release_without_a_verifiable_setup]
- S119 Closing the Update window during a download should cancel it and delete the partial file. [tracker: A14]
- S120 A full disk, a rename failure or an updates folder that can't be made should say "Could not save the download to <folder>: <reason>". [tracker: APP12] [test: test_program_fixes.py::test_a_full_disk_is_reported_as_one]
- S121 After an update it should say "Updated" once and delete the old installers, keeping setup logs. A first run is not an update. [test: test_update_model.py::test_says_so_once_after_an_update, ::test_first_run_is_not_an_update]
- S122 If an update didn't finish, the next start should open the Update window saying so, with setup's log path and Try Again. [user decision: APP7 reopen + message + Try Again] [tracker: AU-45] [test: test_program_fixes.py::test_a_failed_update_is_told_with_try_again]
- S123 Update requests should close their connection with the reply (no stray SSL message about 30 s later). [test-plan: SSL-CONSOLE]

### User data folders
- S124 The data folder should default to Gremlin Platforms in the user's profile. Each folder (profiles, modules, scripts, export, logs, history, deleted devices, plugins) can be chosen in Options → Folders and defaults to a folder inside the data folder. [help: Options] [test-plan: Batch 7 OPT-F] [test-plan: AUDIT2-F-H-REST]
- S125 Changes to the logs folder and the plugins folder should take effect on the next start. [test-plan: OPT-F01..F08 "Plugin dir and logs need a restart"]
- S126 A chosen folder that can't be made or reached should fall back to the default folder. [user confirmed 2026-10-06; was code only]
- S127 (retired) ~~Device files from the old `qml/maps` folder should be copied once into the modules folder, never over an existing file.~~ [changed 2026-10-07 to follow GL-272 (nothing ships in `qml/maps`; `copy_legacy_modules` removed in batch 3)]

### Help viewer
- S128 Help → User Guide (F1) should open the guide by section. The Button Map has its own guide (its F1), apart from the main one. [help] [test: test_help_guide.py::test_button_map_help_is_its_own_guide]
- S129 Every menu path the guide names should exist, every action should have a topic, and removed features should not be mentioned. [test-plan: HELP-C, HELP-CATCH-UP] [test: test_help_guide.py::test_menu_paths_in_the_guide_exist, ::test_every_action_plugin_has_a_topic, ::test_removed_or_wrong_things_are_not_in_the_help]
- S130 About should show the build's version and this repository. [test-plan: HELP-C] [test: test_help_guide.py::test_about_shows_the_build_version]
- S131 Escape should close Help, About and Check for Updates. Windows a stick is used in ignore Escape. [tracker: UI6] [user decision: C19 left as is]
- **S132** Help → Save Diagnostics… (also a button on the Debug tab) should save one zip, through a Save dialog that starts on the Desktop: the program's logs, its settings, the device list (names, ids, kinds, connected), and the program and Windows versions. The open profile is left out unless a box in the dialog is ticked. The user's name in folder paths is replaced by `<user>`. When done it says where the zip went; a failure names the file, folder and reason (as 07 Q19). [user decision 2026-10-07: D-01-DIAG-ZIP]
- **S133** When Check for Updates finds a newer version, the Update window should show that release's notes from GitHub, formatted and scrollable; when versions were skipped, each release's notes newest first. With no notes or no network it says "Release notes unavailable." and updating still works. [user decision 2026-10-07: D-01-UPDATE-NOTES]

## 9. Questions for the user

- Q1 Closing the main window with the X, with nothing unsaved and Minimize to tray off, while a tool window (say the vJoy Viewer) is open. Tool windows are made with no parent window (`helpers.js:47`), and nothing calls quit (`Main.qml:1366-1388`), so the program may keep running with only the viewer showing. Should the X always quit the program (after the usual questions)? Recommendation: yes, the X on the main window quits, the same as File → Exit.
- Q2 Exit while Minimize to tray is on. In Qt 6, quitting first closes every window, and the tray's close filter (`system_tray.py:76-90`) hides the window on any close, not only your X. The quit may be refused and the window just hides. Off-screen runs now have no tray icon (AU-73), so no test covers this. Should Exit always end the program? Recommendation: yes (the help already says so); check it once on a real screen before anything changes.
- Q3 When the X hides the window to the tray, `onClosing` doesn't run, so its place and size aren't saved then (test plan W-21 / S-21 never ticked). Recommendation: save the place whenever the window hides to the tray.
- Q4 Changing the Logs folder (or the data folder) while the program runs. The log files stay open in the old folder, but the Live Log Reader reads the new one, so it shows empty or old logs. Recommendation: the folder rows say "takes effect on the next start", and readers and writers both stay on the start-up folder until then.
- Q5 A chosen data folder that is missing at start (unplugged drive) is silently replaced by the default folder (`util.py:858-872`), so new profiles and logs land somewhere else. Recommendation: use the default and say so once, like Settings Reset.
- Q6 If configuration.json can't be written (read-only, locked), the failure only goes to system.log (`deferred_write.py:100-105`), so you think a setting was kept when it wasn't. Recommendation: one notice per session ("Settings could not be saved: <reason>").
- Q7 History Restore of a setting that acts at once (Diagnostic logs level, UI scale) writes the value but doesn't apply it: the log level is applied only by its Options control, and the UI scale only on its own signal. Recommendation: Restore applies them at once, exactly as the Options control does.
- Q8 A failure while modules load, or while the user folder is made, happens before `main()`'s guard (`joystick_gremlin.py:44-125`, `:74`). The "could not start" box and system.log never see it; the 1.0.18 failure was this kind. Recommendation: the box should cover every start-up failure (APP3's intent).
- Q9 Second copy, Yes: if the other copy still holds the lock afterwards, this copy starts without the lock and says nothing (`joystick_gremlin.py:1064-1067`). Recommendation: say "The other copy could not be closed" and offer No / Cancel again.
- Q10 [code only] Main-thread timers for Tempo, Double Tap and Smart Toggle are not in the program's thread list, so quit and Stop can't see or cancel them (with AU-116). Recommendation: list them like every other timer; build it in the Run lifecycle redesign.
- Q11 [code only] `shutdown_cleanup` runs twice per quit, and may create a listener, speech engine or OSC runtime that never existed just to stop it. Recommendation: run it once, and only stop what exists.
- Q12 [code only] Every Options change sends one general "settings changed" signal. Input-module claims, Home cards, pairing and output choices all reload on it, even for a dark-mode or tray toggle. Is that acceptable? Recommendation: keep it for now; split it by area only if it shows up as slow.
- Q13 The User Guide's Options topic (`help_topics.js:268-279`) is behind the window. It omits Log When Not Responding, the History group, Double Tap, Smart Toggle, Tempo and Axis Delta, and the Folders it lists leave out data, history, deleted devices and plugins. Recommendation: update the text to match `_LAYOUT`.
- Q14 Option text uses retired or odd words: "Show stub cards for detected hardware that has no saved module." (`shell_option.py:29`; glossary: "device without a module") and "Keep the last: value after the control is released." (`:37`). File pickers in Options are titled "Select a File" / "Select a Folder" (`ConfigGroup.qml:245,257`; glossary: titled by what they do). Recommendation: reword to the glossary.
- Q15 [code only] Diagnostic logs default to Warning (`log_option.py:22`). Confirm this is the default you want. Recommendation: keep Warning.
- Q16 [code only] With No in the second-copy box, two copies run at once. Should No stay? Recommendation: keep it (it's your earlier wording), since the box already says vJoy may not respond.

## 10. Known gaps

Code differs from the spec or a rule
- K1 The X can leave the program running with no main window while a tool window is open (Q1). SUSPECTED (`Main.qml:1366-1388`, `helpers.js:47`).
- K2 Exit with Minimize to tray on may be refused by the tray's close filter (Q2). SUSPECTED; not covered by any test.
- K3 The window place isn't saved when the X hides to the tray (Q3). SUSPECTED (W-21 open in the test plan).
- K4 Start-up failures before `main()` bypass the box and the logs (S16, Q8). CONFIRMED (`joystick_gremlin.py:44-125`).
- K5 Logs folder change mid-session splits writers (fixed at start: `joystick_gremlin.py:821-836`, `qt_log.install :1079`, `error_report.install :897`) from readers (`live_debug.py:351-356` call `logs_dir()` each time). CONFIRMED.
- K6 The chosen data folder falls back silently (Q5). In `_configured_child` the fallback `mkdir` is unguarded (`util.py:890-891`), so a data folder that can't be written can raise. CONFIRMED.
- K7 A failed settings write is only logged (Q6). CONFIRMED (`deferred_write.py:100-105`).
- K8 History Restore doesn't re-apply settings that act at once (Q7). SUSPECTED (`history_model.py:294-316`; `apply_log_level` isn't tied to `configChanged`).
- K9 `MainTimer` isn't tracked by `gremlin.threads` (Q10, AU-116). CONFIRMED (`threads.py:93-126`).
- K10 No owner for the list of setting keys; `purge_unused` depends on everything being registered first (rule break, AU-47 class). CONFIRMED.
- K11 Keys defined twice: `ui-scale`, `disable-windows-scaling`, `live-start-empty`. CONFIRMED.
- K12 History Restore reaches into `Configuration._data`. CONFIRMED (`history_model.py:307`).
- K13 `config.py` imports UI and module code. CONFIRMED (`config.py:22,101,261`).
- K14 `shutdown_cleanup` runs twice and may build singletons (Q11). CONFIRMED / SUSPECTED.
- K15 Second copy, Yes with the lock still held starts silently without it (Q9). CONFIRMED.
- K16 The help Options topic is out of date (Q13). CONFIRMED.
- K17 Option wording against the glossary (Q14). CONFIRMED.
- K18 Time not through `gremlin.clock` in `watchdog.py`, `config.py` and `joystick_gremlin.py`. CONFIRMED (low).
- K19 The Live Log Reader's 400 ms refresh calls `logs_dir()` (reads settings and runs `mkdir`). When any file changed under All logs, it reads up to 4 × 512 KB on the main thread. [code only], not measured.
- K20 `Configuration.register` logs a Warning at every start when the PC's IP list changed (the OSC host choices: `joystick_gremlin.py:775-789`, `config.py:300-305`). OSC parked: mapped only.

Open tracker items for this subsystem
- AU-56 (open, on hold): at 200% UI scale on a small screen, contents are cut off, including Options search and the main toolbar.
- AU-119 (open): about 20 tests wait a fixed short time, including the watchdog test.
- AU-116 (open, Run lifecycle map): Tempo, Double Tap and Smart Toggle timers aren't cancelled at Stop; K9 is the shell's side of it.
- AU-74 (won't fix, your choice): no Run/Stop in a menu, the palette or a shortcut.
- C4 (won't fix): menus hide rather than grey out. C19 (won't fix): Close buttons and Esc differ between tool windows.
- Test plan W-21 / S-21 (window place when closing to the tray): never ticked.

Things nothing owns
- The list of settings keys, their defaults and who may write each one (see K10).
- What `signal.configChanged` means: it is used for "any setting changed" and as a general reload trigger (Q12).
- Module Setup's window is kept in `Main.configureWin` (`Main.qml:165`), outside the shared window list in `window_registry.js`.

## 11. Size and test coverage

Size: about 9,500 lines across ~45 files. Python is ~6,300 lines (`joystick_gremlin.py` 1138, `option.py` 856, `live_debug.py` 916, `config.py` 551, `window_placement.py` 519, `update_model.py` 449, `system_tray.py` 332, the rest under 200 each, plus the folder part of `util.py` ~250). QML/JS is ~5,000 lines: `Main.qml` 1898 (roughly a third is shell; the rest is page loaders and room switching owned by other subsystems), `DialogLiveLog.qml` 690, `help_topics.js` 509, `ConfigGroup.qml` 348, the other Options and dialog files 30-240 each.

Covered by tests (about 40 files, ~250 tests):
- Start-up, second copy, could not start, off-screen and imports: `test_could_not_start.py` (3), `test_second_copy_detection.py` (10), `test_audit3_startup.py` (12), `test_audit2_startup_devices.py` (part), `test_program_imports.py`, `test_modules_import_alone.py`, `test_startup_messages.py` (9), `test_startup_settings_kept.py` (2), `test_restart_command.py` (2), `test_user_data_folder.py` (2), `test_open_folders.py` (4).
- Settings: `test_config.py` (4), `test_settings_file_damage.py` (7), `test_settings_versions.py` (3), `test_write_less.py` (8), `test_meta_config_option.py` (4).
- Options: `test_options_layout.py` (3), `test_option_list_saving.py` (3), `test_audit2_options_text.py` (part).
- Threads, errors, freeze: `test_threads.py` (9), `test_bounded_waits.py` (5), `test_error_report.py` (5), `test_watchdog.py` (4), `test_qt_log.py` (4).
- Logs: `test_live_log_debug.py` (9), `test_live_log_view.py` (3), `test_log_feed.py` (5).
- Updates: `test_update_check.py` (13), `test_update_model.py` (4), `test_program_fixes.py` (update and start-up part).
- Main window: `test_menus.py` (5), `test_main_window_fits.py` (4), `test_tray_memory.py` (3, off-screen), `test_help_guide.py` (6), `test_usability_fixes.py`, `test_data_safety.py`.

Obvious untested paths
- The tray in real use: Minimize to tray, the X hiding the window, the one-time balloon (`minimize-to-tray`, `tray-notice-shown`: no test names them), tray Exit, and Exit with Minimize to tray on (K2). Off-screen runs make no tray icon, so tests can't reach these.
- Closing the main window with a tool window open (K1).
- `main()`'s restart path (`QProcess.startDetached` after quit); only `restart_command` is tested.
- Changing the data folder or the logs folder (`data-folder`: no test), `ensure_data_folders`, and the silent fallback.
- A settings file that can't be written (K7); `_keep_damaged_file` when the rename itself fails.
- `threads.main_timer` / `MainTimer` (one indirect reference, no direct test).
- `UpdateModel.skipVersion` and `openReleasePage` (no test calls them; `should_offer` is tested).
- History Restore of a setting that acts at once (K8).
- Failures before `main()` (K4).

## 12. Review (user, 2026-10-06)

Approved by the user as recommended (2026-10-06, blanket approval of the remaining pages): every [code only] statement in section 8 is confirmed, except where a question's recommendation changes it; every question in section 9 is decided as its **Recommend** says. Where a recommendation and a section 8 statement disagree, the recommendation wins.

| Q | Decision |
|---|---|
| All | As recommended in section 9 |

The section 8 statements (with the changes above) are now the definition
of correct for this subsystem.
