# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Group details and Row details, end to end on the real program (batch L).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver and its
"pJoy Pro" (its module claims buttons 1-3, axis 1 and hat 1), and a fake
vJoy 1 (64 buttons) behind the output module. The profile, in mode
"Default":

- button 1: Map to vJoy (button 3) and Map to Xbox;
- button 2: Map to vJoy to vJoy button 100, which vJoy 1 doesn't have
  (output not found), and a custom name;
- button 3: nothing;
- axis 1: a Condition holding Map to vJoy (axis 1);
- hat 1: nothing;
- mode "Combat": button 1 has a Map to vJoy (button 5).

The Device Bindings page is opened from the stick's Home card and its
Appearance panel is driven through its own checkboxes:

1. The Home card reads "⚠ 1 output not found"; the group line by default
   reads "3 buttons [3 bindings] · 1 axis [1 binding] · 1 hat [0 bindings]".
2. Every Group detail on: each detail's exact text, Output not found in the
   warning colour; Hide empty drops "[0 bindings]" (the hat stays); Wrap
   details on a narrow window gives more than one line, off gives one.
3. Every Row detail on: each row's exact details (system name only on
   button 2, no bindings only on button 3, output not found in the warning
   colour, has a condition on the axis, other modes on button 1).
4. The Find ticks read "Output not found" and "No bindings in this mode";
   the Find hint reads "System name, custom name, or group".

Spec: 05 (batch L contract: Group details, Row details, renames).
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
    claim_everything,
    run_journey,
)

B1, B2, B3 = "parent:button:1", "parent:button:2", "parent:button:3"
A1, H1 = "parent:axis:1", "parent:hat:1"
GROUP = "group:"
CUSTOM = "Fire"
MISSING_BUTTON = 100  # vJoy 1 has 64

GROUP_SETTINGS = [
    "Controls by type",
    "Bindings by type",
    "No bindings",
    "Output not found",
    "Output devices",
    "Action types",
    "Custom names",
    "Other modes",
]
ROW_SETTINGS = [
    "Bindings and targets",
    "Action types",
    "Output not found",
    "Other modes",
    "System name",
    "Has a condition",
    "No bindings",
]


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
    """On screen: it and every parent visible, with a size."""
    while item is not None:
        if not item.isVisible():
            return False
        item = item.parentItem()
    return True


def _text_of(item: Any) -> str:  # noqa: ANN401
    """The item's text, or the visible texts inside it joined."""
    value = item.property("text")
    if isinstance(value, str) and value:
        return value
    parts = []
    for child in Journey.walk(item):
        if child is item:
            continue
        value = child.property("text")
        if isinstance(value, str) and value and _shown(child):
            parts.append(value)
    return "".join(parts)


def _color_of(item: Any) -> str:  # noqa: ANN401
    for child in Journey.walk(item):
        text = child.property("text")
        color = child.property("color")
        if isinstance(text, str) and text and color is not None:
            return color.name().lower()
    return ""


def _scene_y(item: Any) -> float:  # noqa: ANN401
    from PySide6 import QtCore

    return round(item.mapToScene(QtCore.QPointF(0, 0)).y(), 0)


def _scene_x(item: Any) -> float:  # noqa: ANN401
    from PySide6 import QtCore

    return round(item.mapToScene(QtCore.QPointF(0, 0)).x(), 0)


def _tree(j: Journey) -> Any:  # noqa: ANN401
    def find() -> Any:  # noqa: ANN401
        for item in j.walk(j.win.contentItem()):
            if (
                item.property("namePrefix") == "deviceBindings"
                and item.property("dragMime") is not None
                and item.isVisible()
            ):
                return item
        return None

    return j.wait_until(find, "the Device Bindings list")


def _row(tree: Any, key: str) -> Any:  # noqa: ANN401
    for item in Journey.walk(tree):
        if item.property("key") == key and item.property("shown") is not None:
            return item
    return None


