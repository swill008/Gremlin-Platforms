# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6 import (
    QtCore,
    QtGui,
    QtQuick,
)

import gremlin.ui.type_aliases as ta
from gremlin.modules import module_file, registry, store
from gremlin.modules.claim import claim_ids
from gremlin.modules.registry import is_output_name, read_doc
from gremlin.signal import signal
from gremlin.ui.live_debug import trace
from gremlin.ui.util import to_local_path

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_IMAGE_EXT = store.PICTURE_EXT

syslog = logging.getLogger("system")

# The Button Map page every position is a fraction of, and the photo frame
# in its middle (07 S68, Q14): the one place it is written. Save stamps it
# into the map (VkbRigEditor's world page follows it).
PAGE_SIZE = {"page": 32000, "pageW": 32000, "pageH": 18000, "photoWell": 0.75}


# Off unless someone is tracing a save. Same idea as the HidHide log switch.
_persist_log = False


def persist_log(message: str) -> None:
    if _persist_log:
        print(message, flush=True)


def _write_map(path: Path, change: Callable[[dict], object]) -> bool:
    """store.update_path for the Button Map's slots: a failed write is False
    (the window says "Not written"), logged once; the old file stays whole
    (07 S20, S23)."""
    try:
        return store.update_path(path, change, "Button Map")
    except OSError as exc:
        syslog.warning(f"Button Map not written to {path}: {exc}")
        return False


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


def _write_problem(path: Path) -> str:
    """Why a file could not be written at path, in a few words."""
    folder = path.parent
    if not str(path) or not folder.is_dir():
        return "the folder does not exist"
    if path.is_dir():
        return "a folder has that name"
    if path.exists():
        try:
            with open(path, "r+b"):
                pass
        except PermissionError:
            return "the file is read-only or open in another program"
        except OSError as exc:
            return str(exc.strerror or exc)
    else:
        import tempfile

        try:
            with tempfile.TemporaryFile(dir=folder):
                pass
        except PermissionError:
            return "the folder is read-only"
        except OSError as exc:
            return str(exc.strerror or exc)
    return "the picture could not be written there"


def export_failure(path: Path) -> str:
    """What Print & Export says when an export can't be written: which file
    and why (07 Q19, as Template export names its file)."""
    path = Path(path)
    return (
        f"Export failed. {path.name} could not be written to {path.parent}: "
        f"{_write_problem(path)}."
    )


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


def _named_pictures(doc: object) -> set[str]:
    """The pictures a map names (its photo and every picture chip, also
    inside groups), as stored references."""
    refs: set[str] = set()
    if isinstance(doc, dict):
        image = str(doc.get("image") or "").strip()
        if image:
            refs.add(image)

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if value.get("shape") == "image" and value.get("src"):
                refs.add(str(value["src"]))
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)

    walk(doc.get("nodes") if isinstance(doc, dict) else None)
    return refs


def _used_pictures() -> set[Path]:
    """Every picture a module file, a template or a recovery copy names
    (where it is in the modules folder)."""
    docs: list[object] = [store.read_path(path) for path in store.module_files()]
    for folder in (store.folder() / "templates", store.recovery_path("x").parent):
        if folder.is_dir():
            docs += [_read_template(path) for path in sorted(folder.glob("*.json"))]
    used: set[Path] = set()
    for doc in docs:
        for ref in _named_pictures(doc):
            try:
                used.add(store.picture_path(ref).resolve())
            except OSError:
                continue
    return used


def unused_pictures(slug: str) -> list[Path]:
    """Pictures in a device's folder no map, template or recovery copy names
    (07 Q11). The photo's files are left to the photo's own safety copy."""
    folder = store.pictures_dir_of(slug)
    if not folder.is_dir():
        return []
    photos = {p.resolve() for p in store.photo_files(slug)}
    used = _used_pictures()
    return [
        path
        for path in sorted(folder.iterdir())
        if path.is_file()
        and path.suffix.lower() in _IMAGE_EXT
        and path.resolve() not in photos
        and path.resolve() not in used
    ]


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
    """The modules folder (the module file store's)."""
    return store.folder()


# Old names of what the module file store now owns, kept for callers that
# have not moved to gremlin.modules.store yet (GL-093). New code uses the
# store.
_asset_ref = store.picture_ref
_module_relative = store.module_relative
_slug = store.own_slug
guid_for_module = store.guid_filter
_write_bindings = store.set_bindings
_binding_store = registry.binding_store
_clear_device_binding = store.unbind
_live_devices = store.live_devices
_guid_text = store.guid_text
_deleted_dir = store.deleted_dir
_keep_deleted_copy = store.keep_deleted_copy
_pack_file_name = store.pack_file_name
_archive_stamp = store.archive_stamp
_unique_archive = store.unique_archive
_doc_direction = store.doc_direction
_target_direction = store.direction_for
_known_pack_devices = store.known_devices
_match_pack_device = store.match_known_device
_suggest_pack_name = store.suggest_device_name
_safe_name = store.safe_picture_name
_read_json_dict = registry.read_doc
_device_input_ids = store.device_input_ids
_filter_nodes = store.filter_nodes
member_kind = store.member_kind
prepare_imported_doc = store.prepare_imported_doc
module_json_path = store.path_for
_active_module_path = store.path_for
_own_file_shared = store.is_shared


