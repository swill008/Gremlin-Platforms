# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Live Log Reader: one file log of reads and saves (Config tab), the
diagnostic log files and the Live log feed (Debug tab), and the Input
Monitor (Input Monitor tab)."""

from __future__ import annotations

import html
import os
import re
import threading
import time
from pathlib import Path

from PySide6 import QtCore, QtGui, QtQuick

import gremlin.ui.type_aliases as ta
from gremlin import input_monitor, log_feed

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

_LOCK = threading.Lock()
# Activity lines waiting to be written: they go to logs.txt in one append
# about a second after the last one (and always on quit), not one file
# open/append/close per read or save.
_buffer: list[str] = []


def log_path() -> Path:
    from gremlin.util import logs_dir

    return logs_dir() / "logs.txt"


def start() -> None:
    """Clear the log for this run. Lines already waiting are from this run
    (made while the program was starting) and are kept."""
    path = log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    except OSError:
        return
    trace("READ", "Live Log", "start", path, "cleared")


def trace(action: str, window: str, function: str, path: object, result: str = "ok") -> None:
    """Append one read or save. A failure here must not change the file operation."""
    try:
        shown = os.path.normcase(os.path.abspath(str(path or "")))
        line = f"{action} | {window} | {function} | {shown} | {result}\n"
        with _LOCK:
            _buffer.append(line)
        from gremlin import deferred_write

        # Held until the application runs: writing needs the log folder,
        # which reads the settings, which may be what is being traced.
        deferred_write.schedule("activity-log", _write_buffer, hold=True)
    except Exception:
        return


def _write_buffer() -> None:
    """Append the waiting activity lines to logs.txt in one write."""
    with _LOCK:
        lines = list(_buffer)
        _buffer.clear()
    if not lines:
        return
    try:
        dest = log_path()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("a", encoding="utf-8") as handle:
            handle.write("".join(lines))
    except Exception:
        return


def flush() -> None:
    """Write the waiting activity lines now (the Config tab shows them)."""
    from gremlin import deferred_write

    deferred_write.flush("activity-log")


@ta.QmlElement
class LiveLog(QtCore.QObject):
    textChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._text = ""
        # (size, mtime) of logs.txt as last read; unchanged means no re-read.
        self._stamp: tuple[int, int] | None = None
        # logs.txt, found once: the refresh runs every 400 ms on the main
        # thread and the logs folder stays until the next start (01 S125).
        self._log_path: Path | None = None

    def _path(self) -> Path:
        if self._log_path is None:
            self._log_path = log_path()
        return self._log_path

    @QtCore.Property(str, notify=textChanged)
    def text(self) -> str:
        return self._text

    @QtCore.Property(str, constant=True)
    def path(self) -> str:
        return str(self._path())

    @QtCore.Slot()
    def refresh(self) -> None:
        flush()  # lines still waiting in memory are shown too
        path = self._path()
        try:
            stat = path.stat()
            stamp: tuple[int, int] | None = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            stamp = None
        if stamp == self._stamp:
            return  # nothing new: no re-read
        self._stamp = stamp
        try:
            data = path.read_text(encoding="utf-8") if stamp else ""
        except OSError:
            data = ""
        if data == self._text:
            return
        self._text = data
        self.textChanged.emit()

    @QtCore.Slot()
    def clear(self) -> None:
        dest = self._path()
        try:
            with _LOCK:
                _buffer.clear()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("", encoding="utf-8")
        except OSError:
            return
        self._text = ""
        self._stamp = None
        self.textChanged.emit()

    @QtCore.Slot()
    def copyAll(self) -> None:
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._text)


# Debug tab: the diagnostic log files (Options → General → Diagnostics).
DEBUG_FILES = {
    "system": "system.log",
    "user": "user.log",
    "event": "event.log",
    # Qt's own messages (gremlin.qt_log); not in Live, which follows the
    # program's logging.
    "qt": "qt.log",
}
# Shown levels, lowest first; "All" shows everything.
DEBUG_LEVELS = ("All", "Info", "Warning", "Error")
_RANKS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 3}
_MIN_RANK = {"All": 0, "Info": 1, "Warning": 2, "Error": 3}
# Only the end of a big file is read; older lines are in the file itself.
_TAIL_BYTES = 512 * 1024
_ENTRY = re.compile(
    r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\s+|,)"
    r"(?:(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b)?"
)


def debug_entries(text: str) -> list[tuple[int, str]]:
    """(rank, text) for each entry. A line without a time stamp (a traceback)
    belongs to the entry above it; an entry without a level (user scripts)
    counts as Info."""
    entries: list[tuple[int, str]] = []
    for line in text.splitlines():
        match = _ENTRY.match(line)
        if match or not entries:
            level = match.group(1) if match else None
            entries.append((_RANKS.get(level or "INFO", 1), line))
        else:
            rank, body = entries[-1]
            entries[-1] = (rank, body + "\n" + line)
    return entries


def filter_entries(
    entries: list[tuple[int, str]], level: str, find: str
) -> list[tuple[int, str]]:
    least = _MIN_RANK.get(level, 0)
    needle = find.strip().lower()
    return [
        (rank, body) for rank, body in entries
        if rank >= least and (not needle or needle in body.lower())
    ]


# The Live Log Reader's last choices (tab, Log, Show), kept between
# sessions; Find starts empty, Live off.
_CHOICES = {"tab": "live-log-tab", "file": "live-log-file", "level": "live-log-level"}


def _choice_key(name: str) -> tuple[str, str, str]:
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    key = _CHOICES[name]
    # Registered when first used; registering again changes nothing.
    Configuration().register(
        "global", "internal", key, PropertyType.String, "",
        "Live Log Reader: the last " + name + " chosen.", {}, False,
    )
    return ("global", "internal", key)


_START_EMPTY = ("global", "internal", "live-start-empty")


def _start_empty_key() -> tuple[str, str, str]:
    """The one definition of Live's Start empty setting (registering again
    changes nothing)."""
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    Configuration().register(
        *_START_EMPTY, PropertyType.Bool, False,
        "Live Log Reader: Live starts with an empty view.", {}, False,
    )
    return _START_EMPTY


def register_options() -> None:
    """At start, before unused settings are purged: every Live Log Reader
    setting (the choices kept and Start empty)."""
    for name in _CHOICES:
        _choice_key(name)
    _start_empty_key()


def _load_choice(name: str, default: str) -> str:
    from gremlin.config import Configuration

    value = Configuration().value(*_choice_key(name))
    return str(value) if value else default


def _save_choice(name: str, value: str) -> None:
    from gremlin.config import Configuration

    Configuration().set(*_choice_key(name), str(value))


def _profile_running() -> bool:
    from gremlin.event_handler import EventListener

    # Never create the listener here (it hooks the keyboard); read it if it exists.
    listener = EventListener.instance
    return bool(listener is not None and listener.gremlin_active)


# The Log dropdown's file keys and the feed's source names.
SOURCE_OF = {"system": "System", "user": "Scripts", "event": "Events"}
# All logs, outside Live: every file, merged by time, each entry tagged
# with the log it came from.
MERGED_NAMES = {"system": "System", "user": "Scripts", "event": "Events", "qt": "Qt"}


def tagged(entries: list[tuple[int, str]], name: str) -> list[tuple[int, str]]:
    """Entries with their log's name after the time stamp ("... [Qt] ...")."""
    out = []
    for rank, text in entries:
        match = re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", text)
        if match:
            end = match.end()
            text = text[:end] + f" [{name}]" + text[end:]
        else:
            text = f"[{name}] " + text
        out.append((rank, text))
    return out


