# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
for a stick and its Print & Export window, changes the paper and scale,
and prints what the window shows as JSON (and a screenshot when a folder
is given). test_print_export_window.py runs it in its own process with a
fresh user folder.

    python test/unit/print_export_window_smoke.py [screenshot folder]
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

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)

# A few chips on the stand-in stick's map, for the preview to show.
from gremlin.ui import hardware_profile  # noqa: E402

_map = hardware_profile.module_json_path("pJoy Pro", GUID)
_map.parent.mkdir(parents=True, exist_ok=True)
_map.write_text(json.dumps({
    "kind": "control.hardware", "device": "pJoy Pro",
    "nodes": [
        {"kind": "btn", "id": f"b{i}", "label": f"Button {i}",
         "chipFx": 0.25 + 0.1 * i, "chipFy": 0.3 + 0.08 * i}
        for i in range(1, 6)
    ],
}), encoding="utf-8")


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
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

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
    ev("_buttonMap.openPrintExport()")
    QtTest.QTest.qWait(1200)
    pw = next(
        w for w in QtGui.QGuiApplication.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow) and w.title() == "Print & Export"
    )

    def child(name: str) -> QtCore.QObject:
        return pw.findChild(QtCore.QObject, name)

    out["open"] = [pw.isVisible(), ev("_tools.isOpen('printArea')")]
    ev("_buttonMap.setPrint('paper', 'letter')")
    ev("_buttonMap.setPrint('scale', 50)")
    QtTest.QTest.qWait(1500)
    page = child("printPreviewPage")
    image = child("printPreviewImage")
    out["page-shape"] = page.property("width") / page.property("height")
    out["preview-ready"] = (image.property("paintedWidth") or 0) > 0
    out["paper-box"] = child("printPaper").property("currentText")
    out["scale-box"] = child("printScale").property("value")
    out["pixels-text"] = child("printPixels").property("text")
    px = json.loads(ev("JSON.stringify(_buttonMap.exportPixels())"))
    out["pixels"] = [px["w"], px["h"]]
    if shots is not None:
        shots.mkdir(parents=True, exist_ok=True)
        pw.grabWindow().save(str(shots / "print-export.png"))
        win.grabWindow().save(str(shots / "map-with-print-area.png"))
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
