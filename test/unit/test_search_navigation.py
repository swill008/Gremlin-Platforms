# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Search's ways in and out of the main window (D-01-SEARCH-INDEX, layer 5).

1. Main.openSearch(textOrQuery): text goes into the Search box as it is; an
   old-style query dict becomes prefix text (mode:"…", vjoy:"2 button 30",
   device:"<name>" button 5, key:"F5"); nothing leaves the box alone.
2. Home's card menu has Search this device: device:"<name>".
3. Main.goToSearchRow(row) for a SearchRow's fields: "open" goes to the row
   in the open profile; "profile" (another file) asks about unsaved changes
   first (Cancel: nothing opens; Discard: that file opens, then the row);
   "library" opens the Device Library on that device.
4. The go-to handlers (keyed by device kind) cover every card's kind.

A journey (test/journeys/_harness.py): the real main window off-screen in
its own process (fake "pJoy Pro", temp USERPROFILE). The Search window is a
stand-in registered as the open DialogSearch.qml that records its text; the
save question's buttons are its signals; the profile load is the real one.
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

STICK = "pJoy Pro"

# +-------------------------------------------------------------------------
# | Script side (the child process)


def _safe(j: Journey, code: str) -> Any:  # noqa: ANN401
    try:
        return j.ev(code)
    except RuntimeError as err:
        return "ERROR " + str(err)


_STUB = (
    "(function() {"
    " var w = Qt.createQmlObject('import QtQuick; QtObject {"
    " property var texts: [];"
    " function searchFor(t) { texts = texts.concat([t]) }"
    " function show() {} function raise() {} function requestActivate() {} }',"
    " _root, 'fakeSearch');"
    ' Helpers._openWindows["DialogSearch.qml"] = w; return w })()'
)


def _texts(j: Journey, stub: Any) -> list[str]:  # noqa: ANN401
    out = json.loads(str(j.ev("JSON.stringify(texts)", stub)))
    j.ev("texts = []; true", stub)
    return out


def _part_open(j: Journey, stub: Any, guid: str) -> None:  # noqa: ANN401
    calls = [
        '"F5 gr tog"',
        "null",
        '{kind: "mode", mode: "Air"}',
        '{kind: "action", actionTag: "remap"}',
        '{kind: "output", output: "vjoy", outputId: 2, inputType: 3, inputId: 30}',
        '{kind: "output", output: "xbox", outputId: 1, inputType: 3, inputId: "a"}',
        '{kind: "output", output: "mouse", inputId: "Left"}',
        '{kind: "input", deviceGuid: '
        + json.dumps(guid)
        + ", inputType: 3, inputId: 5}",
        '{kind: "input", deviceGuid: '
        + json.dumps(guid)
        + ', inputType: 3, inputId: 5, title: "Button 5"}',
        '{kind: "input", deviceGuid: "x", inputType: 1, inputId: [63, false],'
        ' title: "F5"}',
    ]
    for call in calls:
        j.ev(f"_root.openSearch({call}); true")
    j.out["open"] = _texts(j, stub)


def _part_card(j: Journey, stub: Any) -> None:  # noqa: ANN401
    j.ev("uiState.setCurrentRoom('home'); true")
    j.settle()

    def card() -> Any:  # noqa: ANN401
        for item in Journey.walk(j.win.contentItem()):
            name = item.metaObject().className()
            if name.startswith("StatusCard") and item.property("rawName") == STICK:
                return item
        return None

    c = j.wait_until(card, "the stick's Home card")
    j.out["card:rows"] = json.loads(
        str(
            j.ev(
                "JSON.stringify((function(m) { var rows = []; var it = null;"
                " m.sections.forEach(function(s) {"
                " (s.items || []).forEach(function(r) {"
                " rows.push(r.text); if (r.text === 'Search this device') it = r }) });"
                " if (it) it.run(); return rows })(menuModel()))",
                c,
            )
        )
    )
    j.out["card:texts"] = _texts(j, stub)


def _page_on(j: Journey, key: str) -> Any:  # noqa: ANN401
    code = (
        "(function() { var p = deviceBindingsPane(); "
        "return !!p && p.actionOpen && p.paneKey === " + json.dumps(key) + " })()"
    )
    return j.await_value(lambda: _safe(j, code), True, timeout=8.0)


