# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Output Module view (qml/OutputModuleView.qml) passes its device to
its DeviceLiveState and claimed-input model with Binding objects
(memory-qml-factory.md, stage 1).

1. Changing the view's device logs no "changed from elsewhere" warning:
   DeviceLiveState.deviceName has its own change signal, not guidChanged.
2. Swapping to a device with the same number of claimed inputs still
   rebuilds the view with the new device's inputs (the order the view's
   own guid handler and the Binding run in must not matter).

A journey (test/journeys/_harness.py): the real program off-screen with a
temporary USERPROFILE and fake hardware.

Spec: none (no behaviour change).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402

STICK_A = "pJoy Pro"
STICK_B = "Stick Bee"
_SEED_B = 41

_BUTTONS = (
    "(function() { var a = [];"
    " for (var i = 0; i < buttonModel.count; ++i) a.push(buttonModel.get(i).hw);"
    " return a })()"
)


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _before(j: Journey) -> None:
    j.input_module(STICK_A, buttons=[1, 2, 3])
    guid_b = j.add_stick(STICK_B, _SEED_B)
    j.input_module(STICK_B, buttons=[5, 6, 7], guid=guid_b)


def story(j: Journey) -> None:
    from PySide6 import QtCore

    messages: list[str] = []
    previous = None

    def handler(kind: Any, context: Any, text: str) -> None:  # noqa: ANN401
        messages.append(str(text))
        if previous is not None:
            previous(kind, context, text)

    previous = QtCore.qInstallMessageHandler(handler)

    guid_a = str(j.stick(STICK_A).device_guid.uuid)
    guid_b = str(j.stick(STICK_B).device_guid.uuid)
    view = j.ev(
        "(function() {"
        " var win = Qt.createQmlObject('import QtQuick; import QtQuick.Window;"
        " Window { width: 1200; height: 800; visible: true }', _root, 'outhost');"
        " var c = Qt.createComponent('OutputModuleView.qml');"
        " if (c.status !== Component.Ready) return 'error: ' + c.errorString();"
        f" var v = c.createObject(win.contentItem, {{ guid: {guid_a!r},"
        f" deviceName: {STICK_A!r} }});"
        " if (!v) return 'error: not made';"
        " return v })()"
    )
    j.out["made"] = "ok" if hasattr(view, "metaObject") else str(view)
    j.settle()
    j.out["buttonsA"] = j.ev(_BUTTONS, view)

    # Device swaps as Main makes them: the id first, then the name.
    for n, (guid, name) in enumerate(
        ((guid_b, STICK_B), (guid_a, STICK_A), (guid_b, STICK_B))
    ):
        j.ev(f"guid = {guid!r}; deviceName = {name!r}; true", view)
        j.settle()
        j.out[f"buttons{n}"] = j.ev(_BUTTONS, view)

    QtCore.qInstallMessageHandler(previous)
    j.out["messages"] = messages


def main() -> None:
    from _harness import Journey as _J

    _J(_before).run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


import pytest  # noqa: E402


@pytest.fixture(scope="module")
def swaps(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = run_journey(pathlib.Path(__file__), tmp_path_factory.mktemp("swaps"))
    assert "error" not in out, (out.get("error"), out.get("traceback"))
    assert step(out, "made") == "ok"
    return out


def test_device_swap_logs_no_binding_warning(swaps: dict) -> None:
    elsewhere = [m for m in step(swaps, "messages") if "changed from elsewhere" in m]
    assert elsewhere == []


def test_swap_with_same_claim_count_shows_new_inputs(swaps: dict) -> None:
    assert step(swaps, "buttonsA") == [1, 2, 3]
    # Same number of claimed inputs on both: still the new device's.
    assert step(swaps, "buttons0") == [5, 6, 7]
    assert step(swaps, "buttons1") == [1, 2, 3]
    assert step(swaps, "buttons2") == [5, 6, 7]
