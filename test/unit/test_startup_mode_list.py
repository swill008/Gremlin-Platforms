# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 S63, D-04-LAST-ACTIVE: Profile Settings > Startup Mode offers Last
Active and every mode by name, no Use Heuristic; a setting that isn't listed
shows as Last Active; picking a mode sets the profile's Startup Mode.

Loads the real ProfileSettings.qml in the running program off-screen
(stand-in hardware), in its own process, and drives its Startup Mode box."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = r"""
import importlib.util, json, os, sys
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
from gremlin import shared_state
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
QtTest.QTest.qWait(500)

profile = shared_state.current_profile
for name in ("Space", "Ground"):
    if name not in profile.modes.mode_names():
        profile.modes.add_mode(name)
profile.settings.startup_mode = "Use Heuristic"

out = {}
url = QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "ProfileSettings.qml"))
component = QtQml.QQmlComponent(app.engine, url)
page = component.create() if component.isReady() else None
if page is None:
    out["error"] = component.errorString()
else:
    QtTest.QTest.qWait(200)
    box = page.findChild(QtCore.QObject, "startupModeBox")
    help_text = page.findChild(QtCore.QObject, "startupModeHelp")

    def ev(code):
        return QtQml.QQmlExpression(QtQml.qmlContext(box), box, code).evaluate()[0]

    out["modes"] = profile.modes.mode_names()
    out["labels"] = json.loads(
        ev("JSON.stringify([...Array(count).keys()].map(i => textAt(i)))"))
    out["shown"] = ev("displayText")
    out["help"] = help_text.property("text")
    picks = {}
    for i, label in enumerate(out["labels"]):
        ev(f"currentIndex = {i}; activated({i})")
        picks[label] = profile.settings.startup_mode
    out["picks"] = picks
print("OUT " + json.dumps(out), flush=True)
os._exit(0)
"""


def test_startup_mode_box_lists_last_active_and_the_modes(
    tmp_path: pathlib.Path,
) -> None:
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
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("OUT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    out = json.loads(lines[-1][4:])
    assert "error" not in out, out["error"]

    # Last Active, then every mode by name; no Use Heuristic.
    assert out["labels"] == ["Last Active"] + out["modes"]
    assert "Use Heuristic" not in out["labels"]
    # A setting that isn't listed (here Use Heuristic) shows as Last Active.
    assert out["shown"] == "Last Active"
    # Picking an entry sets the profile's Startup Mode to it.
    assert out["picks"] == {label: label for label in out["labels"]}
    # The explanation describes Last Active and drops Use Heuristic.
    assert "Use Heuristic" not in out["help"]
    assert "Last Active opens the mode the profile last ran in" in out["help"]
    assert "top mode in Manage Modes" in out["help"]
