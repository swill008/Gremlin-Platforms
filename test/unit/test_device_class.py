# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every device is external, an internal input or an internal output, decided
in one place (03 S90b, D-03-DEVICE-CLASSES), and what it can do comes from
one table there. Each CAN answer is checked against a copy of the rule the
program used before the table (the "today" oracles below), over every kind of
device; copy, swap, calibrate and a Device Library device row are for
external devices only (S90b, user 2026-10-09)."""

from __future__ import annotations

import sys

sys.path.append(".")

import uuid
from pathlib import Path

import pytest

from gremlin.modules import device_class as dc
from gremlin.modules import hardware, ids, registry
from gremlin.modules.device_class import DeviceClass
from gremlin.modules.ids import guid_key, stored_guid_key
from gremlin.modules.registry import is_output_name, plain_slug

STICK = "{6C3D1E20-1111-2222-3333-444455556666}"
STICK_KB = "{11111111-2222-3333-4444-555555555555}"  # a stick named "Keyboard"
VJOY_ID = "{BBBBBBBB-0000-1111-2222-333344445555}"  # the driver's id for vJoy 1
UNPLUGGED = "{CCCCCCCC-0000-1111-2222-333344445555}"
LIVE = {guid_key(STICK), guid_key(STICK_KB), guid_key(VJOY_ID)}

# (guid, name): every kind of device the program sees.
DEVICES: list[tuple[object, str]] = [
    (ids.KEYBOARD, "Keyboard"),
    (ids.OSC, "OSC"),
    (ids.LOGICAL_DEVICE, "Logical Device"),
    (ids.XBOX, "Xbox 360 Controller"),
    (str(ids.KEYBOARD).upper(), ""),
    ("{" + str(ids.OSC).upper() + "}", "osc"),
    (None, "Keyboard"),
    ("", "OSC"),
    (None, "logical  device"),
    (None, " KEYBOARD "),
    (None, "logical_device"),
    (None, "vJoy 1"),
    (None, "vJoy Device"),
    (VJOY_ID, "vJoy 1"),
    (VJOY_ID, "vJoy  2"),
    (None, "Xbox 360 Controller"),
    (None, "xbox"),
    (None, "Xbox pad 2"),
    (STICK, "VKBSim NXT  SEM THQ FSM.GA"),
    (STICK_KB, "Keyboard"),
    (STICK_KB, "OSC"),
    (STICK, "Controller (XBOX 360 For Windows)"),
    (UNPLUGGED, "Stick B"),
    (None, "Stick B"),
    (None, ""),
    (STICK, ""),
]


def _ids(devices: list) -> list[str]:
    return [f"{g!s:.12}|{n}" for g, n in devices]


# The rules as the program had them before the table.

def _today_plugged_in(guid: object, name: str) -> bool:
    if is_output_name(name):
        return True
    key = guid_key(guid)
    if not key:
        return " ".join(str(name or "").split()).casefold() in {
            "keyboard", "osc", "logical device"}
    built_in = (ids.KEYBOARD, ids.OSC, ids.LOGICAL_DEVICE, ids.XBOX)
    if key in {guid_key(g) for g in built_in}:
        return True
    return key in LIVE


def _today_is_built_in_guid(guid: object) -> bool:
    want = stored_guid_key(guid)
    return bool(want) and want in (
        stored_guid_key(str(ids.KEYBOARD)), stored_guid_key(str(ids.OSC)),
        stored_guid_key(str(ids.LOGICAL_DEVICE)))


def _today_swap_refused(guid: object) -> bool:
    try:
        ident = uuid.UUID(str(guid))
    except ValueError:
        return False
    return ident in {ids.KEYBOARD, ids.LOGICAL_DEVICE, ids.OSC, ids.XBOX}


def _today_is_built_in_input(module: registry.Module) -> bool:
    bound = guid_key(module.bound_guid)
    if bound:
        return bound in (guid_key(ids.KEYBOARD), guid_key(ids.OSC),
                         guid_key(ids.LOGICAL_DEVICE))
    # 2026-10-09 D-04-LD-FILE: the Logical Device is a Library built-in too.
    return module.slug in ("keyboard", "osc", "logical_device") or plain_slug(
        module.name) in ("keyboard", "osc", "logical_device")


def _today_forwarded(guid: object) -> bool:
    return guid_key(guid) in {guid_key(ids.OSC), guid_key(ids.LOGICAL_DEVICE)}


def _today_calibration_skips(slug: str) -> bool:
    return slug in {"keyboard", "osc"}


def _module(slug: str, name: str, guid: str) -> registry.Module:
    return registry.Module(
        slug=slug, path=Path(f"{slug}.json"), doc={}, name=name,
        bound_guid=guid, bound_name=name,
        direction=registry.module_direction({}, slug, name), claim={})


MODULES = [
    _module("keyboard", "Keyboard", "{" + str(ids.KEYBOARD).upper() + "}"),
    _module("osc", "OSC", "{" + str(ids.OSC).upper() + "}"),
    _module("keys_unbound", "Keyboard", ""),
    _module("osc", "", ""),
    _module("keyboard_stick", "Keyboard", STICK_KB),
    _module("stick_a", "Stick A", STICK),
    _module("logical_device", "Logical Device", ""),
    _module("vjoy_1", "vJoy 1", ""),
    _module("xbox", "Xbox 360 Controller", ""),
    _module("keyboard", "Keyboard!", ""),
]


# --- the class of each kind of device --------------------------------------

@pytest.mark.parametrize(
    ("guid", "name", "want"),
    [
        (ids.KEYBOARD, "", DeviceClass.INTERNAL_INPUT),
        (ids.OSC, "", DeviceClass.INTERNAL_INPUT),
        (ids.LOGICAL_DEVICE, "", DeviceClass.INTERNAL_INPUT),
        (ids.XBOX, "", DeviceClass.INTERNAL_OUTPUT),
        (None, "Keyboard", DeviceClass.INTERNAL_INPUT),
        (None, "  logical   DEVICE ", DeviceClass.INTERNAL_INPUT),
        (None, "vJoy 3", DeviceClass.INTERNAL_OUTPUT),
        (VJOY_ID, "vJoy 1", DeviceClass.INTERNAL_OUTPUT),
        (None, "Xbox 360 Controller", DeviceClass.INTERNAL_OUTPUT),
        # A stick named "Keyboard" with its own id is a stick.
        (STICK_KB, "Keyboard", DeviceClass.EXTERNAL),
        (STICK, "Controller (XBOX 360 For Windows)", DeviceClass.EXTERNAL),
        (STICK, "VKBSim NXT  SEM THQ FSM.GA", DeviceClass.EXTERNAL),
        (None, "Stick B", DeviceClass.EXTERNAL),
        (None, "", DeviceClass.EXTERNAL),
    ],
)
def test_device_class(guid: object, name: str, want: DeviceClass) -> None:
    assert dc.device_class(guid, name) is want
    assert dc.is_internal(guid, name) is (want is not DeviceClass.EXTERNAL)
    assert dc.is_internal_input(guid, name) is (want is DeviceClass.INTERNAL_INPUT)
    assert dc.is_internal_output(guid, name) is (want is DeviceClass.INTERNAL_OUTPUT)


def test_kinds_and_names() -> None:
    assert dc.device_kind(None, "vJoy 2") == "vjoy"
    assert dc.device_kind(ids.XBOX) == "xbox"
    assert dc.device_kind(None, "Xbox pad 2") == "xbox"
    assert dc.device_kind(None, "Logical Device") == "logical_device"
    assert dc.device_kind(STICK_KB, "Keyboard") == ""
    assert dc.display_name("osc") == "OSC"
    assert dc.guid_of_kind("keyboard") == ids.KEYBOARD
    assert dc.guid_of_kind("vjoy") is None


def test_module_class() -> None:
    by = {(m.slug, m.name, m.bound_guid): m for m in MODULES}
    assert dc.device_class(module=by["keyboard", "Keyboard", MODULES[0].bound_guid]) \
        is DeviceClass.INTERNAL_INPUT
    assert dc.device_class(module=by["keyboard_stick", "Keyboard", STICK_KB]) \
        is DeviceClass.EXTERNAL
    assert dc.device_class(module=by["logical_device", "Logical Device", ""]) \
        is DeviceClass.INTERNAL_INPUT
    assert dc.device_class(module=by["vjoy_1", "vJoy 1", ""]) \
        is DeviceClass.INTERNAL_OUTPUT


# --- CAN answers equal today's behaviour ------------------------------------

@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hardware, "device_connected", lambda g: guid_key(g) in LIVE)


@pytest.mark.parametrize(("guid", "name"), DEVICES, ids=_ids(DEVICES))
def test_plugged_in_unchanged(live: None, guid: object, name: str) -> None:
    assert hardware.plugged_in(guid, name) is _today_plugged_in(guid, name)


@pytest.mark.parametrize(("guid", "name"), DEVICES, ids=_ids(DEVICES))
def test_by_id_rules_unchanged(guid: object, name: str) -> None:
    # Copy / Library built-in rows / Swap / Run forwarding went by id only.
    if not guid:
        return
    assert dc.can("copy", guid) is not dc.is_internal(guid)
    assert dc.can("library_builtin", guid) is _today_is_built_in_guid(guid)
    assert dc.can("swap", guid) is not dc.is_internal(guid)
    # Swap by id refuses what it refused before (callers pass the id only).
    assert dc.can("swap", guid) is not _today_swap_refused(guid)
    assert dc.can("no_claim_needed", guid) is _today_forwarded(guid)


@pytest.mark.parametrize("slug", ["keyboard", "osc", "logical_device", "vjoy_1",
                                  "xbox", "stick_a", "keyboard_stick", ""])
def test_calibration_skip_unchanged(slug: str) -> None:
    # Calibration skipped input files by slug (outputs were skipped already).
    if registry.is_output_name(slug):
        return
    assert dc.can("calibrate", name=slug, module=None) is not (
        dc.is_internal(name=slug))
    # calibration._source_modules' test: Keyboard / OSC files still skipped.
    skipped = dc.is_internal_input(name=slug) and not dc.can("calibrate", name=slug)
    if slug != "logical_device":
        assert skipped is _today_calibration_skips(slug)


@pytest.mark.parametrize("slug", ["xbox_360_controller", "xbox", "vjoy_1"])
def test_calibration_keeps_pad_with_output_slug(slug: str) -> None:
    # A real pad whose file slug reads as an output name stays calibratable:
    # calibration skips only internal-input slugs.
    assert not (
        dc.is_internal_input(name=slug) and not dc.can("calibrate", name=slug))


@pytest.mark.parametrize("module", MODULES, ids=[f"{m.slug}|{m.name}" for m in MODULES])
def test_is_built_in_input_unchanged(module: registry.Module) -> None:
    assert registry.is_built_in_input(module) is _today_is_built_in_input(module)


@pytest.mark.parametrize("module", MODULES, ids=[f"{m.slug}|{m.name}" for m in MODULES])
def test_library_device_rows_unchanged(module: registry.Module) -> None:
    # A Device Library device row: an input module file that isn't built in.
    if module.is_output:
        return
    assert dc.can("library_device", module=module) is not dc.is_internal(
        module=module)


INTERNAL_DEVICES: list[tuple[object, str]] = [
    (ids.KEYBOARD, "Keyboard"),
    (None, "Keyboard"),
    (ids.OSC, "OSC"),
    (None, "OSC"),
    (ids.LOGICAL_DEVICE, "Logical Device"),
    (None, "Logical Device"),
    (VJOY_ID, "vJoy 1"),
    (None, "vJoy 3"),
    (ids.XBOX, "Xbox 360 Controller"),
    (None, "Xbox 360 Controller"),
]


@pytest.mark.parametrize(("guid", "name"), INTERNAL_DEVICES, ids=_ids(INTERNAL_DEVICES))
@pytest.mark.parametrize("action", ["copy", "swap", "calibrate", "library_device"])
def test_internal_devices_refused(action: str, guid: object, name: str) -> None:
    # Copy, swap, calibrate and a Library device row: external only (S90b).
    assert not dc.can(action, guid, name)


@pytest.mark.parametrize("action", ["copy", "swap", "calibrate", "library_device"])
def test_external_devices_allowed(action: str) -> None:
    assert dc.can(action, STICK, "VKBSim NXT  SEM THQ FSM.GA")
    assert dc.can(action, STICK_KB, "Keyboard")
    assert dc.can(action, None, "Stick B")


@pytest.mark.parametrize(("guid", "name"), DEVICES, ids=_ids(DEVICES))
def test_delete_device_keeps_output_files(guid: object, name: str) -> None:
    # Delete Device kept the module file of a vJoy / Xbox output (by name).
    if guid and dc.device_kind(guid) in ("keyboard", "osc", "logical_device", "xbox"):
        return  # a fixed id with a mismatched name never reaches Delete Device
    assert dc.can("delete_device", guid, name) is not is_output_name(name)


@pytest.mark.parametrize(("guid", "name"), DEVICES, ids=_ids(DEVICES))
def test_button_map_any_device(guid: object, name: str) -> None:
    assert dc.can("button_map", guid, name)


# --- a live vJoy device is known by its id ----------------------------------

def _live_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from gremlin.modules import store

    monkeypatch.setattr(store, "live_devices", lambda: [
        SimpleNamespace(name="vJoy Device", device_guid=VJOY_ID, is_virtual=True),
        SimpleNamespace(name="Stick A", device_guid=STICK, is_virtual=False),
    ])


def test_live_vjoy_id_is_internal_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _live_devices(monkeypatch)
    for guid in (VJOY_ID, VJOY_ID.lower().strip("{}")):
        assert dc.device_kind(guid) == "vjoy"
        assert dc.device_class(guid) is DeviceClass.INTERNAL_OUTPUT
        for action in ("copy", "swap", "calibrate", "library_device"):
            assert not dc.can(action, guid)
    # An ordinary stick's id is still external.
    assert dc.device_class(STICK) is DeviceClass.EXTERNAL
    assert dc.can("swap", STICK)
    assert dc.device_class(UNPLUGGED) is DeviceClass.EXTERNAL


def test_no_device_list_means_not_vjoy(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin.modules import store

    def broken() -> list:
        raise RuntimeError("no devices yet")

    monkeypatch.setattr(store, "live_devices", broken)
    assert dc.device_class(VJOY_ID) is DeviceClass.EXTERNAL
