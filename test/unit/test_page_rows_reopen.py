# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The list pages' rows follow the device and the edits without a stale
frame or a list-view warning.

SHAKE-STRESS-09: opening the Device Bindings page of another stick while the
page is shown kept the first stick's rows until a later event (Main's
deferred syncDeviceBindingsPage); the rows must belong to the new stick as
soon as the card is opened.

SHAKE-JOURNEYS-02: a Logical Device step sequence (shrunk from the audit's
random walks) made the page's ListView log "DelegateModel::cancel: index
out range" because every rebuild was a full model reset, even when nothing
changed. The rows now change with the smallest insert/remove/change.

The program runs off-screen in its own process (journey harness), with a
temporary USERPROFILE and fake hardware.

Spec: 05 S121, S127 (the page shows the chosen device); none for the
warning (no behaviour change).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from typing import Any

import pytest

JOURNEYS = pathlib.Path(__file__).resolve().parents[1] / "journeys"
sys.path.insert(0, str(JOURNEYS))
from _harness import Journey, run_journey, step  # noqa: E402

THROTTLE_BUTTONS = [1, 2, 3]

# SHAKE-JOURNEYS SJ-02, shrunk by the audit (6 of 6 runs logged the warning).
SJ02_OPS = [
    {"op": "switch_page", "page": "logical"},
    {"op": "add", "type": "hat", "n": 2},
    {"op": "add_group", "name": "G2"},
    {"op": "action_ok", "key": "parent:hat:2", "out": 28},
    {"op": "add", "type": "button", "n": 1},
    {"op": "add", "type": "hat", "n": 3},
    {"op": "add", "type": "hat", "n": 2},
    {"op": "save"},
    {"op": "delete_group", "name": "Stick"},
    {"op": "delete_action", "key": "parent:hat:2", "seq": 0},
]


def _j11() -> Any:  # noqa: ANN401
    spec = importlib.util.spec_from_file_location(
        "j11_random", JOURNEYS / "test_j11_random_list_pages.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _device_switch(j: Journey) -> None:
    """pJoy Pro's page, then the Throttle card: the rows at once."""
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    layout = j.open_device_bindings("pjoy_pro")
    j.settle()
    first = {
        "guid": str(layout.property("guid")),
        "parents": int(layout.property("parentCount")),
    }
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("throttle"))')
    page = j.ev("deviceBindingsPane()")
    now = page.findChild(HardwareLayoutModel)
    at_once = {
        "guid": str(now.property("guid")),
        "deviceName": str(now.property("deviceName")),
        "parents": int(now.property("parentCount")),
        "shown": str(j.backend.uiState.currentDevice),
    }
    j.settle()
    later = {
        "guid": str(now.property("guid")),
        "deviceName": str(now.property("deviceName")),
        "parents": int(now.property("parentCount")),
    }
    j.out["switch"] = {"first": first, "at_once": at_once, "later": later}


def _sj02(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import util
    from gremlin.ui.profile import ModeHierarchyModel

    j11 = _j11()
    j11._install_hooks()
    ModeHierarchyModel().newMode("Combat")
    walk = j11._Random(j, 0)
    path = util.profiles_dir() / "sj02.xml"
    walk.url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.backend.saveProfile(walk.url)
    walk.open_page("config")
    j11.PY_EXC.clear()
    j11.QT_MSGS.clear()
    for i, op in enumerate(SJ02_OPS):
        walk.idx = i
        walk.ops.append(op)
        walk.do(op)
        j.settle()
        walk.check_logs()
    j.out["sj02_failures"] = walk.failures


def story(j: Journey) -> None:
    _device_switch(j)
    _sj02(j)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        guid = j.add_stick("Throttle", 3)
        j.input_module("Throttle", buttons=THROTTLE_BUTTONS, guid=guid, slug="throttle")
        j.vjoy_module()

    Journey(before).run(story)


# --- pytest side ----------------------------------------------------------------


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("page_rows"))


def test_rows_belong_to_the_new_device_at_once(run: dict) -> None:
    switch = step(run, "switch")
    assert switch["first"]["guid"] != switch["later"]["guid"], switch
    assert switch["later"]["deviceName"] == "Throttle", switch
    # Nothing waits for a later event: the page already shows the Throttle.
    shown = {key: value for key, value in switch["at_once"].items() if key != "shown"}
    assert shown == switch["later"], switch


def test_shrunk_sj02_steps_log_no_list_warning(run: dict) -> None:
    failures = step(run, "sj02_failures")
    assert failures == [], json.dumps(failures, indent=1)[:4000]


if __name__ == "__main__":
    main()
