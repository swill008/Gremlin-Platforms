# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""History of profile saves: what each save changed, input by input.

Each save is compared with the last load or save of the profile. Every
input whose wires changed (added, changed or removed) gets an entry, as
does every other part of the profile that changed (Profile Settings, the
Logical Device, OSC inputs, modes, scripts). Inputs are compared by what
their actions are, not by the actions' ids (an editor's OK gives them new
ids). An entry keeps the input and its actions as they were and as they
became, so it can be put back. Each save also keeps the whole profile
before and after (compressed), so a whole profile can be put back; only
the newest saves of each profile keep it (gremlin.history.prune).

The comparison runs on the history's writer thread, not while saving.
"""

from __future__ import annotations

import base64
import re
import zlib
from pathlib import Path
from xml.etree import ElementTree

from gremlin import history

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
SECTIONS = {
    "settings": "Profile Settings",
    "logical-device": "the Logical Device",
    "osc-device": "the OSC inputs",
    "modes": "the modes",
    "scripts": "the scripts",
}
_WORDS = {"button": "Button", "axis": "Axis", "hat": "Hat", "key": "Key"}


def pack_text(text: str | None) -> str | None:
    if text is None:
        return None
    return base64.b64encode(zlib.compress(text.encode("utf-8"), 9)).decode("ascii")


def unpack_text(packed: str | None) -> str | None:
    if not packed:
        return None
    return zlib.decompress(base64.b64decode(packed)).decode("utf-8")


def _parse(text: str | None) -> ElementTree.Element | None:
    if not text:
        return None
    try:
        return ElementTree.fromstring(text.lstrip("﻿").encode("utf-8"))
    except ElementTree.ParseError:
        return None


def _actions(root: ElementTree.Element | None) -> dict[str, ElementTree.Element]:
    if root is None:
        return {}
    return {
        node.get("id", "").lower(): node
        for node in root.findall("./library/action")
        if node.get("id")
    }


def _names(root: ElementTree.Element | None) -> dict[str, str]:
    if root is None:
        return {}
    names = {}
    for node in root.findall("./devices/device"):
        key = (node.findtext("device-id") or "").strip().lower()
        if key:
            names[key] = " ".join((node.findtext("device-name") or "").split())
    return names


def _device_name(device_id: str, names: dict[str, str]) -> str:
    if names.get(device_id):
        return names[device_id]
    try:
        import dill
        from gremlin.modules import ids

        if device_id == str(ids.LOGICAL_DEVICE).lower():
            return "Logical Device"
        if device_id == str(ids.OSC).lower():
            return "OSC"
        if device_id == str(dill.UUID_Keyboard).lower():
            return "Keyboard"
    except Exception:
        pass
    return "A device"


def _resolved(
    node: ElementTree.Element, actions: dict[str, ElementTree.Element], depth: int = 0
) -> ElementTree.Element:
    """A copy with every action id replaced by the action it names (its own
    id left out): what the input does, whatever ids the actions have."""
    copy = ElementTree.Element(
        node.tag, {k: v for k, v in node.attrib.items() if k != "id"}
    )
    text = (node.text or "").strip()
    target = actions.get(text.lower()) if _UUID.match(text) else None
    if target is not None and depth < 50:
        copy.append(_resolved(target, actions, depth + 1))
    else:
        copy.text = text
    for child in node:
        copy.append(_resolved(child, actions, depth))
    return copy


def _used_actions(
    node: ElementTree.Element, actions: dict[str, ElementTree.Element]
) -> list[str]:
    """The XML of every action this input uses, children included."""
    found: dict[str, None] = {}
    pending = [node]
    while pending:
        current = pending.pop()
        for element in current.iter():
            text = (element.text or "").strip().lower()
            if text in actions and text not in found:
                found[text] = None
                pending.append(actions[text])
    return [ElementTree.tostring(actions[aid], encoding="unicode") for aid in found]


def _inputs(
    root: ElementTree.Element | None,
) -> dict[tuple[str, str, str, str], ElementTree.Element]:
    if root is None:
        return {}
    found = {}
    for node in root.findall("./inputs/input"):
        key = (
            (node.findtext("device-id") or "").strip().lower(),
            (node.findtext("input-type") or "").strip(),
            (node.findtext("input-id") or "").strip(),
            (node.findtext("mode") or "Default").strip(),
        )
        found[key] = node
    return found


def _input_doc(
    node: ElementTree.Element | None, actions: dict[str, ElementTree.Element]
) -> dict | None:
    if node is None:
        return None
    return {
        "input": ElementTree.tostring(node, encoding="unicode"),
        "actions": _used_actions(node, actions),
    }


def changes(before_text: str | None, after_text: str) -> list[dict]:
    """What a save changed: [{kind, title, subject, before, after}]."""
    before, after = _parse(before_text), _parse(after_text)
    if after is None:
        return []
    old_actions, new_actions = _actions(before), _actions(after)
    names = _names(before) | _names(after)
    old_inputs, new_inputs = _inputs(before), _inputs(after)
    out: list[dict] = []
    for key in sorted(set(old_inputs) | set(new_inputs)):
        old, new = old_inputs.get(key), new_inputs.get(key)
        old_shape = (
            ElementTree.tostring(_resolved(old, old_actions))
            if old is not None
            else None
        )
        new_shape = (
            ElementTree.tostring(_resolved(new, new_actions))
            if new is not None
            else None
        )
        if old_shape == new_shape:
            continue
        device_id, kind, number, mode = key
        device = _device_name(device_id, names)
        word = _WORDS.get(kind, kind.capitalize())
        verb = "Added" if old is None else ("Removed" if new is None else "Changed")
        out.append(
            {
                "kind": "input",
                "title": f"{verb} the actions of {device} {word} {number} in {mode}",
                "subject": {
                    "device": device,
                    "deviceId": device_id,
                    "inputType": kind,
                    "inputId": number,
                    "mode": mode,
                },
                "before": _input_doc(old, old_actions),
                "after": _input_doc(new, new_actions),
            }
        )
    for tag, label in SECTIONS.items():
        old = before.find(tag) if before is not None else None
        new = after.find(tag)
        old_text = (
            ElementTree.tostring(old, encoding="unicode") if old is not None else None
        )
        new_text = (
            ElementTree.tostring(new, encoding="unicode") if new is not None else None
        )
        if old_text == new_text:
            continue
        out.append(
            {
                "kind": "section",
                "title": f"Changed {label}",
                "subject": {"section": tag},
                "before": old_text,
                "after": new_text,
            }
        )
    return out


def record_save(path: Path, before_text: str | None, after_text: str) -> None:
    """Queues the comparison of a save; the writer thread does it."""
    history.later(lambda: _record(Path(path), before_text, after_text))


def _record(path: Path, before_text: str | None, after_text: str) -> None:
    found = changes(before_text, after_text)
    profile = {"profile": str(path), "profileName": path.name}
    for change in found:
        history.write_now(
            "profile",
            change["title"],
            profile | change["subject"],
            change["before"],
            change["after"],
            kind=change["kind"],
        )
    count = sum(1 for change in found if change["kind"] == "input")
    parts = []
    if count:
        parts.append(f"{count} {'input' if count == 1 else 'inputs'}")
    parts.extend(
        SECTIONS[c["subject"]["section"]] for c in found if c["kind"] == "section"
    )
    summary = f" ({', '.join(parts)})" if parts else ""
    history.write_now(
        "profile",
        f"Saved {path.name}{summary}",
        profile,
        {"packed": pack_text(before_text)},
        {"packed": pack_text(after_text)},
        kind="profile",
    )
