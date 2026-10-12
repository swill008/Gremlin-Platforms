# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox Output View's list, end to end on the real program (XO-LIST,
user 1a-5a, 2026-10-12; 03 S139).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver (the
shared RIG: pJoy Pro, Saitek X52 and two Twin Sticks) and the Xbox driver
reported missing (nothing touches ViGEmBus). The open profile has two Map
to Xbox actions from two devices onto pad 1's A (pJoy Pro button 1, Saitek
X52 button 2) and one onto Left Stick X (pJoy Pro axis 1). The Output View
is opened the way Help's Open link does (view.xboxOutput), then:

1. "Show only bound controls" is ticked the first time (only A and Left
   Stick X show); Clear unticks it, and the page opened again keeps it
   unticked (saved with the fold state);
2. then the list shows every Xbox control in pad order, no group header;
   A has two source lines (device name and input), Left Stick X one, the
   others none;
3. the Find bar's text, type choice and "Show only bound controls" narrow
   the rows;
4. view only: no grip, a right-click opens no menu, a click selects and
   opens no action pane;
5. Appearance: the page-bar button shows it, a setting changed and saved is
   stored under list appearance key "xbox-output", and the page opened
   again loads it;
6. a Map to Xbox added onto B shows under B without opening the page again.

Each part records its own values (an error in one doesn't hide the others).
"""

from __future__ import annotations

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

SENDING = "Show only bound controls"


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part; an error is recorded under the part's name and the
    next part still runs."""

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


def _xbox(j: Journey, uid: Any, kind: str, number: int, target: str) -> None:  # noqa: ANN401
    """A Map to Xbox action (pad 1) on a stick input, in the open profile."""
    from gremlin import plugin_manager
    from gremlin.types import InputType
    from vigem.xbox import XboxTarget

    input_type = InputType.JoystickAxis if kind == "axis" else InputType.JoystickButton
    action = plugin_manager.PluginManager().create_instance("Map to Xbox", input_type)
    action.xbox_device_id = 1
    action.xbox_target = XboxTarget.from_string(target)
    item = j.profile.get_input_item(uid, input_type, number, "Default", True)
    item.add_item_binding().root_action.insert_action(action, "children")


def _actions_edited() -> None:
    """What an action editor sends after an edit (ActionModel)."""
    from gremlin.signal import signal

    signal.actionsChanged.emit()


def _page(j: Journey) -> Any:  # noqa: ANN401
    from PySide6 import QtQuick

    item = j.ev("_xboxLoader.item")
    return item if isinstance(item, QtQuick.QQuickItem) else None


def _named(root: Any, name: str) -> Any:  # noqa: ANN401
    return next((i for i in Journey.walk(root) if i.objectName() == name), None)


def _shown(item: Any) -> bool:  # noqa: ANN401
    while item is not None:
        if not item.isVisible():
            return False
        item = item.parentItem()
    return True


def _model(j: Journey) -> Any:  # noqa: ANN401
    """Pad 1's list (its section on the page, D-XBOX-PADS)."""
    page = _page(j)
    assert page is not None, "the Xbox Output View is not open"
    return j.wait_until(lambda: j.ev("padList(1)", page), "pad 1's list")


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    return Journey.catalog_rows(model)


def _parents(model: Any) -> list[str]:  # noqa: ANN401
    return [str(r.get("title")) for r in _rows(model) if r.get("rowKind") == "parent"]


def _sources(model: Any) -> dict[str, list[str]]:  # noqa: ANN401
    """Each parent's title -> its child lines' titles, in list order."""
    out: dict[str, list[str]] = {}
    titles = {}
    for row in _rows(model):
        if row.get("rowKind") == "parent":
            titles[row.get("key")] = str(row.get("title"))
            out[str(row.get("title"))] = []
        elif row.get("rowKind") == "child":
            parent = titles.get(row.get("parentKey"), f"? {row.get('parentKey')}")
            out.setdefault(parent, []).append(str(row.get("title")))
    return out


def _open_page(j: Journey) -> Any:  # noqa: ANN401
    j.ev("Commands.trigger('view.xboxOutput')")
    j.wait_until(lambda: _page(j) is not None, "the Xbox Output View")
    model = _model(j)
    j.wait_until(lambda: (model.property("parentCount") or 0) > 0, "the control rows")
    j.settle()
    return model


def _popups_open(j: Journey) -> list[str]:
    """Menus and popups that are open in the main window."""
    from PySide6 import QtCore

    found = []
    for obj in j.win.findChildren(QtCore.QObject):
        name = obj.metaObject().className()
        if ("Popup" in name or "Menu" in name) and obj.property("opened") is True:
            found.append(f"{name}:{obj.objectName()}")
    return found


def _count_signals(tree: Any, names: list[str]) -> dict[str, list[int]]:  # noqa: ANN401
    """Counts each of the tree's own QML signals as it is sent."""
    from PySide6 import QtCore

    counts: dict[str, list[int]] = {}
    meta = tree.metaObject()
    for i in range(meta.methodCount()):
        method = meta.method(i)
        name = bytes(method.name()).decode()
        if name not in names or method.methodType() != method.MethodType.Signal:
            continue
        box = counts.setdefault(name, [0])
        sig = "2" + bytes(method.methodSignature()).decode()
        QtCore.QObject.connect(tree, sig, lambda *a, b=box: b.__setitem__(0, b[0] + 1))
    return counts


def _click(j: Journey, item: Any, button: Any) -> dict:  # noqa: ANN401
    """A real mouse click at the middle of item, through the window."""
    from PySide6 import QtCore, QtTest

    centre = item.mapToScene(
        QtCore.QPointF(item.width() / 2, item.height() / 2)
    ).toPoint()
    QtTest.QTest.mouseClick(
        j.win, button, QtCore.Qt.KeyboardModifier.NoModifier, centre
    )
    j.settle()
    return {"x": centre.x(), "y": centre.y(), "h": j.win.height()}


def _find_bar(j: Journey) -> Any:  # noqa: ANN401
    page = _page(j)
    box = _named(page, "xboxOutputFind")
    assert box is not None, "no xboxOutputFind box"
    bar = box.parentItem()
    while bar is not None and bar.metaObject().indexOfMethod("isChecked(QVariant)") < 0:
        bar = bar.parentItem()
    assert bar is not None, "no ControlFindBar around the Find box"
    return box, bar


def _part_rows(j: Journey) -> None:
    out = j.out
    from gremlin.ui.input_pairing import device_label
    from vigem.xbox import XboxTarget

    model = _model(j)
    rows = _rows(model)
    out["rows:parents"] = _parents(model)
    out["rows:expected"] = [t.label for t in XboxTarget]
    out["rows:kinds"] = sorted({str(r.get("rowKind")) for r in rows})
    out["rows:keyA"] = next(
        (r.get("key") for r in rows if r.get("title") == "A"), None
    )
    out["rows:keyLSX"] = next(
        (r.get("key") for r in rows if r.get("title") == "Left Stick X"), None
    )
    out["rows:groupNames"] = sorted(
        {str(r.get("groupName") or "") for r in rows} - {""}
    )
    tree = _named(_page(j), "xboxOutputTree1")
    out["rows:treeShowGroups"] = tree.property("showGroups") if tree else None
    out["rows:shownGroupRows"] = sum(
        1
        for i in Journey.walk(tree)
        if i.property("rowKind") == "group" and _shown(i)
    ) if tree else -1
    sources = _sources(model)
    out["sources:A"] = sorted(sources.get("A", []))
    out["sources:LSX"] = sources.get("Left Stick X", [])
    out["sources:others"] = {
        k: v for k, v in sources.items() if k not in ("A", "Left Stick X") and v
    }
    out["sources:childCountA"] = next(
        (r.get("childCount") for r in rows if r.get("title") == "A"), None
    )
    pjoy = str(j.stick("pJoy Pro").device_guid.uuid)
    x52 = str(j.stick("Saitek X52").device_guid.uuid)
    out["sources:expectA"] = sorted(
        [f"{device_label(pjoy)} · Button 1", f"{device_label(x52)} · Button 2"]
    )
    out["sources:expectLSX"] = [f"{device_label(pjoy)} · Axis 1"]
    out["sources:sending"] = sorted(
        str(r.get("title"))
        for r in rows
        if r.get("rowKind") == "parent" and r.get("sending")
    )


def _part_find(j: Journey) -> None:
    out = j.out
    model = _model(j)
    box, bar = _find_bar(j)
    box.setProperty("text", "Left Stick")
    j.settle()
    out["find:text"] = _parents(model)
    box.setProperty("text", "Saitek")
    j.settle()
    out["find:source"] = _parents(model)
    j.ev("clear(); true", bar)
    j.settle()
    out["find:cleared"] = len(_parents(model))

    combo = next(
        (
            i
            for i in Journey.walk(bar)
            if "ComboBox" in i.metaObject().className()
        ),
        None,
    )
    assert combo is not None, "no type choice in the Find bar"
    labels = [str(x) for x in (j.ev("model", combo) or [])]
    out["find:typeLabels"] = labels
    for label, key in (("Triggers", "triggers"), ("Sticks", "sticks"),
                       ("Buttons", "buttons"), ("D-Pad", "dpad")):
        index = labels.index(label) if label in labels else -1
        if index < 0:
            out[f"find:{key}"] = f"no {label!r} choice"
            continue
        j.ev(f"currentIndex = {index}; activated({index}); true", combo)
        j.settle()
        out[f"find:{key}"] = _parents(model)
    j.ev("clear(); true", bar)
    j.settle()

    tick = next(
        (i for i in Journey.walk(bar) if i.property("text") == SENDING and _shown(i)),
        None,
    )
    assert tick is not None, f"no {SENDING!r} tick"
    j.ev("checked = true; clicked(); true", tick)
    j.settle()
    out["find:sending"] = _parents(model)
    out["find:noCantSend"] = not any(
        i.property("text") == "Binding output not found" and _shown(i)
        for i in Journey.walk(bar)
    )
    out["find:noUndo"] = not _shown(_named(bar, "xboxOutputUndoBar"))
    j.ev("clear(); true", bar)
    j.settle()
    out["find:final"] = len(_parents(model))


def _part_view_only(j: Journey) -> None:
    from PySide6 import QtCore

    out = j.out
    page = _page(j)
    tree = _named(page, "xboxOutputTree1")
    assert tree is not None, "no xboxOutputTree1"
    out["view:readOnly"] = tree.property("readOnly")
    out["view:grips"] = sum(
        1 for i in Journey.walk(tree) if i.objectName() == "rowGrip" and _shown(i)
    )
    # A tall window shows pad 1's face and its whole list (the page
    # scrolls, not the list).
    j.win.setHeight(2400)
    j.settle()
    key = "parent:button:a"
    j.ev(f"showKey({key!r}); true", tree)
    j.settle()
    row = next(
        (
            i
            for i in Journey.walk(tree)
            if i.property("key") == key
            and i.property("rowKind") == "parent"
            and _shown(i)
        ),
        None,
    )
    assert row is not None, "row A is not drawn"
    counts = _count_signals(
        tree,
        ["parentMenu", "groupMenu", "actionMenu", "pageMenu", "parentClicked",
         "actionClicked", "feedbackMenu"],
    )
    windows = len(j.app.topLevelWindows())
    out["view:popupsBefore"] = _popups_open(j)
    out["view:rightAt"] = _click(j, row, QtCore.Qt.MouseButton.RightButton)
    out["view:popupsAfterRight"] = _popups_open(j)
    out["view:leftAt"] = _click(j, row, QtCore.Qt.MouseButton.LeftButton)
    out["view:popupsAfterLeft"] = _popups_open(j)
    out["view:signals"] = {k: v[0] for k, v in counts.items()}
    out["view:signalsWatched"] = sorted(counts)
    picked = j.ev("picked", tree)
    out["view:picked"] = [str(p) for p in (picked or [])]
    out["view:newWindows"] = len(j.app.topLevelWindows()) - windows
    out["view:actionPane"] = any(
        "pane" in i.objectName().lower() and _shown(i) for i in Journey.walk(page)
    )
    out["view:room"] = [j.ev("uiState.currentRoom"), j.ev("uiState.currentTab")]


def _bar_button(j: Journey) -> Any:  # noqa: ANN401
    loader = j.ev("_pageBarLoader")
    root = loader.property("item") if loader is not None else None
    if root is None:
        return None
    return _named(root, "xboxOutputAppearanceButton")


def _part_appearance(j: Journey) -> None:
    from gremlin.ui import window_placement

    out = j.out
    page = _page(j)
    button = j.wait_until(lambda: _bar_button(j), "the page-bar Appearance button")
    out["look:buttonShown"] = _shown(button)
    out["look:buttonBefore"] = button.property("text")
    out["look:otherButton"] = _shown(
        _named(j.win.contentItem(), "outputAppearanceButton")
    )
    # The panel is open by default (like the other list pages): the button
    # hides it and shows it again.
    j.click(button)
    j.settle()
    out["look:buttonHidden"] = _bar_button(j).property("text")
    j.click(_bar_button(j))
    j.settle()
    out["look:buttonAfter"] = _bar_button(j).property("text")
    panel = _named(page, "xboxOutputAppearance")
    assert panel is not None, "no xboxOutputAppearance panel"
    out["look:panelShown"] = _shown(panel)
    out["look:pageKey"] = panel.property("pageKey")
    panel.setProperty("parentBold", False)
    panel.setProperty("parentHeight", 61)
    j.settle()
    tree = _named(page, "xboxOutputTree1")
    out["look:treeFollows"] = [
        tree.property("parentBold"),
        tree.property("parentHeight"),
    ]
    j.ev("save(); true", panel)
    j.settle()
    stored = window_placement.list_appearance("xbox-output")
    out["look:stored"] = {
        k: stored.get(k) for k in ("parentBold", "parentHeight") if k in stored
    }
    out["look:storedKeys"] = len(stored)
    for other in ("device-bindings", "keyboard", "logical", "osc"):
        if window_placement.list_appearance(other).get("parentHeight") == 61:
            out.setdefault("look:leaked", []).append(other)
    # A fresh page loads it.
    j.ev("closeWorkRoomNow()")
    j.settle()
    j.wait_until(lambda: _page(j) is None, "the page closed")
    _open_page(j)
    page = _page(j)
    out["look:samePage"] = False
    panel = _named(page, "xboxOutputAppearance")
    tree = _named(page, "xboxOutputTree1")
    out["look:reloaded"] = [
        panel.property("parentBold"),
        panel.property("parentHeight"),
    ]
    out["look:reloadedTree"] = [
        tree.property("parentBold"),
        tree.property("parentHeight"),
    ]
    # The tick left off by Clear stays off on the page opened again.
    out["look:tickReloaded"] = j.ev("isChecked('sending')", _find_bar(j)[1])
    out["look:rowsReloaded"] = len(_parents(_model(j)))
    # Back to defaults for the parts after this one.
    if panel.metaObject().indexOfMethod("reset()") >= 0:
        j.ev("reset(); true", panel)
    j.settle()


def _part_live_binding(j: Journey) -> None:
    out = j.out
    model = _model(j)
    page = _page(j)
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    out["bind:before"] = _sources(model).get("B", [])
    _xbox(j, pjoy, "button", 3, "b")
    _actions_edited()
    out["bind:after"] = j.await_value(
        lambda: len(_sources(model).get("B", [])), 1, timeout=5.0
    )
    out["bind:lines"] = _sources(model).get("B", [])
    out["bind:samePage"] = _page(j) is page
    out["bind:sending"] = j.await_value(
        lambda: any(
            r.get("title") == "B" and r.get("sending") for r in _rows(model)
        ),
        True,
    )


def story(j: Journey) -> None:
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    x52 = j.stick("Saitek X52").device_guid.uuid
    _xbox(j, pjoy, "button", 1, "a")
    _xbox(j, x52, "button", 2, "a")
    _xbox(j, pjoy, "axis", 1, "left_stick_x")
    _actions_edited()
    j.settle()
    with _Part(j, "open"):
        _open_page(j)
        j.out["open:room"] = [j.ev("uiState.currentRoom"), j.ev("uiState.currentTab")]
        _box, bar = _find_bar(j)
        j.out["open:tickFirst"] = j.ev("isChecked('sending')", bar)
        j.out["open:rowsFirst"] = _parents(_model(j))
        # Clear unticks it; the rest of the story starts from every row.
        j.ev("clear(); true", bar)
        j.settle()
        j.out["open:rowsCleared"] = len(_parents(_model(j)))
    for name, part in (
        ("rows", _part_rows),
        ("find", _part_find),
        ("view", _part_view_only),
        ("look", _part_appearance),
        ("bind", _part_live_binding),
    ):
        with _Part(j, name):
            part(j)


def main() -> None:
    def before(j: Journey) -> None:
        from gremlin.modules import output

        # Nothing reaches ViGEmBus: the driver is reported missing.
        output.xbox_driver_installed = lambda: False
        output.xbox_driver_version = lambda: ""
        output.xbox_available = lambda: False
        output.xbox_error = lambda: ""

    Journey(before, **RIG).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("xbox_list"))


