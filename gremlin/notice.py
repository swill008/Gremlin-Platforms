# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""A fact's owner announcing it (D-01-OWNER-NOTICES): one program-wide
signal per burst of changes, always on the main thread, as the can't-be-sent
notice does (gremlin.modules.output). Any thread may ask; without a Qt
application the signal is sent at once."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from PySide6 import QtCore

syslog = logging.getLogger("system")


class NoticeTimer(QtCore.QObject):
    """Lives on the main thread; a worker's ask is queued to it."""

    asked = QtCore.Signal()

    def __init__(self, send: Callable[[], None]) -> None:
        super().__init__()
        self._send_fn = send
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._send)
        self.asked.connect(self.ask)

    @QtCore.Slot()
    def ask(self) -> None:
        """Connected to the program signals that mean the fact may have
        changed (main thread)."""
        self._timer.start()

    @QtCore.Slot()
    def sent_elsewhere(self) -> None:
        """The signal went out by hand after the change: no second send."""
        self._timer.stop()

    @QtCore.Slot()
    def _send(self) -> None:
        try:
            self._send_fn()
        except Exception:  # noqa: BLE001 - a listener never stops the notice
            syslog.exception("A notice's listener failed")


class BurstNotice:
    """send() goes out once for a burst of notify() calls, on the main
    thread. listen(timer), when given, connects the program signals that
    mean the fact may have changed to timer.ask (run once, when the notice
    starts)."""

    def __init__(
        self,
        send: Callable[[], None],
        listen: Callable[[NoticeTimer], None] | None = None,
    ) -> None:
        self._send = send
        self._listen = listen
        self._timer: NoticeTimer | None = None
        self._lock = threading.Lock()

    def watch(self) -> NoticeTimer | None:
        """Starts the notice (once, on the main thread): None without a Qt
        application, or on another thread before it started."""
        if self._timer is not None:
            return self._timer
        app = QtCore.QCoreApplication.instance()
        if app is None or threading.current_thread() is not threading.main_thread():
            return None
        with self._lock:
            if self._timer is None:
                timer = NoticeTimer(self._send)
                if self._listen is not None:
                    self._listen(timer)
                self._timer = timer
            return self._timer

    def notify(self) -> None:
        """The fact may have changed: sent once for the burst, on the main
        thread; at once without a Qt application."""
        timer = self.watch()
        if timer is not None:
            timer.asked.emit()
            return
        app = QtCore.QCoreApplication.instance()
        if app is None:
            self._send()
        else:
            # Another thread before the notice started: started on the main one.
            QtCore.QTimer.singleShot(0, app, self.notify)
