# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor > File > History filter (08 Q15, decided as recommended).

The window filters by the device's id (deviceId, 08 S43; its name only for
an entry written before device folders) and every area, so twin sticks
(same name, different ids and folders) stay apart and a save that also
changed claims (filed under Module files) still shows. Show All (the window
keeps only the area) widens it again. Drives the real HistoryModel over
entries written to a temporary History store, with the filter object
DialogDeviceMappingEditor.qml builds.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history
from gremlin.ui import history_model

_QML = Path(__file__).resolve().parents[2] / "qml" / "DialogDeviceMappingEditor.qml"


def _settle() -> None:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    # Stamped recently, so nothing is old enough to prune.
    now = time.time() - 60
    monkeypatch.setattr(history.clock, "now", lambda: now)
    yield tmp_path
    _settle()


LEFT_ID = "AAAA0001"
RIGHT_ID = "AAAA0002"
THROTTLE_ID = "BBBB0001"


def _module(
    area: str, title: str, device: str, device_id: str, folder: str, parts: list
) -> None:
    # The subject history_modules.py writes for a module file save.
    subject = {
        "device": device,
        "folder": folder,
        "file": f"C:/modules/{folder}/module.json",
        "fileName": f"{folder}/module.json",
        "parts": parts,
    }
    if device_id:
        subject["deviceId"] = device_id
    history.write_now(
        area,
        title,
        subject,
        {"text": "{}", "pictures": []},
        {"text": "{}", "pictures": []},
        "save",
    )


@pytest.fixture
def model(store: Path) -> history_model.HistoryModel:
    # Twin sticks: one name, two ids and folders.
    _module(
        "device-mapping-editor",
        "Left map",
        "Twin Stick",
        LEFT_ID,
        "Twin Stick",
        ["map"],
    )
    _module(
        "modules",
        "Left map and claims",
        "Twin Stick",
        LEFT_ID,
        "Twin Stick",
        ["claims", "map"],
    )
    _module(
        "device-mapping-editor",
        "Right map",
        "Twin Stick",
        RIGHT_ID,
        "Twin Stick (2)",
        ["map"],
    )
    _module(
        "device-mapping-editor",
        "Throttle map",
        "Throttle",
        THROTTLE_ID,
        "Throttle",
        ["map"],
    )
    history.write_now(
        "profile",
        "Saved profile",
        {"profile": str(store / "One.xml")},
        None,
        None,
        "profile",
    )
    history.write_now("settings", "Changed A", {}, 1, 2, "save")
    m = history_model.HistoryModel()
    m.reload()
    return m


def _titles(m: history_model.HistoryModel) -> set[str]:
    return {e["title"] for e in m._rows}


def _window_filter(device_id: str, device_name: str = "Twin Stick") -> str:
    # As DialogDeviceMappingEditor.qml's File > History builds it.
    return json.dumps({"deviceId": device_id, "deviceName": device_name})


_ALL = {
    "Left map",
    "Left map and claims",
    "Right map",
    "Throttle map",
    "Saved profile",
    "Changed A",
}


def test_window_builds_a_device_id_filter_with_no_area() -> None:
    text = _QML.read_text(encoding="utf-8")
    # File > History calls openHistory(), which builds the filter.
    assert re.search(
        r'text:\s*"History".*?onTriggered:\s*_editorWin\.openHistory\(\)', text, re.S
    )
    found = re.search(
        r'function openHistory\(\).*?filter:\s*JSON\.stringify\((\{.*?\})\)', text, re.S
    )
    assert found, "File > History not found in DialogDeviceMappingEditor.qml"
    built = found.group(1)
    assert "deviceId: _fileWatch.deviceIdFor(" in built
    assert "deviceName: targetName" in built
    assert "area" not in built and "fileName" not in built


def test_filter_shows_this_files_entries_in_every_area(
    model: history_model.HistoryModel,
) -> None:
    model.setFilter(_window_filter(LEFT_ID))
    assert _titles(model) == {"Left map", "Left map and claims"}


def test_twin_sticks_stay_apart(model: history_model.HistoryModel) -> None:
    model.setFilter(_window_filter(RIGHT_ID))
    assert _titles(model) == {"Right map"}


def test_device_id_matches_however_written(
    model: history_model.HistoryModel,
) -> None:
    model.setFilter(_window_filter("aaaa0001"))
    assert _titles(model) == {"Left map", "Left map and claims"}


def test_an_entry_from_before_device_folders_matches_by_name(
    model: history_model.HistoryModel,
) -> None:
    _module(
        "device-mapping-editor", "Old throttle map", "Throttle", "", "throttle", ["map"]
    )
    model.reload()
    model.setFilter(_window_filter(THROTTLE_ID, "Throttle"))
    assert _titles(model) == {"Throttle map", "Old throttle map"}


def test_show_all_widens_to_everything(model: history_model.HistoryModel) -> None:
    model.setFilter(_window_filter(LEFT_ID))
    # Show All in DialogHistory.qml keeps only the area; there is none here.
    model.setFilter("")
    assert _titles(model) == _ALL


def test_area_picked_then_show_all_keeps_the_area(
    model: history_model.HistoryModel,
) -> None:
    # Picking Device Mapping Editor in the window adds the area to the file filter.
    model.setFilter(
        json.dumps(
            {
                "deviceId": LEFT_ID,
                "deviceName": "Twin Stick",
                "area": "device-mapping-editor",
            }
        )
    )
    assert _titles(model) == {"Left map"}
    model.setFilter(json.dumps({"area": "device-mapping-editor"}))
    assert _titles(model) == {"Left map", "Right map", "Throttle map"}
