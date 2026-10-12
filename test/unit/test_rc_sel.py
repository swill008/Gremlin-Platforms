# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Right-click additions in the Device Mapping Editor (07 S136, S137): Cut is
one Undo step, Paste Here centres the pasted items on the point, and the
editor carries the Favourites / Repeat properties, signals, command
forwarders and the right-click menu's Favourites wiring.

The editor runs off-screen in its own process (rc_sel_smoke.py).
"""

from __future__ import annotations

import json
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_SMOKE = pathlib.Path(__file__).parent / "rc_sel_smoke.py"


@pytest.fixture(scope="module")
def facts(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("rc_sel") / "facts.json"
    result = proc_tree.run(
        [sys.executable, str(_SMOKE), str(out)], text=True, timeout=240
    )
    assert result.returncode == 0 and out.exists(), smoke_report.explain(result)
    return json.loads(out.read_text(encoding="utf-8"))


def _near(a: list, b: list, tol: float = 2.0) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def test_cut_is_one_undo_step(facts: dict) -> None:
    cut = facts["cut"]
    assert cut == {"gone": True, "copied": 1, "steps": 1, "undoBack": True}


def test_paste_here_centres_one_item(facts: dict) -> None:
    p = facts["pasteOne"]
    assert p["added"] == 1
    assert p["steps"] == 1
    assert p["selectedNew"]
    assert _near(p["centre"], p["want"]), p


def test_paste_here_centres_the_box_of_several(facts: dict) -> None:
    p = facts["pasteTwo"]
    assert p["selected"] == 2
    assert p["steps"] == 1
    assert _near(p["centre"], p["want"]), p


def test_editor_properties_signals_and_forwarders(facts: dict) -> None:
    p = facts["props"]
    assert p["last"] == ""
    assert p["fav"] == []
    assert p["shown"] == 5
    assert p["sig"] == ["function"] * 4
    assert p["fwd"] == ["function"] * 8
    assert p["ctx"] == [0, 0]


def test_menu_favourites_wiring(facts: dict) -> None:
    m = facts["menu"]
    assert m.get("enabled") is True, m
    assert m["ids"] == ["edit.cut"]
    assert m["got"] == ["t:edit.copy", "r:edit.cut"]


def test_select_all_in_the_editor(facts: dict) -> None:
    a = facts["selectAll"]
    assert a["same"] and a["n"] > 1 and a["lockedOut"], a
    assert a["info"]["id"] == "edit.cut", a


def test_no_qml_warnings(facts: dict) -> None:
    assert facts["warnings"] == []
