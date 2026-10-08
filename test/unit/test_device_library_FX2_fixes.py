# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Device Library last fix round (agent FX2), from the second re-trace:

- Undo/Redo of a Swap touches only the profiles the Swap changed (S28, S41);
- Undo on a twin that is unplugged never writes the other twin (S41);
- a Swap whose profiles all failed puts the module files back (S26);
- user text names the stick as Home does, twins with their short id (S17);
- missing Logical Device notes come from the profile changed (S24);
- a twin's pack lands under that twin (S35);
- Move… into a folder with other things touches only the Library's (S36).

On the real Library store, the real Device Pack import and the real
profile Batch."""

# ruff: noqa: F811

from __future__ import annotations

import json
import pathlib
import shutil
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

import gremlin.profile
from gremlin import (
    device_aliases,
    device_initialization,
    library_copy,
    library_swap,
    shared_state,
)
from gremlin import device_library as library
from gremlin.modules import store
from gremlin.ui import device_names, device_pack  # noqa: F401
from test.unit.test_device_library_FX_gaps import (  # noqa: F401 - fixtures
    _real_library,
    _second_twin,
    _twin_doc,
    renamed,
)
from test.unit.test_device_library_LC_copy import (  # noqa: F401 - the fixture
    _REAL,
    _own_path,
    lib,
)
from test.unit.test_device_library_LW_swap import (  # noqa: F401 - the fixture
    ALL,
    LEFT,
    LEFT_ID,
    RIGHT,
    RIGHT_ID,
    _where,
    sticks,
)
from test.unit.test_device_pack_import import (  # noqa: F401 - the fixture
    pack,
)
from test.unit.test_twin_devices import (  # noqa: F401 - the fixtures
    _app,
    _twin,
    _twin_guid,
    twins,
)
from test.unit.test_twin_devices import _module as _twin_module


def _real(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    for name in ("autosave", "set_last_change", "last_change", "pack_path", "devices"):
        monkeypatch.setattr(library, name, _REAL[name])
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")


def _open_saved(xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    profile = gremlin.profile.Profile()
    profile.from_xml(xml_dir / "profile_auto_mapper.xml")
    monkeypatch.setattr(shared_state, "current_profile", profile)
    return Path(profile.fpath)


def _read(path: Path) -> gremlin.profile.Profile:
    profile = gremlin.profile.Profile(bind=False)
    profile.from_xml(path)
    return profile


def _unwritable(monkeypatch: pytest.MonkeyPatch, path: Path) -> dict:
    """Saving this profile fails (a read-only file, a full disk) while
    the returned flag's "on" is True."""
    real = gremlin.profile.Profile.to_xml
    flag = {"on": True}

    def to_xml(
        self: gremlin.profile.Profile, fname: object, *a: object, **k: object
    ) -> object:
        if flag["on"] and Path(str(fname)) == path:
            raise OSError("access denied")
        return real(self, fname, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(gremlin.profile.Profile, "to_xml", to_xml)
    from gremlin import library_profiles

    saver = getattr(library_profiles, "save_profile", None)
    if saver is not None:

        def save(profile: gremlin.profile.Profile, fname: Path) -> None:
            if flag["on"] and Path(str(fname)) == path:
                raise OSError("access denied")
            saver(profile, fname)

        monkeypatch.setattr(library_profiles, "save_profile", save)
    return flag


# --- Item 1: Undo of a Swap only touches what the Swap changed (S28, S41) ---


def test_undo_of_a_swap_leaves_a_profile_the_swap_left(
    renamed: dict,
    xml_dir: pathlib.Path,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _real(monkeypatch, tmp_path)
    opened = _open_saved(xml_dir, monkeypatch)
    other = tmp_path / "other.xml"
    shutil.copyfile(xml_dir / "profile_auto_mapper.xml", other)
    before = other.read_bytes()
    stuck = _unwritable(monkeypatch, other)  # can't be saved now
    result = library_swap.swap(LEFT, RIGHT, ["bindings"], [opened, other])
    assert result["ok"], result
    assert library.last_change()["detail"]["profiles"] == [str(opened)]
    assert other.read_bytes() == before
    # Writable at Undo time: the Swap never changed it, so Undo mustn't.
    stuck["on"] = False
    where = _where(_read(other), LEFT_ID)
    assert where
    undone = library_copy.undo_last()
    assert undone["ok"], undone
    assert other.read_bytes() == before
    assert _where(_read(other), LEFT_ID) == where
    # Redo too.
    assert library_copy.undo_last()["ok"]
    assert other.read_bytes() == before


# --- Item 4: a Swap whose profiles all failed (S26) ---


def test_a_swap_with_every_profile_failing_puts_the_module_files_back(
    renamed: dict,
    xml_dir: pathlib.Path,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _real(monkeypatch, tmp_path)
    files = (store.path_of("left").read_bytes(), store.path_of("right").read_bytes())
    bad = tmp_path / "bad.xml"
    shutil.copyfile(xml_dir / "profile_auto_mapper.xml", bad)
    _unwritable(monkeypatch, bad)
    result = library_swap.swap(LEFT, RIGHT, ALL, [bad])
    assert not result["ok"], result
    assert result["error"]
    assert any("bad.xml" in w for w in result["warnings"]), result
    assert (
        store.path_of("left").read_bytes(),
        store.path_of("right").read_bytes(),
    ) == files
    # Nothing changed, so nothing to undo.
    assert library.last_change() is None


# --- Item 5: the names the user reads (S17, S41) ---


def _aliases(monkeypatch: pytest.MonkeyPatch, names: dict[str, str]) -> None:
    def display(key: str, default: str) -> str:
        return names.get(str(key).lower(), default)

    monkeypatch.setattr(device_aliases, "display_name", display)


def test_swap_words_use_the_home_name(
    renamed: dict, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(library, "devices", _REAL["devices"])
    _aliases(monkeypatch, {LEFT_ID: "My Left"})
    result = library_swap.swap(LEFT, RIGHT, ["appearance"], [])
    assert result["ok"], result
    assert result["label"] == "Swap My Left with Right stick"
    reasons = [call[3] for call in renamed["autosave"]]
    assert reasons == [
        "Autosave: before Swap with Right stick",
        "Autosave: before Swap with My Left",
    ]


def test_swap_words_tell_twins_apart(
    renamed: dict, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(library, "devices", _REAL["devices"])
    _aliases(monkeypatch, {LEFT_ID: "T.16000M", RIGHT_ID: "T.16000M"})
    result = library_swap.swap(LEFT, RIGHT, ["appearance"], [])
    assert result["ok"], result
    assert result["label"] == "Swap T.16000M [97B77B40] with T.16000M [12345678]"


def test_copy_and_output_words_use_the_home_name(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _aliases(monkeypatch, {str(lib["guid"]).lower(): "Right stick"})
    fake = lib["fake"]
    path = lib["tmp"] / "mine.xml"
    lib["profile"].to_xml(path)
    lib["profile"].fpath = path
    done = library_copy.copy(
        lib["setup"]["key"], lib["name"], lib["guid"], ["appearance"], [], []
    )
    assert done["ok"], done
    assert fake.last["label"].endswith(" to Right stick"), fake.last
    for dev in fake.devs:  # the real list's row shows the Home name
        if dev["guid"] == lib["guid"]:
            dev["name"] = "Right stick"
    changed = library_copy.change_output(
        lib["name"], lib["guid"], {1: 2}, False, [path]
    )
    assert changed["ok"], changed
    assert fake.last["label"].startswith("Change vJoy Output of Right stick"), fake.last


# --- Item 2: Undo on an unplugged twin (S41) ---


def _unplug_twin(twins: list) -> None:
    gone = _twin_guid()
    twins[:] = [
        dev
        for dev in twins
        if str(getattr(dev.device_guid, "uuid", "")).upper() != gone
        and dev.device_guid.Data1 != _twin().device_guid.Data1
    ]
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()


def test_apply_zip_onto_an_unplugged_twin_writes_its_own_file(
    lib: dict, twins: list
) -> None:
    second = _second_twin()
    # Its file has the shared name, as a twin's file made alone has.
    _twin_module("pjoy_pro_2", "pJoy Pro", second, [7])
    _unplug_twin(twins)
    first = _own_path(lib["name"]).read_bytes()
    result = device_pack.apply_zip(
        lib["pack"],
        "pJoy Pro",
        {"items": ["in.catalog"]},
        record_undo=False,
        target_guid=second,
    )
    assert result["ok"], result
    assert _twin_doc("pjoy_pro_2")["catalog"] == {"rowHeight": 40}
    assert _own_path(lib["name"]).read_bytes() == first


def test_undo_on_an_unplugged_twin_never_writes_the_other_twin(
    lib: dict, twins: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    _real_library(lib, monkeypatch)
    second = _second_twin()
    _twin_module("pjoy_pro_2", "pJoy Pro", second, [7])
    twin_before = (store.path_of("pjoy_pro_2")).read_bytes()
    imported = library.import_pack(lib["pack"])
    assert imported["ok"], imported
    done = library_copy.copy(
        imported["setup"]["key"], "pJoy Pro (2)", second, ["appearance"], [], []
    )
    assert done["ok"], done
    assert _twin_doc("pjoy_pro_2")["catalog"] == {"rowHeight": 40}
    _unplug_twin(twins)
    first = _own_path(lib["name"]).read_bytes()
    undone = library_copy.undo_last()
    assert undone["ok"], undone
    assert _own_path(lib["name"]).read_bytes() == first
    assert store.path_of("pjoy_pro_2").read_bytes() == twin_before


# --- Item 8: Logical Device notes from the profile changed (S24) ---


# The open profile's import sends to a missing Logical Device input on purpose.
@pytest.mark.validate_off
def test_logical_notes_come_from_the_profile_changed(pack: dict) -> None:
    from gremlin.types import InputType

    other = gremlin.profile.Profile(bind=False)
    other.logical_device.create(InputType.JoystickButton, input_id=7)
    result = device_pack.apply_zip(
        pack["zip"], pack["name"], {"items": ["wire:Default"]}, other, record_undo=False
    )
    assert result["ok"], result
    assert "Logical Device inputs that don't exist" not in result["report"]
    # The open profile lacks it: said there.
    result = device_pack.apply_zip(
        pack["zip"], pack["name"], {"items": ["wire:Default"]}, record_undo=False
    )
    assert "Logical Device inputs that don't exist" in result["report"]


# --- Item 10: a twin's pack lands under that twin (S35) ---


def _pack_from(tmp: Path, name: str, guid: str) -> Path:
    path = tmp / f"{guid[:4]}.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "map.json",
            json.dumps(
                {
                    "device": name,
                    "claim": {"buttons": [1]},
                    "pack": {"exportedName": name, "exportedGuid": guid, "format": 2},
                }
            ),
        )
    return path


def test_a_twins_pack_lands_under_that_twin(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _real(monkeypatch, tmp_path)
    monkeypatch.setattr(
        library,
        "_connected",
        lambda: [("T.16000M", LEFT_ID), ("T.16000M", RIGHT_ID)],
    )
    monkeypatch.setattr(library, "_set_up", lambda: [])
    rows = library.devices()
    assert [r["guid"] for r in rows] == [LEFT_ID, RIGHT_ID] or len(rows) == 2
    out = library.import_pack(_pack_from(tmp_path, "T.16000M", RIGHT_ID))
    assert out["ok"], out
    row = next(r for r in library.devices() if r["guid"] == RIGHT_ID)
    assert [s["key"] for s in row["setups"]] == [out["setup"]["key"]]


# --- Item 11: Move… into a folder holding other things (S36, S38) ---


def test_the_library_in_a_shared_folder_touches_only_its_own(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.config import Configuration

    _real(monkeypatch, tmp_path)
    where = {"folder": tmp_path / "device library"}
    monkeypatch.setattr(library, "folder", lambda: where["folder"])

    def set_folder(self: object, *args: object) -> None:
        if args[:3] == ("global", "files", library.SETTING):
            where["folder"] = Path(str(args[3]))

    monkeypatch.setattr(Configuration, "set", set_folder)
    out = library.import_pack(_pack_from(tmp_path, "Hornet Grip", LEFT_ID))
    assert out["ok"], out
    docs = tmp_path / "Documents"
    (docs / "Empty folder").mkdir(parents=True)
    (docs / "notes.txt").write_bytes(b"x" * 5000)
    library.set_settings({"folder": str(docs)})
    assert where["folder"] == docs
    size = library.size_bytes()
    assert 0 < size < 5000
    assert library.delete(out["setup"]["key"])["ok"]
    assert (docs / "Empty folder").is_dir()
    assert (docs / "notes.txt").is_file()
    # Moving on leaves what wasn't the Library's.
    library.set_settings({"folder": str(tmp_path / "elsewhere")})
    assert (docs / "notes.txt").is_file()
    assert (docs / "Empty folder").is_dir()


def test_a_failed_move_leaves_nothing_behind(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.config import Configuration

    _real(monkeypatch, tmp_path)
    monkeypatch.setattr(Configuration, "set", lambda *a, **k: None)
    out = library.import_pack(_pack_from(tmp_path, "Hornet Grip", LEFT_ID))
    assert out["ok"], out
    target = tmp_path / "new place"
    real_sync = library._sync
    calls = {"n": 0}

    def sync(source: Path, dest: Path) -> None:
        calls["n"] += 1
        real_sync(source, dest)
        if calls["n"] == 2:
            raise OSError("disk full")

    monkeypatch.setattr(library, "_sync", sync)
    with pytest.raises(OSError):
        library.set_settings({"folder": str(target)})
    assert not (target / library.LIST_NAME).exists()
    monkeypatch.setattr(library, "_sync", real_sync)
    library.set_settings({"folder": str(target)})  # not refused now


# --- Section 6: file work runs through library_profiles.background ---


def _steps(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from gremlin import library_profiles

    names: list[str] = []

    def background(name: str, fn: Callable[..., object], *args: object) -> object:
        names.append(name)
        return fn(*args)

    monkeypatch.setattr(library_profiles, "background", background)
    return names


def test_pack_file_work_runs_in_the_background(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.config import Configuration

    _real(monkeypatch, tmp_path)
    monkeypatch.setattr(Configuration, "set", lambda *a, **k: None)
    names = _steps(monkeypatch)
    out = library.import_pack(_pack_from(tmp_path, "Hornet Grip", LEFT_ID))
    assert out["ok"], out
    assert "read Device Pack" in names and "write Device Pack" in names
    names.clear()
    saved = library.export_setup(out["setup"]["key"], tmp_path / "out" / "shared.zip")
    assert saved["ok"], saved
    assert "export Device Pack" in names
    names.clear()
    library.set_settings({"folder": str(tmp_path / "moved")})
    assert "copy Device Library" in names and "remove old Device Library" in names
