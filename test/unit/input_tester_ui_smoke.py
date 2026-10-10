# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-INPUT-TESTER off-screen: input_tester.py starts as it does for a
user (its own QML window), on fake hardware (test/fake_hardware.py: a
"pJoy Pro" stick and a "vJoy Device"), no XInput pads, no HID list, Steam
not running, with an expected.json written for the case ("fail": the stick
Gremlin hides is seen; "pass": everything as expected). Real mouse events
pick a row; a fake button press must light its cell. Prints "RESULT name
json" per check, "QTLOG json" (Qt warnings) and "done".
test_input_tester_ui.py runs it.

    python test/unit/input_tester_ui_smoke.py fail <gremlin dir> <shot.png>
"""

from __future__ import annotations

import importlib.util
import json
import os
import runpy
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Off-screen Qt finds no fonts on its own (and warns); use Windows' fonts.
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert _spec and _spec.loader
fake_hardware = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

# Live values the checks change: (raw guid bytes, index) -> value.
pressed: set[tuple[bytes, int]] = set()
axes: dict[tuple[bytes, int], int] = {}
fake.get_button = lambda guid, index: (bytes(guid), index) in pressed  # type: ignore[method-assign]
fake.get_axis = lambda guid, index: axes.get((bytes(guid), index), 0)  # type: ignore[method-assign]

from gremlin.input_tester import devices, steam  # noqa: E402

devices.xinput_devices = lambda: []  # type: ignore[assignment]
devices.hid_devices = lambda: []  # type: ignore[assignment]
steam.steam_running = lambda: False  # type: ignore[assignment]

from PySide6 import QtCore, QtGui, QtQuick, QtTest  # noqa: E402

CASE, GREMLIN_DIR, SHOT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])

seen = {d.name: d for d in devices.directinput_devices()}
STICK, VJOY = seen["pJoy Pro"], seen["vJoy Device"]
STICK_RAW = bytes(fake_hardware.raw_guid(is_virtual=False))
VJOY_RAW = bytes(fake_hardware.raw_guid(is_virtual=True))


def write_expected() -> None:
    sticks = [
        {
            "name": "Left stick",
            "windows_name": "pJoy Pro",
            "vid": STICK.vid,
            "pid": STICK.pid,
            "guid": STICK.guid,
            "instance_ids": ["HID\\VID_5678&PID_FACE\\1&0001"],
            "feeds": ["vJoy 1"],
            "expect": "hidden" if CASE == "fail" else "visible",
        }
    ]
    if CASE == "pass":
        sticks.append(
            {
                "name": "Right stick",
                "windows_name": "Hidden Stick",
                "vid": 0x1111,
                "pid": 0x2222,
                "guid": "{11111111-2222-3333-4444-555555555555}",
                "instance_ids": ["HID\\VID_1111&PID_2222\\1&0002"],
                "feeds": ["vJoy 1"],
                "expect": "hidden",
            }
        )
    data = {
        "version": 1,
        "written": "2026-10-10T03:14:22",
        "tester_path": str(ROOT / "Gremlin Input Tester.exe"),
        "hidhide": {
            "present": True,
            "cloak": True,
            "mode": "block",
            "tester_on_list": True,
            "apps": [],
        },
        "sticks": sticks,
        "vjoy": [
            {
                "id": 1,
                "guid": VJOY.guid,
                "fed_by": ["Left stick"],
                "used": True,
                "expect": "visible",
            }
        ],
        "xbox": [],
    }
    (GREMLIN_DIR / "tester").mkdir(parents=True, exist_ok=True)
    (GREMLIN_DIR / "tester" / "expected.json").write_text(json.dumps(data), "utf-8")


qt_log: list[str] = []


def _qt_message(mode, context, message) -> None:  # noqa: ANN001
    if mode != QtCore.QtMsgType.QtDebugMsg:
        qt_log.append(message)


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def items(window: QtQuick.QQuickWindow) -> list[QtQuick.QQuickItem]:
    """Every item in the window's visual tree (Repeater rows included)."""
    return items_under(window.contentItem())


