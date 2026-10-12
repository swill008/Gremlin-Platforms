# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor window's background and foreground planes, off-screen
(07 S113-S117, S14, S30, S39-S42, S57, S76; D-07-PLANES-ANSWERS P4a).

Loads the real window with stand-ins for the program's backend, opens a
device whose map has a foreground chip and a background picture, and prints
one "RESULT <name> <value>" line per check, "WARN ..." for each QML warning
and "ERROR ..." for a failing step, then "done". test_planes_window.py runs
it in its own process.

    python test/unit/planes_window_smoke.py <out_dir>
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest.mock
from pathlib import Path

from smoke_exit import smoke_exit

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))

import gremlin.util  # noqa: E402

# Settings and module files in a folder of their own, never the user's.
gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

DEVICE = "Planes Stick"
GUID = "12345678-1234-1234-1234-1234567890ab"


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


def _picture(path: Path, w: int, h: int, colour: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = QtGui.QImage(w, h, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(colour))
    image.save(str(path))


def _write_maps(out: Path) -> Path:
    """This device's map (a chip and a background picture) and another
    device's (a chip and a background shape) to copy from."""
    from gremlin.modules import store

    folder = store.ensure_device_dir(DEVICE)
    _picture(folder / "pictures" / "bg.png", 400, 200, "#336699")
    doc = {
        "kind": "control.hardware",
        "device": DEVICE,
        "nodes": [
            {
                "id": "bg1",
                "kind": "draw",
                "shape": "image",
                "plane": "background",
                "src": "pictures/bg.png",
                "fx": 0.1,
                "fy": 0.1,
                "fw": 0.8,
                "fh": 0.8,
                "rot": 0,
                "opacity": 1,
                "look": {"bright": 0.3},
            },
            {
                "id": "fg1",
                "kind": "draw",
                "shape": "rect",
                "fx": 0.4,
                "fy": 0.4,
                "fw": 0.1,
                "fh": 0.1,
            },
        ],
    }
    target = store.module_file_in(folder)
    target.write_text(json.dumps(doc), encoding="utf-8")
    other = store.ensure_device_dir("Copy Src")
    store.module_file_in(other).write_text(
        json.dumps(
            {
                "device": "Copy Src",
                "nodes": [
                    {
                        "id": "sbg",
                        "kind": "draw",
                        "shape": "rect",
                        "plane": "background",
                        "fx": 0.0,
                        "fy": 0.0,
                        "fw": 0.2,
                        "fh": 0.2,
                    },
                    {
                        "id": "c1",
                        "kind": "draw",
                        "shape": "rect",
                        "fx": 0.5,
                        "fy": 0.5,
                        "fw": 0.1,
                        "fh": 0.1,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    _picture(out / "added.png", 300, 300, "#993366")
    return target


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])
    font = QtGui.QFont("Segoe UI")
    font.setPixelSize(15)
    app.setFont(font)
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
    target = _write_maps(out)

    backend = FakeBackend()
    ui_state = FakeUiState()
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

    def child(name: str) -> QtCore.QObject:
        return win.findChild(QtCore.QObject, name)

    def wait(ms: int = 300) -> None:
        QtTest.QTest.qWait(ms)

    # Old code had a Photo menu, Adjust Photo… popup and Move/Reset Photo.
    result("photo-adjust-gone", js("typeof _photoAdj === 'undefined'"))
    result("photo-menu-gone", js("typeof _photoMenu === 'undefined'"))

    js(f"_editorWin.openForDevice('{DEVICE}', '{GUID}'); 1")
    wait(800)
    # The background menu: shown, its items only while editing (07 S39).
    result(
        "bg-menu",
        js(
            "var m = _bgMenu; var t = [];"
            " for (var i = 0; i < m.count; i++) { var it = m.itemAt(i);"
            " if (it.text !== undefined) t.push(it.text) }"
            " m.title + '|' + m.enabled + '|' + t.join('|')"
        ),
    )
    result("bottom-photo", js("_editorWin.photoOverride.indexOf('bg.png') >= 0"))

    js("_editorWin.enterEdit(); 1")
    wait_until(lambda: js("_bgMenu.enabled") == "True", "Edit on", fail=False)
    result("bg-menu-editing", js("_bgMenu.enabled"))
    result("plane-start", js("_ed().editPlane + ' ' + _editorWin.bgMode"))
    result("status-fg", child("dmePlaneStatus").property("text"))
    # A picture's look shows from an adjusted copy (07 S43).
    result(
        "look",
        js(
            "var n = _ed().nodeAt('bg1');"
            " String(!!n && String(n.lookUrl || '').length > 0)"
        ),
    )
    # Move to Background says so with Undo (07 S121); Undo moves it back.
    result(
        "moved",
        js(
            "var e = _ed(); e.moveToPlane(['fg1'], 'background');"
            " var t = _messageLine.text + '|' + _messageLine.undoText;"
            " e.undo(); t + '|' + (e.nodeAt('fg1').plane || 'foreground')"
        ),
    )
    wait()

    # Edit Background (the editor's editPlane; the window follows): banner,
    # Done, the first-time hint. No switch, no Undo / Redo row (07 S113).
    js("_ed().editPlane = 'background'; 1")
    wait()
    banner = child("dmeBgBanner")
    result(
        "banner",
        f"{banner.property('visible')} "
        f"{child('dmeBgBannerText').property('text')}|{child('dmeBgDone').property('text')}",
    )
    result(
        "hint-first",
        f"{child('dmeBgHint').property('visible')} "
        f"{js('_opts.values["bm-bg-hint-seen"]')}",
    )
    result("status-bg", child("dmePlaneStatus").property("text"))
    result(
        "no-switch",
        f"{child('dmePlaneSwitch') is None} {child('dmePlane_background') is None} "
        f"{child('dmePlane_foreground') is None} "
        f"{child('deviceMappingEditorUndoBar') is None}",
    )
    # Done leaves; entering again shows no hint (once for the program).
    js("_ed().editPlane = 'foreground'; 1")
    wait()
    result("after-done", f"{js('_ed().editPlane')} {banner.property('visible')}")
    js("_editorWin.setEditPlane('background'); 1")
    wait()
    result("hint-second", child("dmeBgHint").property("visible"))

    # Esc leaves Background mode when nothing else takes it.
    js("_ed().setSelection([]); 1")
    wait()
    quick.requestActivate()
    wait()
    plane = js("_ed().editPlane")
    QtTest.QTest.keyClick(quick, QtCore.Qt.Key.Key_Escape)
    wait_until(lambda: js("_ed().editPlane") != plane, "Esc left the plane", fail=False)
    result("esc", js("_ed().editPlane"))
    plane = js("_ed().editPlane")
    # Ctrl+B toggles it.
    QtTest.QTest.keyClick(
        quick, QtCore.Qt.Key.Key_B, QtCore.Qt.KeyboardModifier.ControlModifier
    )
    wait_until(lambda: js("_ed().editPlane") != plane, "Ctrl+B", fail=False)
    result("ctrl-b", js("_ed().editPlane"))
    QtTest.QTest.keyClick(
        quick, QtCore.Qt.Key.Key_B, QtCore.Qt.KeyboardModifier.ControlModifier
    )
    wait_until(lambda: js("_ed().editPlane") == plane, "Ctrl+B back", fail=False)
    result("ctrl-b-back", js("_ed().editPlane"))

    # Ctrl+Shift+B moves the selection to the other plane, and back (07 S121).
    js("_ed().setSelection(['fg1']); 1")
    wait()
    shift_ctrl = (
        QtCore.Qt.KeyboardModifier.ControlModifier
        | QtCore.Qt.KeyboardModifier.ShiftModifier
    )
    QtTest.QTest.keyClick(quick, QtCore.Qt.Key.Key_B, shift_ctrl)
    wait()
    to_bg = js("(_ed().nodeAt('fg1').plane || 'foreground') + '|' + _messageLine.text")
    js("_ed().setSelection(['fg1']); 1")
    QtTest.QTest.keyClick(quick, QtCore.Qt.Key.Key_B, shift_ctrl)
    wait()
    to_fg = js("(_ed().nodeAt('fg1').plane || 'foreground') + '|' + _messageLine.text")
    result("ctrl-shift-b", f"{to_bg}|{to_fg}")
    js("_ed().setSelection([]); 1")
    wait()

    # Program settings follow the editor and the editor follows them.
    js("_opts.set('bm-fg-faint', false); 1")
    wait()
    result(
        "faint-off",
        f"{js('_ed().showFgFaint')} {child('dmeFgFaintTick').property('checked')}",
    )
    js("_ed().showFgFaint = true; 1")
    wait()
    result("faint-kept", js("_opts.values['bm-fg-faint']"))
    js("_ed().bgViewHidden = true; 1")
    wait()
    result(
        "hidden-kept",
        f"{js('_opts.values["bm-bg-hidden"]')} "
        f"{child('dmePlaneStatus').property('text')}",
    )
    js("_ed().bgViewHidden = false; _ed().bgViewOpacity = 0.4; 1")
    wait(600)
    result("opacity-kept", js("_opts.values['bm-bg-opacity'].toFixed(2)"))
    js("_opts.set('bm-bg-opacity', 1.0); 1")
    wait()
    result("opacity-applied", js("_ed().bgViewOpacity.toFixed(2)"))
    # A slider value not kept yet survives another setting changing (PG).
    js("_ed().bgViewOpacity = 0.2; _opts.set('bm-fg-faint', true); 1")
    wait(600)
    result(
        "opacity-pending",
        js(
            "_ed().bgViewOpacity.toFixed(2) + ' '"
            " + _opts.values['bm-bg-opacity'].toFixed(2)"
        ),
    )
    js("_opts.set('bm-bg-opacity', 1.0); 1")
    wait()

    # Add Picture to Background…: the top background layer, fitted to the
    # photo frame, one Undo step, an unsaved change (07 S30, S40).
    added_url = QtCore.QUrl.fromLocalFile(str(out / "added.png")).toString()
    result("clean-before", js("_editorWin.isDirty()"))
    js("_ed().seedHist(); 1")
    wait()
    added = js(f"_editorWin.addBackgroundPicture('{added_url}')")
    wait()
    result(
        "added",
        js(
            f"var e = _ed(); var ids = e.nodes.map(function(n) {{ return n.id }});"
            f" var i = ids.indexOf('{added}'); var n = e.nodes[i];"
            " var lastBg = -1; for (var k = 0; k < e.nodes.length; k++)"
            " if (e.nodes[k].plane === 'background') lastBg = k;"
            " var f = e.frameFit(1);"
            " n.plane + ' ' + (i === lastBg) + ' '"
            " + (Math.abs(n.fw - f.fw) < 0.001 && Math.abs(n.fh - f.fh) < 0.001)"
        ),
    )
    result("dirty-after-add", js("_editorWin.isDirty()"))
    result(
        "add-undo",
        js(
            f"var e = _ed(); e.undo(); var n = e.nodeAt('{added}');"
            " String(n === null || n === undefined)"
        ),
    )
    js("_ed().redo(); 1")
    wait()

    # Clear Background: every background layer, one step, no question.
    result(
        "clear",
        js(
            "function isBg(n) { return n.plane === 'background' }"
            " var e = _ed(); _editorWin.clearBackground();"
            " var bg = e.nodes.filter(isBg).length;"
            " var fg = e.nodes.length - bg;"
            " e.undo();"
            " var back = e.nodes.filter(isBg).length;"
            " bg + ' ' + fg + ' ' + back"
        ),
    )
    wait()

    # Save writes both planes in the nodes and no photo of its own.
    js("_editorWin.saveEdit(false); 1")
    wait()
    saved = json.loads(target.read_text(encoding="utf-8"))
    planes = sorted({n.get("plane", "foreground") for n in saved.get("nodes", [])})
    result(
        "saved",
        f"{'image' in saved} {'photo' in saved} {'|'.join(planes)} "
        f"{'bm-' in json.dumps(saved.get('ui', {}))}",
    )

    # Cancel puts the saved map (both planes) back.
    js("var e = _ed(); _editorWin.clearBackground(); 1")
    wait()
    js("_editorWin.discardEdit(); 1")
    wait(500)
    result(
        "cancel",
        js(
            "function isBg(n) { return n.plane === 'background' }"
            " _editorWin.liveNodes.filter(isBg).length > 0"
            " && _editorWin.editing === false"
        ),
    )
    result("plane-after-edit", js("_ed().editPlane"))

    # Copy Device Map: this device's background stays unless ticked.
    def ids() -> str:
        return js(
            "_ed().nodes.map(function(n) { return n.id + ':' + (n.plane || 'fg') })"
            ".sort().join(',')"
        )

    js("_editorWin.openCopyLayout({name: 'Copy Src', slug: 'Copy Src'}); 1")
    wait()
    result(
        "copy-tick",
        f"{child('dmeCopyBgTick').property('text')}|"
        f"{child('dmeCopyBgTick').property('checked')}",
    )
    js("_copyDlg.close(); 1")
    js(
        "_editorWin.copyLayoutFrom({name: 'Copy Src', slug: 'Copy Src'},"
        " false, false); 1"
    )
    wait(800)
    result("copy-keep", ids())
    js("_editorWin.discardEdit(); 1")
    wait(400)
    js(
        "_editorWin.copyLayoutFrom({name: 'Copy Src', slug: 'Copy Src'},"
        " true, false); 1"
    )
    wait(800)
    result("copy-keep-mirror", ids())
    js("_editorWin.discardEdit(); 1")
    wait(400)
    js(
        "_editorWin.copyLayoutFrom({name: 'Copy Src', slug: 'Copy Src'},"
        " false, true); 1"
    )
    wait(800)
    result("copy-with-bg", ids())
    js("_editorWin.discardEdit(); 1")
    wait(400)

    # Space + left-drag pans in Edit (07 S14), in both modes.
    js("_editorWin.enterEdit(); 1")
    wait(600)
    js("_editorWin.setEditPlane('background'); 1")
    wait()
    face_pan = "var f = _ed().face; f.panX.toFixed(0) + ',' + f.panY.toFixed(0)"
    before = js(face_pan)
    QtTest.QTest.keyPress(quick, QtCore.Qt.Key.Key_Space)
    wait(100)
    held = js("_ed().face.spaceHeld")
    centre = js(
        "var f = _ed().face; var p = f.mapToItem(null, f.width / 2, f.height / 2);"
        " Math.round(p.x) + ',' + Math.round(p.y)"
    )
    x, y = (int(v) for v in centre.split(","))
    QtTest.QTest.mousePress(
        quick,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.QPoint(x, y),
    )
    for step in range(1, 6):
        QtTest.QTest.mouseMove(quick, QtCore.QPoint(x + step * 12, y + step * 6))
        wait(30)
    QtTest.QTest.mouseRelease(
        quick,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.QPoint(x + 60, y + 30),
    )
    QtTest.QTest.keyRelease(quick, QtCore.Qt.Key.Key_Space)
    wait(100)
    after = js(face_pan)
    result("space-pan", f"{held} {before != after} {js('_ed().face.spaceHeld')}")
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
