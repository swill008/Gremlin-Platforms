# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library S15, S43-S50: the real window's right-click menus,
off-screen in its own process (device_library_CU_menus_smoke.py) with the
real model over a stand-in Library and a stand-in main window: right-click
selects first then opens (S43), the items per row kind and state (S44-S46,
hidden not greyed: 01 S66), delete items red and asked first naming what
goes (S47), Remove from Library runs Home's Delete Device first when a
module file is still here and stops when it is refused (S15), Clear Setup,
Delete Saved Setups, Restore (S48), Keep (S49), Ctrl/Shift-click several
rows and one question (S50), the Menu key and Shift+F10 (S43), and Show on
Home / Open Module Setup / Open Button Map reaching Main (S44)."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("dl_menus")
    proc = subprocess.run(
        [sys.executable, str(_HERE / "device_library_CU_menus_smoke.py"), str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_HERE.parents[1]),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1"},
    )
    results: dict = {"errors": [], "warnings": [], "calls": [], "out": out}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            value = json.loads(value)
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
            results[name] = value
        elif line.startswith("ERROR"):
            results["errors"].append(line)
        elif line.startswith("WARN"):
            results["warnings"].append(line)
        elif line.startswith("CALLS "):
            results["calls"] = json.loads(line[6:])
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def _names(run: dict) -> list[str]:
    return [c[0] for c in run["calls"] if c[0] not in ("inputs", "photo", "note_seen")]


def _menu(text: str) -> list[str]:
    return text.split("|")


def test_runs_without_errors_or_warnings(run: dict) -> None:
    assert run["errors"] == []
    assert run["warnings"] == []
    for shot in (
        "real_ctx_device",
        "real_ctx_setup",
        "real_ctx_multi",
        "real_ctx_confirm",
    ):
        assert (run["out"] / f"{shot}.png").stat().st_size > 1000


def test_s43_right_click_selects_first_then_opens(run: dict) -> None:
    got = run["rc-connected"]
    assert got["selected"] == got["details"] == "dev-00000001"
    assert got["picked"] == ["dev-00000001"] and got["highlighted"]
    setup = run["rc-setup"]
    assert setup["selected"] == setup["details"] == "set-00000001"


def test_s44_s15_connected_device_menu(run: dict) -> None:
    got = run["rc-connected"]
    assert _menu(got["menu"]) == [
        "Left throttle · Connected",
        "Copy to Another Stick…",
        "Swap with Another Stick…",
        "Change vJoy Output…",
        "Save to Device Library…",
        "Export Current Setup…",
        "Rename… (F2)",
        "Edit Description",
        "Open Module Setup…",
        "Open Button Map",
        "Show on Home",
        "Expand",
        "Clear Setup…",
        "Its settings go; the stick stays plugged in (off)",
        "Delete Saved Setups…",
        "Only the saved setups go; its settings stay (off)",
    ]
    assert got["danger"] == ["Clear Setup…", "Delete Saved Setups…"]


def test_s44_s15_not_connected_and_deleted_device_menus(run: dict) -> None:
    got = run["rc-not-connected"]
    assert _menu(got["menu"]) == [
        "Rudder pedals · Not connected",
        "Copy to Another Stick…",
        "Change vJoy Output…",
        "Save to Device Library…",
        "Export Current Setup…",
        "Rename… (F2)",
        "Edit Description",
        "Open Module Setup…",
        "Open Button Map",
        "Show on Home",
        "Remove from Library…",
        "Gone from the Library, with its saved setups (off)",
    ]
    assert got["danger"] == ["Remove from Library…"]
    # Deleted: nothing current here, no Home card; only what applies.
    assert _menu(run["rc-deleted"]) == [
        "Old Warthog stick · Deleted",
        "Change vJoy Output…",
        "Rename… (F2)",
        "Edit Description",
        "Expand",
        "Remove from Library…",
        "Gone from the Library, with its saved setups (off)",
    ]


def test_s45_saved_setup_menus(run: dict) -> None:
    got = run["rc-setup"]
    assert _menu(got["menu"]) == [
        "DCS F-16, Viper layout",
        "Copy to Another Stick…",
        "Restore to This Stick…",
        "Export…",
        "Rename… (F2)",
        "Edit Description",
        "Delete…",
    ]
    assert got["danger"] == ["Delete…"]
    assert "Keep This Autosave" in _menu(run["rc-autosave"])
    # Its stick isn't plugged in: no Restore (S48).
    unplugged = _menu(run["rc-autosave-unplugged"])
    assert "Restore to This Stick…" not in unplugged
    assert "Keep This Autosave" in unplugged


def test_s46_empty_space_menu(run: dict) -> None:
    assert _menu(run["rc-space"]["menu"]) == [
        "Device Library",
        "Import Device Pack…",
        "Expand All",
        "Collapse All",
        "Device Library Settings…",
    ]


def test_s49_keep_and_edit_description(run: dict) -> None:
    assert run["keep"]["mark"] == "own"
    assert ["keep", "set-00000003"] in run["calls"]
    assert run["edit-description"] == {"focus": True, "key": "set-00000001"}


