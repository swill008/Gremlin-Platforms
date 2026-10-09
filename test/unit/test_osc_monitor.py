# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The OSC Monitor (D-09-OSC-MONITOR): gremlin.osc_traffic keeps the last 200
messages and hands each to listeners on the main thread; OscMonitorModel
shows them with Pause, Clear, a filter and Show outgoing, holds OSC's port
open while active; "Add as input…" on a "no input" row opens the OSC Add
window filled in, from the monitor window and from the OSC page.

The window part runs the real QML off-screen in a child process (this file
run as a script), with the real model and traffic module, printing
"RESULT name value"."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import threading
import time

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_HARNESS = r"""
import QtQuick
import QtQuick.Controls
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

    OscDevice {
        id: _osc
        objectName: "oscPage"
        anchors.fill: parent
    }

    function prefill(s) { return _osc.openAddWith(s) }
}
"""


class FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def hold_open(self, token: str) -> None:
        self.calls.append(("hold", token))

    def release_open(self, token: str) -> None:
        self.calls.append(("release", token))


# -- in process ---------------------------------------------------------


def _app() -> object:
    from PySide6 import QtCore

    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def _pump(until: object, limit: float = 2.0) -> None:
    from PySide6 import QtCore

    end = time.monotonic() + limit
    while not until() and time.monotonic() < end:  # type: ignore[operator]
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.005)


def test_traffic_keeps_200_and_listeners_run_on_main_thread() -> None:
    from gremlin import osc_traffic

    _app()
    osc_traffic.clear()
    for i in range(250):
        osc_traffic.note("in", f"/a/{i}", [i], ("10.0.0.2", 9000), [])
    kept = osc_traffic.recent()
    assert len(kept) == 200
    assert kept[0]["address"] == "/a/50" and kept[-1]["address"] == "/a/249"
    assert kept[-1]["peer"] == "10.0.0.2:9000"

    got: list[tuple[str, bool]] = []

    def listener(entry: dict) -> None:
        main = threading.current_thread() is threading.main_thread()
        got.append((entry["address"], main))

    osc_traffic.add_listener(listener)
    try:
        worker = threading.Thread(
            target=osc_traffic.note, args=("out", "/fb/1", [0.5], None, None)
        )
        worker.start()
        worker.join(2)
        _pump(lambda: got)
    finally:
        osc_traffic.remove_listener(listener)
        osc_traffic.clear()
    assert got == [("/fb/1", True)]


def _rows(model: object) -> list[dict]:
    from PySide6 import QtCore

    out = []
    for r in range(model.rowCount()):  # type: ignore[attr-defined]
        index = model.index(r, 0)  # type: ignore[attr-defined]
        out.append({
            bytes(name.data()).decode(): model.data(  # type: ignore[attr-defined]
                index, role
            )
            for role, name in model.roleNames().items()  # type: ignore[attr-defined]
        })
    _ = QtCore
    return out


