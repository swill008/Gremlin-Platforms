# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Log When Not Responding (gremlin/watchdog.py).

When the main loop stops for the threshold, system.log gets "Not
responding" with every thread's stack, once per freeze, and "Responding
again" when it comes back. The option (Options › Diagnostics) is off by
default and takes effect at once.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import time
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtTest

from gremlin import watchdog
from gremlin.config import Configuration


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


def test_a_freeze_is_logged_once_with_the_stacks_then_the_recovery(
    caplog: pytest.LogCaptureFixture,
) -> None:
    dog = watchdog.Watchdog(threshold_s=0.4)
    dog.start()
    try:
        QtTest.QTest.qWait(300)  # responding
        assert "Not responding" not in caplog.text
        time.sleep(1.5)  # the main loop is stuck
        QtTest.QTest.qWait(1500)  # and back
    finally:
        dog.stop()
    assert caplog.text.count("Not responding for") == 1
    assert "Threads: MainThread" in caplog.text
    assert "test_a_freeze_is_logged_once" in caplog.text  # where it was stuck
    assert caplog.text.count("Responding again after") == 1


def test_it_stops_cleanly() -> None:
    dog = watchdog.Watchdog()
    dog.start()
    assert dog.running
    dog.stop()
    assert not dog.running


def test_the_option_is_off_by_default_and_takes_effect_at_once() -> None:
    config = Configuration()
    stored = config.value(*watchdog.OPTION)
    assert stored is False  # the tests start from new settings
    try:
        watchdog.apply()
        assert watchdog._watchdog is None or not watchdog._watchdog.running
        config.set(*watchdog.OPTION, True)
        watchdog.apply()
        assert watchdog._watchdog is not None and watchdog._watchdog.running
        config.set(*watchdog.OPTION, False)
        watchdog.apply()
        assert not watchdog._watchdog.running
    finally:
        config.set(*watchdog.OPTION, stored)
        watchdog.apply()


def test_the_option_is_in_options_diagnostics() -> None:
    from gremlin.ui import option

    groups = dict(dict(option._LAYOUT)["General"])
    assert ("global", "general", "log-when-not-responding") in groups["Diagnostics"]
    assert option._ENTRY_TITLES["log-when-not-responding"] == "Log When Not Responding"
