# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Opens qml/WindowScreenSaverMode.qml off-screen with the real
ScreenSaverModeModel and the stand-ins from ssm_ui_fakes.py, works its
controls and prints what happened as JSON, for test_ssm_ui.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import ssm_ui_fakes  # noqa: E402

manager, calls = ssm_ui_fakes.install()

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import gremlin.ui.device_names  # noqa: E402, F401  (Gremlin.Device)
import gremlin.ui.screen_saver_mode_model as ssm_model  # noqa: E402
import gremlin.ui.window_placement  # noqa: E402, F401  (Gremlin.UI)
from gremlin.config import Configuration  # noqa: E402

app = QtGui.QGuiApplication([sys.argv[0]])


class Backend(QtCore.QObject):
    """Style's sizes come from here; without it they are all 0."""

    uiScaleChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)


engine = QtQml.QQmlEngine()
backend = Backend()
engine.rootContext().setContextProperty("backend", backend)
engine.addImportPath(str(ROOT / "theme"))
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
    "Gremlin.Style",
    1,
    0,
    "Style",
)
url = QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "WindowScreenSaverMode.qml"))
component = QtQml.QQmlComponent(engine, url)
win = component.create()
if win is None:
    print(json.dumps({"errors": [e.toString() for e in component.errors()]}))
    smoke_exit(1)
warnings: list[str] = []
QtCore.qInstallMessageHandler(
    lambda kind, _ctx, text: (
        None if kind == QtCore.QtMsgType.QtDebugMsg else warnings.append(text)
    )
)
win.show()
context = QtQml.QQmlEngine.contextForObject(win)


def ev(code: str) -> object:
    value, _ = QtQml.QQmlExpression(context, win, code).evaluate()
    return value


def settle(ms: int = 150) -> None:
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


def until(check, limit: float = 5.0) -> bool:  # noqa: ANN001
    end = time.monotonic() + limit
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        if check():
            return True
    return False


def child(name: str) -> QtCore.QObject:
    found = win.findChild(QtCore.QObject, name)
    assert found is not None, name
    return found


def prop(name: str, key: str) -> object:
    return child(name).property(key)


def emit(name: str, sig: str) -> None:
    QtCore.QMetaObject.invokeMethod(child(name), sig)


def toggle(name: str, on: bool) -> None:
    obj = child(name)
    obj.setProperty("checked", on)
    QtCore.QMetaObject.invokeMethod(obj, "toggled")


def cfg(name: str) -> object:
    return Configuration().value(ssm_model.SECTION, ssm_model.GROUP, name)


def texts() -> dict:
    out = {}
    for name in (
        "ssmProblemText",
        "ssmSaverWindowsWait",
        "ssmOffWindowsWait",
        "ssmSaverProblem",
        "ssmOffProblem",
        "ssmOrderWarning",
    ):
        out[name] = str(prop(name, "text"))
        out[name + "Visible"] = bool(prop(name, "visible"))
    out["statusRows"] = status_rows()
    return out


def status_rows() -> list[dict]:
    """The Status grid as shown: label, value, detail (and value colour)."""
    rows = []
    n = 0
    root = win.contentItem()

    def one(name: str) -> QtQuick.QQuickItem | None:
        found = _items_named(root, name)
        return found[0] if found else None

    while one(f"ssmStatusLabel_{n}") is not None:
        label, value, detail = (
            one(f"ssmStatusLabel_{n}"),
            one(f"ssmStatusValue_{n}"),
            one(f"ssmStatusDetail_{n}"),
        )
        rows.append(
            {
                "label": str(label.property("text")),
                "value": str(value.property("text")) if value else "",
                "detail": str(detail.property("text")) if detail else "",
                "color": value.property("color").name() if value else "",
            }
        )
        n += 1
    return rows


def status_blob() -> str:
    return " | ".join(f"{r['label']} {r['value']}{r['detail']}" for r in status_rows())


