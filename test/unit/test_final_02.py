# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final phase, spec page 02 (devices and raw input): the statements no
test checked yet. Plan: claude/final-test-plan/02-devices-input.md.

Fake driver only: no real hook, HidHide, vJoy or ViGEm call is made; the
HidHide driver is stood in for function by function, and every setting a
test changes is put back.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import collections
import ctypes
import json
import logging
import os
import pathlib
import subprocess
import textwrap
import threading
import types
import uuid
from collections.abc import Callable, Iterator
from typing import Any
from unittest import mock

import pytest
import shiboken6
from PySide6 import QtCore

import dill
from gremlin import (
    device_initialization as di,
)
from gremlin import (
    error,
    event_handler,
    input_cache,
    mode_manager,
    shared_state,
    util,
    windows_event_hook,
)
from gremlin.config import Configuration
from gremlin.event_handler import Event
from gremlin.tree import TreeNode
from gremlin.types import HatDirection, InputType
from test import fake_hardware
from vjoy import vjoy

_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_ROOT = pathlib.Path(__file__).parents[2]
_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid


def _copy_device(of: int, data1: int, name: bytes) -> dill._DeviceSummary:
    """A copy of fake device `of` (0 stick, 1 vJoy) with its own id and name."""
    fake = dill.DILL._dll
    dev = dill._DeviceSummary()
    ctypes.memmove(
        ctypes.byref(dev), ctypes.byref(fake.devices[of]), ctypes.sizeof(dev)
    )
    dev.device_guid.Data1 = data1
    dev.name = name
    return dev


def _input(kind: int, index: int, value: int) -> dill._JoystickInputData:
    """A raw driver event of the fake stick (1 axis, 2 button, 3 hat)."""
    return dill._JoystickInputData(
        device_guid=fake_hardware.raw_guid(is_virtual=False),
        input_type=kind, input_index=index, value=value,
    )


