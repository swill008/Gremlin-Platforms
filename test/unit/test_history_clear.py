# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""08 S12b, D-08-CLEAR-HISTORY: Clear History deletes every History entry
and kept copy, and nothing else (profiles, module files, the Device Library
and any other file in the folder stay); refused while a profile runs;
leaves one red "History cleared" entry the clean-up never removes; empties
the Device Library's Undo/Redo. Device Library entries read "Device Library".
Real History store in a temporary folder."""

from __future__ import annotations

import json
import time
import weakref
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, library_undo, run_scope
from gremlin.ui import history_model


@pytest.fixture
def data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A data folder: History beside profiles, modules and the Library."""
    root = tmp_path / "data"
    hist = root / "history"
    monkeypatch.setattr(history, "folder", lambda: hist)
    monkeypatch.setattr(history, "_pruned", True)
    for name, text in (
        ("profiles/a.xml", "<profile/>"),
        ("modules/stick.json", "{}"),
        ("device library/library.json", "{}"),
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    # Never the real data folder.
    assert history.folder().resolve().is_relative_to(tmp_path.resolve())
    yield root
    _settled()


def _settled() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


def _fill(root: Path) -> None:
    history.record("settings", "Changed A", {}, 1, 2)
    history.record("profile", "Saved a.xml", {"profile": "a.xml"}, None, None)
    history.record(
        "modules", "Saved Stick", {}, {"text": "{}"}, {"text": "{}"}, kind="save"
    )
    picture = root / "modules" / "photo.png"
    picture.write_bytes(b"\x89PNG photo")
    assert history.keep_file(picture)
    _settled()


def _others(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and "history" not in p.relative_to(root).parts[:1]
    }


def test_clear_deletes_history_only(data: Path) -> None:
    _fill(data)
    hist = data / "history"
    # Someone's own file in the History folder is not History's: it stays.
    (hist / "notes.txt").write_text("mine", encoding="utf-8")
    (hist / "files" / "readme.txt").write_text("mine", encoding="utf-8")
    others = _others(data)

    found = history.summary()
    assert found["entries"] == 3
    assert found["bytes"] > 0

    out = history.clear_all()
    assert out == {"ok": True, "error": "", **found}
    assert _others(data) == others
    assert (hist / "notes.txt").read_text(encoding="utf-8") == "mine"
    assert (hist / "files" / "readme.txt").read_text(encoding="utf-8") == "mine"
    assert [p.name for p in (hist / "files").iterdir()] == ["readme.txt"]
    for area in ("settings", "profile", "modules", "button-map"):
        assert not (hist / f"{area}.jsonl").exists()

    left = _settled()
    assert len(left) == 1
    cleared = left[0]
    assert cleared["kind"] == "cleared"
    assert cleared["title"] == "History cleared"
    assert cleared["subject"] == {"entries": 3, "bytes": found["bytes"]}
    assert cleared["before"] is None and cleared["after"] is None
    assert history.summary()["entries"] == 0


def test_refused_while_a_profile_runs(
    data: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fill(data)
    monkeypatch.setattr(run_scope, "running", lambda: True)
    out = history.clear_all()
    assert out["ok"] is False
    assert "running" in out["error"]
    assert len(_settled()) == 3
    assert history.summary()["entries"] == 3


def test_cleared_entries_stay_through_clean_up_and_later_clears(
    data: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fill(data)
    assert history.clear_all()["ok"]
    history.record("settings", "Changed B", {}, 1, 2)
    _settled()
    assert history.clear_all()["ok"]
    titles = [e["title"] for e in _settled()]
    assert titles == ["History cleared", "History cleared"]

    # Long past the day limit, and the file past its size limit: still kept.
    monkeypatch.setattr(history, "_limits", lambda: (1, 0))
    monkeypatch.setattr(history.clock, "now", lambda: time.time() + 400 * 86400)
    history.prune()
    assert [e["kind"] for e in _settled()] == ["cleared", "cleared"]


def test_library_undo_steps_empty(data: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Only this test's Steps: an earlier test's Device Library model whose Qt
    # object is gone but not yet collected would fail first and stop the rest.
    monkeypatch.setattr(library_undo, "_ALL", weakref.WeakSet())
    steps = library_undo.Steps()
    told: list[int] = []
    steps.on_cleared.append(lambda: told.append(1))
    assert steps.note(0.0, "Remove Stick", undo=lambda: {"ok": True})
    assert steps.note(0.0, "Rename Stick", undo=lambda: {"ok": True})
    assert steps.undo()["ok"]
    assert steps.undo_text() and steps.redo_text()
    assert history.clear_all()["ok"]
    assert steps.undo_text() == "" and steps.redo_text() == ""
    assert told == [1]


def test_window_shows_cleared_red_and_library_as_device_library(
    data: Path,
) -> None:
    history.record("modules", "Removed Stick from the Library", {}, {}, {}, "library")
    history.record("settings", "Changed A", {}, 1, 2)
    _settled()
    model = history_model.HistoryModel()
    asked = json.loads(model.summary())
    assert asked["entries"] == 2 and asked["size"]
    out = json.loads(model.clearAll())
    assert out["ok"] and out["entries"] == 2
    assert model.rowCount() == 1

    roles = {bytes(v).decode(): k for k, v in model.roleNames().items()}
    index = model.index(0, 0)
    assert model.data(index, roles["title"]) == "History cleared"
    assert model.data(index, roles["danger"]) is True
    shown = json.loads(model.detail(model.data(index, roles["entryId"])))
    assert shown["danger"] is True
    assert shown["note"] == history_model.CLEARED_NOTE
    assert not shown["canRestoreBefore"] and not shown["canRestoreAfter"]

    history.record("modules", "Removed Stick from the Library", {}, {}, {}, "library")
    group = history.group_entry(
        "modules",
        "Remove Stick",
        [
            history._make("modules", "Saved Stick", {}, {"text": "{}"}, None, "save"),
            history._make("modules", "Library", {}, {}, {}, "library"),
        ],
    )
    history._append(group)
    model.reload()
    index = model.index(0, 0)
    assert model.data(index, roles["danger"]) is False
    names = [model.data(model.index(r, 0), roles["areaName"]) for r in range(2)]
    assert names == ["Device Library", "Device Library"]
    for entry in history.entries()[:2]:
        shown = history_model.describe(entry)
        assert shown["area"] == "Device Library"
        assert shown["note"] == history_model.LIBRARY_NOTE
    plain = history_model.describe(
        history._make("modules", "Saved Stick", {}, {"text": "{}"}, None, "save")
    )
    assert plain["area"] == "Module files"
