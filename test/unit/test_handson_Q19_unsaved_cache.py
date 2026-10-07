# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 Q19 (D-04-Q19, GL-153): the title's "*" was worked out by rebuilding
the whole profile XML every 1.5 s while the window is in front (78-126 ms
for 1,580 actions on the main thread). It now reuses its last answer while
no edit was noted; every kind of edit still shows the "*", a save clears
it, and the Save / Discard / Cancel questions still compare exactly.

The old code had no cheap check: Profile.looks_unsaved and
Backend.profileLooksUnsaved did not exist and Main.qml polled the exact
check."""

from __future__ import annotations

import pathlib
import sys
import time
import uuid
from collections.abc import Callable

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import shared_state
from gremlin.profile import InputItem, Profile, VirtualAxisButton
from gremlin.types import InputType
from gremlin.ui.backend import Backend
from gremlin.ui.profile import InputItemBindingModel

_GUID = uuid.UUID("{11111111-2222-3333-4444-555555555555}")
_OTHER = uuid.UUID("{66666666-7777-8888-9999-000000000000}")

SCRIPT = (
    "import gremlin.user_script as us\n"
    "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n"
)


@pytest.fixture(scope="session", autouse=True)
def terminate_event_listener(request: pytest.FixtureRequest) -> None:
    import gremlin.event_handler

    request.addfinalizer(lambda: gremlin.event_handler.EventListener().terminate())


@pytest.fixture(autouse=True)
def no_history(monkeypatch: pytest.MonkeyPatch) -> None:
    # A save queues a History entry on its writer thread: not needed here.
    from gremlin import history_profile

    monkeypatch.setattr(history_profile, "record_save", lambda *a, **k: None)


_KEEP: list[QtCore.QObject] = []


class _Item(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__()
        self.enumeration_index = 0


class _Counted:
    """Counts the expensive whole-profile builds of one profile."""

    def __init__(self, profile: Profile, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls = 0
        real = profile._xml_text

        def counted() -> str:
            self.calls += 1
            return real()

        monkeypatch.setattr(profile, "_xml_text", counted)


def _process_until(done: Callable[[], bool], limit: float = 5.0) -> None:
    app = QtCore.QCoreApplication.instance()
    assert app is not None
    deadline = time.monotonic() + limit
    while not done():
        if time.monotonic() > deadline:
            raise TimeoutError("waited too long")
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


def _saved_profile(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, inputs: int = 3
) -> tuple[Profile, pathlib.Path]:
    """A saved profile with a Description on each of `inputs` buttons and a
    second mode, read back from its file."""
    path = tmp_path / "big.xml"
    source = Profile()
    monkeypatch.setattr(shared_state, "current_profile", source)
    source.modes.add_mode("Combat")
    for button in range(1, inputs + 1):
        item = source.get_input_item(
            _GUID, InputType.JoystickButton, button, "Default", create_if_missing=True
        )
        assert item is not None
        binding = item.add_item_binding()
        action = source.library.create("Description", InputType.JoystickButton)
        action.description = f"Button {button}"
        binding.root_action.insert_action(action, "children")
    source.to_xml(path)
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    profile.from_xml(path)
    return profile, path


def _first_item(profile: Profile) -> InputItem:
    item = profile.get_input_item(_GUID, InputType.JoystickButton, 1, "Default")
    assert item is not None
    return item


# --- cheap while nothing changes ----------------------------------------------


def test_title_check_does_not_rebuild_an_unedited_large_profile(
    qapp: QtCore.QCoreApplication,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile, _ = _saved_profile(tmp_path, monkeypatch, inputs=400)
    built = _Counted(profile, monkeypatch)
    for _ in range(20):
        # As the 1.5 s title timer does, with the event loop running between.
        qapp.processEvents()
        assert profile.looks_unsaved() is False
    assert built.calls == 0, f"{built.calls} whole-profile builds for 20 polls"

    # One edit: one build, then the answer is reused again.
    _first_item(profile).action_name = "Gear"
    for _ in range(5):
        assert profile.looks_unsaved() is True
    assert built.calls == 1


def test_backend_title_property_uses_the_cheap_check(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, _ = _saved_profile(tmp_path, monkeypatch)
    built = _Counted(profile, monkeypatch)
    fake = type("B", (), {"profile": profile})()
    for _ in range(5):
        assert Backend.klass.profileLooksUnsaved.fget(fake) is False  # type: ignore[attr-defined]
    assert built.calls == 0
    # The questions' property always compares.
    assert Backend.klass.profileContainsUnsavedChanges.fget(fake) is False  # type: ignore[attr-defined]
    assert built.calls == 1


def test_main_window_title_polls_the_cheap_check_and_questions_the_exact() -> None:
    main = pathlib.Path(__file__).parents[2] / "qml" / "Main.qml"
    text = main.read_text(encoding="utf-8")
    poll = text[text.index("function refreshProfileDirty()") :]
    poll = poll[: poll.index("}")]
    assert "backend.profileLooksUnsaved" in poll
    assert "profileContainsUnsavedChanges" not in poll
    # Quit and the save question still ask the exact one.
    assert text.count("backend.profileContainsUnsavedChanges") >= 2


# --- every kind of edit still shows the "*" -------------------------------------


def _pane_description(profile: Profile, value: str) -> None:
    item = _first_item(profile)
    owner = _Item()
    model = InputItemBindingModel(item.action_sequences[0], owner)
    _KEEP.extend([owner, model])
    pane = model.rootAction.getActions("children")[0]
    pane.description = value


def _pane_add_action(profile: Profile) -> None:
    item = _first_item(profile)
    owner = _Item()
    model = InputItemBindingModel(item.action_sequences[0], owner)
    _KEEP.extend([owner, model])
    model.rootAction.appendAction("Description", "children")


def _remove_binding(profile: Profile) -> None:
    item = _first_item(profile)
    item.remove_item_binding(item.action_sequences[0])


def _binding_behavior(profile: Profile) -> None:
    binding = _first_item(profile).action_sequences[0]
    binding.behavior = InputType.JoystickAxis
    binding.virtual_button = VirtualAxisButton()


def _virtual_button_limit(profile: Profile) -> None:
    item = profile.get_input_item(
        _GUID, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    assert item is not None
    binding = item.add_item_binding()
    # An axis acting as a button: its range is the virtual button.
    binding.behavior = InputType.JoystickButton
    binding.virtual_button = VirtualAxisButton()
    action = profile.library.create("Description", InputType.JoystickButton)
    binding.root_action.insert_action(action, "children")
    profile.to_xml(profile.fpath)
    assert not profile.looks_unsaved()
    binding.virtual_button.lower_limit = -0.5


def _vjoy_initial(profile: Profile) -> None:
    profile.settings.set_initial_vjoy_axis_value(1, 1, 0.5)


def _logical_row(profile: Profile) -> None:
    profile.logical_device.create(InputType.JoystickButton)


def _swap(profile: Profile) -> None:
    profile.swap_device_inputs(_GUID, _OTHER)


EDITS: dict[str, Callable[[Profile], None]] = {
    "action property in the pane": lambda p: _pane_description(p, "Gear up"),
    "action property set directly": lambda p: setattr(
        _first_item(p).action_sequences[0].root_action.get_actions()[0][0],
        "description",
        "Flaps",
    ),
    "add action": _pane_add_action,
    "remove binding": _remove_binding,
    "binding behavior": _binding_behavior,
    "virtual button limit": _virtual_button_limit,
    "input name": lambda p: setattr(_first_item(p), "action_name", "Gear"),
    "mode add": lambda p: p.modes.add_mode("Landing"),
    "mode rename": lambda p: p.modes.rename_mode("Combat", "Fight"),
    "mode delete": lambda p: p.modes.delete_mode("Combat"),
    "startup mode": lambda p: setattr(p.settings, "startup_mode", "Combat"),
    "macro delay": lambda p: setattr(p.settings, "macro_default_delay", 0.5),
    "vjoy initial value": _vjoy_initial,
    "logical row": _logical_row,
    "swap devices": _swap,
}


@pytest.mark.parametrize("kind", list(EDITS))
def test_each_kind_of_edit_shows_unsaved_and_save_clears_it(
    qapp: QtCore.QCoreApplication,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    profile, path = _saved_profile(tmp_path, monkeypatch)
    assert profile.looks_unsaved() is False
    EDITS[kind](profile)
    qapp.processEvents()
    assert profile.looks_unsaved() is True, kind
    assert profile.has_unsaved_changes() is True, kind
    profile.to_xml(path)
    built = _Counted(profile, monkeypatch)
    assert profile.looks_unsaved() is False
    assert built.calls == 0, "a save is the new baseline: nothing to rebuild"


def test_script_setting_edit_shows_unsaved(
    qapp: QtCore.QCoreApplication,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_path = tmp_path / "throttle.py"
    script_path.write_text(SCRIPT, encoding="utf-8")
    source = Profile()
    monkeypatch.setattr(shared_state, "current_profile", source)
    source.scripts.add_script(script_path)
    source.scripts.scripts[0].variables["speed"].value = 7
    path = tmp_path / "script.xml"
    source.to_xml(path)

    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    profile.from_xml(path)
    script = profile.scripts.scripts[0]
    # A script that finishes starting shows nothing unsaved (D-04-Q13-NOWAIT).
    _process_until(lambda: not script.starting)
    assert profile.looks_unsaved() is False
    assert profile.has_unsaved_changes() is False

    script.variables["speed"].value = 3
    assert profile.looks_unsaved() is True
    profile.to_xml(path)
    assert profile.looks_unsaved() is False

    profile.scripts.rename_script(script.path, script.name, "Second")
    assert profile.looks_unsaved() is True


# --- the questions never miss an edit -----------------------------------------


def test_an_edit_no_hook_sees_is_still_caught_by_the_questions(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, _ = _saved_profile(tmp_path, monkeypatch)
    assert profile.looks_unsaved() is False
    action = _first_item(profile).action_sequences[0].root_action.get_actions()[0][0]
    # Behind every hook's back.
    vars(action)["description"] = "Sneaky"
    # The title may be late ...
    assert profile.looks_unsaved() is False
    # ... but Save / Discard / Cancel compare exactly, and then the title
    # follows.
    fake = type("B", (), {"profile": profile})()
    assert Backend.klass.profileContainsUnsavedChanges.fget(fake) is True  # type: ignore[attr-defined]
    assert profile.looks_unsaved() is True
