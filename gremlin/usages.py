# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Every use of an input, an output, a mode or an action type in a profile,
for Search (to-do 9) and the walkers built on it. Data only: one walk over
Profile.inputs -> bindings -> actions, asking each action what it uses
(references(), gremlin.references; a macro and a condition pass on their
steps' and conditions'), plus mode inheritance."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from typing import Any, NamedTuple

from gremlin import references as refs
from gremlin.modules import ids

syslog = logging.getLogger("system")

# Group order of the results.
ROLES = (
    "sends-output",
    "reads-input",
    "checks-output",
    "checks-input",
    "switches-mode",
    "loads-profile",
    "runs-in-mode",
    "inherited",
    "uses-action",
)

ROLE_TITLES = {
    "sends-output": "Sends to this output",
    "reads-input": "Reads this input",
    "checks-output": "Checks this output",
    "checks-input": "Checks this input",
    "switches-mode": "Switches to this mode",
    "loads-profile": "Loads this profile",
    "runs-in-mode": "Runs in this mode",
    "inherited": "Inherited by this mode",
    "uses-action": "Uses this action type",
}


@dataclass(frozen=True)
class Usage:
    """One use, by the binding it sits in (device, mode, input, binding)."""

    device_guid: str
    device_name: str
    mode: str
    input_type: int
    input_id: object
    input_label: str
    binding_index: int
    role: str
    text: str
    # Action names from the binding's root down to the use.
    path: tuple[str, ...]
    not_found: bool
    # Why it can't be used (the cant_send_* text), when the piece said.
    why: str = ""
    # Tag of the action that declared the use ("" for the binding's own
    # reads-input, runs-in-mode and inherited).
    action_tag: str = ""
    # The action's own use, not one of its macro steps or conditions.
    own: bool = True


@dataclass(frozen=True)
class Query:
    """What to search for. kind: "input", "output", "mode", "action" or
    "profile". input_type / input_id None: any control of that device or
    output. OSC: output "osc", output_key the target id, input_id the address.
    Mouse: output "mouse", input_id "Left", "WheelUp", "Motion"...
    Profile: output_key the file path."""

    kind: str
    device_guid: str = ""
    input_type: int | None = None
    input_id: object = None
    output: str = ""  # "vjoy" | "xbox" | "osc" | "mouse"
    output_id: int = 0
    output_key: str = ""
    mode: str = ""
    action_tag: str = ""


class Ref(NamedTuple):
    """A use and what it uses: a target shape of gremlin.references
    ("vjoy", "xbox", "input", "mode", "action", "osc-out", "mouse",
    "profile")."""

    target: tuple
    usage: Usage


def _action_text(action: object) -> tuple[str, str]:
    """(name, "name: destination") as the Bindings list shows an action."""
    from gremlin.ui.binding_catalog import summarize_action

    label, dest = summarize_action(action)
    return label, f"{label}: {dest}" if dest and dest != label else label


def _binding_text(root: object) -> str:
    from gremlin.ui.binding_catalog import collect_leaves

    leaves = [
        f"{label}: {dest}" if dest and dest != label else label
        for tag, label, dest in collect_leaves(root)
        if tag != "root"
    ]
    return "; ".join(leaves) or "No actions"


# Classes whose references() failed, logged once each.
_FAILED: set[str] = set()


def _declared(action: Any) -> list[refs.Reference]:  # noqa: ANN401
    """What one action declares it uses (references(); its child actions
    are walked), an empty text filled with the action's Bindings text. An
    action whose references() fails is skipped (logged once per class), so
    the input's other uses are still found."""
    try:
        declared = list(action.references())
    except Exception:  # noqa: BLE001 - one broken piece hides nothing else
        name = type(action).__name__
        if name not in _FAILED:
            _FAILED.add(name)
            syslog.exception(f"usages: {name}.references() failed, skipped")
        return []
    text = ""
    found: list[refs.Reference] = []
    for ref in declared:
        if not ref.text and not text:
            text = _action_text(action)[1]
        found.append(ref if ref.text else replace(ref, text=text))
    return found


