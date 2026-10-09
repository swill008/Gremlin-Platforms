# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""One zip for a whole device: a working copy of what was exported.

Import is destructive by design: each ticked piece replaces what is on this
machine (module file pieces; for a ticked mode, the device's wires and
actions in that mode), except Checked controls: the pack's are added to the
ones checked here (08 Q3). The window warns first, the previous module file is
kept in the imported folder, and Undo Import puts back the last import."""

from __future__ import annotations

import atexit
import io
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from collections.abc import Callable
from typing import TYPE_CHECKING

from gremlin.ui.live_debug import trace
from gremlin.modules import module_file, store
from gremlin.modules.claim import claim_ids
from gremlin.modules.registry import is_output_name
from gremlin.ui.input_pairing import dest_labels_for_item, parse_guid
from gremlin.modules.store import (
    PICTURE_EXT as _IMAGE_EXT,
    doc_direction as _doc_direction,
    match_known_device as _match_pack_device,
    member_kind,
    safe_picture_name as _safe_name,
    suggest_device_name as _suggest_pack_name,
    unique_archive as _unique_archive,
)

if TYPE_CHECKING:
    from gremlin.profile import Profile

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_KIND_WORD = {"btn": "Button", "button": "Button", "axis": "Axis", "hat": "Hat"}
# The pack format this program writes and reads. A newer pack is refused.
PACK_FORMAT = 2
# The Button Map's view settings (module file "ui"), in two rows.
_MAP_VIEW_KEYS = (
    "gridOn", "snapOn", "snapEntOn", "gridSize", "viewPct", "panX", "panY",
    "guidesX", "guidesY", "guidesOn",
)
_PRINT_KEYS = ("printArea", "print")
_FRIENDLY_KIND = {"btn": "button", "button": "button", "axis": "axis", "hat": "hat"}
_VIEW_WORDS = {
    "layout": "Layout",
    "showPads": "Show pads",
    "showHats": "Show hats",
    "showMeters": "Show meters",
    "meterStyle": "Meter style",
    "meterWidth": "Meter width",
    "buttonStyle": "Button style",
    "buttonSize": "Button size",
    "buttonColumns": "Button columns",
    "buttonWidth": "Button width",
    "colorLive": "Live color",
    "colorMeter": "Meter color",
    "colorPress": "Press color",
    "padAX": "Pad A horizontal axis",
    "padAY": "Pad A vertical axis",
    "padBX": "Pad B horizontal axis",
    "padBY": "Pad B vertical axis",
}


def size_text(count: int) -> str:
    if count < 1024:
        return f"{count} bytes" if count != 1 else "1 byte"
    if count < 1024 * 1024:
        value = count / 1024
        text = f"{value:.1f}" if value < 10 else str(round(value))
        return f"{text} KB"
    value = count / (1024 * 1024)
    text = f"{value:.1f}" if value < 10 else str(round(value))
    return f"{text} MB"


def _claim(doc: dict) -> dict:
    raw = doc.get("claim")
    return raw if isinstance(raw, dict) else {}


def _friendly(doc: dict) -> dict:
    raw = _claim(doc).get("friendly")
    return raw if isinstance(raw, dict) else {}


def _control_name(kind: str, number: int, names: dict) -> str:
    word = _KIND_WORD.get(kind, "Control")
    key = f"{_FRIENDLY_KIND.get(kind, kind)}:{number}"
    label = str(names.get(key) or "").strip()
    base = f"{word} {number}"
    return f"{base} — {label}" if label else base


def _control_lines(doc: dict) -> list[str]:
    claim = _claim(doc)
    names = _friendly(doc)
    lines: list[str] = []
    for number in claim_ids(claim, "button"):
        lines.append(_control_name("button", number, names))
    for number in claim_ids(claim, "axis"):
        lines.append(_control_name("axis", number, names))
    for number in claim_ids(claim, "hat"):
        lines.append(_control_name("hat", number, names))
    return lines


def _name_lines(doc: dict) -> list[str]:
    names = _friendly(doc)
    lines: list[str] = []
    claim = _claim(doc)
    groups = (
        ("button", "buttons"),
        ("axis", "axes"),
        ("hat", "hats"),
    )
    for kind, key in groups:
        for number in claim_ids(claim, kind):
            label = str(names.get(f"{kind}:{number}") or "").strip()
            if label:
                lines.append(f"{_KIND_WORD[kind]} {number} — {label}")
    return lines


def _calibration_lines(doc: dict) -> list[str]:
    raw = doc.get("calibration")
    if not isinstance(raw, dict):
        return []
    lines: list[str] = []
    for key in sorted(raw, key=lambda item: int(item) if str(item).isdigit() else 0):
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        value = raw[key]
        if isinstance(value, (list, tuple)) and len(value) >= 4:
            text = f"Axis {number}: {value[0]} to {value[3]}"
            if len(value) >= 5 and value[4]:
                text += ", inverted"
            lines.append(text)
        else:
            lines.append(f"Axis {number}")
    return lines


def _view_lines(doc: dict) -> list[str]:
    view = doc.get("view")
    if not isinstance(view, dict) or not view:
        return []
    lines: list[str] = []
    for key, label in _VIEW_WORDS.items():
        if key not in view:
            continue
        value = view[key]
        if isinstance(value, bool):
            lines.append(f"{label}: {'Yes' if value else 'No'}")
        else:
            lines.append(f"{label}: {value}")
    extra = [key for key in view if key not in _VIEW_WORDS and key != "meters"]
    meters = view.get("meters")
    if isinstance(meters, list) and meters:
        lines.append("Meters: " + ", ".join(str(item) for item in meters))
    if extra:
        lines.append(f"Other settings: {len(extra)}")
    return lines


def _node_controls(node: dict) -> set[tuple[str, int]]:
    found: set[tuple[str, int]] = set()
    kind = str(node.get("kind") or "")
    if kind == "image":
        return found
    try:
        if node.get("hwId") is not None:
            found.add((kind, int(node.get("hwId"))))
    except (TypeError, ValueError):
        pass
    for member in node.get("members") or []:
        if not isinstance(member, dict):
            continue
        try:
            found.add((member_kind(node, member), int(member.get("hwId"))))
        except (TypeError, ValueError):
            continue
    return found


def _chip_lines(doc: dict) -> list[str]:
    lines: list[str] = []
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "")
        if kind == "image":
            lines.append("Picture on the map")
            continue
        if kind == "stack":
            parts = []
            for member in node.get("members") or []:
                if not isinstance(member, dict):
                    continue
                label = str(member.get("friendly") or "").strip()
                number = member.get("hwId")
                parts.append(label or f"{number}")
            if parts:
                lines.append("Stack: " + ", ".join(parts))
            continue
        word = _KIND_WORD.get(kind, "Control")
        number = node.get("hwId")
        text = f"{word} {number}" if number is not None else word
        label = str(node.get("friendly") or "").strip()
        if label:
            text += f" — {label}"
        lines.append(text)
    return lines


def _ui(doc: dict) -> dict:
    raw = doc.get("ui")
    return raw if isinstance(raw, dict) else {}


def _map_view_lines(doc: dict) -> list[str]:
    ui = _ui(doc)
    if not any(key in ui for key in _MAP_VIEW_KEYS):
        return []
    lines = ["Pan, zoom, grid and guides: how the map was last viewed."]
    if "viewPct" in ui:
        lines.append(f"Zoom: {ui.get('viewPct')}%")
    if "gridSize" in ui:
        lines.append(f"Grid size: {ui.get('gridSize')}")
    return lines


def _print_lines(doc: dict) -> list[str]:
    ui = _ui(doc)
    if not any(key in ui for key in _PRINT_KEYS):
        return []
    lines = ["The print area and the Print & Export settings."]
    area = isinstance(ui.get("printArea"), dict)
    lines.append("Print area: " + ("set" if area else "none"))
    setup = ui.get("print")
    if not isinstance(setup, dict):
        setup = {}
    if setup.get("paper"):
        lines.append(f"Size: {setup.get('paper')}")
    return lines


def _catalog_lines(doc: dict) -> list[str]:
    catalog = doc.get("catalog")
    if not isinstance(catalog, dict) or not catalog:
        return []
    return [
        "How the Configuration page looks: rows, colors and sizes.",
        f"Settings: {len(catalog)}",
    ]


def _clip(lines: list[str], limit: int = 40) -> str:
    if len(lines) <= limit:
        return "\n".join(lines)
    hidden = len(lines) - limit
    return "\n".join(lines[:limit] + [f"And {hidden} more."])


def _item(item_id: str, title: str, body: str, checked: bool = True, kind: str = "text") -> dict:
    return {
        "id": item_id,
        "title": title,
        "body": body,
        "checked": checked,
        "kind": kind,
        "needs": [],
    }


def _module_items(prefix: str, doc: dict, pictures: list[dict]) -> list[dict]:
    items: list[dict] = []
    checks = _control_lines(doc)
    if checks:
        items.append(_item(prefix + "checks", "Checked controls", _clip(checks)))
    names = _name_lines(doc)
    if names:
        items.append(_item(prefix + "names", "Friendly names", _clip(names)))
    calibration = _calibration_lines(doc)
    if calibration:
        items.append(_item(prefix + "calibration", "Calibration", _clip(calibration)))
    view = _view_lines(doc)
    if view:
        items.append(_item(prefix + "view", "Output View Appearance", _clip(view)))
    catalog = _catalog_lines(doc)
    if catalog:
        items.append(
            _item(prefix + "catalog", "Configuration Appearance", _clip(catalog))
        )
    chips = _chip_lines(doc)
    needs = [row["id"] for row in pictures if row.get("onMap")]
    if chips:
        row = _item(prefix + "layout", "Map", _clip(chips))
        row["needs"] = needs
        items.append(row)
    for picture in pictures:
        items.append(picture["item"])
    map_view = _map_view_lines(doc)
    if map_view:
        items.append(
            _item(prefix + "mapview", "Map view", _clip(map_view), checked=False)
        )
    print_setup = _print_lines(doc)
    if print_setup:
        title = "Print area and print settings"
        items.append(_item(prefix + "print", title, _clip(print_setup), checked=False))
    return items


def module_text(doc: dict, parts: list[str] | None = None) -> str:
    """A module file (or only its changed parts) in the words of the pack's
    rows, for History's Before and After (08 Q13): "Checked controls",
    "Button 3 — Fire", "Axis 1: 0 to 65535", not raw JSON."""
    wanted = set(parts or doc)
    sections: list[tuple[str, list[str]]] = []
    if "claim" in wanted:
        sections.append(("Checked controls", _control_lines(doc)))
        names = _name_lines(doc)
        if names:
            sections.append(("Friendly names", names))
    if "calibration" in wanted:
        sections.append(("Calibration", _calibration_lines(doc)))
    if "view" in wanted:
        sections.append(("Output View Appearance", _view_lines(doc)))
    if "catalog" in wanted:
        sections.append(("Configuration Appearance", _catalog_lines(doc)))
    if "nodes" in wanted:
        sections.append(("Map", _chip_lines(doc)))
    if wanted & {"photo", "image"}:
        photo = str(doc.get("image") or doc.get("photo") or "")
        sections.append(("Photo", [Path(photo).name] if photo else []))
    if "ui" in wanted:
        sections.append(("Map view", _map_view_lines(doc) + _print_lines(doc)))
    shown = {"claim", "calibration", "view", "catalog", "nodes", "photo", "image", "ui"}
    other = [
        f"{key}: {doc[key]}" if isinstance(doc[key], (str, int, float)) else key
        for key in sorted(wanted - shown)
        if key in doc
    ]
    if other:
        sections.append(("Other settings", other))
    blocks = [
        f"{title}:\n" + (_clip(lines) if lines else "None.")
        for title, lines in sections
    ]
    return "\n\n".join(blocks)


def _picture_item(arc: str, title: str, url: str, on_map: bool) -> dict:
    row = _item("pic:" + arc, title, title, kind="image")
    row["url"] = url
    row["onMap"] = on_map
    return row


def _take_image(stored: str, resolve, used: set[str], files: list[tuple[Path, str]]) -> str:
    found = resolve(stored) if stored else None
    if not found or not found.is_file():
        return ""
    arc = _safe_name(found.name, "photo" + found.suffix.lower())
    if arc in used:
        stem, ext = Path(arc).stem, Path(arc).suffix
        number = 1
        while f"{stem}_{number}{ext}" in used:
            number += 1
        arc = f"{stem}_{number}{ext}"
    used.add(arc)
    files.append((found, arc))
    return arc


def _rewrite_images(doc: dict, resolve, used: set[str], files: list[tuple[Path, str]]) -> tuple[dict, list[dict]]:
    packed = json.loads(json.dumps(doc))
    pictures: list[dict] = []
    image = str(packed.get("image") or "")
    photo_arc = _take_image(image, resolve, used, files) if image else ""
    if photo_arc:
        packed["image"] = photo_arc
        pictures.append({
            "arc": photo_arc,
            "onMap": False,
            "item": _picture_item(photo_arc, "Device photo", "", False),
        })
    else:
        packed.pop("image", None)
    map_count = 0
    for node in packed.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("kind") != "image" and node.get("shape") != "image":
            continue
        arc = _take_image(str(node.get("src") or ""), resolve, used, files)
        if not arc:
            node.pop("src", None)
            node.pop("srcUrl", None)
            continue
        node["src"] = arc
        node.pop("srcUrl", None)
        map_count += 1
        if any(row["arc"] == arc for row in pictures):
            for row in pictures:
                if row["arc"] == arc:
                    row["onMap"] = True
                    row["item"]["onMap"] = True
            continue
        pictures.append({
            "arc": arc,
            "onMap": True,
            "item": _picture_item(arc, f"Map picture {map_count}", "", True),
        })
    return packed, pictures


def _read_doc(path: Path) -> dict | None:
    """A module file's content; None when it is missing or damaged (a
    damaged one is named in the log and skipped, 08 S52)."""
    return (store.read_path(path) or None) if path.is_file() else None


def _pack_key(device_name: str) -> str:
    """An output's key in a pack that has none in its label (an older
    pack): the slug of the name it was exported under."""
    return store.own_slug(device_name)


def _target_direction(name: str, guid: str = "") -> str:
    return store.direction_for(name, guid)


def _walk_actions(action, found: dict[int, object]) -> None:
    if action is None or id(action) in found:
        return
    found[id(action)] = action
    getter = getattr(action, "get_actions", None)
    if not callable(getter):
        return
    try:
        buckets = getter()
    except Exception:
        return
    if not isinstance(buckets, (list, tuple)):
        return
    for bucket in buckets:
        if isinstance(bucket, (list, tuple)):
            for child in bucket:
                _walk_actions(child, found)
        else:
            _walk_actions(bucket, found)


def _input_word(item) -> str:
    from gremlin.types import InputType

    kind = getattr(item, "input_type", None)
    number = getattr(item, "input_id", "")
    if kind == InputType.JoystickAxis:
        return f"Axis {number}"
    if kind == InputType.JoystickHat:
        return f"Hat {number}"
    if kind == InputType.JoystickButton:
        return f"Button {number}"
    return f"Control {number}"


def _mode_tree(profile: Profile, names: list[str]) -> dict[str, str]:
    """Each mode's parent ("" at the top), for these modes and their parents."""
    tree: dict[str, str] = {}
    pending = list(names)
    while pending:
        name = pending.pop()
        if name in tree:
            continue
        try:
            node = profile.modes.find_mode(name)
        except Exception:
            tree[name] = ""
            continue
        parent = node.parent.value if node.parent is not None else ""
        tree[name] = parent or ""
        if parent:
            pending.append(parent)
    return tree


