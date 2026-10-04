# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Xbox tab GUID and ViGEm HID detection. Safe to import without the DLL."""

from __future__ import annotations

import uuid
from typing import Any

XBOX_TAB_GUID = "c8e4b6a1-3d92-4f17-9a50-7b2c4e8f1d60"
XBOX_HID_VID = 0x045E
XBOX_HID_PID = 0x028E


def vigem_client_error() -> str:
    try:
        from vigem import vigem_client

        return vigem_client.load_error() or ""
    except Exception as exc:
        return str(exc)


def is_vigem_xbox_summary(dev: Any) -> bool:
    """True for one of Gremlin's own virtual Xbox pads (vigem.own_pads), not
    for a real Xbox pad, though both have the Xbox 360 hardware ID."""
    from vigem import own_pads

    return own_pads.is_own_pad(dev)


def is_vigem_xbox_guid(device_guid: Any) -> bool:
    try:
        import dill

        if hasattr(device_guid, "uuid"):
            uid = device_guid.uuid
        else:
            uid = uuid.UUID(str(device_guid))
        info = dill.DILL.get_device_information_by_guid(dill.GUID.from_uuid(uid))
        return is_vigem_xbox_summary(info)
    except Exception:
        return False
