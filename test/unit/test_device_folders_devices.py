# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device folders on the device side (D-03-DEVICE-FOLDERS; 03 S1, S3, S4,
S6, S128-S132): a rename renames the device's folder or is refused with the
reason and nothing saved; twins get folders of their own; a scan after a
name changed outside a rename brings the folder along; the Logical Device's
and OSC's files are in their own folders; Save Diagnostics names the folder.
Every module file goes to a temp modules folder, never the real one."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6 import QtCore

import dill
from gremlin import device_aliases, device_initialization
from gremlin.config import Configuration
from test import fake_hardware
from test.unit import _device_folders as folders

_APPS: list[QtCore.QCoreApplication] = []
STICK = "pJoy Pro"


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A temp modules folder, the aliases and twin names put back after."""
    from gremlin import util

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(util, "modules_dir", lambda: folder)
    cfg = Configuration()
    device_aliases._ensure()
    keys = [
        (device_aliases.SECTION, device_aliases.GROUP, device_aliases.NAME),
        device_initialization.TWIN_SETTING,
    ]
    before = [cfg.value(*key) for key in keys]
    cfg.set(*device_initialization.TWIN_SETTING, {})
    device_aliases._CACHE = None
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()
    yield folder
    for key, value in zip(keys, before):
        cfg.set(*key, value)
    device_aliases._CACHE = None
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()


def _stick_guid() -> str:
    return str(dill.GUID(fake_hardware.raw_guid(False)).uuid).upper()


def _stick_doc(guid: str, name: str = STICK) -> dict:
    return {
        "device": name,
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
    }


def _id_in(folder: Path) -> str:
    return str(json.loads((folder / "device.json").read_text("utf-8")).get("id"))


# --- rename renames the folder (S3, S131) -------------------------------------


def test_renaming_a_device_renames_its_folder(modules: Path) -> None:
    guid = _stick_guid()
    old = folders.put_module(modules, STICK, _stick_doc(guid), guid)
    assert old.parent.name == STICK

    assert device_aliases.set_alias(guid, "Main Stick") == ""

    new = modules / "Main Stick" / "module.json"
    assert new.is_file() and not old.parent.exists()
    assert json.loads(new.read_text("utf-8"))["claim"]["buttons"] == [1]
    assert device_aliases.display_name(guid, STICK) == "Main Stick"
    # Every place finds it under the new name (by its id, S1).
    from gremlin.modules import store

    assert store.module_file(STICK, guid) == new


def test_a_folder_name_gets_underscores_but_the_shown_name_stays(
    modules: Path,
) -> None:
    guid = _stick_guid()
    folders.put_module(modules, STICK, _stick_doc(guid), guid)

    assert device_aliases.set_alias(guid, "Left: Stick?") == ""

    assert (modules / "Left_ Stick_" / "module.json").is_file()
    assert device_aliases.display_name(guid, STICK) == "Left: Stick?"


def test_a_busy_folder_refuses_the_rename_and_saves_no_alias(modules: Path) -> None:
    from gremlin.ui import device_names

    guid = _stick_guid()
    path = folders.put_module(modules, STICK, _stick_doc(guid), guid)

    # A file in the folder held open elsewhere: Windows can't rename it.
    with path.open("rb"):
        reason = device_names.set_alias(guid, "Main Stick")

    assert reason, "the rename should be refused with the reason"
    assert STICK in reason and "Main Stick" in reason
    assert path.is_file() and not (modules / "Main Stick").exists()
    assert device_aliases.display_name(guid, STICK) == STICK
    assert guid not in {k.upper() for k in device_aliases._load()}


def test_a_built_in_rename_keeps_its_folder(modules: Path) -> None:
    folders.put_module(modules, "Keyboard", {"device": "Keyboard"})

    assert device_aliases.set_alias("keyboard", "Keys") == ""

    assert (modules / "Keyboard" / "module.json").is_file()
    assert device_aliases.display_name("keyboard", "Keyboard") == "Keys"


# --- twins (S6, S132) ----------------------------------------------------------


def _twin() -> dill._DeviceSummary:
    dev = fake_hardware.raw_device(is_virtual=False)
    dev.device_guid = dill._GUID(
        Data1=0x9900, Data2=1, Data3=1, Data4=(9, 9, 9, 9, 9, 9, 9, 9)
    )
    return dev


def _twin_guid() -> str:
    return str(dill.GUID(_twin().device_guid).uuid).upper()


@pytest.fixture
def twins(modules: Path) -> Iterator[Path]:
    listed = dill.DILL._dll.devices
    before = list(listed)
    listed.append(_twin())
    device_initialization._joystick_devices.clear()
    yield modules
    listed[:] = before


def _names() -> dict[str, str]:
    return {
        str(d.device_guid.uuid).upper(): d.name
        for d in device_initialization.physical_devices()
    }


def test_twins_get_their_own_folders(twins: Path) -> None:
    from gremlin.modules import store

    device_initialization.joystick_devices_initialization()
    names = _names()
    first, second = _stick_guid(), _twin_guid()
    assert sorted(names.values()) == [STICK, f"{STICK} (2)"]

    one = store.ensure_device_dir(names[first], first)
    two = store.ensure_device_dir(names[second], second)

    assert one != two
    assert {one.name, two.name} == {STICK, f"{STICK} (2)"}
    assert store.dir_of_id(first) == one and store.dir_of_id(second) == two


def test_the_device_whose_id_the_folder_holds_keeps_the_plain_name(
    twins: Path,
) -> None:
    # The first stick's id sorts after the twin's: by id alone the twin
    # would get the plain name; the folder holding the first's id decides.
    first = _stick_guid()
    assert _twin_guid() < first
    folders.put_module(twins, STICK, _stick_doc(first), first)

    device_initialization.joystick_devices_initialization()

    names = _names()
    assert names[first] == STICK
    assert names[_twin_guid()] == f"{STICK} (2)"


# --- a scan syncs the folder name (S130, S131) ---------------------------------


def test_a_scan_after_an_outside_name_change_syncs_the_folder(modules: Path) -> None:
    guid = _stick_guid()
    old = folders.put_module(modules, STICK, _stick_doc(guid), guid)
    # Put in the settings from outside (as a History put-back does), no rename.
    device_aliases._save({guid: "Renamed Outside"})

    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()

    assert (modules / "Renamed Outside" / "module.json").is_file()
    assert not old.parent.exists()


def test_a_scan_with_no_change_leaves_the_folder(modules: Path) -> None:
    guid = _stick_guid()
    path = folders.put_module(modules, STICK, _stick_doc(guid), guid)

    device_initialization.joystick_devices_initialization()

    assert path.is_file()
    assert sorted(p.name for p in modules.iterdir() if p.is_dir()) == [STICK]


def test_a_module_file_found_by_id_counts_for_forgetting(modules: Path) -> None:
    guid = _stick_guid()
    folders.put_module(modules, STICK, _stick_doc(guid), guid)

    assert device_initialization._has_module_file("", guid)
    assert device_initialization._has_module_file(STICK, guid)
    assert not device_initialization._has_module_file(
        "", "11111111-2222-3333-4444-555555555555"
    )


# --- the Logical Device's and OSC's files (S128) ------------------------------


class _Rows:
    dirty = True
    unreadable: list = []

    def to_dict(self) -> dict:
        return {"controls": [], "groups": ["Main"]}

    def mark_saved(self) -> None:
        self.dirty = False


def test_the_logical_device_file_lands_in_its_folder(modules: Path) -> None:
    from gremlin import logical_device_file
    from gremlin.modules import ids

    assert logical_device_file.save(_Rows(), "Test")

    path = modules / "Logical Device" / "module.json"
    assert logical_device_file.path() == path and path.is_file()
    assert json.loads(path.read_text("utf-8"))["logical-device"]["groups"] == ["Main"]
    assert folders.id_key("Logical Device", str(ids.LOGICAL_DEVICE)) == _id_in(
        path.parent
    )
    assert not (modules / "logical_device.json").exists()


def test_the_osc_file_lands_in_its_folder(modules: Path) -> None:
    from gremlin import osc_device_file
    from gremlin.modules import ids

    assert osc_device_file.write_server({"port": 9001}, "Test")

    path = modules / "OSC" / "module.json"
    assert osc_device_file.path() == path and path.is_file()
    assert osc_device_file.read_server()["port"] == 9001
    assert folders.id_key("OSC", str(ids.OSC)) == _id_in(path.parent)
    assert not (modules / "osc.json").exists()


# --- Save Diagnostics names the folder ------------------------------------------


def test_the_diagnostics_zip_names_each_modules_folder(
    modules: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import diagnostics
    from gremlin.modules import hardware

    guid = _stick_guid()
    folders.put_module(modules, STICK, _stick_doc(guid), guid)
    monkeypatch.setattr(hardware, "devices", lambda: [])

    listed = diagnostics.devices()
    rows = {row["name"]: row for row in listed["modules"]}
    assert "modulesError" not in listed
    assert rows[STICK]["folder"] == STICK
    assert rows[STICK]["file"] == f"{STICK}/module.json"

    plan = SimpleNamespace(
        logs=None,
        settings=None,
        devices=listed,
        versions={},
        profile_name="",
        profile_text=None,
        tester=None,
        names=[],
        made="now",
    )
    dest = tmp_path / "diag.zip"
    diagnostics.write_zip(plan, dest)  # type: ignore[arg-type]
    with zipfile.ZipFile(dest) as zf:
        written = json.loads(zf.read("devices.json"))
    assert {r["file"] for r in written["modules"]} == {f"{STICK}/module.json"}


# --- Auto Mapping Tool picks the device's own folder (S1) ----------------------------


def test_auto_mapping_tool_keeps_the_devices_own_folder(modules: Path) -> None:
    from gremlin.modules import auto_mapping_tool, store

    guid = _stick_guid()
    own = folders.put_module(modules, STICK, _stick_doc(guid), guid).parent
    other = store.folder() / "Other"
    rows = [
        {"dir": other, "name": STICK, "guid": ""},
        {"dir": own, "name": STICK, "guid": guid},
    ]
    assert auto_mapping_tool._choose_input(rows)["dir"] == own
