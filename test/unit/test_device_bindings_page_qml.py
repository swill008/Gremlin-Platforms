# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Bindings page's own QML (qml/DeviceBindingsPage.qml), driven
off-screen on the real program (batch C, 05 section M).

A journey (test/journeys/_harness.py): the app runs in its own process with
a temporary USERPROFILE, the fake joystick driver ("pJoy Pro", its input
module claiming everything) and a fake vJoy. The page is the one Main shows
for the stick's card; while Main doesn't host it yet, the story hosts the
same file in a window of its own with Main's context (uiState, signal,
backend), so the page's QML is what is tested either way. It checks, as a
user would:

1. The Find bar holds Find, the input-type box, the action Type and Output
   boxes (S124) and the ticks Ungrouped / No bindings in this mode (S123);
   "Move inputs with no actions to the end" is gone (S123).
2. A click on a parent row opens the shared pane on that input (S126);
   it shows the input's actions; Close pane after OK is there.
3. The row's right-click menu: Undo/Redo header; Add Action, Rename,
   History, Module Setup…; sections Row (Clear Name (PB2), Delete
   actions…), Group, Groups, Order (By System Name, By Your Name, Group
   Names A to Z); no Add Inputs (claims come from Module Setup). An action
   row's menu: Open, Delete.
4. The page bar (01 S58a): Appearance… opens the shared Appearance panel
   with the live rows (S125, S131).
5. Jump to pressed input (S131): a stick button pressed on the fake driver
   is shown by the tree (highlightKey) with live decoration on.

