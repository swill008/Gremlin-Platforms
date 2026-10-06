# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the History window (test_history_window.py).

Two saves of a module file are made, then History opens filtered to that
device as Module Setup opens it: the list, a change before and after,
Restore Before through its confirm step, Show All, and the same change
picked again (read again). Prints RESULT
{json}.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import time
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

from PySide6 import QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin import history, util  # noqa: E402
from gremlin.modules import module_file  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
shot = sys.argv[1] if len(sys.argv) > 1 else ""
out: dict = {}


def settle() -> None:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        QtTest.QTest.qWait(20)
    history.flush()


path = util.modules_dir() / "history_stick.json"
module_file.write_json(path, {"device": "History Stick", "claim": {"buttons": [1]}})
settle()
module_file.write_json(path, {"device": "History Stick", "claim": {"buttons": [1, 2]}})
settle()


def ev(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


ev(
    'Helpers.createComponent("DialogHistory.qml", '
    '{ filter: JSON.stringify({ device: "History Stick" }) })'
)
QtTest.QTest.qWait(500)
hist = next(
    w
    for w in app.topLevelWindows()
    if isinstance(w, QtQuick.QQuickWindow) and w.title() == "History" and w.isVisible()
)
hist.resize(1100, 700)
QtTest.QTest.qWait(200)


def hv(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(hist), hist, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


def item(name: str) -> QtQuick.QQuickItem | None:
    """By name: Repeater rows aren't object children, so walk the items."""
    pending = [hist.contentItem()]
    while pending:
        current = pending.pop()
        if current.objectName() == name:
            return current
        pending.extend(current.childItems())
    return hist.findChild(QtQuick.QQuickItem, name)


out["count"] = hv("_list.count")
out["about"] = item("historyAbout").property("text")
first = hv("_model.data(_model.index(0, 0), Qt.UserRole + 1)")
out["first-title"] = hv("_model.data(_model.index(0, 0), Qt.UserRole + 4)")
hv(f'pick("{first}")')
QtTest.QTest.qWait(200)
out["before"] = item("history:before").property("text")
out["after"] = item("history:after").property("text")
out["restore-enabled"] = item("historyRestoreBefore").property("enabled")
if shot:
    hist.grabWindow().save(shot)
# Restore Before, then its confirm step.
hv('restore("before")')
hv("_gate.confirmed()")
QtTest.QTest.qWait(300)
settle()
out["message"] = item("historyMessage").property("text")
out["file-after-restore"] = json.loads(path.read_text(encoding="utf-8"))["claim"]
hv("_model.reload()")
out["count-after-restore"] = hv("_list.count")
hv("showAll()")
QtTest.QTest.qWait(200)
out["about-after-show-all"] = item("historyAbout").property("text")
# The same change picked again is read again: its entry, changed since it
# was first shown, shows as it is now (the title here).
hv(f'pick("{first}")')
QtTest.QTest.qWait(100)
real_entries = history.entries


def edited_entries() -> list[dict]:
    entries = copy.deepcopy(real_entries())
    for entry in entries:
        if entry.get("id") == first:
            entry["title"] = "Changed since it was shown"
    return entries


history.entries = edited_entries
hv("_model.reload()")
hv(f'pick("{first}")')
QtTest.QTest.qWait(100)
out["repicked-title"] = hv("shown.title")
history.entries = real_entries
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
