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

import json
import re

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.signal import signal
from gremlin.types import PropertyType
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

SECTION = "button-map"

# What an option holds.
OptionValue = bool | int | float | str | list

# Groups in the order Options shows them.
GROUPS = ("labels", "editing", "autosave", "view", "export", "colours", "library")

# (group, name, type, default, description, properties). A name's number only
# orders the entries inside their group.
OPTIONS: list[tuple[str, str, PropertyType, OptionValue, str, dict]] = [
    (
        "labels", "01-chip-text", PropertyType.Selection, "Name",
        "What chips show. Name: the control's name, or the name you gave it. "
        "Action: what the control does in the profile, in the mode chosen under "
        "View > Labels mode. Name and action: both.",
        {"valid_options": ["Name", "Action", "Name and action"]},
    ),
    (
        "labels", "02-description-first", PropertyType.Bool, True,
        "When a control has a Description action, show its text instead of the "
        "text made from its other actions.",
        {},
    ),
    (
        "labels", "03-several-actions", PropertyType.Selection, "First",
        "A control with several actions shows the first one's text, or all of "
        "them joined with +.",
        {"valid_options": ["First", "All"]},
    ),
    (
        "labels", "04-unbound", PropertyType.Selection, "Name",
        "What a chip shows in Action mode when its control does nothing in that "
        "mode: its name, nothing, or a dash.",
        {"valid_options": ["Name", "Blank", "Dash"]},
    ),
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
        "editing", "05-mirror-pictures", PropertyType.Bool, False,
        "Mirror layout and Copy layout from also mirror pictures. Off, pictures "
        "only move, so text in them still reads.",
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
        "view", "02-rulers", PropertyType.Bool, False,
        "Show rulers along the top and left of the map while editing. Drag out "
        "of a ruler to add a guide. Also in View > Rulers.",
        {},
    ),
    (
        "view", "01-zoom-speed", PropertyType.Int, 100,
        "How fast the mouse wheel zooms the map, in percent of the usual speed.",
        {"min": 25, "max": 300},
    ),
    (
        "export", "01-export-size", PropertyType.Selection, "2x",
        "How much larger than on screen Export draws the page. Larger is sharper "
        "and makes bigger files.",
        {"valid_options": ["1x", "2x", "3x"]},
    ),
    (
        "export", "03-light-page", PropertyType.Bool, False,
        "Export on a white page for printing: dark colours turn light and light "
        "ones dark, keeping their hue. The photo is not changed. Also in File > "
        "Light page for printing.",
        {},
    ),
    (
        "export", "04-print-light", PropertyType.Bool, True,
        "File > Print prints on a white page with dark ink (see Light page), "
        "whatever the export setting.",
        {},
    ),
    (
        "export", "02-mode-title", PropertyType.Bool, True,
        "File > Export modes writes each mode's name at the top of its page.",
        {},
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
    cfg.register(
        SECTION, "internal", "styles", PropertyType.List, [],
        "Saved Button Map styles: [{name, kind, fields}].", {},
    )


# --- saved styles ----------------------------------------------------------------

# What a style can be saved from and applied to.
STYLE_KINDS = ("chip", "shape", "line", "text")


def styles() -> list[dict]:
    """Saved styles, by kind then name."""
    register()
    raw = Configuration().value(SECTION, "internal", "styles") or []
    out = [
        s for s in raw
        if isinstance(s, dict) and s.get("kind") in STYLE_KINDS
        and str(s.get("name") or "").strip() and isinstance(s.get("fields"), dict)
    ]
    return sorted(out, key=lambda s: (s["kind"], str(s["name"]).lower()))


def _store_styles(rows: list[dict]) -> None:
    register()
    Configuration().set(SECTION, "internal", "styles", rows)


def save_style(name: str, kind: str, fields: dict) -> bool:
    """Keeps a look under a name; one of the same name and kind is replaced."""
    clean = str(name or "").strip()
    if not clean or kind not in STYLE_KINDS:
        return False
    if not isinstance(fields, dict) or not fields:
        return False
    rows = [s for s in styles() if not (s["kind"] == kind and s["name"] == clean)]
    rows.append({"name": clean, "kind": kind, "fields": fields})
    _store_styles(rows)
    return True


def delete_style(name: str, kind: str) -> bool:
    rows = styles()
    kept = [s for s in rows if not (s["kind"] == kind and s["name"] == name)]
    if len(kept) == len(rows):
        return False
    _store_styles(kept)
    return True


def rename_style(name: str, kind: str, new_name: str) -> bool:
    clean = str(new_name or "").strip()
    rows = styles()
    if not clean or any(s["kind"] == kind and s["name"] == clean for s in rows):
        return False
    for s in rows:
        if s["kind"] == kind and s["name"] == name:
            s["name"] = clean
            _store_styles(rows)
            return True
    return False


class ButtonMapLibraryOption(QtCore.QObject, BaseMetaConfigOptionWidget):
    """Options → Button Map → Library: saved styles and templates."""

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionButtonMapLibrary.qml").fileName()


MetaConfigOption().register(
    SECTION,
    "library",
    "saved-styles-and-templates",
    "Styles saved from the Button Map's right-click menus, and layout "
    "templates (File > Templates). Rename or delete them here.",
    ButtonMapLibraryOption,
)


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

    @QtCore.Property(list, notify=changed)
    def styles(self) -> list:
        """Saved styles: [{name, kind, fields}]."""
        return styles()

    @QtCore.Slot(str, str, str, result=bool)
    def saveStyle(self, name: str, kind: str, fields_json: str) -> bool:
        try:
            fields = json.loads(fields_json)
        except ValueError:
            return False
        ok = save_style(name, kind, fields)
        if ok:
            signal.configChanged.emit()
        return ok

    @QtCore.Slot(str, str, result=bool)
    def deleteStyle(self, name: str, kind: str) -> bool:
        ok = delete_style(name, kind)
        if ok:
            signal.configChanged.emit()
        return ok

    @QtCore.Slot(str, str, str, result=bool)
    def renameStyle(self, name: str, kind: str, new_name: str) -> bool:
        ok = rename_style(name, kind, new_name)
        if ok:
            signal.configChanged.emit()
        return ok

    @QtCore.Slot(str, "QVariant")
    def set(self, key: str, new_value: object) -> None:
        if _entry(key) is None:
            return
        set_value(key, new_value)
        signal.configChanged.emit()
