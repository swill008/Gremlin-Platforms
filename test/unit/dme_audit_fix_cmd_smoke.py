# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor menu bar audit fixes (FIX-CMD) in the real window, off-screen
(stand-in hardware, a temporary user folder): Esc stops drawing whatever has
the keyboard focus (07 S134, G45), a greyed Move to Background / Foreground
row says why (S121), and the table cell rows grey out when the table target
is stale. Prints one "RESULT {json}" line; test_dme_audit_fix_cmd.py runs it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "unit"))
sys.path.insert(0, str(ROOT))

# Never the user's own folder: the pytest side gives a temporary one.
_HOME = Path(os.environ.get("USERPROFILE", "")).resolve()
_USERS = Path(os.environ.get("SystemDrive", "C:") + "/Users")
_REAL_HOME = (_USERS / os.environ.get("USERNAME", "")).resolve()
if (
    not os.environ.get("USERPROFILE")
    or _HOME == _REAL_HOME
    or (os.environ.get("QT_QPA_PLATFORM") != "offscreen")
):
    print("RESULT " + json.dumps({"error": "not a test folder or not off-screen"}))
    sys.exit(2)

spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
from gremlin import clock  # noqa: E402
from gremlin.modules import store  # noqa: E402

STICK = next(d for d in fake.devices if bytes(d.name) == b"pJoy Pro")
GUID = str(dill.GUID(STICK.device_guid).uuid)
NAME = "pJoy Pro"
CARD = {"rawName": NAME, "name": NAME, "guid": GUID}
LIMIT = 15.0
NOT_S = 1.0

DEVICE = store.ensure_device_dir(NAME, GUID)


def chip(hw: int, fx: float) -> dict:
    return {
        "kind": "btn",
        "id": f"b{hw}",
        "hwId": hw,
        "label": f"Button {hw}",
        "chipFx": fx,
        "chipFy": 0.3,
        "hotFx": fx,
        "hotFy": 0.5,
    }


# A picture to place (Arrange › Crop needs one).
PICTURE = _HOME / "pictures" / "pic.png"
PICTURE.parent.mkdir(parents=True, exist_ok=True)

store.module_file_in(DEVICE).write_text(
    json.dumps(
        {
            "kind": "control.hardware",
            "device": NAME,
            "nodes": [chip(1, 0.20), chip(2, 0.30), chip(3, 0.40)],
        }
    ),
    encoding="utf-8",
)

import joystick_gremlin  # noqa: E402


def wait_for(cond: Callable[[], object], limit: float = LIMIT) -> object:
    """Runs the event loop until cond() is true (its value), up to limit."""
    end = clock.monotonic() + limit
    while True:
        value = cond()
        if value or clock.monotonic() > end:
            return value
        QtTest.QTest.qWait(25)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj,
        name,
        QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


# Every row of every menu (submenus too), in order:
# {menu, path, text, hint, enabled}.
_ROWS = (
    "(function() { var out = [];"
    " function walk(m, top, path) { if (!m) return;"
    "  for (var i = 0; i < m.count; i++) { var it = m.itemAt(i);"
    "   if (!it || it.text === undefined || !String(it.text).length) continue;"
    "   if (it.subMenu) { walk(it.subMenu, top,"
    " path.concat([String(it.subMenu.title)]));"
    "    continue }"
    "   out.push({ menu: top, path: path, text: String(it.text),"
    "              hint: String(it.hint || ''), enabled: !!it.enabled }) } }"
    " for (var j = 0; j < _menuBar.count; j++) { var m = _menuBar.menuAt(j);"
    "  walk(m, String(m.title), []) }"
    " return out })()"
)

# A menu row by its top menu and text (submenus too).
_ROW = (
    "(function(title, text) { function find(m) { if (!m) return null;"
    " for (var i = 0; i < m.count; i++) { var it = m.itemAt(i);"
    " if (!it) continue; if (it.subMenu) { var f = find(it.subMenu);"
    " if (f) return f; continue }"
    " if (String(it.text) === text) return it } return null }"
    " for (var j = 0; j < _menuBar.count; j++) { var m = _menuBar.menuAt(j);"
    " if (String(m.title) === title) return find(m) } return null })"
)


