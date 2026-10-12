# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Condition waits for off-screen Qt tests and smoke scripts (to-do 24).

A fixed QTest.qWait(N) is either too short on a slow CI machine or wasted
time on a fast one. wait_until pumps events until the named thing is true and
returns at once; a generous bound keeps it hang-proof. Smoke scripts run with
test/unit as sys.path[0], so they add test/ before importing this module.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from PySide6 import QtTest

T = TypeVar("T")

# CI machines are slow; a wait returns as soon as its condition holds.
DEFAULT_TIMEOUT_MS = 20000


def wait_until(
    predicate: Callable[[], T],
    what: str,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    step_ms: int = 10,
    fail: bool = True,
) -> T:
    """Pumps Qt events until predicate() is truthy and returns that value.

    On timeout raises AssertionError naming what (fail=True), or returns the
    last falsy value (fail=False, for callers that check the result
    themselves)."""
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() >= deadline:
            if fail:
                raise AssertionError(
                    f"timed out after {timeout_ms} ms waiting for {what}"
                )
            return value
        QtTest.QTest.qWait(step_ms)
