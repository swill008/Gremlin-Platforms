# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Auto Mapper (08 S97, D-08-AUTOMAP-NOTE): after Create 1:1 Actions the
result says the new actions are in the open profile and not saved yet, with
Overwrite on or off. Only the Overwrite question said so; the result line
under the button is what the Tools slot (createMappings) hands the dialog."""

from __future__ import annotations

from pathlib import Path

import pytest

from gremlin.auto_mapper import AutoMapper, AutoMapperOptions
from gremlin.ui.tools import Tools
from test.unit import test_stage1_modules
from test.unit.test_stage1_history_pack import _auto_map_setup, new_profile
from test.unit.test_stage1_modules import mapped, stick_uid

_app = test_stage1_modules._app
folder = test_stage1_modules.folder

NOTE = (
    "The new actions are in the open profile and not saved yet. "
    "Use File › Save Profile to keep them, or load the profile again to undo."
)


@pytest.mark.parametrize("overwrite", [False, True])
def test_the_result_says_the_new_actions_are_not_saved(
    folder: Path, monkeypatch: pytest.MonkeyPatch, overwrite: bool
) -> None:
    _auto_map_setup(folder, [1, 2], [1, 2])
    profile = new_profile(monkeypatch)
    text = Tools().createMappings(
        "Default", {"pjoy_pro": True}, {"vjoy_1": True}, overwrite, False, False
    )
    assert mapped(profile, stick_uid()) == {("Default", 1), ("Default", 2)}
    assert text.startswith("Made 2 actions in Default;"), text
    assert NOTE in text, text


def test_no_note_when_nothing_changed(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second run with Overwrite off makes nothing: nothing to save."""
    _auto_map_setup(folder, [1], [1])
    profile = new_profile(monkeypatch)
    AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions()
    )
    text = AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions()
    )
    assert text.startswith(
        "Made 0 actions in Default; 1 inputs kept their actions."
    ), text
    assert "not saved yet" not in text, text
