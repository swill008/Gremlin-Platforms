# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
and its Options pane (Edit > Button Map Options...) and prints what it shows
and does as JSON (a screenshot too when a folder is given).
test_button_map_options_pane.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_options_pane_smoke.py [folder]
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.ui import button_map_options  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "buttonMapWindow")
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

    def child(name: str) -> QtQuick.QQuickItem | None:
        # By the item tree (a Repeater's rows are not QObject children).
        found = (c for c in items(win.contentItem()) if c.objectName() == name)
        return next(found, None)

    out["tool"] = [ev("_tools.sideOf('options')"), ev("_tools.isOpen('options')")]
    # Edit > Button Map Options... opens the pane (on the live map too).
    menu = ev("(function(){ var m = _editMenu; for (var i = 0; i < m.count; i++) {"
              " var it = m.itemAt(i); if (it && it.text === 'Button Map Options…')"
              " { it.triggered(); return true } } return false })()")
    QtTest.QTest.qWait(400)
    out["menu"] = menu
    pane = child("optionsPane")
    top_row = child("toolRowTop")
    out["open"] = [ev("_tools.isOpen('options')"), pane.isVisible()]
    out["under-top-row"] = round(
        pane.mapToScene(QtCore.QPointF(0, 0)).y()
        - top_row.mapToScene(QtCore.QPointF(0, top_row.height())).y()
    )
    out["groups"] = [
        g for g in ("labels", "editing", "autosave", "view", "colours", "library")
        if child("optionsGroup:" + g) is not None
    ]

    def rows() -> list:
        return sorted(
            c.objectName()[len("option:"):]
            for c in items(pane)
            if c.objectName().startswith("option:") and c.isVisible()
        )

    out["labels-rows"] = rows()
    # A switch changes and keeps its setting.
    before = ev("_opts.values['description-first']")
    row = child("option:description-first")
    switch = next(c for c in row.childItems()
                  if c.metaObject().className().startswith("Switch") and c.isVisible())
    centre = switch.mapToScene(QtCore.QPointF(switch.width() / 2, switch.height() / 2))
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    QtTest.QTest.qWait(300)
    out["switch"] = [before, ev("_opts.values['description-first']"),
                     button_map_options.value("description-first")]
    # Another group: its settings; kept for next time.
    group = child("optionsGroup:editing")
    centre = group.mapToScene(QtCore.QPointF(group.width() / 2, group.height() / 2))
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    QtTest.QTest.qWait(300)
    out["editing-rows"] = rows()
    out["kept-group"] = button_map_options.ButtonMapOptions().paneGroup
    if shots is not None:
        shots.mkdir(parents=True, exist_ok=True)
        win.grabWindow().save(str(shots / "options-pane.png"))
    ev("_opts.paneGroup = 'library'")
    QtTest.QTest.qWait(300)
    library = [c for c in items(pane)
               if c.metaObject().className().startswith("OptionButtonMapLibrary")]
    out["library"] = bool(library) and library[0].isVisible()

    # Editing: the pool on the same edge (top) sits after the pane.
    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
    ev("_opts.paneGroup = 'labels'")
    ev("_tools.setDock('chips', 'top')")
    QtTest.QTest.qWait(300)
    pane_end = ev("_optionsFloat.y") + ev("_optionsFloat.height")
    out["stacked"] = round(ev("_poolFloat.y") - pane_end)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
