# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Batch 2, input events (spec page 02; GL ids in each test's comment).

No real hook is installed and no key or mouse input reaches the PC: the
Windows calls are stood in for and the hook callbacks are called directly.
"""

from __future__ import annotations

import ctypes
import threading
import types
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import win32con
from PySide6 import QtCore

import dill
from gremlin import (
    clock,
    device_initialization,
    event_handler,
    input_cache,
    keyboard,
    shared_state,
    threads,
    util,
    windows_event_hook,
)
from gremlin.types import HatDirection, InputType, MouseButton
from test import fake_hardware

_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid
_VJOY = dill.GUID(fake_hardware.raw_guid(is_virtual=True)).uuid


def _wait_for(condition: Any, limit: float = 5.0) -> bool:  # noqa: ANN401
    deadline = clock.monotonic() + limit
    while clock.monotonic() < deadline:
        QtCore.QCoreApplication.processEvents()
        if condition():
            return True
        threading.Event().wait(0.01)
    return False


def _run_events(seconds: float) -> None:
    deadline = clock.monotonic() + seconds
    while clock.monotonic() < deadline:
        QtCore.QCoreApplication.processEvents()
        threading.Event().wait(0.01)


@pytest.fixture
def next_hook(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Windows' CallNextHookEx recorded instead of called."""
    passed: list[tuple] = []

    def call_next(hook: object, n_code: int, w_param: int, l_param: int) -> int:
        passed.append((n_code, w_param))
        return 0

    monkeypatch.setattr(
        windows_event_hook, "user32", types.SimpleNamespace(CallNextHookEx=call_next)
    )
    return passed


def _key(w_param: int, scan: int, flags: int = 0, extra: int = 0,
         time: int | None = None) -> None:
    if time is None:
        time = windows_event_hook._tick_count()
    msg = windows_event_hook.KBDLLHOOKSTRUCT(0, scan, flags, time, extra)
    windows_event_hook.process_keyboard_event(0, w_param, ctypes.addressof(msg))


@pytest.fixture
def highlighting_kept() -> Iterator[None]:
    before = shared_state.suspend_input_highlighting()
    yield
    shared_state.set_suspend_input_highlighting(before)


# --- GL-127: an error in a hook callback still passes the event on ----------


