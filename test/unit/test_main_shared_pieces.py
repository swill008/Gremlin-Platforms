# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The main window's pages on the shared pieces (01 S140, S143;
D-01-CONFIRM, D-01-SHARED-PIECES): the profile Save As / Open choosers
remember the profile folder; Home's Delete Device (03 S90, step 2), the
Scripts page's Remove (04 S85) and the OSC page's Clear ask the shared
question, where Enter and Esc cancel; the Output View's Screen Background
uses the picture chooser. Runs the program off-screen in its own process
(main_shared_pieces_smoke.py) with a fresh user folder.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "main_shared_pieces_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
        TEMP=str(home), TMP=str(home),
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    assert not out["errors"], out["errors"]
    assert not out["qml_errors"], out["qml_errors"]
    return out


def test_profile_choosers_remember_the_folder(run: dict) -> None:
    assert run["save_kind"] == "profile"
    assert run["open_kind"] == "profile"
    assert run["saved"], "Save As did not save"
    start = run["open_start"].rstrip("/").lower()
    assert start == run["folder_url"].rstrip("/").lower()


def test_closing_save_as_calls_off_what_waited(run: dict) -> None:
    assert run["cancel_clears"]


def test_delete_device_asks_the_shared_question(run: dict) -> None:
    q = run["delete_question"]
    assert q["title"] == "Delete pJoy Pro?"
    assert q["action"] == "Delete Device"
    assert q["last"] == "You can restore it from Tools › History."
    assert q["text"].startswith("An autosave is kept in the Device Library first.")
    assert run["delete_enter_closed"], "Enter did not close the question"
    assert not run["delete_done_after_enter"], "Enter deleted the device"
    assert run["delete_done_title"] == "Device deleted"


def test_remove_script_asks_the_shared_question(run: dict) -> None:
    assert run["script_kind"] == "script"
    assert run["script_rows_added"] == 1
    q = run["script_question"]
    assert q["title"].startswith("Remove script ")
    assert q["action"] == "Remove Script"
    assert "not deleted" in q["text"]
    assert run["script_enter_closed"]
    assert run["script_rows_after_enter"] == 1, "Enter removed the script"
    assert run["script_rows_after_remove"] == 0, "the red button did not remove it"


def test_osc_clear_is_red_and_asks(run: dict) -> None:
    # 09 S135, S136: no footer; Clear… is a red row in the right-click menu.
    assert run["osc_footer_clear"] is False
    assert run["osc_clear_row"] == {"text": "Clear…", "danger": True, "enabled": True}
    q = run["osc_question"]
    assert q["title"] == "Clear OSC inputs?"
    assert q["action"] == "Clear OSC Inputs"
    assert run["osc_esc_closed"]
    assert run["osc_rows_after_esc"] == 1, "Esc cleared the OSC inputs"


def test_screen_background_uses_the_picture_chooser(run: dict) -> None:
    assert run["picture_kind"] == "picture"
    assert run["picture_set"]
