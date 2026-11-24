# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode S23: a switched-off device unplugged while away is
switched on when it is plugged in again, also when no game controller
change is reported (a disabled device never shows up as one). Every
Windows seam is faked, the device watch included."""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import pytest

from gremlin import clock, device_watch
from gremlin import device_disable as dd
from test.unit.test_ssm_disable import PAD, WHEEL, FakeConn, FakeWindows
from test.unit.test_ssm_switch_off_no_reload import (  # noqa: F401
    _Clock,
    steps,
    wired,
)


class FakeWatch:
    """DeviceWatch's contract: plug_in() reports only watched ids."""

    def __init__(self, on_arrival: Callable[[str], None]) -> None:
        self.on_arrival = on_arrival
        self.ids: list[str] = []
        self.closed = False
        # Runs once while the ids are being registered (before they count).
        self.before: Callable[[], None] | None = None

    def set_ids(self, ids: Iterable[str]) -> list[str]:
        wanted = list(ids)
        before, self.before = self.before, None
        if before is not None:
            before()
        fresh = [i for i in wanted if i not in self.ids]
        self.ids = wanted
        return fresh

    def close(self) -> None:
        self.closed = True
        self.ids = []

    def plug_in(self, device_id: str) -> None:
        assert device_id in self.ids
        self.on_arrival(device_id)


class Rig:
    def __init__(self, tmp_path: Path) -> None:
        self.windows = FakeWindows()
        journal_file = str(tmp_path / "screen saver mode" / "devices.json")
        self.conn = FakeConn(self.windows, journal_file)
        self.windows.conn = self.conn
        self.watches: list[FakeWatch] = []
        self.before: Callable[[], None] | None = None
        self.reads: list[str] = []
        self.d = dd.DeviceDisabler(
            journal_file=journal_file,
            key_file=str(tmp_path / "screen saver mode" / "helper.key"),
            launcher=self.windows.launch,
            listener_factory=self.windows.listen,
            status_reader=self.read,
            connect_timeout_s=1.0,
            watch_factory=self.watch,
        )

    def read(self, device_id: str) -> str:
        self.reads.append(device_id)
        return self.windows.read(device_id)

    def watch(self, on_arrival: Callable[[str], None]) -> FakeWatch:
        w = FakeWatch(on_arrival)
        w.before = self.before
        self.watches.append(w)
        return w

    def start(self) -> None:
        # A stopped helper's connection stays closed: a new one.
        if self.conn.closed:
            self.conn = FakeConn(self.windows, self.conn.journal_file)
            self.windows.conn = self.conn
        done = threading.Event()
        self.d.start_helper(lambda _ok, _e: done.set())
        assert done.wait(10)
        assert self.d.helper_running()

    def state(self, device_id: str = PAD) -> str:
        return self.d.journal().state(device_id)

    def idle(self) -> None:
        assert self.d.wait_idle(10)

    def unplugged_while_away(self) -> FakeWatch:
        """Switched off, unplugged, then the wake."""
        self.windows.status[PAD] = dd.ENABLED
        self.start()
        self.d.disable([("Pad", PAD)])
        self.idle()
        assert self.state() == dd.DISABLED
        assert self.watches == []
        self.windows.status[PAD] = dd.NOT_PRESENT
        self.d.enable_pending()
        self.idle()
        assert self.state() == dd.TO_BE_ENABLED
        return self.watches[-1] if self.watches else FakeWatch(print)

    def enables(self) -> int:
        return sum(r["op"] == "enable" for r in self.conn.requests)


def _until(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    for _ in range(int(seconds / 0.01)):
        if check():
            return True
        threading.Event().wait(0.01)
    return check()


@pytest.fixture(autouse=True)
def short_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dd, "ARRIVAL_DELAY_S", 0.05)
    monkeypatch.setattr(dd, "ARRIVAL_SECOND_TRY_S", 0.1)


