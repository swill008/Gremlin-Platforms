# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Runtime HID listener: input module claim is the only path into the wire."""

from __future__ import annotations

import logging

from PySide6 import QtCore

from gremlin import trace
from gremlin.common import SingletonDecorator
from gremlin.event_handler import Event, EventListener, trace_kind
from gremlin.modules import device_class, registry
from gremlin.modules.gate import should_forward
from gremlin.modules.ids import guid_key
from gremlin.signal import signal
from gremlin.types import InputType

syslog = logging.getLogger("system")


def _trace_dropped(event: Event) -> None:
    """Trace tab (D-01-TRACE): a ticked input its input module doesn't claim."""
    kind = trace_kind(event.event_type)
    index = event.identifier
    if kind is None or not isinstance(index, int):
        return
    if trace.ticked(event.device_guid, kind, index):
        trace.wiring(event.device_guid, kind, index, "not claimed, dropped")


def always_forwarded() -> set[str]:
    """Devices whose inputs exist without an input-module claim: OSC, and the
    Logical Device, whose inputs are created on the Logical Device page. Without
    this, events re-emitted by Map to Logical Device were dropped here and
    nothing wired from a Logical Device input ever ran."""
    # 03 S90b: the built-in devices that need no claim.
    return {
        guid_key(guid)
        for guid in (*device_class.INTERNAL_INPUTS, *device_class.INTERNAL_OUTPUTS)
        if device_class.can("no_claim_needed", guid=guid)
    }


def _vjoy_as_input_ids() -> set[int]:
    try:
        from gremlin import shared_state

        profile = shared_state.current_profile
        if profile is None:
            return set()
        raw = getattr(getattr(profile, "settings", None), "vjoy_as_input", {}) or {}
        return {int(vid) for vid, flag in raw.items() if flag}
    except Exception:
        return set()


def _read_back_vjoy_ids(as_input: set[int]) -> set[str]:
    """Device ids of the connected vJoys read back as an input. They pass
    whatever their output module file says (missing, or without its id)."""
    if not as_input:
        return set()
    from gremlin import device_initialization

    try:
        devices = list(device_initialization.vjoy_devices() or [])
    except Exception:
        return set()
    found = {
        guid_key(getattr(dev, "device_guid", ""))
        for dev in devices
        if getattr(dev, "vjoy_id", -1) in as_input
    }
    return {key for key in found if key}


def _connected_stick_ids() -> set[str]:
    from gremlin import device_initialization

    try:
        devices = list(device_initialization.physical_devices() or [])
    except Exception:
        return set()
    ids = {guid_key(getattr(dev, "device_guid", "")) for dev in devices}
    return {key for key in ids if key}


@SingletonDecorator
class InputModuleRuntime(QtCore.QObject):
    """Hardware events in; claimed input-module events out.

    event carries joystick events, key_event keyboard events. Only what the
    device's input module claims gets through (OSC, the Logical Device and a
    vJoy read back as input pass unfiltered).
    """

    event = QtCore.Signal(Event)
    key_event = QtCore.Signal(Event)

    def __init__(self) -> None:
        super().__init__()
        self._claims: dict[str, dict] = {}
        self._dest_guids: set[str] = set()
        self._passthrough: set[str] = always_forwarded()
        EventListener().joystick_event.connect(self._on_hid)
        EventListener().keyboard_event.connect(self._on_key)
        try:
            signal.configChanged.connect(self.reload)
            signal.profileChanged.connect(self.reload)
            # A stick plugged in while a profile runs (with device changes
            # set to Ignore nothing else reloads) gets its module's claims.
            EventListener().device_change_event.connect(self.reload)
        except Exception:
            pass
        self.reload()

    def reload(self) -> None:
        claims: dict[str, dict] = {}
        dest: set[str] = set()
        passthrough = always_forwarded()
        as_input = _vjoy_as_input_ids()
        connected = _connected_stick_ids()
        passthrough |= _read_back_vjoy_ids(as_input)
        for module in registry.modules():
            guid = guid_key(module.bound_guid)
            # A connected stick's module is the one registry.for_device finds
            # (below), and only that one: an old second file bound to it
            # (one marked output) used to block it at Run.
            if not guid or guid in connected:
                continue
            if not module.is_output:
                claims[guid] = module.claim
            elif registry.vjoy_id_from_name(module.name) in as_input:
                # a vJoy read back as an input: its events pass unfiltered
                passthrough.add(guid)
            else:
                dest.add(guid)
        self._bind_live_physical(claims, dest, passthrough)
        self._claims = claims
        self._dest_guids = dest
        self._passthrough = passthrough

    def _bind_live_physical(
        self, claims: dict[str, dict], dest: set[str], passthrough: set[str]
    ) -> None:
        from gremlin import device_initialization

        try:
            devices = list(device_initialization.physical_devices() or [])
        except Exception:
            return
        for dev in devices:
            guid = guid_key(getattr(dev, "device_guid", ""))
            # A connected stick uses the module Module Setup finds for it
            # (registry.resolve_module_slug), even when another file also
            # names it. None found: no claim, so nothing of it gets through.
            if not guid or guid in passthrough:
                continue
            name = str(getattr(dev, "name", "") or "")
            if not name:
                continue
            try:
                module = registry.for_device(name, str(getattr(dev, "device_guid", "")))
            except Exception:
                continue
            if module is None:
                continue
            if module.is_output:
                dest.add(guid)
                continue
            claims[guid] = module.claim

    def allows(self, guid: object, event_type: object, identifier: object) -> bool:
        """True when this input's input module passes it (same rule as events)."""
        return should_forward(
            guid,
            event_type,
            identifier,
            claims=self._claims,
            dest_guids=self._dest_guids,
            passthrough=self._passthrough,
        )

    def _on_key(self, event: Event) -> None:
        if event is None or getattr(event, "event_type", None) != InputType.Keyboard:
            return
        if should_forward(
            event.device_guid,
            event.event_type,
            getattr(event, "identifier", None),
            claims=self._claims,
            dest_guids=self._dest_guids,
            passthrough=self._passthrough,
        ):
            self.key_event.emit(event)

    def _on_hid(self, event: Event) -> None:
        if event is None:
            return
        if getattr(event, "event_type", None) not in (
            InputType.JoystickAxis,
            InputType.JoystickButton,
            InputType.JoystickHat,
        ):
            return
        if should_forward(
            event.device_guid,
            event.event_type,
            getattr(event, "identifier", None),
            claims=self._claims,
            dest_guids=self._dest_guids,
            passthrough=self._passthrough,
        ):
            self.event.emit(event)
        elif trace.enabled():
            _trace_dropped(event)
