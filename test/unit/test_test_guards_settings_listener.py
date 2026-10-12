# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Guards in the test set-up (items 30, 31, 47): they fire when they should."""

from __future__ import annotations

import os

import gremlin.config
import gremlin.device_initialization
import gremlin.event_handler
from gremlin.modules.runtime import InputModuleRuntime
from test.unit import conftest


def test_program_settings_are_registered_before_devices_start() -> None:
    # Device start-up read the twin names before they were registered, and
    # logged "No parameter with key" (item 31); joystick_init now refuses.
    assert gremlin.config.Configuration().exists(
        *gremlin.device_initialization.TWIN_SETTING
    )
    assert gremlin.config.Configuration().exists(
        "global", "general", "log-when-not-responding"
    )


def test_runtime_listener_guard_names_a_replaced_listener(
    event_listener: gremlin.event_handler.EventListener,
) -> None:
    InputModuleRuntime()  # connects to the package listener
    assert conftest._runtime_listener_problem(event_listener) is None
    kept = gremlin.event_handler.EventListener.instance
    try:
        gremlin.event_handler.EventListener.instance = object()  # type: ignore[assignment]
        assert conftest._runtime_listener_problem(event_listener) == (
            "the EventListener was replaced"
        )
    finally:
        gremlin.event_handler.EventListener.instance = kept


def test_child_programs_print_a_stack_on_a_native_crash() -> None:
    assert os.environ.get("PYTHONFAULTHANDLER")