def _items_named(item: QtQuick.QQuickItem, name: str) -> list[QtQuick.QQuickItem]:
    found = [item] if item.objectName() == name else []
    for sub in item.childItems():
        found += _items_named(sub, name)
    return found


def switches(list_name: str = "ssmProgramList") -> list[dict]:
    """A list's Ignore switches, top to bottom (ListView delegates have no
    QObject parent, so they are found through the items)."""
    view = win.findChild(QtQuick.QQuickItem, list_name)
    assert view is not None
    rows = _items_named(view.property("contentItem"), "ssmIgnoreSwitch")
    return sorted(
        (
            {
                "y": float(o.mapToItem(view, QtCore.QPointF(0, 0)).y()),
                "checked": bool(o.property("checked")),
                "obj": o,
            }
            for o in rows
        ),
        key=lambda r: r["y"],
    )


settle(300)
out: dict[str, object] = {
    "title": win.property("title"),
    "objectName": win.objectName(),
    "visible": bool(win.property("visible")),
}


def row(prefix: str) -> dict:
    """A timer row (S4, S5): its switch, box, ✕ and saved setting."""
    key = "screen-saver" if prefix == "Saver" else "power-off"
    return {
        "on": bool(prop(f"ssm{prefix}On", "checked")),
        "waitText": str(prop(f"ssm{prefix}WaitBox", "text")),
        "placeholder": str(prop(f"ssm{prefix}WaitBox", "placeholderText")),
        "clearVisible": bool(prop(f"ssm{prefix}WaitClear", "visible")),
        "cfgOn": cfg(f"{key}-on"),
        "cfgWait": cfg(f"{key}-wait-s"),
    }


def old_names() -> list[str]:
    return [
        n
        for n in (
            "ssmActionScreenSaver",
            "ssmActionPowerOff",
            "ssmWaitBox",
            "ssmWaitClear",
            "ssmWindowsWait",
        )
        if win.findChild(QtCore.QObject, n) is not None
    ]


def type_in(name: str, text: str) -> None:
    child(name).setProperty("text", text)
    emit(name, "editingFinished")
    settle()


# Start: off, both timers on, Windows' times.
out["start"] = {
    "enabled": bool(prop("ssmEnabled", "checked")),
    "hold": bool(prop("ssmHoldFullscreen", "checked")),
    "saver": row("Saver"),
    "off": row("Off"),
    "cfgEnabled": cfg("enabled"),
    "cfgHold": cfg("hold-fullscreen"),
    "oldNames": old_names(),
    **texts(),
}

# On (S2): saved and applied.
toggle("ssmEnabled", True)
settle()
out["on"] = {
    "cfgEnabled": cfg("enabled"),
    "applied": manager.settings().enabled,
    **texts(),
}

# Each timer's switch (S4): saved and applied on its own.
toggle("ssmSaverOn", False)
settle()
out["saverOff"] = {
    **row("Saver"),
    "applied": [manager.settings().screen_saver_on, manager.settings().power_off_on],
    **texts(),
}
toggle("ssmSaverOn", True)
toggle("ssmOffOn", False)
settle()
out["offOff"] = {
    **row("Off"),
    "applied": [manager.settings().screen_saver_on, manager.settings().power_off_on],
    **texts(),
}
toggle("ssmOffOn", True)
settle()

# Hold off during full-screen programs off (S7).
toggle("ssmHoldFullscreen", False)
settle()
out["holdOff"] = {
    "cfgHold": cfg("hold-fullscreen"),
    "applied": manager.settings().hold_fullscreen,
}

# A typed time per row (S5) replaces Windows' time for that row only; text
# that isn't a time goes back; the order warning follows.
type_in("ssmOffWaitBox", "15")
out["offTyped"] = {
    **row("Off"),
    "saverWait": cfg("screen-saver-wait-s"),
    "applied": manager.settings().power_off_wait_s,
    **texts(),
}
type_in("ssmSaverWaitBox", "20")
out["saverTyped"] = {
    **row("Saver"),
    "applied": manager.settings().screen_saver_wait_s,
    **texts(),
}
type_in("ssmSaverWaitBox", "0")
out["badTyped"] = row("Saver")

