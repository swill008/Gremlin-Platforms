# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Reset Picture (07, D-07-RESET-PICTURE) and Reset Shape on a turned picture
(07 S42).

Reset Picture is the first row of the right-click menu's Picture section and
a button in the picture's Properties. It gives the picture the size a fresh
add would give it, centred where it is, and clears crop, turn, flip, skew and
opacity; snap points, file, plane, name, hidden and locked stay. One Undo
step; every selected picture; greyed out when there is nothing to reset or
the picture is locked. Runs the editor off-screen in its own process.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    folder = tmp_path_factory.mktemp("reset_picture")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "reset_picture_smoke.py"), str(folder)],
        text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT "):])


def _reset_ok(after: dict, before: dict, fresh: dict) -> None:
    cx = before["fx"] + before["fw"] / 2
    cy = before["fy"] + before["fh"] / 2
    assert after["fw"] == pytest.approx(fresh["fw"])
    assert after["fh"] == pytest.approx(fresh["fh"])
    assert after["fx"] + after["fw"] / 2 == pytest.approx(cx)
    assert after["fy"] + after["fh"] / 2 == pytest.approx(cy)
    assert after["rot"] == 0
    assert not after["flipH"] and not after["flipV"]
    assert after["crop"] is None and after["skew"] is None and after["adj"] is None
    assert after["opacity"] == 1
    for key in ("sockets", "src", "plane", "name", "hidden", "locked", "look"):
        assert after[key] == before[key], key


def test_reset_picture_is_the_first_picture_row(results: dict) -> None:
    rows = results["rows-pic"]
    assert rows[0] == ["Reset Picture", True]
    texts = [r[0] for r in rows]
    assert "Reset Crop" in texts


def test_reset_picture_puts_the_picture_back(results: dict) -> None:
    before = results["before"]
    assert before["rot"] == 30 and before["opacity"] == 0.5
    _reset_ok(results["after"], before, results["fresh"])
    assert results["steps"] == 1
    # Nothing left to reset: greyed out.
    assert results["rows-pic-after"][0] == ["Reset Picture", False]


def test_one_undo_brings_it_all_back(results: dict) -> None:
    assert results["undone"] == results["before"]


def test_greyed_out_when_locked_or_nothing_to_reset(results: dict) -> None:
    assert results["can-plain"] is False
    assert results["can-lock"] is False
    assert results["rows-plain"][0] == ["Reset Picture", False]


def test_every_selected_picture_in_one_step(results: dict) -> None:
    multi = results["multi"]
    assert results["multi-steps"] == 1
    _reset_ok(multi["pic"], results["before"], results["fresh"])
    assert multi["pic2"]["rot"] == 0 and multi["pic2"]["opacity"] == 1
    # The locked picture is left as it was.
    assert multi["plock"]["rot"] == 45


def test_menu_bar_command(results: dict) -> None:
    assert results["cmd-applies"] is True
    assert results["cmd-steps"] == 1
    _reset_ok(results["cmd-after"], results["before"], results["fresh"])


def test_properties_button(results: dict) -> None:
    assert "Reset Picture" in results["props-pic"]
    assert results["props-button"] is True
    assert results["props-steps"] == 1
    _reset_ok(results["props-after"], results["before"], results["fresh"])


def test_reset_shape_gives_back_a_turn(results: dict) -> None:
    """S42: Reset Shape on a picture that is only turned (a guard; this
    already worked before Reset Picture)."""
    assert results["shape-enabled"] is True
    assert results["prot-after"]["rot"] == 0


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
