# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Live capture: while it is on, every input the running profile handles is
recorded with the actions it ran (Live Log Reader → Debug → Live).

The tap sits in EventHandler.process_event (the wiring layer), so it sees
exactly what the profile sees: claimed inputs, keys and virtual buttons. It
only reads; it never changes an event or a callback. Off, it costs one
check per event. An axis is recorded at most every AXIS_INTERVAL seconds;
its latest value in between is kept and recorded on the next read."""

from __future__ import annotations

import collections
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any

from gremlin.types import InputType

if TYPE_CHECKING:
    from gremlin.event_handler import Event

# Most entries kept; older ones drop off the top.
MAX_ENTRIES = 5000
AXIS_INTERVAL = 0.1

# Entry kinds: an input that ran actions, or one with nothing bound.
RAN = "ran"
NONE = "none"

_LOCK = threading.Lock()
_enabled = False
_entries: collections.deque[tuple[str, str]] = collections.deque(maxlen=MAX_ENTRIES)
_version = 0
# Axis key -> time last recorded, and the newest unrecorded entry.
_axis_last: dict[tuple[Any, ...], float] = {}
_axis_pending: dict[tuple[Any, ...], tuple[str, str]] = {}


def enabled() -> bool:
    return _enabled


def set_enabled(on: bool) -> None:
    global _enabled
    _enabled = bool(on)


def clear() -> None:
    global _version
    with _LOCK:
        _entries.clear()
        _axis_last.clear()
        _axis_pending.clear()
        _version += 1


def version() -> int:
    """Changes whenever an entry is added or the capture is cleared."""
    with _LOCK:
        return _version + len(_axis_pending)


def entries() -> list[tuple[str, str]]:
    """(kind, text) oldest first; pending axis values are recorded first."""
    global _version
    with _LOCK:
        if _axis_pending:
            for key, entry in _axis_pending.items():
                _entries.append(entry)
                _axis_last[key] = time.monotonic()
            _axis_pending.clear()
            _version += 1
        return list(_entries)


def record(event: Event, callbacks: list[object], paused: bool = False) -> None:
    """Record one processed event and the callbacks that handled it."""
    global _version
    try:
        entry = _entry(event, callbacks, paused)
    except Exception:  # a capture problem must never affect the profile
        return
    now = time.monotonic()
    with _LOCK:
        if event.event_type == InputType.JoystickAxis:
            key = (event.device_guid, event.identifier)
            if now - _axis_last.get(key, 0.0) < AXIS_INTERVAL:
                _axis_pending[key] = entry
                return
            _axis_pending.pop(key, None)
            _axis_last[key] = now
        _entries.append(entry)
        _version += 1


def _entry(event: Event, callbacks: list[object], paused: bool) -> tuple[str, str]:
    stamp = time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
    head = f"{stamp}  {device_name(event.device_guid)} · {input_name(event)}"
    head += f"  {value_text(event)}  [{event.mode}]"
    ran = [text for cb in callbacks if (text := callback_text(cb))]
    if ran:
        return RAN, head + "  →  " + "; ".join(ran)
    if callbacks:
        return RAN, head + "  →  script"
    return NONE, head + ("  →  paused" if paused else "  →  nothing bound")


def device_name(guid: uuid.UUID) -> str:
    import dill
    from gremlin import device_initialization
    from gremlin.osc import OSC_DEVICE_UUID

    if guid == dill.UUID_Keyboard:
        return "Keyboard"
    if guid == dill.UUID_Virtual:
        return "Virtual button"
    if guid == OSC_DEVICE_UUID:
        return "OSC"
    for dev in device_initialization.joystick_devices():
        if dev.device_guid.uuid == guid:
            return dev.name
    return "Unknown device"


def input_name(event: Event) -> str:
    from gremlin import common

    try:
        return common.input_to_ui_string(event.event_type, event.identifier)
    except Exception:
        return str(event.identifier)


def value_text(event: Event) -> str:
    kind = event.event_type
    if kind == InputType.JoystickAxis and isinstance(event.value, (int, float)):
        return f"{float(event.value):+.3f}"
    if kind in (InputType.JoystickButton, InputType.Keyboard):
        return "pressed" if event.is_pressed else "released"
    return str(event.value)


def callback_text(cb: object) -> str:
    """The actions a profile binding ran, with where Map to vJoy / Xbox
    send it; "" for a script callback."""
    # A plugin may wrap the callback in functools.partial.
    while getattr(cb, "func", None) is not None and not hasattr(cb, "_binding"):
        cb = getattr(cb, "func")
    binding = getattr(cb, "_binding", None)
    if binding is None:
        return ""
    from gremlin.modules.wiring import dest_label

    names = []
    for action in binding.root_action.get_actions()[0]:
        name = str(getattr(action, "name", "") or type(action).__name__)
        dest = dest_label(action, short=True)
        names.append(f"{name} ({dest})" if dest else name)
    return ", ".join(names) or "no actions"