def pack_modes(guid: str) -> list[dict]:
    """The modes in which this device has actions: [{name, count}]."""
    try:
        from gremlin.shared_state import current_profile
    except Exception:
        return []
    uid = parse_guid(guid)
    if current_profile is None or uid is None:
        return []
    counts: dict[str, int] = {}
    for item in current_profile.inputs.get(uid, []) or []:
        if getattr(item, "action_sequences", None):
            mode = str(getattr(item, "mode", "") or "Default")
            counts[mode] = counts.get(mode, 0) + 1
    return [{"name": name, "count": counts[name]} for name in sorted(counts)]


def _collect_wires(
    guid: str, only_modes: list[str] | None = None, profile: Profile | None = None
) -> dict:
    """The device's wires in a profile (None: the open one)."""
    text = str(guid or "").strip()
    empty = {"modes": [], "actions": [], "outputs": [], "tree": {}}
    if not text:
        return empty
    try:
        from gremlin.shared_state import current_profile
        from gremlin.util import read_action_ids
    except Exception:
        return empty
    if profile is None:
        profile = current_profile
    uid = parse_guid(text)
    if profile is None or uid is None:
        return empty
    items = profile.inputs.get(uid, []) or []
    modes: dict[str, dict] = {}
    actions: dict[uuid.UUID, object] = {}
    outputs: list[str] = []
    seen_out: set[str] = set()
    try:
        for item in items:
            if not getattr(item, "action_sequences", None):
                continue
            try:
                xml = ElementTree.tostring(item.to_xml(), encoding="unicode")
            except Exception:
                continue
            mode = str(getattr(item, "mode", "") or "Default")
            if only_modes is not None and mode not in only_modes:
                continue
            dest = ""
            try:
                dest = " + ".join(dest_labels_for_item(item))
            except Exception:
                dest = ""
            line = _input_word(item) + (f" → {dest}" if dest else "")
            bucket = modes.setdefault(mode, {"name": mode, "lines": [], "inputs": []})
            bucket["lines"].append(line)
            bucket["inputs"].append(xml)
            for seq in item.action_sequences:
                root = getattr(seq, "root_action", None)
                walked: dict[int, object] = {}
                _walk_actions(root, walked)
                for action in walked.values():
                    if getattr(action, "id", None) is not None:
                        actions[action.id] = action
                pending = [root]
                while pending:
                    action = pending.pop()
                    if action is None:
                        continue
                    node = None
                    try:
                        node = action.to_xml()
                    except Exception:
                        node = None
                    if node is None:
                        continue
                    for child_id in read_action_ids(node):
                        if child_id in actions or not profile.library.has_action(child_id):
                            continue
                        child = profile.library.get_action(child_id)
                        actions[child_id] = child
                        pending.append(child)
            for label in (dest.split(" + ") if dest else []):
                if label.lower().startswith("vjoy"):
                    parts = label.split()
                    if len(parts) >= 2:
                        title = f"vJoy {parts[1]}"
                        if title not in seen_out:
                            seen_out.add(title)
                            outputs.append(title)
                elif label.lower().startswith("xbox"):
                    parts = label.split()
                    title = " ".join(parts[:2]) if len(parts) >= 2 else "Xbox"
                    if title not in seen_out:
                        seen_out.add(title)
                        outputs.append(title)
    except Exception:
        return empty
    action_xml: list[str] = []
    for action in actions.values():
        try:
            node = action.to_xml()
        except Exception:
            node = None
        if node is not None:
            action_xml.append(ElementTree.tostring(node, encoding="unicode"))
    try:
        action_xml = _with_logical_uids(action_xml)
    except Exception:
        pass
    return {
        "modes": list(modes.values()),
        "actions": action_xml,
        "outputs": outputs,
        "tree": _mode_tree(profile, list(modes)),
    }


def _output_doc(name: str, resolve, used: set[str], files: list[tuple[Path, str]]) -> tuple[dict, list[dict]] | None:
    match = _match_pack_device(name)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    # The file the output uses (the store's rule), and its slug as the
    # pack's key; a renamed vJoy's own-name slug could differ (AU-64).
    path = store.path_for(name, guid)
    slug = path.stem
    doc = _read_doc(path)
    if not doc:
        return None
    packed, pictures = _rewrite_images(doc, resolve, used, files)
    packed.pop("boundGuidLocal", None)
    packed.pop("boundName", None)
    packed["device"] = name
    if is_output_name(name):
        packed["direction"] = "dest"
    packed["pack"] = {"exportedName": name, "exportedGuid": guid, "slug": slug}
    return packed, pictures


_NO_FILE = "This device has no module file yet."


def export_refusal(path: Path) -> str:
    """Why a device's module file can't be exported: none yet (08 S51), or
    damaged, pointing to Start Fresh (08 Q19). "" when it can."""
    path = Path(path)
    if not path.is_file():
        return _NO_FILE
    reason = store.damage_of(path)
    if reason:
        return (
            f"The module file {path.name} is damaged ({reason}), so it can't "
            "be exported. Choose Start Fresh on the device's card first (the "
            "damaged file is kept)."
        )
    return ""


def _device_path(name: str, guid: str = "") -> Path:
    if guid:
        # By its id: an unplugged twin's own file, never the other twin's.
        return store.path_for_id(name, guid)
    match = _match_pack_device(name)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    return store.path_for(name, guid)


def _pack_label(name: str, guid: str, notes: dict | None) -> dict:
    from datetime import date

    from gremlin.util import get_code_version

    label = {
        "exportedName": name,
        "exportedGuid": guid,
        "format": PACK_FORMAT,
        "program": get_code_version(),
        "exportedOn": date.today().isoformat(),
    }
    notes = notes if isinstance(notes, dict) else {}
    author = " ".join(str(notes.get("author") or "").split())
    note = str(notes.get("note") or "").strip()
    if author:
        label["author"] = author
    if note:
        label["note"] = note
    return label


