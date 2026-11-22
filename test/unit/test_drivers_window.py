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


def test_rows_are_vjoy_vigembus_hidhide(run: dict) -> None:
    """06 S185 (1b): no Visual C++ Runtime rows."""
    assert run["rowOrder"] == [
        "driverRow_vjoy", "driverRow_vigembus", "driverRow_hidhide"]


def test_vjoy_section(run: dict) -> None:
    """S185 layout (2026-11-22): heading, rows always shown, the heading
    band from drivers.VJOY_AXIS_LABELS, the hint and the Showing line."""
    from gremlin import drivers

    assert run["oldNowLines"] is False
    assert run["heading"] == "vJoy devices"
    assert run["presetFirst"] == "1 device, full"
    assert run["rowBeforeCustom"] is True
    assert run["rowName0"] == "vJoy 1"
    assert run["heads"] == [*drivers.VJOY_AXIS_LABELS, "Buttons", "Hats"]
    assert run["hint"] == (
        "Each device needs its own number of axes, buttons or hats, "
        "so Gremlin-Platforms can tell them apart."
    )
    assert run["showingOne"] == "Showing 1 device"
    assert run["customAfter"] is True
    # The Buttons and Hats lists: 0-128 and 0-4.
    assert (run["buttonsMax"], run["hatsMax"]) == (129, 5)
    assert run["countRange"] == [1, 16]
    assert run["warningVisible"] is False
    assert run["warning"] == ""


def test_each_device_has_eight_axis_tick_boxes(run: dict) -> None:
    assert run["oldAxesBox"] is False  # the axes number box is gone
    assert run["axisBoxes"] == ["X", "Y", "Z", "Rx", "Ry", "Rz", "S1", "S2"]
    assert run["axisChecked"] == [True] * 8


def test_unticking_an_axis_changes_the_device_through_the_model(run: dict) -> None:
    assert "axis 0 rx False" in run["calls"]
    assert run["axisCheckedAfter"] == [True, True, True, False, True, True, True, True]
    assert run["deviceAxesAfter"] == ["x", "y", "z", "ry", "rz", "sl0", "sl1"]
    assert run["presetAfterAxis"] == "Custom"


def test_apply_asks_first_then_runs(run: dict) -> None:
    assert run["applyText"] == "Apply"
    assert run["promptOpen"] is True
    assert run["promptBody"] == "Install vJoy 2.2.2.0 now."
    assert run["applyBeforeOk"] is False
    assert run["applyAfterOk"] is True


def test_alike_devices_ask_yes_or_no_after_ok(run: dict) -> None:
    """D-01-VJOY-COUNTDOWN: the box text is the model's (the real rule)."""
    from gremlin import drivers

    assert run["alikeOpen"] is True
    assert run["alikeTitle"] == "Devices that can't be told apart"
    assert run["alikeBody"] == (
        drivers.alike_warning([[1, 2]]) + " Continue anyway?"
    )
    assert (run["alikeOk"], run["alikeCancel"]) == ("Yes", "No")
    assert run["alikeApplyBefore"] is False


def test_alike_no_keeps_the_editor_and_runs_nothing(run: dict) -> None:
    assert run["alikeNoClosed"] is True
    assert run["alikeNoApply"] is False
    assert run["alikeNoEditor"] is True
    assert run["alikeNoDevices"] == 2


def test_alike_yes_applies(run: dict) -> None:
    assert run["alikeYesApply"] == 1


def test_list_grows_then_scrolls_inside_itself(run: dict) -> None:
    assert run["rowsScroll"] is True
    assert run["applyInView"] is True
    assert run["showing16"].startswith("Showing 1-")
    assert run["showing16"].endswith(" of 16 devices")
    assert run["showingEnd"].endswith("-16 of 16 devices")
    assert run["showingEnd"] != run["showing16"]
    assert run["showing2"] == "Showing all 2 devices"
    assert run["listFits2"] is True


def test_add_device_row_ends_the_list_and_scrolls_with_it(run: dict) -> None:
    """S185: the last row inside the list; clicking adds the lowest free id
    with its countdown buttons; gone at 16 devices."""
    assert run["addRowVisible4"] is True
    assert run["addRowBelowLast"] is True
    assert run["addRowInColumn"] is True
    assert run["addPreview4"] == "vJoy 5 · 124 buttons"
    assert run["addRowCursor"] is True
    assert run["addRowHidden16"] is True
    assert run["addPreview16"] == ""
    assert run["addPreview15"] == "vJoy 16 · 113 buttons"
    assert run["addRowScrolledIn"] is True
    assert run["addCalls"] == ["add"]
    assert run["addIdsAfter"][-1] == 16
    assert run["addNewButtons"] == 113


