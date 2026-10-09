# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S139 (D-01-HELP-LINKS): every Open › / Show me › link in the whole Help
book leads to a real window, menu item, button or setting. Runs the program
off-screen (help_links_smoke.py resolve) and asks the program's own
Style.helpLinks.check() about each link.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "help_links_smoke.py"

# Reasons that mean "not now" (fine in a fresh, empty program), not "no
# such target".
_NOT_NOW = ("Open a profile", "Plug in")


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE), "resolve"], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    assert not out["errors"], out["errors"]
    assert out.get("bridge"), "Style.helpLinks is not set by the main window"
    return out


def test_made_up_targets_are_refused(run: dict) -> None:
    for href, reason in run["bogus"].items():
        assert reason, f"check() accepts a made-up link {href}"


def test_every_link_resolves(run: dict) -> None:
    assert run["links"], "no Open › / Show me › links found in the book"
    bad = [
        f"{x['topic']}: {x['href']} -> {x['reason']}"
        for x in run["links"]
        if x["reason"] and not x["reason"].startswith(_NOT_NOW)
    ]
    assert not bad, "\n".join(bad)


def test_open_links_are_on_the_allowed_list(run: dict) -> None:
    bad = [f"{x['topic']}: {x['href']}" for x in run["links"] if not x["allowed"]]
    assert not bad, "\n".join(bad)


def test_link_text_matches_its_kind(run: dict) -> None:
    want = {"open": "Open ›", "show": "Show me ›"}
    bad = [
        f"{x['topic']}: {x['href']} text {x['text']!r}"
        for x in run["links"]
        if x["text"] != want[x["href"].split(":", 1)[0]]
    ]
    assert not bad, "\n".join(bad)
