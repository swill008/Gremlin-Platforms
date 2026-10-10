# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The running program off-screen (handson_F6_look_smoke.py, its own process
and user folder) at 100 %, 150 % and 175 % UI scale, light and dark.

03 S78 / D-03-Q8-NOFILE: a Home card for a device with no module file shows
the device's own counts; Keyboard, OSC and Xbox (nothing to count) don't.
(The Keyboard page's action summary images, 09 Q16 / GL-200, were removed
with the row icon strip: user decision AS1, 2026-10-10.)"""

from __future__ import annotations

import importlib.util
import pathlib
from typing import Any

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "handson_F6_look_smoke.py"
_LOOKS = [(100, "light"), (150, "dark"), (175, "light"), (175, "dark")]


def _harness() -> Any:  # noqa: ANN401
    spec = importlib.util.spec_from_file_location(
        "_f6_harness", _ROOT / "test" / "journeys" / "_harness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict:
    harness = _harness()
    found = {}
    for scale, theme in _LOOKS:
        home = tmp_path_factory.mktemp(f"f6-{scale}-{theme}")
        found[(scale, theme)] = harness.run_journey(_SMOKE, home, str(scale), theme)
    return found


def _get(out: dict, key: str) -> Any:  # noqa: ANN401
    assert key in out, f"{out.get('error')}\n{out.get('traceback', '')}"
    return out[key]


@pytest.mark.parametrize("look", _LOOKS)
def test_each_look_runs_in_its_own_theme(runs: dict, look: tuple) -> None:
    """The dark looks run in dark mode, the light ones in light mode."""
    assert _get(runs[look], "isDarkMode") is (look[1] == "dark")


def test_a_card_with_no_module_file_shows_the_devices_own_counts(runs: dict) -> None:
    cards = _get(runs[(100, "light")], "cards")
    stick = next(c for c in cards.values() if c["tab"] == "physical" and c["isStub"])
    assert stick["countsVisible"], cards
    assert stick["counts"].split() == ["64", "buttons", "6", "axes", "2", "hats"]


def test_keyboard_osc_and_xbox_cards_show_no_counts(runs: dict) -> None:
    cards = _get(runs[(100, "light")], "cards")
    for slug in ("keyboard", "osc", "xbox"):
        if slug in cards and cards[slug]["isStub"]:
            assert not cards[slug]["countsVisible"], (slug, cards[slug])