def _tag_source(text: str) -> str:
    """The log an All logs entry came from, by its tag ("System" if none)."""
    match = re.match(r"^(?:\d{4}-\d\d-\d\d \d\d:\d\d:\d\d )?\[(\w+)\]", text)
    return match.group(1) if match else "System"


def merged_entries(files: dict[str, str]) -> list[tuple[int, str]]:
    """Every file's entries (name -> its text), tagged, in time order; the
    same second keeps each file's own order."""
    rows: list[tuple[str, int, int, str]] = []
    for name, text in files.items():
        for index, (rank, body) in enumerate(tagged(debug_entries(text), name)):
            rows.append((body[:19] if body[:4].isdigit() else "", index, rank, body))
    rows.sort(key=lambda row: (row[0], row[1]))
    return [(rank, body) for _stamp, _index, rank, body in rows]
# A session divider ("── Live started … ──"): always shown, in its own color.
DIVIDER = 99
# Most lines a Live session view keeps; older ones drop off the top.
MAX_SESSION = 20000


def _html(rows: list[tuple[int, str]], colors: dict[str, str]) -> str:
    """Rows as rich text: warnings and errors in color, dividers and dimmed
    rows in theirs. Each row is its own paragraph, so rows can be added at
    the end and dropped from the top without laying the whole view out
    again."""
    lines = []
    for rank, body in rows:
        text = html.escape(body).replace("\n", "<br>")
        color = (
            colors["divider"] if rank == DIVIDER
            else colors["error"] if rank >= 3
            else colors["warn"] if rank == 2
            else colors["muted"] if rank < 0
            else ""
        )
        if color:
            text = f'<span style="color:{color}">{text}</span>'
        # white-space: pre keeps the view's own font (a <pre> would not).
        lines.append(f'<p style="margin:0;white-space:pre">{text}</p>')
    return "".join(lines)


