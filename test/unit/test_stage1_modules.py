# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stage 1 safety net: input and output modules (page 03).

Covers gap-list section 1 items GL-010 (stacks, hide and unhide, compact
view, split mode: 03 S82, S84, S86), GL-011 (Delete Device edge paths:
03 S90-S97, Q4, Q5, Q6, Q18), GL-012 (import refusals, Import Image Cancel,
keepPhoto, Start Fresh History: 03 S57, S66, Q2, Q3, Q13, Q17), GL-013
(card counts and status after a settings change, the card menus, the Auto
Mapper's damaged output: 03 S34, S65, S78, S88, S120) and GL-014 (output.py
and the registry from several threads: 03 7.13, 7.14).

Tests that pass lock in today's behaviour where it matches the spec. Known
gaps are strict xfails named by their gap-list id, so each flips when it is
fixed: GL-245 (GL-038, GL-043, GL-138, GL-139, GL-140, GL-142, GL-143,
GL-146 and GL-147 were fixed in catch-up batch 2). GL-141 (suspected)
does not happen on the History Restore path: that is locked in instead.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast
from unittest import mock

import pytest
from PySide6 import QtCore, QtQml

from gremlin import (
    clock,
    config,
    device_initialization,
    history,
    history_modules,
    plugin_manager,
    shared_state,
    threads,
    util,
)
from gremlin import device_library as library
from gremlin.modules import module_file, output, registry, store
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType
from gremlin.ui import device_pack, hardware_profile, history_model, module_model

_ROOT = Path(__file__).resolve().parents[2]
_APPS: list[QtCore.QCoreApplication] = []
# A stick that is not plugged in.
_OTHER = uuid.UUID("11111111-2222-3333-4444-555555555555")
_DISPLAY_KEYS = (
    module_model._CFG_HIDDEN,
    module_model._CFG_ORDER,
    module_model._CFG_STACKS,
    module_model._CFG_SIZES,
    module_model._CFG_COMPACT,
    module_model._CFG_SPLIT,
    module_model._CFG_KEPT_STUBS,
    module_model._CFG_SHOW_STUBS,
)


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def wait_for(done: Callable[[], bool], limit: float = 10.0) -> bool:
    """Polls done() (processing Qt events) until it is true or limit passes."""
    deadline = clock.monotonic() + limit
    while not done():
        if clock.monotonic() > deadline:
            return False
        QtCore.QCoreApplication.processEvents()
        clock.sleep(0.01)
    return True


def settle_history() -> None:
    """Waits (bounded) for the History writer to finish and end."""
    wait_for(lambda: history._writer is None)


@pytest.fixture
def folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """The modules folder empty (everything there, including picture and
    imported folders other tests left, is put aside and back), with its
    bindings, the Home layout settings, History, the Device Library
    folder, both Undo Import records and the open profile all put back as
    they were afterwards."""
    settle_history()
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(history_modules, "_last_pictures", {})
    path = util.modules_dir()
    aside = tmp_path / "aside"
    aside.mkdir()
    for old in list(path.iterdir()):
        shutil.move(str(old), str(aside / old.name))
    before = set(path.rglob("*"))
    bindings = store.bindings()
    store.set_bindings({})
    module_model._ensure_display_options()
    cfg = config.Configuration()
    display = {
        key: cfg.value(module_model._CFG_SECTION, module_model._CFG_GROUP, key)
        for key in _DISPLAY_KEYS
    }
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(store, "_file_import_undo", {})
    monkeypatch.setattr(device_pack, "_last_import", None)
    monkeypatch.setattr(shared_state, "current_profile", None)
    yield path
    settle_history()
    for extra in sorted(
        set(path.rglob("*")) - before, key=lambda p: len(p.parts), reverse=True
    ):
        if extra.is_dir():
            shutil.rmtree(extra, ignore_errors=True)
        else:
            extra.unlink(missing_ok=True)
    for old in aside.iterdir():
        shutil.move(str(old), str(path / old.name))
    store.set_bindings(bindings)
    for key, value in display.items():
        cfg.set(module_model._CFG_SECTION, module_model._CFG_GROUP, key, value)


def stick_guid() -> str:
    dev = next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    )
    return str(dev.device_guid)


def stick_uid() -> uuid.UUID:
    dev = next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    )
    return dev.device_guid.uuid


def vjoy_guid() -> str:
    return str(next(iter(device_initialization.vjoy_devices())).device_guid)


def write_module(folder: Path, slug: str, doc: dict) -> Path:
    path = folder / f"{slug}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def stick_doc(**extra: object) -> dict:
    return {
        "kind": "control.hardware",
        "device": "pJoy Pro",
        "direction": "source",
        "boundGuidLocal": stick_guid(),
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "keys": []},
        **extra,
    }


