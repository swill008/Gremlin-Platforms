# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""One zip for a whole device: a working copy of what was exported.

Import is destructive by design: each ticked piece replaces what is on this
machine (module file pieces; for a ticked mode, the device's wires and
actions in that mode). The window warns first, the previous module file is
kept in the imported folder, and Undo Import puts back the last import."""

from __future__ import annotations

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

from typing import TYPE_CHECKING

from gremlin.ui.live_debug import trace
from gremlin.modules.claim import claim_ids
from gremlin.modules.registry import is_output_name
from gremlin.ui.hardware_profile import (
    _IMAGE_EXT,
    _asset_ref,
    _claim_summary,
    _collapsed_name,
    _doc_direction,
    _maps_dir,
    _match_pack_device,
    _outside_maps,
    _read_json_dict,
    _replace_file,
    _safe_name,
    _slug,
    _suggest_pack_name,
    _target_direction,
    _unique_archive,
    member_kind,
    module_json_path,
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
        from gremlin.ui.input_pairing import _guid
    except Exception:
        return []
    uid = _guid(str(guid or "").strip())
    if current_profile is None or uid is None:
        return []
    counts: dict[str, int] = {}
    for item in current_profile.inputs.get(uid, []) or []:
        if getattr(item, "action_sequences", None):
            mode = str(getattr(item, "mode", "") or "Default")
            counts[mode] = counts.get(mode, 0) + 1
    return [{"name": name, "count": counts[name]} for name in sorted(counts)]


def _collect_wires(guid: str, only_modes: list[str] | None = None) -> dict:
    text = str(guid or "").strip()
    empty = {"modes": [], "actions": [], "outputs": [], "tree": {}}
    if not text:
        return empty
    try:
        from gremlin.shared_state import current_profile
        from gremlin.ui.input_pairing import _dest_labels_for_item, _guid
        from gremlin.util import read_action_ids
    except Exception:
        return empty
    profile = current_profile
    uid = _guid(text)
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
                dest = " + ".join(_dest_labels_for_item(item))
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
    return {
        "modes": list(modes.values()),
        "actions": action_xml,
        "outputs": outputs,
        "tree": _mode_tree(profile, list(modes)),
    }


def _output_doc(name: str, resolve, used: set[str], files: list[tuple[Path, str]]) -> tuple[dict, list[dict]] | None:
    match = _match_pack_device(name)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    slug = _slug(name)
    path = module_json_path(name, guid)
    doc = _read_json_dict(path) if path.is_file() else None
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


def _device_path(name: str) -> Path:
    match = _match_pack_device(name)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    return module_json_path(name, guid)


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


def assemble(
    device_name: str,
    resolve,
    modes: list[str] | None = None,
    notes: dict | None = None,
) -> tuple[bytes, dict] | str:
    """The pack for one device. modes: the modes whose wires go in (None:
    all of them). notes: {author, note}, shown when the pack is imported."""
    name = " ".join(str(device_name or "").split())
    if not name:
        return "Choose a device."
    path = _device_path(name)
    doc = _read_json_dict(path) if path.is_file() else None
    if not doc:
        return "This device has no module file yet."
    match = _match_pack_device(name)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    used: set[str] = set()
    files: list[tuple[Path, str]] = []
    packed, pictures = _rewrite_images(doc, resolve, used, files)
    packed.pop("boundGuidLocal", None)
    packed.pop("boundName", None)
    packed["device"] = name
    packed["pack"] = _pack_label(name, guid, notes)
    wires = _collect_wires(guid, modes)
    outputs: list[dict] = []
    for output_name in wires["outputs"]:
        built = _output_doc(output_name, resolve, used, files)
        if built is None:
            continue
        out_doc, out_pictures = built
        outputs.append({"doc": out_doc, "pictures": out_pictures, "name": output_name})
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("map.json", json.dumps(packed, indent=2) + "\n")
        if wires["modes"]:
            zf.writestr("wires.json", json.dumps({
                "modes": wires["modes"],
                "actions": wires["actions"],
                "tree": wires["tree"],
            }, indent=2) + "\n")
        for output in outputs:
            slug = str((output["doc"].get("pack") or {}).get("slug") or _slug(output["name"]))
            zf.writestr(f"outputs/{slug}.json", json.dumps(output["doc"], indent=2) + "\n")
        for src, arc in files:
            zf.write(src, arc)
    data = blob.getvalue()
    photo = ""
    for picture in pictures:
        if not picture.get("onMap"):
            photo = str(resolve(str(doc.get("image") or "")) or "")
            break
    return data, {
        "device": name,
        "photoPath": photo,
        "bytes": len(data),
        "sizeText": size_text(len(data)),
    }


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


def _stage_images(files: dict[str, bytes]) -> tuple[str, dict[str, str]]:
    global _preview_dir
    if _preview_dir and os.path.isdir(_preview_dir):
        shutil.rmtree(_preview_dir, ignore_errors=True)
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
        slug = str(out_label.get("slug") or _slug(out_name))
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
    """The module file after the ticked pieces replace what is here. limits:
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
        for key, value in incoming["calibration"].items():
            try:
                number = int(key)
            except (TypeError, ValueError):
                continue
            if number in axes:
                stored[str(number)] = value
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


