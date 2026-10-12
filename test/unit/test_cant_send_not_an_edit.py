# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The can't-be-sent notice only refreshes what open editors show
(D-05-CANT-SEND-LIVE, 05 S137): Send OSC's and Map to Xbox's red ⚠ re-read
it, but that isn't an edit of the action (no signal.actionsChanged, so no
profile change, Device Mapping Editor recheck or recovery nudge). Picking a pad or a
target still is."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from action_plugins.root import RootData
from gremlin.modules import output
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.signal import signal
from gremlin.types import InputType

B = InputType.JoystickButton


def _model(action: Any) -> tuple[object, Any]:  # noqa: ANN401
    from gremlin.ui.profile import InputItemBindingModel

    profile = Profile()
    item = InputItem(profile.library)
    binding = InputItemBinding(item)
    binding.root_action = RootData(B)
    binding.behavior = B
    profile.library.add_action(binding.root_action)
    profile.library.add_action(action)
    binding.root_action.insert_action(action, "children")
    model = InputItemBindingModel(binding)
    am = next(m for m in model._action_models.values() if m.action_data is action)
    return model, am


def _notified(obj: QtCore.QObject, prop: str) -> list[bool]:
    """Records the notify signal of a QML property (what QML re-reads on)."""
    meta = obj.metaObject()
    notify = meta.property(meta.indexOfProperty(prop)).notifySignal()
    name = bytes(notify.name().data()).decode()
    seen: list[bool] = []
    getattr(obj, name).connect(lambda *_: seen.append(True))
    return seen


@pytest.fixture
def edits(qapp: object) -> Iterator[list[bool]]:  # noqa: ANN401
    seen: list[bool] = []

    def edit() -> None:
        seen.append(True)

    signal.actionsChanged.connect(edit)
    yield seen
    signal.actionsChanged.disconnect(edit)


@pytest.fixture
def reasons(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """What the output layer says can't be sent, set by the test."""
    state = {"osc": "", "xbox": ""}
    monkeypatch.setattr(
        output, "osc_cant_send_text", lambda *a, **k: state["osc"] or None
    )
    monkeypatch.setattr(
        output, "xbox_cant_send_text", lambda *a, **k: state["xbox"] or None
    )
    return state


def _editors() -> tuple[list, Any, Any]:
    from action_plugins.map_to_xbox import MapToXboxData
    from action_plugins.send_osc import SendOscData

    osc = SendOscData(B)
    osc.target = "t1"
    xbox = MapToXboxData(B)
    keep_osc, osc_model = _model(osc)
    keep_xbox, xbox_model = _model(xbox)
    return [keep_osc, keep_xbox], osc_model, xbox_model


def test_the_notice_refreshes_the_warning_without_an_edit(
    edits: list[bool],
    reasons: dict[str, str],
) -> None:
    _keep, osc, xbox = _editors()
    assert osc.cantSendText == ""
    assert xbox.cantSendText == ""
    osc_seen = _notified(osc, "cantSendText")
    xbox_seen = _notified(xbox, "cantSendText")
    pads_seen = _notified(xbox, "padChoices")
    label_seen = _notified(xbox, "padLabel")
    edits.clear()
    reasons.update(osc="OSC output is Off.", xbox="Xbox pad 1 is not Found.")
    signal.cantSendChanged.emit()
    assert edits == [], "a can't-send notice counted as an action edit"
    assert osc_seen and xbox_seen and pads_seen and label_seen
    assert osc.cantSendText == "OSC output is Off."
    assert xbox.cantSendText == "Xbox pad 1 is not Found."


def test_picking_a_pad_is_still_an_edit(
    edits: list[bool],
    reasons: dict[str, str],
) -> None:
    _keep, _osc, xbox = _editors()
    seen = _notified(xbox, "cantSendText")
    edits.clear()
    xbox.xboxDeviceId = 2
    assert edits, "picking an Xbox pad wasn't an action edit"
    assert seen, "picking an Xbox pad didn't refresh the ⚠"


def test_picking_an_osc_target_is_still_an_edit(
    edits: list[bool],
    reasons: dict[str, str],
) -> None:
    _keep, osc, _xbox = _editors()
    edits.clear()
    osc.target = "reply"
    assert edits, "picking an OSC target wasn't an action edit"
