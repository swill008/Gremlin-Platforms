# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""One device file, .gmap, for Export / Import Device (D-FIXLIST-B2, 08
S49-S114): the label carries Made by, Note and the chosen modes; only the
chosen modes' wires go in; the output modules' pictures travel; Import As a
new device writes only the ticked pieces and says what it wrote, for Undo
Import. Every file goes to a temp modules folder, never the real one."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, util
from gremlin.modules import device_zip, store
from gremlin.ui import device_pack

STICK = "B2 Zip Stick"
GUID = "{1A2B3C4D-0000-1111-2222-333344445555}"
OTHER = "{9F8E7D6C-0000-1111-2222-333344445555}"
OUT = "vJoy 1"
ACT_A = "11111111-1111-1111-1111-111111111111"
ACT_B = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(util, "modules_dir", lambda: folder)
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    yield folder
    device_pack.drop_preview()


def _put_device() -> Path:
    base = store.ensure_device_dir(STICK, GUID)
    (base / store.PICTURES).mkdir(exist_ok=True)
    (base / store.PICTURES / "photo.png").write_bytes(b"photo-bytes")
    (base / store.PICTURES / "chip.png").write_bytes(b"chip-bytes")
    doc = {
        "kind": "control.hardware",
        "device": STICK,
        "direction": "source",
        "boundGuidLocal": GUID,
        "boundName": STICK,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "keys": []},
        "nodes": [
            {
                "kind": "draw",
                "shape": "image",
                "plane": "background",
                "src": "pictures/photo.png",
            },
            {"kind": "image", "shape": "image", "src": "pictures/chip.png"},
        ],
    }
    store.module_file_in(base).write_text(json.dumps(doc), encoding="utf-8")
    return base


def _put_output() -> Path:
    base = store.ensure_device_dir(OUT, "")
    (base / store.PICTURES).mkdir(exist_ok=True)
    (base / store.PICTURES / "pad.png").write_bytes(b"pad-bytes")
    doc = {
        "kind": "control.hardware",
        "device": OUT,
        "direction": "dest",
        "nodes": [{"kind": "image", "shape": "image", "src": "pictures/pad.png"}],
    }
    store.module_file_in(base).write_text(json.dumps(doc), encoding="utf-8")
    return base


def _wires() -> dict:
    return {
        "modes": [
            {
                "name": "Default",
                "lines": ["Button 1"],
                "inputs": [f"<input><action-id>{ACT_A}</action-id></input>"],
            },
            {
                "name": "Flight",
                "lines": ["Button 2"],
                "inputs": [f"<input><action-id>{ACT_B}</action-id></input>"],
            },
        ],
        "actions": [
            f'<action id="{ACT_A}" type="x"/>',
            f'<action id="{ACT_B}" type="x"/>',
        ],
        "outputs": [OUT],
        "tree": {"Default": "", "Flight": "Default"},
    }


def _read(data: bytes) -> tuple[list[str], dict]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return sorted(zf.namelist()), json.loads(zf.read("gmap.json"))


def test_label_carries_made_by_note_and_modes(modules: Path, tmp_path: Path) -> None:
    _put_device()
    data = device_zip.build_gmap(
        STICK, GUID, _wires(), made_by="  Stacie  W ", note="For the A-10.\n"
    )
    assert isinstance(data, bytes)
    _names, label = _read(data)
    assert label["madeBy"] == "Stacie W"
    assert label["note"] == "For the A-10."
    assert label["modes"] == ["Default", "Flight"]
    path = tmp_path / "a.gmap"
    path.write_bytes(data)
    loaded = device_zip.read_gmap(path)
    assert isinstance(loaded, dict)
    assert loaded["madeBy"] == "Stacie W"
    assert loaded["note"] == "For the A-10."
    assert loaded["modes"] == ["Default", "Flight"]
    assert loaded["bytes"] == len(data)


