# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

sys.path.append(".")

from action_plugins.root import RootData
from gremlin.profile import Profile
from gremlin.types import InputType


def test_library_check_does_not_drop_unfinished_actions() -> None:
    """Writing the library for a comparison must leave the open profile alone."""
    profile = Profile()
    root = RootData(InputType.JoystickButton)
    profile.library.add_action(root)
    children = []
    for _ in range(13):
        child = RootData(InputType.JoystickButton)
        profile.library.add_action(child)
        root.children.append(child)
        children.append(child)
    children[0].is_valid = lambda: False
    children[12].is_valid = lambda: False

    profile.library.to_xml()

    assert [child.id for child in root.children] == [child.id for child in children]


def test_library_save_removes_every_invalid_child() -> None:
    """An explicit save removes every unfinished action, including a later one.

    Removing the early one first used to crash on a position that no longer
    existed.
    """
    profile = Profile()
    root = RootData(InputType.JoystickButton)
    profile.library.add_action(root)
    children = []
    for _ in range(13):
        child = RootData(InputType.JoystickButton)
        profile.library.add_action(child)
        root.children.append(child)
        children.append(child)
    children[0].is_valid = lambda: False
    children[12].is_valid = lambda: False

    profile.library.drop_invalid_actions()

    assert [child.id for child in root.children] == [
        child.id for child in children[1:12]
    ]
