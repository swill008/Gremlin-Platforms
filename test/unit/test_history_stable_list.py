# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The History window's list stays as it is (D-TESTLIST-1 13, 15).

A Restore is one hidden entry linked to the entry it restored ("of"); that
entry shows a tag ("Restored · HH:MM", "Reapplied · HH:MM") instead of a
new top row. Titles are "Restored: <title>" / "Reapplied: <title>", never
stacked. Changes recorded meanwhile wait as newCount until showNew().
Rows are grouped by day, and repeated changes to one thing fold into one
row that opens with toggleGroup().
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import history, shared_state, util
from gremlin.modules import module_file
from gremlin.profile import Profile
from gremlin.ui import history_model
from test.unit._device_folders import ensure_dir


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    yield folder
    _settle()


def _two_saves() -> tuple[Path, dict]:
    path = ensure_dir(util.modules_dir(), "Stable Stick") / "module.json"
    module_file.write_json(path, {"device": "Stable Stick"})
    _settle()
    module_file.write_json(
        path, {"device": "Stable Stick", "calibration": {"1": [0, 1, 2, 3, True]}}
    )
    return path, _settle()[0]


def _role(model: history_model.HistoryModel, row: int, name: str) -> object:
    role = QtCore.Qt.ItemDataRole.UserRole + history_model._ROLES.index(name) + 1
    return model.data(model.index(row, 0), role)


def test_restore_titles_never_stack() -> None:
    entry = {"title": "Saved X: calibration"}
    assert history.restore_title(entry, "before") == "Restored: Saved X: calibration"
    again = {"title": history.restore_title(entry, "before")}
    assert history.restore_title(again, "after") == "Reapplied: Saved X: calibration"


def test_a_restore_is_one_hidden_entry_linked_to_the_original(
    store: Path, qapp: object
) -> None:
    path, entry = _two_saves()
    model = history_model.HistoryModel()
    model.reload()
    rows = model.rowCount()
    result = json.loads(model.restore(entry["id"], "before"))
    assert result["ok"], result
    assert "calibration" not in json.loads(path.read_text(encoding="utf-8"))
    newest = _settle()[0]
    assert newest["of"] == entry["id"] and newest["restore"] == "before"
    assert newest["title"] == "Restored: Saved Stable Stick: calibration"
    # No new row; the original is tagged in place.
    assert model.rowCount() == rows
    assert model.newCount == 0
    row = model.rowOf(entry["id"])
    assert str(_role(model, row, "tag")).startswith("Restored · ")
    # Restoring to after: "Reapplied", still linked to the first original.
    assert json.loads(model.restore(entry["id"], "after"))["ok"]
    assert str(_role(model, row, "tag")).startswith("Reapplied · ")
    assert _settle()[0]["of"] == entry["id"]
    model.deleteLater()


def test_new_changes_wait_until_show(store: Path, qapp: object) -> None:
    path, entry = _two_saves()
    model = history_model.HistoryModel()
    model.reload()
    first = [_role(model, r, "entryId") for r in range(model.rowCount())]
    history.record("settings", "Changed a setting", {}, {}, {})
    _settle()
    model.refresh()
    assert model.newCount == 1
    assert [_role(model, r, "entryId") for r in range(model.rowCount())] == first
    model.showNew()
    assert model.newCount == 0
    assert _role(model, 0, "title") == "Changed a setting"
    assert [_role(model, r, "entryId") for r in range(1, model.rowCount())] == first
    model.deleteLater()


def test_repeated_changes_fold_and_open(store: Path, qapp: object) -> None:
    _two_saves()
    model = history_model.HistoryModel()
    model.reload()
    # Two saves of the same device's file today: one row of two.
    assert model.rowCount() == 1
    assert _role(model, 0, "groupSize") == 2
    assert _role(model, 0, "groupFirst") is True
    assert _role(model, 0, "day") == "Today"
    key = str(_role(model, 0, "groupKey"))
    model.toggleGroup(key)
    assert model.rowCount() == 2
    assert _role(model, 0, "groupOpen") is True
    assert _role(model, 1, "groupFirst") is False
    model.toggleGroup(key)
    assert model.rowCount() == 1
    model.deleteLater()


def test_day_words() -> None:
    today = date(2026, 10, 11)
    at = time.mktime((2026, 10, 10, 12, 0, 0, 0, 0, -1))
    assert history_model._day(at, today) == "Yesterday"
    at = time.mktime((2026, 10, 9, 12, 0, 0, 0, 0, -1))
    assert history_model._day(at, today) == "2026-10-09"


def test_detail_says_in_plain_words_what_restoring_does(store: Path) -> None:
    _, entry = _two_saves()
    shown = history_model.describe(entry)
    assert shown["effect"] == (
        "Puts Stable Stick's module file back as it was before this change, "
        "with its pictures. Saved at once."
    )
    assert "after this change" in shown["effectAfter"]