def test_model_notes_filter_pause_clear_outgoing_and_hold_open(
    monkeypatch,  # noqa: ANN001
) -> None:
    from gremlin import osc_traffic
    from gremlin.ui import osc_monitor_model as mm

    _app()
    runtime = FakeRuntime()
    monkeypatch.setattr(mm, "_runtime", lambda: runtime)
    osc_traffic.clear()
    osc_traffic.note("in", "/old", [1], ("h", 1), ["OSC Button 1"])
    model = mm.OscMonitorModel()
    model.active = True
    assert runtime.calls == [("hold", model._token)]
    assert [r["address"] for r in _rows(model)] == ["/old"]

    osc_traffic.note("in", "/fader/1", [0.25], ("10.0.0.5", 8000), [])
    osc_traffic.note("out", "/light/1", [1.0], ("10.0.0.5", 9000), None)
    _pump(lambda: model.rowCount() == 3)
    rows = _rows(model)
    assert [r["direction"] for r in rows] == ["in", "in", "out"]
    assert rows[0]["matched"] == "OSC Button 1" and rows[0]["noInput"] is False
    assert rows[1]["matched"] == "no input" and rows[1]["noInput"] is True
    assert rows[1]["values"] == "0.25" and rows[1]["peer"] == "10.0.0.5:8000"
    assert rows[2]["matched"] == "" and rows[2]["noInput"] is False

    model.showOutgoing = False
    assert [r["address"] for r in _rows(model)] == ["/old", "/fader/1"]
    model.showOutgoing = True
    model.filterText = "FADER"
    assert [r["address"] for r in _rows(model)] == ["/fader/1"]
    assert model.count == 1
    model.filterText = ""

    model.paused = True
    osc_traffic.note("in", "/while/paused", [], None, [])
    _pump(lambda: False, 0.1)
    assert model.rowCount() == 3
    model.paused = False

    model.clear()
    assert model.rowCount() == 0 and osc_traffic.recent() == []

    model.active = False
    assert runtime.calls[-1] == ("release", model._token)
    osc_traffic.note("in", "/after/close", [], None, [])
    _pump(lambda: False, 0.1)
    assert model.rowCount() == 0
    osc_traffic.clear()


def test_add_settings_for_no_input_rows_only(monkeypatch) -> None:  # noqa: ANN001
    from gremlin import osc_traffic
    from gremlin.ui import osc_monitor_model as mm

    _app()
    monkeypatch.setattr(mm, "_runtime", lambda: None)
    osc_traffic.clear()
    osc_traffic.note("in", "/fader/2", [-0.5], None, [])
    osc_traffic.note("in", "/btn/3", [1], None, [])
    osc_traffic.note("in", "/scene", ["go"], None, [])
    osc_traffic.note("in", "/known", [1], None, ["OSC Button 2"])
    model = mm.OscMonitorModel()
    model.active = True
    try:
        axis = model.addSettings(0)
        assert axis["address"] == "/fader/2"
        assert axis["mode"] == "axis" and axis["range_min"] == -1.0
        assert axis["values"] == "-0.5"
        button = model.addSettings(1)
        assert button["mode"] == "button" and button["cmd_mode"] == "message"
        text = model.addSettings(2)
        assert text["cmd_mode"] == "data" and text["data"] == ["go"]
        assert model.addSettings(3) == {}
        assert model.addSettings(99) == {}
    finally:
        model.active = False
        osc_traffic.clear()


def test_hover_text_has_the_whole_row() -> None:
    from gremlin.ui import osc_monitor_model as mm

    address = "/custom-variable/gremlin_mode_with_a_long_name/value"
    out = mm.hover_text({"direction": "out", "address": address,
                         "args": ["Flight"], "peer": "127.0.0.1:12321"})
    assert out.splitlines() == [address, "Values: Flight", "To: 127.0.0.1:12321"]
    got = mm.hover_text({"direction": "in", "address": "/x", "args": [3],
                         "peer": "10.0.0.9:8000", "matched": []})
    assert got.splitlines() == ["/x", "Values: 3", "From: 10.0.0.9:8000",
                                f"Input: {mm.NO_INPUT}"]


