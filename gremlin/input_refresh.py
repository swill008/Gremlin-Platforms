# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging

from gremlin import (
    device_initialization,
    log_once,
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
        through the input side (EventListener.axis_value). The axes are the
        ones the reader reports now. An axis that can't be read is skipped
        and logged once: one control never stops the start (06 S91)."""
        from gremlin.event_handler import EventListener

        listener = EventListener()
        devices = device_initialization.input_devices()
        macro_manager = macro.MacroManager()
        for dev in devices:
            guid = dev.device_guid.uuid
            for index in range(dev.axis_count):
                axis_id = dev.axis_map[index].axis_index
                try:
                    value = listener.axis_value(guid, axis_id)
                except Exception as e:  # noqa: BLE001 - any read problem
                    name = device_initialization.device_name(guid) or dev.name
                    log_once.log_once(
                        "system",
                        ("refresh-axis", guid, axis_id),
                        logging.WARNING,
                        f"Start: {name} Axis {axis_id} could not be read, "
                        f"skipped: {e}",
                    )
                    continue
                action = macro.Macro()
                action.add_action(
                    macro.JoystickAction(
                        guid, InputType.JoystickAxis, axis_id, value
                    )
                )
                macro_manager.queue_macro(action)
