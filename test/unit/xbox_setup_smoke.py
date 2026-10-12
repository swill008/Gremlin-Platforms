# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Opens qml/DialogXboxSetup.qml off-screen with the real XboxSetupModel and
a stand-in pad count in gremlin.modules.output, presses its buttons and
prints what happened as JSON, for test_xbox_setup.py. Arg: the scenario
("raise", "lower", "cancel")."""

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
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

from PySide6 import QtCore, QtGui, QtQml  # noqa: E402

import gremlin.ui.vjoy_status  # noqa: E402, F401  (Gremlin.Device)
import gremlin.ui.window_placement  # noqa: E402, F401  (Gremlin.UI)
from gremlin.modules import output  # noqa: E402
from gremlin.signal import signal  # noqa: E402

scenario = sys.argv[1]
state = {"count": 3 if scenario == "lower" else 1}
applied: list[int] = []
asked: list[list[int]] = []
BOUND = "VKBsim Gladiator EVO R · Button 1 → Xbox 360 3 · A (Default)"


def _set(n: int, who: str = "Xbox Setup") -> None:
    applied.append(int(n))
    state["count"] = int(n)
    signal.xboxPadsChanged.emit()


def _on(pads: list[int]) -> list[str]:
    asked.append(list(pads))
    return [BOUND] if 3 in pads else []


# ViGEm is never touched: the driver reads as missing.
output.xbox_driver_installed = lambda: False
output.xbox_driver_version = lambda: ""
output.xbox_driver_problem = lambda: ("ViGEmBus driver not found.", "")
output.xbox_pad_count = lambda: state["count"]
output.set_xbox_pad_count = _set
output.xbox_bindings_on_pads = _on

app = QtGui.QGuiApplication([sys.argv[0]])
engine = QtQml.QQmlEngine()
engine.addImportPath(str(ROOT / "theme"))
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
    "Gremlin.Style", 1, 0, "Style",
)
url = QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogXboxSetup.qml"))
component = QtQml.QQmlComponent(engine, url)
win = component.create()
if win is None:
    print(json.dumps({"errors": [e.toString() for e in component.errors()]}))
    smoke_exit(1)
win.show()
context = QtQml.QQmlEngine.contextForObject(win)


def ev(code: str) -> object:
    value, _ = QtQml.QQmlExpression(context, win, code).evaluate()
    return value


def settle(ms: int = 200) -> None:
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


def child(name: str) -> QtCore.QObject | None:
    return win.findChild(QtCore.QObject, name)


def click(name: str) -> None:
    button = child(name)
    assert button is not None, name
    QtCore.QMetaObject.invokeMethod(button, "clicked")


settle()
out: dict[str, object] = {
    "title": win.property("title"),
    "visible": bool(win.property("visible")),
    "start": int(ev("_count.value")),
    "driverRow": child("xboxDriverRow") is not None,
    "ok": child("xboxSetupOk").property("text"),
    "cancel": child("xboxSetupCancel").property("text"),
}

if scenario == "raise":
    ev("_count.value = 3")
    click("xboxSetupOk")
    settle()
    out["question"] = bool(ev("_question !== null"))
elif scenario == "cancel":
    ev("_count.value = 4")
    click("xboxSetupCancel")
    settle()
else:
    ev("_count.value = 1")
    click("xboxSetupOk")
    settle()
    dialog = child("confirmDialog")
    out["question"] = dialog is not None
    out["questionTitle"] = child("confirmTitle").property("text") if dialog else ""
    out["questionText"] = child("confirmText").property("text") if dialog else ""
    out["yes"] = child("confirmAction").property("text") if dialog else ""
    out["appliedBeforeYes"] = list(applied)
    # No goes back: nothing applied, the window stays open.
    click("confirmCancel")
    settle()
    out["afterNo"] = {
        "applied": list(applied),
        "visible": bool(win.property("visible")),
        "question": bool(ev("_question !== null")),
    }
    click("xboxSetupOk")
    settle()
    # The answered question is deleted later: press the open one's Yes.
    question = ev("_question")
    assert isinstance(question, QtCore.QObject)
    yes = question.findChild(QtCore.QObject, "confirmAction")
    assert yes is not None
    QtCore.QMetaObject.invokeMethod(yes, "clicked")
    settle()

out["applied"] = applied
out["asked"] = asked
out["count"] = int(ev("_setup.padCount"))
out["closed"] = not bool(win.property("visible"))
print(json.dumps(out), flush=True)
smoke_exit(0)