def _details(tree: Any, key: str, kind: str) -> dict:  # noqa: ANN401
    """A row's details (kind "group" or "row"): each visible detail's text
    and colour in reading order, the line as shown, and how many lines."""
    row = _row(tree, key)
    if row is None:
        return {"row": False}
    boxes = [i for i in _named(row, f"{kind}Details") if _shown(i)]
    pieces = [i for i in _named(row, f"{kind}Detail") if _shown(i)]
    pieces.sort(key=lambda i: (_scene_y(i), _scene_x(i)))
    texts = [_text_of(i) for i in pieces]
    texts = [t for t in texts if t]
    whole = _text_of(boxes[0]) if boxes else ""
    lines = 0
    if boxes:
        count = boxes[0].property("lineCount")
        if isinstance(count, int) and count > 0:
            lines = count
    if not lines and pieces:
        lines = len({_scene_y(i) for i in pieces})
    return {
        "row": True,
        "box": bool(boxes),
        "pieces": texts,
        "colors": [_color_of(i) for i in pieces if _text_of(i)],
        "whole": whole,
        "lines": lines,
        "truncated": bool(boxes and boxes[0].property("truncated")),
    }


def _panel_item(panel: Any, test: Any) -> Any:  # noqa: ANN401
    for item in Journey.walk(panel):
        try:
            if test(item):
                return item
        except Exception:  # noqa: BLE001, S112
            continue
    return None


def _open_panel(j: Journey, page: Any) -> Any:  # noqa: ANN401
    panel = j.item(j.win, "deviceBindingsAppearance")
    assert panel is not None, "no Device Bindings Appearance panel"
    if not panel.isVisible():
        j.ev("toggleAppearance(); true", page)
        j.wait_until(panel.isVisible, "the Appearance panel")
    return panel


def _section(j: Journey, panel: Any, title: str) -> Any:  # noqa: ANN401
    fold = _panel_item(
        panel,
        lambda i: i.property("title") == title and i.property("open") is not None,
    )
    assert fold is not None, f"no {title} section in the Appearance panel"
    if not fold.property("open"):
        j.ev("toggled(true); true", fold)
        j.settle()
    return fold


def _box(fold: Any, label: str) -> Any:  # noqa: ANN401
    box = _panel_item(
        fold,
        lambda i: i.property("text") == label and i.property("checked") is not None,
    )
    assert box is not None, f"no {label!r} checkbox"
    return box


def _set(j: Journey, fold: Any, label: str, on: bool) -> None:  # noqa: ANN401
    """The checkbox to on, as a click does."""
    box = _box(fold, label)
    if bool(box.property("checked")) != on:
        j.ev("toggle(); clicked(); true", box)
    j.settle()


def _warn_colors(j: Journey) -> list[str]:
    found = []
    for name in ("warn", "warning"):
        try:
            value = j.ev(f'Qt.color(Style.{name}).toString()')
        except Exception:  # noqa: BLE001, S112
            continue
        if value:
            found.append(str(value).lower())
    return found


def _home_card(j: Journey) -> list[str]:
    texts = []
    for item in j.walk(j.win.contentItem()):
        value = item.property("cantSendText")
        if isinstance(value, str) and value and item.property("cantSendCount"):
            texts.append(value)
    return texts


def _action(name: str, kind: Any, vjoy_id: int = 0) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(name, kind)
    if name == "Map to vJoy":
        action.vjoy_device_id = 1
        action.vjoy_input_id = vjoy_id
        action.vjoy_input_type = (
            InputType.JoystickAxis
            if kind == InputType.JoystickAxis
            else InputType.JoystickButton
        )
    return action


def _bind(j: Journey, uid: Any, kind: Any, hw: int, mode: str, actions: list) -> None:  # noqa: ANN401
    item = j.profile.get_input_item(uid, kind, hw, mode, True)
    root = item.add_item_binding().root_action
    for action in actions:
        root.insert_action(action, "children")


def _profile(j: Journey) -> None:
    from gremlin.signal import signal
    from gremlin.types import InputType

    button, axis = InputType.JoystickButton, InputType.JoystickAxis
    uid = j.stick().device_guid.uuid
    _bind(
        j,
        uid,
        button,
        1,
        "Default",
        [_action("Map to vJoy", button, 3), _action("Map to Xbox", button)],
    )
    missing = _action("Map to vJoy", button, MISSING_BUTTON)
    _bind(j, uid, button, 2, "Default", [missing])
    condition = _action("Condition", axis)
    condition.insert_action(_action("Map to vJoy", axis, 1), "true")
    _bind(j, uid, axis, 1, "Default", [condition])
    j.profile.modes.add_mode("Combat")
    _bind(j, uid, button, 1, "Combat", [_action("Map to vJoy", button, 5)])
    signal.profileChanged.emit()
    j.settle()


