# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""What the history records, at the three places data is saved.

Profile saves (Profile.to_xml): an entry per input whose actions changed,
compared by what they do, not by their ids (an editor's OK gives new ids);
an entry per other part that changed; and the whole profile, compressed.
Module files (module_file.write_text, the import replace, deletes): the file
before and after with its pictures; a Button Map-only save is filed under
Button Map; a change to the map's view only isn't kept. Settings
(Configuration.save_now): the user's own settings that changed, not window
places or what the program remembers for itself.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, history_profile, plugin_manager, shared_state, util
from gremlin.modules import module_file
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType

_STICK = uuid.UUID("33333333-4444-5555-6666-777777777777")


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    yield folder
    _settle()


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


@pytest.fixture
def profile(store: Path) -> Iterator[Profile]:
    made = Profile()
    made.device_database.devices[_STICK] = DeviceInfo(_STICK, "Test Stick")
    shared_state.current_profile = made
    yield made
    shared_state.current_profile = None


def _map(profile: Profile, button: int, out: int, mode: str = "Default") -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _titles(entries: list[dict], kind: str) -> list[str]:
    return [e["title"] for e in entries if e["kind"] == kind]


def test_a_profile_save_records_each_changed_input(
    profile: Profile, tmp_path: Path
) -> None:
    path = tmp_path / "p.xml"
    _map(profile, 1, 1)
    profile.to_xml(path)
    _map(profile, 2, 2)
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    item.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id = 9
    profile.to_xml(path)
    entries = _settle()
    assert set(_titles(entries, "input")) == {
        "Added the actions of Test Stick Button 1 in Default",
        "Changed the actions of Test Stick Button 1 in Default",
        "Added the actions of Test Stick Button 2 in Default",
    }
    changed = next(e for e in entries if e["title"].startswith("Changed the actions"))
    assert (
        changed["subject"]["inputId"] == "1" and changed["subject"]["mode"] == "Default"
    )
    assert "<input>" in changed["before"]["input"] and changed["before"]["actions"]
    saves = _titles(entries, "profile")
    assert saves[0] == "Saved p.xml (2 inputs)"


def test_new_ids_with_the_same_actions_are_no_change(
    profile: Profile, tmp_path: Path
) -> None:
    path = tmp_path / "p.xml"
    _map(profile, 1, 1)
    profile.to_xml(path)
    # As an editor's OK does: the same action under new ids.
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    item.action_sequences.clear()
    _map(profile, 1, 1)
    profile.to_xml(path)
    entries = _settle()
    assert _titles(entries, "input") == [
        "Added the actions of Test Stick Button 1 in Default"
    ]


def test_other_parts_and_the_whole_profile(profile: Profile, tmp_path: Path) -> None:
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    first = profile._saved_snapshot
    profile.modes.add_mode("Combat")
    profile.to_xml(path)
    entries = _settle()
    assert "Changed the modes" in _titles(entries, "section")
    save = next(e for e in entries if e["kind"] == "profile")
    assert history_profile.unpack_text(save["before"]["packed"]) == first
    assert (
        history_profile.unpack_text(save["after"]["packed"]) == profile._saved_snapshot
    )


def test_a_module_save_is_kept_with_its_pictures(store: Path) -> None:
    modules = util.modules_dir()
    (modules / "test_stick").mkdir(parents=True, exist_ok=True)
    (modules / "test_stick" / "photo.png").write_bytes(b"photo")
    path = modules / "test_stick.json"
    module_file.write_json(path, {"device": "Test Stick", "claim": {"buttons": [1]}})
    module_file.write_json(
        path,
        {
            "device": "Test Stick",
            "claim": {"buttons": [1]},
            "calibration": {"1": [0, 1, 2, 3, True]},
        },
    )
    module_file.write_json(
        path,
        {
            "device": "Test Stick",
            "claim": {"buttons": [1]},
            "calibration": {"1": [0, 1, 2, 3, True]},
            "image": "test_stick/photo.png",
            "nodes": [{"id": "a"}],
        },
    )
    entries = _settle()
    titles = [e["title"] for e in entries]
    assert titles[0] == "Saved Test Stick: Button Map, Button Map photo"
    assert entries[0]["area"] == "button-map"
    assert entries[0]["after"]["pictures"][0]["ref"] == "test_stick/photo.png"
    assert history.kept_file(entries[0]["after"]["pictures"][0]["keptFile"])
    assert titles[1] == "Saved Test Stick: calibration"
    assert entries[1]["area"] == "modules"


def test_the_maps_view_alone_is_not_kept(store: Path) -> None:
    path = util.modules_dir() / "test_stick.json"
    module_file.write_json(path, {"device": "Test Stick", "ui": {"viewPct": 80}})
    _settle()
    before = len(history.entries())
    module_file.write_json(path, {"device": "Test Stick", "ui": {"viewPct": 50}})
    assert len(_settle()) == before


def test_other_files_are_not_kept(store: Path, tmp_path: Path) -> None:
    module_file.write_json(tmp_path / "elsewhere.json", {"a": 1})
    module_file.write_json(tmp_path / "elsewhere.json", {"a": 2})
    assert _settle() == []


def test_a_delete_keeps_the_file_and_its_pictures(store: Path) -> None:
    from gremlin import history_modules

    modules = util.modules_dir()
    (modules / "gone").mkdir(parents=True, exist_ok=True)
    (modules / "gone" / "photo.png").write_bytes(b"gone photo")
    path = modules / "gone.json"
    path.write_text(
        json.dumps({"device": "Gone", "image": "gone/photo.png"}), encoding="utf-8"
    )
    history_modules.note_delete(path)
    path.unlink()
    (modules / "gone" / "photo.png").unlink()
    entry = _settle()[0]
    assert entry["kind"] == "delete"
    assert entry["title"] == "Deleted the module file of Gone"
    assert json.loads(entry["before"]["text"])["device"] == "Gone"
    kept = entry["before"]["pictures"][0]["keptFile"]
    assert history.kept_file(kept).read_bytes() == b"gone photo"


def test_settings_the_user_chooses_are_kept(
    store: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gremlin import config
    from gremlin.types import PropertyType

    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    cfg = config.Configuration()
    cfg.register(
        "global",
        "history",
        "keep-days",
        PropertyType.Int,
        90,
        "",
        {"min": 1, "max": 3650},
        True,
    )
    cfg.register(
        "global",
        "internal",
        "window-x",
        PropertyType.Int,
        0,
        "",
        {"min": -100000, "max": 100000},
        False,
    )
    cfg.save_now()
    cfg._history_view = cfg._settings_view()
    cfg.set("global", "history", "keep-days", 30)
    cfg.set("global", "internal", "window-x", 400)
    cfg.save_now()
    entries = [e for e in _settle() if e["area"] == "settings"]
    assert [e["title"] for e in entries] == ["Changed Keep days"]
    assert entries[0]["before"] == {"global/history/keep-days": "90"}
    assert entries[0]["after"] == {"global/history/keep-days": "30"}
