# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The running program off-screen at a UI scale and theme (args: <scale>
<light|dark>): Home's cards (counts line) and the Keyboard page's action
summary images (size, sharpness, ink). test_handson_F6_look.py runs it in
its own process with a fresh user folder (journey harness).

    python test/unit/handson_F6_look_smoke.py 175 light

F6_SHOTS=<folder>: also saves window pictures there.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey  # noqa: E402

SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 100
THEME = sys.argv[2] if len(sys.argv) > 2 else "light"
SHOTS = os.environ.get("F6_SHOTS", "")
_COUNTS = re.compile(r"^\d+ buttons? ")


def _alpha_stats(image: object) -> dict:
    """Ink pixels of an image: how many, how many only partly covered (soft
    edges: an enlarged picture has more), and the most covered pixel's
    lightness."""
    from PySide6 import QtGui

    img = image.convertToFormat(QtGui.QImage.Format.Format_ARGB32)  # type: ignore[attr-defined]
    ink = partial = 0
    best = (-1, 0.0)
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            a = c.alpha()
            if a == 0:
                continue
            ink += 1
            if a < 230:
                partial += 1
            if a > best[0]:
                lum = 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()
                best = (a, lum)
    return {"ink": ink, "partial": partial, "lum": round(best[1], 3)}


def story(j: Journey) -> None:


    out = j.out
    j.win.setProperty("visible", True)
    j.win.setWidth(1600)
    j.win.setHeight(1000)
    out["uiScale"] = j.ev("Style.uiScale")
    out["fontSize"] = j.ev("Style.fontSize")

    # --- Home cards (03 S78 / D-03-Q8-NOFILE) ---
    def cards() -> list:
        return [
            c for c in j.walk(j.win.contentItem())
            if c.metaObject().indexOfSignal("cardFocused()") >= 0
            and c.isVisible() and c.width() > 0
        ]

    j.wait_until(lambda: len(cards()) >= 3, "Home cards")
    shown = {}
    for card in cards():
        line = next(
            (
                it for it in j.walk(card)
                if isinstance(it.property("text"), str)
                and _COUNTS.match(it.property("text"))
            ),
            None,
        )
        shown[card.property("slug")] = {
            "tab": card.property("tab"),
            "isStub": card.property("isStub"),
            "isModule": card.property("isModule"),
            "buttons": card.property("buttons"),
            "counts": line.property("text") if line is not None else None,
            "countsVisible": bool(line is not None and line.isVisible()),
        }
    out["cards"] = shown
    if SHOTS:
        shot = pathlib.Path(SHOTS) / f"f6-home-{SCALE}-{THEME}.png"
        j.win.grabWindow().save(str(shot))


def main() -> None:
    def before(_j: Journey) -> None:
        from gremlin.ui import ui_scale_option

        ui_scale_option.active_scale = lambda: SCALE  # type: ignore[assignment]

    Journey(before).run(story)


if __name__ == "__main__":
    main()