# -- the windows, off-screen in a child process ----------------------------


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

    from gremlin import osc_traffic
    from gremlin.ui import osc_monitor_model as mm

    runtime = FakeRuntime()
    mm._runtime = lambda: runtime  # type: ignore[assignment]

    calls: list[list[object]] = []

    def _plain(value: object) -> object:
        if isinstance(value, QtQml.QJSValue):
            value = value.toVariant()
        return value

    def record(*args: object) -> None:
        calls.append([_plain(a) for a in args])

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
            pass

    class WindowPlacement(QtCore.QObject):
        @QtCore.Slot("QVariant", str, int, int)
        def restoreTool(self, host: object, name: str, w: int, h: int) -> None:
            pass

        @QtCore.Slot("QVariant", str)
        def saveTool(self, host: object, name: str) -> None:
            pass

    class OscDeviceManagementModel(QtCore.QAbstractListModel):
        listenChanged = QtCore.Signal()
        listenBound = QtCore.Signal(int)
        commandCaptured = QtCore.Signal(str, str)

        def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
            return 0

        def data(self, index: QtCore.QModelIndex, role: int = 0) -> object:
            return None

        @QtCore.Slot(int, result=QtCore.QObject)
        def inputIdentifier(self, index: int) -> QtCore.QObject | None:
            return None

        @QtCore.Slot("QVariant", result=bool)
        def createConfiguredInput(self, settings: object) -> bool:
            record("createConfiguredInput", settings)
            return True

        @QtCore.Slot("QVariant")
        def setCaptureSettings(self, settings: object) -> None:
            pass

        listening = QtCore.Property(bool, fget=lambda self: False, notify=listenChanged)

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    stand_ins = (OscDeviceManagementModel, OscSettingsInfo, OscBulkCapture, ActionNames)
    for cls in stand_ins:
        QtQml.qmlRegisterType(cls, "Gremlin.Device", 1, 0, cls.__name__)
    QtQml.qmlRegisterType(WindowPlacement, "Gremlin.UI", 1, 0, "WindowPlacement")
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    sig = FakeSignal()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("signal", sig)
    engine.rootContext().setContextProperty("uiState", None)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))

    def report(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    def finish() -> None:
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)

    def items(quick: QtQuick.QQuickWindow) -> list[QtQuick.QQuickItem]:
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

    def find(quick: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
        for item in items(quick):
            if item.objectName() == name and item.isVisible():
                return item
        return None

    def click(quick: QtQuick.QQuickWindow, name: str) -> None:
        item = find(quick, name)
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

    def as_quick(obj: QtCore.QObject) -> QtQuick.QQuickWindow:
        pointer = shiboken6.getCppPointer(obj)[0]
        return shiboken6.wrapInstance(pointer, QtQuick.QQuickWindow)

    # 1. The monitor window: open holds the port; notes reach the list.
    osc_traffic.clear()
    osc_traffic.note("in", "/known", [1], ("10.0.0.9", 8000), ["OSC Button 1"])
    engine.load(QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "WindowOscMonitor.qml")))
    roots = engine.rootObjects()
    if not roots:
        print("ERROR monitor did not load", flush=True)
        finish()
        return
    mon = roots[-1]
    mq = as_quick(mon)
    mq.show()
    QtTest.QTest.qWait(300)
    report("hold-on-open", [c[0] for c in runtime.calls])
    osc_traffic.note("in", "/fader/3", [0.25], ("10.0.0.9", 8000), [])
    osc_traffic.note("out", "/light/1", [1.0], ("10.0.0.9", 9000), None)
    QtTest.QTest.qWait(300)
    lst = find(mq, "oscMonitorList")
    report("list-count", lst.property("count") if lst else None)

    # Filter through the shared search box.
    box = find(mq, "oscMonitorFilter")
    if box is not None:
        box.setProperty("text", "fader")
        QtTest.QTest.qWait(100)
        report("filtered-count", lst.property("count") if lst else None)
        box.setProperty("text", "")
        QtTest.QTest.qWait(100)

    # 2. Add as input… on the "no input" row: the Add window, filled in.
    click(mq, "oscMonitorAddRow1")
    QtTest.QTest.qWait(200)
    cmd = find(mq, "oscCmd")
    report("monitor-add-address", cmd.property("text") if cmd else None)
    axis = find(mq, "oscModeAxis")
    report("monitor-add-axis", bool(axis and axis.property("checked")))
    click(mq, "oscOk")
    QtTest.QTest.qWait(150)
    last = [c for c in calls if c[0] == "createConfiguredInput"]
    report("monitor-add-call", last[-1][1] if last else None)

    # 2b. Column heads keep to their own widths; hovering a row shows the
    # whole message, the long address in full.
    heads = [find(mq, f"oscMonitorHead{i}") for i in range(6)]
    report("head-geometry", [
        None if h is None else [h.mapToScene(QtCore.QPointF(0, 0)).x(), h.width(),
                                h.property("implicitWidth")]
        for h in heads
    ])
    long_address = "/custom-variable/gremlin_mode_with_a_long_name/value"
    osc_traffic.note("out", long_address, ["Flight"], ("127.0.0.1", 12321), None)
    QtTest.QTest.qWait(300)
    count = lst.property("count") if lst else 0
    cell = find(mq, f"oscMonitorAddress{count - 1}")
    tip_texts: list[str] = []
    if cell is not None:
        point = cell.mapToScene(QtCore.QPointF(cell.width() / 2, cell.height() / 2))
        QtTest.QTest.mouseMove(mq, point.toPoint())
        QtTest.QTest.qWait(50)
        QtTest.QTest.mouseMove(mq, point.toPoint() + QtCore.QPoint(2, 0))
        QtTest.QTest.qWait(1500)
        for item in items(mq):
            text = item.property("text")
            if (item.isVisible() and isinstance(text, str) and long_address in text
                    and "\n" in text):
                tip_texts.append(text)
    report("hover-text", tip_texts)
    report("long-address", long_address)

    # 3. Close releases the port.
    mq.close()
    QtTest.QTest.qWait(200)
    report("release-on-close", [c[0] for c in runtime.calls])

    # 4. The OSC page: openAddWith fills its Add window; Monitor button exists.
    engine.loadData(
        _HARNESS.encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "OscMonitorHarness.qml")),
    )
    page = engine.rootObjects()[-1]
    pq = as_quick(page)
    QtTest.QTest.qWait(300)
    report("monitor-button", find(pq, "oscMonitor") is not None)
    ok = QtCore.QMetaObject.invokeMethod(
        page, "prefill", QtCore.Qt.ConnectionType.DirectConnection,
        QtCore.Q_RETURN_ARG("QVariant"),
        QtCore.Q_ARG("QVariant", mm.add_settings(
            {"address": "/knob/1", "args": [0.4]}
        )),
    )
    QtTest.QTest.qWait(200)
    report("page-prefill-returned", _plain(ok))
    cmd = find(pq, "oscCmd")
    report("page-add-address", cmd.property("text") if cmd else None)
    axis = find(pq, "oscModeAxis")
    report("page-add-axis", bool(axis and axis.property("checked")))
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
    got: dict[str, object] = {}
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            got[name] = json.loads(value)
    errors = [line for line in lines if line.startswith("ERROR")]
    warns = [
        line for line in lines
        if line.startswith("WARN") and ("Osc" in line or "Monitor" in line)
    ]
    return got, errors + warns


