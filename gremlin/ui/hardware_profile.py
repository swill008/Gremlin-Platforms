# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.signal import signal
from gremlin.ui.util import to_local_path

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

# Off unless someone is tracing a save. Same idea as the HiDHide log switch.
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
    return {
        "scale": max(0.25, min(4.0, scale)),
        "offX": max(-1.0, min(1.0, _num("offX", 0.0))),
        "offY": max(-1.0, min(1.0, _num("offY", 0.0))),
        "rot": _num("rot", 0.0),
    }


def _install_root() -> Path:
    return Path(os.path.normcase(os.path.dirname(os.path.abspath(sys.argv[0]))))


def _maps_dir() -> Path:
    path = _install_root() / "qml" / "maps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _plain_slug(device_name: str) -> str:
    raw = (device_name or "").strip().lower()
    if raw.endswith(".json"):
        raw = raw[:-5]
    out = []
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_")


def _slug(device_name: str) -> str:
    raw = (device_name or "device").strip().lower()
    if "gladiator" in raw and "ot" not in raw and ("evo r" in raw):
        return "vkb_evo_r"
    if "gladiator" in raw and "ot" not in raw and ("evo l" in raw):
        return "vkb_evo_l"
    return _plain_slug(device_name) or "device"


def _norm_guid(value: object) -> str:
    return str(value or "").upper().replace("{", "").replace("}", "").replace("-", "")


def guid_for_module(device_name: str, guid: str) -> str:
    """Use guid only when it belongs to device_name. A stale id must not select another module."""
    given = _norm_guid(guid)
    if not given:
        return ""
    owned = _guid_for_name(device_name)
    if owned and owned != given:
        return ""
    return str(guid)


def _guid_for_name(device_name: str) -> str:
    wanted = (device_name or "").strip().lower()
    if not wanted:
        return ""
    try:
        from gremlin import device_initialization
        devices = list(device_initialization.physical_devices() or [])
        devices.extend(device_initialization.vjoy_devices() or [])
    except Exception:
        devices = []
    for dev in devices:
        name = str(getattr(dev, "name", "") or "")
        if name.strip().lower() != wanted:
            continue
        return _norm_guid(getattr(dev, "device_guid", ""))
    return ""


def _binding_store() -> dict[str, str]:
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    cfg = Configuration()
    section, group, name = "global", "internal", "module-file-bindings"
    # Register every launch. An existing value is kept. Skipping this when
    # the key already exists leaves it unregistered, and purge_unused deletes it.
    cfg.register(
        section,
        group,
        name,
        PropertyType.String,
        "{}",
        "Input module file chosen for each device.",
        {},
        False,
    )
    try:
        data = json.loads(cfg.value(section, group, name) or "{}")
    except (TypeError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if key and value}


def _write_bindings(data: dict[str, str]) -> None:
    from gremlin.config import Configuration

    _binding_store()
    Configuration().set("global", "internal", "module-file-bindings", json.dumps(data))


def _name_key(device_name: str) -> str:
    slug = _plain_slug(device_name)
    return f"name:{slug}" if slug else ""


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
    if _norm_guid(guid) and _norm_guid(doc.get("boundGuidLocal")) == _norm_guid(guid):
        return bound
    return own_path


def resolve_module_slug(device_name: str, guid: str = "") -> str:
    data = _binding_store()
    key = _norm_guid(guid) or _guid_for_name(device_name)
    bound = data.get(key, "") if key else ""
    name_key = _name_key(device_name)
    if not bound and name_key:
        bound = data.get(name_key, "")
    if bound:
        return _plain_slug(bound) or _slug(device_name)
    return _slug(device_name)


def module_file_choices(device_name: str, guid: str = "") -> list[str]:
    """Files that can be copied onto this device. Not the file the device uses."""
    del guid
    own = _slug(device_name)
    names = [
        path.stem
        for path in sorted(_maps_dir().glob("*.json"))
        if path.is_file() and path.stem.lower() != own
    ]
    imported = _maps_dir() / "imported"
    if imported.is_dir():
        names.extend(
            f"imported/{path.stem}"
            for path in sorted(imported.glob("*.json"))
            if path.is_file()
        )
    return names


def own_module_slug(device_name: str) -> str:
    return _slug(device_name)


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


