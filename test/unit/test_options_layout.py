# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The main Options window shows every registered setting exactly once, in
its sidebar sections (stored keys unchanged); the Button Map's settings are
only in its own window. The Add Action Menu list reorders an action among
its own kind and leaves every other action in its place."""

from __future__ import annotations

import sys

sys.path.append(".")

from unittest import mock

from gremlin import config
from gremlin.ui import option


def test_every_setting_shows_once_and_button_map_is_apart() -> None:
    layout = option.main_layout()
    titles = [title for title, _groups in layout]
    assert titles[:3] == ["General", "Interface", "Actions"]
    assert "Button Map" not in titles
    shown = [key for _t, groups in layout for _g, keys in groups for key in keys]
    assert len(shown) == len(set(shown))  # nothing twice
    assert not any(key[0] in option._OWN_WINDOW for key in shown)
    assert not any(key in option._HIDDEN for key in shown)
    expected = {
        key for key in option._shown_keys() if key[0] not in option._OWN_WINDOW
    }
    assert set(shown) == expected  # nothing left out


def _rows(names: list[str]) -> list[list]:
    return [[name, True] for name in names]


def test_move_among_keeps_other_kinds_in_place() -> None:
    cfg = config.Configuration()
    key = ("action", "general", "action-priorities")
    old = [list(entry) for entry in cfg.value(*key)]
    start = ["Map to vJoy", "Macro", "Map to Mouse", "Tempo", "Map to Keyboard"]
    cfg.set(*key, _rows(start))
    model = option.ActionSequenceOrdering()
    try:
        with mock.patch.object(cfg, "save"):
            # The "map" rows are 0, 2 and 4: move Map to Keyboard first.
            model.moveAmong([0, 2, 4], 4, 0)
            names = [name for name, _ in cfg.value(*key)]
            assert names == [
                "Map to Keyboard", "Macro", "Map to vJoy", "Tempo", "Map to Mouse"
            ]
            model.setShown(1, False)
            assert cfg.value(*key)[1] == ["Macro", False]
            model.resetDefaults()
            names = [name for name, _ in cfg.value(*key)]
            assert names[:2] == ["Map to vJoy", "Macro"]
            assert all(shown for _n, shown in cfg.value(*key))
    finally:
        cfg.set(*key, old)


def test_history_settings_have_their_own_group() -> None:
    # Help says Options -> General -> History (they were under "Other").
    general = dict(dict(option.main_layout())["General"])
    keys = general.get("History", [])
    assert ("global", "history", "keep-days") in keys
    assert ("global", "history", "max-megabytes") in keys
    assert "Other" not in general or not [
        k for k in general["Other"] if k[1] == "history"
    ]
    assert option.entry_title("keep-days") == "Days to keep changes"
    assert option.entry_title("max-megabytes") == "Largest history file (MB)"
