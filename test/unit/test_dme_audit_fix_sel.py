# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor audit fixes in selection, paths and tables, checked on the real
editor off-screen (dme_audit_fix_sel_smoke.py, its own process and user
folder):

- Paste puts the copies in the plane being edited and selects them
  (07 S116, S119, S121).
- Backspace while drawing a path takes back the last point, not the
  selected item (07 S134; Keyboard Shortcuts "Undo a path point").
- A table cell target left stale by Undo or by selecting another table is
  dropped: Delete then acts on the table, and a new table starts with none.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "dme_audit_fix_sel_smoke.py")],
        cwd=home,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("FIXSEL ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("FIXSEL ") :])


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []


def test_paste_goes_to_the_plane_being_edited(run: dict) -> None:
    assert len(run["paste_fg_new"]) == 1
    assert run["paste_fg_planes"] == [""]
    assert run["paste_fg_in_edit_plane"] == [True]
    assert run["paste_bg_planes"] == ["background"]
    assert run["paste_bg_in_edit_plane"] == [True]


def test_backspace_takes_back_a_path_point(run: dict) -> None:
    assert run["path_before"] == 3
    assert run["path_after"] == 2
    assert run["path_chip_kept"] is True


def test_delete_after_undoing_a_spawned_cell_deletes_the_table(run: dict) -> None:
    assert run["spawned_extras"] == 1
    assert run["after_undo_extras"] == 0
    assert run["tA_gone"] is True
    assert run["after_undo_valid"] is False


def test_another_table_starts_without_a_cell_target(run: dict) -> None:
    assert run["same_table_kept"] == [0, 1, -1]
    assert run["other_selection_reset"] == [-1, -1, -1]