def test_without_bindings_the_label_has_no_modes(modules: Path) -> None:
    _put_device()
    data = device_zip.build_gmap(STICK, GUID, None)
    assert isinstance(data, bytes)
    _names, label = _read(data)
    assert label["madeBy"] == "" and label["note"] == "" and label["modes"] == []


def test_only_the_chosen_modes_wires_go_in(modules: Path, tmp_path: Path) -> None:
    _put_device()
    data = device_zip.build_gmap(STICK, GUID, _wires(), modes=["Flight"])
    assert isinstance(data, bytes)
    _names, label = _read(data)
    assert label["modes"] == ["Flight"]
    path = tmp_path / "f.gmap"
    path.write_bytes(data)
    loaded = device_zip.read_gmap(path)
    assert isinstance(loaded, dict)
    wires = loaded["wires"]
    assert [m["name"] for m in wires["modes"]] == ["Flight"]
    # Its parent stays in the tree; the other mode's action does not travel.
    assert wires["tree"] == {"Flight": "Default", "Default": ""}
    assert len(wires["actions"]) == 1
    assert ACT_B in wires["actions"][0]


def test_export_device_passes_the_new_fields(modules: Path, tmp_path: Path) -> None:
    _put_device()
    out = tmp_path / "e"
    assert (
        device_zip.export_device(
            STICK, GUID, out, _wires(), made_by="Me", note="Hi", modes=["Default"]
        )
        == ""
    )
    _names, label = _read((tmp_path / "e.gmap").read_bytes())
    assert (label["madeBy"], label["note"], label["modes"]) == ("Me", "Hi", ["Default"])


def test_output_module_pictures_travel(modules: Path, tmp_path: Path) -> None:
    _put_device()
    out_base = _put_output()
    data = device_zip.build_gmap(STICK, GUID, _wires())
    assert isinstance(data, bytes)
    names, _label = _read(data)
    slugs = [
        n[len("bindings/outputs/") : -len(".json")]
        for n in names
        if n.startswith("bindings/outputs/") and n.endswith(".json")
    ]
    assert slugs == [out_base.name]
    slug = slugs[0]
    assert f"bindings/outputs/{slug}/pictures/pad.png" in names
    path = tmp_path / "o.gmap"
    path.write_bytes(data)
    loaded = device_zip.read_gmap(path)
    assert isinstance(loaded, dict)
    assert loaded["outputPictures"] == {slug: {"pad.png": b"pad-bytes"}}
    # Output pictures are not the device's own pictures.
    assert "pad.png" not in loaded["pictures"]


def test_import_returns_the_folder_and_what_it_wrote(
    modules: Path, tmp_path: Path
) -> None:
    base = _put_device()
    out = tmp_path / "n.gmap"
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    shutil.rmtree(base)
    store._dirs_changed()
    result = device_zip.import_device(out)
    assert isinstance(result, dict)
    assert result["error"] == "", result["error"]
    assert result["key"] == store.id_key(STICK, GUID)
    folder = store.device_dir(STICK, GUID)
    assert result["folder"] == folder
    assert all(before is None for _p, before in result["written"])
    assert {Path(p) for p, _b in result["written"]} == {
        store.module_file_in(folder),
        folder / "pictures" / "photo.png",
        folder / "pictures" / "chip.png",
    }


def test_import_as_new_device_writes_only_the_ticked_pieces(
    modules: Path, tmp_path: Path
) -> None:
    _put_device()
    out = tmp_path / "p.gmap"
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    loaded = device_zip.read_gmap(out)
    assert isinstance(loaded, dict)
    # The window's ticks: the module without the chip picture.
    doc = dict(loaded["module"])
    doc["nodes"] = [n for n in doc["nodes"] if n.get("src") != "pictures/chip.png"]
    result = device_zip.import_device(
        out, target_name=STICK, target_guid=OTHER, pieces={"module": doc}
    )
    assert result["error"] == "", result["error"]
    folder = store.device_dir(STICK, OTHER)
    # A taken name gets "(2)".
    assert folder.name == f"{store.folder_name_for(STICK)} (2)"
    assert result["folder"] == folder
    assert (folder / "pictures" / "photo.png").is_file()
    assert not (folder / "pictures" / "chip.png").exists()
    written = json.loads(store.module_file_in(folder).read_text(encoding="utf-8"))
    assert len(written["nodes"]) == 1
    assert written["boundGuidLocal"] == OTHER


