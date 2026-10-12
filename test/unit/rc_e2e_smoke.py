# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's right-click additions and Favourites (07 S136, S137) in
the real window: starts the program off-screen (stand-in hardware, a
temporary user folder), opens a stick's Device Mapping Editor, and drives the
right-click menu (its ☆, Favourites block and ×, Repeat, Cut, Paste Here,
Show in Layers, Properties…) and the menu bar's ☆ with the mouse. Prints one
"RESULT {json}" line; a step that raised is {"error": ...} under its own
key. test_rc_e2e.py runs it; test_rc_carry.py runs it with "carry" (only
the favourites, a save, an Export and a Device Pack).

    python test/unit/rc_e2e_smoke.py [carry]
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
import zipfile
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

CARRY = "carry" in sys.argv[1:]

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
from gremlin.ui import device_map_options  # noqa: E402

# Commands that apply to a selected chip (the Favourites block shows them).
CHIP_CMDS = [
    "edit.cut",
    "edit.copy",
    "edit.duplicate",
    "bringToFront",
    "sendToBack",
    "hide",
    "rename",
]


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


# A menu-bar row by its top menu and text (submenus too).
_ROW = (
    "(function(title, text) { function find(m) { if (!m) return null;"
    " for (var i = 0; i < m.count; i++) { var it = m.itemAt(i);"
    " if (!it) continue; if (it.subMenu) { var f = find(it.subMenu);"
    " if (f) return f; continue }"
    " if (String(it.text) === text) return it } return null }"
    " for (var j = 0; j < _menuBar.count; j++) { var m = _menuBar.menuAt(j);"
    " if (String(m.title) === title) return find(m) } return null })"
)
_MENU = (
    "(function(title) { for (var j = 0; j < _menuBar.count; j++) {"
    " var m = _menuBar.menuAt(j); if (String(m.title) === title) return m }"
    " return null })"
)


def _items(item: QtQuick.QQuickItem) -> list:
    # Rows come and go while the menu rebuilds: skip any already deleted.
    found = [item]
    try:
        children = item.childItems()
    except RuntimeError:
        return found
    for c in children:
        found += _items(c)
    return found


