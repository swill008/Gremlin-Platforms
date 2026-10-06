# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Elapsed time goes through gremlin.clock (GL-002; 01 S94, 03 7.15).

clock.monotonic() is the one place the program reads elapsed time, so a test
can step it like clock.now. These tests step it and check that each reader
named in GL-002 follows it: the Configuration reload skip, the output
module's claim cache, the Calibration undo merge window. The vJoy busy retry
(test_device_fixes), the Status claim cache (test_status_claim_cache) and the
Not Responding watchdog (test_watchdog) are stepped the same way in their
own tests. Behaviour is unchanged (Spec: none).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import time
import types

import pytest

from gremlin import clock


class _Stepper:
    """A clock.monotonic the test moves by hand."""

    def __init__(self, start: float = 1000.0) -> None:
        self.value = start

    def __call__(self) -> float:
        return self.value


@pytest.fixture
def stepper(monkeypatch: pytest.MonkeyPatch) -> _Stepper:
    step = _Stepper()
    monkeypatch.setattr(clock, "monotonic", step)
    return step


def test_monotonic_reads_the_monotonic_clock() -> None:
    before = time.monotonic()
    first = clock.monotonic()
    second = clock.monotonic()
    assert before <= first <= second <= time.monotonic()


def test_configuration_skips_a_reload_for_one_second(
    stepper: _Stepper, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.config import Configuration

    cfg = Configuration()
    monkeypatch.setattr(cfg, "_last_reload", stepper.value)
    stepper.value += 0.5
    assert cfg._should_skip_reload()
    stepper.value += 0.6
    assert not cfg._should_skip_reload()


def test_output_claims_are_read_again_after_the_cache_time(
    stepper: _Stepper, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import output

    reads: list[int] = []

    def outputs() -> list:
        reads.append(1)
        return []

    monkeypatch.setattr(output.registry, "outputs", outputs)
    for name in ("_claims_at", "_vjoy_claims", "_vjoy_names", "_vjoy_modules",
                 "_xbox_modules"):
        monkeypatch.setattr(output, name, getattr(output, name))
    output._refresh_claims(force=True)
    assert len(reads) == 1
    stepper.value += output._CLAIM_TTL / 2
    output._refresh_claims()
    assert len(reads) == 1  # still fresh
    stepper.value += output._CLAIM_TTL
    output._refresh_claims()
    assert len(reads) == 2


def test_calibration_undo_merges_steps_inside_the_window(stepper: _Stepper) -> None:
    from gremlin.ui.device import AxisCalibration

    model = types.SimpleNamespace(
        _last_step=None,
        _undo=[],
        _redo=[],
        UNDO_STEPS=AxisCalibration.UNDO_STEPS,
        _MERGE_SECONDS=AxisCalibration._MERGE_SECONDS,
        _limits=lambda index: (index,),
        undoChanged=types.SimpleNamespace(emit=lambda: None),
    )

    def step() -> None:
        AxisCalibration._step(model, 0, "low")  # type: ignore[arg-type]

    step()
    stepper.value += AxisCalibration._MERGE_SECONDS / 2
    step()
    assert len(model._undo) == 1  # one drag, one undo step
    stepper.value += AxisCalibration._MERGE_SECONDS * 2
    step()
    assert len(model._undo) == 2
