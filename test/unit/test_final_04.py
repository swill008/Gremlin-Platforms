# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final phase, page 04 (profile and modes): checks for the section 8
statements that had none (claude/final-test-plan/04-profile-modes.md).

Each test names the statement it checks. Tests marked xfail(strict) with a
FINAL-04-<n> id are spec gaps found here: the program differs from the
spec and the lead routes the fix.

Nothing here touches the PC: no Run of real devices, no vJoy, no files
outside pytest's temporary folders; the open profile, the mode stack, the
program settings and sys.path are put back after each test.
"""

from __future__ import annotations

import sys
import types
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree

sys.path.append(".")

import pytest
from PySide6 import QtCore

import dill
from gremlin import (
    code_runner,
    config,
    device_initialization,
    event_handler,
    mode_manager,
    plugin_manager,
    shared_state,
    swap_devices,
    util,
)
from gremlin.error import GremlinError
from gremlin.logical_device import LogicalDevice
from gremlin.osc import OscDevice
from gremlin.profile import Profile, ScriptManager, VirtualAxisButton
from gremlin.types import InputType
from gremlin.user_script import Script

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")
_OTHER = uuid.UUID("11111111-2222-3333-4444-555555555555")
_THIRD = uuid.UUID("22222222-3333-4444-5555-666666666666")
_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
# Qt objects a test made that hook into the program-wide signals; unhooked
# after the test so a later profile change doesn't reach them.
_KEEP: list[QtCore.QObject] = []
# Backends tests made, kept alive for the whole run: Backend hooks a lambda
# to EventHandler.is_active that can't be unhooked, and a deleted Backend
# makes that lambda raise in a later test.
_BACKENDS: list[QtCore.QObject] = []


def _global_signals() -> list[QtCore.SignalInstance]:
    from gremlin.signal import signal

    owners = (
        signal,
        event_handler.EventListener(),
        event_handler.EventHandler(),
        mode_manager.ModeManager(),
    )
    return [
        getattr(owner, name)
        for owner in owners
        for name in dir(type(owner))
        if isinstance(getattr(type(owner), name, None), QtCore.Signal)
    ]


def _release(obj: QtCore.QObject, signals: list[QtCore.SignalInstance]) -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # "Failed to disconnect"
        for target in (obj, *obj.findChildren(QtCore.QObject)):
            for cls in type(target).__mro__:
                if not cls.__module__.startswith("gremlin"):
                    continue
                for name, value in vars(cls).items():
                    if name.startswith("__") or not isinstance(
                        value, (types.FunctionType, QtCore.Signal)
                    ):
                        continue
                    slot = getattr(target, name)
                    for sig in signals:
                        try:
                            sig.disconnect(slot)
                        except (RuntimeError, TypeError):
                            pass


@pytest.fixture(autouse=True)
def _release_kept() -> Iterator[None]:
    start = len(_KEEP)
    yield
    made = _KEEP[start:]
    del _KEEP[start:]
    if made:
        signals = _global_signals()
        for obj in made:
            _release(obj, signals)


@pytest.fixture
def profile() -> Iterator[Profile]:
    """A new profile as the open one; the one before is put back."""
    before = shared_state.current_profile
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = before
    if isinstance(before, Profile):
        before.bind_devices()
    else:
        LogicalDevice().reset()
        OscDevice().reset()


@pytest.fixture
def settings_kept() -> Iterator[Callable[..., None]]:
    """Puts back the program settings a test changes (keep(*key) first)."""
    cfg = config.Configuration()
    kept: list[tuple[tuple[str, ...], Any]] = []

    def keep(*key: str) -> None:
        kept.append((key, cfg.value(*key)))

    yield keep
    for key, value in reversed(kept):
        cfg.set(*key, value)


@pytest.fixture
def real_backend(
    monkeypatch: pytest.MonkeyPatch, settings_kept: Callable[..., None]
) -> Iterator[Any]:
    """The program's Backend class (not the shared instance), without its
    process-monitor thread or error boxes. Puts back the open profile, the
    mode stack, the recent / last profile / last mode settings and sys.path."""
    from gremlin import process_monitor
    from gremlin.ui import backend

    monkeypatch.setattr(process_monitor.ProcessMonitor, "start", lambda self: None)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(backend, "display_error", lambda *a, **k: None)
    settings_kept("global", "internal", "last-profile")
    settings_kept("global", "internal", "recent-profiles")
    settings_kept("global", "internal", "last-mode-per-profile")
    before = shared_state.current_profile
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    be = backend.Backend.klass(cast(Any, None))
    _KEEP.append(be)
    _BACKENDS.append(be)
    yield be
    shared_state.current_profile = before
    mm._mode_stack = stack
    if isinstance(before, Profile):
        before.bind_devices()
    else:
        LogicalDevice().reset()


def _description(note: str) -> Any:  # noqa: ANN401
    desc = plugin_manager.PluginManager().create_instance(
        "Description", InputType.JoystickButton
    )
    desc.description = note
    return desc


def _bind(
    profile: Profile, hw: int = 1, note: str = "note",
    device: uuid.UUID = _STICK, mode: str = "Default",
) -> Any:  # noqa: ANN401
    item = profile.get_input_item(
        device, InputType.JoystickButton, hw, mode, create_if_missing=True
    )
    assert item is not None
    item.add_item_binding().root_action.insert_action(_description(note), "children")
    return item


def _notes(item: Any) -> list[str]:  # noqa: ANN401
    return [
        a.description
        for binding in item.action_sequences
        for a in binding.root_action.get_actions()[0]
    ]


def _profile_file(path: Path, start: str = "Last Active") -> Path:
    p = Profile()
    p.modes.add_mode("Alpha")
    p.modes.add_mode("Bravo")
    p.settings.startup_mode = start
    p.to_xml(path)
    return path


# --- Profile file ------------------------------------------------------------


def test_s1_s62_profile_settings_stay_in_memory_until_saved(
    profile: Profile, tmp_path: Path
) -> None:
    """S1, S62: Startup Mode, Macro Default Delay, vJoy Behavior and Initial
    Values are the profile's; a change is unsaved until Save writes it."""
    from gremlin.ui.profile import ProfileSettingsModel, StartupModeModel

    path = _profile_file(tmp_path / "settings.xml")
    profile.from_xml(path)
    on_disk = path.read_bytes()
    assert not profile.has_unsaved_changes()

    startup = StartupModeModel()
    delay = ProfileSettingsModel()
    _KEEP.extend([startup, delay])
    labels = [
        startup.data(startup.index(i, 0), QtCore.Qt.ItemDataRole.UserRole + 1)
        for i in range(startup.rowCount())
    ]
    startup.setProperty("currentSelectionIndex", labels.index("Bravo"))
    delay.setProperty("macroDefaultDelay", 0.2)
    profile.settings.vjoy_as_input[2] = True
    profile.settings.set_initial_vjoy_axis_value(1, 3, 0.5)

    assert path.read_bytes() == on_disk  # nothing written yet
    assert profile.has_unsaved_changes()

    profile.to_xml(path)
    back = Profile()
    back.from_xml(path)
    assert back.settings.startup_mode == "Bravo"
    assert back.settings.macro_default_delay == pytest.approx(0.2)
    assert back.settings.vjoy_as_input.get(2) is True
    assert back.settings.get_initial_vjoy_axis_value(1, 3) == pytest.approx(0.5)
    assert not profile.has_unsaved_changes()


