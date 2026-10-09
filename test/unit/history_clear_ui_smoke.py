# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of Tools > History's Clear History… (test_history_clear_ui.py,
08 S12b, D-08-CLEAR-HISTORY).

A module file is saved twice, then History opens: the red button after
Refresh, its question (Enter answers Cancel), then Clear History clicked,
the red "History cleared" row, and picking it. Prints RESULT {json}.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin import history, util  # noqa: E402
from gremlin.modules import module_file  # noqa: E402


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    out: dict = {}

    def settle() -> None:
        deadline = time.monotonic() + 5
        while history._writer is not None and time.monotonic() < deadline:
            QtTest.QTest.qWait(20)
        history.flush()

    path = util.modules_dir() / "clear_stick.json"
    for word in ("one", "two"):
        module_file.write_json(path, {"device": "Clear Stick", "word": word})
        settle()

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()[0]
        assert not expr.hasError(), expr.error().toString()
        return value

    ev('Helpers.createComponent("DialogHistory.qml", {})')
    QtTest.QTest.qWait(500)
    hist = next(
        w
        for w in app.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow)
        and w.title() == "History"
        and w.isVisible()
    )
    hist.resize(1100, 700)
    QtTest.QTest.qWait(200)

    def hv(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(hist), hist, code)
        value = expr.evaluate()[0]
        assert not expr.hasError(), expr.error().toString()
        return value

    def items() -> list:
        found, pending = [], [hist.contentItem().parentItem() or hist.contentItem()]
        while pending:
            current = pending.pop()
            found.append(current)
            pending.extend(current.childItems())
        return found

    def item(name: str) -> QtQuick.QQuickItem | None:
        return next((i for i in items() if i.objectName() == name), None)

    def shown(target: QtQuick.QQuickItem | None) -> bool:
        while target is not None:
            if not target.property("visible"):
                return False
            target = target.parentItem()
        return True

    def click(target: QtQuick.QQuickItem) -> None:
        centre = target.mapToScene(
            QtCore.QPointF(target.width() / 2, target.height() / 2)
        ).toPoint()
        QtTest.QTest.mouseClick(hist, QtCore.Qt.MouseButton.LeftButton, pos=centre)
        QtTest.QTest.qWait(300)

    def colour(value: object) -> str:
        return value.name(QtGui.QColor.NameFormat.HexArgb) if value is not None else ""

    def fill_colour(button: QtQuick.QQuickItem) -> str:
        return colour(button.property("background").property("color"))

    def asking() -> bool:
        # 01 S140: the shared question (Confirm.ask).
        # (confirmDialog is the Popup; its items are in the window.)
        title = item("confirmTitle")
        return bool(title is not None and shown(title))

    out["danger"] = colour(hv("Style.danger"))
    out["danger-text"] = colour(hv("Style.dangerText"))
    out["fg"] = colour(hv("Style.fg"))
    out["rows-before"] = hv("_list.count")
    out["module-file"] = path.is_file()

    clear = item("historyClear")
    out["has-button"] = clear is not None
    if clear is None:
        print("RESULT " + json.dumps(out), flush=True)
        return
    refresh = next(i for i in items() if i.property("text") == "Refresh")
    out["button"] = {
        "text": clear.property("text"),
        "colour": fill_colour(clear),
        "after-refresh": clear.mapToScene(QtCore.QPointF(0, 0)).x()
        > refresh.mapToScene(QtCore.QPointF(0, 0)).x(),
        "same-row": abs(
            clear.mapToScene(QtCore.QPointF(0, 0)).y()
            - refresh.mapToScene(QtCore.QPointF(0, 0)).y()
        )
        < 2,
    }
    found = history.summary()
    out["summary"] = found

    # Asked first; Enter answers the default, Cancel.
    click(clear)
    QtTest.QTest.qWait(300)
    out["asked"] = asking()
    out["question"] = (
        item("confirmText").property("text")
        + " "
        + item("confirmLastLine").property("text")
    )
    out["dialog-title"] = item("confirmTitle").property("text")
    out["cancel-focused"] = bool(item("confirmCancel").property("activeFocus"))
    go = item("confirmAction")
    out["go"] = {"text": go.property("text"), "colour": fill_colour(go)}
    QtTest.QTest.keyClick(hist, QtCore.Qt.Key.Key_Return)
    QtTest.QTest.qWait(400)
    out["after-enter"] = {
        "open": asking(),
        "rows": hv("_list.count"),
        "entries": history.summary()["entries"],
    }

    # Clear History clicked.
    click(clear)
    QtTest.QTest.qWait(300)
    click(item("confirmAction"))
    settle()
    QtTest.QTest.qWait(300)
    out["after-clear"] = {
        "open": asking(),
        "rows": hv("_list.count"),
        "message": hv("message"),
        "module-file": path.is_file(),
    }
    entry_id = hv("_model.data(_model.index(0, 0), Qt.UserRole + 1)")
    row = item(f"historyEntry:{entry_id}")
    title = next(
        (i for i in items() if i.property("text") == "History cleared"
         and row is not None and row.isAncestorOf(i)),
        None,
    )
    out["row"] = {
        "found": row is not None,
        "title-colour": colour(title.property("color")) if title else "",
    }

    # Picking it: the note, no Restore, no Previous/Next Change.
    click(row)
    out["picked"] = {
        "selected": hv("selected") == entry_id,
        "note": item("historyClearedNote").property("text"),
        "note-shown": shown(item("historyClearedNote")),
        "what": item("historyClearedWhat").property("text"),
        "restore-before": shown(item("historyRestoreBefore")),
        "restore-after": shown(item("historyRestoreAfter")),
        "previous": shown(item("historyPreviousChange")),
        "next": shown(item("historyNextChange")),
    }

    # 01 S141: the shared search box. Ctrl+F goes to it, typing filters,
    # the line under it counts, Esc clears it.
    box = item("historySearch")
    field = next(
        (i for i in items() if i.objectName() == "searchField"
         and box is not None and box.isAncestorOf(i)),
        None,
    )
    out["search"] = {"shared": field is not None}
    if field is not None:
        QtTest.QTest.keyClick(
            hist, QtCore.Qt.Key.Key_F, QtCore.Qt.KeyboardModifier.ControlModifier
        )
        QtTest.QTest.qWait(100)
        out["search"]["ctrl-f"] = bool(field.property("activeFocus"))
        for key in (QtCore.Qt.Key.Key_Z, QtCore.Qt.Key.Key_Z, QtCore.Qt.Key.Key_Q):
            QtTest.QTest.keyClick(hist, key)
        QtTest.QTest.qWait(200)
        count = next(
            (i for i in items() if i.objectName() == "searchCount"
             and box.isAncestorOf(i)),
            None,
        )
        out["search"]["rows"] = hv("_list.count")
        out["search"]["line"] = count.property("text") if count else ""
        out["search"]["line-shown"] = shown(count)
        QtTest.QTest.keyClick(hist, QtCore.Qt.Key.Key_Escape)
        QtTest.QTest.qWait(200)
        out["search"]["after-esc"] = {
            "text": field.property("text"),
            "rows": hv("_list.count"),
            "window-open": hist.isVisible(),
        }
    print("RESULT " + json.dumps(out), flush=True)


# Any error ends the run (the app's threads would keep it alive).
try:
    main()
except BaseException:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
os._exit(0)
