# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""One file log of reads and saves, and the window that shows it."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta

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
