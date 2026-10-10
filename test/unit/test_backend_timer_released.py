# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A Backend a test makes stops ticking when the test ends (CRASH-G2).

Backend keeps a recovery copy of the open profile every 60 s (04 S94). Tests
that make their own Backend (test_stage1_app_profile, test_ld_ui, ...) left
it alive with that timer running, so a minute later it serialised a stale
profile inside whichever test came next. In a full run (seed 869523, unit-4)
the part died with an access violation in pytest-qt's processEvents exactly
when the Backends made at 02:21-02:25 were due their first tick (03:23),
during tests that run nothing in-process. test/unit/conftest.py now stops
the timer of every Backend made in a test when the test ends.

Two tests: whichever runs second checks the other's Backend (the order is
shuffled inside a file).
"""

from __future__ import annotations

import sys
from typing import Any, cast

import pytest
from PySide6 import QtCore

# The timer needs an application to run on (as test_stage1_app_profile).
_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_made: dict[str, Any] = {}


def _make_backend(monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: ANN401
    from gremlin import process_monitor
    from gremlin.ui import backend

    monkeypatch.setattr(process_monitor.ProcessMonitor, "start", lambda self: None)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(backend, "display_error", lambda *a, **k: None)
    return backend.Backend.klass(cast(Any, None))


def _check_other(name: str) -> None:
    for other, be in _made.items():
        if other != name:
            assert not be._recovery_timer.isActive(), (  # noqa: SLF001
                f"the Backend made in {other} still ticks after it ended"
            )


@pytest.mark.parametrize("name", ["first", "second"])
def test_a_backend_made_in_a_test_stops_ticking_after_it(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _check_other(name)
    be = _make_backend(monkeypatch)
    assert be._recovery_timer.isActive()  # noqa: SLF001 - ticks during its test
    _made[name] = be
