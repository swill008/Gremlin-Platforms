# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-INPUT-TESTER window end to end: input_tester.py started off-screen
(input_tester_ui_smoke.py) on fake hardware with an expected.json, once for
a Fail case (the stick Gremlin hides is seen) and once for a Pass case.
The verdict line, the red row, a real click that selects a row and shows
its axes, a fake button press that lights its cell, and no QML warnings."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent
# Screenshots for a person to look at (not checked).
_SHOTS = pathlib.Path(os.environ.get("INPUT_TESTER_SHOTS", ""))


def _run(case: str, tmp: pathlib.Path) -> dict:
    home = tmp / "home"
    gremlin_dir = home / "Gremlin Platforms"
    gremlin_dir.mkdir(parents=True)
    shot = (_SHOTS if str(_SHOTS) not in ("", ".") else tmp) / f"tester_{case}.png"
    proc = subprocess.run(
        [
            sys.executable,
            str(_HERE / "input_tester_ui_smoke.py"),
            case,
            str(gremlin_dir),
            str(shot),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ,
            "USERPROFILE": str(home),
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
        },
    )
    out: dict = {"errors": [], "qtlog": None}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            out[name] = json.loads(value)
        elif line.startswith("ERROR"):
            out["errors"].append(line)
        elif line.startswith("QTLOG "):
            out["qtlog"] = json.loads(line[6:])
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return out


@pytest.fixture(scope="module")
def fail_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run("fail", tmp_path_factory.mktemp("tester_fail"))


@pytest.fixture(scope="module")
def pass_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run("pass", tmp_path_factory.mktemp("tester_pass"))


@pytest.mark.parametrize("which", ["fail_run", "pass_run"])
def test_runs_without_errors_or_qml_warnings(
    which: str, request: pytest.FixtureRequest
) -> None:
    run = request.getfixturevalue(which)
    assert run["errors"] == []
    assert run["qtlog"] == []
    assert run["shot"] is True


def test_fail_verdict_and_red_row(fail_run: dict) -> None:
    verdict = fail_run["verdict"]
    assert verdict["line_visible"] is True
    assert verdict["text"] == "✗ Problem:"
    assert verdict["summary"] == "programs can see 1 stick that should be hidden"
    assert verdict["context"].startswith(
        "This window tests what a blocked program sees. It's on HidHide's Block "
        "list, so your hidden sticks should not show up here. (Gremlin's list "
        "from 03:14)"
    )
    assert fail_run["rows"]["stick"] == {"bad": True}
    assert fail_run["rows"]["vjoy"] == {"bad": False}


def test_fail_row_shows_fix_hint(fail_run: dict) -> None:
    """S1: the fix hint under the failing row only."""
    hints = fail_run["hints"]
    assert hints["Left stick"] == [
        "Tick it on Gremlin's HidHide page, then press Restart tester."
    ]
    assert all(v == [] for k, v in hints.items() if k != "Left stick")


def test_pass_rows_have_no_hint_and_plain_headings(pass_run: dict) -> None:
    assert all(v == [] for v in pass_run["hints"].values())
    headings = pass_run["headings"]
    assert "YOUR CONTROLLERS" in headings
    assert "GREMLIN'S VIRTUAL JOYSTICKS (vJoy)" in headings
    assert "ALL GAME DEVICES IN WINDOWS (list only)" in headings


@pytest.mark.parametrize("which", ["fail_run", "pass_run"])
def test_status_line_plain(which: str, request: pytest.FixtureRequest) -> None:
    """TW13, singular forms: one stick + vJoy, no Xbox, no listed game device."""
    assert request.getfixturevalue(which)["status_line"] == (
        "This window sees 2 joysticks · 0 Xbox controllers · 0 game devices · "
        "updating 62 times a second"
    )


