# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Runtime HID listener: input module claim is the only path into the wire."""

from __future__ import annotations

import logging

from PySide6 import QtCore

import dill
from gremlin.common import SingletonDecorator
from gremlin.event_handler import Event, EventListener
from gremlin.input_module_gate import should_forward
from gremlin.modules import registry
from gremlin.modules.claim import read_claim
from gremlin.modules.ids import guid_key
from gremlin.osc import OSC_DEVICE_UUID
from gremlin.signal import signal
from gremlin.types import InputType

syslog = logging.getLogger("system")


def always_forwarded() -> set[str]:
    """Devices whose inputs exist without an input-module claim: OSC, and the
    Logical Device, whose inputs are created on the Logical Device page. Without
    this, events re-emitted by Map to Logical Device were dropped here and
    nothing wired from a Logical Device input ever ran."""
    return {guid_key(OSC_DEVICE_UUID), guid_key(dill.UUID_LogicalDevice)}


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


@SingletonDecorator
class InputModuleRuntime(QtCore.QObject):
    """DILL joystick events in; claimed source-module events out."""

    event = QtCore.Signal(Event)

    def __init__(self) -> None:
        super().__init__()
        self._claims: dict[str, dict] = {}
        self._dest_guids: set[str] = set()
        self._passthrough: set[str] = always_forwarded()
        EventListener().joystick_event.connect(self._on_hid)
        try:
            signal.configChanged.connect(self.reload)
            signal.profileChanged.connect(self.reload)
        except Exception:
            pass
        self.reload()

    def reload(self) -> None:
        claims: dict[str, dict] = {}
        dest: set[str] = set()
        passthrough = always_forwarded()
        as_input = _vjoy_as_input_ids()
        for module in registry.modules():
            guid = guid_key(module.bound_guid)
            if not guid:
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
        try:
            from gremlin import device_initialization
            from gremlin.ui.module_model import _load_module_doc
        except Exception:
            return
        try:
            devices = list(device_initialization.physical_devices() or [])
        except Exception:
            return
        for dev in devices:
            guid = guid_key(getattr(dev, "device_guid", ""))
            if not guid or guid in claims or guid in dest or guid in passthrough:
                continue
            name = str(getattr(dev, "name", "") or "")
            if not name:
                continue
            try:
                doc = _load_module_doc(name, str(getattr(dev, "device_guid", "")))
            except Exception:
                continue
            if not doc:
                continue
            direction = str(doc.get("direction") or "source").strip().lower()
            if direction in ("dest", "target", "output"):
                dest.add(guid)
                continue
            claims[guid] = read_claim(doc)

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
