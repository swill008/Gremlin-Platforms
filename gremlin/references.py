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


def input_label(input_type: object, input_id: object) -> str:
    """An input as the program shows it ("Button 3", "X Axis")."""
    from gremlin import common

    try:
        return common.input_to_ui_string(input_type, input_id)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - an input type with no ui string
        return f"{input_type} {input_id}"


def device_name(guid: object) -> str:
    """A device's shown name."""
    from gremlin.modules.device_class import INTERNAL_INPUTS

    uid = getattr(guid, "uuid", guid)
    if uid in INTERNAL_INPUTS:
        return INTERNAL_INPUTS[uid][0]
    try:
        from gremlin.ui.device_names import shown_name

        return shown_name(uid)
    except Exception:  # noqa: BLE001 - a device nothing can name
        syslog.debug("references: no name for %s", uid, exc_info=True)
        return str(uid)


def in_step(number: int, ref: Reference) -> Reference:
    """A macro step's reference as its macro declares it."""
    where = (f"Step {number}", *ref.where)
    return replace(ref, text=f"In a macro: {ref.text}", where=where)


def in_condition(number: int, ref: Reference) -> Reference:
    """A condition's reference as its Condition action declares it."""
    where = (f"Condition {number}", *ref.where)
    return replace(ref, text=f"Condition: {ref.text}", where=where)
