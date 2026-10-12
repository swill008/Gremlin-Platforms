# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor: Shift/Ctrl+right-click on an item that isn't selected adds it
to the selection, so the menu acts on what it is titled for (audit AUD-CANVAS
P1: Delete Chip used to delete the chip selected before). A plain right-click
on an unselected item still selects just it. Real mouse events on the
off-screen editor, in its own process.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    folder = tmp_path_factory.mktemp("bm_ptr")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "dme_audit_fix_ptr_smoke.py"), str(folder)],
        text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-2000:]
    return json.loads(lines[0][len("RESULT "):])


@pytest.mark.parametrize("mod", ["shift", "ctrl"])
def test_modifier_right_click_adds_item_to_selection(results: dict, mod: str) -> None:
    r = results[mod]
    assert sorted(r["ids"]) == ["b3", "b4"]
    assert r["selected"] == ["b3", "b4"] or sorted(r["selected"]) == ["b3", "b4"]
    assert r["menu"] == {"kind": "multi", "title": "2 selected"}


def test_menu_delete_acts_on_what_it_names(results: dict) -> None:
    assert results["deleted"] == ["b3", "b4"]


def test_plain_right_click_selects_just_the_item(results: dict) -> None:
    r = results["plain"]
    assert r["ids"] == ["b5"]
    assert r["menu"]["kind"] == "chip"
    assert r["menu"]["title"] == "Button 5"


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
