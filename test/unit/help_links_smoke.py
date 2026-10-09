# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and opens Help to work
its Open › / Show me › links (01 S139, D-01-HELP-LINKS). Prints as JSON what
happened. Two modes:

- ``dialog``: a stand-in Style.helpLinks records reveal() calls and says
  show: links can't be shown; one topic's text is swapped (in memory) for
  three links; real mouse moves and clicks on them.
- ``resolve``: the program's own Style.helpLinks checks every open:/show:
  link in the whole book.

test_help_links.py and test_help_links_resolve.py run it in its own process
with a fresh user folder.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
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

MODE = sys.argv[1] if len(sys.argv) > 1 else "dialog"

messages: list[str] = []


def _capture(mode, context, text: str) -> None:  # noqa: ANN001
    messages.append(text)


QtCore.qInstallMessageHandler(_capture)

LEFT = QtCore.Qt.MouseButton.LeftButton
NOMOD = QtCore.Qt.KeyboardModifier.NoModifier


class _UrlCatcher(QtCore.QObject):
    """Takes open:/show: URLs handed to the desktop (old code did that), so
    nothing outside the program starts."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    @QtCore.Slot(QtCore.QUrl)
    def take(self, url: QtCore.QUrl) -> None:
        self.urls.append(url.toString())


catcher = _UrlCatcher()
for scheme in ("open", "show"):
    QtGui.QDesktopServices.setUrlHandler(scheme, catcher, "take")


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


def find_item(item: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem | None:
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None


def step(name: str, fn) -> None:  # noqa: ANN001
    """Runs one step; an error is recorded and the next step still runs."""
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
ev(win, "Commands.trigger('help.guide')")
wait_until(lambda: bool(help_windows()), 8000)
settle(300)
hw = help_windows()[0]
body = hw.findChild(QtQuick.QQuickItem, "topicBody")

_ANCHOR = re.compile(r'<a\b[^>]*\bhref\s*=\s*"([^"]*)"[^>]*>(.*?)</a>', re.I | re.S)


def link_point(text: str, nth: int = 0) -> QtCore.QPoint:
    """The scene point in the middle of the nth link text in the body."""
    plain = str(ev(body, "getText(0, length)"))
    at = -1
    for _ in range(nth + 1):
        at = plain.index(text, at + 1)
    rect = ev(body, f"positionToRectangle({at + 1})")
    x = rect.x() if hasattr(rect, "x") else rect["x"]
    y = rect.y() if hasattr(rect, "y") else rect["y"]
    h = rect.height() if hasattr(rect, "height") else rect["height"]
    return body.mapToScene(QtCore.QPointF(x + 2, y + h / 2)).toPoint()


def hover(point: QtCore.QPoint) -> None:
    QtTest.QTest.mouseMove(hw, point)
    settle(150)


def click(point: QtCore.QPoint) -> None:
    hover(point)
    QtTest.QTest.mouseClick(hw, LEFT, NOMOD, point)
    settle(250)


def tip_shown() -> dict:
    tip = find_item(hw.contentItem(), "linkTip")
    if tip is None:
        return {"found": False}
    for child in tip.findChildren(QtCore.QObject):
        if "ToolTip" in child.metaObject().className():
            return {"found": True, "visible": bool(child.property("visible")),
                    "text": str(child.property("text"))}
    return {"found": False, "children": [
        c.metaObject().className() for c in tip.findChildren(QtCore.QObject)][:10]}


def run_dialog() -> None:
    topic = str(ev(hw, "_book[0].id"))
    other = str(ev(hw, "_book[1].id"))
    html = (
        '<p><b>Device Library…</b> <a href="open:tools.deviceLibrary">Open ›</a></p>'
        '<p><b>File › Exit</b> <a href="show:menu/File/Exit">Show me ›</a></p>'
        '<p><b>Exit</b> <a href="open:file.exit">Open ›</a></p>'
    )
    ev(hw, f"Book.find({json.dumps(topic)}).body = {json.dumps(html)}")
    # The stand-in bridge: show: links "need a profile"; reveal() is logged.
    ev(hw, (
        "(function(){var log=[]; var block=true;"
        "Style.helpLinks = {"
        " log: function(){ return log.slice() },"
        " setBlock: function(b){ block = b },"
        " check: function(l){ return block && l.indexOf('show:') === 0"
        "  ? 'Open a profile first.' : '' },"
        " reveal: function(l){ log.push(String(l)); return '' } };"
        " return true})()"
    ))
    ev(hw, f"showTopic({json.dumps(other)})")
    settle(100)
    ev(hw, f"showTopic({json.dumps(topic)})")
    settle(300)

    def log() -> list:
        return list(ev(hw, "Style.helpLinks.log()") or [])

    step("reasons", lambda: ev(hw, "_linkReasons"))
    step("html", lambda: str(ev(hw, "_shown.html")))
    step("disabled", lambda: str(ev(hw, "String(Style.fgDisabled)")))

    # Hover the greyed Show me ›: its reason as the tooltip.
    def hover_show() -> dict:
        hover(link_point("Show me ›"))
        wait_until(lambda: tip_shown().get("visible", False), 2000)
        return {"hovered": str(ev(body, "hoveredLink")),
                "reason": str(ev(hw, "hoverReason")), "tip": tip_shown()}
    step("hover_show", hover_show)

    # Click Open › (allowed, can show): reveal() is called; Help stays open.
    def click_open() -> dict:
        click(link_point("Open ›", 0))
        return {"log": log(), "help_open": bool(help_windows()),
                "note": str(ev(hw, "_linkNote"))}
    step("click_open", click_open)

    # Click the greyed Show me ›: no reveal, the reason under the title.
    def click_show() -> dict:
        click(link_point("Show me ›"))
        note = find_item(hw.contentItem(), "linkNote")
        return {"log": log(), "note": str(ev(hw, "_linkNote")),
                "note_visible": bool(note is not None and note.isVisible()),
                "note_text": str(note.property("text")) if note is not None else ""}
    step("click_show", click_show)

    # Click Open › for a command not on the list (Exit): refused.
    def click_refused() -> dict:
        click(link_point("Open ›", 1))
        return {"log": log(), "note": str(ev(hw, "_linkNote")),
                "alive": True}
    step("click_refused", click_refused)

    # Help activated again: links are checked again (no topic change).
    def reactivate() -> dict:
        win.requestActivate()
        wait_until(lambda: win.isActive(), 3000)
        ev(hw, "Style.helpLinks.setBlock(false)")
        before = ev(hw, "_linkReasons")
        hw.requestActivate()
        wait_until(lambda: hw.isActive(), 3000)
        settle(200)
        return {"before": before, "after": ev(hw, "_linkReasons")}
    step("reactivate", reactivate)

    # Search highlighting still works on the decorated text.
    def search() -> dict:
        ev(hw, "Style.helpLinks.setBlock(true); recheckLinks()")
        ev(hw, "_search.text = 'library'")
        settle(400)
        return {"current": str(ev(hw, "_currentId")) == topic,
                "total": ev(hw, "_shown.total"),
                "html": str(ev(hw, "_shown.html"))}
    step("search", search)


def run_resolve() -> None:
    wait_until(lambda: bool(ev(win, "Style.helpLinks !== null")), 5000)
    out["bridge"] = bool(ev(win, "Style.helpLinks !== null"))
    bodies = ev(hw, (
        "(function(){var o=[];for(var i=0;i<_book.length;++i)"
        "o.push({id:_book[i].id,body:_book[i].body});return o})()"
    )) or []
    links = []
    for topic in bodies:
        for href, text in _ANCHOR.findall(str(topic["body"])):
            href = href.replace("&amp;", "&")
            if not (href.startswith("open:") or href.startswith("show:")):
                continue
            entry = {"topic": topic["id"], "href": href,
                     "text": re.sub(r"<[^>]+>", "", text).strip(),
                     "allowed": True}
            if href.startswith("open:"):
                entry["allowed"] = bool(ev(
                    hw, f"HelpLinks.isAllowedOpen({json.dumps(href[5:])})"))
            try:
                entry["reason"] = str(ev(
                    win, f"String(Style.helpLinks.check({json.dumps(href)}) || '')"))
            except Exception as exc:  # noqa: BLE001
                entry["reason"] = "error: " + repr(exc)
            links.append(entry)
    out["links"] = links
    # Made-up targets must be refused, or the check above proves nothing.
    bogus = {}
    for href in ("show:menu/File/No Such Item", "show:toolbar/No Such Button",
                 "show:option/No Such Setting", "open:no.such.command"):
        bogus[href] = str(ev(
            win, f"String(Style.helpLinks.check({json.dumps(href)}) || '')"))
    out["bogus"] = bogus


try:
    if MODE == "resolve":
        run_resolve()
    else:
        run_dialog()
except Exception as exc:  # noqa: BLE001
    out["errors"].append(repr(exc))

out["desktop_urls"] = catcher.urls
out["qml_errors"] = [
    m for m in messages
    if any(k in m for k in ("Error", "is not a function", "is not defined"))
    and ("Help" in m or "help_links" in m)
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
