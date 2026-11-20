# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A Run opens every vJoy device an output module claims before the first
input, so the first input doesn't wait for the open (06 S106). A device vJoy
has turned off, or another program holds, is handled as on a write (S47); Stop
releases the devices again (S17). The vJoy driver is a fake: no real device."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import code_runner, shared_state
from gremlin.error import VJoyBusyError
from gremlin.modules import output
from gremlin.profile import Profile

_CLAIM = {"axes": [1, 2], "buttons": [1, 2, 3], "hats": []}
_NO_CLAIM = {"axes": [], "buttons": [], "hats": []}
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


class _Proxy:
    """Stand-in for VJoyProxy: opening is recorded, Stop's reset releases."""

    vjoy_devices: dict = {}
    opened: list[int] = []
    busy: set[int] = set()

    def __getitem__(self, index: int) -> object:
        _Proxy.opened.append(index)
        if index in _Proxy.busy:
            raise VJoyBusyError("held by another program")
        dev = SimpleNamespace()
        _Proxy.vjoy_devices = {**_Proxy.vjoy_devices, index: dev}
        return dev

    @classmethod
    def reset(cls) -> None:
        cls.vjoy_devices = {}


@pytest.fixture
def proxy() -> Iterator[type[_Proxy]]:
    _Proxy.vjoy_devices, _Proxy.opened, _Proxy.busy = {}, [], set()
    yield _Proxy
    _Proxy.vjoy_devices = {}


@pytest.fixture
def runner(
    monkeypatch: pytest.MonkeyPatch, proxy: type[_Proxy]
) -> Iterator[code_runner.CodeRunner]:
    """A real CodeRunner start/stop with the real output module; the vJoy
    driver, devices, sound and network are stand-ins."""
    for name in ("OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    monkeypatch.setattr(output, "refresh", lambda: None)
    modules = [
        (1, SimpleNamespace(name="vJoy 1", claim=_CLAIM)),
        (2, SimpleNamespace(name="vJoy 2", claim=_NO_CLAIM)),
        (3, SimpleNamespace(name="vJoy 3", claim=_CLAIM)),
        (4, SimpleNamespace(name="vJoy 4", claim=_CLAIM)),
    ]
    monkeypatch.setattr(output, "vjoy_modules", lambda: modules)
    monkeypatch.setattr(output, "_vjoy_proxy", lambda: proxy)
    monkeypatch.setattr(output, "vjoy_driver_found", lambda: True)
    monkeypatch.setattr(output, "vjoy_exists", lambda vid: int(vid) != 4)
    monkeypatch.setattr(output, "held_vjoy_ids", lambda: sorted(proxy.vjoy_devices))
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    output.clear_blocked_log()
    yield run
    run.stop()
    shared_state.set_runtime_active(False)
    output.clear_blocked_log()


def test_claimed_devices_are_held_right_after_run_start(
    runner: code_runner.CodeRunner, proxy: type[_Proxy]
) -> None:
    runner.start(Profile(), "Default")  # no input has arrived
    assert sorted(proxy.vjoy_devices) == [1, 3]


def test_a_device_without_claims_is_not_opened(
    runner: code_runner.CodeRunner, proxy: type[_Proxy]
) -> None:
    runner.start(Profile(), "Default")
    assert 2 not in proxy.opened


def test_a_turned_off_device_is_told_once_and_not_asked(
    runner: code_runner.CodeRunner,
    proxy: type[_Proxy],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        runner.start(Profile(), "Default")
    assert 4 not in proxy.opened  # the driver is never asked to open it
    assert len([r for r in caplog.records if "vJoy 4" in r.getMessage()]) == 1


def test_a_busy_device_does_not_stop_the_start(
    runner: code_runner.CodeRunner, proxy: type[_Proxy]
) -> None:
    proxy.busy = {1}
    with mock.patch("gremlin.signal.display_error") as shown:
        runner.start(Profile(), "Default")
    assert runner.is_running()
    assert sorted(proxy.vjoy_devices) == [3]
    assert shown.call_count == 1  # told once (S47)


def test_stop_releases_the_devices_again(
    runner: code_runner.CodeRunner, proxy: type[_Proxy]
) -> None:
    runner.start(Profile(), "Default")
    assert proxy.vjoy_devices
    runner.stop()
    assert proxy.vjoy_devices == {}


def test_nothing_is_opened_while_stopped(proxy: type[_Proxy]) -> None:
    with mock.patch.object(output, "_vjoy_proxy", return_value=proxy):
        assert output.open_claimed_vjoy() == []
    assert proxy.opened == []
