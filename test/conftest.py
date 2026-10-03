# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pathlib
import tempfile

# Mock before any imports happen
from unittest.mock import Mock

import pytest

import gremlin.util

gremlin.util.userprofile_path = Mock(return_value=tempfile.mkdtemp())

import gremlin.ui.backend  # noqa: E402
import joystick_gremlin  # noqa: E402


def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Stops a run that mixes test/unit with the folders needing the Gremlin app.

    The unit tests run on a plain QCoreApplication; test/integration and
    test/action_interaction need JoystickGremlinApp. One process has one
    application, so mixed runs fail in hundreds of confusing ways.
    """
    root = pathlib.Path(__file__).parent
    folders = set()
    for item in items:
        try:
            folders.add(pathlib.Path(str(item.path)).relative_to(root).parts[0])
        except ValueError:
            continue
    if "unit" in folders and folders & {"integration", "action_interaction"}:
        raise pytest.UsageError(
            "Run each test folder in its own pytest run: "
            "pytest test/unit, pytest test/integration, pytest test/action_interaction."
        )


@pytest.fixture(scope="session")
def qapp_cls() -> type[joystick_gremlin.JoystickGremlinApp]:
    return joystick_gremlin.JoystickGremlinApp


@pytest.fixture(scope="session")
def test_root_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent
