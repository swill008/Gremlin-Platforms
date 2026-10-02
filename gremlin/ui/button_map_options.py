# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Button Map editor options.

They live in the program's configuration under the "button-map" section, so
Options lists them like any other setting; the Button Map window opens Options
at that section from Edit -> Editor options. QML reads them through
ButtonMapOptions, which is keyed by the option's name without its ordering
prefix ("01-undo-steps" -> "undo-steps").
"""

from __future__ import annotations

import re

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.signal import signal
from gremlin.types import PropertyType

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

SECTION = "button-map"

# What an option holds.
OptionValue = bool | int | float | str | list

# Groups in the order Options shows them.
GROUPS = ("labels", "editing", "autosave", "view", "export", "colours")

# (group, name, type, default, description, properties). A name's number only
# orders the entries inside their group.
OPTIONS: list[tuple[str, str, PropertyType, OptionValue, str, dict]] = [
    (
        "editing", "01-undo-steps", PropertyType.Int, 80,
        "How many steps Undo can go back while editing a map.",
        {"min": 20, "max": 500},
    ),
    (
        "editing", "02-rotate-snap", PropertyType.Int, 15,
        "Degrees per step when Shift is held while turning an item or drawing a line.",
        {"min": 1, "max": 90},
    ),
    (
        "editing", "03-press-to-find", PropertyType.Bool, True,
        "While editing, pressing a button or hat on the device selects its chip "
        "and scrolls to it. A control not on the map is shown in the pool.",
        {},
    ),
    (
        "editing", "04-find-axes", PropertyType.Bool, False,
        "Press to find also reacts to an axis pushed past halfway.",
        {},
    ),
    (
        "autosave", "01-autosave", PropertyType.Bool, True,
        "While you edit a map, keep a recovery copy of unsaved changes. After a "
        "crash, opening the device offers to restore them.",
        {},
    ),
    (
        "autosave", "02-autosave-seconds", PropertyType.Int, 60,
        "Seconds between recovery copies.",
        {"min": 10, "max": 600},
    ),
    (
        "export", "01-export-size", PropertyType.Selection, "2x",
        "How much larger than on screen Export draws the page. Larger is sharper "
        "and makes bigger files.",
        {"valid_options": ["1x", "2x", "3x"]},
    ),
    (
        "colours", "01-recent-colours", PropertyType.Int, 10,
        "How many recent colours the colour picker keeps.",
        {"min": 4, "max": 30},
    ),
]


def key_of(name: str) -> str:
    """The name QML uses: without the ordering number."""
    return re.sub(r"^[0-9]+-", "", name)


def register() -> None:
    """Registers every option; called at start-up before unused entries are
    purged, and by anything that reads an option."""
    cfg = Configuration()
    # An entry already stored keeps its value; its description and limits
    # are brought up to date.
    for group, name, kind, default, description, properties in OPTIONS:
        cfg.register(SECTION, group, name, kind, default, description, properties, True)


def _entry(key: str) -> tuple[str, str] | None:
    for group, name, *_rest in OPTIONS:
        if key_of(name) == key:
            return group, name
    return None


def value(key: str) -> OptionValue:
    """An option's current value, by its QML name."""
    found = _entry(key)
    if found is None:
        raise KeyError(key)
    cfg = Configuration()
    if not cfg.exists(SECTION, *found):
        register()
    return cfg.value(SECTION, *found)


def set_value(key: str, new_value: object) -> None:
    found = _entry(key)
    if found is None:
        raise KeyError(key)
    cfg = Configuration()
    if not cfg.exists(SECTION, *found):
        register()
    cfg.set(SECTION, *found, new_value)


def scale_of(text: object) -> int:
    """"2x" -> 2, for the export size."""
    match = re.match(r"\s*([123])", str(text or ""))
    return int(match.group(1)) if match else 2


@ta.QmlElement
class ButtonMapOptions(QtCore.QObject):
    """The Button Map options for QML: values[name], and set(name, value)."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        register()
        signal.configChanged.connect(self._on_config)

    @QtCore.Slot()
    def _on_config(self) -> None:
        self.changed.emit()

    @QtCore.Property("QVariantMap", notify=changed)
    def values(self) -> dict[str, OptionValue]:
        cfg = Configuration()
        return {
            key_of(name): cfg.value(SECTION, group, name)
            for group, name, *_rest in OPTIONS
            if cfg.exists(SECTION, group, name)
        }

    @QtCore.Slot(str, "QVariant")
    def set(self, key: str, new_value: object) -> None:
        if _entry(key) is None:
            return
        set_value(key, new_value)
        signal.configChanged.emit()
