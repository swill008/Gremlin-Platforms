# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the History window's outside-folder question
(test_history_ask_dialog.py, 08 S45a, AD6).

A whole-profile change whose profile was in a folder outside the profiles
folder (and isn't there any more) is put in the history. History opens,
the change is picked and Restore Before is clicked through its first
question; the second question (Write Here) is read, then Cancel is
clicked (nothing written), then the same again with Write Here clicked
(the copy is written). Every button is clicked with the mouse. Prints
RESULT {json}.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import uuid
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

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

import joystick_gremlin  # noqa: E402
from gremlin import history, history_profile  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
out: dict = {}

outside = Path(os.environ["USERPROFILE"]) / "outside"
outside.mkdir()
entry_id = uuid.uuid4().hex
entry = {
    "id": entry_id,
    "at": time.time() - 60,  # recent: older entries are pruned
    "area": "profile",
    "kind": "profile",
    "title": "Saved victim.xml",
    "subject": {"profile": str(outside / "victim.xml"), "profileName": "victim.xml"},
    "before": {"packed": history_profile.pack_text("<profile/>")},
    "after": {"packed": history_profile.pack_text("<profile/>")},
}
history.folder().mkdir(parents=True, exist_ok=True)
with open(history.folder() / "profile.jsonl", "a", encoding="utf-8", newline="") as f:
    f.write(json.dumps(entry) + "\n")


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
QtTest.QTest.qWait(200)


def hv(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(hist), hist, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


def gate_button(text: str) -> QtQuick.QQuickItem | None:
    """The shared question's visible button with this text."""
    pending = [hv("_gate.contentItem")]
    while pending:
        current = pending.pop()
        if (
            "Button" in current.metaObject().className()
            and current.property("text") == text
            and current.isVisible()
        ):
            return current
        pending.extend(current.childItems())
    return None


frames = [0]
hist.frameSwapped.connect(lambda: frames.__setitem__(0, frames[0] + 1))


def wait_shown(text: str, what: str) -> None:
    """Waits for the question with this button, laid out and drawn."""
    start = frames[0]
    wait_until(
        lambda: gate_button(text) and frames[0] > start + 1, what, fail=False
    )


def click(text: str) -> bool:
    button = gate_button(text)
    if button is None:
        return False
    centre = button.mapToScene(
        QtCore.QPointF(button.width() / 2, button.height() / 2)
    ).toPoint()
    QtTest.QTest.mouseClick(hist, QtCore.Qt.MouseButton.LeftButton, pos=centre)
    return True


def gate() -> dict:
    write_here = gate_button("Write Here")
    return {
        "visible": bool(hv("_gate.visible")),
        "title": hv("_gate.titleText"),
        "message": hv("_gate.messageText"),
        "confirm": hv("_gate.confirmText"),
        "destructive": bool(hv("_gate.destructive")),
        "button-highlighted": (
            write_here.property("highlighted") if write_here is not None else None
        ),
        "border-is-danger": bool(hv("_gate.background.border.color === Style.danger")),
    }


def written() -> list[str]:
    return sorted(p.name for p in outside.iterdir())


out["outside"] = str(outside)
out["in-list"] = any(
    hv(f"_model.data(_model.index({row}, 0), Qt.UserRole + 1)") == entry_id
    for row in range(int(hv("_list.count")))
)
hv(f'pick("{entry_id}")')
QtTest.QTest.qWait(200)

# Decline: Restore, then Cancel on the outside-folder question.
hv('restore("before")')
wait_shown("Restore", "the Restore? question")
out["first-confirm"] = hv("_gate.confirmText")
out["first-clicked"] = click("Restore")
wait_shown("Write Here", "the outside-folder question")
out["ask"] = gate()
out["written-while-asking"] = written()
out["cancel-clicked"] = click("Cancel")
wait_until(lambda: not hv("_gate.visible"), "the question closed", fail=False)
out["gate-after-cancel"] = bool(hv("_gate.visible"))
out["written-after-cancel"] = written()
out["message-after-cancel"] = hv("message")

# Accept: the same again, Write Here.
hv('restore("before")')
wait_shown("Restore", "the Restore? question")
click("Restore")
wait_shown("Write Here", "the outside-folder question")
out["ask-again"] = gate()
out["write-clicked"] = click("Write Here")
wait_until(lambda: hv("message"), "the restored message", fail=False)
out["gate-after-write"] = bool(hv("_gate.visible"))
out["written-after-write"] = written()
out["message-after-write"] = hv("message")
print("RESULT " + json.dumps(out), flush=True)
smoke_exit(0)  # threads started by the app would keep it alive
