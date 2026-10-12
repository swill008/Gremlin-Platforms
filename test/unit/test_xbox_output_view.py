# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox Viewer moved into the Xbox output's Output View (D-NEXTLIST-1
item 1; user 1a, 2b, 2026-10-12): one ViGEmBus check at the top, then the
live pad of each device that drives it in a section that folds (open by
default, remembered), then the control rows, all in one scroll. The toolbar
button, Tools › Viewers › Xbox Viewer and the viewer window are gone; the
card's viewer entry and Help's Open link open the Output View.

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


def test_one_driver_check_then_pads_then_rows_in_one_scroll(run: dict) -> None:
    page = run["open"]
    assert page["loaded"] is True
    assert page["driverRows"] == 1
    assert page["padsOpen"] is True  # open by default
    assert page["cardShown"] is True
    order = ["driverTop", "headingTop", "cardTop", "findTop", "controlTop"]
    tops = [page[key] for key in order]
    assert tops[0] >= 0 and tops == sorted(set(tops)), dict(zip(order, tops))
    assert page["cardInScroll"] is True and page["controlInScroll"] is True
    assert page["findInScroll"] is True and page["treeInScroll"] is True


def test_the_rows_are_the_shared_list_view_only_and_scroll_with_the_pads(
    run: dict,
) -> None:
    page = run["open"]
    assert page["treeReadOnly"] is True
    assert page["treeGroups"] is False
    assert page["treeOwnScroll"] is False
    assert page["treeFull"] is True


def test_the_list_has_its_own_appearance_button(run: dict) -> None:
    assert run["listAppearanceButton"] is True
    assert run["outputAppearanceButton"] is False
    assert run["pageKey"] == "xbox-output"


def test_folding_hides_the_pads_and_is_remembered(run: dict) -> None:
    folded = run["folded"]
    assert folded["padsOpen"] is False
    assert folded["cardShown"] is False
    assert folded["controlTop"] > 0  # the rows stay
    assert run["closedLoaded"] is False
    again = run["reopenedFolded"]
    assert again["padsOpen"] is False and again["cardShown"] is False
    assert run["reopened"]["cardShown"] is True


def test_the_cards_viewer_entry_opens_the_output_view(run: dict) -> None:
    assert run["pairingRoom"] == ["configuration", "xbox"]
    assert run["pairingWindows"] == []
