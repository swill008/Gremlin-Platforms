# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""HidHide trace (D-01-TRACE item 7): every driver call written with its
result, the 5 s watch naming outside changes, HidHide in use said once, a
ticked stick not hidden under its current instance path. The control
device is faked below the public calls (_open_control/_ioctl): the real
HidHide driver is never opened."""

from __future__ import annotations

import pathlib
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import clock, hidhide_watch, trace, util
from gremlin import hidhide_driver as drv

_OLD = r"HID\VID_231D&PID_0200\7&OLD&0&0000"
_NEW = r"HID\VID_231D&PID_0200\7&NEW&0&0000"
_GAME = r"\Device\HarddiskVolume3\Games\StarCitizen.exe"


class _HidHide:
    """HidHide's control device: its state, and busy while its window is open."""

    def __init__(self) -> None:
        self.cloak = True
        self.inverse = False
        self.apps = [_GAME]
        self.devices = [_OLD]
        self.busy = False
        self.calls = 0

    def open(self) -> object:
        self.calls += 1
        return drv._opened(None, 5) if self.busy else drv._opened("handle", 0)

    def ioctl(
        self, handle: object, code: int, inn: bytes | None = None, out: int = 0
    ) -> tuple[bool, bytes]:
        if code == drv.IOCTL_GET_ACTIVE:
            return True, bytes([self.cloak])
        if code == drv.IOCTL_GET_INVERSE:
            return True, bytes([self.inverse])
        if code == drv.IOCTL_SET_ACTIVE:
            self.cloak = bool(inn and inn[0])
            return True, b""
        if code == drv.IOCTL_SET_INVERSE:
            self.inverse = bool(inn and inn[0])
            return True, b""
        if code == drv.IOCTL_GET_WHITELIST:
            return True, drv._encode_multi_sz(self.apps)
        if code == drv.IOCTL_GET_BLACKLIST:
            return True, drv._encode_multi_sz(self.devices)
        if code == drv.IOCTL_SET_WHITELIST:
            self.apps = drv._decode_multi_sz(inn or b"")
            return True, b""
        if code == drv.IOCTL_SET_BLACKLIST:
            self.devices = drv._decode_multi_sz(inn or b"")
            return True, b""
        return False, b""


@pytest.fixture
def hidhide(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[_HidHide]:
    from gremlin import device_initialization
    from gremlin.ui import hidhide as hh

    fake = _HidHide()
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(drv, "_open_control", fake.open)
    monkeypatch.setattr(drv, "_close", lambda handle: None)
    monkeypatch.setattr(drv, "_ioctl", fake.ioctl)
    monkeypatch.setattr(
        drv,
        "list_hid_devices",
        lambda gaming_only: [
            {"instanceId": _NEW, "instanceIds": [_NEW], "name": "EVO R"}
        ],
    )
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: [])
    monkeypatch.setattr(hh, "_hidhide_managed", lambda: False)
    monkeypatch.setattr(hh, "_load_links", lambda: {})
    # No real running program is ever compared with a HidHide change.
    from gremlin import input_tester_link, process_paths

    monkeypatch.setattr(process_paths, "running_programs", lambda *_a: [])
    monkeypatch.setattr(input_tester_link, "_last_change", None)
    trace._reset_for_tests()
    if hidhide_watch._on_change in trace._hooks:  # installed by an earlier test
        trace._hooks.remove(hidhide_watch._on_change)
    hidhide_watch.stop()
    hidhide_watch._reset()
    drv.take_program_marks()
    drv._opened("handle", 0)
    trace.set_hidhide(True)
    trace.set_enabled(True)
    yield fake
    if hidhide_watch._on_change in trace._hooks:
        trace._hooks.remove(hidhide_watch._on_change)
    trace.set_enabled(False)
    hidhide_watch.stop()
    _watch_threads_end()
    hidhide_watch._reset()
    trace.set_hidhide(False)
    trace._reset_for_tests()


def _watch_threads_end() -> None:
    """Waits (2 s at most) for a watch timer that already fired to finish."""
    from gremlin import threads

    deadline = clock.monotonic() + 2.0
    while clock.monotonic() < deadline and any(
        "HidHide watch" in name for name in threads.running()
    ):
        clock.sleep(0.01)


def _hidhide_lines() -> list[tuple[str, bool]]:
    return [(line[3], line[4]) for line in trace.lines() if line[2] == trace.HIDHIDE]


def _warnings() -> list[str]:
    return [text for text, warning in _hidhide_lines() if warning]


def test_cloak_turned_off_outside_the_program_is_one_warning(hidhide: _HidHide) -> None:
    hidhide_watch.check()
    assert _warnings() == []
    hidhide.cloak = False  # the HidHide window turned it off
    hidhide_watch.check()
    hidhide_watch.check()
    assert _warnings() == ["Cloak turned off (not by Gremlin-Platforms)"]
    assert "Cloak turned off" in trace.notice()


