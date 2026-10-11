# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Keyboard and OSC pages' layouts travel (05 S122, S129; AUD-FILES-11,
AUD-FILES-12).

Both pages keep their groups, order and Rename names in the device's own
module file (Keyboard/module.json: "layout" + "key:<id>" names;
OSC/module.json: "layout" + "osc:<uid>" names). Like the Configuration
page's (test_cfg_page_carry), they must come back through every path that
carries a module file: Device Library save + Restore, Export Current /
Export Saved Setup, History restore and a Device Pack import (with Undo
Import). Swap and Copy are not offered for built-in inputs (10 S6), so they
are not here.

The real Library store, Device Pack and History (temp folders, via the
stage-1 `folder` fixture); OSC's shared rows (test_osc_carry fixtures).
"""

# The fixtures come from other test modules.
# ruff: noqa: F811

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import history, library_copy, osc_device_file, shared_state
from gremlin.modules import store
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.profile import Profile
from gremlin.ui import device_pack, history_model
from gremlin.ui.keyboard_layout import DEVICE_NAME as KB_NAME
from gremlin.ui.keyboard_layout import GUID_TEXT as KB_GUID
from test.unit._device_folders import put_module
from test.unit.test_osc_carry import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    _app,
    _change_to_b,
    _osc_doc_in,
    _save,
    folder,
    modules,
    rows,
    state_a,
)
from test.unit.test_stage1_modules import (  # pyright: ignore[reportMissingImports]
    settle_history,
)

pytestmark = pytest.mark.validate_off


@pytest.fixture(autouse=True)
def _no_held_layouts() -> Iterator[None]:
    store.discard_pending()
    yield
    store.discard_pending()


def _doc_in(path: Path) -> dict:
    """The module file in a zip (module.json in a .gmap export, map.json in
    an old saved setup's pack)."""
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


def _new_entries(before: set[str], file_name: str) -> list[dict]:
    settle_history()
    return [
        e
        for e in history.entries()
        if str(e.get("id")) not in before
        and (e.get("subject") or {}).get("fileName") == file_name
    ]


def _entry_ids() -> set[str]:
    settle_history()
    return {str(e.get("id")) for e in history.entries()}


# --- Keyboard -----------------------------------------------------------------

KB_LAYOUT_A = {
    "groups": ["Flight", "Comms"],
    "order": ["key:31", "key:30"],
    "group_of": {"key:30": "Flight", "key:31": "Comms"},
}
KB_NAMES_A = {"key:30": "Fire", "key:31": "Talk"}
KB_LAYOUT_B = {"groups": ["Other"], "order": ["key:30"], "group_of": {}}
KB_NAMES_B = {"key:30": "", "key:31": "Radio"}


def _kb_path() -> Path:
    return Path(store.module_file(KB_NAME, KB_GUID))


def _file_name(path: Path) -> str:
    """How History names a module file: "<folder>/module.json"."""
    return f"{path.parent.name}/{path.name}"


def _kb_doc() -> dict:
    return json.loads(_kb_path().read_text(encoding="utf-8-sig"))


def _kb_page_save(layout: dict, names: dict) -> None:
    """What the Keyboard page does (held), then File > Save."""
    store.set_pending_layout(KB_GUID, layout, names, KB_NAME)
    assert store.save_pending() == 1


def _kb_assert(layout: dict, names: dict, doc: dict | None = None) -> None:
    doc = _kb_doc() if doc is None else doc
    assert doc.get("layout") == store.normalize_layout(layout), doc
    friendly = (doc.get("claim") or {}).get("friendly") or {}
    for key, text in names.items():
        assert friendly.get(key, "") == text, (key, friendly)


def _kb_page_shows(layout: dict, names: dict) -> None:
    assert store.pending_layout(KB_GUID) is None
    assert store.layout_for(KB_GUID, KB_NAME) == store.normalize_layout(layout)
    for key, text in names.items():
        assert store.friendly_name_for(KB_GUID, key, KB_NAME) == text, key


@pytest.fixture
def kb(modules: Path) -> dict:
    """The Keyboard's module file with layout A saved from its page."""
    path = put_module(
        modules,
        KB_NAME,
        {
            "kind": "control.hardware",
            "device": KB_NAME,
            "direction": "source",
            "claim": {"buttons": [], "axes": [], "hats": [], "keys": []},
            "nodes": [],
        },
        KB_GUID,
    )
    assert _kb_path().resolve() == path.resolve()
    _kb_page_save(KB_LAYOUT_A, KB_NAMES_A)
    _kb_assert(KB_LAYOUT_A, KB_NAMES_A)
    return {"path": path}


def _kb_setup() -> dict:
    out = library.save_setup(KB_NAME, KB_GUID, [])
    assert out["ok"], out
    return out.get("setup") or out["setups"][0]


def _kb_row() -> dict:
    return next(r for r in library.devices() if r["name"] == KB_NAME)


# Library Restore, Import + Restore and a Device Pack all put the module file
# back through device_pack.apply_zip: its "in.groups" part carries the layout
# and its "in.names" part the Keyboard's "key:<id>" names (S129).


def _kb_after_b_by(how: str, tmp_path: Path, no_profile: Profile) -> None:
    """Saved A, changed to B, then A put back by how."""
    if how == "device_pack":
        built = device_pack.assemble(
            KB_NAME, lambda stored: None, None, {}, no_profile, KB_GUID
        )
        assert not isinstance(built, str), built
        path = tmp_path / "kb.zip"
        path.write_bytes(built[0])
        ids = device_pack.pack_item_ids(path)
        assert not isinstance(ids, str), ids
        assert "in.groups" in ids["input"], ids
        _kb_page_save(KB_LAYOUT_B, KB_NAMES_B)
        out = device_pack.apply_zip(
            path, KB_NAME, {"items": ids["input"]}, target_guid=KB_GUID
        )
    elif how == "import_restore":
        setup = _kb_setup()
        _kb_page_save(KB_LAYOUT_B, KB_NAMES_B)  # the saved setup keeps A
        dest = tmp_path / "out" / "saved.gmap"
        out = library.export_setup(setup["key"], dest)
        assert out["ok"], out
        _kb_assert(KB_LAYOUT_A, KB_NAMES_A, _doc_in(dest))
        imported = library.import_pack(dest)
        assert imported["ok"], imported
        out = library_copy.restore_to_stick(imported["setup"]["key"])
    else:
        setup = _kb_setup()
        _kb_page_save(KB_LAYOUT_B, KB_NAMES_B)
        out = getattr(library_copy, how)(setup["key"])
    assert out["ok"], out


@pytest.fixture
def no_profile() -> Iterator[Profile]:
    old = shared_state.current_profile
    made = Profile()
    shared_state.current_profile = made
    yield made
    device_pack.drop_import_undo()
    shared_state.current_profile = old


_PUT_BACK = ["restore_to_stick", "restore", "import_restore", "device_pack"]


@pytest.mark.parametrize("how", _PUT_BACK)
def test_keyboard_layout_comes_back(
    kb: dict, how: str, tmp_path: Path, no_profile: Profile
) -> None:
    _kb_after_b_by(how, tmp_path, no_profile)
    _kb_assert(KB_LAYOUT_A, {})
    _kb_page_shows(KB_LAYOUT_A, {})


@pytest.mark.parametrize("how", _PUT_BACK)
def test_keyboard_names_come_back(
    kb: dict, how: str, tmp_path: Path, no_profile: Profile
) -> None:
    _kb_after_b_by(how, tmp_path, no_profile)
    _kb_assert(KB_LAYOUT_A, KB_NAMES_A)
    _kb_page_shows(KB_LAYOUT_A, KB_NAMES_A)


def test_keyboard_device_pack_undo_puts_b_back(
    kb: dict, tmp_path: Path, no_profile: Profile
) -> None:
    _kb_after_b_by("device_pack", tmp_path, no_profile)
    assert device_pack.undo_import()["ok"]
    _kb_assert(KB_LAYOUT_B, {"key:31": "Radio"})
    _kb_page_shows(KB_LAYOUT_B, {"key:31": "Radio"})


def test_keyboard_export_current_carries_layout_and_names(
    kb: dict, tmp_path: Path
) -> None:
    dest = tmp_path / "out" / "now.gmap"
    out = library.export_current(_kb_row()["key"], dest)
    assert out["ok"], out
    _kb_assert(KB_LAYOUT_A, KB_NAMES_A, _doc_in(dest))


def test_keyboard_history_restore_of_a_layout_save(kb: dict) -> None:
    before = _entry_ids()
    _kb_page_save(KB_LAYOUT_B, KB_NAMES_B)
    entries = _new_entries(before, _file_name(_kb_path()))
    assert len(entries) == 1, entries  # one save: one entry
    out = history_model.restore(str(entries[0]["id"]), "before")
    assert out["ok"], out
    _kb_assert(KB_LAYOUT_A, KB_NAMES_A)
    _kb_page_shows(KB_LAYOUT_A, KB_NAMES_A)


# --- OSC ----------------------------------------------------------------------


def _osc_layout(state: dict, groups: list[str]) -> dict:
    fire, throttle = f"osc:{state['fire']}", f"osc:{state['throttle']}"
    return store.normalize_layout(
        {
            "groups": groups,
            "order": [throttle, fire],
            "group_of": {fire: groups[0]},
        }
    )


def _osc_page_save(rows: object, layout: dict) -> None:
    """What the OSC page does (held on OSC's rows), then File > Save."""
    names = dict(rows.names)  # type: ignore[attr-defined]
    rows.set_layout(layout, names)  # type: ignore[attr-defined]
    assert osc_device_file.save()


def _osc_file_layout(doc: dict | None = None) -> dict:
    if doc is None:
        path = osc_device_file.path()
        assert path is not None
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc is not None
    return store.normalize_layout(doc.get("layout"))


@pytest.fixture
def osc_a(state_a: dict, rows: object) -> dict:
    """OSC saved with layout A (two groups, /throttle first)."""
    layout = _osc_layout(state_a, ["Weapons", "Engines"])
    _osc_page_save(rows, layout)
    assert _osc_file_layout() == layout
    return {**state_a, "layout": layout}


def _osc_to_b(rows: object, state: dict) -> dict:
    """Rows, server and names changed (test_osc_carry's B), and the layout
    moved to B."""
    _change_to_b(rows)
    layout_b = store.normalize_layout(
        {"groups": ["Other"], "order": [f"osc:{state['fire']}"], "group_of": {}}
    )
    _osc_page_save(rows, layout_b)
    assert _osc_file_layout() == layout_b
    return layout_b


def _osc_page_shows(layout: dict) -> None:
    assert _osc_file_layout() == layout
    shared = OscDevice().rows
    assert store.normalize_layout(shared.layout) == layout
    assert not shared.dirty


@pytest.mark.parametrize("how", ["restore_to_stick", "restore"])
def test_osc_library_restore_brings_the_layout_back(
    osc_a: dict, rows: object, how: str
) -> None:
    setup = _save()
    _osc_to_b(rows, osc_a)
    out = getattr(library_copy, how)(setup["key"])
    assert out["ok"], out
    _osc_page_shows(osc_a["layout"])


def test_osc_export_current_and_saved_carry_the_layout(
    osc_a: dict, rows: object, tmp_path: Path
) -> None:
    row = next(r for r in library.devices() if r["name"] == "OSC")
    now = tmp_path / "out" / "now.gmap"
    assert library.export_current(row["key"], now)["ok"]
    assert _osc_file_layout(_osc_doc_in(now)) == osc_a["layout"]
    setup = _save()
    _osc_to_b(rows, osc_a)  # the saved setup keeps A
    saved = tmp_path / "out" / "saved.gmap"
    assert library.export_setup(setup["key"], saved)["ok"]
    assert _osc_file_layout(_osc_doc_in(saved)) == osc_a["layout"]


def test_osc_history_restore_brings_the_layout_back(osc_a: dict, rows: object) -> None:
    before = _entry_ids()
    layout_b = store.normalize_layout(
        {"groups": ["Other"], "order": [], "group_of": {}}
    )
    _osc_page_save(rows, layout_b)
    path = osc_device_file.path()
    assert path is not None
    entries = _new_entries(before, _file_name(Path(path)))
    assert len(entries) == 1, entries
    out = history_model.restore(str(entries[0]["id"]), "before")
    assert out["ok"], out
    _osc_page_shows(osc_a["layout"])


@pytest.fixture
def osc_profile() -> Iterator[Profile]:
    from gremlin.profile import DeviceInfo

    old = shared_state.current_profile
    made = Profile()
    made.device_database.devices[OSC_DEVICE_UUID] = DeviceInfo(OSC_DEVICE_UUID, "OSC")
    shared_state.current_profile = made
    yield made
    device_pack.drop_import_undo()
    shared_state.current_profile = old


def test_osc_device_pack_carries_the_layout_and_undo_reverts(
    osc_a: dict, rows: object, osc_profile: Profile, tmp_path: Path
) -> None:
    built = device_pack.assemble(
        "OSC", lambda stored: None, None, {}, osc_profile, str(OSC_DEVICE_UUID)
    )
    assert not isinstance(built, str), built
    path = tmp_path / "osc.zip"
    path.write_bytes(built[0])
    assert _osc_file_layout(_osc_doc_in(path)) == osc_a["layout"]
    ids = device_pack.pack_item_ids(path)
    assert not isinstance(ids, str), ids
    assert "in.groups" in ids["input"], ids  # the page's layout, offered
    layout_b = _osc_to_b(rows, osc_a)
    result = device_pack.apply_zip(
        path,
        "OSC",
        {"items": ["in.osc", "in.groups"]},
        target_guid=str(OSC_DEVICE_UUID),
    )
    assert result["ok"], result
    _osc_page_shows(osc_a["layout"])
    assert device_pack.undo_import()["ok"]
    _osc_page_shows(layout_b)
