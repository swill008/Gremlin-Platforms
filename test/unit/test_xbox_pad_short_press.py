# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen: on the Xbox Output View's pad card (XboxPadCard), a button tap
shorter than one redraw still lights its chip (input half and pad half) and
the face's D-pad for about 100 ms (minimumVisibleMs, HeldLight.qml), as the
vJoy Viewer chips do (upstream 736129eb); a held press stays lit while held
and goes out after release (gap UP-XBOX-PAD-HOLD, page 02). The real card is
loaded and its XboxPadLive fed a press and release back to back, with no
event loop turn between them."""

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
from gremlin.ui import backend, xbox_output_list, xbox_viewer  # noqa
GUID = "{11111111-2222-3333-4444-555555555555}"
STATE = {}
xbox_viewer.output.xbox_state = lambda pad: dict(STATE)
xbox_viewer.pad_chips = lambda pad: [{
    "guid": GUID, "name": "Stick", "axes": [],
    "buttons": [{"identifier": 1, "label": "1", "kind": "button",
                 "xboxTarget": "a", "xboxLabel": "A", "xboxChip": "A"}]}]
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


url = QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "XboxPadCard.qml"))
comp = QtQml.QQmlComponent(engine, url)
root = comp.createWithInitialProperties(
    {"padId": 1, "title": "Xbox 360 1", "drivenBy": "Stick", "boundCount": 1,
     "running": True, "width": 900})
if root is None:
    print("NOT CREATED " + comp.errorString(), flush=True)
    os._exit(1)
window = QtQuick.QQuickWindow()
window.resize(1000, 800)
root.setParentItem(window.contentItem())
for _ in range(20):
    app.processEvents()
chip = next(i for i in walk(root) if i.objectName() == "xboxChip")
dpad = next(i for i in walk(root) if i.objectName() == "xboxFaceDpadUp")
live = root.findChildren(xbox_viewer.XboxPadLive)[0]
KEY = (xbox_viewer.guid_key(GUID), 1)


def pump(ms):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 5)
        time.sleep(0.002)


def shown():
    return {"hw": chip.property("hwShown"), "xb": chip.property("xbShown"),
            "dpad": dpad.property("lit")}


def press(on):
    live._hw_button[KEY] = 1.0 if on else 0.0
    live._bump_buttons()
    if on:
        STATE.update({"a": 1.0, "dpad_up": 1.0})
    else:
        STATE.clear()
    live._poll_once()


out = {"minimum": root.property("minimumVisibleMs"), "before": shown()}
# A tap: pressed and released with no event loop turn between them.
t0 = time.monotonic()
press(True)
press(False)
out["on_now"] = {"hw": chip.property("hwOn"), "xb": chip.property("xbOn"),
                 "dpad": dpad.property("active")}
out["right_after"] = shown()
pump(50)
out["at_50ms"] = shown()
gone = None
while time.monotonic() - t0 < 1.0:
    app.processEvents()
    if not any(shown().values()):
        gone = (time.monotonic() - t0) * 1000.0
        break
    time.sleep(0.002)
out["gone_ms"] = gone
# A held press stays lit as long as it is held.
press(True)
pump(250)
out["held_250ms"] = shown()
press(False)
pump(250)
out["released_250ms"] = shown()
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)
"""


def test_a_short_press_stays_lit_about_100_ms_on_the_pad_card(
    tmp_path: pathlib.Path,
) -> None:
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
    on = {"hw": True, "xb": True, "dpad": True}
    off = {"hw": False, "xb": False, "dpad": False}
    assert out["minimum"] == 100, out
    assert out["before"] == off, out
    assert out["on_now"] == off, out  # the press itself is already over
    assert out["right_after"] == on, out
    assert out["at_50ms"] == on, out
    assert out["gone_ms"] is not None and 80 <= out["gone_ms"] <= 400, out
    assert out["held_250ms"] == on, out
    assert out["released_250ms"] == off, out
