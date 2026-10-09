# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Help → Save Diagnostics… and the Debug tab's button (01 S132): both open
the Save Diagnostics window, whose Save dialog starts on the Desktop and
whose box adds the open profile. Checked in the running program off-screen
(handson_D11_diagnostics_smoke.py, its own process and a made-up user)."""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest
from PySide6 import QtCore

from test.unit import help_book

_ROOT = pathlib.Path(__file__).parents[2]
_COMMANDS = (_ROOT / "qml" / "main_commands.js").read_text(encoding="utf-8")
_LIVE_LOG = (_ROOT / "qml" / "DialogLiveLog.qml").read_text(encoding="utf-8")
_GLOSSARY = (_ROOT / "claude" / "glossary.md").read_text(encoding="utf-8")


def test_the_command_is_in_the_help_menu_list() -> None:
    assert re.search(
        r'\{ id: "help\.diagnostics", text: "Save Diagnostics…", group: "Help"',
        _COMMANDS,
    )
    # Between Check for Updates and About.
    assert (
        _COMMANDS.index('"help.updates"')
        < _COMMANDS.index('"help.diagnostics"')
        < _COMMANDS.index('"help.about"')
    )


def test_the_debug_tab_has_the_button() -> None:
    assert 'text: qsTr("Save Diagnostics…")' in _LIVE_LOG
    assert "DialogSaveDiagnostics.qml" in _LIVE_LOG


def test_the_guide_and_glossary_name_it(qapp: QtCore.QCoreApplication) -> None:
    assert re.search(r"Help [→›] Save Diagnostics…", help_book.book_text())
    assert "**Save Diagnostics…**" in _GLOSSARY


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("Users") / "Pat Tester"
    (home / "Gremlin Platforms").mkdir(parents=True)
    out = tmp_path_factory.mktemp("out")
    env = dict(
        os.environ, USERPROFILE=str(home), USERNAME="Pat Tester",
        QT_QPA_PLATFORM="offscreen", HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "test" / "unit" / "handson_D11_diagnostics_smoke.py"),
            str(out / "diag.zip"),
        ],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    result = json.loads(lines[0][len("RESULT "):])
    result["dest"] = str(out / "diag.zip")
    return result


def test_help_command_opens_the_window_on_the_desktop(run: dict) -> None:
    assert run["command"] == "Help › Save Diagnostics…"
    assert run["fromMenu"] is True
    assert run["startFolder"] == run["desktop"]
    assert str(run["desktop"]).endswith("/Desktop")
    assert run["box"] == "Include the open profile"
    assert run["boxStarts"] is False


def test_debug_button_opens_it_and_saves_the_zip(run: dict) -> None:
    assert run["button"] == "Save Diagnostics…"
    assert run["fromDebugTab"] is True
    assert run["started"] is True
    assert run["finished"] is True
    assert run["shown"] == f"Diagnostics saved to {run['dest']}."
    files = run["files"]
    assert {"README.txt", "versions.json", "devices.json"} <= set(files)
    assert [f for f in files if f.startswith("logs/")]
    assert [f for f in files if f.startswith("profile/")]


def test_a_failure_is_shown_with_file_folder_and_reason(run: dict) -> None:
    gone = pathlib.Path(run["dest"]).parent / "gone"
    assert run["failure"] == (
        f"Diagnostics not saved. x.zip could not be written to {gone}: "
        "the folder does not exist."
    )
