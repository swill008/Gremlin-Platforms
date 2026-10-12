# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The module file store: the one owner of each device's folder and of
every change to module files and their pictures (system-maps map 1, gap
list GL-067, D-03-DEVICE-FOLDERS).

One folder per device in the modules folder, named after the device's
shown name: device.json (its id and shown name), module.json (the module
file), recovery.json (the Device Mapping Editor's recovery copy), pictures/ and
imported/ (03 S128-S134). Callers pass a device's name and id and never
build paths:

- where:    device_dir, ensure_device_dir, module_file, pictures_dir,
            recovery_path, imported_dir, edit_temp_dir, dir_of_id,
            device_dirs, id_key, folder_name_for, shown_name_of, card_key
- reading:  read, read_path, damage, exists, find_picture, module_files
- writing:  update (load, refuse a damaged file, change, write),
            replace (whole file: import, Device Pack, Undo, Restore),
            write_json / write_text (a whole document as given)
- pictures: picture_ref, normal_ref, put_picture, named_refs,
            remove_unused_pictures, copy_pictures
- the device's background picture (07 S157): visible_background,
            makes_device_photo, background_key, device_photo_path,
            device_photo_key, device_photo_current, write_device_photo,
            remove_device_photo, shown_photo_ref
- an edit:  begin_edit, stage_picture, stage_copied, commit_edit,
            cancel_edit, recover_edit (its temporary folder in cache)
- folders:  rename_device_dir (an alias set), sync_dir_name (after a scan)
- deleting: delete (Delete File / Delete Device), move_aside (Start Fresh),
            delete_path
- import:   import_choices, import_file, can_undo_file_import,
            undo_file_import, drop_file_import_undo (Module Setup's
            "Import from", its Undo tied to the device and window)
- Device Bindings layout: read_layout, write_layout, friendly_name,
            set_friendly_name (the "layout" key: groups, order; names are
            the claim's friendly names, CF-Q1, CF-Q8); the page's unsaved
            changes: set_pending_layout, layout_for, has_pending,
            save_pending (File > Save Profile), discard_pending (CS1)

Rules kept here:
- one lookup rule (device_dir): the folder whose device.json holds the
  device's id, else a folder named after it with no id or its own, else
  the folder it would get; a stale id is filtered out first (guid_filter);
- a lookup by name only is for vJoy, Keyboard, OSC and the program's own
  devices; a stick looked up without its id is logged (decision F4);
- a folder is named after the shown name (folder_name_for); another
  device of the same name gets " (2)" by id (S132); renaming a device
  renames its folder, refused while a file in it is open (S131);
- a module file names its pictures "pictures/<file>" in its own folder;
  nothing is shared between devices (S133); a save removes the pictures
  nothing names (07 S106);
- a damaged file is never written over (ModuleFileDamaged), except by a
  restore that asks for it (force);
- every write is atomic (module_file_io.write_bytes), pictures too;
- History is hooked here only: writes call history_modules.note_write,
  deletes and Start Fresh go through history_modules.deleting;
- a saved module file reaches Run's output claims at once (output.refresh);
- a saved, deleted or moved-aside module file is announced:
  signal.moduleFilesChanged, once per burst, on the main thread
  (notify_module_files, D-01-OWNER-NOTICES).

registry stays the read-only index of module files; module_file the
atomic writer and the damaged-file rule. Main thread only (the folder
index is locked: Run's threads read module files through registry).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from gremlin.modules import ids, registry
from gremlin.modules import module_file as module_file_io
from gremlin.modules.claim import claim_ids
from gremlin.modules.ids import guid_key, stored_guid_key
from gremlin.modules.registry import plain_slug
from gremlin.notice import BurstNotice

PICTURE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

syslog = logging.getLogger("system")


# --- where ---------------------------------------------------------------------

# One folder per device (D-03-DEVICE-FOLDERS):
# <modules>/<Device Folder>/device.json, module.json, recovery.json,
# pictures/<file>, imported/...
MODULE_FILE = "module.json"
ID_FILE = "device.json"
RECOVERY_FILE = "recovery.json"
PICTURES = "pictures"
IMPORTED = "imported"
STATE_FILE = "state.json"
# Folders of the program's own, never a device's (case ignored).
RESERVED = frozenset(
    {"cache", "templates", "library", "recovery", "imported", "backup"}
)
_WINDOWS_RESERVED = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in range(1, 10)}
    | {f"lpt{n}" for n in range(1, 10)}
)
_UNSAFE = set('\\/:*?"<>|')
NAME_LIMIT = 80


def folder() -> Path:
    """The modules folder (Options > Folders). Tests point it elsewhere by
    patching this function."""
    from gremlin.util import modules_dir

    return Path(modules_dir())


def card_key(device_name: str) -> str:
    """A device's Home card key (order, hidden, sizes, stacks): its own
    name's slug, not its folder's (decision F2: changing it would reset
    everyone's card layout)."""
    return plain_slug(device_name) or "device"


def _same_name(left: str, right: str) -> bool:
    return (
        " ".join(str(left or "").split()).casefold()
        == " ".join(str(right or "").split()).casefold()
    )


def guid_filter(device_name: str, guid: str) -> str:
    """guid when it belongs to device_name; "" for a stale id: one that a
    connected device of another name has, or another id while a device of
    this name is connected. A stale id must not select another device's
    folder (03 S2, S9). An id of a device that isn't connected is kept."""
    given = stored_guid_key(guid)
    if not given:
        return ""
    names = {
        name
        for name, found in registry.connected_names().items()
        if guid_key(given) in found
    }
    if names:
        wanted = " ".join(str(device_name or "").split()).casefold()
        return str(guid) if wanted in names else ""
    owned = registry.guid_for_name(device_name)
    if owned and guid_key(owned) != guid_key(given):
        return ""
    return str(guid)


# Not a device class (03 S90b): a slug-PREFIX rule for which devices may be
# looked up by name only without a note ("keyboard_stick" and
# "xbox_wireless_controller" count too).
_NAME_ONLY_OK = ("vjoy", "keyboard", "osc", "logical_device", "xbox")
_told_name_only: set[str] = set()


def _note_name_only(device_name: str) -> None:
    """A connected stick looked up by its name alone: twins share a name, so
    each must be looked up by its id (decision F4). Logged once per name."""
    slug = plain_slug(device_name)
    if not slug or slug.startswith(_NAME_ONLY_OK):
        return
    if registry.is_output_name(device_name):
        return
    if slug in _told_name_only:
        return
    if not any(_same_name(name, device_name) for name in registry.connected_names()):
        return  # not connected: there is no id to look it up by
    _told_name_only.add(slug)
    syslog.warning(f"Folder of {device_name} looked up without its device id")


def _kind(device_name: str, guid: str = "") -> str:
    from gremlin.modules import device_class

    try:
        return device_class.device_kind(guid or None, device_name)
    except Exception:  # noqa: BLE001 - no device list yet
        return ""


def id_key(device_name: str, guid: str = "") -> str:
    """The key a device's folder is found by (device.json "id"): the
    device's id; the fixed id of Keyboard, OSC, the Logical Device and the
    program's Xbox pad; "name:<slug>" for a device known by its name only
    (vJoy N: "name:vjoy_1")."""
    from gremlin.modules import device_class

    kind = _kind(device_name, guid)
    slug = plain_slug(device_name)
    if device_class.is_input_kind(kind) or (
        kind == "xbox"
        and (
            guid_key(guid) == guid_key(ids.XBOX)
            or slug in ("", "xbox", "xbox_360_controller")
        )
    ):
        fixed = device_class.guid_of_kind(kind)
        return stored_guid_key(fixed)
    if device_class.is_output_kind(kind) or registry.is_output_name(device_name):
        return f"name:{slug}" if slug else ""
    key = stored_guid_key(guid)
    if key:
        return key
    return f"name:{slug}" if slug else ""


def _norm(key: str) -> str:
    """An id key compared: "name:" keys as they are, ids by guid_key."""
    text = str(key or "").strip()
    if not text:
        return ""
    if text.lower().startswith("name:"):
        return "name:" + plain_slug(text[5:])
    return guid_key(stored_guid_key(text))


def _key_dir(key: str) -> str:
    """An id key as a folder name (":" can't be in one)."""
    return (str(key or "").replace(":", "_").strip() or "device")[:NAME_LIMIT]


def folder_name_for(shown: str) -> str:
    """A device's folder name from its shown name: spaces collapsed, each
    character a file name can't hold becomes "_", cut to 80 characters, a
    reserved name (CON, LPT1, cache, templates, ...) gets a trailing "_".
    The shown name itself is never changed (03 S128)."""
    text = " ".join(str(shown or "").split())
    out = "".join("_" if ch in _UNSAFE or ord(ch) < 32 else ch for ch in text)
    out = out[:NAME_LIMIT]
    out = _fix_end(out)
    if not out:
        return "Device"
    return _unreserved(out)


def _fix_end(text: str) -> str:
    """A trailing "." or space becomes "_" (Windows drops them)."""
    if text and text[-1] in ". ":
        return text[:-1] + "_"
    return text


def _unreserved(text: str) -> str:
    if text.lower() in _WINDOWS_RESERVED or text.lower() in RESERVED:
        return (text[: NAME_LIMIT - 1] + "_") if len(text) >= NAME_LIMIT else text + "_"
    return text


def _numbered(base: str, number: int) -> str:
    """base with " (n)", base cut so the whole fits in 80 characters."""
    suffix = f" ({number})"
    return _fix_end(base[: NAME_LIMIT - len(suffix)]) + suffix


def shown_name_of(device_name: str, guid: str = "") -> str:
    """The name the program shows for a device (its folder is named after
    it): the user's alias, else the twin name ("<name> (2)"), else its
    name; Keyboard, OSC, Logical Device and the Xbox pad their fixed names;
    a vJoy module its own "vJoy N"."""
    from gremlin.modules import device_class

    name = " ".join(str(device_name or "").split())
    kind = _kind(name, guid)
    if device_class.is_input_kind(kind):
        return device_class.display_name(kind)
    if kind == "xbox" and id_key(name, guid) == stored_guid_key(ids.XBOX):
        return device_class.display_name(kind)
    if device_class.is_output_kind(kind) or registry.is_output_name(name):
        return name or "Device"
    if not stored_guid_key(guid):
        return name or "Device"
    base = name
    try:
        import uuid as _uuid

        from gremlin import device_initialization

        uid = _uuid.UUID(str(guid).strip().strip("{}"))
        if uid in device_initialization._joystick_devices:
            base = device_initialization.shown_name(uid) or name
    except Exception:  # noqa: BLE001 - not a uuid, or no device list yet
        pass
    return _home_label(base, guid, _twin_names()) or name or "Device"


def _read_json(path: Path) -> dict:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return {}
    return doc if isinstance(doc, dict) else {}


def dir_id(path: Path) -> str:
    """The id key a device folder holds: device.json's "id", else (missing
    or damaged) its module.json's boundGuidLocal; "" when neither has one."""
    path = Path(path)
    found = str(_read_json(path / ID_FILE).get("id") or "").strip()
    if found:
        return found
    return stored_guid_key(_read_json(path / MODULE_FILE).get("boundGuidLocal") or "")


def _device_folders(base: Path | None = None) -> list[Path]:
    """Every device folder (reserved folders left out), by name."""
    base = folder() if base is None else base
    if not base.is_dir():
        return []
    try:
        found = [
            p for p in base.iterdir() if p.is_dir() and p.name.lower() not in RESERVED
        ]
    except OSError:
        return []
    return sorted(found, key=lambda p: p.name.lower())


# The index: (folder, its mtime, its folder names) -> {normalized id key: folder}.
_dirs_cache: tuple[tuple, dict[str, Path]] | None = None
_dirs_lock = threading.RLock()
_told_duplicate: set[str] = set()


def _dirs_changed() -> None:
    """A folder was made, renamed or deleted, or a device.json changed: the
    index is built again at the next lookup."""
    global _dirs_cache
    with _dirs_lock:
        _dirs_cache = None


def _index() -> dict[str, Path]:
    global _dirs_cache
    base = folder()
    try:
        stamp: tuple = (str(base), base.stat().st_mtime_ns)
    except OSError:
        stamp = (str(base), 0)
    with _dirs_lock:
        folders = _device_folders(base)
        stamp = stamp + (tuple(p.name for p in folders),)
        if _dirs_cache is not None and _dirs_cache[0] == stamp:
            return _dirs_cache[1]
        index: dict[str, Path] = {}
        for path in folders:
            key = _norm(dir_id(path))
            if not key:
                continue
            held = index.get(key)
            if held is None:
                index[key] = path
                continue
            # Two folders with one id (copied by hand): the one named after
            # the device wins, else the first by name (validate.py says it).
            shown = str(_read_json(path / ID_FILE).get("name") or "")
            if shown and path.name == folder_name_for(shown) and held.name != path.name:
                held_shown = str(_read_json(held / ID_FILE).get("name") or "")
                if not (held_shown and held.name == folder_name_for(held_shown)):
                    index[key] = path
            if key not in _told_duplicate:
                _told_duplicate.add(key)
                syslog.warning(
                    f"Device folders {held.name} and {path.name} have the same id"
                )
        _dirs_cache = (stamp, index)
        return index


def device_dirs() -> dict[str, Path]:
    """{id key: device folder} for every folder with an id."""
    return dict(_index())


def dir_of_id(guid_or_key: str) -> Path | None:
    """The folder of the device with this id (or "name:<slug>" key); None
    when it has none. Never by name: twins share one (10 S41)."""
    key = _norm(guid_or_key)
    if not key:
        return None
    return _index().get(key)


def _named_dir(name: str) -> Path | None:
    """The existing device folder called name (case ignored)."""
    want = name.casefold()
    for path in _device_folders():
        if path.name.casefold() == want:
            return path
    return None


def _may_use(path: Path, key: str) -> bool:
    """A folder of the device's name may be used: it has no id, the same
    one, or one side is known by name only (a stick's folder saved before
    it was plugged in)."""
    held = _norm(dir_id(path))
    want = _norm(key)
    if not held or not want or held == want:
        return True
    return held.startswith("name:") != want.startswith("name:")


def unique_name(base: str, key: str, keep: Path | None = None) -> str:
    """base when no other device's folder has it, else "base (2)", (3)...:
    the first free (03 S132). keep: a folder that may keep its name."""
    number = 1
    name = base
    while True:
        found = _named_dir(name)
        if found is None or (keep is not None and found == keep):
            return name
        if _norm(dir_id(found)) == _norm(key) and _norm(key):
            return name
        number += 1
        name = _numbered(base, number)


def names_for_new(devices: list[tuple[str, str]]) -> dict[str, str]:
    """Folder names for several new devices at once (the one-time move):
    devices [(id key, shown name)] -> {id key: folder name}. Existing
    folders keep their names; among the new ones of one name the lowest id
    key gets the plain name, the others " (2)", (3)... (03 S132)."""
    taken = {p.name.casefold() for p in _device_folders()}
    out: dict[str, str] = {}
    for key, shown in sorted(devices, key=lambda d: (_norm(d[0]), d[1])):
        base = folder_name_for(shown)
        name, number = base, 1
        while name.casefold() in taken:
            number += 1
            name = _numbered(base, number)
        taken.add(name.casefold())
        out[key] = name
    return out


def _lookup_guid(device_name: str, guid: str) -> str:
    """The id a lookup uses: the given one with a stale id filtered out;
    with none, a connected device's of that name."""
    if not stored_guid_key(guid):
        _note_name_only(device_name)
        if registry.is_output_name(device_name):
            return ""
        return registry.guid_for_name(device_name)
    return guid_filter(device_name, guid)


def _own_dir(device_name: str, guid: str) -> Path | None:
    """The folder whose device.json holds exactly this id and this device's
    name. It is the device's own, even when guid_filter would call the id
    stale: an unplugged twin while the other twin of its name is connected
    must still find its own folder, never the other's (10 S41)."""
    if not stored_guid_key(guid):
        return None
    found = _index().get(_norm(id_key(device_name, guid)))
    if found is None:
        return None
    held = str(_read_json(found / ID_FILE).get("name") or "")
    names = (device_name, shown_name_of(device_name, guid))
    return found if any(_same_name(held, name) for name in names) else None


def device_dir(device_name: str, guid: str = "") -> Path:
    """The device's folder (it may not exist yet): found by its id first,
    then a folder named after it whose id is empty or its own, else the
    folder it would get (03 S1, S4, S130)."""
    exact = _own_dir(device_name, guid)
    if exact is not None:
        return exact
    filtered = _lookup_guid(device_name, guid)
    key = id_key(device_name, filtered)
    found = _index().get(_norm(key))
    if found is not None:
        return found
    shown = folder_name_for(shown_name_of(device_name, filtered))
    for name in dict.fromkeys((shown, folder_name_for(device_name))):
        path = _named_dir(name)
        if path is not None and _may_use(path, key):
            return path
    return folder() / unique_name(shown, key)


def _write_id(path: Path, key: str, shown: str) -> None:
    doc = {"format": 1, "id": key, "name": shown}
    module_file_io.write_bytes(
        Path(path) / ID_FILE, (json.dumps(doc, indent=2) + "\n").encode("utf-8")
    )
    _dirs_changed()


def ensure_device_dir(device_name: str, guid: str = "") -> Path:
    """device_dir, made if missing, with its device.json (id and shown
    name). Every writer calls it before writing into a device's folder.
    Raises OSError."""
    filtered = _lookup_guid(device_name, guid)
    path = device_dir(device_name, guid)
    key = id_key(device_name, filtered)
    held = _read_json(path / ID_FILE)
    held_id = str(held.get("id") or "").strip()
    new_id = held_id
    if not held_id or (held_id.startswith("name:") and not key.startswith("name:")):
        new_id = key
    shown = str(held.get("name") or "") or shown_name_of(device_name, filtered)
    if not path.is_dir() or new_id != held_id or not held:
        path.mkdir(parents=True, exist_ok=True)
        _write_id(path, new_id, shown)
    return path


def module_file_in(path: Path) -> Path:
    """<device folder>/module.json."""
    return Path(path) / MODULE_FILE


def module_file(device_name: str, guid: str = "") -> Path:
    """The device's module file (it may not exist: "(not saved yet)")."""
    return module_file_in(device_dir(device_name, guid))


def pictures_dir(device_name: str, guid: str = "") -> Path:
    """<device folder>/pictures: its photo and map pictures."""
    return device_dir(device_name, guid) / PICTURES


def recovery_path(device_name: str, guid: str = "") -> Path:
    """The Device Mapping Editor's recovery copy of unsaved edits (07 S32)."""
    return device_dir(device_name, guid) / RECOVERY_FILE


def imported_dir(device_name: str, guid: str = "") -> Path:
    """<device folder>/imported: the previous files imports keep (03 S58)."""
    return device_dir(device_name, guid) / IMPORTED


def edit_temp_dir(device_name: str, guid: str = "", owner: str = "") -> Path:
    """An edit's temporary folder (07 S107): cache/edit/<id key> for the
    Device Mapping Editor, cache/edit-<owner>/<id key> for another window. Keyed by
    id, so a rename can't race it and export, History and the Library never
    see it."""
    key = id_key(device_name, _lookup_guid(device_name, guid))
    base = folder() / "cache" / ("edit" + (f"-{owner}" if owner else ""))
    return base / _key_dir(key)


def templates_dir() -> Path:
    """<modules>/templates: one folder per template (07 S110)."""
    return folder() / "templates"


def template_dir(name: str) -> Path:
    """A template's folder (template.json and pictures/)."""
    return templates_dir() / folder_name_for(name)


def photo_files(device_name: str, guid: str = "") -> list[Path]:
    """The device photo's files: pictures/photo.<ext> and photo_<name>.<ext>."""
    pictures = pictures_dir(device_name, guid)
    if not pictures.is_dir():
        return []
    return [
        p
        for pattern in ("photo.*", "photo_*")
        for p in sorted(pictures.glob(pattern))
        if p.is_file()
    ]


def is_inside(path: Path) -> bool:
    """True when path is in the modules folder (or below it)."""
    try:
        Path(path).resolve().relative_to(folder().resolve())
    except (ValueError, OSError):
        return False
    return True


# --- reading -------------------------------------------------------------------


def read_path(path: Path) -> dict:
    """A module file's content; {} when it is missing or damaged."""
    return registry.read_doc(Path(path)) or {}


def read(device_name: str, guid: str = "") -> dict:
    """The device's module file; {} when it is missing or damaged."""
    return read_path(module_file(device_name, guid))


def read_text(path: Path) -> str | None:
    """A module file's text as it is on disk; None when it is missing or not
    UTF-8 (damaged)."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def damage(device_name: str, guid: str = "") -> str:
    """Why the device's module file can't be read, or "" (missing or fine)."""
    return module_file_io.damage_reason(module_file(device_name, guid))


def damage_of(path: Path) -> str:
    """damage() for a path the store gave out."""
    return module_file_io.damage_reason(Path(path))


def exists(device_name: str, guid: str = "") -> bool:
    return module_file(device_name, guid).is_file()


def module_files() -> list[Path]:
    """Every device's module file (<folder>/module.json), by folder name."""
    return [
        path / MODULE_FILE
        for path in _device_folders()
        if (path / MODULE_FILE).is_file()
    ]


def _local_path(text: str) -> Path:
    """A file: URL (or a plain path) as a local path; Path() when it names no
    local file. (The modules package doesn't use the UI's helper.)"""
    from urllib.parse import unquote, urlparse
    from urllib.request import url2pathname

    text = str(text or "").strip()
    if not text.lower().startswith("file:"):
        return Path(text) if text else Path()
    parts = urlparse(text)
    if parts.netloc and parts.netloc.lower() != "localhost":
        return Path(url2pathname(f"//{parts.netloc}{parts.path}"))
    local = url2pathname(unquote(parts.path)) if parts.path else ""
    return Path(local) if local else Path()


# --- writing -------------------------------------------------------------------


def _text_of(data: bytes) -> str | None:
    try:
        return data.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return None


def _send_module_files() -> None:
    from gremlin.signal import signal

    signal.moduleFilesChanged.emit()


_module_files = BurstNotice(_send_module_files)


def notify_module_files() -> None:
    """A module file was saved, deleted or moved aside:
    signal.moduleFilesChanged goes out once for a burst, on the main
    thread (D-01-OWNER-NOTICES). Any thread may call it."""
    _module_files.notify()


def _saved() -> None:
    """A module file changed: Run's output claims take effect at once (03
    S36, 06 S53), not after the output layer's one-second cache, and every
    page showing module files is told."""
    try:
        from gremlin.modules import output

        output.refresh()
    except Exception:  # noqa: BLE001 - a refresh never stops a save
        syslog.exception("Output claims could not be re-read after a save")
    notify_module_files()


def _is_module_file(path: Path) -> bool:
    from gremlin import history_modules

    return history_modules.is_module_file(path)


def _write(path: Path, data: bytes, text: str | None = None) -> None:
    """The one writer: atomic, with History for a module file (other files,
    such as the backups in imported, are not kept). Raises OSError; a write
    that failed is no History entry (08 S13)."""
    from gremlin import history_modules

    path = Path(path)
    is_module = _is_module_file(path)
    old = history_modules.text_before(path) if is_module else None
    if is_module:
        # The pictures it names now, before anything replaces them (GL-082).
        history_modules.before_change(path)
    held = _held_parts_of(path) if is_module else {}
    module_file_io.write_bytes(path, data)
    if not is_module:
        return
    if text is None:
        text = _text_of(data)
    if text is not None:
        history_modules.note_write(path, text, old)
        _sync_id_file(path, text)
    _saved()
    if held:
        _drop_replaced(held, _parts_of_text(text))


def _sync_id_file(path: Path, text: str) -> None:
    """device.json follows the module file: made when missing, and its id
    set to a non-empty boundGuidLocal that differs (the lookup authority)."""
    try:
        doc = json.loads(text)
    except (ValueError, RecursionError):
        doc = None
    doc = doc if isinstance(doc, dict) else {}
    bound = stored_guid_key(doc.get("boundGuidLocal") or "")
    id_path = Path(path).parent / ID_FILE
    held = _read_json(id_path)
    held_id = str(held.get("id") or "")
    if held and (not bound or _norm(held_id) == _norm(bound)):
        return
    shown = str(held.get("name") or doc.get("device") or Path(path).parent.name)
    try:
        _write_id(Path(path).parent, bound or held_id, shown)
    except OSError:
        syslog.warning(f"{id_path} could not be written")


def write_file(path: Path, data: bytes) -> None:
    """Writes any file atomically (History keeps a module file). module_file's
    text writers forward module files here, so History is hooked in one
    place. For a module file, callers use update or replace."""
    _write(Path(path), data)


def _doc_bytes(doc: dict) -> tuple[bytes, str]:
    text = json.dumps(doc, indent=2) + "\n"
    return module_file_io.encode(text), text


def update_path(
    path: Path,
    change: Callable[[dict], object],
    who: str,
    *,
    report: bool = True,
) -> bool:
    """Reads the module file at path fresh, lets change(doc) edit it in place
    and writes it back. A damaged file is refused before change() runs (so
    no picture is touched, 07 S12), said in the error dialog unless report
    is False, and left untouched. change() returning False writes nothing.
    True when written; raises OSError when the write failed."""
    path = Path(path)
    try:
        doc = module_file_io.load_for_update(path)
    except module_file_io.ModuleFileDamaged as damaged:
        registry.trace("READ", who, "update", path, "damaged")
        if report:
            module_file_io.report_refused(damaged)
        return False
    if change(doc) is False:
        return False
    data, text = _doc_bytes(doc)
    try:
        _write(path, data, text)
    except OSError:
        registry.trace("SAVE", who, "update", path, "error")
        raise
    registry.trace("SAVE", who, "update", path, "ok")
    return True


def update(
    device_name: str,
    guid: str,
    change: Callable[[dict], object],
    who: str,
    *,
    report: bool = True,
) -> bool:
    """update_path on the device's module file (its folder is made on the
    first write)."""

    def made(doc: dict) -> object:
        result = change(doc)
        if result is not False:
            ensure_device_dir(device_name, guid)
        return result

    return update_path(module_file(device_name, guid), made, who, report=report)


def _reload_logical_device(path: Path) -> None:
    """After the Logical Device's module file was replaced (Restore, Import,
    Undo, History Restore), the Logical Device is read from it again
    (D-04-LD-FILE). Its own saves don't come here."""
    from gremlin import logical_device_file

    try:
        if Path(path).resolve() != logical_device_file.path().resolve():
            return
    except OSError:
        return
    try:
        warnings = logical_device_file.load()
    except Exception:  # noqa: BLE001 - the file is written; say it, go on
        syslog.exception("Logical Device: reload after %s failed", path)
        return
    # Screens: the Logical page drops its Undo steps and redraws.
    from gremlin.signal import signal

    if warnings:
        # AD1: the controls that couldn't be read are said, as at open.
        signal.showNotification.emit("Logical Device", "\n".join(warnings))

    signal.logicalDeviceReloaded.emit()
    signal.logicalDeviceModified.emit()


def _reload_osc(path: Path) -> None:
    """After OSC's module file was replaced (Restore, Import, Undo, History
    Restore), OSC's rows and server settings are read from it again
    (D-09-OSC-FILE). Its own saves don't come here."""
    from gremlin import osc_device_file

    try:
        if Path(path).resolve() != osc_device_file.path().resolve():
            return
    except OSError:
        return
    try:
        osc_device_file.load()
        warnings = list(getattr(osc_device_file._rows(None), "load_warnings", []) or [])
    except Exception:  # noqa: BLE001 - the file is written; say it, go on
        syslog.exception("OSC: reload after %s failed", path)
        return
    from gremlin.signal import signal

    if warnings:
        # The inputs that couldn't be read are said, as at open.
        signal.showNotification.emit("OSC", "\n".join(warnings))

    # Screens drop their Undo steps and redraw; the server applies the
    # settings at once.
    for name in (
        "oscDeviceReloaded",
        "oscDeviceModified",
        "oscServerSettingsChanged",
        "oscFeedbackChanged",
    ):
        sig = getattr(signal, name, None)
        if sig is not None:
            sig.emit()


def _reload_internal(path: Path) -> None:
    """The internal devices kept in their own module file read it again."""
    _reload_logical_device(path)
    _reload_osc(path)


def replace(path: Path, data: bytes, who: str = "", *, force: bool = False) -> None:
    """Writes a whole file (import, Device Pack, Undo, History Restore, and
    the backups they keep). A damaged module file is not written over
    (raises ModuleFileDamaged) unless force: Undo and Restore put back
    exactly what was there. Raises OSError when the write failed."""
    path = Path(path)
    if not force and _is_module_file(path):
        reason = module_file_io.damage_reason(path)
        if reason:
            raise module_file_io.ModuleFileDamaged(path, reason)
    try:
        _write(path, data)
    except OSError:
        registry.trace("SAVE", who or "Module files", "replace", path, "error")
        raise
    registry.trace("SAVE", who or "Module files", "replace", path, "ok")
    _reload_internal(path)


def write_json(path: Path, doc: dict, who: str = "") -> None:
    """Writes a whole module document as given (the caller has read and
    checked it). History keeps it. Raises OSError."""
    data, text = _doc_bytes(doc)
    _write(Path(path), data, text)
    registry.trace("SAVE", who or "Module files", "write", path, "ok")


def write_text(path: Path, text: str, who: str = "") -> None:
    """write_json for text as it is (History Restore)."""
    _write(Path(path), module_file_io.encode(text), text.replace("\r\n", "\n"))
    registry.trace("SAVE", who or "Module files", "write", path, "ok")
    _reload_internal(path)


# --- Device Bindings layout (CF-Q1, CF-Q8) ------------------------------------------

# A hardware input module file's Device Bindings layout, shared by every
# profile: {"groups": [group names in order], "order": [input keys in order],
# "group_of": {input key: group name}}. An input key is "<kind>:<number>"
# ("button:5", "axis:1", "hat:1", "key:<id>"), the same key as the claim's
# friendly names. Names are not kept here: Rename writes the friendly name
# Module Setup edits (03 S121).
LAYOUT_KEY = "layout"


def input_key(kind: str, number: int) -> str:
    """The layout and friendly-name key of an input: "button:5"."""
    return f"{kind}:{int(number)}"


def empty_layout() -> dict:
    return {"groups": [], "order": [], "group_of": {}}


def normalize_layout(raw: object) -> dict:
    """A layout with only what it may hold: group names unique and not blank,
    input keys unique, each group_of naming a listed group."""
    raw = raw if isinstance(raw, dict) else {}
    groups: list[str] = []
    for name in raw.get("groups") or []:
        text = str(name or "").strip()
        if text and text not in groups:
            groups.append(text)
    order: list[str] = []
    for key in raw.get("order") or []:
        text = str(key or "").strip()
        if text and text not in order:
            order.append(text)
    group_of: dict[str, str] = {}
    found = raw.get("group_of")
    for key, name in found.items() if isinstance(found, dict) else ():
        text = str(name or "").strip()
        if str(key).strip() and text in groups:
            group_of[str(key).strip()] = text
    return {"groups": groups, "order": order, "group_of": group_of}


def _layout_path(guid: str, device_name: str = "") -> Path | None:
    """The module file of the device: by its name and id, else its id."""
    if device_name:
        return module_file(device_name, guid)
    found = dir_of_id(guid)
    return module_file_in(found) if found is not None else None


def read_layout(guid: str, device_name: str = "") -> dict:
    """The device's Device Bindings layout (normalized); empty when it has no
    module file, a damaged one, or no layout yet."""
    path = _layout_path(guid, device_name)
    if path is None:
        return empty_layout()
    return normalize_layout(read_path(path).get(LAYOUT_KEY))


_CLAIM_BUCKETS = {"button": "buttons", "axis": "axes", "hat": "hats"}


def _is_claimed(claim: dict, key: str) -> bool:
    """Whether the claim holds a button, axis or hat key ("button:5"); other
    keys (a keyboard's "key:<id>") have no claim list and always count."""
    kind, _, number = key.partition(":")
    bucket = _CLAIM_BUCKETS.get(kind)
    if bucket is None:
        return True
    values = claim.get(bucket)
    if not isinstance(values, list):
        return False
    return number in {str(value) for value in values}


def _set_names(doc: dict, names: dict[str, str]) -> None:
    claim = doc.get("claim")
    if not isinstance(claim, dict):
        claim = doc["claim"] = {}
    friendly = claim.get("friendly")
    if not isinstance(friendly, dict):
        friendly = claim["friendly"] = {}
    for key, name in names.items():
        text = str(name or "").strip()
        if text and not _is_claimed(claim, str(key)):
            continue  # 03 S42: a name only for a claimed control
        if text:
            friendly[str(key)] = text
        else:
            friendly.pop(str(key), None)


def write_layout(
    guid: str,
    layout: dict | None,
    device_name: str = "",
    who: str = "Device Bindings",
    names: dict[str, str] | None = None,
) -> bool:
    """Saves the device's Device Bindings layout (and, names given, friendly
    names in the same write: one History entry). An empty layout removes the
    key. layout None leaves the layout as it is (names only). False when the
    device has no module file or it is damaged (said in the error dialog);
    raises OSError when the write failed."""
    path = _layout_path(guid, device_name)
    if path is None or not path.is_file():
        return False
    clean = None if layout is None else normalize_layout(layout)

    def change(doc: dict) -> bool:
        before = json.dumps(doc, sort_keys=True)
        if clean is not None:
            if clean == empty_layout():
                doc.pop(LAYOUT_KEY, None)
            else:
                doc[LAYOUT_KEY] = clean
        if names:
            _set_names(doc, names)
        return json.dumps(doc, sort_keys=True) != before

    return update_path(path, change, who)


def friendly_name(guid: str, key: str, device_name: str = "") -> str:
    """An input's friendly name ("" when none): the one Module Setup edits."""
    path = _layout_path(guid, device_name)
    if path is None:
        return ""
    claim = read_path(path).get("claim")
    names = claim.get("friendly") if isinstance(claim, dict) else None
    return str((names or {}).get(str(key)) or "").strip()


def set_friendly_name(
    guid: str, key: str, name: str, device_name: str = "", who: str = "Device Bindings"
) -> bool:
    """Rename (CF-Q8): writes the input's friendly name; blank removes it."""
    return write_layout(guid, None, device_name, who, names={str(key): name})


# --- unsaved Device Bindings layouts (CS1) ---------------------------------------
# The Device Bindings page's groups, order and Rename are held here per device
# until File > Save Profile writes them (one write, one History entry per
# device file), like the Logical Device's and OSC's files (D-04-LD-FILE): the
# title's "*" covers them and Discard drops them.
# guid_key(guid) -> {"guid", "device_name", "layout" (dict | None), "names"}
_pending: dict[str, dict] = {}
_pending_listeners: list[Callable[[str, str], None]] = []


def add_pending_listener(callback: Callable[[str, str], None]) -> None:
    """callback(what, guid) after each change to the unsaved layouts: what is
    "changed", "saved", "discarded" (guid "" for every device) or
    "replaced" (another writer changed or deleted the device's file and its
    held change was dropped: re-read and drop its Undo steps)."""
    if callback not in _pending_listeners:
        _pending_listeners.append(callback)


def remove_pending_listener(callback: Callable[[str, str], None]) -> None:
    if callback in _pending_listeners:
        _pending_listeners.remove(callback)


def _tell_pending(what: str, guid: str) -> None:
    for callback in list(_pending_listeners):
        try:
            callback(what, guid)
        except Exception:  # noqa: BLE001 - a listener never stops a save
            syslog.exception("A Device Bindings layout listener failed")


def _file_names(guid: str, device_name: str) -> dict[str, str]:
    path = _layout_path(guid, device_name)
    if path is None:
        return {}
    claim = read_path(path).get("claim")
    names = claim.get("friendly") if isinstance(claim, dict) else None
    if not isinstance(names, dict):
        return {}
    return {str(k): str(v or "").strip() for k, v in names.items()}


def set_pending_layout(
    guid: str,
    layout: dict | None,
    names: dict[str, str] | None = None,
    device_name: str = "",
) -> None:
    """Holds the device's layout (None: as it is) and friendly-name changes
    ({key: name}, "" removes) as unsaved. Names add to the ones already held.
    Back to what the file has: nothing is held (no "*")."""
    key = guid_key(guid)
    entry = _pending.get(key) or {
        "guid": str(guid),
        "device_name": device_name,
        "layout": None,
        "names": {},
    }
    if device_name:
        entry["device_name"] = device_name
    if layout is not None:
        entry["layout"] = normalize_layout(layout)
    for name_key, name in (names or {}).items():
        entry["names"][str(name_key)] = str(name or "").strip()
    saved_layout = read_layout(guid, entry["device_name"])
    saved_names = _file_names(guid, entry["device_name"])
    same_layout = entry["layout"] is None or entry["layout"] == saved_layout
    same_names = all(saved_names.get(k, "") == v for k, v in entry["names"].items())
    if same_layout and same_names:
        _pending.pop(key, None)
    else:
        _pending[key] = entry
    _tell_pending("changed", str(guid))


def set_pending_name(guid: str, key: str, name: str, device_name: str = "") -> None:
    """Rename on the Device Bindings page (CF-Q8), held until Save."""
    set_pending_layout(guid, None, {str(key): name}, device_name)


def pending_layout(guid: str) -> dict | None:
    """The device's unsaved change ({"layout": dict | None, "names": {...}}),
    None when it has none."""
    entry = _pending.get(guid_key(guid))
    if entry is None:
        return None
    layout = entry["layout"]
    return {
        "layout": None if layout is None else dict(layout),
        "names": dict(entry["names"]),
    }


def layout_for(guid: str, device_name: str = "") -> dict:
    """What the page shows: the unsaved layout, else the file's."""
    entry = _pending.get(guid_key(guid))
    if entry is not None and entry["layout"] is not None:
        return normalize_layout(entry["layout"])
    return read_layout(guid, device_name)


def friendly_name_for(guid: str, key: str, device_name: str = "") -> str:
    """What the page shows: the unsaved name, else the file's."""
    entry = _pending.get(guid_key(guid))
    if entry is not None and str(key) in entry["names"]:
        return entry["names"][str(key)]
    return friendly_name(guid, key, device_name)


def has_pending() -> bool:
    """Any device has unsaved Device Bindings layout changes (the title's "*")."""
    return bool(_pending)


def save_pending(who: str = "Device Bindings") -> int:
    """File > Save Profile: writes each device's unsaved layout and names in
    one write (one History entry each). Returns how many files were written.
    A device whose file is gone or damaged (said in the error dialog) is
    dropped; a failed write stays held and its OSError is raised after the
    others were tried."""
    global _saving_pending
    written = 0
    failed: OSError | None = None
    for key, entry in list(_pending.items()):
        path = _layout_path(entry["guid"], entry["device_name"])
        if path is None or not path.is_file():
            _pending.pop(key, None)
            from gremlin import signal as gremlin_signal

            gremlin_signal.display_error(
                f"The layout of {_device_label(entry)} could not be saved: "
                "its module file is gone.",
                str(path or ""),
            )
            continue
        _saving_pending = True
        try:
            if write_layout(
                entry["guid"],
                entry["layout"],
                entry["device_name"],
                who,
                names=entry["names"] or None,
            ):
                written += 1
        except OSError as error:
            failed = failed or error
            continue
        finally:
            _saving_pending = False
        _pending.pop(key, None)
    _tell_pending("saved", "")
    if failed is not None:
        raise failed
    return written


def discard_pending(guid: str = "") -> None:
    """Discard: drops the unsaved layouts (one device's, or every one)."""
    if guid:
        _pending.pop(guid_key(guid), None)
    else:
        _pending.clear()
    _tell_pending("discarded", str(guid))


# The newer file wins (05 S122a, AD2): a module file written by anything but
# save_pending (History Restore, Device Pack, Device Library, Module Setup)
# drops the held change of the device using it when the write changed its
# layout or claim (names); deleting the file drops it too. Pages re-read on
# "replaced". A write that leaves both alone (a picture, the view) keeps it.
_saving_pending = False


def _parts(doc: object) -> tuple[str, str]:
    """The keys a held change sits on: the layout and the claim (names)."""
    if not isinstance(doc, dict):
        return ("", "")
    return (
        json.dumps(doc.get(LAYOUT_KEY), sort_keys=True),
        json.dumps(doc.get("claim"), sort_keys=True),
    )


def _parts_of_text(text: str | None) -> tuple[str, str] | None:
    if text is None:
        return None
    try:
        return _parts(json.loads(text))
    except (ValueError, RecursionError):
        return None


def _held_parts_of(path: Path) -> dict[str, tuple[str, str]]:
    """{held key: the file's layout and claim now} for each held change of
    the device using path (none while save_pending writes)."""
    if _saving_pending or not _pending:
        return {}
    try:
        target = Path(path).resolve()
    except OSError:
        return {}
    held: dict[str, tuple[str, str]] = {}
    parts: tuple[str, str] | None = None
    for key, entry in _pending.items():
        own = _layout_path(entry["guid"], entry["device_name"])
        try:
            if own is None or Path(own).resolve() != target:
                continue
        except OSError:
            continue
        if parts is None:
            parts = _parts(read_path(target))
        held[key] = parts
    return held


def _device_label(entry: dict) -> str:
    return str(entry.get("device_name") or entry.get("guid") or "the device")


def _drop_replaced(
    held: dict[str, tuple[str, str]], after: tuple[str, str] | None
) -> None:
    """Drops each held change whose file changed under it (after None: the
    file is gone or unreadable), tells the pages ("replaced") and says so."""
    for key, before in held.items():
        if after is not None and after == before:
            continue
        entry = _pending.pop(key, None)
        if entry is None:
            continue
        _tell_pending("replaced", str(entry["guid"]))
        try:
            from gremlin.signal import signal

            signal.showNotification.emit(
                "Unsaved layout",
                "The layout changed elsewhere; your unsaved changes for "
                f"{_device_label(entry)} were dropped.",
            )
        except Exception:  # noqa: BLE001 - a note never stops a write
            syslog.exception("The dropped-layout note could not be shown")


# --- pictures ------------------------------------------------------------------
# A module file names its pictures relative to its own folder:
# "pictures/<file>" (07 S10). Each device has its own copies (no sharing,
# S133); a save removes the ones it no longer names (S106).


def safe_picture_name(name: str, fallback: str = "image.jpg") -> str:
    """A picture's file name with only letters, digits, ".", "_" and "-",
    always with a picture extension."""
    raw = Path(str(name or "").replace("\\", "/")).name
    if not raw:
        return fallback
    keep = [ch if ch.isalnum() or ch in "._-" else "_" for ch in raw]
    out = "".join(keep).strip("._") or fallback
    if Path(out).suffix.lower() not in PICTURE_EXT:
        out = out + Path(fallback).suffix
    return out


def picture_ref(name: str) -> str:
    """A picture as a module file names it: "pictures/<name>"."""
    return f"{PICTURES}/{Path(str(name or '').replace(chr(92), '/')).name}"


def _is_outside_ref(text: str) -> bool:
    return text.lower().startswith("file:") or Path(text).is_absolute()


def normal_ref(stored: str) -> str:
    """Any stored picture reference as today's: "pictures/<file name>"
    (old "<slug>/<file>", "qml/maps/...", "library/..." refs too). A file:
    URL or an absolute path is left as it is; "" stays ""."""
    text = str(stored or "").strip()
    if not text:
        return ""
    if _is_outside_ref(text):
        return text
    name = Path(text.replace("\\", "/")).name
    return picture_ref(name) if name else ""


def picture_path(path: Path, ref: str) -> Path:
    """Where a picture a device folder's module file names is (it may not
    exist). path: the device folder."""
    text = normal_ref(ref)
    if not text:
        return Path(path) / PICTURES
    if text.lower().startswith("file:"):
        return _local_path(text)
    if Path(text).is_absolute():
        return Path(text)
    return Path(path) / text


def find_picture(path: Path, stored: str, staged: Path | None = None) -> Path | None:
    """The file a stored picture reference names: in the edit's staged
    pictures first (staged: its added/ folder), then the device folder's
    pictures (path: the device folder), or a file: URL / absolute path.
    None when it is not there: another device's picture of the same name is
    never used instead (07 S11)."""
    text = normal_ref(stored)
    if not text:
        return None
    if _is_outside_ref(text):
        try:
            local = picture_path(Path(path), text)
        except Exception:  # noqa: BLE001 - not a local file
            return None
        return local if str(local) not in ("", ".") and local.is_file() else None
    if staged is not None:
        candidate = Path(staged) / Path(text).name
        if candidate.is_file():
            return candidate
    found = picture_path(Path(path), text)
    return found if found.is_file() else None


def dir_of_picture(path: Path) -> Path:
    """The device folder whose pictures/ holds path."""
    path = Path(path)
    if path.parent.name == PICTURES:
        return path.parent.parent
    return path.parent


def _before_picture_change(path: Path) -> None:
    """History keeps the pictures a device folder's module file names before
    one of them is replaced or removed."""
    from gremlin import history_modules

    path = Path(path)
    if path.parent.name != PICTURES or not is_inside(path):
        return
    history_modules.before_change(module_file_in(dir_of_picture(path)))


def put_picture_at(dest: Path, src: Path | bytes) -> None:
    """Writes one picture (atomic), keeping the pictures its module file
    names for History first. Raises OSError."""
    dest = Path(dest)
    data = src if isinstance(src, bytes) else Path(src).read_bytes()
    _before_picture_change(dest)
    module_file_io.write_bytes(dest, data)


def put_picture(device_name: str, guid: str, src: Path | bytes, as_name: str) -> str:
    """Writes a picture into the device's pictures/ as as_name; its
    reference for the module file. Raises OSError."""
    base = ensure_device_dir(device_name, guid)
    dest = base / PICTURES / Path(str(as_name).replace("\\", "/")).name
    if _reserved(dest.name):
        # The device's background picture's name is never a user picture's
        # (07 S157): renamed as for any other clash.
        number = 1
        while (dest.parent / f"{dest.stem}_{number}{dest.suffix}").exists():
            number += 1
        dest = dest.parent / f"{dest.stem}_{number}{dest.suffix}"
    put_picture_at(dest, src)
    return picture_ref(dest.name)


def remove_picture_files(paths: list[Path]) -> None:
    """Deletes picture files (History keeps the pictures their module file
    names first). Raises OSError on the first one that can't go."""
    for path in paths:
        path = Path(path)
        _before_picture_change(path)
        path.unlink(missing_ok=True)


# The Device Mapping Editor's page and the photo frame in its middle (07 S68), as
# fractions of the page: where the device's photo is fitted.
PAGE_W = 32000
PAGE_H = 18000
PHOTO_FRAME = (0.125, 0.125, 0.75, 0.75)


def is_background(node: object) -> bool:
    """A map layer on the background plane (07 S111); no key: foreground."""
    return isinstance(node, dict) and node.get("plane") == "background"


def _bottom_picture_index(nodes: object) -> int:
    """Where the bottom background picture is in nodes, or -1."""
    if not isinstance(nodes, list):
        return -1
    for index, node in enumerate(nodes):
        if is_background(node) and node.get("shape") == "image":
            return index
    return -1


def device_photo_ref(doc: object) -> str:
    """The device's photo (07 S127): "pictures/<name>" of the bottom
    background picture, "" when there is none. A map saved before the
    planes names it in "image" until it is saved again (OT-2)."""
    if not isinstance(doc, dict):
        return ""
    nodes = doc.get("nodes")
    index = _bottom_picture_index(nodes)
    if isinstance(nodes, list) and index >= 0:
        return normal_ref(str(nodes[index].get("src") or ""))
    # ONE-TIME (tracker OT-2): the old top-level photo, until the next Save.
    return normal_ref(str(doc.get("image") or ""))


def picture_size(folder: Path | None, ref: str) -> tuple[int, int]:
    """A picture's size in pixels, read from its file's header (not the
    whole picture); (0, 0) when it can't be found or read."""
    if folder is None or not str(ref or "").strip():
        return 0, 0
    found = find_picture(Path(folder), str(ref))
    if found is None:
        return 0, 0
    from PySide6 import QtGui

    size = QtGui.QImageReader(str(found)).size()
    if not size.isValid() or size.width() <= 0 or size.height() <= 0:
        return 0, 0
    return size.width(), size.height()


def fit_in_box(
    box: tuple[float, float, float, float], width: float, height: float
) -> tuple[float, float, float, float]:
    """A picture of width x height pixels fitted inside box (fx, fy, fw,
    fh as page fractions), keeping its shape, centred. Unknown size: the
    box itself."""
    fx, fy, fw, fh = box
    if width <= 0 or height <= 0:
        return fx, fy, fw, fh
    box_w, box_h = fw * PAGE_W, fh * PAGE_H
    scale = min(box_w / width, box_h / height)
    out_w = width * scale / PAGE_W
    out_h = height * scale / PAGE_H
    return fx + (fw - out_w) / 2, fy + (fh - out_h) / 2, out_w, out_h


def background_picture_node(ref: str, box: tuple[float, float, float, float]) -> dict:
    """A new background picture layer showing ref in box (page fractions),
    with the editor's defaults for a picture (rig_overlays.addOverlay)."""
    fx, fy, fw, fh = box
    return {
        "kind": "draw",
        "rot": 0,
        "fill": "filled",
        "color": "#14532D",
        "border": "#22C55E",
        "stroke": 2,
        "opacity": 1,
        "pad": 8,
        "around": [],
        "id": "d_bg" + uuid.uuid4().hex[:12],
        "shape": "image",
        "src": ref,
        "locked": False,
        "pinned": False,
        "sockets": [],
        "fx": fx,
        "fy": fy,
        "fw": fw,
        "fh": fh,
        "plane": "background",
    }


def set_device_photo(doc: dict, ref: str, folder: Path | None = None) -> None:
    """Makes ref the device's photo: the bottom background picture (07
    S127, Module Setup's Import Image). An existing one shows the new
    picture in its place (fitted in its box); without one, a new bottom
    layer fitted to the photo frame. "" removes it. folder (the device
    folder) is where the picture's size is read. A map saved before the
    planes is turned into today's first (OT-2); "image" and "photo" go."""
    if not isinstance(doc, dict):
        return
    from gremlin.modules import planes_once

    # ONE-TIME (tracker OT-2): a map saved before the planes, turned into
    # today's; goes with planes_once.
    planes_once.old_photo_to_layer(doc, folder)
    for key in planes_once.OLD_PHOTO_KEYS:
        doc.pop(key, None)
    nodes = doc.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
        doc["nodes"] = nodes
    text = str(ref or "").strip()
    index = _bottom_picture_index(nodes)
    if not text:
        if index >= 0:
            del nodes[index]
        return
    width, height = picture_size(folder, text)
    if index < 0:
        box = fit_in_box(PHOTO_FRAME, width, height)
        nodes.insert(0, background_picture_node(text, box))
        return
    node = nodes[index]
    if str(node.get("src") or "").strip() == text:
        return
    node["src"] = text
    node.pop("srcUrl", None)
    node.pop("lookUrl", None)
    # The old picture's crop means nothing on another picture.
    node.pop("crop", None)
    try:
        fx, fy, fw, fh = (
            float(node.get(key, default))
            for key, default in zip(("fx", "fy", "fw", "fh"), PHOTO_FRAME)
        )
    except (TypeError, ValueError):
        fx, fy, fw, fh = PHOTO_FRAME
    node["fx"], node["fy"], node["fw"], node["fh"] = fit_in_box(
        (fx, fy, fw, fh), width, height
    )


# --- the device's background picture (07 S157) --------------------------------
# pictures/device-photo.png: a picture of the whole visible background plane,
# made by gremlin.ui.device_photo through the hidden renderer whenever the
# background changes. Its key (a PNG text chunk) says which background it
# shows; a file whose key differs is stale and is made again.

DEVICE_PHOTO = "device-photo.png"
DEVICE_PHOTO_SIDE = 1024
DEVICE_PHOTO_KEY = "GremlinBackgroundKey"
# Bump when the renderer's look changes: every file is then made again.
RENDER_VERSION = 1
# Keys only the screen uses; they don't change the picture.
_SCREEN_ONLY = frozenset({"srcUrl", "lookUrl", "selected"})


def _reserved(name: str) -> bool:
    return str(name or "").casefold() == DEVICE_PHOTO.casefold()


def visible_background(doc: object) -> list[dict]:
    """The background nodes a composite draws: plane "background", not
    hidden (a hidden group takes its members with it), in order."""
    if not isinstance(doc, dict):
        return []
    nodes = doc.get("nodes")
    if not isinstance(nodes, list):
        return []
    return [n for n in nodes if is_background(n) and not n.get("hidden")]


def makes_device_photo(doc: object, folder: Path | None = None) -> bool:
    """Whether a device gets the background picture: input modules only
    (07 S157). Outputs (vJoy, the Xbox pad: direction "dest") and the
    Logical Device never do; they show the bottom background picture as
    before (07 S127). Known by the module document (direction, device
    name, bound id) and, with folder, its device.json (id, shown name)."""
    from gremlin.modules import device_class

    def _input(name: str, guid: str) -> bool:
        kind = _kind(name, guid)
        return kind != "logical_device" and not device_class.is_output_kind(kind)

    if isinstance(doc, dict):
        if doc_direction(doc) == "dest":
            return False
        name = str(doc.get("device") or doc.get("boundName") or "")
        if not _input(name, str(doc.get("boundGuidLocal") or "")):
            return False
    if folder is not None:
        held = _read_json(Path(folder) / ID_FILE)
        key = str(held.get("id") or "").strip()
        guid = "" if key.lower().startswith("name:") else key
        name = str(held.get("name") or "")
        if key.lower().startswith("name:") and registry.is_output_name(key[5:]):
            return False
        if (key or name) and not _input(name, guid):
            return False
    return True


def _key_view(value: object) -> object:
    """value without the screen-only keys, at every depth."""
    if isinstance(value, dict):
        return {
            k: _key_view(v)
            for k, v in value.items()
            if k not in _SCREEN_ONLY and not str(k).startswith("_")
        }
    if isinstance(value, list):
        return [_key_view(v) for v in value]
    return value


def background_key(doc: object, folder: Path | None) -> str:
    """Which background the device's background picture shows: "" with no
    visible background, else a hash of the render version, the visible
    background nodes (screen-only keys left out) and the byte size of each
    picture they name (-1 when missing). Size, not time: a copied picture
    keeps its size, so an imported file stays current. "" too for a device
    that gets no background picture (makes_device_photo: outputs and the
    Logical Device)."""
    nodes = visible_background(doc)
    if not nodes or not makes_device_photo(doc, folder):
        return ""
    sizes = {}
    for ref in sorted(_layer_refs({"nodes": nodes})):
        found = find_picture(Path(folder), ref) if folder is not None else None
        try:
            sizes[ref] = found.stat().st_size if found is not None else -1
        except OSError:
            sizes[ref] = -1
    text = "|".join(
        (
            str(RENDER_VERSION),
            json.dumps(_key_view(nodes), sort_keys=True),
            json.dumps(sizes, sort_keys=True),
        )
    )
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


def device_photo_path(folder: Path) -> Path:
    """Where a device folder's background picture is (it may not exist)."""
    return Path(folder) / PICTURES / DEVICE_PHOTO


def device_photo_key(folder: Path) -> str:
    """The key in the folder's background picture (its header only); ""
    when it is missing or unreadable."""
    path = device_photo_path(folder)
    if not path.is_file():
        return ""
    from PySide6 import QtGui

    return str(QtGui.QImageReader(str(path)).text(DEVICE_PHOTO_KEY) or "")


def device_photo_current(folder: Path, doc: object | None = None) -> bool:
    """The folder's background picture is there and shows its background
    (doc, or the folder's module file). False with no visible background."""
    if doc is None:
        doc = read_path(module_file_in(Path(folder)))
    key = background_key(doc, Path(folder))
    return bool(key) and device_photo_key(folder) == key


def write_device_photo(folder: Path, png: bytes) -> None:
    """Writes the folder's background picture (atomic). No History step: it
    is made from the module file, which History keeps. Raises OSError."""
    path = device_photo_path(folder)
    module_file_io.write_bytes(path, png)
    registry.trace("SAVE", "Module files", "write_device_photo", path, "written")


def remove_device_photo(folder: Path) -> None:
    """Removes the folder's background picture (no visible background
    left). A file that can't go is logged and left."""
    path = device_photo_path(folder)
    if not path.is_file():
        return
    try:
        path.unlink()
    except OSError as exc:
        syslog.warning(f"Background picture {path} could not be removed: {exc}")
        return
    registry.trace("SAVE", "Module files", "remove_device_photo", path, "removed")


# --- the Device Image (D-03-DEVICE-IMAGE, input modules only) ------------------
# A picture the user uploads for an input module's device: its own file
# pictures/device-image.<ext>, named by the module file's top-level key
# "deviceImage". Not a map layer: the Device Mapping Editor never shows it
# and it is not part of the background picture's key.

DEVICE_IMAGE_KEY = "deviceImage"
DEVICE_IMAGE_STEM = "device-image"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def device_image_ref(doc: object) -> str:
    """The device's uploaded image as the module file names it
    ("pictures/<file>"), "" when none."""
    if not isinstance(doc, dict):
        return ""
    value = doc.get(DEVICE_IMAGE_KEY)
    return normal_ref(value) if isinstance(value, str) else ""


def device_image_name(src: Path | str) -> str:
    """The file name: device-image + the picked file's extension (IMAGE_EXT,
    else .jpg)."""
    ext = Path(str(src or "")).suffix.lower()
    return DEVICE_IMAGE_STEM + (ext if ext in IMAGE_EXT else ".jpg")


def _has_device_image(device_name: str, guid: str) -> bool:
    """Whether the device may have a Device Image: input modules only."""
    from gremlin.modules import device_class

    kind = _kind(device_name, guid)
    return kind != "logical_device" and not device_class.is_output_kind(kind)


def set_device_image(
    device_name: str, guid: str, src: Path | bytes, who: str, as_name: str = ""
) -> str:
    """Outside any edit (the Home card menu): copies src into the device's
    pictures/ under a free device-image name (as_name gives the extension
    for bytes), names it in the module file (one write, one History entry)
    and then drops the previous image's file. "" (nothing written) for an
    output or the Logical Device, a damaged module file (reported, 03 S64)
    or a failed write (the new file is removed again). The new ref."""
    if not _has_device_image(device_name, guid):
        return ""
    path = module_file(device_name, guid)
    if module_file_io.damage_reason(path):
        update_path(path, lambda doc: False, who)
        return ""
    try:
        data = src if isinstance(src, bytes) else Path(src).read_bytes()
        pictures = ensure_device_dir(device_name, guid) / PICTURES
        name = device_image_name(as_name or ("" if isinstance(src, bytes) else src))
        name, same = _free_picture_name(name, data, [pictures])
        dest = pictures / name
        if not same:
            put_picture_at(dest, data)
    except OSError as exc:
        syslog.warning(f"Device Image for {device_name} could not be written: {exc}")
        return ""
    ref = picture_ref(name)

    def change(doc: dict) -> object:
        doc[DEVICE_IMAGE_KEY] = ref
        return None

    try:
        written = update(device_name, guid, change, who)
    except OSError:
        written = False
    if not written:
        if not same:
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                syslog.warning(f"Picture {dest} could not be removed")
        return ""
    remove_unused_pictures(device_name, guid)
    return ref


def remove_device_image(device_name: str, guid: str, who: str) -> bool:
    """Drops the module file's Device Image key and then its file (History
    keeps it with the entry). False when there was none, or the module file
    is damaged (reported)."""
    path = module_file(device_name, guid)
    if not path.is_file():
        return False

    def change(doc: dict) -> object:
        if DEVICE_IMAGE_KEY not in doc:
            return False
        doc.pop(DEVICE_IMAGE_KEY)
        return None

    try:
        written = update_path(path, change, who)
    except OSError:
        return False
    if written:
        remove_unused_pictures(device_name, guid)
    return written


def shown_photo_ref(doc: object, exists: Callable[[str], bool]) -> str:
    """What every place that shows "the device's photo" uses (07 S127,
    S157, D-03-DEVICE-IMAGE): for an input module, its Device Image when
    set and exists(it), else the device's background picture when the map
    has a visible background and exists(its ref); else the bottom
    background picture (while the file is being made, or when it is
    missing). Outputs and the Logical Device always get the bottom
    background picture (makes_device_photo)."""
    if makes_device_photo(doc):
        image = device_image_ref(doc)
        if image and exists(image):
            return image
        ref = picture_ref(DEVICE_PHOTO)
        if visible_background(doc) and exists(ref):
            return ref
    return device_photo_ref(doc)


def named_refs(doc: object) -> set[str]:
    """The pictures a module document (or template, or recovery copy)
    names, as stored: every picture layer ("shape" or "kind" "image",
    "src"), background and foreground, also inside groups, the old
    top-level photo ("image") of a map saved before the planes (OT-2), the
    Device Image (D-03-DEVICE-IMAGE) and the device's background picture
    when the map has a visible background (07 S157: kept by the clean-up,
    History and every .gmap)."""
    refs = _layer_refs(doc)
    image = device_image_ref(doc)
    if image:
        refs.add(image)
    if visible_background(doc) and makes_device_photo(doc):
        refs.add(picture_ref(DEVICE_PHOTO))
    return refs


def _layer_refs(doc: object) -> set[str]:
    """named_refs without the device's background picture."""
    refs: set[str] = set()
    if not isinstance(doc, dict):
        return refs
    # ONE-TIME (tracker OT-2): the old top-level photo of a map saved
    # before the planes, until its next Save.
    image = str(doc.get("image") or "").strip()
    if image:
        refs.add(image)

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if (
                value.get("shape") == "image" or value.get("kind") == "image"
            ) and value.get("src"):
                refs.add(str(value["src"]).strip())
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)

    walk(doc.get("nodes"))
    refs.discard("")
    return refs


