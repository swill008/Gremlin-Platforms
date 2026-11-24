# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Things repeated many times keep a bounded number of objects (audit
SHAKE-STRESS-02/03/04, AUD-LINT-09): button presses in one Run, opening and
closing Options and the Input Viewer, and reading a response curve's points.
Objects QML gets from ModelFactory leave no shells when their page or
window closes (claude/plans/memory-qml-factory.md, stage 1)."""

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

from gremlin import event_handler, mode_manager
from gremlin.types import Event, InputType

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
    """The event handler, emptied and back in its mode after (its pending
    table holds the presses waiting for their release, D-06-MODE-RELEASE)."""
    handler = event_handler.EventHandler()
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(mode_manager, "_known_modes", lambda: set())  # any name
        handler.clear()
        handler.resume()
        yield handler
        handler.clear()
    mm._mode_stack = stack
    mm.mode_changed.emit(mm.current.name)


def _switch(name: str) -> None:
    """Changes the mode the way the program does."""
    mode_manager.ModeManager().switch_to(mode_manager.Mode(name, None))


def _button(pressed: bool) -> Event:
    # No mode, as from the hardware: the handler reads the live one.
    return Event(InputType.JoystickButton, 6, _GUID, "", is_pressed=pressed)


def _map_to_vjoy_button(monkeypatch: pytest.MonkeyPatch) -> list:
    """A Map to vJoy button bound in Default (a real CallbackObject in the
    event handler); what reaches the output module."""
    from gremlin import code_runner
    from gremlin.modules import output
    from gremlin.profile import Profile

    sent: list[tuple] = []
    monkeypatch.setattr(
        output, "write_vjoy", lambda *a: sent.append(("write",) + a) or True
    )
    monkeypatch.setattr(
        output, "release_vjoy_button", lambda *a: sent.append(("release",) + a) or True
    )
    profile = Profile()
    item = profile.get_input_item(
        _GUID, InputType.JoystickButton, 6, "Default", create_if_missing=True
    )
    action = profile.library.create("Map to vJoy", InputType.JoystickButton)
    action.vjoy_device_id = 1
    action.vjoy_input_id = 4
    item.add_item_binding().root_action.insert_action(action, "children")
    event_handler.EventHandler().add_callback(
        _GUID,
        "Default",
        Event(InputType.JoystickButton, 6, _GUID, "Default"),
        code_runner.CallbackObject(item.action_sequences[0]),
    )
    return sent


def _pending(handler: Any) -> int:  # noqa: ANN401
    return sum(len(entries) for entries in handler._pending.values())


def _releases(sent: list[tuple]) -> int:
    return sent.count(("write", 1, "button", 4, False)) + sent.count(("release", 1, 4))


# --- SHAKE-STRESS-02: release entries in one Run -----------------------------


def test_presses_in_one_mode_keep_no_release_entries(
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    sent = _map_to_vjoy_button(monkeypatch)
    _switch("Default")
    for _ in range(200):
        release_actions.process_event(_button(True))
        release_actions.process_event(_button(False))
    # Each press's pending entry is spent at its release; none pile up.
    assert _pending(release_actions) == 0
    assert _releases(sent) == 200  # one release each, never doubled


def test_a_release_after_a_mode_change_still_lets_go_once(
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    """06 S38 holds with the bounded pending table."""
    sent = _map_to_vjoy_button(monkeypatch)
    _switch("Default")
    for _ in range(20):  # earlier presses in the same mode
        release_actions.process_event(_button(True))
        release_actions.process_event(_button(False))
    sent.clear()
    release_actions.process_event(_button(True))
    _switch("Flight")
    release_actions.process_event(_button(False))
    assert _releases(sent) == 1
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

from gremlin.ui import type_aliases as ta

FACTORY = [ta.QML_TYPES[n] for n in sys.argv[3].split(',') if n in ta.QML_TYPES]

def counts():
    # Live objects by name, and shells of the factory-made types: a shell
    # is a Python wrapper whose C++ object is gone but which PySide still
    # keeps reachable (its __dict__ and what that holds stay in memory);
    # PySide 6.11 keeps one for every object QML instantiates (PYSIDE-1407).
    gc.collect()
    out = dict.fromkeys(NAMES, 0)
    shells = 0
    for obj in gc.get_objects():
        cls = type(obj)
        if cls in FACTORY and not shiboken6.isValid(obj):
            shells += 1
        name = cls.__name__
        if name in out and shiboken6.isValid(obj):
            out[name] += 1
    out['_shells'] = shells
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
    out[qml]['_shells'] = after['_shells']
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)
"""

_NAMES = [
    "ConfigGroupModel", "ConfigEntryModel", "HighlightSpeedModel",
    "WindowPlacement", "PairLiveThrottle", "ModulePairAxisModel",
    "ModulePairButtonModel", "QTimer",
]


