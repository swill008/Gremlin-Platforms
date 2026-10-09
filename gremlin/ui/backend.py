# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path

from PySide6 import (
    QtCore,
    QtGui,
    QtQml,
)

import dill
import gremlin.ui.type_aliases as ta
from gremlin import (
    audio_player,
    code_runner,
    common,
    config,
    device_helpers,
    device_initialization,
    error,
    event_handler,
    mode_manager,
    process_monitor,
    profile,
    profile_recovery,
    shared_state,
    user_script,
    util,
)
from gremlin.logical_device import LogicalDevice
from gremlin.osc import OSC_DEVICE_UUID
from gremlin.signal import (
    display_error,
    signal,
)
from gremlin.ui.device import InputIdentifier
from gremlin.ui.hardware_profile import persist_log
from gremlin.ui.profile import InputItemModel
from gremlin.ui.script import ScriptListModel
from gremlin.ui import ui_scale_option
from gremlin.ui.util import (
    save_image_as_pdf,
    to_local_path,
    updated_recent_profiles,
)
import gremlin.ui.hardware_profile  # noqa: F401

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

_max_recent_profiles = 5


@ta.QmlElement
class UIState(QtCore.QObject):
    deviceChanged = QtCore.Signal()
    inputChanged = QtCore.Signal()
    modeChanged = QtCore.Signal()
    tabChanged = QtCore.Signal()
    roomChanged = QtCore.Signal()
    themeRevisionChanged = QtCore.Signal()
    selectIndex = QtCore.Signal(int)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._current_device = dill.UUID_Invalid
        self._current_input = {}
        self._current_mode = "Default"
        self._current_tab = "physical"
        self._current_room = "status"
        self._theme_revision = 0
        event_handler.EventListener().device_change_event.connect(self._device_change)
        signal.profileChanged.connect(self._device_change)
        # Keys are the profile's own: the old profile's key, kept as the
        # current input, was re-created in the new one by the editor.
        signal.profileChanged.connect(self.clearKeyboardInput)

    def _device_change(self) -> None:
        if self._current_room == "status":
            return
        if self._current_tab != "physical":
            return
        devices = device_initialization.physical_devices()
        selection_valid = False
        for dev in devices:
            if dev.device_guid.uuid == self._current_device:
                selection_valid = True
                break
        if not selection_valid:
            if len(devices) > 0:
                self.setCurrentDevice(str(devices[0].device_guid))
            else:
                self.setCurrentDevice(str(dill.UUID_Invalid))
                self.setCurrentTab("logical")

    @QtCore.Property(str, constant=True)
    def logicalDeviceGuid(self) -> str:
        """The Logical Device's id, for QML (it was typed out in two files)."""
        return str(LogicalDevice.device_guid)

    @QtCore.Property(str, constant=True)
    def oscDeviceGuid(self) -> str:
        """OSC's device id, for QML (its Module Setup opens from Options)."""
        return str(OSC_DEVICE_UUID)

    @QtCore.Slot(str)
    def setCurrentDevice(self, device_name: str) -> None:
        raw = str(device_name or "").replace("{", "").replace("}", "").strip()
        if not raw:
            return
        try:
            device_uuid = uuid.UUID(raw)
        except ValueError:
            return
        if device_uuid != self._current_device:
            self._current_device = device_uuid
            self.deviceChanged.emit()
            self.inputChanged.emit()

    @QtCore.Slot(InputIdentifier, int)
    def setCurrentInput(self, input: InputIdentifier, index: int) -> None:
        if input is None:
            return
        value = (input, index)
        if value != self._current_input.get(input.device_guid, None):
            self._current_input[input.device_guid] = value
            self.inputChanged.emit()

    @QtCore.Slot()
    def clearKeyboardInput(self) -> None:
        """No key is selected (the last one was deleted, or another profile
        loaded): the editor kept the old key, and editing it re-created it."""
        if self._current_input.pop(dill.UUID_Keyboard, None) is not None:
            self.inputChanged.emit()

    @QtCore.Slot(str)
    def setCurrentMode(self, mode_name: str) -> None:
        if mode_name != self._current_mode:
            self._current_mode = mode_name
            self.modeChanged.emit()
            self.inputChanged.emit()

    @QtCore.Slot(str)
    def setCurrentTab(self, tab: str) -> None:
        if tab != self._current_tab:
            self._current_tab = tab
            self.tabChanged.emit()

    @QtCore.Slot(str)
    def setCurrentRoom(self, room: str) -> None:
        name = room or "status"
        if name != self._current_room:
            self._current_room = name
            self.roomChanged.emit()

    @QtCore.Slot()
    def bumpThemeRevision(self) -> None:
        self._theme_revision += 1
        self.themeRevisionChanged.emit()

    @QtCore.Property(str, notify=deviceChanged)
    def currentDevice(self) -> str:
        return str(self._current_device).upper()

    @QtCore.Property(InputIdentifier, notify=inputChanged)
    def currentInput(self) -> InputIdentifier:
        return self._current_input.get(self._current_device, (InputIdentifier(), 0))[0]

    @QtCore.Property(int, notify=inputChanged)
    def currentInputIndex(self) -> int:
        return self._current_input.get(self._current_device, (InputIdentifier(), 0))[1]

    @QtCore.Property(str, notify=modeChanged)
    def currentMode(self) -> str:
        return self._current_mode

    @QtCore.Property(str, notify=tabChanged)
    def currentTab(self) -> str:
        return self._current_tab

    @QtCore.Property(str, notify=roomChanged)
    def currentRoom(self) -> str:
        return self._current_room

    @QtCore.Property(int, notify=themeRevisionChanged)
    def themeRevision(self) -> int:
        return self._theme_revision

    def __str__(self) -> str:
        cur_input = self._current_input.get(
            self._current_device, (InputIdentifier(), 0)
        )
        return (
            f"{self._current_device} {cur_input[0].input_id} "
            + f"{cur_input[1]}  {self._current_tab}"
        )


