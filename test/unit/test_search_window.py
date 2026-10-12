# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Search (D-01-SEARCH, D-01-SEARCH-INDEX): the toolbar button, Tools ›
Mapping › Search…, the one Search window (qml/DialogSearch.qml: the box,
first open, results, Esc, nothing found) and Main.goToBinding.

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
    # Main.openSearch: one window, raised and its box filled when asked again.
    out["open1"] = _safe(
        j,
        "(function() { var w = _root.openSearch(); "
        "return w ? { title: w.title, typed: w.typed, "
        "box: w.search.text } : null })()",
    )
    j.settle()
    out["open2"] = _safe(
        j,
        '(function() { var a = Helpers.windowOf("DialogSearch.qml"); '
        'var b = _root.openSearch("mode:Default"); '
        "return { same: a !== null && a === b, text: b ? b.search.text : '' } })()",
    )
    # A binding in the open profile is found as you type, grouped profile ›
    # device, and a result's row carries the SearchRow field names.
    from gremlin import search_index

    uid = j.stick().device_guid.uuid
    j.map_button(uid, 6, j.profile.modes.first_mode, 4)
    search_index.default_index().rebuild_open(j.profile)
    win = 'Helpers.windowOf("DialogSearch.qml")'
    _safe(j, win + '.searchFor("Button 6")')
    j.await_value(
        lambda: (_safe(j, win + ".search.resultCount") or 0) > 0, True, timeout=8.0
    )
    out["found"] = _safe(
        j,
        "(function() { var w = " + win + "; w.move(1); var r = w.rowOf(w.current); "
        "return { count: w.search.resultCount > 0, picked: w.current >= 0, "
        "fields: r ? ['source', 'device_guid', 'input_label', 'binding_index']"
        ".every(function(k) { return k in r }) : false, "
        "label: r ? r.input_label : '' } })()",
    )
    # Nothing found, then Esc clears the box and Esc again closes the window.
    _safe(j, win + '.searchFor("zzqqxxw")')
    j.await_value(lambda: _safe(j, win + ".nothingFound"), True, timeout=8.0)
    out["nothing"] = _safe(j, win + ".search.nothingFoundText")
    out["esc"] = _safe(
        j,
        "(function() { var w = " + win + "; w.escapePressed(); "
        "var cleared = w.search.text === ''; w.escapePressed(); "
        "return { cleared: cleared } })()",
    )
    j.settle()
    out["closed"] = _safe(j, win + " === null")
    _safe(j, "_root.openSearch()")
    j.settle()

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
        "Search every profile: keys, actions, names and outputs"
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
    assert result["open1"] == {"title": "Search", "typed": False, "box": ""}
    assert result["open2"] == {"same": True, "text": "mode:Default"}


def test_typing_finds_the_open_profile_binding(result: dict) -> None:
    found = result["found"]
    assert isinstance(found, dict), found
    assert found["count"] and found["picked"] and found["fields"], found
    assert found["label"] == "Button 6"


def test_nothing_found_then_esc_clears_and_esc_again_closes(result: dict) -> None:
    assert str(result["nothing"]).startswith("Nothing found for 'zzqqxxw' in ")
    assert result["esc"] == {"cleared": True}
    assert result["closed"] is True


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
