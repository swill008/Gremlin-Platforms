# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Loads an Xbox360Face.qml off-screen and prints its picture state as JSON,
for test_b1_xbox.py. Args: the face's file, then "keep" or "empty" (empty
clears the picture's source after loading)."""

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

from PySide6 import QtCore, QtGui, QtQml, QtQuick  # noqa: E402

import gremlin.ui.hardware_profile  # noqa: E402, F401  (Gremlin.Device, for an older face)

face_file, mode = Path(sys.argv[1]), sys.argv[2]
app = QtGui.QGuiApplication([sys.argv[0]])
engine = QtQml.QQmlEngine()
engine.addImportPath(str(ROOT / "theme"))
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
    "Gremlin.Style", 1, 0, "Style",
)
component = QtQml.QQmlComponent(engine, QtCore.QUrl.fromLocalFile(str(face_file)))
face = component.create()
if face is None:
    print(json.dumps({"errors": [e.toString() for e in component.errors()]}))
    smoke_exit(1)

context = QtQml.QQmlEngine.contextForObject(face)


def ev(code: str) -> object:
    value, _ = QtQml.QQmlExpression(context, face, code).evaluate()
    return value


if mode == "empty":
    ev('_img.source = ""')


def settle() -> None:
    end = time.monotonic() + 5.0
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if ev("_img.status !== Image.Loading"):
            return


settle()
texts = [
    t.property("text")
    for t in face.findChildren(QtQuick.QQuickItem)
    if t.metaObject().className().startswith("QQuickText")
]
print(json.dumps({
    "source": ev("_img.source.toString()"),
    "status": int(ev("_img.status")),
    "texts": texts,
}), flush=True)
smoke_exit(0)
