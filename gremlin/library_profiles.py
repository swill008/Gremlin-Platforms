# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Profiles that aren't open, for the Device Library (10 S33-S34).

profiles_using() finds the profiles with bindings for some devices: the
saved ones in the profiles folder, the Recent list and the open one.
read_profile() reads one without opening it. Batch makes one Copy, Swap or
Change vJoy Output across several profiles: the open profile is changed in
memory and left unsaved (as a Device Pack import, 08 S74); the others are
read, changed and saved (each save a History entry). A profile that can't be
read or written is named in the warnings and left as it was; the rest still
change. No backup copies: the caller's autosave is the way back
(D-10-STREAMLINE).

Threads (10 section 6): the open profile and anything shared (devices,
settings) are touched on the main thread only. Inside responsive() (the
Device Library window's changes) the file work of saved profiles, reading
and writing them, runs on a program thread through background() while the
main thread's event loop keeps running, so the window repaints and shows it
is busy. User input waits until the step is done: nothing the user does can
start another change halfway through this one.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import uuid
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any, TypeVar

from PySide6 import QtCore

from gremlin import shared_state, util
from gremlin.profile import InputItem, Profile, reachable

_log = logging.getLogger("system")

_T = TypeVar("_T")

# A step in the background longer than this is given up (the program
# thread still ends by itself); its caller names it as not done.
BACKGROUND_LIMIT_S = 300.0
_LOOK_MS = 10

# Main thread only: inside responsive(), and inside a background() wait.
_responsive = 0
_waiting = False


@contextlib.contextmanager
def responsive() -> Iterator[None]:
    """Within it, background() steps called on the main thread keep the
    event loop running (the Device Library's changes, section 6)."""
    global _responsive
    _responsive += 1
    try:
        yield
    finally:
        _responsive -= 1


def _can_wait_here() -> bool:
    if not _responsive or _waiting:
        return False
    if threading.current_thread() is not threading.main_thread():
        return False
    return QtCore.QCoreApplication.instance() is not None


def background(name: str, fn: Callable[..., _T], *args: object) -> _T:
    """fn(*args), its value returned and its error raised here. Called on the
    main thread inside responsive(), it runs on a program thread while the
    event loop goes on (repaints, timers and signals; user input waits);
    anywhere else it simply runs here. fn must not touch the open profile
    or anything else the main thread owns. Raises TimeoutError after
    BACKGROUND_LIMIT_S."""
    if not _can_wait_here():
        return fn(*args)
    from gremlin import threads

    global _waiting
    done = threading.Event()
    box: dict[str, Any] = {}
    loop = QtCore.QEventLoop()

    def work() -> None:
        try:
            box["value"] = fn(*args)
        except BaseException as e:  # noqa: BLE001 - raised on the main thread
            box["error"] = e
        finally:
            done.set()

    # The main thread looks every few ms whether the step is done (no Qt
    # object is touched from the program thread).
    look = QtCore.QTimer()
    look.setInterval(_LOOK_MS)
    look.timeout.connect(lambda: done.is_set() and loop.quit())
    limit = QtCore.QTimer()
    limit.setSingleShot(True)
    limit.timeout.connect(loop.quit)
    _waiting = True
    try:
        threads.start(f"Device Library {name}", work)
        limit.start(int(BACKGROUND_LIMIT_S * 1000))
        look.start()
        # Bounded: the limit timer, or the program closing, ends it too.
        while not done.is_set() and limit.isActive():
            # -1: the program is closing (its event loops end at once).
            if (
                loop.exec(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                == -1
            ):
                break
    finally:
        _waiting = False
        look.stop()
        limit.stop()
    if not done.is_set():
        _log.error(f"Device Library: {name} didn't finish in time")
        raise TimeoutError(f"{name} didn't finish in time")
    if "error" in box:
        raise box["error"]
    return box["value"]


def _open_profile() -> Profile | None:
    return shared_state.current_profile


def _same(a: Path | str | None, b: Path | str | None) -> bool:
    if not a or not b:
        return False
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return str(a) == str(b)


def _is_open_path(path: Path | str) -> bool:
    """path is the open profile's file (an empty path: the open profile
    when it was never saved)."""
    current = _open_profile()
    if current is None:
        return False
    if not str(path) or str(path) == ".":
        return current.fpath is None
    return _same(current.fpath, path)


def _ids(guids: Iterable[str]) -> set[uuid.UUID]:
    found = set()
    for guid in guids:
        try:
            found.add(uuid.UUID(str(guid)))
        except ValueError:
            continue
    return found


def _action_count(profile: Profile, ids: set[uuid.UUID]) -> int:
    """Actions bound to inputs of these devices (the binding containers not
    counted)."""
    count = 0
    for device_id in ids:
        for item in profile.inputs.get(device_id, []):
            roots = Profile.roots_of([item])
            count += len(reachable(roots)) - len(roots)
    return count


def _recent() -> list[str]:
    from gremlin import config

    try:
        return [
            str(p)
            for p in config.Configuration().value(
                "global", "internal", "recent-profiles"
            )
            or []
        ]
    except Exception:
        _log.exception("Device Library: the Recent list couldn't be read")
        return []


def _candidates() -> list[Path]:
    """Saved profiles: the profiles folder (and its subfolders), then the
    Recent list, each file once."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            key = str(path.resolve()).lower()
        except OSError:
            key = str(path).lower()
        if key not in seen:
            seen.add(key)
            found.append(path)

    try:
        folder = util.profiles_dir()
        if folder.is_dir():
            for path in sorted(folder.rglob("*.xml")):
                add(path)
    except OSError:
        _log.exception("Device Library: the profiles folder couldn't be read")
    for entry in _recent():
        path = Path(entry)
        if path.is_file():
            add(path)
    return found


def _name(path: Path | str) -> str:
    return Path(path).stem if str(path) and str(path) != "." else "Untitled"


def is_open_path(path: Path | str) -> bool:
    """path is the open profile's file ("" is the open profile when it was
    never saved). Main thread only: it reads the open profile."""
    return _is_open_path(path)


def open_profile_row(guids: list[str], always_open: bool = False) -> dict | None:
    """The open profile's row for profiles_using, as it is in memory (an
    unsaved one has path ""), or None. Main thread only: it walks the open
    profile, which the main thread edits. always_open keeps it with 0
    actions when it has no bindings for these devices (10 S23, 08 S89,
    D-10-PROFILES: Copy, Swap and Change always offer it, ticked)."""
    current = _open_profile()
    if current is None:
        return None
    count = _action_count(current, _ids(guids))
    if not count and not always_open:
        return None
    path = str(current.fpath) if current.fpath else ""
    return {"path": path, "name": _name(path), "open": True, "actions": count}


def saved_profiles_using(guids: list[str], open_path: str = "") -> list[dict]:
    """The saved profiles (profiles folder, Recent list) with bindings for
    any of these devices, as on disk, leaving out open_path (the open
    profile's file, listed by open_profile_row). Reads files only: safe on
    a program thread. A profile that can't be read is left out."""
    ids = _ids(guids)
    rows: list[dict] = []
    if not ids:
        return rows
    for path in _candidates():
        if open_path and _same(open_path, path):
            continue
        read = read_profile(path)
        if isinstance(read, str):
            continue
        count = _action_count(read, ids)
        if count:
            rows.append(
                {
                    "path": str(path),
                    "name": _name(path),
                    "open": False,
                    "actions": count,
                }
            )
    return rows


def profiles_using(guids: list[str], always_open: bool = False) -> list[dict]:
    """The profiles with bindings for any of these devices:
    [{"path", "name", "open", "actions"}]. The open profile comes first,
    as it is now in memory (an unsaved one has path ""); the saved ones as
    on disk. A profile that can't be read is left out. always_open: the
    open profile is listed even with no bindings for them (0 actions).
    Main thread (the open profile); the model splits it with
    open_profile_row and saved_profiles_using to read files in the
    background."""
    if not _ids(guids) and not always_open:
        return []
    rows: list[dict] = []
    row = open_profile_row(guids, always_open)
    if row is not None:
        rows.append(row)
    current = _open_profile()
    open_path = str(current.fpath) if current is not None and current.fpath else ""
    return rows + saved_profiles_using(guids, open_path)


def read_profile(path: Path) -> Profile | str:
    """The profile at path, read without opening it, or why it can't be
    read (missing, damaged, a version this program can't read)."""
    path = Path(path)
    try:
        return background("read profile", _read_here, path)
    except TimeoutError as e:
        return f"{path.name} couldn't be read: {e}."


def _read_here(path: Path) -> Profile | str:
    """read_profile on this thread (a file only: safe on a program thread)."""
    if not path.is_file():
        return f"{path.name}: the file isn't there."
    # Read without binding: the open profile's OSC rows stay the ones
    # shown, and the Logical Device's module file is not changed (a
    # version 14 profile keeps its rows in pending_logical_rows until it
    # is saved, D-04-LD-FILE).
    made = Profile(bind=False)
    try:
        made.from_xml(path)
    except Exception as e:  # noqa: BLE001 - any failure is a reason to show
        reason = str(e) or type(e).__name__
        return f"{path.name} couldn't be read: {reason}"
    return made


def save_profile(profile: Profile, path: Path) -> None:
    """Saves a profile that isn't open, as Profile.to_xml does (written
    safely, a History entry), with its file written through background():
    the device names are read here on the main thread first. A saved
    version 14 profile's Logical Device rows go into the module file first
    (backup kept, as to_xml does), so none are dropped (D-04-LD-FILE)."""
    profile.commit_pending_logical_rows(Path(path))
    profile.library.prune_for_save()
    profile.device_database.update_for_uuids(profile.inputs)

    def write() -> str:
        from gremlin.modules import module_file

        text = profile._xml_text()
        module_file.write_text(Path(path), text, encoding="utf-8-sig", newline="")
        return text

    text = background("save profile", write)
    before = profile._saved_snapshot
    profile._set_saved(text)
    if before != text:
        from gremlin import history_profile

        history_profile.record_save(Path(path), before, text)
    from gremlin.ui.live_debug import trace

    trace("SAVE", "Profile", "to_xml", path, "ok")


class Batch:
    """One Copy, Swap or Change vJoy Output across profiles (10 S33-S34)."""

    def __init__(self, paths: list[Path], label: str) -> None:
        self.label = label
        self.paths: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            key = "<open>" if _is_open_path(path) else str(Path(path)).lower()
            if key not in seen:
                seen.add(key)
                self.paths.append(Path(path))

    def apply(self, change: Callable[[Profile, bool], dict]) -> dict:
        """change(profile, is_open) edits the profile in memory and returns
        its notes ({"notes": [...], "warnings": [...]}; "ok": False, or an
        error raised, means it didn't change). Returns a Result with
        "changed" and "failed" (paths; a saved profile the change left as
        it was is in neither and isn't written); ok is False only when
        nothing changed and something failed."""
        result: dict = {
            "ok": True,
            "error": "",
            "warnings": [],
            "notes": [],
            "changed": [],
            "failed": [],
        }
        for path in self.paths:
            if _is_open_path(path):
                problem = self._apply_open(change, result)
            else:
                problem = self._apply_saved(path, change, result)
            if problem:
                result["warnings"].append(problem)
                result["failed"].append(str(path))
        if result["failed"] and not result["changed"]:
            result["ok"] = False
            result["error"] = f"{self.label}: no profile could be changed."
        return result

    @staticmethod
    def _merge(answer: object, result: dict) -> str:
        """Notes and warnings of one change into the result; the reason it
        failed, or ""."""
        if not isinstance(answer, dict):
            return ""
        result["notes"].extend(str(n) for n in answer.get("notes") or [])
        result["warnings"].extend(str(w) for w in answer.get("warnings") or [])
        if answer.get("ok", True) is False:
            return str(answer.get("error") or "it couldn't be changed")
        return ""

    def _apply_open(self, change: Callable[[Profile, bool], dict], result: dict) -> str:
        profile = _open_profile()
        assert profile is not None
        name = _name(profile.fpath or "")
        before = profile._xml_text()
        items = {
            id(item): (key, profile.input_snapshot(item))
            for key, item in _keyed_items(profile)
        }
        answer: object = None
        failure = ""
        try:
            with profile.library.change():
                answer = change(profile, True)
                if isinstance(answer, dict) and answer.get("ok", True) is False:
                    raise _Refused(str(answer.get("error") or ""))
        except _Refused as e:
            failure = str(e) or "it couldn't be changed"
        except Exception as e:  # noqa: BLE001 - named, the others go on
            _log.exception(f"{self.label}: the open profile couldn't be changed")
            failure = str(e) or type(e).__name__
        if failure:
            _put_back(profile, before, items)
            return f"{name} (open) wasn't changed: {failure}"
        self._merge(answer, result)
        profile.note_edit()
        result["changed"].append(str(profile.fpath or ""))
        return ""

    def _apply_saved(
        self, path: Path, change: Callable[[Profile, bool], dict], result: dict
    ) -> str:
        read = read_profile(path)
        if isinstance(read, str):
            return f"{read} It was left as it was."
        try:
            answer = change(read, False)
        except Exception as e:  # noqa: BLE001 - named, the others go on
            _log.exception(f"{self.label}: {path} couldn't be changed")
            return f"{path.name} wasn't changed: {str(e) or type(e).__name__}"
        said: dict = {"notes": [], "warnings": []}
        problem = self._merge(answer, said)
        if problem:
            return f"{path.name} wasn't changed: {problem}"
        if read._xml_text() == read._saved_snapshot:
            # Nothing to save: the file stays as it is.
            result["notes"].extend(said["notes"])
            result["warnings"].extend(said["warnings"])
            return ""
        try:
            # Written safely (a temporary file, then a swap) with a History
            # entry, as any save; the file in the background (section 6).
            save_profile(read, path)
        except Exception as e:  # noqa: BLE001 - named, the others go on
            _log.exception(f"{self.label}: {path} couldn't be saved")
            return (
                f"{path.name} couldn't be saved ({str(e) or type(e).__name__}); "
                "it was left as it was."
            )
        # A profile left as it was says nothing but why.
        result["notes"].extend(said["notes"])
        result["warnings"].extend(said["warnings"])
        result["changed"].append(str(path))
        return ""


class _Refused(Exception):
    """A change answered ok False."""


def _keyed_items(profile: Profile) -> list[tuple[tuple, InputItem]]:
    return [
        ((device_id, item.input_type, item.input_id, item.mode), item)
        for device_id, items in profile.inputs.items()
        for item in items
    ]


def _put_back(
    profile: Profile, before: str, items: dict[int, tuple[tuple, dict | None]]
) -> None:
    """After Library.change put the structure back: actions edited in place
    get their settings back from the snapshots taken first."""
    if profile._xml_text() == before:
        return
    for key, item in _keyed_items(profile):
        kept = items.get(id(item))
        if kept is None:
            continue
        if profile.input_snapshot(item) != kept[1]:
            device_id, input_type, input_id, mode = kept[0]
            try:
                profile.put_input(device_id, input_type, input_id, mode, kept[1])
            except Exception:  # noqa: BLE001
                _log.exception("Device Library: an input couldn't be put back")
    if profile._xml_text() != before:
        _log.error("Device Library: the open profile couldn't be put back fully")
