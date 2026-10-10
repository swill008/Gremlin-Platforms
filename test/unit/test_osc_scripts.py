# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Scripts and OSC (09 S163).

An OSC input variable names an OSC input by its permanent id; its decorator
puts the script's callback on the normal event path, so an OSC event from
the OSC runtime reaches it like a stick input's. Scripts send OSC through
osc_output, to a named target only: the output switch applies, unknown
targets and pattern addresses are refused, and what goes out is noted for
the Monitor as Out. Nothing leaves the PC: the UDP client is a recorder.

Spec: 09 S163.
"""

from __future__ import annotations

import types as _types
from collections.abc import Iterator
from typing import Any

import pytest

from gremlin import (
    event_handler,
    osc_output,
    run_scope,
    user_script,
)
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
from gremlin.types import InputType

MODE = "Default"


@pytest.fixture
def fresh_registry() -> Iterator[None]:
    user_script.callback_registry.clear()
    yield
    user_script.callback_registry.clear()


def _handler_with_script_callbacks() -> event_handler.EventHandler:
    """What CodeRunner.start does with the scripts' callbacks."""
    handler = event_handler.EventHandler()
    handler.add_plugin(user_script.OscPlugin())
    for dev_id, modes in user_script.callback_registry.registry.items():
        for mode, events in modes.items():
            for event, callbacks in events.items():
                for callback in callbacks.values():
                    handler.add_callback(dev_id, mode, event, callback)
    return handler


def test_osc_input_variable_callback_runs_from_an_osc_event(
    fresh_registry: None,
) -> None:
    rows = OscDevice().rows
    row = rows.create(InputType.JoystickButton, "/script/press")
    var = user_script.OscInputVariable("Press", "", False)
    var.uid = row.uid
    assert var.is_valid()
    assert var.value is row

    seen: list[bool] = []

    @var.decorator(_types.SimpleNamespace(value=MODE))
    def pressed(event: event_handler.Event) -> None:
        seen.append(event.is_pressed)

    handler = _handler_with_script_callbacks()
    listener = event_handler.EventListener()
    listener.joystick_event.connect(handler.process_event)
    try:
        runtime = OscRuntime()
        runtime._running = True  # noqa: SLF001 - a Run is on
        runtime._emit_button(row, True, MODE, "/script/press")  # noqa: SLF001
        runtime._emit_button(row, False, MODE, "/script/press")  # noqa: SLF001
    finally:
        listener.joystick_event.disconnect(handler.process_event)
    assert seen == [True, False]


def test_osc_input_variable_names_the_input_by_permanent_id(
    fresh_registry: None,
) -> None:
    rows = OscDevice().rows
    row = rows.create(InputType.JoystickAxis, "/script/fader")
    var = user_script.OscInputVariable("Fader", "", False)
    var.uid = row.uid
    node = var.to_xml()
    assert node is not None
    assert node.get("uid") == row.uid

    again = user_script.OscInputVariable("Fader", "", False)
    again.from_xml(node)
    assert again.uid == row.uid
    again.decorator(_types.SimpleNamespace(value=MODE))(lambda: None)
    by_mode = user_script.callback_registry.registry[OSC_DEVICE_UUID][MODE]
    assert [(e.event_type, e.identifier) for e in by_mode] == [
        (InputType.JoystickAxis, row.input_id)
    ]


def test_osc_input_variable_with_a_deleted_input_is_kept_and_not_valid(
    fresh_registry: None,
) -> None:
    rows = OscDevice().rows
    row = rows.create(InputType.JoystickButton, "/script/gone")
    var = user_script.OscInputVariable("Gone", "", False)
    var.uid = row.uid
    rows.delete(row.uid)
    assert var.is_missing()
    assert not var.is_valid()
    node = var.to_xml()
    assert node is not None and node.get("uid") == row.uid
    # A missing input registers nothing.
    var.decorator(_types.SimpleNamespace(value=MODE))(lambda: None)
    assert OSC_DEVICE_UUID not in user_script.callback_registry.registry


# --- sending -----------------------------------------------------------------


class _Client:
    def __init__(self, sent: list, peer: tuple[str, int]) -> None:
        self._sent = sent
        self._peer = peer

    def send_message(self, address: str, args: list) -> None:
        self._sent.append((self._peer, address, list(args)))


@pytest.fixture
def osc_out(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    """osc_output with its settings and UDP client faked; a Run is on."""
    state: dict[str, Any] = {
        "server": {"output_enabled": True, "reply_to_sender": True},
        "targets": [
            {"id": "t1", "name": "Mixer", "host": "127.0.0.1", "port": 9001},
        ],
        "sent": [],
        "out": [],
    }
    monkeypatch.setattr(
        osc_output, "_settings", lambda: (state["server"], state["targets"])
    )
    monkeypatch.setattr(
        osc_output, "_client", lambda host, port: _Client(state["sent"], (host, port))
    )
    monkeypatch.setattr(
        osc_output,
        "_note_out",
        lambda address, args, peer: state["out"].append((address, args, peer)),
    )
    monkeypatch.setattr(run_scope, "running", lambda: True)
    yield state


def test_send_goes_to_the_named_target(osc_out: dict[str, Any]) -> None:
    assert user_script.osc.send("Mixer", "/vol", 0.5, 2) is True
    assert osc_out["sent"] == [(("127.0.0.1", 9001), "/vol", [0.5, 2.0])]
    # Noted for the Monitor as Out.
    assert osc_out["out"] == [("/vol", [0.5, 2.0], ("127.0.0.1", 9001))]


def test_send_with_output_off_sends_nothing(osc_out: dict[str, Any]) -> None:
    osc_out["server"]["output_enabled"] = False
    assert user_script.osc.send("Mixer", "/vol", 1) is False
    assert osc_out["sent"] == []


def test_send_to_an_unknown_target_is_refused(osc_out: dict[str, Any]) -> None:
    assert user_script.osc.send("Nobody", "/vol", 1) is False
    # Target ids, "reply" and raw host:port aren't names.
    assert user_script.osc.send("t1", "/vol", 1) is False
    assert user_script.osc.send("reply", "/vol", 1) is False
    assert user_script.osc.send("127.0.0.1:9001", "/vol", 1) is False
    assert osc_out["sent"] == []


def test_send_refuses_a_pattern_address(osc_out: dict[str, Any]) -> None:
    assert user_script.osc.send("Mixer", "/vol/*", 1) is False
    assert user_script.osc.send("Mixer", "vol", 1) is False
    assert osc_out["sent"] == []


def test_osc_plugin_gives_callbacks_the_osc_object() -> None:
    import functools

    def callback(osc: object) -> object:
        return osc

    bound = user_script.OscPlugin().install(callback, functools.partial)
    assert bound() is user_script.osc


def test_script_editor_picks_an_osc_input_by_address(fresh_registry: None) -> None:
    """The Scripts page's model: addresses to pick from, stores the uid."""
    from gremlin.ui import script as ui_script

    rows = OscDevice().rows
    a = rows.create(InputType.JoystickButton, "/script/a")
    b = rows.create(InputType.JoystickAxis, "/script/b")
    var = user_script.OscInputVariable("Pick", "", False)
    assert ui_script.ScriptListModel.data_class_lookup[type(var)] is (
        ui_script.OscInputVariableModel
    )
    model = ui_script.OscInputVariableModel(var)
    assert "/script/a" in model.options and "/script/b" in model.options
    assert model.currentIndex == -1
    model.select(model.options.index("/script/b"))
    assert var.uid == b.uid
    assert model.options[model.currentIndex] == "/script/b"
    assert a.uid != var.uid
