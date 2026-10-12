# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device's background picture on the real path (07 S157, S127),
checked in the running program off-screen (device_photo_e2e_smoke.py, its
own process and user folder): the main window's maker and host, the
Device Mapping Editor's Save slot, the store's key and the photo every
page shows.

- Saving a map with a background makes pictures/device-photo.png: at most
  1024 pixels on its longer side, cut to the visible background's extent,
  on a transparent ground; the hidden layer and the foreground chip are
  left out; its key is current and profilePhotoUrl shows it.
- A Save that moves only the foreground makes nothing new.
- A Save with no background left removes the file; no photo is shown.
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
_SMOKE = _ROOT / "test" / "unit" / "device_photo_e2e_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home-device-photo")
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    with (home / "stdout.txt").open("w") as out, (home / "stderr.txt").open("w") as err:
        tree = proc_tree.popen(
            [sys.executable, str(_SMOKE)],
            cwd=_ROOT, env=env, stdout=out, stderr=err,
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
    result = json.loads(lines[0][len("RESULT "):])
    assert "crash" not in result, (result, stderr[-2000:])
    return result


def _is(rgba: list, rgb: tuple) -> bool:
    return rgba[3] >= 240 and all(abs(a - b) <= 12 for a, b in zip(rgba, rgb))


def test_the_main_window_hosts_the_maker(run: dict) -> None:
    assert run["maker"] == "DevicePhotoMaker", run
    assert run["host-ready"] is True, run
    assert run["start-file"] is False, run


def test_saving_a_background_makes_the_background_picture(run: dict) -> None:
    assert run["save-bg"] is True
    assert run["made"] is True, run
    assert run["renders-1"] >= 1, run
    w, h = run["size"]
    # The visible background spans 0.7 x 0.7 of the 16:9 page; its detail
    # (800 pixels over 0.4 of 1600) asks for more than 1024 pixels.
    assert max(w, h) == 1024, run["size"]
    assert abs(w / h - (0.7 * 16) / (0.7 * 9)) < 0.03, run["size"]
    assert run["has-alpha"] is True


def test_background_picture_shows_the_visible_background_only(run: dict) -> None:
    assert _is(run["red"], (255, 0, 0)), run["red"]
    assert _is(run["blue"], (0, 0, 255)), run["blue"]
    # The hidden green picture and the chip's corner: transparent ground.
    assert run["hidden-green"][3] <= 10, run["hidden-green"]
    assert run["chip-corner"][3] <= 10, run["chip-corner"]


def test_background_picture_key_is_current_and_shown(run: dict) -> None:
    assert not run["errors"], run["errors"]
    assert run["file-key"], run
    assert run["file-key"] == run["store-key"] == run["store-file-key"], run
    assert run["current"] is True
    assert "device-photo.png" in run["photo-url"], run["photo-url"]


def test_a_foreground_only_save_makes_nothing(run: dict) -> None:
    assert run["save-fg"] is True
    assert run["renders-fg"] == 0, run
    assert run["mtime-2"] == run["mtime-1"], run


def test_no_background_removes_the_background_picture(run: dict) -> None:
    assert run["save-none"] is True
    # The file was there first (made by the background Save), then went.
    assert run["made"] is True, run
    assert run["removed"] is True, run
    assert run["photo-url-none"] == "", run["photo-url-none"]
