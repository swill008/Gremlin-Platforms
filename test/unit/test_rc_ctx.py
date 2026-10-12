# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Right-click Favourites in the shared menu (07 S137, D-07-RIGHTCLICK,
D-07-RIGHTCLICK-ANSWERS): ContextMenu's opt-in Favourites block, its × and
the ☆ / ★ on command rows, driven with the pointer off-screen by
rc_ctx_smoke.py; a menu without favouritesEnabled is unchanged."""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).parent


def _run(tmp_path: pathlib.Path) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir()
    result = proc_tree.run(
        [sys.executable, str(_HERE / "rc_ctx_smoke.py"), str(tmp_path / "out")],
        text=True,
        encoding="utf-8",
        timeout=120,
        env={
            **os.environ, "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8", "USERPROFILE": str(home),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, smoke_report.explain(result)
    problems = [line for line in lines if line.startswith(("ERROR", "WARN"))]
    assert problems == []
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }


def test_context_menu_favourites(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    # Without favouritesEnabled: as before, no block and no ☆ on hover.
    assert r["plain-describe"] == "A chip|Copy (Ctrl+C)|Cut (Ctrl+X)|Rename|> More"
    assert r["plain-no-star"] == "true"
    # The always-open block at the very top, above the quick rows.
    assert r["fav-describe"] == (
        "A chip|Favourites:|fav: Copy (Ctrl+C)|fav: Delete (Del)"
        "|Copy (Ctrl+C) [fav]|Cut (Ctrl+X)|Rename|> More"
    )
    assert r["fav-block"] == "true"
    assert r["fav-row-names"] == "true"
    assert r["fav-above"] == "true"
    # ×: favouriteRemoved, that row goes, the menu stays open.
    assert r["fav-after-remove"] == (
        "true removed edit.delete A chip|Favourites:|fav: Copy (Ctrl+C)"
        "|Copy (Ctrl+C) [fav]|Cut (Ctrl+X)|Rename|> More"
    )
    # ☆ only on hover, only on rows with a command.
    assert r["star-hidden"] == "false"
    assert r["star-shown"] == "true true"
    assert r["no-star-plain-row"] == "true"
    # Clicking ☆: favouriteToggled, the row does not run, the menu stays open
    # and the block shows it.
    assert r["after-star"] == (
        "true removed edit.delete;toggled edit.cut edit.copy,edit.cut"
    )
    assert "Favourites:|fav: Copy (Ctrl+C)|fav: Cut (Ctrl+X)|" in r["after-star-block"]
    # ★ on a favourite's row.
    assert r["copy-star"] == "true true"
    # A favourite runs and closes the menu like an action.
    assert r["after-run"] == "false ran fav copy"
    assert r["reopen"].startswith(
        "A chip|Favourites:|fav: Copy (Ctrl+C)|fav: Cut (Ctrl+X)|"
    )
