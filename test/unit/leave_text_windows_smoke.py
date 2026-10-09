# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S134 (D-01-LEAVE-TEXT) off-screen in the real program: the app starts
as joystick_gremlin.py starts it (fake hardware, a stand-in home folder) so
the program-wide leave-text owner is in place, then real Qt key and mouse
events go to real windows: the Device Library description, Options (Esc
closes it) and Module Setup (Esc does nothing there, 03 S50). Prints
"RESULT name json" per check, "CALLS json" (the Library describe calls) and
"done". test_leave_text_windows.py runs it.

    python test/unit/leave_text_windows_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
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

# --no-filter: the program without the leave-text owner (the proof that
# the checks fail without it).
if "--no-filter" in sys.argv:
    import gremlin.ui.leave_text as _leave_text

    _leave_text.install = lambda app: None  # type: ignore[assignment]

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

Key = QtCore.Qt.Key
NoMod = QtCore.Qt.KeyboardModifier.NoModifier
Left = QtCore.Qt.MouseButton.LeftButton


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def wait_until(check, timeout: float = 10.0):  # noqa: ANN001, ANN201
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            return None
        QtTest.QTest.qWait(20)


def quick(win: QtCore.QObject) -> QtQuick.QQuickWindow:
    return shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)


def ev(win: QtCore.QObject, code: str) -> object:
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


def is_control(item: QtQuick.QQuickItem) -> bool:
    return (
        any(
            item.inherits(k)
            for k in (
                "QQuickAbstractButton",
                "QQuickComboBox",
                "QQuickSpinBox",
                "QQuickSlider",
                "QQuickTextInput",
                "QQuickTextEdit",
                "QQuickMouseArea",
            )
        )
        and item.isEnabled()
    )


def blank_point(win: QtQuick.QQuickWindow, near: QtQuick.QQuickItem) -> QtCore.QPoint:
    """A point in the window over a plain label (no control, text box or
    mouse area under it): a blank spot to click. The label nearest `near`."""
    centre = near.mapToScene(QtCore.QPointF(near.width() / 2, near.height() / 2))
    best = None
    for it in items(win.contentItem()):
        if not (it.inherits("QQuickText") and it.isVisible() and it.width() > 4):
            continue
        if not it.property("text"):
            continue
        p = it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2))
        under = [
            u
            for u in items(win.contentItem())
            if u.isVisible() and is_control(u) and u.contains(u.mapFromScene(p))
        ]
        # A label inside a control (a button's text) is not blank.
        if under:
            continue
        d = (p - centre).manhattanLength()
        if best is None or d < best[0]:
            best = (d, p)
    assert best is not None, "no blank spot found"
    return best[1].toPoint()


def type_text(win: QtQuick.QQuickWindow, text: str) -> None:
    for ch in text:
        shift = ch.isupper()
        QtTest.QTest.keyClick(
            win,
            QtCore.Qt.Key(ord(ch.upper())),
            QtCore.Qt.KeyboardModifier.ShiftModifier if shift else NoMod,
        )
    QtTest.QTest.qWait(50)


def esc(win: QtQuick.QQuickWindow) -> None:
    QtTest.QTest.keyClick(win, Key.Key_Escape, NoMod)
    QtTest.QTest.qWait(150)


def click(win: QtQuick.QQuickWindow, point: QtCore.QPoint) -> None:
    QtTest.QTest.mouseClick(win, Left, NoMod, point)
    QtTest.QTest.qWait(150)


def focus_box(win: QtQuick.QQuickWindow, box: QtQuick.QQuickItem) -> bool:
    win.requestActivate()
    wait_until(lambda: QtGui.QGuiApplication.focusWindow() is win, 3)
    # A real click in the box, as the user starts typing.
    QtTest.QTest.mouseClick(
        win,
        Left,
        NoMod,
        box.mapToScene(
            QtCore.QPointF(min(20.0, box.width() / 2), box.height() / 2)
        ).toPoint(),
    )
    focused = bool(wait_until(lambda: box.hasActiveFocus(), 3))
    # Type at the end of what is there.
    QtTest.QTest.keyClick(win, Key.Key_End, NoMod)
    QtTest.QTest.keyClick(win, Key.Key_End, QtCore.Qt.KeyboardModifier.ControlModifier)
    return focused


