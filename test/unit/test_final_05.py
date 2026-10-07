# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final phase, page 05 (actions and their editors): statements with no
check before (claude/final-test-plan/05-actions-editors.md).

Each test names the spec statement it checks. Off-screen, fakes only:
nothing reaches vJoy, ViGEm, the mouse or the keyboard.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree

sys.path.append(".")

import pytest
from PySide6 import QtCore

from action_plugins.root import RootData
from gremlin import plugin_manager, shared_state
from gremlin.base_classes import AbstractFunctor, Value
from gremlin.event_handler import Event
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.types import ActionActivationMode, InputType

_STICK = uuid.UUID("05050505-0505-0505-0505-050505050505")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def profile() -> Iterator[Profile]:
    old = shared_state.current_profile
    shared_state.current_profile = Profile()
    yield shared_state.current_profile
    shared_state.current_profile = old


def _vjoy(out: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _map(
    profile: Profile, button: int, out: int, mode: str = "Default"
) -> Any:  # noqa: ANN401
    item: Any = profile.get_input_item(
        _STICK, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    action = _vjoy(out)
    item.add_item_binding().root_action.insert_action(action, "children")
    return action


def _outs(item: Any) -> list[int]:  # noqa: ANN401
    if item is None:
        return []
    return [
        b.root_action.get_actions()[0][0].vjoy_input_id for b in item.action_sequences
    ]


# --- A. Which actions are offered (S4, S5, S6, S7) ---------------------------


def _offered(input_type: InputType, behavior: InputType) -> list[str]:
    """The Add Action list of a new binding on such an input."""
    from gremlin.ui.profile import InputItemBindingModel

    library = Profile().library
    item = InputItem(library)
    item.input_type = input_type
    binding = InputItemBinding(item)
    binding.root_action = RootData(behavior)
    binding.behavior = behavior
    library.add_action(binding.root_action)
    model = InputItemBindingModel(binding)
    root: Any = model.get_action_model_by_sidx(0)
    return list(root.compatibleActions)


def test_s4_add_action_lists_only_actions_that_suit_the_input() -> None:
    axis = _offered(InputType.JoystickAxis, InputType.JoystickAxis)
    button = _offered(InputType.JoystickButton, InputType.JoystickButton)
    hat = _offered(InputType.JoystickHat, InputType.JoystickHat)
    assert "Response Curve" in axis and "Map to Keyboard" not in axis
    assert "Map to Keyboard" in button and "Response Curve" not in button
    assert "Hat as Buttons" in hat and "Response Curve" not in hat
    for kind, names in (("axis", axis), ("button", button), ("hat", hat)):
        manager = plugin_manager.PluginManager()
        allowed = {
            p.name
            for p in manager.type_action_map[InputType.to_enum(kind)]
        }
        assert set(names) <= allowed, kind


@pytest.mark.parametrize(
    ("input_type", "behavior"),
    [
        (InputType.Keyboard, InputType.Keyboard),
        (InputType.JoystickAxis, InputType.JoystickButton),
        (InputType.JoystickHat, InputType.JoystickButton),
    ],
    ids=["key", "axis-as-button", "hat-as-button"],
)
def test_s5_keys_and_inputs_treated_as_buttons_get_the_button_actions(
    input_type: InputType, behavior: InputType
) -> None:
    offered = _offered(input_type, behavior)
    buttons = _offered(InputType.JoystickButton, InputType.JoystickButton)
    assert set(offered) == set(buttons)
    assert "Map to Keyboard" in offered and "Text to Speech" in offered
    assert "Response Curve" not in offered


def test_s6_root_is_never_offered() -> None:
    kinds = (InputType.JoystickAxis, InputType.JoystickButton, InputType.JoystickHat)
    for kind in kinds:
        assert "Root" not in _offered(kind, kind)


def test_s7_new_plugins_join_the_list_shown_and_gone_ones_leave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gremlin.config
    import joystick_gremlin

    saved: dict[str, Any] = {}
    stored = [["A Plugin No Longer Here", True], ["Macro", False]]
    fake = SimpleNamespace(
        exists=lambda *_k: True,
        value=lambda *_k: stored,
        set=lambda *k: saved.__setitem__("value", k[-1]),
    )
    monkeypatch.setattr(gremlin.config, "Configuration", lambda: fake)
    joystick_gremlin.update_action_priorities()

    result = {name: shown for name, shown in saved["value"]}
    assert "A Plugin No Longer Here" not in result
    assert result["Macro"] is False  # hidden stays hidden
    names = {p.name for p in plugin_manager.PluginManager().repository.values()}
    assert set(result) == names
    assert result["Map to vJoy"] is True and result["Response Curve"] is True


# --- B. Configuration page list (S12, S15, S43) -------------------------------


@pytest.fixture
def catalog(profile: Profile) -> Iterator[tuple[Any, Profile]]:
    """The Configuration page on a stick whose buttons 1-3 are claimed."""
    from gremlin.ui.binding_catalog import BindingCatalogModel

    profile.modes.add_mode("Combat")
    model: Any = BindingCatalogModel()
    model._claimed._device = SimpleNamespace(device_guid=SimpleNamespace(uuid=_STICK))
    model._claimed._rows = [
        {"kind": "button", "hwId": n, "deviceIndex": n - 1, "name": f"Button {n}"}
        for n in (1, 2, 3)
    ]
    yield model, profile
    model.endPane()
    model.deleteLater()


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    model._rebuild()
    return list(model._rows)


def test_s12_the_list_shows_claimed_inputs_in_the_toolbars_mode(
    catalog: tuple[Any, Profile],
) -> None:
    model, profile = catalog
    _map(profile, 1, 1)
    _map(profile, 1, 2)
    _map(profile, 1, 7, "Combat")
    _map(profile, 9, 9)  # not claimed: never listed
    rows = _rows(model)
    names = [r["name"] for r in rows if r["rowKind"] == "group"]
    assert names == ["Button 1", "Button 2", "Button 3"]
    assert [r["sequenceIndex"] for r in rows if r["rowKind"] == "leaf"] == [0, 1]
    model._claimed._mode = "Combat"
    rows = _rows(model)
    leaves = [r for r in rows if r["rowKind"] == "leaf"]
    assert len(leaves) == 1 and leaves[0]["name"] == "Button 1"


def test_s15_inputs_with_no_actions_go_together_under_no_actions(
    catalog: tuple[Any, Profile],
) -> None:
    model, profile = catalog
    _map(profile, 2, 4)
    rows = _rows(model)
    assert rows[0]["name"] == "Button 1" and rows[0]["summary"] == "No actions"
    model.parkEmptyInUnmapped = True
    rows = _rows(model)
    kinds = [(r["rowKind"], r["name"]) for r in rows]
    assert kinds == [
        ("group", "Button 2"),
        ("leaf", "Button 2"),
        ("unmapped-header", "No actions"),
        ("unmapped", "Button 1"),
        ("unmapped", "Button 3"),
    ]


def test_s43_the_note_shows_on_the_inputs_row(catalog: tuple[Any, Profile]) -> None:
    model, profile = catalog
    _map(profile, 1, 1)
    item = _real(profile)
    item.action_sequences[0].root_action.action_label = "Gear lever"
    rows = [r for r in _rows(model) if r["name"] == "Button 1"]
    texts = " ".join(
        str(r.get(key, ""))
        for r in rows
        for key in ("summary", "destLabel", "typeLabel")
    )
    assert "Gear lever" in texts


# --- C. The action pane (S20, S22, S23, S24) and D. Undo (S35, S36, S37) ----


@pytest.fixture
def pane(profile: Profile) -> Iterator[tuple[Any, Profile]]:
    """The Configuration page with button 1 mapped to vJoy buttons 1 and 2."""
    from gremlin.ui.binding_catalog import BindingCatalogModel

    _map(profile, 1, 1)
    _map(profile, 1, 2)
    model: Any = BindingCatalogModel()

    def spec(_index: int) -> tuple:
        real = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
        return profile, _STICK, InputType.JoystickButton, 1, "Default", real

    model._control_spec = spec
    yield model, profile
    model.endPane()
    model.deleteLater()


def _real(profile: Profile) -> Any:  # noqa: ANN401
    return profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")


def _pane_first(model: Any, seq: int = 0) -> Any:  # noqa: ANN401
    return model._pane_shadow.action_sequences[seq].root_action.get_actions()[0][0]


def test_s20_a_parent_opens_every_action_a_child_only_its_own(
    pane: tuple[Any, Profile],
) -> None:
    model, _profile = pane
    assert model.beginPane(0, -1) == 2
    assert [b.root_action.get_actions()[0][0].vjoy_input_id
            for b in model._pane_shadow.action_sequences] == [1, 2]
    model.beginPane(0, 1)
    assert len(model._pane_shadow.action_sequences) == 1
    assert _pane_first(model).vjoy_input_id == 2


def test_s22_ok_writes_keeps_the_profile_unsaved_and_the_pane_on_a_new_copy(
    pane: tuple[Any, Profile], tmp_path: Path
) -> None:
    model, profile = pane
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    on_disk = path.read_bytes()
    assert not profile.has_unsaved_changes()

    model.beginPane(0, -1)
    old_shadow = model._pane_shadow
    _pane_first(model).vjoy_input_id = 8
    model.commitPane()
    assert _outs(_real(profile)) == [8, 2]
    assert profile.has_unsaved_changes()
    assert path.read_bytes() == on_disk  # File > Save writes, OK does not
    # Still open, on a fresh copy: editing it doesn't reach the input.
    assert model._pane_shadow is not None and model._pane_shadow is not old_shadow
    _pane_first(model).vjoy_input_id = 9
    assert _outs(_real(profile)) == [8, 2]


def test_s23_close_after_ok_and_the_pane_width_are_remembered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import config, history
    from gremlin.common import SingletonMetaclass
    from gremlin.ui.window_placement import WindowPlacement

    settings = str(tmp_path / "configuration.json")
    monkeypatch.setattr(config, "_config_file_path", settings)
    monkeypatch.setattr(history, "record", lambda *_a, **_k: None)
    SingletonMetaclass._instances.pop(config.Configuration, None)
    first = WindowPlacement()
    first.setClosePaneAfterOk(True)
    first.setActionPaneWidth(700)
    config.Configuration().save_now()
    first.deleteLater()

    # The next session reads the file again.
    SingletonMetaclass._instances.pop(config.Configuration, None)
    again = WindowPlacement()
    assert again.closePaneAfterOk() is True
    assert again.actionPaneWidth() == 700
    again.deleteLater()


def test_s24_ok_with_nothing_changed_makes_no_undo_step(
    pane: tuple[Any, Profile],
) -> None:
    model, profile = pane
    model.beginPane(0, -1)
    assert not model.paneDirty()
    model.commitPane()
    model.endPane()
    assert not model.canUndo
    assert _outs(_real(profile)) == [1, 2]


def test_s35_undo_keeps_the_last_fifty_steps(pane: tuple[Any, Profile]) -> None:
    model, profile = pane
    for step in range(55):
        before = model._snapshot(0)
        action = _real(profile).action_sequences[0].root_action.get_actions()[0][0]
        action.vjoy_input_id = 10 + step
        model._step(0, before)
    assert len(model._undo) == model.UNDO_STEPS == 50
    for _ in range(50):
        model.undo()
    assert not model.canUndo
    # The oldest step kept is the sixth change (14 -> 15).
    assert _outs(_real(profile))[0] == 14


def test_s36_undo_waits_while_an_action_is_open_in_the_pane(
    pane: tuple[Any, Profile],
) -> None:
    model, profile = pane
    model.beginPane(0, -1)
    _pane_first(model).vjoy_input_id = 8
    model.commitPane()
    assert not model.canUndo
    model.undo()
    assert _outs(_real(profile)) == [8, 2]  # nothing put back
    model.endPane()
    model.undo()
    assert _outs(_real(profile)) == [1, 2]


def test_s37_another_device_starts_with_no_steps(pane: tuple[Any, Profile]) -> None:
    model, profile = pane
    before = model._snapshot(0)
    binding = _real(profile).action_sequences[0]
    _real(profile).remove_item_binding(binding)
    profile.library.release([binding.root_action])  # as the list's Delete does
    model._step(0, before)
    assert model.canUndo
    model.guid = str(uuid.uuid4())
    assert not model.canUndo and not model.canRedo


# --- E. Editing inside an action (S44, S55) ------------------------------------


def test_s44_both_switches_off_is_saved_and_never_runs(profile: Profile) -> None:
    from action_plugins.map_to_mouse import MapToMouseData

    action = MapToMouseData(InputType.JoystickButton)
    action.activation_mode = ActionActivationMode.Deactivated
    node = action.to_xml()
    assert node is not None
    loaded = MapToMouseData(InputType.JoystickButton)
    loaded.from_xml(node, profile.library)
    assert loaded.activation_mode == ActionActivationMode.Deactivated
    runner: Any = SimpleNamespace(data=loaded)
    assert not AbstractFunctor._should_execute(runner, Value(True))
    assert not AbstractFunctor._should_execute(runner, Value(False))


@pytest.mark.parametrize(
    ("module", "cls", "fields"),
    [
        ("description", "DescriptionData", ("description",)),
        ("run_command", "RunCommandData", ("executable", "arguments")),
        ("text_to_speech", "TextToSpeechData", ("text",)),
    ],
)
def test_s55_an_empty_text_field_reloads_empty(
    profile: Profile, module: str, cls: str, fields: tuple[str, ...]
) -> None:
    import importlib

    data_class = getattr(importlib.import_module(f"action_plugins.{module}"), cls)
    action = data_class(InputType.JoystickButton)
    for field in fields:
        setattr(action, field, "")
    saved = ElementTree.tostring(action.to_xml(keep_invalid=True))
    loaded = data_class(InputType.JoystickButton)
    loaded.from_xml(ElementTree.fromstring(saved), profile.library)
    for field in fields:
        assert getattr(loaded, field) == "", field


# --- I. At Run (S80, S83, S86, S98, S103, Q19) -----------------------------------


def test_s80_later_actions_see_the_value_response_curve_made() -> None:
    from action_plugins.response_curve import ResponseCurveData
    from action_plugins.root import RootFunctor
    from gremlin import spline

    curve = ResponseCurveData(InputType.JoystickAxis)
    curve.curve = spline.PiecewiseLinear([(-1.0, 1.0), (1.0, -1.0)])  # inverts
    root = RootData(InputType.JoystickAxis)
    root.insert_action(curve, "children")
    functor = RootFunctor(root)
    seen: list[float] = []
    functor.functors["children"].append(
        lambda _event, value, _props=None: seen.append(value.current)
    )
    event = Event(InputType.JoystickAxis, 1, _STICK, "Default", value=0.5)
    functor(event, Value(0.5))
    assert seen == [pytest.approx(-0.5)]


def test_s83_relative_moves_at_speed_and_stops_a_second_after_the_input_rests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.common import RelativeAxisLoop
    from gremlin import clock, run_scope

    now = [1000.0]
    monkeypatch.setattr(clock, "now", lambda: now[0])
    monkeypatch.setattr(clock, "sleep", lambda s: now.__setitem__(0, now[0] + s))
    monkeypatch.setattr(run_scope, "alive", lambda _run: True)
    monkeypatch.setattr(run_scope, "loop", lambda *_a, **_k: None)  # run below

    class Axis(RelativeAxisLoop):
        def __init__(self) -> None:
            self._init_relative()
            self.value = 0.0
            self.writes: list[float] = []

        def _relative_read(self) -> float:
            return self.value

        def _relative_write(self, value: float) -> bool:
            self.writes.append(value)
            self.value = value
            if len(self.writes) == 30:
                self._relative_input(0.0, 0.0, 100.0)  # the stick is let go
            if len(self.writes) > 1000:  # bound: the loop should have ended
                self._ask_to_stop()
            return True

    axis = Axis()
    axis._relative_input(0.5, 0.5, 100.0)  # half way: 0.05 per step
    assert axis.thread_running
    axis.relative_axis_thread(1, axis._loop_token)

    assert axis.writes[:20] == pytest.approx([0.05 * n for n in range(1, 21)])
    assert axis.writes[20:30] == pytest.approx([1.0] * 10)
    assert not axis.thread_running
    resting = len(axis.writes) - 30  # steps of 10 ms after the stick rested
    assert 95 <= resting <= 105


def test_s86_the_mouse_wheel_turns_once_per_press(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.map_to_mouse import MapToMouseData, MapToMouseFunctor
    from gremlin import sendinput
    from gremlin.types import MouseButton

    turns: list[int] = []
    monkeypatch.setattr(sendinput, "MouseController", lambda: SimpleNamespace())
    monkeypatch.setattr(sendinput, "mouse_wheel", turns.append)
    monkeypatch.setattr(sendinput, "mouse_press", lambda *_a: pytest.fail("press"))
    monkeypatch.setattr(sendinput, "mouse_release", lambda *_a: pytest.fail("release"))
    data = MapToMouseData(InputType.JoystickButton)
    data.button = MouseButton.WheelUp
    functor = MapToMouseFunctor(data)
    for pressed in (True, False, True, False):
        event = Event(
            InputType.JoystickButton, 1, _STICK, "Default", is_pressed=pressed
        )
        functor(event, Value(pressed))
    assert turns == [-1, -1]


def test_s98_description_does_nothing_when_the_input_fires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.description import DescriptionData, DescriptionFunctor
    from gremlin import sendinput

    for name in ("mouse_wheel", "mouse_press", "mouse_release", "send_key_down"):
        if hasattr(sendinput, name):
            monkeypatch.setattr(sendinput, name, lambda *_a: pytest.fail(name))
    data = DescriptionData(InputType.JoystickButton)
    data.description = "a note"
    functor = DescriptionFunctor(data)
    value = Value(True)
    event = Event(InputType.JoystickButton, 1, _STICK, "Default", is_pressed=True)
    functor(event, value)
    assert value.current is True and functor.functors == {}


def test_s103_map_to_xbox_without_vigem_warns_and_stays_in_the_profile(
    profile: Profile, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.base_classes import UserFeedback
    from gremlin.modules import output

    monkeypatch.setattr(output, "xbox_available", lambda: False)
    action = plugin_manager.PluginManager().create_instance(
        "Map to Xbox", InputType.JoystickButton
    )
    feedback = action.user_feedback()
    assert [f.feedback_type for f in feedback] == [UserFeedback.FeedbackType.Warning]
    assert "ViGEmBus" in feedback[0].message
    assert action.is_valid()
    item: Any = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")
    path = tmp_path / "x.xml"
    profile.to_xml(path)
    assert "map-to-xbox" in path.read_text(encoding="utf-8")


def test_q19_chain_times_out_on_the_program_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.chain import ChainData, ChainFunctor
    from gremlin import clock

    now = [1000.0]
    monkeypatch.setattr(clock, "now", lambda: now[0])
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    data = ChainData(InputType.JoystickButton)
    data.timeout = 1.0
    functor = ChainFunctor(data)
    data.chain_sequences = [[], []]
    ran: list[int] = []
    functor.functors = {
        "0": [lambda _e, v, _p=None: v.current and ran.append(0)],
        "1": [lambda _e, v, _p=None: v.current and ran.append(1)],
    }

    def press_and_release() -> None:
        for pressed in (True, False):
            event = Event(
                InputType.JoystickButton, 1, _STICK, "Default", is_pressed=pressed
            )
            functor(event, Value(pressed))

    press_and_release()
    now[0] += 5.0  # past the timeout on the program clock
    press_and_release()
    assert ran == [0, 0]


# --- Q16, Q18: layer rule and unused code ----------------------------------------


def test_q16_map_to_xbox_takes_its_types_from_the_output_module() -> None:
    import ast

    import action_plugins.map_to_xbox as plugin
    from gremlin.modules import output

    tree = ast.parse(Path(str(plugin.__file__)).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.split(".")[0] == "vigem" for name in imported), imported
    assert plugin.XboxTarget is output.XboxTarget


def test_q18_the_unused_editor_code_is_gone() -> None:
    from gremlin.ui import action_model
    from gremlin.ui.profile import InputItemModel

    assert not hasattr(InputItemModel, "newActionSequence")
    assert not hasattr(action_model, "ActionPriorityListModel")
