# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Recovery copies of unsaved Button Map edits (autosave)."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib

import pytest

from gremlin.ui import hardware_profile


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(hardware_profile, "_maps_dir", lambda: tmp_path)
    monkeypatch.setattr(
        hardware_profile, "resolve_module_slug", lambda name, guid="": "test_stick"
    )
    return hardware_profile.HardwareProfile()


def _payload() -> str:
    return json.dumps(
        {"image": "x.png", "photo": {"scale": 1}, "nodes": [{"id": "b1"}]}
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
    # Beside the module files, never in place of one.
    assert (tmp_path / "recovery" / "test_stick.json").is_file()
    assert not (tmp_path / "test_stick.json").exists()
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
    (tmp_path / "recovery").mkdir()
    (tmp_path / "recovery" / "test_stick.json").write_text("{", encoding="utf-8")
    assert profile.loadRecovery("Test Stick") == ""
