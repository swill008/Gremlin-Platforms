# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page in the real program, off-screen (D-09-OSC-COMPANION,
D-09-OSC-TABS, D-09-OSC-PAGE, D-09-OSC-DOCK): the app starts as
joystick_gremlin.py starts it (fake hardware, a stand-in home folder, OSC
never binds), the OSC page (qml/OscPage.qml, 09 S129) opens, then real mouse
clicks: the empty list says how to add inputs and no action pane is open;
the page bar's "OSC Setup…" opens OSC's Module Setup; a right-click on an
input's row opens the page's menu (09 S135) and its rows are clicked:
"Copy for Companion" puts the Generic OSC text on the clipboard, "Edit
Settings…" opens the Add window on that input, "Change Address…" with a bad
address shows the model's error on the message line, Row › "Delete…" asks
the shared question first (undoable, and page Undo puts the input back),
Add Inputs › "Import…" shows the result on the message line; the page bar's
"Monitor" unfolds the docked OSC Monitor (09 S137), whose "Add as Input…"
opens the page's Add window filled in. Prints "RESULT name json" and "done".
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

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

Left = QtCore.Qt.MouseButton.LeftButton
Right = QtCore.Qt.MouseButton.RightButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def main() -> None:  # noqa: C901, PLR0915
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    # The main window by its C++ pointer: a Python wrapper of it can be
    # dropped by PySide once item.window() hands out another one.
    win_ptr = shiboken6.getCppPointer(win)[0]

    def main_win() -> QtQuick.QQuickWindow:
        return shiboken6.wrapInstance(win_ptr, QtQuick.QQuickWindow)
    from gremlin import osc_device_file, osc_traffic
    from gremlin.modules import ids
    from gremlin.osc import OscDevice
    from gremlin.signal import signal
    from gremlin.types import InputType

    warnings: list[str] = []
    engine = app.engine if hasattr(app, "engine") else None
    if isinstance(engine, QtQml.QQmlEngine):
        engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))

    def run(code: str, obj: QtCore.QObject | None = None) -> object:
        obj = obj if obj is not None else main_win()
        expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
        value = expr.evaluate()
        if expr.hasError():
            print("ERROR", code, expr.error().toString(), flush=True)
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def walk(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for child in item.childItems():
            found.extend(walk(child))
        return found

    def top() -> QtQuick.QQuickItem:
        root = main_win().contentItem()
        while root.parentItem() is not None:
            root = root.parentItem()
        return root

    def named(name: str) -> object:
        for item in walk(top()):
            if item.objectName() == name and item.isVisible():
                return item
        return None

    def wait_for(done: object, limit_ms: int = 5000) -> bool:
        timer = QtCore.QElapsedTimer()
        timer.start()
        while not done() and timer.elapsed() < limit_ms:  # type: ignore[operator]
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        return bool(done())  # type: ignore[operator]

    def click(item: QtQuick.QQuickItem, button: object = Left) -> None:
        window = item.window()
        point = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
        QtTest.QTest.mouseClick(window, button, NoMod, point.toPoint())
        app.processEvents()

    def the_page() -> object:
        for item in walk(top()):
            if item.metaObject().className().startswith("OscPage") and item.isVisible():
                return item
        return None

    def inner(item: QtCore.QObject) -> QtCore.QObject:
        """Where OscPage.qml's own ids are in scope: the page itself when
        its Loader loads the file (Main.qml's source: "OscPage.qml")."""
        if run("typeof _pageMenu", item) == "object":
            return item
        for child in item.childItems():
            own = QtQml.qmlContext(child)
            if own is not None and own != QtQml.qmlContext(item):
                return child
        return item

    def question() -> object:
        for obj in main_win().findChildren(QtCore.QObject, "confirmDialog"):
            if obj.property("opened"):
                return obj
        return None

    def message(page: QtQuick.QQuickItem) -> object:
        for i in walk(page):
            if i.objectName() == "messageLine" and i.isVisible():
                return i.property("text")
        return None

    def row_of(page: QtQuick.QQuickItem, key: str) -> object:
        for i in walk(page):
            if (i.isVisible() and i.property("rowKind") == "parent"
                    and i.property("key") == key):
                return i
        return None

    def menu_row(scope: QtCore.QObject, text: str) -> None:
        """Clicks the open right-click menu's row showing this text."""
        wait_for(lambda: bool(run("_pageMenu.opened", scope)), 2000)
        wait_for(lambda: False, 150)  # the menu lays its rows out first
        at = f"_pageMenu.rowIndexOf({json.dumps(text)})"
        rect = run(f"_pageMenu.rowRect({at})", scope)
        if not isinstance(rect, dict):
            print(f"ERROR no menu row {text}: {run('_pageMenu.describe()', scope)}",
                  flush=True)
            return
        point = QtCore.QPointF(rect["x"] + rect["w"] / 2, rect["y"] + rect["h"] / 2)
        QtTest.QTest.mouseClick(scope.window(), Left, NoMod, point.toPoint())
        app.processEvents()
        wait_for(lambda: False, 200)

    def row_menu(page: QtQuick.QQuickItem, scope: QtCore.QObject, key: str,
                 *path: str) -> None:
        """Right-clicks the input's row, then clicks each menu row in turn."""
        run("_pageMenu.close()", scope)
        row = row_of(page, key)
        if row is None:
            print(f"ERROR no row {key}", flush=True)
            return
        click(row, Right)
        for text in path:
            menu_row(scope, text)

    # OSC listens on port 8123; no inputs yet.
    server = dict(osc_device_file.read_server())
    server["port"] = 8123
    osc_device_file.write_server(server, who="test")
    win.setProperty("width", 1400)
    win.setProperty("height", 900)
    wait_for(lambda: False, 500)

    run('_root.openConfigurationNow(_root._cardForGuid("%s"))' % str(ids.OSC).upper())
    wait_for(lambda: the_page() is not None and named("oscSetup") is not None)
    page = the_page()
    result("page", page is not None)
    if page is None:
        print("ERROR no OSC page; tab", run("uiState.currentTab"), flush=True)
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)
        os._exit(0)
    scope = inner(page)

    # 1. No inputs yet: the list says how to add them; no action pane open.
    wait_for(lambda: named("oscEmpty") is not None, 2000)
    empty = named("oscEmpty")
    result("empty-text", empty.property("text") if empty is not None else None)
    result("pane-closed", page.property("actionOpen") is False)

    # Two inputs, added as the Add window adds them.
    dev = OscDevice()
    fire = dev.create(InputType.JoystickButton, label="/sd/fire")
    fader = dev.create(InputType.JoystickAxis, label="/fader/1")
    osc_device_file.save(who="test")
    signal.oscDeviceModified.emit()
    wait_for(lambda: False, 500)

    def key_of(uid: str) -> str:
        return str(run(f"layout.keyOfUid({json.dumps(uid)})", page) or "")

    fire_key, fader_key = key_of(fire.uid), key_of(fader.uid)
    wait_for(lambda: row_of(page, fire_key) is not None, 3000)
    result("rows", [row_of(page, k) is not None for k in (fire_key, fader_key)])

    # 2. OSC Setup… (page bar) opens OSC's Module Setup (by its signal).
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

    # 3. Right-click › Copy for Companion: the text is on the clipboard.
    QtGui.QGuiApplication.clipboard().setText("")
    row_menu(page, scope, fire_key)
    result("menu", run("_pageMenu.describe()", scope))
    menu_row(scope, "Copy for Companion")
    wait_for(lambda: bool(QtGui.QGuiApplication.clipboard().text()), 2000)
    result("clipboard", QtGui.QGuiApplication.clipboard().text())
    result("message", message(page))

    # 4. Right-click › Edit Settings…: the Add window on that input.
    row_menu(page, scope, fader_key, "Edit Settings…")
    wait_for(lambda: named("oscCmd") is not None, 2000)
    cmd = named("oscCmd")
    axis = named("oscModeAxis")
    result("edit-address", cmd.property("text") if cmd else None)
    result("edit-axis", bool(axis and axis.property("checked")))
    run("_addDialog.close()", scope)
    wait_for(lambda: False, 200)

    # 5. Right-click › Change Address… with a bad address: the model's error
    # on the message line, the address kept.
    row_menu(page, scope, fader_key, "Change Address…")
    wait_for(lambda: bool(run("_addressDialog.visible", scope)), 2000)
    result("address-dialog", bool(run("_addressDialog.visible", scope)))
    run('_addressDialog.accepted("fader")', scope)
    wait_for(lambda: False, 200)
    result("rename-error", message(page))
    result("rename-kept", OscDevice().rows.by_uid(fader.uid).label)

    # 6. Right-click › Row › Delete…: asks the shared question first (it can
    # be undone); then the input goes, and page Undo puts it back.
    row_menu(page, scope, fire_key, "Row", "Delete…")
    wait_for(lambda: question() is not None, 3000)
    dlg = question()
    result("delete-before-confirm", OscDevice().rows.by_uid(fire.uid) is not None)
    result("confirm-open", dlg is not None)
    result("confirm-undoable", bool(dlg and dlg.property("undoable")))
    if dlg is not None:
        run("_go.clicked(); true", dlg)
        wait_for(lambda: OscDevice().rows.by_uid(fire.uid) is None, 3000)
    result("delete-after-confirm", OscDevice().rows.by_uid(fire.uid) is None)
    result("can-undo", bool(run("layout.canUndo", page)))
    run("layout.undo()", page)
    wait_for(lambda: OscDevice().rows.by_uid(fire.uid) is not None, 3000)
    result("undo-restores", OscDevice().rows.by_uid(fire.uid) is not None)

    # 7. Right-click › Add Inputs › Import…: the result on the message line.
    row_menu(page, scope, fader_key, "Add Inputs", "Import…")
    wait_for(lambda: named("oscImportText") is not None, 2000)
    box = named("oscImportText")
    if box is not None:
        box.setProperty("text", "/a A\n/b, BNP")
        app.processEvents()
        ok = named("oscImportOk")
        if ok is not None:
            click(ok)
        wait_for(lambda: False, 300)
    result("import-result", message(page))
    result("imported", sorted(
        r.label for r in OscDevice().rows.rows() if r.label in ("/a", "/b")
    ))

    # 8. Monitor (page bar) unfolds the docked Monitor; its "Add as Input…"
    # on a "no input" message opens the page's Add window filled in.
    monitor = named("oscMonitor")
    result("monitor-button", monitor is not None)
    result("monitor-folded", run("monitorPanel.folded", page) is True)
    if monitor is not None:
        click(monitor)
        wait_for(lambda: run("monitorPanel.folded", page) is False, 2000)
    result("monitor-unfolded", run("monitorPanel.folded", page) is False)
    osc_traffic.clear()
    osc_traffic.note("in", "/knob/1", [0.4], ("10.0.0.9", 8000), [])
    wait_for(lambda: named("oscMonitorAddRow0") is not None, 3000)
    add_row = named("oscMonitorAddRow0")
    result("monitor-add-row", add_row is not None)
    if add_row is not None:
        click(add_row)
        wait_for(lambda: named("oscCmd") is not None, 2000)
    cmd = named("oscCmd")
    axis = named("oscModeAxis")
    result("page-add-address", cmd.property("text") if cmd else None)
    result("page-add-axis", bool(axis and axis.property("checked")))

    ours = ("OscPage.qml", "ControlTree.qml", "ControlFindBar.qml", "ActionPane.qml",
            "OscMonitorPanel.qml", "OscAddDialog.qml", "OscImportDialog.qml")
    for w in warnings:
        if any(name in w for name in ours):
            print(f"WARN {w}", flush=True)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        import traceback

        print("ERROR " + " | ".join(traceback.format_exc().splitlines()), flush=True)
        print("done", flush=True)
        os._exit(1)
