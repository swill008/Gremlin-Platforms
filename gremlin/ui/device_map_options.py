# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor options.

They live in the program's configuration under the "device-mapping-editor"
section, so Options lists them like any other setting; the Device Mapping
Editor opens Options at that section from Edit -> Device Map Options. QML
reads them through DeviceMapOptions, which is keyed by the option's name
without its ordering prefix ("01-undo-steps" -> "undo-steps").
"""

from __future__ import annotations

import json
import re
import typing

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.signal import signal
from gremlin.types import PropertyType
from gremlin.ui.option import (
    BaseMetaConfigOptionWidget,
    MetaConfigOption,
    entry_title,
    group_title,
)

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

SECTION = "device-mapping-editor"

# What an option holds.
OptionValue = bool | int | float | str | list

# Groups in the order Options shows them.
GROUPS = (
    "labels", "editing", "right-click", "recovery", "view", "colours", "library",
)

# Headings that differ from group_title(key).
_GROUP_HEADINGS = {"right-click": "Right-click menu"}

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
        "Mirror Layout and Copy Device Map from Device also mirror pictures. "
        "Off, pictures only move, so text in them still reads.",
        {},
    ),
    (
        "editing", "06-chip-only", PropertyType.Bool, False,
        "Chip only: a chip added from the pool is placed on its own, with no "
        "leader and no hotspot. Add them later from the chip's menu (Leader → "
        "Add Leader, Hotspot → Hide Hotspot).",
        {},
    ),
    (
        "right-click", "01-favourites-shown", PropertyType.Int, 5,
        "How many favourites the top of the right-click menu shows (0 turns "
        "them off). Add one with the ☆ on any command's row; remove it "
        "with its ×.",
        {"min": 0, "max": 15},
    ),
    (
        "recovery", "01-recovery-copies", PropertyType.Bool, True,
        "While you edit a map, keep a recovery copy of unsaved changes. After a "
        "crash, opening the device offers to restore them.",
        {},
    ),
    (
        "recovery", "02-recovery-seconds", PropertyType.Int, 60,
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
        "colours", "01-recent-colours", PropertyType.Int, 10,
        "How many recent colors the color picker keeps.",
        {"min": 4, "max": 30},
    ),
    (
        "colours", "02-print-area-color", PropertyType.String, "#EF4444",
        "The print area's frame, label and rubber band (View > Print Area "
        "Color...), as #RRGGBB.",
        {},
    ),
]


# The Device Mapping Editor's plane view settings (07 S114, S115, S120;
# D-07-PLANES-ANSWERS P4a): program settings, the same for every map, never
# in a map file, so they make no History entry. Not listed in Options; QML
# reads and sets them under these names like the options above.
VIEW_GROUP = "plane-view"
VIEW_SETTINGS: list[tuple[str, PropertyType, OptionValue, str, dict]] = [
    (
        "bm-fg-faint", PropertyType.Bool, True,
        "Background mode shows the foreground faintly (the banner's Show "
        "foreground faintly tick).",
        {},
    ),
    (
        "bm-bg-hidden", PropertyType.Bool, False,
        "The Background row's eye: the background is hidden on screen.",
        {},
    ),
    (
        "bm-bg-opacity", PropertyType.Float, 1.0,
        "The Background row's Opacity: how strongly the background shows on "
        "screen.",
        {"min": 0.0, "max": 1.0},
    ),
    (
        "bm-bg-hint-seen", PropertyType.Bool, False,
        "Background mode's first-time line has been shown.",
        {},
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
        "Saved Device Map styles: [{name, kind, fields}].", {},
    )
    for name, kind, default, description, properties in VIEW_SETTINGS:
        cfg.register(
            SECTION, VIEW_GROUP, name, kind, default, description, properties, False
        )
    _register_pane_group(cfg)
    _register_panels(cfg)
    _register_favourites(cfg)


# --- favourites --------------------------------------------------------------------

# Command ids (qml/rig_commands.js) the right-click menu shows at its top (07
# S137): a program setting, never in a map file, Export or Device Pack, and
# left alone by Reset Panels. In the order they were added.
FAVOURITES_KEY = "favourites"


def _register_favourites(cfg: Configuration) -> None:
    # Registering again keeps the stored list.
    cfg.register(
        SECTION, "internal", FAVOURITES_KEY, PropertyType.List, [],
        "Device Mapping Editor: the right-click menu's favourite command ids.",
        {}, False,
    )


def favourites() -> list[str]:
    cfg = Configuration()
    _register_favourites(cfg)
    raw = cfg.value(SECTION, "internal", FAVOURITES_KEY)
    out: list[str] = []
    for item in raw if isinstance(raw, list) else []:
        cmd = str(item or "")
        if cmd and cmd not in out:
            out.append(cmd)
    return out


def _store_favourites(ids: list[str]) -> None:
    cfg = Configuration()
    _register_favourites(cfg)
    cfg.set(SECTION, "internal", FAVOURITES_KEY, ids)


def toggle_favourite(cmd: str) -> bool:
    """Adds cmd at the end, or removes it when already there; False for no id."""
    cmd = str(cmd or "")
    if not cmd:
        return False
    ids = favourites()
    if cmd in ids:
        ids.remove(cmd)
    else:
        ids.append(cmd)
    _store_favourites(ids)
    return True


def remove_favourite(cmd: str) -> bool:
    """False when cmd wasn't a favourite."""
    ids = favourites()
    if cmd not in ids:
        return False
    ids.remove(cmd)
    _store_favourites(ids)
    return True


