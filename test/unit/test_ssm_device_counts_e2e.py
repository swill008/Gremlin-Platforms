# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The last time away's device counts (12 S21-S24, S38, S39), the real path:
the model's hooks, a real DeviceDisabler and the real core, read both through
the control API and in the window's Last time away row. Only Windows' edge
(status reader, helper, device list, displays, input) is faked."""

from __future__ import annotations

import json
import pathlib
import sys
import time
from collections.abc import Callable, Iterable, Iterator
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_ssm_core as _core  # noqa: E402  # pyright: ignore
import test_ssm_disable as _dis  # noqa: E402  # pyright: ignore

from gremlin import device_disable as dd  # noqa: E402

env = _core.env
KB, PAD, WHEEL, OTHER = _dis.KB, _dis.PAD, _dis.WHEEL, _dis.OTHER
NAMES = {KB: "Keyboard", PAD: "Pad", WHEEL: "Wheel"}


class FakeWatch:
    def __init__(self, on_arrival: Callable[[str], None]) -> None:
        self.on_arrival = on_arrival
        self.ids: list[str] = []

    def set_ids(self, ids: Iterable[str]) -> list[str]:
        fresh = [i for i in ids if i not in self.ids]
        self.ids = list(ids)
        return fresh

    def close(self) -> None:
        self.ids = []


class Rig:
    """One Screen Saver Mode on three Automatic devices."""

    def __init__(
        self,
        core_env: _core.Env,
        disabler: dd.DeviceDisabler,
        windows: _dis.FakeWindows,
        journal: pathlib.Path,
        watches: list[FakeWatch],
        window: object,
    ) -> None:
        self.mode, self.api, self.clk, _now, self.run, _t = core_env
        self.disabler = disabler
        self.windows = windows
        self.journal = journal
        self.watches = watches
        self.window = window

    def settle(self) -> None:
        assert self.disabler.wait_idle(10)

    def go_away(self) -> None:
        """Idle until the timer fires, the devices and the displays are off."""
        before = self.api.powered_off
        self.run(120)
        self.settle()
        self.run(1)
        assert self.api.powered_off == before + 1
        assert self.mode.status().keeping_off

    def come_back(self) -> None:
        self.clk.note_input(source=0x1001, kind="keyboard", press=True)
        self.run(1)
        assert not self.mode.status().keeping_off
        self.settle()

    def away(self) -> tuple[int, int]:
        from gremlin import control_api

        state = control_api._screen_saver_state()  # noqa: SLF001
        assert state is not None and state["last_away"] is not None
        return state["last_away"]["devices_off"], state["last_away"]["devices_back"]

    def row(self, label: str = "Last time away") -> dict:
        self.window.refreshStatus()  # type: ignore[attr-defined]
        rows = self.window.property("statusRows")  # type: ignore[attr-defined]
        return {r["label"]: r for r in rows}[label]

    def check(self, off: int, back: int, text: str) -> None:
        """The control API and the window say the same."""
        detail = self.row()["detail"]
        assert (self.away(), detail.split(" · ")[:2][-1]) == ((off, back), text)

    def replug(self, device_id: str) -> None:
        """Plugged in again, as Windows reports it: still disabled."""
        self.windows.status[device_id] = dd.DISABLED
        self.watches[-1].on_arrival(device_id)
        deadline = time.monotonic() + 10
        while self.windows.status[device_id] != dd.ENABLED:
            assert time.monotonic() < deadline, "never switched on again"
            time.sleep(0.02)
        self.settle()


@pytest.fixture
def rig(
    env: _core.Env,
    qapp: object,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Rig]:
    from gremlin import hid_report_scan
    from gremlin import screen_saver_mode as ssm
    from gremlin.config import Configuration
    from gremlin.signal import signal
    from gremlin.ui import screen_saver_mode_model as m

    windows = _dis.FakeWindows()
    journal = tmp_path / "screen saver mode" / "devices.json"
    windows.conn = _dis.FakeConn(windows, str(journal))
    windows.status.update(dict.fromkeys(NAMES, dd.ENABLED))
    watches: list[FakeWatch] = []

    def watch(on_arrival: Callable[[str], None]) -> FakeWatch:
        watches.append(FakeWatch(on_arrival))
        return watches[-1]

    disabler = dd.DeviceDisabler(
        journal_file=str(journal),
        key_file=str(tmp_path / "screen saver mode" / "helper.key"),
        launcher=windows.launch,
        listener_factory=windows.listen,
        status_reader=windows.read,
        connect_timeout_s=1.0,
        watch_factory=watch,
    )
    monkeypatch.setattr(dd, "_manager", disabler)
    monkeypatch.setattr(ssm, "_manager", env[0])
    monkeypatch.setattr(
        hid_report_scan,
        "present",
        lambda: [
            SimpleNamespace(instance_id=i)
            for i in NAMES
            if windows.read(i) != dd.NOT_PRESENT
        ],
    )
    monkeypatch.setattr(m, "_helper_refused", False)
    monkeypatch.setattr(m, "_helper_starting", False)
    m.register_options()
    cfg = Configuration()
    before = {n: cfg.value(m.SECTION, m.GROUP, n) for n in m.NAMES}
    window = None
    try:
        for name in (m.DEVICES, m.WAKE_PC):
            cfg.set(m.SECTION, m.GROUP, name, [])
        m.save_devices(m.merge_devices([], [(n, i, 9.0) for i, n in NAMES.items()]))
        window = m.ScreenSaverModeModel()
        env[0].set_device_hooks(m._before_power_off, m._after_input)  # noqa: SLF001
        env[0].apply(_core._off_only())  # noqa: SLF001
        yield Rig(env, disabler, windows, journal, watches, window)
    finally:
        disabler.stop_helper()
        if window is not None:
            window.setOpen(False)
            try:
                signal.configChanged.disconnect(window._on_config)  # noqa: SLF001
            except (RuntimeError, TypeError):
                pass
        for n, v in before.items():
            cfg.set(m.SECTION, m.GROUP, n, v)


def _start(rig: Rig) -> None:
    assert _dis._start(rig.disabler) == (True, "")  # noqa: SLF001


def test_three_off_three_back_agree_in_both_places(rig: Rig) -> None:
    _start(rig)
    assert rig.row()["value"] == "none yet"
    rig.go_away()
    assert {rig.windows.status[i] for i in NAMES} == {dd.DISABLED}
    assert rig.mode.status().last_away is None
    rig.come_back()
    assert {rig.windows.status[i] for i in NAMES} == {dd.ENABLED}
    rig.check(3, 3, "3 devices switched off and back on")
    assert rig.row("Devices back on")["value"] == "all back on"


def test_a_device_that_did_not_switch_off_is_not_counted(rig: Rig) -> None:
    _start(rig)
    assert rig.windows.conn is not None
    rig.windows.conn.fail_ids = {PAD}
    rig.go_away()
    assert rig.windows.status[PAD] == dd.ENABLED
    rig.come_back()
    rig.check(2, 2, "2 devices switched off and back on")


def test_an_old_leftover_changes_neither_count(rig: Rig) -> None:
    rig.journal.parent.mkdir(parents=True, exist_ok=True)
    entry = {"name": "Old", "state": "to be enabled", "time": "x", "result": ""}
    rig.journal.write_text(json.dumps({OTHER: entry}), encoding="utf-8")
    _start(rig)
    rig.settle()
    rig.go_away()
    rig.come_back()
    rig.check(3, 3, "3 devices switched off and back on")
    assert rig.row("Devices back on")["value"] == "Old is still switched off"
    rig.replug(OTHER)
    rig.check(3, 3, "3 devices switched off and back on")
    assert rig.row("Devices back on")["value"] == "all back on"


def test_a_stick_plugged_in_later_raises_the_back_count(rig: Rig) -> None:
    _start(rig)
    rig.go_away()
    del rig.windows.status[WHEEL]  # unplugged while away
    rig.come_back()
    rig.check(3, 2, "3 devices switched off, 2 back on")
    assert rig.row("Devices back on")["value"] == "Wheel is still switched off"
    rig.replug(WHEEL)
    rig.check(3, 3, "3 devices switched off and back on")
    assert rig.row("Devices back on")["value"] == "all back on"


def test_the_next_power_off_leaves_the_earlier_summary(rig: Rig) -> None:
    _start(rig)
    rig.go_away()
    del rig.windows.status[WHEEL]
    rig.come_back()
    rig.check(3, 2, "3 devices switched off, 2 back on")
    del rig.windows.status[PAD]
    rig.go_away()  # only the keyboard this time
    assert rig.windows.status[KB] == dd.DISABLED
    rig.check(3, 2, "3 devices switched off, 2 back on")
    rig.come_back()
    rig.check(1, 1, "1 device switched off and back on")
    # The first time's leftover comes back: not this time's device.
    rig.replug(WHEEL)
    rig.check(1, 1, "1 device switched off and back on")
