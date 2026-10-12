# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox Output View with one section per pad (D-XBOX-PADS, 03 S139): a
red line only when the ViGEmBus driver is missing (its link asks Main for
Xbox Setup), the Find bar once for every pad, then one foldable section per
pad that is on and bound (a header drawn like the list's group rows from the
Appearance, face, chip rows per device, the pad's own list, a border round
it, "Space between groups" apart; "Show only bound controls" ticked first),
each remembered, all open the first time; nothing bound shows one line and
hides the Find bar and Appearance. The Xbox Viewer window, its toolbar
button and Tools item stay gone; Help's Open link and the card's viewer
entry open this page.

Runs the real main window off-screen in its own process (fake hardware, a
temp USERPROFILE, no update check, the Xbox driver reported missing).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import proc_tree  # noqa: E402  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
_SMOKE = _HERE / "xbox_output_view_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
               HTTPS_PROXY="http://127.0.0.1:9")
    args = [sys.executable, str(_SMOKE)]
    shot = os.environ.get("GREMLIN_SHOT")
    if shot:
        args.append(shot)
    done = proc_tree.run(args, cwd=_ROOT, env=env, text=True, encoding="utf-8",
                         errors="replace", timeout=150)
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, (done.stdout + done.stderr)[-3000:]
    return json.loads(lines[-1][len("RESULT "):])


def test_no_errors(run: dict) -> None:
    assert run["errors"] == []


def test_the_viewer_window_file_is_gone() -> None:
    assert not (_ROOT / "qml" / "DialogXboxViewer.qml").exists()


def test_no_toolbar_button_and_no_tools_menu_item(run: dict) -> None:
    assert run["button"] == "undefined"
    assert "Xbox Viewer" not in run["captions"]
    assert "tools.xboxViewer" not in run["commands"]


def test_help_open_link_goes_to_the_output_view(run: dict) -> None:
    assert "view.xboxOutput" in run["commands"]
    assert "view.xboxOutput" in run["helpAllowed"]
    assert "tools.xboxViewer" not in run["helpAllowed"]
    assert run["paletteHidden"] is True
    assert run["openRoom"] == ["configuration", "xbox"]
    assert run["openWindows"] == []


MISSING = "ViGEmBus driver not found: the Xbox pads can't be sent."
EMPTY = (
    "No Xbox controller has a binding yet. Add a Map to Xbox action on "
    "Device Bindings to see it here."
)


def test_red_line_when_the_driver_is_missing_then_find_then_pads(run: dict) -> None:
    page = run["open"]
    assert page["loaded"] is True
    assert page["missingShown"] is True and page["missingText"] == MISSING
    assert page["linkShown"] is True and page["linkText"] == "Open Xbox Setup"
    assert page["findShown"] is True and page["findInScroll"] is True
    assert page["emptyShown"] is False
    pads = page["pads"]
    # Pads 1 and 2 are on and bound; pad 3 is bound but off: no section.
    assert sorted(pads) == ["1", "2"] and page["sections"] == 2
    tops = [page["missingTop"], page["findTop"], pads["1"]["top"], pads["2"]["top"]]
    assert tops[0] >= 0 and tops == sorted(set(tops)), tops


def test_no_red_line_when_the_driver_is_found(run: dict) -> None:
    found = run["found"]
    assert found["missingShown"] is False and found["linkShown"] is False


def test_the_link_asks_for_xbox_setup(run: dict) -> None:
    assert run["setupAsked"] == 1


def test_each_pad_section_has_header_face_chips_and_its_list(run: dict) -> None:
    pads = run["open"]["pads"]
    one, two = pads["1"], pads["2"]
    assert one["open"] is True and two["open"] is True  # all open at first
    assert "Xbox 360 1" in one["texts"] and "Xbox 360 2" in two["texts"]
    assert "Driven by: Test Stick" in one["texts"]
    assert "2 controls bound" in one["texts"] and "1 control bound" in two["texts"]
    assert one["faceShown"] and one["facePad"] == 1 and one["faceAbove"]
    assert two["faceShown"] and two["facePad"] == 2
    assert "Mapped axes" in one["texts"] and "Mapped buttons" in one["texts"]
    assert "Mapped axes" not in two["texts"]  # pad 2 has no axis
    assert one["chips"] == [["X", "LX"], ["1", "A"]]
    assert one["lines"] == ["Test Stick"]


