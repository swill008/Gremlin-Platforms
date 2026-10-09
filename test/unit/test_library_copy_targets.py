# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Copy goes to external devices only (03 S90b, 10 S22): a vJoy device and
the Xbox pad are refused as targets by their id, with the plugged-in
message users saw before. The live device list is stood in for."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from gremlin import device_initialization, library_copy
from gremlin.modules import hardware, ids

VJOY = "{CCCC0000-1111-2222-3333-444455556666}"
STICK = "{DDDD0000-1111-2222-3333-444455556666}"


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        device_initialization,
        "physical_devices",
        lambda: [
            SimpleNamespace(name="Real Stick", device_guid=STICK, is_virtual=False)
        ],
    )
    monkeypatch.setattr(
        device_initialization,
        "vjoy_devices",
        lambda: [
            SimpleNamespace(name="vJoy Device", device_guid=VJOY, is_virtual=True)
        ],
    )
    # Every id is live in the driver's list: only the class can refuse.
    monkeypatch.setattr(hardware, "device_connected", lambda guid: True)
    monkeypatch.setattr(
        library_copy,
        "_find_setup",
        lambda key: ({"name": "Old Stick", "guid": STICK}, {"key": key}),
    )


@pytest.mark.parametrize(
    ("name", "guid"),
    [("vJoy Device", VJOY), ("Xbox 360 Controller", str(ids.XBOX))],
)
def test_vjoy_and_xbox_are_refused_as_copy_targets(
    live: None, name: str, guid: str
) -> None:
    assert not library_copy._connected(guid)
    plan = library_copy.plan_copy("setup-1", name, guid, ["bindings"], [], [])
    assert not plan["ok"]
    assert plan["error"] == (
        f"{name} isn't plugged in. A setup can only be copied to a stick "
        "plugged in now."
    )


def test_an_external_stick_by_its_id_can_be_a_copy_target(live: None) -> None:
    assert library_copy._connected(STICK)


def test_swap_calls_a_vjoy_device_vjoy(live: None) -> None:
    from gremlin import library_swap

    answer = library_swap._refusal(("vJoy Device", VJOY), ("Real Stick", STICK))
    assert answer == "Swap can't be used with vJoy."
