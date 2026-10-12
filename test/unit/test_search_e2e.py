# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Search (to-do 9, "Find in profile"), end to end on the real program
(batch P, user 2026-10-12 "1a 2a 3a 4a 5a, build it").

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake "pJoy Pro" stick and
vJoy 1 and 2 (vJoy 2 has 56 buttons). The profile:

- an OSC input "/fire" maps to vJoy 2 Button 30 (mode Default);
- the stick's Button 1 runs a macro with a vJoy 2 Button 30 step (mode
  "Combat");
- its Button 2 has a condition on vJoy 2 Button 30 (Default);
- its Button 3 has a Change Mode that switches to "Combat" (Default);
- its Button 4 maps to vJoy 2 Button 60, which vJoy 2 doesn't have
  (Combat): the binding's output is not found.

Through the real screens:

1. The toolbar's Search button (after Input Tester) opens the Search window.
2. Output vJoy 2 Button 30: "Sends to this output" (2 uses: the OSC input
   and the macro) and "Checks this output" (1 use: the condition); 3 uses.
3. A click on the macro's result: the stick's Device Bindings page, mode
   Combat, Button 1's row shown; the Search window stays open.
4. Next › moves on to the next result.
5. "Find uses…" on Button 2's row fills the search for that input.
6. Mode "Combat" lists the Change Mode under "Switches to this mode".
7. Output vJoy 2 Button 60 shows the broken binding with
   [binding output not found].

Spec: 01 D-01-SEARCH (Search window, toolbar, Find uses…); batch P contract.
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
    JourneyIncomplete,
    run_journey,
)

STICK = "pJoy Pro"
COMBAT = "Combat"
NOT_FOUND = "[binding output not found]"


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


def _find(root: Any, test: Any) -> Any:  # noqa: ANN401
    for item in Journey.walk(root):
        try:
            if test(item):
                return item
        except Exception:  # noqa: BLE001, S112
            continue
    return None


def _shown(item: Any) -> bool:  # noqa: ANN401
    return item is not None and item.isVisible() and item.width() > 0


def _texts(root: Any) -> list[str]:  # noqa: ANN401
    """Every visible text under root."""
    out = []
    for item in Journey.walk(root):
        value = item.property("text")
        if isinstance(value, str) and value and _shown(item):
            out.append(value)
    return out


def _toolbar_button(j: Journey, caption: str) -> Any:  # noqa: ANN401
    return _find(
        j.win.contentItem(),
        lambda i: i.property("caption") == caption and i.isVisible(),
    )


def _search_window(j: Journey) -> Any:  # noqa: ANN401
    return j.window("Search")


def _model(window: Any) -> Any:  # noqa: ANN401
    from gremlin.ui.usages_model import UsagesModel

    found = window.findChild(UsagesModel)
    assert found is not None, "no UsagesModel in the Search window"
    return found


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    return Journey.catalog_rows(model)


def _results(model: Any) -> list[dict]:  # noqa: ANN401
    keep = ("group", "groupTitle", "deviceName", "mode", "inputLabel", "text")
    return [
        {**{k: r.get(k) for k in keep}, "notFound": bool(r.get("notFound"))}
        for r in _rows(model)
    ]


def _state(model: Any) -> dict:  # noqa: ANN401
    return {
        "count": model.property("count"),
        "groups": [
            {"title": g.get("title"), "count": g.get("count")}
            for g in (model.property("groups") or [])
        ],
        "rows": _results(model),
    }


def _named(window: Any, name: str) -> Any:  # noqa: ANN401
    """A visible item of the Search window by objectName."""
    found = _find(
        window.contentItem(), lambda i: i.objectName() == name and i.isVisible()
    )
    assert found is not None, f"no {name} in the Search window"
    return found


def _kind(j: Journey, window: Any, kind: str) -> None:  # noqa: ANN401
    """One of the kind buttons (Input, Output, Mode, Action type)."""
    j.click(_named(window, f"searchKind:{kind}"))
    j.wait_until(lambda: _model(window).property("kind") == kind, f"kind {kind}")
    j.settle()


def _pick(j: Journey, window: Any, name: str, test: str) -> bool:  # noqa: ANN401
    """Chooses the first row of a picker whose value passes test (a JS
    expression on v), as a click on it does: False when none does."""
    combo = j.wait_until(lambda: _named(window, name), name)
    j.settle()
    return bool(
        j.ev(
            "(function() { var m = model || [];"
            " for (var i = 0; i < m.length; i++) { var v = m[i].value;"
            f" if ({test}) {{ currentIndex = i; activated(i); return true }} }}"
            " return false })()",
            combo,
        )
    )


