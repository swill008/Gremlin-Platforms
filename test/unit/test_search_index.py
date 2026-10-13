# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Search index (01 S157-S164, D-01-SEARCH-INDEX): rows from every profile
file in the folder (read without opening them), the open profile in place
of its file, Device Library setups and registered sources; "Used twice";
unreadable files with the reason; status while it builds."""

from __future__ import annotations

import pathlib
import sys
import threading
import uuid
from collections.abc import Iterator

sys.path.append(".")

import pytest

from gremlin import search_index, shared_state
from gremlin.modules import ids, output
from gremlin.search_index import SearchIndex, SearchRow
from gremlin.types import InputType

B = InputType.JoystickButton
_STICK = uuid.UUID("{4DCB3090-97EC-11EB-8003-444553540000}")
_KEY_A = (0x1E, False)
_WAIT_S = 20.0


@pytest.fixture(autouse=True)
def _outputs_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(output, "cant_send_text", lambda *a, **k: None)
    monkeypatch.setattr(output, "xbox_cant_send_text", lambda *a, **k: None)
    monkeypatch.setattr(output, "osc_cant_send_text", lambda *a, **k: None)


def _vjoy(vjoy_id: int, control: int) -> object:
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(B)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = B
    action.vjoy_input_id = control
    return action


def _bind(
    profile: object,
    guid: uuid.UUID,
    input_id: object,
    action: object,
    name: str = "",
    mode: str = "Default",
) -> None:
    from action_plugins.root import RootData
    from gremlin.profile import InputItemBinding

    input_type = InputType.Keyboard if guid == ids.KEYBOARD else B
    item = profile.get_input_item(guid, input_type, input_id, mode, True)  # type: ignore[attr-defined]
    root = RootData(B)
    root.children = [action]
    binding = InputItemBinding(item)
    binding.root_action = root
    binding.behavior = B
    item.action_sequences.append(binding)
    item.action_name = name
    for each in (root, action):
        profile.library.add_action(each)  # type: ignore[attr-defined]


@pytest.fixture
def folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Iterator[pathlib.Path]:
    """a.xml: Button 1 ("Gear") and Button 2 both send vJoy 1 Button 5, and
    Keyboard A sends vJoy 2 Button 1. b.xml: Button 3 sends vJoy 1 Button 5.
    bad.xml can't be read."""
    from gremlin.profile import Profile

    root = tmp_path / "profiles"
    root.mkdir()
    a = Profile()
    monkeypatch.setattr(shared_state, "current_profile", a)
    _bind(a, _STICK, 1, _vjoy(1, 5), name="Gear")
    _bind(a, _STICK, 2, _vjoy(1, 5))
    _bind(a, ids.KEYBOARD, _KEY_A, _vjoy(2, 1))
    a.to_xml(root / "a.xml")
    b = Profile()
    monkeypatch.setattr(shared_state, "current_profile", b)
    _bind(b, _STICK, 3, _vjoy(1, 5))
    b.to_xml(root / "b.xml")
    (root / "bad.xml").write_text("this is not a profile", encoding="utf-8")
    monkeypatch.setattr(shared_state, "current_profile", None)
    yield root


def _built(index: SearchIndex, open_profile: object = None) -> tuple[SearchRow, ...]:
    index.build(open_profile=open_profile)
    assert index.wait(_WAIT_S)
    return index.rows()


def _index(folder: pathlib.Path, **kw: object) -> SearchIndex:
    return SearchIndex(
        folder=folder,
        plugged=lambda guid, name: True,
        library=False,
        **kw,  # type: ignore[arg-type]
    )


def test_rows_from_every_profile_file(folder: pathlib.Path) -> None:
    rows = _built(_index(folder))
    assert {r.source_name for r in rows} == {"a", "b"}
    assert {r.source for r in rows} == {"profile"}
    gear = next(r for r in rows if r.custom_name == "Gear")
    assert gear.input_label == "Button 1"
    assert gear.source_path == str(folder / "a.xml")
    assert gear.target_keys == (("vjoy", 1, B.value, 5),)
    assert gear.targets and all(gear.targets)
    assert gear.role == "sends-output"
    assert gear.plugged is True
    assert gear.mode == "Default"
    assert {"action", "name", "vjoy"} <= gear.kinds
    key = next(r for r in rows if r.device_guid == str(ids.KEYBOARD))
    assert "key" in key.kinds
    assert "name" not in key.kinds


def test_unreadable_file_listed_with_reason(folder: pathlib.Path) -> None:
    index = _index(folder)
    _built(index)
    status = index.status()
    assert status["state"] == "ready"
    assert status["done"] == status["total"] == 3
    [(path, reason)] = status["unreadable"]
    assert path == str(folder / "bad.xml")
    assert "bad.xml" in reason


