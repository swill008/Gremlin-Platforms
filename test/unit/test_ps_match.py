# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor, Photoshop-match handles and keys (07 S140-S155):
real mouse and key events on the off-screen editor, in its own process
(ps_match_smoke.py). The rule above all (07 S140): a picture's handles sit
on the picture's drawn edges before, during and after every drag.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")

# How far a drawn handle may sit from the drawn picture's edge (07 S140).
EDGE_PX = 1.5
SIDES = ("nw", "ne", "sw", "se", "n", "s", "w", "e")


# The smoke's sections, run in a few programs: a program the tests start is
# ended after 50 s (GREMLIN_TEST_HANG_LIMIT, test/conftest.py), and all of
# them in one take about 70 s. Each part takes about 20 s on its own.
PARTS = (
    "s140/2to1",
    "s140/import",
    "s141,s142,s143,s144_145,s146",
    "s147,s148,s149,s150,s153,s154,s155",
)


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    folder = tmp_path_factory.mktemp("ps_match")
    home = tmp_path_factory.mktemp("home")
    out: dict = {"warnings": []}
    for part in PARTS:
        done = proc_tree.run(
            [sys.executable, str(_HERE / "ps_match_smoke.py"), str(folder), part],
            text=True,
            timeout=120,
            env={
                **os.environ,
                "QT_QPA_PLATFORM": "offscreen",
                "USERPROFILE": str(home),
            },
        )
        lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
        assert lines, part + "\n" + done.stdout[-2000:] + done.stderr[-2000:]
        res = json.loads(lines[0][len("RESULT ") :])
        out["warnings"] = sorted(set(out["warnings"]) | set(res.pop("warnings")))
        for name, rows in res.items():
            out.setdefault(name, {}).update(rows)
    return out


def _section(results: dict, name: str) -> dict:
    r = results[name]
    assert "error" not in r, r.get("error")
    return r


# --- 07 S140 ---------------------------------------------------------------


@pytest.mark.parametrize("variant", ["plain", "rot30", "skew"])
@pytest.mark.parametrize("pic", ["2to1", "import"])
def test_s140_handles_stay_on_picture_edges(
    results: dict, pic: str, variant: str
) -> None:
    """07 S140: every handle of a 2:1 picture and of an imported picture,
    unrotated, turned 30 degrees and skewed, dragged in steps: at every step
    each drawn handle lies on the drawn picture's edge."""
    row = _section(results, "s140")[f"{pic}/{variant}"]
    assert row["handles"] == 8
    assert row["at_rest"] <= EDGE_PX
    if variant == "skew":
        assert row["skew"] and any(abs(k) > 0.01 for k in row["skew"])
    for name in SIDES:
        r = row[name]
        assert r["dragKind"] == "draw-" + name, (name, r)
        assert r["moved"] > 1, (name, r)
        assert r["max_off"] <= EDGE_PX, (name, r)


# --- 07 S141 ---------------------------------------------------------------


def test_s141_picture_corner_keeps_proportions(results: dict) -> None:
    r = _section(results, "s141")
    c = r["pic_corner"]
    assert c["w_grew"] > 20
    assert c["after"] == pytest.approx(c["before"], rel=0.015)


def test_s141_shift_frees_a_corner(results: dict) -> None:
    r = _section(results, "s141")
    for key in ("pic_corner_shift", "shape_corner_shift"):
        assert abs(r[key]["after"] - r[key]["before"]) / r[key]["before"] > 0.05, (
            key,
            r[key],
        )


def test_s141_shape_corner_keeps_proportions(results: dict) -> None:
    """07 S141: shapes keep their proportions from a corner too (not a square)."""
    c = _section(results, "s141")["shape_corner"]
    assert c["before"] > 1.5
    assert c["after"] == pytest.approx(c["before"], rel=0.015)


def test_s141_side_stretches_one_way(results: dict) -> None:
    r = _section(results, "s141")
    for key in ("pic_side", "shape_side"):
        s = r[key]
        assert s["dw"] > 20, (key, s)
        assert abs(s["dh"]) <= 1, (key, s)
        assert abs(s["dx"]) <= 1 and abs(s["dy"]) <= 1, (key, s)
    assert r["pic_side"]["edge_off"] <= EDGE_PX


def test_s141_shift_has_no_effect_on_a_side(results: dict) -> None:
    r = _section(results, "s141")
    plain, shift = r["shape_side"], r["shape_side_shift"]
    for k in ("dw", "dh", "dx", "dy"):
        assert shift[k] == pytest.approx(plain[k], abs=1), k


def test_s141_alt_resizes_from_the_centre(results: dict) -> None:
    r = _section(results, "s141")
    a = r["alt_corner"]
    assert a["centre_moved"] <= EDGE_PX
    assert a["dw"] > 50  # both sides moved
    assert a["ratio_after"] == pytest.approx(a["ratio_before"], rel=0.015)
    fa = r["alt_shift_corner"]
    assert fa["centre_moved"] <= EDGE_PX
    assert fa["dw"] == pytest.approx(80, abs=2)
    assert fa["dh"] == pytest.approx(40, abs=2)
    side = r["alt_side"]
    assert side["centre_moved"] <= EDGE_PX
    assert side["dw"] == pytest.approx(60, abs=2)
    assert abs(side["dh"]) <= 1


