# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The on/off state of running actions, read by OSC Feedback (09 S157-S158).

A functor whose class defines ``feedback_state()`` is registered here by
AbstractFunctor under its action's id; Feedback reads it by that id. Actions
never import OSC. Weak references: a dropped functor leaves by itself; Run
start and Stop clear the rest.
"""

from __future__ import annotations

import threading
import uuid
import weakref
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gremlin.profile import Profile

_lock = threading.Lock()
_registry: dict[uuid.UUID, list[weakref.ref]] = {}


def register(functor: Any) -> None:  # noqa: ANN401
    """Adds a functor under its action's id."""
    action_id = getattr(getattr(functor, "data", None), "id", None)
    if action_id is None:
        return
    with _lock:
        refs = [r for r in _registry.get(action_id, []) if r() is not None]
        refs.append(weakref.ref(functor))
        _registry[action_id] = refs


def clear() -> None:
    """Forgets every functor (Run start and Stop)."""
    with _lock:
        _registry.clear()


def _live(action_id: uuid.UUID | str) -> list[Any]:
    if isinstance(action_id, str):
        try:
            action_id = uuid.UUID(action_id)
        except ValueError:
            return []
    with _lock:
        refs = list(_registry.get(action_id, []))
    return [f for f in (r() for r in refs) if f is not None]


def _state(functor: Any) -> bool:  # noqa: ANN401
    try:
        return bool(functor.feedback_state())
    except Exception:
        return False


def read(action_id: uuid.UUID | str) -> bool | None:
    """On if any functor of the action is on (S158); None when none runs."""
    functors = _live(action_id)
    if not functors:
        return None
    return any(_state(f) for f in functors)


def read_text(action_id: uuid.UUID | str) -> str | None:
    """The state as text: the first functor that is on, else the first one."""
    functors = _live(action_id)
    if not functors:
        return None
    chosen = next((f for f in functors if _state(f)), functors[0])
    text = getattr(chosen, "feedback_text", None)
    if text is not None:
        try:
            return str(text())
        except Exception:
            return ""
    return "on" if _state(chosen) else "off"


def paused_state() -> bool | None:
    """Running / Paused: True paused, False running, None when not running."""
    from gremlin import shared_state
    from gremlin.event_handler import EventHandler

    if not shared_state.runtime_active():
        return None
    return not EventHandler().process_callbacks


def _has_state(action: Any) -> bool:  # noqa: ANN401
    functor = getattr(action, "functor", None)
    return functor is not None and hasattr(functor, "feedback_state")


def _input_label(item: Any) -> str:  # noqa: ANN401
    if getattr(item, "action_name", ""):
        return item.action_name
    from gremlin import common
    from gremlin.input_monitor import device_name

    device = device_name(item.device_id) if item.device_id is not None else ""
    control = str(item.input_id)
    try:
        control = common.input_to_ui_string(item.input_type, item.input_id)
    except Exception:
        pass
    return f"{device} {control}".strip()


def stateful_actions(profile: Profile) -> list[tuple[uuid.UUID, str]]:
    """Every action with a state, "<input> · <mode> · <action>", for the
    Feedback editor's picker."""
    found: dict[tuple[uuid.UUID, str], None] = {}
    for items in profile.inputs.values():
        for item in items:
            for binding in item.action_sequences:
                stack = [binding.root_action] if binding.root_action else []
                while stack:
                    action = stack.pop()
                    stack.extend(action.get_actions()[0])
                    if _has_state(action):
                        label = (
                            f"{_input_label(item)} · {item.mode or 'Default'}"
                            f" · {action.name}"
                        )
                        found[(action.id, label)] = None
    return sorted(found, key=lambda entry: entry[1])
