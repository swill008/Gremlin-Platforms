# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map layout templates: save, apply, rename, share, delete."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib

import pytest
from PySide6 import QtCore

from gremlin.modules import store
from gremlin.ui import hardware_profile

NODES = json.dumps([{"id": "b1", "kind": "btn", "hwId": 1}])


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(store, "folder", lambda: tmp_path / "maps")
    return hardware_profile.HardwareProfile()


def _url(path: pathlib.Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def test_save_list_and_read_back(profile: hardware_profile.HardwareProfile) -> None:
    assert profile.templates() == []
    assert profile.saveTemplate("Evo: right", NODES, "VKB EVO R")
    assert profile.templateExists("Evo: right")
    rows = profile.templates()
    assert [(r["name"], r["count"]) for r in rows] == [("Evo: right", 1)]
    assert json.loads(profile.templateNodes("Evo: right"))[0]["id"] == "b1"
    # Saving under the same name replaces it.
    assert profile.saveTemplate("Evo: right", NODES, "VKB EVO R")
    assert len(profile.templates()) == 1


def test_nothing_to_save(profile: hardware_profile.HardwareProfile) -> None:
    assert not profile.saveTemplate("Empty", "[]", "x")
    assert not profile.saveTemplate("   ", NODES, "x")
    assert not profile.saveTemplate("Bad", "not json", "x")
    assert profile.templates() == []


def test_rename_and_delete(profile: hardware_profile.HardwareProfile) -> None:
    profile.saveTemplate("One", NODES, "x")
    profile.saveTemplate("Two", NODES, "x")
    assert not profile.renameTemplate("One", "Two")  # taken
    assert profile.renameTemplate("One", "Three")
    assert [r["name"] for r in profile.templates()] == ["Three", "Two"]
    assert profile.deleteTemplate("Three")
    assert not profile.deleteTemplate("Three")
    assert [r["name"] for r in profile.templates()] == ["Two"]


def test_export_and_import(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    profile.saveTemplate("Shared", NODES, "x")
    out = tmp_path / "shared.json"
    assert profile.exportTemplate("Shared", _url(out))
    # Importing a name already there numbers it.
    assert profile.importTemplate(_url(out)) == "Shared 2"
    assert profile.importTemplate(_url(out)) == "Shared 3"
    not_template = tmp_path / "other.json"
    not_template.write_text("{}", encoding="utf-8")
    assert profile.importTemplate(_url(not_template)) == ""
    assert profile.importTemplate(_url(tmp_path / "missing.json")) == ""
