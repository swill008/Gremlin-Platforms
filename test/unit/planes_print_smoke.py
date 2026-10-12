# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) with a device map whose
background holds one plain red picture (800 x 400 pixels, in a box of its
own proportions, 07 S140) and whose
foreground holds a chip, opens Print & Export and exports PNGs into the
folder given: at 100% and 50%, with the screen's plane view settings
turned down, without Include background, and on a Light page. Prints what
it found as JSON. test_planes_print.py runs it in its own process with a
fresh user folder.

With "big" the picture is 4200 x 300 pixels of 4-pixel red and black
stripes instead (over the 4000-pixel screen-copy limit, 07 S124), and only
a 100% export is made: printed from the original, the stripes stay sharp.

With "dense" a second, green picture (400 x 400 pixels) sits above the red
one in a small box at the page's top-left corner, so it has 3.75 times the
red picture's pixels per unit of the page, and a third, blue one, even
denser, is hidden; 100% and 50% exports are made (07 S83 as changed,
D-07-BG-COMPOSITE: 100% is the most detailed visible background picture's
own pixels, hidden pictures left out).

    python test/unit/planes_print_smoke.py <folder> [big|dense]
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.modules import store  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
BIG = len(sys.argv) > 2 and sys.argv[2] == "big"
DENSE = len(sys.argv) > 2 and sys.argv[2] == "dense"
NATURAL = (4200, 300) if BIG else (800, 400)

_map = store.module_file_in(store.ensure_device_dir("pJoy Pro", GUID))
(_map.parent / "pictures").mkdir(exist_ok=True)
_red = QtGui.QImage(NATURAL[0], NATURAL[1], QtGui.QImage.Format.Format_RGB32)
_red.fill(QtGui.QColor(255, 0, 0))
if BIG:
    _paint = QtGui.QPainter(_red)
    for _x in range(4, NATURAL[0], 8):
        _paint.fillRect(_x, 0, 4, NATURAL[1], QtGui.QColor(0, 0, 0))
    _paint.end()
_red.save(str(_map.parent / "pictures" / "bg.png"))
# The picture's box has the picture's own proportions, as the program places
# a new picture (rig_overlays.js frameFit: the photo frame, 0.75 of the 16:9
# page, narrowed to the picture). The picture fills its box exactly (07 S140),
# so a box of other proportions would stretch it.

def _square(name: str, side: int, color: QtGui.QColor) -> None:
    pic = QtGui.QImage(side, side, QtGui.QImage.Format.Format_RGB32)
    pic.fill(color)
    pic.save(str(_map.parent / "pictures" / name))


# A square box fw wide in page fractions (the page is 16:9).
def _box(fx: float, fy: float, fw: float) -> dict:
    return {"fx": fx, "fy": fy, "fw": fw, "fh": fw * 16 / 9}


_dense: list = []
if DENSE:
    _square("dense.png", 400, QtGui.QColor(0, 255, 0))
    _square("hidden.png", 400, QtGui.QColor(0, 0, 255))
    # 400 pixels across 0.1 of the page against the red 800 across 0.75:
    # 3.75 times the detail. The hidden one (0.05 of the page) would be 7.5.
    _dense = [
        {"kind": "draw", "id": "bg2", "shape": "image", "plane": "background",
         "src": "pictures/dense.png", **_box(0.01, 0.01, 0.1), "rot": 0,
         "opacity": 1, "locked": False, "pinned": False, "sockets": [],
         "fill": "filled"},
        {"kind": "draw", "id": "bg3", "shape": "image", "plane": "background",
         "src": "pictures/hidden.png", **_box(0.94, 0.01, 0.05), "rot": 0,
         "opacity": 1, "locked": False, "pinned": False, "sockets": [],
         "fill": "filled", "hidden": True},
    ]
_aspect = NATURAL[0] / NATURAL[1]
_fw, _fh = 0.75, 0.75
if _aspect > 16 / 9:
    _fh = _fw * (16 / 9) / _aspect