@pytest.fixture
def first_scan(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A first scan from an empty list; scan state and settings put back."""
    monkeypatch.setattr(di, "_joystick_devices", collections.OrderedDict())
    monkeypatch.setattr(di, "_left_out", set())
    monkeypatch.setattr(di, "_vjoy_problems", [])
    monkeypatch.setattr(di, "_told", ())
    monkeypatch.setattr(di, "_window_up", False)
    monkeypatch.setattr(di, "_own_pads", [])
    monkeypatch.setattr("gremlin.modules.output.reset_vjoy", lambda: None)
    monkeypatch.setattr("gremlin.signal.display_error", lambda *a: None)
    stored = Configuration().value(*di.TWIN_SETTING)
    Configuration().set(*di.TWIN_SETTING, {})
    yield
    Configuration().set(*di.TWIN_SETTING, stored)


@pytest.fixture
def plugged(event_listener: event_handler.EventListener) -> Iterator[list]:
    """The fake driver's device list for hot-plug tests; put back after,
    with the device list and calibrations scanned again."""
    fake = dill.DILL._dll
    before = list(fake.devices)
    with mock.patch("gremlin.modules.output.reset_vjoy"):
        yield fake.devices
        fake.devices[:] = before
        di.joystick_devices_initialization()
        event_listener._init_joysticks()


# --- A. Device list and scan -------------------------------------------------


def test_s1_s19_physical_by_name_then_vjoy_by_number_linked_by_counts(
    monkeypatch: pytest.MonkeyPatch, first_scan: None
) -> None:
    """02 S1, S19: physical devices sorted by name, then vJoy by number;
    each vJoy number is linked by its count of axes, buttons and hats."""
    fake = dill.DILL._dll
    small_vjoy = _copy_device(1, 0x6600, b"vJoy Device")
    small_vjoy.button_count = 32
    zulu = _copy_device(0, 0x6601, b"Zulu Stick")
    alpha = _copy_device(0, 0x6602, b"Alpha Throttle")
    # Windows lists them in any order; the 32-button vJoy comes first.
    monkeypatch.setattr(
        fake, "devices", [small_vjoy, zulu, fake.devices[0], fake.devices[1], alpha]
    )
    monkeypatch.setattr(vjoy, "device_exists", lambda i: i in (1, 2))
    monkeypatch.setattr(vjoy, "button_count", lambda i: 64 if i == 1 else 32)
    di.joystick_devices_initialization()

    listed = di.joystick_devices()
    physical = [d.name for d in listed if not d.is_virtual]
    assert sorted(physical) == physical
    assert set(physical) == {"Alpha Throttle", "Zulu Stick", "pJoy Pro"}
    assert [d.is_virtual for d in listed] == [False, False, False, True, True]
    assert [(d.vjoy_id, d.button_count) for d in listed if d.is_virtual] == [
        (1, 64), (2, 32)
    ]


def test_s10_input_labels_come_from_the_device_database_by_vid_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """02 S10: labels by VID/PID when Options asks for labels; "Button 2"
    style names otherwise and for inputs the database doesn't name."""
    from gremlin import common

    (tmp_path / "device_db.json").write_text(json.dumps({
        "revision": 1,
        "devices": [{
            "vendor_id": 0x5678, "product_id": 0xFACE, "name": "pJoy Pro",
            "mapping": "pjoy",
        }],
        "mapping": {"pjoy": {"Button 1": "Trigger"}},
    }), encoding="utf-8")
    monkeypatch.setattr(
        input_cache.util, "resource_path", lambda rel: str(tmp_path / rel)
    )
    db = object.__new__(input_cache.DeviceDatabase)
    input_cache.DeviceDatabase.__init__(db)
    stick = di.device_for_uuid(_STICK)
    mapping = db.get_mapping(stick)
    assert mapping is not None

    mode = {"value": "Label"}
    real_value = Configuration.value

    def value(self: Any, *key: str) -> Any:  # noqa: ANN401
        if key == ("ui", "general", "display-mode"):
            return mode["value"]
        return real_value(self, *key)

    monkeypatch.setattr(Configuration, "value", value)
    button1 = (InputType.JoystickButton, 1)
    button2 = (InputType.JoystickButton, 2)
    plain1 = common.input_to_ui_string(*button1)
    assert mapping.input_name(button1) == "Trigger"
    assert mapping.input_name(button2) == common.input_to_ui_string(*button2)
    mode["value"] = "Numerical and Label"
    assert mapping.input_name(button1) == f"{plain1} - Trigger"
    mode["value"] = "Numerical"
    assert mapping.input_name(button1) == plain1
    # A device the database doesn't know has no labels.
    vjoy_dev = next(d for d in di.joystick_devices() if d.is_virtual)
    assert db.get_mapping(vjoy_dev) is None


def test_s4_a_failed_first_scan_shows_the_failure_window_not_the_main_one(
    tmp_path: pathlib.Path,
) -> None:
    """02 S4: one scan at start, before the main window; when it fails the
    failure window opens instead. The app is built off-screen in its own
    process with the fake driver; hooks, HidHide and message boxes are
    stood in for."""
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    code = textwrap.dedent("""
        import ctypes, importlib.util, os, sys
        from pathlib import Path
        ROOT = Path.cwd()
        sys.path.insert(0, str(ROOT))
        spec = importlib.util.spec_from_file_location(
            "fake_hardware", ROOT / "test" / "fake_hardware.py")
        fake_hardware = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fake_hardware)
        fake_hardware.install()

        from gremlin import windows_event_hook
        windows_event_hook._Hook._listen = lambda self: None
        ctypes.windll.user32.MessageBoxW = lambda *a: 2
        import gremlin.ui.hidhide
        gremlin.ui.hidhide.apply_on_start = lambda: None
        import gremlin.ui.update_model as um
        um.UpdateModel.startup = lambda self, *a, **k: None
        import gremlin.device_initialization as di
        import gremlin.error
        scans = []

        def failing_scan():
            scans.append(1)
            raise gremlin.error.GremlinError("The device scan failed in a test.")

        di.joystick_devices_initialization = failing_scan

        from PySide6 import QtCore
        import joystick_gremlin
        app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
        roots = app.engine.rootObjects()
        texts = []
        for root in roots:
            for child in root.findChildren(QtCore.QObject):
                text = child.property("text")
                if isinstance(text, str):
                    texts.append(text)
        print("SCANS", len(scans), flush=True)
        print("ROOTS", len(roots), flush=True)
        print("FAILURE", any("error occurred during startup" in t for t in texts),
              flush=True)
        print("DETAIL", any("device scan failed in a test" in t for t in texts),
              flush=True)
        print("MAIN", hasattr(app, "main_window"), flush=True)
        print("DONE", flush=True)
        os._exit(0)
    """)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = result.stdout
    assert "DONE" in out, out[-2000:] + result.stderr[-2000:]
    assert "SCANS 1" in out
    assert "ROOTS 1" in out
    assert "FAILURE True" in out
    assert "DETAIL True" in out
    assert "MAIN False" in out


# --- C. vJoy devices at scan -------------------------------------------------


def test_s22_a_left_out_vjoy_is_logged_as_an_error_with_logs_off(
    monkeypatch: pytest.MonkeyPatch, first_scan: None, caplog: pytest.LogCaptureFixture
) -> None:
    """02 S22: each left-out vJoy goes to the system log as an error, also
    with Diagnostic logs Off."""
    from gremlin.ui.log_option import LOGGER_NAMES, apply_log_level

    kept = []
    for name in LOGGER_NAMES:
        logger = logging.getLogger(name)
        kept.append((logger, logger.level, logger.disabled,
                     [(h, h.level) for h in logger.handlers]))
    monkeypatch.setattr(vjoy, "hat_configuration_valid", lambda i: False)
    try:
        apply_log_level("Off")
        caplog.clear()
        di.joystick_devices_initialization()
    finally:
        for logger, level, disabled, handlers in kept:
            logger.setLevel(level)
            logger.disabled = disabled
            for handler, handler_level in handlers:
                handler.setLevel(handler_level)
    errors = [
        r for r in caplog.records
        if r.name == "system" and r.levelno == logging.ERROR
        and "vJoy left out" in r.getMessage()
    ]
    assert len(errors) == 1 and "vJoy 1" in errors[0].getMessage()


# --- D. Plug, unplug, reconnect ---------------------------------------------


class _FakeTimer:
    def __init__(self, name: str, interval: float, function: Callable) -> None:
        self.name = name
        self.interval = interval
        self.function = function
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


def _fake_timers(
    monkeypatch: pytest.MonkeyPatch, listener: event_handler.EventListener
) -> list[_FakeTimer]:
    made: list[_FakeTimer] = []

    def timer(name: str, interval: float, function: Callable) -> _FakeTimer:
        made.append(_FakeTimer(name, interval, function))
        return made[-1]

    monkeypatch.setattr(event_handler.threads, "timer", timer)
    monkeypatch.setattr(listener, "_device_update_timer", None)
    return made


def test_s25_several_plug_events_cause_one_update_after_0_2_s(
    monkeypatch: pytest.MonkeyPatch, event_listener: event_handler.EventListener
) -> None:
    """02 S25: each plug event restarts one 0.2 s wait; only the last
    one runs the device list update."""
    made = _fake_timers(monkeypatch, event_listener)
    stick = di.device_for_uuid(_STICK)
    for _ in range(3):
        event_listener._joystick_device_handler(stick, dill.DeviceActionType.Connected)
    assert [t.interval for t in made] == [0.2, 0.2, 0.2]
    assert [t.cancelled for t in made] == [True, True, False]
    assert made[-1].function == event_listener._run_device_list_update


def test_s26_plug_events_of_the_programs_own_xbox_pads_are_ignored(
    monkeypatch: pytest.MonkeyPatch, event_listener: event_handler.EventListener
) -> None:
    """02 S26: an own Xbox pad arriving starts no rescan."""
    made = _fake_timers(monkeypatch, event_listener)
    monkeypatch.setattr(event_handler, "is_vigem_xbox_summary", lambda data: True)
    stick = di.device_for_uuid(_STICK)
    event_listener._joystick_device_handler(stick, dill.DeviceActionType.Connected)
    assert made == []


def test_s27_devices_changed_is_said_only_when_the_list_changed(
    plugged: list, event_listener: event_handler.EventListener
) -> None:
    """02 S27: a rescan that finds the same devices says nothing; a stick
    plugged in or pulled out says "devices changed" once."""
    said: list[bool] = []

    def heard() -> None:
        said.append(True)

    event_listener.device_change_event.connect(heard)
    try:
        event_listener._run_device_list_update()
        assert said == []
        plugged.append(_copy_device(0, 0x6610, b"Plugged Stick"))
        event_listener._run_device_list_update()
        assert said == [True]
        event_listener._run_device_list_update()
        assert said == [True]
        plugged.pop()
        event_listener._run_device_list_update()
        assert said == [True, True]
    finally:
        event_listener.device_change_event.disconnect(heard)


def test_s36_a_failed_update_is_shown_and_the_old_list_stays(
    monkeypatch: pytest.MonkeyPatch,
    plugged: list,
    event_listener: event_handler.EventListener,
) -> None:
    """02 S36: a failed device update during play shows the error and keeps
    the old list; nothing else is told the devices changed."""
    shown: list[tuple] = []
    monkeypatch.setattr("gremlin.signal.display_error", lambda *a: shown.append(a))
    said: list[bool] = []

    def heard() -> None:
        said.append(True)

    before = [d.device_guid.uuid for d in di.joystick_devices()]
    plugged.append(_copy_device(0, 0x6611, b"Plugged Stick"))
    event_listener.device_change_event.connect(heard)
    try:
        with mock.patch.object(
            di, "joystick_devices_initialization",
            side_effect=error.GremlinError("vJoy failed"),
        ):
            event_listener._run_device_list_update()
    finally:
        event_listener.device_change_event.disconnect(heard)
    assert [d.device_guid.uuid for d in di.joystick_devices()] == before
    assert said == []
    assert shown and shown[0][0] == "The device list could not be updated."


def test_s33_the_page_moves_off_a_device_that_disappeared() -> None:
    """02 S33: the selected physical device gone: the page moves to the
    first physical device, or to the Logical tab when none is left."""
    from gremlin.ui.backend import UIState

    state = UIState()
    try:
        state.setCurrentRoom("devices")
        state.setCurrentTab("physical")
        state.setCurrentDevice(str(uuid.UUID(int=0x5151)))  # unplugged
        state._device_change()
        first = di.physical_devices()[0].device_guid.uuid
        assert state.property("currentDevice") == str(first).upper()
        assert state.property("currentTab") == "physical"

        state.setCurrentDevice(str(uuid.UUID(int=0x5151)))
        with mock.patch.object(di, "physical_devices", return_value=[]):
            state._device_change()
        assert state.property("currentTab") == "logical"
    finally:
        shiboken6.delete(state)


# --- E. Stick events, calibration, cached state ------------------------------


def test_s37_the_axis_calibration_is_applied_before_anything_sees_it(
    monkeypatch: pytest.MonkeyPatch, event_listener: event_handler.EventListener
) -> None:
    """02 S37: the event the rest of the program gets carries the
    calibrated value (and the cache keeps it)."""
    guid = dill.GUID.from_uuid(_STICK)
    monkeypatch.setattr(
        event_listener, "_calibrations", {(guid, 1): lambda raw: 0.25}
    )
    axis = input_cache.Joystick()[_STICK].axis(1)
    monkeypatch.setattr(axis, "_value", axis._value)
    monkeypatch.setattr(axis, "_seen", axis._seen)
    got: list[Event] = []

    def heard(event: Event) -> None:
        got.append(event)

    event_listener.joystick_event.connect(heard)
    try:
        event_listener._joystick_event_handler(_input(1, 1, 1234))
    finally:
        event_listener.joystick_event.disconnect(heard)
    assert len(got) == 1
    assert got[0].value == 0.25 and got[0].raw_value == 1234
    assert axis.value == 0.25


def test_s38_an_axis_without_calibration_is_centred_and_logged_once(
    monkeypatch: pytest.MonkeyPatch,
    event_listener: event_handler.EventListener,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """02 S38: no calibration data: the default centred calibration, and
    one Info line per axis."""
    monkeypatch.setattr(event_listener, "_calibrations", {})
    guid = dill.GUID(dill._GUID(
        Data1=0xF1A1, Data2=2, Data3=3, Data4=(9, 8, 7, 6, 5, 4, 3, 2)
    ))
    event = types.SimpleNamespace(device_guid=guid, input_index=7, value=16000)
    with caplog.at_level(logging.INFO, logger="system"):
        first = event_listener._apply_calibration(event)
        second = event_listener._apply_calibration(event)
    assert first == second == util.with_default_center_calibration(16000)
    lines = [r for r in caplog.records if "No calibration data" in r.getMessage()]
    assert len(lines) == 1 and lines[0].levelno == logging.INFO


def test_s39_calibration_is_reloaded_at_each_scan_and_for_one_saved_axis(
    monkeypatch: pytest.MonkeyPatch, event_listener: event_handler.EventListener
) -> None:
    """02 S39: every stick's axes get their calibration at a scan; after
    Calibration saves one axis only that axis is read again."""
    from gremlin.modules import calibration

    monkeypatch.setattr(
        calibration, "values_for_device", lambda uid, axis: (-1000, 0, 0, 1000, True)
    )
    monkeypatch.setattr(event_listener, "_calibrations", {})
    event_listener._init_joysticks()
    expected = {
        (dev.device_guid, entry.axis_index)
        for dev in di.joystick_devices() for entry in dev.axis_map
    }
    assert set(event_listener._calibrations) == expected
    guid = dill.GUID.from_uuid(_STICK)
    assert event_listener._calibrations[(guid, 1)](1000) == pytest.approx(1.0)

    monkeypatch.setattr(
        calibration, "values_for_device", lambda uid, axis: (-500, 0, 0, 500, True)
    )
    other = event_listener._calibrations[(guid, 2)]
    event_listener.reload_calibration(guid, 1)
    assert event_listener._calibrations[(guid, 1)](500) == pytest.approx(1.0)
    assert event_listener._calibrations[(guid, 2)] is other


def test_s41_the_last_value_of_every_stick_input_is_kept(
    monkeypatch: pytest.MonkeyPatch, event_listener: event_handler.EventListener
) -> None:
    """02 S41: buttons and hats keep their last state for scripts,
    conditions and refresh axes."""
    wrapper = input_cache.Joystick()[_STICK]
    button = wrapper.button(5)
    hat = wrapper.hat(1)
    monkeypatch.setattr(button, "_value", button._value)
    monkeypatch.setattr(hat, "_value", hat._value)
    event_listener._joystick_event_handler(_input(2, 5, 1))
    assert button.is_pressed is True
    event_listener._joystick_event_handler(_input(3, 1, 0))  # pushed north
    assert hat.direction == HatDirection.North
    event_listener._joystick_event_handler(_input(2, 5, 0))
    assert button.is_pressed is False


@pytest.mark.xfail(strict=True, reason=(
    "FINAL-02-1: the mode is stamped when the main thread handles the event "
    "(EventHandler.process_event, GL-065), not when it arrives (02 S40, D-02-Q8)"
))
def test_s40_an_event_keeps_the_mode_current_when_it_arrives(
    monkeypatch: pytest.MonkeyPatch, event_listener: event_handler.EventListener
) -> None:
    """02 S40 / D-02-Q8: a press that arrives in mode Flight runs in Flight,
    even when the mode changed before the main thread handles it."""
    mm = mode_manager.ModeManager()
    monkeypatch.setattr(mm, "_mode_stack", [mode_manager.Mode("Flight", None)])
    button = input_cache.Joystick()[_STICK].button(6)
    monkeypatch.setattr(button, "_value", button._value)
    got: list[Event] = []

    def heard(event: Event) -> None:
        got.append(event)

    event_listener.joystick_event.connect(heard)
    try:
        event_listener._joystick_event_handler(_input(2, 6, 1))  # arrives
    finally:
        event_listener.joystick_event.disconnect(heard)
    # Another event handled first changed the mode.
    monkeypatch.setattr(mm, "_mode_stack", [mode_manager.Mode("Landing", None)])
    handler = event_handler.EventHandler()
    monkeypatch.setattr(handler, "_matching_callbacks", lambda e: [])
    handler.process_event(got[0])
    assert got[0].mode == "Flight"


# --- G. Mouse ----------------------------------------------------------------


@pytest.fixture
def highlighting_kept() -> Iterator[None]:
    before = shared_state.suspend_input_highlighting()
    yield
    shared_state.set_suspend_input_highlighting(before)


@pytest.fixture
def mouse_hook_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    hook = windows_event_hook.MouseHook()
    calls: list[str] = []
    monkeypatch.setattr(hook, "_users", 0)
    monkeypatch.setattr(hook, "start", lambda: calls.append("start"))
    monkeypatch.setattr(hook, "stop", lambda: calls.append("stop"))
    return calls


def _listen(kinds: list[InputType], several: bool = False) -> tuple[Any, list]:  # noqa: ANN401
    from gremlin.ui.util import InputListenerModel

    model = InputListenerModel()
    done: list[list] = []
    model.listeningTerminated.connect(lambda inputs: done.append(list(inputs)))
    model.setProperty("eventTypes", [InputType.to_string(k) for k in kinds])
    model.setProperty("multipleInputs", several)
    model.setProperty("enabled", True)
    return model, done


def test_s51_the_mouse_is_hooked_only_while_listen_asks_for_it(
    highlighting_kept: None, mouse_hook_calls: list[str]
) -> None:
    """02 S51: Listen for stick buttons hooks no mouse; Listen for the
    mouse hooks it and unhooks it afterwards."""
    model, _done = _listen([InputType.JoystickButton])
    model.setProperty("enabled", False)
    assert mouse_hook_calls == []
    model, _done = _listen([InputType.Mouse])
    assert mouse_hook_calls == ["start"]
    model.setProperty("enabled", False)
    assert mouse_hook_calls == ["start", "stop"]


# --- I. Listen for input -----------------------------------------------------


def test_s62_listen_takes_an_axis_only_after_a_big_enough_move(
    highlighting_kept: None,
) -> None:
    """02 S62: a small axis move is not the input; a big one is."""
    from gremlin import device_helpers

    significant = device_helpers.JoystickInputSignificant()
    significant.reset()
    model, done = _listen([InputType.JoystickAxis])
    try:
        for value in (0.0, 0.1, 0.2):
            model._joy_event_cb(Event(
                InputType.JoystickAxis, 1, _STICK, "Default", value=value
            ))
        assert done == []
        model._joy_event_cb(Event(
            InputType.JoystickAxis, 1, _STICK, "Default", value=0.7
        ))
        assert [[e.identifier for e in d] for d in done] == [[1]]
    finally:
        model.setProperty("enabled", False)
        significant.reset()


@pytest.mark.filterwarnings("ignore:libpyside. Failed to disconnect:RuntimeWarning")
def test_s65_highlighting_pauses_while_a_macro_records(
    highlighting_kept: None,
) -> None:
    """02 S65 (macro part; the Listen part is test_stage1_app_profile::
    test_listen_single_input_ends_at_the_first_press)."""
    from gremlin.ui.util import MacroRecorder

    shared_state.set_suspend_input_highlighting(False)
    recorder = MacroRecorder(lambda action: None)
    recorder.start([InputType.JoystickButton], False)
    try:
        assert shared_state.suspend_input_highlighting()
    finally:
        recorder.stop()
    assert not shared_state.suspend_input_highlighting()


# --- H. Routing to the profile (EventHandler) --------------------------------


@pytest.fixture
def handler() -> Iterator[Any]:
    """An EventHandler of its own (not the program's one)."""
    own = event_handler.EventHandler.klass()
    yield own
    shiboken6.delete(own)


def _press(number: int, mode: str) -> Event:
    return Event(InputType.JoystickButton, number, _STICK, mode, is_pressed=True)


def test_s54_a_child_mode_uses_its_parents_actions_for_empty_inputs(
    handler: Any,  # noqa: ANN401
) -> None:
    """02 S54: every action of an input in the current mode runs; a child
    (and its child) mode uses the parent's actions where it has none."""
    ran: list[str] = []
    default = TreeNode("Default")
    flight = TreeNode("Flight", default)
    combat = TreeNode("Combat", flight)
    handler.add_callback(_STICK, "Default", _press(1, "Default"),
                         lambda e: ran.append("default 1a"))
    handler.add_callback(_STICK, "Default", _press(1, "Default"),
                         lambda e: ran.append("default 1b"))
    handler.add_callback(_STICK, "Default", _press(2, "Default"),
                         lambda e: ran.append("default 2"))
    handler.add_callback(_STICK, "Flight", _press(2, "Flight"),
                         lambda e: ran.append("flight 2"))
    handler.build_event_lookup([default, flight, combat])
    assert handler.known_modes == {"Default", "Flight", "Combat"}

    handler.process_event(_press(1, "Combat"))
    assert ran == ["default 1a", "default 1b"]
    ran.clear()
    handler.process_event(_press(2, "Combat"))
    assert ran == ["flight 2"]
    ran.clear()
    handler.process_event(_press(2, "Default"))
    assert ran == ["default 2"]


def test_s59_renaming_a_running_mode_moves_its_actions_deleting_drops_them(
    handler: Any,  # noqa: ANN401
) -> None:
    """02 S59."""
    ran: list[str] = []
    handler.add_callback(_STICK, "Flight", _press(1, "Flight"),
                         lambda e: ran.append("flight"))
    handler.build_event_lookup([TreeNode("Default"), TreeNode("Flight")])
    handler.rename_mode("Flight", "Cruise")
    assert "Cruise" in handler.known_modes and "Flight" not in handler.known_modes
    handler.process_event(_press(1, "Cruise"))
    assert ran == ["flight"]
    handler.process_event(_press(1, "Flight"))
    assert ran == ["flight"]
    handler.drop_mode("Cruise")
    handler.process_event(_press(1, "Cruise"))
    assert ran == ["flight"] and "Cruise" not in handler.known_modes


def test_s60_stop_removes_every_action_and_the_running_mode_list(
    handler: Any,  # noqa: ANN401
) -> None:
    """02 S60: EventHandler.clear, as Stop calls it."""
    ran: list[str] = []
    handler.add_callback(_STICK, "Default", _press(1, "Default"),
                         lambda e: ran.append("x"))
    handler.build_event_lookup([TreeNode("Default")])
    handler.clear()
    handler.process_event(_press(1, "Default"))
    assert ran == [] and handler.callbacks == {} and handler.known_modes == set()


# --- J. HidHide --------------------------------------------------------------

_HH_KEYS = [
    ("display", "hidhide", name)
    for name in ("games", "photos", "module-links", "list-mode", "hidden-devices",
                 "cloak", "managed", "gaming-only")
] + [("global", "general", "hidhide-on-start")]
# The values a new install starts with.
_HH_NEW = {
    "games": "[]", "photos": "{}", "module-links": "{}", "list-mode": "",
    "hidden-devices": "", "cloak": "", "managed": "", "gaming-only": "",
    "hidhide-on-start": False,
}
_ROW = r"HID\VID_1234&PID_0001\1"


class _Driver:
    """The HidHide driver, stood in for: what it holds and what it was told."""

    def __init__(self) -> None:
        self.present = True
        self.accept = True
        self.active = False
        self.inverse = False
        self.blacklist: list[str] = []
        self.whitelist: list[str] | None = None
        self.writes: list[tuple] = []
        self.gaming_only: list[bool] = []
        self.rows: list[dict] = []

    def set_active(self, on: bool) -> bool:
        self.writes.append(("active", on))
        if self.accept:
            self.active = on
        return self.accept

    def set_inverse(self, on: bool) -> bool:
        self.writes.append(("inverse", on))
        if self.accept:
            self.inverse = on
        return self.accept

    def set_blacklist(self, ids: list[str]) -> bool:
        self.writes.append(("blacklist", list(ids)))
        if self.accept:
            self.blacklist = list(ids)
        return self.accept

    def set_whitelist(self, paths: list[str]) -> bool:
        self.writes.append(("whitelist", list(paths)))
        self.whitelist = list(paths)
        return True

    def list_hid_devices(self, gaming_only: bool) -> list[dict]:
        self.gaming_only.append(gaming_only)
        return [dict(row) for row in self.rows]


@pytest.fixture
def hidhide(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Driver]:
    """A fake HidHide driver; the HidHide settings start as on a new
    install and are put back afterwards."""
    from gremlin import hidhide_driver
    from gremlin.ui import hidhide as hh

    hh._ensure_options()
    cfg = Configuration()
    kept = {key: cfg.value(*key) for key in _HH_KEYS}
    for key in _HH_KEYS:
        cfg.set(*key, _HH_NEW[key[2]])
    driver = _Driver()
    monkeypatch.setattr(hh, "driver_present", lambda: driver.present)
    monkeypatch.setattr(hh, "driver_version", lambda: "1.5")
    monkeypatch.setattr(hh, "get_active", lambda: driver.active)
    monkeypatch.setattr(hh, "set_active", driver.set_active)
    monkeypatch.setattr(hh, "get_inverse", lambda: driver.inverse)
    monkeypatch.setattr(hh, "set_inverse", driver.set_inverse)
    monkeypatch.setattr(hh, "get_blacklist", lambda: list(driver.blacklist))
    monkeypatch.setattr(hh, "set_blacklist", driver.set_blacklist)
    monkeypatch.setattr(hh, "set_whitelist", driver.set_whitelist)
    monkeypatch.setattr(hh, "list_hid_devices", driver.list_hid_devices)
    monkeypatch.setattr(hh, "_enrich_devices", lambda rows: rows)
    monkeypatch.setattr(hh, "_gremlin_exe", lambda: "C:/Gremlin/gremlin.exe")
    monkeypatch.setattr(hh, "_full_image_name", lambda path: f"IMG:{path}")
    monkeypatch.setattr(hidhide_driver, "last_error", lambda: "The driver said no.")
    monkeypatch.setattr(hh, "_settings_error", "")
    try:
        yield driver
    finally:
        for key, value in kept.items():
            cfg.set(*key, value)


@pytest.fixture
def hidhide_window(hidhide: _Driver) -> Iterator[Any]:
    from gremlin.ui import hidhide as hh

    model = hh.HidHideModel()
    yield model
    shiboken6.delete(model)


def _hh_value(name: str) -> object:
    return Configuration().value("display", "hidhide", name)


def test_s72_a_new_install_has_every_switch_off_and_hides_nothing(
    hidhide: _Driver, hidhide_window: Any  # noqa: ANN401
) -> None:
    """02 S72: every switch off; the window changes nothing in the driver;
    taking control of a new install writes an empty device list."""
    page = hidhide_window
    assert page.property("installed") is True
    for name in ("gremlinControl", "cloakOn", "inverseOn", "startOn", "gamingOnly"):
        assert page.property(name) is False, name
    assert hidhide.writes == []
    assert page.setGremlinControl(True) is True
    assert ("blacklist", []) in hidhide.writes
    assert hidhide.blacklist == [] and hidhide.active is False


def test_s68_nothing_changes_in_hidhide_until_the_program_controls_it(
    hidhide: _Driver, hidhide_window: Any  # noqa: ANN401
) -> None:
    """02 S68: with "Gremlin-Platforms controls HidHide" off, Enabled, the
    list mode and device ticks are refused and the driver is not called."""
    page = hidhide_window
    assert page.setCloak(True) is False
    assert page.setInverse(True) is False
    assert page.setDeviceHidden(_ROW, True) is False
    assert hidhide.writes == []
    assert _hh_value("hidden-devices") == ""


def test_s69_turning_control_off_leaves_hidhide_as_it_is(
    hidhide: _Driver, hidhide_window: Any  # noqa: ANN401
) -> None:
    """02 S69: devices stay hidden and HidHide stays on."""
    page = hidhide_window
    page.setGremlinControl(True)
    assert page.setCloak(True) and page.setDeviceHidden(_ROW, True)
    writes = len(hidhide.writes)
    assert page.setGremlinControl(False) is True
    assert hidhide.writes[writes:] == []
    assert hidhide.active is True and hidhide.blacklist == [_ROW]
    assert page.property("gremlinControl") is False


def test_s70_hidhide_enabled_flips_back_with_the_error_when_refused(
    hidhide: _Driver, hidhide_window: Any  # noqa: ANN401
) -> None:
    """02 S70."""
    page = hidhide_window
    page.setGremlinControl(True)
    hidhide.accept = False
    assert page.setCloak(True) is False
    assert page.property("cloakOn") is False
    assert page.property("lastError") == "The driver said no."
    assert _hh_value("cloak") != "on"
    hidhide.accept = True
    assert page.setCloak(True) is True
    assert page.property("cloakOn") is True and hidhide.active is True
    assert page.property("lastError") == ""
    assert page.setCloak(False) is True and hidhide.active is False


def test_s71_automatically_start_takes_control_turns_on_and_writes_the_lists(
    hidhide: _Driver,
) -> None:
    """02 S71: at start, with Automatically Start on."""
    from gremlin.ui import hidhide as hh

    cfg = Configuration()
    cfg.set("global", "general", "hidhide-on-start", True)
    cfg.set("display", "hidhide", "hidden-devices", json.dumps([_ROW]))
    cfg.set("display", "hidhide", "games", json.dumps(
        [{"name": "Game", "path": "C:/Games/game.exe"}]
    ))
    hh.apply_on_start()
    assert hh._hidhide_managed() is True
    assert _hh_value("cloak") == "on"
    assert hidhide.active is True
    assert hidhide.blacklist == [_ROW]
    assert hidhide.whitelist == ["IMG:C:/Games/game.exe", "IMG:C:/Gremlin/gremlin.exe"]


def test_s71_with_automatically_start_off_nothing_is_written(hidhide: _Driver) -> None:
    from gremlin.ui import hidhide as hh

    hh.apply_on_start()
    assert hidhide.writes == [] and hh._hidhide_managed() is False


def test_s74_a_device_hidden_in_the_driver_is_marked_hidden(
    hidhide: _Driver,
) -> None:
    """02 S74 (the model's part; the dimmed HIDDEN look is hands-on)."""
    from gremlin.ui import hidhide as hh

    hidhide.rows = [
        {"instanceId": _ROW, "name": "Stick A"},
        {"instanceId": r"HID\VID_1234&PID_0002\1", "name": "Stick B"},
    ]
    hidhide.blacklist = [_ROW]
    page = hh.HidHideModel()
    try:
        rows = {page.deviceAt(i)["name"]: page.deviceAt(i)["hidden"]
                for i in range(page.property("deviceCount"))}
    finally:
        shiboken6.delete(page)
    assert rows == {"Stick A": True, "Stick B": False}


def test_s75_gaming_devices_only_asks_for_game_controllers(
    hidhide: _Driver, hidhide_window: Any  # noqa: ANN401
) -> None:
    """02 S75: the switch is kept and the list is read again, game
    controllers only."""
    page = hidhide_window
    assert hidhide.gaming_only[-1] is False
    page.setGamingOnly(True)
    assert hidhide.gaming_only[-1] is True
    assert page.property("gamingOnly") is True and _hh_value("gaming-only") == "on"


def test_s76_allow_list_adds_the_program_block_list_never_blocks_it(
    hidhide: _Driver,
) -> None:
    """02 S76: Allow list: the listed programs and the program itself see
    hidden devices. Block list: the listed programs don't, and the program
    itself is never on it."""
    from gremlin.ui import hidhide as hh

    cfg = Configuration()
    cfg.set("display", "hidhide", "managed", "yes")
    cfg.set("display", "hidhide", "games", json.dumps([
        {"name": "Game", "path": "C:/Games/game.exe"},
        {"name": "Gremlin", "path": "C:/Gremlin/gremlin.exe"},
    ]))
    cfg.set("display", "hidhide", "list-mode", "allow")
    hh.apply_saved_list()
    assert hidhide.inverse is False
    assert hidhide.whitelist == ["IMG:C:/Games/game.exe", "IMG:C:/Gremlin/gremlin.exe"]

    cfg.set("display", "hidhide", "list-mode", "block")
    hh.apply_saved_list()
    assert hidhide.inverse is True
    assert hidhide.whitelist == ["IMG:C:/Games/game.exe"]


def test_s67_s77_get_hidhide_and_test_hidhide_open_the_right_places(
    monkeypatch: pytest.MonkeyPatch, hidhide: _Driver
) -> None:
    """02 S67 (without the driver: not installed, Get HidHide opens the
    Nefarius releases page) and S77 (Test HidHide opens Windows Game
    Controllers)."""
    from PySide6 import QtGui

    from gremlin.ui import hidhide as hh

    hidhide.present = False
    page = hh.HidHideModel()
    opened: list[str] = []
    started: list[list[str]] = []
    monkeypatch.setattr(
        QtGui.QDesktopServices, "openUrl", lambda url: opened.append(url.toString())
    )
    monkeypatch.setattr(
        subprocess, "Popen", lambda args, **kw: started.append(list(args))
    )
    try:
        assert page.property("installed") is False
        assert page.setGremlinControl(True) is False
        page.openDownload()
        page.openGameControllers()
    finally:
        shiboken6.delete(page)
    assert opened == ["https://github.com/nefarius/HidHide/releases"]
    assert len(started) == 1 and "joy.cpl" in started[0]
    assert hidhide.writes == []


def test_s78_a_setting_that_cant_be_saved_shows_in_the_window(
    hidhide: _Driver, hidhide_window: Any  # noqa: ANN401
) -> None:
    """02 S78."""
    page = hidhide_window
    cfg = Configuration()

    with mock.patch.object(cfg, "set", side_effect=OSError("disk full")):
        page.setGamingOnly(True)
    assert "Could not save the HidHide settings" in page.property("lastError")
    assert "disk full" in page.property("lastError")


def test_s83_hidhide_choices_are_in_history_window_size_and_links_are_not(
    hidhide: _Driver,
) -> None:
    """02 S83: what History compares for the settings."""
    view = Configuration()._settings_view()
    for name in ("games", "list-mode", "hidden-devices", "cloak", "managed",
                 "gaming-only", "photos"):
        assert f"display/hidhide/{name}" in view, name
    for name in ("window-width", "window-height", "split-ratio", "module-links"):
        assert f"display/hidhide/{name}" not in view, name


# --- K. Foreground program and auto-load -------------------------------------


class _Steps:
    """A stop request for the monitor loop: set after n rounds, and its
    wait returns at once (no real second passes)."""

    def __init__(self, rounds: int) -> None:
        self.left = rounds

    def is_set(self) -> bool:
        return self.left <= 0

    def wait(self, timeout: float) -> bool:
        self.left -= 1
        return self.left <= 0


def test_s86_a_program_that_cant_be_read_is_not_announced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """02 S86: a program run as administrator (path unreadable) is not
    announced as the previous one again."""
    from gremlin import process_monitor

    pids = iter([10, 20, 30])
    monkeypatch.setattr(process_monitor.win32gui, "GetForegroundWindow", lambda: 1)
    monkeypatch.setattr(
        process_monitor.win32process, "GetWindowThreadProcessId",
        lambda hwnd: (0, next(pids)),
    )
    monitor = process_monitor.ProcessMonitor()
    paths = {10: "C:/Games/a.exe", 20: "", 30: "C:/Games/c.exe"}
    monkeypatch.setattr(monitor, "_image_path", lambda pid: paths[pid])
    heard: list[str] = []
    monitor.process_changed.connect(heard.append)
    try:
        monitor._update(_Steps(3))  # type: ignore[arg-type]
    finally:
        shiboken6.delete(monitor)
    assert heard == ["C:/Games/a.exe", "C:/Games/c.exe"]


def _autoload_backend(
    auto_load: bool, open_path: str, running: bool, calls: list
) -> types.SimpleNamespace:
    settings = {
        ("profile", "automation", "enable-auto-loading"): auto_load,
        ("profile", "automation", "remain-active-on-focus-loss"): False,
    }
    return types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *key: settings[key]),
        profile=types.SimpleNamespace(
            fpath=open_path, has_unsaved_changes=lambda: False
        ),
        gremlinActive=running,
        _autoload_held=None,
        activate_gremlin=lambda on: calls.append(("active", on)),
        loadProfile=lambda path: calls.append(("load", path)),
    )


