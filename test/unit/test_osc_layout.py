# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page's row model on the shared base (D-09-OSC-PAGE, batch 1).

OscLayoutModel: one parent per OSC input with the settings line (S134),
groups / order / your names in OSC's module file (S28, S133), page Undo
(S131) also for the Add window's edits, no Hide system name (S132),
live value and last seen (S141), Send Test (S145), Change Address, Edit
Settings on several inputs (S146), Copy for Companion (S122), Clear (S27).

Spec: 09 S129-S136, S141-S146.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import osc_device_file, plugin_manager, shared_state
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import osc_device_model
from gremlin.ui.osc_device_model import OscDeviceManagementModel
from gremlin.ui.osc_layout import (
    OscLayoutModel,
    OscLayoutStore,
    settings_line,
)


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """OSC's module file in a temporary modules folder."""
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def copied(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    got: list[str] = []
    monkeypatch.setattr(osc_device_model, "copy_text", lambda t: got.append(t) or True)
    return got


@pytest.fixture
def page(qapp: object, modules: Path) -> Iterator[OscLayoutModel]:
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    saved = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    model = OscLayoutModel()
    yield model
    model.endPane()
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    shared_state.current_profile = saved


def _add(address: str, **settings: Any) -> str:  # noqa: ANN401
    row, error = osc_device_model.add_input({"address": address, **settings})
    assert row is not None and not error, error
    osc_device_model._emit_modified()
    return row.uid


def _key(address: str) -> str:
    row = OscDevice().find_address(address)
    assert row is not None
    word = "axis" if row.input_type == InputType.JoystickAxis else "button"
    return f"parent:{word}:{row.input_id}"


def _rows(model: OscLayoutModel) -> list[dict]:
    names = {int(k): bytes(v.data()).decode() for k, v in model.roleNames().items()}
    out = []
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        out.append({name: model.data(index, role) for role, name in names.items()})
    return out


def _parent(model: OscLayoutModel, address: str) -> dict:
    key = _key(address)
    [row] = [r for r in _rows(model) if r["key"] == key]
    return row


def _vjoy(button: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _actions(address: str) -> int:
    row = OscDevice().find_address(address)
    if row is None:
        return -1
    profile = shared_state.current_profile
    assert profile is not None
    return sum(
        len(item.action_sequences)
        for item in profile.inputs.get(OSC_DEVICE_UUID, [])
        if item.input_type == row.input_type and item.input_id == row.input_id
    )


def _bind(page: OscLayoutModel, address: str) -> None:
    page.beginNewAction(_key(address))
    shadow: Any = page._pane_shadow
    shadow.action_sequences[0].root_action.insert_action(_vjoy(3), "children")
    assert page.commitPane() == 0
    page.endPane()


# -- rows -------------------------------------------------------------------


def test_each_input_is_a_parent_row_with_its_settings_line(
    page: OscLayoutModel,
) -> None:
    _add("/deck/1", mode="button")
    _add("/fader", mode="axis", range_min=-1, range_max=1, source=1)
    button = _parent(page, "/deck/1")
    assert button["title"] == "Button 1 - /deck/1"
    assert button["subtitle"] == "Button · Message only · Source value: P1"
    assert button["systemName"] == "/deck/1"
    assert button["uid"] == OscDevice().find_address("/deck/1").uid
    axis = _parent(page, "/fader")
    assert axis["subtitle"] == "Axis · Source value: P2 · Min: -1 · Max: 1"
    assert [r["rowKind"] for r in _rows(page)] == ["group", "parent", "parent"]


def test_settings_line_words() -> None:
    from gremlin.osc_rows import OscRow

    trig = OscRow("u", InputType.JoystickButton, 1, "/t", trigger=True, delay_ms=250)
    assert settings_line(trig) == (
        "Button · Message only · Source value: P1 · Trigger on message · 250 ms"
    )
    data = OscRow(
        "u",
        InputType.JoystickButton,
        1,
        "/d",
        mode="change",
        cmd_mode="data",
        data=["1", "2"],
    )
    assert settings_line(data) == "Change · Message + data: 1, 2"
    enc = OscRow("u", InputType.JoystickAxis, 1, "/e", mode="encoder")
    assert settings_line(enc) == (
        "Encoder · Format: Auto · Output: Axis · Step size: 0.05"
    )


def test_a_new_input_with_no_actions_takes_its_first_action(
    page: OscLayoutModel,
) -> None:
    """OP2 / S130 on the page's shared pane: Add Action on an empty input."""
    _add("/deck/1")
    assert _parent(page, "/deck/1")["childCount"] == 0
    _bind(page, "/deck/1")
    assert _actions("/deck/1") == 1
    assert _parent(page, "/deck/1")["childCount"] == 1
    page.undo()
    assert _actions("/deck/1") == 0
    page.redo()
    assert _actions("/deck/1") == 1


def test_your_name_shows_beside_the_address_and_never_hides_it(
    page: OscLayoutModel,
) -> None:
    _add("/deck/1")
    key = _key("/deck/1")
    page.setRowLabel(key, "Gear Toggle", True)
    row = _parent(page, "/deck/1")
    assert row["title"] == "Button 1 - /deck/1   Gear Toggle"
    assert row["userName"] == "Gear Toggle"
    assert page.hidesSystem(key) is False


def test_filters_type_and_search(page: OscLayoutModel) -> None:
    _add("/deck/1")
    _add("/fader", mode="axis")
    page.setFilter("", "axis", False, False, False)
    assert [r["key"] for r in _rows(page) if r["rowKind"] == "parent"] == [
        _key("/fader")
    ]
    page.setFilter("deck", "all", False, False, False)
    assert [r["key"] for r in _rows(page) if r["rowKind"] == "parent"] == [
        _key("/deck/1")
    ]


# -- groups, order, names in osc.json ----------------------------------------


def test_groups_order_and_names_are_kept_in_osc_json(
    page: OscLayoutModel, modules: Path
) -> None:
    _add("/deck/1")
    _add("/deck/2")
    _add("/fader", mode="axis")
    first, second, fader = _key("/deck/1"), _key("/deck/2"), _key("/fader")
    page.addGroup("Stream Deck")
    page.setSelection([first, second, fader])
    page.moveSelected("Stream Deck")
    page.moveParent(second, first, "before")
    page.setUserName(fader, "Volume")
    shown = [
        r["key"]
        for r in _rows(page)
        if r["groupName"] == "Stream Deck" and r["rowKind"] == "parent"
    ]
    # Buttons and axes in one group (S133).
    assert shown == [second, first, fader]

    # Kept with the inputs until File > Save Profile (D-09-OSC-FILE).
    assert not (modules / "osc.json").is_file() or "layout" not in json.loads(
        (modules / "osc.json").read_text(encoding="utf-8")
    )
    assert OscDevice().rows.dirty
    osc_device_file.save()
    doc = json.loads((modules / "osc.json").read_text(encoding="utf-8"))
    uid = OscDevice().find_address("/fader").uid
    assert doc["layout"]["groups"] == ["Stream Deck"]
    assert doc["layout"]["group_of"][f"osc:{uid}"] == "Stream Deck"
    assert doc["claim"]["friendly"][f"osc:{uid}"] == "Volume"

    osc_device_file.load()
    again = OscLayoutStore()
    again.load()
    assert again.group_names() == ["Stream Deck"]
    assert [i.address for i in again.ordered()] == ["/deck/2", "/deck/1", "/fader"]
    assert again[uid].second_name == "Volume"


def test_order_by_address(page: OscLayoutModel) -> None:
    for address in ("/c", "/a", "/b"):
        _add(address)
    page.sortBySystem()
    assert [r["systemName"] for r in _rows(page) if r["rowKind"] == "parent"] == [
        "/a",
        "/b",
        "/c",
    ]
    assert page.property("lastChange") == "Last change: Sort by Address"


def test_group_move_is_undone(page: OscLayoutModel) -> None:
    _add("/deck/1")
    page.addGroup("G")
    page.setSelection([_key("/deck/1")])
    page.moveSelected("G")
    assert _parent(page, "/deck/1")["groupName"] == "G"
    page.undo()
    assert _parent(page, "/deck/1")["groupName"] == ""


# -- Undo of the page's own edits ---------------------------------------------


def test_delete_takes_the_input_and_its_actions_and_undo_puts_both_back(
    page: OscLayoutModel,
) -> None:
    _add("/deck/1")
    _bind(page, "/deck/1")
    uid = OscDevice().find_address("/deck/1").uid
    page.deleteParents([_key("/deck/1")])
    assert OscDevice().rows.by_uid(uid) is None
    assert OscDevice().rows.dirty
    page.undo()
    assert OscDevice().rows.by_uid(uid) is not None
    assert _actions("/deck/1") == 1
    page.redo()
    assert OscDevice().rows.by_uid(uid) is None


def test_clear_all_is_one_undo_step(page: OscLayoutModel) -> None:
    _add("/a")
    _add("/b", mode="axis")
    page.clearAll()
    assert len(OscDevice().rows) == 0
    assert page.property("lastChange") == "Last change: Clear all inputs"
    page.undo()
    assert sorted(r.label for r in OscDevice().rows.rows()) == ["/a", "/b"]


def test_the_add_window_edits_are_page_undo_steps(page: OscLayoutModel) -> None:
    """S131: Add / Import through OscDeviceManagementModel."""
    add = OscDeviceManagementModel()
    added: list[str] = []
    add.inputAdded.connect(added.append)
    assert add.createConfiguredInput({"address": "/new", "mode": "button"})
    assert added == [OscDevice().find_address("/new").uid]
    assert page.keyOfUid(added[0]) == _key("/new")
    assert page.property("lastChange") == "Last change: Add /new"
    add.importInputs("/i1\n/i2 A")
    assert page.property("lastChange") == "Last change: Import 2 inputs"
    page.undo()
    assert OscDevice().find_address("/i1") is None
    page.undo()
    assert OscDevice().find_address("/new") is None
    page.redo()
    assert OscDevice().find_address("/new") is not None


def test_change_address_checks_and_undoes(page: OscLayoutModel) -> None:
    _add("/one")
    _add("/two")
    key = _key("/one")
    assert page.changeAddress(key, "noslash") != ""
    assert "already" in page.changeAddress(key, "/two")
    assert page.changeAddress(key, "/uno") == ""
    assert page.addressOf(key) == "/uno"
    page.undo()
    assert page.addressOf(key) == "/one"


# -- Edit Settings on several inputs (S146) -----------------------------------


def test_edit_settings_for_shows_shared_values_and_blanks_differences(
    page: OscLayoutModel,
) -> None:
    _add("/a", mode="button", delay_ms=100)
    _add("/b", mode="button", delay_ms=200)
    shared = page.editSettingsFor([_key("/a"), _key("/b")])
    assert shared["count"] == 2
    assert shared["mode"] == "button"
    assert shared["delay_ms"] == ""
    assert "delay_ms" in shared["mixed"] and "mode" not in shared["mixed"]
    assert shared["address"] == ""


def test_apply_settings_changes_only_the_given_fields_in_one_step(
    page: OscLayoutModel,
) -> None:
    _add("/a", delay_ms=100)
    _add("/b", delay_ms=200)
    _add("/c", mode="axis")
    _bind(page, "/a")  # /a has actions: it can't become an axis
    keys = [_key("/a"), _key("/b")]
    assert page.applySettings(keys, {"source": 2}) == ""
    rows = {r.label: r for r in OscDevice().rows.rows()}
    assert (rows["/a"].source, rows["/a"].delay_ms) == (2, 100)
    assert (rows["/b"].source, rows["/b"].delay_ms) == (2, 200)
    assert page.property("lastChange") == "Last change: Edit Settings of 2 inputs"
    message = page.applySettings(keys, {"mode": "axis"})
    assert message.startswith("/a: Remove this input's actions first")
    assert OscDevice().find_address("/b").input_type == InputType.JoystickAxis
    page.undo()
    assert OscDevice().find_address("/b").input_type == InputType.JoystickButton
    page.undo()
    assert OscDevice().find_address("/b").source == 0


# -- live value, Send Test, Companion -------------------------------------------


def test_live_value_and_send_test_update_only_that_row(page: OscLayoutModel) -> None:
    _add("/deck/1")
    _add("/fader", mode="axis")
    assert _parent(page, "/deck/1")["lastSeen"] == "never"
    changed: list[int] = []
    page.dataChanged.connect(lambda a, b, roles=None: changed.append(a.row()))
    # No Run: actions don't fire, the live value still shows (S145).
    assert page.sendTest(_key("/fader"), "value", 0.5) is False
    row = _parent(page, "/fader")
    assert row["liveValue"] == "0.00"  # 0.5 of 0..1 is the middle, -1..1 scale
    assert row["liveSynthetic"] is True
    assert row["lastSeen"].startswith("last seen")
    index = next(i for i, r in enumerate(_rows(page)) if r["key"] == _key("/fader"))
    assert changed == [index]
    page.sendTest(_key("/deck/1"), "press", 0)
    assert _parent(page, "/deck/1")["liveValue"] == "Pressed"
    assert page.lastSeenText(0) == "never"


def test_copy_for_companion(page: OscLayoutModel, copied: list[str]) -> None:
    _add("/sd/fire")
    text = page.copyForCompanion(_key("/sd/fire"))
    assert "Send integer /sd/fire 1" in text
    assert copied == [text]
