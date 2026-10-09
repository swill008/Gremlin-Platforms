# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""ConfigSectionModel works out main_layout() once per instance, not on
every rowCount/data/matchingSections call, and still answers exactly what
a fresh main_layout() gives. A new instance works it out again, so settings
registered since show the next time Options opens."""

from __future__ import annotations

import sys

import pytest
from PySide6 import QtCore

sys.path.append(".")

from gremlin.ui import option  # noqa: E402

_WORDS = ["folder", "tempo", "e", "zzqxj-nothing", "  Other  ", "", "a b"]


@pytest.fixture
def counted(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls = [0]
    real = option.main_layout

    def counting() -> list:
        calls[0] += 1
        return real()

    monkeypatch.setattr(option, "main_layout", counting)
    return calls


def _drive(model: option.ConfigSectionModel) -> list[tuple[str, list]]:
    """What QML asks of the model: rows, every role per row, searches."""
    shown = []
    for _ in range(3):
        rows = model.rowCount()
    for row in range(rows):
        index = model.index(row, 0)
        values = {
            bytes(role_name.data()).decode(): model.data(index, role)
            for role, role_name in model.roleNames().items()
        }
        name = values["name"]
        groups = values["groupModel"]
        shown.append((name, [
            groups.data(groups.index(g, 0), QtCore.Qt.ItemDataRole.UserRole + 1)
            for g in range(groups.rowCount())
        ]))
    for word in _WORDS:
        model.matchingSections(word)
    return shown


def test_layout_worked_out_once_per_instance(counted: list[int]) -> None:
    model = option.ConfigSectionModel()
    _drive(model)
    assert counted[0] <= 1, f"main_layout() ran {counted[0]} times for one model"

    second = option.ConfigSectionModel()
    _drive(second)
    _drive(model)
    assert counted[0] == 2, f"a new model should work it out again: {counted[0]}"


def test_answers_equal_a_fresh_layout() -> None:
    fresh = option.main_layout()
    model = option.ConfigSectionModel()
    shown = _drive(model)
    assert shown == [(title, [g for g, _keys in groups]) for title, groups in fresh]
    for title, groups in fresh:
        for g, keys in groups:
            assert all(len(k) == 3 for k in keys), (title, g)
    for word in _WORDS:
        needle = word.strip().lower()
        expected = [] if not needle else [
            row for row, (_t, groups) in enumerate(option.main_layout())
            if option.ConfigGroupModel("", groups=groups).matches(needle)
        ]
        assert model.matchingSections(word) == expected, word
