# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Layers search in the Device Mapping Editor window (07 S102,
D-07-LAYERS-SEARCH), checked in the running program off-screen
(layers_search_window_smoke.py, its own process and user folder).

- Ctrl+F goes to the Search layers… box, opening Layers if it is closed.
- View > Search layers… (Ctrl+F) in the menu bar does the same.
- The kinds and the search stay when another device's map is shown, and are
  none and empty after the Device Mapping Editor closes and opens again.
- Help describes the box, the kind toggles and the keys.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
from PySide6 import QtCore

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = "layers_search_window_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / _SMOKE)],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_ctrl_f_opens_layers_and_goes_to_the_box(run: dict) -> None:
    assert run["active"] is True
    assert run["layers-before"] is False
    assert run["ctrl-f-opens-layers"] is True
    assert run["ctrl-f-focuses-search"] is True
    assert run["ctrl-f-when-open"] is True


def test_the_view_menu_lists_search_layers(run: dict) -> None:
    assert run["menu-item"] == "Search layers…"
    assert run["menu-shortcut"] == "Ctrl+F"


def test_the_view_menu_item_searches_layers(run: dict) -> None:
    assert run["menu-opens-layers"] is True
    assert run["menu-focuses-search"] is True


def test_kinds_and_search_stay_on_another_devices_map(run: dict) -> None:
    want = {"kinds": ["chip"], "query": "Button 3"}
    assert run["set-filter"] is True
    assert json.loads(run["filter-before-switch"]) == want
    assert run["switched"] == "Other Stick"
    assert run["same-panel-after-switch"] is True
    assert json.loads(run["filter-after-switch"]) == want


def test_closing_the_device_mapping_editor_resets_them(run: dict) -> None:
    assert run["new-window"] is True
    assert json.loads(run["filter-after-reopen"]) == {"kinds": [], "query": ""}


def _layers_help() -> str:
    """The Device Mapping Editor chapter's Layers topics, from the one Help book."""
    from test.unit import help_book  # noqa: PLC0415

    return " ".join(
        t["body"] for t in help_book.chapter_topics("device-mapping-editor")
        if "layer" in t["title"].lower()
    )


def test_help_describes_the_search(qapp: QtCore.QCoreApplication) -> None:
    body = _layers_help()
    for words in (
        "Search layers…",
        "Ctrl+F",
        "Esc",
        "Enter",
        "All · Chips · Groups · Hotspots · Leaders · Shapes · Lines · Pictures"
        " · Text · Tables",
        "No layers match",
        "when the Device Mapping Editor closes",
    ):
        assert words in body, words
    # The old single-choice kind buttons are gone.
    assert "Drawings" not in body
    # No Photo toggle: the background has its own row (07 S102, S120).
    assert "· Photo" not in body