def _factory_made() -> list[str]:
    """The types QML makes only through ModelFactory (the guard's list)."""
    import importlib.util

    path = pathlib.Path(__file__).with_name("test_qml_factory_guard.py")
    spec = importlib.util.spec_from_file_location("_qml_factory_guard", path)
    assert spec is not None and spec.loader is not None
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    return guard.factory_made()


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
         "DialogOptions.qml,DialogInputViewer.qml", ",".join(_factory_made())],
        cwd=_ROOT, env=env, text=True, timeout=240,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-4000:]
    out = json.loads(lines[0][len("RESULT "):])
    print(f"growth over 6 opens: {out}")
    return out


def test_options_opened_and_closed_keeps_no_models(growth: dict) -> None:
    """No live model more, and no shell of a factory-made type."""
    grown = growth["DialogOptions.qml"]
    assert {name: n for name, n in grown.items() if n > 0} == {}


def test_input_viewer_opened_and_closed_keeps_no_objects(growth: dict) -> None:
    grown = growth["DialogInputViewer.qml"]
    assert {name: n for name, n in grown.items() if n > 0} == {}


# +-------------------------------------------------------------------------
# | Factory-made objects leave no shells (plan memory-qml-factory.md, stage 1)

_ROUNDS_SCRIPT = r"""
import gc, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd() / 'test' / 'journeys'))
from _harness import Journey, pump

NAMES = sys.argv[1].split(',')
WINDOWS = ['DialogOptions.qml', 'DialogLiveLog.qml', 'DialogCalibration.qml',
           'DialogManageModes.qml']
ROUNDS = int(sys.argv[2])


def before(j):
    j.input_module()
    j.vjoy_module()


def story(j):
    import shiboken6
    from gremlin import plugin_manager
    from gremlin.types import InputType
    from gremlin.ui import type_aliases as ta

    classes = {n: ta.QML_TYPES[n] for n in NAMES if n in ta.QML_TYPES}
    j.out['missing'] = sorted(set(NAMES) - set(classes))

    def counts():
        pump(100)
        gc.collect()
        valid = dict.fromkeys(classes, 0)
        shells = dict.fromkeys(classes, 0)
        by_cls = {cls: name for name, cls in classes.items()}
        for obj in gc.get_objects():
            name = by_cls.get(type(obj))
            if name is None:
                continue
            if shiboken6.isValid(obj):
                valid[name] += 1
            else:
                shells[name] += 1
        return valid, shells

    # A Change Mode action on button 1, for the pane rounds.
    pm = plugin_manager.PluginManager()
    j.profile.modes.add_mode('Ground')
    j.profile.modes.set_parent('Ground', 'Default')
    uid = j.stick().device_guid.uuid
    item = j.profile.get_input_item(uid, InputType.JoystickButton, 1, 'Default', True)
    root = item.add_item_binding().root_action
    root.insert_action(pm.create_instance('Change Mode', InputType.JoystickButton),
                       'children')
    state = j.backend.uiState

    def page_round():
        catalog = j.open_device_bindings('pjoy_pro')
        j.open_input(catalog, 'button', 1)
        pump(200)
        catalog.endPane()
        j.wait_until(lambda: catalog.paneModel is None, 'pane closed', 10)
        j.ev('uiState.setCurrentRoom("status")')
        j.wait_until(lambda: j.ev('uiState.currentRoom') == 'status', 'Home', 10)
        pump(150)

    def window_round(qml):
        j.ev('Helpers.createComponent("%s")' % qml)
        pump(400)
        j.ev('Helpers.windowOf("%s").close()' % qml)
        pump(250)

    def one_round():
        page_round()
        for qml in WINDOWS:
            window_round(qml)

    one_round()  # warm-up: caches and first-use objects
    valid0, shells0 = counts()
    for _ in range(ROUNDS):
        one_round()
    valid1, shells1 = counts()
    j.out['shells'] = {n: c for n, c in shells1.items() if c}
    j.out['shell-growth'] = {n: shells1[n] - shells0[n] for n in classes
                             if shells1[n] != shells0[n]}
    j.out['valid-growth'] = {n: valid1[n] - valid0[n] for n in classes
                             if valid1[n] > valid0[n]}
    j.out['done'] = True


if __name__ == '__main__':
    Journey(before).run(story)
"""


@pytest.fixture(scope="module")
def rounds(tmp_path_factory: pytest.TempPathFactory) -> dict:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import run_journey  # pyright: ignore[reportMissingImports]

    tmp_path = tmp_path_factory.mktemp("factory_rounds")
    script = tmp_path / "factory_rounds.py"
    script.write_text(_ROUNDS_SCRIPT, encoding="utf-8")
    names = _factory_made()
    out = run_journey(script, tmp_path / "home", ",".join(names), "4")
    print(f"factory types {len(names)}; rounds: "
          f"{ {k: out.get(k) for k in ('shells', 'shell-growth', 'valid-growth')} }")
    assert out.get("done"), (
        f"{out.get('error')}\n{out.get('traceback', '')}\n{out.get('_stderr', '')}"
    )
    return out


def test_factory_types_are_all_registered(rounds: dict) -> None:
    assert rounds["missing"] == []


