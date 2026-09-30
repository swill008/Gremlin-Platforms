# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

from gremlin.ui import ui_scale_option

QML_DIR = pathlib.Path(__file__).resolve().parents[2] / "qml"


@pytest.fixture
def windows_scaling_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QT_ENABLE_HIGHDPI_SCALING", "0")


@pytest.fixture
def windows_scaling_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QT_ENABLE_HIGHDPI_SCALING", raising=False)


def _saved(monkeypatch: pytest.MonkeyPatch, value: int) -> None:
    monkeypatch.setattr(ui_scale_option, "saved_scale", lambda: value)


def test_windows_scaling_on_ignores_slider(
    windows_scaling_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _saved(monkeypatch, 150)
    assert ui_scale_option.active_scale() == 100
    assert ui_scale_option.dp(15) == 15


def test_windows_scaling_off_uses_slider(
    windows_scaling_off: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _saved(monkeypatch, 150)
    assert ui_scale_option.active_scale() == 150
    assert ui_scale_option.dp(15) == 23


def test_dp_rounds_half_up_like_qml(
    windows_scaling_off: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _saved(monkeypatch, 70)
    assert ui_scale_option.dp(15) == 11
    assert ui_scale_option.dp(1) == 1


@pytest.mark.parametrize(
    "raw, expected", [(50, 70), (250, 200), ("abc", 100), (137.6, 138)]
)
def test_clamp_scale(raw: object, expected: int) -> None:
    assert ui_scale_option.clamp_scale(raw) == expected


# Runs in its own process: Qt teardown inside the test session can hang.
_STYLE_SCRIPT = r"""
import os, sys
from PySide6 import QtCore, QtGui, QtQml

class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    def __init__(self):
        super().__init__()
        self._scale = 100
    def _get(self):
        return self._scale
    uiScale = QtCore.Property(int, fget=_get, notify=uiScaleChanged)

app = QtGui.QGuiApplication(sys.argv)
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(sys.argv[1]), "Gremlin.Style", 1, 0, "Style")
backend = FakeBackend()
engine = QtQml.QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.loadData(b'''
import QtQuick
import QtQuick.Controls
import Gremlin.Style
ApplicationWindow {
    font.pixelSize: Style.fontSize
    property string result: [Style.uiScale, Style.dp(10), Style.dp(1),
        Style.fontSize, _label.font.pixelSize, _button.font.pixelSize].join(",")
    Column {
        Label { id: _label; text: "a" }
        Button { id: _button; text: "b" }
    }
}
''')
window = engine.rootObjects()[0]
for scale in (100, 200, 70):
    backend._scale = scale
    backend.uiScaleChanged.emit()
    print(window.property("result"))
sys.stdout.flush()
os._exit(0)
"""


def test_style_follows_backend_live() -> None:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, "-c", _STYLE_SCRIPT, str(QML_DIR / "Style.qml")],
        capture_output=True, text=True, timeout=60, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [
        "100,10,1,15,15,15",
        "200,20,2,30,30,30",
        "70,7,1,11,11,11",
    ]
