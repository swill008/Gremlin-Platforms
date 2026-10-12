# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every QML file in qml/ and its subfolders is used somewhere (by type
name or file name)."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_every_qml_file_is_referenced() -> None:
    sources = [
        *_ROOT.joinpath("qml").rglob("*.qml"),
        *_ROOT.joinpath("qml").rglob("*.js"),
        *_ROOT.joinpath("action_plugins").rglob("*.qml"),
        *_ROOT.joinpath("action_plugins").rglob("*.py"),
        *_ROOT.joinpath("gremlin").rglob("*.py"),
        _ROOT / "joystick_gremlin.py",
        _ROOT / "input_tester.py",  # loads qml/tester/InputTester.qml
    ]
    texts = {
        path: path.read_text(encoding="utf-8", errors="ignore") for path in sources
    }
    unused = []
    for qml in sorted(_ROOT.joinpath("qml").rglob("*.qml")):
        word = re.compile(rf"\b{re.escape(qml.stem)}\b")
        if not any(word.search(text) for path, text in texts.items() if path != qml):
            unused.append(qml.relative_to(_ROOT).as_posix())
    assert unused == []
