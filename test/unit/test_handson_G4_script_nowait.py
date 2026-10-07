# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 Q13, S87 (D-04-Q13-NOWAIT): loading a profile or adding a script does
not wait for the script's top-level code. Load and add finish at once; the
code keeps its time limit on its worker, and a script that doesn't finish is
marked failed with its message when the limit passes (on the main thread,
which keeps running meanwhile). The Scripts page shows a script as starting,
then its settings. Run still waits for a script that is starting
(D-04-Q13-RUNLIMIT).

The old code waited on the main thread for the whole limit (user_script.py
_run_top_level, done.wait)."""

from __future__ import annotations

import builtins
import pathlib
import sys
import threading
import time
import types
from collections.abc import Callable, Iterator
from typing import Any, cast

import pytest
from PySide6 import QtCore

from gremlin import code_runner, user_script
from gremlin.profile import Profile, ScriptManager
from gremlin.ui.script import ScriptListModel

LIMIT = 1.0
TIMEOUT = f"Its top-level code did not finish within {LIMIT:g} s (it may loop or wait)"

GOOD = (
    "import gremlin.user_script as us\n"
    "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n"
)
# Waits for the test's gate (released at the end of each test in any case).
LOOPS = (
    "import builtins\n"
    "import gremlin.user_script as us\n"
    "builtins._g4_gate.wait(30)\n"
    "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n"
)


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> Iterator[threading.Event]:

    event = threading.Event()
    builtins._g4_gate = event  # type: ignore[attr-defined]
    monkeypatch.setattr(user_script, "TOP_LEVEL_TIME_LIMIT", LIMIT)
    yield event
    event.set()
    del builtins._g4_gate  # type: ignore[attr-defined]


def _app() -> QtCore.QCoreApplication:
    app = QtCore.QCoreApplication.instance()
    assert app is not None
    return app


def _process_until(done: Callable[[], bool], limit: float = 5.0) -> None:
    deadline = time.monotonic() + limit
    while not done():
        if time.monotonic() > deadline:
            raise TimeoutError("waited too long")
        _app().processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


class _Ticks:
    """A main-thread timer: it fires only while the main thread runs."""

    def __init__(self) -> None:
        self.count = 0
        self.timer = QtCore.QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _tick(self) -> None:
        self.count += 1

    def stop(self) -> None:
        self.timer.stop()


def _profile_with(
    tmp_path: pathlib.Path, speed: int
) -> tuple[pathlib.Path, pathlib.Path]:
    """A saved profile with one script whose speed is set."""
    script_path = tmp_path / "throttle.py"
    script_path.write_text(GOOD, encoding="utf-8")
    profile = Profile()
    profile.scripts.add_script(script_path)
    profile.scripts.scripts[0].variables["speed"].value = speed
    path = tmp_path / "profile.xml"
    profile.to_xml(path)
    return path, script_path


def test_adding_a_looping_script_does_not_wait(
    tmp_path: pathlib.Path, gate: threading.Event, qapp: QtCore.QCoreApplication
) -> None:
    path = tmp_path / "loops.py"
    path.write_text(LOOPS, encoding="utf-8")
    manager = ScriptManager(Profile())
    started = time.monotonic()
    manager.add_script(path)
    elapsed = time.monotonic() - started
    assert elapsed < LIMIT / 2, f"add waited {elapsed:.2f} s"

    script = manager.scripts[0]
    assert script.starting
    ticks = _Ticks()
    try:
        # Marked failed when the limit passes, on the main thread, which
        # kept running meanwhile.
        _process_until(lambda: not script.starting)
    finally:
        ticks.stop()
    assert ticks.count >= 10
    assert script.load_error == TIMEOUT
    assert script.variables == {}


def test_loading_a_profile_with_a_looping_script_does_not_wait(
    tmp_path: pathlib.Path, gate: threading.Event, qapp: QtCore.QCoreApplication
) -> None:
    profile_path, script_path = _profile_with(tmp_path, 7)
    script_path.write_text(LOOPS, encoding="utf-8")

    profile = Profile()
    started = time.monotonic()
    profile.from_xml(profile_path)
    elapsed = time.monotonic() - started
    assert elapsed < LIMIT / 2, f"load waited {elapsed:.2f} s"

    script = profile.scripts.scripts[0]
    assert script.starting
    # Saving while it starts keeps its settings as saved.
    assert "<value>7</value>" in profile._xml_text()
    ticks = _Ticks()
    try:
        _process_until(lambda: not script.starting)
    finally:
        ticks.stop()
    assert ticks.count >= 10
    assert script.load_error == TIMEOUT
    assert "<value>7</value>" in profile._xml_text()
    assert not profile.has_unsaved_changes()


def test_a_normal_script_shows_as_starting_then_its_settings(
    tmp_path: pathlib.Path, qapp: QtCore.QCoreApplication
) -> None:
    profile_path, _ = _profile_with(tmp_path, 7)
    profile = Profile()
    profile.from_xml(profile_path)
    model = ScriptListModel(profile.scripts)
    roles = {bytes(v).decode(): k for k, v in model.roleNames().items()}
    index = model.index(0, 0)
    changed: list[int] = []
    model.dataChanged.connect(lambda *_: changed.append(1))

    # Right after the load: shown as starting, no settings yet, no error.
    assert model.data(index, roles["starting"]) is True
    assert model.data(index, roles["loadError"]) == ""
    assert model.data(index, roles["variables"]) == []

    script = profile.scripts.scripts[0]
    _process_until(lambda: not script.starting)
    assert changed, "the Scripts page was not told the script started"
    assert model.data(index, roles["starting"]) is False
    assert model.data(index, roles["loadError"]) == ""
    variables = model.data(index, roles["variables"])
    assert [v.property("name") for v in variables] == ["speed"]
    assert script.variables["speed"].value == 7
    # Nothing changed by starting: the profile has nothing unsaved.
    assert not profile.has_unsaved_changes()


def test_run_waits_for_a_script_that_is_starting(
    tmp_path: pathlib.Path,
    gate: threading.Event,
    qapp: QtCore.QCoreApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    path = tmp_path / "slow.py"
    path.write_text(LOOPS, encoding="utf-8")
    manager = ScriptManager(Profile())
    manager.add_script(path)
    script = manager.scripts[0]
    assert script.starting
    monkeypatch.setattr(sys, "path", list(sys.path))
    runner = types.SimpleNamespace(
        _sys_path=None,
        _profile=types.SimpleNamespace(scripts=manager),
    )
    # The script's code finishes a little later, within the limit.
    releaser = threading.Timer(LIMIT / 4, gate.set)
    releaser.start()
    try:
        code_runner.CodeRunner._setup_user_scripts(cast(Any, runner))
    finally:
        releaser.cancel()
        gate.set()
        user_script.periodic_registry.clear()
    # Run waited for it (no event loop ran): started and run.
    assert not script.starting
    assert script.load_error == ""
    assert "speed" in script.variables


def test_a_script_removed_while_starting_leaves_no_settings_behind(
    tmp_path: pathlib.Path, gate: threading.Event, qapp: QtCore.QCoreApplication
) -> None:
    path = tmp_path / "slow.py"
    path.write_text(LOOPS, encoding="utf-8")
    manager = ScriptManager(Profile())
    manager.add_script(path)
    script = manager.scripts[0]
    manager.remove_script(script.path, script.name)
    gate.set()  # its code finishes after it was removed
    _process_until(
        lambda: (
            not any(t.name.endswith("script Instance 1") for t in threading.enumerate())
        )
    )
    for _ in range(5):
        _app().processEvents()
    assert user_script.Script.variable_registry.get(script.id, "speed") is None