def device_library(app, root) -> None:  # noqa: ANN001
    calls: list = []
    api_lib = app.device_library.api.library
    real = api_lib.describe

    def describe(key: str, text: str):  # noqa: ANN202
        calls.append([key, text])
        return real(key, text)

    api_lib.describe = describe
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
        result("library-open", False)
        return
    win = quick(win)
    win.resize(1180, 720)
    rows = wait_until(lambda: ev(win, "deviceLibrary.rows.length"))
    key = ev(
        win, "deviceLibrary.rows.filter(r => r.kind === 'device' || !r.kind)[0].key"
    )
    ev(win, f"deviceLibrary.select('{key}')")
    wait_until(
        lambda: ev(win, "_lib.details.key") == key and ev(win, "_description.visible")
    )
    result("library-open", {"rows": rows, "key": key})
    box = win.findChild(QtQuick.QQuickItem, "libraryDescription") or next(
        i for i in items(win.contentItem()) if i.objectName() == "libraryDescription"
    )
    spot = blank_point(win, box)

    # Type, click a blank spot: the box is left, the text kept and saved.
    focused = focus_box(win, box)
    type_text(win, "click")
    click(win, spot)
    result(
        "library-click-away",
        {
            "focused": focused,
            "focus": box.hasActiveFocus(),
            "text": ev(win, "_description.text"),
            "saved": ev(win, "_lib.details.description"),
            "visible": win.isVisible(),
        },
    )
    # Type, Esc: the box is left, kept and saved; the Library stays open.
    focused = focus_box(win, box)
    type_text(win, " esc")
    esc(win)
    result(
        "library-esc",
        {
            "focused": focused,
            "focus": box.hasActiveFocus(),
            "text": ev(win, "_description.text"),
            "saved": ev(win, "_lib.details.description"),
            "visible": win.isVisible(),
        },
    )
    # Inline Rename (F2): Esc still cancels.
    ev(win, "_lib.startRename()")
    started = bool(wait_until(lambda: ev(win, "_nameField.activeFocus"), 3))
    before = ev(win, "_lib.details.name")
    type_text(win, "zzz")
    esc(win)
    result(
        "library-rename-esc",
        {
            "started": started,
            "renaming": ev(win, "_lib.renaming"),
            "before": before,
            "after": ev(win, "_lib.details.name"),
            "visible": win.isVisible(),
        },
    )
    print("CALLS " + json.dumps(calls), flush=True)
    win.close()
    QtTest.QTest.qWait(100)


def options(app, root) -> None:  # noqa: ANN001
    ev(root, "Helpers.createComponent('DialogOptions.qml')")
    win = wait_until(
        lambda: next(
            (
                w
                for w in app.topLevelWindows()
                if isinstance(w, QtQuick.QQuickWindow)
                and w.isVisible()
                and w.title() == "Options"
            ),
            None,
        )
    )
    if win is None:
        result("options-open", False)
        return
    win = quick(win)
    # The shared SearchBox's text field (01 S141).
    box = ev(win, "_search.field")
    assert isinstance(box, QtQuick.QQuickItem), box
    spot = blank_point(win, box)

    focused = focus_box(win, box)
    type_text(win, "scale")
    click(win, spot)
    result(
        "options-click-away",
        {
            "focused": focused,
            "focus": box.hasActiveFocus(),
            "text": ev(win, "_search.text"),
            "visible": win.isVisible(),
        },
    )
    focused = focus_box(win, box)
    type_text(win, "x")
    esc(win)
    alive = shiboken6.isValid(win) and shiboken6.isValid(box)
    first = {
        "focused": focused,
        "focus": alive and box.hasActiveFocus(),
        "text": ev(win, "_search.text") if alive else None,
        "visible": alive and win.isVisible(),
    }
    if shiboken6.isValid(win):
        esc(win)
    # Closing the window deletes it.
    first["visible-after-second"] = shiboken6.isValid(win) and win.isVisible()
    result("options-esc", first)
    if shiboken6.isValid(win) and win.isVisible():
        win.close()
    QtTest.QTest.qWait(100)


def module_setup(app, root) -> None:  # noqa: ANN001
    ev(root, "_root.openConfigureModule('source', null)")
    win = wait_until(
        lambda: next(
            (
                w
                for w in app.topLevelWindows()
                if isinstance(w, QtQuick.QQuickWindow)
                and w.isVisible()
                and w.title() == "Input Module Setup"
            ),
            None,
        )
    )
    if win is None:
        result("module-open", False)
        return
    win = quick(win)
    win.resize(1200, 800)
    QtTest.QTest.qWait(300)

    def friendly() -> list:
        return [
            i
            for i in items(win.contentItem())
            if i.inherits("QQuickTextField")
            and i.isVisible()
            and i.property("placeholderText") == "Friendly name"
        ]

    boxes = wait_until(friendly)
    if not boxes:
        result("module-open", "no friendly-name boxes")
        return
    box = boxes[0]
    result("module-open", {"boxes": len(boxes), "dirty": ev(win, "claimDirty")})
    spot = blank_point(win, box)

    focused = focus_box(win, box)
    type_text(win, "Trigger")
    esc(win)
    result(
        "module-esc",
        {
            "focused": focused,
            "focus": box.hasActiveFocus(),
            "text": box.property("text"),
            "visible": win.isVisible(),
        },
    )
    click(win, spot)
    result(
        "module-click-away",
        {
            "focus": box.hasActiveFocus(),
            "text": box.property("text"),
            "visible": win.isVisible(),
            # Its onEditingFinished ran (it marks the claims changed).
            "saved": ev(win, "claimDirty"),
        },
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_until(lambda: app.engine.rootObjects())[0]
    for step in (device_library, options, module_setup):
        try:
            step(app, root)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {step.__name__}: {e!r}", flush=True)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
