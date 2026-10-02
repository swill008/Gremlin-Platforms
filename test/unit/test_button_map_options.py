# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map editor options: stored with the program's settings and shown
in Options under their own section."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

from gremlin.config import Configuration
from gremlin.ui import button_map_options as bmo
from gremlin.ui import hardware_profile
from gremlin.ui.option import ConfigGroupModel, ConfigSectionModel

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_every_option_is_registered_and_shown_in_options() -> None:
    bmo.register()
    cfg = Configuration()
    for group, name, _kind, _default, _description, _props in bmo.OPTIONS:
        assert group in bmo.GROUPS, group
        assert cfg.exists(bmo.SECTION, group, name)
        assert cfg.get(bmo.SECTION, group, name, "expose")


def test_options_list_a_button_map_section_in_group_order() -> None:
    bmo.register()
    sections = ConfigSectionModel()
    names = [sections.data(sections.index(i), 257) for i in range(sections.rowCount())]
    assert "Button Map" in names
    groups = ConfigGroupModel(bmo.SECTION)
    shown = [groups.data(groups.index(i), 257) for i in range(groups.rowCount())]
    assert shown == [g for g in bmo.GROUPS if g in shown]


def test_values_by_name_and_set() -> None:
    bmo.register()
    bmo.set_value("undo-steps", 120)
    assert bmo.value("undo-steps") == 120
    qml = bmo.ButtonMapOptions()
    assert qml.values["undo-steps"] == 120
    qml.set("export-size", "3x")
    assert qml.values["export-size"] == "3x"
    assert bmo.scale_of(qml.values["export-size"]) == 3
    qml.set("no-such-option", 1)
    bmo.set_value("undo-steps", 80)
    bmo.set_value("export-size", "2x")


def test_recent_colours_follow_the_option() -> None:
    bmo.register()
    Configuration().set("global", "internal", "button-map-recent-colours", [])
    bmo.set_value("recent-colours", 4)
    profile = hardware_profile.HardwareProfile()
    for i in range(6):
        profile.noteColour(f"#0000{i:02X}")
    assert len(profile.recentColours) == 4
    bmo.set_value("recent-colours", 10)


def test_the_app_registers_the_options_before_purging() -> None:
    source = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    start = source.index("def register_config_options(")
    end = source.index("\ndef ", start + 1)
    # Everything registered there survives Configuration.purge_unused().
    assert "gremlin.ui.button_map_options.register()" in source[start:end]
