# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The dummy script suite (test/fixtures/scripts, listed in scripts.json).

Each script is added to a profile the way the Scripts page of Options adds it, and
checked against its manifest entry: it loads (or fails with the reason the
Scripts page of Options shows), its variables have the listed types, and whether it
counts as configured. The behaviour scripts then run in a real CodeRunner
(04 S87: only configured scripts, reloaded fresh at Run), with drivers,
devices, sound and network as stand-ins: vJoy writes are recorded at
output.write_vjoy, events go straight into the EventHandler, no key is ever
sent.

Spec: 04 S29, S84, S85, S87, S89, S90, S95; 09 S163.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from typing import Any
from unittest import mock
from xml.etree import ElementTree

sys.path.append(".")

import pytest
from PySide6 import QtCore

import dill
from gremlin import code_runner, keyboard, mode_manager, run_scope, shared_state
from gremlin import user_script as us
from gremlin.event_handler import EventHandler
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.profile import Profile
from gremlin.types import Event, InputType

SUITE = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "scripts"
MANIFEST = json.loads((SUITE / "scripts.json").read_text(encoding="utf-8"))
ENTRIES = {entry["file"]: entry for entry in MANIFEST["scripts"]}
MODE = "Default"
_GUID = uuid.UUID("5c1e5c1e-0000-4000-8000-000000000001")  # a stand-in stick
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def profile() -> Iterator[Profile]:
    """A new open profile (scripts read its modes when they load)."""
    previous = shared_state.current_profile
    shared_state.current_profile = p = Profile()
    yield p
    for script in list(p.scripts.scripts):
        us.Script.variable_registry.remove_script(script)
    shared_state.current_profile = previous


