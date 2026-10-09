# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Calibration on the shared pieces (01 S142, S143): Save All says what it
did on the message line, and the Undo / Redo pair names the last change.

Runs the real program off-screen (stand-in hardware) in its own process
with a fresh user folder; clicks are real Qt mouse events.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_calibration_uses_the_message_line_and_undo_bar(
    tmp_path: pathlib.Path,
) -> None:
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve())],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    out = json.loads(lines[-1][len("RESULT "):])
    assert "error" not in out, out
    # The axis whose Calibrate Extrema was clicked, by its name.
    last = out["last-change"]
    assert last.startswith("Last change: "), out
    assert last.endswith(", Calibrate Extrema"), out
    axis = last[len("Last change: "):-len(", Calibrate Extrema")]
    assert axis.endswith("Axis"), out
    assert out["undone"] == f"Undone: a change to {axis}", out
    assert out["message-shown"] is True, out
    assert out["message"] == "Saved every axis to the module file.", out
    assert out["message-failed"] is False, out
    # No "Saved" box to click away any more.
    assert out["gate-open"] is False, out


def _smoke() -> None:  # noqa: C901
    import importlib.util

    sys.path.insert(0, str(_ROOT))
    spec = importlib.util.spec_from_file_location(
        "fake_hardware", _ROOT / "test" / "fake_hardware.py"
    )
    assert spec is not None and spec.loader is not None
    fake_hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_hardware)
    fake = fake_hardware.install()

    import gremlin.ui.update_model as um

    um.UpdateModel.startup = lambda self, *a, **k: None

    import shiboken6
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest

    import dill
    import joystick_gremlin
    from gremlin import clock, event_handler
    from gremlin.ui import hardware_profile

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

    def ev(obj: QtCore.QObject, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(expr.error().toString() + " :: " + code[:200])
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def top_window(title: str):  # noqa: ANN202
        for w in QtGui.QGuiApplication.topLevelWindows():
            if w.isVisible() and w.title() == title:
                return shiboken6.wrapInstance(
                    shiboken6.getCppPointer(w)[0], QtQuick.QQuickWindow
                )
        return None

    out: dict = {}
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    win.setProperty("visible", True)
    wait_until(lambda: win.isVisible())
    try:
        dev = fake.devices[0]
        guid = str(dill.GUID(dev.device_guid).uuid)
        path = hardware_profile.module_json_path("pJoy Pro", guid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "kind": "control.hardware", "device": "pJoy Pro",
            "direction": "source", "boundGuidLocal": guid,
            "claim": {"buttons": [1], "axes": [1, 2], "hats": [], "keys": []},
        }), encoding="utf-8")
        event_handler.EventListener()._run_device_list_update()
        ev(win, "Helpers.createComponent('DialogCalibration.qml',"
                " {initialSlug: 'pjoy_pro'})")
        if not wait_until(lambda: top_window("Calibration") is not None):
            raise RuntimeError("Calibration did not open")
        w = top_window("Calibration")
        if not wait_until(lambda: int(ev(w, "_axisView.count")) > 0):
            raise RuntimeError("no axes shown")
        w.requestActivate()
        if not wait_until(lambda: QtGui.QGuiApplication.focusWindow() is w
                          or w.isActive()):
            raise RuntimeError("Calibration window not active")

        def items() -> list:
            root = w.contentItem().parentItem() or w.contentItem()
            found, pending = [], [root]
            while pending:
                cur = pending.pop()
                found.append(cur)
                pending.extend(cur.childItems())
            return found

        def find(pred):  # noqa: ANN001, ANN202
            return next((i for i in items() if pred(i)), None)

        def click(target) -> None:  # noqa: ANN001
            centre = target.mapToScene(QtCore.QPointF(
                target.width() / 2, target.height() / 2)).toPoint()
            QtTest.QTest.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=centre)
            for _ in range(10):
                QtCore.QCoreApplication.processEvents()

        out["axis"] = str(ev(w, "_calib.data(_calib.index(0, 0), Qt.UserRole + 1)"))
        extrema = find(lambda i: i.property("text") == "Calibrate Extrema"
                       and i.property("visible"))
        click(extrema)
        bar = find(lambda i: i.objectName() == "undoBarText")
        out["last-change"] = bar.property("text") if bar else ""
        click(extrema)  # its capture off again
        click(find(lambda i: i.objectName() == "undoBarUndo"))
        out["undone"] = bar.property("text") if bar else ""
        ev(w, "_calib.setData(_calib.index(0, 0), -20000, Qt.UserRole + 4)")
        wait_until(lambda: bool(ev(w, "anyUnsaved")))
        click(find(lambda i: i.property("text") == "Save All"))
        line = find(lambda i: i.objectName() == "calibrationMessage")
        out["message-shown"] = bool(line and line.property("visible"))
        out["message"] = line.property("text") if line else ""
        out["message-failed"] = bool(line.property("failed")) if line else None
        out["gate-open"] = bool(ev(w, "_saveGate.visible"))
    except Exception as exc:  # noqa: BLE001
        out["error"] = repr(exc)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)  # threads started by the app would keep it alive


if __name__ == "__main__":
    _smoke()
