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
    from PySide6 import QtCore

    import dill
    from gremlin import plugin_manager
    from gremlin.config import Configuration
    from gremlin.types import InputType
    from gremlin.ui.action_image_generator import ActionSummaryImageProvider

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

    # --- Keyboard page images (09 Q16 / GL-200) ---
    Configuration().set("ui", "general", "dark-mode", THEME == "dark")
    j.backend.emitConfigChanged()
    j.wait_until(
        lambda: bool(j.ev("Style.isDarkMode")) == (THEME == "dark"), "theme"
    )
    out["dark"] = j.ev("Style.isDarkMode")
    pm = plugin_manager.PluginManager()

    def key(code: int, names: list[tuple[str, dict]]) -> None:
        item = j.profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, (code, False), "Default", True
        )
        binding = item.add_item_binding()
        for name, attrs in names:
            action = pm.create_instance(name, InputType.JoystickButton)
            for k, v in attrs.items():
                setattr(action, k, v)
            binding.root_action.insert_action(action, "children")

    vjoy = {"vjoy_device_id": 1, "vjoy_input_id": 12,
            "vjoy_input_type": InputType.JoystickButton}
    key(0x1E, [("Map to vJoy", vjoy)])
    key(0x30, [("Map to Keyboard", {})])
    key(0x20, [("Map to vJoy", vjoy), ("Map to Keyboard", {}), ("Macro", {})])
    key(0x12, [("Map to Xbox", {})])

    j.ev('openConfigurationForCard(_moduleModel.cardMap("keyboard"))')
    state = j.backend.uiState
    j.wait_until(lambda: state.currentTab == "keyboard", "Keyboard page")

    def images() -> list:
        found = []
        for item in j.walk(j.win.contentItem()):
            src = item.property("source")
            if (
                isinstance(src, QtCore.QUrl)
                and src.toString().startswith("image://action_summary/")
                and item.isVisible()
                and item.property("sourceSize").width() > 0  # loaded
            ):
                found.append(item)
        return found

    j.wait_until(lambda: len(images()) >= 4, "action summary images")
    rows = []
    for item in images():
        size = item.property("sourceSize")
        rows.append({
            "src": item.property("source").toString(),
            "h": round(item.height()),
            "srcW": size.width(), "srcH": size.height(),
        })
    out["images"] = rows
    if SHOTS:
        shot = pathlib.Path(SHOTS) / f"f6-keyboard-{SCALE}-{THEME}.png"
        j.win.grabWindow().save(str(shot))

    # The images themselves, from the program's provider, by the ids shown.
    provider = ActionSummaryImageProvider()
    widest = max(rows, key=lambda r: r["srcW"])
    image_id = widest["src"][len("image://action_summary/"):]
    image_id = QtCore.QUrl.fromPercentEncoding(image_id.encode())
    shown_image = provider.requestImage(image_id, QtCore.QSize(), QtCore.QSize())
    out["shown"] = _alpha_stats(shown_image)
    out["shownSize"] = [shown_image.width(), shown_image.height()]
    # The same picture drawn at 100 % and enlarged: what sharp must beat.
    plain_id = re.sub(r"([?&])s=\d+", r"\1s=100", image_id)
    if "s=" not in plain_id:
        plain_id += "&s=100"
    plain = provider.requestImage(plain_id, QtCore.QSize(), QtCore.QSize())
    enlarged = plain.scaled(
        shown_image.width(), shown_image.height(),
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    out["enlarged"] = _alpha_stats(enlarged)


def main() -> None:
    def before(_j: Journey) -> None:
        from gremlin.ui import ui_scale_option

        ui_scale_option.active_scale = lambda: SCALE  # type: ignore[assignment]

    Journey(before).run(story)


if __name__ == "__main__":
    main()
