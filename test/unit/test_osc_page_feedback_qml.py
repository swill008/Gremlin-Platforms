# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Feedback rows and address patterns on the real OSC page (OSC rewrite,
batch 2), end to end off-screen.

A journey (test/journeys/_harness.py): the app runs in its own process with
a temporary USERPROFILE, the fake joystick driver and a fake vJoy. The story
drives the page's own QML (its menus, row clicks, the inline box, the shared
pane's editor and OK, the Change Address dialog) as a user would:

1. Stopped: the input row's menu has Add Feedback and a "Companion
   feedback" section (Key text, Key color); Add Feedback puts a feedback
   row under the input after its action (S153, S156); the inline box turns
   it off in OSC's file; a click on the row opens OscFeedbackEditor in the
   pane; an address typed there and OK is written as one Undo step (S156);
   a pattern address is refused on the editor's error line (S149); Delete…
   asks first (01 S140).
2. Change Address… shows why "/fader/[1" is refused inside the dialog and
   OK is off (S152); "/deck/*" shows "Matches N of the addresses seen".
3. Running: the page is locked, yet a feedback row still opens in the pane
   with OK, an edit is written at once, and the inline box and the row's
   menu still work (S155).

Spec: 09 S149, S152-S156.
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, JourneyIncomplete, run_journey  # noqa: E402

ADDRESS = "/deck/1"


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


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    out = []
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        row = {}
        for role, name in names.items():
            value = model.data(index, role)
            plain = isinstance(value, (str, int, float, bool, type(None)))
            row[name] = value if plain else str(value)
        out.append(row)
    return out


def _setup(j: Journey) -> str:
    """The OSC input /deck/1 with a Map to vJoy action; its parent key."""
    from gremlin import osc_device_file, plugin_manager
    from gremlin.modules import ids
    from gremlin.osc import OscDevice
    from gremlin.signal import signal
    from gremlin.types import InputType

    row = OscDevice().create(InputType.JoystickButton, label=ADDRESS)
    osc_device_file.save(who="test")
    signal.oscDeviceModified.emit()
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = 3
    action.vjoy_input_type = InputType.JoystickButton
    mode = j.profile.modes.first_mode
    item = j.profile.get_input_item(ids.OSC, row.input_type, row.input_id, mode, True)
    item.osc_uid = row.uid
    item.add_item_binding().root_action.insert_action(action, "children")
    j.settle()
    return f"parent:button:{row.input_id}"