def _selected(selection: dict | None) -> set[str]:
    if not isinstance(selection, dict):
        return set()
    return {str(item) for item in (selection.get("items") or [])}


def _remap_actions(action_xml: list[str], input_xml: list[str], library) -> tuple[list[str], list[str]]:
    ids: set[str] = set()
    for block in action_xml:
        for found in _UUID_RE.findall(block):
            ids.add(found)
    mapping: dict[str, str] = {}
    for found in ids:
        try:
            key = uuid.UUID(found)
        except ValueError:
            continue
        if library.has_action(key):
            mapping[found.lower()] = str(uuid.uuid4())
    if not mapping:
        return action_xml, input_xml

    def swap(text: str) -> str:
        out = text
        for old, new in mapping.items():
            out = re.sub(old, new, out, flags=re.IGNORECASE)
        return out

    return [swap(block) for block in action_xml], [swap(block) for block in input_xml]


def _write_pictures(
    slug: str,
    files: dict[str, bytes],
    chosen: set[str],
    doc: dict,
    record: list[tuple[Path, bytes | None]] | None = None,
) -> dict[str, str]:
    written: dict[str, str] = {}
    folder = _maps_dir() / slug
    folder.mkdir(parents=True, exist_ok=True)
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
            _replace_file(backup.with_suffix(dest.suffix), dest.read_bytes())
            trace("SAVE", "Device Pack", "_write_pictures", backup, "ok")
        dest.write_bytes(data)
        trace("SAVE", "Device Pack", "_write_pictures", dest, "ok")
        written[arc] = dest.name
    photo = Path(str(doc.get("image") or "")).name
    if photo in written:
        doc["image"] = _asset_ref(slug, written[photo])
    elif "pic:" + photo not in chosen:
        pass
    else:
        doc.pop("image", None)
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        key = Path(str(node.get("src") or "")).name
        if key in written:
            node["src"] = _asset_ref(slug, written[key])
    return written


def _device_limits(guid: str) -> dict[str, set[int]] | None:
    """The buttons, axes and hats the connected device has (None: not
    connected, so not known)."""
    from gremlin.ui.hardware_profile import _guid_text, _live_devices

    want = str(guid or "").strip().lower()
    if not want:
        return None
    for dev in _live_devices():
        if _guid_text(getattr(dev, "device_guid", "")).lower() != want:
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
        slug = str(label.get("slug") or _slug(str(output.get("device") or "")))
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


