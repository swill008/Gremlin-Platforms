# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: a periodic callback counts while the profile runs.

The interval is a variable (0.05 s by default). The program runs periodic
callbacks no faster than every 0.01 s and stops them at Stop.
"""

from gremlin import user_script

interval = user_script.FloatVariable(
    "Interval",
    "Seconds between ticks",
    is_optional=True,
    initial_value=0.05,
    min_value=0.01,
    max_value=1.0,
)

# One entry per tick, for tests.
ticks: list[int] = []


@user_script.periodic(interval.value)
def tick() -> None:
    """Adds one tick."""
    ticks.append(len(ticks) + 1)
