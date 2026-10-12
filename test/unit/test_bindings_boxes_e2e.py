# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Bindings boxes on bindable rows, end to end on the real program
(batch I, D-05-BINDINGS-BOXES).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver and its
"pJoy Pro", and a fake vJoy behind the output module. The profile gives
button 1 two actions (Map to vJoy and Map to Xbox), button 2 one, button 3
none. The Device Bindings page is opened from the stick's Home card:

1. Rows: button 1 shows "Bindings", "[2]" and two boxes with the targets'
   text; button 2 "[1]" and one box; button 3 nothing. The strips start at
   the same x on rows whose names differ in length.
2. The page's Appearance panel, through its own controls (section
   "Bindings"): Brackets off, Corners Square, Target text color changed:
   the row follows; Save Appearance writes the keys to the page's
   Appearance JSON for the shown device. Reset to defaults puts the contract
   defaults back.
3. The Keyboard page shows the boxes for a bound key too.

Spec: 05 S142, S125; D-05-BINDINGS-BOXES.
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
    Journey,
    JourneyIncomplete,
    run_journey,
)

B1, B2, B3 = "parent:button:1", "parent:button:2", "parent:button:3"
LONG_NAME = "Throttle cutoff switch with a long name"
NEW_COLOR = "#00c853"


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """One part of the story; an error is recorded under its name and the
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


def _named(root: Any, name: str) -> list[Any]:  # noqa: ANN401
    return [i for i in Journey.walk(root) if i.objectName() == name]


def _shown(item: Any) -> bool:  # noqa: ANN401
    """Visible on screen: it and every parent visible, with a size."""
    if item is None or not item.isVisible() or item.width() <= 0:
        return False
    return True


def _text_of(item: Any) -> str:  # noqa: ANN401
    """The item's text, or the first visible text inside it."""
    value = item.property("text")
    if isinstance(value, str) and value:
        return value
    for child in Journey.walk(item):
        value = child.property("text")
        if isinstance(value, str) and value and child.isVisible():
            return value
    return ""


def _text_color(item: Any) -> str:  # noqa: ANN401
    for child in Journey.walk(item):
        text = child.property("text")
        if isinstance(text, str) and text and child.property("color") is not None:
            return child.property("color").name().lower()
    return ""


def _scene_x(item: Any) -> float:  # noqa: ANN401
    from PySide6 import QtCore

    return round(item.mapToScene(QtCore.QPointF(0, 0)).x(), 1)


def _tree(j: Journey, prefix: str) -> Any:  # noqa: ANN401
    """The page's ControlTree (the list, not the find bar)."""

    def find() -> Any:  # noqa: ANN401
        for item in j.walk(j.win.contentItem()):
            if (
                item.property("namePrefix") == prefix
                and item.property("dragMime") is not None
                and item.isVisible()
            ):
                return item
        return None

    return j.wait_until(find, f"the {prefix} list")


def _row(tree: Any, key: str) -> Any:  # noqa: ANN401
    for item in Journey.walk(tree):
        if item.property("key") == key and item.property("shown") is not None:
            return item
    return None


def _row_state(tree: Any, key: str) -> dict:  # noqa: ANN401
    """What a row shows after its name."""
    row = _row(tree, key)
    if row is None:
        return {"row": False}
    words = [i for i in _named(row, "bindingsWord") if _shown(i)]
    counts = [i for i in _named(row, "bindingsCount") if _shown(i)]
    boxes = [i for i in _named(row, "bindingBox") if _shown(i)]
    names = _named(row, "rowName")
    return {
        "row": True,
        "word": _text_of(words[0]) if words else None,
        "word_x": _scene_x(words[0]) if words else None,
        "count": _text_of(counts[0]) if counts else None,
        "boxes": [_text_of(b) for b in boxes],
        "box_radius": [float(b.property("radius") or 0) for b in boxes],
        "box_color": [_text_color(b) for b in boxes],
        "name_right": (
            _scene_x(names[0]) + names[0].width() if names else None
        ),
        # The old grey summary (gone with this batch).
        "old_summary": any(_shown(i) for i in _named(row, "actionSummary")),
    }


def _action(name: str, vjoy_button: int = 0) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        name, InputType.JoystickButton
    )
    if name == "Map to vJoy":
        action.vjoy_device_id = 1
        action.vjoy_input_id = vjoy_button
        action.vjoy_input_type = InputType.JoystickButton
    return action


def _bind(j: Journey, uid: Any, input_type: Any, input_id: Any, actions: list) -> None:  # noqa: ANN401
    item = j.profile.get_input_item(uid, input_type, input_id, "Default", True)
    root = item.add_item_binding().root_action
    for action in actions:
        root.insert_action(action, "children")


def _targets(actions: list) -> list[str]:
    from gremlin.ui.binding_catalog import summarize_action

    return [summarize_action(a)[1] for a in actions]


def _panel_item(panel: Any, test: Any) -> Any:  # noqa: ANN401
    for item in Journey.walk(panel):
        try:
            if test(item):
                return item
        except Exception:  # noqa: BLE001, S112
            continue
    return None


