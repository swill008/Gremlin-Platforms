# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Devices that misbehaved (3 Oct review, DEV6, DEV9, DEV11, DEV14).

- A vJoy held by another program was retried and logged as an error on every
  write, and the user was never told (DEV6).
- A stick with a new id (another USB port, a reinstalled driver) had no
  calibration: its module was found by the old id only (DEV9).
- A stick plugged in while a profile ran had no claims until something else
  reloaded the modules (DEV11).
- Two threads asking for the same Xbox pad could each plug one in (DEV14).

The vJoy retry steps gremlin.clock.monotonic (GL-002); the Xbox pad test
holds the first plug-in until every thread has asked, instead of a fixed
sleep (GL-001, AU-119).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin.error import VJoyBusyError, VJoyError

# DEV6 ---------------------------------------------------------------------


def test_vjoy_held_elsewhere_raises_busy_without_an_error_log() -> None:
    from vjoy import vjoy

    iface = vjoy.VJoyInterface
    with (
        mock.patch.object(iface, "vJoyEnabled", lambda: True, create=True),
        mock.patch.object(iface, "GetvJoyVersion", lambda: 0x219, create=True),
        mock.patch.object(
            iface, "GetVJDStatus", lambda i: vjoy.VJoyState.Bust.value, create=True
        ),
        mock.patch.object(iface, "GetOwnerPid", lambda i: os.getpid() + 1, create=True),
        mock.patch.object(vjoy.logging.getLogger("system"), "error") as error,
    ):
        with pytest.raises(VJoyBusyError):
            vjoy.VJoyProxy()[7]
        assert vjoy.held_by_another_program(7)
    error.assert_not_called()


@pytest.fixture
def output() -> object:
    from gremlin.modules import output

    output.clear_blocked_log()
    yield output
    output.clear_blocked_log()


class _Opener:
    def __init__(self, results: list) -> None:
        self.results = results
        self.calls: list = []

    def __getitem__(self, index: int) -> object:
        self.calls.append(index)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_busy_vjoy_is_told_once_and_retried_every_few_seconds(output: object) -> None:
    device = object()
    opener = _Opener([VJoyBusyError("busy"), VJoyBusyError("busy"), device])
    now = [1000.0]
    with (
        mock.patch.object(output, "_vjoy_proxy", lambda: lambda: opener),
        mock.patch.object(output.clock, "monotonic", lambda: now[0]),
        mock.patch("gremlin.signal.display_error") as told,
    ):
        assert output._open_vjoy(2) is None
        for _ in range(50):  # a stream of writes: no new tries, no new messages
            assert output._open_vjoy(2) is None
        assert opener.calls == [2]
        now[0] += output._VJOY_RETRY
        assert output._open_vjoy(2) is None  # tried again, still busy
        now[0] += output._VJOY_RETRY
        assert output._open_vjoy(2) is device  # free: carries on by itself
    told.assert_called_once_with(
        "vJoy 2 is in use by another program.",
        "Its outputs won't move until that program lets it go.",
    )
    assert opener.calls == [2, 2, 2]


def test_a_new_run_tells_again(output: object) -> None:
    opener = _Opener([VJoyBusyError("busy"), VJoyBusyError("busy")])
    with (
        mock.patch.object(output, "_vjoy_proxy", lambda: lambda: opener),
        mock.patch("gremlin.signal.display_error") as told,
    ):
        output._open_vjoy(3)
        output.clear_blocked_log()  # Run
        output._open_vjoy(3)
    assert told.call_count == 2


def test_other_vjoy_failures_are_not_called_in_use(output: object) -> None:
    opener = _Opener([VJoyError("vJoy is not currently running")])
    with (
        mock.patch.object(output, "_vjoy_proxy", lambda: lambda: opener),
        mock.patch("gremlin.signal.display_error") as told,
    ):
        assert output._open_vjoy(1) is None
    told.assert_not_called()


def test_the_home_card_says_in_use(output: object) -> None:
    with mock.patch("vjoy.vjoy.held_by_another_program", lambda i: i == 2):
        assert output.vjoy_in_use_elsewhere(2)
        assert not output.vjoy_in_use_elsewhere(1)
    with mock.patch("vjoy.vjoy.held_by_another_program", side_effect=OSError):
        assert not output.vjoy_in_use_elsewhere(2)  # no vJoy: no note


