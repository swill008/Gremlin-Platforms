# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest

from gremlin import config, util
from gremlin.ui import hardware_profile

_KEY = ("global", "files", "deleted-devices-folder")


@pytest.fixture
def restore_setting() -> Iterator[config.Configuration]:
    cfg = config.Configuration()
    old = cfg.value(*_KEY)
    yield cfg
    cfg.set(*_KEY, pathlib.Path(old))


def test_option_is_a_folder_picker_like_the_others() -> None:
    cfg = config.Configuration()
    assert cfg.exists(*_KEY)
    props = cfg.properties(*_KEY)
    assert props["is_folder"] is True
    assert props["allow_reset"] is True
    default = pathlib.Path(props["default_path"])
    assert default == pathlib.Path(util.data_folder()) / "deleted devices"


def test_backups_default_to_the_data_folder(
    restore_setting: config.Configuration,
) -> None:
    restore_setting.set(*_KEY, pathlib.Path("."))
    folder = hardware_profile._deleted_dir()
    assert folder == pathlib.Path(util.data_folder()) / "deleted devices"
    assert folder.is_dir()


def test_backups_follow_the_chosen_folder(
    restore_setting: config.Configuration, tmp_path: pathlib.Path
) -> None:
    chosen = tmp_path / "my backups"
    restore_setting.set(*_KEY, chosen)
    assert hardware_profile._deleted_dir() == chosen.resolve()
    assert chosen.is_dir()
