# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup and device fixes from the code audit (AU-04, 05, 06, 22, 23,
24, 25, 61)."""

from __future__ import annotations

import json
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import device_initialization
from gremlin.modules import calibration, claim, registry

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _pjoy_guid() -> str:
    devices = device_initialization.physical_devices()
    return str(next(d for d in devices if d.name == "pJoy Pro").device_guid)


@pytest.fixture
def pjoy_folder_cleared(tmp_path: Path) -> Iterator[None]:
    """pJoy Pro's device folders earlier tests left (Module Setup saves make
    them) are put aside, so a test's own folder is its only one with that
    id, and put back afterwards; folders the test made are removed."""
    import shutil

    from gremlin.modules import store

    folder = store.folder()
    before = {p.name for p in folder.iterdir()} if folder.is_dir() else set()
    aside = tmp_path / "aside"
    aside.mkdir()
    for key, path in store.device_dirs().items():
        if key == _pjoy_key() or path.name.casefold() == "pjoy pro":
            shutil.move(str(path), str(aside / path.name))
    store._dirs_changed()
    try:
        yield
    finally:
        for path in list(folder.iterdir()) if folder.is_dir() else []:
            if path.name not in before and path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        for path in aside.iterdir():
            if not (folder / path.name).exists():
                shutil.move(str(path), str(folder / path.name))
        store._dirs_changed()


def _pjoy_key() -> str:
    from gremlin.modules.ids import guid_key

    return guid_key(_pjoy_guid())


@pytest.fixture
def setup() -> Iterator[Any]:
    from gremlin.ui.module_model import DriverInputModel

    model = DriverInputModel()
    yield model
    model.deleteLater()


def test_keyboard_saved_with_no_keys_passes_none() -> None:
    saved = claim.read_claim({"claim": {"keys": [], "keysChosen": True}})
    never = claim.read_claim({"claim": {"keys": []}})
    assert claim.claim_allows_key(saved, (30, False)) is False
    assert claim.claim_allows_key(never, (30, False)) is True


def test_keyboard_setup_shows_a_saved_empty_choice_unticked(setup: Any) -> None:  # noqa: ANN401
    setup._is_keyboard = lambda: True
    setup._load_keyboard({"keys": [], "keysChosen": True, "friendly": {}})
    assert setup._rows and not any(r["claimed"] for r in setup._rows)
    setup._load_keyboard({"keys": [], "friendly": {}})
    assert all(r["claimed"] for r in setup._rows)


def test_keyboard_undo_still_works_after_a_new_key_row(setup: Any) -> None:  # noqa: ANN401
    setup._is_keyboard = lambda: True
    setup._load_keyboard({"keys": [], "keysChosen": True, "friendly": {}})
    setup.setClaimed(0, True)
    count = setup.rowCount()
    # A key that isn't listed (scan code 0x7F, extended) is pressed.
    setup._on_key(types.SimpleNamespace(is_pressed=True, identifier=(0x7F, True)))
    assert setup.rowCount() == count + 1 and setup._rows[-1]["claimed"]
    setup.undo()
    assert not setup._rows[-1]["claimed"]
    setup.undo()
    assert not setup._rows[0]["claimed"]


def test_an_unplugged_xbox_pad_is_not_the_xbox_output(setup: Any) -> None:  # noqa: ANN401
    setup.loadDevice("{DEADBEEF-0000-0000-0000-000000000001}", "Controller (Xbox One)")
    assert setup.saveBlockedReason()  # refused: not connected
    assert not any(r.get("label") == "LB" for r in setup._rows)


@pytest.mark.usefixtures("pjoy_folder_cleared")
def test_save_writes_to_the_bound_file(setup: Any) -> None:  # noqa: ANN401
    # The stick's folder is found by its id (03 S130), whatever its name.
    import shutil

    from gremlin.modules import store
    from gremlin.modules.ids import stored_guid_key

    guid = _pjoy_guid()
    own = store.folder() / "Renamed Stick"
    own.mkdir(parents=True)
    (own / "device.json").write_text(
        json.dumps({"format": 1, "id": stored_guid_key(guid), "name": "Renamed Stick"}),
        encoding="utf-8",
    )
    store._dirs_changed()
    try:
        setup.loadDevice(guid, "pJoy Pro")
        setup.setClaimed(0, True)
        assert setup.saveClaim("pJoy Pro", "source")
        assert (own / "module.json").is_file()
    finally:
        shutil.rmtree(own, ignore_errors=True)
        store._dirs_changed()


@pytest.mark.usefixtures("pjoy_folder_cleared")
def test_an_input_module_stays_an_input_module(setup: Any) -> None:  # noqa: ANN401
    from gremlin.modules import store

    guid = _pjoy_guid()
    setup.loadDevice(guid, "pJoy Pro")
    setup.setClaimed(0, True)
    assert setup.saveClaim("pJoy Pro", "source")
    assert setup.saveClaim("pJoy Pro", "dest")  # the Output menu on an input
    path = store.module_file("pJoy Pro", guid)
    try:
        assert json.loads(path.read_text(encoding="utf-8"))["direction"] == "source"
    finally:
        path.unlink(missing_ok=True)


def test_calibration_with_low_above_high_is_not_used() -> None:
    assert calibration._as_tuple([100, 0, 0, -100, True]) is None
    assert calibration._as_tuple([-100, 50, 0, 100, True]) is None
    assert calibration._as_tuple([-100, 0, 0, 100, True]) == (-100, 0, 0, 100, True)
    # Without a center the center values aren't used.
    assert calibration._as_tuple([0, 0, 0, 100, False]) == (0, 0, 0, 100, False)


def _module(slug: str, guid: str, buttons: list[int]) -> registry.Module:
    doc = {"claim": {"buttons": buttons}}
    return registry.Module(
        slug=slug,
        path=Path(f"{slug}.json"),
        doc=doc,
        name="pJoy Pro",
        bound_guid=guid,
        bound_name="pJoy Pro",
        direction="source",
        claim=claim.read_claim(doc),
    )


def test_runtime_uses_the_module_setup_file_for_a_stick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import runtime
    from gremlin.modules.ids import guid_key

    guid = _pjoy_guid()
    stale = _module("old_copy", guid, [1])
    bound = _module("pjoy_pro", guid, [5])
    monkeypatch.setattr(registry, "modules", lambda: [stale])
    monkeypatch.setattr(registry, "for_device", lambda name, device_guid="": bound)
    gate = runtime.InputModuleRuntime()
    gate.reload()  # one shared instance: it may exist from an earlier test
    try:
        assert gate._claims[guid_key(guid)]["buttons"] == [5]
    finally:
        # The shared instance stays (deleting it broke later tests that use
        # it); it reads the real modules again.
        monkeypatch.undo()
        gate.reload()


@pytest.mark.usefixtures("pjoy_folder_cleared")
def test_a_stick_marked_as_an_output_is_repaired_by_saving(setup: Any) -> None:  # noqa: ANN401
    # The old Output menu bug left input sticks' files marked "dest".
    from gremlin.modules import store

    guid = _pjoy_guid()
    path = store.ensure_device_dir("pJoy Pro", guid) / "module.json"
    path.write_text(
        json.dumps(
            {
                "device": "pJoy Pro",
                "direction": "dest",
                "boundGuidLocal": guid,
                "claim": {"buttons": [1], "axes": [], "hats": []},
            }
        ),
        encoding="utf-8",
    )
    try:
        setup.loadDevice(guid, "pJoy Pro")
        assert setup.saveClaim("pJoy Pro", "source")
        assert json.loads(path.read_text(encoding="utf-8"))["direction"] == "source"
    finally:
        path.unlink(missing_ok=True)


def test_module_setup_run_and_calibration_use_the_same_file(tmp_path: Path) -> None:
    # A stick with a folder holding its id and a folder of its own name:
    # Module Setup used one, Run and Calibration the other (ticks did
    # nothing).
    import shutil

    from gremlin.modules import calibration, runtime, store
    from gremlin.modules.ids import guid_key, stored_guid_key

    guid = _pjoy_guid()
    folder = store.folder()
    files = {
        "Old Name": (stored_guid_key(guid), guid, [1, 2, 3]),
        "pJoy Pro": ("", "", [9]),
    }
    aside = tmp_path / "aside"
    aside.mkdir()
    for name in files:  # folders earlier tests left are put back afterwards
        if (folder / name).exists():
            shutil.move(str(folder / name), str(aside / name))
    for name, (ident, bound, buttons) in files.items():
        (folder / name).mkdir(parents=True)
        if ident:
            (folder / name / "device.json").write_text(
                json.dumps({"format": 1, "id": ident, "name": name}),
                encoding="utf-8",
            )
        (folder / name / "module.json").write_text(
            json.dumps(
                {
                    "device": name,
                    "direction": "source",
                    "boundGuidLocal": bound,
                    "claim": {"buttons": buttons, "axes": [1], "hats": [], "keys": []},
                }
            ),
            encoding="utf-8",
        )
    store._dirs_changed()
    try:
        setup = store.device_dir("pJoy Pro", guid).name
        assert setup == "Old Name"
        gate = runtime.InputModuleRuntime()
        gate.reload()
        assert gate._claims[guid_key(guid)]["buttons"] == files[setup][2]
        rows = {guid_key(r["guid"]): r["slug"] for r in calibration._source_modules()}
        assert rows[guid_key(guid)] == setup
    finally:
        for name in files:
            shutil.rmtree(folder / name, ignore_errors=True)
        for kept in aside.iterdir():
            shutil.move(str(kept), str(folder / kept.name))
        store._dirs_changed()


def test_calibration_window_picks_the_second_stick_on_a_shared_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # GL-088 (03 S100, S110): two sticks on one file are two entries in the
    # Calibration window's drop-down, each picked (and saved) by its own key.
    # The drop-down used the file's slug, so the second could not be picked.
    import uuid

    from gremlin.modules import store
    from gremlin.modules.ids import guid_key
    from gremlin.ui.module_calibration import CalibrationModuleModel

    path = tmp_path / "stick.json"
    path.write_text(json.dumps({"device": "Stick"}), encoding="utf-8")
    one, two = uuid.uuid4(), uuid.uuid4()
    module = registry.Module(
        slug="stick",
        path=path,
        doc={},
        name="Stick",
        bound_guid=str(one),
        bound_name="Stick A",
        direction="source",
        claim={},
    )
    devices = [
        types.SimpleNamespace(name="Stick A", device_guid=one),
        types.SimpleNamespace(name="Stick B", device_guid=two),
    ]
    monkeypatch.setattr(calibration, "physical_devices", lambda: devices)
    monkeypatch.setattr(registry, "for_device", lambda *a, **k: module)
    monkeypatch.setattr(
        store, "_write", lambda p, data, text=None: Path(p).write_bytes(data)
    )
    model = CalibrationModuleModel()
    try:
        roles = {bytes(v).decode(): k for k, v in model.roleNames().items()}
        assert "key" in roles
        entries = {
            model.data(model.index(i, 0), roles["name"]): model.data(
                model.index(i, 0), roles["key"]
            )
            for i in range(model.rowCount())
        }
        assert set(entries) == {"Stick A", "Stick B"}
        # A card opens Calibration by the file's slug: the first stick.
        assert entries["Stick A"] == "stick"
        assert entries["Stick B"] == f"stick@{guid_key(two)}"
        # Each stick's key picks its own row.
        assert list(entries.values()).count(entries["Stick B"]) == 1
        # The second stick's key saves to the shared file, recording its id.
        assert calibration.write_axis(entries["Stick B"], 1, (-100, -5, 5, 100, True))
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["calibration"]["1"] == [-100, -5, 5, 100, True]
        assert doc["boundGuidLocal"] == str(two)
    finally:
        model.deleteLater()
    # The window's drop-down picks rows by that key.
    qml = Path(__file__).resolve().parents[2] / "qml" / "DialogCalibration.qml"
    assert 'valueRole: "key"' in qml.read_text(encoding="utf-8")