def _names_of(refs: Iterable[str] | None) -> set[str]:
    """The file names in pictures/ that refs name (outside refs left out)."""
    names: set[str] = set()
    for ref in refs or ():
        text = normal_ref(str(ref))
        if text and not _is_outside_ref(text):
            names.add(Path(text).name.casefold())
    return names


def remove_unused_pictures(
    device_name: str, guid: str = "", used_refs: Iterable[str] | None = None
) -> list[Path]:
    """Removes the files in the device's pictures/ that nothing names (07
    S106): used_refs, or (None) the pictures module.json and recovery.json
    name. Nothing is removed while module.json is damaged. The files
    removed."""
    base = device_dir(device_name, guid)
    pictures = base / PICTURES
    if not pictures.is_dir():
        return []
    if used_refs is None:
        main = module_file_in(base)
        if module_file_io.damage_reason(main) or module_file_io.damage_reason(
            base / RECOVERY_FILE
        ):
            return []
        used_refs = named_refs(read_path(main)) | named_refs(
            read_path(base / RECOVERY_FILE)
        )
    keep = _names_of(used_refs)
    unused = [
        p
        for p in sorted(pictures.iterdir())
        if p.is_file() and p.name.casefold() not in keep
    ]
    removed: list[Path] = []
    for path in unused:
        try:
            remove_picture_files([path])
        except OSError:
            syslog.warning(f"Unused picture {path} could not be removed")
            continue
        removed.append(path)
        registry.trace(
            "SAVE", "Module files", "remove_unused_pictures", path, "removed"
        )
    return removed


