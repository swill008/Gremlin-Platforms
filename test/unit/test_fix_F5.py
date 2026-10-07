# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""F5: a pulse release that already ran is not "still waiting" (validate)."""

from __future__ import annotations

import sys

sys.path.append(".")

import pytest

from gremlin import base_classes, run_scope, validate


def test_a_release_that_ran_is_not_a_pending_pulse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # _pulse_event keeps a fired release in the list until the next pulse.
    run_scope._reset_for_tests()
    fired = run_scope.timer("pulse release", 60, lambda: None, at_stop="fire")
    fired.fire_now()
    monkeypatch.setattr(base_classes, "_pending_pulses", [fired])
    assert validate.after_stop() == []


def test_a_release_still_waiting_is_a_pending_pulse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_scope._reset_for_tests()
    waiting = run_scope.timer("pulse release", 60, lambda: None, at_stop="fire")
    try:
        monkeypatch.setattr(base_classes, "_pending_pulses", [waiting])
        problems = validate.after_stop()
        assert any(p.startswith("RUN-PENDING-PULSES") for p in problems)
    finally:
        waiting.cancel()
        run_scope._reset_for_tests()
