# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A chip dragged from the Chips panel drops centred on the pointer, with or
without Chip only, at zoom 1 and 2; with a hotspot, the hotspot is at the
drop point (07 S156, D-07-CHIP-DROP). Checked in the running program
off-screen (chip_drop_centre_smoke.py, its own process and user folder).
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
_SMOKE = "chip_drop_centre_smoke.py"
_TOL = 2.0


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
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT "):])


@pytest.mark.parametrize("case", range(4), ids=[
    "zoom1-hotspot", "zoom1-chip-only", "zoom2-hotspot", "zoom2-chip-only"])
def test_the_chip_drops_centred_on_the_pointer(run: dict, case: int) -> None:
    d = run["drops"][case]
    g = d["got"]
    assert isinstance(g, dict), d
    assert abs(g["cx"] - d["x"]) <= _TOL and abs(g["cy"] - d["y"]) <= _TOL, d
    # The hotspot stays at the drop point, under the chip's centre.
    assert abs(g["hx"] - d["x"]) <= _TOL and abs(g["hy"] - d["y"]) <= _TOL, d
    assert g["hidden"] is d["chipOnly"], d


def test_with_no_point_the_chip_is_centred_on_the_view(run: dict) -> None:
    g = run["centre"]
    assert isinstance(g, dict), g
    assert abs(g["cx"] - g["vx"]) <= _TOL and abs(g["cy"] - g["vy"]) <= _TOL, g
    assert abs(g["hx"] - g["vx"]) <= _TOL and abs(g["hy"] - g["vy"]) <= _TOL, g
