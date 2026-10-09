# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starting up and moving devices (audit 2).

- A user action plugin is checked in full before it is kept: a bad one is
  left out entirely (it stopped the program starting), one can't replace a
  built-in action, and a core plugin that fails still raises.
- The tray icon follows the platform Qt started on, options and all.
- Swap Devices leaves out and refuses the keyboard, the Logical Device, OSC
  and the Xbox pad.
- A condition moved onto a device that isn't connected forgets the old one.
- A mode that is its own parent, or a loop of parents, in a profile file is
  kept top-level instead of vanishing or stopping the load.
"""

from __future__ import annotations

import inspect
import json
import os
import pathlib
import subprocess
import sys
import textwrap
import uuid
from collections.abc import Iterator
from typing import Any
from xml.etree import ElementTree

sys.path.append(".")

import pytest

import dill
from gremlin import error, plugin_manager, shared_state, swap_devices
from gremlin.modules import ids
from gremlin.profile import ModeHierarchy, Profile
from gremlin.tree import TreeNode
from gremlin.types import InputType

_STICK = uuid.UUID("12121212-3434-5656-7878-909090909090")
_OTHER = uuid.UUID("abababab-cdcd-efef-0101-232323232323")


# --- Plugin manager ---------------------------------------------------------

_PLUGIN = """
from PySide6 import QtCore
from gremlin.types import InputType


class {cls}Model(QtCore.QObject):
    pass


class {cls}Data:
    name = {name!r}
    tag = {tag!r}
    model = {model}
    properties = ()
    input_types = {input_types}

    @classmethod
    def can_create(cls):
        return True


create = {cls}Data
"""


def _write_plugin(
    root: pathlib.Path,
    module: str,
    *,
    name: object = None,
    tag: object = None,
    model: str | None = None,
    input_types: str = "(InputType.JoystickButton,)",
) -> None:
    cls = "".join(part.title() for part in module.split("_"))
    folder = root / module
    folder.mkdir(parents=True)
    (folder / "__init__.py").write_text(
        _PLUGIN.format(
            cls=cls,
            name=module if name is None else name,
            tag=module if tag is None else tag,
            model=model or f"{cls}Model",
            input_types=input_types,
        ),
        encoding="utf-8",
    )


def _fresh_manager() -> plugin_manager.PluginManager:
    # Not the shared one other tests use: an empty manager to load into.
    manager = object.__new__(plugin_manager.PluginManager)
    manager._plugins = {}
    manager._type_to_action_map = {}
    manager._name_to_type_map = {}
    manager._tag_to_type_map = {}
    manager._parameter_requirements = {}
    return manager


@pytest.fixture
def registered(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Records QML registrations instead of making them."""
    names: list[str] = []

    def register(model: object, uri: str, major: int, minor: int, name: str) -> int:
        if not isinstance(model, type):
            raise TypeError("not a class")
        names.append(name)
        return len(names)

    monkeypatch.setattr(plugin_manager.QtQml, "qmlRegisterType", register)
    monkeypatch.setattr(sys, "path", list(sys.path))
    return names


@pytest.mark.parametrize(
    "fields",
    [
        {"input_types": "('axis',)"},
        {"input_types": "(InputType.Mouse,)"},
        {"input_types": "None"},
        {"tag": ""},
        {"name": 5},
        {"model": "None"},
    ],
    ids=[
        "text-type",
        "other-type",
        "no-types",
        "empty-tag",
        "name-not-text",
        "no-model",
    ],
)
def test_a_bad_user_plugin_is_left_out_entirely(
    tmp_path: pathlib.Path, registered: list[str], fields: dict[str, Any]
) -> None:
    suffix = uuid.uuid4().hex[:8]
    good, bad = f"audit2_good_{suffix}", f"audit2_bad_{suffix}"
    _write_plugin(tmp_path, good)
    _write_plugin(tmp_path, bad, **fields)
    manager = _fresh_manager()
    manager._discover_plugins(tmp_path, False)

    assert list(manager._plugins) == [good]
    assert registered == [f"{good.title().replace('_', '')}Model"]
    # The lookup tables build (a half-kept plugin stopped the start).
    manager._create_type_action_map()
    manager._create_action_name_map()
    assert set(manager.tag_map) == {good}


