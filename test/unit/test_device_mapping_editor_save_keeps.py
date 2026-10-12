# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor Save keeps what it doesn't write; Cancel writes safely.

Save rewrote the module file and kept only claims, names, Appearance and
the binding, so a device's calibration (saved in the same file) was lost at
the next Device Mapping Editor Save (G-BMCALIB). Cancel put the photo back with a raw
write: no damage check, not atomic (G-PHOTORAW); now the edit's pictures
wait in its temporary folder and Cancel never writes the module file
(07 S107).
"""

from __future__ import annotations

import json
import pathlib

import pytest

from gremlin.modules import module_file, store
from gremlin.ui import hardware_profile
from test.unit._device_folders import module_path, put_module


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    return tmp_path


def test_save_keeps_calibration_and_other_keys(maps: pathlib.Path) -> None:
    path = put_module(
        maps,
        "Stick R",
        {
            "device": "Stick R",
            "claim": {"buttons": [1], "axes": [1], "hats": []},
            "calibration": {"1": [-32768, -10, 10, 32767, True]},
            "layout": {"groups": ["G40"]},
            "laterKey": {"kept": True},
            "nodes": [{"id": "old"}],
        },
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
    assert saved["layout"]["groups"] == ["G40"]
    assert saved["laterKey"] == {"kept": True}
    assert saved["claim"]["axes"] == [1]
    # What the device map writes is its own.
    assert saved["nodes"] == [{"id": "new"}]


def _photo(maps: pathlib.Path) -> str:
    src = maps.parent / "chosen.png"
    src.write_bytes(b"png")
    return src.as_uri()


def test_cancel_never_writes_the_module_file(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = put_module(
        maps, "Stick R", {"device": "Stick R", "image": "pictures/old.png"}
    )
    before = path.read_bytes()
    writes = []
    real = module_file.write_bytes
    monkeypatch.setattr(
        module_file,
        "write_bytes",
        lambda p, data: (writes.append(p), real(p, data)),
    )
    profile = hardware_profile.HardwareProfile()
    profile.beginEditFor("Stick R", "")
    assert profile.copyImage(_photo(maps), "Stick R") == "pictures/photo.png"
    assert profile.cancelEdit("Stick R")
    assert path not in writes
    assert path.read_bytes() == before
    # The chosen photo waited in the edit and went with it.
    assert not (path.parent / "pictures" / "photo.png").exists()
    assert not profile.editActiveFor("Stick R", "")


def test_cancel_leaves_a_damaged_module_file_alone(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = put_module(maps, "Stick R", "{ damaged")
    told = []
    monkeypatch.setattr(
        module_file, "report_refused", lambda damaged: told.append(damaged)
    )
    profile = hardware_profile.HardwareProfile()
    profile.beginEditFor("Stick R", "")
    # A new photo (Import Image) into a damaged file is refused before
    # anything is kept.
    assert profile.copyImage(_photo(maps), "Stick R") == ""
    profile.cancelEdit("Stick R")
    assert path.read_text(encoding="utf-8") == "{ damaged"
    assert len(told) == 1
    assert module_path(maps, "Stick R") == path
