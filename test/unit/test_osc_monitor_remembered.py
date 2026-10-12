# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The OSC Monitor's state is remembered (09 S137, D-09-MONITOR-REMEMBERED).

A journey (test/journeys/_harness.py) run four times with the same
temporary USERPROFILE, so each run after the first is a restart:

1. First start: the docked Monitor is folded. Unfold it, leave for the
   Keyboard page and come back: still open. Fold it: stays folded. × it:
   stays closed.
2. Restart: still closed. The page bar's Monitor shows it; fold it.
3. Restart: folded. Pop it out; leave the page and come back: the dock
   stays aside while the pop-out window is open.
4. Restart: popping out is never kept; the Monitor is docked and open, and
   no pop-out window opens.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
    step,
)

# +-------------------------------------------------------------------------
# | Script side (the child process)


def _page(j: Journey) -> Any:  # noqa: ANN401
    """Opens the OSC page; returns the page item."""
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: j.backend.uiState.currentTab == "osc", "the OSC page")

    def find() -> Any:  # noqa: ANN401
        for item in j.walk(j.win.contentItem()):
            if item.property("monitorShown") is not None and item.isVisible():
                return item
        return None

    page = j.wait_until(find, "the OSC page item")
    j.settle()
    return page


def _leave_and_back(j: Journey) -> Any:  # noqa: ANN401
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(
        lambda: j.backend.uiState.currentTab == "keyboard", "the Keyboard page"
    )
    j.settle()
    return _page(j)


def _pop_out_open() -> bool:
    from PySide6.QtGui import QGuiApplication

    return any(
        w.title() == "OSC Monitor" and w.isVisible()
        for w in QGuiApplication.topLevelWindows()
    )


def _state(j: Journey, page: Any) -> str:  # noqa: ANN401
    panel = j.item(j.win, "oscMonitorPanel")
    shown = bool(page.property("monitorShown"))
    if _pop_out_open():
        return "popped" if not shown else "popped+docked"
    if not shown:
        return "closed"
    return "folded" if panel.property("folded") else "open"


def story(j: Journey) -> None:
    run = sys.argv[1]
    out = j.out
    page = _page(j)
    out["start"] = _state(j, page)
    panel = j.item(j.win, "oscMonitorPanel")
    if run == "1":
        panel.setProperty("folded", False)
        j.settle()
        page = _leave_and_back(j)
        out["unfolded"] = _state(j, page)
        j.item(j.win, "oscMonitorPanel").setProperty("folded", True)
        j.settle()
        page = _leave_and_back(j)
        out["folded"] = _state(j, page)
        j.click(j.item(j.win, "oscMonitorClose"))
        j.settle()
        page = _leave_and_back(j)
        out["closed"] = _state(j, page)
    elif run == "2":
        j.ev("toggleMonitor(); true", page)
        j.settle()
        out["shown"] = _state(j, page)
        j.item(j.win, "oscMonitorPanel").setProperty("folded", True)
        j.settle()
    elif run == "3":
        j.click(j.item(j.win, "oscMonitorPopOut"))
        j.wait_until(_pop_out_open, "the pop-out window")
        out["popped"] = _state(j, page)
        page = _leave_and_back(j)
        out["popped-back"] = _state(j, page)
    # Quitting writes the settings (the journey ends without a real quit).
    from gremlin import deferred_write

    deferred_write.flush_all()


def main() -> None:
    Journey().run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> list[dict]:
    home = tmp_path_factory.mktemp("osc_monitor_remembered")
    return [run_journey(__file__, home, str(n)) for n in (1, 2, 3, 4)]


def test_first_start_is_folded_and_each_state_is_kept_across_pages(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert step(first, "start") == "folded"
    assert step(first, "unfolded") == "open"
    assert step(first, "folded") == "folded"
    assert step(first, "closed") == "closed"


def test_closed_and_folded_are_kept_after_a_restart(runs: list[dict]) -> None:
    assert step(runs[1], "start") == "closed"
    assert step(runs[1], "shown") == "open"
    assert step(runs[2], "start") == "folded"


def test_a_popped_out_monitor_comes_back_docked_and_open_after_a_restart(
    runs: list[dict],
) -> None:
    assert step(runs[2], "popped") == "popped"
    # Leaving the page with the pop-out open: the dock stays aside.
    assert step(runs[2], "popped-back") == "popped"
    assert step(runs[3], "start") == "open"


if __name__ == "__main__":
    main()
