# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The module file store: the one owner of which module file a device uses
and of every change to module files, their pictures
and the file choices (system-maps map 1, gap list GL-067).

Callers pass a device's name and id and never build module paths:

- where:    slug_for, path_for, pictures_dir, card_key, path_of, ...
- reading:  read, read_path, damage, exists, find_picture
- writing:  update (load, refuse a damaged file, change, write),
            replace (whole file: import, Device Pack, Undo, Restore),
            write_json / write_text (a whole document as given)
- pictures: put_picture, remove_pictures, into_library
- deleting: delete (Delete File / Delete Device), move_aside (Start Fresh),
            delete_path
- choices:  bind, unbind, unbind_file, bindings, users_of, is_shared
- import:   import_file, can_undo_file_import, undo_file_import,
            drop_file_import_undo (Module Setup's "Import from", its Undo
            tied to the device and window that made it)

Rules kept here:
- one lookup rule (registry.resolve_module_slug), a stale id filtered out
  first (guid_filter);
- a lookup by name only is for vJoy, Keyboard, OSC and the program's own
  devices; a stick looked up without its id is logged (decision F4);
- a damaged file is never written over (ModuleFileDamaged), except by a
  restore that asks for it (force);
- every write is atomic (module_file.write_bytes), pictures too;
- History is hooked here only: writes call history_modules.note_write,
  deletes and Start Fresh go through history_modules.deleting;
- a saved module file reaches Run's output claims at once (output.refresh).

registry stays the read-only index of module files and the home of the
lookup rule; module_file the atomic writer and the damaged-file rule.
Main thread only.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from gremlin.modules import module_file, registry
from gremlin.modules.claim import claim_ids
from gremlin.modules.ids import guid_key, stored_guid_key
from gremlin.modules.registry import plain_slug

PICTURE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

syslog = logging.getLogger("system")


# --- where ---------------------------------------------------------------------


def folder() -> Path:
    """The modules folder (Options > Folders). Tests point it elsewhere by
    patching this function."""
    from gremlin.util import modules_dir

    return Path(modules_dir())


def card_key(device_name: str) -> str:
    """A device's Home card key (order, hidden, sizes, stacks): its own
    name's slug, not its file's (decision F2: changing it would reset
    everyone's card layout)."""
    return plain_slug(device_name) or "device"


def own_slug(device_name: str) -> str:
    """The file named after the device (the lookup rule's last step)."""
    return plain_slug(device_name) or "device"


def own_path(device_name: str) -> Path:
    """The module file named after the device, whichever device uses it
    (twin naming at start-up asks which device it is bound to)."""
    return path_of(own_slug(device_name))


def _same_name(left: str, right: str) -> bool:
    return (
        " ".join(str(left or "").split()).casefold()
        == " ".join(str(right or "").split()).casefold()
    )


def guid_filter(device_name: str, guid: str) -> str:
    """guid when it belongs to device_name; "" for a stale id: one that a
    connected device of another name has, or another id while a device of
    this name is connected. A stale id must not select another device's file
    (03 S2, S9). An id of a device that isn't connected is kept."""
    given = stored_guid_key(guid)
    if not given:
        return ""
    names = {
        name
        for name, ids in registry.connected_names().items()
        if guid_key(given) in ids
    }
    if names:
        wanted = " ".join(str(device_name or "").split()).casefold()
        return str(guid) if wanted in names else ""
    owned = registry.guid_for_name(device_name)
    if owned and guid_key(owned) != guid_key(given):
        return ""
    return str(guid)


# Not a device class (03 S90b): a slug-PREFIX rule for which module files
# may be looked up by name only without a note ("keyboard_stick" and
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
    syslog.warning(f"Module file of {device_name} looked up without its device id")


def slug_for(device_name: str, guid: str = "") -> str:
    """The module file (slug) a device uses: the one rule, a stale id
    filtered out first."""
    if not stored_guid_key(guid):
        _note_name_only(device_name)
    filtered = guid_filter(device_name, guid)
    return registry.resolve_module_slug(device_name, filtered) or own_slug(device_name)


