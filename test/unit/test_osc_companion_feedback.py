# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Companion feedback (D-09-OSC-COMPANION): the Add Row templates build
ordinary rows to the Companion target with Companion's /custom-variable and
/location API, and a row's Off/On values go out instead of Min/Max (a colour
to a key colour as three ints r g b). No network: osc_output is a stand-in."""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtTest

import gremlin
from gremlin import osc_device_file as odf
from gremlin import osc_feedback
from gremlin.modules import output
from gremlin.ui import osc_feedback_model
from gremlin.ui.osc_feedback_model import OscFeedbackModel


@pytest.fixture
def osc_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    file = tmp_path / "osc.json"
    monkeypatch.setattr(odf, "path", lambda: file)
    monkeypatch.setattr(osc_feedback_model, "_vjoy_ids", lambda: [2])
    return file


def _companion() -> dict:
    found = [t for t in odf.read_targets() if t["name"] == "Companion"]
    assert len(found) == 1
    return found[0]


# -- templates ---------------------------------------------------------------


def test_custom_variable_template_adds_companion_target_and_row(
    qapp: object, osc_file: Path
) -> None:
    model = OscFeedbackModel()
    said = model.addTemplateRow("companion_variable", {"name": "gremlin_mode"})
    assert said == "Create the custom variable in Companion first."
    target = _companion()
    assert (target["host"], target["port"]) == ("127.0.0.1", 12321)
    [row] = odf.read_feedback()
    assert row["address"] == "/custom-variable/gremlin_mode/value"
    assert row["type"] == "text"
    assert row["source"]["kind"] == "mode"
    assert row["target"] == target["id"]
    assert row["template"] == "companion_variable"
    # A second row reuses the target.
    model.addTemplateRow("companion_variable", {"name": "gear"})
    assert _companion()["id"] == target["id"]
    assert odf.read_feedback()[1]["address"] == "/custom-variable/gear/value"


def test_key_text_template_uses_location_api(qapp: object, osc_file: Path) -> None:
    model = OscFeedbackModel()
    model.addTemplateRow("companion_text", {"page": "2", "row": "1", "column": "3"})
    [row] = odf.read_feedback()
    assert row["address"] == "/location/2/1/3/style/text"
    assert row["type"] == "text"
    assert row["target"] == _companion()["id"]


def test_key_colour_template_has_off_on_colours(qapp: object, osc_file: Path) -> None:
    model = OscFeedbackModel()
    model.addTemplateRow("companion_colour", {"page": 1, "row": 0, "column": 0})
    [row] = odf.read_feedback()
    assert row["address"] == "/location/1/0/0/style/bgcolor"
    assert (row["off_value"], row["on_value"]) == ("#333333", "#2a7a46")
    assert row["source"] == {"kind": "vjoy_button", "device": 2, "input": 1}
    assert row["template"] == "companion_colour"
    shown = model.rows[0]
    assert (shown["offValue"], shown["onValue"]) == ("#333333", "#2a7a46")


def test_bad_template_fields_add_nothing(qapp: object, osc_file: Path) -> None:
    model = OscFeedbackModel()
    assert "no spaces" in model.addTemplateRow("companion_variable", {"name": "a b"})
    assert "1 or more" in model.addTemplateRow("companion_text", {"page": "0"})
    assert "#rrggbb" in model.addTemplateRow(
        "companion_colour", {"page": 1, "row": 0, "column": 0, "on": "green"}
    )
    assert odf.read_feedback() == []
    assert not [t for t in odf.read_targets() if t["name"] == "Companion"]


def test_blank_row_and_off_on_fields(qapp: object, osc_file: Path) -> None:
    model = OscFeedbackModel()
    model.addTemplateRow("blank", {})
    assert odf.read_feedback()[0].get("off_value") is None
    assert model.setRowValue(0, "off_value", "#FF0000")
    assert model.setRowValue(0, "on_value", "3")
    row = odf.read_feedback()[0]
    assert (row["off_value"], row["on_value"]) == ("#FF0000", 3)
    assert model.setRowValue(0, "on_value", "")
    assert odf.read_feedback()[0].get("on_value") is None


def test_clean_feedback_keeps_off_on_and_template() -> None:
    [row] = odf.clean_feedback(
        [{"off_value": " #333333 ", "on_value": 2, "template": "companion_colour"}]
    )
    assert (row["off_value"], row["on_value"], row["template"]) == (
        "#333333",
        2,
        "companion_colour",
    )
    [row] = odf.clean_feedback([{"off_value": "", "template": "bank"}])
    # Not set: the keys stay out (rows without them are written as before).
    assert not {"off_value", "on_value", "template"} & set(row)


# -- off/on values at run time -----------------------------------------------


class FakeOutput(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("gremlin.osc_output")
        self.sent: list[tuple] = []

    def send(
        self, target_id: str, address: str, values: list, types: list | None = None
    ) -> bool:
        self.sent.append((target_id, address, list(values), types))
        return True

    def note_sender(self, host: str, port: int) -> None:
        pass


@pytest.fixture
def fb(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    server: dict[str, Any] = {
        "feedback_enabled": True,
        "resend_run": False,
        "resend_mode": False,
        "resend_profile": False,
        "sync_enabled": False,
        "feedback_rate": 1000,
    }
    rows: list[dict] = []
    vjoy: dict[tuple, Any] = {}
    fake = FakeOutput()
    monkeypatch.setitem(sys.modules, "gremlin.osc_output", fake)
    monkeypatch.setattr(gremlin, "osc_output", fake, raising=False)
    monkeypatch.setattr(odf, "read_server", lambda: dict(server))
    monkeypatch.setattr(
        odf, "read_feedback", lambda: odf.clean_feedback([dict(r) for r in rows])
    )
    monkeypatch.setattr(
        output, "vjoy_value", lambda vid, kind, iid: vjoy.get((vid, kind, iid), False)
    )
    osc_feedback.stop()
    osc_feedback._settings = None
    osc_feedback.instance()._profile_path = None
    yield SimpleNamespace(rows=rows, vjoy=vjoy, out=fake)
    osc_feedback.stop()
    osc_feedback._settings = None


def _row(rid: str, address: str, button: int, **extra: object) -> dict:
    row = {
        "id": rid,
        "enabled": True,
        "source": {"kind": "vjoy_button", "device": 1, "input": button},
        "target": "comp",
        "address": address,
        "min": 0.0,
        "max": 1.0,
        "type": "auto",
    }
    row.update(extra)
    return row


def _press(fb: SimpleNamespace, button: int, on: bool) -> list[tuple]:
    fb.out.sent.clear()
    fb.vjoy[(1, "button", button)] = on
    osc_feedback.instance().poll()
    # Past the rate limit (1 ms) so a send held back goes too.
    QtTest.QTest.qWait(5)
    osc_feedback.instance().poll()
    return list(fb.out.sent)


def test_colour_off_on_goes_as_three_ints(fb: SimpleNamespace) -> None:
    fb.rows.append(
        _row("c", "/location/1/0/0/style/bgcolor", 1,
             off_value="#333333", on_value="#2a7a46")
    )
    fb.rows.append(
        _row("t", "/location/1/0/1/style/color", 2,
             off_value="0 0 0", on_value="255 255 255")
    )
    osc_feedback.start()
    rgb = ["int", "int", "int"]
    assert _press(fb, 1, True) == [
        ("comp", "/location/1/0/0/style/bgcolor", [42, 122, 70], rgb)
    ]
    assert _press(fb, 1, False) == [
        ("comp", "/location/1/0/0/style/bgcolor", [51, 51, 51], rgb)
    ]
    assert _press(fb, 2, True) == [
        ("comp", "/location/1/0/1/style/color", [255, 255, 255], rgb)
    ]


def test_off_on_values_replace_min_max(fb: SimpleNamespace) -> None:
    fb.rows.append(
        _row("v", "/custom-variable/gear/value", 1, off_value="up", on_value="down")
    )
    fb.rows.append(_row("n", "/n", 2, off_value=10, on_value=20, type="int"))
    fb.rows.append(_row("m", "/m", 3, min=0.0, max=127.0, type="int"))
    osc_feedback.start()
    assert _press(fb, 1, True) == [
        ("comp", "/custom-variable/gear/value", ["down"], ["text"])
    ]
    assert _press(fb, 2, True) == [("comp", "/n", [20], ["int"])]
    assert _press(fb, 2, False) == [("comp", "/n", [10], ["int"])]
    # Not set: Min/Max as before.
    assert _press(fb, 3, True) == [("comp", "/m", [127], ["int"])]


# -- address case (HELP audit) -----------------------------------------------


def test_mixed_case_sync_address_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        odf,
        "read_server",
        lambda: {"sync_enabled": True, "sync_address": "/Gremlin/Sync"},
    )
    osc_feedback.stop()
    # Incoming addresses arrive casefolded.
    assert osc_feedback.handle_incoming("/gremlin/sync", (), None) is True
    assert osc_feedback.handle_incoming("/gremlin/other", (), None) is False


def test_auto_type_found_for_an_address_typed_in_another_case() -> None:
    from gremlin import osc_output

    osc_output.reset()
    try:
        osc_output.note_received_type("/fader", (5,))
        assert osc_output.received_type("/Fader", 0) == "int"
        assert osc_output.convert(3.0, "auto", "/Fader") == 3
    finally:
        osc_output.reset()
