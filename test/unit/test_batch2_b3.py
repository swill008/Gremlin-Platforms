# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catch-up batch 2, agent B3: modules and Home cards (page 03, 06 Q16).

GL-139, GL-140, GL-142, GL-143, GL-146, GL-147 and GL-038 are also checked
by test_stage1_modules (their strict xfails were removed).
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from typing import cast
from unittest import mock

import pytest
from PySide6 import QtQml

from gremlin import shared_state
from gremlin.modules import auto_map, module_file, output
from gremlin.profile import Profile
from gremlin.ui import module_model
from test.unit.test_stage1_modules import (  # noqa: F401
    _OTHER,
    _ROOT,
    _app,
    _function_source,
    folder,
    mapped,
    setup_cards,
    stick_doc,
    stick_uid,
    vjoy_doc,
    write_module,
)

# --- GL-141: a damaged card turns back when the file is fixed --------------


def test_a_fixed_file_is_no_longer_damaged_after_a_settings_change(
    folder: Path,  # noqa: F811
) -> None:
    path = write_module(folder, "pjoy_pro", stick_doc())
    model = module_model.ModuleListModel()
    assert model.cardMap("pjoy_pro")["damaged"] == ""
    path.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    model._refresh_inplace()  # what configChanged runs
    card = model.cardMap("pjoy_pro")
    assert card["damaged"]
    assert card["status"] == "Module file damaged – inputs blocked"
    # Fixed by something that says only configChanged: S65.
    path.write_text(json.dumps(stick_doc()), encoding="utf-8")
    model._refresh_inplace()
    card = model.cardMap("pjoy_pro")
    assert card["damaged"] == ""
    assert card["status"] == "Connected"


