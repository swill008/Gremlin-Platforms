# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A damaged module file (a device's Button Map, claims, calibration).

Every save that changes a module file used to treat a file it couldn't read
as empty and write a nearly empty one over it, losing the map and claims.
Now such a save is refused, the user is told, and the file is left exactly
as it was; the card says the file is damaged and offers Start Fresh, which
keeps the damaged file as a copy. Writes are made safely (temporary file,
then a swap).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import device_initialization
from gremlin.modules import module_file
from gremlin.signal import signal
from gremlin.util import modules_dir

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _good_doc(guid: str) -> dict:
    return {
        "device": "pJoy Pro",
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "axes": [1], "hats": [], "keys": []},
        "nodes": [{"id": f"n{i}"} for i in range(40)],
        "calibration": {"1": [-30000, -50, 50, 30000, True]},
    }


@pytest.fixture
def damaged() -> Iterator[tuple[pathlib.Path, bytes, str]]:
    """pJoy Pro's module file cut off halfway (as after a power cut)."""
    devices = device_initialization.physical_devices()
    dev = next(d for d in devices if d.name == "pJoy Pro")
    guid = str(dev.device_guid)
    path = modules_dir() / "pjoy_pro.json"
    text = json.dumps(_good_doc(guid), indent=2)
    path.write_text(text[: len(text) // 2], encoding="utf-8")
    before = path.read_bytes()
    yield path, before, guid
    for leftover in path.parent.glob("pjoy_pro.json*"):
        leftover.unlink()


@pytest.fixture
def errors() -> Iterator[list[tuple[str, str]]]:
    shown: list[tuple[str, str]] = []

    def record(message: str, details: str) -> None:
        shown.append((message, details))

    signal.showError.connect(record)
    yield shown
    signal.showError.disconnect(record)


# --- the helper ---------------------------------------------------------------


def test_missing_file_reads_as_empty(tmp_path: pathlib.Path) -> None:
    assert module_file.load_for_update(tmp_path / "none.json") == {}
    assert module_file.damage_reason(tmp_path / "none.json") == ""


@pytest.mark.parametrize("text", ['{"device": "x", "nod', "[1, 2]", ""])
def test_damaged_file_is_refused(tmp_path: pathlib.Path, text: str) -> None:
    path = tmp_path / "m.json"
    path.write_text(text, encoding="utf-8")
    assert module_file.damage_reason(path)
    with pytest.raises(module_file.ModuleFileDamaged):
        module_file.load_for_update(path)


def test_write_is_safe_and_leaves_no_temporary_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "sub" / "m.json"
    module_file.write_json(path, {"device": "x"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"device": "x"}
    assert [p.name for p in path.parent.iterdir()] == ["m.json"]


def test_start_fresh_keeps_the_damaged_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "m.json"
    path.write_text("{broken", encoding="utf-8")
    copy = module_file.start_fresh(path)
    assert not path.exists()
    assert copy.name.startswith("m.json.bad-")
    assert copy.read_text(encoding="utf-8") == "{broken"


# --- every save into a damaged file is refused and changes nothing ------------


def test_layout_saves_are_refused(
    damaged: tuple[pathlib.Path, bytes, str], errors: list
) -> None:
    from gremlin.ui.module_model import ModuleListModel

    path, before, guid = damaged
    model = ModuleListModel()
    catalog = json.dumps({"rowSpacing": 6})
    assert model.saveCatalogConfig("pJoy Pro", guid, catalog) is False
    assert model.saveViewConfig("pJoy Pro", guid, json.dumps({"meters": []})) is False
    assert path.read_bytes() == before  # was: rewritten with 0 of its 40 nodes
    assert len(errors) == 2 and "Nothing was saved" in errors[0][0]


def test_module_setup_save_is_refused(
    damaged: tuple[pathlib.Path, bytes, str], errors: list
) -> None:
    from gremlin.ui.module_model import DriverInputModel

    path, before, guid = damaged
    model = DriverInputModel()
    model.loadDevice(guid, "pJoy Pro")
    assert model.saveClaim("pJoy Pro", "source") is False
    assert path.read_bytes() == before
    assert errors


def test_button_map_save_is_refused(
    damaged: tuple[pathlib.Path, bytes, str], errors: list
) -> None:
    from gremlin.ui.hardware_profile import HardwareProfile

    path, before, guid = damaged
    profile = HardwareProfile()
    profile.setDeviceGuid(guid)
    saved = profile.save("pJoy Pro", json.dumps({"nodes": [{"id": "new"}]}))
    assert saved is False
    assert path.read_bytes() == before
    assert errors


def test_calibration_save_does_not_touch_it(
    damaged: tuple[pathlib.Path, bytes, str],
) -> None:
    from gremlin.modules import calibration

    path, before, _guid = damaged
    assert calibration.write_axes("pjoy_pro", {1: (-1, 0, 0, 1, True)}) is False
    assert path.read_bytes() == before


# --- the card -----------------------------------------------------------------


def test_card_says_damaged_and_start_fresh_keeps_a_copy(
    damaged: tuple[pathlib.Path, bytes, str],
) -> None:
    from gremlin.ui.module_model import ModuleListModel

    path, before, guid = damaged
    model = ModuleListModel()
    model._reload()
    card = model.cardMap("pjoy_pro")
    assert card["damaged"]
    assert card["status"].startswith("Module file damaged")

    copy = pathlib.Path(model.startFresh("pJoy Pro", guid))
    assert copy.read_bytes() == before  # nothing lost
    assert not path.exists()
    assert model.cardMap("pjoy_pro").get("damaged", "") == ""
