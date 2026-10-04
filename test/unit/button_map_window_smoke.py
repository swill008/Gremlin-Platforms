# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Loads the Button Map window off-screen, with stand-ins for the program's
backend, and runs each step given in STEPS: a line of QML JavaScript in the
window's own scope. Prints "ERROR ..." for a failing step and "WARN ..." for
each QML warning, then "done". test_button_map_window.py runs it in its own
process.

    python test/unit/button_map_window_smoke.py <out_dir>
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest.mock
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import gremlin.util  # noqa: E402

# Settings and module files in a folder of their own, never the user's.
gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

# Each step: (name, JavaScript run in the window's scope).
STEPS = [
    ("template-name", "_templateNameDlg.open()"),
    ("templates", "_templateNameDlg.close(); _templatesDlg.open()"),
    ("copy",
     "_templatesDlg.close(); _buttonMap.openCopyLayout({name: 'Stick R', slug: 'x'})"),
    ("apply-template",
     "_copyDlg.close(); _buttonMap.openCopyLayout({name: 'Mine', template: true})"),
    ("style-name", "_copyDlg.close(); _buttonMap.askStyleName('shape', '{}')"),
    ("library",
     "_styleNameDlg.close();"
     " Qt.createComponent('OptionButtonMapLibrary.qml')"
     ".createObject(_buttonMap.contentItem).destroy()"),
    # The File menu with no device: only what can be used shows.
    ("file-menu",
     "_fileMenu.popup(0, 30);"
     " var shown = [];"
     " for (var i = 0; i < _fileMenu.count; i++) {"
     "   var it = _fileMenu.itemAt(i);"
     "   if (it.visible) shown.push(it.text === undefined ? '---' : it.text) }"
     " shown.join('|')"),
    ("photo-adjust", "_fileMenu.close(); _photoAdj.open()"),
    ("guide", "_photoAdj.close(); _buttonMap.openGuide()"),
    ("zoom",
     "_photoAdj.close(); _buttonMap.zoomToPage(); _buttonMap.zoomToSelection()"),
    ("closed", "_photoAdj.close(); _styleNameDlg.close()"),
]


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    propertyChanged = QtCore.Signal()
    activityChanged = QtCore.Signal()

    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)
    gremlinActive = QtCore.Property(
        bool, fget=lambda self: False, notify=activityChanged
    )
    currentMode = QtCore.Property(
        str, fget=lambda self: "Default", notify=propertyChanged
    )

    @QtCore.Slot(str)
    def noteSave(self, text: str) -> None:
        pass


