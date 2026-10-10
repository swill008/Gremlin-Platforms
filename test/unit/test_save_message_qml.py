# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""File › Save that wrote the profile but not OSC's file (04 S13).

The main window is built off-screen (journey harness, its own process).
The profile is saved once, then OSC's file write is made to fail and the
user picks File › Save: the result shown, and the line noted for the save
history, name the file that was not written instead of saying the profile
was not written.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402


def story(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import osc_device_file, util

    out = j.out
    path = util.profiles_dir() / "save_message.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    out["first-save"] = j.backend.saveProfile(url)

    def refuse() -> None:
        raise OSError(28, "No space left on device", str(osc_device_file.path()))

    osc_device_file.save_if_dirty = refuse  # type: ignore[assignment]
    noted: list[str] = []
    j.backend.saveNoted.connect(noted.append)

    # File › Save, as the menu runs it.
    j.ev("saveCurrentProfile(); true")
    j.wait_until(lambda: j.ev("_saveResultDialog.opened"), "the save result")
    out["title"] = j.ev("_saveResultDialog.titleText")
    out["message"] = j.ev("_saveResultDialog.messageText")
    out["noted"] = list(noted)
    out["problem"] = j.backend.saveProblem()


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("save_message"))


def test_the_save_result_names_the_file_not_written(run: dict) -> None:
    assert step(run, "first-save") is True
    problem = step(run, "problem")
    assert "OSC's file" in problem
    message = step(run, "message")
    assert message == problem
    assert "Not written" not in message
    assert step(run, "title") == "Save Failed"


def test_the_noted_line_names_the_file_not_written(run: dict) -> None:
    noted = step(run, "noted")
    assert noted and "OSC's file" in noted[-1]
    assert noted[-1] != "The profile was not written."


if __name__ == "__main__":
    Journey().run(story)
