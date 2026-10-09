# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC inputs are shown by their address (D-09-OSC-ADDRESSES, plan H): the
Button Map's chips and pool, and the Home OSC card's last-pressed line, say
"/fire" instead of "Button 1"; a name the user gave still wins."""

from __future__ import annotations

import pathlib
import types
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtQml

from gremlin.modules import ids, store
from gremlin.osc import OscDevice
from gremlin.types import InputType
from gremlin.ui import hardware_profile, input_pairing

_ROOT = pathlib.Path(__file__).parents[2]
_OSC = str(ids.OSC)


@pytest.fixture
def osc_rows() -> Iterator[object]:
    rows = OscDevice().rows
    rows.reset()
    rows.create(InputType.JoystickButton, "/fire", input_id=1)
    rows.create(InputType.JoystickAxis, "/throttle", input_id=2)
    yield rows
    rows.reset()


# --- Button Map: the pool rows carry the address ---------------------------


def test_osc_pool_rows_carry_the_address(
    osc_rows: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(input_pairing, "_device_name", lambda g: "OSC")
    monkeypatch.setattr(
        hardware_profile, "_device_input_ids", lambda g: ([1], [2], []))
    monkeypatch.setattr(store, "read", lambda name, g="": {})
    rows = hardware_profile.chips_for_guid(_OSC)
    names = {(r["kind"], r["hwId"]): r.get("hwName") for r in rows}
    assert names == {("btn", 1): "/fire", ("axis", 2): "/throttle"}
    # A renamed address gives a new key, so the card reads the rows again.
    before = hardware_profile.chips_key(_OSC)
    row = OscDevice().rows.by_number(InputType.JoystickButton, 1)
    OscDevice().rows.set_label(row.uid, "/shoot")
    assert hardware_profile.chips_key(_OSC) != before


def test_other_devices_have_no_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(input_pairing, "_device_name", lambda g: "Stick")
    monkeypatch.setattr(
        hardware_profile, "_device_input_ids", lambda g: ([1], [], []))
    monkeypatch.setattr(store, "read", lambda name, g="": {})
    rows = hardware_profile.chips_for_guid("{11111111-2222-3333-4444-555555555555}")
    assert rows and "hwName" not in rows[0]


# --- Button Map: chip names in the real rig_chips.js ------------------------


_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture
def chips_js() -> Iterator[QtQml.QJSEngine]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    engine = QtQml.QJSEngine()
    source = _ROOT / "qml" / "rig_chips.js"
    result = engine.evaluate(source.read_text(encoding="utf-8"), str(source))
    assert not result.isError(), result.toString()
    # The editor's face, with the OSC pool rows chips_for_guid gives.
    engine.evaluate(
        "var tick = 0; var nodes = [];"
        # Editor helpers from other files (rig_groups.js, rig_draw.js).
        " function isGroup(n) { return false }; function isDraw(n) { return false };"
        " var face = {chipRows: ["
        '{kind: "btn", hwId: 1, hwName: "/fire", dest: ""},'
        ' {kind: "axis", hwId: 2, hwName: "/throttle", dest: ""},'
        ' {kind: "btn", hwId: 3, dest: ""}],'
        ' labelBtn: function(i) { return "—" },'
        ' labelAxis: function(i) { return "—" },'
        ' labelHat: function(i) { return "—" }}'
    )
    yield engine


def _js(engine: QtQml.QJSEngine, code: str) -> str:
    result = engine.evaluate(code)
    assert not result.isError(), result.toString()
    return result.toString()


def test_osc_chips_show_the_address(chips_js: QtQml.QJSEngine) -> None:
    assert _js(chips_js, 'hardwareLabel("btn", 1)') == "/fire"
    assert _js(chips_js, 'hardwareLabel("axis_stack", 2)') == "/throttle"
    # A placed chip that stored the old plain name shows the address.
    assert _js(chips_js, 'friendlyOf({kind: "btn", hwId: 1, friendly: "Button 1"})') \
        == "/fire"
    # The pool lists it by its address too.
    assert _js(chips_js, 'catalog().filter(function(c){return c.hwId===1})[0].hwName') \
        == "/fire"
    # An input with no address keeps its plain name.
    assert _js(chips_js, 'hardwareLabel("btn", 3)') == "Button 3"


def test_a_user_name_still_wins_over_the_address(chips_js: QtQml.QJSEngine) -> None:
    assert _js(chips_js, 'friendlyOf({kind: "btn", hwId: 1, friendly: "Trigger"})') \
        == "Trigger"
    # A new chip stores the plain name, so a later address change still shows.
    assert _js(chips_js, 'defaultFriendly("btn", 1)') == "Button 1"


# --- Home: the OSC card's last-pressed line ----------------------------------


def _last_line(guid: str, claim: dict, kind: str, hid: int) -> tuple[str, str]:
    from gremlin.ui import module_model

    row = types.SimpleNamespace(guid=guid, slug="osc")
    emitter = types.SimpleNamespace(emit=lambda *a: None)
    fake = types.SimpleNamespace(
        _last={}, _rows=[row], index=lambda r, c: None,
        dataChanged=emitter, lastChanged=emitter,
    )
    module_model.ModuleListModel._set_last(fake, row, kind, hid, claim)  # type: ignore[arg-type]
    return fake._last["osc"]


def test_home_osc_card_last_line_shows_the_address(osc_rows: object) -> None:
    assert _last_line(_OSC, {}, "button", 1) == ("/fire", "button 1")
    assert _last_line(_OSC, {}, "axis", 2)[0] == "/throttle"


def test_home_last_line_user_name_wins_and_sticks_keep_plain_names(
    osc_rows: object,
) -> None:
    claim = {"friendly": {"button:1": "Gun"}}
    assert _last_line(_OSC, claim, "button", 1)[0] == "Gun"
    stick = "{11111111-2222-3333-4444-555555555555}"
    assert _last_line(stick, {}, "button", 1)[0] == "Button 1"
