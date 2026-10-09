# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page and Companion (D-09-OSC-COMPANION, D-09-OSC-TABS):
companionText(uid) gives Companion's Generic OSC connection settings
(this PC's address, the listening port, UDP, Listen for Feedback on, a
source port that isn't the program's) and the key actions for the input's
mode, worded as Generic OSC 2.8.2 and 3.0.0 name them. In the real program
off-screen (osc_page_companion_smoke.py): "OSC Setup…" opens OSC's Module
Setup, the row menu's "Copy for Companion" puts that text on the
clipboard, and the right side says "Select an input to see its actions"
while no input is selected."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterator
from typing import Any

import pytest
from PySide6 import QtCore, QtQml

from gremlin import osc_device_file, shared_state
from gremlin.osc import OscDevice
from gremlin.ui import osc_device_model
from gremlin.ui.osc_device_model import OscDeviceManagementModel

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "osc_page_companion_smoke.py"


@pytest.fixture
def model(
    qapp: object, monkeypatch: pytest.MonkeyPatch
) -> Iterator[OscDeviceManagementModel]:
    import gremlin.osc as gosc

    monkeypatch.setattr(
        gosc, "local_ipv4_addresses", lambda: ["10.0.0.7", "127.0.0.1", "0.0.0.0"]
    )
    monkeypatch.setattr(
        osc_device_file, "read_server", lambda: {"host": "", "port": 8001}
    )
    OscDevice().rows.reset()
    saved = shared_state.current_profile
    shared_state.current_profile = None
    m = OscDeviceManagementModel()
    yield m
    OscDevice().rows.reset()
    shared_state.current_profile = saved


def _qml(model: OscDeviceManagementModel, body: str) -> Any:  # noqa: ANN401
    engine = QtQml.QQmlEngine()
    engine.rootContext().setContextProperty("m", model)
    comp = QtQml.QQmlComponent(engine)
    comp.setData(
        f"import QtQuick\nQtObject {{ property var result: {body} }}".encode(),
        QtCore.QUrl(),
    )
    obj = comp.create()
    assert obj is not None, comp.errorString()
    value = obj.property("result")
    return value.toVariant() if hasattr(value, "toVariant") else value


def _add(model: OscDeviceManagementModel, settings: str) -> str:
    assert _qml(model, f"m.createConfiguredInput({settings})") is True
    return list(OscDevice().rows.rows())[-1].uid


def _text(model: OscDeviceManagementModel, uid: str) -> str:
    return str(_qml(model, f'm.companionText("{uid}")'))


def test_companion_text_has_the_generic_osc_connection(
    model: OscDeviceManagementModel,
) -> None:
    uid = _add(model, '{address: "/sd/fire", mode: "button"}')
    text = _text(model, uid)
    assert "Target Hostname or IP: 10.0.0.7" in text
    assert "Target Port: 8001" in text
    assert "Protocol: UDP" in text
    assert "Listen for Feedback: on" in text
    assert "Source Port: 9001" in text
    assert "Press: Send integer /sd/fire 1" in text
    assert "Release: Send integer /sd/fire 0" in text


def test_companion_text_follows_the_mode(model: OscDeviceManagementModel) -> None:
    axis = _add(
        model, '{address: "/fader/1", mode: "axis", range_min: -1, range_max: 1}'
    )
    assert "Send float /fader/1 <value -1..1>" in _text(model, axis)
    trig = _add(model, '{address: "/go", mode: "button", trigger: true}')
    assert "Send message without arguments /go" in _text(model, trig)
    data = _add(
        model,
        '{address: "/scene", mode: "button", cmd_mode: "data", data: ["2", "x"]}',
    )
    assert "Send message with multiple arguments /scene 2 x" in _text(model, data)
    enc = _add(model, '{address: "/knob", mode: "encoder", enc_format: "signed"}')
    got = _text(model, enc)
    assert "Rotate right: Send integer /knob 1" in got
    assert "Rotate left: Send integer /knob -1" in got
    assert _text(model, "no-such-uid") == ""


def test_companion_host_without_another_address_is_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gremlin.osc as gosc

    monkeypatch.setattr(gosc, "local_ipv4_addresses", lambda: ["127.0.0.1", "0.0.0.0"])
    assert osc_device_model._companion_host("") == "127.0.0.1"
    assert osc_device_model._companion_host("0.0.0.0") == "127.0.0.1"
    assert osc_device_model._companion_host("192.168.5.5") == "192.168.5.5"


def test_osc_page_setup_copy_and_empty_side_in_the_program(
    tmp_path: pathlib.Path,
) -> None:
    result = subprocess.run(
        [sys.executable, str(_SMOKE)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    problems = [x for x in lines if x.startswith(("ERROR", "WARN"))]
    assert problems == [], problems
    got = {
        x.split(" ", 2)[1]: json.loads(x.split(" ", 2)[2])
        for x in lines if x.startswith("RESULT ")
    }
    assert got["empty-text"] == "Select an input to see its actions"
    assert got["setup-button"] is True
    assert got["setup-signal"] is True
    assert got["setup-window"] is True
    assert got["copy-item"] is True
    clip = got["clipboard"]
    assert "Target Hostname or IP: 192.168.1.20" in clip
    assert "Target Port: 8123" in clip
    assert "Send integer /sd/fire 1" in clip or "Send float /fader/1" in clip
    assert str(got["message"]).startswith("Copied")
