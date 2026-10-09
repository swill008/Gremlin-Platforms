# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Pack Export by the chosen row's id (08 S106a): with two identical
sticks, the window's options carry the row's "guid" and the export takes that
stick's id and its own module file. Without an id the name-only refusal
stays as a guard."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from gremlin.modules import store
from gremlin.ui import device_pack, hardware_profile
from test.unit import test_stage1_modules
from test.unit.test_id_not_name_lookups import FIRST, SECOND, TWIN, twins
from test.unit.test_stage1_history_pack import _url

_app = test_stage1_modules._app
folder = test_stage1_modules.folder
_ = twins

WAIT_MS = 10000


def _write_own_files() -> None:
    """Each twin's own file, told apart by a marker."""
    for guid, marker in ((str(FIRST), "first"), (str(SECOND), "second")):
        doc = {
            "kind": "control.hardware",
            "device": TWIN,
            "direction": "source",
            "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
            "twinMarker": marker,
        }
        path = store.path_for_id(TWIN, guid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")


def _map(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        return json.loads(zf.read("map.json"))


def test_export_with_the_second_twins_id_exports_it(
    folder: Path, twins: None, tmp_path: Path
) -> None:
    """Old code ignored "guid" and refused the shared name."""
    _write_own_files()
    hw = hardware_profile.HardwareProfile()
    dest = tmp_path / "second.zip"
    done = json.loads(
        hw.exportPack(TWIN, _url(dest), json.dumps({"guid": str(SECOND)}))
    )
    assert done["ok"], done
    packed = _map(dest)
    assert packed["pack"]["exportedGuid"] == str(SECOND)
    assert packed["twinMarker"] == "second"


def test_async_export_with_the_second_twins_id_exports_it(
    folder: Path, twins: None, tmp_path: Path, qtbot: object
) -> None:
    _write_own_files()
    hw = hardware_profile.HardwareProfile()
    dest = tmp_path / "second_async.zip"
    with qtbot.waitSignal(hw.packExported, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        started = json.loads(
            hw.exportPackAsync(TWIN, _url(dest), json.dumps({"guid": str(SECOND)}))
        )
        assert started["ok"], started
    assert json.loads(blocker.args[0])["ok"]
    packed = _map(dest)
    assert packed["pack"]["exportedGuid"] == str(SECOND)
    assert packed["twinMarker"] == "second"


@pytest.mark.parametrize("options", ["{}", '{"guid": ""}'])
def test_export_without_an_id_keeps_the_twins_refusal(
    folder: Path, twins: None, tmp_path: Path, options: str
) -> None:
    _write_own_files()
    hw = hardware_profile.HardwareProfile()
    done = json.loads(hw.exportPack(TWIN, _url(tmp_path / "x.zip"), options))
    assert not done["ok"]
    assert f"More than one device is called {TWIN}" in done["error"]
    started = json.loads(hw.exportPackAsync(TWIN, _url(tmp_path / "y.zip"), options))
    assert not started["ok"]
    assert f"More than one device is called {TWIN}" in started["error"]


def test_a_twin_rows_label_reaches_the_pack_list(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window shows the row's label (Home's name for that id, 08 S106a);
    old code replaced it with the bare device name."""
    rows = [
        {"name": TWIN, "guid": str(FIRST), "hasFile": False, "label": TWIN},
        {"name": TWIN, "guid": str(SECOND), "hasFile": False,
         "label": f"{TWIN} (2)"},
    ]
    monkeypatch.setattr(store, "known_devices", lambda: [dict(r) for r in rows])
    labels = [row["label"] for row in device_pack.pack_devices()]
    assert labels == [TWIN, f"{TWIN} (2)"]


def test_a_damaged_twin_row_keeps_its_label(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = store.path_for_id(TWIN, str(SECOND))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    row = {"name": TWIN, "guid": str(SECOND), "hasFile": True,
           "label": f"{TWIN} (2)"}
    monkeypatch.setattr(store, "known_devices", lambda: [dict(row)])
    monkeypatch.setattr(store, "path_for", lambda _n, _g: path)
    (listed,) = device_pack.pack_devices()
    assert listed["label"] == f"{TWIN} (2) (file damaged)"