else:
    _fw = _fh * _aspect / (16 / 9)
_map.write_text(json.dumps({
    "kind": "control.hardware", "device": "pJoy Pro",
    "nodes": [
        # The bottom background picture, in the photo frame.
        {"kind": "draw", "id": "bg1", "shape": "image", "plane": "background",
         "src": "pictures/bg.png", "fx": 0.125 + (0.75 - _fw) / 2,
         "fy": 0.125 + (0.75 - _fh) / 2, "fw": _fw, "fh": _fh, "rot": 0,
         "opacity": 1, "locked": False, "pinned": False,
         "sockets": [], "fill": "filled"},
        *_dense,
        {"kind": "btn", "id": "b1", "label": "Button 1",
         "chipFx": 0.05, "chipFy": 0.05},
    ],
}), encoding="utf-8")


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def red_box(path: Path) -> dict:
    """Size of the image, how many strong red points a 7-pixel grid finds
    (not 8: the big picture's stripes repeat every 8), and the red run's
    exact width and height through the red area's middle, with the colour
    there."""
    img = QtGui.QImage(str(path))
    if img.isNull():
        return {"missing": True}
    img = img.convertToFormat(QtGui.QImage.Format.Format_RGB32)

    def red(x: int, y: int) -> bool:
        c = img.pixelColor(x, y)
        return c.red() > 200 and c.green() < 60 and c.blue() < 60

    pts = [(x, y) for y in range(0, img.height(), 7)
           for x in range(0, img.width(), 7) if red(x, y)]
    out: dict = {"size": [img.width(), img.height()], "red": len(pts)}
    if pts:
        cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) // 2
        cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) // 2
        row = [x for x in range(img.width()) if red(x, cy)]
        # A red column near the middle (the big picture has black stripes).
        if row:
            cx = min(row, key=lambda x: abs(x - cx))
        col = [y for y in range(img.height()) if red(cx, y)]
        mid = img.pixelColor(cx, cy)
        out["box"] = [max(row) - min(row) + 1 if row else 0,
                      max(col) - min(col) + 1 if col else 0]
        # Near-black points on the middle row, between the first and last
        # red: the big picture's stripes, when drawn sharp.
        if row:
            span = range(min(row), max(row) + 1)
            dark = [x for x in span if img.pixelColor(x, cy).red() < 60]
            out["dark-share"] = round(len(dark) / max(1, len(span)), 3)
        out["middle"] = [mid.red(), mid.green(), mid.blue()]
    return out


