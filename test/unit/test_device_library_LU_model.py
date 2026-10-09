# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library: the window's model (gremlin/ui/device_library_model.py)
over a stand-in Library (device_library_LU_fake_smoke.py). Rows, filters,
search, caret, details, names, busy (one change at a time), Undo, import,
tidy and settings (S3-S8, S10-S13, S15, S19, S35-S41)."""

from __future__ import annotations

import importlib.util
import pathlib
from collections.abc import Callable

import pytest
from pytestqt.qtbot import QtBot

from gremlin.ui.device_library_model import DeviceLibraryModel

_HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "device_library_LU_fake_smoke", _HERE / "device_library_LU_fake_smoke.py"
)
assert _spec and _spec.loader
fake_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_mod)
Fake = fake_mod.FakeLibrary


@pytest.fixture
def lib() -> Fake:
    return fake_mod.FakeLibrary()


@pytest.fixture
def model(qtbot: QtBot, lib: Fake) -> DeviceLibraryModel:
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()
    qtbot.waitUntil(lambda: "Library: 48 MB" in m.statusText, timeout=5000)
    return m


def _keys(model: DeviceLibraryModel) -> list[str]:
    return [r["key"] for r in model.rows]


def _run(qtbot: QtBot, model: DeviceLibraryModel, start: Callable[[], int]) -> dict:
    with qtbot.waitSignal(model.result, timeout=5000) as blocker:
        ticket = start()
    assert ticket
    return blocker.args[0]


def test_s6_s10_one_row_per_device_and_setups_under_a_caret(
    model: DeviceLibraryModel,
) -> None:
    assert _keys(model) == [f"dev-0000000{i}" for i in range(1, 6)]
    first = model.rows[0]
    assert first["stateLabel"] == "Connected" and first["countText"] == "3 saved setups"
    assert [r["stateLabel"] for r in model.rows] == [
        "Connected",
        "Connected",
        "Not connected",
        "Deleted",
        "Not connected",
    ]
    model.toggleOpen("dev-00000001")
    rows = model.rows
    assert [r["kind"] for r in rows[:4]] == ["device", "setup", "setup", "setup"]
    # S10: own setups show a save mark, autosaves an autosave mark; a renamed
    # autosave is the user's own (S13).
    assert [r["mark"] for r in rows[1:4]] == ["own", "own", "autosave"]
    assert rows[2]["sub"] == "Was an autosave, now yours"
    model.toggleOpen("dev-00000001")
    assert len(model.rows) == 5


def test_s3_filters_and_autosaves(model: DeviceLibraryModel) -> None:
    model.setFilter("deleted", False)
    assert "dev-00000004" not in _keys(model)
    model.setFilter("connected", False)
    assert _keys(model) == ["dev-00000003", "dev-00000005"]
    model.setFilter("connected", True)
    model.toggleOpen("dev-00000001")
    model.setFilter("autosaves", False)
    assert "set-00000003" not in _keys(model) and "set-00000002" in _keys(model)
    assert model.filters["autosaves"] is False


def test_s5_search_opens_devices_with_matching_setups(
    model: DeviceLibraryModel,
) -> None:
    model.setSearch("landing")
    assert _keys(model) == ["dev-00000001", "set-00000001"]
    model.setSearch("crosswind")
    assert _keys(model) == ["dev-00000003"]
    model.setSearch("")
    assert len(model.rows) == 5


def test_s4_status_bar(model: DeviceLibraryModel) -> None:
    assert model.statusText.startswith("5 devices · 6 saved setups")
    assert "Autosaves: newest 10 per stick" in model.statusText
    assert model.folderText.endswith("device library")


def test_s8_s11_details(model: DeviceLibraryModel) -> None:
    model.select("dev-00000003")
    d = model.details
    assert d["kind"] == "device" and d["stateLabel"] == "Not connected"
    model.select("set-00000001")
    d = model.details
    assert d["crumb"] == "Left throttle › saved setup"
    assert d["kept"] == "Saved by you · 2026-10-02 14:20"
    assert d["holdsLabels"] == [
        "Setup (claims, friendly names)",
        "Button Map and photo",
        "Appearance",
        "Calibration",
    ]
    assert d["bindings"] == [
        "Bindings from DCS.xml · modes Default, Landing, AAR · 212 actions"
    ]
    assert d["sends"] == "Sends to vJoy 1 (38 inputs) and vJoy 2 (4 inputs)"
    assert d["history"][0] == {
        "at": "2026-10-08",
        "text": "Copied to Right stick (Setup, Bindings)",
    }
    # Selecting a setup opens its device.
    assert "set-00000001" in _keys(model)


def test_s7_s13_rename_and_describe(model: DeviceLibraryModel, lib: Fake) -> None:
    assert model.rename("set-00000003", "Kept for later")
    assert ("rename", "set-00000003", "Kept for later") in lib.calls
    model.toggleOpen("dev-00000001")
    row = next(r for r in model.rows if r["key"] == "set-00000003")
    assert row["name"] == "Kept for later" and row["mark"] == "own"
    assert not model.rename("set-00000001", "   ")
    assert model.describe("dev-00000002", "New words")
    model.select("dev-00000002")
    assert model.details["description"] == "New words"


def test_one_change_at_a_time_and_busy(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    results: list[dict] = []
    model.result.connect(results.append)
    ticket = model.copy(
        "set-00000001", "dev-00000002", ["setup"], ["file:///C:/p/DCS.xml"], ["Default"]
    )
    assert ticket and model.busy
    assert model.swap("dev-00000001", "dev-00000002", ["setup"], []) == 0
    assert results[-1]["op"] == "swap" and not results[-1]["ok"]
    assert "still running" in results[-1]["error"]
    # Copy changes the open profile: it runs on the main thread (LP's rule),
    # after the window has drawn busy.
    assert not any(c[0] == "copy" for c in lib.calls)
    qtbot.waitUntil(lambda: not model.busy, timeout=5000)
    qtbot.waitUntil(lambda: any(r["op"] == "copy" for r in results), timeout=5000)
    done = next(r for r in results if r["op"] == "copy")
    assert done["ok"] and done["ticket"] == ticket
    call = next(c for c in lib.calls if c[0] == "copy")
    assert call[2] == "Right stick" and call[4] == [str(pathlib.Path("C:/p/DCS.xml"))]
    # S53: the Copy is a step; its Undo goes through the autosaves (the
    # owner's undo, S33), then Redo names it.
    assert model.undoText == "Undo Copied DCS F-16, Viper layout to Right stick"
    res = _run(qtbot, model, model.undo)
    assert res["ok"] and ("undo_last",) in lib.calls
    assert model.undoText == ""
    assert model.redoText == "Redo Copied DCS F-16, Viper layout to Right stick"
    assert model.undo() == 0


def test_a_failed_change_says_why(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    lib.fail["copy"] = "The autosave could not be written."
    res = _run(
        qtbot,
        model,
        lambda: model.copy("set-00000001", "dev-00000002", ["setup"], [], []),
    )
    assert not res["ok"] and res["error"] == "The autosave could not be written."
    assert not model.busy


def test_plans_and_profiles_come_back_with_their_ticket(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    res = _run(
        qtbot,
        model,
        lambda: model.planCopy(
            "set-00000001", "dev-00000002", ["setup", "bindings"], [], ["Default"]
        ),
    )
    assert res["op"] == "planCopy" and len(res["warnings"]) == 3
    assert not model.busy
    res = _run(
        qtbot, model, lambda: model.profilesUsing(["{AAAA-0001}", "{BBBB-0002}"])
    )
    assert [p["name"] for p in res["profiles"]] == [
        "DCS.xml",
        "StarCitizen.xml",
        "Elite.xml",
    ]
    res = _run(
        qtbot, model, lambda: model.planOutput("dev-00000001", {"1": 2}, True, [])
    )
    assert res["rows"][0]["changes"] and res["others"][0]["name"] == "Right stick"
    assert next(c for c in lib.calls if c[0] == "plan_output")[2] == {1: 2}
    res = _run(
        qtbot,
        model,
        lambda: model.planSwap("dev-00000001", "dev-00000002", ["setup"], []),
    )
    assert len(res["warnings"]) == 2


def test_s35_s39_import_takes_only_a_zip(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake, tmp_path: pathlib.Path
) -> None:
    results: list[dict] = []
    model.result.connect(results.append)
    assert model.importPack((tmp_path / "notes.txt").as_uri()) == 0
    assert not results[-1]["ok"] and "isn't a Device Pack" in results[-1]["error"]
    res = _run(
        qtbot, model, lambda: model.importPack((tmp_path / "Sam MFDs.zip").as_uri())
    )
    assert res["ok"] and lib.calls[-1][0] == "import_pack"
    assert model.statusText.startswith("5 devices · 7 saved setups")


def test_s14_export_adds_zip(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake, tmp_path: pathlib.Path
) -> None:
    _run(
        qtbot,
        model,
        lambda: model.exportSetup("set-00000001", (tmp_path / "mine").as_uri()),
    )
    assert lib.calls[-1] == ("export_setup", "set-00000001", str(tmp_path / "mine.zip"))


def test_s15_delete_and_s38_tidy(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    model.select("set-00000006")
    res = _run(qtbot, model, lambda: model.deleteItem("set-00000006"))
    assert res["ok"] and model.selected == ""
    preview = model.tidyPreview(1)
    assert [p["key"] for p in preview] == ["set-00000005", "set-00000003"]
    assert ("tidy",) not in [c[:1] for c in lib.calls]
    _run(qtbot, model, lambda: model.tidy(["set-00000005"]))
    assert ("tidy", ["set-00000005"]) in lib.calls


def test_s36_settings(qtbot: QtBot, model: DeviceLibraryModel, lib: Fake) -> None:
    assert model.settings()["keep"] == 10
    _run(
        qtbot,
        model,
        lambda: model.setSettings(
            {"keep": 5, "default_parts": ["setup", "calibration", "bogus"]}
        ),
    )
    assert lib.calls[-1] == (
        "set_settings",
        {"keep": 5, "default_parts": ["setup", "calibration"]},
    )
    assert "Autosaves: newest 5 per stick" in model.statusText


def test_s12_save_and_connected_sticks(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    sticks = model.connectedSticks()
    assert [s["name"] for s in sticks] == ["Left throttle", "Right stick"]
    assert sticks[1]["label"] == "Right stick  (VKB Gunfighter Mk IV)"
    res = _run(
        qtbot,
        model,
        lambda: model.saveToLibrary("dev-00000002", ["file:///C:/p/Elite.xml"]),
    )
    assert res["ok"] and lib.calls[-1][:3] == (
        "save_setup",
        "Right stick",
        "{BBBB-0002}",
    )
    assert model.findDevice("", "bbbb-0002") == "dev-00000002"
    assert model.findDevice("Rudder pedals", "") == "dev-00000003"
