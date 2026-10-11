# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Clear on the Find bar resets every Find filter (05 S124, decision
D-05-FIND-CLEAR): on the Device Bindings page that includes the action Type
and Output boxes, as Clear Filters does.

A journey (test/journeys/_harness.py) on the real program, off-screen, with a
temporary USERPROFILE and the fake joystick driver. The page is hosted the
way test_device_bindings_page_qml hosts it; the user picks a Type and an
Output, then presses the bar's Clear button.

Spec: 05 S124 (FC1).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, JourneyIncomplete, run_journey  # noqa: E402

STICK = "pJoy Pro"


def _before(j: Journey) -> None:
    j.input_module(STICK)
    j.vjoy_module()


def _find_page(j: Journey) -> Any:  # noqa: ANN401
    from PySide6 import QtQuick

    for w in j.app.topLevelWindows():
        if not isinstance(w, QtQuick.QQuickWindow) or not w.isVisible():
            continue
        for item in j.walk(w.contentItem()):
            if item.metaObject().className().startswith(
                "DeviceBindingsPage"
            ) and item.isVisible():
                return item
    return None


def _by_name(j: Journey, root: Any, name: str) -> Any:  # noqa: ANN401
    for item in j.walk(root):
        if item.objectName() == name and item.isVisible():
            return item
    return None


def story(j: Journey) -> None:
    uid = j.stick(STICK).device_guid.uuid
    mode = j.profile.modes.first_mode
    j.map_button(uid, 1, mode, 1)
    j.map_button(uid, 2, mode, 2)
    j.settle()
    ui = j.backend.uiState
    ui.setCurrentDevice(str(uid))
    ui.setCurrentTab("physical")
    ui.setCurrentRoom("settings")
    j.settle()
    made = j.ev(
        "(function() {"
        " var win = Qt.createQmlObject('import QtQuick; import QtQuick.Window;"
        " Window { width: 1600; height: 900; visible: true }', _root, 'host');"
        " var c = Qt.createComponent('DeviceBindingsPage.qml');"
        " if (c.status !== Component.Ready) return 'error: ' + c.errorString();"
        f" var page = c.createObject(win.contentItem, {{ guid: {str(uid)!r},"
        f" deviceName: {STICK!r} }});"
        " if (!page) return 'error: not made';"
        " page.anchors.fill = win.contentItem;"
        " return 'ok' })()"
    )
    assert made == "ok", made
    page = j.wait_until(lambda: _find_page(j), "the hosted DeviceBindingsPage")
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    layout = j.wait_until(lambda: page.findChild(HardwareLayoutModel), "the model")
    j.wait_until(lambda: layout.property("parentCount") > 0, "the claimed inputs")
    j.QTest.qWait(300)
    j.out["rowsBefore"] = layout.rowCount()

    kind = _by_name(j, page, "deviceBindingsActionType")
    output = _by_name(j, page, "deviceBindingsOutputFilter")
    keys = list(layout.property("typeFilterKeys"))
    # Keyboard: no input here has one, so the list is filtered.
    kind.setProperty("currentIndex", keys.index("keyboard"))
    output.setProperty("currentIndex", 1 if output.property("count") > 1 else 0)
    j.ev("activated(currentIndex); true", kind)
    j.ev("activated(currentIndex); true", output)
    j.settle()
    j.out["typeSet"] = layout.property("actionType")
    j.out["rowsFiltered"] = layout.rowCount()

    clear = next(
        i
        for i in j.walk(page)
        if i.property("text") == "Clear"
        and i.isVisible()
        and i.metaObject().className().startswith("Button")
    )
    j.click(clear)
    j.settle()
    j.out["typeIndex"] = kind.property("currentIndex")
    j.out["outputIndex"] = output.property("currentIndex")
    j.out["typeAfter"] = layout.property("actionType")
    j.out["rowsAfter"] = layout.rowCount()


def main() -> None:
    Journey(_before).run(story)


if __name__ == "__main__":
    main()


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = run_journey(pathlib.Path(__file__), tmp_path_factory.mktemp("findclear"))
    if "error" in out:
        raise JourneyIncomplete(f"{out['error']}\n{out.get('traceback', '')}")
    return out


def test_the_type_and_output_filters_were_applied(result: dict) -> None:
    assert result["typeSet"] == "keyboard"
    assert result["rowsFiltered"] < result["rowsBefore"]


def test_clear_on_the_find_bar_resets_type_and_output(result: dict) -> None:
    assert result["typeIndex"] == 0
    assert result["outputIndex"] == 0
    assert result["typeAfter"] == "all"
    assert result["rowsAfter"] == result["rowsBefore"]