def _same_bytes(left: Path, right: Path) -> bool:
    try:
        if left.stat().st_size != right.stat().st_size:
            return False
        return left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def _free_picture_name(
    name: str, data: bytes, places: list[Path], reuse_first: bool = True
) -> tuple[str, bool]:
    """A file name for data in the first of places: name when it is free in
    all of them (or holds the same bytes: (name, True), nothing to write),
    else <stem>_<n><ext>. reuse_first=False: a file already in the first
    place is never reused, even with the same bytes. The device's
    background picture's name is always taken (07 S157)."""
    stem, ext = Path(name).stem, Path(name).suffix
    number = 0
    candidate = name
    while True:
        same = False
        taken = _reserved(candidate)
        for place in places if not taken else ():
            path = place / candidate
            if path.is_file() and (reuse_first or place != places[0]):
                try:
                    if path.read_bytes() == data:
                        same = True
                        continue
                except OSError:
                    pass
                taken = True
            elif path.exists():
                taken = True
        if not taken:
            return candidate, same
        number += 1
        candidate = f"{stem}_{number}{ext}"


def _copy_into(
    src_dir: Path, refs: Iterable[str] | None, dest: Path, also: list[Path]
) -> dict:
    """Copies the pictures refs name (in device folder src_dir) into the
    folder dest; {old ref: new ref}. A missing picture is left out."""
    moved: dict[str, str] = {}
    for ref in sorted({str(r) for r in (refs or ()) if str(r or "").strip()}):
        if normal_ref(ref) == picture_ref(DEVICE_PHOTO):
            # Made from the destination's own background (07 S157).
            continue
        src = find_picture(Path(src_dir), ref)
        if src is None:
            continue
        try:
            data = src.read_bytes()
        except OSError:
            continue
        name = safe_picture_name(src.name, src.name)
        name, same = _free_picture_name(name, data, [Path(dest), *also])
        if not same:
            put_picture_at(Path(dest) / name, data)
        moved[ref] = picture_ref(name)
    return moved


