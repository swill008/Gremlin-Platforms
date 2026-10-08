# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library, the last fix round (agent FM2): the real window and
dialogs off-screen (device_library_LU_window_smoke.py, its "fm2-" steps),
with a stick plugged in that has no module file (Throttle Quadrant):

- S12: Save to Device Library… is enabled for it (its bindings can be
  saved) and its dialog offers the open profile, ticked; it is disabled on
  a Deleted device's saved setup (nothing current to save).
- S30: Change vJoy Output… is enabled for an unplugged stick; the "Also
  move" line names every other stick on the target vJoy, each with its own
  vJoys.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("dl_fm2_window")
    proc = subprocess.run(
        [
            sys.executable,
            str(_HERE / "device_library_LU_window_smoke.py"),
            str(out),
            "fm2-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_HERE.parents[1]),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1"},
    )
    results: dict = {"errors": [], "warnings": [], "calls": []}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            value = json.loads(value)
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
            results[name] = value
        elif line.startswith("ERROR"):
            results["errors"].append(line)
        elif line.startswith("WARN"):
            results["warnings"].append(line)
        elif line.startswith("CALLS "):
            results["calls"] = json.loads(line[6:])
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_no_errors(run: dict) -> None:
    assert run["errors"] == []


def test_s12_save_is_enabled_for_a_plugged_in_stick_with_no_module_file(
    run: dict,
) -> None:
    assert run["fm2-save-connected-no-module"] == {"button": True, "menu": True}


def test_s12_the_save_dialog_offers_the_open_profile_ticked(run: dict) -> None:
    # The open profile has no bindings for it (0 actions): listed only
    # because the dialog asks with alwaysOpen.
    got = run["fm2-save-dialog"]
    assert got == {"profiles": ["DCS.xml:true"], "save": True}


def test_s12_save_is_disabled_on_a_deleted_devices_saved_setup(run: dict) -> None:
    assert run["fm2-save-deleted-setup"] == {"menu": False, "canSave": False}


def test_s30_change_vjoy_output_for_an_unplugged_stick(run: dict) -> None:
    assert run["fm2-output-unplugged"] == {"button": True, "menu": True}


def test_s30_also_move_names_every_other_stick(run: dict) -> None:
    assert run["fm2-output-also-move"] == (
        "Also move Right stick from vJoy 2 to vJoy 1,"
        " and Rudder pedals from vJoy 3 to vJoy 1 (swap them)"
    )