def _no_error(run: dict, part: str) -> None:
    assert f"{part}:error" not in run, (
        run.get(f"{part}:error"),
        run.get(f"{part}:traceback"),
    )


def test_the_page_opens(run: dict) -> None:
    _no_error(run, "open")
    assert step(run, "open:room") == ["configuration", "xbox"]


def test_show_only_bound_is_ticked_first_and_remembered(run: dict) -> None:
    _no_error(run, "open")
    assert step(run, "open:tickFirst") is True
    assert step(run, "open:rowsFirst") == ["Left Stick X", "A"]  # pad order
    assert step(run, "open:rowsCleared") == 22
    _no_error(run, "look")
    assert step(run, "look:tickReloaded") is False
    assert step(run, "look:rowsReloaded") == 22


def test_every_control_in_pad_order_without_a_group_header(run: dict) -> None:
    _no_error(run, "rows")
    assert step(run, "rows:parents") == step(run, "rows:expected")
    assert "group" not in step(run, "rows:kinds")
    assert step(run, "rows:groupNames") == []
    assert step(run, "rows:treeShowGroups") is False
    assert step(run, "rows:shownGroupRows") == 0
    assert step(run, "rows:keyA") == "parent:button:a"
    assert step(run, "rows:keyLSX") == "parent:axis:left_stick_x"


