# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor: the empty-space right-click menu switches planes (07 S113).

Right-clicking an empty part of the map while editing offers Edit Background
(Foreground mode) or Exit Background Editing (Background mode), Ctrl+B beside
it; clicking it switches the editor's plane. Undo/Redo stay in the menu's
header and Paste and Draw stay. Runs the editor off-screen in its own
process.
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
    folder = tmp_path_factory.mktemp("canvas_menu")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "canvas_menu_planes_smoke.py"), str(folder)],
        text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-2000:]
    return json.loads(lines[0][len("RESULT "):])


def _item(menu: dict) -> dict:
    return next(i for i in menu["quick"] if i["name"] == "dmeEditPlane")


def test_foreground_offers_edit_background(results: dict) -> None:
    menu = results["fg"]
    assert menu["kind"] == "canvas"
    assert menu["title"] == "Canvas"
    item = _item(menu)
    assert item["text"] == "Edit Background"
    assert item["hint"] == "Ctrl+B"
    assert item["enabled"] is True


def test_clicking_it_enters_background_mode(results: dict) -> None:
    assert results["after-enter"] == "background"


def test_background_offers_exit(results: dict) -> None:
    item = _item(results["bg"])
    assert item["text"] == "Exit Background Editing"
    assert item["hint"] == "Ctrl+B"
    assert results["after-exit"] == "foreground"


def test_other_items_stay(results: dict) -> None:
    for key in ("fg", "bg"):
        menu = results[key]
        assert menu["header"] == ["Undo", "Redo"], key
        assert "Paste" in [i["text"] for i in menu["quick"]], key
        assert "draw" in menu["sections"], key


def test_not_offered_while_viewing(results: dict) -> None:
    assert results["viewing-interactive"] is False
    assert all(i["name"] != "dmeEditPlane" for i in results["viewing"]["quick"])


def test_no_warnings(results: dict) -> None:
    assert results["warnings"] == []
