# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Every action a Built-in inputs row offers (10 S6, S6a, D-04-LD-FILE):
Save to Device Library…, Export…, Rename…, Edit Description, and History
restore of what they did, for Keyboard, OSC and the Logical Device with no
stick plugged in. Each goes through the slot WindowDeviceLibrary.qml calls
(saveToLibrary, exportCurrent, exportSetup, rename, describe) and History's
restore; none is refused and each does its job. Restore itself is covered by
test_ld_restore_builtin.py. The real model, Library, store and History in
temporary folders."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore
from pytestqt.qtbot import QtBot

from gremlin import device_library as library
from gremlin import history, logical_device_file
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids, module_file, store
from gremlin.ui import history_model
from gremlin.ui.device_library_model import DeviceLibraryModel
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    settle_history,
)


def _g(uid: object) -> str:
    return "{" + str(uid).upper() + "}"


# (shown name, id, module file name)
BUILT_INS = [
    ("Keyboard", _g(ids.KEYBOARD), "keyboard.json"),
    ("OSC", _g(ids.OSC), "osc.json"),
    ("Logical Device", _g(ids.LOGICAL_DEVICE), "logical_device.json"),
]


def _layout(*labels: str) -> dict:
    return {
        "controls": [
            {
                "uid": f"{n:032x}",
                "type": "button",
                "id": n,
                "label": label,
                "user-label": "",
                "group": "",
                "hide-system": False,
            }
            for n, label in enumerate(labels, start=1)
        ],
        "groups": [],
    }


def _doc(name: str, guid: str, *labels: str) -> dict:
    doc: dict = {
        "kind": "control.hardware",
        "device": name,
        "boundGuidLocal": guid,
        "nodes": [],
        "claim": {},
    }
    if guid == _g(ids.LOGICAL_DEVICE):
        doc[logical_device_file.KEY] = _layout(*(labels or ("Saved",)))
    else:
        doc["note"] = " ".join(labels)
    return doc


@pytest.fixture
def rows() -> Iterator[LogicalDevice]:
    device = LogicalDevice()
    kept = device.to_dict()
    yield device
    device.load_dict(kept)


@pytest.fixture(params=BUILT_INS, ids=[b[0] for b in BUILT_INS])
def built_in(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    rows: LogicalDevice,
) -> tuple[str, str, Path]:
    # No stick plugged in; Home names (device_aliases) kept in a dict here.
    monkeypatch.setattr(library, "_connected", lambda: [])
    aliases: dict[str, str] = {}
    monkeypatch.setattr(
        library, "_alias", lambda guid, default: aliases.get(guid, default)
    )
    monkeypatch.setattr(library, "_set_alias", aliases.__setitem__)
    modules: Path = request.getfixturevalue(folder.__name__)
    name, guid, file_name = request.param
    path = modules / file_name
    module_file.write_bytes(path, json.dumps(_doc(name, guid, "Saved")).encode())
    if guid == _g(ids.LOGICAL_DEVICE):
        rows.load_dict(_layout("Saved"))
    return name, guid, path


@pytest.fixture
def model(qtbot: QtBot, built_in: tuple[str, str, Path]) -> DeviceLibraryModel:
    m = DeviceLibraryModel(watch_devices=False)
    m.refresh()
    return m


def _run(qtbot: QtBot, model: DeviceLibraryModel, start: Callable[[], object]) -> dict:
    with qtbot.waitSignal(model.result, timeout=10000) as blocker:
        assert start()
    res = blocker.args[0]
    assert res["ok"], res
    return res


def _row(model: DeviceLibraryModel, guid: str) -> dict:
    model.refresh()
    return next(d for d in model._devices if d.get("guid") == guid)


