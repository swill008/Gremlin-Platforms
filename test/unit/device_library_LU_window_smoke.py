# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Runs the real Device Library window (qml/WindowDeviceLibrary.qml) off-screen
with its real model over the stand-in Library (device_library_LU_fake_smoke.py)
and runs each step in STEPS: a line of QML JavaScript in the window's scope,
then waits (bounded) for its condition. Prints "RESULT name json" per step,
"ERROR ..." for a failing step, "WARN ..." for each QML warning, "CALLS json"
(the owner calls made) and "done". Saves <out>/<name>.png for the steps
named in SHOTS. test_device_library_LU_window.py runs it in its own process.

    python test/unit/device_library_LU_window_smoke.py <out_dir> [prefix]
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


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)


def _rows() -> str:
    return "JSON.stringify(deviceLibrary.rows.map(r => r.key))"


# (name, code run in the window, condition to wait for ("" = none), value
# to print after the wait ("" = the code's value)).
STEPS: list[tuple[str, str, str, str]] = [
    (
        "opens",
        "_lib.title",
        "deviceLibrary.statusText.indexOf('Library: 48 MB') >= 0",
        "JSON.stringify({title: _lib.title, status: deviceLibrary.statusText,"
        " folder: deviceLibrary.folderText, rows: _list.count})",
    ),
    ("caret", "deviceLibrary.toggleOpen('dev-00000001')", "", _rows()),
    (
        "select-setup",
        "deviceLibrary.select('set-00000001')",
        "",
        "JSON.stringify({name: _nameLabel.text, desc: _description.text,"
        " holds: _lib.details.holdsLabels, bindings: _lib.details.bindings,"
        " copy: _lib.canCopy, swap: _lib.deviceConnected, del: _lib.canDelete})",
    ),
    (
        "photo",
        "deviceLibrary.select('set-00000001')",
        "_bridge.item('libraryPhoto').status === Image.Ready",
        "JSON.stringify({shown: _bridge.item('libraryPhoto').visible,"
        " placeholder: _bridge.item('libraryPhotoPlaceholder').visible})",
    ),
    ("main", "''", "", "''"),
    (
        "filter-chip",
        "var c = _bridge.item('libraryFilter_deleted'); c.toggle();"
        " JSON.stringify(deviceLibrary.filters)",
        "",
        "JSON.stringify({filters: deviceLibrary.filters, rows:"
        " deviceLibrary.rows.map(r => r.key)})",
    ),
    ("filter-back", "_bridge.item('libraryFilter_deleted').toggle()", "", _rows()),
    ("search", "_search.text = 'landing'", "", _rows()),
    (
        "search-esc",
        "_search.forceActiveFocus(); _bridge.esc(_search)",
        "",
        "JSON.stringify({text: _search.text, rows: deviceLibrary.rows.length})",
    ),
    (
        "rename",
        "deviceLibrary.select('set-00000003'); _lib.startRename();"
        " _nameField.text = 'Kept for later'; _nameField.accepted(); _nameLabel.text",
        "",
        "JSON.stringify({name: _nameLabel.text, mark: deviceLibrary.rows.filter("
        "r => r.key === 'set-00000003')[0].mark})",
    ),
    (
        "describe",
        "_description.text = 'New words'; _description.editingFinished()",
        "",
        "_lib.details.description",
    ),
    (
        "describe-then-move",
        "_description.forceActiveFocus(); _description.text = 'Typed then moved';"
        " deviceLibrary.select('set-00000001'); _description.text",
        "",
        "JSON.stringify({shown: _description.text, kept: deviceLibrary.rows.length >= 0"
        " && (deviceLibrary.select('set-00000003'), _lib.details.description)})",
    ),
    (
        "device-details",
        "deviceLibrary.select('dev-00000003')",
        "",
        "JSON.stringify({state: _lib.details.stateLabel, copy: _lib.canCopy,"
        " swap: _lib.deviceConnected, del: _lib.canDelete,"
        " inputs: _bridge.item('libraryDeviceInputs').text,"
        " seen: _bridge.item('libraryDeviceSeen').text})",
    ),
    (
        "menu",
        "deviceLibrary.select('set-00000001'); _deviceMenu.popup(_menuBar, 100, 30);"
        " _deviceMenu.describe().join('|')",
        "",
        "",
    ),
    (
        "edit-menu",
        "_deviceMenu.close(); _editMenu.popup(_menuBar, 60, 30);"
        " _editMenu.describe().join('|')",
        "",
        "",
    ),
    (
        "view-menu",
        "_editMenu.close(); _viewMenu.popup(_menuBar, 160, 30);"
        " _viewMenu.describe().join('|')",
        "",
        "",
    ),
    (
        "copy",
        "_viewMenu.close(); _lib.openCopy()",
        "_copyDlg.planned && _copyDlg.profiles.length === 3",
        "JSON.stringify({open: _copyDlg.opened, from: _copyDlg.fromText,"
        " to: _copyDlg.target ? _copyDlg.target.name : '', sticks:"
        " _copyDlg.sticks.map(s => s.name),"
        " parts: _copyDlg.chosenParts(), profiles: _copyDlg.profiles.map(p => p.name"
        " + ':' + p.checked),"
        " modes: _copyDlg.chosenModes(), warnings: _copyDlg.warnings.length})",
    ),
    (
        "copy-go",
        "_copyDlg.accept()",
        "!deviceLibrary.busy && _lib.message.length > 0",
        "JSON.stringify({message: _lib.message, undo: deviceLibrary.undoText})",
    ),
    (
        "undo",
        "_h.findMenuItem(_editMenu, 'libraryUndoItem').triggered()",
        "!deviceLibrary.busy && deviceLibrary.undoText === ''",
        "JSON.stringify({message: _lib.message, undo: deviceLibrary.undoText})",
    ),
    (
        "double-click",
        "_copyDlg.close(); deviceLibrary.toggleOpen('dev-00000002');"
        " _bridge.dblclick('libraryRow_set-00000004')",
        "_copyDlg.planned",
        "JSON.stringify({from: _copyDlg.fromText, to: _copyDlg.target ?"
        " _copyDlg.target.name : ''})",
    ),
    (
        "copy-from-device",
        "_copyDlg.close(); deviceLibrary.select('dev-00000002'); _lib.openCopy()",
        "_copyDlg.planned",
        "JSON.stringify({from: _copyDlg.fromText, selected: deviceLibrary.selected,"
        " source: _copyDlg.sourceKey})",
    ),
    (
        "copy-current",
        "_copyDlg.close(); deviceLibrary.select('dev-00000003'); _lib.openCopy()",
        "_copyDlg.planned && _copyDlg.modes.length === 2"
        " && _copyDlg.profiles.length === 1",
        "JSON.stringify({open: _copyDlg.opened, from: _copyDlg.fromText,"
        " source: _copyDlg.sourceKey, modes: _copyDlg.chosenModes(),"
        " parts: _copyDlg.chosenParts(), profiles: _copyDlg.chosenProfiles()})",
    ),
    (
        "copy-current-go",
        "_copyDlg.accept()",
        "!deviceLibrary.busy && _lib.message.length > 0",
        "_lib.message",
    ),
    (
        "save-unsaved-open",
        "deviceLibrary.select('dev-00000003'); _lib.openSave()",
        "_saveDlg.profiles.length === 1",
        "JSON.stringify(_saveDlg.ticked())",
    ),
    (
        "swap",
        "_saveDlg.close(); _copyDlg.close(); deviceLibrary.select('set-00000001');"
        " _lib.openSwap()",
        "_swapDlg.warnings.length === 2",
        "JSON.stringify({open: _swapDlg.opened, first: _swapDlg.firstName,"
        " other: _swapDlg.sticks.map(s => s.name), warnings: _swapDlg.warnings})",
    ),
    (
        "output",
        "_swapDlg.close(); _lib.openOutput()",
        "_outputDlg.rows.length === 2",
        "JSON.stringify({open: _outputDlg.opened, rows: _outputDlg.rows, anyChange:"
        " _outputDlg.anyChange})",
    ),
    (
        "output-move",
        "_outputDlg.move(1, 2)",
        "_outputDlg.anyChange",
        "JSON.stringify({other: _outputDlg.other, warnings: _outputDlg.warnings.length,"
        " swapOtherShown: _bridge.item('libraryOutputSwapOther').visible})",
    ),
    (
        "settings",
        "_outputDlg.close(); _settingsDlg.openNow()",
        "",
        "JSON.stringify({open: _settingsDlg.opened, parts: _settingsDlg.parts,"
        " folder: _settingsDlg.folder})",
    ),
    (
        "settings-ok",
        "_settingsDlg.accept()",
        "!deviceLibrary.busy && deviceLibrary.statusText.indexOf('newest 10') >= 0",
        "deviceLibrary.statusText",
    ),
    (
        "tidy",
        "_tidyDlg.openNow()",
        "",
        "JSON.stringify({open: _tidyDlg.opened, items: _tidyDlg.items.map(i =>"
        " i.key)})",
    ),
    (
        "tidy-remove",
        "_tidyDlg.accept()",
        "!deviceLibrary.busy && _lib.message.indexOf('tidied') >= 0",
        _rows(),
    ),
    (
        "drop",
        "_bridge.drop(['file:///C:/x/notes.txt', 'file:///C:/x/Sam%20MFDs.zip'])",
        "!deviceLibrary.busy && _lib.message.indexOf('Device Pack added') >= 0",
        "_lib.message",
    ),
    (
        "delete",
        "deviceLibrary.select('set-00000006'); _lib.askDelete(); _deleteDlg.title",
        "",
        "_deleteDlg.title",
    ),
    (
        "delete-go",
        "_deleteDlg.accept()",
        "!deviceLibrary.busy && deviceLibrary.selected === ''",
        _rows(),
    ),
    (
        "open-on",
        "_deleteDlg.close(); _lib.openOn('Right stick', '{BBBB-0002}', 'swap')",
        "_swapDlg.opened",
        "JSON.stringify({selected: deviceLibrary.selected, first: _swapDlg.firstName})",
    ),
]

