# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-1): the move to device folders (03 S134,
D-03-DEVICE-FOLDERS). Removed once it has run on the user's PC.

The old layout kept a device's module file at <modules>/<slug>.json, its
pictures in <modules>/<slug>/, an old photo at <modules>/<slug>_photo.<ext>,
its recovery copy at <modules>/recovery/<slug>.json and import backups in
<modules>/imported/; a setting (file bindings) chose which file a device
used. On the first start of this version each device's files are gathered
into its own folder (03 S128-S133):

1. backup: everything the move touches is copied to
   <data folder>/backup/<date> device folders move/ and checked (count and
   size); any failure stops with nothing moved;
2. plan: an id and a shown name for every root module file, twins that
   shared one file each get their own (S6), folder names by id key (S132);
3. move: module.json, pictures/, photo, recovery.json, imported/;
4. picture references rewritten to "pictures/<name>", pictures outside the
   folder copied in, a missing one kept as "pictures/<name>" (S108);
5. templates/<name>.json -> templates/<name>/template.json + pictures/;
6. leftovers (library/, photo stashes, old recovery/, empty picture folders)
   moved into the backup folder: nothing is deleted;
7. <modules>/folders.json written: the move never runs again.

Every step skips work already done: a run cut short resumes from its saved
plan (<modules>/folders-move.state). Plain file operations, no History
entries. Main thread, before the device scan (joystick_gremlin).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

from gremlin.modules import module_file, store
from gremlin.modules.ids import stored_guid_key
from gremlin.modules.registry import is_gremlin_xbox_name, plain_slug

syslog = logging.getLogger("system")

# ONE-TIME (tracker OT-1): the marker, the resume file and the old setting.
MARKER = "folders.json"
STATE = "folders-move.state"
LAYOUT = 2
BINDINGS = ("global", "internal", "module-file-bindings")
BINDINGS_FILE = "module-file-bindings.json"
STAGING = ("cache", "folders-move")


class MoveError(Exception):
    """ONE-TIME (tracker OT-1): the move stopped; the reason is the text."""


# --- the old file-bindings setting ----------------------------------------------


def register_setting() -> None:
    """ONE-TIME (tracker OT-1): registers the old file-bindings setting (every
    start until the move has run), so purge_unused keeps it for the move."""
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    Configuration().register(
        *BINDINGS,
        PropertyType.String,
        "{}",
        "Input module file chosen for each device (read once by the move to "
        "device folders).",
        {},
        False,
    )


