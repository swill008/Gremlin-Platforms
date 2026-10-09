# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library, agent FD: a Device Pack import onto a stick keeps a
"before Device Pack" autosave first (10 S16-S17), Delete Device's autosave
holds a never-saved open profile's bindings (10 S18, 03 S91), and the
library folder is chosen in Device Library Settings only, not Options
(10 S37, 01 S124)."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib

import pytest

from gremlin import device_library as library
from gremlin import shared_state
from gremlin.modules import registry, store
from gremlin.profile import Profile
from gremlin.ui import device_pack, hardware_profile, option


class _FakeLibrary:
    """Records library.autosave calls; answers ok (or the given failure)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.answer: dict = {"ok": True, "error": "", "warnings": [], "notes": []}

    def autosave(self, name: str, guid: str, trigger: str, reason: str,
                 profiles: list[pathlib.Path]) -> dict:
        self.calls.append((name, guid, trigger, reason, list(profiles)))
        return dict(self.answer)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeLibrary:
    fake = _FakeLibrary()
    monkeypatch.setattr(library, "autosave", fake.autosave)
    return fake


@pytest.fixture
def pack(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> dict:
    """A pack file on disk; apply_zip recorded instead of run."""
    zip_path = tmp_path / "Hornet stick.zip"
    zip_path.write_bytes(b"PK")
    applied: list[tuple] = []

    def apply(path: pathlib.Path, target: str, selection: dict,
              *args: object, **kwargs: object) -> dict:
        applied.append((pathlib.Path(path), target))
        return {"ok": True, "report": "Imported."}

    monkeypatch.setattr(device_pack, "apply_zip", apply)
    monkeypatch.setattr(device_pack, "_match_pack_device",
                        lambda name: {"name": name, "guid": "{GUID-R}"})
    monkeypatch.setattr(store, "direction_for", lambda name, guid="": "source")
    return {"zip": zip_path, "applied": applied}


def _import(pack: dict, target: str = "Stick R") -> dict:
    selection = json.dumps({"items": ["in.claim"], "outputs": {}})
    cls = hardware_profile.HardwareProfile
    url = pack["zip"].as_uri()
    return json.loads(cls.importPack(cls.__new__(cls), url, target, selection))


# --- Gap 3: Device Pack import ------------------------------------------------------


def test_pack_import_keeps_a_before_device_pack_autosave_first(
    pack: dict, fake: _FakeLibrary, monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    profile = Profile()
    profile.fpath = tmp_path / "open.xml"
    monkeypatch.setattr(shared_state, "current_profile", profile)
    assert _import(pack)["ok"]
    assert fake.calls == [(
        "Stick R", "{GUID-R}", "pack", "Autosave: before Device Pack Hornet stick",
        [tmp_path / "open.xml"],
    )]
    assert pack["applied"] == [(pack["zip"], "Stick R")]


def test_pack_import_with_a_never_saved_profile_autosaves_it(
    pack: dict, fake: _FakeLibrary, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    assert _import(pack)["ok"]
    assert fake.calls[0][4] == [pathlib.Path("")]


def test_pack_import_refused_when_the_autosave_fails(
    pack: dict, fake: _FakeLibrary, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    fake.answer = {"ok": False, "error": "The autosave could not be kept: disk full."}
    info = _import(pack)
    assert not info["ok"]
    assert "disk full" in info["error"]
    assert pack["applied"] == []  # nothing imported


def test_pack_import_onto_an_output_keeps_no_stick_autosave(
    pack: dict, fake: _FakeLibrary, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # S16: the autosave is of a stick; a vJoy pack onto a vJoy has none.
    monkeypatch.setattr(store, "direction_for", lambda name, guid="": "dest")
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    assert _import(pack, "vJoy 1")["ok"]
    assert fake.calls == []
    assert pack["applied"] == [(pack["zip"], "vJoy 1")]


# --- Gap 8: Delete Device with a never-saved profile --------------------------------


def test_delete_device_with_a_never_saved_profile_autosaves_its_bindings(
    fake: _FakeLibrary, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    maps = tmp_path / "modules"
    maps.mkdir()
    (maps / "stick_r.json").write_text(json.dumps({"claim": {"buttons": [1]}}),
                                       encoding="utf-8")
    monkeypatch.setattr(store, "folder", lambda: maps)
    monkeypatch.setattr(store, "users_of", lambda slug: set())
    monkeypatch.setattr(store, "bindings", lambda: {})
    monkeypatch.setattr(store, "set_bindings", lambda data: None)
    monkeypatch.setattr(registry, "guid_for_name", lambda name: "")
    monkeypatch.setattr(hardware_profile, "_profile_running", lambda: False)
    monkeypatch.setattr(hardware_profile, "_device_stays_listed", lambda *_a: False)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    assert json.loads(hardware_profile.delete_device("Stick R", ""))["ok"]
    assert fake.calls[0][2:] == (
        "deleted", "Autosave: stick deleted", [pathlib.Path("")]
    )


def test_no_open_profile_gives_no_profile_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shared_state, "current_profile", None)
    assert hardware_profile._open_profile_paths() == []


# --- Gap 7: the library folder is not in Options --------------------------------------


def test_options_do_not_show_the_library_folder() -> None:
    library._register_setting()
    keys = [
        key
        for _section, groups in option.main_layout()
        for _title, entries in groups
        for key in entries
    ]
    assert ("global", "files", library.SETTING) not in keys