def _url(path: Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def _save(qtbot: QtBot, model: DeviceLibraryModel, guid: str) -> dict:
    count = len(_row(model, guid).get("setups") or [])
    _run(qtbot, model, lambda: model.saveToLibrary(_row(model, guid)["key"], []))
    setups = _row(model, guid).get("setups") or []
    assert len(setups) == count + 1
    return setups[0]


def _new_entries(before: set[str]) -> list[dict]:
    settle_history()
    return [e for e in history.entries() if e.get("id") not in before]


def _ids() -> set[str]:
    settle_history()
    return {str(e.get("id")) for e in history.entries()}


# --- the row is a built-in and its actions are on (S6) ----------------------


def test_row_is_built_in_and_can_save(
    model: DeviceLibraryModel, built_in: tuple[str, str, Path]
) -> None:
    _name, guid, _path = built_in
    row = _row(model, guid)
    assert row.get("builtIn") is True
    model.select(row["key"])
    details = model.details
    assert details["builtIn"] is True
    # canSave in WindowDeviceLibrary.qml.
    assert details["hasCurrent"] is True


# --- Save to Device Library… (S12) ------------------------------------------


def test_save_to_device_library(
    qtbot: QtBot, model: DeviceLibraryModel, built_in: tuple[str, str, Path]
) -> None:
    _name, guid, _path = built_in
    setup = _save(qtbot, model, guid)
    pack = library.pack_path(setup["key"])
    assert pack.is_file()
    with zipfile.ZipFile(pack) as z:
        assert z.namelist()


# --- Export… (S44 Export Current Setup, and a saved setup's Export) ---------


def test_export_current(
    qtbot: QtBot,
    model: DeviceLibraryModel,
    built_in: tuple[str, str, Path],
    tmp_path: Path,
) -> None:
    _name, guid, _path = built_in
    dest = tmp_path / "out" / "current"
    dest.parent.mkdir()
    key = _row(model, guid)["key"]
    _run(qtbot, model, lambda: model.exportCurrent(key, _url(dest)))
    made = dest.with_name("current.zip")
    assert made.is_file()
    with zipfile.ZipFile(made) as z:
        assert z.namelist()


def test_export_saved_setup(
    qtbot: QtBot,
    model: DeviceLibraryModel,
    built_in: tuple[str, str, Path],
    tmp_path: Path,
) -> None:
    _name, guid, _path = built_in
    setup = _save(qtbot, model, guid)
    dest = tmp_path / "saved.zip"
    _run(qtbot, model, lambda: model.exportSetup(setup["key"], _url(dest)))
    assert dest.is_file()


# --- Rename… and Edit Description (S7, S11, S13) -----------------------------


def test_rename_and_describe_the_row(
    qtbot: QtBot, model: DeviceLibraryModel, built_in: tuple[str, str, Path]
) -> None:
    _name, guid, _path = built_in
    key = _row(model, guid)["key"]
    with qtbot.waitSignal(model.result, timeout=5000) as blocker:
        model.rename(key, "My Built-in")
    assert blocker.args[0]["ok"], blocker.args[0]
    assert _row(model, guid)["name"] == "My Built-in"
    with qtbot.waitSignal(model.result, timeout=5000) as blocker:
        model.describe(key, "Kept for the sim")
    assert blocker.args[0]["ok"], blocker.args[0]
    assert _row(model, guid)["description"] == "Kept for the sim"


def test_rename_and_describe_a_saved_setup(
    qtbot: QtBot, model: DeviceLibraryModel, built_in: tuple[str, str, Path]
) -> None:
    _name, guid, _path = built_in
    setup = _save(qtbot, model, guid)
    with qtbot.waitSignal(model.result, timeout=5000) as blocker:
        model.rename(setup["key"], "Before the update")
    assert blocker.args[0]["ok"], blocker.args[0]
    with qtbot.waitSignal(model.result, timeout=5000) as blocker:
        model.describe(setup["key"], "Old layout")
    assert blocker.args[0]["ok"], blocker.args[0]
    got = next(
        s for s in _row(model, guid).get("setups") or [] if s["key"] == setup["key"]
    )
    assert got["name"] == "Before the update"
    assert got["description"] == "Old layout"


# --- History: a built-in's changes put back (08, 10 S51) ---------------------


def test_history_restores_the_save(
    qtbot: QtBot, model: DeviceLibraryModel, built_in: tuple[str, str, Path]
) -> None:
    _name, guid, _path = built_in
    before = _ids()
    setup = _save(qtbot, model, guid)
    made = _new_entries(before)
    assert made, "Save to Device Library made no History entry"
    entry = made[0]
    out = history_model.restore(str(entry["id"]), "before")
    assert out["ok"], out
    keys = [s["key"] for s in _row(model, guid).get("setups") or []]
    assert setup["key"] not in keys
    out = history_model.restore(str(entry["id"]), "after")
    assert out["ok"], out
    keys = [s["key"] for s in _row(model, guid).get("setups") or []]
    assert setup["key"] in keys


def test_history_restores_the_module_file(
    model: DeviceLibraryModel,
    built_in: tuple[str, str, Path],
    rows: LogicalDevice,
) -> None:
    name, guid, path = built_in
    old = path.read_bytes()
    before = _ids()
    store.replace(
        path, json.dumps(_doc(name, guid, "Changed")).encode(), "Home", force=True
    )
    made = [
        e
        for e in _new_entries(before)
        if (e.get("subject") or {}).get("fileName") == path.name
    ]
    assert made, "the module file change made no History entry"
    out = history_model.restore(str(made[0]["id"]), "before")
    assert out["ok"], out
    assert json.loads(path.read_bytes()) == json.loads(old)
    if guid == _g(ids.LOGICAL_DEVICE):
        assert [c["label"] for c in rows.to_dict()["controls"]] == ["Saved"]

