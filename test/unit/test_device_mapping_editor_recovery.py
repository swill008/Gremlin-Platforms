# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Recovery copies of unsaved device map edits (autosave)."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib

import pytest

from gremlin.modules import store
from gremlin.ui import hardware_profile
from test.unit._device_folders import ensure_dir


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    return hardware_profile.HardwareProfile()


def _payload() -> str:
    return json.dumps(
        {"nodes": [{"id": "b1"}]}
    )


def test_save_load_and_clear(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    assert profile.loadRecovery("Test Stick") == ""
    assert profile.saveRecovery("Test Stick", _payload())
    doc = json.loads(profile.loadRecovery("Test Stick"))
    assert doc["nodes"] == [{"id": "b1"}]
    assert doc["device"] == "Test Stick"
    assert doc["savedAt"]
    # In the device's folder beside its module file, never in place of it.
    assert (tmp_path / "Test Stick" / "recovery.json").is_file()
    assert not (tmp_path / "Test Stick" / "module.json").exists()
    profile.clearRecovery("Test Stick")
    assert profile.loadRecovery("Test Stick") == ""
    profile.clearRecovery("Test Stick")  # nothing left: no error


def test_rejects_what_is_not_a_layout(
    profile: hardware_profile.HardwareProfile,
) -> None:
    assert not profile.saveRecovery("Test Stick", "not json")
    assert not profile.saveRecovery("Test Stick", json.dumps({"nodes": "x"}))
    assert profile.loadRecovery("Test Stick") == ""


def test_a_broken_copy_reads_as_none(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    folder = ensure_dir(tmp_path, "Test Stick")
    (folder / "recovery.json").write_text("{", encoding="utf-8")
    assert profile.loadRecovery("Test Stick") == ""