def _open_folder(folder: str) -> None:
    """Shows a folder in Explorer."""
    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))


def _same_file(a: str | Path | None, b: str | Path | None) -> bool:
    """The same file, however the paths are written (a Path and a str were
    never equal, so auto-load reloaded the open profile at every focus)."""
    if not a or not b:
        return False
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


def _sync_run_highlight_hold(runner: code_runner.CodeRunner) -> None:
    """Run holds input highlighting off while it runs; Stop lets go of only
    its own hold, so Calibration, OSC Add, Listen or Record still hold
    theirs (03 S114)."""
    if runner.is_running():
        shared_state.hold_input_highlighting("run")
    else:
        shared_state.release_input_highlighting("run")


def _load_logical_device() -> None:
    """Fills LogicalDevice() from its module file (D-04-LD-FILE)."""
    from gremlin import logical_device_file

    try:
        logical_device_file.load()
    except Exception:
        logging.getLogger("system").exception("Could not read the Logical Device file")


def _logical_unsaved() -> bool:
    """The Logical Device has edits its file doesn't have yet."""
    return bool(getattr(LogicalDevice(), "dirty", False))


def logical_migration_text(added: list[str] | None) -> str:
    """The one-time note after a version 14 profile's Logical Device moved
    to the shared file; "" when nothing was added."""
    names = [str(name) for name in (added or []) if str(name)]
    if not names:
        return ""
    return "Logical Device moved to its own file: added " + ", ".join(names) + "."


def _load_osc_device() -> None:
    """Fills OscDevice() and its server settings from OSC's module file;
    the first time, the settings are copied from the configuration
    (D-09-OSC-FILE)."""
    from gremlin import osc_device_file

    log = logging.getLogger("system")
    try:
        osc_device_file.migrate_settings_from_config()
    except Exception:
        log.exception("Could not copy the OSC settings to OSC's file")
    try:
        osc_device_file.load()
    except Exception:
        log.exception("Could not read OSC's file")


def _osc_unsaved() -> bool:
    """OSC's address list has edits its file doesn't have yet."""
    from gremlin.osc import OscDevice

    rows = getattr(OscDevice(), "rows", None)
    return bool(getattr(rows, "dirty", False))


def _internal_unsaved() -> bool:
    """The shared internal devices (Logical Device, OSC) have edits that
    Save writes too."""
    return _logical_unsaved() or _osc_unsaved()


def osc_migration_text(added: list[str] | None) -> str:
    """The one-time note after an older profile's OSC rows moved to OSC's
    file; "" when nothing was added."""
    names = [str(name) for name in (added or []) if str(name)]
    if not names:
        return ""
    return "OSC addresses moved to OSC's own file: added " + ", ".join(names) + "."


def migration_notes(new_profile: object) -> tuple[str, str]:
    """(title, text) of the one note said after opening an older profile
    whose Logical Device and/or OSC rows moved to their own files; text ""
    when there is nothing to say."""
    logical = logical_migration_text(
        getattr(new_profile, "logical_migration_note", None)
    )
    osc = osc_migration_text(getattr(new_profile, "osc_migration_note", None))
    if logical and osc:
        return "Open Profile", logical + " " + osc
    if osc:
        return "OSC", osc
    return "Logical Device", logical


