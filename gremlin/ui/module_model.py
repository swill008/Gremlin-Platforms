# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import (
    config,
    device_initialization,
    event_handler,
)
from gremlin.shared_state import runtime_active
from gremlin.signal import signal
from gremlin.types import InputType, PropertyType
from gremlin import keyboard as gremlin_keyboard
from gremlin.ui.live_debug import trace
from gremlin.modules.ids import guid_key
from gremlin.modules import ids, module_file
from gremlin.modules.claim import (
    claim_allows,
    claim_friendly,
    claim_is_empty,
    key_id,
    kind_of,
    read_claim,
)
from gremlin.modules.registry import is_output_name, read_doc, resolve_module_slug
from gremlin.modules.registry import modules as registry_modules
from gremlin.ui.hardware_profile import (
    HardwareProfile,
    _maps_dir,
    _slug,
    bind_module_file,
    delete_module_file,
    delete_device,
    delete_preview,
    foreign_module_file,
    guid_for_module,
    import_module_file,
    import_can_undo,
    drop_import_undo,
    undo_last_import,
    imported_folder_url,
    maps_folder_url,
    module_file_choices,
    module_json_path,
    persist_log,
)
from gremlin.modules import hardware

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

# Built-in device rows; upper-case text as already written to module files.
KEYBOARD_GUID = str(ids.KEYBOARD).upper()
OSC_GUID = str(ids.OSC).upper()
XBOX_GUID = str(ids.XBOX).upper()
LOGICAL_GUID = str(ids.LOGICAL_DEVICE).upper()

_CFG_SECTION = "display"
_CFG_GROUP = "status"
_CFG_HIDDEN = "hidden-slugs"
_CFG_ORDER = "card-order"
_CFG_SHOW_STUBS = "show-stubs"
_CFG_SPLIT = "split-mode"
_CFG_COMPACT = "compact-view"
_CFG_SPLIT_RATIO = "split-ratio"
_CFG_STACKS = "card-stacks"
_CFG_SIZES = "card-sizes"
_CFG_KEPT_STUBS = "kept-stubs"


def _ensure_display_options() -> None:
    cfg = config.Configuration()

    def _reg(name, dtype, initial, desc, props=None, expose: bool = True) -> None:
        try:
            cfg.register(
                _CFG_SECTION,
                _CFG_GROUP,
                name,
                dtype,
                initial,
                desc,
                props or {},
                expose,
            )
        except Exception as exc:
            import logging
            logging.getLogger("system").warning("status option %s: %s", name, exc)

    _reg(_CFG_HIDDEN, PropertyType.String, "", "Ignored Status card slugs (comma separated).", expose=False)
    _reg(
        _CFG_SHOW_STUBS,
        PropertyType.Bool,
        True,
        "Show stub cards for detected hardware with no saved module.",
    )
    _reg(_CFG_ORDER, PropertyType.String, "", "Status card order (comma separated slugs).", expose=False)
    _reg(
        _CFG_COMPACT,
        PropertyType.Bool,
        False,
        "Status compact cards: text only, no photo.",
    )
    _reg(
        _CFG_SPLIT,
        PropertyType.String,
        "none",
        "Status split: none, vertical, or horizontal.",
        expose=False,
    )
    _reg(
        _CFG_SPLIT_RATIO,
        PropertyType.Float,
        0.5,
        "Status splitter position (0.2–0.8).",
        {"min": 0.2, "max": 0.8},
        expose=False,
    )
    _reg(_CFG_STACKS, PropertyType.String, "", "Status card stacks (slug+slug|slug).", expose=False)
    _reg(_CFG_SIZES, PropertyType.String, "", "Status card sizes (slug=WxH).", expose=False)
    _reg(
        _CFG_KEPT_STUBS,
        PropertyType.String,
        "",
        "Devices kept visible as stubs after Delete Device.",
        expose=False,
    )


def _write_status(name: str, value) -> None:
    _ensure_display_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, name, value)
    except Exception as exc:
        import logging
        logging.getLogger("system").warning("status save %s: %s", name, exc)


def _hidden_slugs() -> set[str]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_HIDDEN) or "")
    return {p.strip() for p in raw.split(",") if p.strip()}


def _kept_stubs() -> set[str]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_KEPT_STUBS) or "")
    return {p.strip() for p in raw.split(",") if p.strip()}


def _set_kept_stubs(slugs: set[str]) -> None:
    _write_status(_CFG_KEPT_STUBS, ",".join(sorted(slugs)))


def _remember_stub(slug: str) -> None:
    if not slug:
        return
    kept = _kept_stubs()
    if slug in kept:
        return
    kept.add(slug)
    _set_kept_stubs(kept)


def _release_kept_stub(slug: str) -> None:
    kept = _kept_stubs()
    if slug not in kept:
        return
    kept.discard(slug)
    _set_kept_stubs(kept)


def _show_unconfigured(slug: str, saved: bool, show_stubs: bool) -> bool:
    if saved:
        _release_kept_stub(slug)
        return True
    return show_stubs or slug in _kept_stubs()


def _set_hidden(slugs: set[str]) -> None:
    _ensure_display_options()
    _write_status(_CFG_HIDDEN, ",".join(sorted(slugs)))


