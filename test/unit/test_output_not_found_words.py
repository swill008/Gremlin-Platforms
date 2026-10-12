# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The renamed words show (batch L renames, 05 S137-S139, 03 S30/S78a,
04 S32a): "Output not found" for what can't be sent, "No bindings" for an
input with nothing bound, singular and plural."""

from __future__ import annotations

from pathlib import Path

import pytest

from gremlin.modules import output
from gremlin.ui import backend, module_model

_QML = Path(__file__).resolve().parents[2] / "qml"


def test_home_card_line_counts_outputs() -> None:
    assert module_model.cant_send_line(1) == "⚠ 1 output not found"
    assert module_model.cant_send_line(3) == "⚠ 3 outputs not found"
    card = (_QML / "StatusCard.qml").read_text(encoding="utf-8")
    assert '" output" : " outputs") + " not found"' in card
    assert "can't be sent" not in card.split("cantSendText:")[1].split("\n")[1]


def test_load_notice_counts_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    found = [{"device_name": "VKBSim NXT"}] * 94 + [{"device_name": "OSC"}]
    monkeypatch.setattr(output, "cant_send_bindings", lambda loaded: found)
    assert backend._cant_send_notice(object()) == (
        "VKBSim NXT: 94 outputs not found. OSC: 1."
    )
    monkeypatch.setattr(output, "cant_send_bindings", lambda loaded: found[-1:])
    assert backend._cant_send_notice(object()) == "OSC: 1 output not found."


def test_find_tick_and_input_monitor_words() -> None:
    bar = (_QML / "ControlFindBar.qml").read_text(encoding="utf-8")
    assert 'text: "Output not found"' in bar
    assert 'text: "Can\'t be sent"' not in bar
    log = (_QML / "DialogLiveLog.qml").read_text(encoding="utf-8")
    assert 'text: "Inputs with no bindings"' in log
    assert "no actions" not in log
