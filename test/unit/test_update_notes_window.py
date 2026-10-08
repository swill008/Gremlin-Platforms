# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S133 (D-01-UPDATE-NOTES, D-01-UPDATE-WHATSNEW, D-01-UPDATE-NOTES-CACHE):
the Update window shows
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

import pytest

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

from PySide6 import QtCore, QtGui, QtNetwork, QtQml, QtQuick
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
    uiScale = QtCore.Property(
        int, fget=lambda self: int(os.environ.get("NOTES_UI_SCALE", "100")),
        notify=changed)


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
elif CASE == "refill":
    # 1.0.26 running, 1.0.28 offered: its own notes show at once, then the
    # list arrives and the text grows with 1.0.27's (the user's 2026-10-08
    # report: the new part stayed blank until the window was redrawn).
    view = win.findChild(QtCore.QObject, "releaseNotesView")
    area = win.findChild(QtCore.QObject, "releaseNotes")
    texts = []
    area.textChanged.connect(lambda: texts.append(area.property("text")))
    net.replies[0].finish(doc("1.0.28", release_text("1.0.28"), setup=True))
    pump(300)
    # Still "Checking…" while the list is on its way: nothing shown yet.
    out["state_before_list"] = model.state
    out["view_visible_before_list"] = bool(view.property("visible"))
    out["texts_before_list"] = len(
        [t for t in texts if "Release notes unavailable." not in t])
    out["area_h_before"] = area.property("height")
    out["view_content_before"] = view.property("contentHeight")
    net.replies[1].finish([
        doc("1.0.28", release_text("1.0.28")),
        doc("1.0.27", release_text("1.0.27")),
    ])
    # On screen a frame can be drawn as soon as the text changes, before
    # the text area's new height has reached it.
    out["area_h_at_change"] = area.property("height")
    win.grabWindow()
    pump(300)
    out["state"] = model.state
    # The notes put in the box (a format switch re-sends the placeholder).
    out["texts_after_list"] = len(
        [t for t in texts if "Release notes unavailable." not in t])
    out["has_both"] = all(v in area.property("text") for v in ("1.0.28", "1.0.27"))
    # The window is drawn with the new text at the top first (as on screen),
    # then scrolled; a grab only redraws what changed since.
    win.grabWindow()
    out["text_len"] = len(area.property("text"))
    out["observes_viewport"] = bool(
        area.flags() & QtQuick.QQuickItem.Flag.ItemObservesViewport)
    quick_doc = area.property("textDocument")
    doc_h = quick_doc.textDocument().size().height()
    out["doc_h"] = doc_h
    out["area_h"] = area.property("height")
    out["area_implicit_h"] = area.property("implicitHeight")
    out["area_content_h"] = area.property("contentHeight")
    out["view_content_h"] = view.property("contentHeight")
    flick = view.property("contentItem")
    out["flick_content_h"] = flick.property("contentHeight")
    out["view_h"] = view.property("height")
    # Scroll to the bottom, as the user did, and look at what is painted.
    flick.setProperty(
        "contentY", max(0, flick.property("contentHeight") - view.property("height")))
    pump(200)
    out["content_y"] = flick.property("contentY")
    image = win.grabWindow()
    if SHOT:
        image.save(SHOT)
    top_left = view.mapToItem(None, QtCore.QPointF(0, 0))
    x0, y0 = int(top_left.x()), int(top_left.y())
    w, h = int(view.property("width")), int(view.property("height"))
    image = image.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    ratio = image.devicePixelRatio()
    def inked(ys, ye):
        back = image.pixel(int((x0 + 3) * ratio), int((y0 + ys) * ratio))
        count = 0
        for y in range(int((y0 + ys) * ratio), int((y0 + ye) * ratio), 2):
            for x in range(int((x0 + 4) * ratio), int((x0 + w - 16) * ratio), 2):
                if image.pixel(x, y) != back:
                    count += 1
        return count
    out["ink_upper"] = inked(2, h // 2)
    out["ink_lower"] = inked(h // 2, h - 2)
    # Just above the "Full release notes" link, the last of 1.0.27's text.
    expr = QtQml.QQmlExpression(QtQml.qmlContext(area), area, "getText(0, length)")
    out["last_line"] = expr.evaluate()[0].strip().splitlines()[-1]
    print("RESULT " + json.dumps(out), flush=True)
    sys.exit(0)
elif CASE in ("focus_dark", "focus_light"):
    # Clicking into the notes (the user's report, dark theme: the box
    # turned white). Each state is grabbed and the box's commonest colour
    # is compared with the box's own colour.
    style = engine.singletonInstance("Gremlin.Style", "Style")
    style.setProperty("isDarkMode", CASE == "focus_dark")
    net.replies[0].finish(doc("1.0.27", release_text("1.0.27"), setup=True))
    net.replies[1].finish([doc("1.0.27", release_text("1.0.27"))])
    pump(300)
    box = win.findChild(QtCore.QObject, "releaseNotesBox")
    area = win.findChild(QtCore.QObject, "releaseNotes")
    view = win.findChild(QtCore.QObject, "releaseNotesView")
    out["well"] = box.property("color").name()

    def commonest():
        image = win.grabWindow().convertToFormat(QtGui.QImage.Format.Format_RGB32)
        ratio = image.devicePixelRatio()
        tl = view.mapToItem(None, QtCore.QPointF(0, 0))
        w, h = view.property("width"), view.property("height")
        counts = {}
        for y in range(int((tl.y() + 2) * ratio), int((tl.y() + h - 2) * ratio), 3):
            for x in range(int((tl.x() + 2) * ratio), int((tl.x() + w - 2) * ratio), 3):
                c = image.pixel(x, y) & 0xFFFFFF
                counts[c] = counts.get(c, 0) + 1
        return "#%06x" % max(counts, key=counts.get), image

    out["unfocused"], _ = commonest()
    out["text_unfocused"] = area.property("color").name()
    win.requestActivate()
    area.forceActiveFocus()
    pump(150)
    out["area_focus"] = bool(area.property("activeFocus"))
    out["focused"], _ = commonest()
    out["text_focused"] = area.property("color").name()
    # And a real click into the text.
    from PySide6 import QtTest
    area.setProperty("focus", False)
    win.contentItem().forceActiveFocus()
    pump(50)
    centre = view.mapToItem(None, QtCore.QPointF(
        view.property("width") / 2, view.property("height") / 2))
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier,
                            centre.toPoint())
    pump(150)
    out["click_focus"] = bool(area.property("activeFocus"))
    out["clicked"], image = commonest()
    out["read_only"] = bool(area.property("readOnly"))
    out["select_by_mouse"] = bool(area.property("selectByMouse"))
    out["text_clicked"] = area.property("color").name()
    if SHOT:
        image.save(SHOT)
    print("RESULT " + json.dumps(out), flush=True)
    sys.exit(0)
elif CASE == "slow":
    update_model._NOTES_WAIT_MS = 200
    net.replies[0].finish(
        doc("1.0.1", "## What's new in 1.0.1\n\n- Point one\n", setup=True))
    # The list never answers.
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
# The space around the rule between versions: from the bottom of the last
# line above it to the top of the next "What's new in" line, in lines.
out["rules"] = 0
out["rule_gap_lines"] = 0.0
if area is not None:
    layout = document.documentLayout()
    rule = QtGui.QTextFormat.Property.BlockTrailingHorizontalRulerWidth
    prev = None
    block = document.begin()
    while block.isValid():
        if block.blockFormat().hasProperty(rule):
            out["rules"] += 1
            after = block.next()
            if prev is not None and after.isValid() and out["rules"] == 1:
                top = layout.blockBoundingRect(prev)
                line = prev.layout().lineAt(prev.layout().lineCount() - 1)
                above = top.top() + line.rect().bottom()
                below = (layout.blockBoundingRect(after).top()
                         + after.layout().lineAt(0).rect().top())
                out["rule_gap_lines"] = (below - above) / line.height()
                out["rule_next"] = after.text()
        elif block.text().strip():
            prev = block
        block = block.next()
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
        # And again further down, where the next version starts: the rule
        # and its "What's new in" line in the middle of the box.
        y = 0.0
        if area is not None:
            block = document.begin()
            while block.isValid():
                if block.blockFormat().hasProperty(
                        QtGui.QTextFormat.Property.BlockTrailingHorizontalRulerWidth):
                    y = document.documentLayout().blockBoundingRect(block).top()
                    break
                block = block.next()
        QtQml.QQmlExpression(
            QtQml.qmlContext(view), view,
            f"contentItem.contentY = Math.max(0, Math.min({y} - height / 2, "
            "contentHeight - height))").evaluate()
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
    tmp_path: pathlib.Path, case: str, running: str = "1.0.0", shot: str = "",
    scale: int = 100,
) -> dict:
    script = tmp_path / "update_notes_window.py"
    script.write_text(_SCRIPT, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", NOTES_UI_SCALE=str(scale),
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


_UB_DIR = _ROOT / ".agent-logs" / "handson" / "UB"


def _shot_ub(name: str) -> str:
    return str(_UB_DIR / name) if _UB_DIR.is_dir() else ""


def test_several_releases_show_only_whats_new_newest_first(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "several", "1.0.25")
    assert out["state"] == "available"
    notes = out["notes"]
    assert notes is not None and out["view_visible"] and out["rich"]
    # Only What's new: no install text, no marks.
    for gone in ("Installer", "How to install", "Checksums",
                 "Running", "#", "**"):
        assert gone not in notes, gone
    # A small "What's new in <version>" line for each, newest first, and
    # nothing else says it (D-01-UPDATE-VERSION-LINE).
    assert notes.count("What's new") == 2
    assert notes.index("What's new in 1.0.27") < notes.index("Search layers")
    assert notes.index("Search layers") < notes.index("What's new in 1.0.26")
    assert notes.index("What's new in 1.0.26") < notes.index("Save Diagnostics")
    # A thin rule between them, with about a line of space each side.
    assert out["rules"] == 1 and out["rule_next"] == "What's new in 1.0.26"
    assert out["rule_gap_lines"] >= 2.5, out["rule_gap_lines"]
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
    assert notes.lstrip().startswith("What's new in 1.0.27")
    assert notes.index("Search layers") < notes.index("What's new in 1.0.26")
    assert notes.index("What's new in 1.0.26") < notes.index("Save Diagnostics")
    assert notes.count("What's new") == 2 and "Installer" not in notes
    assert out["rules"] == 1 and out["rule_gap_lines"] >= 2.5, out
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
    # One version: no "What's new in" line and no rule.
    assert "What's new" not in notes and out["rules"] == 0
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
    # After the wait, the newest release's own notes.
    assert out["notes"] is not None and "Point one" in out["notes"]
    assert out["update_now_visible"] and out["setup_requested"]
    assert out["after_click"] == "downloading"


@pytest.mark.parametrize("scale", [100, 175])
def test_skipped_versions_fill_the_box_once_laid_out_and_painted(
    tmp_path: pathlib.Path, scale: int,
) -> None:
    """1.0.26 running, 1.0.28 offered (1.0.27 skipped; the user's report
    2026-10-08: the box was refilled while open and the added part stayed
    blank until a resize). D-01-UPDATE-NOTES-CACHE: the window waits for
    the list and is filled once, with both; scrolled to the bottom, the
    text is laid out and drawn, not a blank area."""
    out = _run(tmp_path, "refill", "1.0.26",
               _shot_ub(f"scrolled_after_refill_{scale}.png"), scale)
    assert out["state_before_list"] == "checking", out
    assert out["texts_before_list"] == 0, out
    assert out["state"] == "available" and out["has_both"], out
    assert out["texts_after_list"] == 1, out  # filled once
    # The text area and the scroll view follow the longer text.
    assert out["area_h"] >= out["doc_h"] - 1, out
    assert out["view_content_h"] >= out["doc_h"] - 1, out
    assert out["flick_content_h"] >= out["doc_h"] - 1, out
    assert out["view_content_h"] > out["view_content_before"], out
    # Scrolled down past the first screenful, and the lower half is drawn.
    assert out["content_y"] > 0, out
    assert out["ink_upper"] > 50 and out["ink_lower"] > 50, out


_UC_DIR = _ROOT / ".agent-logs" / "handson" / "UC"


@pytest.mark.parametrize("case", ["focus_dark", "focus_light"])
def test_clicking_into_the_notes_keeps_the_box_colour(
    tmp_path: pathlib.Path, case: str,
) -> None:
    """The user's report (dark theme): clicking into the release notes
    turned their background white. The read-only notes draw no background
    of their own in any state: the box's colour shows, focused or not, and
    the text keeps the theme's colour."""
    shot = str(_UC_DIR / f"{case}.png") if _UC_DIR.is_dir() else ""
    out = _run(tmp_path, case, "1.0.26", shot)
    assert out["unfocused"] == out["well"], out
    assert out["area_focus"] and out["focused"] == out["well"], out
    assert out["click_focus"] and out["clicked"] == out["well"], out
    assert out["read_only"] and out["select_by_mouse"], out
    # The text keeps its colour (the style's focused look switched it to
    # the light theme's black, unreadable on the dark box).
    assert out["text_focused"] == out["text_unfocused"], out
    assert out["text_clicked"] == out["text_unfocused"], out

    def light(c: str) -> float:
        r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255

    assert abs(light(out["text_unfocused"]) - light(out["well"])) > 0.4, out
