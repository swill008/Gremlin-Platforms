# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S3, S6 (D-NEXTLIST-1 items 4 and 6): runs the real Device Library
window off-screen with the stand-in Library of device_library_CU_menus_smoke.py,
whose device_photo(folder) gives "left-throttle" a picture. Prints what the
device rows show (the small picture or its icon, the name / description /
saved setups lines, the badge on the right, the row height), the list's
minimum width, and the divider's share kept after a real drag of the divider.
test_library_rows.py runs it.

    python test/unit/library_rows_smoke.py <out_dir>

LIB_ROWS_ROOT (optional) runs another copy of the window and model (a folder
with qml/, theme/ and gremlin/ui/device_library_model.py), to show the test
fails on the old code.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "device_library_CU_menus_smoke", _HERE / "device_library_CU_menus_smoke.py"
)
assert _spec and _spec.loader
menus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(menus)

from PySide6 import QtCore, QtGui, QtTest  # noqa: E402

import gremlin.ui.device_library_model as model_mod  # noqa: E402
from gremlin.ui import window_placement  # noqa: E402

_OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
_OLD = os.environ.get("LIB_ROWS_ROOT", "")
if _OLD:
    menus.ROOT = Path(_OLD)
    _old_spec = importlib.util.spec_from_file_location(
        "old_device_library_model",
        Path(_OLD) / "gremlin" / "ui" / "device_library_model.py",
    )
    assert _old_spec and _old_spec.loader
    _old = importlib.util.module_from_spec(_old_spec)
    _old_spec.loader.exec_module(_old)
    _Base = _old.DeviceLibraryModel
else:
    _Base = model_mod.DeviceLibraryModel

# A picture for the "left-throttle" module folder, with the owner's stamp.
_PIC = _OUT / "photo.png"
_img = QtGui.QImage(64, 48, QtGui.QImage.Format.Format_ARGB32)
_img.fill(QtGui.QColor(200, 60, 60))
_img.save(str(_PIC))


class RowsLibrary(menus.MenuLibrary):
    def device_photo(self, folder: str) -> str:
        self.calls.append(("device_photo", folder))
        return f"{_PIC}?t=123" if folder == "left-throttle" else ""


class DragModel(_Base):
    """The real model with two test seams: a real mouse drag in the window
    and the divider share the program kept."""

    @QtCore.Slot(float, float, float)
    def dragAt(self, x0: float, y: float, x1: float) -> None:
        win = QtGui.QGuiApplication.topLevelWindows()
        quick = next(w for w in win if w.isVisible())
        start = QtCore.QPoint(int(x0), int(y))
        QtTest.QTest.mousePress(
            quick,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            start,
        )
        steps = 10
        for i in range(1, steps + 1):
            x = int(x0 + (x1 - x0) * i / steps)
            QtTest.QTest.mouseMove(quick, QtCore.QPoint(x, int(y)), 10)
        QtTest.QTest.mouseRelease(
            quick,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            QtCore.QPoint(int(x1), int(y)),
        )

    @QtCore.Slot(result=float)
    def savedSplit(self) -> float:
        return float(window_placement.split_ratio("deviceLibrary", -1.0))


menus.MenuLibrary = RowsLibrary
model_mod.DeviceLibraryModel = DragModel


_FINDERS = (
    " function kid(t, name) { if (!t) return null;"
    " for (var i = 0; i < t.children.length; i++)"
    " if (t.children[i].objectName === name) return t.children[i]; return null }"
    " function badgeOf(r) { var b = null;"
    " var kids = r.children[r.children.length - 1].children;"
    " for (var k = 0; k < kids.length; k++)"
    " if (kids[k].border !== undefined && kids[k].radius > 0) b = kids[k]; return b }"
)


def _row(key: str) -> str:
    """One device row's parts, by their place in the window."""
    return (
        "(function() {" + _FINDERS + " var r = _bridge.item('libraryRow_" + key + "');"
        " var t = _bridge.item('libraryThumb_" + key + "');"
        " var c = _bridge.item('libraryRowCount_" + key + "');"
        " var n = _bridge.item('libraryRowName_" + key + "');"
        " var p = kid(t, 'deviceThumbImage'); var g = kid(t, 'deviceThumbGlyph');"
        " var badge = badgeOf(r);"
        " return {height: r.height,"
        " thumb: t ? {w: t.width, h: t.height, visible: t.visible,"
        "  picture: p ? (p.visible && p.status === Image.Ready) : false,"
        "  source: p ? String(p.source) : '', glyph: g ? g.visible : false} : null,"
        " name: n ? n.mapToItem(r, 0, 0).y : -1,"
        " count: c ? {visible: c.visible, text: c.text, y: c.mapToItem(r, 0, 0).y,"
        "  x: c.mapToItem(r, 0, 0).x, nameX: n.mapToItem(r, 0, 0).x} : null,"
        " badgeX: badge ? badge.mapToItem(r, 0, 0).x : -1, width: r.width} })()"
    )


menus.STEPS = [
    (
        "rows",
        "deviceLibrary.setAllOpen(false)",
        "_bridge.item('libraryThumb_dev-00000001') !== null"
        " && _bridge.item('libraryThumb_dev-00000001').showsPicture",
        "JSON.stringify({photo: deviceLibrary.rows[0].photo,"
        " one: " + _row("dev-00000001") + ", three: " + _row("dev-00000003") + "})",
    ),
    (
        "min",
        "true",
        "",
        "JSON.stringify({min: _listPane.SplitView.minimumWidth, dp: Style.dp(260)})",
    ),
    (
        "drag",
        "var p = _listPane.mapToItem(null, _listPane.width + 2, 200);"
        " deviceLibrary.dragAt(p.x, p.y, p.x - 250)",
        "",
        "JSON.stringify({pane: _listPane.width, split: _split.width,"
        " saved: deviceLibrary.savedSplit ? deviceLibrary.savedSplit() : -1})",
    ),
]
menus.SHOTS = {"rows": "library_rows"}

if __name__ == "__main__":
    sys.argv = sys.argv[:2]
    menus.main()
