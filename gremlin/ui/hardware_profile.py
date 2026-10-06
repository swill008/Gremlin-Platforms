# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from PySide6 import (
    QtCore,
    QtGui,
    QtQuick,
)

import gremlin.ui.type_aliases as ta
from gremlin.modules import hardware, module_file
from gremlin.modules.claim import claim_ids
from gremlin.modules.ids import stored_guid_key
from gremlin.modules.registry import (
    _binding_store,
    _guid_for_name,
    _name_key,
    device_has_name,
    is_output_name,
    plain_slug,
    resolve_module_slug,
)
from gremlin.signal import signal
from gremlin.ui.live_debug import trace
from gremlin.ui.util import to_local_path

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


# Off unless someone is tracing a save. Same idea as the HidHide log switch.
_persist_log = False


def persist_log(message: str) -> None:
    if _persist_log:
        print(message, flush=True)


def _photo_pose(raw) -> dict:
    src = raw if isinstance(raw, dict) else {}

    def _num(key: str, default: float) -> float:
        try:
            val = float(src.get(key, default))
        except (TypeError, ValueError):
            val = default
        return val

    scale = _num("scale", 1.0)
    if scale <= 0:
        scale = 1.0
    pose = {
        "scale": max(0.25, min(4.0, scale)),
        "offX": max(-1.0, min(1.0, _num("offX", 0.0))),
        "offY": max(-1.0, min(1.0, _num("offY", 0.0))),
        "rot": _num("rot", 0.0),
    }
    # Set from the Button Map's Layers panel; written only when on.
    for flag in ("hidden", "locked"):
        if src.get(flag) is True:
            pose[flag] = True
    # The photo's look (Photo > Adjust photo); written only when changed.
    for key, low, high in _PHOTO_LOOK:
        value = max(low, min(high, _num(key, 0.0)))
        if value:
            pose[key] = value
    return pose


# Brightness and contrast -1..1, greyscale 0..1, fade 0..0.9.
_PHOTO_LOOK = (("bright", -1.0, 1.0), ("contrast", -1.0, 1.0), ("grey", 0.0, 1.0),
               ("fade", 0.0, 0.9))


_RECENT_COLOURS = 10


def _recent_count() -> int:
    """How many recent colours to keep (Options → Button Map → Colours)."""
    try:
        from gremlin.ui import button_map_options

        return max(1, int(button_map_options.value("recent-colours")))
    except Exception:
        return _RECENT_COLOURS


# A PDF without a paper (Print & Export's Freeform (As Drawn)): the page is the
# picture at 96 pixels an inch, as Windows shows things at 100%.
PDF_PPI = 96