def _filter_nodes(nodes: list, buttons: set[int], axes: set[int], hats: set[int], keys: set[int]) -> list:
    kept: list = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "")
        if kind in ("stack", "axis_stack"):
            want = axes if kind == "axis_stack" else buttons
            members = []
            for member in node.get("members") or []:
                if not isinstance(member, dict):
                    continue
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
        import dill
        info = dill.DILL.get_device_information_by_guid(dill.GUID.from_str(guid))
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
    source_buttons = set(_explicit_ids(claim, "buttons"))
    source_axes = set(_explicit_ids(claim, "axes"))
    source_hats = set(_explicit_ids(claim, "hats"))
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
    path = _maps_dir() / f"{_plain_slug(rel)}.json"
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


def _owner_name(stem: str, device_name: str, guid: str) -> str:
    """Another connected device whose own file name is this stem. A binding is not ownership."""
    me = _norm_guid(guid)
    me_name = str(device_name or "").strip().lower()
    want = stem.lower()
    for dev in _live_devices():
        name = str(getattr(dev, "name", "") or "").strip()
        dev_guid = _norm_guid(getattr(dev, "device_guid", ""))
        if me and dev_guid == me:
            continue
        if not me and name.lower() == me_name:
            continue
        if _slug(name).lower() == want:
            return name or want
    return ""


def _clear_bindings_to(slug: str) -> None:
    data = _binding_store()
    want = _plain_slug(slug)
    keys = [key for key, value in data.items() if _plain_slug(value) == want]
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
    """Put this device's previous file back. Do not put old bindings back."""
    global _import_undo
    record = _import_undo
    if not record:
        return "Undo failed. There is nothing to undo."
    notes = []
    dest = Path(record["dest"])
    previous = record.get("previous")
    try:
        if previous is None:
            if dest.is_file():
                dest.unlink()
            notes.append("The new module file was removed.")
        else:
            _replace_file(dest, previous)
            notes.append("The previous module file was put back.")
    except OSError:
        return "Undo failed. The previous module file could not be put back."
    moved_from = str(record.get("moved_from") or "")
    moved_to = str(record.get("moved_to") or "")
    if moved_from and moved_to:
        source = Path(moved_to)
        target = Path(moved_from)
        if not source.is_file():
            notes.append(f"{source.name} could not be moved back.")
        elif target.exists():
            notes.append(f"{target.name} could not be moved back because that name is already in use.")
        else:
            try:
                shutil.move(str(source), str(target))
                notes.append(f"{target.name} was moved back.")
            except OSError:
                notes.append(f"{source.name} could not be moved back.")
    _import_undo = None
    return "Undone. " + " ".join(notes)


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
        return "That file could not be read."
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
        return "The module file could not be written."
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
    moved_from = ""
    moved_to = ""
    if previous_bytes is not None:
        backup = _archive_path(own_slug, stamp)
        try:
            if backup.exists():
                raise FileExistsError(backup)
            _replace_file(backup, previous_bytes)
            lines.append(f"The previous file was saved as {backup.name}.")
        except OSError:
            lines.append("The previous file could not be saved to imported.")
    maps = _maps_dir().resolve()
    imported = (maps / "imported").resolve()
    try:
        src_res = src.resolve()
    except OSError:
        src_res = src
    if src_res.parent == imported:
        lines.append(f"{src.name} was left in imported.")
    else:
        owner = _owner_name(src.stem, name, str(guid or ""))
        if owner:
            lines.append(f"{src.name} was left in place. {owner} uses that file.")
        else:
            archived = _archive_path(src.stem, stamp)
            try:
                if archived.exists():
                    raise FileExistsError(archived)
                archived.parent.mkdir(parents=True, exist_ok=True)
                if src_res.parent == maps:
                    shutil.move(str(src_res), str(archived))
                    moved_from = str(src_res)
                    moved_to = str(archived)
                    lines.append(f"{src.name} was moved to imported as {archived.name}.")
                else:
                    _replace_file(archived, src_res.read_bytes())
                    lines.append(f"{src.name} was copied to imported as {archived.name}. The original was left where it was.")
            except OSError:
                lines.append(f"{src.name} could not be moved to imported.")
    _clear_bindings_to(src.stem)
    _clear_device_binding(name, str(guid or ""))
    _import_undo = {
        "dest": str(dest),
        "previous": previous_bytes,
        "moved_from": moved_from,
        "moved_to": moved_to,
    }
    persist_log(f"Persist import file name={name!r} guid={guid!r} src={src} dest={dest}")
    return "\n".join(lines)


