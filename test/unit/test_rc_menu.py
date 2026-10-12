# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor right-click additions (07 S136, S137; D-07-RIGHTCLICK,
D-07-RIGHTCLICK-ANSWERS), through a real right-click on the editor run
off-screen in its own process (rc_menu_smoke.py):

- rows that are commands carry their command id (cmd), so the menu can offer
  the ☆; picker rows do not;
- Cut (Ctrl+X) beside Copy on an item; Paste Here and Select All (Ctrl+A) on
  empty space; Show in Layers and Properties… (F4) on every item;
- Paste Here puts the centre of the pasted items on the spot right-clicked;
- Repeat is the first quick row after a right-click command, named for it;
- favourites: in the order added, only those that apply, at most the count
  set (0 turns them off).
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
    folder = tmp_path_factory.mktemp("rc_menu")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "rc_menu_smoke.py"), str(folder)],
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT ") :])


def _by_text(rows: list[dict], text: str) -> dict:
    found = [r for r in rows if r["text"] == text]
    assert found, f"no row {text!r} in {[r['text'] for r in rows]}"
    return found[0]


def test_no_menu_warnings(results: dict) -> None:
    assert results["warnings"] == []


def test_command_rows_are_tagged(results: dict) -> None:
    chip = results["chip"]
    assert _by_text(chip["quick"], "Copy")["cmd"] == "edit.copy"
    assert _by_text(chip["quick"], "Paste")["cmd"] == "edit.paste"
    assert _by_text(chip["quick"], "Rename")["cmd"] == "rename"
    assert (
        _by_text(chip["sections"]["arrange"], "Bring to Front")["cmd"] == "bringToFront"
    )
    assert _by_text(chip["sections"]["arrange"], "Lock")["cmd"] == "lock"
    assert _by_text(chip["sections"]["colours"], "Fill Color…")["cmd"] == "color.fill"
    shape = results["shape"]
    assert _by_text(shape["quick"], "Duplicate")["cmd"] == "edit.duplicate"
    assert _by_text(shape["quick"], "Delete")["cmd"] == "edit.delete"
    rot = shape["sections"]["rotate"]
    assert _by_text(rot, "Flip Horizontally")["cmd"] == "flipH"
    # Picker and number rows have no ☆.
    assert all(r["cmd"] == "" for r in rot if r["kind"] in ("choice", "number"))


def test_cut_beside_copy(results: dict) -> None:
    for key in ("chip", "shape"):
        texts = [r["text"] for r in results[key]["quick"]]
        assert texts.index("Cut") + 1 == texts.index("Copy"), key
        cut = _by_text(results[key]["quick"], "Cut")
        assert cut["cmd"] == "edit.cut" and cut["hint"] == "Ctrl+X", key


def test_show_in_layers_and_properties_on_items(results: dict) -> None:
    for key in ("chip", "shape"):
        quick = results[key]["quick"]
        assert _by_text(quick, "Show in Layers")["enabled"] is True, key
        props = _by_text(quick, "Properties…")
        assert props["hint"] == "F4" and props["enabled"] is True, key
    texts = [r["text"] for r in results["canvas"]["quick"]]
    assert "Show in Layers" not in texts


def test_canvas_paste_here_and_select_all(results: dict) -> None:
    quick = results["canvas"]["quick"]
    texts = [r["text"] for r in quick]
    # Existing rows keep their places: Paste first.
    assert texts[0] == "Paste"
    assert "Paste Here" in texts
    sel = _by_text(quick, "Select All")
    assert (
        sel["cmd"] == "edit.selectAll"
        and sel["hint"] == "Ctrl+A"
        and sel["enabled"] is True
    )


def test_paste_here_centres_on_the_spot(results: dict) -> None:
    assert len(results["pasted"]) == 1
    cx, cy = results["pasteCentre"]
    sx, sy = results["pasteSpot"]
    assert abs(cx - sx) <= 4 and abs(cy - sy) <= 4, (
        results["pasteCentre"],
        results["pasteSpot"],
    )


def test_repeat_first_after_right_click_command(results: dict) -> None:
    first = results["afterFlip"]["quick"][0]
    assert first["name"] == "dmeRepeat"
    assert first["text"] == 'Repeat "Flip Horizontally"'


def test_favourites_order_applies_and_count(results: dict) -> None:
    fav5 = [r["cmd"] for r in results["fav5"]]
    # One shape selected: Group Selected does not apply, so it is left out.
    assert fav5 == ["flipH", "edit.selectAll", "rotatePlus"]
    assert all(r["enabled"] is True for r in results["fav5"])
    assert _by_text(results["fav5"], "Flip Horizontally")["cmd"] == "flipH"
    assert [r["cmd"] for r in results["fav2"]] == ["flipH", "edit.selectAll"]
    assert results["fav0"] == []