def _safe_stem(slug: str) -> str:
    text = str(slug or "").strip()
    if text.lower().endswith(".json"):
        text = text[:-5]
    if not text or any(c in text for c in ("/", "\\", ":")) or text in (".", ".."):
        return ""
    return text


def path_of(slug: str) -> Path:
    """<modules>/<slug>.json for a slug the program already has (a card's
    file, a History entry's file name, a layout picked by file). A slug
    that is not a plain name is "device"."""
    return folder() / f"{_safe_stem(slug) or 'device'}.json"


def path_for(device_name: str, guid: str = "") -> Path:
    """<modules>/<slug>.json: the file the device uses."""
    return path_of(slug_for(device_name, guid))


def _live(guid: str) -> bool:
    want = guid_key(stored_guid_key(guid))
    return bool(want) and any(
        guid_key(guid_text(getattr(dev, "device_guid", ""))) == want
        for dev in live_devices()
    )


def file_of_guid(guid: str) -> Path | None:
    """The module file of the device with this id, found by the id alone
    (the file chosen for the id, else the one bound to it); None when it
    has none. Never by name: twins share one (10 S41)."""
    key = stored_guid_key(guid)
    want = guid_key(key)
    if not want:
        return None
    found = registry.modules()
    chosen = plain_slug(bindings().get(key, ""))
    if chosen and path_of(chosen).is_file():
        module = next((m for m in found if m.slug == chosen), None)
        bound = guid_key(module.bound_guid) if module is not None else ""
        if not bound or bound == want:
            return path_of(chosen)
    for module in found:
        if guid_key(module.bound_guid) == want:
            return path_of(module.slug)
    return None


def path_for_id(device_name: str, guid: str) -> Path:
    """path_for for a device known by its id, plugged in or not (the Device
    Library and Device Pack, 10 S41): its own file found by its id first
    (file_of_guid), as twins share a name; else path_for. Unplugged with no
    file of its own: a path no other device uses, so nothing of another
    stick (a twin of the same name) is written or removed."""
    if not stored_guid_key(guid):
        return path_for(device_name, guid)
    found = file_of_guid(guid)
    if found is not None:
        return found
    path = path_for(device_name, guid)
    if _live(guid):
        return path
    want = guid_key(stored_guid_key(guid))
    module = next((m for m in registry.modules() if m.slug == path.stem), None)
    other = guid_key(module.bound_guid) if module is not None else ""
    named = registry.guid_for_name(device_name)
    if (other and other != want) or (named and guid_key(named) != want):
        return path_of(f"{own_slug(device_name)}_{want[:8].lower()}")
    return path


def pictures_dir_of(slug: str) -> Path:
    """<modules>/<slug>/ for a slug the program already has."""
    return folder() / (_safe_stem(slug) or "device")


def pictures_dir(device_name: str, guid: str = "") -> Path:
    """<modules>/<slug>/: the device's photo and map pictures."""
    return pictures_dir_of(slug_for(device_name, guid))


def picture_ref(slug: str, name: str) -> str:
    """A picture as a module file names it (relative to the modules folder)."""
    return f"{slug}/{name}"


def module_relative(stored: str) -> str:
    """A stored picture reference relative to the modules folder ("qml/maps/"
    as old files wrote it is dropped)."""
    text = str(stored or "").replace("\\", "/").lstrip("/")
    marker = "qml/maps/"
    if text.lower().startswith(marker):
        return text[len(marker) :]
    return text


def picture_path(ref: str) -> Path:
    """Where a picture a module file names is (it may not exist)."""
    return folder() / module_relative(ref)


def module_of_picture(path: Path) -> Path:
    """The module file whose picture folder holds path."""
    path = Path(path)
    return path.parent.with_name(path.parent.name + ".json")


def library_dir() -> Path:
    """modules/library: every photo and picture chosen, kept for reuse."""
    return folder() / "library"


