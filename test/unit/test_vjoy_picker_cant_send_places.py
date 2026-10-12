# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The vJoy picker's red ⚠ in every place that uses it (05 S137, to-do 95).

The vJoy picker (qml/VJoySelector.qml) is the same in the Condition
editor's vJoy condition, the macro editor's vJoy steps and the Script
settings page as in Map to vJoy (user, 2026-10-11, option 3a). Each points
at a vJoy control the output module doesn't claim (vJoy 1's Button 57; the
module claims Buttons 1-56): the picker shows "⚠ Button 57" in red
(Style.danger), its tooltip is ``output.cant_send_text`` for that control
and the box is wide enough for the text.

Run as a script, this file is the child process: the real program
off-screen (journey harness: temporary home, fake hardware), printing
RESULT. ``argv[1]`` is the folder for the screenshots, ``argv[2]`` the
UI scale (default 100); at 150 and 200 % only the Script settings page is
checked, in a window of the same size in UI units (to-do 98).
"""

from __future__ import annotations

import os
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
# Off-screen screenshots go here when set (else the test's tmp folder).
SHOTS_ENV = "COND95_SHOTS"
PLACES = ("condition", "macro", "script")
# Script settings at larger UI scales (to-do 98), window 1600 x 950 in UI units.
SCALES = (150, 200)
VJOY, BUTTON = 1, 57
SCRIPT = (
    "import gremlin.user_script as us\n"
    "from gremlin.types import InputType\n"
    "out = us.VirtualInputVariable(\n"
    "    'Output', 'The vJoy button to press', True, [InputType.JoystickButton]\n"
    ")\n"
)


# +-------------------------------------------------------------------------
# | Child process


def _measure(j, selector, shot: pathlib.Path, frame) -> dict:  # noqa: ANN001
    """What the picker shows; saves a screenshot with the tooltip shown."""
    from PySide6 import QtCore

    combos = [
        it
        for it in j.walk(selector)
        if "ComboBox" in it.metaObject().className() and it.isVisible()
    ]
    box = next(
        (c for c in combos if str(c.property("currentText")).startswith("⚠")), None
    )
    found: dict = {
        "cantSend": selector.property("cantSend"),
        "cantSendText": selector.property("cantSendText"),
        "texts": [str(c.property("currentText")) for c in combos],
    }
    if box is None:
        return found
    content = box.property("contentItem")
    found["color"] = content.property("color").name()
    found["contentWidth"] = content.property("contentWidth")
    found["truncated"] = content.property("truncated")
    found["needed"] = (
        content.property("contentWidth")
        + (content.property("leftPadding") or 0)
        + (content.property("rightPadding") or 0)
        + box.property("leftPadding")
        + box.property("rightPadding")
    )
    found["boxWidth"] = box.width()
    # The box's right edge, the editor's (or page's) and the window's.
    found["boxRight"] = box.mapToScene(QtCore.QPointF(box.width(), 0)).x()
    found["frameRight"] = frame.mapToScene(QtCore.QPointF(frame.width(), 0)).x()
    found["window"] = j.win.contentItem().width()
    found["tooltipsOn"] = box.property("enableTooltips")
    # The Script settings row: the name gives way so the picker fits.
    row = selector.parentItem()
    name = next(
        (it for it in j.walk(row) if it.metaObject().className().startswith("JGText")),
        None,
    )
    if row is not None and name is not None:
        found["row"] = {
            "rowRight": row.mapToScene(QtCore.QPointF(row.width(), 0)).x(),
            "nameWidth": name.width(),
            "nameImplicit": name.property("implicitWidth"),
            "nameLines": name.property("lineCount"),
            "pickerX": selector.mapToScene(QtCore.QPointF(0, 0)).x(),
            "pickerWidth": selector.width(),
            "pickerImplicit": selector.property("implicitWidth"),
        }
    # Hover the box (a Qt event to the off-screen window): the ⚠ tooltip.
    centre = box.mapToScene(QtCore.QPointF(box.width() / 2, box.height() / 2))
    j.QTest.mouseMove(j.win, QtCore.QPoint(int(centre.x()), int(centre.y())))

    def tooltips() -> list[QtCore.QObject]:
        return [
            t
            for t in selector.findChildren(QtCore.QObject)
            if t.metaObject().className().startswith("WrappingTooltip")
        ]

    try:
        j.wait_until(
            lambda: any(t.property("visible") for t in tooltips()),
            "the hover tooltip", timeout=10,
        )
    except TimeoutError:
        pass
    tips = tooltips()
    found["tooltip"] = [
        {"text": t.property("text"), "visible": t.property("visible")} for t in tips
    ]
    img = j.win.grabWindow()
    r = frame.mapRectToScene(QtCore.QRectF(0, 0, frame.width(), frame.height()))
    s = selector.mapRectToScene(
        QtCore.QRectF(0, 0, selector.width(), selector.height())
    )
    # The editor (or page) around the picker, with room for the tooltip.
    left = max(0, int(min(r.x() - 10, s.x() - 200)))
    right = min(img.width(), int(max(r.x() + r.width() + 10, s.x() + s.width() + 40)))
    top = max(0, int(min(r.y(), s.y() - 60)))
    bottom = min(
        img.height(),
        int(max(s.y() + s.height() + 120, min(r.y() + r.height(), s.y() + 300))),
    )
    img.copy(QtCore.QRect(left, top, right - left, bottom - top)).save(str(shot))
    found["shot"] = str(shot)
    j.QTest.mouseMove(j.win, QtCore.QPoint(2, 2))
    j.QTest.qWait(100)
    return found


def _selector_in(j, item):  # noqa: ANN001, ANN202
    for it in j.walk(item):
        if it.metaObject().className().startswith("VJoySelector"):
            return it
    return None


def _editor(j, catalog, name: str, stem: str):  # noqa: ANN001, ANN202
    j.open_input(catalog, "button", 1)
    root = j.wait_until(lambda: j.pane_actions(catalog)[0], "the root action")
    n = len(j.pane_actions(catalog))
    root.appendAction(name, "children")
    j.wait_until(lambda: len(j.pane_actions(catalog)) > n, f"the {name} action")
    model = j.pane_actions(catalog)[-1]

    def find():  # noqa: ANN202
        for item in j.walk(j.win.contentItem()):
            if item.metaObject().className().startswith(stem + "_QML"):
                return item
        return None

    return model, j.wait_until(find, f"the {stem} editor", timeout=10)


def _story(j) -> None:  # noqa: ANN001
    from gremlin.modules import output

    shots = pathlib.Path(sys.argv[1])
    shots.mkdir(parents=True, exist_ok=True)
    scale = _scale()
    out = j.out
    out["danger"] = j.ev("Style.danger").name()
    out["expected"] = output.cant_send_text(VJOY, "button", BUTTON)
    out["scale"] = scale
    j.win.setWidth(1600 * scale // 100)
    j.win.setHeight(950 * scale // 100)
    j.settle()
    if scale == 100:
        _editors(j, shots)
    _script_page(j, shots, scale)


def _editors(j, shots: pathlib.Path) -> None:  # noqa: ANN001
    from action_plugins.condition import condition as ca
    from gremlin import macro
    from gremlin.types import InputType

    out = j.out

    # The Condition editor's vJoy condition.
    catalog = j.open_device_bindings("pjoy_pro")
    model, editor = _editor(j, catalog, "Condition", "ConditionAction")
    cond = ca.VJoyCondition(model)
    cond.start_on(VJOY, InputType.JoystickButton, BUTTON)
    model._data.conditions.append(cond)
    model.conditionsChanged.emit()
    selector = j.wait_until(lambda: _selector_in(j, editor), "the vJoy condition")
    j.QTest.qWait(400)
    out["condition"] = _measure(j, selector, shots / "cond95_condition.png", editor)
    out["condition"]["saved"] = [cond.vjoyDeviceId, cond.vjoyInputId]
    catalog.discardPane()
    catalog.endPane()
    j.settle()

    # A macro's vJoy step.
    model, editor = _editor(j, catalog, "Macro", "MacroAction")
    step = macro.VJoyAction(VJOY, InputType.JoystickButton, BUTTON, True)
    model._action_list_model.append(step)
    model.changed.emit()
    selector = j.wait_until(lambda: _selector_in(j, editor), "the macro vJoy step")
    j.QTest.qWait(400)
    out["macro"] = _measure(j, selector, shots / "cond95_macro.png", editor)
    out["macro"]["saved"] = [step.vjoy_id, step.input_id]
    catalog.discardPane()
    catalog.endPane()
    j.settle()


def _script_page(j, shots: pathlib.Path, scale: int) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    from gremlin import util

    out = j.out
    # The Script settings page: a script's vJoy setting.
    folder = pathlib.Path(util.scripts_dir())
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "press.py").write_text(SCRIPT, encoding="utf-8")
    j.backend.ui_state.setCurrentRoom("scripts")
    j.backend.ui_state.setCurrentTab("scripts")
    j.settle()
    scripts = j.ev("_scriptLoader.item.scriptListModel")
    scripts.addScript(QtCore.QUrl.fromLocalFile(str(folder / "press.py")).toString())
    script = j.wait_until(
        lambda: next(
            (
                s
                for s in j.profile.scripts.scripts
                if s.path.name == "press.py" and not s.starting
            ),
            None,
        ),
        "the script started",
    )
    variable = script.shown_variables["Output"]
    variable._vjoy_id, variable._input_id = VJOY, BUTTON
    configure = j.ev("bsi.icons.configure")

    def button():  # noqa: ANN202
        for row in j.walk(j.win.contentItem()):
            if row.property("loadError") is None or row.property("path") is None:
                continue
            for it in j.walk(row):
                if (
                    it.metaObject().className().startswith("IconButton")
                    and it.property("text") == configure
                    and it.property("enabled")
                ):
                    return it
        return None

    QtCore.QMetaObject.invokeMethod(j.wait_until(button, "its settings"), "clicked")
    page = j.wait_until(
        lambda: next(
            (
                it
                for it in j.walk(j.win.contentItem())
                if it.metaObject().className().startswith("ScriptConfiguration")
            ),
            None,
        ),
        "the Script settings page",
    )
    selector = j.wait_until(lambda: _selector_in(j, page), "the vJoy setting")
    j.QTest.qWait(400)
    suffix = "" if scale == 100 else f"_{scale}"
    out["script"] = _measure(j, selector, shots / f"cond95_script{suffix}.png", page)
    out["script"]["saved"] = [variable.vjoy_id, variable.input_id]


def _scale() -> int:
    return int(sys.argv[2]) if len(sys.argv) > 2 else 100


def _main() -> None:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import Journey, claim_everything  # pyright: ignore

    scale = _scale()

    def before(j) -> None:  # noqa: ANN001
        from gremlin.ui import ui_scale_option

        ui_scale_option.active_scale = lambda: scale  # type: ignore[assignment]
        j.input_module()
        claim = claim_everything()
        claim["buttons"] = list(range(1, 57))
        j.write_module(
            "vjoy_1", {"device": "vJoy 1", "direction": "dest", "claim": claim}
        )

    Journey(before).run(_story)


# +-------------------------------------------------------------------------
# | The test


@pytest.fixture(scope="module")
def shown(tmp_path_factory: pytest.TempPathFactory) -> dict:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import run_journey  # pyright: ignore[reportMissingImports]

    tmp = tmp_path_factory.mktemp("cond95")
    shots = pathlib.Path(os.environ.get(SHOTS_ENV) or tmp)
    out = run_journey(pathlib.Path(__file__), tmp / "home", str(shots))
    assert not out.get("error"), out.get("traceback")
    return out


@pytest.fixture(scope="module")
def scaled(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The Script settings page at 150 and 200 %, one process per scale."""
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import run_journey  # pyright: ignore[reportMissingImports]

    tmp = tmp_path_factory.mktemp("script98")
    shots = pathlib.Path(os.environ.get(SHOTS_ENV) or tmp)
    found = {}
    for scale in SCALES:
        out = run_journey(
            pathlib.Path(__file__), tmp / f"home{scale}", str(shots), str(scale)
        )
        assert not out.get("error"), out.get("traceback")
        assert out.get("scale") == scale, out.get("scale")
        found[scale] = out
    return found


