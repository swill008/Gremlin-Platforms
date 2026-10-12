# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor window's part of the right-click additions (07 S136,
S137) in the real window, off-screen (stand-in hardware, a temporary user
folder): the star on menu-bar rows, Edit rows and keys through
rig_commands.js (Repeat sees them), the favourites store wiring, Show in
Layers and Properties. Prints one "RESULT {json}" line. test_rc_win.py runs
it.

    python test/unit/rc_win_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
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

from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

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
            # Enough rows that Layers scrolls (Show in Layers).
            "nodes": [chip(i, 0.05 + 0.03 * i) for i in range(1, 31)],
        }
    ),
    encoding="utf-8",
)

import joystick_gremlin  # noqa: E402
from gremlin.ui import device_map_options  # noqa: E402


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
    def win(self) -> QtGui.QWindow:
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
        return self.js("_ed().nodes") or []

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




# The star under a menu row (made by the window's addStar), or null.
_STAR = (
    "(function(r) { if (!r) return null; for (var i = 0; i < r.children.length; i++) {"
    " var c = r.children[i]; if (String(c.objectName).indexOf('dmeStar_') === 0)"
    " return c } return null })"
)

EDIT_ROWS = {
    "Cut": "edit.cut",
    "Copy": "edit.copy",
    "Paste": "edit.paste",
    "Duplicate": "edit.duplicate",
    "Delete": "edit.delete",
    "Select All": "edit.selectAll",
}

