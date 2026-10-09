# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Every window's title bar starts with the program name and version (01 S57).

A window keeps its own title ("Device Library", "* Flight.xml"); the title
bar Windows draws shows "Gremlin-Platforms R1 1.0.30 - Device Library". Qt
would add the program name at the end instead (it appends the display name
to a title that doesn't end with it), so the bar's text is set here, once
for every window, whenever its title changes. Off Windows (off-screen tests)
nothing is changed.
"""

from __future__ import annotations

import ctypes
import logging

from PySide6 import QtCore, QtGui

from gremlin import util

PROGRAM = "Gremlin-Platforms R1"


def program_title() -> str:
    """The program name and version: "Gremlin-Platforms R1 1.0.30"."""
    return f"{PROGRAM} {util.get_code_version()}"


def format_title(title: str, program: str | None = None) -> str:
    """The title bar text for a window titled `title`: the program first,
    then the window's own title ("" or the program itself: the program)."""
    program = program or program_title()
    own = (title or "").strip()
    # A title written the old way ("x - Gremlin-Platforms R1 ...") keeps
    # only its own part.
    cut = own.rfind(" - " + PROGRAM)
    if cut >= 0:
        own = own[:cut].rstrip()
    if not own or own == program or own == PROGRAM:
        return program
    return f"{program} - {own}"


def _set_native(window: QtGui.QWindow, text: str) -> None:
    hwnd = int(window.winId())
    if hwnd:
        ctypes.windll.user32.SetWindowTextW(ctypes.c_void_p(hwnd), text)


class TitleBars(QtCore.QObject):
    """Watches every window's title and writes the title bar's text."""

    def __init__(
        self, app: QtGui.QGuiApplication, setter=None, watch_shown: bool = True  # noqa: ANN001
    ) -> None:
        super().__init__(app)
        self._set = setter or _set_native
        self._seen: set[int] = set()
        if watch_shown:
            app.installEventFilter(self)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802
        if event.type() == QtCore.QEvent.Type.Show and isinstance(obj, QtGui.QWindow):
            self.watch(obj)
        return False

    def watch(self, window: QtGui.QWindow) -> None:
        key = id(window)
        if key not in self._seen:
            self._seen.add(key)
            window.windowTitleChanged.connect(lambda _t, w=window: self.apply(w))
            window.destroyed.connect(lambda *_a, k=key: self._seen.discard(k))
        self.apply(window)

    def apply(self, window: QtGui.QWindow) -> None:
        try:
            self._set(window, format_title(window.title()))
        except (RuntimeError, OSError) as e:  # a window going away
            logging.getLogger("system").debug(f"Title bar: {e}")


def install(app: QtGui.QGuiApplication) -> TitleBars | None:
    """Starts writing title bars (Windows only; nothing off-screen)."""
    if QtGui.QGuiApplication.platformName() != "windows":
        return None
    return TitleBars(app)
