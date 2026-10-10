# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Axis shaping maths shared by the Response Curve action and OSC's axis
inputs (S161). Pure, no Qt."""

from __future__ import annotations


def deadzone(
    value: float, low: float, low_center: float, high_center: float, high: float
) -> float:
    """Returns the mapped value taking the provided deadzone into
    account.

    The following relationship between the limits has to hold.
    -1 <= low < low_center <= 0 <= high_center < high <= 1

    Args:
        value: the raw input value
        low: low deadzone limit
        low_center: lower center deadzone limit
        high_center: upper center deadzone limit
        high: high deadzone limit

    Returns:
        Corrected value
    """
    if value >= 0:
        return min(
            1.0, max(0.0, (value - high_center) / max(0.01, abs(high - high_center)))
        )
    else:
        return max(
            -1.0, min(0.0, (value - low_center) / max(0.01, abs(low - low_center)))
        )


def shape(value: float, invert: bool, low: float, high: float) -> float:
    """An OSC axis value (-1..1) after its centre deadzone (values between
    low <= 0 and high >= 0 become 0, the rest stretched to the full range)
    and then Invert. (0, 0) is no deadzone."""
    if low != 0.0 or high != 0.0:
        value = deadzone(value, -1.0, low, high, 1.0)
    return -value if invert else value
