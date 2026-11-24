# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Options › Profiles: the no-profile choice and the Default profile file
row (02 S90, S90a, D-B5-UPSTREAM)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import config
from gremlin.types import PropertyType
from gremlin.ui import option

_CHOICE = ("profile", "automation", "no-profile-action")
_FILE = ("profile", "automation", "default-profile")
_OLD = ("profile", "automation", "remain-active-on-focus-loss")


@pytest.fixture
def model() -> Iterator[tuple[option.ConfigEntryModel, dict[str, int]]]:
    cfg = config.Configuration()
    # Registered by joystick_gremlin's setup; registered here as that
    # setup does when a test runs without it.
    if not cfg.exists(*_CHOICE):
        cfg.register(
            *_CHOICE, PropertyType.Selection, "stop", "",
            {"valid_options": ["stop", "keep", "default"]}, True,
        )
    if not cfg.exists(*_FILE):
        cfg.register(
            *_FILE, PropertyType.Path, Path(""), "", {"is_folder": False}, True,
        )
    before = (cfg.value(*_CHOICE), cfg.value(*_FILE))
    entries = option.ConfigEntryModel("profile", "automation", keys=[_CHOICE, _FILE])
    roles = {bytes(v.data()).decode(): k for k, v in entries.roles.items()}
    try:
        yield entries, roles
    finally:
        cfg.set(*_CHOICE, before[0])
        cfg.set(*_FILE, Path(before[1]))


def test_the_rows_replace_the_keep_running_switch() -> None:
    groups = dict(dict(option._LAYOUT)["Profiles"])  # noqa: SLF001
    keys = groups["Auto-load"]
    assert _OLD not in keys
    assert keys.index(_CHOICE) + 1 == keys.index(_FILE)
    assert option.entry_title("no-profile-action") == (
        "When a program with no profile comes to the front"
    )
    assert option.entry_title("default-profile") == "Default profile"


def test_the_choice_shows_its_three_words(
    model: tuple[option.ConfigEntryModel, dict[str, int]],
) -> None:
    entries, roles = model
    ix = entries.index(0, 0)
    assert entries.data(ix, roles["data_type"]) == "selection"
    assert entries.data(ix, roles["properties"])["valid_options"] == [
        "Stop the profile", "Keep running", "Load the default profile",
    ]


def test_choosing_writes_the_setting_and_only_default_enables_the_file(
    model: tuple[option.ConfigEntryModel, dict[str, int]],
) -> None:
    entries, roles = model
    cfg = config.Configuration()
    choice, file_row = entries.index(0, 0), entries.index(1, 0)
    changed: list[int] = []
    entries.dataChanged.connect(lambda top, _bottom, _roles: changed.append(top.row()))

    expected = {
        "Stop the profile": ("stop", False),
        "Keep running": ("keep", False),
        "Load the default profile": ("default", True),
    }
    for shown, (stored, enabled) in expected.items():
        changed.clear()
        assert entries.setData(choice, shown, roles["value"])
        assert cfg.value(*_CHOICE) == stored
        assert entries.data(choice, roles["value"]) == shown
        assert entries.data(file_row, roles["enabled"]) is enabled
        # The file row is told to update its greyed-out state.
        assert 1 in changed
    # The choice row itself is always usable.
    assert entries.data(choice, roles["enabled"]) is True


def test_the_file_row_is_a_profile_file_picker(
    model: tuple[option.ConfigEntryModel, dict[str, int]],
) -> None:
    entries, roles = model
    file_row = entries.index(1, 0)
    assert entries.data(file_row, roles["data_type"]) == "path"
    props = entries.data(file_row, roles["properties"])
    assert props["picker_kind"] == "profile"
    assert not props.get("is_folder", False)
    # No file chosen shows an empty field, not ".".
    config.Configuration().set(*_FILE, Path(""))
    assert entries.data(file_row, roles["value"]) == ""

    chosen = "C:/Profiles/default.xml"
    assert entries.setData(file_row, chosen, roles["value"])
    assert config.Configuration().value(*_FILE) == Path(chosen)
    assert Path(entries.data(file_row, roles["value"])) == Path(chosen)
