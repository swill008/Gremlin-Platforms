# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The program really uses scripts: every example script in
test/fixtures/scripts (its manifest scripts.json) is added through the
Scripts window (04 S96) the way Add Script adds it (S84), shows its row or
why it can't load (S29), is configured through the window's variables pane
(S85), is saved with the profile and comes back on reload (S86), and runs:
a stick button and axis reach the stand-in vJoy through the output module
(S87, S89), a script changes the mode, a periodic callback ticks only while
running (S90), and a script with a required variable unset is skipped (S87).

The real program off-screen in its own process (the journey harness):
temporary USERPROFILE, stand-in sticks and vJoy, no real keys.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import time
from typing import Any

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
    step,
)

FIXTURES = _ROOT / "test" / "fixtures" / "scripts"
MANIFEST = json.loads((FIXTURES / "scripts.json").read_text(encoding="utf-8"))
ENTRIES = MANIFEST["scripts"]

# Stick inputs each script is set to (none share a button, so one script's
# press can't be taken for another's; mode_switch's is pressed last).
BUTTON_TO_VJOY_STICK = 3
TWO_A_STICK, TWO_A_VJOY = 1, 3
TWO_B_STICK, TWO_B_VJOY = 2, 5
MODE_SWITCH_STICK = 4
AXIS_STICK, AXIS_SCALE = 1, 0.25
RAW_AXIS = 26214  # about 0.8 of full scale


# +-------------------------------------------------------------------------
# | Child process


