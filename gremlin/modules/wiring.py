# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""How a wire's destination is described, in one place.

Long form, for rows and lists:  "vJoy 3 · Button 5 (Fire)",
                                "Xbox 360 Controller · Left Trigger".
Short form, for chips:          "vJoy 3 B5", "Xbox 1 LT".
A vJoy destination that can't be sent (output.cant_send_text: not in the
action editor's drop-down, or that vJoy turned off) reads, in the long form,
"⚠ vJoy 3 Button 57" (D-05-CANT-SEND); the page draws it red with the
reason as its tooltip. The short form (Device Mapping Editor, trace, Device Pack)
keeps "(not claimed)" / "(no output module)" (D-05-CANT-SEND-ALL: Device Mapping Editor
unchanged). Xbox has no claim: every Xbox control is always sent.
"""

from __future__ import annotations

from typing import Any

from gremlin import common
from gremlin.axis_names import AXIS_SHORT
from gremlin.modules import output
from gremlin.modules.claim import claim_friendly, kind_of
from gremlin.types import InputType

CANT_SEND = "⚠"
NOT_CLAIMED = "(not claimed)"
NO_MODULE = "(no output module)"


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
    if short:
        text = f"vJoy {vjoy_id} {_input_short(input_type, input_id)}"
        if not name:
            return f"{text} {NO_MODULE}"
        if not output.vjoy_allows(vjoy_id, kind, input_id):
            return f"{text} {NOT_CLAIMED}"
        return text
    claim = output.vjoy_claim(vjoy_id)
    if output.cant_send_text(vjoy_id, kind, input_id) is not None:
        control = output.control_label(claim, kind, input_id)
        return f"{CANT_SEND} vJoy {vjoy_id} {control}"
    text = f"{name or f'vJoy {vjoy_id}'} · {_input_long(input_type, input_id)}"
    named = claim_friendly(claim, kind, input_id)
    return f"{text} ({named})" if named else text


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
    # No claim mark: the Xbox output module passes every control.
    if short:
        return f"Xbox {int(pad_id)} {XBOX_SHORT.get(value, value[:3] or 'xb')}"
    return f"{output.xbox_pad_label(int(pad_id))} · {label}"


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