def collect_bound_names(
    source_guid_to_name: dict[str, str],
    dest_vjoy_to_name: dict[int, str],
    xbox_name: str,
    maps: list[tuple[str, str, int]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Group profile wires into unique device names per source GUID and dest key."""
    src_bound: dict[str, list[str]] = {}
    dest_bound: dict[str, list[str]] = {}

    def add(bucket: dict[str, list[str]], key: str, value: str) -> None:
        if not key or not value:
            return
        items = bucket.setdefault(key, [])
        if value not in items:
            items.append(value)

    for guid, kind, dest_id in maps:
        src_name = source_guid_to_name.get(guid, "")
        if kind == "xbox":
            dest_name = xbox_name or "Xbox 360 Controller"
            dest_key = "xbox"
        else:
            dest_name = dest_vjoy_to_name.get(int(dest_id), f"vJoy {dest_id}")
            dest_key = f"vjoy:{int(dest_id)}"
        add(src_bound, guid, dest_name)
        add(dest_bound, dest_key, src_name)
    return src_bound, dest_bound


def _profile_wire_maps() -> list[tuple[str, str, int]]:
    try:
        from gremlin import shared_state
        from gremlin.ui.input_pairing import _maps_for_item
    except Exception:
        return []
    profile = getattr(shared_state, "current_profile", None)
    if profile is None:
        return []
    out: list[tuple[str, str, int]] = []
    for uid, items in (getattr(profile, "inputs", None) or {}).items():
        guid = guid_key(uid)
        for item in items or []:
            try:
                mapped = _maps_for_item(item)
            except Exception:
                continue
            for vjoy_id, vtype, _hid in mapped:
                kind = "xbox" if vtype is None else "vjoy"
                try:
                    out.append((guid, kind, int(vjoy_id)))
                except (TypeError, ValueError):
                    continue
    return out


def apply_bound_targets(rows: list) -> None:
    guid_to_name = {
        guid_key(getattr(row, "guid", "")): getattr(row, "name", "")
        for row in rows
        if getattr(row, "direction", "") == "source"
    }
    vjoy_to_name: dict[int, str] = {}
    xbox_name = ""
    for row in rows:
        if getattr(row, "direction", "") != "dest":
            continue
        name = str(getattr(row, "name", "") or "")
        tab = str(getattr(row, "tab", "") or "")
        if tab == "xbox" or "xbox" in name.lower():
            xbox_name = name
            continue
        digits = "".join(ch for ch in name if ch.isdigit())
        if digits:
            vjoy_to_name[int(digits)] = name
    src_bound, dest_bound = collect_bound_names(
        guid_to_name, vjoy_to_name, xbox_name, _profile_wire_maps()
    )
    for row in rows:
        direction = getattr(row, "direction", "")
        name = str(getattr(row, "name", "") or "")
        tab = str(getattr(row, "tab", "") or "")
        if direction == "source":
            names = src_bound.get(guid_key(getattr(row, "guid", "")), [])
        elif tab == "xbox" or "xbox" in name.lower():
            names = dest_bound.get("xbox", [])
        else:
            digits = "".join(ch for ch in name if ch.isdigit())
            names = dest_bound.get(f"vjoy:{int(digits)}", []) if digits else []
        # Spaces kept in a module file's name ("EVO OT L  ") don't show.
        row.target = ", ".join(" ".join(str(n).split()) for n in names)


def _order_slugs() -> list[str]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_ORDER) or "")
    return [p.strip() for p in raw.split(",") if p.strip()]


def _set_order(slugs: list[str]) -> None:
    _ensure_display_options()
    _write_status(_CFG_ORDER, ",".join(slugs))


def _merged_order(saved: list[str], showing: list[str]) -> list[str]:
    """The card order to save: the showing cards in their given order, and
    each saved card that isn't showing (a stick unplugged) kept in its saved
    place, so it comes back there. Showing cards new to the order go last."""
    here = set(showing)
    queue = iter(showing)
    out: list[str] = []
    for slug in dict.fromkeys(saved):
        if slug not in here:
            out.append(slug)
            continue
        out.append(next(queue))
    out.extend(queue)
    return out


def _renamed_into_order(order: list[str], rows: list, hidden: set[str]) -> list[str]:
    """The card order with a renamed stick in its old card's place. A card
    is named after its device; a renamed stick still opens its old module
    file, whose name is its old card's. Without this the old card's place
    stayed in the order for good and the stick went last. Only a file bound
    to this stick counts: a file chosen in Module Setup that is another
    (unplugged) stick's would take that stick's place."""
    showing = {row.slug for row in rows}
    bound = {module.slug: guid_key(module.bound_guid) for module in registry_modules()}
    out = list(order)
    for row in rows:
        if row.direction != "source" or row.tab != "physical" or row.slug in out:
            continue
        try:
            old = resolve_module_slug(row.raw_name or row.name, row.guid)
        except Exception:
            continue
        if old == row.slug or old not in out or old in showing or old in hidden:
            continue
        if bound.get(old) and bound.get(old) == guid_key(row.guid):
            out[out.index(old)] = row.slug
    return out


def _sizes() -> dict[str, tuple[int, int]]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SIZES) or "")
    out: dict[str, tuple[int, int]] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" not in part or "x" not in part:
            continue
        slug, dim = part.split("=", 1)
        try:
            w_s, h_s = dim.lower().split("x", 1)
            w, h = int(w_s), int(h_s)
        except ValueError:
            continue
        if slug.strip() and w > 0 and h > 0:
            out[slug.strip()] = (w, h)
    return out


def _set_sizes(sizes: dict[str, tuple[int, int]]) -> None:
    packed = ",".join(f"{slug}={w}x{h}" for slug, (w, h) in sizes.items())
    _write_status(_CFG_SIZES, packed)


def _plog(action: str, **parts: object) -> None:
    detail = " ".join(f"{key}={value!r}" for key, value in parts.items())
    persist_log(f"Persist {action} {detail}")


def _clamp_size(w: int, h: int) -> tuple[int, int]:
    return (
        max(220, min(720, int(w))),
        max(140, min(520, int(h))),
    )


def _show_stubs() -> bool:
    _ensure_display_options()
    return bool(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SHOW_STUBS))


def _load_module_doc(device_name: str, guid: str = "") -> dict:
    slug = resolve_module_slug(device_name, guid)
    path = _maps_dir() / f"{slug}.json"
    if not path.is_file():
        _plog("load miss", name=device_name, guid=guid, slug=slug, path=str(path))
        return {}
    # One reader for every module file: a damaged one (not UTF-8 too) reads
    # as {} here; it used to stop Home, the Run lists and the card polling.
    data = read_doc(path)
    if data is None:
        _plog("load bad", name=device_name, guid=guid, path=str(path))
        return {}
    claim = data.get("claim") if isinstance(data.get("claim"), dict) else {}
    _plog(
        "load",
        name=device_name,
        guid=guid,
        path=str(path),
        buttons=len(claim.get("buttons") or []),
        axes=len(claim.get("axes") or []),
        hats=len(claim.get("hats") or []),
        nodes=len(data.get("nodes") or []) if isinstance(data.get("nodes"), list) else 0,
        view="view" in data,
        catalog="catalog" in data,
    )
    return data


_DEFAULT_CATALOG = {
    "listPadding": 8,
    "rowSpacing": 4,
    "parentHeight": 50,
    "childHeight": 36,
    "parentAlign": "left",
    "parentLeft": 0,
    "parentRight": 0,
    "parentWidthPct": 100,
    "childAlign": "left",
    "childLeft": 24,
    "childRight": 24,
    "childWidthPct": 50,
    "parentFont": 13,
    "childFont": 12,
    "summaryFont": 12,
    "parentBold": True,
    "showChildren": True,
    "showLiveBars": True,
    "showLeds": True,
    "showSummary": True,
    "rowRadius": 3,
    "nameColW": 180,
    "childNameColW": 160,
    "rowInnerPad": 10,
    "editorIndent": 12,
    "editorAlign": "left",
    "editorRight": 0,
    "editorWidthPct": 100,
    "editorPad": 10,
    "editorGap": 4,
    "editorRadius": 3,
    "editorBorderW": 1,
    "editorAccentW": 3,
    "showEditorAccent": True,
    "groupPadShape": "box",
    "groupPad": 48,
    "groupPadTop": 48,
    "groupPadRight": 48,
    "groupPadBottom": 48,
    "groupPadLeft": 48,
    "parkEmptyInUnmapped": False,
    "unmappedGap": 48,
    # Colors: "" follows Dark mode; a value is the user's own choice.
    "colorParent": "",
    "colorChild": "",
    "colorSelected": "",
    "colorText": "",
    "colorMuted": "",
    "colorLive": "",
    "colorBorder": "",
    "colorSelectBorder": "",
    "colorEditor": "",
    "colorEditorBorder": "",
    "colorEditorAccent": "",
}


_DEFAULT_VIEW = {
    "layout": "pads_meters_grid",
    "padAX": 1,
    "padAY": 2,
    "padBX": 4,
    "padBY": 5,
    "showPads": True,
    "showHats": True,
    "showMeters": True,
    "meterStyle": "vertical",
    "meterWidth": 22,
    "meters": [],
    "buttonStyle": "tile",
    "buttonSize": "medium",
    "buttonColumns": 12,
    "buttonWidth": 64,
    # Colors: "" follows Dark mode; a value is the user's own choice.
    "colorLive": "",
    "colorMeter": "",
    "colorPress": "",
    "colorScreen": "#00000000",
    "screenImage": "",
}


def _module_damage(device_name: str, guid: str = "") -> str:
    """Why the device's module file can't be read ("" when it is fine)."""
    slug = resolve_module_slug(device_name, guid)
    return module_file.damage_reason(_maps_dir() / f"{slug}.json")


def _device_connected(guid: str) -> bool:
    """True when the joystick driver sees a device with this GUID."""
    try:
        return hardware.device_connected(guid)
    except Exception:
        # A GUID the driver can't read is not one of its devices.
        return False


def module_exists(device_name: str) -> bool:
    path = _maps_dir() / f"{resolve_module_slug(device_name)}.json"
    return path.is_file()


class ModuleRow:
    __slots__ = (
        "slug",
        "name",
        "raw_name",
        "guid",
        "direction",
        "status",
        "bus",
        "buttons",
        "axes",
        "hats",
        "photo",
        "is_stub",
        "is_module",
        "tab",
        "target",
        "vid",
        "pid",
        "last_friendly",
        "last_hardware",
        "damaged",
    )

    def __init__(self) -> None:
        self.slug = ""
        self.name = ""
        self.raw_name = ""
        self.guid = ""
        self.direction = "source"
        self.status = "Stub"
        # Why the device's module file can't be read ("" when it is fine).
        self.damaged = ""
        self.bus = "DirectInput"
        self.buttons = 0
        self.axes = 0
        self.hats = 0
        self.photo = ""
        self.is_stub = True
        self.is_module = False
        self.tab = "physical"
        self.target = ""
        self.vid = ""
        self.pid = ""
        self.last_friendly = ""
        self.last_hardware = ""


def reset_all_card_sizes() -> None:
    """Back to the default size for every card. Home cards follow on configChanged."""
    _set_sizes({})
    signal.configChanged.emit()


@ta.QmlElement
class CardSizes(QtCore.QObject):
    """Card size reset for pages that do not show the cards (Options)."""

    @QtCore.Slot()
    def resetAll(self) -> None:
        reset_all_card_sizes()


@ta.QmlElement
class ModuleListModel(QtCore.QAbstractListModel):
    """Status cards: detected hardware stubs plus saved modules."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"slug"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"rawName"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"direction"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"status"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"bus"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"buttons"),
        QtCore.Qt.ItemDataRole.UserRole + 9: QtCore.QByteArray(b"axes"),
        QtCore.Qt.ItemDataRole.UserRole + 10: QtCore.QByteArray(b"hats"),
        QtCore.Qt.ItemDataRole.UserRole + 11: QtCore.QByteArray(b"photo"),
        QtCore.Qt.ItemDataRole.UserRole + 12: QtCore.QByteArray(b"isStub"),
        QtCore.Qt.ItemDataRole.UserRole + 13: QtCore.QByteArray(b"isModule"),
        QtCore.Qt.ItemDataRole.UserRole + 14: QtCore.QByteArray(b"tab"),
        QtCore.Qt.ItemDataRole.UserRole + 15: QtCore.QByteArray(b"target"),
        QtCore.Qt.ItemDataRole.UserRole + 16: QtCore.QByteArray(b"vid"),
        QtCore.Qt.ItemDataRole.UserRole + 17: QtCore.QByteArray(b"pid"),
        QtCore.Qt.ItemDataRole.UserRole + 18: QtCore.QByteArray(b"lastLine"),
        QtCore.Qt.ItemDataRole.UserRole + 19: QtCore.QByteArray(b"lastHardware"),
        QtCore.Qt.ItemDataRole.UserRole + 20: QtCore.QByteArray(b"focused"),
        QtCore.Qt.ItemDataRole.UserRole + 21: QtCore.QByteArray(b"damaged"),
    }

    modelResetNeeded = QtCore.Signal()
    lastChanged = QtCore.Signal()
    focusChanged = QtCore.Signal()
    hiddenChanged = QtCore.Signal()
    panesChanged = QtCore.Signal()
    claimsChanged = QtCore.Signal()
    # A card's "Driven by" changed (an action added, removed or retargeted).
    targetsChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[ModuleRow] = []
        self._hidden_names: dict[str, str] = {}
        self._focus = ""
        self._last: dict[str, tuple[str, str]] = {}
        self._last_saved_path = ""
        self._hw = HardwareProfile(self)
        _ensure_display_options()
        self._reload_timer = QtCore.QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(200)
        self._reload_timer.timeout.connect(self._reload)
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(50)
        self._refresh_timer.timeout.connect(self._refresh_inplace)
        # "Driven by" follows action edits; a burst of edits is one check.
        self._targets_timer = QtCore.QTimer(self)
        self._targets_timer.setSingleShot(True)
        self._targets_timer.setInterval(200)
        self._targets_timer.timeout.connect(self._refresh_targets)
        self._dest_snap: dict[str, dict] = {}
        # vJoy id and claim per output card, read once per reload.
        self._dest_targets: dict[str, tuple[int, dict]] = {}
        # Claim per input card: (checked at, file stamp, claim). Input events
        # come hundreds of times a second while sticks move; re-reading and
        # parsing the module file for each one churned memory and CPU.
        self._source_claims: dict[str, tuple[float, tuple[int, int] | None, dict]] = {}
        self._reload()
        event_handler.EventListener().device_change_event.connect(self._schedule_reload)
        from gremlin.modules.runtime import InputModuleRuntime

        InputModuleRuntime().event.connect(self._on_joy)
        self._dest_timer = QtCore.QTimer(self)
        self._dest_timer.setInterval(50)
        self._dest_timer.timeout.connect(self._poll_dest_last)
        self._dest_timer.start()
        signal.profileChanged.connect(self._schedule_reload)
        signal.configChanged.connect(self._schedule_refresh)
        signal.inputItemChanged.connect(lambda _index: self._targets_timer.start())
        signal.logicalDeviceModified.connect(self._targets_timer.start)
        signal.actionsChanged.connect(self._targets_timer.start)
        # Options > Reset all card sizes changes the saved sizes elsewhere;
        # re-read them here so Home cards follow at once.
        self._sizes_snap = _sizes()
        signal.configChanged.connect(self._follow_card_sizes)

    @QtCore.Slot()
    def _follow_card_sizes(self) -> None:
        sizes = _sizes()
        if sizes == self._sizes_snap:
            return
        self._sizes_snap = sizes
        self.panesChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if role not in self.roles or not index.isValid():
            return None
        row = self._rows[index.row()]
        last_f, last_h = self._last.get(row.slug, (row.last_friendly, row.last_hardware))
        match bytes(self.roles[role]).decode():
            case "slug":
                return row.slug
            case "name":
                return row.name
            case "rawName":
                return row.raw_name
            case "guid":
                return row.guid
            case "direction":
                return row.direction
            case "status":
                return row.status
            case "bus":
                return row.bus
            case "buttons":
                return row.buttons
            case "axes":
                return row.axes
            case "hats":
                return row.hats
            case "photo":
                return row.photo
            case "isStub":
                return row.is_stub
            case "isModule":
                return row.is_module
            case "tab":
                return row.tab
            case "target":
                return row.target
            case "vid":
                return row.vid
            case "pid":
                return row.pid
            case "lastLine":
                return last_f
            case "lastHardware":
                return last_h
            case "focused":
                return row.slug == self._focus
            case "damaged":
                return row.damaged
            case _:
                return None

    @QtCore.Slot()
    def reload(self) -> None:
        self._reload()

    @QtCore.Slot(str)
    def setFocus(self, slug: str) -> None:
        if slug == self._focus:
            return
        self._focus = slug
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._rows) - 1, 0),
                [QtCore.Qt.ItemDataRole.UserRole + 20],
            )
        self.focusChanged.emit()

    @QtCore.Property(str, notify=focusChanged)
    def focusedSlug(self) -> str:
        return self._focus

    viewChanged = QtCore.Signal()

    @QtCore.Slot(str, str, result=str)
    def viewConfigJson(self, device_name: str, guid: str) -> str:
        doc: dict = {}
        if device_name:
            path = module_json_path(device_name, guid)
            if path.is_file():
                loaded = read_doc(path)
                doc = loaded or {}
                result = "ok" if loaded is not None else "error"
                trace("READ", "Output Configuration", "viewConfigJson", path, result)
            else:
                trace("READ", "Output Configuration", "viewConfigJson", path, "missing")
        view = dict(_DEFAULT_VIEW)
        view["meters"] = list(_DEFAULT_VIEW["meters"])
        raw = doc.get("view")
        if isinstance(raw, dict):
            view.update(raw)
        return json.dumps(view)

    @QtCore.Slot(str, str, str, result=bool)
    def saveViewConfig(self, device_name: str, guid: str, json_text: str) -> bool:
        name = str(device_name or "").strip()
        if not name:
            return False
        try:
            incoming = json.loads(json_text or "{}")
        except json.JSONDecodeError:
            return False
        if not isinstance(incoming, dict):
            return False
        path = module_json_path(name, guid)
        try:
            doc = module_file.load_for_update(path)
        except module_file.ModuleFileDamaged as damaged:
            trace("READ", "Output Configuration", "saveViewConfig", path, "damaged")
            module_file.report_refused(damaged)
            return False
        trace("READ", "Output Configuration", "saveViewConfig", path, "ok")
        view = dict(_DEFAULT_VIEW)
        view["meters"] = list(_DEFAULT_VIEW["meters"])
        raw = doc.get("view")
        if isinstance(raw, dict):
            view.update(raw)
        view.update(incoming)
        doc["view"] = view
        doc.setdefault("kind", "control.hardware")
        doc.setdefault("device", name)
        path.parent.mkdir(parents=True, exist_ok=True)
        _plog("save view", name=name, path=str(path))
        try:
            module_file.write_json(path, doc)
            written = json.loads(path.read_text(encoding="utf-8"))
            trace("SAVE", "Output Configuration", "saveViewConfig", path, "ok")
        except (OSError, json.JSONDecodeError) as exc:
            _plog("save view failed", path=str(path), error=exc)
            trace("SAVE", "Output Configuration", "saveViewConfig", path, "error")
            return False
        if not isinstance(written.get("view"), dict):
            _plog("save view mismatch", path=str(path))
            return False
        self.viewChanged.emit()
        _plog("save view ok", path=str(path))
        self._last_saved_path = str(path)
        return True

    @QtCore.Slot(result=str)
    def lastSavedPath(self) -> str:
        return self._last_saved_path

    @QtCore.Slot(str, str, result=str)
    def catalogConfigJson(self, device_name: str, guid: str) -> str:
        path = module_json_path(device_name, guid_for_module(device_name, guid)) if device_name else None
        doc = _load_module_doc(device_name, guid_for_module(device_name, guid)) if device_name else {}
        if path is not None:
            trace(
                "READ",
                "Input Configuration",
                "catalogConfigJson",
                path,
                "ok" if path.is_file() else "missing",
            )
        catalog = dict(_DEFAULT_CATALOG)
        raw = (doc or {}).get("catalog")
        if isinstance(raw, dict):
            catalog.update(raw)
        return json.dumps(catalog)

    @QtCore.Slot(str, result=str)
    def otherSourceCatalogs(self, current_name: str) -> str:
        current = str(current_name or "").strip()
        rows = []
        seen = set()
        for row in self._rows:
            if getattr(row, "direction", "") != "source":
                continue
            name = str(getattr(row, "name", "") or "").strip()
            if not name or name.casefold() == current.casefold() or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            rows.append({"name": name, "guid": str(getattr(row, "guid", "") or "")})
        rows.sort(key=lambda item: item["name"].lower())
        return json.dumps(rows)

    @QtCore.Slot(str, result=str)
    def otherDestViews(self, current_name: str) -> str:
        current = str(current_name or "").strip()
        rows = []
        seen = set()
        for row in self._rows:
            if getattr(row, "direction", "") != "dest":
                continue
            name = str(getattr(row, "name", "") or "").strip()
            if not name or name.casefold() == current.casefold() or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            rows.append({"name": name, "guid": str(getattr(row, "guid", "") or "")})
        rows.sort(key=lambda item: item["name"].lower())
        return json.dumps(rows)

    @QtCore.Slot(str, str, str, result=bool)
    def saveCatalogConfig(self, device_name: str, guid: str, json_text: str) -> bool:
        name = str(device_name or "").strip()
        if not name:
            return False
        try:
            incoming = json.loads(json_text or "{}")
        except json.JSONDecodeError:
            return False
        if not isinstance(incoming, dict):
            return False
        path = _maps_dir() / f"{resolve_module_slug(name, guid_for_module(name, guid))}.json"
        try:
            doc = module_file.load_for_update(path)
        except module_file.ModuleFileDamaged as damaged:
            trace("READ", "Input Configuration", "saveCatalogConfig", path, "damaged")
            module_file.report_refused(damaged)
            return False
        trace("READ", "Input Configuration", "saveCatalogConfig", path, "ok")
        catalog = dict(_DEFAULT_CATALOG)
        raw = doc.get("catalog")
        if isinstance(raw, dict):
            catalog.update(raw)
        catalog.update(incoming)
        doc["catalog"] = catalog
        doc.setdefault("kind", "control.hardware")
        doc.setdefault("device", name)
        path.parent.mkdir(parents=True, exist_ok=True)
        _plog("save catalog", name=name, path=str(path))
        try:
            module_file.write_json(path, doc)
            written = json.loads(path.read_text(encoding="utf-8"))
            trace("SAVE", "Input Configuration", "saveCatalogConfig", path, "ok")
        except (OSError, json.JSONDecodeError) as exc:
            _plog("save catalog failed", path=str(path), error=exc)
            trace("SAVE", "Input Configuration", "saveCatalogConfig", path, "error")
            return False
        if not isinstance(written.get("catalog"), dict):
            _plog("save catalog mismatch", path=str(path))
            return False
        self.viewChanged.emit()
        _plog("save catalog ok", path=str(path))
        self._last_saved_path = str(path)
        return True

    @QtCore.Slot(str)
    def ignoreSlug(self, slug: str) -> None:
        hidden = _hidden_slugs()
        hidden.add(slug)
        _set_hidden(hidden)
        if self._focus == slug:
            self._focus = ""
        self._reload()
        self.hiddenChanged.emit()

    @QtCore.Slot(str)
    def unignoreSlug(self, slug: str) -> None:
        hidden = _hidden_slugs()
        hidden.discard(slug)
        _set_hidden(hidden)
        self._reload()
        self.hiddenChanged.emit()

    @QtCore.Slot()
    def unignoreAll(self) -> None:
        hidden = _hidden_slugs()
        if not hidden:
            return
        _set_hidden(set())
        self._reload()
        self.hiddenChanged.emit()

    @QtCore.Slot(result=list)
    def hiddenList(self) -> list[str]:
        return sorted(_hidden_slugs())

    @QtCore.Slot(result=list)
    def hiddenCards(self) -> list[dict[str, str]]:
        """Each hidden card as {slug, name}, by name (Home menu → Hidden
        Cards). A card whose device is not here now shows its stored id."""
        names = self._hidden_names
        cards = [{"slug": s, "name": names.get(s, s)} for s in _hidden_slugs()]
        return sorted(cards, key=lambda c: c["name"].lower())

    @QtCore.Slot(str, str)
    def moveSlugBefore(self, slug: str, before_slug: str) -> None:
        groups = {g[0]: g for g in self._stacks()}
        stacked = {s for g in groups.values() for s in g}
        leaders: list[str] = []
        for row in self._rows:
            if row.slug in stacked and row.slug not in groups:
                continue
            leaders.append(row.slug)
        if slug not in leaders:
            leaders.append(slug)
        leaders = [s for s in leaders if s != slug]
        if before_slug and before_slug in leaders:
            leaders.insert(leaders.index(before_slug), slug)
        else:
            leaders.append(slug)
        expanded: list[str] = []
        for lead in leaders:
            expanded.extend(groups.get(lead, [lead]))
        # Hidden cards keep their places (they used to be dropped here, while
        # a reload kept them): _merged_order keeps every card not showing.
        _set_order(_merged_order(_order_slugs(), expanded))
        self._reload()
        self.panesChanged.emit()

    @QtCore.Slot(result=int)
    def visibleCount(self) -> int:
        return len(self._rows)

    def _stacks(self) -> list[list[str]]:
        _ensure_display_options()
        raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_STACKS) or "")
        groups: list[list[str]] = []
        visible = {row.slug for row in self._rows}
        for part in raw.split("|"):
            group = [s.strip() for s in part.split("+") if s.strip() and s.strip() in visible]
            if len(group) > 1:
                groups.append(group)
        return groups

    def _set_stacks(self, groups: list[list[str]]) -> None:
        _ensure_display_options()
        packed = "|".join("+".join(g) for g in groups if len(g) > 1)
        _write_status(_CFG_STACKS, packed)

    @QtCore.Property(bool, notify=panesChanged)
    def compactView(self) -> bool:
        try:
            _ensure_display_options()
            return bool(
                config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_COMPACT)
            )
        except Exception:
            return False

    @QtCore.Slot(bool)
    def setCompactView(self, compact: bool) -> None:
        flag = bool(compact)
        if flag == self.compactView:
            return
        try:
            _ensure_display_options()
            _write_status(_CFG_COMPACT, flag)
        except Exception:
            return
        self.panesChanged.emit()

    @QtCore.Property(str, notify=panesChanged)
    def splitMode(self) -> str:
        try:
            _ensure_display_options()
            raw = str(
                config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SPLIT) or "none"
            ).lower()
        except Exception:
            return "none"
        return raw if raw in ("none", "vertical", "horizontal") else "none"

    @QtCore.Slot(str)
    def setSplitMode(self, mode: str) -> None:
        name = (mode or "none").lower()
        if name not in ("none", "vertical", "horizontal"):
            name = "none"
        if name == self.splitMode:
            return
        try:
            _ensure_display_options()
            _write_status(_CFG_SPLIT, name)
        except Exception:
            return
        self.panesChanged.emit()

    @QtCore.Property(float, notify=panesChanged)
    def splitRatio(self) -> float:
        """The Home page's divider. Kept with the other window layout
        (window_placement); a value saved the old way here is the starting
        point."""
        from gremlin.ui import window_placement

        old = 0.5
        try:
            _ensure_display_options()
            old = float(
                config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SPLIT_RATIO) or 0.5
            )
        except Exception:
            pass
        return min(0.8, max(0.2, window_placement.split_ratio("home", old)))

    @QtCore.Slot(float)
    def setSplitRatio(self, ratio: float) -> None:
        from gremlin.ui import window_placement

        value = min(0.8, max(0.2, float(ratio)))
        if abs(value - self.splitRatio) < 0.001:
            return
        try:
            window_placement.save_split("home", value)
        except Exception:
            return
        self.panesChanged.emit()

    @QtCore.Slot(str, result=list)
    def pileLeaders(self, direction: str) -> list:
        groups = {g[0]: g for g in self._stacks()}
        stacked = {s for g in groups.values() for s in g}
        leaders: list[str] = []
        for row in self._rows:
            if direction and row.direction != direction:
                continue
            if row.slug in stacked and row.slug not in groups:
                continue
            leaders.append(row.slug)
        return leaders

    @QtCore.Slot(str, result=list)
    def pileMembers(self, leader: str) -> list:
        for group in self._stacks():
            if leader in group:
                return group
        return [leader] if leader else []

    @QtCore.Slot(str, result=int)
    def cardWidth(self, slug: str) -> int:
        return int(_sizes().get(slug, (0, 0))[0])

    @QtCore.Slot(str, result=int)
    def cardHeight(self, slug: str) -> int:
        return int(_sizes().get(slug, (0, 0))[1])

    @QtCore.Slot(str, int, int)
    def setPileSize(self, slug: str, width: int, height: int) -> None:
        w, h = _clamp_size(width, height)
        sizes = _sizes()
        for member in self.pileMembers(slug):
            sizes[member] = (w, h)
        _set_sizes(sizes)
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def resetCardSize(self, slug: str) -> None:
        sizes = _sizes()
        for member in self.pileMembers(slug):
            sizes.pop(member, None)
        _set_sizes(sizes)
        signal.configChanged.emit()
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def clearCardSettings(self, slug: str) -> None:
        sizes = _sizes()
        sizes.pop(slug, None)
        _set_sizes(sizes)
        self.unstackSlug(slug)
        signal.configChanged.emit()
        self.panesChanged.emit()

    @QtCore.Slot()
    def resetAllCardSizes(self) -> None:
        reset_all_card_sizes()
        self.panesChanged.emit()

    @QtCore.Slot(str, str)
    def stackSelected(self, leader: str, slugs_csv: str) -> None:
        """Stack the listed slugs onto leader. Leader keeps the pile slot."""
        if not leader:
            return
        names: list[str] = []
        seen: set[str] = set()
        for raw in [leader] + [p.strip() for p in (slugs_csv or "").split(",")]:
            if raw and raw not in seen:
                names.append(raw)
                seen.add(raw)
        dirs = {row.slug: row.direction for row in self._rows}
        lead_dir = dirs.get(leader)
        names = [
            s for s in names
            if s in dirs and (not lead_dir or dirs.get(s) == lead_dir)
        ]
        if leader not in names or len(names) < 2:
            return
        selected = set(names)
        groups = []
        for group in self._stacks():
            rest = [s for s in group if s not in selected]
            if len(rest) > 1:
                groups.append(rest)
        merged = [leader] + [s for s in names if s != leader]
        groups.append(merged)
        self._set_stacks(groups)
        sizes = _sizes()
        shared = sizes.get(leader)
        if not shared:
            for slug in names:
                if slug in sizes:
                    shared = sizes[slug]
                    break
        if shared:
            for member in merged:
                sizes[member] = shared
            _set_sizes(sizes)
        self._reload()
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def unstackSlug(self, slug: str) -> None:
        groups = []
        changed = False
        for group in self._stacks():
            if slug in group:
                rest = [s for s in group if s != slug]
                if len(rest) > 1:
                    groups.append(rest)
                changed = True
            else:
                groups.append(group)
        if changed:
            self._set_stacks(groups)
            self._reload()
            self.panesChanged.emit()

    @QtCore.Slot(str)
    def unstackAll(self, slug: str) -> None:
        groups = []
        changed = False
        for group in self._stacks():
            if slug in group:
                changed = True
                continue
            groups.append(group)
        if changed:
            self._set_stacks(groups)
            self._reload()
            self.panesChanged.emit()

    @QtCore.Slot(str)
    def raiseSlug(self, slug: str) -> None:
        groups = []
        changed = False
        for group in self._stacks():
            if slug in group and group[-1] != slug:
                group = [s for s in group if s != slug] + [slug]
                changed = True
            groups.append(group)
        if changed:
            self._set_stacks(groups)
            self._reload()
            self.panesChanged.emit()

    def _row_map(self, row: ModuleRow) -> dict:
        last_f, last_h = self._last.get(row.slug, (row.last_friendly, row.last_hardware))
        return {
            "slug": row.slug,
            "name": row.name,
            "rawName": row.raw_name,
            "guid": row.guid,
            "direction": row.direction,
            "status": row.status,
            "bus": row.bus,
            "buttons": row.buttons,
            "axes": row.axes,
            "hats": row.hats,
            "photo": row.photo,
            "isStub": row.is_stub,
            "isModule": row.is_module,
            "tab": row.tab,
            "target": row.target,
            "vid": row.vid,
            "pid": row.pid,
            "lastLine": last_f,
            "lastHardware": last_h,
            "focused": row.slug == self._focus,
            "damaged": row.damaged,
        }

    @QtCore.Slot(str, result="QVariantMap")
    def cardMap(self, slug: str) -> dict:
        for row in self._rows:
            if row.slug == slug:
                return self._row_map(row)
        return {}

    @QtCore.Slot()
    def _refresh_targets(self) -> None:
        """Works out every card's "Driven by" again from the profile's actions
        and updates the cards whose list changed."""
        before = [row.target for row in self._rows]
        apply_bound_targets(self._rows)
        role = QtCore.Qt.ItemDataRole.UserRole + 15
        changed = False
        for idx, row in enumerate(self._rows):
            if row.target != before[idx]:
                changed = True
                at = self.index(idx, 0)
                self.dataChanged.emit(at, at, [role])
        if changed:
            self.targetsChanged.emit()

    @QtCore.Slot(str, result=str)
    def boundLine(self, device_name: str) -> str:
        # Fresh, not as of the last check: the header asks when a page opens.
        self._targets_timer.stop()
        self._refresh_targets()
        name = str(device_name or "")
        for row in self._rows:
            if str(getattr(row, "name", "") or "") == name:
                target = str(getattr(row, "target", "") or "")
                return "Driven by: [" + (target if target else "nothing") + "]"
        return "Driven by: [nothing]"

    @QtCore.Slot(str, result="QVariantMap")
    def firstCardMap(self, direction: str) -> dict:
        """The first card of that direction ("source" or "dest"), not the
        Xbox output (it has no Module Setup); {} when there is none."""
        for row in self._rows:
            found = self._row_map(row)
            if found.get("direction") != direction:
                continue
            if found.get("bus") == "XInput" or found.get("tab") == "xbox":
                continue
            return found
        return {}

    @QtCore.Slot(result="QVariantMap")
    def focusedCardMap(self) -> dict:
        if self._focus:
            found = self.cardMap(self._focus)
            if found:
                return found
        if self._rows:
            return self._row_map(self._rows[0])
        return {}

    @QtCore.Slot(str, result=int)
    def claimedCount(self, device_name: str) -> int:
        doc = _load_module_doc(device_name)
        if not doc:
            return 0
        claim = read_claim(doc)
        return (
            len(claim["buttons"])
            + len(claim["axes"])
            + len(claim["hats"])
            + len(claim["keys"])
        )

    @QtCore.Slot()
    def _schedule_reload(self) -> None:
        self._reload_timer.start()

    @QtCore.Slot()
    def _schedule_refresh(self) -> None:
        self._refresh_timer.start()

    def _refresh_inplace(self) -> None:
        self._dest_targets = {}
        self._source_claims = {}
        if not self._rows:
            self._reload()
            return
        roles = [
            QtCore.Qt.ItemDataRole.UserRole + 2,
            QtCore.Qt.ItemDataRole.UserRole + 6,
            QtCore.Qt.ItemDataRole.UserRole + 8,
            QtCore.Qt.ItemDataRole.UserRole + 9,
            QtCore.Qt.ItemDataRole.UserRole + 10,
            QtCore.Qt.ItemDataRole.UserRole + 11,
            QtCore.Qt.ItemDataRole.UserRole + 12,
            QtCore.Qt.ItemDataRole.UserRole + 13,
        ]
        apply_bound_targets(self._rows)
        roles = roles + [QtCore.Qt.ItemDataRole.UserRole + 15]
        for idx, row in enumerate(self._rows):
            name = row.raw_name or row.name
            row.photo = self._hw.profilePhotoUrl(name)
            saved = module_exists(name)
            row.is_module = saved
            row.is_stub = not saved
            if saved:
                doc = _load_module_doc(name)
                claim = read_claim(doc)
                row.buttons = len(claim["buttons"])
                row.axes = len(claim["axes"])
                row.hats = len(claim["hats"])
                if row.direction == "dest":
                    row.status = "Virtual"
                elif row.status == "Stub":
                    row.status = "Connected"
            ix = self.index(idx, 0)
            self.dataChanged.emit(ix, ix, roles)
        self.claimsChanged.emit()

    @QtCore.Slot()
    def notifyClaims(self) -> None:
        self._refresh_inplace()

    @QtCore.Slot(str, str, result="QVariantList")
    def moduleFileNames(self, guid: str, device_name: str) -> list:
        return module_file_choices(device_name, guid)

    @QtCore.Slot(str, str, result=str)
    def moduleFileFor(self, guid: str, device_name: str) -> str:
        """The device's module file (slug), by the shared rule: twin sticks
        share a name but not a file."""
        if not device_name:
            return ""
        return module_json_path(device_name, guid).stem

    @QtCore.Slot(str, str, result=str)
    def foreignModuleFile(self, guid: str, device_name: str) -> str:
        return foreign_module_file(device_name, guid)

    @QtCore.Slot(result=str)
    def mapsFolderUrl(self) -> str:
        return maps_folder_url()

    @QtCore.Slot(result=str)
    def importedFolderUrl(self) -> str:
        return imported_folder_url()

    @QtCore.Slot(str, str, result=bool)
    def moduleFileExists(self, guid: str, device_name: str) -> bool:
        """True when the file moduleFileFor names is saved (a renamed stick's
        old file: it was looked for under the new name)."""
        if not device_name:
            return False
        return module_json_path(device_name, guid).is_file()

    @QtCore.Slot(str, str, str, str, result=str)
    def importModuleFile(self, guid: str, device_name: str, file_name: str, direction: str) -> str:
        message = import_module_file(device_name, guid, file_name, direction)
        if str(message).startswith("Imported "):
            signal.configChanged.emit()
            self._refresh_inplace()
        return message

    @QtCore.Slot(result=bool)
    def importCanUndo(self) -> bool:
        return import_can_undo()

    @QtCore.Slot()
    def dropImportUndo(self) -> None:
        drop_import_undo()

    @QtCore.Slot(result=str)
    def undoLastImport(self) -> str:
        message = undo_last_import()
        if str(message).startswith("Undone"):
            signal.configChanged.emit()
            self._refresh_inplace()
        return message

    @QtCore.Slot(str, str, result=str)
    def deletePreview(self, device_name: str, guid: str) -> str:
        return delete_preview(device_name, guid)

    @QtCore.Slot(str, str, bool, result=str)
    def deleteDevice(self, device_name: str, guid: str, save_copy: bool) -> str:
        raw = delete_device(device_name, guid, bool(save_copy))
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if data.get("ok"):
            slug = _slug(device_name)
            if data.get("stub"):
                _remember_stub(slug)
            self.clearCardSettings(slug)
            if self._focus == slug:
                self._focus = ""
            self._reload()
            # Its card is gone: so is its place in the card order (a stick
            # still plugged in keeps its card and its place).
            if slug not in {row.slug for row in self._rows}:
                order = _order_slugs()
                if slug in order:
                    _set_order([s for s in order if s != slug])
        return raw

    @QtCore.Slot(str, str, result=str)
    def startFresh(self, device_name: str, guid: str) -> str:
        """Moves a damaged module file aside (kept as .bad-<date>) so the
        device can be set up again. Returns where the copy is, or ""."""
        slug = resolve_module_slug(device_name, guid)
        path = _maps_dir() / f"{slug}.json"
        if not module_file.damage_reason(path):
            return ""
        try:
            copy = module_file.start_fresh(path)
        except OSError as e:
            _plog("start fresh failed", path=str(path), error=e)
            return ""
        trace("SAVE", "Home", "startFresh", copy, "ok")
        signal.configChanged.emit()
        self._reload()
        return str(copy)

    @QtCore.Slot(str, str, result=str)
    def deleteModuleFile(self, guid: str, device_name: str) -> str:
        message = delete_module_file(device_name, guid)
        if not message:
            signal.configChanged.emit()
            self._refresh_inplace()
        return message

    def _on_joy(self, event: event_handler.Event) -> None:
        if event is None:
            return
        from gremlin.modules.gate import status_last_from_hid

        guid = guid_key(event.device_guid)
        row = next((r for r in self._rows if guid_key(r.guid) == guid), None)
        if row is None:
            return
        if not status_last_from_hid(row.direction):
            return
        kind = kind_of(getattr(event, "event_type", None)) or "button"
        try:
            hid = int(getattr(event, "identifier", 0) or 0)
        except (TypeError, ValueError):
            return
        claim = self._source_claim(row)
        if not claim_is_empty(claim) and not claim_allows(claim, kind, hid):
            return
        self._set_last(row, kind, hid, claim)

    # How often an input card looks at its module file for a newer save.
    _CLAIM_CHECK_S = 0.5

    def _source_claim(self, row: ModuleRow) -> dict:
        """An input card's claim, re-read only when its module file changed
        (looked at no more than twice a second)."""
        now = time.monotonic()
        cached = self._source_claims.get(row.slug)
        if cached is not None and now - cached[0] < self._CLAIM_CHECK_S:
            return cached[2]
        name = row.raw_name or row.name
        path = _maps_dir() / f"{resolve_module_slug(name, row.guid)}.json"
        try:
            stat = path.stat()
            stamp: tuple[int, int] | None = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            stamp = None
        if cached is not None and cached[1] == stamp:
            claim = cached[2]
        else:
            doc = _load_module_doc(name, row.guid) if stamp else {}
            claim = read_claim(doc) if doc else {}
        self._source_claims[row.slug] = (now, stamp, claim)
        return claim

    def _set_last(self, row: ModuleRow, kind: str, hid: int, claim: dict | None) -> None:
        hardware = f"{kind} {hid}"
        friendly = claim_friendly(claim, kind, hid) or hardware.replace(
            "button", "Button"
        ).replace("axis", "Axis").replace("hat", "Hat")
        # The same input again (an axis moving): the card already shows it.
        if self._last.get(row.slug) == (friendly, hardware):
            return
        self._last[row.slug] = (friendly, hardware)
        idx = self._rows.index(row)
        self.dataChanged.emit(
            self.index(idx, 0),
            self.index(idx, 0),
            [QtCore.Qt.ItemDataRole.UserRole + 18, QtCore.Qt.ItemDataRole.UserRole + 19],
        )
        self.lastChanged.emit()

    def _dest_target(self, row: ModuleRow) -> tuple[int, dict]:
        """vJoy id and claim of an output card's output module."""
        cached = self._dest_targets.get(row.slug)
        if cached is not None:
            return cached
        from gremlin.modules.registry import resolve_vjoy_id

        name = row.raw_name or row.name
        vid = int(resolve_vjoy_id(name, row.guid) or 0)
        doc = _load_module_doc(name, row.guid) if vid else None
        target = (vid, read_claim(doc) if doc else {})
        self._dest_targets[row.slug] = target
        return target

    def _poll_dest_last(self) -> None:
        # Outputs only change while a profile runs.
        if not runtime_active():
            self._dest_snap = {}
            return
        from gremlin.modules.gate import dest_last_change
        from gremlin.modules.output import vjoy_state

        for row in self._rows:
            if row.direction != "dest":
                continue
            vid, claim = self._dest_target(row)
            if not vid:
                continue
            snap = vjoy_state(vid, claim)
            prev = self._dest_snap.get(row.slug)
            self._dest_snap[row.slug] = snap
            changed = dest_last_change(prev or {}, snap)
            if changed is None:
                continue
            kind, hid = changed
            self._set_last(row, kind, hid, claim)

    def _reload(self) -> None:
        self._dest_targets = {}
        self._source_claims = {}
        hidden = _hidden_slugs()
        # The names of the hidden cards (Home menu → Hidden Cards).
        hidden_names: dict[str, str] = {}
        self._hidden_names = hidden_names
        show_stubs = _show_stubs()
        rows: list[ModuleRow] = []

        for dev in device_initialization.physical_devices():
            name = dev.name
            slug = _slug(name)
            if slug in hidden:
                hidden_names[slug] = name
                continue
            saved = module_exists(name)
            if not _show_unconfigured(slug, saved, show_stubs):
                continue
            row = ModuleRow()
            row.slug = slug
            row.raw_name = name
            row.name = name
            row.guid = str(dev.device_guid)
            row.direction = "source"
            row.tab = "physical"
            row.bus = "DirectInput"
            row.vid = f"{dev.vendor_id:04X}"
            row.pid = f"{dev.product_id:04X}"
            row.photo = self._hw.profilePhotoUrl(name)
            if saved:
                doc = _load_module_doc(name, str(dev.device_guid))
                claim = read_claim(doc)
                row.is_stub = False
                row.is_module = True
                row.status = "Connected"
                row.damaged = _module_damage(name, str(dev.device_guid))
                if row.damaged:
                    row.status = "Module file damaged – inputs blocked"
                row.buttons = len(claim["buttons"]) or int(getattr(dev, "button_count", 0) or 0)
                row.axes = len(claim["axes"]) or int(getattr(dev, "axis_count", 0) or 0)
                row.hats = len(claim["hats"]) or int(getattr(dev, "hat_count", 0) or 0)
            else:
                row.is_stub = True
                row.is_module = False
                row.status = "Stub"
                row.buttons = int(getattr(dev, "button_count", 0) or 0)
                row.axes = int(getattr(dev, "axis_count", 0) or 0)
                row.hats = int(getattr(dev, "hat_count", 0) or 0)
            rows.append(row)

        def extra(slug: str, name: str, guid: str, tab: str, bus: str, direction: str) -> None:
            if slug in hidden:
                hidden_names[slug] = name
                return
            saved = module_exists(name)
            if not _show_unconfigured(slug, saved, show_stubs) and direction == "source":
                return
            row = ModuleRow()
            row.slug = slug
            row.name = name
            row.raw_name = name
            row.guid = guid
            row.direction = direction
            row.tab = tab
            row.bus = bus
            row.is_module = saved
            row.is_stub = not saved
            row.status = "Virtual" if direction == "dest" else ("Connected" if saved else "Stub")
            row.photo = self._hw.profilePhotoUrl(name)
            if saved:
                row.damaged = _module_damage(name, guid)
                if row.damaged:
                    row.status = "Module file damaged – inputs blocked"
                claim = read_claim(_load_module_doc(name, guid))
                row.buttons = len(claim["buttons"])
                row.axes = len(claim["axes"])
                row.hats = len(claim["hats"])
            rows.append(row)

        extra("keyboard", "Keyboard", KEYBOARD_GUID, "keyboard", "HID", "source")
        extra("osc", "OSC", OSC_GUID, "osc", "OSC", "source")

        from gremlin.modules.output import vjoy_in_use_elsewhere

        for vdev in device_initialization.vjoy_devices():
            name = f"vJoy {vdev.vjoy_id}"
            slug = _slug(name)
            if slug in hidden:
                hidden_names[slug] = name
                continue
            row = ModuleRow()
            row.slug = slug
            row.name = name
            row.raw_name = name
            row.guid = str(vdev.device_guid)
            row.direction = "dest"
            row.tab = "physical"
            row.bus = "DirectInput"
            row.status = "Virtual"
            if vjoy_in_use_elsewhere(vdev.vjoy_id):
                row.status = "In use by another program"
            row.is_stub = not module_exists(name)
            row.is_module = not row.is_stub
            row.photo = self._hw.profilePhotoUrl(name)
            if not row.photo:
                row.photo = self._hw.profilePhotoUrl("vJoy")
            if row.is_module:
                claim = read_claim(_load_module_doc(name, str(vdev.device_guid)))
                row.buttons = len(claim["buttons"]) or int(vdev.button_count)
                row.axes = len(claim["axes"]) or int(vdev.axis_count)
                row.hats = len(claim["hats"]) or int(vdev.hat_count)
            else:
                row.buttons = vdev.button_count
                row.axes = vdev.axis_count
                row.hats = vdev.hat_count
            rows.append(row)

        extra("xbox", "Xbox 360 Controller", XBOX_GUID, "xbox", "XInput", "dest")

        logical = Path(_maps_dir() / "logical_device.json")
        if logical.is_file() or module_exists("Logical Device"):
            extra("logical", "Logical Device", LOGICAL_GUID, "logical", "Logical", "source")

        if not self._focus and rows:
            src = next((r for r in rows if r.direction == "source" and r.status != "Stub"), None)
            if src is None:
                src = next((r for r in rows if r.direction == "source"), rows[0])
            self._focus = src.slug

        saved_order = _order_slugs()
        order = _renamed_into_order(saved_order, rows, hidden)
        if order:
            rank = {slug: index for index, slug in enumerate(order)}
            rows.sort(key=lambda row: rank.get(row.slug, 1000 + len(rank)))
        visible = [row.slug for row in rows]
        merged = _merged_order(order, visible)
        if visible and merged != saved_order:
            _set_order(merged)

        apply_bound_targets(rows)

        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.focusChanged.emit()
        self.panesChanged.emit()