def imported_dir() -> Path:
    """modules/imported: files to import from, and the backups imports keep."""
    return folder() / "imported"


def recovery_path(slug: str) -> Path:
    """The Button Map's recovery copy of unsaved edits for a module file."""
    return folder() / "recovery" / f"{_safe_stem(slug) or 'device'}.json"


def photo_stash_dir(slug: str, owner: str = "") -> Path:
    """Where an editing session keeps the photo it started with (Button
    Map: owner ""; another window: its own owner name)."""
    base = folder() / "cache" / ("photo-stash" + (f"-{owner}" if owner else ""))
    return base / (_safe_stem(slug) or "device")


def photo_files(slug: str) -> list[Path]:
    """The device photo's files: photo.<ext> (and photo_<name>.<ext>) in its
    picture folder, and an old <slug>_photo.<ext> beside the module files."""
    found: list[Path] = []
    pictures = pictures_dir_of(slug)
    if pictures.is_dir():
        found = [
            p
            for pattern in ("photo.*", "photo_*")
            for p in pictures.glob(pattern)
            if p.is_file()
        ]
    stem = _safe_stem(slug)
    for ext in PICTURE_EXT:
        legacy = folder() / f"{stem}_photo{ext}"
        if stem and legacy.is_file():
            found.append(legacy)
    return found


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
    return read_path(path_for(device_name, guid))


def read_text(path: Path) -> str | None:
    """A module file's text as it is on disk; None when it is missing or not
    UTF-8 (damaged)."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def damage(device_name: str, guid: str = "") -> str:
    """Why the device's module file can't be read, or "" (missing or fine)."""
    return module_file.damage_reason(path_for(device_name, guid))


def damage_of(path: Path) -> str:
    """damage() for a path the store gave out."""
    return module_file.damage_reason(Path(path))


def exists(device_name: str, guid: str = "") -> bool:
    return path_for(device_name, guid).is_file()


def module_files() -> list[Path]:
    """Every module file in the folder, by name."""
    base = folder()
    return sorted(base.glob("*.json")) if base.is_dir() else []


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


def find_picture(stored: str) -> Path | None:
    """The file a stored picture reference names, in the modules folder (or
    a file: URL); None when it is not there. A missing picture is missing:
    another device's picture with the same name is never used instead
    (07 S11, GL-085)."""
    text = str(stored or "").strip().replace("\\", "/")
    if not text:
        return None
    if text.startswith("file:"):
        try:
            local = _local_path(text)
        except Exception:  # noqa: BLE001 - not a local file
            return None
        return local if local and Path(local).is_file() else None
    path = Path(text)
    if path.is_absolute():
        return path if path.is_file() else None
    found = picture_path(text)
    return found if found.is_file() else None


# --- writing -------------------------------------------------------------------


def _text_of(data: bytes) -> str | None:
    try:
        return data.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return None


def _saved() -> None:
    """A module file changed: Run's output claims take effect at once (03
    S36, 06 S53), not after the output layer's one-second cache."""
    try:
        from gremlin.modules import output

        output.refresh()
    except Exception:  # noqa: BLE001 - a refresh never stops a save
        syslog.exception("Output claims could not be re-read after a save")


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
    module_file.write_bytes(path, data)
    if not is_module:
        return
    if text is None:
        text = _text_of(data)
    if text is not None:
        history_modules.note_write(path, text, old)
    _saved()


def write_file(path: Path, data: bytes) -> None:
    """Writes any file atomically (History keeps a module file). module_file's
    text writers forward module files here, so History is hooked in one
    place. For a module file, callers use update or replace."""
    _write(Path(path), data)