@ta.QmlElement
class DebugLog(QtCore.QObject):
    """The Live Log Reader's Debug tab: one diagnostic log file, filtered by
    level and text; or, with Live on, a session view that keeps what was
    shown and adds every line the program logs as it happens
    (gremlin.log_feed)."""

    changed = QtCore.Signal()
    # Live added rows straight to the view (no redraw): the view keeps to
    # the end if it was there.
    appended = QtCore.Signal()
    countsChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        # The view's document (attachView): Live adds rows to it directly.
        self._view: QtQuick.QQuickTextDocument | None = None
        # The view shows self._shown (set by each full redraw).
        self._drawn = False
        self._file = "system"
        self._level = "All"
        self._find = ""
        self._raw: str | None = None
        self._shown: list[tuple[int, str]] = []
        self._total = 0
        self._warn = "#F0A30A"
        self._error = "#F87171"
        self._divider = "#F87171"
        self._muted = "#9CA3AF"
        self._on = True
        self._running = False
        # Load Whole File: read all of a big file, not just its end.
        self._whole = False
        self._cut = False
        # (size, mtime) of the file as last read; unchanged means no re-read.
        self._stamp: tuple[int, int] | None = None
        # Live: (rank, source, text) rows of this session, or None for the
        # file view. A session stays after Live stops until Show Log File.
        self._live = False
        self._session: list[tuple[int, str, str]] | None = None
        self._seq = 0
        # All logs (file view): the merged entries, or None.
        self._merged: list[tuple[int, str]] | None = None
        # All logs: each file's (stamp, text, cut) as last read, so only a
        # file that changed is read again (01 K19).
        self._texts: dict[str, tuple[tuple[int, int] | None, str, bool]] = {}
        # The logs folder, found once (see LiveLog._path).
        self._logs: Path | None = None

    def _path(self) -> Path:
        if self._logs is None:
            from gremlin.util import logs_dir

            self._logs = logs_dir()
        if self._file == "all":
            return self._logs
        return self._logs / DEBUG_FILES.get(self._file, "system.log")

    def _set(self, name: str, value: str) -> None:
        if getattr(self, name) != value:
            setattr(self, name, value)
            self._apply()

    def _session_rows(
        self, entries: list[tuple[int, str, str]]
    ) -> list[tuple[int, str]]:
        """The session entries the filters let through."""
        source = SOURCE_OF.get(self._file, "")
        least = _MIN_RANK.get(self._level, 0)
        needle = self._find.strip().lower()
        return [
            (rank, text) for rank, src, text in entries
            if rank == DIVIDER or (
                (not source or src == source)
                and rank >= least
                and (not needle or needle in text.lower())
            )
        ]

    def _apply(self) -> None:
        if self._session is not None:
            self._total = sum(1 for rank, _s, _t in self._session if rank != DIVIDER)
            self._shown = self._session_rows(self._session)[-MAX_SESSION:]
        else:
            if self._file == "all":
                entries = self._merged or []
            else:
                entries = debug_entries(self._raw or "")
            self._total = len(entries)
            self._shown = filter_entries(entries, self._level, self._find)
        self._drawn = True
        self.changed.emit()
        self.countsChanged.emit()

    @QtCore.Slot(QtQuick.QQuickTextDocument)
    def attachView(self, document: QtQuick.QQuickTextDocument) -> None:
        """The Debug view's document, so Live can add rows to it."""
        self._view = document

    def _colors(self) -> dict[str, str]:
        return {
            "warn": self._warn, "error": self._error,
            "divider": self._divider, "muted": self._muted,
        }

    def _extend(self, new: list[tuple[int, str, str]]) -> None:
        """Live's new lines: added at the end of the view and the oldest
        dropped from the top, instead of drawing the whole view again (which
        took about a third of a second with 20,000 rows and lost a
        selection)."""
        rows = self._session_rows(new)
        self._total = sum(1 for rank, _s, _t in self._session or [] if rank != DIVIDER)
        had = len(self._shown)
        self._shown.extend(rows)
        cut = max(0, len(self._shown) - MAX_SESSION)
        if cut:
            del self._shown[:cut]
        doc = self._view.textDocument() if self._view is not None else None
        if doc is None or not self._drawn:
            self._apply()
            return
        if not rows and not cut:
            self.countsChanged.emit()
            return
        if rows:
            cursor = QtGui.QTextCursor(doc)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            if had:
                cursor.insertBlock()
            cursor.insertHtml(_html(rows, self._colors()))
        if cut:
            cursor = QtGui.QTextCursor(doc)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.NextBlock,
                QtGui.QTextCursor.MoveMode.KeepAnchor,
                cut,
            )
            cursor.removeSelectedText()
        self.appended.emit()
        self.countsChanged.emit()

    def _set_file(self, value: str) -> None:
        if value == self._file:
            return
        self._file = value
        if not self._live:
            _save_choice("file", value)
        if self._session is not None:
            if self._live:
                self._apply()  # a session is only filtered by its source
                return
            # Live stopped: picking a log leaves the session for that log.
            self._session = None
        self._whole = False
        self._reload()
        self._apply()

    def _divide(self, what: str) -> None:
        if self._session is not None:
            stamp = time.strftime("%H:%M:%S")
            self._session.append((DIVIDER, "", f"── Live {what} {stamp} ──"))

    def _set_live(self, on: bool) -> None:
        on = bool(on)
        if on == self._live:
            return
        self._live = on
        if on:
            empty = self._get_start_empty()
            if self._session is None or empty:
                # Keep what the file view showed (unless Start empty): one
                # file, or All logs (each entry's log from its tag).
                if empty:
                    self._session = []
                elif self._file == "all":
                    self._session = [
                        (rank, _tag_source(text), text)
                        for rank, text in (self._merged or [])
                    ]
                else:
                    source = SOURCE_OF.get(self._file, "System")
                    self._session = [
                        (rank, source, text)
                        for rank, text in debug_entries(self._raw or "")
                    ]
            self._seq = log_feed.last_seq()
            self._file = "all"
            self._divide("started")
            log_feed.start()
        else:
            log_feed.stop()
            self._take_new()
            self._divide("stopped")
        self._apply()

    file = QtCore.Property(
        str, lambda self: self._file, _set_file, notify=changed,
    )
    def _set_level(self, value: str) -> None:
        if value in DEBUG_LEVELS:
            _save_choice("level", value)
        self._set("_level", value)

    level = QtCore.Property(str, lambda self: self._level, _set_level, notify=changed)

    @QtCore.Slot(result="QVariant")
    def restoreChoices(self) -> dict:
        """The window's last tab, Log and Show choices (the window asks when
        it opens; a choice not known any more is left as it is). Returns
        {"tab": index}."""
        file = _load_choice("file", "")
        if (file in DEBUG_FILES or file == "all") and self._session is None:
            self._file = file
            self._whole = False
            self._reload()
        level = _load_choice("level", "")
        if level in DEBUG_LEVELS:
            self._level = level
        self._apply()
        try:
            tab = int(_load_choice("tab", "0"))
        except ValueError:
            tab = 0
        return {"tab": tab if 0 <= tab <= 3 else 0}

    @QtCore.Slot(int)
    def saveTab(self, index: int) -> None:
        if 0 <= index <= 3:
            _save_choice("tab", str(index))
    find = QtCore.Property(
        str, lambda self: self._find, lambda self, v: self._set("_find", v),
        notify=changed,
    )
    warningColor = QtCore.Property(
        str, lambda self: self._warn, lambda self, v: self._set("_warn", v),
        notify=changed,
    )
    errorColor = QtCore.Property(
        str, lambda self: self._error, lambda self, v: self._set("_error", v),
        notify=changed,
    )
    dividerColor = QtCore.Property(
        str, lambda self: self._divider, lambda self, v: self._set("_divider", v),
        notify=changed,
    )
    live = QtCore.Property(bool, lambda self: self._live, _set_live, notify=changed)

    def _get_start_empty(self) -> bool:
        from gremlin.config import Configuration

        cfg = Configuration()
        key = ("global", "internal", "live-start-empty")
        return bool(cfg.value(*key)) if cfg.exists(*key) else False

    def _set_start_empty(self, value: bool) -> None:
        from gremlin.config import Configuration

        Configuration().set(*_start_empty_key(), bool(value))
        self.changed.emit()

    startEmpty = QtCore.Property(
        bool, _get_start_empty, _set_start_empty, notify=changed,
    )

    @QtCore.Property(bool, notify=changed)
    def session(self) -> bool:
        """A Live session is shown (running, or stopped and kept)."""
        return self._session is not None

    @QtCore.Property(str, notify=changed)
    def path(self) -> str:
        return str(self._path())

    @QtCore.Property(int, notify=countsChanged)
    def shownCount(self) -> int:
        return sum(1 for rank, _t in self._shown if rank != DIVIDER)

    @QtCore.Property(int, notify=countsChanged)
    def totalCount(self) -> int:
        return self._total

    @QtCore.Property(bool, notify=changed)
    def exists(self) -> bool:
        if self._file == "all":
            return any((self._path() / DEBUG_FILES[k]).is_file() for k in MERGED_NAMES)
        return self._path().is_file()

    @QtCore.Property(bool, notify=changed)
    def truncated(self) -> bool:
        """Only the end of a big file is shown (Load Whole File shows all)."""
        return self._cut

    @QtCore.Property(int, constant=True)
    def tailKilobytes(self) -> int:
        return _TAIL_BYTES // 1024

    @QtCore.Property(bool, notify=changed)
    def loggingOn(self) -> bool:
        """Diagnostic logs are not Off (read again on every refresh)."""
        return self._on

    @QtCore.Property(bool, notify=changed)
    def running(self) -> bool:
        """A profile is running."""
        return self._running

    @staticmethod
    def _logging_on() -> bool:
        from gremlin.config import Configuration
        from gremlin.ui.log_option import (
            DEFAULT_LEVEL,
            LOG_GROUP,
            LOG_NAME,
            LOG_SECTION,
            normalize_level,
        )

        cfg = Configuration()
        value = (
            cfg.value(LOG_SECTION, LOG_GROUP, LOG_NAME)
            if cfg.exists(LOG_SECTION, LOG_GROUP, LOG_NAME) else DEFAULT_LEVEL
        )
        return normalize_level(value) != "Off"

    @QtCore.Property(str, notify=changed)
    def html(self) -> str:
        """The shown entries; warnings, errors and dividers in color."""
        return _html(self._shown, self._colors())

    def _take_new(self) -> list[tuple[int, str, str]]:
        """Add the feed's new lines to the session and return them."""
        if self._session is None:
            return []
        new = log_feed.entries_after(self._seq)
        if not new:
            return []
        self._seq = new[-1].seq
        added = [(e.rank, e.source, e.text) for e in new]
        self._session.extend(added)
        if len(self._session) > MAX_SESSION:
            del self._session[: len(self._session) - MAX_SESSION]
        return added

    @QtCore.Slot()
    def refresh(self) -> None:
        on = self._logging_on()
        running = _profile_running()
        if (on, running) != (self._on, self._running):
            self._on, self._running = on, running
            self.changed.emit()
        if self._session is not None:
            if self._live:
                new = self._take_new()
                if new:
                    self._extend(new)
            return
        if self._file == "all":
            self._refresh_all()
            return
        path = self._path()
        stamp = self._stamp_of(path)
        if stamp == self._stamp and self._raw is not None:
            return
        self._stamp = stamp
        data, cut = self._read(path, stamp)
        if data == self._raw and cut == self._cut:
            return
        self._raw = data
        self._cut = cut
        self._apply()

    @staticmethod
    def _stamp_of(path: Path) -> tuple[int, int] | None:
        try:
            stat = path.stat()
        except OSError:
            return None
        return (stat.st_size, stat.st_mtime_ns)

    def _read(self, path: Path, stamp: tuple[int, int] | None) -> tuple[str, bool]:
        """The file's text (its end only when big, unless Load Whole File),
        and whether it was cut."""
        if stamp is None:
            return "", False
        cut = False
        try:
            with path.open("rb") as handle:
                if stamp[0] > _TAIL_BYTES and not self._whole:
                    handle.seek(stamp[0] - _TAIL_BYTES)
                    handle.readline()  # drop the cut-off line
                    cut = True
                return handle.read().decode("utf-8", errors="replace"), cut
        except OSError:
            return "", False

    def _refresh_all(self) -> None:
        """All logs: every file read again when one changed, merged."""
        folder = self._path()
        paths = {MERGED_NAMES[k]: folder / DEBUG_FILES[k] for k in MERGED_NAMES}
        stamps = tuple(self._stamp_of(p) for p in paths.values())
        if stamps == self._stamp and self._merged is not None:
            return
        self._stamp = stamps  # type: ignore[assignment]
        texts = {}
        cut = False
        for (name, path), stamp in zip(paths.items(), stamps):
            kept = self._texts.get(name)
            if kept is not None and kept[0] == stamp:
                text, was_cut = kept[1], kept[2]
            else:
                text, was_cut = self._read(path, stamp)
                self._texts[name] = (stamp, text, was_cut)
            texts[name] = text
            cut = cut or was_cut
        self._merged = merged_entries(texts)
        self._cut = cut
        self._apply()

    def _reload(self) -> None:
        self._raw = None
        self._merged = None
        self._stamp = None
        self._texts = {}
        self.refresh()

    @QtCore.Slot()
    def loadWhole(self) -> None:
        """Read all of the file this time (until another log is chosen)."""
        self._whole = True
        self._reload()

    @QtCore.Slot()
    def showFile(self) -> None:
        """Leave a stopped Live session and show the log file again."""
        if self._live:
            return
        self._session = None
        if self._file not in DEBUG_FILES and self._file != "all":
            self._file = "system"
        self._reload()
        self._apply()

    @QtCore.Slot()
    def clearView(self) -> None:
        """Live session: empty the view (never a file). Live keeps going;
        a stopped session goes back to the log file."""
        log_feed.clear()
        if self._live:
            self._session = []
            self._seq = log_feed.last_seq()
            self._apply()
        else:
            self.showFile()

    @QtCore.Slot()
    def clear(self) -> None:
        """Empty the shown file. The program's own log handler has it open,
        so it is emptied through that handler; otherwise directly."""
        import logging

        if self._session is not None:
            self.clearView()
            return
        path = self._path()
        done = False
        for handler in logging.getLogger(self._file).handlers:
            name = getattr(handler, "baseFilename", "")
            stream = getattr(handler, "stream", None)
            if stream is None or os.path.normcase(name) != os.path.normcase(str(path)):
                continue
            handler.acquire()
            try:
                stream.flush()
                stream.seek(0)
                stream.truncate()
                done = True
            except (OSError, ValueError):
                pass
            finally:
                handler.release()
        if not done:
            try:
                if path.is_file():
                    path.write_bytes(b"")
            except OSError:
                pass
        self._whole = False
        self._reload()

    def _shown_text(self) -> str:
        return "\n".join(body for _rank, body in self._shown)

    @QtCore.Slot()
    def copyShown(self) -> None:
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._shown_text())

    @QtCore.Slot(str, result=bool)
    def saveTo(self, url: str) -> bool:
        """Save Feed…: write what is shown to a text file."""
        path = QtCore.QUrl(url).toLocalFile() or url
        try:
            Path(path).write_text(self._shown_text() + "\n", encoding="utf-8")
        except OSError:
            return False
        return True

    @QtCore.Slot()
    def openFolder(self) -> None:
        folder = self._path().parent
        folder.mkdir(parents=True, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))


