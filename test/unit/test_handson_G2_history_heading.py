# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fix G2: History's "Before" heading clear of Restore Before.

At 150 % the History window's "Before" heading touched the "Restore
Before" button (hands-on 08, note O5, s48-created-entry.png): the heading
was squeezed to less than its text, which drew on under the button.

Since D-TESTLIST-1 item 13 the Restore buttons are no longer beside the
headings: one controls row holds "Restore to before this change", the link
"Restore to after this change" and "Show full before/after". This checks
that row stays clear (no control drawn over the next, all inside the row)
and that each heading, shown with "Show full before/after", is drawn inside
its own side (shortened (…) when there is no room).

The real History window off-screen in its own process
(handson_G2_history_smoke.py) at 100, 150 and 175 %.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module", params=[100, 150, 175])
def run(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> dict:
    home = tmp_path_factory.mktemp("g2history")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    args = [sys.executable, "test/unit/handson_G2_history_smoke.py", str(request.param)]
    if os.environ.get("GREMLIN_SHOT"):
        args.append(os.environ["GREMLIN_SHOT"].replace(".png", f"-{request.param}.png"))
    result = proc_tree.run(
        args, cwd=_ROOT, env=env, text=True, timeout=120
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


def test_restore_controls_do_not_overlap(run: dict) -> None:
    controls = run["controls"]
    assert [c["name"] for c in controls] == [
        "historyRestoreBefore",
        "historyRestoreAfter",
        "historyShowFull",
    ]
    for left, right in zip(controls, controls[1:]):
        # The drawn text and the box, with a gap before the next control.
        limit = right["start"] - run["gap-wanted"] + 0.5
        assert left["text-end"] <= limit, (left, right)
        assert left["end"] <= limit, (left, right)


def test_restore_controls_inside_the_row(run: dict) -> None:
    for control in run["controls"]:
        assert control["start"] >= run["row-start"] - 0.5, control
        assert control["end"] <= run["row-end"] + 0.5, control
        assert control["text-end"] <= run["row-end"] + 0.5, control


@pytest.mark.parametrize("side", ["Before", "After"])
def test_heading_drawn_inside_its_side(run: dict, side: str) -> None:
    at = run[side]
    assert at["heading-start"] >= at["side-start"] - 0.5, at
    assert at["text-end"] <= at["side-end"] + 0.5, at
