# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Pack window, off-screen (handson_G3_pack_smoke.py): 08 S106
(D-08-PACK-START) and 08 S107 (D-08-PACK-BG)."""

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
    result = subprocess.run(
        [sys.executable, "test/unit/handson_G3_pack_smoke.py"],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


def test_s106_opens_on_the_first_device_that_can_be_exported(run: dict) -> None:
    assert run["open-on"] == "pJoy Pro"
    assert run["open-shown"] == "pJoy Pro"
    assert run["open-status"] == ""
    assert run["labels"][0] == "Alpha Stick (file damaged)"
    assert "pJoy Pro" in run["labels"]


def test_s106_a_damaged_device_stays_listed_and_says_why(run: dict) -> None:
    assert run["alpha-index"] == 0
    # The choice set from code is read at once (it used to show the device
    # chosen before).
    assert run["picked-name"] == "Alpha Stick"
    assert "is damaged" in run["picked-status"]
    assert "Start Fresh" in run["picked-status"]
    assert run["picked-export-enabled"] is False
    assert run["back-name"] == "pJoy Pro"


def test_s107_the_photo_loads_in_the_background_at_preview_size(run: dict) -> None:
    assert run["photo-async"] is True
    width, height = run["photo-source-size"]
    assert 0 < width <= 1200 and 0 < height <= 1200
    assert run["photo-ready"] is True
    # Decoded at preview size, not the photo's 3000 pixels.
    assert 0 < run["photo-loaded-width"] <= 1200


def test_s107_export_runs_in_the_background(run: dict) -> None:
    assert run["entered"] is True
    assert run["timer-fired"] is True
    assert run["busy-shown"] is True
    assert run["busy-text"] == "Exporting…"
    assert run["export-enabled-while-busy"] is False
    assert run["file-before-release"] is False
    assert run["finished"] is True
    assert run["status-after"].startswith("Wrote ")
    assert "g3 pack.zip" in run["status-after"]
    assert run["busy-after"] is False
    assert run["export-enabled-after"] is True
    assert run["show-folder-after"] is True
    assert run["file-after"] is True
    # One at a time: the second Export was not started.
    assert run["second-file"] is False
    assert run["writes"] == 1
    assert run["worker-thread"] != "MainThread"


def test_s107_a_failure_names_file_folder_and_reason(run: dict) -> None:
    status = run["status-failed"]
    assert status.startswith("Export failed. taken.zip could not be written to ")
    assert status.endswith(": a folder has that name.")
    assert run["export-enabled-after-fail"] is True
