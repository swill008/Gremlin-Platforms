# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""GL-144 (03 Q16): typing a friendly name in Keyboard Module Setup does not
tick the typed keys. The keyboard hook sees every key, so Module Setup
ignores key presses while a text box of the program has the focus.

Needs a QGuiApplication with a real (off-screen) window, which can't share a
process with the unit tests' QCoreApplication, so the check runs in a child
process (this file run as a script).
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _child() -> None:
    import types
    from unittest import mock

    from PySide6 import QtCore, QtGui, QtQuick

    app = QtGui.QGuiApplication(sys.argv)
    import gremlin.util

    gremlin.util.userprofile_path = mock.Mock(return_value=sys.argv[2])
    from gremlin.ui import module_model

    view = QtQuick.QQuickView()
    view.setSource(QtCore.QUrl.fromLocalFile(sys.argv[3]))
    view.show()
    view.requestActivate()
    deadline = QtCore.QDeadlineTimer(5000)
    while QtGui.QGuiApplication.focusObject() is None and not deadline.hasExpired():
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
    focus = QtGui.QGuiApplication.focusObject()
    print("RESULT focus", focus.metaObject().className() if focus else None)

    setup = module_model.DriverInputModel()
    setup._guid = module_model.KEYBOARD_GUID
    setup._load_keyboard({"keys": [], "keysChosen": True, "friendly": {}})
    before = setup.rowCount()
    claimed = sum(1 for r in setup._rows if r["claimed"])
    # "F" pressed while the name box has the focus.
    setup._on_key(types.SimpleNamespace(is_pressed=True, identifier=(0x21, False)))
    setup._on_key(types.SimpleNamespace(is_pressed=True, identifier=(0x7F, True)))
    print("RESULT typing", before == setup.rowCount()
          and claimed == sum(1 for r in setup._rows if r["claimed"]))

    # The text box loses the focus: a press is a press again.
    root = view.rootObject()
    root.setProperty("focus", False)
    view.contentItem().forceActiveFocus()
    app.processEvents()
    print("RESULT after", module_model._typing_in_a_text_box())
    setup._on_key(types.SimpleNamespace(is_pressed=True, identifier=(0x7F, True)))
    added = setup.rowCount() == before + 1 and setup._rows[-1]["claimed"]
    print("RESULT pressed", added)
    print("done")
    sys.stdout.flush()
    os._exit(0)


def test_keys_typed_into_a_text_box_are_not_ticked(tmp_path: pathlib.Path) -> None:
    qml = tmp_path / "box.qml"
    qml.write_text(
        "import QtQuick\nTextInput { width: 200; height: 30; focus: true }\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), "child", str(tmp_path), str(qml)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
            "PYTHONPATH": str(_ROOT),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-2000:] + result.stderr[-2000:]
    found = dict(
        line.split(" ", 2)[1:] for line in lines if line.startswith("RESULT ")
    )
    assert found["focus"] == "QQuickTextInput", found
    assert found["typing"] == "True", found
    assert found["after"] == "False", found
    assert found["pressed"] == "True", found


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "child":
    sys.path.insert(0, str(_ROOT))
    _child()
