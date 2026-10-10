# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input Tester buttons area off-screen (02 S147, S148): input_tester.py
started as for a user, on fake hardware whose "pJoy Pro" stick has 128
buttons. In a tall window every button row shows with no scrolling; in a
short one, a fake press of button 120 with Follow input on scrolls it into
view, and with Follow input off the view stays put. Prints
"RESULT name json", "QTLOG json" (Qt warnings) and "done".
test_input_tester_buttons.py runs it.

    python test/unit/input_tester_buttons_smoke.py <gremlin dir> <shot.png>
"""

from __future__ import annotations

import importlib.util
import json
import os
import runpy
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
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
fake.devices[0].button_count = 128  # the "pJoy Pro" stick

pressed: set[tuple[bytes, int]] = set()
fake.get_button = lambda guid, index: (bytes(guid), index) in pressed  # type: ignore[method-assign]

from gremlin.input_tester import devices, steam  # noqa: E402

devices.xinput_devices = lambda: []  # type: ignore[assignment]
devices.hid_devices = lambda: []  # type: ignore[assignment]
devices.hid_scan = lambda: ([], [])  # type: ignore[assignment]
devices.last_hid_skips = lambda: []  # type: ignore[assignment]
steam.steam_running = lambda: False  # type: ignore[assignment]

from PySide6 import QtCore, QtGui, QtQuick, QtTest  # noqa: E402

GREMLIN_DIR, SHOT = Path(sys.argv[1]), Path(sys.argv[2])
STICK_RAW = bytes(fake_hardware.raw_guid(is_virtual=False))
qt_log: list[str] = []


def _qt_message(mode, context, message) -> None:  # noqa: ANN001
    if mode != QtCore.QtMsgType.QtDebugMsg:
        qt_log.append(message)


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def items_under(root: QtQuick.QQuickItem) -> list[QtQuick.QQuickItem]:
    found, todo = [], [root]
    while todo:
        current = todo.pop()
        found.append(current)
        todo.extend(current.childItems())
    return found


def item(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
    return next(
        (i for i in items_under(window.contentItem()) if i.objectName() == name),
        None,
    )


def click(window: QtQuick.QQuickWindow, target: QtQuick.QQuickItem) -> None:
    centre = target.mapToScene(QtCore.QPointF(target.width() / 2, target.height() / 2))
    QtTest.QTest.mouseClick(
        window,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        centre.toPoint(),
    )


def cell_in_view(window: QtQuick.QQuickWindow, number: int) -> bool:
    """Button `number`'s cell lies wholly inside the buttons area."""
    view = item(window, "buttonsView")
    cell = item(window, f"buttonCell_{number}")
    top = cell.mapToItem(view, QtCore.QPointF(0, 0)).y()
    return bool(top >= -0.5 and top + cell.height() <= view.height() + 0.5)


def state(window: QtQuick.QQuickWindow) -> dict:
    view = item(window, "buttonsView")
    detail = item(window, "deviceView")
    hats = item(window, "hat_1")
    hat_top = hats.mapToItem(detail, QtCore.QPointF(0, 0)).y()
    return {
        "view_h": round(view.height(), 1),
        "content_h": round(view.property("contentHeight"), 1),
        "content_y": round(view.property("contentY"), 1),
        "interactive": bool(view.property("interactive")),
        "detail_scrolls": detail.property("contentHeight") > detail.height() + 0.5,
        "hats_in_view": bool(hat_top + hats.height() <= detail.height() + 0.5),
        "label": next(
            (
                i.property("text")
                for i in items_under(detail)
                if str(i.property("text") or "").startswith("BUTTONS")
            ),
            None,
        ),
    }


def checks(app: QtGui.QGuiApplication) -> None:
    window = next(
        w
        for w in app.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow) and w.objectName() == "inputTester"
    )
    window.resize(1100, 1000)
    QtTest.QTest.qWait(600)
    rows = {}
    for row in items_under(window.contentItem()):
        if row.objectName().startswith("deviceRow_"):
            label = next(i for i in items_under(row) if i.objectName() == "rowName")
            rows[label.property("text")] = row
    result("rows", sorted(rows))
    click(window, rows["pJoy Pro"])
    QtTest.QTest.qWait(300)
    tall = state(window)
    tall["all_cells"] = all(cell_in_view(window, n) for n in range(1, 129))
    result("tall", tall)
    SHOT.parent.mkdir(parents=True, exist_ok=True)
    window.grabWindow().save(str(SHOT))

    # Short window: some rows don't fit.
    window.resize(1100, 700)
    QtTest.QTest.qWait(300)
    short: dict = {"before": state(window)}
    pressed.add((STICK_RAW, 120))
    QtTest.QTest.qWait(300)
    short["follow_on"] = state(window)
    short["follow_on"]["cell_120"] = cell_in_view(window, 120)
    window.grabWindow().save(str(SHOT.parent / (SHOT.stem + "_short.png")))
    pressed.discard((STICK_RAW, 120))
    QtTest.QTest.qWait(300)

    # Follow input off: the view stays where the user put it.
    item(window, "buttonsView").setProperty("contentY", 0)
    click(window, item(window, "followInputSwitch"))
    QtTest.QTest.qWait(200)
    short["switch_off"] = not bool(
        item(window, "followInputSwitch").property("checked")
    )
    pressed.add((STICK_RAW, 120))
    QtTest.QTest.qWait(300)
    short["follow_off"] = state(window)
    short["follow_off"]["cell_120"] = cell_in_view(window, 120)
    short["follow_off"]["cell_120_pressed"] = bool(
        item(window, "buttonCell_120").property("pressed")
    )
    result("short", short)


def main() -> None:
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