# The fix wave's steps (agent FM), run with prefix "fm-": a twin of Right
# stick (same name, no bindings) is plugged in too.
FM_STEPS: list[tuple[str, str, str, str]] = [
    (
        "fm-list-twins",
        "deviceLibrary.select('dev-00000006')",
        "",
        "JSON.stringify([_bridge.item('libraryRowName_dev-00000002').text,"
        " _bridge.item('libraryRowName_dev-00000006').text,"
        " _bridge.item('libraryRowName_dev-00000001').text])",
    ),
    (
        "fm-copy-deleted",
        "deviceLibrary.toggleOpen('dev-00000004');"
        " deviceLibrary.select('set-00000005');"
        " _lib.openCopy()",
        "_copyDlg.planned && _copyDlg.profiles.length === 3",
        "JSON.stringify({sticks: _copyDlg.sticks.map(s => s.label),"
        " to: _copyDlg.target ? _copyDlg.target.key : ''})",
    ),
    (
        "fm-copy-to-twin",
        "_bridge.item('libraryCopyTo').currentIndex = 2; _copyDlg.askProfiles()",
        "_copyDlg.profiles.length === 1 && !deviceLibrary.planning && _copyDlg.planned",
        "JSON.stringify({to: _copyDlg.target.key, profiles: _copyDlg.profiles.map("
        "p => p.name + ':' + p.checked), chosen: _copyDlg.chosenProfiles()})",
    ),
    (
        "fm-copy-twin-go",
        "_copyDlg.accept()",
        "!deviceLibrary.busy && _lib.message.length > 0",
        "JSON.stringify({message: _lib.message, undo: _h.findMenuItem(_editMenu,"
        " 'libraryUndoItem').text})",
    ),
    (
        "fm-output-vjoys",
        "_copyDlg.close(); deviceLibrary.select('dev-00000001'); _lib.openOutput()",
        "_outputDlg.rows.length === 2",
        "JSON.stringify({vjoys: _outputDlg.vjoys, row1: _bridge.item("
        "'libraryOutputTo_1').model, profiles: _outputDlg.profiles.map(p => p.name)})",
    ),
    (
        "fm-swap-twin",
        "_outputDlg.close(); deviceLibrary.select('dev-00000002'); _lib.openSwap()",
        "_swapDlg.warnings.length === 2",
        "JSON.stringify(_swapDlg.sticks.map(s => s.label))",
    ),
]

