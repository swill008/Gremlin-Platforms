# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC with the Run on the input thread (06 S100; contract-THR.md, thread
audit item 1 and the OSC hop): OscRuntime lives on the main thread (port,
Listen, Monitor), but the Run's input state is the Run's thread's. While a
Run is on the input thread a packet goes from the OSC thread straight there
(not through main), its auto-release timer is made there, release_held()
sends the releases before it returns, and start()/stop() queue only the
port work to main; no Qt cross-thread timer warning. OSC feedback lives on
the Run's thread. Inline mode keeps everything on main.

These tests start the real input thread. Network: only 127.0.0.1 with an
OS-picked port (the end-to-end test); the others use a stand-in listener.

Spec: 06 S100; 09 (OSC runtime).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtCore, QtTest

from gremlin import (
    clock,
    code_runner,
    history_modules,
    input_thread,
    mode_manager,
    osc,
    osc_feedback,
    osc_traffic,
    shared_state,
)
from gremlin import osc_device_file as odf
from gremlin.event_handler import EventHandler, EventListener
from gremlin.modules import runtime as module_runtime
from gremlin.modules import store
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import InputItem, Library
from gremlin.types import Event, InputType

MODE = "Default"
LIMIT = 3.0
CROSS_THREAD = ("another thread", "different thread", "Timers cannot")
# The real UDP listener, taken before any test stands one in.
_REAL_LISTENER = osc.OscListener


class FakeListener:
    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def bound_port(self) -> int:
        return self.port


def _wait_for(done: Callable[[], bool], limit_s: float = LIMIT) -> bool:
    """Runs the main thread's events until done() or limit_s (bounded)."""
    end = clock.monotonic() + limit_s
    while not done() and clock.monotonic() < end:
        QtTest.QTest.qWait(5)
    return done()


def _on_main() -> bool:
    app = QtCore.QCoreApplication.instance()
    return app is not None and QtCore.QThread.currentThread() is app.thread()


def _cross_thread(messages: list[str]) -> list[str]:
    return [m for m in messages if any(t in m for t in CROSS_THREAD)]


@pytest.fixture
def qt_warnings() -> Iterator[list[str]]:
    seen: list[str] = []

    def handler(_mode: object, _context: object, message: str) -> None:
        seen.append(message)

    previous = QtCore.qInstallMessageHandler(handler)
    yield seen
    QtCore.qInstallMessageHandler(previous)


@pytest.fixture
def rt(
    qapp: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[SimpleNamespace]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    monkeypatch.setattr(odf, "read_server", lambda: {"host": "127.0.0.1"})
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [InputItem(Library())]}),
    )
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.cancel_listen()
    runtime.stop()
    # (on the input thread, pressed) of each OSC event, where it is emitted.
    events: list[tuple[bool, bool]] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            events.append((input_thread.is_input_thread(), event.is_pressed))

    EventListener().joystick_event.connect(
        record, QtCore.Qt.ConnectionType.DirectConnection
    )
    yield SimpleNamespace(runtime=runtime, rows=rows, events=events)
    EventListener().joystick_event.disconnect(record)
    if input_thread.is_running() and not input_thread.is_inline():
        input_thread.call_wait(runtime.stop, timeout=LIMIT)
    runtime.stop()
    runtime.cancel_listen()
    _wait_for(lambda: False, 0.05)
    rows.load_dict(saved)
    rows.mark_saved()


def _spy(monkeypatch: pytest.MonkeyPatch, runtime: object, name: str) -> list[bool]:
    """Wraps runtime.<name>; records whether each call ran on the main thread."""
    ran: list[bool] = []
    original = getattr(runtime, name)

    def wrapper(*args: Any) -> Any:  # noqa: ANN401
        ran.append(_on_main())
        return original(*args)

    monkeypatch.setattr(runtime, name, wrapper)
    return ran


def test_start_and_stop_from_the_input_thread_queue_the_port_work_to_main(
    input_thread_running: None,
    rt: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    qt_warnings: list[str],
) -> None:
    started = _spy(monkeypatch, rt.runtime, "_start_here")
    stopped = _spy(monkeypatch, rt.runtime, "_stop_here")
    input_thread.call_wait(rt.runtime.start, timeout=LIMIT)
    assert rt.runtime._running and rt.runtime._input_here  # noqa: SLF001
    assert _wait_for(lambda: bool(started))
    assert started == [True]
    input_thread.call_wait(rt.runtime.stop, timeout=LIMIT)
    assert not rt.runtime._running and not rt.runtime._input_here  # noqa: SLF001
    assert _wait_for(lambda: bool(stopped))
    assert stopped == [True]
    assert not _cross_thread(qt_warnings)


def test_a_packet_in_a_run_is_applied_on_the_input_thread_and_released_there(
    input_thread_running: None,
    rt: SimpleNamespace,
    qt_warnings: list[str],
) -> None:
    rt.rows.create(InputType.JoystickButton, "/thr/press", delay_ms=5000)
    input_thread.call_wait(rt.runtime.start, timeout=LIMIT)
    # The OSC listener's thread delivers the packet (no value: a pulse).
    sender = threading.Thread(
        target=rt.runtime._from_thread,  # noqa: SLF001
        args=("/thr/press", (), ("127.0.0.1", 7000)),
    )
    sender.start()
    sender.join(LIMIT)
    assert _wait_for(lambda: bool(rt.events))
    assert rt.events == [(True, True)]
    timers = input_thread.call_wait(
        lambda: [
            t.thread() is QtCore.QThread.currentThread()
            for t in rt.runtime._timers.values()  # noqa: SLF001
        ],
        timeout=LIMIT,
    )
    assert timers == [True], "the auto-release timer is not the input thread's"
    order: list[str] = []

    def release() -> None:
        rt.runtime.release_held()
        # Sent on this (input) thread before release_held returned.
        order.extend(f"event {where} {pressed}" for where, pressed in rt.events[1:])

    input_thread.call_wait(release, timeout=LIMIT)
    assert order == ["event True False"]
    assert rt.runtime._timers == {} and rt.runtime._held == {}  # noqa: SLF001
    QtTest.QTest.qWait(100)
    assert rt.events == [(True, True), (True, False)]
    assert not _cross_thread(qt_warnings)