def pack_devices() -> list[dict]:
    """The Device Pack's device list: store.known_devices() rows, each with
    damaged (its module file can't be read), canExport (a module file that
    can be read) and label, the name shown, marked "(file damaged)" when it is
    (08 S106). The window opens on the first row that can be exported."""
    rows = store.known_devices()
    for row in rows:
        name = str(row.get("name") or "")
        damaged = False
        if row.get("hasFile"):
            path = store.path_for(name, str(row.get("guid") or ""))
            damaged = bool(store.damage_of(path))
        row["damaged"] = damaged
        row["canExport"] = bool(row.get("hasFile")) and not damaged
        # The row's own label: Home's name for that id (twins, 08 S106a).
        base = str(row.get("label") or name)
        row["label"] = f"{base} (file damaged)" if damaged else base
    return rows


_TWINS = (
    "More than one device is called {name}: export it from the Device "
    "Library, where each has its own id."
)


def _ids_named(name: str, profile: Profile | None = None) -> dict[str, str]:
    """{id key: id} of every device called name: plugged in now, or in the
    profile's device list (the open one when profile is None)."""
    want = " ".join(str(name or "").split()).casefold()
    found: dict[str, str] = {}

    def add(label: object, guid: object) -> None:
        text = store.guid_text(guid) if guid else ""
        key = store.stored_guid_key(text)
        if key and " ".join(str(label or "").split()).casefold() == want:
            found.setdefault(key, text)

    for dev in store.live_devices():
        add(getattr(dev, "name", ""), getattr(dev, "device_guid", ""))
    if profile is None:
        try:
            from gremlin.shared_state import current_profile as profile
        except Exception:  # noqa: BLE001 - no profile yet
            profile = None
    if profile is not None:
        for uid, info in profile.device_database.devices.items():
            add(info.name, uid)
    return found


def plan_pack(
    device_name: str,
    resolve: Callable[[str], Path | None],
    modes: list[str] | None = None,
    notes: dict | None = None,
    profile: Profile | None = None,
    guid: str = "",
) -> dict | str:
    """Everything the pack takes from the open profile (or profile, one
    that isn't open: the Device Library) and the module files,
    read on the main thread: the documents, the wires and the picture files
    to copy. build_pack(plan) makes the zip from it on any thread (08 S107).
    A str when the device can't be exported (none, or damaged: 08 S51, Q19)."""
    name = " ".join(str(device_name or "").split())
    if not name:
        return "Choose a device."
    if not guid:
        # No id given: the name stands for one device only when exactly one
        # has it; twins share a name, so it would pick the wrong one (03 S90a).
        ids = _ids_named(name, profile)
        if len(ids) > 1:
            return _TWINS.format(name=name)
        guid = next(iter(ids.values()), "")
    # With its id, its own file (twins share a name).
    path = _device_path(name, guid)
    refused = export_refusal(path)
    if refused:
        return refused
    doc = _read_doc(path)
    if not doc:
        return _NO_FILE
    used: set[str] = set()
    files: list[tuple[Path, str]] = []
    packed, pictures = _rewrite_images(doc, resolve, used, files)
    packed.pop("boundGuidLocal", None)
    packed.pop("boundName", None)
    packed["device"] = name
    packed["pack"] = _pack_label(name, guid, notes)
    wires = _collect_wires(guid, modes, profile)
    outputs: list[tuple[str, dict]] = []
    for output_name in wires["outputs"]:
        built = _output_doc(output_name, resolve, used, files)
        if built is None:
            continue
        out_doc = built[0]
        label = out_doc.get("pack") or {}
        slug = str(label.get("slug") or _pack_key(output_name))
        outputs.append((slug, out_doc))
    photo = ""
    for picture in pictures:
        if not picture.get("onMap"):
            photo = str(resolve(str(doc.get("image") or "")) or "")
            break
    return {
        "device": name,
        "map": packed,
        "wires": {
            "modes": wires["modes"],
            "actions": wires["actions"],
            "tree": wires["tree"],
        } if wires["modes"] else None,
        "outputs": outputs,
        "files": files,
        "photoPath": photo,
    }


def build_pack(plan: dict) -> tuple[bytes, dict]:
    """The zip of a plan_pack() plan. Reads only the plan and the picture
    files, so it may run on a worker thread (08 S107)."""
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("map.json", json.dumps(plan["map"], indent=2) + "\n")
        if plan["wires"]:
            zf.writestr("wires.json", json.dumps(plan["wires"], indent=2) + "\n")
        for slug, out_doc in plan["outputs"]:
            zf.writestr(f"outputs/{slug}.json", json.dumps(out_doc, indent=2) + "\n")
        for src, arc in plan["files"]:
            zf.write(src, arc)
    data = blob.getvalue()
    return data, {
        "device": plan["device"],
        "photoPath": plan["photoPath"],
        "bytes": len(data),
        "sizeText": size_text(len(data)),
    }


def write_pack(plan: dict, dest: Path) -> dict:
    """Builds the plan's zip and saves it (save_pack). Runs on the export
    worker (08 S107): no profile, no window."""
    try:
        data, info = build_pack(plan)
    except OSError as exc:
        # A picture that went away or can't be read meanwhile.
        name = Path(str(getattr(exc, "filename", "") or "")).name or "a picture"
        return {
            "ok": False,
            "error": f"Export failed. {name} could not be read: "
            f"{exc.strerror or exc}.",
        }
    return save_pack(data, info, Path(dest))


def save_pack(data: bytes, info: dict, dest: Path) -> dict:
    """Writes a built pack to dest through a temporary file (a failed write
    never leaves half a zip over an older pack, 08 R4), then reads it back.
    The result: {ok, path, folderUrl, device, sizeText}, or {ok: False,
    error} naming the file, the folder and why (Q19)."""
    from gremlin.ui.hardware_profile import export_failure

    dest = Path(dest)
    try:
        store.write_file(dest, data)
    except Exception:
        trace("SAVE", "Device Pack", "exportPack", dest, "error")
        return {
            "ok": False,
            "error": export_failure(
                dest, fallback="the pack could not be written there"
            ),
        }
    if not _zip_readable(dest):
        trace("SAVE", "Device Pack", "exportPack", dest, "unreadable")
        return {
            "ok": False,
            "error": export_failure(
                dest, reason="it was written but could not be read back"
            ),
        }
    trace("SAVE", "Device Pack", "exportPack", dest, "ok")
    return {
        "ok": True,
        "path": str(dest),
        "folderUrl": dest.parent.as_uri(),
        "device": info["device"],
        "sizeText": info["sizeText"],
    }


def _zip_readable(path: Path) -> bool:
    """The pack at path opens and has a map.json that is a document."""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "map.json" not in zf.namelist():
                return False
            doc = json.loads(zf.read("map.json").decode("utf-8"))
        return isinstance(doc, dict)
    except Exception:
        return False


def assemble(
    device_name: str,
    resolve,
    modes: list[str] | None = None,
    notes: dict | None = None,
    profile: Profile | None = None,
    guid: str = "",
) -> tuple[bytes, dict] | str:
    """The pack for one device. modes: the modes whose wires go in (None:
    all of them). notes: {author, note}, shown when the pack is imported."""
    plan = plan_pack(device_name, resolve, modes, notes, profile, guid)
    if isinstance(plan, str):
        return plan
    return build_pack(plan)


def _read_zip(path: Path) -> dict | str:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            json_name = "map.json" if "map.json" in names else ""
            if not json_name:
                for name in names:
                    if name.lower().endswith(".json") and name.count("/") == 0:
                        json_name = name
                        break
            if not json_name:
                return "No map.json in this zip."
            doc = json.loads(zf.read(json_name).decode("utf-8"))
            wires = {}
            if "wires.json" in names:
                wires = json.loads(zf.read("wires.json").decode("utf-8"))
            outputs = []
            blobs = {}
            for name in names:
                if name.startswith("outputs/") and name.lower().endswith(".json"):
                    payload = json.loads(zf.read(name).decode("utf-8"))
                    if isinstance(payload, dict):
                        outputs.append(payload)
                base = Path(name).name
                if base and Path(base).suffix.lower() in _IMAGE_EXT and not name.endswith("/"):
                    blobs[base] = zf.read(name)
                    blobs[name] = zf.read(name)
    except zipfile.BadZipFile:
        return "Not a valid zip."
    except Exception as exc:
        return str(exc)
    if not isinstance(doc, dict):
        return "No map.json in this zip."
    return {"doc": doc, "wires": wires if isinstance(wires, dict) else {}, "outputs": outputs, "files": blobs}


def drop_preview() -> None:
    """Removes the pack's preview pictures folder in %TEMP%: when the
    Device Pack window closes and at quit (08 section 10 gap 29)."""
    global _preview_dir
    if _preview_dir and os.path.isdir(_preview_dir):
        shutil.rmtree(_preview_dir, ignore_errors=True)
    _preview_dir = ""


def _stage_images(files: dict[str, bytes]) -> tuple[str, dict[str, str]]:
    global _preview_dir, _drop_at_exit
    drop_preview()
    if not _drop_at_exit:
        atexit.register(drop_preview)
        _drop_at_exit = True
    folder = tempfile.mkdtemp(prefix="gremlin-pack-")
    _preview_dir = folder
    urls: dict[str, str] = {}
    for name, data in files.items():
        if "/" in name.replace("\\", "/"):
            continue
        dest = Path(folder) / _safe_name(name, name)
        try:
            dest.write_bytes(data)
        except OSError:
            continue
        urls[name] = dest.as_uri()
        urls[Path(name).name] = dest.as_uri()
    return folder, urls


_preview_dir = ""
_drop_at_exit = False


def _too_new(doc: dict) -> str:
    """Why a pack from a newer program can't be read ("" when it can)."""
    label = doc.get("pack") if isinstance(doc.get("pack"), dict) else {}
    try:
        made = int(label.get("format") or 1)
    except (TypeError, ValueError):
        made = 1
    if made <= PACK_FORMAT:
        return ""
    program = str(label.get("program") or "").strip()
    by = f" (version {program})" if program else ""
    return (
        f"This pack was made by a newer Gremlin-Platforms{by}. "
        "Update the program to import it."
    )


