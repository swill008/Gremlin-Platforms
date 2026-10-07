# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S133 (D-01-UPDATE-NOTES): the Update window shows the release notes,
formatted and scrollable, newest first; "Release notes unavailable." when
there are none, and Update Now still works.

The real DialogUpdate.qml and UpdateModel run off-screen in their own
process; a stand-in network hands over GitHub's replies (nothing goes out).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_SCRIPT = r'''
import json, os, sys, tempfile, unittest.mock
from pathlib import Path

ROOT = Path(sys.argv[1])
CASE = sys.argv[2]
sys.path.insert(0, str(ROOT))
import gremlin.util
gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

from PySide6 import QtCore, QtGui, QtNetwork, QtQml
from gremlin import clock, updater
from gremlin.config import Configuration

app = QtGui.QGuiApplication(sys.argv[:1])
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
    "Gremlin.Style", 1, 0, "Style",
)
import joystick_gremlin
joystick_gremlin.register_config_options()
from gremlin.ui import update_model

updates = Path(tempfile.mkdtemp())
updater.updates_dir = lambda: updates
update_model.util.get_code_version = lambda: "1.0.0"
Configuration().set("global", "internal", "update-feed-url", "")


class Reply(QtCore.QObject):
    finished = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.data, self.err = b"", QtNetwork.QNetworkReply.NetworkError.NoError

    def finish(self, doc=None, err=None):
        self.data = json.dumps(doc).encode() if doc is not None else b""
        if err is not None:
            self.err = err
        self.finished.emit()

    def error(self): return self.err
    def errorString(self): return "Host not found"
    def readAll(self): return QtCore.QByteArray(self.data)
    def deleteLater(self): pass
    def abort(self): pass

    class _Sig:
        def connect(self, *_): pass
    readyRead = _Sig()
    downloadProgress = _Sig()


class Network:
    def __init__(self):
        self.urls, self.replies = [], []

    def get(self, request):
        self.urls.append(request.url().toString())
        reply = Reply()
        self.replies.append(reply)
        return reply


class Backend(QtCore.QObject):
    changed = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)


def doc(version, body, setup=False):
    d = {"tag_name": f"Gremlin-Platforms-R1-{version}",
         "html_url": "https://github.com/x/y", "assets": [], "body": body}
    if setup:
        d["assets"] = [{"name": updater.setup_name(version),
                        "browser_download_url": "https://github.com/x/y/s.exe",
                        "size": 10, "digest": "sha256:" + "a" * 64}]
    return d


model = update_model.UpdateModel()
model._kind = updater.INSTALLED
net = Network()
model._network = net
os.environ.pop("GREMLIN_OFFLINE", None)

engine = QtQml.QQmlApplicationEngine()
engine.addImportPath(str(ROOT / "theme"))
warnings = []
engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
backend = Backend()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("updater", model)
engine.load(QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogUpdate.qml")))
win = engine.rootObjects()[0]
win.setProperty("visible", True)


def pump(ms=300):
    end = clock.monotonic() + ms / 1000.0
    while clock.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


def notes_shown():
    area = win.findChild(QtCore.QObject, "releaseNotes")
    if area is None:
        return None
    expr = QtQml.QQmlExpression(QtQml.qmlContext(area), area, "getText(0, length)")
    return expr.evaluate()[0]


out = {}
model.check(True)
long_body = "\n\n".join(f"- Fix number {i}." for i in range(80))
if CASE == "several":
    net.replies[0].finish(doc("1.0.2", "Two", setup=True))
    pump(100)
    out["height_before"] = win.property("height")
    body = "## Fixed\n\nThe **mouse** sticks.\n\n" + long_body
    net.replies[1].finish(
        [doc("1.0.2", body), doc("1.0.1", "One"), doc("1.0.0", "Running")])
elif CASE == "unavailable":
    net.replies[0].finish(doc("1.0.1", None, setup=True))
    net.replies[1].finish(None, QtNetwork.QNetworkReply.NetworkError.HostNotFoundError)
elif CASE == "slow":
    net.replies[0].finish(doc("1.0.1", "", setup=True))  # the list never answers
pump()
out["state"] = model.state
out["notes"] = notes_shown()
view = win.findChild(QtCore.QObject, "releaseNotesView")
out["view_visible"] = bool(view and view.property("visible"))
out["scrolls"] = bool(view) and (
    (view.property("contentHeight") or 0) > (view.property("height") or 0))
out["height_after"] = win.property("height")
button = win.findChild(QtCore.QObject, "updateNow")
out["update_now_visible"] = bool(button and button.property("visible"))
if button is not None:
    QtCore.QMetaObject.invokeMethod(button, "click")
    pump(100)
out["after_click"] = model.state
out["setup_requested"] = any(u.endswith("/s.exe") for u in net.urls)
out["warnings"] = [w for w in warnings if "DialogUpdate" in w]
print("RESULT " + json.dumps(out), flush=True)
'''


def _run(tmp_path: pathlib.Path, case: str) -> dict:
    script = tmp_path / "update_notes_window.py"
    script.write_text(_SCRIPT, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    result = subprocess.run(
        [sys.executable, str(script), str(_ROOT), case], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-3000:]
    return json.loads(lines[-1][len("RESULT "):])


def test_several_releases_show_newest_first_formatted_and_scrollable(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "several")
    assert out["state"] == "available"
    notes = out["notes"]
    assert notes is not None and out["view_visible"]
    assert notes.index("Version 1.0.2") < notes.index("Version 1.0.1")
    assert "Running" not in notes
    # Formatted: the Markdown marks are gone, the words stay.
    assert "The mouse sticks." in notes and "**" not in notes and "##" not in notes
    assert out["scrolls"]  # long notes scroll inside the window
    assert out["height_after"] == out["height_before"]
    assert out["update_now_visible"] and out["setup_requested"]
    assert out["after_click"] == "downloading"
    assert out["warnings"] == []


def test_no_notes_or_no_network_says_unavailable_and_update_now_works(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "unavailable")
    assert out["state"] == "available"
    assert out["notes"].strip() == "Release notes unavailable."
    assert out["update_now_visible"] and out["setup_requested"]
    assert out["after_click"] == "downloading"
    assert out["warnings"] == []


def test_a_list_that_never_answers_doesnt_hold_up_the_window(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "slow")
    assert out["state"] == "available"
    assert out["notes"] is not None and "unavailable" not in out["notes"]
    assert out["update_now_visible"] and out["setup_requested"]
    assert out["after_click"] == "downloading"
