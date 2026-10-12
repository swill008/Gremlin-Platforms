# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The vJoy Viewer lists OSC's and the Logical Device's Map to vJoy wires
(03 S122): they need no input-module claim (03 S90b), so the source-claim
filter must not drop them. Their lights follow the vJoy output module and
their own input events."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest import mock

import pytest

from gremlin import run_scope, shared_state
from gremlin.event_handler import Event, EventListener
from gremlin.modules import ids, output, store
from gremlin.modules import runtime as module_runtime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import module_pairing, pair_live
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    _app,
    folder,
    map_button,
    setup_cards,
    vjoy_doc,
    write_module,
)

_SOURCES = [
    pytest.param(ids.OSC, "OSC Button 1", id="osc"),
    pytest.param(ids.LOGICAL_DEVICE, "Button 1", id="logical-device"),
]


class _Button:
    """A vJoy button like the driver's: the write sets what a read sees."""

    def __init__(self) -> None:
        self._is_pressed = False

    @property
    def is_pressed(self) -> bool:
        return self._is_pressed

    @is_pressed.setter
    def is_pressed(self, value: bool) -> None:
        self._is_pressed = bool(value)


class _FakeVJoy:
    """A held vJoy device with 64 buttons."""

    def __init__(self) -> None:
        self._buttons = {i: _Button() for i in range(1, 65)}

    def is_axis_valid(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> bool:
        return False

    def is_button_valid(self, index: int) -> bool:
        return index in self._buttons

    def is_hat_valid(self, index: int) -> bool:
        return False

    def button(self, index: int) -> _Button:
        return self._buttons[index]


def _cards(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    source: uuid.UUID,
) -> Profile:
    setup_cards(folder)
    claim = {"buttons": [30], "axes": [], "hats": []}
    write_module(folder, "vjoy_1", vjoy_doc(claim=claim))
    if source == ids.LOGICAL_DEVICE:
        write_module(
            folder,
            "logical_device",
            {
                "kind": "control.hardware",
                "device": "Logical Device",
                "direction": "source",
                "boundName": "Logical Device",
                "boundGuidLocal": str(ids.LOGICAL_DEVICE).upper(),
                "claim": {"buttons": [], "axes": [], "hats": []},
            },
        )
    if source == ids.OSC:
        # The OSC input itself (the conftest puts OSC's rows back after).
        from gremlin.osc import OscDevice

        osc = OscDevice()
        if osc.rows.by_number(InputType.JoystickButton, 1) is None:
            osc.rows.create(InputType.JoystickButton, "/osc/button/1", input_id=1)
    output.refresh()
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    map_button(profile, source, 1, 30)
    return profile


def _rows(model) -> list[dict]:  # noqa: ANN001
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    return [
        {name: model.data(model.index(r, 0), role) for role, name in names.items()}
        for r in range(model.rowCount())
    ]


@pytest.mark.parametrize(("source", "label"), _SOURCES)
def test_the_viewer_lists_the_wire(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    source: uuid.UUID,
    label: str,
) -> None:
    _cards(folder, monkeypatch, source)
    devices = _rows(module_pairing.ModulePairDeviceModel())
    card = next(
        (row for row in devices if uuid.UUID(str(row["guid"]).strip("{}")) == source),
        None,
    )
    assert card is not None, devices
    buttons = module_pairing.ModulePairButtonModel()
    buttons.guid = card["guid"]
    buttons.deviceName = card["deviceName"]
    rows = _rows(buttons)
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["identifier"] == 1
    assert row["vjoyInput"] == 30
    assert row["destClaimed"] is True
    assert row["label"] == label


def test_an_osc_input_shows_its_name(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _cards(folder, monkeypatch, ids.OSC)
    from gremlin.osc import OscDevice

    uid = OscDevice().rows.uid_of(InputType.JoystickButton, 1)
    assert uid
    write_module(
        folder,
        "osc",
        {
            "kind": "control.hardware",
            "device": "OSC",
            "direction": "source",
            "claim": {
                "buttons": [],
                "axes": [],
                "hats": [],
                "friendly": {f"osc:{uid}": "Gear"},
            },
        },
    )
    rows = module_pairing._module_pair_rows(
        str(ids.OSC), "OSC", InputType.JoystickButton
    )
    assert [row["label"] for row in rows] == ["Gear"]


@pytest.mark.parametrize(("source", "label"), _SOURCES)
def test_the_lights_follow_the_input_and_the_output(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    source: uuid.UUID,
    label: str,
) -> None:
    _cards(folder, monkeypatch, source)
    dev = _FakeVJoy()
    vjoy_guid = module_pairing.pairing._vjoy_guid(1)
    assert vjoy_guid
    run_scope.begin()
    try:
        with (
            mock.patch.object(output, "_open_vjoy", return_value=dev),
            mock.patch.object(output, "_opened_vjoy", return_value=dev),
            mock.patch.object(pair_live, "_gremlin_running", return_value=True),
        ):
            live = pair_live.PairLiveThrottle()
            live.guid = str(source)  # pyright: ignore[reportAttributeAccessIssue]
            # The real output module write (claimed vJoy 1 Button 30).
            assert output.write_vjoy(1, "button", 30, True)
            live._poll_vjoy()
            assert live.vjoyButtonValue(vjoy_guid, 30) == 1.0
            # The input half: its own event through the input module feed.
            assert guid_passes(source)
            EventListener().joystick_event.emit(
                Event(InputType.JoystickButton, 1, source, "Default", is_pressed=True)
            )
            assert live.buttonValue(1) == 1.0
    finally:
        run_scope.stop()
        run_scope._reset_for_tests()


def guid_passes(source: uuid.UUID) -> bool:
    return module_runtime.guid_key(source) in module_runtime.always_forwarded()


@pytest.mark.parametrize(("source", "label"), _SOURCES)
def test_the_card_shows_without_a_module_file(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    source: uuid.UUID,
    label: str,
) -> None:
    """Gap 33 (reopened): OSC and the Logical Device need no module file
    (03 S90b), so a Map to vJoy from either shows its card without one."""
    write_module(folder, "vjoy_1", vjoy_doc(claim={"buttons": [30]}))
    if source == ids.OSC:
        from gremlin.osc import OscDevice

        osc = OscDevice()
        if osc.rows.by_number(InputType.JoystickButton, 1) is None:
            osc.rows.create(InputType.JoystickButton, "/osc/button/1", input_id=1)
    output.refresh()
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    map_button(profile, source, 1, 30)
    name = "OSC" if source == ids.OSC else "Logical Device"
    assert not store.exists(name, str(source))
    devices = _rows(module_pairing.ModulePairDeviceModel())
    card = next(
        (row for row in devices if uuid.UUID(str(row["guid"]).strip("{}")) == source),
        None,
    )
    assert card is not None, devices
    assert card["name"] in ("OSC", "Logical Device"), card
    buttons = module_pairing.ModulePairButtonModel()
    buttons.guid = card["guid"]
    buttons.deviceName = card["deviceName"]
    assert [row["label"] for row in _rows(buttons)] == [label]


def test_a_new_map_to_vjoy_is_polled(
    folder: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The live card polls a vJoy device first wired after it opened: the ids
    follow the bindings notice (03 S122a; D-01-OWNER-NOTICES)."""
    from gremlin.signal import signal

    write_module(folder, "vjoy_1", vjoy_doc(claim={"buttons": [30]}))
    output.refresh()
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    live = pair_live.PairLiveThrottle()
    live.guid = str(ids.LOGICAL_DEVICE)  # pyright: ignore[reportAttributeAccessIssue]
    assert live._vjoy_ids == {}
    map_button(profile, ids.LOGICAL_DEVICE, 1, 30)
    signal.bindingsChanged.emit()
    assert 1 in live._vjoy_ids.values()
    assert live._vjoy_poll.isActive()
