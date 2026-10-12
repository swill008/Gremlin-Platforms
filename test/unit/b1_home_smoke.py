# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home off-screen (D-FIXLIST-B1 items 6 and 10; args: <ui scale>): where
the page bar's controls sit (Compact view and Layout only, D-03-HOME-BAND),
and Home's Undo / Redo driven through what the page calls (the model's slots,
the keys, the card menu's and the empty-space menu's header pairs; Hide
Selected Cards and Reset Size of Selected Cards). test_b1_home.py runs it
in its own process with a fresh user folder (journey harness).

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
        "compactRight": right("homeCompactView"),
        "labelLeft": left("homeLayoutLabel"),
        "labelRight": right("homeLayoutLabel"),
        "layoutLeft": left("homeLayoutCombo"),
        "layoutRight": right("homeLayoutCombo"),
        "undoBar": j.item(j.win, "homeUndoBar") is not None,
        "loaderWidth": round(flick.width(), 1) if flick is not None else None,
        "dp10": j.ev("Style.dp(10)"),
        "dp40": j.ev("Style.dp(40)"),
        "dp16": j.ev("Style.dp(16)"),
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

    def last_step() -> str:
        """The label of the step Undo would take back ("" for none)."""
        done = ev(model)._undo_steps  # type: ignore[attr-defined]
        return done[-1][0] if done else ""

    def undone_step() -> str:
        """The label of the step Redo would put back ("" for none)."""
        undone = ev(model)._redo_steps  # type: ignore[attr-defined]
        return undone[-1][0] if undone else ""

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
            "last": last_step()}
    keys(z, ctrl)
    seen["ctrlZ"] = ev(f"{model}.compactView")
    seen["undone"] = undone_step()
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

    # --- Layout, undone with the empty-space menu's Undo / Redo -----------------
    ev(f"{model}.setSplitMode('vertical')")
    j.settle()
    lay = {"after": ev(f"{model}.splitMode"), "tip": last_step()}
    page = "_statusLoader.item"
    header = j.ev(
        f"JSON.stringify({page}.emptyMenuModel().header.map(function(h) {{"
        " return [h.label, h.enabled] }))"
    )
    lay["emptyHeader"] = header
    j.ev(f"{page}.emptyMenuModel().header[0].run(); true")
    j.settle()
    j.settle()
    lay["undone"] = ev(f"{model}.splitMode")
    j.ev(f"{page}.emptyMenuModel().header[1].run(); true")
    j.settle()
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

    # --- Hide Selected Cards / Reset Size of Selected Cards: one step each -------
    sel: dict = {}
    ev(f"{model}.unstackAll('{a}')")  # a and b are stacked again after the undo
    ev(f"{model}.setPileSize('{a}', 400, 300)")
    ev(f"{model}.setPileSize('{b}', 420, 300)")
    n = steps()
    ev(f"{model}.resetSelectedSizes('{a},{b}')")
    sel["reset"] = [ev(f"{model}.cardWidth('{a}')"), ev(f"{model}.cardWidth('{b}')")]
    sel["resetSteps"] = steps() - n
    sel["resetTip"] = last_step()
    ev(f"{model}.undo()")
    sel["resetUndone"] = [
        ev(f"{model}.cardWidth('{a}')"), ev(f"{model}.cardWidth('{b}')")
    ]
    n = steps()
    ev(f"{model}.hideSelected('{a},{b}')")
    sel["hidden"] = sorted(ev(f"{model}.hiddenList()"))  # type: ignore[arg-type]
    def shown() -> list:
        leaders = ev(f"{model}.pileLeaders('')")
        return [s for s in (a, b) if s in leaders]  # type: ignore[operator]

    sel["shownAfterHide"] = shown()
    sel["hideSteps"] = steps() - n
    sel["hideTip"] = last_step()
    ev(f"{model}.undo()")
    sel["hiddenUndone"] = ev(f"{model}.hiddenList()")
    sel["shownUndone"] = shown()
    ev(f"{model}.redo()")
    sel["hiddenRedone"] = sorted(ev(f"{model}.hiddenList()"))  # type: ignore[arg-type]
    ev(f"{model}.undo()")
    sel["ab"] = sorted([a, b])
    # Undo brings back only the cards that step hid: c, hidden with Hide
    # Card afterwards, stays hidden; Redo hides a and b again.
    ev(f"{model}.hideSelected('{a},{b}')")
    ev(f"{model}.ignoreSlug('{c}')")
    ev(f"{model}.undo()")
    sel["onlyStepUndone"] = sorted(
        ev(f"{model}.hiddenList()")  # type: ignore[arg-type]
    )
    ev(f"{model}.redo()")
    sel["onlyStepRedone"] = sorted(
        ev(f"{model}.hiddenList()")  # type: ignore[arg-type]
    )
    sel["abc"] = sorted([a, b, c])
    sel["c"] = [c]
    ev(f"{model}.undo()")
    ev(f"{model}.unignoreSlug('{c}')")
    out["selected"] = sel

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
    picture["addTip"] = last_step()
    picture["removed"] = ev(f"{model}.removeCardImage('logical')")
    picture["filesRemoved"] = files()
    picture["photoRemoved"] = bool(ev(f"{model}.cardMap('logical').photo"))
    ev("_statusLoader.item.undo()")
    picture["filesBack"] = files()
    picture["photoBack"] = bool(ev(f"{model}.cardMap('logical').photo"))
    picture["nextUndo"] = last_step()
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
