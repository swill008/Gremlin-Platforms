# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

# ONE-TIME (tracker OT-2b): remove only when the user says (user,
# 2026-11-20: "dont remove it unless I direct it").

"""ONE-TIME (tracker OT-2b): at start, every device map still saved in the
layout from before the background and foreground planes (a top-level
"image"/"photo"/"imageWidth"/"imageHeight", no bottom background picture) is
written in today's layout, once. The conversion is planes_once's, the same
one a map gets in memory when it opens (OT-2, which stays).

- live maps: <modules root>/<device folder>/module.json
- Device Library saved setups: the .gmap files in the library folder
  (module.json and bindings/outputs/*.json inside; exact/ is the autosave's
  verbatim copy for Undo and is kept as it was)

Each file is backed up first to <data folder>/backup/<date> map photo
convert/<path> (an existing backup is never written over), written safely
(temporary file, then a swap) and read back; a file that fails is left as
it was, reported and tried again next start. Exports (.gmap in export),
History copies and the imported backups are not touched. With nothing old
left, <modules root>/.planes-converted is written and later starts do
nothing. Never shows a message; a huge folder is capped per start.
"""

from __future__ import annotations

import io
import json
import logging
import shutil
import zipfile
from collections.abc import Callable
from datetime import date
from pathlib import Path

from gremlin.modules import module_file as module_file_io
from gremlin.modules import planes_once, store

syslog = logging.getLogger("system")

MARKER = ".planes-converted"
BACKUP_NAME = "map photo convert"
LIBRARY_NAME = "device library"
# Files looked at per start; the rest wait for the next start.
MAX_FILES = 2000

_GMAP_MODULE = "module.json"
_GMAP_OUTPUTS = "bindings/outputs/"


def _is_old(doc: object) -> bool:
    return isinstance(doc, dict) and any(k in doc for k in planes_once.OLD_PHOTO_KEYS)


def _is_new(doc: object, had_image: bool) -> bool:
    if not isinstance(doc, dict) or _is_old(doc):
        return False
    if not had_image:
        return True
    return store._bottom_picture_index(doc.get("nodes")) >= 0


def _backup_dir(data_folder: Path) -> Path:
    return Path(data_folder) / "backup" / f"{date.today().isoformat()} {BACKUP_NAME}"


def _relative(path: Path, data_folder: Path, modules_root: Path) -> Path:
    for base, prefix in ((data_folder, Path()), (modules_root, Path("modules"))):
        try:
            return prefix / Path(path).resolve().relative_to(Path(base).resolve())
        except ValueError:
            continue
    return Path(path.name)


def _backup(path: Path, data_folder: Path, modules_root: Path) -> Path:
    """Copies path into the backup folder; an existing backup is never
    written over (" (2)", " (3)"... added). Raises OSError."""
    dest = _backup_dir(data_folder) / _relative(path, data_folder, modules_root)
    number = 2
    while dest.exists():
        dest = dest.with_name(f"{dest.stem} ({number}){dest.suffix}")
        number += 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    if dest.stat().st_size != Path(path).stat().st_size:
        raise OSError(f"backup {dest} is incomplete")
    return dest


