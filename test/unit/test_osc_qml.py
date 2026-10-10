# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page's Add / Import windows (D-09-OSC-INPUT, D-09-OSC-FAULTS):
the Add window sends all its settings (mode, Message only / + data, source
P1..Pn, axis range, trigger + delay) to createConfiguredInput; Listen and
Bulk capture pass the same settings; the Listening box's button is "Stop";
Edit Settings… opens an input again, its type locked while it has actions;
Import's help names the suffixes and its text reaches the model.

The windows are hosted as qml/OscPage.qml hosts them (09 S129, S135: Add…,
Import… and Edit Settings… are right-click menu rows now, no footer or
pencil menu): openAdd() is resetFields() + open(), Edit Settings… is
openForEdit(uid, inputSettings(uid)), OK goes to createConfiguredInput and
Import's OK to importInputs. The page's own parts (Delete asks first,
Change Address… shows the model's error, Import's result on the message
line) are driven on the real page, from its right-click menu, in
osc_page_companion_smoke.py (test_osc_page_companion.py).

The real QML runs off-screen in a child process (this file run as a script)
against a stand-in model that records every call, printing "RESULT name value".
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

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

    QtObject {
        id: bsi
        property var icons: ({"edit": "E", "remove": "X"})
    }

    OscDeviceManagementModel { id: _devices }

    // As OscPage.qml hosts and opens them.
    OscAddDialog {
        id: _addDialog
        objectName: "oscAdd"
        deviceModel: _devices
        onAccepted: (settings) => _devices.createConfiguredInput(settings)
    }

    OscImportDialog {
        id: _importDialog
        onAccepted: (text) => _devices.importInputs(text)
    }

    function openAdd() {
        _addDialog.resetFields()
        _addDialog.open()
        return true
    }

    function editSettings(uid) {
        _addDialog.openForEdit(uid, _devices.inputSettings(uid))
        return true
    }

    function openImport() {
        _importDialog.resetFields()
        _importDialog.open()
        return true
    }
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

    def record(*args: object) -> None:
        calls.append([_plain(a) for a in args])

    def _plain(value: object) -> object:
        if isinstance(value, QtQml.QJSValue):
            value = value.toVariant()
        return value

    class FakeBackend(QtCore.QObject):
        uiScaleChanged = QtCore.Signal()
        gremlinActiveChanged = QtCore.Signal()
        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)
        gremlinActive = QtCore.Property(
            bool, fget=lambda self: False, notify=gremlinActiveChanged
        )

        @QtCore.Slot(str)
        def pauseInputHighlighting(self, who: str) -> None:
            pass

        @QtCore.Slot(str)
        def resumeInputHighlighting(self, who: str) -> None:
            pass

    class FakeSignal(QtCore.QObject):
        inputItemChanged = QtCore.Signal(int)

    class InputIdentifier(QtCore.QObject):
        pass

    class ActionNames(QtCore.QObject):
        @QtCore.Slot("QVariant", int, str)
        def setOnModel(self, model: object, index: int, name: str) -> None:
            pass

        @QtCore.Slot("QVariant", int, result=str)
        def getOnModel(self, model: object, index: int) -> str:
            return ""

    class OscSettingsInfo(QtCore.QObject):
        @QtCore.Slot(result=str)
        def summary(self) -> str:
            return "Listening on port 8001."

    class OscBulkCapture(QtCore.QObject):
        @QtCore.Slot("QVariant", "QVariant")
        def start(self, model: object, settings: object) -> None:
            record("bulkStart", settings)
            model.setListening(True)

    rows = [
        {"uid": "u1", "label": "/fader/1", "name": "Axis 1 - /fader/1"},
        {"uid": "u2", "label": "/btn/1", "name": "Button 1 - /btn/1"},
    ]
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + i: QtCore.QByteArray(n.encode())
        for i, n in enumerate(
            [
                "name",
                "label",
                "uid",
                "actionSequenceCount",
                "actionSequenceDescriptor",
                "actionSequenceDisplayMode",
                "description",
            ],
            start=1,
        )
    }

    class OscDeviceManagementModel(QtCore.QAbstractListModel):
        listenChanged = QtCore.Signal()
        listenBound = QtCore.Signal(int)
        commandCaptured = QtCore.Signal(str, str)

        def __init__(self, parent: QtCore.QObject | None = None) -> None:
            super().__init__(parent)
            self._listening = False
            models.append(self)

        def setListening(self, on: bool) -> None:
            self._listening = on
            self.listenChanged.emit()

        def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
            return len(rows)

        def roleNames(self) -> dict[int, QtCore.QByteArray]:
            return roles

        def data(self, index: QtCore.QModelIndex, role: int = 0) -> object:
            name = bytes(roles.get(role, QtCore.QByteArray()).data()).decode()
            row = rows[index.row()]
            if name in row:
                return row[name]
            return 0 if name == "actionSequenceCount" else ""

        @QtCore.Slot(int, result=QtCore.QObject)
        def inputIdentifier(self, index: int) -> QtCore.QObject:
            return InputIdentifier(self)

        @QtCore.Slot("QVariant", result=bool)
        def createConfiguredInput(self, settings: object) -> bool:
            record("createConfiguredInput", settings)
            return True

        @QtCore.Slot(str, result="QVariant")
        def inputSettings(self, uid: str) -> object:
            record("inputSettings", uid)
            return {
                "address": "/fader/1", "mode": "axis", "cmd_mode": "message",
                "data": [], "source": 1, "range_min": -1.0, "range_max": 1.0,
                "trigger": None, "delay_ms": None, "locked": True,
            }

        @QtCore.Slot(str, "QVariant", result=str)
        def updateInputSettings(self, uid: str, settings: object) -> str:
            record("updateInputSettings", uid, settings)
            return ""

        @QtCore.Slot(str, str, result=str)
        def changeName(self, uid: str, address: str) -> str:
            record("changeName", uid, address)
            if address.startswith("/"):
                return ""
            return "An OSC address must start with /."

        @QtCore.Slot(str, result=str)
        def importInputs(self, text: str) -> str:
            record("importInputs", text)
            return "Added 2, skipped 1."

        @QtCore.Slot(str)
        def deleteInput(self, uid: str) -> None:
            record("deleteInput", uid)

        @QtCore.Slot("QVariant")
        def setCaptureSettings(self, settings: object) -> None:
            record("setCaptureSettings", settings)

        @QtCore.Slot("QVariant")
        def listenForCommand(self, settings: object = None) -> None:
            record("listenForCommand", settings)
            self.setListening(True)

        @QtCore.Slot()
        def cancelListen(self) -> None:
            record("cancelListen")
            self.setListening(False)

        @QtCore.Slot()
        def sortInputs(self) -> None:
            record("sortInputs")

        @QtCore.Slot()
        def clearAllInputs(self) -> None:
            record("clearAllInputs")

        listening = QtCore.Property(
            bool, fget=lambda self: self._listening, notify=listenChanged
        )

    models: list[OscDeviceManagementModel] = []

    sys.stdout.reconfigure(encoding="utf-8")
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    for cls in (
        OscDeviceManagementModel, OscSettingsInfo, OscBulkCapture,
        ActionNames, InputIdentifier,
    ):
        QtQml.qmlRegisterType(cls, "Gremlin.Device", 1, 0, cls.__name__)
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    sig = FakeSignal()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("signal", sig)
    engine.rootContext().setContextProperty("uiState", None)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "OscQmlHarness.qml"))
    engine.loadData(_HARNESS.encode("utf-8"), here)
    roots = engine.rootObjects()

    def report(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    def finish() -> None:
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)

    if not roots:
        print("ERROR window did not load", flush=True)
        finish()
        return
    win = roots[0]
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    quick.requestActivate()
    QtTest.QTest.qWait(300)
    model = models[0]

    def items() -> list[QtQuick.QQuickItem]:
        # Visual tree: Repeater and ListView items have no QObject parent.
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

    def by_text(text: str) -> QtQuick.QQuickItem | None:
        for item in items():
            if (
                item.isVisible()
                and item.metaObject().indexOfProperty("checkable") >= 0
                and item.property("text") == text
            ):
                return item
        return None

    def click_item(item: QtQuick.QQuickItem | None, what: str) -> None:
        if item is None:
            print(f"ERROR missing {what}", flush=True)
            return
        point = item.mapToScene(
            QtCore.QPointF(item.width() / 2, item.height() / 2)
        ).toPoint()
        QtTest.QTest.mouseClick(
            quick, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier, point,
        )
        QtTest.QTest.qWait(150)

    def click(name: str) -> None:
        click_item(find(name), name)

    def click_text(text: str) -> None:
        click_item(by_text(text), text)

    def set_text(name: str, text: str) -> None:
        item = find(name)
        if item is None:
            print(f"ERROR missing {name}", flush=True)
            return
        item.setProperty("text", text)
        QtTest.QTest.qWait(50)

    def last(kind: str) -> object:
        for call in reversed(calls):
            if call[0] == kind:
                return call[1:]
        return None

    def visible(name: str) -> bool:
        return find(name) is not None

    def call(fn: str, *args: object) -> None:
        # The page's own function behind the menu row (OscPage.qml).
        QtCore.QMetaObject.invokeMethod(
            win, fn, QtCore.Qt.ConnectionType.DirectConnection,
            QtCore.Q_RETURN_ARG("QVariant"),
            *[QtCore.Q_ARG("QVariant", a) for a in args],
        )
        QtTest.QTest.qWait(150)

    # 1. Add Inputs › Add…, typed, Axis with a range: the whole map reaches the model.
    call("openAdd")
    set_text("oscCmd", "/fader/2")
    click("oscModeAxis")
    report("range-shown", visible("oscRangeRow"))
    report("source-hidden", not visible("oscSourceRow"))
    set_text("oscRangeMin", "5")
    set_text("oscRangeMax", "2")
    QtTest.QTest.qWait(50)
    ok = find("oscOk")
    report("ok-text", ok.property("text") if ok else None)
    report("ok-disabled-bad-range", bool(ok and not ok.property("enabled")))
    set_text("oscRangeMin", "-2")
    click("oscOk")
    report("add-axis", last("createConfiguredInput"))

    # 2. Listen: same settings go to the model; the box's button is Stop and stops.
    calls.clear()
    call("openAdd")
    click("oscMessageData")
    click("oscListen")
    report("listen-settings", last("listenForCommand"))
    report("listen-capture-settings", last("setCaptureSettings"))
    report("listening", model.listening)
    report("stop-shown", by_text("Stop") is not None)
    click_text("Stop")
    QtTest.QTest.qWait(150)
    report("stopped", [model.listening, last("cancelListen") is not None])

    # A capture with Message + data: the captured values are the data.
    click("oscListen")
    model.commandCaptured.emit("/btn/7", "1, 0.5")
    QtTest.QTest.qWait(200)
    report("capture-add", last("createConfiguredInput"))

    # 3. Bulk capture: the window's settings, P1..Pn from the values.
    calls.clear()
    call("openAdd")
    click("oscModeButton")
    click("oscBulk")
    click("oscListen")
    report("bulk-settings", last("bulkStart"))
    model.commandCaptured.emit("/deck/1", "3, 4, 5")
    QtTest.QTest.qWait(200)
    report("sources", [visible(f"oscSource{i}") for i in range(3)])
    click_text("Stop")
    QtTest.QTest.qWait(150)
    click("oscSource2")
    click("oscTrigger")
    click_text("1/2s")
    click("oscOk")
    report("trigger-add", last("createConfiguredInput"))

    # 4. Edit Settings… (right-click menu): opens with the input's settings.
    calls.clear()
    call("editSettings", "u1")
    report("edit-asked", last("inputSettings"))
    report("edit-range-shown", visible("oscRangeRow"))
    report("edit-locked", [
        bool(find(n).property("enabled")) if find(n) else None
        for n in ("oscModeChange", "oscModeButton", "oscModeAxis")
    ])
    set_text("oscRangeMax", "4")
    click("oscOk")
    report("edit-saved", last("updateInputSettings"))

    # 5. Add Inputs › Import…: help names the suffixes; the text reaches the model.
    call("openImport")
    help_item = find("oscImportHelp")
    report("import-help", help_item.property("text") if help_item else None)
    set_text("oscImportText", "/a A\n/b, BNP")
    click("oscImportOk")
    report("import-call", last("importInputs"))
    finish()


