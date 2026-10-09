# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The program's history: every saved change, kept in its own files.

One file per area in the history folder (profile.jsonl, modules.jsonl,
button-map.jsonl, settings.jsonl): one JSON line per entry, only ever
appended. Only one copy of the program runs at a time (its lock file), so
only this one writes them. A damaged line (a crash mid-write) is skipped.
Pictures an entry needs are kept once each in history/files, named by
their content. An entry holds what changed before and after, so it can be
looked at and put back (Restore).

record() only queues the entry. A writer thread (gremlin.threads) appends
what is queued and ends by itself when nothing more comes. close() (at
quit) writes what is left and anything recorded after it at once. Entries
older than the Options limit, or past a file's size limit, go when the
first entry of a session is written.
"""

from __future__ import annotations

import hashlib
import json
import logging
import queue
import re
import shutil
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gremlin import clock, threads

AREAS = {
    "profile": "Profile",
    "modules": "Module files",
    "button-map": "Button Map",
    "settings": "Settings",
    # Tools › History's own: the "History cleared" entries (08 S12b).
    "history": "History",
}
# A clearing of History (08 S12b): never removed by the clean-up.
CLEARED_KIND = "cleared"
# Options › History: how long entries are kept and how big a file may grow.
KEEP_DAYS = 90
MAX_MEGABYTES = 20
# How long the writer waits for more before it ends.
_IDLE = 1.0
# How long entries() waits for the writer to write what is queued.
_SETTLE = 2.0
# Whole-profile copies kept per profile (the newest saves).
SNAPSHOTS = 20

_queue: queue.Queue[dict | Callable[[], None]] = queue.Queue()
_write_lock = threading.Lock()
# One queued item is handled at a time, by the writer or by flush(): the
# comparisons share _last_pictures and must keep their order (GL-187).
_handle_lock = threading.RLock()
_start_lock = threading.Lock()
_writer: threading.Thread | None = None
_stop = threading.Event()
_pruned = False
# At quit (close()): entries are written at once, no writer is started.
_closing = False
# Pictures kept this session: an entry waiting to be written may need them
# (a delete keeps its pictures at once), so pruning leaves them.
_kept_now: set[str] = set()

syslog = logging.getLogger("system")


def folder() -> Path:
    from gremlin import util

    return util.history_dir()


def files_folder() -> Path:
    path = folder() / "files"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _limits() -> tuple[int, int]:
    """(days, megabytes) from Options, or the defaults."""
    try:
        from gremlin.config import Configuration

        cfg = Configuration()
        days = int(cfg.value("global", "history", "keep-days"))
        megabytes = int(cfg.value("global", "history", "max-megabytes"))
        return max(1, days), max(1, megabytes)
    except Exception:
        return KEEP_DAYS, MAX_MEGABYTES


def record(
    area: str,
    title: str,
    subject: dict,
    before: Any,  # noqa: ANN401
    after: Any,  # noqa: ANN401
    kind: str = "save",
) -> str:
    """Queues one entry; returns its id. area: one of AREAS. title: what
    happened, as the History window shows it. subject: what it was about
    (profile, device, input, mode, file...). before/after: the content."""
    entry = _make(area, title, subject, before, after, kind)
    if _held(entry):
        return entry["id"]
    if _closing:
        _handle(entry)
        return entry["id"]
    _queue.put(entry)
    _wake_writer()
    return entry["id"]


def _make(
    area: str,
    title: str,
    subject: dict,
    before: Any,  # noqa: ANN401
    after: Any,  # noqa: ANN401
    kind: str,
) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "at": clock.now(),
        "area": area if area in AREAS else "settings",
        "kind": kind,
        "title": title,
        "subject": subject,
        "before": before,
        "after": after,
    }


def write_now(
    area: str,
    title: str,
    subject: dict,
    before: Any,  # noqa: ANN401
    after: Any,  # noqa: ANN401
    kind: str = "save",
) -> str:
    """Writes an entry at once: for work later() runs on the writer thread."""
    entry = _make(area, title, subject, before, after, kind)
    held = getattr(_capture, "entries", None)
    if held is not None:
        held.append(entry)
        return entry["id"]
    _append(entry)
    return entry["id"]


def later(work: Callable[[], None]) -> None:
    """Runs work on the writer thread (comparing a save, keeping pictures),
    so the save itself stays quick. It writes with write_now()."""
    if _held(work):
        return
    if _closing:
        _handle(work)
        return
    _queue.put(work)
    _wake_writer()


# --- one action, one entry (10 S51, 08 S12a) -----------------------------------
#
# An action made of several steps that each record (Remove from Library:
# Delete Device's autosave, its module file, the Library's list) opens a
# group: what the opening thread records until the group ends is held, then
# written as one entry (kind "group") holding each part, so Restore puts
# them all back. Other threads record as usual.

GROUP_KIND = "group"
_group_lock = threading.Lock()
_group: dict | None = None
# On the writer thread, while a group's held work runs: write_now() lands here.
_capture = threading.local()


def begin_group(title: str, area: str = "modules") -> str:
    """Opens a group named title; returns its token ("" when one is open
    already: what this records joins that one)."""
    global _group
    with _group_lock:
        if _group is not None:
            return ""
        token = uuid.uuid4().hex
        _group = {
            "token": token,
            "title": title,
            "area": area,
            "thread": threading.get_ident(),
            "items": [],
        }
        return token


def end_group(token: str) -> None:
    """Ends the group begin_group() opened (a token "" or not the open
    one: nothing). What it held is written as one entry."""
    global _group
    with _group_lock:
        if not token or _group is None or _group["token"] != token:
            return
        mine = _group["thread"] == threading.get_ident()
    if mine:
        _save_settings_now()
    with _group_lock:
        if _group is None or _group["token"] != token:
            return
        group, _group = _group, None
    if group["items"]:
        later(lambda: _write_group(group))


def _save_settings_now() -> None:
    """Settings changed in the group are saved (and so recorded) now, not
    a second later, so they join it."""
    try:
        from gremlin import deferred_write

        if deferred_write.pending("configuration"):
            deferred_write.flush("configuration")
    except Exception:  # noqa: BLE001 - the group ends either way
        syslog.exception("History: settings not saved with the change")


def _held(item: dict | Callable[[], None]) -> bool:
    """True when the open group takes item (recorded on its thread)."""
    with _group_lock:
        if _group is None or _group["thread"] != threading.get_ident():
            return False
        _group["items"].append(item)
        return True


def _write_group(group: dict) -> None:
    parts: list[dict] = []
    _capture.entries = parts
    try:
        for item in group["items"]:
            if callable(item):
                try:
                    item()
                except Exception:
                    syslog.exception("History: could not record a change")
            else:
                parts.append(item)
    finally:
        _capture.entries = None
    if not parts:
        return
    if len(parts) == 1:
        entry = dict(parts[0], title=group["title"] or parts[0]["title"])
        _append(entry)
        return
    _append(group_entry(group["area"], group["title"], parts))


def group_entry(area: str, title: str, parts: list[dict]) -> dict:
    """One entry for several: before/after list each part's side."""

    def side(which: str) -> list[dict]:
        return [
            {
                "area": p.get("area"),
                "kind": p.get("kind"),
                "title": p.get("title"),
                "subject": p.get("subject"),
                "side": p.get(which),
            }
            for p in parts
        ]

    subject: dict = {"parts": [str(p.get("title") or "") for p in parts]}
    # The devices its parts name, once each (10 S56: Show in History).
    devices: list[dict] = []
    for part in parts:
        for dev in (part.get("subject") or {}).get("devices") or []:
            if isinstance(dev, dict) and dev not in devices:
                devices.append(dev)
    if devices:
        subject["devices"] = devices
    return _make(area, title, subject, side("before"), side("after"), GROUP_KIND)