def _children(action: Any) -> list[Any]:  # noqa: ANN401
    try:
        return list(action.get_actions()[0] or [])
    except Exception:  # noqa: BLE001 - an action with no children list
        return []


def walk_actions(root: Any) -> list[Any]:  # noqa: ANN401
    """The action and every action inside it, depth first (a parent's
    children next to it), each object once; an object without get_actions
    has no children."""
    return [action for action, _path in _walk(root, None, set())]


def _walk(
    action: Any,  # noqa: ANN401
    path: tuple[str, ...] | None,
    seen: set[int],
) -> Iterator[tuple[Any, tuple[str, ...]]]:
    """Every action below and including this one, with the names of the
    actions above it (path None: no names); each object once (a shared
    action, a loop)."""
    if action is None or id(action) in seen:
        return
    seen.add(id(action))
    yield action, path or ()
    here = path
    if path is not None and getattr(action, "tag", "") != "root":
        here = (*path, _action_text(action)[0])
    for child in _children(action):
        yield from _walk(child, here, seen)


def _descendants(profile: Any) -> dict[str, list[Any]]:  # noqa: ANN401
    """Each mode's child modes (tree nodes)."""
    found: dict[str, list[Any]] = {}
    try:
        nodes = profile.modes.mode_list()
    except Exception:  # noqa: BLE001 - a profile without modes
        return found
    for node in nodes:
        found[str(node.value)] = list(node.children)
    return found


def _inheriting(
    mode: str, children: dict[str, list[Any]], has_own: Iterable[str]
) -> list[str]:
    """The modes that run this mode's binding of an input: child modes
    without their own binding for it, and theirs (event_handler's
    build_event_lookup)."""
    own = set(has_own)
    found: list[str] = []
    pending = [str(node.value) for node in children.get(mode, [])]
    while pending:
        name = pending.pop(0)
        if name in own or name in found:
            continue
        found.append(name)
        pending.extend(str(node.value) for node in children.get(name, []))
    return found


def iter_usages(profile: Any) -> Iterator[Ref]:  # noqa: ANN401
    """Every use in the profile, one walk."""
    if profile is None:
        return
    names: dict[str, str] = {}
    children = _descendants(profile)
    for guid, items in list(profile.inputs.items()):
        bound: dict[tuple, set[str]] = {}
        for item in items:
            if item.action_sequences:
                key = (refs.type_int(item.input_type), refs.id_key(item.input_id))
                bound.setdefault(key, set()).add(str(item.mode or ""))
        for item in items:
            yield from _item_usages(guid, item, names, children, bound)


def item_usages(profile: Any, item: Any) -> Iterator[Ref]:  # noqa: ANN401
    """The uses of one input's bindings. With its profile, the modes that
    inherit them too; with None, no inheritance."""
    if item is None or not getattr(item, "action_sequences", None):
        return  # nothing bound: no uses (also stand-in items with no mode)
    children = _descendants(profile) if profile is not None else {}
    bound: dict[tuple, set[str]] = {}
    device = getattr(item, "device_id", None)  # stand-in items may lack it
    others = profile.inputs.get(device, []) if profile is not None else []
    for other in others or []:
        if other.action_sequences:
            key = (refs.type_int(other.input_type), refs.id_key(other.input_id))
            bound.setdefault(key, set()).add(str(other.mode or ""))
    yield from _item_usages(device, item, {}, children, bound)


