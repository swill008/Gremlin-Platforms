# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the History window's stable list
(test_history_window_stable.py, D-TESTLIST-1 13).

One module file is saved three times (one folded run), then 25 other
devices once each. History opens, scrolled to the bottom with the folded
run's head selected. A restore, a change saved meanwhile and Show are each
checked for: rows, scroll and selection kept. Prints RESULT {json}.
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
sys.path.insert(0, str(ROOT / "test"))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtQml, QtQuick, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

import joystick_gremlin  # noqa: E402
from gremlin import history  # noqa: E402
from gremlin.modules import module_file, store  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
out: dict = {}


def settle() -> None:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        QtTest.QTest.qWait(20)
    history.flush()
    QtTest.QTest.qWait(50)


def save(device: str, buttons: list[int]) -> Path:
    path = store.module_file_in(store.ensure_device_dir(device))
    module_file.write_json(path, {"device": device, "claim": {"buttons": buttons}})
    settle()
    return path


for i in range(25):
    save(f"Other Stick {i:02d}", [1])
fold = None
for n in (1, 2, 3):
    fold = save("Fold Stick", list(range(1, n + 1)))


def ev(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


ev('Helpers.createComponent("DialogHistory.qml", {})')
hist = wait_until(
    lambda: next((
    w
    for w in app.topLevelWindows()
    if isinstance(w, QtQuick.QQuickWindow) and w.title() == "History" and w.isVisible()
    ), None),
    "the History window",
)
hist.resize(1100, 700)
QtTest.QTest.qWait(300)


def hv(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(hist), hist, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


def row_of(entry_id: str) -> int:
    """The row an entry shows on now (-1: not shown), from the page's model."""
    model = hv("_model")
    rows = getattr(model, "_rows", [])
    return next((r for r, e in enumerate(rows) if e.get("id") == entry_id), -1)


def item(name: str) -> QtQuick.QQuickItem | None:
    pending = [hist.contentItem()]
    while pending:
        current = pending.pop()
        if current.objectName() == name:
            return current
        pending.extend(current.childItems())
    return None


def prop(name: str, what: str) -> object:
    found = item(name)
    return found.property(what) if found is not None else None


def place() -> dict:
    return {
        "count": hv("_list.count"),
        "contentY": round(float(hv("_list.contentY")), 1),
        "selected": hv("selected"),
    }


out["count"] = hv("_list.count")
out["today-heading"] = item("historyDay:Today") is not None
# The newest row is Fold Stick's run; it is picked, then the list is
# scrolled down past it.
head = hv("_model.data(_model.index(0, 0), Qt.UserRole + 1)")
out["head-title"] = hv("_model.data(_model.index(0, 0), Qt.UserRole + 4)")
out["head-size"] = hv("_model.data(_model.index(0, 0), Qt.UserRole + 9)")
out["toggle-visible"] = prop(f"historyGroupToggle:{head}", "visible")
hv(f'pick("{head}")')
QtTest.QTest.qWait(200)
out["effect"] = prop("historyEffect", "text")
out["restore-text"] = prop("historyRestoreBefore", "text")
out["restore-enabled"] = prop("historyRestoreBefore", "enabled")
out["after-link"] = prop("historyRestoreAfter", "text")
out["full-shown-at-first"] = hv("_sides.visible")
hv("showFull = true")
QtTest.QTest.qWait(100)
out["full-shown-after-link"] = hv("_sides.visible")
hv("showFull = false")
hv("_list.positionViewAtIndex(12, ListView.Beginning)")
QtTest.QTest.qWait(200)
out["place-before"] = place()

# A restore: the entry is tagged in place, no new row, nothing moves.
hv('restore("before")')
hv("_gate.confirmed()")
QtTest.QTest.qWait(300)
settle()
QtTest.QTest.qWait(300)
out["file-after-restore"] = json.loads(fold.read_text(encoding="utf-8"))["claim"]
out["place-after-restore"] = place()
out["tag"] = hv(
    f'_model.data(_model.index({row_of(head)}, 0), Qt.UserRole + 12)'
)
out["new-after-restore"] = hv("_model.newCount")
out["message"] = prop("historyMessage", "text")

# A change saved meanwhile waits behind the bar.
save("Late Stick", [1])
QtTest.QTest.qWait(500)
hv("_model.refresh()")  # as the window does when it comes back to the front
QtTest.QTest.qWait(100)
out["place-after-new"] = place()
out["new-count"] = hv("_model.newCount")
out["bar-visible"] = prop("historyNewBar", "visible")
out["bar-text"] = prop("historyNewText", "text")

# Show adds it; the selection stays on its entry.
hv("showNew()")
QtTest.QTest.qWait(200)
out["place-after-show"] = place()
out["bar-after-show"] = prop("historyNewBar", "visible")

# The folded run opens under its head.
hv(f'_model.toggleGroup("{head}")')
QtTest.QTest.qWait(200)
out["count-open"] = hv("_list.count")
print("RESULT " + json.dumps(out), flush=True)
smoke_exit(0)  # threads started by the app would keep it alive
