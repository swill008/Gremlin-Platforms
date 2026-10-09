# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library, agent DD: Delete Device and Delete File keep their
autosave in the Device Library (03 S62, S90-S91; 08 S86, S88; 10 S16-S21),
and the deleted devices folder is gone (01 S124, 10 S37,
D-10-NO-DELETED-FOLDER)."""

from __future__ import annotations

import sys

sys.path.append(".")

import inspect
import json
import pathlib

import pytest

from gremlin import device_library as library
from gremlin import shared_state, util
from gremlin.modules import registry, store
from gremlin.profile import Profile
from gremlin.ui import hardware_profile, option


class _FakeLibrary:
    """Records library.autosave calls; answers ok (or the given failure)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.answer: dict | Exception = {"ok": True, "error": "", "warnings": [],
                                         "notes": []}

    def autosave(self, name: str, guid: str, trigger: str, reason: str,
                 profiles: list[pathlib.Path]) -> dict:
        self.calls.append((name, guid, trigger, reason, list(profiles)))
        if isinstance(self.answer, Exception):
            raise self.answer
        return dict(self.answer)


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    maps = tmp_path / "modules"
    maps.mkdir()
    monkeypatch.setattr(store, "folder", lambda: maps)
    monkeypatch.setattr(store, "users_of", lambda slug: set())
    monkeypatch.setattr(store, "bindings", lambda: {})
    monkeypatch.setattr(store, "set_bindings", lambda data: None)
    monkeypatch.setattr(registry, "guid_for_name", lambda name: "")
    monkeypatch.setattr(hardware_profile, "_profile_running", lambda: False)
    monkeypatch.setattr(hardware_profile, "_device_stays_listed", lambda *_a: False)
    return maps


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeLibrary:
    fake = _FakeLibrary()
    monkeypatch.setattr(library, "autosave", fake.autosave)
    return fake


@pytest.fixture
def open_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Profile:
    profile = Profile()
    profile.fpath = tmp_path / "open.xml"
    monkeypatch.setattr(shared_state, "current_profile", profile)
    return profile


def _stick(modules: pathlib.Path) -> pathlib.Path:
    path = modules / "stick_r.json"
    path.write_text(json.dumps({"claim": {"buttons": [1]}}), encoding="utf-8")
    return path


# --- Delete Device ---------------------------------------------------------------


def test_delete_device_has_no_save_a_copy_choice() -> None:
    # 10 S21, 03 S90: no "Save a copy" question.
    params = list(inspect.signature(hardware_profile.delete_device).parameters)
    assert params == ["device_name", "guid"]


def test_delete_device_keeps_a_stick_deleted_autosave_first(
    modules: pathlib.Path, fake: _FakeLibrary, open_profile: Profile,
    tmp_path: pathlib.Path,
) -> None:
    path = _stick(modules)
    result = json.loads(hardware_profile.delete_device("Stick R", ""))
    assert result["ok"], result
    assert result["autosaved"] is True
    # The open profile's bindings go into the autosave (10 S18).
    assert fake.calls == [
        ("Stick R", "", "deleted", "Autosave: stick deleted", [tmp_path / "open.xml"])
    ]
    assert not path.exists()
    # Nothing written to a deleted devices folder (D-10-NO-DELETED-FOLDER).
    assert not list(tmp_path.rglob("deleted devices"))


def test_delete_device_refused_when_the_autosave_fails(
    modules: pathlib.Path, fake: _FakeLibrary, open_profile: Profile,
) -> None:
    path = _stick(modules)
    fake.answer = {"ok": False, "error": "The autosave could not be kept: disk full"}
    result = json.loads(hardware_profile.delete_device("Stick R", ""))
    # 10 S20, 03 S91: nothing is deleted, and it says so.
    assert result["ok"] is False
    assert "not deleted" in result["error"] and "disk full" in result["error"]
    assert path.exists()


def test_delete_device_refused_when_the_autosave_raises(
    modules: pathlib.Path, fake: _FakeLibrary, open_profile: Profile,
) -> None:
    path = _stick(modules)
    fake.answer = OSError("read back failed")
    result = json.loads(hardware_profile.delete_device("Stick R", ""))
    assert result["ok"] is False
    assert "The autosave could not be kept" in result["error"]
    assert "read back failed" in result["error"]
    assert path.exists()


