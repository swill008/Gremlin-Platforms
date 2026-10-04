# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""File -> Open Program Folder and Open Data Folder (main window).

Program folder: where gremlin_platforms.exe is (the source folder when run
from source). Data folder: the one chosen in Options, by default Gremlin
Platforms in the user's profile. Explorer is stood in for: nothing opens.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest
from PySide6 import QtCore, QtGui

from gremlin import util
from gremlin.ui import backend

_ROOT = pathlib.Path(__file__).parents[2]


def test_program_folder_from_source_is_the_source_folder() -> None:
    assert pathlib.Path(util.program_folder()) == _ROOT.resolve()


def test_program_folder_installed_is_the_exe_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    exe = tmp_path / "Gremlin-Platforms" / "gremlin_platforms.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert pathlib.Path(util.program_folder()) == exe.parent.resolve()


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    urls: list[str] = []
    monkeypatch.setattr(
        QtGui.QDesktopServices,
        "openUrl",
        lambda url: urls.append(QtCore.QUrl(url).toLocalFile()) or True,
    )
    return urls


def test_the_actions_open_those_folders(
    opened: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.setattr(util, "data_folder", lambda: str(tmp_path))
    # The class behind the one shared Backend (no window needed).
    klass = backend.Backend.klass
    klass.openProgramFolder(None)  # type: ignore[arg-type]
    klass.openDataFolder(None)  # type: ignore[arg-type]
    assert [pathlib.Path(p) for p in opened] == [_ROOT.resolve(), tmp_path]


def test_both_are_in_the_file_menu() -> None:
    commands = (_ROOT / "qml" / "main_commands.js").read_text(encoding="utf-8")
    assert re.search(r'id: "file.programFolder", text: "Open Program Folder"', commands)
    assert re.search(r'id: "file.dataFolder", text: "Open Data Folder"', commands)
    main = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    start = main.index('title: qsTr("File")')
    file_menu = main[start:main.index('title: qsTr("View")')]
    rows = re.findall(r'command: "([^"]+)"|(ThemedMenuSeparator)', file_menu)
    names = [c or s for c, s in rows]
    at = names.index("file.programFolder")
    # After Save Profile As, before Exit, set apart by separators.
    assert names[at - 2:at + 4] == [
        "file.saveAs", "ThemedMenuSeparator", "file.programFolder",
        "file.dataFolder", "ThemedMenuSeparator", "file.exit",
    ]