def test_s141_alt_from_the_centre_when_turned(results: dict) -> None:
    a = _section(results, "s141")["alt_rotated"]
    assert a["centre_moved"] <= EDGE_PX
    assert a["grew"] > 10


# --- 07 S142 ---------------------------------------------------------------


def test_s142_ctrl_skips_snapping(results: dict) -> None:
    r = _section(results, "s142")
    assert r["plain"]["edge_to_grid"] <= 0.6, r["plain"]
    assert r["plain"]["snapOffHeld"] is False
    assert r["ctrl"]["edge_to_pointer"] <= EDGE_PX, r["ctrl"]
    assert r["ctrl"]["edge_to_grid"] > 5, r["ctrl"]
    assert r["ctrl"]["snapOffHeld"] is True


# --- 07 S143 ---------------------------------------------------------------


def test_s143_alt_drag_copies_in_one_undo_step(results: dict) -> None:
    r = _section(results, "s143")
    a = r["alt_drag"]
    assert len(a["new"]) == 1, a
    assert a["selected"] == a["new"]
    assert a["original_moved"] <= 0.5
    assert a["copy_moved"] > 40
    assert a["copy_above"]
    assert a["hist_steps"] == 1
    u = r["alt_drag_undo"]
    assert u["ids"] is True
    assert u["original_moved"] <= 0.5


def test_s143_duplicate_in_place(results: dict) -> None:
    d = _section(results, "s143")["in_place"]
    assert len(d["new"]) == 1
    assert d["selected"] == d["new"]
    assert d["above"] and d["same_plane"] and d["same_box"]


# --- 07 S144, S145 ---------------------------------------------------------


def test_s144_shift_locks_a_move(results: dict) -> None:
    r = _section(results, "s144_145")
    assert r["horizontal"]["dx"] > 40 and abs(r["horizontal"]["dy"]) <= 1
    assert r["vertical"]["dy"] > 40 and abs(r["vertical"]["dx"]) <= 1
    d = r["diagonal"]
    assert d["dx"] > 30
    assert abs(d["dx"] - d["dy"]) <= 1.5


def test_s145_shift_arrow_nudges_ten_pixels(results: dict) -> None:
    n = _section(results, "s144_145")["nudge"]
    assert n["plain"] == pytest.approx(1, abs=0.1)
    assert n["shift"] == pytest.approx(10 * n["plain"], abs=0.2)
    assert n["shift_down"] == pytest.approx(10, abs=0.2)


# --- 07 S146 ---------------------------------------------------------------


@pytest.mark.parametrize("tool", ["line", "arrowline"])
def test_s146_lines_take_45_degree_steps(results: dict, tool: str) -> None:
    r = _section(results, "s146")[tool]
    assert r["ends"] == 2
    assert r["off45"] <= 0.5, r  # dragged at about 30 degrees
    e = r["end_drag"]
    assert e["dragKind"] in ("draw-end0", "draw-end1")
    assert e["off45"] <= 0.5, e  # dragged at about 20 degrees


def test_s146_alt_draws_from_the_centre(results: dict) -> None:
    r = _section(results, "s146")
    a = r["alt"]
    assert a["drawn"]
    assert a["centre_off"] <= EDGE_PX
    assert a["w"] == pytest.approx(100, abs=2)
    assert a["h"] == pytest.approx(60, abs=2)
    sq = r["alt_shift"]
    assert sq["drawn"]
    assert sq["centre_off"] <= EDGE_PX
    assert sq["w"] == pytest.approx(sq["h"], abs=1.5)


# --- 07 S147 ---------------------------------------------------------------


@pytest.mark.parametrize("variant", ["plain", "rot30"])
@pytest.mark.parametrize("side", ["e", "n"])
def test_s147_ctrl_shift_side_skews(results: dict, variant: str, side: str) -> None:
    r = _section(results, "s147")[f"{variant}/{side}"]
    assert r["dragKind"] == "sideskew"
    assert r["fixed_moved"] <= EDGE_PX, r
    kx, ky = r["skew"]
    if side == "e":
        assert abs(ky) > 0.05 and abs(kx) < 0.01, r
    else:
        assert abs(kx) > 0.05 and abs(ky) < 0.01, r
    assert r["hist_steps"] == 1


def test_s147_side_skew_refused_for_lines(results: dict) -> None:
    r = _section(results, "s147")["line"]
    assert not r["began"]
    assert not r["skew"] or all(abs(k) < 1e-6 for k in r["skew"])


# --- 07 S148 ---------------------------------------------------------------


def test_s148_crop_shift_corner_keeps_proportions(results: dict) -> None:
    r = _section(results, "s148")
    assert r["entered"]
    c = r["shift_corner"]
    assert c["shrank"] > 10
    assert c["crop"]
    assert c["after"] == pytest.approx(c["before"], rel=0.015)


