# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fix G2 (N22): the Merge Axis editor fits the action pane.

At the pane's default width the "Second axis" Rec button and Add Action
sat past the pane's right edge until the pane was widened (hands-on 05,
c4_merge_recorded.png). Every control of the editor now lies inside it,
at 100 % and 175 %.

Driven through the real program off-screen (the journey harness): the X
Axis pane opened as a row's Add Action opens it, a Merge Axis added there,
both axes recorded so their names are shown.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402

SCALE = int(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) > 1 else 100
SHOT = sys.argv[2] if __name__ == "__main__" and len(sys.argv) > 2 else ""
# A wider pane (the user widened it): the lists beside their labels.
UNITS = int(sys.argv[3]) if __name__ == "__main__" and len(sys.argv) > 3 else 0


def _items(item):  # noqa: ANN001, ANN202
    yield item
    for c in item.childItems():
        yield from _items(c)


def _shown(item) -> bool:  # noqa: ANN001
    p = item
    while p is not None:
        if not p.isVisible() or p.opacity() == 0:
            return False
        p = p.parentItem()
    return True


def story(j: Journey) -> None:
    from PySide6 import QtCore

    out = j.out
    j.win.setWidth(1600)
    j.win.setHeight(950)
    j.QTest.qWait(300)
    catalog = j.open_configuration("pjoy_pro")
    page = j.ev("catalogPane()")
    hid = j.device_index(catalog, "axis", 1)
    j.ev(f"openAdvancedPane({hid}); true", page)
    j.wait_until(lambda: catalog.paneModel is not None, "the pane")
    if UNITS:
        j.ev(f"paneUnits = {UNITS}; true", page)
    root = j.wait_until(lambda: j.pane_actions(catalog)[0], "the root action")
    root.appendAction("Merge Axis", "children")
    editor = j.wait_until(
        lambda: next(
            (
                it
                for it in _items(j.win.contentItem())
                if it.metaObject().className().startswith("MergeAxisAction")
                and _shown(it)
            ),
            None,
        ),
        "the Merge Axis editor",
    )
    # Both axes recorded as the Rec buttons do (the selected input).
    merge = j.pane_actions(catalog)[1]
    current = j.backend.uiState.currentInput
    merge.firstAxis = current
    merge.secondAxis = current
    j.QTest.qWait(400)
    out["labels"] = [merge.firstAxis.label, merge.secondAxis.label]
    out["page-width"] = page.width()
    out["pane-units"] = j.ev("paneUnits", page)
    out["wide"] = next(
        (
            it.property("wide")
            for it in _items(editor)
            if it.property("wide") is not None
        ),
        None,
    )

    left = editor.mapToScene(QtCore.QPointF(0, 0)).x()
    right = editor.mapToScene(QtCore.QPointF(editor.width(), 0)).x()
    out["editor"] = [round(left), round(right)]
    past = []
    for it in _items(editor):
        if it is editor or not _shown(it) or it.width() <= 0:
            continue
        name = it.metaObject().className()
        if not (it.inherits("QQuickControl") or it.inherits("QQuickText")):
            continue
        # Only what the editor itself draws (not child actions).
        p, own = it.parentItem(), True
        while p is not None and p is not editor:
            if p.metaObject().className().startswith("ActionNode"):
                own = False
                break
            p = p.parentItem()
        if not own:
            continue
        at = it.mapToScene(QtCore.QPointF(0, 0)).x()
        end = at + it.width()
        if end > right + 0.5 or at < left - 0.5:
            past.append([name, str(it.property("text") or ""), round(at), round(end)])
    out["past-edge"] = past
    if SHOT:
        j.win.grabWindow().save(SHOT)


def main() -> None:
    def before(j: Journey) -> None:
        from gremlin.ui import ui_scale_option

        ui_scale_option.active_scale = lambda: SCALE  # type: ignore[assignment]
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module", params=[(100, 0), (175, 0), (100, 900)], ids=str)
def run(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> dict:
    import os

    scale, units = request.param
    shot = os.environ.get("GREMLIN_SHOT", "")
    if shot:
        shot = shot.replace(".png", f"-{scale}-{units}.png")
    return run_journey(
        __file__, tmp_path_factory.mktemp("g2merge"), str(scale), shot, str(units)
    )


def test_both_axes_are_named(run: dict) -> None:
    labels = step(run, "labels")
    assert all("Axis" in label for label in labels), labels


def test_every_control_is_inside_the_pane(run: dict) -> None:
    assert step(run, "pane-units") in (560, 900)  # the default width, widened
    assert step(run, "past-edge") == [], run.get("editor")


def test_a_wide_pane_keeps_the_lists_beside_their_labels(run: dict) -> None:
    if step(run, "pane-units") == 900:
        assert step(run, "wide") is True


if __name__ == "__main__":
    main()