def test_monitor_window_and_osc_page_add_as_input(tmp_path: pathlib.Path) -> None:
    got, problems = _run(tmp_path)
    assert problems == [], problems
    assert got["hold-on-open"] == ["hold"]
    assert got["list-count"] == 3
    assert got["filtered-count"] == 1
    assert got["monitor-add-address"] == "/fader/3"
    assert got["monitor-add-axis"] is True
    added = got["monitor-add-call"]
    assert isinstance(added, dict)
    assert added["address"] == "/fader/3" and added["mode"] == "axis"
    assert got["release-on-close"] == ["hold", "release"]
    heads = got["head-geometry"]
    assert isinstance(heads, list) and None not in heads, heads
    for x, width, implicit in heads:
        assert implicit <= width + 0.5, heads  # whole heading fits its column
    for (x, width, _), (nx, _, _) in zip(heads, heads[1:]):
        assert x + width <= nx + 0.5, heads  # never runs into the next
    tips = got["hover-text"]
    assert tips, "no hover text showing the full address"
    assert any(t.splitlines()[0] == got["long-address"] and "To: 127.0.0.1:12321" in t
               and "Values: Flight" in t for t in tips), tips
    assert got["monitor-button"] is True
    assert got["page-prefill-returned"] is True
    assert got["page-add-address"] == "/knob/1"
    assert got["page-add-axis"] is True


if __name__ == "__main__":
    _smoke()