def test_a_settings_change_gives_the_same_status_and_counts_as_a_reload(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_cards(folder)
    monkeypatch.setattr(output, "vjoy_in_use_elsewhere", lambda vjoy_id: True)
    model = module_model.ModuleListModel()
    keys = ("status", "buttons", "axes", "hats", "damaged", "isModule")
    before = {
        slug: {k: model.cardMap(slug)[k] for k in keys}
        for slug in ("pjoy_pro", "keyboard", "osc", "vjoy_1", "xbox")
    }
    model._refresh_inplace()
    after = {slug: {k: model.cardMap(slug)[k] for k in keys} for slug in before}
    assert after == before
    assert after["vjoy_1"]["status"] == "In use by another program"


# --- GL-142: stacks keep cards that aren't showing --------------------------


def test_unstacking_another_card_keeps_a_hidden_card_in_its_stack(
    folder: Path,  # noqa: F811
) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.stackSelected("pjoy_pro", "keyboard,osc")
    model.ignoreSlug("osc")
    model.unstackSlug("keyboard")
    model.unignoreSlug("osc")
    # Q10: OSC was not showing, so it stays with pJoy Pro.
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro", "osc"]


def test_a_new_stack_keeps_a_hidden_card_in_its_old_stack(folder: Path) -> None:  # noqa: F811
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.stackSelected("pjoy_pro", "keyboard,osc")
    model.ignoreSlug("osc")
    model.stackSelected("vjoy_1", "xbox")
    model.unignoreSlug("osc")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro", "keyboard", "osc"]
    assert model.pileMembers("vjoy_1") == ["vjoy_1", "xbox"]


def test_unstack_all_and_reset_card_layout_still_clear_the_stack(
    folder: Path,  # noqa: F811
) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.stackSelected("pjoy_pro", "keyboard,osc")
    model.ignoreSlug("osc")
    model.unstackAll("pjoy_pro")
    model.unignoreSlug("osc")
    assert model.pileMembers("osc") == ["osc"]
    model.stackSelected("pjoy_pro", "keyboard")
    model.ignoreSlug("keyboard")
    # A card that isn't showing (a deleted device's) leaves its stack.
    model.clearCardSettings("keyboard")
    model.unignoreSlug("keyboard")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro"]


# --- GL-145: Keyboard and OSC by their built-in id only ---------------------


@pytest.mark.parametrize("name", ["Keyboard", "OSC", "keyboard"])
def test_a_stick_named_keyboard_or_osc_is_a_stick(name: str) -> None:
    setup = module_model.DriverInputModel()
    setup.loadDevice(str(_OTHER), name)
    assert not setup._is_keyboard() and not setup._is_osc()
    # A stick that isn't plugged in: its Save is refused (Keyboard and OSC
    # never are, S46).
    assert setup.saveBlockedReason().startswith("Plug in")
    before = setup.rowCount()
    setup._on_key(types.SimpleNamespace(is_pressed=True, identifier=(0x21, False)))
    assert setup.rowCount() == before
    setup.deleteLater()


def test_the_built_in_keyboard_and_osc_are_found_by_id() -> None:
    setup = module_model.DriverInputModel()
    setup.loadDevice(module_model.KEYBOARD_GUID, "Keyboard")
    assert setup._is_keyboard() and setup.rowCount() > 0
    setup.loadDevice(module_model.OSC_GUID, "OSC")
    assert setup._is_osc()
    setup.deleteLater()


# --- GL-146: Tools › Input Module Setup never picks the Logical Device ------


def test_first_input_card_is_not_the_logical_device(folder: Path) -> None:  # noqa: F811
    model = module_model.ModuleListModel()
    logical = module_model.ModuleRow()
    logical.slug, logical.name, logical.tab = "logical", "Logical Device", "logical"
    stick = module_model.ModuleRow()
    stick.slug, stick.name = "pjoy_pro", "pJoy Pro"
    model._rows = [logical, stick]
    assert model.firstCardMap("source")["slug"] == "pjoy_pro"


# --- GL-043 / GL-147: Home's Delete Device ----------------------------------


def _ask_delete(card: dict, running: bool) -> dict:
    """Runs StatusPage.qml's askDelete on stand-ins; what it did."""
    text = (_ROOT / "qml" / "StatusPage.qml").read_text(encoding="utf-8")
    script = (
        "var did = {preview: 0, explain: 0, done: 0};"
        f" var backend = {{ gremlinActive: {json.dumps(running)} }};"
        " var model = { deletePreview: function() { did.preview++;"
        " return JSON.stringify({name: 'pJoy Pro', canPack: true}) } };"
        " var _doneTitle = '', _doneMessage = '';"
        " var _explainDialog = { open: function() { did.explain++ } };"
        " var _doneDialog = { open: function() { did.done++ } };"
        " var _saveCopyBox = {}; var _deleteCard, _deleteName, _deleteCanPack,"
        " _deleteShared, _deleteForeign, _deleteListed, _deleteKeepModule,"
        " _deleteSaveCopy, _explainAdvance;"
        + _function_source(text, "askDelete")
        + f" askDelete({json.dumps(card)});"
        " did.title = _doneTitle; did.message = _doneMessage;"
    )
    engine = QtQml.QJSEngine()
    loaded = cast(QtQml.QJSValue, engine.evaluate(script))
    assert not loaded.isError(), loaded.toString()
    result = cast(QtQml.QJSValue, engine.evaluate("JSON.stringify(did)"))
    return json.loads(result.toString())


_STICK_CARD = {"rawName": "pJoy Pro", "guid": "x", "direction": "source"}


def test_delete_device_is_refused_on_home_while_running() -> None:
    did = _ask_delete(_STICK_CARD, running=True)
    # Q6: "Stop first"; nothing is asked or previewed.
    assert did["explain"] == 0 and did["preview"] == 0 and did["done"] == 1
    assert did["title"] == "Delete stopped"
    assert "Stop the profile first" in did["message"]


def test_delete_device_asks_first_when_stopped() -> None:
    did = _ask_delete(_STICK_CARD, running=False)
    assert did["explain"] == 1 and did["done"] == 0


def test_an_output_card_is_never_deleted_from_home() -> None:
    did = _ask_delete(dict(_STICK_CARD, direction="dest"), running=False)
    assert did["explain"] == 0 and did["preview"] == 0


# --- GL-143: Also claim when the output file can't be written ---------------


def test_also_claim_with_an_output_file_that_cant_be_written(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.auto_mapper import AutoMapper, AutoMapperOptions

    write_module(folder, "pjoy_pro", stick_doc())
    path = write_module(
        folder, "vjoy_1", vjoy_doc(claim={"buttons": [], "axes": [], "hats": []})
    )
    before = path.read_bytes()
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    real_write = module_file.write_bytes

    def refuse(target: Path, data: bytes) -> None:
        if Path(target).name == "vjoy_1.json":
            raise OSError("access denied")
        real_write(target, data)

    monkeypatch.setattr(module_file, "write_bytes", refuse)
    report = AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions(claim_outputs=True)
    )
    # Q15: skipped and listed "not claimed"; no actions, the file as it was.
    assert mapped(profile, stick_uid()) == set()
    assert "not claimed" in report
    assert path.read_bytes() == before


def test_merge_keeps_the_old_claim_when_the_write_fails(tmp_path: Path) -> None:
    dest = {"path": tmp_path / "vjoy_1.json", "claim": {"buttons": [7]}}
    with mock.patch.object(auto_map.store, "update_path", side_effect=OSError("no")):
        kept = auto_map.merge_claim_into_output(dest, {"buttons": [1, 2]})
    assert kept == {"buttons": [7]}
    assert dest["claim"] == {"buttons": [7]}
    with mock.patch.object(auto_map.store, "update_path", return_value=False):
        auto_map.merge_claim_into_output(dest, {"buttons": [1, 2]})
    assert dest["claim"] == {"buttons": [7]}


# --- GL-170: reading a vJoy value never opens the device --------------------


class _Held:
    def is_axis_valid(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> bool:
        return axis_id == 1

    def is_button_valid(self, index: int) -> bool:
        return index == 2

    def is_hat_valid(self, index: int) -> bool:
        return False

    def axis(self, axis_id: int) -> types.SimpleNamespace:
        return types.SimpleNamespace(value=0.5)

    def button(self, index: int) -> types.SimpleNamespace:
        return types.SimpleNamespace(is_pressed=True)


_CLAIM = {"buttons": [2], "axes": [1], "hats": [], "keys": [], "friendly": {}}


def test_reading_a_vjoy_value_never_opens_the_device() -> None:
    opener = mock.Mock(side_effect=AssertionError("a read opened the vJoy"))
    with (
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
        mock.patch.object(output, "_open_vjoy", opener),
        mock.patch.object(output, "_opened_vjoy", return_value=None),
    ):
        # 06 Q16: not held, so neutral; only writes open a device.
        assert output.vjoy_value(1, "axis", 1) == 0.0
        assert output.vjoy_value(1, "button", 2) is False
    opener.assert_not_called()


def test_reading_a_held_vjoy_gives_its_value() -> None:
    with (
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
        mock.patch.object(output, "_opened_vjoy", return_value=_Held()),
    ):
        assert output.vjoy_value(1, "axis", 1) == 0.5
        assert output.vjoy_value(1, "button", 2) is True
