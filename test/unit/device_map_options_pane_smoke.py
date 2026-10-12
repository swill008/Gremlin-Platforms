# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Device Mapping Editor
and Device Map Options, its own small window (Edit > Device Map Options...,
Ctrl+,; 07 S98), and prints what it shows and does as JSON (a screenshot
too when a folder is given).
test_device_map_options_pane.py runs it in its own process with a fresh
user folder.

    python test/unit/device_map_options_pane_smoke.py [folder]
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.ui import device_map_options  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_until(lambda: app.engine.rootObjects(), "the main window")[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openDeviceMappingEditorForCard", card)
    win = wait_until(
        lambda: call(root, "deviceMappingEditorWindow"), "the Device Mapping Editor"
    )
    win.setProperty("width", 1200)
    win.setProperty("height", 800)
    QtTest.QTest.qWait(300)
    out: dict = {}

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for c in item.childItems():
            found += items(c)
        return found

    # Edit > Device Map Options... opens its window (on the live map too).
    menu = ev("(function(){ var m = _editMenu; for (var i = 0; i < m.count; i++) {"
              " var it = m.itemAt(i); if (it && it.text === 'Device Map Options…')"
              " { it.triggered(); return it.hint } } return false })()")
    wait_until(
        lambda: (lambda w: w is not None and w.isVisible())(ev("_optionsWin")),
        "the Device Map Options window", fail=False,
    )
    out["menu"] = menu
    options = ev("_optionsWin")
    out["open"] = [bool(options is not None and options.isVisible()),
                   ev("_optionsWin.title"), bool(ev("_editorWin.editing"))]
    pane = next(c for c in items(options.contentItem())
                if c.objectName() == "deviceMapOptionsPanel")

    def child(name: str) -> QtQuick.QQuickItem | None:
        found = (c for c in items(options.contentItem()) if c.objectName() == name)
        return next(found, None)

    # No Options pane or tool tab left in the Device Mapping Editor window (07 S99).
    out["no-pane"] = [
        c.objectName() for c in items(win.contentItem())
        if c.objectName() in ("optionsPane", "tool:options")
    ]
    out["groups"] = [
        g for g in ("labels", "editing", "right-click", "recovery", "view",
                    "colours", "library")
        if child("optionsGroup:" + g) is not None
    ]
    rc = child("optionsGroup:right-click")
    out["right-click-title"] = [
        c.property("text") for c in items(rc) if c.property("text")
    ] if rc is not None else []

    def rows() -> list:
        return sorted(
            c.objectName()[len("option:"):]
            for c in items(pane)
            if c.objectName().startswith("option:") and c.isVisible()
        )

    ev("_opts.paneGroup = 'right-click'")
    QtTest.QTest.qWait(300)
    out["right-click-rows"] = rows()
    ev("_opts.paneGroup = 'labels'")
    QtTest.QTest.qWait(300)
    out["labels-rows"] = rows()
    # A switch changes and keeps its setting.
    before = ev("_opts.values['description-first']")
    row = child("option:description-first")
    switch = next(c for c in row.childItems()
                  if c.metaObject().className().startswith("Switch") and c.isVisible())
    centre = switch.mapToScene(QtCore.QPointF(switch.width() / 2, switch.height() / 2))
    QtTest.QTest.mouseClick(options, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    wait_until(lambda: ev("_opts.values['description-first']") != before,
               "the switch changed", 5000, fail=False)
    out["switch"] = [before, ev("_opts.values['description-first']"),
                     device_map_options.value("description-first")]
    # Another group: its settings; kept for next time.
    group = child("optionsGroup:editing")
    centre = group.mapToScene(QtCore.QPointF(group.width() / 2, group.height() / 2))
    QtTest.QTest.mouseClick(options, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    wait_until(lambda: ev("_opts.paneGroup") == "editing", "the Editing group",
               5000, fail=False)
    out["editing-rows"] = rows()
    out["kept-group"] = device_map_options.DeviceMapOptions().paneGroup
    if shots is not None:
        shots.mkdir(parents=True, exist_ok=True)
        options.grabWindow().save(str(shots / "options-window.png"))
    ev("_opts.paneGroup = 'library'")

    def library_items() -> list:
        return [c for c in items(pane) if c.metaObject().className().startswith(
            "OptionDeviceMapLibrary")]

    wait_until(lambda: any(c.isVisible() for c in library_items()),
               "the Library group", 5000, fail=False)
    library = library_items()
    out["library"] = bool(library) and library[0].isVisible()
    # Esc closes it.
    options.requestActivate()
    wait_until(lambda: options.isActive(),
               "the Options window active", 5000, fail=False)
    QtTest.QTest.keyClick(options, QtCore.Qt.Key.Key_Escape)
    wait_until(lambda: not options.isVisible(), "Esc closed it", 5000, fail=False)
    out["esc-closed"] = not options.isVisible()
    # Ctrl+, opens it again (07 S133): the window's key, as the menu shows.
    ev("_editorWin.requestActivate()")
    wait_until(lambda: win.isActive(),
               "the editor active", 5000, fail=False)
    QtTest.QTest.keyClick(win, QtCore.Qt.Key.Key_Comma,
                          QtCore.Qt.KeyboardModifier.ControlModifier)
    wait_until(lambda: options.isVisible(), "Ctrl+, opened it", 5000, fail=False)
    out["key-opens"] = options.isVisible()
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
