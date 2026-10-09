# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import copy
import logging
import re
from pathlib import Path
from typing import (
    Any,
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
    "display": "Home",
    "automap": "Auto Mapper",
    "button-map": "Button Map",
}

# Titles for entries whose key does not read well as a title; any other
# entry shows its key with spaces ("zoom-speed" -> "Zoom speed").
_ENTRY_TITLES = {
    "ui-scale": "UI scale",
    "refresh-axis-on-activation": "Refresh axes when Run starts",
    "keep-days": "Days to keep changes",
    "max-megabytes": "Largest history file (MB)",
    "disable-windows-scaling": "Ignore Windows display scaling",
    "show-stubs": "Show devices without a module",
    "last-keep-after-release": "Keep last value after release",
    "debug": "Diagnostic logs",
    # The Diagnostic logs level (not a row of its own; recorded for History).
    "log-level": "Diagnostic logs",
    "log-when-not-responding": "Log When Not Responding",
    # Not shown in Options (the HidHide window has the switch); History
    # names it by the switch's own words.
    "hidhide-on-start": "HidHide Automatically Start",
    "hidhide-start": "HidHide",
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
    "recent-colours": "Recent colors",
    "display-mode": "Input names",
    "action-list": "Actions offered",
    # The Actions offered list's stored order (History names it).
    "action-priorities": "Actions offered",
    "action-sequence-information": "Action details",
}

# Where the main Options window shows each setting: sidebar sections, their
# groups, and the stored keys in each (section, group, name). Showing a
# setting somewhere else never changes its stored key. A registered setting
# missing from here still shows, under "Other" at the end of its section's
# page, so nothing disappears; _HIDDEN lists the ones that must not show.
_LAYOUT: list[tuple[str, list[tuple[str, list[tuple[str, str, str]]]]]] = [
    ("General", [
        ("Startup and Tray", [
            ("global", "general", "check-for-updates"),
            ("global", "general", "minimize-to-tray"),
            # Only a pointer: the switch is in the HidHide window (02 Q16).
            ("global", "general", "hidhide-start"),
        ]),
        ("Devices", [
            ("global", "general", "device-change-behavior"),
            ("global", "general", "refresh-axis-on-activation"),
            ("global", "general", "refresh-axis-on-mode-change"),
        ]),
        ("Diagnostics", [
            ("global", "general", "debug"),
            ("global", "general", "log-when-not-responding"),
        ]),
        ("History", [
            ("global", "history", "keep-days"),
            ("global", "history", "max-megabytes"),
        ]),
    ]),
    ("Interface", [
        ("Display", [
            ("ui", "general", "dark-mode"),
            ("ui", "general", "ui-scale"),
            ("ui", "general", "disable-windows-scaling"),
        ]),
        ("Inputs", [
            ("ui", "general", "display-mode"),
            ("ui", "general", "input-highlighting"),
            ("global", "general", "action-sequence-information"),
        ]),
    ]),
    ("Actions", [
        ("Add Action Menu", [("action", "general", "action-list")]),
        ("Macro", [("action", "macro", "default-delay")]),
        ("Change Mode", [("action", "change-mode", "resolution-mode")]),
        ("Double Tap", [("action", "double-tap", "duration")]),
        ("Smart Toggle", [("action", "smart-toggle", "duration")]),
        ("Tempo", [("action", "tempo", "duration")]),
        ("Axis Delta", [("action", "axis-delta", "threshold")]),
        ("Play Sound", [("action", "play-sound", "playback-mode")]),
        ("Text to Speech", [("action", "text-to-speech", "voice-selection")]),
    ]),
    ("Profiles", [
        ("Auto-load", [
            ("profile", "automation", "enable-auto-loading"),
            ("profile", "automation", "auto-loading"),
            ("profile", "automation", "remain-active-on-focus-loss"),
        ]),
    ]),
    ("Home", [
        ("Cards", [
            ("display", "status", "compact-view"),
            ("display", "status", "show-stubs"),
            ("display", "status", "last-keep-after-release"),
            ("display", "status", "reset-card-sizes"),
        ]),
    ]),
    ("OSC", [
        # OSC's settings are in its own file, edited in OSC › Module Setup
        # (D-09-OSC-FILE point 4); Options only points there.
        ("", [("osc", "connection", "module-setup")]),
    ]),
    ("Folders", [
        # Each folder its own untitled card, the page showing between them.
        ("", [("global", "files", "data-folder")]),
        ("", [("global", "files", "profiles-folder")]),
        ("", [("global", "files", "modules-folder")]),
        ("", [("global", "files", "scripts-folder")]),
        ("", [("global", "files", "export-folder")]),
        ("", [("global", "files", "logs-folder")]),
        ("", [("global", "files", "history-folder")]),
        ("", [("global", "files", "plugin-directory")]),
    ]),
]

