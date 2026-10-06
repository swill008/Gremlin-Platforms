# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from gremlin import (
    device_initialization,
    input_cache,
    macro,
)
from gremlin.types import InputType


class RefreshPhysicalInputs:
    """Emits input events using cached device information to trigger Gremlin
    action execution."""

    @classmethod
    def refresh_axes(cls) -> None:
        """Refreshes input axes using cached values. An axis not moved since
        the program started is read from the driver first (decision D-02-Q7),
        through the input side (EventListener.axis_value)."""
        from gremlin.event_handler import EventListener

        listener = EventListener()
        cache = input_cache.Joystick()
        devices = device_initialization.input_devices()
        macro_manager = macro.MacroManager()
        for dev in devices:
            joy = cache[dev.device_guid.uuid]
            for index in range(joy.axis_count):
                axis_id = dev.axis_map[index].axis_index
                action = macro.Macro()
                action.add_action(
                    macro.JoystickAction(
                        dev.device_guid.uuid,
                        InputType.JoystickAxis,
                        axis_id,
                        listener.axis_value(dev.device_guid.uuid, axis_id),
                    )
                )
                macro_manager.queue_macro(action)
