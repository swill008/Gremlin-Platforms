# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Batch 3, devices and input (spec page 02).

GL-209 the vJoy message ends "Then restart the program.", GL-239 no dead
mouse "injected" filter and mouse events carry the keyboard's UUID, GL-240
the HidHide driver client lives outside gremlin/ui, GL-241 the Xbox driver
package reads devices through gremlin.modules.hardware, GL-244 events can
be marked as made by the program, GL-265 the hook stop and own-pad window
run on gremlin.clock, and the Input Monitor and input pairing names come
from device_names.shown_name. Fakes only: nothing here touches real
HidHide, vJoy or ViGEm.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
import uuid
from types import SimpleNamespace

import pytest

import dill
from gremlin import clock, event_handler, windows_event_hook
from gremlin import device_initialization as di
from gremlin.types import InputType, MouseButton

_ROOT = pathlib.Path(__file__).parents[2]


# --- GL-209 -----------------------------------------------------------------


def test_vjoy_left_out_message_says_restart_the_program(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    told: list[tuple] = []
    monkeypatch.setattr("gremlin.signal.display_error", lambda *a: told.append(a))
    monkeypatch.setattr(di, "_vjoy_problems", [(1, "Fix it.")])
    monkeypatch.setattr(di, "_told", ())
    di._tell_vjoy_problems()
    _title, details = told[0]
    assert details.endswith("Then restart the program.")
    assert "Gremlin-Platforms" not in details


# --- GL-239 -----------------------------------------------------------------


def test_mouse_events_carry_the_keyboard_uuid_and_are_never_dropped() -> None:
    sent: list[event_handler.Event] = []
    listener = SimpleNamespace(mouse_event=SimpleNamespace(emit=sent.append))
    evt = windows_event_hook.MouseEvent(MouseButton.Left, True)
    assert event_handler.EventListener.klass._mouse_handler(listener, evt) is True
    assert len(sent) == 1
    assert sent[0].device_guid == dill.UUID_Keyboard
    assert isinstance(sent[0].device_guid, uuid.UUID)
    assert sent[0].event_type == InputType.Mouse
    assert not hasattr(evt, "is_injected")


# --- GL-265 -----------------------------------------------------------------


class _StuckThread:
    name = "stuck"

    def is_alive(self) -> bool:
        return True

    def join(self, timeout: float | None = None) -> None:
        pass


def test_hook_stop_waits_on_the_program_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks: list[float] = []

    def stepped() -> float:
        ticks.append(len(ticks) * 1.0)  # a second per read
        return ticks[-1]

    monkeypatch.setattr(clock, "monotonic", stepped)
    hook = windows_event_hook._Hook()
    hook._running = True
    hook._listen_thread = _StuckThread()  # type: ignore[assignment]
    monkeypatch.setattr(hook, "_post_quit", lambda thread: None)
    hook.stop()
    # Read on the stepped clock: the 2 s wait ends after a few reads.
    assert 2 <= len(ticks) <= 5


def test_own_pad_window_runs_on_the_program_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vigem import own_pads

    own_pads.forget_all()
    monkeypatch.setattr(own_pads, "_save", lambda: None)
    monkeypatch.setattr(own_pads, "_present_with_xbox_id", lambda: set())
    now = [100.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    own_pads.before_plug()
    pad = SimpleNamespace(
        vendor_id=own_pads.XBOX_HID_VID,
        product_id=own_pads.XBOX_HID_PID,
        device_guid=uuid.UUID(int=7),
    )
    now[0] += own_pads._WINDOW_S + 1  # the window is over
    try:
        assert own_pads.note_device(pad) is False
        now[0] = 101.0
        assert own_pads.note_device(pad) is True
    finally:
        own_pads.forget_all()


# --- GL-241 -----------------------------------------------------------------


def test_xbox_package_reads_devices_through_the_hardware_door(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import hardware
    from vigem import ids

    asked: list[object] = []
    info = SimpleNamespace(name="pad")
    monkeypatch.setattr(hardware, "device_info", lambda uid: asked.append(uid) or info)
    monkeypatch.setattr(ids, "is_vigem_xbox_summary", lambda dev: dev is info)
    uid = uuid.UUID(int=9)
    assert ids.is_vigem_xbox_guid(uid) is True
    assert asked == [uid]
    assert "dill.DILL" not in (_ROOT / "vigem" / "ids.py").read_text(encoding="utf-8")


# --- GL-240 -----------------------------------------------------------------


def test_hidhide_driver_calls_live_outside_the_ui() -> None:
    from gremlin import hidhide_driver

    ui = (_ROOT / "gremlin" / "ui" / "hidhide.py").read_text(encoding="utf-8")
    for word in ("ctypes", "WinDLL", "DeviceIoControl", "setupapi", "cfgmgr32"):
        assert word not in ui, word
    for name in ("driver_present", "get_active", "set_active", "get_inverse",
                 "set_inverse", "get_blacklist", "set_blacklist",
                 "set_whitelist", "driver_version", "list_hid_devices",
                 "last_error"):
        assert callable(getattr(hidhide_driver, name)), name


def test_hidhide_driver_writes_the_block_list_through_its_control_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import hidhide_driver as drv

    calls: list[tuple] = []
    monkeypatch.setattr(drv, "_open_control", lambda: "handle")
    monkeypatch.setattr(drv, "_close", lambda handle: calls.append(("close", handle)))
    monkeypatch.setattr(
        drv, "_ioctl",
        lambda handle, code, inn=None, out=0: calls.append((code, inn)) or (True, b""),
    )
    assert drv.set_blacklist([r"HID\A"]) is True
    assert calls == [
        (drv.IOCTL_SET_BLACKLIST, drv._encode_multi_sz([r"HID\A"])),
        ("close", "handle"),
    ]


def test_a_refused_hidhide_tick_shows_the_driver_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import hidhide_driver as drv
    from gremlin.ui import hidhide as hh

    page = SimpleNamespace(
        _present=True, _devices=[], _last_error="", reload=lambda: None
    )
    monkeypatch.setattr(drv, "_ioctl_error", "HidHide driver call failed (5).")
    monkeypatch.setattr(hh, "_hidhide_managed", lambda: True)
    monkeypatch.setattr(hh, "_saved_hidden", lambda: [])
    monkeypatch.setattr(hh, "_save_hidden", lambda ids: None)
    monkeypatch.setattr(hh, "set_blacklist", lambda ids: False)
    assert hh.HidHideModel.setDeviceHidden(page, r"HID\VID_1&PID_2\1", True) is False
    assert page._last_error == "HidHide driver call failed (5)."


# --- GL-244 -----------------------------------------------------------------


def test_an_event_can_be_marked_as_made_by_the_program() -> None:
    real = event_handler.Event(InputType.JoystickButton, 1, uuid.UUID(int=1), "Default")
    assert real.synthetic is False
    made = event_handler.Event(
        InputType.JoystickButton, 1, uuid.UUID(int=1), "Default", synthetic=True
    )
    assert made.synthetic is True
    assert made.clone().synthetic is True
    assert made == real  # same input: the flag is not part of its identity


# --- Batch 2 follow-up: one shown name ---------------------------------------


def test_input_monitor_and_pairing_show_the_shown_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import input_monitor
    from gremlin.ui import device_names, input_pairing

    uid = uuid.UUID(int=0x51)
    monkeypatch.setattr(
        device_names, "shown_name", lambda g: "My Stick" if g == uid else ""
    )
    assert input_monitor.device_name(uid) == "My Stick"
    assert input_pairing.device_label(str(uid)) == "My Stick"
    # Built-in devices keep their own names.
    assert input_monitor.device_name(dill.UUID_Keyboard) == "Keyboard"
    assert input_pairing.device_label(str(dill.UUID_LogicalDevice)) == "Logical Device"
    # Unknown: as before.
    other = uuid.UUID(int=0x52)
    assert input_monitor.device_name(other) == "Unknown device"


def test_own_pads_list_devices_through_the_hardware_door(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import hardware
    from vigem import own_pads

    pad = SimpleNamespace(
        vendor_id=own_pads.XBOX_HID_VID,
        product_id=own_pads.XBOX_HID_PID,
        device_guid=uuid.UUID(int=11),
    )
    stick = SimpleNamespace(vendor_id=1, product_id=2, device_guid=uuid.UUID(int=12))
    monkeypatch.setattr(hardware, "devices", lambda: [pad, stick])
    assert own_pads._present_with_xbox_id() == {own_pads._key(pad.device_guid)}
    assert "dill" not in (_ROOT / "vigem" / "own_pads.py").read_text(encoding="utf-8")


# --- GL-244: Listen and macro recording ignore events the program made ------


class _Seen:
    """An event-type list that notes it was asked (the event got that far)."""

    def __init__(self) -> None:
        self.asked = 0

    def __contains__(self, item: object) -> bool:
        self.asked += 1
        return False


def _joy(synthetic: bool) -> event_handler.Event:
    return event_handler.Event(
        InputType.JoystickButton, 1, uuid.UUID(int=0x60), "Default",
        is_pressed=True, synthetic=synthetic,
    )


def test_listen_ignores_events_the_program_made() -> None:
    from gremlin.ui import util

    seen = _Seen()
    model = SimpleNamespace(_event_types=seen)
    util.InputListenerModel._joy_event_cb(model, _joy(True))
    assert seen.asked == 0
    util.InputListenerModel._joy_event_cb(model, _joy(False))
    assert seen.asked == 1


def test_macro_recording_ignores_events_the_program_made(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import util

    queued: list[object] = []
    monkeypatch.setattr(
        util.QtCore.QTimer, "singleShot", lambda ms, fn: queued.append(fn)
    )
    recorder = SimpleNamespace()
    util.MacroRecorder._queue_event_recording(recorder, _joy(True))
    assert queued == []
    util.MacroRecorder._queue_event_recording(recorder, _joy(False))
    assert len(queued) == 1