def test_import_without_the_module_piece(modules: Path, tmp_path: Path) -> None:
    base = _put_device()
    out = tmp_path / "w.gmap"
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    shutil.rmtree(base)
    store._dirs_changed()
    result = device_zip.import_device(out, pieces={"module": None, "pictures": []})
    assert result["error"] == "", result["error"]
    assert result["written"] == []
    assert not store.module_file_in(store.device_dir(STICK, GUID)).exists()


def test_chosen_modes_keep_root_actions_and_what_they_reach() -> None:
    # An input names its action by <root-action> (profile.InputItemBinding);
    # that root names its children by <action-id>, and they name theirs.
    root = "aaaaaaaa-0000-0000-0000-000000000001"
    child = "aaaaaaaa-0000-0000-0000-000000000002"
    grandchild = "aaaaaaaa-0000-0000-0000-000000000003"
    other = "bbbbbbbb-0000-0000-0000-000000000001"
    wires = {
        "modes": [
            {
                "name": "Default",
                "lines": ["Button 1"],
                "inputs": [
                    "<input><action-configuration><root-action>"
                    f"{root.upper()}</root-action></action-configuration></input>"
                ],
            },
            {
                "name": "Combat",
                "lines": ["Button 2"],
                "inputs": [f"<input><root-action>{other}</root-action></input>"],
            },
        ],
        "actions": [
            f'<action id="{root}" type="root"><actions>'
            f"<action-id>{child}</action-id></actions></action>",
            f'<action id="{child}" type="chain"><chain-0>'
            f"<action-id>{grandchild}</action-id></chain-0></action>",
            f'<action id="{grandchild}" type="map-to-vjoy"/>',
            f'<action id="{other}" type="root"/>',
        ],
        "outputs": [],
        "tree": {"Default": "", "Combat": "Default"},
    }
    kept = device_zip.only_modes(wires, ["Default"])
    ids = sorted(a.split('"')[1] for a in kept["actions"])
    assert ids == [root, child, grandchild]


def test_a_twin_file_comes_in_as_two_while_its_twin_is_connected(
    modules: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import registry

    _put_device()
    out = tmp_path / "t.gmap"
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    # The stick of this name that is connected here is GUID; the file comes
    # from its twin (OTHER), which has no folder here.
    monkeypatch.setattr(
        registry, "connected_names", lambda: {STICK.casefold(): {store.guid_key(GUID)}}
    )
    monkeypatch.setattr(
        registry, "guid_for_name", lambda name: GUID if name == STICK else ""
    )
    result = device_zip.import_device(out, target_name=STICK, target_guid=OTHER)
    assert result["error"] == "", result["error"]
    assert result["key"] == store.id_key(STICK, OTHER)
    folder = result["folder"]
    assert folder is not None
    assert folder.name == f"{store.folder_name_for(STICK)} (2)"
    held = json.loads((folder / store.ID_FILE).read_text(encoding="utf-8"))
    assert held["id"] == store.id_key(STICK, OTHER)
    assert held["name"] == STICK
    assert store.dir_of_id(store.id_key(STICK, OTHER)) == folder
    assert store.module_file_in(folder).is_file()
    # The connected stick's own folder is untouched; the same id is refused.
    again = device_zip.import_device(out, target_name=STICK, target_guid=OTHER)
    assert "already has a device folder" in again["error"]
    same = device_zip.import_device(out, target_name=STICK, target_guid=GUID)
    assert "already has a device folder" in same["error"]