# Choices shown in other words than they are stored (the stored value never
# changes, so saved settings keep working): Device change behavior's
# "Disable" is Stop (glossary Run / Stop; 02 Q2).
_SHOWN_CHOICES: dict[tuple[str, str, str], dict[str, str]] = {
    ("global", "general", "device-change-behavior"): {"Disable": "Stop"},
}


def shown_choice(key: tuple[str, str, str], stored: Any) -> Any:  # noqa: ANN401
    """A Selection setting's stored value as Options shows it."""
    if not isinstance(stored, str):
        return stored
    return _SHOWN_CHOICES.get(key, {}).get(stored, stored)


def stored_choice(key: tuple[str, str, str], shown: Any) -> Any:  # noqa: ANN401
    """The stored value of a Selection setting's choice as Options shows it."""
    for stored, text in _SHOWN_CHOICES.get(key, {}).items():
        if shown == text:
            return stored
    return shown


# Stored values that are not settings to show: the Action list's raw data,
# and HidHide's Automatically Start (switched in the HidHide window only,
# 02 Q16; still stored, and History still records it).
_HIDDEN = {
    ("action", "general", "action-priorities"),
    ("global", "general", "hidhide-on-start"),
    # Chosen in Device Library Settings only (10 S37, 01 S124).
    ("global", "files", "device-library-folder"),
}

# Sections with a window of their own (the Button Map's options).
_OWN_WINDOW = {"button-map"}

# Which sidebar section an unplaced setting's stored section belongs to.
_HOME_OF = {
    "global": "General", "ui": "Interface", "action": "Actions",
    "profile": "Profiles", "display": "Home", "osc": "OSC",
}


def _shown_keys() -> list[tuple[str, str, str]]:
    """Every setting that can show in an Options window, from the registry."""
    cfg = gremlin.config.Configuration()
    option = MetaConfigOption()
    keys: set[tuple[str, str, str]] = set()
    for section in set(cfg.sections() + option.sections()):
        for group in set(cfg.groups(section) + option.groups(section)):
            names = cfg.entries(section, group) + option.entries(section, group)
            for name in set(names):
                keys.add((section, group, name))
    return sorted(keys - _HIDDEN)


def main_layout() -> list[tuple[str, list[tuple[str, list[tuple[str, str, str]]]]]]:
    """The main Options window's sections, groups and settings: _LAYOUT, plus
    any registered setting it does not place (under "Other"), minus settings
    that are not registered here (an option module not loaded)."""
    available = set(_shown_keys())
    placed = {key for _s, groups in _LAYOUT for _g, keys in groups for key in keys}
    out = []
    for title, groups in _LAYOUT:
        shown = [(g, [k for k in keys if k in available]) for g, keys in groups]
        extra = sorted(
            key for key in available - placed
            if key[0] not in _OWN_WINDOW and _HOME_OF.get(key[0], "General") == title
        )
        if extra:
            shown.append(("Other", extra))
        shown = [(g, keys) for g, keys in shown if keys]
        if shown:
            out.append((title, shown))
    return out

# Headings for groups whose stored key is spelled differently (glossary: US).
_GROUP_TITLES = {
    "colours": "colors",
}