def test_inline_mode_keeps_the_inputs_on_main(rt: SimpleNamespace) -> None:
    """Inline (the wiring tests): everything happens at once on main."""
    rt.rows.create(InputType.JoystickButton, "/inline/press", delay_ms=5000)
    rt.runtime.start()
    assert not rt.runtime._input_here  # noqa: SLF001
    rt.runtime._from_thread("/inline/press", (), None)  # noqa: SLF001
    assert rt.events == [(False, True)]
    rt.runtime.release_held()
    assert rt.events == [(False, True), (False, False)]
    assert rt.runtime._timers == {}  # noqa: SLF001
    rt.runtime.stop()
    assert not rt.runtime._running  # noqa: SLF001


def test_a_runtime_first_made_off_main_moves_to_main(
    input_thread_running: None, qapp: object
) -> None:
    holder = osc.OscRuntime  # the SingletonDecorator
    saved = holder.instance
    holder.instance = None
    try:
        made = input_thread.call_wait(OscRuntime, timeout=LIMIT)
        app = QtCore.QCoreApplication.instance()
        assert app is not None
        assert made.thread() is app.thread()
        made.deleteLater()
    finally:
        holder.instance = saved


def test_feedback_made_on_another_thread_is_replaced_on_the_run_thread(
    input_thread_running: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(osc_feedback, "_feedback", None)
    on_main = osc_feedback.instance()
    on_input = input_thread.call_wait(osc_feedback.instance, timeout=LIMIT)
    assert on_input is not on_main
    assert input_thread.call_wait(
        lambda: on_input.thread() is QtCore.QThread.currentThread(), timeout=LIMIT
    )
    assert input_thread.call_wait(osc_feedback.instance, timeout=LIMIT) is on_input
    input_thread.call_wait(on_input.deleteLater, timeout=LIMIT)


@pytest.fixture
def wired(input_thread_running: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """The input path adopted by the input thread and connected as a Run
    connects it (InputModuleRuntime -> EventHandler)."""
    monkeypatch.setattr(module_runtime, "should_forward", lambda *a, **k: True)
    code_runner.adopt_runtime_objects()
    handler = EventHandler()
    bus: Any = module_runtime.InputModuleRuntime()
    mode = mode_manager.ModeManager().current.name
    saved = (handler.callbacks, handler.process_callbacks)

    def connect() -> None:
        bus.event.connect(handler.process_event)
        handler.process_callbacks = True

    input_thread.call_wait(connect, timeout=LIMIT)
    try:
        yield mode
    finally:

        def undo() -> None:
            bus.event.disconnect(handler.process_event)
            handler.callbacks, handler.process_callbacks = saved

        try:
            input_thread.call_wait(undo, timeout=LIMIT)
        finally:
            code_runner.release_runtime_objects()


def test_an_osc_packet_reaches_its_binding_while_the_window_is_frozen(
    wired: str, rt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """06 S100 end to end: a real UDP packet (127.0.0.1, OS-picked port)
    reaches the binding on the input thread while the main thread is blocked
    for ~2 s; the Monitor's traffic log still gets it, after."""
    from pythonosc.udp_client import SimpleUDPClient

    row = rt.rows.create(InputType.JoystickButton, "/frozen/fire", delay_ms=5000)
    fired: list[tuple[float, bool]] = []
    noted: list[tuple[float, str]] = []
    monkeypatch.setattr(
        osc_traffic,
        "note",
        lambda direction, address, *a, **k: noted.append((clock.monotonic(), address)),
    )

    def binding(_event: Event) -> None:
        fired.append((clock.monotonic(), input_thread.is_input_thread()))

    press = Event(
        InputType.JoystickButton,
        row.input_id,
        osc.OSC_DEVICE_UUID,
        wired,
        is_pressed=True,
    )

    def install() -> None:
        EventHandler().callbacks = {osc.OSC_DEVICE_UUID: {wired: {press: [binding]}}}

    input_thread.call_wait(install, timeout=LIMIT)
    input_thread.call_wait(rt.runtime.start, timeout=LIMIT)
    # The real UDP listener (the rt fixture stands one in for the runtime's
    # own port), on 127.0.0.1 with a port the OS picks.
    server = _REAL_LISTENER("127.0.0.1", 0, rt.runtime._from_thread)  # noqa: SLF001
    server.start()
    try:
        client = SimpleUDPClient("127.0.0.1", server.bound_port())
        client.send_message("/frozen/fire", [])
        blocked_at = clock.monotonic()
        time.sleep(2.0)  # the window is frozen: no main-thread events
        unblocked_at = clock.monotonic()
        assert fired, "the binding did not fire while the main thread was blocked"
        when, on_input = fired[0]
        assert on_input
        assert blocked_at - 0.5 < when < unblocked_at
        assert _wait_for(lambda: bool(noted))
        assert noted[0][1] == "/frozen/fire"
        assert noted[0][0] >= unblocked_at
    finally:
        server.stop()