def main() -> None:
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_until(lambda: app.engine.rootObjects(), "the main window")[0]
    out: dict = {}
    # Binding loops in Print & Export (its export size once read a picture
    # it changed while working that size out). engine.warnings, not a Qt
    # message handler (gremlin/qt_log.py).
    loops: list[str] = []

    def warned(found: list) -> None:
        for w in found:
            text = w.toString()
            if "Binding loop" in text and "PrintExportWindow" in text:
                loops.append(text)

    app.engine.warnings.connect(warned)
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openDeviceMappingEditorForCard", card)
    win = wait_until(
        lambda: (w := call(root, "deviceMappingEditorWindow")) is not None
        and w.property("visible") and w,
        "the Device Mapping Editor",
    )
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
    wait_until(lambda: ev("editing") is True, "Edit on", fail=False)
    ev("_editorWin.openPrintExport()")
    pw = wait_until(
        lambda: next((
        w for w in QtGui.QGuiApplication.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow) and w.title() == "Print & Export"
        ), None),
        "the Print & Export window",
    )

    def child(name: str) -> QtCore.QObject:
        return pw.findChild(QtCore.QObject, name)

    # The window's words (glossary: Page, Include background).
    page = child("printPage")
    tick = child("printIncludeBg")
    out["page-label"] = page.property("text") if page else None
    out["tick"] = [tick.property("text"), tick.property("checked")] if tick else None
    out["setup-default"] = ev("_editorWin.printSetup.includeBg !== false")
    # The snapshot the renderer draws from carries no photo keys.
    out["snapshot-keys"] = ev(
        "var s = _renderer.snapshot(_editorWin._ed(), true);"
        " JSON.stringify(Object.keys(s)) + JSON.stringify(Object.keys(s.props))")

    saved: list = []
    ev("_hw").areaSaved.connect(lambda ok, error: saved.append([ok, error]))

    def export(name: str) -> dict:
        target = folder / name
        url = QtCore.QUrl.fromLocalFile(str(target)).toString()
        count = len(saved) + 1
        ev(f"_editorWin.exportTo({json.dumps(url)}, 'png')")
        wait_until(
            lambda: len(saved) >= count and ev("_editorWin.exportBusy") is False,
            f"{name} exported",
            timeout_ms=10000,
            fail=False,
        )
        return red_box(target)

    ev("_editorWin.setPrint('paper', 'fit')")
    ev("_editorWin._ed().clearPrintArea()")
    ev("_editorWin.setPrint('scale', 100)")
    QtTest.QTest.qWait(300)
    out["full-100"] = export("full-100.png")
    if BIG:
        out["screen-side"] = ev("Screen.width")
        pw.close()
        win.close()
        QtTest.QTest.qWait(300)
        print("RESULT " + json.dumps(out), flush=True)
        smoke_exit(0)
    ev("_editorWin.setPrint('scale', 50)")
    QtTest.QTest.qWait(200)
    out["full-50"] = export("full-50.png")
    if DENSE:
        out["export-pixels"] = ev("JSON.stringify(_editorWin.exportPixels())")
        pw.close()
        win.close()
        QtTest.QTest.qWait(300)
        print("RESULT " + json.dumps(out), flush=True)
        smoke_exit(0)

    # Screen-only views turned down: the print is unchanged (07 S87, S120).
    # The live values are read as each picture is asked for.
    views = ("var e = _editorWin._ed(); JSON.stringify([e.editPlane,"
             " e.showFgFaint, e.bgViewHidden, e.bgViewOpacity])")
    # Background mode first: entering it puts the program's view settings
    # back on the editor.
    ev("_editorWin._ed().editPlane = 'background'")
    QtTest.QTest.qWait(300)
    ev("var e = _editorWin._ed(); e.bgViewOpacity = 0.2; e.showFgFaint = true")
    QtTest.QTest.qWait(300)
    out["live-views-down"] = ev(views)
    out["views-down"] = export("views-down.png")
    ev("_editorWin._ed().bgViewHidden = true")
    QtTest.QTest.qWait(300)
    out["live-bg-hidden"] = ev(views)
    out["bg-hidden-view"] = export("bg-hidden-view.png")
    ev("var e = _editorWin._ed(); e.bgViewHidden = false; e.bgViewOpacity = 1;"
       " e.showFgFaint = true; e.editPlane = 'foreground'")

    # Include background off, through the tick: no background.
    QtCore.QMetaObject.invokeMethod(tick, "click")
    wait_until(
        lambda: not tick.property("checked"), "Include background off", fail=False
    )
    out["tick-off"] = [tick.property("checked"), ev("_editorWin.printSetup.includeBg")]
    out["no-bg"] = export("no-bg.png")
    QtCore.QMetaObject.invokeMethod(tick, "click")
    wait_until(lambda: tick.property("checked"), "Include background on", fail=False)
    out["tick-on"] = [tick.property("checked"), ev("_editorWin.printSetup.includeBg")]

    # Light page: pictures unchanged (07 S89).
    ev("_editorWin.setPrint('light', true)")
    QtTest.QTest.qWait(200)
    out["light"] = export("light.png")
    ev("_editorWin.setPrint('light', false)")
    out["live-exporting"] = ev("_editorWin._ed().exporting")
    out["binding-loops"] = loops[:5]
    pw.close()
    win.close()
    QtTest.QTest.qWait(300)
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        smoke_exit(1)
