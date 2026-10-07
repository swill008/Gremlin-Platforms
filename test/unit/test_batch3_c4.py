# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Batch 3, actions (C4): GL-217, GL-244, GL-255, GL-256, GL-257, GL-259
(comment only), GL-260, GL-261, GL-262, GL-263, GL-264 and the unused
MergeAxisData._do_create."""

from __future__ import annotations

import ast
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from action_plugins.root import RootData
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.types import InputType

_ROOT = Path(__file__).resolve().parents[2]
_STICK = uuid.UUID("{11111111-2222-3333-4444-555555555555}")


def _binding_model(*children: Any) -> Any:  # noqa: ANN401
    from gremlin.ui.profile import InputItemBindingModel

    profile = Profile()
    item = InputItem(profile.library)
    item.device_id = _STICK
    item.input_type = InputType.JoystickAxis
    item.input_id = 1
    binding = InputItemBinding(item)
    binding.root_action = RootData(InputType.JoystickAxis)
    binding.behavior = InputType.JoystickAxis
    profile.library.add_action(binding.root_action)
    for child in children:
        profile.library.add_action(child)
        binding.root_action.insert_action(child, "children")
    return InputItemBindingModel(binding)


def _model_of(binding_model: Any, data: Any) -> Any:  # noqa: ANN401
    return next(
        m for m in binding_model._action_models.values() if m.action_data is data
    )


# --- GL-217 / GL-257: the Configuration list's words (05 S14, S15, Q6) ------


def _catalog_texts() -> list[str]:
    tree = ast.parse((_ROOT / "gremlin/ui/binding_catalog.py").read_text("utf-8"))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_the_configuration_list_says_no_actions() -> None:
    texts = _catalog_texts()
    assert "Unmapped" not in texts
    assert "Sequence" not in texts and "Empty" not in texts
    assert not any("assignment" in text for text in texts)


def test_an_empty_wrapper_shows_its_name_and_no_actions() -> None:
    from action_plugins.tempo import TempoData
    from gremlin.ui.binding_catalog import sequences_for_item

    tempo = TempoData(InputType.JoystickButton)
    root = RootData(InputType.JoystickButton)
    root.insert_action(tempo, "children")
    item = SimpleNamespace(action_sequences=[SimpleNamespace(root_action=root)])
    assert sequences_for_item(item) == [(0, "Tempo", "No actions")]


def test_the_action_count_reads_actions() -> None:
    from gremlin.ui.binding_catalog import assignment_summary

    one = assignment_summary([(0, "Map to vJoy", "vJoy 1 · Button 1")])
    assert one == ("1 action — vJoy 1 · Button 1", "vJoy 1 · Button 1")
    two = assignment_summary([(0, "", "A"), (1, "", "B")])
    assert two[0] == "2 actions — A, B"


def test_type_names_are_the_plugins_names() -> None:
    from gremlin.plugin_manager import PluginManager
    from gremlin.ui.binding_catalog import summarize_action, type_filter_names

    plugins = PluginManager().tag_map
    names = type_filter_names()
    assert names[0] == "All types" and names[-2:] == ["Other", "No actions"]
    for tag in ("map-to-vjoy", "map-to-keyboard", "map-to-mouse", "map-to-xbox",
                "macro", "change-mode"):
        assert plugins[tag].name in names
    pause = plugins["pause-resume"](InputType.JoystickButton)
    assert summarize_action(pause)[0] == "Pause and Resume"


def test_the_type_box_reads_its_names_from_the_model() -> None:
    qml = (_ROOT / "qml/BindingCatalog.qml").read_text("utf-8")
    assert "model: _catalog.typeFilterNames" in qml
    assert '"Map to keyboard"' not in qml


def test_action_kinds_name_real_actions() -> None:
    import re

    from gremlin.plugin_manager import PluginManager

    js = (_ROOT / "qml/action_kinds.js").read_text("utf-8")
    block = js[js.index("var kinds = {"): js.index("}", js.index("var kinds = {"))]
    named = set(re.findall(r'"([^"]+)":', block))
    plugins = {p.name for p in PluginManager().tag_map.values()}
    assert named and named <= plugins, named - plugins


# --- GL-261: unused catalog code (05 Q18) ------------------------------------


def test_the_quick_editor_is_gone() -> None:
    from gremlin.ui.binding_catalog import BindingCatalogModel

    for name in ("vjoyDevices", "addSequence", "noteOpenRow", "refreshOpenRow"):
        assert not hasattr(BindingCatalogModel, name), name
    qml = (_ROOT / "qml/BindingCatalog.qml").read_text("utf-8")
    for word in ("openSequence", "editingHid", "quickHid", "armReveal"):
        assert word not in qml, word


# --- GL-255: a Map to Logical Device editor doesn't refresh the Logical page -


def test_opening_a_logical_editor_changes_nothing() -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData
    from gremlin.signal import signal

    fired: list[int] = []
    slot = lambda: fired.append(1)  # noqa: E731
    signal.logicalDeviceModified.connect(slot)
    try:
        _binding_model(MapToLogicalDeviceData(InputType.JoystickButton))
    finally:
        signal.logicalDeviceModified.disconnect(slot)
    assert fired == []


# --- GL-256: Xbox output has no claims (05 S54) ------------------------------


def test_no_claim_comment_on_xbox() -> None:
    text = (_ROOT / "action_plugins/map_to_xbox/__init__.py").read_text("utf-8")
    assert "passes only the controls it claims" not in text


# --- GL-260 / GL-263: plain axes in the data, one pick list ------------------


@pytest.mark.parametrize(
    ("module", "cls", "axes"),
    [
        ("merge_axis", "MergeAxisData", ("axis_in1", "axis_in2")),
        ("dual_axis_deadzone", "DualAxisDeadzoneData", ("axis1", "axis2")),
    ],
)
def test_axis_data_holds_no_qt_type(module: str, cls: str, axes: tuple) -> None:
    import importlib

    data_cls = getattr(importlib.import_module(f"action_plugins.{module}"), cls)
    data = data_cls(InputType.JoystickAxis)
    for name in axes:
        assert not isinstance(getattr(data, name), QtCore.QObject)
    copy = data.copy_unfinished()
    for name in axes:
        assert not isinstance(getattr(copy, name), QtCore.QObject)


@pytest.mark.parametrize(
    ("module", "cls", "prop", "attr"),
    [
        ("merge_axis", "MergeAxisData", "firstAxis", "axis_in1"),
        ("dual_axis_deadzone", "DualAxisDeadzoneData", "axis1", "axis1"),
    ],
)
def test_a_recorded_axis_is_a_copy(module: str, cls: str, prop: str, attr: str) -> None:
    import importlib

    from gremlin.ui.device import InputIdentifier

    data = getattr(importlib.import_module(f"action_plugins.{module}"), cls)(
        InputType.JoystickAxis
    )
    model = _model_of(_binding_model(data), data)
    current = InputIdentifier(_STICK, InputType.JoystickAxis, 3)
    model.setProperty(prop, current)
    current.input_id = 5  # the page's current input moves on
    stored = getattr(data, attr)
    assert not isinstance(stored, QtCore.QObject)
    assert (stored.device_guid, stored.input_id) == (_STICK, 3)
    shown = model._get_axis(1)  # what QML reads
    assert shown.input_id == 3 and model._get_axis(1) is shown


@pytest.mark.parametrize(
    ("module", "cls", "slot"),
    [
        ("merge_axis", "MergeAxisData", "newMergeAxis"),
        ("dual_axis_deadzone", "DualAxisDeadzoneData", "newDeadzone"),
    ],
)
def test_plus_numbers_after_the_action_name(module: str, cls: str, slot: str) -> None:
    import importlib

    data_cls = getattr(importlib.import_module(f"action_plugins.{module}"), cls)
    data = data_cls(InputType.JoystickAxis)
    data.label = f"{data_cls.name} 1"
    binding_model = _binding_model(data)
    model = _model_of(binding_model, data)
    getattr(model, slot)()
    library = binding_model.input_item_binding.library
    labels = {a.label for a in library.actions_by_type(data_cls)}
    assert f"{data_cls.name} 2" in labels


# --- MergeAxisData._do_create is gone; Library.create reuses ----------------


def test_merge_axis_reuse_goes_through_the_library() -> None:
    from action_plugins.merge_axis import MergeAxisData

    assert "_do_create" not in MergeAxisData.__dict__
    profile = Profile()
    old = profile.library.create(MergeAxisData.name, InputType.JoystickAxis)
    # Nothing uses it: a new one is made, not the unused one.
    fresh = profile.library.create(MergeAxisData.name, InputType.JoystickAxis)
    assert fresh is not old


# --- GL-262: one macro step table (05 RB13) ---------------------------------


def test_one_macro_step_table() -> None:
    from action_plugins.macro import MacroModel
    from gremlin import macro

    assert set(MacroModel.action_lookup) == set(macro.STEP_TYPES)
    for tag, step in macro.STEP_TYPES.items():
        assert step.tag == tag
        assert isinstance(MacroModel.action_lookup[tag](), step)
    text = (_ROOT / "action_plugins/macro/__init__.py").read_text("utf-8")
    assert "macro.PauseAction.create" not in text


# --- GL-264: one relative-axis loop (05 RB15) -------------------------------


def test_both_maps_share_the_relative_loop() -> None:
    from action_plugins.common import RelativeAxisLoop
    from action_plugins.map_to_logical_device import MapToLogicalDeviceFunctor
    from action_plugins.map_to_vjoy import MapToVjoyFunctor

    for functor in (MapToVjoyFunctor, MapToLogicalDeviceFunctor):
        assert issubclass(functor, RelativeAxisLoop)
        for name in ("relative_axis_thread", "_start_loop", "_current", "_end"):
            assert name not in functor.__dict__, (functor, name)


def test_the_relative_loop_stops_when_the_axis_is_moved_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.common import RelativeAxisLoop
    from gremlin import clock, run_scope

    class Axis(RelativeAxisLoop):
        def __init__(self) -> None:
            self._init_relative()
            self.value = 0.0
            self.writes: list[float] = []

        def _relative_read(self) -> float:
            return self.value

        def _relative_write(self, value: float) -> bool:
            self.writes.append(value)
            # Something else moves the axis after the second step.
            self.value = value if len(self.writes) < 2 else 0.9
            return True

    monkeypatch.setattr(clock, "sleep", lambda _s: None)
    monkeypatch.setattr(run_scope, "alive", lambda _run: True)
    axis = Axis()
    axis.axis_delta_value = 0.1
    axis.thread_running = True
    axis._loop_token = token = object()
    axis.relative_axis_thread(1, token)
    assert axis.writes == pytest.approx([0.1, 0.2])
    assert not axis.thread_running and axis.should_stop_thread


# --- GL-244: macro and Hat as Buttons events are marked synthetic -----------


def test_a_macro_joystick_step_is_synthetic() -> None:
    from gremlin import event_handler, macro

    got: list = []
    listener = event_handler.EventListener()
    listener.joystick_event.connect(got.append)
    try:
        macro.JoystickAction(_STICK, InputType.JoystickButton, 1, True)()
        macro.JoystickAction(_STICK, InputType.JoystickAxis, 1, 0.5)()
    finally:
        listener.joystick_event.disconnect(got.append)
    assert len(got) == 2 and all(event.synthetic for event in got)


def test_a_hat_button_event_is_synthetic() -> None:
    from action_plugins.hat_buttons import DirectionalButton
    from gremlin import event_handler
    from gremlin.base_classes import Value
    from gremlin.types import HatDirection

    button = DirectionalButton({"North": []}, "North")
    got: list = []
    listener = event_handler.EventListener()
    listener.virtual_event.connect(got.append)
    try:
        event = event_handler.Event(
            InputType.JoystickHat, 1, _STICK, "Default", value=HatDirection.North
        )
        button(event, Value(HatDirection.North))
    finally:
        listener.virtual_event.disconnect(got.append)
    assert len(got) == 1 and got[0].synthetic


def test_bindings_still_run_on_synthetic_events() -> None:
    # Only hardware-only screens ignore them (02 S44); the runtime doesn't.
    runtime = (_ROOT / "gremlin/modules/runtime.py").read_text("utf-8")
    assert "synthetic" not in runtime
