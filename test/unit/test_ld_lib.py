# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device as a built-in input with its own module file
(D-04-LD-FILE): listed under the Device Library's Built-in inputs (10 S6,
03 S90b), its module file imported with no plugged-in check (10 S55, by
class), the Logical Device read again whenever its file is replaced
(Restore, Import, Undo, History Restore), and always a card on Home
(03 S71). The real store in an empty modules folder."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import config, logical_device_file
from gremlin import device_library as library
from gremlin.logical_device import LogicalDevice
from gremlin.modules import device_class, ids, module_file, registry, store
from gremlin.ui import module_model
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
)

LD_GUID = "{" + str(ids.LOGICAL_DEVICE).upper() + "}"
STICK_GUID = "{6C3D1E20-1111-2222-3333-444455556666}"

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    return request.getfixturevalue(folder.__name__)


@pytest.fixture
def rows() -> Iterator[LogicalDevice]:
    """The Logical Device, put back as it was afterwards."""
    device = LogicalDevice()
    kept = device.to_dict()
    yield device
    device.load_dict(kept)


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


def _doc(name: str, guid: str, layout: dict | None = None) -> dict:
    doc: dict = {"kind": "control.hardware", "device": name, "nodes": [], "claim": {}}
    if guid:
        doc["boundGuidLocal"] = guid
    if layout is not None:
        doc[logical_device_file.KEY] = layout
    return doc


def _write(path: Path, doc: dict) -> None:
    module_file.write_bytes(path, json.dumps(doc).encode("utf-8"))


def _labels(device: LogicalDevice) -> list[str]:
    return [c["label"] for c in device.to_dict()["controls"]]


# --- Device Library: Built-in inputs (10 S6, 03 S90b) -----------------------


def test_logical_device_is_a_library_built_in() -> None:
    assert device_class.can("library_builtin", ids.LOGICAL_DEVICE)
    assert library.is_built_in_guid(LD_GUID)
    # Still no copy, swap or calibrate, and still always present.
    for action in ("copy", "swap", "calibrate"):
        assert not device_class.can(action, ids.LOGICAL_DEVICE)
    assert device_class.can("always_present", ids.LOGICAL_DEVICE)


def test_logical_device_listed_under_built_in_inputs(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library, "_connected", lambda: [])
    layout = _doc("Logical Device", LD_GUID, _layout("A"))
    _write(modules / "logical_device.json", layout)
    _write(modules / "stick_a.json", _doc("Stick A", STICK_GUID))
    module = next(m for m in registry.modules() if m.slug == "logical_device")
    assert registry.is_built_in_input(module)
    rows = library.devices()
    names = [r["name"] for r in rows]
    assert names[0] == "Stick A"
    ld = next(r for r in rows if r["name"] == "Logical Device")
    assert ld["builtIn"] is True
    assert ld["state"] == "builtin"
    # Remove from Library is refused for it, as for Keyboard and OSC.
    assert library.remove_device(ld["key"])["ok"] is False


# --- Import: no plugged-in check for built-ins without hardware (10 S55) ---


def test_import_onto_the_logical_device_skips_the_plugged_in_check_and_reloads(
    modules: Path, rows: LogicalDevice, tmp_path: Path
) -> None:
    rows.load_dict(_layout("Old"))
    src = tmp_path / "picked" / "other_layout.json"
    src.parent.mkdir()
    _write(src, _doc("Logical Device", LD_GUID, _layout("Throttle", "Fire")))
    message = store.import_file(
        "Logical Device", LD_GUID, str(src), "source", "Device Library"
    )
    assert message.startswith("Imported into logical_device.json"), message
    written = json.loads(logical_device_file.path().read_text(encoding="utf-8"))
    assert [c["label"] for c in written[logical_device_file.KEY]["controls"]] == [
        "Throttle", "Fire"]
    # The Logical Device now shows the imported layout, not the old one.
    assert _labels(rows) == ["Throttle", "Fire"]
    assert not rows.dirty


def test_import_onto_an_unplugged_stick_is_still_checked(
    modules: Path, tmp_path: Path
) -> None:
    src = tmp_path / "stick.json"
    _write(src, _doc("Stick A", STICK_GUID))
    message = store.import_file(
        "Stick A", STICK_GUID, str(src), "source", "Device Library"
    )
    assert "not connected" in message


# --- Restore / Undo / History Restore read the file again -------------------


def test_replacing_the_logical_device_file_reloads_it(
    modules: Path, rows: LogicalDevice
) -> None:
    rows.load_dict(_layout("Before"))
    data = json.dumps(_doc("Logical Device", LD_GUID, _layout("Restored"))).encode()
    store.replace(logical_device_file.path(), data, "Device Library", force=True)
    assert _labels(rows) == ["Restored"]
    text = json.dumps(_doc("Logical Device", LD_GUID, _layout("From History")))
    store.write_text(logical_device_file.path(), text, "History")
    assert _labels(rows) == ["From History"]


def test_replacing_another_file_leaves_the_logical_device(
    modules: Path, rows: LogicalDevice
) -> None:
    rows.load_dict(_layout("Mine"))
    data = json.dumps(_doc("Stick A", STICK_GUID)).encode()
    store.replace(modules / "stick_a.json", data, "Device Library", force=True)
    assert _labels(rows) == ["Mine"]


# --- Home always shows the Logical Device card (03 S71) ---------------------


def test_logical_device_card_shows_without_a_file(modules: Path) -> None:
    assert not logical_device_file.path().exists()
    config.Configuration().set(
        module_model._CFG_SECTION,
        module_model._CFG_GROUP,
        module_model._CFG_SHOW_STUBS,
        False,
    )
    card = module_model.ModuleListModel().cardMap("logical")
    assert card.get("name") == "Logical Device"
    assert card.get("direction") == "source"
