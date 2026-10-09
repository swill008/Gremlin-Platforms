# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library, the fix wave (agent FM): the real window and dialogs
off-screen (device_library_LU_window_smoke.py, its "fm-" steps) with a twin
of Right stick plugged in: twins are told apart in the To lists and the copy
goes to the twin's id (S22, S26); Copy from a deleted stick's autosave onto
a stick with no bindings offers the open profile, ticked (S23, 08 S89,
D-10-PROFILES); Edit › Undo says "Undo" once (S41); Change vJoy Output
offers only the vJoys that exist (S30)."""

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
    out = tmp_path_factory.mktemp("dl_fm_window")
    proc = subprocess.run(
        [
            sys.executable,
            str(_HERE / "device_library_LU_window_smoke.py"),
            str(out),
            "fm-",
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


def test_s22_s26_twins_are_told_apart(run: dict) -> None:
    sticks = run["fm-copy-deleted"]["sticks"]
    assert sticks == [
        "Left throttle  (VKB Gladiator, the one with the sticky slider)",
        "Right stick [BBBB0002]  (VKB Gunfighter Mk IV)",
        "Right stick [EEEE0006]",
    ]
    assert run["fm-swap-twin"] == [
        "Left throttle  (VKB Gladiator, the one with the sticky slider)",
        "Right stick [EEEE0006]",
    ]
    copy = [c for c in run["calls"] if c[0] == "copy"][-1]
    assert copy[1] == "set-00000005" and copy[-1] == "{EEEE-0006}"


def test_s23_the_open_profile_is_offered_ticked(run: dict) -> None:
    got = run["fm-copy-to-twin"]
    assert got["to"] == "dev-00000006"
    assert got["profiles"] == ["DCS.xml:true"]
    assert got["chosen"] == ["C:/p/DCS.xml"]


def test_s53_undo_names_the_copy(run: dict) -> None:
    assert run["fm-copy-twin-go"]["undo"] == (
        "Undo Copied Autosave: stick deleted to Right stick"
    )


def test_s30_only_the_vjoys_that_exist(run: dict) -> None:
    got = run["fm-output-vjoys"]
    assert got["vjoys"] == [1, 2, 3]
    assert got["row1"] == ["vJoy 1", "vJoy 2", "vJoy 3"]


def test_twins_are_told_apart_in_the_list(run: dict) -> None:
    assert run["fm-list-twins"] == [
        "Right stick [BBBB0002]",
        "Right stick [EEEE0006]",
        "Left throttle",
    ]
