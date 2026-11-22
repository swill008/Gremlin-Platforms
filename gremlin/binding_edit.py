# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Fixing a binding from Search (01 S195, D-01-SEARCH-FIX-BINDING): remove
it, or point a Map to vJoy at another vJoy output, on the open profile
directly, so it works for a device that isn't plugged in and has no card.
Each edit is noted as an unsaved change and announced as actionsChanged
(the Device Bindings page's notice), so Search, Home and the can't-be-sent
checks read the profile again; each returns an Undo that puts it back
exactly. Data only, no Qt widgets; never touches a device or a driver.

A row_ref is a Search result row (gremlin.search_index.SearchRow) or any
object or mapping with its fields: device_guid, mode, input_type,
input_id, binding_index, path, action_tag; optional target_keys (to tell
two actions of the same name apart), inherited_from (the mode the binding
is defined in), source ("library" rows can't be edited), action_name,
input_label, custom_name."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from gremlin import references as refs
from gremlin.edits import note_edit
from gremlin.modules import ids
from gremlin.types import DataInsertionMode, InputType

syslog = logging.getLogger("system")

_ROOT = "root"
_VJOY = "map-to-vjoy"
_KIND_TYPES = {
    "axis": InputType.JoystickAxis,
    "button": InputType.JoystickButton,
    "hat": InputType.JoystickHat,
}


class EditError(Exception):
    """The edit can't be made; the text says why, for the user."""


@dataclass
class Undo:
    """What one edit changed, to put it back (undo())."""

    kind: str  # "remove-action" | "remove-binding" | "target"
    text: str  # describe() of the edited binding
    profile: Any
    item: Any = None
    binding: Any = None
    parent: Any = None
    selector: str = ""
    index: int = 0
    action: Any = None
    # Library entries the removal released, and the library's order before.
    released: dict = field(default_factory=dict)
    copied: dict = field(default_factory=dict)
    order: list = field(default_factory=list)
    # Map to vJoy target before the change: (device id, InputType, input id).
    target: tuple = ()
    done: bool = False


# --- the row --------------------------------------------------------------------


def _get(row_ref: Any, name: str, default: Any = None) -> Any:  # noqa: ANN401
    if isinstance(row_ref, Mapping):
        return row_ref.get(name, default)
    return getattr(row_ref, name, default)


def _mode_of(row_ref: Any) -> str:  # noqa: ANN401
    """The mode the binding is defined in (an inherited row's parent mode)."""
    return str(_get(row_ref, "inherited_from", "") or _get(row_ref, "mode", "") or "")


def _profile_of(profile: Any) -> Any:  # noqa: ANN401
    if profile is not None:
        return profile
    from gremlin import shared_state

    found = shared_state.current_profile
    if found is None:
        raise EditError("No profile is open.")
    return found


def _check_editable(row_ref: Any) -> None:  # noqa: ANN401
    if _get(row_ref, "source", "") == "library":
        raise EditError("A Device Library setup can't be changed from Search.")
    from gremlin.ui.binding_catalog import editing_locked

    if editing_locked():
        raise EditError("The profile is running: stop it to change its bindings.")


def _label(action: Any) -> str:  # noqa: ANN401
    """The action's name as Search's row path holds it (usages._action_text)."""
    from gremlin.ui.binding_catalog import summarize_action

    return summarize_action(action)[0]


def _walk(
    action: Any,  # noqa: ANN401
    parent: Any,  # noqa: ANN401
    selector: str,
    above: tuple[str, ...],
    seen: set[int],
) -> Iterator[tuple[Any, Any, str, tuple[str, ...]]]:
    """(action, parent, its container, path) for the action and every action
    inside it, depth first, as gremlin.usages walks (the root's name is not
    in its children's paths)."""
    if action is None or id(action) in seen:
        return
    seen.add(id(action))
    here = (*above, _label(action))
    yield action, parent, selector, here
    below = above if getattr(action, "tag", "") == _ROOT else here
    try:
        children, selectors = action.get_actions()
    except Exception:  # noqa: BLE001 - an action with no containers
        return
    for child, sel in zip(children or [], selectors or [], strict=False):
        yield from _walk(child, action, sel, below, seen)


def _targets(action: Any) -> tuple:  # noqa: ANN401
    try:
        return tuple(ref.target for ref in action.references())
    except Exception:  # noqa: BLE001 - a broken piece: no targets to compare
        return ()


def _item_of(profile: Any, row_ref: Any) -> Any:  # noqa: ANN401
    guid = ids.guid_key(_get(row_ref, "device_guid", ""))
    mode = _mode_of(row_ref)
    want_type = refs.type_int(_get(row_ref, "input_type"))
    want_id = refs.id_key(_get(row_ref, "input_id"))
    for device, items in list(profile.inputs.items()):
        if ids.guid_key(device) != guid:
            continue
        for item in items:
            if (
                item.input_type is not None
                and refs.type_int(item.input_type) == want_type
                and refs.id_key(item.input_id) == want_id
                and str(item.mode or "") == mode
            ):
                return item
    raise EditError(f"{describe(row_ref, profile)} is no longer in the profile.")


def _locate(profile: Any, row_ref: Any) -> tuple[Any, Any, Any, Any, str]:  # noqa: ANN401
    """(item, binding, action, parent, container) of the row's action."""
    item = _item_of(profile, row_ref)
    index = int(_get(row_ref, "binding_index", 0) or 0)
    gone = EditError(f"{describe(row_ref, profile)} is no longer in the profile.")
    if not 0 <= index < len(item.action_sequences):
        raise gone
    binding = item.action_sequences[index]
    tag = str(_get(row_ref, "action_tag", "") or "")
    path = tuple(_get(row_ref, "path", ()) or ())
    keys = tuple(_get(row_ref, "target_keys", ()) or ())
    found = [
        (action, parent, selector)
        for action, parent, selector, here in _walk(
            binding.root_action, None, "", (), set()
        )
        if str(getattr(action, "tag", "") or "") == tag and (not path or here == path)
    ]
    if not found:
        raise gone
    exact = [f for f in found if keys and _targets(f[0]) == keys]
    action, parent, selector = (exact or found)[0]
    return item, binding, action, parent, selector


# --- names ----------------------------------------------------------------------


def device_name(guid: object, profile: Any = None) -> str:  # noqa: ANN401
    """A device's name, plugged in or not: the user's name for it, the
    connected device's name, its Device Library module's name, the name the
    profile stored, the driver's name, else its id. Never raises."""
    uid = getattr(guid, "uuid", guid)
    try:
        uid = uid if isinstance(uid, uuid.UUID) else uuid.UUID(str(uid))
    except (ValueError, TypeError, AttributeError):
        return str(guid or "")
    from gremlin.modules.device_class import INTERNAL_INPUTS

    if uid in INTERNAL_INPUTS:
        return INTERNAL_INPUTS[uid][0]
    for find in (
        lambda: _alias(uid),
        lambda: _connected_name(uid),
        lambda: _module_name(uid),
        lambda: _stored_name(uid, profile),
        lambda: _driver_name(uid),
    ):
        try:
            name = str(find() or "").strip()
        except Exception:  # noqa: BLE001 - one source failing hides no other
            syslog.debug("binding_edit: device name lookup failed", exc_info=True)
            continue
        if name:
            return name
    return str(uid)


def _alias(uid: uuid.UUID) -> str:
    from gremlin.device_aliases import display_name

    return display_name(str(uid), "")


def _connected_name(uid: uuid.UUID) -> str:
    from gremlin import device_initialization

    try:
        device_initialization.device_for_uuid(uid)
    except KeyError:
        return ""
    return device_initialization.shown_name(uid)


def _module_name(uid: uuid.UUID) -> str:
    import json

    from gremlin.modules import store

    folder = store.dir_of_id(ids.stored_guid_key(uid))
    if folder is None:
        return ""
    try:
        doc = json.loads((folder / store.ID_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        doc = None
    name = str(doc.get("name") or "") if isinstance(doc, dict) else ""
    # No name in the module's file: the module folder's own name (04 S32a).
    return name or getattr(folder, "name", "") or ""


def _stored_name(uid: uuid.UUID, profile: Any) -> str:  # noqa: ANN401
    if profile is None:
        from gremlin import shared_state

        profile = shared_state.current_profile
    database = getattr(profile, "device_database", None)
    info = getattr(database, "devices", {}).get(uid) if database else None
    return str(getattr(info, "name", "") or "")


def _driver_name(uid: uuid.UUID) -> str:
    from gremlin import device_initialization

    return device_initialization.device_name(uid)


def describe(row_ref: Any, profile: Any = None) -> str:  # noqa: ANN401
    """'the Map to vJoy binding from Z Axis of HID Remapper 2DGG (Default
    mode)', for the Remove question and the Undo text."""
    path = tuple(_get(row_ref, "path", ()) or ())
    action = str(
        _get(row_ref, "action_name", "")
        or (path[-1] if path else "")
        or _get(row_ref, "action_tag", "")
        or "action"
    )
    label = str(_get(row_ref, "input_label", "") or "")
    if not label:
        label = refs.input_label(
            _input_type(_get(row_ref, "input_type")), _get(row_ref, "input_id")
        )
    custom = str(_get(row_ref, "custom_name", "") or "")
    if custom and custom != label:
        label = f"{label} ({custom})"
    device = device_name(_get(row_ref, "device_guid", ""), profile)
    mode = _mode_of(row_ref) or "Default"
    return f"the {action} binding from {label} of {device} ({mode} mode)"


def _input_type(value: object) -> object:
    if isinstance(value, int) and not isinstance(value, bool):
        try:
            return InputType(value)
        except ValueError:
            return value
    return value


# --- edits ----------------------------------------------------------------------


def _changed() -> None:
    """The profile changed: an unsaved change, and the Device Bindings
    page's notice (actionsChanged, which also sends bindingsChanged through
    gremlin.ui.input_pairing for Search, Home and the can't-be-sent checks)."""
    note_edit()
    from gremlin.signal import signal

    signal.actionsChanged.emit()


def _release(library: Any, roots: list, record: Undo) -> None:  # noqa: ANN401
    """library.release (the one removal rule), noting what left and the
    order before, so undo puts each entry back in its place."""
    before = library.entries()
    record.order = list(before)
    copied = library.copy_marks()
    library.release(roots)
    after = library.entries()
    record.released = {k: v for k, v in before.items() if k not in after}
    record.copied = {k: v for k, v in copied.items() if k in record.released}


def _restore_library(library: Any, record: Undo) -> None:  # noqa: ANN401
    library.put_back(record.released, record.order)
    library.put_copy_marks(record.copied)


def _only_child(root: Any, action: Any) -> bool:  # noqa: ANN401
    try:
        children = list(root.get_actions()[0] or [])
    except Exception:  # noqa: BLE001
        return False
    return len(children) == 1 and children[0] is action


def remove_binding(row_ref: Any, profile: Any = None) -> Undo:  # noqa: ANN401
    """Removes the row's action from its input and mode; when it is the
    binding's only action (or the row is the binding itself), the whole
    binding goes, as the Device Bindings page's delete does."""
    profile = _profile_of(profile)
    _check_editable(row_ref)
    item, binding, action, parent, selector = _locate(profile, row_ref)
    record = Undo("remove-action", describe(row_ref, profile), profile, item, binding)
    root = binding.root_action
    if parent is None or (parent is root and _only_child(root, action)):
        record.kind = "remove-binding"
        record.index = item.action_sequences.index(binding)
        item.remove_item_binding(binding)
        _release(profile.library, [root], record)
    else:
        container = parent.get_actions(selector)[0]
        index = next(i for i, each in enumerate(container) if each is action)
        record.parent, record.selector, record.index = parent, selector, index
        record.action = action
        parent.remove_action(index, selector)
        _release(profile.library, [action], record)
    _changed()
    return record


def change_vjoy_target(
    row_ref: Any,  # noqa: ANN401
    vjoy_id: int,
    kind: str,
    control_id: int,
    profile: Any = None,  # noqa: ANN401
) -> Undo:
    """Points the row's Map to vJoy at vJoy vjoy_id's kind ("axis",
    "button", "hat") number control_id."""
    profile = _profile_of(profile)
    _check_editable(row_ref)
    input_type = _KIND_TYPES.get(str(kind or "").lower())
    if input_type is None:
        raise EditError(f"A vJoy output is an axis, a button or a hat, not {kind!r}.")
    item, binding, action, _parent, _selector = _locate(profile, row_ref)
    if getattr(action, "tag", "") != _VJOY:
        raise EditError("Change target… is only for a Map to vJoy action.")
    record = Undo("target", describe(row_ref, profile), profile, item, binding)
    record.action = action
    record.target = (
        action.vjoy_device_id,
        action.vjoy_input_type,
        action.vjoy_input_id,
    )
    action.vjoy_device_id = int(vjoy_id)
    action.vjoy_input_type = input_type
    action.vjoy_input_id = int(control_id)
    _changed()
    return record


def undo(record: Undo) -> None:
    """Puts the edit back exactly: the same action objects (same ids) in the
    same places, the library in its order. Each record undoes once."""
    if record.done:
        raise EditError("That change was already undone.")
    from gremlin.ui.binding_catalog import editing_locked

    if editing_locked():
        raise EditError("The profile is running: stop it to undo.")
    if record.kind == "target":
        action = record.action
        (
            action.vjoy_device_id,
            action.vjoy_input_type,
            action.vjoy_input_id,
        ) = record.target
    elif record.kind == "remove-binding":
        sequences = record.item.action_sequences
        sequences.insert(min(record.index, len(sequences)), record.binding)
        _restore_library(record.profile.library, record)
    elif record.kind == "remove-action":
        container = record.parent.get_actions(record.selector)[0]
        index = min(record.index, len(container))
        if index < len(container):
            record.parent.insert_action(
                record.action, record.selector, DataInsertionMode.Prepend, index
            )
        else:
            record.parent.insert_action(record.action, record.selector)
        _restore_library(record.profile.library, record)
    else:
        raise EditError(f"Unknown change {record.kind!r}.")
    record.done = True
    _changed()
