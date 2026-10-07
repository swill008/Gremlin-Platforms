# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""History's Before and After show what changed (08 S104,
D-08-HISTORY-DIFF): the two texts line up row for row (gremlin.text_diff),
each row same / removed / added / changed, a changed row with its changed
words, and the change blocks Previous Change / Next Change move between.
The History model gives them for the change it shows."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, text_diff, util
from gremlin.modules import module_file
from gremlin.ui import history_model


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
    yield folder
    _settle()


def _kinds(rows: list[dict]) -> list[str]:
    return [row["kind"] for row in rows]


def _words(line: str, spans: list[list[int]]) -> list[str]:
    return [line[start:end] for start, end in spans]


def test_rows_line_up_with_fillers() -> None:
    before = "Title:\nButton 1\nButton 2\nAxis 1: 0 to 100\nEnd"
    after = "Title:\nButton 1\nAxis 1: 0 to 255\nEnd\nButton 9"
    rows = text_diff.rows(before, after)
    assert _kinds(rows) == ["same", "same", "changed", "removed", "same", "added"]
    # A changed row has both lines; a filler row's other side is blank.
    assert (rows[2]["before"], rows[2]["after"]) == ("Button 2", "Axis 1: 0 to 255")
    assert (rows[3]["before"], rows[3]["after"]) == ("Axis 1: 0 to 100", "")
    assert (rows[5]["before"], rows[5]["after"]) == ("", "Button 9")
    # Same, removed and added rows have no word ranges.
    for index in (0, 1, 3, 4, 5):
        assert rows[index]["beforeSpans"] == rows[index]["afterSpans"] == []


def test_a_changed_row_marks_its_changed_words() -> None:
    rows = text_diff.rows("Axis 1: 0 to 100 (inverted)", "Axis 1: 0 to 255 (inverted)")
    assert _kinds(rows) == ["changed"]
    row = rows[0]
    assert _words(row["before"], row["beforeSpans"]) == ["100"]
    assert _words(row["after"], row["afterSpans"]) == ["255"]


def test_words_next_to_each_other_are_one_range() -> None:
    row = text_diff.rows("Button 3 â€” Fire", "Button 3 â€” Fire Main Gun")[0]
    assert row["beforeSpans"] == []
    assert _words(row["after"], row["afterSpans"]) == ["Main Gun"]


def test_change_blocks() -> None:
    before = "a\nb\nc\nd\ne\nf"
    after = "a\nB\nC\nd\ne\nF\ng"
    rows = text_diff.rows(before, after)
    assert _kinds(rows) == [
        "same",
        "changed",
        "changed",
        "same",
        "same",
        "changed",
        "added",
    ]
    assert [row["block"] for row in rows] == [-1, 0, 0, -1, -1, 1, 1]
    assert text_diff.blocks(rows) == [1, 5]


def test_the_same_text_has_no_changes() -> None:
    rows = text_diff.rows("a\nb", "a\nb")
    assert _kinds(rows) == ["same", "same"]
    assert text_diff.blocks(rows) == []
    assert text_diff.rows("", "") == []
    assert _kinds(text_diff.rows("", "new")) == ["added"]


def test_the_model_gives_the_shown_changes_rows(store: Path) -> None:
    # A module file saved twice, as the History window's own run does:
    # the second save added Button 2.
    path = util.modules_dir() / "diff_stick.json"
    module_file.write_json(path, {"device": "Diff Stick", "claim": {"buttons": [1]}})
    _settle()
    module_file.write_json(path, {"device": "Diff Stick", "claim": {"buttons": [1, 2]}})
    entry = _settle()[0]
    model = history_model.HistoryModel()
    model.setFilter('{"device": "Diff Stick"}')
    model.reload()
    told: list[bool] = []
    model.diffChanged.connect(lambda: told.append(True))
    shown = json.loads(model.detail(entry["id"]))
    assert told
    rows = model.diffRows
    assert rows == shown["diffRows"]
    assert model.diffBlocks == shown["diffBlocks"]
    added = [row for row in rows if row["kind"] != "same"]
    assert [(row["kind"], row["before"], row["after"]) for row in added] == [
        ("added", "", "Button 2")
    ]
    assert model.diffBlocks == [rows.index(added[0])]
    # Every row's lines put together are the Before and After text.
    before = [row["before"] for row in rows if row["kind"] != "added"]
    after = [row["after"] for row in rows if row["kind"] != "removed"]
    assert "\n".join(before) == shown["before"]
    assert "\n".join(after) == shown["after"]
    # Nothing picked: no rows.
    model.detail("")
    assert model.diffRows == [] and model.diffBlocks == []
