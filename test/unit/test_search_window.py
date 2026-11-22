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


_SHOWN_ROW = (
    "{ rowKind: 'result', inputLabel: 'Button 6', mode: 'Air', "
    "notes: ['Lower the landing gear', 'unused'], inheritedFrom: 'Default', "
    "highlights: { 'notes:0': [[10, 17]] }, tags: ['inherited'] }"
)


def _shown(j: Journey, win: str) -> Any:  # noqa: ANN401
    """The notes and inherited texts the result row and detail pane show."""
    from PySide6 import QtCore

    window = j.ev(win)
    if window is None or isinstance(window, str):
        return "no window"
    detail = window.findChild(QtCore.QObject, "searchDetail")
    try:
        row = j.ev(
            "(function() { var it = _list.itemAtIndex(_root.current); "
            "if (!it) return null; it.model = " + _SHOWN_ROW + "; "
            "function named(item, name) { if (item.objectName === name) "
            "return item; for (var i = 0; i < item.children.length; i++) { "
            "var f = named(item.children[i], name); if (f) return f } "
            "return null } "
            "function text(name) { var f = named(it, name + _root.current); "
            "return f ? String(f.text) : '' } "
            "return { notes: text('searchRowNotes:'), "
            "inherited: text('searchRowInherited:') } })()",
            window,
        )
        j.ev(
            "row = " + _SHOWN_ROW + "; info = { notes: row.notes, "
            "inheritedFrom: 'Default' }",
            detail,
        )
    except RuntimeError as err:
        return "ERROR " + str(err)

    def text(name: str) -> str:
        found = window.findChild(QtCore.QObject, name)
        return str(found.property("text")) if found is not None else ""

    row = row or {}
    return {
        "rowNotes": row.get("notes", ""),
        "rowInherited": row.get("inherited", ""),
        "detailNotes": text("searchDetailNotes"),
        "detailNotesHeading": text("searchDetailNotesHeading"),
        "detailInherited": text("searchDetailInherited"),
    }


def _fix(j: Journey, win: str) -> Any:  # noqa: ANN401
    """01 S195 on the picked Map to vJoy row of the open profile: the menu
    shows Remove binding… and Change target…, Remove asks first (Cancel
    keeps it), Change target… opens the vJoy pickers."""
    from PySide6 import QtCore

    window = j.ev(win)
    if window is None or isinstance(window, str):
        return "no window"
    menu = window.findChild(QtCore.QObject, "searchRowMenu")
    try:
        j.ev("fixes = _root.fixesOf(_root.current)", menu)
    except RuntimeError as err:
        return "ERROR " + str(err)

    # What the items' visible bindings read (a closed menu shows none).
    try:
        found = j.ev(
            "({ remove: !!fixes.remove, change: !!fixes.changeTarget, "
            "undo: !!_model.canUndo })",
            menu,
        )
    except RuntimeError as err:
        return "ERROR " + str(err)
    found["question"] = _safe(
        j,
        "(function() { var w = " + win + "; var d = w.askRemove(w.current); "
        "if (!d) return null; var r = { title: d.titleText, action: d.actionText }; "
        "d.cancel(); return r })()",
    )
    j.settle()
    found["afterCancel"] = _safe(j, win + ".search.resultCount > 0")
    found["box"] = _safe(
        j,
        "(function() { var w = " + win + "; if (w.current < 0) w.move(1); "
        "w.askChangeTarget(w.current); "
        "return { current: w.current, start: w.search.changeTargetOf(w.current) } })()",
    )
    j.settle()
    box = window.findChild(QtCore.QObject, "searchTargetBox")
    found["boxOpen"] = None if box is None else bool(box.property("visible"))
    if box is not None:
        j.ev("close()", box)
    # A refused edit: the window's box says why.
    try:
        j.ev(
            '_model.editRefused("Can\'t change the binding", '
            '"The profile is running: stop it to change its bindings.")',
            window,
        )
    except RuntimeError as err:
        found["refused"] = "ERROR " + str(err)
        return found
    j.settle()

    def prop(name: str, key: str) -> object:
        item = window.findChild(QtCore.QObject, name)
        return None if item is None else item.property(key)

    found["refused"] = {
        "open": prop("searchOpenMessage", "visible"),
        "title": prop("searchOpenMessageTitle", "text"),
        "text": prop("searchOpenMessageText", "text"),
    }
    message = window.findChild(QtCore.QObject, "searchOpenMessage")
    if message is not None:
        j.ev("close()", message)
    return found


