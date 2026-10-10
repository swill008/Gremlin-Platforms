# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-RESET-DEVICES: the Reset Devices window, opened from the HidHide
page by a real click in the real program off-screen
(device_reset_ui_smoke.py: fake hardware, fake HidHide driver, fake device
list, fake reset runner; pnputil is never run)."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

RESTART_TEXT = "needs a Windows restart, or unplug it and plug it back in"

_HERE = pathlib.Path(__file__).parent
R_USB = r"USB\VID_231D&PID_0200\9&AAC4F3F&0&2"
L_USB = r"USB\VID_231D&PID_3201\9&1D65FFE4&0&3"
P_USB = r"USB\VID_16D0&PID_0A38\7&11111111&0&1"
X_USB = r"USB\VID_045E&PID_0B12\8&6666&0&5"
WARNING = (
    "The ticked USB devices will be reset. Center your sticks before you "
    "press Reset: while a device restarts, the program keeps its axes where they "
    "were and releases its buttons."
)


def by_usb(state: dict, key: str) -> dict:
    """{usb id: value} for the plugged-in rows (sorted by name)."""
    return dict(zip(state["usb"], state[key], strict=False))


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("reset_ui_home")
    (home / "Gremlin Platforms").mkdir()
    work = tmp_path_factory.mktemp("reset_ui_work")
    shot = os.environ.get("GREMLIN_RESET_SHOT") or str(work / "reset.png")
    proc = subprocess.run(
        [sys.executable, str(_HERE / "device_reset_ui_smoke.py"), str(work), shot],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=150,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ,
            "USERPROFILE": str(home),
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
        },
    )
    results: dict = {"shot": shot}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    assert results.get("open") is True, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_the_page_has_a_red_reset_devices_button(run: dict) -> None:
    assert run["page-button"] == {"header": ["Reset Devices…"], "enabled": [True]}
    assert run["clicked"] is True


def test_hidden_devices_are_ticked_and_virtual_pads_are_not_listed(run: dict) -> None:
    first = run["first"]
    # Only plugged-in devices (02 S144 RW1a: the hidden stick that isn't
    # plugged in is not listed); no vJoy, no ViGEm pad.
    assert sorted(first["usb"]) == sorted([P_USB, L_USB, R_USB])
    assert by_usb(first, "names") == {
        P_USB: "Example pedals", L_USB: "VKBsim Gladiator EVO OT L",
        R_USB: "Right stick",
    }
    assert by_usb(first, "ticked") == {P_USB: False, L_USB: True, R_USB: True}
    assert first["enabled"] == [True, True, True]
    assert "not plugged in" not in first["results"]
    assert first["notes"] == []
    assert first["count"] == ["2 of 3 plugged-in devices ticked"]
    assert first["reset"] == ["Reset 2 Devices"]


def test_the_open_window_follows_unplug_and_plug_in(run: dict) -> None:
    """02 S144: the device-change signal drops and adds rows live; ticks,
    footer and Reset follow."""
    gone = run["unplugged"]
    assert sorted(gone["usb"]) == sorted([L_USB, R_USB])
    assert gone["count"] == ["2 of 2 plugged-in devices ticked"]
    back = run["replugged"]
    assert sorted(back["usb"]) == sorted([P_USB, L_USB, R_USB])
    # The pedals aren't hidden: back unticked.
    assert by_usb(back, "ticked") == {P_USB: False, L_USB: True, R_USB: True}
    assert back["reset"] == ["Reset 2 Devices"]


def test_an_xbox_pad_plugged_in_is_unticked_with_its_note(run: dict) -> None:
    """02 S145."""
    pad = run["xbox"]
    assert X_USB in pad["usb"]
    assert by_usb(pad, "ticked")[X_USB] is False
    assert pad["notes"] == [
        "Xbox pads can't be restarted live: unplug and plug back in"
    ]
    assert pad["count"] == ["2 of 4 plugged-in devices ticked"]


def test_the_warning_running_game_and_permission_lines(run: dict) -> None:
    first = run["first"]
    assert first["warning"] == [WARNING]
    assert first["games"] == [
        "StarCitizen.exe is running and will lose these devices for a moment."
    ]
    assert first["permission"] == ["Windows may ask for administrator permission."]


def test_ticks_follow_clicks(run: dict) -> None:
    # The first row (the pedals, not hidden) is clicked on, then off.
    assert run["first"]["usb"][0] == P_USB
    assert by_usb(run["untick"], "ticked")[P_USB] is True
    assert run["untick"]["count"] == ["3 of 3 plugged-in devices ticked"]
    assert run["untick"]["reset"] == ["Reset 3 Devices"]
    assert by_usb(run["tick"], "ticked")[P_USB] is False
    assert run["tick"]["reset"] == ["Reset 2 Devices"]


def test_declined_permission_touches_nothing(run: dict) -> None:
    res = run["declined"]
    assert res["clicked"] is True
    assert len(res["calls"]) == 1 and sorted(res["calls"][0]) == sorted([L_USB, R_USB])
    assert by_usb(res, "results") == {
        P_USB: "—", L_USB: "permission declined",
        R_USB: "permission declined",
    }
    assert res["close"] == ["Close"] and res["reset"] == []
    assert run["closed"] is True


def test_ticked_again_on_each_open_and_reset_shows_results(run: dict) -> None:
    assert by_usb(run["second"], "ticked") == by_usb(run["first"], "ticked")
    res = run["reset"]
    assert len(res["calls"]) == 1 and sorted(res["calls"][0]) == sorted([L_USB, R_USB])
    assert by_usb(res, "results") == {
        P_USB: "—", L_USB: RESTART_TEXT,
        R_USB: "reset ✓ · back after 0.0 s",
    }
    assert res["close"] == ["Close"] and res["reset"] == []
    assert res["enabled"] == [False, False, False]
    assert pathlib.Path(run["shot"]).is_file()


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []
