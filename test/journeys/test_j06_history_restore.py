# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 6: History keeps a setting, a module file and an input; Restore.

The user changes three things, each saved as the program saves it:
- an input: stick button 1 sent vJoy button 1; in the Configuration pane
  it now sends vJoy button 7 (OK), and the profile is saved;
- a module file: Module Setup checks button 2 on the pJoy Pro and saves;
- a setting: Options > History > Days to keep changes goes from 90 to 30.

Tools > History lists the three changes. For each one the user picks it,
presses Restore Before and confirms: the input goes back into the open
profile as an unsaved change (vJoy button 1 again), the module file is put
back at once (button 1 only), and the setting goes back to 90.

Spec: 08 S2, S8, S11, S15, S28, S30, S38, S40, S43, S44. No known gap on
this path (Q1: a restored input becomes a History entry when the profile
is next saved, so the count is not checked here). The setting is changed
after the first settings write; a second run changes it right away on a
first run (08 S16), known gap GL-311, marked xfail.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    return [
        {name: model.data(model.index(row, 0), role) for role, name in names.items()}
        for row in range(model.rowCount())
    ]


def story(j: Journey) -> None:
    import json

    from gremlin import deferred_write, history, util
    from gremlin.config import Configuration
    from gremlin.types import InputType
    from gremlin.ui.history_model import HistoryModel
    from gremlin.ui.module_model import DriverInputModel

    out = j.out
    stick = j.stick()
    uid = stick.device_guid.uuid
    module_path = util.modules_dir() / "pjoy_pro.json"

    def vjoy_target() -> int:
        item = j.profile.get_input_item(
            uid, InputType.JoystickButton, 1, "Default", False
        )
        return item.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id

    def entries(area: str) -> list[dict]:
        return history.entries(area)

    # The profile, saved once: button 1 -> vJoy button 1.
    j.map_button(uid, 1, "Default", 1)
    _path, url = j.save_and_reopen("journey6")

    # 1. An input, edited in the pane (OK) and saved.
    catalog = j.open_configuration("pjoy_pro")
    catalog.beginPane(j.device_index(catalog, "button", 1), -1)
    j.pane_actions(catalog)[1].vjoyInputId = 7
    catalog.commitPane()
    catalog.endPane()
    assert j.backend.saveProfile(url)
    out["input-now"] = vjoy_target()
    j.wait_until(
        lambda: any(e.get("kind") == "input" for e in entries("profile")),
        "the input's History entry",
    )

    # 2. The module file, through Module Setup.
    j.ev('openConfigureModule("source", _moduleModel.cardMap("pjoy_pro"))')
    setup = j.window("Input Module Setup")
    driver = j.wait_until(lambda: setup.findChild(DriverInputModel), "Module Setup")
    j.wait_until(lambda: driver.rowCount() > 0, "the pJoy's controls")
    for index, row in enumerate(_rows(driver)):
        if (row["kind"], int(row["hwId"])) == ("button", 2):
            driver.setClaimed(index, True)
    out["setup-saved"] = j.ev("commitModule()", setup)
    j.ev("close()", setup)
    out["module-now"] = json.loads(module_path.read_text(encoding="utf-8"))["claim"][
        "buttons"
    ]
    j.wait_until(lambda: entries("modules"), "the module file's History entry")

    # 3. A setting (Options writes it, saved about a second later). The
    # settings writes the steps above set off are done first, as they are
    # for a user who takes more than a second: on a first run the file
    # didn't exist, and a setting seen for the first time isn't a change.
    j.wait_until(
        lambda: not deferred_write.pending("configuration"), "the settings file"
    )
    Configuration().set("global", "history", "keep-days", 30)
    j.wait_until(
        lambda: any(
            "global/history/keep-days" in (e.get("subject") or {}).get("keys", [])
            for e in entries("settings")
        ),
        "the setting's History entry",
        20,
    )

    # Tools > History, on every change.
    j.ev('Helpers.createComponent("DialogHistory.qml")')
    window = j.window("History")
    model = j.wait_until(lambda: window.findChild(HistoryModel), "the History list")
    j.ev("_model.reload()", window)
    shown = _rows(model)
    out["titles"] = [row["title"] for row in shown]

    def restore_before(title_start: str) -> str:
        row = next(r for r in _rows(model) if r["title"].startswith(title_start))
        j.ev(f'pick("{row["entryId"]}")', window)
        j.ev('restore("before")', window)
        out.setdefault("asks", []).append(j.ev("_gate.titleText", window))
        j.ev("_gate.confirmed()", window)
        return j.wait_until(
            lambda: j.ev("message", window), f"Restore of {title_start}"
        )

    out["input-message"] = restore_before("Changed the actions of")
    out["input-after"] = vjoy_target()
    out["input-unsaved"] = j.backend.profile.has_unsaved_changes()

    out["module-message"] = restore_before("Saved pJoy Pro")
    out["module-after"] = json.loads(module_path.read_text(encoding="utf-8"))["claim"][
        "buttons"
    ]

    out["setting-message"] = restore_before("Changed Days to keep changes")
    out["setting-after"] = Configuration().value("global", "history", "keep-days")


def setting_right_away(j: Journey) -> None:
    """First run: a setting changed as soon as the program is up, while
    the first settings write is still to come (GL-311)."""
    from gremlin import deferred_write, history
    from gremlin.config import Configuration

    def keep_days_entries() -> int:
        return sum(
            "global/history/keep-days" in (e.get("subject") or {}).get("keys", [])
            for e in history.entries("settings")
        )

    j.out["before"] = Configuration().value("global", "history", "keep-days")
    Configuration().set("global", "history", "keep-days", 30)
    j.wait_until(
        lambda: not deferred_write.pending("configuration"), "the settings file"
    )
    j.out["entries"] = j.await_value(keep_days_entries, 1, 5.0)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1])
        j.vjoy_module()

    phase = sys.argv[1] if len(sys.argv) > 1 else "story"
    Journey(before).run(setting_right_away if phase == "right-away" else story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j06"))


@pytest.fixture(scope="module")
def right_away(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j06b"), "right-away")


def test_the_three_changes_are_made(run: dict) -> None:
    assert step(run, "input-now") == 7
    assert step(run, "setup-saved") is True
    assert step(run, "module-now") == [1, 2]


def test_history_lists_each_change(run: dict) -> None:
    titles = step(run, "titles")
    assert any(
        t.startswith("Changed the actions of pJoy Pro") and t.endswith("in Default")
        for t in titles
    ), titles
    assert any(t.startswith("Saved pJoy Pro") for t in titles), titles
    assert "Changed Days to keep changes" in titles


def test_restore_asks_first(run: dict) -> None:
    assert step(run, "asks") == ["Restore?", "Restore?", "Restore?"]


def test_the_input_goes_back_into_the_open_profile_unsaved(run: dict) -> None:
    assert step(run, "input-message")
    assert step(run, "input-after") == 1
    assert step(run, "input-unsaved") is True


def test_the_module_file_goes_back(run: dict) -> None:
    assert step(run, "module-message")
    assert step(run, "module-after") == [1]


def test_the_setting_goes_back(run: dict) -> None:
    assert step(run, "setting-message")
    assert step(run, "setting-after") == 90


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-311: a setting changed right away on a first run leaves no entry",
)
def test_a_setting_changed_right_away_on_a_first_run_is_one_entry(
    right_away: dict,
) -> None:
    # 08 S16: a first appearance isn't a change, but a change of a setting
    # the program already had is (one entry).
    assert step(right_away, "before") == 90
    assert step(right_away, "entries") == 1


if __name__ == "__main__":
    main()
