# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's right-click additions and Favourites (07 S136, S137;
D-07-RIGHTCLICK, D-07-RIGHTCLICK-ANSWERS) in the running window, off-screen
in its own process and user folder (rc_e2e_smoke.py):

- the ☆ on a right-click row and on a menu-bar row adds a favourite without
  running the row; the Favourites block sits at the top in the order added;
- a favourite row runs its command; its × removes it and the menu stays open;
- only favourites that apply to the selection show; none: no block;
- Device Map Options › Favourites shown 0 / 2 / 5;
- Repeat follows a menu-bar command, a right-click row and a key (not Copy
  or Select All), and its row runs it again;
- Cut is one Undo step; Paste Here centres the pasted items on the spot;
- Show in Layers unfolds Layers and lights the row; Properties… shows
  Properties;
- Reset Panels keeps the favourites and the next window has them.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "rc_e2e_smoke.py"


def run_smoke(home: pathlib.Path, *args: str) -> dict:
    """Runs rc_e2e_smoke.py in home (a temporary user folder); its RESULT."""
    (home / "Gremlin Platforms").mkdir(exist_ok=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        QT_FORCE_STDERR_LOGGING="1",
        QT_QPA_FONTDIR=os.environ.get(
            "QT_QPA_FONTDIR",
            os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"),
        ),
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, str(_SMOKE), *args],
        cwd=_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if not lines:
        raise RuntimeError(done.stdout[-2000:] + done.stderr[-2000:])
    out = json.loads(lines[-1][len("RESULT ") :])
    if "error" in out:
        raise RuntimeError(out.get("traceback") or out["error"])
    out["_stderr"] = (done.stderr or "") + (done.stdout or "")
    return out


@pytest.fixture(scope="module")
def seen(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_smoke(tmp_path_factory.mktemp("rc_e2e"))


def _step(seen: dict, name: str) -> dict:
    res = seen.get(name)
    assert isinstance(res, dict), f"{name}: {res!r}"
    assert "error" not in res, res.get("traceback") or res["error"]
    return res


def test_contract_names_are_there(seen: dict) -> None:
    api = _step(seen, "api")
    assert "undefined" not in api["opts"], api
    assert "undefined" not in api["ed"], api
    assert "undefined" not in api["cmd"], api
    assert api["layers"] == "function"
    assert api["shown"] == 5 and api["edShown"] == 5


def test_star_adds_from_the_right_click_menu_and_the_menu_bar(seen: dict) -> None:
    res = _step(seen, "add")
    ctx = res["ctx"]
    assert ctx.get("row") and ctx.get("star"), ctx
    assert ctx["ran-nothing"], "the ☆ ran the row"
    assert res["after-ctx"] == ["edit.cut"]
    bar = res["bar"]
    assert bar.get("row") and bar.get("star"), bar
    assert bar["ran-nothing"]
    assert res["after-bar"] == ["edit.cut", "bringToFront"]
    assert res["bar-edit"].get("star"), res["bar-edit"]
    assert res["after-bar-edit"] == ["edit.cut", "bringToFront", "edit.duplicate"]
    # The editor follows the store.
    assert res["ed-favs"] == res["after-bar-edit"]


def test_the_block_is_at_the_top_in_the_order_added(seen: dict) -> None:
    res = _step(seen, "add")
    assert res["block"]
    assert res["rows"] == ["edit.cut", "bringToFront", "edit.duplicate"]
    assert res["model"] == res["rows"]


def test_a_favourite_runs_and_its_cross_removes_it(seen: dict) -> None:
    res = _step(seen, "remove")
    assert res["row"] and res["ran"], res
    assert res["x"], res
    assert res["ran-nothing"], "the × ran the row"
    assert res["menu-open"], "the menu closed on ×"
    assert "bringToFront" not in res["rows"]
    assert res["favs"] == ["edit.cut", "edit.duplicate"]


def test_only_what_applies_shows(seen: dict) -> None:
    res = _step(seen, "applies")
    assert res["applies"]["edit.duplicate"]
    assert not res["applies"]["table.idCol"]
    shown = [c for c in ("table.idCol", "edit.duplicate", "flipH") if res["applies"][c]]
    assert res["rows"] == shown
    assert not res["none-block"]
    assert res["none-model"] == []


@pytest.mark.parametrize("n", [0, 2, 5])
def test_how_many_show(seen: dict, n: int) -> None:
    res = _step(seen, "counts")
    got = res[str(n)]
    assert got["opt"] == n and got["ed"] == n, got
    assert got["rows"] == res["favs"][:n]
    assert got["block"] == (n > 0)


def test_repeat_after_a_menu_a_right_click_and_a_key(seen: dict) -> None:
    res = _step(seen, "repeat")
    assert res["menu"] == ["bringToFront", 'Repeat "Bring to Front"']
    assert res["menu-row"], res["menu-first-row"]
    assert res["after-copy"] == "bringToFront", "Copy changed what Repeat runs"
    assert res["cut-clicked"] and res["cut-ran"]
    assert res["right-click"] == "edit.cut"
    assert res["key"] == "bringForward"
    assert res["after-select-all"] == "bringForward"
    assert res["label"] == 'Repeat "Bring to Front"'
    assert res["repeat-clicked"] and res["repeat-ran"], res


def test_cut_is_one_undo_step(seen: dict) -> None:
    res = _step(seen, "cut")
    assert res["clicked"], "no Cut row"
    assert res["gone"]
    assert res["copied"] == ["b3"]
    assert res["steps"] == 1
    assert res["undone"]


def test_paste_here_centres_on_the_spot(seen: dict) -> None:
    res = _step(seen, "paste-here")
    assert res["clicked"], "no Paste Here row"
    assert res["new"] == 2
    assert res["steps"] == 1
    assert res["selected"]
    cx, cy = res["centre"]
    wx, wy = res["want"]
    assert abs(cx - wx) < 2 and abs(cy - wy) < 2, res


def test_show_in_layers(seen: dict) -> None:
    res = _step(seen, "show-in-layers")
    assert res["clicked"], "no Show in Layers row"
    assert res["open"]
    assert res["revealed"] == "b2"
    assert res["row"]["index"] >= 0 and res["row"]["inView"]


def test_properties(seen: dict) -> None:
    res = _step(seen, "properties")
    assert res["clicked"], "no Properties… row"
    assert res["props-on"] and res["layers-open"] and res["shown"]


def test_kept_for_the_next_window_and_by_reset_panels(seen: dict) -> None:
    res = _step(seen, "kept")
    want = ["edit.duplicate", "bringToFront", "hide"]
    assert res["after-reset"] == want
    assert res["stored"] == want
    assert res["next-window"] == want
    assert res["rows"] == want
