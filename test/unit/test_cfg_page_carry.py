# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Configuration page's layout travels (05 S122, S129; batch C).

The page holds its groups, order and Rename names as an unsaved change
(store.set_pending_layout, CS1 a) until File > Save writes them into the
stick's input module file (the "layout" key and the claim's friendly
names, in one write). From there they must come back through every path
that carries a module file:

- Save to Device Library, then Restore (and Copy, part "setup");
- Export Current Setup / Export Saved Setup, then Import into the Library
  and Restore;
- Swap with Another Stick (part "setup");
- History restore of the layout save;
- a Device Pack import of "Configuration layout" (in.groups), Undo Import.

After each put-back the page shows it: store.layout_for and
store.friendly_name_for (what the page reads) give the restored layout and
names, with nothing left held as unsaved.

The real Library store (temp folder), Device Pack, History (temp folder)
and Profile; the fake pJoy Pro stick (conftest).
"""

# The fixtures lib / sticks come from other test modules.
# ruff: noqa: F811

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import history, history_modules, library_copy, library_swap
from gremlin.modules import module_file, store
from gremlin.ui import device_pack, history_model
from test.unit import (  # pyright: ignore[reportMissingImports]
    test_device_library_LC_copy as _lc,
)
from test.unit.test_device_library_LC_copy import (  # pyright: ignore[reportMissingImports]
    _REAL,
    _own_path,
)
from test.unit.test_device_library_LW_swap import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    LEFT,
    LEFT_ID,
    RIGHT,
    RIGHT_ID,
    sticks,
)
from test.unit.test_stage1_modules import (  # pyright: ignore[reportMissingImports]
    settle_history,
)

pytestmark = pytest.mark.validate_off

lib = _lc.lib  # the LC fixture

LAYOUT_A = {
    "groups": ["Weapons", "Flight"],
    "order": ["button:2", "button:1", "button:3"],
    "group_of": {"button:2": "Weapons", "button:1": "Flight"},
}
NAMES_A = {"button:1": "Trigger", "button:2": "Pinkie"}
LAYOUT_B = {"groups": ["Other"], "order": ["button:3"], "group_of": {}}
NAMES_B = {"button:1": "", "button:2": "Thumb"}


@pytest.fixture(autouse=True)
def _no_held_layouts() -> Iterator[None]:
    store.discard_pending()
    yield
    store.discard_pending()


def _module(name: str) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "claim": {
            "buttons": [1, 2, 3],
            "axes": [1],
            "hats": [],
            "keys": [],
            "friendly": {},
        },
        "nodes": [],
    }


def _doc(name: str) -> dict:
    return json.loads(_own_path(name).read_text(encoding="utf-8"))


def _page_edit(cfg: dict, layout: dict, names: dict) -> None:
    """What the page does on group/move/reorder/Rename: held until Save."""
    store.set_pending_layout(cfg["guid"], layout, names, cfg["name"])


def _file_save(cfg: dict) -> None:
    """File > Save Profile on the open (bound) profile."""
    cfg["profile"].to_xml(cfg["path"])
    cfg["profile"].mark_clean()


def _assert_page_shows(cfg: dict, layout: dict, names: dict) -> None:
    guid, name = cfg["guid"], cfg["name"]
    assert store.pending_layout(guid) is None
    assert store.layout_for(guid, name) == store.normalize_layout(layout)
    for key, text in names.items():
        assert store.friendly_name_for(guid, key, name) == text, key


def _assert_file(cfg: dict, layout: dict, names: dict) -> None:
    doc = _doc(cfg["name"])
    assert doc.get("layout") == store.normalize_layout(layout), doc
    friendly = doc["claim"].get("friendly") or {}
    for key, text in names.items():
        assert friendly.get(key, "") == text, (key, friendly)


@pytest.fixture
def cfg(lib: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    """The stick with layout A saved from the page (File > Save), the real
    Library store and a History folder of its own."""
    for name, fn in _REAL.items():
        monkeypatch.setattr(library, name, fn)
    monkeypatch.setattr(library, "folder", lambda: lib["tmp"] / "device library")
    settle_history()
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(history_modules, "_last_pictures", {})
    name = lib["name"]
    module_file.write_json(_own_path(name), _module(name))
    cfg = dict(lib, path=lib["tmp"] / "mine.xml")
    cfg["profile"].fpath = cfg["path"]
    settle_history()
    cfg["entries_before"] = {str(e.get("id")) for e in history.entries()}
    _page_edit(cfg, LAYOUT_A, NAMES_A)
    assert store.has_pending()
    _file_save(cfg)
    return cfg


def _change_to_b(cfg: dict) -> None:
    _page_edit(cfg, LAYOUT_B, NAMES_B)
    _file_save(cfg)
    _assert_file(cfg, LAYOUT_B, NAMES_B)


def _save_setup(cfg: dict) -> dict:
    out = library.save_setup(cfg["name"], cfg["guid"], [cfg["path"]])
    assert out["ok"], out
    return out.get("setup") or out["setups"][0]


def _module_doc_in(path: Path) -> dict:
    """The stick's module file inside a pack."""
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            try:
                doc = json.loads(zf.read(name).decode("utf-8-sig"))
            except ValueError:
                continue
            if isinstance(doc, dict) and doc.get("kind") == "control.hardware":
                return doc
    return {}


# --- File > Save: the start of every path -------------------------------------


