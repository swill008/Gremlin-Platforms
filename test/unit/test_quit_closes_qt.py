# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""After the quit steps the program closes its windows and the QML engine
and lets the application go before the process ends (01 S154, AD5,
D-01-QUIT-CLOSE): Qt's own clean-up must never run at DLL unload on
objects still alive (the Qt6Gui.dll exit crash, AUD-THREADS-01).

The real main() runs off-screen in its own process (stand-in hardware, a
fresh user folder) and quits through the main window's File > Exit path
(quitGremlin). The child's os._exit records what was still alive.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_CHILD = r'''
import importlib.util, json, os, sys
from pathlib import Path

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6
from PySide6 import QtCore, QtGui, QtQml

import joystick_gremlin as jg

# Not the user's own copy: no second-copy question.
jg._check_second_copy = lambda: (None, True)
seen = {"quit_asked": False}
real_exit = os._exit


def _exit(code):
    app = QtCore.QCoreApplication.instance()
    engine = seen.get("engine")
    windows = []
    if app is not None:
        windows = [
            w.objectName() or type(w).__name__
            for w in QtGui.QGuiApplication.topLevelWindows()
        ]
    out = {
        "code": code,
        "quit_asked": seen["quit_asked"],
        "app_alive": app is not None,
        "engine_alive": engine is not None and shiboken6.isValid(engine),
        "windows": windows,
    }
    print("RESULT " + json.dumps(out), flush=True)
    real_exit(code)


os._exit = _exit
_process = jg.JoystickGremlinApp.process_cmd_args


def _quit_soon(self, args):
    _process(self, args)
    seen["engine"] = self.engine

    def quit_now():
        seen["quit_asked"] = True
        window = self.engine.rootObjects()[0]
        QtCore.QMetaObject.invokeMethod(
            window, "quitGremlin",
            QtCore.Q_ARG("QVariant", False), QtCore.Q_ARG("QVariant", False),
        )

    QtCore.QTimer.singleShot(500, quit_now)


jg.JoystickGremlinApp.process_cmd_args = _quit_soon
sys.argv = [str(ROOT / "joystick_gremlin.py")]
jg.main()
print("RESULT " + json.dumps({"code": "main returned"}), flush=True)
'''


def test_quit_closes_windows_engine_and_app_before_the_process_ends(
    tmp_path: pathlib.Path,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
        TEMP=str(home), TMP=str(home),
    )
    start = time.monotonic()
    result = proc_tree.run(
        [sys.executable, "-c", _CHILD, str(_ROOT)], cwd=_ROOT, env=env,
        text=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    took = time.monotonic() - start
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    out = json.loads(lines[0][len("RESULT "):])
    assert out["quit_asked"], out
    assert out["code"] == 0, out
    # S154: nothing of Qt's is left for the DLL unload.
    assert not out["engine_alive"], out
    assert out["windows"] == [], out
    assert not out["app_alive"], out
    assert result.returncode == 0, smoke_report.explain(result)
    assert took < 90, took


def test_a_stuck_release_still_ends_the_process(monkeypatch) -> None:  # noqa: ANN001
    """The tear-down is bounded: a stuck step ends the process anyway."""
    import threading

    import joystick_gremlin as jg

    ended: list[int] = []
    released = threading.Event()

    def _exit(code: int) -> None:
        ended.append(code)
        released.set()

    def _stuck() -> list:
        released.wait(10)
        return []

    monkeypatch.setattr(jg.os, "_exit", _exit)
    monkeypatch.setattr(jg.logging, "shutdown", lambda: None)
    monkeypatch.setattr(jg, "_RELEASE_LIMIT_S", 0.2)
    monkeypatch.setattr(jg.QtGui.QGuiApplication, "topLevelWindows", _stuck)

    class _App:
        engine = None

        def shutdown(self) -> None:
            pass

    start = time.monotonic()
    jg.release_qt(_App(), limit=0.2)  # type: ignore[arg-type]
    assert ended == [0]
    assert time.monotonic() - start < 5
