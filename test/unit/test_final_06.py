# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final test plan, page 06 (Run time and outputs): the statements no
earlier test checked. claude/final-test-plan/06-runtime-outputs.md lists
every statement of the page and what checks it.

- S4: after Stop no input event reaches the profile's actions.
- S5: a toolbar mode the profile lacks falls back to its Startup Mode.
- S10, S12: a script that fails to load is skipped and logged, the rest
  run; a missing user plugin gives its own message and no Run.
- S15: New Profile and opening a profile Stop first.
- S55: the vJoy driver wording (D-02-Q17 wording).
- S60, S63: a viewer never plugs in an Xbox pad; a failed Xbox write is
  logged once.
- S71, S72: Map to Keyboard (modifiers first, released in reverse) and Map
  to Mouse (click, wheel once per press, axis motion direction).
- S80, S81: Logical Device Assign Hardware lists claimed controls of the
  same type and adds or removes only a Map to Logical Device on the source.

Nothing reaches the PC: drivers, sound, speech, keys and mouse are stand-ins.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import code_runner, event_handler, keyboard, shared_state
from gremlin.base_classes import Value
from gremlin.common import SingletonMetaclass
from gremlin.event_handler import Event
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.types import InputType, MouseButton

_GUID = uuid.UUID("06060606-0606-0606-0606-060606060606")
_STICK = uuid.UUID("06060606-1111-2222-3333-444444444444")


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


def _fake_listener(monkeypatch: pytest.MonkeyPatch, listener: object) -> None:
    fake = mock.MagicMock(return_value=listener)
    fake.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake)


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[code_runner.CodeRunner]:
    """A CodeRunner whose drivers, devices, sound and network are stand-ins;
    macros, the mouse controller, modes and the event handler are real."""
    from gremlin import mode_manager

    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    _fake_listener(monkeypatch, mock.MagicMock())
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    shared_state.set_runtime_active(False)
    event_handler.EventHandler().resume()
    mm._mode_stack = stack


class _Bus(QtCore.QObject):
    """The input modules' event bus, with real signals."""

    event = QtCore.Signal(object)  # pyright: ignore[reportAssignmentType]
    key_event = QtCore.Signal(object)

    def reload(self) -> None:
        pass