def test_file_save_writes_layout_and_names_in_one_entry(cfg: dict) -> None:
    _assert_file(cfg, LAYOUT_A, NAMES_A)
    _assert_page_shows(cfg, LAYOUT_A, NAMES_A)
    assert not store.has_pending()
    settle_history()
    saves = [
        e
        for e in history.entries()
        if str(e.get("id")) not in cfg["entries_before"]
        and (e.get("subject") or {}).get("fileName") == _own_path(cfg["name"]).name
    ]
    assert len(saves) == 1, saves
    assert "Configuration layout" in str(saves[0].get("title", "")), saves[0]
    # Nothing of the layout goes into the profile.
    assert "Weapons" not in cfg["path"].read_text(encoding="utf-8-sig")


# --- Device Library: Save + Restore, Copy ----------------------------------------


@pytest.mark.parametrize("how", ["restore_to_stick", "copy"])
def test_library_save_and_put_back_brings_the_layout_back(cfg: dict, how: str) -> None:
    setup = _save_setup(cfg)
    _change_to_b(cfg)
    if how == "copy":
        out = library_copy.copy(
            setup["key"], cfg["name"], cfg["guid"], ["setup"], [], []
        )
    else:
        out = library_copy.restore_to_stick(setup["key"])
    assert out["ok"], out
    _assert_file(cfg, LAYOUT_A, NAMES_A)
    _assert_page_shows(cfg, LAYOUT_A, NAMES_A)


# --- Export / Import ------------------------------------------------------------


def _device_key(cfg: dict) -> str:
    row = library.find_device(cfg["name"], cfg["guid"])
    assert row, "the stick is not in the Library"
    return row["key"]


@pytest.mark.parametrize("which", ["current", "saved"])
def test_export_then_import_and_restore_brings_the_layout_back(
    cfg: dict, which: str, tmp_path: Path
) -> None:
    setup = _save_setup(cfg)
    dest = tmp_path / "out" / f"{which}.zip"
    dest.parent.mkdir()
    if which == "current":
        out = library.export_current(_device_key(cfg), dest)
    else:
        out = library.export_setup(setup["key"], dest)
    assert out["ok"], out
    doc = _module_doc_in(dest)
    assert doc.get("layout") == LAYOUT_A, doc
    assert doc["claim"]["friendly"] == NAMES_A
    _change_to_b(cfg)
    imported = library.import_pack(dest)
    assert imported["ok"], imported
    out = library_copy.restore_to_stick(imported["setup"]["key"])
    assert out["ok"], out
    _assert_file(cfg, LAYOUT_A, NAMES_A)
    _assert_page_shows(cfg, LAYOUT_A, NAMES_A)


# --- Swap with Another Stick ---------------------------------------------------------


def test_swap_moves_the_page_saved_layout_with_the_setup(sticks: dict) -> None:
    store.set_pending_layout(LEFT_ID, LAYOUT_A, {"button:1": "Trigger"}, LEFT[0])
    assert store.save_pending() == 1
    right_before = store.read_layout(RIGHT_ID, RIGHT[0])
    result = library_swap.swap(LEFT, RIGHT, ["setup"], [])
    assert result["ok"] is True, result
    assert store.layout_for(RIGHT_ID, RIGHT[0]) == LAYOUT_A
    assert store.layout_for(LEFT_ID, LEFT[0]) == right_before
    assert store.friendly_name_for(RIGHT_ID, "button:1", RIGHT[0]) == "Trigger"
    assert not store.has_pending()


# --- History restore ---------------------------------------------------------------


def test_history_restore_of_a_layout_save_puts_it_back(cfg: dict) -> None:
    settle_history()
    before = {str(e.get("id")) for e in history.entries()}
    _change_to_b(cfg)
    settle_history()
    file_name = _own_path(cfg["name"]).name
    entries = [
        e
        for e in history.entries()
        if str(e.get("id")) not in before
        and (e.get("subject") or {}).get("fileName") == file_name
    ]
    assert len(entries) == 1, entries  # one save: one entry
    assert "Configuration layout" in str(entries[0].get("title", "")), entries[0]
    out = history_model.restore(str(entries[0]["id"]), "before")
    assert out["ok"], out
    _assert_file(cfg, LAYOUT_A, NAMES_A)
    _assert_page_shows(cfg, LAYOUT_A, NAMES_A)


# --- Device Pack ----------------------------------------------------------------


def test_device_pack_import_of_in_groups_and_undo(cfg: dict, tmp_path: Path) -> None:
    built = device_pack.assemble(cfg["name"], lambda stored: None, None, None)
    assert not isinstance(built, str), built
    path = tmp_path / "pack.zip"
    path.write_bytes(built[0])
    ids = device_pack.pack_item_ids(path)
    assert not isinstance(ids, str), ids
    assert "in.groups" in ids["input"], ids
    _change_to_b(cfg)
    result = device_pack.apply_zip(
        path, cfg["name"], {"items": ["in.groups", "in.names"]}
    )
    assert result["ok"], result
    _assert_file(cfg, LAYOUT_A, NAMES_A)
    _assert_page_shows(cfg, LAYOUT_A, NAMES_A)
    assert device_pack.undo_import()["ok"]
    _assert_file(cfg, LAYOUT_B, {"button:2": "Thumb"})
    _assert_page_shows(cfg, LAYOUT_B, {"button:2": "Thumb"})
    device_pack.drop_import_undo()


def test_device_pack_without_in_groups_leaves_the_layout(
    cfg: dict, tmp_path: Path
) -> None:
    built = device_pack.assemble(cfg["name"], lambda stored: None, None, None)
    assert not isinstance(built, str), built
    path = tmp_path / "pack.zip"
    path.write_bytes(built[0])
    _change_to_b(cfg)
    result = device_pack.apply_zip(path, cfg["name"], {"items": ["in.checks"]})
    assert result["ok"], result
    assert _doc(cfg["name"]).get("layout") == LAYOUT_B
    device_pack.drop_import_undo()
