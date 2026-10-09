# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Pack window, off-screen (device_pack_window_smoke.py).

Export lists the device's modes (all ticked) and takes a name and a note.
Import shows who made the pack, keeps its list below Open All when every
section is open (it used to draw over the buttons), warns before it
replaces anything (with the option to create missing Logical Device
inputs), and offers Undo Import afterwards. Two identical sticks are two
rows; Export sends the chosen one's id, and Import onto the "(2)" row
sends its id and changes only that stick's module file (08 S106a).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


def _smoke(home: pathlib.Path, part: str = "") -> dict:
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
        GREMLIN_PACK_PART=part,
    )
    args = [sys.executable, "test/unit/device_pack_window_smoke.py"]
    if os.environ.get("GREMLIN_SHOT"):
        args.append(os.environ["GREMLIN_SHOT"] + part)
    result = subprocess.run(
        args,
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _smoke(tmp_path_factory.mktemp("home"))


@pytest.fixture(scope="module")
def twins(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _smoke(tmp_path_factory.mktemp("home"), "twins")


def _key(guid: object) -> str:
    return str(guid or "").strip("{}").lower()


def test_export_lists_the_modes_and_takes_notes(run: dict) -> None:
    assert run["export-modes"] == [
        {"name": "Combat", "count": 1},
        {"name": "Default", "count": 2},
    ]
    options = dict(run["export-options"])
    # The chosen row's id goes with it (08 S106a).
    assert options.pop("guid")
    assert options == {
        "modes": ["Default"],
        "author": "Sam",
        "note": "My setup",
    }
    assert run["show-folder-hidden"] is True


def test_import_shows_who_made_it(run: dict) -> None:
    assert run["notes"].startswith("By Sam")
    assert run["notes"].endswith("My setup")
    assert run["sections"][:3] == ["Input module", "Map settings", "Wires"]


def test_the_list_stays_in_its_own_area(run: dict) -> None:
    assert run["list-below-buttons"] is True
    assert run["import-below-list"] is True


def test_the_warning_says_what_is_replaced(run: dict) -> None:
    warning = run["warning"]
    assert "Import replaces these on pJoy Pro:" in warning
    assert (
        "The wires and actions of pJoy Pro in Default: 3 here, 2 from the pack."
        in warning
    )
    assert "Logical Device inputs that don't exist here: Button 9" in warning
    assert "The previous module file is kept in the imported folder." in warning
    assert "The profile changes on disk only when you save it." in warning
    assert run["create-logical-shown"] is True


def test_replace_then_undo(run: dict) -> None:
    assert "Replaced the wires of pJoy Pro in Default" in run["status-after"]
    assert run["undo-shown"] is True
    assert run["default-after"] == [1, 5]
    assert run["logical-created"] is True
    assert run["default-undone"] == [1, 3, 5]
    assert run["status-undone"].startswith("Undid the import.")
    assert run["undo-hidden"] is True


def test_a_failed_import_keeps_undo_import(run: dict) -> None:
    # The backend keeps the earlier import; the button has to stay with it.
    assert "could not be written" in run["status-failed"]
    assert run["backend-undo-after-failed"] is True
    assert run["undo-after-failed"] is True
    # And Undo Import still puts back the first import.
    assert run["default-undone"] == [1, 3, 5]


def test_a_missing_driver_is_told_before_import(run: dict) -> None:
    assert run["drivers-shown"] is True
    assert run["drivers"].startswith("vJoy is not installed or not running:")
    assert "vJoy is not installed or not running:" in run["warning"]


def test_messages_are_on_the_shared_message_line(run: dict) -> None:
    # 01 S142: the import's report with an Undo Import link; a failure red.
    after = run["message-after"]
    assert after["shown"] and not after["failed"]
    assert after["text"] == run["status-after"]
    assert after["undo"] == "Undo Import"
    failed = run["message-failed"]
    assert failed["failed"] and failed["text"] == run["status-failed"]
    assert failed["undo"] == ""
    undone = run["message-undone"]
    assert undone["text"].startswith("Undid the import.") and not undone["failed"]


def test_the_choosers_open_in_the_last_device_pack_folder(run: dict) -> None:
    # 01 S143: picked in Open, Export opens there too (same kind).
    got = run["remembered"].rstrip("/").lower()
    assert got == run["remembered-want"].rstrip("/").lower()


def test_twins_are_two_rows_and_export_sends_the_chosen_id(twins: dict) -> None:
    # 08 S106a: identical sticks are separate rows named as on Home, and
    # Export exports the chosen row's device by its id.
    first, second = twins["twin-ids"]
    rows = twins["twin-rows"]
    assert sorted(_key(r["guid"]) for r in rows) == sorted([_key(first), _key(second)])
    assert [r["name"] for r in rows] == ["pJoy Pro", "pJoy Pro"]
    assert sorted(r["label"] for r in rows) == ["pJoy Pro", "pJoy Pro (2)"]
    assert "pJoy Pro (2)" in twins["twin-shown"]
    assert twins["twin-second-index"] >= 0
    chosen = _key(twins["twin-second-guid"])
    assert chosen in {_key(first), _key(second)}
    assert _key(twins["twin-options"]["guid"]) == chosen
    # The preview is the chosen stick's: only it has wires in "Twin".
    assert twins["twin-preview-modes"] == [{"name": "Twin", "count": 1}]
    assert twins["twin-kept"] is True
    assert twins["twin-export"]["ok"] is True, twins["twin-export"]
    assert _key(twins["twin-pack-guid"]) == chosen


def test_import_onto_the_second_twin_goes_by_its_id(twins: dict) -> None:
    # 08 S106a: the "Put this pack on" row's id decides which twin gets it.
    assert twins["twin-import-shown"] == "pJoy Pro (2)"
    chosen = _key(twins["twin-second-guid"])
    assert _key(twins["twin-selection"].get("targetGuid")) == chosen
    assert twins["twin-first-unchanged"] is True, twins["twin-import-status"]
    # The pack's checked control (1) is added to the second stick's own (9).
    assert twins["twin-second-buttons"] == [1, 9], twins["twin-import-status"]
