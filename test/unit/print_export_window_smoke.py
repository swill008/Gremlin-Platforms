# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
for a stick and its Print & Export window, changes the paper and scale,
exports the whole page and a print area as PNG and a PDF on Letter into
the folder given, and prints what the window shows as JSON.
test_print_export_window.py runs it in its own process with a fresh user
folder, at screen scales 1 and 1.5.

    python test/unit/print_export_window_smoke.py <folder> [screenshots]
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

# A few chips on the stand-in stick's map, for the preview to show
# (SMOKE_CHIPS: that many instead, and SMOKE_PHOTO: a photo, to time a big
# map).
from gremlin.ui import hardware_profile  # noqa: E402

_map = hardware_profile.module_json_path("pJoy Pro", GUID)
_map.parent.mkdir(parents=True, exist_ok=True)
_chips = int(os.environ.get("SMOKE_CHIPS", "5"))
_doc: dict = {
    "kind": "control.hardware", "device": "pJoy Pro",
    "nodes": [
        {"kind": "btn", "id": f"b{i}", "label": f"Button {i}",
         "chipFx": 0.25 + 0.5 * ((i * 37) % 100) / 100,
         "chipFy": 0.3 + 0.4 * ((i * 61) % 100) / 100}
        if _chips != 5 else
        {"kind": "btn", "id": f"b{i}", "label": f"Button {i}",
         "chipFx": 0.25 + 0.1 * i, "chipFy": 0.3 + 0.08 * i}
        for i in range(1, _chips + 1)
    ],
}
if os.environ.get("SMOKE_PHOTO"):
    import shutil

    (_map.parent / "timing").mkdir(exist_ok=True)
    shutil.copy(os.environ["SMOKE_PHOTO"], _map.parent / "timing" / "photo.jpg")
    _doc["image"] = "timing/photo.jpg"
_map.write_text(json.dumps(_doc), encoding="utf-8")


