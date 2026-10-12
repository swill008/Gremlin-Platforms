# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The pan cursor in the Device Mapping Editor window, off-screen (07 S14;
D-07-PAN-CURSOR).

Loads the real window (stand-ins from planes_window_smoke.py), drags with the
middle button in Edit, the left button outside Edit and Space + left in Edit,
and prints "RESULT <name> <cursor shapes>" lines (the window's cursor before,
during and after each drag), "WARN ..." per QML warning, then "done".
test_pan_cursor.py runs it in its own process.

    python test/unit/pan_cursor_smoke.py <out_dir>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import planes_window_smoke as pws  # sets the off-screen platform and profile
from smoke_exit import smoke_exit

# The fake driver: its "pJoy Pro" is plugged in, so outside Edit the map
# shows (an unplugged stick's map is covered).
_spec = importlib.util.spec_from_file_location(
    "fake_hardware", pws.ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import dill  # noqa: E402

pws.DEVICE = "pJoy Pro"
pws.GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

ROOT = pws.ROOT
Btn = QtCore.Qt.MouseButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841  (kept alive)
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style",
        1,
        0,
        "Style",
    )
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.device_map_options  # noqa: F401
    import gremlin.ui.device_names  # noqa: F401
    import joystick_gremlin

    joystick_gremlin.register_config_options()
    pws._write_maps(out)

    backend = pws.FakeBackend()
    ui_state = pws.FakeUiState()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.load(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogDeviceMappingEditor.qml"))
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        print("done", flush=True)
        smoke_exit(0)
    win = roots[0]
    win.setProperty("width", 1400)
    win.setProperty("height", 900)
    win.setProperty("visible", True)
    QtTest.QTest.qWait(500)
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )

    def js(code: str) -> str:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()[0]
        if expr.hasError():
            return "ERROR " + expr.error().toString()
        return str(value)

    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {value}", flush=True)

    def wait(ms: int = 300) -> None:
        QtTest.QTest.qWait(ms)

    def shape() -> str:
        return quick.cursor().shape().name

    def centre() -> tuple[int, int]:
        text = js(
            "var f = _ed().face; var p = f.mapToItem(null, f.width / 2, f.height / 2);"
            " Math.round(p.x) + ',' + Math.round(p.y)"
        )
        x, y = (int(v) for v in text.split(","))
        return x, y

    def drag(button: Btn) -> str:
        """Hover, press, drag, release; the cursor at each stage and whether
        the view panned."""
        x, y = centre()
        pan = "var f = _ed().face; f.panX.toFixed(0) + ',' + f.panY.toFixed(0)"
        before_pan = js(pan)
        QtTest.QTest.mouseMove(quick, QtCore.QPoint(x - 5, y - 5))
        wait(60)
        QtTest.QTest.mouseMove(quick, QtCore.QPoint(x, y))
        wait(60)
        before = shape()
        QtTest.QTest.mousePress(quick, button, NoMod, QtCore.QPoint(x, y))
        for step in range(1, 6):
            QtTest.QTest.mouseMove(quick, QtCore.QPoint(x + step * 12, y + step * 6))
            wait(30)
        during = shape()
        QtTest.QTest.mouseRelease(quick, button, NoMod, QtCore.QPoint(x + 60, y + 30))
        wait(60)
        QtTest.QTest.mouseMove(quick, QtCore.QPoint(x + 62, y + 31))
        wait(60)
        after = shape()
        return f"{before} {during} {after} {before_pan != js(pan)}"

    js(f"_editorWin.openForDevice('{pws.DEVICE}', '{pws.GUID}'); 1")
    wait(800)
    quick.requestActivate()
    wait()

    # Outside Edit: a left-drag pans with a closed hand.
    result("left-view", drag(Btn.LeftButton))
    result("middle-view", drag(Btn.MiddleButton))

    # In Edit: a middle-drag pans with a closed hand, over the editor.
    js("_editorWin.enterEdit(); 1")
    wait(800)
    result("middle-edit", drag(Btn.MiddleButton))

    # In Edit with Space held: open hand, closed while dragging.
    x, y = centre()
    QtTest.QTest.keyPress(quick, QtCore.Qt.Key.Key_Space)
    wait(100)
    QtTest.QTest.mouseMove(quick, QtCore.QPoint(x + 1, y + 1))
    wait(60)
    result("space-held", shape())
    result("space-drag", drag(Btn.LeftButton))
    QtTest.QTest.keyRelease(quick, QtCore.Qt.Key.Key_Space)
    wait(100)
    QtTest.QTest.mouseMove(quick, QtCore.QPoint(x + 2, y + 2))
    wait(60)
    result("space-released", shape())
    js("_editorWin.discardEdit(); 1")
    wait(300)

    for warning in warnings:
        print("WARN " + warning.encode("ascii", "replace").decode(), flush=True)
    print("done", flush=True)
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
