# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Action state for OSC Feedback (09 S157-S158, OX9F).

Smart Toggle and Tempo report their state to gremlin.action_state, read by
action id; a real CodeRunner runs the profile (output stand-ins, no vJoy).
"""

from __future__ import annotations

import pathlib
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import action_state, code_runner, run_scope, shared_state
from gremlin.base_classes import AbstractActionData
from gremlin.event_handler import Event, EventHandler
from gremlin.profile import Profile
from gremlin.types import InputType

_GUID = uuid.UUID("77777777-5555-2222-3333-444444444444")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[code_runner.CodeRunner]:
    """A CodeRunner whose drivers, devices, sound and network are stand-ins."""
    from gremlin.modules import output

    monkeypatch.setattr(output, "write_vjoy", lambda *a: True)
    monkeypatch.setattr(output, "release_vjoy_button", lambda *a: True)
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    shared_state.set_runtime_active(False)
    run_scope._reset_for_tests()


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return False


def _container(
    profile: Profile, name: str, button: int, mode: str = "Default"
) -> AbstractActionData:
    """A container action (with a Map to vJoy child) on a button."""
    item = profile.get_input_item(
        _GUID, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    root = item.add_item_binding().root_action
    library = profile.library
    container = library.create(name, InputType.JoystickButton)
    child = library.create("Map to vJoy", InputType.JoystickButton)
    child.vjoy_device_id = 1
    child.vjoy_input_id = button
    selector = "children" if name == "Smart Toggle" else "long"
    container.insert_action(child, selector)
    if name == "Tempo":
        short = library.create("Map to vJoy", InputType.JoystickButton)
        short.vjoy_device_id = 1
        short.vjoy_input_id = button + 10
        container.insert_action(short, "short")
    root.insert_action(container, "children")
    return container


def _press(button: int, pressed: bool) -> None:
    EventHandler().process_event(
        Event(InputType.JoystickButton, button, _GUID, "Default", is_pressed=pressed)
    )


def test_smart_toggle_reports_on_until_its_second_release(
    runner: code_runner.CodeRunner,
) -> None:
    profile = Profile()
    toggle = _container(profile, "Smart Toggle", 1)
    toggle.delay = 5.0  # a quick release toggles
    runner.start(profile, "Default")
    assert action_state.read(toggle.id) is False
    _press(1, True)
    assert action_state.read(toggle.id) is True
    _press(1, False)  # quick release: toggled on, stays on
    assert action_state.read(toggle.id) is True
    assert action_state.read_text(toggle.id) == "on"
    _press(1, True)
    assert action_state.read(toggle.id) is True
    _press(1, False)  # second release: off
    assert action_state.read(toggle.id) is False
    assert action_state.read_text(str(toggle.id)) == "off"


def test_tempo_reports_its_last_press_long_on_short_off(
    runner: code_runner.CodeRunner,
) -> None:
    profile = Profile()
    tempo = _container(profile, "Tempo", 2)
    tempo.threshold = 0.05
    runner.start(profile, "Default")
    assert action_state.read(tempo.id) is False
    assert action_state.read_text(tempo.id) == ""
    _press(2, True)
    assert _wait_for(lambda: action_state.read(tempo.id) is True)
    _press(2, False)
    assert action_state.read(tempo.id) is True  # last press was long
    assert action_state.read_text(tempo.id) == "long"
    _press(2, True)
    _press(2, False)  # short press
    assert action_state.read(tempo.id) is False
    assert action_state.read_text(tempo.id) == "short"


def test_on_if_any_instance_is_on(runner: code_runner.CodeRunner) -> None:
    profile = Profile()
    toggle = _container(profile, "Smart Toggle", 3)
    toggle.delay = 5.0
    # The same action on a second button (S158).
    item = profile.get_input_item(
        _GUID, InputType.JoystickButton, 4, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(toggle, "children")
    runner.start(profile, "Default")
    assert action_state.read(toggle.id) is False
    _press(4, True)
    assert action_state.read(toggle.id) is True
    _press(4, False)
    _press(4, True)
    _press(4, False)
    assert action_state.read(toggle.id) is False


def test_missing_action_reads_none_and_stop_clears(
    runner: code_runner.CodeRunner,
) -> None:
    profile = Profile()
    toggle = _container(profile, "Smart Toggle", 5)
    assert action_state.read(uuid.uuid4()) is None
    assert action_state.read("not a uuid") is None
    runner.start(profile, "Default")
    assert action_state.read(toggle.id) is False
    assert action_state.read(uuid.uuid4()) is None
    runner.stop()
    assert action_state.read(toggle.id) is None


def test_run_start_drops_the_last_runs_functors(
    runner: code_runner.CodeRunner,
) -> None:
    first = Profile()
    toggle = _container(first, "Smart Toggle", 6)
    runner.start(first, "Default")
    assert action_state.read(toggle.id) is False
    runner.start(Profile(), "Default")  # Run again with another profile
    assert action_state.read(toggle.id) is None


def test_paused_state(runner: code_runner.CodeRunner) -> None:
    assert action_state.paused_state() is None  # not running
    runner.start(Profile(), "Default")
    assert action_state.paused_state() is False
    EventHandler().pause()
    try:
        assert action_state.paused_state() is True
    finally:
        EventHandler().resume()
    assert action_state.paused_state() is False


def test_stateful_actions_lists_every_toggle_and_tempo() -> None:
    profile = Profile()
    toggle = _container(profile, "Smart Toggle", 7)
    tempo = _container(profile, "Tempo", 8, mode="Default")
    found = action_state.stateful_actions(profile)
    ids = [aid for aid, _ in found]
    assert toggle.id in ids and tempo.id in ids
    labels = dict(found)
    assert labels[toggle.id].endswith(" · Default · Smart Toggle")
    assert labels[tempo.id].endswith(" · Default · Tempo")


def test_no_action_plugin_imports_osc() -> None:
    """Actions report state; OSC reads it (S157). Never the other way."""
    import ast

    # Send OSC is an OSC output action by design; every other action must
    # not know about OSC.
    root = pathlib.Path(__file__).resolve().parents[2] / "action_plugins"
    files = [p for p in root.rglob("*.py") if p.parent.name != "send_osc"]
    assert len(files) > 20, root
    bad = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [
                    f"{node.module}.{a.name}" for a in node.names
                ]
            if any(part.startswith("osc") for n in names for part in n.split(".")):
                bad.append(f"{path}:{node.lineno}")
    assert bad == []