def story(j: Journey) -> None:  # noqa: PLR0915
    from PySide6 import QtCore

    from gremlin import mode_manager, util
    from gremlin.types import Event, InputType

    out = j.out
    folder = pathlib.Path(util.scripts_dir())
    folder.mkdir(parents=True, exist_ok=True)
    for entry in ENTRIES:
        shutil.copy(FIXTURES / entry["file"], folder / entry["file"])
    # A second mode for mode_switch's "Switch to".
    j.profile.modes.add_mode("Second")

    # 04 S96: Tools › Scripts… opens the Scripts window.
    j.ev('Commands.trigger("tools.scripts")')
    window = j.window("Scripts")
    out["window-object"] = window.objectName()
    manager = j.wait_until(lambda: j.item(window, "scriptManager"), "scriptManager")
    model = j.ev("scriptListModel", manager)

    # S84: every manifest script through the window's own model (Add Script's
    # path), two_instances twice.
    for entry in ENTRIES:
        url = QtCore.QUrl.fromLocalFile(str(folder / entry["file"])).toString()
        model.addScript(url)
        if entry["file"] == "two_instances.py":
            model.addScript(url)
    j.wait_until(
        lambda: (
            len(j.profile.scripts.scripts) == len(ENTRIES) + 1
            and not any(s.starting for s in j.profile.scripts.scripts)
        ),
        "every script started",
        30,
    )

    def rows() -> list:
        return [
            it
            for it in j.walk(window.contentItem())
            if it.objectName().startswith("scriptRow:")
        ]

    def row(file: str, name: str = "") -> Any:  # noqa: ANN401
        for it in rows():
            if pathlib.Path(str(it.property("path"))).name == file and (
                not name or it.property("name") == name
            ):
                return it
        return None

    def child(item: Any, name: str) -> Any:  # noqa: ANN401
        return next((it for it in j.walk(item) if it.objectName() == name), None)

    def shown_row(file: str, name: str = "") -> dict:
        it = row(file, name)
        if it is None:
            return {}
        error = child(it, "scriptLoadError")
        return {
            "name": it.property("name"),
            "shown-name": child(it, "scriptName").property("text"),
            "error": str(error.property("text")) if error.isVisible() else "",
            "starting": bool(child(it, "scriptStarting").isVisible()),
            "configure": bool(child(it, "scriptConfigure").property("enabled")),
        }

    j.wait_until(lambda: len(rows()) == len(ENTRIES) + 1, "every row shown", 15)
    j.settle()
    out["empty-shown"] = bool(j.item(window, "scriptsEmpty").isVisible())
    out["rows"] = {entry["file"]: shown_row(entry["file"]) for entry in ENTRIES}
    out["two-names"] = sorted(
        str(it.property("name"))
        for it in rows()
        if pathlib.Path(str(it.property("path"))).name == "two_instances.py"
    )
    out["configured-when-added"] = {
        s.path.name + ":" + s.name: s.is_configured for s in j.profile.scripts.scripts
    }

    # S85: configure through the variables pane, as a click on the row's
    # configure button does.
    config = j.item(window, "scriptVariables")

    def configure(file: str, name: str = "") -> dict:
        it = row(file, name)
        assert it is not None, f"no row for {file} {name}"
        j.click(child(it, "scriptConfigure"))
        j.settle()
        found = {}
        for m in j.ev("model", config) or []:
            found[m.property("name")] = m
        return found

    stick = j.stick()
    guid = stick.device_guid.uuid

    def pick(variable: Any, kind: InputType, index: int) -> None:  # noqa: ANN401
        """The input listener's answer: this stick input."""
        variable.updateJoystick(
            [Event(kind, index, guid, "Default", is_pressed=True)]
        )

    # vars_all_types: all eleven shown.
    variables = configure("vars_all_types.py")
    out["vars-all-names"] = sorted(variables)
    out["vars-all-shown"] = sorted(
        str(it.property("text"))
        for it in j.walk(config)
        if it.objectName() == "scriptVariableName" and it.isVisible()
    )
    out["vars-all-heading"] = [
        str(it.property("text"))
        for it in j.walk(window.contentItem())
        if str(it.property("text") or "").startswith("Variables of ")
    ]

    variables = configure("button_to_vjoy.py")
    out["button-invalid-before"] = sum(
        1
        for it in j.walk(config)
        if it.objectName() == "scriptVariableInvalid" and it.isVisible()
    )
    pick(variables["Button"], InputType.JoystickButton, BUTTON_TO_VJOY_STICK)
    j.settle()
    out["button-invalid-after"] = sum(
        1
        for it in j.walk(config)
        if it.objectName() == "scriptVariableInvalid" and it.isVisible()
    )

    variables = configure("axis_to_vjoy.py")
    pick(variables["Stick axis"], InputType.JoystickAxis, AXIS_STICK)
    variables["Scale"].setProperty("value", AXIS_SCALE)

    variables = configure("mode_switch.py")
    pick(variables["Button"], InputType.JoystickButton, MODE_SWITCH_STICK)
    variables["Switch to"].setProperty("value", "Second")

    variables = configure("two_instances.py", "Instance 1")
    pick(variables["Button"], InputType.JoystickButton, TWO_A_STICK)
    variables["vJoy button"].setProperty("value", TWO_A_VJOY)
    variables = configure("two_instances.py", "Instance 2")
    pick(variables["Button"], InputType.JoystickButton, TWO_B_STICK)
    variables["vJoy button"].setProperty("value", TWO_B_VJOY)

    def values() -> dict:
        """Every script's variable values, by file:name."""
        found = {}
        for s in j.profile.scripts.scripts:
            shown = {}
            for name, var in s.variables.items():
                # A logical input by its permanent id, not the row object.
                value = var.uid if hasattr(var, "uid") else var.value
                if isinstance(value, tuple):
                    value = [str(v) for v in value]
                elif value is not None and not isinstance(value, (bool, int, float)):
                    value = str(value)
                shown[name] = value
            found[s.path.name + ":" + s.name] = {
                "values": shown,
                "configured": s.is_configured,
                "error": s.load_error,
            }
        return found

    out["values-before-save"] = values()

    # S86: Save Profile, open another profile, then this one again.
    path, _url = j.save_and_reopen("scripts_e2e")
    saved = path.read_text(encoding="utf-8")
    # Inside the scripts folder: saved relative to it.
    out["saved-full-folder"] = str(folder) in saved
    out["saved-files"] = sorted(e["file"] for e in ENTRIES if e["file"] in saved)
    j.wait_until(
        lambda: (
            len(j.profile.scripts.scripts) == len(ENTRIES) + 1
            and not any(s.starting for s in j.profile.scripts.scripts)
        ),
        "the scripts back after reload",
        30,
    )
    out["values-after-reload"] = values()
    j.wait_until(lambda: len(rows()) == len(ENTRIES) + 1, "rows after reload", 15)
    j.settle()
    out["rows-after-reload"] = {
        entry["file"]: shown_row(entry["file"]) for entry in ENTRIES
    }

    def script(file: str, name: str = "") -> Any:  # noqa: ANN401
        return next(
            s
            for s in j.profile.scripts.scripts
            if s.path.name == file and (not name or s.name == name)
        )

    # Before Run: no periodic ticks.
    out["ticks-before-run"] = len(script("periodic_counter.py").module.ticks)

    # Run (S87: each script loaded fresh).
    out["mode-before"] = mode_manager.ModeManager().current.name
    j.backend.toggleActiveState()
    out["running"] = j.await_run(True)
    counter = script("periodic_counter.py").module.ticks
    unset = script("required_var_unset.py").module.ticks

    def held() -> list[int]:
        return j.vjoy.held_buttons()

    # button_to_vjoy: stick button 3 -> vJoy 1 button 1.
    j.press(stick, BUTTON_TO_VJOY_STICK, True)
    out["button-down"] = j.await_value(held, [1])
    j.press(stick, BUTTON_TO_VJOY_STICK, False)
    out["button-up"] = j.await_value(held, [])

    # two_instances: each instance its own button.
    j.press(stick, TWO_A_STICK, True)
    out["two-a-down"] = j.await_value(held, [TWO_A_VJOY])
    j.press(stick, TWO_A_STICK, False)
    j.await_value(held, [])
    j.press(stick, TWO_B_STICK, True)
    out["two-b-down"] = j.await_value(held, [TWO_B_VJOY])
    j.press(stick, TWO_B_STICK, False)
    out["two-b-up"] = j.await_value(held, [])

    # axis_to_vjoy: stick axis 1 -> vJoy 1 axis 1, times Scale.
    import dill

    callback = j.dill_fake.input_event_callback
    callback(
        dill._JoystickInputData(
            device_guid=stick.device_guid.ctypes,
            input_type=1,
            input_index=AXIS_STICK,
            value=RAW_AXIS,
        )
    )

    def axis() -> Any:  # noqa: ANN401
        device = j.vjoy.vjoy_devices.get(1)
        return device.state.get(("axis", 1)) if device else None

    # Run writes the initial value (0.0) first; wait for the script's.
    out["axis"] = j.await_value(
        lambda: round(axis() or 0.0, 2), round(0.8 * AXIS_SCALE, 2)
    )
    out["axis-writes"] = [w for w in j.vjoy.all_writes() if w[0] == "axis"]

    # periodic_counter ticks; required_var_unset is skipped.
    j.wait_until(lambda: len(counter) >= 5, "periodic ticks", 10)
    out["ticks-while-running"] = len(counter)
    out["unset-ticks"] = len(unset)

    # mode_switch: stick button 4 -> mode "Second" (pressed last).
    j.press(stick, MODE_SWITCH_STICK, True)
    out["mode-after-press"] = j.await_value(
        lambda: mode_manager.ModeManager().current.name, "Second"
    )
    j.press(stick, MODE_SWITCH_STICK, False)
    j.settle()
    out["mode-after-release"] = mode_manager.ModeManager().current.name

    # Stop: no more ticks.
    j.backend.toggleActiveState()
    out["running-after-stop"] = j.await_run(False)
    at_stop = len(counter)
    started = time.monotonic()
    while time.monotonic() - started < 0.4:
        j.QTest.qWait(50)
    out["ticks-after-stop"] = len(counter) - at_stop


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | The tests


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("scripts_e2e"))