def setup_cards(folder: Path) -> None:
    """Input cards pJoy Pro, Keyboard and OSC; output cards vJoy 1 and Xbox."""
    write_module(folder, "pjoy_pro", stick_doc())
    for name in ("Keyboard", "OSC"):
        write_module(
            folder,
            name.lower(),
            {
                "kind": "control.hardware",
                "device": name,
                "direction": "source",
                "claim": {"buttons": [], "axes": [], "hats": [], "keys": [30]},
            },
        )
    write_module(folder, "vjoy_1", vjoy_doc())


def vjoy_doc(**extra: object) -> dict:
    return {
        "kind": "control.hardware",
        "device": "vJoy 1",
        "direction": "dest",
        "claim": {"buttons": [1], "axes": [], "hats": []},
        **extra,
    }


def map_button(
    profile: Profile, uid: uuid.UUID, button: int, out: int, mode: str = "Default"
) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    assert item is not None
    root = item.add_item_binding().root_action
    assert root is not None
    root.insert_action(action, "children")


def mapped(profile: Profile, uid: uuid.UUID) -> set[tuple[str, int]]:
    """(mode, button) of every input of the device that has actions."""
    return {
        (str(item.mode), int(str(item.input_id)))
        for item in profile.inputs.get(uid, []) or []
        if item.action_sequences
    }


def open_profile(monkeypatch: pytest.MonkeyPatch) -> Profile:
    """A profile with actions on pJoy Pro (Default and Combat) and on another
    stick, open as the current profile."""
    profile = Profile()
    profile.device_database.devices[stick_uid()] = DeviceInfo(stick_uid(), "pJoy Pro")
    profile.device_database.devices[_OTHER] = DeviceInfo(_OTHER, "Gone Stick")
    monkeypatch.setattr(shared_state, "current_profile", profile)
    profile.modes.add_mode("Combat")
    map_button(profile, stick_uid(), 1, 1)
    map_button(profile, stick_uid(), 2, 2, "Combat")
    map_button(profile, _OTHER, 3, 3)
    return profile


# --- GL-010: stacks, hide and unhide, compact view, split mode ----------------