def _doc_bytes(doc: dict) -> tuple[bytes, str]:
    text = json.dumps(doc, indent=2) + "\n"
    return module_file.encode(text), text


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
        doc = module_file.load_for_update(path)
    except module_file.ModuleFileDamaged as damaged:
        registry.trace("READ", who, "update", path, "damaged")
        if report:
            module_file.report_refused(damaged)
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
    """update_path on the file the device uses."""
    return update_path(path_for(device_name, guid), change, who, report=report)


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
        logical_device_file.load()
    except Exception:  # noqa: BLE001 - the file is written; say it, go on
        syslog.exception("Logical Device: reload after %s failed", path)
        return
    # Screens: the Logical page drops its Undo steps and redraws.
    from gremlin.signal import signal

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
    except Exception:  # noqa: BLE001 - the file is written; say it, go on
        syslog.exception("OSC: reload after %s failed", path)
        return
    from gremlin.signal import signal

    # Screens drop their Undo steps and redraw; the server applies the
    # settings at once.
    for name in ("oscDeviceReloaded", "oscDeviceModified", "oscServerSettingsChanged"):
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
        reason = module_file.damage_reason(path)
        if reason:
            raise module_file.ModuleFileDamaged(path, reason)
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
    _write(Path(path), module_file.encode(text), text.replace("\r\n", "\n"))
    registry.trace("SAVE", who or "Module files", "write", path, "ok")
    _reload_internal(path)


# --- pictures ------------------------------------------------------------------


def safe_picture_name(name: str, fallback: str = "image.jpg") -> str:
    """A picture's file name with only letters, digits, ".", "_" and "-",
    always with a picture extension."""
    raw = Path(name or "").name
    if not raw:
        return fallback
    keep = [ch if ch.isalnum() or ch in "._-" else "_" for ch in raw]
    out = "".join(keep).strip("._") or fallback
    if Path(out).suffix.lower() not in PICTURE_EXT:
        out = out + Path(fallback).suffix
    return out


def put_picture_at(dest: Path, src: Path | bytes) -> None:
    """Writes one picture (atomic), keeping the pictures its module file
    names for History first. Raises OSError."""
    from gremlin import history_modules

    dest = Path(dest)
    data = src if isinstance(src, bytes) else Path(src).read_bytes()
    history_modules.before_change(module_of_picture(dest))
    module_file.write_bytes(dest, data)


def put_picture(device_name: str, guid: str, src: Path | bytes, as_name: str) -> str:
    """Writes a picture into the device's picture folder as as_name; its
    reference for the module file. Raises OSError."""
    slug = slug_for(device_name, guid)
    dest = pictures_dir_of(slug) / Path(as_name).name
    put_picture_at(dest, src)
    return picture_ref(slug, dest.name)


def remove_picture_files(paths: list[Path]) -> None:
    """Deletes picture files (History keeps the pictures their module file
    names first). Raises OSError on the first one that can't go."""
    from gremlin import history_modules

    for path in paths:
        path = Path(path)
        if is_inside(path) and path.parent.parent.resolve() == folder().resolve():
            history_modules.before_change(module_of_picture(path))
        path.unlink(missing_ok=True)


def remove_pictures(
    device_name: str, guid: str = "", pattern: str = "photo.*", keep: Path | None = None
) -> bool:
    """Deletes the device's pictures matching pattern (the photo by default),
    and the old <slug>_photo.<ext> files when pattern is the photo's, except
    keep. False when one could not be deleted."""
    slug = slug_for(device_name, guid)
    pictures = pictures_dir_of(slug)
    found: list[Path] = []
    if pictures.is_dir():
        found = [p for p in pictures.glob(pattern) if p.is_file()]
    if pattern == "photo.*":
        found += [p for p in photo_files(slug) if p.parent == folder()]
    if keep is not None:
        found = [p for p in found if p.resolve() != Path(keep).resolve()]
    try:
        remove_picture_files(found)
    except OSError:
        return False
    for path in found:
        registry.trace("SAVE", "Module files", "remove_pictures", path, "removed")
    return True


