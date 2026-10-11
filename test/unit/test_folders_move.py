# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-1): the move to device folders (03 S134,
D-03-DEVICE-FOLDERS contract section 6). An old-layout modules folder is
built in tmp and moved; the real data folder is never touched."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from gremlin.config import Configuration
from gremlin.modules import folders_move, store
from gremlin.modules.ids import KEYBOARD, LOGICAL_DEVICE, OSC, stored_guid_key

G1 = "11111111-0000-0000-0000-000000000001"  # T.16000M
G2 = "22222222-0000-0000-0000-000000000002"  # Other Stick, alias "My Stick"
G3 = "33333333-0000-0000-0000-000000000003"  # Twin Stick (file's own id)
G4 = "44444444-0000-0000-0000-000000000004"  # its twin, bound to the same file
G5 = "55555555-0000-0000-0000-000000000005"  # Same Name
G6 = "66666666-0000-0000-0000-000000000006"  # Same Name, another device
G7 = "77777777-0000-0000-0000-000000000007"  # damaged file, by binding
PNG = b"\x89PNG\r\n\x1a\n-picture-"


def _key(guid: str) -> str:
    return stored_guid_key(guid)


def _doc(device: str, guid: str = "", image: str = "", chips: tuple = ()) -> dict:
    doc: dict = {"device": device, "boundName": device}
    if guid:
        doc["boundGuidLocal"] = "{" + guid.upper() + "}"
    if image:
        doc["image"] = image
    doc["nodes"] = [
        {"shape": "group", "children": [{"shape": "image", "src": src}]}
        for src in chips
    ]
    return doc


def _put(path: Path, content: bytes | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, dict):
        content = json.dumps(content).encode("utf-8")
    path.write_bytes(content)


