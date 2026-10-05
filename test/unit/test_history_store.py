# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The history store (gremlin.history).

Every saved change is appended as one JSON line to its area's file in the
history folder; a writer thread does it and ends by itself; a damaged line
doesn't stop the rest from being read; entries past the day or size limit
go, with the kept pictures nothing needs any more.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    yield folder
    history.flush()


def _wait_for_writer() -> None:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)


def test_an_entry_is_appended_and_read_back(store: Path) -> None:
    first = history.record("profile", "Saved profile", {"profile": "a.xml"}, "x", "y")
    second = history.record("modules", "Saved Stick", {"device": "Stick"}, {}, {"a": 1})
    _wait_for_writer()
    assert (store / "profile.jsonl").is_file()
    assert (store / "modules.jsonl").is_file()
    read = history.entries()
    assert [e["id"] for e in read] == [second, first]
    assert history.entry(first)["after"] == "y"
    assert [e["id"] for e in history.entries("modules")] == [second]


def test_the_writer_ends_by_itself(store: Path) -> None:
    history.record("settings", "Changed an option", {}, 1, 2)
    _wait_for_writer()
    assert history._writer is None
    assert not [t for t in threading.enumerate() if t.name.endswith("History")]


def test_a_damaged_line_is_skipped(store: Path) -> None:
    store.mkdir(parents=True)
    good = {"id": "a", "at": 1.0, "area": "profile", "title": "ok"}
    (store / "profile.jsonl").write_text(
        "{ half a line\n" + json.dumps(good) + "\n", encoding="utf-8"
    )
    assert [e["id"] for e in history.entries("profile")] == ["a"]


def _line(entry_id: str, at: float, **extra: object) -> str:
    return json.dumps({"id": entry_id, "at": at, "area": "profile", **extra}) + "\n"


def test_old_entries_and_unneeded_pictures_go(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.mkdir(parents=True)
    now = 100 * 86400.0
    monkeypatch.setattr(history.clock, "now", lambda: now)
    monkeypatch.setattr(history, "_limits", lambda: (30, 20))
    (store / "files").mkdir()
    (store / "files" / "old.png").write_bytes(b"old")
    (store / "files" / "new.png").write_bytes(b"new")
    (store / "profile.jsonl").write_text(
        _line("old", now - 40 * 86400, before={"keptFile": "old.png"})
        + _line("new", now - 2 * 86400, after={"keptFile": "new.png"}),
        encoding="utf-8",
    )
    history.prune()
    assert [e["id"] for e in history.entries("profile")] == ["new"]
    assert not (store / "files" / "old.png").exists()
    assert (store / "files" / "new.png").exists()


def test_a_file_past_its_size_loses_its_oldest_entries(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.mkdir(parents=True)
    monkeypatch.setattr(history.clock, "now", lambda: 1000.0)
    monkeypatch.setattr(history, "_limits", lambda: (90, 1))
    big = "x" * 400_000
    (store / "profile.jsonl").write_text(
        "".join(_line(f"e{i}", 900.0 + i, after=big) for i in range(4)),
        encoding="utf-8",
    )
    history.prune()
    kept = [e["id"] for e in history.entries("profile")]
    assert kept == ["e3", "e2"]
    assert (store / "profile.jsonl").stat().st_size <= 1024 * 1024


def test_a_picture_is_kept_once_and_put_back(store: Path, tmp_path: Path) -> None:
    photo = tmp_path / "photo.PNG"
    photo.write_bytes(b"picture")
    name = history.keep_file(photo)
    assert name.endswith(".png")
    assert history.keep_file(photo) == name
    assert len(list((store / "files").iterdir())) == 1
    dest = tmp_path / "back" / "photo.png"
    assert history.restore_file(name, dest)
    assert dest.read_bytes() == b"picture"
