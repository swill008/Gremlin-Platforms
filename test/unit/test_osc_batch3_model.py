# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC batch 3, the page's models (D-09-OSC-EXTRAS).

Invert on the parent row and a deadzone in Edit Settings for axis inputs
(S161), the encoder acceleration preset (S164), TouchOSC layout preview and
import through the Import path (S162), the Server tab's allowed senders and
the OSC Monitor's blocked rows with "Allow this sender" (S160).

Spec: 09 S160-S162, S164.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import osc_device_file, osc_traffic, shared_state
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import osc_device_model
from gremlin.ui.osc_device_model import OscDeviceManagementModel
from gremlin.ui.osc_layout import OscLayoutModel, settings_line
from gremlin.ui.osc_monitor_model import OscMonitorModel
from gremlin.ui.osc_option import OscServerModel


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def page(qapp: object, modules: Path) -> Iterator[OscLayoutModel]:
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    saved = shared_state.current_profile
    shared_state.current_profile = Profile()
    model = OscLayoutModel()
    yield model
    model.endPane()
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    shared_state.current_profile = saved


def _add(address: str, **settings: Any) -> str:  # noqa: ANN401
    row, error = osc_device_model.add_input({"address": address, **settings})
    assert row is not None and not error, error
    osc_device_model._emit_modified()
    return row.uid


def _key(address: str) -> str:
    row = OscDevice().find_address(address)
    assert row is not None
    word = "axis" if row.input_type == InputType.JoystickAxis else "button"
    return f"parent:{word}:{row.input_id}"


def _parent(model: OscLayoutModel, address: str) -> dict:
    names = {int(k): bytes(v.data()).decode() for k, v in model.roleNames().items()}
    key = _key(address)
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        row = {name: model.data(index, role) for role, name in names.items()}
        if row["key"] == key:
            return row
    raise AssertionError(f"no row {key}")


def _row(address: str) -> Any:  # noqa: ANN401
    row = OscDevice().find_address(address)
    assert row is not None
    return row


# -- Invert and deadzone (S161) ----------------------------------------------


def test_axis_parent_row_offers_invert_and_a_button_does_not(
    page: OscLayoutModel,
) -> None:
    _add("/fader", mode="axis")
    _add("/knob", mode="encoder", enc_output="axis")
    _add("/btn", mode="button")
    assert _parent(page, "/fader")["canInvert"] is True
    assert _parent(page, "/knob")["canInvert"] is True
    assert _parent(page, "/btn")["canInvert"] is False
    assert _parent(page, "/fader")["inverted"] is False


def test_invert_check_box_is_one_undo_step(page: OscLayoutModel) -> None:
    _add("/fader", mode="axis")
    assert page.setInverted(_key("/fader"), True) is True
    assert _row("/fader").invert is True
    assert _parent(page, "/fader")["inverted"] is True
    assert "Inverted" in settings_line(_row("/fader"))
    assert page.property("lastChange") == "Last change: Turn Invert On · /fader"
    page.undo()
    assert _row("/fader").invert is False
    assert _parent(page, "/fader")["inverted"] is False
    page.redo()
    assert _row("/fader").invert is True


def test_invert_is_refused_on_a_button(page: OscLayoutModel) -> None:
    _add("/btn", mode="button")
    assert page.setInverted(_key("/btn"), True) is False
    assert _row("/btn").invert is False


def test_edit_settings_deadzone_on_several_axes(page: OscLayoutModel) -> None:
    _add("/a", mode="axis")
    _add("/b", mode="axis")
    keys = [_key("/a"), _key("/b")]
    shared = page.editSettingsFor(keys)
    assert shared["shaping"] is True
    assert shared["invert"] is False
    assert shared["deadzone_low"] == 0.0 and shared["deadzone_high"] == 0.0

    assert page.applySettings(keys, {"deadzone_low": -0.1, "deadzone_high": 0.2}) == ""
    assert _row("/a").deadzone == (-0.1, 0.2)
    assert _row("/b").deadzone == (-0.1, 0.2)
    assert "Deadzone: -0.1..0.2" in settings_line(_row("/a"))

    # Only high changed on /a: low stays its own; then the pair differs.
    assert page.applySettings([_key("/a")], {"deadzone_high": 0.3}) == ""
    assert _row("/a").deadzone == (-0.1, 0.3)
    mixed = page.editSettingsFor(keys)
    assert mixed["deadzone_low"] == -0.1
    assert mixed["deadzone_high"] == ""
    assert "deadzone_high" in mixed["mixed"]

    page.undo()
    assert _row("/a").deadzone == (-0.1, 0.2)


