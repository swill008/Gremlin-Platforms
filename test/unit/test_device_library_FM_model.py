# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library model, the fix wave (agent FM), over LU's stand-in
Library (device_library_LU_fake_smoke.py):

- Gap 1 (S12, S22, S26): every owner call gets the device's id and its own
  name (not the Home alias the Library shows); twins are distinct targets.
- Gap 6 (S23, 08 S89, D-10-PROFILES): the open profile is always offered.
- Gap 9: the open profile is read on the main thread, saved ones in the
  background.
- Gap 10 (section 6): plans wait for ticks to settle. A plan runs on the
  main thread (FM2, item 7: it reads the device lists and the open
  profile); its saved profiles are read in the background through
  library_profiles (test_device_library_FM2_threads.py).
- S11 / S41 wording, S30 the vJoys that exist.
"""

from __future__ import annotations

import gc
import importlib.util
import pathlib
import threading
from collections.abc import Callable

import pytest
from pytestqt.qtbot import QtBot

from gremlin import threads
from gremlin.ui.device_library_model import DeviceLibraryModel

_HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "device_library_LU_fake_smoke", _HERE / "device_library_LU_fake_smoke.py"
)
assert _spec and _spec.loader
fake_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_mod)
Fake = fake_mod.FakeLibrary

_MAIN = threading.main_thread().name
_DCS = str(pathlib.Path("C:/p/DCS.xml"))
_ELITE = str(pathlib.Path("C:/p/Elite.xml"))


@pytest.fixture
def lib() -> Fake:
    return fake_mod.FakeLibrary()


@pytest.fixture
def model(qtbot: QtBot, lib: Fake) -> DeviceLibraryModel:
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()
    qtbot.waitUntil(lambda: "Library: 48 MB" in m.statusText, timeout=5000)
    return m


def _run(qtbot: QtBot, model: DeviceLibraryModel, start: Callable[[], int]) -> dict:
    with qtbot.waitSignal(model.result, timeout=5000) as blocker:
        ticket = start()
    assert ticket
    return blocker.args[0]


def _calls(lib: Fake, name: str) -> list[tuple]:
    return [c for c in lib.calls if c[0] == name]


def _alias_right_stick(lib: Fake, model: DeviceLibraryModel) -> None:
    # Renamed on Home: the Library shows the alias; its own name finds its
    # module file (S7).
    lib.devs[1]["name"] = "My right hand"
    lib.devs[1]["ownName"] = "Right stick"
    model.refresh()


def test_gap1_owner_calls_get_the_own_name_and_the_id(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    _alias_right_stick(lib, model)
    _run(
        qtbot,
        model,
        lambda: model.planCopy("set-00000001", "dev-00000002", ["setup"], [], []),
    )
    plan = _calls(lib, "plan_copy")[-1]
    assert plan[2] == "Right stick" and plan[-1] == "{BBBB-0002}"
    _run(
        qtbot,
        model,
        lambda: model.copy("set-00000001", "dev-00000002", ["setup"], [], []),
    )
    done = _calls(lib, "copy")[-1]
    assert done[2] == "Right stick" and done[-1] == "{BBBB-0002}"
    _run(
        qtbot, model, lambda: model.swap("dev-00000001", "dev-00000002", ["setup"], [])
    )
    assert _calls(lib, "swap")[-1][2] == ("Right stick", "{BBBB-0002}")
    _run(
        qtbot,
        model,
        lambda: model.planSwap("dev-00000001", "dev-00000002", ["setup"], []),
    )
    assert _calls(lib, "plan_swap")[-1][2] == ("Right stick", "{BBBB-0002}")
    _run(qtbot, model, lambda: model.planOutput("dev-00000002", {"1": 2}, False, []))
    assert _calls(lib, "plan_output")[-1][1] == "Right stick"
    assert _calls(lib, "plan_output")[-1][-1] == "{BBBB-0002}"
    _run(qtbot, model, lambda: model.changeOutput("dev-00000002", {"1": 2}, False, []))
    assert _calls(lib, "change_output")[-1][1] == "Right stick"
    assert _calls(lib, "change_output")[-1][-1] == "{BBBB-0002}"
    _run(qtbot, model, lambda: model.saveToLibrary("dev-00000002", []))
    assert _calls(lib, "save_setup")[-1][1:3] == ("Right stick", "{BBBB-0002}")


def test_gap1_twins_are_distinct_targets(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    twin = {
        "key": "dev-00000006",
        "name": "Right stick",
        "description": "",
        "state": "connected",
        "guid": "{EEEE-0006}",
        "module": "right-stick-2",
        "setups": [],
    }
    lib.devs.insert(2, twin)
    model.refresh()
    sticks = model.connectedSticks()
    assert [s["key"] for s in sticks] == [
        "dev-00000001",
        "dev-00000002",
        "dev-00000006",
    ]
    labels = [s["label"] for s in sticks]
    assert len(set(labels)) == 3, labels
    assert labels[1] == "Right stick [BBBB0002]  (VKB Gunfighter Mk IV)"
    assert labels[2] == "Right stick [EEEE0006]"
    _run(
        qtbot,
        model,
        lambda: model.copy("set-00000001", "dev-00000006", ["setup"], [], []),
    )
    assert _calls(lib, "copy")[-1][-1] == "{EEEE-0006}"


def test_gap6_the_open_profile_is_always_offered(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    # A deleted stick's autosave onto a stick with no bindings: neither has
    # bindings in any profile, yet the open profile is offered (S23).
    res = _run(qtbot, model, lambda: model.profilesUsing(["{DDDD-0004}"], True))
    assert res["profiles"] == [
        {"path": "C:/p/DCS.xml", "name": "DCS.xml", "open": True, "actions": 0}
    ]
    # Save to Device Library (S12) lists only profiles with bindings.
    res = _run(qtbot, model, lambda: model.profilesUsing(["{DDDD-0004}"]))
    assert res["profiles"] == []


def test_gap9_open_profile_on_the_main_thread_saved_ones_in_the_background(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    res = _run(qtbot, model, lambda: model.profilesUsing(["{AAAA-0001}"], True))
    assert [p["name"] for p in res["profiles"]] == [
        "DCS.xml",
        "StarCitizen.xml",
        "Elite.xml",
    ]
    assert lib.threads["open"] == _MAIN
    assert lib.threads["saved"] != _MAIN
    # The saved scan leaves out the open profile's file.
    assert _calls(lib, "saved_profiles_using")[-1][2] == "C:/p/DCS.xml"


def test_gap10_replans_settle_and_run_once(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    results: list[dict] = []
    model.result.connect(results.append)
    profiles = ["file:///C:/p/DCS.xml", "file:///C:/p/Elite.xml"]
    tickets = [
        model.planCopy("dev-00000001", "dev-00000002", ["bindings"], profiles, [m])
        for m in ("A", "B", "C", "D", "E")
    ]
    # Ticks don't plan on the spot; the window shows it is checking.
    assert not _calls(lib, "plan_copy") and model.planning
    qtbot.waitUntil(lambda: any(r["op"] == "planCopy" for r in results), timeout=5000)
    qtbot.waitUntil(lambda: not model.planning, timeout=5000)
    plans = [r for r in results if r["op"] == "planCopy"]
    assert [r["ticket"] for r in plans] == [tickets[-1]]
    # One replan for five ticks, on the main thread (FM2 item 7).
    calls = _calls(lib, "plan_copy")
    assert [(c[4], c[5]) for c in calls] == [([_DCS, _ELITE], ["E"])]
    assert lib.plan_threads == [_MAIN]
    assert len(plans[0]["warnings"]) == 3
    assert plans[0]["sourceModes"] == ["Default", "Combat"]


def test_gap10_a_plan_runs_on_the_main_thread(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    # From a saved setup the bindings come from its pack.
    res = _run(
        qtbot,
        model,
        lambda: model.planCopy(
            "set-00000001", "dev-00000002", ["bindings"], ["file:///C:/p/DCS.xml"], []
        ),
    )
    assert res["ok"] and lib.plan_threads == [_MAIN]


def test_s30_only_the_vjoys_that_exist(model: DeviceLibraryModel, lib: Fake) -> None:
    assert model.vjoyNumbers() == [1, 2, 3]
    lib.vjoys = [2]
    assert model.vjoyNumbers() == [2]


def test_s11_setup_wording(model: DeviceLibraryModel) -> None:
    model.select("set-00000001")
    assert model.details["holdsLabels"][0] == "Setup (claims, friendly names)"


def test_s53_undo_and_redo_are_separate(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    """S53 (replaces S41's single "Undo"/"Redo" item): Undo names the
    newest step, Redo the one undone; the Library's last change alone is
    no step."""
    lib.last = {"op": "copy", "autosaves": ["a"], "label": "Copy DCS F-16"}
    model.refresh()
    assert model.undoText == "" and model.redoText == ""
    _run(
        qtbot,
        model,
        lambda: model.copy("set-00000001", "dev-00000002", ["setup"], [], ["Default"]),
    )
    assert model.undoText.startswith("Undo Copied ")
    _run(qtbot, model, model.undo)
    assert model.undoText == ""
    assert model.redoText.startswith("Redo Copied ")


def test_a_model_gone_mid_change_lets_its_thread_end(qtbot: QtBot, lib: Fake) -> None:
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()
    lib.gate = threading.Event()
    # The saved profiles' scan runs on a program thread.
    lib.saved_profiles_using = lambda guids, open_path="": (  # type: ignore[method-assign]
        lib.gate.wait(10),
        [],
    )[1]
    assert m.profilesUsing(["{AAAA-0001}"])
    import shiboken6

    shiboken6.delete(m)
    del m
    gc.collect()
    lib.gate.set()
    qtbot.waitUntil(
        lambda: not any("Device Library" in n for n in threads.running()), timeout=5000
    )


def test_twins_are_told_apart_in_the_device_list(
    model: DeviceLibraryModel, lib: Fake
) -> None:
    lib.devs.insert(
        2,
        {
            "key": "dev-00000006",
            "name": "Right stick",
            "description": "",
            "state": "connected",
            "guid": "{EEEE-0006}",
            "module": "right-stick-2",
            "setups": [],
        },
    )
    model.refresh()
    rows = {r["key"]: r for r in model.rows}
    assert rows["dev-00000002"]["label"] == "Right stick [BBBB0002]"
    assert rows["dev-00000006"]["label"] == "Right stick [EEEE0006]"
    # Only twins get the id; the name stays the same everywhere else.
    assert rows["dev-00000001"]["label"] == "Left throttle"
    assert rows["dev-00000006"]["name"] == "Right stick"
    model.select("dev-00000006")
    assert model.details["name"] == "Right stick"
    model.setSearch("right stick")
    assert {"dev-00000002", "dev-00000006"} <= {r["key"] for r in model.rows}