def test_used_twice_same_output_same_mode_same_profile(folder: pathlib.Path) -> None:
    rows = _built(_index(folder))
    twice = {(r.source_name, r.input_id) for r in rows if r.used_twice}
    # b.xml's Button 3 sends the same output, but in another profile.
    assert twice == {("a", 1), ("a", 2)}


def test_open_profile_rows_replace_its_file(folder: pathlib.Path) -> None:
    from gremlin.profile import Profile

    opened = Profile()
    opened.from_xml(folder / "a.xml")
    _bind(opened, _STICK, 7, _vjoy(3, 3))
    index = _index(folder)
    rows = _built(index, opened)
    from_a = [r for r in rows if r.source_name == "a"]
    assert {r.source for r in from_a} == {"open"}
    assert 7 in {r.input_id for r in from_a}
    assert len(from_a) == 4
    index.rebuild_open(None)
    from_a = [r for r in index.rows() if r.source_name == "a"]
    assert {r.source for r in from_a} == {"profile"}
    assert 7 not in {r.input_id for r in from_a}


def _row(input_id: int, **kw: object) -> SearchRow:
    values: dict = dict(
        source="profile",
        source_name="Plug",
        source_path="plug",
        device_guid=str(_STICK),
        device_name="Stick",
        plugged=None,
        mode="Default",
        input_type=B.value,
        input_id=input_id,
        input_label=f"Button {input_id}",
        custom_name="",
        action_tag="plug",
        action_name="Plug",
        text="Plug",
        targets=("Out 1",),
        target_keys=(("plug", 1),),
        role="sends-output",
        not_found=False,
        why="",
        used_twice=False,
        binding_index=0,
        path=("Plug",),
        kinds=frozenset({"action"}),
    )
    values.update(kw)
    return SearchRow(**values)


def test_register_source_is_the_plug_in_point(folder: pathlib.Path) -> None:
    index = _index(folder)
    index.register_source("Plug", lambda: [_row(1), _row(2)])

    def broken() -> list[SearchRow]:
        raise RuntimeError("no plug today")

    index.register_source("Broken", broken)
    rows = _built(index)
    plug = [r for r in rows if r.source_name == "Plug"]
    assert len(plug) == 2
    assert all(r.used_twice for r in plug)
    assert ("Broken", "no plug today") in index.status()["unreadable"]


def test_status_while_building_and_change_callback(folder: pathlib.Path) -> None:
    release = threading.Event()
    entered = threading.Event()
    changes: list[int] = []

    def slow() -> list[SearchRow]:
        entered.set()
        assert release.wait(_WAIT_S)
        return [_row(1)]

    index = _index(folder, on_change=lambda: changes.append(1))
    index.register_source("Slow", slow)
    index.build(open_profile=None)
    try:
        assert entered.wait(_WAIT_S)
        status = index.status()
        assert status["state"] == "building"
        assert status["total"] == 4
        assert status["done"] == 3
        # Results while building: the files are in already.
        assert {r.source_name for r in index.rows()} == {"a", "b"}
    finally:
        release.set()
    assert index.wait(_WAIT_S)
    assert index.status()["state"] == "ready"
    assert "Plug" in {r.source_name for r in index.rows()}
    assert changes


def test_device_library_setups(
    monkeypatch: pytest.MonkeyPatch, folder: pathlib.Path
) -> None:
    from gremlin import device_library
    from gremlin.profile import Profile
    from gremlin.ui import device_pack

    made = Profile()
    made.from_xml(folder / "a.xml")
    wires = device_pack._collect_wires(str(_STICK), None, made)
    setups = [
        {"key": "set1", "name": "Setup 1", "holds": ["bindings"], "pack": "x.gmap"}
    ]
    monkeypatch.setattr(
        device_library,
        "devices",
        lambda: [{"name": "Stick", "guid": str(_STICK), "setups": setups}],
    )
    asked: list[str] = []
    monkeypatch.setattr(
        device_library, "setup_wires", lambda key: asked.append(key) or wires
    )
    rows = list(search_index.library_rows())
    assert {r.source for r in rows} == {"library"}
    assert {r.source_name for r in rows} == {"Setup 1"}
    assert {r.device_name for r in rows} == {"Stick"}
    assert {r.plugged for r in rows} == {None}
    assert {r.input_id for r in rows} == {1, 2}
    assert all(r.used_twice for r in rows)
    assert {r.custom_name for r in rows} == {"Gear", ""}
    assert asked == ["set1"]


def test_device_library_is_a_built_in_source(
    monkeypatch: pytest.MonkeyPatch, folder: pathlib.Path
) -> None:
    called: list[int] = []
    monkeypatch.setattr(
        search_index, "library_rows", lambda: called.append(1) or iter(())
    )
    index = SearchIndex(folder=folder, plugged=lambda guid, name: True)
    _built(index)
    assert index.status()["total"] == 4
    assert called == [1]


