# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

sys.path.append(".")

import logging
import pathlib
import uuid
from unittest import mock
from xml.etree import ElementTree

import pytest
from PySide6 import QtCore

from action_plugins.run_command import (
    RunCommandData,
    RunCommandFunctor,
)
from gremlin import log_once
from gremlin.base_classes import Value
from gremlin.profile import Library
from gremlin.types import InputType

_ACTION_RUN_COMMAND_SIMPLE = "action_run_command_simple.xml"
_RUN_COMMAND_UUID = uuid.UUID("b5d8f3a1-2c47-4e9a-8f16-7d0e4a6c9b32")


def test_ctor() -> None:
    action = RunCommandData(InputType.JoystickButton)

    assert action.executable == ""
    assert action.arguments == ""


def test_from_xml(xml_dir: pathlib.Path) -> None:
    library = Library()
    action = RunCommandData(InputType.JoystickButton)
    action.from_xml(
        ElementTree.fromstring((xml_dir / _ACTION_RUN_COMMAND_SIMPLE).read_text()),
        library,
    )

    assert action._id == _RUN_COMMAND_UUID
    assert action.executable == "C:\\Windows\\System32\\notepad.exe"
    assert action.arguments == '"C:\\my notes\\todo.txt" --readonly'


def test_to_xml() -> None:
    action = RunCommandData(InputType.JoystickButton)
    action._id = _RUN_COMMAND_UUID
    action.executable = "C:\\Windows\\System32\\notepad.exe"
    action.arguments = '"C:\\my notes\\todo.txt" --readonly'

    node = action._to_xml()

    assert node.attrib["type"] == "run-command"
    assert node.attrib["id"] == str(_RUN_COMMAND_UUID)
    assert (
        node.find("./property/name[.='executable']/../value").text
        == "C:\\Windows\\System32\\notepad.exe"
    )
    assert (
        node.find("./property/name[.='arguments']/../value").text
        == '"C:\\my notes\\todo.txt" --readonly'
    )


def test_roundtrip(xml_dir: pathlib.Path) -> None:
    library = Library()
    source = RunCommandData(InputType.JoystickButton)
    source.from_xml(
        ElementTree.fromstring((xml_dir / _ACTION_RUN_COMMAND_SIMPLE).read_text()),
        library,
    )
    node = source.to_xml()
    assert node is not None

    target = RunCommandData(InputType.JoystickButton)
    target.from_xml(node, library)

    assert target.executable == source.executable
    assert target.arguments == source.arguments


def test_whitespace_preserved() -> None:
    library = Library()
    action = RunCommandData(InputType.JoystickButton)
    action.executable = "C:\\path with spaces\\app.exe"
    action.arguments = '  --flag  "a b"  '

    node = action.to_xml()
    assert node is not None
    restored = RunCommandData(InputType.JoystickButton)
    restored.from_xml(node, library)

    assert restored.executable == "C:\\path with spaces\\app.exe"
    assert restored.arguments == '  --flag  "a b"  '


def test_user_feedback_empty_executable() -> None:
    action = RunCommandData(InputType.JoystickButton)
    action.executable = ""

    feedback = action.user_feedback()

    assert len(feedback) == 1
    assert feedback[0].feedback_type == feedback[0].FeedbackType.Error


def test_user_feedback_whitespace_only() -> None:
    action = RunCommandData(InputType.JoystickButton)
    action.executable = "   \t\n"

    feedback = action.user_feedback()

    assert len(feedback) == 1
    assert feedback[0].feedback_type == feedback[0].FeedbackType.Error


def test_user_feedback_valid() -> None:
    action = RunCommandData(InputType.JoystickButton)
    action.executable = "notepad.exe"

    assert action.user_feedback() == []


def test_functor_launches_with_split_arguments() -> None:
    action = RunCommandData(InputType.JoystickButton)
    action.executable = "C:\\Windows\\System32\\notepad.exe"
    action.arguments = '"C:\\my notes\\todo.txt" --readonly'
    functor = RunCommandFunctor(action)

    with mock.patch.object(QtCore.QProcess, "startDetached") as launch:
        functor(mock.MagicMock(), Value(True))

    launch.assert_called_once_with(
        "C:\\Windows\\System32\\notepad.exe",
        ["C:\\my notes\\todo.txt", "--readonly"],
    )


def test_functor_skips_when_no_executable() -> None:
    action = RunCommandData(InputType.JoystickButton)
    action.executable = ""
    action.arguments = "--flag"
    functor = RunCommandFunctor(action)

    with mock.patch.object(QtCore.QProcess, "startDetached") as launch:
        functor(mock.MagicMock(), Value(True))

    launch.assert_not_called()


def test_functor_skips_when_not_pressed() -> None:
    action = RunCommandData(InputType.JoystickButton)
    action.executable = "notepad.exe"
    functor = RunCommandFunctor(action)

    with mock.patch.object(QtCore.QProcess, "startDetached") as launch:
        functor(mock.MagicMock(), Value(False))

    launch.assert_not_called()


# 05 S97 (R2): a program that can't be started is reported once in the
# user log; nothing else happens.
def _user_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage() for r in caplog.records
        if r.name == "user" and r.levelno == logging.WARNING
    ]


def test_functor_failed_start_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log_once.reset()
    action = RunCommandData(InputType.JoystickButton)
    action.executable = "C:/missing/nothing.exe"
    functor = RunCommandFunctor(action)

    with caplog.at_level(logging.WARNING, logger="user"), mock.patch.object(
        QtCore.QProcess, "startDetached", return_value=(False, -1)
    ):
        functor(mock.MagicMock(), Value(True))
        functor(mock.MagicMock(), Value(True))

    warnings = _user_warnings(caplog)
    assert len(warnings) == 1
    assert "Run Command: could not start 'C:/missing/nothing.exe'" in warnings[0]


def test_functor_raising_start_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log_once.reset()
    action = RunCommandData(InputType.JoystickButton)
    action.executable = "C:/broken/app.exe"
    functor = RunCommandFunctor(action)

    with caplog.at_level(logging.WARNING, logger="user"), mock.patch.object(
        QtCore.QProcess, "startDetached", side_effect=RuntimeError("boom")
    ):
        functor(mock.MagicMock(), Value(True))
        functor(mock.MagicMock(), Value(True))

    warnings = _user_warnings(caplog)
    assert len(warnings) == 1
    assert "Run Command: could not start 'C:/broken/app.exe'" in warnings[0]
