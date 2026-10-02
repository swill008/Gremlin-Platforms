# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A profile that fails to load says why and puts back what was open; the
rename dialog never accepts a name its rule rejects, however it got there."""

from __future__ import annotations

import sys

sys.path.append(".")

import os
import pathlib
import subprocess
import types

import pytest

from gremlin.ui import backend

_ROOT = pathlib.Path(__file__).resolve().parents[2]
# Backend is a singleton wrapper; the method lives on the class inside it.
_LOAD = backend.Backend.klass._load_profile


def _fake(previous: str, broken: str) -> types.SimpleNamespace:
    fake = types.SimpleNamespace(
        profile=types.SimpleNamespace(fpath=previous or None),
        activate_gremlin=lambda on: None,
        blank=False,
        opened=[],
    )

    def read(path: str) -> None:
        if path == broken:
            raise ValueError("not well-formed (invalid token): line 3")
        fake.opened.append(path)

    def new_profile() -> None:
        fake.blank = True

    fake._read_profile = read
    fake.newProfile = new_profile
    return fake


@pytest.fixture
def errors(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        backend, "display_error", lambda msg, detail="": shown.append((msg, detail))
    )
    return shown


def test_failed_load_reopens_the_profile_that_was_open(
    tmp_path: pathlib.Path, errors: list[tuple[str, str]]
) -> None:
    good = tmp_path / "good.xml"
    broken = tmp_path / "broken.xml"
    good.write_text("<profile/>", encoding="utf-8")
    broken.write_text("<profile", encoding="utf-8")
    fake = _fake(str(good), str(broken))
    assert _LOAD(fake, str(broken)) is False
    assert fake.opened == [str(good)]
    assert not fake.blank
    (message, detail), = errors
    assert "Could not load the profile" in message and "broken.xml" in message
    assert "not well-formed" in detail and "is open again" in detail


def test_failed_load_with_nothing_to_reopen_says_so(
    tmp_path: pathlib.Path, errors: list[tuple[str, str]]
) -> None:
    broken = tmp_path / "broken.xml"
    broken.write_text("<profile", encoding="utf-8")
    fake = _fake("", str(broken))
    assert _LOAD(fake, str(broken)) is False
    assert fake.blank
    (_message, detail), = errors
    assert "new, empty profile" in detail


# Runs off-screen in its own process: the tests' qapp fixture starts the
# whole program.
_DIALOG = r"""
import os, sys
from PySide6 import QtCore, QtGui, QtQml

class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)

root = sys.argv[1]
app = QtGui.QGuiApplication([])
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(root + "/qml/Style.qml"), "Gremlin.Style", 1, 0, "Style")
engine = QtQml.QQmlApplicationEngine()
engine.addImportPath(root + "/theme")
fake = FakeBackend()
engine.rootContext().setContextProperty("backend", fake)
engine.loadData(b'''
import QtQuick
import QtQuick.Controls
ApplicationWindow {
    width: 400; height: 300; visible: true
    property var got: []
    TextInputDialog {
        id: dlg
        allowBlank: false
        validator: function(v) { return v !== "taken" }
        onAccepted: (v) => got.push(v)
    }
    function attempt(seed) {
        dlg.text = seed
        dlg.open()
        dlg._accept()
        dlg.close()
        return got.join(",")
    }
}
''', QtCore.QUrl.fromLocalFile(root + "/qml/Harness.qml"))
win = engine.rootObjects()[0]
for seed in ("taken", "", "  ", "free"):
    ctx = QtQml.qmlContext(win)
    out = QtQml.QQmlExpression(ctx, win, f"attempt({seed!r})").evaluate()
    print("RESULT", repr(seed), out[0] if isinstance(out, tuple) else out, flush=True)
os._exit(0)
"""


def test_rename_dialog_rejects_seeded_and_blank_names() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _DIALOG, str(_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_CONTROLS_STYLE": "GremlinStyle",
        },
    )
    lines = [line for line in result.stdout.splitlines() if line.startswith("RESULT")]
    # A taken name (even pre-filled), a blank and a spaces-only name are
    # refused; only the free name gets through.
    assert lines == [
        "RESULT 'taken' ",
        "RESULT '' ",
        "RESULT '  ' ",
        "RESULT 'free' free",
    ], result.stderr[-2000:]
