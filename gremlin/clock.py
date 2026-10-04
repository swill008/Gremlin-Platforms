# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The time the program's timed loops run on.

The relative axis loops read the time and sleep between steps. They do it
through here, so a test can run them on a clock it steps itself (replace
now and sleep) instead of patching the time module.
"""

from __future__ import annotations

import time


def now() -> float:
    """Seconds since the epoch, like time.time()."""
    return time.time()


def sleep(seconds: float) -> None:
    """Waits seconds, like time.sleep()."""
    time.sleep(seconds)