def _same_bytes(left: Path, right: Path) -> bool:
    try:
        if left.stat().st_size != right.stat().st_size:
            return False
        return left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def into_library(src: Path) -> Path:
    """Keeps a chosen picture in modules/library. A picture already there
    (the same content) is not copied again (03 Q3, GL-089). Its path there.
    Raises OSError."""
    src = Path(src)
    base = library_dir()
    base.mkdir(parents=True, exist_ok=True)
    try:
        if src.resolve().parent == base.resolve():
            return src
    except OSError:
        pass
    dest = base / safe_picture_name(src.name, src.name)
    stem, ext = dest.stem, dest.suffix
    for kept in sorted(base.glob(f"{stem}*{ext}")):
        if kept.is_file() and _same_bytes(kept, src):
            return kept
    number = 1
    while dest.exists():
        dest = base / f"{stem}_{number}{ext}"
        number += 1
    module_file.write_bytes(dest, src.read_bytes())
    return dest


# --- deleting ------------------------------------------------------------------


def delete_path(path: Path, who: str = "") -> None:
    """Deletes one file (a module file is kept by History once it is gone,
    08 S12). Raises OSError; a missing file is fine."""
    from gremlin import history_modules

    path = Path(path)
    if not path.exists():
        return
    if _is_module_file(path):
        with history_modules.deleting(path):
            path.unlink()
        _saved()
    else:
        path.unlink()
    registry.trace("SAVE", who or "Module files", "delete", path, "removed")


def _remove_device_leftovers(slug: str, who: str) -> str:
    """A deleted device's picture folder, old photo files, Button Map
    recovery copy and photo safety copies (07 Q11, GL-094). Its error, or
    ""."""
    try:
        pictures = pictures_dir_of(slug)
        if pictures.is_dir():
            shutil.rmtree(pictures)
            registry.trace("SAVE", who, "delete", pictures, "removed")
        stem = _safe_stem(slug)
        for extra in folder().glob(f"{stem}_photo.*") if stem else []:
            if extra.is_file():
                extra.unlink()
                registry.trace("SAVE", who, "delete", extra, "removed")
        recovery_path(slug).unlink(missing_ok=True)
        stashes = folder() / "cache"
        if stem and stashes.is_dir():
            for stash in stashes.glob(f"photo-stash*/{stem}"):
                if stash.is_dir():
                    shutil.rmtree(stash)
    except OSError as exc:
        return str(exc)
    return ""


def delete(
    device_name: str,
    guid: str = "",
    *,
    pictures: bool = False,
    who: str = "Configure Module",
) -> str:
    """Deletes the device's module file (the one it uses: a renamed stick's
    old file) and the file choices pointing it there.

    The caller keeps the Device Library's autosave first (03 S62, S91).
    pictures: its picture folder, old photo files,
    recovery copy and photo safety copies go too (Delete Device; Delete File
    keeps the pictures, 03 Q14). Refused when another device uses the file.
    The reason it was refused or failed, or "".
    """
    path = path_for(device_name, guid)
    slug = path.stem
    if other_users(slug, device_name, guid):
        return "Another stick is using this file."
    if path.is_file():
        try:
            delete_path(path, who)
        except OSError as exc:
            return f"The module file could not be deleted. {exc}"
    error = _remove_device_leftovers(slug, who) if pictures else ""
    # No other device uses the file, so every choice left for it is this
    # device's own or a stale one (an old id of it, 03 S94): all go.
    data = bindings()
    stale = [each for each, value in data.items() if plain_slug(str(value)) == slug]
    for each in stale:
        data.pop(each, None)
    if stale:
        set_bindings(data)
    return error


def move_aside_path(path: Path) -> Path:
    """Moves the module file at path aside as <name>.json.bad-<date> (kept,
    not deleted, 03 S66) and records it in History (decision F3). Raises
    OSError when the move failed."""
    from gremlin import history_modules

    path = Path(path)
    copy = path.with_name(f"{path.name}.bad-{time.strftime('%Y%m%d-%H%M%S')}")
    with history_modules.deleting(path, moved_to=copy):
        os.replace(path, copy)
    registry.trace("SAVE", "Home", "startFresh", copy, "ok")
    _saved()
    return copy


