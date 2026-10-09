# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Restore of a built-in input's saved setup (10 S6, S6a, D-04-LD-FILE):
Keyboard, OSC and the Logical Device are always there, so Restore skips the
plugged-in check and Copy's built-in refusal; it autosaves first, is one
change for Undo and one History entry, and the Logical Device reloads. The
real Library, store and History in an empty modules folder."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_library as library
from gremlin import history, library_copy, logical_device_file
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids, module_file, store
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    settle_history,
)


def _g(uid: object) -> str:
    return "{" + str(uid).upper() + "}"


LD_GUID = _g(ids.LOGICAL_DEVICE)
STICK_GUID = "{11111111-2222-3333-4444-555555555555}"

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Path:
    # No stick plugged in.
    monkeypatch.setattr(library, "_connected", lambda: [])
    return request.getfixturevalue(folder.__name__)


@pytest.fixture
def rows() -> Iterator[LogicalDevice]:
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
    doc: dict = {
        "kind": "control.hardware",
        "device": name,
        "boundGuidLocal": guid,
        "nodes": [],
        "claim": {},
    }
    if layout is not None:
        doc[logical_device_file.KEY] = layout
    return doc


def _labels(device: LogicalDevice) -> list[str]:
    return [c["label"] for c in device.to_dict()["controls"]]


def _save(name: str, guid: str) -> dict:
    out = library.save_setup(name, guid, [])
    assert out["ok"], out
    return (out.get("setups") or [out.get("setup")])[0]


def _ld_entries() -> list[dict]:
    settle_history()
    return [
        e
        for e in history.entries("modules")
        if (e.get("subject") or {}).get("fileName") == "logical_device.json"
    ]


def test_restore_of_the_logical_device_skips_the_plugged_in_check(
    modules: Path, rows: LogicalDevice
) -> None:
    path = logical_device_file.path()
    module_file.write_bytes(
        path, json.dumps(_doc("Logical Device", LD_GUID, _layout("Saved"))).encode()
    )
    rows.load_dict(_layout("Saved"))
    setup = _save("Logical Device", LD_GUID)
    changed = _doc("Logical Device", LD_GUID, _layout("Changed", "Later"))
    store.replace(path, json.dumps(changed).encode(), "Home", force=True)
    assert _labels(rows) == ["Changed", "Later"]
    before = len(_ld_entries())

    out = library_copy.restore_to_stick(setup["key"])

    assert out["ok"], out
    # The layout is back in the file and the Logical Device reloaded it.
    written = json.loads(path.read_text(encoding="utf-8-sig"))
    assert [c["label"] for c in written[logical_device_file.KEY]["controls"]] == [
        "Saved"
    ]
    assert _labels(rows) == ["Saved"]
    # Autosaved first, one change for Undo, one History entry.
    assert out["autosaves"]
    names = [
        s.get("name") for d in library.devices() for s in d.get("setups") or []
    ]
    assert any(str(n).startswith("Autosave: before Restore of") for n in names)
    last = library.last_change()
    assert last and last.get("op") == "copy"
    assert str(last.get("label") or "").startswith("Restore ")
    assert len(_ld_entries()) == before + 1


@pytest.mark.parametrize(
    ("name", "uid"), [("Keyboard", ids.KEYBOARD), ("OSC", ids.OSC)]
)
def test_restore_of_keyboard_and_osc_is_not_refused(
    modules: Path, name: str, uid: object
) -> None:
    guid = _g(uid)
    module_file.write_bytes(
        modules / f"{name.lower()}.json", json.dumps(_doc(name, guid)).encode()
    )
    setup = _save(name, guid)
    out = library_copy.restore_to_stick(setup["key"])
    assert out["ok"], out
    assert "plugged in" not in str(out.get("error") or "")


def test_restore_to_an_unplugged_stick_is_still_refused(modules: Path) -> None:
    module_file.write_bytes(
        modules / "stick_a.json", json.dumps(_doc("Stick A", STICK_GUID)).encode()
    )
    found = {
        "key": "dev",
        "guid": STICK_GUID,
        "name": "Stick A",
        "setups": [{"key": "s1", "name": "Mine", "holds": ["bindings"]}],
    }
    real = library.devices
    try:
        library.devices = lambda: [found]  # type: ignore[assignment]
        out = library_copy.restore_to_stick("s1")
    finally:
        library.devices = real  # type: ignore[assignment]
    assert not out["ok"]
    assert "isn't plugged in" in out["error"]


# --- the layout in the same write as the other parts (D-04-LD-FILE) ---------


def _ld_file_labels() -> list[str]:
    doc = json.loads(logical_device_file.path().read_text(encoding="utf-8-sig"))
    return [c["label"] for c in doc[logical_device_file.KEY]["controls"]]


def _set_layout(labels: tuple[str, ...]) -> None:
    def change(doc: dict) -> None:
        doc[logical_device_file.KEY] = _layout(*labels)

    assert store.update_path(logical_device_file.path(), change, "Home")


def test_restore_of_picture_and_layout_is_one_history_entry(
    modules: Path, rows: LogicalDevice
) -> None:
    from test.unit.test_ld_card_image_carry import (  # pyright: ignore[reportMissingImports]
        PNG,
        _clear_photo,
        _image_key,
        _set_photo,
    )

    path = logical_device_file.path()
    module_file.write_bytes(
        path, json.dumps(_doc("Logical Device", LD_GUID, _layout("Saved"))).encode()
    )
    rows.load_dict(_layout("Saved"))
    _set_photo()
    setup = _save("Logical Device", LD_GUID)
    _clear_photo()
    _set_layout(("Changed", "Later"))
    rows.load_dict(_layout("Changed", "Later"))
    before = len(_ld_entries())

    out = library_copy.restore_to_stick(setup["key"])

    assert out["ok"], out
    assert _ld_file_labels() == ["Saved"]
    assert _labels(rows) == ["Saved"]
    assert _image_key()
    found = store.photo_files(logical_device_file.SLUG)
    assert found and found[0].read_bytes() == PNG
    assert len(_ld_entries()) == before + 1


def test_import_device_pack_carries_the_layout(
    modules: Path, rows: LogicalDevice, tmp_path: Path
) -> None:
    from gremlin.ui import device_pack

    path = logical_device_file.path()
    module_file.write_bytes(
        path,
        json.dumps(_doc("Logical Device", LD_GUID, _layout("Packed", "Two"))).encode(),
    )
    setup = _save("Logical Device", LD_GUID)
    pack = tmp_path / "ld.zip"
    pack.write_bytes(library.pack_path(setup["key"]).read_bytes())
    _set_layout(("Here",))
    rows.load_dict(_layout("Here"))
    ids_ = device_pack.pack_item_ids(pack)
    assert isinstance(ids_, dict)
    assert "in.logical" in ids_["input"]
    before = len(_ld_entries())

    # File > Import Device Pack… with its rows ticked as the window shows them.
    out = device_pack.apply_zip(
        pack, "Logical Device", {"items": ids_["input"]}, target_guid=LD_GUID
    )

    assert out["ok"], out
    assert _ld_file_labels() == ["Packed", "Two"]
    assert _labels(rows) == ["Packed", "Two"]
    assert len(_ld_entries()) == before + 1
