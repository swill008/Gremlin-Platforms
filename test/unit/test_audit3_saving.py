# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Saving and History (audit 3).

A Device Pack import that wrote nothing used to replace Undo Import (the
import before it then couldn't be undone, its replaced actions dropped for
good); one that copied calibration took a curve loading throws away over a
good one. History recorded a module file's delete before it happened (a
locked file that stayed was "Deleted"); a History folder that couldn't be
made raised out of quit (no update installed, no restart); a picture that
wasn't kept left the entry, so Restore couldn't name it, and an old-style
"qml/maps/..." picture was looked for in the wrong place. Settings titles:
three "Duration"s, "Action priorities", and old entries kept old names.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, history_modules, util
from gremlin.modules import module_file
from gremlin.ui import device_pack

# The Device Pack fixtures (a pack exported on one PC, a profile on another).
_spec = importlib.util.spec_from_file_location(
    "audit3_device_pack_import",
    pathlib.Path(__file__).parent / "test_device_pack_import.py",
)
assert _spec is not None and _spec.loader is not None
_dpi = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _dpi
_spec.loader.exec_module(_dpi)
pack = _dpi.pack
_import = _dpi._import


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


def _locked(monkeypatch: pytest.MonkeyPatch, locked: Path) -> None:
    """Deleting this file fails, as when another program has it open."""
    real = pathlib.Path.unlink

    def unlink(self: Path, missing_ok: bool = False) -> None:
        if self == locked:
            raise PermissionError("in use")
        real(self, missing_ok)

    monkeypatch.setattr(pathlib.Path, "unlink", unlink)


# --- Device Pack: Undo Import ------------------------------------------------


