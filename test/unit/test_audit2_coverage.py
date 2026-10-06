# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Fixes from the code audits that had no test of their own.

- An axis button reads an event with no value as 0 (it compared with None).
- The Run flag is on while a profile runs and off after Stop.
- A script's folder goes on the import path once, however often Run starts.
- A failing action doesn't stop the release actions of that input.
- Load Profile waits over unsaved changes and skips a missing file.
- At quit: threads stop, settings are written, History is closed, then the
  activity lines it added are written, before the installer starts.
- Quit to install saves the pending update before the installer starts.
- Log files are written as UTF-8.
- Undo of a module file import binds the devices it unbound again.
- Output View numbers buttons and hats within their kind.
- Swap Devices moves script variables both ways.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import sys
import types
import uuid
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore, QtQml

from gremlin import code_runner, config, history, shared_state
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.types import AxisButtonDirection, InputType

_ROOT = Path(__file__).parents[2]
_GUID = uuid.UUID("55555555-6666-7777-8888-999999999999")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def no_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)


# --- runtime ----------------------------------------------------------------


def test_an_axis_event_with_no_value_counts_as_zero() -> None:
    button = code_runner.VirtualAxisButton(-1.0, 0.2, AxisButtonDirection.Above)

    def axis(value: float | None) -> Event:
        return Event(InputType.JoystickAxis, 1, _GUID, "Default", value=value)

    assert button(axis(0.5)) == []  # first value: outside the range
    # No value: 0, coming down from 0.5 (it compared 0.5 with None and failed).
    assert button(axis(None)) == [True]


def test_the_run_flag_is_on_only_while_a_profile_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = code_runner.CodeRunner()
    # The parts that reach drivers, devices, sound or the network.
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    for name in ("macro", "sendinput"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    listener = mock.MagicMock()
    # A stand-in for the class: called it gives the listener, and like the
    # real one it has .instance (the mode switch at start reads it).
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    monkeypatch.setattr(runner, "_refresh_axes", lambda: None)
    shared_state.set_runtime_active(False)
    try:
        runner.start(Profile(), "Default")
        assert runner.is_running()
        assert shared_state.runtime_active()
    finally:
        runner.stop()
    assert not shared_state.runtime_active()


def test_a_script_folder_goes_on_the_import_path_once(tmp_path: Path) -> None:
    folder = tmp_path / "ScriptFolder"  # capitals: normcase changes it
    folder.mkdir()
    script = folder / "audit_script.py"
    script.write_text("value = 1\n", encoding="utf-8")
    profile = Profile()
    profile.scripts.add_script(script)
    runner = code_runner.CodeRunner()
    runner._profile = profile
    saved = list(sys.path)
    want = os.path.normcase(os.path.abspath(folder))
    try:
        runner._setup_user_scripts()
        runner._setup_user_scripts()  # a second Run
        found = [p for p in sys.path if os.path.normcase(os.path.abspath(p)) == want]
        assert len(found) == 1
    finally:
        sys.path[:] = saved


def test_a_failing_action_still_runs_the_release_actions() -> None:
    from gremlin.event_handler import EventHandler
    from gremlin.event_helpers import ButtonReleaseActions

    handler = EventHandler()
    press = Event(InputType.JoystickButton, 78, _GUID, "Default", is_pressed=True)
    release = Event(InputType.JoystickButton, 78, _GUID, "Default", is_pressed=False)
    released: list[bool] = []

    def fails(_event: Event) -> None:
        raise RuntimeError("an action failed")

    releases = ButtonReleaseActions()
    releases.register_callback(lambda e: released.append(e.is_pressed), press)
    handler.add_callback(_GUID, "Default", release, fails)
    handler.process_callbacks = True
    try:
        handler.process_event(release)  # no error out of it
    finally:
        handler.clear()
        releases.reset()
    assert released == [False]


# --- Load Profile -------------------------------------------------------------


@pytest.fixture
def load_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[object, types.SimpleNamespace, list]]:
    from action_plugins.load_profile import LoadProfileFunctor
    from gremlin import plugin_manager
    from gremlin.signal import signal
    from gremlin.ui import backend

    calls: list = []
    fake = types.SimpleNamespace(
        profile=types.SimpleNamespace(has_unsaved_changes=lambda: False),
        loadProfile=lambda path: calls.append(("load", path)),
        activate_gremlin=lambda on: calls.append(("active", on)),
    )
    monkeypatch.setattr(backend, "Backend", lambda: fake)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    data = plugin_manager.PluginManager().create_instance(
        "Load Profile", InputType.JoystickButton
    )
    functor = LoadProfileFunctor(data)

    def noted(title: str, _text: str) -> None:
        calls.append(("note", title))

    signal.showNotification.connect(noted)
    yield functor, fake, calls
    signal.showNotification.disconnect(noted)


