# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from gremlin.ui import module_model


def test_home_cards_follow_sizes_reset_elsewhere() -> None:
    # Options > Reset all card sizes runs on its own model copy; the Home model
    # must notice the saved sizes changed and refresh its cards.
    home = SimpleNamespace(_sizes_snap={"vjoy_1": (300, 400)}, panesChanged=mock.Mock())
    with mock.patch.object(module_model, "_sizes", return_value={}):
        module_model.ModuleListModel._follow_card_sizes(home)
    home.panesChanged.emit.assert_called_once()
    assert home._sizes_snap == {}


def test_unrelated_config_changes_do_not_refresh_cards() -> None:
    home = SimpleNamespace(_sizes_snap={"vjoy_1": (300, 400)}, panesChanged=mock.Mock())
    with mock.patch.object(module_model, "_sizes", return_value={"vjoy_1": (300, 400)}):
        module_model.ModuleListModel._follow_card_sizes(home)
    home.panesChanged.emit.assert_not_called()
