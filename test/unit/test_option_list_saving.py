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
            # Drop targets are "just before this row"; 2 is the end slot.
            model.move(0, 2)
            assert save.call_count == 1
        assert [name for name, _ in cfg.value(*key)] == ["second", "first"]
    finally:
        cfg.set(*key, old)


def test_action_order_drops_land_where_shown() -> None:
    cfg = config.Configuration()
    key = ("action", "general", "action-priorities")
    old = [list(entry) for entry in cfg.value(*key)]
    model = ActionSequenceOrdering()

    def order(src: int, dst: int) -> list[str]:
        cfg.set(*key, [[n, True] for n in "abcd"])
        model.move(src, dst)
        return [name for name, _ in cfg.value(*key)]

    try:
        with mock.patch.object(cfg, "save"):
            assert order(0, 2) == list("bacd")  # Down: before c.
            assert order(3, 1) == list("adbc")  # Up: before b.
            assert order(1, 1) == list("abcd")  # Onto itself.
            assert order(1, 2) == list("abcd")  # Just below itself.
            assert order(0, 4) == list("bcda")  # The end slot.
    finally:
        cfg.set(*key, old)
