# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/rig_layers.js normalizeStacking: the Button Map's stacking order.

It sorted every map each time it was opened or saved, putting every drawing
under every chip, so Bring to Front and Layers-panel moves were undone. Only
old layouts (with zLayer) are sorted now; the list order is the stack.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import (
    QtCore,
    QtQml,
)

_SOURCE = pathlib.Path(__file__).parents[2] / "qml" / "rig_layers.js"
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module")
def js() -> Iterator[QtQml.QJSEngine]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    engine = QtQml.QJSEngine()
    code = _SOURCE.read_text(encoding="utf-8").replace(".pragma library", "")
    # The editor's own helpers that normalizeStacking uses.
    code += "\nfunction isDraw(n) { return n.kind === 'draw' }\nvar nodes = []\n"
    result = engine.evaluate(code, str(_SOURCE))
    assert not result.isError(), result.toString()
    yield engine


def _stack(engine: QtQml.QJSEngine, nodes: list[dict]) -> list[dict]:
    engine.evaluate(f"nodes = {json.dumps(nodes)}; normalizeStacking()")
    return json.loads(engine.evaluate("JSON.stringify(nodes)").toString())


def test_list_order_is_kept(js: QtQml.QJSEngine) -> None:
    nodes = [
        {"id": "chip1", "kind": "btn"},
        {"id": "rect", "kind": "draw"},  # brought to the front
    ]
    assert [n["id"] for n in _stack(js, nodes)] == ["chip1", "rect"]


def test_old_layouts_are_sorted_once_by_layer(js: QtQml.QJSEngine) -> None:
    nodes = [
        {"id": "chip1", "kind": "btn", "zLayer": 3},
        {"id": "top", "kind": "draw", "zLayer": 4, "pinned": True},
        {"id": "rect", "kind": "draw", "zLayer": 2},
    ]
    out = _stack(js, nodes)
    assert [n["id"] for n in out] == ["rect", "chip1", "top"]
    assert all("zLayer" not in n for n in out)
    assert out[2]["locked"] is True and "pinned" not in out[2]
