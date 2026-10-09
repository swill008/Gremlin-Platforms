# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's Module Setup "Server" section off-screen (D-09-OSC-FILE point 4;
it replaced the Options OSC pages): each text box edited with the cursor
still in it, then the window closes. Prints RESULT lines with what OSC's
file holds afterwards. test_handson_F8_osc.py runs it in its own process
with a fresh user folder.

    python test/unit/handson_F8_osc_close_smoke.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest.mock

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Box objectName -> (key in OSC's file, text typed).
_FIELDS = {
    "oscServerHost": ("host", "studio-pc"),
    "oscServerPort": ("port", "9123"),
    "oscServerDelay": ("autorelease_delay_ms", "400"),
}


def _boot() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    sys.path.insert(0, str(ROOT))
    import gremlin.util

    # Settings in a folder of their own, never the user's.
    gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())


def _wait_until(app: object, done: object, what: str, limit_ms: int = 5000) -> None:
    from PySide6 import QtCore

    timer = QtCore.QElapsedTimer()
    timer.start()
    while not done():  # type: ignore[operator]
        if timer.elapsed() > limit_ms:
            raise TimeoutError(what)
        flags = QtCore.QEventLoop.ProcessEventsFlag.AllEvents
        app.processEvents(flags, 20)  # type: ignore[attr-defined]


def _walk(item: object) -> list:
    out = [item]
    for child in item.childItems():  # type: ignore[attr-defined]
        out.extend(_walk(child))
    return out


def main() -> None:
    _boot()
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: F401

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    import gremlin.ui.osc_option  # noqa: F401  (Gremlin.Config types)
    import joystick_gremlin

    joystick_gremlin.register_config_options()  # History reads its options
    from gremlin import osc_device_file

    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))

    # Like Module Setup: a window made with no parent, destroyed when it
    # closes, the Server section in a Loader.
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Item {
    property var opened: []
    Component {
        id: _page
        Window {
            property url page
            width: 700; height: 400; visible: true
            onClosing: () => { destroy() }
            Loader { anchors.fill: parent; source: page }
        }
    }
    function open(page) {
        var win = _page.createObject(null, {"page": page})
        opened.push(win)
        return win
    }
}
""",
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Root.qml")),
    )
    host = engine.rootObjects()[0]
    section = QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "OscSetupTabs.qml"))

    def open_section(name: str) -> tuple:
        expr = QtQml.QQmlExpression(
            QtQml.qmlContext(host), host, f'open("{section.toString()}")'
        )
        win = expr.evaluate()[0]
        if expr.hasError():
            raise RuntimeError(expr.error().toString())
        win.requestActivate()
        found: list = []

        def shown() -> bool:
            found[:] = [i for i in _walk(win.contentItem()) if i.objectName() == name]
            return bool(found)

        _wait_until(app, shown, f"{name} shown")
        return win, found[0]

    def close(win: object) -> None:
        gone: list = []
        destroyed = win.destroyed  # type: ignore[attr-defined]
        destroyed.connect(lambda *_: gone.append(True))
        win.close()  # type: ignore[attr-defined]
        _wait_until(app, lambda: bool(gone), "window destroyed")

    def type_into(win: object, field: object, text: str) -> None:
        field.forceActiveFocus()  # type: ignore[attr-defined]
        QtCore.QMetaObject.invokeMethod(field, "selectAll")
        for char in text:
            QtTest.QTest.keyClick(win, char)

    for name, (key, text) in _FIELDS.items():
        before = osc_device_file.read_server()[key]
        # Typed into the box, the cursor still there: no Tab, no Enter.
        win, field = open_section(name)
        type_into(win, field, text)
        _wait_until(app, lambda: field.property("text") == text, f"typed {name}")
        print(f"RESULT {key}-focus {field.property('activeFocus')}", flush=True)
        print(f"RESULT {key}-before {before}", flush=True)
        close(win)
        after = osc_device_file.read_server()[key]
        print(f"RESULT {key}-after {after}", flush=True)

    for warning in warnings:
        print("WARN " + warning.encode("ascii", "replace").decode(), flush=True)
    print("done", flush=True)
    # os._exit skips Qt's teardown, which can hang off-screen.
    os._exit(0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    try:
        main()
    except Exception as failed:  # noqa: BLE001 (said, then the process ends)
        import traceback

        traceback.print_exc()
        print(f"ERROR {failed!r}", flush=True)
        os._exit(1)