def _run(tmp_path: pathlib.Path) -> tuple[dict[str, object], list[str]]:
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
    got = {}
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            got[name] = json.loads(value)
    errors = [line for line in lines if line.startswith("ERROR")]
    warns = [
        line for line in lines
        if line.startswith("WARN") and "Osc" in line
    ]
    return got, errors + warns


def test_osc_add_listen_edit_and_import_reach_the_model(tmp_path: pathlib.Path) -> None:
    got, problems = _run(tmp_path)
    assert problems == [], problems

    assert got["range-shown"] is True
    assert got["source-hidden"] is True
    assert got["ok-text"] == "OK"
    assert got["ok-disabled-bad-range"] is True
    (add,) = got["add-axis"]
    assert add["address"] == "/fader/2"
    assert add["mode"] == "axis"
    assert add["cmd_mode"] == "message"
    assert add["range_min"] == -2 and add["range_max"] == 2
    assert add["source"] == 0

    (listen,) = got["listen-settings"]
    assert listen["cmd_mode"] == "data" and listen["mode"] == "button"
    assert got["listen-capture-settings"] is not None
    assert got["listening"] is True
    assert got["stop-shown"] is True
    assert got["stopped"] == [False, True]
    (captured,) = got["capture-add"]
    assert captured["address"] == "/btn/7"
    assert captured["cmd_mode"] == "data"
    assert captured["data"] == ["1", "0.5"]

    (bulk,) = got["bulk-settings"]
    assert bulk["mode"] == "button"
    assert got["sources"] == [True, True, True]
    (trig,) = got["trigger-add"]
    assert trig["address"] == "/deck/1"
    assert trig["source"] == 2
    assert trig["trigger"] is True and trig["delay_ms"] == 500

    (asked,) = got["edit-asked"]
    assert asked == "u1"
    assert got["edit-range-shown"] is True
    # An axis with actions stays an axis: Change and Button are greyed.
    assert got["edit-locked"] == [False, False, True]
    uid, edited = got["edit-saved"]
    assert uid == asked
    assert edited["mode"] == "axis" and edited["range_max"] == 4
    assert edited["range_min"] == -1 and edited["source"] == 1

    help_text = got["import-help"]
    for piece in ("A: axis", "BNP", "C: change",
                  "E: encoder, added as an encoder axis",
                  "unknown suffix", "space or a comma"):
        assert piece in help_text, piece
    assert got["import-call"] == ["/a A\n/b, BNP"]


if __name__ == "__main__":
    _smoke()