# DEV9 ---------------------------------------------------------------------


def test_calibration_finds_a_stick_with_a_new_id_and_records_it(
    tmp_path: Path,
) -> None:
    from gremlin.modules import calibration, registry

    old_id, new_id = uuid.uuid4(), uuid.uuid4()
    path = tmp_path / "stick.json"
    path.write_text(json.dumps({"name": "Stick", "boundGuidLocal": str(old_id)}))
    module = registry.Module(
        slug="stick", path=path, doc={}, name="Stick", bound_guid=str(old_id),
        bound_name="Stick", direction="source", claim={},
    )
    device = SimpleNamespace(name="Stick", device_guid=new_id)
    with (
        mock.patch.object(calibration, "physical_devices", lambda: [device]),
        mock.patch.object(registry, "inputs", lambda: [module]),
        mock.patch.object(registry, "for_device", lambda name, guid: module),
    ):
        row = calibration.module_for_slug("stick")
        assert row is not None and row["guid"] == str(new_id) and row["rebind"]
        assert calibration.write_axis("stick", 1, (-100, -5, 5, 100, True))
    doc = json.loads(path.read_text())
    assert doc["calibration"]["1"] == [-100, -5, 5, 100, True]
    assert doc["boundGuidLocal"] == str(new_id)


def test_calibration_of_a_stick_found_by_id_leaves_its_binding(
    tmp_path: Path,
) -> None:
    from gremlin.modules import calibration, registry

    stick_id = uuid.uuid4()
    path = tmp_path / "stick.json"
    path.write_text(json.dumps({"name": "Stick", "boundGuidLocal": "kept"}))
    module = registry.Module(
        slug="stick", path=path, doc={}, name="Stick", bound_guid=str(stick_id),
        bound_name="Stick", direction="source", claim={},
    )
    device = SimpleNamespace(name="Stick", device_guid=stick_id)
    with (
        mock.patch.object(calibration, "physical_devices", lambda: [device]),
        mock.patch.object(registry, "inputs", lambda: [module]),
        # The stick's file is the one the shared rule picks for it.
        mock.patch.object(registry, "for_device", lambda *a, **k: module),
    ):
        assert calibration.module_for_slug("stick")["rebind"] is False
        assert calibration.write_axis("stick", 1, (-100, -5, 5, 100, True))
    assert json.loads(path.read_text())["boundGuidLocal"] == "kept"


# DEV11 --------------------------------------------------------------------


def test_input_modules_reload_when_a_device_is_plugged_in() -> None:
    from gremlin.modules import runtime

    connected: list = []
    listener = SimpleNamespace(
        joystick_event=SimpleNamespace(connect=lambda f: None),
        keyboard_event=SimpleNamespace(connect=lambda f: None),
        device_change_event=SimpleNamespace(connect=connected.append),
    )
    with (
        mock.patch.object(runtime, "EventListener", return_value=listener),
        mock.patch.object(runtime.InputModuleRuntime.klass, "reload"),
    ):
        bus = runtime.InputModuleRuntime.klass()
        assert connected == [bus.reload]


# DEV14 --------------------------------------------------------------------


def test_two_threads_asking_for_a_pad_plug_in_one() -> None:
    from vigem import xbox

    made: list = []
    asked: list = []
    workers_count = 6

    def slow_pad(pad_id: int, busp: int) -> object:
        made.append(pad_id)
        # Plugging in takes a moment: until every thread has asked.
        end = time.monotonic() + 10.0
        while len(asked) < workers_count and time.monotonic() < end:
            time.sleep(0.005)
        return SimpleNamespace(pad_id=pad_id)

    def ask() -> None:
        asked.append(1)
        got.append(proxy[1])

    proxy = object.__new__(xbox.XboxProxy)
    xbox.XboxProxy.__init__(proxy)
    got: list = []
    with (
        mock.patch.object(xbox, "XboxPad", slow_pad),
        mock.patch.object(xbox.XboxProxy, "_ensure_bus", lambda self: 1),
    ):
        workers = [threading.Thread(target=ask) for _ in range(workers_count)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(15.0)
    assert made == [1]
    assert len({id(pad) for pad in got}) == 1