def _wake_writer() -> None:
    global _writer
    with _start_lock:
        if _writer is not None:
            return
        _stop.clear()
        _writer = threads.start("History", _run, stop=_stop.set)


def _run() -> None:
    global _writer
    _prune_once()
    while True:
        try:
            entry = _queue.get(timeout=0.05 if _stop.is_set() else _IDLE)
        except queue.Empty:
            # Nothing more came: end. Decided under the same lock record()
            # starts a writer with, so an entry queued now isn't left behind.
            with _start_lock:
                if _queue.empty():
                    _writer = None
                    return
            continue
        try:
            _handle(entry)
        finally:
            _queue.task_done()


def flush() -> None:
    """Writes every queued entry now, on this thread (at quit, in tests)."""
    while True:
        # Bounded: a writer stuck on one item never holds up quit (S24).
        if not _handle_lock.acquire(timeout=_SETTLE):
            syslog.warning("History: the writer is still busy; not waiting for it")
            return
        try:
            try:
                entry = _queue.get_nowait()
            except queue.Empty:
                return
            try:
                _handle(entry)
            finally:
                _queue.task_done()
        finally:
            _handle_lock.release()


def _settle(timeout: float = _SETTLE) -> None:
    """Before reading: what is queued gets written. While the writer runs it
    does that and this waits for it (bounded), so profile comparisons and
    picture copies never run on the caller's (UI) thread beside it (08 S23,
    GL-187). With no writer running, it is written here."""
    with _start_lock:
        writer = _writer
    if writer is None or writer is threading.current_thread():
        flush()
        return
    deadline = time.monotonic() + timeout
    with _queue.all_tasks_done:
        while _queue.unfinished_tasks:
            left = deadline - time.monotonic()
            if left <= 0:
                syslog.warning("History: the writer is busy; listing what is written")
                return
            _queue.all_tasks_done.wait(left)