@pytest.mark.parametrize("which", ["fail_run", "pass_run"])
def test_show_details_folds_game_devices(
    which: str, request: pytest.FixtureRequest
) -> None:
    """S3 by real clicks: closed at start, opens, closes again."""
    assert request.getfixturevalue(which)["details"] == {
        "toggle_visible": True,
        "heading_visible": True,
        "closed": [False],
        "open": [True],
        "closed_again": [False],
    }


def test_hidden_row_detail_line(pass_run: dict) -> None:
    """TW10/TW11 by a real click on the hidden stick."""
    assert pass_run["not_seen"] == {
        "detail": "Hidden from programs, so there's nothing to show.",
        "detail_visible": True,
        "should_be": "Should be: hidden from programs",
    }


def test_pass_verdict_no_red_row(pass_run: dict) -> None:
    verdict = pass_run["verdict"]
    assert verdict["line_visible"] is True
    assert verdict["text"] == "✓ Pass: programs see only what they should"
    assert verdict["summary"] == "(1 hidden · 2 shown)"
    assert pass_run["rows"]["stick"] == {"bad": False}
    assert pass_run["rows"]["vjoy"] == {"bad": False}


@pytest.mark.parametrize("which", ["fail_run", "pass_run"])
def test_click_selects_row_and_shows_axes(
    which: str, request: pytest.FixtureRequest
) -> None:
    sel = request.getfixturevalue(which)["select"]
    assert sel["detail"] == "vJoy Device 1"
    assert sel["row_selected"] is True
    assert sel["axes"] == 6
    assert sel["first_axis"] == -0.5


@pytest.mark.parametrize("which", ["fail_run", "pass_run"])
def test_left_out_hid_row_dimmed(which: str, request: pytest.FixtureRequest) -> None:
    """Item 6c: a HID path HidHide hides from the tester shows as a dimmed
    "left out" row."""
    skipped = request.getfixturevalue(which)["hid_skipped"]
    assert skipped == [
        {
            "label": "left out: access denied (hidden from this program)",
            "visible": True,
            "opacity": 0.65,
        }
    ]


def test_follow_input_selects_moved_device(pass_run: dict) -> None:
    """Item 7: an axis moved on another device selects and shows it;
    jitter under 0.05 doesn't; the All devices view never switches."""
    follow = pass_run["follow"]
    assert follow["switch_visible"] is True
    assert follow["switch_on"] is True
    assert follow["jitter_detail"] == "vJoy Device 1"
    assert follow["moved"] == {
        "detail": "Left stick",
        "row_selected": True,
        "vjoy_selected": False,
    }
    assert follow["all_view"] == {
        "compact_visible": True,
        "vjoy_selected": False,
        "detail_visible": False,
    }


def test_logs_tab_pick_find_follow(pass_run: dict) -> None:
    logs = pass_run["logs"]
    assert logs["logs_visible"] is True
    assert logs["devices_hidden"] is True
    assert logs["choices"] >= 2  # tester log + dill_debug.log at least
    assert logs["picked"] == "Tester log (tester.log)"
    assert logs["lines"] > 0
    assert any(t.startswith("Started") for t in logs["texts"]), logs["texts"]
    assert "tester.log" in logs["status"]
    assert logs["follow_after_off"] is False
    assert logs["follow_after_on"] is True
    assert logs["at_end"] is True
    assert logs["find_matches"] and all(
        "started" in t.lower() for t in logs["find_matches"]
    )
    assert logs["find_count"] != "none"
    assert logs["warnings_only_all_warn"] is True


def test_stale_banner_and_restart(pass_run: dict) -> None:
    stale = pass_run["stale"]
    assert stale["before"] is False
    assert stale["after"] is True
    assert "HidHide changed after this tester started (program list" in stale["text"]
    assert len(stale["started"]) == 1
    assert stale["quits"] == 1


@pytest.mark.parametrize("which", ["fail_run", "pass_run"])
def test_fake_button_press_lights_cell(
    which: str, request: pytest.FixtureRequest
) -> None:
    button = request.getfixturevalue(which)["button"]
    assert button == {"before": False, "after": True, "other": False}
