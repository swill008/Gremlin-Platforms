# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S135 (D-01-ONE-RENAME) in the Device Library, off-screen in the real
program (started as joystick_gremlin.py starts it, fake hardware, a
stand-in home folder) with real Qt key and mouse events: F2 opens the
shared Rename box focused with the whole name selected, typing replaces it,
Enter or a click away saves once, Esc cancels, an empty or unchanged name
is not saved. Prints "RESULT name json" per check, "CALLS json" (the
library rename calls) and "done". test_rename_library.py runs it.

    python test/unit/rename_library_smoke.py
"""

from __future__ import annotations

import json
import os
import sys

import leave_text_windows_smoke as lt  # fake hardware, app helpers
from PySide6 import QtCore, QtGui, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

Key = QtCore.Qt.Key
NoMod = QtCore.Qt.KeyboardModifier.NoModifier
ev = lt.ev
result = lt.result
wait_until = lt.wait_until


def key(win: QtQuick.QQuickWindow, k: QtCore.Qt.Key) -> None:
    QtTest.QTest.keyClick(win, k, NoMod)
    QtTest.QTest.qWait(150)


def field(win: QtQuick.QQuickWindow) -> QtQuick.QQuickItem:
    return next(
        i for i in lt.items(win.contentItem()) if i.objectName() == "libraryNameField"
    )


def typing_box(win: QtQuick.QQuickWindow) -> QtQuick.QQuickItem | None:
    """The text box with the cursor, when it is the rename box (or inside
    it); None otherwise."""
    box = win.activeFocusItem()
    outer = field(win)
    it = box
    while it is not None:
        if it is outer:
            return box
        it = it.parentItem()
    return None


def state(win: QtQuick.QQuickWindow) -> dict:
    box = typing_box(win)
    return {
        "open": field(win).isVisible(),
        "focused": box is not None,
        "text": box.property("text") if box is not None else None,
        "selected": box.property("selectedText") if box is not None else None,
        "name": ev(win, "_lib.details.name"),
        "visible": win.isVisible(),
    }


def press_f2(win: QtQuick.QQuickWindow) -> dict:
    win.requestActivate()
    wait_until(lambda: QtGui.QGuiApplication.focusWindow() is win, 3)
    key(win, Key.Key_F2)
    wait_until(lambda: typing_box(win) is not None, 3)
    return state(win)


def device_library(app, root) -> None:  # noqa: ANN001
    calls: list = []
    api_lib = app.device_library.api.library
    real = api_lib.rename

    def rename(k: str, name: str):  # noqa: ANN202
        calls.append([k, name])
        return real(k, name)

    api_lib.rename = rename
    ev(root, "_root.openDeviceLibrary('', '', '')")
    win = wait_until(
        lambda: next(
            (
                w
                for w in app.topLevelWindows()
                if isinstance(w, QtQuick.QQuickWindow)
                and w.isVisible()
                and ev(w, "typeof _description !== 'undefined'") is True
            ),
            None,
        )
    )
    if win is None:
        result("open", False)
        return
    win = lt.quick(win)
    win.resize(1180, 720)
    wait_until(lambda: ev(win, "deviceLibrary.rows.length"))
    k = ev(win, "deviceLibrary.rows.filter(r => r.kind === 'device' || !r.kind)[0].key")
    ev(win, f"deviceLibrary.select('{k}')")
    wait_until(lambda: ev(win, "_lib.details.key") == k)
    first = ev(win, "_lib.details.name")
    result("open", {"key": k, "name": first})

    # F2: open, focused, the whole name selected; typing replaces; Enter.
    result("f2", press_f2(win))
    lt.type_text(win, "alpha")
    result("typed", state(win))
    key(win, Key.Key_Return)
    wait_until(lambda: ev(win, "_lib.details.name") == "alpha", 3)
    result("enter", {**state(win), "calls": list(calls)})

    # A click away saves once.
    press_f2(win)
    lt.type_text(win, "beta")
    spot = lt.blank_point(win, field(win))
    lt.click(win, spot)
    wait_until(lambda: ev(win, "_lib.details.name") == "beta", 3)
    result("click-away", {**state(win), "calls": list(calls)})

    # Esc cancels: the old name stays, nothing saved.
    press_f2(win)
    lt.type_text(win, "zzz")
    lt.esc(win)
    result("esc", {**state(win), "calls": list(calls)})

    # Empty: the old name stays, nothing saved.
    press_f2(win)
    key(win, Key.Key_Backspace)
    empty = state(win)["text"]
    key(win, Key.Key_Return)
    result("empty", {**state(win), "typed": empty, "calls": list(calls)})

    # Unchanged: nothing saved.
    press_f2(win)
    key(win, Key.Key_Return)
    result("unchanged", {**state(win), "calls": list(calls)})

    # The rename button opens it the same way.
    button = next(
        i
        for i in lt.items(win.contentItem())
        if i.objectName() == "libraryRenameButton"
    )
    lt.click(
        win,
        button.mapToScene(
            QtCore.QPointF(button.width() / 2, button.height() / 2)
        ).toPoint(),
    )
    wait_until(lambda: typing_box(win) is not None, 3)
    opened = state(win)
    lt.esc(win)
    result("button", {**opened, "calls": list(calls)})

    print("CALLS " + json.dumps(calls), flush=True)
    win.close()
    QtTest.QTest.qWait(100)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_until(lambda: app.engine.rootObjects())[0]
    try:
        device_library(app, root)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR device_library: {e!r}", flush=True)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
