# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens Help (F1) from
the main window and works its topic list (01 S138): drags and double-clicks
the handle, closes and reopens Help, clicks chapter headings and Expand all
/ Collapse all, opens a topic and searches. Prints as JSON what the list
showed. test_help_list.py runs it in its own process with a fresh user
folder.
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
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin import clock  # noqa: E402

messages: list[str] = []


def _capture(mode, context, text: str) -> None:  # noqa: ANN001
    messages.append(text)


QtCore.qInstallMessageHandler(_capture)

LEFT = QtCore.Qt.MouseButton.LeftButton
NOMOD = QtCore.Qt.KeyboardModifier.NoModifier
CTRL = QtCore.Qt.KeyboardModifier.ControlModifier


def wait_until(cond, limit_ms: int = 10000) -> bool:  # noqa: ANN001
    end = clock.monotonic() + limit_ms / 1000.0
    qapp = QtCore.QCoreApplication.instance()
    while True:
        if cond():
            return True
        if clock.monotonic() > end:
            return False
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        clock.sleep(0.005)


def settle(ms: int = 250) -> None:
    wait_until(lambda: False, ms)


def ev(obj: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString() + " :: " + code[:200])
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def help_windows() -> list:
    return [
        w for w in QtGui.QGuiApplication.topLevelWindows()
        if w.isVisible() and (w.title() == "Help" or w.title().startswith("Help — "))
    ]


def find_all(item: QtQuick.QQuickItem, name: str) -> list:
    """Visible items by objectName, through the visual tree."""
    out = []
    if item.objectName() == name and item.isVisible():
        out.append(item)
    for child in item.childItems():
        out.extend(find_all(child, name))
    return out


def find_item(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
    found = find_all(window.contentItem(), name)
    return found[0] if found else None


def centre(item: QtQuick.QQuickItem) -> QtCore.QPoint:
    return item.mapToScene(
        QtCore.QPointF(item.width() / 2, item.height() / 2)
    ).toPoint()


def click(window: QtQuick.QQuickWindow, item: QtQuick.QQuickItem) -> None:
    QtTest.QTest.mouseClick(window, LEFT, NOMOD, centre(item))
    settle(300)


def drag_handle(window: QtQuick.QQuickWindow, dx: int) -> bool:
    """Drags the list's handle dx pixels sideways with the mouse."""
    handle = find_item(window, "helpListHandle")
    if handle is None:
        return False
    start = centre(handle)
    QtTest.QTest.mousePress(window, LEFT, NOMOD, start)
    steps = 10
    for i in range(1, steps + 1):
        at = QtCore.QPoint(start.x() + dx * i // steps, start.y())
        QtTest.QTest.mouseMove(window, at)
        settle(15)
    QtTest.QTest.mouseRelease(
        window, LEFT, NOMOD, QtCore.QPoint(start.x() + dx, start.y())
    )
    settle(300)
    return True


def model_data(item: QtQuick.QQuickItem) -> dict | None:
    """The row's modelData: on the item or the nearest delegate above it."""
    node = item
    while node is not None:
        value = node.property("modelData")
        if value is not None:
            value = value.toVariant() if hasattr(value, "toVariant") else value
            if isinstance(value, dict):
                return value
        node = node.parentItem()
    return None


def press_f1(window: QtGui.QWindow) -> None:
    window.requestActivate()
    wait_until(lambda: window.isActive(), 3000)
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_F1)
    wait_until(lambda: bool(help_windows()), 4000)
    settle(400)


def open_help() -> QtQuick.QQuickWindow:
    press_f1(win)
    found = help_windows()
    if not found:
        raise RuntimeError("Help did not open")
    return found[0]


def close_help(help_win: QtGui.QWindow) -> None:
    help_win.close()
    wait_until(lambda: not help_windows(), 3000)
    settle(400)


_LIST = (
    "(function(){var t=[],c=[],f={};for(var i=0;i<_rows.length;++i){var r=_rows[i];"
    "if(r.kind==='topic')t.push([r.id,r.chapterId]);"
    "else if(r.kind==='chapter')c.push(r.chapterId)}"
    "var all=Book.chapters();for(var j=0;j<all.length;++j)"
    "f[all[j].id]=typeof isFolded==='function'?isFolded(all[j].id):null;"
    "return {topics:t,chapters:c,folded:f,current:_current?_current.chapterId:'',"
    "currentId:_currentId,searching:_searching}})()"
)


def list_state(help_win: QtCore.QObject) -> dict:
    return ev(help_win, _LIST) or {}


def section(name: str, fn) -> None:  # noqa: ANN001
    try:
        out[name] = fn()
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"{name}: {exc!r}")


out: dict = {"errors": []}
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))

help_win = open_help()
out["dp180"] = ev(help_win, "Style.dp(180)")
out["dp290"] = ev(help_win, "Style.dp(290)")
out["dp26"] = ev(help_win, "Style.dp(26)")
out["book"] = ev(help_win, "_book.length")


def widths() -> dict:
    pane = find_item(help_win, "helpListPane")
    return {
        "list": ev(help_win, "listWidth"),
        "pane": round(pane.width()) if pane is not None else None,
        "half": ev(help_win, "Math.floor(width / 2)"),
    }


# 1. Resize with the handle.
def resize() -> dict:
    res: dict = {"start": widths()}
    res["dragged"] = drag_handle(help_win, 100)
    res["plus100"] = widths()
    drag_handle(help_win, 3000)
    res["max"] = widths()
    drag_handle(help_win, -3000)
    res["min"] = widths()
    drag_handle(help_win, 140)
    res["kept_before"] = widths()
    return res


