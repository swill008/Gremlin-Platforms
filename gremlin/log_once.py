# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Log a repeating problem once instead of on every input.

Some problems repeat for every input while they last (vJoy missing while a
stick moves, an axis with no calibration): logging each one would write the
log file hundreds of times a second. log_once() writes the first one; the
same key stays quiet until reset(), which runs when a profile starts.
"""

from __future__ import annotations

import logging
import threading

_LOCK = threading.Lock()
_seen: set[tuple[str, object]] = set()


def log_once(logger: str, key: object, level: int, message: str) -> None:
    """Log message on logger at level, the first time for this key."""
    with _LOCK:
        if (logger, key) in _seen:
            return
        _seen.add((logger, key))
    logging.getLogger(logger).log(
        level, message + " (shown once; it may keep happening)"
    )


def reset() -> None:
    """Allow every problem to be logged again (a profile starts)."""
    with _LOCK:
        _seen.clear()
