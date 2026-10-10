# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home cards resize by edge or corner (03 S83): a real drag on a card's
corner grip or east edge grip resizes the card and the page under it does
not scroll (the user's report: the drag started resizing, then the page's
Flickable took it and scrolled). The whole program runs off-screen in its
own process with a fresh user folder; no network."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = r"""
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
import shiboken6
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
w = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)

out = {}
Qt = QtCore.Qt
LEFT = Qt.MouseButton.LeftButton
NOMOD = Qt.KeyboardModifier.NoModifier

def walk(item):
    found = [item]
    for child in item.childItems():
        found.extend(walk(child))
    return found

def pause(ms):
    timer = QtCore.QElapsedTimer()
    timer.start()
    while timer.elapsed() < ms:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)

def cards():
    return [i for i in walk(w.contentItem())
            if i.objectName() == "statusCard" and i.isVisible()
            and i.width() > 0 and i.height() > 0]

def flick_of(item):
    p = item.parentItem()
    while p is not None and not p.inherits("QQuickFlickable"):
        p = p.parentItem()
    return p

def grip(card, shape):
    for it in card.childItems():
        if it.inherits("QQuickMouseArea") and it.isVisible() \
                and it.property("cursorShape") == shape:
            return it
    return None

def send(kind, pos, button, buttons):
    pos = QtCore.QPointF(pos)
    glob = QtCore.QPointF(w.mapToGlobal(pos.toPoint()))
    ev = QtGui.QMouseEvent(kind, pos, pos, glob, button, buttons, NOMOD)
    app.sendEvent(w, ev)
    app.processEvents()

def drag(start, dx, dy, steps=10):
    # A real press, held moves and a release on the window, with the button
    # carried on each move (as a hand on the mouse would).
    nobtn = Qt.MouseButton.NoButton
    send(QtCore.QEvent.Type.MouseMove, start, nobtn, nobtn)
    pause(30)
    send(QtCore.QEvent.Type.MouseButtonPress, start, LEFT, LEFT)
    pause(30)
    for i in range(1, steps + 1):
        p = QtCore.QPointF(start.x() + dx * i / steps, start.y() + dy * i / steps)
        send(QtCore.QEvent.Type.MouseMove, p, nobtn, LEFT)
        pause(25)
    end = QtCore.QPointF(start.x() + dx, start.y() + dy)
    return end

def release(end):
    send(QtCore.QEvent.Type.MouseButtonRelease, end, LEFT, Qt.MouseButton.NoButton)
    pause(300)

# A short window: the Home page scrolls.
w.resize(1000, 500)
pause(1500)
found = cards()
out["cards"] = len(found)

def try_grip(name, shape, dx, dy, at):
    found = cards()
    if not found:
        out[name] = None
        return
    # The last card on the page: the bottom of the scroll.
    card = max(found, key=lambda c: c.mapToScene(QtCore.QPointF(0, 0)).y())
    flick = flick_of(card)
    g = grip(card, shape)
    res = {"flick": flick is not None, "grip": g is not None}
    out[name] = res
    if flick is None or g is None:
        return
    content_h = float(flick.property("contentHeight"))
    res["scrollable"] = content_h > flick.height()
    # Scroll so the card's grip sits inside the view, and leave room both ways.
    top = card.mapToItem(flick.property("contentItem"), QtCore.QPointF(0, 0)).y()
    want = max(0.0, top + card.height() - flick.height() + 40)
    want = min(want, max(0.0, content_h - flick.height()))
    flick.setProperty("contentY", want)
    pause(200)
    res["w0"], res["h0"] = card.width(), card.height()
    res["y0"] = float(flick.property("contentY"))
    start = g.mapToScene(at(g))
    res["start"] = [start.x(), start.y()]
    end = drag(start, dx, dy)
    res["w-held"], res["h-held"] = card.width(), card.height()
    res["y-held"] = float(flick.property("contentY"))
    res["moving"] = bool(flick.property("moving") or flick.property("dragging"))
    slug = card.property("slug")
    res["slug"] = slug
    release(end)
    # Cards are rebuilt from the saved size (and may reflow); read the same
    # card again by its slug.
    card2 = next((c for c in cards() if c.property("slug") == slug), None)
    res["w1"] = card2.width() if card2 is not None else None
    res["h1"] = card2.height() if card2 is not None else None
    res["y1"] = float(flick.property("contentY"))

try_grip("corner", Qt.CursorShape.SizeFDiagCursor, 80, 80,
         lambda g: QtCore.QPointF(g.width() / 2, g.height() / 2))
try_grip("east", Qt.CursorShape.SizeHorCursor, 80, 30,
         lambda g: QtCore.QPointF(g.width() / 2, g.height() / 2))

print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "card_resize.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    done = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-3000:]
    return json.loads(lines[-1][len("RESULT "):])


def _setup_ok(res: dict | None) -> None:
    assert res is not None, "no Home card"
    assert res["flick"] and res["grip"], res
    assert res["scrollable"], res


def test_corner_drag_resizes_and_page_does_not_scroll(result: dict) -> None:
    res = result["corner"]
    _setup_ok(res)
    assert res["y-held"] == res["y0"], "scrolled mid-drag: " + json.dumps(res)
    assert res["y1"] == res["y0"], "page scrolled: " + json.dumps(res)
    assert res["w-held"] >= res["w0"] + 40, "card did not grow: " + json.dumps(res)
    assert res["h-held"] >= res["h0"] + 40, "card did not grow: " + json.dumps(res)
    assert res["w1"] is not None, "card gone: " + json.dumps(res)
    assert res["w1"] >= res["w0"] + 40 and res["h1"] >= res["h0"] + 40, json.dumps(res)


def test_east_edge_drag_resizes_and_page_does_not_scroll(result: dict) -> None:
    res = result["east"]
    _setup_ok(res)
    assert res["y-held"] == res["y0"], "scrolled mid-drag: " + json.dumps(res)
    assert res["y1"] == res["y0"], "page scrolled: " + json.dumps(res)
    assert res["w-held"] >= res["w0"] + 40, "card did not grow: " + json.dumps(res)
    assert res["w1"] is not None, "card gone: " + json.dumps(res)
    assert res["w1"] >= res["w0"] + 40, json.dumps(res)