def describe_zip(path: Path) -> dict | str:
    loaded = _read_zip(path)
    if isinstance(loaded, str):
        return loaded
    doc = loaded["doc"]
    newer = _too_new(doc)
    if newer:
        return newer
    label = doc.get("pack") if isinstance(doc.get("pack"), dict) else {}
    exported = str(label.get("exportedName") or doc.get("device") or "").strip()
    if not exported:
        return "This pack has no device name."
    _folder, urls = _stage_images(loaded["files"])
    pictures = []
    photo_arc = Path(str(doc.get("image") or "")).name
    if photo_arc and photo_arc in urls:
        pictures.append({
            "arc": photo_arc,
            "onMap": False,
            "item": _picture_item(photo_arc, "Device photo", urls.get(photo_arc, ""), False),
        })
    map_count = 0
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("kind") != "image" and node.get("shape") != "image":
            continue
        arc = Path(str(node.get("src") or "")).name
        if not arc or arc not in urls:
            continue
        if arc == photo_arc and not pictures:
            continue
        if any(row["arc"] == arc for row in pictures):
            for row in pictures:
                if row["arc"] == arc:
                    row["onMap"] = True
                    row["item"]["onMap"] = True
            continue
        map_count += 1
        pictures.append({
            "arc": arc,
            "onMap": True,
            "item": _picture_item(arc, f"Map picture {map_count}", urls.get(arc, ""), True),
        })
    sections = []
    module_rows, map_rows, setting_rows = _split_sections(doc, pictures, "in.")
    if module_rows:
        sections.append({"id": "input", "title": "Input module", "items": module_rows})
    if map_rows:
        sections.append({"id": "map", "title": "Button map", "items": map_rows})
    if setting_rows:
        sections.append(
            {"id": "mapset", "title": "Map settings", "items": setting_rows}
        )
    wire_items = []
    for mode in loaded["wires"].get("modes") or []:
        if not isinstance(mode, dict):
            continue
        mode_name = str(mode.get("name") or "Default")
        lines = [str(line) for line in (mode.get("lines") or []) if str(line).strip()]
        if not lines:
            continue
        parent = str((loaded["wires"].get("tree") or {}).get(mode_name) or "")
        title = f"{mode_name} (under {parent})" if parent else mode_name
        wire_items.append(_item("wire:" + mode_name, title, _clip(lines)))
    if wire_items:
        sections.append({"id": "wires", "title": "Wires", "items": wire_items})
    for output in loaded["outputs"]:
        out_label = output.get("pack") if isinstance(output.get("pack"), dict) else {}
        out_name = str(out_label.get("exportedName") or output.get("device") or "Output").strip()
        slug = str(out_label.get("slug") or _pack_key(out_name))
        out_pictures = []
        out_photo = Path(str(output.get("image") or "")).name
        if out_photo and out_photo in urls:
            out_pictures.append({
                "arc": out_photo,
                "onMap": False,
                "item": _picture_item(out_photo, "Device photo", urls.get(out_photo, ""), False),
            })
        sections.append({
            "id": "out:" + slug,
            "title": out_name,
            "kind": "output",
            "target": _suggest_pack_name(out_name) or out_name,
            "items": [
                row
                for rows in _split_sections(output, out_pictures, "out:" + slug + ".")
                for row in rows
            ],
        })
    photo_url = urls.get(photo_arc, "") if photo_arc else ""
    return {
        "ok": True,
        "exportedName": exported,
        "exportedGuid": str(label.get("exportedGuid") or ""),
        "suggestedName": _suggest_pack_name(exported),
        "photoUrl": photo_url,
        "direction": _doc_direction(doc, exported),
        "sections": [row for row in sections if row.get("items")],
        "drivers": _pack_drivers(loaded),
        "notes": {
            "author": str(label.get("author") or ""),
            "note": str(label.get("note") or ""),
            "exportedOn": str(label.get("exportedOn") or ""),
            "program": str(label.get("program") or ""),
        },
    }


def _split_sections(
    doc: dict, pictures: list[dict], prefix: str
) -> tuple[list[dict], list[dict], list[dict]]:
    """The module rows, the Button Map rows and the Map settings rows."""
    placed = _place_pictures(doc, pictures, prefix)
    module_ids = {
        prefix + "checks", prefix + "names", prefix + "calibration",
        prefix + "view", prefix + "catalog",
    }
    setting_ids = {prefix + "mapview", prefix + "print"}
    return (
        [row for row in placed if row["id"] in module_ids],
        [row for row in placed if row["id"] not in module_ids | setting_ids],
        [row for row in placed if row["id"] in setting_ids],
    )


def _place_pictures(doc: dict, pictures: list[dict], prefix: str = "in.") -> list[dict]:
    items = _module_items(prefix, doc, pictures)
    photos = [row["item"] for row in pictures if not row.get("onMap")]
    maps = [row["item"] for row in pictures if row.get("onMap")]
    placed: list[dict] = []
    inserted = False
    for item in items:
        if str(item["id"]).startswith("pic:"):
            continue
        placed.append(item)
        if item["id"].endswith("layout"):
            placed.extend(maps)
            placed.extend(photos)
            inserted = True
    if not inserted:
        placed.extend(photos)
        placed.extend(maps)
    return placed


def _checked_ids(doc: dict) -> tuple[set[int], set[int], set[int]]:
    claim = _claim(doc)
    return (
        set(claim_ids(claim, "button")),
        set(claim_ids(claim, "axis")),
        set(claim_ids(claim, "hat")),
    )


def _skeleton(name: str, direction: str, guid: str) -> dict:
    payload = {
        "kind": "control.hardware",
        "device": name,
        "direction": direction,
        "claim": {"buttons": [], "axes": [], "hats": [], "keys": [], "friendly": {}},
        "nodes": [],
    }
    if guid:
        payload["boundName"] = name
        payload["boundGuidLocal"] = guid
    return payload


def _copy_names_onto_nodes(nodes: list, names: dict) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "")
        word = _FRIENDLY_KIND.get(kind, "")
        if word and node.get("hwId") is not None:
            label = str(names.get(f"{word}:{int(node['hwId'])}") or "").strip()
            if label:
                node["friendly"] = label
        for member in node.get("members") or []:
            if not isinstance(member, dict) or member.get("hwId") is None:
                continue
            word = _FRIENDLY_KIND[member_kind(node, member)]
            label = str(names.get(f"{word}:{int(member['hwId'])}") or "").strip()
            if label:
                member["friendly"] = label


def _merge_module(
    existing: dict | None,
    incoming: dict,
    chosen: set[str],
    prefix: str,
    name: str,
    guid: str,
    limits: dict[str, set[int]] | None = None,
) -> tuple[dict, list[str]]:
    """The module file after the ticked pieces replace what is here (checked
    controls are added, 08 Q3). limits:
    the controls the device has (None: not known); others are left out."""
    direction = _doc_direction(incoming, str((incoming.get("pack") or {}).get("exportedName") or name))
    base = json.loads(json.dumps(existing)) if isinstance(existing, dict) else _skeleton(name, direction, guid)
    base["kind"] = "control.hardware"
    base["device"] = name
    base["direction"] = "dest" if direction == "dest" else "source"
    if guid:
        base["boundName"] = name
        base["boundGuidLocal"] = guid
    notes: list[str] = []
    claim = _claim(base)
    claim.setdefault("buttons", [])
    claim.setdefault("axes", [])
    claim.setdefault("hats", [])
    claim.setdefault("keys", [])
    claim.setdefault("friendly", {})
    buttons, axes, hats = _checked_ids(base)
    in_buttons, in_axes, in_hats = _checked_ids(incoming)
    if limits is not None and prefix + "checks" in chosen:
        has_buttons = limits.get("button", in_buttons)
        left_out = (
            [f"Button {n}" for n in sorted(in_buttons - has_buttons)]
            + [f"Axis {n}" for n in sorted(in_axes - limits.get("axis", in_axes))]
            + [f"Hat {n}" for n in sorted(in_hats - limits.get("hat", in_hats))]
        )
        in_buttons &= limits.get("button", in_buttons)
        in_axes &= limits.get("axis", in_axes)
        in_hats &= limits.get("hat", in_hats)
        if left_out:
            notes.append(
                f"Left out controls {name} doesn't have: " + ", ".join(left_out) + "."
            )
    if prefix + "checks" in chosen:
        buttons |= in_buttons
        axes |= in_axes
        hats |= in_hats
    claim["buttons"] = sorted(buttons)
    claim["axes"] = sorted(axes)
    claim["hats"] = sorted(hats)
    incoming_names = _friendly(incoming)
    if prefix + "names" in chosen:
        written = 0
        skipped = 0
        groups = (
            ("button", buttons),
            ("axis", axes),
            ("hat", hats),
        )
        for kind, allowed in groups:
            for key, label in incoming_names.items():
                if not str(key).startswith(kind + ":"):
                    continue
                try:
                    number = int(str(key).split(":", 1)[1])
                except (TypeError, ValueError):
                    continue
                if number not in allowed:
                    skipped += 1
                    continue
                claim["friendly"][f"{kind}:{number}"] = label
                written += 1
        if skipped:
            notes.append("Names for controls that are not checked were left out.")
        if written == 0 and skipped:
            notes.append("No friendly names were written.")
    if prefix + "calibration" in chosen and isinstance(incoming.get("calibration"), dict):
        stored = base.get("calibration") if isinstance(base.get("calibration"), dict) else {}
        from gremlin.modules.calibration import as_tuple

        unusable = []
        for key, value in incoming["calibration"].items():
            try:
                number = int(key)
            except (TypeError, ValueError):
                continue
            if number not in axes:
                continue
            # A curve loading would throw away (low not below high, the
            # center outside them) doesn't replace a good one.
            if as_tuple(value) is None:
                unusable.append(f"Axis {number}")
                continue
            stored[str(number)] = value
        if unusable:
            notes.append(
                "Calibration that can't be used was left out: "
                + ", ".join(unusable) + "."
            )
        base["calibration"] = stored
    if prefix + "view" in chosen and isinstance(incoming.get("view"), dict):
        base["view"] = json.loads(json.dumps(incoming["view"]))
        missing = []
        for key in ("padAX", "padAY", "padBX", "padBY"):
            try:
                number = int(base["view"].get(key))
            except (TypeError, ValueError):
                continue
            if number and number not in axes:
                missing.append(f"Axis {number}")
        for item in base["view"].get("meters") or []:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue
            if number and number not in axes:
                missing.append(f"Axis {number}")
        if missing:
            unique = sorted(set(missing))
            noun = "that axis is" if len(unique) == 1 else "those axes are"
            notes.append(
                "The Output View Appearance points at "
                + ", ".join(unique)
                + f", and {noun} not checked."
            )
    if prefix + "catalog" in chosen and isinstance(incoming.get("catalog"), dict):
        base["catalog"] = json.loads(json.dumps(incoming["catalog"]))
    nodes = [node for node in (base.get("nodes") or []) if isinstance(node, dict)]
    if prefix + "layout" in chosen:
        incoming_nodes = [json.loads(json.dumps(node)) for node in (incoming.get("nodes") or []) if isinstance(node, dict)]
        missing_picture = False
        for node in incoming_nodes:
            if node.get("kind") != "image" and node.get("shape") != "image":
                continue
            arc = Path(str(node.get("src") or "")).name
            if arc and "pic:" + arc not in chosen:
                missing_picture = True
                node.pop("src", None)
                node.pop("srcUrl", None)
        if missing_picture:
            notes.append("The map uses a picture that was not ticked. That picture was left out.")
        covered: set[tuple[str, int]] = set()
        incoming_ids = set()
        for node in incoming_nodes:
            covered |= _node_controls(node)
            if node.get("id"):
                incoming_ids.add(node.get("id"))
        consumed = False
        merged_nodes = []
        for node in nodes:
            if node.get("id") in incoming_ids or (_node_controls(node) & covered):
                if not consumed:
                    merged_nodes.extend(incoming_nodes)
                    consumed = True
                continue
            merged_nodes.append(node)
        if not consumed:
            merged_nodes.extend(incoming_nodes)
        nodes = merged_nodes
    if prefix + "names" in chosen and prefix + "layout" in chosen:
        _copy_names_onto_nodes(nodes, claim.get("friendly") or {})
    base["nodes"] = nodes
    in_ui = _ui(incoming)
    rows = ((prefix + "mapview", _MAP_VIEW_KEYS), (prefix + "print", _PRINT_KEYS))
    for row, keys in rows:
        if row not in chosen or not any(key in in_ui for key in keys):
            continue
        ui = json.loads(json.dumps(_ui(base)))
        for key in keys:
            if key in in_ui:
                ui[key] = json.loads(json.dumps(in_ui[key]))
            else:
                ui.pop(key, None)
        base["ui"] = ui
    photo = Path(str(incoming.get("image") or "")).name
    if photo and ("pic:" + photo) in chosen:
        base["image"] = photo
        # Where the photo sits on the page (position, size, turn, crop).
        if isinstance(incoming.get("photo"), dict):
            base["photo"] = json.loads(json.dumps(incoming["photo"]))
    base.pop("pack", None)
    return base, notes


