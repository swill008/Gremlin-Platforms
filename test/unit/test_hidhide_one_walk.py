# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Opening Hardware Hide walks the HID device list once: Reset Devices'
availability is worked out from the rows the window already read, with the
same answer a separate gaming-only walk gives. Fakes only: no SetupAPI,
no HidHide driver."""

from __future__ import annotations

import ctypes
import inspect
import os
from collections.abc import Iterator

import pytest
import shiboken6

from gremlin import device_reset, hidhide_driver
from gremlin.ui import hidhide as hh

STICK = "HID\\VID_231D&PID_3201\\A&1&0000"
STICK_KBD = "HID\\VID_231D&PID_3201&MI_01\\A&1&0001"
KEYBOARD = "HID\\VID_046D&PID_C31C\\K&1&0000"
LOCKED = "HID\\VID_0001&PID_0002\\L&1&0000"
VIGEM = "HID\\VID_045E&PID_028E&IG_00\\V&1"

# HID collection -> (USB parent, gaming, denied)
_INSTANCES = {
    STICK: ("USB\\VID_231D&PID_3201\\9&1", True, False),
    STICK_KBD: ("USB\\VID_231D&PID_3201&MI_01\\9&2", False, False),
    KEYBOARD: ("USB\\VID_046D&PID_C31C\\8&1", False, False),
    LOCKED: ("USB\\VID_0001&PID_0002\\7&1", False, True),
    VIGEM: ("USB\\VID_045E&PID_028E\\6&1", True, False),
}
_PARENTS = {
    "USB\\VID_045E&PID_028E\\6&1": "ROOT\\SYSTEM\\0002",
}
_DESC = {"ROOT\\SYSTEM\\0002": "Nefarius Virtual Gamepad Emulation Bus"}


def _walk(groups: dict[str, list[str]], gaming_only: bool) -> list[dict]:
    """What the real walk builds: one row per container; a gaming-only walk
    keeps gaming and unreadable collections."""
    out = []
    for name, ids in groups.items():
        kept = [
            i for i in ids
            if not gaming_only or _INSTANCES[i][1] or _INSTANCES[i][2]
        ]
        if not kept:
            continue
        out.append({
            "instanceId": kept[0],
            "instanceIds": list(kept),
            "gamingIds": [i for i in kept if _INSTANCES[i][1] or _INSTANCES[i][2]],
            "name": name,
            "canHide": True,
            "photo": "",
            "gaming": any(_INSTANCES[i][1] for i in kept),
            "openDenied": False,
        })
    return out


class _Hid:
    def __init__(self) -> None:
        self.groups: dict[str, list[str]] = {}
        self.calls: list[bool] = []

    def walk(self, gaming_only: bool) -> list[dict]:
        self.calls.append(gaming_only)
        return _walk(self.groups, gaming_only)


@pytest.fixture
def fake_hid(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Hid]:
    hid = _Hid()
    monkeypatch.setattr(hh, "driver_present", lambda: False)
    monkeypatch.setattr(hh, "list_hid_devices", hid.walk)
    monkeypatch.setattr(hidhide_driver, "list_hid_devices", hid.walk)
    monkeypatch.setattr(hh, "_enrich_devices", lambda rows: rows)
    monkeypatch.setattr(hh, "_forget_unlisted_photos", lambda rows: None)
    monkeypatch.setattr(hh, "_load_games", lambda: [])

    def parent(instance: str) -> str:
        if instance in _INSTANCES:
            return _INSTANCES[instance][0]
        return _PARENTS.get(instance, "")

    monkeypatch.setattr(hidhide_driver, "_parent_instance", parent)
    monkeypatch.setattr(
        hidhide_driver, "_device_description", lambda i: _DESC.get(i, "")
    )
    monkeypatch.setattr(hidhide_driver, "_vid_pid", lambda usb: (0x231D, 0x3201))
    monkeypatch.setattr(device_reset, "os", _NtOs())
    device_reset.set_enumerator(None)
    yield hid
    device_reset.set_enumerator(None)


class _NtOs:
    """device_reset's os with name 'nt', so the real enumerate path runs on
    the fakes on every platform."""

    name = "nt"

    def __getattr__(self, item: str) -> object:
        return getattr(os, item)


CASES = {
    "stick": {"Stick": [STICK, STICK_KBD], "Keyboard": [KEYBOARD]},
    "keyboard only": {"Keyboard": [KEYBOARD]},
    "composite keyboard only": {"Stick": [STICK_KBD]},
    "unreadable only": {"Locked": [LOCKED]},
    "virtual pad only": {"Pad": [VIGEM]},
    "nothing": {},
}


@pytest.mark.parametrize("gaming_only", [False, True])
@pytest.mark.parametrize("case", list(CASES))
def test_one_open_walks_the_device_list_once(
    fake_hid: _Hid, monkeypatch: pytest.MonkeyPatch, case: str, gaming_only: bool
) -> None:
    fake_hid.groups = CASES[case]
    # The answer a separate gaming-only walk gives (the old way).
    expected = bool(device_reset.list_devices([]))
    fake_hid.calls.clear()

    monkeypatch.setattr(hh, "_saved_gaming_only", lambda: gaming_only)
    model = hh.HidHideModel()
    try:
        assert fake_hid.calls == [gaming_only]
        assert model.property("resetAvailable") is expected
        fake_hid.calls.clear()
        model.reload()
        assert fake_hid.calls == [gaming_only]
        assert model.property("resetAvailable") is expected
    finally:
        shiboken6.delete(model)


def test_gaming_only_rows_match_a_gaming_only_walk(fake_hid: _Hid) -> None:
    fake_hid.groups = CASES["stick"] | {"Locked": [LOCKED], "Pad": [VIGEM]}
    full = fake_hid.walk(False)
    gaming = fake_hid.walk(True)
    assert [r["instanceIds"] for r in hidhide_driver.gaming_only_rows(full)] == [
        r["instanceIds"] for r in gaming
    ]


@pytest.mark.skipif(os.name != "nt", reason="Windows structure")
def test_shellexecuteinfo_is_defined_once() -> None:
    cls = device_reset.SHELLEXECUTEINFOW
    assert issubclass(cls, ctypes.Structure)
    assert "class SHELLEXECUTEINFOW" not in inspect.getsource(
        device_reset._elevated_launch
    )