def _logical_targets(action_xml: list[str]) -> list[tuple[str, int]]:
    """The Logical Device inputs these actions send to: (type, number)."""
    found: list[tuple[str, int]] = []
    for block in action_xml:
        node = ElementTree.fromstring(block)
        if node.get("type") != "map-to-logical-device":
            continue
        props = {
            prop.findtext("name"): prop.findtext("value")
            for prop in node.findall("property")
        }
        kind = str(props.get("logical-input-type") or "").strip().lower()
        try:
            number = int(str(props.get("logical-input-id") or "").strip())
        except ValueError:
            continue
        if kind and (kind, number) not in found:
            found.append((kind, number))
    return found


def _missing_logical(action_xml: list[str]) -> list[tuple[str, int]]:
    from gremlin.logical_device import LogicalDevice
    from gremlin.types import InputType

    missing = []
    for kind, number in _logical_targets(action_xml):
        try:
            ident = LogicalDevice.Input.Identifier(InputType.to_enum(kind), number)
        except Exception:
            continue
        if not LogicalDevice().exists(ident):
            missing.append((kind, number))
    return missing


def _plan_wires(
    wires: dict, chosen: set[str], limits: dict[str, set[int]] | None
) -> dict:
    """What importing the ticked modes would write, before anything changes:
    their inputs (less the controls the device doesn't have) and only the
    actions those inputs use."""
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
        "missingLogical": _missing_logical(actions),
    }


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
) -> tuple[list[str], dict | None]:
    """Replaces the device's wires and actions in each ticked mode with the
    pack's. Returns the notes and what Undo Import needs."""
    if not plan["modes"]:
        return [], None
    if not target_guid:
        return ["The wires were not written. This name has no device id."], None
    try:
        from gremlin.logical_device import LogicalDevice
        from gremlin.profile import DeviceInfo, InputItem
        from gremlin.shared_state import current_profile
        from gremlin.types import InputType
        from gremlin.ui.input_pairing import _guid
    except Exception:
        return ["The wires were not written."], None
    profile = current_profile
    if profile is None:
        return ["The wires were not written. No profile is open."], None
    uid = _guid(target_guid)
    if uid is None:
        return ["The wires were not written. This name has no device id."], None
    notes: list[str] = []
    try:
        action_xml, input_xml = _remap_actions(
            plan["actions"], plan["inputs"], profile.library
        )
        action_xml = _retarget_vjoy(action_xml, moves)
        created_logical = []
        missing = plan["missingLogical"]
        if missing and create_logical:
            for kind, number in missing:
                made = LogicalDevice().create(InputType.to_enum(kind), input_id=number)
                created_logical.append(made.identifier)
            notes.append(
                "Created on the Logical Device: "
                + ", ".join(f"{kind.capitalize()} {number}" for kind, number in missing)
                + "."
            )
        elif missing:
            notes.append(
                "These wires send to Logical Device inputs that don't exist here, "
                "so they do nothing until you add them: "
                + ", ".join(f"{kind.capitalize()} {number}" for kind, number in missing)
                + "."
            )
        created_modes = _ensure_modes(profile, plan["modes"], tree, notes)
        # Each ticked mode: everything the device had there goes.
        removed = []
        kept = []
        for item in profile.inputs.get(uid, []) or []:
            replaced = str(item.mode or "Default") in plan["modes"]
            (removed if replaced else kept).append(item)
        if uid in profile.inputs:
            profile.inputs[uid] = kept
        if action_xml:
            library_node = ElementTree.Element("library")
            for block in action_xml:
                library_node.append(ElementTree.fromstring(block))
            root = ElementTree.Element("profile")
            root.append(library_node)
            profile.library.from_xml(root)
        added = []
        for block in input_xml:
            item = InputItem(profile.library)
            item.from_xml(ElementTree.fromstring(block))
            item.device_id = uid
            item.mode = str(item.mode or "Default")
            for seq in item.action_sequences:
                seq.input_item = item
            profile.inputs.setdefault(uid, []).append(item)
            added.append(item)
        if uid not in profile.device_database.devices:
            profile.device_database.devices[uid] = DeviceInfo(uid, target_name)
    except Exception as exc:
        return [f"The wires were not written. {exc}"], None
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
        from gremlin.signal import signal

        signal.logicalDeviceModified.emit()
    undo = {
        "profile": profile,
        "uid": uid,
        "removed": removed,
        "added": added,
        "modes": created_modes,
        "logical": created_logical,
    }
    return notes, undo


