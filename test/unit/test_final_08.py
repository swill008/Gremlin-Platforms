# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final phase: the page 08 statements (History, Device Pack, Auto Mapper)
that had no check yet. The plan is claude/final-test-plan/08-history-pack-automap.md.

Every test points History at a tmp folder (the stage 1 `folder` fixture or
`store` here) after the History work earlier tests queued is written.
"""

from __future__ import annotations

import json
import uuid
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from gremlin import (
    clock,
    config,
    deferred_write,
    history,
    history_profile,
    util,
)
from gremlin.auto_mapper import AutoMapper, AutoMapperOptions
from gremlin.modules import auto_map
from gremlin.profile import Profile
from gremlin.types import PropertyType
from gremlin.ui import device_pack, hardware_profile, history_model
from test.unit import test_stage1_modules
from test.unit.test_stage1_history_pack import (
    _pack_map,
    _pack_with_wires,
    _url,
    _write_zip,
    new_profile,
)
from test.unit.test_stage1_modules import (
    map_button,
    mapped,
    settle_history,
    setup_cards,
    stick_doc,
    stick_guid,
    stick_uid,
    vjoy_doc,
    write_module,
)

# Qt's application (the deferred settings write needs it) and the modules
# folder, emptied and put back, with History in a tmp folder.
_app = test_stage1_modules._app
folder = test_stage1_modules.folder


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """History in a tmp folder (no clean-up at the first entry)."""
    settle_history()
    path = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: path)
    monkeypatch.setattr(history, "_pruned", True)
    yield path
    settle_history()


@pytest.fixture
def cfg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[config.Configuration]:
    """The settings, written to a tmp file; their entries put back after."""
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    settings = config.Configuration()
    monkeypatch.setattr(
        settings, "_data", {k: dict(v) for k, v in settings._data.items()}
    )
    monkeypatch.setattr(settings, "_history_view", None, raising=False)
    yield settings
    # A write still waiting goes to the tmp file, not the user's.
    deferred_write.flush("configuration")


def _keep_days(settings: config.Configuration) -> None:
    if not settings.exists("global", "history", "keep-days"):
        settings.register(
            "global", "history", "keep-days", PropertyType.Int, 90, "",
            {"min": 1, "max": 3650}, True,
        )


def _write_entries(path: Path, area: str, entries: list[dict]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with open(path / f"{area}.jsonl", "a", encoding="utf-8", newline="") as out:
        for entry in entries:
            out.write(json.dumps(entry) + "\n")


def _entry(area: str, kind: str, title: str, at: float, **extra: object) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "at": at,
        "area": area,
        "kind": kind,
        "title": title,
        "subject": extra.pop("subject", {}),
        "before": extra.pop("before", None),
        "after": extra.pop("after", None),
    }


def _role(model: history_model.HistoryModel, row: int, name: str) -> object:
    role = history_model._ROLES.index(name) + 1 + int(
        history_model.QtCore.Qt.ItemDataRole.UserRole
    )
    return model.data(model.index(row, 0), role)


# --- History: what is kept --------------------------------------------------


def test_s1_changes_are_kept_in_the_history_folder_not_the_profile(
    store: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "p.xml"
    profile = new_profile(monkeypatch, path)
    profile.to_xml(path)
    map_button(profile, stick_uid(), 1, 1)
    profile.to_xml(path)
    settle_history()
    found = history.entries("profile")
    assert found and (store / "profile.jsonl").is_file()
    text = path.read_text(encoding="utf-8-sig")
    assert not any(e["id"] in text for e in found)
    assert "history" not in text.lower()


def test_s5_only_the_newest_20_saves_keep_the_whole_profile(store: Path) -> None:
    now = clock.now()
    packed = {"packed": history_profile.pack_text("<profile/>")}
    saves = [
        _entry(
            "profile", "profile", f"Saved p.xml {n}", now - 100 + n,
            subject={"profile": "C:/p.xml"}, before=packed, after=packed,
        )
        for n in range(history.SNAPSHOTS + 2)
    ]
    change = _entry(
        "profile", "input", "Changed the actions of X Button 1 in Default",
        now - 100, subject={"profile": "C:/p.xml"}, before={"a": 1}, after={"a": 2},
    )
    _write_entries(store, "profile", [change, *saves])
    history.prune()
    kept = {e["id"]: e for e in history.entries("profile")}
    oldest = [saves[0]["id"], saves[1]["id"]]
    assert all(kept[i]["before"] is None and kept[i]["after"] is None for i in oldest)
    assert all(kept[s["id"]]["after"] == packed for s in saves[2:])
    # Older saves keep what they changed.
    assert kept[change["id"]]["after"] == {"a": 2}


def test_s6_a_save_with_the_same_text_makes_no_entry(
    store: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "p.xml"
    profile = new_profile(monkeypatch, path)
    map_button(profile, stick_uid(), 1, 1)
    profile.to_xml(path)
    settle_history()
    count = len(history.entries("profile"))
    profile.to_xml(path)  # saved again, nothing changed
    settle_history()
    assert len(history.entries("profile")) == count
    loaded = Profile()
    loaded.from_xml(path)
    loaded.to_xml(path)  # loaded and saved as it was
    settle_history()
    assert len(history.entries("profile")) == count


def test_s16_a_setting_appearing_is_not_a_change(
    store: Path, cfg: config.Configuration
) -> None:
    _keep_days(cfg)
    cfg.save_now()
    cfg.register(
        "global", "final08", "new-option", PropertyType.Int, 5, "",
        {"min": 0, "max": 100}, True,
    )
    cfg.save_now()
    settle_history()
    assert history.entries("settings") == []


def test_s16_changes_within_a_second_make_one_entry(
    store: Path, cfg: config.Configuration
) -> None:
    _keep_days(cfg)
    cfg.register(
        "global", "final08", "other-option", PropertyType.Int, 5, "",
        {"min": 0, "max": 100}, True,
    )
    cfg.save_now()
    cfg.set("global", "history", "keep-days", 30)
    cfg.set("global", "final08", "other-option", 6)
    # One write waits (about a second after the last change).
    assert deferred_write.pending("configuration")
    deferred_write.flush("configuration")
    settle_history()
    found = history.entries("settings")
    assert len(found) == 1
    assert sorted(found[0]["subject"]["keys"]) == [
        "global/final08/other-option",
        "global/history/keep-days",
    ]


# --- History: store, limits ---------------------------------------------------


def test_s19_the_clean_up_runs_at_the_first_entry_of_a_session(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = _entry("settings", "save", "Changed Old", clock.now() - 400 * 86400)
    _write_entries(store, "settings", [old])
    monkeypatch.setattr(history, "_pruned", False)
    history.record("settings", "Changed New", {}, 1, 2)
    settle_history()
    titles = [e["title"] for e in history.entries("settings")]
    assert titles == ["Changed New"]
    assert history._pruned


@pytest.fixture
def history_option(
    cfg: config.Configuration, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict]:
    """Options > Folders > History folder, set by the test (History's
    folder found through it, as the program does)."""
    settle_history()
    monkeypatch.setattr(history, "_pruned", True)
    key = ("global", "files", "history-folder")
    if not cfg.exists(*key):
        cfg.register(*key, PropertyType.Path, "", "", {"is_folder": True}, True)
    yield cfg._data[key]
    settle_history()


def test_s26_the_history_folder_follows_the_option(
    history_option: dict, tmp_path: Path
) -> None:
    chosen = tmp_path / "my history"
    history_option["value"] = str(chosen)
    assert util.history_dir() == chosen.resolve()
    assert history.folder() == chosen.resolve()
    history.record("settings", "Changed Something", {}, 1, 2)
    settle_history()
    assert (chosen / "settings.jsonl").is_file()


def test_s27_after_a_move_old_entries_stay_in_the_old_folder(
    history_option: dict, tmp_path: Path
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    history_option["value"] = str(first)
    old = history.record("settings", "Changed Before", {}, 1, 2)
    settle_history()
    history_option["value"] = str(second)
    new = history.record("settings", "Changed After", {}, 2, 3)
    settle_history()
    shown = [e["id"] for e in history.entries()]
    assert new in shown and old not in shown
    assert old in (first / "settings.jsonl").read_text(encoding="utf-8")


# --- History window ------------------------------------------------------------


def test_s28_every_change_newest_first_with_title_date_and_area(store: Path) -> None:
    now = clock.now()
    _write_entries(
        store, "settings", [_entry("settings", "save", "Changed A", now - 30)]
    )
    _write_entries(
        store, "modules", [_entry("modules", "save", "Saved B: calibration", now - 10)]
    )
    _write_entries(
        store, "profile", [_entry("profile", "profile", "Saved c.xml", now - 20)]
    )
    model = history_model.HistoryModel()
    model.reload()
    assert model.rowCount() == 3
    assert [_role(model, r, "title") for r in range(3)] == [
        "Saved B: calibration",
        "Saved c.xml",
        "Changed A",
    ]
    assert [_role(model, r, "areaName") for r in range(3)] == [
        "Module files",
        "Profile",
        "Settings",
    ]
    assert all(_role(model, r, "when") for r in range(3))


def test_s35_refresh_shows_new_changes(store: Path) -> None:
    model = history_model.HistoryModel()
    model.reload()
    assert model.rowCount() == 0
    history.record("settings", "Changed Something", {}, 1, 2)
    model.reload()  # Refresh, or the window coming to the front
    assert model.rowCount() == 1


# --- Restore -------------------------------------------------------------------


def test_s39_a_module_file_restore_is_a_new_entry(folder: Path) -> None:
    from gremlin.modules import module_file

    path = write_module(folder, "pjoy_pro", stick_doc())
    module_file.write_json(path, stick_doc(calibration={"1": [0, 1, 2, 3, True]}))
    settle_history()
    saved = history.entries("modules")[0]
    count = len(history.entries())
    result = history_model.restore(saved["id"], "before")
    assert result["ok"], result
    settle_history()
    found = history.entries()
    assert len(found) == count + 1
    assert found[0]["area"] == "modules"


def test_s39_a_settings_restore_is_a_new_entry(
    store: Path, cfg: config.Configuration
) -> None:
    _keep_days(cfg)
    cfg.set("global", "history", "keep-days", 30)
    cfg._history_view = cfg._settings_view()
    entry_id = history.record(
        "settings", "Changed Days to keep changes",
        {"keys": ["global/history/keep-days"]},
        {"global/history/keep-days": "90"}, {"global/history/keep-days": "30"},
    )
    settle_history()
    assert history_model.restore(entry_id, "before")["ok"]
    deferred_write.flush("configuration")  # the settings save, a second later
    settle_history()
    newest = history.entries("settings")[0]
    assert newest["id"] != entry_id
    assert newest["after"] == {"global/history/keep-days": "90"}


def test_s41_an_input_restore_that_cant_be_read_changes_nothing(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "p.xml"
    profile = new_profile(monkeypatch, path)
    map_button(profile, stick_uid(), 1, 1)
    profile.to_xml(path)
    before = profile._xml_text()
    entry_id = history.record(
        "profile",
        "Changed the actions of pJoy Pro Button 1 in Default",
        {
            "profile": str(path),
            "profileName": path.name,
            "deviceId": stick_guid(),
            "device": "pJoy Pro",
            "inputType": "button",
            "inputId": "1",
            "mode": "Default",
        },
        None,
        {"input": "<input broken", "actions": ["<action"]},
        kind="input",
    )
    settle_history()
    result = history_model.restore(entry_id, "after")
    assert not result["ok"]
    assert mapped(profile, stick_uid()) == {("Default", 1)}
    assert profile._xml_text() == before


def test_s46_a_part_of_the_profile_cant_be_restored_on_its_own(store: Path) -> None:
    entry = _entry(
        "profile", "section", "Changed the modes", clock.now(),
        subject={"section": "modes"}, before="<modes/>", after="<modes><m/></modes>",
    )
    _write_entries(store, "profile", [entry])
    shown = history_model.describe(entry)
    assert not shown["canRestoreBefore"] and not shown["canRestoreAfter"]
    assert "Restore on the profile's save" in shown["note"]
    assert not history_model.restore(entry["id"], "before")["ok"]


def test_s47_a_version_no_longer_kept_says_so(store: Path, tmp_path: Path) -> None:
    entry = _entry(
        "profile", "profile", "Saved p.xml", clock.now(),
        subject={"profile": str(tmp_path / "p.xml")},
        before=None, after={"packed": history_profile.pack_text("<profile/>")},
    )
    _write_entries(store, "profile", [entry])
    shown = history_model.describe(entry)
    assert shown["before"] == "Not kept." and not shown["canRestoreBefore"]
    result = history_model.restore(entry["id"], "before")
    assert result == {"ok": False, "message": "That version can't be put back."}
    gone = history_model.restore(uuid.uuid4().hex, "after")
    assert gone == {
        "ok": False,
        "message": "That change isn't in the history any more.",
    }
    assert list(tmp_path.glob("p (history*")) == []


def test_s48_created_has_no_before_and_deleted_no_after(store: Path) -> None:
    created = _entry(
        "modules", "save", "Created the module file of X", clock.now(),
        before=None, after={"text": "{}", "pictures": []},
    )
    deleted = _entry(
        "modules", "delete", "Deleted the module file of X", clock.now(),
        before={"text": "{}", "pictures": []}, after=None,
    )
    _write_entries(store, "modules", [created, deleted])
    made, gone = history_model.describe(created), history_model.describe(deleted)
    assert not made["canRestoreBefore"] and made["canRestoreAfter"]
    assert gone["canRestoreBefore"] and not gone["canRestoreAfter"]
    assert not history_model.restore(created["id"], "before")["ok"]
    assert not history_model.restore(deleted["id"], "after")["ok"]


# --- Device Pack: export --------------------------------------------------------


def test_s49_s55_a_pack_holds_the_file_pictures_wires_and_outputs(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gremlin.util import get_code_version

    (folder / "pjoy_pro").mkdir()
    (folder / "pjoy_pro" / "photo.png").write_bytes(b"a photo")
    write_module(folder, "pjoy_pro", stick_doc(image="pjoy_pro/photo.png"))
    write_module(folder, "vjoy_1", vjoy_doc())
    profile = new_profile(monkeypatch)
    profile.modes.add_mode("Combat")
    profile.modes.set_parent("Combat", "Default")
    map_button(profile, stick_uid(), 1, 1)
    map_button(profile, stick_uid(), 2, 2, "Combat")
    hw = hardware_profile.HardwareProfile()
    done = json.loads(hw.exportPack("pJoy Pro", _url(tmp_path / "p.zip"), "{}"))
    assert done["ok"], done
    with zipfile.ZipFile(tmp_path / "p.zip") as zf:
        names = set(zf.namelist())
        doc = json.loads(zf.read("map.json"))
        wires = json.loads(zf.read("wires.json"))
    assert {"map.json", "wires.json", "photo.png"} <= names
    assert any(n.startswith("outputs/") for n in names), names
    assert doc["claim"]["buttons"] == [1, 2]
    assert sorted(m["name"] for m in wires["modes"]) == ["Combat", "Default"]
    assert wires["actions"]
    # S55: format, program version, date, each mode's parent.
    label = doc["pack"]
    assert label["format"] == 2
    assert label["program"] == get_code_version()
    assert label["exportedOn"] == date.today().isoformat()
    assert wires["tree"] == {"Default": "", "Combat": "Default"}


def test_s50_the_device_list_holds_connected_seen_and_saved_devices(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(
        folder,
        "saved_only",
        {"kind": "control.hardware", "device": "Saved Only", "direction": "source"},
    )
    new_profile(monkeypatch)  # has seen "Gone Stick"
    hw = hardware_profile.HardwareProfile()
    rows = {r["name"]: r for r in json.loads(hw.packDevices())["devices"]}
    assert rows["pJoy Pro"]["connected"] and not rows["pJoy Pro"]["hasFile"]
    assert "Gone Stick" in rows and not rows["Gone Stick"]["connected"]
    assert rows["Saved Only"]["hasFile"]


# --- Device Pack: import --------------------------------------------------------


def test_s62_the_pack_suggests_the_device_of_its_name(
    folder: Path, tmp_path: Path
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    pack = _write_zip(
        tmp_path / "p.zip",
        {"map.json": _pack_map(pack={"exportedName": "pjoy  PRO", "format": 2})},
    )
    described = device_pack.describe_zip(pack)
    assert not isinstance(described, str), described
    assert described["suggestedName"] == "pJoy Pro"


def test_s63_a_stick_pack_cant_go_on_a_vjoy_nor_the_other_way(
    folder: Path, tmp_path: Path
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    write_module(folder, "vjoy_1", vjoy_doc())
    stick = _write_zip(tmp_path / "stick.zip", {"map.json": _pack_map()})
    onto_vjoy = device_pack.apply_zip(stick, "vJoy 1", {"items": ["in.checks"]})
    assert onto_vjoy == {
        "ok": False,
        "error": "A stick pack cannot be copied onto a vJoy.",
    }
    vjoy = _write_zip(
        tmp_path / "vjoy.zip",
        {"map.json": vjoy_doc(pack={"exportedName": "vJoy 1", "format": 2})},
    )
    onto_stick = device_pack.apply_zip(vjoy, "pJoy Pro", {"items": ["in.checks"]})
    assert onto_stick == {
        "ok": False,
        "error": "A vJoy pack cannot be copied onto a stick.",
    }
    claims = json.loads((folder / "vjoy_1.json").read_text(encoding="utf-8"))["claim"]
    assert claims == vjoy_doc()["claim"]


def test_s65_q3_checked_controls_are_added(folder: Path, tmp_path: Path) -> None:
    path = write_module(folder, "pjoy_pro", stick_doc())  # buttons 1, 2
    pack = _write_zip(tmp_path / "p.zip", {"map.json": _pack_map()})  # button 5
    result = device_pack.apply_zip(pack, "pJoy Pro", {"items": ["in.checks"]})
    assert result["ok"], result
    claim = json.loads(path.read_text(encoding="utf-8"))["claim"]
    assert claim["buttons"] == [1, 2, 5]


def test_s66_controls_the_device_doesnt_have_are_left_out_and_said() -> None:
    merged, notes = device_pack._merge_module(
        {"claim": {"buttons": [1], "axes": [], "hats": [], "keys": []}},
        {"claim": {"buttons": [1, 2, 40], "axes": [9], "hats": []}},
        {"in.checks"},
        "in.",
        "Small Stick",
        "",
        {"button": {1, 2}, "axis": {1}, "hat": set()},
    )
    assert merged["claim"]["buttons"] == [1, 2]
    assert merged["claim"]["axes"] == []
    assert (
        "Left out controls Small Stick doesn't have: Button 40, Axis 9." in notes
    )


def test_s67_names_are_written_only_for_checked_controls() -> None:
    merged, notes = device_pack._merge_module(
        {"claim": {"buttons": [1], "axes": [], "hats": [], "keys": []}},
        {"claim": {"friendly": {"button:1": "Fire", "button:9": "Gear"}}},
        {"in.names"},
        "in.",
        "Some Stick",
        "",
    )
    assert merged["claim"]["friendly"] == {"button:1": "Fire"}
    assert "Names for controls that are not checked were left out." in notes


def test_s73_the_previous_file_and_an_overwritten_picture_are_kept_in_imported(
    folder: Path, tmp_path: Path
) -> None:
    (folder / "pjoy_pro").mkdir()
    (folder / "pjoy_pro" / "photo.png").write_bytes(b"old photo")
    path = write_module(folder, "pjoy_pro", stick_doc(image="pjoy_pro/photo.png"))
    before = path.read_bytes()
    pack = _write_zip(
        tmp_path / "p.zip",
        {"map.json": _pack_map(image="photo.png"), "photo.png": "new photo"},
    )
    result = device_pack.apply_zip(
        pack, "pJoy Pro", {"items": ["in.checks", "pic:photo.png"]}
    )
    assert result["ok"], result
    imported = folder / "imported"
    backups = list(imported.glob("pjoy_pro.*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == before
    # A dated name: pjoy_pro.<year>-<day>-<MON>_<h>_<m>_<s>.json
    assert backups[0].name.split(".")[1][:4].isdigit()
    assert f"imported\\{backups[0].name}" in result["report"]
    pictures = list(imported.glob("pjoy_pro_photo.*.png"))
    assert len(pictures) == 1 and pictures[0].read_bytes() == b"old photo"
    assert (folder / "pjoy_pro" / "photo.png").read_bytes() == b"new photo"


# Wires to Logical Device button 7, which is missing and not created (08 S64)
@pytest.mark.validate_off
def test_s74_the_profile_changes_in_memory_only(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    pack = _pack_with_wires(monkeypatch, tmp_path)
    path = tmp_path / "target.xml"
    target = new_profile(monkeypatch, path)
    map_button(target, stick_uid(), 3, 3)
    target.to_xml(path)
    on_disk = path.read_bytes()
    result = device_pack.apply_zip(pack, "pJoy Pro", {"items": ["wire:Default"]})
    assert result["ok"], result
    assert ("Default", 1) in mapped(target, stick_uid())
    assert path.read_bytes() == on_disk
    assert target.has_unsaved_changes()


# Wires to Logical Device button 7, which is missing and not created (08 S64)
@pytest.mark.validate_off
def test_s81_keeping_the_import_ends_undo_and_drops_the_replaced_actions(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    pack = _pack_with_wires(monkeypatch, tmp_path)
    target = new_profile(monkeypatch)
    map_button(target, stick_uid(), 3, 3)
    hw = hardware_profile.HardwareProfile()
    result = json.loads(
        hw.importPack(_url(pack), "pJoy Pro", json.dumps({"items": ["wire:Default"]}))
    )
    assert result["ok"], result
    assert hw.canUndoPackImport()
    hw.keepPackImport()  # the next import, another pack opened, or closing
    assert not hw.canUndoPackImport()
    assert set(target.library._actions) == target.actions_in_use()
    assert ("Default", 3) not in mapped(target, stick_uid())


# --- Auto Mapper ----------------------------------------------------------------


def _auto_map_cards(folder: Path) -> None:
    write_module(
        folder,
        "pjoy_pro",
        stick_doc(claim={"buttons": [1, 2], "axes": [], "hats": [], "keys": []}),
    )
    write_module(
        folder, "vjoy_1", vjoy_doc(claim={"buttons": [1, 2], "axes": [], "hats": []})
    )


def test_s90_actions_go_in_the_chosen_mode(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _auto_map_cards(folder)
    profile = new_profile(monkeypatch)
    profile.modes.add_mode("Combat")
    AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions(mode="Combat")
    )
    assert mapped(profile, stick_uid()) == {("Combat", 1), ("Combat", 2)}


def test_s96_the_overwrite_choice_is_remembered(
    folder: Path, cfg: config.Configuration, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import shell_option, tools

    shell_option.ensure_shell_options()
    cfg.set("automap", "mapper", "remember-overwrite", True)
    cfg.set("automap", "mapper", "overwrite-used-inputs", False)
    _auto_map_cards(folder)
    new_profile(monkeypatch)
    window = tools.Tools()
    window.createMappings("Default", {"pjoy_pro": True}, {"vjoy_1": True}, True, False)
    assert window.lastOverwriteUsedInputs() is True
    window.createMappings("Default", {"pjoy_pro": True}, {"vjoy_1": True}, False, False)
    assert window.lastOverwriteUsedInputs() is False


def test_s97_the_new_actions_are_in_memory_only(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _auto_map_cards(folder)
    path = tmp_path / "p.xml"
    profile = new_profile(monkeypatch, path)
    profile.to_xml(path)
    on_disk = path.read_bytes()
    AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions()
    )
    assert mapped(profile, stick_uid()) == {("Default", 1), ("Default", 2)}
    assert path.read_bytes() == on_disk
    assert profile.has_unsaved_changes()
    # Undo: load the profile again without saving.
    again = Profile()
    again.from_xml(path)
    assert mapped(again, stick_uid()) == set()


def test_s99_only_vjoy_outputs(folder: Path) -> None:
    setup_cards(folder)  # outputs vJoy 1 and Xbox; inputs Keyboard and OSC too
    outputs = auto_map.output_modules()
    assert outputs
    assert all(int(row["vjoyId"]) > 0 for row in outputs), outputs
    names = {str(row.get("name") or row.get("device") or "") for row in outputs}
    assert not any(
        word in name for name in names for word in ("Xbox", "Keyboard", "OSC")
    ), names