def close(timeout: float = 2.0) -> None:
    """At quit: writes what is queued, here, and anything recorded from now
    on at once; waits (bounded) for a writer still writing, so the program
    doesn't end in the middle of a line. Never raises: quit goes on (an
    update to install, a restart) whatever History couldn't write."""
    global _closing
    _closing = True
    try:
        flush()
        with _start_lock:
            writer = _writer
        if writer is not None and writer is not threading.current_thread():
            _stop.set()
            writer.join(timeout)
        flush()
    except Exception:
        syslog.exception("History: could not write the last changes")


def _handle(item: dict | Callable[[], None]) -> None:
    with _handle_lock:
        if callable(item):
            try:
                item()
            except Exception:
                syslog.exception("History: could not record a change")
            return
        _append(item)


def _file(area: str) -> Path:
    return folder() / f"{area}.jsonl"


def _append(entry: dict) -> None:
    from gremlin.ui.live_debug import trace

    path: Path | str = f"{entry.get('area')}.jsonl"
    with _write_lock:
        try:
            # Finding the folder makes it (util.history_dir()): a folder that
            # can't be made is a warning, not an error out of the writer
            # thread or quit.
            path = _file(entry["area"])
            line = json.dumps(entry, ensure_ascii=False) + "\n"
            path.parent.mkdir(parents=True, exist_ok=True)
            # A line cut short by a crash: this entry starts on a line of its
            # own, or it would be lost with it.
            if _ends_cut(path):
                line = "\n" + line
            with open(path, "a", encoding="utf-8", newline="") as out:
                out.write(line)
        except (OSError, TypeError, ValueError) as exc:
            syslog.warning(f"History: could not write {path}: {exc}")
            trace("SAVE", "History", "record", path, "error")
            return
    trace("SAVE", "History", "record", path, "ok")