def test_each_source_is_a_line_under_its_control(run: dict) -> None:
    _no_error(run, "rows")
    assert step(run, "sources:A") == step(run, "sources:expectA")
    assert step(run, "sources:childCountA") == 2
    assert step(run, "sources:LSX") == step(run, "sources:expectLSX")
    assert step(run, "sources:others") == {}
    assert step(run, "sources:sending") == ["A", "Left Stick X"]


def test_find_text_type_and_sending_narrow_the_rows(run: dict) -> None:
    _no_error(run, "find")
    assert step(run, "find:text") == ["Left Stick X", "Left Stick Y"]
    assert step(run, "find:source") == ["A"]
    assert step(run, "find:cleared") == 22
    assert step(run, "find:triggers") == ["Left Trigger", "Right Trigger"]
    assert step(run, "find:sticks") == [
        "Left Stick X", "Left Stick Y", "Right Stick X", "Right Stick Y"
    ]
    buttons = step(run, "find:buttons")
    assert "A" in buttons and "Guide" in buttons
    assert not any("Stick" in b or "Trigger" in b for b in buttons)
    dpad = step(run, "find:dpad")
    assert dpad and all(d.startswith("DPad") for d in dpad)
    assert step(run, "find:sending") == ["Left Stick X", "A"]  # pad order
    assert step(run, "find:noCantSend") is True
    assert step(run, "find:noUndo") is True
    assert step(run, "find:final") == 22


