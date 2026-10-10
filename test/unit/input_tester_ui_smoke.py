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
# One HID path HidHide hides from this process (open -> access denied).
DENIED = devices.HidSkip(
    path="\\\\?\\hid#vid_231d&pid_0200#a&6b6f223&0&0000#{4d1e55b2}",
    name="VKBsim Gladiator EVO R",
    vid=0x231D,
    pid=0x0200,
    reason="access denied (5)",
    code=5,
)
devices.hid_scan = lambda: ([], [DENIED])  # type: ignore[assignment]
devices.last_hid_skips = lambda: [DENIED]  # type: ignore[assignment]
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
# Restart tester: what the injected starter was asked to start, and quits.
started: list[object] = []
quits: list[bool] = []


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
    result(
        "hints",
        {
            name: [
                i.property("text")
                for i in items_under(row)
                if i.objectName() == "rowHint" and i.isVisible()
            ]
            for name, row in rows.items()
        },
    )
    result(
        "headings",
        [
            i.property("text")
            for i in items(window)
            if i.isVisible()
            and isinstance(i.property("text"), str)
            and i.property("text").startswith(("YOUR", "GREMLIN'S", "XBOX", "ALL"))
        ],
    )
    result(
        "status_line",
        item(window, "statusLine").property("text"),
    )

    def skipped() -> list[dict]:
        return [
            {
                "label": i.property("text"),
                "visible": bool(i.isVisible()),
                "opacity": round(float(i.parentItem().property("opacity")), 2),
            }
            for i in items(window)
            if i.objectName() == "hidSkippedLabel"
        ]

    # S3: the game devices list is folded under Show details, closed at start;
    # a real click opens it and another closes it.
    toggle = item(window, "showDetailsToggle")
    details: dict = {
        "toggle_visible": bool(toggle.isVisible()),
        "heading_visible": bool(item(window, "hidHeading").isVisible()),
        "closed": [s["visible"] for s in skipped()],
    }
    click(window, toggle)
    QtTest.QTest.qWait(150)
    details["open"] = [s["visible"] for s in skipped()]
    result("hid_skipped", skipped())
    click(window, toggle)
    QtTest.QTest.qWait(150)
    details["closed_again"] = [s["visible"] for s in skipped()]
    result("details", details)
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

    # The stick row (hidden from programs in the pass case) shows the
    # detail line and Should be line instead of live values.
    if CASE == "pass":
        hidden_row = rows.get("Right stick")
        click(window, hidden_row)
        QtTest.QTest.qWait(200)
        result(
            "not_seen",
            {
                "detail": item(window, "notSeenDetail").property("text"),
                "detail_visible": bool(item(window, "notSeenDetail").isVisible()),
                "should_be": item(window, "shouldBe").property("text"),
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

    if CASE == "pass":
        follow_checks(window, rows, stick_row, vjoy_row)
        logs_checks(window)
        stale_checks(window)


def visible_named(window: QtQuick.QQuickWindow, name: str) -> list[QtQuick.QQuickItem]:
    return [i for i in items(window) if i.objectName() == name and i.isVisible()]


def follow_checks(window, rows, stick_row, vjoy_row) -> None:  # noqa: ANN001
    """Item 7: moving a fake axis on another device selects and shows it;
    jitter doesn't; the All devices view never switches."""
    stick_key = stick_row.objectName().removeprefix("deviceRow_")
    vjoy_key = vjoy_row.objectName().removeprefix("deviceRow_")
    switch = item(window, "followInputSwitch")
    QtTest.QTest.qWait(1200)  # past the 1 s hold after any earlier switch
    axes[(STICK_RAW, 2)] = 600  # jitter, under 0.05
    QtTest.QTest.qWait(300)
    jitter = item(window, "detailName").property("text")
    axes[(STICK_RAW, 2)] = 20000
    QtTest.QTest.qWait(300)
    moved = {
        "detail": item(window, "detailName").property("text"),
        "row_selected": bool(stick_row.property("selected")),
        "vjoy_selected": bool(vjoy_row.property("selected")),
    }
    # All devices: moving the vJoy axis changes nothing.
    QtTest.QTest.qWait(1200)
    click(window, item(window, "allDevicesRow"))
    QtTest.QTest.qWait(200)
    axes[(VJOY_RAW, 2)] = -20000
    QtTest.QTest.qWait(400)
    all_view = {
        "compact_visible": bool(item(window, "compactView").isVisible()),
        "vjoy_selected": bool(vjoy_row.property("selected")),
        "detail_visible": bool(item(window, "deviceView").isVisible()),
    }
    result(
        "follow",
        {
            "switch_visible": bool(switch.isVisible()) if switch else None,
            "switch_on": bool(switch.property("checked")) if switch else None,
            "jitter_detail": jitter,
            "moved": moved,
            "all_view": all_view,
            "keys_differ": stick_key != vjoy_key,
        },
    )
    click(window, vjoy_row)  # back to one device for the shots
    QtTest.QTest.qWait(200)


def logs_checks(window: QtQuick.QQuickWindow) -> None:
    """Logs tab by a real click: pick Tester log, Find filters, Follow on."""
    out: dict = {}
    click(window, item(window, "tab_logs"))
    QtTest.QTest.qWait(300)
    view = item(window, "logsView")
    out["logs_visible"] = bool(view and view.isVisible())
    out["devices_hidden"] = not item(window, "deviceList").isVisible()
    picker = item(window, "logPicker")
    click(window, picker)
    QtTest.QTest.qWait(150)
    choices = {
        i.objectName(): i
        for i in items_under(picker)
        if i.objectName().startswith("comboChoice_") and i.isVisible()
    }
    out["choices"] = len(choices)
    if "comboChoice_0" in choices:
        click(window, choices["comboChoice_0"])
    QtTest.QTest.qWait(700)
    shown = item(window, "logPickerText")
    out["picked"] = shown.property("text") if shown else None
    lines = visible_named(window, "logLine")
    out["lines"] = len(lines)
    out["texts"] = [str(i.property("lineText")) for i in lines][:20]
    out["status"] = item(window, "logStatus").property("text")
    QtTest.QTest.qWait(200)
    window.grabWindow().save(str(SHOT.parent / "logs.png"))

    # Follow off by a click, then on again.
    follow = item(window, "logFollow")
    click(window, follow)
    QtTest.QTest.qWait(150)
    out["follow_after_off"] = bool(follow.property("checked"))
    click(window, follow)
    QtTest.QTest.qWait(150)
    out["follow_after_on"] = bool(follow.property("checked"))
    out["at_end"] = bool(item(window, "logLines").property("atYEnd"))

    # Find: type into the box; only matching lines are marked.
    find = item(window, "logFind")
    click(window, find)
    for ch in "Started":
        QtTest.QTest.keyClick(window, ch)
    QtTest.QTest.qWait(400)
    shown = visible_named(window, "logLine")
    out["find_count"] = item(window, "logFindCount").property("text")
    out["find_matches"] = [
        str(i.property("lineText")) for i in shown if i.property("match")
    ]
    out["find_others"] = len([i for i in shown if not i.property("match")])
    # Show: Warnings only.
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Escape)
    show = item(window, "logShow")
    click(window, show)
    QtTest.QTest.qWait(150)
    warn = next(
        i
        for i in items_under(show)
        if i.objectName() == "comboChoice_1" and i.isVisible()
    )
    click(window, warn)
    QtTest.QTest.qWait(400)
    out["warnings_only_all_warn"] = all(
        bool(i.property("warn")) for i in visible_named(window, "logLine")
    )
    click(window, show)
    QtTest.QTest.qWait(150)
    choice = next(i for i in items_under(show) if i.objectName() == "comboChoice_0")
    click(window, choice)
    QtTest.QTest.qWait(200)
    result("logs", out)
    click(window, item(window, "tab_devices"))
    QtTest.QTest.qWait(200)


def stale_checks(window: QtQuick.QQuickWindow) -> None:
    """Gremlin changes HidHide after the tester started: yellow banner;
    Restart tester calls the (injected) starter."""
    from datetime import datetime, timedelta

    banner = item(window, "staleBanner")
    before = bool(banner.isVisible())
    path = GREMLIN_DIR / "tester" / "expected.json"
    data = json.loads(path.read_text("utf-8"))
    data["hidhide_changed_at"] = (datetime.now() + timedelta(seconds=1)).isoformat(
        timespec="seconds"
    )
    data["hidhide_change"] = "program list"
    path.write_text(json.dumps(data), "utf-8")
    QtTest.QTest.qWait(2500)
    after = bool(banner.isVisible())
    text = item(window, "staleText").property("text")
    window.grabWindow().save(str(SHOT.parent / "banner.png"))
    click(window, item(window, "restartTesterButton"))
    QtTest.QTest.qWait(200)
    result(
        "stale",
        {
            "before": before,
            "after": after,
            "text": text,
            "started": started,
            "quits": len(quits),
        },
    )


def main() -> None:
    write_expected()
    from gremlin.input_tester import model as tester_model

    tester_model.set_starter(lambda args: started.append(list(args)))
    tester_model.set_quitter(lambda: quits.append(True))
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
