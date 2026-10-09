# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S53: the Undo / Redo buttons beside a right-click menu's title, one step
list for the window. Library changes finish in the background, after the
menu's own refresh: the still-open menu must follow them (Redo comes on, the
next Undo), and close when what it was for is gone.

Runs the real Device Library window off-screen in its own process (this file
as a script, over library_undo_ui_smoke.py's stand-in Library) with an Undo
that finishes later, as the real one does; the header button gets a real
click.

    python test/unit/test_library_menu_refresh.py <out_dir>
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_FIRST = "Undo Rename Left throttle"
_NEXT = "Undo Copy to Another Stick"
_REDO = "Redo Rename Left throttle"

# Finds the open menu's Undo header button and clicks its centre.
_CLICK_UNDO = (
    "(function() { function f(it) {"
    " if (it.modelData && it.modelData.label === 'Undo') return it;"
    " var k = it.children; for (var i = 0; i < k.length; i++) {"
    " var r = f(k[i]); if (r) return r } return null }"
    " var b = f(_rowMenu.contentItem);"
    " var p = b.mapToItem(null, b.width / 2, b.height / 2);"
    " deviceLibrary.clickAt(p.x, p.y); return true })()"
)
_MENU = (
    "JSON.stringify({opened: _rowMenu.opened, title: _rowMenu.model.title,"
    " header: _rowMenu.model.header.map(h => [h.label, h.enabled])})"
)


def _smoke() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "library_undo_ui_smoke", _HERE / "library_undo_ui_smoke.py"
    )
    assert spec and spec.loader
    undo_ui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(undo_ui)
    menus = undo_ui.menus

    import shiboken6
    from PySide6 import QtCore, QtGui, QtQuick, QtTest

    base = undo_ui.UndoStandIn

    class LaterUndo(base):
        """Undo finishes later, as the Library's background work does; it
        can also take a saved setup away (that undo removed it)."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self._gone = ""

        @QtCore.Slot(str)
        def goneOnUndo(self, key: str) -> None:
            self._gone = key

        @QtCore.Slot()
        def undo(self) -> None:
            undo_ui._CALLS.append("undo")

            def finish() -> None:
                if self._gone:
                    self.deleteItem(self._gone)
                self.setSteps(_NEXT, _REDO)

            QtCore.QTimer.singleShot(300, finish)

        @QtCore.Slot(float, float)
        def clickAt(self, x: float, y: float) -> None:
            for w in QtGui.QGuiApplication.topLevelWindows():
                if w.isVisible() and w.title() == "Device Library":
                    quick = shiboken6.wrapInstance(
                        shiboken6.getCppPointer(w)[0], QtQuick.QQuickWindow
                    )
                    QtTest.QTest.mouseClick(
                        quick,
                        QtCore.Qt.MouseButton.LeftButton,
                        QtCore.Qt.KeyboardModifier.NoModifier,
                        QtCore.QPoint(int(x), int(y)),
                    )
                    return

    import gremlin.ui.device_library_model as dlm

    dlm.DeviceLibraryModel = LaterUndo
    idle = "!deviceLibrary.busy"
    menus.STEPS = [
        (
            "open",
            f"deviceLibrary.setSteps('{_FIRST}', ''); _list.forceActiveFocus();"
            " _bridge.click('libraryRow_dev-00000001', 'right', '')",
            "_rowMenu.opened",
            _MENU,
        ),
        (
            "undo-click",
            _CLICK_UNDO,
            f"{idle} && deviceLibrary.redoText === '{_REDO}'",
            "",
        ),
        ("after-undo", "true", "", _MENU),
        (
            "open-setup",
            "_rowMenu.close(); deviceLibrary.setSteps('Undo Save', '');"
            " deviceLibrary.setAllOpen(true); deviceLibrary.goneOnUndo('set-00000001')",
            "_bridge.item('libraryRow_set-00000001') !== null",
            "",
        ),
        (
            "setup-menu",
            "_bridge.click('libraryRow_set-00000001', 'right', '')",
            "_rowMenu.opened",
            _MENU,
        ),
        (
            "gone-click",
            _CLICK_UNDO,
            f"{idle} && deviceLibrary.rows.every(r => r.key !== 'set-00000001')"
            f" && deviceLibrary.undoText === '{_NEXT}'",
            "",
        ),
        ("after-gone", "true", "", _MENU),
    ]
    menus.SHOTS = {}
    sys.argv = sys.argv[:2]
    menus.main()


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("dl_menu_refresh")
    home = tmp_path_factory.mktemp("home")
    proc = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve()), str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
            "USERPROFILE": str(home),
        },
    )
    results: dict = {"errors": [], "warnings": []}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            value = json.loads(value)
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
            results[name] = value
        elif line.startswith("ERROR"):
            results["errors"].append(line)
        elif line.startswith("WARN"):
            results["warnings"].append(line)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_runs_without_errors_or_warnings(run: dict) -> None:
    assert run["errors"] == []
    assert run["warnings"] == []


def test_open_menu_follows_an_undo_that_finishes_later(run: dict) -> None:
    before = run["open"]
    assert before["opened"] is True
    assert before["header"] == [["Undo", True], ["Redo", False]]
    after = run["after-undo"]
    # The same menu, still open, now with Redo on.
    assert after["opened"] is True
    assert after["title"] == before["title"]
    assert after["header"] == [["Undo", True], ["Redo", True]]


def test_menu_closes_when_its_item_is_gone(run: dict) -> None:
    assert run["setup-menu"]["opened"] is True
    assert run["after-gone"]["opened"] is False


if __name__ == "__main__":
    _smoke()