def _difference(a: QtGui.QImage, b: QtGui.QImage) -> float:
    """Mean difference per color channel (0-255), b scaled to a's size."""
    a = a.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    b = b.convertToFormat(QtGui.QImage.Format.Format_RGB32).scaled(
        a.size(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation)
    total = 0
    count = 0
    for y in range(0, a.height(), 2):
        for x in range(0, a.width(), 2):
            p = a.pixelColor(x, y)
            q = b.pixelColor(x, y)
            total += (abs(p.red() - q.red()) + abs(p.green() - q.green())
                      + abs(p.blue() - q.blue()))
            count += 3
    return round(total / max(1, count), 2)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    shots = len(sys.argv) > 2
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

    def print_export_shown() -> bool:
        return any(
            isinstance(w, QtQuick.QQuickWindow) and w.title() == "Print & Export"
            and w.isVisible()
            for w in QtGui.QGuiApplication.topLevelWindows()
        )

    # Made with the Button Map, hidden until asked for.
    out["shown-with-the-map"] = print_export_shown()
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
    out["dpr"] = pw.devicePixelRatio()

    def region(item: QtCore.QObject) -> QtGui.QImage:
        """What the window shows of an item, at the window's pixels."""
        shot = pw.grabWindow()
        ratio = shot.devicePixelRatio()
        top = item.mapToScene(QtCore.QPointF(0, 0))
        return shot.copy(
            round(top.x() * ratio), round(top.y() * ratio),
            round(item.property("width") * ratio),
            round(item.property("height") * ratio),
        )

    # The print area moved: the preview follows at once (the page picture
    # cut to the area), then the sharp picture of the area takes over.
    content = child("printPreviewArea")
    crop = child("printPreviewCrop")
    sharp = child("printPreviewImage")
    moved = {"fx": 0.1, "fy": 0.15, "fw": 0.3, "fh": 0.6}
    ev(f"_buttonMap._ed().printArea = {json.dumps(moved)}")
    QtTest.QTest.qWait(40)
    out["moved-at-once"] = {
        "aspect": content.property("width") / content.property("height"),
        "crop": [crop.property("visible"), sharp.property("visible")],
        "offset": [-crop.property("x") / crop.property("width"),
                   -crop.property("y") / crop.property("height")],
    }
    cropped = region(content)
    for _ in range(100):
        QtTest.QTest.qWait(50)
        if sharp.property("visible") and (sharp.property("paintedWidth") or 0) > 0:
            break
    QtTest.QTest.qWait(150)
    out["moved-later"] = [crop.property("visible"), sharp.property("visible")]
    drawn = region(content)
    if shots:
        cropped.save(str(folder / "preview-crop.png"))
        drawn.save(str(folder / "preview-sharp.png"))
    out["crop-vs-sharp"] = _difference(cropped, drawn)

    # How long the hidden copy takes: the whole page, then the area.
    import time

    def timed(kind: str) -> float:
        start = time.perf_counter()
        ev(f"_buttonMap.renderPreview('{kind}', 1560, 1560, function(r) {{}})")
        QtTest.QTest.qWait(1)
        while ev("_renderer.busy") is True or ev("_renderer._queue.length") > 0:
            QtTest.QTest.qWait(5)
        return round((time.perf_counter() - start) * 1000)

    out["ms"] = {"page": timed("page"), "area": timed("area")}

    # Drag and zoom in the preview: the print area follows.
    def area_now() -> dict:
        return json.loads(str(ev("JSON.stringify(_buttonMap._ed().printArea)")))

    def middle() -> QtCore.QPointF:
        return content.mapToScene(QtCore.QPointF(
            content.property("width") / 2, content.property("height") / 2))

    def drag_preview(dx: float, dy: float) -> None:
        a = middle()
        b = a + QtCore.QPointF(dx, dy)
        Button = QtCore.Qt.MouseButton
        none = QtCore.Qt.KeyboardModifier.NoModifier
        QtTest.QTest.mousePress(pw, Button.LeftButton, none, a.toPoint())
        QtTest.QTest.qWait(30)
        for i in range(1, 11):
            p = a + (b - a) * (i / 10)
            move = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove, p, p, Button.NoButton,
                Button.LeftButton, none,
            )
            QtCore.QCoreApplication.sendEvent(pw, move)
            QtTest.QTest.qWait(15)
        QtTest.QTest.mouseRelease(pw, Button.LeftButton, none, b.toPoint())
        QtTest.QTest.qWait(200)

    def wheel(at: QtCore.QPointF, clicks: int) -> None:
        event = QtGui.QWheelEvent(
            at, pw.mapToGlobal(at), QtCore.QPoint(), QtCore.QPoint(0, 120 * clicks),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.KeyboardModifier.NoModifier,
            QtCore.Qt.ScrollPhase.NoScrollPhase, False,
        )
        QtCore.QCoreApplication.sendEvent(pw, event)
        QtTest.QTest.qWait(50)

    ev("_buttonMap.setPrint('paper', 'fit')")
    start = {"fx": 0.3, "fy": 0.3, "fw": 0.4, "fh": 0.4}
    ev(f"_buttonMap._ed().printArea = {json.dumps(start)}")
    QtTest.QTest.qWait(300)
    width = content.property("width")
    drag_preview(width / 4, 0)
    out["dragged"] = area_now()
    # Far to the right: the area stops at the page's left edge.
    drag_preview(width * 3, 0)
    out["dragged-to-edge"] = area_now()
    QtTest.QTest.qWait(200)
    doc = json.loads(_map.read_text(encoding="utf-8"))
    out["kept"] = (doc.get("ui") or {}).get("printArea")
    # The wheel: in (smaller) about the pointer, out (larger).
    ev(f"_buttonMap._ed().printArea = {json.dumps(start)}")
    QtTest.QTest.qWait(300)
    wheel(middle(), 1)
    out["zoomed-in"] = area_now()
    wheel(middle(), -2)
    out["zoomed-out"] = area_now()
    # Locked: neither moves it.
    ev("_tools.setLocked('printArea', true)")
    QtTest.QTest.qWait(100)
    before = area_now()
    drag_preview(width / 4, 0)
    wheel(middle(), 1)
    out["locked-unchanged"] = area_now() == before
    ev("_tools.setLocked('printArea', false)")
    ev("_buttonMap.setPrint('paper', 'letter')")
    QtTest.QTest.qWait(200)
    # Custom > Freeform (As Drawn): no paper, and back to the last one.
    freeform = child("printFreeform")
    paper = child("printPaper")
    out["paper-count"] = paper.property("count")

    def freeform_state() -> list:
        return [freeform.property("checked"), paper.property("enabled"),
                ev("_buttonMap.printSetup.paper"), paper.property("currentText")]

    QtCore.QMetaObject.invokeMethod(freeform, "click")
    QtTest.QTest.qWait(200)
    out["freeform-on"] = freeform_state()
    QtCore.QMetaObject.invokeMethod(freeform, "click")
    QtTest.QTest.qWait(200)
    out["freeform-off"] = freeform_state()
    if shots:
        pw.grabWindow().save(str(folder / "print-export.png"))
        win.grabWindow().save(str(folder / "map-with-print-area.png"))

    def export(name: str, fmt: str) -> list:
        """Exports through Print & Export's pipeline and waits for it."""
        target = folder / name
        url = QtCore.QUrl.fromLocalFile(str(target)).toString()
        size = json.loads(str(ev("JSON.stringify(_buttonMap.exportPixels())")))
        ev(f"_buttonMap.exportTo({json.dumps(url)}, {json.dumps(fmt)})")
        for _ in range(200):
            QtTest.QTest.qWait(50)
            if ev("_renderer.busy") is False and target.exists():
                break
        return [size["w"], size["h"], target.exists()]

    # The whole page, then a print area: the same scale, no paper.
    ev("_buttonMap.setPrint('paper', 'fit')")
    ev("_buttonMap.setPrint('scale', 50)")
    ev("_buttonMap._ed().clearPrintArea()")
    QtTest.QTest.qWait(300)
    out["full"] = export("full.png", "png")
    ev("_buttonMap.setPrint('scale', 200)")
    out["full-200"] = export("full-200.png", "png")
    ev("_buttonMap.setPrint('scale', 50)")
    area = {"fx": 0.25, "fy": 0.2, "fw": 0.5, "fh": 0.5}
    ev(f"_buttonMap._ed().printArea = {json.dumps(area)}; _buttonMap.printArea = _buttonMap._ed().printArea")
    QtTest.QTest.qWait(300)
    out["area"] = export("area.png", "png")
    out["light"] = None
    ev("_buttonMap.setPrint('light', true)")
    out["light"] = export("light.png", "png")
    ev("_buttonMap.setPrint('light', false)")
    ev("_buttonMap.setPrint('paper', 'letter')")
    out["pdf"] = export("letter.pdf", "pdf")
    # The map on screen was never put into export mode.
    out["live-exporting"] = ev("_buttonMap._ed().exporting")
    # Closed (its place kept), then the Button Map opened again: it stays
    # closed (restoring its place used to show it).
    pw.close()
    QtTest.QTest.qWait(300)
    win.close()
    QtTest.QTest.qWait(500)
    call(root, "openButtonMapForCard", card)
    QtTest.QTest.qWait(1200)
    out["shown-after-reopening"] = print_export_shown()
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