# ✕ clears its own row: Windows' time again.
emit("ssmSaverWaitClear", "clicked")
settle()
out["saverCleared"] = {
    **row("Saver"),
    "applied": manager.settings().screen_saver_wait_s,
    "offWait": cfg("power-off-wait-s"),
    **texts(),
}
emit("ssmOffWaitClear", "clicked")
settle()
out["offCleared"] = {
    **row("Off"),
    "applied": manager.settings().power_off_wait_s,
    **texts(),
}

# Status texts follow the manager, polled once a second (S9, S15, S8).
manager.extra = {
    "idle_s": 161.0,
    "windows_idle_s": 0.0,
    "hold": "display_request",
    "hold_program": "chrome.exe",
}
until(lambda: "chrome.exe" in status_blob(), 3.0)
out["held"] = texts()
manager.extra = {
    "idle_s": 30.0,
    "windows_idle_s": 30.0,
    "hold": "fullscreen",
    "hold_program": "StarCitizen.exe",
    "last_reset_kind": "program",
    "program_input_per_min": 8,
}
until(lambda: "StarCitizen.exe" in status_blob(), 3.0)
out["fullscreen"] = texts()
manager.extra = {
    "last_reset_kind": "keyboard",
    "last_reset_by": "Logitech G915",
    "last_reset_age_s": 0.5,
}
until(lambda: "G915" in status_blob(), 3.0)
out["keyboardReset"] = texts()
manager.extra = {"saver_problem": "no_screen_saver", "off_remaining_s": 200.0}
until(lambda: bool(prop("ssmSaverProblem", "text")), 3.0)
out["noScreenSaver"] = texts()
manager.extra = {"off_problem": "windows_never", "saver_remaining_s": 80.0}
until(lambda: bool(prop("ssmOffProblem", "text")), 3.0)
out["offNever"] = texts()
manager.extra = {"problem": "not_listening", "listening": False}
until(lambda: "can't be listened" in str(prop("ssmProblemText", "text")), 3.0)
out["notListening"] = texts()
manager.extra = {"saver_remaining_s": 80.0, "off_remaining_s": 200.0}
until(lambda: "3 min" in status_blob(), 3.0)
out["countdown"] = texts()
manager.extra = {
    "saver_fired": True,
    "off_fired": True,
    "keeping_off": True,
    "wakes": 136,
}
until(lambda: "136" in status_blob(), 3.0)
out["keepingOff"] = texts()
manager.extra = {}

# Test now button, Wait for devices box, status grid (SSM2 items 5, 9, 13).
out["ssm2"] = {
    "testText": str(prop("ssmTestNow", "text")),
    "waitText": str(prop("ssmDevicesWait", "text")),
    "gridRows": status_rows(),
}
# The fake manager has no test timer: give it a minimal one.
_test_left = [0]
manager.start_test = lambda delay_s=5.0: _test_left.__setitem__(0, 5)
manager.cancel_test = lambda: _test_left.__setitem__(0, 0)
manager.test_remaining = lambda: _test_left[0]
if ev("ssm.testCountdown !== undefined"):
    emit("ssmTestNow", "clicked")
    settle(200)
    out["ssm2"]["afterTestClick"] = {
        "text": str(prop("ssmTestNow", "text")),
        "countdown": int(ev("ssm.testCountdown")),
    }
    emit("ssmTestNow", "clicked")  # Cancel test (N)
    settle(200)
    out["ssm2"]["afterCancel"] = {
        "text": str(prop("ssmTestNow", "text")),
        "countdown": int(ev("ssm.testCountdown")),
    }
    waitbox = child("ssmDevicesWait")
    waitbox.forceActiveFocus()
    waitbox.setProperty("text", "25")
    QtCore.QMetaObject.invokeMethod(waitbox, "editingFinished")
    settle(200)
    out["ssm2"]["waitTyped"] = {
        "text": str(prop("ssmDevicesWait", "text")),
        "model": int(ev("ssm.devicesWaitS")),
        "cfg": cfg("devices-wait-s"),
    }