def test_a_user_plugin_cant_replace_a_built_in_action(
    tmp_path: pathlib.Path, registered: list[str]
) -> None:
    suffix = uuid.uuid4().hex[:8]
    manager = _fresh_manager()
    core = type(
        "CoreData", (), {"name": "Macro", "tag": "macro", "model": type("M", (), {})}
    )
    manager._plugins["macro"] = core  # type: ignore[assignment]
    _write_plugin(tmp_path, f"audit2_same_tag_{suffix}", tag="macro")
    _write_plugin(tmp_path, f"audit2_same_name_{suffix}", name="Macro")
    _write_plugin(tmp_path, f"audit2_same_model_{suffix}", model="type('M', (), {})")
    manager._discover_plugins(tmp_path, False)

    assert manager._plugins == {"macro": core}
    assert registered == []


def test_a_plugin_whose_qml_type_fails_is_not_kept(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_args: object) -> int:
        raise RuntimeError("QML said no")

    monkeypatch.setattr(plugin_manager.QtQml, "qmlRegisterType", refuse)
    monkeypatch.setattr(sys, "path", list(sys.path))
    _write_plugin(tmp_path, f"audit2_no_qml_{uuid.uuid4().hex[:8]}")
    manager = _fresh_manager()
    manager._discover_plugins(tmp_path, False)
    assert manager._plugins == {}


def test_a_bad_core_plugin_still_raises(
    tmp_path: pathlib.Path, registered: list[str]
) -> None:
    package = f"audit2_core_{uuid.uuid4().hex[:8]}"
    (tmp_path / package).mkdir()
    (tmp_path / package / "__init__.py").write_text("", encoding="utf-8")
    _write_plugin(tmp_path / package, "broken", input_types="('axis',)")
    sys.path.insert(0, str(tmp_path))
    manager = _fresh_manager()
    with pytest.raises(error.GremlinError):
        manager._discover_plugins(tmp_path / package, True)
    assert manager._plugins == {}


def test_the_lookup_table_uses_the_shared_input_types() -> None:
    manager = _fresh_manager()
    manager._create_type_action_map()
    assert tuple(manager.type_action_map) == plugin_manager.ACTION_INPUT_TYPES


# --- Tray icon --------------------------------------------------------------


