# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Reset Devices results (D-02-RESET-DEVICES item 4): a system.log line per
device, HIDHIDE trace lines only with tracing on and the HidHide row ticked,
expected.json rewritten only when a tester uses it, no HidHide change
recorded and no device touched."""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import device_reset_log, input_tester_link, trace, util

_USB_A = r"USB\VID_231D&PID_3201\9&1d65ffe4&0&3"
_USB_B = r"USB\VID_044F&PID_0402\5&abc&0&1"


def _results() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(usb_id=_USB_A, outcome="ok", code=0, back_after=2.4),
        SimpleNamespace(usb_id=_USB_B, outcome="failed", code=5, back_after=None),
    ]


def _devices() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(usb_id=_USB_A, name="Right stick", windows_name="EVO R"),
        SimpleNamespace(usb_id=_USB_B, name="", windows_name="T.16000M"),
    ]


@pytest.fixture
def env(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SimpleNamespace]:
    writes: list[int] = []
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(input_tester_link, "gremlin_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(input_tester_link, "running", lambda: False)
    monkeypatch.setattr(input_tester_link, "_last_change", None)
    monkeypatch.setattr(input_tester_link, "build_expected", lambda: {"n": 1})
    real_write = input_tester_link.write_expected

    def _write() -> bool:
        writes.append(1)
        return real_write()

    monkeypatch.setattr(input_tester_link, "write_expected", _write)
    # No device is ever restarted from here.
    try:
        from gremlin import device_reset

        def _boom(*_a: object, **_k: object) -> None:
            raise AssertionError("device_reset_log reset a device")

        monkeypatch.setattr(device_reset, "reset", _boom)
    except ImportError:
        pass
    trace._reset_for_tests()
    yield SimpleNamespace(writes=writes, expected=input_tester_link.expected_file())
    trace._reset_for_tests()


def _hidhide_lines() -> list[tuple[str, str, str, str, bool]]:
    return [line for line in trace.lines() if line[2] == trace.HIDHIDE]


def test_one_system_log_line_per_device(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="system"):
        device_reset_log.report(_results(), _devices())
    lines = [r.getMessage() for r in caplog.records if r.name == "system"]
    assert lines == [
        f"Reset Devices: Right stick ({_USB_A}) → reset ✓ · back after 2.4 s",
        f"Reset Devices: T.16000M ({_USB_B}) → failed: 5",
    ]


def test_outcome_texts() -> None:
    def r(outcome: str, code: int = 0) -> SimpleNamespace:
        return SimpleNamespace(
            usb_id=_USB_A, outcome=outcome, code=code, back_after=None
        )

    assert (
        device_reset_log.outcome_text(r("restart", 3010)) == "needs a Windows restart"
    )
    assert device_reset_log.outcome_text(r("not_found")) == "not found"
    assert device_reset_log.outcome_text(r("declined", 1223)) == "permission declined"
    assert device_reset_log.outcome_text(r("ok")) == "reset ✓ · not back after 10 s"
    # ResetResult.text (device_reset) wins when present.
    own = SimpleNamespace(
        usb_id=_USB_A, outcome="failed", code=None, text="failed: timed out"
    )
    assert device_reset_log.outcome_text(own) == "failed: timed out"


def test_trace_lines_when_tracing_with_hidhide_row(env: SimpleNamespace) -> None:
    trace.set_hidhide(True)
    trace.set_enabled(True)
    device_reset_log.report(_results(), _devices())
    lines = _hidhide_lines()
    assert len(lines) == 2
    assert _USB_A in lines[0][3] and lines[0][4] is False
    assert _USB_B in lines[1][3] and lines[1][4] is True


@pytest.mark.parametrize(("tracing", "row"), [(False, True), (True, False)])
def test_no_trace_lines_otherwise(
    env: SimpleNamespace, tracing: bool, row: bool
) -> None:
    trace.set_hidhide(row)
    trace.set_enabled(tracing)
    device_reset_log.report(_results(), _devices())
    assert _hidhide_lines() == []


def test_expected_rewritten_only_when_it_exists(env: SimpleNamespace) -> None:
    device_reset_log.report(_results(), _devices())
    assert env.writes == []
    assert not env.expected.exists()

    env.expected.parent.mkdir(parents=True, exist_ok=True)
    env.expected.write_text("{}", encoding="utf-8")
    device_reset_log.report(_results(), _devices())
    assert env.writes == [1]
    assert env.expected.read_text(encoding="utf-8").strip().startswith("{\n")
    # A reset is not a HidHide change: no restart banner.
    assert input_tester_link.last_hidhide_change() is None


def test_expected_written_while_tester_runs(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(input_tester_link, "running", lambda: True)
    device_reset_log.report(_results(), _devices())
    assert env.writes == [1]
    assert env.expected.exists()
