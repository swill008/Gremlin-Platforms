# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

# Tests never put a window on the user's screen: the Gremlin app some tests
# build (pytest-qt's qapp) and every window it opens stay off-screen.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)

# Mock before any imports happen
from unittest.mock import Mock

import pytest

import gremlin.util

gremlin.util.userprofile_path = Mock(return_value=tempfile.mkdtemp())

import gremlin.ui.backend  # noqa: E402
import gremlin.windows_event_hook  # noqa: E402
import joystick_gremlin  # noqa: E402

# By its folder: as a plain module (pytest -p conftest), "test" is Python's own.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fake_input  # noqa: E402  # pyright: ignore[reportMissingImports]

# Tests never hook the keyboard and mouse of the PC they run on, and never
# send keys or mouse input to it (test/fake_input.py).
gremlin.windows_event_hook.enabled = False
fake_input.install()


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


@pytest.fixture(autouse=True)
def _no_message_boxes(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """No test shows a real Windows message box (they appear on screen even
    off-screen, and wait for a click): they are recorded instead."""
    shown: list[tuple] = []
    monkeypatch.setattr(
        joystick_gremlin, "_message_box", lambda *a: shown.append(a) or 1
    )
    return shown


@pytest.fixture(scope="session")
def qapp_cls() -> type[joystick_gremlin.JoystickGremlinApp]:
    return joystick_gremlin.JoystickGremlinApp


@pytest.fixture(scope="session")
def test_root_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent
