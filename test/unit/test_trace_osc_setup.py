# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC "Setup and files" and script/condition trace lines (D-09-OSC-TRACE)
and the quiet logging fixes: unreadable rows logged once without a
traceback (E5), Bulk capture only in Trace (E6), TouchOSC refusals without
a traceback (E7), a missing OSC input in a condition bounded (E8), the
Monitor's swallowed errors logged (E10); Monitor hold/release written once;
a Run on a port already open says so; errors capped at 10, refusals not
(D-09-OSC-TRACE-ERRORS)."""

from __future__ import annotations

import json
import logging
import zlib
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import osc_device_file as odf
from gremlin import trace, util
from gremlin.modules import store
from test.unit._device_folders import put_module


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def at(self, level: int) -> list[str]:
        return [r.getMessage() for r in self.records if r.levelno == level]


@pytest.fixture
def logs() -> Iterator[_Records]:
    handler = _Records()
    loggers = [logging.getLogger(name) for name in ("system", "user")]
    levels = [lg.level for lg in loggers]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
    yield handler
    for lg, level in zip(loggers, levels):
        lg.removeHandler(handler)
        lg.setLevel(level)


@pytest.fixture
def traced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    trace.set_osc_all(True)
    trace.set_enabled(True)
    yield
    trace.set_enabled(False)
    trace.set_osc_all(False)  # the ticks live in the config: don't leak them
    trace._reset_for_tests()


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    from gremlin import history_modules

    monkeypatch.setattr(history_modules, "note_write", lambda *_a: None)
    return folder


def _osc_lines(area: str = "setup") -> list[str]:
    control = f"OSC {trace.OSC_AREA_NAMES[area]}"
    return [line[3] for line in trace.lines() if line[1] == control]


def _write_osc(folder: Path, doc: dict) -> None:
    put_module(folder, "OSC", json.dumps(doc))


# -- OSC/module.json (E5) --------------------------------------------------


def test_unreadable_row_is_one_warning_no_traceback_and_traced(
    modules: Path, logs: _Records, traced: None
) -> None:
    from gremlin.osc_rows import OscRows

    _write_osc(
        modules,
        {
            "inputs": [
                {"type": "button", "label": "/good", "mode": "button"},
                {"type": "button", "label": "/bad", "mode": "nonsense"},
            ],
            "server": {"port": "abc"},
        },
    )
    rows = OscRows()
    odf.load(rows)
    assert len(rows.rows()) == 1
    assert logs.at(logging.ERROR) == []  # no GremlinError traceback
    warnings = logs.at(logging.WARNING)
    assert len(warnings) == 1 and "/bad" in warnings[0]
    lines = _osc_lines()
    assert any(
        t.startswith("row 2 unreadable:") and t.endswith("(kept in the file)")
        for t in lines
    ), lines
    assert any(
        t.startswith("OSC/module.json loaded (1 inputs, 1 targets") for t in lines
    )
    assert "port abc cleaned to 8001" in lines


def test_missing_file_gives_defaults_and_a_line(
    modules: Path, logs: _Records, traced: None
) -> None:
    from gremlin.osc_rows import OscRows

    server = odf.load(OscRows())
    assert server["port"] == odf.SERVER_DEFAULTS["port"]
    assert any("OSC/module.json missing" in t for t in _osc_lines())


def test_save_and_settings_writes_are_traced(modules: Path, traced: None) -> None:
    from gremlin.osc_rows import OscRows
    from gremlin.types import InputType

    rows = OscRows()
    odf.load(rows)
    rows.create(InputType.JoystickButton, "/a", mode="button")
    assert odf.save(rows)
    assert odf.write_server(dict(odf.SERVER_DEFAULTS, port=9001))
    lines = _osc_lines()
    assert "OSC/module.json saved (1 inputs)" in lines
    assert "OSC/module.json saved (server settings)" in lines


# -- TouchOSC (E7) -----------------------------------------------------------


def test_touchosc_refusal_is_shown_with_one_warning_no_traceback(
    tmp_path: Path, logs: _Records, traced: None
) -> None:
    from gremlin.ui import osc_device_model as odm

    bad = tmp_path / "bad.tosc"
    bad.write_bytes(b"not a layout")
    rows, skipped, error = odm.touchosc_rows(str(bad))
    assert rows == [] and error == "Not a TouchOSC layout (.tosc) file."
    assert logs.at(logging.ERROR) == []
    assert len(logs.at(logging.WARNING)) == 1
    assert any("TouchOSC" in t and "refused" in t for t in _osc_lines())


def test_touchosc_skipped_controls_are_traced(tmp_path: Path, traced: None) -> None:
    from gremlin.ui import osc_device_model as odm

    body = (
        '<node ID="a" type="LABEL"><properties><property type="s"><key>name'
        "</key><value>title</value></property></properties><values/>"
        "<messages/><children/></node>"
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><lexml version="3">{body}</lexml>'
    path = tmp_path / "l.tosc"
    path.write_bytes(zlib.compress(xml.encode("utf-8")))
    rows, skipped, error = odm.touchosc_rows(str(path))
    assert error == "" and skipped
    assert any(t.startswith("TouchOSC skipped title (LABEL)") for t in _osc_lines())


def test_import_refused_input_has_no_traceback(
    logs: _Records, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.error import GremlinError
    from gremlin.ui import osc_device_model as odm

    class Rows:
        def create(self, *_a: object, **_k: object) -> None:
            raise GremlinError("OSC input id 3 already exists")

    monkeypatch.setattr(odm, "_rows", lambda: Rows())
    monkeypatch.setattr(odm, "find_duplicate", lambda *_a: None)
    row, error = odm.add_input({"address": "/x", "mode": "button"})
    assert row is None and "already exists" in error
    assert logs.at(logging.ERROR) == []


# -- Listen / Bulk (E6) ------------------------------------------------------


def test_bulk_skip_and_debounce_are_trace_only(
    logs: _Records, traced: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import osc_bulk

    monkeypatch.setattr(
        osc_bulk,
        "OscDevice",
        lambda: SimpleNamespace(
            rows=SimpleNamespace(answered_by=lambda a: True, matches=lambda *a: [])
        ),
    )
    model = SimpleNamespace(_bulk=True, _bulk_settings={"mode": "button"})
    osc_bulk.on_bulk_learned(model, "/known", (1.0,))
    osc_bulk.on_bulk_learned(model, "/known", (1.0,))
    assert osc_bulk.bulk_skipped(model) == 1
    assert logs.at(logging.INFO) == []
    lines = _osc_lines()
    assert "Bulk skipped /known (already answered)" in lines
    assert any(t.startswith("Bulk skipped /known (repeat within") for t in lines)


def test_listen_owner_drop_is_traced(
    traced: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import osc_device_model

    monkeypatch.setattr(
        osc_device_model,
        "OscRuntime",
        lambda: SimpleNamespace(listens_for=lambda o: False),
    )
    # The model checks it owns the Listen before Bulk capture sees anything.
    osc_device_model.OscDeviceManagementModel._on_learned(
        SimpleNamespace(_bulk=True), "/x", ()
    )
    assert any(
        t.startswith("Listen: /x not taken (another window listens)")
        for t in _osc_lines()
    )


# -- Monitor (E10) -----------------------------------------------------------


def test_traffic_listener_error_is_logged_and_traced(
    logs: _Records, traced: None
) -> None:
    from gremlin import osc_traffic

    def broken(entry: dict) -> None:
        raise RuntimeError("boom")

    osc_traffic.add_listener(broken)
    try:
        osc_traffic._call_listeners({"address": "/a"})
    finally:
        osc_traffic.remove_listener(broken)
    assert any("boom" in t for t in logs.at(logging.DEBUG))
    assert any("Monitor" in t and "boom" in t for t in _osc_lines())


class _FakeListener:
    host = "127.0.0.1"
    port = 9000

    def bound_port(self) -> int:
        return self.port

    def stop(self) -> None:
        pass


def _open_runtime(monkeypatch: pytest.MonkeyPatch) -> object:
    """An OscRuntime whose port is already open on 127.0.0.1:9000 (a fake
    listener: nothing binds)."""
    from gremlin import osc

    runtime = osc.OscRuntime()
    monkeypatch.setattr(
        runtime, "_read_options", lambda: (True, "127.0.0.1", 9000)
    )
    runtime._listener = _FakeListener()  # type: ignore[assignment]
    return runtime


def test_run_on_a_port_already_open_says_so(
    traced: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Monitor holds the port; a Run that uses OSC says it now uses it
    (_bind writes nothing when the port is already open)."""
    from PySide6 import QtCore

    from gremlin import osc

    _ = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    runtime = _open_runtime(monkeypatch)
    monkeypatch.setattr(osc, "profile_uses_osc", lambda: True)
    token = "osc-monitor-test"
    runtime.hold_open(token)  # type: ignore[attr-defined]
    try:
        runtime.start()  # type: ignore[attr-defined]
        receive = _osc_lines("receive")
        assert (
            "port 127.0.0.1:9000 already open; now used by Run, Monitor"
            in receive
        ), receive
    finally:
        runtime.stop()  # type: ignore[attr-defined]
        runtime.release_open(token)  # type: ignore[attr-defined]
        runtime._listener = None  # type: ignore[attr-defined]


