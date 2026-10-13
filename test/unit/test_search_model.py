# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Search window's model (D-01-SEARCH-INDEX, layer 3): typing searches
the index after a short wait, toggles and Look in, quick and Health filters
with counts, grouping profile → device with folds and sort, the detail
pane, Listen (stick, key, OSC; OSC off said so), the nothing-found hints,
Recent and the remembered state. A stand-in index gives the rows; matching
is the real gremlin.search_query."""

from __future__ import annotations

import types
import uuid
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtGui, QtTest

from gremlin import shared_state
from gremlin.search_index import SearchRow
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import search_model
from gremlin.ui.search_model import SearchModel

# The program's clipboard helper, before the autouse stub replaces it.
_REAL_SET_CLIPBOARD = search_model._set_clipboard

_STICK = str(uuid.UUID("{61111111-2222-3333-4444-555555555555}"))
_KEYS = str(uuid.UUID("{6F1D2B61-D5A0-11CF-BFC7-444553540000}"))


def _row(**fields: object) -> SearchRow:
    base: dict = {
        "source": "profile",
        "source_name": "DCS",
        "source_path": "C:/p/DCS.xml",
        "device_guid": _STICK,
        "device_name": "T.16000M",
        "plugged": True,
        "mode": "Default",
        "input_type": int(InputType.JoystickButton.value),
        "input_id": 3,
        "input_label": "Button 3",
        "custom_name": "",
        "action_tag": "map-to-vjoy",
        "action_name": "Map to vJoy",
        "text": "vJoy 1 Button 3",
        "targets": ("vJoy 1 Button 3",),
        "target_keys": (("vjoy", 1, 2, 3),),
        "role": "reads-input",
        "not_found": False,
        "why": "",
        "used_twice": False,
        "binding_index": 0,
        "path": (),
        "kinds": frozenset({"action", "vjoy"}),
    }
    base.update(fields)
    return SearchRow(**base)


ROWS = [
    _row(),
    _row(
        input_id=4,
        input_label="Button 4",
        custom_name="Gear Toggle",
        kinds=frozenset({"action", "vjoy", "name"}),
        used_twice=True,
        target_keys=(("vjoy", 1, 2, 9),),
    ),
    _row(
        input_id=5,
        input_label="Button 5",
        used_twice=True,
        target_keys=(("vjoy", 1, 2, 9),),
        plugged=False,
    ),
    _row(
        source="open",
        source_name="Elite",
        source_path="C:/p/Elite.xml",
        device_guid=_KEYS,
        device_name="Keyboard",
        input_type=int(InputType.Keyboard.value),
        input_id=(63, False),
        input_label="F5",
        action_tag="",
        action_name="",
        text="",
        targets=(),
        target_keys=(),
        kinds=frozenset({"key"}),
    ),
    _row(
        source="library",
        source_name="Warthog setup",
        source_path="pack.zip",
        plugged=None,
        input_label="Button 7",
        input_id=7,
        not_found=True,
        why="vJoy 3 is not set up",
    ),
]


class _Index:
    """Stand-in SearchIndex: rows, status and the calls made to it."""

    def __init__(self, rows: list[SearchRow]) -> None:
        self._rows = tuple(rows)
        self.on_change = None
        self.builds = 0
        self.rebuilt: list[object] = []
        self.state = {"state": "ready", "done": 3, "total": 3, "unreadable": []}

    def set_on_change(self, callback: object) -> None:
        self.on_change = callback

    def build(self) -> None:
        self.builds += 1

    def rebuild_open(self, profile: object) -> None:
        self.rebuilt.append(profile)

    def rows(self) -> tuple[SearchRow, ...]:
        return self._rows

    def status(self) -> dict:
        return dict(self.state)


@pytest.fixture(autouse=True)
def copied(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Copy as text never reaches the real clipboard (the user's; setText
    crashed a full run, 2026-10-12, as conftest's _no_real_clipboard says)."""
    got: list[str] = []
    monkeypatch.setattr(search_model, "_set_clipboard", got.append)
    return got


@pytest.fixture
def saved(monkeypatch: pytest.MonkeyPatch) -> dict:
    store: dict = {}
    monkeypatch.setattr(search_model, "_settings_load", lambda: dict(store))
    monkeypatch.setattr(search_model, "_settings_save", store.update)
    return store


