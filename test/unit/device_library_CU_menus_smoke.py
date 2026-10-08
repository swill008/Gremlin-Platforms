# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Runs the real Device Library window (qml/WindowDeviceLibrary.qml) off-screen
with its real model over the stand-in Library (device_library_LU_fake_smoke.py,
plus the row menus' owner functions) and a stand-in main window that records
what reaches Main.qml's libraryAction. Each step in STEPS is a line of QML
JavaScript in the window's scope, then a bounded wait for its condition.
Mouse clicks and keys are real Qt events sent to the window in-process.
Prints "RESULT name json" per step, "ERROR ..." for a failing step,
"WARN ..." for each QML warning, "CALLS json" (the owner and main window
calls, in order) and "done". test_device_library_CU_menus.py runs it.

    python test/unit/device_library_CU_menus_smoke.py <out_dir>
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest.mock
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
os.environ["QT_FILE_SELECTORS"] = "Universal"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import gremlin.util  # noqa: E402

gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

from gremlin import clock  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "device_library_LU_fake_smoke",
    ROOT / "test" / "unit" / "device_library_LU_fake_smoke.py",
)
assert _spec and _spec.loader
fake_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_mod)


class MenuLibrary(fake_mod.FakeLibrary):
    """The stand-in with the row menus' owner functions (agent CL's names)."""

    def removal_plan(self, key: str) -> dict:
        dev = self.device(key) or {}
        return {
            "module_file": f"{dev['module']}.json" if dev.get("module") else "",
            "setups": len(dev.get("setups", [])),
        }

    def remove_device(self, key: str) -> dict:
        self._rec("remove_device", key)
        self.devs = [d for d in self.devs if d["key"] != key]
        return self._res("remove_device")

    def delete_saved_setups(self, key: str) -> dict:
        self._rec("delete_saved_setups", key)
        dev = self.device(key)
        if dev is not None:
            dev["setups"] = []
        return self._res("delete_saved_setups")

    def keep(self, key: str) -> dict:
        self._rec("keep", key)
        item = self._find(key)
        if item is not None:
            item["own"] = True
        return self._res("keep")

    def delete_many(self, keys: list[str]) -> dict:
        self._rec("delete_many", list(keys))
        for key in keys:
            fake_mod.FakeLibrary.delete(self, key)
        return self._res("delete_many")

    def export_current(self, key: str, dest: Path) -> dict:
        self._rec("export_current", key, str(dest))
        return self._res("export_current")

    def restore_to_stick(self, key: str) -> dict:
        self._rec("restore_to_stick", key)
        self.set_last_change("restore", ["set-r"], "Restore DCS F-16 to Left throttle")
        return self._res("restore_to_stick")


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)


# A stand-in for Main.qml's libraryAction (the window reaches it through
# device_library_open.js and helpers.js's main window).
_FAKE_MAIN = r"""
import QtQuick
QtObject {
    property string refuse: ""
    function libraryAction(action, target) {
        _bridge.note(action, target.name || "", target.slug || "")
        if (action === "deleteDevice" && refuse.length)
            return JSON.stringify({ ok: false, error: refuse })
        return JSON.stringify({ ok: true })
    }
}
"""


def _menu() -> str:
    return "_rowMenu.opened ? _rowMenu.describe().join('|') : 'closed'"


def _dangers() -> str:
    return "_rowMenu.model.quick.filter(i => i.danger && i.enabled).map(i => i.text)"


def _gone(key: str) -> str:
    return f"!deviceLibrary.busy && deviceLibrary.rows.every(r => r.key !== '{key}')"


_SEL_TITLE = (
    "JSON.stringify({selected: deviceLibrary.selected, title: _rowMenu.model.title})"
)


