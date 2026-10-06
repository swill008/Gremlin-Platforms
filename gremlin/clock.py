# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The time the program's timed loops run on.

The relative axis loops read the time and sleep between steps. They do it
through here, so a test can run them on a clock it steps itself (replace
now and sleep) instead of patching the time module. Code that measures how
long something took (timeouts, retry gaps, the watchdog) reads monotonic(),
which a test replaces the same way.
"""

from __future__ import annotations

import time


def now() -> float:
    """Seconds since the epoch, like time.time()."""
    return time.time()


def monotonic() -> float:
    """Seconds that only go forward, like time.monotonic(): for elapsed time."""
    return time.monotonic()


def sleep(seconds: float) -> None:
    """Waits seconds, like time.sleep()."""
    time.sleep(seconds)
