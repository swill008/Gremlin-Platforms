# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, two sticks with a map
each) and drives the Button Map's Layers search from the window (07 S102):
Ctrl+F, View > Search layers… in the Command Palette, the kinds and search
kept when another device's map is shown, and both gone after the window
closes and opens again. Prints what it saw as JSON.
test_layers_search_window.py runs it in its own process and user folder.

    python test/unit/layers_search_window_smoke.py

Waits poll for what is checked with a generous limit; none sleeps a fixed
time (GL-001).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

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

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
from gremlin.ui import hardware_profile  # noqa: E402

# Two sticks, each with a map of five chips.
stick = fake.devices[0]
other = fake_hardware.raw_device(is_virtual=False)
other.device_guid.Data1 += 7
other.name = b"Other Stick"
fake.devices.append(other)
GUID = str(dill.GUID(stick.device_guid).uuid)
OTHER_GUID = str(dill.GUID(other.device_guid).uuid)
NODES = [
    {
        "kind": "btn",
        "id": f"b{i}",
        "label": f"Button {i}",
        "chipFx": 0.2 + 0.05 * i,
        "chipFy": 0.3,
    }
    for i in range(1, 6)
]
for _name, _guid in (("pJoy Pro", GUID), ("Other Stick", OTHER_GUID)):
    _map = hardware_profile.module_json_path(_name, _guid)
    _map.parent.mkdir(parents=True, exist_ok=True)
    _map.write_text(
        json.dumps({"kind": "control.hardware", "device": _name, "nodes": NODES}),
        encoding="utf-8",
    )

import joystick_gremlin  # noqa: E402

Key = QtCore.Qt.Key
Mod = QtCore.Qt.KeyboardModifier
# Generous: a busy PC is slow, never wrong.
LIMIT_S = 15.0


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj,
        name,
        QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def same(a: object, b: object) -> bool:
    return (
        a is not None
        and b is not None
        and shiboken6.getCppPointer(a)[0] == shiboken6.getCppPointer(b)[0]
    )


def wait_for(check: Callable[[], object], limit: float = LIMIT_S) -> object:
    """Runs the event loop until check() is true (its value), up to limit."""
    end = time.monotonic() + limit
    while True:
        value = check()
        if value or time.monotonic() > end:
            return value
        QtTest.QTest.qWait(25)


def ev(obj: QtCore.QObject, code: str) -> object:
    context = QtQml.qmlContext(obj)
    assert context is not None
    expr = QtQml.QQmlExpression(context, obj, code)
    value = expr.evaluate()
    if expr.hasError():
        return "error: " + expr.error().description()
    value = value[0] if isinstance(value, tuple) else value
    if hasattr(value, "toVariant"):
        value = value.toVariant()
    return value


# The Layers search box has the keyboard: the window's focus is a text
# field inside the Layers panel.
IN_SEARCH = (
    "(function() { var f = _buttonMap.activeFocusItem; var p = f;"
    " while (p && p !== _layersPanel) p = p.parent;"
    " return !!p && f.selectAll !== undefined && f.cursorPosition !== undefined })()"
)
FILTER = (
    "JSON.stringify({ kinds: _layersPanel.kinds, query: _layersPanel.searchText })"
)


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {}

    def open_map(name: str, guid: str) -> QtCore.QObject:
        card = {"rawName": name, "name": name, "guid": guid}
        call(root, "openButtonMapForCard", card)
        win = wait_for(lambda: call(root, "buttonMapWindow"))
        assert isinstance(win, QtCore.QObject)
        wait_for(lambda: ev(win, "mapShown && targetName === '" + name + "'"))
        return win

    def edit(win: QtCore.QObject) -> None:
        call(win, "enterEdit")
        wait_for(lambda: ev(cast(QtCore.QObject, win),
                            "editing && _ed() !== null && _ed().seeded"
                            " && !_baseWanted"))

    def focus_map(win: QtCore.QObject) -> None:
        ev(win, "_buttonMap.contentItem.forceActiveFocus()")
        wait_for(lambda: not ev(win, IN_SEARCH))

    win = open_map("pJoy Pro", GUID)
    edit(win)
    win.requestActivate()
    out["active"] = bool(wait_for(win.isActive))

    # Ctrl+F with Layers closed: opens it and goes to the box.
    ev(win, "_tools.setOpen('layers', false)")
    focus_map(win)
    out["layers-before"] = ev(win, "_tools.isOpen('layers')")
    QtTest.QTest.keyClick(win, Key.Key_F, Mod.ControlModifier)
    out["ctrl-f-opens-layers"] = bool(wait_for(
        lambda: ev(win, "_tools.isOpen('layers') && _layersPanel.visible") is True))
    out["ctrl-f-focuses-search"] = bool(wait_for(lambda: ev(win, IN_SEARCH) is True))
    # With Layers already open, it goes to the box again.
    focus_map(win)
    QtTest.QTest.keyClick(win, Key.Key_F, Mod.ControlModifier)
    out["ctrl-f-when-open"] = bool(wait_for(lambda: ev(win, IN_SEARCH) is True))

    # The Command Palette lists View > Search layers… and runs it.
    ev(win, "_tools.setOpen('layers', false)")
    focus_map(win)
    ev(win, "_palette.open()")
    wait_for(lambda: ev(win, "_palette.opened"))
    ev(win, "_palette.search('search layers')")
    listed = ev(win, "_palette.describe()") or []
    out["palette-lists"] = list(listed)
    out["palette-shortcut"] = ev(
        win,
        "(function() { var c = _palette.results[0]; return c ? c.shortcut : '' })()",
    )
    ev(win, "_palette.runPick(0)")
    out["palette-opens-layers"] = bool(wait_for(
        lambda: ev(win, "_tools.isOpen('layers') && _layersPanel.visible") is True))
    out["palette-focuses-search"] = out["palette-opens-layers"] and bool(
        wait_for(lambda: ev(win, IN_SEARCH) is True))

    # Kinds and search stay when another device's map is shown.
    panel = ev(win, "_layersPanel")
    out["set-filter"] = ev(
        win,
        "_layersPanel.kinds = ['chip']; _layersPanel.searchText = 'Button 3'; true",
    )
    out["filter-before-switch"] = ev(win, FILTER)
    call(win, "discardEdit")
    call(win, "openForDevice", "Other Stick", "", OTHER_GUID)
    wait_for(lambda: ev(win, "mapShown && targetName === 'Other Stick'"))
    edit(win)
    out["switched"] = ev(win, "targetName")
    out["same-panel-after-switch"] = same(ev(win, "_layersPanel"), panel)
    out["filter-after-switch"] = ev(win, FILTER)

    # Closing the Button Map and opening it again: none and empty.
    call(win, "discardEdit")
    old = win
    ev(win, "_buttonMap.close()")
    wait_for(lambda: not same(call(root, "buttonMapWindow"), old))
    win = open_map("pJoy Pro", GUID)
    out["new-window"] = not same(win, old)
    edit(win)
    out["filter-after-reopen"] = ev(win, FILTER)

    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    finally:
        # The program's threads would keep it running after a failed check.
        sys.stdout.flush()
        os._exit(1)
