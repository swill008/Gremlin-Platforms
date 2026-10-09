# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Recovery copies of unsaved profile edits (04 S94, Q14).

While the open profile has unsaved changes, a copy of it is kept about
every minute in the data folder's "recovery" folder, one file per profile
path (Untitled too). On the next open of that profile, or at start after a
crash, the program offers it: Restore / Discard / Not now, as the Button
Map's Autosave does. Save, Discard and a clean close remove the copies this
session wrote; a copy put off with Not now stays until it is restored or
discarded (or this session's own edits to that profile replace it).

The copy is written on the main thread, as the Button Map's is: the text is
the one the unsaved check already builds, and the file is small.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from gremlin import clock
from gremlin.edits import edit_count

if TYPE_CHECKING:
    from gremlin.profile import Profile

# How often the copy is kept (S94: "about every minute"). Tests and the
# smoke set it lower before the Backend starts its timer.
INTERVAL_SECONDS = 60.0


def default_folder() -> Path:
    from gremlin.util import data_folder

    return Path(data_folder()) / "recovery"


def profile_key(path: str | Path | None) -> str:
    """One name per profile path (case and slashes as Windows sees them)."""
    if not path or str(path) in ("", "."):
        return "profile-untitled"
    full = os.path.normcase(os.path.abspath(str(path)))
    digest = hashlib.sha1(full.encode("utf-8")).hexdigest()[:16]
    stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in Path(full).stem)
    return f"profile-{stem[:40]}-{digest}"


class ProfileRecovery:
    """Keeps, offers and removes profile recovery copies."""

    def __init__(self, folder: Callable[[], Path] = default_folder) -> None:
        self._folder = folder
        # Copies this session wrote: file -> the XML in it.
        self._written: dict[Path, str] = {}
        # (profile, edit count) at the last tick that left nothing to do.
        self._seen: tuple[int, int] | None = None

    def file_for(self, path: str | Path | None) -> Path:
        return self._folder() / f"{profile_key(path)}.json"

    # --- keeping ----------------------------------------------------------

    def tick(self, profile: Profile) -> None:
        """Keeps a copy when the profile has unsaved changes; with none left
        (everything undone), removes the copy this session wrote."""
        seen = (id(profile), edit_count())
        if seen == self._seen:
            return
        target = self.file_for(getattr(profile, "fpath", None))
        text = profile._xml_text()
        if text == getattr(profile, "_saved_snapshot", None):
            if target in self._written:
                self._remove(target)
            self._seen = seen
            return
        if self._written.get(target) == text and target.is_file():
            self._seen = seen
            return
        if self._write(target, getattr(profile, "fpath", None), text):
            self._seen = seen

    def _write(self, target: Path, path: object, text: str) -> bool:
        doc = {
            "path": str(path) if path else "",
            "savedAt": datetime.fromtimestamp(clock.now()).isoformat(
                timespec="seconds"
            ),
            "xml": text,
        }
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".tmp")
            tmp.write_text(json.dumps(doc), encoding="utf-8")
            os.replace(tmp, target)
        except OSError:
            logging.getLogger("system").warning(
                f"The profile's recovery copy could not be written to {target}."
            )
            return False
        self._written[target] = text
        return True

    def _remove(self, target: Path) -> None:
        self._written.pop(target, None)
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass

    # --- removing ---------------------------------------------------------

    def saved(self, path: str | Path | None) -> None:
        """After a Save (or Save As to path): this session's copies and
        path's copy go; the edits are in the file now."""
        self.forget_session()
        self._remove(self.file_for(path))

    def forget_session(self) -> None:
        """Discard (the profile was replaced after Save / Discard) or a
        clean close: the copies this session wrote go. A copy put off with
        Not now stays."""
        for target in list(self._written):
            self._remove(target)
        self._seen = None

    def discard(self, path: str | Path | None) -> None:
        """The offer's Discard."""
        self._remove(self.file_for(path))

    # --- offering ---------------------------------------------------------

    def _read(self, path: str | Path | None) -> dict | None:
        try:
            doc = json.loads(self.file_for(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(doc, dict) or not isinstance(doc.get("xml"), str):
            return None
        return doc

    def offer_for(self, path: str | Path | None) -> dict | None:
        """{path, name, savedAt} of the copy kept for this profile path, or
        None. A copy this session wrote is no crash's copy."""
        if self.file_for(path) in self._written:
            return None
        doc = self._read(path)
        if doc is None:
            return None
        where = str(path) if path else ""
        return {
            "path": where,
            "name": Path(where).name if where else "Untitled",
            "savedAt": str(doc.get("savedAt") or ""),
        }

    def restore(self, path: str | Path | None, current: Profile) -> Profile | None:
        """A new Profile from path's copy, unsaved (compared with current,
        the profile as opened from its file), or None when the copy can't
        be read. This session carries the copy on: Save or Discard removes
        it."""
        from gremlin.profile import Profile as _Profile

        doc = self._read(path)
        if doc is None:
            return None
        target = self.file_for(path)
        scratch = target.with_suffix(".restoring.xml")
        restored = _Profile()
        try:
            scratch.parent.mkdir(parents=True, exist_ok=True)
            scratch.write_text(doc["xml"], encoding="utf-8")
            restored.from_xml(scratch)
        except Exception:
            logging.getLogger("system").exception(
                f"The recovery copy {target} could not be read."
            )
            return None
        finally:
            try:
                scratch.unlink(missing_ok=True)
            except OSError:
                pass
        restored.fpath = Path(str(path)) if path else None  # type: ignore[assignment]
        same = profile_key(getattr(current, "fpath", None)) == profile_key(path)
        base = getattr(current, "_saved_snapshot", None) if same else None
        restored._set_saved(base or "")
        # None: unsaved whatever it holds (no file to compare with).
        restored._saved_snapshot = base
        restored.note_edit()
        self._written[target] = doc["xml"]
        self._seen = None
        return restored
