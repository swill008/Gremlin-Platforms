# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Startup Mode has no Use Heuristic: Last Active or a named mode (04 S46,
S52, S63, Q2; D-04-LAST-ACTIVE). Profiles go through the real load path."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
from xml.etree import ElementTree

import pytest

import gremlin.mode_manager
from gremlin.config import Configuration
from gremlin.profile import Profile

_XML = """<?xml version="1.0" ?>
<profile version="14">
    <settings>
        <startup-mode>{startup}</startup-mode>
        <macro-default-delay>0.05</macro-default-delay>
    </settings>
    <inputs/>
    <library/>
    <modes>
        <mode>Test Mode</mode>
        <mode parent="Test Mode">Default</mode>
        <mode>Zulu</mode>
    </modes>
    <plugins/>
</profile>
"""


def _load(tmp_path: pathlib.Path, startup: str) -> Profile:
    fpath = tmp_path / "start_mode.xml"
    fpath.write_text(_XML.format(startup=startup), encoding="utf-8")
    p = Profile()
    p.from_xml(str(fpath))
    return p


def _stored_last_mode(monkeypatch: pytest.MonkeyPatch, stored: dict[str, str]) -> None:
    original = Configuration.value

    def value(self: Configuration, section: str, group: str, name: str) -> object:
        if name == "last-mode-per-profile":
            return stored
        return original(self, section, group, name)

    monkeypatch.setattr(Configuration, "value", value)
    monkeypatch.setattr(gremlin.mode_manager, "_pending_last", {})


def test_use_heuristic_loads_as_last_active(tmp_path: pathlib.Path) -> None:
    assert _load(tmp_path, "Use Heuristic").settings.startup_mode == "Last Active"


def test_unknown_value_loads_as_last_active(tmp_path: pathlib.Path) -> None:
    assert _load(tmp_path, "No Such Mode").settings.startup_mode == "Last Active"


def test_new_profile_starts_on_last_active() -> None:
    assert Profile().settings.startup_mode == "Last Active"


def test_stored_last_mode_is_used(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = _load(tmp_path, "Use Heuristic")
    _stored_last_mode(monkeypatch, {str(p.fpath): "Zulu"})
    assert gremlin.mode_manager.resolve_start_mode(p) == "Zulu"


def test_no_record_is_top_row_of_mode_list(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Top row in Manage Modes (alphabetical, children included), not the
    first parentless mode (was Test Mode)."""
    p = _load(tmp_path, "Use Heuristic")
    _stored_last_mode(monkeypatch, {})
    assert gremlin.mode_manager.resolve_start_mode(p) == "Default"


def test_stored_mode_that_is_gone_falls_back_to_top_row(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = _load(tmp_path, "Last Active")
    _stored_last_mode(monkeypatch, {str(p.fpath): "Gone"})
    assert gremlin.mode_manager.resolve_start_mode(p) == "Default"


def test_named_mode_is_itself(tmp_path: pathlib.Path) -> None:
    assert gremlin.mode_manager.resolve_start_mode(_load(tmp_path, "Zulu")) == "Zulu"


def test_deleting_named_startup_mode_sets_last_active(tmp_path: pathlib.Path) -> None:
    p = _load(tmp_path, "Zulu")
    memo = p.modes.delete_mode("Zulu")
    assert p.settings.startup_mode == "Last Active"
    p.modes.restore_mode(memo)
    assert p.settings.startup_mode == "Zulu"


def test_save_writes_last_active(tmp_path: pathlib.Path) -> None:
    p = _load(tmp_path, "Use Heuristic")
    out = tmp_path / "saved.xml"
    p.to_xml(out)
    node = ElementTree.parse(out).getroot().find("./settings/startup-mode")
    assert node is not None and node.text == "Last Active"