def _rename_refs(doc: dict, moved: dict[str, str]) -> None:
    """Rewrites the picture references in doc (photo, Device Image and
    chips, nested) by moved {old ref: new ref}."""
    if str(doc.get("image") or "").strip() in moved:
        doc["image"] = moved[str(doc["image"]).strip()]
    image = device_image_ref(doc)
    if image and image in moved:
        doc[DEVICE_IMAGE_KEY] = moved[image]

    def walk(value: object) -> None:
        if isinstance(value, dict):
            src = str(value.get("src") or "").strip()
            if (
                value.get("shape") == "image" or value.get("kind") == "image"
            ) and src in moved:
                value["src"] = moved[src]
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)

    walk(doc.get("nodes"))


def copy_pictures(
    src_dir: Path, refs: Iterable[str] | None, dest_dir: Path
) -> dict[str, str]:
    """Copies the pictures refs name from device folder src_dir into device
    folder dest_dir's pictures/ (copying a map to another device, a
    template, the Library: no sharing, 07 S109, 10 S61). The same name with
    the same bytes is reused; the same name with other bytes is written as
    <stem>_<n><ext>. {old ref: new ref}; a missing picture is left out.
    Raises OSError."""
    return _copy_into(Path(src_dir), refs, Path(dest_dir) / PICTURES, [])


