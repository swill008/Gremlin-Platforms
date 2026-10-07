# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""History's Before and After show what changed (08 S104,
D-08-HISTORY-DIFF), off-screen (history_diff_window_smoke.py): changed rows
tinted with a bar (red Before, green After), changed words in a stronger
tint, same and filler rows plain, the sides lined up row for row, and
Previous Change / Next Change moving both sides together."""

from __future__ import annotations

import html
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_SPAN = re.compile(
    r'<span style="[^"]*background-color:(#[0-9a-f]{6})[^"]*">([^<]*)</span>'
)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    args = [sys.executable, "test/unit/history_diff_window_smoke.py"]
    if os.environ.get("GREMLIN_SHOT"):
        args.append(os.environ["GREMLIN_SHOT"])
    result = subprocess.run(
        args, cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


def _rgb(argb: str) -> str:
    return "#" + argb[-6:]


def test_the_change_has_each_kind_of_row(run: dict) -> None:
    assert {"same", "added", "removed", "changed"} <= set(run["kinds"])
    assert len(run["blocks"]) == 3


def test_rows_are_tinted_by_kind(run: dict) -> None:
    tokens = run["tokens"]
    checked = 0
    for key, row in run["rows"].items():
        side, kind = key.split(":")[0], row["kind"]
        marked = kind == "changed" or kind == (
            "removed" if side == "before" else "added"
        )
        filler = kind == ("added" if side == "before" else "removed")
        if marked:
            red = side == "before"
            assert row["tint"] == tokens["diffRemovedBg" if red else "diffAddedBg"], key
            assert row["bar"] == tokens["diffRemovedBar" if red else "diffAddedBar"], (
                key
            )
            checked += 1
        else:
            assert row["tint"] == tokens["clear"], key
            assert row["bar"] == "", key
        if filler:
            assert row["plain"] == "", key
    assert checked >= 6


def test_changed_words_get_the_stronger_tint(run: dict) -> None:
    tokens = run["tokens"]
    rows = run["rows"]

    def marked(key: str) -> list[tuple[str, str]]:
        return [(c, html.unescape(t)) for c, t in _SPAN.findall(rows[key]["html"])]

    red, green = _rgb(tokens["diffRemovedWord"]), _rgb(tokens["diffAddedWord"])
    assert marked("before:36") == [(red, "two")]
    assert marked("after:36") == [(green, "2")]
    assert marked("before:35") == [(red, "slow")]
    assert marked("after:35") == [(green, "fast")]
    # The text is escaped, not read as HTML.
    assert rows["before:35"]["plain"] == rows["before:35"]["line"]
    assert rows["before:35"]["plain"] == "alpha: slow <b>&amp; steady"
    # Same, added and removed rows are plain text.
    assert not any(r["rich"] for r in rows.values() if r["kind"] != "changed")


def test_the_sides_line_up(run: dict) -> None:
    rows = run["rows"]
    for key, row in rows.items():
        if key.startswith("before:"):
            twin = rows.get("after:" + key.split(":")[1])
            if twin:
                assert row["height"] == twin["height"], key
    assert run["start"]["aligned"]


def test_previous_and_next_change_move_both_sides(run: dict) -> None:
    start, steps = run["start"], run["steps"]
    assert (start["previous"], start["next"]) == (False, True)
    # Next to the first, second and last change.
    assert [s["at"] for s in steps] == [0, 1, 2, 1, 0]
    second = steps[1]
    assert second["before-y"] > 0
    assert second["before-y"] == second["after-y"]
    assert second["aligned"]
    assert second["first-row"] <= run["blocks"][1]
    assert (second["previous"], second["next"]) == (True, True)
    assert (steps[2]["previous"], steps[2]["next"]) == (True, False)
    assert steps[4]["before-y"] == steps[4]["after-y"] == 0
    assert (steps[4]["previous"], steps[4]["next"]) == (False, True)


def test_the_whole_text_is_still_there(run: dict) -> None:
    assert run["before-text"].startswith("Checked controls:\nButton 1\nButton 3")
