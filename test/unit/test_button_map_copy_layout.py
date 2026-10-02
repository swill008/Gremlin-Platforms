# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Copy layout from: other devices' saved Button Map layouts."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib

import pytest

from gremlin.ui import hardware_profile


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(hardware_profile, "_maps_dir", lambda: tmp_path)
    monkeypatch.setattr(
        hardware_profile,
        "resolve_module_slug",
        lambda name, guid="": name.lower().replace(" ", "_"),
    )
    for slug, device, nodes in (
        ("stick_r", "Stick R", [{"id": "b1"}]),
        ("stick_l", "Stick L", [{"id": "b2"}]),
        ("pedals", "Pedals", []),
    ):
        doc = {"device": device, "nodes": nodes}
        (tmp_path / f"{slug}.json").write_text(json.dumps(doc), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    return hardware_profile.HardwareProfile()


def test_lists_other_devices_with_a_layout(
    profile: hardware_profile.HardwareProfile,
) -> None:
    rows = profile.savedLayouts("Stick L")
    assert rows == [{"name": "Stick R", "slug": "stick_r"}]
    names = [row["name"] for row in profile.savedLayouts("")]
    assert names == ["Stick L", "Stick R"]


def test_reads_a_layout_by_slug(profile: hardware_profile.HardwareProfile) -> None:
    assert json.loads(profile.layoutNodes("stick_r")) == [{"id": "b1"}]
    assert profile.layoutNodes("pedals") == ""
    assert profile.layoutNodes("missing") == ""
    assert profile.layoutNodes("../stick_r") == ""
    assert profile.layoutNodes("") == ""