def _entries(loads: bool) -> list[dict]:
    return [e for e in ENTRIES if e["loads"] is loads]


def test_every_script_is_added_and_shows_its_row(run: dict) -> None:
    assert step(run, "window-object") == "scriptsWindow"
    rows = step(run, "rows")
    assert step(run, "empty-shown") is False
    for entry in ENTRIES:
        assert rows[entry["file"]], f"{entry['file']}: no row in the Scripts window"
        assert rows[entry["file"]]["starting"] is False, entry["file"]
    # S84: one file twice, Instance 1 and Instance 2.
    assert step(run, "two-names") == ["Instance 1", "Instance 2"]


def test_scripts_that_cant_load_say_why_and_cant_be_configured(run: dict) -> None:
    rows = step(run, "rows")
    for entry in _entries(False):
        shown = rows[entry["file"]]
        assert shown["error"].startswith("Can't load: "), (entry["file"], shown)
        assert entry["expected_error_contains"] in shown["error"], (
            entry["file"],
            shown,
        )
        assert shown["configure"] is False, (entry["file"], "configure is on")
    for entry in _entries(True):
        shown = rows[entry["file"]]
        assert shown["error"] == "", (entry["file"], shown)
        assert shown["configure"] is True, (entry["file"], "configure is off")


def test_configured_when_added_matches_the_manifest(run: dict) -> None:
    configured = step(run, "configured-when-added")
    for entry in _entries(True):
        keys = [k for k in configured if k.startswith(entry["file"] + ":")]
        assert keys, entry["file"]
        for key in keys:
            assert configured[key] is entry["configured_when_added"], key


