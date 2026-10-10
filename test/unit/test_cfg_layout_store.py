# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Configuration layout in the device's module file (CF-Q1): groups and
order under "layout", names as the claim's friendly names (CF-Q8), and the
layout travelling with Device Pack, the Device Library (Copy, Restore,
Swap) and History. One shared list Appearance in program settings (CF-Q4)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import history, history_modules, library_copy, library_swap
from gremlin.modules import module_file, store
from gremlin.ui import device_pack, window_placement
from test.unit.test_device_library_LC_copy import (  # noqa: F401
    FakeLibrary,
    lib,
)
from test.unit.test_device_pack_import import (  # noqa: F401
    _import,
    _own_path,
    pack,
)

LAYOUT = {
    "groups": ["Weapons", "Flight"],
    "order": ["button:2", "button:1"],
    "group_of": {"button:2": "Weapons", "button:1": "Flight"},
}


def _doc(name: str) -> dict:
    return json.loads(_own_path(name).read_text(encoding="utf-8"))


# --- the store API ---------------------------------------------------------------


def test_normalize_drops_blanks_repeats_and_unknown_groups() -> None:
    raw = {
        "groups": ["A", " ", "A", "B"],
        "order": ["button:1", "button:1", ""],
        "group_of": {"button:1": "A", "button:2": "Gone"},
    }
    assert store.normalize_layout(raw) == {
        "groups": ["A", "B"],
        "order": ["button:1"],
        "group_of": {"button:1": "A"},
    }
    assert store.normalize_layout(None) == store.empty_layout()
    assert store.input_key("axis", 3) == "axis:3"


def test_layout_and_names_are_written_to_the_module_file(pack: dict) -> None:  # noqa: F811
    name, guid = pack["name"], str(pack["uid"])
    assert store.write_layout(guid, LAYOUT, name)
    assert store.read_layout(guid, name) == LAYOUT
    assert _doc(name)["layout"] == LAYOUT
    # Rename writes the friendly name Module Setup edits: no second name.
    assert store.set_friendly_name(guid, "button:1", " Trigger ", name)
    assert store.friendly_name(guid, "button:1", name) == "Trigger"
    assert _doc(name)["claim"]["friendly"]["button:1"] == "Trigger"
    assert "names" not in _doc(name)["layout"]
    # Layout and names in one write; a blank name removes it.
    moved = dict(LAYOUT, order=["button:1", "button:2"])
    assert store.write_layout(
        guid, moved, name, names={"button:1": "", "button:2": "Pinkie"}
    )
    doc = _doc(name)
    assert doc["layout"]["order"] == ["button:1", "button:2"]
    assert doc["claim"]["friendly"] == {"button:2": "Pinkie"}
    # Nothing changed: nothing written.
    assert store.write_layout(guid, moved, name) is False
    # An empty layout removes the key.
    assert store.write_layout(guid, store.empty_layout(), name)
    assert "layout" not in _doc(name)
    assert store.read_layout(guid, name) == store.empty_layout()


def test_no_module_file_is_never_created(pack: dict) -> None:  # noqa: F811
    path = _own_path(pack["name"])
    path.unlink()
    assert store.write_layout(str(pack["uid"]), LAYOUT, pack["name"]) is False
    assert not path.exists()
    assert store.read_layout(str(pack["uid"]), pack["name"]) == store.empty_layout()


