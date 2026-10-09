# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Layers search in the Button Map window (07 S102,
D-07-LAYERS-SEARCH), checked in the running program off-screen
(layers_search_window_smoke.py, its own process and user folder).

- Ctrl+F goes to the Search layers… box, opening Layers if it is closed.
- The Command Palette lists View > Search layers… (Ctrl+F), which does the
  same.
- The kinds and the search stay when another device's map is shown, and are
  none and empty after the Button Map closes and opens again.
- Help describes the box, the kind toggles and the keys.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest
from PySide6 import QtCore

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = "layers_search_window_smoke.py"
_HELP = _ROOT / "qml" / "help_topics.js"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / _SMOKE)],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
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


def test_the_palette_lists_search_layers(run: dict) -> None:
    assert run["palette-lists"][0] == "Search layers…"
    assert run["palette-shortcut"] == "Ctrl+F"


# Needs the unpinned palette to run the command it picks: today closing it
# takes the window's commands away (onClosed: Commands.removeOwner) before
# runPick's deferred Commands.trigger(id) looks the command up.
def test_the_palette_searches_layers(run: dict) -> None:
    assert run["palette-opens-layers"] is True
    assert run["palette-focuses-search"] is True


def test_kinds_and_search_stay_on_another_devices_map(run: dict) -> None:
    want = {"kinds": ["chip"], "query": "Button 3"}
    assert run["set-filter"] is True
    assert json.loads(run["filter-before-switch"]) == want
    assert run["switched"] == "Other Stick"
    assert run["same-panel-after-switch"] is True
    assert json.loads(run["filter-after-switch"]) == want


def test_closing_the_button_map_resets_them(run: dict) -> None:
    assert run["new-window"] is True
    assert json.loads(run["filter-after-reopen"]) == {"kinds": [], "query": ""}


def _layers_help() -> str:
    """The Button Map chapter's Layers topics, from the one Help book."""
    from test.unit import help_book  # noqa: PLC0415

    return " ".join(
        t["body"] for t in help_book.chapter_topics("button-map")
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
        " · Text · Tables · Photo",
        "No layers match",
        "when the Button Map closes",
    ):
        assert words in body, words
    # The old single-choice kind buttons are gone.
    assert "Drawings" not in body
