# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Bindings Appearance per device, end to end on the real program
(batch J, 05 S125).

A journey (test/journeys/_harness.py): the app off-screen in its own
process with a temporary USERPROFILE, the fake "pJoy Pro" (device A) and a
second fake stick (device B). The shared Device Bindings look is saved
first (parentHeight 50), then on the Device Bindings page:

1. A shows the shared look; "Apply to all devices" is shown.
2. A: Input row height 70, Save Appearance: A's list shows 70, saved as
   A's own look; the shared look stays 50.
3. Switch to B (uiState.setCurrentDevice, as ‹ › does): B's list shows the
   shared 50 at once.
4. B: 60, Apply to all devices: the shared look is 60 and A's own look is
   gone; back on A its list shows 60.
5. Reset Appearance on A: A's defaults (44) saved as A's own look; B still
   shows 60.
6. The Keyboard page's panel has no scope and no Apply to all devices.
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    JourneyIncomplete,
    run_journey,
)

PAGE = "device-bindings"


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _find(root: Any, test: Any) -> Any:  # noqa: ANN401
    for item in Journey.walk(root):
        try:
            if test(item):
                return item
        except Exception:  # noqa: BLE001, S112
            continue
    return None


def _tree(j: Journey) -> Any:  # noqa: ANN401
    def find() -> Any:  # noqa: ANN401
        return _find(
            j.win.contentItem(),
            lambda i: i.property("namePrefix") == "deviceBindings"
            and i.property("dragMime") is not None
            and i.isVisible(),
        )

    return j.wait_until(find, "the Device Bindings list")


def _button(panel: Any, text: str) -> Any:  # noqa: ANN401
    found = _find(
        panel,
        lambda i: str(i.property("text") or "") == text
        and i.property("highlighted") is not None,
    )
    assert found is not None, f"no {text!r} button"
    return found


def _switch(j: Journey, page: Any, guid: str) -> None:  # noqa: ANN401
    j.ev(f"uiState.setCurrentDevice({guid!r}); true")
    j.wait_until(lambda: page.property("guid") == guid, f"the page on {guid}")
    j.settle()


def story(j: Journey) -> None:
    from gremlin.ui import window_placement

    out = j.out
    other = str(j.out.pop("_other"))
    window_placement.set_list_appearance(PAGE, {"parentHeight": 50})
    try:
        j.open_device_bindings("pjoy_pro")
        page = j.ev("deviceBindingsPane()")
        a = str(page.property("guid"))
        out["a-guid"] = a
        out["b-guid"] = other
        tree = _tree(j)
        panel = j.item(j.win, "deviceBindingsAppearance")
        assert panel is not None, "no Device Bindings Appearance panel"
        if not panel.isVisible():
            j.ev("toggleAppearance(); true", page)
            j.wait_until(panel.isVisible, "the Appearance panel")
        j.settle()
        apply_all = j.item(j.win, "applyAppearanceAll")
        out["1:tree"] = tree.property("parentHeight")
        out["1:apply-shown"] = apply_all is not None and apply_all.isVisible()

        panel.setProperty("parentHeight", 70)
        j.click(_button(panel, "Save\nAppearance"))
        j.settle()
        out["2:tree"] = tree.property("parentHeight")
        out["2:own-a"] = window_placement.has_own_list_appearance(PAGE, a)
        out["2:a"] = window_placement.list_appearance_for(PAGE, a).get("parentHeight")
        out["2:shared"] = window_placement.list_appearance(PAGE).get("parentHeight")

        _switch(j, page, other)
        out["3:tree"] = tree.property("parentHeight")
        out["3:panel"] = panel.property("parentHeight")

        panel.setProperty("parentHeight", 60)
        j.click(j.item(j.win, "applyAppearanceAll"))
        j.settle()
        out["4:shared"] = window_placement.list_appearance(PAGE).get("parentHeight")
        out["4:own-a"] = window_placement.has_own_list_appearance(PAGE, a)
        out["4:own-b"] = window_placement.has_own_list_appearance(PAGE, other)
        _switch(j, page, a)
        out["4:tree-a"] = tree.property("parentHeight")

        j.click(_button(panel, "Reset\nAppearance"))
        j.settle()
        out["5:tree-a"] = tree.property("parentHeight")
        out["5:own-a"] = window_placement.has_own_list_appearance(PAGE, a)
        out["5:a"] = window_placement.list_appearance_for(PAGE, a).get("parentHeight")
        out["5:shared"] = window_placement.list_appearance(PAGE).get("parentHeight")
        _switch(j, page, other)
        out["5:tree-b"] = tree.property("parentHeight")

        keyboard = j.item(j.win, "keyboardAppearance")
        out["6:keyboard-scope"] = (
            None if keyboard is None else keyboard.property("scopeKey")
        )
    except Exception as failed:  # noqa: BLE001
        out["error"] = f"{type(failed).__name__}: {failed}"
        out["traceback"] = traceback.format_exc()


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2])
        j.out["_other"] = str(j.add_stick("Other Stick", 3))

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("appearance_per_device"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    raise JourneyIncomplete(
        f"The journey never reached {key!r}.\n"
        f"Error: {out.get('error', '(none)')}\n{out.get('traceback', '')}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


def test_a_device_starts_with_the_shared_look(run: dict) -> None:
    assert _step(run, "1:tree") == 50
    assert _step(run, "1:apply-shown") is True


def test_save_on_a_device_writes_only_that_device(run: dict) -> None:
    assert _step(run, "2:tree") == 70
    assert _step(run, "2:own-a") is True
    assert _step(run, "2:a") == 70
    assert _step(run, "2:shared") == 50


def test_another_device_still_shows_the_shared_look(run: dict) -> None:
    assert _step(run, "3:tree") == 50
    assert _step(run, "3:panel") == 50


def test_apply_to_all_devices_reaches_every_device(run: dict) -> None:
    assert _step(run, "4:shared") == 60
    assert _step(run, "4:own-a") is False
    assert _step(run, "4:own-b") is False
    assert _step(run, "4:tree-a") == 60


def test_reset_on_a_device_leaves_the_others(run: dict) -> None:
    assert _step(run, "5:tree-a") == 44
    assert _step(run, "5:own-a") is True
    assert _step(run, "5:a") == 44
    assert _step(run, "5:shared") == 60
    assert _step(run, "5:tree-b") == 60


def test_other_pages_have_no_scope(run: dict) -> None:
    assert _step(run, "6:keyboard-scope") in ("", None)


if __name__ == "__main__":
    main()
