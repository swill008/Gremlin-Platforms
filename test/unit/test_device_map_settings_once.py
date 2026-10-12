# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-3): the Button Map's settings move to the Device
Mapping Editor's names (gremlin/device_map_settings_once.py), on a temporary
settings file loaded into the running Configuration."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from gremlin import config
from gremlin import device_map_settings_once as once
from gremlin.types import PropertyType


def _entry(value: str, data_type: str = "string") -> dict:
    return {"value": value, "data_type": data_type, "properties": {}, "expose": False}


@pytest.fixture
def settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[[dict], Path]]:
    """Writes a settings file, loads it into Configuration; the real one is
    loaded back afterwards."""
    path = tmp_path / "configuration.json"
    cfg = config.Configuration()
    original = config._config_file_path

    def load(doc: dict) -> Path:
        path.write_text(json.dumps(doc), encoding="utf-8")
        monkeypatch.setattr(config, "_config_file_path", str(path))
        cfg._last_reload = None
        cfg.load()
        return path

    yield load
    monkeypatch.setattr(config, "_config_file_path", original)
    cfg._last_reload = None
    cfg.load()


def _saved(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_old_settings_are_copied_to_the_new_names_and_dropped(
    settings: Callable[[dict], Path],
) -> None:
    path = settings(
        {
            "button-map": {"panels": {"left": _entry("open")}},
            "global": {
                "internal": {
                    "button-map-options-group": _entry("Layout"),
                    "button-map-recent-colours": _entry("#ff0000"),
                    "other": _entry("kept"),
                }
            },
        }
    )
    assert once.run() != ""
    saved = _saved(path)
    assert "button-map" not in saved
    assert saved["device-mapping-editor"]["panels"]["left"]["value"] == "open"
    internal = saved["global"]["internal"]
    assert internal["device-map-options-group"]["value"] == "Layout"
    assert internal["device-map-recent-colours"]["value"] == "#ff0000"
    assert "button-map-options-group" not in internal
    assert "button-map-recent-colours" not in internal
    assert internal["other"]["value"] == "kept"
    cfg = config.Configuration()
    assert cfg.value("device-mapping-editor", "panels", "left") == "open"
    assert not cfg.exists("button-map", "panels", "left")


def test_registering_after_the_move_keeps_the_moved_value(
    settings: Callable[[dict], Path],
) -> None:
    # The start's order: the move, then register_config_options registers
    # the new names (an entry already stored keeps its value).
    settings({"global": {"internal": {"button-map-options-group": _entry("Wiring")}}})
    once.run()
    cfg = config.Configuration()
    cfg.register(
        "global",
        "internal",
        "device-map-options-group",
        PropertyType.String,
        "Layout",
        "test",
        {},
        False,
    )
    assert cfg.value("global", "internal", "device-map-options-group") == "Wiring"
    assert not cfg.exists("global", "internal", "button-map-options-group")


def test_new_names_already_present_are_untouched(
    settings: Callable[[dict], Path],
) -> None:
    path = settings(
        {
            "button-map": {"panels": {"left": _entry("old")}},
            "device-mapping-editor": {"panels": {"right": _entry("new")}},
            "global": {
                "internal": {
                    "button-map-options-group": _entry("old"),
                    "device-map-options-group": _entry("new"),
                }
            },
        }
    )
    before = path.read_text(encoding="utf-8")
    assert once.run() == ""
    assert path.read_text(encoding="utf-8") == before
    cfg = config.Configuration()
    assert cfg.value("global", "internal", "device-map-options-group") == "new"
    assert not cfg.exists("device-mapping-editor", "panels", "left")


def test_runs_once(settings: Callable[[dict], Path]) -> None:
    path = settings({"button-map": {"panels": {"left": _entry("open")}}})
    assert once.run() != ""
    after = path.read_text(encoding="utf-8")
    assert once.run() == ""
    assert path.read_text(encoding="utf-8") == after


def test_no_history_entry(
    settings: Callable[[dict], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import history

    recorded = []
    monkeypatch.setattr(history, "record", lambda *a, **k: recorded.append(a))
    settings({"button-map": {"panels": {"left": _entry("open", "string")}}})
    once.run()
    assert recorded == []


def test_refuses_the_real_settings_under_tests(
    settings: Callable[[dict], Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = settings({"button-map": {"panels": {"left": _entry("open")}}})
    before = path.read_text(encoding="utf-8")
    monkeypatch.setattr(once, "_REAL_DATA", [tmp_path])
    assert once.run() == once.REFUSED
    assert once.run_if_needed() == once.REFUSED
    assert path.read_text(encoding="utf-8") == before


def test_real_folder_is_the_users_profile() -> None:
    import os

    real = Path(os.environ["USERPROFILE"]) / "Gremlin Platforms"
    assert once.refuses_real_settings(real / "configuration.json")
    assert not once.refuses_real_settings(Path(config._config_file_path))