def entry_title(name: str, key: str = "") -> str:
    """An option's name as Options shows it ("01-chip-text" -> "Chip text").
    key ("section/group/name", for History): a name Options shows in more
    than one group gets its group's title first ("Tempo duration")."""
    shown = re.sub(r"^[0-9]+-", "", name)
    if shown in _ENTRY_TITLES:
        title = _ENTRY_TITLES[shown]
    else:
        title = re.sub(r"[_-]+", " ", shown).capitalize()
    group = _repeated_name_group(key) if key else ""
    if group:
        # "Duration" -> "Tempo duration"; "UI scale" keeps its capitals.
        if not title[:2].isupper():
            title = title[:1].lower() + title[1:]
        title = f"{group} {title}"
    return title


def _repeated_name_group(key: str) -> str:
    """The Options group title of a setting whose name repeats in _LAYOUT
    (Double Tap, Smart Toggle and Tempo each have a "duration"), else ""."""
    parts = tuple(str(key).split("/", 2))
    if len(parts) != 3:
        return ""
    names = [k[2] for _s, groups in _LAYOUT for _g, keys in groups for k in keys]
    if names.count(parts[2]) < 2:
        return ""
    for _section, groups in _LAYOUT:
        for group, keys in groups:
            if parts in keys:
                return group
    return ""


def group_title(name: str) -> str:
    """A group's heading as Options shows it ("colours" -> "Colors")."""
    return str(_GROUP_TITLES.get(name, name)).capitalize()

# Group order inside a section; others follow by name.
_GROUP_ORDER = {
    "general": 0, "files": 1, "input-names": 2,
    # Button Map (gremlin/ui/button_map_options.py)
    "labels": 10, "editing": 11, "autosave": 12, "view": 13, "export": 14,
    "colours": 15, "library": 16,
}


# What JavaScript's String.trim() removes.
_JS_SPACE = (
    " \t\n\v\f\r\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007"
    "\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)


def _js_trim(text: str) -> str:
    return text.strip(_JS_SPACE)


@ta.QmlElement
class ConfigSectionModel(QtCore.QAbstractListModel):
    """The sections an Options window lists, each with its groups.

    scope "" is the main Options window: the sections of main_layout(). Any
    other scope is one stored section shown on its own (the Button Map's
    options window uses "button-map").
    """

    scopeChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"groupModel"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._scope = ""
        self._main_sections: list[tuple[str, list | None]] | None = None

    def _get_scope(self) -> str:
        return self._scope

    def _set_scope(self, value: str) -> None:
        if value != self._scope:
            self.beginResetModel()
            self._scope = value
            self.endResetModel()
            self.scopeChanged.emit()

    scope = QtCore.Property(str, fget=_get_scope, fset=_set_scope, notify=scopeChanged)

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._sections())

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> ConfigGroupModel | str | None:
        if role not in self.roles:
            return None
        sections = self._sections()
        if index.row() >= len(sections):
            return None
        title, groups = sections[index.row()]
        match cast(str, self.roles[role]):
            case "name":
                return title
            case "groupModel":
                if groups is None:
                    return ConfigGroupModel(self._scope)
                return ConfigGroupModel(self._scope, groups=groups)
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Slot(str, result=list)
    def matchingSections(self, text: str) -> list[int]:  # noqa: N802 (QML)
        """Rows of the sections with a setting the search text finds, matched
        as ConfigGroup.matches does, from the models alone (no QML built)."""
        needle = _js_trim(text).lower()
        if not needle:
            return []
        return [
            row
            for row, (_title, groups) in enumerate(self._sections())
            if ConfigGroupModel(self._scope, groups=groups).matches(needle)
        ]

    def _settings(self) -> list[tuple[int, str, str, str]]:
        """(section row, group title, on-screen label, History-style label)
        of every setting, in page order."""
        name_role = QtCore.Qt.ItemDataRole.UserRole + 5
        out = []
        for row, (_title, groups) in enumerate(self._sections()):
            group_model = ConfigGroupModel(self._scope, groups=groups)
            for title, keys, stored in group_model._combined_groups():
                entries = ConfigEntryModel(self._scope, stored, keys=keys)
                for index, key in enumerate(entries._keys):
                    label = str(entries.data(entries.index(index), name_role) or "")
                    if label:
                        full = entry_title(key[2], "/".join(key))
                        out.append((row, title, label, full))
        return out

    @QtCore.Slot(result=list)
    def settingLabels(self) -> list[str]:  # noqa: N802 (QML)
        """Every setting's on-screen label, once each, in page order (Help's
        show:option/<label> links)."""
        labels: list[str] = []
        for _row, _group, label, _full in self._settings():
            if label not in labels:
                labels.append(label)
        return labels

    @QtCore.Slot(str, result=list)
    def findSetting(self, label: str) -> list:  # noqa: N802 (QML)
        """[section row, group title, on-screen label] of the setting with
        this label (any case; a repeated label such as "Duration" also by its
        group's name, "Tempo duration"), else []."""
        needle = _js_trim(label).lower()
        if not needle:
            return []
        settings = self._settings()
        for row, group, shown, _full in settings:
            if shown.lower() == needle:
                return [row, group, shown]
        for row, group, shown, full in settings:
            if full.lower() == needle:
                return [row, group, shown]
        return []

    def _sections(self) -> list[tuple[str, list | None]]:
        if self._scope:
            return [(SECTION_DISPLAY_NAMES.get(self._scope, self._scope), None)]
        # main_layout() walks the whole registry; Qt asks for the sections
        # many times while the window opens, so build it once per model. A
        # new model is made each time an Options window opens.
        if self._main_sections is None:
            self._main_sections = [
                (title, groups) for title, groups in main_layout()
            ]
        return self._main_sections