# --- an edit's temporary folder (07 S26 S36 S40 S62 S107 S109) ---------------
# cache/edit[-<owner>]/<id key>/:
#   state.json  {"phase": "editing" | "committing"}; none once Save is done
#               (a folder left without it is a finished edit: removed by
#               the next begin_edit, dropped by recover_edit)
#   start/      module.json and the pictures it named when the edit began
#   added/      pictures added during the edit (named "pictures/<file>")
# Save (commit_edit) copies the added pictures into the device's pictures/,
# writes module.json and removes the pictures nothing names; Cancel drops
# the folder. A crash is sorted out at the next start (recover_edit).


def _state(path: Path) -> str:
    return str(_read_json(Path(path) / STATE_FILE).get("phase") or "")


def _set_state(path: Path, phase: str) -> None:
    module_file_io.write_bytes(
        Path(path) / STATE_FILE,
        (json.dumps({"phase": phase}) + "\n").encode("utf-8"),
    )


def _remove_tree(path: Path) -> None:
    if Path(path).is_dir():
        shutil.rmtree(path)


def begin_edit(device_name: str, guid: str = "", owner: str = "") -> Path:
    """Starts an edit: a fresh temporary folder with a copy of module.json
    and the pictures it names as they are now (start/). Its path. Raises
    OSError."""
    temp = edit_temp_dir(device_name, guid, owner)
    _remove_tree(temp)
    start = temp / "start"
    (temp / "added").mkdir(parents=True, exist_ok=True)
    start.mkdir(parents=True, exist_ok=True)
    base = device_dir(device_name, guid)
    main = module_file_in(base)
    if main.is_file():
        shutil.copyfile(main, start / MODULE_FILE)
        for ref in named_refs(read_path(main)):
            src = find_picture(base, ref)
            if src is not None and src.parent == base / PICTURES:
                (start / PICTURES).mkdir(exist_ok=True)
                shutil.copyfile(src, start / PICTURES / src.name)
    _set_state(temp, "editing")
    return temp


