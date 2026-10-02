# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""One zip for a whole device. Import chooses which pieces to append."""

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

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_KIND_WORD = {"btn": "Button", "button": "Button", "axis": "Axis", "hat": "Hat"}
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


def _camera_lines(doc: dict) -> list[str]:
    ui = doc.get("ui")
    if not isinstance(ui, dict) or not ui:
        return []
    lines = ["Pan, zoom, and grid. This is how the map was last viewed."]
    if "viewPct" in ui:
        lines.append(f"Zoom: {ui.get('viewPct')}")
    return lines


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
        items.append(_item(prefix + "view", "Display Editor", _clip(view)))
    chips = _chip_lines(doc)
    needs = [row["id"] for row in pictures if row.get("onMap")]
    if chips:
        row = _item(prefix + "layout", "Map", _clip(chips))
        row["needs"] = needs
        items.append(row)
    for picture in pictures:
        items.append(picture["item"])
    camera = _camera_lines(doc)
    if camera:
        items.append(_item(prefix + "camera", "Map camera", _clip(camera), checked=False))
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


def _collect_wires(guid: str) -> dict:
    text = str(guid or "").strip()
    empty = {"modes": [], "actions": [], "outputs": []}
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


def assemble(device_name: str, resolve) -> tuple[bytes, dict] | str:
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
    packed["pack"] = {"exportedName": name, "exportedGuid": guid}
    wires = _collect_wires(guid)
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


def _with_urls(pictures: list[dict], urls: dict[str, str]) -> list[dict]:
    rows = []
    for picture in pictures:
        item = dict(picture["item"])
        item["url"] = urls.get(picture["arc"], "")
        rows.append({
            "arc": picture["arc"],
            "onMap": picture.get("onMap"),
            "item": item,
        })
    return rows


def describe_zip(path: Path) -> dict | str:
    loaded = _read_zip(path)
    if isinstance(loaded, str):
        return loaded
    doc = loaded["doc"]
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
    module_rows, map_rows = _split_sections(doc, pictures, "in.")
    if module_rows:
        sections.append({"id": "input", "title": "Input module", "items": module_rows})
    if map_rows:
        sections.append({"id": "map", "title": "Button map", "items": map_rows})
    wire_items = []
    for mode in loaded["wires"].get("modes") or []:
        if not isinstance(mode, dict):
            continue
        mode_name = str(mode.get("name") or "Default")
        lines = [str(line) for line in (mode.get("lines") or []) if str(line).strip()]
        if not lines:
            continue
        wire_items.append(_item("wire:" + mode_name, mode_name, _clip(lines)))
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
            "items": _split_sections(output, out_pictures, "out:" + slug + ".")[0]
            + _split_sections(output, out_pictures, "out:" + slug + ".")[1],
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
    }