class Window:
    def __init__(self, root: QtCore.QObject) -> None:
        self.root = root

    @property
    def win(self) -> QtQuick.QQuickWindow:
        return call(self.root, "deviceMappingEditorWindow")  # type: ignore[return-value]

    def ev(self, code: str) -> object:
        win = self.win
        context = QtQml.qmlContext(win)
        assert context is not None
        expr = QtQml.QQmlExpression(context, win, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(f"{code[:80]}: {expr.error().toString()}")
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def js(self, code: str) -> object:
        text = self.ev(f"JSON.stringify({code})")
        return json.loads(text) if isinstance(text, str) and text else None

    def row(self, menu: str, text: str) -> str:
        return f"{_ROW}({json.dumps(menu)}, {json.dumps(text)})"

    def trigger(self, menu: str, text: str) -> None:
        self.ev(f"{self.row(menu, text)}.triggered()")

    def nodes(self) -> list:
        value = self.js("_ed().nodes")
        return value if isinstance(value, list) else []

    def hist(self) -> int:
        return int(self.ev("_ed().histAt"))  # type: ignore[arg-type]

    def select(self, ids: list[str]) -> None:
        self.ev(f"_ed().setSelection({json.dumps(ids)})")

    def activate(self, window: QtGui.QWindow) -> bool:
        window.requestActivate()
        return bool(wait_for(lambda: QtGui.QGuiApplication.focusWindow() is window, 3))

    def key(
        self,
        key: QtCore.Qt.Key,
        mods: QtCore.Qt.KeyboardModifier = QtCore.Qt.KeyboardModifier.NoModifier,
    ) -> None:
        self.activate(self.win)
        QtTest.QTest.keyClick(self.win, key, mods)
        QtTest.QTest.qWait(150)


from smoke_exit import smoke_exit  # noqa: E402

MSGS: list = []
TAG = [""]


def _handler(mode: QtCore.QtMsgType, ctx: QtCore.QMessageLogContext, msg: str) -> None:
    if "qml" in msg.lower() or ".js" in msg or "TypeError" in msg or "Error" in msg:
        MSGS.append((TAG[0], msg))


def main() -> None:
    QtCore.qInstallMessageHandler(_handler)
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    w = Window(root)
    call(root, "openDeviceMappingEditorForCard", CARD)
    wait_for(lambda: w.win is not None)
    w.win.setProperty("width", 1200)
    w.win.setProperty("height", 800)
    wait_for(
        lambda: w.ev(
            f"_editorWin.targetName === {json.dumps(NAME)} && _editorWin.faceLive"
            " && _ed() !== null && _ed().nodes.length > 0"
        )
    )
    out: dict = {}
    w.ev("_editorWin.enterEdit()")
    wait_for(
        lambda: w.ev(
            "_editorWin.editing && _ed() !== null && _ed().seeded"
            " && !_editorWin._baseWanted"
        )
    )

    def _typed(prefix: str) -> QtQuick.QQuickItem:
        found = []
        win = w.win
        todo = [win.contentItem()]
        while todo:
            o = todo.pop()
            if o.metaObject().className().startswith(prefix):
                found.append(o)
            todo.extend(o.childItems())
        assert len(found) == 1, (prefix, len(found))
        return found[0]

    def _off_map() -> None:
        # The keyboard on the window, not the map (as after a menu click).
        win = w.win
        w.activate(win)
        win.contentItem().forceActiveFocus()

    def ed_ev(code: str) -> object:
        # The editor found by its type each time (a variant from _ed()
        # doesn't keep the C++ object for Python).
        ed = _typed("VkbRigEditor")
        context = QtQml.qmlContext(ed)
        assert context is not None
        expr = QtQml.QQmlExpression(context, ed, f"JSON.stringify({code})")
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(f"{code[:80]}: {expr.error().toString()}")
        value = value[0] if isinstance(value, tuple) else value
        return json.loads(value) if isinstance(value, str) and value else None

    def step(name: str, fn: Callable[[], object]) -> None:
        TAG[0] = name
        try:
            out[name] = fn()
        except Exception as error:  # one step's failure doesn't hide the rest
            out[name] = {"error": repr(error), "tb": traceback.format_exc()[-600:]}

    # 1. Esc stops drawing when the tool came from the menu bar (focus not
    # on the map).
    def esc_from_menu() -> dict:
        w.select([])
        w.trigger("Insert", "Rectangle")
        _off_map()
        tool = w.ev("_ed().drawTool")
        focus = str(w.ev("String(_editorWin.activeFocusItem)"))
        w.key(QtCore.Qt.Key.Key_Escape)
        return {"tool": tool, "focus": focus, "after": w.ev("_ed().drawTool")}

    step("esc_menu", esc_from_menu)

    # 2. Esc with the map focused still stops drawing (and clears a path draft).
    def esc_on_map() -> dict:
        w.ev("_ed().drawTool = 'path'")
        w.ev("_ed().pathDraft = [{x: 10, y: 10}, {x: 40, y: 40}]")
        w.activate(w.win)
        _typed("RigPointerArea").forceActiveFocus()
        focus = str(w.ev("String(_editorWin.activeFocusItem)"))
        w.key(QtCore.Qt.Key.Key_Escape)
        return {
            "focus": focus,
            "after": w.ev("_ed().drawTool"),
            "draft": w.js("_ed().pathDraft.length"),
        }

    step("esc_map", esc_on_map)

    # 3. Background mode: Esc while drawing stops drawing and stays in
    # Background mode; the next Esc leaves it.
    def esc_background() -> dict:
        w.select([])
        w.ev("_editorWin.setEditPlane('background')")
        QtTest.QTest.qWait(50)
        w.ev("_ed().drawTool = 'rect'")
        _off_map()
        QtTest.QTest.qWait(30)
        w.key(QtCore.Qt.Key.Key_Escape)
        first = {"tool": w.ev("_ed().drawTool"), "bg": bool(w.ev("_editorWin.bgMode"))}
        w.key(QtCore.Qt.Key.Key_Escape)
        second = {"bg": bool(w.ev("_editorWin.bgMode"))}
        w.ev("_editorWin.setEditPlane('foreground')")
        return {"first": first, "second": second}

    step("esc_bg", esc_background)

    # 4. Why Move to Background / Foreground is greyed: the menu bar's
    # reason and the right-click menu's tip.
    def why() -> dict:
        w.select(["b1"])
        QtTest.QTest.qWait(30)
        menu = ed_ev("planeMoveItems([selectedId]).map(function(a) { return a.tip })")
        return {
            "back": w.ev("RigCommands.whyDisabled(_ed(), 'moveToBackground')"),
            "front": w.ev("RigCommands.whyDisabled(_ed(), 'moveToForeground')"),
            "other": w.ev("RigCommands.whyDisabled(_ed(), 'flipH')"),
            "menu": menu,
            "enabled": [
                bool(w.ev("_editorWin.cmdOk('moveToBackground')")),
                bool(w.ev("_editorWin.cmdOk('moveToForeground')")),
            ],
        }

    step("why", why)

    # 5. A stale table target (row 3 of another table) on a 2-row table.
    CELL = ["cell.free", "cell.independent", "cell.place.left", "table.deleteCell"]

    def stale() -> dict:
        w.ev(
            "(function(){var e=_ed(); e.addDrawFree('table',"
            " e.fxToX(0.1), e.fyToY(0.1),"
            " e.fxToX(0.4), e.fyToY(0.4)); return true})()"
        )
        ta = str(w.ev("_ed().selectedId"))
        w.ev(
            "(function(){var e=_ed(); e.addDrawFree('table',"
            " e.fxToX(0.5), e.fyToY(0.5),"
            " e.fxToX(0.8), e.fyToY(0.8)); return true})()"
        )
        tb = str(w.ev("_ed().selectedId"))
        w.select([ta])
        w.ev("_ed().tableExtra = -1; _ed().tableRow = 0; _ed().tableCol = 0")
        valid = {i: bool(w.ev(f"_editorWin.cmdOk({json.dumps(i)})")) for i in CELL}
        w.select([tb])
        w.ev("_ed().tableExtra = -1; _ed().tableRow = 7; _ed().tableCol = 1")
        bar = {i: bool(w.ev(f"_editorWin.cmdOk({json.dumps(i)})")) for i in CELL}
        sect = ed_ev(
            "RigMenu._tableSections()"
            ".filter(function(s) { return s.key === 'cell' })[0]"
            ".items.map(function(i) { return [i.text, i.enabled] })"
        )
        w.ev("_ed().tableRow = -1; _ed().tableCol = -1; _ed().tableExtra = 5")
        extra = bool(w.ev("_editorWin.cmdOk('table.deleteCell')"))
        return {"valid": valid, "bar": bar, "menu": sect, "staleExtra": extra}

    step("stale", stale)

    TAG[0] = ""
    out["warnings"] = [m for _, m in MSGS][:20]
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            "RESULT "
            + json.dumps({"error": repr(error), "traceback": traceback.format_exc()}),
            flush=True,
        )
        smoke_exit(1)