# The Edit menu itself.
_EDIT_MENU = (
    "(function() { for (var j = 0; j < _menuBar.count; j++)"
    " if (String(_menuBar.menuAt(j).title) === 'Edit')"
    " return _menuBar.menuAt(j); return null })()"
)


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    small = QtGui.QImage(40, 20, QtGui.QImage.Format.Format_RGB32)
    small.fill(QtGui.QColor("#a05020"))
    small.save(str(PICTURE))
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    w = Window(root)
    out: dict = {}

    def step(name: str, fn: Callable[[], object]) -> None:
        try:
            out[name] = fn()
        except Exception as error:
            out[name] = {"error": repr(error), "traceback": traceback.format_exc()}

    call(root, "openDeviceMappingEditorForCard", CARD)
    wait_for(lambda: w.win is not None)
    w.win.setProperty("width", 1200)
    w.win.setProperty("height", 700)
    wait_for(
        lambda: w.ev(
            f"_editorWin.targetName === {json.dumps(NAME)} && _editorWin.faceLive"
            " && _ed() !== null && _ed().nodes.length > 0"
        )
    )
    w.ev("_editorWin.enterEdit()")
    out["editing"] = bool(
        wait_for(
            lambda: w.ev(
                "_editorWin.editing && _ed() !== null && _ed().seeded &&"
                " !_editorWin._baseWanted"
            )
        )
    )

    # --- the star on the six Edit rows and a command row ----------------------
    def stars() -> dict:
        res: dict = {}
        for text, cid in EDIT_ROWS.items():
            res[cid] = w.ev(f"String(({_STAR})({w.row('Edit', text)}).objectName)")
        res["bringToFront"] = w.ev(
            f"String(({_STAR})({w.row('Arrange', 'Bring to Front')}).objectName)"
        )
        return res

    step("stars", stars)

    # --- a click on the star toggles the favourite and runs nothing ----------
    def star_click() -> dict:
        res: dict = {}
        w.select(["b1"])
        before = [w.nodes(), w.hist()]
        w.activate(w.win)
        w.ev(f"{_EDIT_MENU}.open()")
        wait_for(lambda: w.ev(f"{_EDIT_MENU}.opened"), 3)
        QtTest.QTest.qWait(300)
        row = w.row("Edit", "Duplicate")
        # Hover the row, then click its star.
        pt = w.js(
            f"(function() {{ var r = {row}; var p = r.mapToItem(null, r.width / 2,"
            " r.height / 2); return [p.x, p.y] })()"
        )
        # A few steps, so the window sees the pointer arrive.
        for dx in (-30, -15, 0):
            QtTest.QTest.mouseMove(w.win, QtCore.QPoint(int(pt[0]) + dx, int(pt[1])))
            QtTest.QTest.qWait(80)
        res["shown-on-hover"] = bool(w.ev(f"({_STAR})({row}).visible"))
        sp = w.js(
            f"(function() {{ var s = ({_STAR})({row}); var p = s.mapToItem(null,"
            " s.width / 2, s.height / 2); return [p.x, p.y] })()"
        )
        QtTest.QTest.mouseClick(
            w.win,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            QtCore.QPoint(int(sp[0]), int(sp[1])),
        )
        QtTest.QTest.qWait(200)
        res["stored"] = list(device_map_options.favourites())
        res["editor"] = w.js("_ed().favourites")
        res["star-text"] = w.ev(f"({_STAR})({row}).text")
        res["ran-nothing"] = [w.nodes(), w.hist()] == before
        w.ev(f"{_EDIT_MENU}.close()")
        # A second toggle (what the click runs) takes it off again.
        w.ev(f"({_STAR})({row}).toggle()")
        res["after-second"] = list(device_map_options.favourites())
        # The editor's own signals reach the store.
        w.ev("_ed().favouriteToggled('rotatePlus')")
        res["from-editor"] = list(device_map_options.favourites())
        res["editor-after"] = w.js("_ed().favourites")
        w.ev("_ed().favouriteRemoved('rotatePlus')")
        res["removed-from-editor"] = list(device_map_options.favourites())
        res["shown-count"] = w.ev("_ed().favouritesShown")
        return res

    step("star", star_click)

    # --- Edit rows and keys go through rig_commands.js (Repeat sees them) -----
    def through_commands() -> dict:
        res: dict = {}
        ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        w.ev("_ed().lastCommandId = ''")
        w.select(["b2"])
        w.trigger("Edit", "Duplicate")
        wait_for(lambda: w.ev("_ed().lastCommandId"), 3)
        res["menu-duplicate"] = w.ev("_ed().lastCommandId")
        w.ev("_ed().undo()")
        w.ev("_ed().lastCommandId = ''")
        w.select(["b2"])
        w.key(QtCore.Qt.Key.Key_D, ctrl)
        res["key-duplicate"] = w.ev("_ed().lastCommandId")
        w.ev("_ed().undo()")
        w.ev("_ed().lastCommandId = ''")
        w.select(["b2"])
        w.key(QtCore.Qt.Key.Key_L, ctrl)
        res["key-lock"] = w.ev("_ed().lastCommandId")
        w.ev("_ed().undo()")
        w.ev("_ed().lastCommandId = ''")
        w.select(["b2"])
        at = w.hist()
        count = len(w.nodes())
        w.trigger("Edit", "Cut")
        wait_for(lambda: w.ev("_ed().lastCommandId"), 3)
        res["menu-cut"] = w.ev("_ed().lastCommandId")
        res["cut-steps"] = w.hist() - at
        res["cut-removed"] = count - len(w.nodes())
        w.ev("_ed().undo()")
        w.ev("_ed().lastCommandId = ''")
        w.select(["b3"])
        w.key(QtCore.Qt.Key.Key_Delete)
        res["key-delete"] = w.ev("_ed().lastCommandId")
        w.ev("_ed().undo()")
        w.select([])
        w.key(QtCore.Qt.Key.Key_A, ctrl)
        res["key-select-all"] = len(w.js("_ed().selectedIds") or [])
        w.select([])
        return res

    step("commands", through_commands)

    # --- Show in Layers: unfold, scroll to, light the row ---------------------
    def show_in_layers() -> dict:
        res: dict = {}
        w.ev("_layersSide.fold()")
        wait_for(lambda: not w.ev("_layersSide.open"), 3)
        res["folded"] = not w.ev("_layersSide.open")
        # b1 is first in the file: the bottom of the stack, the last row.
        w.ev("_ed().showInLayersRequested('b1')")
        wait_for(lambda: w.ev("_layersSide.open"), 3)
        QtTest.QTest.qWait(300)
        res["open"] = bool(w.ev("_layersSide.open"))
        res["revealed"] = w.js("_layersPanel.revealedRow()")
        res["revealed-id"] = w.ev("_layersPanel.revealedId")
        # A search that hides the row is cleared.
        w.ev("_layersPanel.searchText = 'Button 30'")
        QtTest.QTest.qWait(50)
        w.ev("_ed().showInLayersRequested('b2')")
        QtTest.QTest.qWait(300)
        res["search-cleared"] = w.ev("_layersPanel.searchText") == ""
        res["revealed-2"] = w.js("_layersPanel.revealedRow()")
        return res

    step("show-in-layers", show_in_layers)

    # --- Properties...: Layers with Properties shown --------------------------
    def properties() -> dict:
        res: dict = {}
        w.ev("_editorWin.propsOn = false")
        w.ev("_layersSide.fold()")
        w.select(["b3"])
        w.ev("_ed().propertiesRequested()")
        wait_for(lambda: w.ev("_editorWin.propsShown"), 3)
        res["open"] = bool(w.ev("_layersSide.open"))
        res["propsOn"] = bool(w.ev("_editorWin.propsOn"))
        res["propsShown"] = bool(w.ev("_editorWin.propsShown"))
        w.select([])
        return res

    step("properties", properties)

    w.ev("_editorWin.discardEdit()")
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
