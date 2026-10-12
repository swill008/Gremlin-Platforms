# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-4): the Device Library's part id "button_map"
becomes "device_map" (gremlin/library_part_id_once.py), on a temporary
library folder and data folder; never the user's own."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import library_part_id_once as once


def _old_doc() -> dict:
    return {
        "format": 1,
        "settings": {"keep": 10, "default_parts": ["setup", "button_map", "bindings"]},
        "devices": [
            {
                "key": "dev-1",
                "name": "Stick",
                "guid": "{0000}",
                "setups": [
                    {
                        "key": "set-1",
                        "name": "Mine",
                        "file": "Stick/Mine.gmap",
                        "holds": ["setup", "button_map", "appearance"],
                    }
                ],
            }
        ],
        "lastChange": {
            "kind": "swap",
            "detail": {"parts": ["setup", "button_map"], "first": ["a"]},
        },
    }


@pytest.fixture
def lib(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    folder = tmp_path / "device library"
    folder.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(library, "folder", lambda: folder)
    path = folder / library.LIST_NAME
    path.write_text(json.dumps(_old_doc(), indent=2) + "\n", encoding="utf-8")
    return {"path": path, "data": data}


def test_part_id_is_device_map() -> None:
    assert "device_map" in library.PARTS
    assert "button_map" not in library.PARTS
    assert library.PART_LABELS["device_map"] == "Device Map"
    assert "device_map" in library.DEFAULT_PARTS


def test_saved_setups_read_back_with_the_new_id_after_the_move(lib: dict) -> None:
    summary = once.run(lib["path"], lib["data"])
    assert "3 renamed" in summary
    doc = json.loads(lib["path"].read_text(encoding="utf-8"))
    assert doc["settings"]["default_parts"] == ["setup", "device_map", "bindings"]
    assert doc["lastChange"]["detail"]["parts"] == ["setup", "device_map"]
    assert doc["lastChange"]["detail"]["first"] == ["a"]
    assert "button_map" not in lib["path"].read_text(encoding="utf-8")
    # The Library itself shows the setup's Device Map part again.
    (setup,) = [
        s for row in library.devices() for s in row["setups"] if s["key"] == "set-1"
    ]
    assert setup["holds"] == ["setup", "device_map", "appearance"]
    assert "device_map" in library.settings()["default_parts"]


def test_a_backup_is_kept_and_the_move_runs_once(lib: dict) -> None:
    before = lib["path"].read_bytes()
    once.run(lib["path"], lib["data"])
    (backup,) = (lib["data"] / "backup").glob("*library part id move/library.json")
    assert backup.read_bytes() == before
    after = lib["path"].read_bytes()
    assert once.run(lib["path"], lib["data"]) == ""
    assert lib["path"].read_bytes() == after
    assert len(list((lib["data"] / "backup").iterdir())) == 1


def test_new_id_already_there_is_not_doubled() -> None:
    doc = {"settings": {"default_parts": ["device_map", "button_map"]}, "devices": []}
    assert once.migrate(doc) == 1
    assert doc["settings"]["default_parts"] == ["device_map"]


def test_no_library_is_nothing_to_do(tmp_path: Path) -> None:
    assert once.run(tmp_path / "library.json", tmp_path) == ""


def test_refuses_the_real_library_under_tests(
    lib: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(once, "_REAL_DATA", [tmp_path])
    before = lib["path"].read_bytes()
    assert once.run(lib["path"], lib["data"]) == once.REFUSED
    assert lib["path"].read_bytes() == before
    assert not (lib["data"] / "backup").exists()


def _user_shaped_doc() -> dict:
    """The shape the user's library.json had after the first move: holds
    renamed, three setups' "covers" still with the old id."""
    def setup(key: str, covers: list[str]) -> dict:
        return {
            "key": key,
            "name": key,
            "file": f"Stick/{key}.gmap",
            "holds": ["setup", "device_map", "appearance", "bindings"],
            "covers": covers,
        }

    return {
        "format": 1,
        "settings": {"default_parts": ["setup", "device_map", "bindings"]},
        "devices": [
            {
                "key": "dev-1",
                "setups": [
                    setup("a", ["setup", "device_map"]),
                    setup("b", ["setup", "device_map"]),
                    setup("c", ["setup", "button_map", "appearance"]),
                ],
            },
            {"key": "dev-2", "setups": []},
            {
                "key": "dev-3",
                "setups": [
                    setup("d", ["setup", "device_map"]),
                    setup("e", ["setup", "button_map"]),
                    setup("f", ["setup", "button_map", "bindings"]),
                ],
            },
        ],
        "lastChange": {"kind": "restore", "detail": {"part": "button_map"}},
    }


def test_covers_and_every_other_part_id_value_are_renamed(tmp_path: Path) -> None:
    path = tmp_path / "library.json"
    path.write_text(json.dumps(_user_shaped_doc(), indent=2) + "\n", encoding="utf-8")
    summary = once.run(path, tmp_path)
    assert "4 renamed" in summary
    text = path.read_text(encoding="utf-8")
    assert "button_map" not in text
    doc = json.loads(text)
    covers = [s["covers"] for d in doc["devices"] for s in d["setups"]]
    assert covers[2] == ["setup", "device_map", "appearance"]
    assert covers[4] == ["setup", "device_map"]
    assert covers[5] == ["setup", "device_map", "bindings"]
    assert doc["lastChange"]["detail"]["part"] == "device_map"
    # Nothing is left, so the next start does nothing and keeps no new backup.
    assert once.run(path, tmp_path) == ""
    assert len(list((tmp_path / "backup").iterdir())) == 1


def test_free_text_mentioning_the_old_id_is_kept() -> None:
    doc = {"devices": [{"setups": [{"name": "my button_map copy", "covers": []}]}]}
    assert once.migrate(doc) == 0
    assert doc["devices"][0]["setups"][0]["name"] == "my button_map copy"
