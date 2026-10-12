# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Copy layout from: other devices' saved device map layouts."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib

import pytest

from gremlin.modules import store
from gremlin.ui import hardware_profile
from test.unit._device_folders import put_module


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    for device, nodes in (
        ("Stick R", [{"id": "b1"}]),
        ("Stick L", [{"id": "b2"}]),
        ("Pedals", []),
    ):
        put_module(tmp_path, device, {"device": device, "nodes": nodes})
    put_module(tmp_path, "Broken", "{")
    return hardware_profile.HardwareProfile()


def test_lists_other_devices_with_a_layout(
    profile: hardware_profile.HardwareProfile,
) -> None:
    rows = profile.savedLayouts("Stick L")
    assert rows == [{"name": "Stick R", "slug": "Stick R"}]
    names = [row["name"] for row in profile.savedLayouts("")]
    assert names == ["Stick L", "Stick R"]


def test_reads_a_layout_by_folder(profile: hardware_profile.HardwareProfile) -> None:
    assert json.loads(profile.layoutNodes("Stick R")) == [{"id": "b1"}]
    assert profile.layoutNodes("Pedals") == ""
    assert profile.layoutNodes("missing") == ""
    assert profile.layoutNodes("../Stick R") == ""
    assert profile.layoutNodes("cache") == ""
    assert profile.layoutNodes("") == ""