def old_bindings() -> dict[str, str]:
    """ONE-TIME (tracker OT-1): the old file-bindings setting, {id key or
    name:<slug>: slug}; {} when unset or unreadable."""
    from gremlin.config import Configuration

    register_setting()
    try:
        data = json.loads(Configuration().value(*BINDINGS) or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


# --- when ---------------------------------------------------------------------


def is_done(modules: Path) -> bool:
    """ONE-TIME (tracker OT-1): the marker is there."""
    return (Path(modules) / MARKER).is_file()


def _root_module_files(modules: Path) -> list[Path]:
    """ONE-TIME (tracker OT-1): old-layout module files at the modules root."""
    if not modules.is_dir():
        return []
    return sorted(p for p in modules.glob("*.json") if p.is_file() and p.name != MARKER)


# ONE-TIME (tracker OT-1): the user's own Gremlin Platforms folder, read from
# the environment when this module loads (tests patch gremlin.util, and may
# change USERPROFILE later).
_REAL_DATA = [
    Path(base) / "Gremlin Platforms"
    for base in (
        os.environ.get("USERPROFILE", ""),
        os.environ.get("HOMEDRIVE", "") + os.environ.get("HOMEPATH", ""),
    )
    if base
]
REFUSED = "refused: tests"


def _inside(path: Path, parent: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
    except (ValueError, OSError):
        return False
    return True


def refuses_real_data(modules: Path, data: Path) -> bool:
    """ONE-TIME (tracker OT-1): True in a test run (GREMLIN_TESTS=1, or
    pytest loaded) when the data or modules folder is the user's real
    Gremlin Platforms folder: a test never moves the user's files."""
    testing = os.environ.get("GREMLIN_TESTS") == "1" or "pytest" in sys.modules
    if not testing:
        return False
    return any(_inside(each, real) for real in _REAL_DATA for each in (modules, data))


# --- run ----------------------------------------------------------------------


def run_if_needed(modules_dir: Path, data_dir: Path) -> str:
    """ONE-TIME (tracker OT-1): the start's entry point (joystick_gremlin):
    runs the move when it is needed; "" when done or nothing to do, else
    the error (logged; the marker is not written, so the next start
    retries). REFUSED in a test run on the real data folder."""
    if refuses_real_data(Path(modules_dir), Path(data_dir)):
        # Expected in a test run (temp home): a warning, not an error.
        syslog.warning(f"Device folders move {REFUSED} ({data_dir})")
        return REFUSED
    try:
        run(Path(modules_dir), Path(data_dir))
    except Exception as exc:  # noqa: BLE001 - any failure: logged, retried next start
        syslog.exception("Device folders move failed")
        return str(exc) or type(exc).__name__
    return ""


def run(modules: Path | None = None, data: Path | None = None) -> str:
    """ONE-TIME (tracker OT-1): moves the old layout into device folders once
    (03 S134). Returns a summary ("" when nothing was to do); raises
    MoveError (or OSError) on a failure, with the marker not written."""
    register_setting()
    if modules is None:
        modules = store.folder()
    if data is None:
        from gremlin.util import data_folder

        data = Path(data_folder())
    modules, data = Path(modules), Path(data)
    if refuses_real_data(modules, data):
        raise MoveError(REFUSED)
    if is_done(modules):
        return ""
    state_path = modules / STATE
    state = _read_json(state_path) if state_path.is_file() else None
    if state is None and not _root_module_files(modules):
        if modules.is_dir() or modules.parent.is_dir():
            _write_marker(modules, "")
        return ""
    if state is None:
        backup = _backup(modules, data)
        plan = _plan(modules)
        state = {"backup": str(backup), "plan": plan}
        _write_json(state_path, state)
    backup = Path(state["backup"])
    plan = list(state["plan"])
    _stage_pictures(modules, plan)
    for entry in _move_order(plan):
        _move_device(modules, backup, plan, entry)
    for entry in plan:
        _rewrite_refs(modules, plan, modules / entry["folder"])
    templates = _move_templates(modules, backup)
    _archive_leftovers(modules, backup, plan)
    _write_marker(modules, str(backup))
    _move_into(state_path, backup / "leftovers" / STATE)
    summary = (
        f"Device folders move: {len(plan)} device folder(s), {templates} "
        f"template(s); backup in {backup}"
    )
    syslog.info(summary)
    return summary


# --- 1. backup -------------------------------------------------------------------


def _backup_dir(data: Path) -> Path:
    """ONE-TIME (tracker OT-1): <data>/backup/<date> device folders move, with
    " (2)" and up when taken."""
    base = data / "backup" / f"{datetime.now():%Y-%m-%d} device folders move"
    path, number = base, 2
    while path.exists():
        path = base.with_name(f"{base.name} ({number})")
        number += 1
    return path


def _backup_items(modules: Path) -> list[Path]:
    """ONE-TIME (tracker OT-1): what the move touches: root *.json, every root
    folder but cache/ (only its photo stashes) and any already new-layout
    folder, old photo files."""
    items: list[Path] = []
    for path in sorted(modules.iterdir()):
        name = path.name
        if path.is_file():
            if name == MARKER or name == STATE:
                continue
            stem = path.stem.lower()
            if path.suffix.lower() == ".json" or "_photo" in stem:
                items.append(path)
        elif path.is_dir():
            if name.lower() == "cache":
                items += sorted(p for p in path.glob("photo-stash*") if p.is_dir())
            elif not (path / store.ID_FILE).is_file():
                items.append(path)
    return items


def _tree_size(path: Path) -> tuple[int, int]:
    if path.is_file():
        return 1, path.stat().st_size
    count = size = 0
    for each in path.rglob("*"):
        if each.is_file():
            count += 1
            size += each.stat().st_size
    return count, size


def _backup(modules: Path, data: Path) -> Path:
    """ONE-TIME (tracker OT-1): step 1. Copies and verifies; on any failure the
    half-made backup is removed and MoveError raised: nothing moved."""
    dest = _backup_dir(data)
    try:
        dest.mkdir(parents=True)
        items = _backup_items(modules)
        for item in items:
            target = dest / item.relative_to(modules)
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        (dest / BINDINGS_FILE).write_text(
            json.dumps(old_bindings(), indent=2) + "\n", encoding="utf-8"
        )
        for item in items:
            if _tree_size(item) != _tree_size(dest / item.relative_to(modules)):
                raise MoveError(f"The backup copy of {item} does not match it")
    except (OSError, shutil.Error, MoveError) as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise MoveError(
            f"The backup before the device folders move failed, nothing was "
            f"moved: {exc}"
        ) from exc
    return dest


# --- 2. plan ---------------------------------------------------------------------


def _builtin(slug: str) -> tuple[str, str] | None:
    """ONE-TIME (tracker OT-1): (id key, shown name) of a built-in device's
    old file by its slug."""
    from gremlin.modules import device_class

    if device_class.is_input_kind(slug):
        kind = slug
    elif is_gremlin_xbox_name(slug):
        kind = "xbox"
    else:
        return None
    return (
        stored_guid_key(str(device_class.guid_of_kind(kind))),
        device_class.display_name(kind),
    )


def _is_guid(key: str) -> bool:
    try:
        uuid.UUID(str(key))
    except ValueError:
        return False
    return True


def _shown(key: str, doc: dict | None, stem: str, twins: dict[str, str]) -> str:
    """ONE-TIME (tracker OT-1): alias(id), else twin name(id), else the file's
    device, boundName, else the file name."""
    doc = doc or {}
    fallback = str(doc.get("device") or doc.get("boundName") or stem).strip()
    if not _is_guid(key):
        return fallback or stem
    shown = twins.get(key, "") or fallback or stem
    try:
        from gremlin import device_aliases

        return device_aliases.display_name(key, shown)
    except Exception:  # noqa: BLE001 - no settings: no alias
        return shown


def _twins() -> dict[str, str]:
    try:
        from gremlin import device_initialization

        stored = device_initialization.stored_twins()
    except Exception:  # noqa: BLE001 - no settings yet
        return {}
    return {stored_guid_key(k): str(v) for k, v in stored.items()}


def _unique(base: str, taken: set[str]) -> str:
    """ONE-TIME (tracker OT-1): base, else "<base> (2)", (3)... (S132), the
    base cut so the name stays within 80 characters."""
    name, number = base, 2
    while name.casefold() in taken:
        suffix = f" ({number})"
        name = store.folder_name_for(base[: 80 - len(suffix)].rstrip() + suffix)
        number += 1
    return name


def _plan(modules: Path) -> list[dict]:
    """ONE-TIME (tracker OT-1): step 2. One entry per device:
    {slug, id, name, folder, owner}; owner is the entry that moves the old
    files (the others, twins that shared the file, get copies)."""
    bindings = old_bindings()
    twins = _twins()
    entries: list[dict] = []
    files = _root_module_files(modules)
    for path in files:
        stem = path.stem
        slug = plain_slug(stem)
        doc = store.read_path(path) or None
        keys: list[str] = []
        bound = stored_guid_key((doc or {}).get("boundGuidLocal", ""))
        if bound:
            keys.append(bound)
        for key, value in sorted(bindings.items()):
            if key.startswith("name:") or plain_slug(value) != slug:
                continue
            key = stored_guid_key(key)
            if key and key not in keys:
                keys.append(key)
        builtin = _builtin(slug)
        if not keys and builtin is not None:
            keys = [builtin[0]]
        if not keys:
            keys = [f"name:{slug or 'device'}"]
        for key in keys:
            if builtin is not None and key == builtin[0]:
                shown = builtin[1]
            else:
                shown = _shown(key, doc, stem, twins)
            entries.append({"file": path.name, "slug": slug, "id": key, "name": shown})
    old_dirs = {p.stem.casefold() for p in files}
    taken = {
        p.name.casefold()
        for p in modules.iterdir()
        if p.is_dir() and p.name.casefold() not in old_dirs
    }
    entries.sort(key=lambda e: (e["id"], store.folder_name_for(e["name"]).casefold()))
    owners: set[str] = set()
    for entry in entries:
        entry["folder"] = _unique(store.folder_name_for(entry["name"]), taken)
        taken.add(entry["folder"].casefold())
        entry["owner"] = entry["file"] not in owners
        owners.add(entry["file"])
    return entries


def _move_order(plan: list[dict]) -> list[dict]:
    """ONE-TIME (tracker OT-1): the copies first, so the owner's move never
    takes a file a twin still needs."""
    return [e for e in plan if not e["owner"]] + [e for e in plan if e["owner"]]


# --- 3. move -------------------------------------------------------------------


def _staged(modules: Path, entry: dict) -> Path:
    return modules.joinpath(*STAGING, Path(entry["file"]).stem)


def _stage_pictures(modules: Path, plan: list[dict]) -> None:
    """ONE-TIME (tracker OT-1): each old <slug>/ picture folder goes to
    cache/folders-move/ first: a new folder may have its name ("Keyboard"
    and "keyboard" are one folder on Windows)."""
    for entry in plan:
        old = modules / Path(entry["file"]).stem
        staged = _staged(modules, entry)
        if old.is_dir() and not (old / store.ID_FILE).is_file() and not staged.exists():
            staged.parent.mkdir(parents=True, exist_ok=True)
            os.replace(old, staged)


def _move_into(src: Path, dest: Path) -> None:
    """ONE-TIME (tracker OT-1): moves src to dest unless dest is there."""
    if not src.exists() or dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))


