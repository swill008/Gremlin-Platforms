# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-TESTER-XBOX-SLOT (02 S105, S106, S122): the Input Tester matches each
of Gremlin's Xbox pads by the real XInput slot written in expected.json
("xinput"), never by Gremlin's own pad number."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.append(".")

from gremlin.input_tester import compare as cmp
from gremlin.input_tester.devices import SeenDevice


def slot(n: int) -> SeenDevice:
    """A pad the tester sees in XInput slot n (1-4, as devices.py numbers them)."""
    return SeenDevice(
        key=f"xi:{n}",
        kind="xinput",
        name=f"Xbox pad {n}",
        pad=n,
        axes=6,
        buttons=10,
        hats=1,
    )


def expected_file(tmp_path: pathlib.Path, xbox: list[dict]) -> dict:
    """Hand-written expected.json, read back the way the tester reads it."""
    path = tmp_path / "expected.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "written": "2026-10-10T15:40:00",
                "hidhide": {"present": True, "cloak": True, "mode": "block"},
                "sticks": [],
                "vjoy": [],
                "xbox": xbox,
            }
        ),
        encoding="utf-8",
    )
    data, problem = cmp.read_expected(str(path))
    assert problem == ""
    assert data is not None
    return data


def xbox_rows(v: cmp.Verdict) -> list[cmp.Row]:
    return [r for r in v.rows if r.kind == "xbox"]


def others(v: cmp.Verdict) -> list[cmp.Row]:
    return [r for r in v.rows if r.kind == "other"]


def test_pad_matches_its_xinput_slot_not_its_number(tmp_path: pathlib.Path) -> None:
    data = expected_file(
        tmp_path, [{"pad": 1, "xinput": 2, "on": True, "expect": "visible"}]
    )
    v = cmp.compare(data, [slot(1), slot(2)], False)
    (row,) = xbox_rows(v)
    assert (row.verdict, row.key) == ("ok", "xi:2")
    # The pad in slot 1 isn't Gremlin's: it stays an unknown extra.
    assert [r.key for r in others(v)] == ["xi:1"]


def test_pad_in_slot_two_is_missing_when_only_slot_one_seen(
    tmp_path: pathlib.Path,
) -> None:
    data = expected_file(
        tmp_path, [{"pad": 1, "xinput": 2, "on": True, "expect": "visible"}]
    )
    v = cmp.compare(data, [slot(1)], False)
    (row,) = xbox_rows(v)
    assert row.verdict == "missing"
    assert row.device is None


def test_null_slot_gets_no_verdict_and_takes_nothing(tmp_path: pathlib.Path) -> None:
    data = expected_file(
        tmp_path, [{"pad": 1, "xinput": None, "on": True, "expect": "visible"}]
    )
    v = cmp.compare(data, [slot(1)], False)
    (row,) = xbox_rows(v)
    assert (row.verdict, row.device) == ("", None)
    assert [r.key for r in others(v)] == ["xi:1"]
    assert v.verdict == "pass"


def test_missing_slot_gets_no_verdict(tmp_path: pathlib.Path) -> None:
    data = expected_file(tmp_path, [{"pad": 1, "on": True, "expect": "hidden"}])
    v = cmp.compare(data, [slot(1)], False)
    (row,) = xbox_rows(v)
    assert (row.verdict, row.device) == ("", None)
    assert v.verdict == "pass"


def test_real_pad_in_slot_one_is_not_green_for_gremlin_pad_one(
    tmp_path: pathlib.Path,
) -> None:
    """Gremlin pad 1 got slot 3 (a real pad holds slot 1): slot 1 never passes
    for it."""
    data = expected_file(
        tmp_path, [{"pad": 1, "xinput": 3, "on": True, "expect": "visible"}]
    )
    v = cmp.compare(data, [slot(1)], False)
    (row,) = xbox_rows(v)
    assert row.verdict == "missing"
    assert row.device is None
    assert v.verdict != "pass"


def test_xinput_wrong_type_is_refused(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "expected.json"
    path.write_text(
        json.dumps({"xbox": [{"pad": 1, "xinput": "two", "expect": "visible"}]}),
        encoding="utf-8",
    )
    _data, problem = cmp.read_expected(str(path))
    assert "xbox[0].xinput" in problem
