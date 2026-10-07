# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stage 1 safety net: History, Device Pack and the Auto Mapper (page 08).

Covers gap-list section 1 items GL-022 (History: entries read while the
writer runs, the first save's pictures, Save As, restore into a deleted
mode, a setting that no longer exists, Show, Search and the editors'
filters: 08 S7, S23, S29, S31, S42, S44), GL-023 (Device Pack: exportPack's
checks, import onto a damaged file, a wire import failing partway, Undo
Import after a later save or with another profile open, vJoy sizes, a bad
wires.json or output file, an empty selection: 08 S57, S78, S79, S83, Q5,
Q18), GL-024 (Delete Device's "Save a copy" pack: written, read back,
refused, imported back: 08 S86, S89) and GL-025 (Auto Mapper: Combine with
more inputs than outputs, Overwrite with nested actions, twin sticks, Also
claim with an output file that can't be written: 08 S91, S93, S95, Q7, Q9).

Tests that pass lock in today's behaviour where it matches the spec. Known
gaps are strict xfails named by their gap-list id, so each flips when it is
fixed: GL-031, GL-072, GL-082, GL-099, GL-143, GL-187, GL-188, GL-189,
GL-191, GL-194.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import (
    config,
    device_initialization,
    history,
    plugin_manager,
    shared_state,
)
from gremlin.auto_mapper import AutoMapper, AutoMapperOptions
from gremlin.modules import module_file
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType, PropertyType
from gremlin.ui import device_pack, hardware_profile, history_model, module_model
from test.unit import test_stage1_modules, test_twin_devices
from test.unit.test_stage1_modules import (
    _OTHER,
    map_button,
    mapped,
    settle_history,
    stick_doc,
    stick_guid,
    stick_uid,
    vjoy_doc,
    write_module,
)
from test.unit.test_twin_devices import _first_guid, _twin_guid

# The shared fixtures: Qt's application, the modules folder, twin sticks.
_app = test_stage1_modules._app
folder = test_stage1_modules.folder
twins = test_twin_devices.twins

_ROOT = Path(__file__).resolve().parents[2]


def _url(path: Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def new_profile(monkeypatch: pytest.MonkeyPatch, path: Path | None = None) -> Profile:
    """A new profile, open as the current one (put back afterwards)."""
    profile = Profile()
    profile.device_database.devices[stick_uid()] = DeviceInfo(stick_uid(), "pJoy Pro")
    profile.device_database.devices[_OTHER] = DeviceInfo(_OTHER, "Gone Stick")
    if path is not None:
        profile.fpath = path
    monkeypatch.setattr(shared_state, "current_profile", profile)
    return profile


def nested_map(profile: Profile, uid: uuid.UUID, button: int, out: int) -> None:
    """Button -> Tempo -> Map to vJoy (vJoy 1, button out)."""
    manager = plugin_manager.PluginManager()
    action = manager.create_instance("Map to vJoy", InputType.JoystickButton)
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    tempo = manager.create_instance("Tempo", InputType.JoystickButton)
    tempo.insert_action(action, "short")
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    assert item is not None
    root = item.add_item_binding().root_action
    assert root is not None
    root.insert_action(tempo, "children")


def vjoy_targets(profile: Profile) -> list[tuple[int, int]]:
    """(vJoy, button) of every Map to vJoy in the profile, nested ones too."""
    found = []
    for action in profile.library._actions.values():
        if getattr(action, "tag", "") == "map-to-vjoy":
            found.append(
                (getattr(action, "vjoy_device_id"), getattr(action, "vjoy_input_id"))
            )
    return sorted(found)


# --- GL-022: History -------------------------------------------------------------


def test_reading_history_while_the_writer_works_keeps_its_work_on_the_writer(
    folder: Path,
) -> None:
    started, release = threading.Event(), threading.Event()
    ran_on: list[str] = []

    def slow() -> None:
        started.set()
        release.wait(10.0)

    def compare() -> None:
        ran_on.append(threading.current_thread().name)
        history.write_now("settings", "Changed an option", {}, 1, 2)

    history.later(slow)
    assert started.wait(10.0)
    history.later(compare)
    try:
        history.entries()  # the History window opening (UI thread)
    finally:
        release.set()
    settle_history()
    # S23: comparing and picture copies run on the History thread.
    assert ran_on and ran_on[0].endswith("History")


def test_a_saves_before_picture_is_the_picture_it_had(folder: Path) -> None:
    (folder / "pjoy_pro").mkdir()
    photo = folder / "pjoy_pro" / "photo.png"
    photo.write_bytes(b"old photo")
    path = write_module(folder, "pjoy_pro", stick_doc(image="pjoy_pro/photo.png"))
    started, release = threading.Event(), threading.Event()

    def busy() -> None:
        started.set()
        release.wait(10.0)

    history.later(busy)  # the writer is busy with an earlier save
    assert started.wait(10.0)
    try:
        doc = stick_doc(
            image="pjoy_pro/photo.png", calibration={"1": [0, 1, 2, 3, True]}
        )
        module_file.write_json(path, doc)
        photo.write_bytes(b"new photo")  # the next save's picture
    finally:
        release.set()
    settle_history()
    entry = history.entries("modules")[0]
    assert entry["title"] == "Saved pJoy Pro: calibration"
    # S8: the file before the save, with the pictures it had.
    kept = history.kept_file(entry["before"]["pictures"][0]["keptFile"])
    assert kept is not None and kept.read_bytes() == b"old photo"


def test_save_as_is_recorded_under_the_new_file(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile = new_profile(monkeypatch)
    first, second = tmp_path / "first.xml", tmp_path / "second.xml"
    map_button(profile, stick_uid(), 1, 1)
    profile.to_xml(first)
    first_text = profile._saved_snapshot
    map_button(profile, stick_uid(), 2, 2)
    profile.to_xml(second)  # File > Save As
    settle_history()
    save = next(
        e
        for e in history.entries("profile")
        if e["kind"] == "profile" and e["subject"]["profile"] == str(second)
    )
    # S7: under the new file, with the old file's text as "before".
    from gremlin import history_profile

    assert save["title"].startswith("Saved second.xml")
    assert history_profile.unpack_text(save["before"]["packed"]) == first_text


def test_an_input_restore_into_a_deleted_mode_is_refused(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "p.xml"
    profile = new_profile(monkeypatch, path)
    profile.modes.add_mode("Combat")
    map_button(profile, stick_uid(), 1, 1, "Combat")
    profile.to_xml(path)
    map_button(profile, stick_uid(), 2, 2)
    profile.to_xml(path)
    settle_history()
    entry = next(
        e
        for e in history.entries("profile")
        if e["kind"] == "input" and e["subject"]["mode"] == "Combat"
    )
    profile.modes.delete_mode("Combat")
    before = profile._xml_text()
    result = history_model.restore(entry["id"], "after")
    # S42: refused with its reason, nothing changed.
    assert not result["ok"]
    assert "Combat" in result["message"]
    assert profile._xml_text() == before


def test_a_setting_that_no_longer_exists_is_skipped(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    cfg = config.Configuration()
    # The settings are one shared object: put its entries back afterwards
    # (a registration here has no description).
    monkeypatch.setattr(cfg, "_data", {k: dict(v) for k, v in cfg._data.items()})
    cfg.register(
        "global",
        "history",
        "keep-days",
        PropertyType.Int,
        90,
        "",
        {"min": 1, "max": 3650},
        True,
    )
    cfg.set("global", "history", "keep-days", 30)
    entry_id = history.record(
        "settings",
        "Changed Keep days",
        {"keys": ["global/history/keep-days", "global/gone/old-option"]},
        {"global/history/keep-days": "90", "global/gone/old-option": "1"},
        {"global/history/keep-days": "30", "global/gone/old-option": "2"},
    )
    settle_history()
    result = history_model.restore(entry_id, "before")
    # S44: put back at once; a setting the program no longer has is skipped.
    assert result["ok"], result
    assert cfg.value("global", "history", "keep-days") == 90
    assert not cfg.exists("global", "gone", "old-option")


def _subject(**parts: object) -> dict:
    return dict(parts)


@pytest.fixture
def entries(folder: Path, tmp_path: Path) -> dict[str, str]:
    """One entry of each kind the editors filter on."""
    stick = stick_guid().strip("{}").lower()
    made = {
        "input": history.record(
            "profile",
            "Changed the actions of pJoy Pro Button 3 in Default",
            _subject(
                profile=str(tmp_path / "a.xml"),
                profileName="a.xml",
                deviceId=stick,
                device="pJoy Pro",
                inputType="button",
                inputId="3",
                mode="Default",
            ),
            None,
            None,
            kind="input",
        ),
        "other profile": history.record(
            "profile",
            "Changed the actions of pJoy Pro Button 3 in Default",
            _subject(
                profile=str(tmp_path / "b.xml"),
                profileName="b.xml",
                deviceId=stick,
                device="pJoy Pro",
                inputType="button",
                inputId="3",
                mode="Default",
            ),
            None,
            None,
            kind="input",
        ),
        "logical": history.record(
            "profile",
            "Changed the actions of Logical Device Button 3 in Default",
            _subject(
                profile=str(tmp_path / "a.xml"),
                device="Logical Device",
                inputType="button",
                inputId="3",
                mode="Default",
            ),
            None,
            None,
            kind="input",
        ),
        "checks": history.record(
            "modules",
            "Saved pJoy Pro: checked controls and names",
            _subject(device="pJoy Pro", fileName="pjoy_pro.json"),
            None,
            None,
        ),
        "map": history.record(
            "button-map",
            "Saved pJoy Pro: Button Map",
            _subject(device="pJoy Pro", fileName="pjoy_pro.json"),
            None,
            None,
        ),
        "twin": history.record(
            "button-map",
            "Saved pJoy Pro: Button Map",
            _subject(device="pJoy Pro", fileName="pjoy_pro_2.json"),
            None,
            None,
        ),
        "settings": history.record(
            "settings",
            "Changed Days to keep changes",
            _subject(keys=[]),
            None,
            None,
        ),
    }
    settle_history()
    return {value: key for key, value in made.items()}


def _shown(model: history_model.HistoryModel, names: dict[str, str]) -> set[str]:
    role = QtCore.Qt.ItemDataRole.UserRole + 1
    ids = [
        str(model.data(model.index(row, 0), role)) for row in range(model.rowCount())
    ]
    # Only this test's entries (a settings change can add one of its own).
    return {names[entry_id] for entry_id in ids if entry_id in names}


def test_show_and_search(entries: dict[str, str]) -> None:
    model = history_model.HistoryModel()
    model.reload()
    assert _shown(model, entries) == set(entries.values())
    # S29: Show narrows by area.
    model.setFilter(json.dumps({"area": "button-map"}))
    assert _shown(model, entries) == {"map", "twin"}
    model.setFilter(json.dumps({"area": "settings"}))  # Options' History
    assert _shown(model, entries) == {"settings"}
    model.setFilter("")
    # Search finds words in the title and in what it is about.
    model.setSearch("pjoy_pro_2")
    assert _shown(model, entries) == {"twin"}
    model.setSearch("logical button 3")
    assert _shown(model, entries) == {"logical"}
    model.setSearch("b.xml")
    assert _shown(model, entries) == {"other profile"}


def test_the_editors_filters(entries: dict[str, str]) -> None:
    model = history_model.HistoryModel()
    model.reload()
    # Module Setup and Calibration: the device's own file, every area (S31).
    model.setFilter(json.dumps({"fileName": "pjoy_pro.json"}))
    assert _shown(model, entries) == {"checks", "map"}
    # A Logical Device control.
    model.setFilter(
        json.dumps(
            {
                "device": "Logical Device",
                "inputType": "button",
                "inputId": "3",
                "mode": "Default",
            }
        )
    )
    assert _shown(model, entries) == {"logical"}
    # A Configuration row (by device id, however written: S32).
    model.setFilter(
        json.dumps(
            {
                "deviceId": "{" + stick_guid().upper() + "}",
                "inputType": "button",
                "inputId": "3",
                "mode": "Default",
            }
        )
    )
    assert "input" in _shown(model, entries)


def _qml_history_filter(file_name: str) -> str:
    """The filter an editor's History opens with (its JSON.stringify({...}))."""
    text = (_ROOT / "qml" / file_name).read_text(encoding="utf-8")
    start = text.index('"DialogHistory.qml"')
    found = re.search(r"JSON\.stringify\((\{.*?\})\)", text[start:], re.DOTALL)
    assert found, file_name
    return found.group(1)


@pytest.fixture(scope="module")
def opened_history(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The filters History opens with from the Button Map's File menu and a
    Configuration row, in the running program off-screen (its own process)."""
    from test.unit.test_stage1_button_map import (  # pyright: ignore[reportMissingImports]
        _run,
    )

    return _run("history", tmp_path_factory.mktemp("history_filters"))


def test_tools_history_opens_on_every_change() -> None:
    # S34.
    text = (_ROOT / "qml" / "main_commands.js").read_text(encoding="utf-8")
    assert 'openToolWith("DialogHistory.qml", { filter: "" })' in text
    assert "fileName" in _qml_history_filter("DialogConfigureModule.qml")
    assert "fileName" in _qml_history_filter("DialogCalibration.qml")


def test_button_map_history_is_by_its_own_file_in_every_area(
    opened_history: dict,
) -> None:
    # Q15: by the device's own module file name, all areas.
    found = opened_history["button-map-filter"]
    assert found.get("fileName") == opened_history["map-file"]
    assert not found.get("area")


def test_configuration_row_history_is_for_the_open_profile(
    opened_history: dict,
) -> None:
    # Q16: the open profile is part of the filter (the entries' "profile",
    # its path; a "profileName" alone would mix two profiles of one name).
    found = opened_history["row-filter"]
    assert "profile" in found
    assert Path(found["profile"]).resolve() == Path(
        opened_history["open-profile"]
    ).resolve()


# --- GL-023: Device Pack -----------------------------------------------------------


def test_export_pack_checks_the_place_and_the_name(
    folder: Path, tmp_path: Path
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    hw = hardware_profile.HardwareProfile()
    # S57: never inside the modules folder.
    inside = json.loads(hw.exportPack("pJoy Pro", _url(folder / "pack.zip"), "{}"))
    assert inside == {"ok": False, "error": "Save the pack outside the module folder."}
    assert not (folder / "pack.zip").exists()
    # A name without .zip gets .zip.
    done = json.loads(hw.exportPack("pJoy Pro", _url(tmp_path / "my pack"), "{}"))
    assert done["ok"], done
    assert done["path"] == str(tmp_path / "my pack.zip")
    with zipfile.ZipFile(tmp_path / "my pack.zip") as zf:
        doc = json.loads(zf.read("map.json"))
    # S56: not this machine's binding.
    assert "boundGuidLocal" not in doc and "boundName" not in doc
    # S51: a device without a module file can't be exported.
    none = json.loads(hw.exportPack("Gone Stick", _url(tmp_path / "x.zip"), "{}"))
    assert none == {"ok": False, "error": "This device has no module file yet."}


def _write_zip(path: Path, files: dict[str, object]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            text = content if isinstance(content, str) else json.dumps(content)
            zf.writestr(name, text)
    return path


def _pack_map(**extra: object) -> dict:
    return {
        "kind": "control.hardware",
        "device": "pJoy Pro",
        "direction": "source",
        "claim": {"buttons": [5], "axes": [], "hats": [], "keys": [], "friendly": {}},
        "catalog": {"rowHeight": 44},
        "pack": {"exportedName": "pJoy Pro", "format": 2},
        **extra,
    }


@pytest.mark.parametrize("bad", ["wires.json", "outputs/vjoy_2.json"])
def test_a_pack_with_a_bad_part_changes_nothing(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad: str
) -> None:
    path = write_module(folder, "pjoy_pro", stick_doc())
    before = path.read_bytes()
    profile = new_profile(monkeypatch)
    map_button(profile, stick_uid(), 1, 1)
    pack = _write_zip(tmp_path / "bad.zip", {"map.json": _pack_map(), bad: "{ half"})
    result = device_pack.apply_zip(pack, "pJoy Pro", {"items": ["in.checks"]})
    assert not result["ok"]
    assert path.read_bytes() == before
    assert mapped(profile, stick_uid()) == {("Default", 1)}
    assert not device_pack.can_undo_import()


def test_an_import_with_nothing_ticked_is_refused(folder: Path, tmp_path: Path) -> None:
    path = write_module(folder, "pjoy_pro", stick_doc())
    before = path.read_bytes()
    pack = _write_zip(tmp_path / "p.zip", {"map.json": _pack_map()})
    hw = hardware_profile.HardwareProfile()
    result = json.loads(
        hw.importPack(_url(pack), "pJoy Pro", json.dumps({"items": []}))
    )
    assert result == {"ok": False, "error": "Choose at least one piece to import."}
    assert path.read_bytes() == before


def test_a_pack_import_onto_a_damaged_module_file_is_refused(
    folder: Path, tmp_path: Path
) -> None:
    path = folder / "pjoy_pro.json"
    path.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    before = path.read_bytes()
    pack = _write_zip(tmp_path / "p.zip", {"map.json": _pack_map()})
    result = device_pack.apply_zip(pack, "pJoy Pro", {"items": ["in.checks"]})
    # Q2 / F1: refused, pointing to Start Fresh; the file stays as it is.
    assert not result["ok"]
    assert "Start Fresh" in result["error"]
    assert path.read_bytes() == before


def _pack_with_wires(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """pJoy Pro's pack from another PC: button 1 in Default, button 2 in
    Combat (a mode this profile lacks) and button 5 to Logical Device
    button 7 (an input this Logical Device lacks)."""
    source = new_profile(monkeypatch)
    source.modes.add_mode("Combat")
    map_button(source, stick_uid(), 1, 1)
    map_button(source, stick_uid(), 2, 2, "Combat")
    logical = plugin_manager.PluginManager().create_instance(
        "Map to Logical Device", InputType.JoystickButton
    )
    logical.logical_input_id = 7
    logical.logical_input_type = InputType.JoystickButton
    item = source.get_input_item(
        stick_uid(), InputType.JoystickButton, 5, "Default", create_if_missing=True
    )
    assert item is not None
    root = item.add_item_binding().root_action
    assert root is not None
    root.insert_action(logical, "children")
    built = device_pack.assemble("pJoy Pro", lambda stored: None)
    assert not isinstance(built, str), built
    pack = tmp_path / "wires.zip"
    pack.write_bytes(built[0])
    return pack


@pytest.fixture
def logical_seven() -> Iterator[object]:
    """Logical Device button 7, removed again if a test made it."""
    from gremlin.logical_device import LogicalDevice

    ident = LogicalDevice.Input.Identifier(InputType.JoystickButton, 7)
    assert not LogicalDevice().exists(ident)
    yield ident
    if LogicalDevice().exists(ident):
        LogicalDevice().delete(ident)


def test_a_wire_import_that_fails_partway_puts_everything_back(
    folder: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logical_seven: object,
) -> None:
    from gremlin.logical_device import LogicalDevice

    write_module(folder, "pjoy_pro", stick_doc())
    pack = _pack_with_wires(monkeypatch, tmp_path)
    target = new_profile(monkeypatch)
    map_button(target, stick_uid(), 3, 3)

    def fails(*_args: object, **_kwargs: object) -> list:
        raise RuntimeError("disk full")

    monkeypatch.setattr(target, "add_inputs", fails)
    device_pack.apply_zip(
        pack,
        "pJoy Pro",
        {"items": ["wire:Default", "wire:Combat"], "createLogical": True},
    )
    # S79 / Q20: undo everything it did.
    assert mapped(target, stick_uid()) == {("Default", 3)}
    assert not target.modes.mode_exists("Combat")
    assert not LogicalDevice().exists(logical_seven)


def test_undo_import_keeps_a_later_save(folder: Path, tmp_path: Path) -> None:
    path = write_module(folder, "pjoy_pro", stick_doc())
    pack = _write_zip(tmp_path / "p.zip", {"map.json": _pack_map()})
    assert device_pack.apply_zip(pack, "pJoy Pro", {"items": ["in.catalog"]})["ok"]
    later = json.loads(path.read_text(encoding="utf-8"))
    later["calibration"] = {"1": [-30000, -50, 50, 30000, True]}
    module_file.write_json(path, later)  # a later Module Setup or Calibration save
    device_pack.undo_import()
    # Q5: a file changed since the import is not put back without asking.
    assert json.loads(path.read_text(encoding="utf-8")).get("calibration")


def test_undo_import_with_another_profile_open_puts_back_only_the_files(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = write_module(folder, "pjoy_pro", stick_doc())
    pack = _pack_with_wires(monkeypatch, tmp_path)
    path.write_bytes(json.dumps(stick_doc()).encode("utf-8"))
    before = path.read_bytes()
    target = new_profile(monkeypatch)
    map_button(target, stick_uid(), 3, 3)
    result = device_pack.apply_zip(
        pack, "pJoy Pro", {"items": ["in.catalog", "wire:Default"]}
    )
    assert result["ok"], result
    imported = mapped(target, stick_uid())
    new_profile(monkeypatch)  # File > Load Profile of another profile
    undone = device_pack.undo_import()
    # S83: the files go back, the wires don't, and it says so.
    assert undone["ok"]
    assert (
        "Another profile is open now, so the wires were not put back."
        in undone["report"]
    )
    assert path.read_bytes() == before
    assert mapped(target, stick_uid()) == imported


def test_a_pack_output_module_keeps_to_the_vjoys_size(
    folder: Path, tmp_path: Path
) -> None:
    write_module(folder, "vjoy_1", vjoy_doc())
    output_doc = vjoy_doc(
        device="vJoy 9",
        claim={"buttons": [2, 99], "axes": [], "hats": []},
        pack={"exportedName": "vJoy 9", "slug": "vjoy_9"},
    )
    pack = _write_zip(
        tmp_path / "p.zip",
        {"map.json": _pack_map(), "outputs/vjoy_9.json": output_doc},
    )
    result = device_pack.apply_zip(
        pack,
        "pJoy Pro",
        {"items": ["out:vjoy_9.checks"], "outputs": {"vjoy_9": "vJoy 1"}},
    )
    assert result["ok"], result
    claim = json.loads((folder / "vjoy_1.json").read_text(encoding="utf-8"))["claim"]
    # Q18: vJoy 1 has 64 buttons; button 99 is left out and listed.
    assert 2 in claim["buttons"] and 99 not in claim["buttons"]
    assert "Button 99" in result["report"]


# --- GL-024: Delete Device's "Save a copy" pack ------------------------------------


def _stick_to_delete(folder: Path, monkeypatch: pytest.MonkeyPatch) -> Profile:
    write_module(folder, "pjoy_pro", stick_doc(image="pjoy_pro/photo.jpg"))
    (folder / "pjoy_pro").mkdir()
    (folder / "pjoy_pro" / "photo.jpg").write_bytes(b"\xff\xd8 a photo \xff\xd9")
    profile = new_profile(monkeypatch)
    profile.modes.add_mode("Combat")
    map_button(profile, stick_uid(), 1, 1)
    map_button(profile, stick_uid(), 2, 2, "Combat")
    return profile


def test_delete_device_saves_a_pack_that_can_be_imported_back(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile = _stick_to_delete(folder, monkeypatch)
    model = module_model.ModuleListModel()
    result = json.loads(model.deleteDevice("pJoy Pro", stick_guid(), True))
    assert result["ok"], result
    pack = Path(result["packPath"])
    # S86: the deleted devices folder, a folder per device name.
    assert pack.parent == tmp_path / "deleted devices" / "pJoy Pro"
    assert re.fullmatch(r"pJoy Pro\..+\.zip", pack.name)
    with zipfile.ZipFile(pack) as zf:
        names = zf.namelist()
        doc = json.loads(zf.read("map.json"))
    assert "wires.json" in names and "photo.jpg" in names
    assert doc["claim"]["buttons"] == [1, 2]
    assert not (folder / "pjoy_pro.json").exists()
    assert mapped(profile, stick_uid()) == set()

    # S89: Device Pack > Import puts it back (the pieces ticked by default).
    hw = hardware_profile.HardwareProfile()
    back = json.loads(hw.importPack(_url(pack), "pJoy Pro", ""))
    assert back["ok"], back
    restored = json.loads((folder / "pjoy_pro.json").read_text(encoding="utf-8"))
    assert restored["claim"]["buttons"] == [1, 2]
    assert (
        folder / "pjoy_pro" / "photo.jpg"
    ).read_bytes() == b"\xff\xd8 a photo \xff\xd9"
    assert mapped(profile, stick_uid()) == {("Default", 1), ("Combat", 2)}


def test_delete_device_is_refused_when_the_pack_cant_be_read_back(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile = _stick_to_delete(folder, monkeypatch)
    before = (folder / "pjoy_pro.json").read_bytes()
    monkeypatch.setattr(
        device_pack,
        "assemble",
        lambda *_a, **_k: (b"not a zip", {"device": "pJoy Pro"}),
    )
    result = json.loads(hardware_profile.delete_device("pJoy Pro", stick_guid(), True))
    # S86: if it can't be read back, nothing is deleted (and no bad pack stays).
    assert result == {
        "ok": False,
        "error": "The pack could not be read back, so the device was not deleted.",
    }
    assert (folder / "pjoy_pro.json").read_bytes() == before
    assert mapped(profile, stick_uid()) == {("Default", 1), ("Combat", 2)}
    assert not list((tmp_path / "deleted devices").rglob("*.zip"))


def test_delete_device_is_refused_when_the_pack_cant_be_written(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile = _stick_to_delete(folder, monkeypatch)
    blocked = tmp_path / "a folder where the pack would go"
    blocked.mkdir()
    monkeypatch.setattr(hardware_profile, "_deleted_pack_path", lambda name: blocked)
    result = json.loads(hardware_profile.delete_device("pJoy Pro", stick_guid(), True))
    assert not result["ok"]
    assert result["error"].startswith("The pack could not be written.")
    assert (folder / "pjoy_pro.json").is_file()
    assert mapped(profile, stick_uid()) == {("Default", 1), ("Combat", 2)}


def test_save_a_copy_needs_a_module_file(folder: Path) -> None:
    result = json.loads(hardware_profile.delete_device("pJoy Pro", stick_guid(), True))
    assert result == {
        "ok": False,
        "error": "This device has no module file, so a pack cannot be saved.",
    }


# --- GL-025: Auto Mapper -------------------------------------------------------------


def _auto_map_setup(folder: Path, buttons: list[int], outputs: list[int]) -> None:
    write_module(
        folder,
        "pjoy_pro",
        stick_doc(claim={"buttons": buttons, "axes": [], "hats": [], "keys": []}),
    )
    write_module(
        folder, "vjoy_1", vjoy_doc(claim={"buttons": outputs, "axes": [], "hats": []})
    )


def test_combine_with_more_inputs_than_outputs_uses_each_output_once(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _auto_map_setup(folder, [1, 2, 3], [1, 2, 3, 4, 5])
    write_module(
        folder,
        "gone_stick",
        {
            "kind": "control.hardware",
            "device": "Gone Stick",
            "direction": "source",
            "boundGuidLocal": str(_OTHER),
            "claim": {"buttons": [1, 2, 3], "axes": [], "hats": []},
        },
    )
    profile = new_profile(monkeypatch)
    report = AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro", "gone_stick"],
        ["vjoy_1"],
        AutoMapperOptions(repeat_vjoy_inputs=True),
    )
    # S91: both input modules go onto the one output, in turn; S94: an
    # output another input already uses in that mode is not used again.
    assert "No output module left" not in report
    assert vjoy_targets(profile) == [(1, 1), (1, 2), (1, 3)]
    assert len(mapped(profile, stick_uid()) | mapped(profile, _OTHER)) == 3


def test_without_combine_the_extra_input_module_is_named(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _auto_map_setup(folder, [1], [1])
    write_module(
        folder,
        "gone_stick",
        {
            "kind": "control.hardware",
            "device": "Gone Stick",
            "direction": "source",
            "boundGuidLocal": str(_OTHER),
            "claim": {"buttons": [1], "axes": [], "hats": []},
        },
    )
    profile = new_profile(monkeypatch)
    report = AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro", "gone_stick"], ["vjoy_1"], AutoMapperOptions()
    )
    assert "No output module left for pJoy Pro" in report
    assert mapped(profile, stick_uid()) == set()
    assert mapped(profile, _OTHER) == {("Default", 1)}


def test_overwrite_removes_nested_actions_and_leaves_nothing_behind(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _auto_map_setup(folder, [1], [1])
    profile = new_profile(monkeypatch)
    nested_map(profile, stick_uid(), 1, 7)
    AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions(overwrite_used_inputs=True)
    )
    # S95: every action on the input goes, nested ones too, none left behind.
    assert vjoy_targets(profile) == [(1, 1)]
    assert not [a for a in profile.library._actions.values() if a.tag == "tempo"]
    assert set(profile.library._actions) == profile.actions_in_use()


def test_an_output_a_nested_action_uses_is_not_used_again(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _auto_map_setup(folder, [1], [1])
    profile = new_profile(monkeypatch)
    nested_map(profile, stick_uid(), 9, 1)  # button 9 -> Tempo -> vJoy 1 button 1
    AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions()
    )
    # Q7: nested actions count; vJoy 1 button 1 isn't sent to twice.
    assert vjoy_targets(profile) == [(1, 1)]


def test_an_output_an_unplugged_stick_uses_is_not_used_again(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _auto_map_setup(folder, [2], [2])
    profile = new_profile(monkeypatch)
    map_button(profile, _OTHER, 5, 2)  # the unplugged stick -> vJoy 1 button 2
    AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions()
    )
    # Q7 (S98 replaced): every input in the profile counts.
    assert vjoy_targets(profile) == [(1, 2)]


def test_each_twin_stick_is_mapped_on_its_own_device(
    folder: Path,
    monkeypatch: pytest.MonkeyPatch,
    twins: list,
) -> None:
    import dill

    twin_uid = dill.GUID.from_str(_twin_guid()).uuid
    first_uid = dill.GUID.from_str(_first_guid()).uuid
    write_module(
        folder,
        "pjoy_pro",
        {
            "kind": "control.hardware",
            "device": "pJoy Pro",
            "direction": "source",
            "boundGuidLocal": _first_guid(),
            "claim": {"buttons": [1], "axes": [], "hats": []},
        },
    )
    write_module(
        folder,
        "pjoy_pro_2",
        {
            "kind": "control.hardware",
            "device": "pJoy Pro (2)",
            "direction": "source",
            "claim": {"buttons": [2], "axes": [], "hats": []},
        },
    )
    write_module(
        folder, "vjoy_1", vjoy_doc(claim={"buttons": [1, 2], "axes": [], "hats": []})
    )
    device_initialization.joystick_devices_initialization()
    names = {
        d.device_guid.uuid: d.name for d in device_initialization.physical_devices()
    }
    assert names[first_uid] == "pJoy Pro"
    assert names[twin_uid] == "pJoy Pro (2)"
    profile = new_profile(monkeypatch)
    AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro", "pjoy_pro_2"],
        ["vjoy_1"],
        AutoMapperOptions(repeat_vjoy_inputs=True),
    )
    # Each twin's module maps its own device (S6, S119).
    assert mapped(profile, first_uid) == {("Default", 1)}
    assert mapped(profile, twin_uid) == {("Default", 2)}


def test_also_claim_with_an_output_file_that_cant_be_written(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _auto_map_setup(folder, [1, 2], [])
    profile = new_profile(monkeypatch)
    real_write = module_file.write_bytes

    # The store writes every module file through write_bytes.
    def refuse(path: Path, data: bytes) -> None:
        if Path(path).name == "vjoy_1.json":
            raise OSError("access denied")
        real_write(path, data)

    monkeypatch.setattr(module_file, "write_bytes", refuse)
    report = AutoMapper(profile).generate_module_mappings(
        ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions(claim_outputs=True)
    )
    # S93 / Q9: no actions to outputs it couldn't claim; listed "not claimed".
    assert vjoy_targets(profile) == []
    assert "not claimed" in report