class FakeUiState(QtCore.QObject):
    modeChanged = QtCore.Signal()
    currentMode = QtCore.Property(str, fget=lambda self: "Default", notify=modeChanged)


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])
    font = QtGui.QFont("Segoe UI")
    font.setPixelSize(15)
    app.setFont(font)
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    # The QML types the window uses, registered as the program does.
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.button_map_options  # noqa: F401
    import gremlin.ui.device_names  # noqa: F401
    import joystick_gremlin

    joystick_gremlin.register_config_options()

    backend = FakeBackend()
    ui_state = FakeUiState()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.load(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogJoystickButtonMap.qml"))
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
    else:
        win = roots[0]
        win.setProperty("width", 1400)
        win.setProperty("height", 900)
        win.setProperty("visible", True)
        QtTest.QTest.qWait(600)
        quick = shiboken6.wrapInstance(
            shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
        )
        for name, code in STEPS:
            expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
            value = expr.evaluate()
            if expr.hasError():
                print(f"ERROR {name}: {expr.error().toString()}", flush=True)
            elif isinstance(value, tuple) and value[0] not in (None, ""):
                print(f"RESULT {name} {value[0]}", flush=True)
            QtTest.QTest.qWait(250)
            quick.grabWindow().save(str(out / f"{name}.png"))
        # A real export on a light page: the page must come out white. A
        # device that is not plugged in still gets a map to export.
        device = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "_buttonMap.targetGuid = '12345678-1234-1234-1234-123456789abc';"
            " _buttonMap.targetName = 'Smoke Stick'",
        )
        device.evaluate()
        QtTest.QTest.qWait(800)
        target = out / "light-export.png"
        url = QtCore.QUrl.fromLocalFile(str(target)).toString()
        code = (
            "_buttonMap.setPrint('light', true);"
            f" _buttonMap.exportTo('{url}', 'png')"
        )
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        expr.evaluate()
        if expr.hasError():
            print(f"ERROR light-export: {expr.error().toString()}", flush=True)
        for _ in range(100):
            QtTest.QTest.qWait(50)
            if target.exists():
                break
        image = QtGui.QImage(str(target))
        if image.isNull():
            print("ERROR light-export: nothing written", flush=True)
        else:
            corner = image.pixelColor(2, 2).name()
            print(f"LIGHT {corner}", flush=True)
            if corner != "#ffffff":
                print(f"ERROR light-export: page corner is {corner}", flush=True)
        reset = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win, "_buttonMap.setPrint('light', false)"
        )
        reset.evaluate()
        menu = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "_fileMenu.popup(0, 30); var shown = [];"
            " for (var i = 0; i < _fileMenu.count; i++) {"
            "   var it = _fileMenu.itemAt(i);"
            "   if (it.visible) shown.push(it.text === undefined ? '---' : it.text) }"
            " _fileMenu.close(); shown.join('|')",
        )
        print(f"RESULT file-menu-device {menu.evaluate()[0]}", flush=True)
        QtTest.QTest.qWait(200)
        # Cancel leaves no undo steps: an edit, then Cancel, then nothing
        # to undo (the Edit menu's Undo too).
        edit = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "_buttonMap.enterEdit(); var e = _ed(); e.seedHist();"
            " e.nodes.push({id: 'smoke_box', kind: 'draw', shape: 'rect',"
            " x: 0.1, y: 0.1, w: 0.1, h: 0.1}); e.bump(); String(e.canUndo)",
        )
        before = edit.evaluate()[0]
        QtTest.QTest.qWait(300)
        cancel = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win, "_buttonMap.discardEdit(); 'ok'"
        )
        cancel.evaluate()
        QtTest.QTest.qWait(300)
        after = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win, "String(_ed().canUndo)"
        ).evaluate()[0]
        print(f"RESULT undo-after-cancel {before} {after}", flush=True)
        # A map file without a photo frame value opens as it is: no
        # rescale, and the file is not rewritten. Written here directly,
        # since the program's own save always adds the frame value.
        where = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "_hw.load(_buttonMap.targetName); _hw.path",
        ).evaluate()[0]
        plain_doc = {
            "kind": "control.hardware",
            "device": "Smoke Stick",
            "image": "",
            "nodes": [{
                "id": "p1", "kind": "draw", "shape": "rect",
                "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1, "fx": 0.1, "fy": 0.2,
            }],
        }
        plain_text = json.dumps(plain_doc)
        Path(where).parent.mkdir(parents=True, exist_ok=True)
        Path(where).write_text(plain_text, encoding="utf-8")
        plain = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "_buttonMap.loadLive();"
            " String(JSON.stringify(_buttonMap.liveNodes) === "
            + json.dumps(json.dumps(plain_doc["nodes"], separators=(",", ":")))
            + ")",
        )
        value = plain.evaluate()
        QtTest.QTest.qWait(200)
        untouched = Path(where).read_text(encoding="utf-8") == plain_text
        if plain.hasError():
            print(f"ERROR plain-file: {plain.error().toString()}", flush=True)
        else:
            print(f"RESULT plain-file {value[0]} {str(untouched).lower()}", flush=True)
        # Pictures: a copied picture file pastes with Ctrl+V's choice (the
        # clipboard changed after the last chip copy), and a dropped file
        # lands centred on the drop point with the picture's own shape.
        wide = QtGui.QImage(400, 100, QtGui.QImage.Format.Format_RGB32)
        wide.fill(QtGui.QColor("#336699"))
        wide_path = out / "wide.png"
        wide.save(str(wide_path))
        QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "_buttonMap.enterEdit(); _ed().copySelection(); 1",
        ).evaluate()
        QtTest.QTest.qWait(300)
        mime = QtCore.QMimeData()
        mime.setUrls([QtCore.QUrl.fromLocalFile(str(wide_path))])
        QtGui.QGuiApplication.clipboard().setMimeData(mime)
        QtTest.QTest.qWait(300)
        pasted = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "var e = _ed(); var before = e.nodes.length; e.pasteClipboard();"
            " var n = e.nodeAt(e.selectedId);"
            " (e.nodes.length - before) + ' ' + (n ? n.shape : '-')",
        ).evaluate()[0]
        print(f"RESULT paste-picture {pasted}", flush=True)
        dropped = QtQml.QQmlExpression(
            QtQml.qmlContext(win), win,
            "var e = _ed(); var at = Qt.point(e.fxToX(0.3), e.fyToY(0.6));"
            " var ok = _buttonMap.dropPictures(['"
            + QtCore.QUrl.fromLocalFile(str(wide_path)).toString()
            + "'], at.x, at.y, e);"
            " var n = e.nodeAt(e.selectedId); var s = e.spaceRect();"
            " var cx = n.fx + n.fw / 2; var cy = n.fy + n.fh / 2;"
            " var shape = (n.fw * s.w) / (n.fh * s.h);"
            " ok + ' ' + cx.toFixed(2) + ' ' + cy.toFixed(2) + ' ' + shape.toFixed(1)",
        ).evaluate()[0]
        print(f"RESULT drop-picture {dropped}", flush=True)
        QtQml.QQmlExpression(
            QtQml.qmlContext(win), win, "_buttonMap.discardEdit(); 1"
        ).evaluate()
        QtTest.QTest.qWait(300)

        def js(code: str) -> str:
            expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
            value = expr.evaluate()[0]
            if expr.hasError():
                return "ERROR " + expr.error().toString()
            return str(value)

        # Entering Edit changes nothing: no undo step, no unsaved changes
        # (BM11; the map has a drawing without a name).
        js("_buttonMap.loadLive(); _buttonMap.enterEdit(); 1")
        QtTest.QTest.qWait(600)
        print(
            "RESULT edit-is-clean "
            + js("String(_buttonMap.isDirty()) + ' ' + String(_ed().canUndo)"),
            flush=True,
        )
        js("_buttonMap.discardEdit(); 1")
        QtTest.QTest.qWait(300)
        # Copy Button Map from Device outside Edit: Undo brings the map that
        # was there back (BM9).
        Path(where).with_name("copysrc.json").write_text(json.dumps({
            "device": "Copy Src",
            "nodes": [{"id": "c1", "kind": "draw", "shape": "rect",
                       "fx": 0.5, "fy": 0.5, "fw": 0.1, "fh": 0.1}],
        }), encoding="utf-8")
        js("_buttonMap.copyLayoutFrom({name: 'Copy Src', slug: 'copysrc'}, false); 1")
        QtTest.QTest.qWait(600)
        ids = "function ids() { return _ed().nodes.map(function(n) { return n.id })"
        copied = js(f"{ids}.join(',') }}; ids()")
        undone = js(f"{ids}.join(',') }}; _ed().undo(); ids()")
        print(f"RESULT copy-undo {copied} {undone}", flush=True)
        js("_buttonMap.discardEdit(); 1")
        QtTest.QTest.qWait(300)
        # Ctrl+S while a text box's text is being typed saves the typed text
        # (BM15).
        js("_buttonMap.enterEdit(); var e = _ed();"
           " e.nodes.push({id: 't1', kind: 'draw', shape: 'text', text: 'old',"
           " fx: 0.2, fy: 0.2, fw: 0.2, fh: 0.05}); e.bump();"
           " e.beginTextRename('t1'); e.renameDraft = 'typed'; 1")
        QtTest.QTest.qWait(300)
        js("_buttonMap.saveEdit(false); 1")
        QtTest.QTest.qWait(300)
        saved = json.loads(Path(where).read_text(encoding="utf-8"))
        texts = [n.get("text") for n in saved.get("nodes", []) if n.get("id") == "t1"]
        print(f"RESULT save-while-typing {texts}", flush=True)
        # The colour picker takes a typed hex (#RGB too), and follows the
        # theme (BM17, E5).
        typed = js("_colorPop.openField('color', '#112233', null);"
                   " _hexField.text = 'abc'; _hexField.take();"
                   " var r = _buttonMap._toHex(_colorPop.live) + ' ' + _hexField.text;"
                   " _colorPop.close(); r")
        print(f"RESULT typed-hex {typed}", flush=True)
    for warning in warnings:
        print("WARN " + warning.encode("ascii", "replace").decode(), flush=True)
    print("done", flush=True)
    # os._exit skips Qt's teardown, which can hang off-screen.
    os._exit(0)


if __name__ == "__main__":
    main()