def _target_guid(selection: dict | None, target_guid: str = "") -> str:
    """The chosen "Put this pack on" row's id: the argument, else the
    selection's "targetGuid" (08 S106a); "" goes by the name."""
    given = str(target_guid or "").strip()
    if given or not isinstance(selection, dict):
        return given
    return str(selection.get("targetGuid") or "").strip()


def _selected(selection: dict | None) -> set[str]:
    if not isinstance(selection, dict):
        return set()
    return {str(item) for item in (selection.get("items") or [])}


def _write_pictures(
    slug: str,
    files: dict[str, bytes],
    chosen: set[str],
    doc: dict,
    record: list[tuple[Path, bytes | None]] | None = None,
) -> dict[str, str]:
    written: dict[str, str] = {}
    folder = store.pictures_dir_of(slug)
    wanted = {item[4:] for item in chosen if item.startswith("pic:")}
    used = set()
    photo = Path(str(doc.get("image") or "")).name
    if photo:
        used.add(photo)
    for node in doc.get("nodes") or []:
        if isinstance(node, dict):
            name = Path(str(node.get("src") or "")).name
            if name:
                used.add(name)
    for arc, data in files.items():
        if "/" in arc.replace("\\", "/"):
            continue
        if arc not in wanted or arc not in used:
            continue
        dest = folder / _safe_name(arc, arc)
        if record is not None:
            record.append((dest, dest.read_bytes() if dest.is_file() else None))
        if dest.is_file():
            backup = _unique_archive(f"{slug}_{dest.stem}")
            store.replace(
                backup.with_suffix(dest.suffix), dest.read_bytes(), "Device Pack"
            )
        # A temporary file, then a swap: a crash can't leave half a picture
        # (08 S76, R3).
        store.put_picture_at(dest, data)
        trace("SAVE", "Device Pack", "_write_pictures", dest, "ok")
        written[arc] = dest.name
    photo = Path(str(doc.get("image") or "")).name
    if photo in written:
        doc["image"] = store.picture_ref(slug, written[photo])
    elif "pic:" + photo not in chosen:
        pass
    else:
        doc.pop("image", None)
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        key = Path(str(node.get("src") or "")).name
        if key in written:
            node["src"] = store.picture_ref(slug, written[key])
    return written


def _device_limits(guid: str) -> dict[str, set[int]] | None:
    """The buttons, axes and hats the connected device has (None: not
    connected, so not known)."""
    want = str(guid or "").strip().lower()
    if not want:
        return None
    for dev in store.live_devices():
        if store.guid_text(getattr(dev, "device_guid", "")).lower() != want:
            continue
        axes_count = int(getattr(dev, "axis_count", 0) or 0)
        axes = {
            int(getattr(entry, "axis_index", 0) or 0)
            for entry in list(getattr(dev, "axis_map", []) or [])[:axes_count]
        } - {0}
        if len(axes) < axes_count:
            axes = set(range(1, axes_count + 1))
        return {
            "button": set(range(1, int(getattr(dev, "button_count", 0) or 0) + 1)),
            "axis": axes,
            "hat": set(range(1, int(getattr(dev, "hat_count", 0) or 0) + 1)),
        }
    return None


def _vjoy_limits(number: int) -> dict[str, set[int]] | None:
    """What vJoy device number has, as _device_limits() for a stick (None:
    not a vJoy name, or that vJoy isn't here)."""
    if not number:
        return None
    for dev in store.live_devices():
        if not getattr(dev, "is_virtual", False):
            continue
        try:
            if int(getattr(dev, "vjoy_id", 0) or 0) != number:
                continue
        except (TypeError, ValueError):
            continue
        return _device_limits(store.guid_text(getattr(dev, "device_guid", "")))
    return None


