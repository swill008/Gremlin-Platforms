# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catch-up batch 2, agent B4: profiles, modes and scripts (spec page 04).

Each test names the GL id it covers and fails on the code before the fix.
"""

from __future__ import annotations

import sys
import types
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import (
    config,
    device_initialization,
    event_handler,
    mode_manager,
    plugin_manager,
    shared_state,
    swap_devices,
)
from gremlin.error import GremlinError
from gremlin.logical_device import LogicalDevice
from gremlin.osc import OscDevice
from gremlin.profile import Profile, ScriptManager
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import backend
from gremlin.user_script import Script

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")
_OTHER = uuid.UUID("11111111-2222-3333-4444-555555555555")
_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_AUTOLOAD = backend.Backend.klass._active_process_changed_cb


def _release(obj: QtCore.QObject) -> None:
    """Unhooks obj (and its children) from the program-wide signals, so a
    later test's signal doesn't reach it."""
    import warnings

    owners = (
        signal,
        event_handler.EventListener(),
        event_handler.EventHandler(),
        mode_manager.ModeManager(),
    )
    signals = [
        getattr(owner, name)
        for owner in owners
        for name in dir(type(owner))
        if isinstance(getattr(type(owner), name, None), QtCore.Signal)
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
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


@pytest.fixture
def profile() -> Iterator[Profile]:
    before = shared_state.current_profile
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = before
    LogicalDevice().reset()


def _bind(
    profile: Profile, mode: str, hw: int = 1, note: str = "note"
) -> Any:  # noqa: ANN401
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, hw, mode, create_if_missing=True
    )
    assert item is not None
    desc = plugin_manager.PluginManager().create_instance(
        "Description", InputType.JoystickButton
    )
    desc.description = note
    item.add_item_binding().root_action.insert_action(desc, "children")
    return item


def _notes(profile: Profile, mode: str, hw: int = 1) -> list[str]:
    item = profile.get_input_item(_STICK, InputType.JoystickButton, hw, mode)
    if item is None:
        return []
    return [
        a.description
        for binding in item.action_sequences
        for a in binding.root_action.get_actions()[0]
    ]


# --- GL-027: Delete Mode can be undone --------------------------------------


def test_undo_delete_mode_brings_back_the_mode_and_its_bindings(
    profile: Profile,
) -> None:
    from gremlin.ui.profile import ModeHierarchyModel

    modes = profile.modes
    for name in ("Parent", "Mid", "Kid"):
        modes.add_mode(name)
    modes.set_parent("Mid", "Parent")
    modes.set_parent("Kid", "Mid")
    _bind(profile, "Mid", note="kept")
    profile.settings.startup_mode = "Mid"
    model = ModeHierarchyModel()
    try:
        model.deleteMode("Mid")
        assert not modes.mode_exists("Mid")
        assert modes.find_mode("Kid").parent.value == "Parent"
        assert profile.settings.startup_mode == "Use Heuristic"
        assert model.canUndoDelete and model.undoDeleteName == "Mid"

        assert model.undoDelete() == ""
        assert modes.find_mode("Mid").parent.value == "Parent"
        assert modes.find_mode("Kid").parent.value == "Mid"
        assert _notes(profile, "Mid") == ["kept"]
        assert profile.settings.startup_mode == "Mid"
        assert not model.canUndoDelete
    finally:
        model.deleteLater()


def test_undo_delete_mode_refuses_a_name_taken_since(profile: Profile) -> None:
    from gremlin.ui.profile import ModeHierarchyModel

    profile.modes.add_mode("Flight")
    model = ModeHierarchyModel()
    try:
        model.deleteMode("Flight")
        model.newMode("FLIGHT")
        assert model.undoDelete() != ""
        assert profile.modes.mode_names() == ["Default", "FLIGHT"]
    finally:
        model.deleteLater()


# --- GL-028, GL-151, GL-039: what a damaged mode list loads as --------------


def _saved(profile: Profile, path: Path) -> str:
    profile.to_xml(path)
    return path.read_text(encoding="utf-8-sig")


def _reload(path: Path, text: str) -> Profile:
    path.write_text(text, encoding="utf-8-sig")
    back = Profile()
    back.from_xml(path)
    return back


def test_bindings_in_an_unlisted_mode_are_named_at_load(
    profile: Profile, tmp_path: Path
) -> None:
    profile.modes.add_mode("Ghost")
    _bind(profile, "Ghost")
    path = tmp_path / "ghost.xml"
    # Out of the mode list (the last one), not out of the input.
    head, tail = _saved(profile, path).rsplit("<mode>Ghost</mode>", 1)
    back = _reload(path, head + tail)
    assert any("Ghost (1 input)" in w for w in back.load_warnings)


def test_a_profile_without_modes_gets_default(profile: Profile, tmp_path: Path) -> None:
    path = tmp_path / "none.xml"
    text = _saved(profile, path).replace("<mode>Default</mode>", "")
    back = _reload(path, text)
    assert back.modes.mode_names() == ["Default"]
    assert any("no modes" in w for w in back.load_warnings)


def test_a_mode_listed_twice_is_warned_about(profile: Profile, tmp_path: Path) -> None:
    path = tmp_path / "twice.xml"
    text = _saved(profile, path).replace(
        "<mode>Default</mode>", "<mode>Default</mode><mode>Default</mode>"
    )
    back = _reload(path, text)
    assert back.modes.mode_names() == ["Default"]
    assert any("more than once" in w for w in back.load_warnings)


def test_an_unknown_startup_mode_loads_as_use_heuristic(
    profile: Profile, tmp_path: Path
) -> None:
    path = tmp_path / "odd.xml"
    text = _saved(profile, path).replace(
        "<startup-mode>Use Heuristic</startup-mode>",
        "<startup-mode>Gone</startup-mode>",
    )
    back = _reload(path, text)
    assert back.settings.startup_mode == "Use Heuristic"


# --- GL-074: the Logical Device and OSC rows belong to the profile ----------


def test_a_new_profile_object_keeps_another_profiles_rows(profile: Profile) -> None:
    LogicalDevice().create(InputType.JoystickButton, label="Fire")
    OscDevice().create(InputType.JoystickButton, label="/osc/fire")
    other = Profile()  # a throwaway one used to wipe them
    assert not LogicalDevice().exists("Fire")  # the new one is shown
    text = profile._xml_text()
    assert "Fire" in text and "/osc/fire" in text
    assert "Fire" not in other._xml_text()
    profile.bind_devices()
    assert LogicalDevice().exists("Fire")
    assert OscDevice().find_address("/osc/fire") is not None


# --- GL-119: the vJoy Behavior switch never touches a Run -------------------


def test_vjoy_behavior_switch_sends_no_device_change(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import output
    from gremlin.ui.profile import VJoyInputOrOutputModel

    monkeypatch.setattr(output, "vjoy_axes", lambda: {1: []})
    listener = event_handler.EventListener()
    changes: list[int] = []
    notes: list[str] = []

    def changed() -> None:
        changes.append(1)

    def noted(title: str, text: str) -> None:
        notes.append(text)

    listener.device_change_event.connect(changed)
    signal.showNotification.connect(noted)
    was_active = listener.gremlin_active
    model = VJoyInputOrOutputModel()
    try:
        listener.gremlin_active = True
        role = QtCore.Qt.ItemDataRole.UserRole + 2
        assert model.setData(model.index(0, 0), True, role)
        assert profile.settings.vjoy_as_input == {1: True}
        assert changes == []
        assert any("next Run" in text for text in notes)
    finally:
        listener.gremlin_active = was_active
        listener.device_change_event.disconnect(changed)
        signal.showNotification.disconnect(noted)
        signal.profileChanged.disconnect(model._reset)
        model.deleteLater()


# --- GL-129, GL-130, GL-150, GL-157: Backend ---------------------------------


def test_auto_load_hears_the_program_in_front_at_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import process_monitor

    heard: list[str] = []
    # The monitor runs only while auto-load is on (D-02-Q19).
    value = config.Configuration.value

    def auto_load_on(self: Any, *key: str) -> Any:  # noqa: ANN401
        if key == ("profile", "automation", "enable-auto-loading"):
            return True
        return value(self, *key)

    monkeypatch.setattr(config.Configuration, "value", auto_load_on)
    monkeypatch.setattr(
        process_monitor.ProcessMonitor,
        "start",
        lambda self: self.process_changed.emit("C:/x/game.exe"),
    )
    monkeypatch.setattr(
        backend.Backend.klass,
        "_active_process_changed_cb",
        lambda self, path: heard.append(path),
    )
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = shared_state.current_profile
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    be = backend.Backend.klass(cast(Any, None))
    try:
        assert heard == ["C:/x/game.exe"]
    finally:
        _release(be)
        shared_state.current_profile = before
        mm._mode_stack = stack
        be.deleteLater()


def _fake_backend(settings: dict, unsaved: bool, calls: list) -> Any:  # noqa: ANN401
    return types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *key: settings[key]),
        profile=types.SimpleNamespace(
            fpath="open.xml", has_unsaved_changes=lambda: unsaved
        ),
        gremlinActive=True,
        _autoload_held=None,
        activate_gremlin=lambda on: calls.append(("active", on)),
        loadProfile=lambda path: calls.append(("load", path)),
    )


def test_focusing_the_program_itself_keeps_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: None)
    calls: list = []
    settings = {
        ("profile", "automation", "enable-auto-loading"): True,
        ("profile", "automation", "remain-active-on-focus-loss"): False,
    }
    _AUTOLOAD(_fake_backend(settings, False, calls), sys.executable)
    assert calls == []
    _AUTOLOAD(_fake_backend(settings, False, calls), "C:/x/game.exe")
    assert calls == [("active", False)]


@pytest.mark.parametrize("keep_running", [False, True])
def test_auto_load_held_by_unsaved_edits_stops_the_open_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keep_running: bool
) -> None:
    there = tmp_path / "game.xml"
    there.write_text("<profile/>", encoding="utf-8")
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: str(there))
    calls: list = []
    settings = {
        ("profile", "automation", "enable-auto-loading"): True,
        ("profile", "automation", "remain-active-on-focus-loss"): keep_running,
    }
    _AUTOLOAD(_fake_backend(settings, True, calls), "C:/x/game.exe")
    assert calls == ([] if keep_running else [("active", False)])


def test_a_missing_recent_profile_offers_forget_it(tmp_path: Path) -> None:
    failed: list[tuple[str, str]] = []
    recorded: list[Path] = []
    errors: list[str] = []
    fake = types.SimpleNamespace(
        recentProfileFailed=types.SimpleNamespace(
            emit=lambda path, why: failed.append((path, why))
        ),
        profileChanged=types.SimpleNamespace(emit=lambda: None),
        _record_profile_use=recorded.append,
        _load_problem="",
        profile=types.SimpleNamespace(fpath=Path("open.xml")),
    )
    fake._load_profile = lambda path, report=True: backend.Backend.klass._load_profile(
        fake, path, report
    )
    gone = tmp_path / "gone.xml"
    orig = backend.display_error
    backend.display_error = lambda *a, **k: errors.append(str(a))
    try:
        backend.Backend.klass.loadRecentProfile(fake, str(gone))
    finally:
        backend.display_error = orig
    assert failed == [(str(gone), "The file isn't there any more.")]
    assert errors == [] and recorded == []
    assert fake.profile.fpath == Path("open.xml")  # the open profile stays


# --- GL-149, GL-152: the last mode --------------------------------------------


@pytest.fixture
def last_modes(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    """The last-mode store in memory: the settings file is not touched."""
    stored: dict = {}
    real = config.Configuration()
    key_of = mode_manager._LAST_KEY

    def value(*key: str) -> Any:  # noqa: ANN401
        return dict(stored) if key == key_of else real.value(*key)

    def put(*args: Any) -> None:  # noqa: ANN401
        if args[:-1] == key_of:
            stored.update(args[-1])

    fake = types.SimpleNamespace(value=value, set=put)
    monkeypatch.setattr(mode_manager, "Configuration", lambda: fake)
    from gremlin import deferred_write

    monkeypatch.setattr(deferred_write, "schedule", lambda *a, **k: None)
    mode_manager._pending_last.clear()
    yield stored
    mode_manager._pending_last.clear()


class _Manager:
    def __init__(self, name: str) -> None:
        self._mode_stack = [mode_manager.Mode(name, None)]


def test_a_toolbar_pick_while_stopped_is_not_the_last_mode(
    profile: Profile, last_modes: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile.fpath = tmp_path / "flight.xml"
    monkeypatch.setattr(mode_manager, "_profile_running", lambda: False)
    mode_manager.ModeManager.klass._store_last_mode(cast(Any, _Manager("Picked")))
    assert mode_manager._stored_last_modes() == {}


def test_the_last_mode_is_found_by_another_spelling(
    profile: Profile, last_modes: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "Flight").mkdir()
    profile.fpath = tmp_path / "Flight" / "Flight.xml"
    profile.modes.add_mode("Zulu")
    monkeypatch.setattr(mode_manager, "_profile_running", lambda: True)
    mode_manager.ModeManager.klass._store_last_mode(cast(Any, _Manager("Zulu")))
    mode_manager.flush_last_modes()
    other = Profile()
    other.modes.add_mode("Zulu")
    other.settings.startup_mode = "Last Active"
    spelled = str(tmp_path).upper().replace("\\", "/")
    other.fpath = Path(spelled + "/flight/./FLIGHT.xml")
    assert mode_manager.resolve_start_mode(other) == "Zulu"


# --- GL-153: the unsaved check doesn't change the profile --------------------


def test_plugging_in_a_used_stick_is_not_an_unsaved_change(
    profile: Profile, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind(profile, "Default")
    monkeypatch.setattr(
        device_initialization,
        "device_for_uuid",
        lambda guid: (_ for _ in ()).throw(KeyError(guid)),
    )
    profile.mark_clean()
    # The stick is plugged in now.
    monkeypatch.setattr(
        device_initialization,
        "device_for_uuid",
        lambda guid: types.SimpleNamespace(name="Plugged Stick"),
    )
    assert not profile.has_unsaved_changes()
    assert profile.device_database.devices == {}
    path = tmp_path / "saved.xml"
    profile.to_xml(path)  # a save fills in the names
    assert "Plugged Stick" in path.read_text(encoding="utf-8-sig")


# --- GL-154: the mode name rules live in the mode tree -----------------------


def test_the_mode_tree_refuses_blank_and_look_alike_names(profile: Profile) -> None:
    modes = profile.modes
    assert not modes.mode_exists("")
    with pytest.raises(GremlinError):
        modes.find_mode("")
    for bad in ("", "   "):
        with pytest.raises(GremlinError):
            modes.add_mode(bad)
    modes.add_mode("Test Mode")
    with pytest.raises(GremlinError):
        modes.add_mode("test   MODE")
    modes.add_mode("Other")
    with pytest.raises(GremlinError):
        modes.rename_mode("Other", "TEST MODE")
    with pytest.raises(GremlinError):
        modes.rename_mode("Other", " ")
    modes.rename_mode("Test Mode", "TEST MODE")  # its own capitals may change
    modes.set_parent("Other", "TEST MODE")
    modes.set_parent("Other", "")  # no parent: top level
    assert modes.find_mode("Other").parent.value == ""


# --- GL-155: a removed script's settings go -----------------------------------


def test_a_removed_script_leaves_no_settings_behind(tmp_path: Path) -> None:
    path = tmp_path / "script.py"
    path.write_text(
        "import gremlin.user_script as us\n"
        "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n",
        encoding="utf-8",
    )
    manager = ScriptManager(Profile())
    manager.add_script(path)
    script = manager.scripts[0]
    assert Script.variable_registry.get(script.id, "speed") is not None
    manager.remove_script(script.path, script.name)
    assert Script.variable_registry.get(script.id, "speed") is None


# --- GL-156: vJoy Initial Values stay in -1..1 --------------------------------


def test_initial_values_set_in_the_ui_are_clamped(profile: Profile) -> None:
    settings = profile.settings
    settings.set_initial_vjoy_axis_value(1, 1, 5.0)
    settings.set_initial_vjoy_axis_value(1, 2, -3.0)
    assert settings.get_initial_vjoy_axis_value(1, 1) == 1.0
    assert settings.get_initial_vjoy_axis_value(1, 2) == -1.0


# --- GL-158: Swap Devices refuses the same device -----------------------------


def test_swap_devices_refuses_the_same_device(profile: Profile) -> None:
    from gremlin.ui.tools import Tools

    item = _bind(profile, "Default")
    with pytest.raises(swap_devices.SameDevice):
        swap_devices.swap_devices(profile, _STICK, _STICK)
    tools = Tools()
    try:
        text = tools.swapDevices(str(_STICK), str(_STICK))
    finally:
        tools.deleteLater()
    assert "same device" in text
    assert item.device_id == _STICK and profile.inputs[_STICK] == [item]


def test_swap_moves_inputs_through_the_profile(profile: Profile) -> None:
    item = _bind(profile, "Default")
    assert profile.swap_device_inputs(_STICK, _OTHER) == 1
    assert item.device_id == _OTHER and profile.inputs[_OTHER] == [item]
    assert profile.inputs[_STICK] == []


# --- GL-159: Script rename refreshes only rows that exist ---------------------


def test_script_rename_refreshes_rows_inside_the_list(tmp_path: Path) -> None:
    from gremlin.ui.script import ScriptListModel

    path = tmp_path / "script.py"
    path.write_text("x = 1\n", encoding="utf-8")
    manager = ScriptManager(Profile())
    manager.add_script(path)
    manager.add_script(path)
    model = ScriptListModel(manager)
    rows: list[tuple[int, int]] = []
    model.dataChanged.connect(
        lambda top, bottom, roles=None: rows.append((top.row(), bottom.row()))
    )
    try:
        script = manager.scripts[0]
        model.renameScript(str(script.path), script.name, "Renamed")
        assert rows == [(0, model.rowCount() - 1)]
    finally:
        model.deleteLater()


# --- GL-171 (lead request): binding edits refuse while running ---------------


def test_binding_edits_refuse_while_running(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import binding_catalog
    from gremlin.ui.profile import InputItemModel

    item = _bind(profile, "Default")
    model = InputItemModel(item, 0)
    try:
        monkeypatch.setattr(binding_catalog, "editing_locked", lambda: True)
        model.newActionSequence()
        assert len(item.action_sequences) == 1
        monkeypatch.setattr(binding_catalog, "editing_locked", lambda: False)
        model.newActionSequence()
        assert len(item.action_sequences) == 2
    finally:
        model.deleteLater()


# --- Device names through the profile (B7 request) ----------------------------


def test_remember_device_is_saved_and_rolled_back(profile: Profile) -> None:
    profile.remember_device(_STICK, "Pack Stick")
    assert profile.device_database.devices[_STICK].name == "Pack Stick"
    with pytest.raises(RuntimeError), profile.library.change():
        profile.remember_device(_OTHER, "Failed Stick")
        raise RuntimeError("import failed")
    assert _OTHER not in profile.device_database.devices
    assert "Pack Stick" in profile._xml_text()
