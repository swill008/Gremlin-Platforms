# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's Print & Export window, checked in the running program
off-screen (print_export_window_smoke.py, its own process and user folder),
at screen scales 1 and 1.5 (on a 150% screen an export once lost a third of
the print area).

- File > Print & Export opens it and shows the print area on the map.
- Its paper and scale follow the map's settings; the page in the preview has
  the paper's shape and shows the print area's picture. Freeform (As Drawn)
  under Custom sets no paper (the Paper list greys out) and unticked goes
  back to the last paper.
- It gives the export's size in pixels, the same as the export makes.
- An export is exactly that size; a print area's export is the same picture
  as that part of the whole page's; both screen scales give the same
  picture, and so does a larger scale; Light is a white page; the map on screen is never put into
  export mode.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest
from PySide6 import QtCore, QtGui

_ROOT = pathlib.Path(__file__).parents[2]
_SCALES = ("1", "1.5")


def _smoke(folder: pathlib.Path, home: pathlib.Path, scale: str) -> dict:
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        QT_SCALE_FACTOR=scale, HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "print_export_window_smoke.py"),
         str(folder)],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = {}
    for scale in _SCALES:
        folder = tmp_path_factory.mktemp("out")
        out[scale] = (_smoke(folder, tmp_path_factory.mktemp("home"), scale), folder)
    return out


@pytest.fixture(scope="module")
def run(runs: dict) -> dict:
    return runs["1"][0]


def _image(path: pathlib.Path) -> QtGui.QImage:
    image = QtGui.QImage(str(path))
    assert not image.isNull(), path
    return image.convertToFormat(QtGui.QImage.Format.Format_RGB32)


def _difference(a: QtGui.QImage, b: QtGui.QImage) -> float:
    """Mean difference per color channel (0-255), b scaled to a's size."""
    b = b.scaled(a.size(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                 QtCore.Qt.TransformationMode.SmoothTransformation)
    total = 0
    count = 0
    for y in range(0, a.height(), 3):
        for x in range(0, a.width(), 3):
            p = a.pixelColor(x, y)
            q = b.pixelColor(x, y)
            total += abs(p.red() - q.red()) + abs(p.green() - q.green()) + abs(p.blue() - q.blue())
            count += 3
    return total / max(1, count)


def _busy(image: QtGui.QImage) -> float:
    """The share of the picture not the color of its corner (0: flat)."""
    first = image.pixelColor(0, 0)
    differ = 0
    count = 0
    for y in range(0, image.height(), 4):
        for x in range(0, image.width(), 4):
            count += 1
            if image.pixelColor(x, y) != first:
                differ += 1
    return differ / max(1, count)


def test_it_opens_with_the_print_area_shown(run: dict) -> None:
    assert run["open"] == [True, True]


def test_the_page_and_its_preview(run: dict) -> None:
    assert abs(run["page-shape"] - 8.5 / 11) < 0.001
    assert run["preview-ready"] is True
    assert run["paper-box"].startswith("Letter")
    assert run["scale-box"] == 50


def test_freeform_is_no_paper(run: dict) -> None:
    # The Paper list has only papers; Freeform (As Drawn) is the tick box.
    assert run["paper-count"] == 6
    on = run["freeform-on"]
    assert on[:3] == [True, False, "fit"]
    assert on[3].startswith("Letter")
    assert run["freeform-off"][:3] == [False, True, "letter"]


def test_it_tells_the_export_size(run: dict) -> None:
    w, h = run["pixels"]
    assert run["pixels-text"].startswith(f"Export: {w} × {h} pixels\nOn the paper: ")
    assert run["pixels-text"].endswith(" dpi")


@pytest.mark.parametrize("scale", _SCALES)
def test_exports_are_the_size_given(runs: dict, scale: str) -> None:
    result, folder = runs[scale]
    for name in ("full", "area", "light"):
        w, h, written = result[name]
        assert written, name
        image = QtGui.QImage(str(folder / f"{name}.png"))
        assert (image.width(), image.height()) == (w, h), name
    # 50% of a page 1920 px wide (no photo); the area half of it.
    assert result["full"][0] == 960
    assert abs(result["area"][0] - 480) <= 1
    assert result["pdf"][2] is True
    assert result["live-exporting"] is False


@pytest.mark.parametrize("scale", _SCALES)
def test_the_print_area_is_that_part_of_the_page(runs: dict, scale: str) -> None:
    _result, folder = runs[scale]
    full = _image(folder / "full.png")
    area = _image(folder / "area.png")
    w, h = full.width(), full.height()
    part = full.copy(round(0.25 * w), round(0.2 * h), round(0.5 * w), round(0.5 * h))
    assert _busy(area) > 0.003
    assert _difference(area, part) < 6


def test_every_screen_scale_gives_the_same_picture(runs: dict) -> None:
    one = runs["1"][1]
    other = runs["1.5"][1]
    assert runs["1.5"][0]["dpr"] == 1.5
    for name in ("full.png", "area.png"):
        assert _difference(_image(one / name), _image(other / name)) < 6, name


@pytest.mark.parametrize("scale", _SCALES)
def test_a_larger_export_is_the_same_picture(runs: dict, scale: str) -> None:
    """Drawn at four times the pixels, not enlarged: lines, borders and
    text keep their size on the page."""
    result, folder = runs[scale]
    assert result["full-200"][0] == 3840
    big = _image(folder / "full-200.png")
    assert _difference(_image(folder / "full.png"), big) < 6


def test_light_is_a_white_page(runs: dict) -> None:
    folder = runs["1"][1]
    light = _image(folder / "light.png")
    dark = _image(folder / "area.png")
    assert light.pixelColor(1, 1).lightness() > 240
    assert dark.pixelColor(1, 1).lightness() < 80
