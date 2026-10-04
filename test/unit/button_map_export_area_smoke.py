# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
for a stick, sets its export area with Alt+drag, exports, resizes the area
by its handle and clears it; prints what happened as JSON.
test_button_map_export_area.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_export_area_smoke.py
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
        call(win, "exportViewTo", url, "png")
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
    out["area"] = json.loads(ev("JSON.stringify(_buttonMap.exportArea)"))
    out["shown"] = [ev("_ed().exportAreaShown"), ev("_tools.isOpen('exportArea')")]
    # Like every tool: pinned it stays when the map is clicked, unpinned
    # it hides.
    ev("_tools.setPinned('exportArea', true)")
    ev("_ed().mapPressed()")
    QtTest.QTest.qWait(200)
    out["pinned-after-map-click"] = ev("_tools.isOpen('exportArea')")
    ev("_tools.setPinned('exportArea', false)")
    ev("_ed().mapPressed()")
    QtTest.QTest.qWait(200)
    out["unpinned-after-map-click"] = ev("_tools.isOpen('exportArea')")
    ev("_tools.setOpen('exportArea', true)")
    doc = json.loads(hp.module_json_path("pJoy Pro", GUID).read_text(encoding="utf-8"))
    out["saved"] = (doc.get("ui") or {}).get("exportArea")
    out["export"] = export()
    page = json.loads(ev("JSON.stringify(_ed().spaceRect())"))
    out["page"] = [page["w"], page["h"], ev("_buttonMap.exportScale")]
    # The bottom-right handle, dragged out.
    corner = at("(function(){ var r = e.exportAreaRect();"
                " return {x: r.x + r.w, y: r.y + r.h} })()")
    drag(corner, corner + QtCore.QPoint(60, 40), Mods.NoModifier)
    out["resized"] = json.loads(ev("JSON.stringify(_buttonMap.exportArea)"))
    # Locked: Alt+drag no longer changes it.
    ev("_tools.setLocked('exportArea', true)")
    QtTest.QTest.qWait(200)
    drag(start, end + QtCore.QPoint(100, 0), Mods.AltModifier)
    out["locked"] = json.loads(ev("JSON.stringify(_buttonMap.exportArea)"))
    ev("_tools.setLocked('exportArea', false)")
    # Cleared: the whole page again.
    ev("_ed().clearExportArea()")
    QtTest.QTest.qWait(300)
    out["cleared"] = [ev("JSON.stringify(_buttonMap.exportArea)")] + export()
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
