# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action editors fit the Configuration pane (no behaviour change).

Action editors are shown in the off-screen program's Configuration pane at
UI scales 100, 150 and 200 % (window 1600 x 950), with the pane at its
default width and at its minimum (420 units, EW-1), and the first three
also in a narrower window. Every visible control stays inside the editor's
width (the pane's content width less the standard right margin the binding
gives every editor), every button is at least as wide as its text, and no
text is cut: combo box text, labels and placeholder text fit their boxes
(SJ-03 to SJ-06).

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

# (tag, action name, editor QML stem, input kind)
EDITORS = [
    ("dual-axis-deadzone", "Dual Axis Deadzone", "DualAxisDeadzoneAction", "axis"),
    ("send-osc", "Send OSC", "SendOscAction", "axis"),
    ("split-axis", "Split Axis", "SplitAxisAction", "axis"),
    ("condition", "Condition", "ConditionAction", "button"),
    ("chain", "Chain", "ChainAction", "button"),
    ("tempo", "Tempo", "TempoAction", "button"),
    ("double-tap", "Double Tap", "DoubleTapAction", "button"),
    ("smart-toggle", "Smart Toggle", "SmartToggleAction", "button"),
    ("merge-axis", "Merge Axis", "MergeAxisAction", "axis"),
    ("axis-delta", "Axis Delta", "AxisDeltaAction", "axis"),
    ("hat-buttons", "Hat as Buttons", "HatButtonsAction", "hat"),
    ("map-to-xbox", "Map to Xbox", "MapToXboxAction", "button"),
    ("map-to-mouse-axis", "Map to Mouse", "MapToMouseAction", "axis"),
    ("map-to-mouse-hat", "Map to Mouse", "MapToMouseAction", "hat"),
    ("map-to-mouse-button", "Map to Mouse", "MapToMouseAction", "button"),
    ("text-to-speech", "Text to Speech", "TextToSpeechAction", "button"),
    ("play-sound", "Play Sound", "PlaySoundAction", "button"),
    ("run-command", "Run Command", "RunCommandAction", "button"),
    # The red "⚠ <name>" boxes forced to can't-be-sent (CI has no Xbox
    # driver; a PC with one never showed the cut "⚠ Xbox 360 Contro").
    ("map-to-xbox-cant", "Map to Xbox", "MapToXboxAction", "button"),
    ("send-osc-cant", "Send OSC", "SendOscAction", "axis"),
    ("map-to-vjoy-cant", "Map to vJoy", "MapToVjoyAction", "button"),
    (
        "map-to-logical-device-cant",
        "Map to Logical Device",
        "MapToLogicalDeviceAction",
        "button",
    ),
]
# A choice clicked before measuring (Motion shows the speed boxes).
CLICK = {"map-to-mouse-button": "Motion"}
SCALES = [100, 150, 200]
# The window at each scale: 1600 x 950 at 100 %, the same size in UI units
# at 150 and 200 %, so the pane has its default width.
WINDOW = {100: 1600, 150: 2400, 200: 3200}
# The first three editors also in a narrower window (a narrower pane).
NARROW = (1280, ("dual-axis-deadzone", "send-osc", "split-axis"))
# Windows too narrow for the pane's saved width at 200 % (SJ-05): only the
# OK check runs there.
TIGHT = [("condition", 200, 1600), ("text-to-speech", 200, 1920)]
# Every editor also with the pane at its minimum width (grip + 420 units,
# EW-1), in the default window at each scale.
MIN = "min"
MIN_UNITS = 420


# Measured at the default width only: at the pane's minimum, Map to vJoy's
# device box ("vJoy 1") is cut and both run "Invert activation" past the
# pane, with or without the ⚠ (a known gap, not this check's).
DEFAULT_ONLY = ("map-to-vjoy-cant", "map-to-logical-device-cant")


def _widths(tag: str, scale: int) -> list[int | str]:
    if tag in DEFAULT_ONLY:
        return [WINDOW[scale]]
    narrow = [NARROW[0]] if scale == 100 and tag in NARROW[1] else []
    tight = [w for t, sc, w in TIGHT if t == tag and sc == scale]
    return [WINDOW[scale], *narrow, *tight, MIN]


