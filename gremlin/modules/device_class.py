# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Which class a device is, and what that class can do (03 S90b).

Every device is external (Windows lists it with its own id: sticks,
throttles, pedals, button boxes), an internal input (Keyboard, OSC, the
Logical Device) or an internal output (vJoy N, the program's Xbox pad). This
is the one place that knows the built-in ids and names; other code asks here.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from gremlin.modules import ids

if TYPE_CHECKING:
    from gremlin.modules.registry import Module


class DeviceClass(str, enum.Enum):
    EXTERNAL = "external"
    INTERNAL_INPUT = "internal-input"
    INTERNAL_OUTPUT = "internal-output"


# Internal inputs: id -> (name, slug).
INTERNAL_INPUTS: dict = {
    ids.KEYBOARD: ("Keyboard", "keyboard"),
    ids.OSC: ("OSC", "osc"),
    ids.LOGICAL_DEVICE: ("Logical Device", "logical_device"),
}

# Internal outputs with a fixed id: the Xbox pad. vJoy N has the driver's id
# and is known by its name ("vJoy <n>", registry.is_output_name), as is the
# Xbox pad without its id.
INTERNAL_OUTPUTS: dict = {
    ids.XBOX: ("Xbox 360 Controller", "xbox"),
}
VJOY = "vjoy"

_KIND_BY_KEY = {
    ids.guid_key(g): slug
    for g, (_, slug) in (*INTERNAL_INPUTS.items(), *INTERNAL_OUTPUTS.items())
}
_INPUT_SLUGS = {slug for _, slug in INTERNAL_INPUTS.values()}


def _plain(name: str) -> str:
    """Spaces collapsed, case ignored."""
    return " ".join(str(name or "").split()).casefold()


_INPUT_BY_NAME = {_plain(n): slug for n, slug in INTERNAL_INPUTS.values()}


def _output_kind(name: str) -> str:
    """"xbox" / "vjoy" for an output module name, "" otherwise."""
    from gremlin.modules.registry import is_gremlin_xbox_name, is_output_name

    if not name or not is_output_name(name):
        return ""
    return "xbox" if is_gremlin_xbox_name(name) else VJOY


def _is_vjoy_id(key: str) -> bool:
    """Whether this id is a live vJoy device (the driver's devices are the
    virtual ones). vJoy has no fixed id; no device list means not vJoy."""
    try:
        from gremlin.modules import store

        return any(
            getattr(dev, "is_virtual", False)
            and ids.guid_key(getattr(dev, "device_guid", "")) == key
            for dev in store.live_devices()
        )
    except Exception:  # noqa: BLE001 - no device list yet
        return False


def _input_kind(names: list[str], module: Module | None) -> str:
    """The internal input with one of these fixed names. A module file's
    name and slug also count in file-name form ("logical_device")."""
    for name in names:
        kind = _INPUT_BY_NAME.get(_plain(name), "")
        if kind:
            return kind
    if module is not None:
        from gremlin.modules.registry import plain_slug

        for name in names:
            if plain_slug(name) in _INPUT_SLUGS:
                return plain_slug(name)
    return ""


def device_kind(
    guid: object = None, name: str = "", module: Module | None = None
) -> str:
    """Which built-in device this is: "keyboard", "osc", "logical_device",
    "xbox" or "vjoy"; "" for an external device.

    A built-in id decides; a vJoy / Xbox output name is that output whatever
    its id; any other id is external (a stick named "Keyboard" with its own
    id is external), except a live vJoy device's id (the driver's, found in
    the live device list). With no id, Keyboard / OSC / Logical Device are known by
    their fixed names (spaces collapsed, case ignored)."""
    if module is not None:
        guid = guid or module.bound_guid
        names = [n for n in (name, module.name, module.slug) if n]
    else:
        names = [name] if name else []
    key = ids.guid_key(guid)
    if key in _KIND_BY_KEY:
        return _KIND_BY_KEY[key]
    if key and _is_vjoy_id(key):
        return VJOY
    if not key:
        kind = _input_kind(names, module)
        if kind:
            return kind
    for n in names:
        kind = _output_kind(n)
        if kind:
            return kind
    return ""


def class_of_kind(kind: str) -> DeviceClass:
    if not kind:
        return DeviceClass.EXTERNAL
    if kind in _INPUT_SLUGS:
        return DeviceClass.INTERNAL_INPUT
    return DeviceClass.INTERNAL_OUTPUT


def device_class(
    guid: object = None, name: str = "", module: Module | None = None
) -> DeviceClass:
    """The class of a device from its id and/or name, or its module file
    (its bound id, name and slug)."""
    return class_of_kind(device_kind(guid, name, module))


def is_internal(
    guid: object = None, name: str = "", module: Module | None = None
) -> bool:
    return device_class(guid, name, module) is not DeviceClass.EXTERNAL


def is_internal_input(
    guid: object = None, name: str = "", module: Module | None = None
) -> bool:
    return device_class(guid, name, module) is DeviceClass.INTERNAL_INPUT


def is_internal_output(
    guid: object = None, name: str = "", module: Module | None = None
) -> bool:
    return device_class(guid, name, module) is DeviceClass.INTERNAL_OUTPUT


def display_name(kind: str) -> str:
    """The built-in device's fixed name ("Keyboard", "OSC", ...)."""
    for name, slug in (*INTERNAL_INPUTS.values(), *INTERNAL_OUTPUTS.values()):
        if slug == kind:
            return name
    return "vJoy" if kind == VJOY else ""


def guid_of_kind(kind: str) -> uuid.UUID | None:
    """The fixed id of a built-in device (None for vJoy and external)."""
    for guid, (_, slug) in (*INTERNAL_INPUTS.items(), *INTERNAL_OUTPUTS.items()):
        if slug == kind:
            return guid
    return None


_EXT = DeviceClass.EXTERNAL
_IN = DeviceClass.INTERNAL_INPUT
_OUT = DeviceClass.INTERNAL_OUTPUT

# What each device can do: a class, or one built-in device by its kind where
# the rule is narrower than its class.
CAN: dict[str, frozenset] = {
    # Delete Device removes its module file; vJoy / Xbox keep theirs.
    "delete_device": frozenset({_EXT, _IN}),
    # A device row in the Device Library (input module files only).
    "library_device": frozenset({_EXT}),
    # The Library's Built-in inputs section (10 S6).
    "library_builtin": frozenset({"keyboard", "osc"}),
    # Copy, swap and calibrate are for external devices only (S90b).
    "copy": frozenset({_EXT}),
    "swap": frozenset({_EXT}),
    "calibrate": frozenset({_EXT}),
    "always_present": frozenset({_IN, _OUT}),
    # Inputs that run without an input-module claim.
    "no_claim_needed": frozenset({"osc", "logical_device"}),
    "button_map": frozenset({_EXT, _IN, _OUT}),
}


def can(
    action: str, guid: object = None, name: str = "", module: Module | None = None
) -> bool:
    """Whether the device can do this action (a key of CAN)."""
    kind = device_kind(guid, name, module)
    allowed = CAN[action]
    return class_of_kind(kind) in allowed or (bool(kind) and kind in allowed)
