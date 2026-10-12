# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor, view mode (07): the chip hover tooltip sits just
above the pointer, centred on it, at every zoom, and keeps its screen size.
The tooltip is a child of the zoomed editor, so its offsets are divided by
the zoom. Real mouse moves on the off-screen editor, in its own process
(chip_tooltip_zoom_smoke.py).
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
    folder = tmp_path_factory.mktemp("chip_tooltip_zoom")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "chip_tooltip_zoom_smoke.py"), str(folder)],
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


@pytest.mark.parametrize("index", range(3), ids=["zoom1", "zoom4", "zoom8"])
def test_tooltip_sits_just_above_the_pointer(results: dict, index: int) -> None:
    z = results["zooms"][index]
    assert z["opened"] and z["label"], z
    bx, by = z["bottom_centre"]
    mx, my = z["mouse"]
    assert abs(bx - mx) <= 2, z
    assert 4 <= my - by <= 12, z


def test_tooltip_keeps_its_size_at_every_zoom(results: dict) -> None:
    sizes = {(z["w"], z["h"]) for z in results["zooms"]}
    assert len(sizes) == 1, results["zooms"]