def _copy_into(src: Path, dest: Path) -> None:
    """ONE-TIME (tracker OT-1): copies src to dest unless dest is there."""
    if not src.exists() or dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def _imported_of(modules: Path, plan: list[dict], entry: dict) -> list[Path]:
    """ONE-TIME (tracker OT-1): imported/<slug>.* and imported/<slug>_* of
    this file (the longest matching slug wins: "a_b_1" is not "a_b")."""
    base = modules / "imported"
    if not base.is_dir():
        return []
    stems = sorted({Path(e["file"]).stem for e in plan}, key=len, reverse=True)
    mine = Path(entry["file"]).stem
    found = []
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        owner = next(
            (s for s in stems if path.name.startswith((f"{s}.", f"{s}_"))), None
        )
        if owner == mine:
            found.append(path)
    return found


def _move_device(modules: Path, backup: Path, plan: list[dict], entry: dict) -> None:
    """ONE-TIME (tracker OT-1): step 3 for one device: its folder and
    device.json, module.json, pictures, photo, recovery copy, imported files.
    The owner moves the old files; a twin copies them."""
    folder = modules / entry["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    id_file = folder / store.ID_FILE
    if not id_file.is_file():
        module_file.write_bytes(
            id_file,
            (
                json.dumps(
                    {"format": 1, "id": entry["id"], "name": entry["name"]}, indent=2
                )
                + "\n"
            ).encode("utf-8"),
        )
    put = _move_into if entry["owner"] else _copy_into
    stem = Path(entry["file"]).stem
    put(modules / entry["file"], folder / store.MODULE_FILE)
    pictures = folder / store.PICTURES
    staged = _staged(modules, entry)
    if staged.is_dir():
        for each in sorted(staged.iterdir()):
            put(each, pictures / each.name)
    for each in sorted(modules.glob(f"{stem}_photo.*")):
        if each.is_file() and each.suffix.lower() in store.PICTURE_EXT:
            if not any(pictures.glob("photo.*")):
                put(each, pictures / f"photo{each.suffix.lower()}")
    put(modules / "recovery" / f"{stem}.json", folder / store.RECOVERY_FILE)
    for each in _imported_of(modules, plan, entry):
        put(each, folder / store.IMPORTED / each.name)
    if not entry["owner"]:
        _own_bound_id(folder / store.MODULE_FILE, entry["id"])


def _own_bound_id(path: Path, key: str) -> None:
    """ONE-TIME (tracker OT-1): a twin's copy names its own id, else a later
    save would hand its folder the other twin's id."""
    doc = store.read_path(path)
    if not doc or not _is_guid(key):
        return
    if stored_guid_key(doc.get("boundGuidLocal", "")) in ("", key):
        return
    doc["boundGuidLocal"] = str(uuid.UUID(key)).upper()
    module_file.write_bytes(path, (json.dumps(doc, indent=2) + "\n").encode("utf-8"))


# --- 4. picture references ---------------------------------------------------


def _old_location(
    modules: Path, plan: list[dict], folder: Path, ref: str
) -> Path | None:
    """ONE-TIME (tracker OT-1): where an old-layout reference's file is now:
    modules-relative ("<slug>/x", "library/x", "qml/maps/x"), absolute or
    file:. An old "<slug>/x" is looked up where step 3 put it."""
    text = str(ref or "").strip()
    if not text:
        return None
    if text.lower().startswith("file:"):
        try:
            return store._local_path(text)  # noqa: SLF001 - the one URL reader
        except Exception:  # noqa: BLE001 - not a local file
            return None
    if Path(text).is_absolute():
        return Path(text)
    rel = text.replace("\\", "/").lstrip("/")
    if rel.lower().startswith("qml/maps/"):
        rel = rel[len("qml/maps/") :]
    own = folder / rel
    if rel.lower().startswith(f"{store.PICTURES}/") and own.is_file():
        return own
    head, _, rest = rel.partition("/")
    if rest:
        for entry in plan:
            if Path(entry["file"]).stem.casefold() == head.casefold():
                moved = modules / entry["folder"] / store.PICTURES / rest
                if moved.is_file():
                    return moved
                staged = _staged(modules, entry) / rest
                if staged.is_file():
                    return staged
    return modules / rel


def _copy_in(src: Path, folder: Path) -> str:
    """ONE-TIME (tracker OT-1): a picture from outside the folder copied into
    its pictures/ by store.copy_pictures (same name and bytes reused, same
    name other bytes: <stem>_<n><ext>, S133); its new reference."""
    ref = str(src.resolve())
    return store.copy_pictures(folder, [ref], folder)[ref]


def _replace_refs(doc: object, mapping: dict[str, str]) -> None:
    """ONE-TIME (tracker OT-1): the map's photo and every picture chip's src
    (store.named_refs' places) set through mapping."""
    if not isinstance(doc, dict):
        return
    image = doc.get("image")
    if isinstance(image, str) and image.strip() in mapping:
        doc["image"] = mapping[image.strip()]

    def walk(value: object) -> None:
        if isinstance(value, dict):
            src = value.get("src")
            if value.get("shape") == "image" or value.get("kind") == "image":
                if isinstance(src, str) and src in mapping:
                    value["src"] = mapping[src]
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)

    walk(doc.get("nodes"))


