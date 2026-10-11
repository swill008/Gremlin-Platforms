# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""An unreadable row in the Logical Device module file (AD1, SHAKE-DAMAGE-01): it is
skipped for use with a load warning, the good rows after it still load, and
Save writes it back as it was, in its place, so no row is ever lost."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin import logical_device_file as ldf
from gremlin.logical_device import LogicalRows
from gremlin.modules import store
from gremlin.types import InputType
from test.unit._device_folders import ensure_dir

GOOD_FIRST = {"uid": "a" * 32, "type": "button", "id": 1, "label": "Button 1"}
GOOD_AFTER = [
    {"uid": "b" * 32, "type": "button", "id": 2, "label": "Button 2"},
    {"uid": "c" * 32, "type": "axis", "id": 1, "label": "Axis 1"},
]

BAD_ROWS = {
    "missing id": {"uid": "d" * 32, "type": "button", "label": "No id"},
    "id not a number": {"uid": "d" * 32, "type": "button", "id": "abc"},
    "NaN id": {"uid": "d" * 32, "type": "button", "id": float("nan")},
    "duplicate label": {
        "uid": "d" * 32,
        "type": "button",
        "id": 7,
        "label": "Button 1",
    },
    "unknown type": {"uid": "d" * 32, "type": "key", "id": 1},
    "label not text": {"uid": "d" * 32, "type": "button", "id": 8, "label": [1]},
    "not an object": 42,
}


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


def _ld_path() -> Path:
    """The Logical Device's module.json, its folder made."""
    from gremlin.modules import ids

    ensure_dir(store.folder(), "Logical Device", str(ids.LOGICAL_DEVICE))
    return ldf.path()


def _write(controls: list) -> Path:
    path = _ld_path()
    doc = {"device": "Logical Device", ldf.KEY: {"controls": controls, "groups": []}}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _controls(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8"))[ldf.KEY]["controls"]


def _uids(rows: LogicalRows) -> set[str]:
    return {item.uid for item in rows.ordered()}


@pytest.mark.parametrize("case", sorted(BAD_ROWS))
def test_bad_row_is_skipped_warned_and_kept_at_save(modules: Path, case: str) -> None:
    bad = BAD_ROWS[case]
    path = _write([GOOD_FIRST, bad, *GOOD_AFTER])
    rows = LogicalRows()

    warnings = ldf.load(rows)

    # The good rows after the bad one load too.
    assert _uids(rows) == {"a" * 32, "b" * 32, "c" * 32}
    assert not rows.dirty
    assert warnings and len(warnings) == 1
    assert rows.load_warnings == warnings

    # An edit, then Save: every good row and the bad row, in its place.
    rows.create(InputType.JoystickButton)
    assert ldf.save(rows)
    saved = _controls(path)
    assert len(saved) == 5
    assert json.dumps(saved[1]) == json.dumps(bad)
    assert [saved[i]["uid"] for i in (0, 2, 3)] == ["a" * 32, "b" * 32, "c" * 32]

    # Read again: the same rows, the bad one still skipped.
    again = LogicalRows()
    ldf.load(again)
    assert len(again.ordered()) == 4
    assert len(again.load_warnings) == 1


def test_save_without_edit_leaves_the_rows_as_they_were(modules: Path) -> None:
    path = _write([GOOD_FIRST, BAD_ROWS["missing id"], *GOOD_AFTER])
    before = _controls(path)
    rows = LogicalRows()
    ldf.load(rows)
    assert ldf.save(rows)
    after = _controls(path)
    # Good rows are written in full (the save adds their default keys).
    assert [c["uid"] for c in after] == [c["uid"] for c in before]
    assert after[1] == before[1]
    for old, new in zip(before, after):
        assert {k: new[k] for k in old} == old


def test_a_clean_file_has_no_warnings(modules: Path) -> None:
    _write([GOOD_FIRST, *GOOD_AFTER])
    rows = LogicalRows()
    assert ldf.load(rows) == []
    assert rows.load_warnings == []


def test_reload_of_a_fixed_file_forgets_the_bad_row(modules: Path) -> None:
    path = _write([GOOD_FIRST, BAD_ROWS["id not a number"]])
    rows = LogicalRows()
    ldf.load(rows)
    _write([GOOD_FIRST])
    ldf.load(rows)
    assert rows.load_warnings == []
    assert ldf.save(rows)
    assert len(_controls(path)) == 1


def test_deep_nesting_is_refused_cleanly(modules: Path) -> None:
    path = _ld_path()
    text = '{"logical-device": {"controls": [' + "[" * 100000 + "]" * 100000 + "]}}"
    path.write_text(text, encoding="utf-8")
    rows = LogicalRows()

    warnings = ldf.load(rows)

    assert warnings
    assert rows.ordered() == []
    rows.create(InputType.JoystickButton)
    # Nothing is written over a file that couldn't be read.
    assert ldf.save(rows) is False
    assert path.read_text(encoding="utf-8") == text