def test_an_app_dropped_and_the_mode_changed_outside_are_named(
    hidhide: _HidHide,
) -> None:
    hidhide_watch.check()
    hidhide.apps = []
    hidhide.inverse = True
    hidhide_watch.check()
    assert set(_warnings()) == {
        "StarCitizen.exe no longer on the list (not by Gremlin-Platforms)",
        "mode changed to Block list (not by Gremlin-Platforms)",
    }


def test_the_programs_own_change_is_named_as_the_programs(hidhide: _HidHide) -> None:
    hidhide_watch.check()
    assert drv.set_active(False) is True
    hidhide_watch.check()
    lines = _hidhide_lines()
    assert ("set cloak off → ok", False) in lines
    assert ("Cloak turned off by Gremlin-Platforms", False) in lines
    assert _warnings() == []


def test_hidhide_in_use_is_said_once_until_a_call_works(hidhide: _HidHide) -> None:
    hidhide.busy = True
    assert drv.get_active() is False
    assert drv.last_open_error() == 5
    drv.get_blacklist()
    hidhide_watch.check()
    hidhide_watch.check()
    busy = [text for text, _ in _hidhide_lines() if "in use by another program" in text]
    assert busy == ["read cloak → in use by another program (HidHide window open)"]
    hidhide.busy = False
    hidhide_watch.check()  # free again: read, then quiet no more
    hidhide.busy = True
    hidhide_watch.check()
    busy = [text for text, _ in _hidhide_lines() if "in use by another program" in text]
    assert busy[-1] == "HidHide in use by another program" and len(busy) == 2


def test_every_call_writes_what_was_sent_and_the_result(hidhide: _HidHide) -> None:
    drv.set_whitelist([_GAME])
    drv.set_blacklist([_OLD])
    drv.get_inverse()
    texts = [text for text, _ in _hidhide_lines()]
    assert texts == [
        "set app list 1 app: StarCitizen.exe → ok",
        f"set device list 1 device: {_OLD} → ok",
        "read mode → ok: Allow list",
    ]


def test_a_ticked_stick_not_on_the_hidden_list_is_a_warning(
    hidhide: _HidHide, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import device_initialization

    stick_id = uuid.uuid4()
    stick = SimpleNamespace(
        device_guid=SimpleNamespace(uuid=stick_id),
        name="EVO R",
        vendor_id=0x231D,
        product_id=0x0200,
        is_virtual=False,
    )
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: [stick])
    trace.set_device(stick_id, True)
    hidhide_watch.check()
    hidhide_watch.check()
    expected = f"EVO R is NOT hidden: it is {_NEW}, which isn't on the list"
    assert _warnings() == [expected]
    hidhide.devices = [_NEW]  # hidden under its new path: clears
    hidhide_watch.check()
    assert _warnings().count(expected) == 1


def test_off_or_unticked_writes_nothing_and_reads_nothing(hidhide: _HidHide) -> None:
    trace.set_hidhide(False)
    before = hidhide.calls
    hidhide_watch.check()
    assert hidhide.calls == before
    drv.get_active()
    trace.set_hidhide(True)
    trace.set_enabled(False)
    hidhide_watch.check()
    drv.set_active(False)
    assert _hidhide_lines() == []


def test_install_runs_the_watch_only_while_tracing(hidhide: _HidHide) -> None:
    trace.set_enabled(False)
    hidhide_watch.install()
    hidhide_watch.install()
    assert not hidhide_watch.running()
    trace.set_enabled(True)
    assert hidhide_watch.running()
    trace.set_enabled(False)
    assert not hidhide_watch.running()


def test_hidhide_apart_from_the_saved_setup_is_one_warning(
    hidhide: _HidHide, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import hidhide as hh

    monkeypatch.setattr(hh, "_hidhide_managed", lambda: True)
    monkeypatch.setattr(hh, "_saved_cloak", lambda: True)
    monkeypatch.setattr(hh, "_saved_block_list", lambda: False)
    monkeypatch.setattr(
        hh, "_load_games", lambda: [{"name": "SC", "path": r"C:\Games\StarCitizen.exe"}]
    )
    monkeypatch.setattr(hh, "_saved_hidden", lambda: [_OLD])
    hidhide.cloak = False
    hidhide.apps = []
    hidhide_watch.check()
    hidhide_watch.check()
    assert sorted(_warnings()) == [
        "Cloak is off, but Gremlin-Platforms has it saved on",
        "StarCitizen.exe is not on HidHide's app list (saved in Gremlin-Platforms)",
    ]
