# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Right-click Favourites in the shared menu (07 S137): loads
Gremlin.Menus.ContextMenu off-screen with a small model fed straight in, and
drives it with the pointer: the always-open Favourites block, its × and the
☆ / ★ on rows that are commands. A second menu without favouritesEnabled shows
none of it. Prints "RESULT name value" lines, "WARN ..." for each QML warning,
then "done". test_rc_ctx.py runs it in its own process.

    python test/unit/rc_ctx_smoke.py <out_dir>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
os.environ["QT_FILE_SELECTORS"] = "Universal"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)


HARNESS = """
import QtQuick
import QtQuick.Controls
import Gremlin.Menus
import Gremlin.Style
import "../../../theme/Gremlin/Menus/menu_model.js" as MenuModel

ApplicationWindow {
    id: _win
    width: 900
    height: 700
    visible: true
    property var log: []
    property var favs: ["edit.copy", "edit.delete"]
    function note(s) { log = log.concat([s]) }
    function build() {
        var copy = MenuModel.action("Copy", function() { note("ran copy") }, true,
                                    { hint: "Ctrl+C" })
        copy.cmd = "edit.copy"
        var cut = MenuModel.action("Cut", function() { note("ran cut") }, true,
                                   { hint: "Ctrl+X" })
        cut.cmd = "edit.cut"
        var plain = MenuModel.action("Rename", function() { note("ran rename") }, true)
        var all = [
            { cmd: "edit.copy", text: "Copy", hint: "Ctrl+C", enabled: true,
              run: function() { note("ran fav copy") } },
            { cmd: "edit.delete", text: "Delete", hint: "Del", enabled: true,
              run: function() { note("ran fav delete") } },
            { cmd: "edit.cut", text: "Cut", hint: "Ctrl+X", enabled: true,
              run: function() { note("ran fav cut") } }
        ]
        var m = MenuModel.menu("item", "A chip", [copy, cut, plain],
            [MenuModel.section("more", "More",
                               [MenuModel.action("Other", function() {}, true)])])
        // In the order added, as rig_menu.js gives them.
        m.favourites = favs.map(function(c) {
            return all.filter(function(f) { return f.cmd === c })[0]
        })
        return m
    }
    // Any item, by objectName, anywhere in the window (the popups too).
    function find(name, from) {
        var root = from || _win.Overlay.overlay
        if (root.objectName === name)
            return root
        var kids = root.children
        for (var i = 0; i < kids.length; i++) {
            var hit = find(name, kids[i])
            if (hit)
                return hit
        }
        return null
    }
    function centre(item) {
        var p = item.mapToItem(null, item.width / 2, item.height / 2)
        return Math.round(p.x) + "," + Math.round(p.y)
    }
    function rowCentre(menu, text) {
        var r = menu.rowRect(menu.rowIndexOf(text))
        return Math.round(r.x + r.w / 2) + "," + Math.round(r.y + r.h / 2)
    }
    // The quick row (not the favourite) showing this text.
    function quickRowCentre(menu, text) {
        var at = -1
        for (var i = 0; i < menu.rows.length; i++) {
            var r = menu.rows[i]
            if (r.type === "item" && r.item.text === text)
                at = i
        }
        var b = menu.rowRect(at)
        return Math.round(b.x + b.w / 2) + "," + Math.round(b.y + b.h / 2)
    }
    Item { id: _anchor; x: 40; y: 40; width: 10; height: 10 }
    ContextMenu {
        id: _plain
        build: _win.build
    }
    ContextMenu {
        id: _fav
        build: _win.build
        favouritesEnabled: true
        favouriteIds: _win.favs
        onFavouriteToggled: (cmd) => {
            _win.note("toggled " + cmd)
            var i = _win.favs.indexOf(cmd)
            var next = _win.favs.slice()
            if (i >= 0) next.splice(i, 1); else next.push(cmd)
            _win.favs = next
        }
        onFavouriteRemoved: (cmd) => {
            _win.note("removed " + cmd)
            _win.favs = _win.favs.filter(function(c) { return c !== cmd })
        }
    }
}
"""

