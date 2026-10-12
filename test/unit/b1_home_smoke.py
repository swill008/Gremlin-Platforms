# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home off-screen (D-FIXLIST-B1 items 6 and 10; args: <ui scale>): where
the page bar's controls sit, and Home's Undo / Redo driven through what the
page calls (the model's slots, the page bar's Undo / Redo pair, the keys,
the card menu's header). test_b1_home.py runs it in its own process with a
fresh user folder (journey harness).

    python test/unit/b1_home_smoke.py 100
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import RIG, Journey  # noqa: E402

SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def _bar(j: Journey) -> dict:
    """Scene x of the page bar's pieces, and the bar's width."""
    from PySide6 import QtCore

    def left(name: str) -> float | None:
        item = j.item(j.win, name)
        if item is None or not item.isVisible():
            return None
        return round(item.mapToScene(QtCore.QPointF(0, 0)).x(), 1)

    def right(name: str) -> float | None:
        item = j.item(j.win, name)
        if item is None or not item.isVisible():
            return None
        return round(item.mapToScene(QtCore.QPointF(item.width(), 0)).x(), 1)

    flick = j.item(j.win, "pageBarLoader")
    return {
        "winWidth": j.win.width(),
        "divider": right("modeBarDivider"),
        "compact": left("homeCompactView"),
        "layoutRight": right("homeLayoutCombo"),
        "undoBar": left("homeUndoBar"),
        "undoButton": j.item(j.win, "undoBarUndo") is not None,
        "loaderWidth": round(flick.width(), 1) if flick is not None else None,
        "dp10": j.ev("Style.dp(10)"),
        "dp40": j.ev("Style.dp(40)"),
    }


def story(j: Journey) -> None:
    from PySide6 import QtCore, QtTest

    out = j.out
    j.win.setProperty("visible", True)
    j.win.setWidth(1600)
    j.win.setHeight(1000)
    j.win.requestActivate()
    out["uiScale"] = j.ev("Style.uiScale")
    j.wait_until(lambda: j.item(j.win, "homeLayoutCombo") is not None, "the page bar")
    j.settle()
    out["barWide"] = _bar(j)
    # The narrowest the window goes.
    j.win.setWidth(j.win.minimumWidth())
    j.settle()
    out["barNarrow"] = _bar(j)
    j.win.setWidth(1600)
    j.settle()
    if SCALE != 100:
        return

    model = "_moduleModel"

    def ev(code: str) -> object:
        return j.ev(code)

    def steps() -> int:
        return len(ev(model)._undo_steps)  # type: ignore[attr-defined]

    out["start"] = {"steps": steps(), "canUndo": ev(f"{model}.canUndo")}

    def keys(key: QtCore.Qt.Key, mods: QtCore.Qt.KeyboardModifier) -> None:
        QtTest.QTest.keyClick(j.win, key, mods)
        j.settle()

    ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
    shift = QtCore.Qt.KeyboardModifier.ShiftModifier
    z = QtCore.Qt.Key.Key_Z
    y = QtCore.Qt.Key.Key_Y

    # --- Compact view through its tick box, then the keys --------------------
    box = j.item(j.win, "homeCompactView")
    j.ev("toggle(); toggled(); true", box)
    j.settle()
    seen = {"after": ev(f"{model}.compactView"), "steps": steps(),
            "last": ev(f"{model}.lastChange")}
    keys(z, ctrl)
    seen["ctrlZ"] = ev(f"{model}.compactView")
    seen["undone"] = ev(f"{model}.undone")
    seen["boxAfterUndo"] = box.property("checked")
    keys(y, ctrl)
    seen["ctrlY"] = ev(f"{model}.compactView")
    keys(z, ctrl)
    keys(z, ctrl | shift)
    seen["ctrlShiftZ"] = ev(f"{model}.compactView")
    keys(z, ctrl)
    out["compact"] = seen

    # A text box being typed in keeps Ctrl+Z.
    j.ev(
        "Qt.createQmlObject('import QtQuick.Controls;"
        " TextField { objectName: \"b1Field\" }', _statusLoader.item)"
    )
    field = j.item(j.win, "b1Field")
    j.ev("forceActiveFocus(); true", field)
    j.settle()
    ev(f"{model}.setCompactView(true)")
    before = steps()
    keys(z, ctrl)
    out["typing"] = {
        "compact": ev(f"{model}.compactView"), "steps": steps(), "before": before
    }
    j.ev("destroy(); true", field)
    j.settle()
    j.ev("_statusLoader.item.forceActiveFocus(); true")
    keys(z, ctrl)
    out["typing"]["afterFieldGone"] = ev(f"{model}.compactView")

    # --- Layout, undone with the page bar's Undo button ------------------------
    ev(f"{model}.setSplitMode('vertical')")
    j.settle()
    lay = {"after": ev(f"{model}.splitMode"), "tip": ev(f"{model}.undoTip")}
    undo_button = j.item(j.win, "undoBarUndo")
    lay["buttonEnabled"] = undo_button.property("enabled")
    j.click(undo_button)
    j.settle()
    lay["undone"] = ev(f"{model}.splitMode")
    j.click(j.item(j.win, "undoBarRedo"))
    j.settle()
    lay["redone"] = ev(f"{model}.splitMode")

    # --- The divider: one step per drag ------------------------------------------
    start = float(ev(f"{model}.splitRatio"))
    n = steps()
    ev(f"{model}.beginDivider()")
    ev(f"{model}.setSplitRatio(0.35)")  # the page's timer while dragging
    ev(f"{model}.setSplitRatio(0.3)")
    ev(f"{model}.endDivider(0.3)")
    lay["divider"] = {"start": start, "moved": ev(f"{model}.splitRatio"),
                      "steps": steps() - n}
    ev(f"{model}.undo()")
    lay["divider"]["undone"] = ev(f"{model}.splitRatio")
    ev(f"{model}.setSplitMode('none')")
    j.settle()
    out["layout"] = lay

    # --- Card size, order and stacks ----------------------------------------------
    leaders = ev(f"{model}.pileLeaders('')")
    a, b, c = leaders[0], leaders[1], leaders[2]
    out["leaders"] = leaders
    cards: dict = {}
    n = steps()
    ev(f"{model}.setPileSize('{a}', 400, 300)")
    cards["sized"] = ev(f"{model}.cardWidth('{a}')")
    ev(f"{model}.undo()")
    cards["sizeUndone"] = ev(f"{model}.cardWidth('{a}')")
    ev(f"{model}.redo()")
    ev(f"{model}.resetCardSize('{a}')")
    cards["reset"] = ev(f"{model}.cardWidth('{a}')")
    ev(f"{model}.undo()")
    cards["resetUndone"] = ev(f"{model}.cardWidth('{a}')")
    ev(f"{model}.resetAllCardSizes()")
    cards["resetAll"] = ev(f"{model}.cardWidth('{a}')")
    ev(f"{model}.undo()")
    cards["resetAllUndone"] = ev(f"{model}.cardWidth('{a}')")
    cards["sizeSteps"] = steps() - n

    # A drag to a new place (the page's drop): one step.
    n = steps()
    ev(f"_statusLoader.item.insertBefore = '{a}'; _statusLoader.item.homeBefore = '';"
       f" _statusLoader.item.dragSlug = '{c}'; _statusLoader.item.handleDrop('{c}')")
    j.settle()
    cards["dragged"] = ev(f"{model}.pileLeaders('')")[:3]
    cards["dragSteps"] = steps() - n
    ev(f"{model}.undo()")
    cards["dragUndone"] = ev(f"{model}.pileLeaders('')")[:3]

    ev(f"{model}.stackSelected('{a}', '{a},{b}')")
    cards["stacked"] = ev(f"{model}.pileMembers('{a}')")
    ev(f"{model}.unstackSlug('{b}')")
    cards["unstacked"] = ev(f"{model}.pileMembers('{a}')")
    ev(f"{model}.undo()")
    cards["unstackUndone"] = ev(f"{model}.pileMembers('{a}')")
    ev(f"{model}.unstackAll('{a}')")
    cards["unstackAll"] = ev(f"{model}.pileMembers('{a}')")
    ev(f"{model}.undo()")
    cards["unstackAllUndone"] = ev(f"{model}.pileMembers('{a}')")
    ev(f"{model}.setPileSize('{a}', 400, 300)")
    n = steps()
    ev(f"{model}.clearCardSettings('{a}')")
    def layout_of(slug: str) -> list:
        return [
            ev(f"{model}.pileMembers('{slug}')"), ev(f"{model}.cardWidth('{slug}')")
        ]

    cards["cleared"] = layout_of(a)
    cards["clearSteps"] = steps() - n
    ev(f"{model}.undo()")
    cards["clearUndone"] = layout_of(a)
    out["cards"] = cards

    # --- The Logical Device card's picture -----------------------------------------
    from PySide6 import QtGui

    from gremlin.modules import store
    from gremlin.ui import module_model

    home = pathlib.Path(__import__("os").environ["USERPROFILE"])
    pic = home / "b1_card.png"
    image = QtGui.QImage(8, 8, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#3366cc"))
    image.save(str(pic))
    url = QtCore.QUrl.fromLocalFile(str(pic)).toString()

    def files() -> dict:
        found = store.photo_files("Logical Device", module_model.LOGICAL_GUID)
        return {p.name: len(p.read_bytes()) for p in found}

    picture: dict = {"logged": []}
    plain_plog = module_model._plog
    # What Undo couldn't put back is logged ("home undo picture failed").
    module_model._plog = lambda action, **parts: (  # type: ignore[assignment]
        picture["logged"].append(f"{action} {parts}") if "failed" in action else None,
        plain_plog(action, **parts),
    )
    picture["added"] = ev(f"{model}.setCardImage('logical', '{url}')")
    picture["files"] = files()
    picture["photo"] = bool(ev(f"{model}.cardMap('logical').photo"))
    picture["addTip"] = ev(f"{model}.undoTip")
    picture["removed"] = ev(f"{model}.removeCardImage('logical')")
    picture["filesRemoved"] = files()
    picture["photoRemoved"] = bool(ev(f"{model}.cardMap('logical').photo"))
    ev("_statusLoader.item.undo()")
    picture["filesBack"] = files()
    picture["photoBack"] = bool(ev(f"{model}.cardMap('logical').photo"))
    picture["nextUndo"] = ev(f"{model}.undoTip")
    ev("_statusLoader.item.undo()")
    picture["filesAddUndone"] = files()
    picture["photoAddUndone"] = bool(ev(f"{model}.cardMap('logical').photo"))
    ev("_statusLoader.item.redo()")
    picture["filesRedone"] = files()
    picture["photoRedone"] = bool(ev(f"{model}.cardMap('logical').photo"))
    out["picture"] = picture

    # --- The card menu's header pair --------------------------------------------------
    j.settle()
    card = next(
        it for it in j.walk(j.win.contentItem())
        if it.metaObject().indexOfSignal("cardFocused()") >= 0 and it.isVisible()
    )
    header = j.ev("JSON.stringify(menuModel().header.map(function(h) {"
                  " return [h.label, h.enabled] }))", card)
    menu = {
        "header": header, "stepsBefore": steps(), "redoBefore": ev(f"{model}.canRedo")
    }
    j.ev("menuModel().header[0].run(); true", card)
    j.settle()
    j.settle()
    menu["stepsAfter"] = steps()
    menu["redoAfter"] = ev(f"{model}.canRedo")
    out["menu"] = menu

    # --- About 50 steps; another profile clears them ---------------------------------
    for i in range(60):
        ev(f"{model}.setCompactView({'true' if i % 2 == 0 else 'false'})")
    out["cap"] = steps()
    j.backend.newProfile()
    j.settle()
    out["afterProfile"] = {"steps": steps(), "canRedo": ev(f"{model}.canRedo")}


def main() -> None:
    def before(_j: Journey) -> None:
        from gremlin.ui import ui_scale_option

        ui_scale_option.active_scale = lambda: SCALE  # type: ignore[assignment]

    Journey(before, **RIG).run(story)


if __name__ == "__main__":
    main()
