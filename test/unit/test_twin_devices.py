# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Two identical devices (same name, e.g. a pair of T.16000M).

They shared one module file (claims, card, device map, calibration), and
saving from one moved the other's calibration. The second is now
"<name> (2)" with its own device folder (03 S6, S132); the device whose id
the existing folder holds (device.json) keeps the plain name, and the names
are kept by device id.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

import dill
from gremlin import device_initialization
from gremlin.config import Configuration
from gremlin.modules import store
from gremlin.util import modules_dir
from test import fake_hardware
from test.unit._device_folders import put_module

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _twin() -> dill._DeviceSummary:
    dev = fake_hardware.raw_device(is_virtual=False)  # also "pJoy Pro"
    dev.device_guid = dill._GUID(
        Data1=0x9900, Data2=1, Data3=1, Data4=(9, 9, 9, 9, 9, 9, 9, 9)
    )
    return dev


@pytest.fixture
def twins() -> Iterator[list]:
    listed = dill.DILL._dll.devices
    before = list(listed)
    stored = Configuration().value(*device_initialization.TWIN_SETTING)
    Configuration().set(*device_initialization.TWIN_SETTING, {})
    listed.append(_twin())
    device_initialization._joystick_devices.clear()
    yield listed
    listed[:] = before
    Configuration().set(*device_initialization.TWIN_SETTING, stored)
    for leftover in modules_dir().glob("pJoy Pro*"):
        shutil.rmtree(leftover, ignore_errors=True)
    store._dirs_changed()
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()


def _names() -> dict[str, str]:
    return {
        str(d.device_guid.uuid).upper(): d.name
        for d in device_initialization.physical_devices()
    }


def _first_guid() -> str:
    return str(dill.GUID(fake_hardware.raw_guid(False)).uuid).upper()


def _twin_guid() -> str:
    return str(dill.GUID(_twin().device_guid).uuid).upper()


def test_the_second_identical_device_gets_its_own_name(twins: list) -> None:
    device_initialization.joystick_devices_initialization()
    assert sorted(_names().values()) == ["pJoy Pro", "pJoy Pro (2)"]
    stored = Configuration().value(*device_initialization.TWIN_SETTING)
    assert list(stored.values()) == ["pJoy Pro (2)"]

    # The same names on the next scan (kept by device id).
    first = _names()
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()
    assert _names() == first


def test_each_twin_has_its_own_card(twins: list) -> None:
    from gremlin.ui.module_model import ModuleListModel

    device_initialization.joystick_devices_initialization()
    model = ModuleListModel()
    model._reload()
    assert model.cardMap("pjoy_pro").get("name") == "pJoy Pro"
    assert model.cardMap("pjoy_pro_2").get("name") == "pJoy Pro (2)"


def test_labels_use_the_shown_name(twins: list) -> None:
    device_initialization.joystick_devices_initialization()
    twin = dill.GUID(_twin().device_guid)
    assert device_initialization.device_name(twin).startswith("pJoy Pro")
    assert device_initialization.device_name(twin) == _names()[_twin_guid()]


def test_a_single_device_is_not_renamed() -> None:
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()
    assert "pJoy Pro" in [d.name for d in device_initialization.physical_devices()]


def test_each_twin_keeps_its_own_calibration(twins: list) -> None:
    from gremlin.modules import calibration

    device_initialization.joystick_devices_initialization()
    names = _names()
    for guid, curve in ((_first_guid(), -100), (_twin_guid(), -200)):
        name = names[guid]
        put_module(modules_dir(), name, {
            "device": name, "direction": "source", "boundGuidLocal": guid,
            "claim": {"buttons": [1], "axes": [1], "hats": [], "keys": []},
            "calibration": {"1": [curve, 0, 0, 30000, True]},
        }, guid)
    rows = {r["slug"]: r for r in calibration._source_modules()}
    assert {"pJoy Pro", "pJoy Pro (2)"} <= set(rows)  # both in Calibration
    first = calibration.values_for_device(dill.GUID.from_str(_first_guid()).uuid, 1)
    second = calibration.values_for_device(dill.GUID.from_str(_twin_guid()).uuid, 1)
    assert first[0] == -100 and second[0] == -200


# --- one rule for every part of the program (audit 2, group A) -------------


def _module(slug: str, name: str, guid: str, buttons: list[int]) -> Path:
    """name's device folder (slug is unused: the folder is named after the
    device, 03 S128)."""
    return put_module(modules_dir(), name, {
        "device": name, "direction": "source", "boundGuidLocal": guid,
        "claim": {"buttons": buttons, "axes": [], "hats": [], "keys": []},
    }, guid)


def test_the_device_map_of_the_second_twin_opens_its_own_file(twins: list) -> None:
    from gremlin.ui.hardware_profile import HardwareProfile

    first, second = _first_guid(), _twin_guid()
    _module("pjoy_pro", "pJoy Pro", first, [1])
    device_initialization.joystick_devices_initialization()
    _module("pjoy_pro_2", "pJoy Pro (2)", second, [2])
    assert _names()[second] == "pJoy Pro (2)"
    hw = HardwareProfile()
    hw.setDeviceGuid(second)
    own = store.module_file("pJoy Pro (2)", second)
    assert own.parent.name == "pJoy Pro (2)" and own.is_file()
    assert store.module_file("pJoy Pro", first).parent.name == "pJoy Pro"
    hw.deleteLater()



def test_a_restored_module_file_goes_back_to_its_devices_folder() -> None:
    """08 Q14 (GL-081), D-03-DEVICE-FOLDERS: History Restore writes the file
    into the folder holding the device's id (dir_of_id of boundGuidLocal),
    even for an old entry named by a file name of the old layout."""
    from gremlin.ui import history_model

    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()
    guid = _first_guid()
    own = _module("pjoy_pro", "pJoy Pro", guid, [1])
    store._dirs_changed()
    doc = {
        "device": "pJoy Pro", "direction": "source", "boundGuidLocal": guid,
        "boundName": "pJoy Pro",
        "claim": {"buttons": [5], "axes": [], "hats": [], "keys": []},
    }
    try:
        ok, _message = history_model._restore_module(
            {"subject": {"fileName": "my_setup.json", "device": "pJoy Pro"}},
            {"text": json.dumps(doc, indent=2), "pictures": []},
        )
        assert ok
        assert store.module_file("pJoy Pro", guid) == own
        written = json.loads(own.read_text(encoding="utf-8"))
        assert written["claim"]["buttons"] == [5]
        assert not (modules_dir() / "my_setup.json").exists()
    finally:
        shutil.rmtree(own.parent, ignore_errors=True)
        store._dirs_changed()