tabs = child("ssmTabs")
out["summaryEmpty"] = str(prop("ssmDevicesSummary", "text"))
emit("ssmOpenDevices", "clicked")  # S12: Open Devices opens the Devices tab
settle()
out["openDevices"] = int(tabs.property("currentIndex"))
out["detectionOnDevices"] = list(manager.detection)

# Refresh Devices (S27): busy text while it reads, then the list.
out["devicesBefore"] = int(prop("ssmDeviceList", "count"))
calls.gate = threading.Event()
emit("ssmRefreshDevices", "clicked")
settle(100)
out["devicesBusy"] = {
    "text": str(prop("ssmRefreshDevices", "text")),
    "enabled": bool(prop("ssmRefreshDevices", "enabled")),
}
calls.gate.set()
until(lambda: int(prop("ssmDeviceList", "count")) > 0)
settle()
out["devices"] = {
    "scans": list(calls.scans),
    "count": int(prop("ssmDeviceList", "count")),
    "rows": [
        str(d["name"]) + " · " + str(round(d["rate"])) for d in ev("_ssm.devices")
    ],
    "text": str(prop("ssmRefreshDevices", "text")),
    "summary": str(prop("ssmDevicesSummary", "text")),
    "message": str(prop("ssmDevicesMessage", "text")),
    "modelMessage": str(ev("_ssm.devicesMessage")),
}
calls.gate = None
tabs.setProperty("currentIndex", 0)
settle()


# The three sections (S12, S13, S17), stacked, each with its own button.
def section_of(obj: QtQuick.QQuickItem) -> str:
    item = obj
    while item is not None:
        if item.objectName().startswith(("ssmSection", "ssmDevicesPage")):
            return item.objectName()
        item = item.parentItem()
    return ""


def y_of(name: str) -> float:
    obj = win.findChild(QtQuick.QQuickItem, name)
    return float(obj.mapToScene(QtCore.QPointF(0, 0)).y())


def section_texts(name: str) -> list[str]:
    found = []

    def walk(item: QtQuick.QQuickItem) -> None:
        text = item.property("text")
        # A Button and its label both carry the text: once.
        if isinstance(text, str) and text and item.isVisible() and text not in found:
            found.append(text)
        for sub in item.childItems():
            walk(sub)

    walk(win.findChild(QtQuick.QQuickItem, name))
    return found


out["sections"] = {
    "order": sorted(
        ("ssmSectionDevices", "ssmSectionPrograms", "ssmSectionSystem"), key=y_of
    ),
    "homes": {
        n: section_of(win.findChild(QtQuick.QQuickItem, n))
        for n in (
            "ssmOpenDevices",
            "ssmDevicesSummary",
            "ssmRefreshDevices",
            "ssmRefreshPrograms",
            "ssmRefreshSystem",
            "ssmDeviceList",
            "ssmProgramList",
            "ssmSystemList",
            "ssmProgramsMessage",
            "ssmSystemMessage",
        )
    },
    "texts": {
        n: section_texts(n)
        for n in ("ssmSectionDevices", "ssmSectionPrograms", "ssmSectionSystem")
    },
    "systemText": str(prop("ssmRefreshSystem", "text")),
}

# Refresh Programs (S13), then Ignore (S14).
emit("ssmRefreshPrograms", "clicked")
until(lambda: int(prop("ssmProgramList", "count")) == 2)
settle()
rows = switches()