def _ends_cut(path: Path) -> bool:
    """True when the file doesn't end with a line end (a crash mid-write)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            if f.tell() == 0:
                return False
            f.seek(-1, 2)
            return f.read(1) != b"\n"
    except OSError:
        return False


def _text(path: Path) -> str:
    """The file's text; a character cut by a crash doesn't stop the rest
    being read (that line is skipped as damaged)."""
    return path.read_bytes().decode("utf-8", errors="replace")


# What was read of each file: the History window comes to the front often,
# and a file can hold 20 MB. Only what was appended since is read and
# parsed; a file rewritten (clean-up) or replaced is read again (GL-041).
_read: dict[str, dict] = {}
_read_lock = threading.Lock()
_TAIL = 64


def _lines(area: str, fresh: bool = False) -> list[dict]:
    """The file's entries, oldest first. fresh: read it all again, into new
    objects the caller may change (the clean-up)."""
    path = _file(area)
    if fresh:
        try:
            return _parse(_text(path))
        except OSError:
            return []
    key = str(path)
    with _read_lock:
        try:
            stat = path.stat()
        except OSError:
            _read.pop(key, None)
            return []
        now = (stat.st_ino, stat.st_dev, stat.st_mtime_ns, stat.st_size)
        known = _read.get(key)
        if known is not None and known["stat"] == now:
            return list(known["entries"])
        start, found = 0, []
        if known is not None and known["stat"][:2] == now[:2]:
            if stat.st_size >= known["offset"]:
                start, found = known["offset"], list(known["entries"])
        try:
            with open(path, "rb") as f:
                if start and known is not None:
                    # Still the same text up to where it was read last time?
                    f.seek(max(0, start - _TAIL))
                    if f.read(start - max(0, start - _TAIL)) != known["tail"]:
                        start, found = 0, []
                f.seek(start)
                data = f.read()
        except OSError:
            _read.pop(key, None)
            return []
        # Whole lines only: a line still being written (or cut by a crash)
        # is read again, with what comes after it, next time.
        whole = data.rfind(b"\n") + 1
        found.extend(_parse(data[:whole].decode("utf-8", errors="replace")))
        offset = start + whole
        tail = data[max(0, whole - _TAIL):whole]
        if start and known is not None and len(tail) < _TAIL:
            tail = known["tail"] + tail
        _read[key] = {
            "stat": now,
            "offset": offset,
            "tail": tail[-_TAIL:],
            "entries": found,
        }
        return list(found)


def _parse(text: str) -> list[dict]:
    entries = []
    # Split at line ends only: a line or paragraph separator in a name
    # (splitlines splits there too) cut the entry in two and lost it.
    for raw in text.split("\n"):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue  # a damaged line is skipped, the rest still read
        if isinstance(entry, dict) and "id" in entry:
            entries.append(entry)
    return entries


def entries(area: str | None = None) -> list[dict]:
    """Every entry (of one area, or all), newest first."""
    _settle()
    found: list[dict] = []
    for name in [area] if area else list(AREAS):
        found.extend(_lines(name))
    found.sort(key=lambda e: float(e.get("at") or 0), reverse=True)
    return found


def entry(entry_id: str) -> dict | None:
    for item in entries():
        if item.get("id") == entry_id:
            return item
    return None


# --- pictures ---------------------------------------------------------------


def keep_file(path: Path) -> str:
    """Keeps a copy of a file (once per content); returns its name in the
    history's files folder, "" when it can't be read."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return ""
    name = hashlib.sha1(data).hexdigest() + Path(path).suffix.lower()
    try:
        dest = files_folder() / name
        if not dest.is_file():
            dest.write_bytes(data)
    except OSError:
        return ""
    _kept_now.add(name)
    return name


def kept_file(name: str) -> Path | None:
    path = files_folder() / Path(str(name)).name
    return path if path.is_file() else None


def restore_file(name: str, dest: Path) -> bool:
    src = kept_file(name)
    if src is None:
        return False
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


# --- limits -----------------------------------------------------------------


def _prune_once() -> None:
    global _pruned
    if _pruned:
        return
    _pruned = True
    try:
        prune()
    except Exception:
        syslog.exception("History: pruning failed")


def prune() -> None:
    """Drops entries older than the day limit, then the oldest until each
    file is under its size limit; then the kept files no entry needs (nor
    one waiting to be written: those kept this session)."""
    from gremlin.modules import module_file

    days, megabytes = _limits()
    oldest = clock.now() - days * 86400
    limit = megabytes * 1024 * 1024
    needed: set[str] = set(_kept_now)
    with _write_lock:
        for area in AREAS:
            path = _file(area)
            if not path.is_file():
                continue
            # A "History cleared" entry stays whatever its age or size (S12b).
            kept = [
                e
                for e in _lines(area, fresh=True)
                if float(e.get("at") or 0) >= oldest or _is_cleared(e)
            ]
            _trim_snapshots(kept)
            lines = [json.dumps(e, ensure_ascii=False) + "\n" for e in kept]
            # The oldest go first until the file fits (sizes added once: the
            # old way re-added every line for each one dropped).
            total = sum(len(line.encode("utf-8")) for line in lines)
            dropped: set[int] = set()
            for index, item in enumerate(kept):
                if total <= limit:
                    break
                if _is_cleared(item):
                    continue
                total -= len(lines[index].encode("utf-8"))
                dropped.add(index)
            lines = [line for i, line in enumerate(lines) if i not in dropped]
            text = "".join(lines)
            if text != _text(path):
                module_file.write_text(path, text, newline="")
            for line in lines:
                needed.update(_file_refs(json.loads(line)))
        files = folder() / "files"
        if files.is_dir():
            for path in files.iterdir():
                if path.is_file() and path.name not in needed:
                    try:
                        path.unlink()
                    except OSError:
                        pass


