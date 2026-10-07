# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 Q13 (D-04-Q13-NOWAIT) on the Scripts page: Add Script returns at once
while the script's code still runs; the row says "Starting…" (its settings
button off) and the main thread keeps running; when the time limit passes
the row says why it can't load. A normal script's settings button turns on
once it has started.

Driven through the real window, off-screen, in its own process (the journey
harness), with the time limit made short.
"""

from __future__ import annotations

import pathlib
import sys
import time

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "test" / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402

LOOPS = (
    "import threading\n"
    "import gremlin.user_script as us\n"
    "threading.Event().wait(20)\n"
    "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n"
)
GOOD = (
    "import gremlin.user_script as us\n"
    "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n"
)


def story(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import user_script, util

    user_script.TOP_LEVEL_TIME_LIMIT = 1.5
    out = j.out
    folder = pathlib.Path(util.scripts_dir())
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "loops.py").write_text(LOOPS, encoding="utf-8")
    (folder / "good.py").write_text(GOOD, encoding="utf-8")

    j.backend.ui_state.setCurrentRoom("scripts")
    j.backend.ui_state.setCurrentTab("scripts")
    j.settle()

    def rows() -> dict[str, dict]:
        """Each script row: its texts and whether its settings button is on."""
        found: dict[str, dict] = {}
        for item in j.walk(j.win.contentItem()):
            if item.property("loadError") is None or item.property("path") is None:
                continue
            texts = [
                str(it.property("text"))
                for it in j.walk(item)
                if it.isVisible() and it.property("text") not in (None, "")
            ]
            found[pathlib.Path(str(item.property("path"))).name] = {
                "texts": texts,
                "starting": item.property("starting"),
            }
        return found

    ticks = [0]
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: ticks.__setitem__(0, ticks[0] + 1))
    timer.start(20)

    model = j.ev("_scriptLoader.item.scriptListModel")
    url = QtCore.QUrl.fromLocalFile(str(folder / "loops.py")).toString()
    started = time.monotonic()
    model.addScript(url)
    out["add-seconds"] = round(time.monotonic() - started, 2)
    j.wait_until(lambda: "loops.py" in rows(), "the loops.py row")
    out["loops-at-once"] = rows()["loops.py"]
    j.wait_until(
        lambda: any("Can't load" in t for t in rows()["loops.py"]["texts"]),
        "the loops.py row says why",
        10,
    )
    out["loops-after"] = rows()["loops.py"]
    out["ticks"] = ticks[0]

    # The main thread busy meanwhile (the rows read again and again): a
    # normal script still starts well within its limit.
    url = QtCore.QUrl.fromLocalFile(str(folder / "good.py")).toString()
    started = time.monotonic()
    model.addScript(url)
    j.wait_until(lambda: "good.py" in rows(), "the good.py row")
    j.wait_until(lambda: rows()["good.py"]["starting"] is False, "good.py started")
    out["good-seconds"] = round(time.monotonic() - started, 2)
    out["good-after"] = rows()["good.py"]
    out["good-variables"] = [
        s.path.name + ":" + ",".join(s.variables)
        for s in j.profile.scripts.scripts
        if s.path.name == "good.py"
    ]
    timer.stop()


def main() -> None:
    Journey().run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("g4_scripts"))


def test_add_returns_at_once_and_the_row_says_starting(run: dict) -> None:
    assert step(run, "add-seconds") < 0.75, run
    row = step(run, "loops-at-once")
    assert row["starting"] is True, row
    assert "Starting…" in row["texts"], row


def test_the_row_says_why_when_the_limit_passes(run: dict) -> None:
    row = step(run, "loops-after")
    assert row["starting"] is False, row
    assert "Starting…" not in row["texts"], row
    assert any(
        "Can't load: Its top-level code did not finish within 1.5 s" in t
        for t in row["texts"]
    ), row
    # The main thread ran meanwhile (a 20 ms timer, over at least 1.5 s).
    assert step(run, "ticks") >= 30


def test_a_normal_script_has_started(run: dict) -> None:
    row = step(run, "good-after")
    assert row["starting"] is False
    assert not any("Can't load" in t for t in row["texts"]), row
    assert "Starting…" not in row["texts"], row
    assert step(run, "good-variables") == ["good.py:speed"]
    assert step(run, "good-seconds") < 1.5


if __name__ == "__main__":
    main()