def _replace_file(path: Path, data: bytes) -> None:
    """Writes a whole file through the store (History for a module file).
    Raises OSError. New code calls store.replace."""
    store.replace(Path(path), data, force=True)


def module_file_choices(device_name: str, guid: str = "") -> list[str]:
    """Files in the import folder. Live module files are not listed."""
    del device_name, guid
    return store.import_choices()


def foreign_module_file(device_name: str, guid: str = "") -> str:
    """The file the device uses when it isn't the one named after it."""
    return store.foreign_file(device_name, guid)


def bind_module_file(device_name: str, guid: str, file_name: str) -> str:
    slug = store.bind(device_name, guid, file_name)
    if slug:
        persist_log(f"Persist bind file name={device_name!r} guid={guid!r} slug={slug!r}")
    return slug


# --- Delete File and Delete Device ---------------------------------------------


def delete_module_file(device_name: str, guid: str) -> str:
    """Delete File: deletes this device's file (the one it opens: a renamed
    stick's is its old file), keeping a copy in the deleted devices folder
    (03 S62). The pictures stay (03 Q14). Refused when another stick uses
    the file."""
    return store.delete(
        device_name, guid, keep_copy=True, pictures=False, who="Configure Module"
    )


def _deleted_pack_path(device_name: str) -> Path:
    """Where Delete Device's "Save a copy" writes the pack (03 S91)."""
    return store.deleted_pack_path(device_name)


def _zip_readable(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "map.json" not in zf.namelist():
                return False
            doc = json.loads(zf.read("map.json").decode("utf-8"))
        return isinstance(doc, dict)
    except Exception:
        return False


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


_STOP_FIRST = (
    "Stop the profile first. A device can't be deleted while the profile is running."
)


def delete_preview(device_name: str, guid: str) -> str:
    name = " ".join(str(device_name or "").split())
    path = store.path_for(name, guid)
    running = _profile_running()
    return json.dumps({
        "name": name,
        # Delete Device is refused while running (03 Q6): said up front.
        "running": running,
        "runningText": _STOP_FIRST if running else "",
        "canPack": path.is_file(),
        "shared": store.is_shared(name, guid),
        "foreign": bool(store.foreign_file(name, guid)),
        "listed": _device_stays_listed(name),
        "keepModule": is_output_name(name),
    })


def _drop_inputs(profile, uid) -> None:
    """The device's inputs leave the profile, with the actions only they
    used (the library's one removal rule)."""
    profile.drop_inputs(uid, list(profile.inputs.get(uid, []) or []))
    profile.inputs.pop(uid, None)


def _prune_empty_inputs(profile) -> None:
    for key, items in list(profile.inputs.items()):
        empty = [item for item in items if not getattr(item, "action_sequences", None)]
        if empty:
            profile.drop_inputs(key, empty)
        if not profile.inputs.get(key):
            profile.inputs.pop(key, None)


def _drop_profile_wires(device_name: str, guid: str) -> None:
    """The device's actions leave the profile in memory; the profile is left
    unsaved, so its own Save (with its unfinished-actions check) keeps the
    removal (03 Q4)."""
    from gremlin.shared_state import current_profile
    from gremlin.ui.input_pairing import parse_guid

    profile = current_profile
    if profile is None:
        return
    text = str(guid or "").strip() or registry.guid_for_name(device_name)
    uid = parse_guid(text)
    with profile.library.change():
        if uid is not None:
            _drop_inputs(profile, uid)
        _prune_empty_inputs(profile)
    signal.profileChanged.emit()


def _profile_running() -> bool:
    from gremlin import run_scope, shared_state

    return bool(run_scope.running() or shared_state.runtime_active())


def delete_device(device_name: str, guid: str, save_copy: bool) -> str:
    """Delete Device: the pack first when asked, then the device's wires (in
    memory, the profile left unsaved, 03 Q4), its module file (a copy always
    kept in the deleted devices folder, 03 Q5), its pictures, recovery copy
    and photo safety copies (07 Q11) and its file choices. An output module
    file, or one another stick uses, stays. Refused while running (03 Q6)."""
    from gremlin.shared_state import current_profile

    name = " ".join(str(device_name or "").split())
    if not name:
        return json.dumps({"ok": False, "error": "Choose a device."})
    # It changes the running profile (03 Q6).
    if _profile_running():
        return json.dumps({"ok": False, "error": _STOP_FIRST})
    pack_path = ""
    if save_copy:
        if not store.exists(name, guid):
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
            store.write_deleted_pack(dest, data)
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
    _drop_profile_wires(name, guid)
    # The device's file is the one it opens (a renamed stick's old file),
    # found before its file choices are cleared.
    own_path = store.path_for(name, guid)
    shared = store.is_shared(name, guid)
    protected = is_output_name(name)
    file_error = ""
    if not shared and not protected:
        file_error = store.delete(
            name, guid, keep_copy=True, pictures=True, who="Delete Device"
        )
    store.unbind(name, guid)
    own_left = own_path.is_file()
    profile = current_profile
    # The removal is in memory only: Save the profile to keep it.
    saved = profile is None or not profile.has_unsaved_changes()
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
    return store.folder().as_uri()


def imported_folder_url() -> str:
    path = store.imported_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path.as_uri()


_PICTURE_FOLDER = ("global", "internal", "button-map-picture-folder")


def _picture_folder_config():  # noqa: ANN202 - Configuration, imported late
    """The settings, with the last picture folder's entry in them."""
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    cfg = Configuration()
    if not cfg.exists(*_PICTURE_FOLDER):
        cfg.register(
            *_PICTURE_FOLDER, PropertyType.String, "",
            "Folder Choose Photo and Import Picture last took a picture from.", {},
        )
    return cfg


def _picture_folder() -> Path:
    """The last folder a picture was chosen from (when it is still there),
    else Pictures, else the home folder."""
    try:
        last = str(_picture_folder_config().value(*_PICTURE_FOLDER) or "")
    except Exception:
        last = ""
    if last and Path(last).is_dir():
        return Path(last)
    pictures = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.PicturesLocation
    )
    if pictures and Path(pictures).is_dir():
        return Path(pictures)
    return Path.home()


