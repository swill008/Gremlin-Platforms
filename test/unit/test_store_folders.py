# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""One folder per device (D-03-DEVICE-FOLDERS): folder names, lookup by
id, pictures, an edit's temporary folder, rename and delete. Every test
works in a tmp modules folder."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin.modules import store

STICK_A = "1111AAAA2222BBBB3333CCCC4444DDDD"
STICK_B = "5555EEEE6666FFFF7777AAAA8888BBBB"
NAME = "Folder Test Stick"


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    base = tmp_path / "modules"
    base.mkdir()
    monkeypatch.setattr(store, "folder", lambda: base)
    store._dirs_changed()
    yield base
    store._dirs_changed()


def _id_file(path: Path, key: str, name: str = NAME) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / store.ID_FILE).write_text(
        json.dumps({"format": 1, "id": key, "name": name}), encoding="utf-8"
    )
    store._dirs_changed()


def _module(path: Path, doc: dict) -> None:
    (path / store.MODULE_FILE).write_text(json.dumps(doc), encoding="utf-8")


def _picture(path: Path, name: str, data: bytes = b"png") -> Path:
    found = path / store.PICTURES / name
    found.parent.mkdir(parents=True, exist_ok=True)
    found.write_bytes(data)
    return found


# --- folder names ----------------------------------------------------------------


def test_folder_name_replaces_unsafe_characters() -> None:
    assert store.folder_name_for('A/B\\C:D*E?F"G<H>I|J') == "A_B_C_D_E_F_G_H_I_J"
    assert store.folder_name_for("  Two   spaces  ") == "Two spaces"
    assert store.folder_name_for("Ends with dot.") == "Ends with dot_"
    assert store.folder_name_for("ctrl\x01char") == "ctrl_char"
    assert store.folder_name_for("") == "Device"


def test_folder_name_is_cut_to_80_characters() -> None:
    assert len(store.folder_name_for("x" * 200)) == 80
    numbered = store._numbered("y" * 80, 2)
    assert len(numbered) == 80 and numbered.endswith(" (2)")


@pytest.mark.parametrize("name", ["CON", "nul", "COM1", "lpt9", "cache", "Templates"])
def test_reserved_names_get_a_trailing_underscore(name: str) -> None:
    assert store.folder_name_for(name) == name + "_"


def test_same_name_other_id_gets_a_number(modules: Path) -> None:
    _id_file(modules / NAME, STICK_A)
    found = store.device_dir(NAME, STICK_B)
    assert found == modules / f"{NAME} (2)"
    made = store.ensure_device_dir(NAME, STICK_B)
    assert made == found and made.is_dir()
    assert json.loads((made / store.ID_FILE).read_text())["id"] == STICK_B
    # Both found by id afterwards; the first keeps its name.
    assert store.device_dir(NAME, STICK_A) == modules / NAME
    assert store.device_dir(NAME, STICK_B) == modules / f"{NAME} (2)"


def test_lowest_id_gets_the_plain_name(modules: Path) -> None:
    names = store.names_for_new([(STICK_B, NAME), (STICK_A, NAME)])
    assert names == {STICK_A: NAME, STICK_B: f"{NAME} (2)"}
    _id_file(modules / NAME, "9999")
    later = store.names_for_new([(STICK_A, NAME)])
    assert later == {STICK_A: f"{NAME} (2)"}


# --- lookup ----------------------------------------------------------------------


def test_lookup_by_id_after_the_folder_was_renamed(modules: Path) -> None:
    made = store.ensure_device_dir(NAME, STICK_A)
    _module(made, {"device": NAME, "boundGuidLocal": STICK_A})
    made.rename(modules / "Renamed By Hand")
    assert store.device_dir(NAME, STICK_A) == modules / "Renamed By Hand"
    assert (
        store.module_file(NAME, STICK_A) == modules / "Renamed By Hand" / "module.json"
    )
    assert store.dir_of_id(STICK_A) == modules / "Renamed By Hand"


def test_id_from_module_file_when_device_json_is_missing(modules: Path) -> None:
    path = modules / "Somewhere"
    path.mkdir()
    _module(path, {"device": NAME, "boundGuidLocal": STICK_A})
    store._dirs_changed()
    assert store.device_dir(NAME, STICK_A) == path


