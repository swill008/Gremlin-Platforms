# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Play Sound whose sound file was moved or deleted.

It used to stop the whole profile from loading. Now the action loads and is
kept on save (a warning, not an error), and pressing it plays nothing
instead of raising.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
from unittest import mock

import gremlin.plugin_manager
from action_plugins.play_sound import PlaySoundData, PlaySoundFunctor
from gremlin.base_classes import UserFeedback
from gremlin.profile import Library


def _round_trip(filename: str) -> PlaySoundData:
    gremlin.plugin_manager.PluginManager()
    action = PlaySoundData()
    action.sound_filename = filename
    loaded = PlaySoundData()
    loaded.from_xml(action.to_xml(), Library())
    return loaded


def _kinds(action: PlaySoundData) -> list[UserFeedback.FeedbackType]:
    return [f.feedback_type for f in action.user_feedback()]


def test_missing_file_loads_and_is_kept(tmp_path: pathlib.Path) -> None:
    missing = str(tmp_path / "moved.wav")
    action = _round_trip(missing)
    assert action.sound_filename == missing
    assert _kinds(action) == [UserFeedback.FeedbackType.Warning]
    assert action.is_valid()  # a save keeps it


def test_no_file_chosen_is_still_unfinished() -> None:
    action = PlaySoundData()
    assert _kinds(action) == [UserFeedback.FeedbackType.Error]
    assert not action.is_valid()


def test_existing_file_has_no_feedback(tmp_path: pathlib.Path) -> None:
    sound = tmp_path / "beep.wav"
    sound.write_bytes(b"RIFF")
    assert _kinds(_round_trip(str(sound))) == []


def test_pressing_with_a_missing_file_plays_nothing(tmp_path: pathlib.Path) -> None:
    action = PlaySoundData()
    action.sound_filename = str(tmp_path / "moved.wav")
    functor = PlaySoundFunctor(action)
    with (
        mock.patch.object(functor, "_should_execute", return_value=True),
        mock.patch("action_plugins.play_sound.AudioPlayer") as player,
    ):
        functor(mock.Mock(), mock.Mock())
    player.return_value.enqueue.assert_not_called()


def test_pressing_with_an_unreadable_file_does_not_raise(
    tmp_path: pathlib.Path,
) -> None:
    sound = tmp_path / "damaged.wav"
    sound.write_bytes(b"not audio")
    action = PlaySoundData()
    action.sound_filename = str(sound)
    functor = PlaySoundFunctor(action)
    with (
        mock.patch.object(functor, "_should_execute", return_value=True),
        mock.patch("action_plugins.play_sound.AudioPlayer") as player,
    ):
        player.return_value.enqueue.side_effect = RuntimeError("cannot decode")
        functor(mock.Mock(), mock.Mock())
    player.return_value.enqueue.assert_called_once()
