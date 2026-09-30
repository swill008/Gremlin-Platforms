# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from unittest import mock

from gremlin import config
from gremlin.ui.option import ActionSequenceOrdering, ProfileAutoLoadingModel


def test_auto_loading_new_entry_and_remove_are_saved() -> None:
    cfg = config.Configuration()
    key = ("profile", "automation", "entries-auto-loading")
    cfg.set(*key, [])
    model = ProfileAutoLoadingModel()
    with mock.patch.object(cfg, "save") as save:
        model.newEntry()
        assert save.call_count == 1
        model.removeEntry(0)
        assert save.call_count == 2
    assert cfg.value(*key) == []


def test_action_order_move_is_saved() -> None:
    cfg = config.Configuration()
    key = ("action", "general", "action-priorities")
    old = [list(entry) for entry in cfg.value(*key)]
    cfg.set(*key, [["first", True], ["second", True]])
    model = ActionSequenceOrdering()
    try:
        with mock.patch.object(cfg, "save") as save:
            model.move(0, 1)
            assert save.call_count == 1
        assert [name for name, _ in cfg.value(*key)] == ["second", "first"]
    finally:
        cfg.set(*key, old)
