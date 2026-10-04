# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
for a stick, sets its print area with Alt+drag, exports, resizes the area
by its handle and clears it; prints what happened as JSON.
test_button_map_print_area.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_print_area_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import gremlin.ui.hardware_profile as hp  # noqa: E402
import joystick_gremlin  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
Button = QtCore.Qt.MouseButton
Mods = QtCore.Qt.KeyboardModifier


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    out: dict = {}
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "buttonMapWindow")
    win.setProperty("width", 1200)
    win.setProperty("height", 800)
    QtTest.QTest.qWait(300)
    qwin = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def at(code: str) -> QtCore.QPoint:
        # An editor point (from code) in the window.
        p = json.loads(ev(
            "(function(){ var e = _ed(); var q = (" + code + ");"
            " var w = e.mapToItem(null, q.x, q.y);"
            " return JSON.stringify({x: w.x, y: w.y}) })()"
        ))
        return QtCore.QPoint(round(p["x"]), round(p["y"]))

    def drag(a: QtCore.QPoint, b: QtCore.QPoint, mods: Mods) -> None:
        QtTest.QTest.mousePress(qwin, Button.LeftButton, mods, a)
        QtTest.QTest.qWait(50)
        for i in range(1, 11):
            p = QtCore.QPointF(a + (b - a) * (i / 10))
            move = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove, p, p, Button.NoButton,
                Button.LeftButton, mods,
            )
            QtCore.QCoreApplication.sendEvent(qwin, move)
            QtTest.QTest.qWait(20)
        QtTest.QTest.mouseRelease(qwin, Button.LeftButton, mods, b)
        QtTest.QTest.qWait(300)

    target = Path(os.environ["USERPROFILE"]) / "export.png"

    def export() -> list:
        if target.exists():
            target.unlink()
        url = QtCore.QUrl.fromLocalFile(str(target)).toString()
        call(win, "exportTo", url, "png")
        QtTest.QTest.qWait(1500)
        image = QtGui.QImage(str(target))
        return [image.width(), image.height()]

    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
    # Alt+drag on an empty part of the page.
    def page_at(fx: float, fy: float) -> QtCore.QPoint:
        return at("(function(){ var s = e.spaceRect();"
                  f" return {{x: s.x + s.w * {fx}, y: s.y + s.h * {fy}}} }})()")

    start = page_at(0.3, 0.3)
    end = page_at(0.6, 0.7)
    drag(start, end, Mods.AltModifier)
    out["area"] = json.loads(ev("JSON.stringify(_buttonMap.printArea)"))
    out["shown"] = [ev("_ed().printAreaShown"), ev("_tools.isOpen('printArea')")]
    # Like every tool: pinned it stays when the map is clicked, unpinned
    # it hides.
    ev("_tools.setPinned('printArea', true)")
    ev("_ed().mapPressed()")
    QtTest.QTest.qWait(200)
    out["pinned-after-map-click"] = ev("_tools.isOpen('printArea')")
    ev("_tools.setPinned('printArea', false)")
    ev("_ed().mapPressed()")
    QtTest.QTest.qWait(200)
    out["unpinned-after-map-click"] = ev("_tools.isOpen('printArea')")
    ev("_tools.setOpen('printArea', true)")
    doc = json.loads(hp.module_json_path("pJoy Pro", GUID).read_text(encoding="utf-8"))
    out["saved"] = (doc.get("ui") or {}).get("printArea")
    out["export"] = export()
    # What the export should be: the area at 100% (1:1 with the photo, or
    # the page 1920 px wide without one; the stand-in stick has none).
    out["pixels"] = json.loads(ev("JSON.stringify(_buttonMap.exportPixels())"))
    out["whole-page-at-100"] = ev(
        "Math.round(_ed().spaceRect().w * _buttonMap.exportFactor())")
    # The bottom-right handle, dragged out. The chip pool docked at the
    # bottom covers it in this small window: docked at the top instead.
    ev("_tools.setDock('chips', 'top')")
    QtTest.QTest.qWait(200)
    corner = at("(function(){ var r = e.printAreaRect();"
                " return {x: r.x + r.w, y: r.y + r.h} })()")
    drag(corner, corner + QtCore.QPoint(60, 40), Mods.NoModifier)
    out["resized"] = json.loads(ev("JSON.stringify(_buttonMap.printArea)"))
    # Locked: Alt+drag no longer changes it.
    ev("_tools.setLocked('printArea', true)")
    QtTest.QTest.qWait(200)
    drag(start, end + QtCore.QPoint(100, 0), Mods.AltModifier)
    out["locked"] = json.loads(ev("JSON.stringify(_buttonMap.printArea)"))
    ev("_tools.setLocked('printArea', false)")
    # Cleared: the whole page again.
    ev("_ed().clearPrintArea()")
    QtTest.QTest.qWait(300)
    out["cleared"] = [ev("JSON.stringify(_buttonMap.printArea)")] + export()

    def aspect() -> float:
        return float(ev(
            "(function(){ var r = _ed().printAreaRect(); return r.w / r.h })()"))

    # A paper: with no area yet, the largest of its shape, centred; then
    # the area keeps the paper's shape (Letter inside 1/4" margins: 8 x 10.5).
    ev("_buttonMap.setPrint('paper', 'letter')")
    QtTest.QTest.qWait(200)
    out["letter-aspect"] = [aspect(), ev("_ed().printAspect")]
    drag(start, end, Mods.AltModifier)
    out["letter-drawn-aspect"] = aspect()
    ev("_buttonMap.setPrint('landscape', true)")
    QtTest.QTest.qWait(200)
    out["landscape-aspect"] = [aspect(), ev("_ed().printAspect")]
    ev("_buttonMap.setPrint('scale', 50)")
    out["scale-50"] = json.loads(ev("JSON.stringify(_buttonMap.exportPixels())"))
    ev("_buttonMap.setPrint('scale', 100)")
    out["scale-100"] = json.loads(ev("JSON.stringify(_buttonMap.exportPixels())"))
    doc = json.loads(hp.module_json_path("pJoy Pro", GUID).read_text(encoding="utf-8"))
    out["saved-print"] = (doc.get("ui") or {}).get("print")
    # Only while editing: its tool open and pinned, the frame shows in Edit,
    # not on the live map, and again in the next Edit.
    ev("_tools.setPinned('printArea', true); _tools.setOpen('printArea', true)")
    QtTest.QTest.qWait(200)
    out["frame-editing"] = ev("_ed().printAreaShown")
    ev("_buttonMap.discardEdit()")
    QtTest.QTest.qWait(800)
    out["frame-live"] = [ev("_buttonMap.editing"), ev("_ed().printAreaShown"),
                         ev("_tools.isOpen('printArea')")]
    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
    out["frame-edit-again"] = ev("_ed().printAreaShown")
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
