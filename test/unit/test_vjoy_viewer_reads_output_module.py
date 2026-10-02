# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The vJoy Viewer cards show what the vJoy output module sent: claimed
outputs only, and nothing while Gremlin is not running."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from gremlin.modules import output
from gremlin.ui import pair_live


def _card() -> SimpleNamespace:
    card = SimpleNamespace(
        _vjoy_ids={"vjoy3": 3},
        _vj_axis={},
        _vj_button={},
        bumps=[],
    )
    card._bump_axis = lambda: card.bumps.append("axis")
    card._bump_button = lambda: card.bumps.append("button")
    return card


def test_values_come_from_the_output_module() -> None:
    card = _card()
    state = {("axis", 1): 0.5, ("button", 7): 1.0}
    with (
        mock.patch.object(pair_live, "_gremlin_running", return_value=True),
        mock.patch.object(output, "vjoy_state", return_value=state) as read,
    ):
        pair_live.PairLiveThrottle._poll_vjoy(card)
    read.assert_called_once_with(3)
    assert card._vj_axis == {("vjoy3", 1): 0.5}
    assert card._vj_button == {("vjoy3", 7): 1.0}
    assert card.bumps == ["axis", "button"]


def test_nothing_shown_while_gremlin_is_off() -> None:
    card = _card()
    card._vj_button = {("vjoy3", 7): 1.0}
    with (
        mock.patch.object(pair_live, "_gremlin_running", return_value=False),
        mock.patch.object(output, "vjoy_state") as read,
    ):
        pair_live.PairLiveThrottle._poll_vjoy(card)
    read.assert_not_called()
    assert card._vj_button == {}
