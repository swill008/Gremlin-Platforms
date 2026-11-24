# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The action pane's feedback cache keeps no entry per pane open.

Each open drafts the input (Library.draft), so the pane's root action is a
fresh copy with a new id; the cache must not keep one entry per open."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest

from gremlin import action_analysis, clock
from gremlin.profile import Profile
from gremlin.types import InputType

_DEV = uuid.UUID("11111111-2222-3333-4444-555555555555")


class _FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeClock]:
    fake = _FakeClock()
    monkeypatch.setattr(clock, "monotonic", fake.monotonic)
    action_analysis._feedback_cache.clear()
    yield fake
    action_analysis._feedback_cache.clear()


def _input() -> object:
    p = Profile()
    item = p.get_input_item(
        _DEV, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    assert item is not None
    item.add_item_binding()
    return item


def test_opening_the_pane_many_times_keeps_the_cache_size_fixed(
    fake_clock: _FakeClock,
) -> None:
    item = _input()
    sizes = []
    for _ in range(50):
        draft = item.library.draft(item)  # type: ignore[attr-defined]
        binding = draft.item.action_sequences[0]
        action_analysis.action_sequence_feedback(binding)
        item.library.discard(draft)  # type: ignore[attr-defined]
        sizes.append(len(action_analysis._feedback_cache))
        fake_clock.t += action_analysis._CACHE_TTL * 2
    assert max(sizes) <= 1, sizes


def test_a_changed_action_still_gets_a_fresh_result(
    fake_clock: _FakeClock,
) -> None:
    item = _input()
    binding = item.action_sequences[0]  # type: ignore[attr-defined]
    first = action_analysis.action_sequence_feedback(binding)
    # Within the time-to-live the same result is served.
    assert action_analysis.action_sequence_feedback(binding) is first
    fake_clock.t += action_analysis._CACHE_TTL * 2
    again = action_analysis.action_sequence_feedback(binding)
    assert again is not first and again == first
