# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Fixtures for the action editor matrix (harness.py)."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import shared_state
from gremlin.logical_device import LogicalDevice
from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    Case,
    open_case,
)

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


class Matrix:
    """Opens cases for one test and closes them after it."""

    def __init__(self, tmp: pathlib.Path) -> None:
        self.tmp = tmp
        self.cases: list[Case] = []

    def open(self, tag: str, input_type: str, surface: str) -> Case:
        case = open_case(tag, input_type, surface, self.tmp)
        self.cases.append(case)
        return case

    def close(self) -> None:
        for case in reversed(self.cases):
            case.close()


@pytest.fixture
def matrix(tmp_path: pathlib.Path) -> Iterator[Matrix]:
    LogicalDevice().reset()
    kept = shared_state.current_profile
    m = Matrix(tmp_path)
    yield m
    m.close()
    shared_state.current_profile = kept
    LogicalDevice().reset()