@pytest.fixture
def old(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """An old-layout modules folder, its data folder, the bindings setting,
    an alias and a twin name."""
    modules = tmp_path / "data" / "modules"
    data = tmp_path / "data"
    modules.mkdir(parents=True)
    monkeypatch.setattr(store, "folder", lambda: modules)
    t16 = _doc(
        "T.16000M",
        G1,
        image="t16000m/back.png",
        chips=(
            "t16000m/chip.png",
            "qml/maps/t16000m/chip2.png",
            "library/lib.png",
            "other_stick/theirs.png",
            "t16000m/gone.png",
        ),
    )
    _put(modules / "t16000m.json", t16)
    _put(modules / "t16000m" / "back.png", PNG + b"back")
    _put(modules / "t16000m" / "chip.png", PNG + b"chip")
    _put(modules / "t16000m" / "chip2.png", PNG + b"chip2")
    _put(modules / "t16000m_photo.png", PNG + b"photo")
    _put(modules / "library" / "lib.png", PNG + b"lib")
    _put(
        modules / "other_stick.json",
        _doc("Other Stick", G2, chips=("other_stick/theirs.png",)),
    )
    _put(modules / "other_stick" / "theirs.png", PNG + b"theirs")
    _put(modules / "twins.json", _doc("Twin Stick", G3, chips=("twins/t.png",)))
    _put(modules / "twins" / "t.png", PNG + b"twin")
    _put(modules / "same_a.json", _doc("Same Name", G5))
    _put(modules / "same_b.json", _doc("Same Name", G6))
    _put(modules / "damaged.json", b"{not json at all")
    _put(modules / "keyboard.json", _doc("Keyboard"))
    _put(modules / "osc.json", _doc("OSC"))
    _put(modules / "logical_device.json", _doc("Logical Device"))
    _put(modules / "vjoy_1.json", _doc("vJoy 1"))
    _put(
        modules / "recovery" / "t16000m.json",
        _doc("T.16000M", G1, chips=("t16000m/chip.png",)),
    )
    _put(modules / "imported" / "t16000m.2026-01-JAN_00_00_00.json", _doc("T.16000M"))
    _put(modules / "imported" / "unknown thing.json", _doc("?"))
    _put(
        modules / "templates" / "My Layout.json",
        {"name": "My Layout", "nodes": [{"shape": "image", "src": "library/lib.png"}]},
    )
    _put(modules / "cache" / "photo-stash" / "t16000m" / "photo.png", PNG + b"stash")
    bindings = {
        _key(G3): "twins",
        _key(G4): "twins",
        _key(G7): "damaged",
        "name:keyboard": "keyboard",
    }
    Configuration().set(*folders_move.BINDINGS, json.dumps(bindings))
    aliases = {_key(G2): "My Stick"}
    from gremlin import device_aliases, device_initialization

    monkeypatch.setattr(
        device_aliases,
        "display_name",
        lambda key, default: aliases.get(_key(key), default),
    )
    monkeypatch.setattr(
        device_initialization, "stored_twins", lambda: {_key(G4): "Twin Stick (2)"}
    )
    return {"modules": modules, "data": data, "bindings": bindings}


def _files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _device(folder: Path) -> dict:
    return json.loads((folder / "device.json").read_text(encoding="utf-8"))


def _module(folder: Path) -> dict:
    return json.loads((folder / "module.json").read_text(encoding="utf-8"))


def _srcs(doc: dict) -> list[str]:
    return [child["src"] for node in doc["nodes"] for child in node.get("children", [])]


def _backup(old: dict) -> Path:
    found = sorted((old["data"] / "backup").iterdir())
    assert len(found) == 1
    assert found[0].name.endswith(" device folders move")
    return found[0]


def test_the_backup_holds_everything_before_anything_moves(old: dict) -> None:
    modules = old["modules"]
    before = _files(modules)
    assert folders_move.run_if_needed(modules, old["data"]) == ""
    backup = _backup(old)
    kept = _files(backup)
    for rel, data in before.items():
        assert kept[rel] == data, rel
    bindings = json.loads((backup / folders_move.BINDINGS_FILE).read_text("utf-8"))
    assert bindings == old["bindings"]


def test_a_failed_backup_moves_nothing(
    old: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    modules = old["modules"]
    before = _files(modules)

    def broken(*_args: object, **_kw: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copy2", broken)
    error = folders_move.run_if_needed(modules, old["data"])
    assert "nothing was moved" in error and "disk full" in error
    assert _files(modules) == before
    assert not (modules / folders_move.MARKER).exists()
    assert not any((old["data"] / "backup").iterdir())


def test_folders_ids_and_names(old: dict) -> None:
    modules = old["modules"]
    assert folders_move.run_if_needed(modules, old["data"]) == ""
    expect = {
        "T.16000M": _key(G1),
        "My Stick": _key(G2),  # alias
        "Twin Stick": _key(G3),
        "Twin Stick (2)": _key(G4),  # twin name, its own copy (S6)
        "Same Name": _key(G5),
        "Same Name (2)": _key(G6),  # same name, second by id (S132)
        "Keyboard": _key(str(KEYBOARD)),
        "OSC": _key(str(OSC)),
        "Logical Device": _key(str(LOGICAL_DEVICE)),
        "vJoy 1": "name:vjoy_1",
        "damaged": _key(G7),
    }
    for name, key in expect.items():
        folder = modules / name
        assert (folder / "module.json").is_file(), name
        # The shown name is never changed; only the folder gets " (2)".
        shown = "Same Name" if name == "Same Name (2)" else name
        assert _device(folder) == {"format": 1, "id": key, "name": shown}
    assert len([p for p in modules.iterdir() if (p / "device.json").is_file()]) == len(
        expect
    )
    assert [p.name for p in modules.glob("*.json")] == ["folders.json"]


def test_twins_each_get_their_own_copy(old: dict) -> None:
    modules = old["modules"]
    folders_move.run_if_needed(modules, old["data"])
    first, second = modules / "Twin Stick", modules / "Twin Stick (2)"
    assert (first / "pictures" / "t.png").read_bytes() == PNG + b"twin"
    assert (second / "pictures" / "t.png").read_bytes() == PNG + b"twin"
    assert _key(_module(first)["boundGuidLocal"]) == _key(G3)
    assert _key(_module(second)["boundGuidLocal"]) == _key(G4)
    assert _srcs(_module(second)) == ["pictures/t.png"]


def test_a_damaged_file_moves_as_it_is(old: dict) -> None:
    modules = old["modules"]
    folders_move.run_if_needed(modules, old["data"])
    assert (modules / "damaged" / "module.json").read_bytes() == b"{not json at all"


def test_pictures_moved_and_references_rewritten(old: dict) -> None:
    modules = old["modules"]
    folders_move.run_if_needed(modules, old["data"])
    folder = modules / "T.16000M"
    doc = _module(folder)
    assert doc["image"] == "pictures/back.png"
    assert _srcs(doc) == [
        "pictures/chip.png",
        "pictures/chip2.png",
        "pictures/lib.png",  # the picture library's file, copied in
        "pictures/theirs.png",  # another device's picture, copied in (S133)
        "pictures/gone.png",  # missing: kept, shows "Picture missing" (S108)
    ]
    pictures = folder / "pictures"
    assert (pictures / "lib.png").read_bytes() == PNG + b"lib"
    assert (pictures / "theirs.png").read_bytes() == PNG + b"theirs"
    assert (pictures / "photo.png").read_bytes() == PNG + b"photo"
    assert not (pictures / "gone.png").exists()
    # The other device keeps its own file: nothing shared.
    assert (modules / "My Stick" / "pictures" / "theirs.png").is_file()
    assert _srcs(_module(modules / "My Stick")) == ["pictures/theirs.png"]
    recovery = json.loads((folder / "recovery.json").read_text("utf-8"))
    assert _srcs(recovery) == ["pictures/chip.png"]
    assert (folder / "imported" / "t16000m.2026-01-JAN_00_00_00.json").is_file()
    assert (modules / "imported" / "unknown thing.json").is_file()


def test_templates_converted_and_leftovers_archived(old: dict) -> None:
    modules = old["modules"]
    folders_move.run_if_needed(modules, old["data"])
    template = store.template_dir("My Layout")
    doc = json.loads((template / "template.json").read_text("utf-8"))
    assert doc["nodes"][0]["src"] == "pictures/lib.png"
    assert (template / "pictures" / "lib.png").read_bytes() == PNG + b"lib"
    assert not (modules / "templates" / "My Layout.json").exists()
    for gone in ("library", "recovery", "t16000m", "t16000m_photo.png"):
        assert not (modules / gone).exists(), gone
    assert not list((modules / "cache").glob("photo-stash*"))
    leftovers = _backup(old) / "leftovers"
    assert (leftovers / "library" / "lib.png").is_file()
    assert (leftovers / "templates" / "My Layout.json").is_file()


def test_the_marker_is_written_and_a_second_run_does_nothing(old: dict) -> None:
    modules = old["modules"]
    folders_move.run_if_needed(modules, old["data"])
    marker = json.loads((modules / "folders.json").read_text("utf-8"))
    assert marker["layout"] == 2
    assert marker["backup"] == str(_backup(old))
    after = _files(modules)
    _put(modules / "stray.json", _doc("Stray"))
    assert folders_move.run_if_needed(modules, old["data"]) == ""
    assert (modules / "stray.json").is_file()
    assert _files(modules) == {
        **after,
        "stray.json": (modules / "stray.json").read_bytes(),
    }
    assert len(list((old["data"] / "backup").iterdir())) == 1


def test_a_new_install_just_gets_the_marker(tmp_path: Path) -> None:
    modules, data = tmp_path / "modules", tmp_path
    modules.mkdir()
    assert folders_move.run_if_needed(modules, data) == ""
    assert (modules / "folders.json").is_file()
    assert not (data / "backup").exists()


def test_a_cut_short_run_resumes(old: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = old["modules"]
    real = folders_move._move_device
    calls = {"n": 0}

    def stops(*args: Any) -> None:  # noqa: ANN401 - passed through
        calls["n"] += 1
        if calls["n"] == 4:
            raise OSError("power cut")
        real(*args)

    monkeypatch.setattr(folders_move, "_move_device", stops)
    assert "power cut" in folders_move.run_if_needed(modules, old["data"])
    assert not (modules / "folders.json").exists()
    assert (modules / folders_move.STATE).is_file()
    monkeypatch.setattr(folders_move, "_move_device", real)
    assert folders_move.run_if_needed(modules, old["data"]) == ""
    assert (modules / "folders.json").is_file()
    assert len(list((old["data"] / "backup").iterdir())) == 1  # one backup
    assert _device(modules / "Twin Stick (2)")["id"] == _key(G4)
    assert _srcs(_module(modules / "T.16000M"))[2] == "pictures/lib.png"
    assert not (modules / folders_move.STATE).exists()


def test_the_bindings_setting_is_registered_for_the_move() -> None:
    folders_move.register_setting()
    assert Configuration().exists(*folders_move.BINDINGS)


def test_the_move_refuses_the_real_data_folder_under_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard (agreed with A8a): with GREMLIN_TESTS=1 a data folder under the
    real %USERPROFILE%\\Gremlin Platforms is refused, nothing moved."""
    real = tmp_path / "profile" / "Gremlin Platforms"
    modules = real / "modules"
    _put(modules / "stick.json", _doc("Stick", G1))
    monkeypatch.setattr(folders_move, "_REAL_DATA", [real])
    monkeypatch.setenv("GREMLIN_TESTS", "1")
    before = _files(real)
    assert folders_move.run_if_needed(modules, real) == folders_move.REFUSED
    assert _files(real) == before


def test_the_guard_knows_the_real_folder_and_tests_never_use_it() -> None:
    """The guard's real folder comes from USERPROFILE as it was at import;
    the modules folder the tests' own app start moves is never inside it."""
    import os

    profile = os.environ.get("USERPROFILE", "")
    assert profile
    assert folders_move._REAL_DATA[0] == Path(profile) / "Gremlin Platforms"
    assert not any(
        folders_move._inside(store.folder(), real) for real in folders_move._REAL_DATA
    )


def test_the_start_shows_a_failed_move_once_and_goes_on(
    monkeypatch: pytest.MonkeyPatch, _no_message_boxes: list[tuple]
) -> None:
    """The call site (joystick_gremlin, before the device scan): a failure
    is shown in one message box; the start is not stopped."""
    import joystick_gremlin

    # Outside tests (under tests the reason is only logged, so an off-screen
    # program never waits for a click).
    monkeypatch.delenv("GREMLIN_TESTS", raising=False)
    monkeypatch.setattr(folders_move, "run_if_needed", lambda *_a: "disk full")
    joystick_gremlin._move_to_device_folders()
    assert len(_no_message_boxes) == 1
    assert "disk full" in _no_message_boxes[0][0]

    def raises(*_a: object) -> str:
        raise RuntimeError("bad")

    monkeypatch.setattr(folders_move, "run_if_needed", raises)
    joystick_gremlin._move_to_device_folders()
    assert len(_no_message_boxes) == 2


def test_the_start_runs_the_move_before_the_device_scan() -> None:
    import inspect

    import joystick_gremlin

    source = inspect.getsource(joystick_gremlin.JoystickGremlinApp.__init__)
    move = source.index("_move_to_device_folders()")
    assert source.index("apply_log_level()") < move
    assert move < source.index("joystick_devices_initialization()")
    assert move < source.index("purge_unused()")


def test_under_tests_a_failed_move_is_logged_not_shown(
    monkeypatch: pytest.MonkeyPatch, _no_message_boxes: list[tuple]
) -> None:
    """Under tests (GREMLIN_TESTS=1) or when refused, the reason is logged and
    no message box waits for a click (an off-screen program would hang)."""
    import joystick_gremlin

    monkeypatch.setenv("GREMLIN_TESTS", "1")
    monkeypatch.setattr(folders_move, "run_if_needed", lambda *_a: "disk full")
    joystick_gremlin._move_to_device_folders()
    monkeypatch.delenv("GREMLIN_TESTS")
    monkeypatch.setattr(
        folders_move, "run_if_needed", lambda *_a: folders_move.REFUSED
    )
    joystick_gremlin._move_to_device_folders()
    assert _no_message_boxes == []