# (name, code run in the window, condition to wait for ("" = none), value
# to print after the wait ("" = the code's value)).
STEPS: list[tuple[str, str, str, str]] = [
    (
        "rc-connected",
        "deviceLibrary.select('');"
        " _bridge.click('libraryRow_dev-00000001', 'right', '')",
        "_rowMenu.opened",
        "JSON.stringify({selected: deviceLibrary.selected, picked:"
        " deviceLibrary.selectedKeys, details: _lib.details.key, highlighted:"
        " _bridge.item('libraryRow_dev-00000001').isSel, menu: " + _menu() + ","
        " danger: " + _dangers() + "})",
    ),
    (
        "rc-not-connected",
        "_rowMenu.close(); _bridge.click('libraryRow_dev-00000003', 'right', '')",
        "_rowMenu.opened",
        "JSON.stringify({selected: deviceLibrary.selected, menu: " + _menu() + ","
        " danger: " + _dangers() + "})",
    ),
    (
        "rc-deleted",
        "_rowMenu.close(); _bridge.click('libraryRow_dev-00000004', 'right', '')",
        "_rowMenu.opened",
        _menu(),
    ),
    (
        "rc-setup",
        "_rowMenu.close(); deviceLibrary.toggleOpen('dev-00000001');"
        " _bridge.click('libraryRow_set-00000001', 'right', '')",
        "_rowMenu.opened",
        "JSON.stringify({selected: deviceLibrary.selected, details: _lib.details.key,"
        " menu: " + _menu() + ", danger: " + _dangers() + "})",
    ),
    (
        "rc-autosave",
        "_rowMenu.close(); _bridge.click('libraryRow_set-00000003', 'right', '')",
        "_rowMenu.opened",
        _menu(),
    ),
    (
        "rc-autosave-unplugged",
        "_rowMenu.close(); deviceLibrary.toggleOpen('dev-00000004');"
        " _bridge.click('libraryRow_set-00000005', 'right', '')",
        "_rowMenu.opened",
        _menu(),
    ),
    (
        "rc-space",
        "_rowMenu.close(); deviceLibrary.setAllOpen(false);"
        " _bridge.clickIn('libraryListMenuArea', 'right', 30, -30)",
        "_rowMenu.opened",
        "JSON.stringify({menu: " + _menu() + ", selected: deviceLibrary.selected})",
    ),
    (
        "keep",
        "_rowMenu.close(); deviceLibrary.toggleOpen('dev-00000001');"
        " _bridge.click('libraryRow_set-00000003', 'right', '');"
        " _rowMenu.activate('Keep This Autosave')",
        "",
        "JSON.stringify({mark: deviceLibrary.rows.filter(r => r.key ==="
        " 'set-00000003')[0].mark, message: _lib.message})",
    ),
    (
        "edit-description",
        "_bridge.click('libraryRow_set-00000001', 'right', '');"
        " _rowMenu.activate('Edit Description')",
        "_description.activeFocus",
        "JSON.stringify({focus: _description.activeFocus, key: _description.forKey})",
    ),
    (
        "remove-ask",
        "_bridge.click('libraryRow_dev-00000003', 'right', '');"
        " _rowMenu.activate('Remove from Library…')",
        "_deleteDlg.opened",
        "JSON.stringify({title: _deleteDlg.title, body: _deleteDlg.body,"
        " go: _deleteDlg.goText, red: Qt.colorEqual(_bridge.item("
        "'libraryDeleteDialogGo').contentItem.color, Style.dangerText)})",
    ),
    (
        "remove-refused",
        "_fakeMain.refuse = 'Stop the profile first: Delete Device changes it.';"
        " _deleteDlg.accept()",
        "!_deleteDlg.opened",
        "JSON.stringify({message: _lib.message, bad: _lib.messageBad,"
        " rows: deviceLibrary.rows.map(r => r.key)})",
    ),
    (
        "remove-go",
        "_fakeMain.refuse = ''; _bridge.click('libraryRow_dev-00000003', 'right', '');"
        " _rowMenu.activate('Remove from Library…'); _deleteDlg.accept()",
        _gone("dev-00000003"),
        "JSON.stringify({message: _lib.message, selected: deviceLibrary.selected})",
    ),
    (
        "remove-no-module",
        "_bridge.click('libraryRow_dev-00000005', 'right', '');"
        " _rowMenu.activate('Remove from Library…'); var t = _deleteDlg.title;"
        " _deleteDlg.accept(); t",
        _gone("dev-00000005"),
        "",
    ),
    (
        "clear-setup",
        "_bridge.click('libraryRow_dev-00000002', 'right', '');"
        " _rowMenu.activate('Clear Setup…');"
        " var t = [_deleteDlg.title, _deleteDlg.body];"
        " _deleteDlg.accept(); JSON.stringify(t)",
        "",
        "",
    ),
    (
        "delete-setups",
        "_bridge.click('libraryRow_dev-00000002', 'right', '');"
        " _rowMenu.activate('Delete Saved Setups…'); var t = [_deleteDlg.title,"
        " _deleteDlg.body]; _deleteDlg.accept(); JSON.stringify(t)",
        "!deviceLibrary.busy && deviceLibrary.rows.filter(r => r.key ==="
        " 'dev-00000002')[0].count === 0",
        "",
    ),
    (
        "restore",
        "deviceLibrary.setAllOpen(true);"
        " _bridge.click('libraryRow_set-00000001', 'right', '');"
        " _rowMenu.activate('Restore to This Stick…');"
        " var t = [_deleteDlg.title, _deleteDlg.goText, _deleteDlg.danger];"
        " _deleteDlg.accept(); t.push(_bridge.item('libraryRow_set-00000001').isBusy,"
        " _bridge.item('libraryRowBusy_set-00000001').visible); JSON.stringify(t)",
        "!deviceLibrary.busy && _lib.message.indexOf('Restored') === 0",
        "",
    ),
    (
        "restore-after",
        "''",
        "",
        "JSON.stringify({undo: deviceLibrary.undoText, busyMark:"
        " _bridge.item('libraryRow_set-00000001').isBusy})",
    ),
    (
        "main-routes",
        "_bridge.click('libraryRow_dev-00000001', 'right', '');"
        " _rowMenu.activate('Show on Home');"
        " _bridge.click('libraryRow_dev-00000001', 'right', '');"
        " _rowMenu.activate('Open Module Setup…');"
        " _bridge.click('libraryRow_dev-00000001', 'right', '');"
        " _rowMenu.activate('Open Button Map'); 'ok'",
        "",
        "",
    ),
    (
        "multi-setups",
        "_rowMenu.close(); deviceLibrary.setAllOpen(true);"
        " _bridge.click('libraryRow_set-00000001', 'left', '');"
        " _bridge.click('libraryRow_set-00000002', 'left', 'ctrl');"
        " _bridge.click('libraryRow_set-00000003', 'left', 'ctrl');"
        " _bridge.click('libraryRow_set-00000002', 'right', '')",
        "_rowMenu.opened",
        "JSON.stringify({picked: deviceLibrary.selectedKeys, menu: " + _menu() + ","
        " danger: " + _dangers() + ", copy: _lib.canCopy, rename:"
        " _lib.several, highlighted: ['set-00000001', 'set-00000002',"
        " 'set-00000003'].map(k => _bridge.item('libraryRow_' + k).isSel)})",
    ),
    (
        "multi-ask",
        "_rowMenu.activate('Delete…')",
        "_deleteDlg.opened",
        "JSON.stringify({title: _deleteDlg.title, body: _deleteDlg.body})",
    ),
    (
        "multi-go",
        "_deleteDlg.accept()",
        _gone("set-00000002"),
        "JSON.stringify(deviceLibrary.rows.map(r => r.key))",
    ),
    (
        "shift-range",
        "_bridge.click('libraryRow_dev-00000001', 'left', '');"
        " _bridge.click('libraryRow_dev-00000004', 'left', 'shift')",
        "",
        "JSON.stringify({picked: deviceLibrary.selectedKeys,"
        " action: _lib.manyAction()})",
    ),
    (
        "multi-devices",
        "_bridge.click('libraryRow_dev-00000002', 'left', '');"
        " _bridge.click('libraryRow_dev-00000004', 'left', 'ctrl');"
        " _bridge.click('libraryRow_dev-00000004', 'right', '');"
        " var m = " + _menu() + "; _rowMenu.close();"
        " _bridge.click('libraryRow_dev-00000004', 'left', '');"
        " _bridge.click('libraryRow_dev-00000006', 'left', 'ctrl');"
        " _bridge.click('libraryRow_dev-00000006', 'right', '');"
        " JSON.stringify({connectedIncluded: m, menu: " + _menu() + "})",
        "",
        "",
    ),
    (
        "multi-devices-go",
        "_rowMenu.activate('Remove from Library…'); var t = [_deleteDlg.title,"
        " _deleteDlg.body]; _deleteDlg.accept(); JSON.stringify(t)",
        _gone("dev-00000006"),
        "",
    ),
    (
        "keys-shift-f10",
        "_rowMenu.close(); deviceLibrary.select('dev-00000001');"
        " _bridge.key('shift+f10')",
        "_rowMenu.opened",
        _SEL_TITLE,
    ),
    (
        "keys-menu",
        "_rowMenu.close(); deviceLibrary.select('dev-00000002'); _bridge.key('menu')",
        "_rowMenu.opened",
        _SEL_TITLE,
    ),
    (
        "hover",
        "_rowMenu.close(); deviceLibrary.select('');"
        " _bridge.hover('libraryRow_dev-00000002')",
        "Qt.colorEqual(_bridge.item('libraryRow_dev-00000002').color, Style.bgHover)",
        "Qt.colorEqual(_bridge.item('libraryRow_dev-00000002').color, Style.bgHover)",
    ),
    (
        "export-current",
        "deviceLibrary.exportCurrent('dev-00000001', 'file:///C:/x/Left%20throttle')",
        "!deviceLibrary.busy && _lib.message.indexOf('Current setup exported') === 0",
        "_lib.message",
    ),
]

