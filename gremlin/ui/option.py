# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import (
    cast,
)

from PySide6 import QtCore

import gremlin.config
import gremlin.ui.type_aliases as ta
from gremlin.common import SingletonMetaclass
from gremlin.error import (
    GremlinError,
    MissingImplementationError,
)
from gremlin.signal import signal
from gremlin.tts import TTSManager
from gremlin.types import PropertyType

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1

SECTION_DISPLAY_NAMES = {
    "global": "Global",
    "ui": "User Interface (UI)",
    "action": "Action",
    "profile": "Profile",
    "osc": "OSC Connection",
    "display": "Display",
    "automap": "Auto Mapper",
    "button-map": "Button Map",
}

# Titles for entries whose key does not read well as a title; any other
# entry shows its key with spaces ("zoom-speed" -> "Zoom speed").
_ENTRY_TITLES = {
    "ui-scale": "UI scale",
    "disable-windows-scaling": "Ignore Windows display scaling",
    "show-stubs": "Show devices without a module",
    "last-keep-after-release": "Keep last value after release",
    "debug": "Diagnostic logs",
    "hidhide-on-start": "Turn HidHide on at start",
    "autorelease-no-arg": "Auto-release address-only messages",
    "pad-args": "Treat address-only messages as 1.0",
    "delay-presets": "Auto-release delay presets",
    "plugin-directory": "Plugins folder",
    "autosave-seconds": "Seconds between recovery copies",
    "remain-active-on-focus-loss": "Keep running when the program loses focus",
    "enable-auto-loading": "Load profiles automatically",
    "auto-loading": "Programs and their profiles",
    "resolution-mode": "Mode cycle resolution",
    "unbound": "No actions",
}

# Group order inside a section; others follow by name.
_GROUP_ORDER = {
    "general": 0, "files": 1, "input-names": 2,
    # Button Map (gremlin/ui/button_map_options.py)
    "labels": 10, "editing": 11, "autosave": 12, "view": 13, "export": 14,
    "colours": 15, "library": 16,
}


