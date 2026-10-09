# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page in the real program, off-screen (D-09-OSC-COMPANION,
D-09-OSC-TABS): the app starts as joystick_gremlin.py starts it (fake
hardware, a stand-in home folder, OSC never binds), the OSC page opens,
then real mouse clicks: "OSC Setup…" opens OSC's Module Setup; a row's
pencil menu "Copy for Companion" puts the Generic OSC text on the
clipboard; the right side says "Select an input to see its actions" while
no input is selected. Prints "RESULT name json" and "done".
test_osc_page_companion.py runs it.

    python test/unit/osc_page_companion_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert _spec and _spec.loader
fake_hardware = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import gremlin.osc as gosc  # noqa: E402

# No network: OSC never binds; this PC's address is a fixed one.
gosc.OscRuntime._bind = lambda self: None  # type: ignore[method-assign]
gosc.OscRuntime.hold_open = lambda self, token: True  # type: ignore[method-assign]
gosc.OscRuntime.release_open = lambda self, token: None  # type: ignore[method-assign]
gosc.local_ipv4_addresses = lambda: ["192.168.1.20", "127.0.0.1", "0.0.0.0"]

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

Left = QtCore.Qt.MouseButton.LeftButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    from gremlin import osc_device_file
    from gremlin.modules import ids
    from gremlin.osc import OscDevice
    from gremlin.signal import signal
    from gremlin.types import InputType

    warnings: list[str] = []
    engine = app.engine if hasattr(app, "engine") else None
    if isinstance(engine, QtQml.QQmlEngine):
        engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))

    def run(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            print("ERROR", code, expr.error().toString(), flush=True)
        return value[0] if isinstance(value, tuple) else value

    def walk(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for child in item.childItems():
            found.extend(walk(child))
        return found

    def named(name: str, window: QtQuick.QQuickWindow = win) -> object:
        root = window.contentItem()
        while root.parentItem() is not None:
            root = root.parentItem()
        for item in walk(root):
            if item.objectName() == name and item.isVisible():
                return item
        return None

    def wait_for(done: object, limit_ms: int = 5000) -> bool:
        timer = QtCore.QElapsedTimer()
        timer.start()
        while not done() and timer.elapsed() < limit_ms:  # type: ignore[operator]
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        return bool(done())  # type: ignore[operator]

    def click(item: QtQuick.QQuickItem) -> None:
        window = item.window()
        point = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
        QtTest.QTest.mouseClick(window, Left, NoMod, point.toPoint())
        app.processEvents()

    # OSC listens on port 8123; no inputs yet.
    server = dict(osc_device_file.read_server())
    server["port"] = 8123
    osc_device_file.write_server(server, who="test")
    win.setProperty("width", 1400)
    win.setProperty("height", 900)
    wait_for(lambda: False, 500)

    run('_root.openConfigurationNow(_root._cardForGuid("%s"))' % str(ids.OSC).upper())
    wait_for(lambda: named("oscClear") is not None)

    # 1. No input selected (none to select yet): the right side says so.
    wait_for(lambda: named("oscNoInput") is not None, 2000)
    empty = named("oscNoInput")
    result("empty-text", empty.property("text") if empty is not None else None)

    # Two inputs, added as the Add window adds them.
    dev = OscDevice()
    dev.create(InputType.JoystickButton, label="/sd/fire")
    dev.create(InputType.JoystickAxis, label="/fader/1")
    osc_device_file.save(who="test")
    signal.oscDeviceModified.emit()
    wait_for(lambda: False, 500)

    # 2. OSC Setup… opens OSC's Module Setup (by its signal).
    opened: list[bool] = []
    signal.openOscModuleSetup.connect(lambda: opened.append(True))
    setup_button = named("oscSetup")
    result("setup-button", setup_button is not None)
    if setup_button is not None:
        before = set(app.topLevelWindows())
        click(setup_button)
        wait_for(lambda: bool(opened), 2000)
        new = wait_for(
            lambda: any(
                w.isVisible() for w in set(app.topLevelWindows()) - before
            ),
            3000,
        )
        result("setup-signal", bool(opened))
        result("setup-window", new)
        for w in set(app.topLevelWindows()) - before:
            w.close()
        wait_for(lambda: False, 200)

    # 3. Row menu › Copy for Companion: the text is on the clipboard.
    QtGui.QGuiApplication.clipboard().setText("")
    pencils = [
        i for i in walk(win.contentItem())
        if i.isVisible() and i.property("text") == run("bsi.icons.edit")
        and i.parentItem() is not None
    ]
    result("pencils", len(pencils) >= 1)
    if pencils:
        click(pencils[0])
        wait_for(lambda: named("oscCopyCompanion") is not None, 2000)
        item = named("oscCopyCompanion")
        result("copy-item", item is not None)
        if item is not None:
            click(item)
            wait_for(lambda: bool(QtGui.QGuiApplication.clipboard().text()), 2000)
    result("clipboard", QtGui.QGuiApplication.clipboard().text())
    page = [i for i in walk(win.contentItem()) if i.objectName() == "oscClear"]
    message = None
    if page:
        for i in walk(win.contentItem()):
            if i.metaObject().className().startswith("MessageLine") and i.isVisible():
                message = i.property("text")
                break
    result("message", message)

    for w in warnings:
        if "OscDevice.qml" in w or "InputConfiguration.qml" in w:
            print(f"WARN {w}", flush=True)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
