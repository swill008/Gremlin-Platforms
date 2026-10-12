# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Find uses… (Search, D-01-SEARCH) in the right-click menus: each one
calls the main window's openSearch(query) with the thing clicked.

1. A list page's row (Device Bindings here; the four pages share
   control_menu.js and ControlLayoutModel.findQuery): the input's device,
   InputType and id. Several rows picked: no Find uses….
2. An Xbox Output View row (a real right-click on the view-only list):
   {kind: "output", output: "xbox", outputId: pad, inputType, inputId}.
3. A vJoy Viewer chip (a real right-click; the stick's button sends to
   vJoy 1 button 2): {kind: "output", output: "vjoy", outputId, inputType
   button, inputId}.
4. A mode in Manage Modes (a real right-click on its name): {kind: "mode"}.

A journey (test/journeys/_harness.py): the app runs in its own process
off-screen with fake hardware; the main window's openSearch is stood in for
by an object registered as the main window (Helpers.setMainWindow), which
records what it is asked.
"""

from __future__ import annotations

import json
import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    RIG,
    Journey,
    run_journey,
    step,
)

STICK = "pJoy Pro"
CARD = "pjoy_pro"


class _Part:
    """Runs one part; an error is recorded under its name and the next part
    still runs."""

    def __init__(self, j: Journey, name: str) -> None:
        self.j = j
        self.name = name

    def __enter__(self) -> _Part:
        return self

    def __exit__(self, kind: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
        if exc is not None:
            self.j.out[f"{self.name}:error"] = f"{kind.__name__}: {exc}"
            self.j.out[f"{self.name}:traceback"] = traceback.format_exc()[-3000:]
        return True


def _asked(j: Journey, fake: Any) -> list[dict]:  # noqa: ANN401
    """What openSearch was asked since the last look, and forget it."""
    out = [json.loads(q) for q in json.loads(str(j.ev("JSON.stringify(asked)", fake)))]
    j.ev("asked = []; true", fake)
    return out


def _right_click(j: Journey, window: Any, item: Any) -> None:  # noqa: ANN401
    """A real right-click on item's middle. window is item's window as the
    journey holds it (not item.window(): a second wrapper of the main window
    leaves the journey's own one deleted when it goes)."""
    from PySide6 import QtCore

    p = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    j.QTest.mouseClick(
        window,
        QtCore.Qt.MouseButton.RightButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        p.toPoint(),
    )
    j.settle()


# Runs the open menu's Find uses… row; returns its rows' texts and whether
# the row ran. M. is the menu: "" when evaluated on the menu itself, else
# its id in the context the code runs in.
_RUN_FIND = """(function() {
    var rows = M.model.quick.map(function(r) { return r.text })
    var it = M.model.quick.filter(function(r) { return r.text === "Find uses…" })[0]
    if (it && it.enabled) it.run()
    return JSON.stringify({ opened: M.opened, title: M.model.title, rows: rows,
                            ran: !!(it && it.enabled) })
})()"""


def _run_code(menu: str = "") -> str:
    return _RUN_FIND.replace("M.", f"{menu}." if menu else "")


def _open_menu(j: Journey, root: Any) -> Any:  # noqa: ANN401
    """The open ContextMenu under root (a window or an item)."""
    from PySide6 import QtCore, QtQuick

    start = root.contentItem() if isinstance(root, QtQuick.QQuickWindow) else root
    for item in [root, *Journey.walk(start)]:
        try:
            for obj in item.findChildren(QtCore.QObject):
                name = obj.metaObject().className()
                if name.startswith("ContextMenu") and obj.property("opened") is True:
                    return obj
        except RuntimeError:  # a live row rebuilt while looked at
            continue
    raise AssertionError("no open ContextMenu")


def _run_find(j: Journey, root: Any) -> dict:  # noqa: ANN401
    menu = j.wait_until(lambda: _try_menu(j, root), "the open menu")
    out = json.loads(str(j.ev(_run_code(), menu)))
    # Not ev("close()"): that name reaches the main window's close().
    menu.setProperty("visible", False)
    j.settle()
    return out


def _try_menu(j: Journey, root: Any) -> Any:  # noqa: ANN401
    try:
        return _open_menu(j, root)
    except AssertionError:
        return None


def _find_item(j: Journey, root: Any, test: Any) -> Any:  # noqa: ANN401
    return next((i for i in Journey.walk(root) if test(i)), None)


def _part_row(j: Journey, fake: Any) -> None:  # noqa: ANN401
    uid = j.stick(STICK).device_guid.uuid
    j.map_button(uid, 2, j.profile.modes.first_mode, 2)
    j.settle()
    j.ev(f"openDeviceBindingsForCard(_moduleModel.cardMap({json.dumps(CARD)}))")

    def page() -> Any:  # noqa: ANN401
        from PySide6 import QtQuick

        for w in j.app.topLevelWindows():
            if isinstance(w, QtQuick.QQuickWindow) and w.isVisible():
                found = _find_item(
                    j,
                    w.contentItem(),
                    lambda i: i.isVisible()
                    and i.metaObject().className().startswith("DeviceBindingsPage"),
                )
                if found is not None:
                    return found
        return None

    p = j.wait_until(page, "the stick's Device Bindings page")
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    layout = j.wait_until(lambda: p.findChild(HardwareLayoutModel), "the page's model")
    j.wait_until(lambda: (layout.property("parentCount") or 0) > 0, "the page's rows")
    key = "parent:button:2"
    j.ev(f"_menuOnRow = true; _menuOnGroup = false; _menuKey = {key!r}; true", p)
    j.ev(f"_picked = [{key!r}]; true", p)
    j.out["row:menu"] = json.loads(
        str(
            j.ev(
                "JSON.stringify((function(m) { var it = m.quick.filter(function(r)"
                " { return r.text === 'Find uses\u2026' })[0]; if (it) it.run();"
                " return m.quick.map(function(r) { return r.text }) })"
                "(_layoutMenuModel()))",
                p,
            )
        )
    )
    j.out["row:asked"] = _asked(j, fake)
    j.out["row:guid"] = str(uid)
    j.ev(f"_picked = [{key!r}, 'parent:button:1']; true", p)
    j.out["row:many"] = json.loads(
        str(
            j.ev(
                "JSON.stringify(_layoutMenuModel().quick"
                ".map(function(r) { return r.text }))",
                p,
            )
        )
    )
    j.ev("_menuOnRow = false; _picked = []; true", p)


def _part_xbox(j: Journey, fake: Any) -> None:  # noqa: ANN401
    from PySide6 import QtQuick

    from gremlin import plugin_manager
    from gremlin.signal import signal
    from gremlin.types import InputType
    from vigem.xbox import XboxTarget

    uid = j.stick(STICK).device_guid.uuid
    action = plugin_manager.PluginManager().create_instance(
        "Map to Xbox", InputType.JoystickButton
    )
    action.xbox_device_id = 1
    action.xbox_target = XboxTarget.from_string("a")
    item = j.profile.get_input_item(uid, InputType.JoystickButton, 1, "Default", True)
    item.add_item_binding().root_action.insert_action(action, "children")
    signal.actionsChanged.emit()
    j.settle()
    j.ev("Commands.trigger('view.xboxOutput')")
    view = j.wait_until(
        lambda: (
            lambda it: it if isinstance(it, QtQuick.QQuickItem) else None
        )(j.ev("_xboxLoader.item")),
        "the Xbox Output View",
    )
    section = j.wait_until(
        lambda: _find_item(j, view, lambda i: i.objectName() == "xboxPadSection1"),
        "pad 1's section",
    )
    j.win.setHeight(2400)
    j.settle()
    tree = _find_item(j, section, lambda i: i.objectName() == "xboxOutputTree1")
    key = "parent:button:a"
    j.ev(f"showKey({key!r}); true", tree)
    j.settle()
    row = j.wait_until(
        lambda: _find_item(
            j,
            tree,
            lambda i: i.property("key") == key
            and i.property("rowKind") == "parent"
            and i.isVisible(),
        ),
        "row A",
    )
    _right_click(j, j.win, row)
    j.out["xbox:menu"] = _run_find(j, section)
    j.out["xbox:asked"] = _asked(j, fake)


def _part_vjoy(j: Journey, fake: Any) -> None:  # noqa: ANN401
    # The stick's button 2 sends to vJoy 1 button 2 (_part_row's binding).
    j.ev("Commands.trigger('tools.vjoyViewer')")
    win = j.window("vJoy Viewer")
    area = j.wait_until(
        lambda: _find_item(
            j, win.contentItem(), lambda i: i.objectName() == "vjoyViewerChipMenu"
        ),
        "a chip",
    )
    j.settle()
    j.QTest.qWait(300)  # the cards are laid out after their models fill
    _right_click(j, win, area)
    # Through the chip (its file's context names the menu): the card's live
    # rows are rebuilt too often to hold on to the menu object itself.
    j.out["vjoy:menu"] = json.loads(
        str(j.ev(_run_code("_chipMenu"), area))
    )
    j.ev("_chipMenu.visible = false; true", area)
    j.settle()
    j.out["vjoy:asked"] = _asked(j, fake)
    win.close()
    j.settle()


def _part_modes(j: Journey, fake: Any) -> None:  # noqa: ANN401
    j.ev("Commands.trigger('tools.manageModes')")
    win = j.window("Manage Modes")
    area = j.wait_until(
        lambda: _find_item(
            j, win.contentItem(), lambda i: i.objectName() == "modeNameMenu"
        ),
        "a mode's name",
    )
    _right_click(j, win, area)
    j.out["modes:menu"] = _run_find(j, win)
    j.out["modes:asked"] = _asked(j, fake)
    win.close()
    j.settle()


def story(j: Journey) -> None:
    fake = j.ev(
        "(function() {"
        " var f = Qt.createQmlObject('import QtQuick; QtObject {"
        " property var asked: [];"
        " function openSearch(q) { asked = asked.concat([JSON.stringify(q)]) } }',"
        " _root, 'fakeMain');"
        " Helpers.setMainWindow(f); return f })()"
    )
    assert fake is not None, "no stand-in main window"
    for name, part in (
        ("row", _part_row),
        ("xbox", _part_xbox),
        ("vjoy", _part_vjoy),
        ("modes", _part_modes),
    ):
        with _Part(j, name):
            part(j, fake)
    j.ev("Helpers.setMainWindow(_root); true")


def main() -> None:
    def before(j: Journey) -> None:
        from gremlin.modules import output

        j.input_module(STICK)
        j.vjoy_module()

        # Nothing reaches ViGEmBus: the driver is reported missing.
        output.xbox_driver_installed = lambda: False
        output.xbox_driver_version = lambda: ""
        output.xbox_available = lambda: False
        output.xbox_error = lambda: ""

    Journey(before, **RIG).run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("find_uses"))


