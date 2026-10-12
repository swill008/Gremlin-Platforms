# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Right-click Favourites setting (07 S137, D-07-RIGHTCLICK-ANSWERS): a
program setting kept by DeviceMapOptions, and the Options group "Right-click
menu" with how many favourites show."""

from __future__ import annotations

import sys

sys.path.append(".")

from gremlin.config import Configuration
from gremlin.ui import device_map_options as bmo


def _clear() -> None:
    bmo.register()
    Configuration().set(bmo.SECTION, "internal", "favourites", [])
    bmo.set_value("favourites-shown", 5)


def test_favourites_toggle_remove_and_keep_order() -> None:
    _clear()
    opts = bmo.DeviceMapOptions()
    other = bmo.DeviceMapOptions()
    seen: list[str] = []
    other.favouritesChanged.connect(lambda: seen.append("x"))
    opts.toggleFavourite("edit.cut")
    opts.toggleFavourite("arrange.group")
    opts.toggleFavourite("edit.paste")
    assert opts.favourites == ["edit.cut", "arrange.group", "edit.paste"]
    # Every open window hears about it.
    assert len(seen) == 3
    assert other.favourites == opts.favourites
    opts.toggleFavourite("arrange.group")
    assert opts.favourites == ["edit.cut", "edit.paste"]
    opts.removeFavourite("edit.cut")
    assert opts.favourites == ["edit.paste"]
    opts.removeFavourite("no.such")
    assert len(seen) == 5
    # Kept for the next window, in the program's settings.
    assert bmo.DeviceMapOptions().favourites == ["edit.paste"]
    stored = Configuration().value(bmo.SECTION, "internal", "favourites")
    assert stored == ["edit.paste"]
    _clear()


def test_favourites_shown_option() -> None:
    _clear()
    group, name, _kind, default, description, props = next(
        o for o in bmo.OPTIONS if o[1] == "01-favourites-shown"
    )
    assert (group, default, props) == ("right-click", 5, {"min": 0, "max": 15})
    assert description.startswith("How many favourites the top of the right-click")
    opts = bmo.DeviceMapOptions()
    assert opts.favouritesShown == 5
    hits: list[int] = []
    opts.favouritesShownChanged.connect(lambda: hits.append(opts.favouritesShown))
    opts.set("favourites-shown", 0)
    assert opts.favouritesShown == 0 and hits == [0]
    opts.set("favourites-shown", 2)
    assert hits == [0, 2]
    _clear()


def test_right_click_group_in_the_options_pane() -> None:
    opts = bmo.DeviceMapOptions()
    titles = {g["key"]: g["title"] for g in opts.groups}
    assert titles["right-click"] == "Right-click menu"
    rows = [e for e in opts.entries if e["group"] == "right-click"]
    assert [(e["key"], e["kind"], e["min"], e["max"]) for e in rows] == [
        ("favourites-shown", "int", 0, 15)
    ]


def test_reset_panels_leaves_favourites() -> None:
    _clear()
    opts = bmo.DeviceMapOptions()
    opts.toggleFavourite("edit.copy")
    opts.resetPanels()
    assert opts.favourites == ["edit.copy"]
    _clear()
