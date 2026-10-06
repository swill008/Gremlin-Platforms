# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Batch 2, B5b: action logic and speech.

- GL-310 / GL-312: axis-range virtual buttons (06 S39, D-06-S39-NORELEASE).
- GL-042: speech asked for on another thread is spoken on the main thread
  (09 R10).
- GL-198: Options shows "(default)" for a missing or unset voice (09 Q12).
- GL-199: one warning when Windows speech is not available (09 Q13).
- GL-197: Text to Speech on keyboard keys (09 Q11, 05 Q7).
- GL-161: Axis Delta uses the shaped value and treats 0 as a value (05 Q9).
- GL-162: Split Axis's change stays inside its two lists (05 Q10).
- GL-167: new Dual Axis Deadzones are numbered (05 Q14).
- GL-165: damaged Add Action order settings never empty the menu (05 S6, S7).
- GL-163: a macro Joystick step passes the input module's claims (05 Q17).

Nothing reaches the PC: the speech engine is a stand-in.
"""

from __future__ import annotations

import logging
import sys
import threading
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import code_runner, macro, threads, tts
from gremlin.base_classes import Value
from gremlin.common import SingletonMetaclass
from gremlin.event_handler import Event
from gremlin.types import AxisButtonDirection, InputType

_GUID = uuid.UUID("12345678-1234-1234-1234-123456789abc")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


# --- GL-310 / GL-312: axis-range buttons -------------------------------------


def _axis(lower: float, upper: float, direction: AxisButtonDirection) -> Any:  # noqa: ANN401
    button = code_runner.VirtualAxisButton(lower, upper, direction)
    sent: list[bool] = []

    def move(value: float) -> None:
        sent.extend(
            button(Event(InputType.JoystickAxis, 1, _GUID, "Default", value=value))
        )

    return move, sent


def test_a_jump_across_the_range_presses_and_releases() -> None:
    move, sent = _axis(0.2, 0.6, AxisButtonDirection.Anywhere)
    move(-0.8)
    move(0.9)
    assert sent == [True, False]
    move(0.4)  # back inside: a normal press, the button is up again
    assert sent == [True, False, True]


def test_a_jump_presses_only_in_the_chosen_direction() -> None:
    # "Below": entered from below, the axis moving up.
    move, sent = _axis(0.2, 0.6, AxisButtonDirection.Below)
    move(-0.8)
    move(0.9)  # up across: entered from below
    assert sent == [True, False]
    move(-0.9)  # down across: entered from above, nothing
    assert sent == [True, False]


def test_inside_at_run_then_leaving_sends_nothing_and_re_entering_presses() -> None:
    move, sent = _axis(0.2, 0.6, AxisButtonDirection.Anywhere)
    move(0.4)  # inside at Run: no press (Q13)
    move(0.5)
    move(0.9)  # leaves: no release without a press (D-06-S39-NORELEASE)
    assert sent == []
    move(0.3)
    move(0.0)
    assert sent == [True, False]


def test_moving_back_inside_the_range_does_not_release() -> None:
    # S39: the release comes on leaving the range, not on a reverse move.
    move, sent = _axis(0.2, 0.6, AxisButtonDirection.Below)
    move(0.0)
    move(0.4)  # entered from below
    move(0.3)  # moving down, still inside
    assert sent == [True]
    move(0.0)
    assert sent == [True, False]


# --- speech stand-in ----------------------------------------------------------


class _Voice:
    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name


class _Engine:
    State = SimpleNamespace(Ready="ready", Speaking="speaking", Error="error")
    engines_available = ["mock", "winrt", "sapi"]

    def __init__(self, backend: str) -> None:
        self.backend = backend
        self.said: list[tuple[str, bool]] = []
        self.voice = ""
        self._state = "ready"
        self.stateChanged = mock.MagicMock()

    @classmethod
    def availableEngines(cls) -> list[str]:  # noqa: N802
        return list(cls.engines_available)

    def availableVoices(self) -> list[_Voice]:  # noqa: N802
        return [_Voice("Voice A"), _Voice("Voice B")]

    def setVoice(self, voice: _Voice) -> None:  # noqa: N802
        self.voice = voice.name()

    def state(self) -> str:
        return self._state

    def setRate(self, _v: float) -> None:  # noqa: N802
        pass

    def setPitch(self, _v: float) -> None:  # noqa: N802
        pass

    def setVolume(self, _v: float) -> None:  # noqa: N802
        pass

    def say(self, text: str) -> None:
        on_main = threading.current_thread() is threading.main_thread()
        self.said.append((text, on_main))
        self._state = "speaking"

    def stop(self) -> None:
        self._state = "ready"


@pytest.fixture
def speech(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:  # noqa: ANN401
    monkeypatch.setattr(tts, "QTextToSpeech", _Engine)
    saved = {"voice": ""}
    config = SimpleNamespace(
        value=lambda *_a: saved["voice"],
        set=lambda *a: saved.__setitem__("voice", a[-1]),
    )
    monkeypatch.setattr(tts, "Configuration", lambda: config)
    manager = object.__new__(tts.TTSManager)
    manager.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, tts.TTSManager, manager)
    manager.saved = saved
    manager.config = config
    yield manager
    manager.stop()


# --- GL-042: speech from another thread ----------------------------------------


def test_speech_asked_for_on_a_timer_thread_is_spoken_on_the_main_thread(
    speech: Any,  # noqa: ANN401
) -> None:
    speech.start()
    worker = threads.start(
        "tts test",
        speech.enqueue,
        tts.TTSRequest("gear up", 0.0, 1.0, 0.0),
        tts.TTSQueueMode.QueueBack,
    )
    worker.join(2.0)
    assert speech._engine.said == []  # not touched from the worker
    QtCore.QCoreApplication.processEvents()
    assert speech._engine.said == [("gear up", True)]


def test_speech_arriving_after_stop_is_dropped(speech: Any) -> None:  # noqa: ANN401
    speech.start()
    worker = threads.start(
        "tts test",
        speech.enqueue,
        tts.TTSRequest("late", 0.0, 1.0, 0.0),
        tts.TTSQueueMode.QueueBack,
    )
    worker.join(2.0)
    speech.stop()
    QtCore.QCoreApplication.processEvents()
    assert speech._engine.said == []


# --- GL-199: Windows speech missing -------------------------------------------


def test_missing_windows_speech_warns_once_in_the_log_and_the_action(
    speech: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from action_plugins.text_to_speech import TextToSpeechData

    monkeypatch.setattr(_Engine, "engines_available", ["mock", "sapi"])
    with caplog.at_level(logging.WARNING, logger="system"):
        speech.prepare_engine()
        speech.start()
        assert speech.speech_available() is False
    warnings = [r for r in caplog.records if "Windows speech" in r.getMessage()]
    assert len(warnings) == 1

    data = TextToSpeechData(InputType.JoystickButton)
    data.text = "hello"
    feedback = data.user_feedback()
    assert [f.feedback_type for f in feedback] == [
        f.FeedbackType.Warning for f in feedback
    ]
    assert len(feedback) == 1 and "Windows speech" in feedback[0].message


def test_windows_speech_present_gives_no_warning(speech: Any) -> None:  # noqa: ANN401
    from action_plugins.text_to_speech import TextToSpeechData

    data = TextToSpeechData(InputType.JoystickButton)
    data.text = "hello"
    assert data.user_feedback() == []


# --- GL-198: Options voice list ----------------------------------------------------


def _voice_model(speech: Any, monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: ANN401
    from gremlin.ui import option

    monkeypatch.setattr(option.gremlin.config, "Configuration", lambda: speech.config)
    return option.TTSVoiceSelectionModel()


def test_options_show_default_when_the_saved_voice_is_gone(
    speech: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    speech.saved["voice"] = "Uninstalled Voice"
    model = _voice_model(speech, monkeypatch)
    role = QtCore.Qt.ItemDataRole.UserRole + 1
    assert model.data(model.index(0, 0), role) == "(default)"
    assert model.currentIndex == 0
    speech.saved["voice"] = ""
    assert model.currentIndex == 0
    speech.saved["voice"] = "Voice B"
    assert model.data(model.index(model.currentIndex, 0), role) == "Voice B"


def test_choosing_default_saves_no_voice_and_speaks_with_the_default(
    speech: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    speech.saved["voice"] = "Voice B"
    model = _voice_model(speech, monkeypatch)
    assert speech._engine.voice == "Voice B"
    model.currentIndex = 0
    assert speech.saved["voice"] == ""
    assert speech._engine.voice == ""  # a new engine: the system's default


# --- GL-197: keyboard keys ------------------------------------------------------


def test_text_to_speech_is_offered_on_keyboard_keys() -> None:
    from action_plugins.text_to_speech import TextToSpeechData

    assert InputType.Keyboard in TextToSpeechData.input_types


# --- GL-161: Axis Delta ------------------------------------------------------------


def _axis_delta() -> tuple[Any, list[str]]:  # noqa: ANN401
    from action_plugins.axis_delta import AxisDeltaFunctor

    functor = object.__new__(AxisDeltaFunctor)
    functor.data = SimpleNamespace(change_threshold=0.5)
    functor.functors = {"positive": ["pos"], "negative": ["neg"]}
    functor._last_value = None
    functor._accumulated = 0.0
    pulses: list[str] = []
    functor._pulse_event = lambda functors, *_a: pulses.append(functors[0])
    return functor, pulses


def _feed(functor: Any, raw: float, shaped: float) -> None:  # noqa: ANN401
    value = Value(raw)
    value.current = shaped
    functor(Event(InputType.JoystickAxis, 1, _GUID, "Default", value=raw), value)


def test_axis_delta_uses_the_value_shaped_by_earlier_actions() -> None:
    functor, pulses = _axis_delta()
    _feed(functor, 0.0, -0.9)
    _feed(functor, 0.1, 0.9)  # raw moved 0.1, the curve made it 1.8
    assert pulses == ["pos"]


def test_axis_delta_treats_zero_as_a_value() -> None:
    functor, pulses = _axis_delta()
    _feed(functor, -0.6, -0.6)
    _feed(functor, 0.0, 0.0)  # a move of 0.6 to exactly 0
    assert pulses == ["pos"]


# --- GL-162: Split Axis ----------------------------------------------------------


def test_split_axis_does_not_change_the_value_for_later_actions() -> None:
    from action_plugins.split_axis import SplitAxisFunctor

    seen: list[float] = []
    functor = object.__new__(SplitAxisFunctor)
    functor.data = SimpleNamespace(split_value=0.0)
    functor.functors = {
        "lower": [],
        "upper": [lambda _e, v, _p: seen.append(v.current)],
    }
    functor._side = None
    value = Value(0.5)
    functor(Event(InputType.JoystickAxis, 1, _GUID, "Default", value=0.5), value)
    assert seen == [pytest.approx(0.0)]  # the upper half is rescaled
    assert value.current == 0.5  # what the next action in the list sees


# --- GL-167: Dual Axis Deadzone names --------------------------------------------


def test_new_dual_axis_deadzones_are_numbered() -> None:
    from action_plugins.dual_axis_deadzone import (
        DualAxisDeadzoneData,
        DualAxisDeadzoneModel,
    )
    from gremlin.profile import Library

    library = Library()
    shown: list[str] = []
    fake = SimpleNamespace(
        library=library,
        _binding_model=SimpleNamespace(behavior_type=InputType.JoystickAxis),
        _set_deadzone=shown.append,
    )
    DualAxisDeadzoneModel.newDeadzone(fake)
    DualAxisDeadzoneModel.newDeadzone(fake)
    labels = sorted(a.label for a in library.actions_by_type(DualAxisDeadzoneData))
    assert labels == ["Dual Axis Deadzone 1", "Dual Axis Deadzone 2"]
    assert len(shown) == 2


# --- GL-165: Add Action list ---------------------------------------------------------


@pytest.mark.parametrize(
    "priorities",
    [
        [["Map to vJoy", True]],  # most actions missing from the list
        None,  # the setting gone
        [["Map to vJoy", True], "junk", ["Macro"]],  # bad entries
    ],
)
def test_damaged_action_order_settings_never_empty_the_add_action_list(
    priorities: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.plugin_manager import PluginManager
    from gremlin.ui import action_model

    monkeypatch.setattr(
        action_model,
        "Configuration",
        lambda: SimpleNamespace(value=lambda *_a: priorities),
    )
    fake = SimpleNamespace(_action_behavior=lambda: "button")
    names = action_model.ActionModel.compatibleActions.fget(fake)
    expected = {
        e.name
        for e in PluginManager().type_action_map[InputType.JoystickButton]
        if e.tag != "root"
    }
    assert set(names) == expected
    if priorities and priorities[0] == ["Map to vJoy", True]:
        assert names[0] == "Map to vJoy"


def test_hidden_actions_stay_hidden_with_others_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import action_model

    monkeypatch.setattr(
        action_model,
        "Configuration",
        lambda: SimpleNamespace(value=lambda *_a: [["Macro", False]]),
    )
    fake = SimpleNamespace(_action_behavior=lambda: "button")
    names = action_model.ActionModel.compatibleActions.fget(fake)
    assert "Macro" not in names and names


# --- GL-163: macro Joystick step and claims -------------------------------------


@pytest.mark.parametrize(("button", "passes"), [(3, True), (4, False)])
def test_a_macro_joystick_step_passes_only_claimed_controls(
    button: int, passes: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules.claim import empty_claim
    from gremlin.modules.gate import guid_key
    from gremlin.modules.runtime import InputModuleRuntime

    claim = empty_claim()
    claim["buttons"] = [3]
    reached: list[Event] = []
    gate = SimpleNamespace(
        _claims={guid_key(_GUID): claim},
        _dest_guids=set(),
        _passthrough=set(),
        event=SimpleNamespace(emit=reached.append),
    )
    listener = SimpleNamespace(
        joystick_event=SimpleNamespace(
            emit=lambda e: InputModuleRuntime.klass._on_hid(gate, e)
        )
    )
    monkeypatch.setattr(macro.event_handler, "EventListener", lambda: listener)
    monkeypatch.setattr(macro, "_mode_name", lambda: "Default")
    macro.JoystickAction(_GUID, InputType.JoystickButton, button, True)()
    assert bool(reached) is passes


# --- GL-135: one switch for HidHide's Automatically Start ---------------------


def test_options_no_longer_show_the_hidhide_switch_but_point_to_it() -> None:
    import gremlin.config
    import gremlin.ui.hidhide  # noqa: F401  (registers the setting)
    from gremlin.ui import option

    key = ("global", "general", "hidhide-on-start")
    shown = [
        k for _s, groups in option.main_layout() for _g, keys in groups for k in keys
    ]
    assert key not in shown
    assert ("global", "general", "hidhide-start") in shown
    # The setting itself stays (the HidHide window and History use it).
    assert gremlin.config.Configuration().exists(*key)

    model = option.ConfigEntryModel(
        "global", "general", keys=[key, ("global", "general", "hidhide-start")]
    )
    assert model.rowCount() == 1  # the switch is left out even when asked for
    role = {bytes(v.data()).decode(): r for r, v in model.roles.items()}
    index = model.index(0, 0)
    assert model.data(index, role["data_type"]) == "meta_option"
    assert model.data(index, role["value"]) == ""  # text only, no control
    assert "Automatically Start" in model.data(index, role["description"])