def _layout(j: Journey, win: str) -> Any:  # noqa: ANN401
    """01 S196: Listen left of the box, the Suggestion list tick under the
    bar (not in the sidebar), recent searches in the drop-down under the
    empty focused box with Clear at its end, the welcome panel only with
    nothing typed and no results, no health filters."""
    from PySide6 import QtCore

    window = j.ev(win)
    if window is None or isinstance(window, str):
        return "no window"

    def item(name: str) -> Any:  # noqa: ANN401
        return window.findChild(QtCore.QObject, name)

    listen, box, tick = (
        item("searchListenButton"),
        item("searchBox"),
        item("searchSuggestionsOn"),
    )
    side = item("searchSidebar")
    found: dict[str, Any] = {
        "listenFirst": listen is not None
        and box is not None
        and listen.mapToScene(QtCore.QPointF(0, 0)).x()
        < box.mapToScene(QtCore.QPointF(0, 0)).x(),
        "tickUnderBar": tick is not None
        and box is not None
        and tick.mapToScene(QtCore.QPointF(0, 0)).y()
        > box.mapToScene(QtCore.QPointF(0, 0)).y(),
        "tickInSidebar": side is not None
        and side.findChild(QtCore.QObject, "searchSuggestionsOn") is not None,
        "healthFilters": _safe(
            j,
            "(" + win + ".search.filters || []).filter(function(f) "
            "{ return f.group !== 'show' }).length",
        ),
    }
    # Results with nothing typed (a Show filter): no welcome panel.
    _safe(j, win + '.search.text = ""')
    _safe(j, win + '.search.setFilter("action", true)')
    j.settle()
    found["results"] = _safe(j, win + "._list.count")
    welcome = item("searchFirstOpen")
    found["welcomeShown"] = (
        None if welcome is None else bool(welcome.property("visible"))
    )
    _safe(j, win + '.search.setFilter("action", false)')
    # The recent drop-down under the empty, focused box.
    found["drop"] = _safe(
        j,
        "(function() { var w = " + win + "; w._suggestDismissed = false; "
        "w.focusBox(); return { recent: w.showingRecent, lines: w.dropList.length, "
        "count: w.dropCount } })()",
    )
    j.settle()
    popup = item("searchSuggestions")
    clear = item("searchClearRecent")
    found["dropOpen"] = None if popup is None else bool(popup.property("visible"))
    found["clearShown"] = None if clear is None else bool(clear.property("visible"))
    _safe(j, win + "._suggestDismissed = true")
    return found


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
    # A row's typed notes (lit where they matched) and "Inherited from
    # <mode>" on the row and in the detail pane (stand-in row values).
    out["shown"] = _shown(j, win)
    out["fix"] = _fix(j, win)
    out["layout"] = _layout(j, win)
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


def test_notes_and_inherited_are_shown(result: dict) -> None:
    """D-01-SEARCH-INDEX (SEARCH-NOTES-DETAIL, SEARCH-INHERIT): the row shows
    the note that matched, lit, and "Inherited from <mode>"; the detail pane
    lists every note under Notes and says where the binding comes from."""
    shown = result["shown"]
    assert isinstance(shown, dict), shown
    assert "landing" in shown["rowNotes"] and "<span" in shown["rowNotes"]
    assert "unused" not in shown["rowNotes"]  # only the notes that matched
    assert shown["rowInherited"] == "Inherited from Default"
    assert shown["detailNotesHeading"] == "Notes"
    assert shown["detailNotes"] == "Lower the landing gear\nunused"
    assert shown["detailInherited"] == "Inherited from Default"


def test_a_map_to_vjoy_row_offers_remove_and_change_target(result: dict) -> None:
    """01 S195: the real window's menu, Remove's question (Cancel keeps the
    binding) and Change target…'s box."""
    fix = result["fix"]
    assert isinstance(fix, dict), fix
    assert fix["remove"] is True and fix["change"] is True
    assert fix["undo"] is False
    question = fix["question"]
    assert isinstance(question, dict), question
    assert question["action"] == "Remove"
    assert question["title"].startswith("Remove the Map to vJoy binding from ")
    assert question["title"].endswith(" mode)?")
    assert fix["afterCancel"] is True
    assert fix["boxOpen"] is True, fix["box"]


def test_a_refused_edit_shows_why_in_a_box(result: dict) -> None:
    """01 S195: an edit that can't be made says why in the window's box."""
    fix = result["fix"]
    assert isinstance(fix, dict), fix
    assert fix["refused"] == {
        "open": True,
        "title": "Can't change the binding",
        "text": "The profile is running: stop it to change its bindings.",
    }


def test_search_layout_follows_s196(result: dict) -> None:
    layout = result["layout"]
    assert layout["listenFirst"] is True
    assert layout["tickUnderBar"] is True
    assert layout["tickInSidebar"] is False
    assert layout["healthFilters"] == 0
    assert layout["welcomeShown"] is False
    assert layout["drop"]["recent"] is True
    assert layout["drop"]["lines"] >= 1
    assert layout["drop"]["count"] == layout["drop"]["lines"] + 1
    assert layout["dropOpen"] is True
    assert layout["clearShown"] is True
