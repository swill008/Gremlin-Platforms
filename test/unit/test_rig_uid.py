# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/rig_groups.js _uid: the Button Map's ids for new items.

An id was the clock and a random number 0-999. Break Group makes all its
chips in one millisecond, so two of them now and then shared an id; grouping
them again then took one chip twice and lost the other (the golden test
group_keeps failed about one run in a hundred).
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import (
    QtCore,
    QtQml,
)

_SOURCE = pathlib.Path(__file__).parents[2] / "qml" / "rig_groups.js"
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module")
def js() -> Iterator[QtQml.QJSEngine]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    engine = QtQml.QJSEngine()
    result = engine.evaluate(_SOURCE.read_text(encoding="utf-8"), str(_SOURCE))
    assert not result.isError(), result.toString()
    yield engine


def test_ids_made_at_once_differ(js: QtQml.QJSEngine) -> None:
    # The same millisecond and the same random number: the worst case.
    js.evaluate("Date.now = function () { return 1700000000000 }")
    js.evaluate("Math.random = function () { return 0.5 }")
    ids = js.evaluate(
        "var out = []; for (var i = 0; i < 50; i++) out.push(_uid('b')); out.join(',')"
    ).toString()
    ids = ids.split(",")
    assert len(set(ids)) == len(ids)
    assert all(i.startswith("b_") for i in ids)
