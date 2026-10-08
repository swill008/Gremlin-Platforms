# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fixes F3: Device Information's list and Calibration waiting for
a stick (spec 02 S9 / Q6, 03 S101). (The Swap Devices window these fixes
also covered, 04 S80, was replaced by the Device Library, D-10-SWAP.)

02 S9: DeviceListModel.deviceType had no getter, so QML's
`deviceType: "information"` was silently dropped and Device Information
left out the left-out vJoy; Swap Devices' "physical" was dropped too.

03 S101: Calibration opened for a stick not plugged in picked the first
connected stick and stayed on it after the stick was plugged in.

Each runs the real windows off-screen in its own process
(handson_F3_windows_smoke.py) with stand-in hardware.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import pathlib
import subprocess

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "handson_F3_windows_smoke.py"


def _run(tmp_path: pathlib.Path, *args: str) -> dict:
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, str(_SMOKE), *args], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    out = json.loads(lines[-1][len("RESULT "):])
    assert "error" not in out, out
    return out


def test_device_information_lists_the_left_out_vjoy(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "devinfo")
    assert "vJoy Device — left out (see message)" in out["devinfo-names"], out
    assert "pJoy Pro" in out["devinfo-names"], out


def test_calibration_waits_for_a_stick_not_plugged_in(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, "calib")
    before, after = out["before"], out["after"]
    # Waiting: no other stick shown in its place.
    assert before["shown"] == "second_stick", out
    assert before["current"] == "" and before["axes"] == 0, out
    assert before["not-connected"], out
    # Plugged in: it is shown.
    assert after["shown"] == "second_stick", out
    assert after["current"] == "Second Stick" and after["axes"] > 0, out
    assert not after["not-connected"], out


def test_the_device_type_reads_back() -> None:
    """A QML property needs a getter: without one QML drops the value."""
    from gremlin.ui.device import DeviceListModel

    meta = DeviceListModel.staticMetaObject
    prop = meta.property(meta.indexOfProperty("deviceType"))
    assert prop.isReadable() and prop.isWritable()