def test_saved_file_is_read_again(folder: pathlib.Path) -> None:
    from gremlin.profile import Profile

    index = _index(folder)
    _built(index)
    changed = Profile()
    changed.from_xml(folder / "b.xml")
    _bind(changed, _STICK, 8, _vjoy(4, 4))
    changed.to_xml(folder / "b.xml")
    (folder / "bad.xml").write_text("<still not a profile", encoding="utf-8")
    for name in ("b.xml", "bad.xml"):
        thread = index.file_saved(folder / name)
        assert thread is not None
        thread.join(_WAIT_S)
        assert not thread.is_alive()
    assert 8 in {r.input_id for r in index.rows() if r.source_name == "b"}
    assert [p for p, _ in index.status()["unreadable"]] == [str(folder / "bad.xml")]
    # A file outside the profiles folder is not searched.
    assert index.file_saved(folder.parent / "elsewhere.xml") is None


def test_default_index_is_one_and_hears_saves(
    monkeypatch: pytest.MonkeyPatch, folder: pathlib.Path
) -> None:
    from gremlin import util

    monkeypatch.setattr(search_index, "_default", None)
    monkeypatch.setattr(util, "profiles_dir", lambda: folder)
    monkeypatch.setattr(search_index, "library_rows", lambda: iter(()))
    monkeypatch.setattr(search_index, "_default_plugged", lambda guid, name: True)
    seen: list[pathlib.Path] = []
    first = search_index.default_index()
    monkeypatch.setattr(first, "file_saved", lambda path: seen.append(path))
    assert search_index.default_index() is first
    assert first.wait(_WAIT_S)
    assert {r.source_name for r in first.rows()} == {"a", "b"}
    search_index.note_saved(folder / "a.xml")
    assert seen == [folder / "a.xml"]
    monkeypatch.setattr(search_index, "_default", None)
    search_index.note_saved(folder / "a.xml")  # no index: nothing to do
    assert seen == [folder / "a.xml"]


def test_user_typed_action_text_is_found(folder: pathlib.Path) -> None:
    """Text the user typed into an action (search_texts()) is searchable:
    a Description's note is found by a free term."""
    from action_plugins.description import DescriptionData
    from gremlin import search_query
    from gremlin.profile import Profile

    opened = Profile()
    opened.from_xml(folder / "a.xml")
    note = DescriptionData(B)
    note.description = "Flaps down before landing"
    _bind(opened, _STICK, 9, note)
    rows = _built(_index(folder), opened)
    query = search_query.parse("flaps landing")
    found = [r for r in rows if search_query.match(r, query) is not None]
    assert [(r.source_name, r.input_id) for r in found] == [("a", 9)]
    assert found[0].notes == ("Flaps down before landing",)


def test_key_prefix_finds_map_to_keyboard_sending_it(folder: pathlib.Path) -> None:
    """key:F5 finds a stick button whose Map to Keyboard presses F5."""
    from action_plugins.map_to_keyboard import MapToKeyboardData
    from gremlin import keyboard, search_query
    from gremlin.profile import Profile

    opened = Profile()
    opened.from_xml(folder / "a.xml")
    press = MapToKeyboardData(B)
    press.keys = [keyboard.key_from_name("F5")]
    _bind(opened, _STICK, 11, press)
    rows = _built(_index(folder), opened)
    query = search_query.parse("key:F5")
    found = [r for r in rows if search_query.match(r, query) is not None]
    assert [(r.source_name, r.input_id) for r in found] == [("a", 11)]


def test_child_mode_inherits_parent_bindings(folder: pathlib.Path) -> None:
    """A child mode with no own binding for an input runs its parent's
    (event_handler build_event_lookup): Search lists it in the child, tagged
    with the parent, and Used twice counts it. A child that binds the input
    itself inherits nothing for it."""
    from gremlin.profile import Profile

    p = Profile()
    p.modes.add_mode("Child")
    p.modes.set_parent("Child", "Default")
    p.modes.add_mode("Own")
    p.modes.set_parent("Own", "Default")
    _bind(p, _STICK, 1, _vjoy(1, 5))
    _bind(p, _STICK, 2, _vjoy(1, 5), mode="Child")
    _bind(p, _STICK, 1, _vjoy(3, 3), mode="Own")
    rows = search_index.profile_rows(p, "open", "p", "")
    child = [r for r in rows if r.mode == "Child"]
    inherited = [r for r in child if r.inherited_from]
    assert [(r.input_id, r.inherited_from) for r in inherited] == [(1, "Default")]
    assert {r.input_id for r in child} == {1, 2}
    assert all(r.used_twice for r in child)
    assert inherited[0].target_keys == (("vjoy", 1, B.value, 5),)
    own = [r for r in rows if r.mode == "Own"]
    assert [(r.input_id, r.inherited_from) for r in own] == [(1, "")]
    parent = [r for r in rows if r.mode == "Default"]
    assert [r.inherited_from for r in parent] == [""]
    assert not parent[0].used_twice