def staged_dir(device_name: str, guid: str = "", owner: str = "") -> Path:
    """The edit's added/ folder (find_picture's staged)."""
    return edit_temp_dir(device_name, guid, owner) / "added"


def _staging(device_name: str, guid: str, owner: str) -> Path:
    temp = edit_temp_dir(device_name, guid, owner)
    if not (temp / STATE_FILE).is_file():
        begin_edit(device_name, guid, owner)
    added = temp / "added"
    added.mkdir(parents=True, exist_ok=True)
    return added


def stage_picture(
    device_name: str, guid: str, src: Path | bytes, as_name: str, owner: str = ""
) -> str:
    """Keeps a picture added during an edit in its added/ folder (the
    device's pictures/ are not touched until Save). Its reference,
    "pictures/<name>": a name another picture of the device already has
    gets _<n> (one added earlier in the edit too, even with the same bytes).
    Raises OSError."""
    added = _staging(device_name, guid, owner)
    data = src if isinstance(src, bytes) else Path(src).read_bytes()
    name = safe_picture_name(as_name)
    pictures = pictures_dir(device_name, guid)
    # Each picture added in the edit gets its own file (a second identical
    # paste is pasted_1.png, 07 S62); one the device already has is reused.
    name, same = _free_picture_name(name, data, [added, pictures], reuse_first=False)
    if not same:
        module_file_io.write_bytes(added / name, data)
    return picture_ref(name)


def stage_copied(
    device_name: str,
    guid: str,
    src_dir: Path,
    refs: Iterable[str] | None,
    owner: str = "",
) -> dict[str, str]:
    """copy_pictures into an edit: the pictures refs name in device folder
    src_dir (another device's, a template's) are staged in added/.
    {old ref: new ref}. Raises OSError."""
    added = _staging(device_name, guid, owner)
    return _copy_into(Path(src_dir), refs, added, [pictures_dir(device_name, guid)])


def commit_edit(
    device_name: str,
    guid: str,
    change: Callable[[dict], object],
    owner: str = "",
    who: str = "Device Mapping Editor",
) -> str:
    """Save: the added pictures go into the device's pictures/, change(doc)
    is written into module.json (update_path), the pictures nothing names
    are removed (S106) and the temporary folder goes. The error, or "".
    A failed write keeps the edit (phase "editing") so Save can be tried
    again."""
    temp = edit_temp_dir(device_name, guid, owner)
    if not (temp / STATE_FILE).is_file():
        begin_edit(device_name, guid, owner)
    try:
        base = ensure_device_dir(device_name, guid)
    except OSError as exc:
        return f"The pictures could not be saved. {exc}"
    path = module_file_in(base)
    if module_file_io.damage_reason(path):
        # A damaged file refuses the Save before any picture moves (07 S12):
        # update_path reports the refusal and writes nothing; the edit stays.
        try:
            update_path(path, change, who)
        except OSError:
            pass
        _back_to_editing(temp)
        return "The module file is damaged, so the change was not saved."
    try:
        _set_state(temp, "committing")
        added = temp / "added"
        if added.is_dir():
            for picture in sorted(added.iterdir()):
                dest = base / PICTURES / picture.name
                if dest.is_file() and not _same_bytes(dest, picture):
                    syslog.warning(f"Picture {dest} not replaced by the edit's copy")
                    continue
                if not dest.is_file():
                    put_picture_at(dest, picture)
    except OSError as exc:
        _back_to_editing(temp)
        return f"The pictures could not be saved. {exc}"
    try:
        update_path(path, change, who)
    except OSError as exc:
        _back_to_editing(temp)
        remove_unused_pictures(device_name, guid)
        return f"The module file could not be saved. {exc}"
    # The Save is done: drop state.json first, so a folder that can't be
    # removed (a picture still open) is a finished edit, never a Save to
    # undo (recover_edit) or an edit to add to (_staging) (07 G32).
    try:
        (temp / STATE_FILE).unlink(missing_ok=True)
    except OSError:
        syslog.warning(f"Edit folder {temp} could not be marked finished")
    remove_unused_pictures(device_name, guid)
    try:
        _remove_tree(temp)
    except OSError:
        syslog.warning(f"Edit folder {temp} could not be removed")
    return ""


def _back_to_editing(temp: Path) -> None:
    try:
        _set_state(temp, "editing")
    except OSError:
        syslog.warning(f"Edit folder {temp} could not be marked")


def cancel_edit(device_name: str, guid: str = "", owner: str = "") -> None:
    """Cancel: the temporary folder goes; the device's folder was never
    touched."""
    temp = edit_temp_dir(device_name, guid, owner)
    try:
        _remove_tree(temp)
    except OSError:
        syslog.warning(f"Edit folder {temp} could not be removed")


def recover_edit(device_name: str, guid: str = "", owner: str = "") -> str:
    """After a crash: an edit with a recovery copy waiting is kept
    ("kept"); an edit without one is dropped ("dropped"); a Save that
    stopped part way puts start/ back ("restored"). "" when there was no
    edit."""
    temp = edit_temp_dir(device_name, guid, owner)
    if not temp.is_dir():
        return ""
    phase = _state(temp)
    base = device_dir(device_name, guid)
    if phase == "editing" and (base / RECOVERY_FILE).is_file():
        return "kept"
    if phase == "committing":
        start = temp / "start"
        try:
            pictures = start / PICTURES
            if pictures.is_dir():
                for path in sorted(pictures.iterdir()):
                    dest = base / PICTURES / path.name
                    if not dest.is_file() or not _same_bytes(dest, path):
                        put_picture_at(dest, path)
            main = module_file_in(base)
            if (start / MODULE_FILE).is_file():
                replace(
                    main,
                    (start / MODULE_FILE).read_bytes(),
                    "Device Mapping Editor",
                    force=True,
                )
            elif main.is_file():
                delete_path(main, "Device Mapping Editor")
        except OSError:
            syslog.exception(f"Edit of {device_name} could not be put back")
            return "error"
        remove_unused_pictures(device_name, guid)
        cancel_edit(device_name, guid, owner)
        return "restored"
    cancel_edit(device_name, guid, owner)
    return "dropped"


# --- deleting ------------------------------------------------------------------


def delete_path(path: Path, who: str = "") -> None:
    """Deletes one file (a module file is kept by History once it is gone,
    08 S12). Raises OSError; a missing file is fine."""
    from gremlin import history_modules

    path = Path(path)
    if not path.exists():
        return
    if _is_module_file(path):
        held = _held_parts_of(path)
        with history_modules.deleting(path):
            path.unlink()
        _saved()
        _drop_replaced(held, None)
    else:
        path.unlink()
    registry.trace("SAVE", who or "Module files", "delete", path, "removed")


def _edit_dirs(device_name: str, guid: str) -> list[Path]:
    """Every window's edit folder of the device."""
    key = _key_dir(id_key(device_name, _lookup_guid(device_name, guid)))
    cache = folder() / "cache"
    if not cache.is_dir():
        return []
    return [p for p in cache.glob(f"edit*/{key}") if p.is_dir()]