def _no_error(run: dict, part: str) -> None:
    assert f"{part}:error" not in run, (
        run.get(f"{part}:error"),
        run.get(f"{part}:traceback"),
    )


def test_a_list_row_finds_uses_of_its_input(run: dict) -> None:
    _no_error(run, "row")
    menu = step(run, "row:menu")
    assert menu.index("Find uses…") == menu.index("History") + 1, menu
    assert step(run, "row:asked") == [
        {
            "kind": "input",
            "deviceGuid": step(run, "row:guid"),
            "inputType": 3,
            "inputId": 2,
        }
    ]
    # Several rows picked: one input to search for is not known.
    assert "Find uses…" not in step(run, "row:many")


def test_an_xbox_output_row_finds_uses_of_the_pad_control(run: dict) -> None:
    _no_error(run, "xbox")
    menu = step(run, "xbox:menu")
    assert menu["opened"] is True, menu  # the real right-click opened it
    assert menu["rows"] == ["Find uses…"] and menu["ran"], menu
    assert step(run, "xbox:asked") == [
        {"kind": "output", "output": "xbox", "outputId": 1, "inputType": 3,
         "inputId": "a"}
    ]


def test_a_vjoy_viewer_chip_finds_uses_of_its_output(run: dict) -> None:
    _no_error(run, "vjoy")
    menu = step(run, "vjoy:menu")
    assert menu["opened"] is True, menu  # the real right-click opened it
    assert menu["rows"] == ["Find uses…"] and menu["ran"], menu
    assert step(run, "vjoy:asked") == [
        {"kind": "output", "output": "vjoy", "outputId": 1, "inputType": 3,
         "inputId": 2}
    ]


def test_a_mode_finds_its_uses(run: dict) -> None:
    _no_error(run, "modes")
    menu = step(run, "modes:menu")
    assert menu["opened"] is True, menu
    assert menu["rows"] == ["Find uses…"] and menu["ran"], menu
    asked = step(run, "modes:asked")
    assert len(asked) == 1 and asked[0]["kind"] == "mode", asked
    assert asked[0]["mode"] == menu["title"]
