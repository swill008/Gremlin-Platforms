# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Encoder inputs in the OSC Add window and list model (D-09-OSC-ENCODER).

The Add window's Action mode has "Encoder": Format (Auto / 1 = clockwise,
0 = counter-clockwise / +n and -n), Output (Axis / Pulses clockwise / Pulses
counter-clockwise), Step size for an axis and the release delay for pulses
all reach the model. A locked input keeps its kind: an encoder axis is an
axis, encoder pulses are a button. Import's E suffix adds an encoder axis
with Auto format, and the Import help says so.

The QML part runs the real windows off-screen in a child process (this file
run as a script) against a stand-in model, printing "RESULT name value"."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from gremlin.ui.osc_device_model import OscDeviceManagementModel as Model

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_HARNESS = r"""
import QtQuick
import QtQuick.Controls
import Gremlin.Device
import Gremlin.Style

ApplicationWindow {
    id: _win
    width: 1200
    height: 900
    visible: true
    property var lastAccepted: null

    OscDeviceManagementModel { id: _model; objectName: "fakeModel" }

    OscAddDialog {
        id: _add
        objectName: "addDialog"
        deviceModel: _model
        onAccepted: (s) => _win.lastAccepted = s
    }

    OscImportDialog { id: _import; objectName: "importDialog" }
}
"""