def shown(name: str, list_name: str = "ssmProgramList") -> list[dict]:
    """The rows' labels named `name`, top to bottom: text and visible."""
    view = win.findChild(QtQuick.QQuickItem, list_name)
    found = _items_named(view.property("contentItem"), name)
    found.sort(key=lambda o: float(o.mapToItem(view, QtCore.QPointF(0, 0)).y()))
    return [
        {"text": str(o.property("text")), "visible": bool(o.property("visible"))}
        for o in found
    ]


out["programs"] = {
    "lists": calls.lists,
    "count": int(prop("ssmProgramList", "count")),
    "systemCount": int(prop("ssmSystemList", "count")),
    "alsoAwake": shown("ssmAlsoAwake"),
    "checked": [r["checked"] for r in rows],
    "message": str(prop("ssmProgramsMessage", "text")),
    "names": [r["text"] for r in shown("ssmProgramName")],
    "kinds": shown("ssmProgramKind"),
    "details": shown("ssmProgramDetail"),
}

# Refused: the switch goes back, the window says so.
calls.ignore_answer = (False, "Administrator rights were refused.")
first = rows[0]["obj"]
first.setProperty("checked", True)
QtCore.QMetaObject.invokeMethod(first, "toggled")
until(lambda: "refused" in str(prop("ssmProgramsMessage", "text")))
settle()
out["refused"] = {
    "ignores": list(calls.ignores),
    "checked": [r["checked"] for r in switches()],
    "message": str(prop("ssmProgramsMessage", "text")),
}

# Accepted: it stays on.
calls.ignore_answer = (True, "")
first = switches()[0]["obj"]
first.setProperty("checked", True)
QtCore.QMetaObject.invokeMethod(first, "toggled")
until(lambda: "is ignored" in str(prop("ssmProgramsMessage", "text")))
settle()
out["accepted"] = {
    "ignores": list(calls.ignores),
    "checked": [r["checked"] for r in switches()],
    "message": str(prop("ssmProgramsMessage", "text")),
}

# Refresh System (S17): its own check, its own list; Programs stays.
emit("ssmRefreshSystem", "clicked")
until(lambda: int(prop("ssmSystemList", "count")) == 3)
settle()
out["system"] = {
    "lists": calls.lists,
    "count": int(prop("ssmSystemList", "count")),
    "programCount": int(prop("ssmProgramList", "count")),
    "names": [r["text"] for r in shown("ssmProgramName", "ssmSystemList")],
    "kinds": shown("ssmProgramKind", "ssmSystemList"),
    "details": shown("ssmProgramDetail", "ssmSystemList"),
    "alsoAwake": shown("ssmAlsoAwake", "ssmSystemList"),
    "checked": [r["checked"] for r in switches("ssmSystemList")],
    "message": str(prop("ssmSystemMessage", "text")),
}

# A driver's row (S14 widened): its switch passes the kind on; the message
# is the System one.
second = switches("ssmSystemList")[1]["obj"]
second.setProperty("checked", True)
QtCore.QMetaObject.invokeMethod(second, "toggled")
until(lambda: len(calls.ignores) == 3 and not ev("_ssm.pendingIgnore"))
settle()
out["driver"] = {
    "ignores": list(calls.ignores),
    "checked": [r["checked"] for r in switches("ssmSystemList")],
    "programsChecked": [r["checked"] for r in switches()],
    "message": str(prop("ssmSystemMessage", "text")),
    "programsMessage": str(prop("ssmProgramsMessage", "text")),
}

# A refused list (S13): the window says so, the list stays as it was.
calls.requests = ssm_ui_fakes.RequestsResult(
    False, "Administrator rights were refused.", []
)
emit("ssmRefreshPrograms", "clicked")
until(lambda: calls.lists == 3 and not ev("_ssm.scanningPrograms"))
settle()
out["listRefused"] = {
    "count": int(prop("ssmProgramList", "count")),
    "message": str(prop("ssmProgramsMessage", "text")),
}

