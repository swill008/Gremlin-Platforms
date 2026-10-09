# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library store (10 Device Library): the one writer of the
library list (library.json) and of the saved setups' packs.

- where:     folder (setting device-library-folder, default
             <data folder>\\device library), pack_path
- devices:   devices, device, find_device (S6-S9)
- keeping:   save_setup (S12), autosave (S16-S21, always on)
- editing:   rename, describe (S7, S13), delete (S15), add_history (S11)
- sharing:   import_pack (S35, S39), export_setup (S14)
- tidying:   tidy_preview, tidy (S38), size_bytes (S4), search (S5)
- settings:  settings, set_settings (S36-S37)
- undo:      set_last_change, last_change (S41)
- now:       inputs, note_seen (S8), photo (S11), current_pack (S22)

Each saved setup is a Device Pack (08 S49-S55), built with
gremlin.ui.device_pack. Bindings of a profile that isn't open come from
gremlin.library_profiles.read_profile. Module files are only read here
(through gremlin.modules.store and registry). Nothing is read from the old
deleted devices folder (S9, S37, D-10-NO-DELETED-FOLDER).

Writes are atomic (module_file.write_bytes) and every read-modify-write of
library.json holds one lock. Building a pack reads the profile, so the
functions that build one (save_setup, autosave) run on the main thread;
size_bytes reads only files and is safe anywhere.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import shutil
import threading
import uuid
import zipfile
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from gremlin import clock
from gremlin.modules import module_file
from gremlin.modules.ids import stored_guid_key

if TYPE_CHECKING:
    from gremlin.profile import Profile

syslog = logging.getLogger("system")

PARTS = ["setup", "button_map", "appearance", "calibration", "bindings"]
# A damaged module file kept exactly as it was (S20a): never copied or
# swapped onto another stick; only the setup's bindings can be.
DAMAGED_PART = "setup_damaged"
# Where the damaged file's bytes sit inside the pack (beside map.json, which
# then holds nothing from it but {"damaged": {"file", "reason"}}).
DAMAGED_ENTRY = "damaged/"
# An autosave also keeps the module file's bytes exactly, so Undo puts it
# back as it was, parts it lacked included (S25, S41).
EXACT_ENTRY = "exact/"
# The order holds are listed in.
HOLDS = ["setup", DAMAGED_PART, "button_map", "appearance", "calibration", "bindings"]
PART_LABELS = {
    DAMAGED_PART: "Setup (damaged file, kept as is)",
    "setup": "Setup",
    "button_map": "Button Map",
    "appearance": "Appearance",
    "calibration": "Calibration",
    "bindings": "Bindings",
}
# What Copy and Swap tick to start (S23, S36): Calibration off.
DEFAULT_PARTS = ["setup", "button_map", "appearance", "bindings"]
TRIGGERS = ("deleted", "module_file", "copy", "swap", "output", "pack")
DEFAULT_KEEP = 10
SETTING = "device-library-folder"
LIST_NAME = "library.json"
_FORMAT = 1

_LOCK = threading.RLock()


class LibraryDamaged(Exception):
    """library.json exists but can't be read: it is never written over."""


# --- small helpers ---------------------------------------------------------------


def _result(ok: bool = True, error: str = "", **extra: object) -> dict:
    out = {"ok": ok, "error": error, "warnings": [], "notes": []}
    out.update(extra)
    return out


def _now() -> datetime:
    return datetime.fromtimestamp(clock.now())


def _iso(moment: datetime | None = None) -> str:
    return (moment or _now()).isoformat(timespec="seconds")


def _parse_iso(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(text))
    except ValueError:
        return None


