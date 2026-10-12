# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Every use of an input, an output, a mode or an action type in a profile,
for Search (to-do 9). Data only: one walk over Profile.inputs -> bindings ->
actions, reading action targets, macro steps, condition objects and Change
Mode targets, plus mode inheritance."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, NamedTuple

from gremlin.modules import ids
from gremlin.types import InputType

syslog = logging.getLogger("system")

# Group order of the results.
ROLES = (
    "sends-output",
    "reads-input",
    "checks-output",
    "checks-input",
    "switches-mode",
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


@dataclass(frozen=True)
class Query:
    """What to search for. kind: "input", "output", "mode" or "action".
    input_type / input_id None: any control of that device or output."""

    kind: str
    device_guid: str = ""
    input_type: int | None = None
    input_id: object = None
    output: str = ""  # "vjoy" | "xbox"
    output_id: int = 0
    mode: str = ""
    action_tag: str = ""


class Ref(NamedTuple):
    """A use and what it uses: ("vjoy", id, type, control), ("xbox", pad,
    control), ("input", guid key, type, id), ("mode", name), ("action", tag)."""

    target: tuple
    usage: Usage


def _type_int(value: object) -> int:
    if isinstance(value, InputType):
        return value.value
    return int(value)  # type: ignore[arg-type]


def _id_key(value: object) -> object:
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


def _input(guid: object, input_type: object, input_id: object) -> tuple:
    return ("input", ids.guid_key(guid), _type_int(input_type), _id_key(input_id))


def _device_name(guid: object) -> str:
    from gremlin.modules.device_class import INTERNAL_INPUTS

    uid = getattr(guid, "uuid", guid)
    if uid in INTERNAL_INPUTS:
        return INTERNAL_INPUTS[uid][0]
    try:
        from gremlin.ui.device_names import shown_name

        return shown_name(uid)
    except Exception:  # noqa: BLE001 - a device nothing can name
        syslog.debug("Search: no name for %s", uid, exc_info=True)
        return str(uid)


def _input_label(input_type: object, input_id: object) -> str:
    from gremlin import common

    try:
        return common.input_to_ui_string(input_type, input_id)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - an input type with no ui string
        return f"{input_type} {input_id}"


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


def _step_target(step: object) -> tuple[tuple | None, str, bool]:
    """(target, words, not found) of one macro step."""
    from gremlin import macro
    from gremlin.modules import output

    if isinstance(step, macro.VJoyAction):
        target = (
            "vjoy",
            int(step.vjoy_id),
            _type_int(step.input_type),
            int(step.input_id),
        )
        words = f"vJoy {step.vjoy_id} {_input_label(step.input_type, step.input_id)}"
        missing = output.cant_send_text(
            step.vjoy_id, output.kind_of(step.input_type), step.input_id
        )
        return target, words, bool(missing)
    if isinstance(step, macro.KeyAction) and step.key is not None:
        key = (int(step.key.scan_code), bool(step.key.is_extended))
        return _input(ids.KEYBOARD, InputType.Keyboard, key), step.key.name, False
    if isinstance(step, macro.JoystickAction):
        target = _input(step.device_guid, step.input_type, step.input_id)
        words = f"{_device_name(step.device_guid)} " + _input_label(
            step.input_type, step.input_id
        )
        return target, words, False
    if isinstance(step, macro.LogicalDeviceAction) and step.input_id is not None:
        ident = step.current_identifier()
        input_type = ident.type if ident is not None else step.input_type
        input_id = ident.id if ident is not None else step.input_id
        target = _input(ids.LOGICAL_DEVICE, input_type, input_id)
        words = f"Logical Device {_input_label(input_type, input_id)}"
        return target, words, ident is None
    if isinstance(step, macro.OscAction) and step.uid:
        from gremlin.osc_persist import osc_rows

        ident = osc_rows().identifier_of_uid(step.uid)
        if ident is None:
            return None, "", True
        target = _input(ids.OSC, ident[0], ident[1])
        return target, f"OSC {_input_label(ident[0], ident[1])}", False
    return None, "", False


def _condition_targets(cond: object) -> Iterator[tuple[str, tuple, str, bool]]:
    """(role, target, words, not found) for each state of one condition."""
    from action_plugins.condition import condition as ca

    for state in getattr(cond, "_states", None) or []:
        if isinstance(cond, ca.VJoyCondition):
            target = (
                "vjoy",
                int(state.vjoy_id),
                _type_int(state.input_type),
                int(state.input_id),
            )
            words = f"vJoy {state.vjoy_id} " + _input_label(
                state.input_type, state.input_id
            )
            yield "checks-output", target, words, False
        elif isinstance(cond, ca.KeyboardCondition):
            key = (int(state.key.scan_code), bool(state.key.is_extended))
            target = _input(ids.KEYBOARD, InputType.Keyboard, key)
            yield "checks-input", target, state.key.name, False
        elif isinstance(cond, ca.JoystickCondition):
            target = _input(state.device_uuid, state.input_type, state.input_id)
            words = f"{_device_name(state.device_uuid)} " + _input_label(
                state.input_type, state.input_id
            )
            yield "checks-input", target, words, False
        elif isinstance(cond, ca.LogicalDeviceCondition):
            target = _input(ids.LOGICAL_DEVICE, state.input_type, state.input_id)
            words = "Logical Device " + _input_label(state.input_type, state.input_id)
            yield "checks-input", target, words, bool(state.missing)


def _action_targets(
    action: Any, memo: dict  # noqa: ANN401
) -> Iterator[tuple[str, tuple, str, tuple[str, ...], bool]]:
    """(role, target, text, path below the action, not found) of the
    outputs, inputs and modes one action names itself."""
    from action_plugins.change_mode import ChangeModeData
    from action_plugins.condition import ConditionData
    from action_plugins.macro import MacroData
    from action_plugins.map_to_keyboard import MapToKeyboardData
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData
    from action_plugins.map_to_vjoy import MapToVjoyData
    from action_plugins.map_to_xbox import MapToXboxData
    from gremlin.modules import output

    _name, text = _action_text(action)
    missing = bool(output.cant_send_action_texts(action, memo))
    if isinstance(action, MapToVjoyData):
        target = (
            "vjoy",
            int(action.vjoy_device_id),
            _type_int(action.vjoy_input_type),
            int(action.vjoy_input_id),
        )
        yield "sends-output", target, text, (), missing
    elif isinstance(action, MapToXboxData):
        control = getattr(action.xbox_target, "value", action.xbox_target)
        target = ("xbox", int(action.xbox_device_id), str(control))
        yield "sends-output", target, text, (), missing
    elif isinstance(action, MapToKeyboardData):
        for key in action.keys or []:
            target = _input(ids.KEYBOARD, InputType.Keyboard, key)
            yield "sends-output", target, text, (), False
    elif isinstance(action, MapToLogicalDeviceData):
        target = _input(
            ids.LOGICAL_DEVICE, action.logical_input_type, action.logical_input_id
        )
        yield "sends-output", target, text, (), missing
    elif isinstance(action, MacroData):
        for number, step in enumerate(action.actions, start=1):
            target, words, step_missing = _step_target(step)
            if target is not None:
                text = f"In a macro: {words}"
                where = (f"Step {number}",)
                yield "sends-output", target, text, where, step_missing
    elif isinstance(action, ConditionData):
        for number, cond in enumerate(action.conditions, start=1):
            for role, target, words, gone in _condition_targets(cond):
                where = (f"Condition {number}",)
                yield role, target, f"Condition: {words}", where, gone
    elif isinstance(action, ChangeModeData):
        kind = action.change_type.name
        for mode in action.target_modes:
            text = f"Change Mode ({kind}): {mode}"
            yield "switches-mode", ("mode", str(mode)), text, (), False


def _walk(
    action: Any, path: tuple[str, ...], seen: set[int]  # noqa: ANN401
) -> Iterator[tuple[Any, tuple[str, ...]]]:
    """Every action below and including this one, with the names of the
    actions above it; each object once (a shared action, a loop)."""
    if action is None or id(action) in seen:
        return
    seen.add(id(action))
    yield action, path
    here = path
    if getattr(action, "tag", "") != "root":
        here = (*path, _action_text(action)[0])
    try:
        children = action.get_actions()[0]
    except Exception:  # noqa: BLE001 - an action with no children list
        children = []
    for child in children:
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
    memo: dict = {}
    names: dict[str, str] = {}
    children = _descendants(profile)
    for guid, items in list(profile.inputs.items()):
        bound: dict[tuple, set[str]] = {}
        for item in items:
            if item.action_sequences:
                key = (_type_int(item.input_type), _id_key(item.input_id))
                bound.setdefault(key, set()).add(str(item.mode or ""))
        for item in items:
            yield from _item_usages(guid, item, memo, names, children, bound)


def _item_usages(
    guid: Any,  # noqa: ANN401
    item: Any,  # noqa: ANN401
    memo: dict,
    names: dict[str, str],
    children: dict[str, list[Any]],
    bound: dict[tuple, set[str]],
) -> Iterator[Ref]:
    uid = getattr(item.device_id, "uuid", item.device_id) or guid
    guid_text = str(uid)
    if guid_text not in names:
        names[guid_text] = _device_name(uid)
    mode = str(item.mode or "")
    input_type = _type_int(item.input_type)
    input_id = item.input_id
    label = _input_label(item.input_type, input_id)
    own = _input(uid, item.input_type, input_id)

    def usage(
        index: int, role: str, text: str, path: tuple[str, ...], gone: bool
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
        )

    inheriting = _inheriting(
        mode, children, bound.get((input_type, _id_key(input_id)), set())
    )
    for index, binding in enumerate(item.action_sequences):
        root = binding.root_action
        if root is None:
            continue
        found: list[Ref] = []
        for action, path in _walk(root, (), set()):
            tag = str(getattr(action, "tag", "") or "")
            name, text = _action_text(action)
            here = (*path, name)
            for role, target, words, below, gone in _action_targets(action, memo):
                found.append(Ref(target, usage(index, role, words, here + below, gone)))
            if tag != "root":
                found.append(
                    Ref(("action", tag), usage(index, "uses-action", text, here, False))
                )
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
    if kind == "input":
        if target[0] != "input" or target[1] != ids.guid_key(query.device_guid):
            return False
    elif kind == "output":
        if target[0] != query.output or target[1] != int(query.output_id):
            return False
        if query.output == "xbox":
            return query.input_id is None or target[2] == str(query.input_id)
    else:
        return False
    if query.input_type is not None and target[2] != _type_int(query.input_type):
        return False
    return query.input_id is None or target[3] == _id_key(query.input_id)


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
