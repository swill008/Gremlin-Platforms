# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map > File > History filter (08 Q15, decided as recommended).

The window filters by the device's own module file name and every area, so
twin sticks (same name, different files) stay apart and a save that also
changed claims (filed under Module files) still shows. Show All (the window
keeps only the area) widens it again. Drives the real HistoryModel over
entries written to a temporary History store, with the filter object
DialogJoystickButtonMap.qml builds.
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

_QML = Path(__file__).resolve().parents[2] / "qml" / "DialogJoystickButtonMap.qml"


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


def _module(area: str, title: str, device: str, file_name: str, parts: list) -> None:
    # The subject history_modules.py writes for a module file save.
    history.write_now(
        area,
        title,
        {
            "device": device,
            "file": f"C:/modules/{file_name}",
            "fileName": file_name,
            "parts": parts,
        },
        {"text": "{}", "pictures": []},
        {"text": "{}", "pictures": []},
        "save",
    )


@pytest.fixture
def model(store: Path) -> history_model.HistoryModel:
    # Twin sticks: one name, two files.
    _module("button-map", "Left map", "Twin Stick", "twin-stick.json", ["map"])
    _module(
        "modules",
        "Left map and claims",
        "Twin Stick",
        "twin-stick.json",
        ["claims", "map"],
    )
    _module("button-map", "Right map", "Twin Stick", "twin-stick-2.json", ["map"])
    _module("button-map", "Throttle map", "Throttle", "throttle.json", ["map"])
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


def _window_filter(file_name: str) -> str:
    # As DialogJoystickButtonMap.qml's File > History builds it.
    return json.dumps({"fileName": file_name})


_ALL = {
    "Left map",
    "Left map and claims",
    "Right map",
    "Throttle map",
    "Saved profile",
    "Changed A",
}


def test_window_builds_a_file_name_filter_with_no_area() -> None:
    text = _QML.read_text(encoding="utf-8")
    found = re.search(
        r'text:\s*"History".*?filter:\s*JSON\.stringify\((\{.*?\})\)', text, re.S
    )
    assert found, "File > History not found in DialogJoystickButtonMap.qml"
    built = found.group(1)
    assert "fileName: _hw.moduleFileName(" in built
    assert "area" not in built and "device" not in built


def test_filter_shows_this_files_entries_in_every_area(
    model: history_model.HistoryModel,
) -> None:
    model.setFilter(_window_filter("twin-stick.json"))
    assert _titles(model) == {"Left map", "Left map and claims"}


def test_twin_sticks_stay_apart(model: history_model.HistoryModel) -> None:
    model.setFilter(_window_filter("twin-stick-2.json"))
    assert _titles(model) == {"Right map"}


def test_file_name_matches_however_cased(model: history_model.HistoryModel) -> None:
    model.setFilter(_window_filter("Twin-Stick.JSON"))
    assert _titles(model) == {"Left map", "Left map and claims"}


def test_show_all_widens_to_everything(model: history_model.HistoryModel) -> None:
    model.setFilter(_window_filter("twin-stick.json"))
    # Show All in DialogHistory.qml keeps only the area; there is none here.
    model.setFilter("")
    assert _titles(model) == _ALL


def test_area_picked_then_show_all_keeps_the_area(
    model: history_model.HistoryModel,
) -> None:
    # Picking Button Map in the window adds the area to the file filter.
    model.setFilter(json.dumps({"fileName": "twin-stick.json", "area": "button-map"}))
    assert _titles(model) == {"Left map"}
    model.setFilter(json.dumps({"area": "button-map"}))
    assert _titles(model) == {"Left map", "Right map", "Throttle map"}
