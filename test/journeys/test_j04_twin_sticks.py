# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 4: twin sticks each use their own module file.

Two identical "pJoy Pro" sticks are plugged in. The first already has its
module file (buttons 1, 3 and 5, axis 1); the second shows as "pJoy Pro
(2)" with a card of its own. The user opens Module Setup on the second
card, checks button 2 and axis 1, and saves: the second twin gets its own
file, the first twin's file is untouched, and each card counts its own
controls. In Calibration the user picks the second twin's file, moves the
low end of axis 1 and saves all: only that file gets the curve, and the
program reads it for the second twin only. Then Run: each twin's buttons
go through its own input module (twin 1 button 1 and twin 2 button 2
reach vJoy; twin 1 button 2 and twin 2 button 1 are not checked and send
nothing).

Spec: 03 S6, S9, S77 and decision F4 (twins are looked up by id); map 1
(module file ownership: one rule for every reader); 02 S16 (the "(2)"
name); 06 S33. GL-076 (suspected: a twin's card counts the other twin's
controls after a save) does not show on this path; the counts are right
today and test_each_card_counts_its_own_twins_controls keeps them so.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

_LOW = -20000


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    return [
        {name: model.data(model.index(row, 0), role) for role, name in names.items()}
        for row in range(model.rowCount())
    ]


def story(j: Journey) -> None:
    import json

    from gremlin import device_initialization, util
    from gremlin.modules import calibration
    from gremlin.ui.device import AxisCalibration
    from gremlin.ui.module_model import DriverInputModel

    out = j.out
    modules = util.modules_dir()
    first = j.stick("pJoy Pro")
    second = j.stick("pJoy Pro (2)")
    out["names"] = sorted(d.name for d in device_initialization.physical_devices())
    first_file = modules / "pjoy_pro.json"
    first_text = first_file.read_text(encoding="utf-8")
    out["cards"] = [
        j.ev('_moduleModel.cardMap("pjoy_pro").name'),
        j.ev('_moduleModel.cardMap("pjoy_pro_2").name'),
    ]

    # Module Setup on the second twin's card: check button 2 and axis 1, Save.
    j.ev('openConfigureModule("source", _moduleModel.cardMap("pjoy_pro_2"))')
    setup = j.window("Input Module Setup")
    driver = j.wait_until(
        lambda: setup.findChild(DriverInputModel), "the Module Setup controls"
    )
    j.wait_until(lambda: driver.rowCount() > 0, "the controls of pJoy Pro (2)")
    out["setup-device"] = j.ev("deviceName", setup)
    for index, row in enumerate(_rows(driver)):
        if (row["kind"], int(row["hwId"])) in (("button", 2), ("axis", 1)):
            driver.setClaimed(index, True)
    out["setup-saved"] = j.ev("commitModule()", setup)
    second_file = modules / "pjoy_pro_2.json"
    out["second-file"] = second_file.is_file()
    second_doc = json.loads(second_file.read_text(encoding="utf-8"))
    out["second-claim"] = [second_doc["claim"]["buttons"], second_doc["claim"]["axes"]]
    out["second-bound"] = (
        str(second_doc.get("boundGuidLocal", "")).upper().strip("{}").replace("-", "")
    )
    out["second-guid"] = str(second.device_guid).upper().strip("{}").replace("-", "")
    out["first-untouched"] = first_file.read_text(encoding="utf-8") == first_text
    j.ev("_moduleModel.notifyClaims()")
    out["card-buttons"] = [
        j.ev('_moduleModel.cardMap("pjoy_pro").buttons'),
        j.ev('_moduleModel.cardMap("pjoy_pro_2").buttons'),
    ]
    j.ev("close()", setup)

    # Calibration on the second twin's file: move the low end, Save All.
    j.ev(
        'Helpers.createComponent("DialogCalibration.qml",'
        ' {"initialSlug": "pjoy_pro_2"})'
    )
    cal = j.window("Calibration")
    axes = j.wait_until(lambda: cal.findChild(AxisCalibration), "the calibration list")
    j.wait_until(lambda: axes.rowCount() > 0, "the axes of pJoy Pro (2)")
    out["cal-slug"] = j.ev("shownSlug", cal)
    low_role = next(int(k) for k, v in axes.roleNames().items() if bytes(v) == b"low")
    axes.setData(axes.index(0, 0), _LOW, low_role)
    out["cal-saved"] = axes.saveAll()
    second_doc = json.loads(second_file.read_text(encoding="utf-8"))
    out["second-has-curve"] = "1" in (second_doc.get("calibration") or {})
    out["first-untouched-after-cal"] = (
        first_file.read_text(encoding="utf-8") == first_text
    )
    out["curves"] = [
        calibration.values_for_device(first.device_guid.uuid, 1)[0],
        calibration.values_for_device(second.device_guid.uuid, 1)[0],
    ]

    # Run: each twin through its own input module.
    j.map_button(first.device_guid.uuid, 1, "Default", 1)
    j.map_button(first.device_guid.uuid, 2, "Default", 4)
    j.map_button(second.device_guid.uuid, 1, "Default", 3)
    j.map_button(second.device_guid.uuid, 2, "Default", 2)
    j.save_and_reopen("journey4")
    j.backend.toggleActiveState()
    out["running"] = j.backend.runner.is_running()
    for stick, button in ((first, 1), (first, 2), (second, 1), (second, 2)):
        j.press(stick, button, True)
    out["held"] = j.await_value(j.vjoy.held_buttons, [1, 2])
    j.backend.toggleActiveState()


def main() -> None:
    def before(j: Journey) -> None:
        j.add_stick("pJoy Pro", 2)
        j.input_module("pJoy Pro", buttons=[1, 3, 5])
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j04"))


def test_each_twin_has_its_own_name_and_card(run: dict) -> None:
    assert step(run, "names") == ["pJoy Pro", "pJoy Pro (2)"]
    assert step(run, "cards") == ["pJoy Pro", "pJoy Pro (2)"]


def test_module_setup_saves_the_second_twins_own_file(run: dict) -> None:
    assert step(run, "setup-device") == "pJoy Pro (2)"
    assert step(run, "setup-saved") is True
    assert step(run, "second-file") is True
    assert step(run, "second-claim") == [[2], [1]]
    assert step(run, "second-bound") == step(run, "second-guid")
    assert step(run, "first-untouched") is True


def test_each_card_counts_its_own_twins_controls(run: dict) -> None:
    assert step(run, "card-buttons") == [3, 1]


def test_calibration_writes_only_the_second_twins_file(run: dict) -> None:
    assert step(run, "cal-slug") == "pjoy_pro_2"
    assert step(run, "cal-saved") is True
    assert step(run, "second-has-curve") is True
    assert step(run, "first-untouched-after-cal") is True
    first_low, second_low = step(run, "curves")
    assert second_low == _LOW
    assert first_low != _LOW


def test_run_passes_each_twins_own_checked_buttons(run: dict) -> None:
    assert step(run, "running") is True
    assert step(run, "held") == [1, 2]


if __name__ == "__main__":
    main()
