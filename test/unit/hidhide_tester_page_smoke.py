# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-INPUT-TESTER on the HidHide page, off-screen in the real program: the
app starts as joystick_gremlin.py starts it (fake hardware, a fake HidHide
driver, a stand-in home folder, an injected Input Tester launcher and a fake
process list), the page is opened by the Tools menu's HidHide item, and the
page's buttons get real mouse clicks. Prints "RESULT name json" per check
and "done". test_hidhide_tester_page.py runs it.

    python test/unit/hidhide_tester_page_smoke.py <work folder>
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import time
import types
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert _spec and _spec.loader
fake_hardware = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

from gremlin import hidhide_driver, process_paths  # noqa: E402
from gremlin.ui import hidhide as hh  # noqa: E402

WORK = Path(sys.argv[1])
TESTER = str(WORK / "new" / "Gremlin Input Tester.exe")
OLD_TESTER = str(WORK / "old" / "Gremlin Input Tester.exe")
LIVE = r"D:\StarCitizen\LIVE\Bin64\StarCitizen.exe"
PTU = r"D:\StarCitizen\PTU\Bin64\StarCitizen.exe"
Left = QtCore.Qt.MouseButton.LeftButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier


# A fake HidHide driver: never the real one.
class Driver:
    present = True
    active = False
    inverse = True
    blacklist: list[str] = []
    whitelist: list[str] = []


DRV = Driver()


def _set(name: str, value: object) -> bool:
    setattr(DRV, name, value)
    return True


_FAKES = {
    "driver_present": lambda: True,
    "driver_version": lambda: "1.5",
    "get_active": lambda: DRV.active,
    "set_active": lambda on: _set("active", on),
    "get_inverse": lambda: DRV.inverse,
    "set_inverse": lambda on: _set("inverse", on),
    "get_blacklist": lambda: list(DRV.blacklist),
    "set_blacklist": lambda ids: _set("blacklist", list(ids)),
    "get_whitelist": lambda: list(DRV.whitelist),
    "set_whitelist": lambda paths: _set("whitelist", list(paths)),
    "list_hid_devices": lambda gaming_only=False: [],
    "_full_image_name": lambda path: path,
    "_gremlin_exe": lambda: r"C:\Gremlin\joystick_gremlin.exe",
}
for _name, _fake in _FAKES.items():
    for _mod in (hidhide_driver, hh):
        if hasattr(_mod, _name):
            setattr(_mod, _name, _fake)

# The running programs: the LIVE game, and the PTU copy that isn't listed.
process_paths.running_images = lambda: [LIVE, PTU, r"C:\Windows\explorer.exe"]

# The Input Tester link: the real module when it is there, with its launcher
# and paths injected; a stand-in otherwise.
LAUNCHES: list[int] = []
LAUNCH_ANSWER = ["The Input Tester isn't built. From the program folder run: "
                 "python tools/build_input_tester.py"]
RESULT_DIR = WORK / "tester"
RESULT_DIR.mkdir(parents=True, exist_ok=True)


class Watcher(QtCore.QObject):
    resultChanged = QtCore.Signal()


_WATCHER = Watcher()
try:
    link = importlib.import_module("gremlin.input_tester_link")
except ImportError:
    link = types.ModuleType("gremlin.input_tester_link")
    sys.modules["gremlin.input_tester_link"] = link
    import gremlin

    gremlin.input_tester_link = link  # type: ignore[attr-defined]


def _launch() -> str:
    LAUNCHES.append(1)
    return LAUNCH_ANSWER[0]


def _last_result() -> dict | None:
    path = RESULT_DIR / "result.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


link.tester_path = lambda: Path(TESTER)  # type: ignore[attr-defined]
link.tester_dir = lambda: RESULT_DIR  # type: ignore[attr-defined]
link.launch = _launch  # type: ignore[attr-defined]
link.running = lambda: False  # type: ignore[attr-defined]
link.hidhide_changed = lambda *a: None  # type: ignore[attr-defined]
if not hasattr(link, "last_result"):
    link.last_result = _last_result  # type: ignore[attr-defined]