def test_a_damaged_module_file_is_not_written(
    pack: dict,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _own_path(pack["name"])
    path.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(module_file, "report_refused", lambda error: None)
    assert store.write_layout(str(pack["uid"]), LAYOUT, pack["name"]) is False
    assert path.read_text(encoding="utf-8") == "{ not json"


# --- History -----------------------------------------------------------------------


def test_history_names_a_layout_save(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    written: list[tuple] = []
    monkeypatch.setattr(
        history, "write_now", lambda area, title, *a, **k: written.append((area, title))
    )
    monkeypatch.setattr(history_modules, "_keep_pictures", lambda doc: [])
    old = {"device": "pJoy Pro", "claim": {"buttons": [1]}}
    new = dict(old, layout=LAYOUT)
    history_modules._record(
        tmp_path / "pjoy_pro.json", json.dumps(old), json.dumps(new), "save"
    )
    assert written == [("modules", "Saved pJoy Pro: Configuration layout")]
    assert "catalog" not in history_modules._WORDS


# --- Device Pack ---------------------------------------------------------------------


def test_device_pack_carries_the_layout(pack: dict) -> None:  # noqa: F811
    name = pack["name"]
    described = device_pack.describe_zip(pack["zip"])
    titles = {
        section["title"]: [item["title"] for item in section["items"]]
        for section in described["sections"]
    }
    assert "Configuration layout" in titles["Input module"]
    assert "Configuration Appearance" not in titles["Input module"]
    doc = _doc(name)
    doc["layout"] = {"groups": ["Mine"]}
    module_file.write_json(_own_path(name), doc)
    assert _import(pack, ["in.groups"])["ok"]
    assert _doc(name)["layout"]["groups"] == ["G40"]


def test_a_pack_catalog_is_not_imported(pack: dict) -> None:  # noqa: F811
    merged, _notes = device_pack._merge_module(
        {"kind": "control.hardware"},
        {"catalog": {"rowHeight": 40}, "layout": LAYOUT, "nodes": []},
        {"in.catalog", "in.groups"},
        "in.",
        pack["name"],
        "",
    )
    assert "catalog" not in merged
    assert merged["layout"] == LAYOUT
    assert "Configuration layout" in device_pack.module_text(
        {"layout": LAYOUT}, ["layout"]
    )


# --- Device Library ----------------------------------------------------------------


def test_library_copy_puts_the_layout_back(lib: dict) -> None:  # noqa: F811
    name, guid, fake = lib["name"], lib["guid"], lib["fake"]
    doc = _doc(name)
    doc["layout"] = LAYOUT
    module_file.write_json(_own_path(name), doc)
    built = device_pack.assemble(name, lambda stored: None, None, None)
    assert not isinstance(built, str), built
    setup = fake.add(name, guid, built[0], list(library.PARTS), [])
    doc["layout"] = {"groups": ["Changed"]}
    module_file.write_json(_own_path(name), doc)
    result = library_copy.copy(setup["key"], name, guid, ["setup"], [], [])
    assert result["ok"], result
    assert _doc(name)["layout"] == LAYOUT


def test_library_restore_puts_the_layout_back(lib: dict) -> None:  # noqa: F811
    name, guid, fake = lib["name"], lib["guid"], lib["fake"]
    doc = _doc(name)
    doc["layout"] = LAYOUT
    module_file.write_json(_own_path(name), doc)
    saved = fake.autosave(name, guid, "test", "Autosave", [])["setups"][0]
    doc["layout"] = {"groups": ["Changed"]}
    module_file.write_json(_own_path(name), doc)
    result = library_copy.restore(saved["key"])
    assert result["ok"], result
    assert _doc(name)["layout"] == LAYOUT


def test_a_saved_setup_holding_only_a_layout_holds_setup() -> None:
    held = library._contents({"map": {"layout": LAYOUT}, "wires": {}})[0]
    assert "setup" in held
    held = library._contents({"map": {"catalog": {"rowHeight": 4}}, "wires": {}})[0]
    assert "appearance" not in held


def test_swap_exchanges_the_layout_with_the_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    left_layout = copy.deepcopy(LAYOUT)
    paths = {"L": tmp_path / "left.json", "R": tmp_path / "right.json"}
    paths["L"].write_text(
        json.dumps({"layout": left_layout, "view": {"a": 1}}), "utf-8"
    )
    paths["R"].write_text(json.dumps({"catalog": {"rows": 2}}), "utf-8")
    monkeypatch.setattr(store, "path_for_id", lambda name, guid: paths[name])
    monkeypatch.setattr(store, "damage_of", lambda path: "")
    monkeypatch.setattr(
        store, "read_path", lambda path: json.loads(Path(path).read_text("utf-8"))
    )
    shared = {"button": set(), "axis": set(), "hat": set()}
    _a, _b, left, right, _files = library_swap._swapped_docs(
        ("L", ""), ("R", ""), ["setup"], shared
    )
    assert "layout" not in left and right["layout"] == left_layout
    # Appearance is the Output View only: no "catalog" moves.
    _a, _b, left, right, _files = library_swap._swapped_docs(
        ("L", ""), ("R", ""), ["appearance"], shared
    )
    assert "catalog" not in left and right["view"] == {"a": 1}


# --- the shared Appearance (CF-Q4) ---------------------------------------------------


def test_one_list_appearance_in_program_settings() -> None:
    placement = window_placement.WindowPlacement()
    seen: list[bool] = []
    placement.listAppearanceChanged.connect(lambda: seen.append(True))
    try:
        placement.setListAppearance(json.dumps({"rowHeight": 30, "showLeds": False}))
        assert json.loads(placement.listAppearance()) == {
            "rowHeight": 30,
            "showLeds": False,
        }
        assert window_placement.list_appearance() == {
            "rowHeight": 30,
            "showLeds": False,
        }
        assert seen == [True]
        placement.setListAppearance("[1, 2]")  # not an object: ignored
        placement.setListAppearance("not json")
        assert window_placement.list_appearance() == {
            "rowHeight": 30,
            "showLeds": False,
        }
        assert seen == [True]
    finally:
        placement.setListAppearance("{}")
    assert placement.listAppearance() == "{}"
