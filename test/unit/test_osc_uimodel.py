# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC device page list model (D-09-OSC-INPUT, D-09-OSC-FAULTS): per-input
settings from the Add window, Import suffixes and result text, address
checks, delete by uid, selection after Sort. Edit Settings goes through the
OSC page's OscLayoutModel.applySettings (09 S146), the path the page uses.
Slots are called from real QML so the QVariantMap / return types are the
ones the page uses."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore, QtQml

from gremlin import shared_state
from gremlin.osc import OscDevice
from gremlin.types import InputType
from gremlin.ui.osc_device_model import (
    OscDeviceManagementModel,
    has_actions,
    settings_of,
)
from gremlin.ui.osc_layout import OscLayoutModel


@pytest.fixture
def model(qapp: object) -> Iterator[OscDeviceManagementModel]:
    OscDevice().rows.reset()
    saved = shared_state.current_profile
    shared_state.current_profile = None
    m = OscDeviceManagementModel()
    yield m
    OscDevice().rows.reset()
    shared_state.current_profile = saved


@pytest.fixture
def page(
    model: OscDeviceManagementModel, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[OscLayoutModel]:
    """The OSC page's model (Edit Settings… applies through it, S146), with
    OSC's module file in a temporary modules folder."""
    from gremlin.modules import store
    from gremlin.profile import Profile

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    shared_state.current_profile = Profile()
    p = OscLayoutModel()
    yield p
    p.endPane()


def _qml(model: object, body: str) -> Any:  # noqa: ANN401
    """Run a JS expression in real QML with `m` = the model; returns it."""
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
    if hasattr(value, "toVariant"):
        value = value.toVariant()
    return value


def _rows() -> list[Any]:
    return list(OscDevice().rows.rows())


def _edit(page: OscLayoutModel, uid: str, settings: str) -> Any:  # noqa: ANN401
    """Edit Settings… OK on one input, as OscAddDialog sends it: the page's
    applySettings(keys, changed); "" or the refusal."""
    return _qml(page, f'm.applySettings([m.keyOfUid("{uid}")], {settings})')


def test_create_configured_input_saves_settings(
    model: OscDeviceManagementModel,
) -> None:
    ok = _qml(model, (
        'm.createConfiguredInput({address: "/fader/1", mode: "axis", '
        'cmd_mode: "message", source: 1, range_min: -1, range_max: 1, '
        'trigger: null, delay_ms: 300})'
    ))
    assert ok is True
    [row] = _rows()
    assert row.label == "/fader/1"
    assert row.input_type == InputType.JoystickAxis
    got = (row.mode, row.source, row.range_min, row.range_max)
    assert got == ("axis", 1, -1.0, 1.0)
    assert row.delay_ms == 300
    assert OscDevice().rows.dirty
    assert settings_of(row)["mode"] == "axis"


def test_data_mode_inputs_may_share_an_address(model: OscDeviceManagementModel) -> None:
    base = '{address: "/btn", mode: "button", cmd_mode: "data", data: %s}'
    assert _qml(model, "m.createConfiguredInput(%s)" % (base % '["1"]')) is True
    assert _qml(model, "m.createConfiguredInput(%s)" % (base % '["2"]')) is True
    assert _qml(model, "m.createConfiguredInput(%s)" % (base % '["2"]')) is False
    assert sorted(r.data[0] for r in _rows()) == ["1", "2"]


def test_old_create_mapped_input_still_works(model: OscDeviceManagementModel) -> None:
    model.createMappedInput("Button", "/x")
    model.createMappedInput("Axis", "")
    labels = sorted(r.label for r in _rows())
    assert labels == ["/osc/axis/1", "/x"]


def test_import_suffixes_and_result_text(model: OscDeviceManagementModel) -> None:
    text = "/a A\n/b, B\n/c BNP\n/d,C\n/e E\n/f Q\n/a A\nnot-an-address\n\n/g"
    result = _qml(model, "m.importInputs(%r)" % text)
    by = {r.label: r for r in _rows()}
    assert by["/a"].mode == "axis"
    assert by["/b"].mode == "button" and by["/b"].trigger is None
    assert by["/c"].mode == "button" and by["/c"].trigger is True
    assert by["/d"].mode == "change"
    # E: an encoder axis, format Auto (D-09-OSC-ENCODER), with no note.
    assert by["/e"].mode == "encoder"
    assert by["/e"].input_type == InputType.JoystickAxis
    assert (by["/e"].enc_format, by["/e"].enc_output) == ("auto", "axis")
    assert by["/f"].mode == "button"
    assert by["/g"].mode == "button"
    lines = result.splitlines()
    assert lines[0] == "Added 7, skipped 2"
    assert not any("/e E" in line for line in lines)
    assert any("/f Q" in line for line in lines)


def test_change_name_checks_the_address(
    model: OscDeviceManagementModel, page: OscLayoutModel
) -> None:
    model.createMappedInput("Button", "/one")
    model.createMappedInput("Button", "/two")
    uid = next(r.uid for r in _rows() if r.label == "/one")
    assert _edit(page, uid, '{address: "   "}') != ""
    assert _edit(page, uid, '{address: "noslash"}') != ""
    assert "already" in _edit(page, uid, '{address: "/two"}')
    assert _edit(page, uid, '{address: "/uno"}') == ""
    assert OscDevice().rows.by_uid(uid).label == "/uno"


def test_edit_settings_applies_to_the_input(
    model: OscDeviceManagementModel, page: OscLayoutModel
) -> None:
    model.createMappedInput("Button", "/p")
    uid = _rows()[0].uid
    assert _edit(page, uid, '{mode: "change", delay_ms: 50}') == ""
    row = OscDevice().rows.by_uid(uid)
    assert (row.mode, row.delay_ms) == ("change", 50)


def test_adding_an_existing_input_selects_it(model: OscDeviceManagementModel) -> None:
    """09 S14: adding an input that already exists selects the one there
    (OscPage selects on inputAdded), and makes no second one."""
    model.createMappedInput("Button", "/dup")
    [first] = _rows()
    picked: list[str] = []
    model.inputAdded.connect(picked.append)
    ok = _qml(model, 'm.createConfiguredInput({address: "/dup", mode: "button"})')
    assert ok is False
    assert [r.uid for r in _rows()] == [first.uid]
    assert picked == [first.uid]


def test_osc_row_description_is_the_input_name(
    model: OscDeviceManagementModel,
) -> None:
    """Q15: the description role is the model's own (no import-time patch)
    and shows the input name; an input with no item shows nothing."""
    import gremlin.ui.device_names  # noqa: F401  (imported by the app at start)
    from gremlin.osc import OSC_DEVICE_UUID
    from gremlin.profile import Profile

    assert OscDeviceManagementModel.data.__module__ == "gremlin.ui.osc_device_model"
    profile = Profile()
    shared_state.current_profile = profile
    model.createMappedInput("Button", "/named")
    model.createMappedInput("Button", "/bare")
    role = next(
        k for k, v in model.roles.items() if bytes(v.data()) == b"description"
    )
    by_label = {
        model.data(model.index(i, 0), QtCore.Qt.ItemDataRole.UserRole + 2): i
        for i in range(model.rowCount())
    }
    row = OscDevice().rows.by_uid(
        next(r.uid for r in _rows() if r.label == "/named")
    )
    item = profile.get_input_item(
        OSC_DEVICE_UUID, row.input_type, row.input_id, "Default", True
    )
    item.action_name = "Fire"
    assert model.data(model.index(by_label["/named"], 0), role) == "Fire"
    assert model.data(model.index(by_label["/bare"], 0), role) == ""


def test_listen_uses_the_window_settings(model: OscDeviceManagementModel) -> None:
    _qml(model, 'm.setCaptureSettings({mode: "change", cmd_mode: "data", '
                'delay_ms: 80})')
    model._on_learned("/learned", (3, "x"))
    [row] = _rows()
    assert (row.label, row.mode, row.cmd_mode, row.data, row.delay_ms) == (
        "/learned", "change", "data", ["3", "x"], 80,
    )


def test_type_change_refused_while_the_input_has_actions(
    model: OscDeviceManagementModel, page: OscLayoutModel
) -> None:
    from gremlin.osc import OSC_DEVICE_UUID
    from gremlin.profile import InputItemBinding, Profile

    profile = Profile()
    profile.modes.add_mode("Other")  # actions in a mode the page isn't showing
    shared_state.current_profile = profile
    model.createMappedInput("Button", "/held")
    row = _rows()[0]
    item = profile.get_input_item(
        OSC_DEVICE_UUID, row.input_type, row.input_id, "Other", True
    )
    item.action_sequences.append(InputItemBinding(item))  # an empty sequence
    assert has_actions(row) is True
    err = _edit(page, row.uid, '{mode: "axis"}')
    assert err.startswith("/held: Remove this input's actions first")
    assert OscDevice().rows.by_uid(row.uid).input_type == InputType.JoystickButton
    assert _edit(page, row.uid, '{mode: "change"}') == ""
    item.action_sequences.clear()
    profile.drop_inputs(OSC_DEVICE_UUID, [item])
    assert has_actions(OscDevice().rows.by_uid(row.uid)) is False
    assert _edit(page, row.uid, '{mode: "axis"}') == ""
