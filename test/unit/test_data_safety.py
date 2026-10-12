# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Nothing the user made is lost without being asked: saving names the
unfinished actions it would leave out, deleting a module file keeps an
autosave in the Device Library,
and cancelling a Device Mapping Editor edit leaves the photo as it was."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
import types

import pytest

from gremlin import device_library as library
from gremlin import profile
from gremlin.modules import registry, store
from gremlin.ui import hardware_profile
from test.unit._device_folders import picture_file, put_module, put_picture


def _action(name: str, feedback: list[tuple[str, str]]) -> types.SimpleNamespace:
    entries = [
        types.SimpleNamespace(
            feedback_type=types.SimpleNamespace(name=kind), message=text
        )
        for kind, text in feedback
    ]
    return types.SimpleNamespace(name=name, user_feedback=lambda: entries)


def test_unfinished_actions_are_named_with_their_first_error() -> None:
    library = profile.Library()
    library._actions = {
        1: _action(
            "Play Sound",
            [("Error", "The sound file is missing"), ("Error", "second")],
        ),
        2: _action("Map to vJoy", [("Warning", "Not claimed yet")]),
        3: _action("Map to Keyboard", [("Error", "No keys")]),
    }
    assert library.unfinished_actions() == [
        "Play Sound: The sound file is missing",
        "Map to Keyboard: No keys",
    ]


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    maps = tmp_path / "modules"
    maps.mkdir()
    monkeypatch.setattr(store, "folder", lambda: maps)
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(registry, "guid_for_name", lambda name: "")
    return maps


def test_deleting_a_module_file_keeps_a_copy(modules: pathlib.Path) -> None:
    # 03 S62, 08 S88: the copy is a "module file deleted" autosave in the
    # Device Library (D-10-NO-DELETED-FOLDER).
    claim = {"claim": {"buttons": [1]}}
    path = put_module(modules, "Stick R", claim)
    assert hardware_profile.delete_module_file("Stick R", "") == ""
    assert not path.exists()
    found = library.find_device("Stick R", "")
    assert found is not None
    names = [setup["name"] for setup in found["setups"]]
    assert names == ["Autosave: module file deleted"]
    assert not (modules.parent / "deleted devices").exists()