def test_delete_device_with_an_unsaved_profile_passes_the_open_mark(
    modules: pathlib.Path, fake: _FakeLibrary, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 10 S18: the never-saved open profile's bindings are in the autosave
    # (Path("") is the Library's mark for it).
    _stick(modules)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    assert json.loads(hardware_profile.delete_device("Stick R", ""))["ok"]
    assert fake.calls[0][2:] == (
        "deleted", "Autosave: stick deleted", [pathlib.Path("")]
    )


def test_the_delete_device_slot_takes_no_save_a_copy() -> None:
    from gremlin.ui.module_model import ModuleListModel

    params = list(inspect.signature(ModuleListModel.deleteDevice).parameters)
    assert params == ["self", "device_name", "guid"]


# --- Delete File -----------------------------------------------------------------


def test_delete_file_keeps_a_module_file_deleted_autosave(
    modules: pathlib.Path, fake: _FakeLibrary, tmp_path: pathlib.Path,
) -> None:
    path = _stick(modules)
    assert hardware_profile.delete_module_file("Stick R", "") == ""
    # 03 S62, 08 S88: setup only, no profiles.
    assert fake.calls == [
        ("Stick R", "", "module_file", "Autosave: module file deleted", [])
    ]
    assert not path.exists()
    assert not list(tmp_path.rglob("deleted devices"))


def test_delete_file_refused_when_the_autosave_fails(
    modules: pathlib.Path, fake: _FakeLibrary,
) -> None:
    path = _stick(modules)
    fake.answer = {"ok": False, "error": "The autosave could not be kept: no room"}
    message = hardware_profile.delete_module_file("Stick R", "")
    assert message.startswith("The module file was not deleted.")
    assert "no room" in message
    assert path.exists()


def test_delete_file_used_by_another_stick_keeps_no_autosave(
    modules: pathlib.Path, fake: _FakeLibrary, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _stick(modules)
    monkeypatch.setattr(store, "other_users", lambda slug, name, guid="": {"x"})
    assert hardware_profile.delete_module_file("Stick R", "") == (
        "Another stick is using this file."
    )
    assert fake.calls == [] and path.exists()


# --- the real Device Library ------------------------------------------------------


def test_a_deleted_stick_shows_in_the_device_library(
    modules: pathlib.Path, open_profile: Profile, tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real path: Delete Device through library.autosave into a Library
    in a temp folder; the stick is listed as Deleted with its autosave."""
    lib = tmp_path / "device library"
    monkeypatch.setattr(library, "folder", lambda: lib)
    _stick(modules)
    result = json.loads(hardware_profile.delete_device("Stick R", ""))
    assert result["ok"], result
    found = library.find_device("Stick R", "")
    assert found is not None, library.devices()
    assert found["state"] == "deleted"
    names = [setup["name"] for setup in found["setups"]]
    assert "Autosave: stick deleted" in names, found


# --- no deleted devices folder ----------------------------------------------------


def test_there_is_no_deleted_devices_folder(tmp_path: pathlib.Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    for gone in ("deleted_devices_dir",):
        assert not hasattr(util, gone)
    for gone in ("deleted_dir", "keep_deleted_copy", "deleted_pack_path",
                 "write_deleted_pack", "deleted_items"):
        assert not hasattr(store, gone), gone
    assert "keep_copy" not in inspect.signature(store.delete).parameters
    # ensure_data_folders doesn't make one.
    monkeypatch.setattr(util, "data_folder", lambda: str(tmp_path))
    monkeypatch.setattr(util, "_configured_child",
                        lambda key, name: _make(tmp_path / name))
    monkeypatch.setattr(util, "_child_dir", lambda name: _make(tmp_path / name))
    util.ensure_data_folders()
    assert not (tmp_path / "deleted devices").exists()


def _make(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_options_folders_do_not_list_deleted_devices() -> None:
    # 01 S124, 10 S37.
    keys = [
        key
        for section, groups in option.main_layout()
        if section == "Folders"
        for _title, entries in groups
        for key in entries
    ]
    assert ("global", "files", "modules-folder") in keys
    assert ("global", "files", "deleted-devices-folder") not in keys
