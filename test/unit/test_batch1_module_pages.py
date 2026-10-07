# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module pages on the module file store (map 1, batch 1).

Home cards, Module Setup, Calibration and the Button Map find a device's
module file through gremlin.modules.store, by the device's name and id:
twins are looked up by id (decision F4, GL-076), a stale id is filtered the
same way for every caller (GL-075), Start Fresh is a History entry
(decision F3, GL-080), Calibration lists every stick, also two on one file
(GL-088), and the Button Map can see its file changed elsewhere (GL-071).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from PySide6 import QtCore

import dill
from gremlin import clock, device_initialization, history, history_modules
from gremlin.config import Configuration
from gremlin.modules import registry, store
from gremlin.modules.ids import stored_guid_key
from test import fake_hardware

_ROOT = Path(__file__).resolve().parents[2]
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _wait_for(done: Callable[[], bool], limit: float = 10.0) -> bool:
    deadline = clock.monotonic() + limit
    while not done():
        if clock.monotonic() > deadline:
            return False
        QtCore.QCoreApplication.processEvents()
        QtCore.QThread.msleep(5)
    return True


@pytest.fixture
def folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """An empty modules folder of its own, no file choices, History in the
    temporary folder."""
    modules = tmp_path / "modules"
    modules.mkdir()
    _wait_for(lambda: history._writer is None)
    monkeypatch.setattr(store, "folder", lambda: modules)
    monkeypatch.setattr(registry, "_binding_store", lambda: {})
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(history_modules, "_last_pictures", {})
    registry._cache.clear()
    yield modules
    _wait_for(lambda: history._writer is None)
    registry._cache.clear()


def _twin() -> dill._DeviceSummary:
    dev = fake_hardware.raw_device(is_virtual=False)  # also "pJoy Pro"
    dev.device_guid = dill._GUID(
        Data1=0x9911, Data2=1, Data3=1, Data4=(9, 9, 9, 9, 9, 9, 9, 9)
    )
    return dev


@pytest.fixture
def twins(folder: Path) -> Iterator[Path]:
    """Two "pJoy Pro" sticks: "pJoy Pro" and "pJoy Pro (2)"."""
    listed = dill.DILL._dll.devices
    before = list(listed)
    stored = Configuration().value(*device_initialization.TWIN_SETTING)
    Configuration().set(*device_initialization.TWIN_SETTING, {})
    listed.append(_twin())
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()
    yield folder
    listed[:] = before
    Configuration().set(*device_initialization.TWIN_SETTING, stored)
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()


def _guid_of(name: str) -> str:
    """The id of the connected device shown as name (which twin keeps the
    plain name depends on the files bound earlier)."""
    return str(next(
        d for d in device_initialization.physical_devices() if d.name == name
    ).device_guid)


def _first_guid() -> str:
    return _guid_of("pJoy Pro")


def _twin_guid() -> str:
    return _guid_of("pJoy Pro (2)")


def _module(folder: Path, slug: str, name: str, guid: str, buttons: list[int]) -> Path:
    path = folder / f"{slug}.json"
    path.write_text(json.dumps({
        "kind": "control.hardware", "device": name, "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": buttons, "axes": [], "hats": [], "keys": []},
    }), encoding="utf-8")
    return path


def _two_twin_files(folder: Path) -> None:
    _module(folder, "pjoy_pro", "pJoy Pro", _first_guid(), [1])
    _module(folder, "pjoy_pro_2", "pJoy Pro (2)", _twin_guid(), [1, 2, 3])


# --- GL-076 / F4: twins are looked up by id ------------------------------------


