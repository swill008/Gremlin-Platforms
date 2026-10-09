# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""File choices left by old ids of a stick (03 S94, D-03-STALE-CHOICES).

A HID Remapper that came back with a new id left its old ids' file choices
pointing at its module file. They counted as "another stick uses this
file", so Delete Device kept the file and the Device Library could not
remove the device. Only a device plugged in now, or one the Device Library
has as a separate device, keeps the file; Delete Device and Delete File
clear the stale choices with it.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_initialization, util
from gremlin import device_library as library
from gremlin.modules import registry
from gremlin.modules import store as module_store
from gremlin.modules.ids import stored_guid_key
from gremlin.ui import hardware_profile, module_model

_APPS: list[QtCore.QCoreApplication] = []

NAME = "HID Remapper ACHB"
SLUG = "hid_remapper_achb"
OWN = "10C58030-BE86-11F1-8001-444553540000"  # the file's bound id
OLD = ("41328A00B45F11F18003444553540000", "032D8D70BE8911F18005444553540000")
LIBRARY_ONLY = "7777777788889999AAAABBBBCCCCDDDD"


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """The modules folder with only the HID Remapper's file, no file choices
    and an empty Device Library of its own; put back afterwards."""
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    path = util.modules_dir()
    aside = tmp_path / "aside"
    aside.mkdir()
    for old in path.glob("*.json"):
        shutil.move(str(old), str(aside / old.name))
    before = {p.name for p in path.iterdir()}
    bindings = module_store.bindings()
    order = module_model._order_slugs()
    hidden = module_model._hidden_slugs()
    (path / f"{SLUG}.json").write_text(
        json.dumps({
            "kind": "control.hardware",
            "device": NAME,
            "direction": "source",
            "boundGuidLocal": OWN,
            "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
        }),
        encoding="utf-8",
    )
    module_store.set_bindings({
        stored_guid_key(OWN): SLUG,
        OLD[0]: SLUG,
        OLD[1]: SLUG,
        registry.name_key(NAME): SLUG,
    })
    yield path
    for extra in path.iterdir():
        if extra.name in before:
            continue
        if extra.is_dir():
            shutil.rmtree(extra, ignore_errors=True)
        else:
            extra.unlink(missing_ok=True)
    for old in aside.iterdir():
        shutil.move(str(old), str(path / old.name))
    module_store.set_bindings(bindings)
    module_model._set_order(order)
    module_model._set_hidden(hidden)


def _plugged_in_guid() -> str:
    dev = next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    )
    return stored_guid_key(str(dev.device_guid))


def _library_knows(tmp_path: Path, guid: str) -> None:
    lib = tmp_path / "device library"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / library.LIST_NAME).write_text(
        json.dumps({
            "format": 1,
            "devices": [{"key": "other", "name": "Other Stick", "guid": guid}],
        }),
        encoding="utf-8",
    )


def test_old_ids_choices_do_not_keep_the_file(folder: Path) -> None:
    assert registry.resolve_module_slug(NAME, OWN) == SLUG
    # Old: True (the two old ids counted as other sticks).
    assert not module_store.is_shared(NAME, OWN)
    assert module_store.other_users(SLUG, NAME, OWN) == set()


def test_delete_device_deletes_the_file_and_the_old_choices(folder: Path) -> None:
    out = json.loads(hardware_profile.delete_device(NAME, OWN))
    assert out["ok"], out
    # Old: keptFile True and the file stayed.
    assert not out["keptFile"]
    assert not (folder / f"{SLUG}.json").exists()
    left = module_store.bindings()
    assert all(key not in left for key in (stored_guid_key(OWN), *OLD))
    assert SLUG not in {str(v) for v in left.values()}


def test_store_delete_drops_the_old_choices(folder: Path) -> None:
    assert module_store.delete(NAME, OWN) == ""
    assert not (folder / f"{SLUG}.json").exists()
    assert SLUG not in {str(v) for v in module_store.bindings().values()}


def test_a_plugged_in_stick_using_the_file_keeps_it(folder: Path) -> None:
    other = _plugged_in_guid()
    data = module_store.bindings()
    data[other] = SLUG
    module_store.set_bindings(data)
    assert module_store.other_users(SLUG, NAME, OWN) == {other}
    assert module_store.is_shared(NAME, OWN)
    assert module_store.delete(NAME, OWN) == "Another stick is using this file."
    assert (folder / f"{SLUG}.json").is_file()


def test_a_device_the_library_knows_keeps_the_file(
    folder: Path, tmp_path: Path
) -> None:
    _library_knows(tmp_path, LIBRARY_ONLY)
    data = module_store.bindings()
    data[LIBRARY_ONLY] = SLUG
    module_store.set_bindings(data)
    assert module_store.other_users(SLUG, NAME, OWN) == {LIBRARY_ONLY}
    assert module_store.is_shared(NAME, OWN)
    out = json.loads(hardware_profile.delete_device(NAME, OWN))
    assert out["ok"], out
    assert out["keptFile"]
    assert (folder / f"{SLUG}.json").is_file()
    assert module_store.bindings().get(LIBRARY_ONLY) == SLUG

