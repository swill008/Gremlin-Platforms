# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Fix round X1: a vJoy read back as an input (03 S16) and the Keyboard and
OSC cards on Home (D-03-S71-ALWAYS)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import config, shared_state
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import module_model
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    vjoy_doc,
    vjoy_guid,
    write_module,
)

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    return request.getfixturevalue(folder.__name__)


@pytest.fixture
def gate(modules: Path) -> Iterator[InputModuleRuntime]:
    runtime = InputModuleRuntime()
    kept = (runtime._claims, runtime._dest_guids, runtime._passthrough)
    yield runtime
    runtime._claims, runtime._dest_guids, runtime._passthrough = kept


@pytest.mark.parametrize("case", ["no output module file", "file without its id"])
def test_a_read_back_vjoy_passes_every_control_whatever_its_file(
    modules: Path, gate: InputModuleRuntime, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    if case == "file without its id":
        write_module(modules, "vjoy_1", vjoy_doc())
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    gate.reload()
    assert not gate.allows(vjoy_guid(), InputType.JoystickButton, 1)
    profile.settings.vjoy_as_input = {1: True}
    gate.reload()
    for kind, ident in (
        (InputType.JoystickButton, 1),
        (InputType.JoystickButton, 9),
        (InputType.JoystickAxis, 2),
        (InputType.JoystickHat, 1),
    ):
        assert gate.allows(vjoy_guid(), kind, ident)


def test_keyboard_and_osc_cards_show_without_a_file_and_show_stubs_off(
    modules: Path,
) -> None:
    module_model._ensure_display_options()
    config.Configuration().set(
        module_model._CFG_SECTION,
        module_model._CFG_GROUP,
        module_model._CFG_SHOW_STUBS,
        False,
    )
    model = module_model.ModuleListModel()
    keyboard = model.cardMap("keyboard")
    osc = model.cardMap("osc")
    assert keyboard.get("name") == "Keyboard"
    assert osc.get("name") == "OSC"
    assert keyboard.get("direction") == "source"
    assert osc.get("direction") == "source"
    # Hidden by the user (Home menu → Hidden Cards) still hides it.
    model.ignoreSlug("osc")
    assert not module_model.ModuleListModel().cardMap("osc").get("name")
    model.unignoreSlug("osc")