@ta.QmlElement
class ConfigSectionModel(QtCore.QAbstractListModel):
    """Exposes the sections present in the configuration as a list model."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"groupModel"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._config = gremlin.config.Configuration()
        self._option = MetaConfigOption()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._combined_sections())

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> ConfigGroupModel | str | None:
        if role not in self.roles:
            return None

        sections = self._combined_sections()
        if index.row() >= len(sections):
            return None

        match cast(str, self.roles[role]):
            case "name":
                raw = sections[index.row()]
                return SECTION_DISPLAY_NAMES.get(raw, raw)
            case "groupModel":
                return ConfigGroupModel(sections[index.row()])

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _combined_sections(self) -> list[str]:
        def priority(name: str) -> int:
            match name:
                case "global":
                    return 0
                case "ui":
                    return 1
                case "action":
                    return 2
                case "profile":
                    return 3
                case "osc":
                    return 4
                case "display":
                    return 5
                case "automap":
                    return 6
                case "button-map":
                    return 7
                case _:
                    return 99

        return list(
            sorted(set(self._config.sections() + self._option.sections()), key=priority)
        )


@ta.QmlElement
class ConfigGroupModel(QtCore.QAbstractListModel):
    """Exposes the groups present in a specific configuration section as a
    list model.
    """

    changed = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"groupName"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"entryModel"),
    }

    def __init__(self, section: str, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._config = gremlin.config.Configuration()
        self._option = MetaConfigOption()
        self._section_name = section

    @QtCore.Property(str, notify=changed)
    def sectionName(self) -> str:
        return self._section_name

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._combined_groups())

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> ConfigEntryModel | str | None:
        groups = self._combined_groups()
        if index.row() >= len(groups):
            return None

        match cast(str, self.roles[role]):
            case "entryModel":
                return ConfigEntryModel(self._section_name, groups[index.row()])
            case "groupName":
                return groups[index.row()]
            case _:
                return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _combined_groups(self) -> list[str]:
        names = set(
            self._config.groups(self._section_name)
            + self._option.groups(self._section_name)
        )
        return sorted(names, key=lambda name: (_GROUP_ORDER.get(name, 50), name))


@ta.QmlElement
class ConfigEntryModel(QtCore.QAbstractListModel):
    """Exposes the entries in a section's group as a list model."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"data_type"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"value"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"description"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"properties"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"name"),
    }

    def __init__(self, section: str, group: str, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._config = gremlin.config.Configuration()
        self._option = MetaConfigOption()
        self._section_name = section
        self._group_name = group

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._combined_entries())

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        entries = self._combined_entries()
        if not index.isValid() or index.row() >= len(entries):
            return None

        value = None
        if role in self.roles:
            role_name = bytes(self.roles[role].data()).decode()

            name = entries[index.row()]
            if role_name == "name":
                name = re.sub(r"^[0-9]+-", "", name)
                if name in _ENTRY_TITLES:
                    return _ENTRY_TITLES[name]
                return re.sub(r"[_-]+", " ", name).capitalize()
            if name in self._option.entries(self._section_name, self._group_name):
                match role_name:
                    case "description":
                        value = self._option.description(
                            self._section_name, self._group_name, name
                        )
                    case "value":
                        value = self._option.qml_widget(
                            self._section_name, self._group_name, name
                        )().qml_path
                    case "data_type":
                        value = "meta_option"
            elif self._config.exists(self._section_name, self._group_name, name):
                key = [self._section_name, self._group_name, entries[index.row()]]
                value = self._config.get(*key, role_name)
                if role_name == "value":
                    if self._config.data_type(*key) == PropertyType.Path:
                        value = str(value)
                if isinstance(value, PropertyType):
                    value = PropertyType.to_string(value)
        return value

    def setData(
        self,
        index: ta.ModelIndex,
        value: str,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        entries = self._combined_entries()
        if not index.isValid() or index.row() >= len(entries):
            return False

        name = entries[index.row()]
        if not self._config.exists(self._section_name, self._group_name, name):
            raise GremlinError(
                "Cannot set data for non-config entry "
                + f"{self._section_name}.{self._group_name}.{name}"
            )

        if self.roles[role] == "value":
            key = [self._section_name, self._group_name, entries[index.row()]]
            if self._config.data_type(*key) == PropertyType.Path:
                value = Path(value)

            self._config.set(*key, value)
            self.dataChanged.emit(index, index, [role])
            signal.configChanged.emit()
            return True
        return False

    def flags(self, index: ta.ModelIndex) -> QtCore.Qt.ItemFlag:
        return super().flags(index) | QtCore.Qt.ItemFlag.ItemIsEditable

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _combined_entries(self) -> list[str]:
        return list(
            sorted(
                set(
                    self._config.entries(self._section_name, self._group_name)
                    + self._option.entries(self._section_name, self._group_name)
                )
            )
        )


class BaseMetaConfigOptionWidget:
    @property
    def qml_path(self) -> str:
        return self._qml_path()

    def _qml_path(self) -> str:
        raise MissingImplementationError(
            "BaseMetaConfigOptionWidget: Subclasses must implement the "
            + "qml_path method."
        )


@ta.QmlElement
class ActionSequenceOrdering(QtCore.QAbstractListModel, BaseMetaConfigOptionWidget):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"visible"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"index"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QAbstractListModel.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

        self._config = gremlin.config.Configuration()
        self._cfg_key = ["action", "general", "action-priorities"]

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._config.value(*self._cfg_key))

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> bool | int | str:
        if role not in self.roles:
            raise GremlinError("Invalid role encountered")

        data = self._config.value(*self._cfg_key)[index.row()]
        match cast(str, self.roles[role]):
            case "name":
                return data[0]
            case "visible":
                return data[1]
            case "index":
                return index.row()
            case _:
                raise GremlinError(f"Unknown role name {role}")

    def setData(
        self,
        index: ta.ModelIndex,
        value: bool,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        data = self._config.value(*self._cfg_key)
        match cast(str, self.roles[role]):
            case "visible":
                data[index.row()][1] = value
                self._config.set(*self._cfg_key, data)
                return True
            case "index":
                return False
            case _:
                return False

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Slot(int, int)
    def move(self, source_index: int, target_index: int) -> None:
        """Moves the row to sit just before target_index (as shown before the move)."""
        if source_index < target_index:
            # The rows below the source shift up once it is taken out.
            target_index -= 1
        if source_index == target_index:
            return
        self.layoutAboutToBeChanged.emit()
        data = self._config.value(*self._cfg_key)
        item = data.pop(source_index)
        data.insert(target_index, item)
        self._config.set(*self._cfg_key, data)
        self.layoutChanged.emit()

    def _qml_path(self) -> str:
        return (
            "file:///" + QtCore.QFile("qml:OptionActionSequenceOrdering.qml").fileName()
        )


@ta.QmlElement
class ProfileAutoLoadingModel(QtCore.QAbstractListModel, BaseMetaConfigOptionWidget):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"profile"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"executable"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"isEnabled"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QAbstractListModel.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

        self._config = gremlin.config.Configuration()
        self._cfg_key = ["profile", "automation", "entries-auto-loading"]

    @QtCore.Slot()
    def newEntry(self) -> None:
        """Creates a new empty auto-load entry."""
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        data = self._config.value(*self._cfg_key)
        data.append(["", "", False])
        self._config.set(*self._cfg_key, data)
        self.endInsertRows()

    @QtCore.Slot(int)
    def removeEntry(self, index: int) -> None:
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        data = self._config.value(*self._cfg_key)
        del data[index]
        self._config.set(*self._cfg_key, data)
        self.endRemoveRows()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._config.value(*self._cfg_key))

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> bool | str:
        data = self._config.value(*self._cfg_key)[index.row()]
        match cast(str, self.roles[role]):
            case "profile":
                return data[0]
            case "executable":
                return data[1]
            case "isEnabled":
                return data[2]
            case _:
                raise GremlinError(f"Unknown role name {role}")

    def setData(
        self,
        index: ta.ModelIndex,
        value: bool | str,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        data = self._config.value(*self._cfg_key)
        match cast(str, self.roles[role]):
            case "profile":
                data[index.row()][0] = value
                self._config.set(*self._cfg_key, data)
                return True
            case "executable":
                data[index.row()][1] = value
                self._config.set(*self._cfg_key, data)
                return True
            case "isEnabled":
                data[index.row()][2] = value
                self._config.set(*self._cfg_key, data)
                return True
            case _:
                return False

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionProfileAutoLoading.qml").fileName()


@ta.QmlElement
class TTSVoiceSelectionModel(QtCore.QAbstractListModel, BaseMetaConfigOptionWidget):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
    }

    currentIndexChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QAbstractListModel.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

        TTSManager().start()
        self._voices = [voice.name() for voice in TTSManager().available_voices()]
        self._config = gremlin.config.Configuration()
        self._cfg_key = ["action", "text-to-speech", "voice"]

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._voices)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if role == QtCore.Qt.ItemDataRole.UserRole + 1:
            return self._voices[index.row()]
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionTTSVoiceSelection.qml").fileName()

    def _get_current_index(self) -> int:
        try:
            return self._voices.index(self._config.value(*self._cfg_key))
        except ValueError:
            return 0

    def _set_current_index(self, index: int) -> None:
        if not (0 <= index < len(self._voices)):
            return
        self._config.set(*self._cfg_key, self._voices[index])
        TTSManager().update_voice(self._voices[index])
        self.currentIndexChanged.emit()

    currentIndex = QtCore.Property(
        int,
        fget=_get_current_index,
        fset=_set_current_index,
        notify=currentIndexChanged,
    )


