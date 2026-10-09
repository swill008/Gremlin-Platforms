# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC discovery (D-09-OSC-DISCOVERY): announce / find through zeroconf.

A stand-in zeroconf library throughout: these tests never touch the network.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import time
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from PySide6 import QtWidgets

from gremlin import osc_discovery as disc
from gremlin.signal import signal


class FakeInfo:
    def __init__(
        self,
        type_: str,
        name: str,
        addresses: list[bytes] | None = None,
        port: int | None = None,
        properties: dict | None = None,
        server: str | None = None,
    ) -> None:
        self.type = type_
        self.name = name
        self.addresses = addresses or []
        self.port = port
        self.server = server
        self._parsed = [".".join(str(b) for b in a) for a in self.addresses]

    def parsed_addresses(self) -> list[str]:
        return list(self._parsed)


class FakeZeroconf:
    made: list[FakeZeroconf] = []

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.remote: dict[str, FakeInfo] = {}
        FakeZeroconf.made.append(self)

    def register_service(self, info: FakeInfo, allow_name_change: bool = False) -> None:
        self.calls.append(("register", info.name, info.port))

    def unregister_service(self, info: FakeInfo) -> None:
        self.calls.append(("unregister", info.name, info.port))

    def get_service_info(
        self, type_: str, name: str, timeout: int = 3000
    ) -> FakeInfo | None:
        return self.remote.get(name)

    def close(self) -> None:
        self.calls.append(("close",))


class FakeBrowser:
    made: list[FakeBrowser] = []

    def __init__(
        self, zc: FakeZeroconf, type_: str, handlers: list | None = None
    ) -> None:
        self.zc = zc
        self.type = type_
        self.handlers = handlers or []
        self.cancelled = False
        FakeBrowser.made.append(self)

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self, name: str, state: str) -> None:
        for h in self.handlers:
            h(
                zeroconf=self.zc,
                service_type=self.type,
                name=name,
                state_change=SimpleNamespace(name=state),
            )


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    FakeZeroconf.made = []
    FakeBrowser.made = []
    lib = SimpleNamespace(
        Zeroconf=FakeZeroconf, ServiceBrowser=FakeBrowser, ServiceInfo=FakeInfo
    )
    monkeypatch.setattr(disc, "_lib", lib)
    monkeypatch.setattr(disc, "_addresses", lambda host: [bytes([192, 168, 1, 5])])
    disc._reset_for_tests()
    yield lib
    disc._reset_for_tests()