def _open_page(j: Journey) -> tuple[Any, Any]:  # noqa: ANN401
    from gremlin.ui.osc_layout import OscLayoutModel

    j.ev('openConfigurationForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: j.backend.uiState.currentTab == "osc", "the OSC page")
    layout = j.wait_until(lambda: j.win.findChild(OscLayoutModel), "the layout model")
    page = j.wait_until(lambda: _page(j), "the OscPage item")
    return page, layout


def _page(j: Journey) -> Any:  # noqa: ANN401
    for item in j.walk(j.win.contentItem()):
        if item.metaObject().className().startswith("OscPage") and item.isVisible():
            return item
    return None


def _visible(j: Journey, root: Any, name: str) -> list:  # noqa: ANN401
    return [i for i in j.walk(root) if i.objectName() == name and i.isVisible()]


def _with_text(j: Journey, root: Any, text: str) -> Any:  # noqa: ANN401
    for i in j.walk(root):
        if i.isVisible() and str(i.property("text") or "") == text:
            return i
    return None


def _mouse(j: Journey, item: Any, right: bool = False) -> None:  # noqa: ANN401
    from PySide6 import QtCore

    p = item.mapToScene(QtCore.QPointF(min(40.0, item.width() / 2), item.height() / 2))
    button = (
        QtCore.Qt.MouseButton.RightButton if right else QtCore.Qt.MouseButton.LeftButton
    )
    j.QTest.mouseClick(
        j.win, button, QtCore.Qt.KeyboardModifier.NoModifier, p.toPoint()
    )
    j.settle()


def _type(j: Journey, field: Any, text: str) -> None:  # noqa: ANN401
    from PySide6 import QtCore

    field.forceActiveFocus()
    QtCore.QMetaObject.invokeMethod(field, "selectAll")
    for char in text:
        j.QTest.keyClick(j.win, char)
    j.QTest.keyClick(j.win, QtCore.Qt.Key.Key_Tab)
    j.settle()


def _pane_ok(j: Journey, page: Any) -> Any:  # noqa: ANN401
    pane = j.ev("_pane", page)
    for i in j.walk(pane):
        if (
            i.isVisible()
            and i.property("text") == "OK"
            and "Button" in i.metaObject().className()
        ):
            return i
    return None


def _menu_texts(j: Journey, page: Any, key: str) -> dict:  # noqa: ANN401
    code = (
        '_tree.select("%s", false); _menuKey = "%s"; _menuTitle = "t"; _menuUser = "";'
        ' _menuGroup = ""; _menuOnRow = true; _menuOnGroup = false;'
        " (function(m) { var s = {};"
        " s.quick = m.quick.map(function(r) { return r.text });"
        " m.sections.forEach(function(x) {"
        " s[x.title] = x.items.map(function(r) { return r.text }) });"
        " return JSON.stringify(s) })(_layoutMenuModel())" % (key, key)
    )
    import json

    return json.loads(j.ev(code, page))


def _feedback(j: Journey) -> list[dict]:  # noqa: ANN401
    from gremlin import osc_device_file

    return osc_device_file.read_feedback()


def _part_stopped(j: Journey, page: Any, layout: Any, parent: str) -> None:  # noqa: ANN401
    out = j.out
    menu = _menu_texts(j, page, parent)
    out["1:menu-quick"] = menu.get("quick", [])
    out["1:menu-companion"] = menu.get("Companion feedback", [])
    # The menu's own Add Feedback entry.
    j.ev(
        "_layoutMenuModel().quick.filter(function(r) {"
        " return r.text === 'Add Feedback' })[0].run(); true",
        page,
    )
    j.settle()
    rows = _rows(layout)
    under = [r for r in rows if r["parentKey"] == parent and r["rowKind"] != "parent"]
    out["1:under-input"] = [r["rowKind"] for r in under]
    fb = [r for r in rows if r["rowKind"] == "feedback"]
    out["1:file-rows"] = len(_feedback(j))
    key, title = fb[0]["key"], fb[0]["title"]

    # The inline box turns the row off in OSC's file.
    boxes = _visible(j, page, "oscFeedbackRowOn")
    out["1:inline-boxes"] = len(boxes)
    _mouse(j, boxes[0])
    out["1:enabled-after-box"] = _feedback(j)[0]["enabled"]

    # A click on the row opens the editor in the pane.
    _mouse(j, _with_text(j, page, title))
    out["1:pane-key"] = j.ev("_pane.paneKey", page)
    out["1:editor-shown"] = bool(_visible(j, page, "oscFeedbackEditor"))
    field = _visible(j, page, "oscFeedbackAddress")[0]
    _type(j, field, "/gear/*")
    out["1:pattern-error"] = str(layout.feedbackEditor.get("error", ""))
    _type(j, field, "/gear/lamp")
    undo_before = j.ev("_layout.canUndo", page)
    j.click(_pane_ok(j, page))
    j.settle()
    out["1:address-after-ok"] = _feedback(j)[0]["address"]
    out["1:undo-after-ok"] = [undo_before, j.ev("_layout.canUndo", page)]
    j.ev("_pane.closeNow(); _layout.undo(); true", page)
    j.settle()
    out["1:address-after-undo"] = _feedback(j)[0]["address"]

    # Delete… asks first.
    j.ev('deleteFeedbackAsked("%s", "x"); true' % key, page)
    root = j.win.contentItem()
    while root.parentItem() is not None:
        root = root.parentItem()
    confirm = j.wait_until(
        lambda: (_visible(j, root, "confirmAction") or [None])[0],
        "the confirm button",
        5,
    )
    out["1:asked"] = confirm is not None
    out["1:rows-while-asking"] = len(_feedback(j))
    j.click(confirm)
    j.settle()
    out["1:rows-after-delete"] = len(_feedback(j))
    j.ev("_layout.undo(); true", page)
    j.settle()


def _part_change_address(j: Journey, page: Any, parent: str) -> None:  # noqa: ANN401
    from gremlin import osc_traffic

    out = j.out
    for address in ("/deck/1", "/deck/2", "/fader/1"):
        osc_traffic.note("in", address, [1], ("192.168.1.30", 51234), [])
    j.ev('_askChangeAddress("%s"); true' % parent, page)
    j.settle()
    field = "_addressDialog.contentItem.children[1].children[0]"
    ok = "_addressDialog.contentItem.children[1].children[1]"
    j.ev(field + '.text = "/fader/[1"; true', page)
    j.settle()
    out["2:error"] = j.ev("_addressDialog.errorText", page)
    out["2:ok-enabled-bad"] = j.ev(ok + ".enabled", page)
    j.ev(field + '.text = "/deck/*"; true', page)
    j.settle()
    out["2:hint"] = j.ev("_addressDialog.hintText", page)
    out["2:ok-enabled-good"] = j.ev(ok + ".enabled", page)
    j.ev("_addressDialog.close(); true", page)
    j.settle()


def _part_running(j: Journey, page: Any, layout: Any) -> None:  # noqa: ANN401
    out = j.out
    j.backend.toggleActiveState()
    j.wait_until(lambda: j.backend.runner.is_running(), "the profile running", 10)
    j.settle()
    out["3:locked"] = j.ev("editorLocked", page)
    fb = [r for r in _rows(layout) if r["rowKind"] == "feedback"]
    key, title = fb[0]["key"], fb[0]["title"]
    _mouse(j, _with_text(j, page, title))
    out["3:pane-key"] = j.ev("_pane.paneKey", page)
    out["3:lock-line"] = bool(_visible(j, page, "oscPaneLocked"))
    field = _visible(j, page, "oscFeedbackMax")[0]
    _type(j, field, "5")
    ok = _pane_ok(j, page)
    out["3:ok-shown"] = ok is not None
    if ok is not None:
        j.click(ok)
        j.settle()
    out["3:max-after-ok"] = _feedback(j)[0]["max"]
    j.ev("_pane.closeNow(); true", page)
    j.settle()
    before = _feedback(j)[0]["enabled"]
    _mouse(j, _visible(j, page, "oscFeedbackRowOn")[0])
    out["3:box-toggles"] = [before, _feedback(j)[0]["enabled"]]
    j.ev('_fbKey = ""; true', page)
    _mouse(j, _with_text(j, page, title), right=True)
    out["3:menu-key"] = j.ev("_fbKey", page) == key
    j.backend.toggleActiveState()
    j.settle()


def story(j: Journey) -> None:
    j.win.setWidth(1600)
    j.win.setHeight(950)
    parent = _setup(j)
    page, layout = _open_page(j)
    with _Part(j, "1"):
        _part_stopped(j, page, layout, parent)
    with _Part(j, "2"):
        _part_change_address(j, page, parent)
    with _Part(j, "3"):
        _part_running(j, page, layout)


def main() -> None:
    def before(j: Journey) -> None:
        import gremlin.osc as gosc

        # No socket: the page and Run work without the OSC listener.
        gosc.OscRuntime._bind = lambda self: None
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_page_feedback"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    part = key.split(":", 1)[0]
    raise JourneyIncomplete(
        f"Part {part} never reached {key!r}.\n"
        f"Error: {out.get(part + ':error', out.get('error', '(none)'))}\n"
        f"{out.get(part + ':traceback', out.get('traceback', ''))}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


def test_input_menu_offers_feedback_and_companion_section(run: dict) -> None:
    assert "Add Feedback" in _step(run, "1:menu-quick")
    assert _step(run, "1:menu-companion") == ["Key text", "Key color"]


def test_add_feedback_puts_a_row_under_the_input_after_its_action(run: dict) -> None:
    assert _step(run, "1:under-input") == ["child", "feedback"]
    assert _step(run, "1:file-rows") == 1


def test_inline_box_turns_the_row_off(run: dict) -> None:
    assert _step(run, "1:inline-boxes") == 1
    assert _step(run, "1:enabled-after-box") is False


def test_row_opens_the_editor_and_ok_is_one_undo_step(run: dict) -> None:
    assert _step(run, "1:pane-key").startswith("feedback:")
    assert _step(run, "1:editor-shown") is True
    assert "pattern" in _step(run, "1:pattern-error")
    assert _step(run, "1:address-after-ok") == "/gear/lamp"
    assert _step(run, "1:undo-after-ok")[1] is True
    assert _step(run, "1:address-after-undo") == ADDRESS


def test_delete_feedback_asks_first(run: dict) -> None:
    assert _step(run, "1:asked") is True
    assert _step(run, "1:rows-while-asking") == 1
    assert _step(run, "1:rows-after-delete") == 0


def test_change_address_shows_the_pattern_error_and_match_hint(run: dict) -> None:
    assert "never closed" in _step(run, "2:error")
    assert _step(run, "2:ok-enabled-bad") is False
    assert _step(run, "2:hint") == "Matches 2 of the addresses seen"
    assert _step(run, "2:ok-enabled-good") is True


def test_feedback_stays_editable_while_running(run: dict) -> None:
    assert _step(run, "3:locked") is True
    assert _step(run, "3:pane-key").startswith("feedback:")
    assert _step(run, "3:lock-line") is False
    assert _step(run, "3:ok-shown") is True
    assert _step(run, "3:max-after-ok") == 5
    before, after = _step(run, "3:box-toggles")
    assert after is (not before)
    assert _step(run, "3:menu-key") is True


if __name__ == "__main__":
    main()