@common.SingletonDecorator
class Backend(QtCore.QObject):
    windowTitleChanged = QtCore.Signal()
    profileChanged = QtCore.Signal()
    recentProfilesChanged = QtCore.Signal()
    inputConfigurationChanged = QtCore.Signal()
    activityChanged = QtCore.Signal()
    propertyChanged = QtCore.Signal()
    uiChanged = QtCore.Signal()
    quitRequested = QtCore.Signal()
    saveNoted = QtCore.Signal(str)
    # The profile used last didn't open at start: (its path, why).
    lastProfileFailed = QtCore.Signal(str, str)
    # A Recent entry that didn't open: (its path, why); Main.qml offers
    # Forget It / Keep, as at start (GL-157).
    recentProfileFailed = QtCore.Signal(str, str)
    uiScaleChanged = QtCore.Signal()
    restartRequested = QtCore.Signal()
    # A recovery copy waits to be offered (takeRecoveryOffer, 04 S94).
    recoveryOfferChanged = QtCore.Signal()
    # Something the "*" covers changed outside the profile (a Logical page
    # edit): Main.qml checks the "*" again.
    unsavedChanged = QtCore.Signal()

    def __init__(
        self, engine: QtQml.QQmlApplicationEngine, parent: ta.OQO = None
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.config = config.Configuration()
        # One Logical Device for every profile, read from its module file
        # once, before any profile (D-04-LD-FILE, 04 S2).
        _load_logical_device()
        # OSC's address list and server settings likewise (D-09-OSC-FILE).
        _load_osc_device()
        self.profile = profile.Profile()
        self.profile.mark_clean()
        shared_state.current_profile = self.profile
        self._last_error = ""
        # Why the last _load_profile(report=False) failed.
        self._load_problem = ""
        # Read by main() after the event loop ends; set only by the quit path.
        self.restart_on_exit = False
        self._action_state = {}
        # Auto-load target held back by unsaved edits (said once).
        self._autoload_held: str | None = None
        self.runner = code_runner.CodeRunner()
        self.ui_state = UIState(self)
        self.process_monitor = process_monitor.ProcessMonitor()
        # Connected before the monitor starts: the program in front at start
        # was missed (GL-129, 02 G21).
        self.process_monitor.process_changed.connect(self._active_process_changed_cb)
        # It runs only while auto-load is on (02 Q19).
        self._sync_process_monitor()
        signal.configChanged.connect(self._sync_process_monitor)
        # The Configuration pane's models: the newest few are kept (05 RB18).
        self._editor_models: list[InputItemModel] = []
        self.joystick_change_monitor = device_helpers.JoystickInputSignificant()
        mm = mode_manager.ModeManager()
        mm.mode_changed.connect(self._on_mode_changed)
        # One handler, in order: the open profile first, then its modes.
        self.profileChanged.connect(self._profile_change_handler)
        # Signal to signal: let go of when this Backend is deleted (a lambda
        # would stay connected and fail on a deleted Backend).
        event_handler.EventHandler().is_active.connect(self.activityChanged)
        event_handler.EventListener().device_change_event.connect(self._device_change)
        event_handler.EventListener().joystick_event.connect(self._highlight_input)
        signal.uiScaleChanged.connect(self.uiScaleChanged)
        # A Logical page edit changes the "*" (04 S2: Save writes it).
        signal.logicalDeviceModified.connect(self.unsavedChanged)
        # So does an OSC page edit (D-09-OSC-FILE).
        signal.oscDeviceModified.connect(self.unsavedChanged)
        # Recovery copies of unsaved edits, kept about every minute (04 S94).
        self._recovery = profile_recovery.ProfileRecovery()
        self._recovery_offer: dict | None = None
        self._recovery_timer = QtCore.QTimer(self)
        self._recovery_timer.setInterval(
            int(profile_recovery.INTERVAL_SECONDS * 1000)
        )
        self._recovery_timer.timeout.connect(self._keep_recovery_copy)
        self._recovery_timer.start()
        app = QtCore.QCoreApplication.instance()
        if app is not None:
            # A clean close: this session's copies go.
            app.aboutToQuit.connect(self._recovery.forget_session)
        self.profileChanged.emit()

    def _highlight_input(self, event: event_handler.Event) -> None:
        if (
            not self.config.value("ui", "general", "input-highlighting")
            or shared_state.suspend_input_highlighting()
        ):
            return
        if event.device_guid == OSC_DEVICE_UUID:
            return
        # Events the program makes (macro steps, refresh axes, Hat as
        # Buttons) are not the hardware moving (GL-244).
        if getattr(event, "synthetic", False):
            return
        if not self.joystick_change_monitor.should_process(event):
            return
        if self.ui_state.currentRoom == "status":
            return
        # Highlighting stays on the device page that is open.
        current_input = self.ui_state.currentInput
        same_device = (
            current_input is not None
            and current_input.device_guid == event.device_guid
        )
        if self.ui_state.currentTab != "physical" or not same_device:
            return
        try:
            new_input = InputIdentifier(
                event.device_guid, event.event_type, event.identifier
            )
            signal.setInputIndex.emit(new_input.linear_index)
        except Exception:
            return

    def _profile_change_handler(self) -> None:
        # The open profile is set first: the start mode is worked out from
        # it, not from the profile open before (04 S52, GL-053).
        shared_state.current_profile = self.profile
        # The Logical Device and OSC stay as they are: each one list from
        # its own file, loaded at start, for every profile (D-04-LD-FILE,
        # D-09-OSC-FILE).
        user_script.forget_other_scripts(self.profile.scripts.scripts)
        mm = mode_manager.ModeManager()
        mm.reset()
        self.ui_state.setCurrentMode(mm.current.name)
        self.windowTitleChanged.emit()
        signal.reloadUi.emit()
        signal.profileChanged.emit()

    def _device_change(self) -> None:
        behavior = self.config.value("global", "general", "device-change-behavior")
        match behavior:
            case "Disable":
                self.activate_gremlin(False)
            case "Ignore":
                pass
            case "Reload":
                if self.gremlinActive:
                    self.activate_gremlin(False)
                    self.activate_gremlin(True)

    def _on_mode_changed(self, name: str) -> None:
        self.ui_state.setCurrentMode(str(name or ""))
        self.propertyChanged.emit()

    @QtCore.Slot(str)
    def selectMode(self, mode_name: str) -> None:
        name = str(mode_name or "")
        if name not in self.profile.modes.mode_names():
            return
        self.ui_state.setCurrentMode(name)
        mm = mode_manager.ModeManager()
        if mm.current.name != name:
            mm.switch_to(mode_manager.Mode(name, mm.current.name))

    @QtCore.Slot()
    def openProgramFolder(self) -> None:
        """File -> Open Program Folder: where Gremlin-Platforms is."""
        _open_folder(util.program_folder())

    @QtCore.Slot()
    def openDataFolder(self) -> None:
        """File -> Open Data Folder: profiles, modules and settings (the
        folder chosen in Options, by default Gremlin Platforms in the user's
        profile)."""
        _open_folder(util.data_folder())

    @QtCore.Slot()
    def requestRestart(self) -> None:
        """Quit through the normal path, then start Gremlin again."""
        self.restartRequested.emit()

    @QtCore.Slot(bool)
    def setRestartOnExit(self, restart: bool) -> None:
        self.restart_on_exit = bool(restart)

    @QtCore.Slot()
    def emitConfigChanged(self) -> None:
        signal.configChanged.emit()
        audio_player.AudioPlayer().refresh()

    def _sync_process_monitor(self) -> None:
        """Watches the program in front only while auto-load is on."""
        if self.config.value("profile", "automation", "enable-auto-loading"):
            self.process_monitor.start()
        else:
            self.process_monitor.stop()

    def _active_process_changed_cb(self, path: str) -> None:
        if not self.config.value("profile", "automation", "enable-auto-loading"):
            return
        # The program's own window is no change: clicking into it stopped
        # the Run (GL-130, 02 Q18).
        if _same_file(path, sys.executable):
            return
        profile_path = config.get_profile_with_regex(path)
        if profile_path and not os.path.isfile(profile_path):
            # Its profile is gone: say so once, and don't run the open one
            # in its place (it kept running: this game got the last game's
            # bindings), unless it is set to keep running.
            if self._autoload_held != profile_path:
                self._autoload_held = profile_path
                signal.showNotification.emit(
                    "Auto-load",
                    f"{Path(profile_path).name} was not loaded: the file is missing.",
                )
            if self.gremlinActive and not self.config.value(
                "profile", "automation", "remain-active-on-focus-loss"
            ):
                self.activate_gremlin(False)
            return
        if profile_path:
            if not _same_file(self.profile.fpath, profile_path):
                if self.profile.has_unsaved_changes():
                    # The open profile isn't this program's: it stops, as
                    # when the file is missing (GL-150, 04 Q3).
                    if self.gremlinActive and not self.config.value(
                        "profile", "automation", "remain-active-on-focus-loss"
                    ):
                        self.activate_gremlin(False)
                    # Never switch over unsaved edits; say so once per profile.
                    if self._autoload_held != profile_path:
                        self._autoload_held = profile_path
                        signal.showNotification.emit(
                            "Auto-load Waited",
                            f"{Path(profile_path).name} was not loaded because "
                            "the open profile has unsaved changes. Save or "
                            "discard them and auto-load switches next time.",
                        )
                    return
                self._autoload_held = None
                self.activate_gremlin(False)
                self.loadProfile(profile_path)
            if not self.gremlinActive:
                self.activate_gremlin(True)
        else:
            if not self.config.value(
                "profile", "automation", "remain-active-on-focus-loss"
            ):
                self.activate_gremlin(False)

    @QtCore.Property(str, notify=propertyChanged)
    def gremlinVersion(self) -> str:
        return util.get_code_version()

    @QtCore.Property(UIState, notify=uiChanged)
    def uiState(self) -> UIState:
        return self.ui_state

    @QtCore.Property(bool, notify=activityChanged)
    def gremlinPaused(self) -> bool:
        return not event_handler.EventHandler().process_callbacks

    @QtCore.Property(bool, notify=activityChanged)
    def gremlinActive(self) -> bool:
        return self.runner.is_running()

    @QtCore.Slot()
    def toggleActiveState(self) -> None:
        self.activate_gremlin(not self.runner.is_running())

    def activate_gremlin(self, activate: bool) -> None:
        """Run (True) or Stop (False). A Run that fails stops itself and
        shows its one error (CodeRunner.start); the status then reads
        Stopped (06 Q5)."""
        try:
            if activate:
                shared_state.hold_input_highlighting("run")
                try:
                    self.runner.start(self.profile, self.ui_state.currentMode)
                except Exception:
                    # Logged and shown by the runner, which has stopped.
                    pass
            else:
                self.runner.stop()
        finally:
            _sync_run_highlight_hold(self.runner)
            self.activityChanged.emit()

    def run_profile(self, fpath: str) -> bool:
        """Stop, open the profile at fpath and Run it (a Load Profile
        action, handed over after its event). Runs again only when the
        profile opened; False when it didn't."""
        local_path = to_local_path(fpath)
        loaded = self._load_profile(str(local_path))
        if loaded:
            self._record_profile_use(local_path)
        self.profileChanged.emit()
        signal.reloadCurrentInputItem.emit()
        if loaded:
            self.activate_gremlin(True)
        return loaded

    def minimize(self) -> None:
        root_window = self.engine.rootObjects()[0]
        root_window.setVisibility(QtGui.QWindow.Visibility.Minimized)

    @QtCore.Slot(InputIdentifier, result=int)
    def getActionCount(self, identifier: InputIdentifier) -> int:
        if identifier is None:
            return 0
        try:
            item = self.profile.get_input_item(
                identifier.device_guid,
                identifier.input_type,
                identifier.input_id,
                self.ui_state.currentMode,
                False,
            )
            return len(item.action_sequences)
        except error.ProfileError:
            return 0

    @QtCore.Slot(InputIdentifier, int, result=InputItemModel)
    def getInputItem(
        self, identifier: InputIdentifier, enumeration_index: int
    ) -> InputItemModel | None:
        # No input selected (a deleted key, a new profile): nothing to show.
        if identifier is None or not identifier.isValid:
            return None
        try:
            item = self.profile.get_input_item(
                identifier.device_guid,
                identifier.input_type,
                identifier.input_id,
                self.ui_state.currentMode,
                True,
            )
        except error.ProfileError:
            return None
        if item is None:
            return None
        return self._editor_model(item, enumeration_index)

    # The one pane that asks for these shows the newest; it asks twice when
    # it opens. Older ones were kept for the whole session (05 RB18).
    _KEPT_EDITOR_MODELS = 4

    def _editor_model(
        self, item: profile.InputItem, enumeration_index: int
    ) -> InputItemModel:
        """A new model for the Configuration pane; the oldest beyond the
        newest few is freed."""
        model = InputItemModel(item, enumeration_index, self)
        self._editor_models.append(model)
        while len(self._editor_models) > self._KEPT_EDITOR_MODELS:
            self._editor_models.pop(0).deleteLater()
        return model

    @QtCore.Slot(str)
    def pauseInputHighlighting(self, holder: str) -> None:
        """Pauses input highlighting until every holder has resumed it
        (the holds are kept in shared_state, with Run, Listen and Record)."""
        shared_state.hold_input_highlighting(holder)

    @QtCore.Slot(str)
    def resumeInputHighlighting(self, holder: str) -> None:
        shared_state.release_input_highlighting(holder)

    @QtCore.Slot(str, int, result=bool)
    def isActionExpanded(self, uuid_str: str, index: int) -> bool:
        return self._action_state.get((uuid.UUID(uuid_str), index), True)

    @QtCore.Slot(str, int, bool)
    def setIsActionExpanded(self, uuid_str: str, index: int, is_expanded: bool) -> None:
        self._action_state[(uuid.UUID(uuid_str), index)] = bool(is_expanded)

    @QtCore.Property(bool, notify=propertyChanged)
    def useDarkMode(self) -> bool:
        return self.config.value("ui", "general", "dark-mode")

    @QtCore.Property(int, notify=uiScaleChanged)
    def uiScale(self) -> int:
        return ui_scale_option.active_scale()

    @QtCore.Property(type=list, notify=recentProfilesChanged)
    def recentProfiles(self) -> list[str]:
        return self.config.value("global", "internal", "recent-profiles")

    def _keep_recovery_copy(self) -> None:
        try:
            self._recovery.tick(self.profile)
        except Exception:
            logging.getLogger("system").exception("Keeping the recovery copy")

    def _set_recovery_offer(self, offer: dict | None) -> None:
        self._recovery_offer = offer
        self.recoveryOfferChanged.emit()

    @QtCore.Slot(result="QVariantMap")
    def takeRecoveryOffer(self) -> dict:
        """The recovery copy to offer for the open profile ({path, name,
        savedAt}), once; {} when none."""
        offer = self._recovery_offer
        self._recovery_offer = None
        return dict(offer) if offer else {}

    @QtCore.Slot(str, result=bool)
    def restoreRecovery(self, fpath: str) -> bool:
        """Restore: the open profile (fpath, "" for Untitled) becomes its
        recovery copy, unsaved."""
        path = fpath or None
        current = self.profile.fpath
        # Only the open profile's copy; an Untitled one (offered at start
        # with the last profile open) replaces a profile with no edits.
        key = profile_recovery.profile_key
        if key(current) != key(path) and (
            path is not None or self.profile.has_unsaved_changes()
        ):
            return False
        restored = self._recovery.restore(path, self.profile)
        if restored is None:
            signal.showNotification.emit(
                "Unsaved Edits Found", "The unsaved edits could not be read."
            )
            return False
        self.activate_gremlin(False)
        self.profile = restored
        if path:
            folder = os.path.dirname(str(path))
            if folder not in sys.path:
                sys.path.insert(0, folder)
        self.profileChanged.emit()
        self.windowTitleChanged.emit()
        self.propertyChanged.emit()
        signal.reloadCurrentInputItem.emit()
        return True

    @QtCore.Slot()
    def discardLogicalDevice(self) -> None:
        """Discard on the save-changes question: the Logical Device's edits
        go with the profile's, read again from its file (D-04-LD-FILE)."""
        if not _logical_unsaved():
            return
        _load_logical_device()
        # Its Undo steps would play the discarded edits again.
        signal.logicalDeviceReloaded.emit()
        signal.logicalDeviceModified.emit()

    @QtCore.Slot()
    def discardOscDevice(self) -> None:
        """Discard on the save-changes question: OSC's address edits go
        with the profile's, read again from OSC's file (D-09-OSC-FILE)."""
        if not _osc_unsaved():
            return
        _load_osc_device()
        # Its OSC page Undo steps would play the discarded edits again.
        signal.oscDeviceReloaded.emit()
        signal.oscDeviceModified.emit()

    @QtCore.Slot(str)
    def discardRecovery(self, fpath: str) -> None:
        """Discard: the recovery copy of fpath ("" for Untitled) goes."""
        self._recovery.discard(fpath or None)

    @QtCore.Slot()
    def newProfile(self) -> None:
        self.activate_gremlin(False)
        # The open profile's edits were saved or discarded (or there were
        # none): this session's recovery copies go.
        self._recovery.forget_session()
        self.profile = profile.Profile()
        self.profile.mark_clean()
        self._set_recovery_offer(self._recovery.offer_for(None))
        self.profileChanged.emit()
        self.windowTitleChanged.emit()
        signal.reloadCurrentInputItem.emit()
        signal.reloadUi.emit()

    @QtCore.Slot(result=list)
    def unfinishedActions(self) -> list[str]:
        """Unfinished actions a save would leave out of the file, so the
        screens can ask before saving."""
        try:
            return self.profile.library.unfinished_actions()
        except Exception:
            logging.getLogger("system").exception("Listing unfinished actions")
            return []

    @QtCore.Slot(str, result=bool)
    def saveProfile(self, qml_url: str) -> bool:
        try:
            path = to_local_path(qml_url)
            if str(path) in ("", "."):
                return False
            # Written first: a save that fails leaves the profile on its file.
            self.profile.to_xml(path)
            self.profile.fpath = path
            if not os.path.isfile(str(self.profile.fpath)):
                persist_log(f"Persist profile save failed path={path!r} reason='file missing after write'")
                return False
            self._record_profile_use(path)
            self._recovery.saved(path)
            self.windowTitleChanged.emit()
            persist_log(f"Persist profile save ok path={path}")
            return True
        except Exception:
            persist_log(f"Persist profile save failed path={qml_url!r}")
            logging.getLogger("system").exception("Failed to save profile")
            return False

    @QtCore.Slot(str)
    def noteSave(self, text: str) -> None:
        self.saveNoted.emit(str(text or ""))

    @QtCore.Slot(QtGui.QImage, "QVariant", result=bool)
    def saveImageAsPdf(self, image: QtGui.QImage, url: QtCore.QUrl | str) -> bool:
        path = to_local_path(url)
        if save_image_as_pdf(image, path):
            return True
        signal.showNotification.emit(
            "Export PDF", f"Could not write {path}."
        )
        return False

    @QtCore.Slot(result=str)
    def profilesFolderUrl(self) -> str:
        return util.profiles_dir().as_uri()

    @QtCore.Slot(result=str)
    def scriptsFolderUrl(self) -> str:
        return util.scripts_dir().as_uri()

    @QtCore.Slot(result=str)
    def profilePath(self) -> str:
        path = self.profile.fpath
        return "" if path is None else str(path)

    @QtCore.Slot(str)
    def loadRecentProfile(self, fpath: str) -> None:
        """File > Recent: as loadProfile, but one that doesn't open (a file
        that is gone) is reported through recentProfileFailed, so Main.qml
        offers Forget It as at start, instead of the error box; the open
        profile stays (GL-157, 04 Q15, S19)."""
        local_path = to_local_path(fpath)
        if self._load_profile(str(local_path), report=False):
            self._record_profile_use(local_path)
            self._opened_by_user(local_path)
        else:
            self.recentProfileFailed.emit(str(local_path), self._load_problem)
        self.profileChanged.emit()
        signal.reloadCurrentInputItem.emit()

    @QtCore.Slot(str)
    def loadProfile(self, fpath: str) -> None:
        local_path = to_local_path(fpath)
        if self._load_profile(str(local_path)):
            self._record_profile_use(local_path)
            self._opened_by_user(local_path)
        self.profileChanged.emit()
        signal.reloadCurrentInputItem.emit()

    def _opened_by_user(self, path: Path) -> None:
        """A profile opened after Save / Discard: the copies this session
        kept of the one before go, and this one's copy (a crash's) is
        offered."""
        self._recovery.forget_session()
        self._set_recovery_offer(self._recovery.offer_for(path))

    def openLastProfile(self, fpath: str) -> None:
        """At start: open the profile used last. If it won't open, say why
        once and offer to forget it (lastProfileFailed), instead of the same
        error at every start."""
        local_path = to_local_path(fpath)
        if self._load_profile(str(local_path), report=False):
            self._record_profile_use(local_path)
            # At start: this profile's copy, else an Untitled one (offered
            # by newProfile before it).
            offer = self._recovery.offer_for(local_path)
            if offer is not None:
                self._set_recovery_offer(offer)
        else:
            self.lastProfileFailed.emit(str(local_path), self._load_problem)
        self.profileChanged.emit()
        signal.reloadCurrentInputItem.emit()

    @QtCore.Slot(str)
    def forgetProfile(self, fpath: str) -> None:
        """Takes a profile off the start-up and Recent lists (the file stays
        where it is)."""
        gone = Path(fpath).resolve()
        if str(self.config.value("global", "internal", "last-profile") or ""):
            last = Path(str(self.config.value("global", "internal", "last-profile")))
            if last.resolve() == gone:
                self.config.set("global", "internal", "last-profile", "")
        recent = list(self.config.value("global", "internal", "recent-profiles") or [])
        kept = [entry for entry in recent if Path(entry).resolve() != gone]
        if kept != recent:
            self.config.set("global", "internal", "recent-profiles", kept)
            self.recentProfilesChanged.emit()

    @QtCore.Property(bool, notify=propertyChanged)
    def profileContainsUnsavedChanges(self) -> bool:
        """Exact: what the Save / Discard / Cancel questions ask about.
        Edits to the Logical Device and OSC count: Save writes them too
        (04 S2, D-09-OSC-FILE)."""
        return self.profile.has_unsaved_changes() or _internal_unsaved()

    @QtCore.Property(bool, notify=propertyChanged)
    def profileLooksUnsaved(self) -> bool:
        """For the title's "*" (checked every 1.5 s): reuses the last answer
        while no edit was noted, so a large profile isn't rebuilt each time
        (04 Q19). An edit no hook sees makes the "*" late, never a question
        skipped: those use profileContainsUnsavedChanges."""
        return self.profile.looks_unsaved() or _internal_unsaved()

    @QtCore.Property(type=ScriptListModel, notify=profileChanged)
    def scriptListModel(self) -> ScriptListModel:
        return ScriptListModel(self.profile.scripts, self)

    @QtCore.Property(type=str, notify=propertyChanged)
    def currentMode(self) -> str:
        return mode_manager.ModeManager().current.name

    @QtCore.Property(type=str, notify=windowTitleChanged)
    def windowTitle(self) -> str:
        """The profile's file name (the full path is in File → Save As and
        the footer), or "Untitled" before its first save."""
        if self.profile and self.profile.fpath:
            return Path(self.profile.fpath).name
        return "Untitled"

    def _record_profile_use(self, path: Path) -> None:
        """Records the given profile as the most recently used one.

        Args:
            path: file path of the profile that was loaded or saved
        """
        self.config.set("global", "internal", "last-profile", str(path))
        self.config.set(
            "global",
            "internal",
            "recent-profiles",
            updated_recent_profiles(
                self.config.value("global", "internal", "recent-profiles"),
                path,
                _max_recent_profiles,
            ),
        )
        self.recentProfilesChanged.emit()

    def _read_profile(self, fpath: str) -> None:
        """Make the profile at fpath the open one; raises when it can't be
        read."""
        # A new Profile has its own OSC rows: the open one keeps its own if
        # this fails (GL-074). The Logical Device is shared (D-04-LD-FILE).
        new_profile = profile.Profile()
        new_profile.from_xml(Path(fpath))
        profile_folder = os.path.dirname(fpath)
        # Added once, in front; the rest keeps its order (it was made a set,
        # so a script folder's module could hide a library one at random).
        if profile_folder not in sys.path:
            sys.path.insert(0, profile_folder)
        self.profile = new_profile
        persist_log(f"Persist profile load path={fpath}")
        # What opened but won't run as saved (actions of an unknown type,
        # GL-105): said once, at load.
        for warning in getattr(new_profile, "load_warnings", []) or []:
            logging.getLogger("system").warning(warning)
            signal.showNotification.emit("Open Profile", warning)
        # An older profile's Logical Device / OSC rows moved to their own
        # files: said once, in one note, the first time it opens (04 S25,
        # D-04-LD-FILE, D-09-OSC-FILE).
        title, note = migration_notes(new_profile)
        if note:
            logging.getLogger("system").info(note)
            signal.showNotification.emit(title, note)

    def _load_profile(self, fpath: str, report: bool = True) -> bool:
        """Opens a profile; False if it couldn't. report=False: the reason is
        kept in _load_problem for the caller to show, not shown here."""
        self._load_problem = ""
        if not os.path.isfile(fpath):
            self._load_problem = "The file isn't there any more."
            if report:
                display_error(
                    f"Could not load the profile {fpath}: the file does not exist."
                )
            return False
        self.activate_gremlin(False)
        open_now = self.profile.fpath if self.profile else None
        previous = str(open_now) if open_now else ""
        try:
            self._read_profile(fpath)
        except Exception as e:
            # Any failure (bad XML, content this version can't read, a
            # missing plugin...): say so, and put back what was open, read
            # again from its file.
            logging.getLogger("system").exception(f"Failed to load profile {fpath}")
            reason = str(e) or type(e).__name__
            reopened = False
            if previous and previous != fpath and os.path.isfile(previous):
                try:
                    self._read_profile(previous)
                    reopened = True
                except Exception:
                    logging.getLogger("system").exception(
                        f"Failed to reopen profile {previous}"
                    )
            if not reopened:
                self.newProfile()
            self._load_problem = reason
            if report:
                display_error(
                    f"Could not load the profile {fpath}.",
                    reason + "\n\n" + (
                        f"The profile you had open ({previous}) is open again."
                        if reopened
                        else "A new, empty profile is open instead."
                    ),
                )
            return False
        return True