@ta.QmlElement
class ConfigGroupModel(QtCore.QAbstractListModel):
    """The groups of one Options page. With groups given, they are display
    groups of (title, keys); otherwise the stored groups of the section."""

    changed = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"groupName"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"entryModel"),
    }

    def __init__(
        self,
        section: str,
        parent: ta.OQO = None,
        groups: list[tuple[str, list[tuple[str, str, str]]]] | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = gremlin.config.Configuration()
        self._option = MetaConfigOption()
        self._section_name = section
        self._groups = groups

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

        title, keys, stored = groups[index.row()]
        match cast(str, self.roles[role]):
            case "entryModel":
                return ConfigEntryModel(self._section_name, stored, keys=keys)
            case "groupName":
                return title
            case _:
                return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def matches(self, needle: str) -> bool:
        """Some row of some group contains needle (trimmed, lower case)."""
        name_role = QtCore.Qt.ItemDataRole.UserRole + 5
        text_role = QtCore.Qt.ItemDataRole.UserRole + 3
        for title, keys, stored in self._combined_groups():
            # As ConfigGroup.qml: "Other" only gathers, so its title never counts.
            heading = "" if title == "Other" else title
            entries = ConfigEntryModel(self._section_name, stored, keys=keys)
            for row in range(entries.rowCount()):
                ix = entries.index(row)
                name = entries.data(ix, name_role) or ""
                try:
                    text = entries.data(ix, text_role) or ""
                except KeyError:
                    # A stored setting without a description: the page
                    # shows none either.
                    text = ""
                if needle in f"{heading} {name} {text}".lower():
                    return True
        return False

    def _combined_groups(
        self,
    ) -> list[tuple[str, list[tuple[str, str, str]] | None, str]]:
        """(heading, keys or None, stored group name) for each group."""
        if self._groups is not None:
            return [(title, keys, title) for title, keys in self._groups]
        names = set(
            self._config.groups(self._section_name)
            + self._option.groups(self._section_name)
        )
        ordered = sorted(names, key=lambda name: (_GROUP_ORDER.get(name, 50), name))
        # Shown as the group's heading; the stored key itself never changes.
        return [
            (str(_GROUP_TITLES.get(name, name)), None, str(name)) for name in ordered
        ]


@ta.QmlElement
class ConfigEntryModel(QtCore.QAbstractListModel):
    """The settings of one Options group. With keys given, exactly those
    (section, group, name) settings in that order; otherwise every setting
    stored in the section's group."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"data_type"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"value"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"description"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"properties"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"name"),
    }

    def __init__(
        self,
        section: str,
        group: str,
        parent: ta.OQO = None,
        keys: list[tuple[str, str, str]] | None = None,
    ) -> None:
        super().__init__(parent)

        self._config = gremlin.config.Configuration()
        self._option = MetaConfigOption()
        self._section_name = section
        self._group_name = group
        if keys is None:
            stored = set(
                self._config.entries(section, group)
                + self._option.entries(section, group)
            )
            keys = [(section, group, name) for name in sorted(stored)]
        self._keys = [key for key in keys if key not in _HIDDEN]

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._keys)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: ANN401  (a value, its text or its properties)
        if (
            not index.isValid()
            or index.row() >= len(self._keys)
            or role not in self.roles
        ):
            return None
        section, group, name = self._keys[index.row()]
        role_name = bytes(self.roles[role].data()).decode()
        if role_name == "name":
            return entry_title(name)
        value = None
        # A custom widget wins over a stored value of the same name.
        if name in self._option.entries(section, group):
            match role_name:
                case "description":
                    value = self._option.description(section, group, name)
                case "value":
                    value = self._option.qml_widget(section, group, name)().qml_path
                case "data_type":
                    value = "meta_option"
        elif self._config.exists(section, group, name):
            key = (section, group, name)
            value = self._config.get(section, group, name, role_name)
            if role_name == "value":
                if self._config.data_type(section, group, name) == PropertyType.Path:
                    value = str(value)
                value = shown_choice(key, value)
            elif role_name == "properties" and key in _SHOWN_CHOICES:
                value = dict(value)
                value["valid_options"] = [
                    shown_choice(key, v) for v in value.get("valid_options", [])
                ]
            if isinstance(value, PropertyType):
                value = PropertyType.to_string(value)
        return value

    def setData(
        self,
        index: ta.ModelIndex,
        value: str,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid() or index.row() >= len(self._keys):
            return False
        section, group, name = self._keys[index.row()]
        if not self._config.exists(section, group, name):
            raise GremlinError(
                f"Cannot set data for non-config entry {section}.{group}.{name}"
            )
        if self.roles[role] == "value":
            if self._config.data_type(section, group, name) == PropertyType.Path:
                value = Path(value)
            value = stored_choice((section, group, name), value)
            self._config.set(section, group, name, value)
            self.dataChanged.emit(index, index, [role])
            signal.configChanged.emit()
            return True
        return False

    def flags(self, index: ta.ModelIndex) -> QtCore.Qt.ItemFlag:
        return super().flags(index) | QtCore.Qt.ItemFlag.ItemIsEditable

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles


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
        # A copy: editing the stored list in place would defeat set()'s
        # "changed?" check and save every time.
        data = copy.deepcopy(self._config.value(*self._cfg_key))
        match cast(str, self.roles[role]):
            case "visible":
                data[index.row()][1] = value
                self._config.set(*self._cfg_key, data)
                self.dataChanged.emit(index, index, [role])
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
        # A copy: editing the stored list in place would defeat set()'s
        # "changed?" check and save every time.
        data = copy.deepcopy(self._config.value(*self._cfg_key))
        item = data.pop(source_index)
        data.insert(target_index, item)
        self._config.set(*self._cfg_key, data)
        self.layoutChanged.emit()

    @QtCore.Slot(int, bool)
    def setShown(self, row: int, shown: bool) -> None:
        """Offers the action in the Add Action menu, or not."""
        self.setData(self.index(row, 0), shown, QtCore.Qt.ItemDataRole.UserRole + 2)

    @QtCore.Slot("QVariantList", int, int)
    def moveAmong(self, rows: list, source: int, before: int) -> None:
        """Reorders one kind of action among its own rows: source goes just
        before the row before (-1: after the last). Every other action keeps
        its place, so the order across kinds (the first three are the quick
        adds in an action's menu) stays as it was."""
        rows = [int(r) for r in rows]
        if source not in rows or source == before:
            return
        order = [r for r in rows if r != source]
        order.insert(order.index(before) if before in order else len(order), source)
        if order == rows:
            return
        self.layoutAboutToBeChanged.emit()
        # A copy: editing the stored list in place would defeat set()'s
        # "changed?" check and save every time.
        data = copy.deepcopy(self._config.value(*self._cfg_key))
        items = [data[r] for r in order]
        for slot, item in zip(rows, items):
            data[slot] = item
        self._config.set(*self._cfg_key, data)
        self.layoutChanged.emit()

    @QtCore.Slot()
    def resetDefaults(self) -> None:
        """The order and choice a new install starts with: Map to vJoy, Macro
        and Response Curve first, the rest by name, every one offered."""
        first = ["Map to vJoy", "Macro", "Response Curve"]
        names = [name for name, _shown in self._config.value(*self._cfg_key)]
        rest = sorted(n for n in names if n not in first)
        ordered = [n for n in first if n in names] + rest
        self.beginResetModel()
        self._config.set(*self._cfg_key, [[name, True] for name in ordered])
        self.endResetModel()

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
        # A copy: editing the stored list in place would defeat set()'s
        # "changed?" check and save every time.
        data = copy.deepcopy(self._config.value(*self._cfg_key))
        data.append(["", "", False])
        self._config.set(*self._cfg_key, data)
        self.endInsertRows()

    @QtCore.Slot(int)
    def removeEntry(self, index: int) -> None:
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        # A copy: editing the stored list in place would defeat set()'s
        # "changed?" check and save every time.
        data = copy.deepcopy(self._config.value(*self._cfg_key))
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
        # A copy: editing the stored list in place would defeat set()'s
        # "changed?" check and save every time.
        data = copy.deepcopy(self._config.value(*self._cfg_key))
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


_DEFAULT_VOICE = "(default)"


@ta.QmlElement
class TTSVoiceSelectionModel(QtCore.QAbstractListModel, BaseMetaConfigOptionWidget):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
    }

    currentIndexChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QAbstractListModel.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

        TTSManager().prepare_engine()
        # Row 0 is the system's default voice: shown when none is saved or
        # the saved one is no longer installed (09 Q12, S59).
        self._voices = [_DEFAULT_VOICE] + [
            voice.name() for voice in TTSManager().available_voices()
        ]
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
        saved = self._config.value(*self._cfg_key)
        if saved and saved in self._voices[1:]:
            return self._voices.index(saved, 1)
        return 0

    def _set_current_index(self, index: int) -> None:
        if not (0 <= index < len(self._voices)):
            return
        name = self._voices[index] if index > 0 else ""
        self._config.set(*self._cfg_key, name)
        TTSManager().update_voice(name)
        self.currentIndexChanged.emit()

    currentIndex = QtCore.Property(
        int,
        fget=_get_current_index,
        fset=_set_current_index,
        notify=currentIndexChanged,
    )


class OptionPointer(BaseMetaConfigOptionWidget):
    """An Options row that only explains where a setting lives: its text is
    the description, no control."""

    def _qml_path(self) -> str:
        return ""


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
    "Choose which actions the Add Action menu offers. Drag one by its handle "
    "to change its place among its kind.",
    ActionSequenceOrdering,
)

MetaConfigOption().register(
    "profile",
    "automation",
    "auto-loading",
    "Each program and the profile it loads. A program's path can be typed "
    "by hand, or written as a regular expression to match several.",
    ProfileAutoLoadingModel,
)

MetaConfigOption().register(
    "action",
    "text-to-speech",
    "voice-selection",
    "Voices available for use with Text to Speech actions.",
    TTSVoiceSelectionModel,
)

MetaConfigOption().register(
    "global",
    "general",
    "hidhide-start",
    "To turn HidHide on each time the program starts, use Automatically "
    "Start in Tools → Device Setup → HidHide.",
    OptionPointer,
)

import gremlin.ui.ui_scale_option  # noqa: F401
import gremlin.ui.windows_scale_option  # noqa: F401
