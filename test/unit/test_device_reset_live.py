# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Reset Devices window follows plug/unplug live (02 S144, RW) and Xbox pads
start unticked (02 S145). Drives ResetDevicesModel with a fake device list,
emitting the program's own device-change signal; the reset runner is a fake
(pnputil is never run)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import clock, device_reset, event_handler, threads
from gremlin.ui import device_reset_model as drm

STICK_HID = "HID\\VID_231D&PID_3201\\A&1&0000"
STICK_USB = "USB\\VID_231D&PID_3201\\9&1D65FFE4&0&3"
PEDAL_HID = "HID\\VID_06A3&PID_0763\\B&2&0000"
PEDAL_USB = "USB\\VID_06A3&PID_0763\\5&ABC&0&1"
THR_HID = "HID\\VID_044F&PID_0404\\C&3&0000"
THR_USB = "USB\\VID_044F&PID_0404\\6&DEF&0&2"
PAD_HID = "HID\\VID_045E&PID_0B12&IG_00\\D&4&0000"
PAD_USB = "USB\\VID_045E&PID_0B12\\7&123&0&4"


def _row(hid: str, usb: str, name: str) -> dict:
    vid, pid = (int(p[4:8], 16) for p in usb.split("\\")[1].split("&"))
    return {
        "hid_id": hid, "usb_id": usb, "bus_id": "USB\\ROOT_HUB30\\4&1",
        "bus_desc": "Root Hub", "name": name, "windows_name": "USB Input Device",
        "vid": vid, "pid": pid,
    }