def test_the_tray_icon_follows_the_platform_qt_started_on(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import joystick_gremlin

    # The tray follows the shared off-screen check, nothing of its own.
    source = inspect.getsource(joystick_gremlin.JoystickGremlinApp)
    assert "if not running_offscreen():" in source
    assert "QT_QPA_PLATFORM" not in source
    # Before Qt starts the check reads the platform part of the variable;
    # undone inside the test, Qt's teardown asks for the real instance.
    with monkeypatch.context() as patch:
        patch.setattr(
            joystick_gremlin.QtCore.QCoreApplication, "instance", lambda: None
        )
        patch.setattr(sys, "argv", ["joystick_gremlin.py"])
        for value, expected in (
            ("offscreen:configfile=x.json", True),
            ("offscreen", True),
            ("windows", False),
        ):
            patch.setenv("QT_QPA_PLATFORM", value)
            assert joystick_gremlin.running_offscreen() is expected, value

    # With options the variable isn't just "offscreen", the platform still is.
    (tmp_path / "screen.json").write_text(
        json.dumps(
            {
                "screens": [
                    {
                        "name": "s",
                        "x": 0,
                        "y": 0,
                        "width": 800,
                        "height": 600,
                        "logicalDpiX": 96,
                        "logicalDpiY": 96,
                        "dpr": 1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    code = textwrap.dedent("""
        from PySide6 import QtGui
        app = QtGui.QGuiApplication([])
        print("PLATFORM", app.platformName(), flush=True)
    """)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen:configfile=screen.json")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "PLATFORM offscreen" in result.stdout, result.stderr[-1500:]


# --- Swap Devices -----------------------------------------------------------


@pytest.fixture
def profile() -> Iterator[Profile]:
    # The bindings below include OSC Button 1: OSC's file must have it
    # (D-09-OSC-FILE), or the rule check flags PROFILE-OSC-MISSING.
    from gremlin.osc import OscDevice

    rows = OscDevice().rows
    saved = rows.to_dict()
    if rows.by_number(InputType.JoystickButton, 1) is None:
        rows.create(InputType.JoystickButton, "/swap/test", input_id=1)
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = None
    rows.load_dict(saved)


def test_swap_devices_lists_only_sticks(profile: Profile) -> None:
    profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default", True)
    profile.get_input_item(
        dill.UUID_Keyboard, InputType.Keyboard, (0x1E, False), "Default", True
    )
    for device in (ids.LOGICAL_DEVICE, ids.OSC, ids.XBOX):
        profile.get_input_item(device, InputType.JoystickButton, 1, "Default", True)
    listed = [d.device_uuid for d in swap_devices.get_profile_devices(profile)]
    assert listed == [_STICK]


@pytest.mark.parametrize(
    "device",
    [ids.KEYBOARD, ids.LOGICAL_DEVICE, ids.OSC, ids.XBOX],
    ids=["keyboard", "logical", "osc", "xbox"],
)
def test_swap_devices_refuses_what_isnt_a_stick(
    profile: Profile, device: uuid.UUID
) -> None:
    item = profile.get_input_item(device, InputType.JoystickButton, 1, "Default", True)
    for source, target in ((device, _STICK), (_STICK, device)):
        with pytest.raises(error.GremlinError):
            swap_devices.swap_devices(profile, source, target)
    assert item is not None and item.device_id == device
    assert _STICK not in profile.inputs


# --- Condition --------------------------------------------------------------


def test_a_condition_moved_to_an_unplugged_device_forgets_the_old_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.condition import condition as module

    class Stick:
        name = "Old Stick"

    class Sticks:
        def __getitem__(self, device: uuid.UUID) -> Stick:
            if device == _STICK:
                return Stick()
            raise error.GremlinError("not connected")

    monkeypatch.setattr(module, "Joystick", Sticks)
    state = module.JoystickCondition.State(_STICK, InputType.JoystickButton, 3)
    assert state.joystick is not None

    state.initialize_for_uuid(_OTHER)
    assert state.joystick is None
    assert state.device_uuid == _OTHER
    assert "Old Stick" not in state.display_name()
    with pytest.raises(error.GremlinError):
        state.get(None)  # type: ignore[arg-type]


# --- Mode tree from a file ----------------------------------------------------


def _modes(*entries: tuple[str, str | None]) -> ElementTree.Element:
    root = ElementTree.Element("profile")
    modes = ElementTree.SubElement(root, "modes")
    for name, parent in entries:
        mode = ElementTree.SubElement(modes, "mode")
        mode.text = name
        if parent is not None:
            mode.set("parent", parent)
    return root


def test_a_node_cant_be_its_own_parent() -> None:
    node = TreeNode("A")
    with pytest.raises(error.GremlinError):
        node.set_parent(node)
    assert node.parent is None and node.children == []


def test_a_mode_that_is_its_own_parent_is_kept_top_level() -> None:
    hierarchy = ModeHierarchy(Profile())
    hierarchy.from_xml(_modes(("Default", None), ("Self", "Self")))
    assert hierarchy.mode_names() == ["Default", "Self"]
    assert hierarchy.find_mode("Self").parent is hierarchy._hierarchy
    assert hierarchy.find_mode("Self").children == []


def test_a_loop_of_parents_loads_with_one_mode_top_level() -> None:
    hierarchy = ModeHierarchy(Profile())
    hierarchy.from_xml(_modes(("Default", None), ("A", "B"), ("B", "A")))
    assert hierarchy.mode_names() == ["A", "B", "Default"]
    top = {node.value for node in hierarchy._hierarchy.children}
    assert top == {"Default", "B"}
    assert hierarchy.find_mode("A").parent is hierarchy.find_mode("B")
    # Saved again, it no longer loops.
    saved = {m.text: m.get("parent") for m in hierarchy.to_xml()}
    assert saved == {"Default": None, "B": None, "A": "B"}


def test_setting_a_parent_under_itself_keeps_the_mode() -> None:
    hierarchy = ModeHierarchy(Profile())
    hierarchy.add_mode("Child")
    hierarchy.set_parent("Child", "Default")
    for parent in ("Default", "Child"):
        with pytest.raises(error.GremlinError):
            hierarchy.set_parent("Default", parent)
    assert hierarchy.mode_names() == ["Child", "Default"]
    assert hierarchy.find_mode("Default").parent is hierarchy._hierarchy
    assert hierarchy.find_mode("Child").parent is hierarchy.find_mode("Default")
    # A normal move still works, and to the top ("" is the root).
    hierarchy.add_mode("Other")
    hierarchy.set_parent("Child", "Other")
    assert hierarchy.find_mode("Child").parent is hierarchy.find_mode("Other")
    hierarchy.set_parent("Child", "")
    assert hierarchy.find_mode("Child").parent is hierarchy._hierarchy
