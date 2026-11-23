# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script with a required variable that starts unset.

"Callsign" is required (is_optional=False) and starts empty, which isn't a
valid text, so the script loads without an error but is not configured:
Run skips it (its periodic callback never ticks) until Callsign is set.
"""

from gremlin import user_script

callsign = user_script.StringVariable(
    "Callsign", "Required: any text", is_optional=False, initial_value=""
)

repeat = user_script.IntegerVariable(
    "Repeat",
    "Optional: how many times",
    is_optional=True,
    initial_value=1,
    min_value=1,
    max_value=5,
)

# One entry per tick, for tests.
ticks: list[str] = []


@user_script.periodic(0.02)
def tick() -> None:
    """Ticks only when the script runs."""
    ticks.append(callsign.value * repeat.value)
