# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The "Listening for OSC" box shows where OSC sends from the Targets list
(09 S96), not the old output host and port (AUD-OSC-01)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gremlin import osc_device_file as odf
from gremlin.ui.osc_settings_info import OscSettingsInfo


@pytest.fixture
def osc_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    file = tmp_path / "osc.json"
    monkeypatch.setattr(odf, "path", lambda: file)
    return file


def test_edited_default_target_is_shown(osc_file: Path) -> None:
    [default] = odf.read_targets()
    default["host"] = "192.168.1.30"
    default["port"] = 9000
    assert odf.write_targets([default])
    summary = OscSettingsInfo().summary()
    assert "Targets: Default 192.168.1.30:9000" in summary
    assert "127.0.0.1:8000" not in summary
    assert "Output host" not in summary
    assert "Output port" not in summary


def test_every_target_is_listed(osc_file: Path) -> None:
    [default] = odf.read_targets()
    companion = {"id": "c1", "name": "Companion", "host": "127.0.0.1", "port": 12321}
    assert odf.write_targets([default, companion])
    summary = OscSettingsInfo().summary()
    assert "Default 127.0.0.1:8000, Companion 127.0.0.1:12321" in summary


def test_output_switch_and_no_targets(osc_file: Path) -> None:
    server = odf.read_server()
    server["output_enabled"] = False
    assert odf.write_server(server)
    assert odf.write_targets([]) or odf.read_targets() == []
    summary = OscSettingsInfo().summary()
    assert "OSC output: Off" in summary
    assert "Targets: none" in summary