def _press(functor: object) -> None:
    from gremlin.base_classes import Value

    event = Event(InputType.JoystickButton, 1, _GUID, "Default", is_pressed=True)
    functor(event, Value(True), [])  # type: ignore[operator]


def test_load_profile_loads_and_restarts_the_run(
    load_profile: tuple[object, types.SimpleNamespace, list], tmp_path: Path
) -> None:
    functor, _fake, calls = load_profile
    target = tmp_path / "other.xml"
    target.write_text("<profile/>")
    functor.data.profile_filename = str(target)  # type: ignore[attr-defined]
    _press(functor)
    assert calls == [("load", str(target)), ("active", False), ("active", True)]


def test_load_profile_waits_over_unsaved_changes(
    load_profile: tuple[object, types.SimpleNamespace, list], tmp_path: Path
) -> None:
    functor, fake, calls = load_profile
    target = tmp_path / "other.xml"
    target.write_text("<profile/>")
    functor.data.profile_filename = str(target)  # type: ignore[attr-defined]
    fake.profile.has_unsaved_changes = lambda: True
    _press(functor)
    assert calls == [("note", "Load Profile Waited")]


def test_load_profile_skips_a_missing_file(
    load_profile: tuple[object, types.SimpleNamespace, list], tmp_path: Path
) -> None:
    functor, _fake, calls = load_profile
    functor.data.profile_filename = str(tmp_path / "gone.xml")  # type: ignore[attr-defined]
    _press(functor)
    assert calls == [("note", "Load Profile")]


# --- quit and update ----------------------------------------------------------


def _calls_in_order(function: ast.FunctionDef) -> list[str]:
    calls = [n for n in ast.walk(function) if isinstance(n, ast.Call)]
    calls.sort(key=lambda n: (n.lineno, n.col_offset))
    return [ast.unparse(n.func) for n in calls]