def test_an_import_that_wrote_nothing_keeps_undo_import(
    pack: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _import(pack, ["wire:Default"])
    assert first["ok"], first
    last = device_pack._last_import
    assert last and last["wires"]

    def fails(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(device_pack, "_write_pictures", fails)
    result = _import(pack, ["out:vjoy_2.claim"])
    # Nothing was written: it says why, and the import before it can still
    # be undone (its replaced actions still kept).
    assert result["ok"] is False
    assert "could not be written" in result["error"]
    assert device_pack._last_import is last
    undone = device_pack.undo_import()
    assert undone["ok"], undone
    assert _dpi._targets(pack["profile"], pack["uid"], "Default") == {3: (1, 3)}


# --- Device Pack: calibration ------------------------------------------------


def test_a_curve_that_cant_be_used_doesnt_replace_a_good_one() -> None:
    good = [-32768, -100, 100, 32767, True]
    existing = {
        "claim": {"buttons": [], "axes": [1, 2, 3], "hats": [], "keys": []},
        "calibration": {"1": good},
    }
    incoming = {
        "calibration": {
            "1": [500, 0, 0, 100, True],  # low not below high
            "2": [-100, 900, 950, 100, True],  # the center outside
            "3": [-30000, 0, 0, 30000, False],
        }
    }
    merged, notes = device_pack._merge_module(
        existing, incoming, {"in.calibration"}, "in.", "Some Stick", ""
    )
    assert merged["calibration"] == {"1": good, "3": [-30000, 0, 0, 30000, False]}
    assert "Calibration that can't be used was left out: Axis 1, Axis 2." in notes


# --- History: deletes are recorded once they happen --------------------------


def test_a_delete_that_failed_is_no_history_entry(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = util.modules_dir() / "locked_stick.json"
    module_file.write_json(path, {"device": "Locked Stick"})
    _settle()
    _locked(monkeypatch, path)
    with pytest.raises(PermissionError):
        with history_modules.deleting(path):
            path.unlink()
    assert path.is_file()
    assert [e for e in _settle() if e["kind"] == "delete"] == []


def test_a_delete_that_went_through_is_recorded(store: Path) -> None:
    path = util.modules_dir() / "gone_stick.json"
    module_file.write_json(path, {"device": "Gone Stick"})
    with history_modules.deleting(path):
        path.unlink()
    deletes = [e for e in _settle() if e["kind"] == "delete"]
    assert [e["title"] for e in deletes] == ["Deleted the module file of Gone Stick"]
    assert json.loads(deletes[0]["before"]["text"]) == {"device": "Gone Stick"}


def test_undo_import_of_a_locked_new_file_isnt_recorded_as_deleted(
    pack: dict, store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The pack's output on vJoy 1, which has no module file yet: Undo
    # Import deletes the new file, and Windows refuses.
    result = _import(pack, ["out:vjoy_2.claim"])
    assert result["ok"], result
    made = util.modules_dir() / "vjoy_1.json"
    assert made.is_file()
    real_unlink = pathlib.Path.unlink
    _locked(monkeypatch, made)
    undone = device_pack.undo_import()
    assert "vjoy_1.json could not be put back." in undone["report"]
    assert made.is_file()
    titles = [e["title"] for e in _settle()]
    assert "Deleted the module file of vJoy 1" not in titles
    real_unlink(made)


# --- History: quit ------------------------------------------------------------


def test_quit_goes_on_when_the_history_folder_cant_be_made(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(history, "_closing", False)
    monkeypatch.setattr(history, "_pruned", True)

    def no_folder() -> Path:
        raise PermissionError("can't make the history folder")

    monkeypatch.setattr(util, "history_dir", no_folder)
    history._queue.put(history._make("settings", "Changed X", {}, {}, {}, "save"))
    history.close()  # the settings save at quit: queued
    # and recorded once closing (written at once).
    history.record("settings", "Changed Y", {}, {}, {})


# --- History: pictures --------------------------------------------------------


def test_every_picture_is_named_and_old_style_ones_are_found(store: Path) -> None:
    from gremlin.ui import history_model

    modules = util.modules_dir()
    (modules / "old_stick").mkdir(parents=True, exist_ok=True)
    photo = modules / "old_stick" / "photo.png"
    photo.write_bytes(b"old photo")
    path = modules / "old_stick.json"
    doc = {
        "device": "Old Stick",
        "image": "qml/maps/old_stick/photo.png",
        "nodes": [{"kind": "image", "src": "old_stick/gone.png"}],
        "claim": {"buttons": [1]},
    }
    module_file.write_json(path, doc)
    module_file.write_json(path, {**doc, "claim": {"buttons": [1, 2]}})
    entry = next(e for e in _settle() if e["title"].startswith("Saved Old Stick"))
    pictures = {p["ref"]: p["keptFile"] for p in entry["after"]["pictures"]}
    assert set(pictures) == {"qml/maps/old_stick/photo.png", "old_stick/gone.png"}
    assert pictures["old_stick/gone.png"] == ""
    kept = history.kept_file(pictures["qml/maps/old_stick/photo.png"])
    assert kept is not None and kept.read_bytes() == b"old photo"
    # Restore puts the photo back where the Button Map finds it and names
    # the one no copy was kept of.
    photo.unlink()
    result = history_model.restore(entry["id"], "before")
    assert result["ok"], result
    assert photo.read_bytes() == b"old photo"
    assert "old_stick/gone.png" in result["message"]


# --- History: settings titles -------------------------------------------------


def test_a_repeated_setting_name_says_its_group(
    store: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gremlin import config, plugin_manager
    from gremlin.ui import history_model

    plugin_manager.PluginManager()  # Double Tap and Tempo register theirs
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    cfg = config.Configuration()
    keys = [("action", "double-tap", "duration"), ("action", "tempo", "duration")]
    was = [cfg.value(*key) for key in keys]
    try:
        cfg.save_now()
        cfg._history_view = cfg._settings_view()
        # Both in one save, as Options' changes are.
        cfg._data[keys[0]]["value"] = 1.25
        cfg._data[keys[1]]["value"] = 2.5
        cfg.save_now()
        entry = next(e for e in _settle() if e["area"] == "settings")
    finally:
        for key, value in zip(keys, was, strict=True):
            cfg._data[key]["value"] = value
        cfg.save_now()
    assert entry["title"] == "Changed Double Tap duration, Tempo duration"
    shown = history_model.describe(entry)
    assert shown["before"].splitlines() == [
        f"Double Tap duration: {was[0]}",
        f"Tempo duration: {was[1]}",
    ]
    assert shown["after"].splitlines() == [
        "Double Tap duration: 1.25",
        "Tempo duration: 2.5",
    ]


def test_action_priorities_is_called_as_options_calls_it() -> None:
    from gremlin.config import settings_history_title

    assert (
        settings_history_title(["action/general/action-priorities"])
        == "Changed Actions offered"
    )


def test_an_old_settings_entry_reads_as_a_new_one(store: Path) -> None:
    from PySide6 import QtCore

    from gremlin.ui import history_model

    history.write_now(
        "settings",
        "Changed Duration",
        {"keys": ["action/smart-toggle/duration"]},
        {"action/smart-toggle/duration": 1},
        {"action/smart-toggle/duration": 2},
    )
    entry = _settle()[0]
    assert history_model.describe(entry)["title"] == "Changed Smart Toggle duration"
    model = history_model.HistoryModel()
    model.reload()
    model.setSearch("smart toggle")
    assert model.rowCount() == 1
    title_role = QtCore.Qt.ItemDataRole.UserRole + 1 + history_model._ROLES.index(
        "title"
    )
    assert model.data(model.index(0, 0), title_role) == "Changed Smart Toggle duration"
