# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Options › OSC off-screen: the Input and Output host and port boxes edited
with the cursor still in them, then the page goes (Options closes). Prints
RESULT lines with what the settings hold afterwards. test_handson_F8_osc.py
runs it in its own process with a fresh user folder.

    python test/unit/handson_F8_osc_close_smoke.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest.mock

ROOT = pathlib.Path(__file__).resolve().parents[2]

_PAGES = {
    "input": ("OptionOscInputHost.qml", "host", "port"),
    "output": ("OptionOscOutputHost.qml", "output-host", "output-port"),
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
    from PySide6 import QtCore, QtGui, QtQml, QtTest

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    import gremlin.ui.osc_option  # noqa: F401  (Gremlin.Config types)
    import joystick_gremlin

    joystick_gremlin.register_config_options()
    from gremlin.config import Configuration
    from gremlin.osc import OSC_GROUP, OSC_SECTION

    cfg = Configuration()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))

    # Like Options (helpers.js createComponent): a window made with no
    # parent, destroyed when it closes.
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
            width: 700; height: 200; visible: true
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

    def open_page(page: str) -> tuple:
        url = QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / page)).toString()
        expr = QtQml.QQmlExpression(QtQml.qmlContext(host), host, f'open("{url}")')
        win = expr.evaluate()[0]
        if expr.hasError():
            raise RuntimeError(expr.error().toString())
        win.requestActivate()
        items: list = []
        _wait_until(
            app,
            lambda: (items.clear(), items.extend(_walk(win.contentItem())))
            and any(i.inherits("QQuickComboBox") for i in items),
            f"{page} shown",
        )
        combo = next(i for i in items if i.inherits("QQuickComboBox"))
        port = next(
            i for i in items
            if i.inherits("QQuickTextField") and i.parentItem() is not combo
        )
        return win, combo, port

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

    for name, (page, host_key, port_key) in _PAGES.items():
        before_host = cfg.value(OSC_SECTION, OSC_GROUP, host_key)
        before_port = cfg.value(OSC_SECTION, OSC_GROUP, port_key)

        # Typed into the host box, the cursor still there: no Tab, no Enter.
        win, combo, _port = open_page(page)
        field = combo.property("contentItem")
        type_into(win, field, "127.0.0.5")
        _wait_until(
            app, lambda: combo.property("editText") == "127.0.0.5", "typed host"
        )
        print(f"RESULT {name}-focus {field.property('activeFocus')}", flush=True)
        print(f"RESULT {name}-host-before {before_host}", flush=True)
        close(win)
        after = cfg.value(OSC_SECTION, OSC_GROUP, host_key)
        print(f"RESULT {name}-host-after {after}", flush=True)

        # The port box the same way.
        win, _combo, port = open_page(page)
        type_into(win, port, "9123")
        _wait_until(app, lambda: port.property("text") == "9123", "typed port")
        print(f"RESULT {name}-port-focus {port.property('activeFocus')}", flush=True)
        print(f"RESULT {name}-port-before {before_port}", flush=True)
        close(win)
        after = cfg.value(OSC_SECTION, OSC_GROUP, port_key)
        print(f"RESULT {name}-port-after {after}", flush=True)

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
