# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Restore from the History (gremlin.ui.history_model).

Restore puts back the version before or after a change, through the normal
save paths, so it is itself a new entry. An input's actions go back into
the open profile, unsaved (only when that profile is open). A module file
(with its pictures) and settings are saved at once. A whole profile is
written as a copy next to it. Filters match a device id however it is
written (case, braces).
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, plugin_manager, shared_state, util
from gremlin.modules import module_file
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType
from gremlin.ui import history_model

_STICK = uuid.UUID("44444444-5555-6666-7777-888888888888")


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    yield folder
    _settle()
    shared_state.current_profile = None


def _map(profile: Profile, button: int, out: int) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _target(profile: Profile, button: int) -> int | None:
    item = profile.get_input_item(_STICK, InputType.JoystickButton, button, "Default")
    if item is None or not item.action_sequences:
        return None
    return item.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id


def _saved_profile(tmp_path: Path) -> tuple[Profile, Path]:
    profile = Profile()
    profile.device_database.devices[_STICK] = DeviceInfo(_STICK, "Test Stick")
    shared_state.current_profile = profile
    path = tmp_path / "p.xml"
    profile.fpath = path
    _map(profile, 1, 1)
    profile.to_xml(path)
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    item.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id = 7
    profile.to_xml(path)
    return profile, path


def test_an_input_goes_back_into_the_open_profile(store: Path, tmp_path: Path) -> None:
    profile, _path = _saved_profile(tmp_path)
    entry = next(e for e in _settle() if e["title"].startswith("Changed the actions"))
    detail = history_model.describe(entry)
    assert "Map to vJoy" in detail["before"] and "vjoy input id 1" in detail["before"]
    result = history_model.restore(entry["id"], "before")
    assert result["ok"], result
    assert _target(profile, 1) == 1
    assert profile.has_unsaved_changes()
    assert set(profile.library._actions) >= profile.actions_in_use()


def test_an_input_needs_its_profile_open(store: Path, tmp_path: Path) -> None:
    _saved_profile(tmp_path)
    entry = next(e for e in _settle() if e["title"].startswith("Changed the actions"))
    other = Profile()
    other.fpath = tmp_path / "other.xml"
    shared_state.current_profile = other
    result = history_model.restore(entry["id"], "before")
    assert result == {"ok": False, "message": "Open p.xml first."}


def test_a_whole_profile_is_written_as_a_copy(store: Path, tmp_path: Path) -> None:
    _saved_profile(tmp_path)
    save = next(e for e in _settle() if e["kind"] == "profile")
    result = history_model.restore(save["id"], "before")
    assert result["ok"], result
    copies = list(tmp_path.glob("p (history *).xml"))
    assert len(copies) == 1
    assert copies[0].read_bytes().startswith(b"\xef\xbb\xbf")


def test_a_module_file_and_its_picture_go_back(store: Path) -> None:
    modules = util.modules_dir()
    (modules / "restore_stick").mkdir(parents=True, exist_ok=True)
    photo = modules / "restore_stick" / "photo.png"
    photo.write_bytes(b"first photo")
    path = modules / "restore_stick.json"
    module_file.write_json(
        path, {"device": "Restore Stick", "image": "restore_stick/photo.png"}
    )
    _settle()
    photo.write_bytes(b"second photo")
    module_file.write_json(
        path,
        {
            "device": "Restore Stick",
            "image": "restore_stick/photo.png",
            "calibration": {"1": [0, 1, 2, 3, True]},
        },
    )
    entry = _settle()[0]
    assert entry["title"] == "Saved Restore Stick: calibration"
    result = history_model.restore(entry["id"], "before")
    assert result["ok"], result
    assert "calibration" not in json.loads(path.read_text(encoding="utf-8"))
    # The picture as it was with that version.
    assert photo.read_bytes() == b"first photo"
    # Restore is itself a change.
    assert _settle()[0]["title"] == "Saved Restore Stick: calibration"
    assert _settle()[0]["id"] != entry["id"]


def test_settings_go_back(
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
    cfg.set("global", "history", "keep-days", 30)
    entry_id = history.record(
        "settings",
        "Changed Keep days",
        {"keys": ["global/history/keep-days"]},
        {"global/history/keep-days": "90"},
        {"global/history/keep-days": "30"},
    )
    _settle()
    shown = history_model.describe(history.entry(entry_id))
    assert shown["before"] == "Days to keep changes: 90"
    assert history_model.restore(entry_id, "before")["ok"]
    assert cfg.value("global", "history", "keep-days") == 90


def test_filters_match_a_device_id_however_written() -> None:
    entry = {"area": "profile", "subject": {"deviceId": "abcd-ef", "mode": "Default"}}
    assert history_model._matches(entry, {"deviceId": "{ABCD-EF}", "mode": "default"})
    assert not history_model._matches(entry, {"deviceId": "{ABCD-00}"})
    assert history_model._matches(entry, {"area": "profile"})
    assert not history_model._matches(entry, {"area": "settings"})
