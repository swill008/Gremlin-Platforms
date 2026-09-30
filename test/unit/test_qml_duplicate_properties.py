# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PROPERTY = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*:(?!:)")


def _duplicates(path: pathlib.Path) -> list[str]:
    """Properties set twice in one QML object; QML refuses to load such a file."""
    found = []
    seen: list[set[str]] = [set()]
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        code = line.split("//")[0]
        match = _PROPERTY.match(code)
        if (
            match
            and "{" not in code
            and not code.strip().startswith(("case", "default"))
        ):
            name = match.group(1)
            if name in seen[-1]:
                found.append(f"{path.relative_to(_ROOT)}:{number}: {name}")
            seen[-1].add(name)
        for char in code:
            if char == "{":
                seen.append(set())
            elif char == "}" and len(seen) > 1:
                seen.pop()
    return found


def test_no_qml_object_sets_a_property_twice() -> None:
    files = [
        *(_ROOT / "qml").rglob("*.qml"),
        *(_ROOT / "action_plugins").rglob("*.qml"),
    ]
    assert files
    assert [dup for path in files for dup in _duplicates(path)] == []
