# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode S38, D-12-DEVICE-COUNTS: the record disable() returns
counts what Windows confirmed off and back (gremlin/device_disable.py). The
real jobs run on the real worker; every Windows seam is faked."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import pytest

from gremlin import device_disable as dd
from gremlin import device_helper_protocol as protocol
from test.unit.test_ssm_disable import (
    EXIT_3010,
    KB,
    OTHER,
    PAD,
    WHEEL,
    FakeConn,
    FakeWindows,
    _entry,
    _journal,
    _settle,
    _start,
    _write,
)


class FakeWatch:
    """The device watch; the tests report each return themselves."""

    def __init__(self, on_arrival: Callable[[str], None]) -> None:
        self.on_arrival = on_arrival

    def set_ids(self, ids: Iterable[str]) -> list[str]:
        return []

    def close(self) -> None:
        pass


Env = tuple[dd.DeviceDisabler, FakeWindows, FakeConn, str]
DEVICES = [("Keyboard", KB), ("Pad", PAD), ("Wheel", WHEEL)]


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    windows = FakeWindows()
    journal_file = str(tmp_path / "screen saver mode" / "devices.json")
    conn = windows.conn = FakeConn(windows, journal_file)
    windows.status.update({i: dd.ENABLED for _name, i in DEVICES})
    disabler = dd.DeviceDisabler(
        journal_file=journal_file,
        key_file=str(tmp_path / "screen saver mode" / "helper.key"),
        launcher=windows.launch,
        listener_factory=windows.listen,
        status_reader=windows.read,
        connect_timeout_s=1.0,
        watch_factory=FakeWatch,
    )
    yield disabler, windows, conn, journal_file
    disabler.stop_helper()


def _off(
    disabler: dd.DeviceDisabler, devices: list[tuple[str, str]]
) -> dd.SwitchRecord:
    record = disabler.disable(devices)
    _settle(disabler)
    return record


def _on(disabler: dd.DeviceDisabler) -> None:
    disabler.enable_pending()
    _settle(disabler)


# SwitchRecord ----------------------------------------------------------------


def test_record_counts_each_device_once_and_back_only_if_off() -> None:
    record = dd.SwitchRecord(3, lambda: True)
    assert (record.asked, record.busy(), record.counts()) == (3, True, (0, 0))
    record.note_back(KB)  # never noted off
    record.note_off(KB)
    record.note_off(KB)
    record.note_off(PAD)
    assert record.counts() == (2, 0)
    record.note_back(KB)
    record.note_back(KB)
    record.note_back(OTHER)
    assert record.counts() == (2, 1)


# One time away -----------------------------------------------------------------


def test_all_off_and_back(env: Env) -> None:
    disabler, _, _, _ = env
    _start(disabler)
    record = _off(disabler, DEVICES)
    assert (record.asked, record.counts()) == (3, (3, 0))
    _on(disabler)
    assert record.counts() == (3, 3)
    _on(disabler)
    assert record.counts() == (3, 3)


def test_busy_until_the_jobs_end(env: Env) -> None:
    disabler, _, conn, _ = env
    _start(disabler)
    asked, answer = threading.Event(), threading.Event()
    real_send = conn.send

    def held_send(req: dict) -> None:
        asked.set()
        assert answer.wait(10)
        real_send(req)

    conn.send = held_send
    try:
        record = disabler.disable(DEVICES)
        assert record.busy()
        assert asked.wait(10)
        assert record.busy()
        assert record.counts() == (0, 0)
    finally:
        answer.set()
    _settle(disabler)
    assert not record.busy()
    assert record.counts() == (3, 0)


def test_a_device_that_fails_to_switch_off_is_not_counted(env: Env) -> None:
    disabler, _, conn, _ = env
    _start(disabler)
    conn.fail_ids = {PAD}
    record = _off(disabler, DEVICES)
    assert (record.asked, record.counts()) == (3, (2, 0))
    conn.fail_ids = set()
    _on(disabler)  # enables the failed one too (S34): not back, never off
    assert record.counts() == (2, 2)


def test_a_device_that_fails_to_come_back_counts_once_it_does(env: Env) -> None:
    disabler, _, conn, _ = env
    _start(disabler)
    record = _off(disabler, DEVICES)
    conn.fail_ids = {PAD}
    _on(disabler)
    assert record.counts() == (3, 2)
    conn.fail_ids = set()
    _on(disabler)
    assert record.counts() == (3, 3)


def test_switched_on_by_someone_else_counts_back(env: Env) -> None:
    disabler, windows, _, _ = env
    _start(disabler)
    record = _off(disabler, DEVICES)
    windows.status[KB] = dd.ENABLED
    _on(disabler)
    assert record.counts() == (3, 3)


def test_disabled_by_someone_else_or_absent_is_not_counted(env: Env) -> None:
    disabler, windows, _, _ = env
    windows.status[PAD] = dd.DISABLED
    windows.status[WHEEL] = dd.NOT_PRESENT
    _start(disabler)
    record = _off(disabler, [*DEVICES, ("Bad", 'USB\\X" & del')])
    assert (record.asked, record.counts()) == (4, (1, 0))
    _on(disabler)
    assert record.counts() == (1, 1)