@ta.QmlElement
class DriverInputModel(QtCore.QAbstractListModel):
    """Full hardware list for Configure module (press-to-check)."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"kind"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"hwId"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"claimed"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"friendly"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"lit"),
    }

    changed = QtCore.Signal()
    rowActivated = QtCore.Signal(int)
    userEdited = QtCore.Signal()
    undoChanged = QtCore.Signal()

    # Undo steps kept (each a check, a press that checks, or a name).
    UNDO_STEPS = 100

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._undo: list[dict[tuple, tuple[bool, str]]] = []
        self._redo: list[dict[tuple, tuple[bool, str]]] = []
        self._guid = ""
        # Why Save is refused for the loaded device ("" when it isn't).
        self._not_connected = ""
        self._device_name = ""
        self._rows: list[dict] = []
        # The device's controls were read (it was plugged in at load).
        self._read_from_device = False
        self._lit_index = -1
        self._last_saved_path = ""
        try:
            listener = event_handler.EventListener()
            listener.joystick_event.connect(
                self._on_joy, QtCore.Qt.ConnectionType.QueuedConnection
            )
            listener.device_change_event.connect(self._device_list_changed)
            listener.keyboard_event.connect(
                self._on_key, QtCore.Qt.ConnectionType.QueuedConnection
            )
        except Exception:
            pass

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if role not in self.roles or not index.isValid():
            return None
        row = self._rows[index.row()]
        return row.get(bytes(self.roles[role]).decode())

    def _device_list_changed(self) -> None:
        """The stick came or went while its setup is open: Save is refused
        while it is unplugged (and allowed again, with the work on screen,
        when it is back); opened while unplugged, its controls load now."""
        if not self._guid or self._is_keyboard() or self._is_osc():
            return
        if guid_key(self._guid) == guid_key(XBOX_GUID):
            return
        if _device_connected(self._guid):
            if not self._not_connected:
                return
            if self._read_from_device:
                self._not_connected = ""
            else:
                self.loadDevice(self._guid, self._device_name)
        elif not self._not_connected:
            self._not_connected = (
                f"Plug in {self._device_name or 'the device'} to save its setup. "
                "Nothing was saved."
            )

    @QtCore.Slot(str, str)
    def loadDevice(self, guid: str, device_name: str) -> None:
        self._guid = guid or ""
        self._device_name = device_name or ""
        self._not_connected = ""
        self._read_from_device = False
        rows: list[dict] = []
        claim = read_claim(_load_module_doc(device_name, guid)) if device_name else {
            "buttons": [],
            "axes": [],
            "hats": [],
            "friendly": {},
        }
        _plog(
            "open module",
            name=device_name,
            guid=guid,
            buttons=claim.get("buttons"),
            axes=claim.get("axes"),
            hats=claim.get("hats"),
            friendly=list((claim.get("friendly") or {})),
        )
        info = None
        if guid:
            try:
                info = hardware.device_info(guid)
            except Exception:
                info = None
        if self._is_keyboard():
            self._load_keyboard(claim)
            return
        if self._is_osc():
            self._load_osc(claim)
            return
        # The Xbox output (no Windows game controller behind it). A real Xbox
        # pad that is unplugged has its own id and is refused below instead.
        if info is None and (
            guid_key(guid) == guid_key(XBOX_GUID)
            or (not guid and "xbox" in (device_name or "").lower())
        ):
            self._load_xbox_dest(claim)
            return
        # A device that isn't plugged in shows no controls: saving would
        # erase its claims and names, so Save is refused until it is back.
        if guid and not _device_connected(guid):
            self._not_connected = (
                f"Plug in {device_name or 'the device'} to change its setup. "
                "Nothing was saved."
            )
        if info is not None:
            self._read_from_device = True
            for i in range(info.axis_count):
                hid = info.axis_map[i].axis_index
                rows.append(
                    {
                        "kind": "axis",
                        "hwId": hid,
                        "label": f"Axis {hid}",
                        "claimed": hid in claim["axes"],
                        "friendly": claim["friendly"].get(f"axis:{hid}", ""),
                        "lit": False,
                    }
                )
            for hid in range(1, info.button_count + 1):
                rows.append(
                    {
                        "kind": "button",
                        "hwId": hid,
                        "label": f"Button {hid}",
                        "claimed": hid in claim["buttons"],
                        "friendly": claim["friendly"].get(f"button:{hid}", ""),
                        "lit": False,
                    }
                )
            for hid in range(1, info.hat_count + 1):
                rows.append(
                    {
                        "kind": "hat",
                        "hwId": hid,
                        "label": f"Hat {hid}",
                        "claimed": hid in claim["hats"],
                        "friendly": claim["friendly"].get(f"hat:{hid}", ""),
                        "lit": False,
                    }
                )
        self.beginResetModel()
        self._rows = rows
        self._forget_steps()
        self.endResetModel()
        self.changed.emit()

    def _is_keyboard(self) -> bool:
        name = (self._device_name or "").strip().lower()
        return name == "keyboard" or guid_key(self._guid) == guid_key(KEYBOARD_GUID)

    def _is_osc(self) -> bool:
        name = (self._device_name or "").strip().lower()
        return name == "osc" or guid_key(self._guid) == guid_key(OSC_GUID)

    def _load_osc(self, claim: dict) -> None:
        from gremlin.osc import OscDevice
        from gremlin.types import InputType

        osc = OscDevice()
        claimed_btn = {int(x) for x in (claim.get("buttons") or [])}
        claimed_axis = {int(x) for x in (claim.get("axes") or [])}
        friendly = claim.get("friendly") or {}
        rows: list[dict] = []
        for label in osc.labels_of_type():
            item = osc.find_address(label)
            if item is None:
                continue
            if item.type == InputType.JoystickAxis:
                kind, claimed = "axis", item.id in claimed_axis
            else:
                kind, claimed = "button", item.id in claimed_btn
            rows.append(
                {
                    "kind": kind,
                    "hwId": int(item.id),
                    "label": item.label,
                    "claimed": claimed if (claimed_btn or claimed_axis) else True,
                    "friendly": friendly.get(f"{kind}:{int(item.id)}", ""),
                    "lit": False,
                }
            )
        self.beginResetModel()
        self._rows = rows
        self._forget_steps()
        self.endResetModel()
        self.changed.emit()

    def _load_keyboard(self, claim: dict) -> None:
        saved = {int(k) for k in (claim.get("keys") or [])}
        # Never saved: every key ticked (they all pass). Saved with none: none.
        chosen = bool(saved) or bool(claim.get("keysChosen"))
        friendly = claim.get("friendly") or {}
        skip = {"noname", "eraseeof", "zoom"}
        seen: set[int] = set()
        rows = []

        def add_key(key) -> None:
            hid = key_id(key.scan_code, key.is_extended)
            if hid in seen:
                return
            seen.add(hid)
            rows.append(
                {
                    "kind": "key",
                    "hwId": hid,
                    "label": key.name,
                    "claimed": hid in saved if chosen else True,
                    "friendly": friendly.get(f"key:{hid}", ""),
                    "lit": False,
                }
            )

        for name, key in gremlin_keyboard.g_name_to_key.items():
            if name in skip:
                continue
            add_key(key)
        for ch in list("abcdefghijklmnopqrstuvwxyz0123456789`-=[]\\;'\",./"):
            try:
                add_key(gremlin_keyboard.key_from_name(ch))
            except Exception:
                pass
        for hid in saved:
            if hid in seen:
                continue
            scan = hid & 0xFFFF
            ext = bool(hid >> 16)
            try:
                add_key(gremlin_keyboard.key_from_code(scan, ext))
            except Exception:
                rows.append(
                    {
                        "kind": "key",
                        "hwId": hid,
                        "label": f"Key {scan}",
                        "claimed": True,
                        "friendly": friendly.get(f"key:{hid}", ""),
                        "lit": False,
                    }
                )
        self.beginResetModel()
        self._rows = rows
        self._forget_steps()
        self.endResetModel()
        self.changed.emit()

    def _on_key(self, event: event_handler.Event) -> None:
        if event is None or not self._is_keyboard():
            return
        if event.is_pressed is False:
            return
        ident = event.identifier
        try:
            scan, ext = ident[0], ident[1]
        except Exception:
            return
        hid = key_id(int(scan), bool(ext))
        try:
            label = gremlin_keyboard.key_from_code(int(scan), bool(ext)).name
        except Exception:
            label = f"Key {scan}"
        found = None
        for i, row in enumerate(self._rows):
            if row["kind"] == "key" and int(row["hwId"]) == hid:
                found = i
                break
        if found is None:
            # A key that wasn't listed: added ticked, an Undo step like a press.
            self._step()
            self.beginInsertRows(QtCore.QModelIndex(), len(self._rows), len(self._rows))
            self._rows.append(
                {
                    "kind": "key",
                    "hwId": hid,
                    "label": label,
                    "claimed": True,
                    "friendly": "",
                    "lit": False,
                }
            )
            self.endInsertRows()
            found = len(self._rows) - 1
            self.changed.emit()
        self.markPressed("key", hid)

    def _load_xbox_dest(self, claim: dict) -> None:
        labels = [
            ("button", 1, "A"),
            ("button", 2, "B"),
            ("button", 3, "X"),
            ("button", 4, "Y"),
            ("button", 5, "LB"),
            ("button", 6, "RB"),
            ("button", 7, "Back"),
            ("button", 8, "Start"),
            ("button", 9, "LS"),
            ("button", 10, "RS"),
            ("axis", 1, "Left stick X"),
            ("axis", 2, "Left stick Y"),
            ("axis", 3, "Right stick X"),
            ("axis", 4, "Right stick Y"),
            ("axis", 5, "LT"),
            ("axis", 6, "RT"),
            ("hat", 1, "D-pad"),
        ]
        rows = []
        buckets = {"button": "buttons", "axis": "axes", "hat": "hats"}
        for kind, hid, label in labels:
            key = f"{kind}:{hid}"
            rows.append(
                {
                    "kind": kind,
                    "hwId": hid,
                    "label": label,
                    "claimed": hid in claim.get(buckets[kind], []),
                    "friendly": claim.get("friendly", {}).get(key, ""),
                    "lit": False,
                }
            )
        self.beginResetModel()
        self._rows = rows
        self._forget_steps()
        self.endResetModel()
        self.changed.emit()

    def _same_device(self, event: event_handler.Event) -> bool:
        if event is None:
            return False
        if guid_key(event.device_guid) == guid_key(self._guid):
            return True
        if not self._device_name:
            return False
        try:
            devices = list(device_initialization.joystick_devices())
        except Exception:
            devices = []
        want = _slug(self._device_name)
        ev = guid_key(event.device_guid)
        for dev in devices:
            if guid_key(dev.device_guid) != ev:
                continue
            if _slug(dev.name) == want or dev.name == self._device_name:
                self._guid = str(dev.device_guid)
                return True
        return False

    def _on_joy(self, event: event_handler.Event) -> None:
        try:
            if event is None or not self._rows:
                return
            if not self._same_device(event):
                return
            et = getattr(event, "event_type", None)
            kind = "button"
            if et == InputType.JoystickAxis:
                kind = "axis"
                try:
                    if abs(float(event.value)) < 0.35:
                        return
                except Exception:
                    return
            elif et == InputType.JoystickHat:
                kind = "hat"
                if getattr(event, "value", None) in (0, (0, 0), "center", None):
                    return
            elif et == InputType.JoystickButton:
                if event.is_pressed is False:
                    return
            try:
                hid = int(event.identifier)
            except Exception:
                return
            self.markPressed(kind, hid)
        except Exception:
            return

    # --- Undo / Redo: the checks and names, as they were before each edit ---

    def _marks(self) -> dict[tuple, tuple[bool, str]]:
        # By control: a pressed key that wasn't listed adds a row.
        return {
            (r["kind"], int(r["hwId"])): (
                bool(r["claimed"]), str(r.get("friendly") or "")
            )
            for r in self._rows
        }

    def _step(self) -> None:
        """Before an edit: keep how it was, for Undo."""
        self._undo.append(self._marks())
        del self._undo[: -self.UNDO_STEPS]
        self._redo.clear()
        self.undoChanged.emit()

    def _forget_steps(self) -> None:
        if self._undo or self._redo:
            self._undo.clear()
            self._redo.clear()
            self.undoChanged.emit()

    def _put_marks(self, marks: dict[tuple, tuple[bool, str]]) -> None:
        for row in self._rows:
            # A row added since (a key pressed): it wasn't claimed then.
            claimed, friendly = marks.get((row["kind"], int(row["hwId"])), (False, ""))
            row["claimed"] = claimed
            row["friendly"] = friendly
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._rows) - 1, 0),
                [
                    QtCore.Qt.ItemDataRole.UserRole + 4,
                    QtCore.Qt.ItemDataRole.UserRole + 5,
                ],
            )
        self.userEdited.emit()
        self.undoChanged.emit()

    @QtCore.Slot()
    def undo(self) -> None:
        if self._undo:
            self._redo.append(self._marks())
            self._put_marks(self._undo.pop())

    @QtCore.Slot()
    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._marks())
            self._put_marks(self._redo.pop())

    def _can_undo(self) -> bool:
        return bool(self._undo)

    def _can_redo(self) -> bool:
        return bool(self._redo)

    canUndo = QtCore.Property(bool, fget=_can_undo, notify=undoChanged)
    canRedo = QtCore.Property(bool, fget=_can_redo, notify=undoChanged)

    @QtCore.Slot(int, bool)
    def setClaimed(self, index: int, claimed: bool) -> None:
        if not (0 <= index < len(self._rows)):
            return
        if bool(self._rows[index]["claimed"]) == bool(claimed):
            return
        self._step()
        self._rows[index]["claimed"] = bool(claimed)
        ix = self.index(index, 0)
        self.dataChanged.emit(ix, ix, [QtCore.Qt.ItemDataRole.UserRole + 4])
        self.userEdited.emit()

    @QtCore.Slot(int, str)
    def setFriendly(self, index: int, name: str) -> None:
        if not (0 <= index < len(self._rows)):
            return
        if str(self._rows[index].get("friendly") or "") == str(name or ""):
            return
        self._step()
        self._rows[index]["friendly"] = name
        ix = self.index(index, 0)
        self.dataChanged.emit(ix, ix, [QtCore.Qt.ItemDataRole.UserRole + 5])
        self.userEdited.emit()

    def _set_lit(self, index: int, lit: bool) -> None:
        if not (0 <= index < len(self._rows)):
            return
        if bool(self._rows[index].get("lit")) == bool(lit):
            return
        self._rows[index]["lit"] = bool(lit)
        ix = self.index(index, 0)
        self.dataChanged.emit(ix, ix, [QtCore.Qt.ItemDataRole.UserRole + 6])

    @QtCore.Slot(str, int)
    def markPressed(self, kind: str, hw_id: int) -> None:
        for i, row in enumerate(self._rows):
            if row["kind"] == kind and int(row["hwId"]) == int(hw_id):
                if not row["claimed"]:
                    self.setClaimed(i, True)
                if self._lit_index == i:
                    return
                if self._lit_index >= 0:
                    self._set_lit(self._lit_index, False)
                self._lit_index = i
                self._set_lit(i, True)
                self.rowActivated.emit(i)
                return

    @QtCore.Slot(result=str)
    def saveBlockedReason(self) -> str:
        """Why Save is refused for the loaded device ("" when it isn't)."""
        return self._not_connected

    @QtCore.Slot(str, str, result=bool)
    def saveClaim(self, device_name: str, direction: str) -> bool:
        if self.saveBlockedReason():
            _plog("save claim refused", name=device_name, reason=self._not_connected)
            return False
        name = device_name or self._device_name
        # The file Module Setup opened (the device's bound file), not one
        # named after the device: a device whose name changed kept its file.
        slug = resolve_module_slug(name, self._guid)
        path = _maps_dir() / f"{slug}.json"
        try:
            doc = module_file.load_for_update(path)
        except module_file.ModuleFileDamaged as damaged:
            trace("READ", "Configure Module", "saveClaim", path, "damaged")
            module_file.report_refused(damaged)
            return False
        trace("READ", "Configure Module", "saveClaim", path, "ok")
        buttons = [int(r["hwId"]) for r in self._rows if r["kind"] == "button" and r["claimed"]]
        axes = [int(r["hwId"]) for r in self._rows if r["kind"] == "axis" and r["claimed"]]
        hats = [int(r["hwId"]) for r in self._rows if r["kind"] == "hat" and r["claimed"]]
        keys = [int(r["hwId"]) for r in self._rows if r["kind"] == "key" and r["claimed"]]
        friendly = {}
        for r in self._rows:
            if r["claimed"] and r.get("friendly"):
                friendly[f"{r['kind']}:{int(r['hwId'])}"] = str(r["friendly"])
        doc["kind"] = "control.hardware"
        doc["device"] = name
        if is_output_name(name):
            doc["direction"] = "dest"
        elif self._guid and _device_connected(self._guid):
            # A physical stick is an input (a file the old Output menu
            # marked "dest" blocked every input; saving here repairs it).
            doc["direction"] = "source"
        elif doc.get("direction") not in ("source", "dest"):
            doc["direction"] = direction or "source"
        if self._guid:
            doc["boundName"] = name
            # GUID stays local-only; stored for this machine bind, not exported.
            doc["boundGuidLocal"] = self._guid
        doc["claim"] = {
            "buttons": buttons,
            "axes": axes,
            "hats": hats,
            "keys": keys,
            "friendly": friendly,
        }
        if self._is_keyboard() and not keys:
            doc["claim"]["keysChosen"] = True
        doc.setdefault("space", "world")
        doc.setdefault("pageW", 32000)
        doc.setdefault("pageH", 18000)
        doc.setdefault("photoWell", 0.75)
        doc.setdefault("nodes", [])
        folder = _maps_dir() / slug
        if folder.is_dir():
            photos = sorted(p for p in folder.glob("photo.*") if p.is_file())
            if photos:
                doc["image"] = f"{slug}/{photos[-1].name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(doc, indent=2) + "\n"
        _plog(
            "save claim",
            name=name,
            guid=self._guid,
            direction=direction,
            path=str(path),
            buttons=buttons,
            axes=axes,
            hats=hats,
            friendly=list(friendly),
        )
        try:
            module_file.write_text(path, text)
            written = json.loads(path.read_text(encoding="utf-8"))
            trace("SAVE", "Configure Module", "saveClaim", path, "ok")
        except (OSError, json.JSONDecodeError) as exc:
            _plog("save claim failed", path=str(path), error=exc)
            trace("SAVE", "Configure Module", "saveClaim", path, "error")
            return False
        got = written.get("claim") if isinstance(written.get("claim"), dict) else {}
        if [int(n) for n in (got.get("buttons") or [])] != buttons:
            _plog("save claim mismatch", path=str(path), field="buttons", wrote=buttons, read=got.get("buttons"))
            return False
        if [int(n) for n in (got.get("axes") or [])] != axes:
            _plog("save claim mismatch", path=str(path), field="axes", wrote=axes, read=got.get("axes"))
            return False
        if [int(n) for n in (got.get("hats") or [])] != hats:
            _plog("save claim mismatch", path=str(path), field="hats", wrote=hats, read=got.get("hats"))
            return False
        bind_module_file(name, self._guid, slug)
        signal.configChanged.emit()
        _plog("save claim ok", path=str(path), bytes=path.stat().st_size)
        self._last_saved_path = str(path)
        return True

    @QtCore.Slot(result=str)
    def lastSavedPath(self) -> str:
        return self._last_saved_path