# The last fix round's steps (agent FM2), run with prefix "fm2-": a stick
# plugged in with no module file (Throttle Quadrant) and two other sticks on
# the target vJoy of a Change vJoy Output.
FM2_STEPS: list[tuple[str, str, str, str]] = [
    (
        "fm2-save-connected-no-module",
        "deviceLibrary.select('dev-00000007')",
        "",
        "JSON.stringify({button: _bridge.item('librarySaveButton').enabled,"
        " menu: _deviceMenu.itemAt(0).enabled})",
    ),
    (
        "fm2-save-dialog",
        "_lib.openSave()",
        "_saveDlg.profiles.length > 0",
        "JSON.stringify({profiles: _saveDlg.profiles.map("
        "p => p.name + ':' + p.checked),"
        " save: _bridge.item('librarySaveDialogSave').enabled})",
    ),
    (
        "fm2-save-deleted-setup",
        "_saveDlg.close(); deviceLibrary.toggleOpen('dev-00000004');"
        " deviceLibrary.select('set-00000005')",
        "",
        "JSON.stringify({menu: _deviceMenu.itemAt(0).enabled, canSave: _lib.canSave})",
    ),
    (
        "fm2-output-unplugged",
        "deviceLibrary.select('dev-00000003')",
        "",
        "JSON.stringify({button: _bridge.item('libraryOutputButton').enabled,"
        " menu: _deviceMenu.itemAt(4).enabled})",
    ),
    (
        "fm2-output-others",
        "deviceLibrary.select('dev-00000001'); _lib.openOutput()",
        "_outputDlg.rows.length === 2",
        "",
    ),
    (
        "fm2-output-also-move",
        "_outputDlg.move(1, 2)",
        "_bridge.item('libraryOutputSwapOther').visible",
        "JSON.stringify(_bridge.item('libraryOutputSwapOtherText').text)",
    ),
]

