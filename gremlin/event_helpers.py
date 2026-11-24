# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Mode change callbacks of a Run.

The release after a mode change (06 S38) is the event handler's pending
table (EventHandler._pending), not a registry here: the old release registry
(ButtonReleaseActions) went with D-06-MODE-RELEASE, so nothing releases twice.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Hashable

from gremlin import common

# Called with (old mode name, new mode name); True when it has done its work
# and its entry can go.
type ModeChangeCallback = Callable[[str, str], bool]


@common.SingletonDecorator
class ModeChangeActions:
    """Runs callbacks when the running profile's mode changes.

    An action holding state from the mode it started in (Map to Mouse
    motion, 06 S88) registers a callback; the callback decides what to do.
    The runner calls fire() from its mode change listener, which is
    connected only while a profile runs; nothing connects here itself.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._registry: dict[Hashable, ModeChangeCallback] = {}

    def register(self, key: Hashable, callback: ModeChangeCallback) -> None:
        """Adds callback under key; an existing key's callback is replaced
        (a repeated press doesn't pile up entries)."""
        with self._lock:
            self._registry[key] = callback

    def unregister(self, key: Hashable) -> None:
        with self._lock:
            self._registry.pop(key, None)

    def reset(self) -> None:
        """Forgets every callback (start and Stop)."""
        with self._lock:
            self._registry = {}

    def fire(self, old_mode: str, new_mode: str) -> None:
        """Runs every callback for the change from old_mode to new_mode."""
        with self._lock:
            entries = list(self._registry.items())
        # Run without the lock: a callback may register or unregister.
        for key, callback in entries:
            try:
                done = callback(old_mode, new_mode)
            except Exception:
                logging.getLogger("system").exception(
                    f"Mode change callback for {key} failed"
                )
                done = True
            if done:
                with self._lock:
                    # Not if it was replaced while it ran.
                    if self._registry.get(key) is callback:
                        del self._registry[key]