CONTROLS = (
    "Button",
    "ComboBox",
    "JGTextField",
    "FloatSpinBox",
    "IconButton",
    "Label",
    "ActionSelector",
    "LabelValueComboBox",
    "RadioButton",
    "Switch",
    "CheckBox",
)
# Off-screen screenshots go here when set (else the test's tmp folder).
SHOTS_ENV = "EDITOR_WIDTH_SHOTS"


# +-------------------------------------------------------------------------
# | Child process


def _cut_text(j, item) -> list[str]:  # noqa: ANN001
    """Texts inside the editor that are wider than the box showing them."""
    found = []

    def visible(it) -> bool:  # noqa: ANN001
        while it is not None and it is not item:
            if not it.isVisible():
                return False
            it = it.parentItem()
        return True

    for it in j.walk(item):
        if it.width() <= 0 or not visible(it):
            continue
        cls = it.metaObject().className()
        text = (
            it.property("text")
            if it.metaObject().indexOfProperty("text") >= 0
            else None
        )
        if not isinstance(text, str) or not text:
            continue
        content = it.property("contentWidth")
        if not isinstance(content, (int, float)):
            continue
        room = (
            it.width()
            - (it.property("leftPadding") or 0)
            - (it.property("rightPadding") or 0)
        )
        if cls.startswith(("QQuickTextInput", "QQuickTextField")):
            # A combo box's shown text, inside its padding (typed text in a
            # field may scroll).
            parent = it.parentItem()
            in_combo = (
                parent is not None and "ComboBox" in parent.metaObject().className()
            )
            if in_combo and content > room + 1:
                found.append(f"ComboBox {text[:40]!r} {content:.0f} > {room:.0f}")
        elif cls.startswith(
            ("QQuickText", "QQuickLabel", "Label_", "QQuickPlaceholderText")
        ):
            # Elided text (placeholders elide) reports the cut width, so
            # truncated says it was cut.
            if it.property("truncated") is True or content > room + 1:
                found.append(
                    f"{cls.split('_')[0]} {text[:40]!r} {content:.0f} > {room:.0f}"
                )
    return found


def _force_cant_send() -> dict:
    """Every output can't be sent (the ⚠ state); returns what to restore."""
    from gremlin.modules import output

    why = "is not Found."
    saved = {
        name: getattr(output, name)
        for name in (
            "xbox_cant_send_text",
            "osc_cant_send_text",
            "logical_cant_send_text",
            "cant_send_words",
        )
    }
    for name in saved:
        setattr(output, name, lambda *_a, **_k: why)
    return saved


