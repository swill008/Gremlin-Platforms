# -*- coding: utf-8; -*-
"""Saved window and tab settings survive the startup purge."""
import json
import tempfile
from collections.abc import Iterator
from unittest import mock

import pytest

import gremlin.config
from gremlin.common import SingletonMetaclass

SAVED = {
    ("global", "internal", "window-x"): ("int", 120),
    ("global", "internal", "window-y"): ("int", 80),
    ("global", "internal", "window-width"): ("int", 1600),
    ("global", "internal", "window-height"): ("int", 1000),
    ("global", "internal", "window-maximized"): ("bool", True),
    ("global", "internal", "button-map-menu-width"): ("int", 300),
    ("global", "internal", "button-map-menu-height"): ("int", 600),
    ("global", "internal", "display-panels"): ("string", '{"a": true}'),
    ("global", "internal", "close-pane-after-ok"): ("bool", True),
    ("global", "internal", "action-pane-width"): ("int", 700),
    ("global", "internal", "tool-windows"): ("string", '{"options": [1, 2, 3, 4]}'),
    ("global", "internal", "logical-layout"): ("string", '{"k": 1}'),
    ("devices", "display", "vjoy-tabs"): ("list", [1, 3]),
    ("devices", "display", "extra-tabs"): ("list", ["osc"]),
}


@pytest.fixture
def saved_cfg() -> Iterator[gremlin.config.Configuration]:
    """A configuration file from an earlier session, holding every saved value."""
    data: dict = {}
    for (section, group, name), (kind, value) in SAVED.items():
        data.setdefault(section, {}).setdefault(group, {})[name] = {
            "data_type": kind,
            "description": "",
            "expose": False,
            "properties": {},
            "value": value,
        }
    path = tempfile.mkstemp(suffix=".json")[1]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    with mock.patch.object(gremlin.config, "_config_file_path", path):
        try:
            yield gremlin.config.Configuration()
        finally:
            SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


def test_window_and_tab_settings_survive_purge(
    saved_cfg: gremlin.config.Configuration,
) -> None:
    from gremlin.ui import vjoy_status, window_placement

    window_placement._ensure()
    vjoy_status.register_options()
    saved_cfg.purge_unused()

    for (section, group, name), (_, value) in SAVED.items():
        assert saved_cfg.exists(section, group, name), name
        assert saved_cfg.value(section, group, name) == value, name


def test_startup_registration_keeps_them(
    saved_cfg: gremlin.config.Configuration,
) -> None:
    import joystick_gremlin

    joystick_gremlin.register_config_options()
    saved_cfg.purge_unused()

    for (section, group, name), (_, value) in SAVED.items():
        assert saved_cfg.value(section, group, name) == value, name