def test_quit_closes_history_between_the_two_writes() -> None:
    # main() is the whole program: its order is read from the source.
    tree = ast.parse((_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8"))
    main = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    names = _calls_in_order(main)
    after_exec = names[names.index("app.exec") :]
    wanted = [
        "gremlin.threads.shutdown",
        "gremlin.deferred_write.flush_all",
        "gremlin.history.close",
        "gremlin.deferred_write.flush_all",
        "update_model.start_pending_install",
    ]
    seen = [n for n in after_exec if n in wanted]
    assert seen == wanted
    assert "gremlin.history.flush" not in names


def test_quit_to_install_saves_the_pending_update_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_history: None
) -> None:
    from gremlin import updater
    from gremlin.ui import update_model

    settings = tmp_path / "configuration.json"
    monkeypatch.setattr(config, "_config_file_path", str(settings))
    monkeypatch.setattr(updater, "updates_dir", lambda: tmp_path)
    setup = tmp_path / "Gremlin-Platforms-R1-9.9.9-Setup.exe"
    setup.write_bytes(b"x")
    model = update_model.UpdateModel()
    # The scheduled save is a timer in the program: it never runs at quit.
    monkeypatch.setattr(model._config, "save", lambda *args: None)
    model._ready_path = setup
    model._release = types.SimpleNamespace(version="9.9.9")
    model.setInstallOnExit(True)
    on_disk: list[dict] = []

    def start(*_args: object) -> bool:
        on_disk.append(json.loads(settings.read_text(encoding="utf-8")))
        return True

    monkeypatch.setattr(QtCore.QProcess, "startDetached", start)
    try:
        assert model.start_pending_install() is True
        internal = on_disk[0]["global"]["internal"]
        assert internal["update-pending-version"]["value"] == "9.9.9"
        assert internal["update-pending-setup"]["value"] == str(setup)
    finally:
        model._config.set("global", "internal", "update-pending-version", "")
        model._config.set("global", "internal", "update-pending-setup", "")


@pytest.mark.parametrize("mode", ["rotate", "session"])
def test_log_files_are_utf8(tmp_path: Path, mode: str) -> None:
    import joystick_gremlin

    name = f"audit2-utf8-{mode}"
    path = tmp_path / f"{mode}.log"
    joystick_gremlin.configure_logger(
        {
            "name": name,
            "level": logging.INFO,
            "mode": mode,
            "logfile": str(path),
            "format": "%(message)s",
        }
    )
    logger = logging.getLogger(name)
    try:
        logger.info("Путь C:/Игры 日本語 é")
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
    assert "Путь C:/Игры 日本語 é" in path.read_text(encoding="utf-8")


# --- Module Setup import --------------------------------------------------------


def test_undo_of_a_module_import_binds_the_devices_again(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_history: None
) -> None:
    from gremlin import util
    from gremlin.ui import hardware_profile

    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(util, "modules_dir", lambda: modules)
    chosen = tmp_path / "picked" / "shared_keys.json"
    chosen.parent.mkdir()
    chosen.write_text(
        json.dumps(
            {"kind": "control.hardware", "device": "Keyboard", "claim": {"keys": [30]}}
        ),
        encoding="utf-8",
    )
    before = hardware_profile._binding_store()
    bound = {"name:stick_a": "shared_keys", "name:keyboard": "old_keys"}
    hardware_profile._write_bindings(bound)
    monkeypatch.setattr(hardware_profile, "_import_undo", None)
    try:
        note = hardware_profile.import_module_file("Keyboard", "", str(chosen))
        assert note.startswith("Imported into keyboard.json"), note
        assert (modules / "keyboard.json").is_file()
        # The import unbinds the chosen file's device and the keyboard.
        assert hardware_profile._binding_store() == {}
        assert hardware_profile.undo_last_import().startswith("Undone.")
        assert not (modules / "keyboard.json").exists()
        assert hardware_profile._binding_store() == bound
    finally:
        hardware_profile._write_bindings(before)


# --- Output View ------------------------------------------------------------------


def _rebuild_source() -> str:
    text = (_ROOT / "qml" / "OutputModuleView.qml").read_text(encoding="utf-8")
    found = re.search(r"\n    function rebuild\(\) \{\n.*?\n    \}\n", text, re.S)
    assert found, "rebuild() not found in OutputModuleView.qml"
    return found.group(0)


def test_output_view_numbers_buttons_and_hats_within_their_kind() -> None:
    # The page's own rebuild(), with no claimed list: every output is shown.
    engine = QtQml.QJSEngine()
    script = (
        """
        var shown = { "axis": [], "button": [], "hat": [] }
        function list(kind) {
            return { clear: function() {}, append: function(r) { shown[kind].push(r) } }
        }
        var axisModel = list("axis")
        var buttonModel = list("button")
        var hatModel = list("hat")
        var _claimed = { count: 0 }
        var kinds = ["axis", "axis", "button", "button", "button", "hat", "hat"]
        var _live = { kindAt: function(j) { return kinds[j] || "" } }
        function axisShort(hw, name) { return "Axis " + hw }
        function fillAxisPick() {}
        """
        + _rebuild_source()
        + "\nrebuild(); JSON.stringify(shown)"
    )
    result = engine.evaluate(script)
    assert not result.isError(), result.toString()
    shown = json.loads(result.toString())
    assert [(r["idx"], r["hw"], r["name"]) for r in shown["button"]] == [
        (2, 1, "1"),
        (3, 2, "2"),
        (4, 3, "3"),
    ]
    assert [(r["idx"], r["name"]) for r in shown["hat"]] == [(5, "Hat 1"), (6, "Hat 2")]
    assert [r["hw"] for r in shown["axis"]] == [1, 2]


# --- Swap Devices -----------------------------------------------------------------


def test_swap_devices_moves_script_variables_both_ways() -> None:
    from gremlin import swap_devices
    from gremlin.user_script import PhysicalInputVariable, Script

    a, b = uuid.uuid4(), uuid.uuid4()

    def variable(device: uuid.UUID) -> PhysicalInputVariable:
        var = PhysicalInputVariable("v", "", True, [InputType.JoystickButton])
        var.value = (device, InputType.JoystickButton, 1)
        return var

    on_a, on_b, also_b = variable(a), variable(b), variable(b)
    one, two = Script(), Script()
    one.variables = {"on_a": on_a, "on_b": on_b}
    two.variables = {"also_b": also_b}
    profile = Profile()
    profile.scripts.scripts.extend([one, two])
    swap_devices.swap_devices(profile, a, b)
    assert on_a.device_guid == b
    assert on_b.device_guid == a
    assert also_b.device_guid == a