ALL = {
    STICK_USB: _row(STICK_HID, STICK_USB, "B Stick"),
    PEDAL_USB: _row(PEDAL_HID, PEDAL_USB, "A Pedals"),
    THR_USB: _row(THR_HID, THR_USB, "C Throttle"),
    PAD_USB: _row(PAD_HID, PAD_USB, "D Xbox Wireless Controller"),
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    plugged = [STICK_USB, PEDAL_USB]
    codes: dict[str, int] = {}
    vanish: set[str] = set()  # gone once the runner has run
    hold: list = []

    def present(instance: str) -> bool:
        ids = {i.upper() for u in plugged for i in (u, ALL[u]["hid_id"])}
        return instance.upper() in ids

    def runner(ids: list[str]) -> dict[str, int]:
        plugged[:] = [u for u in plugged if u not in vanish]
        return {i: codes.get(i, 0) for i in ids}

    device_reset.set_enumerator(lambda: [dict(ALL[u]) for u in plugged])
    device_reset.set_presence(present)
    device_reset.set_runner(runner)
    monkeypatch.setattr(drm, "profile_device_names", lambda: [])
    now = [0.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    monkeypatch.setattr(clock, "sleep", lambda s: now.__setitem__(0, now[0] + s))

    def start(name: str, target: object, *args: object, **_k: object) -> None:
        hold.append(lambda: target(*args))  # type: ignore[operator]

    monkeypatch.setattr(threads, "start", start)
    model = drm.ResetDevicesModel()
    yield SimpleNamespace(
        model=model, plugged=plugged, codes=codes, vanish=vanish, hold=hold
    )
    model.detach()
    device_reset.set_runner(None)
    device_reset.set_enumerator(None)
    device_reset.set_presence(None)


def _rows(model: drm.ResetDevicesModel) -> list[dict]:
    return [model.rowAt(i) for i in range(model.rowCount)]


def _by_usb(model: drm.ResetDevicesModel) -> dict[str, dict]:
    return {r["usbId"]: r for r in _rows(model)}


def _change(env: SimpleNamespace, plugged: list[str]) -> None:
    env.plugged[:] = plugged
    event_handler.EventListener().device_change_event.emit()


def _open(env: SimpleNamespace, hidden: list[str] | None = None) -> None:
    env.model.load({"hiddenIds": hidden or [], "games": [], "names": {}})


def test_unplugged_row_disappears_and_plugged_row_appears(env: SimpleNamespace) -> None:
    """S144: the list follows the device-change signal both ways."""
    _open(env, [STICK_HID])
    assert set(_by_usb(env.model)) == {STICK_USB, PEDAL_USB}
    _change(env, [STICK_USB])
    assert set(_by_usb(env.model)) == {STICK_USB}
    assert env.model.summary == "1 of 1 plugged-in devices ticked"
    _change(env, [STICK_USB, THR_USB])
    assert [r["usbId"] for r in _rows(env.model)] == [STICK_USB, THR_USB]


def test_a_new_hidden_device_arrives_ticked_and_footer_follows(
    env: SimpleNamespace,
) -> None:
    """S144: a newly plugged device is ticked if hidden (same rule as opening)."""
    _open(env, [STICK_HID, THR_HID])
    assert env.model.tickedCount == 1
    _change(env, [STICK_USB, PEDAL_USB, THR_USB])
    assert _by_usb(env.model)[THR_USB]["ticked"] is True
    assert env.model.tickedCount == 2
    assert env.model.summary == "2 of 3 plugged-in devices ticked"


def test_a_tick_survives_a_device_change(env: SimpleNamespace) -> None:
    _open(env)
    env.model.setTicked(0, True)
    _change(env, [STICK_USB, PEDAL_USB, THR_USB])
    assert _by_usb(env.model)[PEDAL_USB]["ticked"] is True


def test_known_but_unplugged_devices_are_not_listed(env: SimpleNamespace) -> None:
    """RW1a: no greyed "not plugged in" rows."""
    env.model.load({
        "hiddenIds": [STICK_HID, THR_HID], "games": [], "names": {},
        "known": [{"usb_id": THR_USB, "name": "Old throttle", "vid": 0x044F,
                   "pid": 0x0404}],
    })
    rows = _rows(env.model)
    assert [r["usbId"] for r in rows] == [PEDAL_USB, STICK_USB]
    assert all(r["result"] != "not plugged in" for r in rows)
    assert all("plugged" not in r for r in rows)


def test_a_row_being_reset_stays_until_its_result_is_in(env: SimpleNamespace) -> None:
    """RW2a."""
    _open(env, [STICK_HID])
    env.model.startReset()
    _change(env, [PEDAL_USB])  # the stick restarts: gone for a moment
    assert set(_by_usb(env.model)) == {STICK_USB, PEDAL_USB}
    assert _by_usb(env.model)[STICK_USB]["result"] == "resetting…"
    _change(env, [STICK_USB, PEDAL_USB])
    env.hold.pop()()
    from PySide6 import QtCore

    QtCore.QCoreApplication.processEvents()
    assert _by_usb(env.model)[STICK_USB]["result"] == "reset ✓ · back after 0.0 s"


@pytest.mark.parametrize(
    ("code", "first"),
    [
        (0, "reset ✓ · not back after 10 s"),
        (3010, "needs a Windows restart, or unplug it and plug it back in"),
    ],
)
def test_a_device_not_back_that_comes_back_says_so_and_logs_it(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture, code: int, first: str
) -> None:
    """RW3."""
    _open(env, [STICK_HID])
    env.codes[STICK_USB] = code
    env.model.startReset()
    if code == 0:
        env.vanish.add(STICK_USB)  # not back within the wait
    env.hold.pop()()
    from PySide6 import QtCore

    QtCore.QCoreApplication.processEvents()
    assert _by_usb(env.model)[STICK_USB]["result"] == first
    _change(env, [PEDAL_USB])  # still away (or unplugged by the user)
    assert _by_usb(env.model)[STICK_USB]["result"] == first
    with caplog.at_level(logging.INFO, logger="system"):
        _change(env, [STICK_USB, PEDAL_USB])
    row = _by_usb(env.model)[STICK_USB]
    assert row["result"] == "back ✓ (plugged back in)"
    assert row["resultKind"] == "ok"
    lines = [r.getMessage() for r in caplog.records if r.name == "system"]
    assert lines == [f"Reset Devices: B Stick ({STICK_USB}) → back ✓ (plugged back in)"]
    with caplog.at_level(logging.INFO, logger="system"):
        _change(env, [STICK_USB, PEDAL_USB])
    assert len([r for r in caplog.records if r.name == "system"]) == 1


def test_xbox_pads_start_unticked_with_a_note(env: SimpleNamespace) -> None:
    """S145: hidden or not, an Xbox pad (VID 045E) isn't ticked; it can be."""
    env.plugged.append(PAD_USB)
    _open(env, [STICK_HID, PAD_HID])
    pad = _by_usb(env.model)[PAD_USB]
    assert pad["ticked"] is False
    assert pad["note"] == drm.XBOX_NOTE == (
        "Xbox pads can't be restarted live: unplug and plug back in"
    )
    assert _by_usb(env.model)[STICK_USB]["note"] == ""
    index = [r["usbId"] for r in _rows(env.model)].index(PAD_USB)
    env.model.setTicked(index, True)
    assert _by_usb(env.model)[PAD_USB]["ticked"] is True


def test_an_xbox_pad_plugged_in_later_is_unticked(env: SimpleNamespace) -> None:
    _open(env, [PAD_HID])
    _change(env, [STICK_USB, PEDAL_USB, PAD_USB])
    pad = _by_usb(env.model)[PAD_USB]
    assert pad["ticked"] is False and pad["note"] == drm.XBOX_NOTE


def test_the_signal_is_let_go_when_the_window_closes(env: SimpleNamespace) -> None:
    _open(env)
    env.model.detach()
    _change(env, [STICK_USB])
    assert set(_by_usb(env.model)) == {STICK_USB, PEDAL_USB}
    _open(env)  # opened again: follows again, connected once
    _change(env, [PEDAL_USB])
    assert set(_by_usb(env.model)) == {PEDAL_USB}