def _trim_snapshots(kept: list[dict]) -> None:
    """Only the newest SNAPSHOTS saves of each profile keep the whole
    profile; older ones keep what they changed (their other entries)."""
    seen: dict[str, int] = {}
    for item in sorted(kept, key=lambda e: float(e.get("at") or 0), reverse=True):
        if item.get("kind") != "profile":
            continue
        name = str((item.get("subject") or {}).get("profile") or "")
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > SNAPSHOTS:
            item["before"] = item["after"] = None


def _file_refs(value: Any) -> set[str]:  # noqa: ANN401
    """Kept file names an entry points at ({"keptFile": name} anywhere)."""
    found: set[str] = set()
    if isinstance(value, dict):
        name = value.get("keptFile")
        if isinstance(name, str):
            found.add(name)
        for item in value.values():
            found |= _file_refs(item)
    elif isinstance(value, list):
        for item in value:
            found |= _file_refs(item)
    return found


# --- Clear History (08 S12b, D-08-CLEAR-HISTORY) -------------------------------

# History's own kept copies: named by their content (keep_file()).
_KEPT_NAME = re.compile(r"^[0-9a-f]{40}(\.[0-9A-Za-z]{1,10})?$")
# Told after a clearing (the Device Library's Undo steps empty).
_cleared_listeners: list[Callable[[], None]] = []
REFUSED_RUNNING = "Stop the running profile before clearing History."


def _is_cleared(entry: dict) -> bool:
    return entry.get("kind") == CLEARED_KIND


def add_cleared_listener(listener: Callable[[], None]) -> None:
    """listener() runs after every clearing of History."""
    if listener not in _cleared_listeners:
        _cleared_listeners.append(listener)


def remove_cleared_listener(listener: Callable[[], None]) -> None:
    if listener in _cleared_listeners:
        _cleared_listeners.remove(listener)


def _kept_files() -> list[Path]:
    """History's own kept copies; nothing else in its files folder."""
    files = folder() / "files"
    if not files.is_dir():
        return []
    return [p for p in files.iterdir() if p.is_file() and _KEPT_NAME.match(p.name)]


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def summary() -> dict:
    """What Clear History would delete: {"entries", "bytes"} (every entry
    but the "History cleared" ones, and the kept copies)."""
    _settle()
    count = 0
    size = 0
    for area in AREAS:
        path = _file(area)
        if not path.is_file():
            continue
        size += _size(path)
        count += sum(1 for e in _lines(area) if not _is_cleared(e))
    size += sum(_size(p) for p in _kept_files())
    return {"entries": count, "bytes": size}


def _profile_running() -> bool:
    try:
        from gremlin import run_scope, shared_state

        return bool(run_scope.running() or shared_state.runtime_active())
    except Exception:  # noqa: BLE001 - not known: not running
        return False


def clear_all() -> dict:
    """Deletes every History entry and kept copy (only History's own files:
    the area files and the kept copies), refused while a profile runs. Then
    records one "History cleared" entry. {"ok", "error", "entries", "bytes"}:
    what was deleted."""
    if _profile_running():
        return {"ok": False, "error": REFUSED_RUNNING, "entries": 0, "bytes": 0}
    from gremlin.modules import module_file

    found = summary()
    errors: list[str] = []
    with _handle_lock, _write_lock:
        for area in AREAS:
            path = _file(area)
            if not path.is_file():
                continue
            # The earlier "History cleared" entries stay (S12b).
            kept = [e for e in _lines(area, fresh=True) if _is_cleared(e)]
            try:
                if kept:
                    text = "".join(
                        json.dumps(e, ensure_ascii=False) + "\n" for e in kept
                    )
                    module_file.write_text(path, text, newline="")
                else:
                    path.unlink()
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")
        for path in _kept_files():
            try:
                path.unlink()
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")
        _kept_now.clear()
    with _read_lock:
        _read.clear()
    if errors:
        syslog.warning(f"History: not all of it could be cleared: {errors}")
    _append(
        _make(
            "history",
            "History cleared",
            {"entries": found["entries"], "bytes": found["bytes"]},
            None,
            None,
            CLEARED_KIND,
        )
    )
    for listener in list(_cleared_listeners):
        try:
            listener()
        except Exception:  # noqa: BLE001 - one listener never stops the rest
            syslog.exception("History: a clear listener failed")
    if errors:
        return {
            "ok": False,
            "error": "Some of History couldn't be deleted: " + "; ".join(errors),
            "entries": found["entries"],
            "bytes": found["bytes"],
        }
    return {"ok": True, "error": "", **found}
