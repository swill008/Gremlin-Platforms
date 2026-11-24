# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The vJoy driver checks (vJoyEnabled, GetvJoyVersion) run until they pass
once per process (upstream d3f55d9b); the vJoy guard forgets the pass before
each test so a later "vJoy not running" test still sees the check. Uses the
guard's stand-in vJoy only."""

from __future__ import annotations

from unittest import mock

import pytest
import vjoy_guard  # pyright: ignore[reportMissingImports]

from gremlin.error import VJoyError


class _Counter:
    def __init__(self, answer: object) -> None:
        self.answer = answer
        self.calls = 0

    def __call__(self) -> object:
        self.calls += 1
        return self.answer


def _open_twice(enabled: _Counter, version: _Counter) -> None:
    """Two opens of a device that passes the driver checks but can't be
    acquired (so no device is set up)."""
    from vjoy import vjoy

    iface = vjoy.VJoyInterface
    with (
        mock.patch.object(iface, "vJoyEnabled", enabled, create=True),
        mock.patch.object(iface, "GetvJoyVersion", version, create=True),
        mock.patch.object(
            iface, "GetVJDStatus", lambda i: vjoy.VJoyState.Free.value, create=True
        ),
        mock.patch.object(iface, "AcquireVJD", lambda i: False, create=True),
    ):
        for _ in range(2):
            with pytest.raises(VJoyError, match="acquire"):
                vjoy.VJoy(1)


def test_opening_devices_checks_the_driver_once() -> None:
    enabled, version = _Counter(True), _Counter(0x219)
    _open_twice(enabled, version)
    assert (enabled.calls, version.calls) == (1, 1)

    # The guard's reset (run before every test): the checks run again.
    vjoy_guard.reset_vjoy_checks()
    _open_twice(enabled, version)
    assert (enabled.calls, version.calls) == (2, 2)


def test_a_failed_check_is_tried_again() -> None:
    from vjoy import vjoy

    enabled = _Counter(False)
    iface = vjoy.VJoyInterface
    with mock.patch.object(iface, "vJoyEnabled", enabled, create=True):
        for _ in range(2):
            with pytest.raises(VJoyError, match="not currently running"):
                vjoy.VJoy(1)
    assert enabled.calls == 2


def test_the_guard_resets_the_pass_before_each_test() -> None:
    from vjoy import vjoy

    vjoy.VJoy._driver_verified = True
    vjoy_guard.pytest_runtest_setup(None)
    assert vjoy.VJoy._driver_verified is False