def move_aside(device_name: str, guid: str = "") -> Path | None:
    """Start Fresh: moves the device's damaged module file aside
    (move_aside_path). None when the file is not damaged; raises OSError
    when the move failed."""
    path = path_for(device_name, guid)
    if not module_file.damage_reason(path):
        return None
    return move_aside_path(path)


def pack_file_name(device_name: str) -> str:
    """A device name as a file name (characters files can't hold become
    spaces)."""
    raw = " ".join(str(device_name or "").split()) or "device"
    cleaned = [" " if ch in '<>:"/\\|?*' or ord(ch) < 32 else ch for ch in raw]
    name = " ".join("".join(cleaned).split()).strip(" .")
    return name or "device"


# --- file choices (the binding store) -------------------------------------------


def bindings() -> dict[str, str]:
    """Device id (or name:<slug>) -> the module file chosen for it."""
    return registry.binding_store()


def set_bindings(data: dict[str, str]) -> None:
    """Replaces every file choice (Undo puts a saved set back)."""
    from gremlin.config import Configuration

    registry.binding_store()  # registers the setting
    Configuration().set(
        "global", "internal", "module-file-bindings", json.dumps(dict(data))
    )


def bind(device_name: str, guid: str, slug: str) -> str:
    """Records that the device uses module file slug (by its id and by its
    name). The slug, or "" when there is no id to record it by."""
    slug = plain_slug(slug)
    key = stored_guid_key(guid) or registry.guid_for_name(device_name)
    if not slug or not key:
        return ""
    data = bindings()
    data[key] = slug
    name_key = registry.name_key(device_name)
    if name_key:
        data[name_key] = slug
    set_bindings(data)
    return slug


def unbind(device_name: str, guid: str = "") -> None:
    """Forgets the device's file choice (by its id and by its name)."""
    data = bindings()
    key = stored_guid_key(guid) or registry.guid_for_name(device_name)
    name_key = registry.name_key(device_name)
    changed = False
    for each in (key, name_key):
        if each and each in data:
            data.pop(each, None)
            changed = True
    if changed:
        set_bindings(data)


def unbind_file(slug: str) -> None:
    """Forgets every choice of module file slug."""
    data = bindings()
    want = plain_slug(slug)
    keys = [key for key, value in data.items() if plain_slug(value) == want]
    if not keys:
        return
    for key in keys:
        data.pop(key, None)
    set_bindings(data)


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


def users_of(slug: str) -> set[str]:
    """Who uses module file slug: file choice keys, and connected devices
    whose file it is."""
    users: set[str] = set()
    for key, value in bindings().items():
        if plain_slug(value) == slug:
            users.add(key)
    for dev in live_devices():
        guid = stored_guid_key(getattr(dev, "device_guid", ""))
        name = str(getattr(dev, "name", "") or "")
        if guid and name and registry.resolve_module_slug(name, guid) == slug:
            users.add(guid)
    return users


def _library_ids() -> set[str]:
    """The ids of the devices the Device Library has a record of."""
    try:
        from gremlin import device_library

        records = device_library._read().get("devices") or []
    except Exception:  # noqa: BLE001 - no Library: it knows no device
        return set()
    ids = {
        guid_key(stored_guid_key(rec.get("guid", "")))
        for rec in records
        if isinstance(rec, dict)
    }
    return ids - {""}


def other_users(slug: str, device_name: str, guid: str = "") -> set[str]:
    """The other devices that use module file slug: plugged in now, or one
    the Device Library has as a separate device (03 S94). A choice left by
    any other id (an old id of the same stick) is stale and doesn't count.
    Name entries are left out: each is saved with its device's id, and a
    renamed stick's old name entry is the stick itself."""
    key = stored_guid_key(guid) or registry.guid_for_name(device_name)
    own = guid_key(key)
    users = {
        user
        for user in users_of(slug)
        if not user.startswith("name:") and not (own and guid_key(user) == own)
    }
    if not users:
        return users
    known = _library_ids()
    return {
        user
        for user in users
        if _live(user) or guid_key(stored_guid_key(user)) in known
    }