# S26: the helper should run and doesn't (refused): the message and Try
# again, in the Devices section; Try again asks once more.
disabler = calls.disabler
disabler.running = False
disabler.answer = (False, "The confirmation was declined.")
ev("_ssm.setEnabled(true); _ssm.setOffOn(true); true")
starts = disabler.starts
ev("_ssm.tryAgain(); true")
tabs.setProperty("currentIndex", 1)
settle()
helper_label = win.findChild(QtQuick.QQuickItem, "ssmHelperMessage")
helper_button = win.findChild(QtQuick.QQuickItem, "ssmHelperTryAgain")
out["helper"] = {
    "saved": [d.get("instance_ids") for d in (cfg("devices") or [])],
    "text": str(prop("ssmHelperMessage", "text")),
    "visible": bool(helper_label.isVisible()),
    "buttonText": str(prop("ssmHelperTryAgain", "text")),
    "buttonVisible": bool(helper_button.isVisible()),
    "section": [section_of(helper_label), section_of(helper_button)],
    "starts": disabler.starts - starts,
}
disabler.answer = (True, "")
emit("ssmHelperTryAgain", "clicked")
settle()
out["helperAfter"] = {
    "visible": bool(helper_label.isVisible()),
    "starts": disabler.starts - starts,
}
tabs.setProperty("currentIndex", 0)
settle()

# Wake PC (S28-S31): three tabs; the list renders on its own tab, read when
# it opens; a key press ticks a device; a tick by hand; leaving the tab
# stops the detection.
TABS = ("ssmTabSettings", "ssmTabDevices", "ssmTabWake")
HEADER = ("ssmEnabled", "ssmTestNow", "ssmDescription")


def tab_texts() -> list[str]:
    return [str(prop(n, "text")) for n in TABS]


def layout() -> dict:
    """S28: the header and the tab bar as laid out now."""
    root = win.contentItem()

    def box(name: str) -> list[int]:
        item = win.findChild(QtQuick.QQuickItem, name)
        at = item.mapToItem(root, QtCore.QPointF(0, 0))
        return [round(v) for v in (at.x(), at.y(), item.width(), item.height())]

    return {
        "width": round(root.width()),
        "header": {n: [item_shown(n), *box(n)] for n in HEADER},
        "bar": box("ssmTabs"),
        "tabs": [box(n) for n in TABS],
        "fills": [
            child(n).property("background").property("color").name() for n in TABS
        ],
        "sizes": [
            child(n).property("contentItem").property("font").pixelSize() for n in TABS
        ],
    }


def item_shown(name: str) -> bool:
    return bool(win.findChild(QtQuick.QQuickItem, name).isVisible())