def delete(
    device_name: str,
    guid: str = "",
    *,
    pictures: bool = False,
    who: str = "Configure Module",
) -> str:
    """Deletes the device's module file (Delete File keeps the rest of its
    folder, 03 Q14). pictures: the whole folder goes (Delete Device, Remove
    from Library), module.json first so History keeps it, and its edit
    folders. The caller keeps the Device Library's autosave first (03 S62,
    S91). The reason it failed, or ""."""
    base = device_dir(device_name, guid)
    path = module_file_in(base)
    if path.is_file():
        try:
            delete_path(path, who)
        except OSError as exc:
            return f"The module file could not be deleted. {exc}"
    if not pictures:
        return ""
    try:
        for temp in _edit_dirs(device_name, guid):
            shutil.rmtree(temp)
        if base.is_dir():
            shutil.rmtree(base)
            registry.trace("SAVE", who, "delete", base, "removed")
    except OSError as exc:
        return str(exc)
    finally:
        _dirs_changed()
        notify_module_files()
    return ""


def move_aside_path(path: Path) -> Path:
    """Moves the module file at path aside as <name>.bad-<date> (kept, not
    deleted, 03 S66) and records it in History (decision F3). Raises
    OSError when the move failed."""
    from gremlin import history_modules

    path = Path(path)
    copy = path.with_name(f"{path.name}.bad-{time.strftime('%Y%m%d-%H%M%S')}")
    held = _held_parts_of(path)
    with history_modules.deleting(path, moved_to=copy):
        os.replace(path, copy)
    registry.trace("SAVE", "Home", "startFresh", copy, "ok")
    _saved()
    _drop_replaced(held, None)
    return copy


def move_aside(device_name: str, guid: str = "") -> Path | None:
    """Start Fresh: moves the device's damaged module file aside
    (move_aside_path). None when the file is not damaged; raises OSError
    when the move failed."""
    path = module_file(device_name, guid)
    if not module_file_io.damage_reason(path):
        return None
    return move_aside_path(path)


def pack_file_name(device_name: str) -> str:
    """A device name as a file name (characters files can't hold become
    spaces)."""
    raw = " ".join(str(device_name or "").split()) or "device"
    cleaned = [" " if ch in '<>:"/\\|?*' or ord(ch) < 32 else ch for ch in raw]
    name = " ".join("".join(cleaned).split()).strip(" .")
    return name or "device"


# --- renaming a device's folder (03 S131) ----------------------------------------


def rename_device_dir(device_name: str, guid: str, new_shown: str) -> tuple[bool, str]:
    """Renames the device's folder after its new shown name (an alias set
    or cleared). Refused, with nothing changed, while a file in it is open
    in another program. (True, "") when done or the device has no folder
    yet; (False, reason) when refused."""
    base = device_dir(device_name, guid)
    if not base.is_dir():
        return True, ""
    shown = " ".join(str(new_shown or "").split()) or shown_name_of(device_name, guid)
    key = dir_id(base) or id_key(device_name, _lookup_guid(device_name, guid))
    want = unique_name(folder_name_for(shown), key, keep=base)
    target = base.with_name(want)
    if want != base.name:
        try:
            os.rename(base, target)
        except OSError as exc:
            reason = exc.strerror or str(exc)
            return False, (
                f"The folder {base.name} could not be renamed to {want}: a file "
                f"in it is open in another program ({reason})."
            )
        registry.trace("SAVE", "Device names", "rename", target, "ok")
    try:
        held = _read_json(target / ID_FILE)
        if held.get("name") != shown or not held.get("id"):
            _write_id(target, str(held.get("id") or key), shown)
    except OSError:
        syslog.warning(f"device.json of {target} could not be written")
    _dirs_changed()
    notify_module_files()
    return True, ""


def sync_dir_name(device_name: str, guid: str = "") -> None:
    """After a device scan or a names change: the device's folder takes its
    shown name when it differs. A failure is logged and tried again at the
    next one (no message)."""
    base = device_dir(device_name, guid)
    if not base.is_dir():
        return
    shown = shown_name_of(device_name, _lookup_guid(device_name, guid))
    key = dir_id(base) or id_key(device_name, _lookup_guid(device_name, guid))
    if unique_name(folder_name_for(shown), key, keep=base) == base.name:
        return
    ok, reason = rename_device_dir(device_name, guid, shown)
    if not ok:
        syslog.warning(reason)


# --- devices ---------------------------------------------------------------------


def guid_text(value: object) -> str:
    """A device id as text ("" for none)."""
    raw = getattr(value, "uuid", value)
    text = str(raw or "").strip()
    return "" if text.lower() in ("", "none") else text


def live_devices() -> list:
    """The connected sticks and vJoy devices ([] before devices are known)."""
    try:
        from gremlin import device_initialization

        devices = list(device_initialization.physical_devices() or [])
        devices.extend(device_initialization.vjoy_devices() or [])
        return devices
    except Exception:  # noqa: BLE001 - no device list yet
        return []


# --- directions and the devices a pack can name ---------------------------------


def doc_direction(doc: dict, exported_name: str = "") -> str:
    """ "dest" or "source" for a module document (a pack's or a file's)."""
    label = _dict(doc.get("pack"))
    named = str(doc.get("device") or label.get("exportedName") or exported_name or "")
    if registry.is_output_name(named):
        return "dest"
    raw = str(doc.get("direction") or "").strip().lower()
    if raw in ("source", "dest"):
        return raw
    return "dest" if registry.is_output_name(exported_name) else "source"


def direction_for(device_name: str, guid: str = "") -> str:
    """ "dest" for an output device (or a file marked dest), else "source"."""
    if registry.is_output_name(device_name):
        return "dest"
    doc = read(device_name, guid)
    if str(doc.get("direction") or "").strip().lower() == "dest":
        return "dest"
    return "source"


_TWIN_NUMBER = re.compile(r" \((\d+)\)$")


def _collapsed(value: str) -> str:
    return " ".join(str(value or "").split()).lower()


def _twin_names() -> dict[str, str]:
    """{id key: twin name} kept for second identical sticks (02 S11-S16)."""
    try:
        from gremlin import device_initialization
        from gremlin.config import Configuration

        if not Configuration().exists(*device_initialization.TWIN_SETTING):
            return {}  # not registered yet: no twin names kept
        stored = device_initialization.stored_twins()
    except Exception:  # noqa: BLE001 - no settings yet
        return {}
    return {stored_guid_key(key): str(name) for key, name in stored.items()}


def _home_label(name: str, guid: str, twins: dict[str, str]) -> str:
    """The name Home's card shows for this device: the user's alias, else
    its twin name ("<name> (2)", only while its base name still matches,
    02 S16), else name."""
    shown = name
    twin = twins.get(stored_guid_key(guid), "")
    if twin and _collapsed(_TWIN_NUMBER.sub("", twin)) == _collapsed(name):
        shown = twin
    try:
        from gremlin import device_aliases

        return device_aliases.display_name(guid, shown)
    except Exception:  # noqa: BLE001 - no settings yet
        return shown


def known_devices() -> list[dict]:
    """Connected devices, devices the open profile has seen, and saved module
    files: one row per device (08 S106a), by its id when it has one (vJoy and
    Xbox outputs share one file: by name), else by name (files only):
    [{name, guid, connected, hasFile, fileName, label}]; label is the name
    Home shows (alias, twin name "<name> (2)"), else name."""
    rows: dict[str, dict] = {}

    def by_name(key: str) -> list[dict]:
        return [row for row in rows.values() if row["name"].lower() == key]

    def touch(
        name: str, guid: str = "", connected: bool = False, path: Path | None = None
    ) -> None:
        label = " ".join(str(name or "").split())
        key = label.lower()
        if not key:
            return
        row_id = "" if registry.is_output_name(label) else stored_guid_key(guid)
        # A saved file is already found: never look a connected stick's
        # folder up again by its name alone (decision F4).
        path = path if path is not None else module_file(label, guid)
        row = rows.get("id:" + row_id) if row_id else None
        if row is None and not row_id:
            same = by_name(key)
            # A name with no id (a file only) is the device of that name;
            # with several of that name (twins) it is none of them.
            if len(same) > 1:
                return
            row = same[0] if same else None
        if row is None:
            rows["id:" + row_id if row_id else "name:" + key] = {
                "name": label,
                "guid": guid,
                "connected": bool(connected),
                "hasFile": path.is_file(),
                "fileName": path.parent.name,
            }
            return
        if guid and not row["guid"]:
            row["guid"] = guid
        if connected:
            row["connected"] = True
        if path.is_file():
            row["hasFile"] = True

    for dev in live_devices():
        touch(
            str(getattr(dev, "name", "") or ""),
            guid_text(getattr(dev, "device_guid", "")),
            True,
        )
    try:
        from gremlin.shared_state import current_profile

        if current_profile is not None:
            for info in current_profile.device_database.devices.values():
                touch(str(info.name or ""), guid_text(info.device_uuid), False)
    except Exception:  # noqa: BLE001 - no profile yet
        pass
    for path in module_files():
        doc = registry.read_doc(path)
        if not doc or doc.get("kind") != "control.hardware":
            continue
        touch(str(doc.get("device") or "").strip() or path.parent.name, "", False, path)
    twins = _twin_names()
    for row in rows.values():
        row["label"] = (
            _home_label(row["name"], row["guid"], twins) if row["guid"] else row["name"]
        )
    return sorted(rows.values(), key=lambda row: (row["label"].lower(), row["guid"]))


def match_known_device(name: str, guid: str = "") -> dict | None:
    """The known_devices() row of this name, or None. With guid, the guid
    decides (twins share a name, 10 S22): the connected device with that
    id, else the known row with it; None when neither has it."""
    want = _collapsed(name)
    key = stored_guid_key(guid)
    if key:
        for dev in live_devices():
            text = guid_text(getattr(dev, "device_guid", ""))
            if stored_guid_key(text) != key:
                continue
            own = " ".join(str(getattr(dev, "name", "") or name).split())
            path = module_file(own, text)
            return {
                "name": own,
                "guid": text,
                "connected": True,
                "hasFile": path.is_file(),
                "fileName": path.parent.name,
            }
        for row in known_devices():
            if stored_guid_key(row.get("guid", "")) == key:
                return row
        # Unplugged, its folder found by its id (a twin's shares the other
        # twin's name, so the name would find the wrong one, 10 S41).
        found = dir_of_id(guid)
        if found is not None and module_file_in(found).is_file():
            doc = registry.read_doc(module_file_in(found)) or {}
            own = " ".join(str(doc.get("device") or name or found.name).split())
            return {
                "name": own,
                "guid": str(guid),
                "connected": False,
                "hasFile": True,
                "fileName": found.name,
            }
        return None
    if not want:
        return None
    for row in known_devices():
        if _collapsed(row["name"]) == want:
            return row
    return None


def suggest_device_name(exported: str, devices: list[dict] | None = None) -> str:
    """The one known device of this name, or ""."""
    want = _collapsed(exported)
    if not want:
        return ""
    hits = [
        row["name"]
        for row in (devices if devices is not None else known_devices())
        if _collapsed(row["name"]) == want
    ]
    return hits[0] if len(hits) == 1 else ""


# --- imported backups -----------------------------------------------------------


def archive_stamp(moment: datetime | None = None) -> str:
    """Year, day, month, then hour, minute and second (local time)."""
    moment = moment or datetime.now()
    month = (
        "JAN",
        "FEB",
        "MAR",
        "APR",
        "MAY",
        "JUN",
        "JUL",
        "AUG",
        "SEP",
        "OCT",
        "NOV",
        "DEC",
    )[moment.month - 1]
    return (
        f"{moment.year:04d}-{moment.day:02d}-{month}_"
        f"{moment.hour:02d}_{moment.minute:02d}_{moment.second:02d}"
    )


def unique_archive(path: Path, stem: str, stamp: str = "") -> Path:
    """A free <device folder>/imported/<stem> <stamp>.json for the previous
    file an import keeps (03 S58, 08 S73)."""
    stamp = stamp or archive_stamp()
    base = Path(path) / IMPORTED
    found = base / f"{stem} {stamp}.json"
    number = 2
    while found.exists():
        found = base / f"{stem} {stamp}_{number}.json"
        number += 1
    return found


# --- Module Setup's "Import from" ------------------------------------------------


def import_choices(device_name: str = "", guid: str = "") -> list[str]:
    """The device folders to import from: every folder with a module file,
    by name; with a device named, its own folder is left out."""
    own = device_dir(device_name, guid) if (device_name or guid) else None
    return [
        path.parent.name for path in module_files() if own is None or path.parent != own
    ]


