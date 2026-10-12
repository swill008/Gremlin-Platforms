# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Print & Export with the Device Mapping Editor's two planes (07 S82, S83, S87, S89,
S123), checked in the running program off-screen (planes_print_smoke.py,
its own process and user folder). The map's background holds one plain red
picture of 800 x 400 pixels.

- The page colour setting is called "Page"; the tick "Include background"
  is on by default and kept in printSetup.includeBg.
- 100% scale is the bottom background picture's own pixels: exported at
  100% it is 800 x 400 pixels, at 50% 400 x 200.
- Both planes print at full strength: the screen's background opacity,
  hidden background, faint foreground and Background mode never reach the
  print.
- Without Include background the background is left out.
- A Light page leaves pictures unchanged.
- The renderer's snapshot carries no photo keys.
- Print & Export's export size is worked out without a binding loop.
- A picture over 4000 pixels on a side (drawn on screen from a screen-sized
  copy) prints from the original (07 S124): its 4-pixel stripes stay sharp.
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
_SMOKE = _ROOT / "test" / "unit" / "planes_print_smoke.py"


def _start(home: pathlib.Path, folder: pathlib.Path, *extra: str) -> proc_tree.Tree:
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    with (home / "stdout.txt").open("w") as out, (home / "stderr.txt").open("w") as err:
        return proc_tree.popen(
            [sys.executable, str(_SMOKE), str(folder), *extra],
            cwd=_ROOT, env=env, stdout=out, stderr=err,
        )


def _result(tree: proc_tree.Tree, home: pathlib.Path) -> dict:
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
    return json.loads(lines[0][len("RESULT "):])


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict:
    # Both at once, each in its own process and user folder.
    started = {}
    for kind in ("plain", "big"):
        home = tmp_path_factory.mktemp(f"home-{kind}")
        folder = tmp_path_factory.mktemp(f"out-{kind}")
        extra = ("big",) if kind == "big" else ()
        started[kind] = (_start(home, folder, *extra), home)
    return {kind: _result(tree, home) for kind, (tree, home) in started.items()}


@pytest.fixture(scope="module")
def run(runs: dict) -> dict:
    return runs["plain"]


def _near(box: list, want: tuple, slack: int = 3) -> bool:
    return abs(box[0] - want[0]) <= slack and abs(box[1] - want[1]) <= slack


def _full_red(shot: dict) -> bool:
    r, g, b = shot["middle"]
    return r >= 245 and g <= 12 and b <= 12


def test_page_setting_and_include_background_tick(run: dict) -> None:
    assert run["page-label"] == "Page"
    assert run["tick"] == ["Include background", True]
    assert run["setup-default"] is True
    assert run["tick-off"] == [False, False]
    assert run["tick-on"] == [True, True]


def test_snapshot_has_no_photo_keys(run: dict) -> None:
    assert "photo" not in run["snapshot-keys"].lower()


def test_100_percent_is_the_bottom_background_pictures_own_pixels(run: dict) -> None:
    assert _near(run["full-100"]["box"], (800, 400)), run["full-100"]
    assert _near(run["full-50"]["box"], (400, 200)), run["full-50"]
    assert _full_red(run["full-100"])


def test_screen_views_never_print(run: dict) -> None:
    # Opacity 0.2, faint foreground and Background mode, then hidden: the
    # print is the same full-strength picture (scale 50 by then).
    assert json.loads(run["live-views-down"]) == ["background", True, False, 0.2]
    assert json.loads(run["live-bg-hidden"])[2] is True
    for name in ("views-down", "bg-hidden-view"):
        shot = run[name]
        assert _near(shot["box"], (400, 200)), (name, shot)
        assert _full_red(shot), (name, shot)


def test_without_include_background_the_background_is_left_out(run: dict) -> None:
    assert run["no-bg"]["red"] == 0, run["no-bg"]


def test_light_page_leaves_pictures_unchanged(run: dict) -> None:
    assert _full_red(run["light"]), run["light"]
    assert run["live-exporting"] is False


def test_big_picture_prints_from_the_original(runs: dict) -> None:
    big = runs["big"]
    shot = big["full-100"]
    # The screen is far smaller than the picture: on screen it is a copy.
    assert big["screen-side"] < 4000
    # No strong red at all: drawn from a blurred screen copy.
    assert "box" in shot, shot
    assert _near(shot["box"], (4200, 300), slack=6), shot
    # Half the stripes are black: sharp, not blurred into dark red.
    assert shot["dark-share"] > 0.35, shot


def test_no_binding_loop_in_print_and_export(run: dict) -> None:
    assert run["binding-loops"] == []
