# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC Feedback sources from batch 2 (09 S149, S153, S157-S158): an
action's state and Running / Paused as sources, the "Show under this input"
key, where each row shows on the OSC page, the page's by-id edits, and
outgoing addresses refusing patterns. No network: osc_output is a stand-in
that records the sends."""

from __future__ import annotations

import types
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

import gremlin
from gremlin import action_state, osc, osc_feedback, osc_pattern
from gremlin import osc_device_file as odf
from gremlin.ui import osc_feedback_model as fbm


class FakeOutput(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("gremlin.osc_output")
        self.sent: list[tuple] = []

    def send(
        self, target_id: str, address: str, values: list, types: list | None = None
    ) -> bool:
        self.sent.append((target_id, address, list(values), types))
        return True


class FakeFunctor:
    """A functor with feedback_state(), as Smart Toggle / Tempo have."""

    def __init__(self, action_id: uuid.UUID, on: bool) -> None:
        self.data = SimpleNamespace(id=action_id)
        self.on = on

    def feedback_state(self) -> bool:
        return self.on


def _row(rid: str, source: dict, address: str = "/k", **extra: object) -> dict:
    row = {
        "id": rid,
        "enabled": True,
        "source": {"device": None, "input": None, **source},
        "target": "t1",
        "address": address,
        "min": 0.0,
        "max": 1.0,
        "type": "auto",
    }
    row.update(extra)
    return row


@pytest.fixture
def running(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    fake = FakeOutput()
    monkeypatch.setattr(gremlin, "osc_output", fake, raising=False)
    action_state.clear()
    feedback = osc_feedback.OscFeedback()
    feedback._running = True
    # No rate limit: every change sends at once.
    feedback._settings = dict(osc_feedback._DEFAULTS, feedback_rate=0)
    yield SimpleNamespace(fb=feedback, out=fake)
    action_state.clear()


# -- action state and paused sources (S157, S158) ------------------------


def test_action_state_row_sends_on_and_off_values(running: SimpleNamespace) -> None:
    aid = uuid.uuid4()
    functor = FakeFunctor(aid, on=False)
    action_state.register(functor)
    row = _row(
        "a",
        {"kind": "action_state", "action": str(aid)},
        off_value="#333333",
        on_value="#2a7a46",
        address="/location/1/0/0/style/bgcolor",
    )
    running.fb._rows = odf.clean_feedback([row])
    running.fb.poll()
    assert running.out.sent[-1][2] == [0x33, 0x33, 0x33]
    functor.on = True
    running.fb.poll()
    assert running.out.sent[-1][2] == [0x2A, 0x7A, 0x46]


def test_action_state_any_functor_on_means_on(running: SimpleNamespace) -> None:
    aid = uuid.uuid4()
    off, on = FakeFunctor(aid, False), FakeFunctor(aid, True)
    action_state.register(off)
    action_state.register(on)
    row = odf.clean_feedback(
        [_row("a", {"kind": "action_state", "action": str(aid)}, max=5.0)]
    )[0]
    assert running.fb.value_of(row) == [5.0]


def test_missing_action_sends_nothing(running: SimpleNamespace) -> None:
    row = _row("a", {"kind": "action_state", "action": str(uuid.uuid4())})
    running.fb._rows = odf.clean_feedback([row])
    running.fb.poll()
    assert running.fb.resend_all("test") == 0
    assert running.out.sent == []


def test_running_paused_source_is_on_while_running(
    running: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    state: dict[str, Any] = {"paused": False}
    monkeypatch.setattr(action_state, "paused_state", lambda: state["paused"])
    row = odf.clean_feedback(
        [_row("p", {"kind": "paused"}, min=0.0, max=1.0, type="int")]
    )[0]
    assert row["source"]["kind"] == "paused"
    # On = Running, off = Paused (user, 2026-10-10, RP1).
    assert running.fb.value_of(row) == [1]
    state["paused"] = True
    assert running.fb.value_of(row) == [0]
    state["paused"] = None
    assert running.fb.value_of(row) is None


# -- the file keeps the new keys -------------------------------------------


def test_cleaning_keeps_input_key_and_action_id() -> None:
    aid = str(uuid.uuid4())
    rows = odf.clean_feedback(
        [
            _row("a", {"kind": "action_state", "action": aid}, input="osc-uid-1"),
            _row("b", {"kind": "mode"}, input=""),
        ]
    )
    assert rows[0]["input"] == "osc-uid-1"
    assert rows[0]["source"]["kind"] == "action_state"
    assert rows[0]["source"]["action"] == aid
    assert "input" not in rows[1]
    assert "action" not in rows[1]["source"]


# -- placement on the OSC page (S153) --------------------------------------


class FakeAction:
    def __init__(self, children: list[FakeAction] | None = None) -> None:
        self.id = uuid.uuid4()
        self.children = children or []

    def get_actions(self) -> tuple[list, list]:
        return (self.children, ["children"] * len(self.children))


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A profile whose OSC input 7 holds a container with a nested action."""
    inner = FakeAction()
    outer = FakeAction([inner])
    item = SimpleNamespace(
        input_type="button",
        input_id=7,
        action_sequences=[SimpleNamespace(root_action=outer)],
    )
    rows = SimpleNamespace(uid_of=lambda kind, number: f"osc-{number}")
    monkeypatch.setattr(osc, "OscDevice", lambda: SimpleNamespace(rows=rows))
    return SimpleNamespace(
        inputs={osc.OSC_DEVICE_UUID: [item]}, inner=inner, outer=outer
    )


