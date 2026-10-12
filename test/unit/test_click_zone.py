# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor click zone (07 S136, D-07-CLICK-ZONE, G71): the whole
visible area of the view takes clicks, right-clicks, selection, drags and box
select at every zoom and pan, also in the bands beside and below the map's
box at the lowest zoom (50 %). Middle-drag pan, Space pan, wheel zoom, the
rulers and the side panels keep working. Real mouse events on the off-screen
editor, in its own process (click_zone_smoke.py).
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
    folder = tmp_path_factory.mktemp("click_zone")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "click_zone_smoke.py"), str(folder)],
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT ") :])


def test_points_are_outside_the_maps_box(results: dict) -> None:
    x0, y0, x1, y1 = results["world"]
    for x, y in results["points"]:
        assert not (x0 <= x <= x1 and y0 <= y <= y1), (x, y, results["world"])


@pytest.mark.parametrize("where", ["below", "right", "corner"])
def test_right_click_outside_the_box_opens_the_menu(results: dict, where: str) -> None:
    assert results["menus"][where] is True


def test_click_trace_logs_editor_position(results: dict) -> None:
    lines = results["trace"]["lines"]
    assert len(lines) == 1, lines
    x, y = results["trace"]["want"]
    text = lines[0]
    got_x = int(text.split(" x=")[1].split()[0])
    got_y = int(text.split(" y=")[1].split()[0])
    assert abs(got_x - x) <= 1 and abs(got_y - y) <= 1, (text, x, y)
    assert "branch=empty-menu" in text


def test_left_click_on_picture_past_the_page_selects_it(results: dict) -> None:
    pic = results["picture"]
    left, right = pic["box"]
    assert left < 0 < right  # it does hang past the page's left edge
    assert pic["selected"] == [pic["id"]]


def test_box_select_starting_outside_the_box(results: dict) -> None:
    assert len(results["band"]) > 0


@pytest.mark.parametrize("where", ["outside", "inside"])
def test_middle_drag_pans(results: dict, where: str) -> None:
    assert results["midpan"][where] == [60, -40]


def test_space_drag_pans_and_selects_nothing(results: dict) -> None:
    assert results["spacepan"]["pan"] == [60, -40]
    assert results["spacepan"]["selected"] == []


@pytest.mark.parametrize("where", ["outside", "inside"])
def test_wheel_zooms(results: dict, where: str) -> None:
    assert results["wheel"][where] > results["wheel"]["min"]


def test_ruler_drag_adds_a_guide(results: dict) -> None:
    before, after = results["ruler"]
    assert after == before + 1


def test_side_panel_click_leaves_the_selection(results: dict) -> None:
    assert results["panel"] == ["b3"]


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
