# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The running program off-screen (handson_F6_look_smoke.py, its own process
and user folder) at 100 %, 150 % and 175 % UI scale, light and dark.

03 S78 / D-03-Q8-NOFILE: a Home card for a device with no module file shows
the device's own counts; Keyboard, OSC and Xbox (nothing to count) don't.
09 Q16 / G6 / GL-200: the Keyboard page's action summary images follow the
UI scale (as tall next to the row text as at 100 %), drawn sharp at that
size (not an enlarged 100 % picture), with ink that suits the theme."""

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


@pytest.mark.parametrize("look", _LOOKS[1:])
def test_action_images_follow_the_ui_scale(runs: dict, look: tuple) -> None:
    base = runs[(100, "light")]
    out = runs[look]
    assert _get(out, "uiScale") == look[0]
    base_ratio = max(i["h"] for i in _get(base, "images")) / base["fontSize"]
    tallest = max(i["h"] for i in _get(out, "images"))
    # As tall next to the row text as at 100 % (21 px next to 15 px).
    ratio = tallest / out["fontSize"]
    assert abs(ratio - base_ratio) < 0.12, (tallest, out["fontSize"])
    # Shown at the size it was drawn (not stretched by the list).
    for image in out["images"]:
        assert abs(image["h"] - image["srcH"]) <= 1, image


@pytest.mark.parametrize("look", _LOOKS[1:])
def test_action_images_are_drawn_sharp_at_the_scale(runs: dict, look: tuple) -> None:
    out = runs[look]
    shown, enlarged = _get(out, "shown"), _get(out, "enlarged")
    # Drawn at the size shown: fewer soft edge pixels than the 100 %
    # picture enlarged to the same size.
    soft = shown["partial"] / shown["ink"]
    soft_enlarged = enlarged["partial"] / enlarged["ink"]
    assert soft < 0.9 * soft_enlarged, (shown, enlarged)


@pytest.mark.parametrize("look", _LOOKS)
def test_action_image_ink_suits_the_theme(runs: dict, look: tuple) -> None:
    out = runs[look]
    assert _get(out, "dark") == (look[1] == "dark")
    lum = out["shown"]["lum"]
    assert lum > 0.7 if look[1] == "dark" else lum < 0.4, out["shown"]
