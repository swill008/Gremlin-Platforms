# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""How a wire's destination is described, in one place.

Long form, for rows and lists:  "vJoy 3 · Button 5 (Fire)",
                                "Xbox 360 Controller · Left Trigger".
Short form, for chips:          "vJoy 3 B5", "Xbox 1 LT".
A destination its output module does not claim (so nothing is sent since
Phase 2) ends in "(not claimed)"; one with no output module says so.
"""

from __future__ import annotations

from typing import Any

from gremlin import common
from gremlin.modules import output
from gremlin.modules.claim import claim_friendly, kind_of
from gremlin.types import InputType

NOT_CLAIMED = "(not claimed)"
NO_MODULE = "(no output module)"

AXIS_SHORT = {1: "X", 2: "Y", 3: "Z", 4: "Rx", 5: "Ry", 6: "Rz", 7: "S1", 8: "S2"}

XBOX_SHORT = {
    "left_stick_x": "LSX",
    "left_stick_y": "LSY",
    "right_stick_x": "RSX",
    "right_stick_y": "RSY",
    "left_trigger": "LT",
    "right_trigger": "RT",
    "a": "A",
    "b": "B",
    "x": "X",
    "y": "Y",
    "left_shoulder": "LB",
    "right_shoulder": "RB",
    "left_thumb": "LS",
    "right_thumb": "RS",
    "start": "Str",
    "back": "Bak",
    "guide": "G",
    "dpad_up": "U",
    "dpad_down": "D",
    "dpad_left": "L",
    "dpad_right": "R",
    "dpad": "Hat",
}


def _input_short(input_type: object, input_id: int) -> str:
    kind = kind_of(input_type)
    if kind == "axis":
        return AXIS_SHORT.get(int(input_id), f"A{int(input_id)}")
    if kind == "hat":
        return f"H{int(input_id)}"
    return f"B{int(input_id)}"


def _input_long(input_type: object, input_id: int) -> str:
    try:
        return common.input_to_ui_string(input_type, int(input_id))
    except Exception:
        return str(input_id)


def vjoy_dest(
    vjoy_id: int, input_type: object, input_id: int, short: bool = False
) -> str:
    """Destination text for a vJoy output."""
    vjoy_id, input_id = int(vjoy_id), int(input_id)
    if input_type == InputType.Keyboard:  # Map to vJoy treats keys as buttons
        input_type = InputType.JoystickButton
    kind = kind_of(input_type)
    name = output.vjoy_module_name(vjoy_id)
    flag = ""
    if not name:
        name, flag = f"vJoy {vjoy_id}", NO_MODULE
    elif not output.vjoy_allows(vjoy_id, kind, input_id):
        flag = NOT_CLAIMED
    if short:
        text = f"vJoy {vjoy_id} {_input_short(input_type, input_id)}"
    else:
        text = f"{name} · {_input_long(input_type, input_id)}"
        named = claim_friendly(output.vjoy_claim(vjoy_id), kind, input_id)
        if named:
            text += f" ({named})"
    return f"{text} {flag}" if flag else text


def xbox_dest(pad_id: int, target: Any, short: bool = False) -> str:  # noqa: ANN401
    """Destination text for an Xbox control."""
    value = str(getattr(target, "value", target) or "").lower()
    label = str(getattr(target, "label", "") or "")
    if not label:
        try:
            from vigem.xbox import XboxTarget

            label = XboxTarget.from_string(value).label
        except Exception:
            label = value.replace("_", " ") or "Xbox"
    module = output.xbox_module(int(pad_id))
    flag = ""
    if module is None:
        flag = NO_MODULE
    elif not output.xbox_allows(int(pad_id), value):
        flag = NOT_CLAIMED
    if short:
        text = f"Xbox {int(pad_id)} {XBOX_SHORT.get(value, value[:3] or 'xb')}"
    else:
        name = module.name if module is not None else f"Xbox pad {int(pad_id)}"
        text = f"{name} · {label}"
    return f"{text} {flag}" if flag else text


def dest_label(action: object, short: bool = False) -> str:
    """Destination of a Map to vJoy / Map to Xbox action; "" for other actions."""
    tag = str(getattr(action, "tag", "") or "")
    try:
        if tag == "map-to-vjoy":
            return vjoy_dest(
                getattr(action, "vjoy_device_id", 0),
                getattr(action, "vjoy_input_type", InputType.JoystickButton),
                getattr(action, "vjoy_input_id", 1),
                short,
            )
        if tag == "map-to-xbox":
            return xbox_dest(
                getattr(action, "xbox_device_id", 1),
                getattr(action, "xbox_target", ""),
                short,
            )
    except (TypeError, ValueError):
        return ""
    return ""