def _smoke() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
    os.environ["QT_FILE_SELECTORS"] = "Universal"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    sys.path.insert(0, str(_ROOT))

    import shiboken6
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest

    calls: list[list[object]] = []

    def plain(value: object) -> object:
        if isinstance(value, QtQml.QJSValue):
            value = value.toVariant()
        return value

    class FakeBackend(QtCore.QObject):
        @QtCore.Slot(str)
        def pauseInputHighlighting(self, who: str) -> None:
            pass

        @QtCore.Slot(str)
        def resumeInputHighlighting(self, who: str) -> None:
            pass

    class OscSettingsInfo(QtCore.QObject):
        @QtCore.Slot(result=str)
        def summary(self) -> str:
            return ""

    class OscBulkCapture(QtCore.QObject):
        @QtCore.Slot("QVariant", "QVariant")
        def start(self, model: object, settings: object) -> None:
            pass

    class OscDeviceManagementModel(QtCore.QObject):
        listenChanged = QtCore.Signal()
        commandCaptured = QtCore.Signal(str, str)

        @QtCore.Slot(str, "QVariantMap", result=str)
        def updateInputSettings(self, uid: str, settings: object) -> str:
            calls.append(["updateInputSettings", uid, plain(settings)])
            return ""

        @QtCore.Slot("QVariant")
        def setCaptureSettings(self, settings: object) -> None:
            pass

        @QtCore.Slot()
        def cancelListen(self) -> None:
            pass

        listening = QtCore.Property(bool, fget=lambda self: False, notify=listenChanged)

    sys.stdout.reconfigure(encoding="utf-8")
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    for cls in (OscDeviceManagementModel, OscSettingsInfo, OscBulkCapture):
        QtQml.qmlRegisterType(cls, "Gremlin.Device", 1, 0, cls.__name__)
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "OscEncHarness.qml"))
    engine.loadData(_HARNESS.encode("utf-8"), here)

    def report(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    def finish() -> None:
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)

    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        finish()
        return
    win = roots[0]
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    QtTest.QTest.qWait(200)
    dialog = win.findChild(QtCore.QObject, "addDialog")
    importer = win.findChild(QtCore.QObject, "importDialog")

    def call(obj: QtCore.QObject, expr: str) -> object:
        result = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, expr).evaluate()
        QtTest.QTest.qWait(150)
        return plain(result[0] if isinstance(result, tuple) else result)

    def items() -> list[QtQuick.QQuickItem]:
        top = quick.contentItem()
        while top.parentItem() is not None:
            top = top.parentItem()
        out: list[QtQuick.QQuickItem] = []
        stack = [top]
        while stack:
            item = stack.pop()
            out.append(item)
            stack.extend(item.childItems())
        return out

    def find(name: str) -> QtQuick.QQuickItem | None:
        for item in items():
            if item.objectName() == name and item.isVisible():
                return item
        return None

    def click(name: str) -> None:
        item = find(name)
        if item is None:
            print(f"ERROR missing {name}", flush=True)
            return
        point = item.mapToScene(
            QtCore.QPointF(item.width() / 2, item.height() / 2)
        ).toPoint()
        QtTest.QTest.mouseClick(
            quick, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier, point,
        )
        QtTest.QTest.qWait(150)

    def set_text(name: str, text: str) -> None:
        item = find(name)
        if item is None:
            print(f"ERROR missing {name}", flush=True)
            return
        item.setProperty("text", text)
        QtTest.QTest.qWait(50)

    def shown(*names: str) -> list[bool]:
        return [find(n) is not None for n in names]

    def enabled(*names: str) -> list[object]:
        return [
            bool(find(n).property("enabled")) if find(n) else None for n in names
        ]

    rows = ("oscEncoderFormatRow", "oscEncoderOutputRow", "oscEncoderStepRow",
            "oscEncoderDelayRow")
    outs = ("oscEncOutAxis", "oscEncOutCw", "oscEncOutCcw")

    # 1. New encoder driving an axis, +n/-n format, step 0.1.
    call(dialog, "resetFields(), open()")
    report("before-encoder", shown(*rows))
    set_text("oscCmd", "/knob/1")
    click("oscModeEncoder")
    report("axis-rows", shown(*rows))
    report("format-texts", [
        find(n).property("text") if find(n) else None
        for n in ("oscEncFormatAuto", "oscEncFormatDirection", "oscEncFormatSigned")
    ])
    report("output-texts", [
        find(n).property("text") if find(n) else None for n in outs
    ])
    click("oscEncFormatSigned")
    set_text("oscEncStep", "0")
    report("bad-step-ok", enabled("oscOk"))
    set_text("oscEncStep", "0.1")
    click("oscOk")
    report("add-axis", plain(win.property("lastAccepted")))

    # 2. New encoder giving counter-clockwise pulses with a 250 ms release.
    win.setProperty("lastAccepted", None)
    call(dialog, "resetFields(), open()")
    set_text("oscCmd", "/knob/2")
    click("oscModeEncoder")
    click("oscEncOutCcw")
    report("pulse-rows", shown(*rows))
    set_text("oscEncDelay", "250")
    click("oscOk")
    report("add-pulse", plain(win.property("lastAccepted")))

    # 3. Edit a locked encoder axis: pulses are greyed, it saves its settings.
    calls.clear()
    call(dialog, (
        'openForEdit("u1", {address: "/knob/1", locked: true, mode: "encoder", '
        'enc_format: "direction", enc_step: 0.2, enc_output: "axis", '
        'cmd_mode: "message", data: [], source: 0})'
    ))
    report("locked-axis-modes", enabled(
        "oscModeChange", "oscModeButton", "oscModeAxis", "oscModeEncoder"))
    report("locked-axis-outs", enabled(*outs))
    report("locked-axis-step", find("oscEncStep").property("text")
           if find("oscEncStep") else None)
    report("locked-axis-format", bool(find("oscEncFormatDirection")
           and find("oscEncFormatDirection").property("checked")))
    click("oscOk")
    report("edit-saved", calls[-1][1:] if calls else None)

    # 4. A locked button switched to Encoder gets pulses, never the axis.
    call(dialog, (
        'openForEdit("u2", {address: "/btn/1", locked: true, mode: "button", '
        'cmd_mode: "message", data: [], source: 0})'
    ))
    click("oscModeEncoder")
    report("locked-button-outs", enabled(*outs))
    report("locked-button-output", call(dialog, "encoderOutput()"))
    call(dialog, "close()")

    # 5. Import help names E as an encoder.
    call(importer, "open()")
    help_item = find("oscImportHelp")
    report("import-help", help_item.property("text") if help_item else None)
    finish()