class _Listener(QtCore.QObject):
    virtual_event = QtCore.Signal(object)
    joystick_event = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.gremlin_active = False


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A CodeRunner wired to real signals; handled events are counted."""
    for name in ("output", "OscRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    bus = _Bus()
    listener = _Listener()
    monkeypatch.setattr(code_runner, "InputModuleRuntime", lambda: bus)
    _fake_listener(monkeypatch, listener)
    handled: list[object] = []
    run = code_runner.CodeRunner()
    handler = mock.MagicMock()
    handler.process_event = handled.append
    run.event_handler = handler
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield SimpleNamespace(run=run, bus=bus, listener=listener, handled=handled)
    run.stop()
    shared_state.set_runtime_active(False)


def _button(pressed: bool, mode: str = "Default") -> Event:
    return Event(InputType.JoystickButton, 5, _GUID, mode, is_pressed=pressed)


# --- S4: stopped means nothing is sent ---------------------------------------


def test_after_stop_no_input_event_reaches_the_profile(
    wired: SimpleNamespace,
) -> None:
    wired.run.start(Profile(), "Default")
    wired.bus.event.emit("while running")
    assert wired.handled == ["while running"]
    wired.run.stop()
    assert not wired.listener.gremlin_active
    assert not shared_state.runtime_active()
    wired.bus.event.emit("stick")
    wired.bus.key_event.emit("key")
    wired.listener.virtual_event.emit("virtual button")
    assert wired.handled == ["while running"]


# --- S5: the toolbar mode, else the Startup Mode rule ------------------------


def test_a_toolbar_mode_the_profile_lacks_uses_the_startup_mode(
    runner: code_runner.CodeRunner,
) -> None:
    from gremlin import mode_manager

    profile = Profile()
    profile.modes.add_mode("Alpha")
    profile.settings.startup_mode = "Alpha"
    runner.start(profile, "Default")  # the toolbar mode, in the profile
    assert mode_manager.ModeManager().current.name == "Default"
    runner.stop()
    runner.start(profile, "Gone")  # not in this profile
    assert mode_manager.ModeManager().current.name == "Alpha"


# --- S10 / S12: scripts at Run ------------------------------------------------


class _Script:
    """A profile script as the Run sees it."""

    def __init__(self, name: str, load_error: str, fixed: bool = False) -> None:
        self.name = name
        self.load_error = load_error
        self.is_configured = True
        self.path = Path("C:/gremlin-final-06-scripts") / f"{name}.py"
        self.retries = 0
        self.reloads = 0
        self._fixed = fixed

    def retry(self) -> bool:
        self.retries += 1
        if self._fixed:
            self.load_error = ""
        return self._fixed

    def reload(self) -> bool:
        self.reloads += 1
        return True


def test_a_script_that_fails_to_load_is_skipped_and_the_rest_run(
    runner: code_runner.CodeRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    import logging

    monkeypatch.setattr(sys, "path", list(sys.path))
    warnings: list[str] = []
    monkeypatch.setattr(
        logging.getLogger("system"),
        "warning",
        lambda msg, *a, **k: warnings.append(msg),
    )
    profile = Profile()
    broken = _Script("broken", "Syntax error, line 2")
    fixed = _Script("fixed", "Syntax error, line 3", fixed=True)
    good = _Script("good", "")
    profile.scripts.scripts.extend(cast(Any, [broken, fixed, good]))
    try:
        runner.start(profile, "Default")
        assert runner.is_running()  # the Run goes on
        assert broken.retries == 1  # tried again once at Run
        assert broken.reloads == 0  # not run
        assert fixed.retries == 1 and fixed.reloads == 1  # fixed since: runs
        assert good.reloads == 1
        assert any("broken" in w and "Syntax error, line 2" in w for w in warnings)
    finally:
        runner.stop()
        del profile.scripts.scripts[:]


def test_a_missing_user_plugin_says_so_and_runs_nothing(
    runner: code_runner.CodeRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[tuple] = []
    monkeypatch.setattr(
        code_runner.signal, "display_error", lambda *a: shown.append(a)
    )

    def missing() -> None:
        raise ImportError("No module named 'my_plugin'")

    monkeypatch.setattr(runner, "_setup_user_scripts", missing)
    runner.start(Profile(), "Default")  # shown, not raised
    assert [s[0] for s in shown] == [
        "Could not run the profile: a user plugin is missing."
    ]
    assert not runner.is_running()
    assert not shared_state.runtime_active()


# --- S15: Stop before another profile opens -----------------------------------


def _backend_stub(order: list[str], running: bool = True) -> Any:  # noqa: ANN401
    def activate(on: bool) -> None:
        order.append("run" if on else "stop")
        stub.gremlinActive = on

    def read(fpath: str) -> None:
        order.append("read")
        stub.profile = SimpleNamespace(fpath=Path(fpath))

    stub: Any = SimpleNamespace(
        gremlinActive=running,
        activate_gremlin=activate,
        profile=SimpleNamespace(fpath=None),
        _load_problem="",
        _read_profile=read,
        newProfile=lambda: order.append("new"),
        profileChanged=mock.MagicMock(),
        windowTitleChanged=mock.MagicMock(),
        # The recovery copy (04 S94): New and Open drop / offer copies.
        _recovery=mock.MagicMock(),
        _set_recovery_offer=lambda offer: None,
    )
    return stub


def test_new_profile_stops_the_run_first(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin.ui import backend as backend_mod

    order: list[str] = []
    stub = _backend_stub(order)
    old = stub.profile
    monkeypatch.setattr(backend_mod, "signal", mock.MagicMock())

    def stop(on: bool) -> None:
        assert stub.profile is old  # stopped while the old one is still open
        order.append("stop")

    stub.activate_gremlin = stop
    backend_mod.Backend.klass.newProfile(stub)
    assert order == ["stop"]
    assert stub.profile is not old


def test_opening_a_profile_stops_the_run_first(tmp_path: Path) -> None:
    from gremlin.ui import backend as backend_mod

    path = tmp_path / "other.xml"
    path.write_text("<profile/>", encoding="utf-8")
    order: list[str] = []
    stub = _backend_stub(order)
    assert backend_mod.Backend.klass._load_profile(stub, str(path), report=False)
    assert order == ["stop", "read"]


# --- S55: the vJoy driver wording --------------------------------------------


def test_the_vjoy_driver_check_has_one_wording(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import output

    monkeypatch.setattr(output, "vjoy_driver_found", lambda: False)
    # 06 S55 as changed by D-02-Q17: "the program", not the name.
    assert output.vjoy_driver_problem() == (
        "vJoy is not installed or not running",
        "Install vJoy, then restart the program.",
    )
    monkeypatch.setattr(output, "vjoy_driver_found", lambda: True)
    assert output.vjoy_driver_problem() == ("", "")


# --- S60 / S63: the Xbox pad --------------------------------------------------


class _FakeVigem:
    """ViGEmClient.dll stand-in: records plug and unplug."""

    def __init__(self) -> None:
        from vigem.xbox import VIGEM_OK

        self.ok = VIGEM_OK
        self.log: list[str] = []

    def vigem_alloc(self) -> int:
        return 11

    def vigem_connect(self, _bus: int) -> int:
        return self.ok

    def vigem_disconnect(self, _bus: int) -> None:
        self.log.append("disconnect")

    def vigem_free(self, _bus: int) -> None:
        pass

    def vigem_target_x360_alloc(self) -> int:
        return 22

    def vigem_target_add(self, _bus: int, _dev: int) -> int:
        self.log.append("plug")
        return self.ok

    def vigem_target_x360_update(self, *_a: object) -> int:
        return self.ok

    def vigem_target_remove(self, _bus: int, _dev: int) -> None:
        self.log.append("unplug")

    def vigem_target_free(self, _dev: int) -> None:
        pass


@pytest.fixture
def vigem(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[_FakeVigem, Any]]:
    """A fresh XboxProxy (the shared one put back) on a fake ViGEm."""
    from vigem import own_pads, vigem_client, xbox

    lib = _FakeVigem()
    monkeypatch.setattr(vigem_client, "client", lambda: lib)
    monkeypatch.setattr(own_pads, "before_plug", lambda: None)
    fresh = object.__new__(xbox.XboxProxy)
    fresh.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, xbox.XboxProxy, fresh)
    yield lib, fresh
    fresh.reset()


def test_a_viewer_never_plugs_in_an_xbox_pad(
    vigem: tuple[_FakeVigem, Any],
) -> None:
    from gremlin.modules import output
    from vigem.xbox import XboxTarget

    lib, proxy = vigem
    assert output.xbox_state(1) == {}  # the Xbox Viewer asks: nothing plugged
    assert lib.log == []
    assert proxy._pads == {}
    assert output.write_xbox(1, XboxTarget.A, True)  # a Map to Xbox send
    assert lib.log == ["plug"]
    assert output.xbox_state(1)  # now the viewer sees the pad
    assert lib.log == ["plug"]  # and plugged nothing more


def test_a_failed_xbox_write_is_logged_once_and_goes_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import output
    from vigem import xbox

    class _BrokenPad:
        def apply(self, _target: object, _value: object) -> None:
            raise RuntimeError("bus gone")

    class _Proxy:
        def __getitem__(self, _pad: int) -> _BrokenPad:
            return _BrokenPad()

    log = mock.Mock()
    monkeypatch.setattr(output, "syslog", log)
    monkeypatch.setattr(output, "_blocked", set())
    monkeypatch.setattr(xbox, "XboxProxy", _Proxy)
    assert output.write_xbox(1, xbox.XboxTarget.A, True) is False  # no raise
    assert output.write_xbox(1, xbox.XboxTarget.B, True) is False
    assert log.warning.call_count == 1
    assert "Xbox pad 1 write failed" in log.warning.call_args[0][0]


# --- S71: Map to Keyboard -----------------------------------------------------


class _Binding(QtCore.QObject):
    behaviorChanged = QtCore.Signal()


def _key_event(key: keyboard.Key) -> Event:
    return Event(
        InputType.Keyboard, (key.scan_code, key.is_extended), _GUID, "Default",
        is_pressed=True,
    )


def test_map_to_keyboard_puts_modifiers_first_and_releases_in_reverse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.map_to_keyboard import (
        MapToKeyboardData,
        MapToKeyboardFunctor,
        MapToKeyboardModel,
    )
    from gremlin import macro

    m = keyboard.key_from_name("m")
    shift = keyboard.key_from_name("leftshift")
    ctrl = keyboard.key_from_name("leftcontrol")
    data = MapToKeyboardData(InputType.JoystickButton)
    binding = _Binding()
    model = MapToKeyboardModel(data, cast(Any, binding), cast(Any, None),
                               cast(Any, None), cast(Any, None))
    try:
        model.updateInputs([_key_event(m), _key_event(shift), _key_event(ctrl)])
    finally:
        model.dispose()
        model.deleteLater()
        binding.deleteLater()
    assert data.keys == [shift, ctrl, m]  # recorded: modifiers first

    queued: list[Any] = []
    monkeypatch.setattr(macro.MacroManager(), "queue_macro", queued.append)
    functor = MapToKeyboardFunctor(data)
    functor(_button(True), Value(True))
    functor(_button(False), Value(False))

    def keys(one: Any) -> list[tuple[str, bool]]:  # noqa: ANN401
        return [
            (step.key.name, step.is_pressed)
            for step in one.sequence
            if isinstance(step, macro.KeyAction)
        ]

    assert [keys(q) for q in queued] == [
        [(shift.name, True), (ctrl.name, True), (m.name, True)],  # held
        [(m.name, False), (ctrl.name, False), (shift.name, False)],  # let go
    ]


# --- S72: Map to Mouse --------------------------------------------------------


@pytest.fixture
def mouse(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """sendinput's mouse calls, recorded instead of sent."""
    from gremlin import sendinput

    sent: list[tuple] = []
    monkeypatch.setattr(sendinput, "mouse_press", lambda b: sent.append(("press", b)))
    monkeypatch.setattr(
        sendinput, "mouse_release", lambda b: sent.append(("release", b))
    )
    monkeypatch.setattr(sendinput, "mouse_wheel", lambda d: sent.append(("wheel", d)))
    return sent


