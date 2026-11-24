# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""What a profile piece points at. Every action, macro step and condition
declares its own references(); gremlin.usages walks the profile and asks
them, so a new piece is found by Search (and the walkers built on it) as
soon as it declares what it uses. The target shapes live here only."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace
from typing import Any

from gremlin.modules import ids
from gremlin.types import InputType

syslog = logging.getLogger("system")

# Roles a piece can declare (gremlin.usages adds runs-in-mode, inherited
# and uses-action itself).
ROLES = (
    "sends-output",
    "reads-input",
    "checks-output",
    "checks-input",
    "switches-mode",
    "loads-profile",
)


@dataclass(frozen=True)
class Reference:
    """One thing a piece uses.

    text: the words Search shows; "" on an action means the action's own
    Bindings text. where: names below the piece, e.g. ("Step 2",).
    why: the reason it can't be used (the cant_send_* text); it also makes
    it not found.
    """

    role: str
    target: tuple
    text: str = ""
    not_found: bool = False
    where: tuple[str, ...] = ()
    why: str = ""

    @property
    def missing(self) -> bool:
        """Not found: flagged, or a reason given."""
        return self.not_found or bool(self.why)


def type_int(value: object) -> int:
    """An input type as its number."""
    if isinstance(value, InputType):
        return value.value
    return int(value)  # type: ignore[arg-type]


def id_key(value: object) -> object:
    """A control id comparable whatever its form: keys as (scan, extended)."""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (int(value[0]), bool(value[1]))
    if hasattr(value, "scan_code"):
        key: Any = value
        return (int(key.scan_code), bool(key.is_extended))
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(value)


def vjoy(vjoy_id: object, input_type: object, control: object) -> tuple:
    """("vjoy", device id, input type number, control number)."""
    device: Any = vjoy_id
    number: Any = control
    return ("vjoy", int(device), type_int(input_type), int(number))


def xbox(pad: object, control: object) -> tuple:
    """("xbox", pad number, control value as text)."""
    value = str(getattr(control, "value", control))
    number: Any = pad
    return ("xbox", int(number), value)


def input_ref(guid: object, input_type: object, input_id: object) -> tuple:
    """("input", device guid key, input type number, control id key)."""
    return ("input", ids.guid_key(guid), type_int(input_type), id_key(input_id))


def keyboard(key: object) -> tuple:
    """A keyboard key as an input (a Key or (scan code, extended))."""
    return input_ref(ids.KEYBOARD, InputType.Keyboard, key)


def mode(name: object) -> tuple:
    """("mode", name)."""
    return ("mode", str(name))


def action(tag: object) -> tuple:
    """("action", tag)."""
    return ("action", str(tag))


def osc_out(target: object, address: object) -> tuple:
    """("osc-out", OSC target id, address)."""
    return ("osc-out", str(target or ""), str(address or ""))


def mouse(control: object) -> tuple:
    """("mouse", control): a MouseButton member's name ("Left", "WheelUp")
    or "Motion" for mouse motion."""
    return ("mouse", str(getattr(control, "name", control)))


def path_key(path: object) -> str:
    """A profile file path comparable whatever its spelling."""
    text = str(path or "")
    if not text:
        return ""
    return os.path.normcase(os.path.normpath(os.path.abspath(text)))


def profile(path: object) -> tuple:
    """("profile", path key)."""
    return ("profile", path_key(path))


_DEVICE_DB_TYPES = (
    InputType.JoystickAxis,
    InputType.JoystickButton,
    InputType.JoystickHat,
)


def input_label(
    input_type: object,
    input_id: object,
    device: object = None,
    mapping: object = None,
) -> str:
    """An input as the program shows it ("Button 3", "X Axis"): the one
    helper every page names inputs with (02 S10, D-05-UPSTREAM-B2). Given
    the device (or its device database mapping), its device_db.json name is
    applied as Options > Input names asks."""
    from gremlin import common

    try:
        plain = common.input_to_ui_string(input_type, input_id)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - an input type with no ui string
        return f"{input_type} {input_id}"
    if input_type not in _DEVICE_DB_TYPES:
        return plain
    if mapping is None and device is not None:
        mapping = _device_mapping(device)
    if mapping is None:
        return plain
    try:
        return str(mapping.input_name((input_type, input_id)))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - a mapping that can't name it
        syslog.debug("references: no database name for %s", plain, exc_info=True)
        return plain


def _device_mapping(device: object) -> object:
    """The device database mapping of a physical device, or None."""
    from gremlin.modules.device_class import INTERNAL_INPUTS

    uid = getattr(device, "uuid", device)
    if uid in INTERNAL_INPUTS:
        return None
    try:
        from gremlin.input_cache import DeviceDatabase

        return DeviceDatabase().get_mapping_by_uuid(uid)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - a device DILL doesn't know
        return None


def device_name(guid: object) -> str:
    """A device's shown name."""
    from gremlin.modules.device_class import INTERNAL_INPUTS

    uid = getattr(guid, "uuid", guid)
    if uid in INTERNAL_INPUTS:
        return INTERNAL_INPUTS[uid][0]
    name = ""
    try:
        from gremlin.ui.device_names import shown_name

        name = str(shown_name(uid) or "").strip()
    except Exception:  # noqa: BLE001 - a device nothing can name
        syslog.debug("references: no name for %s", uid, exc_info=True)
    if name:
        return name
    # Not plugged in: the one naming rule (module, profile, ...; 04 S32a).
    from gremlin import binding_edit

    return binding_edit.device_name(uid)


def place_parts(item: Any) -> tuple[str, str, str]:  # noqa: ANN401
    """An input's mode, shown device name and input name, the parts of
    place_label()."""
    device = getattr(item, "device_id", None)
    uid = getattr(device, "uuid", device)
    return (
        str(getattr(item, "mode", "") or ""),
        device_name(uid),
        input_label(item.input_type, item.input_id, uid),
    )


def place_label(item: Any) -> str:  # noqa: ANN401
    """Where an input is, as pick lists show it: "[mode] device - input"
    (05 S60b)."""
    mode_name, device, name = place_parts(item)
    return f"[{mode_name}] {device} - {name}"


def in_step(number: int, ref: Reference) -> Reference:
    """A macro step's reference as its macro declares it."""
    where = (f"Step {number}", *ref.where)
    return replace(ref, text=f"In a macro: {ref.text}", where=where)


def in_condition(number: int, ref: Reference) -> Reference:
    """A condition's reference as its Condition action declares it."""
    where = (f"Condition {number}", *ref.where)
    return replace(ref, text=f"Condition: {ref.text}", where=where)