def test_bad_deadzone_is_refused_with_a_reason(page: OscLayoutModel) -> None:
    _add("/a", mode="axis")
    why = page.applySettings([_key("/a")], {"deadzone_low": 0.5})
    assert "Deadzone low must be from -0.99 to 0." in why
    assert _row("/a").deadzone == (0.0, 0.0)


def test_shaping_is_not_offered_when_a_button_is_chosen(page: OscLayoutModel) -> None:
    _add("/a", mode="axis")
    _add("/btn", mode="button")
    shared = page.editSettingsFor([_key("/a"), _key("/btn")])
    assert shared["shaping"] is False
    assert "deadzone_low" not in shared
    # Sent anyway: the button keeps no shaping.
    assert page.applySettings([_key("/btn")], {"invert": True}) == ""
    assert _row("/btn").invert is False


# -- Encoder acceleration (S164) ---------------------------------------------


def test_accel_preset_from_the_add_window_is_saved(page: OscLayoutModel) -> None:
    manage = OscDeviceManagementModel()
    assert [c["value"] for c in manage.encAccelChoices()] == [
        "off", "low", "medium", "high",
    ]
    assert manage.createConfiguredInput(
        {"address": "/enc", "mode": "encoder", "enc_accel": "Medium"}
    )
    assert _row("/enc").enc_accel == "medium"
    assert manage.inputSettings(_row("/enc").uid)["enc_accel"] == "medium"
    assert "Acceleration: Medium" in settings_line(_row("/enc"))
    saved = OscDevice().rows.to_dict()["inputs"]
    assert [r["enc_accel"] for r in saved] == ["medium"]


def test_accel_preset_in_edit_settings(page: OscLayoutModel) -> None:
    _add("/enc", mode="encoder")
    key = _key("/enc")
    assert page.editSettingsFor([key])["enc_accel"] == "off"
    assert page.applySettings([key], {"enc_accel": "high"}) == ""
    assert _row("/enc").enc_accel == "high"
    page.undo()
    assert _row("/enc").enc_accel == "off"


# -- TouchOSC layout (S162) --------------------------------------------------


def _node(kind: str, name: str, args: str = "<partial><type>VALUE</type>"
          "<conversion>FLOAT</conversion><value>x</value><scaleMin>0</scaleMin>"
          "<scaleMax>1</scaleMax></partial>") -> str:
    path = (
        "<partial><type>CONSTANT</type><conversion>STRING</conversion>"
        "<value>/</value><scaleMin>0</scaleMin><scaleMax>1</scaleMax></partial>"
        "<partial><type>PROPERTY</type><conversion>STRING</conversion>"
        "<value>name</value><scaleMin>0</scaleMin><scaleMax>1</scaleMax></partial>"
    )
    return (
        f'<node ID="id-{name}" type="{kind}"><properties>'
        f'<property type="s"><key>name</key><value>{name}</value></property>'
        "</properties><values/><messages><osc><enabled>1</enabled><send>1</send>"
        f"<receive>1</receive><path>{path}</path><arguments>{args}</arguments>"
        "</osc></messages><children/></node>"
    )