def test_fallback_to_the_folder_named_after_the_device(modules: Path) -> None:
    path = modules / NAME
    path.mkdir()
    _module(path, {"device": NAME})
    store._dirs_changed()
    assert store.device_dir(NAME, STICK_A) == path
    # Not created by a lookup.
    assert not (modules / "Never Seen").exists()
    assert store.device_dir("Never Seen", STICK_B) == modules / "Never Seen"
    assert not (modules / "Never Seen").exists()


def test_module_files_leave_reserved_folders_out(modules: Path) -> None:
    for name in ("Stick", "cache", "templates"):
        (modules / name).mkdir()
        _module(modules / name, {"device": name})
    assert store.module_files() == [modules / "Stick" / "module.json"]


# --- rename ----------------------------------------------------------------------


def test_rename_moves_the_folder_and_keeps_the_id(modules: Path) -> None:
    made = store.ensure_device_dir(NAME, STICK_A)
    ok, reason = store.rename_device_dir(NAME, STICK_A, "My Pedals")
    assert (ok, reason) == (True, "")
    assert not made.exists()
    held = json.loads((modules / "My Pedals" / store.ID_FILE).read_text())
    assert held == {"format": 1, "id": STICK_A, "name": "My Pedals"}
    assert store.device_dir(NAME, STICK_A) == modules / "My Pedals"


