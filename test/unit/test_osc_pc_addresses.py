# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC Setup › Server's "Use one of these in your app:" list (09 S97):
read again on refreshPcAddresses (window to the front, the 5 s tick), with
its own notice that goes out only when the list changed, so the other
settings don't re-read every 5 s. Addresses faked; no network.

Spec: 09 S97.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gremlin.ui import osc_option
from gremlin.ui.osc_option import OscServerModel


@pytest.fixture
def ips(qapp: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    found = ["192.168.1.20", "127.0.0.1", "0.0.0.0"]
    monkeypatch.setattr(osc_option, "local_ipv4_addresses", lambda: list(found))
    return found


def _counts(model: OscServerModel) -> dict[str, int]:
    seen = {"pc": 0, "changed": 0}
    model.pcAddressesChanged.connect(lambda: seen.__setitem__("pc", seen["pc"] + 1))
    model.changed.connect(lambda: seen.__setitem__("changed", seen["changed"] + 1))
    return seen


def test_refresh_updates_the_list_and_says_so(ips: list[str]) -> None:
    model = OscServerModel()
    assert model.property("pcAddresses") == ["192.168.1.20"]
    seen = _counts(model)
    ips[:] = ["10.0.0.5", "127.0.0.1"]
    model.refreshPcAddresses()
    assert model.property("pcAddresses") == ["10.0.0.5"]
    assert seen == {"pc": 1, "changed": 0}


def test_no_notice_when_nothing_changed(ips: list[str]) -> None:
    model = OscServerModel()
    seen = _counts(model)
    model.refreshPcAddresses()
    model.refreshPcAddresses()
    assert seen == {"pc": 0, "changed": 0}


def test_settings_reload_does_not_reread_the_addresses(ips: list[str]) -> None:
    model = OscServerModel()
    seen = _counts(model)
    ips[:] = ["10.0.0.9"]
    model.reload()
    # The list waits for its own refresh, and other settings' notice
    # doesn't carry it.
    assert model.property("pcAddresses") == ["192.168.1.20"]
    assert seen == {"pc": 0, "changed": 1}


def test_only_loopback_falls_back_to_it(ips: list[str]) -> None:
    model = OscServerModel()
    ips[:] = ["127.0.0.1", "0.0.0.0"]
    model.refreshPcAddresses()
    assert model.property("pcAddresses") == ["127.0.0.1"]