SHOTS = {
    "rc-connected": "real_ctx_device",
    "rc-setup": "real_ctx_setup",
    "multi-setups": "real_ctx_multi",
    "multi-ask": "real_ctx_confirm",
}

_KEYS = {
    "shift+f10": (QtCore.Qt.Key.Key_F10, QtCore.Qt.KeyboardModifier.ShiftModifier),
    "menu": (QtCore.Qt.Key.Key_Menu, QtCore.Qt.KeyboardModifier.NoModifier),
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])
    font = QtGui.QFont("Segoe UI")
    font.setPixelSize(15)
    app.setFont(font)
    try:
        import resources  # noqa: F401  (the icon font)

        QtGui.QFontDatabase.addApplicationFont(":/BootstrapIcons")
    except Exception:
        pass
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style",
        1,
        0,
        "Style",
    )
    import gremlin.ui.window_placement  # noqa: F401  (Gremlin.UI WindowPlacement)
    import joystick_gremlin
    from gremlin.ui.device_library_model import DeviceLibraryModel

    joystick_gremlin.register_config_options()
    lib = MenuLibrary()
    # A twin plugged in (connected, no saved setups) for the device steps.
    lib.devs.insert(
        2,
        {
            "key": "dev-00000006",
            "name": "Throttle Quadrant",
            "description": "",
            "state": "not_connected",
            "guid": "{FFFF-0006}",
            "module": "",
            "setups": [],
        },
    )
    model = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("deviceLibrary", model)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))

    def walk(item: QtQuick.QQuickItem):  # noqa: ANN202
        yield item
        for kid in item.childItems():
            yield from walk(kid)

    holder: dict = {}

    def find_item(name: str) -> QtCore.QObject | None:
        win = holder["win"]
        found = win.findChild(QtCore.QObject, name)
        if found is not None:
            return found
        return next(
            (i for i in walk(holder["quick"].contentItem()) if i.objectName() == name),
            None,
        )

    def centre(
        item: QtQuick.QQuickItem, dx: float = -1, dy: float = -1
    ) -> QtCore.QPoint:
        x = item.width() / 2 if dx < 0 else dx
        y = item.height() / 2 if dy == -1 else (item.height() + dy if dy < 0 else dy)
        return item.mapToScene(QtCore.QPointF(x, y)).toPoint()

    def mods(text: str) -> QtCore.Qt.KeyboardModifier:
        return {
            "ctrl": QtCore.Qt.KeyboardModifier.ControlModifier,
            "shift": QtCore.Qt.KeyboardModifier.ShiftModifier,
        }.get(text, QtCore.Qt.KeyboardModifier.NoModifier)

    def button(text: str) -> QtCore.Qt.MouseButton:
        return (
            QtCore.Qt.MouseButton.RightButton
            if text == "right"
            else QtCore.Qt.MouseButton.LeftButton
        )

    class Bridge(QtCore.QObject):
        @QtCore.Slot(str, result=QtCore.QObject)
        def item(self, name: str) -> QtCore.QObject | None:
            return find_item(name)

        @QtCore.Slot(str, str, str)
        def note(self, action: str, name: str, slug: str) -> None:
            lib.calls.append(("main." + action, name, slug))

        @QtCore.Slot(str, str, str)
        def click(self, name: str, which: str, modifier: str) -> None:
            # A real click on a list row.
            item = find_item(name)
            assert isinstance(item, QtQuick.QQuickItem), name
            QtTest.QTest.mouseClick(
                holder["quick"], button(which), mods(modifier), centre(item, 60)
            )

        @QtCore.Slot(str, str, int, int)
        def clickIn(self, name: str, which: str, x: int, y: int) -> None:
            item = find_item(name)
            assert isinstance(item, QtQuick.QQuickItem), name
            QtTest.QTest.mouseClick(
                holder["quick"],
                button(which),
                QtCore.Qt.KeyboardModifier.NoModifier,
                centre(item, x, y),
            )

        @QtCore.Slot(str)
        def hover(self, name: str) -> None:
            item = find_item(name)
            assert isinstance(item, QtQuick.QQuickItem), name
            QtTest.QTest.mouseMove(holder["quick"], centre(item, 80))

        @QtCore.Slot(str)
        def key(self, which: str) -> None:
            code, modifier = _KEYS[which]
            QtTest.QTest.keyClick(holder["quick"], code, modifier)

    bridge = Bridge()
    engine.rootContext().setContextProperty("_bridge", bridge)
    fake_main_c = QtQml.QQmlComponent(engine)
    fake_main_c.setData(_FAKE_MAIN.encode(), QtCore.QUrl())
    fake_main = fake_main_c.create()
    engine.rootContext().setContextProperty("_fakeMain", fake_main)
    engine.load(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "WindowDeviceLibrary.qml"))
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)
        return
    win = roots[0]
    win.setProperty("width", 1180)
    win.setProperty("height", 720)
    win.setProperty("visible", True)
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    holder["win"] = win
    holder["quick"] = quick
    quick.requestActivate()

    def evaluate(code: str) -> tuple[object, str]:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        value = value[0] if isinstance(value, tuple) else value
        return value, (expr.error().toString() if expr.hasError() else "")

    def pump(cond: str = "", timeout: float = 5.0) -> bool:
        deadline = clock.monotonic() + timeout
        while True:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
            if not cond or bool(evaluate(cond)[0]):
                return True
            if clock.monotonic() > deadline:
                return False

    evaluate("Style.isDarkMode = true")
    evaluate("Helpers.setMainWindow(_fakeMain)")
    pump("deviceLibrary.rows.length > 0 && _lib.active")

    for name, code, cond, show in STEPS:
        value, err = evaluate(code)
        if err:
            print(f"ERROR {name}: {err}", flush=True)
            continue
        if not pump(cond):
            print(f"ERROR {name}: timed out waiting for {cond}", flush=True)
        if show:
            value, err = evaluate(show)
            if err:
                print(f"ERROR {name}: {err}", flush=True)
                continue
        print(f"RESULT {name} {json.dumps(value)}", flush=True)
        if name in SHOTS:
            pump()
            quick.grabWindow().save(str(out / f"{SHOTS[name]}.png"))
    print("CALLS " + json.dumps([list(map(str, c)) for c in lib.calls]), flush=True)
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
