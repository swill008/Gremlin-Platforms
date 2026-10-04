# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's Print & Export window, checked in the running program
off-screen (print_export_window_smoke.py, its own process and user folder).

- File > Print & Export opens it and shows the print area on the map.
- Its paper and scale follow the map's settings; the page in the preview has
  the paper's shape and shows the print area's picture.
- It gives the export's size in pixels, the same as the export makes.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "print_export_window_smoke.py")],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_it_opens_with_the_print_area_shown(run: dict) -> None:
    assert run["open"] == [True, True]


def test_the_page_and_its_preview(run: dict) -> None:
    assert abs(run["page-shape"] - 8.5 / 11) < 0.001
    assert run["preview-ready"] is True
    assert run["paper-box"].startswith("Letter")
    assert run["scale-box"] == 50


def test_it_tells_the_export_size(run: dict) -> None:
    w, h = run["pixels"]
    assert run["pixels-text"] == f"Export: {w} × {h} pixels"