def test_remove_button_and_lowering_devices(run: dict) -> None:
    assert run["removeCalls"] == ["remove 1"]
    assert run["idsAfterRemove"] == [1, 3, 4]
    assert run["idsAfterLower"] == [1, 3]


def test_last_ticked_axis_cannot_be_unticked(run: dict) -> None:
    assert run["lastAxisEnabled"] is False
    assert run["otherAxisEnabled"] is True
    assert run["lastAxisStill"] is True


def test_device_in_use_by_another_program(run: dict) -> None:
    """D-01-VJOY-IN-USE: the row says so; Apply asks Yes/No before the alike
    box; No runs nothing. The text is the model's."""
    from gremlin import drivers

    # User 2026-11-22 (1a, 2a): no words on the row; the name is red (the
    # Style's danger colour) and bold, the words only in its hover tip.
    assert run["inUseRow"] == [False, True]
    assert run["oldInUseLabel"] is False
    assert run["inUseText"] == "vJoy 2"
    assert run["styleDanger"] and run["styleDanger"] != run["styleFg"]
    assert run["inUseColor"] == [run["styleFg"], run["styleDanger"]]
    assert run["inUseBold"] == [False, True]
    assert run["inUseTip"] == ["", "in use by another program"]
    assert run["inUseTitle"] == "Devices in use"
    assert run["inUseBody"] == drivers.in_use_warning([2])
    assert run["inUseButtons"] == ["Yes", "No"]
    assert "apply" not in run["inUseNoCalls"]
    yes = run["inUseYesCalls"]
    assert yes.index("inUseWarning") < yes.index("alikeWarning") < yes.index("apply")


def test_own_run_is_stopped_first_and_not_called_in_use(run: dict) -> None:
    """User 2026-11-22 ("a"): our own Run's devices aren't "in use by
    another program"; Apply asks to stop Run first, Yes stops it and the
    busy ids are read again before the in-use box; No returns."""
    assert run["runHidesInUse"] is False
    assert run["runTitle"] == "Run is on"
    assert run["runBody"] == "Run stops while the vJoy devices change. Continue?"
    assert run["runButtons"] == ["Yes", "No"]
    assert not any(c.startswith("toggle") for c in run["runNoCalls"])
    assert "inUseWarning" not in run["runNoCalls"]
    yes = run["runYesCalls"]
    assert "toggle False" in yes
    assert "apply" not in yes
    assert run["runYesBackend"] is False
    # After Stop the busy ids are read again: vJoy 2 is someone else's.
    assert yes.index("toggle False") < yes.index("inUseWarning")
    assert run["runYesNext"] == "Devices in use"


def test_info_box_before_a_vjoy_update(run: dict) -> None:
    """06 S185: after the what-will-happen prompt, OK only, the model's
    text; OK goes on to the in-use box; no text, no box."""
    from gremlin import drivers

    v2 = drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)
    v4 = drivers.VJoyDevice(4, drivers.VJOY_AXES, 32, 0)
    assert run["infoOpen"] is True
    assert run["infoTitle"] == "vJoy update and your devices"
    assert run["infoBody"] == drivers.update_info_text([v2, v4])
    assert run["infoOk"] == "OK"
    assert run["infoCancelVisible"] is False
    assert "inUseWarning" not in run["infoCallsBefore"]
    assert "apply" not in run["infoCallsAfter"]
    after = run["infoCallsAfter"]
    assert after.index("updateInfo") < after.index("inUseWarning")
    assert run["infoNext"] == "Devices in use"
    assert run["noInfoNext"] == "Devices in use"


def test_lost_box_after_the_results(run: dict) -> None:
    """Repair Now runs the repair; Repair Later only closes it; nothing lost,
    no box."""
    from gremlin import drivers

    v4 = drivers.VJoyDevice(4, drivers.VJOY_AXES, 32, 0)
    assert run["lostOpen"] is True
    assert run["lostTitle"] == "The vJoy update lost a device"
    assert run["lostBody"] == drivers.lost_text([v4])
    assert run["lostButtons"] == ["Repair Now", "Repair Later"]
    assert run["lostNowCalls"] == ["repairNow"]
    assert run["lostLaterCalls"] == ["repairLater"]
    assert run["nothingLostOpen"] is False
    assert run["nothingLostCalls"] == []


def test_lost_rows_with_repair(run: dict) -> None:
    assert run["lostRowBefore"] is False
    assert run["lostRowName"] == "vJoy 4"
    assert run["lostRowSummary"] == "8 axes (X-S2), 32 buttons, 0 hats"
    assert run["lostRowMark"] == "lost in the vJoy update"
    assert run["lostRowMarkColor"] == run["styleWarn"]
    assert run["lostRowRepair"] == "Repair"
    assert run["lostRowCalls"] == ["repairDevice 4"]
    assert run["lostRowGone"] is True


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
