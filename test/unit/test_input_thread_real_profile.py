# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""End to end with the real input thread and REAL profile actions (thread
batches 2-5, claude/plans/fix-plans/thread-ui.md section 3).

test_input_thread_ui_blocked.py proves the path with a stand-in binding;
here the bindings come from a real profile (Map to vJoy, Tempo, Change Mode,
Macro, Map to Logical Device) read from profile XML, Run through RunControl
on the input thread. The driver side is faked: dill events go through
EventListener -> claim gate -> EventHandler -> the real action functors, and
vJoy writes are recorded (output._write_vjoy). The window (main) thread is
blocked on purpose in several tests.

Everything waits with a limit. The main thread is the test's own thread.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore

import dill
from gremlin import (
    clock,
    code_runner,
    config,
    event_handler,
    input_thread,
    mode_manager,
    profile,
    run_scope,
    shared_state,
)
from gremlin.logical_device import LogicalDevice
from gremlin.macro import MacroManager
from gremlin.modules import output, runtime
from gremlin.types import InputType
from test import fake_hardware

fake_hardware.install(vjoy_ids=(1,))

_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid
_LIMIT = 3.0

# The stick's inputs used by the profile below.
B_MAP = 6  # Map to vJoy button 3 (Default); button 9 (Bravo)
A_MAP = 1  # Map to vJoy axis 2, absolute
B_TEMPO = 7  # Tempo: short vJoy button 4, long vJoy button 5
B_MODE = 8  # Change Mode: Switch to Bravo
B_MACRO = 9  # Macro: vJoy 20, pause, vJoy 21
B_LOGICAL = 10  # Map to Logical Device button 11 (press)
LD_IN = 11  # a Logical Device button, bound to Map to vJoy button 12
THRESHOLD = 0.3
MACRO_PAUSE = 1.5


# +-------------------------------------------------------------------------
# | Profile XML (the format the program saves)


def _prop(kind: str, name: str, value: object) -> str:
    return (
        f'<property type="{kind}"><name>{name}</name>'
        f"<value>{value}</value></property>"
    )


def _action(
    kind: str, body: str, mode: str = "both", label: str = ""
) -> tuple[str, str]:
    ident = str(uuid.uuid4())
    text = (
        f'<action id="{ident}" type="{kind}">{body}'
        + _prop("string", "action-label", label or kind)
        + _prop("activation-mode", "activation-mode", mode)
        + "</action>"
    )
    return ident, text


def _vjoy(kind: str, number: int, **extra: str) -> tuple[str, str]:
    body = _prop("int", "vjoy-device-id", 1) + _prop("int", "vjoy-input-id", number)
    body += _prop("input_type", "vjoy-input-type", kind)
    if kind == "axis":
        body += _prop("axis_mode", "axis-mode", "absolute")
        body += _prop("float", "axis-scaling", 1.0)
    else:
        body += _prop("bool", "button-inverted", "False")
    return _action("map-to-vjoy", body)


def _root(children: list[str]) -> tuple[str, str]:
    ids = "".join(f"<action-id>{c}</action-id>" for c in children)
    return _action("root", f"<actions>{ids}</actions>", mode="disallowed")


def _binding(guid: uuid.UUID, kind: str, number: int, mode: str, root: str) -> str:
    return (
        f"<input><device-id>{guid}</device-id><input-type>{kind}</input-type>"
        f"<mode>{mode}</mode><input-id>{number}</input-id>"
        f"<action-configuration><root-action>{root}</root-action>"
        f"<behavior>{kind}</behavior></action-configuration></input>"
    )


