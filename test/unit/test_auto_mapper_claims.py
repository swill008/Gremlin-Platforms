# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Auto Mapper maps within the output module's claim, reports what it
skipped, and claims outputs only when asked to."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import auto_mapper
from gremlin.auto_mapper import AutoMapper, AutoMapperOptions, _ranges

_NXT = {"slug": "nxt", "name": "NXT", "claim": {"buttons": list(range(1, 61))}}


def _vjoy3() -> dict:
    return {
        "slug": "vjoy_3",
        "name": "vJoy 3",
        "vjoyId": 3,
        "claim": {"buttons": list(range(1, 57))},
    }


@pytest.fixture
def mapper() -> Iterator[tuple[AutoMapper, list, list]]:
    created: list = []
    merged: list = []
    dest = _vjoy3()

    def merge(target: dict, claim: dict) -> dict:
        merged.append(claim)
        target["claim"] = {"buttons": sorted(set(claim["buttons"]))}
        return target["claim"]

    profile = SimpleNamespace(
        get_input_item=lambda *a, **k: SimpleNamespace(action_sequences=[])
    )
    m = AutoMapper(profile)
    limits = {"axes": set(), "buttons": set(range(1, 59)), "hats": set()}
    with (
        mock.patch.object(auto_mapper.auto_map, "input_modules", return_value=[_NXT]),
        mock.patch.object(auto_mapper.auto_map, "output_modules", return_value=[dest]),
        mock.patch.object(auto_mapper.auto_map, "merge_claim_into_output", merge),
        mock.patch.object(AutoMapper, "_vjoy_limits", return_value=limits),
        mock.patch.object(AutoMapper, "_get_used_vjoy_inputs", return_value=[]),
        mock.patch.object(AutoMapper, "_source_uuid", return_value=uuid.uuid4()),
        mock.patch.object(
            AutoMapper,
            "_create_new_mapping",
            lambda self, item, target: (
                created.append(target),
                self._created_mappings.append(target),
            ),
        ),
    ):
        yield m, created, merged


def test_maps_only_to_claimed_outputs_and_reports_the_rest(
    mapper: tuple[AutoMapper, list, list],
) -> None:
    m, created, merged = mapper
    report = m.generate_module_mappings(["nxt"], ["vjoy_3"], AutoMapperOptions())
    assert [t.input_id for t in created] == list(range(1, 57))
    assert merged == []  # nothing claimed behind your back
    assert "Skipped vJoy 3 buttons 57-58: not claimed by the output module." in report
    assert "Skipped vJoy 3 buttons 59-60: not on the vJoy device." in report


def test_claim_option_claims_first(mapper: tuple[AutoMapper, list, list]) -> None:
    m, created, merged = mapper
    options = AutoMapperOptions(claim_outputs=True)
    report = m.generate_module_mappings(["nxt"], ["vjoy_3"], options)
    assert len(merged) == 1
    assert [t.input_id for t in created] == list(range(1, 59))
    assert "not claimed" not in report
    assert "Skipped vJoy 3 buttons 59-60: not on the vJoy device." in report


def test_ranges() -> None:
    assert _ranges([57, 58, 59, 1, 3, 126]) == "1, 3, 57-59, 126"
    assert _ranges([]) == ""


def test_input_modules_left_without_an_output_are_named(
    mapper: tuple[AutoMapper, list, list],
) -> None:
    m, _created, _merged = mapper
    second = {"slug": "evo", "name": "EVO", "claim": {"buttons": [1]}}
    with mock.patch.object(
        auto_mapper.auto_map, "input_modules", return_value=[_NXT, second]
    ):
        report = m.generate_module_mappings(
            ["nxt", "evo"], ["vjoy_3"], AutoMapperOptions()
        )
    assert "No output module left for EVO" in report