def _rewrite_doc(path: Path, modules: Path, plan: list[dict], folder: Path) -> None:
    """ONE-TIME (tracker OT-1): step 4 for one file: every named picture as
    "pictures/<name>", copied in when it is elsewhere; a missing one keeps
    store.normal_ref (the map shows "Picture missing", S108)."""
    if not path.is_file():
        return
    doc = store.read_path(path)
    if not doc:
        return  # damaged: kept as it is
    pictures = folder / store.PICTURES
    mapping: dict[str, str] = {}
    for ref in store.named_refs(doc):
        found = _old_location(modules, plan, folder, ref)
        if found is not None and found.is_file():
            if _inside(found, pictures):
                rel = found.resolve().relative_to(pictures.resolve()).as_posix()
                new = f"{store.PICTURES}/{rel}"
            else:
                new = _copy_in(found, folder)
        else:
            new = store.normal_ref(ref)
        if new != ref:
            mapping[ref] = new
    if not mapping:
        return
    _replace_refs(doc, mapping)
    module_file.write_bytes(path, (json.dumps(doc, indent=2) + "\n").encode("utf-8"))


def _rewrite_refs(modules: Path, plan: list[dict], folder: Path) -> None:
    """ONE-TIME (tracker OT-1): step 4 for a device: module.json and
    recovery.json."""
    for name in (store.MODULE_FILE, store.RECOVERY_FILE):
        _rewrite_doc(folder / name, modules, plan, folder)


