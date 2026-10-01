# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid

import dill
from gremlin.input_module_gate import should_forward
from gremlin.input_module_runtime import always_forwarded
from gremlin.types import InputType


def _forward(guid: uuid.UUID, passthrough: set[str]) -> bool:
    # No input module claims anything: only always-forwarded devices pass.
    return should_forward(
        guid,
        InputType.JoystickButton,
        1,
        claims={},
        dest_guids=set(),
        passthrough=passthrough,
    )


def test_logical_device_events_reach_the_wire() -> None:
    # Map to Logical Device re-emits with the Logical Device GUID; that event
    # used to be dropped, so Logical Device -> vJoy wiring never ran.
    assert _forward(dill.UUID_LogicalDevice, always_forwarded())


def test_unclaimed_hardware_is_still_dropped() -> None:
    assert not _forward(uuid.uuid4(), always_forwarded())
