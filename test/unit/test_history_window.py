# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The History window, off-screen (history_window_smoke.py): opened for one
device as Module Setup opens it, it lists that device's saved changes,
shows one before and after, Restore Before puts the file back (a new
change in the list), Show All drops the device filter, and picking the
same change again reads it again."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


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
    args = [sys.executable, "test/unit/history_window_smoke.py"]
    if os.environ.get("GREMLIN_SHOT"):
        args.append(os.environ["GREMLIN_SHOT"])
    result = subprocess.run(
        args, cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


def test_it_lists_the_devices_changes(run: dict) -> None:
    assert run["count"] == 2
    assert run["about"] == "Only History Stick"
    assert run["first-title"] == "Saved History Stick: checked controls and names"


def test_a_change_before_and_after(run: dict) -> None:
    # In words, as the Device Pack rows (08 Q13), not raw JSON.
    assert run["before"].startswith("Checked controls:\nButton 1")
    assert "Button 2" not in run["before"]
    assert "Button 1\nButton 2" in run["after"]
    assert run["restore-enabled"] is True


def test_restore_before_puts_the_file_back(run: dict) -> None:
    assert run["message"] == "Put back history_stick.json."
    assert run["file-after-restore"] == {"buttons": [1]}
    assert run["count-after-restore"] == 3


def test_show_all_drops_the_device(run: dict) -> None:
    assert run["about-after-show-all"] in ("", "Only ")


def test_picking_the_same_change_again_reads_it_again(run: dict) -> None:
    # pick() bumps shownRevision; selected alone doesn't change for the
    # same entry, so the details stayed as first read.
    assert run["repicked-title"] == "Changed since it was shown"
