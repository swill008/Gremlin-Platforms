# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the History window at a UI scale
(test_handson_G2_history_heading.py): a change picked, then where the
restore controls lie (the main button and the two links), and, with "Show
full before/after" on, where each side's heading ("Before", "After") lies.
Prints RESULT {json}.

    python test/unit/handson_G2_history_smoke.py SCALE [shot.png]
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

from smoke_exit import smoke_exit

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
from gremlin import history  # noqa: E402
from gremlin.modules import module_file, store  # noqa: E402

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


path = store.module_file_in(store.ensure_device_dir("History Stick"))
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
    "the restore controls",
)
QtTest.QTest.qWait(200)

# The restore controls row (D-TESTLIST-1 item 13): the main button, the
# "Restore to after" link and the "Show full before/after" link, left to
# right, each clear of the next and inside the row.
controls = [
    named(n)
    for n in ("historyRestoreBefore", "historyRestoreAfter", "historyShowFull")
]
row = controls[0].parentItem()
out["controls"] = []
for control in controls:
    at = control.mapToScene(QtCore.QPointF(0, 0)).x()
    # A Label's drawn text can run past its box; a Button draws inside it.
    drawn = control.property("contentWidth") if control.inherits("QQuickText") else None
    out["controls"].append(
        {
            "name": control.objectName(),
            "start": at,
            "end": at + control.width(),
            "text-end": at + (drawn if drawn is not None else control.width()),
        }
    )
out["row-start"] = row.mapToScene(QtCore.QPointF(0, 0)).x()
out["row-end"] = row.mapToScene(QtCore.QPointF(row.width(), 0)).x()
out["gap-wanted"] = hv("Style.dp(8)")

# The Before / After headings, shown with "Show full before/after": each
# drawn inside its own side (shortened when there is no room).
hv("showFull = true")
QtTest.QTest.qWait(300)
for side in ("Before", "After"):
    heading = next(
        i
        for i in items(hist.contentItem())
        if i.inherits("QQuickText") and i.property("text") == side and i.isVisible()
    )
    column = heading.parentItem()
    h_at = heading.mapToScene(QtCore.QPointF(0, 0)).x()
    out[side] = {
        "text-end": h_at
        + (
            heading.width()
            if heading.property("truncated")
            else heading.property("contentWidth")
        ),
        "side-start": column.mapToScene(QtCore.QPointF(0, 0)).x(),
        "side-end": column.mapToScene(QtCore.QPointF(column.width(), 0)).x(),
        "heading-start": h_at,
    }
if SHOT:
    hist.grabWindow().save(SHOT)
print("RESULT " + json.dumps(out), flush=True)
smoke_exit(0)  # threads started by the app would keep it alive
