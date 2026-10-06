# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Waits for these tests that end on a result, not after a fixed time
(GL-001, AU-119; 01 S94, program thread rules).

A busy PC makes timers late, never early: a test waits for what it expects
with a generous limit, and a test that checks timing makes the time in its
profile comfortably large (profile_with) instead of shrinking its waits.
"""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from collections.abc import Callable
from pathlib import Path

from gremlin import event_handler

from .conftest import JoystickGremlinBot

# Generous: a busy PC is slow, never wrong.
LIMIT_MS = 10_000


def wait_until(jgbot: JoystickGremlinBot, done: Callable[[], bool]) -> None:
    """Runs the event loop until done() is true, up to LIMIT_MS."""
    jgbot.qtbot.waitUntil(done, timeout=LIMIT_MS)


def next_event(jgbot: JoystickGremlinBot) -> event_handler.Event:
    """The next event, waiting up to LIMIT_MS for it (next_event() alone
    gives up after half a second)."""
    wait_until(jgbot, lambda: jgbot.event_count() > 0)
    return jgbot.next_event()


def assert_no_event_for(jgbot: JoystickGremlinBot, seconds: float) -> None:
    """Nothing more comes in seconds: a check that something does not happen
    can only wait a fixed time (a slow PC makes it pass, never fail)."""
    jgbot.wait(seconds)
    assert jgbot.event_count() == 0


def profile_with(
    source: Path, folder: Path, changes: dict[str, dict[str, str]]
) -> Path:
    """A copy of the profile in folder with some action properties changed.

    changes: {action id: {property name: new value}}, for a time in the
    test data made comfortably large.
    """
    tree = ElementTree.parse(source)
    library = tree.getroot().find("library")
    assert library is not None
    found = {}
    for action in library:
        wanted = changes.get(action.get("id", ""))
        if wanted is None:
            continue
        for prop in action.iter("property"):
            name = prop.findtext("name")
            if name in wanted:
                value = prop.find("value")
                assert value is not None
                value.text = wanted[name]
                found[(action.get("id"), name)] = True
    missing = [
        (action_id, name)
        for action_id, names in changes.items()
        for name in names
        if (action_id, name) not in found
    ]
    assert not missing, f"not in {source.name}: {missing}"
    target = folder / source.name
    tree.write(target, encoding="utf-8", xml_declaration=True)
    return target