# --- side panels -------------------------------------------------------------------

# The Device Mapping Editor window's side panels, the Layers/Properties divider and the
# print area's frame: program settings, not listed in Options. Widths are
# logical px at 100% (QML multiplies by Style.dp(1)).
PANELS_GROUP = "panels"
SIDE_PANELS_KEY = "side-panels"
PROPS_SPLIT_KEY = "props-split"
PRINT_AREA_SHOWN_KEY = "print-area-shown"
PROPS_SHOWN_KEY = "props-shown"
# The Options window's group list width (its divider); 0 = fit the names.
OPTIONS_GROUPS_WIDTH_KEY = "options-groups-width"
OPTIONS_GROUPS_WIDTH_MAX = 2000

PROPS_SPLIT_DEFAULT = 0.6
PROPS_SPLIT_MIN = 0.2
PROPS_SPLIT_MAX = 0.8
# The frame starts hidden, as the Print Area tool did.
PRINT_AREA_SHOWN_DEFAULT = False
# Properties under Layers starts shown (View > Properties, F4).
PROPS_SHOWN_DEFAULT = True


def _register_panels(cfg: Configuration) -> None:
    # Registering again keeps the stored values.
    cfg.register(
        SECTION, PANELS_GROUP, SIDE_PANELS_KEY, PropertyType.Dict, {},
        "Device Mapping Editor side panels: {id: {width, pinned, open}}.", {}, False,
    )
    cfg.register(
        SECTION, PANELS_GROUP, PROPS_SPLIT_KEY, PropertyType.Float,
        PROPS_SPLIT_DEFAULT,
        "Device Mapping Editor: the Layers panel's share above the Properties panel.",
        {"min": PROPS_SPLIT_MIN, "max": PROPS_SPLIT_MAX}, False,
    )
    cfg.register(
        SECTION, PANELS_GROUP, PRINT_AREA_SHOWN_KEY, PropertyType.Bool,
        PRINT_AREA_SHOWN_DEFAULT,
        "Device Mapping Editor: the print area's frame is shown "
        "(View > Show Print Area).",
        {}, False,
    )
    cfg.register(
        SECTION, PANELS_GROUP, PROPS_SHOWN_KEY, PropertyType.Bool,
        PROPS_SHOWN_DEFAULT,
        "Device Mapping Editor: Properties shows under Layers (View > Properties).",
        {}, False,
    )
    cfg.register(
        SECTION, PANELS_GROUP, OPTIONS_GROUPS_WIDTH_KEY, PropertyType.Int, 0,
        "Device Map Options: the group list's width (0 = fit the names).",
        {"min": 0, "max": OPTIONS_GROUPS_WIDTH_MAX}, False,
    )


def _panels_cfg() -> Configuration:
    cfg = Configuration()
    _register_panels(cfg)
    return cfg


def side_panel_default(panel_id: str) -> dict:
    """A side panel never changed: Chips pinned open, Layers closed."""
    if panel_id == "chips":
        return {"width": 260, "pinned": True, "open": True}
    if panel_id == "layers":
        return {"width": 300, "pinned": False, "open": False}
    return {"width": 260, "pinned": False, "open": False}


def _clean_side(panel_id: str, raw: object, base: dict | None = None) -> dict:
    """{width, pinned, open} from raw over base (the default when None): a
    positive whole width, pinned and open as True/False."""
    out = dict(base if base is not None else side_panel_default(panel_id))
    if not isinstance(raw, dict):
        return out
    if "width" in raw:
        try:
            width = round(float(typing.cast(float, raw["width"])))
        except (TypeError, ValueError, OverflowError):
            width = 0
        if width > 0:
            out["width"] = width
    for flag in ("pinned", "open"):
        if raw.get(flag) is not None:
            out[flag] = bool(raw[flag])
    return out