class Window:
    def __init__(self, root: QtCore.QObject) -> None:
        self.root = root

    @property
    def win(self) -> QtQuick.QQuickWindow:
        return call(self.root, "deviceMappingEditorWindow")  # type: ignore[return-value]

    def content(self) -> QtQuick.QQuickItem:
        """The window's content item (its overlay holds the menus)."""
        win = self.win
        self._keep = win
        item = win.contentItem()
        self._keep_item = item
        return item

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

    def nodes(self) -> list:
        return self.js("_ed().nodes") or []

    def ids(self) -> list:
        return [n.get("id") for n in self.nodes()]

    def hist(self) -> int:
        return int(self.ev("_ed().histAt"))  # type: ignore[arg-type]

    def select(self, ids: list[str]) -> None:
        self.ev(f"_ed().setSelection({json.dumps(ids)})")

    def favs(self) -> list:
        return list(self.js("_opts.favourites") or [])

    def set_favs(self, ids: list[str]) -> None:
        for cid in self.favs():
            self.ev(f"_opts.removeFavourite({json.dumps(cid)})")
        for cid in ids:
            self.ev(f"_opts.toggleFavourite({json.dumps(cid)})")
        QtTest.QTest.qWait(50)

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

    # --- mouse ----------------------------------------------------------------

    def _pt(self, x: float, y: float) -> QtCore.QPoint:
        return QtCore.QPoint(round(x), round(y))

    def move(self, p: QtCore.QPoint) -> None:
        QtTest.QTest.mouseMove(self.win, p)
        QtTest.QTest.qWait(60)

    def click(
        self,
        p: QtCore.QPoint,
        button: QtCore.Qt.MouseButton = QtCore.Qt.MouseButton.LeftButton,
    ) -> None:
        self.move(p)
        QtTest.QTest.mouseClick(
            self.win, button, QtCore.Qt.KeyboardModifier.NoModifier, p
        )
        QtTest.QTest.qWait(150)

    def ed_point(self, x: float, y: float) -> QtCore.QPoint:
        p = self.js(
            f"(function() {{ var p = _ed().mapToItem(null, {x}, {y});"
            " return [p.x, p.y] })()"
        )
        assert isinstance(p, list)
        return self._pt(p[0], p[1])

    def box(self, nid: str) -> dict:
        return self.js(f"_ed().nodeBox(_ed().nodeAt({json.dumps(nid)}))") or {}

    def centre(self, nid: str) -> QtCore.QPoint:
        b = self.box(nid)
        return self.ed_point(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)

    def frac_point(self, fx: float, fy: float) -> QtCore.QPoint:
        p = self.js(f"[_ed().fxToX({fx}), _ed().fyToY({fy})]")
        assert isinstance(p, list)
        return self.ed_point(p[0], p[1])

    def right_click(self, p: QtCore.QPoint) -> bool:
        self.close_menu()
        self.click(p, QtCore.Qt.MouseButton.RightButton)
        return bool(wait_for(lambda: self.menu_open(), 3))

    def menu_open(self) -> bool:
        return bool((self.js("_ed().menuBox()") or {}).get("open"))

    def close_menu(self) -> None:
        if self.menu_open():
            self.ev("_ed().closeMenu()")
            wait_for(lambda: not self.menu_open(), 2)

    def menu_lines(self) -> list:
        return list(self.js("_ed().menuLines()") or [])

    def row_rect(self, text: str) -> dict | None:
        r = self.js(f"_ed().menuRowRect({json.dumps(text)})")
        return r if isinstance(r, dict) and r.get("w") else None

    def open_section_with(self, cmd: str) -> None:
        """Opens the right-click menu's section holding the row of cmd."""
        model = (
            self.js(
                "(function() { var m = _ed().menuModel(); var out = [];"
                " (m.sections || []).forEach(function(s) { var cmds = [];"
                " (s.items || []).forEach(function(i) { if (i.cmd) cmds.push(i.cmd) });"
                " out.push({ title: String(s.title || s.label || ''), cmds: cmds }) });"
                " return out })()"
            )
            or []
        )
        for sect in model:
            if cmd in sect["cmds"]:
                r = self.row_rect(sect["title"])
                if r:
                    self.click(self._pt(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2))
                return

    def row_point(self, text: str) -> QtCore.QPoint | None:
        r = self.row_rect(text)
        if not r:
            return None
        return self._pt(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)

    def click_row(self, text: str) -> bool:
        p = self.row_point(text)
        if p is None:
            return False
        self.click(p)
        return True

    def find(self, name: str) -> QtQuick.QQuickItem | None:
        found = self.find_prefix(name)
        return next((it for it in found if it.objectName() == name), None)

    def find_prefix(self, prefix: str) -> list:
        out = []
        for it in _items(self.content()):
            try:
                if it.objectName().startswith(prefix) and it.isVisible():
                    out.append(it)
            except RuntimeError:
                continue
        return out

    def item_point(self, it: QtQuick.QQuickItem) -> QtCore.QPoint:
        p = it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2))
        return self._pt(p.x(), p.y())

    def click_item(self, it: QtQuick.QQuickItem) -> None:
        self.click(self.item_point(it))

    def fav_rows(self) -> list:
        """The Favourites block's rows top to bottom, by command id."""
        rows = self.find_prefix("ctxFavRow_")
        rows.sort(key=lambda it: it.mapToScene(QtCore.QPointF(0, 0)).y())
        return [it.objectName()[len("ctxFavRow_") :] for it in rows]

    def star_ctx(self, nid: str, cmd: str) -> dict:
        """Right-clicks nid, hovers cmd's row and clicks its ☆."""
        self.select([nid])
        self.right_click(self.centre(nid))
        text = (self.js(f"_ed().cmdInfo({json.dumps(cmd)})") or {}).get("text", "")
        p = self.row_point(text)
        if p is None:
            self.open_section_with(cmd)
            p = self.row_point(text)
        res: dict = {"text": text, "row": p is not None}
        if p is None:
            return res
        self.move(p)
        star = wait_for(lambda: self.find(f"ctxStar_{cmd}"), 2)
        res["star"] = star is not None
        if star is None:
            return res
        before = [self.nodes(), self.hist()]
        self.click_item(star)  # type: ignore[arg-type]
        res["ran-nothing"] = [self.nodes(), self.hist()] == before
        res["menu-open"] = self.menu_open()
        return res

    def star_bar(self, menu: str, text: str, cid: str) -> dict:
        """Opens a menu-bar menu, hovers the row and clicks its ☆."""
        self.ev(f"{_MENU}({json.dumps(menu)}).open()")
        QtTest.QTest.qWait(200)
        row = self.ev(f"{_ROW}({json.dumps(menu)}, {json.dumps(text)})")
        res: dict = {"row": isinstance(row, QtQuick.QQuickItem)}
        if not isinstance(row, QtQuick.QQuickItem):
            self.ev(f"{_MENU}({json.dumps(menu)}).close()")
            return res
        self.move(self.item_point(row))
        star = wait_for(
            lambda: next(
                (
                    c
                    for c in _items(row)
                    if c.objectName() == f"dmeStar_{cid}" and c.isVisible()
                ),
                None,
            ),
            2,
        )
        res["star"] = star is not None
        if star is not None:
            before = [self.nodes(), self.hist()]
            self.click_item(star)  # type: ignore[arg-type]
            res["ran-nothing"] = [self.nodes(), self.hist()] == before
        self.ev(f"{_MENU}({json.dumps(menu)}).close()")
        QtTest.QTest.qWait(100)
        return res


