# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""How Screen Saver Mode recognises a remembered device (12 S43): by maker
number, model number, name and reporting part (HID interface and
collection), so the same row in any USB port. Two identical devices share
one key. Without maker and model numbers: the full Windows id."""

from __future__ import annotations

import re
from typing import NamedTuple

# VID_28DE (USB) and VID&0002057E (Bluetooth; the last four digits).
_MAKER = re.compile(r"VID[_&]([0-9A-F]+)")
_MODEL = re.compile(r"PID[_&]([0-9A-F]+)")
_INTERFACE = re.compile(r"&MI_([0-9A-F]+)")
_COLLECTION = re.compile(r"&COL([0-9A-F]+)")


class DeviceNumbers(NamedTuple):
    maker: str
    model: str
    interface: str
    collection: str


def device_numbers(instance_id: str) -> DeviceNumbers:
    """The maker, model, interface (MI) and collection (Col) in a Windows
    id, "" for each one absent."""
    parts = str(instance_id).upper().split("\\")
    hardware = parts[1] if len(parts) > 1 else parts[0]

    def find(pattern: re.Pattern[str]) -> str:
        m = pattern.search(hardware)
        return m.group(1) if m else ""

    return DeviceNumbers(
        find(_MAKER)[-4:], find(_MODEL)[-4:], find(_INTERFACE), find(_COLLECTION)
    )


def has_numbers(numbers: DeviceNumbers) -> bool:
    return bool(numbers.maker and numbers.model)


def device_key(name: str, instance_id: str) -> str:
    """The key of a device's row (S43)."""
    numbers = device_numbers(instance_id)
    full = str(instance_id).strip().upper()
    if not has_numbers(numbers):
        return full
    shown = str(name).strip()
    # A device without a name is listed by its id, which the port changes.
    if shown.upper() == full:
        shown = ""
    return "|".join((*numbers, shown))
