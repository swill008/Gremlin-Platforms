# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Search (to-do 9, D-01-SEARCH): the toolbar button, Tools › Mapping ›
Search…, the one Search window and Main.goToBinding.

A journey (test/journeys/_harness.py): the real main window off-screen in
its own process (fake "pJoy Pro" with an input module claiming buttons 1-8,
a temp USERPROFILE, no update check).
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
)

# +-------------------------------------------------------------------------
# | Script side (the child process)


def _safe(j: Journey, code: str) -> Any:  # noqa: ANN401
    try:
        return j.ev(code)
    except RuntimeError as err:
        return "ERROR " + str(err)


def story(j: Journey) -> None:
    out = j.out
    j.settle()
    # The toolbar button (01 S58): after Input Tester, before Mapping Editor.
    out["button"] = _safe(
        j,
        "(function() { var b = _searchButton; return { "
        "caption: b.caption, glyph: b.text.charCodeAt(0), tooltip: b.tooltip, "
        "afterTester: b.x > _inputTesterButton.x, "
        "beforeEditor: b.x < _deviceMappingEditorButton.x, "
        'helpFinds: _helpToolbarButton("Search") === b } })()',
    )
    # Tools › Mapping › Search… (main_commands.js).
    out["command"] = _safe(
        j,
        "(function() { var l = MainCommands.commandList(); "
        'for (var i = 0; i < l.length; i++) if (l[i].id === "tools.search") '
        "return { text: l[i].text, group: l[i].group, "
        'shortcut: l[i].shortcut || "" }; return null })()',
    )
    # Main.openSearch: one window, raised and filled when asked again.
    out["open1"] = _safe(
        j,
        '(function() { var w = _root.openSearch({kind: "mode", mode: "Default"}); '
        "return w ? w.title : null })()",
    )
    j.settle()
    out["open2"] = _safe(
        j,
        '(function() { var a = Helpers.windowOf("DialogSearch.qml"); '
        'var b = _root.openSearch({kind: "action", actionTag: "remap"}); '
        "return { same: a !== null && a === b, kind: b ? b.usages.kind : '', "
        "tag: b ? b.usages.actionTag : '' } })()",
    )
    out["tabs"] = _safe(
        j,
        '(function() { var w = Helpers.windowOf("DialogSearch.qml"); '
        "return w ? w.kindLabels : null })()",
    )

    # Main.goToBinding: the mode, the device's page and the row.
    j.profile.modes.add_mode("Air")
    guid = _safe(
        j,
        "(function() { for (var i = 0; i < _cardGuids.count; i++) { "
        "var r = _cardGuids.objectAt(i); var c = _moduleModel.cardMap(r.slug); "
        'if (c && (c.tab || "physical") === "physical" '
        '&& (c.direction || "source") === "source") return String(r.guid) } '
        'return "" })()',
    )
    out["guid"] = guid
    if guid and not str(guid).startswith("ERROR"):
        out["go"] = _safe(
            j, "_root.goToBinding(" + json.dumps(guid) + ', "Air", 3, 5, 0)'
        )
        pane = (
            "(function() { var p = deviceBindingsPane(); "
            'return !!p && p.actionOpen && p.paneKey === "parent:button:5" })()'
        )
        j.await_value(lambda: _safe(j, pane), True, timeout=8.0)
        out["afterGo"] = _safe(
            j,
            "(function() { var p = deviceBindingsPane(); return { "
            "room: uiState.currentRoom, tab: uiState.currentTab, "
            "mode: uiState.currentMode, "
            "device: _plainGuid(uiState.currentDevice) === _plainGuid("
            + json.dumps(guid)
            + "), "
            'pageMode: p ? p.mode : "", paneKey: p ? p.paneKey : "", '
            'searchOpen: Helpers.windowOf("DialogSearch.qml") !== null } })()',
        )
    # The Logical Device's own page.
    out["goLogical"] = _safe(
        j, '_root.goToBinding(uiState.logicalDeviceGuid, "Default", 3, 1, 0)'
    )
    j.await_value(lambda: _safe(j, "uiState.currentTab"), "logical", timeout=8.0)
    out["logical"] = _safe(
        j, "({ tab: uiState.currentTab, mode: uiState.currentMode })"
    )


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2, 3, 4, 5, 6, 7, 8])

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("search_window"))


def test_the_toolbar_has_search_after_input_tester(result: dict) -> None:
    button = result["button"]
    assert isinstance(button, dict), button
    assert button["caption"] == "Search"
    assert button["glyph"] == 0xF52A  # Bootstrap Icons "search"
    assert button["tooltip"] == (
        "Search the profile: every use of an input, output, mode or action type"
    )
    assert button["afterTester"] and button["beforeEditor"]
    assert button["helpFinds"] is True


def test_tools_mapping_has_search(result: dict) -> None:
    assert result["command"] == {
        "text": "Search…",
        "group": "Tools › Mapping",
        "shortcut": "Ctrl+Shift+F",
    }


def test_open_search_opens_one_window_and_fills_it(result: dict) -> None:
    assert result["open1"] == "Search"
    assert result["open2"] == {"same": True, "kind": "action", "tag": "remap"}
    assert result["tabs"] == ["Input", "Output", "Mode", "Action type"]


def test_go_to_binding_opens_the_device_page_in_its_mode_on_the_row(
    result: dict,
) -> None:
    assert result["guid"], result
    go = result.get("go")
    assert go is None or not str(go).startswith("ERROR"), result
    assert result["afterGo"] == {
        "room": "configuration",
        "tab": "physical",
        "mode": "Air",
        "device": True,
        "pageMode": "Air",
        "paneKey": "parent:button:5",
        "searchOpen": True,
    }


def test_go_to_binding_on_the_logical_device_opens_its_page(result: dict) -> None:
    assert result["logical"] == {"tab": "logical", "mode": "Default"}


if __name__ == "__main__":
    main()