def open_window(root: QtCore.QObject, w: Window) -> None:
    call(root, "openDeviceMappingEditorForCard", CARD)
    wait_for(lambda: w.win is not None)
    w.win.setProperty("width", 1300)
    w.win.setProperty("height", 860)
    wait_for(
        lambda: w.ev(
            f"_editorWin.targetName === {json.dumps(NAME)} && _editorWin.faceLive"
            " && _ed() !== null && _ed().nodes.length > 0"
        )
    )
    w.ev("_editorWin.enterEdit()")
    wait_for(
        lambda: w.ev(
            "_editorWin.editing && _ed() !== null && _ed().seeded &&"
            " !_editorWin._baseWanted"
        )
    )


def carry(
    w: Window, out: dict, step: Callable[[str, Callable[[], object]], None]
) -> None:
    """Favourites are a program setting: a saved map, an Export (.gmap) and a
    Device Pack never hold them."""
    w.set_favs([])

    def add() -> dict:
        res = {
            "ctx": w.star_ctx("b1", "edit.cut"),
            "bar": w.star_bar("Arrange", "Bring to Front", "bringToFront"),
        }
        w.close_menu()
        w.ev("_opts.toggleFavourite('hide')")
        res["favs"] = w.favs()
        return res

    step("carry-add", add)

    def save() -> dict:
        # A change so the save writes.
        w.select(["b2"])
        w.ev("_ed().nodeAt('b2').label = 'Saved'; _ed().bump()")
        w.ev("_editorWin.saveEdit()")
        wait_for(lambda: not w.ev("_editorWin.editing"), 5)
        path = store.module_file_in(DEVICE)
        text = path.read_text(encoding="utf-8")
        return {"path": str(path), "text": text, "saved": "Saved" in text}

    step("carry-module", save)

    def gmap() -> dict:
        from gremlin.modules import device_zip

        dest = _HOME / "out" / "map.gmap"
        dest.parent.mkdir(parents=True, exist_ok=True)
        err = device_zip.export_device(NAME, GUID, dest, None)
        return {"error": err, "files": _zip_texts(dest) if not err else {}}

    step("carry-gmap", gmap)

    def pack() -> dict:
        from gremlin.ui import hardware_profile

        # Export / Import Device writes a .gmap (D-FIXLIST-B2).
        dest = _HOME / "out" / "pack.gmap"
        dest.parent.mkdir(parents=True, exist_ok=True)
        hw = hardware_profile.HardwareProfile()
        url = QtCore.QUrl.fromLocalFile(str(dest)).toString()
        done = json.loads(hw.exportPack(NAME, url, json.dumps({"guid": GUID})))
        written = Path(done.get("path") or dest)
        return {"done": done, "files": _zip_texts(written) if written.is_file() else {}}

    step("carry-pack", pack)

    # The program's settings file holds them (a program setting).
    step(
        "carry-setting",
        lambda: {
            "stored": device_map_options.favourites(),
            "files": {
                str(p.relative_to(_HOME)): p.read_text(
                    encoding="utf-8", errors="replace"
                )
                for p in (_HOME / "Gremlin Platforms").glob("*.json")
            },
        },
    )