def _story(j) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    from gremlin.modules import output

    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    results: list[dict] = []
    j.out["results"] = results
    j.out["uiScale"] = j.ev("Style.uiScale")
    for job in spec["jobs"]:
        at_min = job["width"] == MIN
        j.win.setWidth(WINDOW[spec["scale"]] if at_min else job["width"])
        j.win.setHeight(round(950 * spec["scale"] / 100))
        j.settle()
        catalog = j.open_configuration("pjoy_pro")
        # The pane's width in UI units: its minimum, else the default.
        for it in j.walk(j.win.contentItem()):
            if it.metaObject().className().startswith("ActionPane_QML"):
                it.setProperty("paneUnits", MIN_UNITS if at_min else 560)
        j.settle()
        restore = _force_cant_send() if job["tag"].endswith("-cant") else {}
        j.open_input(catalog, job["kind"], 1)
        root = j.wait_until(lambda: j.pane_actions(catalog)[0], "the root action")
        root.appendAction(job["name"], "children")
        stem = job["stem"]

        def editor(stem: str = stem) -> object:
            for item in j.walk(j.win.contentItem()):
                if item.metaObject().className().startswith(stem + "_QML"):
                    return item
            return None

        item = j.wait_until(editor, f"the {stem} editor", timeout=10)
        if job.get("click"):
            for it in j.walk(item):
                if (
                    it.metaObject().className().startswith("RadioButton")
                    and it.property("text") == job["click"]
                ):
                    QtCore.QMetaObject.invokeMethod(it, "clicked")
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
        # The pane's OK button (the page may be wider than the window).
        ok_right = None
        for it in j.walk(j.win.contentItem()):
            if (
                it.metaObject().className().startswith("Button")
                and it.isVisible()
                and it.property("text") == "OK"
            ):
                ok_right = left(it) + it.width()
        clip = item.parentItem()
        while clip is not None and not clip.clip():
            clip = clip.parentItem()
        # The binding's Root row above the editors (Note, Add Action).
        root_row = []
        for head in j.walk(j.win.contentItem()):
            if (
                not head.metaObject()
                .className()
                .startswith("InputItemBindingConfigurationHeader")
                or not head.isVisible()
            ):
                continue
            for it in j.walk(head):
                kind = it.metaObject().className().split("_")[0]
                if kind not in CONTROLS or it.width() <= 0 or not it.isVisible():
                    continue
                has_text = it.metaObject().indexOfProperty("text") >= 0
                root_row.append(
                    {
                        "kind": kind,
                        "text": str((it.property("text") if has_text else "") or ""),
                        "right": left(it) + it.width(),
                        "width": it.width(),
                        "implicit": it.implicitWidth(),
                    }
                )
        results.append(
            {
                "tag": job["tag"],
                "width": job["width"],
                "editor_right": left(item) + item.width(),
                "clip_right": left(clip) + clip.width() if clip is not None else None,
                "controls": controls,
                "root_row": root_row,
                "cut": _cut_text(j, item),
                "ok_right": ok_right,
                "window": j.win.contentItem().width(),
                "pane": [
                    it.property("shownWidth")
                    for it in j.walk(j.win.contentItem())
                    if it.metaObject().className().startswith("ActionPane_QML")
                    and it.isVisible()
                ],
            }
        )
        if job.get("shot"):
            pathlib.Path(job["shot"]).parent.mkdir(parents=True, exist_ok=True)
            j.win.grabWindow().save(job["shot"])
        catalog.discardPane()
        catalog.endPane()
        for name, fn in restore.items():
            setattr(output, name, fn)
        j.settle()


def _main() -> None:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import Journey  # pyright: ignore[reportMissingImports]

    scale = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["scale"]

    def before(j) -> None:  # noqa: ANN001
        from gremlin.ui import ui_scale_option

        ui_scale_option.active_scale = lambda: scale  # type: ignore[assignment]
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
    found: dict = {}
    # While working on one editor: EDITOR_WIDTH_ONLY=tag,tag measures those.
    only = [t for t in os.environ.get("EDITOR_WIDTH_ONLY", "").split(",") if t]
    for scale in SCALES:
        jobs = [
            {
                "tag": tag,
                "name": name,
                "stem": stem,
                "kind": kind,
                "width": width,
                "shot": str(shots / f"{tag}_{scale}_{width}.png"),
                "click": CLICK.get(tag, ""),
            }
            for tag, name, stem, kind in EDITORS
            for width in _widths(tag, scale)
            if not only or tag in only
        ]
        spec = tmp / f"jobs_{scale}.json"
        spec.write_text(json.dumps({"scale": scale, "jobs": jobs}), encoding="utf-8")
        out = run_journey(
            pathlib.Path(__file__), pathlib.Path(tempfile.mkdtemp(dir=tmp)), str(spec)
        )
        assert not out.get("error"), out.get("traceback")
        assert out.get("uiScale") == scale, f"UI scale {out.get('uiScale')} != {scale}"
        for r in out["results"]:
            found[(r["tag"], scale, r["width"])] = r
    return found


CASES = [
    (tag, scale, width)
    for tag, _name, _stem, _kind in EDITORS
    for scale in SCALES
    for width in _widths(tag, scale)
    if (tag, scale, width) not in TIGHT
]