def _collapsed_name(value: str) -> str:
    return " ".join(str(value or "").split()).lower()


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


def _export_dir() -> Path:
    from gremlin.util import export_dir

    return export_dir()


def _outside_maps(path: Path) -> bool:
    return not store.is_inside(path)


def _profile_input_ids(guid: str) -> tuple[list[int], list[int], list[int]]:
    from gremlin.types import InputType
    from gremlin.ui import input_pairing as pairing

    buttons: list[int] = []
    axes: list[int] = []
    hats: list[int] = []
    for item in pairing.items_for_guid(guid):
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

    for text in pairing.dest_labels_for_item(item):
        add(text)
    if item is None:
        return ""
    for seq in getattr(item, "action_sequences", []) or []:
        root = getattr(seq, "root_action", None)
        if root is None:
            continue
        for action in pairing.walk_actions(root):
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
    for item in pairing.items_for_guid(guid):
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


# Bumped when the profile, its modes or its actions change: the pool rows'
# labels come from the profile (07 RB8).
_profile_generation = 0
_generation_hooked = False


def _profile_changed() -> None:
    global _profile_generation
    _profile_generation += 1


def _hook_profile_generation() -> None:
    global _generation_hooked
    if _generation_hooked:
        return
    _generation_hooked = True
    signal.profileChanged.connect(_profile_changed)
    signal.modesChanged.connect(_profile_changed)
    signal.actionsChanged.connect(_profile_changed)


def chips_key(guid: str) -> str:
    """What the pool rows of chips_for_guid depend on, cheaply: the module
    file (its time and size), the profile's generation and what the device
    reports. The same key: the same rows, so a live press need not read the
    module file and the profile again (07 RB8, S14)."""
    text = str(guid or "").strip()
    if not text:
        return ""
    from gremlin.ui import input_pairing as pairing

    name = pairing.device_name(text)
    stamp = "-"
    if name:
        try:
            stat = store.path_for(name, text).stat()
            stamp = f"{stat.st_mtime_ns}:{stat.st_size}"
        except OSError:
            stamp = "missing"
    return f"{text}|{name}|{stamp}|{_profile_generation}|{_device_input_ids(text)}"