def _clear_device_binding(device_name: str, guid: str) -> None:
    data = _binding_store()
    key = _norm_guid(guid) or _guid_for_name(device_name)
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
    slug = _plain_slug(file_name)
    key = _norm_guid(guid) or _guid_for_name(device_name)
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


def module_file_exists(device_name: str, guid: str = "") -> bool:
    slug = resolve_module_slug(device_name, guid)
    return bool(slug) and (_maps_dir() / f"{slug}.json").is_file()


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
        if _plain_slug(value) == slug:
            users.add(key)
    for dev in _live_devices():
        guid = _norm_guid(getattr(dev, "device_guid", ""))
        name = str(getattr(dev, "name", "") or "")
        if guid and name and resolve_module_slug(name, guid) == slug:
            users.add(guid)
    return users


def load_module_file(device_name: str, guid: str, source_url: str, direction: str = "source") -> str:
    return import_module_file(device_name, guid, source_url, direction)


def delete_module_file(device_name: str, guid: str) -> str:
    """Delete this device's own file. Do not delete, or unhook, a different file."""
    slug = _slug(device_name)
    key = _norm_guid(guid) or _guid_for_name(device_name)
    others = _users_of_slug(slug) - ({key} if key else set())
    name_key = _name_key(device_name)
    others.discard(name_key)
    if others:
        return "Another stick is using this file."
    path = _maps_dir() / f"{slug}.json"
    if path.is_file():
        path.unlink()
    data = _binding_store()
    changed = False
    if key and _plain_slug(str(data.get(key, ""))) == slug:
        data.pop(key, None)
        changed = True
    if name_key and _plain_slug(str(data.get(name_key, ""))) == slug:
        data.pop(name_key, None)
        changed = True
    if changed:
        _write_bindings(data)
    return ""


def maps_folder_url() -> str:
    return _maps_dir().as_uri()


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


def _explicit_ids(claim: dict, key: str) -> list[int]:
    raw = claim.get(key) if isinstance(claim, dict) else None
    ids: list[int] = []
    for item in raw or []:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number > 0:
            ids.append(number)
    return sorted(set(ids))