class _Run:
    def __init__(self, modules_root: Path, data_folder: Path) -> None:
        self.modules_root = Path(modules_root)
        self.data_folder = Path(data_folder)
        self.converted = 0
        self.left = 0
        self.problems: list[str] = []
        self.seen = 0
        self.zip_photo: Callable[[dict, dict], None] | None = None

    def _room(self) -> bool:
        self.seen += 1
        if self.seen > MAX_FILES:
            self.left += 1
            return False
        return True

    # --- live maps ----------------------------------------------------------

    def live_map(self, path: Path) -> None:
        if not self._room():
            return
        try:
            raw = path.read_bytes()
        except OSError as exc:
            self.left += 1
            self.problems.append(f"{path}: not read ({exc})")
            return
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError, RecursionError):
            self.problems.append(f"{path}: not a readable map, left as it is")
            return
        if not _is_old(doc):
            return
        had_image = bool(str(doc.get("image") or "").strip())
        try:
            planes_once.old_photo_to_layer(doc, path.parent)
            data, _ = store._doc_bytes(doc)
            _backup(path, self.data_folder, self.modules_root)
            module_file_io.write_bytes(path, data)
            check = json.loads(path.read_bytes().decode("utf-8"))
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            self.left += 1
            self.problems.append(f"{path}: not converted ({exc})")
            return
        if not _is_new(check, had_image):
            self.left += 1
            self.problems.append(f"{path}: still in the old layout after writing")
            return
        self.converted += 1

    # --- Device Library saved setups ------------------------------------------

    def saved_setup(self, path: Path) -> None:
        if not self._room():
            return
        try:
            with zipfile.ZipFile(path, "r") as zf:
                infos = zf.infolist()
                entries = {info.filename: zf.read(info) for info in infos}
        except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
            self.problems.append(f"{path}: not a readable saved setup ({exc})")
            return
        targets = [
            name
            for name in entries
            if name == _GMAP_MODULE
            or (
                name.startswith(_GMAP_OUTPUTS)
                and "/" not in name[len(_GMAP_OUTPUTS) :]
                and name.lower().endswith(".json")
            )
        ]
        files = {Path(n).name: b for n, b in entries.items() if not n.endswith(".json")}
        changed: dict[str, bytes] = {}
        images: dict[str, bool] = {}
        for name in targets:
            try:
                doc = json.loads(entries[name].decode("utf-8"))
            except (UnicodeError, ValueError, RecursionError):
                continue  # a damaged module file kept as it was (10 S20a)
            if not _is_old(doc):
                continue
            images[name] = bool(str(doc.get("image") or "").strip())
            # The conversion a saved setup gets when it opens (OT-2): passed
            # in by the caller, as this package never imports the UI.
            if self.zip_photo is not None:
                self.zip_photo(doc, files)
            if _is_old(doc):
                planes_once.old_photo_to_layer(doc, None)
            changed[name] = store._doc_bytes(doc)[0]
        if not changed:
            return
        try:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as out:
                for info in infos:
                    data = changed.get(info.filename, entries[info.filename])
                    out.writestr(info, data)
            _backup(path, self.data_folder, self.modules_root)
            module_file_io.write_bytes(path, buffer.getvalue())
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                ok = sorted(names) == sorted(entries) and all(
                    _is_new(json.loads(zf.read(n).decode("utf-8")), images[n])
                    for n in changed
                )
        except (
            OSError,
            zipfile.BadZipFile,
            UnicodeError,
            ValueError,
            RecursionError,
        ) as exc:
            self.left += 1
            self.problems.append(f"{path}: not converted ({exc})")
            return
        if not ok:
            self.left += 1
            self.problems.append(f"{path}: still in the old layout after writing")
            return
        self.converted += 1


def _device_maps(modules_root: Path) -> list[Path]:
    return [
        folder / store.MODULE_FILE
        for folder in store._device_folders(modules_root)
        if (folder / store.MODULE_FILE).is_file()
    ]


def _saved_setups(library: Path) -> list[Path]:
    if not library.is_dir():
        return []
    try:
        return sorted(p for p in library.rglob("*.gmap") if p.is_file())
    except OSError:
        return []


def run_if_needed(
    modules_root: Path,
    data_folder: Path,
    library_folder: Path | None = None,
    zip_photo: Callable[[dict, dict], None] | None = None,
) -> list[str]:
    """Converts every old-layout live map and Device Library saved setup on
    disk, once (see the module). library_folder: the Device Library folder
    (device_library.folder()); default <data folder>/device library.
    zip_photo: the on-open conversion of a saved setup's map
    (device_pack._old_photo_in_zip), given by the caller.
    Returns the problems (empty when all went well or nothing was to do)."""
    modules_root = Path(modules_root)
    marker = modules_root / MARKER
    if marker.is_file() or not modules_root.is_dir():
        return []
    library = (
        Path(library_folder)
        if library_folder is not None
        else Path(data_folder) / LIBRARY_NAME
    )
    run = _Run(modules_root, Path(data_folder))
    run.zip_photo = zip_photo
    for path in _device_maps(modules_root):
        run.live_map(path)
    for path in _saved_setups(library):
        run.saved_setup(path)
    if run.converted or run.problems:
        problems = f" ({'; '.join(run.problems)})" if run.problems else ""
        syslog.info(
            f"Map photo convert: {run.converted} maps converted, "
            f"{run.left} left{problems}"
        )
    if run.left == 0:
        try:
            module_file_io.write_bytes(
                marker,
                (
                    json.dumps(
                        {
                            "date": date.today().isoformat(),
                            "converted": run.converted,
                            "problems": len(run.problems),
                        },
                        indent=2,
                    )
                    + "\n"
                ).encode("utf-8"),
            )
        except OSError as exc:
            run.problems.append(f"{marker}: not written ({exc})")
    return run.problems
