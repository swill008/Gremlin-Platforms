# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Layers panel search and per-kind filter: the editor's side (07 S102,
D-07-LAYERS-SEARCH).

layerRows takes { kinds, query } and marks each row match (passes the
filter) or heading (shown only for a matching part under it); layerCounts
gives "N of M"; selectLayerMatches selects the matches without an undo step.
The search matches the row's name, the control (even when renamed), what the
chip shows and the kind of row. The old single kind names still work.
Runs the editor off-screen in its own process.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results() -> dict:
    done = proc_tree.run(
        [sys.executable, str(_HERE / "layers_filter_logic_smoke.py")],
        text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    out = json.loads(lines[0][len("RESULT "):])
    # In Foreground mode the list ends with the folded Background row (07
    # S120), whatever the filter; it is not one of the filtered rows, so the
    # checks below look at the rows above it.
    ends = {}
    for key, value in list(out.items()):
        if (
                isinstance(value, list) and value
                and isinstance(value[0], dict) and "part" in value[0]
        ):
            ends[key] = value[-1]
            out[key] = [r for r in value if r.get("part") != "background"]
    out["_background-rows"] = ends
    return out


def _shown(rows: list) -> list:
    return [(r["id"], r["part"]) for r in rows]


def _matches(rows: list) -> list:
    assert isinstance(rows, list), rows
    return [(r["id"], r["part"]) for r in rows if r.get("match")]


def _without_filter_keys(rows: list) -> list:
    return [{k: v for k, v in r.items() if k not in ("match", "heading")} for r in rows]


def test_empty_filter_gives_todays_rows(results: dict) -> None:
    for got, old in (("empty", "old-all"), ("empty-open", "old-all-open")):
        rows = results[got]
        assert _without_filter_keys(rows) == _without_filter_keys(results[old])
        assert all(r["match"] is True and r["heading"] is False for r in rows)
    # The open chip still shows its hotspot and leader.
    assert ("b3", "hot") in _shown(results["empty-open"])
    assert ("b3", "leader:0") in _shown(results["empty-open"])


def test_old_kind_names_still_work(results: dict) -> None:
    assert {r["type"] for r in results["old-chips"]} == {"chip", "group"}
    assert {r["type"] for r in results["old-drawings"]} == {"shape", "line"}
    # The Photo kind is gone (07 S102); the folded Background row ends the
    # list instead (S120): never selectable, never deleted.
    assert all(r["type"] for r in results["old-all"])
    assert "photo" not in {r["type"] for r in results["old-all"]}


def test_every_list_ends_with_the_folded_background_row(results: dict) -> None:
    ends = results["_background-rows"]
    assert "old-all" in ends and "q:zzz" in ends
    for key, row in ends.items():
        assert (row["id"], row["part"], row["type"], row["name"]) == (
            "", "background", "background", "Background"), key


def test_hotspots_alone_show_under_dimmed_headings(results: dict) -> None:
    rows = results["hotspots"]
    chips = [r for r in results["old-all"] if r["type"] in ("chip", "group")]
    hots = [r for r in rows if r["type"] == "hotspot"]
    assert [r["id"] for r in hots] == [c["id"] for c in chips]
    assert all(r["match"] for r in hots)
    heads = [r for r in rows if r["depth"] == 0]
    assert [r["id"] for r in heads] == [c["id"] for c in chips]
    assert all(r["heading"] and not r["match"] for r in heads)
    # No leaders or drawings; each hotspot right under its chip.
    assert {r["type"] for r in rows} == {"chip", "group", "hotspot"}
    for i, r in enumerate(rows):
        if r["type"] == "hotspot":
            assert rows[i - 1]["id"] == r["id"] and rows[i - 1]["depth"] == 0


def test_shapes_alone(results: dict) -> None:
    assert _matches(results["shapes"]) == [(results["ids"]["rect"], "")]
    assert _shown(results["shapes"]) == [(results["ids"]["rect"], "")]


def test_hat_finds_named_and_unnamed_hats(results: dict) -> None:
    for q in ("q:hat", "q:HAT "):
        assert _matches(results[q]) == [("h2", ""), ("h1", "")]
        assert all(not r["heading"] for r in results[q])


def test_button_finds_renamed_chips_and_group_members(results: dict) -> None:
    hits = _matches(results["q:button"])
    assert ("b40", "") in hits  # named "Fire"
    assert ("b3", "") in hits
    assert ("h1", "") not in hits
    # Group rows are named after their members; members also show.
    assert ("p2122", "") in hits


def test_member_shows_under_a_dimmed_group(results: dict) -> None:
    rows = results["chip+button"]
    assert _shown(rows) == [("p2122", ""), ("p2122", "member:0")]
    head, mem = rows
    assert head["heading"] and not head["match"]
    assert mem["match"] and mem["name"] == "Button 21" and mem["depth"] == 1


def test_hotspot_finds_every_hotspot(results: dict) -> None:
    rows = results["q:hotspot"]
    chips = [r["id"] for r in results["old-all"] if r["type"] in ("chip", "group")]
    assert _matches(rows) == [(c, "hot") for c in chips]
    assert all(r["heading"] for r in rows if r["depth"] == 0)


def test_chip_text_and_name(results: dict) -> None:
    assert _matches(results["q:fire"]) == [("b40", "")]
    # What b5 shows on the map (its action), not its name.
    assert _matches(results["q:weapon"]) == [("b5", "")]
    assert _matches(results["q:rect"]) == [(results["ids"]["rect"], "")]
    assert results["q:zzz"] == []


def test_kinds_and_query_together(results: dict) -> None:
    assert _matches(results["chip+hat"]) == [("h2", ""), ("h1", "")]
    assert results["shape+hat"] == []


def test_an_open_matching_chip_keeps_its_parts(results: dict) -> None:
    rows = results["open+filter"]
    assert _shown(rows) == [("h2", ""), ("h2", "hot"), ("h2", "leader:0")]
    assert [r["match"] for r in rows] == [True, False, False]


def test_counts(results: dict) -> None:
    every = results["all-rows"]
    members = sum(len(r["name"].split(", ")) for r in every if r["type"] == "group")
    total = len(every) + members
    assert results["counts-empty"] == {"matches": total, "total": total}
    assert results["counts-hat"] == {"matches": 2, "total": total}
    hots = len([r for r in every if r["type"] == "hotspot"])
    assert results["counts-hotspots"] == {"matches": hots, "total": total}
    assert results["counts-zzz"] == {"matches": 0, "total": total}


def test_select_matches_selects_without_an_undo_step(results: dict) -> None:
    assert results["select-hat"] == 2
    assert sorted(results["select-hat-ids"]) == ["h1", "h2"]
    before_at, after_at, before_len, after_len = results["select-hat-steps"]
    assert (after_at, after_len) == (before_at, before_len)
    # A member selects its group; the Background row is not selectable.
    assert results["select-member"] == 1
    assert results["select-member-ids"] == ["p2122"]
    assert results["select-background"] == 0


def test_a_member_row_is_not_deleted(results: dict) -> None:
    # Deleting a member row would return its whole group to the pool.
    assert results["can-delete-member"] is False
