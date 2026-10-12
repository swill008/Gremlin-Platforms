# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""test/qt_wait.py: wait_until returns as soon as ready and fails clearly."""

from __future__ import annotations

import time

import pytest
import qt_wait  # pyright: ignore[reportMissingImports]  (test/)
from PySide6 import QtCore


@pytest.fixture(scope="module")
def app() -> QtCore.QCoreApplication:
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def test_returns_early_with_the_value(app: QtCore.QCoreApplication) -> None:
    hits: list[int] = []
    QtCore.QTimer.singleShot(30, lambda: hits.append(1))
    start = time.monotonic()
    value = qt_wait.wait_until(lambda: hits and "ready", "timer", 20000)
    assert value == "ready"
    assert time.monotonic() - start < 5


def test_times_out_with_the_message(app: QtCore.QCoreApplication) -> None:
    start = time.monotonic()
    with pytest.raises(AssertionError, match="waiting for the thing"):
        qt_wait.wait_until(lambda: False, "the thing", 100)
    assert time.monotonic() - start >= 0.1


def test_no_fail_returns_the_last_value(app: QtCore.QCoreApplication) -> None:
    assert qt_wait.wait_until(lambda: 0, "zero", 50, fail=False) == 0
