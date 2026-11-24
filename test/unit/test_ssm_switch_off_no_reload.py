# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-12-SWITCH-OFF-NO-RELOAD (12 S21): while Screen Saver Mode switches
devices off, keeps them off and switches them back on (also the switch-on of
devices left off at program start), and for 10 s after, a device change
doesn't follow Options > Device change behavior: the running profile keeps
running. The device list re-read still announces the change to every other
listener (was: Reload stopped and started the profile)."""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import dill
from gremlin import clock, device_initialization, event_handler, input_cache
from gremlin import device_disable as dd
from test import fake_hardware
from test.unit.test_ssm_disable import PAD, FakeConn, FakeWindows

_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid
_KEY = ("global", "general", "device-change-behavior")


class _Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t


@pytest.fixture
def steps(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    c = _Clock()
    monkeypatch.setattr(clock, "monotonic", c.monotonic)
    return c


@pytest.fixture
def disabler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[dd.DeviceDisabler, FakeWindows]]:
    windows = FakeWindows()
    journal_file = str(tmp_path / "screen saver mode" / "devices.json")
    windows.conn = FakeConn(windows, journal_file)
    d = dd.DeviceDisabler(
        journal_file=journal_file,
        key_file=str(tmp_path / "screen saver mode" / "helper.key"),
        launcher=windows.launch,
        listener_factory=windows.listen,
        status_reader=windows.read,
        connect_timeout_s=1.0,
    )
    # The one instance Backend asks (dd.manager()).
    monkeypatch.setattr(dd, "_manager", d)
    yield d, windows
    d.stop_helper()


def _start_helper(d: dd.DeviceDisabler) -> None:
    done = threading.Event()
    d.start_helper(lambda ok, _e: done.set())
    assert done.wait(10)
    assert d.helper_running()


@pytest.fixture
def wired(
    event_listener: event_handler.EventListener,
) -> Iterator[SimpleNamespace]:
    """The real device list re-read with the stick unplugged, the real
    Backend._device_change (Reload, profile running) and another listener
    on the same signal."""
    from gremlin.ui import backend as backend_mod

    calls: list[bool] = []
    others: list[bool] = []

    def activate(on: bool) -> None:
        calls.append(on)
        stub._wanted_active = on

    stub: Any = SimpleNamespace(
        _wanted_active=True,
        activate_gremlin=activate,
        config=SimpleNamespace(value=lambda *key: {_KEY: "Reload"}.get(key)),
    )

    def backend_slot() -> None:
        backend_mod.Backend.klass._device_change(stub)

    def other_slot() -> None:
        others.append(True)

    devices = dill.DILL._dll.devices
    kept = list(devices)
    device_initialization.joystick_devices_initialization()
    input_cache.Joystick()[_STICK]
    signal = event_listener.device_change_event
    signal.connect(backend_slot)
    signal.connect(other_slot)

    def unplug() -> None:
        devices[:] = [
            d for d in devices if dill.GUID(d.device_guid).uuid != _STICK
        ]
        event_listener._run_device_list_update()

    def plug_in() -> None:
        devices[:] = kept
        event_listener._run_device_list_update()

    yield SimpleNamespace(calls=calls, others=others, unplug=unplug, plug_in=plug_in)
    signal.disconnect(backend_slot)
    signal.disconnect(other_slot)
    devices[:] = kept
    device_initialization.joystick_devices_initialization()
    input_cache.Joystick().reconnected(_STICK)


def test_no_disabler_reloads_as_before(
    wired: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dd, "_manager", None)
    assert dd.devices_switching() is False
    wired.unplug()
    assert wired.others == [True]
    assert wired.calls == [False, True]


def test_disable_queued_keeps_the_profile_running(
    wired: SimpleNamespace,
    disabler: tuple[dd.DeviceDisabler, FakeWindows],
    steps: _Clock,
) -> None:
    d, windows = disabler
    windows.status[PAD] = dd.ENABLED
    _start_helper(d)
    gate = threading.Event()
    d._enqueue("hold", lambda: gate.wait(10))  # the worker is busy
    d.disable([("Pad", PAD)])
    assert dd.devices_switching()
    wired.unplug()
    assert wired.others == [True]  # other listeners still run
    assert wired.calls == []  # no Stop + Run
    gate.set()
    assert d.wait_idle(10)


def test_held_off_then_grace_then_reload_again(
    wired: SimpleNamespace,
    disabler: tuple[dd.DeviceDisabler, FakeWindows],
    steps: _Clock,
) -> None:
    d, windows = disabler
    windows.status[PAD] = dd.ENABLED
    _start_helper(d)
    d.disable([("Pad", PAD)])
    assert d.wait_idle(10)
    # Held off long after the job: the journal lists it "disabled".
    steps.t += 3600
    assert d.journal().state(PAD) == dd.DISABLED
    wired.unplug()
    assert wired.calls == []
    d.enable_pending()
    assert d.wait_idle(10)
    assert d.journal().state(PAD) == dd.ENABLED
    # Inside the grace window: the plug-in that follows doesn't reload.
    steps.t += dd.SWITCH_GRACE_S - 1
    wired.plug_in()
    assert wired.others == [True, True]
    assert wired.calls == []
    # After it: Device change behavior applies again.
    steps.t += 2
    assert not dd.devices_switching()
    wired.unplug()
    assert wired.calls == [False, True]


def test_recover_at_start_enable_keeps_the_profile_running(
    wired: SimpleNamespace,
    disabler: tuple[dd.DeviceDisabler, FakeWindows],
    steps: _Clock,
) -> None:
    d, windows = disabler
    # Left switched off by an earlier run.
    journal = d.journal()
    journal.set(PAD, "Pad", dd.DISABLED)
    journal.save()
    windows.status[PAD] = dd.DISABLED
    d.recover_at_start()
    # The enable is queued once the helper has started (bounded wait).
    for _ in range(200):
        if d.journal().state(PAD) == dd.ENABLED:
            break
        threading.Event().wait(0.05)
    assert d.wait_idle(10)
    assert d.journal().state(PAD) == dd.ENABLED
    wired.unplug()
    assert wired.others == [True]
    assert wired.calls == []


def test_a_device_left_to_be_enabled_does_not_pause_for_good(
    wired: SimpleNamespace,
    disabler: tuple[dd.DeviceDisabler, FakeWindows],
    steps: _Clock,
) -> None:
    # Unplugged while away: it stays "to be enabled" (S23), which is not
    # kept off, so the pause ends after the grace window.
    d, windows = disabler
    windows.status[PAD] = dd.ENABLED
    _start_helper(d)
    d.disable([("Pad", PAD)])
    assert d.wait_idle(10)
    windows.status[PAD] = dd.NOT_PRESENT
    d.enable_pending()
    assert d.wait_idle(10)
    assert d.journal().state(PAD) != dd.ENABLED
    steps.t += dd.SWITCH_GRACE_S + 1
    assert not dd.devices_switching()
    wired.unplug()
    assert wired.calls == [False, True]