Spec: 05 S121-S131; 01 S58a.
"""

from __future__ import annotations

import os
import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, JourneyIncomplete, run_journey  # noqa: E402

STICK = "pJoy Pro"
B2, B5 = "parent:button:2", "parent:button:5"


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    def __init__(self, j: Journey, name: str) -> None:
        self.j = j
        self.name = name

    def __enter__(self) -> _Part:
        return self

    def __exit__(self, kind: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
        if exc is not None:
            self.j.out[f"{self.name}:error"] = f"{kind.__name__}: {exc}"
            self.j.out[f"{self.name}:traceback"] = traceback.format_exc()
        return True


def _before(j: Journey) -> None:
    j.input_module(STICK)
    j.vjoy_module()


def _shot(j: Journey, window: Any, name: str) -> None:  # noqa: ANN401
    folder = j.out.get("_shots")
    if not folder:
        return
    j.QTest.qWait(400)
    j.out[f"shot:{name}"] = bool(
        window.grabWindow().save(str(pathlib.Path(folder) / name))
    )


def _find_page(j: Journey) -> Any:  # noqa: ANN401
    from PySide6 import QtQuick

    for w in j.app.topLevelWindows():
        if not isinstance(w, QtQuick.QQuickWindow) or not w.isVisible():
            continue
        for item in j.walk(w.contentItem()):
            name = item.metaObject().className()
            if name.startswith("DeviceBindingsPage") and item.isVisible():
                return item
    return None


def _host_page(j: Journey, guid: str) -> Any:  # noqa: ANN401
    """The page in a window of its own, made from Main's context (the same
    file and engine Main would use)."""
    made = j.ev(
        "(function() {"
        " var win = Qt.createQmlObject('import QtQuick; import QtQuick.Window;"
        " Window { width: 1600; height: 900; visible: true;"
        " color: \"black\" }', _root, 'host');"
        " var c = Qt.createComponent('DeviceBindingsPage.qml');"
        " if (c.status !== Component.Ready) return 'error: ' + c.errorString();"
        " var page = c.createObject(win.contentItem,"
        f" {{ guid: {guid!r}, deviceName: {STICK!r} }});"
        " if (!page) return 'error: not made';"
        " page.anchors.fill = win.contentItem;"
        " return 'ok' })()"
    )
    j.out["hosted"] = made
    assert made == "ok", made
    return j.wait_until(lambda: _find_page(j), "the hosted DeviceBindingsPage")


def _by_name(j: Journey, root: Any, name: str) -> Any:  # noqa: ANN401
    for item in j.walk(root):
        if item.objectName() == name and item.isVisible():
            return item
    return None


def _texts(j: Journey, root: Any) -> list[str]:  # noqa: ANN401
    return [
        str(i.property("text"))
        for i in j.walk(root)
        if i.isVisible() and isinstance(i.property("text"), str) and i.property("text")
    ]


def _row_item(j: Journey, page: Any, key: str) -> Any:  # noqa: ANN401
    """A ControlTree row delegate by its key."""
    for item in j.walk(page):
        if (
            item.isVisible()
            and item.property("key") == key
            and item.property("rowKind")
        ):
            return item
    return None


def _click(j: Journey, item: Any, right: bool = False) -> None:  # noqa: ANN401
    from PySide6 import QtCore

    p = item.mapToScene(QtCore.QPointF(min(160.0, item.width() / 2), item.height() / 2))
    button = (
        QtCore.Qt.MouseButton.RightButton if right else QtCore.Qt.MouseButton.LeftButton
    )
    j.QTest.mouseClick(
        item.window(), button, QtCore.Qt.KeyboardModifier.NoModifier, p.toPoint()
    )


def story(j: Journey) -> None:
    import json

    shots = sys.argv[1] if len(sys.argv) > 1 else ""
    if shots:
        j.out["_shots"] = shots
    j.win.setWidth(1600)
    j.win.setHeight(900)
    uid = j.stick(STICK).device_guid.uuid
    mode = j.profile.modes.first_mode
    j.map_button(uid, 2, mode, 2)
    j.map_button(uid, 2, mode, 3)
    j.map_button(uid, 1, mode, 1)
    j.settle()

    main_hosts = "DeviceBindingsPage" in (ROOT / "qml" / "Main.qml").read_text(
        encoding="utf-8"
    )
    main_hosts = main_hosts and not os.environ.get("CFG_PAGE_OWN_WINDOW")
    if main_hosts:
        # Main shows the page for the stick's card (the real path).
        j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("pjoy_pro"))')
        j.wait_until(
            lambda: j.backend.uiState.currentTab == "physical", "the stick's page"
        )
        page = j.wait_until(lambda: _find_page(j), "Main's DeviceBindingsPage")
        j.out["host"] = "main"
    else:
        # Main doesn't host it yet: the stick is the current device on a
        # page that isn't Home (the pressed-input highlight needs both).
        ui = j.backend.uiState
        ui.setCurrentDevice(str(uid))
        ui.setCurrentTab("physical")
        ui.setCurrentRoom("settings")
        j.settle()
        page = _host_page(j, str(ui.currentDevice))
        j.out["host"] = "own window"
    win = page.window()
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    layout = j.wait_until(
        lambda: page.findChild(HardwareLayoutModel), "the page's model"
    )
    j.wait_until(lambda: layout.property("parentCount") > 0, "the claimed inputs")
    j.QTest.qWait(500)

    with _Part(j, "find"):
        find = _by_name(j, page, "deviceBindingsFind")
        j.out["find"] = find is not None
        j.out["actionType"] = _by_name(j, page, "deviceBindingsActionType") is not None
        j.out["output"] = _by_name(j, page, "deviceBindingsOutputFilter") is not None
        texts = _texts(j, page)
        j.out["ticks"] = [
            t for t in ("Ungrouped", "No bindings in this mode") if t in texts
        ]
        everywhere = _texts(j, win.contentItem()) + _texts(j, j.win.contentItem())
        j.out["parkGone"] = "Move inputs with no actions to the end" not in everywhere

    with _Part(j, "rowClick"):
        row = j.wait_until(lambda: _row_item(j, page, B2), "Button 2's row")
        _click(j, row)
        j.wait_until(lambda: page.property("actionOpen"), "the pane open")
        j.out["paneKey"] = page.property("paneKey")
        j.out["closeAfterOk"] = "Close pane after OK" in _texts(j, page)
        _shot(j, win, "config_page_pane.png")

    with _Part(j, "menu"):
        from PySide6 import QtCore

        # The pane is open on Button 2: its menu has no Delete actions… (S31).
        row = _row_item(j, page, B2)
        _click(j, row, right=True)
        j.wait_until(lambda: j.ev("_menuKey", page) == B2, "the menu on Button 2")
        j.out["menuKey"] = j.ev("_menuKey", page)
        j.QTest.keyClick(win, QtCore.Qt.Key.Key_Escape)
        j.out["deleteWhileOpen"] = '"Delete actions…"' in str(
            j.ev("JSON.stringify(_layoutMenuModel())", page)
        )
        j.ev("actionPane.closePaneNow(); true", page)
        j.QTest.qWait(300)
        _click(j, _row_item(j, page, B2), right=True)
        j.QTest.qWait(500)
        _shot(j, win, "config_page_menu.png")
        j.QTest.keyClick(win, QtCore.Qt.Key.Key_Escape)
        flat = str(j.ev("JSON.stringify(_layoutMenuModel())", page))
        j.out["menuRaw"] = flat[:3000]
        j.out["rowSection"] = [
            r.get("text")
            for s in json.loads(flat)["sections"]
            if s["key"] == "row"
            for r in s["items"]
        ]
        j.out["menuHas"] = {
            w: (f'"{w}"' in flat)
            for w in (
                "Undo",
                "Redo",
                "Add Action",
                "Rename",
                "History",
                "Module Setup…",
                "Clear Name",
                "Delete actions…",
                "Group as",
                "New Group",
                "By System Name",
                "By Your Name",
                "Group Names A to Z",
                "Add Inputs",
                "Assign Hardware",
            )
        }
        action = j.ev(
            "(function() { _actionParent = %s; _actionSeq = 0; _actionTitle = 'x';"
            " return JSON.stringify(_actionMenu.build()) })()" % json.dumps(B2),
            page,
        )
        j.out["actionMenuHas"] = {
            w: (f'"{w}"' in str(action)) for w in ("Open", "Delete")
        }

    with _Part(j, "appearance"):
        j.out["pageBar"] = j.ev("pageBar !== null", page)
        bar = j.ev("pageBar.createObject(_root)", page)
        j.out["barText"] = _texts(j, bar) if bar is not None else []
        if bar is not None:
            button = _by_name(j, bar, "deviceBindingsAppearanceButton")
            if button is None:
                button = next(
                    (
                        i
                        for i in j.walk(bar)
                        if i.objectName() == "deviceBindingsAppearanceButton"
                    ),
                    None,
                )
            if page.property("displayOpen"):
                j.click(button)
                j.wait_until(
                    lambda: not page.property("displayOpen"), "the panel hidden"
                )
            j.out["barClosedText"] = _texts(j, bar)
            j.click(button)
        j.wait_until(lambda: page.property("displayOpen"), "the Appearance panel")
        if bar is not None:
            bar.setVisible(False)
            bar.deleteLater()
        panel = _by_name(j, page, "deviceBindingsAppearance")
        j.out["panel"] = panel is not None
        j.out["panelLive"] = bool(panel is not None and panel.property("liveOptions"))
        _shot(j, win, "config_page_appearance.png")
        j.ev("toggleAppearance(); true", page)
        j.wait_until(
            lambda: not page.property("displayOpen"), "the Appearance panel closed"
        )
        j.out["panelClosed"] = not page.property("displayOpen")

    with _Part(j, "jump"):
        j.ev("actionPane.closePaneNow(); true", page)
        stick = j.stick(STICK)
        j.press(stick, 5, True)
        tree = next(
            i
            for i in j.walk(page)
            if i.metaObject().className().startswith("ControlTree")
        )
        j.out["liveDecoration"] = bool(tree.property("liveDecoration"))
        try:
            j.wait_until(
                lambda: tree.property("highlightKey") == B5, "Button 5 shown", timeout=6
            )
        except Exception as exc:  # noqa: BLE001
            j.out["jumpWait"] = str(exc)
        j.out["highlightKey"] = tree.property("highlightKey")
        j.QTest.qWait(100)
        _shot(j, win, "config_page_live.png")
        j.press(stick, 5, False)


def main() -> None:
    from _harness import Journey as _J

    _J(_before).run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = run_journey(pathlib.Path(__file__), tmp_path_factory.mktemp("cfgpage"))
    if "error" in out:
        raise JourneyIncomplete(f"{out['error']}\n{out.get('traceback', '')}")
    return out


def _clean(result: dict, part: str) -> None:
    assert f"{part}:error" not in result, (
        result.get(f"{part}:error"),
        result.get(f"{part}:traceback"),
    )


def test_the_find_bar_holds_the_type_and_output_boxes_and_ticks(result: dict) -> None:
    _clean(result, "find")
    assert result["find"] and result["actionType"] and result["output"]
    assert result["ticks"] == ["Ungrouped", "No bindings in this mode"]
    assert result["parkGone"]


def test_a_row_click_opens_the_pane_on_that_input(result: dict) -> None:
    _clean(result, "rowClick")
    assert result["paneKey"] == B2
    assert result["closeAfterOk"]


def test_the_row_menu_matches_the_logical_style(result: dict) -> None:
    _clean(result, "menu")
    assert result["menuKey"] == B2
    assert not result["deleteWhileOpen"], (
        "S31: no Delete for the input open in the pane"
    )
    has = result["menuHas"]
    for word in (
        "Undo",
        "Redo",
        "Add Action",
        "Rename",
        "History",
        "Module Setup…",
        "Clear Name",
        "Delete actions…",
        "Group as",
        "New Group",
        "By System Name",
        "By Your Name",
        "Group Names A to Z",
    ):
        assert has[word], (word, result["menuRaw"])
    assert not has["Add Inputs"] and not has["Assign Hardware"], result["menuRaw"]
    # PB2: the Row section is Clear Name, then Delete actions…, as on Logical.
    assert result["rowSection"] == ["Clear Name", "Delete actions…"], result["menuRaw"]
    assert result["actionMenuHas"] == {"Open": True, "Delete": True}


def test_the_page_bar_opens_the_shared_appearance_with_live_rows(result: dict) -> None:
    _clean(result, "appearance")
    assert result["pageBar"]
    assert "Appearance…" in result["barClosedText"]
    assert result["panel"] and result["panelLive"]
    assert result["panelClosed"]


def test_a_pressed_button_is_shown_by_the_tree(result: dict) -> None:
    _clean(result, "jump")
    assert result["liveDecoration"]
    assert result["highlightKey"] == B5, result.get("jumpWait")