def test_view_only_no_grip_no_menu_no_pane(run: dict) -> None:
    _no_error(run, "view")
    assert step(run, "view:readOnly") is True
    assert step(run, "view:grips") == 0
    at = step(run, "view:rightAt")
    assert 0 <= at["y"] < at["h"], at  # the click landed in the window
    assert step(run, "view:popupsAfterRight") == step(run, "view:popupsBefore")
    assert step(run, "view:popupsAfterLeft") == step(run, "view:popupsBefore")
    signals = step(run, "view:signals")
    assert step(run, "view:signalsWatched"), "the tree's signals were not found"
    assert all(n == 0 for n in signals.values()), signals
    assert step(run, "view:picked") == ["parent:button:a"]  # a click selects
    assert step(run, "view:newWindows") == 0
    assert step(run, "view:actionPane") is False
    assert step(run, "view:room") == ["configuration", "xbox"]


def test_appearance_is_saved_under_xbox_output_and_loaded_again(run: dict) -> None:
    _no_error(run, "look")
    assert step(run, "look:buttonShown") is True
    assert step(run, "look:buttonBefore") == "Hide Appearance"  # open by default
    assert step(run, "look:buttonHidden") == "Appearance…"
    assert step(run, "look:otherButton") is False
    assert step(run, "look:buttonAfter") == "Hide Appearance"
    assert step(run, "look:panelShown") is True
    assert step(run, "look:pageKey") == "xbox-output"
    assert step(run, "look:treeFollows") == [False, 61]
    assert step(run, "look:stored") == {"parentBold": False, "parentHeight": 61}
    assert "look:leaked" not in run
    assert step(run, "look:reloaded") == [False, 61]
    assert step(run, "look:reloadedTree") == [False, 61]


def test_a_new_binding_shows_without_reopening(run: dict) -> None:
    _no_error(run, "bind")
    assert step(run, "bind:before") == []
    assert step(run, "bind:after") == 1
    lines = step(run, "bind:lines")
    assert len(lines) == 1 and lines[0].endswith("· Button 3"), lines
    assert step(run, "bind:samePage") is True
    assert step(run, "bind:sending") is True


def test_no_program_errors(run: dict) -> None:
    assert run.get("error") is None, (run.get("error"), run.get("traceback"))
    assert run.get("_errors") == []


if __name__ == "__main__":
    main()