def settle(timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while disc._worker is not None:
        assert time.monotonic() < deadline, "discovery worker did not finish"
        time.sleep(0.01)


def own_name() -> str:
    return f"{disc.service_name()}.{disc.SERVICE_TYPE}"


def test_both_switches_off_never_starts_zeroconf(fake: SimpleNamespace) -> None:
    disc.set_announce(False, 8001)
    disc.set_find(False)
    settle()
    assert FakeZeroconf.made == []
    assert disc._worker is None
    disc.shutdown()
    assert FakeZeroconf.made == []


def test_announce_registers_follows_port_and_stops(fake: SimpleNamespace) -> None:
    disc.set_announce(True, 8001)
    settle()
    zc = FakeZeroconf.made[0]
    assert zc.calls == [("register", own_name(), 8001)]
    assert disc.service_name().startswith("Gremlin-Platforms on ")
    disc.set_announce(True, 9000)
    settle()
    assert zc.calls[1:] == [
        ("unregister", own_name(), 8001),
        ("register", own_name(), 9000),
    ]
    disc.set_announce(False, 9000)
    settle()
    assert zc.calls[3:] == [("unregister", own_name(), 9000), ("close",)]
    assert disc._zc is None


def test_find_lists_devices_and_says_so(fake: SimpleNamespace) -> None:
    hits = []
    slot = lambda: hits.append(1)  # noqa: E731
    signal.oscDevicesFound.connect(slot)
    try:
        disc.set_find(True)
        settle()
        browser = FakeBrowser.made[0]
        assert browser.type == "_osc._udp.local."
        zc = browser.zc
        name = "TouchOSC on iPad._osc._udp.local."
        zc.remote[name] = FakeInfo(
            "_osc._udp.local.", name, addresses=[bytes([10, 0, 0, 7])], port=9000
        )
        browser.fire(name, "Added")
        assert disc.found() == [
            {"name": "TouchOSC on iPad", "host": "10.0.0.7", "port": 9000}
        ]
        assert len(hits) == 1
        browser.fire(name, "Updated")  # same details: no new signal
        assert len(hits) == 1
        browser.fire(name, "Removed")
        assert disc.found() == []
        assert len(hits) == 2
        browser.fire(name, "Added")
        disc.set_find(False)
        settle()
        assert browser.cancelled
        assert disc.found() == []
        assert zc.calls == [("close",)]
    finally:
        signal.oscDevicesFound.disconnect(slot)


def test_own_announcement_is_not_listed(fake: SimpleNamespace) -> None:
    disc.set_announce(True, 8001)
    disc.set_find(True)
    settle()
    browser = FakeBrowser.made[0]
    browser.zc.remote[own_name()] = FakeInfo(
        "_osc._udp.local.", own_name(), addresses=[bytes([192, 168, 1, 5])], port=8001
    )
    browser.fire(own_name(), "Added")
    assert disc.found() == []


def test_settings_from_osc_file(
    fake: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import osc_device_file

    server = {"announce": True, "find_devices": True, "port": 8123, "host": ""}
    monkeypatch.setattr(osc_device_file, "read_server", lambda: dict(server))
    disc.apply_settings()
    settle()
    zc = FakeZeroconf.made[0]
    assert ("register", own_name(), 8123) in zc.calls
    assert len(FakeBrowser.made) == 1
    server.update(announce=False, find_devices=False)
    disc.apply_settings()
    settle()
    assert zc.calls[-2:] == [("unregister", own_name(), 8123), ("close",)]
    assert FakeBrowser.made[0].cancelled


def test_shutdown_unregisters_closes_and_stays_off(fake: SimpleNamespace) -> None:
    disc.set_announce(True, 8001)
    disc.set_find(True)
    settle()
    zc = FakeZeroconf.made[0]
    disc.shutdown()
    assert disc._worker is None
    assert ("unregister", own_name(), 8001) in zc.calls
    assert zc.calls[-1] == ("close",)
    assert FakeBrowser.made[0].cancelled
    disc.set_announce(True, 8001)  # after quit: ignored
    settle()
    assert len(FakeZeroconf.made) == 1


def test_without_zeroconf_switches_do_nothing(
    fake: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(disc, "_lib", None)
    assert disc.available() is False
    disc.set_announce(True, 8001)
    disc.set_find(True)
    assert disc._worker is None
    assert disc.found() == []
    disc.shutdown()


def test_module_loads_when_zeroconf_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "zeroconf", None)  # import fails
    fresh = importlib.import_module("gremlin.osc_discovery")
    try:
        fresh = importlib.reload(fresh)
        assert fresh.available() is False
    finally:
        monkeypatch.delitem(sys.modules, "zeroconf")
        importlib.reload(fresh)


def test_real_library_has_what_we_use(monkeypatch: pytest.MonkeyPatch) -> None:
    zeroconf = pytest.importorskip("zeroconf")
    for name in ("Zeroconf", "ServiceBrowser", "ServiceInfo"):
        assert hasattr(zeroconf, name)
    # Builds a real ServiceInfo the way the program does (no network).
    monkeypatch.setattr(disc, "_lib", zeroconf)
    monkeypatch.setattr(disc, "_addresses", lambda host: [bytes([192, 168, 1, 5])])
    info = disc._service_info(8001, "")
    assert info.name == own_name()
    assert info.port == 8001
    assert info.parsed_addresses() == ["192.168.1.5"]
    assert (
        "allow_name_change"
        in inspect.signature(zeroconf.Zeroconf.register_service).parameters
    )


def test_found_signal_arrives_on_main_thread(
    fake: SimpleNamespace, qapp: QtWidgets.QApplication
) -> None:
    import threading

    from gremlin import threads

    disc._make_relay()
    seen: list[bool] = []
    slot = lambda: seen.append(  # noqa: E731
        threading.current_thread() is threading.main_thread()
    )
    signal.oscDevicesFound.connect(slot)
    try:
        threads.start("test discovery emit", disc._emit).join(5)
        assert seen == []  # queued, not said on the other thread
        deadline = time.monotonic() + 5
        while not seen and time.monotonic() < deadline:
            qapp.processEvents()
        assert seen == [True]
    finally:
        signal.oscDevicesFound.disconnect(slot)
