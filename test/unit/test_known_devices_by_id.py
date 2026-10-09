# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Pack's device list is one row per device by its Windows id
(08 S106a): identical sticks are two rows, named as on Home."""

from __future__ import annotations

import json
import types
import uuid
from collections.abc import Iterator

import pytest

from gremlin import device_aliases, device_initialization, shared_state
from gremlin.config import Configuration
from gremlin.modules import store
from gremlin.profile import DeviceInfo, Profile
from gremlin.util import modules_dir

NAME = "VKBsim Gladiator EVO"
FIRST = uuid.UUID("11111111-2222-3333-4444-555555555551")
SECOND = uuid.UUID("11111111-2222-3333-4444-555555555552")
SINGLE = uuid.UUID("11111111-2222-3333-4444-555555555553")


def _dev(name: str, uid: uuid.UUID) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        name=name, device_guid=types.SimpleNamespace(uuid=uid), is_virtual=False
    )


@pytest.fixture
def setup(monkeypatch: pytest.MonkeyPatch) -> Iterator[Profile]:
    twins = Configuration().value(*device_initialization.TWIN_SETTING)
    Configuration().set(
        *device_initialization.TWIN_SETTING, {str(SECOND).upper(): f"{NAME} (2)"}
    )
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    monkeypatch.setattr(store, "live_devices", lambda: [])
    yield profile
    Configuration().set(*device_initialization.TWIN_SETTING, twins)
    for uid in (FIRST, SECOND, SINGLE):
        device_aliases.set_alias(str(uid), "")


def _rows() -> list[dict]:
    return [
        row
        for row in store.known_devices()
        if row["name"].startswith(("VKBsim", "Lone", "Files"))
    ]


def test_two_identical_sticks_in_the_profile_are_two_rows(setup: Profile) -> None:
    setup.device_database.devices[FIRST] = DeviceInfo(FIRST, NAME)
    setup.device_database.devices[SECOND] = DeviceInfo(SECOND, NAME)
    rows = _rows()
    assert [(row["guid"], row["label"]) for row in rows] == [
        (str(FIRST), NAME),
        (str(SECOND), f"{NAME} (2)"),
    ]


def test_plugged_in_twins_are_labelled_as_on_home(
    setup: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        store, "live_devices", lambda: [_dev(NAME, FIRST), _dev(f"{NAME} (2)", SECOND)]
    )
    # The profile knows both by the driver's name: still two rows.
    setup.device_database.devices[FIRST] = DeviceInfo(FIRST, NAME)
    setup.device_database.devices[SECOND] = DeviceInfo(SECOND, NAME)
    rows = _rows()
    assert [(row["guid"], row["label"], row["connected"]) for row in rows] == [
        (str(FIRST), NAME, True),
        (str(SECOND), f"{NAME} (2)", True),
    ]


def test_an_alias_is_the_label(setup: Profile) -> None:
    setup.device_database.devices[SECOND] = DeviceInfo(SECOND, NAME)
    device_aliases.set_alias(str(SECOND), "Left Hand")
    (row,) = _rows()
    assert (row["name"], row["label"]) == (NAME, "Left Hand")


def test_a_one_of_a_kind_stick_has_its_plain_name(setup: Profile) -> None:
    setup.device_database.devices[SINGLE] = DeviceInfo(SINGLE, "Lone  Stick")
    (row,) = _rows()
    assert (row["name"], row["guid"], row["label"]) == (
        "Lone Stick",
        str(SINGLE),
        "Lone Stick",
    )


def test_a_file_only_device_is_one_row_by_name(setup: Profile) -> None:
    path = modules_dir() / "files_only_stick.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"kind": "control.hardware", "device": "Files Only Stick"}),
        encoding="utf-8",
    )
    try:
        rows = _rows()
    finally:
        path.unlink(missing_ok=True)
    assert [(r["name"], r["guid"], r["label"], r["hasFile"]) for r in rows] == [
        ("Files Only Stick", "", "Files Only Stick", True)
    ]