# The last import, so Undo Import can put it back: the files it replaced
# (with their previous bytes, None for a new file) and the wires.
_last_import: dict | None = None


def _roots(items: list) -> list:
    return [
        binding.root_action
        for item in items
        for binding in item.action_sequences
        if binding.root_action is not None
    ]


def can_undo_import() -> bool:
    return _last_import is not None


def drop_import_undo() -> None:
    """Keeps the last import: the actions it replaced leave the profile."""
    global _last_import
    record, _last_import = _last_import, None
    wires = (record or {}).get("wires")
    if not wires:
        return
    from gremlin.shared_state import current_profile

    profile = current_profile
    if profile is not None and wires["profile"] is profile:
        profile.drop_unused_actions(_roots(wires["removed"]))


def undo_import() -> dict:
    """Puts back what the last import replaced."""
    global _last_import
    record, _last_import = _last_import, None
    if record is None:
        return {"ok": False, "error": "There is no import to undo."}
    notes: list[str] = []
    for path, previous in reversed(record["files"]):
        try:
            if previous is None:
                if path.is_file():
                    path.unlink()
            else:
                _replace_file(path, previous)
            trace("SAVE", "Device Pack", "undo_import", path, "ok")
        except OSError:
            notes.append(f"{path.name} could not be put back.")
    wires = record.get("wires")
    if wires:
        from gremlin.logical_device import LogicalDevice
        from gremlin.shared_state import current_profile

        profile = wires["profile"]
        if profile is not current_profile:
            notes.append("Another profile is open now, so the wires were not put back.")
        else:
            added = {id(item) for item in wires["added"]}
            items = [
                item
                for item in profile.inputs.get(wires["uid"], [])
                if id(item) not in added
            ]
            profile.inputs[wires["uid"]] = items + list(wires["removed"])
            profile.drop_unused_actions(_roots(wires["added"]))
            for mode in reversed(wires["modes"]):
                modes = profile.modes
                if modes.mode_exists(mode) and modes.bindings_in_mode(mode) == 0:
                    profile.modes.delete_mode(mode)
            for ident in wires["logical"]:
                if LogicalDevice().exists(ident):
                    LogicalDevice().delete(ident)
    try:
        from gremlin.signal import signal

        if wires and wires.get("logical"):
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
        _replace_file(backup, previous)
        trace("SAVE", "Device Pack", "apply_zip", backup, "ok")
        backup_name = backup.name
    record.append((dest, previous))
    _replace_file(dest, (json.dumps(merged, indent=2) + "\n").encode("utf-8"))
    trace("SAVE", "Device Pack", "apply_zip", dest, "ok")
    return backup_name


_INPUT_KEYS = {
    "in.checks", "in.names", "in.calibration", "in.view", "in.catalog",
    "in.layout", "in.mapview", "in.print",
}


def _titles(path: Path, chosen: set[str]) -> list[str]:
    described = describe_zip(path)
    if isinstance(described, str):
        return []
    out = []
    for section in described.get("sections") or []:
        # Wires are listed per mode, with their counts, by the warning.
        if section.get("id") == "wires":
            continue
        names = [
            str(item.get("title") or "")
            for item in section.get("items") or []
            if item.get("id") in chosen
        ]
        if names:
            out.append(f"{section.get('title')}: " + ", ".join(names))
    return out