def _part_default(j: Journey) -> tuple[Any, Any, Any]:  # noqa: ANN401
    out = j.out
    out["1:card"] = j.await_value(lambda: _home_card(j), ["⚠ 1 output not found"])
    layout = j.open_device_bindings("pjoy_pro")
    page = j.ev("deviceBindingsPane()")
    layout.setUserName(B2, CUSTOM)
    j.settle()
    tree = _tree(j)
    j.wait_until(lambda: _row(tree, H1) is not None, "the rows")
    j.settle()
    out["1:group"] = _details(tree, GROUP, "group")
    out["1:rows"] = {k: _details(tree, k, "row") for k in (B1, B2, B3, A1, H1)}
    rows = {r["key"]: r for r in j.catalog_rows(layout) if r.get("key")}
    out["1:system-b2"] = rows.get(B2, {}).get("systemName")
    out["1:warn"] = _warn_colors(j)
    return layout, page, tree


def _part_group(j: Journey, page: Any, tree: Any) -> None:  # noqa: ANN401
    out = j.out
    panel = _open_panel(j, page)
    fold = _section(j, panel, "Group details")
    for label in GROUP_SETTINGS:
        _set(j, fold, label, True)
    _set(j, fold, "Wrap details", False)
    _set(j, fold, "Hide empty", False)
    out["2:all"] = _details(tree, GROUP, "group")
    _set(j, fold, "Hide empty", True)
    out["2:hide-empty"] = _details(tree, GROUP, "group")
    _set(j, fold, "Hide empty", False)
    # A narrow window: the long line can't fit on one line.
    width = j.win.width()
    j.win.setWidth(720)
    j.settle()
    _set(j, fold, "Wrap details", True)
    j.QTest.qWait(100)
    out["2:wrap-on"] = _details(tree, GROUP, "group")
    _set(j, fold, "Wrap details", False)
    j.QTest.qWait(100)
    out["2:wrap-off"] = _details(tree, GROUP, "group")
    j.win.setWidth(width)
    j.settle()


def _part_rows(j: Journey, page: Any, tree: Any) -> None:  # noqa: ANN401
    out = j.out
    panel = _open_panel(j, page)
    fold = _section(j, panel, "Row details")
    for label in ROW_SETTINGS:
        _set(j, fold, label, True)
    _set(j, fold, "Wrap details", False)
    j.QTest.qWait(50)
    out["3:rows"] = {k: _details(tree, k, "row") for k in (B1, B2, B3, A1, H1)}


def _part_find(j: Journey) -> None:
    out = j.out
    find = j.item(j.win, "deviceBindingsFind")
    assert find is not None, "no deviceBindingsFind box"
    out["4:hint"] = find.property("placeholder")
    bar = find
    while bar is not None and bar.property("showCantSend") is None:
        bar = bar.parentItem()
    assert bar is not None, "no find bar"
    out["4:ticks"] = [
        str(i.property("text"))
        for i in Journey.walk(bar)
        if i.property("checked") is not None
        and isinstance(i.property("text"), str)
        and i.isVisible()
    ]


def story(j: Journey) -> None:
    from gremlin.modules import output

    # Map to Xbox can be sent (pad 1, the driver there): only button 2's
    # output is not found.
    output.xbox_available = lambda: True  # type: ignore[assignment]
    _profile(j)
    page = tree = None
    with _Part(j, "1"):
        _layout, page, tree = _part_default(j)
    with _Part(j, "2"):
        if tree is None:
            raise RuntimeError("part 1 did not open the page")
        _part_group(j, page, tree)
    with _Part(j, "3"):
        if tree is None:
            raise RuntimeError("part 1 did not open the page")
        _part_rows(j, page, tree)
    with _Part(j, "4"):
        _part_find(j)


def main() -> None:
    def before(j: Journey) -> None:
        import dill
        from gremlin.modules.ids import stored_guid_key

        claim = claim_everything()
        claim.update(buttons=[1, 2, 3], axes=[1], hats=[1])
        j.write_module(
            "pjoy_pro",
            {
                "kind": "control.hardware",
                "device": "pJoy Pro",
                "direction": "source",
                "boundGuidLocal": stored_guid_key(
                    dill.GUID(j.fake_hardware.raw_guid(False))
                ),
                "claim": claim,
                "nodes": [],
            },
        )
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("details"))


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


