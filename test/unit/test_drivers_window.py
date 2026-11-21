# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Tools > Drivers (06 S185), the one driver prompt (S187), Open Drivers on
the Xbox driver line (S188) and Home's "HidHide update not finished" line
(S186). Runs the real QML off-screen in its own process with a fake
DriversModel (the contract's API), a temp USERPROFILE."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import proc_tree  # noqa: E402  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
_SMOKE = _HERE / "drivers_window_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
               HTTPS_PROXY="http://127.0.0.1:9")
    done = proc_tree.run([sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
                         text=True, encoding="utf-8", errors="replace",
                         timeout=150)
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[-1][len("RESULT "):])


def test_no_errors(run: dict) -> None:
    assert run["errors"] == []


def test_one_row_per_driver_with_its_label(run: dict) -> None:
    assert run["title"] == "Drivers"
    assert run["names"] == {
        "vjoy": "vJoy", "vigembus": "ViGEmBus", "hidhide": "HidHide",
    }
    assert run["labels"]["vjoy"] == "not installed"
    assert run["labels"]["vigembus"] == "update available: 1.21.442.0 → 1.22.0"
    assert run["labels"]["hidhide"] == "1.5.230"


def test_tick_boxes_only_where_tickable(run: dict) -> None:
    assert run["tickVisible"] == {"vjoy": True, "vigembus": True, "hidhide": False}
    assert run["tickChecked"]["vjoy"] is True
    assert run["tickChecked"]["vigembus"] is False
    assert "tick vigembus True" in run["calls"]


def test_vjoy_section(run: dict) -> None:
    assert run["current"] == "Device 1: 6 axes, 32 buttons, 1 hats"
    assert run["customVisible"] is False
    assert run["customAfter"] is True
    assert (run["axesMax"], run["buttonsMax"], run["hatsMax"]) == (8, 128, 4)
    assert run["countRange"] == [1, 16]
    assert run["warningVisible"] is False
    assert run["warning"] == ""


def test_apply_asks_first_then_runs(run: dict) -> None:
    assert run["applyText"] == "Apply"
    assert run["promptOpen"] is True
    assert run["promptBody"] == "Install vJoy 2.2.2.0 now."
    assert run["applyBeforeOk"] is False
    assert run["applyAfterOk"] is True


def test_results_and_restart_buttons(run: dict) -> None:
    assert run["result0"] == "vJoy: Installed 2.2.2.0"
    assert run["restartVisible"] is True
    assert "restartNow" in run["calls"]
    assert run["restartHidden"] is True


def test_finish_hidhide_on_open_installs_then_asks_for_the_restart(run: dict) -> None:
    assert "finishHidHide" in run["finishCalls"]
    assert run["restartPromptTitle"] == "HidHide is installed: one more restart"
    assert run["restartPromptBody"] == (
        "Restart Windows to finish. Your devices aren't hidden until then."
    )
    assert run["restartPromptOk"] == "Restart now"
    assert run["restartPromptCancel"] == "Restart later"


def test_xbox_driver_line_opens_drivers(run: dict) -> None:
    assert run["openDrivers"] == "Open Drivers"
    assert run["testButton"] == "Test ViGEmBus"
    assert run["xboxSignals"] == ["driversRequested"]


def test_home_shows_the_unfinished_update_line(run: dict) -> None:
    assert run["homeNotice"] is True
    assert run["homeText"] == "HidHide update not finished: devices aren't hidden"
    assert run["homeButton"] == "Finish update"


def test_old_get_button_and_old_hint_are_gone() -> None:
    text = (_ROOT / "qml" / "XboxDriverCheck.qml").read_text(encoding="utf-8")
    assert "Get ViGEmBus" not in text
    from gremlin.modules import output
    out = output.vjoy_driver_problem
    src = pathlib.Path(output.__file__).read_text(encoding="utf-8")
    assert "Open Tools › Drivers to install vJoy, then restart the program." in src
    assert out is not None
