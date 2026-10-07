# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""08 S108 / S109 (D-08-AUTOMAP-MODE, D-08-AUTOMAP-REASON): the Auto Mapper's
result line names the mode, and gives the true reason when nothing is made:
outputs another input already uses in the mode are skipped (not kept), and an
output module that claims none is named, pointing to "Also claim the matching
outputs on the output module" (the old line blamed the input module)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import auto_mapper
from gremlin.auto_mapper import AutoMapper, AutoMapperOptions


def test_report_names_the_mode() -> None:
    mapper = AutoMapper(None)  # type: ignore[arg-type]
    mapper._created_mappings = [object()] * 36  # type: ignore[list-item]
    assert mapper._create_mappings_report("Default") == (
        "Made 36 actions in Default; 0 inputs kept their actions."
    )


_NXT = {"slug": "nxt", "name": "NXT", "claim": {"buttons": [1, 2, 3]}}


@pytest.fixture
def claims_none() -> Iterator[AutoMapper]:
    dest = {"slug": "vjoy_3", "name": "vJoy 3", "vjoyId": 3, "claim": {}}
    profile = SimpleNamespace(
        get_input_item=lambda *a, **k: SimpleNamespace(action_sequences=[])
    )
    limits = {"axes": set(), "buttons": set(range(1, 9)), "hats": set()}
    with (
        mock.patch.object(auto_mapper.auto_map, "input_modules", return_value=[_NXT]),
        mock.patch.object(auto_mapper.auto_map, "output_modules", return_value=[dest]),
        mock.patch.object(AutoMapper, "_vjoy_limits", return_value=limits),
        mock.patch.object(AutoMapper, "_get_used_vjoy_inputs", return_value=[]),
        mock.patch.object(AutoMapper, "_source_uuid", return_value=uuid.uuid4()),
    ):
        yield AutoMapper(profile)


def test_output_module_that_claims_none_is_named(claims_none: AutoMapper) -> None:
    text = claims_none.generate_module_mappings(
        ["nxt"], ["vjoy_3"], AutoMapperOptions()
    )
    assert text.startswith("The output module vJoy 3 claims none of these outputs"), (
        text
    )
    assert "Also claim the matching outputs on the output module" in text, text
    assert "Input module has no selected" not in text, text
    assert "Skipped vJoy 3 buttons 1-3: not claimed by the output module." in text


def test_used_by_another_input_is_a_skip_not_kept() -> None:
    from gremlin import types

    dest = {
        "slug": "vjoy_3",
        "name": "vJoy 3",
        "vjoyId": 3,
        "claim": {"buttons": [1, 2, 3]},
    }
    profile = SimpleNamespace(
        get_input_item=lambda *a, **k: SimpleNamespace(action_sequences=[])
    )
    used = [types.VjoyInput(3, types.InputType.JoystickButton, n) for n in (1, 2, 3)]
    limits = {"axes": set(), "buttons": set(range(1, 9)), "hats": set()}
    with (
        mock.patch.object(auto_mapper.auto_map, "input_modules", return_value=[_NXT]),
        mock.patch.object(auto_mapper.auto_map, "output_modules", return_value=[dest]),
        mock.patch.object(AutoMapper, "_vjoy_limits", return_value=limits),
        mock.patch.object(AutoMapper, "_get_used_vjoy_inputs", return_value=used),
        mock.patch.object(AutoMapper, "_source_uuid", return_value=uuid.uuid4()),
    ):
        text = AutoMapper(profile).generate_module_mappings(
            ["nxt"], ["vjoy_3"], AutoMapperOptions()
        )
    assert text.startswith("Made 0 actions in Default; 0 inputs kept their actions."), (
        text
    )
    assert (
        "Skipped vJoy 3 buttons 1-3: already used by another input in this mode."
        in text
    ), text