def test_twin_cards_keep_their_own_counts_and_are_looked_up_by_id(
    twins: Path,
) -> None:
    from gremlin.ui import module_model

    _two_twin_files(twins)
    calls: list[tuple[str, str]] = []
    real = registry.resolve_module_slug

    def spy(name: str, guid: str = "") -> str:
        calls.append((name, guid))
        return real(name, guid)

    with mock.patch.object(registry, "resolve_module_slug", spy):
        if hasattr(module_model, "resolve_module_slug"):  # the old code
            module_model.resolve_module_slug = spy  # type: ignore[attr-defined]
        try:
            model = module_model.ModuleListModel()
            model._reload()
            calls.clear()
            model.notifyClaims()  # what a save elsewhere runs
        finally:
            if hasattr(module_model, "resolve_module_slug"):
                module_model.resolve_module_slug = real  # type: ignore[attr-defined]
    first, second = model.cardMap("pjoy_pro"), model.cardMap("pjoy_pro_2")
    assert (first["buttons"], second["buttons"]) == (1, 3)
    # Every lookup of a twin's file carried its id (S77, decision F4).
    twins_named = [c for c in calls if c[0].startswith("pJoy Pro")]
    assert twins_named and all(guid for _name, guid in twins_named), twins_named


def test_pairing_and_module_inputs_read_the_twins_own_file(twins: Path) -> None:
    from gremlin.ui import module_inputs, module_pairing

    _two_twin_files(twins)
    # Each twin's claim, looked up by its id (GL-076).
    one = module_pairing._source_claim("pJoy Pro", _first_guid())
    two = module_pairing._source_claim("pJoy Pro (2)", _twin_guid())
    assert (one["buttons"], two["buttons"]) == ([1], [1, 2, 3])
    counts = []
    for name, guid in (("pJoy Pro", _first_guid()), ("pJoy Pro (2)", _twin_guid())):
        model = module_inputs.ModuleClaimedInputModel()
        model._device_name = name
        model._set_guid(guid)
        counts.append(model.rowCount())
    assert counts == [1, 3]


# --- GL-075: a stale id reaches the same file as Delete ------------------------


def test_a_stale_id_does_not_send_start_fresh_to_another_devices_file(
    twins: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import module_model

    fine = _module(twins, "pjoy_pro", "pJoy Pro", _first_guid(), [1])
    # An old stick's file, chosen for an id no connected device has, damaged.
    stale = "{0BADBEEF-0000-0000-0000-000000000001}"
    damaged = twins / "old_stick.json"
    damaged.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    monkeypatch.setattr(
        registry, "_binding_store", lambda: {stored_guid_key(stale): "old_stick"}
    )
    model = module_model.ModuleListModel()
    for guid in (stale, _twin_guid()):
        # pJoy Pro (connected with its own id) called with another id: its
        # own file, as Delete and the Device Pack find it (03 S9, S2).
        assert module_model._module_damage("pJoy Pro", guid) == ""
        doc = module_model._load_module_doc("pJoy Pro", guid)
        assert doc["claim"]["buttons"] == [1]
        assert model.moduleFileFor(guid, "pJoy Pro") == "pjoy_pro"
        assert model.startFresh("pJoy Pro", guid) == ""
        assert damaged.is_file() and fine.is_file()


# --- GL-080 / F3: Start Fresh is a History entry -------------------------------


def test_start_fresh_is_one_history_entry(folder: Path) -> None:
    from gremlin.ui import module_model

    path = folder / "pjoy_pro.json"
    path.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    guid = str(next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    ).device_guid)
    model = module_model.ModuleListModel()
    copy = Path(model.startFresh("pJoy Pro", guid))
    assert copy.name.startswith("pjoy_pro.json.bad-") and not path.exists()
    _wait_for(lambda: history._writer is None)
    entries = [
        e for e in history.entries("modules")
        if (e.get("subject") or {}).get("fileName") == "pjoy_pro.json"
    ]
    assert len(entries) == 1


# --- GL-088: Calibration lists two sticks on one file --------------------------


