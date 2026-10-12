# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Device Mapping Editor,
Device Map Options and Keyboard Shortcuts, and prints as JSON what the
fix-list item 4 (D-FIXLIST-B1) needs: the windows' flags (the ×), the
Options pin, closing on a click elsewhere, and the group list's width and
divider. test_b1_optwin.py runs it in its own process and user folder.

    python test/unit/b1_optwin_smoke.py [ui-scale]
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

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

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.config import Configuration  # noqa: E402
from gremlin.ui import device_map_options, ui_scale_option  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)


def wait_for(cond: Callable[[], object], limit: float = 3.0) -> object:
    end = time.monotonic() + limit
    while True:
        value = cond()
        if value or time.monotonic() > end:
            return value
        QtTest.QTest.qWait(25)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj,
        name,
        QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def items(item: QtQuick.QQuickItem) -> list:
    found = [item]
    for c in item.childItems():
        found += items(c)
    return found


def main() -> None:
    if len(sys.argv) > 1:
        ui_scale_option.register()
        Configuration().set(
            ui_scale_option.SCALE_SECTION,
            ui_scale_option.SCALE_GROUP,
            ui_scale_option.SCALE_NAME,
            int(sys.argv[1]),
        )
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openDeviceMappingEditorForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "deviceMappingEditorWindow")
    win.setProperty("width", 1200)
    win.setProperty("height", 800)
    QtTest.QTest.qWait(300)
    out: dict = {"scale": ui_scale_option.active_scale()}

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def activate(window: QtGui.QWindow) -> bool:
        window.requestActivate()
        return bool(wait_for(lambda: QtGui.QGuiApplication.focusWindow() is window))

    def flags(window: QtGui.QWindow) -> dict:
        f = window.flags()
        wt = QtCore.Qt.WindowType
        return {
            "Tool": (f & wt.WindowType_Mask) == wt.Tool,
            "WindowTitleHint": bool(f & wt.WindowTitleHint),
            "WindowSystemMenuHint": bool(f & wt.WindowSystemMenuHint),
            "WindowCloseButtonHint": bool(f & wt.WindowCloseButtonHint),
        }

    ev("_editorWin.openOptions()")
    opts_win = wait_for(
        lambda: (lambda w: w if w is not None and w.isVisible() else None)(
            ev("_optionsWin")
        )
    )
    assert isinstance(opts_win, QtGui.QWindow), opts_win
    ev("_editorWin.openShortcuts()")
    sc_win = ev("_shortcutsWin")
    wait_for(lambda: sc_win.isVisible())
    out["flags"] = {"options": flags(opts_win), "shortcuts": flags(sc_win)}
    ev("_shortcutsWin.pinned = true")
    ev("_shortcutsWin.close()")
    # Keyboard Shortcuts took the focus: the unpinned Options closed.
    out["closed-by-shortcuts"] = bool(wait_for(lambda: not opts_win.isVisible()))
    QtTest.QTest.qWait(200)
    ev("_optionsWin.openFor(_editorWin)")
    wait_for(lambda: opts_win.isVisible())
    activate(opts_win)
    QtTest.QTest.qWait(200)
    out["open-before-pin"] = opts_win.isVisible()

    def child(name: str) -> QtQuick.QQuickItem | None:
        return next(
            (c for c in items(opts_win.contentItem()) if c.objectName() == name), None
        )

    # --- the pin -----------------------------------------------------------
    pin = child("optionsPin")
    out["pin-shown"] = pin is not None and pin.isVisible()
    if pin is not None:
        centre = pin.mapToScene(QtCore.QPointF(pin.width() / 2, pin.height() / 2))
        QtTest.QTest.mouseClick(
            opts_win,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            centre.toPoint(),
        )
        QtTest.QTest.qWait(150)
    out["pin-clicked"] = ev("_optionsWin.pinned")
    out["pin-kept"] = device_map_options.side_panel_state("options").get("pinned")
    # Pinned: going back to the Device Mapping Editor leaves it open.
    activate(opts_win)
    out["activated-map"] = activate(win)
    QtTest.QTest.qWait(300)
    out["pinned-stays"] = opts_win.isVisible()
    # Reset Panels keeps the pin.
    ev("_editorWin.resetPanels()")
    QtTest.QTest.qWait(100)
    out["reset-keeps-pin"] = [
        ev("_optionsWin.pinned"),
        device_map_options.side_panel_state("options").get("pinned"),
    ]
    # Unpinned: going back to the Device Mapping Editor closes it.
    ev("_optionsWin.pinned = false")
    out["unpin-kept"] = device_map_options.side_panel_state("options").get("pinned")
    ev("_optionsWin.openFor(_editorWin)")
    wait_for(lambda: opts_win.isVisible())
    activate(opts_win)
    QtTest.QTest.qWait(100)
    activate(win)
    out["unpinned-closes"] = bool(wait_for(lambda: not opts_win.isVisible()))
    # Not a transient child (its own focus-out is reported): it closes too.
    ev("_optionsWin.close()")
    opts_win.setTransientParent(None)
    opts_win.show()
    wait_for(lambda: opts_win.isVisible())
    activate(opts_win)
    QtTest.QTest.qWait(100)
    activate(win)
    out["unpinned-closes-own"] = bool(wait_for(lambda: not opts_win.isVisible()))

    # --- the group list ----------------------------------------------------
    ev("_optionsWin.pinned = true")
    ev("_optionsWin.openFor(_editorWin)")
    wait_for(lambda: opts_win.isVisible())
    opts_win.resize(1000, 600)
    QtTest.QTest.qWait(300)
    fits = {}
    for g in (
        "labels",
        "editing",
        "right-click",
        "recovery",
        "view",
        "colours",
        "library",
    ):
        row = child("optionsGroup:" + g)
        label = next(
            c
            for c in row.childItems()
            if c.metaObject().className().startswith("Label")
        )
        # The whole name inside its row.
        fits[label.property("text")] = (
            label.x() + label.implicitWidth() <= row.width() + 0.5
        )
    out["names-fit"] = fits
    groups = child("optionsGroups")
    panel = child("deviceMapOptionsPanel")
    out["start-width"] = groups.width() if groups is not None else None
    divider = child("optionsDivider")
    out["divider"] = divider is not None
    if divider is not None:

        def drag(dx: float) -> float:
            p = divider.mapToScene(
                QtCore.QPointF(divider.width() / 2, divider.height() / 2)
            ).toPoint()
            QtTest.QTest.mousePress(
                opts_win,
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.KeyboardModifier.NoModifier,
                p,
            )
            steps = 10
            for i in range(1, steps + 1):
                at = QtCore.QPointF(p + QtCore.QPoint(int(dx * i / steps), 0))
                # A move with the left button held (QTest.mouseMove sends none).
                move = QtGui.QMouseEvent(
                    QtCore.QEvent.Type.MouseMove,
                    at,
                    at,
                    QtCore.Qt.MouseButton.NoButton,
                    QtCore.Qt.MouseButton.LeftButton,
                    QtCore.Qt.KeyboardModifier.NoModifier,
                )
                QtCore.QCoreApplication.sendEvent(opts_win, move)
                QtTest.QTest.qWait(15)
            end = p + QtCore.QPoint(int(dx), 0)
            QtTest.QTest.mouseRelease(
                opts_win,
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.KeyboardModifier.NoModifier,
                end,
            )
            QtTest.QTest.qWait(150)
            return groups.width()

        start = groups.width()
        wider = drag(60)
        out["drag-wider"] = [start, wider]
        out["kept-width"] = [
            device_map_options.options_groups_width(),
            round(wider / (out["scale"] / 100)),
        ]
        out["drag-max"] = [drag(2000), panel.width() / 2]
        out["drag-min"] = [drag(-4000), panel.property("minW")]
        out["min-shows-labels"] = fits.get("Labels")
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
