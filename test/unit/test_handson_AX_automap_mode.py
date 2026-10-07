# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""08 S108 (D-08-AUTOMAP-MODE): the mode the Auto Mapper works in.

S108: the Auto Mapper's Select Mode starts on the toolbar's mode, and the
result names the mode the actions went into; when that is not the toolbar's
mode it says so. Driven through the real window, off-screen, in its own
process (the journey harness): a profile with "Z Mode" and, under it,
"Default", the toolbar on "Z Mode". The old window started on the first mode
by name ("Default"; a parent named "A Mode" would sort first and hide that)
and the result named no mode.

The result line itself and S109 are in test_handson_AX_automap_reason.py.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "test" / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402

# "Default" sorts before "Z Mode", so a window that starts on the first mode
# by name does not start on the toolbar's.
PARENT = "Z Mode"


def story(j: Journey) -> None:
    from gremlin import signal

    out = j.out
    profile = j.profile
    profile.modes.add_mode(PARENT)
    profile.modes.set_parent("Default", PARENT)
    signal.signal.modesChanged.emit()
    j.backend.uiState.setCurrentMode(PARENT)

    j.ev('Helpers.createComponent("DialogAutoMapper.qml", { initialSlug: "pjoy_pro" })')
    win = j.window("Auto Mapper")

    def boxes() -> dict[str, object]:
        return {
            str(it.property("text")): it
            for it in j.walk(win.contentItem())
            if it.metaObject().className().startswith("CheckBox")
        }

    j.wait_until(lambda: "vJoy 1" in boxes(), "the module lists")
    j.ev("toggle(); true", boxes()["vJoy 1"])
    out["starts-on"] = j.ev("_modeSelector.currentText", win)

    def choose(mode: str) -> None:
        # As picking it from the list does.
        j.ev(
            f"_modeSelector.currentIndex = _modeSelector.find({mode!r});"
            f" _modeSelector.activated(_modeSelector.currentIndex); true",
            win,
        )

    def create() -> str:
        j.ev("_statusMessage.text = ''", win)
        button = next(
            it
            for it in j.walk(win.contentItem())
            if it.property("text") == "Create 1:1 Actions"
        )
        j.click(button)
        return j.wait_until(lambda: j.ev("_statusMessage.text", win), "the result")

    choose("Default")
    out["in-default"] = create()
    # The mode list is rebuilt after Create (the profile changed): the
    # choice stays.
    out["after-create"] = j.ev("_modeSelector.currentText", win)
    choose(PARENT)
    out["in-toolbar-mode"] = create()


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2])
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("ax_automap_mode"))


def test_select_mode_starts_on_the_toolbars_mode(run: dict) -> None:
    assert step(run, "starts-on") == PARENT


def test_result_names_the_mode_and_says_the_toolbar_shows_another(run: dict) -> None:
    text = step(run, "in-default")
    assert text.startswith("Made "), text
    assert " actions in Default; " in text, text
    assert f"The toolbar shows {PARENT}: switch to Default to see them." in text, text
    # D-08-AUTOMAP-NOTE stays.
    assert "not saved yet" in text, text
    assert step(run, "after-create") == "Default"


def test_no_toolbar_note_when_the_mode_is_the_toolbars(run: dict) -> None:
    text = step(run, "in-toolbar-mode")
    assert f" actions in {PARENT}; " in text, text
    assert "The toolbar shows" not in text, text


if __name__ == "__main__":
    main()