def test_calibration_lists_both_sticks_that_share_a_file(tmp_path: Path) -> None:
    from gremlin.modules import calibration

    path = tmp_path / "stick.json"
    path.write_text(json.dumps({"device": "Stick"}), encoding="utf-8")
    one, two = uuid.uuid4(), uuid.uuid4()
    module = registry.Module(
        slug="stick", path=path, doc={}, name="Stick", bound_guid=str(one),
        bound_name="Stick A", direction="source", claim={},
    )
    devices = [
        SimpleNamespace(name="Stick A", device_guid=one),
        SimpleNamespace(name="Stick B", device_guid=two),
    ]
    with (
        mock.patch.object(calibration, "physical_devices", lambda: devices),
        mock.patch.object(registry, "inputs", lambda: [module]),
        mock.patch.object(registry, "for_device", lambda *a, **k: module),
        mock.patch.object(
            store, "_write", lambda p, data, text=None: Path(p).write_bytes(data)
        ),
    ):
        rows = calibration._source_modules()
        # Both listed by device id, each by its own name (03 S100).
        assert sorted(r["name"] for r in rows) == ["Stick A", "Stick B"]
        assert {r["guid"] for r in rows} == {str(one), str(two)}
        keys = {r["name"]: r["key"] for r in rows}
        assert keys["Stick A"] == "stick"
        second = calibration.module_for_slug(keys["Stick B"])
        assert second is not None and second["guid"] == str(two)
        assert second["rebind"] is True
        assert calibration.write_axis(keys["Stick B"], 1, (-100, -5, 5, 100, True))
    assert json.loads(path.read_text())["calibration"]["1"] == [-100, -5, 5, 100, True]


# --- GL-071: the Button Map sees its file changed elsewhere ----------------------


def test_map_parts_change_with_the_map_and_photo_only(folder: Path) -> None:
    from gremlin.ui import module_model

    guid = str(next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    ).device_guid)
    path = _module(folder, "pjoy_pro", "pJoy Pro", guid, [1])
    watch = module_model.ModuleFileWatch()
    start = watch.mapParts("pJoy Pro", guid)
    assert start

    def edit(change: Callable[[dict], None]) -> str:
        doc = json.loads(path.read_text(encoding="utf-8"))
        change(doc)
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        return watch.mapParts("pJoy Pro", guid)

    # Claims, calibration and the map's ui block are not the map's parts.
    assert edit(lambda d: d.update(claim={"buttons": [1, 2]})) == start
    assert edit(lambda d: d.update(ui={"grid": 4})) == start
    # The map and the photo are (History Restore, Device Pack, Module Setup).
    moved = edit(lambda d: d.update(nodes=[{"hwId": 1}]))
    assert moved != start
    assert edit(lambda d: d.update(image="pjoy_pro/photo.png")) != moved
    path.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    assert watch.mapParts("pJoy Pro", guid) == ""


def test_button_map_asks_before_writing_over_a_change_and_follows_one() -> None:
    qml = (_ROOT / "qml" / "DialogJoystickButtonMap.qml").read_text(encoding="utf-8")
    assert "ModuleFileWatch { id: _fileWatch }" in qml
    # In Edit, Save asks Keep Mine / Take Theirs (07 Q6; glossary D15).
    assert '"Keep Mine", "Take Theirs"' in qml
    # Outside Edit, the map follows the file.
    assert "_buttonMap.loadLive(true)" in qml


# --- GL-078 / GL-089: Module Setup's photo ---------------------------------------


def _function(qml: str, name: str) -> str:
    start = qml.index(f"function {name}(")
    end = qml.index("\n    function ", start + 1)
    return qml[start:end]


def test_module_setup_keeps_the_photo_to_put_back_and_saves_once() -> None:
    qml = (_ROOT / "qml" / "DialogConfigureModule.qml").read_text(encoding="utf-8")
    # 03 Q3: Save Module no longer copies the photo again (one write, no
    # new library copy per Save).
    commit = _function(qml, "commitModule")
    assert "keepPhoto" not in commit and "copyImage" not in commit
    assert "dropPhotoStash()" in commit
    # 03 Q2: Import Image keeps the starting photo first; Discard puts it
    # back.
    dialog = qml[qml.index("id: _imageDialog"):]
    assert dialog.index("_win.stashPhoto()") < dialog.index("_hw.copyImage(")
    gate = qml[qml.index("id: _saveGate"):]
    assert "_win.putPhotoBack()" in gate[:gate.index("onCancelled")]
