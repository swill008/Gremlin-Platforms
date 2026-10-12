# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Things repeated many times keep a bounded number of objects (audit
SHAKE-STRESS-02/03/04, AUD-LINT-09): button presses in one Run, opening and
closing Options and the Input Viewer, and reading a response curve's points."""

from __future__ import annotations

import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

sys.path.append(".")

import json
import os
import pathlib
import re
import uuid
from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest
from PySide6 import QtCore

from gremlin import event_handler, event_helpers, mode_manager
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.types import InputType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_GUID = uuid.UUID("77777777-5555-2222-3333-555555555555")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def release_actions() -> Iterator[Any]:
    bra = event_helpers.ButtonReleaseActions()
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(mode_manager, "_known_modes", lambda: set())  # any name
        bra.reset()
        yield bra
        bra.reset()
    mm._mode_stack = stack
    mm.mode_changed.emit(mm.current.name)


def _switch(name: str) -> None:
    """Changes the mode the way the program does."""
    mode_manager.ModeManager().switch_to(mode_manager.Mode(name, None))


def _button(mode: str, pressed: bool) -> Event:
    return Event(InputType.JoystickButton, 6, _GUID, mode, is_pressed=pressed)


def _map_to_vjoy_button(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list]:
    from action_plugins.map_to_vjoy import MapToVjoyData, MapToVjoyFunctor
    from gremlin.modules import output

    sent: list[tuple] = []
    monkeypatch.setattr(
        output, "write_vjoy", lambda *a: sent.append(("write",) + a) or True
    )
    monkeypatch.setattr(
        output, "release_vjoy_button", lambda *a: sent.append(("release",) + a) or True
    )
    data = MapToVjoyData(InputType.JoystickButton)
    data.vjoy_device_id = 1
    data.vjoy_input_id = 4
    return MapToVjoyFunctor(data), sent


def _pending(bra: Any) -> int:  # noqa: ANN401
    return sum(len(entries) for entries in bra._registry.values())


# --- SHAKE-STRESS-02: release entries in one Run -----------------------------


