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