def _labelled(fold: Any, words: str) -> Any:  # noqa: ANN401
    """The control on the row whose label starts with words."""
    label = _panel_item(
        fold,
        lambda i: str(i.property("text") or "").lower().startswith(words.lower())
        and i.property("checked") is None
        and i.property("currentIndex") is None,
    )
    assert label is not None, f"no {words!r} row in the Bindings section"
    row = label.parentItem()
    control = _panel_item(
        row,
        lambda i: i is not label
        and (
            i.property("currentIndex") is not None
            or str(i.property("text") or "").startswith("Choose")
        ),
    )
    assert control is not None, f"no control on the {words!r} row"
    return control


def _part_rows(j: Journey, tree: Any, made: dict) -> None:  # noqa: ANN401
    out = j.out
    for key in (B1, B2, B3):
        out[f"1:{key}"] = _row_state(tree, key)
    out["1:want-b1"] = _targets(made["b1"])
    out["1:want-b2"] = _targets(made["b2"])
    out["1:tree-defaults"] = _tree_props(tree)


_PROPS = (
    "showBindings",
    "bindingsWordSize",
    "bindingsNumberSize",
    "bindingsNumberMono",
    "bindingsBrackets",
    "bindingTargetSize",
    "bindingTargetMono",
    "bindingTargetBorderWidth",
    "bindingTargetRounded",
    "bindingTargetRadius",
    "bindingTargetSpacing",
)


def _tree_props(tree: Any) -> dict:  # noqa: ANN401
    values: dict = {}
    for name in _PROPS:
        values[name] = tree.property(name)
    color = tree.property("bindingTargetTextColor")
    values["bindingTargetTextColor"] = color.name().lower() if color else None
    return values


def _part_appearance(j: Journey, page: Any, tree: Any) -> None:  # noqa: ANN401
    from gremlin.ui import window_placement

    out = j.out
    panel = j.item(j.win, "deviceBindingsAppearance")
    assert panel is not None, "no Device Bindings Appearance panel"
    if not panel.isVisible():
        j.ev("toggleAppearance(); true", page)
        j.wait_until(panel.isVisible, "the Appearance panel")
    fold = _panel_item(
        panel,
        lambda i: i.property("title") == "Bindings" and i.property("open") is not None,
    )
    assert fold is not None, "no Bindings section in the Appearance panel"
    j.ev("toggled(true); true", fold)
    j.settle()
    out["2:section-open"] = bool(fold.property("open"))

    # Brackets off: its checkbox, as a click does.
    brackets = _panel_item(
        fold,
        lambda i: i.property("text") == "Brackets"
        and i.property("checked") is not None,
    )
    assert brackets is not None, "no Brackets checkbox"
    j.ev("toggle(); clicked(); true", brackets)
    # Corners: Square.
    corners = _labelled(fold, "Corners")
    index = j.ev("find('Square')", corners)
    assert index is not None and int(index) >= 0, "no Square corner choice"
    j.ev(f"currentIndex = {int(index)}; activated({int(index)}); true", corners)
    # Target text color: Choose..., then the color dialog's OK.
    choose = _labelled(fold, "Target text color")
    j.click(choose)
    j.settle()
    # The dialog is the panel file's own: reached from the button's context.
    j.ev(f'_colorDlg.selectedColor = "{NEW_COLOR}"; _colorDlg.accept(); true', choose)
    j.settle()
    out["2:row"] = _row_state(tree, B1)
    out["2:tree"] = _tree_props(tree)

    # Save Appearance: the page's JSON keeps the keys.
    save = _panel_item(
        panel,
        lambda i: str(i.property("text") or "") == "Save\nAppearance"
        and i.property("highlighted") is not None,
    )
    j.click(save)
    j.settle()
    # Saved for the shown device (05 S125: per device on Device Bindings).
    saved = window_placement.list_appearance_for(
        "device-bindings", str(page.property("guid"))
    )
    keys = ("bindingsBrackets", "bindingTargetRounded", "bindingTargetTextColor")
    out["2:saved"] = {key: saved.get(key) for key in keys}
    out["2:saved-old-key"] = "showActionSummary" in saved

    # Reset to defaults (this section only).
    reset = _panel_item(
        fold,
        lambda i: i.property("text") == "Reset to defaults"
        and i.property("highlighted") is not None,
    )
    assert reset is not None, "no Reset to defaults button in Bindings"
    j.click(reset)
    j.settle()
    out["2:reset-tree"] = _tree_props(tree)
    out["2:reset-row"] = _row_state(tree, B1)


def _part_keyboard(j: Journey, made: list) -> None:
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel

    out = j.out
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(
        lambda: j.backend.uiState.currentTab == "keyboard", "the Keyboard page"
    )
    model = j.wait_until(
        lambda: j.win.findChild(KeyboardLayoutModel), "the Keyboard page's model"
    )
    tree = _tree(j, "keyboard")
    keys = j.wait_until(
        lambda: [
            r["key"]
            for r in j.catalog_rows(model)
            if r.get("rowKind") == "parent"
        ],
        "the bound key's row",
    )
    j.settle()
    out["3:keys"] = keys
    out["3:row"] = _row_state(tree, keys[0])
    out["3:want"] = _targets(made)


