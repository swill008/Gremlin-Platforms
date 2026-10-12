# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's grid covers the map's box scaled 1.2x about
its centre (10 % past each side), not only the page, with a border on its
edge and nothing beyond; it never shows in an export (S87). Driven
off-screen by grid_box_smoke.py in its own process."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

_SMOKE = pathlib.Path(__file__).parent / "grid_box_smoke.py"


def _run(tmp_path: pathlib.Path) -> dict:
    env = dict(os.environ, USERPROFILE=str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    result = proc_tree.run(
        [sys.executable, str(_SMOKE), str(tmp_path)], text=True, timeout=180, env=env
    )
    report = tmp_path / "grid_box.json"
    assert result.returncode == 0 and report.exists(), result.stderr[-2000:]
    return json.loads(report.read_text(encoding="utf-8"))


def test_grid_fills_the_box_with_a_border_and_never_exports(
    tmp_path: pathlib.Path,
) -> None:
    r = _run(tmp_path)
    w, h = r["window"]
    gl, gt, gr, gb = r["gridBox"]
    # The zoomed-out view shows the whole grid box and some space past it.
    assert gl > 10 and gt > 10 and gr + 60 < w and gb + 60 < h, r
    # Grid lines past the editor's edges, within the box.
    assert r["bandRight"] > 0, r
    assert r["bandBelow"] > 0, r
    assert r["bandLeft"] > 0, r
    # Nothing past the box.
    assert r["beyondRight"] == 0, r
    assert r["beyondBelow"] == 0, r
    # The border runs along the box's edge.
    assert r["borderRightRows"] == r["rowsChecked"], r
    assert r["borderBelowCols"] == r["colsChecked"], r
    # Export: the editor's own size, and no grid in it.
    assert r["exportSize"] == [round(v) for v in r["editorSize"]], r
    assert r["exportSame"], r
    assert not r["warnings"], r["warnings"]
