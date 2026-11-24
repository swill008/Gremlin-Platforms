# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Watching for a switched-off device being plugged in (12 S23)."""

from __future__ import annotations

import ctypes
import logging
import threading
from collections.abc import Callable

import pytest

from gremlin import device_watch
from gremlin.device_watch import DeviceWatch

A = r"HID\VID_231D&PID_2234\8&2fe8e01b&0&0000"
B = r"HID\VID_046D&PID_C216\7&1"
ENUMERATED, STARTED, REMOVED = 7, 8, 9


class FakeApi:
    def __init__(self) -> None:
        self.live: dict[int, tuple[str, Callable[[int], None]]] = {}
        self.registered: list[str] = []
        self.unregistered: list[str] = []
        self.callbacks: list[Callable[[int], None]] = []
        self.fail: set[str] = set()
        self.during_register: Callable[[], object] | None = None
        self.during_unregister: Callable[[Callable[[int], None]], object] | None = None

    def register(self, device_id: str, callback: Callable[[int], None]) -> int:
        if device_id in self.fail:
            raise OSError("no")
        if self.during_register is not None:
            self.during_register()
        self.registered.append(device_id)
        self.callbacks.append(callback)
        token = len(self.registered)
        self.live[token] = (device_id, callback)
        return token

    def unregister(self, token: object) -> None:
        assert isinstance(token, int)
        device_id, callback = self.live.pop(token)
        if self.during_unregister is not None:
            self.during_unregister(callback)
        self.unregistered.append(device_id)


@pytest.fixture
def api() -> FakeApi:
    return FakeApi()


@pytest.fixture
def arrived() -> list[str]:
    return []


@pytest.fixture
def watch(api: FakeApi, arrived: list[str]) -> DeviceWatch:
    return DeviceWatch(arrived.append, api)


def test_watches_exactly_the_ids(watch: DeviceWatch, api: FakeApi) -> None:
    assert watch.set_ids([B, A]) == [B, A]
    assert watch.set_ids([A, B]) == []
    assert watch.set_ids([A]) == []
    assert api.unregistered == [B]
    assert watch.set_ids([A, B]) == [B]
    assert watch.set_ids([]) == []
    assert not api.live


def test_ids_compare_case_insensitively(
    watch: DeviceWatch, api: FakeApi, arrived: list[str]
) -> None:
    assert watch.set_ids([A, A.upper()]) == [A]
    assert watch.set_ids([A.lower()]) == []
    assert api.registered == [A]
    assert api.unregistered == []
    api.callbacks[0](ENUMERATED)
    assert arrived == [A.lower()]


def test_only_enumerated_is_an_arrival(
    watch: DeviceWatch, api: FakeApi, arrived: list[str]
) -> None:
    watch.set_ids([A, B])
    for action in (STARTED, REMOVED, 0):
        api.callbacks[0](action)
    assert arrived == []
    api.callbacks[0](ENUMERATED)
    assert arrived == [A]


def test_close_is_final(watch: DeviceWatch, api: FakeApi) -> None:
    watch.set_ids([A, B])
    watch.close()
    watch.close()
    assert sorted(api.unregistered) == sorted([A, B])
    assert watch.set_ids([A]) == []
    assert api.registered == [A, B]


def test_late_callbacks_are_ignored(
    watch: DeviceWatch, api: FakeApi, arrived: list[str]
) -> None:
    watch.set_ids([A, B])
    watch.set_ids([B])
    api.callbacks[0](ENUMERATED)
    watch.close()
    api.callbacks[1](ENUMERATED)
    assert arrived == []


def test_failure_is_logged_once_and_retried(
    watch: DeviceWatch, api: FakeApi, caplog: pytest.LogCaptureFixture
) -> None:
    api.fail = {A}
    with caplog.at_level(logging.WARNING, logger="system"):
        assert watch.set_ids([A, B]) == [B]
        assert watch.set_ids([A, B]) == []
    assert len([r for r in caplog.records if A in r.getMessage()]) == 1
    api.fail = set()
    assert watch.set_ids([A, B]) == [A]


def test_long_id_is_refused(watch: DeviceWatch, api: FakeApi) -> None:
    assert watch.set_ids(["x" * 200, "x" * 199]) == ["x" * 199]
    assert api.registered == ["x" * 199]


def test_callback_exception_is_logged(
    api: FakeApi, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(_id: str) -> None:
        raise ValueError("broken handler")

    DeviceWatch(broken, api).set_ids([A])
    with caplog.at_level(logging.ERROR, logger="system"):
        api.callbacks[0](ENUMERATED)
    assert any(A in r.getMessage() and r.exc_info for r in caplog.records)


def test_failed_unregister_does_not_raise(watch: DeviceWatch, api: FakeApi) -> None:
    def fail(_callback: Callable[[int], None]) -> None:
        raise OSError("no")

    watch.set_ids([A, B])
    api.during_unregister = fail
    watch.close()
    assert not api.live


@pytest.mark.parametrize("close", [True, False])
def test_no_lock_held_during_unregister(
    watch: DeviceWatch, api: FakeApi, close: bool
) -> None:
    """As Windows does, unregister waits for a running callback."""
    finished: list[bool] = []

    def fire(callback: Callable[[int], None]) -> None:
        # _lock is checked too: the callback may take it one day.
        def run() -> None:
            callback(ENUMERATED)
            if watch._lock.acquire(timeout=2):
                watch._lock.release()
                finished.append(True)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(5)

    watch.set_ids([A])
    api.during_unregister = fire
    if close:
        watch.close()
    else:
        watch.set_ids([])
    assert finished == [True]


def test_close_while_registering_leaves_nothing(
    watch: DeviceWatch, api: FakeApi
) -> None:
    api.during_register = watch.close
    assert watch.set_ids([A]) == []
    assert not api.live
    assert api.unregistered == [A]


def test_real_api_refuses_under_pytest(
    arrived: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    with pytest.raises(device_watch.RealCallBlocked):
        device_watch.RealWatchApi().register(A, lambda _action: None)
    with caplog.at_level(logging.WARNING, logger="system"):
        assert DeviceWatch(arrived.append).set_ids([A]) == []
    assert "called from a test" in caplog.text


class _FakeCall:
    """A cfgmgr32 function that takes argtypes/restype."""

    def __init__(self, result: int = 0) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *args: object) -> int:
        self.calls.append(args)
        return self.result


class _FakeCfg:
    def __init__(self) -> None:
        self.CM_Register_Notification = _FakeCall()
        self.CM_Unregister_Notification = _FakeCall()


def test_real_api_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _FakeCfg()
    api = device_watch.RealWatchApi()
    monkeypatch.setattr(device_watch, "_under_test", lambda: False)
    monkeypatch.setattr(ctypes, "WinDLL", lambda _name: cfg)
    actions: list[int] = []
    token = api.register(A, actions.append)
    assert isinstance(token, device_watch._Registration)
    assert ctypes.sizeof(token.filter) == token.filter.cbSize == 416
    assert (token.filter.FilterType, token.filter.InstanceId) == (2, A)
    assert token.callback(None, None, ENUMERATED, None, 0) == 0
    assert actions == [ENUMERATED]
    # Kept alive until Windows has really let go of it.
    cfg.CM_Unregister_Notification.result = 1
    with pytest.raises(OSError):
        api.unregister(token)
    assert token in api._live
    cfg.CM_Unregister_Notification.result = 0
    api.unregister(token)
    assert token not in api._live
    cfg.CM_Register_Notification.result = 1
    with pytest.raises(OSError):
        api.register(A, actions.append)
    assert not api._live