def test_presses_in_one_mode_keep_no_release_entries(
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    functor, sent = _map_to_vjoy_button(monkeypatch)
    _switch("Default")
    handler = event_handler.EventHandler()
    for _ in range(200):
        functor(_button("Default", True), Value(True))
        handler.process_event(_button("Default", True))
        functor(_button("Default", False), Value(False))
        handler.process_event(_button("Default", False))
    # Each press's entry is spent at its release; none pile up.
    assert _pending(release_actions) <= 1
    assert ("release", 1, 4) not in sent  # same mode: no doubled release


def test_a_release_after_a_mode_change_still_lets_go_once(
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    """06 S38 holds with the bounded registry."""
    functor, sent = _map_to_vjoy_button(monkeypatch)
    _switch("Default")
    handler = event_handler.EventHandler()
    for _ in range(20):  # earlier presses in the same mode
        functor(_button("Default", True), Value(True))
        functor(_button("Default", False), Value(False))
        handler.process_event(_button("Default", False))
    functor(_button("Default", True), Value(True))
    _switch("Flight")
    handler.process_event(_button("Flight", False))
    assert sent.count(("release", 1, 4)) == 1
    assert _pending(release_actions) == 0


# --- AUD-LINT-09: response curve points --------------------------------------


def _curve_model() -> Any:  # noqa: ANN401
    from action_plugins.response_curve import ResponseCurveData, ResponseCurveModel

    data = ResponseCurveData(InputType.JoystickAxis)
    return ResponseCurveModel(data, mock.MagicMock(), None, None, None)  # type: ignore[arg-type]


def test_reading_control_points_does_not_make_new_objects() -> None:
    from action_plugins.response_curve import ControlPoint

    model = _curve_model()
    for _ in range(100):
        points = model.controlPoints
        _ = model.deadzone
    children = model.findChildren(QtCore.QObject)
    assert len([c for c in children if isinstance(c, ControlPoint)]) == len(points)
    assert len(children) <= len(points) + 1  # the points and one Deadzone


def test_control_points_follow_the_curve() -> None:
    model = _curve_model()
    count = len(model.controlPoints)
    model.addControlPoint(0.25, 0.5)
    points = model.controlPoints
    assert len(points) == count + 1
    assert any(
        abs(p.center.x() - 0.25) < 1e-9 and abs(p.center.y() - 0.5) < 1e-9
        for p in points
    )
    index = [p.center.x() for p in points].index(0.25)
    model.setControlPoint(0.3, 0.1, index, False)  # a drop, not a drag
    assert any(abs(p.center.x() - 0.3) < 1e-9 for p in model.controlPoints)
    model.removeControlPoint(1)
    assert len(model.controlPoints) == count


# --- SHAKE-STRESS-03/04: windows opened and closed ---------------------------

_SCRIPT = r"""
import gc, json, os, sys, time
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtQml

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        QtCore.QCoreApplication.sendPostedEvents(
            None, QtCore.QEvent.Type.DeferredDelete)
        time.sleep(0.005)

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), code + ': ' + expr.error().toString()
    return value

NAMES = sys.argv[1].split(',')

import shiboken6

def counts():
    # Live objects only: PySide 6.11 keeps the Python wrapper of every
    # Python object QML made after QML deletes it (C++ gone, no holder in
    # Python, signals disconnected); those shells aren't ours to free.
    gc.collect()
    out = dict.fromkeys(NAMES, 0)
    for obj in gc.get_objects():
        name = type(obj).__name__
        if name in out and shiboken6.isValid(obj):
            out[name] += 1
    return out

def cycle(qml):
    run('Helpers.createComponent("%s")' % qml)
    pump(0.4)
    run('Helpers.windowOf("%s").close()' % qml)
    pump(0.3)

out = {}
for qml in sys.argv[2].split(','):
    for _ in range(2):
        cycle(qml)
    before = counts()
    for _ in range(6):
        cycle(qml)
    after = counts()
    out[qml] = {name: after[name] - before[name] for name in NAMES}
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)
"""

_NAMES = [
    "ConfigGroupModel", "ConfigEntryModel", "HighlightSpeedModel",
    "WindowPlacement", "PairLiveThrottle", "ModulePairAxisModel",
    "ModulePairButtonModel", "QTimer",
]


@pytest.fixture(scope="module")
def growth(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp_path = tmp_path_factory.mktemp("leaks")
    path = tmp_path / "leaks_app.py"
    path.write_text(_SCRIPT, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    result = proc_tree.run(
        [sys.executable, str(path), ",".join(_NAMES),
         "DialogOptions.qml,DialogInputViewer.qml"],
        cwd=_ROOT, env=env, text=True, timeout=240,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-4000:]
    out = json.loads(lines[0][len("RESULT "):])
    print(f"growth over 6 opens: {out}")
    return out


def test_options_opened_and_closed_keeps_no_models(growth: dict) -> None:
    grown = growth["DialogOptions.qml"]
    assert {name: n for name, n in grown.items() if n > 0} == {}


def test_input_viewer_opened_and_closed_keeps_no_objects(growth: dict) -> None:
    grown = growth["DialogInputViewer.qml"]
    assert {name: n for name, n in grown.items() if n > 0} == {}


# +-------------------------------------------------------------------------
# | Live cards made by tests

_OSC_CARDS = "test/unit/test_vjoy_viewer_lists_osc.py::"
_CARD_TESTS = [
    "test/unit/test_final_07.py::test_presses_come_only_from_the_input_module_feed",
    _OSC_CARDS + "test_the_lights_follow_the_input_and_the_output",
    _OSC_CARDS + "test_a_new_map_to_vjoy_is_polled",
]

_CARD_PLUGIN = """
import gc

import pytest
import shiboken6

KEPT = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    from gremlin.ui.pair_live import PairLiveThrottle

    gc.collect()
    alive = [
        obj for obj in gc.get_objects()
        if isinstance(obj, PairLiveThrottle) and shiboken6.isValid(obj)
    ]
    if alive:
        KEPT.append(item.nodeid)


def pytest_sessionfinish(session):
    print("CARDS KEPT " + repr(KEPT), flush=True)
"""


def test_no_live_card_outlives_its_test(tmp_path: pathlib.Path) -> None:
    """A test's PairLiveThrottle is deleted at its end: one left alive keeps
    answering bindings notices in later tests, where stand-in vJoy devices
    broke it (CI 38277644763, test_new_action_defaults)."""
    (tmp_path / "card_check.py").write_text(_CARD_PLUGIN, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONPATH=os.pathsep.join(
            p for p in (str(tmp_path), os.environ.get("PYTHONPATH")) if p
        ),
    )
    result = proc_tree.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
         "-p", "no:cacheprovider", "-p", "card_check", *_CARD_TESTS],
        cwd=_ROOT, env=env, text=True, timeout=240,
    )
    kept = re.search(r"CARDS KEPT (\[.*\])", result.stdout)
    assert kept, result.stdout[-3000:] + result.stderr[-3000:]
    assert kept.group(1) == "[]", result.stdout[-3000:]
    assert result.returncode == 0, result.stdout[-3000:]
