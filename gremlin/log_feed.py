# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Live log feed (Live Log Reader → Debug → Live): while it runs, every line
the program logs (System, Scripts, Events) is caught in memory at full
detail, as it happens.

The log files are not changed by it: each file handler keeps the level set in
Diagnostic logs, and only the loggers themselves are opened up to Debug
while the feed runs (log_option.apply_log_level calls reassert() so a level
change made meanwhile keeps the feed going). Stopping puts the loggers back
the way Diagnostic logs says."""

from __future__ import annotations

import collections
import logging
import threading
import time
from collections.abc import Callable

# Logger name -> the name shown in the feed (and the Log dropdown).
SOURCES = {"system": "System", "user": "Scripts", "event": "Events"}
MAX_ENTRIES = 10000

_LEVEL_RANK = {
    logging.DEBUG: 0, logging.INFO: 1, logging.WARNING: 2,
    logging.ERROR: 3, logging.CRITICAL: 3,
}


class Entry:
    """One caught line: when, from which log, how serious, and the text."""

    __slots__ = ("rank", "seq", "source", "text")

    def __init__(self, rank: int, source: str, text: str) -> None:
        self.rank = rank
        self.source = source
        self.text = text
        # Numbered in the order caught, so a reader can take only new ones.
        self.seq = 0


class _FeedHandler(logging.Handler):
    # apply_log_level leaves a handler marked like this at Debug.
    live_feed = True

    def __init__(self, source: str) -> None:
        super().__init__(logging.DEBUG)
        self._source = source

    def emit(self, record: logging.LogRecord) -> None:
        try:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
            text = (
                f"{stamp}  [{self._source}]  {record.levelname:<8} "
                + record.getMessage()
            )
            if record.exc_info:
                text += "\n" + logging.Formatter().formatException(record.exc_info)
            rank = _LEVEL_RANK.get(record.levelno, 1)
        except Exception:  # a feed problem must never break logging
            return
        _add(Entry(rank, self._source, text))


_LOCK = threading.Lock()
_entries: collections.deque[Entry] = collections.deque(maxlen=MAX_ENTRIES)
_version = 0
_seq = 0
_handlers: dict[str, _FeedHandler] = {}
_listeners: list[Callable[[], None]] = []


def _add(entry: Entry) -> None:
    global _version, _seq
    with _LOCK:
        _seq += 1
        entry.seq = _seq
        _entries.append(entry)
        _version += 1


def last_seq() -> int:
    """The number of the newest line caught so far."""
    with _LOCK:
        return _seq


def entries_after(seq: int) -> list[Entry]:
    """The caught lines newer than seq, oldest first."""
    with _LOCK:
        return [entry for entry in _entries if entry.seq > seq]


def active() -> bool:
    return bool(_handlers)


def start() -> None:
    """Catch every line from now on (the caught lines so far are kept)."""
    if _handlers:
        return
    for name, source in SOURCES.items():
        handler = _FeedHandler(source)
        logging.getLogger(name).addHandler(handler)
        _handlers[name] = handler
    reassert()
    _changed()


def stop() -> None:
    """Stop catching; the loggers go back to the Diagnostic logs level."""
    if not _handlers:
        return
    for name, handler in _handlers.items():
        logging.getLogger(name).removeHandler(handler)
    _handlers.clear()
    from gremlin.ui.log_option import apply_log_level

    apply_log_level()
    _changed()


def reassert() -> None:
    """While the feed runs, every logger passes everything on; the file
    handlers still drop what is below their own (Diagnostic logs) level."""
    if not _handlers:
        return
    for name in SOURCES:
        logger = logging.getLogger(name)
        logger.disabled = False
        logger.setLevel(logging.DEBUG)


def clear() -> None:
    global _version
    with _LOCK:
        _entries.clear()
        _version += 1


def version() -> int:
    with _LOCK:
        return _version


def entries() -> list[Entry]:
    with _LOCK:
        return list(_entries)


def add_listener(callback: Callable[[], None]) -> None:
    """Called when the feed starts or stops (the red debug frame)."""
    _listeners.append(callback)


def _changed() -> None:
    for callback in list(_listeners):
        try:
            callback()
        except Exception:
            pass
