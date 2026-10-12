# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device folder Export / Import as ".gmap" and templates as ".gtemplate"
(08 S111, S112, S49, S73; D-03-DEVICE-FOLDERS). Export zips one device's
folder (module.json without this machine's id, only the pictures it names,
the bindings only when ticked) and is refused inside the modules folder;
Import unpacks into a new device folder, a taken name getting "(2)"; a
damaged or too big file is refused. The Device Pack reads a .gmap and its
import writes pictures into the device's folder, keeping the ones it
replaces in that folder's imported/. Every file goes to a temp modules
folder, never the real one."""

from __future__ import annotations

import json
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, util
from gremlin.modules import device_zip, pack_checks, store
from gremlin.ui import device_pack

STICK = "Zip Test Stick"
GUID = "{1A2B3C4D-0000-1111-2222-333344445555}"
OTHER = "{9F8E7D6C-0000-1111-2222-333344445555}"


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(util, "modules_dir", lambda: folder)
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    yield folder
    device_pack.drop_preview()


def _stick_doc(guid: str = GUID, name: str = STICK) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "boundGuidLocal": guid,
        "boundName": name,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "keys": []},
        "nodes": [
            # The device's photo: the bottom background picture (07 S127).
            {"kind": "draw", "shape": "image", "plane": "background",
             "src": "pictures/photo.png"},
            {"kind": "image", "shape": "image", "src": "pictures/chip.png"},
            {"kind": "btn", "hwId": 1},
        ],
    }


def _put_device(name: str = STICK, guid: str = GUID, doc: dict | None = None) -> Path:
    base = store.ensure_device_dir(name, guid)
    (base / store.PICTURES).mkdir(exist_ok=True)
    (base / store.PICTURES / "photo.png").write_bytes(b"photo-bytes")
    (base / store.PICTURES / "chip.png").write_bytes(b"chip-bytes")
    (base / store.PICTURES / "unused.png").write_bytes(b"not named")
    (base / store.RECOVERY_FILE).write_text("{}", encoding="utf-8")
    (base / store.IMPORTED).mkdir(exist_ok=True)
    (base / store.IMPORTED / "module old.json").write_text("{}", encoding="utf-8")
    store.module_file_in(base).write_text(
        json.dumps(doc or _stick_doc(guid, name), indent=2), encoding="utf-8"
    )
    return base


def _names(data: bytes) -> list[str]:
    import io

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return sorted(zf.namelist())


def test_export_then_import_round_trip(modules: Path, tmp_path: Path) -> None:
    base = _put_device()
    out = tmp_path / "out" / "EVO R.gmap"
    out.parent.mkdir()
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    with zipfile.ZipFile(out) as zf:
        names = sorted(zf.namelist())
        label = json.loads(zf.read("gmap.json"))
        module = json.loads(zf.read("module.json"))
    # Only the named pictures; never device.json, recovery, imported.
    assert names == [
        "gmap.json",
        "module.json",
        "pictures/chip.png",
        "pictures/photo.png",
    ]
    assert label["format"] == "gremlin-device" and label["version"] == 1
    assert label["parts"] == ["folder"]
    assert label["deviceName"] == STICK and label["direction"] == "source"
    assert label["id"] == store.id_key(STICK, GUID)
    assert "boundGuidLocal" not in module and "boundName" not in module

    # On another machine (the folder gone), Import makes it again.
    import shutil

    shutil.rmtree(base)
    store._dirs_changed()
    result = device_zip.import_device(out)
    key, error = result["key"], result["error"]
    assert error == "", error
    assert key == store.id_key(STICK, GUID)
    again = store.device_dir(STICK, GUID)
    assert (again / "pictures" / "photo.png").read_bytes() == b"photo-bytes"
    assert (again / "pictures" / "chip.png").read_bytes() == b"chip-bytes"
    assert not (again / "pictures" / "unused.png").exists()
    doc = json.loads(store.module_file_in(again).read_text(encoding="utf-8"))
    assert store.device_photo_ref(doc) == "pictures/photo.png"
    assert doc["claim"]["buttons"] == [1, 2]


def test_import_refuses_a_device_that_has_a_folder(
    modules: Path, tmp_path: Path
) -> None:
    _put_device()
    out = tmp_path / "a.gmap"
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    result = device_zip.import_device(out)
    key, error = result["key"], result["error"]
    assert key == ""
    assert "already has a device folder" in error


def test_a_taken_name_gets_two(modules: Path, tmp_path: Path) -> None:
    _put_device()
    out = tmp_path / "a.gmap"
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    # Another stick of the same name (another id) on this machine.
    result = device_zip.import_device(out, target_name=STICK, target_guid=OTHER)
    key, error = result["key"], result["error"]
    assert error == "", error
    assert key == store.id_key(STICK, OTHER)
    folder = store.device_dir(STICK, OTHER)
    assert folder.name == f"{store.folder_name_for(STICK)} (2)"
    assert (folder / "module.json").is_file()
    assert (folder / "pictures" / "photo.png").is_file()


def test_bindings_only_when_ticked(
    modules: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _put_device()
    wires = {
        "modes": [{"name": "Default", "lines": ["Button 1"], "inputs": ["<input/>"]}],
        "actions": [],
        "outputs": [],
        "tree": {"Default": None},
    }
    seen: list[str] = []

    def collect(guid: str, modes: object = None, profile: object = None) -> dict:
        seen.append(guid)
        return wires

    monkeypatch.setattr(device_pack, "collect_wires", collect)
    without = device_zip.build_gmap(STICK, GUID, None)
    assert isinstance(without, bytes)
    assert not any(n.startswith("bindings/") for n in _names(without))
    assert seen == []
    with_ = device_zip.build_gmap(STICK, GUID, device_pack.collect_wires(GUID))
    assert isinstance(with_, bytes)
    assert "bindings/wires.json" in _names(with_)
    path = tmp_path / "b.gmap"
    path.write_bytes(with_)
    loaded = device_zip.read_gmap(path)
    assert isinstance(loaded, dict)
    assert loaded["gmap"]["parts"] == ["folder", "bindings"]
    assert loaded["wires"]["modes"][0]["name"] == "Default"


def test_export_refused_inside_the_modules_folder(modules: Path) -> None:
    _put_device()
    out = modules / "copy.gmap"
    error = device_zip.export_device(STICK, GUID, out, None)
    assert "modules folder" in error
    assert not out.exists()


def test_export_without_a_module_file(modules: Path, tmp_path: Path) -> None:
    error = device_zip.export_device("Nobody", "", tmp_path / "x.gmap", None)
    assert "no module file" in error
    assert not (tmp_path / "x.gmap").exists()


def test_keep_damaged_puts_the_bytes_in(modules: Path, tmp_path: Path) -> None:
    base = store.ensure_device_dir(STICK, GUID)
    store.module_file_in(base).write_bytes(b'{"device": broken')
    assert isinstance(device_zip.build_gmap(STICK, GUID, None), str)
    data = device_zip.build_gmap(STICK, GUID, None, keep_damaged=True)
    assert isinstance(data, bytes)
    path = tmp_path / "d.gmap"
    path.write_bytes(data)
    loaded = device_zip.read_gmap(path)
    assert isinstance(loaded, dict)
    assert loaded["gmap"]["damaged"]
    assert loaded["module"] is None
    assert loaded["moduleBytes"] == b'{"device": broken'


def test_a_corrupt_file_is_refused(modules: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.gmap"
    bad.write_bytes(b"not a zip at all")
    assert device_zip.read_gmap(bad) == "Not a valid zip."
    result = device_zip.import_device(bad)
    key, error = result["key"], result["error"]
    assert key == "" and error
    no_label = tmp_path / "nolabel.gmap"
    with zipfile.ZipFile(no_label, "w") as zf:
        zf.writestr("module.json", "{}")
    assert "gmap.json" in device_zip.read_gmap(no_label)
    broken = tmp_path / "broken.gmap"
    with zipfile.ZipFile(broken, "w") as zf:
        zf.writestr("gmap.json", json.dumps({"format": "gremlin-device", "version": 1}))
        zf.writestr("module.json", "{not json")
    assert "module.json" in device_zip.read_gmap(broken)
    newer = tmp_path / "newer.gmap"
    with zipfile.ZipFile(newer, "w") as zf:
        zf.writestr("gmap.json", json.dumps({"format": "gremlin-device", "version": 9}))
        zf.writestr("module.json", "{}")
    assert "newer" in device_zip.read_gmap(newer)


def test_an_over_limit_file_is_refused(
    modules: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _put_device()
    path = tmp_path / "big.gmap"
    assert device_zip.export_device(STICK, GUID, path, None) == ""
    monkeypatch.setattr(pack_checks, "MAX_UNPACKED", 10)
    refused = device_zip.read_gmap(path)
    assert isinstance(refused, str) and "too big" in refused


def test_a_picture_path_outside_pictures_is_not_unpacked(
    modules: Path, tmp_path: Path
) -> None:
    path = tmp_path / "evil.gmap"
    doc = {"kind": "control.hardware", "device": "Evil", "nodes": []}
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "gmap.json",
            json.dumps(
                {"format": "gremlin-device", "version": 1, "deviceName": "Evil"}
            ),
        )
        zf.writestr("module.json", json.dumps(doc))
        zf.writestr("pictures/../../escape.png", b"x")
        zf.writestr("pictures/ok.png", b"ok")
    loaded = device_zip.read_gmap(path)
    assert isinstance(loaded, dict)
    assert list(loaded["pictures"]) == ["ok.png"]


def test_gtemplate_round_trip(modules: Path, tmp_path: Path) -> None:
    base = store.template_dir("Desk")
    (base / "pictures").mkdir(parents=True)
    (base / "pictures" / "panel.png").write_bytes(b"panel")
    (base / "pictures" / "spare.png").write_bytes(b"spare")
    template = {
        "kind": "device-map-template",
        "name": "Desk",
        "nodes": [{"shape": "image", "kind": "image", "src": "pictures/panel.png"}],
    }
    (base / "template.json").write_text(json.dumps(template), encoding="utf-8")
    data = device_zip.build_gtemplate("Desk")
    assert _names(data) == ["pictures/panel.png", "template.json"]
    path = tmp_path / "Desk.gtemplate"
    path.write_bytes(data)
    name = device_zip.import_gtemplate(path)
    assert name == "Desk 2"
    again = store.template_dir(name)
    assert (again / "pictures" / "panel.png").read_bytes() == b"panel"
    doc = json.loads((again / "template.json").read_text(encoding="utf-8"))
    assert doc["name"] == "Desk 2"
    assert doc["nodes"][0]["src"] == "pictures/panel.png"


def test_an_old_json_template_brings_the_pictures_that_exist(
    modules: Path, tmp_path: Path
) -> None:
    (modules / "old_stick").mkdir()
    (modules / "old_stick" / "here.png").write_bytes(b"here")
    old = tmp_path / "Old.json"
    old.write_text(
        json.dumps(
            {
                "kind": "device-map-template",
                "name": "Old",
                "nodes": [
                    {"shape": "image", "src": "old_stick/here.png"},
                    {"shape": "image", "src": "old_stick/gone.png"},
                ],
            }
        ),
        encoding="utf-8",
    )
    name = device_zip.import_gtemplate(old)
    assert name == "Old"
    base = store.template_dir("Old")
    assert (base / "pictures" / "here.png").read_bytes() == b"here"
    assert not (base / "pictures" / "gone.png").exists()
    doc = json.loads((base / "template.json").read_text(encoding="utf-8"))
    assert [n["src"] for n in doc["nodes"]] == [
        "pictures/here.png",
        "pictures/gone.png",
    ]
    not_one = tmp_path / "nope.json"
    not_one.write_text("{}", encoding="utf-8")
    assert device_zip.import_gtemplate(not_one) == ""


# --- the Device Pack ----------------------------------------------------------------


def test_the_device_pack_reads_a_gmap(modules: Path, tmp_path: Path) -> None:
    _put_device()
    path = tmp_path / "Stick.gmap"
    assert device_zip.export_device(STICK, GUID, path, None) == ""
    loaded = device_pack._read_zip(path)
    assert isinstance(loaded, dict), loaded
    # The pack's own way: pictures at the zip's root, refs their file names.
    assert loaded["doc"]["nodes"][0]["src"] == "photo.png"
    assert loaded["doc"]["nodes"][1]["src"] == "chip.png"
    assert set(loaded["files"]) == {"photo.png", "chip.png"}
    assert loaded["doc"]["pack"]["exportedName"] == STICK
    described = device_pack.describe_zip(path)
    assert isinstance(described, dict), described


def test_device_pack_import_writes_pictures_into_the_device_folder(
    modules: Path, tmp_path: Path
) -> None:
    base = _put_device()
    path = tmp_path / "Stick.gmap"
    assert device_zip.export_device(STICK, GUID, path, None) == ""
    # The pictures here changed since: the import's are written over them,
    # the ones here kept in the device folder's imported/.
    (base / "pictures" / "photo.png").write_bytes(b"photo-here")
    record: list[tuple[Path, bytes | None]] = []
    doc = {"nodes": [
        {"shape": "image", "plane": "background", "src": "photo.png"},
        {"shape": "image", "src": "chip.png"},
    ]}
    written = device_pack._write_pictures(
        base,
        {"photo.png": b"photo-bytes", "chip.png": b"chip-bytes"},
        {"pic:photo.png", "pic:chip.png"},
        doc,
        record,
    )
    assert written == {"photo.png": "photo.png", "chip.png": "chip.png"}
    assert (base / "pictures" / "photo.png").read_bytes() == b"photo-bytes"
    assert doc["nodes"][0]["src"] == "pictures/photo.png"
    assert doc["nodes"][1]["src"] == "pictures/chip.png"
    kept = list((base / "imported" / "pictures").glob("photo *.png"))
    assert [p.read_bytes() for p in kept] == [b"photo-here"]
    # Nothing written at the modules folder's root or an old imported/.
    assert not (modules / "imported").exists()


def test_device_pack_import_keeps_the_previous_module_file_in_the_folder(
    modules: Path, tmp_path: Path
) -> None:
    base = _put_device()
    before = store.module_file_in(base).read_bytes()
    record: list[tuple[Path, bytes | None]] = []
    name = device_pack._write_module(
        store.module_file_in(base),
        {"kind": "control.hardware", "device": STICK},
        record,
    )
    assert name
    assert (base / "imported" / name).read_bytes() == before
    assert not (modules / "imported").exists()


def test_a_gmap_with_a_random_id_is_not_a_guid() -> None:
    assert device_zip.guid_like(GUID)
    assert device_zip.guid_like(str(uuid.uuid4()))
    assert not device_zip.guid_like("name:vjoy_1")


# --- import with bindings is one Undo step (user decision 3a, 2026-10-11) -------


def _wire(profile: object, uid: uuid.UUID, button: int) -> None:
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _wired(profile: object, uid: uuid.UUID) -> list[int]:
    return sorted(
        item.input_id for item in profile.inputs.get(uid, []) if item.action_sequences
    )


def _ticked(described: dict) -> dict:
    """Every piece the import window shows ticked, as it sends them."""
    items, outputs = [], {}
    for section in described.get("sections") or []:
        if str(section.get("id", "")).startswith("out:"):
            outputs[str(section["id"])[4:]] = section.get("target") or ""
        for item in section.get("items") or []:
            if item.get("checked") is not False:
                items.append(item["id"])
    return {"items": items, "outputs": outputs, "target": "new"}


@pytest.mark.parametrize("with_folder", [True, False])
def test_import_as_new_with_bindings_is_one_undo_step(
    modules: Path, tmp_path: Path, with_folder: bool
) -> None:
    """Import as a new device puts the file's wires into the open profile
    (device_pack.import_as_new -> apply_zip), with and without a device
    folder in the file (a Device Library setup of a stick with no module
    file holds only bindings); Undo Import takes the wires and the folder
    back in one step."""
    import shutil

    from gremlin import shared_state
    from gremlin.profile import DeviceInfo, Profile

    uid = uuid.UUID(GUID.strip("{}"))
    source = Profile()
    source.device_database.devices[uid] = DeviceInfo(uid, STICK)
    shared_state.current_profile = source
    try:
        _wire(source, uid, 1)
        base = _put_device()
        out = tmp_path / "wired.gmap"
        wires = device_pack.collect_wires(GUID)
        if not with_folder:
            shutil.rmtree(base)
            store._dirs_changed()
        built = device_zip.build_gmap(STICK, GUID, wires, no_file_ok=True)
        assert isinstance(built, bytes), built
        out.write_bytes(built)
        with zipfile.ZipFile(out) as zf:
            assert ("module.json" in zf.namelist()) is with_folder
        if with_folder:
            # Another PC: no folder, a profile without the wires.
            shutil.rmtree(base)
            store._dirs_changed()
        target = Profile()
        target.device_database.devices[uid] = DeviceInfo(uid, STICK)
        shared_state.current_profile = target
        described = device_pack.describe_zip(out)
        assert isinstance(described, dict), described
        selection = _ticked(described)
        preview = device_pack.preview_new(out, "", selection)
        assert preview.get("ok"), preview
        result = device_pack.import_as_new(out, "", selection)
        assert result.get("ok"), result
        assert _wired(target, uid) == [1]
        folder = store.device_dir(STICK, GUID)
        assert (folder / "module.json").is_file() is with_folder
        assert device_pack.can_undo_import()
        undone = device_pack.undo_import()
        assert undone["ok"], undone
        # One step: the wires (and the folder it made) are gone again.
        assert _wired(target, uid) == []
        assert not (folder / "module.json").exists()
        assert not device_pack.can_undo_import()
    finally:
        device_pack.drop_import_undo()
        shared_state.current_profile = None


def test_import_without_bindings_leaves_no_undo(modules: Path, tmp_path: Path) -> None:
    import shutil

    base = _put_device()
    out = tmp_path / "plain.gmap"
    assert device_zip.export_device(STICK, GUID, out, None) == ""
    shutil.rmtree(base)
    store._dirs_changed()
    device_pack.drop_import_undo()
    result = device_zip.import_device(out)
    key, error = result["key"], result["error"]
    assert error == "" and key
    assert not device_pack.can_undo_import()
