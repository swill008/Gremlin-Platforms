# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC output and the Send OSC action (D-09-OSC-OUTPUT): sends go to the
target's host and port (or back to the last sender for "reply") with the
values and types set; nothing goes out with OSC output off or no Run;
Auto is the type last received on the address; the action saves and loads
and its functor sends the input value scaled; the editor loads in the real
program off-screen (send_osc_editor_smoke.py). No network: the UDP client
is a stand-in."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import uuid
from collections.abc import Iterator
from typing import Any
from xml.etree import ElementTree

import pytest

from gremlin import osc_device_file, osc_output, run_scope
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.profile import Library
from gremlin.types import ActionActivationMode, InputType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_EVENT = Event(
    InputType.JoystickButton, 1, uuid.UUID(int=5), "Default", is_pressed=True
)


def _harness() -> Any:  # noqa: ANN401
    spec = importlib.util.spec_from_file_location(
        "_send_osc_harness", _ROOT / "test" / "journeys" / "_harness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    sent: list[tuple] = []

    def __init__(self, host: str, port: int) -> None:
        self.peer = (host, port)

    def send_message(self, address: str, args: list) -> None:
        FakeClient.sent.append((self.peer, address, list(args)))


@pytest.fixture
def osc(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    """OSC's file in a temp folder with two targets; a Run going; fake UDP."""
    doc = {
        "server": {"output_enabled": True, "reply_to_sender": True},
        "targets": [
            {"id": "t1", "name": "Desk", "host": "10.0.0.5", "port": 9000},
            {"id": "t2", "name": "Tablet", "host": "10.0.0.6", "port": 9001},
        ],
    }
    file = tmp_path / "osc.json"

    def write(d: dict) -> None:
        file.write_text(json.dumps(d), encoding="utf-8")
        from gremlin.modules import registry

        registry._cache.pop(file, None)  # read again at once

    write(doc)
    monkeypatch.setattr(osc_device_file, "path", lambda: file)
    FakeClient.sent = []
    monkeypatch.setattr(osc_output, "_make_client", FakeClient)
    monkeypatch.setattr(run_scope, "running", lambda: True)
    stops: list = []
    monkeypatch.setattr(run_scope, "on_stop", lambda *a: stops.append(a))
    osc_output.reset()
    yield {"doc": doc, "write": write, "stops": stops}
    osc_output.reset()


def test_send_goes_to_the_target_with_values_and_types(osc: dict) -> None:
    assert osc_output.send("t2", "/fader/1", ["3", 0.5, "1", "hi"],
                           ["int", "float", "bool", "text"])
    assert FakeClient.sent == [(("10.0.0.6", 9001), "/fader/1", [3, 0.5, True, "hi"])]
    assert osc_output.resolve_target("t1") == ("10.0.0.5", 9000)
    assert osc_output.resolve_target("nope") is None


def test_output_off_or_no_run_sends_nothing(
    osc: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = osc["doc"]
    doc["server"]["output_enabled"] = False
    osc["write"](doc)
    assert osc_device_file.read_server()["output_enabled"] is False
    assert not osc_output.send("t1", "/a", [1])
    assert osc_output.send("t1", "/a", [1], force=True)  # force still sends
    doc["server"]["output_enabled"] = True
    osc["write"](doc)
    monkeypatch.setattr(run_scope, "running", lambda: False)
    assert not osc_output.send("t1", "/b", [1])
    assert [s[1] for s in FakeClient.sent] == ["/a"]


def test_reply_goes_to_the_last_sender(osc: dict) -> None:
    assert not osc_output.send("reply", "/r", [1])  # nobody heard yet
    osc_output.note_sender("192.168.1.9", 53000)
    osc_output.note_sender("192.168.1.10", 53001)
    assert osc_output.send("reply", "/r", [1])
    assert FakeClient.sent[-1][0] == ("192.168.1.10", 53001)
    doc = osc["doc"]
    doc["server"]["reply_to_sender"] = False
    osc["write"](doc)
    assert not osc_output.send("reply", "/r", [1])


def test_auto_is_the_type_last_received_else_float(osc: dict) -> None:
    osc_output.note_received_type("/mute", (1,))
    osc_output.send("t1", "/mute", ["0.0"])
    osc_output.send("t1", "/other", ["2"])
    osc_output.note_received_type("/name", ("x",))
    osc_output.send("t1", "/name", [5])
    assert [s[2] for s in FakeClient.sent] == [[0], [2.0], ["5"]]


def test_one_client_per_peer_closed_at_stop(osc: dict) -> None:
    osc_output.send("t1", "/a", [1])
    osc_output.send("t1", "/b", [1])
    assert len(osc_output._clients) == 1
    assert [s[1] for s in osc["stops"]] == ["OSC output"]
    osc["stops"][0][2]()  # Stop runs it
    assert osc_output._clients == {}


def test_sends_are_noted_as_out(osc: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    noted: list = []
    fake = types.ModuleType("gremlin.osc_traffic")
    fake.note = lambda *a: noted.append(a)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.osc_traffic", fake)
    import gremlin

    monkeypatch.setattr(gremlin, "osc_traffic", fake, raising=False)
    osc_output.send("t1", "/n", [1], ["int"])
    assert noted == [("out", "/n", [1], ("10.0.0.5", 9000), [])]


# --- the Send OSC action ------------------------------------------------------


def _action(behavior: InputType = InputType.JoystickButton):  # noqa: ANN202
    from action_plugins.send_osc import SendOscData

    return SendOscData(behavior)


def test_action_saves_and_loads(osc: dict) -> None:
    from action_plugins.send_osc import SendOscData

    action = _action()
    assert action.target == "t1"  # the first target
    action.target = "reply"
    action.address = "/light/2"
    action.values = [
        {"source": "fixed", "value": "7", "type": "int"},
        {"source": "input", "value": "", "type": "float"},
    ]
    action.input_min, action.input_max = -5.0, 5.0
    action.activation_mode = ActionActivationMode.Both
    node = action.to_xml()
    assert node is not None and node.attrib["type"] == "send-osc"
    loaded = SendOscData(InputType.JoystickButton)
    loaded.from_xml(ElementTree.fromstring(ElementTree.tostring(node)), Library())
    assert (loaded.target, loaded.address, loaded.values) == (
        "reply", "/light/2", action.values
    )
    assert (loaded.input_min, loaded.input_max) == (-5.0, 5.0)
    assert loaded.activation_mode == ActionActivationMode.Both
    no_address = _action()
    assert not no_address.is_valid() and no_address.to_xml() is None


def test_functor_sends_fixed_and_input_values(osc: dict) -> None:
    from action_plugins.send_osc import SendOscFunctor

    button = _action()
    button.address = "/go"
    button.values = [
        {"source": "fixed", "value": "2", "type": "int"},
        {"source": "input", "value": "", "type": "auto"},
    ]
    functor = SendOscFunctor(button)
    functor(_EVENT, Value(True))
    functor(_EVENT, Value(False))  # press only
    axis = _action(InputType.JoystickAxis)
    axis.address = "/vol"
    axis.input_min, axis.input_max = 0.0, 100.0
    SendOscFunctor(axis)(_EVENT, Value(0.5))
    assert [(s[0], s[1], s[2]) for s in FakeClient.sent] == [
        (("10.0.0.5", 9000), "/go", [2, 1.0]),
        (("10.0.0.5", 9000), "/vol", [75.0]),
    ]


def test_functor_sends_nothing_without_a_run(
    osc: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from action_plugins.send_osc import SendOscFunctor

    monkeypatch.setattr(run_scope, "running", lambda: False)
    action = _action()
    action.address = "/go"
    SendOscFunctor(action)(_EVENT, Value(True))
    assert FakeClient.sent == []


# --- the editor in the real program -------------------------------------------


@pytest.fixture(scope="module")
def editor_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _harness().run_journey(
        _ROOT / "test" / "unit" / "send_osc_editor_smoke.py",
        tmp_path_factory.mktemp("sendosc"),
    )


def test_the_editor_loads_and_edits_the_action(editor_run: dict) -> None:
    step = _harness().step
    assert step(editor_run, "editor") is True
    assert step(editor_run, "typed-address") == "/fire"
    assert step(editor_run, "values-after-add") == 2
    assert "Reply to sender" in step(editor_run, "targets")
