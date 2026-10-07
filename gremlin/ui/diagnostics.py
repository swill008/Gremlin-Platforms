# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Save Diagnostics (01 S132) for QML: saveAsync collects on the main thread,
writes the zip on a worker and announces saved(ok, message) back on the main
thread."""

from __future__ import annotations

import logging

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import diagnostics
from gremlin.ui.util import to_local_path

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1


def _write_in_background(plan: diagnostics.Plan, dest: object, done: object) -> None:
    """saveAsync's worker: writes the zip, then done(ok, message). Touches no
    window or profile."""
    ok, message = diagnostics.save(plan, dest)  # type: ignore[arg-type]
    try:
        done(ok, message)  # type: ignore[operator]
    except RuntimeError:
        # The window closed while it ran: nobody to tell.
        pass


@ta.QmlElement
class Diagnostics(QtCore.QObject):
    """Help → Save Diagnostics… and the Debug tab's button."""

    busyChanged = QtCore.Signal()
    # Done, on the main thread: ok, and where the zip went or why it failed.
    saved = QtCore.Signal(bool, str)
    # The worker's result, queued to the main thread.
    _done = QtCore.Signal(bool, str)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._message = ""
        self._done.connect(self._finish, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        """A zip is being written."""
        return self._busy

    @QtCore.Property(str, notify=busyChanged)
    def message(self) -> str:
        """Where the last zip went, or why it failed ("" before one)."""
        return self._message

    @QtCore.Property(str, constant=True)
    def desktopUrl(self) -> str:
        return QtCore.QUrl.fromLocalFile(str(diagnostics.desktop_folder())).toString()

    @QtCore.Slot(result=str)
    def defaultFileUrl(self) -> str:
        """The suggested zip on the Desktop."""
        path = diagnostics.desktop_folder() / diagnostics.default_name()
        return QtCore.QUrl.fromLocalFile(str(path)).toString()

    @QtCore.Slot(str, bool, result=bool)
    def saveAsync(self, url: str, include_profile: bool) -> bool:
        """Starts writing the zip at url; returns False, starting nothing,
        while one is being written."""
        if self._busy:
            return False
        from gremlin import threads

        dest = to_local_path(url)
        if dest.suffix.lower() != ".zip":
            dest = dest.with_name(dest.name + ".zip")
        try:
            plan = diagnostics.collect(bool(include_profile))
        except Exception:
            logging.getLogger("system").exception("Diagnostics: collect failed")
            self._finish(False, diagnostics.failure_text(dest))
            return False
        self._busy = True
        self._message = ""
        try:
            threads.start(
                "Save diagnostics", _write_in_background, plan, dest, self._done.emit
            )
        except Exception:
            logging.getLogger("system").exception("Diagnostics: could not start")
            self._busy = False
            self.busyChanged.emit()
            return False
        self.busyChanged.emit()
        return True

    @QtCore.Slot(bool, str)
    def _finish(self, ok: bool, message: str) -> None:
        self._busy = False
        self._message = message
        self.busyChanged.emit()
        self.saved.emit(ok, message)