def test_s84_auto_load_loads_and_runs_the_programs_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """02 S84: with "Load profiles automatically" on, the program's chosen
    profile is loaded and run when it gets focus; off, nothing happens."""
    from gremlin.ui import backend

    game = tmp_path / "game.xml"
    game.write_text("<profile/>", encoding="utf-8")
    monkeypatch.setattr(backend.config, "get_profile_with_regex", lambda p: str(game))
    callback = backend.Backend.klass._active_process_changed_cb

    calls: list = []
    callback(_autoload_backend(True, str(tmp_path / "open.xml"), False, calls),
             "C:/Games/game.exe")
    assert calls == [("active", False), ("load", str(game)), ("active", True)]

    calls.clear()
    callback(_autoload_backend(False, str(tmp_path / "open.xml"), False, calls),
             "C:/Games/game.exe")
    assert calls == []


# --- L. Safety, start and exit -----------------------------------------------


def test_s93_the_listener_stops_its_timer_hooks_and_driver_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """02 S93 (listener part): terminate cancels the hot-plug timer, stops
    both hooks and swaps the driver callbacks for ones that do nothing."""
    fake = dill.DILL._dll
    monkeypatch.setattr(fake, "input_event_callback", fake.input_event_callback)
    monkeypatch.setattr(fake, "device_change_callback", fake.device_change_callback)
    stopped: list[str] = []
    timer = _FakeTimer("device list update", 0.2, lambda: None)
    listener = types.SimpleNamespace(
        _running=True,
        _stop_event=threading.Event(),
        _device_update_timer=timer,
        keyboard_hook=types.SimpleNamespace(stop=lambda: stopped.append("keyboard")),
        mouse_hook=types.SimpleNamespace(stop=lambda: stopped.append("mouse")),
    )
    event_handler.EventListener.klass.terminate(listener)  # type: ignore[arg-type]
    assert timer.cancelled and listener._device_update_timer is None
    assert stopped == ["keyboard", "mouse"]
    assert listener._stop_event.is_set() and listener._running is False
    assert fake.input_event_callback is not None
    # Callbacks that do nothing (the listener's own would cache and emit).
    assert fake.input_event_callback(_input(2, 1, 1)) is None
    assert fake.device_change_callback(dill._DeviceSummary(), 1) is None


