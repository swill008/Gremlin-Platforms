# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The hidden renderer's device's background picture (07 S157) and the 100%
export scale (07 S83), checked in the running program off-screen
(device_photo_render_smoke.py, its own process and user folder).

- DevicePhotoHost answers devicePhotoMaker's renderWanted: the visible
  background alone (hidden layers and the foreground left out), cut to the
  background's own extent, 1024 pixels on its longer side, drawn on black
  and on white so the transparent picture can be made from the two: its
  corners clear, a half-strength box at half strength, a flipped picture
  flipped.
- A background whose pictures give fewer pixels is not enlarged.
- No visible background: no picture, the maker hears "not done".
- 100% is the most detailed visible background picture's own pixels;
  hiding it hands 100% back to the next one; without picture sizes the
  bottom picture's own size is used.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "device_photo_render_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home-photo")
    folder = tmp_path_factory.mktemp("out-photo")
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    env.pop("SMOKE_QML_DIR", None)
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    with (home / "stdout.txt").open("w") as out, (home / "stderr.txt").open("w") as err:
        tree = proc_tree.popen(
            [sys.executable, str(_SMOKE), str(folder)],
            cwd=_ROOT,
            env=env,
            stdout=out,
            stderr=err,
        )
    try:
        tree.process.wait(timeout=150)
    except subprocess.TimeoutExpired:
        tree.kill()
        tree.process.wait()
        raise
    stdout = (home / "stdout.txt").read_text(errors="replace")
    stderr = (home / "stderr.txt").read_text(errors="replace")
    lines = [ln for ln in stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, stdout[-1500:] + stderr[-1500:]
    return json.loads(lines[0][len("RESULT ") :])


def test_the_host_answers_the_maker(run: dict) -> None:
    assert run["host-errors"] == []
    assert run["host-ready"] is True


def test_only_the_visible_background_is_drawn(run: dict) -> None:
    # Hidden picture and foreground chip left out.
    assert json.loads(run["area"]) == ["bg1", "bg3", "bg4"]
    assert run["whole"]["blue"] == 0


def test_the_picture_is_the_backgrounds_extent_at_1024(run: dict) -> None:
    whole = run["whole"]
    assert whole["done"] == ["whole", True]
    # The background covers x 0.1-0.65 and y 0.1-0.778 of the 1600 x 900
    # page: 880 x 610 page pixels, 1024 on the longer side.
    assert whole["size"][0] == 1024
    assert abs(whole["size"][1] - round(1024 * 610 / 880)) <= 2
    assert whole["white-size"] == whole["size"]


def test_the_ground_is_transparent(run: dict) -> None:
    whole = run["whole"]
    assert whole["has-alpha"] is True
    assert whole["corner-top-right"][3] == 0
    assert whole["corner-bottom-right"][3] == 0
    assert whole["red-middle"] == [255, 0, 0, 255]


def test_opacity_and_flip_are_kept(run: dict) -> None:
    whole = run["whole"]
    r, g, b, a = whole["green"]
    assert g > 200 and r < 40 and b < 40
    assert 110 <= a <= 145
    # The flipped picture (yellow left, black right) shows black on its left.
    assert whole["flip-left"][:3] == [0, 0, 0] and whole["flip-left"][3] == 255
    assert whole["flip-right"] == [255, 255, 0, 255]


def test_a_small_background_is_not_enlarged(run: dict) -> None:
    # One 300 x 150 picture: its own pixels, not 1024.
    assert run["small"]["size"] == [300, 150]


def test_no_visible_background_makes_no_picture(run: dict) -> None:
    assert run["empty"]["missing"] is True
    assert run["empty"]["done"] == ["empty", False]


def test_100_percent_is_the_most_detailed_background_picture(run: dict) -> None:
    geom = run["geom"]
    assert geom["ids"] == ["p1", "p2"]
    assert run["sized-100"] == pytest.approx(geom["dense"], rel=1e-6)
    assert run["sized-50"] == pytest.approx(geom["dense"] / 2, rel=1e-6)
    # Hidden, the denser picture no longer sets 100%.
    assert run["dense-hidden-100"] == pytest.approx(geom["bottom"], rel=1e-6)


def test_without_picture_sizes_the_bottom_picture_sets_100_percent(run: dict) -> None:
    geom = run["geom"]
    assert geom["natural"] == {"w": 800, "h": 400}
    assert run["fallback-100"] == pytest.approx(geom["bottom"], rel=1e-6)