def test_the_variables_pane_shows_and_sets_the_variables(run: dict) -> None:
    expected = sorted(ENTRIES[0]["variables"])
    assert ENTRIES[0]["file"] == "vars_all_types.py"
    assert step(run, "vars-all-names") == expected
    assert len(step(run, "vars-all-shown")) == len(expected)
    assert step(run, "vars-all-heading") == ["Variables of Instance 1"]
    # button_to_vjoy: the required Button is marked until set.
    assert step(run, "button-invalid-before") == 1
    assert step(run, "button-invalid-after") == 0
    values = step(run, "values-before-save")
    assert values["axis_to_vjoy.py:Instance 1"]["values"]["Scale"] == AXIS_SCALE
    assert values["mode_switch.py:Instance 1"]["values"]["Switch to"] == "Second"
    assert values["two_instances.py:Instance 1"]["values"]["vJoy button"] == TWO_A_VJOY
    assert values["two_instances.py:Instance 2"]["values"]["vJoy button"] == TWO_B_VJOY
    for key in (
        "button_to_vjoy.py:Instance 1",
        "axis_to_vjoy.py:Instance 1",
        "mode_switch.py:Instance 1",
        "two_instances.py:Instance 1",
        "two_instances.py:Instance 2",
    ):
        assert values[key]["configured"] is True, key


def test_s86_scripts_and_values_come_back_after_save_and_reload(run: dict) -> None:
    assert step(run, "saved-files") == sorted(e["file"] for e in ENTRIES)
    assert step(run, "saved-full-folder") is False, "saved with the full path"
    before = step(run, "values-before-save")
    after = step(run, "values-after-reload")
    assert sorted(after) == sorted(before)
    for key, was in before.items():
        assert after[key]["values"] == was["values"], key
        assert after[key]["configured"] == was["configured"], key
        assert bool(after[key]["error"]) == bool(was["error"]), key
    # The window follows the reloaded profile: every row again, same errors.
    rows = step(run, "rows-after-reload")
    for entry in ENTRIES:
        assert rows[entry["file"]], f"{entry['file']}: no row after reload"
        assert (
            rows[entry["file"]]["error"] == step(run, "rows")[entry["file"]]["error"]
        ), entry["file"]


def test_running_scripts_drive_vjoy_and_the_mode(run: dict) -> None:
    assert step(run, "running") is True
    assert step(run, "mode-before") == "Default"
    # button_to_vjoy
    assert step(run, "button-down") == [1], "button_to_vjoy: vJoy button 1 not down"
    assert step(run, "button-up") == [], "button_to_vjoy: vJoy button 1 not up"
    # two_instances
    assert step(run, "two-a-down") == [TWO_A_VJOY], "two_instances Instance 1"
    assert step(run, "two-b-down") == [TWO_B_VJOY], "two_instances Instance 2"
    assert step(run, "two-b-up") == []
    # axis_to_vjoy: about 0.8 times 0.25.
    assert step(run, "axis") == pytest.approx(0.8 * AXIS_SCALE, abs=0.01), (
        "axis_to_vjoy: vJoy 1 axis 1"
    )
    # mode_switch
    assert step(run, "mode-after-press") == "Second", "mode_switch: mode"
    assert step(run, "mode-after-release") == "Second"


def test_periodic_ticks_only_while_running_and_unset_scripts_are_skipped(
    run: dict,
) -> None:
    assert step(run, "ticks-before-run") == 0, "periodic_counter ticked before Run"
    assert step(run, "ticks-while-running") >= 5, "periodic_counter"
    assert step(run, "unset-ticks") == 0, "required_var_unset ran unset"
    assert step(run, "running-after-stop") is False
    assert step(run, "ticks-after-stop") == 0, "periodic_counter ticked after Stop"


if __name__ == "__main__":
    main()
