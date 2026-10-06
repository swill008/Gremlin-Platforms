# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""What a Run starts is registered with run_scope and let go at Stop (map 3,
batch 1, the callers).

- Tempo, Double Tap and Smart Toggle timers never fire after Stop (GL-047).
- A macro that ends early lets go of its keys at once; the relative axis
  loops end with their Run and a new loop never waits for the old one on
  the main thread (GL-048, GL-061).
- Keys a script sends during a Run are released at Stop; keys sent with no
  Run on are left alone (GL-049, decision R4).
- Mouse buttons are held in the same one list (GL-064).
- Logical Device values go back to neutral, and change under one lock
  (GL-050, GL-059); the vJoy device list opens each device once (GL-059).
- Sound and speech asked for with no Run on are ignored (GL-058).
- An empty Logical Device: a new macro step creates nothing (GL-108).
- A removed Chain sequence leaves the library (GL-103).

No real input reaches the PC (test/fake_input.py); timers run on Qt's
event loop here.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import keyboard, macro, run_scope, sendinput, threads
from gremlin.keyboard import key_from_name
from gremlin.logical_device import LogicalDevice
from gremlin.types import HatDirection, InputType, MouseButton


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


@pytest.fixture(autouse=True)
def _scope() -> Iterator[None]:
    """Each test starts with no Run and leaves none behind."""
    run_scope._reset_for_tests()
    yield
    run_scope.stop()
    run_scope._reset_for_tests()


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    """Runs Qt events until check() is True (or seconds pass)."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return False


def _after_main_timers(seconds: float) -> bool:
    """Runs Qt events until a main-thread timer set now for seconds fired."""
    done: list[bool] = []
    sentinel = threads.main_timer("test sentinel", seconds, lambda: done.append(True))
    try:
        return _wait_for(lambda: bool(done))
    finally:
        sentinel.cancel()


# --- GL-047: Tempo, Double Tap and Smart Toggle timers ------------------------


def _functor(plugin: str, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list]:
    import importlib

    module = importlib.import_module(f"action_plugins.{plugin}")
    name = {
        "tempo": "Tempo",
        "double_tap": "DoubleTap",
        "smart_toggle": "SmartToggle",
    }[plugin]
    fired: list[str] = []
    functor_class = getattr(module, f"{name}Functor")
    monkeypatch.setattr(functor_class, "_timeout", lambda self: fired.append(plugin))
    data = getattr(module, f"{name}Data")(InputType.JoystickButton)
    if hasattr(data, "threshold"):
        data.threshold = 0.05
    if hasattr(data, "delay"):
        data.delay = 0.05
    return functor_class(data), fired


@pytest.mark.parametrize("plugin", ["tempo", "double_tap", "smart_toggle"])
def test_a_timer_fires_while_its_run_is_on(
    plugin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_scope.begin()
    functor, fired = _functor(plugin, monkeypatch)
    functor._start_timer()
    assert _after_main_timers(0.2)
    assert fired == [plugin]


@pytest.mark.parametrize("plugin", ["tempo", "double_tap", "smart_toggle"])
def test_a_timer_never_fires_after_stop(
    plugin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_scope.begin()
    functor, fired = _functor(plugin, monkeypatch)
    functor._start_timer()
    assert run_scope.pending_timers()  # registered with the Run
    run_scope.stop()  # before it fires (the Stop button or quitting)
    assert _after_main_timers(0.2)
    assert fired == []
    assert run_scope.pending_timers() == []


# --- GL-049 / GL-064: keys and mouse buttons held in one place ----------------


@pytest.fixture
def key_events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, bool]]:
    """Key output as (scan code, is_pressed), in order."""
    sent: list[tuple[int, bool]] = []

    def record(_vk: int, scan: int, flags: int, _extra: int = 0) -> None:
        sent.append((scan, not flags & 0x0002))  # KEYEVENTF_KEYUP

    monkeypatch.setattr(keyboard.win32api, "keybd_event", record)
    return sent


def test_a_key_a_script_holds_is_released_at_stop(
    key_events: list[tuple[int, bool]],
) -> None:
    key = key_from_name("a")
    run_scope.begin()
    keyboard.send_key_down(key)  # a script presses and never lets go
    run_scope.stop()
    assert key_events == [(key.scan_code, True), (key.scan_code, False)]
    run_scope.stop()  # a second Stop (quit after Stop) sends nothing more
    assert len(key_events) == 2


def test_a_key_let_go_before_stop_is_not_sent_up_again(
    key_events: list[tuple[int, bool]],
) -> None:
    key = key_from_name("a")
    run_scope.begin()
    keyboard.send_key_down(key)
    keyboard.send_key_up(key)
    run_scope.stop()
    assert key_events == [(key.scan_code, True), (key.scan_code, False)]


def test_keys_sent_with_no_run_on_are_left_alone(
    key_events: list[tuple[int, bool]],
) -> None:
    keyboard.send_key_down(key_from_name("a"))  # decision R4
    assert run_scope.held() == []
    run_scope.begin()
    run_scope.stop()
    assert len(key_events) == 1


def test_a_mouse_button_held_at_stop_is_released(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flags: list[int] = []

    def record(*inputs: Any) -> int:  # noqa: ANN401
        flags.extend(item.union.mi.dwFlags for item in inputs)
        return len(inputs)

    monkeypatch.setattr(sendinput, "_send_input", record)
    run_scope.begin()
    sendinput.mouse_press(MouseButton.Left)
    assert run_scope.held() == [("mouse", MouseButton.Left)]
    run_scope.stop()
    assert flags == [sendinput.MOUSEEVENTF_LEFTDOWN, sendinput.MOUSEEVENTF_LEFTUP]
    assert not hasattr(sendinput, "_held_buttons")  # one list: run_scope's
    assert not hasattr(macro, "_held_keys")


# --- GL-048: a macro that ends early -----------------------------------------


def test_a_macro_that_ends_early_lets_go_of_its_keys_at_once(
    key_events: list[tuple[int, bool]],
) -> None:
    key = key_from_name("a")

    class Fails:
        def __call__(self) -> None:
            raise RuntimeError("a step that fails")

    run_scope.begin()
    manager = macro.MacroManager()
    manager.start()
    try:
        held = macro.Macro()
        held.press(key)
        held.sequence.append(Fails())  # the macro ends before its release
        held.release(key)
        manager.queue_macro(held)
        assert _wait_for(lambda: (key.scan_code, False) in key_events)
        # Let go of when the macro ended, while the Run goes on (it used to
        # stay down until Stop).
        assert run_scope.running()
        assert key_events == [(key.scan_code, True), (key.scan_code, False)]
        assert run_scope.held() == []
    finally:
        manager.stop()


def test_a_macro_that_finishes_keeps_what_it_pressed_down(
    key_events: list[tuple[int, bool]],
) -> None:
    # Map to Keyboard: the press macro ends with the key down on purpose.
    key = key_from_name("a")
    run_scope.begin()
    manager = macro.MacroManager()
    manager.start()
    try:
        press = macro.Macro()
        press.press(key)
        manager.queue_macro(press)
        assert _wait_for(lambda: press.id not in manager._scheduled_macro)
        assert _wait_for(lambda: key_events == [(key.scan_code, True)])
        assert run_scope.held() == [("key", (key.scan_code, key.is_extended))]
    finally:
        manager.stop()
    run_scope.stop()
    assert key_events == [(key.scan_code, True), (key.scan_code, False)]


# --- GL-048 / GL-061: relative axis loops -------------------------------------


@pytest.fixture
def vjoy_axis(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    from gremlin.modules import output

    state = SimpleNamespace(value=0.0, writes=0)

    def write(_vid: int, _kind: str, _aid: int, value: float) -> bool:
        state.value = value
        state.writes += 1
        return True

    monkeypatch.setattr(output, "vjoy_value", lambda *_a: state.value)
    monkeypatch.setattr(output, "vjoy_owned", lambda *_a: True)
    monkeypatch.setattr(output, "write_vjoy", write)
    return state


def _vjoy_relative() -> Any:  # noqa: ANN401
    from action_plugins.map_to_vjoy import MapToVjoyData, MapToVjoyFunctor
    from gremlin.types import AxisMode

    data = MapToVjoyData(InputType.JoystickAxis)
    data.axis_mode = AxisMode.Relative
    data.vjoy_device_id = 1
    data.vjoy_input_id = 1
    functor = MapToVjoyFunctor(data)
    functor.axis_delta_value = 0.001
    return functor


def test_the_vjoy_relative_loop_ends_with_stop_and_run_again(
    vjoy_axis: SimpleNamespace,
) -> None:
    run_scope.begin()
    functor = _vjoy_relative()
    functor._start_loop()
    try:
        assert _wait_for(lambda: vjoy_axis.writes > 3)
        thread = functor.thread
        run_scope.stop()
        run_scope.begin()  # Stop and Run again at once
        assert _wait_for(lambda: not thread.is_alive())
        writes = vjoy_axis.writes
        time.sleep(0.1)
        # It used to go on moving the axis in the new Run.
        assert vjoy_axis.writes == writes
    finally:
        functor.thread_running = False
        functor.thread.join(timeout=2.0)


@pytest.mark.parametrize("plugin", ["map_to_vjoy", "map_to_logical_device"])
def test_a_new_loop_does_not_wait_for_the_old_one(
    plugin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    module = importlib.import_module(f"action_plugins.{plugin}")
    name = {
        "map_to_vjoy": "MapToVjoyFunctor",
        "map_to_logical_device": "MapToLogicalDeviceFunctor",
    }[plugin]
    functor = object.__new__(getattr(module, name))
    stuck = threading.Event()
    started: list[tuple] = []
    monkeypatch.setattr(
        functor,
        "relative_axis_thread",
        lambda run, token: started.append((run, token)) or stuck.wait(2.0),
        raising=False,
    )
    functor.thread_running = False
    run_scope.begin()
    functor._start_loop()
    old = functor.thread
    functor.thread_running = False  # released: the old loop is ending
    begin = time.monotonic()
    functor._start_loop()  # moved again at once
    try:
        # It used to join the old loop on the main thread (up to 1 s).
        assert time.monotonic() - begin < 0.5
        assert functor.thread is not old
        assert _wait_for(lambda: len(started) == 2)
        old_token, new_token = started[0][1], started[1][1]
        assert not functor._current(started[0][0], old_token)  # the old ends
        assert functor._current(started[1][0], new_token)
    finally:
        stuck.set()
        functor.thread_running = False
        old.join(timeout=2.0)
        functor.thread.join(timeout=2.0)


# --- GL-050 / GL-059: Logical Device values -----------------------------------


@pytest.fixture
def logical() -> Iterator[LogicalDevice]:
    ld = LogicalDevice()
    saved = (ld._inputs, ld._label_lookup, ld._groups, ld._order)
    ld.reset()
    yield ld
    ld._inputs, ld._label_lookup, ld._groups, ld._order = saved


def test_logical_device_values_go_back_to_neutral(logical: LogicalDevice) -> None:
    axis = logical.create(InputType.JoystickAxis)
    button = logical.create(InputType.JoystickButton)
    hat = logical.create(InputType.JoystickHat)
    axis.update(0.7)
    button.update(True)
    hat.update(HatDirection.North)
    logical.reset_values()
    assert axis.value == 0.0
    assert button.is_pressed is False
    assert hat.direction == HatDirection.Center
    assert len(logical.inputs_of_type()) == 3  # the controls stay


def test_relative_steps_from_two_threads_add_up(logical: LogicalDevice) -> None:
    axis = logical.create(InputType.JoystickAxis)

    def nudge() -> None:
        for _ in range(500):
            axis.nudge(0.0001)

    workers = [threading.Thread(target=nudge) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=5.0)
    assert axis.value == pytest.approx(0.2)
    axis.nudge(5.0)
    assert axis.value == 1.0  # kept in -1..1


def test_two_threads_opening_one_vjoy_device_get_the_same_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vjoy import vjoy

    made: list[int] = []

    class FakeVJoy:
        def __init__(self, index: int) -> None:
            time.sleep(0.05)  # a slow driver call: the other thread comes in
            made.append(index)

        def invalidate(self) -> None:
            pass

    monkeypatch.setattr(vjoy, "VJoy", FakeVJoy)
    monkeypatch.setattr(vjoy.VJoyProxy, "vjoy_devices", {})
    got: list[object] = []
    workers = [
        threading.Thread(target=lambda: got.append(vjoy.VJoyProxy()[7]))
        for _ in range(4)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=5.0)
    assert made == [7]
    assert len(got) == 4 and all(device is got[0] for device in got)
    vjoy.VJoyProxy.reset()
    assert vjoy.VJoyProxy.vjoy_devices == {}


# --- GL-058: sound and speech with no Run on ----------------------------------


def test_a_sound_asked_for_with_no_run_on_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import audio_player

    player = object.__new__(audio_player.AudioPlayer)
    player.__init__()
    player.enqueue("late.wav", 50)  # a late timer after Stop
    assert player._play_list == []


def test_speech_asked_for_with_no_run_on_is_dropped() -> None:
    from gremlin import tts

    manager = object.__new__(tts.TTSManager)
    manager.__init__()
    manager._engine = SimpleNamespace(stop=lambda: None)  # no real engine
    manager.enqueue(
        tts.TTSRequest("late", 1.0, 0.0, 0.0), tts.TTSQueueMode.QueueBack
    )
    assert list(manager._queue) == []


# --- GL-108: no hidden Logical Device control --------------------------------


def test_a_new_macro_step_on_an_empty_logical_device_creates_nothing(
    logical: LogicalDevice,
) -> None:
    step = macro.LogicalDeviceAction.create()
    assert logical.inputs_of_type() == []  # it used to add Button 1
    assert not step.is_valid()  # not saved until a control is chosen
    step()  # playing it does nothing (no error)


# --- GL-103: a removed Chain sequence leaves the library ---------------------


def test_a_removed_chain_sequence_is_released_from_the_library() -> None:
    from action_plugins.chain import ChainModel

    released: list[list] = []
    first, second = [object()], [object(), object()]
    model = SimpleNamespace(
        _data=SimpleNamespace(chain_sequences=[first, second]),
        library=SimpleNamespace(release=released.append),
        changed=SimpleNamespace(emit=lambda: None),
        _binding_model=SimpleNamespace(sync_data=lambda: None),
    )
    ChainModel.removeSequence(model, 1)  # pyright: ignore[reportArgumentType]
    assert model._data.chain_sequences == [first]
    # Its actions leave the library unless an input still uses them (it
    # used to drop the list and keep them).
    assert released == [second]
