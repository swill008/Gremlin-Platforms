# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the History window at a UI scale
(test_handson_G2_history_heading.py): a change picked, then where each
side's heading ("Before", "After") and its Restore button lie. Prints
RESULT {json}.

    python test/unit/handson_G2_history_smoke.py SCALE [shot.png]
"""

from __future__ import annotations

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

SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 100
SHOT = sys.argv[2] if len(sys.argv) > 2 else ""

from gremlin.ui import ui_scale_option  # noqa: E402

ui_scale_option.active_scale = lambda: SCALE  # type: ignore[assignment]

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin import history, util  # noqa: E402
from gremlin.modules import module_file  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
out: dict = {"scale": SCALE}


def wait_until(check, what: str, timeout: float = 10.0):  # noqa: ANN001, ANN201
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            raise TimeoutError(what)
        QtTest.QTest.qWait(20)


def settle() -> None:
    wait_until(lambda: history._writer is None, "the history writer", 5)
    history.flush()


path = util.modules_dir() / "history_stick.json"
module_file.write_json(path, {"device": "History Stick", "claim": {"buttons": [1]}})
settle()
module_file.write_json(path, {"device": "History Stick", "claim": {"buttons": [1, 2]}})
settle()

expr = QtQml.QQmlExpression(
    QtQml.qmlContext(win), win, 'Helpers.createComponent("DialogHistory.qml")'
)
expr.evaluate()
assert not expr.hasError(), expr.error().toString()


def find_window():  # noqa: ANN201
    return next(
        (
            w
            for w in app.topLevelWindows()
            if isinstance(w, QtQuick.QQuickWindow)
            and w.title() == "History"
            and w.isVisible()
        ),
        None,
    )


hist = wait_until(find_window, "the History window")
# The size the hands-on check used (1100 x 720 at 150 %).
hist.resize(1100, 720)


def hv(code: str) -> object:
    e = QtQml.QQmlExpression(QtQml.qmlContext(hist), hist, code)
    value = e.evaluate()[0]
    assert not e.hasError(), e.error().toString()
    return value


def items(item: QtQuick.QQuickItem) -> list:
    found = [item]
    for c in item.childItems():
        found += items(c)
    return found


def named(name: str) -> QtQuick.QQuickItem | None:
    return next((i for i in items(hist.contentItem()) if i.objectName() == name), None)


wait_until(lambda: hv("_list.count") >= 2, "the changes")
first = hv("_model.data(_model.index(0, 0), Qt.UserRole + 1)")
hv(f'pick("{first}")')
wait_until(
    lambda: (
        named("historyRestoreBefore") is not None
        and named("historyRestoreBefore").isVisible()
    ),
    "the sides",
)
QtTest.QTest.qWait(200)

for side, button_name in (
    ("Before", "historyRestoreBefore"),
    ("After", "historyRestoreAfter"),
):
    button = named(button_name)
    row = button.parentItem()
    heading = next(
        c
        for c in row.childItems()
        if c.property("text") == side and c.inherits("QQuickText")
    )
    h_at = heading.mapToScene(QtCore.QPointF(0, 0)).x()
    b_at = button.mapToScene(QtCore.QPointF(0, 0)).x()
    out[side] = {
        # Where the heading's drawn text ends: shortened (elided) inside its
        # width, else all of it, past its width too.
        "text-end": h_at
        + (
            heading.width()
            if heading.property("truncated")
            else heading.property("contentWidth")
        ),
        "heading-end": h_at + heading.width(),
        "button-start": b_at,
        "button-end": b_at + button.width(),
        "row-end": row.mapToScene(QtCore.QPointF(row.width(), 0)).x(),
        "gap-wanted": hv("Style.dp(8)"),
        "truncated": heading.property("truncated"),
    }
if SHOT:
    hist.grabWindow().save(SHOT)
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