if not hasattr(link, "watcher"):
    link.watcher = lambda: _WATCHER  # type: ignore[attr-defined]

# The saved list: the LIVE game and an old copy of the Input Tester;
# Gremlin control on.
hh._ensure_options()
hh._save_games([
    {"name": "Star Citizen", "path": LIVE},
    {"name": "Gremlin Input Tester", "path": OLD_TESTER},
])
hh._mark_managed()
hh._save_list_mode(True)

import joystick_gremlin  # noqa: E402


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def wait_until(check, timeout: float = 10.0):  # noqa: ANN001, ANN201
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            return None
        QtTest.QTest.qWait(20)


def ev(win: QtCore.QObject, code: str) -> object:
    context = QtQml.qmlContext(win) or QtQml.qmlEngine(win).rootContext()
    expr = QtQml.QQmlExpression(context, win, code)
    value = expr.evaluate()
    if expr.hasError():
        return "error: " + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def items(item: QtQuick.QQuickItem) -> list:
    found = [item]
    for c in item.childItems():
        found += items(c)
    return found


def named(win: QtQuick.QQuickWindow, name: str) -> list:
    return [i for i in items(win.contentItem()) if i.objectName() == name]


def shown(win: QtQuick.QQuickWindow, name: str) -> list[str]:
    return [str(i.property("text")) for i in named(win, name) if i.isVisible()]


def last_status(win: QtQuick.QQuickWindow) -> list[str]:
    return shown(win, "hidHideTesterResult")


def click(win: QtQuick.QQuickWindow, name: str) -> bool:
    found = [i for i in named(win, name) if i.isVisible() and i.isEnabled()]
    if not found:
        return False
    it = found[0]
    QtTest.QTest.qWait(150)  # let a row that just appeared settle
    p = it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2)).toPoint()
    QtTest.QTest.mouseClick(win, Left, NoMod, p)
    QtTest.QTest.qWait(50)
    return True