def profile_xml(vjoy_button: int = 3) -> str:
    """The test profile; vjoy_button: what B_MAP sends in Default."""
    library: list[str] = []
    inputs: list[str] = []

    def bind(
        guid: uuid.UUID, kind: str, number: int, mode: str, *acts: tuple[str, str]
    ) -> None:
        library.extend(text for _, text in acts)
        rid, rtext = _root([ident for ident, _ in acts])
        library.append(rtext)
        inputs.append(_binding(guid, kind, number, mode, rid))

    # 1. Map to vJoy, button and axis; Bravo's own button.
    bind(_STICK, "button", B_MAP, "Default", _vjoy("button", vjoy_button))
    bind(_STICK, "button", B_MAP, "Bravo", _vjoy("button", 9))
    bind(_STICK, "axis", A_MAP, "Default", _vjoy("axis", 2))

    # 2. Tempo.
    short, short_text = _vjoy("button", 4)
    long_, long_text = _vjoy("button", 5)
    library += [short_text, long_text]
    tempo, tempo_text = _action(
        "tempo",
        f"<short-actions><action-id>{short}</action-id></short-actions>"
        f"<long-actions><action-id>{long_}</action-id></long-actions>"
        + _prop("float", "threshold", THRESHOLD)
        + _prop("string", "activate-on", "press"),
        mode="disallowed",
    )
    bind(_STICK, "button", B_TEMPO, "Default", (tempo, tempo_text))

    # 3. Change Mode (Switch to Bravo).
    change = _action(
        "change-mode",
        _prop("string", "change-type", "Switch")
        + "<target-mode>" + _prop("string", "name", "Bravo") + "</target-mode>",
        mode="press",
    )
    bind(_STICK, "button", B_MODE, "Default", change)

    # 4. Macro: vJoy 20 down, a pause, vJoy 21 down.
    def step(kind: str, props: str) -> str:
        return f'<macro-action type="{kind}">{props}</macro-action>'

    def vjoy_step(number: int) -> str:
        return step(
            "vjoy",
            _prop("int", "vjoy-id", 1) + _prop("input_type", "input-type", "button")
            + _prop("int", "input-id", number) + _prop("bool", "value", "True"),
        )

    macro = _action(
        "macro",
        _prop("bool", "is-exclusive", "False") + _prop("bool", "is-preemptive", "False")
        + _prop("string", "repeat-mode", "Single") + _prop("int", "repeat-count", 1)
        + _prop("float", "repeat-delay", 0.1)
        + vjoy_step(20)
        + step("pause", _prop("float", "duration", MACRO_PAUSE))
        + vjoy_step(21),
        mode="press",
    )
    bind(_STICK, "button", B_MACRO, "Default", macro)

    # 5. Map to Logical Device button 11, whose own binding is Map to vJoy 12.
    to_ld = _action(
        "map-to-logical-device",
        _prop("int", "logical-input-id", LD_IN)
        + _prop("input_type", "logical-input-type", "button")
        + _prop("bool", "button-inverted", "False"),
    )
    bind(_STICK, "button", B_LOGICAL, "Default", to_ld)
    bind(LogicalDevice.device_guid, "button", LD_IN, "Default", _vjoy("button", 12))

    return (
        '<?xml version="1.0" ?><profile version="16"><inputs>'
        + "".join(inputs)
        + "</inputs><settings><startup-mode>Default</startup-mode>"
        "<macro-default-delay>0.05</macro-default-delay></settings><library>"
        + "".join(library)
        + "</library><modes><mode>Default</mode><mode>Bravo</mode></modes>"
        "<scripts/><devices/></profile>"
    )


# +-------------------------------------------------------------------------
# | Helpers


def _pump(until: Callable[[], bool], limit: float = _LIMIT) -> bool:
    """Runs the main thread's event loop until `until()` or `limit` s."""
    end = clock.monotonic() + limit
    while clock.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if until():
            return True
        time.sleep(0.005)
    QtCore.QCoreApplication.processEvents()
    return until()


def _block_main(seconds: float) -> float:
    """A busy window: no event loop for `seconds`, in bounded steps.
    Returns the time it let go."""
    end = clock.monotonic() + seconds
    while clock.monotonic() < end:
        time.sleep(0.01)
    return clock.monotonic()


def _after(delay: float, fn: Callable[[], None]) -> threading.Thread:
    """The driver side: fn runs on another thread after `delay` s."""

    def run() -> None:
        time.sleep(delay)
        fn()

    thread = threading.Thread(target=run, name="test-listener", daemon=True)
    thread.start()
    return thread


def _dill(kind: int, index: int, value: int) -> dill._JoystickInputData:
    return dill._JoystickInputData(
        device_guid=fake_hardware.raw_guid(is_virtual=False),
        input_type=kind, input_index=index, value=value,
    )


def press(number: int, down: bool = True) -> None:
    """One stick button event from the driver (called on any thread)."""
    event_handler.EventListener()._joystick_event_handler(_dill(2, number, int(down)))


def make_logical_device() -> None:
    device = LogicalDevice()
    device.reset()
    device.create(InputType.JoystickButton, LD_IN, "Input Button 11")


