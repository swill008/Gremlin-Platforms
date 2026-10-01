# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device identity: one way to compare device GUIDs, and the built-in device IDs."""

from __future__ import annotations

import uuid

import dill
from vigem.ids import XBOX_TAB_GUID

# Devices that are not hardware.
LOGICAL_DEVICE: uuid.UUID = dill.UUID_LogicalDevice
KEYBOARD: uuid.UUID = dill.UUID_Keyboard
OSC: uuid.UUID = uuid.UUID("a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70")
XBOX: uuid.UUID = uuid.UUID(XBOX_TAB_GUID)


def guid_key(value: object) -> str:
    """Key for comparing two device GUIDs, whatever their form.

    Lower case with no braces or dashes; accepts strings, uuid.UUID and DILL
    GUID objects. Use it on both sides of a comparison; never save it.
    """
    if value is not None and hasattr(value, "uuid"):
        value = value.uuid
    return str(value or "").strip().strip("{}").replace("-", "").lower()


def stored_guid_key(value: object) -> str:
    """The upper-case form, without braces or dashes, that the module binding
    store and per-device settings already use as keys. Kept exactly as saved
    so existing settings still match."""
    return str(value or "").upper().replace("{", "").replace("}", "").replace("-", "")
