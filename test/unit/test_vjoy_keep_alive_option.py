# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The vJoy keep-alive (06 S54) is an Options switch, off at first: each
reset counts as user input, so Windows turns the displays on about once a
minute (claude/audits/2026-11-22-display-wakes-vjoy-keepalive). Off, a held
vJoy arms no keep-alive and is never reset; on, it is reset 60 s after its
last write as before. The switch is read when a device is opened, so a
change applies at the next Run, not in the middle of one.

These run the real open path (output._open_vjoy) on a fake vJoy driver,
never the real device, with a stepped gremlin.clock and the keep-alive's
Run timers kept here and fired by the test.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import clock, run_scope
from gremlin.config import Configuration
from gremlin.modules import output

_KEY = ("global", "vjoy", "keep-alive")
_ROOT = Path(__file__).resolve().parents[2]


class _Device:
    """A held vJoy: when it was last written and when it was reset."""

    def __init__(self, now: list[float]) -> None:
        self._now = now
        self.last_active = now[0]
        self.resets: list[float] = []

    def reset(self) -> None:
        self.resets.append(self._now[0])
        self.last_active = self._now[0]


class _Driver:
    """A stepped clock, the fake vJoy proxy and the keep-alive's timers
    (due time, function, args), fired by run_until."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.now = [1000.0]
        self.timers: list[list[Any]] = []
        self.devices: dict[int, _Device] = {}
        driver = self

        class Timer:
            def __init__(self, entry: list[Any]) -> None:
                self.entry = entry

            def is_alive(self) -> bool:
                return self.entry in driver.timers

            def cancel(self) -> None:
                if self.entry in driver.timers:
                    driver.timers.remove(self.entry)

        def timer(_name: str, seconds: float, fn: Any, *args: object) -> Timer:  # noqa: ANN401
            entry = [driver.now[0] + seconds, fn, args]
            driver.timers.append(entry)
            return Timer(entry)

        class Proxy:
            vjoy_devices: dict[int, _Device] = {}

            def __getitem__(self, vid: int) -> _Device:
                device = _Device(driver.now)
                driver.devices[vid] = device
                Proxy.vjoy_devices = {**Proxy.vjoy_devices, vid: device}
                return device

            @classmethod
            def reset(cls) -> None:
                cls.vjoy_devices = {}

        self.proxy = Proxy
        monkeypatch.setattr(clock, "monotonic", lambda: driver.now[0])
        monkeypatch.setattr(output.run_scope, "timer", timer)
        monkeypatch.setattr(output, "_vjoy_proxy", lambda: Proxy)
        monkeypatch.setattr(output, "_keep_alive", {})

    def run_until(self, end: float) -> None:
        for _ in range(100):
            due = [t for t in self.timers if t[0] <= end]
            if not due:
                break
            entry = min(due, key=lambda t: t[0])
            self.timers.remove(entry)
            self.now[0] = entry[0]
            entry[1](*entry[2])
        self.now[0] = end

    def next_run(self) -> None:
        """Stop, then Start: the devices are released and opened again."""
        output.reset_vjoy()
        run_scope.stop()
        run_scope.begin()


@pytest.fixture
def driver(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Driver]:
    before = Configuration().value(*_KEY)
    run_scope._reset_for_tests()
    run_scope.begin()
    fake = _Driver(monkeypatch)
    try:
        yield fake
    finally:
        output.reset_vjoy()
        run_scope.stop()
        run_scope._reset_for_tests()
        Configuration().set(*_KEY, before)


def _switch(on: bool) -> None:
    Configuration().set(*_KEY, on)


def test_the_keep_alive_is_off_in_new_settings(tmp_path: Path) -> None:
    """A first start (no settings file yet) has the switch off. Its own
    process, so the option is registered into empty settings."""
    env = dict(os.environ)
    env["USERPROFILE"] = str(tmp_path)
    env["userprofile"] = str(tmp_path)
    env["QT_QPA_PLATFORM"] = "offscreen"
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from gremlin.modules import output;"
        "from gremlin.config import Configuration;"
        "print(repr(Configuration().value('global', 'vjoy', 'keep-alive')),"
        " output.keep_alive_enabled())"
    )
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    done = proc_tree.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines()[-1] == "False False"


def test_keep_alive_enabled_follows_the_switch(driver: _Driver) -> None:
    _switch(False)
    assert output.keep_alive_enabled() is False
    _switch(True)
    assert output.keep_alive_enabled() is True


def test_off_a_held_vjoy_arms_no_keep_alive_and_is_never_reset(
    driver: _Driver,
) -> None:
    _switch(False)
    output._open_vjoy(2)
    assert driver.timers == []
    assert output._keep_alive == {}
    driver.run_until(driver.now[0] + 300.0)
    assert driver.devices[2].resets == []
    assert run_scope.pending_timers() == []


def test_on_an_idle_held_vjoy_is_reset_after_60_s(driver: _Driver) -> None:
    _switch(True)
    opened = driver.now[0]
    output._open_vjoy(2)
    assert len(driver.timers) == 1
    driver.run_until(opened + 130.0)
    assert driver.devices[2].resets == [
        pytest.approx(opened + 60.0),
        pytest.approx(opened + 120.0),
    ]


def test_turned_on_mid_run_applies_at_the_next_run(driver: _Driver) -> None:
    _switch(False)
    output._open_vjoy(2)
    output._open_vjoy(2)  # written again in the same Run: still held
    _switch(True)
    driver.run_until(driver.now[0] + 300.0)
    assert driver.devices[2].resets == []  # not in the middle of the Run
    assert driver.timers == []

    driver.next_run()
    opened = driver.now[0]
    output._open_vjoy(2)
    driver.run_until(opened + 61.0)
    assert driver.devices[2].resets == [pytest.approx(opened + 60.0)]


def test_turned_off_mid_run_applies_at_the_next_run(driver: _Driver) -> None:
    _switch(True)
    opened = driver.now[0]
    output._open_vjoy(2)
    _switch(False)
    driver.run_until(opened + 130.0)
    # Already armed: this Run keeps it until Stop.
    assert len(driver.devices[2].resets) == 2

    driver.next_run()
    assert driver.timers == []
    output._open_vjoy(2)
    assert driver.timers == []
    driver.run_until(driver.now[0] + 300.0)
    assert driver.devices[2].resets == []


def test_options_shows_the_switch_under_general_vjoy() -> None:
    from gremlin.ui import option

    general = dict(dict(option.main_layout())["General"])
    assert general["vJoy"] == [_KEY]
    assert option.entry_title("keep-alive", "/".join(_KEY)) == (
        "Keep vJoy devices awake"
    )
