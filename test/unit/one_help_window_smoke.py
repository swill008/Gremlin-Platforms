# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and opens Help from the
main window, the Device Library and the Button Map (01 S128, 10 S42),
printing as JSON what the one Help window showed. test_one_help_window.py
runs it in its own process with a fresh user folder.
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


def ev(obj: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString() + " :: " + code[:200])
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def visible(pred) -> list:  # noqa: ANN001
    return [
        w for w in QtGui.QGuiApplication.topLevelWindows()
        if w.isVisible() and pred(w.title())
    ]


def help_windows() -> list:
    return visible(lambda t: t == "Help" or t.startswith("Help — "))


def help_items(win: QtCore.QObject, bar: str) -> list | None:
    return ev(win, (
        "(function(){var ms=" + bar + ".menus;var o=[];"
        "for(var i=0;i<ms.length;++i){if(ms[i].title!=='Help')continue;"
        "for(var j=0;j<ms[i].count;++j){var it=ms[i].itemAt(j);"
        "if(!it||it.text===undefined||it.text==='')continue;"
        "o.push({text:String(it.text),hint:String(it.hint||'')})}}"
        "return o})()"
    ))


_STATE = (
    "(function(){var c={};for(var i=0;i<_topics.length;++i)"
    "c[_topics[i].chapterId]=1;var heads=[];"
    "for(var j=0;j<_rows.length;++j)if(_rows[j].kind==='chapter')"
    "heads.push(_rows[j].text);"
    "return {chapter:chapter,title:title,count:_topics.length,"
    "chapters:Object.keys(c),heads:heads,full:_book.length,"
    "current:_currentId,currentChapter:_current?_current.chapterId:''}})()"
)


def state() -> dict:
    found = help_windows()
    out: dict = {"windows": len(found)}
    if found:
        out.update(ev(found[0], _STATE) or {})
    return out


def find_item(item: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem | None:
    """The first visible item by objectName, through the visual tree
    (Repeater rows are not QObject children)."""
    if item.objectName() == name and item.isVisible():
        return item
    for child in item.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None


def click_object(window: QtQuick.QQuickWindow, name: str) -> bool:
    item = find_item(window.contentItem(), name)
    if item is None or not item.isVisible():
        return False
    centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(
        window, QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint(),
    )
    wait_until(lambda: False, 300)
    return True


def press_f1(window: QtGui.QWindow) -> None:
    window.requestActivate()
    wait_until(lambda: window.isActive(), 3000)
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_F1)
    wait_until(lambda: bool(help_windows()), 4000)
    wait_until(lambda: False, 300)


out: dict = {"errors": []}
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))

try:
    out["main_items"] = help_items(win, "menuBar")
    # Main window F1: the whole book.
    press_f1(win)
    out["main_f1"] = state()
    help_win = help_windows()[0]

    # A link in a topic's text opens that topic.
    first = ev(help_win, "_topics[0].id")
    target = ev(help_win, "_topics[_topics.length - 1].id")
    body = help_win.findChild(QtCore.QObject, "topicBody")
    body.linkActivated.emit("topic:" + str(target))
    wait_until(lambda: False, 200)
    out["link_opened"] = ev(help_win, "_currentId") == target

    # A Related topics link (a real click) opens that topic.
    rel = ev(help_win, (
        "(function(){for(var i=0;i<_book.length;++i){var r=_book[i].related;"
        "if(r&&r.length&&Book.find(r[0]))return [_book[i].id,Book.find(r[0]).id]}"
        "return null})()"
    ))
    out["related_clicked"] = False
    out["related_opened"] = False
    if rel:
        ev(help_win, f"showTopic({json.dumps(rel[0])})")
        wait_until(lambda: False, 300)
        out["related_clicked"] = click_object(help_win, "relatedLink")
        out["related_opened"] = ev(help_win, "_currentId") == rel[1]
    ev(help_win, f"showTopic({json.dumps(first)})")

    # Device Library F1: its chapter only, in the same window.
    ev(win, "Commands.trigger('tools.deviceLibrary')")
    wait_until(lambda: bool(visible(lambda t: t == "Device Library")), 8000)
    lib = visible(lambda t: t == "Device Library")[0]
    out["library_items"] = help_items(lib, "_menuBar")
    press_f1(lib)
    out["library_f1"] = state()
    help_win = help_windows()[0]
    out["full_clicked"] = click_object(help_win, "viewFullHelp")
    out["library_full"] = state()
    out["back_clicked"] = click_object(help_win, "viewChapterOnly")
    out["library_back"] = state()

    # The Button Map: its chapter only.
    ev(win, "Commands.trigger('tools.buttonMap')")
    wait_until(lambda: bool(visible(lambda t: t.startswith("Button Map"))), 8000)
    bm = visible(lambda t: t.startswith("Button Map"))[0]
    out["buttonmap_items"] = help_items(bm, "_menuBar")
    help_win.close()
    wait_until(lambda: not help_windows(), 3000)
    press_f1(bm)
    out["buttonmap_f1"] = state()

    # Main F1 again: the whole book, in the same window.
    press_f1(win)
    out["main_again"] = state()
except Exception as exc:  # noqa: BLE001
    out["errors"].append(repr(exc))

out["qml_errors"] = [
    m for m in messages
    if any(k in m for k in ("Error", "is not a function", "is not defined"))
    and "Help" in m
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
