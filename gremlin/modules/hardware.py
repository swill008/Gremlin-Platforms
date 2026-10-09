# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The hardware as the input side sees it: device information by device id.

The layer rule: hardware is reached through the input side, never from the
UI directly. The UI models ask here instead of calling the device library
(dill) themselves.
"""

from __future__ import annotations

import uuid

import dill


def _guid(device_id: str | uuid.UUID) -> dill.GUID:
    if isinstance(device_id, uuid.UUID):
        return dill.GUID.from_uuid(device_id)
    return dill.GUID.from_str(str(device_id))


def device_info(device_id: str | uuid.UUID) -> dill.DeviceSummary:
    """The device's description (name, axes, buttons, hats...).

    Raises ValueError for an id the device library can't read, and for a
    device that isn't connected (the library describes one as empty: no
    name, no inputs), so callers don't keep an empty device as if it were
    the real one."""
    guid = _guid(device_id)
    if not dill.DILL.device_exists(guid):
        raise ValueError(f"Device {device_id} is not connected")
    return dill.DILL.get_device_information_by_guid(guid)


def device_connected(device_id: str | uuid.UUID) -> bool:
    """Whether a device with this id is connected now."""
    return bool(dill.DILL.device_exists(_guid(device_id)))


def plugged_in(guid: str | uuid.UUID | None, name: str = "") -> bool:
    """Whether a device is there now (03 S90a). Built-ins are always there:
    vJoy and Gremlin's Xbox output (registry.is_output_name), and Keyboard,
    OSC, Logical Device and the Xbox tab by their fixed ids (or, with no id,
    their fixed names). Any other device
    only while its id is in the live device list; never by its name, and a
    device with no id is not plugged in."""
    from gremlin.modules import ids
    from gremlin.modules.registry import is_output_name

    if is_output_name(name):
        return True
    key = ids.guid_key(guid)
    if not key:
        # A built-in card may carry no id: Keyboard, OSC and the Logical
        # Device are known by their fixed names, which no stick can have
        # here (a stick with its own id is always checked by its id).
        plain = " ".join(str(name or "").split()).casefold()
        return plain in {"keyboard", "osc", "logical device"}
    built_in = (ids.KEYBOARD, ids.OSC, ids.LOGICAL_DEVICE, ids.XBOX)
    if key in {ids.guid_key(g) for g in built_in}:
        return True
    try:
        return device_connected(str(guid))
    except Exception:  # noqa: BLE001 - an id the driver can't read isn't listed
        return False


def devices() -> list[dill.DeviceSummary]:
    """Every device the input driver lists now."""
    return [
        dill.DILL.get_device_information_by_index(i)
        for i in range(dill.DILL.get_device_count())
    ]