def preview_import(path: Path, target_name: str, selection: dict | None) -> dict:
    """What Import would replace, for the warning before it."""
    target = " ".join(str(target_name or "").split())
    loaded = _read_zip(path)
    if isinstance(loaded, str):
        return {"ok": False, "error": loaded}
    newer = _too_new(loaded["doc"])
    if newer:
        return {"ok": False, "error": newer}
    chosen = _selected(selection)
    match = _match_pack_device(target)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    limits = _device_limits(guid)
    plan = _plan_wires(loaded["wires"], chosen, limits)
    here: dict[str, int] = {}
    profile_open = False
    try:
        from gremlin.shared_state import current_profile
        from gremlin.ui.input_pairing import _guid

        profile_open = current_profile is not None
        uid = _guid(guid) if guid else None
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
    moves = _vjoy_moves(loaded["outputs"], targets if isinstance(targets, dict) else {})
    return {
        "ok": True,
        "device": target,
        "pieces": _titles(path, chosen),
        "modes": [
            {
                "name": name,
                "here": here.get(name, 0),
                "pack": plan["counts"].get(name, 0),
            }
            for name in plan["modes"]
        ],
        "hasModuleFile": _device_path(target).is_file() if target else False,
        "profileOpen": profile_open,
        "missingLogical": [f"{k.capitalize()} {n}" for k, n in plan["missingLogical"]],
        "leftOut": left_out,
        "moves": [
            {"from": f"vJoy {a}", "to": f"vJoy {b}"} for a, b in sorted(moves.items())
        ],
        "deviceKnown": limits is not None,
    }


def apply_zip(path: Path, target_name: str, selection: dict | None) -> dict:
    global _last_import
    target = " ".join(str(target_name or "").split())
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
    # A new import keeps the one before it for good.
    drop_import_undo()
    match = _match_pack_device(target)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    limits = _device_limits(guid)
    notes: list[str] = []
    files: list[tuple[Path, bytes | None]] = []
    # Picture ids are pic:<archive name>, including output photos that share the zip root.
    touches_input = bool(chosen & _INPUT_KEYS) or any(
        item.startswith("pic:") and _picture_is_input(item, doc) for item in chosen
    )
    if touches_input:
        dest = _device_path(target)
        existing = _read_json_dict(dest) if dest.is_file() else None
        merged, merged_notes = _merge_module(
            existing, doc, chosen, "in.", target, guid, limits
        )
        _write_pictures(_slug_for_path(dest), loaded["files"], chosen, merged, files)
        try:
            backup_name = _write_module(dest, merged, files)
        except OSError:
            return {
                "ok": False,
                "error": "The module file could not be written, so nothing was replaced.",
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
        slug = str(out_label.get("slug") or _slug(str(output.get("device") or "")))
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
        existing = _read_json_dict(dest) if dest.is_file() else None
        merged, merged_notes = _merge_module(existing, output, chosen, prefix, out_name, out_guid)
        _write_pictures(dest.stem, loaded["files"], chosen, merged, files)
        try:
            _write_module(dest, merged, files)
        except OSError:
            notes.append(
                f"The file for {out_name} could not be written, so it was not changed."
            )
            continue
        notes.append(f"Saved {dest.name} for {out_name}.")
        notes.extend(merged_notes)
    plan = _plan_wires(loaded["wires"], chosen, limits)
    wire_notes, wires_undo = _apply_wires(
        plan,
        loaded["wires"].get("tree") or {},
        guid,
        target,
        _vjoy_moves(loaded["outputs"], targets),
        bool((selection or {}).get("createLogical")),
    )
    notes.extend(wire_notes)
    if not notes:
        return {"ok": False, "error": "Nothing in the pack matched the pieces you ticked."}
    _last_import = {"files": files, "wires": wires_undo}
    try:
        from gremlin.signal import signal
        signal.configChanged.emit()
        signal.profileChanged.emit()
        signal.reloadUi.emit()
    except Exception:
        pass
    return {"ok": True, "device": target, "report": "\n".join(notes), "canUndo": True}


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