# --- 5. templates ------------------------------------------------------------


def _move_templates(modules: Path, backup: Path) -> int:
    """ONE-TIME (tracker OT-1): step 5. templates/<name>.json ->
    templates/<name>/template.json with its pictures copied in; the old file
    goes into the backup's leftovers. The number converted."""
    base = modules / "templates"
    if not base.is_dir():
        return 0
    count = 0
    for path in sorted(base.glob("*.json")):
        doc = store.read_path(path)
        name = str((doc or {}).get("name") or path.stem)
        folder = store.template_dir(name)
        target = folder / "template.json"
        if not target.is_file():
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            _rewrite_doc(target, modules, [], folder)
        _move_into(path, backup / "leftovers" / "templates" / path.name)
        count += 1
    return count


# --- 6. leftovers ------------------------------------------------------------


def _archive_leftovers(modules: Path, backup: Path, plan: list[dict]) -> None:
    """ONE-TIME (tracker OT-1): step 6. What the new layout no longer uses
    goes into <backup>/leftovers/: library/, photo stashes, old recovery/,
    the staged picture folders, old photo files a photo.<ext> was already
    there for. Unattributed imported/ files stay."""
    leftovers = backup / "leftovers"

    def keep(path: Path) -> None:
        dest = leftovers / path.relative_to(modules)
        number = 2
        while dest.exists():
            dest = dest.with_name(f"{path.name} ({number})")
            number += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))

    for name in ("library", "recovery"):
        if (modules / name).is_dir():
            keep(modules / name)
    cache = modules / "cache"
    if cache.is_dir():
        for stash in sorted(cache.glob("photo-stash*")):
            keep(stash)
    staging = modules.joinpath(*STAGING)
    if staging.is_dir():
        keep(staging)
    for entry in plan:
        stem = Path(entry["file"]).stem
        for each in sorted(modules.glob(f"{stem}_photo.*")):
            if each.is_file():
                keep(each)


# --- 7. marker ---------------------------------------------------------------


def _write_marker(modules: Path, backup: str) -> None:
    """ONE-TIME (tracker OT-1): <modules>/folders.json, the layout marker."""
    _write_json(
        modules / MARKER,
        {
            "layout": LAYOUT,
            "movedAt": datetime.now().isoformat(timespec="seconds"),
            "backup": backup,
        },
    )


def _write_json(path: Path, doc: dict) -> None:
    module_file.write_bytes(path, (json.dumps(doc, indent=2) + "\n").encode("utf-8"))


def _read_json(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None