def open_page(app, root) -> QtQuick.QQuickWindow | None:  # noqa: ANN001
    """The Tools › Device Setup › HidHide menu item."""
    item = next(
        (o for o in root.findChildren(QtCore.QObject)
         if "ThemedMenuItem" in o.metaObject().className()
         and o.property("command") == "tools.hidhide"),
        None,
    )
    if item is None:
        return None
    QtCore.QMetaObject.invokeMethod(item, "triggered")
    win = wait_until(
        lambda: next(
            (w for w in app.topLevelWindows()
             if isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
             and w.title() == "HidHide"),
            None,
        )
    )
    if win is None:
        return None
    win = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)
    win.resize(900, 900)
    QtTest.QTest.qWait(200)
    return win


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_until(lambda: app.engine.rootObjects())[0]
    win = open_page(app, root)
    result("open", win is not None)
    if win is None:
        print("done", flush=True)
        os._exit(0)

    # On open: the PTU copy and the old tester entry are named.
    result("open-state", {
        "games": shown(win, "hidHideGamePathProblem"),
        "tester": shown(win, "hidHideTesterPathProblem"),
        "update": bool(shown(win, "hidHideUpdateTesterPath")),
        "add": bool(shown(win, "hidHideAddTester")),
        "last": shown(win, "hidHideTesterResult"),
    })

    # Update path replaces the old entry with the current one.
    clicked = click(win, "hidHideUpdateTesterPath")
    wait_until(lambda: not shown(win, "hidHideTesterPathProblem"), 3)
    result("update", {
        "clicked": clicked,
        "whitelist": list(DRV.whitelist),
        "tester": shown(win, "hidHideTesterPathProblem"),
        "onList": ev(win, "_hh.testerOnList"),
    })

    # Off the list: Add Input Tester to the list puts it back.
    ev(win, f"_hh.removeGame({json.dumps(TESTER)})")
    wait_until(lambda: shown(win, "hidHideAddTester"), 3)
    before = list(DRV.whitelist)
    clicked = click(win, "hidHideAddTester")
    wait_until(lambda: not shown(win, "hidHideAddTester"), 3)
    result("add", {
        "clicked": clicked,
        "before": before,
        "whitelist": list(DRV.whitelist),
        "addShown": bool(shown(win, "hidHideAddTester")),
    })

    # Input Tester: the launcher is called; its message is shown.
    clicked = click(win, "hidHideOpenTester")
    wait_until(lambda: shown(win, "hidHideTesterMessage"), 3)
    result("launch", {
        "clicked": clicked,
        "launches": len(LAUNCHES),
        "message": shown(win, "hidHideTesterMessage"),
    })

    # A result written by the tester shows on the page.
    (RESULT_DIR / "result.json").write_text(json.dumps({
        "version": 1, "written": "2000-01-01T03:14:22", "verdict": "fail",
        "summary": "1 stick visible that should be hidden", "rows": [],
        "steam": {"running": False, "on_list": False},
    }), encoding="utf-8")
    try:
        link.watcher().resultChanged.emit()
    except Exception:  # noqa: BLE001
        pass  # the 5 s re-read picks it up
    wait_until(lambda: "Problem" in "".join(shown(win, "hidHideTesterResult")), 8)
    result("result", shown(win, "hidHideTesterResult"))
    shots = os.environ.get("HH_TESTER_SHOTS", "")

    # 02 S112 (HS2): the line wraps on its own row; at a narrow window the
    # whole text is there, over more lines, never cut off.
    for name, width in (("wide", 1200), ("narrow", 520)):
        win.resize(width, 900)
        QtTest.QTest.qWait(300)
        label = next(iter(named(win, "hidHideTesterResult")), None)
        button = next(iter(named(win, "hidHideOpenTester")), None)
        if label is None or button is None:
            result(f"layout-{name}", None)
            continue
        lp = label.mapToScene(QtCore.QPointF(0, 0))
        bp = button.mapToScene(QtCore.QPointF(0, 0))
        result(f"layout-{name}", {
            "wrapMode": ev(label, "wrapMode === Text.NoWrap ? 'none' : 'wrap'"),
            "elide": ev(label, "elide === Text.ElideNone ? 'none' : 'elide'"),
            "truncated": bool(label.property("truncated")),
            "lineCount": int(label.property("lineCount")),
            "height": label.height(),
            "below": lp.y() >= bp.y() + button.height(),
            "width": label.width(),
        })
        if shots:
            top = int(bp.y()) - 50
            image = win.grabWindow().copy(0, max(0, top), width, 200)
            image.save(str(Path(shots) / f"{name}.png"))
    win.resize(900, 900)
    QtTest.QTest.qWait(200)

    # 02 S112 (HS4): a HidHide change after the result was written adds the
    # suffix; a result written after the change doesn't have it. (The
    # result above is from 2000; this one from 2099, after any change.)
    record = getattr(link, "record_hidhide_change", None)
    if record is not None:
        record("program list")
    link.watcher().resultChanged.emit()
    wait_until(lambda: "HidHide change" in "".join(last_status(win)), 8)
    result("stale", last_status(win))
    (RESULT_DIR / "result.json").write_text(json.dumps({
        "version": 1, "written": "2099-01-01T06:30:00", "verdict": "pass",
        "summary": "", "rows": [], "steam": {"running": False, "on_list": False},
    }), encoding="utf-8")
    link.watcher().resultChanged.emit()
    wait_until(lambda: "Pass" in "".join(shown(win, "hidHideTesterResult")), 8)
    result("fresh", shown(win, "hidHideTesterResult"))
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
