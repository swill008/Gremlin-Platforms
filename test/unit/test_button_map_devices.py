# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map window and its stick being plugged and unplugged, checked
in the running program off-screen (button_map_devices_smoke.py, its own
process and user folder).

- A stick that isn't connected shows "Connect <name>" over its map; the map
  loads by itself when the stick connects, and again after a replug (the
  window used to stay blank). Export still works without the stick.
- Unplugged during Edit Mapping, the edit stays on screen to save or
  cancel; other devices coming and going leave the editor alone.
- File -> Device stays in the menu during an edit (it used to vanish).
- Entering Edit Mapping is not a change: Cancel used to ask to save when
  the editor had only filled in what the file left out.
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
        [sys.executable, str(_ROOT / "test" / "unit" / "button_map_devices_smoke.py")],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def _shown(chips: int | None, connected: bool, shown: bool, editing: bool) -> dict:
    return {"chips": chips, "connected": connected, "shown": shown, "editing": editing}


def test_unplugged_stick_shows_no_map(run: dict) -> None:
    assert run["opened-unplugged"] == _shown(5, False, False, False)
    assert run["unplugged"] == _shown(5, False, False, False)


def test_unplugged_stick_still_exports(run: dict) -> None:
    assert run["export-while-unplugged"] is True


def test_map_loads_when_the_stick_connects(run: dict) -> None:
    assert run["plugged-in"] == _shown(5, True, True, False)
    assert run["plugged-in-again"] == _shown(5, True, True, False)


def test_outputs_and_built_in_devices_need_no_stick(run: dict) -> None:
    assert run["available"] == {
        "vJoy Device 1": True,
        "Xbox 360 Controller": True,
        "Keyboard": True,
        "pJoy Pro": True,
        "Nowhere Stick": False,
    }


def test_an_edit_survives_device_changes(run: dict) -> None:
    assert run["same-editor-after-other-stick"] is True
    assert run["unplugged-mid-edit"] == _shown(5, False, True, True)
    assert run["same-editor-after-unplug"] is True
    assert run["edit-ended-unplugged"] == _shown(5, False, False, False)
    assert run["back-after-edit"] == _shown(5, True, True, False)


def test_entering_edit_is_not_a_change(run: dict) -> None:
    assert run["unsaved-after-entering-edit"] is False
    assert run["unsaved-after-a-move"] is True


def test_device_menu_stays_during_an_edit(run: dict) -> None:
    assert run["device-menu-rows-while-editing"] >= 4
