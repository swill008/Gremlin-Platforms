# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Runtime HID listener: input module claim is the only path into the wire."""

from __future__ import annotations

import logging

from PySide6 import QtCore

from gremlin import trace, trace_timing
from gremlin.common import SingletonDecorator
from gremlin.event_handler import EventListener, trace_kind
from gremlin.modules import device_class, registry
from gremlin.modules.gate import should_forward
from gremlin.modules.ids import guid_key
from gremlin.signal import signal
from gremlin.types import Event, InputType


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

        profile = shared_state.profile_for_runtime()
        if profile is None:
            return set()
        raw = getattr(getattr(profile, "settings", None), "vjoy_as_input", {}) or {}
        # A copy first: the window may change the open profile's dict meanwhile.
        return {int(vid) for vid, flag in list(dict(raw).items()) if flag}
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

    Lives on the input thread (code_runner.adopt_runtime_objects): events
    from the driver and hook threads are queued to it; one emitted on the
    input thread itself (Map to Logical Device) is handled at once. Its
    slots are QObject slots so Qt, not PySide, picks their thread.
    """

    event = QtCore.Signal(Event)
    key_event = QtCore.Signal(Event)

    def __init__(self) -> None:
        super().__init__()
        # (claims, dest_guids, passthrough), published as one tuple so the
        # gate never reads a mix of an old and a new reload.
        self._gate: tuple[dict[str, dict], set[str], set[str]] = (
            {}, set(), always_forwarded()
        )
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

    @property
    def _claims(self) -> dict[str, dict]:
        return self._gate[0]

    @_claims.setter
    def _claims(self, value: dict[str, dict]) -> None:
        self._gate = (value, self._gate[1], self._gate[2])

    @property
    def _dest_guids(self) -> set[str]:
        return self._gate[1]

    @_dest_guids.setter
    def _dest_guids(self, value: set[str]) -> None:
        self._gate = (self._gate[0], value, self._gate[2])

    @property
    def _passthrough(self) -> set[str]:
        return self._gate[2]

    @_passthrough.setter
    def _passthrough(self, value: set[str]) -> None:
        self._gate = (self._gate[0], self._gate[1], value)

    @QtCore.Slot()
    def reload(self) -> None:
        """Reads the claims again (on the input thread while it runs). A
        failed read keeps the claims it had, logged, rather than none."""
        try:
            gate = self._read_gate()
        except Exception:
            logging.getLogger("system").exception(
                "Input modules: claims not re-read; the previous ones are kept"
            )
            return
        self._gate = gate

    def _read_gate(self) -> tuple[dict[str, dict], set[str], set[str]]:
        claims: dict[str, dict] = {}
        dest: set[str] = set()
        passthrough = always_forwarded()
        as_input = _vjoy_as_input_ids()
        connected = _connected_stick_ids()
        passthrough |= _read_back_vjoy_ids(as_input)
        # A copy: the window may add or remove modules meanwhile.
        for module in list(registry.modules()):
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
        return claims, dest, passthrough

    def _bind_live_physical(
        self, claims: dict[str, dict], dest: set[str], passthrough: set[str]
    ) -> None:
        from gremlin import device_initialization

        # The window changes the device dict at a device change; one retry
        # covers "changed size during iteration". A second failure raises so
        # reload keeps the previous claims rather than binding fewer.
        try:
            devices = list(device_initialization.physical_devices() or [])
        except RuntimeError:
            devices = list(device_initialization.physical_devices() or [])
        for dev in devices:
            guid = guid_key(getattr(dev, "device_guid", ""))
            # A connected stick uses the module Module Setup finds for it
            # (registry.for_device: the folder holding its id, else the one
            # named after it; 03 S1), even when another file also names it.
            # None found: no claim, so nothing of it gets through.
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
        claims, dest, passthrough = self._gate
        return should_forward(
            guid,
            event_type,
            identifier,
            claims=claims,
            dest_guids=dest,
            passthrough=passthrough,
        )

    @QtCore.Slot(Event)
    def _on_key(self, event: Event) -> None:
        if event is None or getattr(event, "event_type", None) != InputType.Keyboard:
            return
        claims, dest, passthrough = self._gate
        if should_forward(
            event.device_guid,
            event.event_type,
            getattr(event, "identifier", None),
            claims=claims,
            dest_guids=dest,
            passthrough=passthrough,
        ):
            self.key_event.emit(event)

    @QtCore.Slot(Event)
    def _on_hid(self, event: Event) -> None:
        if event is None:
            return
        if trace_timing.on:
            trace_timing.dispatch(event)
        if getattr(event, "event_type", None) not in (
            InputType.JoystickAxis,
            InputType.JoystickButton,
            InputType.JoystickHat,
        ):
            return
        claims, dest, passthrough = self._gate
        if should_forward(
            event.device_guid,
            event.event_type,
            getattr(event, "identifier", None),
            claims=claims,
            dest_guids=dest,
            passthrough=passthrough,
        ):
            self.event.emit(event)
        elif trace.enabled():
            _trace_dropped(event)
