# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Nothing the user made is lost without being asked: saving names the
unfinished actions it would leave out, deleting a module file keeps an
autosave in the Device Library,
and cancelling a Button Map edit puts the photo back."""

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
    monkeypatch.setattr(store, "users_of", lambda slug: set())
    monkeypatch.setattr(store, "bindings", lambda: {})
    monkeypatch.setattr(registry, "guid_for_name", lambda name: "")
    return maps


def test_deleting_a_module_file_keeps_a_copy(modules: pathlib.Path) -> None:
    # 03 S62, 08 S88: the copy is a "module file deleted" autosave in the
    # Device Library (D-10-NO-DELETED-FOLDER).
    claim = {"claim": {"buttons": [1]}}
    (modules / "stick_r.json").write_text(json.dumps(claim), encoding="utf-8")
    assert hardware_profile.delete_module_file("Stick R", "") == ""
    assert not (modules / "stick_r.json").exists()
    found = library.find_device("Stick R", "")
    assert found is not None
    names = [setup["name"] for setup in found["setups"]]
    assert names == ["Autosave: module file deleted"]
    assert not (modules.parent / "deleted devices").exists()


def test_no_copy_means_no_delete(
    modules: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (modules / "stick_r.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        library, "autosave", lambda *args: {"ok": False, "error": "no room"}
    )
    message = hardware_profile.delete_module_file("Stick R", "")
    assert "not deleted" in message
    assert (modules / "stick_r.json").exists()


def test_cancel_puts_the_starting_photo_back(modules: pathlib.Path) -> None:
    folder = modules / "stick_r"
    folder.mkdir()
    (folder / "photo.jpg").write_bytes(b"original")
    doc = modules / "stick_r.json"
    doc.write_text(json.dumps({"image": "stick_r/photo.jpg"}), encoding="utf-8")
    hw = hardware_profile.HardwareProfile()

    hw.stashPhoto("Stick R")
    # Choose photo… with a .png, then a second change in the same edit.
    (folder / "photo.jpg").unlink()
    (folder / "photo.png").write_bytes(b"new")
    doc.write_text(json.dumps({"image": "stick_r/photo.png"}), encoding="utf-8")
    hw.stashPhoto("Stick R")  # Keeps the session's first photo, not this one.

    assert hw.restorePhoto("Stick R") is True
    assert (folder / "photo.jpg").read_bytes() == b"original"
    assert not (folder / "photo.png").exists()
    assert json.loads(doc.read_text(encoding="utf-8"))["image"] == "stick_r/photo.jpg"
    # Nothing left to restore.
    assert hw.restorePhoto("Stick R") is False


def test_clear_image_then_cancel_and_save_drops_the_copy(modules: pathlib.Path) -> None:
    folder = modules / "stick_r"
    folder.mkdir()
    (folder / "photo.jpg").write_bytes(b"original")
    hw = hardware_profile.HardwareProfile()

    hw.stashPhoto("Stick R")
    assert hw.clearImage("Stick R")
    assert not (folder / "photo.jpg").exists()
    assert hw.restorePhoto("Stick R") is True
    assert (folder / "photo.jpg").read_bytes() == b"original"

    hw.stashPhoto("Stick R")
    hw.dropPhotoStash("Stick R")
    assert hw.restorePhoto("Stick R") is False


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