@pytest.fixture
def index() -> _Index:
    return _Index(ROWS)


@pytest.fixture
def model(qapp: object, saved: dict, index: _Index) -> Iterator[SearchModel]:
    made = SearchModel(index=index)
    yield made
    made.close()
    made.deleteLater()


def _rows(model: SearchModel) -> list[dict]:
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    return [
        {name: model.data(model.index(r, 0), role) for role, name in names.items()}
        for r in range(model.rowCount())
    ]


def _results(model: SearchModel) -> list[dict]:
    return [r for r in _rows(model) if r["rowKind"] == "result"]


def test_roles_hold_the_contract_names(model: SearchModel) -> None:
    names = {bytes(v).decode() for v in model.roleNames().values()}
    for name in (
        "rowKind", "title", "count", "folded", "sourceName", "deviceName",
        "mode", "inputLabel", "customName", "actionName", "text", "targets",
        "notFound", "usedTwice", "bindingIndex", "path", "highlights", "tags",
        "notPlugged",
    ):  # fmt: skip
        assert name in names


def test_follows_the_index(model: SearchModel, index: _Index) -> None:
    assert index.on_change is not None
    model.close()
    assert index.on_change is None


def test_typing_waits_then_searches_every_source(model: SearchModel) -> None:
    model.text = "button"
    assert model.resultCount == 0  # not yet: the wait
    QtTest.QTest.qWait(search_model.DEBOUNCE_MS + 80)
    assert model.resultCount == 4
    assert model.profileCount == 2
    assert model.statusText == "4 uses in 2 profiles"
    kinds = [r["rowKind"] for r in _rows(model)]
    assert kinds[0] == "profile" and kinds[1] == "device"
    first = _results(model)[0]
    assert first["highlights"]  # matched letters to show


def test_open_profile_first_then_profiles_then_library(model: SearchModel) -> None:
    model.searchFor("t")
    titles = [r["title"] for r in _rows(model) if r["rowKind"] == "profile"]
    assert titles[0] == "Elite (open)"
    assert titles[-1] == "Warthog setup"


def test_look_in_this_profile_and_library(model: SearchModel, saved: dict) -> None:
    model.searchFor("f5")
    assert model.resultCount == 1
    model.lookIn = "library"
    assert model.resultCount == 0
    assert saved["lookIn"] == "library"
    assert {"text": "Search all profiles", "action": "lookIn:all"} in (
        model.nothingFoundHints
    )
    model.applyHint("lookIn:all")
    assert model.lookIn == "all" and model.resultCount == 1


def test_filters_have_counts_and_narrow(model: SearchModel) -> None:
    model.searchFor("button")
    counts = {f["name"]: f["count"] for f in model.filters}
    assert counts["usedTwice"] == 2
    assert counts["notFound"] == 1
    assert counts["notPlugged"] == 1  # the library row doesn't count
    model.setFilter("usedTwice", True)
    assert model.resultCount == 2
    assert all("usedTwice" in r["tags"] for r in _results(model))
    model.setFilter("name", True)
    assert [r["customName"] for r in _results(model)] == ["Gear Toggle"]
    model.clearFilters()
    assert model.resultCount == 4


def test_a_health_filter_alone_lists_without_text(model: SearchModel) -> None:
    model.searchFor("")
    assert model.resultCount == 0
    model.setFilter("notFound", True)
    assert [r["why"] for r in _results(model)] == ["vJoy 3 is not set up"]


def test_prefix_and_regex(model: SearchModel) -> None:
    model.searchFor("key:F5")
    assert [r["inputLabel"] for r in _results(model)] == ["F5"]
    model.regex = True
    model.searchFor("Button [45]")
    assert model.resultCount == 2
    model.searchFor("Button [")
    assert model.resultCount == 0
    assert model.queryError == "" or "pattern" in model.queryError


def test_sort_and_folds(model: SearchModel) -> None:
    model.lookIn = "all"
    model.searchFor("button")
    model.setSort("input", 1)
    dcs = [r["inputLabel"] for r in _results(model) if r["sourceName"] == "DCS"]
    assert dcs == ["Button 5", "Button 4", "Button 3"]
    header = next(i for i, r in enumerate(_rows(model)) if r["title"] == "DCS")
    model.toggleFold(header)
    assert all(r["sourceName"] != "DCS" for r in _results(model))
    assert _rows(model)[header]["folded"] is True
    model.foldAll(False)
    model.foldAll(True)
    assert _results(model) == []
    model.foldAll(False)
    assert len(_results(model)) == 4


