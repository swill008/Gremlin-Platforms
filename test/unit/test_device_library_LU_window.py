# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library: the real window (qml/WindowDeviceLibrary.qml and its
dialogs) with the real model over a stand-in Library, off-screen in its own
process (device_library_LU_window_smoke.py): menus (S1), chips, search and
Esc (S3, S5), caret (S10), details (S8, S11), rename and in-place
description (S7, S13), Copy / Swap / Change vJoy Output dialogs and their
warnings (S23, S27, S30-S31), Undo (S41), settings (S36), tidy (S38),
drop import (S39), double-click to Copy (S40), Delete asks (S15), and
opening on a card's device (S2)."""

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
    out = tmp_path_factory.mktemp("dl_window")
    proc = subprocess.run(
        [sys.executable, str(_HERE / "device_library_LU_window_smoke.py"), str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_HERE.parents[1]),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1"},
    )
    results: dict = {"errors": [], "warnings": [], "calls": [], "out": out}
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


def _call(run: dict, name: str) -> list:
    return [c for c in run["calls"] if c[0] == name]


def test_loads_without_errors_or_warnings(run: dict) -> None:
    assert run["errors"] == []
    assert run["warnings"] == []
    for shot in ("main", "menu", "copy", "swap", "output", "settings", "tidy"):
        assert (run["out"] / f"{shot}.png").stat().st_size > 1000


def test_s1_s4_window_menus_and_status(run: dict) -> None:
    opens = run["opens"]
    assert opens["title"] == "Device Library" and opens["rows"] == 5
    assert opens["status"].startswith("5 devices · 6 saved setups")
    assert "Library: 48 MB" in opens["status"]
    assert run["menu"] == (
        "Save to Device Library…|-|Copy to Another Stick…|"
        "Swap with Another Stick…|Change vJoy Output…"
    )
    # Undo is left out while there is nothing to undo (01 S66).
    assert run["edit-menu"] == "Rename… (F2)|Delete…|-|Tidy Library…"
    assert run["view-menu"].startswith(
        "Connected|Not Connected|Deleted|Autosaves|-|Expand All"
    )


def test_s3_s5_s10_list(run: dict) -> None:
    assert run["caret"][:4] == [
        "dev-00000001",
        "set-00000001",
        "set-00000002",
        "set-00000003",
    ]
    assert run["filter-chip"]["filters"]["deleted"] is False
    assert "dev-00000004" not in run["filter-chip"]["rows"]
    assert "dev-00000004" in run["filter-back"]
    assert run["search"] == ["dev-00000001", "set-00000001"]
    assert run["search-esc"]["text"] == ""


def test_s7_s8_s11_s13_details_names_descriptions(run: dict) -> None:
    sel = run["select-setup"]
    assert sel["name"] == "DCS F-16, Viper layout"
    assert sel["bindings"] == [
        "Bindings from DCS.xml · modes Default, Landing, AAR · 212 actions"
    ]
    assert sel["copy"] and sel["swap"] and sel["del"]
    assert run["rename"] == {"name": "Kept for later", "mark": "own"}
    assert run["describe"] == "New words"
    # Typed, then another row selected: kept for the row it was typed on.
    assert run["describe-then-move"]["kept"] == "Typed then moved"
    assert ["describe", "set-00000003", "Typed then moved"] in run["calls"]
    dev = run["device-details"]
    # S15 (changed 2026-10-08, D-10-REMOVE): a device that isn't connected
    # can be removed from the Library (Remove from Library…).
    assert dev["state"] == "Not connected" and not dev["swap"] and dev["del"]


def test_s23_s25_s41_copy_and_undo(run: dict) -> None:
    copy = run["copy"]
    assert copy["from"] == "Left throttle  ›  DCS F-16, Viper layout"
    assert copy["to"] == "Right stick"
    assert copy["sticks"] == ["Left throttle", "Right stick"]
    # Calibration unticked by default; only the open profile ticked.
    assert copy["parts"] == ["setup", "button_map", "appearance", "bindings"]
    assert copy["profiles"] == [
        "DCS.xml:true",
        "StarCitizen.xml:false",
        "Elite.xml:false",
    ]
    assert copy["warnings"] == 3
    assert run["copy-go"]["undo"] == "Undo Copy to Right stick"
    assert _call(run, "copy")[0][2] == "Right stick"
    assert run["undo"]["undo"] == "" and _call(run, "undo_last")


def test_s40_double_click_opens_copy(run: dict) -> None:
    assert run["double-click"]["from"] == "Right stick  ›  Elite night setup"


def test_s27_s30_s31_swap_and_output(run: dict) -> None:
    swap = run["swap"]
    assert swap["first"] == "Left throttle" and swap["other"] == ["Right stick"]
    assert len(swap["warnings"]) == 2
    out = run["output"]
    assert [r["vjoy"] for r in out["rows"]] == [1, 2] and not out["anyChange"]
    moved = run["output-move"]
    assert moved["other"]["text"] == (
        "Also move Right stick from vJoy 2 to vJoy 1 (swap them)"
    )
    assert moved["swapOtherShown"]
    assert moved["warnings"] == 2


def test_s36_s38_settings_and_tidy(run: dict) -> None:
    s = run["settings"]
    assert s["parts"]["calibration"] is False and s["parts"]["bindings"] is True
    assert _call(run, "set_settings")
    assert run["tidy"]["items"] == ["set-00000005"]
    assert _call(run, "tidy") == [["tidy", "['set-00000005']"]]
    assert "set-00000005" not in run["tidy-remove"]


def test_s39_drop_imports_the_zip(run: dict) -> None:
    assert run["drop"] == "Device Pack added as a saved setup."
    assert [c[1] for c in _call(run, "import_pack")] == [
        str(pathlib.Path("C:/x/Sam MFDs.zip"))
    ]


def test_s15_delete_asks_first(run: dict) -> None:
    assert run["delete"] == "Delete the saved setup “Sam's MFDs”?"
    assert ["delete", "set-00000006"] in run["calls"]


def test_s2_opens_on_a_cards_device(run: dict) -> None:
    assert run["open-on"] == {"selected": "dev-00000002", "first": "Right stick"}


def test_s22_copy_takes_a_devices_current_settings(run: dict) -> None:
    # A device row copies its current settings (module file and bindings),
    # also when it has no saved setup (LF).
    assert run["copy-from-device"] == {
        "from": "Right stick  ›  current settings",
        "selected": "dev-00000002",
        "source": "dev-00000002",
    }
    cur = run["copy-current"]
    assert cur["open"] is True
    assert cur["from"] == "Rudder pedals  ›  current settings"
    assert cur["source"] == "dev-00000003"
    assert cur["modes"] == ["Default", "Combat"]
    assert cur["parts"] == ["setup", "button_map", "bindings"]
    # The open profile, never saved, is passed on as "" (S33).
    assert cur["profiles"] == [""]
    copies = _call(run, "copy")
    assert copies[-1][1] == "dev-00000003" and copies[-1][4] == "['.']"


def test_s8_device_inputs_and_last_seen(run: dict) -> None:
    dev = run["device-details"]
    assert dev["inputs"] == "Inputs: no buttons, 3 axes, no hats"
    assert dev["seen"] == "Last seen 2026-10-05 18:30"


def test_s11_photo_preview(run: dict) -> None:
    assert run["photo"] == {"shown": True, "placeholder": False}


def test_s12_save_passes_the_never_saved_open_profile(run: dict) -> None:
    assert run["save-unsaved-open"] == [""]
