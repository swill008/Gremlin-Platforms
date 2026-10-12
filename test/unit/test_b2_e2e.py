# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Export / Import Device end to end (D-FIXLIST-B2, 08 S49-S114), off-screen
through the real main window and DialogDevicePack.qml (b2_e2e_smoke.py):
Tools › Export / Import Device and the Home card's Export Device… /
Import Device… open the one window on the right tab and device; Export
writes a .gmap carrying Made by, Note, the chosen modes and the output
modules' pictures; Import As a new device makes a "(2)" folder that Undo
Import removes; Import Onto an existing device merges after the warning
and Undo Import puts it back; no .zip anywhere."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]
NAME = "pJoy Pro"
TITLE = "Export / Import Device"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    result = proc_tree.run(
        [sys.executable, "test/unit/b2_e2e_smoke.py"],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT ") :])


def _ok(run: dict, step: str) -> None:
    assert step not in run["errors"], run["errors"][step]


# --- entry points ---------------------------------------------------------------


def test_tools_item_opens_the_window_on_export(run: dict) -> None:
    _ok(run, "tools")
    assert TITLE in run["tools-texts"]
    assert "Device Pack" not in run["tools-texts"]
    assert run["tools-title"] == TITLE
    assert run["tools-mode"] == "export"


def test_home_card_export_opens_the_export_tab_on_that_device(run: dict) -> None:
    _ok(run, "home")
    assert run["home-export-title"] == TITLE
    assert run["home-export-mode"] == "export"
    assert run["home-export-device"] == NAME


def test_home_card_import_opens_the_import_tab_for_that_device(run: dict) -> None:
    _ok(run, "home")
    assert run["home-import-title"] == TITLE
    assert run["home-import-mode"] == "import"
    assert any(NAME in shown for shown in run["home-import-target"])


def test_the_old_window_is_gone() -> None:
    assert not (_ROOT / "qml" / "DialogDeviceExport.qml").exists()
    assert not (_ROOT / "gremlin" / "ui" / "device_export.py").exists()
    for path in (_ROOT / "qml" / "StatusPage.qml", _ROOT / "joystick_gremlin.py"):
        text = path.read_text(encoding="utf-8")
        assert "DialogDeviceExport" not in text and "device_export" not in text, path


# --- no .zip anywhere -------------------------------------------------------------


def test_choosers_and_default_name_are_gmap_only(run: dict) -> None:
    _ok(run, "tools")
    assert run["save-filters"] == ["Device files (*.gmap)"]
    assert run["save-suffix"] == "gmap"
    assert run["pick-filters"] and all(".zip" not in f for f in run["pick-filters"])
    assert any(".gmap" in f for f in run["pick-filters"])
    assert run["default-url"].endswith(".gmap")


def test_no_zip_writer_remains() -> None:
    for rel in ("gremlin/ui/device_pack.py", "gremlin/ui/hardware_profile.py"):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert '".zip"' not in text and "'.zip'" not in text, rel
    qml = (_ROOT / "qml" / "DialogDevicePack.qml").read_text(encoding="utf-8")
    assert "*.zip" not in qml and "Choose Zip" not in qml


# --- export -----------------------------------------------------------------------


def test_export_writes_a_gmap_with_made_by_note_and_chosen_modes(run: dict) -> None:
    _ok(run, "export")
    assert run["export-device"] == NAME
    assert run["export-written"] is True
    assert run["zip-written"] == []
    label = run["gmap-label"]
    assert label["madeBy"] == "Sam"
    assert label["note"] == "My setup"
    assert label["modes"] == ["Default"]
    assert "Combat" not in run["gmap-wire-modes"]
    assert run["read-gmap"]["madeBy"] == "Sam"
    assert run["read-gmap"]["note"] == "My setup"
    assert run["read-gmap"]["modes"] == ["Default"]


def test_export_carries_the_output_modules_pictures(run: dict) -> None:
    _ok(run, "setup-output")
    _ok(run, "export")
    pictures = [
        n
        for n in run["gmap-names"]
        if n.startswith("bindings/outputs/") and "/pictures/" in n
    ]
    assert any(n.endswith("/pictures/face.png") for n in pictures), run["gmap-names"]
    assert run["read-gmap"]["outputPictures"]


# --- import As a new device -------------------------------------------------------


def test_as_new_device_for_a_device_with_a_folder_is_refused(run: dict) -> None:
    """A device folder is that device's identity (03 S128-S132): the same
    id as a new device writes nothing (lead, 2026-10-11)."""
    _ok(run, "import-new")
    assert run["new-radios"] == [True, True]
    # The file's device has a folder here: "Onto an existing device" first.
    assert run["new-default-existing"] is True
    assert run["new-picked"] is True
    assert run["new-folders"] == []
    assert "already has a device folder" in run["new-status"]
    assert run["new-stick-unchanged"] is True


def test_as_new_device_with_a_taken_name_makes_a_2_folder_and_undo_removes_it(
    run: dict,
) -> None:
    _ok(run, "import-default-new")
    # No folder for the file's id: "As a new device" first.
    assert run["twin-default-new"] is True
    assert run["twin-folders"] == [f"{NAME} (2)"], run["twin-status"]
    # Its wires come along under the file's own id, connected or not.
    assert "not written" not in run["twin-status"], run["twin-status"]
    assert run["twin-stick-unchanged"] is True
    # The output's tick was off: its module file is not written.
    assert run["twin-out-items"], "no output section in the preview"
    assert run["twin-output-unchanged"] is True
    assert run["twin-undo-shown"] is True
    assert run["twin-after-undo"] == []


# --- import Onto an existing device ------------------------------------------------


def test_import_onto_existing_merges_after_the_warning_and_undo_restores(
    run: dict,
) -> None:
    _ok(run, "import-existing")
    assert run["existing-before"] == [1, 3]
    assert run["existing-target"] == NAME
    assert run["existing-warning"] is True
    assert "Default" in run["existing-warning-text"]
    # The pack's Default wires replace this machine's (button 3 goes).
    assert run["existing-after"] == [1]
    assert run["existing-undo-shown"] is True
    assert run["existing-undone"] == [1, 3]