def test_pages_and_windows_opened_again_leave_no_shells(rounds: dict) -> None:
    """Device Bindings (with the Change Mode pane), Options, Live Log,
    Calibration and Manage Modes, opened and closed 4 times: no shell of a
    factory-made type, and no live one more than after the first round."""
    assert rounds["shells"] == {}
    assert rounds["shell-growth"] == {}
    assert rounds["valid-growth"] == {}


# +-------------------------------------------------------------------------
# | Stage 2 pages and windows (plan memory-qml-factory.md, stage 2); its own
# | journey so each stays inside the journey time limit.

_STAGE2_SCRIPT = r"""
import gc, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd() / 'test' / 'journeys'))
from _harness import Journey, pump

NAMES = sys.argv[1].split(',')
ROUNDS = int(sys.argv[2])
PAGES = [('logical', 'logical'), ('keyboard', 'keyboard'), ('osc', 'osc')]
WINDOWS = ['DialogProfileSettings.qml', 'DialogScripts.qml', 'DialogHistory.qml',
           'DialogSearch.qml', 'DialogHealth.qml', 'DialogInputViewer.qml',
           'DialogDeviceInformation.qml']


def before(j):
    j.input_module()
    j.vjoy_module()


def story(j):
    import shiboken6
    from gremlin.ui import type_aliases as ta

    classes = {n: ta.QML_TYPES[n] for n in NAMES if n in ta.QML_TYPES}
    j.out['missing'] = sorted(set(NAMES) - set(classes))
    state = j.backend.uiState

    def counts():
        pump(100)
        gc.collect()
        valid = dict.fromkeys(classes, 0)
        shells = dict.fromkeys(classes, 0)
        by_cls = {cls: name for name, cls in classes.items()}
        for obj in gc.get_objects():
            name = by_cls.get(type(obj))
            if name is None:
                continue
            if shiboken6.isValid(obj):
                valid[name] += 1
            else:
                shells[name] += 1
        return valid, shells

    def home():
        j.ev('uiState.setCurrentRoom("status")')
        j.wait_until(lambda: state.currentRoom == 'status', 'Home', 10)
        pump(150)

    def page_round(slug, tab):
        j.ev('openDeviceBindingsForCard(_moduleModel.cardMap(%s))' % json.dumps(slug))
        j.wait_until(lambda: state.currentTab == tab
                     and state.currentRoom == 'configuration', 'page ' + tab, 10)
        pump(300)
        home()

    def window_round(qml):
        j.ev('Helpers.createComponent("%s")' % qml)
        pump(400)
        j.ev('Helpers.windowOf("%s").close()' % qml)
        pump(250)

    def mapping_editor_round():
        j.ev('openBlankDeviceMappingEditor()')
        pump(500)
        j.ev('Helpers.windowOf("DialogDeviceMappingEditor.qml").close()')
        pump(300)

    def one_round():
        for slug, tab in PAGES:
            page_round(slug, tab)
        for qml in WINDOWS:
            window_round(qml)
        mapping_editor_round()

    one_round()  # warm-up: caches and first-use objects
    valid0, shells0 = counts()
    for _ in range(ROUNDS):
        one_round()
    valid1, shells1 = counts()
    j.out['shells'] = {n: c for n, c in shells1.items() if c}
    j.out['shell-growth'] = {n: shells1[n] - shells0[n] for n in classes
                             if shells1[n] != shells0[n]}
    j.out['valid-growth'] = {n: valid1[n] - valid0[n] for n in classes
                             if valid1[n] > valid0[n]}
    j.out['done'] = True


if __name__ == '__main__':
    Journey(before).run(story)
"""


@pytest.fixture(scope="module")
def stage2_rounds(tmp_path_factory: pytest.TempPathFactory) -> dict:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import run_journey  # pyright: ignore[reportMissingImports]

    tmp_path = tmp_path_factory.mktemp("factory_rounds_stage2")
    script = tmp_path / "factory_rounds_stage2.py"
    script.write_text(_STAGE2_SCRIPT, encoding="utf-8")
    names = _factory_made()
    out = run_journey(script, tmp_path / "home", ",".join(names), "3")
    print(f"factory types {len(names)}; stage 2 rounds ({out.get('_seconds')} s): "
          f"{ {k: out.get(k) for k in ('shells', 'shell-growth', 'valid-growth')} }")
    assert out.get("done"), (
        f"{out.get('error')}\n{out.get('traceback', '')}\n{out.get('_stderr', '')}"
    )
    return out


def test_stage2_pages_and_windows_opened_again_leave_no_shells(
    stage2_rounds: dict,
) -> None:
    """Logical, Keyboard and OSC pages, Profile Settings, Scripts, History,
    Search, Health, Input Viewer, Device Information and the Device Mapping
    Editor, opened and closed 3 times: no shell of a factory-made type, and
    no live one more than after the first round."""
    assert stage2_rounds["missing"] == []
    assert stage2_rounds["shells"] == {}
    assert stage2_rounds["shell-growth"] == {}
    assert stage2_rounds["valid-growth"] == {}


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