def story(j: Journey) -> None:
    import dill
    from gremlin.signal import signal
    from gremlin.types import InputType

    uid = j.stick().device_guid.uuid
    made = {
        "b1": [_action("Map to vJoy", 3), _action("Map to Xbox")],
        "b2": [_action("Map to vJoy", 4)],
        "key": [_action("Map to vJoy", 5)],
    }
    _bind(j, uid, InputType.JoystickButton, 1, made["b1"])
    _bind(j, uid, InputType.JoystickButton, 2, made["b2"])
    _bind(j, dill.UUID_Keyboard, InputType.Keyboard, (30, False), made["key"])
    signal.profileChanged.emit()
    j.settle()
    page = None
    tree = None
    with _Part(j, "1"):
        layout = j.open_device_bindings("pjoy_pro")
        page = j.ev("deviceBindingsPane()")
        # Names of different lengths: button 2 gets a long one.
        layout.setUserName(B2, LONG_NAME)
        j.settle()
        tree = _tree(j, "deviceBindings")
        j.wait_until(lambda: _row(tree, B3) is not None, "the rows")
        j.settle()
        _part_rows(j, tree, made)
    with _Part(j, "2"):
        if page is None or tree is None:
            raise RuntimeError("part 1 did not open the page")
        _part_appearance(j, page, tree)
    with _Part(j, "3"):
        _part_keyboard(j, made["key"])


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2, 3])
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("bindings_boxes"))


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


def test_two_actions_show_bindings_two_and_two_boxes(run: dict) -> None:
    row = _step(run, f"1:{B1}")
    want = _step(run, "1:want-b1")
    assert row["word"] == "Bindings", row
    assert row["count"] == "[2]", row
    assert row["boxes"] == want, row
    assert len(want) == 2 and all(want), want
    assert row["old_summary"] is False, row


def test_one_action_shows_one_box(run: dict) -> None:
    row = _step(run, f"1:{B2}")
    assert row["word"] == "Bindings", row
    assert row["count"] == "[1]", row
    assert row["boxes"] == _step(run, "1:want-b2"), row


def test_an_unbound_row_shows_nothing(run: dict) -> None:
    row = _step(run, f"1:{B3}")
    assert row["row"] is True, row
    assert row["word"] is None and row["count"] is None, row
    assert row["boxes"] == [], row


def test_the_strips_start_in_one_column(run: dict) -> None:
    short, long = _step(run, f"1:{B1}"), _step(run, f"1:{B2}")
    assert short["word_x"] is not None and long["word_x"] is not None
    assert abs(short["word_x"] - long["word_x"]) <= 1, (short, long)
    # After the longest name, not over it.
    assert long["word_x"] >= long["name_right"], long


def test_the_contract_defaults(run: dict) -> None:
    props = _step(run, "1:tree-defaults")
    assert props["showBindings"] is True, props
    assert props["bindingsBrackets"] is True, props
    assert props["bindingTargetRounded"] is True, props
    assert props["bindingsNumberMono"] is True and props["bindingTargetMono"] is True
    assert props["bindingTargetBorderWidth"] == 1, props
    assert props["bindingTargetRadius"] == 5, props
    assert props["bindingTargetSpacing"] == 6, props
    for size in ("bindingsWordSize", "bindingsNumberSize", "bindingTargetSize"):
        assert props[size] == 12, props
    row = _step(run, f"1:{B1}")
    assert all(r > 0 for r in row["box_radius"]), row
    assert row["box_color"] == [props["bindingTargetTextColor"]] * 2, row


def test_appearance_controls_change_the_row(run: dict) -> None:
    assert _step(run, "2:section-open") is True
    tree = _step(run, "2:tree")
    assert tree["bindingsBrackets"] is False, tree
    assert tree["bindingTargetRounded"] is False, tree
    assert tree["bindingTargetTextColor"] == NEW_COLOR, tree
    row = _step(run, "2:row")
    assert row["count"] == "2", row
    assert row["box_radius"] == [0.0, 0.0], row
    assert row["box_color"] == [NEW_COLOR, NEW_COLOR], row


def test_save_appearance_keeps_the_keys(run: dict) -> None:
    saved = _step(run, "2:saved")
    assert saved["bindingsBrackets"] is False, saved
    assert saved["bindingTargetRounded"] is False, saved
    assert str(saved["bindingTargetTextColor"]).lower() == NEW_COLOR, saved
    assert _step(run, "2:saved-old-key") is False


def test_reset_to_defaults_restores_the_contract_defaults(run: dict) -> None:
    assert _step(run, "2:reset-tree") == _step(run, "1:tree-defaults")
    row = _step(run, "2:reset-row")
    assert row["count"] == "[2]", row
    assert all(r > 0 for r in row["box_radius"]), row


def test_the_keyboard_page_shows_bindings(run: dict) -> None:
    assert len(_step(run, "3:keys")) == 1
    row = _step(run, "3:row")
    assert row["word"] == "Bindings", row
    assert row["count"] == "[1]", row
    assert row["boxes"] == _step(run, "3:want"), row


if __name__ == "__main__":
    main()