def test_the_expected_wording(shown: dict) -> None:
    assert shown["expected"] == (
        "vJoy 1's Button 57 is not Found (vJoy 1 has Buttons 1–56)."
    )


@pytest.mark.parametrize("place", PLACES)
def test_red_warning_sign_and_its_tooltip(shown: dict, place: str) -> None:
    got = shown[place]
    assert got["cantSend"] is True, got
    assert f"⚠ Button {BUTTON}" in got["texts"], got
    assert got["color"] == shown["danger"], got
    assert got["cantSendText"] == shown["expected"], got
    # Its own tooltip in place of the box's, and shown on hover.
    assert got["tooltipsOn"] is False, got
    # On hover only the ⚠ tooltip shows (the boxes' own stay hidden).
    shown_tips = [t["text"] for t in got["tooltip"] if t["visible"]]
    assert shown_tips == [shown["expected"]], got
    # The saved control is kept, not re-pointed.
    assert got["saved"] == [VJOY, BUTTON], got


def _assert_not_cut(got: dict) -> None:
    assert got["truncated"] is not True, got
    assert got["needed"] <= got["boxWidth"] + 1, got
    # The box stays inside its editor (or page) and the window.
    edges = {k: got[k] for k in ("boxRight", "frameRight", "window")}
    assert got["boxRight"] <= got["frameRight"] + 1, edges
    assert got["boxRight"] <= got["window"] + 1, edges


@pytest.mark.parametrize("place", PLACES)
def test_the_box_is_not_cut(shown: dict, place: str) -> None:
    _assert_not_cut(shown[place])


@pytest.mark.parametrize("scale", SCALES)
def test_the_script_setting_fits_at_scale(scaled: dict, scale: int) -> None:
    got = scaled[scale]["script"]
    assert got["cantSend"] is True, got
    assert f"⚠ Button {BUTTON}" in got["texts"], got
    _assert_not_cut(got)


@pytest.mark.parametrize("scale", [100, *SCALES])
def test_the_script_setting_name_gives_way(
    shown: dict, scaled: dict, scale: int
) -> None:
    # Option a (to-do 98): the name, not the picker, gives up width.
    row = (shown if scale == 100 else scaled[scale])["script"]["row"]
    assert row["pickerX"] + row["pickerWidth"] <= row["rowRight"] + 1, row
    assert row["pickerWidth"] >= row["pickerImplicit"] - 1, row
    assert row["nameWidth"] < scale * 250 / 100, row


if __name__ == "__main__":
    _main()