def test_rename_refused_while_a_file_is_open(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made = store.ensure_device_dir(NAME, STICK_A)

    def refuse(src: object, dst: object) -> None:
        raise PermissionError(13, "The process cannot access the file")

    monkeypatch.setattr(store.os, "rename", refuse)
    ok, reason = store.rename_device_dir(NAME, STICK_A, "My Pedals")
    assert not ok
    assert reason == (
        f"The folder {NAME} could not be renamed to My Pedals: a file in it is "
        "open in another program (The process cannot access the file)."
    )
    assert made.is_dir() and not (modules / "My Pedals").exists()
    assert json.loads((made / store.ID_FILE).read_text())["name"] == NAME


def test_rename_without_a_folder_is_fine(modules: Path) -> None:
    assert store.rename_device_dir(NAME, STICK_A, "Other") == (True, "")
    assert not any(modules.iterdir())


# --- pictures --------------------------------------------------------------------


def test_picture_refs_are_relative_to_the_device_folder() -> None:
    assert store.picture_ref("photo.png") == "pictures/photo.png"
    assert store.normal_ref("old_slug/map.png") == "pictures/map.png"
    assert store.normal_ref("qml/maps/old_slug/map.png") == "pictures/map.png"
    assert store.normal_ref("library\\shot.jpg") == "pictures/shot.jpg"
    assert store.normal_ref("pictures/a.png") == "pictures/a.png"
    assert store.normal_ref("file:///C:/x/a.png") == "file:///C:/x/a.png"
    assert store.normal_ref("") == ""


def test_find_picture_never_uses_another_devices_file(modules: Path) -> None:
    mine = modules / "Mine"
    other = modules / "Other"
    _picture(other, "shot.png")
    assert store.find_picture(mine, "pictures/shot.png") is None
    _picture(mine, "shot.png", b"mine")
    assert store.find_picture(mine, "old/shot.png") == mine / "pictures" / "shot.png"
    staged = modules / "staged"
    staged.mkdir()
    (staged / "shot.png").write_bytes(b"staged")
    assert store.find_picture(mine, "pictures/shot.png", staged) == staged / "shot.png"


def test_named_refs_finds_photo_and_nested_chips() -> None:
    doc = {
        "image": "pictures/photo.png",
        "nodes": [
            {"shape": "image", "src": "pictures/a.png"},
            {"kind": "stack", "members": [{"kind": "image", "src": "pictures/b.png"}]},
            {"shape": "rect", "src": "pictures/not.png"},
        ],
    }
    assert store.named_refs(doc) == {
        "pictures/photo.png",
        "pictures/a.png",
        "pictures/b.png",
    }


def test_remove_unused_pictures(modules: Path) -> None:
    made = store.ensure_device_dir(NAME, STICK_A)
    _module(made, {"device": NAME, "image": "pictures/photo.png"})
    (made / store.RECOVERY_FILE).write_text(
        json.dumps({"nodes": [{"shape": "image", "src": "pictures/held.png"}]})
    )
    for name in ("photo.png", "held.png", "gone.png"):
        _picture(made, name)
    removed = store.remove_unused_pictures(NAME, STICK_A)
    assert removed == [made / "pictures" / "gone.png"]
    assert sorted(p.name for p in (made / "pictures").iterdir()) == [
        "held.png",
        "photo.png",
    ]


def test_remove_unused_pictures_keeps_all_while_damaged(modules: Path) -> None:
    made = store.ensure_device_dir(NAME, STICK_A)
    (made / store.MODULE_FILE).write_text("{ not json")
    _picture(made, "photo.png")
    assert store.remove_unused_pictures(NAME, STICK_A) == []
    assert (made / "pictures" / "photo.png").is_file()


def test_copy_pictures_reuses_same_bytes_and_numbers_others(modules: Path) -> None:
    src = modules / "Source"
    dest = modules / "Dest"
    _picture(src, "a.png", b"one")
    _picture(src, "b.png", b"two")
    _picture(dest, "a.png", b"one")
    _picture(dest, "b.png", b"other")
    moved = store.copy_pictures(
        src, ["pictures/a.png", "pictures/b.png", "pictures/missing.png"], dest
    )
    assert moved == {
        "pictures/a.png": "pictures/a.png",
        "pictures/b.png": "pictures/b_1.png",
    }
    assert (dest / "pictures" / "b_1.png").read_bytes() == b"two"
    assert (dest / "pictures" / "b.png").read_bytes() == b"other"


# --- an edit's temporary folder -----------------------------------------------------


def _saved_device(modules: Path) -> Path:
    made = store.ensure_device_dir(NAME, STICK_A)
    _module(made, {"device": NAME, "image": "pictures/photo.png", "nodes": []})
    _picture(made, "photo.png", b"old photo")
    return made


def test_edit_cancel_leaves_nothing(modules: Path) -> None:
    made = _saved_device(modules)
    temp = store.begin_edit(NAME, STICK_A)
    assert temp == store.edit_temp_dir(NAME, STICK_A)
    assert (temp / "start" / "module.json").is_file()
    assert (temp / "start" / "pictures" / "photo.png").read_bytes() == b"old photo"
    ref = store.stage_picture(NAME, STICK_A, b"new chip", "chip.png")
    assert ref == "pictures/chip.png"
    assert not (made / "pictures" / "chip.png").exists()
    store.cancel_edit(NAME, STICK_A)
    assert not temp.exists()
    assert sorted(p.name for p in (made / "pictures").iterdir()) == ["photo.png"]


def test_stage_picture_numbers_a_taken_name(modules: Path) -> None:
    _saved_device(modules)
    store.begin_edit(NAME, STICK_A)
    assert (
        store.stage_picture(NAME, STICK_A, b"old photo", "photo.png")
        == "pictures/photo.png"
    )
    assert (
        store.stage_picture(NAME, STICK_A, b"other", "photo.png")
        == "pictures/photo_1.png"
    )
    store.cancel_edit(NAME, STICK_A)


def test_edit_commit_copies_and_cleans(modules: Path) -> None:
    made = _saved_device(modules)
    store.begin_edit(NAME, STICK_A)
    chip = store.stage_picture(NAME, STICK_A, b"new chip", "chip.png")
    store.stage_picture(NAME, STICK_A, b"dropped", "dropped.png")

    def change(doc: dict) -> None:
        doc["image"] = ""
        doc["nodes"] = [{"shape": "image", "src": chip}]

    assert store.commit_edit(NAME, STICK_A, change) == ""
    assert not store.edit_temp_dir(NAME, STICK_A).exists()
    assert sorted(p.name for p in (made / "pictures").iterdir()) == ["chip.png"]
    doc = json.loads((made / "module.json").read_text())
    assert doc["nodes"] == [{"shape": "image", "src": "pictures/chip.png"}]


def test_a_commit_onto_a_damaged_file_moves_no_picture(modules: Path) -> None:
    """07 S12 (GL-079): a Save refused because module.json is damaged
    copies no picture into the device folder; the edit stays for another
    try."""
    made = _saved_device(modules)
    (made / "module.json").write_text("{ not json")
    store.begin_edit(NAME, STICK_A)
    store.stage_picture(NAME, STICK_A, b"new chip", "chip.png")
    error = store.commit_edit(NAME, STICK_A, lambda doc: None)
    assert "damaged" in error
    assert not (made / "pictures" / "chip.png").exists()
    assert (made / "module.json").read_text() == "{ not json"
    assert store.edit_temp_dir(NAME, STICK_A).is_dir()


def test_recover_edit_by_phase(modules: Path) -> None:
    made = _saved_device(modules)
    # Editing, no recovery copy: dropped.
    store.begin_edit(NAME, STICK_A)
    assert store.recover_edit(NAME, STICK_A) == "dropped"
    assert not store.edit_temp_dir(NAME, STICK_A).exists()
    # Editing with a recovery copy waiting: kept.
    temp = store.begin_edit(NAME, STICK_A)
    (made / store.RECOVERY_FILE).write_text("{}")
    assert store.recover_edit(NAME, STICK_A) == "kept"
    assert temp.is_dir()
    (made / store.RECOVERY_FILE).unlink()
    # A Save that stopped part way: start/ put back.
    store._set_state(temp, "committing")
    (made / "module.json").write_text(json.dumps({"device": NAME, "nodes": [1]}))
    (made / "pictures" / "photo.png").unlink()
    _picture(made, "half.png")
    assert store.recover_edit(NAME, STICK_A) == "restored"
    assert not temp.exists()
    doc = json.loads((made / "module.json").read_text())
    assert doc["nodes"] == [] and doc["image"] == "pictures/photo.png"
    assert sorted(p.name for p in (made / "pictures").iterdir()) == ["photo.png"]


# --- delete ----------------------------------------------------------------------


def test_delete_keeps_the_folder_without_pictures(modules: Path) -> None:
    made = _saved_device(modules)
    assert store.delete(NAME, STICK_A) == ""
    assert not (made / "module.json").exists()
    assert (made / "pictures" / "photo.png").is_file()


def test_delete_with_pictures_removes_folder_and_edit_folders(modules: Path) -> None:
    made = _saved_device(modules)
    temp = store.begin_edit(NAME, STICK_A)
    other = store.begin_edit(NAME, STICK_A, owner="calibration")
    assert store.delete(NAME, STICK_A, pictures=True) == ""
    assert not made.exists()
    assert not temp.exists() and not other.exists()


# --- import ----------------------------------------------------------------------


def test_import_choices_and_source(modules: Path) -> None:
    for name in ("Alpha", "Beta"):
        (modules / name).mkdir()
        _module(modules / name, {"device": name})
    (modules / "Empty").mkdir()
    store._dirs_changed()
    assert store.import_choices() == ["Alpha", "Beta"]
    assert store.import_choices("Alpha") == ["Beta"]
    assert store.resolve_import_source("beta") == modules / "Beta" / "module.json"
    assert store.resolve_import_source("Empty") is None
    assert store.resolve_import_source("cache") is None


def test_file_direction_reads_the_file_not_its_name(modules: Path) -> None:
    # Every file is module.json: a vJoy's must still count as an output.
    vjoy = modules / "vJoy 1" / "module.json"
    stick = modules / "Stick" / "module.json"
    marked = modules / "Renamed Output" / "module.json"
    assert store.file_direction({"device": "vJoy 1"}, vjoy) == "dest"
    assert store.file_direction({}, vjoy) == "dest"
    assert store.file_direction({"direction": "dest"}, marked) == "dest"
    assert store.file_direction({"device": "Stick"}, stick) == "source"


def test_refused_message_names_the_device_folder(modules: Path) -> None:
    from gremlin.modules import module_file

    path = modules / "VKBSim NXT" / "module.json"
    text = module_file.refused_message(module_file.ModuleFileDamaged(path, "bad"))
    assert "the module file VKBSim NXT\module.json is damaged (bad)" in text