def _choose_output(j: Journey, window: Any, vjoy: int, button: int) -> bool:  # noqa: ANN401
    """Output, then vJoy <vjoy>, then its Button <button> in the pickers.
    False when the control picker doesn't list the button."""
    from gremlin.types import InputType

    _kind(j, window, "output")
    assert _pick(
        j, window, "searchOutput", f"v.output === 'vjoy' && v.outputId === {vjoy}"
    ), f"vJoy {vjoy} is not in the Output picker"
    j.settle()
    return _pick(
        j,
        window,
        "searchOutputInput",
        f"v.inputType === {InputType.JoystickButton.value} && v.inputId === {button}",
    )


def _result_items(window: Any) -> list[Any]:  # noqa: ANN401
    """The results list's row delegates, by row number."""
    rows = [
        i
        for i in Journey.walk(window.contentItem())
        if i.objectName().startswith("searchRow:") and i.isVisible()
    ]
    return sorted(rows, key=lambda i: int(i.objectName().split(":", 1)[1]))


def _click_row(j: Journey, row: Any) -> None:  # noqa: ANN401
    """A click on a result row (its MouseArea's onClicked)."""
    from PySide6 import QtQuick

    area = next(
        (
            i
            for i in Journey.walk(row)
            if i is not row and i.property("hoverEnabled") is not None
            and i.property("pressAndHoldInterval") is not None
        ),
        None,
    )
    assert isinstance(area, QtQuick.QQuickItem), "no MouseArea on the result row"
    j.ev("clicked(null); true", area)


def _goto_state(j: Journey) -> dict:
    page = j.ev("deviceBindingsPane()")
    tree = None
    if page is not None:
        tree = _find(
            page,
            lambda i: i.property("namePrefix") == "deviceBindings"
            and i.property("dragMime") is not None,
        )
    return {
        "tab": str(j.ev("uiState.currentTab")),
        "mode": str(j.ev("uiState.currentMode")),
        "device": str(page.property("deviceName") or "") if page else "",
        "pane": str(page.property("paneKey") or "") if page else "",
        "shown": str(tree.property("highlightKey") or "") if tree else "",
    }


def _part_open(j: Journey) -> None:
    out = j.out
    button = j.wait_until(lambda: _toolbar_button(j, "Search"), "the Search button")
    tester = _toolbar_button(j, "Input Tester")
    out["1:after-tester"] = bool(tester is not None and button.x() > tester.x())
    out["1:glyph"] = str(button.property("text") or "")
    j.click(button)
    window = _search_window(j)
    out["1:title"] = window.title()


def _part_output(j: Journey) -> None:
    window = _search_window(j)
    assert _choose_output(j, window, 2, 30), "no Button 30 in the control picker"
    model = _model(window)
    j.wait_until(lambda: model.property("count"), "results for vJoy 2 Button 30")
    j.settle()
    j.out["2:state"] = _state(model)
    j.out["2:texts"] = _texts(window.contentItem())


def _part_go(j: Journey) -> None:
    window = _search_window(j)
    rows = _result_items(window)
    j.out["3:rows"] = [str(r.property("text")) for r in rows]
    macro = [r for r in rows if r.property("deviceName") == STICK
             and r.property("inputLabel") == "Button 1"]
    assert macro, f"no macro result among {j.out['3:rows']}"
    j.out["3:index"] = int(macro[0].objectName().split(":", 1)[1])
    _click_row(j, macro[0])
    j.wait_until(
        lambda: _goto_state(j)["pane"] == "parent:button:1", "Button 1 shown"
    )
    j.settle()
    j.out["3:at"] = _goto_state(j)
    j.out["3:window-open"] = window.isVisible()
    j.out["3:current"] = window.property("current")


def _part_next(j: Journey) -> None:
    window = _search_window(j)
    before = _goto_state(j)
    current = window.property("current")
    j.click(_named(window, "searchNext"))
    j.wait_until(lambda: window.property("current") != current, "Next › to move on")
    rows = _rows(_model(window))
    row = rows[window.property("current")]
    if row["deviceName"] == STICK:
        # Settled once the page shows that row (or after 5 s, to show it).
        j.await_value(lambda: _goto_state(j)["pane"], _key(row), 5.0)
    j.settle()
    j.out["4:before"] = before
    j.out["4:index"] = [current, window.property("current")]
    j.out["4:at"] = _goto_state(j)
    j.out["4:row"] = row


def _key(row: dict) -> str:
    return f"parent:button:{row['inputId']}"


