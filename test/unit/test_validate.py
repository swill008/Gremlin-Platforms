# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The rule checks (gremlin/validate.py) find what they should (Stage 1).

Each check gets a small broken case and must name it by its code; a clean
profile, a clean modules folder and a clean Run -> Stop give no problems.
The checks never raise. Rules from spec 04 S14, S26, S27, S39-S42, S46,
S69, S71, S75 (profile), 03 S1, S6, S7, S22, S64 (module files) and 06
S17-S29 (after Stop). No GL item is fixed here; the checks report the
gaps they meet (GL-046, GL-047) through the test run's validate report.
"""

from __future__ import annotations

import json
import sys
import threading
import types
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import (
    code_runner,
    device_initialization,
    macro,
    plugin_manager,
    run_scope,
    shared_state,
    threads,
    validate,
)
from gremlin.common import SingletonMetaclass
from gremlin.logical_device import LogicalDevice
from gremlin.modules import registry, store
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.tree import TreeNode
from gremlin.types import InputType

# Broken state is built here on purpose: not for the run's validate report.
pytestmark = pytest.mark.validate_off

_STICK = uuid.UUID("5a1d0000-1111-2222-3333-444444444444")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def profile() -> Iterator[Profile]:
    """A new profile, the open one while the test runs. The Logical Device
    rows and the open profile are put back afterwards."""
    before = shared_state.current_profile
    rows = LogicalDevice().memento()
    made = Profile()
    shared_state.current_profile = made
    yield made
    shared_state.current_profile = before
    LogicalDevice().restore(rows)


def _codes(problems: list[str]) -> set[str]:
    return {validate.code_of(p) for p in problems}


def _bind(
    profile: Profile, button: int, name: str = "Description", mode: str = "Default"
) -> tuple[InputItem, InputItemBinding, Any]:
    """An input with one action under its root, as Add Action makes it."""
    action = plugin_manager.PluginManager().create_instance(
        name, InputType.JoystickButton
    )
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    assert item is not None and action is not None
    binding = item.add_item_binding()
    assert binding.root_action is not None
    binding.root_action.insert_action(action, "children")
    return item, binding, action


def _clean(profile: Profile) -> None:
    profile.modes.add_mode("Child")
    profile.modes.set_parent("Child", "Default")
    _bind(profile, 1)
    _bind(profile, 2, mode="Child")
    _bind(profile, 3, name="Map to Logical Device")


# --- profile ------------------------------------------------------------------


def test_a_clean_profile_has_no_problems(profile: Profile) -> None:
    _clean(profile)
    assert validate.profile(profile) == []


def test_a_clean_profile_saved_and_loaded_has_no_problems(
    profile: Profile, tmp_path: Path
) -> None:
    _clean(profile)
    path = tmp_path / "clean.xml"
    profile.to_xml(path)
    loaded = Profile()  # resets the Logical Device rows; the load puts them back
    loaded.from_xml(path)
    shared_state.current_profile = loaded
    assert validate.profile(loaded) == []
    assert loaded.modes.mode_names() == ["Child", "Default"]


def test_an_action_missing_from_the_library_is_dangling(profile: Profile) -> None:
    _, binding, action = _bind(profile, 1)
    del profile.library._actions[action.id]
    problems = validate.profile(profile)
    assert "PROFILE-DANGLING" in _codes(problems)
    # The root still holds it: a library child that isn't there.
    assert "PROFILE-CHILD-MISSING" in _codes(problems)
    assert any(str(action.id) in p for p in problems)


def test_a_root_action_missing_from_the_library_is_dangling(profile: Profile) -> None:
    _, binding, _ = _bind(profile, 1)
    assert binding.root_action is not None
    del profile.library._actions[binding.root_action.id]
    assert "PROFILE-DANGLING" in _codes(validate.profile(profile))


def test_an_input_holding_another_copy_than_the_library(profile: Profile) -> None:
    _, binding, action = _bind(profile, 1)
    other = type(action)(action.behavior_type)
    other._id = action.id
    profile.library._actions[action.id] = other
    assert "PROFILE-NOT-LIBRARY-COPY" in _codes(validate.profile(profile))


def test_a_binding_with_no_action(profile: Profile) -> None:
    _, binding, _ = _bind(profile, 1)
    binding.root_action = None
    assert "PROFILE-BINDING-EMPTY" in _codes(validate.profile(profile))


def test_an_input_in_a_mode_that_isnt_there(profile: Profile) -> None:
    item, _, _ = _bind(profile, 1)
    item.mode = "Gone"
    problems = validate.profile(profile)
    assert _codes(problems) == {"PROFILE-MODE-MISSING"}
    assert "'Gone'" in problems[0]


def test_an_input_in_the_hidden_root_mode(profile: Profile) -> None:
    # mode_exists("") is True (04 gap #13); the check doesn't count the root.
    item, _, _ = _bind(profile, 1)
    item.mode = ""
    assert "PROFILE-MODE-MISSING" in _codes(validate.profile(profile))


def test_a_loop_in_the_mode_tree(profile: Profile) -> None:
    profile.modes.add_mode("A")
    profile.modes.add_mode("B")
    profile.modes.set_parent("B", "A")
    a = profile.modes.find_mode("A")
    b = profile.modes.find_mode("B")
    b.children.append(a)  # past set_parent's check: A is under B too
    problems = validate.profile(profile)  # finishes: never walks for ever
    assert "PROFILE-MODE-LOOP" in _codes(problems)


def test_a_mode_that_is_its_own_parent(profile: Profile) -> None:
    profile.modes.add_mode("A")
    a = profile.modes.find_mode("A")
    a.parent = a
    problems = validate.profile(profile)
    assert "PROFILE-MODE-SELF-PARENT" in _codes(problems)
    assert "PROFILE-MODE-LOOP" in _codes(problems)  # its parents never reach the top


def test_two_modes_of_one_name_and_a_blank_one(profile: Profile) -> None:
    root = profile.modes._hierarchy
    root.add_child(TreeNode("Default"))
    root.add_child(TreeNode(""))
    codes = _codes(validate.profile(profile))
    assert {"PROFILE-MODE-DUPLICATE", "PROFILE-MODE-BLANK"} <= codes


def test_an_unused_action_is_a_warning(profile: Profile) -> None:
    _bind(profile, 1)
    item, binding, _ = _bind(profile, 2)
    item.remove_item_binding(binding)  # kept in memory for Undo (04 S14)
    problems = validate.profile(profile)
    assert _codes(problems) == {"PROFILE-UNUSED-ACTION"}
    assert len(problems) == 2  # the root and the action under it
    assert all(validate.is_warning(p) for p in problems)


def test_an_open_pane_draft_is_not_unused(profile: Profile) -> None:
    _, binding, _ = _bind(profile, 1)
    # An editor opens a draft copy of the binding (Library._copied_from).
    copy = profile.library.clone_action(binding.root_action, draft=True)
    assert copy is not None and copy.id in profile.library._copied_from
    assert validate.profile(profile) == []
    # The same copy without the draft mark is reported.
    profile.library._copied_from.clear()
    assert _codes(validate.profile(profile)) == {"PROFILE-UNUSED-ACTION"}


def test_a_missing_logical_device_input(profile: Profile) -> None:
    _, _, action = _bind(profile, 1, name="Map to Logical Device")
    assert validate.profile(profile) == []
    LogicalDevice().delete(
        LogicalDevice.Input.Identifier(
            action.logical_input_type, action.logical_input_id
        )
    )
    problems = validate.profile(profile)
    assert _codes(problems) == {"PROFILE-LOGICAL-MISSING"}


def test_a_missing_logical_device_input_in_a_condition(profile: Profile) -> None:
    from action_plugins.condition.condition import LogicalDeviceCondition

    LogicalDevice().create(InputType.JoystickButton)
    _, _, action = _bind(profile, 1, name="Condition")
    condition = LogicalDeviceCondition()
    action.conditions.append(condition)
    assert validate.profile(profile) == []
    state: Any = condition._states[0]
    LogicalDevice().delete(
        LogicalDevice.Input.Identifier(state.input_type, state.input_id)
    )
    assert "PROFILE-LOGICAL-MISSING" in _codes(validate.profile(profile))


def test_the_logical_check_makes_no_logical_device(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Report only: with no Logical Device yet the check skips, makes none.
    _bind(profile, 1, name="Map to Logical Device")
    # Put the shared one back before the fixtures tidy up: undone at the end
    # of the test, the Logical Device keeper would tidy a stand-in instead.
    with monkeypatch.context() as patch:
        patch.delitem(SingletonMetaclass._instances, LogicalDevice, raising=False)
        assert validate.profile(profile) == []
        assert LogicalDevice not in SingletonMetaclass._instances


def test_the_profile_check_never_raises() -> None:
    problems = validate.profile(object())  # type: ignore[arg-type]
    assert problems and _codes(problems) == {"VALIDATE-ERROR"}


# --- module files -------------------------------------------------------------


_Folder = tuple[Path, dict[str, str], list[types.SimpleNamespace]]


@pytest.fixture
def modules_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[_Folder]:
    """An empty modules folder, saved file choices and connected sticks, all
    stand-ins for this test."""
    folder = tmp_path / "modules"
    folder.mkdir()
    bindings: dict[str, str] = {}
    sticks: list[types.SimpleNamespace] = []
    monkeypatch.setattr(registry, "_folder", lambda: folder)
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(registry, "_binding_store", lambda: dict(bindings))
    monkeypatch.setattr(validate, "_bindings_registered", lambda: True)
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: list(sticks))
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    yield folder, bindings, sticks
    registry._cache.clear()


def _stick(name: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(name=name, device_guid=uuid.uuid4(), is_virtual=False)


def _module(folder: Path, slug: str, device: str, guid: object = "") -> None:
    doc = {"device": device, "direction": "source", "boundGuidLocal": str(guid)}
    (folder / f"{slug}.json").write_text(json.dumps(doc), encoding="utf-8")


def test_clean_module_files_have_no_problems(modules_folder: _Folder) -> None:
    folder, bindings, sticks = modules_folder
    sticks += [_stick("Stick A"), _stick("Stick B")]
    _module(folder, "stick_a", "Stick A", sticks[0].device_guid)
    _module(folder, "stick_b", "Stick B", sticks[1].device_guid)
    bindings["name:stick_a"] = "stick_a"
    assert validate.modules() == []


def test_a_damaged_module_file(modules_folder: _Folder) -> None:
    folder, _, _ = modules_folder
    (folder / "broken.json").write_text("{not json", encoding="utf-8")
    (folder / "latin.json").write_bytes(b'{"device": "\xe9"}')
    (folder / "list.json").write_text("[]", encoding="utf-8")
    problems = validate.modules()
    assert _codes(problems) == {"MODULES-DAMAGED"}
    assert sorted(p.split(" ")[1] for p in problems) == [
        "broken.json",
        "latin.json",
        "list.json",
    ]


def test_two_connected_sticks_on_one_file(modules_folder: _Folder) -> None:
    folder, bindings, sticks = modules_folder
    sticks += [_stick("Stick A"), _stick("Stick B")]
    _module(folder, "shared", "Shared")
    for stick in sticks:
        bindings[str(stick.device_guid).upper().replace("-", "")] = "shared"
    problems = validate.modules()
    assert _codes(problems) == {"MODULES-SHARED-FILE"}
    assert "shared.json" in problems[0]


def test_a_saved_choice_naming_a_missing_file(modules_folder: _Folder) -> None:
    _, bindings, _ = modules_folder
    bindings["name:stick_a"] = "gone"
    assert _codes(validate.modules()) == {"MODULES-BINDING-MISSING"}


def test_the_modules_check_never_raises(
    modules_folder: _Folder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> Path:
        raise OSError("no folder")

    monkeypatch.setattr(store, "folder", broken)
    assert _codes(validate.modules()) == {"VALIDATE-ERROR"}


# --- after Stop ---------------------------------------------------------------


def test_nothing_left_is_no_problem() -> None:
    assert validate.after_stop() == []


def test_held_keys_buttons_and_pulses(monkeypatch: pytest.MonkeyPatch) -> None:
    # What a Run holds is run_scope's (map 3): a key, a mouse button and a
    # pulse's release (a timer that fires at Stop) a Stop left behind.
    run_scope.stop()
    run_scope._reset_for_tests()
    run = run_scope.begin()
    try:
        run_scope.hold(None, "key", (30, False), lambda: None)
        run_scope.hold(None, "mouse", "left", lambda: None)
        run_scope.timer("pulse", 60, lambda: None, at_stop="fire")
        # A Stop that ended the Run but let go of nothing.
        monkeypatch.setattr(run_scope, "_running", False)
        monkeypatch.setattr(run_scope, "_number", run + 1)
        assert _codes(validate.after_stop()) == {
            "RUN-HELD-KEYS",
            "RUN-HELD-BUTTONS",
            "RUN-PENDING-PULSES",
        }
    finally:
        monkeypatch.undo()
        run_scope._reset_for_tests()


def test_runtime_and_macro_manager_still_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shared_state, "_runtime_active", True)
    monkeypatch.setitem(
        SingletonMetaclass._instances,
        macro.MacroManager,
        types.SimpleNamespace(_is_running=True),
    )
    assert _codes(validate.after_stop()) == {"RUN-ACTIVE", "RUN-MACRO-RUNNING"}


def test_a_vjoy_device_or_xbox_pad_still_held(monkeypatch: pytest.MonkeyPatch) -> None:
    from vigem.xbox import XboxProxy
    from vjoy.vjoy import VJoyProxy

    monkeypatch.setattr(VJoyProxy, "vjoy_devices", {1: object()})
    monkeypatch.setitem(
        SingletonMetaclass._instances, XboxProxy, types.SimpleNamespace(_pads={1: 0})
    )
    assert _codes(validate.after_stop()) == {"RUN-VJOY-HELD", "RUN-XBOX-PLUGGED"}


def test_held_vjoy_ids_never_loads_vjoy(monkeypatch: pytest.MonkeyPatch) -> None:
    # 06 Q16: a read never opens a device, so vJoyInterface.dll isn't loaded.
    from gremlin.modules import output

    for name in ("vjoy.vjoy", "vjoy.vjoy_interface"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    assert output.held_vjoy_ids() == []
    assert validate.after_stop() == []
    assert "vjoy.vjoy" not in sys.modules
    assert "vjoy.vjoy_interface" not in sys.modules


def test_a_run_thread_still_running() -> None:
    release = threading.Event()
    thread = threads.start("user script timers", release.wait, 30.0, stop=release.set)
    try:
        problems = validate.after_stop()
        assert _codes(problems) == {"RUN-THREADS-LEFT"}
        assert "user script timers" in problems[0]
    finally:
        release.set()
        thread.join(10.0)
    assert validate.after_stop() == []


def test_the_after_stop_check_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shared_state, "runtime_active", mock.Mock(side_effect=OSError))
    assert _codes(validate.after_stop()) == {"VALIDATE-ERROR"}


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[code_runner.CodeRunner]:
    """A CodeRunner whose drivers, devices, sound and network are stand-ins;
    macros and the mouse controller are the real ones."""
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    fake_listener = mock.MagicMock(return_value=mock.MagicMock())
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    shared_state.set_runtime_active(False)


def _settles(check: Callable[[], list[str]], seconds: float = 10.0) -> list[str]:
    """check() once it is empty, or its last result after seconds (Stop asks
    the Run's threads to end; they end soon after)."""
    import time

    end = time.monotonic() + seconds
    found = check()
    while found and time.monotonic() < end:
        time.sleep(0.02)
        found = check()
    return found


def test_run_then_stop_leaves_nothing(
    runner: code_runner.CodeRunner, profile: Profile
) -> None:
    _clean(profile)
    runner.start(profile, "Default")
    assert "RUN-ACTIVE" in _codes(validate.after_stop())
    runner.stop()
    assert _settles(validate.after_stop) == []