def test_map_to_mouse_clicks_a_button_and_turns_the_wheel_once_per_press(
    mouse: list[tuple],
) -> None:
    from action_plugins.map_to_mouse import MapToMouseData, MapToMouseFunctor

    data = MapToMouseData(InputType.JoystickButton)
    data.button = MouseButton.Right
    click = MapToMouseFunctor(data)
    click(_button(True), Value(True))
    assert mouse == [("press", MouseButton.Right)]  # held while held
    click(_button(False), Value(False))
    assert mouse[-1] == ("release", MouseButton.Right)

    mouse.clear()
    data.button = MouseButton.WheelDown
    wheel = MapToMouseFunctor(data)
    wheel(_button(True), Value(True))
    wheel(_button(False), Value(False))
    data.button = MouseButton.WheelUp
    wheel(_button(True), Value(True))
    wheel(_button(False), Value(False))
    assert mouse == [("wheel", 1), ("wheel", -1)]  # one step per press


def test_map_to_mouse_moves_the_pointer_with_the_axis_in_its_direction() -> None:
    from action_plugins.map_to_mouse import MapToMouseData, MapToMouseFunctor

    data = MapToMouseData(InputType.JoystickAxis)
    data.min_speed = 10
    data.max_speed = 110
    data.direction = 90  # left / right
    functor = MapToMouseFunctor(data)
    moves: list[tuple] = []

    def set_velocity(_key: object, v: Any) -> None:  # noqa: ANN401
        moves.append((round(v.x, 6) + 0.0, round(v.y, 6) + 0.0))

    functor._motion = cast(
        Any,
        SimpleNamespace(
            set_velocity=set_velocity, clear=lambda _key: moves.append((0.0, 0.0))
        ),
    )

    def axis(value: float) -> None:
        functor(
            Event(InputType.JoystickAxis, 1, _GUID, "Default", value=value),
            Value(value),
        )

    axis(0.5)
    axis(-1.0)
    axis(0.0)
    assert moves == [(60.0, 0.0), (-110.0, 0.0), (0.0, 0.0)]  # 0: stopped
    data.direction = 0  # up / down (positive moves down)
    axis(1.0)
    assert moves[-1] == (0.0, 110.0)


