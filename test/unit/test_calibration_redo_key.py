# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Calibration's Redo key works (no behaviour change).

The window's Redo Shortcut listed StandardKey.Redo and "Ctrl+Y"; on Windows
StandardKey.Redo is Ctrl+Y, so Ctrl+Y was there twice, the Shortcut was
ambiguous and never fired. StandardKey.Redo there is Ctrl+Y and
Ctrl+Shift+Z, so it is listed alone (adding "Ctrl+Shift+Z" would make that
key ambiguous instead).

The test runs the real program off-screen (stand-in hardware) in its own
process with a fresh user folder: this file run as a script opens
Calibration, changes an axis's low end, and presses Ctrl+Z, Ctrl+Y,
Ctrl+Z, Ctrl+Shift+Z with real Qt key events.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ctrl_y_and_ctrl_shift_z_redo_in_calibration(
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
    assert out["edited"] == -20000 and out["original"] != -20000, out
    assert out["after-ctrl-z"] == out["original"], out
    assert out["after-ctrl-y"] == -20000, out
    assert out["after-ctrl-z-2"] == out["original"], out
    assert out["after-ctrl-shift-z"] == -20000, out


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

        def low() -> int:
            return int(ev(w, "_calib.data(_calib.index(0, 0),"
                             " Qt.UserRole + 4)"))

        def key(k: QtCore.Qt.Key, mods: QtCore.Qt.KeyboardModifier) -> None:
            QtTest.QTest.keyClick(w, k, mods)
            for _ in range(10):
                QtCore.QCoreApplication.processEvents()

        ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        shift = QtCore.Qt.KeyboardModifier.ShiftModifier
        out["original"] = low()
        ev(w, "_calib.setData(_calib.index(0, 0), -20000, Qt.UserRole + 4)")
        out["edited"] = low()
        key(QtCore.Qt.Key.Key_Z, ctrl)
        out["after-ctrl-z"] = low()
        key(QtCore.Qt.Key.Key_Y, ctrl)
        out["after-ctrl-y"] = low()
        key(QtCore.Qt.Key.Key_Z, ctrl)
        out["after-ctrl-z-2"] = low()
        key(QtCore.Qt.Key.Key_Z, ctrl | shift)
        out["after-ctrl-shift-z"] = low()
    except Exception as exc:  # noqa: BLE001
        out["error"] = repr(exc)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)  # threads started by the app would keep it alive


if __name__ == "__main__":
    _smoke()
