# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S133 (D-01-UPDATE-NOTES, D-01-UPDATE-WHATSNEW): the Update window shows
only each release's What's new, with small headings, scrollable, newest first
(a version line only when there are several), and a "Full release notes on
GitHub" link below them; "Release notes unavailable." when there are none,
and Update Now still works.

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
RUNNING = sys.argv[3]
SHOT = sys.argv[4]
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
update_model.util.get_code_version = lambda: RUNNING
opened = []
update_model.QtGui.QDesktopServices.openUrl = (
    lambda url: opened.append(url.toString()) or True)
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
         "html_url": f"https://github.com/x/y/releases/tag/{version}",
         "assets": [], "body": body}
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


def release_text(version, extra=""):
    """The release text the release workflow builds: install steps first."""
    notes = (ROOT / "release-notes" / f"{version}.md").read_text(encoding="utf-8")
    return (f"## How to install\n\nInstaller: run Setup {version}.\n\n"
            + notes + extra + "\n## Checksums\n\nsha256 abc\n")


out = {}
model.check(True)
long_points = "".join(f"- Fix number {i}.\n" for i in range(80))
if CASE == "several":
    net.replies[0].finish(doc("1.0.27", release_text("1.0.27"), setup=True))
    pump(100)
    out["height_before"] = win.property("height")
    net.replies[1].finish([
        doc("1.0.27", release_text("1.0.27", long_points)),
        doc("1.0.26", release_text("1.0.26")),
        doc("1.0.25", "Running"),
    ])
elif CASE == "two":
    net.replies[0].finish(doc("1.0.27", release_text("1.0.27"), setup=True))
    net.replies[1].finish([
        doc("1.0.27", release_text("1.0.27")),
        doc("1.0.26", release_text("1.0.26")),
    ])
elif CASE == "one":
    net.replies[0].finish(doc("1.0.27", release_text("1.0.27"), setup=True))
    net.replies[1].finish([doc("1.0.27", release_text("1.0.27"))])
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
area =win.findChild(QtCore.QObject, "releaseNotes")
out["rich"] = bool(area) and QtQml.QQmlExpression(
    QtQml.qmlContext(area), area, "textFormat === TextEdit.RichText").evaluate()[0]
# Every line of the notes is drawn at the window's text size or smaller.
base = win.property("font").pixelSize()
sizes = []
if area is not None:
    quick_document = area.property("textDocument")
    document = quick_document.textDocument()
    block = document.begin()
    while block.isValid():
        frags = block.begin()
        while not frags.atEnd():
            fmt = frags.fragment().charFormat()
            size = fmt.font().pixelSize()
            if size <= 0:
                size = round(fmt.font().pointSizeF() * 96 / 72)
            # Markdown and HTML headings are drawn larger this way.
            size += 4 * max(0, fmt.intProperty(
                QtGui.QTextFormat.Property.FontSizeAdjustment))
            sizes.append(size)
            frags += 1
        block = block.next()
out["largest"] = max(sizes) if sizes else 0
out["base"] = base
link = win.findChild(QtCore.QObject, "fullReleaseNotes")
out["link_visible"] = bool(link and link.property("visible"))
out["link_text"] = link.property("text") if link else ""
out["link_inside_box"] = False
box = win.findChild(QtCore.QObject, "releaseNotesBox")
if link is not None and box is not None:
    parent = link.parentItem()
    while parent is not None and parent != box:
        parent = parent.parentItem()
    out["link_inside_box"] = parent == box
out["old_link"] = any(
    "Release notes</a>" in str(o.property("text") or "")
    for o in win.findChildren(QtCore.QObject)
    if o.metaObject().indexOfProperty("text") >= 0
)
if link is not None and out["link_visible"]:
    QtQml.QQmlExpression(
        QtQml.qmlContext(link), link, "linkActivated('open')").evaluate()
    pump(50)
out["opened"] = list(opened)
if SHOT:
    win.grabWindow().save(SHOT)
    if view is not None and out["scrolls"]:
        # And again further down, where the next version starts.
        QtQml.QQmlExpression(QtQml.qmlContext(view), view,
                             "contentItem.contentY = contentHeight * 0.26").evaluate()
        pump(50)
        win.grabWindow().save(SHOT.replace(".png", "_scrolled.png"))
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


def _run(
    tmp_path: pathlib.Path, case: str, running: str = "1.0.0", shot: str = ""
) -> dict:
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
        [sys.executable, str(script), str(_ROOT), case, running, shot],
        cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-3000:]
    return json.loads(lines[-1][len("RESULT "):])


_SHOT_DIR = _ROOT / ".agent-logs" / "handson" / "UW"


def _shot(name: str) -> str:
    """Where the window's picture is saved for a look, when that folder is
    there (an agent's working copy); "" otherwise."""
    return str(_SHOT_DIR / name) if _SHOT_DIR.is_dir() else ""


def test_several_releases_show_only_whats_new_newest_first(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "several", "1.0.25")
    assert out["state"] == "available"
    notes = out["notes"]
    assert notes is not None and out["view_visible"] and out["rich"]
    # Only What's new: no install text, no "What's new in" line, no marks.
    for gone in ("Installer", "How to install", "Checksums", "What's new",
                 "Running", "#", "**"):
        assert gone not in notes, gone
    # A small version line for each, newest first.
    assert notes.index("1.0.27") < notes.index("Search layers")
    assert notes.index("Search layers") < notes.index("1.0.26")
    assert notes.index("1.0.26") < notes.index("Save Diagnostics")
    assert "Version 1.0" not in notes
    # Small headings: nothing is drawn larger than the window's text.
    assert 0 < out["largest"] <= out["base"]
    assert out["scrolls"]  # long notes scroll inside the window
    assert out["height_after"] == out["height_before"]
    assert out["update_now_visible"] and out["setup_requested"]
    assert out["after_click"] == "downloading"
    assert out["warnings"] == []


def test_two_releases_each_get_a_small_version_line(tmp_path: pathlib.Path) -> None:
    """The real 1.0.27 and 1.0.26 notes, as shown with 1.0.25 running."""
    out = _run(tmp_path, "two", "1.0.25", _shot("update_window.png"))
    notes = out["notes"]
    assert notes.lstrip().startswith("1.0.27")
    assert notes.index("Search layers") < notes.index("1.0.26")
    assert notes.index("1.0.26") < notes.index("Save Diagnostics")
    assert "Installer" not in notes and "What's new" not in notes
    assert 0 < out["largest"] <= out["base"]
    assert out["link_visible"] and out["link_inside_box"]
    assert out["warnings"] == []


def test_one_release_has_no_version_line_and_the_full_notes_link(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "one", "1.0.26", _shot("update_window_one.png"))
    notes = out["notes"]
    assert notes.lstrip().startswith("New")
    assert "1.0.27" not in notes and "Installer" not in notes
    assert 0 < out["largest"] <= out["base"]
    # The link sits in the notes box and opens the newest release's page.
    assert out["link_visible"] and out["link_inside_box"]
    assert "Full release notes on GitHub" in out["link_text"]
    assert out["opened"] == ["https://github.com/x/y/releases/tag/1.0.27"]
    # The old separate "Release notes" link is gone.
    assert out["old_link"] is False
    assert out["warnings"] == []


def test_no_notes_or_no_network_says_unavailable_and_update_now_works(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "unavailable")
    assert out["state"] == "available"
    assert out["notes"].strip() == "Release notes unavailable."
    assert out["link_visible"] and out["link_inside_box"]
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
