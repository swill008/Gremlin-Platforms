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
    shared_state,
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
    uiScaleChanged = QtCore.Signal()
    restartRequested = QtCore.Signal()

    def __init__(
        self, engine: QtQml.QQmlApplicationEngine, parent: ta.OQO = None
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.config = config.Configuration()
        self.profile = profile.Profile()
        self.profile.mark_clean()
        shared_state.current_profile = self.profile
        self._last_error = ""
        # Read by main() after the event loop ends; set only by the quit path.
        self.restart_on_exit = False
        self._action_state = {}
        # Auto-load target held back by unsaved edits (said once).
        self._autoload_held: str | None = None
        # Windows holding input highlighting paused (OSC Add, Calibration).
        self._highlight_holders: set[str] = set()
        self.runner = code_runner.CodeRunner()
        self.ui_state = UIState(self)
        self.process_monitor = process_monitor.ProcessMonitor()
        self.process_monitor.start()
        self.joystick_change_monitor = device_helpers.JoystickInputSignificant()
        mm = mode_manager.ModeManager()
        mm.mode_changed.connect(self._on_mode_changed)
        self.profileChanged.connect(mm.reset)
        self.profileChanged.connect(
            lambda: self.ui_state.setCurrentMode(mm.current.name)
        )
        self.profileChanged.connect(self._profile_change_handler)
        self.process_monitor.process_changed.connect(self._active_process_changed_cb)
        event_handler.EventHandler().is_active.connect(
            lambda: self.activityChanged.emit()
        )
        event_handler.EventListener().device_change_event.connect(self._device_change)
        event_handler.EventListener().joystick_event.connect(self._highlight_input)
        signal.uiScaleChanged.connect(self.uiScaleChanged)
        self.profileChanged.emit()

    def _highlight_input(self, event: event_handler.Event) -> None:
        if (
            not self.config.value("ui", "general", "input-highlighting")
            or shared_state.suspend_input_highlighting()
        ):
            return
        if event.device_guid == OSC_DEVICE_UUID:
            return
        if not self.joystick_change_monitor.should_process(event):
            return
        from gremlin.ui.highlight_option import highlight_follows_any_device

        if self.ui_state.currentRoom == "status":
            return
        follow = highlight_follows_any_device()
        current_input = self.ui_state.currentInput
        same_device = (
            current_input is not None
            and current_input.device_guid == event.device_guid
        )
        if follow:
            if self.ui_state.currentTab != "physical" or not same_device:
                self.ui_state.setCurrentTab("physical")
                self.ui_state.setCurrentDevice(str(event.device_guid))
        else:
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
        shared_state.current_profile = self.profile
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

    def _emit_change(self) -> None:
        self.propertyChanged.emit()

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

    def _active_process_changed_cb(self, path: str) -> None:
        if not self.config.value("profile", "automation", "enable-auto-loading"):
            return
        profile_path = config.get_profile_with_regex(path)
        if profile_path:
            if self.profile.fpath != profile_path:
                if self.profile.has_unsaved_changes():
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
        if activate:
            shared_state.set_suspend_input_highlighting(True)
            self.runner.start(self.profile, self.ui_state.currentMode)
        else:
            self.runner.stop()
            if self.config.value("ui", "general", "input-highlighting"):
                shared_state.set_suspend_input_highlighting(False)
        self.activityChanged.emit()

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
        if identifier is None:
            return
        try:
            item = self.profile.get_input_item(
                identifier.device_guid,
                identifier.input_type,
                identifier.input_id,
                self.ui_state.currentMode,
                True,
            )
            return InputItemModel(item, enumeration_index, self)
        except error.ProfileError:
            pass

    @QtCore.Slot(str)
    def pauseInputHighlighting(self, holder: str) -> None:
        """Pauses input highlighting until every holder has resumed it."""
        self._highlight_holders.add(holder)
        shared_state.set_suspend_input_highlighting(True)

    @QtCore.Slot(str)
    def resumeInputHighlighting(self, holder: str) -> None:
        self._highlight_holders.discard(holder)
        if not self._highlight_holders:
            shared_state.set_suspend_input_highlighting(False)

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

    @QtCore.Slot()
    def newProfile(self) -> None:
        self.activate_gremlin(False)
        self.profile = profile.Profile()
        self.profile.mark_clean()
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
            if not path:
                return False
            self.profile.fpath = path
            self.profile.to_xml(self.profile.fpath)
            if not os.path.isfile(str(self.profile.fpath)):
                persist_log(f"Persist profile save failed path={path!r} reason='file missing after write'")
                return False
            self._record_profile_use(path)
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
    def loadProfile(self, fpath: str) -> None:
        local_path = to_local_path(fpath)
        if self._load_profile(str(local_path)):
            self._record_profile_use(local_path)
        self.profileChanged.emit()
        signal.reloadCurrentInputItem.emit()

    @QtCore.Property(bool, notify=propertyChanged)
    def profileContainsUnsavedChanges(self) -> bool:
        return self.profile.has_unsaved_changes()

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
        LogicalDevice().reset()
        new_profile = profile.Profile()
        profile_was_converted = new_profile.from_xml(Path(fpath))
        profile_folder = os.path.dirname(fpath)
        if profile_folder not in sys.path:
            sys.path = list(set(sys.path))
            sys.path.insert(0, profile_folder)
        self.profile = new_profile
        persist_log(f"Persist profile load path={fpath}")
        if profile_was_converted:
            self.profile.to_xml(Path(fpath))

    def _load_profile(self, fpath: str) -> bool:
        if not os.path.isfile(fpath):
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
            # missing plugin...): say so, and put back what was open. Reading
            # starts by resetting the Logical Device, so the old profile is
            # read again from its file.
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