@pytest.fixture
def vjoy_writes(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Every vJoy write a script makes, (vjoy id, kind, input id, value)."""
    from gremlin.modules import output

    writes: list[tuple] = []

    def record(vjoy_id: int, kind: str, input_id: int, value: Any) -> bool:  # noqa: ANN401
        writes.append((int(vjoy_id), kind, int(input_id), value))
        return True

    monkeypatch.setattr(output, "write_vjoy", record)
    monkeypatch.setattr(output, "release_vjoy_button", lambda *a: True)
    return writes


@pytest.fixture
def runner(
    monkeypatch: pytest.MonkeyPatch, vjoy_writes: list[tuple]
) -> Iterator[code_runner.CodeRunner]:
    """A CodeRunner whose drivers, devices, sound and network are stand-ins
    (as test_action_state's)."""
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    manager = mode_manager.ModeManager()
    stack = list(manager._mode_stack)  # noqa: SLF001 - one per process
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    shared_state.set_runtime_active(False)
    run_scope._reset_for_tests()  # noqa: SLF001
    manager._mode_stack = stack  # noqa: SLF001
    manager._current = stack[-1] if stack else manager._current  # noqa: SLF001


def _wait_for(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return check()


def _add(profile: Profile, file: str) -> us.Script:
    """Adds the file as the Scripts page of Options does; the instance just added."""
    before = set(map(id, profile.scripts.scripts))
    profile.scripts.add_script(SUITE / file)
    return next(s for s in profile.scripts.scripts if id(s) not in before)


def _button(script: us.Script, name: str, number: int) -> None:
    script.get_variable(name).value = (_GUID, InputType.JoystickButton, number)


def _press(number: int, pressed: bool, device: uuid.UUID = _GUID) -> None:
    EventHandler().process_event(
        Event(InputType.JoystickButton, number, device, MODE, is_pressed=pressed)
    )


# --- the manifest -------------------------------------------------------------


def test_every_script_is_in_the_manifest_and_back() -> None:
    files = {p.name for p in SUITE.glob("*.py")}
    assert files == set(ENTRIES), "scripts.json and the .py files differ"
    assert len(ENTRIES) == len(MANIFEST["scripts"]), "a file is listed twice"
    for entry in MANIFEST["scripts"]:
        assert entry["purpose"] and entry["checks"], entry["file"]
        if entry["loads"]:
            assert "configured_when_added" in entry, entry["file"]
        else:
            assert entry["expected_error_contains"], entry["file"]


@pytest.mark.parametrize("file", sorted(ENTRIES))
def test_script_loads_as_the_manifest_says(profile: Profile, file: str) -> None:
    entry = ENTRIES[file]
    script = _add(profile, file)
    assert script.name == "Instance 1"  # S84
    assert script in profile.scripts.scripts  # kept, even when it can't load
    if entry["loads"]:
        assert script.load_error == ""
        shown = {name: type(v).__name__ for name, v in script.variables.items()}
        assert shown == entry["variables"]
        assert script.is_configured is entry["configured_when_added"]
    else:
        # S29: the reason shown on the Scripts page of Options, and no variables.
        assert entry["expected_error_contains"] in script.load_error
        assert script.variables == {}
        assert script.retry() is False  # still broken: Run skips it


def test_every_variable_type_is_in_the_suite() -> None:
    types_used = {t for e in ENTRIES.values() for t in e["variables"].values()}
    every = {
        cls.__name__
        for cls in vars(us).values()
        if isinstance(cls, type)
        and issubclass(cls, us.AbstractVariable)
        and cls is not us.AbstractVariable
    }
    assert every <= types_used, f"no script uses {sorted(every - types_used)}"


# --- variables: defaults and limits -------------------------------------------


def test_vars_all_types_defaults_and_limits(profile: Profile) -> None:
    script = _add(profile, "vars_all_types.py")
    v = script.get_variable
    assert v("Flag").value is True
    gain = v("Gain")
    assert (gain.value, gain.min_value, gain.max_value) == (0.5, -2.0, 2.0)
    gain.value = 5.0
    assert gain.value == 2.0  # held at the limit
    count = v("Count")
    assert (count.value, count.min_value, count.max_value) == (3, 0, 10)
    count.value = -4
    assert count.value == 0
    assert v("Hotkey").value is None
    assert v("OSC input").uid is None
    assert v("Active mode").value == profile.modes.first_mode
    choice = v("Choice")
    assert (choice.options, choice.value) == (["Low", "Medium", "High"], "Medium")
    assert v("Label").value == "hello"
    assert not v("Stick axis").is_valid()  # none chosen
    hat = v("vJoy hat")
    assert (hat.vjoy_id, hat.input_type, hat.input_id) == (
        1,
        InputType.JoystickHat,
        1,
    )
    assert all(var.is_optional for var in script.variables.values())


def test_settings_are_saved_and_read_back(profile: Profile) -> None:
    """S86: the values go with the profile and come back on load."""
    script = _add(profile, "vars_all_types.py")
    script.get_variable("Count").value = 7
    script.get_variable("Choice").value = "High"
    script.get_variable("Label").value = "saved"
    root = ElementTree.Element("profile")  # what a saved profile holds
    root.append(profile.scripts.to_xml())

    again = Profile()
    again.scripts.from_xml(root)
    loaded = again.scripts.scripts[0]
    try:
        assert loaded.get_variable("Count").value == 7
        assert loaded.get_variable("Choice").value == "High"
        assert loaded.get_variable("Label").value == "saved"
    finally:
        us.Script.variable_registry.remove_script(loaded)


# --- behaviour in a real Run ---------------------------------------------------


def test_button_to_vjoy_presses_vjoy_button_1(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    script = _add(profile, "button_to_vjoy.py")
    _button(script, "Button", 4)
    assert script.is_configured
    runner.start(profile, MODE)
    _press(4, True)
    _press(4, False)
    _press(5, True)  # another button: not this script's
    assert script.module.presses == [True, False]
    assert vjoy_writes == [(1, "button", 1, True), (1, "button", 1, False)]


def test_axis_to_vjoy_scales_the_axis(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    script = _add(profile, "axis_to_vjoy.py")
    script.get_variable("Stick axis").value = (_GUID, InputType.JoystickAxis, 2)
    script.get_variable("Scale").value = 0.25  # the set value, not the default
    runner.start(profile, MODE)
    EventHandler().process_event(
        Event(InputType.JoystickAxis, 2, _GUID, MODE, value=0.8)
    )
    assert vjoy_writes == [(1, "axis", 1, pytest.approx(0.2))]


def test_mode_switch_changes_the_mode(
    profile: Profile, runner: code_runner.CodeRunner
) -> None:
    profile.modes.add_mode("Second")
    script = _add(profile, "mode_switch.py")
    _button(script, "Button", 1)
    script.get_variable("Switch to").value = "Second"
    assert script.is_configured
    runner.start(profile, MODE)
    manager = mode_manager.ModeManager()
    assert manager.current.name == MODE
    _press(1, True)
    assert manager.current.name == "Second"


def test_periodic_counter_ticks_only_while_running(
    profile: Profile, runner: code_runner.CodeRunner
) -> None:
    script = _add(profile, "periodic_counter.py")
    script.get_variable("Interval").value = 0.01
    time.sleep(0.1)
    assert script.module.ticks == []  # nothing before Run
    runner.start(profile, MODE)
    assert _wait_for(lambda: len(script.module.ticks) >= 5)
    runner.stop()
    stopped_at = len(script.module.ticks)
    time.sleep(0.1)
    assert len(script.module.ticks) <= stopped_at + 1  # S90: stops at Stop


def test_keyboard_reader_reacts_to_its_key_only(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    script = _add(profile, "keyboard_reader.py")
    assert not script.is_configured  # Key is required
    f13 = keyboard.key_from_name("f13")
    script.get_variable("Key").value = f13
    assert script.is_configured
    runner.start(profile, MODE)

    def key(k: keyboard.Key, pressed: bool) -> None:
        EventHandler().process_event(
            Event(
                InputType.Keyboard,
                (k.scan_code, k.is_extended),
                dill.UUID_Keyboard,
                MODE,
                is_pressed=pressed,
            )
        )

    key(f13, True)
    key(f13, False)
    key(keyboard.key_from_name("f12"), True)  # another key: nothing
    assert [pressed for pressed, _state in script.module.seen] == [True, False]
    assert all(isinstance(state, bool) for _p, state in script.module.seen)
    assert vjoy_writes == []


def test_osc_input_presses_the_vjoy_button(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    row = OscDevice().rows.create(InputType.JoystickButton, "/suite/press")
    script = _add(profile, "osc_input.py")
    assert not script.is_configured  # none chosen yet
    script.get_variable("OSC button").uid = row.uid
    assert script.is_configured
    runner.start(profile, MODE)
    _press(row.input_id, True, OSC_DEVICE_UUID)
    _press(row.input_id, False, OSC_DEVICE_UUID)
    assert script.module.presses == [True, False]
    assert vjoy_writes == [(1, "button", 1, True), (1, "button", 1, False)]


def test_two_instances_keep_their_own_settings(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    first = _add(profile, "two_instances.py")
    second = _add(profile, "two_instances.py")
    assert (first.name, second.name) == ("Instance 1", "Instance 2")  # S84
    _button(first, "Button", 1)
    first.get_variable("vJoy button").value = 3
    _button(second, "Button", 2)
    second.get_variable("vJoy button").value = 5
    runner.start(profile, MODE)
    _press(1, True)
    assert vjoy_writes == [(1, "button", 3, True)]
    vjoy_writes.clear()
    _press(2, True)
    assert vjoy_writes == [(1, "button", 5, True)]


def test_required_variable_unset_is_not_run_until_set(
    profile: Profile, runner: code_runner.CodeRunner
) -> None:
    """S87: only scripts whose required variables are set run."""
    script = _add(profile, "required_var_unset.py")
    assert script.load_error == ""
    assert not script.is_configured
    runner.start(profile, MODE)
    time.sleep(0.2)
    assert script.module.ticks == []
    runner.stop()

    script.get_variable("Callsign").value = "Alpha"
    assert script.is_configured
    runner.start(profile, MODE)
    assert _wait_for(lambda: len(script.module.ticks) >= 2)
    assert set(script.module.ticks) == {"Alpha"}


@pytest.mark.parametrize(
    "broken", sorted(f for f, e in ENTRIES.items() if not e["loads"])
)
def test_a_broken_script_does_not_stop_the_run(
    profile: Profile, runner: code_runner.CodeRunner, broken: str
) -> None:
    """S29, S87: the broken script is kept and skipped; the rest runs."""
    bad = _add(profile, broken)
    good = _add(profile, "periodic_counter.py")
    good.get_variable("Interval").value = 0.01
    runner.start(profile, MODE)
    assert _wait_for(lambda: len(good.module.ticks) >= 2)
    assert ENTRIES[broken]["expected_error_contains"] in bad.load_error
    assert bad in profile.scripts.scripts


# --- from the upstream research (claude/audits/2026-11-23-script-examples) ----


def test_keyboard_variable_decorator_numpad_key(profile: Profile) -> None:
    """Ported from upstream Joystick Gremlin's test_user_script.py
    (https://github.com/WhiteMagic/JoystickGremlin/blob/develop/test/unit/test_user_script.py,
    Lionel Ott and contributors, GPL-3.0-only): a Numpad key registers by
    its scan code, not its name (04 S95). Upstream uses its example
    script's mode variable; here the suite's keyboard_reader.py."""
    script = _add(profile, "keyboard_reader.py")
    mode_variable = script.get_variable("Mode")
    var = us.KeyboardVariable("", "", True)
    var.value = keyboard.key_from_code(0x4C, False)

    us.callback_registry.clear()
    try:

        @var.decorator(mode_variable)
        def callback() -> None:
            pass

        events = us.callback_registry.registry[dill.UUID_Keyboard][mode_variable.value]
        assert [event.identifier for event in events] == [(0x4C, False)]
    finally:
        us.callback_registry.clear()


def test_script_keeps_working_after_a_mode_change(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    """Upstream's mode-change case (test_e2e_user_script_mode_change.py,
    GPL-3.0-only), at engine level with the vJoy stand-in: a script and a
    profile action share one stick axis. In the other mode the action
    (bound in Default only) writes nothing; back in Default the script and
    the action both work again. Upstream's relative-axis thread is not
    covered here (it needs real vJoy timing)."""
    profile.modes.add_mode("Other")
    item = profile.get_input_item(
        _GUID, InputType.JoystickAxis, 1, MODE, create_if_missing=True
    )
    root = item.add_item_binding().root_action
    action = profile.library.create("Map to vJoy", InputType.JoystickAxis)
    action.vjoy_device_id = 1
    action.vjoy_input_id = 3
    root.insert_action(action, "children")
    script = _add(profile, "axis_to_vjoy.py")
    script.get_variable("Stick axis").value = (_GUID, InputType.JoystickAxis, 1)
    script.get_variable("Scale").value = 1.0
    runner.start(profile, MODE)
    manager = mode_manager.ModeManager()

    def move(value: float) -> list[tuple]:
        vjoy_writes.clear()
        # No mode on the event: the handler uses the current one.
        EventHandler().process_event(
            Event(InputType.JoystickAxis, 1, _GUID, "", value=value)
        )
        return sorted((w[2], round(w[3], 3)) for w in vjoy_writes if w[1] == "axis")

    assert move(0.5) == [(1, 0.5), (3, 0.5)]  # script axis 1, action axis 3
    manager.switch_to(mode_manager.Mode("Other", MODE))
    assert manager.current.name == "Other"
    assert move(0.7) == []  # neither is bound in Other
    manager.switch_to(mode_manager.Mode(MODE, "Other"))
    assert move(0.25) == [(1, 0.25), (3, 0.25)]  # the script still works


# D-04-EVENT-TYPES: scripts annotate gremlin.types.Event, as upstream's do,
# so upstream's R14 example loads with its code unchanged.
def test_upstream_example_loads_unchanged(profile: Profile) -> None:
    script = _add(profile, "upstream_example.py")
    assert script.load_error == ""
    assert len(script.variables) == 14


def test_axes_merge_sums_two_axes(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    script = _add(profile, "axes_merge.py")
    script.get_variable("Axis A").value = (_GUID, InputType.JoystickAxis, 1)
    script.get_variable("Axis B").value = (_GUID, InputType.JoystickAxis, 2)
    runner.start(profile, MODE)
    for axis, value in ((1, 0.3), (2, 0.5), (1, 0.9)):
        EventHandler().process_event(
            Event(InputType.JoystickAxis, axis, _GUID, MODE, value=value)
        )
    assert [round(w[3], 3) for w in vjoy_writes] == [0.3, 0.8, 1.0]
    assert {w[:3] for w in vjoy_writes} == {(1, "axis", 1)}


def test_short_and_long_press_tap_two_buttons(
    profile: Profile,
    runner: code_runner.CodeRunner,
    vjoy_writes: list[tuple],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import clock

    now = [100.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    script = _add(profile, "short_long_press.py")
    _button(script, "Button", 1)
    runner.start(profile, MODE)
    vjoy_writes.clear()

    _press(1, True)
    assert vjoy_writes == []  # nothing on the press itself
    now[0] += 0.1
    _press(1, False)
    assert vjoy_writes == [(1, "button", 1, True), (1, "button", 1, False)]
    vjoy_writes.clear()
    _press(1, True)
    now[0] += 1.0
    _press(1, False)
    assert vjoy_writes == [(1, "button", 2, True), (1, "button", 2, False)]


def test_encoder_steps_go_out_one_per_tick(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    script = _add(profile, "encoder_periodic.py")
    _button(script, "Clockwise", 1)
    _button(script, "Counter-clockwise", 2)
    runner.start(profile, MODE)
    for number in (1, 1, 1, 2):
        _press(number, True)
        _press(number, False)
    assert _wait_for(lambda: len(vjoy_writes) >= 8)
    presses = [w[2] for w in vjoy_writes if w[3] is True]
    assert presses == [1, 1, 1, 2]
    assert script.module.pending == []


def test_macro_from_button_presses_then_releases(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    script = _add(profile, "macro_from_button.py")
    _button(script, "Button", 1)
    runner.start(profile, MODE)
    _press(1, True)
    _press(1, False)
    assert _wait_for(lambda: len(vjoy_writes) >= 2)
    time.sleep(0.1)  # nothing more follows
    assert vjoy_writes == [(1, "button", 7, True), (1, "button", 7, False)]


def test_three_position_switch_sets_its_start_state_at_run(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    from test.unit.conftest import get_fake_device_guid

    stick = get_fake_device_guid(is_virtual=False).uuid  # a listed stand-in
    script = _add(profile, "three_position_switch.py")
    script.get_variable("Up").value = (stick, InputType.JoystickButton, 1)
    script.get_variable("Down").value = (stick, InputType.JoystickButton, 2)
    vjoy_writes.clear()  # what adding it tried (refused then: no Run)
    runner.start(profile, MODE)
    # The switch is in the middle (its inputs read released).
    assert vjoy_writes == [
        (1, "button", 1, False),
        (1, "button", 2, True),
        (1, "button", 3, False),
    ]
    vjoy_writes.clear()
    _press(1, True, stick)
    assert vjoy_writes == [
        (1, "button", 1, True),
        (1, "button", 2, False),
        (1, "button", 3, False),
    ]


def test_three_position_switch_writes_are_refused_without_a_run(
    profile: Profile,
) -> None:
    """Its top-level code also runs when it is added: the real output
    module refuses those writes, as every write with no Run (06 S4)."""
    from gremlin.modules import output

    calls: list[bool] = []
    real = output.write_vjoy

    def spy(*args: object) -> bool:
        calls.append(real(*args))
        return calls[-1]

    with mock.patch.object(output, "write_vjoy", spy):
        script = _add(profile, "three_position_switch.py")
        assert script.load_error == ""
    assert calls == [False, False, False]


def test_r13_migrated_plugin_forwards_the_button(
    profile: Profile, runner: code_runner.CodeRunner, vjoy_writes: list[tuple]
) -> None:
    script = _add(profile, "r13_migrated_plugin.py")
    _button(script, "Physical button", 3)
    runner.start(profile, MODE)
    _press(3, True)
    _press(3, False)
    assert vjoy_writes == [(1, "button", 1, True), (1, "button", 1, False)]
