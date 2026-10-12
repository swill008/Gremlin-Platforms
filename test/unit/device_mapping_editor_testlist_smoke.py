# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor off-screen, for D-TESTLIST-1 items 3 and 4:
the view-only banner's two texts and its "File › Device" link, and an edit's
just-added picture let go before the edit's temporary folder goes. Prints
"RESULT <name> <json>", "WARN ..." for each QML warning, then "done".
test_device_mapping_editor_testlist.py runs it in its own process.

    python test/unit/device_mapping_editor_testlist_smoke.py <out_dir>
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

import gremlin.util  # noqa: E402

gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

from device_mapping_editor_window_smoke import FakeBackend, FakeUiState  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

# The banner's parts as shown: texts and which links are visible.
BANNER = (
    " function find(o, name) { if (!o) return null;"
    "   if (o.objectName === name) return o;"
    "   var k = o.children || [];"
    "   for (var i = 0; i < k.length; i++) {"
    "     var f = find(k[i], name); if (f) return f }"
    "   return null }"
    " var root = _editorWin.contentItem;"
    " var t = find(root, 'dmeViewOnlyText'), d = find(root, 'dmeViewOnlyDevice'),"
    "     e = find(root, 'dmeViewOnlyEdit');"
    " var tail = e ? e.parent.children[e.parent.children.length - 1] : null;"
    " JSON.stringify({banner: !!find(root, 'dmeViewOnlyBanner') &&"
    "   find(root, 'dmeViewOnlyBanner').visible,"
    "   text: t ? t.text : null, device: d ? d.visible : null,"
    "   deviceText: d ? d.text : null, edit: e ? e.visible : null,"
    "   tail: tail ? tail.text : null})"
)

# Every picture the editor draws (RigDrawItem), held by the script.
DRAWN = (
    "function drawn(o, out) { if (!o) return out;"
    "   if (typeof o.pictureInfo === 'function') out.push(o);"
    "   var k = o.children || [];"
    "   for (var i = 0; i < k.length; i++) drawn(k[i], out);"
    "   return out }"
)


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841 (kept alive)
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.device_map_options  # noqa: F401
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
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogDeviceMappingEditor.qml"))
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        smoke_exit(1)
    win = roots[0]
    win.setProperty("width", 1400)
    win.setProperty("height", 900)
    win.setProperty("visible", True)
    QtTest.QTest.qWait(600)

    def js(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()[0]
        if expr.hasError():
            print(f"ERROR {expr.error().toString()}", flush=True)
            return None
        return value

    # Item 4: no device chosen.
    print(f"RESULT banner-none {js(BANNER)}", flush=True)
    # Its link opens the File menu with the Device list out.
    opened = js(
        "var r = _editorWin.openDeviceMenu();"
        " JSON.stringify({ok: r, file: _fileMenu.opened, device: _deviceMenu.opened})"
    )
    QtTest.QTest.qWait(300)
    after = js(
        "JSON.stringify({file: _fileMenu.opened || _fileMenu.visible,"
        " device: _deviceMenu.opened || _deviceMenu.visible})"
    )
    print(f"RESULT device-link {opened} {after}", flush=True)
    js("_deviceMenu.close(); _fileMenu.close(); 1")
    QtTest.QTest.qWait(300)

    # A device chosen: today's text with its Edit Mapping link.
    js(
        "_editorWin.targetGuid = '12345678-1234-1234-1234-123456789abc';"
        " _editorWin.targetName = 'Smoke Stick'; 1"
    )
    QtTest.QTest.qWait(800)
    print(f"RESULT banner-device {js(BANNER)}", flush=True)

    # Item 3: a picture dropped and the edit discarded at once, while the
    # picture reader is still busy with a big picture: no picture the editor
    # still holds may name a file that is gone, and nothing warns.
    big = QtGui.QImage(6000, 6000, QtGui.QImage.Format.Format_RGB32)
    big.fill(QtGui.QColor("#123456"))
    big_path = out / "big.png"
    big.save(str(big_path))
    wide = QtGui.QImage(400, 100, QtGui.QImage.Format.Format_RGB32)
    wide.fill(QtGui.QColor("#336699"))
    wide_path = out / "wide.png"
    wide.save(str(wide_path))
    big_url = QtCore.QUrl.fromLocalFile(str(big_path)).toString()
    wide_url = QtCore.QUrl.fromLocalFile(str(wide_path)).toString()
    js("_editorWin.enterEdit(); 1")
    QtTest.QTest.qWait(600)
    held = js(
        DRAWN + ";"
        " Qt.createQmlObject('import QtQuick; Image { asynchronous: true; source: \""
        + big_url + "\" }', _editorWin.contentItem);"
        " var e = _ed();"
        " var ok = _editorWin.dropPictures(['" + wide_url + "'], 100, 100, e);"
        " var mine = drawn(e, []).filter(function(d) {"
        "   return String(d.pictureInfo().source).indexOf('wide') >= 0 });"
        " var count = mine.length;"
        " _editorWin.discardEdit();"
        " JSON.stringify({ok: ok, count: count, after: mine.map(function(d) {"
        "   var p = d.pictureInfo();"
        "   return {source: String(p.source), status: p.status} })})"
    )
    print(f"RESULT drop-discard {held}", flush=True)
    data = json.loads(held) if held else {"after": []}
    gone = []
    for one in data["after"]:
        src = one["source"]
        if src:
            path = Path(QtCore.QUrl(src).toLocalFile())
            if not path.is_file():
                gone.append(src)
    print(f"RESULT held-missing {json.dumps(gone)}", flush=True)
    QtTest.QTest.qWait(3000)
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
