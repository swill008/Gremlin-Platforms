# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import ast
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _hidden_imports() -> set[str]:
    """The hidden_imports list of the PyInstaller spec."""
    tree = ast.parse((_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "hidden_imports"
                for target in node.targets
            )
        ):
            return set(ast.literal_eval(node.value))
    raise AssertionError("joystick_gremlin.spec has no hidden_imports list")


def test_every_action_plugin_is_a_hidden_import() -> None:
    # A plugin left out is not compiled into the exe and may not appear in
    # Add Action in a build.
    plugins = {
        f"action_plugins.{init.parent.name}"
        for init in (_ROOT / "action_plugins").glob("*/__init__.py")
    }
    missing = sorted(plugins - _hidden_imports())
    assert not missing, f"Add to hidden_imports in joystick_gremlin.spec: {missing}"