def side_panel_state(panel_id: str) -> dict:
    stored = _panels_cfg().value(SECTION, PANELS_GROUP, SIDE_PANELS_KEY)
    raw = stored.get(panel_id) if isinstance(stored, dict) else None
    return _clean_side(panel_id, raw)


def set_side_panel_state(panel_id: str, state: object) -> bool:
    """Merges state into the panel's; False when nothing changed."""
    panel_id = str(panel_id or "")
    if not panel_id:
        return False
    now = side_panel_state(panel_id)
    new = _clean_side(panel_id, state, now)
    if new == now:
        return False
    cfg = _panels_cfg()
    stored = cfg.value(SECTION, PANELS_GROUP, SIDE_PANELS_KEY)
    rows = dict(stored) if isinstance(stored, dict) else {}
    rows[panel_id] = new
    cfg.set(SECTION, PANELS_GROUP, SIDE_PANELS_KEY, rows)
    return True


def _clamp_split(raw: object) -> float:
    try:
        share = float(typing.cast(float, raw))
    except (TypeError, ValueError):
        return PROPS_SPLIT_DEFAULT
    if share != share:  # NaN
        return PROPS_SPLIT_DEFAULT
    return max(PROPS_SPLIT_MIN, min(PROPS_SPLIT_MAX, share))


def props_split() -> float:
    return _clamp_split(_panels_cfg().value(SECTION, PANELS_GROUP, PROPS_SPLIT_KEY))


def set_props_split(share: object) -> bool:
    """Keeps the share, clamped to 0.2..0.8; False when nothing changed."""
    try:
        float(typing.cast(float, share))
    except (TypeError, ValueError):
        return False
    new = _clamp_split(share)
    if new == props_split():
        return False
    _panels_cfg().set(SECTION, PANELS_GROUP, PROPS_SPLIT_KEY, new)
    return True


def print_area_shown() -> bool:
    return bool(_panels_cfg().value(SECTION, PANELS_GROUP, PRINT_AREA_SHOWN_KEY))


def set_print_area_shown(shown: object) -> bool:
    new = bool(shown)
    if new == print_area_shown():
        return False
    _panels_cfg().set(SECTION, PANELS_GROUP, PRINT_AREA_SHOWN_KEY, new)
    return True


def props_shown() -> bool:
    return bool(_panels_cfg().value(SECTION, PANELS_GROUP, PROPS_SHOWN_KEY))


def set_props_shown(shown: object) -> bool:
    new = bool(shown)
    if new == props_shown():
        return False
    _panels_cfg().set(SECTION, PANELS_GROUP, PROPS_SHOWN_KEY, new)
    return True


def options_groups_width() -> int:
    """The Options window's group list width in logical px at 100%; 0 when
    never dragged (the window fits the names)."""
    raw = _panels_cfg().value(SECTION, PANELS_GROUP, OPTIONS_GROUPS_WIDTH_KEY)
    try:
        width = round(float(typing.cast(float, raw)))
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(OPTIONS_GROUPS_WIDTH_MAX, width))


def set_options_groups_width(width: object) -> bool:
    """Keeps the dragged width (the window clamps it to its own room);
    False when nothing changed."""
    try:
        new = round(float(typing.cast(float, width)))
    except (TypeError, ValueError, OverflowError):
        return False
    new = max(0, min(OPTIONS_GROUPS_WIDTH_MAX, new))
    if new == options_groups_width():
        return False
    _panels_cfg().set(SECTION, PANELS_GROUP, OPTIONS_GROUPS_WIDTH_KEY, new)
    return True


# Windows of their own, not Device Mapping Editor panels: Reset Panels keeps their pin.
_RESET_KEEPS = ("shortcuts", "options")


def reset_panels() -> None:
    """The side panels, the divider and Properties back to their defaults
    (View > Reset Panels, 07 S99). Not the print area's frame, the
    Keyboard Shortcuts and Options windows (pin, group list width) or the
    favourites: they aren't panels."""
    cfg = _panels_cfg()
    stored = dict(cfg.value(SECTION, PANELS_GROUP, SIDE_PANELS_KEY) or {})
    kept = {k: v for k, v in stored.items() if k in _RESET_KEEPS}
    cfg.set(SECTION, PANELS_GROUP, SIDE_PANELS_KEY, kept)
    cfg.set(SECTION, PANELS_GROUP, PROPS_SPLIT_KEY, PROPS_SPLIT_DEFAULT)
    cfg.set(SECTION, PANELS_GROUP, PROPS_SHOWN_KEY, PROPS_SHOWN_DEFAULT)