def wake_rows() -> list[dict]:
    view = win.findChild(QtQuick.QQuickItem, "ssmWakeList")
    rows = _items_named(view.property("contentItem"), "ssmWakeRow")
    rows.sort(key=lambda o: float(o.mapToItem(view, QtCore.QPointF(0, 0)).y()))

    def one(r: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem:
        return _items_named(r, name)[0]

    return [
        {
            "name": str(one(r, "ssmWakeName").property("text")),
            "kinds": str(one(r, "ssmWakeKinds").property("text")),
            "ticked": bool(one(r, "ssmWakeTick").property("checked")),
            "note": str(one(r, "ssmWakeNote").property("text")),
            # S33: the row's background lit while its device is in use.
            "lit": bool(one(r, "ssmWakeRowHighlight").isVisible()),
        }
        for r in rows
    ]


def wake_ticks() -> list[QtQuick.QQuickItem]:
    view = win.findChild(QtQuick.QQuickItem, "ssmWakeList")
    found = _items_named(view.property("contentItem"), "ssmWakeTick")
    found.sort(key=lambda o: float(o.mapToItem(view, QtCore.QPointF(0, 0)).y()))
    return found


wake: dict[str, object] = {
    "tabs": tab_texts(),
    "startIndex": int(tabs.property("currentIndex")),
    "settingsShown": item_shown("ssmStatusGrid"),
    "wakeShown": item_shown("ssmWakeList"),
    "settingsHome": [
        n
        for n in ("ssmEnabled", "ssmSectionDevices", "ssmStatusGrid")
        if win.findChild(QtQuick.QQuickItem, n) is not None
    ],
}
layouts = []
for index in range(3):
    tabs.setProperty("currentIndex", index)
    settle()
    layouts.append(layout())
    if index == 1:
        wake["detectionOnDevices"] = list(manager.detection)
out["layouts"] = layouts
tabs.setProperty("currentIndex", 0)
settle()
manager.detection.clear()
reads = len(calls.input_reads)
tabs.setProperty("currentIndex", 2)
until(lambda: int(prop("ssmWakeList", "count")) == 2)
settle()
wake["openDetection"] = list(manager.detection)
wake["wakeVisible"] = item_shown("ssmWakeList") and not item_shown("ssmStatusGrid")
wake["reads"] = len(calls.input_reads) - reads
wake["heading"] = str(prop("ssmWakeHeading", "text"))
wake["programsNote"] = str(prop("ssmWakeProgramsNote", "text"))
wake["rows"] = wake_rows()
# S33: a short highlight time so the real timer ends it here.
ssm_model.IN_USE_S = 0.6
manager.press(ssm_ui_fakes.INPUT_DEVICES[0].physical_id, "keyboard")
settle()
wake["pressed"] = wake_rows()
# S33: movement lights the other row without ticking it.
manager.activity(ssm_ui_fakes.INPUT_DEVICES[1].physical_id)
settle()
wake["moved"] = wake_rows()
until(lambda: not any(r["lit"] for r in wake_rows()))
wake["faded"] = wake_rows()
tick = wake_ticks()[1]
tick.setProperty("checked", True)
QtCore.QMetaObject.invokeMethod(tick, "toggled")
settle()
wake["clicked"] = {
    "ticked": [r["ticked"] for r in wake_rows()],
    "cfg": [[r["ticked"], r["how"]] for r in (cfg("wake-pc") or [])],
}
tabs.setProperty("currentIndex", 0)
settle()
wake["back"] = {
    "detection": list(manager.detection),
    "settingsShown": item_shown("ssmStatusGrid"),
}
out["wake"] = wake

# The Devices tab (S27, S35): one choice a row; a virtual row is locked on
# Manual with its note; a device not found keeps its row, with no rate; a long
# name elides; Remove forgets the row.
LONG = "A very long device name that goes on " * 6
VJOY = "vJoy Device"
PD = "PD200X Microphone (buttons)"
VKB = "VKBSim NXT SEM THQ FSM.GA"
calls.devices.append(ssm_ui_fakes.DeviceRate(VJOY, "ROOT\\HIDCLASS\\0001", 1, 4, 20.0))
calls.devices.append(ssm_ui_fakes.DeviceRate(LONG, "HID\\VID_5&PID_6\\1", 1, 4, 5.0))
tabs.setProperty("currentIndex", 1)
win.setProperty("width", win.property("minimumWidth"))
win.setProperty("height", win.property("minimumHeight"))
emit("ssmRefreshDevices", "clicked")
until(lambda: int(prop("ssmDeviceList", "count")) == 4)
settle()


def device_rows() -> dict[str, dict]:
    """The rows as shown, by name."""
    view = win.findChild(QtQuick.QQuickItem, "ssmDeviceList")

    def view_of(row: QtQuick.QQuickItem) -> dict:
        def one(name: str) -> QtQuick.QQuickItem:
            return _items_named(row, name)[0]

        found = one("ssmDeviceFound")
        remove = one("ssmDeviceRemove")
        return {
            "name": str(one("ssmDeviceName").property("text")),
            "truncated": bool(one("ssmDeviceName").property("truncated")),
            "rate": str(one("ssmDeviceRate").property("text")),
            "automatic": bool(one("ssmDeviceAutomatic").property("checked")),
            "manual": bool(one("ssmDeviceManual").property("checked")),
            "enabled": [
                bool(one(n).property("enabled"))
                for n in ("ssmDeviceAutomatic", "ssmDeviceManual")
            ],
            "found": str(found.property("text")),
            "foundVisible": found.isVisible(),
            "foundColor": found.property("color").name(),
            "virtualNote": one("ssmDeviceVirtual").isVisible(),
            "virtualText": str(one("ssmDeviceVirtual").property("text")),
            "right": round(
                remove.mapToItem(
                    win.contentItem(), QtCore.QPointF(remove.width(), 0)
                ).x()
            ),
        }

    rows = [view_of(r) for r in _items_named(view, "ssmDeviceRow")]
    return {r["name"]: r for r in rows}


def part(device: str, name: str) -> QtQuick.QQuickItem:
    view = win.findChild(QtQuick.QQuickItem, "ssmDeviceList")
    for row in _items_named(view, "ssmDeviceRow"):
        if _items_named(row, "ssmDeviceName")[0].property("text") == device:
            return _items_named(row, name)[0]
    raise AssertionError(device)


def click(item: QtQuick.QQuickItem) -> None:
    """A real mouse click in the middle of the item."""
    at = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(
        win,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        at.toPoint(),
    )
    settle()


def stored() -> dict[str, str]:
    return {d["name"]: d["choice"] for d in (cfg("devices") or [])}


def scroll_to(item: QtQuick.QQuickItem) -> None:
    """Scrolls the Devices page so the item is in the window's middle."""
    flick = item
    while flick is not None and flick.property("contentY") is None:
        flick = flick.parentItem()
    # The list's own flickable doesn't scroll: the page's does.
    page = flick.parentItem()
    while page is not None and page.property("contentY") is None:
        page = page.parentItem()
    top = max(0.0, page.property("contentHeight") - page.height())
    y = item.mapToItem(page.property("contentItem"), QtCore.QPointF(0, 0)).y()
    page.setProperty("contentY", min(top, max(0.0, y - page.height() / 2)))
    settle(50)


def press(device: str, name: str) -> None:
    scroll_to(part(device, name))
    click(part(device, name))


dev: dict[str, object] = {
    "width": round(win.contentItem().width()),
    "warnColor": ev("Style.warn").name(),
    "heading": str(prop("ssmDevicesHeading", "text")),
    "description": str(prop("ssmDevicesDescription", "text")),
    "header": section_texts("ssmDeviceHeader"),
    "start": device_rows(),
}
press(PD, "ssmDeviceManual")
dev["manual"] = {"rows": device_rows(), "stored": stored()}
dev["manualSummary"] = str(prop("ssmDevicesSummary", "text"))
press(PD, "ssmDeviceAutomatic")
dev["automatic"] = {"rows": device_rows(), "stored": stored()}
press(PD, "ssmDeviceManual")
press(VJOY, "ssmDeviceAutomatic")
dev["locked"] = {"rows": device_rows(), "stored": stored()}

# Not found by the next Refresh Devices: the row and its choice stay.
calls.devices[:] = [d for d in calls.devices if d.name != PD]
emit("ssmRefreshDevices", "clicked")
until(lambda: "Not found" in str(device_rows()[PD]["found"]))
settle()
dev["gone"] = {"rows": device_rows(), "stored": stored()}
dev["goneSummary"] = str(prop("ssmDevicesSummary", "text"))
dev["goneMessage"] = str(prop("ssmDevicesMessage", "text"))

press(PD, "ssmDeviceRemove")
dev["removed"] = {"rows": device_rows(), "stored": stored()}
out["devicesTab"] = dev

win.close()
settle()
out["warnings"] = warnings
out["closed"] = not bool(win.property("visible"))
print(json.dumps(out), flush=True)
smoke_exit(0)
