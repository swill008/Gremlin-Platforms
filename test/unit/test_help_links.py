# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S139 (D-01-HELP-LINKS): Help's Open › / Show me › links. qml/help_links.js
in a QJSEngine (parsing, the allowed list, greying), and the Help window off-
screen with a stand-in Style.helpLinks: a click reveals, Help stays open, a
link that can't be shown is greyed with its reason on hover and under the
title, an Open › for a command not on the list is refused, and links are
checked again when Help is activated.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest
from PySide6 import QtCore, QtQml

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "qml" / "help_links.js"
_COMMANDS = _ROOT / "qml" / "main_commands.js"
_SMOKE = _ROOT / "test" / "unit" / "help_links_smoke.py"


def _js(call: str) -> object:
    source = "\n".join(
        "" if line.startswith(".") else line
        for line in _SCRIPT.read_text(encoding="utf-8").splitlines()
    )
    engine = QtQml.QJSEngine()
    result = engine.evaluate(source + "\nJSON.stringify(" + call + ")", str(_SCRIPT))
    assert not result.isError(), result.toString()
    return json.loads(result.toString())


def _q(value: object) -> str:
    return json.dumps(value)


def test_parse(qapp: QtCore.QCoreApplication) -> None:
    assert _js(_q_call("parse", "open:tools.deviceLibrary")) == {
        "kind": "open", "parts": ["tools.deviceLibrary"]}
    assert _js(_q_call("parse", "show:menu/Tools/Device Setup/Calibration")) == {
        "kind": "show", "parts": ["menu", "Tools", "Device Setup", "Calibration"]}
    assert _js(_q_call("parse", "show:modebar")) == {
        "kind": "show", "parts": ["modebar"]}
    assert _js(_q_call("parse", "topic:gs-start")) == {
        "kind": "topic", "parts": ["gs-start"]}
    assert _js(_q_call("parse", "https://x.org"))["kind"] == "other"


def _q_call(name: str, *args: object) -> str:
    return name + "(" + ", ".join(_q(a) for a in args) + ")"


def test_allowed_list_is_only_window_and_page_commands(
    qapp: QtCore.QCoreApplication,
) -> None:
    allowed = _js("allowedOpen()")
    source = _COMMANDS.read_text(encoding="utf-8")
    ids = set(re.findall(r'\{ id: "([^"]+)"', source))
    assert set(allowed) <= ids, set(allowed) - ids
    for bad in ("file.new", "file.load", "file.save", "file.saveAs", "file.exit",
                "file.programFolder", "file.dataFolder", "view.layout.single",
                "help.updates", "help.diagnostics", "help.guide"):
        assert bad not in allowed
        assert _js(_q_call("isAllowedOpen", bad)) is False
    for good in ("tools.deviceLibrary", "tools.options", "tools.history"):
        assert _js(_q_call("isAllowedOpen", good)) is True


def test_all_links_and_program_links(qapp: QtCore.QCoreApplication) -> None:
    html = ('<p><a href="topic:a">A</a> <b>X</b>'
            ' <a href="open:tools.options">Open ›</a>'
            ' <a class="k" href="show:menu/File/Save Profile">Show me ›</a>'
            ' <a href="https://x.org/?a=1&amp;b=2">web</a></p>')
    assert _js(_q_call("allLinks", html)) == [
        "topic:a", "open:tools.options", "show:menu/File/Save Profile",
        "https://x.org/?a=1&b=2"]
    assert _js(_q_call("programLinks", html)) == [
        "open:tools.options", "show:menu/File/Save Profile"]


def test_decorate_greys_only_links_with_a_reason(
    qapp: QtCore.QCoreApplication,
) -> None:
    html = ('<p><a href="open:tools.options">Open ›</a> '
            '<a href="show:modebar">Show me ›</a></p>')
    reasons = {"show:modebar": "Open a profile first."}
    out = _js(_q_call("decorate", html, reasons, "#777777"))
    assert '<a href="open:tools.options">Open ›</a>' in out
    assert re.search(
        r'<a href="show:modebar" style="color:#777777; text-decoration:none">'
        r'<span style="color:#777777[^"]*">Show me ›</span></a>', out), out
    assert re.sub(r"<[^>]+>", "", out) == re.sub(r"<[^>]+>", "", html)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE), "dialog"], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    return json.loads(lines[-1][len("RESULT "):])


def _part(run: dict, name: str) -> dict:
    assert name in run, run["errors"]
    return run[name]


def test_no_errors_and_nothing_handed_to_the_desktop(run: dict) -> None:
    assert not run["errors"], run["errors"]
    assert not run["qml_errors"], run["qml_errors"]
    # open:/show: are the program's own links, never a URL for Windows.
    assert run["desktop_urls"] == []


def test_click_reveals_and_help_stays_open(run: dict) -> None:
    click = _part(run, "click_open")
    assert click["log"] == ["open:tools.deviceLibrary"]
    assert click["help_open"]
    assert click["note"] == ""


def test_link_that_cannot_be_shown_is_greyed_with_why(run: dict) -> None:
    assert _part(run, "reasons").get("show:menu/File/Exit") == "Open a profile first."
    grey = _part(run, "disabled")
    html = _part(run, "html")
    assert re.search(r'<a href="show:menu/File/Exit" style="color:' + grey, html), html
    assert '<a href="open:tools.deviceLibrary">' in html, "a showable link is grey"
    hover = _part(run, "hover_show")
    assert hover["reason"] == "Open a profile first."
    assert hover["tip"].get("visible")
    assert hover["tip"].get("text") == "Open a profile first."
    click = _part(run, "click_show")
    assert click["log"] == ["open:tools.deviceLibrary"], "reveal ran for a greyed link"
    assert click["note_visible"] and click["note_text"] == "Open a profile first."


def test_open_of_a_command_not_on_the_list_is_refused(run: dict) -> None:
    assert _part(run, "reasons").get("open:file.exit")
    click = _part(run, "click_refused")
    assert "open:file.exit" not in click["log"]
    assert click["note"]


def test_links_are_checked_again_when_help_is_activated(run: dict) -> None:
    again = _part(run, "reactivate")
    assert "show:menu/File/Exit" in again["before"]
    assert "show:menu/File/Exit" not in again["after"]
    assert "open:file.exit" in again["after"]


def test_search_highlighting_still_works(run: dict) -> None:
    found = _part(run, "search")
    assert found["current"] and found["total"] >= 1
    assert "background-color:" in found["html"]
    assert re.search(r'href="show:menu/File/Exit" style="color:', found["html"])