class _PanelsNotifier(QtCore.QObject):
    """One signal for every DeviceMapOptions, so each window sees a change
    made through another."""

    changed = QtCore.Signal()
    # The favourites list changed.
    favouritesChanged = QtCore.Signal()


_panels_notifier: _PanelsNotifier | None = None


def _notifier() -> _PanelsNotifier:
    global _panels_notifier
    if _panels_notifier is None:
        _panels_notifier = _PanelsNotifier()
    return _panels_notifier


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


class DeviceMapLibraryOption(QtCore.QObject, BaseMetaConfigOptionWidget):
    """Device Map Options → Library: saved styles and templates."""

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionDeviceMapLibrary.qml").fileName()


MetaConfigOption().register(
    SECTION,
    "library",
    "saved-styles-and-templates",
    "Styles saved from the Device Mapping Editor's right-click menus, and layout "
    "templates (File > Templates). Rename or delete them here.",
    DeviceMapLibraryOption,
)


def _entry(key: str) -> tuple[str, str] | None:
    for group, name, *_rest in OPTIONS:
        if key_of(name) == key:
            return group, name
    for name, *_rest in VIEW_SETTINGS:
        if name == key:
            return VIEW_GROUP, name
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


# The Device Mapping Editor's Options pane: the group last shown.
_PANE_GROUP = ("global", "internal", "device-map-options-group")


def _register_pane_group(cfg: Configuration) -> None:
    # Registering again changes nothing.
    cfg.register(
        *_PANE_GROUP, PropertyType.String, GROUPS[0],
        "Device Mapping Editor: the Options pane's group last shown.", {}, False,
    )