def _run(tmp_path: pathlib.Path) -> tuple[dict[str, Any], list[str]]:
    result = subprocess.run(
        [sys.executable, __file__],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    got: dict[str, Any] = {}
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            got[name] = json.loads(value)
    problems = [
        line for line in lines
        if line.startswith("ERROR") or (line.startswith("WARN") and "Osc" in line)
    ]
    return got, problems


def test_add_window_encoder_settings_reach_the_model(tmp_path: pathlib.Path) -> None:
    got, problems = _run(tmp_path)
    assert problems == [], problems

    assert got["before-encoder"] == [False, False, False, False]
    assert got["axis-rows"] == [True, True, True, False]
    assert got["format-texts"] == [
        "Auto", "1 = clockwise, 0 = counter-clockwise", "+n and \u2212n"]
    assert got["output-texts"] == [
        "Axis", "Pulses clockwise", "Pulses counter-clockwise"]
    assert got["bad-step-ok"] == [False]
    add = got["add-axis"]
    assert add["address"] == "/knob/1" and add["mode"] == "encoder"
    assert add["enc_format"] == "signed" and add["enc_output"] == "axis"
    assert add["enc_step"] == pytest.approx(0.1)

    assert got["pulse-rows"] == [True, True, False, True]
    pulse = got["add-pulse"]
    assert pulse["mode"] == "encoder" and pulse["enc_output"] == "pulse_ccw"
    assert pulse["enc_format"] == "auto" and pulse["delay_ms"] == 250

    # Encoder axis counts as an axis: only Axis / Encoder modes, only Axis output.
    assert got["locked-axis-modes"] == [False, False, True, True]
    assert got["locked-axis-outs"] == [True, False, False]
    assert got["locked-axis-step"] == "0.2"
    assert got["locked-axis-format"] is True
    uid, saved = got["edit-saved"]
    assert uid == "u1" and saved["mode"] == "encoder"
    assert saved["enc_format"] == "direction" and saved["enc_output"] == "axis"
    assert saved["enc_step"] == pytest.approx(0.2)

    # Encoder pulses count as a button.
    assert got["locked-button-outs"] == [False, True, True]
    assert got["locked-button-output"] == "pulse_cw"

    help_text = got["import-help"]
    assert "E: encoder" in help_text and "not supported" not in help_text


# -- the list model --------------------------------------------------------


@pytest.fixture
def model(qapp: object) -> Iterator[Model]:
    from gremlin import shared_state
    from gremlin.osc import OscDevice
    from gremlin.ui.osc_device_model import OscDeviceManagementModel

    OscDevice().rows.reset()
    saved = shared_state.current_profile
    shared_state.current_profile = None
    yield OscDeviceManagementModel()
    OscDevice().rows.reset()
    shared_state.current_profile = saved


def _rows() -> list[Any]:
    from gremlin.osc import OscDevice

    return list(OscDevice().rows.rows())


def test_import_e_adds_an_encoder_axis_with_auto_format(model: Model) -> None:
    from gremlin.types import InputType

    result = model.importInputs("/knob E\n/wheel, e")
    assert result == "Added 2, skipped 0"
    for row in _rows():
        assert row.input_type == InputType.JoystickAxis
        assert (row.mode, row.enc_format, row.enc_output) == ("encoder", "auto", "axis")


def test_encoder_settings_create_update_and_read_back(model: Model) -> None:
    from gremlin.types import InputType

    assert model.createConfiguredInput({
        "address": "/knob", "mode": "encoder", "enc_format": "signed",
        "enc_step": 0.1, "enc_output": "pulse_cw", "delay_ms": 120,
    }) is True
    [row] = _rows()
    assert row.input_type == InputType.JoystickButton
    settings = model.inputSettings(row.uid)
    assert settings["mode"] == "encoder"
    assert (settings["enc_format"], settings["enc_output"]) == ("signed", "pulse_cw")
    assert settings["enc_step"] == pytest.approx(0.1)

    # Pulses -> axis moves it to an axis while nothing is mapped on it.
    assert model.updateInputSettings(row.uid, {"enc_output": "axis"}) == ""
    [row] = _rows()
    assert row.input_type == InputType.JoystickAxis
    assert model.inputSettings(row.uid)["enc_output"] == "axis"


def test_encoder_kind_change_is_refused_when_locked(
    model: Model, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import osc_device_model as odm

    assert model.createConfiguredInput(
        {"address": "/knob", "mode": "encoder", "enc_output": "axis"}) is True
    [row] = _rows()
    monkeypatch.setattr(odm, "has_actions", lambda r: True)
    # Encoder axis -> plain axis keeps the kind; -> pulses changes it.
    assert model.updateInputSettings(row.uid, {"enc_output": "pulse_ccw"}) == \
        odm.TYPE_LOCKED
    assert model.updateInputSettings(row.uid, {"mode": "button"}) == odm.TYPE_LOCKED
    assert model.updateInputSettings(row.uid, {"mode": "axis"}) == ""


def test_normalize_settings_cleans_encoder_fields() -> None:
    from gremlin.ui.osc_device_model import normalize_settings

    got = normalize_settings({"mode": "Encoder", "enc_format": "x",
                              "enc_step": "-1", "enc_output": "PULSE_CCW"})
    assert got == {"mode": "encoder", "enc_format": "auto", "enc_step": 0.05,
                   "enc_output": "pulse_ccw"}


if __name__ == "__main__":
    _smoke()