def _new_key(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _derived_key(name: str, guid: str) -> str:
    """A stable key for a device the list doesn't hold yet."""
    basis = stored_guid_key(guid) or "name:" + _collapsed(name)
    return "dev-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8]


def _collapsed(value: str) -> str:
    return " ".join(str(value or "").split()).lower()


def _clean(value: str) -> str:
    return " ".join(str(value or "").split())


def _file_name(text: str) -> str:
    from gremlin.modules import store

    return store.pack_file_name(text)


# --- where -------------------------------------------------------------------------


def _register_setting() -> None:
    """Registers device-library-folder (01 Folders style) when nothing has."""
    from gremlin import util
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    cfg = Configuration()
    if cfg.exists("global", "files", SETTING):
        return
    default = str(Path(util.data_folder()) / "device library")
    cfg.register(
        "global",
        "files",
        SETTING,
        PropertyType.Path,
        default,
        "The Device Library: saved setups and autosaves.",
        {"is_folder": True, "allow_reset": True, "default_path": default},
        True,
    )


def folder() -> Path:
    """The library folder: its own setting, default <data folder>\\device
    library (S37). Tests point it elsewhere by patching this function."""
    from gremlin import util

    try:
        _register_setting()
    except Exception:  # noqa: BLE001 - no configuration yet: the default
        pass
    return Path(util._configured_child(SETTING, "device library"))


def _list_path() -> Path:
    return folder() / LIST_NAME


def _empty() -> dict:
    return {
        "format": _FORMAT,
        "settings": {"keep": DEFAULT_KEEP, "default_parts": list(DEFAULT_PARTS)},
        "devices": [],
        "lastChange": None,
    }


def _load() -> dict:
    """library.json, or an empty list when there is none. Raises
    LibraryDamaged when it can't be read."""
    path = _list_path()
    if not path.is_file():
        return _empty()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LibraryDamaged(f"{path.name} could not be read: {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("devices", []), list):
        raise LibraryDamaged(f"{path.name} is not a library list.")
    base = _empty()
    base.update(doc)
    if not isinstance(base.get("settings"), dict):
        base["settings"] = _empty()["settings"]
    return base


def _save(doc: dict) -> None:
    data = (json.dumps(doc, indent=2) + "\n").encode("utf-8")
    with _action():
        _note_list()
        module_file.write_bytes(_list_path(), data)


@contextlib.contextmanager
def _editing(title: str = "", quiet: bool = False) -> Iterator[dict]:
    """The list to change, under the lock; written when the block ends
    without an error. title/quiet: its History entry (_action)."""
    with _LOCK, _action(title, quiet):
        doc = _load()
        yield doc
        _save(doc)


# --- History (S51, 08 S12a) --------------------------------------------------------
#
# Every write of the list and every pack written or removed is noted
# (_note_list, _note_file) inside an _action: one user action is one History
# entry (area "modules", kind "library") holding the list and each pack it
# touched as they were before and after, so Restore puts them back.

HISTORY_KIND = "library"
# The action being recorded; set only while _LOCK is held (a pack written by
# _bg on a program thread notes into it while the caller waits).
_current: dict | None = None


@contextlib.contextmanager
def _action(title: str = "", quiet: bool = False) -> Iterator[dict]:
    """One History entry for what the block changes. Nested: part of the
    outer one (its title offered to it). quiet: bookkeeping (when sticks
    were seen, Undo's last change, a saved setup's own log), no entry."""
    global _current
    with _LOCK:
        if _current is not None:
            _name_action(title)
            yield _current
            return
        act: dict = {"title": title, "titles": [], "files": {}, "quiet": quiet}
        _current = act
        try:
            yield act
        finally:
            _current = None
            if not quiet:
                try:
                    _finish(act)
                except Exception:  # noqa: BLE001 - History never stops a change
                    syslog.exception("Device Library: the change was not recorded")


def _name_action(title: str) -> None:
    """What the action open now did (its title when it was given none)."""
    if _current is not None and title:
        _current["titles"].append(title)


def _list_text() -> str | None:
    try:
        return _list_path().read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _note_list() -> None:
    if _current is not None and "list" not in _current:
        _current["list"] = _list_text()


def _rel(path: Path) -> str | None:
    try:
        return Path(path).resolve().relative_to(folder().resolve()).as_posix()
    except (OSError, ValueError):
        return None


def _kept(path: Path) -> dict:
    from gremlin import history

    if not Path(path).is_file():
        return {"exists": False, "keptFile": ""}
    return {"exists": True, "keptFile": history.keep_file(Path(path))}


def _note_file(path: Path) -> None:
    """A pack about to be written or removed: kept as it is now."""
    if _current is None:
        return
    rel = _rel(path)
    if rel and rel != LIST_NAME and rel not in _current["files"]:
        _current["files"][rel] = _kept(folder() / rel)


def _finish(act: dict) -> None:
    from gremlin import history

    before: dict = {"files": []}
    after: dict = {"files": []}
    changed = False
    if "list" in act:
        now = _list_text()
        before["text"], after["text"] = act["list"], now
        changed = act["list"] != now
    for rel, was in sorted(act["files"].items()):
        now = _kept(folder() / rel)
        before["files"].append({"file": rel, **was})
        after["files"].append({"file": rel, **now})
        changed = changed or now != was
    if not changed:
        return
    titles = list(dict.fromkeys(act["titles"]))
    if act["title"]:
        title = act["title"]
    elif len(titles) == 1:
        title = titles[0]
    elif titles:
        title = f"Changed {len(titles)} things in the Device Library"
    else:
        title = "Changed the Device Library"
    subject = {
        "library": str(folder()),
        "files": [f["file"] for f in after["files"]],
    }
    history.record("modules", title, subject, before, after, kind=HISTORY_KIND)


def history_text(side: dict | None) -> str:
    """A Library entry's side as the History window shows it: each device
    with its saved setups, then the packs."""
    if not side:
        return "Not there."
    lines: list[str] = []
    if "text" in side:
        text = side.get("text")
        try:
            doc = json.loads(text) if text is not None else None
        except ValueError:
            doc = None
        if text is None:
            lines.append("No Device Library list.")
        elif not isinstance(doc, dict):
            lines.append("The Device Library list can't be read.")
        else:
            for rec in doc.get("devices") or []:
                if not isinstance(rec, dict):
                    continue
                lines.append(_clean(rec.get("name") or rec.get("ownName") or "?"))
                for setup in rec.get("setups") or []:
                    if isinstance(setup, dict):
                        lines.append(f"    {_clean(setup.get('name') or '?')}")
            if not lines:
                lines.append("No devices.")
    for item in side.get("files") or []:
        state = "" if item.get("exists") else " (not there)"
        lines.append(f"File {item.get('file')}{state}")
    return "\n".join(lines)


def restore_history(entry: dict, side: dict | None) -> tuple[bool, str]:
    """Restore of a Library entry: the list and each pack it touched as
    they were on that side. Recorded as a new entry."""
    from gremlin import history

    if not side:
        return False, "There is nothing to put back."
    base = folder()
    title = str(entry.get("title") or "a Device Library change")
    missing: list[str] = []
    with _action(f"Put back from History: {title}"):
        for item in side.get("files") or []:
            rel = str(item.get("file") or "")
            path = base / rel
            if not rel or rel == LIST_NAME or not _inside(path, base):
                continue
            _note_file(path)
            try:
                if item.get("exists"):
                    kept = history.kept_file(str(item.get("keptFile") or ""))
                    if kept is None:
                        missing.append(rel)
                        continue
                    module_file.write_bytes(path, kept.read_bytes())
                elif path.is_file():
                    path.unlink()
            except OSError as exc:
                return False, f"{path.name} could not be put back. {exc}"
        if "text" in side:
            _note_list()
            text = side.get("text")
            try:
                if text is None:
                    _list_path().unlink(missing_ok=True)
                else:
                    module_file.write_bytes(_list_path(), str(text).encode("utf-8"))
            except OSError as exc:
                return False, f"The Device Library list could not be put back. {exc}"
    _drop_empty_folders()
    if missing:
        return True, (
            "Put back the Device Library, without these saved setups (no copy "
            f"was kept): {', '.join(missing)}."
        )
    return True, "Put back the Device Library as it was."


def _read() -> dict:
    with _LOCK:
        try:
            return _load()
        except LibraryDamaged as exc:
            syslog.warning(f"Device Library: {exc}")
            return _empty()


# --- settings (S36-S37) ------------------------------------------------------------


def settings() -> dict:
    """{"keep", "default_parts", "folder"}. Autosaves are always on
    (D-10-STREAMLINE)."""
    stored = _read().get("settings") or {}
    keep = stored.get("keep", DEFAULT_KEEP)
    try:
        keep = max(1, int(keep))
    except (TypeError, ValueError):
        keep = DEFAULT_KEEP
    parts = [p for p in (stored.get("default_parts") or []) if p in PARTS]
    if not isinstance(stored.get("default_parts"), list):
        parts = list(DEFAULT_PARTS)
    return {"keep": keep, "default_parts": parts, "folder": str(folder())}


def set_settings(values: dict) -> None:
    """Changes any of keep, default_parts and folder. A new folder gets the
    library moved into it (Move…, S36); refused (ValueError) when it already
    holds another library."""
    values = dict(values or {})
    target = str(values.pop("folder", "") or "").strip()
    if target and Path(target) != folder():
        _move_to(Path(target))
    if not values:
        return
    with _editing("Changed the Device Library's settings") as doc:
        stored = doc.setdefault("settings", {})
        if "keep" in values:
            stored["keep"] = max(1, int(values["keep"]))
        if "default_parts" in values:
            stored["default_parts"] = [
                p for p in PARTS if p in list(values["default_parts"] or [])
            ]
        _apply_limits(doc)


def _inside(path: Path, base: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(base).resolve())
    except (OSError, ValueError):
        return False
    return True


_T = TypeVar("_T")


def _bg(name: str, fn: Callable[..., _T], *args: object) -> _T:
    """fn(*args) on a program thread while the window keeps painting
    (section 6; library_profiles.background). Only file work: fn never
    touches the open profile, the registry, device lists or settings."""
    from gremlin import library_profiles

    return library_profiles.background(name, fn, *args)


def _sync(source: Path, target: Path) -> None:
    """Copies what target lacks or holds differently (size or time)."""
    if not source.is_dir():
        return
    for item in source.rglob("*"):
        dest = target / item.relative_to(source)
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        try:
            mine, theirs = item.stat(), dest.stat()
            if (mine.st_size, mine.st_mtime_ns) == (theirs.st_size, theirs.st_mtime_ns):
                continue
        except OSError:
            pass
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, dest)


def _move_to(target: Path) -> None:
    """Move… (S36): the packs are copied without holding the lock, so an
    autosave on the main thread never waits for the whole copy; then, under
    the lock, only what changed meanwhile is copied and the folder switched.
    Refused into a folder inside the library folder."""
    from gremlin.config import Configuration

    source = folder()
    if _inside(target, source):
        raise ValueError(
            f"{target} is inside the Device Library's folder: choose another folder."
        )
    if (target / LIST_NAME).exists():
        raise ValueError(f"{target} already holds a Device Library.")
    made = not target.exists()
    before: set[Path] = set()
    try:
        target.mkdir(parents=True, exist_ok=True)
        before = set(target.rglob("*"))
        _bg("copy Device Library", _sync, source, target)
        with _LOCK:
            _sync(source, target)
            _register_setting()
            Configuration().set("global", "files", SETTING, str(target))
    except BaseException:
        # What this copied goes again, so a later Move… isn't refused.
        _undo_copy(target, before, made)
        raise
    if source.is_dir() and source != target:
        _bg("remove old Device Library", _remove_own, source)


def _undo_copy(target: Path, before: set[Path], made: bool) -> None:
    """Removes what a failed Move… copied into target (only that)."""
    if not target.is_dir():
        return
    for path in sorted(target.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path in before:
            continue
        try:
            if path.is_dir():
                path.rmdir()
            else:
                path.unlink()
        except OSError:
            pass
    if made:
        try:
            target.rmdir()
        except OSError:
            pass


def _remove_own(source: Path) -> None:
    """After Move…: the Library's own files leave the old folder, and the
    folder too when nothing else is in it (S36). Anything else stays."""
    files = _own_files(source)
    for path in files:
        try:
            path.unlink()
        except OSError:
            pass
    dirs = {p.parent for p in files if p.parent != source}
    for each in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        try:
            each.rmdir()
        except OSError:
            pass
    try:
        source.rmdir()
    except OSError:
        pass


# --- devices (S6-S9) ---------------------------------------------------------------


def _connected() -> list[tuple[str, str]]:
    """(name, guid) of each stick plugged in now (vJoy left out)."""
    from gremlin.modules import store

    found = []
    try:
        from gremlin import device_initialization

        for dev in device_initialization.physical_devices() or []:
            name = _clean(getattr(dev, "name", ""))
            guid = store.guid_text(getattr(dev, "device_guid", ""))
            if name:
                found.append((name, guid))
    except Exception:  # noqa: BLE001 - no device list yet
        pass
    return found


def _set_up() -> list[tuple[str, str, str]]:
    """(name, guid, slug) of each input module file here, the built-in
    inputs too (S6)."""
    return [(name, guid, slug) for name, guid, slug, _built in _modules()]


def _modules() -> list[tuple[str, str, str, bool]]:
    """(name, guid, slug, built-in) of each input module file here (S6):
    Keyboard and OSC are built-in inputs (D-10-BUILTIN-SECTION)."""
    from gremlin.modules import registry

    found = []
    for module in registry.inputs():
        doc = module.doc or {}
        if doc.get("kind") not in (None, "control.hardware"):
            continue
        found.append(
            (
                module.name,
                module.bound_guid,
                module.slug,
                registry.is_built_in_input(module),
            )
        )
    return found


def is_built_in_guid(guid: str) -> bool:
    """True for the device id of a built-in input, Keyboard or OSC (S6)."""
    from gremlin.modules import ids

    want = stored_guid_key(guid)
    return bool(want) and want in (
        stored_guid_key(str(ids.KEYBOARD)),
        stored_guid_key(str(ids.OSC)),
    )


def built_in_refusal(name: str, what: str) -> str:
    """Why an action isn't offered for a built-in input (S6)."""
    return f"{name or 'This'} is a built-in input: {what} isn't offered for it."


def _alias(guid: str, default: str) -> str:
    """The name the Home card shows (S7)."""
    if not guid:
        return default
    try:
        from gremlin import device_aliases as device_names

        return device_names.display_name(guid, default)
    except Exception:  # noqa: BLE001 - no settings: the device's own name
        return default


def own_name(name: str, guid: str = "") -> str:
    """The device's own name, which finds its module file, for the name a
    caller has (the Home card's alias, or its own) and its device id: the id
    decides (S7). Set up here: its module file's name; plugged in: the device
    list's; else the Library's record; else the name as given."""
    name = _clean(name)
    want = stored_guid_key(guid)
    if not want:
        return name
    try:
        for own, bound, _slug in _set_up():
            if own and stored_guid_key(bound) == want:
                return _clean(own)
    except Exception:  # noqa: BLE001 - no module list yet: the device list
        pass
    for own, plugged in _connected():
        if own and stored_guid_key(plugged) == want:
            return own
    for rec in _read().get("devices") or []:
        if isinstance(rec, dict) and stored_guid_key(rec.get("guid", "")) == want:
            return _clean(rec.get("ownName") or rec.get("name") or name) or name
    return name


def short_id(guid: str) -> str:
    """A few characters of a device id, to tell twins apart (as the list)."""
    return "".join(c for c in str(guid or "") if c.isalnum())[:8].upper()


def shown(name: str, guid: str = "") -> str:
    """The name the user reads for a device in autosave names, Undo labels
    and messages (S7, S17, S41): its Home card's name (the Library's row),
    never the internal own name; a twin (another device of the same name)
    with its short id, as the list shows it ("T.16000M [EEEE0006]")."""
    want = stored_guid_key(guid)
    label = _clean(name)
    if not want:
        return label
    try:
        rows = devices()
    except Exception:  # noqa: BLE001 - no list: the Home name alone
        rows = []
    row = next((r for r in rows if stored_guid_key(r.get("guid", "")) == want), None)
    if row is not None and row.get("name"):
        label = _clean(row["name"])
    else:
        label = _alias(guid, own_name(name, guid) or label) or label
    # Another device id with the same name: a twin.
    same = [r for r in rows if _collapsed(r.get("name", "")) == _collapsed(label)]
    others = {stored_guid_key(r.get("guid", "")) for r in same} - {want, ""}
    if others and short_id(guid):
        return f"{label} [{short_id(guid)}]"
    return label


def _set_alias(guid: str, name: str) -> None:
    from gremlin import device_aliases as device_names

    device_names.set_alias(guid, name)


def _match(records: list[dict], name: str, guid: str) -> dict | None:
    want = stored_guid_key(guid)
    if want:
        for rec in records:
            if stored_guid_key(rec.get("guid", "")) == want:
                return rec
    named = _collapsed(name)
    if not named:
        return None
    for rec in records:
        if want and rec.get("guid") and stored_guid_key(rec["guid"]) != want:
            continue
        if (
            _collapsed(rec.get("name", "")) == named
            or _collapsed(rec.get("ownName", "")) == named
        ):
            return rec
    return None


def _setup_out(rec: dict, setup: dict) -> dict:
    out = {
        "key": setup["key"],
        "device": rec["key"],
        "name": setup.get("name", ""),
        "description": setup.get("description", ""),
        "created": setup.get("created", ""),
        "origin": setup.get("origin", "user"),
        "own": bool(setup.get("own")),
        "reason": setup.get("reason", ""),
        "holds": [p for p in HOLDS if p in (setup.get("holds") or [])],
        "profiles": list(setup.get("profiles") or []),
        "vjoys": dict(setup.get("vjoys") or {}),
        "pack": str(folder() / setup.get("file", "")),
        "history": list(setup.get("history") or []),
    }
    if "covers" in setup:
        out["covers"] = list(setup.get("covers") or [])
        out["moduleFile"] = str(setup.get("moduleFile") or "")
    return out


def _view(doc: dict) -> list[dict]:
    """Every device: the list's records joined with the sticks set up here
    and the ones plugged in now."""
    records = [rec for rec in doc.get("devices") or [] if isinstance(rec, dict)]
    rows: dict[str, dict] = {}
    order: list[str] = []

    def row_for(rec: dict | None, name: str, guid: str) -> dict:
        key = rec["key"] if rec else _derived_key(name, guid)
        row = rows.get(key)
        if row is None:
            row = {
                "key": key,
                "name": (rec or {}).get("name") or name,
                "description": (rec or {}).get("description", ""),
                "state": "",
                "guid": (rec or {}).get("guid") or guid,
                "module": "",
                "builtIn": False,
                # The device's own name (the module file's, or the plugged-in
                # stick's): with the guid it finds the stick (S7).
                "ownName": (rec or {}).get("ownName")
                or (rec or {}).get("name")
                or name,
                "seen": (rec or {}).get("seen", ""),
                "setups": [],
                "_rec": rec,
            }
            rows[key] = row
            order.append(key)
        if guid and not row["guid"]:
            row["guid"] = guid
        return row

    for name, guid, slug, built in _modules():
        row = row_for(_match(records, name, guid), name, guid)
        row["module"] = slug
        row["ownName"] = name
        row["name"] = _alias(row["guid"], name)
        # A built-in input is never plugged in or unplugged (S6).
        row["builtIn"] = row["builtIn"] or built
        row["state"] = "builtin" if row["builtIn"] else row["state"] or "not_connected"
    for name, guid in _connected():
        row = row_for(_match(records, name, guid), name, guid)
        if not row["module"]:
            row["ownName"] = name
            row["name"] = _alias(guid, name)
        row["state"] = "connected"
        row["seen"] = "now"
    for rec in records:
        row = row_for(rec, rec.get("name", ""), rec.get("guid", ""))
        if is_built_in_guid(row["guid"]):
            row["builtIn"] = True
            row["state"] = "builtin"
        if not row["state"]:
            row["state"] = (
                "deleted" if rec.get("kind") == "deleted" else "not_connected"
            )
    seen_map = doc.get("seen")
    seen: dict = seen_map if isinstance(seen_map, dict) else {}
    out = []
    for key in order:
        row = rows[key]
        rec = row.pop("_rec")
        noted = str(seen.get(stored_guid_key(row["guid"]), "")) if row["guid"] else ""
        if row["seen"] != "now" and noted > str(row["seen"] or ""):
            row["seen"] = noted
        setups = list((rec or {}).get("setups") or [])
        setups = _newest_first(setups)
        row["setups"] = [_setup_out(row, s) for s in setups]
        out.append(row)
    # The built-in inputs come after every device (S6).
    out.sort(key=lambda r: (r["builtIn"], _collapsed(r["name"])))
    return out


def devices() -> list[dict]:
    """S6, S9: set-up devices, connected ones, deleted ones (since the
    Library exists) and devices only from packs (Not connected)."""
    with _LOCK:
        return _view(_read())


def device(key: str) -> dict | None:
    for row in devices():
        if row["key"] == key:
            return row
    return None


def find_device(name: str, guid: str = "") -> dict | None:
    rows = devices()
    want = stored_guid_key(guid)
    if want:
        for row in rows:
            if stored_guid_key(row["guid"]) == want:
                return row
    named = _collapsed(name)
    for row in rows:
        if want and row["guid"] and stored_guid_key(row["guid"]) != want:
            continue
        if named and _collapsed(row["name"]) == named:
            return row
    return None


def _record(doc: dict, name: str, guid: str) -> dict:
    """The list's record for a device, made when there is none."""
    records = doc.setdefault("devices", [])
    rec = _match(records, name, guid)
    if rec is None:
        view = [r for r in _view(doc) if r["key"] == _derived_key(name, guid)]
        rec = {
            "key": view[0]["key"] if view else _derived_key(name, guid),
            "name": _clean(name),
            "ownName": _clean(name),
            "description": "",
            "guid": guid,
            "kind": "setup",
            "seen": "",
            "setups": [],
        }
        if any(r.get("key") == rec["key"] for r in records):
            rec["key"] = _new_key("dev")
        records.append(rec)
    if guid and not rec.get("guid"):
        rec["guid"] = guid
    return rec


def _pack_record(doc: dict, name: str) -> dict:
    """A Not connected device for a pack whose device isn't in the Library
    (S35): a record of its own, never another device's of the same name."""
    records = doc.setdefault("devices", [])
    for rec in records:
        if (
            rec.get("kind") == "pack"
            and not rec.get("guid")
            and _collapsed(rec.get("name", "")) == _collapsed(name)
        ):
            return rec
    taken = {r.get("key") for r in records} | {r["key"] for r in _view(doc)}
    key = _derived_key(name, "")
    rec = {
        "key": key if key not in taken else _new_key("dev"),
        "name": _clean(name),
        "ownName": _clean(name),
        "description": "",
        "guid": "",
        "kind": "pack",
        "seen": "",
        "setups": [],
    }
    records.append(rec)
    return rec


def _find_setup(doc: dict, key: str) -> tuple[dict, dict] | None:
    for rec in doc.get("devices") or []:
        for setup in rec.get("setups") or []:
            if setup.get("key") == key:
                return rec, setup
    return None


def _find_record(doc: dict, key: str) -> dict | None:
    for rec in doc.get("devices") or []:
        if rec.get("key") == key:
            return rec
    return None


# --- building packs ------------------------------------------------------------------


def read_profile(path: Path) -> Profile | str:
    """A profile that isn't open (LP's reader; a test may replace this)."""
    from gremlin.library_profiles import read_profile as lp_read

    return lp_read(path)


def _open_profile() -> Profile | None:
    from gremlin import shared_state

    return shared_state.current_profile


def _is_open(path: Path) -> bool:
    current = _open_profile()
    if current is None:
        return False
    if not str(path) or str(path) == ".":
        return current.fpath is None
    if current.fpath is None:
        return False
    try:
        return Path(current.fpath).resolve() == Path(path).resolve()
    except OSError:
        return str(current.fpath) == str(path)


def _profile_for(path: Path) -> Profile | str:
    if _is_open(path):
        current = _open_profile()
        assert current is not None
        return current
    return read_profile(Path(path))


def _resolve(stored: str) -> Path | None:
    """A module file's picture on disk (as Device Pack Export finds them)."""
    from gremlin.modules import store

    found = store.find_picture(stored)
    if found is not None:
        return found
    text = (stored or "").strip().replace("\\", "/")
    if not text or text.startswith("file:") or Path(text).is_absolute():
        return None
    try:
        from gremlin.util import program_folder

        installed = Path(program_folder()) / text
    except Exception:  # noqa: BLE001
        return None
    return installed if installed.is_file() else None


def _build(
    name: str, guid: str, profile: Profile | None, keep_damaged: bool = False
) -> tuple[bytes, dict] | str:
    """The pack of a device: its module file and pictures, and its wires in
    every mode of profile (None: no bindings). A str says why it can't.

    keep_damaged (autosaves, S20a): a damaged module file goes in exactly as
    it is, as DAMAGED_ENTRY + its name, beside a map.json with only the
    device's name and {"damaged": {"file", "reason"}}; info["damaged"] is
    (entry, bytes) for the read-back."""
    from gremlin.modules import store
    from gremlin.ui import device_pack

    modes: list[str] | None = None if profile is not None else []
    # Its own file by its id: a twin's, never the other twin's (S41).
    path = store.path_for_id(name, guid)
    damaged: tuple[str, bytes] | None = None
    if path.is_file():
        reason = store.damage_of(path)
        if not (reason and keep_damaged):
            built = device_pack.assemble(name, _resolve, modes, None, profile, guid)
            if isinstance(built, str) or not keep_damaged:
                return built
            try:
                exact = (EXACT_ENTRY + path.name, path.read_bytes())
            except OSError as exc:
                return f"{path.name} could not be read ({exc.strerror or exc})."
            blob = io.BytesIO(built[0])
            with zipfile.ZipFile(blob, "a", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(exact[0], exact[1])
            info = dict(built[1])
            info["exact"] = exact
            return blob.getvalue(), info
        try:
            damaged = (DAMAGED_ENTRY + path.name, path.read_bytes())
        except OSError as exc:
            return f"{path.name} could not be read ({exc.strerror or exc})."
    # No module file (a stick never set up here), or a damaged one kept
    # as it is: the bindings only in the pack's own map.
    wires = (
        device_pack.collect_wires(guid, modes, profile) if profile is not None else {}
    )
    label = device_pack.pack_label(name, guid, None)
    doc: dict = {"device": name, "pack": label}
    if damaged is not None:
        doc["damaged"] = {"file": path.name, "reason": store.damage_of(path)}
    plan = {
        "device": name,
        "map": doc,
        "wires": {
            "modes": wires["modes"],
            "actions": wires["actions"],
            "tree": wires["tree"],
        }
        if wires and wires.get("modes")
        else None,
        "outputs": [],
        "files": [],
        "photoPath": "",
    }
    data, info = device_pack.build_pack(plan)
    if damaged is not None:
        blob = io.BytesIO(data)
        with zipfile.ZipFile(blob, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(damaged[0], damaged[1])
        data = blob.getvalue()
        info["damaged"] = damaged
    return data, info


def _read_pack(data: bytes | Path) -> dict | str:
    """The pack's map.json and wires.json, or why it can't be read."""
    try:
        source = io.BytesIO(data) if isinstance(data, bytes) else Path(data)
        with zipfile.ZipFile(source, "r") as zf:
            names = zf.namelist()
            if "map.json" not in names:
                return "It has no map.json."
            doc = json.loads(zf.read("map.json").decode("utf-8"))
            wires = {}
            if "wires.json" in names:
                wires = json.loads(zf.read("wires.json").decode("utf-8"))
            if zf.testzip() is not None:
                return "It is damaged."
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        return f"It could not be read ({exc})."
    if not isinstance(doc, dict):
        return "Its map.json is not a document."
    return {"map": doc, "wires": wires if isinstance(wires, dict) else {}}


def _contents(pack: dict) -> tuple[list[str], list[str], int, dict[str, int]]:
    """What a pack holds: parts, modes, inputs with bindings, inputs per vJoy."""
    doc = pack["map"]
    held = set()
    if doc.get("claim"):
        held.add("setup")
    if doc.get("nodes") or doc.get("image"):
        held.add("button_map")
    if doc.get("view") or doc.get("catalog"):
        held.add("appearance")
    if doc.get("calibration"):
        held.add("calibration")
    if isinstance(doc.get("damaged"), dict):
        held.add(DAMAGED_PART)
    modes: list[str] = []
    actions = 0
    vjoys: dict[str, int] = {}
    for mode in pack["wires"].get("modes") or []:
        if not isinstance(mode, dict):
            continue
        modes.append(str(mode.get("name") or "Default"))
        for line in mode.get("lines") or []:
            actions += 1
            text = str(line)
            if "→" not in text:
                continue
            for label in text.split("→", 1)[1].split(" + "):
                words = label.split()
                if (
                    len(words) >= 2
                    and words[0].lower() == "vjoy"
                    and words[1].isdigit()
                ):
                    vjoys[words[1]] = vjoys.get(words[1], 0) + 1
    if modes:
        held.add("bindings")
    return [p for p in HOLDS if p in held], modes, actions, vjoys


def _unique_pack(device_name: str, setup_name: str) -> Path:
    base = folder() / _file_name(device_name)
    stamp = _now().strftime("%Y-%m-%d %H%M%S")
    stem = f"{_file_name(setup_name)} {stamp}"
    dest = base / f"{stem}.zip"
    number = 2
    while dest.exists():
        dest = base / f"{stem} {number}.zip"
        number += 1
    return dest


def _same_entry(dest: Path, entry: tuple[str, bytes] | None) -> bool:
    """The written pack holds entry's bytes exactly (None: nothing to check)."""
    if entry is None:
        return True
    try:
        with zipfile.ZipFile(dest, "r") as zf:
            return zf.read(entry[0]) == entry[1]
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def _write_pack(dest: Path, data: bytes, entry: tuple[str, bytes] | None = None) -> str:
    """Writes the pack and reads it back (and entry's bytes, when given);
    "" or why it failed (S20)."""
    _note_file(dest)
    try:
        module_file.write_bytes(dest, data)
    except OSError as exc:
        return f"{dest.name} could not be written ({exc.strerror or exc})."
    if isinstance(_read_pack(dest), str) or not _same_entry(dest, entry):
        try:
            dest.unlink()
        except OSError:
            pass
        return f"{dest.name} was written but could not be read back."
    return ""


def _remove_files(paths: list[Path]) -> None:
    for path in paths:
        _note_file(path)
        try:
            path.unlink()
        except OSError:
            pass


def _keep(
    device_name: str,
    guid: str,
    profiles: list[Path],
    *,
    origin: str,
    own: bool,
    reason: str,
    parts: list[str] | None,
    name: str = "",
    mark_deleted: bool = False,
    keep_damaged: bool = False,
) -> dict:
    """Builds, writes and reads back one saved setup per profile (module
    only when profiles is empty) and lists them; nothing is kept when one
    fails (S20)."""
    device_name = own_name(device_name, guid)
    if not device_name:
        return _result(False, "Choose a device.")
    wanted = [p for p in PARTS if p in (parts if parts is not None else PARTS)]
    entry_title = (
        f"Autosave: {reason}"
        if origin == "autosave"
        else f"Saved {shown(device_name, guid) or device_name} to the Device Library"
    )
    # One History entry: the new packs, the list and any autosave pruned.
    with _LOCK, _action(entry_title):
        try:
            doc = _load()
        except LibraryDamaged as exc:
            return _result(False, f"The Device Library list can't be read: {exc}")
        sources: list[tuple[Path | None, Profile | None]] = []
        warnings: list[str] = []
        for path in profiles:
            loaded = _profile_for(Path(path))
            if isinstance(loaded, str):
                return _result(False, loaded)
            sources.append((Path(path), loaded))
        if not sources:
            sources.append((None, None))
        written: list[Path] = []
        made: list[dict] = []
        for path, profile in sources:
            built = _build(device_name, guid, profile, keep_damaged)
            if isinstance(built, str):
                _remove_files(written)
                return _result(False, built)
            data, info = built
            pack = _bg("read Device Pack", _read_pack, data)
            if isinstance(pack, str):
                _remove_files(written)
                return _result(False, pack)
            held, modes, actions, vjoys = _contents(pack)
            holds = [
                p
                for p in held
                if p in wanted or (p == DAMAGED_PART and "setup" in wanted)
            ]
            profile_name = (
                path.stem if path is not None and str(path) not in ("", ".") else ""
            )
            if path is not None and not profile_name:
                profile_name = "Open profile"
            title = (
                name
                or (reason if origin == "autosave" else "")
                or profile_name
                or device_name
            )
            dest = _unique_pack(device_name, title)
            entry = info.get("damaged") or info.get("exact")
            failed = _bg("write Device Pack", _write_pack, dest, data, entry)
            if failed:
                _remove_files(written)
                return _result(False, failed)
            written.append(dest)
            created = _iso()
            made.append(
                {
                    "key": _new_key("set"),
                    "name": title,
                    "description": "",
                    "created": created,
                    "origin": origin,
                    "own": bool(own),
                    "reason": "" if own else reason,
                    "holds": holds,
                    "profiles": [
                        {
                            "name": profile_name,
                            "path": str(path),
                            "modes": modes,
                            "actions": actions,
                        }
                    ]
                    if path is not None
                    else [],
                    "vjoys": vjoys,
                    "file": dest.relative_to(folder()).as_posix(),
                    "history": [{"at": created, "text": reason or "Saved"}],
                }
            )
            if origin == "autosave":
                # What it was asked to keep: a part it doesn't hold is one
                # the stick didn't have, so Undo removes it (S25, S41).
                # moduleFile: the module file kept exactly, "damaged", or
                # "" (the stick had none).
                made[-1]["covers"] = list(wanted)
                made[-1]["moduleFile"] = (
                    "damaged"
                    if info.get("damaged")
                    else (Path(entry[0]).name if entry else "")
                )
        rec = _record(doc, device_name, guid)
        rec.setdefault("ownName", device_name)
        if mark_deleted:
            rec["kind"] = "deleted"
            rec["name"] = _alias(rec.get("guid", ""), rec.get("name") or device_name)
        rec["seen"] = _iso()
        rec.setdefault("setups", []).extend(made)
        try:
            _save(doc)
        except OSError as exc:
            _remove_files(written)
            return _result(
                False, f"The Device Library list could not be written ({exc})."
            )
        saved = _read()
        found = [_find_setup(saved, s["key"]) for s in made]
        if not all(found):
            return _result(False, "The Device Library list could not be read back.")
        rows = [_setup_out(r, s) for r, s in found if r]  # type: ignore[misc]
        # The limit only now, after the new ones are written and read back;
        # it never removes them or Undo's way back (S19, S41).
        try:
            with _editing() as again:
                removed = _apply_limits(again, {s["key"] for s in made})
        except (LibraryDamaged, OSError) as exc:
            removed = []
            warnings.append(f"Old autosaves were not removed ({exc}).")
        _remove_files(removed)
        return _result(
            True,
            "",
            warnings=warnings,
            setups=rows,
            setup=rows[0] if rows else None,
            keys=[s["key"] for s in rows],
            device=rec["key"],
        )


def _newest_first(setups: list[dict]) -> list[dict]:
    """Newest first; kept in the same second: the later one first."""
    order = sorted(
        enumerate(setups), key=lambda pair: (str(pair[1].get("created", "")), pair[0])
    )
    return [setup for _index, setup in reversed(order)]


def _apply_limits(doc: dict, keep_keys: set[str] | None = None) -> list[Path]:
    """Keeps the newest N autosaves per stick (S19); the user's own saved
    setups and pack setups stay, and so do keep_keys (the autosaves just
    kept) and the last change's autosaves (Undo's way back, S41). The
    removed setups' pack files."""
    try:
        keep = max(1, int((doc.get("settings") or {}).get("keep", DEFAULT_KEEP)))
    except (TypeError, ValueError):
        keep = DEFAULT_KEEP
    kept = set(keep_keys or ())
    last = doc.get("lastChange")
    if isinstance(last, dict):
        kept.update(str(k) for k in last.get("autosaves") or [])
    gone: list[Path] = []
    for rec in doc.get("devices") or []:
        setups = rec.get("setups") or []
        autos = [
            s for s in setups if s.get("origin") == "autosave" and not s.get("own")
        ]
        autos = _newest_first(autos)
        drop = {id(s) for s in autos[keep:] if s.get("key") not in kept}
        if not drop:
            continue
        for setup in setups:
            if id(setup) in drop:
                gone.append(folder() / setup.get("file", ""))
        rec["setups"] = [s for s in setups if id(s) not in drop]
    return gone


def save_setup(
    device_name: str,
    guid: str,
    profiles: list[Path],
    *,
    own: bool = True,
    reason: str = "",
    parts: list[str] | None = None,
) -> dict:
    """S12: a saved setup of the device: its module file now and its
    bindings from each profile given (one saved setup per profile, named
    after it). profiles=[]: the module file only. {"setups": [SavedSetup]}"""
    return _keep(
        device_name,
        guid,
        list(profiles or []),
        origin="user" if own else "autosave",
        own=own,
        reason=reason,
        parts=parts,
    )


def autosave(
    device_name: str, guid: str, trigger: str, reason: str, profiles: list[Path]
) -> dict:
    """S16-S20: an autosave of the stick, named after why it was kept, one
    per profile the action changes. Written and read back, then the limit
    applied. ok False: the caller must not go on (S20)."""
    if trigger not in TRIGGERS:
        return _result(False, f"Unknown autosave trigger {trigger!r}.")
    parts = ["setup"] if trigger == "module_file" else None
    reason = _clean(reason) or "Autosave"
    out = _keep(
        device_name,
        guid,
        [] if trigger == "module_file" else list(profiles or []),
        origin="autosave",
        own=False,
        reason=reason,
        parts=parts,
        mark_deleted=trigger in ("deleted", "module_file"),
        keep_damaged=True,
    )
    if not out["ok"]:
        out["error"] = f"The autosave could not be kept: {out['error']}"
    return out


# --- a device now (S8, S11, S22) -----------------------------------------------------


def note_seen(guids: list[str]) -> None:
    """S8: the sticks plugged in now (and the ones just unplugged) were
    seen now. Kept by device id; no device is added to the list for it."""
    keys = sorted({stored_guid_key(g) for g in guids or [] if stored_guid_key(g)})
    if not keys:
        return
    try:
        with _editing(quiet=True) as doc:
            kept = doc.get("seen")
            seen: dict = kept if isinstance(kept, dict) else {}
            now = _iso()
            for key in keys:
                seen[key] = now
            doc["seen"] = seen
    except (LibraryDamaged, OSError) as exc:
        syslog.warning(f"Device Library: when sticks were seen not kept ({exc})")


def _counts(buttons: object, axes: object, hats: object, source: str) -> dict:
    def size(value: object) -> int:
        try:
            return len(value)  # type: ignore[arg-type]
        except TypeError:
            return 0

    return {
        "buttons": size(buttons),
        "axes": size(axes),
        "hats": size(hats),
        "from": source,
    }


def inputs(key: str) -> dict:
    """S8: what inputs a device has: {"buttons", "axes", "hats", "from"}.
    From the device list when it is plugged in, else from its module file
    (what is set up), else from its newest saved setup; {} when unknown."""
    from gremlin.modules import store

    row = device(key)
    if row is None:
        return {}
    if row.get("state") == "connected" and row.get("guid"):
        try:
            live = store.connected_input_ids(row["guid"])
        except Exception:  # noqa: BLE001 - no device list: try the file
            live = None
        if live is not None:
            return _counts(*live, "device")
    if row.get("module"):
        doc = store.read_path(store.path_of(row["module"]))
        claim = doc.get("claim") if isinstance(doc.get("claim"), dict) else None
        if claim is not None:
            return _counts(
                claim.get("buttons") or [],
                claim.get("axes") or [],
                claim.get("hats") or [],
                "module file",
            )
    for setup in row.get("setups") or []:
        pack = _read_pack(Path(setup.get("pack", "")))
        if isinstance(pack, str):
            continue
        claim = pack["map"].get("claim")
        if isinstance(claim, dict):
            return _counts(
                claim.get("buttons") or [],
                claim.get("axes") or [],
                claim.get("hats") or [],
                "saved setup",
            )
    return {}


def _photo_cache() -> Path:
    """Where saved setups' photos are taken out to be shown (not in the
    Library, so its size and Tidy never count them)."""
    import tempfile

    return Path(tempfile.gettempdir()) / "Gremlin Platforms" / "device library photos"


def photo(setup_key: str) -> str:
    """S11: the saved setup's Button Map photo as a file to show, taken out
    of its pack once; "" when it has none (or it can't be read)."""
    try:
        pack = pack_path(setup_key)
        stamp = pack.stat()
    except (KeyError, OSError):
        return ""
    try:
        with zipfile.ZipFile(pack, "r") as zf:
            doc = json.loads(zf.read("map.json").decode("utf-8"))
            arc = str(doc.get("image") or "") if isinstance(doc, dict) else ""
            if not arc or arc not in zf.namelist():
                return ""
            tag = hashlib.sha1(
                f"{pack}|{stamp.st_size}|{stamp.st_mtime_ns}|{arc}".encode("utf-8")
            ).hexdigest()[:16]
            dest = _photo_cache() / f"{tag}{Path(arc).suffix.lower()}"
            if not dest.is_file():
                module_file.write_bytes(dest, zf.read(arc))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        syslog.warning(f"Device Library: photo of {setup_key} not shown ({exc})")
        return ""
    return str(dest)


def _own_name(row: dict) -> str:
    """The device's own name (the module file's, or the plugged-in
    stick's), which finds its module file; the Library shows the Home
    card's name (S7)."""
    if row.get("module"):
        for name, _guid, slug in _set_up():
            if slug == row["module"]:
                return name
    want = stored_guid_key(row.get("guid", ""))
    if want:
        for name, guid in _connected():
            if stored_guid_key(guid) == want:
                return name
    return str(row.get("name") or "")


def current_pack(key: str, profile: Profile | None = None) -> dict:
    """S22: a device's current settings as a pack in memory, kept nowhere:
    its module file and pictures, and (profile given) its bindings in every
    mode of that profile. {"data": bytes, "holds", "modes", "name", "guid"}.
    A damaged module file goes in as it is (holds DAMAGED_PART, S20a), so
    only its bindings can be copied."""
    row = device(key)
    if row is None:
        return _result(False, "That device is no longer in the Device Library.")
    if not row.get("module") and row.get("state") != "connected":
        return _result(
            False,
            f"{row.get('name', '')} has no settings here now: copy one of its "
            "saved setups instead.",
        )
    built = _build(_own_name(row), str(row.get("guid") or ""), profile, True)
    if isinstance(built, str):
        return _result(False, built)
    data, _info = built
    pack = _read_pack(data)
    if isinstance(pack, str):
        return _result(False, pack)
    held, modes, _actions, vjoys = _contents(pack)
    return _result(
        True,
        "",
        data=data,
        holds=held,
        modes=modes,
        vjoys=vjoys,
        name=str(row.get("name") or ""),
        guid=str(row.get("guid") or ""),
        device=row["key"],
    )


# --- undo (S41) ----------------------------------------------------------------------


def set_last_change(
    op: str,
    autosave_keys: list[str],
    label: str,
    detail: dict | None = None,
    *,
    undone: bool = False,
) -> None:
    """S41: what Undo puts back. label describes the change ("Copy DCS F-16
    to Right stick"); the window shows "Undo " + label, or "Redo " + label
    while undone (right after an Undo, D-10-REDO-LABEL). detail (JSON) is what
    Undo needs beyond the autosaves (a swap: the sticks, parts, profiles and
    controls, to swap back)."""
    with _editing(quiet=True) as doc:
        doc["lastChange"] = {
            "op": str(op),
            "autosaves": [str(k) for k in autosave_keys],
            "label": str(label),
            "at": _iso(),
            "undone": bool(undone),
        }
        if detail:
            doc["lastChange"]["detail"] = json.loads(json.dumps(detail))


def last_change() -> dict | None:
    value = _read().get("lastChange")
    return dict(value) if isinstance(value, dict) else None


# --- names, descriptions, history (S7, S11, S13) -------------------------------------


def _history(setup: dict, text: str) -> None:
    setup.setdefault("history", []).append({"at": _iso(), "text": text})


def rename(key: str, name: str) -> dict:
    """A device or saved setup. A device set up here or plugged in has one
    name with its Home card (S7); renaming an autosave makes it the user's
    own (S13)."""
    name = _clean(name)
    if not name:
        return _result(False, "Type a name.")
    with _LOCK:
        try:
            with _editing() as doc:
                found = _find_setup(doc, key)
                if found:
                    _rec, setup = found
                    _name_action(
                        f"Renamed saved setup {_clean(setup.get('name', ''))} to {name}"
                    )
                    setup["name"] = name
                    setup["own"] = True
                    _history(setup, f"Renamed to {name}")
                    return _result()
                row = next((r for r in _view(doc) if r["key"] == key), None)
                if row is None:
                    raise KeyError(key)
                if row["state"] == "connected" or row["module"]:
                    if row["guid"]:
                        _set_alias(row["guid"], name)
                _name_action(f"Renamed {row['name']} to {name} in the Device Library")
                rec = _record(doc, row["name"], row["guid"])
                rec["name"] = name
        except KeyError:
            return _result(False, "That is no longer in the Device Library.")
        except LibraryDamaged as exc:
            return _result(False, str(exc))
    return _result()


def describe(key: str, text: str) -> dict:
    text = str(text or "").strip()
    with _LOCK:
        try:
            with _editing() as doc:
                found = _find_setup(doc, key)
                if found:
                    _rec, setup = found
                    _name_action(
                        "Edited the description of saved setup "
                        f"{_clean(setup.get('name', ''))}"
                    )
                    setup["description"] = text
                    setup["own"] = True
                    _history(setup, "Description edited")
                    return _result()
                row = next((r for r in _view(doc) if r["key"] == key), None)
                if row is None:
                    raise KeyError(key)
                _name_action(f"Edited the description of {row['name']}")
                rec = _record(doc, row["name"], row["guid"])
                rec["description"] = text
        except KeyError:
            return _result(False, "That is no longer in the Device Library.")
        except LibraryDamaged as exc:
            return _result(False, str(exc))
    return _result()


def add_history(setup_key: str, text: str) -> None:
    with _editing(quiet=True) as doc:
        found = _find_setup(doc, setup_key)
        if found:
            _history(found[1], str(text))


def module_bytes(setup_key: str) -> bytes | None:
    """The module file an autosave kept exactly (S41); None when it kept
    none that way (an older autosave, or a damaged file). KeyError when the
    saved setup is gone."""
    found = _find_setup(_read(), setup_key)
    if not found:
        raise KeyError(setup_key)
    entry = str(found[1].get("moduleFile") or "")
    if not entry or entry == "damaged":
        return None
    try:
        with zipfile.ZipFile(folder() / found[1].get("file", ""), "r") as zf:
            return zf.read(EXACT_ENTRY + entry)
    except (OSError, KeyError, zipfile.BadZipFile):
        return None


def pack_path(setup_key: str) -> Path:
    found = _find_setup(_read(), setup_key)
    if not found:
        raise KeyError(setup_key)
    return folder() / found[1].get("file", "")


# --- delete (S15) and tidy (S38) ------------------------------------------------------


def delete(key: str) -> dict:
    """A saved setup, or a device with all its saved setups. A connected
    device is refused (S15: Clear Setup… or Delete Saved Setups…); a
    set-up device that isn't plugged in stays (Remove from Library runs
    Delete Device first); only its saved setups go."""
    return _delete(key)


def _plugged_in(name: str) -> str:
    return f"{name} is plugged in: use Clear Setup… or Delete Saved Setups… instead."


def _delete(key: str, setups_only: bool = False) -> dict:
    """delete(); setups_only: a device keeps its record, plugged in or not
    (Delete Saved Setups…, S15)."""
    with _LOCK, _action():
        try:
            doc = _load()
        except LibraryDamaged as exc:
            return _result(False, str(exc))
        files: list[Path] = []
        notes: list[str] = []
        found = _find_setup(doc, key)
        if found:
            rec, setup = found
            rec["setups"] = [s for s in rec["setups"] if s is not setup]
            files.append(folder() / setup.get("file", ""))
            _name_action(f"Deleted saved setup {_clean(setup.get('name', ''))}")
        else:
            row = next((r for r in _view(doc) if r["key"] == key), None)
            if row is None:
                return _result(False, "That is no longer in the Device Library.")
            if row["builtIn"]:
                return _result(
                    False,
                    built_in_refusal(
                        row["name"],
                        "Delete Saved Setups" if setups_only else "Remove from Library",
                    ),
                )
            if row["state"] == "connected" and not setups_only:
                return _result(False, _plugged_in(row["name"]))
            label = shown(row["name"], row["guid"]) or row["name"]
            _name_action(
                f"Deleted the saved setups of {label}"
                if setups_only or row["module"]
                else f"Removed {label} from the Device Library"
            )
            rec = _find_record(doc, key)
            if rec is not None:
                files.extend(
                    folder() / s.get("file", "") for s in rec.get("setups") or []
                )
                if setups_only:
                    rec["setups"] = []
                elif row["module"]:
                    rec["setups"] = []
                    notes.append(
                        f"{row['name']} stays: it is set up here "
                        "(Delete Device removes it). Its saved setups were removed."
                    )
                else:
                    doc["devices"] = [r for r in doc["devices"] if r is not rec]
        try:
            _save(doc)
        except OSError as exc:
            return _result(
                False, f"The Device Library list could not be written ({exc})."
            )
        _remove_files(files)
        # Only the folders of the packs removed, when left empty.
        base = folder()
        _drop_empty_folders(
            {
                f.relative_to(base).parts[0]
                for f in files
                if f.parent != base and f != base
            }
        )
        return _result(True, "", notes=notes)


# --- the context menus (S15, S44, S49, S50) -------------------------------------------


def removal_plan(key: str) -> dict:
    """What Remove from Library… would remove (S15, S47), for the question
    and for the caller to run Delete Device first when the device still has
    a module file here: {"name", "shown", "setups", "module_file",
    "connected"}."""
    row = device(key)
    if row is None:
        return _result(False, "That device is no longer in the Device Library.")
    if row.get("builtIn"):
        return _result(
            False, built_in_refusal(str(row.get("name") or ""), "Remove from Library")
        )
    return _result(
        True,
        "",
        name=str(row.get("name") or ""),
        shown=shown(str(row.get("name") or ""), str(row.get("guid") or "")),
        setups=len(row.get("setups") or []),
        module_file=bool(row.get("module")),
        connected=row.get("state") == "connected",
    )


def remove_device(key: str) -> dict:
    """Remove from Library… (S15, D-10-REMOVE): a device that isn't plugged
    in, with all its saved setups (the "stick deleted" autosave too).
    Refused while it is plugged in, and while it still has a module file
    here (module_file True: the caller runs Delete Device first)."""
    plan = removal_plan(key)
    if not plan["ok"]:
        return plan
    if plan["connected"]:
        return _result(False, _plugged_in(plan["shown"]))
    if plan["module_file"]:
        return _result(
            False,
            f"{plan['shown']} still has a module file here: Delete Device "
            "removes it first.",
            module_file=True,
        )
    return _delete(key)


def delete_saved_setups(key: str) -> dict:
    """Delete Saved Setups… (S15): every saved setup of a device plugged in
    (or set up here) goes; the device and its settings stay."""
    row = device(key)
    if row is None:
        return _result(False, "That device is no longer in the Device Library.")
    if row.get("builtIn"):
        return _result(
            False, built_in_refusal(str(row.get("name") or ""), "Delete Saved Setups")
        )
    if row.get("state") != "connected" and not row.get("module"):
        return _result(
            False,
            f"{row.get('name', '')} isn't plugged in: use Remove from Library… "
            "instead.",
        )
    return _delete(key, setups_only=True)


def keep(setup_key: str) -> dict:
    """Keep This Autosave (S49): the autosave becomes the user's own, as
    renaming or describing it does (S13), so the limit never removes it."""
    with _LOCK:
        try:
            with _editing() as doc:
                found = _find_setup(doc, setup_key)
                if not found:
                    raise KeyError(setup_key)
                _rec, setup = found
                if setup.get("origin") != "autosave":
                    return _result(False, "Only an autosave can be kept this way.")
                if not setup.get("own"):
                    _name_action(
                        f"Kept autosave {_clean(setup.get('name', ''))} as your own"
                    )
                    setup["own"] = True
                    _history(setup, "Kept as your own")
        except KeyError:
            return _result(False, "That is no longer in the Device Library.")
        except LibraryDamaged as exc:
            return _result(False, str(exc))
    return _result()


def delete_many(keys: list[str]) -> dict:
    """Delete… / Remove from Library… on several rows (S50): each by the
    rules of delete (a saved setup) or remove_device (a device); saved
    setups first. ok when anything went; "removed" lists the keys that
    went, "refused" [{"key", "error"}] the others (also in warnings)."""
    wanted = list(dict.fromkeys(str(k) for k in keys or []))
    doc = _read()
    setups = [k for k in wanted if _find_setup(doc, k)]
    removed: list[str] = []
    refused: list[dict] = []
    # One History entry for the lot (each removal names itself in it).
    with _action():
        for key in setups + [k for k in wanted if k not in setups]:
            out = delete(key) if key in setups else remove_device(key)
            if out["ok"]:
                removed.append(key)
            else:
                refused.append({"key": key, "error": str(out["error"])})
    warnings = [r["error"] for r in refused]
    if not removed:
        return _result(
            False,
            " ".join(warnings) or "Nothing was chosen.",
            removed=removed,
            refused=refused,
        )
    return _result(True, "", warnings=warnings, removed=removed, refused=refused)


def export_current(device_key: str, dest: Path) -> dict:
    """Export Current Setup… (S44): a Device Pack of the device's current
    settings (its module file, and its bindings in the open profile),
    written where the user picked as Export Saved Setup… is (S14, 08 S57).
    No saved setup is kept. Reads the open profile: call on the main
    thread."""
    from gremlin.modules import store
    from gremlin.ui import device_pack

    dest = Path(dest)
    if dest.suffix.lower() != ".zip":
        dest = dest.with_name(dest.name + ".zip")
    if store.is_inside(dest):
        return _result(False, "A Device Pack can't be saved inside the modules folder.")
    built = current_pack(device_key, _open_profile())
    if not built["ok"]:
        return built
    data = built["data"]
    info = {"device": built["name"], "sizeText": device_pack.size_text(len(data))}
    out = _bg("export Device Pack", device_pack.save_pack, data, info, dest)
    base = _result(bool(out.get("ok")), str(out.get("error") or ""))
    base.update({k: v for k, v in out.items() if k not in ("ok", "error")})
    return base


def _own_dirs(doc: dict) -> set[str]:
    """The device folders the Library made (its packs' folders), lower
    case: a library folder may hold other things (Move… into Documents,
    S36)."""
    found: set[str] = set()
    for rec in doc.get("devices") or []:
        if not isinstance(rec, dict):
            continue
        found.add(_file_name(rec.get("name", "")).lower())
        for setup in rec.get("setups") or []:
            parts = Path(str(setup.get("file") or "")).parts
            if len(parts) > 1:
                found.add(parts[0].lower())
    found.discard("")
    return found


def _list_of(base: Path) -> dict:
    try:
        doc = json.loads((base / LIST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _own_files(base: Path, doc: dict | None = None) -> list[Path]:
    """The Library's own files in base: library.json and the files in its
    device folders (S4: the size counts only these)."""
    if not base.is_dir():
        return []
    mine = _own_dirs(_list_of(base) if doc is None else doc)
    out = [base / LIST_NAME] if (base / LIST_NAME).is_file() else []
    for child in base.iterdir():
        if child.is_dir() and child.name.lower() in mine:
            out.extend(p for p in child.rglob("*") if p.is_file())
    return out


def _drop_empty_folders(gone: set[str] | None = None) -> None:
    """Removes the Library's own device folders left empty (gone: folders
    of the devices just removed from the list); never another folder."""
    base = folder()
    if not base.is_dir():
        return
    mine = _own_dirs(_list_of(base)) | {g.lower() for g in gone or set()}
    for child in base.iterdir():
        if child.is_dir() and child.name.lower() in mine:
            try:
                child.rmdir()
            except OSError:
                pass


def _file_bytes(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def tidy_preview(months: int) -> list[dict]:
    """S38: what Tidy would remove: autosaves older than months, and deleted
    devices with no saved setups. [{"key", "label", "bytes"}]"""
    cutoff = _now() - timedelta(days=30.44 * max(0, int(months)))
    rows = []
    for row in devices():
        for setup in row["setups"]:
            if setup["origin"] != "autosave" or setup["own"]:
                continue
            made = _parse_iso(setup["created"])
            if made is not None and made < cutoff:
                rows.append(
                    {
                        "key": setup["key"],
                        "label": f"{row['name']} › {setup['name']} "
                        f"({setup['created'][:10]})",
                        "bytes": _file_bytes(Path(setup["pack"])),
                    }
                )
        if row["state"] == "deleted" and not row["setups"]:
            rows.append(
                {"key": row["key"], "label": f"{row['name']} (deleted)", "bytes": 0}
            )
    return rows


def tidy(keys: list[str]) -> dict:
    """Removes what tidy_preview listed and the user confirmed: autosaves
    and deleted devices without saved setups only."""
    wanted = set(keys or [])
    by_key = {}
    for row in devices():
        by_key[row["key"]] = ("device", row)
        for setup in row["setups"]:
            by_key[setup["key"]] = ("setup", setup)
    warnings = []
    removed = 0
    with _action("Tidied the Device Library"):
        removed, warnings = _tidy(wanted, by_key)
    return _result(True, "", warnings=warnings, removed=removed)


def _tidy(wanted: set[str], by_key: dict) -> tuple[int, list[str]]:
    warnings: list[str] = []
    removed = 0
    for key in wanted:
        kind, item = by_key.get(key, ("", None))
        allowed = (
            kind == "setup" and item["origin"] == "autosave" and not item["own"]
        ) or (kind == "device" and item["state"] == "deleted" and not item["setups"])
        if not allowed:
            warnings.append(
                f"{key} was left: Tidy removes only old autosaves and "
                "empty deleted devices."
            )
            continue
        out = delete(key)
        if out["ok"]:
            removed += 1
        else:
            warnings.append(out["error"])
    return removed, warnings


def size_bytes() -> int:
    """S4: the library folder's size on disk (files only; no Qt)."""
    return sum(_file_bytes(path) for path in _own_files(folder()))


# --- search (S5) ---------------------------------------------------------------


def search(text: str) -> list[str]:
    """S5: the keys of devices and saved setups that match (a saved setup's
    device is listed too, so it can be shown under it)."""
    want = _collapsed(text)
    if not want:
        return []
    hits: list[str] = []
    for row in devices():
        device_hit = want in _collapsed(f"{row['name']} {row['description']}")
        setup_hits = []
        for setup in row["setups"]:
            words = [setup["name"], setup["description"], setup["reason"]]
            words += [PART_LABELS[p] for p in setup["holds"]]
            for profile in setup["profiles"]:
                words.append(profile.get("name", ""))
                words += list(profile.get("modes") or [])
            words += [f"vJoy {number}" for number in setup["vjoys"]]
            if want in _collapsed(" | ".join(words)):
                setup_hits.append(setup["key"])
        if device_hit or setup_hits:
            hits.append(row["key"])
            hits.extend(setup_hits)
    return hits


# --- sharing (S14, S35, S39) ----------------------------------------------------


def import_pack(path: Path) -> dict:
    """S35, S39: the pack becomes a saved setup under the device it was made
    from when that device is in the Library, otherwise under a new Not
    connected device named after the pack. {"setup": SavedSetup}"""
    from gremlin.ui import device_pack

    path = Path(path)
    if path.suffix.lower() != ".zip":
        return _result(False, f"{path.name} is not a Device Pack (.zip).")
    try:
        data = _bg("read Device Pack", path.read_bytes)
    except OSError as exc:
        return _result(False, f"{path.name} could not be read ({exc.strerror or exc}).")
    pack = _bg("read Device Pack", _read_pack, data)
    if isinstance(pack, str):
        return _result(False, f"{path.name} is not a Device Pack it can read. {pack}")
    newer = device_pack.too_new(pack["map"])
    if newer:
        return _result(False, newer)
    label = pack["map"].get("pack") if isinstance(pack["map"].get("pack"), dict) else {}
    made_from = (
        _clean(label.get("exportedName") or pack["map"].get("device") or "")
        or path.stem
    )
    guid = str(label.get("exportedGuid") or "")
    author = _clean(label.get("author") or "")
    note = str(label.get("note") or "").strip()
    held, modes, actions, vjoys = _contents(pack)
    with _LOCK, _action(f"Imported {path.name} into the Device Library"):
        try:
            doc = _load()
        except LibraryDamaged as exc:
            return _result(False, str(exc))
        # The device it was made from: by its id; by its name only when the
        # pack has no id, so a twin's pack never lands under the other twin
        # (S35).
        row = None
        want = stored_guid_key(guid)
        for each in _view(doc):
            if (want and stored_guid_key(each["guid"]) == want) or (
                not want and _collapsed(each["name"]) == _collapsed(made_from)
            ):
                row = each
                break
        if row is not None:
            rec = _record(doc, row["name"], row["guid"])
        else:
            rec = _pack_record(doc, made_from)
        device_name = rec.get("name") or made_from
        dest = _unique_pack(device_name, path.stem)
        failed = _bg("write Device Pack", _write_pack, dest, data)
        if failed:
            return _result(False, failed)
        created = _iso()
        reason = f"From {author}'s pack" if author else "From a Device Pack"
        setup = {
            "key": _new_key("set"),
            "name": path.stem,
            "description": note,
            "created": created,
            "origin": "pack",
            "own": False,
            "reason": reason,
            "holds": held,
            "profiles": [{"name": "", "path": "", "modes": modes, "actions": actions}]
            if modes
            else [],
            "vjoys": vjoys,
            "file": dest.relative_to(folder()).as_posix(),
            "history": [{"at": created, "text": f"Imported from {path.name}"}],
        }
        rec.setdefault("setups", []).append(setup)
        try:
            _save(doc)
        except OSError as exc:
            _remove_files([dest])
            return _result(
                False, f"The Device Library list could not be written ({exc})."
            )
        return _result(True, "", setup=_setup_out(rec, setup), device=rec["key"])


def export_setup(key: str, dest: Path) -> dict:
    """S14: the saved setup's pack, written where the user picked (08 S57:
    not inside the modules folder; .zip added), then read back."""
    from gremlin.modules import store
    from gremlin.ui import device_pack

    dest = Path(dest)
    if dest.suffix.lower() != ".zip":
        dest = dest.with_name(dest.name + ".zip")
    if store.is_inside(dest):
        return _result(False, "A Device Pack can't be saved inside the modules folder.")
    try:
        source = pack_path(key)
        data = source.read_bytes()
    except KeyError:
        return _result(False, "That saved setup is no longer in the Device Library.")
    except OSError as exc:
        return _result(
            False, f"The saved setup's pack could not be read ({exc.strerror or exc})."
        )
    found = _find_setup(_read(), key)
    name = found[0].get("name", "") if found else ""
    info = {"device": name, "sizeText": device_pack.size_text(len(data))}
    out = _bg("export Device Pack", device_pack.save_pack, data, info, dest)
    if out.get("ok"):
        add_history(key, f"Exported to {dest.name}")
    base = _result(bool(out.get("ok")), str(out.get("error") or ""))
    base.update({k: v for k, v in out.items() if k not in ("ok", "error")})
    return base
