# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Map Options (07 S98), checked in the running program off-screen
(device_map_options_pane_smoke.py, its own process and user folder).

- Its own small window: Edit > Device Map Options... (Ctrl+,) opens it, on
  the live map too; no Options pane or tool tab in the Device Mapping Editor (S99).
- The groups down the left, the chosen group's settings on the right.
- A setting changed in it is kept at once; the group shown is kept.
- Library shows the saved styles and templates.
- Esc closes it; Ctrl+, opens it again.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    script = _ROOT / "test" / "unit" / "device_map_options_pane_smoke.py"
    done = proc_tree.run(
        [sys.executable, str(script)],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_the_menu_opens_its_own_window(run: dict) -> None:
    assert run["menu"] == "Ctrl+,"
    assert run["open"] == [True, "Device Map Options", False]
    assert run["no-pane"] == []


def test_groups_and_their_settings(run: dict) -> None:
    assert run["groups"] == [
        "labels", "editing", "right-click", "recovery", "view", "colours",
        "library"]
    assert run["labels-rows"] == [
        "chip-text", "description-first", "several-actions", "unbound"]
    assert len(run["editing-rows"]) == 6
    assert run["right-click-title"] == ["Right-click menu"]
    assert run["right-click-rows"] == ["favourites-shown"]
    assert run["library"] is True


def test_a_change_is_kept_and_so_is_the_group(run: dict) -> None:
    before, now, saved = run["switch"]
    assert now is (not before) and saved is now
    assert run["kept-group"] == "editing"


def test_esc_closes_it_and_ctrl_comma_opens_it(run: dict) -> None:
    assert run["esc-closed"] is True
    assert run["key-opens"] is True