def items_under(root: QtQuick.QQuickItem) -> list[QtQuick.QQuickItem]:
    found, todo = [], [root]
    while todo:
        current = todo.pop()
        found.append(current)
        todo.extend(current.childItems())
    return found


def item(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
    return next((i for i in items(window) if i.objectName() == name), None)


def click(window: QtQuick.QQuickWindow, target: QtQuick.QQuickItem) -> None:
    centre = target.mapToScene(QtCore.QPointF(target.width() / 2, target.height() / 2))
    QtTest.QTest.mouseClick(
        window,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        centre.toPoint(),
    )


def checks(app: QtGui.QGuiApplication) -> None:
    window = next(
        w
        for w in app.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow) and w.objectName() == "inputTester"
    )
    QtTest.QTest.qWait(600)
    verdict = item(window, "verdictText")
    result(
        "verdict",
        {
            "text": verdict.property("text") if verdict else None,
            "line_visible": bool(item(window, "verdictLine").isVisible()),
            "summary": item(window, "verdictSummary").property("text"),
            "context": item(window, "contextLine").property("text"),
        },
    )
    rows = {}
    for row in items(window):
        if row.objectName().startswith("deviceRow_"):
            label = next(i for i in items_under(row) if i.objectName() == "rowName")
            rows[label.property("text")] = row
    result("row_names", sorted(rows))
    stick_row = rows.get("Left stick")
    vjoy_row = next((r for n, r in rows.items() if n.startswith("vJoy Device")), None)
    result(
        "rows",
        {
            "stick": None
            if stick_row is None
            else {"bad": bool(stick_row.property("bad"))},
            "vjoy": None
            if vjoy_row is None
            else {"bad": bool(vjoy_row.property("bad"))},
        },
    )

    # A click on the vJoy row shows its axes.
    axes[(VJOY_RAW, 1)] = -16384
    click(window, vjoy_row)
    QtTest.QTest.qWait(300)
    bars = [b for b in items(window) if b.objectName() == "axisBar" and b.isVisible()]
    result(
        "select",
        {
            "detail": item(window, "detailName").property("text"),
            "row_selected": bool(vjoy_row.property("selected")),
            "axes": len(bars),
            "first_axis": next(
                (
                    round(float(b.property("value")), 2)
                    for b in bars
                    if b.property("name") == "X"
                ),
                None,
            ),
        },
    )

    # Pressing a fake button lights its cell.
    cell = item(window, "buttonCell_3")
    before = bool(cell.property("pressed")) if cell else None
    pressed.add((VJOY_RAW, 3))
    QtTest.QTest.qWait(300)
    cell = item(window, "buttonCell_3")
    result(
        "button",
        {
            "before": before,
            "after": bool(cell.property("pressed")) if cell else None,
            "other": bool(item(window, "buttonCell_4").property("pressed")),
        },
    )

    SHOT.parent.mkdir(parents=True, exist_ok=True)
    window.grabWindow().save(str(SHOT))
    result("shot", SHOT.is_file())


def main() -> None:
    write_expected()
    QtCore.qInstallMessageHandler(_qt_message)

    def exec_with_checks(*_args) -> int:  # noqa: ANN002
        app = QtGui.QGuiApplication.instance()
        try:
            checks(app)
        except Exception as error:  # noqa: BLE001
            print(f"ERROR {type(error).__name__}: {error}", flush=True)
        print(f"QTLOG {json.dumps(qt_log)}", flush=True)
        print("done", flush=True)
        return 0

    QtGui.QGuiApplication.exec = exec_with_checks  # type: ignore[method-assign]
    sys.argv = [str(ROOT / "input_tester.py"), "--gremlin-dir", str(GREMLIN_DIR)]
    try:
        runpy.run_path(str(ROOT / "input_tester.py"), run_name="__main__")
    except SystemExit:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