def _tosc(tmp_path: Path) -> Path:
    body = (
        _node("FADER", "vol") + _node("BUTTON", "go")
        + '<node ID="id-l" type="LABEL"><properties><property type="s"><key>name'
        "</key><value>title</value></property></properties><values/><messages/>"
        "<children/></node>"
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><lexml version="3">{body}</lexml>'
    path = tmp_path / "layout.tosc"
    path.write_bytes(zlib.compress(xml.encode("utf-8")))
    return path


def test_touchosc_preview_lists_rows_ticked_and_skipped(
    page: OscLayoutModel, tmp_path: Path
) -> None:
    _add("/go", mode="button")
    manage = OscDeviceManagementModel()
    preview = manage.previewTouchOsc(_tosc(tmp_path).as_uri())
    assert preview["error"] == ""
    rows = {r["address"]: r for r in preview["rows"]}
    assert rows["/vol"]["ticked"] is True and rows["/vol"]["kindText"] == "Axis"
    assert rows["/go"]["exists"] is True and rows["/go"]["ticked"] is False
    assert any("title" in note for note in preview["skipped"])


def test_touchosc_import_adds_the_chosen_rows_as_one_undo_step(
    page: OscLayoutModel, tmp_path: Path
) -> None:
    _add("/go", mode="button")
    manage = OscDeviceManagementModel()
    added: list[str] = []
    manage.inputAdded.connect(added.append)
    path = str(_tosc(tmp_path))
    every = [r["index"] for r in manage.previewTouchOsc(path)["rows"]]
    result = manage.importTouchOsc(path, every)
    assert result.startswith("Added 1, skipped 1")
    vol = _row("/vol")
    assert vol.mode == "axis"
    assert added == [vol.uid]
    assert page.property("lastChange") == "Last change: Import /vol"
    page.undo()
    assert OscDevice().find_address("/vol") is None
    assert OscDevice().find_address("/go") is not None


def test_touchosc_refused_file_reports_why(
    page: OscLayoutModel, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.tosc"
    bad.write_bytes(b"not a layout")
    manage = OscDeviceManagementModel()
    preview = manage.previewTouchOsc(str(bad))
    assert preview["rows"] == [] and preview["error"]
    assert manage.importTouchOsc(str(bad), [0]) == preview["error"]


# -- Allowed senders (S160) --------------------------------------------------


def test_server_tab_allow_list_add_validate_remove(qapp: object, modules: Path) -> None:
    server = OscServerModel()
    assert server.property("allowSenders") == []
    assert server.addSender("192.168.1.7/24") is True
    assert server.addSender("10.0.0.5") is True
    assert server.property("allowSenders") == ["192.168.1.0/24", "10.0.0.5"]
    assert osc_device_file.read_server()["allow_senders"] == [
        "192.168.1.0/24", "10.0.0.5",
    ]
    assert server.addSender("not an address") is False
    assert "192.168.1.5" in server.property("message")
    assert server.addSender("10.0.0.5") is False
    assert server.property("message") == "10.0.0.5 is already in the list."
    assert server.setValue("allow_senders", True) is False
    assert server.removeSender("10.0.0.5") is True
    assert server.property("allowSenders") == ["192.168.1.0/24"]
    assert server.removeSender("10.0.0.5") is False


@pytest.fixture
def monitor(qapp: object, modules: Path) -> Iterator[OscMonitorModel]:
    osc_traffic.clear()
    model = OscMonitorModel()
    yield model
    model.setProperty("active", False)
    osc_traffic.clear()


def _monitor_rows(model: OscMonitorModel) -> list[dict]:
    names = {int(k): bytes(v.data()).decode() for k, v in model.roleNames().items()}
    return [
        {name: model.data(model.index(r, 0), role) for role, name in names.items()}
        for r in range(model.rowCount())
    ]


def test_monitor_shows_blocked_and_allow_this_sender_adds_it(
    monitor: OscMonitorModel,
) -> None:
    osc_traffic.note("in", "/x", [1], ("192.168.1.9", 9001), ["blocked"])
    osc_traffic.note("in", "/y", [1], ("127.0.0.1", 9001), [])
    monitor.setProperty("active", True)
    blocked, open_row = _monitor_rows(monitor)
    assert blocked["blocked"] is True
    assert blocked["matched"] == "blocked"
    assert blocked["noInput"] is False
    assert blocked["senderHost"] == "192.168.1.9"
    assert open_row["blocked"] is False and open_row["noInput"] is True

    assert monitor.allowSender(blocked["senderHost"]) == ""
    assert osc_device_file.read_server()["allow_senders"] == ["192.168.1.9"]
    assert monitor.allowSender("192.168.1.9") == ""  # already there
    assert monitor.allowSender("nope") != ""


def test_import_reads_a_picked_text_file(tmp_path) -> None:  # noqa: ANN001
    from gremlin.ui import osc_device_model

    path = tmp_path / "addresses.txt"
    path.write_text("/deck/1\n/fader/1 axis\n", encoding="utf-8")
    got = osc_device_model.read_import_text(path.as_uri())
    assert got == {"text": "/deck/1\n/fader/1 axis\n", "error": ""}
    assert osc_device_model.read_import_text(str(tmp_path / "missing.txt"))["error"]
    big = tmp_path / "big.txt"
    big.write_text("x" * (osc_device_model.IMPORT_TEXT_MAX + 1), encoding="utf-8")
    assert "too big" in osc_device_model.read_import_text(str(big))["error"]
