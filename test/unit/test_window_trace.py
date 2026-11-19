# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Window tracing (01 S175-S178, D-01-WINDOW-TRACE).

One off-screen process runs a window built like Main.qml (a `trayed` flag
and the real qml/PageLoader.qml for Home and Device Bindings) with the real
window_trace taps, Tracing on and the Window row ticked, under a temporary
user profile. Its results are shared by the tests below.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib
import sys
import tempfile

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_SCRIPT = r"""
import json, logging, os, sys, time
sys.path.insert(0, sys.argv[1])
from PySide6 import QtCore, QtGui, QtQml, QtTest

app = QtGui.QGuiApplication([])
from gremlin import trace
from gremlin.ui import window_trace

def wait(ms):
    QtTest.QTest.qWait(ms)

def until(fn, ms=3000):
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end and not fn():
        wait(20)
    return fn()

def window_lines():
    return [(c, d) for (_t, c, p, d, *_r) in trace.lines() if p == trace.WINDOW]

trace.set_enabled(True)
trace.set_window(True)

engine = QtQml.QQmlApplicationEngine()
window_trace.expose(engine)
qml_dir = os.path.join(sys.argv[1], "qml")
engine.loadData(b'''
import QtQuick
import QtQuick.Window
Window {
    id: win
    x: 40; y: 40; width: 300; height: 200
    property bool trayed: false
    PageLoader {
        traceName: "Home"
        active: !win.trayed
        sourceComponent: Rectangle {}
    }
    PageLoader {
        traceName: "Device Bindings"
        active: !win.trayed
        sourceComponent: Rectangle {}
    }
}
''', QtCore.QUrl.fromLocalFile(os.path.join(qml_dir, "_window_trace_test.qml")))
window = engine.rootObjects()[0]
window.show()
wait(100)
window_trace.install(window, engine)
out = {"startup": window_lines()}

# Hidden to the tray, then shown again.
window.hide()
window.setProperty("trayed", True)
until(lambda: ("Home", "Home unloaded") in window_lines())
window.setProperty("trayed", False)
window.show()
until(lambda: ("Home", "Home loaded") in window_lines()[len(out["startup"]):])
out["tray"] = window_lines()
out["recent"] = trace.recent_lines()

# The tray and the page disagree: shown, page trayed, tray says not.
window_trace.set_tray_state_reader(lambda: False)
window_trace.bridge()._trayed_at = -1e9
seen = len(trace.recent_lines())
window.setProperty("trayed", True)
wait(50)
out["state_differ"] = window_trace.state_text()
window.setProperty("trayed", False)
wait(50)
out["state_same"] = window_trace.state_text()
out["recent_visible"] = trace.recent_lines()[seen:]

# Save Window State with the default system.log level (Warning).
records = []
class Grab(logging.Handler):
    def emit(self, record):
        records.append((record.levelno, record.getMessage()))
syslog = logging.getLogger("system")
syslog.setLevel(logging.WARNING)
syslog.addHandler(Grab(level=logging.WARNING))
window_trace.save_state()
out["saved"] = records[:]
records.clear()
window_trace.warn("test warning")
out["warned"] = records[:]

# A drag: many moves settle to one line.
before = len(window_lines())
for i in range(20):
    window.setX(50 + i)
    wait(5)
wait(window_trace.SETTLE_MS + 400)
out["moves"] = [d for (_c, d) in window_lines()[before:] if d.startswith("moved to")]

# Screens added and removed (Qt's own signals).
screen = app.primaryScreen()
app.screenAdded.emit(screen)
app.screenRemoved.emit(screen)
out["screens"] = [d for (_c, d) in window_lines() if d.startswith("screen ")]

# Active: rate limited to one line a second.
bridge = window_trace.bridge()
bridge._active_line_at = -1e9
before = len(window_lines())
for _ in range(6):
    bridge._active_changed()
quick = [d for (_c, d) in window_lines()[before:] if "active" in d]
wait(int(window_trace.ACTIVE_GAP_S * 1000) + 300)
out["active"] = {"quick": quick,
                 "after": [d for (_c, d) in window_lines()[before:] if "active" in d]}
out["last_known"] = window_trace.last_known()
print("RESULT " + json.dumps(out, default=str), flush=True)
os._exit(0)
"""


@functools.lru_cache(maxsize=1)
def _run() -> dict:
    home = tempfile.mkdtemp(prefix="wt-home-")
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "USERPROFILE": home,
        "APPDATA": os.path.join(home, "AppData", "Roaming"),
        "LOCALAPPDATA": os.path.join(home, "AppData", "Local"),
        "PYTHONIOENCODING": "utf-8",
    }
    result = proc_tree.run(
        [sys.executable, "-c", _SCRIPT, str(_ROOT)],
        text=True,
        encoding="utf-8",
        timeout=90,
        env=env,
    )
    for line in result.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):])
    raise AssertionError(result.stdout[-2000:] + result.stderr[-3000:])


def test_hiding_and_showing_writes_window_and_page_lines() -> None:
    out = _run()
    tray = [tuple(x) for x in out["tray"][len(out["startup"]):]]
    assert ("Main window", "hidden") in tray
    assert ("Home", "Home unloaded") in tray
    assert ("Device Bindings", "Device Bindings unloaded") in tray
    assert ("Main window", "page trayed: yes") in tray
    assert ("Main window", "shown (Windowed)") in tray
    assert tray.index(("Home", "Home loaded")) > tray.index(("Home", "Home unloaded"))


def test_tray_page_lines_are_kept_in_the_recent_events() -> None:
    recent = "\n".join(_run()["recent"])
    assert "Home unloaded" in recent and "Home loaded" in recent
    assert "hidden" in recent and "page trayed: yes" in recent


def test_tray_page_lines_are_kept_while_the_window_shows() -> None:
    # The page's trayed flag flips with the window showing (today's blank
    # window): the page lines are tray events, kept in the recent events.
    recent = "\n".join(_run()["recent_visible"])
    assert "Home  Home unloaded" in recent and "Home  Home loaded" in recent


def test_state_text_marks_tray_and_page_out_of_step() -> None:
    out = _run()
    assert "page says trayed YES  <-- differ" in out["state_differ"]
    assert "tray says hidden-to-tray no" in out["state_differ"]
    assert "differ" not in out["state_same"]
    assert "Recent window events" in out["state_same"]


def test_save_window_state_writes_at_warning_with_the_default_level() -> None:
    saved = _run()["saved"]
    assert len(saved) == 1
    level, text = saved[0]
    assert level == 30  # logging.WARNING
    assert text.startswith("Window state (asked for):")


def test_warn_writes_window_line_and_recent_events() -> None:
    warned = _run()["warned"]
    assert len(warned) == 1 and warned[0][0] == 30
    assert warned[0][1].startswith("Window: test warning\nRecent window events")


def test_move_writes_one_line_after_it_settles() -> None:
    moves = _run()["moves"]
    assert len(moves) == 1, moves
    assert moves[0].startswith("moved to 69,")


def test_screen_added_and_removed_are_recorded() -> None:
    screens = _run()["screens"]
    assert any(s.startswith("screen added ") for s in screens), screens
    assert any(s.startswith("screen removed ") for s in screens), screens


def test_active_changes_are_rate_limited() -> None:
    active = _run()["active"]
    assert len(active["quick"]) == 1, active
    assert len(active["after"]) == 2, active
    assert "(4 changes between)" in active["after"][1]


def test_last_known_is_plain_values() -> None:
    known = _run()["last_known"]
    assert known["visible"] is True
    assert known["tray_says_trayed"] is False
    assert known["pages"]["Home"] == "loaded"