def exact_page(image: QtGui.QImage, width: int, height: int) -> QtGui.QImage | None:
    """The picture of the print area (RigRenderer's grab, already on its
    background) at exactly width x height pixels, opaque. A grab comes back
    at the screen's scale, a pixel or so off the size asked for."""
    if image is None or image.isNull() or width < 1 or height < 1:
        return None
    page = image.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    page.setDevicePixelRatio(1.0)
    if page.width() != width or page.height() != height:
        page = page.scaled(
            int(width),
            int(height),
            QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
    return page


def save_area(
    image: QtGui.QImage,
    width: int,
    height: int,
    path: Path,
    fmt: str,
    setup: dict | None = None,
) -> bool:
    """Writes the print area as PNG, JPG or a one-page PDF, width x height
    pixels. A PDF goes on the paper of setup (page_layout), filling the
    space inside the margins, or with no paper on a page of its own shape
    at PDF_PPI."""
    page = exact_page(image, width, height)
    if page is None:
        return False
    kind = str(fmt or "png").lower()
    if kind == "pdf":
        from gremlin.ui.util import page_layout, save_images_as_pdf

        return save_images_as_pdf([page], path, PDF_PPI / 72, page_layout(setup))
    return _save_image(page, path, kind)


def _setup(setup_json: str) -> dict:
    """Print & Export's settings from QML (JSON), or {} when unreadable."""
    try:
        setup = json.loads(setup_json or "{}")
    except (TypeError, ValueError):
        return {}
    return setup if isinstance(setup, dict) else {}


def _save_image(page: QtGui.QImage, path: Path, kind: str) -> bool:
    if kind in ("jpg", "jpeg"):
        return page.save(str(path), "JPG", 92)
    return page.save(str(path), "PNG")


def adjust_photo(
    image: QtGui.QImage, bright: float, contrast: float, grey: float
) -> QtGui.QImage:
    """The photo with its look applied (Photo > Adjust photo): greyscale
    0..1 blends towards grey; contrast -1..1 flattens towards mid grey or
    deepens with an overlay of itself; brightness -1..1 washes towards white
    or black. Transparent parts stay transparent."""
    out = image.convertToFormat(QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    painter = QtGui.QPainter(out)
    mode = QtGui.QPainter.CompositionMode
    if grey > 0:
        flat = image.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
        painter.setCompositionMode(mode.CompositionMode_SourceAtop)
        painter.setOpacity(min(1.0, grey))
        painter.drawImage(0, 0, flat.convertToFormat(QtGui.QImage.Format.Format_ARGB32))
    if contrast > 0:
        copy = out.copy()
        painter.setCompositionMode(mode.CompositionMode_Overlay)
        painter.setOpacity(min(1.0, contrast))
        painter.drawImage(0, 0, copy)
    elif contrast < 0:
        painter.setCompositionMode(mode.CompositionMode_SourceAtop)
        painter.setOpacity(min(1.0, -contrast) * 0.8)
        painter.fillRect(out.rect(), QtGui.QColor(128, 128, 128))
    if bright:
        painter.setCompositionMode(mode.CompositionMode_SourceAtop)
        painter.setOpacity(min(1.0, abs(bright)) * 0.8)
        wash = QtGui.QColor(255, 255, 255) if bright > 0 else QtGui.QColor(0, 0, 0)
        painter.fillRect(out.rect(), wash)
    painter.end()
    return out


# How many adjusted photos the cache keeps.
_LOOK_CACHE = 12


def print_image(printer: QtGui.QPagedPaintDevice, image: QtGui.QImage) -> bool:
    """Draws image as large as fits on the printer's page (inside its
    margins), keeping its shape, centred."""
    if image is None or image.isNull():
        return False
    from gremlin.ui.util import paint_fitted

    painter = QtGui.QPainter()
    if not painter.begin(printer):
        return False
    paint_fitted(painter, image)
    return painter.end()


def _template_stem(name: str) -> str:
    """A template's file name: its name, with characters files cannot hold
    replaced."""
    text = str(name or "").strip()
    stem = "".join(c if c.isalnum() or c in " -_" else "_" for c in text).strip()
    return stem[:80]


def _read_template(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("nodes"), list):
        return None
    if not doc["nodes"]:
        return None
    return doc


def _is_hex_colour(value: object) -> bool:
    text = str(value or "")
    return (
        len(text) == 7
        and text.startswith("#")
        and all(ch in "0123456789abcdefABCDEF" for ch in text[1:])
    )


def _as_urls(items: object) -> list[QtCore.QUrl]:
    """Dropped or chosen URLs as QUrls. A drag from QML arrives as QUrl
    objects, whose str() is their repr ("PySide6.QtCore.QUrl('file:…')"),
    not the address: only text is turned into a QUrl."""
    if hasattr(items, "toVariant"):  # a JavaScript array (QJSValue)
        items = items.toVariant()  # type: ignore[union-attr]
    found = list(items) if isinstance(items, (list, tuple)) else []
    return [u if isinstance(u, QtCore.QUrl) else QtCore.QUrl(str(u)) for u in found]


def _image_files(urls: list[QtCore.QUrl]) -> list[Path]:
    """The local picture files among these URLs, in order."""
    out: list[Path] = []
    for url in urls:
        if not url.isLocalFile():
            continue
        path = Path(url.toLocalFile())
        if path.suffix.lower() in _IMAGE_EXT and path.is_file():
            out.append(path)
    return out


def _clipboard() -> QtGui.QClipboard | None:
    app = QtGui.QGuiApplication.instance()
    return app.clipboard() if isinstance(app, QtGui.QGuiApplication) else None


def _install_root() -> Path:
    return Path(os.path.normcase(os.path.dirname(os.path.abspath(sys.argv[0]))))


def _maps_dir() -> Path:
    from gremlin.util import modules_dir

    return modules_dir()


def _asset_ref(slug: str, name: str) -> str:
    """Picture path stored in a device file, relative to the modules folder."""
    return f"{slug}/{name}"


def _module_relative(stored: str) -> str:
    text = stored.replace("\\", "/").lstrip("/")
    marker = "qml/maps/"
    if text.lower().startswith(marker):
        return text[len(marker):]
    return text




def _slug(device_name: str) -> str:
    return plain_slug(device_name) or "device"


def guid_for_module(device_name: str, guid: str) -> str:
    """Use guid only when it belongs to device_name. A stale id must not select another module."""
    given = stored_guid_key(guid)
    if not given:
        return ""
    # Another connected device of that name may own it (twin sticks).
    owned = _guid_for_name(device_name)
    if owned and owned != given and not device_has_name(given, device_name):
        return ""
    return str(guid)


def _write_bindings(data: dict[str, str]) -> None:
    from gremlin.config import Configuration

    _binding_store()
    Configuration().set("global", "internal", "module-file-bindings", json.dumps(data))


def module_json_path(device_name: str, guid: str = "") -> Path:
    """The module file for this device.

    A binding may be used only when that file belongs to this device. A vJoy
    save must not write another vJoy's module file.
    """
    own = _slug(device_name)
    own_path = _maps_dir() / f"{own}.json"
    slug = resolve_module_slug(device_name, guid_for_module(device_name, guid))
    if not slug or slug == own:
        return own_path
    bound = _maps_dir() / f"{slug}.json"
    if not bound.is_file():
        return bound
    try:
        doc = json.loads(bound.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return own_path
    if not isinstance(doc, dict):
        return own_path
    named = str(doc.get("device") or "").strip().lower()
    this = str(device_name or "").strip().lower()
    if named and named == this:
        return bound
    key = stored_guid_key(guid)
    if key and stored_guid_key(doc.get("boundGuidLocal")) == key:
        return bound
    return own_path


def module_file_choices(device_name: str, guid: str = "") -> list[str]:
    """Files in the import folder. Live module files are not listed."""
    del device_name, guid
    imported = _maps_dir() / "imported"
    if not imported.is_dir():
        return []
    return [
        f"imported/{path.stem}"
        for path in sorted(imported.glob("*.json"))
        if path.is_file()
    ]


def foreign_module_file(device_name: str, guid: str = "") -> str:
    """A binding that still points this device at some other file."""
    bound = resolve_module_slug(device_name, guid)
    own = _slug(device_name)
    if bound and bound != own:
        return bound
    return ""


def _hid(node: dict) -> int | None:
    try:
        number = int(node.get("hwId"))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _infer_direction(doc: dict, path: Path) -> str:
    del doc
    if path.stem.lower().startswith("vjoy"):
        return "dest"
    return "source"


def member_kind(node: dict, member: dict) -> str:
    """Kind of one chip in a group: its own kind when saved, otherwise from the
    group (an axis stack holds axes, any other group buttons)."""
    own = str(member.get("kind") or "").strip().lower()
    if own in ("axis", "hat"):
        return own
    if own in ("btn", "button"):
        return "btn"
    return "axis" if str(node.get("kind") or "") == "axis_stack" else "btn"


def _filter_nodes(nodes: list, buttons: set[int], axes: set[int], hats: set[int], keys: set[int]) -> list:
    kept: list = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "")
        if kind in ("stack", "axis_stack"):
            members = []
            for member in node.get("members") or []:
                if not isinstance(member, dict):
                    continue
                by_kind = {"axis": axes, "hat": hats}
                want = by_kind.get(member_kind(node, member), buttons)
                hid = _hid(member)
                if hid is not None and hid not in want:
                    continue
                members.append(member)
            if not members:
                continue
            copied = dict(node)
            copied["members"] = members
            kept.append(copied)
            continue
        hid = _hid(node)
        if kind in ("btn", "button"):
            if hid in buttons:
                kept.append(node)
            continue
        if kind == "axis":
            if hid in axes:
                kept.append(node)
            continue
        if kind == "hat":
            if hid in hats:
                kept.append(node)
            continue
        if kind == "key":
            if hid in keys:
                kept.append(node)
            continue
        if hid is None:
            kept.append(node)
    return kept


def _filter_friendly(friendly: dict, buttons: set[int], axes: set[int], hats: set[int], keys: set[int]) -> dict:
    pools = {"button": buttons, "axis": axes, "hat": hats, "key": keys}
    out = {}
    for key, value in friendly.items():
        kind, _, raw = str(key).partition(":")
        try:
            hid = int(raw)
        except ValueError:
            continue
        if hid in pools.get(kind, ()):
            out[str(key)] = value
    return out


def _left_out_text(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return f" {labels[0]} was not copied. This device does not have {labels[0]}."
    listed = ", ".join(labels[:-1]) + " and " + labels[-1]
    return f" {listed} were not copied. This device does not have them."


def _connected_input_ids(guid: str) -> tuple[set[int], set[int], set[int]] | None:
    if not str(guid or "").strip():
        return None
    try:
        info = hardware.device_info(guid)
    except Exception:
        info = None
    if info is None:
        return None
    buttons, axes, hats = _device_input_ids(guid)
    return set(buttons), set(axes), set(hats)


def prepare_imported_doc(
    doc: dict,
    device_name: str,
    guid: str,
    direction: str,
    buttons: set[int],
    axes: set[int],
    hats: set[int],
    *,
    keep_keys: bool,
    previous_image: str = "",
) -> tuple[dict, str]:
    """Copy a module onto this device. The returned document is the copy."""
    claim = doc.get("claim") if isinstance(doc.get("claim"), dict) else {}
    keys = set()
    if keep_keys:
        for item in claim.get("keys") or []:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue
            if number > 0:
                keys.add(number)
    source_buttons = set(claim_ids(claim, "button"))
    source_axes = set(claim_ids(claim, "axis"))
    source_hats = set(claim_ids(claim, "hat"))
    source_keys = set()
    for item in claim.get("keys") or []:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number > 0:
            source_keys.add(number)
    kept_buttons = source_buttons & buttons
    kept_axes = source_axes & axes
    kept_hats = source_hats & hats
    kept_keys = source_keys & keys
    payload = json.loads(json.dumps(doc))
    payload["kind"] = "control.hardware"
    payload["device"] = device_name
    payload["direction"] = "dest" if direction == "dest" else "source"
    if guid:
        payload["boundName"] = device_name
        payload["boundGuidLocal"] = guid
    else:
        payload.pop("boundGuidLocal", None)
        payload.pop("boundName", None)
    payload["claim"] = {
        "buttons": sorted(kept_buttons),
        "axes": sorted(kept_axes),
        "hats": sorted(kept_hats),
        "keys": sorted(kept_keys),
        "friendly": _filter_friendly(
            claim.get("friendly") if isinstance(claim.get("friendly"), dict) else {},
            kept_buttons,
            kept_axes,
            kept_hats,
            kept_keys,
        ),
    }
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    payload["nodes"] = _filter_nodes(nodes, kept_buttons, kept_axes, kept_hats, kept_keys)
    calibration = payload.get("calibration")
    if isinstance(calibration, dict):
        kept_cal = {}
        for key, value in calibration.items():
            try:
                number = int(key)
            except (TypeError, ValueError):
                continue
            if number in kept_axes:
                kept_cal[str(int(number))] = value
        payload["calibration"] = kept_cal
    view = payload.get("view")
    if isinstance(view, dict) and isinstance(view.get("meters"), list):
        meters = []
        for item in view["meters"]:
            try:
                number = int(item)
            except (TypeError, ValueError):
                meters.append(item)
                continue
            if number == 0 or number in kept_axes:
                meters.append(item)
        view = dict(view)
        view["meters"] = meters
        payload["view"] = view
    if previous_image:
        payload["image"] = previous_image
    else:
        payload.pop("image", None)
    left = []
    left.extend(f"Button {number}" for number in sorted(source_buttons - kept_buttons))
    left.extend(f"Axis {number}" for number in sorted(source_axes - kept_axes))
    left.extend(f"Hat {number}" for number in sorted(source_hats - kept_hats))
    left.extend(f"Key {number}" for number in sorted(source_keys - kept_keys))
    return payload, _left_out_text(left)


def _resolve_import_source(file_name: str) -> Path | None:
    raw = str(file_name or "").strip()
    if not raw:
        return None
    if "://" in raw or raw.lower().startswith("file:"):
        try:
            src = to_local_path(raw)
        except Exception:
            return None
        return src if src and Path(src).is_file() else None
    direct = Path(raw)
    if direct.is_file():
        return direct
    rel = raw.replace("\\", "/")
    if rel.lower().endswith(".json"):
        rel = rel[:-5]
    if rel.lower().startswith("imported/"):
        path = _maps_dir() / "imported" / f"{Path(rel).name}.json"
        return path if path.is_file() else None
    path = _maps_dir() / f"{plain_slug(rel)}.json"
    return path if path.is_file() else None


def _archive_stamp(moment: datetime | None = None) -> str:
    """Year, day, month, then hour, minute, and second. Local time."""
    moment = moment or datetime.now()
    month = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")[moment.month - 1]
    return f"{moment.year:04d}-{moment.day:02d}-{month}_{moment.hour:02d}_{moment.minute:02d}_{moment.second:02d}"


def _archive_path(stem: str, stamp: str) -> Path:
    return _maps_dir() / "imported" / f"{stem}.{stamp}.json"


def _replace_file(path: Path, data: bytes) -> None:
    """Write a temporary file, then replace the live file only if that write finishes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Tools > History, as module_file.write_text does (import, Device Pack).
    from gremlin import history_modules

    old = history_modules.text_before(path)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    except OSError:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
        raise
    # After the write: a write that failed is no History entry.
    try:
        history_modules.note_write(path, data.decode("utf-8"), old)
    except UnicodeDecodeError:
        pass


def _clear_bindings_to(slug: str) -> None:
    data = _binding_store()
    want = plain_slug(slug)
    keys = [key for key, value in data.items() if plain_slug(value) == want]
    if not keys:
        return
    for key in keys:
        data.pop(key, None)
    _write_bindings(data)


def _count_phrase(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _copied_sentence(buttons: int, axes: int, hats: int, keys: int) -> str:
    parts = []
    if buttons:
        parts.append(_count_phrase(buttons, "button", "buttons"))
    if axes:
        parts.append(_count_phrase(axes, "axis", "axes"))
    if hats:
        parts.append(_count_phrase(hats, "hat", "hats"))
    if keys:
        parts.append(_count_phrase(keys, "key", "keys"))
    if not parts:
        return "No buttons, axes, or hats were copied."
    if len(parts) == 1:
        return f"Copied {parts[0]}."
    return "Copied " + ", ".join(parts[:-1]) + ", and " + parts[-1] + "."


_import_undo: dict | None = None


def import_can_undo() -> bool:
    return _import_undo is not None


def drop_import_undo() -> None:
    global _import_undo
    _import_undo = None


def undo_last_import() -> str:
    """Put this device's previous file back. The chosen file is not touched."""
    global _import_undo
    record = _import_undo
    if not record:
        return "Undo failed. There is nothing to undo."
    dest = Path(record["dest"])
    previous = record.get("previous")
    try:
        if previous is None:
            if dest.is_file():
                from gremlin import history_modules

                history_modules.note_delete(dest)
                dest.unlink()
            note = "The new module file was removed."
        else:
            _replace_file(dest, previous)
            note = "The previous module file was put back."
            trace("SAVE", "Configure Module", "undo_last_import", dest, "ok")
    except OSError:
        return "Undo failed. The previous module file could not be put back."
    # The devices the import unbound from that file are bound again.
    if record.get("bindings") is not None:
        _write_bindings(record["bindings"])
    _import_undo = None
    return "Undone. " + note


def import_module_file(device_name: str, guid: str, file_name: str, direction: str = "source") -> str:
    """Copy a module file onto this device's own file. Archives happen only after that write."""
    global _import_undo
    name = str(device_name or "").strip()
    if not name:
        return "That file could not be read."
    src = _resolve_import_source(file_name)
    if src is None or not src.is_file():
        return "That file could not be read."
    own_slug = _slug(name)
    dest = _maps_dir() / f"{own_slug}.json"
    try:
        if src.resolve() == dest.resolve():
            return "That file is already this device's file."
    except OSError:
        return "That file could not be read."
    try:
        doc = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        trace("READ", "Configure Module", "import_module_file", src, "error")
        return "That file could not be read."
    trace("READ", "Configure Module", "import_module_file", src, "ok")
    if not isinstance(doc, dict) or doc.get("kind") != "control.hardware":
        return "That file is not a module file."
    target = "dest" if str(direction or "").strip().lower() == "dest" else "source"
    source_direction = _infer_direction(doc, src)
    if target == "source" and source_direction == "dest":
        return "A vJoy file cannot be copied onto a stick."
    if target == "dest" and source_direction == "source":
        return "A stick file cannot be copied onto a vJoy."
    keyboard = name.lower() == "keyboard"
    if keyboard:
        limits = (set(), set(), set())
    else:
        limits = _connected_input_ids(guid)
        if limits is None:
            return "This device is not connected, so the file cannot be checked."
    buttons, axes, hats = limits
    previous_image = ""
    previous_bytes: bytes | None = None
    if dest.is_file():
        try:
            previous_bytes = dest.read_bytes()
            previous = json.loads(previous_bytes.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            trace("READ", "Configure Module", "import_module_file", dest, "error")
            return "The current file could not be read, so it was not replaced."
        if isinstance(previous, dict):
            previous_image = str(previous.get("image") or "")
    payload, left = prepare_imported_doc(
        doc,
        name,
        str(guid or ""),
        target,
        buttons,
        axes,
        hats,
        keep_keys=keyboard,
        previous_image=previous_image,
    )
    try:
        _replace_file(dest, (json.dumps(payload, indent=2) + "\n").encode("utf-8"))
    except OSError:
        trace("SAVE", "Configure Module", "import_module_file", dest, "error")
        return "The module file could not be written."
    trace("SAVE", "Configure Module", "import_module_file", dest, "ok")
    claim = payload.get("claim") if isinstance(payload.get("claim"), dict) else {}
    friendly = claim.get("friendly") if isinstance(claim.get("friendly"), dict) else {}
    stamp = _archive_stamp()
    lines = [
        f"Imported into {own_slug}.json.",
        _copied_sentence(
            len(claim.get("buttons") or []),
            len(claim.get("axes") or []),
            len(claim.get("hats") or []),
            len(claim.get("keys") or []),
        ),
    ]
    if friendly:
        lines.append(_count_phrase(len(friendly), "name was copied.", "names were copied."))
    if left.strip():
        lines.append(left.strip())
    else:
        lines.append("Everything in the file was copied.")
    if previous_image:
        lines.append("The picture already on this device was kept.")
    else:
        lines.append("No picture was added from the chosen file.")
    lines.append("Profile wires were not changed.")
    lines.append("The chosen file was left where it was.")
    if previous_bytes is not None:
        backup = _archive_path(own_slug, stamp)
        try:
            if backup.exists():
                raise FileExistsError(backup)
            _replace_file(backup, previous_bytes)
            lines.append("The previous file was saved as")
            lines.append(backup.name.replace("-", "\u2011"))
        except OSError:
            lines.append("The previous file could not be saved to imported.")
    bindings = _binding_store()
    _clear_bindings_to(src.stem)
    _clear_device_binding(name, str(guid or ""))
    _import_undo = {
        "dest": str(dest),
        "previous": previous_bytes,
        "bindings": bindings,
    }
    persist_log(f"Persist import file name={name!r} guid={guid!r} src={src} dest={dest}")
    return "\n".join(lines)


def _clear_device_binding(device_name: str, guid: str) -> None:
    data = _binding_store()
    key = stored_guid_key(guid) or _guid_for_name(device_name)
    name_key = _name_key(device_name)
    changed = False
    if key and key in data:
        data.pop(key, None)
        changed = True
    if name_key and name_key in data:
        data.pop(name_key, None)
        changed = True
    if changed:
        _write_bindings(data)


def bind_module_file(device_name: str, guid: str, file_name: str) -> str:
    slug = plain_slug(file_name)
    key = stored_guid_key(guid) or _guid_for_name(device_name)
    if not slug or not key:
        return ""
    data = _binding_store()
    data[key] = slug
    name_key = _name_key(device_name)
    if name_key:
        data[name_key] = slug
    _write_bindings(data)
    persist_log(f"Persist bind file name={device_name!r} guid={guid!r} slug={slug!r}")
    return slug


def _live_devices() -> list:
    try:
        from gremlin import device_initialization
        devices = list(device_initialization.physical_devices() or [])
        devices.extend(device_initialization.vjoy_devices() or [])
        return devices
    except Exception:
        return []


def _users_of_slug(slug: str) -> set[str]:
    users: set[str] = set()
    for key, value in _binding_store().items():
        if plain_slug(value) == slug:
            users.add(key)
    for dev in _live_devices():
        guid = stored_guid_key(getattr(dev, "device_guid", ""))
        name = str(getattr(dev, "name", "") or "")
        if guid and name and resolve_module_slug(name, guid) == slug:
            users.add(guid)
    return users


def delete_module_file(device_name: str, guid: str) -> str:
    """Delete this device's own file. Do not delete, or unhook, a different file."""
    slug = _slug(device_name)
    key = stored_guid_key(guid) or _guid_for_name(device_name)
    others = _users_of_slug(slug) - ({key} if key else set())
    name_key = _name_key(device_name)
    others.discard(name_key)
    if others:
        return "Another stick is using this file."
    path = _maps_dir() / f"{slug}.json"
    if path.is_file():
        # The file holds claims, calibration and the Button Map layout: keep
        # a copy in the deleted devices folder, or do not delete it.
        kept = _keep_deleted_copy(path)
        if kept is None:
            return "Could not keep a copy of the module file, so it was not deleted."
        from gremlin import history_modules

        history_modules.note_delete(path)
        path.unlink()
        trace(
            "SAVE", "Configure Module", "delete_module_file", path,
            f"removed, copy at {kept}",
        )
    data = _binding_store()
    changed = False
    if key and plain_slug(str(data.get(key, ""))) == slug:
        data.pop(key, None)
        changed = True
    if name_key and plain_slug(str(data.get(name_key, ""))) == slug:
        data.pop(name_key, None)
        changed = True
    if changed:
        _write_bindings(data)
    return ""


def _deleted_dir() -> Path:
    from gremlin.util import deleted_devices_dir

    return deleted_devices_dir()


def _keep_deleted_copy(path: Path) -> Path | None:
    """Copy a module file about to be deleted into the deleted devices folder
    as "<name> <date time>.json", so it can be imported back. None when the
    copy could not be made."""
    try:
        folder = _deleted_dir()
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
        dest = folder / f"{path.stem} {stamp}.json"
        shutil.copy2(path, dest)
        return dest
    except OSError:
        return None


def _pack_file_name(device_name: str) -> str:
    raw = " ".join(str(device_name or "").split()) or "device"
    cleaned = []
    for ch in raw:
        if ch in '<>:"/\\|?*' or ord(ch) < 32:
            cleaned.append(" ")
        else:
            cleaned.append(ch)
    name = " ".join("".join(cleaned).split()).strip(" .")
    return name or "device"


def _deleted_pack_path(device_name: str) -> Path:
    """One folder per Windows device name. Every pack uses the agreed stamp."""
    base = _pack_file_name(device_name)
    folder = _deleted_dir() / base
    folder.mkdir(parents=True, exist_ok=True)
    stamp = _archive_stamp()
    return folder / f"{base}.{stamp}.zip"


def _zip_readable(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "map.json" not in zf.namelist():
                return False
            doc = json.loads(zf.read("map.json").decode("utf-8"))
        return isinstance(doc, dict)
    except Exception:
        return False


def _active_module_path(device_name: str, guid: str) -> Path:
    slug = resolve_module_slug(device_name, guid_for_module(device_name, guid))
    return _maps_dir() / f"{(slug or _slug(device_name))}.json"




def _own_file_shared(device_name: str, guid: str) -> bool:
    own = _slug(device_name)
    if not (_maps_dir() / f"{own}.json").is_file():
        return False
    key = stored_guid_key(guid) or _guid_for_name(device_name)
    others = _users_of_slug(own) - ({key} if key else set())
    others.discard(_name_key(device_name))
    return bool(others)


def _device_stays_listed(device_name: str) -> bool:
    wanted = " ".join(str(device_name or "").split()).lower()
    if wanted in {"keyboard", "osc", "xbox 360 controller", "logical device"}:
        return True
    if wanted.startswith("vjoy "):
        return True
    try:
        from gremlin import device_initialization

        for dev in list(device_initialization.physical_devices() or []):
            if str(getattr(dev, "name", "") or "").strip().lower() == wanted:
                return True
        for dev in list(device_initialization.vjoy_devices() or []):
            label = f"vjoy {getattr(dev, 'vjoy_id', '')}".strip().lower()
            if label == wanted:
                return True
    except Exception:
        return False
    return False


def delete_preview(device_name: str, guid: str) -> str:
    name = " ".join(str(device_name or "").split())
    path = _active_module_path(name, guid)
    return json.dumps({
        "name": name,
        "canPack": path.is_file(),
        "shared": _own_file_shared(name, guid),
        "foreign": bool(foreign_module_file(name, guid)),
        "listed": _device_stays_listed(name),
        "keepModule": is_output_name(name),
    })


def _drop_binding_tree(profile, binding) -> None:
    root = getattr(binding, "root_action", None)
    if root is None or not profile.library.has_action(getattr(root, "id", None)):
        return
    try:
        profile.library.remove_unused(root, True)
    except Exception:
        pass


def _drop_inputs(profile, uid) -> None:
    items = list(profile.inputs.pop(uid, []) or [])
    for item in items:
        for binding in list(getattr(item, "action_sequences", None) or []):
            _drop_binding_tree(profile, binding)


def _prune_empty_inputs(profile) -> None:
    empty = []
    for key, items in list(profile.inputs.items()):
        kept = [item for item in items if getattr(item, "action_sequences", None)]
        if kept:
            profile.inputs[key] = kept
        else:
            empty.append(key)
    for key in empty:
        profile.inputs.pop(key, None)


def _save_profile_wires(device_name: str, guid: str) -> str:
    from gremlin.shared_state import current_profile
    from gremlin.ui.input_pairing import _guid

    profile = current_profile
    if profile is None:
        return ""
    text = str(guid or "").strip() or _guid_for_name(device_name)
    uid = _guid(text)
    if uid is not None:
        _drop_inputs(profile, uid)
    _prune_empty_inputs(profile)
    path = getattr(profile, "fpath", None)
    if path:
        try:
            profile.to_xml(path)
        except Exception as exc:
            signal.profileChanged.emit()
            return (
                "The profile could not be saved, so the module file was kept. "
                "Reload the profile to bring the wires back. "
                f"{exc}"
            )
    signal.profileChanged.emit()
    return ""


def _clear_device_binding_keys(device_name: str, guid: str) -> None:
    data = _binding_store()
    key = stored_guid_key(guid) or _guid_for_name(device_name)
    name_key = _name_key(device_name)
    changed = False
    if key and key in data:
        data.pop(key, None)
        changed = True
    if name_key and name_key in data:
        data.pop(name_key, None)
        changed = True
    if changed:
        _write_bindings(data)


def _delete_own_module_files(device_name: str) -> str:
    slug = _slug(device_name)
    try:
        path = _maps_dir() / f"{slug}.json"
        if path.is_file():
            from gremlin import history_modules

            history_modules.note_delete(path)
            path.unlink()
            trace("SAVE", "Delete Device", "_delete_own_module_files", path, "removed")
        folder = _maps_dir() / slug
        if folder.is_dir():
            shutil.rmtree(folder)
            trace("SAVE", "Delete Device", "_delete_own_module_files", folder, "removed")
        for extra in _maps_dir().glob(f"{slug}_photo.*"):
            if extra.is_file():
                extra.unlink()
                trace("SAVE", "Delete Device", "_delete_own_module_files", extra, "removed")
    except OSError as exc:
        return str(exc)
    return ""


def delete_device(device_name: str, guid: str, save_copy: bool) -> str:
    """Archive this device when asked, then remove its live module and wires."""
    from gremlin.shared_state import current_profile

    name = " ".join(str(device_name or "").split())
    if not name:
        return json.dumps({"ok": False, "error": "Choose a device."})
    pack_path = ""
    if save_copy:
        if not _active_module_path(name, guid).is_file():
            return json.dumps({
                "ok": False,
                "error": "This device has no module file, so a pack cannot be saved.",
            })
        from gremlin.ui.device_pack import assemble

        built = assemble(name, HardwareProfile()._resolve_existing)
        if isinstance(built, str):
            return json.dumps({"ok": False, "error": built})
        data, _info = built
        dest = _deleted_pack_path(name)
        try:
            dest.write_bytes(data)
        except OSError as exc:
            trace("SAVE", "Delete Device", "delete_device", dest, "error")
            return json.dumps({"ok": False, "error": f"The pack could not be written. {exc}"})
        trace("SAVE", "Delete Device", "delete_device", dest, "ok")
        if not _zip_readable(dest):
            try:
                dest.unlink()
            except OSError:
                pass
            return json.dumps({
                "ok": False,
                "error": "The pack could not be read back, so the device was not deleted.",
            })
        pack_path = str(dest)
    wire_error = _save_profile_wires(name, guid)
    if wire_error:
        if pack_path:
            try:
                Path(pack_path).unlink()
            except OSError:
                pass
        return json.dumps({"ok": False, "error": wire_error})
    shared = _own_file_shared(name, guid)
    protected = is_output_name(name)
    file_error = ""
    if not shared and not protected:
        file_error = _delete_own_module_files(name)
    _clear_device_binding_keys(name, guid)
    own_left = (_maps_dir() / f"{_slug(name)}.json").is_file()
    profile = current_profile
    if profile is None:
        saved = True
    else:
        saved = bool(getattr(profile, "fpath", None))
    if file_error and own_left:
        return json.dumps({
            "ok": False,
            "error": (
                "The wires were removed, but the module file could not be deleted. "
                f"{file_error}"
            ),
            "packPath": pack_path,
        })
    listed = _device_stays_listed(name)
    return json.dumps({
        "ok": True,
        "name": name,
        "packPath": pack_path,
        "keptFile": bool((shared or protected) and own_left),
        "keepModule": protected,
        "stub": listed and not own_left,
        "listed": listed,
        "profileSaved": saved,
    })


def maps_folder_url() -> str:
    return _maps_dir().as_uri()


def imported_folder_url() -> str:
    path = _maps_dir() / "imported"
    path.mkdir(parents=True, exist_ok=True)
    return path.as_uri()


def _stock_photo() -> Path:
    return _install_root() / "qml" / "images" / "vkb_gladiator_rig.jpg"


def _stock_photo_l() -> Path:
    return _install_root() / "qml" / "images" / "vkb_gladiator_evo_l.jpg"


def _safe_name(name: str, fallback: str = "image.jpg") -> str:
    raw = Path(name or "").name
    if not raw:
        return fallback
    keep = []
    for ch in raw:
        if ch.isalnum() or ch in "._-":
            keep.append(ch)
        else:
            keep.append("_")
    out = "".join(keep).strip("._") or fallback
    if Path(out).suffix.lower() not in _IMAGE_EXT:
        out = out + Path(fallback).suffix
    return out


def _guid_text(value: object) -> str:
    raw = getattr(value, "uuid", value)
    text = str(raw or "").strip()
    if text.lower() in ("", "none"):
        return ""
    return text


def _collapsed_name(value: str) -> str:
    return " ".join(str(value or "").split()).lower()


def _doc_direction(doc: dict, exported_name: str) -> str:
    label = doc.get("pack") if isinstance(doc.get("pack"), dict) else {}
    named = str(doc.get("device") or label.get("exportedName") or exported_name or "")
    if is_output_name(named):
        return "dest"
    raw = str(doc.get("direction") or "").strip().lower()
    if raw in ("source", "dest"):
        return raw
    return "dest" if is_output_name(exported_name) else "source"


def _read_json_dict(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except ValueError as exc:
        # A damaged file (bad text or not UTF-8) is skipped and named; it
        # used to stop the whole Device Pack window.
        import logging

        logging.getLogger("system").warning(f"Skipped damaged file {path}: {exc}")
        return None
    return doc if isinstance(doc, dict) else None


def _claim_summary(doc: dict) -> dict:
    claim = doc.get("claim") if isinstance(doc.get("claim"), dict) else {}
    nodes = [node for node in (doc.get("nodes") or []) if isinstance(node, dict)]
    image = str(doc.get("image") or "").strip()
    return {
        "buttons": len(claim_ids(claim, "button")),
        "axes": len(claim_ids(claim, "axis")),
        "hats": len(claim_ids(claim, "hat")),
        "nodes": len(nodes),
        "hasPhoto": bool(image),
        "hasMap": bool(nodes),
    }


def _known_pack_devices() -> list[dict]:
    """Connected devices, devices this profile has seen, and saved module files."""
    rows: dict[str, dict] = {}

    def touch(name: str, guid: str = "", connected: bool = False) -> None:
        label = " ".join(str(name or "").split())
        key = label.lower()
        if not key:
            return
        slug = _slug(label)
        path = _maps_dir() / f"{slug}.json"
        row = rows.get(key)
        if row is None:
            rows[key] = {
                "name": label,
                "guid": guid,
                "connected": bool(connected),
                "hasFile": path.is_file(),
                "fileName": f"{slug}.json",
            }
            return
        if guid and not row["guid"]:
            row["guid"] = guid
        if connected:
            row["connected"] = True
        if path.is_file():
            row["hasFile"] = True

    for dev in _live_devices():
        touch(
            str(getattr(dev, "name", "") or ""),
            _guid_text(getattr(dev, "device_guid", "")),
            True,
        )
    try:
        from gremlin.shared_state import current_profile
        profile = current_profile
        if profile is not None:
            for info in profile.device_database.devices.values():
                touch(str(info.name or ""), _guid_text(info.device_uuid), False)
    except Exception:
        pass
    for path in sorted(_maps_dir().glob("*.json")):
        doc = _read_json_dict(path)
        if not doc or doc.get("kind") != "control.hardware":
            continue
        touch(str(doc.get("device") or "").strip() or path.stem, "", False)
    return sorted(rows.values(), key=lambda row: row["name"].lower())


def _match_pack_device(name: str) -> dict | None:
    want = _collapsed_name(name)
    if not want:
        return None
    for row in _known_pack_devices():
        if _collapsed_name(row["name"]) == want:
            return row
    return None


def _suggest_pack_name(exported: str, devices: list[dict] | None = None) -> str:
    want = _collapsed_name(exported)
    if not want:
        return ""
    hits = [
        row["name"]
        for row in (devices if devices is not None else _known_pack_devices())
        if _collapsed_name(row["name"]) == want
    ]
    if len(hits) == 1:
        return hits[0]
    return ""


def _target_direction(name: str) -> str:
    if is_output_name(name):
        return "dest"
    path = _maps_dir() / f"{_slug(name)}.json"
    doc = _read_json_dict(path) if path.is_file() else None
    if doc and str(doc.get("direction") or "").strip().lower() == "dest":
        return "dest"
    return "source"


def _unique_archive(stem: str) -> Path:
    stamp = _archive_stamp()
    path = _archive_path(stem, stamp)
    number = 2
    while path.exists():
        path = _maps_dir() / "imported" / f"{stem}.{stamp}_{number}.json"
        number += 1
    return path


def _export_dir() -> Path:
    from gremlin.util import export_dir

    return export_dir()


def _outside_maps(path: Path) -> bool:
    try:
        path.resolve().relative_to(_maps_dir().resolve())
    except ValueError:
        return True
    return False


def _device_input_ids(guid: str) -> tuple[list[int], list[int], list[int]]:
    buttons: list[int] = []
    axes: list[int] = []
    hats: list[int] = []
    try:
        info = hardware.device_info(guid)
    except Exception:
        info = None
    if info is None:
        return buttons, axes, hats
    try:
        button_count = int(getattr(info, "button_count", 0) or 0)
    except (TypeError, ValueError):
        button_count = 0
    buttons = list(range(1, button_count + 1))
    try:
        hat_count = int(getattr(info, "hat_count", 0) or 0)
    except (TypeError, ValueError):
        hat_count = 0
    hats = list(range(1, hat_count + 1))
    for entry in getattr(info, "axis_map", None) or []:
        index = getattr(entry, "axis_index", None)
        if index is None and isinstance(entry, dict):
            index = entry.get("axis_index")
        try:
            number = int(index)
        except (TypeError, ValueError):
            continue
        if number > 0:
            axes.append(number)
    if not axes:
        try:
            axis_count = int(getattr(info, "axis_count", 0) or 0)
        except (TypeError, ValueError):
            axis_count = 0
        axes = list(range(1, axis_count + 1))
    return buttons, sorted(set(axes)), hats


def _profile_input_ids(guid: str) -> tuple[list[int], list[int], list[int]]:
    from gremlin.types import InputType
    from gremlin.ui import input_pairing as pairing

    buttons: list[int] = []
    axes: list[int] = []
    hats: list[int] = []
    for item in pairing._items_for_guid(guid):
        try:
            number = int(item.input_id)
        except (TypeError, ValueError):
            continue
        if number <= 0:
            continue
        kind = getattr(item, "input_type", None)
        if kind == InputType.JoystickAxis:
            axes.append(number)
        elif kind == InputType.JoystickHat:
            hats.append(number)
        elif kind == InputType.JoystickButton:
            buttons.append(number)
    return sorted(set(buttons)), sorted(set(axes)), sorted(set(hats))


def _output_labels(item) -> str:
    from gremlin.ui import input_pairing as pairing

    labels: list[str] = []
    seen: set[str] = set()

    def add(text: object) -> None:
        label = str(text or "").strip()
        if not label or label in seen:
            return
        seen.add(label)
        labels.append(label)

    for text in pairing._dest_labels_for_item(item):
        add(text)
    if item is None:
        return ""
    for seq in getattr(item, "action_sequences", []) or []:
        root = getattr(seq, "root_action", None)
        if root is None:
            continue
        for action in pairing._walk_actions(root):
            tag = str(getattr(action, "tag", "") or "")
            if tag in ("", "root", "map-to-vjoy", "map-to-xbox"):
                continue
            add(getattr(action, "name", "") or tag.replace("-", " "))
    return " + ".join(labels)


def _label_for(guid: str, kind: str, hw_id: int) -> str:
    from gremlin.types import InputType
    from gremlin.ui import input_pairing as pairing

    wanted = {
        "axis": InputType.JoystickAxis,
        "hat": InputType.JoystickHat,
    }.get(kind, InputType.JoystickButton)
    labels: list[str] = []
    for item in pairing._items_for_guid(guid):
        try:
            number = int(item.input_id)
        except (TypeError, ValueError):
            continue
        if number != hw_id or getattr(item, "input_type", None) != wanted:
            continue
        text = _output_labels(item)
        if text:
            labels.append(text)
    return " + ".join(labels)


def chips_for_guid(guid: str) -> list[dict]:
    """One chip per input this device's module reports, labeled from its outputs."""
    text = str(guid or "").strip()
    if not text:
        return []
    from gremlin.ui import input_pairing as pairing
    from gremlin.ui.module_model import _load_module_doc

    name = pairing._device_name(text)
    doc = _load_module_doc(name, text) if name else {}
    claim = doc.get("claim") if isinstance(doc, dict) and isinstance(doc.get("claim"), dict) else {}
    reported = _device_input_ids(text)
    stored = _profile_input_ids(text)
    groups = (
        ("btn", claim_ids(claim, "button"), reported[0], stored[0]),
        ("axis", claim_ids(claim, "axis"), reported[1], stored[1]),
        ("hat", claim_ids(claim, "hat"), reported[2], stored[2]),
    )
    rows: list[dict] = []
    for kind, claimed, live, saved in groups:
        ids = claimed or live or saved
        for hw_id in ids:
            rows.append({
                "kind": kind,
                "hwId": int(hw_id),
                "dest": _label_for(text, kind, int(hw_id)),
            })
    return rows


@ta.QmlElement
class HardwareProfile(QtCore.QObject):
    """Load / save a control.hardware JSON beside the Button Map."""

    documentChanged = QtCore.Signal()
    pathChanged = QtCore.Signal()
    imageChanged = QtCore.Signal()
    clipboardChanged = QtCore.Signal()
    recentColoursChanged = QtCore.Signal()
    # The profile's actions or modes changed: chip action labels are stale.
    profileLabelsChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._device_name = "VKBsim Gladiator EVO R"
        self._text = "{}"
        self._path = ""
        self._peek_photo = ""
        self._device_guid = ""
        # Counts clipboard changes, so Ctrl+V can tell a picture copied after
        # the last chip copy from an old one.
        self._clipboard_serial = 0
        clipboard = _clipboard()
        if clipboard is not None:
            clipboard.dataChanged.connect(self._clipboard_changed)
        signal.profileChanged.connect(self.profileLabelsChanged)
        signal.modesChanged.connect(self.profileLabelsChanged)

    @QtCore.Slot(str, str, bool, bool, result="QVariantMap")
    def actionLabels(
        self, guid: str, mode: str, prefer_description: bool, join_all: bool
    ) -> dict[str, str]:
        """What each control of a device does in a mode: {"btn:5": "Gear up"}."""
        from gremlin import shared_state
        from gremlin.ui.button_map_labels import action_labels

        return action_labels(
            shared_state.current_profile, guid, mode, prefer_description, join_all
        )

    @QtCore.Slot(result=list)
    def profileModes(self) -> list:
        """The loaded profile's modes, parents before their children."""
        from gremlin import shared_state
        from gremlin.ui.button_map_labels import mode_order

        return mode_order(shared_state.current_profile)

    @QtCore.Property(list, notify=recentColoursChanged)
    def recentColours(self) -> list:
        """Colours last applied in the editor, newest first (all devices)."""
        from gremlin.config import Configuration

        stored = Configuration().value(
            "global", "internal", "button-map-recent-colours"
        )
        return [str(c) for c in (stored or []) if _is_hex_colour(c)][:_recent_count()]

    @QtCore.Slot(str)
    def noteColour(self, hex_colour: str) -> None:
        """Puts a colour first in the recent colours (once, at most ten)."""
        from gremlin.config import Configuration

        colour = str(hex_colour or "").strip().upper()
        if not _is_hex_colour(colour):
            return
        recent = [c for c in self.recentColours if c.upper() != colour]
        recent = [colour, *recent][:_recent_count()]
        Configuration().set("global", "internal", "button-map-recent-colours", recent)
        self.recentColoursChanged.emit()

    @QtCore.Slot(QtCore.QObject, float, float, result=str)
    def colorAt(self, window: QtCore.QObject, x: float, y: float) -> str:
        """The colour on screen at a point of a window (the eyedropper)."""
        import shiboken6

        try:
            quick = window
            if not isinstance(quick, QtQuick.QQuickWindow):
                # A wrapper made before QtQuick loaded: view it as one.
                quick = shiboken6.wrapInstance(
                    shiboken6.getCppPointer(window)[0], QtQuick.QQuickWindow
                )
            # The red debug frame is not part of what the user picks from.
            from gremlin.ui.debug_mode import hidden_frames

            with hidden_frames(quick):
                image = quick.grabWindow()
        except Exception:
            return ""
        if image.isNull():
            return ""
        ratio = image.devicePixelRatio() or 1.0
        px = int(x * ratio)
        py = int(y * ratio)
        if not (0 <= px < image.width() and 0 <= py < image.height()):
            return ""
        return image.pixelColor(px, py).name().upper()

    @QtCore.Slot(QtGui.QImage, int, int, str, str, str, result=bool)
    def saveArea(
        self,
        image: QtGui.QImage,
        width: int,
        height: int,
        url: str,
        fmt: str,
        setup_json: str,
    ) -> bool:
        """Saves the print area (Print & Export): image is RigRenderer's
        picture of it, written at width x height pixels; setup_json the
        paper for a PDF."""
        return save_area(
            image, width, height, to_local_path(url), fmt, _setup(setup_json)
        )

    # --- printing (Print & Export > Print) ------------------------------------

    @QtCore.Slot(QtGui.QImage, int, int, str, str, result=bool)
    def printImage(
        self,
        image: QtGui.QImage,
        width: int,
        height: int,
        title: str,
        setup_json: str,
    ) -> bool:
        """Prints the print area: the printer dialog first (its paper,
        orientation and margins from Print & Export), then the area filling
        the space inside the margins. With no paper chosen it goes on the
        printer's own paper, turned to landscape when wider than tall."""
        from PySide6 import QtPrintSupport

        from gremlin.ui.util import page_layout

        page = exact_page(image, width, height)
        if page is None:
            return False
        printer = QtPrintSupport.QPrinter(
            QtPrintSupport.QPrinter.PrinterMode.HighResolution
        )
        printer.setDocName(title or "Button Map")
        layout = page_layout(_setup(setup_json))
        if layout is not None:
            printer.setPageLayout(layout)
        else:
            printer.setPageOrientation(
                QtGui.QPageLayout.Orientation.Landscape
                if page.width() > page.height()
                else QtGui.QPageLayout.Orientation.Portrait
            )
        dialog = QtPrintSupport.QPrintDialog(printer)
        dialog.setWindowTitle("Print Button Map")
        if dialog.exec() != QtPrintSupport.QPrintDialog.DialogCode.Accepted:
            return False
        return print_image(printer, page)

    def _clipboard_changed(self) -> None:
        self._clipboard_serial += 1
        self.clipboardChanged.emit()

    @QtCore.Property(int, notify=clipboardChanged)
    def clipboardSerial(self) -> int:
        return self._clipboard_serial

    @QtCore.Property(bool, notify=clipboardChanged)
    def clipboardHasImage(self) -> bool:
        """The clipboard holds a picture the Button Map can paste: picture
        data, or picture files copied in Explorer."""
        clipboard = _clipboard()
        data = clipboard.mimeData() if clipboard is not None else None
        if data is None:
            return False
        return data.hasImage() or bool(_image_files(data.urls()))

    @QtCore.Slot(str, result=list)
    def pasteClipboardPictures(self, device_name: str) -> list[str]:
        """The clipboard's pictures as layer pictures for the device: copied
        files first (each one), else the picture data. Stored paths."""
        clipboard = _clipboard()
        data = clipboard.mimeData() if clipboard is not None else None
        if data is None:
            return []
        files = _image_files(data.urls())
        if files:
            return self.importPictureFiles([f.as_uri() for f in files], device_name)
        image = clipboard.image() if clipboard is not None else QtGui.QImage()
        rel = self.savePastedImage(image, device_name)
        return [rel] if rel else []

    @QtCore.Slot(list, str, result=list)
    def importPictureFiles(self, urls: list, device_name: str) -> list[str]:
        """Copies dropped or pasted picture files in as layer pictures; skips
        anything that is not a picture file. Stored paths."""
        out: list[str] = []
        for path in _image_files(_as_urls(urls)):
            rel = self.copyOverlay(path.as_uri(), device_name)
            if rel:
                out.append(rel)
        return out

    @QtCore.Slot("QVariant", result=bool)
    def hasPictureFiles(self, urls: object) -> bool:
        """Some of these dropped URLs are picture files."""
        return bool(_image_files(_as_urls(urls)))

    @QtCore.Slot(str, result=float)
    def imageAspect(self, stored: str) -> float:
        """Width / height of a stored picture (1 when unknown)."""
        found = self._resolve_existing(stored)
        if not found:
            return 1.0
        size = QtGui.QImageReader(str(found)).size()
        if size.width() <= 0 or size.height() <= 0:
            return 1.0
        return size.width() / size.height()

    def savePastedImage(self, image: QtGui.QImage, device_name: str) -> str:
        """Writes a pasted picture to the device's folder (and the library) as
        pasted.png, pasted_1.png...; returns its stored path, or "" if none."""
        if image is None or image.isNull():
            return ""
        folder = self._profile_dir(device_name)
        dest = folder / "pasted.png"
        n = 1
        while dest.exists():
            dest = folder / f"pasted_{n}.png"
            n += 1
        if not image.save(str(dest), "PNG"):
            return ""
        self._into_library(dest)
        self.imageChanged.emit()
        return _asset_ref(folder.name, dest.name)

    def _guid_for_this_device(self, device_name: str) -> str:
        # The object remembers one device. Do not use that id for a different name.
        guid = stored_guid_key(self._device_guid)
        if not guid:
            return ""
        # Any connected device of that name with that id (the second of two
        # twin sticks has its own id: it used to get the first one's file).
        if not device_has_name(guid, device_name):
            return ""
        return str(self._device_guid)

    def _file_for(self, device_name: str) -> Path:
        slug = resolve_module_slug(device_name, self._guid_for_this_device(device_name))
        return _maps_dir() / f"{slug}.json"

    def _profile_dir(self, device_name: str) -> Path:
        slug = resolve_module_slug(device_name, self._guid_for_this_device(device_name))
        path = _maps_dir() / slug
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _library_dir(self) -> Path:
        path = _maps_dir() / "library"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _copy_file(self, src: Path, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.resolve() != src.resolve():
            shutil.copy2(src, dest)
        return dest

    def _into_library(self, src: Path) -> Path:
        dest = self._library_dir() / _safe_name(src.name, src.name)
        n = 1
        stem, ext = dest.stem, dest.suffix
        while dest.exists() and dest.resolve() != src.resolve():
            dest = self._library_dir() / f"{stem}_{n}{ext}"
            n += 1
        return self._copy_file(src, dest)

    def _resolve_existing(self, stored: str) -> Path | None:
        s = (stored or "").strip().replace("\\", "/")
        if not s:
            return None
        if s.startswith("file:"):
            try:
                p = to_local_path(s)
            except Exception:
                return None
            return p if p.is_file() else None
        p = Path(s)
        if not p.is_absolute():
            rel = _module_relative(s)
            in_modules = _maps_dir() / rel
            if in_modules.is_file():
                return in_modules
            p = _install_root() / s
        if p.is_file():
            return p
        name = Path(s).name
        for cand in (
            _maps_dir() / name,
            _maps_dir() / "overlays" / name,
            _maps_dir() / "library" / name,
            _stock_photo(),
        ):
            if cand.is_file() and (name in cand.name or cand == _stock_photo()):
                if cand == _stock_photo() and "vkb_gladiator_rig" not in s and name != cand.name:
                    continue
                return cand
        stock = _stock_photo()
        if "vkb_gladiator_rig" in s and stock.is_file():
            return stock
        return None

    def _pack_assets(self, device_name: str, payload: dict) -> dict:
        folder = self._profile_dir(device_name)
        slug = folder.name
        image = str(payload.get("image") or "")
        src = self._resolve_existing(image) or _stock_photo()
        ext = src.suffix.lower() if src and src.suffix.lower() in _IMAGE_EXT else ".jpg"
        if not src or not src.is_file():
            payload["image"] = "qml/images/vkb_gladiator_rig.jpg"
        else:
            dest = folder / f"photo{ext}"
            self._copy_file(src, dest)
            payload["image"] = _asset_ref(slug, dest.name)
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            rel = str(node.get("src") or "")
            if not rel or node.get("shape") != "image":
                continue
            ov = self._resolve_existing(rel)
            if not ov or not ov.is_file():
                continue
            dest = folder / _safe_name(ov.name, "overlay.png")
            if dest.exists() and dest.resolve() != ov.resolve():
                n = 1
                while dest.exists() and dest.resolve() != ov.resolve():
                    dest = folder / f"{dest.stem}_{n}{dest.suffix}"
                    n += 1
            self._copy_file(ov, dest)
            node["src"] = _asset_ref(slug, dest.name)
            node.pop("srcUrl", None)
        return payload

    @QtCore.Slot(result=str)
    def exportFolderUrl(self) -> str:
        return _export_dir().as_uri()

    @QtCore.Slot(str, result=str)
    def defaultExportUrl(self, device_name: str) -> str:
        path = _export_dir() / f"{_slug(device_name)}_map.zip"
        return path.as_uri()

    @QtCore.Slot(result=str)
    def packDevices(self) -> str:
        return json.dumps({"ok": True, "devices": _known_pack_devices()})

    @QtCore.Slot(str, result=str)
    def peekPackDevice(self, device_name: str) -> str:
        from gremlin.ui.device_pack import assemble, pack_modes

        built = assemble(device_name, self._resolve_existing)
        if isinstance(built, str):
            return json.dumps({"ok": False, "error": built, "device": device_name})
        _data, info = built
        photo = info.get("photoPath") or ""
        match = _match_pack_device(device_name)
        guid = str(match["guid"]) if match and match.get("guid") else ""
        return json.dumps({
            "ok": True,
            "device": info["device"],
            "photoUrl": Path(photo).as_uri() if photo else "",
            "sizeText": info["sizeText"],
            "bytes": info["bytes"],
            # The modes in which it has wires, for Export's choice.
            "modes": pack_modes(guid),
        })

    @QtCore.Slot(str, result=str)
    def peekPackZip(self, zip_url: str) -> str:
        from gremlin.ui.device_pack import describe_zip

        try:
            src = to_local_path(zip_url)
        except Exception:
            return json.dumps({"ok": False, "error": "Cannot read that file."})
        if not src or not src.is_file():
            return json.dumps({"ok": False, "error": "File not found."})
        described = describe_zip(Path(src))
        if isinstance(described, str):
            return json.dumps({"ok": False, "error": described})
        return json.dumps(described)

    @QtCore.Slot(str, str, str, result=str)
    def exportPack(self, device_name: str, dest_url: str, options: str) -> str:
        """options: {"modes": [...] (or absent: all), "author", "note"}."""
        from gremlin.ui.device_pack import assemble

        try:
            chosen = json.loads(options) if str(options or "").strip() else {}
        except json.JSONDecodeError:
            chosen = {}
        if not isinstance(chosen, dict):
            chosen = {}
        modes = chosen.get("modes")
        built = assemble(
            device_name,
            self._resolve_existing,
            [str(m) for m in modes] if isinstance(modes, list) else None,
            {"author": chosen.get("author"), "note": chosen.get("note")},
        )
        if isinstance(built, str):
            return json.dumps({"ok": False, "error": built})
        data, info = built
        try:
            dest = to_local_path(dest_url)
        except Exception:
            return json.dumps({"ok": False, "error": "Cannot write that path."})
        if not dest or not str(dest).strip() or dest.name in ("", ".zip"):
            return json.dumps({"ok": False, "error": "Cannot write that path."})
        if dest.suffix.lower() != ".zip":
            dest = dest.with_suffix(".zip")
        if not _outside_maps(dest):
            return json.dumps({
                "ok": False,
                "error": "Save the pack outside the module folder.",
            })
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_bytes(data)
        except Exception as exc:
            trace("SAVE", "Device Pack", "exportPack", dest, "error")
            return json.dumps({"ok": False, "error": str(exc)})
        trace("SAVE", "Device Pack", "exportPack", dest, "ok")
        return json.dumps({
            "ok": True,
            "path": str(dest),
            "folderUrl": dest.parent.as_uri(),
            "device": info["device"],
            "sizeText": info["sizeText"],
        })

    @QtCore.Slot(str, str, str, result=str)
    def importPack(self, zip_url: str, target_name: str, selection: str) -> str:
        from gremlin.ui.device_pack import apply_zip, describe_zip

        try:
            src = to_local_path(zip_url)
        except Exception:
            return json.dumps({"ok": False, "error": "Cannot read that file."})
        if not src or not src.is_file():
            return json.dumps({"ok": False, "error": "File not found."})
        chosen: dict | None
        if str(selection or "").strip():
            try:
                chosen = json.loads(selection)
            except json.JSONDecodeError:
                return json.dumps({"ok": False, "error": "The selection could not be read."})
        else:
            described = describe_zip(Path(src))
            if isinstance(described, str):
                return json.dumps({"ok": False, "error": described})
            items = []
            outputs = {}
            for section in described.get("sections") or []:
                if str(section.get("id", "")).startswith("out:"):
                    slug = str(section["id"])[4:]
                    outputs[slug] = section.get("target") or section.get("title") or ""
                for item in section.get("items") or []:
                    if item.get("checked") is False:
                        continue
                    items.append(item["id"])
            chosen = {"items": items, "outputs": outputs}
        result = apply_zip(Path(src), target_name, chosen if isinstance(chosen, dict) else {})
        return json.dumps(result)

    @QtCore.Slot(str, str, str, result=str)
    def previewPackImport(self, zip_url: str, target_name: str, selection: str) -> str:
        """What Import would replace, for the warning before it."""
        from gremlin.ui.device_pack import preview_import

        try:
            src = to_local_path(zip_url)
            chosen = json.loads(selection) if str(selection or "").strip() else {}
        except Exception:
            error = "The pack or the selection could not be read."
            return json.dumps({"ok": False, "error": error})
        if not src or not src.is_file():
            return json.dumps({"ok": False, "error": "File not found."})
        chosen = chosen if isinstance(chosen, dict) else {}
        return json.dumps(preview_import(Path(src), target_name, chosen))

    @QtCore.Slot(result=str)
    def undoPackImport(self) -> str:
        from gremlin.ui.device_pack import undo_import

        return json.dumps(undo_import())

    @QtCore.Slot()
    def keepPackImport(self) -> None:
        """The last import stays: Undo Import is no longer offered."""
        from gremlin.ui.device_pack import drop_import_undo

        drop_import_undo()

    @QtCore.Slot(result=bool)
    def canUndoPackImport(self) -> bool:
        from gremlin.ui.device_pack import can_undo_import

        return can_undo_import()

    @QtCore.Slot(str)
    def showFolder(self, folder_url: str) -> None:
        """Opens a folder in Explorer (Show Folder after Export)."""
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(folder_url))

    @QtCore.Slot(str, result="QVariant")
    def chips(self, guid: str):
        return chips_for_guid(guid)

    @QtCore.Slot(str)
    def setDeviceGuid(self, guid: str) -> None:
        self._device_guid = str(guid or "")

    # --- the photo's look (Photo > Adjust photo) ---------------------------------

    @QtCore.Slot(str, float, float, float, result=str)
    def adjustedPhotoUrl(
        self, url: str, bright: float, contrast: float, grey: float
    ) -> str:
        """A copy of the photo with brightness, contrast and greyscale applied,
        kept in a cache beside the module files; "" when nothing is changed
        or the photo cannot be read."""
        if not (bright or contrast or grey):
            return ""
        text = str(url or "")
        source = text[len("qrc"):] if text.startswith("qrc:") else to_local_path(text)
        image = QtGui.QImage(str(source))
        if image.isNull():
            return ""
        stamp = ""
        try:
            stamp = str(Path(source).stat().st_mtime_ns)
        except OSError:
            pass
        key = hashlib.sha1(
            f"{source}|{stamp}|{bright:.3f}|{contrast:.3f}|{grey:.3f}".encode()
        ).hexdigest()[:16]
        folder = _maps_dir() / "cache"
        target = folder / f"photo-{key}.png"
        if not target.is_file():
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError:
                return ""
            if not adjust_photo(image, bright, contrast, grey).save(str(target), "PNG"):
                return ""
            # Only the latest few are kept.
            old = sorted(folder.glob("photo-*.png"), key=lambda f: f.stat().st_mtime)
            for stale in old[:-_LOOK_CACHE]:
                try:
                    stale.unlink()
                except OSError:
                    pass
        return QtCore.QUrl.fromLocalFile(str(target)).toString()

    # --- layouts of other devices (Edit > Copy Button Map from Device) ---

    @QtCore.Slot(str, result=list)
    def savedLayouts(self, device_name: str) -> list:
        """Other devices' module files that hold a Button Map layout, as
        [{name, slug}] by name; device_name's own file is left out."""
        own = ""
        if device_name:
            own = self._file_for(device_name).stem
        rows = []
        for path in sorted(_maps_dir().glob("*.json")):
            if path.stem == own:
                continue
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(doc, dict) or not doc.get("nodes"):
                continue
            name = str(doc.get("device") or path.stem)
            rows.append({"name": name, "slug": path.stem})
        rows.sort(key=lambda row: row["name"].lower())
        return rows

    @QtCore.Slot(str, result=str)
    def layoutNodes(self, slug: str) -> str:
        """The layout (nodes) in another device's module file, as JSON text;
        "" when there is none."""
        if not slug or any(c in slug for c in ("/", "\\", ":")):
            return ""
        try:
            doc = json.loads((_maps_dir() / f"{slug}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        nodes = doc.get("nodes") if isinstance(doc, dict) else None
        return json.dumps(nodes) if isinstance(nodes, list) and nodes else ""

    # --- layout templates (File > Templates) ----------------------------------

    def _templates_dir(self) -> Path:
        return _maps_dir() / "templates"

    def _template_file(self, name: str) -> Path | None:
        stem = _template_stem(name)
        return self._templates_dir() / f"{stem}.json" if stem else None

    @QtCore.Slot(result=list)
    def templates(self) -> list:
        """Saved layout templates by name: [{name, savedAt, count}]."""
        rows = []
        folder = self._templates_dir()
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            doc = _read_template(path)
            if doc is None:
                continue
            rows.append({
                "name": str(doc.get("name") or path.stem),
                "savedAt": str(doc.get("savedAt") or ""),
                "count": len(doc["nodes"]),
            })
        rows.sort(key=lambda row: row["name"].lower())
        return rows

    @QtCore.Slot(str, result=bool)
    def templateExists(self, name: str) -> bool:
        path = self._template_file(name)
        return bool(path and path.is_file())

    @QtCore.Slot(str, str, str, result=bool)
    def saveTemplate(self, name: str, nodes_json: str, device_name: str) -> bool:
        """Saves a layout under a name, replacing a template of that name."""
        path = self._template_file(name)
        try:
            nodes = json.loads(nodes_json)
        except ValueError:
            return False
        if path is None or not isinstance(nodes, list) or not nodes:
            return False
        doc = {
            "kind": "button-map-template",
            "name": name.strip(),
            "device": device_name,
            "savedAt": datetime.now().isoformat(timespec="seconds"),
            "nodes": nodes,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        except OSError:
            return False
        return True

    @QtCore.Slot(str, result=str)
    def templateNodes(self, name: str) -> str:
        path = self._template_file(name)
        doc = _read_template(path) if path else None
        return json.dumps(doc["nodes"]) if doc else ""

    @QtCore.Slot(str, result=bool)
    def deleteTemplate(self, name: str) -> bool:
        path = self._template_file(name)
        if not path or not path.is_file():
            return False
        try:
            path.unlink()
        except OSError:
            return False
        return True

    @QtCore.Slot(str, str, result=bool)
    def renameTemplate(self, name: str, new_name: str) -> bool:
        path = self._template_file(name)
        target = self._template_file(new_name)
        doc = _read_template(path) if path else None
        if doc is None or target is None:
            return False
        if target.is_file() and target != path:
            return False
        doc["name"] = new_name.strip()
        try:
            target.write_text(json.dumps(doc, indent=1), encoding="utf-8")
            if target != path:
                path.unlink()
        except OSError:
            return False
        return True

    @QtCore.Slot(str, str, result=bool)
    def exportTemplate(self, name: str, url: str) -> bool:
        """Writes a template to a file to share."""
        path = self._template_file(name)
        if not path or _read_template(path) is None:
            return False
        try:
            shutil.copyfile(path, to_local_path(url))
        except OSError:
            return False
        return True

    @QtCore.Slot(str, result=str)
    def importTemplate(self, url: str) -> str:
        """Adds a shared template file; returns its name ("" when the file is
        not a template). A name already taken gets a number."""
        doc = _read_template(Path(to_local_path(url)))
        if doc is None:
            return ""
        base = str(doc.get("name") or Path(to_local_path(url)).stem).strip() or "Template"
        name = base
        number = 2
        while self.templateExists(name):
            name = f"{base} {number}"
            number += 1
        doc["name"] = name
        path = self._template_file(name)
        if path is None:
            return ""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        except OSError:
            return ""
        return name

    # --- recovery copies (autosave) ------------------------------------------

    def _recovery_file(self, device_name: str) -> Path:
        slug = resolve_module_slug(device_name, self._guid_for_this_device(device_name))
        return _maps_dir() / "recovery" / f"{slug}.json"

    @QtCore.Slot(str, str, result=bool)
    def saveRecovery(self, device_name: str, payload: str) -> bool:
        """Keeps a copy of unsaved Button Map edits, stamped with the time.

        payload is the editor's {image, photo, nodes}. The module file is not
        touched; Save or Discard removes the copy.
        """
        try:
            doc = json.loads(payload)
        except ValueError:
            return False
        if not isinstance(doc, dict) or not isinstance(doc.get("nodes"), list):
            return False
        doc["device"] = device_name
        doc["savedAt"] = datetime.now().isoformat(timespec="seconds")
        path = self._recovery_file(device_name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(doc), encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            return False
        return True

    @QtCore.Slot(str, result=str)
    def loadRecovery(self, device_name: str) -> str:
        """The recovery copy for a device as JSON text, or "" when none."""
        path = self._recovery_file(device_name)
        try:
            text = path.read_text(encoding="utf-8")
            doc = json.loads(text)
        except (OSError, ValueError):
            return ""
        if not isinstance(doc, dict) or not isinstance(doc.get("nodes"), list):
            return ""
        return text

    @QtCore.Slot(str)
    def clearRecovery(self, device_name: str) -> None:
        try:
            self._recovery_file(device_name).unlink(missing_ok=True)
        except OSError:
            pass

    @QtCore.Slot(str, result=str)
    def load(self, device_name: str) -> str:
        name = device_name or self._device_name
        path = self._file_for(name)
        self._path = str(path)
        self.pathChanged.emit()
        if path.is_file():
            self._text = path.read_text(encoding="utf-8")
            trace("READ", "Button Map", "load", path, "ok")
        else:
            self._text = ""
            trace("READ", "Button Map", "load", path, "missing")
        persist_log(
            f"Persist map load name={name!r} guid={self._device_guid!r} path={path} bytes={len(self._text)}"
        )
        self.documentChanged.emit()
        return self._text

    @QtCore.Slot(str, str, result=bool)
    def save(self, device_name: str, json_text: str) -> bool:
        name = device_name or self._device_name
        path = self._file_for(name)
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError:
            return False
        payload["kind"] = "control.hardware"
        payload["device"] = name
        payload["space"] = "world"
        payload["page"] = 32000
        payload["pageW"] = 32000
        payload["pageH"] = 18000
        payload["photoWell"] = 0.75
        payload["photo"] = _photo_pose(payload.get("photo"))
        payload = self._pack_assets(name, payload)
        try:
            existing = module_file.load_for_update(path)
        except module_file.ModuleFileDamaged as damaged:
            # Its claims, layout and calibration would be lost: refuse.
            trace("SAVE", "Button Map", "save", path, "damaged")
            module_file.report_refused(damaged)
            return False
        if existing:
            if isinstance(existing, dict):
                # The Button Map writes its own keys; everything else in the
                # file (claims, names, calibration, Appearance...) stays.
                for key, value in existing.items():
                    if key not in payload:
                        payload[key] = value
        if is_output_name(name):
            payload["direction"] = "dest"
        module_file.write_json(path, payload)
        trace("SAVE", "Button Map", "save", path, "ok")
        kept = payload.get("claim") if isinstance(payload.get("claim"), dict) else {}
        persist_log(
            f"Persist map save name={name!r} guid={self._device_guid!r} path={path} "
            f"nodes={len(payload.get('nodes') or [])} "
            f"claimButtons={len(kept.get('buttons') or [])} "
            f"claimAxes={len(kept.get('axes') or [])}"
        )
        self._path = str(path)
        self._text = path.read_text(encoding="utf-8")
        self.pathChanged.emit()
        self.documentChanged.emit()
        self.imageChanged.emit()
        return True

    @QtCore.Slot(str, str, result=bool)
    def saveUi(self, device_name: str, json_text: str) -> bool:
        """Write only the ui block. Do not stamp page size or rewrite nodes."""
        name = device_name or self._device_name
        path = self._file_for(name)
        try:
            incoming = json.loads(json_text)
        except json.JSONDecodeError:
            return False
        if not path.is_file():
            return self.save(name, json_text)
        try:
            payload = module_file.load_for_update(path)
        except module_file.ModuleFileDamaged as damaged:
            module_file.report_refused(damaged)
            return False
        payload["ui"] = incoming.get("ui", payload.get("ui") or {})
        module_file.write_json(path, payload)
        trace("SAVE", "Button Map", "saveUi", path, "ok")
        persist_log(f"Persist map ui name={name!r} guid={self._device_guid!r} path={path}")
        self._path = str(path)
        self._text = path.read_text(encoding="utf-8")
        self.pathChanged.emit()
        self.documentChanged.emit()
        return True

    @QtCore.Slot(str, str, result=str)
    def copyOverlay(self, source_url: str, device_name: str) -> str:
        src = to_local_path(source_url)
        if not src.is_file():
            return ""
        ext = src.suffix.lower() or ".png"
        if ext not in _IMAGE_EXT:
            ext = ".png"
        self._into_library(src)
        dest = self._profile_dir(device_name) / _safe_name(src.stem + ext, src.name)
        n = 1
        while dest.exists() and dest.resolve() != src.resolve():
            dest = self._profile_dir(device_name) / f"{src.stem}_{n}{ext}"
            n += 1
        self._copy_file(src, dest)
        self.imageChanged.emit()
        return _asset_ref(self._profile_dir(device_name).name, dest.name)

    def _local_image(self, source_url: str) -> Path | None:
        raw = str(source_url or "").strip().split("?")[0].split("#")[0]
        if not raw:
            return None
        try:
            if raw.startswith("file:"):
                local = QtCore.QUrl(raw).toLocalFile()
                src = Path(local) if local else Path()
            else:
                src = to_local_path(raw)
        except Exception:
            src = Path(raw)
        return src if src.is_file() else None

    @QtCore.Slot(str, str, result=str)
    def keepPhoto(self, device_name: str, source_url: str) -> str:
        return self.copyImage(source_url, device_name)

    @QtCore.Slot(str, str, result=str)
    def copyImage(self, source_url: str, device_name: str) -> str:
        src = self._local_image(source_url)
        if src is None:
            return ""
        ext = src.suffix.lower() or ".jpg"
        if ext not in _IMAGE_EXT:
            ext = ".jpg"
        name = device_name or self._device_name
        slug = _slug(name)
        self._into_library(src)
        folder = _maps_dir() / slug
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f"photo{ext}"
        for old in folder.glob("photo.*"):
            if old.resolve() != dest.resolve():
                try:
                    old.unlink()
                except OSError:
                    pass
        try:
            self._copy_file(src, dest)
        except OSError:
            dest = folder / f"photo_{src.stem}{ext}"
            self._copy_file(src, dest)
        trace("SAVE", "Button Map", "copyImage", dest, "ok")
        rel = _asset_ref(slug, dest.name)
        # Record the picture on this device's own file only. A shared module
        # binding must not change every other card.
        path = _maps_dir() / f"{slug}.json"
        if path.is_file():
            try:
                loaded = module_file.load_for_update(path)
            except module_file.ModuleFileDamaged as damaged:
                module_file.report_refused(damaged)
                loaded = None
            if loaded is not None:
                loaded["image"] = rel
                module_file.write_json(path, loaded)
                trace("SAVE", "Button Map", "copyImage", path, "ok")
        persist_log(f"Persist photo name={name!r} guid={self._device_guid!r} path={path} image={rel!r}")
        self._path = str(path)
        self.pathChanged.emit()
        self.documentChanged.emit()
        self.imageChanged.emit()
        return rel

    @QtCore.Slot(str, result=bool)
    def clearImage(self, device_name: str) -> bool:
        name = device_name or self._device_name
        folder = _maps_dir() / _slug(name)
        for p in folder.glob("photo.*"):
            try:
                p.unlink()
                trace("SAVE", "Button Map", "clearImage", p, "removed")
            except OSError:
                return False
        for ext in _IMAGE_EXT:
            p = _maps_dir() / f"{_slug(name)}_photo{ext}"
            if p.is_file():
                try:
                    p.unlink()
                    trace("SAVE", "Button Map", "clearImage", p, "removed")
                except OSError:
                    return False
        self.imageChanged.emit()
        return True

    # Photo safety copy for one Button Map editing session. Choose
    # background… and Clear image change the photo files at once; Cancel
    # puts the session's starting photo (files and the module file's
    # "image") back, Save drops the copy.

    def _photo_files(self, slug: str) -> list[Path]:
        folder = _maps_dir() / slug
        files = []
        if folder.is_dir():
            # photo.<ext>, and copyImage's fallback photo_<name>.<ext>.
            files = [
                p
                for pattern in ("photo.*", "photo_*")
                for p in folder.glob(pattern)
                if p.is_file()
            ]
        for ext in _IMAGE_EXT:
            legacy = _maps_dir() / f"{slug}_photo{ext}"
            if legacy.is_file():
                files.append(legacy)
        return files

    @staticmethod
    def _stash_dir(slug: str) -> Path:
        return _maps_dir() / "cache" / "photo-stash" / slug

    @QtCore.Slot(str)
    def stashPhoto(self, device_name: str) -> None:
        """Keep the current photo before this session first changes it."""
        slug = _slug(device_name or self._device_name)
        stash = self._stash_dir(slug)
        if (stash / "manifest.json").is_file():
            return  # This session's starting photo is already kept.
        try:
            stash.mkdir(parents=True, exist_ok=True)
            files = []
            for i, p in enumerate(self._photo_files(slug)):
                kept = stash / f"{i}{p.suffix}"
                shutil.copy2(p, kept)
                files.append({"kept": kept.name, "to": str(p.relative_to(_maps_dir()))})
            image = None
            doc_path = _maps_dir() / f"{slug}.json"
            if doc_path.is_file():
                try:
                    loaded = json.loads(doc_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        image = loaded.get("image")
                except (OSError, json.JSONDecodeError):
                    pass
            (stash / "manifest.json").write_text(
                json.dumps({"files": files, "image": image}), encoding="utf-8"
            )
        except OSError:
            persist_log(f"Persist photo stash failed slug={slug!r}")

    @QtCore.Slot(str, result=bool)
    def restorePhoto(self, device_name: str) -> bool:
        """Put the session's starting photo back. False when none was kept."""
        slug = _slug(device_name or self._device_name)
        stash = self._stash_dir(slug)
        manifest = stash / "manifest.json"
        if not manifest.is_file():
            return False
        try:
            kept = json.loads(manifest.read_text(encoding="utf-8"))
            for p in self._photo_files(slug):
                p.unlink()
            for entry in kept.get("files", []):
                dest = _maps_dir() / entry["to"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stash / entry["kept"], dest)
            doc_path = _maps_dir() / f"{slug}.json"
            if doc_path.is_file():
                # As copyImage: a damaged file is left alone (and said), and
                # the write replaces the file whole.
                try:
                    loaded = module_file.load_for_update(doc_path)
                except module_file.ModuleFileDamaged as damaged:
                    module_file.report_refused(damaged)
                    loaded = None
                if loaded is not None:
                    if kept.get("image") is None:
                        loaded.pop("image", None)
                    else:
                        loaded["image"] = kept["image"]
                    module_file.write_json(doc_path, loaded)
        except (OSError, json.JSONDecodeError, KeyError):
            persist_log(f"Persist photo restore failed slug={slug!r}")
            return False
        shutil.rmtree(stash, ignore_errors=True)
        trace("SAVE", "Button Map", "restorePhoto", slug, "ok")
        self.imageChanged.emit()
        return True

    @QtCore.Slot(str, result=bool)
    def hasPhotoStash(self, device_name: str) -> bool:
        """True while a photo change of this editing session isn't saved."""
        slug = _slug(device_name or self._device_name)
        return (self._stash_dir(slug) / "manifest.json").is_file()

    @QtCore.Slot(str)
    def dropPhotoStash(self, device_name: str) -> None:
        """The session was saved: its starting photo is no longer needed."""
        slug = _slug(device_name or self._device_name)
        shutil.rmtree(self._stash_dir(slug), ignore_errors=True)

    @QtCore.Slot(result=str)
    def imagesFolderUrl(self) -> str:
        path = _install_root() / "qml" / "images"
        path.mkdir(parents=True, exist_ok=True)
        return QtCore.QUrl.fromLocalFile(str(path)).toString()

    @QtCore.Slot(str, result=str)
    def imageUrl(self, stored: str) -> str:
        found = self._resolve_existing(stored)
        if found and found.is_file():
            return found.as_uri()
        s = (stored or "").strip().replace("\\", "/")
        if not s or "vkb_gladiator_rig" in s:
            return ""
        if s.startswith("file:") or s.startswith("qrc:"):
            return s
        return ""

    @QtCore.Slot(str, result=str)
    def profilePhotoUrl(self, device_name: str) -> str:
        own = _maps_dir() / _slug(device_name)
        for p in sorted(own.glob("photo.*")):
            if p.is_file():
                return p.as_uri() + f"?t={int(p.stat().st_mtime_ns)}"
        text = self.load(device_name)
        try:
            doc = json.loads(text) if text else {}
        except json.JSONDecodeError:
            doc = {}
        found = self._resolve_existing(str(doc.get("image") or ""))
        if found and found.is_file():
            # Never reuse the EVO R grip shot for a different module.
            if found == _stock_photo() and _slug(device_name) != "vkb_evo_r":
                return ""
            try:
                # A picture saved for another device lives in that device's folder.
                if found.resolve().parent != own.resolve():
                    found = None
            except OSError:
                found = None
            if found is not None:
                return found.as_uri() + f"?t={int(found.stat().st_mtime_ns)}"
        if _slug(device_name) == "vkb_evo_r":
            stock = _stock_photo()
            return stock.as_uri() if stock.is_file() else ""
        if _slug(device_name) == "vkb_evo_l":
            stock = _stock_photo_l()
            if stock.is_file():
                return stock.as_uri()
            packed = _maps_dir() / "vkb_evo_l" / "photo.jpg"
            return packed.as_uri() if packed.is_file() else ""
        return ""

    @QtCore.Property(str, notify=pathChanged)
    def path(self) -> str:
        return self._path

    @QtCore.Property(str, notify=documentChanged)
    def text(self) -> str:
        return self._text
