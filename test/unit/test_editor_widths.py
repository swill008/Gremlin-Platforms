# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action editors fit the Configuration pane (no behaviour change).

The Dual Axis Deadzone, Send OSC and Split Axis editors are shown in the off-screen
program's Configuration pane at the default window size and at a narrower
one. Every visible control stays inside the editor's width (the pane's
content width less the standard right margin the binding gives every
editor), and every button is at least as wide as its text.

Run as a script, this file is the child process: it opens the program
(journey harness: temporary home, fakes, off-screen) and prints RESULT.

    python test/unit/test_editor_widths.py <requests.json>
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]

EDITORS = [
    ("dual-axis-deadzone", "Dual Axis Deadzone", "DualAxisDeadzoneAction"),
    ("send-osc", "Send OSC", "SendOscAction"),
    ("split-axis", "Split Axis", "SplitAxisAction"),
]
# Default window size, and a narrower one (a narrower pane).
WIDTHS = [1600, 1280]
CONTROLS = (
    "Button",
    "ComboBox",
    "JGTextField",
    "FloatSpinBox",
    "IconButton",
    "Label",
    "ActionSelector",
    "LabelValueComboBox",
)
# Off-screen screenshots go here when set (else the test's tmp folder).
SHOTS_ENV = "EDITOR_WIDTH_SHOTS"


# +-------------------------------------------------------------------------
# | Child process


def _story(j) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    jobs = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    results: list[dict] = []
    j.out["results"] = results
    for job in jobs:
        j.win.setWidth(job["width"])
        j.win.setHeight(950)
        j.settle()
        catalog = j.open_configuration("pjoy_pro")
        page = j.ev("catalogPane()")
        hid = j.device_index(catalog, "axis", 1)
        j.ev(f"openAdvancedPane({hid}); true", page)
        j.wait_until(lambda: catalog.paneModel is not None, "the pane")
        root = j.wait_until(lambda: j.pane_actions(catalog)[0], "the root action")
        root.appendAction(job["name"], "children")
        stem = job["stem"]

        def editor(stem: str = stem) -> object:
            for item in j.walk(j.win.contentItem()):
                if item.metaObject().className().startswith(stem + "_QML"):
                    return item
            return None

        item = j.wait_until(editor, f"the {stem} editor", timeout=10)
        j.QTest.qWait(400)

        def left(it) -> float:  # noqa: ANN001
            return it.mapToScene(QtCore.QPointF(0, 0)).x()

        def visible(it) -> bool:  # noqa: ANN001
            while it is not None and it is not item:
                if not it.isVisible():
                    return False
                it = it.parentItem()
            return True

        controls = []
        for it in j.walk(item):
            kind = it.metaObject().className().split("_")[0]
            if kind not in CONTROLS or it.width() <= 0 or not visible(it):
                continue
            has_text = it.metaObject().indexOfProperty("text") >= 0
            text = it.property("text") if has_text else ""
            controls.append(
                {
                    "kind": kind,
                    "text": str(text or ""),
                    "left": left(it),
                    "right": left(it) + it.width(),
                    "width": it.width(),
                    "implicit": it.implicitWidth(),
                }
            )
        clip = item.parentItem()
        while clip is not None and not clip.clip():
            clip = clip.parentItem()
        results.append(
            {
                "tag": job["tag"],
                "width": job["width"],
                "editor_right": left(item) + item.width(),
                "clip_right": left(clip) + clip.width() if clip is not None else None,
                "controls": controls,
            }
        )
        if job.get("shot"):
            pathlib.Path(job["shot"]).parent.mkdir(parents=True, exist_ok=True)
            j.win.grabWindow().save(job["shot"])
        catalog.discardPane()
        catalog.endPane()
        j.settle()


def _main() -> None:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import Journey  # pyright: ignore[reportMissingImports]

    def before(j) -> None:  # noqa: ANN001
        j.input_module()
        j.vjoy_module()

    Journey(before).run(_story)


# +-------------------------------------------------------------------------
# | The test


@pytest.fixture(scope="module")
def measured(tmp_path_factory: pytest.TempPathFactory) -> dict:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import run_journey  # pyright: ignore[reportMissingImports]

    tmp = tmp_path_factory.mktemp("editor-widths")
    shots = pathlib.Path(os.environ.get(SHOTS_ENV) or tmp)
    jobs = [
        {
            "tag": tag,
            "name": name,
            "stem": stem,
            "width": width,
            "shot": str(shots / f"{tag}_{width}.png"),
        }
        for tag, name, stem in EDITORS
        for width in WIDTHS
    ]
    spec = tmp / "jobs.json"
    spec.write_text(json.dumps(jobs), encoding="utf-8")
    out = run_journey(
        pathlib.Path(__file__), pathlib.Path(tempfile.mkdtemp(dir=tmp)), str(spec)
    )
    assert not out.get("error"), out.get("traceback")
    return {(r["tag"], r["width"]): r for r in out["results"]}


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("tag", [e[0] for e in EDITORS])
def test_editor_fits_the_pane(measured: dict, tag: str, width: int) -> None:
    """Spec: none (no behaviour change). AX2: Dual Axis Deadzone's Add Action
    buttons were cut off ("Add A"); O2: Send OSC ran under the pane's
    scrollbar; SA1: Split Axis's "Actions for the lower / left part" label
    pushed its Add Action selector out of the pane. Each editor lays out
    inside its own width."""
    got = measured[(tag, width)]
    edge = got["editor_right"]
    assert got["clip_right"] is None or edge <= got["clip_right"] + 0.5
    assert got["controls"], "no controls measured"
    over = [
        f"{c['kind']} {c['text']!r} right {c['right']:.0f} > {edge:.0f}"
        for c in got["controls"]
        if c["right"] > edge + 0.5
    ]
    assert not over, f"{tag} at {width}: past the pane's content width: {over}"
    squeezed = [
        f"{c['kind']} {c['text']!r} {c['width']:.0f} < {c['implicit']:.0f}"
        for c in got["controls"]
        if c["kind"] == "Button" and c["width"] + 0.5 < c["implicit"]
    ]
    assert not squeezed, f"{tag} at {width}: narrower than their text: {squeezed}"


if __name__ == "__main__":
    _main()