def _vjoy_number(name: str) -> int:
    match = re.fullmatch(r"\s*vjoy\s*(\d+)\s*", str(name or ""), re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _vjoy_moves(outputs: list[dict], targets: dict) -> dict[int, int]:
    """vJoy device numbers the wires should follow: an output put on
    another vJoy ("vJoy 2" on vJoy 1) sends there."""
    moves: dict[int, int] = {}
    for output in outputs:
        label = output.get("pack")
        if not isinstance(label, dict):
            label = {}
        slug = str(label.get("slug") or _pack_key(str(output.get("device") or "")))
        old = _vjoy_number(str(label.get("exportedName") or output.get("device") or ""))
        new = _vjoy_number(str(targets.get(slug) or ""))
        if old and new and old != new:
            moves[old] = new
    return moves


def _retarget_vjoy(action_xml: list[str], moves: dict[int, int]) -> list[str]:
    if not moves:
        return action_xml
    out = []
    for block in action_xml:
        node = ElementTree.fromstring(block)
        if node.get("type") == "map-to-vjoy":
            for prop in node.findall("property"):
                if prop.findtext("name") != "vjoy-device-id":
                    continue
                value = prop.find("value")
                if value is None or value.text is None:
                    continue
                try:
                    old = int(value.text.strip())
                except ValueError:
                    continue
                if old in moves:
                    value.text = str(moves[old])
            block = ElementTree.tostring(node, encoding="unicode")
        out.append(block)
    return out


def _logical_targets(action_xml: list[str]) -> list[tuple[str, int, str]]:
    """The Logical Device inputs these actions send to: (type, number,
    uid); uid "" in an older pack, which has none."""
    found: list[tuple[str, int, str]] = []
    for block in action_xml:
        node = ElementTree.fromstring(block)
        if node.get("type") != "map-to-logical-device":
            continue
        props = {
            prop.findtext("name"): prop.findtext("value")
            for prop in node.findall("property")
        }
        kind = str(props.get("logical-input-type") or "").strip().lower()
        uid = str(props.get("logical-input-uid") or "").strip().lower()
        try:
            number = int(str(props.get("logical-input-id") or "").strip())
        except ValueError:
            continue
        if kind and (kind, number, uid) not in found:
            found.append((kind, number, uid))
    return found


def _with_logical_uids(action_xml: list[str]) -> list[str]:
    """The actions with each Logical Device target's permanent id written
    in (logical-input-uid), so an import finds the same control by id."""
    from gremlin.logical_device import LogicalDevice
    from gremlin.types import InputType

    out = []
    for block in action_xml:
        node = ElementTree.fromstring(block)
        if node.get("type") != "map-to-logical-device":
            out.append(block)
            continue
        props = {prop.findtext("name"): prop for prop in node.findall("property")}
        if "logical-input-uid" in props:
            out.append(block)
            continue
        try:
            kind = InputType.to_enum(
                str(props["logical-input-type"].findtext("value") or "").strip().lower()
            )
            number = int(str(props["logical-input-id"].findtext("value") or "").strip())
            uid = LogicalDevice().uid_of(kind, number)
        except Exception:
            uid = None
        if not uid:
            out.append(block)
            continue
        prop = ElementTree.SubElement(node, "property", {"type": "string"})
        ElementTree.SubElement(prop, "name").text = "logical-input-uid"
        ElementTree.SubElement(prop, "value").text = str(uid)
        out.append(ElementTree.tostring(node, encoding="unicode"))
    return out


def _rows_of(profile: object) -> object:
    """The Logical Device rows a profile that isn't open still carries: a
    saved version 14 profile read without opening it keeps its own rows
    until it is saved (pending_logical_rows; the shared file is not
    changed by reading it). None: the Logical Device's module file, which
    every other profile uses (D-04-LD-FILE)."""
    from gremlin import shared_state

    if profile is None or profile is shared_state.current_profile:
        return None
    pending = getattr(profile, "pending_logical_rows", None)
    if not pending:
        return None
    if isinstance(pending, dict):
        from gremlin.logical_device import LogicalRows

        rows = LogicalRows()
        rows.load_dict(pending)
        return rows
    return pending


def _missing_logical(
    action_xml: list[str], rows: object = None
) -> list[tuple[str, int, str]]:
    """The Logical Device inputs these actions send to that the Logical
    Device's module file lacks (one layout for every profile, D-04-LD-FILE).
    A target with an id is found by its id (decision 4); one without (an
    older pack) by type and number. rows: a saved version 14 profile's own
    rows (_rows_of), checked by type and number as well."""
    from gremlin.logical_device import LogicalDevice
    from gremlin.types import InputType

    shared = LogicalDevice()
    missing = []
    for kind, number, uid in _logical_targets(action_xml):
        if uid and shared.by_uid(uid) is not None:
            continue
        try:
            ident = LogicalDevice.Input.Identifier(InputType.to_enum(kind), number)
        except Exception:
            continue
        if rows is not None:
            if rows.exists(ident):  # type: ignore[attr-defined]
                continue
        elif not uid and shared.exists(ident):
            continue
        missing.append((kind, number, uid))
    return missing


def _needs(action_xml: list[str]) -> tuple[set[int], bool]:
    """The vJoy devices these actions send to, and whether one sends to Xbox."""
    vjoys: set[int] = set()
    xbox = False
    for block in action_xml:
        node = ElementTree.fromstring(block)
        kind = node.get("type")
        if kind == "map-to-xbox":
            xbox = True
        elif kind == "map-to-vjoy":
            for prop in node.findall("property"):
                if prop.findtext("name") == "vjoy-device-id":
                    try:
                        vjoys.add(int(str(prop.findtext("value") or "").strip()))
                    except ValueError:
                        pass
    return vjoys, xbox


def driver_notes(vjoys: set[int], xbox: bool) -> list[str]:
    """What is missing for these outputs to work: the vJoy driver, a vJoy
    device it doesn't have, the Xbox driver (ViGEmBus). The driver wording is
    the output module's, as on the Xbox Viewer."""
    from gremlin.modules import output

    notes: list[str] = []
    if vjoys:
        problem, hint = output.vjoy_driver_problem()
        if problem:
            notes.append(f"{problem}: wires to vJoy won't do anything. {hint}")
        else:
            absent = [n for n in sorted(vjoys) if not output.vjoy_exists(n)]
            if absent:
                names = ", ".join(f"vJoy {n}" for n in absent)
                verb = "isn't" if len(absent) == 1 else "aren't"
                notes.append(
                    f"{names} {verb} set up in the vJoy driver, so wires to it "
                    "won't do anything. Add it in Configure vJoy."
                )
    problem, hint = output.xbox_driver_problem() if xbox else ("", "")
    if problem:
        notes.append(f"{problem}: wires to Xbox won't do anything. {hint}")
    return notes


def _pack_drivers(loaded: dict, moves: dict[int, int] | None = None) -> list[str]:
    """The drivers the whole pack needs (its wires and output modules)."""
    actions = [str(block) for block in (loaded["wires"].get("actions") or [])]
    vjoys, xbox = _needs(_retarget_vjoy(actions, moves or {}))
    for output in loaded["outputs"]:
        label = output.get("pack") if isinstance(output.get("pack"), dict) else {}
        name = str(label.get("exportedName") or output.get("device") or "")
        number = _vjoy_number(name)
        if number:
            vjoys.add((moves or {}).get(number, number))
        elif "xbox" in name.lower():
            xbox = True
    return driver_notes(vjoys, xbox)


def _plan_wires(
    wires: dict,
    chosen: set[str],
    limits: dict[str, set[int]] | None,
    rows: object = None,
) -> dict:
    """What importing the ticked modes would write, before anything changes:
    their inputs (less the controls the device doesn't have) and only the
    actions those inputs use. rows: a saved version 14 profile's own
    Logical Device rows (_rows_of; None: the Logical Device's module file)."""
    from gremlin.types import InputType
    from gremlin.util import read_subelement

    modes = []
    inputs: list[str] = []
    left_out: list[str] = []
    counts: dict[str, int] = {}
    for mode in wires.get("modes") or []:
        if not isinstance(mode, dict):
            continue
        name = str(mode.get("name") or "Default")
        if "wire:" + name not in chosen:
            continue
        modes.append(name)
        counts[name] = 0
        for block in mode.get("inputs") or []:
            node = ElementTree.fromstring(str(block))
            try:
                kind = InputType.to_string(read_subelement(node, "input-type"))
                number = int(read_subelement(node, "input-id"))
            except Exception:
                kind, number = "", 0
            if limits is not None and kind in limits and number not in limits[kind]:
                label = f"{kind.capitalize()} {number}"
                if label not in left_out:
                    left_out.append(label)
                continue
            inputs.append(str(block))
            counts[name] += 1
    by_id: dict[str, str] = {}
    for block in wires.get("actions") or []:
        node = ElementTree.fromstring(str(block))
        aid = node.get("id")
        if aid:
            by_id[aid.lower()] = str(block)
    reachable: set[str] = set()
    pending = [found.lower() for block in inputs for found in _UUID_RE.findall(block)]
    while pending:
        aid = pending.pop()
        if aid in reachable or aid not in by_id:
            continue
        reachable.add(aid)
        pending.extend(found.lower() for found in _UUID_RE.findall(by_id[aid]))
    actions = [block for aid, block in by_id.items() if aid in reachable]
    return {
        "modes": modes,
        "counts": counts,
        "inputs": inputs,
        "actions": actions,
        "leftOut": left_out,
        "missingLogical": _missing_logical(actions, rows),
    }


def _mode_here(profile: Profile, name: str) -> str:
    """The profile's mode a pack mode is: "test mode" is this profile's
    "Test Mode" (capitals and spacing don't count, as Manage Modes, 04 S40);
    a mode not here keeps its own name."""
    from gremlin.profile import clean_mode_name

    if profile.modes.mode_exists(name):
        return name
    text = clean_mode_name(name).casefold()
    for existing in profile.modes.mode_names():
        if text and clean_mode_name(existing).casefold() == text:
            return existing
    return name


def _match_modes(profile: Profile, plan: dict, tree: dict) -> tuple[dict, dict]:
    """The plan and mode tree with each pack mode under the name of the
    look-alike mode this profile has (add_mode refuses look-alikes)."""
    wanted = set(plan["modes"]) | set(tree)
    names = {name: _mode_here(profile, name) for name in wanted}
    names.update(
        {str(p): _mode_here(profile, str(p)) for p in tree.values() if p}
    )
    if all(old == new for old, new in names.items()):
        return plan, tree
    inputs = []
    for block in plan["inputs"]:
        node = ElementTree.fromstring(str(block))
        mode = node.find("mode")
        if mode is not None and (mode.text or "") in names:
            mode.text = names[mode.text or ""]
        inputs.append(ElementTree.tostring(node, encoding="unicode"))
    matched = dict(plan)
    matched["modes"] = list(dict.fromkeys(names.get(m, m) for m in plan["modes"]))
    matched["counts"] = {}
    for mode, count in plan["counts"].items():
        key = names.get(mode, mode)
        matched["counts"][key] = matched["counts"].get(key, 0) + count
    matched["inputs"] = inputs
    new_tree = {
        names.get(name, name): (names.get(str(parent), parent) if parent else parent)
        for name, parent in tree.items()
    }
    return matched, new_tree


def _ensure_modes(
    profile: Profile, names: list[str], tree: dict, notes: list[str]
) -> list[str]:
    """Creates the modes that aren't in the profile, under their parent from
    the pack (a parent that isn't here: under Default)."""
    created: list[str] = []

    def ensure(name: str, chain: tuple[str, ...]) -> None:
        if profile.modes.mode_exists(name) or name in chain:
            return
        parent = str(tree.get(name) or "")
        if parent and not profile.modes.mode_exists(parent):
            if parent in names or parent in tree:
                ensure(parent, chain + (name,))
        if parent and not profile.modes.mode_exists(parent):
            fallback = "Default" if profile.modes.mode_exists("Default") else ""
            notes.append(
                f"{parent} isn't in this profile, so {name} was put "
                + (f"under {fallback}." if fallback else "at the top.")
            )
            parent = fallback
        profile.modes.add_mode(name)
        if parent:
            profile.modes.set_parent(name, parent)
        created.append(name)

    for name in names:
        ensure(name, ())
    if created:
        notes.append("Created " + ", ".join(created) + ".")
    return created


def _apply_wires(
    plan: dict,
    tree: dict,
    target_guid: str,
    target_name: str,
    moves: dict[int, int],
    create_logical: bool,
    into: Profile | None = None,
) -> tuple[list[str], dict | None]:
    """Replaces the device's wires and actions in each ticked mode with the
    pack's. Returns the notes and what Undo Import needs. into: the profile
    to change (None: the open one)."""
    if not plan["modes"]:
        return [], None
    if not target_guid:
        return ["The wires were not written. This name has no device id."], None
    try:
        from gremlin.logical_device import LogicalDevice
        from gremlin.shared_state import current_profile
        from gremlin.types import InputType
    except Exception:
        return ["The wires were not written."], None
    profile = into if into is not None else current_profile
    if profile is None:
        return ["The wires were not written. No profile is open."], None
    uid = parse_guid(target_guid)
    if uid is None:
        return ["The wires were not written. This name has no device id."], None
    notes: list[str] = []
    plan, tree = _match_modes(profile, plan, tree)
    try:
        # All or nothing (decision A3, 08 S79): when any step fails, the
        # Library puts back the inputs, actions, modes, Logical Device
        # inputs and device list as they were (map 2, GL-099, GL-109).
        with profile.library.change():
            action_xml = _retarget_vjoy(plan["actions"], moves)
            created_logical: list[str] = []
            made_names: list[str] = []
            missing = plan["missingLogical"]
            if missing and create_logical:
                for kind, number, pack_uid in missing:
                    # Into the Logical Device's module file (one layout for
                    # every profile), under the pack's id when it has one;
                    # a number taken by another control: the lowest free one.
                    made = LogicalDevice().create(
                        InputType.to_enum(kind), input_id=number, uid=pack_uid or None
                    )
                    created_logical.append(made.uid)
                    made_names.append(f"{kind.capitalize()} {made.id}")
                notes.append(
                    "Created on the Logical Device: " + ", ".join(made_names) + "."
                )
            elif missing:
                notes.append(
                    "These wires send to Logical Device inputs that don't exist "
                    "here, so they do nothing until you add them: "
                    + ", ".join(
                        f"{kind.capitalize()} {number}" for kind, number, _ in missing
                    )
                    + "."
                )
            created_modes = _ensure_modes(profile, plan["modes"], tree, notes)
            # Each ticked mode: everything the device had there goes. Undo
            # Import puts each back from its snapshot.
            removed = [
                item
                for item in profile.inputs.get(uid, []) or []
                if str(item.mode or "Default") in plan["modes"]
            ]
            restore = [_input_back(profile, item) for item in removed]
            profile.drop_inputs(uid, removed)
            added = profile.add_inputs(uid, plan["inputs"], action_xml)
            if uid not in profile.device_database.devices:
                profile.remember_device(uid, target_name)
    except Exception as exc:
        # Nothing of the wires stays (the module files written before are
        # kept, and Undo Import puts them back).
        return [
            f"The wires were not written, and nothing in the profile was changed. {exc}"
        ], None
    had = sum(1 for item in removed if item.action_sequences)
    for mode in plan["modes"]:
        count = plan["counts"].get(mode, 0)
        noun = "wire" if count == 1 else "wires"
        notes.insert(0, f"{mode}: {count} {noun} from the pack.")
    notes.insert(
        0,
        f"Replaced the wires of {target_name} in "
        + ", ".join(plan["modes"])
        + f" ({had} {'control' if had == 1 else 'controls'} had actions here). "
        "Save the profile to keep them.",
    )
    if plan["leftOut"]:
        notes.append(
            f"Left out wires for controls {target_name} doesn't have: "
            + ", ".join(plan["leftOut"]) + "."
        )
    if created_logical:
        from gremlin import logical_device_file
        from gremlin.signal import signal

        try:
            logical_device_file.save(who="Device Pack")
        except OSError as exc:
            notes.append(f"The Logical Device file could not be saved: {exc}")
        signal.logicalDeviceModified.emit()
    undo = {
        "profile": profile,
        "uid": uid,
        "removed": [],
        "restore": restore,
        "added": added,
        "modes": created_modes,
        "logical": created_logical,
    }
    return notes, undo


def _input_back(profile: Profile, item: object) -> dict:
    """What Undo Import needs to put a replaced input back: its snapshot
    (Library.snapshot), or, for one without actions, its XML."""
    from gremlin.types import InputType

    snapshot = profile.input_snapshot(item)  # type: ignore[arg-type]
    return {
        "type": InputType.to_string(getattr(item, "input_type")),
        "id": getattr(item, "input_id"),
        "mode": str(getattr(item, "mode", "") or "Default"),
        "snapshot": snapshot,
        "xml": None
        if snapshot
        else ElementTree.tostring(item.to_xml(), encoding="unicode"),  # type: ignore[attr-defined]
    }


def _put_inputs_back(profile: Profile, uid: uuid.UUID, wires: dict) -> None:
    """Undo Import's wires: the imported inputs go, the replaced ones come
    back. All or nothing (Library.change); Profile methods only (GL-109)."""
    from gremlin.types import InputType

    with profile.library.change():
        added = {id(item) for item in wires.get("added") or []}
        doomed = [item for item in profile.inputs.get(uid, []) if id(item) in added]
        profile.drop_inputs(uid, doomed)
        for back in wires.get("restore") or []:
            if back.get("snapshot"):
                profile.put_input(
                    uid,
                    InputType.to_enum(back["type"]),
                    back["id"],
                    back["mode"],
                    back["snapshot"],
                )
            elif back.get("xml"):
                profile.add_inputs(uid, [back["xml"]], [], remap=False)


def _logical_has_actions(profile: Profile, ident: object) -> bool:
    """Whether an input of the profile on this Logical Device input has
    actions (Undo Import keeps it then, 08 Q21)."""
    from gremlin.logical_device import LogicalDevice

    for item in profile.inputs.get(LogicalDevice.device_guid, []) or []:
        try:
            same = item.input_type == ident.type and int(item.input_id) == int(ident.id)  # type: ignore[attr-defined]
        except (TypeError, ValueError):
            continue
        if same and item.action_sequences:
            return True
    return False


# The last import, so Undo Import can put it back: the files it replaced
# (with their previous bytes, None for a new file), what it wrote in them
# ("written": a file changed since is asked about, 08 Q5) and the wires.
_last_import: dict | None = None


def can_undo_import() -> bool:
    return _last_import is not None


def drop_import_undo() -> None:
    """Keeps the last import: Undo Import is no longer offered. The actions
    it replaced left the profile with their inputs (Library.release)."""
    global _last_import
    _last_import = None


def _put_back(files: list[tuple[Path, bytes | None]]) -> None:
    """Puts files back as they were before a failed import wrote them.
    History records each module file put back or removed (08 Q12, F3)."""
    for path, previous in reversed(files):
        try:
            if previous is None:
                store.delete_path(path, "Device Pack")
            else:
                store.replace(path, previous, "Device Pack", force=True)
        except OSError:
            pass


def _bytes_now(path: Path) -> bytes | None:
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError:
        return None


def _written(files: list[tuple[Path, bytes | None]]) -> dict[str, bytes | None]:
    """What the import left in each file it wrote, to see later edits."""
    return {str(path): _bytes_now(path) for path, _ in files}


def changed_since_import() -> list[str]:
    """Files of the last import saved again since (the Button Map, Module
    Setup): Undo Import would lose those changes (08 Q5)."""
    record = _last_import
    if record is None or "written" not in record:
        return []
    written = record["written"]
    names: list[str] = []
    for path, _ in record["files"]:
        if str(path) in written and _bytes_now(path) != written[str(path)]:
            if path.name not in names:
                names.append(path.name)
    return names


def undo_import(force: bool = False) -> dict:
    """Puts back what the last import replaced. A file changed since the
    import is asked about first (08 Q5, GL-031): {"ask": True, ...} and
    nothing changes; force=True puts it back anyway."""
    global _last_import
    changed = changed_since_import()
    if changed and not force:
        return {
            "ok": False,
            "ask": True,
            "changed": changed,
            "error": "Changed after the import: "
            + ", ".join(changed)
            + ". Undo Import puts these back as they were before the import, "
            "and those changes are lost.",
        }
    record, _last_import = _last_import, None
    if record is None:
        return {"ok": False, "error": "There is no import to undo."}
    notes: list[str] = []
    for path, previous in reversed(record["files"]):
        try:
            # Through the store, as every other put-back: History shows a
            # removal once it went through; the old bytes go back as they
            # were, also over a file damaged since.
            if previous is None:
                store.delete_path(path, "Device Pack")
            else:
                store.replace(path, previous, "Device Pack", force=True)
        except OSError:
            notes.append(f"{path.name} could not be put back.")
    wires = record.get("wires")
    logical_changed = False
    if wires:
        from gremlin.logical_device import LogicalDevice
        from gremlin.shared_state import current_profile
        from gremlin.types import InputType

        profile = wires["profile"]
        if profile is not current_profile:
            notes.append("Another profile is open now, so the wires were not put back.")
        else:
            try:
                _put_inputs_back(profile, wires["uid"], wires)
            except Exception as exc:
                notes.append(f"The wires could not be put back, so they stay. {exc}")
                wires = None
        if wires and profile is current_profile:
            # The full delete (running modes, main window, pages), as Manage
            # Modes does; the profile alone left them on the deleted mode.
            from gremlin.ui.profile import delete_mode

            for mode in reversed(wires["modes"]):
                modes = profile.modes
                if (
                    modes.mode_exists(mode)
                    and modes.bindings_in_mode(mode) == 0
                    and len(modes.mode_names()) > 1
                ):
                    delete_mode(mode)
            kept = []
            for made_uid in wires["logical"]:
                # By its permanent id: the number may have changed since.
                ident = LogicalDevice().identifier_of_uid(made_uid)
                if ident is None:
                    continue
                if _logical_has_actions(profile, ident):
                    # Actions added since the import stay with it (08 Q21).
                    kept.append(
                        f"{InputType.to_string(ident.type).capitalize()} {ident.id}"
                    )
                    continue
                LogicalDevice().delete(ident)
                logical_changed = True
            if kept:
                notes.append(
                    "Kept on the Logical Device, because they have actions now: "
                    + ", ".join(kept)
                    + "."
                )
    if logical_changed:
        # Out of the module file too (08 S80).
        from gremlin import logical_device_file

        try:
            logical_device_file.save(who="Device Pack")
        except OSError as exc:
            notes.append(f"The Logical Device file could not be saved: {exc}")
    try:
        from gremlin.signal import signal

        if logical_changed:
            signal.logicalDeviceModified.emit()
        signal.configChanged.emit()
        signal.profileChanged.emit()
        signal.reloadUi.emit()
    except Exception:
        pass
    return {"ok": True, "report": "\n".join(["Undid the import."] + notes)}


def _write_module(
    dest: Path,
    merged: dict,
    record: list[tuple[Path, bytes | None]],
) -> str:
    """Writes one module file, keeping the previous one in imported\\ and
    for Undo Import. Returns the backup's name, "" for a new file; raises
    OSError when it can't."""
    previous = dest.read_bytes() if dest.is_file() else None
    backup_name = ""
    if previous is not None:
        backup = _unique_archive(dest.stem)
        store.replace(backup, previous, "Device Pack")
        backup_name = backup.name
    record.append((dest, previous))
    try:
        # A damaged file is refused (decision F1); apply_zip checks first.
        store.replace(
            dest, (json.dumps(merged, indent=2) + "\n").encode("utf-8"), "Device Pack"
        )
    except module_file.ModuleFileDamaged as damaged:
        raise OSError(str(damaged)) from damaged
    return backup_name


_INPUT_KEYS = {
    "in.checks", "in.names", "in.calibration", "in.view", "in.catalog",
    "in.layout", "in.mapview", "in.print",
}


def _is_checks(item_id: str) -> bool:
    """A Checked controls piece ("in.checks", "out:<slug>.checks")."""
    return item_id == "in.checks" or (
        item_id.startswith("out:") and item_id.endswith(".checks")
    )


def _titles(path: Path, chosen: set[str]) -> list[str]:
    described = describe_zip(path)
    if isinstance(described, str):
        return []
    out = []
    for section in described.get("sections") or []:
        # Wires are listed per mode, with their counts, by the warning.
        if section.get("id") == "wires":
            continue
        # Checked controls are added, not replaced: said on their own line
        # (addsChecks, 08 Q3).
        names = [
            str(item.get("title") or "")
            for item in section.get("items") or []
            if item.get("id") in chosen and not _is_checks(str(item.get("id")))
        ]
        if names:
            out.append(f"{section.get('title')}: " + ", ".join(names))
    return out


def preview_import(
    path: Path, target_name: str, selection: dict | None, *, target_guid: str = ""
) -> dict:
    """What Import would replace, for the warning before it. target_guid
    (or the selection's "targetGuid"): the chosen row's id, which decides
    the device when twins share a name (08 S106a)."""
    target = " ".join(str(target_name or "").split())
    target_guid = _target_guid(selection, target_guid)
    loaded = _read_zip(path)
    if isinstance(loaded, str):
        return {"ok": False, "error": loaded}
    newer = _too_new(loaded["doc"])
    if newer:
        return {"ok": False, "error": newer}
    chosen = _selected(selection)
    if target_guid:
        match = _match_pack_device(target, target_guid) or {
            "name": target, "guid": target_guid, "connected": False
        }
        target = str(match.get("name") or target)
    else:
        match = _match_pack_device(target)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    limits = _device_limits(guid)
    plan = _plan_wires(loaded["wires"], chosen, limits)
    here: dict[str, int] = {}
    profile_open = False
    try:
        from gremlin.shared_state import current_profile

        profile_open = current_profile is not None
        uid = parse_guid(guid) if guid else None
        if current_profile is not None and uid is not None:
            for item in current_profile.inputs.get(uid, []) or []:
                mode = str(item.mode or "Default")
                if mode in plan["modes"] and item.action_sequences:
                    here[mode] = here.get(mode, 0) + 1
    except Exception:
        pass
    left_out = list(plan["leftOut"])
    if limits is not None and "in.checks" in chosen:
        buttons, axes, hats = _checked_ids(loaded["doc"])
        for word, ids in (("Button", buttons), ("Axis", axes), ("Hat", hats)):
            for number in sorted(ids - limits[word.lower()]):
                label = f"{word} {number}"
                if label not in left_out:
                    left_out.append(label)
    targets = selection.get("outputs") if isinstance(selection, dict) else {}
    targets = targets if isinstance(targets, dict) else {}
    moves = _vjoy_moves(loaded["outputs"], targets)
    vjoys, xbox = _needs(_retarget_vjoy(plan["actions"], moves))
    for output in loaded["outputs"]:
        label = output.get("pack") if isinstance(output.get("pack"), dict) else {}
        slug = str(label.get("slug") or _pack_key(str(output.get("device") or "")))
        if not any(item.startswith(f"out:{slug}.") for item in chosen):
            continue
        name = str(targets.get(slug) or label.get("exportedName") or "")
        if _vjoy_number(name):
            vjoys.add(_vjoy_number(name))
        elif "xbox" in name.lower():
            xbox = True
    return {
        "drivers": driver_notes(vjoys, xbox),
        "ok": True,
        "device": target,
        "pieces": _titles(path, chosen),
        # Checked controls are added to the ones checked here (08 Q3).
        "addsChecks": any(_is_checks(item) for item in chosen),
        "modes": [
            {
                "name": name,
                "here": here.get(name, 0),
                "pack": plan["counts"].get(name, 0),
            }
            for name in plan["modes"]
        ],
        "hasModuleFile": (
            _device_path(target, guid if target_guid else "").is_file()
            if target
            else False
        ),
        "profileOpen": profile_open,
        "missingLogical": [f"{k.capitalize()} {n}" for k, n, _ in plan["missingLogical"]],
        "leftOut": left_out,
        "moves": [
            {"from": f"vJoy {a}", "to": f"vJoy {b}"} for a, b in sorted(moves.items())
        ],
        "deviceKnown": limits is not None,
    }


def apply_zip(
    path: Path,
    target_name: str,
    selection: dict | None,
    profile: Profile | None = None,
    *,
    record_undo: bool = True,
    fresh: bool = False,
    target_guid: str = "",
) -> dict:
    """Imports the ticked pieces onto target_name. For the Device Library
    (10 S24, S41), without the window: profile is the profile the wires go
    into (None: the open one); record_undo=False leaves Undo Import as it
    was (the Library's autosave is the way back); fresh=True builds the
    module file from the pack alone instead of adding to the one here;
    target_guid (twins share a name) decides which device it is."""
    global _last_import
    target = " ".join(str(target_name or "").split())
    target_guid = _target_guid(selection, target_guid)
    if not target:
        return {"ok": False, "error": "Choose the device this pack is for."}
    loaded = _read_zip(path)
    if isinstance(loaded, str):
        trace("READ", "Device Pack", "apply_zip", path, "error")
        return {"ok": False, "error": loaded}
    trace("READ", "Device Pack", "apply_zip", path, "ok")
    doc = loaded["doc"]
    newer = _too_new(doc)
    if newer:
        return {"ok": False, "error": newer}
    label = doc.get("pack") if isinstance(doc.get("pack"), dict) else {}
    exported = str(label.get("exportedName") or doc.get("device") or "").strip()
    if not exported:
        return {"ok": False, "error": "This pack has no device name."}
    if _doc_direction(doc, exported) != _target_direction(target):
        if _doc_direction(doc, exported) == "dest":
            return {"ok": False, "error": "A vJoy pack cannot be copied onto a stick."}
        return {"ok": False, "error": "A stick pack cannot be copied onto a vJoy."}
    chosen = _selected(selection)
    if not chosen:
        return {"ok": False, "error": "Choose at least one piece to import."}
    match = _match_pack_device(target, target_guid)
    if target_guid:
        # The id decides (twins share a name). A stick that isn't plugged
        # in is still the one the caller knows (the Device Library's Undo,
        # 10 S41): its own file by its id, never another's by the name.
        if not match:
            match = {"name": target, "guid": target_guid, "connected": False}
        target = str(match.get("name") or target)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    limits = _device_limits(guid)
    notes: list[str] = []
    files: list[tuple[Path, bytes | None]] = []
    # Picture ids are pic:<archive name>, including output photos that share the zip root.
    touches_input = bool(chosen & _INPUT_KEYS) or any(
        item.startswith("pic:") and _picture_is_input(item, doc) for item in chosen
    )
    if touches_input:
        dest = _device_path(target, guid if target_guid else "")
        damaged = store.damage_of(dest)
        if damaged:
            # 08 Q2 / F1: refused, as every other save into a damaged file;
            # nothing is changed (the wires neither).
            return {"ok": False, "error": _damaged_text(dest, damaged)}
        existing = None if fresh else _read_doc(dest)
        merged, merged_notes = _merge_module(
            existing, doc, chosen, "in.", target, guid, limits
        )
        try:
            _write_pictures(_slug_for_path(dest), loaded["files"], chosen, merged, files)
            backup_name = _write_module(dest, merged, files)
        except OSError:
            # The pictures written for it go back too; the import before
            # this one can still be undone.
            _put_back(files)
            return {
                "ok": False,
                "error": "The module file or its pictures could not be written, "
                "so nothing was replaced.",
            }
        notes.append(f"Saved {dest.name} for {target}.")
        notes.append(
            f"The previous file was kept as imported\\{backup_name}."
            if backup_name
            else "A new file was created."
        )
        notes.extend(merged_notes)
    targets = selection.get("outputs") if isinstance(selection, dict) else {}
    if not isinstance(targets, dict):
        targets = {}
    for output in loaded["outputs"]:
        out_label = output.get("pack") if isinstance(output.get("pack"), dict) else {}
        slug = str(out_label.get("slug") or _pack_key(str(output.get("device") or "")))
        prefix = "out:" + slug + "."
        if not any(item.startswith(prefix) or item == "pic:" + Path(str(output.get("image") or "")).name for item in chosen):
            continue
        out_name = " ".join(str(targets.get(slug) or out_label.get("exportedName") or output.get("device") or "").split())
        if not out_name:
            notes.append("An output module was skipped because it has no name.")
            continue
        if _doc_direction(output, out_name) != _target_direction(out_name):
            notes.append(f"{out_name} was skipped because a stick and a vJoy cannot share a file.")
            continue
        out_match = _match_pack_device(out_name)
        out_guid = str(out_match["guid"]) if out_match and out_match.get("guid") else ""
        dest = _device_path(out_name)
        if store.damage_of(dest):
            notes.append(
                f"{out_name} was skipped because its module file {dest.name} "
                "is damaged. Choose Start Fresh on its card first."
            )
            continue
        existing = _read_doc(dest)
        # Within what the vJoy device has, as for a stick (08 Q18, GL-191).
        out_limits = _vjoy_limits(_vjoy_number(out_name))
        merged, merged_notes = _merge_module(
            existing, output, chosen, prefix, out_name, out_guid, out_limits
        )
        start = len(files)
        try:
            _write_pictures(dest.stem, loaded["files"], chosen, merged, files)
            _write_module(dest, merged, files)
        except OSError:
            # Its pictures written so far go back.
            _put_back(files[start:])
            del files[start:]
            notes.append(
                f"The file or pictures for {out_name} could not be written, "
                "so it was not changed."
            )
            continue
        notes.append(f"Saved {dest.name} for {out_name}.")
        notes.extend(merged_notes)
    # The profile they go into says which Logical Device inputs it lacks.
    plan = _plan_wires(loaded["wires"], chosen, limits, _rows_of(profile))
    wire_notes, wires_undo = _apply_wires(
        plan,
        loaded["wires"].get("tree") or {},
        guid,
        target,
        _vjoy_moves(loaded["outputs"], targets),
        bool((selection or {}).get("createLogical")),
        profile,
    )
    notes.extend(wire_notes)
    if not notes:
        return {"ok": False, "error": "Nothing in the pack matched the pieces you ticked."}
    if not files and wires_undo is None:
        # Nothing was written (an output that couldn't be, wires that
        # weren't): the import before this one can still be undone.
        return {"ok": False, "error": "\n".join(notes)}
    if record_undo:
        # A new import keeps the one before it for good (only an import that
        # changed something: a failed one leaves the last one undoable).
        drop_import_undo()
        _last_import = {"files": files, "wires": wires_undo, "written": _written(files)}
    try:
        from gremlin.signal import signal
        signal.configChanged.emit()
        signal.profileChanged.emit()
        signal.reloadUi.emit()
    except Exception:
        pass
    return {"ok": True, "device": target, "report": "\n".join(notes), "canUndo": record_undo}


def pack_item_ids(path: Path) -> dict | str:
    """A pack's input device pieces as the window's item ids, without
    staging its pictures (for the Device Library, 10 S23-S24):
    {"input": [ids], "modes": [modes with wires]}; a str when it can't be
    read."""
    loaded = _read_zip(path)
    if isinstance(loaded, str):
        return loaded
    doc = loaded["doc"]
    newer = _too_new(doc)
    if newer:
        return newer
    arcs: list[str] = []
    photo = Path(str(doc.get("image") or "")).name
    if photo and photo in loaded["files"]:
        arcs.append(photo)
    for node in doc.get("nodes") or []:
        if isinstance(node, dict) and (
            node.get("kind") == "image" or node.get("shape") == "image"
        ):
            arc = Path(str(node.get("src") or "")).name
            if arc and arc in loaded["files"] and arc not in arcs:
                arcs.append(arc)
    pictures = [{"item": _item("pic:" + arc, arc, arc)} for arc in arcs]
    ids = [str(row["id"]) for row in _module_items("in.", doc, pictures)]
    ids.extend("pic:" + arc for arc in arcs)
    modes = [
        str(mode.get("name") or "Default")
        for mode in loaded["wires"].get("modes") or []
        if isinstance(mode, dict) and mode.get("inputs")
    ]
    return {"input": list(dict.fromkeys(ids)), "modes": modes}


def _damaged_text(path: Path, reason: str) -> str:
    return (
        f"Nothing was imported: the module file {path.name} is damaged "
        f"({reason}). Choose Start Fresh on the device's card first (the "
        "damaged file is kept)."
    )


def _slug_for_path(path: Path) -> str:
    return path.stem


def _picture_is_input(item: str, doc: dict) -> bool:
    arc = item[4:]
    if Path(str(doc.get("image") or "")).name == arc:
        return True
    for node in doc.get("nodes") or []:
        if isinstance(node, dict) and Path(str(node.get("src") or "")).name == arc:
            return True
    return False


# Public names for the Device Library store (gremlin/modules/library.py).
collect_wires = _collect_wires
pack_label = _pack_label
too_new = _too_new
