# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S57: every title bar starts with the program name and version, then
the window's own title, and the name shows once."""

from __future__ import annotations

import json
import pathlib

from PySide6 import QtCore, QtGui

from gremlin.ui import window_titles

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_VERSION = json.loads((_ROOT / "version.json").read_text(encoding="utf-8"))["version"]
_PROGRAM = f"Gremlin-Platforms R1 {_VERSION}"


def test_the_program_comes_first_then_the_window() -> None:
    assert window_titles.program_title() == _PROGRAM
    assert window_titles.format_title("* Flight.xml") == f"{_PROGRAM} - * Flight.xml"
    assert window_titles.format_title("Untitled") == f"{_PROGRAM} - Untitled"
    library = window_titles.format_title("Device Library")
    assert library == f"{_PROGRAM} - Device Library"
    assert (
        window_titles.format_title("Help — Button Map")
        == f"{_PROGRAM} - Help — Button Map"
    )


def test_the_name_shows_once() -> None:
    assert window_titles.format_title("") == _PROGRAM
    assert window_titles.format_title(_PROGRAM) == _PROGRAM
    assert window_titles.format_title("Gremlin-Platforms R1") == _PROGRAM
    # A title written the old way keeps only its own part.
    old = f"Flight.xml - Gremlin-Platforms R1 {_VERSION}"
    assert window_titles.format_title(old) == f"{_PROGRAM} - Flight.xml"


class _Window(QtCore.QObject):
    """A stand-in with a window's title API: no native window is made
    (a real one could take a shared test process down)."""

    windowTitleChanged = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._title = ""

    def title(self) -> str:
        return self._title

    def setTitle(self, title: str) -> None:  # noqa: N802
        self._title = title
        self.windowTitleChanged.emit(title)


def test_a_watched_window_follows_its_title(qapp: object) -> None:
    # watch() is what the app's Show filter calls for every window.
    written: list[str] = []
    bars = window_titles.TitleBars(
        QtGui.QGuiApplication.instance(),
        setter=lambda _w, text: written.append(text),
        watch_shown=False,
    )
    window = _Window()
    window.setTitle("Device Library")
    bars.watch(window)
    assert written[-1] == f"{_PROGRAM} - Device Library"
    window.setTitle("Options")
    assert written[-1] == f"{_PROGRAM} - Options"


def test_nothing_is_changed_off_windows(qapp: object) -> None:
    # The tests run off-screen: no title bar to write.
    assert window_titles.install(QtGui.QGuiApplication.instance()) is None