def test_s15_s47_remove_asks_and_runs_delete_device_first(run: dict) -> None:
    ask = run["remove-ask"]
    assert ask["title"] == "Remove Rudder pedals from the Library?"
    assert "module file" in ask["body"] and ask["red"] and ask["go"] == "Remove"
    # D-10-DELETE-CLARITY: nothing is said to be kept (Remove deletes it all).
    assert "Nothing is kept: this can't be undone." in ask["body"]
    assert "autosave is kept" not in ask["body"]
    # Refused (the profile runs): nothing removed from the Library.
    refused = run["remove-refused"]
    assert refused["bad"] and refused["message"].startswith("Stop the profile first")
    assert "dev-00000003" in refused["rows"]
    names = _names(run)
    first = names.index("main.deleteDevice")
    assert names[first + 1] == "main.deleteDevice"
    assert names[first + 2] == "remove_device"
    assert ["remove_device", "dev-00000003"] in run["calls"]
    assert names.count("remove_device") == 2
    # No module file here: no Delete Device.
    assert run["remove-no-module"] == (
        "Remove Friend's MFD pair and its saved setup from the Library?"
    )
    deletes = [c for c in run["calls"] if c[0] == "main.deleteDevice"]
    assert all(c[1] != "Friend's MFD pair" for c in deletes)


def test_s15_clear_setup_and_delete_saved_setups(run: dict) -> None:
    title, body = run["clear-setup"]
    assert title == "Clear the setup of Right stick?"
    assert "autosave" in body and "stays plugged in" in body
    assert ["main.deleteDevice", "Right stick", "right_stick"] in run["calls"]
    title, body = run["delete-setups"]
    assert title == "Delete Right stick's saved setup?"
    assert "keeps its settings" in body
    assert ["delete_saved_setups", "dev-00000002"] in run["calls"]


def test_s48_restore_with_busy_mark_and_undo(run: dict) -> None:
    title, go, danger, busy, mark = run["restore"]
    assert title == "Restore “DCS F-16, Viper layout” to Left throttle?"
    assert go == "Restore" and danger is False
    assert busy and mark
    assert ["restore_to_stick", "set-00000001"] in run["calls"]
    after = run["restore-after"]
    assert after["undo"] == "Undo Restore DCS F-16 to Left throttle"
    assert after["busyMark"] is False


def test_s44_routes_reach_main(run: dict) -> None:
    assert [
        c
        for c in run["calls"]
        if c[0] in ("main.home", "main.moduleSetup", "main.buttonMap")
    ] == [
        ["main.home", "Left throttle", "left_throttle"],
        ["main.moduleSetup", "Left throttle", "left_throttle"],
        ["main.buttonMap", "Left throttle", "left_throttle"],
    ]


def test_s50_several_saved_setups_one_question(run: dict) -> None:
    got = run["multi-setups"]
    assert got["picked"] == ["set-00000001", "set-00000002", "set-00000003"]
    assert got["highlighted"] == [True, True, True]
    # Single-row actions are hidden.
    assert _menu(got["menu"]) == ["3 saved setups", "Delete…"]
    assert got["danger"] == ["Delete…"] and got["copy"] is False
    ask = run["multi-ask"]
    assert ask["title"] == "Delete these 3 saved setups?"
    for name in (
        "DCS F-16, Viper layout",
        "Star Citizen 4.0",
        "Autosave: before Copy from Old Warthog",
    ):
        assert name in ask["body"]
    assert ["delete_many", "['set-00000001', 'set-00000002', 'set-00000003']"] in run[
        "calls"
    ]


def test_s50_several_devices(run: dict) -> None:
    assert run["shift-range"]["picked"] == [
        "dev-00000001",
        "dev-00000002",
        "dev-00000006",
        "dev-00000004",
    ]
    got = run["multi-devices"]
    # A connected one among them: Remove from Library doesn't apply, and a
    # grey line says why (user, 2026-10-08) instead of an empty menu.
    assert _menu(got["connectedIncluded"]) == [
        "2 devices",
        "Remove from Library works only on devices that aren't plugged in (off)",
    ]
    assert _menu(got["menu"]) == ["2 devices", "Remove from Library…"]
    title, body = run["multi-devices-go"]
    assert title == "Remove these 2 devices and their saved setup from the Library?"
    assert "Old Warthog stick" in body and "Throttle Quadrant" in body
    assert "module file" not in body
    assert ["delete_many", "['dev-00000004', 'dev-00000006']"] in run["calls"]


def test_s43_keyboard_and_hover(run: dict) -> None:
    assert run["keys-shift-f10"] == {
        "selected": "dev-00000001",
        "title": "Left throttle · Connected",
    }
    assert run["keys-menu"] == {
        "selected": "dev-00000002",
        "title": "Right stick · Connected",
    }
    assert run["hover"] is True


def test_s44_export_current(run: dict) -> None:
    assert run["export-current"] == "Current setup exported."
    calls = [c for c in run["calls"] if c[0] == "export_current"]
    assert calls and calls[0][1] == "dev-00000001"
    assert calls[0][2].endswith("Left throttle.zip")
