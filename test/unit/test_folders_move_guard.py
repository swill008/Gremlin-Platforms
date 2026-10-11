# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Tests never reach the real Gremlin Platforms folder (D-03-DEVICE-FOLDERS,
contract section 7): the conftest side of the guard. test/conftest.py sets
GREMLIN_TESTS=1, which the one-time device folders move (03 S134, OT-1;
folders_move.run_if_needed) checks, and points the data and modules folders
at a temporary one. The move's own refusal is tested in test_folders_move.py.
"""

from __future__ import annotations

import os
from pathlib import Path

from gremlin import util
from gremlin.modules import store


def _real_data_folder() -> Path:
    return (Path(os.environ["USERPROFILE"]) / util.USER_DATA_FOLDER).resolve()


def _under(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(root)
    except ValueError:
        return False
    return True


def test_tests_say_they_are_tests() -> None:
    assert os.environ.get("GREMLIN_TESTS") == "1"


def test_data_and_modules_folders_are_not_the_real_ones() -> None:
    real = _real_data_folder()
    assert not _under(Path(util.data_folder()), real), util.data_folder()
    assert not _under(store.folder(), real), store.folder()