SHOTS = {
    "main": "main",
    "menu": "menu",
    "copy": "copy",
    "swap": "swap",
    "output-move": "output",
    "settings": "settings",
    "tidy": "tidy",
    "fm-list-twins": "main",
    "fm-copy-to-twin": "copy_open_profile",
    "fm-output-vjoys": "output_vjoys",
    "fm2-save-dialog": "save_open_profile",
    "fm2-output-also-move": "output_also_move",
}

# Helpers the steps use, added to the window from here (the window
# itself has no test code).
_HELPERS = r"""
import QtQuick
QtObject {
    function findMenuItem(menu, name) {
        for (var i = 0; i < menu.count; i++) {
            var it = menu.itemAt(i)
            if (it && it.objectName === name)
                return it
        }
        return null
    }
}
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out = Path(sys.argv[1])
    prefix = sys.argv[2] if len(sys.argv) > 2 else ""
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
    lib = fake_mod.FakeLibrary()
    steps = STEPS
    if prefix.startswith("fm-"):
        steps = FM_STEPS
        lib.devs.insert(
            2,
            {
                "key": "dev-00000006",
                "name": "Right stick",
                "description": "",
                "state": "connected",
                "guid": "{EEEE-0006}",
                "module": "right-stick-2",
                "setups": [],
            },
        )
    if prefix.startswith("fm2"):
        steps = FM2_STEPS
        lib.devs.insert(
            2,
            {
                "key": "dev-00000007",
                "name": "Throttle Quadrant",
                "description": "",
                "state": "connected",
                "guid": "{FFFF-0007}",
                "module": "",
                "setups": [],
            },
        )
        planned = lib.plan_output

        def plan_output(*args: object) -> dict:
            res = planned(*args)
            if res.get("others"):
                res["others"] = res["others"] + [
                    {
                        "guid": "{CCCC-0003}",
                        "name": "Rudder pedals",
                        "vjoy": 3,
                        "to": 1,
                        "inputs": 3,
                    }
                ]
            return res

        lib.plan_output = plan_output
    photo = out / "photo-in.png"
    image = QtGui.QImage(40, 30, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("steelblue"))
    image.save(str(photo))
    lib.photo_file = str(photo)
    model = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("deviceLibrary", model)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
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

    def pump(cond: str = "", timeout: float = 5.0) -> bool:
        deadline = clock.monotonic() + timeout
        while True:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
            if not cond or bool(evaluate(cond)[0]):
                return True
            if clock.monotonic() > deadline:
                return False

    def evaluate(code: str) -> tuple[object, str]:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        value = value[0] if isinstance(value, tuple) else value
        return value, (expr.error().toString() if expr.hasError() else "")

    # Test helpers on the window: find items, press Esc, drop urls.
    finder = QtQml.QQmlComponent(engine)
    finder.setData(_HELPERS.encode(), QtCore.QUrl())
    helper = finder.create()
    engine.rootContext().setContextProperty("_h", helper)

    def walk(item: QtQuick.QQuickItem):  # noqa: ANN202
        yield item
        for kid in item.childItems():
            yield from walk(kid)

    def find_item(name: str) -> QtCore.QObject | None:
        found = win.findChild(QtCore.QObject, name)
        if found is not None:
            return found
        return next(
            (i for i in walk(quick.contentItem()) if i.objectName() == name), None
        )

    class Bridge(QtCore.QObject):
        @QtCore.Slot(str, result=QtCore.QObject)
        def item(self, name: str) -> QtCore.QObject | None:
            return find_item(name)

        @QtCore.Slot(QtCore.QObject)
        def esc(self, target: QtCore.QObject) -> None:
            ev = QtGui.QKeyEvent(
                QtCore.QEvent.Type.KeyPress,
                QtCore.Qt.Key.Key_Escape,
                QtCore.Qt.KeyboardModifier.NoModifier,
            )
            QtCore.QCoreApplication.sendEvent(target, ev)

        @QtCore.Slot(str)
        def dblclick(self, name: str) -> None:
            # A real double-click on a list row (S40).
            item = find_item(name)
            assert isinstance(item, QtQuick.QQuickItem), name
            at = item.mapToScene(
                QtCore.QPointF(item.width() / 2, item.height() / 2)
            ).toPoint()
            QtTest.QTest.mouseDClick(
                quick,
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.KeyboardModifier.NoModifier,
                at,
            )

        @QtCore.Slot("QVariantList")
        def drop(self, urls: list) -> None:
            # A real drop on the window's drop area (S39).
            area = find_item("libraryDrop")
            assert isinstance(area, QtQuick.QQuickItem)
            mime = QtCore.QMimeData()
            mime.setUrls([QtCore.QUrl(u) for u in urls])
            pos = QtCore.QPointF(200, 200)
            actions = QtCore.Qt.DropAction.CopyAction
            buttons = QtCore.Qt.MouseButton.NoButton
            mods = QtCore.Qt.KeyboardModifier.NoModifier
            enter = QtGui.QDragEnterEvent(pos.toPoint(), actions, mime, buttons, mods)
            QtCore.QCoreApplication.sendEvent(quick, enter)
            move = QtGui.QDragMoveEvent(pos.toPoint(), actions, mime, buttons, mods)
            QtCore.QCoreApplication.sendEvent(quick, move)
            dropped = QtGui.QDropEvent(pos, actions, mime, buttons, mods)
            QtCore.QCoreApplication.sendEvent(quick, dropped)

    bridge = Bridge()
    engine.rootContext().setContextProperty("_bridge", bridge)
    # The renders were drawn in Dark mode.
    evaluate("Style.isDarkMode = true")
    pump("deviceLibrary.statusText.length > 0")

    for name, code, cond, show in steps:
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
            quick.grabWindow().save(str(out / f"{prefix}{SHOTS[name]}.png"))
    print("CALLS " + json.dumps([list(map(str, c)) for c in lib.calls]), flush=True)
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