def test_traffic_note_error_is_logged_and_traced(logs: _Records, traced: None) -> None:
    from gremlin import osc_traffic

    osc_traffic.note("in", "/a", [], None, matched=object())  # type: ignore[arg-type]
    assert any("not noted" in t for t in logs.at(logging.DEBUG))
    assert any("Monitor: a message was not noted" in t for t in _osc_lines())


def test_monitor_hold_release_and_paused_drop_are_traced(
    traced: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtCore

    from gremlin import osc_traffic
    from gremlin.ui import osc_monitor_model as mm

    _ = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    # The real runtime's hold/release with the port already open (no bind).
    runtime = _open_runtime(monkeypatch)
    monkeypatch.setattr(mm, "_runtime", lambda: runtime)
    model = mm.OscMonitorModel()
    model.active = True  # pyright: ignore[reportAttributeAccessIssue]
    model.paused = True  # pyright: ignore[reportAttributeAccessIssue]
    model._on_note({"address": "/p", "direction": "in", "args": []})
    model.active = False  # pyright: ignore[reportAttributeAccessIssue]
    lines = _osc_lines()
    # Each once: the runtime writes them, the Monitor doesn't repeat them.
    assert lines.count("Monitor holds the port") == 1, lines
    assert lines.count("Monitor released the port") == 1, lines
    assert any(t.startswith("Monitor paused: /p not shown") for t in lines)
    osc_traffic.clear()


# -- scripts and conditions --------------------------------------------------


def test_script_osc_refusal_is_traced(traced: None) -> None:
    from gremlin import user_script

    assert user_script.ScriptOsc().send("Nowhere", "/a/*", 1) is False
    lines = _osc_lines("inputs")
    assert any(t.startswith("script send to /a/* refused:") for t in lines), lines


def test_condition_missing_osc_input_is_bounded_no_traceback(
    logs: _Records, traced: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from action_plugins.condition import ConditionFunctor
    from action_plugins.condition.condition import JoystickCondition
    from gremlin import osc_persist
    from gremlin.modules import ids

    monkeypatch.setattr(
        osc_persist,
        "osc_rows",
        lambda: SimpleNamespace(identifier_of_uid=lambda uid: None),
    )
    state = object.__new__(JoystickCondition.State)
    state.device_uuid = ids.OSC
    state.osc_uid = "gone"
    state.joystick = object()
    state.device_lookup = None

    def truth(_value: object) -> bool:
        return bool(state.get(None))  # type: ignore[arg-type]

    action = SimpleNamespace(
        _should_execute=lambda v: True, _condition_truth_state=truth
    )
    for _ in range(15):
        ConditionFunctor.__call__(action, None, None)  # type: ignore[arg-type]
    assert logs.at(logging.ERROR) == []
    warnings = logs.at(logging.WARNING)
    assert 1 <= len(warnings) <= 11 and "gone" in warnings[0]
    assert any("not logged until the next Run" in t for t in warnings)
    lines = _osc_lines("inputs")
    assert any(t.startswith("condition: OSC input gone is missing") for t in lines)
    # An error (D-09-OSC-TRACE-ERRORS): 10 lines, then one note, then quiet.
    missing = [t for t in lines if "OSC input gone is missing" in t]
    assert len(missing) == trace.REPEAT_LIMIT + 1, missing
    assert missing[-1].endswith(trace.OSC_REPEAT_NOTE)
