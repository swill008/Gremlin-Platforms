# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The vJoy Viewer's device list shows the user's name for a device, as the
Home cards do, and follows the device names notice (03 S122a;
D-01-OWNER-NOTICES 3a). Both failed before: the title was the module file's
"device" field and the list never heard deviceNamesChanged."""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin.signal import signal

_ONE = "11111111-2222-3333-4444-000000000001"
_TWO = "11111111-2222-3333-4444-000000000002"


@pytest.fixture(scope="module", autouse=True)
def terminate_event_listener() -> Iterator[None]:
    yield
    import gremlin.event_handler

    gremlin.event_handler.EventListener().terminate()


@pytest.fixture(autouse=True)
def names_kept() -> Iterator[None]:
    """The user's device names are put back after each test."""
    from gremlin import device_aliases

    device_aliases._ensure()
    before = dict(device_aliases._load())
    yield
    device_aliases._save(before)


@pytest.fixture
def twins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two twin sticks, each with its own module file and a vJoy wire."""
    from gremlin import device_initialization
    from gremlin.ui import module_pairing

    devices = [
        SimpleNamespace(name="Twin Stick", device_guid=_ONE),
        SimpleNamespace(name="Twin Stick", device_guid=_TWO),
    ]
    titles = {_ONE: "Twin Stick", _TWO: "Twin Stick (2)"}
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: devices)
    monkeypatch.setattr(device_initialization, "input_devices", lambda: [])
    monkeypatch.setattr(module_pairing.store, "exists", lambda name, guid="": True)
    monkeypatch.setattr(
        module_pairing.store,
        "read",
        lambda name, guid="": {"device": titles.get(guid, name)},
    )
    monkeypatch.setattr(module_pairing.pairing, "_items_for_guid", lambda guid: [guid])
    monkeypatch.setattr(module_pairing, "_vjoy_maps_only", lambda item: [(1, 1, 1)])
    empty = {"buttons": [], "axes": [], "hats": []}
    monkeypatch.setattr(
        module_pairing,
        "_dest_for_vjoy",
        lambda vid: {"name": f"vJoy {vid}", "claim": empty},
    )


def _rows(model: object) -> dict[str, tuple[str, str]]:
    return {r["guid"]: (r["name"], r["deviceName"]) for r in model._rows}  # type: ignore[attr-defined]


def test_a_renamed_twin_shows_its_new_name(qtbot: object, twins: None) -> None:
    from gremlin import device_aliases
    from gremlin.ui.module_pairing import ModulePairDeviceModel

    device_aliases.set_alias(_TWO, "Right Twin")
    model = ModulePairDeviceModel()
    try:
        rows = _rows(model)
        assert rows[_TWO] == ("Right Twin", "Twin Stick")
        assert rows[_ONE] == ("Twin Stick", "Twin Stick")
    finally:
        model.deleteLater()


def test_a_rename_reaches_an_open_list(qtbot: object, twins: None) -> None:
    from gremlin import device_aliases
    from gremlin.ui.module_pairing import ModulePairDeviceModel

    model = ModulePairDeviceModel()
    try:
        assert _rows(model)[_TWO][0] == "Twin Stick (2)"
        device_aliases.set_alias(_TWO, "Right Twin")
        signal.deviceNamesChanged.emit()
        qtbot.wait(20)  # type: ignore[attr-defined]
        assert _rows(model)[_TWO] == ("Right Twin", "Twin Stick")
    finally:
        model.deleteLater()


def test_a_built_in_uses_its_home_card_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # Home stores the Logical Device's name under "logical", not its id.
    from gremlin import device_aliases
    from gremlin.modules import ids
    from gremlin.ui import module_pairing

    monkeypatch.setattr(
        module_pairing.store, "read", lambda name, guid="": {"device": name}
    )
    device_aliases.set_alias("logical", "My Logic")
    assert (
        module_pairing._shown_title("Logical Device", str(ids.LOGICAL_DEVICE))
        == "My Logic"
    )