def test_ours_already_disabled_is_counted(env: Env) -> None:
    disabler, windows, _, journal_file = env
    _write(journal_file, {KB: _entry("Keyboard", dd.DISABLED)})
    windows.status[KB] = dd.DISABLED
    _start(disabler)
    record = _off(disabler, DEVICES)
    assert record.counts() == (3, 0)
    _on(disabler)
    assert record.counts() == (3, 3)


def test_restart_undo_is_not_counted(env: Env) -> None:
    disabler, windows, conn, journal_file = env
    _start(disabler)
    conn.said[("disable", KB)] = EXIT_3010  # undone
    conn.said[("disable", PAD)] = EXIT_3010  # the undo fails
    conn.said[("enable", PAD)] = "error: pnputil exit 1: no"
    real_send = conn.send

    def send(req: dict) -> None:
        real_send(req)
        if req["op"] == "disable":
            windows.status[PAD] = dd.DISABLED

    conn.send = send
    record = _off(disabler, DEVICES)
    assert _journal(journal_file)[KB]["result"] == dd.RESTART_UNDONE
    assert record.counts() == (1, 0)
    conn.said.clear()
    _on(disabler)
    assert record.counts() == (1, 1)


def test_an_older_leftover_is_not_counted(env: Env) -> None:
    disabler, windows, _, journal_file = env
    _write(journal_file, {OTHER: _entry("Other", dd.TO_BE_ENABLED)})
    _start(disabler)
    record = _off(disabler, DEVICES)
    windows.status[OTHER] = dd.DISABLED  # plugged in
    _on(disabler)
    assert _journal(journal_file)[OTHER]["state"] == dd.ENABLED
    assert record.counts() == (3, 3)


def test_unplugged_counts_back_when_plugged_in_later(env: Env) -> None:
    disabler, windows, _, _ = env
    _start(disabler)
    record = _off(disabler, DEVICES)
    windows.status[WHEEL] = dd.NOT_PRESENT
    _on(disabler)
    assert record.counts() == (3, 2)
    windows.status[WHEEL] = dd.DISABLED
    disabler.on_device_arrival()
    _settle(disabler)
    assert record.counts() == (3, 3)


def test_no_helper_counts_nothing(env: Env) -> None:
    disabler, _, _, _ = env
    record = _off(disabler, DEVICES)
    assert (record.asked, record.busy(), record.counts()) == (3, False, (0, 0))
    _start(disabler)
    _on(disabler)
    assert record.counts() == (0, 0)


# The next time away --------------------------------------------------------------


def test_the_next_record_leaves_the_first_unchanged(env: Env) -> None:
    disabler, windows, _, _ = env
    _start(disabler)
    first = _off(disabler, DEVICES)
    windows.status[WHEEL] = dd.NOT_PRESENT
    _on(disabler)
    second = _off(disabler, DEVICES)
    windows.status[WHEEL] = dd.DISABLED
    _on(disabler)
    assert first.counts() == (3, 2)
    assert second.counts() == (2, 2)  # the wheel is the first's leftover


def test_enable_queued_before_the_next_disable_counts_for_the_first(
    env: Env,
) -> None:
    disabler, _, conn, _ = env
    _start(disabler)
    first = _off(disabler, DEVICES)
    asked, answer = threading.Event(), threading.Event()
    real_send = conn.send

    def held_send(req: dict) -> None:
        asked.set()
        assert answer.wait(10)
        real_send(req)

    conn.send = held_send
    try:
        # The worker is held in another job while both are queued.
        def hold() -> None:
            disabler._ask(protocol.make_request("ping", []), 1)

        disabler._enqueue("hold", hold)
        assert asked.wait(10)
        disabler.enable_pending()
        second = disabler.disable(DEVICES)
    finally:
        answer.set()
    _settle(disabler)
    assert first.counts() == (3, 3)
    assert second.counts() == (3, 0)
    _on(disabler)
    assert first.counts() == (3, 3)
    assert second.counts() == (3, 3)


def test_enable_asked_after_a_queued_disable_runs_after_it(env: Env) -> None:
    # SSM-ENABLE-MERGED-BEFORE-DISABLE: an enable already waited in the queue
    # when the devices were to be switched off; the wake's own enable must
    # still run after that disable.
    disabler, windows, _, journal_file = env
    _start(disabler)
    held, gate = threading.Event(), threading.Event()

    def hold() -> None:
        held.set()
        assert gate.wait(10)

    disabler._enqueue("hold", hold)
    try:
        assert held.wait(10)
        disabler.enable_pending()
        record = disabler.disable(DEVICES)
        disabler.enable_pending()  # the wake
        disabler.enable_pending()  # still merged with the wake's
        assert disabler._jobs.qsize() == 3
    finally:
        gate.set()
    _settle(disabler)
    assert record.counts() == (3, 3)
    for _name, device_id in DEVICES:
        assert windows.status[device_id] == dd.ENABLED
        assert _journal(journal_file)[device_id]["state"] == dd.ENABLED