def _part_find_uses(j: Journey) -> None:
    from gremlin.types import InputType

    j.open_device_bindings("pjoy_pro")
    page = j.ev("deviceBindingsPane()")
    j.ev(
        "_menuKey = 'parent:button:2'; _menuTitle = 'Button 2';"
        " _menuOnRow = true; _menuOnGroup = false; _picked = []; true",
        page,
    )
    menu = j.ev("_layoutMenuModel()", page)
    labels = [i.get("text") for i in menu.get("quick", [])]
    for section in menu.get("sections", []) or []:
        if section:
            labels.extend(i.get("text") for i in section.get("items", []))
    j.out["5:menu"] = labels
    ran = j.ev(
        "(function() { var m = _layoutMenuModel(); var all = m.quick.slice();"
        " (m.sections || []).forEach(function(s) { if (s) all = all.concat(s.items) });"
        " for (var i = 0; i < all.length; i++) if (all[i].text === 'Find uses…')"
        " { all[i].run(); return true } return false })()",
        page,
    )
    assert ran, f"no Find uses… in the row menu: {labels}"
    window = _search_window(j)
    model = _model(window)
    j.wait_until(lambda: model.property("kind") == "input", "the Input kind")
    j.settle()
    j.out["5:query"] = {
        "kind": model.property("kind"),
        "device": str(model.property("deviceGuid")),
        "inputType": model.property("inputType"),
        "inputId": model.property("inputId"),
    }
    j.out["5:stick"] = str(j.stick(STICK).device_guid.uuid)
    j.out["5:button"] = InputType.JoystickButton.value
    j.out["5:state"] = _state(model)


def _part_mode(j: Journey) -> None:
    window = _search_window(j)
    _kind(j, window, "mode")
    assert _pick(j, window, "searchMode", f"v === {COMBAT!r}"), "no Combat mode"
    model = _model(window)
    j.wait_until(lambda: model.property("count"), "results for mode Combat")
    j.settle()
    j.out["6:state"] = _state(model)


def _part_broken(j: Journey) -> None:
    from gremlin.types import InputType

    window = _search_window(j)
    listed = _choose_output(j, window, 2, 60)
    j.out["7:picker-lists-it"] = listed
    if not listed:
        # The picker lists what vJoy 2 has; the broken binding's control
        # is found the way Find uses… fills the window.
        j.ev(
            "fill({kind: 'output', output: 'vjoy', outputId: 2,"
            f" inputType: {InputType.JoystickButton.value}, inputId: 60}}); true",
            window,
        )
    model = _model(window)
    j.wait_until(lambda: model.property("count"), "results for vJoy 2 Button 60")
    j.settle()
    j.out["7:state"] = _state(model)
    j.out["7:texts"] = _texts(window.contentItem())


# --- the profile ---------------------------------------------------------------


def _profile(j: Journey) -> None:
    from action_plugins.change_mode import ChangeType
    from action_plugins.condition import condition as ca
    from gremlin import macro, plugin_manager
    from gremlin.osc import OSC_DEVICE_UUID, OscDevice
    from gremlin.signal import signal
    from gremlin.types import InputType
    from gremlin.ui.osc_device_model import OscDeviceManagementModel

    B = InputType.JoystickButton
    make = plugin_manager.PluginManager().create_instance
    profile = j.profile
    profile.modes.add_mode(COMBAT)
    uid = j.stick(STICK).device_guid.uuid

    def bind(device: Any, button: int, mode: str, action: Any) -> Any:  # noqa: ANN401
        item = profile.get_input_item(device, B, button, mode, True)
        item.add_item_binding().root_action.insert_action(action, "children")
        return item

    def to_vjoy(vjoy: int, button: int) -> Any:  # noqa: ANN401
        action = make("Map to vJoy", B)
        action.vjoy_device_id = vjoy
        action.vjoy_input_id = button
        action.vjoy_input_type = B
        return action

    # OSC "/fire" -> vJoy 2 Button 30.
    assert OscDeviceManagementModel().createConfiguredInput(
        {"address": "/fire", "mode": "button"}
    ), "the OSC input was not added"
    row = next(r for r in OscDevice().rows.rows() if r.label == "/fire")
    item = profile.get_input_item(
        OSC_DEVICE_UUID, row.input_type, row.input_id, "Default", True
    )
    item.osc_uid = row.uid
    item.add_item_binding().root_action.insert_action(to_vjoy(2, 30), "children")

    # Button 1 (Combat): a macro pressing vJoy 2 Button 30.
    macro_action = make("Macro", B)
    macro_action.actions = [macro.VJoyAction(2, B, 30, True)]
    bind(uid, 1, COMBAT, macro_action)

    # Button 2: a condition on vJoy 2 Button 30.
    cond_action = make("Condition", B)
    cond = ca.VJoyCondition()
    cond.start_on(2, B, 30)
    cond_action.conditions = [cond]
    cond_action.true_actions = [to_vjoy(1, 5)]
    bind(uid, 2, "Default", cond_action)

    # Button 3: Change Mode to Combat.
    change = make("Change Mode", B)
    change.change_type = ChangeType.Switch
    change.target_modes = [COMBAT]
    bind(uid, 3, "Default", change)

    # Button 4 (Combat): vJoy 2 Button 60, which vJoy 2 doesn't have.
    bind(uid, 4, COMBAT, to_vjoy(2, 60))

    signal.profileChanged.emit()
    j.settle()