def test_s93_exit_stops_the_listener_the_run_and_the_process_monitor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """02 S93 (exit part): shutdown_cleanup stops the listener, the Run and
    the process monitor, which waits at most 2 s for its thread."""
    import joystick_gremlin
    from gremlin import process_monitor
    from gremlin.modules import output
    from gremlin.ui import backend

    steps: list[object] = []
    monitor = process_monitor.ProcessMonitor()
    monkeypatch.setattr(
        monitor, "_update_thread",
        types.SimpleNamespace(join=lambda timeout: steps.append(("join", timeout))),
    )
    monkeypatch.setattr(joystick_gremlin, "_shutdown_done", False)
    monkeypatch.setattr(
        event_handler.EventListener, "instance",
        types.SimpleNamespace(terminate=lambda: steps.append("terminate")),
    )
    monkeypatch.setattr(
        backend.Backend, "instance",
        types.SimpleNamespace(
            activate_gremlin=lambda on: steps.append(("run", on)),
            process_monitor=monitor,
        ),
    )
    monkeypatch.setattr(output, "reset_drivers", lambda: steps.append("drivers"))
    try:
        joystick_gremlin.shutdown_cleanup()
    finally:
        shiboken6.delete(monitor)
    assert steps == ["terminate", ("run", False), ("join", 2.0), "drivers"]