@ta.QmlElement
class DeviceMapOptions(QtCore.QObject):
    """The Device Mapping Editor options for QML: values[name], and set(name, value)."""

    changed = QtCore.Signal()
    # A side panel, the Layers/Properties divider or the print area's frame
    # changed. Not sent on configChanged, so a drag doesn't redraw every option.
    panelsChanged = QtCore.Signal()
    favouritesChanged = QtCore.Signal()
    favouritesShownChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        register()
        signal.configChanged.connect(self._on_config)
        _notifier().changed.connect(self.panelsChanged)
        _notifier().favouritesChanged.connect(self.favouritesChanged)
        self._shown = self._get_favourites_shown()

    @QtCore.Slot()
    def _on_config(self) -> None:
        self.changed.emit()
        shown = self._get_favourites_shown()
        if shown != self._shown:
            self._shown = shown
            self.favouritesShownChanged.emit()

    # --- favourites ----------------------------------------------------------

    def _get_favourites(self) -> list:
        return favourites()

    # Command ids in the order added; shared by every open window.
    favourites = QtCore.Property(list, _get_favourites, notify=favouritesChanged)

    def _get_favourites_shown(self) -> int:
        try:
            shown = int(typing.cast(int, value("favourites-shown")))
        except (TypeError, ValueError):
            return 5
        return max(0, min(15, shown))

    # How many the right-click menu shows (Options: Right-click menu).
    favouritesShown = QtCore.Property(
        int, _get_favourites_shown, notify=favouritesShownChanged
    )

    @QtCore.Slot(str)
    def toggleFavourite(self, cmd: str) -> None:
        if toggle_favourite(cmd):
            _notifier().favouritesChanged.emit()

    @QtCore.Slot(str)
    def removeFavourite(self, cmd: str) -> None:
        if remove_favourite(cmd):
            _notifier().favouritesChanged.emit()

    @QtCore.Property("QVariantMap", notify=changed)
    def values(self) -> dict[str, OptionValue]:
        cfg = Configuration()
        out = {
            key_of(name): cfg.value(SECTION, group, name)
            for group, name, *_rest in OPTIONS
            if cfg.exists(SECTION, group, name)
        }
        for name, *_rest in VIEW_SETTINGS:
            if cfg.exists(SECTION, VIEW_GROUP, name):
                out[name] = cfg.value(SECTION, VIEW_GROUP, name)
        return out

    @QtCore.Property(list, constant=True)
    def groups(self) -> list:
        """The groups in order, for the Options pane: [{key, title}]."""
        return [
            {"key": g, "title": _GROUP_HEADINGS.get(g) or group_title(g)}
            for g in GROUPS
        ]

    @QtCore.Property(list, constant=True)
    def entries(self) -> list:
        """Every option for the Options pane, in order: {group, key, title,
        kind ("bool", "int", "choice", "color" or "text"), description,
        choices, min, max}. Values come from `values`."""
        out = []
        ordered = sorted(OPTIONS, key=lambda o: (GROUPS.index(o[0]), o[1]))
        for group, name, kind, _default, description, props in ordered:
            key = key_of(name)
            if kind == PropertyType.Bool:
                shown = "bool"
            elif kind == PropertyType.Int:
                shown = "int"
            elif kind == PropertyType.Selection:
                shown = "choice"
            elif key.endswith("-color"):
                shown = "color"
            else:
                shown = "text"
            out.append({
                "group": group,
                "key": key,
                "title": entry_title(name),
                "kind": shown,
                "description": description,
                "choices": list(props.get("valid_options", [])),
                "min": props.get("min", 0),
                "max": props.get("max", 100000),
            })
        return out

    def _get_pane_group(self) -> str:
        cfg = Configuration()
        _register_pane_group(cfg)
        value = str(cfg.value(*_PANE_GROUP) or "")
        return value if value in GROUPS else GROUPS[0]

    def _set_pane_group(self, value: str) -> None:
        if value not in GROUPS:
            return
        cfg = Configuration()
        _register_pane_group(cfg)
        cfg.set(*_PANE_GROUP, value)
        self.changed.emit()

    # The Options pane's group, kept for next time.
    paneGroup = QtCore.Property(str, _get_pane_group, _set_pane_group, notify=changed)

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

    # --- side panels ---------------------------------------------------------

    @QtCore.Slot(str, result="QVariantMap")
    def sidePanelState(self, panel_id: str) -> dict:
        """{width, pinned, open}; width in logical px at 100%."""
        return side_panel_state(panel_id)

    @QtCore.Slot(str, "QVariantMap")
    def setSidePanelState(self, panel_id: str, state: dict) -> None:
        """Merges the given keys of {width, pinned, open} into the panel's."""
        if set_side_panel_state(panel_id, state):
            _notifier().changed.emit()

    @QtCore.Slot(result=float)
    def propsSplit(self) -> float:
        """The Layers panel's share above Properties, 0.2..0.8."""
        return props_split()

    @QtCore.Slot(float)
    def setPropsSplit(self, share: float) -> None:
        if set_props_split(share):
            _notifier().changed.emit()

    @QtCore.Slot(result=bool)
    def printAreaShown(self) -> bool:
        return print_area_shown()

    @QtCore.Slot(bool)
    def setPrintAreaShown(self, shown: bool) -> None:
        if set_print_area_shown(shown):
            _notifier().changed.emit()

    @QtCore.Slot(result=bool)
    def propsShown(self) -> bool:
        return props_shown()

    @QtCore.Slot(bool)
    def setPropsShown(self, shown: bool) -> None:
        if set_props_shown(shown):
            _notifier().changed.emit()

    @QtCore.Slot(result=int)
    def optionsGroupsWidth(self) -> int:
        """The Options window's group list width; 0 = fit the names."""
        return options_groups_width()

    @QtCore.Slot(float)
    def setOptionsGroupsWidth(self, width: float) -> None:
        if set_options_groups_width(width):
            _notifier().changed.emit()

    @QtCore.Slot()
    def resetPanels(self) -> None:
        reset_panels()
        _notifier().changed.emit()

    @QtCore.Slot(str, "QVariant")
    def set(self, key: str, new_value: object) -> None:
        if _entry(key) is None:
            return
        if key == "bm-bg-opacity":
            try:
                new_value = max(0.0, min(1.0, float(typing.cast(float, new_value))))
            except (TypeError, ValueError):
                return
        set_value(key, new_value)
        signal.configChanged.emit()


@ta.QmlElement
class DeviceMapSpaceKey(QtCore.QObject):
    """Whether Space is held down, for Space + left-drag panning in Edit
    (07 S14). It only watches: every key still goes where it went."""

    heldChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._held = False
        app = QtCore.QCoreApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _set_held(self, value: bool) -> None:
        if value != self._held:
            self._held = value
            self.heldChanged.emit()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802
        kind = event.type()
        if kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
            key = typing.cast(QtGui.QKeyEvent, event)
            if key.key() == QtCore.Qt.Key.Key_Space and not key.isAutoRepeat():
                self._set_held(kind == QtCore.QEvent.Type.KeyPress)
        elif kind == QtCore.QEvent.Type.ApplicationDeactivate:
            self._set_held(False)
        return False

    held = QtCore.Property(bool, lambda self: self._held, notify=heldChanged)
