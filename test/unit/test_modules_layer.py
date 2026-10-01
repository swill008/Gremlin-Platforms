# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin/modules holds the module logic; it must not depend on the UI."""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

# The live debug log is a UI window; it is loaded inside a function only.
_ALLOWED_UI = {"gremlin.ui.live_debug"}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            # "from gremlin.ui import x" imports gremlin.ui.x
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return names


def test_modules_package_does_not_import_the_ui() -> None:
    for path in sorted((_ROOT / "gremlin" / "modules").glob("*.py")):
        for name in _imports(path):
            if name.startswith("gremlin.ui."):
                allowed = name in _ALLOWED_UI or name.rsplit(".", 1)[0] in _ALLOWED_UI
                assert allowed, f"{path.name} imports {name}"
            assert not name.startswith("PySide6.QtQml"), path.name


def test_core_reads_modules_from_the_modules_package() -> None:
    for rel in (
        "gremlin/event_handler.py",
        "gremlin/code_runner.py",
        "gremlin/auto_mapper.py",
    ):
        names = _imports(_ROOT / rel)
        for ui_module in (
            "gremlin.ui.module_calibration",
            "gremlin.ui.auto_map_modules",
            "gremlin.ui.output_modules",
            "gremlin.ui.module_model",
            "gremlin.ui.hardware_profile",
        ):
            assert ui_module not in names, f"{rel} imports {ui_module}"
