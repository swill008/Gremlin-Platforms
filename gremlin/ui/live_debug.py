# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Live Log Reader: one file log of reads and saves (Config tab), and
the diagnostic log files (Debug tab)."""

from __future__ import annotations

import html
import os
import re
import threading
from pathlib import Path

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin import live_capture

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

_LOCK = threading.Lock()


def log_path() -> Path:
    from gremlin.util import logs_dir

    return logs_dir() / "logs.txt"


def start() -> None:
    """Clear the log for this run."""
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
        dest = log_path()
        with _LOCK:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("a", encoding="utf-8") as handle:
                handle.write(line)
    except Exception:
        return


@ta.QmlElement
class LiveLog(QtCore.QObject):
    textChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._text = ""

    @QtCore.Property(str, notify=textChanged)
    def text(self) -> str:
        return self._text

    @QtCore.Property(str, constant=True)
    def path(self) -> str:
        return str(log_path())

    @QtCore.Slot()
    def refresh(self) -> None:
        try:
            data = log_path().read_text(encoding="utf-8")
        except OSError:
            data = ""
        if data == self._text:
            return
        self._text = data
        self.textChanged.emit()

    @QtCore.Slot()
    def clear(self) -> None:
        dest = log_path()
        try:
            with _LOCK:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("", encoding="utf-8")
        except OSError:
            return
        self._text = ""
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


def _profile_running() -> bool:
    from gremlin.event_handler import EventListener

    # Never create the listener here (it hooks the keyboard); read it if it exists.
    listener = EventListener.instance
    return bool(listener is not None and listener.gremlin_active)


@ta.QmlElement
class DebugLog(QtCore.QObject):
    """One diagnostic log file, filtered by level and text, for the Live Log
    Reader's Debug tab."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._file = "system"
        self._level = "All"
        self._find = ""
        self._raw: str | None = None
        self._shown: list[tuple[int, str]] = []
        self._total = 0
        self._warn = "#F0A30A"
        self._error = "#F87171"
        self._on = True
        # Load Whole File: read all of a big file, not just its end.
        self._whole = False
        self._cut = False
        # (size, mtime) of the file as last read; unchanged means no re-read.
        self._stamp: tuple[int, int] | None = None
        # Live: show the live capture (gremlin.live_capture) instead of a file.
        self._live = False
        self._live_version = -1
        self._live_rows: list[tuple[int, str]] = []
        self._muted = "#9CA3AF"
        self._running = False

    def _path(self) -> Path:
        from gremlin.util import logs_dir

        return logs_dir() / DEBUG_FILES.get(self._file, "system.log")

    def _set(self, name: str, value: str) -> None:
        if getattr(self, name) != value:
            setattr(self, name, value)
            self._apply()

    def _apply(self) -> None:
        if self._live:
            # Levels do not apply to live capture; Find does.
            entries = self._live_rows
            needle = self._find.strip().lower()
            self._shown = [
                row for row in entries if not needle or needle in row[1].lower()
            ]
        else:
            entries = debug_entries(self._raw or "")
            self._shown = filter_entries(entries, self._level, self._find)
        self._total = len(entries)
        self.changed.emit()

    def _set_live(self, on: bool) -> None:
        on = bool(on)
        if on == self._live:
            return
        self._live = on
        live_capture.set_enabled(on)
        self._live_version = -1
        if on:
            self.refresh()
        else:
            self._reload()

    def _set_file(self, value: str) -> None:
        if value != self._file:
            self._file = value
            self._whole = False
            self._reload()

    file = QtCore.Property(
        str, lambda self: self._file, _set_file, notify=changed,
    )
    level = QtCore.Property(
        str, lambda self: self._level, lambda self, v: self._set("_level", v),
        notify=changed,
    )
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
    mutedColor = QtCore.Property(
        str, lambda self: self._muted, lambda self, v: self._set("_muted", v),
        notify=changed,
    )
    live = QtCore.Property(
        bool, lambda self: self._live, _set_live, notify=changed,
    )

    @QtCore.Property(bool, notify=changed)
    def running(self) -> bool:
        """A profile is running (live capture only sees inputs then)."""
        return self._running

    @QtCore.Property(str, notify=changed)
    def path(self) -> str:
        return str(self._path())

    @QtCore.Property(int, notify=changed)
    def shownCount(self) -> int:
        return len(self._shown)

    @QtCore.Property(int, notify=changed)
    def totalCount(self) -> int:
        return self._total

    @QtCore.Property(bool, notify=changed)
    def exists(self) -> bool:
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
        """The shown entries; warnings and errors in color."""
        lines = []
        for rank, body in self._shown:
            text = html.escape(body).replace("\n", "<br>")
            if rank >= 3:
                text = f'<span style="color:{self._error}">{text}</span>'
            elif rank == 2:
                text = f'<span style="color:{self._warn}">{text}</span>'
            elif rank < 0:
                text = f'<span style="color:{self._muted}">{text}</span>'
            lines.append(text)
        # white-space: pre keeps the view's own font (a <pre> would not).
        return '<div style="white-space:pre">' + "<br>".join(lines) + "</div>"

    @QtCore.Slot()
    def refresh(self) -> None:
        on = self._logging_on()
        running = _profile_running()
        if (on, running) != (self._on, self._running):
            self._on, self._running = on, running
            self.changed.emit()
        if self._live:
            current = live_capture.version()
            if current == self._live_version:
                return
            rows = live_capture.entries()
            self._live_version = live_capture.version()
            self._live_rows = [
                (1 if kind == live_capture.RAN else -1, text) for kind, text in rows
            ]
            self._apply()
            return
        path = self._path()
        try:
            stat = path.stat()
            stamp = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            stamp = None
        if stamp == self._stamp and self._raw is not None:
            return
        self._stamp = stamp
        cut = False
        data = ""
        if stamp is not None:
            try:
                with path.open("rb") as handle:
                    if stamp[0] > _TAIL_BYTES and not self._whole:
                        handle.seek(stamp[0] - _TAIL_BYTES)
                        handle.readline()  # drop the cut-off line
                        cut = True
                    data = handle.read().decode("utf-8", errors="replace")
            except OSError:
                data = ""
        if data == self._raw and cut == self._cut:
            return
        self._raw = data
        self._cut = cut
        self._apply()

    def _reload(self) -> None:
        self._raw = None
        self._stamp = None
        self.refresh()

    @QtCore.Slot()
    def loadWhole(self) -> None:
        """Read all of the file this time (until another log is chosen)."""
        self._whole = True
        self._reload()

    @QtCore.Slot()
    def clear(self) -> None:
        """Empty the shown file. The program's own log handler has it open,
        so it is emptied through that handler; otherwise directly."""
        import logging

        if self._live:
            live_capture.clear()
            self._live_version = -1
            self.refresh()
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

    @QtCore.Slot()
    def copyShown(self) -> None:
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText("\n".join(body for _rank, body in self._shown))

    @QtCore.Slot()
    def openFolder(self) -> None:
        folder = self._path().parent
        folder.mkdir(parents=True, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))