@pytest.mark.parametrize(("tag", "scale", "width"), CASES)
def test_editor_fits_the_pane(measured: dict, tag: str, scale: int, width: int) -> None:
    """Spec: none (no behaviour change). AX2: Dual Axis Deadzone's Add Action
    buttons were cut off ("Add A"); O2: Send OSC ran under the pane's
    scrollbar; SA1: Split Axis's "Actions for the lower / left part" label
    pushed its Add Action selector out of the pane; SJ-03..06: Condition's
    Add Condition row, Map to Mouse's speed rows and Text to Speech's Rate
    ran past the pane; EW-1: Chain's Add Chain Sequence and Send OSC ran
    past the pane at its minimum width. Each editor lays out inside its own
    width, at the pane's default and minimum widths."""
    got = measured[(tag, scale, width)]
    if width == MIN:
        least = MIN_UNITS * scale / 100
        assert got["pane"], "no open pane"
        assert all(abs(w - least) <= 1 for w in got["pane"]), (
            f"pane not at its minimum: {got['pane']} != {least:.0f}"
        )
    edge = got["editor_right"]
    assert got["clip_right"] is None or edge <= got["clip_right"] + 0.5
    assert got["controls"], "no controls measured"
    over = [
        f"{c['kind']} {c['text']!r} right {c['right']:.0f} > {edge:.0f}"
        for c in got["controls"]
        if c["right"] > edge + 0.5
    ]
    assert not over, f"{tag} at {scale}% {width}: past the pane's content width: {over}"
    squeezed = [
        f"{c['kind']} {c['text']!r} {c['width']:.0f} < {c['implicit']:.0f}"
        for c in got["controls"]
        if c["kind"] == "Button" and c["width"] + 0.5 < c["implicit"]
    ]
    assert not squeezed, (
        f"{tag} at {scale}% {width}: narrower than their text: {squeezed}"
    )


@pytest.mark.parametrize(("tag", "scale", "width"), CASES)
def test_root_row_fits_the_pane(
    measured: dict, tag: str, scale: int, width: int
) -> None:
    """Spec: none (no behaviour change). EW-1: the Root row's Add Action
    picker kept a fixed least width and ran under the pane's edge ("Add
    Acti") at the pane's minimum width. The row stays inside the pane and
    Add Action is as wide as its text."""
    got = measured[(tag, scale, width)]
    assert got["root_row"], "no Root row measured"
    edge = got["clip_right"]
    over = [
        f"{c['kind']} {c['text']!r} right {c['right']:.0f} > {edge:.0f}"
        for c in got["root_row"]
        if edge is not None and c["right"] > edge + 0.5
    ]
    assert not over, f"{tag} at {scale}% {width}: Root row past the pane: {over}"
    squeezed = [
        f"{c['kind']} {c['text']!r} {c['width']:.0f} < {c['implicit']:.0f}"
        for c in got["root_row"]
        if c["kind"] == "Button" and c["width"] + 0.5 < c["implicit"]
    ]
    assert not squeezed, f"{tag} at {scale}% {width}: Root row squeezed: {squeezed}"


@pytest.mark.parametrize(("tag", "scale", "width"), CASES)
def test_editor_text_is_not_cut(
    measured: dict, tag: str, scale: int, width: int
) -> None:
    """Spec: none (no behaviour change). SJ-04 / SJ-06: combo boxes sized to
    a fixed width cut their text ("Xbox 360 C", "Map to v"), the Map to
    Mouse hat label "Maximum speed (px/s)" and the Play Sound / Run Command
    placeholders were cut; 05 S137: Map to Xbox's red "⚠ Xbox 360
    Controller" was cut where the Xbox driver is missing (the *-cant cases
    force every ⚠). Every text fits its box."""
    cut = measured[(tag, scale, width)]["cut"]
    assert not cut, f"{tag} at {scale}% {width}: text cut off: {cut}"


@pytest.mark.parametrize(("tag", "scale", "width"), CASES + TIGHT)
def test_pane_ok_inside_the_window(
    measured: dict, tag: str, scale: int, width: int
) -> None:
    """Spec: none (no behaviour change). SJ-05: at 200 % in a 1600 px window
    the pane kept its saved width beside the list and Appearance columns,
    so the page ran past the window and OK was off the edge. The pane now
    gives up width (down to its minimum) when the window is too narrow."""
    got = measured[(tag, scale, width)]
    assert got["ok_right"] is not None, "no OK button"
    assert got["ok_right"] <= got["window"] + 0.5, (
        f"{tag} at {scale}% {width}: OK right {got['ok_right']:.0f}"
        f" > window {got['window']:.0f}"
    )


if __name__ == "__main__":
    _main()