def _split_sections(doc: dict, pictures: list[dict], prefix: str) -> tuple[list[dict], list[dict]]:
    placed = _place_pictures(doc, pictures, prefix)
    module_ids = {prefix + "checks", prefix + "names", prefix + "calibration", prefix + "view"}
    return (
        [row for row in placed if row["id"] in module_ids],
        [row for row in placed if row["id"] not in module_ids],
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
    camera = [row for row in placed if row["id"].endswith("camera")]
    rest = [row for row in placed if not row["id"].endswith("camera")]
    return rest + camera


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


def _merge_module(existing: dict | None, incoming: dict, chosen: set[str], prefix: str, name: str, guid: str) -> tuple[dict, list[str]]:
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
            notes.append("The Display Editor points at " + ", ".join(unique) + f", and {noun} not checked.")
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
    if prefix + "camera" in chosen and isinstance(incoming.get("ui"), dict):
        base["ui"] = json.loads(json.dumps(incoming["ui"]))
    photo = Path(str(incoming.get("image") or "")).name
    if photo and ("pic:" + photo) in chosen:
        base["image"] = photo
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


def _apply_wires(wires: dict, chosen: set[str], target_guid: str, target_name: str) -> list[str]:
    modes = [mode for mode in (wires.get("modes") or []) if isinstance(mode, dict)]
    wanted = []
    for mode in modes:
        name = str(mode.get("name") or "Default")
        if "wire:" + name in chosen:
            wanted.append(mode)
    if not wanted:
        return []
    if not target_guid:
        return ["The wires were not written. This name has no device id."]
    try:
        from gremlin.profile import DeviceInfo, InputItem
        from gremlin.shared_state import current_profile
        from gremlin.ui.input_pairing import _guid
    except Exception:
        return ["The wires were not written."]
    profile = current_profile
    if profile is None:
        return ["The wires were not written. No profile is open."]
    uid = _guid(target_guid)
    if uid is None:
        return ["The wires were not written. This name has no device id."]
    action_xml = [str(block) for block in (wires.get("actions") or [])]
    input_xml = []
    for mode in wanted:
        input_xml.extend(str(block) for block in (mode.get("inputs") or []))
    try:
        action_xml, input_xml = _remap_actions(action_xml, input_xml, profile.library)
        if action_xml:
            library_node = ElementTree.Element("library")
            for block in action_xml:
                library_node.append(ElementTree.fromstring(block))
            root = ElementTree.Element("profile")
            root.append(library_node)
            profile.library.from_xml(root)
        added = 0
        skipped = 0
        created_modes: list[str] = []
        for block in input_xml:
            node = ElementTree.fromstring(block)
            item = InputItem(profile.library)
            item.from_xml(node)
            item.device_id = uid
            mode_name = str(item.mode or "Default")
            item.mode = mode_name
            if not profile.modes.mode_exists(mode_name):
                profile.modes.add_mode(mode_name)
                created_modes.append(mode_name)
            existing = profile.get_input_item(uid, item.input_type, item.input_id, mode_name, False)
            if existing is not None and existing.action_sequences:
                skipped += 1
                continue
            for seq in item.action_sequences:
                seq.input_item = item
            if existing is None:
                profile.inputs.setdefault(uid, []).append(item)
            else:
                existing.action_sequences = item.action_sequences
                for seq in existing.action_sequences:
                    seq.input_item = existing
            added += 1
        if uid not in profile.device_database.devices:
            profile.device_database.devices[uid] = DeviceInfo(uid, target_name)
    except Exception as exc:
        return [f"The wires were not written. {exc}"]
    notes = []
    if added:
        notes.append(
            f"Added {added} {'wire' if added == 1 else 'wires'} to the open profile. Save the profile to keep them."
        )
    if skipped:
        notes.append(
            f"Left {skipped} {'control' if skipped == 1 else 'controls'} alone because {'it already has' if skipped == 1 else 'they already have'} a wire in that mode."
        )
    if created_modes:
        notes.append("Created " + ", ".join(created_modes) + ".")
    if not added and not skipped:
        notes.append("No wires were written.")
    return notes


def _write_pictures(slug: str, files: dict[str, bytes], chosen: set[str], doc: dict) -> dict[str, str]:
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


def apply_zip(path: Path, target_name: str, selection: dict | None) -> dict:
    target = " ".join(str(target_name or "").split())
    if not target:
        return {"ok": False, "error": "Choose the device this pack is for."}
    loaded = _read_zip(path)
    if isinstance(loaded, str):
        trace("READ", "Device Pack", "apply_zip", path, "error")
        return {"ok": False, "error": loaded}
    trace("READ", "Device Pack", "apply_zip", path, "ok")
    doc = loaded["doc"]
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
    match = _match_pack_device(target)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    notes: list[str] = []
    input_keys = {"in.checks", "in.names", "in.calibration", "in.view", "in.layout", "in.camera"}
    input_pics = {item for item in chosen if item.startswith("pic:") and not item.startswith("pic:out_")}
    # Picture ids are pic:<archive name>, including output photos that share the zip root.
    touches_input = bool(chosen & input_keys) or any(
        item.startswith("pic:") and _picture_is_input(item, doc) for item in chosen
    )
    if touches_input:
        dest = _device_path(target)
        existing = _read_json_dict(dest) if dest.is_file() else None
        merged, merged_notes = _merge_module(existing, doc, chosen, "in.", target, guid)
        _write_pictures(_slug_for_path(dest), loaded["files"], chosen, merged)
        previous = dest.read_bytes() if dest.is_file() else None
        backup_name = ""
        if previous is not None:
            backup = _unique_archive(dest.stem)
            try:
                _replace_file(backup, previous)
                trace("SAVE", "Device Pack", "apply_zip", backup, "ok")
            except OSError:
                return {"ok": False, "error": "The previous file could not be saved, so nothing was replaced."}
            backup_name = backup.name
        try:
            _replace_file(dest, (json.dumps(merged, indent=2) + "\n").encode("utf-8"))
            trace("SAVE", "Device Pack", "apply_zip", dest, "ok")
        except OSError:
            return {"ok": False, "error": "The module file could not be written."}
        notes.append(f"Saved {dest.name} for {target}.")
        notes.append(
            f"The previous file was saved as {backup_name}."
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
        _write_pictures(dest.stem, loaded["files"], chosen, merged)
        previous = dest.read_bytes() if dest.is_file() else None
        if previous is not None:
            archive = _unique_archive(dest.stem)
            try:
                _replace_file(archive, previous)
                trace("SAVE", "Device Pack", "apply_zip", archive, "ok")
            except OSError:
                notes.append(f"The previous file for {out_name} could not be saved, so it was not changed.")
                continue
        try:
            _replace_file(dest, (json.dumps(merged, indent=2) + "\n").encode("utf-8"))
            trace("SAVE", "Device Pack", "apply_zip", dest, "ok")
        except OSError:
            notes.append(f"The file for {out_name} could not be written.")
            continue
        notes.append(f"Saved {dest.name} for {out_name}.")
        notes.extend(merged_notes)
    notes.extend(_apply_wires(loaded["wires"], chosen, guid, target))
    if not notes:
        return {"ok": False, "error": "Nothing in the pack matched the pieces you ticked."}
    try:
        from gremlin.signal import signal
        signal.configChanged.emit()
        signal.profileChanged.emit()
        signal.reloadUi.emit()
    except Exception:
        pass
    return {"ok": True, "device": target, "report": "\n".join(notes)}


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