def _part_go(j: Journey, guid: str) -> None:
    from PySide6 import QtCore

    from gremlin import util

    uid = j.stick(STICK).device_guid.uuid
    j.out["kinds"] = _safe(
        j,
        "(function() { var out = { stick: deviceKindOf(" + json.dumps(guid) + "), "
        "logical: deviceKindOf(uiState.logicalDeviceGuid), missing: [] }; "
        "for (var i = 0; i < _cardGuids.count; i++) { "
        "var c = _moduleModel.cardMap(_cardGuids.objectAt(i).slug); "
        'var k = c ? String(c.tab || "physical") : ""; '
        "if (k && typeof goToHandlers[k] !== 'function') out.missing.push(k) } "
        "return out })()",
    )

    # "open": the row in the open profile.
    j.map_button(uid, 5, j.profile.modes.first_mode, 5)
    j.settle()
    row = {
        "source": "open",
        "device_guid": guid,
        "mode": "Default",
        "input_type": 3,
        "input_id": 5,
        "binding_index": 0,
        "input_label": "Button 5",
        "custom_name": "",
    }
    j.out["go:open"] = _safe(j, f"_root.goToSearchRow({json.dumps(row)})")
    j.out["go:openShown"] = _page_on(j, "parent:button:5")

    # "profile": another file. Saved as other.xml with button 3 bound, then
    # a new profile with an unsaved edit is open.
    j.map_button(uid, 3, j.profile.modes.first_mode, 3)
    other = util.profiles_dir() / "other.xml"
    assert j.backend.saveProfile(QtCore.QUrl.fromLocalFile(str(other)).toString())
    j.ev("uiState.setCurrentRoom('home'); true")
    j.backend.newProfile()
    j.map_button(uid, 7, j.profile.modes.first_mode, 7)
    j.settle()
    j.out["dirty"] = bool(j.backend.property("profileContainsUnsavedChanges"))
    prow = dict(
        row,
        source="profile",
        source_path=str(other),
        input_id=3,
        input_label="Button 3",
    )
    asked = (
        "(function() { var d = _saveBeforeContinueDialog; "
        "return d.visible && d.pendingAction !== null })()"
    )
    # Cancel: the question goes, nothing opens.
    _safe(j, f"_root.goToSearchRow({json.dumps(prow)})")
    j.out["go:asked1"] = j.await_value(lambda: _safe(j, asked), True, timeout=8.0)
    # As its Cancel button: closing it is Cancel.
    j.ev("_saveBeforeContinueDialog.close(); true")
    j.settle()
    j.out["go:afterCancel"] = str(j.backend.profilePath())
    # Discard: other.xml opens and its row is shown.
    _safe(j, f"_root.goToSearchRow({json.dumps(prow)})")
    j.out["go:asked2"] = j.await_value(lambda: _safe(j, asked), True, timeout=8.0)
    # As its Discard button does (DismissibleDialog).
    j.ev(
        "(function(d) { d._choice = 'discard'; d.close(); d.discarded();"
        " d.discardChosen();"
        " return true })(_saveBeforeContinueDialog)"
    )
    j.settle()
    j.out["go:afterDiscard"] = str(j.backend.profilePath())
    j.out["go:other"] = str(other)
    j.out["go:otherShown"] = _page_on(j, "parent:button:3")

    # The same file again, now open: straight there, no question.
    j.out["go:same"] = _safe(
        j, f"_root.goToSearchRow({json.dumps(dict(prow, input_id=5))})"
    )
    j.out["go:sameShown"] = _page_on(j, "parent:button:5")

    # "library": the Device Library on the device.
    lrow = dict(row, source="library", device_name=STICK)
    j.out["go:library"] = _safe(j, f"_root.goToSearchRow({json.dumps(lrow)})")
    j.settle()
    j.out["go:libraryOpen"] = _safe(
        j, 'Helpers.windowOf("WindowDeviceLibrary.qml") !== null'
    )


def story(j: Journey) -> None:
    j.settle()
    stub = j.ev(_STUB)
    assert stub is not None, "no stand-in Search window"
    guid = str(
        _safe(
            j,
            "(function() { for (var i = 0; i < _cardGuids.count; i++) { "
            "var r = _cardGuids.objectAt(i); var c = _moduleModel.cardMap(r.slug); "
            "if (c && c.rawName === " + json.dumps(STICK) + ") return String(r.guid) } "
            'return "" })()',
        )
    )
    j.out["guid"] = guid
    for name, part in (
        ("open", lambda: _part_open(j, stub, guid)),
        ("card", lambda: _part_card(j, stub)),
        ("go", lambda: _part_go(j, guid)),
    ):
        try:
            part()
        except Exception as err:  # noqa: BLE001
            j.out[f"{name}:error"] = f"{type(err).__name__}: {err}"


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(STICK, buttons=[1, 2, 3, 4, 5, 6, 7, 8])
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("search_navigation"))


def _no_error(result: dict, part: str) -> None:
    assert f"{part}:error" not in result, result.get(f"{part}:error")


def test_open_search_puts_text_or_a_query_as_prefix_text_in_the_box(
    result: dict,
) -> None:
    _no_error(result, "open")
    assert result["guid"], result
    assert result["open"] == [
        "F5 gr tog",
        'mode:"Air"',
        'action:"remap"',
        'vjoy:"2 button 30"',
        'xbox:"1 button a"',
        'mouse:"Left"',
        f'device:"{STICK}" button 5',
        f'device:"{STICK}" Button 5',
        'key:"F5"',
    ]


def test_the_home_card_searches_its_device(result: dict) -> None:
    _no_error(result, "card")
    assert "Search this device" in result["card:rows"], result["card:rows"]
    assert result["card:texts"] == [f'device:"{STICK}"']


def test_every_card_kind_has_a_go_to_handler(result: dict) -> None:
    _no_error(result, "go")
    assert result["kinds"] == {"stick": "physical", "logical": "logical", "missing": []}


def test_a_result_in_the_open_profile_goes_to_its_row(result: dict) -> None:
    _no_error(result, "go")
    assert result["go:open"] is True
    assert result["go:openShown"] is True


def test_a_result_in_another_profile_asks_to_save_then_opens_it_on_the_row(
    result: dict,
) -> None:
    _no_error(result, "go")
    assert result["dirty"] is True
    assert result["go:asked1"] is True
    assert result["go:afterCancel"] == ""  # Cancel: the new profile stays
    assert result["go:asked2"] is True
    assert pathlib.Path(result["go:afterDiscard"]) == pathlib.Path(result["go:other"])
    assert result["go:otherShown"] is True
    assert result["go:same"] is True and result["go:sameShown"] is True


def test_a_device_library_result_opens_the_device_library(result: dict) -> None:
    _no_error(result, "go")
    assert result["go:library"] is True
    assert result["go:libraryOpen"] is True


if __name__ == "__main__":
    main()