# (name, JavaScript, pointer action): the action is None, "move x,y" or
# "click x,y", taken from the JavaScript's value.
STEPS = [
    # Without favouritesEnabled: the menu is as before (no block, no ☆).
    ("plain-describe",
     "_plain.openAt(_anchor, 0, 0); _plain.describe().join('|')", None),
    ("plain-hover-pos", "rowCentre(_plain, 'Copy')", "move"),
    ("plain-no-star",
     "String(find('ctxStar_edit.copy') === null"
     " && find('ctxFavourites') === null)", None),
    ("plain-closed", "_plain.close(); 'ok'", None),
    # With it: the Favourites block on top, ★ for favourites in the rows.
    ("fav-describe", "_fav.openAt(_anchor, 0, 0); _fav.describe().join('|')", None),
    ("fav-block",
     "String(find('ctxFavourites') !== null && find('ctxFavourites').visible)",
     None),
    ("fav-row-names",
     "String(!!find('ctxFavRow_edit.copy') && !!find('ctxFavRow_edit.delete')"
     " && !!find('ctxFavRemove_edit.copy'))", None),
    # The block sits above the quick rows.
    ("fav-above",
     "String(find('ctxFavRow_edit.delete').mapToItem(null, 0, 0).y"
     " < _fav.rowRect(_fav.rowIndexOf('Cut')).y)", None),
    # × removes it: the signal, the row goes, the menu stays open.
    ("fav-remove-pos", "centre(find('ctxFavRemove_edit.delete'))", "click"),
    ("fav-after-remove",
     "String(_fav.opened) + ' ' + log.join(';') + ' '"
     " + _fav.describe().join('|')", None),
    # A ☆ shows only on hover, on rows that are commands.
    ("star-hidden",
     "var s = find('ctxStar_edit.cut'); String(s !== null && s.visible)", None),
    ("cut-hover-pos", "rowCentre(_fav, 'Cut')", "move"),
    ("star-shown",
     "var s = find('ctxStar_edit.cut');"
     " String(s.visible) + ' ' + (s.text === '\\uF588')", None),
    ("no-star-plain-row", "String(find('ctxStar_') === null)", None),
    # Clicking the ☆ adds it and does not run the row.
    ("star-click-pos", "centre(find('ctxStar_edit.cut'))", "click"),
    ("after-star",
     "String(_fav.opened) + ' ' + log.join(';') + ' ' + favs.join(',')", None),
    # The block shows the new favourite at once (the menu rebuilt).
    ("after-star-block", "_fav.describe().join('|')", None),
    # The ★ for a favourite (Copy is one).
    ("copy-hover-pos", "quickRowCentre(_fav, 'Copy')", "move"),
    ("copy-star",
     "var s = find('ctxStar_edit.copy');"
     " String(s.visible) + ' ' + (s.text === '\\uF586')", None),
    # Clicking a favourite runs it and closes the menu like an action.
    ("fav-run-pos", "_win.log = []; centre(find('ctxFavRow_edit.copy'))", "click"),
    ("after-run", "String(_fav.opened) + ' ' + log.join(';')", None),
    # Reopened, the menu shows the store's list again (Cut added, Delete gone).
    ("reopen", "_fav.openAt(_anchor, 0, 0); _fav.describe().join('|')", None),
    ("closed", "_fav.close(); 'ok'", None),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])
    font = QtGui.QFont("Segoe UI")
    font.setPixelSize(15)
    app.setFont(font)
    QtGui.QFontDatabase.addApplicationFont(str(ROOT / "gfx" / "bootstrap-icons.otf"))
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    # Never written: the harness's imports resolve from test/unit/qml.
    base = QtCore.QUrl.fromLocalFile(
        str(ROOT / "test" / "unit" / "qml" / "RcCtxHarness.qml")
    )
    engine.loadData(HARNESS.encode("utf-8"), base)
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
    else:
        win = roots[0]
        QtTest.QTest.qWait(300)
        quick = shiboken6.wrapInstance(
            shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
        )
        for name, code, act in STEPS:
            expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
            value = expr.evaluate()
            if expr.hasError():
                print(f"ERROR {name}: {expr.error().toString()}", flush=True)
                continue
            value = value[0] if isinstance(value, tuple) else value
            print(f"RESULT {name} {value}", flush=True)
            if act and isinstance(value, str) and "," in value:
                x, y = (int(v) for v in value.split(","))
                pos = QtCore.QPoint(x, y)
                # Two moves: the menu ignores a first report at a still point.
                QtTest.QTest.mouseMove(quick, QtCore.QPoint(x - 3, y))
                QtTest.QTest.qWait(30)
                QtTest.QTest.mouseMove(quick, pos)
                QtTest.QTest.qWait(60)
                if act == "click":
                    QtTest.QTest.mouseClick(
                        quick, QtCore.Qt.MouseButton.LeftButton,
                        QtCore.Qt.KeyboardModifier.NoModifier, pos,
                    )
            QtTest.QTest.qWait(120)
            quick.grabWindow().save(str(out / f"{name}.png"))
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
