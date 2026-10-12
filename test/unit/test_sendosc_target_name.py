# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Send OSC keeps its target's name (D-09-SENDOSC-TARGET-NAME, 05 S137):
the action saves the name with the id, refreshed from the current Targets
whenever the id still resolves (pick, load, save, a rename in OSC Setup
while the action is open), so a missing target reads "OSC target <name> is
not Found." and the editor shows "⚠ <name>". The id is used only when no
name was ever saved."""

from __future__ import annotations

import json
import pathlib
import sys
from collections.abc import Callable, Iterator
from xml.etree import ElementTree

sys.path.append(".")

import pytest

from action_plugins.root import RootData
from gremlin import osc_device_file, osc_output
from gremlin.modules import output
from gremlin.profile import InputItem, InputItemBinding, Library, Profile
from gremlin.types import InputType

B = InputType.JoystickButton


@pytest.fixture
def osc(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    """OSC's file in a temp folder with one target "Mixer" (id t1)."""
    file = tmp_path / "osc.json"
    monkeypatch.setattr(osc_device_file, "path", lambda: file)

    def write(targets: list[dict]) -> None:
        file.write_text(
            json.dumps({"server": {"output_enabled": True}, "targets": targets}),
            encoding="utf-8",
        )
        from gremlin.modules import registry

        registry._cache.pop(file, None)
        osc_output.invalidate()

    write([{"id": "t1", "name": "Mixer", "host": "127.0.0.1", "port": 9000}])
    yield {"write": write, "file": file}
    osc_output.reset()


def _round_trip(action: object) -> object:
    from action_plugins.send_osc import SendOscData

    action.address = "/a"  # type: ignore[attr-defined]
    node = action.to_xml()  # type: ignore[attr-defined]
    loaded = SendOscData(B)
    loaded.from_xml(ElementTree.fromstring(ElementTree.tostring(node)), Library())
    return loaded


def _saved_name(action: object) -> str | None:
    action.address = "/a"  # type: ignore[attr-defined]
    node = action.to_xml()  # type: ignore[attr-defined]
    for prop in node.iter("property"):
        if prop.findtext("name") == "target-name":
            return prop.findtext("value")
    return None


def test_name_saved_with_the_id(osc: dict) -> None:
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    assert action.target == "t1"
    assert action.target_name == "Mixer"
    assert _saved_name(action) == "Mixer"
    loaded = _round_trip(action)
    assert (loaded.target, loaded.target_name) == ("t1", "Mixer")


def test_missing_target_reads_its_saved_name(osc: dict) -> None:
    from action_plugins.send_osc import SendOscData

    loaded = _round_trip(SendOscData(B))
    osc["write"]([])  # the target was deleted in OSC Setup
    settings = output.osc_settings()
    assert (
        output.osc_cant_send_text(loaded.target, settings, loaded.target_name)
        == "OSC target Mixer is not Found."
    )
    # Reloaded while missing: the saved name stays.
    again = _round_trip(loaded)
    assert again.target_name == "Mixer"
    assert output.osc_cant_send_text("t1", settings, again.target_name) == (
        "OSC target Mixer is not Found."
    )


def test_id_only_when_no_name_was_saved(osc: dict) -> None:
    settings = ({"output_enabled": True}, [])
    assert output.osc_cant_send_text("gone", settings) == (
        "OSC target gone is not Found."
    )
    assert output.osc_cant_send_text("gone", settings, "") == (
        "OSC target gone is not Found."
    )


def test_setting_another_id_takes_that_targets_name(osc: dict) -> None:
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    action.target = "gone"  # no such target: no stale "Mixer"
    assert action.target_name == ""
    action.target = "t1"
    assert action.target_name == "Mixer"


def test_load_and_save_refresh_a_renamed_target(osc: dict) -> None:
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    osc["write"]([{"id": "t1", "name": "Desk", "host": "127.0.0.1", "port": 9000}])
    # Saved while the old name was held: the current name is written.
    assert _saved_name(action) == "Desk"
    # Loaded with a stale saved name: the current name wins.
    action.target_name = "Old"
    node = action.to_xml()
    for prop in node.iter("property"):
        if prop.findtext("name") == "target-name":
            prop.find("value").text = "Old"  # type: ignore[union-attr]
    loaded = SendOscData(B)
    loaded.from_xml(ElementTree.fromstring(ElementTree.tostring(node)), Library())
    assert loaded.target_name == "Desk"


@pytest.fixture
def make_model() -> Iterator[Callable[[object], tuple]]:
    """(binding model, the action's model) for an action, deleted after the
    test: unparented (the program parents it), it would stay alive and
    connected to the program's signals (to-do 133)."""
    import shiboken6

    from gremlin.ui.profile import InputItemBindingModel

    made: list[InputItemBindingModel] = []

    def make(action: object) -> tuple:
        profile = Profile()
        item = InputItem(profile.library)
        binding = InputItemBinding(item)
        binding.root_action = RootData(B)
        binding.behavior = B
        profile.library.add_action(binding.root_action)
        profile.library.add_action(action)
        binding.root_action.insert_action(action, "children")
        model = InputItemBindingModel(binding)
        made.append(model)
        am = next(
            m for m in model._action_models.values() if m.action_data is action
        )
        return model, am

    yield make
    for model in made:
        if shiboken6.isValid(model):
            shiboken6.delete(model)


def test_open_editor_follows_a_rename_and_shows_the_name(
    osc: dict, make_model: Callable[[object], tuple]
) -> None:
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    _keep, am = make_model(action)
    seen: list[bool] = []
    am.targetChanged.connect(lambda: seen.append(True))
    osc_device_file.write_targets(
        [{"id": "t1", "name": "Desk", "host": "127.0.0.1", "port": 9000}]
    )
    assert seen, "the open editor wasn't told of the rename"
    assert action.target_name == "Desk"
    osc_device_file.write_targets([])
    assert am.cantSendText == "OSC target Desk is not Found."
    assert am.targetChoices[-1] == {"id": "t1", "name": "Desk"}


def test_missing_with_no_name_still_says_missing_target(
    osc: dict, make_model: Callable[[object], tuple]
) -> None:
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    action.target = "gone"
    _keep, am = make_model(action)
    assert am.targetChoices[-1] == {"id": "gone", "name": "Missing target"}
    assert am.cantSendText == "OSC target gone is not Found."


def test_reference_why_uses_the_saved_name(osc: dict) -> None:
    """The rows, Home card and Find tick (the sends-output Reference.why)."""
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    osc["write"]([])
    assert [ref.why for ref in action.references() if ref.why] == [
        "OSC target Mixer is not Found."
    ]