def is_shared(device_name: str, guid: str = "") -> bool:
    """True when another device uses the file this one uses."""
    path = path_for(device_name, guid)
    return path.is_file() and bool(other_users(path.stem, device_name, guid))


def foreign_file(device_name: str, guid: str = "") -> str:
    """The file the device uses when it isn't the one named after it (a
    renamed stick, a chosen file); "" otherwise."""
    used = slug_for(device_name, guid)
    return used if used and used != own_slug(device_name) else ""


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

    def touch(name: str, guid: str = "", connected: bool = False) -> None:
        label = " ".join(str(name or "").split())
        key = label.lower()
        if not key:
            return
        id_key = "" if registry.is_output_name(label) else stored_guid_key(guid)
        path = path_for(label, guid)
        row = rows.get("id:" + id_key) if id_key else None
        if row is None and not id_key:
            same = by_name(key)
            # A name with no id (a file only) is the device of that name;
            # with several of that name (twins) it is none of them.
            if len(same) > 1:
                return
            row = same[0] if same else None
        if row is None:
            rows["id:" + id_key if id_key else "name:" + key] = {
                "name": label,
                "guid": guid,
                "connected": bool(connected),
                "hasFile": path.is_file(),
                "fileName": path.name,
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
        touch(str(doc.get("device") or "").strip() or path.stem, "", False)
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
            path = path_for(own, text)
            return {
                "name": own,
                "guid": text,
                "connected": True,
                "hasFile": path.is_file(),
                "fileName": path.name,
            }
        for row in known_devices():
            if stored_guid_key(row.get("guid", "")) == key:
                return row
        # Unplugged, its module file found by its id (a twin's shares the
        # other twin's name, so the name would find the wrong one, 10 S41).
        found = file_of_guid(guid)
        if found is not None:
            doc = registry.read_doc(found) or {}
            own = " ".join(str(doc.get("device") or name or found.stem).split())
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


def unique_archive(stem: str, stamp: str = "") -> Path:
    """A free imported/<stem>.<stamp>.json for a backup an import keeps."""
    stamp = stamp or archive_stamp()
    path = imported_dir() / f"{stem}.{stamp}.json"
    number = 2
    while path.exists():
        path = imported_dir() / f"{stem}.{stamp}_{number}.json"
        number += 1
    return path


# --- Module Setup's "Import from" ------------------------------------------------


def import_choices() -> list[str]:
    """The files in modules/imported to import from ("imported/<name>").
    Live module files are not listed."""
    base = imported_dir()
    if not base.is_dir():
        return []
    return [f"imported/{p.stem}" for p in sorted(base.glob("*.json")) if p.is_file()]


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
    """The Button Map nodes whose control is in these sets (groups keep the
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
    previous_image: str = "",
) -> tuple[dict, str]:
    """A module document copied onto this device: only the controls it has,
    its own name and id, its own picture. (the copy, what was left out)."""
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
    payload["nodes"] = filter_nodes(nodes, *kept)
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
    left.extend(f"Button {n}" for n in sorted(source_buttons - kept_buttons))
    left.extend(f"Axis {n}" for n in sorted(source_axes - kept_axes))
    left.extend(f"Hat {n}" for n in sorted(source_hats - kept_hats))
    left.extend(f"Key {n}" for n in sorted(source_keys - kept_keys))
    return payload, _left_out_text(left)


def resolve_import_source(file_name: str) -> Path | None:
    """The file "Import from" names: a path or file: URL, "imported/<name>",
    or a module file's name. None when there is no such file."""
    raw = str(file_name or "").strip()
    if not raw:
        return None
    if "://" in raw or raw.lower().startswith("file:"):
        try:
            src = _local_path(raw)
        except Exception:  # noqa: BLE001 - not a local file
            return None
        return src if src and Path(src).is_file() else None
    direct = Path(raw)
    if direct.is_file():
        return direct
    rel = raw.replace("\\", "/")
    if rel.lower().endswith(".json"):
        rel = rel[:-5]
    if rel.lower().startswith("imported/"):
        path = imported_dir() / f"{Path(rel).name}.json"
        return path if path.is_file() else None
    path = path_of(plain_slug(rel))
    return path if path.is_file() else None


def file_direction(doc: dict, path: Path) -> str:
    """The direction a file to import from is taken as: a vjoy* file is an
    output, anything else an input."""
    del doc
    return "dest" if Path(path).stem.lower().startswith("vjoy") else "source"


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
# (device key, window) -> {"dest", "previous", "bindings", "at"}.
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
    """Puts this device's previous file back (or removes the new one) and
    binds again the devices the import unbound (03 S59, 08 S85). The chosen
    file is not touched. What happened, in words."""
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
    if record.get("bindings") is not None:
        set_bindings(record["bindings"])
    _file_import_undo.pop(key, None)  # type: ignore[arg-type]
    return "Undone. " + note


def import_file(
    device_name: str,
    guid: str,
    file_name: str,
    direction: str = "source",
    window: str = "Configure Module",
) -> str:
    """Copies a module file onto the file this device uses (03 S55, Q13: a
    renamed stick's old file, not a new one named after it). The chosen file
    stays where it is; the previous file is kept in imported. A damaged
    current file is refused. What happened, in words (lines)."""
    name = str(device_name or "").strip()
    if not name:
        return "That file could not be read."
    src = resolve_import_source(file_name)
    if src is None or not src.is_file():
        return "That file could not be read."
    dest = path_for(name, guid)
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
    previous_image = ""
    previous_bytes: bytes | None = None
    if dest.is_file():
        try:
            previous_bytes = dest.read_bytes()
            previous = json.loads(previous_bytes.decode("utf-8"))
        except (OSError, UnicodeError, ValueError):
            registry.trace("READ", window, "import_file", dest, "error")
            return "The current file could not be read, so it was not replaced."
        if not isinstance(previous, dict):
            return "The current file could not be read, so it was not replaced."
        previous_image = str(previous.get("image") or "")
    payload, left = prepare_imported_doc(
        doc,
        name,
        str(guid or ""),
        target,
        buttons,
        axes,
        hats,
        keep_keys=keep_keys,
        previous_image=previous_image,
    )
    try:
        replace(dest, (json.dumps(payload, indent=2) + "\n").encode("utf-8"), window)
    except (OSError, module_file.ModuleFileDamaged):
        return "The module file could not be written."
    claim = _dict(payload.get("claim"))
    friendly = _dict(claim.get("friendly"))
    lines = [
        f"Imported into {dest.name}.",
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
    if previous_image:
        lines.append("The picture already on this device was kept.")
    else:
        lines.append("No picture was added from the chosen file.")
    lines.append("Profile wires were not changed.")
    lines.append("The chosen file was left where it was.")
    if previous_bytes is not None:
        backup = imported_dir() / f"{dest.stem}.{archive_stamp()}.json"
        try:
            if backup.exists():
                raise FileExistsError(backup)
            replace(backup, previous_bytes, window)
            lines.append("The previous file was saved as")
            lines.append(backup.name.replace("-", "‑"))
        except OSError:
            lines.append("The previous file could not be saved to imported.")
    saved_bindings = bindings()
    unbind_file(src.stem)
    if dest.stem == own_slug(name):
        unbind(name, str(guid or ""))
    # Otherwise the device keeps its choice of the file it uses (03 Q13): a
    # renamed stick's, or a name-only device's (Keyboard has no id to bind
    # it again by).
    global _undo_serial
    _undo_serial += 1
    _file_import_undo[_undo_key(name, str(guid or ""), window)] = {
        "dest": str(dest),
        "previous": previous_bytes,
        "bindings": saved_bindings,
        "at": _undo_serial,
    }
    return "\n".join(lines)
