# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The "Updated" bar and What's New window on the real start path (01 S183).

Starts the real main window off-screen in its own process (fake hardware, no
network, a temporary home) with a configuration file that says which version
ran last, then reads the banner, the model, the window and the setting.
The setting is written by UpdateModel at the same start, after WhatsNewModel
has read it; two starts in a row on one home show the bar only once.
"""

from __future__ import annotations

import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

sys.path.append(".")

import json
import os
import pathlib
import re

_ROOT = pathlib.Path(__file__).parents[2]
_VERSION = json.loads((_ROOT / "version.json").read_text(encoding="utf-8"))["version"]

_CODE = """
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import joystick_gremlin
from PySide6 import QtCore, QtQml, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty('visible', True)
QtTest.QTest.qWait(500)

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value[0] if isinstance(value, tuple) else value

def child(name):
    return win.findChild(QtCore.QObject, name)

def whats_new_window():
    for w in app.topLevelWindows():
        if w.title() == "What's New":
            return w
    return None

banner = child('whatsNewBanner')
out = {
    'bannerVisible': bool(banner.property('visible')),
    'bannerTitle': child('whatsNewBannerTitle').property('text'),
    'bannerMessage': child('whatsNewBannerMessage').property('text'),
    'modelBanner': bool(app.whats_new.property('bannerVisible')),
    'windowBefore': whats_new_window() is not None,
}
if sys.argv[1] == 'help':
    run('Commands.trigger("help.whatsNew")')
    QtTest.QTest.qWait(1500)
    w = whats_new_window()
    out['window'] = w is not None
    if w is not None:
        out['windowVisible'] = bool(w.isVisible())
        notes = w.findChild(QtCore.QObject, 'whatsNewNotes')
        out['windowText'] = notes.property('text') if notes else None
    out['notesHtml'] = app.whats_new.property('notesHtml')
elif sys.argv[1] == 'banner':
    # The banner's link, as a click does it.
    link = child('whatsNewBannerLink')
    QtCore.QMetaObject.invokeMethod(link, 'activate')
    QtTest.QTest.qWait(1500)
    w = whats_new_window()
    out['window'] = w is not None
    out['notesHtml'] = app.whats_new.property('notesHtml')
    out['bannerStaysAfterOpen'] = bool(app.whats_new.property('bannerVisible'))
from gremlin.config import Configuration
Configuration().save_now()
out['setting'] = Configuration().value('global', 'internal', 'last-run-version')
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def _seed(home: pathlib.Path, last: str | None) -> None:
    """A configuration file whose last-run-version is `last` (none: no file)."""
    folder = home / "Gremlin Platforms"
    folder.mkdir(parents=True, exist_ok=True)
    if last is None:
        return
    entry = {"value": last, "data_type": "string", "properties": {}, "expose": False}
    data = {"global": {"internal": {"last-run-version": entry}}}
    (folder / "configuration.json").write_text(json.dumps(data), encoding="utf-8")


def _start(home: pathlib.Path, mode: str = "plain") -> dict:
    script = home / "whats_new_child.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    result = proc_tree.run(
        [sys.executable, str(script), mode], cwd=_ROOT, env=env,
        text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT "):])


def _first_bold_words() -> str:
    """The first three words of the first bold text in the running version's notes."""
    text = (_ROOT / "release-notes" / f"{_VERSION}.md").read_text(encoding="utf-8")
    bold = re.search(r"\*\*(.+?)\*\*", text)
    assert bold, "the running version's notes have no bold text"
    return " ".join(bold.group(1).split()[:3])


def test_first_start_after_an_update_shows_the_bar_and_records_the_version(
    tmp_path: pathlib.Path,
) -> None:
    _seed(tmp_path, "1.0.39")
    out = _start(tmp_path)
    assert out["bannerVisible"] and out["modelBanner"]
    assert out["bannerTitle"] == f"Updated to {_VERSION}"
    assert out["bannerMessage"] == "See what changed in this version."
    assert out["setting"] == _VERSION
    assert not out["windowBefore"]


def test_the_bar_link_opens_the_notes_of_the_versions_since(
    tmp_path: pathlib.Path,
) -> None:
    _seed(tmp_path, "1.0.39")
    out = _start(tmp_path, "banner")
    assert out["window"], "the What's New window did not open"
    assert out["bannerStaysAfterOpen"]
    assert _first_bold_words() in out["notesHtml"]


def test_second_start_on_the_same_home_has_no_bar(tmp_path: pathlib.Path) -> None:
    _seed(tmp_path, "1.0.39")
    assert _start(tmp_path)["bannerVisible"]
    again = _start(tmp_path)
    assert not again["bannerVisible"] and not again["modelBanner"]
    assert again["setting"] == _VERSION


def test_fresh_profile_has_no_bar_and_records_the_version(
    tmp_path: pathlib.Path,
) -> None:
    _seed(tmp_path, None)
    out = _start(tmp_path)
    assert not out["bannerVisible"] and not out["modelBanner"]
    assert out["setting"] == _VERSION


def test_help_whats_new_opens_the_window_with_the_running_versions_notes(
    tmp_path: pathlib.Path,
) -> None:
    # No bar here (the same version ran last): the Help command alone opens it.
    _seed(tmp_path, _VERSION)
    out = _start(tmp_path, "help")
    assert not out["bannerVisible"]
    assert out["window"] and out["windowVisible"]
    assert _first_bold_words() in out["notesHtml"]
    assert _first_bold_words() in (out["windowText"] or "")
