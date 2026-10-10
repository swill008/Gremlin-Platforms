# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Control tracing core (gremlin/trace.py, D-01-TRACE): ticks saved, axis
rate limit, nothing written or opened while off, OUTPUT only for a ticked
input, warnings raise the notice."""

from __future__ import annotations

import json
import os
import pathlib
import uuid
from collections.abc import Iterator

import pytest

from gremlin import clock, config, trace, util


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    yield
    trace._reset_for_tests()


def _dev() -> uuid.UUID:
    return uuid.uuid4()


def _points() -> list[str]:
    return [line[2] for line in trace.lines()]


def test_off_by_default_writes_nothing_and_opens_no_file(
    tmp_path: pathlib.Path,
) -> None:
    dev = _dev()
    trace.set_device(dev, True)
    assert not trace.enabled()
    trace.raw(dev, "button", 1, True)
    trace.wiring(dev, "button", 1, "claimed")
    trace.event("Profile Start")
    trace.warn(trace.OUT_OF_STEP, "x", "y")
    assert trace.lines() == []
    assert trace.notice() == ""
    assert not (tmp_path / "logs" / "trace.log").exists()


def test_on_writes_lines_and_file(tmp_path: pathlib.Path) -> None:
    dev = _dev()
    trace.set_tick(dev, "button", 2, True)
    hooked: list[bool] = []

    def hook() -> None:
        hooked.append(trace.enabled())

    trace.on_change(hook)
    trace.set_enabled(True)
    assert hooked == [True]
    assert trace.since() is not None
    trace.raw(dev, "button", 2, True, label="Stick Button 2")
    trace.raw(dev, "button", 3, True, label="Stick Button 3")  # not ticked
    trace.set_enabled(False)
    assert hooked == [True, False]
    trace._hooks.remove(hook)
    assert _points() == [trace.EVENT, trace.RAW, trace.EVENT]
    assert trace.lines()[1][1:4] == ("Stick Button 2", trace.RAW, "pressed")
    text = (tmp_path / "logs" / "trace.log").read_text(encoding="utf-8")
    assert "Tracing on" in text and "Stick Button 2  RAW  pressed" in text
    assert "Button 3" not in text


def test_axis_rate_limit_and_still_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    dev = _dev()
    trace.set_tick(dev, "axis", 1, True)
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    monkeypatch.setattr(trace, "_schedule_flush", lambda: None)
    trace.set_enabled(True)
    for i in range(5):  # five values inside one interval
        trace.raw(dev, "axis", 1, i / 10, label="A")
        now[0] += 0.01
    raws = [line for line in trace.lines() if line[2] == trace.RAW]
    assert len(raws) == 1 and raws[0][3] == "+0.000"
    # The stick goes still: the latest value is written once.
    now[0] += trace.AXIS_INTERVAL
    trace._on_flush()
    raws = [line for line in trace.lines() if line[2] == trace.RAW]
    assert len(raws) == 2
    assert raws[1][3].startswith("+0.400  (last value; stick still)")
    assert "(3 values between)" in raws[1][3]
    last = trace.last_raw(dev, "axis", 1)
    assert last is not None and last[0] == pytest.approx(0.4)


def test_ticks_persist_in_config() -> None:
    dev, other = _dev(), _dev()
    trace.set_tick(dev, "axis", 3, True)
    trace.set_device(other, True)
    trace.set_oos(dev, True)
    trace.set_hidhide(True)
    saved = json.loads(config.Configuration().value("debug", "trace", "ticks"))
    assert saved[str(dev)]["axis"] == [3]
    assert saved[str(other)]["all"] is True
    # A fresh start reads them back from the config.
    trace._reset_for_tests()
    assert trace.ticked(dev, "axis", 3)
    assert not trace.ticked(dev, "axis", 4)
    assert trace.ticked(other, "hat", 1)
    assert trace.oos_ticked(dev) and trace.hidhide_ticked()
    assert {dev, other} <= set(trace.ticked_devices())
    assert trace.device_ticks(dev)["axis"] == {3}
    trace.set_device(other, False)
    assert not trace.ticked(other, "hat", 1)
    assert not trace.enabled()  # never saved on


def test_output_only_for_ticked_current_input() -> None:
    dev, untracked = _dev(), _dev()
    trace.set_tick(dev, "axis", 1, True)
    trace.set_enabled(True)
    trace.begin_input(untracked, "axis", 1)
    trace.output(3, "axis", 1, 0.5, "written")
    trace.end_input()
    assert trace.OUTPUT not in _points()
    written = trace.last_written(3, "axis", 1)
    assert written is not None and written[0] == 0.5
    trace.begin_input(dev, "axis", 1)
    trace.output(3, "axis", 1, 0.25, "written")
    trace.output(3, "button", 4, True, "blocked (not claimed by the vJoy 3 module)")
    trace.end_input()
    assert trace.current_input() is None
    out = [line for line in trace.lines() if line[2] in (trace.OUTPUT, trace.BLOCKED)]
    assert [line[2] for line in out] == [trace.OUTPUT, trace.BLOCKED]
    assert out[0][3] == "vJoy 3 axis X = +0.250 · written"
    assert out[1][3].startswith("vJoy 3 Button 4 = True · blocked")


def test_warn_sets_notice_and_clear_view_keeps_file(tmp_path: pathlib.Path) -> None:
    trace.set_enabled(True)
    v = trace.version()
    trace.warn(trace.OUT_OF_STEP, "EVO R Axis 1", "stick reads 0.5")
    assert trace.version() > v
    assert trace.lines()[-1][4] is True
    assert "stick reads 0.5" in trace.notice()
    trace.clear_notice()
    assert trace.notice() == ""
    trace.hidhide("Cloak turned off", warning=True)
    assert "Cloak turned off" in trace.notice()
    trace.clear_view()
    assert trace.lines() == []
    assert trace.file_size() > 0
    assert trace.file_path() == tmp_path / "logs" / "trace.log"


def test_control_label_names_the_control() -> None:
    label = trace.control_label(_dev(), "axis", 1)
    assert label.endswith(" Axis 1")
    assert trace.control_label(_dev(), "hat", 2).endswith(" Hat 2")


def test_userprofile_is_temp() -> None:
    assert "Stacie\\Gremlin Platforms" not in os.path.abspath(config._config_file_path)