def _zip_texts(path: Path) -> dict:
    out = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith((".json", ".txt", ".xml", ".gmap")):
                out[name] = zf.read(name).decode("utf-8", errors="replace")
    return out


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    w = Window(root)
    out: dict = {}

    def step(name: str, fn: Callable[[], object]) -> None:
        try:
            out[name] = fn()
        except Exception as error:
            out[name] = {"error": repr(error), "traceback": traceback.format_exc()}
        try:
            w.close_menu()
        except Exception:
            pass

    open_window(root, w)
    out["editing"] = bool(w.ev("_editorWin.editing"))

    if CARRY:
        carry(w, out, step)
        print("RESULT " + json.dumps(out), flush=True)
        smoke_exit(0)
        return

    # --- the contract's names are there -----------------------------------
    step(
        "api",
        lambda: w.js(
            "(function() { var e = _ed(); return {"
            " opts: [typeof _opts.favourites, typeof _opts.favouritesShown,"
            "  typeof _opts.toggleFavourite, typeof _opts.removeFavourite],"
            " ed: [typeof e.favourites, typeof e.favouritesShown,"
            "  typeof e.lastCommandId, typeof e.cutSelection, typeof e.pasteAt,"
            "  typeof e.cmdApplies, typeof e.cmdInfo, typeof e.cmdRun,"
            "  typeof e.cmdRepeatLabel, typeof e.cmdCanRepeat, typeof e.cmdRepeat],"
            " cmd: [typeof RigCommands.info, typeof RigCommands.applies,"
            "  typeof RigCommands.noteRun, typeof RigCommands.repeatLabel,"
            "  typeof RigCommands.canRepeat, typeof RigCommands.repeat],"
            " shown: _opts.favouritesShown, edShown: e.favouritesShown,"
            " layers: typeof _layersPanel.revealNode } })()"
        ),
    )
    w.set_favs([])

    # --- ☆ in the right-click menu and in the menu bar adds; order kept ----
    def add() -> dict:
        res = {"ctx": w.star_ctx("b1", "edit.cut")}
        w.close_menu()
        res["after-ctx"] = w.favs()
        res["bar"] = w.star_bar("Arrange", "Bring to Front", "bringToFront")
        res["after-bar"] = w.favs()
        res["bar-edit"] = w.star_bar("Edit", "Duplicate", "edit.duplicate")
        res["after-bar-edit"] = w.favs()
        res["ed-favs"] = w.js("_ed().favourites")
        # The block at the top, in the order added.
        w.select(["b1"])
        w.right_click(w.centre("b1"))
        res["block"] = w.find("ctxFavourites") is not None
        res["rows"] = w.fav_rows()
        res["model"] = [
            f.get("cmd") for f in (w.js("_ed().menuModel().favourites") or [])
        ]
        res["lines"] = w.menu_lines()
        # ★ on a favourite's own row: clicking it again takes it off.
        return res

    step("add", add)

    # --- a favourite row runs; × removes, the menu stays open --------------
    def remove() -> dict:
        res: dict = {}
        w.select(["b1"])
        w.right_click(w.centre("b1"))
        n = len(w.ids())
        at = w.hist()
        row = w.find("ctxFavRow_edit.duplicate")
        res["row"] = row is not None
        if row is not None:
            w.click_item(row)
            res["ran"] = len(w.ids()) == n + 1 and w.hist() == at + 1
            w.ev("_ed().undo()")
        w.select(["b1"])
        w.right_click(w.centre("b1"))
        first = w.find("ctxFavRow_bringToFront")
        if first is not None:
            w.move(w.item_point(first))
        x = wait_for(lambda: w.find("ctxFavRemove_bringToFront"), 2)
        res["x"] = x is not None
        if x is not None:
            before = [w.nodes(), w.hist()]
            w.click_item(x)  # type: ignore[arg-type]
            res["ran-nothing"] = [w.nodes(), w.hist()] == before
            res["menu-open"] = w.menu_open()
            res["rows"] = w.fav_rows()
        res["favs"] = w.favs()
        return res

    step("remove", remove)

    # --- only what applies shows -------------------------------------------
    def applies() -> dict:
        w.set_favs(["table.idCol", "edit.duplicate", "flipH"])
        w.select(["b1"])
        w.right_click(w.centre("b1"))
        res = {
            "rows": w.fav_rows(),
            "applies": {
                c: bool(w.ev(f"_ed().cmdApplies({json.dumps(c)})"))
                for c in ("table.idCol", "edit.duplicate", "flipH")
            },
        }
        w.set_favs(["table.idCol"])
        w.right_click(w.centre("b1"))
        res["none-block"] = w.find("ctxFavourites") is not None
        res["none-model"] = w.js("_ed().menuModel().favourites")
        return res

    step("applies", applies)

    # --- the count option: 0 / 2 / 5 ---------------------------------------
    def counts() -> dict:
        w.set_favs(CHIP_CMDS)
        res: dict = {"favs": w.favs()}
        for n in (0, 2, 5):
            w.ev(f"_opts.set('favourites-shown', {n})")
            QtTest.QTest.qWait(80)
            w.select(["b1"])
            w.right_click(w.centre("b1"))
            res[str(n)] = {
                "opt": w.ev("_opts.favouritesShown"),
                "ed": w.ev("_ed().favouritesShown"),
                "rows": w.fav_rows(),
                "block": w.find("ctxFavourites") is not None,
            }
        w.ev("_opts.set('favourites-shown', 5)")
        return res

    step("counts", counts)

    # --- Repeat after a menu, a right-click and a key ----------------------
    def repeat() -> dict:
        res: dict = {}
        w.ev("_ed().lastCommandId = ''")
        # Menu bar: Arrange › Bring to Front.
        w.select(["b1"])
        w.ev(f"{_ROW}('Arrange', 'Bring to Front').triggered()")
        wait_for(lambda: w.ev("_ed().lastCommandId"), 3)
        res["menu"] = [w.ev("_ed().lastCommandId"), w.ev("_ed().cmdRepeatLabel()")]
        w.right_click(w.centre("b1"))
        res["menu-first-row"] = (w.menu_lines() or [])[:3]
        label = str(w.ev("_ed().cmdRepeatLabel()"))
        res["menu-row"] = w.row_rect(label) is not None
        # Copy does not change it.
        w.close_menu()
        w.key(QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier)
        res["after-copy"] = w.ev("_ed().lastCommandId")
        # Right-click › Cut (no favourites, so the row is the menu's own).
        w.set_favs([])
        w.select(["b1"])
        w.right_click(w.centre("b1"))
        res["cut-clicked"] = w.click_row("Cut")
        res["cut-ran"] = "b1" not in w.ids()
        res["right-click"] = w.ev("_ed().lastCommandId")
        w.close_menu()
        w.ev("_ed().undo()")
        # A key: Ctrl+] (Bring Forward) on b1.
        w.select(["b1"])
        w.ev("_ed().lastCommandId = ''")
        w.key(
            QtCore.Qt.Key.Key_BracketRight, QtCore.Qt.KeyboardModifier.ControlModifier
        )
        res["key"] = w.ev("_ed().lastCommandId")
        # Ctrl+A (Select All) does not change it.
        w.key(QtCore.Qt.Key.Key_A, QtCore.Qt.KeyboardModifier.ControlModifier)
        res["after-select-all"] = w.ev("_ed().lastCommandId")
        # The Repeat row runs it again: one more step.
        w.ev("_ed().lastCommandId = 'bringToFront'")
        w.select(["b2"])
        w.right_click(w.centre("b2"))
        label = str(w.ev("_ed().cmdRepeatLabel()"))
        res["label"] = label
        at = w.hist()
        before = w.ids()
        res["repeat-clicked"] = w.click_row(label)
        after = w.ids()
        res["repeat-ran"] = w.hist() == at + 1 and after.index("b2") > before.index(
            "b2"
        )
        w.close_menu()
        w.ev("_ed().undo()")
        return res

    step("repeat", repeat)

    # --- Cut: one Undo step --------------------------------------------------
    def cut() -> dict:
        w.select(["b3"])
        w.right_click(w.centre("b3"))
        before = w.nodes()
        at = w.hist()
        res = {"clicked": w.click_row("Cut")}
        res["gone"] = "b3" not in w.ids()
        res["copied"] = [n.get("id") for n in (w.js("_ed().copiedNodes") or [])]
        res["steps"] = w.hist() - at
        w.close_menu()
        w.ev("_ed().undo()")
        res["undone"] = w.nodes() == before
        return res

    step("cut", cut)

    # --- Paste Here: the copied items' centre on the spot right-clicked ----
    def paste_here() -> dict:
        w.select(["b1", "b2"])
        w.ev("_ed().copySelection()")
        w.select([])
        spot = w.frac_point(0.75, 0.75)
        w.right_click(spot)
        before = set(w.ids())
        at = w.hist()
        res: dict = {"clicked": w.click_row("Paste Here")}
        new = [i for i in w.ids() if i not in before]
        res["new"] = len(new)
        res["steps"] = w.hist() - at
        res["selected"] = sorted(w.js("_ed().selectedIds") or []) == sorted(new)
        if new:
            boxes = [w.box(i) for i in new]
            x0 = min(b["x"] for b in boxes)
            y0 = min(b["y"] for b in boxes)
            x1 = max(b["x"] + b["w"] for b in boxes)
            y1 = max(b["y"] + b["h"] for b in boxes)
            want = w.js("[_ed().fxToX(0.75), _ed().fyToY(0.75)]") or [0, 0]
            res["centre"] = [(x0 + x1) / 2, (y0 + y1) / 2]
            res["want"] = want
        w.close_menu()
        if res["steps"]:
            w.ev("_ed().undo()")
        return res

    step("paste-here", paste_here)

    # --- Show in Layers ------------------------------------------------------
    def show_in_layers() -> dict:
        w.ev("_layersSide.pinned = false; _layersSide.open = false")
        QtTest.QTest.qWait(100)
        w.select(["b2"])
        w.right_click(w.centre("b2"))
        res: dict = {"clicked": w.click_row("Show in Layers")}
        wait_for(
            lambda: w.ev("_layersSide.open")
            and w.ev("_layersPanel.revealedId") == "b2"
            and (w.js("_layersPanel.revealedRow()") or {}).get("inView"),
            3,
        )
        res["open"] = w.ev("_layersSide.open")
        res["revealed"] = w.ev("_layersPanel.revealedId")
        res["row"] = w.js("_layersPanel.revealedRow()")
        return res

    step("show-in-layers", show_in_layers)

    # --- Properties… ---------------------------------------------------------
    def properties() -> dict:
        w.ev("_editorWin.propsOn = false")
        w.ev("_layersSide.pinned = false; _layersSide.open = false")
        QtTest.QTest.qWait(100)
        w.select(["b2"])
        w.right_click(w.centre("b2"))
        res: dict = {"clicked": w.click_row("Properties…")}
        wait_for(lambda: w.ev("_editorWin.propsShown"), 3)
        res["props-on"] = w.ev("_editorWin.propsOn")
        res["layers-open"] = w.ev("_layersSide.open")
        res["shown"] = w.ev("_editorWin.propsShown")
        return res

    step("properties", properties)

    # --- Reset Panels keeps them; the next window has them ------------------
    def kept() -> dict:
        w.set_favs(["edit.duplicate", "bringToFront", "hide"])
        w.ev(f"{_ROW}('View', 'Reset Panels').triggered()")
        QtTest.QTest.qWait(100)
        res: dict = {"after-reset": w.favs()}
        w.ev("_editorWin.discardEdit()")
        wait_for(lambda: not w.ev("_editorWin.editing"), 5)
        w.win.close()
        QtTest.QTest.qWait(300)
        open_window(root, w)
        res["next-window"] = w.js("_ed().favourites")
        res["stored"] = device_map_options.favourites()
        w.select(["b1"])
        w.right_click(w.centre("b1"))
        res["rows"] = w.fav_rows()
        return res

    step("kept", kept)

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
