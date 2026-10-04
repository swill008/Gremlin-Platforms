# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The vJoy selector (output picker in the configuration editor) loads
without QML errors: it set a scroll bar switch the shared dropdown no
longer has, and printed an error for every picker shown. Loaded in the
running program off-screen (stand-in hardware), its own process."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = r"""
import importlib.util, os, sys
ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location(
    "fake_hardware", os.path.join(ROOT, "test", "fake_hardware.py"))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtQml, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
QtTest.QTest.qWait(500)
warnings = []
app.engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
for compact in (False, True):
    component = QtQml.QQmlComponent(
        app.engine, QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "VJoySelector.qml")))
    obj = component.createWithInitialProperties({"useCompact": compact}) if component.isReady() else None
    if obj is None:
        warnings.append("not created: " + component.errorString())
    QtTest.QTest.qWait(300)
for w in warnings:
    print("WARN " + w, flush=True)
print("DONE", flush=True)
os._exit(0)
"""


def test_the_vjoy_selector_loads_without_errors(tmp_path: pathlib.Path) -> None:
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    done = subprocess.run(
        [sys.executable, "-c", _CODE, str(_ROOT)],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    assert "DONE" in done.stdout, done.stdout[-1500:] + done.stderr[-1500:]
    problems = [ln for ln in done.stdout.splitlines()
                if ln.startswith("WARN") and "VJoySelector" in ln]
    assert problems == []
