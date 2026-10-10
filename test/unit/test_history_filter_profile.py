# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""History window filter by profile (08 Q16, decided as recommended).

The Configuration row's History filters by that input, mode and the open
profile, so another profile's changes to the same input stay out; Show All
(the window keeps only the area) widens it again. Drives the real
HistoryModel over entries written to a temporary History store.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history
from gremlin.ui import history_model

_STICK = "44444444-5555-6666-7777-888888888888"


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


def _input(profile: Path, title: str, mode: str = "Default") -> None:
    history.write_now(
        "profile",
        title,
        {
            "profile": str(profile),
            "profileName": profile.name,
            "device": "Stick",
            "deviceId": _STICK,
            "inputType": "button",
            "inputId": 1,
            "mode": mode,
        },
        {"actions": []},
        {"actions": []},
        "input",
    )


@pytest.fixture
def model(store: Path) -> history_model.HistoryModel:
    one, two = store / "One.xml", store / "Two.xml"
    _input(one, "One: button 1")
    _input(one, "One: button 1 in Other", mode="Other")
    _input(two, "Two: button 1")
    history.write_now(
        "profile",
        "Saved One",
        {"profile": str(one), "profileName": one.name},
        None,
        None,
        "profile",
    )
    history.write_now(
        "modules", "Saved Stick", {"fileName": "stick.json"}, {}, {}, "save"
    )
    history.write_now("settings", "Changed A", {}, 1, 2, "save")
    m = history_model.HistoryModel()
    m.reload()
    return m


def _titles(m: history_model.HistoryModel) -> set[str]:
    return {e["title"] for e in m._rows}


def _row_filter(profile: Path) -> str:
    # As ConfigurationPage.qml historyFilter builds it.
    return json.dumps(
        {
            "deviceId": _STICK,
            "inputType": "button",
            "inputId": "1",
            "mode": "Default",
            "profile": str(profile),
        }
    )


_ALL = {
    "One: button 1",
    "One: button 1 in Other",
    "Two: button 1",
    "Saved One",
    "Saved Stick",
    "Changed A",
}


def test_no_filter_shows_every_entry(model: history_model.HistoryModel) -> None:
    assert _titles(model) == _ALL


def test_configuration_row_shows_only_the_open_profiles_input(
    model: history_model.HistoryModel, store: Path
) -> None:
    model.setFilter(_row_filter(store / "One.xml"))
    assert _titles(model) == {"One: button 1"}
    model.setFilter(_row_filter(store / "Two.xml"))
    assert _titles(model) == {"Two: button 1"}


def test_profile_path_matches_however_written(
    model: history_model.HistoryModel, store: Path
) -> None:
    written = str(store / "One.xml").upper().replace("\\", "/")
    model.setFilter(_row_filter(Path(written)))
    assert _titles(model) == {"One: button 1"}


def test_profile_alone_shows_that_profiles_entries_only(
    model: history_model.HistoryModel, store: Path
) -> None:
    model.setFilter(json.dumps({"profile": str(store / "One.xml")}))
    assert _titles(model) == {"One: button 1", "One: button 1 in Other", "Saved One"}


def test_show_all_and_clearing_widen_to_everything(
    model: history_model.HistoryModel, store: Path
) -> None:
    model.setFilter(_row_filter(store / "One.xml"))
    # Show All in DialogHistory.qml keeps only the area.
    model.setFilter(json.dumps({"area": "profile"}))
    assert _titles(model) == {
        "One: button 1",
        "One: button 1 in Other",
        "Two: button 1",
        "Saved One",
    }
    model.setFilter("")
    assert _titles(model) == _ALL
    assert json.loads(model.filterText) == {}
