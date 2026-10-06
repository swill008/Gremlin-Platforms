# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action labels for Button Map chips: what each control does in a mode.

A control's label is made from the actions the profile runs for it in that
mode, or, when the mode has none for it, in the nearest parent mode that has
(as the running profile inherits them). A Description action can stand for
the whole binding; otherwise each action gives a short text: the keys of Map
to Keyboard, the vJoy or Xbox output, the target of Change Mode, and so on.
Actions that only shape a value (response curves, deadzones) and the
containers around other actions (Chain, Tempo, Condition...) give no text of
their own; the actions inside them do.
"""

from __future__ import annotations

import uuid

from gremlin.modules import wiring
from gremlin.types import InputType
from gremlin.ui.input_pairing import walk_actions

# Label prefix per input type: "btn:5", "axis:1", "hat:1" as the chips use.
_KINDS = {
    InputType.JoystickButton: "btn",
    InputType.JoystickAxis: "axis",
    InputType.JoystickHat: "hat",
}

# Short fixed texts for actions whose settings say little at a glance.
_FIXED = {
    "map-to-mouse": "Mouse",
    "macro": "Macro",
    "load-profile": "Load profile",
    "run-command": "Run command",
    "play-sound": "Sound",
    "pause-resume": "Pause / resume",
    "map-to-logical-device": "Logical Device",
}


def _guid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value or "").strip().strip("{}"))
    except ValueError:
        return None


def mode_order(profile: object) -> list[str]:
    """The profile's modes, each parent followed by its children."""
    modes = getattr(profile, "modes", None)
    if modes is None:
        return []
    children: dict[str, list[str]] = {}
    for node in modes.mode_list():
        parent = getattr(getattr(node, "parent", None), "value", "") or ""
        children.setdefault(parent, []).append(node.value)
    out: list[str] = []

    def walk(name: str) -> None:
        for child in sorted(children.get(name, [])):
            out.append(child)
            walk(child)

    walk("")
    return out


def _parent_chain(profile: object, mode: str) -> list[str]:
    """The mode, then its parent, its parent's parent..."""
    chain = [mode]
    try:
        node = profile.modes.find_mode(mode)
    except Exception:  # noqa: BLE001 - an unknown mode has no parents
        return chain
    parent = getattr(node, "parent", None)
    while parent is not None and getattr(parent, "value", ""):
        chain.append(parent.value)
        parent = getattr(parent, "parent", None)
    return chain


def action_text(action: object) -> str:
    """Short text for one action; "" when it says nothing on its own."""
    tag = str(getattr(action, "tag", "") or "")
    if tag == "description":
        return str(getattr(action, "description", "") or "").strip()
    if tag == "map-to-keyboard":
        keys = [str(getattr(k, "name", "") or "") for k in getattr(action, "keys", [])]
        return "+".join(k for k in keys if k)
    if tag in ("map-to-vjoy", "map-to-xbox"):
        return wiring.dest_label(action, short=True)
    if tag == "change-mode":
        kind = getattr(getattr(action, "change_type", None), "name", "")
        targets = [str(t) for t in (getattr(action, "target_modes", None) or [])]
        if kind == "Cycle":
            return "Cycle " + "/".join(targets) if targets else "Cycle modes"
        if kind == "Previous":
            return "Previous mode"
        if kind == "Unwind":
            return "Unwind mode"
        return "→ " + "/".join(targets) if targets else "Change mode"
    if tag == "text-to-speech":
        said = str(getattr(action, "text", "") or "").strip()
        return f"Say “{said}”" if said else "Speak"
    return _FIXED.get(tag, "")


def _has_actions(item: object) -> bool:
    """Whether the item runs anything; one without actions leaves the
    parent mode's binding in place."""
    for seq in getattr(item, "action_sequences", []) or []:
        root = getattr(seq, "root_action", None)
        if root is None:
            continue
        if any(getattr(a, "tag", "") != "root" for a in walk_actions(root)):
            return True
    return False


def _texts_for_item(item: object, prefer_description: bool) -> list[str]:
    texts: list[str] = []
    descriptions: list[str] = []
    for seq in getattr(item, "action_sequences", []) or []:
        root = getattr(seq, "root_action", None)
        if root is None:
            continue
        for action in walk_actions(root):
            text = action_text(action)
            if not text:
                continue
            if getattr(action, "tag", "") == "description":
                descriptions.append(text)
            else:
                texts.append(text)
    if prefer_description and descriptions:
        return descriptions
    return texts + descriptions


def action_labels(
    profile: object,
    guid: str,
    mode: str,
    prefer_description: bool = True,
    join_all: bool = False,
) -> dict[str, str]:
    """{"btn:5": "Gear up", ...} for one device in one mode."""
    if profile is None:
        return {}
    uid = _guid(guid)
    if uid is None:
        return {}
    items = profile.inputs.get(uid, []) or []
    by_mode: dict[str, dict[str, object]] = {}
    for item in items:
        kind = _KINDS.get(getattr(item, "input_type", None))
        if kind is None:
            continue
        try:
            key = f"{kind}:{int(item.input_id)}"
        except (TypeError, ValueError):
            continue
        by_mode.setdefault(str(getattr(item, "mode", "")), {})[key] = item
    labels: dict[str, str] = {}
    # The nearest mode first: a child's own binding hides its parent's.
    for name in reversed(_parent_chain(profile, mode)):
        for key, item in by_mode.get(name, {}).items():
            if not _has_actions(item):
                continue
            texts = _texts_for_item(item, prefer_description)
            unique = list(dict.fromkeys(texts))
            if not unique:
                labels.pop(key, None)
                continue
            labels[key] = " + ".join(unique) if join_all else unique[0]
    return labels