@pytest.fixture
def rig(tmp_path: Path) -> Iterator[Rig]:
    r = Rig(tmp_path)
    yield r
    r.d.stop_helper()


def test_plugged_in_again_is_switched_on(rig: Rig) -> None:
    rig.unplugged_while_away()
    rig.windows.status[PAD] = dd.DISABLED
    for watch in rig.watches:  # no device_change_event
        watch.plug_in(PAD)
    assert _until(lambda: rig.state() == dd.ENABLED)
    rig.idle()
    assert rig.windows.status[PAD] == dd.ENABLED
    assert rig.watches[-1].ids == []


def test_several_arrivals_are_one_retry(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    watch = rig.unplugged_while_away()
    monkeypatch.setattr(dd, "ARRIVAL_DELAY_S", 0.3)
    rig.windows.status[PAD] = dd.DISABLED
    queued: list[str] = []
    enqueue = rig.d._enqueue

    def spy(name: str, run: Callable[[], None], counted: bool = True) -> None:
        queued.append(name)
        enqueue(name, run, counted)

    monkeypatch.setattr(rig.d, "_enqueue", spy)
    for _ in range(3):
        watch.plug_in(PAD)
    assert _until(lambda: rig.state() == dd.ENABLED)
    rig.idle()
    assert queued == ["enable"]
    assert rig.enables() == 1


def test_nothing_watched_when_nothing_waits(rig: Rig) -> None:
    rig.windows.status[PAD] = dd.ENABLED
    rig.start()
    rig.d.disable([("Pad", PAD)])
    rig.idle()
    rig.d.enable_pending()
    rig.idle()
    assert rig.state() == dd.ENABLED
    assert rig.watches == []


def test_a_present_device_is_not_watched(rig: Rig) -> None:
    # "pending system reboot" leaves it to be enabled while plugged in.
    rig.windows.status.update({PAD: dd.DISABLED, WHEEL: dd.NOT_PRESENT})
    journal = rig.d.journal()
    journal.set(PAD, "Pad", dd.DISABLED)
    journal.set(WHEEL, "Wheel", dd.DISABLED)
    journal.save()
    rig.conn.said[("enable", PAD)] = "pending system reboot"
    rig.start()
    rig.d.enable_pending()
    rig.idle()
    assert rig.state(PAD) == dd.TO_BE_ENABLED
    assert rig.watches[-1].ids == [WHEEL]
    assert rig.enables() == 1  # no retry loop


def test_back_before_the_watch_took_effect(rig: Rig) -> None:
    def back() -> None:
        rig.windows.status[PAD] = dd.DISABLED

    rig.before = back
    rig.windows.status[PAD] = dd.NOT_PRESENT
    journal = rig.d.journal()
    journal.set(PAD, "Pad", dd.DISABLED)
    journal.save()
    rig.start()
    rig.d.enable_pending()
    rig.idle()
    assert rig.state() == dd.ENABLED  # no arrival reported


def test_back_between_the_enable_and_the_watch(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Missing at the job's read, there at the read that picks the watched.
    journal = rig.d.journal()
    journal.set(PAD, "Pad", dd.DISABLED)
    journal.save()
    rig.start()
    reads: list[str] = []

    def read(device_id: str) -> str:
        reads.append(device_id)
        if len(reads) == 1:
            return dd.NOT_PRESENT
        rig.windows.status.setdefault(PAD, dd.DISABLED)
        return rig.windows.read(device_id)

    monkeypatch.setattr(rig.d, "_status", read)
    rig.d.enable_pending()
    rig.idle()
    assert rig.state() == dd.ENABLED


def test_still_missing_gets_one_second_try(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    watch = rig.unplugged_while_away()
    runs: list[int] = []
    enable = rig.d._enable

    def spy() -> None:
        runs.append(1)
        enable()

    monkeypatch.setattr(rig.d, "_enable", spy)
    watch.plug_in(PAD)
    assert _until(lambda: len(runs) == 2)
    threading.Event().wait(0.4)
    assert len(runs) == 2
    assert rig.enables() == 0
    assert watch.ids == [PAD]  # waits for the next event
    rig.windows.status[PAD] = dd.DISABLED
    watch.plug_in(PAD)
    assert _until(lambda: rig.state() == dd.ENABLED)


def test_second_try_switches_it_on(rig: Rig) -> None:
    watch = rig.unplugged_while_away()
    rig.reads.clear()
    watch.plug_in(PAD)
    # The first try has read it missing.
    assert _until(lambda: len(rig.reads) >= 2)
    rig.windows.status[PAD] = dd.DISABLED
    assert _until(lambda: rig.state() == dd.ENABLED)


def test_no_effect_after_stop(rig: Rig) -> None:
    watch = rig.unplugged_while_away()
    rig.windows.status[PAD] = dd.DISABLED
    watch.plug_in(PAD)  # its timer still waits
    rig.d.stop_helper()
    assert watch.closed
    rig.reads.clear()
    watch.on_arrival(PAD)
    threading.Event().wait(0.3)
    assert rig.reads == []
    assert rig.state() == dd.TO_BE_ENABLED
    assert rig.d._arrival_timer is None


def test_watched_again_after_the_helper_restarts(rig: Rig) -> None:
    rig.unplugged_while_away()
    rig.d.stop_helper()
    rig.start()
    assert _until(lambda: len(rig.watches) == 2 and rig.watches[1].ids == [PAD])
    rig.windows.status[PAD] = dd.DISABLED
    rig.watches[1].plug_in(PAD)
    assert _until(lambda: rig.state() == dd.ENABLED)


def test_back_while_the_helper_was_stopped(rig: Rig) -> None:
    rig.unplugged_while_away()
    rig.d.stop_helper()
    rig.windows.status[PAD] = dd.DISABLED
    rig.start()
    assert _until(lambda: rig.state() == dd.ENABLED)


def test_not_watched_while_the_helper_is_gone(rig: Rig) -> None:
    watch = rig.unplugged_while_away()
    rig.d._drop()
    rig.d.on_device_arrival()
    rig.idle()
    assert watch.ids == []


def test_the_real_watch_is_blocked_in_tests() -> None:
    with pytest.raises(dd.RealCallBlocked):
        dd._real_watch(lambda _i: None)


def test_with_the_real_device_watch(rig: Rig) -> None:
    """DeviceWatch itself, only its Windows calls faked."""
    registered: dict[str, Callable[[int], None]] = {}

    class Api:
        def register(self, device_id: str, callback: Callable[[int], None]) -> object:
            registered[device_id] = callback
            return device_id

        def unregister(self, token: object) -> None:
            del registered[str(token)]

    rig.d._watch_factory = lambda f: device_watch.DeviceWatch(f, Api())
    rig.windows.status[PAD] = dd.ENABLED
    rig.start()
    rig.d.disable([("Pad", PAD)])
    rig.idle()
    rig.windows.status[PAD] = dd.NOT_PRESENT
    rig.d.enable_pending()
    rig.idle()
    assert list(registered) == [PAD]
    rig.windows.status[PAD] = dd.DISABLED
    registered[PAD](device_watch.ACTION_INSTANCE_ENUMERATED)
    assert _until(lambda: rig.state() == dd.ENABLED)
    rig.idle()
    assert registered == {}


def test_other_controllers_reload_while_one_is_watched(
    wired,  # noqa: ANN001, F811
    rig: Rig,
    steps: _Clock,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert clock.monotonic() == steps.t
    monkeypatch.setattr(dd, "_manager", rig.d)
    watch = rig.unplugged_while_away()
    steps.t += dd.SWITCH_GRACE_S + 1
    assert watch.ids == [PAD]
    assert not dd.devices_switching()
    wired.unplug()
    assert wired.calls == [False, True]
    # The watched device's return, until something is switched on, neither.
    watch.plug_in(PAD)
    assert not dd.devices_switching()