class Writes:
    """The recorded vJoy writes: (time, on input thread, kind, id, value)."""

    def __init__(self) -> None:
        self.items: list[tuple[float, bool, str, int, Any]] = []
        self.lock = threading.Lock()

    def add(self, kind: str, number: int, value: Any) -> None:  # noqa: ANN401
        with self.lock:
            self.items.append(
                (clock.monotonic(), input_thread.is_input_thread(), kind, number, value)
            )

    def find(self, kind: str, number: int, value: Any = None) -> list[tuple]:  # noqa: ANN401
        with self.lock:
            return [
                w for w in self.items
                if w[2] == kind and w[3] == number and (value is None or w[4] == value)
            ]

    def has(self, kind: str, number: int, value: Any = True) -> bool:  # noqa: ANN401
        return bool(self.find(kind, number, value))


class Rig:
    def __init__(self, tmp_path: Path, writes: Writes) -> None:
        self.tmp_path = tmp_path
        self.writes = writes
        self.control = code_runner.run_control()
        self.open_profile = self.load()
        self.running = False

    def load(self, vjoy_button: int = 3) -> profile.Profile:
        path = self.tmp_path / f"p{uuid.uuid4().hex[:6]}.xml"
        path.write_text(profile_xml(vjoy_button), encoding="utf-8")
        opened = profile.Profile()
        # Actions (Change Mode, Map to Logical Device) read the open profile
        # while they load.
        shared_state.current_profile = opened
        opened.from_xml(path)
        return opened

    def run(self, open_profile: profile.Profile | None = None) -> None:
        """Run as the window does: a snapshot taken here (main), started on
        the input thread."""
        shared_state.current_profile = open_profile or self.open_profile
        snap = code_runner.profile_snapshot(shared_state.current_profile)
        input_thread.call_wait(
            self.control.start, snap, "Default", timeout=10.0
        )
        assert input_thread.call_wait(self.control.runner.is_running, timeout=_LIMIT)
        self.running = True

    def stop(self) -> None:
        input_thread.call_wait(self.control.stop, timeout=10.0)
        self.running = False

    def on_input(self, fn: Callable[[], Any]) -> Any:  # noqa: ANN401
        return input_thread.call_wait(fn, timeout=_LIMIT)