def test_detail_has_clash_partners_and_copy_text(
    model: SearchModel, copied: list[str]
) -> None:
    model.searchFor("gear")
    row = next(i for i, r in enumerate(_rows(model)) if r["rowKind"] == "result")
    info = model.detail(row)
    assert info["clashPartners"] == ["T.16000M · Button 5"]
    assert info["modeChain"] == ["Default"]
    assert "vJoy 1 Button 3" in info["bindingText"]
    line = model.copyText(row)
    assert line.startswith("DCS › T.16000M › Default › Gear Toggle (Button 4)")
    assert copied == [line]
    assert model.get(row)["customName"] == "Gear Toggle"
    assert model.detail(0) == {}  # a header row


def test_nothing_found_says_what_where_and_did_you_mean(model: SearchModel) -> None:
    model.matchCase = True
    model.searchFor("Gaer Toggle")
    assert model.resultCount == 0
    assert model.nothingFoundText == "Nothing found for 'Gaer Toggle' in All profiles."
    assert model.didYouMean
    hint = model.nothingFoundHints[0]["text"]
    assert hint == f"Did you mean {model.didYouMean}?"
    actions = [h["action"] for h in model.nothingFoundHints]
    assert "off:_case" in actions
    model.applyHint("off:_case")
    assert model.matchCase is False


def test_recent_keeps_ten_and_typing_on_replaces(model: SearchModel) -> None:
    model.searchFor("gear")
    model.searchFor("gear tog")
    assert model.recent == ["gear tog"]
    for n in range(12):
        model.searchFor(f"x{n}")
    assert len(model.recent) == search_model.RECENT_MAX
    assert model.recent[0] == "x11"


def test_remembered_state_comes_back(qapp: object, saved: dict, index: _Index) -> None:
    first = SearchModel(index=index)
    first.searchFor("gear")
    first.wholeWord = True
    first.setFilter("vjoy", True)
    first.detailOpen = False
    first.suggestionsOn = True
    first.close()
    again = SearchModel(index=index)
    try:
        assert again.text == "gear"
        assert again.wholeWord is True
        assert {f["name"] for f in again.filters if f["on"]} == {"vjoy"}
        assert again.detailOpen is False
        assert again.suggestionsOn is True
    finally:
        again.close()


def test_suggestions_off_by_default(model: SearchModel) -> None:
    assert model.suggestionsOn is False
    model.text = "gea"
    assert model.suggestions == []
    model.suggestionsOn = True
    model.text = "gear"
    assert isinstance(model.suggestions, list)


def test_status_line_while_building_and_unreadable(
    model: SearchModel, index: _Index
) -> None:
    index.state = {
        "state": "building",
        "done": 1,
        "total": 4,
        "unreadable": [("C:/p/bad.xml", "not a profile")],
    }
    index.on_change()  # pyright: ignore[reportOptionalCall]
    QtTest.QTest.qWait(20)
    assert model.statusText.startswith("Indexing 1 of 4 profiles…")
    assert model.unreadable == [{"path": "C:/p/bad.xml", "reason": "not a profile"}]