section("resize", resize)


def reopen() -> dict:
    global help_win
    close_help(help_win)
    help_win = open_help()
    res = {"after": widths()}
    handle = find_item(help_win, "helpListHandle")
    if handle is not None:
        QtTest.QTest.mouseDClick(help_win, LEFT, NOMOD, centre(handle))
        settle(300)
    res["reset"] = widths()
    return res


section("reopen", reopen)


# 2. Single-spaced topic rows.
def rows() -> dict:
    found = find_all(help_win.contentItem(), "helpTopicRow")
    return {"heights": [round(i.height(), 1) for i in found]}


section("rows", rows)


# 3. Folding.
def folding() -> dict:
    res: dict = {"opened": list_state(help_win)}
    expand = find_item(help_win, "expandAll")
    collapse = find_item(help_win, "collapseAll")
    res["buttons_whole_book"] = [expand is not None, collapse is not None]
    if expand is not None:
        click(help_win, expand)
    res["expanded"] = list_state(help_win)
    if collapse is not None:
        click(help_win, collapse)
    res["collapsed"] = list_state(help_win)

    # Click a chapter heading twice (all folded: every heading is in view).
    heads = find_all(help_win.contentItem(), "helpChapterRow")
    heads.sort(key=lambda i: i.mapToScene(QtCore.QPointF(0, 0)).y())
    res["heads"] = len(heads)
    target = heads[1] if len(heads) > 1 else None
    if target is not None:
        data = model_data(target)
        state = list_state(help_win)
        cid = data.get("chapterId") if data else state["chapters"][1]
        res["clicked_chapter"] = cid
        click(help_win, target)
        res["toggled_open"] = list_state(help_win)
        heads = find_all(help_win.contentItem(), "helpChapterRow")
        again = None
        for h in heads:
            d = model_data(h)
            if d and d.get("chapterId") == cid:
                again = h
        if again is None:
            heads.sort(key=lambda i: i.mapToScene(QtCore.QPointF(0, 0)).y())
            again = heads[1]
        click(help_win, again)
        res["toggled_shut"] = list_state(help_win)

    # Opening a topic in a folded chapter unfolds it.
    ev(help_win, "collapseAll()")
    settle(200)
    pick = ev(help_win, "_book[_book.length - 1].id")
    res["show_id"] = pick
    res["show_chapter"] = ev(help_win, "_book[_book.length - 1].chapterId")
    ev(help_win, f"showTopic({json.dumps(pick)})")
    settle(300)
    res["shown"] = list_state(help_win)

    # An area's chapter: no Expand all / Collapse all.
    ev(help_win, "chapter = 'device-library'")
    settle(300)
    res["buttons_area"] = [
        find_item(help_win, "expandAll") is not None,
        find_item(help_win, "collapseAll") is not None,
    ]
    ev(help_win, "chapter = ''")
    settle(300)
    return res


section("folding", folding)


# 3b / 4. Search (typed): matching topics of folded chapters show; clearing
# restores the folds.
def search() -> dict:
    res: dict = {}
    try:
        ev(help_win, "collapseAll()")
    except RuntimeError as exc:
        res["no_collapse"] = str(exc)
    settle(200)
    res["before"] = list_state(help_win)
    help_win.requestActivate()
    wait_until(lambda: help_win.isActive(), 3000)
    QtTest.QTest.keyClick(help_win, QtCore.Qt.Key.Key_F, CTRL)
    settle(200)
    for ch in "device":
        QtTest.QTest.keyClick(help_win, ch)
    settle(600)
    res["results"] = ev(
        help_win,
        "(function(){var o=[];for(var i=0;i<_results.length;++i)"
        "o.push([_results[i].topic.id,_results[i].topic.chapterId]);return o})()",
    )
    res["during"] = list_state(help_win)
    QtTest.QTest.keyClick(help_win, QtCore.Qt.Key.Key_A, CTRL)
    QtTest.QTest.keyClick(help_win, QtCore.Qt.Key.Key_Backspace)
    settle(600)
    res["after"] = list_state(help_win)
    return res


section("search", search)


_RESULTS = (
    "(function(){var o=[];for(var i=0;i<_results.length;++i)"
    "o.push(_results[i].topic.id);return o})()"
)


# A whole search pasted into the empty box at once (one text change) lists
# its matches.
def paste() -> dict:
    res: dict = {"empty_before": ev(help_win, "_search.text") == ""}
    help_win.requestActivate()
    wait_until(lambda: help_win.isActive(), 3000)
    QtTest.QTest.keyClick(help_win, QtCore.Qt.Key.Key_F, CTRL)
    settle(200)
    QtGui.QGuiApplication.clipboard().setText("memory")
    settle(100)
    QtTest.QTest.keyClick(help_win, QtCore.Qt.Key.Key_V, CTRL)
    settle(600)
    res["text"] = ev(help_win, "_search.text")
    res["results"] = ev(help_win, _RESULTS)
    res["listed"] = list_state(help_win)["topics"]
    QtTest.QTest.keyClick(help_win, QtCore.Qt.Key.Key_A, CTRL)
    QtTest.QTest.keyClick(help_win, QtCore.Qt.Key.Key_Backspace)
    settle(400)
    return res


section("paste", paste)

out["binding_warnings"] = [m for m in messages if "Overwriting binding" in m][:10]
out["qml_errors"] = [
    m for m in messages
    if any(k in m for k in ("Error", "is not a function", "is not defined"))
    and "Help" in m
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