def test_a_failing_key_callback_still_passes_the_key_on(
    next_hook: list[tuple], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(event: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(windows_event_hook, "g_keyboard_callbacks", [fail])
    monkeypatch.setattr(windows_event_hook, "g_mouse_callbacks", [fail])
    _key(0x0100, 0x1E)
    msg = windows_event_hook.MSLLHOOKSTRUCT()
    windows_event_hook.process_mouse_event(
        0, windows_event_hook.WM_LBUTTONDOWN, ctypes.addressof(msg)
    )
    assert next_hook == [(0, 0x0100), (0, windows_event_hook.WM_LBUTTONDOWN)]


# --- GL-126: a lost keyboard hook is put back -------------------------------


class _FakeWindows:
    """The Windows calls of a hook's message loop, scripted."""

    def __init__(self, messages: list[tuple[int, int]]) -> None:
        self.messages = list(messages)
        self.installed: list[int] = []
        self.removed: list[int] = []
        self.dispatched: list[int] = []
        self.posted: list[tuple] = []
        self.timer_ms = 0

    def SetWindowsHookExW(self, kind: int, proc: object, mod: object, tid: int) -> int:  # noqa: N802
        self.installed.append(100 + len(self.installed))
        return self.installed[-1]

    def UnhookWindowsHookEx(self, hook_id: int) -> bool:  # noqa: N802
        self.removed.append(hook_id)
        return True

    def SetTimer(self, hwnd: object, ident: int, ms: int, fn: object) -> int:  # noqa: N802
        self.timer_ms = ms
        return 7

    def KillTimer(self, hwnd: object, ident: int) -> bool:  # noqa: N802
        return True

    def GetMessageW(self, pmsg: Any, hwnd: object, low: int, high: int) -> int:  # noqa: N802, ANN401
        if not self.messages:
            return 0
        message, w_param = self.messages.pop(0)
        msg = pmsg._obj
        msg.message, msg.wParam, msg.hWnd = message, w_param, None
        return 1

    def TranslateMessage(self, pmsg: Any) -> None:  # noqa: N802, ANN401
        pass

    def DispatchMessageW(self, pmsg: Any) -> None:  # noqa: N802, ANN401
        self.dispatched.append(pmsg._obj.message)

    def PostThreadMessageW(self, ident: int, message: int, w: int, l: int) -> bool:  # noqa: N802, E741
        self.posted.append((ident, message))
        return True


class _TestHook(windows_event_hook._Hook):
    _NAME = "test hook"
    _HOOK_TYPE = windows_event_hook.WH_KEYBOARD_LL

    def _handler(self) -> Any:  # noqa: ANN401
        return windows_event_hook.process_keyboard_event


def test_the_hook_is_put_back_on_its_timer_and_when_asked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook = windows_event_hook
    fake = _FakeWindows([
        (hook.WM_TIMER, 7),  # the regular check
        (0x0400, 0),  # some other message: dispatched as before
        (hook.WM_REHOOK, 0),  # a callback was slow
    ])
    monkeypatch.setattr(hook, "user32", fake)
    test_hook = _TestHook()
    test_hook._running = True
    test_hook._listen()  # on this thread: the loop ends when messages do
    assert fake.installed == [100, 101, 102]
    # Each old hook removed only after its new one is in; the last at the end.
    assert fake.removed == [100, 101, 102]
    assert fake.dispatched == [0x0400]
    assert fake.timer_ms == hook.REHOOK_EVERY_MS


def test_a_late_key_asks_for_the_hook_to_be_put_back_once(
    next_hook: list[tuple], monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[bool] = []
    monkeypatch.setattr(windows_event_hook, "g_keyboard_callbacks", [])
    monkeypatch.setattr(
        windows_event_hook.KeyboardHook(), "rehook_soon", lambda: asked.append(True)
    )
    _key(0x0100, 0x1E)  # on time
    assert asked == []
    _key(0x0100, 0x1E, time=windows_event_hook._tick_count() - 5000)  # 5 s late
    assert asked == [True]

    fake = _FakeWindows([])
    monkeypatch.setattr(windows_event_hook, "user32", fake)
    test_hook = _TestHook()
    test_hook._running = True
    test_hook._listen_thread = types.SimpleNamespace(ident=42)  # type: ignore[assignment]
    test_hook.rehook_soon()
    test_hook.rehook_soon()  # already asked: not posted again
    assert fake.posted == [(42, windows_event_hook.WM_REHOOK)]


# --- GL-121: the program's own keys are not input while a Run is on ---------


def test_the_hook_marks_the_programs_own_keys(
    next_hook: list[tuple], monkeypatch: pytest.MonkeyPatch
) -> None:
    keys: list[windows_event_hook.KeyEvent] = []
    monkeypatch.setattr(windows_event_hook, "g_keyboard_callbacks", [keys.append])
    _key(0x0100, 0x1E, flags=0x10, extra=windows_event_hook.OWN_KEY_MARK)
    _key(0x0100, 0x1E, flags=0x10)  # injected by another program
    _key(0x0100, 0x1E)  # typed
    assert [(k.is_injected, k.is_own) for k in keys] == [
        (True, True), (True, False), (False, False)
    ]


def test_keys_the_program_sends_carry_the_mark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[tuple] = []
    monkeypatch.setattr(keyboard.win32api, "keybd_event", lambda *a: sent.append(a))
    key = keyboard.key_from_name("a")
    keyboard.send_key_down(key)
    keyboard.send_key_up(key)
    assert [args[3] for args in sent] == [windows_event_hook.OWN_KEY_MARK] * 2


def _key_events(listener: event_handler.EventListener) -> list[tuple]:
    seen: list[tuple] = []
    listener.keyboard_event.connect(
        lambda e: seen.append((e.identifier, e.is_pressed)),
        QtCore.Qt.ConnectionType.DirectConnection,
    )
    return seen


def _release_all(listener: event_handler.EventListener, scan: int) -> None:
    listener._keyboard_handler(windows_event_hook.KeyEvent(scan, False, False, False))


def test_own_keys_are_ignored_while_a_run_is_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import run_scope

    listener = event_handler.EventListener()
    seen = _key_events(listener)
    own = windows_event_hook.KeyEvent(0x30, False, True, True, True)
    own_up = windows_event_hook.KeyEvent(0x30, False, False, True, True)
    try:
        monkeypatch.setattr(run_scope, "running", lambda: True)
        listener._keyboard_handler(own)
        listener._keyboard_handler(own_up)
        assert seen == []
        monkeypatch.setattr(run_scope, "running", lambda: False)
        listener._keyboard_handler(own)
        listener._keyboard_handler(own_up)
        assert seen == [((0x30, False), True), ((0x30, False), False)]
    finally:
        listener.keyboard_event.disconnect()
        _release_all(listener, 0x30)


# --- GL-125: a key whose release Windows lost is not ignored next time ------


def test_a_press_after_a_lost_release_is_a_new_press(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = event_handler.EventListener()
    now = [1000.0]
    monkeypatch.setattr(
        event_handler, "clock", types.SimpleNamespace(monotonic=lambda: now[0])
    )
    down_in_windows = [True]
    monkeypatch.setattr(
        keyboard, "is_down_in_windows", lambda key: down_in_windows[0]
    )
    seen = _key_events(listener)
    press = windows_event_hook.KeyEvent(0x2F, False, True, False)
    try:
        listener._keyboard_handler(press)
        now[0] += 0.03
        listener._keyboard_handler(press)  # Windows repeating the held key
        assert len(seen) == 1
        # The release is lost (Ctrl+Alt+Del); Windows has the key up.
        down_in_windows[0] = False
        now[0] += 0.5
        listener._keyboard_handler(press)  # soon after: still taken as a repeat
        assert len(seen) == 1
        now[0] += 5.0
        listener._keyboard_handler(press)  # pressed again later
        assert seen == [((0x2F, False), True)] * 2
        # Held for a long time, Windows still has it down: no new press.
        down_in_windows[0] = True
        now[0] += 5.0
        listener._keyboard_handler(press)
        assert len(seen) == 2
    finally:
        listener.keyboard_event.disconnect()
        _release_all(listener, 0x2F)


# --- GL-128: Numpad Enter is sent as Enter with the extended flag -----------


def test_numpad_enter_is_sent_as_extended_enter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[tuple] = []
    monkeypatch.setattr(keyboard.win32api, "keybd_event", lambda *a: sent.append(a))
    key = keyboard.key_from_name("npenter")
    keyboard.send_key_down(key)
    vk, scan, flags, _extra = sent[0]
    assert (vk, scan) == (win32con.VK_RETURN, 0x1C)
    assert flags & win32con.KEYEVENTF_EXTENDEDKEY
    assert keyboard.key_from_code(0x1C, True) == key  # the hook still tells it apart


# --- GL-036: no device_db.json gives plain names ----------------------------


def test_a_missing_device_database_gives_plain_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        input_cache.util, "resource_path", lambda rel: str(tmp_path / rel)
    )
    db = object.__new__(input_cache.DeviceDatabase)
    input_cache.DeviceDatabase.__init__(db)
    device = device_initialization.physical_devices()[0]
    assert db.get_mapping(device) is None
    assert db.get_mapping_by_uuid(device.device_guid.uuid) is None


# --- GL-037, GL-137: Esc held 1 s cancels Listen, on the main thread --------


def _listener(kinds: list[InputType], several: bool = False) -> tuple[Any, list]:  # noqa: ANN401
    from gremlin.ui.util import InputListenerModel

    model = InputListenerModel()
    done: list[list] = []
    model.listeningTerminated.connect(lambda inputs: done.append(list(inputs)))
    model.setProperty("eventTypes", [InputType.to_string(k) for k in kinds])
    model.setProperty("multipleInputs", several)
    model.setProperty("enabled", True)
    return model, done


def _esc(pressed: bool) -> event_handler.Event:
    esc = keyboard.key_from_name("esc")
    return event_handler.Event(
        InputType.Keyboard, (esc.scan_code, esc.is_extended), dill.UUID_Keyboard,
        "Default", is_pressed=pressed,
    )


def test_a_short_esc_tap_does_not_cancel_listen(highlighting_kept: None) -> None:
    model, done = _listener([InputType.JoystickButton])
    try:
        model._kb_event_cb(_esc(True))
        model._kb_event_cb(_esc(False))
        _run_events(1.4)
        assert done == []
    finally:
        model.setProperty("enabled", False)


def test_holding_esc_cancels_listen_on_the_main_thread(
    highlighting_kept: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, done = _listener([InputType.JoystickButton])
    ran_on: list[threading.Thread] = []
    abort = model._abort_listening

    def record() -> None:
        ran_on.append(threading.current_thread())
        abort()

    monkeypatch.setattr(model, "_abort_listening", record)
    try:
        model._kb_event_cb(_esc(True))
        assert isinstance(model._abort_timer, threads.MainTimer)
        assert _wait_for(lambda: bool(done))
        assert done == [[]]
        assert ran_on == [threading.main_thread()]
    finally:
        model.setProperty("enabled", False)


def test_an_esc_tap_is_the_input_when_keys_are_listened_for(
    highlighting_kept: None,
) -> None:
    model, done = _listener([InputType.Keyboard])
    try:
        model._kb_event_cb(_esc(True))
        model._kb_event_cb(_esc(False))
        assert [[e.identifier for e in d] for d in done] == [[(0x01, False)]]
        _run_events(1.2)
        assert len(done) == 1  # the hold timer was stopped
    finally:
        model.setProperty("enabled", False)


# --- GL-120: Listen and macro Record share the mouse hook -------------------


@pytest.mark.filterwarnings("ignore:libpyside. Failed to disconnect:RuntimeWarning")
def test_listen_ending_does_not_cut_off_a_mouse_recording(
    highlighting_kept: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui.util import MacroRecorder

    hook = windows_event_hook.MouseHook()
    calls: list[str] = []
    monkeypatch.setattr(hook, "_users", 0)
    monkeypatch.setattr(hook, "start", lambda: calls.append("start"))
    monkeypatch.setattr(hook, "stop", lambda: calls.append("stop"))

    model, done = _listener([InputType.Mouse])
    recorder = MacroRecorder(lambda action: None)
    recorder.start([InputType.Mouse], False)
    try:
        wheel = event_handler.Event(
            InputType.Mouse, MouseButton.WheelUp, dill.UUID_Keyboard, "Default",  # type: ignore[arg-type]
            is_pressed=True,
        )
        model._mouse_event_cb(wheel)  # Listen ends
        assert done and calls == ["start"]
        model.setProperty("enabled", False)
        assert calls == ["start"]  # still recording
    finally:
        recorder.stop()
    assert calls == ["start", "stop"]


def test_a_listen_closed_early_lets_go_of_the_mouse_hook(
    highlighting_kept: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = windows_event_hook.MouseHook()
    calls: list[str] = []
    monkeypatch.setattr(hook, "_users", 0)
    monkeypatch.setattr(hook, "start", lambda: calls.append("start"))
    monkeypatch.setattr(hook, "stop", lambda: calls.append("stop"))
    model, done = _listener([InputType.Mouse])
    model.setProperty("enabled", False)  # the dialog closed without an input
    assert calls == ["start", "stop"] and done == []


# --- GL-131: Listen ignores vJoy and Gremlin's own Xbox pads ----------------


def _button(device: uuid.UUID) -> event_handler.Event:
    return event_handler.Event(
        InputType.JoystickButton, 3, device, "Default", is_pressed=True,
    )


def test_listen_ignores_vjoy_and_own_xbox_pads(
    highlighting_kept: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vigem.ids

    assert _VJOY in {d.device_guid.uuid for d in device_initialization.vjoy_devices()}
    pad = uuid.UUID("12345678-0000-0000-0000-000000000360")
    monkeypatch.setattr(vigem.ids, "is_vigem_xbox_guid", lambda guid: guid == pad)
    model, done = _listener([InputType.JoystickButton])
    try:
        model._joy_event_cb(_button(_VJOY))
        model._joy_event_cb(_button(pad))
        assert done == []
        model._joy_event_cb(_button(_STICK))
        assert [[e.device_guid for e in d] for d in done] == [[_STICK]]
    finally:
        model.setProperty("enabled", False)


def test_listen_takes_a_vjoy_used_as_input(
    highlighting_kept: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    every = device_initialization.joystick_devices()
    monkeypatch.setattr(device_initialization, "input_devices", lambda: every)
    model, done = _listener([InputType.JoystickButton])
    try:
        model._joy_event_cb(_button(_VJOY))
        assert [[e.device_guid for e in d] for d in done] == [[_VJOY]]
    finally:
        model.setProperty("enabled", False)


# --- GL-122: Run reads an axis not yet seen from the driver -----------------


def test_an_axis_not_yet_seen_is_read_from_the_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import macro
    from gremlin.input_refresh import RefreshPhysicalInputs

    listener = event_handler.EventListener()
    axis = input_cache.Joystick()[_STICK].axis(1)
    monkeypatch.setattr(axis, "_value", 0.0)
    monkeypatch.setattr(axis, "_seen", False)
    raw = 26214  # a throttle resting at about 80%
    monkeypatch.setattr(
        dill.DILL._dll, "get_axis", lambda guid, index: raw if index == 1 else 0
    )
    calibrate = listener._calibrations.get((dill.GUID.from_uuid(_STICK), 1))
    expected = (
        calibrate(raw) if calibrate else util.with_default_center_calibration(raw)
    )

    queued: list[Any] = []
    monkeypatch.setattr(
        macro.MacroManager(), "queue_macro", lambda m: queued.append(m)
    )
    monkeypatch.setattr(
        device_initialization, "input_devices",
        lambda: [d for d in device_initialization.joystick_devices()
                 if d.device_guid.uuid == _STICK],
    )
    RefreshPhysicalInputs.refresh_axes()
    sent = {
        a.input_id: a.value
        for m in queued for a in m.sequence
        if getattr(a, "device_guid", None) == _STICK
    }
    assert sent[1] == pytest.approx(expected) and sent[1] > 0.5
    assert axis.seen and axis.value == pytest.approx(expected)
    # Read once: the cached value is used from then on.
    monkeypatch.setattr(dill.DILL._dll, "get_axis", lambda guid, index: 0)
    assert listener.axis_value(_STICK, 1) == pytest.approx(expected)


# --- GL-123: a stick back with another layout; an unknown input is logged ---


def _input(kind: int, index: int, value: int) -> dill._JoystickInputData:
    return dill._JoystickInputData(
        device_guid=fake_hardware.raw_guid(is_virtual=False),
        input_type=kind, input_index=index, value=value,
    )


def test_a_stick_back_with_more_buttons_reports_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = event_handler.EventListener()
    wrapper = input_cache.Joystick()[_STICK]
    held = wrapper.button(2)
    stick = device_initialization.device_for_uuid(_STICK)
    bigger = fake_hardware.raw_device(is_virtual=False)
    bigger.button_count = 80
    fake = dill.DILL._dll
    original_info = fake.get_device_information_by_guid

    # The stick goes and comes back (same id) with 80 buttons. The scan is
    # stood in for: it sets the list the listener reads after it.
    listed: list[Any] = [[stick]]
    after_scan: list[Any] = [[]]

    def scan() -> None:
        listed[0] = after_scan[0]

    monkeypatch.setattr(device_initialization, "joystick_devices_initialization", scan)
    monkeypatch.setattr(device_initialization, "joystick_devices", lambda: listed[0])
    monkeypatch.setattr(listener, "device_change_event",
                        types.SimpleNamespace(emit=lambda: None))
    try:
        listener._run_device_list_update()  # unplugged
        assert wrapper.button(2) is held  # kept while it is away
        monkeypatch.setattr(fake, "get_device_information_by_guid",
                            lambda guid: bigger)
        after_scan[0] = [stick]
        listener._run_device_list_update()  # back, with 80 buttons
        seen: list[tuple] = []
        listener.joystick_event.connect(
            lambda e: seen.append((e.identifier, e.is_pressed)),
            QtCore.Qt.ConnectionType.DirectConnection,
        )
        listener._joystick_event_handler(_input(2, 70, 1))
        assert seen == [(70, True)]
        assert wrapper.button(70).is_pressed
        assert wrapper.button(2) is held  # the inputs it had are the same objects
    finally:
        listener.joystick_event.disconnect()
        monkeypatch.setattr(fake, "get_device_information_by_guid", original_info)
        input_cache.Joystick().reconnected(_STICK)  # back to 64 buttons


def test_an_event_for_an_unknown_input_is_logged_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import log_once

    logged: list[str] = []
    monkeypatch.setattr(log_once, "log_once", lambda *a: logged.append(a[3]))
    listener = event_handler.EventListener()
    listener._joystick_event_handler(_input(2, 200, 1))  # button 200 of 64
    assert len(logged) == 1 and "200" in logged[0]


# --- GL-172: a vJoy error in an action does not pause the profile -----------


def test_a_vjoy_error_in_an_action_does_not_pause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import error, signal

    shown: list[tuple] = []
    monkeypatch.setattr(signal, "display_error", lambda *a: shown.append(a))
    handler = event_handler.EventHandler()
    ran: list[str] = []

    def fail(event: object) -> None:
        raise error.VJoyError("vJoy write failed")

    event = event_handler.Event(InputType.JoystickButton, 9, _STICK, "Default",
                                is_pressed=True)
    callbacks = [fail, lambda e: ran.append("next")]
    monkeypatch.setattr(handler, "callbacks", {_STICK: {"Default": {event: callbacks}}})
    monkeypatch.setattr(handler, "process_callbacks", True)
    handler.process_event(event)
    assert handler.process_callbacks
    assert shown == [] and ran == ["next"]


# --- GL-124 (input cache side): scripts see the shown (twin) name -----------


def test_the_cached_stick_has_the_shown_name(monkeypatch: pytest.MonkeyPatch) -> None:
    stick = device_initialization.device_for_uuid(_STICK)
    monkeypatch.setattr(stick, "name", "pJoy Pro (2)")
    assert input_cache.Joystick()[_STICK].name == "pJoy Pro (2)"
    event = event_handler.Event(InputType.JoystickButton, 1, _STICK, "Default")
    assert event.display_name().startswith("pJoy Pro (2) - ")
    assert HatDirection.Center  # (types imported for the module's other tests)
