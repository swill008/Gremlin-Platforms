# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Audit 2: Options places and names, History titles, Home card order,
scripts that can't load.

The History folder shows with the other folders, not under General > Other.
Double Tap, Smart Toggle, Tempo and Axis Delta settings each have their own
group (they were "Duration"/"Threshold" under Actions > Other). History
names a changed setting the way Options does ("Plugins folder", not "Plugin
directory"). The Home card order keeps an unplugged stick's place. A script
that can't load doesn't gain blank lines at each save.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import time
from collections.abc import Iterator
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree

import pytest

from gremlin import config, history
from gremlin.common import SingletonMetaclass
from gremlin.profile import Profile, ScriptManager
from gremlin.types import PropertyType
from gremlin.ui import history_model, module_model, option
from gremlin.user_script import Script


@pytest.fixture
def cfg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> config.Configuration:
    """A fresh settings file of its own (the program's is put back after)."""
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    instances = SingletonMetaclass._instances
    monkeypatch.delitem(instances, config.Configuration, raising=False)
    return config.Configuration()


def _register_folder(cfg: config.Configuration, key: str) -> None:
    cfg.register(
        "global", "files", key, PropertyType.Path, Path("C:/x"), "",
        {"is_folder": True}, True,
    )


def test_history_folder_shows_with_the_other_folders(cfg: config.Configuration) -> None:
    for key in ("logs-folder", "history-folder"):
        _register_folder(cfg, key)
    layout = dict(option.main_layout())
    folders = [key for _g, keys in layout["Folders"] for key in keys]
    history_key = ("global", "files", "history-folder")
    assert history_key in folders
    assert folders.index(history_key) == folders.index(
        ("global", "files", "logs-folder")
    ) + 1
    # No folder (nor any other "global" setting) lands under General > Other.
    other = dict(layout["General"]).get("Other", [])
    assert not [key for key in other if key[1] == "files"]
    assert option.entry_title("history-folder") == "History folder"


@pytest.mark.parametrize(
    ("group", "key"),
    [
        ("Double Tap", ("action", "double-tap", "duration")),
        ("Smart Toggle", ("action", "smart-toggle", "duration")),
        ("Tempo", ("action", "tempo", "duration")),
        ("Axis Delta", ("action", "axis-delta", "threshold")),
    ],
)
def test_action_settings_have_their_own_group(
    cfg: config.Configuration, group: str, key: tuple[str, str, str]
) -> None:
    # As the plugin registers it (action_plugins/<name>/__init__.py).
    cfg.register(*key, PropertyType.Float, 0.5, "", {"min": 0.0, "max": 10.0}, True)
    actions = dict(dict(option.main_layout())["Actions"])
    assert actions.get(group) == [key]
    assert key not in actions.get("Other", [])


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


def test_history_names_settings_as_options_does(
    store: Path, cfg: config.Configuration
) -> None:
    _register_folder(cfg, "plugin-directory")
    cfg.save_now()
    cfg._history_view = cfg._settings_view()
    cfg.set("global", "files", "plugin-directory", Path("C:/plugins"))
    cfg.save_now()
    entries = [e for e in _settle() if e["area"] == "settings"]
    assert [e["title"] for e in entries] == ["Changed Plugins folder"]
    shown = history_model.describe(entries[0])
    assert shown["after"].startswith("Plugins folder: ")


def test_numbered_setting_loses_its_number_in_history() -> None:
    # Button Map's "01-autosave" read "Changed 01 autosave".
    text = history_model._settings_text({"button-map/autosave/01-autosave": "true"})
    assert text == "Autosave: true"


def test_card_order_keeps_an_unplugged_stick_in_its_place() -> None:
    saved = ["throttle", "stick", "pedals", "vjoy1"]
    # The stick is unplugged: the others show in their saved order.
    assert module_model._merged_order(saved, ["throttle", "pedals", "vjoy1"]) == saved
    # A card moved while the stick is away; the stick keeps its slot.
    assert module_model._merged_order(saved, ["pedals", "throttle", "vjoy1"]) == [
        "pedals", "stick", "throttle", "vjoy1"
    ]
    # A new card goes last.
    showing = ["throttle", "pedals", "vjoy1", "new"]
    assert module_model._merged_order(saved, showing) == [
        "throttle", "stick", "pedals", "vjoy1", "new"
    ]


GOOD = (
    "import gremlin.user_script as us\n"
    "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n"
)


def _pretty(scripts: ElementTree.Element) -> str:
    """A profile's <scripts> as a profile save writes it (Profile.to_xml)."""
    root = ElementTree.Element("profile")
    root.append(scripts)
    ugly = ElementTree.tostring(root, encoding="utf-8")
    return minidom.parseString(ugly).toprettyxml(indent="    ")


def test_script_that_cannot_load_does_not_grow_at_each_save(tmp_path: Path) -> None:
    path = tmp_path / "gone.py"
    path.write_text(GOOD, encoding="utf-8")
    script = Script(path, "Instance 1")
    script.variables["speed"].value = 3
    first = ScriptManager(Profile())
    first.scripts.append(script)
    text = _pretty(first.to_xml())
    path.unlink()

    saves = []
    for _ in range(3):
        manager = ScriptManager(Profile())
        manager.from_xml(ElementTree.fromstring(text))
        assert manager.scripts[0].load_error == "File not found"
        text = _pretty(manager.to_xml())
        saves.append(text)
    assert saves[0] == saves[1] == saves[2]
    assert "\n\n" not in saves[2].replace("\r\n", "\n")
    assert "<value>3</value>" in saves[2]
