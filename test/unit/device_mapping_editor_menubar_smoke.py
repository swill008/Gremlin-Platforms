# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's menu bar (07 S98-S100, S133-S135) in the real window:
starts the program off-screen (stand-in hardware, a temporary user folder),
opens a stick's Device Mapping Editor, and drives its menus, keys, Device Map Options
and Keyboard Shortcuts windows. Prints one "RESULT {json}" line; a step that
raised is {"error": ...} under its own key. test_device_mapping_editor_menubar.py runs
it (with Qt's messages on the error stream, which it reads for warnings).

    python test/unit/device_mapping_editor_menubar_smoke.py
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
    w.win.setProperty("height", 800)
    wait_for(
        lambda: w.ev(
            f"_editorWin.targetName === {json.dumps(NAME)} && _editorWin.faceLive"
            " && _ed() !== null && _ed().nodes.length > 0"
        )
    )

    # --- S135: the menus in order; outside Edit ------------------------------
    step(
        "titles",
        lambda: w.js(
            "(function() { var t = []; for (var i = 0; i < _menuBar.count; i++)"
            " t.push(String(_menuBar.menuAt(i).title)); return t })()"
        ),
    )
    step("live-rows", lambda: w.js(_ROWS))

    w.ev("_editorWin.enterEdit()")
    out["editing"] = bool(
        wait_for(
            lambda: w.ev(
                "_editorWin.editing && _ed() !== null && _ed().seeded &&"
                " !_editorWin._baseWanted"
            )
        )
    )

    # --- S135 Edit › Background; every row and its hint while editing --------
    step(
        "background",
        lambda: w.js(
            "(function() { var r = []; for (var i = 0; i < _bgMenu.count; i++) {"
            " var it = _bgMenu.itemAt(i); if (it && it.text) r.push(String(it.text)) }"
            " return r })()"
        ),
    )
    step(
        "commands",
        lambda: w.js(
            "RigCommands.list(_ed()).filter(function(c) { return c.id !== '-' })"
        ),
    )

    # --- S134: greyed with no selection, enabled with a matching one ---------
    ids = [
        "bringToFront",
        "hide",
        "rename",
        "addLeader",
        "flipH",
        "copyFormat",
        "editText",
        "importPicture",
    ]

    def states() -> dict:
        # The menu rows' own enabled, and the command list's.
        rows = {f"{r['menu']}/{r['text']}": r["enabled"] for r in (w.js(_ROWS) or [])}
        cmds = {
            c["id"]: f"{c['menu']}/{c['text']}"
            for c in (w.js("RigCommands.list(_ed())") or [])
            if c["id"] in ids
        }
        return {cid: rows.get(cmds.get(cid, ""), "missing") for cid in ids}

    def enabled_states() -> dict:
        res: dict = {}
        w.select([])
        res["none"] = states()
        w.select(["b1"])
        res["chip"] = states()
        # A rectangle and a text box, drawn on the map.
        w.ev(
            "(function() { var e = _ed(); e.addDrawFree('rect', e.fxToX(0.6),"
            " e.fyToY(0.6),"
            " e.fxToX(0.7), e.fyToY(0.7)); return true })()"
        )
        res["rect-id"] = w.ev("_ed().selectedId")
        res["rect"] = states()
        w.ev(
            "(function() { var e = _ed(); e.addDrawFree('text', e.fxToX(0.6),"
            " e.fyToY(0.2),"
            " e.fxToX(0.8), e.fyToY(0.3)); return true })()"
        )
        res["text-id"] = w.ev("_ed().selectedId")
        res["text"] = states()
        w.select([])
        return res

    step("enabled", enabled_states)
    rect_id = (out.get("enabled") or {}).get("rect-id", "")
    text_id = (out.get("enabled") or {}).get("text-id", "")

    # --- S134: one run per kind, each one Undo step --------------------------
    def one_step(
        select: list[str], menu: str, text: str, check: Callable[[list, list], bool]
    ) -> dict:
        w.select(select)
        before = w.nodes()
        at = w.hist()
        w.trigger(menu, text)
        QtTest.QTest.qWait(50)
        after = w.nodes()
        steps = w.hist() - at
        w.ev("_ed().undo()")
        return {
            "changed": check(before, after),
            "steps": steps,
            "undone": w.nodes() == before,
        }

    def ids_of(nodes: list) -> list:
        return [n.get("id") for n in nodes]

    def node(nodes: list, nid: str) -> dict:
        return next((n for n in nodes if n.get("id") == nid), {})

    step(
        "bring-to-front",
        lambda: one_step(
            ["b1"],
            "Arrange",
            "Bring to Front",
            lambda b, a: (
                ids_of(a) != ids_of(b) and ids_of(a).index("b1") > ids_of(b).index("b1")
            ),
        ),
    )
    step(
        "flip-h",
        lambda: one_step(
            [rect_id],
            "Arrange",
            "Flip Horizontally",
            lambda b, a: (
                bool(node(a, rect_id).get("flipH"))
                != bool(node(b, rect_id).get("flipH"))
            ),
        ),
    )
    step(
        "add-leader",
        lambda: one_step(
            ["b2"],
            "Leader",
            "Add Leader",
            lambda b, a: (
                len(node(a, "b2").get("leaders") or [])
                > len(node(b, "b2").get("leaders") or [])
            ),
        ),
    )

    def format_copy() -> dict:
        # Copy Format changes nothing (no step); Paste Format onto a second
        # text box is one step.
        w.select([text_id])
        w.ev("_ed().nodeAt(" + json.dumps(text_id) + ").fontSize = 30; _ed().bump()")
        at = w.hist()
        w.trigger("Format", "Copy Format")
        copied = w.hist() - at
        w.ev(
            "(function() { var e = _ed(); e.addDrawFree('text', e.fxToX(0.1),"
            " e.fyToY(0.7),"
            " e.fxToX(0.3), e.fyToY(0.8)); return true })()"
        )
        other = w.ev("_ed().selectedId")
        res = one_step(
            [other],
            "Format",
            "Paste Format",
            lambda b, a: (
                node(a, other).get("fontSize") == 30
                and node(b, other).get("fontSize") != 30
            ),
        )
        res["copy-steps"] = copied
        return res

    step("paste-format", format_copy)

    # --- S135: Cut = Copy then Delete, one Undo step --------------------------
    def cut() -> dict:
        w.select(["b3"])
        before = w.nodes()
        at = w.hist()
        w.trigger("Edit", "Cut")
        QtTest.QTest.qWait(50)
        res = {
            "gone": "b3" not in ids_of(w.nodes()),
            "copied": [n.get("id") for n in (w.js("_ed().copiedNodes") or [])],
            "steps": w.hist() - at,
        }
        w.ev("_ed().undo()")
        res["undone"] = w.nodes() == before
        return res

    step("cut", cut)

    # --- S133: Select All: the edited plane's items ---------------------------
    def select_all() -> dict:
        w.select([])
        w.trigger("Edit", "Select All")
        got = sorted(w.js("_ed().selectedIds") or [])
        want = sorted(
            w.js(
                "_ed().nodes.filter(function(n) { var e = _ed(); return"
                " e.inEditPlane(n)"
                " && !e.isHidden(n) && !e.isLocked(n) }).map(function(n) { return n.id"
                " })"
            )
            or []
        )
        # Ctrl+A does the same.
        w.select([])
        w.key(QtCore.Qt.Key.Key_A, QtCore.Qt.KeyboardModifier.ControlModifier)
        by_key = sorted(w.js("_ed().selectedIds") or [])
        w.select([])
        return {
            "menu": got,
            "want": want,
            "key": by_key,
            "has-chips": all(c in got for c in ("b1", "b2", "b3")),
        }

    step("select-all", select_all)

    # --- S133: Zoom In / Zoom Out ---------------------------------------------
    def zoom() -> dict:
        w.ev("_ed().face.resetView()")
        start = float(w.ev("_ed().face.viewPct"))  # type: ignore[arg-type]
        w.trigger("View", "Zoom In")
        zin = float(w.ev("_ed().face.viewPct"))  # type: ignore[arg-type]
        w.trigger("View", "Zoom Out")
        zout = float(w.ev("_ed().face.viewPct"))  # type: ignore[arg-type]
        w.key(QtCore.Qt.Key.Key_Equal, QtCore.Qt.KeyboardModifier.ControlModifier)
        key_in = float(w.ev("_ed().face.viewPct"))  # type: ignore[arg-type]
        w.key(QtCore.Qt.Key.Key_Minus, QtCore.Qt.KeyboardModifier.ControlModifier)
        key_out = float(w.ev("_ed().face.viewPct"))  # type: ignore[arg-type]
        w.ev("_ed().face.resetView()")
        return {
            "in": zin > start,
            "out": zout < zin,
            "back": abs(zout - start) < 1e-6,
            "key-in": key_in > zout,
            "key-out": key_out < key_in,
        }

    step("zoom", zoom)

    # --- S98: Device Map Options from Edit (Ctrl+,) ---------------------------
    def options() -> dict:
        w.trigger("Edit", "Device Map Options…")
        shown = bool(wait_for(lambda: w.ev("_optionsWin.visible")))
        w.ev("_optionsWin.close()")
        wait_for(lambda: not w.ev("_optionsWin.visible"), NOT_S)
        w.key(QtCore.Qt.Key.Key_Comma, QtCore.Qt.KeyboardModifier.ControlModifier)
        by_key = bool(wait_for(lambda: w.ev("_optionsWin.visible")))
        # Keys pressed in it never run the Device Mapping Editor's commands (S133).
        opts_win = w.ev("_optionsWin")
        w.select(["b1"])
        before = [w.nodes(), w.hist()]
        w.activate(opts_win)
        QtTest.QTest.keyClick(opts_win, QtCore.Qt.Key.Key_Delete)
        QtTest.QTest.keyClick(
            opts_win, QtCore.Qt.Key.Key_D, QtCore.Qt.KeyboardModifier.ControlModifier
        )
        QtTest.QTest.qWait(150)
        quiet = [w.nodes(), w.hist()] == before
        if not quiet:
            while w.hist() > before[1]:
                w.ev("_ed().undo()")
        w.select([])
        w.ev("_optionsWin.close()")
        return {"menu": shown, "key": by_key, "keys-in-it-run-nothing": quiet}

    step("options", options)

    # --- S134: Arrange › Crop and Format › Table › ID Column tick when on ---
    def ticks() -> dict:
        res: dict = {}

        def tick(menu: str, text: str) -> object:
            # As the menu opens (beforeShow), the rows read the state again.
            w.ev("_editorWin.refreshCommandTexts()")
            return w.ev(f"{w.row(menu, text)}.checked")

        url = QtCore.QUrl.fromLocalFile(str(PICTURE)).toString()
        w.ev(f"_ed().addOverlay('pictures/pic.png', {json.dumps(url)})")
        pic = w.ev("_ed().selectedId")
        w.select([pic])
        res["crop-checkable"] = w.ev(f"{w.row('Arrange', 'Crop')}.checkable")
        off = tick("Arrange", "Crop")
        w.trigger("Arrange", "Crop")
        on = tick("Arrange", "Crop")
        w.trigger("Arrange", "Crop")
        res["crop"] = [off, on, tick("Arrange", "Crop"), w.ev("_ed().cropId")]
        w.ev("_ed().cropId = ''")
        w.ev(
            "(function() { var e = _ed(); e.addDrawFree('table', e.fxToX(0.1),"
            " e.fyToY(0.1),"
            " e.fxToX(0.4), e.fyToY(0.4)); return true })()"
        )
        table = w.ev("_ed().selectedId")
        w.select([table])
        res["table-kind"] = w.ev(f"_ed().isTable(_ed().nodeAt({json.dumps(table)}))")
        off = tick("Format", "ID Column")
        w.trigger("Format", "ID Column")
        on = tick("Format", "ID Column")
        w.trigger("Format", "ID Column")
        res["id-col"] = [off, on, tick("Format", "ID Column")]
        w.select([])
        return res

    step("ticks", ticks)

    # --- S133 (G38): keys never run while typing in a text field --------------
    def typing() -> dict:
        res: dict = {}
        w.select(["b1", "b2"])
        w.ev("_ed().beginRename('b1', -1)")
        res["renaming"] = bool(
            wait_for(
                lambda: w.ev(
                    "_ed().renameId === 'b1' && _editorWin.activeFocusItem !== null"
                    " && _editorWin.activeFocusItem.cursorPosition !== undefined"
                )
            )
        )
        before = [w.nodes(), w.hist(), w.ev("_editorWin.bgMode")]
        ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        win = w.win
        for key, mods in (
            (QtCore.Qt.Key.Key_B, ctrl),
            (QtCore.Qt.Key.Key_L, ctrl),
            (QtCore.Qt.Key.Key_G, ctrl),
            (QtCore.Qt.Key.Key_D, ctrl),
            (QtCore.Qt.Key.Key_Z, ctrl),
            (QtCore.Qt.Key.Key_Delete, QtCore.Qt.KeyboardModifier.NoModifier),
        ):
            QtTest.QTest.keyClick(win, key, mods)
            QtTest.QTest.qWait(80)
        res["ran-nothing"] = [w.nodes(), w.hist(), w.ev("_editorWin.bgMode")] == before
        res["still-renaming"] = w.ev("_ed().renameId")
        for ch in "Qz":
            QtTest.QTest.keyClick(win, ch)
        QtTest.QTest.qWait(100)
        res["typed"] = w.ev(
            "_editorWin.activeFocusItem ? String(_editorWin.activeFocusItem.text) : ''"
        )
        w.ev("_ed().cancelRename()")
        w.select([])
        return res

    step("typing", typing)

    # --- S99: Reset Panels keeps Show Print Area and the Shortcuts pin -------
    def reset_panels() -> dict:
        w.ev("_editorWin.setPrintAreaShown(true)")
        w.ev("_shortcutsWin.pinned = true")
        w.trigger("View", "Reset Panels")
        QtTest.QTest.qWait(100)
        res = {
            "print-area": [
                w.ev("_editorWin.printAreaOn"),
                device_map_options.print_area_shown(),
            ],
            "pin": [
                w.ev("_shortcutsWin.pinned"),
                bool(device_map_options.side_panel_state("shortcuts").get("pinned")),
            ],
        }
        w.ev("_editorWin.setPrintAreaShown(false)")
        w.ev("_shortcutsWin.pinned = false")
        return res

    step("reset-panels", reset_panels)

    # --- S100: Keyboard Shortcuts ---------------------------------------------
    def shortcuts() -> dict:
        res: dict = {}
        w.ev("_shortcutsWin.pinned = false")
        w.select(["b1"])
        before = [w.nodes(), w.hist(), w.js("_ed().selectedIds")]
        w.key(QtCore.Qt.Key.Key_K, QtCore.Qt.KeyboardModifier.ControlModifier)
        res["ctrl-k"] = bool(wait_for(lambda: w.ev("_shortcutsWin.visible")))
        sw = w.ev("_shortcutsWin")
        assert isinstance(sw, QtGui.QWindow)
        res["described"] = w.js("_shortcutsWin.list.describe()")
        # Clicks on its rows and keys typed in it run nothing.
        res["active"] = w.activate(sw)
        lst = next(
            (c for c in _items(sw.contentItem()) if c.objectName() == "shortcutsList"),
            None,
        )
        if lst is not None:
            for fy in (0.1, 0.3, 0.5):
                at = lst.mapToScene(QtCore.QPointF(lst.width() / 2, lst.height() * fy))
                QtTest.QTest.mouseClick(
                    sw,
                    QtCore.Qt.MouseButton.LeftButton,
                    QtCore.Qt.KeyboardModifier.NoModifier,
                    at.toPoint(),
                )
                QtTest.QTest.mouseDClick(
                    sw,
                    QtCore.Qt.MouseButton.LeftButton,
                    QtCore.Qt.KeyboardModifier.NoModifier,
                    at.toPoint(),
                )
        res["clicks-ran-nothing"] = [
            w.nodes(),
            w.hist(),
            w.js("_ed().selectedIds"),
        ] == before
        # Keys typed in it: none reaches the Device Mapping Editor's commands.
        keys: dict = {}
        ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        none = QtCore.Qt.KeyboardModifier.NoModifier
        for name, key, mods in (
            ("Return", QtCore.Qt.Key.Key_Return, none),
            ("Delete", QtCore.Qt.Key.Key_Delete, none),
            ("Ctrl+D", QtCore.Qt.Key.Key_D, ctrl),
            ("Ctrl+L", QtCore.Qt.Key.Key_L, ctrl),
        ):
            w.select(["b1"])
            w.activate(sw)
            QtTest.QTest.keyClick(sw, key, mods)
            QtTest.QTest.qWait(150)
            keys[name] = [w.nodes(), w.hist(), w.js("_ed().selectedIds")] == before
            if not keys[name]:
                w.ev("_ed().undo()")
        res["keys-ran-nothing"] = keys
        res["ran-nothing"] = res["clicks-ran-nothing"] and all(keys.values())
        res["still-editing"] = bool(w.ev("_editorWin.editing"))
        # Unpinned: activating the Device Mapping Editor closes it.
        res["visible-before-away"] = sw.isVisible()
        res["activated-map"] = w.activate(w.win)
        res["unpinned-closes"] = bool(wait_for(lambda: not sw.isVisible(), 3))
        # Pinned: it stays; the pin is kept.
        w.ev("_shortcutsWin.openFor(_editorWin)")
        wait_for(lambda: sw.isVisible())
        w.activate(sw)
        w.ev("_shortcutsWin.pinned = true")
        w.activate(w.win)
        QtTest.QTest.qWait(300)
        res["pinned-stays"] = sw.isVisible()
        res["pin-kept"] = bool(
            device_map_options.side_panel_state("shortcuts").get("pinned")
        )
        w.ev("_shortcutsWin.pinned = false")
        res["unpin-kept"] = device_map_options.side_panel_state("shortcuts").get(
            "pinned"
        )
        w.ev("_shortcutsWin.close()")
        # The search box filters.
        w.ev("_shortcutsWin.openFor(_editorWin)")
        wait_for(lambda: sw.isVisible())
        search = next(
            (
                c
                for c in _items(sw.contentItem())
                if c.objectName() == "shortcutsSearch"
            ),
            None,
        )
        if search is not None:
            search.setProperty("text", "zoom")
            QtTest.QTest.qWait(100)
            w.ev("_shortcutsWin.list.search()")
            res["search"] = w.js("_shortcutsWin.list.describe()")
            search.setProperty("text", "")
        w.ev("_shortcutsWin.close()")
        w.select([])
        return res

    step("shortcuts", shortcuts)

    # Outside Edit the Keyboard Shortcuts window lists the same menus.
    w.ev("_editorWin.discardEdit()")
    wait_for(lambda: not w.ev("_editorWin.editing"))
    step(
        "shortcuts-live",
        lambda: (
            w.ev("_shortcutsWin.openFor(_editorWin)"),
            w.js("_shortcutsWin.list.describe()"),
            w.ev("_shortcutsWin.close()"),
        )[1],
    )

    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


def _items(item: QtQuick.QQuickItem) -> list:
    found = [item]
    for c in item.childItems():
        found += _items(c)
    return found


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
