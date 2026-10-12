# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Calibration's "Raw" box is read-only and follows the stick (03 gap 25).

The box accepted typing but saved nothing (to-do 49). The test runs the real
program off-screen (stand-in hardware) in its own process with a fresh user
folder: this file run as a script opens Calibration, types into the first
axis's Raw box with real Qt key events, then sends a stick movement through
the event listener and reads the box again.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_raw_box_ignores_typing_and_shows_live_value(
    tmp_path: pathlib.Path,
) -> None:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__).resolve())],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    out = json.loads(lines[-1][len("RESULT ") :])
    assert "error" not in out, out
    assert out["read-only"] is True, out
    assert out["focused"] is True, out
    assert out["after-typing"] == out["before"], out
    assert out["raw-after-typing"] == out["raw-before"], out
    assert out["after-move"] == "1234", out


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
    from gremlin.modules import store
    from gremlin.types import InputType

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
        guid = dill.GUID(dev.device_guid).uuid
        folder = store.ensure_device_dir("pJoy Pro", str(guid))
        path = store.module_file_in(folder)
        path.write_text(
            json.dumps(
                {
                    "kind": "control.hardware",
                    "device": "pJoy Pro",
                    "direction": "source",
                    "boundGuidLocal": str(guid),
                    "claim": {"buttons": [1], "axes": [1, 2], "hats": [], "keys": []},
                }
            ),
            encoding="utf-8",
        )
        event_handler.EventListener()._run_device_list_update()
        ev(
            win,
            "Helpers.createComponent('DialogCalibration.qml',"
            " {initialSlug: " + json.dumps(folder.name) + "})",
        )
        if not wait_until(lambda: top_window("Calibration") is not None):
            raise RuntimeError("Calibration did not open")
        w = top_window("Calibration")
        if not wait_until(lambda: int(ev(w, "_axisView.count")) > 0):
            raise RuntimeError("no axes shown")
        w.requestActivate()
        wait_until(lambda: QtGui.QGuiApplication.focusWindow() is w or w.isActive())

        def find_item(item, name: str):  # noqa: ANN001, ANN202
            # Delegates have a visual parent only, so walk childItems.
            if item.objectName() == name:
                return item
            for child in item.childItems():
                hit = find_item(child, name)
                if hit is not None:
                    return hit
            return None

        box = find_item(w.contentItem(), "calibrationRaw0")
        if box is None:
            raise RuntimeError("Raw box not found")

        def raw_role() -> int:
            return int(ev(w, "_calib.data(_calib.index(0, 0), Qt.UserRole + 3)"))

        out["read-only"] = bool(box.property("readOnly"))
        out["before"] = box.property("text")
        out["raw-before"] = raw_role()
        box.forceActiveFocus()
        wait_until(lambda: box.hasActiveFocus(), 2000)
        out["focused"] = bool(box.hasActiveFocus())
        for k in (QtCore.Qt.Key.Key_9, QtCore.Qt.Key.Key_8, QtCore.Qt.Key.Key_7):
            QtTest.QTest.keyClick(w, k)
        QtTest.QTest.keyClick(w, QtCore.Qt.Key.Key_Backspace)
        for _ in range(10):
            QtCore.QCoreApplication.processEvents()
        out["after-typing"] = box.property("text")
        out["raw-after-typing"] = raw_role()

        # A stick movement still shows: axis 1 is the first row.
        first_axis = 1
        event_handler.EventListener().joystick_event.emit(
            event_handler.Event(
                InputType.JoystickAxis,
                first_axis,
                guid,
                "Default",
                value=0.0,
                raw_value=1234,
            )
        )
        wait_until(lambda: box.property("text") == "1234", 3000)
        out["after-move"] = box.property("text")
    except Exception as exc:  # noqa: BLE001
        out["error"] = repr(exc)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)  # threads started by the app would keep it alive


if __name__ == "__main__":
    _smoke()
