# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin's own virtual Xbox 360 pads, remembered by the devices they are.

A pad Gremlin plugs in (ViGEm) shows up as a DirectInput device with the
Xbox 360 hardware ID (VID 045E, PID 028E), the same ID a genuine wired
Xbox 360 pad has. Gremlin used to ignore every device with that ID (and
every name with "xbox 360 ... windows"), so real pads vanished. Now it
notes the devices present just before it plugs a pad in; a device with the
Xbox ID that appears after that is its own and is remembered (in the
settings, so a pad left behind by a crash is still known). Every other
device, real Xbox pads included, is a normal input device.

The joystick driver gives no device path, so this is the one dependable
link: a real Xbox pad plugged in within seconds of Gremlin plugging one
could be taken for Gremlin's (rare).
"""

from __future__ import annotations

import threading

from gremlin import clock
from vigem.ids import XBOX_HID_PID, XBOX_HID_VID

SETTING = ("global", "internal", "own-xbox-pads")
# How long after plugging a pad its device may take to appear.
_WINDOW_S = 5.0

_LOCK = threading.RLock()
_known: set[str] | None = None
_before: set[str] = set()
_expect_until = 0.0


def _key(guid: object) -> str:
    raw = getattr(guid, "uuid", guid)
    return str(raw).strip("{}").upper()


def has_xbox_id(dev: object) -> bool:
    """The Xbox 360 hardware ID: Gremlin's pads and genuine wired 360 pads."""
    try:
        vid = int(getattr(dev, "vendor_id", 0) or 0)
        pid = int(getattr(dev, "product_id", 0) or 0)
    except (TypeError, ValueError):
        return False
    return vid == XBOX_HID_VID and pid == XBOX_HID_PID


def _load() -> set[str]:
    global _known
    if _known is None:
        try:
            from gremlin.config import Configuration

            stored = Configuration().value(*SETTING) or []
        except Exception:
            stored = []
        _known = {str(g).upper() for g in stored}
    return _known


def _save() -> None:
    try:
        from gremlin.config import Configuration

        Configuration().set(*SETTING, sorted(_load()))
    except Exception:
        pass


def _present_with_xbox_id() -> set[str]:
    try:
        # The one door to the device driver (D-02-Q11).
        from gremlin.modules import hardware

        out = set()
        for dev in hardware.devices():
            if has_xbox_id(dev):
                out.add(_key(dev.device_guid))
        return out
    except Exception:
        return set()


def before_plug() -> None:
    """Called just before Gremlin plugs in a pad: what is there already."""
    global _before, _expect_until
    present = _present_with_xbox_id()
    with _LOCK:
        _before = present
        _expect_until = clock.monotonic() + _WINDOW_S


def note_device(dev: object) -> bool:
    """A device appeared (or is listed): True when it is one of Gremlin's own
    pads, remembering it if it is the pad Gremlin just plugged in."""
    if not has_xbox_id(dev):
        return False
    key = _key(getattr(dev, "device_guid", ""))
    with _LOCK:
        known = _load()
        if key in known:
            return True
        if clock.monotonic() <= _expect_until and key not in _before:
            known.add(key)
            _save()
            return True
    return False


def is_own_pad(dev: object) -> bool:
    """True for a device Gremlin plugged in (now or in an earlier session)."""
    return note_device(dev)


def forget_all() -> None:
    """For tests: nothing remembered, nothing expected."""
    global _known, _before, _expect_until
    with _LOCK:
        _known = set()
        _before = set()
        _expect_until = 0.0