@ta.QmlElement
class InputMonitor(QtCore.QObject):
    """The Live Log Reader's Input Monitor tab: each input the running
    profile handles and the actions it ran (gremlin.input_monitor)."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._find = ""
        self._unbound = True
        self._muted = "#9CA3AF"
        self._rows: list[tuple[int, str]] = []
        self._shown: list[tuple[int, str]] = []
        self._version = -1
        self._running = False

    def _set(self, name: str, value: object) -> None:
        if getattr(self, name) != value:
            setattr(self, name, value)
            self._apply()

    def _apply(self) -> None:
        needle = self._find.strip().lower()
        self._shown = [
            (rank, text) for rank, text in self._rows
            if (self._unbound or rank >= 0)
            and (not needle or needle in text.lower())
        ]
        self.changed.emit()

    def _set_on(self, on: bool) -> None:
        if bool(on) != input_monitor.enabled():
            input_monitor.set_enabled(bool(on))
            self._version = -1
            self.refresh()
            self.changed.emit()

    monitoring = QtCore.Property(
        bool, lambda self: input_monitor.enabled(), _set_on, notify=changed,
    )
    find = QtCore.Property(
        str, lambda self: self._find, lambda self, v: self._set("_find", v),
        notify=changed,
    )
    showUnbound = QtCore.Property(
        bool, lambda self: self._unbound,
        lambda self, v: self._set("_unbound", bool(v)), notify=changed,
    )
    mutedColor = QtCore.Property(
        str, lambda self: self._muted, lambda self, v: self._set("_muted", v),
        notify=changed,
    )

    @QtCore.Property(bool, notify=changed)
    def running(self) -> bool:
        """A profile is running (the monitor only sees inputs then)."""
        return self._running

    @QtCore.Property(int, notify=changed)
    def shownCount(self) -> int:
        return len(self._shown)

    @QtCore.Property(int, notify=changed)
    def totalCount(self) -> int:
        return len(self._rows)

    @QtCore.Property(str, notify=changed)
    def html(self) -> str:
        return _html(self._shown, {
            "warn": "", "error": "", "divider": "", "muted": self._muted,
        })

    @QtCore.Slot()
    def refresh(self) -> None:
        running = _profile_running()
        if running != self._running:
            self._running = running
            self.changed.emit()
        current = input_monitor.version()
        if current == self._version:
            return
        rows = input_monitor.entries()
        self._version = input_monitor.version()
        self._rows = [
            (1 if kind == input_monitor.RAN else -1, text) for kind, text in rows
        ]
        self._apply()

    @QtCore.Slot()
    def clear(self) -> None:
        input_monitor.clear()
        self._version = -1
        self.refresh()

    @QtCore.Slot()
    def copyShown(self) -> None:
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText("\n".join(text for _rank, text in self._shown))