def _device_input_ids(guid: str) -> tuple[list[int], list[int], list[int]]:
    buttons: list[int] = []
    axes: list[int] = []
    hats: list[int] = []
    try:
        import dill
        info = dill.DILL.get_device_information_by_guid(dill.GUID.from_str(guid))
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
        ("btn", _explicit_ids(claim, "buttons"), reported[0], stored[0]),
        ("axis", _explicit_ids(claim, "axes"), reported[1], stored[1]),
        ("hat", _explicit_ids(claim, "hats"), reported[2], stored[2]),
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

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._device_name = "VKBsim Gladiator EVO R"
        self._text = "{}"
        self._path = ""
        self._peek_photo = ""
        self._device_guid = ""

    def _guid_for_this_device(self, device_name: str) -> str:
        # The object remembers one device. Do not use that id for a different name.
        guid = _norm_guid(self._device_guid)
        if not guid:
            return ""
        owned = _norm_guid(_guid_for_name(device_name))
        if not owned or owned != guid:
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
            payload["image"] = f"qml/maps/{slug}/{dest.name}"
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
            node["src"] = f"qml/maps/{slug}/{dest.name}"
            node.pop("srcUrl", None)
        return payload

    @QtCore.Slot(str, result=str)
    def defaultPath(self, device_name: str) -> str:
        return str(self._file_for(device_name))

    @QtCore.Slot(str, result=str)
    def defaultExportUrl(self, device_name: str) -> str:
        path = _maps_dir() / f"{_slug(device_name)}_map.zip"
        return path.as_uri()

    @QtCore.Slot(str, result="QVariant")
    def chips(self, guid: str):
        return chips_for_guid(guid)

    @QtCore.Slot(str)
    def setDeviceGuid(self, guid: str) -> None:
        self._device_guid = str(guid or "")

    @QtCore.Slot(str, result=str)
    def load(self, device_name: str) -> str:
        name = device_name or self._device_name
        path = self._file_for(name)
        self._path = str(path)
        self.pathChanged.emit()
        if path.is_file():
            self._text = path.read_text(encoding="utf-8")
        else:
            self._text = ""
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
        payload.pop("worldRev", None)
        payload["photo"] = _photo_pose(payload.get("photo"))
        payload = self._pack_assets(name, payload)
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
            if isinstance(existing, dict):
                for key in (
                    "claim",
                    "direction",
                    "boundGuidLocal",
                    "boundName",
                    "view",
                    "catalog",
                ):
                    if key in existing and key not in payload:
                        payload[key] = existing[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
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
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict):
            return False
        payload["ui"] = incoming.get("ui", payload.get("ui") or {})
        payload.pop("worldRev", None)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
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
        return f"qml/maps/{self._profile_dir(device_name).name}/{dest.name}"

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
        rel = f"qml/maps/{slug}/{dest.name}"
        # Record the picture on this device's own file only. A shared module
        # binding must not change every other card.
        path = _maps_dir() / f"{slug}.json"
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded = None
            if isinstance(loaded, dict):
                loaded["image"] = rel
                path.write_text(json.dumps(loaded, indent=2) + "\n", encoding="utf-8")
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
            except OSError:
                return False
        for ext in _IMAGE_EXT:
            p = _maps_dir() / f"{_slug(name)}_photo{ext}"
            if p.is_file():
                try:
                    p.unlink()
                except OSError:
                    return False
        self.imageChanged.emit()
        return True

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

    def _plate_count(self, payload: dict) -> int:
        n = 0
        for node in payload.get("nodes") or []:
            if isinstance(node, dict) and node.get("shape") == "image" and node.get("src"):
                n += 1
        return n

    @QtCore.Slot(str, result=str)
    def peekLocal(self, device_name: str) -> str:
        name = device_name or self._device_name
        text = self.load(name)
        try:
            doc = json.loads(text) if text else {}
        except json.JSONDecodeError:
            doc = {}
        device = str(doc.get("device") or name)
        return json.dumps({
            "ok": True,
            "device": device,
            "slug": _slug(device),
            "photoUrl": self.profilePhotoUrl(name),
            "plates": self._plate_count(doc),
            "fallback": "vkb_gladiator_rig" in str(doc.get("image") or "") or not doc,
        })

    @QtCore.Slot(str, result=str)
    def peekZip(self, zip_url: str) -> str:
        try:
            src = to_local_path(zip_url)
        except Exception:
            return json.dumps({"ok": False, "error": "Cannot read that file."})
        if not src or not src.is_file():
            return json.dumps({"ok": False, "error": "File not found."})
        try:
            with zipfile.ZipFile(src, "r") as zf:
                names = zf.namelist()
                json_name = "map.json" if "map.json" in names else next(
                    (n for n in names if n.lower().endswith(".json") and "/" not in n.strip("/")),
                    "",
                )
                if not json_name:
                    return json.dumps({"ok": False, "error": "No map.json in this zip."})
                doc = json.loads(zf.read(json_name).decode("utf-8"))
                device = str(doc.get("device") or "")
                photo_name = Path(str(doc.get("image") or "photo.jpg")).name
                photo_member = photo_name if photo_name in names else next(
                    (n for n in names if Path(n).name.startswith("photo")),
                    "",
                )
                photo_url = ""
                fallback = False
                if photo_member:
                    data = zf.read(photo_member)
                    tmp = Path(tempfile.gettempdir()) / f"jg_peek_{_slug(device) or 'map'}{Path(photo_member).suffix}"
                    tmp.write_bytes(data)
                    self._peek_photo = str(tmp)
                    photo_url = tmp.as_uri()
                else:
                    stock = _stock_photo()
                    photo_url = stock.as_uri() if stock.is_file() else ""
                    fallback = True
                return json.dumps({
                    "ok": True,
                    "device": device,
                    "slug": _slug(device),
                    "photoUrl": photo_url,
                    "plates": self._plate_count(doc),
                    "fallback": fallback,
                })
        except zipfile.BadZipFile:
            return json.dumps({"ok": False, "error": "Not a valid zip."})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    @QtCore.Slot(str, str, result=str)
    def exportMap(self, device_name: str, dest_url: str) -> str:
        name = device_name or self._device_name
        if not name:
            return json.dumps({"ok": False, "error": "Select a Status card first."})
        path = self._file_for(name)
        if not path.is_file():
            return json.dumps({"ok": False, "error": "Save the module first."})
        try:
            dest = to_local_path(dest_url)
        except Exception:
            return json.dumps({"ok": False, "error": "Cannot write that path."})
        if not dest or not str(dest).strip() or dest.name in ("", ".zip"):
            return json.dumps({"ok": False, "error": "Cannot write that path."})
        if dest.suffix.lower() != ".zip":
            dest = dest.with_suffix(".zip")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return json.dumps({"ok": False, "error": "Profile JSON is not valid."})
        payload = self._pack_assets(name, payload)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        persist_log(f"Persist export rewrite name={name!r} guid={self._device_guid!r} path={path}")
        packed = json.loads(json.dumps(payload))
        packed.pop("boundGuidLocal", None)
        files = []
        photo = self._resolve_existing(str(packed.get("image") or ""))
        if photo and photo.is_file():
            files.append((photo, photo.name if photo.name.startswith("photo") else "photo" + photo.suffix.lower()))
            packed["image"] = files[-1][1]
        for node in packed.get("nodes") or []:
            if not isinstance(node, dict) or node.get("shape") != "image":
                continue
            ov = self._resolve_existing(str(node.get("src") or ""))
            if not ov or not ov.is_file():
                continue
            arc = _safe_name(ov.name, "overlay.png")
            used = {a for _, a in files}
            if arc in used:
                n = 1
                stem, ext = Path(arc).stem, Path(arc).suffix
                while f"{stem}_{n}{ext}" in used:
                    n += 1
                arc = f"{stem}_{n}{ext}"
            files.append((ov, arc))
            node["src"] = arc
            node.pop("srcUrl", None)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("map.json", json.dumps(packed, indent=2) + "\n")
                for src, arc in files:
                    zf.write(src, arc)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})
        return json.dumps({"ok": True, "path": str(dest), "device": name})

    @QtCore.Slot(str, result=str)
    def importMap(self, zip_url: str) -> str:
        try:
            src = to_local_path(zip_url)
        except Exception:
            return json.dumps({"ok": False, "error": "Cannot read that file."})
        if not src or not src.is_file():
            return json.dumps({"ok": False, "error": "File not found."})
        try:
            with zipfile.ZipFile(src, "r") as zf:
                names = zf.namelist()
                json_name = "map.json" if "map.json" in names else next(
                    (n for n in names if n.lower().endswith(".json") and n.count("/") == 0),
                    "",
                )
                if not json_name:
                    return json.dumps({"ok": False, "error": "No map.json in this zip."})
                payload = json.loads(zf.read(json_name).decode("utf-8"))
                device = str(payload.get("device") or "").strip()
                if not device:
                    return json.dumps({"ok": False, "error": "Zip has no device name."})
                slug = _slug(device)
                folder = self._profile_dir(device)
                extracted = {}
                for member in names:
                    if member.endswith("/") or member == json_name:
                        continue
                    base = Path(member).name
                    if not base or Path(base).suffix.lower() not in _IMAGE_EXT:
                        continue
                    dest = folder / _safe_name(base, base)
                    dest.write_bytes(zf.read(member))
                    extracted[base] = dest
                    extracted[member] = dest
                photo_key = Path(str(payload.get("image") or "photo.jpg")).name
                if photo_key in extracted:
                    payload["image"] = f"qml/maps/{slug}/{extracted[photo_key].name}"
                for node in payload.get("nodes") or []:
                    if not isinstance(node, dict):
                        continue
                    rel = str(node.get("src") or "")
                    key = Path(rel).name
                    if key in extracted:
                        node["src"] = f"qml/maps/{slug}/{extracted[key].name}"
                    node.pop("srcUrl", None)
                payload["kind"] = "control.hardware"
                payload["device"] = device
                payload["space"] = "world"
                payload["page"] = 32000
                payload["pageW"] = 32000
                payload["pageH"] = 18000
                payload["photoWell"] = 0.75
                payload.pop("worldRev", None)
                payload["photo"] = _photo_pose(payload.get("photo"))
                out = self._file_for(device)
                out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                self._path = str(out)
                self._text = out.read_text(encoding="utf-8")
                self.pathChanged.emit()
                self.documentChanged.emit()
                self.imageChanged.emit()
                signal.configChanged.emit()
                return json.dumps({"ok": True, "device": device, "slug": slug})
        except zipfile.BadZipFile:
            return json.dumps({"ok": False, "error": "Not a valid zip."})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    @QtCore.Property(str, notify=pathChanged)
    def path(self) -> str:
        return self._path

    @QtCore.Property(str, notify=documentChanged)
    def text(self) -> str:
        return self._text
