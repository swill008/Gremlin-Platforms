# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

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
from gremlin.modules.claim import claim_ids
from gremlin.modules.ids import stored_guid_key
from gremlin.modules.registry import (
    _binding_store,
    _guid_for_name,
    _name_key,
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
    return pose


_RECENT_COLOURS = 10


def _is_hex_colour(value: object) -> bool:
    text = str(value or "")
    return (
        len(text) == 7
        and text.startswith("#")
        and all(ch in "0123456789abcdefABCDEF" for ch in text[1:])
    )


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
    owned = _guid_for_name(device_name)
    if owned and owned != given:
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
                dest.unlink()
            note = "The new module file was removed."
        else:
            _replace_file(dest, previous)
            note = "The previous module file was put back."
            trace("SAVE", "Configure Module", "undo_last_import", dest, "ok")
    except OSError:
        return "Undo failed. The previous module file could not be put back."
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
    _clear_bindings_to(src.stem)
    _clear_device_binding(name, str(guid or ""))
    _import_undo = {
        "dest": str(dest),
        "previous": previous_bytes,
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
        if plain_slug(value) == slug:
            users.add(key)
    for dev in _live_devices():
        guid = stored_guid_key(getattr(dev, "device_guid", ""))
        name = str(getattr(dev, "name", "") or "")
        if guid and name and resolve_module_slug(name, guid) == slug:
            users.add(guid)
    return users


def load_module_file(device_name: str, guid: str, source_url: str, direction: str = "source") -> str:
    return import_module_file(device_name, guid, source_url, direction)


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
        path.unlink()
        trace("SAVE", "Configure Module", "delete_module_file", path, "removed")
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
    except (OSError, json.JSONDecodeError):
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

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._device_name = "VKBsim Gladiator EVO R"
        self._text = "{}"
        self._path = ""
        self._peek_photo = ""
        self._device_guid = ""
        clipboard = _clipboard()
        if clipboard is not None:
            clipboard.dataChanged.connect(self.clipboardChanged)

    @QtCore.Property(list, notify=recentColoursChanged)
    def recentColours(self) -> list:
        """Colours last applied in the editor, newest first (all devices)."""
        from gremlin.config import Configuration

        stored = Configuration().value(
            "global", "internal", "button-map-recent-colours"
        )
        return [str(c) for c in (stored or []) if _is_hex_colour(c)][:_RECENT_COLOURS]

    @QtCore.Slot(str)
    def noteColour(self, hex_colour: str) -> None:
        """Puts a colour first in the recent colours (once, at most ten)."""
        from gremlin.config import Configuration

        colour = str(hex_colour or "").strip().upper()
        if not _is_hex_colour(colour):
            return
        recent = [c for c in self.recentColours if c.upper() != colour]
        recent = [colour, *recent][:_RECENT_COLOURS]
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

    @QtCore.Property(bool, notify=clipboardChanged)
    def clipboardHasImage(self) -> bool:
        """The clipboard holds a picture the Button Map can paste."""
        clipboard = _clipboard()
        data = clipboard.mimeData() if clipboard is not None else None
        return bool(data is not None and data.hasImage())

    @QtCore.Slot(str, result=str)
    def pasteClipboardImage(self, device_name: str) -> str:
        """Saves the clipboard's picture as a layer picture for the device."""
        clipboard = _clipboard()
        image = clipboard.image() if clipboard is not None else QtGui.QImage()
        return self.savePastedImage(image, device_name)

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
        owned = stored_guid_key(_guid_for_name(device_name))
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
        from gremlin.ui.device_pack import assemble

        built = assemble(device_name, self._resolve_existing)
        if isinstance(built, str):
            return json.dumps({"ok": False, "error": built, "device": device_name})
        _data, info = built
        photo = info.get("photoPath") or ""
        return json.dumps({
            "ok": True,
            "device": info["device"],
            "photoUrl": Path(photo).as_uri() if photo else "",
            "sizeText": info["sizeText"],
            "bytes": info["bytes"],
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

    @QtCore.Slot(str, str, result=str)
    def exportPack(self, device_name: str, dest_url: str) -> str:
        from gremlin.ui.device_pack import assemble

        built = assemble(device_name, self._resolve_existing)
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
                    if str(item.get("id", "")).endswith("camera"):
                        continue
                    items.append(item["id"])
            chosen = {"items": items, "outputs": outputs}
        result = apply_zip(Path(src), target_name, chosen if isinstance(chosen, dict) else {})
        return json.dumps(result)

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
        if is_output_name(name):
            payload["direction"] = "dest"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
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
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict):
            return False
        payload["ui"] = incoming.get("ui", payload.get("ui") or {})
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
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
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded = None
            if isinstance(loaded, dict):
                loaded["image"] = rel
                path.write_text(json.dumps(loaded, indent=2) + "\n", encoding="utf-8")
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