def test_each_list_is_the_shared_list_view_only_in_the_page_scroll(
    run: dict,
) -> None:
    for pad in run["open"]["pads"].values():
        assert pad["treeShown"] is True and pad["treeInScroll"] is True
        assert pad["treeReadOnly"] is True
        assert pad["treeGroups"] is False
        assert pad["treeOwnScroll"] is False
        assert pad["treeFull"] is True
    # "Show only bound controls" is ticked the first time: pad 1 shows A
    # and Left Stick X, pad 2 shows B.
    assert run["tickFirst"] is True
    assert run["open"]["pads"]["1"]["rows"] == 2
    assert run["open"]["pads"]["2"]["rows"] == 1


def test_one_find_bar_filters_every_pad(run: dict) -> None:
    assert run["find"] == {"1": 1, "2": 0}  # bound and "Left Stick": LSX
    assert run["findCleared"] == {"1": 2, "2": 1}


def test_pad_headers_use_the_appearance_group_look(run: dict) -> None:
    look = run["look"]
    assert look["headers"] == [look["group"], look["group"]]
    assert look["headerBorders"] == [look["border"], look["border"]]
    assert look["titleColours"] == [look["text"], look["text"]]
    changed = run["lookChanged"]
    assert changed["group"] == "#ff123456"
    assert changed["headers"] == ["#ff123456", "#ff123456"]


def test_each_pad_section_has_a_border(run: dict) -> None:
    look = run["look"]
    assert look["sectionBorders"] == [look["border"], look["border"]]
    assert all(w and w >= 1 for w in look["sectionBorderWidths"])


def test_sections_are_space_between_groups_apart(run: dict) -> None:
    assert run["look"]["spacing"] == 0 and run["look"]["gap"] == 0
    changed = run["lookChanged"]
    assert changed["spacing"] > 0  # Style.dp(20)
    assert changed["gap"] == changed["spacing"]


def test_the_list_has_its_own_appearance_button(run: dict) -> None:
    assert run["listAppearanceButton"] is True
    assert run["outputAppearanceButton"] is False
    assert run["pageKey"] == "xbox-output"


def test_folding_one_pad_is_remembered_per_pad(run: dict) -> None:
    folded = run["folded"]["pads"]
    assert folded["2"]["open"] is False
    assert folded["2"]["headingShown"] is True
    assert not folded["2"]["faceShown"] and not folded["2"]["treeShown"]
    assert folded["2"]["chips"] == []
    assert folded["1"]["open"] is True and folded["1"]["treeShown"] is True
    assert run["closedLoaded"] is False
    again = run["reopenedFolded"]["pads"]
    assert again["2"]["open"] is False and again["1"]["open"] is True
    assert run["reopened"]["pads"]["2"]["faceShown"] is True


def test_a_pad_turned_off_loses_its_section(run: dict) -> None:
    assert sorted(run["padsOne"]["pads"]) == ["1"]


def test_nothing_bound_shows_one_line_and_hides_find_and_appearance(
    run: dict,
) -> None:
    empty = run["empty"]
    assert empty["sections"] == 0 and empty["pads"] == {}
    assert empty["emptyShown"] is True and empty["emptyText"] == EMPTY
    assert empty["findShown"] is False
    assert run["emptyAppearanceButton"] is False


def test_the_cards_viewer_entry_opens_the_output_view(run: dict) -> None:
    assert run["pairingRoom"] == ["configuration", "xbox"]
    assert run["pairingWindows"] == []