def test_profile_notices_rebuild_the_open_profile_once(
    model: SearchModel, index: _Index, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.profile import Profile

    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    signal.bindingsChanged.emit()
    signal.actionsChanged.emit()
    signal.modesChanged.emit()
    QtTest.QTest.qWait(search_model.REBUILD_MS + 100)
    assert index.rebuilt == [profile]


class _Listener(QtCore.QObject):
    listeningTerminated = QtCore.Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.enabled = False


class _Osc(QtCore.QObject):
    incoming = QtCore.Signal(str, object, object)

    def __init__(self, state: str) -> None:
        super().__init__()
        self.state = state

    def listenInfo(self) -> dict:  # noqa: N802
        return {"state": self.state}


@pytest.fixture
def listen_parts(
    model: SearchModel, monkeypatch: pytest.MonkeyPatch
) -> tuple[_Listener, _Osc]:
    listener, osc = _Listener(), _Osc("listening")
    monkeypatch.setattr(model, "_make_listener", lambda: listener)
    monkeypatch.setattr(SearchModel, "_osc_runtime", staticmethod(lambda: osc))
    return listener, osc


def test_listen_a_key_fills_the_box(
    model: SearchModel, listen_parts: tuple[_Listener, _Osc]
) -> None:
    listener, _ = listen_parts
    model.listen()
    assert model.listening and listener.enabled
    assert model.listenError == ""
    event = types.SimpleNamespace(
        event_type=InputType.Keyboard, identifier=(63, False), device_guid=_KEYS
    )
    listener.listeningTerminated.emit([event])
    assert not model.listening and not listener.enabled
    assert model.heardText == "Heard: F5"
    assert model.text == 'key:"F5"'
    assert [r["inputLabel"] for r in _results(model)] == ["F5"]


def test_listen_a_stick_button(
    model: SearchModel,
    listen_parts: tuple[_Listener, _Osc],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import input_pairing

    monkeypatch.setattr(input_pairing, "device_label", lambda guid: "T.16000M")
    listener, _ = listen_parts
    model.listen()
    event = types.SimpleNamespace(
        event_type=InputType.JoystickButton, identifier=4, device_guid=_STICK
    )
    listener.listeningTerminated.emit([event])
    assert model.text == 'device:"T.16000M" "Button 4"'
    assert [r["inputLabel"] for r in _results(model)] == ["Button 4"]


def test_listen_osc_and_esc(
    model: SearchModel, listen_parts: tuple[_Listener, _Osc]
) -> None:
    listener, osc = listen_parts
    model.listen()
    osc.incoming.emit("/fader1", [0.5], ("127.0.0.1", 9000))
    assert model.heardText == "Heard: OSC /fader1"
    assert model.text == 'osc:"/fader1"'
    model.listen()
    listener.listeningTerminated.emit([])  # Esc held
    assert not model.listening and model.text == 'osc:"/fader1"'


def test_listen_says_when_osc_listening_is_off(
    model: SearchModel, listen_parts: tuple[_Listener, _Osc]
) -> None:
    _, osc = listen_parts
    osc.state = "closed"
    model.listen()
    assert model.listenError == (
        "OSC is not listening (Listen for OSC messages is off)"
    )
    osc.incoming.emit("/fader1", [1.0], None)
    assert model.listening  # not heard: OSC isn't hooked
    model.stopListen()
    assert not model.listening


def test_qml_creates_it(
    qapp: object, saved: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gremlin.Device's SearchModel from QML."""
    from PySide6 import QtQml

    stand_in = _Index(ROWS)
    monkeypatch.setattr(search_model, "_default_index", lambda: stand_in)
    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine)
    component.setData(
        b"import Gremlin.Device\nSearchModel { text: 'gear'; lookIn: 'all' }",
        QtCore.QUrl(),
    )
    made = component.create()
    assert made is not None, component.errorString()
    made.search()
    assert made.property("resultCount") == 1
    made.close()
    made.deleteLater()
    # Gone before the engine is, not left for a later test's event loop.
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    del engine


def test_set_clipboard_only_on_the_main_thread(
    qapp: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The program's own path (a stand-in clipboard): set on the main
    thread, nothing off it."""
    import threading

    got: list[str] = []
    board = types.SimpleNamespace(setText=got.append)
    monkeypatch.setattr(QtGui.QGuiApplication, "clipboard", lambda: board)
    _REAL_SET_CLIPBOARD("main")
    worker = threading.Thread(target=_REAL_SET_CLIPBOARD, args=("worker",))
    worker.start()
    worker.join(5.0)
    assert not worker.is_alive()
    # Earlier tests in the same process may have made a QCoreApplication
    # (no clipboard): then the helper must leave the clipboard alone.
    gui = isinstance(QtGui.QGuiApplication.instance(), QtGui.QGuiApplication)
    assert got == (["main"] if gui else [])


def test_nothing_found_hint_texts(model: SearchModel) -> None:
    model.lookIn = "this"
    model.setFilter("vjoy", True)
    model.matchCase = True
    model.wholeWord = True
    model.searchFor("zzzz")
    texts = [h["text"] for h in model.nothingFoundHints]
    assert texts == [
        "Search all profiles",
        "Clear filters",
        "Turn off Match case",
        "Turn off Whole word",
    ]
    model.wholeWord = False
    model.regex = True
    model.searchFor("zzzz")
    assert "Turn off Regular expression" in [h["text"] for h in model.nothingFoundHints]


def test_prefixes_for_the_help_popup(model: SearchModel) -> None:
    from gremlin import search_query

    names = [p["name"] for p in model.prefixes]
    assert names == list(search_query.PREFIXES)
    assert all(p["description"] for p in model.prefixes)


def test_search_for_target_finds_every_use(model: SearchModel) -> None:
    model.searchFor("gear")
    row = next(i for i, r in enumerate(_rows(model)) if r["rowKind"] == "result")
    model.searchForTarget(row)
    assert model.text == 'vjoy:"vJoy 1 Button 3"'
    # Every row sending to it: three in DCS and the Device Library setup.
    assert model.resultCount == 4
    header = 0
    model.searchForTarget(header)  # a header: nothing changes
    assert model.text == 'vjoy:"vJoy 1 Button 3"'


def test_target_text_without_a_target_prefix() -> None:
    row = _row(targets=("Combat",), target_keys=(("mode", "Combat"),))
    assert search_model.target_text(row) == 'mode:"Combat"'
    # A target no prefix reads (a condition on an input): the text alone.
    row = _row(targets=("T.16000M Button 9",), target_keys=(("input", _STICK, 1, 9),))
    assert search_model.target_text(row) == '"T.16000M Button 9"'
    assert search_model.target_text(_row(targets=(), target_keys=())) == ""


def _inherited(row: SearchRow, parent: str) -> object:
    """row seen from a child mode that inherits it from parent (a stand-in
    until SearchRow has inherited_from)."""
    import dataclasses

    if any(f.name == "inherited_from" for f in dataclasses.fields(SearchRow)):
        return dataclasses.replace(row, inherited_from=parent)  # type: ignore[call-arg]
    fields = {f.name: getattr(row, f.name) for f in dataclasses.fields(row)}
    return types.SimpleNamespace(**fields, inherited_from=parent)


def test_notes_are_shown_and_lit_when_they_matched(qapp: object, saved: dict) -> None:
    """A typed note matched: the row carries its notes with the matched
    letters lit, the detail pane lists them (D-01-SEARCH-INDEX)."""
    rows = [_row(notes=("Lower the landing gear",), input_label="Button 9")]
    made = SearchModel(index=_Index(rows))
    try:
        made.searchFor("landing")
        assert "notes" in {bytes(v).decode() for v in made.roleNames().values()}
        found = _results(made)
        assert found[0]["notes"] == ["Lower the landing gear"]
        assert found[0]["highlights"]["notes:0"] == [[10, 17]]
        row = next(i for i, r in enumerate(_rows(made)) if r["rowKind"] == "result")
        assert made.detail(row)["notes"] == ["Lower the landing gear"]
        assert "Lower the landing gear" in made.copyText(row)
    finally:
        made.close()
        made.deleteLater()


def test_inherited_rows_say_where_they_come_from(
    qapp: object, saved: dict, copied: list[str]
) -> None:
    """A binding seen from a child mode that inherits it: role inheritedFrom,
    tag "inherited", detail and Copy as text say "Inherited from <mode>"."""
    rows = [_inherited(_row(mode="Combat", input_label="Button 8"), "Default")]
    made = SearchModel(index=_Index(rows))  # type: ignore[arg-type]
    try:
        made.searchFor("button 8")
        found = _results(made)
        assert found[0]["inheritedFrom"] == "Default"
        assert "inherited" in found[0]["tags"]
        row = next(i for i, r in enumerate(_rows(made)) if r["rowKind"] == "result")
        assert made.detail(row)["inheritedFrom"] == "Default"
        assert "Inherited from Default" in made.copyText(row)
    finally:
        made.close()
        made.deleteLater()


def test_own_rows_are_not_inherited(model: SearchModel) -> None:
    model.searchFor("gear")
    found = _results(model)
    assert found[0]["inheritedFrom"] == ""
    assert "inherited" not in found[0]["tags"]
