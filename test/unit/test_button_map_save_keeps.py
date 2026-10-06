# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map Save keeps what it doesn't write; Cancel writes safely.

Save rewrote the module file and kept only claims, names, Appearance and
the binding, so a device's calibration (saved in the same file) was lost at
the next Button Map Save (G-BMCALIB). Cancel put the photo back with a raw
write: no damage check, not atomic (G-PHOTORAW); it now writes as Choose
Photo does.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from gremlin.modules import module_file, store
from gremlin.ui import hardware_profile


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    monkeypatch.setattr(
        store,
        "slug_for",
        lambda name, guid="": name.lower().replace(" ", "_"),
    )
    return tmp_path


def test_save_keeps_calibration_and_other_keys(maps: pathlib.Path) -> None:
    path = maps / "stick_r.json"
    path.write_text(
        json.dumps(
            {
                "device": "Stick R",
                "claim": {"buttons": [1], "axes": [1], "hats": []},
                "calibration": {"1": [-32768, -10, 10, 32767, True]},
                "catalog": {"rowHeight": 40},
                "laterKey": {"kept": True},
                "nodes": [{"id": "old"}],
            }
        ),
        encoding="utf-8",
    )
    payload = {
        "kind": "control.hardware",
        "device": "Stick R",
        "image": "",
        "photo": {},
        "ui": {},
        "nodes": [{"id": "new"}],
    }
    assert hardware_profile.HardwareProfile().save("Stick R", json.dumps(payload))
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["calibration"] == {"1": [-32768, -10, 10, 32767, True]}
    assert saved["catalog"] == {"rowHeight": 40}
    assert saved["laterKey"] == {"kept": True}
    assert saved["claim"]["axes"] == [1]
    # What the Button Map writes is its own.
    assert saved["nodes"] == [{"id": "new"}]


def _stash(maps: pathlib.Path, slug: str, image: str) -> None:
    stash = maps / "cache" / "photo-stash" / slug
    stash.mkdir(parents=True)
    (stash / "manifest.json").write_text(
        json.dumps({"files": [], "image": image}), encoding="utf-8"
    )


def test_cancel_puts_the_photo_back_through_the_module_file_writer(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = maps / "stick_r.json"
    path.write_text(
        json.dumps({"device": "Stick R", "image": "new.png"}), encoding="utf-8"
    )
    _stash(maps, "stick_r", "stick_r/photo.png")
    writes = []
    # Every module file write goes through the store to the atomic writer.
    real = module_file.write_bytes
    monkeypatch.setattr(
        module_file,
        "write_bytes",
        lambda p, data: (writes.append(p), real(p, data)),
    )
    assert hardware_profile.HardwareProfile().restorePhoto("Stick R")
    assert writes == [path]
    assert json.loads(path.read_text(encoding="utf-8"))["image"] == "stick_r/photo.png"


def test_cancel_leaves_a_damaged_module_file_alone(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = maps / "stick_r.json"
    path.write_text("{ damaged", encoding="utf-8")
    _stash(maps, "stick_r", "stick_r/photo.png")
    told = []
    monkeypatch.setattr(
        module_file, "report_refused", lambda damaged: told.append(damaged)
    )
    hardware_profile.HardwareProfile().restorePhoto("Stick R")
    assert path.read_text(encoding="utf-8") == "{ damaged"
    assert len(told) == 1
