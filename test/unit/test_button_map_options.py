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
    # Only in the Button Map's own window, never in the main Options.
    sections = ConfigSectionModel()
    names = [sections.data(sections.index(i), 257) for i in range(sections.rowCount())]
    assert "Button Map" not in names
    own = ConfigSectionModel()
    own.setProperty("scope", bmo.SECTION)
    titles = [own.data(own.index(i), 257) for i in range(own.rowCount())]
    assert titles == ["Button Map"]
    groups = ConfigGroupModel(bmo.SECTION)
    shown = [groups.data(groups.index(i), 257) for i in range(groups.rowCount())]
    # Headings may be spelled differently from the stored keys ("colours").
    from gremlin.ui.option import _GROUP_TITLES

    keys = [_GROUP_TITLES.get(g, g) for g in bmo.GROUPS]
    assert shown == [g for g in keys if g in shown]


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


def test_saved_styles_save_replace_rename_delete() -> None:
    bmo.register()
    bmo._store_styles([])
    assert bmo.save_style("Red", "shape", {"color": "#FF0000"})
    assert bmo.save_style("Red", "chip", {"color": "#FF0000"})
    # Same name and kind: replaced, not added.
    assert bmo.save_style("Red", "shape", {"color": "#AA0000"})
    rows = bmo.styles()
    assert [(s["kind"], s["name"]) for s in rows] == [("chip", "Red"), ("shape", "Red")]
    assert rows[1]["fields"] == {"color": "#AA0000"}
    assert not bmo.save_style("", "shape", {"color": "#000000"})
    assert not bmo.save_style("X", "picture", {"color": "#000000"})
    assert not bmo.save_style("X", "shape", {})
    assert bmo.rename_style("Red", "shape", "Warning")
    assert not bmo.rename_style("Warning", "shape", "")
    assert bmo.delete_style("Red", "chip")
    assert not bmo.delete_style("Red", "chip")
    qml = bmo.ButtonMapOptions()
    assert [s["name"] for s in qml.styles] == ["Warning"]
    assert qml.saveStyle("Calm", "line", '{"border": "#00FF00"}')
    assert not qml.saveStyle("Bad", "line", "not json")
    assert qml.renameStyle("Calm", "line", "Calmer")
    assert qml.deleteStyle("Calmer", "line")
    bmo._store_styles([])


def test_library_is_listed_in_options() -> None:
    from gremlin.ui.option import MetaConfigOption

    entries = MetaConfigOption().entries(bmo.SECTION, "library")
    assert "saved-styles-and-templates" in entries
