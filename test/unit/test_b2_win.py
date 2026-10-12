# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Export / Import Device window, off-screen (b2_win_smoke.py;
D-FIXLIST-B2, 08 S49-S114): its title, .gmap only in both file choosers,
openFor() on each tab with the device chosen or suggested, and the
As a new device / Onto an existing device choice when a file is opened."""

from __future__ import annotations

import json
import os
import pathlib
import sys
from urllib.parse import unquote

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    result = proc_tree.run(
        [sys.executable, "test/unit/b2_win_smoke.py"],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT ") :])


def _key(guid: object) -> str:
    return str(guid or "").strip("{}").lower()


def test_the_window_is_export_import_device(run: dict) -> None:
    assert run.get("title") == "Export / Import Device"


def test_only_gmap_files(run: dict) -> None:
    assert run["save-filters"] == ["Device files (*.gmap)"]
    assert run["save-suffix"] == "gmap"
    assert run["open-filters"] == ["Device files (*.gmap)"]
    # The default name is "<device>.gmap".
    assert unquote(str(run["hint"])).endswith("/pJoy Pro.gmap"), run["hint"]


def test_open_for_export_chooses_the_device(run: dict) -> None:
    assert run["export-tab"] == 0
    assert run["export-device"] == "pJoy Pro"
    assert _key(run["export-guid"])


def test_open_for_import_suggests_the_device(run: dict) -> None:
    assert run["import-tab"] == 1
    assert run["import-target"] == "existing"
    assert run["import-name"] == "pJoy Pro"
    assert _key(run["import-guid"])
    assert run["choice-shown"] is True
    assert run["existing-checked"] is True
    # A file opened after it goes onto the suggested device.
    assert run["suggested-target"] == "existing"
    assert run["suggested-name"] == "pJoy Pro"


def test_a_device_without_a_folder_goes_as_a_new_device(run: dict) -> None:
    assert run["new-target"] == "new"
    assert run["new-name"] == "Unknown Stick"
    assert run["new-checked"] is True
    assert run["new-combo-hidden"] is True
    assert run["new-selection"]["target"] == "new"
    assert run["new-selection"]["targetGuid"] == ""


def test_a_device_with_a_folder_goes_onto_it(run: dict) -> None:
    assert run["folder-target"] == "existing"
    assert run["folder-row"] >= 0
    assert run["folder-selection"]["target"] == "existing"


def test_the_piece_ticks_show_for_both_targets(run: dict) -> None:
    assert run["ticks-existing"] is True
    assert run["clicked-target"] == "new"
    assert run["ticks-new"] is True
