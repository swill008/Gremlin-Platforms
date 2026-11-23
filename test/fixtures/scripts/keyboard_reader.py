# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: reacts to the key chosen in a Keyboard variable.

It only records the key events it receives and reads the key's state
through the "keyboard" object; it never sends a key.
"""

from gremlin import event_handler, user_script

mode = user_script.ModeVariable("Mode", "The mode the key works in", True)
key = user_script.KeyboardVariable("Key", "The key to react to", False)

# (pressed, state read through the keyboard object) per event, for tests.
seen: list[tuple[bool, bool]] = []


@key.decorator(mode)
def on_key(event: event_handler.Event, keyboard: object) -> None:
    """Records the key event; reads only, sends nothing."""
    seen.append((bool(event.is_pressed), bool(keyboard.is_pressed(key.value))))
