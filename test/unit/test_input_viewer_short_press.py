# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen: a button tap shorter than one redraw still lights its vJoy
Viewer chip (InputViewerCard) for about 100 ms (minimumVisibleMs), from
upstream 736129eb; a held press stays lit while held and goes out after
release (03 S122). The real card is loaded and its PairLiveThrottle fed a
press and release back to back, with no event loop turn between them."""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_CODE = r"""
import importlib.util, json, os, sys, time
ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location(
    "fake_hardware", os.path.join(ROOT, "test", "fake_hardware.py"))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from PySide6 import QtCore, QtGui, QtQml, QtQuick
app = QtGui.QGuiApplication([sys.argv[0]])
from gremlin.ui import backend, module_pairing, pair_live  # noqa
GUID = "{11111111-2222-3333-4444-555555555555}"
module_pairing._module_pair_rows = lambda guid, name, kind: (
    [{"identifier": 3, "label": "3", "vjoyId": 1, "vjoyInput": 3,
      "vjoyLabel": "vJoy 1 Button 3", "vjoyGuid": GUID, "destClaimed": True}]
    if "Button" in str(kind) else [])
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "Style.qml")),
    "Gremlin.Style", 1, 0, "Style")
engine = QtQml.QQmlEngine()
engine.addImportPath(os.path.join(ROOT, "theme"))
engine.rootContext().setContextProperty("backend", None)


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


url = QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "InputViewerCard.qml"))
comp = QtQml.QQmlComponent(engine, url)
root = comp.createWithInitialProperties(
    {"deviceGuid": GUID, "deviceName": "Stick", "title": "Stick", "width": 600})
if root is None:
    print("NOT CREATED " + comp.errorString(), flush=True)
    os._exit(1)
window = QtQuick.QQuickWindow()
window.resize(800, 600)
root.setParentItem(window.contentItem())
for _ in range(20):
    app.processEvents()
chip = next(i for i in walk(root) if i.objectName() == "vjoyViewerChip")
live = root.findChildren(pair_live.PairLiveThrottle)[0]


def pump(ms):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 5)
        time.sleep(0.002)


out = {"minimum": root.property("minimumVisibleMs"),
       "before": chip.property("hwShown")}
# A tap: pressed and released with no event loop turn between them.
t0 = time.monotonic()
live._hw_button[3] = 1.0
live._bump_button()
live._hw_button[3] = 0.0
live._bump_button()
out["hwOn"] = chip.property("hwOn")
out["right_after"] = chip.property("hwShown")
pump(50)
out["at_50ms"] = chip.property("hwShown")
gone = None
while time.monotonic() - t0 < 1.0:
    app.processEvents()
    if not chip.property("hwShown"):
        gone = (time.monotonic() - t0) * 1000.0
        break
    time.sleep(0.002)
out["gone_ms"] = gone
# A held press stays lit as long as it is held.
live._hw_button[3] = 1.0
live._bump_button()
pump(250)
out["held_250ms"] = chip.property("hwShown")
live._hw_button[3] = 0.0
live._bump_button()
pump(250)
out["released_250ms"] = chip.property("hwShown")
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)
"""


def test_a_short_press_stays_lit_about_100_ms(tmp_path: pathlib.Path) -> None:
    root = pathlib.Path(__file__).parents[2]
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, "-c", _CODE, str(root)],
        cwd=root,
        env=env,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    lines = [ln for ln in (done.stdout or "").splitlines() if ln.startswith("RESULT ")]
    assert lines, (done.stdout or "")[-3000:] + smoke_report.explain(done)
    import json

    out = json.loads(lines[-1][len("RESULT ") :])
    assert out["minimum"] == 100, out
    assert out["before"] is False, out
    assert out["hwOn"] is False, out  # the press itself is already over
    assert out["right_after"] is True, out
    assert out["at_50ms"] is True, out
    assert out["gone_ms"] is not None and 80 <= out["gone_ms"] <= 400, out
    assert out["held_250ms"] is True, out
    assert out["released_250ms"] is False, out