def test_no_copy_means_no_delete(
    modules: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = put_module(modules, "Stick R", {})
    monkeypatch.setattr(
        library, "autosave", lambda *args: {"ok": False, "error": "no room"}
    )
    message = hardware_profile.delete_module_file("Stick R", "")
    assert "not deleted" in message
    assert path.exists()


def _png(path: pathlib.Path) -> pathlib.Path:
    from PySide6 import QtGui

    image = QtGui.QImage(4, 4, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#336699"))
    assert image.save(str(path))
    return path


def test_cancel_puts_the_starting_photo_back(
    modules: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    # 07 S26, S107: a new photo (Import Image) waits in the edit's
    # temporary folder; the device's folder and module file are not touched
    # until Save, so Cancel leaves the starting photo as it was.
    ref = put_picture(modules, "Stick R", "photo.jpg", b"original")
    doc = put_module(modules, "Stick R", {"nodes": [_background(ref)]})
    before = doc.read_bytes()
    folder = doc.parent / "pictures"
    hw = hardware_profile.HardwareProfile()

    hw.beginEdit("Stick R")
    assert hw.editActive("Stick R")
    new = hw.copyImage(_png(tmp_path / "new.png").as_uri(), "Stick R")
    assert new == "pictures/photo.png"
    hw.beginEdit("Stick R")  # An edit already open goes on.
    assert sorted(p.name for p in folder.iterdir()) == ["photo.jpg"]
    assert doc.read_bytes() == before

    assert hw.cancelEdit("Stick R") is True
    assert not hw.editActive("Stick R")
    assert (folder / "photo.jpg").read_bytes() == b"original"
    assert not (folder / "photo.png").exists()
    assert doc.read_bytes() == before
    # Nothing left to cancel.
    assert hw.cancelEdit("Stick R") is False


def _background(ref: str) -> dict:
    """The device's photo: the bottom background picture (07 S111, S127)."""
    return {"id": "bg", "kind": "draw", "shape": "image", "plane": "background",
            "src": ref, "fx": 0.125, "fy": 0.125, "fw": 0.75, "fh": 0.75}


def test_clearing_the_background_changes_nothing_until_save(
    modules: pathlib.Path,
) -> None:
    ref = put_picture(modules, "Stick R", "photo.jpg", b"original")
    doc = put_module(modules, "Stick R", {"nodes": [_background(ref)]})
    folder = picture_file(modules, "Stick R", "photo.jpg").parent
    hw = hardware_profile.HardwareProfile()

    # Clear Background only changes the window's map: Cancel keeps it (07
    # S41, S26).
    hw.beginEdit("Stick R")
    assert hw.cancelEdit("Stick R") is True
    assert (folder / "photo.jpg").read_bytes() == b"original"
    assert store.device_photo_ref(json.loads(doc.read_text(encoding="utf-8"))) == ref

    # Save ends the edit; the picture nothing names any more goes (07 S106).
    hw.beginEdit("Stick R")
    assert hw.save("Stick R", json.dumps({"nodes": []}))
    assert not hw.editActive("Stick R")
    saved = json.loads(doc.read_text(encoding="utf-8"))
    assert store.device_photo_ref(saved) == ""
    assert "image" not in saved and "photo" not in saved
    assert not (folder / "photo.jpg").exists()


def test_hat_switch_keeps_the_shared_directions() -> None:
    from action_plugins.hat_buttons import HatButtonsData

    data = HatButtonsData()
    data.set_button_count(8)
    data.direction["North"] = ["n"]
    data.direction["North-East"] = ["ne1", "ne2"]
    data.direction["South"] = ["s"]
    # Going to 4 way would drop the two North-East actions; nothing else.
    assert data.actions_dropped_by(4) == 2
    data.set_button_count(4)
    assert data.direction["North"] == ["n"]
    assert data.direction["South"] == ["s"]
    assert "North-East" not in data.direction
    # And back: the shared directions still keep theirs.
    data.set_button_count(8)
    assert data.direction["North"] == ["n"]
    assert data.direction["North-East"] == []
    assert data.actions_dropped_by(4) == 0


# --- 04 Q7 (GL-105): an action type this program doesn't have ----------------

def test_a_profile_with_an_unknown_action_type_opens_and_keeps_it(
    tmp_path: pathlib.Path, qapp: object
) -> None:
    import uuid
    from xml.etree import ElementTree

    from gremlin import plugin_manager, shared_state
    from gremlin.types import InputType

    stick = uuid.UUID("abababab-cdcd-efef-0101-232323232323")
    made = profile.Profile()
    before, shared_state.current_profile = shared_state.current_profile, made
    try:
        item = made.get_input_item(
            stick, InputType.JoystickButton, 1, "Default", create_if_missing=True
        )
        root = item.add_item_binding().root_action
        chain = plugin_manager.PluginManager().create_instance(
            "Smart Toggle", InputType.JoystickButton
        )
        note = plugin_manager.PluginManager().create_instance(
            "Description", InputType.JoystickButton
        )
        note.description = "inside"
        chain.insert_action(note, "children")
        root.insert_action(chain, "children")
        path = tmp_path / "unknown.xml"
        made.to_xml(path)
    finally:
        shared_state.current_profile = before
    # The Smart Toggle plugin is gone here: its type is unknown.
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace('type="smart-toggle"', 'type="gone-plugin"')
    path.write_text(text, encoding="utf-8")

    p = profile.Profile()
    p.from_xml(path)  # used to raise "Unknown type 'gone-plugin'"
    assert any("gone-plugin" in w for w in p.load_warnings)
    item = p.get_input_item(stick, InputType.JoystickButton, 1, "Default")
    assert item is not None
    odd = item.action_sequences[0].root_action.get_actions()[0][0]
    assert odd.tag == "gone-plugin" and odd.id == chain.id
    assert note.id in p.library.in_use()  # what it holds stays

    out = tmp_path / "saved.xml"
    p.to_xml(out)
    saved = ElementTree.parse(out).getroot()
    kept = saved.find(f"./library/action[@id='{chain.id}']")
    assert kept is not None and kept.get("type") == "gone-plugin"
    assert str(note.id) in [e.text for e in kept.iter("action-id")]
    assert saved.find(f"./library/action[@id='{note.id}']") is not None

    # The editor shows a note for it (nothing to edit).
    from gremlin.ui.profile import InputItemBindingModel, InputItemModel

    shared_state.current_profile = p
    try:
        owner = InputItemModel(item, 0, None)
        binding = InputItemBindingModel(item.action_sequences[0], owner)
        notes = [
            m.note
            for m in binding._action_models.values()
            if m.action_data is odd
        ]
        assert notes and "gone-plugin" in notes[0]
        assert any(
            m.qmlPath.endswith("UnknownAction.qml")
            for m in binding._action_models.values()
            if m.action_data is odd
        )
        binding.deleteLater()
        owner.deleteLater()
    finally:
        shared_state.current_profile = before