def test_s2_logical_osc_rows_and_device_names_are_in_the_profile_file(
    profile: Profile, tmp_path: Path
) -> None:
    """S2: the Logical Device and OSC rows and the device names list are
    saved in the profile file and come back with it."""
    profile.bind_devices()
    LogicalDevice().create(InputType.JoystickButton, label="Fire")
    OscDevice().create(InputType.JoystickButton, label="/osc/fire")
    _bind(profile)
    profile.remember_device(_STICK, "Test Stick")
    path = tmp_path / "rows.xml"
    profile.to_xml(path)

    LogicalDevice().reset()
    OscDevice().reset()
    back = Profile()
    back.from_xml(path)
    back.bind_devices()
    assert LogicalDevice().exists("Fire")
    assert OscDevice().find_address("/osc/fire") is not None
    assert back.device_database.devices[_STICK].name == "Test Stick"


def test_s5_new_and_load_stop_the_running_profile_first(
    real_backend: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> None:
    """S5: New and Load stop a running profile before the profile changes."""
    stopped_with: list[object] = []
    monkeypatch.setattr(
        real_backend.runner, "stop", lambda: stopped_with.append(real_backend.profile)
    )
    path = _profile_file(tmp_path / "flight.xml")

    before = real_backend.profile
    real_backend.loadProfile(str(path))
    assert stopped_with[:1] == [before]
    assert real_backend.profile is not before

    stopped_with.clear()
    loaded = real_backend.profile
    real_backend.newProfile()
    assert stopped_with[:1] == [loaded]
    assert real_backend.profile is not loaded


def test_s17_every_save_that_changed_something_is_a_history_entry(
    profile: Profile, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S17: a save that changed the file records a History entry; a save
    that changed nothing records none."""
    from gremlin import history_profile

    recorded: list[Path] = []
    monkeypatch.setattr(
        history_profile,
        "record_save",
        lambda path, before, after: recorded.append(path),
    )
    path = tmp_path / "history.xml"
    _bind(profile, note="first")
    profile.to_xml(path)
    assert recorded == [path]

    profile.to_xml(path)  # nothing changed
    assert recorded == [path]

    _bind(profile, hw=2, note="second")
    profile.to_xml(path)
    assert recorded == [path, path]


# --- Loading -----------------------------------------------------------------


def test_s24_a_profile_that_failed_to_load_is_not_recent_or_last(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    """S24: a profile that failed to load is not added to Recent and is not
    made the last profile."""
    good = _profile_file(tmp_path / "good.xml")
    real_backend.loadProfile(str(good))
    cfg = config.Configuration()
    recent = list(cfg.value("global", "internal", "recent-profiles"))

    bad = tmp_path / "bad.xml"
    bad.write_text("<profile version='14'><inputs>", encoding="utf-8")
    real_backend.loadProfile(str(bad))

    assert real_backend.profile.fpath == good  # the open one again (S23)
    assert cfg.value("global", "internal", "last-profile") == str(good)
    assert list(cfg.value("global", "internal", "recent-profiles")) == recent
    assert all("bad.xml" not in entry for entry in recent)


def test_s32_another_profile_clears_the_selected_key(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    """S32: loading another profile clears the Keyboard page's selected key
    (a stick's selected input stays)."""
    from gremlin.ui.device import InputIdentifier

    state = real_backend.ui_state
    key = InputIdentifier(dill.UUID_Keyboard, InputType.Keyboard, 30)
    stick = InputIdentifier(_STICK, InputType.JoystickButton, 1)
    _KEEP.extend([key, stick])
    state.setCurrentInput(key, 0)
    state.setCurrentInput(stick, 0)
    assert dill.UUID_Keyboard in state._current_input

    real_backend.loadProfile(str(_profile_file(tmp_path / "other.xml")))
    assert dill.UUID_Keyboard not in state._current_input
    assert _STICK in state._current_input


# --- Modes: the tree ------------------------------------------------------------


def _listed(model: Any) -> list[str]:  # noqa: ANN401
    role = QtCore.Qt.ItemDataRole.UserRole + 1
    return [model.data(model.index(i, 0), role) for i in range(model.rowCount())]


def test_s41_modes_are_listed_in_name_order(profile: Profile) -> None:
    """S41: the mode list (Manage Modes and the toolbar Mode box) is in name
    order, whatever order the modes were added in."""
    from gremlin.ui.profile import ModeListModel

    for name in ("Zulu", "Mike", "Echo"):
        profile.modes.add_mode(name)
    profile.modes.set_parent("Echo", "Zulu")
    model = ModeListModel()
    _KEEP.append(model)
    assert _listed(model) == ["Default", "Echo", "Mike", "Zulu"]


def test_s41_modes_are_listed_alphabetically_whatever_the_capitals(
    profile: Profile,
) -> None:
    """S41: alphabetical order, as a person reads it: capitals don't move a
    mode to the front."""
    from gremlin.ui.profile import ModeListModel

    for name in ("bravo", "Charlie", "alpha"):
        profile.modes.add_mode(name)
    model = ModeListModel()
    _KEEP.append(model)
    assert _listed(model) == ["alpha", "bravo", "Charlie", "Default"]


def test_s52_last_active_with_no_record_is_the_first_listed_mode(
    profile: Profile,
) -> None:
    """S52: new profiles start on Last Active; with no record it is the first
    mode in the mode list (alphabetical ignoring capitals, nested or not)."""
    profile.modes.add_mode("Bravo")
    profile.modes.add_mode("alpha")
    profile.modes.set_parent("alpha", "Bravo")
    assert profile.settings.startup_mode == "Last Active"
    assert mode_manager.resolve_start_mode(profile) == "alpha"


def test_s42_a_mode_inherits_from_any_mode_not_itself_or_below(
    profile: Profile,
) -> None:
    """S42: Inherits from offers "(none)" and every mode that is not the mode
    itself or below it; "(none)" makes it top-level."""
    from gremlin.ui.profile import ModeHierarchyModel

    modes = profile.modes
    for name in ("Top", "Mid", "Low", "Other"):
        modes.add_mode(name)
    modes.set_parent("Mid", "Top")
    modes.set_parent("Low", "Mid")
    model = ModeHierarchyModel()
    _KEEP.append(model)

    offered = [entry["value"] for entry in model.validParents("Mid")]
    assert offered == ["", "Default", "Other", "Top"]
    assert "Mid" not in offered and "Low" not in offered

    model.setParent("Mid", "")
    assert modes.find_mode("Mid").parent.value == ""  # the hidden root
    assert modes.find_mode("Low").parent.value == "Mid"  # moved with it
    low_offers = [e["value"] for e in model.validParents("Low")]
    assert "Low" not in low_offers and "Mid" in low_offers


def test_s43_a_child_mode_uses_its_parents_actions_through_every_level(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S43: an input the child mode leaves empty uses the parent's actions,
    through any number of levels; a mode's own actions win, also for the
    modes below it."""
    handler = event_handler.EventHandler()
    monkeypatch.setattr(handler, "callbacks", {})
    monkeypatch.setattr(handler, "known_modes", set())
    modes = profile.modes
    # Names chosen so name order is not tree order.
    for name in ("Zeta", "Kappa", "Alpha"):
        modes.add_mode(name)
    modes.set_parent("Kappa", "Zeta")
    modes.set_parent("Alpha", "Kappa")

    def event(hw: int) -> event_handler.Event:
        return event_handler.Event(
            event_type=InputType.JoystickButton,
            device_guid=_STICK,
            identifier=hw,
            mode="",
        )

    def top_one(_e: object) -> None: ...
    def top_two(_e: object) -> None: ...
    def middle_two(_e: object) -> None: ...

    handler.add_callback(_STICK, "Zeta", event(1), top_one)
    handler.add_callback(_STICK, "Zeta", event(2), top_two)
    handler.add_callback(_STICK, "Kappa", event(2), middle_two)
    handler.build_event_lookup(modes.mode_list())

    lookup = handler.callbacks[_STICK]
    assert lookup["Alpha"][event(1)] is lookup["Zeta"][event(1)]
    assert lookup["Kappa"][event(1)] is lookup["Zeta"][event(1)]
    assert lookup["Alpha"][event(2)] is lookup["Kappa"][event(2)]
    assert lookup["Kappa"][event(2)] is not lookup["Zeta"][event(2)]
    assert event(1) not in lookup.get("Default", {})


# --- Modes at run time ---------------------------------------------------------


def test_s51_the_toolbar_follows_the_running_mode(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    """S51: one Mode on the toolbar; a mode change while running (Change
    Mode) shows there."""
    real_backend.loadProfile(str(_profile_file(tmp_path / "flight.xml")))
    mm = mode_manager.ModeManager()
    assert real_backend.ui_state.currentMode == mm.current.name == "Alpha"
    mm.switch_to(mode_manager.Mode("Bravo", mm.current.name))
    assert real_backend.ui_state.currentMode == "Bravo"
    assert real_backend.currentMode == "Bravo"


def test_s53_run_starts_in_the_toolbar_mode_not_the_startup_mode(
    real_backend: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> None:
    """S53: Run starts in the mode shown on the toolbar."""
    started: list[tuple[object, str]] = []
    monkeypatch.setattr(
        real_backend.runner, "start", lambda prof, mode: started.append((prof, mode))
    )
    monkeypatch.setattr(real_backend.runner, "stop", lambda: None)
    real_backend.loadProfile(str(_profile_file(tmp_path / "flight.xml", "Alpha")))
    real_backend.selectMode("Bravo")
    real_backend.activate_gremlin(True)
    assert started == [(real_backend.profile, "Bravo")]


# --- Profile Settings ----------------------------------------------------------


def test_s63_startup_mode_offers_last_active_and_every_mode(
    profile: Profile,
) -> None:
    """S63: Startup Mode offers Last Active and every mode by name (no Use
    Heuristic); picking one sets the profile's Startup Mode."""
    from gremlin.ui.profile import StartupModeModel

    profile.modes.add_mode("Space")
    profile.modes.add_mode("Ground")
    model = StartupModeModel()
    _KEEP.append(model)
    labels = _listed(model)
    assert labels == ["Last Active", "Default", "Ground", "Space"]
    for index, label in enumerate(labels):
        model.setProperty("currentSelectionIndex", index)
        assert profile.settings.startup_mode == label
        assert model.property("currentSelectionIndex") == index


def test_s66_a_vjoy_switched_to_input_is_listed_with_the_physical_devices(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S66: each vJoy device is an output by default; one switched to input
    is listed with the physical devices, not with the outputs."""
    stick = types.SimpleNamespace(name="stick", is_virtual=False, vjoy_id=0)
    vjoy1 = types.SimpleNamespace(name="vjoy 1", is_virtual=True, vjoy_id=1)
    vjoy2 = types.SimpleNamespace(name="vjoy 2", is_virtual=True, vjoy_id=2)
    monkeypatch.setattr(
        device_initialization,
        "_joystick_devices",
        {_STICK: stick, _OTHER: vjoy1, _THIRD: vjoy2},
    )
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [vjoy1, vjoy2])

    assert device_initialization.input_devices() == [stick]
    assert device_initialization.output_vjoy_devices() == [vjoy1, vjoy2]

    profile.settings.vjoy_as_input[1] = True
    assert device_initialization.input_devices() == [stick, vjoy1]
    assert device_initialization.output_vjoy_devices() == [vjoy2]


def test_s67_initial_values_are_clamped_when_the_profile_loads(
    profile: Profile, tmp_path: Path
) -> None:
    """S67: vJoy Initial Values outside -1..1 in the file load clamped."""
    profile.settings.vjoy_initial_values = {1: {1: 2.5, 2: -7.0, 3: 0.25}}
    path = tmp_path / "initial.xml"
    profile.to_xml(path)
    back = Profile()
    back.from_xml(path)
    assert back.settings.get_initial_vjoy_axis_value(1, 1) == 1.0
    assert back.settings.get_initial_vjoy_axis_value(1, 2) == -1.0
    assert back.settings.get_initial_vjoy_axis_value(1, 3) == pytest.approx(0.25)


# --- Bindings, inputs and the action library -----------------------------------


def test_s68_one_input_item_per_input_and_mode_and_empty_ones_are_not_saved(
    profile: Profile, tmp_path: Path
) -> None:
    """S68: one input item per device, input and mode; an input with no
    actions is not written to the file."""
    profile.modes.add_mode("Space")
    first = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    again = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    other_mode = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Space", create_if_missing=True
    )
    assert first is again and first is not other_mode
    _bind(profile, hw=2)
    profile.get_input_item(
        _STICK, InputType.JoystickButton, 3, "Default", create_if_missing=True
    )

    path = tmp_path / "items.xml"
    profile.to_xml(path)
    inputs = ElementTree.parse(path).getroot().find("inputs")
    assert inputs is not None and len(inputs) == 1
    back = Profile()
    back.from_xml(path)
    assert back.get_input_item(_STICK, InputType.JoystickButton, 2, "Default")
    assert back.get_input_item(_STICK, InputType.JoystickButton, 1, "Default") is None
    assert back.get_input_item(_STICK, InputType.JoystickButton, 3, "Default") is None


def test_s69_treat_as_button_keeps_its_settings_and_is_refused_without(
    profile: Profile, tmp_path: Path
) -> None:
    """S69: a binding keeps its root action and "Treat as"; an axis treated
    as a button needs its virtual button settings or the profile is
    refused."""
    item = profile.get_input_item(
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    binding = item.add_item_binding()
    binding.behavior = InputType.JoystickButton
    binding.virtual_button = VirtualAxisButton(0.2, 0.6)
    binding.root_action.insert_action(_description("axis button"), "children")
    path = tmp_path / "treat_as.xml"
    profile.to_xml(path)

    back = Profile()
    back.from_xml(path)
    loaded = back.get_input_item(_STICK, InputType.JoystickAxis, 1, "Default")
    kept = loaded.action_sequences[0]
    assert kept.behavior == InputType.JoystickButton
    assert isinstance(kept.virtual_button, VirtualAxisButton)
    assert (kept.virtual_button.lower_limit, kept.virtual_button.upper_limit) == (
        pytest.approx(0.2),
        pytest.approx(0.6),
    )
    assert _notes(loaded) == ["axis button"]

    tree = ElementTree.parse(path)
    for config_node in tree.getroot().iter("action-configuration"):
        for vb in config_node.findall("virtual-button"):
            config_node.remove(vb)
    broken = tmp_path / "no_virtual_button.xml"
    tree.write(broken, encoding="utf-8", xml_declaration=True)
    with pytest.raises(GremlinError):
        Profile().from_xml(broken)


def test_s72_actions_added_twice_get_new_ids(profile: Profile) -> None:
    """S72: the same actions added twice (Device Pack, History) get new ids,
    so they never clash with the ones already there."""
    item = _bind(profile, note="shared look")
    snapshot = profile.input_snapshot(item)
    assert snapshot is not None
    old_root = item.action_sequences[0].root_action.id

    added = []
    for device in (_OTHER, _THIRD):
        added += profile.add_inputs(device, [snapshot["input"]], snapshot["actions"])

    roots = [old_root] + [i.action_sequences[0].root_action.id for i in added]
    assert len(set(roots)) == 3
    assert all(profile.library.has_action(r) for r in roots)
    assert [_notes(i) for i in [item, *added]] == [["shared look"]] * 3
    child_ids = {
        a.id
        for i in [item, *added]
        for a in i.action_sequences[0].root_action.get_actions()[0]
    }
    assert len(child_ids) == 3


# --- Swap Devices ----------------------------------------------------------------


def test_s78_inputs_with_no_actions_move_with_their_device(profile: Profile) -> None:
    """S78: inputs with no actions move with their device too."""
    empty = profile.get_input_item(
        _STICK, InputType.JoystickButton, 7, "Default", create_if_missing=True
    )
    bound = _bind(profile, hw=1)
    swap_devices.swap_devices(profile, _STICK, _OTHER)
    assert empty.device_id == _OTHER and bound.device_id == _OTHER
    button = InputType.JoystickButton
    assert profile.get_input_item(_OTHER, button, 7, "Default") is empty
    assert profile.get_input_item(_STICK, button, 7, "Default") is None


def test_s83_a_swap_needs_a_save_to_stick(profile: Profile, tmp_path: Path) -> None:
    """S83: a swap changes the open profile only; the file keeps the old
    device until the profile is saved."""
    _bind(profile, note="fire")
    path = tmp_path / "swap.xml"
    profile.to_xml(path)
    on_disk = path.read_bytes()

    swap_devices.swap_devices(profile, _STICK, _OTHER)
    assert profile.has_unsaved_changes()
    assert path.read_bytes() == on_disk

    profile.to_xml(path)
    back = Profile()
    back.from_xml(path)
    moved = back.get_input_item(_OTHER, InputType.JoystickButton, 1, "Default")
    assert moved is not None and _notes(moved) == ["fire"]
    assert back.get_input_item(_STICK, InputType.JoystickButton, 1, "Default") is None


# --- User scripts ----------------------------------------------------------------


@pytest.fixture
def scripts_made() -> Iterator[list[Script]]:
    """Scripts a test made: taken out of the program-wide variable list."""
    made: list[Script] = []
    yield made
    for script in made:
        Script.variable_registry.remove_script(script)


def test_s84_a_script_file_added_twice_gets_its_own_instance_names(
    tmp_path: Path, scripts_made: list[Script]
) -> None:
    """S84: an added script is named "Instance N"; one file may be added more
    than once under different names."""
    path = tmp_path / "script.py"
    path.write_text("x = 1\n", encoding="utf-8")
    other = tmp_path / "other.py"
    other.write_text("y = 2\n", encoding="utf-8")
    manager = ScriptManager(Profile())
    for p in (path, path, other, path):
        manager.add_script(p)
    scripts_made.extend(manager.scripts)
    names = sorted((s.path.name, s.name) for s in manager.scripts)
    assert names == [
        ("other.py", "Instance 1"),
        ("script.py", "Instance 1"),
        ("script.py", "Instance 2"),
        ("script.py", "Instance 3"),
    ]


def test_s85_a_script_name_is_unique_per_file(
    tmp_path: Path, scripts_made: list[Script]
) -> None:
    """S85: a script can be renamed, but not to a name another instance of
    the same file has; another file may use the same name."""
    path = tmp_path / "script.py"
    path.write_text("x = 1\n", encoding="utf-8")
    other = tmp_path / "other.py"
    other.write_text("y = 2\n", encoding="utf-8")
    manager = ScriptManager(Profile())
    for p in (path, path, other):
        manager.add_script(p)
    scripts_made.extend(manager.scripts)

    manager.rename_script(path, "Instance 2", "Instance 1")  # taken in this file
    assert sorted(s.name for s in manager.scripts if s.path == path) == [
        "Instance 1",
        "Instance 2",
    ]
    manager.rename_script(path, "Instance 2", "Pilot")
    manager.rename_script(other, "Instance 1", "Pilot")
    assert sorted((s.path.name, s.name) for s in manager.scripts) == [
        ("other.py", "Pilot"),
        ("script.py", "Instance 1"),
        ("script.py", "Pilot"),
    ]


def test_s86_a_script_saved_with_a_path_in_the_scripts_folder_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scripts_made: list[Script]
) -> None:
    """S86: scripts and their variable values are saved with the profile; a
    path relative to the scripts folder is read from there."""
    folder = tmp_path / "scripts"
    folder.mkdir()
    monkeypatch.setattr(util, "scripts_dir", lambda: folder)
    path = folder / "throttle.py"
    path.write_text(
        "import gremlin.user_script as us\n"
        "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n",
        encoding="utf-8",
    )
    script = Script(path, "Instance 1")
    scripts_made.append(script)
    script.variables["speed"].value = 8
    node = script.to_xml()
    for prop in node.iter("property"):
        if prop.findtext("name") == "path":
            value = prop.find("value")
            assert value is not None
            value.text = "throttle.py"
    root = ElementTree.Element("profile")
    ElementTree.SubElement(root, "scripts").append(node)

    manager = ScriptManager(Profile())
    manager.from_xml(root)
    scripts_made.extend(manager.scripts)
    loaded = manager.scripts[0]
    assert loaded.path == path
    assert loaded.load_error == ""
    assert loaded.variables["speed"].value == 8


def test_s87_only_configured_scripts_run_and_each_run_reloads_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scripts_made: list[Script]
) -> None:
    """S87: Run runs only scripts whose required variables are set, and
    loads each script fresh at every Run."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    path = tmp_path / "counted.py"
    runs = tmp_path / "runs.txt"
    path.write_text(
        "import gremlin.user_script as us\n"
        "label = us.StringVariable('label', 'Label', False, '')\n"
        f"with open({str(runs)!r}, 'a', encoding='utf-8') as f:\n"
        "    f.write('ran\\n')\n",
        encoding="utf-8",
    )

    def count() -> int:
        return len(runs.read_text(encoding="utf-8").splitlines())

    script = Script(path, "Instance 1")
    scripts_made.append(script)
    # Adding doesn't wait for the script's code (D-04-Q13-NOWAIT); reading
    # its load error does.
    assert script.load_error == ""
    assert count() == 1  # its variables were read when it was added
    runner = types.SimpleNamespace(
        _sys_path=None,
        _profile=types.SimpleNamespace(scripts=types.SimpleNamespace(scripts=[script])),
    )

    assert not script.is_configured
    code_runner.CodeRunner._setup_user_scripts(cast(Any, runner))
    assert count() == 1  # a required variable isn't set: not run

    script.variables["label"].value = "set"
    assert script.is_configured
    code_runner.CodeRunner._setup_user_scripts(cast(Any, runner))
    assert count() == 2
    code_runner.CodeRunner._setup_user_scripts(cast(Any, runner))
    assert count() == 3  # fresh at every Run