# --- S80 / S81: Logical Device Assign Hardware --------------------------------


@pytest.fixture
def assign(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """The Logical page model, with one stick, the Keyboard and OSC saved as
    input modules (stand-in files), two OSC addresses in OSC's shared list
    and a vJoy device used as output."""
    from gremlin import device_initialization
    from gremlin.modules.claim import key_id
    from gremlin.osc import OscDevice
    from gremlin.ui import logical_layout
    from gremlin.ui.module_model import KEYBOARD_GUID, OSC_GUID

    key_a = keyboard.key_from_name("a")
    docs = {
        "Stick": {
            "direction": "source",
            "claim": {"buttons": [3], "axes": [1], "hats": [1]},
        },
        "Keyboard": {
            "direction": "source",
            "claim": {"keys": [key_id(key_a.scan_code, key_a.is_extended)]},
        },
        # An old claim in OSC's file is not what Assign Hardware lists.
        "OSC": {"direction": "source", "claim": {"buttons": [7]}},
        "vJoy 1": {"direction": "dest", "claim": {"buttons": [1]}},
    }
    monkeypatch.setattr(
        logical_layout,
        "store",
        SimpleNamespace(
            exists=lambda name, _guid: name in docs,
            read=lambda name, _guid: docs[name],
        ),
    )
    monkeypatch.setattr(
        device_initialization,
        "physical_devices",
        lambda: [
            SimpleNamespace(name="Stick", device_guid=SimpleNamespace(uuid=_STICK))
        ],
    )
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    profile = Profile()
    profile.modes.add_mode("Flight")
    monkeypatch.setattr(shared_state, "current_profile", profile)
    LogicalDevice().reset()
    logical = LogicalDevice()
    logical.create(InputType.JoystickButton)
    logical.create(InputType.JoystickAxis)
    OscDevice().rows.load_dict({"inputs": []})
    OscDevice().create(InputType.JoystickButton, label="/fire")
    OscDevice().create(InputType.JoystickAxis, label="/throttle")
    model = logical_layout.LogicalLayoutModel()
    yield SimpleNamespace(
        model=model,
        profile=profile,
        logical=logical,
        key_a=key_a,
        keyboard_guid=KEYBOARD_GUID,
        osc_guid=OSC_GUID,
    )
    model.deleteLater()
    LogicalDevice().reset()
    OscDevice().rows.load_dict({"inputs": []})
    OscDevice().rows.mark_saved()


def _listed(rows: list) -> dict[str, list[str]]:
    return {row["name"]: [c["label"] for c in row["controls"]] for row in rows}


def test_assign_hardware_lists_claimed_controls_and_osc_inputs_of_the_same_type(
    assign: SimpleNamespace,
) -> None:
    buttons = _listed(assign.model.hardware("parent:button:1", ""))
    assert buttons["Stick"] == ["Button 3"]
    assert buttons["Keyboard"] == [assign.key_a.name]  # keys for buttons
    # OSC: its addresses from its own list (D-09-OSC-FILE), not claims.
    assert buttons["OSC"] == ["/fire"]
    assert "vJoy 1" not in buttons  # a vJoy used as output is no source
    axes = _listed(assign.model.hardware("parent:axis:1", ""))
    assert axes["Stick"] == ["Axis 1"]
    assert "Keyboard" not in axes  # no keys for an axis
    assert axes["OSC"] == ["/throttle"]


def _links(profile: Profile, mode: str) -> list[tuple]:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 3, mode, create_if_missing=False
    )
    if item is None:
        return []
    return [
        (kid.tag, kid.logical_input_type, int(kid.logical_input_id))
        for binding in item.action_sequences
        for kid in binding.root_action.get_actions()[0]
    ]


def test_assign_hardware_adds_and_removes_only_a_map_to_logical_device(
    assign: SimpleNamespace,
) -> None:
    model, profile = assign.model, assign.profile
    stick_button = f"{_STICK}|button|3|0"
    model.setMode("Flight")  # the page's mode
    model.setLinks("parent:button:1", [stick_button], True)
    assert _links(profile, "Flight") == [
        ("map-to-logical-device", InputType.JoystickButton, 1)
    ]
    assert _links(profile, "Default") == []  # only in the page's mode
    # S81: the Logical control itself gets no action (sending on to Xbox or
    # vJoy is only through its own actions).
    own = profile.get_input_item(
        assign.logical.device_guid, InputType.JoystickButton, 1, "Flight",
        create_if_missing=False,
    )
    assert own is None or not own.action_sequences
    listed = model.hardware("parent:button:1", "")
    stick = next(row for row in listed if row["name"] == "Stick")
    assert stick["controls"][0]["on"] is True
    model.setLinks("parent:button:1", [stick_button], False)
    assert _links(profile, "Flight") == []