def test_placement_rules(profile: SimpleNamespace) -> None:
    rows = odf.clean_feedback(
        [
            _row("echo", {"kind": "osc_input", "input": "osc-3"}),
            _row("nested", {"kind": "action_state", "action": str(profile.inner.id)}),
            _row("gone", {"kind": "action_state", "action": str(uuid.uuid4())}),
            _row("mode", {"kind": "mode"}),
            _row("pinned", {"kind": "mode"}, input="osc-9"),
            _row("over", {"kind": "osc_input", "input": "osc-3"}, input="osc-4"),
        ]
    )
    placed = {r["id"]: r["placement"] for r in fbm.rows_for_page(rows, profile)}
    assert placed == {
        "echo": "osc-3",
        "nested": "osc-7",
        "gone": None,
        "mode": None,
        "pinned": "osc-9",
        "over": "osc-4",
    }


# -- the model's by-id edits and outgoing refusals (S149) -----------------


@pytest.fixture
def model(qapp: object, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    store = {"rows": odf.clean_feedback([_row("r1", {"kind": "mode"}, address="/m")])}

    def write(rows: list[dict], who: str = "") -> bool:
        store["rows"] = odf.clean_feedback(rows)
        return True

    monkeypatch.setattr(odf, "read_server", lambda: {})
    monkeypatch.setattr(odf, "read_targets", lambda: [])
    monkeypatch.setattr(odf, "read_feedback", lambda: [dict(r) for r in store["rows"]])
    monkeypatch.setattr(odf, "write_feedback", write)
    monkeypatch.setattr(fbm, "_current_profile", lambda: None)
    return SimpleNamespace(m=fbm.OscFeedbackModel(), store=store)


def test_feedback_row_address_refuses_patterns(model: SimpleNamespace) -> None:
    m = model.m
    for address in ("/fader/*", "/f?", "/f/[12]", "/f/{a,b}"):
        assert m.setRowValue(0, "address", address) is False
        assert m.message == osc_pattern.NO_PATTERN
        assert fbm.check_address(address) == osc_pattern.NO_PATTERN
    assert model.store["rows"][0]["address"] == "/m"
    assert m.addRowFor({"address": "/x/*"}) == ""
    assert len(model.store["rows"]) == 1
    assert m.setRowValue(0, "address", "/fader/1") is True


def test_by_id_edits_enable_duplicate_show_under(model: SimpleNamespace) -> None:
    m = model.m
    assert m.setRowEnabled("r1", False) is True
    assert model.store["rows"][0]["enabled"] is False
    new_id = m.duplicateRow("r1")
    assert new_id and new_id != "r1"
    assert [r["id"] for r in model.store["rows"]] == ["r1", new_id]
    assert m.setRowValueById(new_id, "showUnder", "osc-2") is True
    assert m.rowById(new_id)["placement"] == "osc-2"
    assert m.rowById("r1")["placement"] == ""
    assert m.removeRowById("r1") is True
    assert [r["id"] for r in model.store["rows"]] == [new_id]
    added = m.addRowFor(
        {"source": {"kind": "action_state", "action": "abc"}, "address": "/k"}
    )
    assert m.rowById(added)["action"] == "abc"
    assert m.actionMissing(added) is True
    assert m.duplicateRow("nope") == ""


def test_send_osc_refuses_a_pattern_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(odf, "read_targets", lambda: [])
    from action_plugins import send_osc

    assert send_osc.address_error("/fader/*") == osc_pattern.NO_PATTERN
    assert send_osc.address_error("/fader/1") == ""
    data = send_osc.SendOscData()
    data.address = "/fader/{1,2}"
    messages = [f.message for f in data.user_feedback()]
    assert messages == [osc_pattern.NO_PATTERN]
    data.address = "/fader/1"
    assert data.user_feedback() == []
