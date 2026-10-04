# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A stick unplugged and plugged back in while the program runs, checked in
the running program off-screen (device_reconnect_smoke.py, its own process
and user folder).

- Screens set to a stick while it was unplugged stayed empty after it came
  back (the driver describes an absent stick as an empty device, which was
  kept): Input Configuration's list, the axis graph, live values, claimed
  inputs, Module Setup and Calibration now read it when it connects.
- Module Setup refuses Save while its stick is unplugged (the work on
  screen stays) and allows it again when the stick is back.
- Calibration's list follows the connected sticks; HidHide re-reads its
  list; Auto Mapper keeps its ticks.
- A button held (or a hat pushed) as its stick is unplugged is let go of,
  so nothing stays held on the outputs.
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
        [sys.executable, str(_ROOT / "test" / "unit" / "device_reconnect_smoke.py")],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


_EMPTY = {
    "input-configuration": 0,
    "axis-graph": 0,
    "live-values": 0,
    "claimed": False,
    "module-setup-rows": 0,
    "module-setup-save-refused": True,
    "calibration-axes": 0,
    "calibration-modules": 0,
}
# The stand-in stick: 6 axes, 64 buttons, 2 hats.
_READ = {
    "input-configuration": 72,
    "axis-graph": 6,
    "live-values": 72,
    "claimed": True,
    "module-setup-rows": 72,
    "module-setup-save-refused": False,
    "calibration-axes": 6,
    "calibration-modules": 1,
}


def test_screens_set_while_unplugged_read_the_stick_when_it_connects(run: dict) -> None:
    assert run["calibration-modules-plugged"] == 1
    assert run["unplugged"] == _EMPTY
    assert run["plugged-in"] == _READ
    assert run["back"] == _READ


def test_unplugging_keeps_what_is_shown_and_refuses_save(run: dict) -> None:
    assert run["unplugged-again"] == dict(
        _READ, **{"module-setup-save-refused": True, "calibration-modules": 0}
    )


def test_held_inputs_are_let_go_on_unplug(run: dict) -> None:
    assert run["let-go"] == [
        ["JoystickButton", 3, False, "None"],
        ["JoystickHat", 1, None, "HatDirection.Center"],
    ]
    assert run["held-after"] == [False, "HatDirection.Center"]


def test_hidhide_rereads_its_list(run: dict) -> None:
    # Once on opening, once for each change.
    assert run["hidhide-reads"] == 3


def test_auto_mapper_keeps_its_ticks(run: dict) -> None:
    assert run["auto-mapper"] == {"box": True, "ticked-after-replug": [True]}
