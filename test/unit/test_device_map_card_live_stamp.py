# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Map card's liveStamp (qml/DeviceMapCard.qml) feeds the face
and its editor (VkbRigFace onLiveStampChanged, VkbRigEditor tick, find and
hot pulse). It read `count` on the mapped models, which they don't have:
the sum was NaN, so liveStamp stayed 0 and never told the face anything
(audit 2026-10-12 BRIDGE item 1). The test runs the card's own liveStamp
expression against the real mapped models."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.append(".")

import pytest
from PySide6 import QtCore, QtQml

from gremlin.signal import signal

_ROOT = Path(__file__).resolve().parents[2]
_CARD = _ROOT / "qml" / "DeviceMapCard.qml"
_LINE = re.compile(r"^\s*property int liveStamp:\s*(.+)$", re.MULTILINE)


@pytest.fixture(scope="session", autouse=True)
def terminate_event_listener(request: pytest.FixtureRequest) -> None:
    import gremlin.event_handler

    request.addfinalizer(lambda: gremlin.event_handler.EventListener().terminate())


def _card_expression() -> str:
    found = _LINE.search(_CARD.read_text(encoding="utf-8"))
    assert found, "DeviceMapCard.qml has no 'property int liveStamp:' line"
    return found.group(1).strip()


def _harness() -> str:
    return f"""
import QtQuick
import SmallfixLiveStamp

Item {{
    property int axisStamp: 0
    property int buttonStamp: 0
    property int hatStamp: 0
    property int liveStamp: {_card_expression()}
    property int changes: 0
    onLiveStampChanged: changes++
    MappedButtonModel {{ id: _buttons }}
    MappedAxisModel {{ id: _axes }}
    MappedHatModel {{ id: _hats }}
}}
"""


def test_live_stamp_changes_on_live_input_and_binding_changes(qtbot: object) -> None:
    from gremlin.ui.input_pairing import (
        MappedAxisModel,
        MappedButtonModel,
        MappedHatModel,
    )

    for cls in (MappedButtonModel, MappedAxisModel, MappedHatModel):
        uri, name = "SmallfixLiveStamp", cls.__name__
        QtQml.qmlRegisterType(cls, uri, 1, 0, name)  # pyright: ignore
    engine = QtQml.QQmlEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    comp = QtQml.QQmlComponent(engine)
    comp.setData(_harness().encode("utf-8"), QtCore.QUrl.fromLocalFile(str(_CARD)))
    root = comp.create()
    assert root is not None, comp.errorString()
    try:
        start = root.property("liveStamp")
        root.setProperty("buttonStamp", 5)
        after_input = root.property("liveStamp")
        assert after_input != start, (
            f"liveStamp did not follow live input ({start} -> {after_input}); "
            f"warnings: {warnings}"
        )
        signal.bindingsChanged.emit()
        qtbot.wait(20)  # type: ignore[attr-defined]
        after_bindings = root.property("liveStamp")
        assert after_bindings != after_input, (
            "liveStamp did not change when what drives what changed "
            f"({after_input} -> {after_bindings}); warnings: {warnings}"
        )
        assert root.property("changes") >= 2
    finally:
        root.deleteLater()
        engine.deleteLater()
        qtbot.wait(10)  # type: ignore[attr-defined]


def test_mapped_model_stamp_goes_up_on_each_reload(qtbot: object) -> None:
    from gremlin.ui.input_pairing import MappedButtonModel

    model = MappedButtonModel()
    try:
        seen: list[int] = []
        model.stampChanged.connect(lambda: seen.append(model.property("stamp")))
        before = model.property("stamp")
        signal.bindingsChanged.emit()
        signal.bindingsChanged.emit()
        assert model.property("stamp") == before + 2
        assert seen == [before + 1, before + 2]
    finally:
        model.deleteLater()
        qtbot.wait(10)  # type: ignore[attr-defined]
