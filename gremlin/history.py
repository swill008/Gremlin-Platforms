# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The program's history: every saved change, kept in its own files.

One file per area in the history folder (profile.jsonl, modules.jsonl,
button-map.jsonl, settings.jsonl): one JSON line per entry, only ever
appended, so two copies of the program running at once can't break it.
Pictures an entry needs are kept once each in history/files, named by
their content. An entry holds what changed before and after, so it can be
looked at and put back (Restore).

record() only queues the entry. A writer thread (gremlin.threads) appends
what is queued and ends by itself when nothing more comes; flush() writes
what is left (at quit). Entries older than the Options limit, or past a
file's size limit, go when the first entry of a session is written.
"""

from __future__ import annotations

import hashlib
import json
import logging
import queue
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any

from gremlin import clock, threads

AREAS = {
    "profile": "Profile",
    "modules": "Module files",
    "button-map": "Button Map",
    "settings": "Settings",
}
# Options › History: how long entries are kept and how big a file may grow.
KEEP_DAYS = 90
MAX_MEGABYTES = 20
# How long the writer waits for more before it ends.
_IDLE = 1.0

_queue: queue.Queue[dict] = queue.Queue()
_write_lock = threading.Lock()
_start_lock = threading.Lock()
_writer: threading.Thread | None = None
_stop = threading.Event()
_pruned = False

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
    entry = {
        "id": uuid.uuid4().hex,
        "at": clock.now(),
        "area": area if area in AREAS else "settings",
        "kind": kind,
        "title": title,
        "subject": subject,
        "before": before,
        "after": after,
    }
    _queue.put(entry)
    _wake_writer()
    return entry["id"]


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
        _append(entry)


def flush() -> None:
    """Writes every queued entry now, on this thread (at quit, in tests)."""
    while True:
        try:
            entry = _queue.get_nowait()
        except queue.Empty:
            return
        _append(entry)


def _file(area: str) -> Path:
    return folder() / f"{area}.jsonl"


def _append(entry: dict) -> None:
    from gremlin.ui.live_debug import trace

    path = _file(entry["area"])
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with _write_lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # One write per entry: a second copy of the program appending at
            # the same time can't split a line.
            with open(path, "a", encoding="utf-8", newline="") as out:
                out.write(line)
        except OSError as exc:
            syslog.warning(f"History: could not write {path}: {exc}")
            trace("SAVE", "History", "record", path, "error")
            return
    trace("SAVE", "History", "record", path, "ok")


def _lines(area: str) -> list[dict]:
    path = _file(area)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    entries = []
    for raw in text.splitlines():
        try:
            entry = json.loads(raw)
        except ValueError:
            continue  # a damaged line is skipped, the rest still read
        if isinstance(entry, dict) and "id" in entry:
            entries.append(entry)
    return entries


def entries(area: str | None = None) -> list[dict]:
    """Every entry (of one area, or all), newest first."""
    flush()
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
    dest = files_folder() / name
    if not dest.is_file():
        try:
            dest.write_bytes(data)
        except OSError:
            return ""
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
    file is under its size limit; then the kept files no entry needs."""
    from gremlin.modules import module_file

    days, megabytes = _limits()
    oldest = clock.now() - days * 86400
    limit = megabytes * 1024 * 1024
    needed: set[str] = set()
    with _write_lock:
        for area in AREAS:
            path = _file(area)
            if not path.is_file():
                continue
            kept = [e for e in _lines(area) if float(e.get("at") or 0) >= oldest]
            lines = [json.dumps(e, ensure_ascii=False) + "\n" for e in kept]
            while lines and sum(len(line.encode("utf-8")) for line in lines) > limit:
                lines.pop(0)
            text = "".join(lines)
            if text != path.read_text(encoding="utf-8"):
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