def _hid(node: dict) -> int | None:
    try:
        number = int(node.get("hwId"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def member_kind(node: dict, member: dict) -> str:
    """Kind of one chip in a group: its own kind when saved, otherwise from
    the group (an axis stack holds axes, any other group buttons)."""
    own = str(member.get("kind") or "").strip().lower()
    if own in ("axis", "hat"):
        return own
    if own in ("btn", "button"):
        return "btn"
    return "axis" if str(node.get("kind") or "") == "axis_stack" else "btn"


def filter_nodes(
    nodes: list, buttons: set[int], axes: set[int], hats: set[int], keys: set[int]
) -> list:
    """The device map nodes whose control is in these sets (groups keep the
    members that are); nodes of no control are kept."""
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
        pool = {
            "btn": buttons,
            "button": buttons,
            "axis": axes,
            "hat": hats,
            "key": keys,
        }
        if kind in pool:
            if hid in pool[kind]:
                kept.append(node)
            continue
        if hid is None:
            kept.append(node)
    return kept


def _filter_friendly(
    friendly: dict, buttons: set[int], axes: set[int], hats: set[int], keys: set[int]
) -> dict:
    pools = {"button": buttons, "axis": axes, "hat": hats, "key": keys}
    out = {}
    for key, value in friendly.items():
        kind, _, raw = str(key).partition(":")
        if kind == "osc" and re.fullmatch(r"[0-9a-f]{32}", raw):
            # OSC's names are kept by input uid (D-09-OSC-FILE).
            out[str(key)] = value
            continue
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


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _numbers(items: object) -> set[int]:
    found = set()
    for item in items if isinstance(items, list) else []:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number > 0:
            found.add(number)
    return found


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
    previous_background: list | None = None,
) -> tuple[dict, str]:
    """A module document copied onto this device: only the controls it has,
    its own name and id; its device map keeps this device's background
    (previous_background, its layers bottom first) and takes the file's
    foreground (03 S135). (the copy, what was left out)."""
    claim = _dict(doc.get("claim"))
    source_keys = _numbers(claim.get("keys"))
    keys = set(source_keys) if keep_keys else set()
    source_buttons = set(claim_ids(claim, "button"))
    source_axes = set(claim_ids(claim, "axis"))
    source_hats = set(claim_ids(claim, "hat"))
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
    kept = (kept_buttons, kept_axes, kept_hats, kept_keys)
    payload["claim"] = {
        "buttons": sorted(kept_buttons),
        "axes": sorted(kept_axes),
        "hats": sorted(kept_hats),
        "keys": sorted(kept_keys),
        "friendly": _filter_friendly(_dict(claim.get("friendly")), *kept),
    }
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    foreground = [n for n in filter_nodes(nodes, *kept) if not is_background(n)]
    background = json.loads(json.dumps(list(previous_background or [])))
    payload["nodes"] = background + foreground
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
    # ONE-TIME (tracker OT-2): the file's own photo (a map saved before the
    # planes) is background, never copied.
    for key in ("image", "photo", "imageWidth", "imageHeight"):
        payload.pop(key, None)
    left = []
    left.extend(f"Button {n}" for n in sorted(source_buttons - kept_buttons))
    left.extend(f"Axis {n}" for n in sorted(source_axes - kept_axes))
    left.extend(f"Hat {n}" for n in sorted(source_hats - kept_hats))
    left.extend(f"Key {n}" for n in sorted(source_keys - kept_keys))
    return payload, _left_out_text(left)


def resolve_import_source(folder_name: str) -> Path | None:
    """The module file "Import from" names: a device folder's name (its
    module.json), or a path or file: URL of a file. None when there is no
    such file."""
    raw = str(folder_name or "").strip()
    if not raw:
        return None
    if "://" in raw or raw.lower().startswith("file:"):
        try:
            src = _local_path(raw)
        except Exception:  # noqa: BLE001 - not a local file
            return None
        return src if str(src) not in ("", ".") and Path(src).is_file() else None
    if "/" not in raw and "\\" not in raw and raw.lower() not in RESERVED:
        named = _named_dir(raw)
        if named is not None and module_file_in(named).is_file():
            return module_file_in(named)
    direct = Path(raw)
    if direct.is_absolute() and direct.is_file():
        return direct
    return None


def file_direction(doc: dict, path: Path) -> str:
    """The direction a file to import from is taken as: its "direction",
    else its device or folder name (a vJoy or the program's Xbox pad is an
    output), else an input. Every file is module.json, so its own file name
    says nothing."""
    path = Path(path)
    folder_name = path.parent.name if path.name == MODULE_FILE else path.stem
    return registry.module_direction(doc, folder_name)


def device_input_ids(guid: str) -> tuple[list[int], list[int], list[int]]:
    """The buttons, axes and hats a connected device reports (empty lists
    when it isn't connected)."""
    from gremlin.modules import hardware

    buttons: list[int] = []
    axes: list[int] = []
    hats: list[int] = []
    try:
        info = hardware.device_info(guid)
    except Exception:  # noqa: BLE001 - not connected
        info = None
    if info is None:
        return buttons, axes, hats

    def count(name: str) -> int:
        try:
            return int(getattr(info, name, 0) or 0)
        except (TypeError, ValueError):
            return 0

    buttons = list(range(1, count("button_count") + 1))
    hats = list(range(1, count("hat_count") + 1))
    for entry in getattr(info, "axis_map", None) or []:
        index = getattr(entry, "axis_index", None)
        if index is None and isinstance(entry, dict):
            index = entry.get("axis_index")
        try:
            number = int(index)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if number > 0:
            axes.append(number)
    if not axes:
        axes = list(range(1, count("axis_count") + 1))
    return buttons, sorted(set(axes)), hats


def connected_input_ids(guid: str) -> tuple[set[int], set[int], set[int]] | None:
    """device_input_ids as sets; None when the device isn't connected."""
    from gremlin.modules import hardware

    if not str(guid or "").strip():
        return None
    try:
        info = hardware.device_info(guid)
    except Exception:  # noqa: BLE001 - not connected
        info = None
    if info is None:
        return None
    buttons, axes, hats = device_input_ids(guid)
    return set(buttons), set(axes), set(hats)


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


# Undo of "Import from", one per device and window (03 S59, GL-087):
# (device key, window) -> {"dest", "previous", "at"}.
_file_import_undo: dict[tuple[str, str], dict] = {}
_undo_serial = 0


def _undo_key(device_name: str, guid: str, window: str) -> tuple[str, str]:
    device = stored_guid_key(guid) or f"name:{plain_slug(device_name)}"
    return device, str(window or "")


def _undo_record(device_name: str, guid: str, window: str) -> tuple[str, str] | None:
    """The key of the Undo record asked for: this device's in this window,
    or, with no device named, the latest one."""
    if device_name or guid:
        key = _undo_key(device_name, guid, window)
        return key if key in _file_import_undo else None
    if not _file_import_undo:
        return None
    return max(_file_import_undo, key=lambda k: _file_import_undo[k]["at"])


def can_undo_file_import(
    device_name: str = "", guid: str = "", window: str = ""
) -> bool:
    """True when this device's last "Import from" in this window can be
    undone (with no device named: any)."""
    return _undo_record(device_name, guid, window) is not None


def drop_file_import_undo(
    device_name: str = "", guid: str = "", window: str = ""
) -> None:
    """The import stays (OK in its notice): its Undo is dropped. With no
    device named, every one is."""
    if not (device_name or guid):
        _file_import_undo.clear()
        return
    _file_import_undo.pop(_undo_key(device_name, guid, window), None)


def undo_file_import(device_name: str = "", guid: str = "", window: str = "") -> str:
    """Puts this device's previous file back (or removes the new one) (03
    S59, 08 S85). The chosen file is not touched. What happened, in
    words."""
    key = _undo_record(device_name, guid, window)
    record = _file_import_undo.get(key) if key else None
    if not record:
        return "Undo failed. There is nothing to undo."
    dest = Path(record["dest"])
    previous = record.get("previous")
    try:
        if previous is None:
            delete_path(dest, "Configure Module")
            note = "The new module file was removed."
        else:
            replace(dest, previous, "Configure Module", force=True)
            note = "The previous module file was put back."
    except OSError:
        return "Undo failed. The previous module file could not be put back."
    _file_import_undo.pop(key, None)  # type: ignore[arg-type]
    return "Undone. " + note


def import_file(
    device_name: str,
    guid: str,
    file_name: str,
    direction: str = "source",
    window: str = "Configure Module",
) -> str:
    """Copies another device's module file (file_name: its folder's name,
    or a file) onto this device's (03 S55). The chosen file stays where it
    is; the picture chips it names are copied into this device's pictures
    (no sharing, S133); the previous file is kept in this device's
    imported/ (S58). A damaged current file is refused. What happened, in
    words (lines)."""
    name = str(device_name or "").strip()
    if not name:
        return "That file could not be read."
    src = resolve_import_source(file_name)
    if src is None or not src.is_file():
        return "That file could not be read."
    dest = module_file(name, guid)
    try:
        if src.resolve() == dest.resolve():
            return "That file is already this device's file."
    except OSError:
        return "That file could not be read."
    doc = registry.read_doc(src)
    if doc is None:
        registry.trace("READ", window, "import_file", src, "error")
        return "That file could not be read."
    registry.trace("READ", window, "import_file", src, "ok")
    if doc.get("kind") != "control.hardware":
        return "That file is not a module file."
    target = "dest" if str(direction or "").strip().lower() == "dest" else "source"
    source_direction = file_direction(doc, src)
    if target == "source" and source_direction == "dest":
        return "A vJoy file cannot be copied onto a stick."
    if target == "dest" and source_direction == "source":
        return "A stick file cannot be copied onto a vJoy."
    # Built-ins without hardware (Keyboard, Logical Device) have no
    # plugged-in buttons, axes and hats to check against: by class (03 S90b).
    from gremlin.modules import device_class

    keep_keys = device_class.can("key_claim", guid, name)
    no_limits = device_class.can("no_hardware_limits", guid, name)
    limits = (set(), set(), set()) if no_limits else connected_input_ids(guid)
    if limits is None:
        return "This device is not connected, so the file cannot be checked."
    buttons, axes, hats = limits
    previous_background: list = []
    previous_bytes: bytes | None = None
    if dest.is_file():
        try:
            previous_bytes = dest.read_bytes()
            previous = json.loads(previous_bytes.decode("utf-8"))
        except (OSError, UnicodeError, ValueError, RecursionError):
            registry.trace("READ", window, "import_file", dest, "error")
            return "The current file could not be read, so it was not replaced."
        if not isinstance(previous, dict):
            return "The current file could not be read, so it was not replaced."
        # ONE-TIME (tracker OT-2): a map saved before the planes: its photo
        # as a layer first.
        from gremlin.modules import planes_once

        planes_once.old_photo_to_layer(previous, dest.parent)
        previous_nodes = previous.get("nodes")
        previous_background = (
            [n for n in previous_nodes if is_background(n)]
            if isinstance(previous_nodes, list)
            else []
        )
    payload, left = prepare_imported_doc(
        doc,
        name,
        str(guid or ""),
        target,
        buttons,
        axes,
        hats,
        keep_keys=keep_keys,
        previous_background=previous_background,
    )
    try:
        dest = module_file_in(ensure_device_dir(name, guid))
        # Only the file's foreground brings pictures; the background's are
        # this device's own already.
        imported = {"nodes": [n for n in payload["nodes"] if not is_background(n)]}
        chips = named_refs(imported)
        moved = copy_pictures(src.parent, chips, dest.parent) if chips else {}
        if moved:
            _rename_refs(imported, moved)
        replace(dest, (json.dumps(payload, indent=2) + "\n").encode("utf-8"), window)
    except (OSError, module_file_io.ModuleFileDamaged):
        return "The module file could not be written."
    claim = _dict(payload.get("claim"))
    friendly = _dict(claim.get("friendly"))
    lines = [
        f"Imported into {dest.parent.name}.",
        _copied_sentence(
            len(claim.get("buttons") or []),
            len(claim.get("axes") or []),
            len(claim.get("hats") or []),
            len(claim.get("keys") or []),
        ),
    ]
    if friendly:
        lines.append(
            _count_phrase(len(friendly), "name was copied.", "names were copied.")
        )
    lines.append(left.strip() if left.strip() else "Everything in the file was copied.")
    if previous_background:
        lines.append("This device's background was kept.")
    else:
        lines.append("No background was copied from the chosen file.")
    lines.append("Profile wires were not changed.")
    lines.append("The chosen file was left where it was.")
    if previous_bytes is not None:
        backup = unique_archive(dest.parent, "module")
        try:
            replace(backup, previous_bytes, window)
            lines.append("The previous file was saved as")
            lines.append(backup.name.replace("-", "‑"))
        except OSError:
            lines.append("The previous file could not be saved to imported.")
    global _undo_serial
    _undo_serial += 1
    _file_import_undo[_undo_key(name, str(guid or ""), window)] = {
        "dest": str(dest),
        "previous": previous_bytes,
        "at": _undo_serial,
    }
    return "\n".join(lines)