def _line(details: dict) -> str:
    """The group line as read: the pieces joined by the separator, or the
    one text when the line is a single text."""
    if details.get("pieces"):
        return " · ".join(details["pieces"])
    return details.get("whole", "")


DEFAULT_LINE = "3 buttons [3 bindings] · 1 axis [1 binding] · 1 hat [0 bindings]"


def test_the_home_card_says_one_output_not_found(run: dict) -> None:
    assert _step(run, "1:card") == ["⚠ 1 output not found"]


def test_the_default_group_line(run: dict) -> None:
    group = _step(run, "1:group")
    assert group["row"] and group["box"], group
    assert _line(group) == DEFAULT_LINE, group


def test_every_group_detail(run: dict) -> None:
    group = _step(run, "2:all")
    want = [
        "3 buttons [3 bindings]",
        "1 axis [1 binding]",
        "1 hat [0 bindings]",
        "[2 with no bindings]",
        "[1 output not found]",
        "[outputs: vJoy 1, Xbox 360 Controller]",
        "[3 Map to vJoy, 1 Map to Xbox]",
        "[1 custom name]",
        "[also in mode Combat]",
    ]
    assert _line(group) == " · ".join(want), group


def test_group_output_not_found_is_in_the_warning_colour(run: dict) -> None:
    group = _step(run, "2:all")
    warn = _step(run, "1:warn")
    index = next(
        i for i, t in enumerate(group["pieces"]) if "output not found" in t
    )
    assert group["colors"][index] in warn, (group, warn)
    assert group["colors"][0] not in warn, (group, warn)


def test_hide_empty_drops_zero_bindings(run: dict) -> None:
    line = _line(_step(run, "2:hide-empty"))
    assert "[0 bindings]" not in line, line
    assert "1 hat" in line, line
    assert line.startswith("3 buttons [3 bindings] · 1 axis [1 binding] · 1 hat"), line


def test_wrap_details_wraps_the_group_line(run: dict) -> None:
    on, off = _step(run, "2:wrap-on"), _step(run, "2:wrap-off")
    assert on["lines"] > 1, on
    assert off["lines"] == 1, off


def _row_line(rows: dict, key: str) -> list[str]:
    return rows[key]["pieces"]


def test_every_row_detail(run: dict) -> None:
    rows = _step(run, "3:rows")
    assert _step(run, "1:system-b2") == "Button 2"
    assert _row_line(rows, B1) == [
        "[Map to vJoy, Map to Xbox]",
        "[also in mode Combat]",
    ], rows[B1]
    assert _row_line(rows, B2) == [
        "[Map to vJoy]",
        "[output not found]",
        "[system name: Button 2]",
    ], rows[B2]
    assert _row_line(rows, B3) == ["[no bindings]"], rows[B3]
    assert _row_line(rows, A1) == ["[Map to vJoy]", "[has a condition]"], rows[A1]
    assert _row_line(rows, H1) == ["[no bindings]"], rows[H1]


def test_row_output_not_found_is_in_the_warning_colour(run: dict) -> None:
    rows = _step(run, "3:rows")
    warn = _step(run, "1:warn")
    b2 = rows[B2]
    assert b2["colors"][1] in warn, (b2, warn)
    assert b2["colors"][0] not in warn, (b2, warn)


def test_row_details_are_off_by_default(run: dict) -> None:
    rows = _step(run, "1:rows")
    for key in (B1, B2, B3, A1, H1):
        assert rows[key]["row"] is True, (key, rows[key])
        assert rows[key]["pieces"] == [], (key, rows[key])


def test_find_ticks_and_hint(run: dict) -> None:
    assert _step(run, "4:hint") == "System name, custom name, or group"
    ticks = _step(run, "4:ticks")
    assert "Output not found" in ticks, ticks
    assert "No bindings in this mode" in ticks, ticks
    assert "Can't be sent" not in ticks, ticks
    assert "No actions in this mode" not in ticks, ticks


if __name__ == "__main__":
    main()