def story(j: Journey) -> None:
    _profile(j)
    j.out["0:mode"] = str(j.backend.uiState.currentMode)
    for name, part in (
        ("1", _part_open),
        ("2", _part_output),
        ("3", _part_go),
        ("4", _part_next),
        ("5", _part_find_uses),
        ("6", _part_mode),
        ("7", _part_broken),
    ):
        with _Part(j, name):
            part(j)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module(1)
        j.vjoy_module(2)

    Journey(before, vjoy_ids=RIG["vjoy_ids"]).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("search_e2e"))


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


def _group(state: dict, title: str) -> list[dict]:
    return [r for r in state["rows"] if r["groupTitle"] == title]


def test_the_toolbar_search_button_opens_the_search_window(run: dict) -> None:
    assert _step(run, "1:title") == "Search"
    assert _step(run, "1:after-tester") is True
    assert _step(run, "1:glyph") == ""


def test_output_finds_the_osc_input_the_macro_and_the_condition(run: dict) -> None:
    state = _step(run, "2:state")
    assert state["count"] == 3, state
    assert state["groups"] == [
        {"title": "Sends to this output", "count": 2},
        {"title": "Checks this output", "count": 1},
    ], state
    sends = _group(state, "Sends to this output")
    assert sorted(r["deviceName"] for r in sends) == sorted(["OSC", STICK]), sends
    macro = [r for r in sends if r["deviceName"] == STICK]
    assert macro and macro[0]["mode"] == COMBAT, sends
    assert "macro" in macro[0]["text"].lower(), sends
    checks = _group(state, "Checks this output")
    assert [(r["deviceName"], r["inputLabel"]) for r in checks] == [
        (STICK, "Button 2")
    ], checks
    assert not any(r["notFound"] for r in state["rows"]), state
    texts = _step(run, "2:texts")
    assert "3 uses" in texts, texts
    assert "Sends to this output (2 uses)" in texts, texts
    assert "Checks this output (1 use)" in texts, texts


def test_a_result_opens_the_bindings_page_in_its_mode(run: dict) -> None:
    assert _step(run, "0:mode") == "Default"
    at = _step(run, "3:at")
    assert at["device"] == STICK, at
    assert at["mode"] == COMBAT, at
    assert at["pane"] == "parent:button:1", at
    assert at["shown"] == "parent:button:1", at
    assert _step(run, "3:window-open") is True


def test_next_moves_to_the_next_result(run: dict) -> None:
    before, after = _step(run, "4:before"), _step(run, "4:at")
    assert after != before, (before, after)
    first, second = _step(run, "4:index")
    assert first == _step(run, "3:index"), (first, second)
    assert second == first + 1, (first, second)
    row = _step(run, "4:row")
    if row["deviceName"] == STICK:
        assert after["pane"] == f"parent:button:{row['inputId']}", (row, after)
        assert after["shown"] == after["pane"], (row, after)
        assert after["mode"] == row["mode"], (row, after)


def test_find_uses_on_a_row_fills_the_search(run: dict) -> None:
    assert "Find uses…" in _step(run, "5:menu")
    query = _step(run, "5:query")
    assert query["kind"] == "input", query
    assert query["device"] == _step(run, "5:stick"), query
    assert int(query["inputType"]) == _step(run, "5:button"), query
    assert int(query["inputId"]) == 2, query
    state = _step(run, "5:state")
    assert state["count"] >= 1, state
    assert all(r["inputLabel"] == "Button 2" for r in state["rows"]), state


def test_mode_finds_the_change_mode(run: dict) -> None:
    state = _step(run, "6:state")
    switches = _group(state, "Switches to this mode")
    assert [(r["deviceName"], r["inputLabel"]) for r in switches] == [
        (STICK, "Button 3")
    ], state
    assert {"title": "Switches to this mode", "count": 1} in state["groups"]
    runs = _group(state, "Runs in this mode")
    broken = [r for r in runs if r["inputLabel"] == "Button 4"]
    assert broken and broken[0]["notFound"] is True, runs


def test_a_broken_binding_says_its_output_is_not_found(run: dict) -> None:
    state = _step(run, "7:state")
    assert state["count"] == 1, state
    row = state["rows"][0]
    assert row["notFound"] is True, row
    assert row["inputLabel"] == "Button 4" and row["mode"] == COMBAT, row
    texts = _step(run, "7:texts")
    assert any(NOT_FOUND in t for t in texts), texts


def test_no_program_errors(run: dict) -> None:
    assert run.get("_errors") == [], run.get("_errors")
    assert "error" not in run, run.get("traceback")


if __name__ == "__main__":
    main()