def _item_usages(
    guid: Any,  # noqa: ANN401
    item: Any,  # noqa: ANN401
    names: dict[str, str],
    children: dict[str, list[Any]],
    bound: dict[tuple, set[str]],
) -> Iterator[Ref]:
    device = getattr(item, "device_id", None)
    uid = getattr(device, "uuid", device) or guid
    guid_text = str(uid)
    if guid_text not in names:
        names[guid_text] = refs.device_name(uid)
    mode = str(item.mode or "")
    input_type = refs.type_int(item.input_type)
    input_id = item.input_id
    label = refs.input_label(item.input_type, input_id)
    own = refs.input_ref(uid, item.input_type, input_id)

    def usage(
        index: int,
        role: str,
        text: str,
        path: tuple[str, ...],
        gone: bool,
        why: str = "",
        tag: str = "",
        own: bool = True,
    ) -> Usage:
        return Usage(
            device_guid=guid_text,
            device_name=names[guid_text],
            mode=mode,
            input_type=input_type,
            input_id=input_id,
            input_label=label,
            binding_index=index,
            role=role,
            text=text,
            path=path,
            not_found=gone,
            why=why,
            action_tag=tag,
            own=own,
        )

    inheriting = _inheriting(
        mode, children, bound.get((input_type, refs.id_key(input_id)), set())
    )
    # Each action once per input, as two bindings may share one.
    seen: set[int] = set()
    for index, binding in enumerate(item.action_sequences):
        root = binding.root_action
        if root is None:
            continue
        found: list[Ref] = []
        for action, path in _walk(root, (), seen):
            tag = str(getattr(action, "tag", "") or "")
            name, text = _action_text(action)
            here = (*path, name)
            for ref in _declared(action):
                where = here + ref.where
                use = usage(
                    index,
                    ref.role,
                    ref.text,
                    where,
                    ref.missing,
                    ref.why,
                    tag,
                    not ref.where,
                )
                found.append(Ref(ref.target, use))
            if tag != "root":
                use = usage(index, "uses-action", text, here, False, "", tag)
                found.append(Ref(("action", tag), use))
        broken = any(ref.usage.not_found for ref in found)
        summary = _binding_text(root)
        yield from found
        yield Ref(own, usage(index, "reads-input", summary, (), broken))
        yield Ref(("mode", mode), usage(index, "runs-in-mode", summary, (), broken))
        for child in inheriting:
            text = f"Inherited from {mode}: {summary}"
            found_in = usage(index, "inherited", text, (child,), broken)
            yield Ref(("mode", child), found_in)


def _matches(query: Query, target: tuple) -> bool:
    kind = query.kind
    if kind == "mode":
        return target[0] == "mode" and target[1] == query.mode
    if kind == "action":
        return target[0] == "action" and target[1] == query.action_tag
    if kind == "profile":
        return target[0] == "profile" and target[1] == refs.path_key(
            query.output_key
        )
    if kind == "input":
        if target[0] != "input" or target[1] != ids.guid_key(query.device_guid):
            return False
    elif kind == "output" and query.output == "osc":
        if target[0] != "osc-out" or target[1] != str(query.output_key):
            return False
        return query.input_id is None or target[2] == str(query.input_id)
    elif kind == "output" and query.output == "mouse":
        return target[0] == "mouse" and (
            query.input_id is None or target[1] == refs.mouse(query.input_id)[1]
        )
    elif kind == "output":
        if target[0] != query.output or target[1] != int(query.output_id):
            return False
        if query.output == "xbox":
            return query.input_id is None or target[2] == str(query.input_id)
    else:
        return False
    if query.input_type is not None and target[2] != refs.type_int(query.input_type):
        return False
    return query.input_id is None or target[3] == refs.id_key(query.input_id)


def _id_order(value: object) -> tuple:
    if isinstance(value, tuple):
        return (1, *value)
    if isinstance(value, int):
        return (0, value)
    return (2, str(value))


def _order(usage: Usage) -> tuple:
    return (
        ROLES.index(usage.role),
        usage.device_name.casefold(),
        usage.mode.casefold(),
        usage.input_type,
        _id_order(usage.input_id),
        usage.binding_index,
        usage.path,
    )


def find(profile: Any, query: Query) -> list[Usage]:  # noqa: ANN401
    """The uses matching the query, by group, then device, then mode."""
    found = [ref.usage for ref in iter_usages(profile) if _matches(query, ref.target)]
    return sorted(found, key=_order)
