# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import importlib
import pathlib
from xml.etree import ElementTree

import pytest

from gremlin import shared_state
from gremlin.base_classes import AbstractActionData
from gremlin.profile import Profile
from gremlin.types import InputType

_PLUGIN_DIR = pathlib.Path(__file__).resolve().parents[2] / "action_plugins"

# Known failures from the test plan. An empty string reloads as "None".
_EMPTY_TEXT_BECOMES_NONE = {"DescriptionData", "RunCommandData", "TextToSpeechData"}
# The empty first sequence is not written back after a reload.
_EMPTY_SEQUENCE_DROPPED = {"ChainData"}


def _plugin_folders() -> set[str]:
    return {f.name for f in _PLUGIN_DIR.iterdir() if (f / "__init__.py").exists()}


def _action_classes() -> list[type[AbstractActionData]]:
    classes = []
    for name in sorted(_plugin_folders()):
        module = importlib.import_module(f"action_plugins.{name}")
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, AbstractActionData)
                and value.__module__ == module.__name__
                and value not in classes
            ):
                classes.append(value)
    return classes


def _case(cls: type[AbstractActionData], input_type: InputType) -> pytest.param:
    marks = []
    if cls.__name__ in _EMPTY_TEXT_BECOMES_NONE:
        marks.append(
            pytest.mark.xfail(reason="empty text reloads as 'None'", strict=True)
        )
    if cls.__name__ in _EMPTY_SEQUENCE_DROPPED:
        marks.append(pytest.mark.xfail(reason="empty sequence dropped", strict=True))
    return pytest.param(
        cls, input_type, id=f"{cls.__name__}-{input_type.name}", marks=marks
    )


_CLASSES = _action_classes()
_CASES = [_case(cls, t) for cls in _CLASSES for t in cls.input_types]


@pytest.fixture
def profile() -> Profile:
    old = shared_state.current_profile
    shared_state.current_profile = Profile()
    yield shared_state.current_profile
    shared_state.current_profile = old


def test_every_plugin_is_covered() -> None:
    assert {cls.__module__.split(".")[1] for cls in _CLASSES} == _plugin_folders()


@pytest.mark.parametrize("cls, input_type", _CASES)
def test_default_action_survives_save_and_load(
    profile: Profile, cls: type[AbstractActionData], input_type: InputType
) -> None:
    try:
        first = cls(input_type)
    except IndexError:
        pytest.skip("needs a vJoy device")
    if not first.is_valid():
        pytest.skip("a new action is not valid until set up; the app does not save it")
    saved = ElementTree.tostring(first._to_xml())

    loaded = cls(input_type)
    loaded._from_xml(ElementTree.fromstring(saved), profile.library)
    assert ElementTree.tostring(loaded._to_xml()) == saved


def test_blank_action_label_stays_blank(profile: Profile) -> None:
    from action_plugins.pause_resume import PauseResumeData

    action = PauseResumeData(InputType.JoystickButton)
    action.action_label = ""
    loaded = PauseResumeData(InputType.JoystickButton)
    loaded.from_xml(action.to_xml(), profile.library)
    assert loaded.action_label == ""