def test_s148_enter_keeps_the_crop(results: dict) -> None:
    r = _section(results, "s148")
    assert r["enter"]["cropId"] == ""
    assert r["enter"]["crop"] == r["shift_corner"]["crop"]


def test_s148_esc_puts_the_crop_back(results: dict) -> None:
    e = _section(results, "s148")["esc"]
    assert e["changed_first"]
    assert e["cropId"] == ""
    assert e["crop_back"]
    assert e["box_back"] <= 0.5


def test_s148_flipped_crop_moves_the_side_you_see(results: dict) -> None:
    f = _section(results, "s148")["flipped"]
    assert f["right_moved"] == pytest.approx(-40, abs=2)
    assert abs(f["left_moved"]) <= EDGE_PX
    assert f["edge_off"] <= EDGE_PX


# --- 07 S149 ---------------------------------------------------------------


def test_s149_past_the_edge_mirrors(results: dict) -> None:
    r = _section(results, "s149")
    assert r["shape_e"]["flipH"] and not r["shape_e"]["flipV"]
    assert r["shape_e"]["w"] >= 8
    assert r["shape_e"]["right_edge_now_left"] <= 1
    assert r["shape_s"]["flipV"] and not r["shape_s"]["flipH"]
    assert r["picture_w"]["flipH"]
    assert r["picture_w"]["edge_off"] <= EDGE_PX


# --- 07 S150 ---------------------------------------------------------------


@pytest.mark.parametrize("kind", ["resize", "move", "rotate"])
def test_s150_esc_cancels_a_drag(results: dict, kind: str) -> None:
    r = _section(results, "s150")[kind]
    assert r["dragKind"], r
    assert r["changed_mid"], r
    assert r["dragKind_after_esc"] == ""
    assert r["back_at_esc"] <= 0.5
    assert r["back_after_release"] <= 0.5
    assert r["rot_same"]
    assert r["hist_after"] == r["hist_before"]
    assert len(r["selected"]) == 1


# --- 07 S153 ---------------------------------------------------------------


def test_s153_group_corner_keeps_proportions(results: dict) -> None:
    r = _section(results, "s153")["corner"]
    # The selection box's handles are named tl, t, tr, r, br, b, bl, l.
    assert r["handle"] == "br"
    assert r["dragKind"] == "groupresize"
    assert r["kx"] > 1.05
    assert r["bounds_ratio"][1] == pytest.approx(r["bounds_ratio"][0], rel=0.015)
    for kx, ky in zip(r["rect_kx"], r["rect_ky"]):
        assert kx == pytest.approx(r["kx"], rel=0.02)
        assert ky == pytest.approx(kx, rel=0.02)
    assert r["chip_size"] == [pytest.approx(0, abs=0.5), pytest.approx(0, abs=0.5)]
    assert r["chip_moved"] > 1
    assert r["hist_steps"] == 1


def test_s153_group_side_stretches(results: dict) -> None:
    r = _section(results, "s153")["side"]
    assert r["handle"] == "r"
    assert r["kx"] > 1.05
    assert r["ky"] == pytest.approx(1, abs=0.01)
    for ky in r["rect_ky"]:
        assert ky == pytest.approx(1, abs=0.01)
    assert r["chip_size"] == [pytest.approx(0, abs=0.5), pytest.approx(0, abs=0.5)]
    assert r["hist_steps"] == 1


# --- 07 S154 ---------------------------------------------------------------


def test_s154_reset_shape_restores_picture_proportions(results: dict) -> None:
    r = _section(results, "s154")
    assert r["aspect"] == pytest.approx(2)
    w = r["with_hook"]
    assert abs(w["stretched"] - 2) > 0.2
    assert w["after"] == pytest.approx(2, rel=0.01)
    assert abs(w["dw"]) <= 0.5
    assert w["centre_moved"] <= 0.5


def test_s154_reset_shape_without_hook_keeps_size(results: dict) -> None:
    r = _section(results, "s154")
    assert not r["aspect_no_hook"]
    assert abs(r["no_hook"]["dw"]) <= 0.5
    assert abs(r["no_hook"]["dh"]) <= 0.5


# --- 07 S155 ---------------------------------------------------------------


def test_s155_properties_link_keeps_proportions(results: dict) -> None:
    r = _section(results, "s155")
    assert r["default_on"] is True
    lk = r["linked"]
    assert lk["w1"] == pytest.approx(lk["w0"] * 2, abs=0.15)
    assert lk["h1"] == pytest.approx(lk["h0"] * 2, abs=0.15)
    assert lk["hist_steps"] == 1
    assert r["undo"]["w"] == pytest.approx(lk["w0"], abs=0.1)
    assert r["undo"]["h"] == pytest.approx(lk["h0"], abs=0.1)


def test_s155_properties_link_off(results: dict) -> None:
    r = _section(results, "s155")
    assert r["link_found"]
    assert r["after_click"] is False
    u = r["unlinked"]
    assert u["w1"] == pytest.approx(u["w0"] * 1.5, abs=0.15)
    assert u["h1"] == pytest.approx(u["h0"], abs=0.05)


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