def chips_for_guid(guid: str) -> list[dict]:
    """One chip per input this device's module reports, labeled from its outputs."""
    text = str(guid or "").strip()
    if not text:
        return []
    from gremlin.ui import input_pairing as pairing

    name = pairing.device_name(text)
    doc = store.read(name, text) if name else {}
    claim = doc.get("claim") if isinstance(doc.get("claim"), dict) else {}
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
        self._export_error = ""
        # Counts clipboard changes, so Ctrl+V can tell a picture copied after
        # the last chip copy from an old one.
        self._clipboard_serial = 0
        clipboard = _clipboard()
        if clipboard is not None:
            clipboard.dataChanged.connect(self._clipboard_changed)
        # First: the generation is new before any card asks for its rows.
        _hook_profile_generation()
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
        paper for a PDF. When it fails, exportError() says which file and
        why (07 Q19)."""
        self._export_error = ""
        path = to_local_path(url)
        if save_area(image, width, height, path, fmt, _setup(setup_json)):
            return True
        self._export_error = export_failure(path)
        return False

    @QtCore.Slot(result=str)
    def exportError(self) -> str:
        """Why the last export failed, naming the file ("" after one that
        worked)."""
        return self._export_error

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
        data = QtCore.QByteArray()
        buffer = QtCore.QBuffer(data)
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        saved = image.save(buffer, "PNG")
        buffer.close()
        if not saved:
            return ""
        try:
            store.put_picture_at(dest, bytes(data.data()))
            store.into_library(dest)
        except OSError:
            return ""
        self.imageChanged.emit()
        return store.picture_ref(folder.name, dest.name)

    def _module_slug(self, device_name: str) -> str:
        """The device's module file (slug) by the store's one rule, with the
        id this object was given (a stale id is filtered out there): the
        Button Map document, its pictures, its photo and the photo's safety
        copy all use it."""
        return store.slug_for(device_name, self._device_guid)

    def _file_for(self, device_name: str) -> Path:
        return store.path_of(self._module_slug(device_name))

    def _profile_dir(self, device_name: str) -> Path:
        path = store.pictures_dir_of(self._module_slug(device_name))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _into_library(self, src: Path) -> Path:
        return store.into_library(src)

    def _resolve_existing(self, stored: str) -> Path | None:
        """The file of a stored picture: in the modules folder (only where
        the reference says, 07 S11), or one of the program's own pictures.
        None when it is missing. (No stock photos ship, 07 Q12.)"""
        found = store.find_picture(stored)
        if found is not None:
            return found
        s = (stored or "").strip().replace("\\", "/")
        if not s or s.startswith("file:") or Path(s).is_absolute():
            return None
        installed = _install_root() / s
        if installed.is_file():
            return installed
        return None

    def _pack_assets(self, device_name: str, payload: dict) -> dict:
        """Copies the photo and the map's pictures into the device's folder
        (atomic, through the store) and points the document at them."""
        folder = self._profile_dir(device_name)
        slug = folder.name
        image = str(payload.get("image") or "")
        src = self._resolve_existing(image) if image else None
        if src is None or not src.is_file():
            # No photo (Clear Photo leaves none, 07 Q4), or one that is
            # gone: never another device's or a stock photo (07 S11).
            payload["image"] = ""
        else:
            ext = src.suffix.lower() if src.suffix.lower() in _IMAGE_EXT else ".jpg"
            dest = folder / f"photo{ext}"
            self._put(src, dest)
            payload["image"] = store.picture_ref(slug, dest.name)
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            rel = str(node.get("src") or "")
            if not rel or node.get("shape") != "image":
                continue
            ov = self._resolve_existing(rel)
            if not ov or not ov.is_file():
                continue
            dest = folder / store.safe_picture_name(ov.name, "overlay.png")
            if dest.exists() and dest.resolve() != ov.resolve():
                n = 1
                while dest.exists() and dest.resolve() != ov.resolve():
                    dest = folder / f"{dest.stem}_{n}{dest.suffix}"
                    n += 1
            self._put(ov, dest)
            node["src"] = store.picture_ref(slug, dest.name)
            node.pop("srcUrl", None)
        return payload

    @staticmethod
    def _put(src: Path, dest: Path) -> Path:
        """A picture copied into a device folder (nothing when it is already
        that file)."""
        if dest.resolve() != src.resolve():
            store.put_picture_at(dest, src)
        return dest

    @QtCore.Slot(result=str)
    def exportFolderUrl(self) -> str:
        return _export_dir().as_uri()

    @QtCore.Slot(str, result=str)
    def defaultExportUrl(self, device_name: str) -> str:
        path = _export_dir() / f"{store.own_slug(device_name)}_map.zip"
        return path.as_uri()

    @QtCore.Slot(result=str)
    def packDevices(self) -> str:
        return json.dumps({"ok": True, "devices": _known_pack_devices()})

    @QtCore.Slot(str, result=str)
    def peekPackDevice(self, device_name: str) -> str:
        """Device Pack's export preview: the device, its photo, its modes and
        about how large the pack will be. The size is estimated from the
        files' sizes; the zip is built only by Export (08 S49, GL-196: this
        runs at every device change, on the UI thread)."""
        from gremlin.ui.device_pack import export_refusal, pack_modes, size_text

        name = " ".join(str(device_name or "").split())
        if not name:
            return json.dumps({"ok": False, "error": "Choose a device.", "device": device_name})
        # The file the pack takes (device_pack.assemble's rule).
        match = _match_pack_device(name)
        guid = str(match["guid"]) if match and match.get("guid") else ""
        path = store.path_for(name, guid)
        # None yet, or damaged (08 S51, Q19).
        refused = export_refusal(path)
        doc = {} if refused else store.read_path(path)
        if not doc:
            return json.dumps({
                "ok": False,
                "error": refused or "This device has no module file yet.",
                "device": device_name,
            })
        estimate = path.stat().st_size
        seen: set[Path] = set()
        refs = [str(doc.get("image") or "")]
        refs += [
            str(node.get("src") or "")
            for node in doc.get("nodes") or []
            if isinstance(node, dict) and node.get("shape") == "image"
        ]
        photo = self._resolve_existing(refs[0]) if refs[0] else None
        for ref in refs:
            found = self._resolve_existing(ref) if ref else None
            if found is None or found in seen:
                continue
            seen.add(found)
            try:
                estimate += found.stat().st_size
            except OSError:
                continue
        return json.dumps({
            "ok": True,
            "device": name,
            "photoUrl": photo.as_uri() if photo else "",
            "sizeText": "about " + size_text(estimate),
            "bytes": estimate,
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
        # Through a temporary file, so a failed write never leaves half a
        # zip over an older pack (08 R4); then read back, as Delete Device's
        # pack is.
        try:
            store.write_file(dest, data)
        except Exception as exc:
            trace("SAVE", "Device Pack", "exportPack", dest, "error")
            return json.dumps({"ok": False, "error": str(exc)})
        if not _zip_readable(dest):
            trace("SAVE", "Device Pack", "exportPack", dest, "unreadable")
            return json.dumps({
                "ok": False,
                "error": "The pack was written but could not be read back.",
            })
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
    @QtCore.Slot(bool, result=str)
    def undoPackImport(self, force: bool = False) -> str:
        """Undo Import. A file saved again since the import makes it ask
        first ({"ask": True, "changed": [...]}); force: the user said yes."""
        from gremlin.ui.device_pack import undo_import

        return json.dumps(undo_import(bool(force)))

    @QtCore.Slot()
    def keepPackImport(self) -> None:
        """The last import stays: Undo Import is no longer offered."""
        from gremlin.ui.device_pack import drop_import_undo

        drop_import_undo()

    @QtCore.Slot()
    def dropPackPreview(self) -> None:
        """The Device Pack window closed: its preview pictures go."""
        from gremlin.ui.device_pack import drop_preview

        drop_preview()

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

    @QtCore.Slot(str, result=str)
    def chipsKey(self, guid: str) -> str:
        """chips_key: the pool rows are read again only when it changes."""
        return chips_key(guid)

    @QtCore.Slot(str)
    def setDeviceGuid(self, guid: str) -> None:
        self._device_guid = str(guid or "")

    @QtCore.Slot(str, result=str)
    def moduleFileName(self, device_name: str) -> str:
        """The file name of the module file this device's map opens (its own
        file, so twin sticks stay apart): History's filter (08 Q15)."""
        if not str(device_name or "").strip():
            return ""
        return self._file_for(device_name).name

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
        folder = store.folder() / "cache"
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
        for path in store.module_files():
            if path.stem == own:
                continue
            doc = store.read_path(path)
            if not doc.get("nodes"):
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
        nodes = store.read_path(store.path_of(slug)).get("nodes")
        return json.dumps(nodes) if isinstance(nodes, list) and nodes else ""

    # --- layout templates (File > Templates) ----------------------------------

    def _templates_dir(self) -> Path:
        return store.folder() / "templates"

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

    @QtCore.Slot(str, result=list)
    def templateMissingPictures(self, name: str) -> list:
        """The pictures a template names that are no longer where it says
        (moved or deleted; a template keeps where they are, not the files,
        07 S81): their file names."""
        path = self._template_file(name)
        doc = _read_template(path) if path else None
        if doc is None:
            return []
        missing: list[str] = []
        for node in doc["nodes"]:
            if not isinstance(node, dict) or node.get("shape") != "image":
                continue
            ref = str(node.get("src") or "").strip()
            if not ref or self._resolve_existing(ref) is not None:
                continue
            label = ref.replace("\\", "/").rsplit("/", 1)[-1]
            if label not in missing:
                missing.append(label)
        return missing

    @QtCore.Slot(str, result="QVariantMap")
    def deviceControls(self, guid: str) -> dict:
        """The controls a device has, for "N chips are for controls this
        device does not have" (07 Q8): what it reports when connected, else
        its pool's controls. {"known": False} when nothing is known."""
        text = str(guid or "").strip()
        reported = store.connected_input_ids(text) if text else None
        if reported is not None:
            buttons, axes, hats = (sorted(ids) for ids in reported)
        else:
            rows = chips_for_guid(text) if text else []
            buttons = sorted({r["hwId"] for r in rows if r["kind"] == "btn"})
            axes = sorted({r["hwId"] for r in rows if r["kind"] == "axis"})
            hats = sorted({r["hwId"] for r in rows if r["kind"] == "hat"})
        known = bool(buttons or axes or hats)
        return {"known": known, "btn": buttons, "axis": axes, "hat": hats}

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
        return store.recovery_path(self._module_slug(device_name))

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
            text = store.read_text(path)
            # Not UTF-8 (damaged): shown empty; saving into it is refused.
            self._text = text if text is not None else ""
            trace("READ", "Button Map", "load", path, "ok" if text is not None else "damaged")
        else:
            self._text = ""
            trace("READ", "Button Map", "load", path, "missing")
        persist_log(
            f"Persist map load name={name!r} guid={self._device_guid!r} path={path} bytes={len(self._text)}"
        )
        self.documentChanged.emit()
        return self._text

    def _after_save(self, path: Path) -> None:
        self._path = str(path)
        self._text = store.read_text(path) or ""
        self.pathChanged.emit()
        self.documentChanged.emit()

    @QtCore.Slot(str, str, result=bool)
    def save(self, device_name: str, json_text: str) -> bool:
        name = device_name or self._device_name
        path = self._file_for(name)
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict):
            return False
        payload["kind"] = "control.hardware"
        payload["device"] = name
        payload["space"] = "world"
        payload.update(PAGE_SIZE)
        payload["photo"] = _photo_pose(payload.get("photo"))

        def change(doc: dict) -> None:
            # Runs only once the file is known not to be damaged: a refused
            # save copies no photo or picture (07 S12, GL-079).
            packed = self._pack_assets(name, payload)
            # The Button Map writes its own keys; everything else in the
            # file (claims, names, calibration, Appearance...) stays.
            for key, value in doc.items():
                packed.setdefault(key, value)
            if is_output_name(name):
                packed["direction"] = "dest"
            doc.clear()
            doc.update(packed)

        if not _write_map(path, change):
            return False
        kept = payload.get("claim") if isinstance(payload.get("claim"), dict) else {}
        persist_log(
            f"Persist map save name={name!r} guid={self._device_guid!r} path={path} "
            f"nodes={len(payload.get('nodes') or [])} "
            f"claimButtons={len(kept.get('buttons') or [])} "
            f"claimAxes={len(kept.get('axes') or [])}"
        )
        self._after_save(path)
        self.imageChanged.emit()
        return True

    @QtCore.Slot(str, str, result=bool)
    def saveUi(self, device_name: str, json_text: str) -> bool:
        """Write only the ui block. Do not stamp page size or rewrite nodes.
        With no module file nothing is written: the ui block waits in the
        window until Save (07 S29, S96)."""
        name = device_name or self._device_name
        path = self._file_for(name)
        try:
            incoming = json.loads(json_text)
        except json.JSONDecodeError:
            return False
        if not isinstance(incoming, dict) or not path.is_file():
            return False

        def change(doc: dict) -> None:
            doc["ui"] = incoming.get("ui", doc.get("ui") or {})

        if not _write_map(path, change):
            return False
        persist_log(f"Persist map ui name={name!r} guid={self._device_guid!r} path={path}")
        self._after_save(path)
        return True

    @QtCore.Slot(str, str, result=str)
    def copyOverlay(self, source_url: str, device_name: str) -> str:
        src = to_local_path(source_url)
        if not src.is_file():
            return ""
        ext = src.suffix.lower() or ".png"
        if ext not in _IMAGE_EXT:
            ext = ".png"
        folder = self._profile_dir(device_name)
        dest = folder / store.safe_picture_name(src.stem + ext, src.name)
        n = 1
        while dest.exists() and dest.resolve() != src.resolve():
            dest = folder / f"{src.stem}_{n}{ext}"
            n += 1
        try:
            store.into_library(src)
            self._put(src, dest)
        except OSError:
            return ""
        self.imageChanged.emit()
        return store.picture_ref(folder.name, dest.name)

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
        """Makes a picture the device's photo: photo.<ext> in its folder (the
        window's safety copy keeps the old one for Cancel); its reference
        for the window's Save. A damaged module file is refused before
        any photo file is touched (03 S64, GL-070). The device's own photo
        again changes nothing: no library copy, no write (03 Q3, GL-089)."""
        src = self._local_image(source_url)
        if src is None:
            return ""
        ext = src.suffix.lower() or ".jpg"
        if ext not in _IMAGE_EXT:
            ext = ".jpg"
        name = device_name or self._device_name
        slug = self._module_slug(name)
        path = store.path_of(slug)
        reason = store.damage_of(path)
        if reason:
            trace("SAVE", "Button Map", "copyImage", path, "damaged")
            module_file.report_refused(module_file.ModuleFileDamaged(path, reason))
            return ""
        folder = store.pictures_dir_of(slug)
        dest = folder / f"photo{ext}"
        same = dest.is_file() and dest.resolve() == src.resolve()
        if not same:
            try:
                store.into_library(src)
                store.put_picture_at(dest, src)
            except OSError:
                dest = folder / f"photo_{src.stem}{ext}"
                try:
                    store.put_picture_at(dest, src)
                except OSError:
                    return ""
            others = [
                p
                for p in folder.glob("photo.*")
                if p.is_file() and p.resolve() != dest.resolve()
            ]
            try:
                store.remove_picture_files(others)
            except OSError:
                pass
            trace("SAVE", "Button Map", "copyImage", dest, "ok")
        rel = store.picture_ref(slug, dest.name)
        # The module file's "image" is written by the window's Save, not
        # here: nothing in the module file or History until Save (07 Q2).
        persist_log(f"Persist photo name={name!r} guid={self._device_guid!r} path={path} image={rel!r}")
        self._path = str(path)
        self.pathChanged.emit()
        self.documentChanged.emit()
        self.imageChanged.emit()
        return rel

    @QtCore.Slot(str, result=str)
    def photoCopyUrl(self, device_name: str) -> str:
        """A lasting copy of the device's photo as it is now (in the
        library, not copied again when it is there), so Undo can make it
        the photo again (07 Q3); "" when it has no photo."""
        slug = self._module_slug(device_name or self._device_name)
        pictures = store.pictures_dir_of(slug)
        found = (
            sorted(p for p in pictures.glob("photo.*") if p.is_file())
            if pictures.is_dir()
            else []
        )
        if not found:
            return ""
        try:
            return store.into_library(found[0]).as_uri()
        except OSError:
            return ""

    @QtCore.Slot(str, result=bool)
    def clearImage(self, device_name: str) -> bool:
        name = device_name or self._device_name
        if not store.remove_pictures(name, self._device_guid):
            return False
        self.imageChanged.emit()
        return True

    @QtCore.Slot(str, result=int)
    def removeUnusedPictures(self, device_name: str) -> int:
        """An edit ended (saved or cancelled): pictures it added to the
        device's folder that no map uses go (07 Q11, GL-273). How many."""
        slug = self._module_slug(device_name or self._device_name)
        unused = unused_pictures(slug)
        removed = 0
        for path in unused:
            try:
                store.remove_picture_files([path])
            except OSError:
                continue
            removed += 1
            trace("SAVE", "Button Map", "removeUnusedPictures", path, "removed")
        return removed

    # Photo safety copy for one Button Map editing session. Choose
    # background... and Clear image change the photo files at once; Cancel
    # puts the session's starting photo (files and the module file's
    # "image") back, Save drops the copy.

    def _photo_files(self, slug: str) -> list[Path]:
        return store.photo_files(slug)

    @staticmethod
    def _stash_dir(slug: str, owner: str = "") -> Path:
        return store.photo_stash_dir(slug, owner)

    @QtCore.Slot(str)
    def stashPhoto(self, device_name: str) -> None:
        """Keep the current photo before this session first changes it."""
        self.stashPhotoFor(device_name, "")

    @QtCore.Slot(str, str)
    def stashPhotoFor(self, device_name: str, owner: str) -> None:
        """stashPhoto for one window's session (owner: "" the Button Map,
        "setup" Module Setup), so two windows don't share one safety copy."""
        slug = self._module_slug(device_name or self._device_name)
        stash = self._stash_dir(slug, owner)
        if (stash / "manifest.json").is_file():
            return  # This session's starting photo is already kept.
        try:
            stash.mkdir(parents=True, exist_ok=True)
            files = []
            for i, p in enumerate(self._photo_files(slug)):
                kept = stash / f"{i}{p.suffix}"
                shutil.copy2(p, kept)
                files.append({"kept": kept.name, "to": str(p.relative_to(store.folder()))})
            loaded = read_doc(store.path_of(slug))
            image = loaded.get("image") if loaded is not None else None
            (stash / "manifest.json").write_text(
                json.dumps({"files": files, "image": image}), encoding="utf-8"
            )
        except OSError:
            persist_log(f"Persist photo stash failed slug={slug!r}")

    @QtCore.Slot(str, result=bool)
    def restorePhoto(self, device_name: str) -> bool:
        """Put the session's starting photo back. False when none was kept."""
        return self.restorePhotoFor(device_name, "")

    @QtCore.Slot(str, str, result=bool)
    def restorePhotoFor(self, device_name: str, owner: str) -> bool:
        """restorePhoto for one window's session (see stashPhotoFor)."""
        slug = self._module_slug(device_name or self._device_name)
        stash = self._stash_dir(slug, owner)
        manifest = stash / "manifest.json"
        if not manifest.is_file():
            return False
        try:
            kept = json.loads(manifest.read_text(encoding="utf-8"))
            store.remove_picture_files(self._photo_files(slug))
            for entry in kept.get("files", []):
                store.put_picture_at(store.folder() / entry["to"], stash / entry["kept"])
            doc_path = store.path_of(slug)
            if doc_path.is_file():
                # As copyImage: a damaged file is left alone (and said).

                def change(doc: dict) -> bool:
                    before = doc.get("image")
                    if kept.get("image") is None:
                        doc.pop("image", None)
                    else:
                        doc["image"] = kept["image"]
                    return doc.get("image") != before

                store.update_path(doc_path, change, "Button Map")
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
        return self.hasPhotoStashFor(device_name, "")

    @QtCore.Slot(str, str, result=bool)
    def hasPhotoStashFor(self, device_name: str, owner: str) -> bool:
        slug = self._module_slug(device_name or self._device_name)
        return (self._stash_dir(slug, owner) / "manifest.json").is_file()

    @QtCore.Slot(str)
    def dropPhotoStash(self, device_name: str) -> None:
        """The session was saved: its starting photo is no longer needed."""
        self.dropPhotoStashFor(device_name, "")

    @QtCore.Slot(str, str)
    def dropPhotoStashFor(self, device_name: str, owner: str) -> None:
        slug = self._module_slug(device_name or self._device_name)
        shutil.rmtree(self._stash_dir(slug, owner), ignore_errors=True)

    @QtCore.Slot(result=str)
    def imagesFolderUrl(self) -> str:
        """Where Choose Photo and Import Picture open: the last folder a
        picture was chosen from, else the user's Pictures folder. No folder
        is made, never in the program's own folder (07 Q13)."""
        return QtCore.QUrl.fromLocalFile(str(_picture_folder())).toString()

    @QtCore.Slot(str)
    def notePictureFolder(self, file_url: str) -> None:
        """A picture was chosen: its folder is where the next one opens."""
        try:
            folder = to_local_path(str(file_url or "")).parent
        except Exception:
            return
        if not folder.is_dir():
            return
        try:
            _picture_folder_config().set(*_PICTURE_FOLDER, str(folder))
        except Exception:
            persist_log(f"Persist picture folder failed folder={folder}")

    @QtCore.Slot(str, result=str)
    def imageUrl(self, stored: str) -> str:
        found = self._resolve_existing(stored)
        if found and found.is_file():
            return found.as_uri()
        s = (stored or "").strip().replace("\\", "/")
        if not s:
            return ""
        if s.startswith("file:") or s.startswith("qrc:"):
            return s
        return ""

    @QtCore.Slot(str, result=str)
    @QtCore.Slot(str, str, result=str)
    def profilePhotoUrl(self, device_name: str, guid: str | None = None) -> str:
        """The device's photo; with guid, for the device with that id (it
        becomes this object's device)."""
        if guid is not None:
            self.setDeviceGuid(guid)
        # The folder of the file the Button Map opens (a renamed stick's
        # old file, by the store's one rule with this object's id).
        slug = self._module_slug(device_name)
        own = store.pictures_dir_of(slug)
        for p in sorted(own.glob("photo.*")):
            if p.is_file():
                return p.as_uri() + f"?t={int(p.stat().st_mtime_ns)}"
        # Read only: asking for the photo doesn't change this object's
        # document (07 S11, GL-271).
        doc = store.read_path(store.path_of(slug))
        found = self._resolve_existing(str(doc.get("image") or ""))
        if found and found.is_file():
            try:
                # A picture saved for another device lives in that device's folder.
                if found.resolve().parent != own.resolve():
                    found = None
            except OSError:
                found = None
            if found is not None:
                return found.as_uri() + f"?t={int(found.stat().st_mtime_ns)}"
        # No photo: none, never another device's (07 S11; no stock photos
        # ship, 07 Q12).
        return ""

    @QtCore.Property(str, notify=pathChanged)
    def path(self) -> str:
        return self._path

    @QtCore.Property(str, notify=documentChanged)
    def text(self) -> str:
        return self._text