def test_stacked_cards_of_one_kind_share_a_pile_and_a_size(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.setPileSize("keyboard", 300, 200)
    # vJoy 1 is an output: it doesn't join a pile of inputs (S84).
    model.stackSelected("pjoy_pro", "keyboard,vjoy_1")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro", "keyboard"]
    leaders = model.pileLeaders("source")
    assert "pjoy_pro" in leaders and "keyboard" not in leaders
    assert "vjoy_1" in model.pileLeaders("dest")
    # Cards in a stack share a size (S83).
    assert (model.cardWidth("pjoy_pro"), model.cardHeight("pjoy_pro")) == (300, 200)
    # The stacks persist (a new Home reads them).
    assert module_model.ModuleListModel().pileMembers("keyboard") == [
        "pjoy_pro",
        "keyboard",
    ]


def test_an_input_and_an_output_card_are_not_stacked(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.stackSelected("pjoy_pro", "vjoy_1")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro"]
    assert model.pileMembers("vjoy_1") == ["vjoy_1"]


def test_raise_unstack_and_unstack_all(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.stackSelected("pjoy_pro", "keyboard,osc")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro", "keyboard", "osc"]
    # Clicking a stacked card brings it to the top (the last one is on top).
    model.raiseSlug("keyboard")
    assert model.pileMembers("pjoy_pro")[-1] == "keyboard"
    model.unstackSlug("osc")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro", "keyboard"]
    assert "osc" in model.pileLeaders("source")
    model.unstackAll("keyboard")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro"]
    assert {"pjoy_pro", "keyboard", "osc"} <= set(model.pileLeaders("source"))


def test_hide_card_and_hidden_cards_and_unhide_all(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    showing = model.visibleCount()
    model.ignoreSlug("pjoy_pro")
    model.ignoreSlug("keyboard")
    # Hide Card only takes the card off Home (S82): the file stays.
    assert (folder / "pjoy_pro.json").is_file()
    assert model.visibleCount() == showing - 2
    assert model.cardMap("pjoy_pro") == {}
    # Hidden Cards lists each by name.
    assert model.hiddenCards() == [
        {"slug": "keyboard", "name": "Keyboard"},
        {"slug": "pjoy_pro", "name": "pJoy Pro"},
    ]
    model.unignoreSlug("keyboard")
    assert model.cardMap("keyboard")["name"] == "Keyboard"
    assert model.hiddenList() == ["pjoy_pro"]
    model.unignoreAll()
    assert model.visibleCount() == showing
    assert model.hiddenList() == []


def test_hiding_a_stacked_card_alone_keeps_its_stack(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.stackSelected("pjoy_pro", "keyboard,osc")
    model.ignoreSlug("osc")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro", "keyboard"]
    model.unignoreSlug("osc")
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro", "keyboard", "osc"]


def test_a_stack_edit_keeps_a_hidden_card_in_its_stack(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model.stackSelected("pjoy_pro", "keyboard,osc")
    model.ignoreSlug("osc")
    model.raiseSlug("pjoy_pro")  # any stack edit while OSC is hidden
    model.unignoreSlug("osc")
    # Q10: stacks keep cards that aren't showing, as card order does.
    assert "osc" in model.pileMembers("pjoy_pro")


def test_compact_view_and_layout_persist(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    changes: list[int] = []
    model.panesChanged.connect(lambda: changes.append(1))
    model.setCompactView(True)
    model.setSplitMode("vertical")
    assert len(changes) == 2
    again = module_model.ModuleListModel()
    assert again.compactView is True
    assert again.splitMode == "vertical"
    # An unknown layout name is the single list.
    again.setSplitMode("sideways")
    assert module_model.ModuleListModel().splitMode == "none"
    again.setCompactView(False)
    assert module_model.ModuleListModel().compactView is False


# --- GL-011: Delete Device edge paths ------------------------------------------


def _stick_with_photo(folder: Path) -> None:
    write_module(folder, "pjoy_pro", stick_doc(image="pjoy_pro/photo.jpg"))
    (folder / "pjoy_pro").mkdir()
    (folder / "pjoy_pro" / "photo.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    store.bind("pJoy Pro", stick_guid(), "pjoy_pro")


def test_delete_device_removes_the_devices_actions_file_and_card_layout(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup_cards(folder)
    _stick_with_photo(folder)
    profile = open_profile(monkeypatch)
    model = module_model.ModuleListModel()
    model.setPileSize("pjoy_pro", 400, 300)
    model.stackSelected("pjoy_pro", "keyboard")

    result = json.loads(model.deleteDevice("pJoy Pro", stick_guid()))
    assert result["ok"], result
    # S92: actions in every mode, the module file, its pictures, its file
    # bindings, and the card's size and stack. Other devices keep theirs.
    assert mapped(profile, stick_uid()) == set()
    assert mapped(profile, _OTHER) == {("Default", 3)}
    assert not (folder / "pjoy_pro.json").exists()
    assert not (folder / "pjoy_pro").exists()
    assert "pjoy_pro" not in store.bindings().values()
    assert model.cardWidth("pjoy_pro") == 0
    assert model.pileMembers("keyboard") == ["keyboard"]
    # S96: still plugged in, so it keeps a card without a module.
    assert result["stub"] and result["listed"]
    card = model.cardMap("pjoy_pro")
    assert card["name"] == "pJoy Pro" and card["isModule"] is False


def test_delete_device_of_an_unplugged_stick(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(
        folder,
        "gone_stick",
        {
            "kind": "control.hardware",
            "device": "Gone Stick",
            "direction": "source",
            "boundGuidLocal": str(_OTHER),
            "claim": {"buttons": [3], "axes": [], "hats": []},
        },
    )
    profile = open_profile(monkeypatch)
    model = module_model.ModuleListModel()
    result = json.loads(model.deleteDevice("Gone Stick", str(_OTHER)))
    assert result["ok"], result
    assert not (folder / "gone_stick.json").exists()
    assert mapped(profile, _OTHER) == set()
    assert mapped(profile, stick_uid()) == {("Default", 1), ("Combat", 2)}
    # S96: an unplugged device's card goes.
    assert not result["listed"] and not result["stub"]
    assert model.cardMap("gone_stick") == {}


def test_delete_device_on_a_vjoy_keeps_its_output_module_file(folder: Path) -> None:
    path = write_module(folder, "vjoy_1", vjoy_doc())
    before = path.read_bytes()
    preview = json.loads(hardware_profile.delete_preview("vJoy 1", vjoy_guid()))
    assert preview["keepModule"] is True
    result = json.loads(hardware_profile.delete_device("vJoy 1", vjoy_guid()))
    assert result["ok"], result
    # S93 / Q18: output module files are not deleted.
    assert path.read_bytes() == before
    assert result["keepModule"] and result["keptFile"]


def test_delete_device_always_keeps_a_stick_deleted_autosave(
    folder: Path, tmp_path: Path
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    result = json.loads(hardware_profile.delete_device("pJoy Pro", stick_guid()))
    assert result["ok"], result
    # S91, 10 S21: always an autosave in the Device Library (no deleted
    # devices folder, D-10-NO-DELETED-FOLDER).
    found = library.find_device("pJoy Pro", stick_guid())
    assert found is not None
    assert [s["name"] for s in found["setups"]] == ["Autosave: stick deleted"]
    assert not (tmp_path / "deleted devices").exists()


def test_delete_device_is_refused_while_running(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_module(folder, "pjoy_pro", stick_doc())
    profile = open_profile(monkeypatch)
    monkeypatch.setattr(shared_state, "_runtime_active", True)
    result = json.loads(hardware_profile.delete_device("pJoy Pro", stick_guid()))
    # Q6: "Stop first"; nothing changes.
    assert not result["ok"]
    assert "stop" in result["error"].lower()
    assert path.is_file()
    assert mapped(profile, stick_uid()) == {("Default", 1), ("Combat", 2)}


def test_delete_device_leaves_the_profile_unsaved(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    profile = open_profile(monkeypatch)
    saved = tmp_path / "saved.xml"
    profile.fpath = saved
    profile.to_xml(saved)
    on_disk = saved.read_bytes()
    map_button(profile, _OTHER, 9, 9)  # another edit, not saved
    result = json.loads(hardware_profile.delete_device("pJoy Pro", stick_guid()))
    assert result["ok"], result
    assert mapped(profile, stick_uid()) == set()
    # Q4: removed in memory only; the profile on disk is as it was.
    assert saved.read_bytes() == on_disk
    assert profile.has_unsaved_changes()


# --- GL-012: import refusals, Import Image, keepPhoto, Start Fresh -------------


def _source_file(tmp_path: Path, name: str, doc: object) -> str:
    path = tmp_path / name
    text = doc if isinstance(doc, str) else json.dumps(doc)
    path.write_text(text, encoding="utf-8")
    return str(path)


_STICK_FILE = {
    "kind": "control.hardware",
    "device": "Other Stick",
    "direction": "source",
    "claim": {"buttons": [1, 2, 3], "axes": [1], "hats": [], "keys": []},
}


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("unreadable", "That file could not be read."),
        ("not a module file", "That file is not a module file."),
        ("vjoy onto a stick", "A vJoy file cannot be copied onto a stick."),
        ("stick onto a vjoy", "A stick file cannot be copied onto a vJoy."),
        (
            "not connected",
            "This device is not connected, so the file cannot be checked.",
        ),
        (
            "current damaged",
            "The current file could not be read, so it was not replaced.",
        ),
    ],
)
def test_import_refusals_change_nothing(
    folder: Path, tmp_path: Path, case: str, message: str
) -> None:
    stick = write_module(folder, "pjoy_pro", stick_doc())
    vjoy = write_module(folder, "vjoy_1", vjoy_doc())
    device, guid, direction = "pJoy Pro", stick_guid(), "source"
    source = _source_file(tmp_path, "other_stick.json", _STICK_FILE)
    if case == "unreadable":
        source = _source_file(tmp_path, "half.json", '{"kind": "control.hard')
    elif case == "not a module file":
        source = _source_file(tmp_path, "settings.json", {"theme": "dark"})
    elif case == "vjoy onto a stick":
        source = _source_file(tmp_path, "vjoy_7.json", vjoy_doc(device="vJoy 7"))
    elif case == "stick onto a vjoy":
        device, guid, direction = "vJoy 1", vjoy_guid(), "dest"
    elif case == "not connected":
        device, guid = "Gone Stick", str(_OTHER)
    else:
        stick.write_text('{"kind": "control.hard', encoding="utf-8")
    files = {stick: stick.read_bytes(), vjoy: vjoy.read_bytes()}

    model = module_model.ModuleListModel()
    assert model.importModuleFile(guid, device, source, direction) == message
    # S57: refused, nothing written, nothing to undo.
    assert {path: path.read_bytes() for path in files} == files
    assert not (folder / "gone_stick.json").exists()
    assert not (folder / "imported").exists() or not any(
        (folder / "imported").iterdir()
    )
    assert not model.importCanUndo()


def test_import_into_a_renamed_stick_goes_into_the_file_it_uses(
    folder: Path, tmp_path: Path
) -> None:
    write_module(folder, "old_name", stick_doc(device="Old Name"))
    assert registry.resolve_module_slug("pJoy Pro", stick_guid()) == "old_name"
    source = _source_file(tmp_path, "other_stick.json", _STICK_FILE)
    model = module_model.ModuleListModel()
    message = model.importModuleFile(stick_guid(), "pJoy Pro", source, "source")
    assert message.startswith("Imported "), message
    # Q13: into the file the device uses (map 1), not a new own-name file.
    assert not (folder / "pjoy_pro.json").exists()
    claim = json.loads((folder / "old_name.json").read_text(encoding="utf-8"))["claim"]
    assert claim["buttons"] == [1, 2, 3]


def test_module_setup_cancel_puts_the_old_picture_back(tmp_path: Path) -> None:
    # Q2: Import Image works like the Button Map: Module Setup, off-screen in
    # the running program, imports a picture, then Cancel and Discard; the
    # starting photo is back on the module file, on disk and in the window.
    from test.unit.test_stage1_button_map import (  # pyright: ignore[reportMissingImports]
        _run,
    )

    out = _run("setup", tmp_path / "home")
    back = out["setup-cancel"]
    assert back["file-image"] == back["start-image"]
    assert back["old-photo"] is True
    assert back["new-photo"] is False
    assert out["setup-reopened-photo"] == "photo.png"


def test_save_module_with_the_same_photo_adds_nothing_to_the_library(
    folder: Path,
) -> None:
    write_module(folder, "pjoy_pro", stick_doc(image="pjoy_pro/photo.jpg"))
    (folder / "pjoy_pro").mkdir()
    (folder / "pjoy_pro" / "photo.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(stick_guid())
    library = folder / "library"
    # What Save Module does (DialogConfigureModule.commitModule).
    hw.keepPhoto("pJoy Pro", hw.profilePhotoUrl("pJoy Pro"))
    before = sorted(p.name for p in library.iterdir()) if library.is_dir() else []
    # Saved again, the photo unchanged.
    hw.keepPhoto("pJoy Pro", hw.profilePhotoUrl("pJoy Pro"))
    after = sorted(p.name for p in library.iterdir()) if library.is_dir() else []
    # Q3: copied to the library only when the photo changed.
    assert after == before


def _damaged_stick(folder: Path) -> Path:
    path = folder / "pjoy_pro.json"
    path.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    return path


def test_start_fresh_moves_the_damaged_file_aside(folder: Path) -> None:
    path = _damaged_stick(folder)
    damaged = path.read_bytes()
    model = module_model.ModuleListModel()
    assert model.cardMap("pjoy_pro")["damaged"]
    copy = Path(model.startFresh("pJoy Pro", stick_guid()))
    # S66: moved aside as <name>.json.bad-<date>, nothing deleted.
    assert copy.name.startswith("pjoy_pro.json.bad-")
    assert copy.read_bytes() == damaged
    assert not path.exists()
    assert model.cardMap("pjoy_pro")["damaged"] == ""
    # A file that is fine is not moved.
    write_module(folder, "pjoy_pro", stick_doc())
    assert model.startFresh("pJoy Pro", stick_guid()) == ""
    assert path.is_file()


def test_start_fresh_is_a_history_entry(folder: Path) -> None:
    _damaged_stick(folder)
    model = module_model.ModuleListModel()
    assert model.startFresh("pJoy Pro", stick_guid())
    settle_history()
    # Q17 / F3: Start Fresh is recorded (S69).
    entries = history.entries("modules")
    assert any(
        (e.get("subject") or {}).get("fileName") == "pjoy_pro.json" for e in entries
    )


# --- GL-013: card counts and status, card menus --------------------------------


def test_card_counts_after_a_settings_change_are_the_claimed_counts(
    folder: Path,
) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    model._refresh_inplace()  # what configChanged runs
    card = model.cardMap("pjoy_pro")
    assert (card["buttons"], card["axes"], card["hats"]) == (2, 0, 0)
    card = model.cardMap("vjoy_1")
    assert (card["buttons"], card["axes"], card["hats"]) == (1, 0, 0)


def test_card_counts_at_a_reload_are_the_claimed_counts(folder: Path) -> None:
    setup_cards(folder)
    model = module_model.ModuleListModel()
    # Q8 / S78: always the claimed counts (pJoy Pro has 6 axes, 2 hats).
    card = model.cardMap("pjoy_pro")
    assert (card["buttons"], card["axes"], card["hats"]) == (2, 0, 0)
    card = model.cardMap("vjoy_1")
    assert (card["buttons"], card["axes"], card["hats"]) == (1, 0, 0)


def test_a_busy_vjoy_card_says_in_use(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(folder, "vjoy_1", vjoy_doc())
    monkeypatch.setattr(output, "vjoy_in_use_elsewhere", lambda vjoy_id: True)
    model = module_model.ModuleListModel()
    assert model.cardMap("vjoy_1")["status"] == "In use by another program"


def test_a_busy_vjoy_card_still_says_in_use_after_a_settings_change(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(folder, "vjoy_1", vjoy_doc())
    monkeypatch.setattr(output, "vjoy_in_use_elsewhere", lambda vjoy_id: True)
    model = module_model.ModuleListModel()
    model._refresh_inplace()
    # S34: the card says "In use by another program".
    assert model.cardMap("vjoy_1")["status"] == "In use by another program"


def test_a_damaged_card_turns_back_after_history_restore(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # GL-141 (suspected) on the real path: Restore says profileChanged as
    # well as configChanged, so Home reloads its cards in full, which checks
    # the file again (_refresh_inplace alone would not).
    # The app (once made) has a mode list that reads the open profile on
    # profileChanged; the program always has one open.
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    path = folder / "pjoy_pro.json"
    module_file.write_json(path, stick_doc())
    settle_history()
    created = history.entries("modules")[0]
    assert created["title"].startswith("Created the module file")
    path.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    model = module_model.ModuleListModel()
    assert model.cardMap("pjoy_pro")["damaged"]

    result = history_model.restore(created["id"], "after")
    assert result["ok"], result
    # S65: the file can be read again, so the card is no longer damaged.
    assert wait_for(lambda: model.cardMap("pjoy_pro").get("damaged") == "")
    assert model.cardMap("pjoy_pro")["status"] == "Connected"


def _function_source(text: str, name: str) -> str:
    start = text.index(f"function {name}(")
    depth = 0
    for index in range(text.index("{", start), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"{name} has no end")


def card_menu(
    slug: str, name: str, direction: str, bus: str, tab: str, damaged: str = ""
) -> list[str]:
    """The items of a Home card's right-click menu (StatusCard.qml's own
    menuModel(), run on a stand-in MenuModel)."""
    text = (_ROOT / "qml" / "StatusCard.qml").read_text(encoding="utf-8")
    script = (
        """
        var MenuModel = {
            action: function(text) { return text },
            section: function(id, title, items) { return items },
            menu: function(kind, title, quick, sections) {
                var out = quick.filter(function(i) { return i !== null })
                sections.forEach(function(items) {
                    items.forEach(function(i) { if (i !== null) out.push(i) })
                })
                return out
            }
        }
        """
        + f"var slug = {json.dumps(slug)}; var cardName = {json.dumps(name)};"
        + f" var rawName = cardName; var direction = {json.dumps(direction)};"
        + f" var bus = {json.dumps(bus)}; var tab = {json.dumps(tab)};"
        + " var stacked = false;"
        + f" var _card = {{ damaged: {json.dumps(damaged)}, canStackSelected: false }};"
        + _function_source(text, "menuModel")
    )
    engine = QtQml.QJSEngine()
    loaded = cast(QtQml.QJSValue, engine.evaluate(script))
    assert not loaded.isError(), loaded.toString()
    result = cast(QtQml.QJSValue, engine.evaluate("JSON.stringify(menuModel())"))
    assert not result.isError(), result.toString()
    return json.loads(result.toString())


_NOT_FOR_LOGICAL = {
    "Module Setup…",
    "Calibration",
    "Auto Mapper",
    "Device Information",
    "Copy Setup to Another Stick…",
    "Swap with Another Stick…",
    "Change vJoy Output…",
}


def test_card_menus_leave_out_what_does_not_apply() -> None:
    # S88.
    stick = card_menu("pjoy_pro", "pJoy Pro", "source", "DirectInput", "physical")
    assert {
        "Module Setup…", "Calibration", "Auto Mapper", "Swap with Another Stick…"
    } <= set(stick)
    assert "Swap Device…" not in stick
    assert "Start Fresh…" not in stick
    damaged = card_menu(
        "pjoy_pro", "pJoy Pro", "source", "DirectInput", "physical", "bad JSON"
    )
    assert "Start Fresh…" in damaged
    xbox = card_menu("xbox", "Xbox 360 Controller", "dest", "XInput", "xbox")
    assert not {
        "Module Setup…", "Calibration", "Auto Mapper", "Swap with Another Stick…"
    } & set(xbox)
    vjoy = card_menu("vjoy_1", "vJoy 1", "dest", "DirectInput", "physical")
    assert "Module Setup…" in vjoy
    assert not {"Calibration", "Swap with Another Stick…"} & set(vjoy)
    for slug, name in (("keyboard", "Keyboard"), ("osc", "OSC")):
        menu = card_menu(slug, name, "source", "HID", slug)
        assert not (_NOT_FOR_LOGICAL - {"Module Setup…"}) & set(menu)


def test_the_logical_device_card_menu() -> None:
    menu = card_menu("logical", "Logical Device", "source", "Logical", "logical")
    # Q7.
    assert not _NOT_FOR_LOGICAL & set(menu)


def test_output_cards_have_no_delete_device() -> None:
    vjoy = card_menu("vjoy_1", "vJoy 1", "dest", "DirectInput", "physical")
    xbox = card_menu("xbox", "Xbox 360 Controller", "dest", "XInput", "xbox")
    # Q18.
    assert "Delete Device" not in vjoy
    assert "Delete Device" not in xbox


def test_an_input_card_offers_delete_device() -> None:
    stick = card_menu("pjoy_pro", "pJoy Pro", "source", "DirectInput", "physical")
    assert "Delete Device" in stick


def test_auto_mapper_also_claim_on_a_damaged_output_file_makes_no_actions(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.auto_mapper import AutoMapper, AutoMapperOptions

    write_module(folder, "pjoy_pro", stick_doc())
    write_module(
        folder, "vjoy_1", vjoy_doc(claim={"buttons": [], "axes": [], "hats": []})
    )
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    real_load = module_file.load_for_update

    def damaged_meanwhile(path: Path) -> dict:
        # The output module file is damaged after the Auto Mapper read it.
        if Path(path).name == "vjoy_1.json":
            raise module_file.ModuleFileDamaged(Path(path), "it is not valid JSON")
        return real_load(path)

    monkeypatch.setattr(module_file, "load_for_update", damaged_meanwhile)
    with mock.patch.object(module_file, "report_refused"):
        report = AutoMapper(profile).generate_module_mappings(
            ["pjoy_pro"], ["vjoy_1"], AutoMapperOptions(claim_outputs=True)
        )
    # S120 / Q15: refused, so no claim and no action; the outputs are listed.
    assert mapped(profile, stick_uid()) == set()
    assert "not claimed" in report


# --- GL-014: output.py and the registry from several threads -------------------


class _PausingCache(dict):
    """registry._cache that pauses one thread in the middle of a walk over
    it, until another thread has had its turn (bounded)."""

    def __init__(self, paused: threading.Event, resume: threading.Event) -> None:
        super().__init__()
        self.thread = threading.current_thread()
        self.paused, self.resume = paused, resume
        self.done = False

    def __iter__(self) -> Iterator:
        walk = super().__iter__()
        if threading.current_thread() is not self.thread or self.done:
            yield from walk
            return
        self.done = True
        first = next(walk, None)
        if first is None:
            return
        yield first
        self.paused.set()
        self.resume.wait(2.0)  # a fixed registry makes the other thread wait
        yield from walk


def test_the_module_cache_read_on_two_threads_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("one", "two"):
        (tmp_path / f"{name}.json").write_text(
            json.dumps({"kind": "control.hardware", "device": name}), encoding="utf-8"
        )
    monkeypatch.setattr(registry, "_folder", lambda: tmp_path)
    paused, resume = threading.Event(), threading.Event()
    monkeypatch.setattr(registry, "_cache", _PausingCache(paused, resume))
    other: list[object] = []

    def second_reader() -> None:
        if not paused.wait(10.0):
            return
        (tmp_path / "three.json").write_text(
            json.dumps({"kind": "control.hardware", "device": "three"}),
            encoding="utf-8",
        )
        try:
            other.append(len(registry.modules()))
        except Exception as exc:  # noqa: BLE001
            other.append(exc)
        resume.set()

    thread = threads.start("stage1 registry reader", second_reader)
    try:
        first = registry.modules()
    finally:
        resume.set()
        paused.set()
        thread.join(10.0)
    assert not thread.is_alive()
    assert {m.slug for m in first} >= {"one", "two"}
    assert other == [3]


class _PausingSet(set):
    """output._blocked that pauses the first thread right after its check,
    until another thread has checked too (bounded)."""

    def __init__(
        self, checked: threading.Event, other_checked: threading.Event
    ) -> None:
        super().__init__()
        self.thread = threading.current_thread()
        self.checked, self.other_checked = checked, other_checked

    def __contains__(self, key: object) -> bool:
        found = super().__contains__(key)
        if threading.current_thread() is self.thread:
            if not self.checked.is_set():
                self.checked.set()
                self.other_checked.wait(2.0)  # a fixed output makes it wait
        else:
            self.other_checked.set()
        return found


def test_a_blocked_output_is_logged_once_from_two_threads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked, other_checked = threading.Event(), threading.Event()
    monkeypatch.setattr(output, "_blocked", _PausingSet(checked, other_checked))
    log = mock.Mock(spec=logging.Logger)
    monkeypatch.setattr(output, "syslog", log)
    key = ("vjoy", 1, "button", 99)

    def second_writer() -> None:
        if checked.wait(10.0):
            output._log_once(key, "Output blocked: vJoy 1 button 99")

    thread = threads.start("stage1 output writer", second_writer)
    try:
        output._log_once(key, "Output blocked: vJoy 1 button 99")
    finally:
        checked.set()
        thread.join(10.0)
    assert not thread.is_alive()
    # S29: logged once per Run.
    assert log.warning.call_count == 1


def test_output_claims_and_modules_from_several_threads(
    folder: Path,
) -> None:
    write_module(folder, "vjoy_1", vjoy_doc())
    write_module(folder, "pjoy_pro", stick_doc())
    errors: list[BaseException] = []
    start = threading.Event()

    def reader() -> None:
        start.wait(10.0)
        try:
            for _turn in range(200):
                output.refresh()
                assert output.vjoy_claim(1).get("buttons") == [1]
                assert {m.slug for m in registry.modules()} >= {"vjoy_1", "pjoy_pro"}
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    started = [threads.start(f"stage1 reader {n}", reader) for n in range(4)]
    start.set()
    for thread in started:
        thread.join(30.0)
    assert not [t for t in started if t.is_alive()]
    assert errors == []


# --- Batch 1: the module file store (map 1, gap list section 4) ---------------


def test_a_failed_output_read_keeps_the_last_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # GL-083 (06 RB16, S47): a read that fails keeps the claims read before;
    # it used to give no claims, so every vJoy output was blocked.
    good = {1: {"buttons": [1]}}
    monkeypatch.setattr(output, "_vjoy_claims", dict(good))
    monkeypatch.setattr(output, "_claims_at", 0.0)
    monkeypatch.setattr(output, "_told_read_failed", False)

    def broken() -> list:
        raise OSError("modules folder unreadable")

    monkeypatch.setattr(registry, "outputs", broken)
    output.refresh()
    assert output._vjoy_claims == good


def test_a_module_save_reaches_the_output_claims_at_once(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # GL-084 (03 S36, 06 S53): every module file write re-reads the claims.
    calls: list[int] = []
    monkeypatch.setattr(output, "refresh", lambda: calls.append(1))
    path = write_module(folder, "vjoy_1", vjoy_doc())
    assert store.update_path(path, lambda doc: doc.update(note=1), "test")
    assert calls


def test_import_undo_belongs_to_its_device_and_window(
    folder: Path, tmp_path: Path
) -> None:
    # GL-087 (03 S59): another device's or window's Undo is not this one's.
    source = _source_file(
        tmp_path,
        "keys.json",
        {"kind": "control.hardware", "device": "Keys", "claim": {"keys": [5]}},
    )
    message = store.import_file("Keyboard", "", source, "source", "Configure Module")
    assert message.startswith("Imported "), message
    assert store.can_undo_file_import("Keyboard", "", "Configure Module")
    assert not store.can_undo_file_import("pJoy Pro", stick_guid(), "Configure Module")
    assert not store.can_undo_file_import("Keyboard", "", "Device Pack")
    assert store.undo_file_import("pJoy Pro", stick_guid(), "Configure Module") == (
        "Undo failed. There is nothing to undo."
    )
    assert (folder / "keyboard.json").is_file()
    undone = store.undo_file_import("Keyboard", "", "Configure Module")
    assert undone.startswith("Undone.")
    assert not (folder / "keyboard.json").exists()


def test_a_missing_picture_is_not_another_devices(folder: Path) -> None:
    # GL-085 (07 S11): a picture is found only where its reference says.
    (folder / "library").mkdir()
    (folder / "library" / "photo.jpg").write_bytes(b"someone else's")
    assert store.find_picture("pjoy_pro/photo.jpg") is None
    hw = hardware_profile.HardwareProfile()
    assert hw._resolve_existing("pjoy_pro/photo.jpg") is None


def test_a_damaged_file_keeps_its_photo_on_import_image(
    folder: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # GL-070 (03 S64): Import Image on a damaged module file touches no photo.
    monkeypatch.setattr(module_file, "report_refused", lambda error: None)
    _damaged_stick(folder)
    (folder / "pjoy_pro").mkdir()
    old = folder / "pjoy_pro" / "photo.png"
    old.write_bytes(b"old")
    new = tmp_path / "new.jpg"
    new.write_bytes(b"new")
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(stick_guid())
    assert hw.copyImage(new.as_uri(), "pJoy Pro") == ""
    assert old.read_bytes() == b"old"
    assert not (folder / "pjoy_pro" / "photo.jpg").exists()


def test_a_refused_button_map_save_copies_no_picture(
    folder: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # GL-079 (07 S12): the damage check comes before any picture is copied.
    monkeypatch.setattr(module_file, "report_refused", lambda error: None)
    _damaged_stick(folder)
    picture = tmp_path / "chosen.png"
    picture.write_bytes(b"picture")
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(stick_guid())
    payload = {"image": picture.as_uri(), "nodes": []}
    assert not hw.save("pJoy Pro", json.dumps(payload))
    pictures = folder / "pjoy_pro"
    assert not pictures.exists() or not any(pictures.iterdir())


def test_delete_device_removes_its_recovery_and_photo_safety_copies(
    folder: Path,
) -> None:
    # GL-094 (07 Q11): nothing of the deleted device is left behind.
    write_module(folder, "pjoy_pro", stick_doc())
    recovery = store.recovery_path("pjoy_pro")
    recovery.parent.mkdir(parents=True)
    recovery.write_text("{}", encoding="utf-8")
    stash = store.photo_stash_dir("pjoy_pro")
    stash.mkdir(parents=True)
    (stash / "manifest.json").write_text("{}", encoding="utf-8")
    result = json.loads(hardware_profile.delete_device("pJoy Pro", stick_guid()))
    assert result["ok"], result
    assert not recovery.exists()
    assert not stash.exists()
