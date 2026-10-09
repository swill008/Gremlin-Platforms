# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Plugged in is decided by the device's id, never its name (03 S90a):
hardware.plugged_in, and Delete Device's text (delete_preview) and result
(delete_device) on Home."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
import uuid
from collections.abc import Callable, Iterator

import pytest

import dill
from gremlin import device_initialization, shared_state
from gremlin import device_library as library
from gremlin.modules import hardware, ids, registry, store
from gremlin.profile import Profile
from gremlin.ui import hardware_profile
from test import fake_hardware

_SPACED = "VKBSim NXT  SEM THQ FSM.GA"
_VKB = uuid.UUID("0a1b2c3d-0000-1111-2222-333344445555")
_TWIN_IN = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")
_TWIN_OUT = uuid.UUID("bbbbbbbb-1111-2222-3333-444444444444")


def _summary(name: str, guid: uuid.UUID) -> dill._DeviceSummary:
    raw = fake_hardware.raw_device(is_virtual=False)
    raw.name = name.encode("utf-8")
    raw.device_guid = dill.GUID.from_uuid(guid).ctypes
    return raw


@pytest.fixture
def live() -> Iterator[Callable[[str, uuid.UUID], None]]:
    """The live device list: what the driver answers and what the program's
    device list holds agree, so the old name check saw the same devices."""
    fake = dill.DILL._dll
    before = list(fake.devices)
    known = dict(device_initialization._joystick_devices)

    def plug(name: str, guid: uuid.UUID) -> None:
        raw = _summary(name, guid)
        fake.devices.append(raw)
        summary = dill.DeviceSummary(raw)
        device_initialization._joystick_devices[summary.device_guid.uuid] = summary

    yield plug
    fake.devices[:] = before
    device_initialization._joystick_devices.clear()
    device_initialization._joystick_devices.update(known)


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    maps = tmp_path / "modules"
    maps.mkdir()
    monkeypatch.setattr(store, "folder", lambda: maps)
    monkeypatch.setattr(store, "users_of", lambda slug: set())
    monkeypatch.setattr(store, "bindings", lambda: {})
    monkeypatch.setattr(store, "set_bindings", lambda data: None)
    monkeypatch.setattr(registry, "guid_for_name", lambda name: "")
    monkeypatch.setattr(hardware_profile, "_profile_running", lambda: False)
    monkeypatch.setattr(
        library, "autosave",
        lambda *a: {"ok": True, "error": "", "warnings": [], "notes": []},
    )
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    return maps


def _preview(name: str, guid: object) -> dict:
    return json.loads(hardware_profile.delete_preview(name, str(guid)))


def _delete(name: str, guid: object) -> dict:
    result = json.loads(hardware_profile.delete_device(name, str(guid)))
    assert result["ok"], result
    return result


# --- hardware.plugged_in -----------------------------------------------------


def test_a_plugged_in_stick_is_found_by_its_id_whatever_its_name(
    live: Callable,
) -> None:
    live(_SPACED, _VKB)
    assert hardware.plugged_in(str(_VKB), _SPACED)
    assert hardware.plugged_in(str(_VKB), "VKBSim NXT SEM THQ FSM.GA")
    assert hardware.plugged_in(str(_VKB), "My Left Stick")
    assert hardware.plugged_in(str(_VKB), "")


def test_no_id_is_not_plugged_in_even_with_a_plugged_in_name(live: Callable) -> None:
    live(_SPACED, _VKB)
    assert not hardware.plugged_in("", _SPACED)
    assert not hardware.plugged_in(None, "pJoy Pro")
    assert not hardware.plugged_in("not an id", _SPACED)


def test_of_two_identical_sticks_only_the_plugged_in_one_is(live: Callable) -> None:
    live("Twin Stick", _TWIN_IN)
    assert hardware.plugged_in(str(_TWIN_IN), "Twin Stick")
    assert not hardware.plugged_in(str(_TWIN_OUT), "Twin Stick")


@pytest.mark.parametrize(
    ("guid", "name"),
    [
        (ids.KEYBOARD, "Keyboard"),
        (ids.OSC, "OSC"),
        (ids.LOGICAL_DEVICE, "Logical Device"),
        (ids.XBOX, "Xbox 360 Controller"),
        ("", "vJoy 1"),
        ("", "Xbox 360 Controller"),
        (uuid.uuid4(), "vJoy 2"),
    ],
)
def test_built_ins_are_always_there(guid: object, name: str) -> None:
    assert hardware.plugged_in(str(guid) if guid else "", name)


def test_a_stick_named_keyboard_is_a_stick() -> None:
    assert not hardware.plugged_in(str(uuid.uuid4()), "Keyboard")


# --- Delete Device: its text and its result -----------------------------------


def test_delete_text_a_stick_with_a_double_spaced_name_is_plugged_in(
    live: Callable, modules: pathlib.Path
) -> None:
    # The user's stick: no input yet, so Home passes the card's own name.
    live(_SPACED, _VKB)
    assert _preview(_SPACED, _VKB)["listed"] is True


def test_delete_text_a_renamed_stick_is_plugged_in(
    live: Callable, modules: pathlib.Path
) -> None:
    live(_SPACED, _VKB)
    assert _preview("Left Throttle", _VKB)["listed"] is True


def test_delete_text_the_unplugged_twin_is_not_plugged_in(
    live: Callable, modules: pathlib.Path
) -> None:
    live("Twin Stick", _TWIN_IN)
    assert _preview("Twin Stick", _TWIN_IN)["listed"] is True
    assert _preview("Twin Stick", _TWIN_OUT)["listed"] is False


def test_delete_text_a_card_with_no_id_is_not_plugged_in(
    live: Callable, modules: pathlib.Path
) -> None:
    live("Twin Stick", _TWIN_IN)
    assert _preview("Twin Stick", "")["listed"] is False


def test_delete_result_keeps_a_plugged_in_sticks_card_by_its_id(
    live: Callable, modules: pathlib.Path
) -> None:
    live(_SPACED, _VKB)
    result = _delete(_SPACED, _VKB)
    assert result["listed"] is True and result["stub"] is True


def test_delete_result_the_unplugged_twins_card_goes(
    live: Callable, modules: pathlib.Path
) -> None:
    live("Twin Stick", _TWIN_IN)
    result = _delete("Twin Stick", _TWIN_OUT)
    assert result["listed"] is False and result["stub"] is False


def test_delete_result_a_renamed_plugged_in_stick_keeps_its_card(
    live: Callable, modules: pathlib.Path
) -> None:
    live(_SPACED, _VKB)
    assert _delete("Left Throttle", _VKB)["listed"] is True


def test_built_in_cards_without_an_id_are_there() -> None:
    # Module Setup and the Button Map open Keyboard / OSC / Logical Device
    # with no id; a stick with no id is still not plugged in.
    from gremlin.modules import hardware

    for name in ("Keyboard", "OSC", "Logical  Device", "keyboard"):
        assert hardware.plugged_in("", name) is True
    assert hardware.plugged_in("", "VKBsim Gladiator EVO R") is False