class MetaConfigOption(metaclass=SingletonMetaclass):
    def __init__(self) -> None:
        self._options = {}

    def count(self) -> int:
        return len(self._options)

    def register(
        self,
        section: str,
        group: str,
        name: str,
        description: str,
        qml_widget: type[BaseMetaConfigOptionWidget],
    ) -> None:
        key = (section, group, name)
        if key in self._options:
            logging.getLogger("system").warning(
                f"Option {section}.{group}.{name} already registered."
            )
            return

        self._options[key] = {"description": description, "qml_widget": qml_widget}

    def sections(self) -> list[str]:
        return list(set(section for section, _, _ in self._options.keys()))

    def groups(self, section: str) -> list[str]:
        return list(
            set(group for sec, group, _ in self._options.keys() if sec == section)
        )

    def entries(self, section: str, group: str) -> list[str]:
        return list(
            name
            for sec, grp, name in self._options.keys()
            if sec == section and grp == group
        )

    def qml_widget(
        self, section: str, group: str, name: str
    ) -> type[BaseMetaConfigOptionWidget]:
        return cast(
            type[BaseMetaConfigOptionWidget],
            self._retrieve_value(section, group, name, "qml_widget"),
        )

    def description(self, section: str, group: str, name: str) -> str | None:
        return cast(str, self._retrieve_value(section, group, name, "description"))

    def _retrieve_value(
        self, section: str, group: str, name: str, entry: str
    ) -> str | type[BaseMetaConfigOptionWidget]:
        key = (section, group, name)
        if key not in self._options:
            raise GremlinError(f"No option with key {key} exists.")

        match entry:
            case "description":
                return self._options[key]["description"]
            case "qml_widget":
                return self._options[key]["qml_widget"]
            case _:
                raise GremlinError(f"Unknown entry '{entry}' requested.")


MetaConfigOption().register(
    "action",
    "general",
    "action-list",
    "Reorder the order in which actions appear in the drop down menu as desired "
    "by dragging and dropping them in the list. Actions that are not desired "
    "can be turned off via the switch next to each action.",
    ActionSequenceOrdering,
)

MetaConfigOption().register(
    "profile",
    "automation",
    "auto-loading",
    "Automatically load profiles based on the currently active executable. "
    "Each entry an executable and the profile to load with it. The executable "
    "can be changed manually if needed. This also allows specifying the path "
    "to an executable as a regular expression.",
    ProfileAutoLoadingModel,
)

MetaConfigOption().register(
    "action",
    "text-to-speech",
    "voice-selection",
    "Voices available for use with Text to Speech actions.",
    TTSVoiceSelectionModel,
)

import gremlin.ui.menu_preview_option  # noqa: E402, F401
import gremlin.ui.ui_scale_option  # noqa: F401
import gremlin.ui.windows_scale_option  # noqa: F401
