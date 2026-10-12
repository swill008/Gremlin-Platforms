# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen: a long input name on a vJoy Viewer chip (InputViewerCard) or an
Xbox Output View chip (XboxPadCard) is cut with "…" inside its half, so it
never runs over the output half ("OSC Button 30" | "30"); a short chip keeps
today's size (03 S122, D-03-VJOY-VIEWER-QUICK). The real cards are loaded with
their row models fed one long and one short chip."""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

_CODE = r"""
import importlib.util, json, os, sys
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
from gremlin.ui import xbox_output_list, xbox_viewer  # noqa
LONG = "OSC Button 30 with a very long user name"
GUID = "{11111111-2222-3333-4444-555555555555}"


def _vjoy(identifier, label, vinput):
    return {"identifier": identifier, "label": label, "vjoyId": 1,
            "vjoyInput": vinput, "vjoyLabel": f"vJoy 1 Button {vinput}",
            "vjoyGuid": GUID, "destClaimed": True}


module_pairing._module_pair_rows = lambda guid, name, kind: (
    [_vjoy(1, "1", 1), _vjoy(30, LONG, 30)]
    if "Button" in str(kind) else [])


def _xbox(identifier, label, target):
    return {"identifier": identifier, "label": label, "kind": "button",
            "xboxTarget": target, "xboxLabel": target, "xboxChip": "A"}


xbox_viewer.pad_chips = lambda pad: [{
    "guid": GUID, "name": "Stick", "axes": [],
    "buttons": [_xbox(1, "1", "a"), _xbox(30, LONG, "b")]}]
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "Style.qml")),
    "Gremlin.Style", 1, 0, "Style")
engine = QtQml.QQmlEngine()
engine.addImportPath(os.path.join(ROOT, "theme"))
engine.rootContext().setContextProperty("backend", None)
out = {}


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


def chips(root):
    found = []
    for item in walk(root):
        left = [c for c in walk(item) if c.objectName() == "chipLeftText"]
        right = [c for c in walk(item) if c.objectName() == "chipRightText"]
        if len(left) == 1 and len(right) == 1 and item.objectName().endswith(
                "Chip"):
            lx = left[0].mapToScene(QtCore.QPointF(0, 0)).x()
            rx = right[0].mapToScene(QtCore.QPointF(0, 0)).x()
            found.append({
                "text": left[0].property("text"),
                "leftEnd": lx + left[0].width(),
                "rightX": rx,
                "chipWidth": item.width(),
                "truncated": bool(left[0].property("truncated")),
            })
    return found


for name, props in (
    ("InputViewerCard", {"deviceGuid": GUID, "deviceName": "OSC",
                         "title": "OSC", "width": 600}),
    ("XboxPadCard", {"padId": 1, "title": "Xbox 360 1", "drivenBy": "",
                     "boundCount": 2, "width": 900}),
):
    url = QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", name + ".qml"))
    comp = QtQml.QQmlComponent(engine, url)
    root = comp.createWithInitialProperties(props)
    if root is None:
        print("NOT CREATED " + comp.errorString(), flush=True)
        os._exit(1)
    window = QtQuick.QQuickWindow()
    window.resize(1000, 800)
    root.setParentItem(window.contentItem())
    for _ in range(20):
        app.processEvents()
    out[name] = chips(root)
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)
"""


def test_long_chip_names_do_not_overlap(tmp_path: pathlib.Path) -> None:
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
    assert lines, (done.stdout or "")[-3000:] + (done.stderr or "")[-3000:]
    import json

    result = json.loads(lines[-1][len("RESULT ") :])
    # Today's short chip sizes (dp at scale 1): vJoy 40, Xbox 64.
    for card, short_width in (("InputViewerCard", 40), ("XboxPadCard", 64)):
        chips = result[card]
        assert len(chips) == 2, (card, chips)
        by_text = {chip["text"]: chip for chip in chips}
        short, long_ = by_text["1"], by_text[next(t for t in by_text if t != "1")]
        assert short["chipWidth"] == short_width, (card, short)
        assert not short["truncated"], (card, short)
        assert long_["truncated"], (card, long_)
        assert long_["rightX"] >= long_["leftEnd"], (card, long_)
        assert short["rightX"] >= short["leftEnd"], (card, short)