@pytest.fixture
def rig(
    input_thread_running: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[Rig]:
    writes = Writes()
    monkeypatch.setattr(runtime, "should_forward", lambda *a, **k: True)
    monkeypatch.setattr(
        output, "_write_vjoy",
        lambda vid, kind, number, value: writes.add(kind, number, value) or "ok",
    )
    cfg = config.Configuration()
    cfg.set("global", "general", "refresh-axis-on-mode-change", False)
    cfg.set("global", "general", "refresh-axis-on-activation", False)
    make_logical_device()
    code_runner.adopt_runtime_objects()
    saved = shared_state.current_profile
    made = Rig(tmp_path, writes)
    try:
        yield made
    finally:
        try:
            if made.running:
                made.stop()
            else:
                input_thread.call_wait(made.control.stop, timeout=10.0)
        finally:
            shared_state.current_profile = saved
            run_scope._reset_for_tests()
            MacroManager().stop()
            code_runner.release_runtime_objects()


# 1 ---------------------------------------------------------------------------


def test_map_to_vjoy_button_and_axis_while_main_blocked(rig: Rig) -> None:
    rig.run()
    feeders = [
        _after(0.3, lambda: press(B_MAP)),
        _after(0.4, lambda: event_handler.EventListener()._joystick_event_handler(
            _dill(1, A_MAP, 16384))),
    ]
    unblocked_at = _block_main(2.0)
    for feeder in feeders:
        feeder.join(_LIMIT)
    button = rig.writes.find("button", 3, True)
    axis = rig.writes.find("axis", 2)
    assert button, "Map to vJoy (button) wrote nothing while the window was blocked"
    assert axis, "Map to vJoy (axis) wrote nothing while the window was blocked"
    for found in (button[0], axis[0]):
        assert found[1], "the output was written off the input thread"
        assert found[0] < unblocked_at - 1.0, "the write waited for the window"
    assert axis[0][4] == pytest.approx(0.5, abs=0.05)


# 2 ---------------------------------------------------------------------------


def test_tempo_long_press_fires_on_time_while_main_blocked(rig: Rig) -> None:
    rig.run()
    pressed_at: list[float] = []

    def down() -> None:
        pressed_at.append(clock.monotonic())
        press(B_TEMPO)

    feeder = _after(0.2, down)
    unblocked_at = _block_main(THRESHOLD + 1.5)
    feeder.join(_LIMIT)
    short = rig.writes.find("button", 4, True)
    long_ = rig.writes.find("button", 5, True)
    assert short, "Tempo's short action (on press) never ran"
    assert long_, "Tempo's long action never fired while the window was blocked"
    assert long_[0][1], "Tempo's timer ran its action off the input thread"
    assert long_[0][0] < unblocked_at - 0.5, "the long press waited for the window"
    assert THRESHOLD - 0.05 <= long_[0][0] - pressed_at[0] <= THRESHOLD + 1.0
    press(B_TEMPO, False)


# 3 ---------------------------------------------------------------------------


def test_change_mode_next_event_uses_new_mode(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import process_monitor
    from gremlin.ui import backend

    monkeypatch.setattr(process_monitor.ProcessMonitor, "start", lambda self: None)
    monkeypatch.setattr(backend, "display_error", lambda *a, **k: None)
    be = backend.Backend.klass(None)  # type: ignore[arg-type]
    # The Backend read the Logical Device module file afresh: the button
    # goes back and the profile is read again, so it finds the button.
    make_logical_device()
    rig.open_profile = rig.load()
    be.profile = rig.open_profile
    rig.run()
    changed_on: list[bool] = []
    mm = mode_manager.ModeManager()
    mm.mode_changed.connect(
        lambda name: changed_on.append(input_thread.is_input_thread()),
        QtCore.Qt.ConnectionType.DirectConnection,
    )
    feeders = [_after(0.2, lambda: press(B_MODE)), _after(0.5, lambda: press(B_MAP))]
    _block_main(1.2)
    for feeder in feeders:
        feeder.join(_LIMIT)
    assert changed_on and changed_on[0], "the mode did not change on the input thread"
    assert rig.writes.has("button", 9), "the next event did not use Bravo's binding"
    assert not rig.writes.has("button", 3), "the next event used Default's binding"
    assert _pump(lambda: be.ui_state.currentMode == "Bravo"), (
        "the mode selector did not follow after the window unblocked"
    )


# 4 ---------------------------------------------------------------------------


def test_macro_runs_on_own_thread_and_stop_cancels_it(rig: Rig) -> None:
    rig.run()
    press(B_MACRO)
    assert _pump(lambda: rig.writes.has("button", 20)), "the macro never started"
    first = rig.writes.find("button", 20, True)[0]
    assert not first[1], "the macro ran on the input thread (it has its own)"
    # Stop while the macro waits in its pause.
    rig.stop()
    time.sleep(MACRO_PAUSE + 0.7)
    QtCore.QCoreApplication.processEvents()
    assert not rig.writes.has("button", 21), "the macro went on after Stop"


def test_macro_finishes_when_not_stopped(rig: Rig) -> None:
    rig.run()
    press(B_MACRO)
    assert _pump(lambda: rig.writes.has("button", 21), MACRO_PAUSE + 2.5), (
        "the macro did not finish its steps"
    )


# 5 ---------------------------------------------------------------------------


def test_logical_device_reentry_is_synchronous_on_input_thread(rig: Rig) -> None:
    rig.run()
    handler = event_handler.EventHandler()
    seen: list[bool] = []

    def one_press() -> None:
        event = event_handler.Event(
            InputType.JoystickButton, B_LOGICAL, _STICK,
            mode_manager.ModeManager().current.name, is_pressed=True,
        )
        handler.process_event(event)
        # Back from the first press: the re-emitted Logical Device event was
        # handled inside the action, so its own binding has written already.
        seen.append(rig.writes.has("button", 12))

    rig.on_input(one_press)
    assert seen == [True], "the Logical Device re-entry was not handled at once"
    found = rig.writes.find("button", 12, True)[0]
    assert found[1], "the re-entered binding ran off the input thread"


# 6 ---------------------------------------------------------------------------


def test_editing_open_profile_during_run_changes_nothing_until_next_run(
    rig: Rig,
) -> None:
    opened = rig.open_profile
    rig.run(opened)
    # The user edits the open profile while the Run goes on.
    item = opened.get_input_item(
        _STICK, InputType.JoystickButton, B_MAP, "Default", False
    )
    assert item is not None
    edited = item.action_sequences[0].root_action.get_actions()[0][0]
    assert edited.vjoy_input_id == 3
    edited.vjoy_input_id = 15
    press(B_MAP)
    assert _pump(lambda: rig.writes.has("button", 3)), "the running binding changed"
    assert not rig.writes.has("button", 15), "an edit reached the running bindings"
    press(B_MAP, False)
    rig.stop()
    # The next Run takes the edit.
    rig.run(opened)
    press(B_MAP)
    assert _pump(lambda: rig.writes.has("button", 15)), "the next Run lost the edit"
