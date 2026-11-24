# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Reports when a given device is plugged in, disabled ones included (S23).

A disabled device that is plugged in again sends no joystick or interface
arrival. Windows' per-device notification ("enumerated") does report it,
also for a device that was absent when it was registered.

CM_Unregister_Notification waits for callbacks still running, so no lock is
held around the Windows calls, and set_ids() and close() must never be
called from on_arrival.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
from collections.abc import Callable, Iterable
from ctypes import wintypes
from typing import Protocol

MAX_DEVICE_ID_LEN = 200  # the terminating null included

ACTION_INSTANCE_ENUMERATED = 7
_FILTER_TYPE_DEVICE_INSTANCE = 2
_CR_SUCCESS = 0

_log = logging.getLogger("system")


class RealCallBlocked(RuntimeError):
    """A real Windows notification call from a test."""


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


class WatchApi(Protocol):
    """Windows' device notifications; tests pass a fake."""

    def register(self, device_id: str, callback: Callable[[int], None]) -> object:
        """Calls callback(action) on events of one device; raises on failure."""
        ...

    def unregister(self, token: object) -> None:
        """Ends a registration once its running callbacks have returned."""
        ...


class _NotifyFilter(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("Flags", wintypes.DWORD),
        ("FilterType", wintypes.DWORD),
        ("Reserved", wintypes.DWORD),
        ("InstanceId", wintypes.WCHAR * MAX_DEVICE_ID_LEN),
    ]


_NotifyCallback = ctypes.WINFUNCTYPE(
    wintypes.DWORD,
    ctypes.c_void_p,  # notification handle
    ctypes.c_void_p,  # context
    ctypes.c_int,  # action
    ctypes.c_void_p,  # event data
    wintypes.DWORD,  # event data size
)


class _Registration:
    def __init__(self, device_id: str, callback: Callable[[int], None]) -> None:
        def on_event(
            _handle: int | None,
            _context: int | None,
            action: int,
            _data: int | None,
            _size: int,
        ) -> int:
            try:
                callback(action)
            except Exception:
                _log.exception("Device notification for %s failed", device_id)
            return 0

        self.filter = _NotifyFilter(
            cbSize=ctypes.sizeof(_NotifyFilter),
            FilterType=_FILTER_TYPE_DEVICE_INSTANCE,
            InstanceId=device_id,
        )
        self.callback = _NotifyCallback(on_event)
        self.handle = ctypes.c_void_p()


class RealWatchApi:
    """cfgmgr32's CM_Register_Notification; refuses to run under pytest."""

    # Windows may call a registration until it is unregistered, whatever
    # became of the DeviceWatch, so its callback must stay alive that long.
    _live: set[_Registration] = set()

    @staticmethod
    def _cfgmgr() -> ctypes.WinDLL:
        if _under_test():
            raise RealCallBlocked("device_watch notification called from a test")
        cfg = ctypes.WinDLL("cfgmgr32")
        cfg.CM_Register_Notification.argtypes = [
            ctypes.POINTER(_NotifyFilter),
            ctypes.c_void_p,
            _NotifyCallback,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        cfg.CM_Register_Notification.restype = wintypes.DWORD
        cfg.CM_Unregister_Notification.argtypes = [ctypes.c_void_p]
        cfg.CM_Unregister_Notification.restype = wintypes.DWORD
        return cfg

    def register(
        self, device_id: str, callback: Callable[[int], None]
    ) -> _Registration:
        cfg = self._cfgmgr()
        registration = _Registration(device_id, callback)
        self._live.add(registration)
        result = cfg.CM_Register_Notification(
            ctypes.byref(registration.filter),
            None,
            registration.callback,
            ctypes.byref(registration.handle),
        )
        if result != _CR_SUCCESS:
            self._live.discard(registration)
            raise OSError(f"CM_Register_Notification returned {result}")
        return registration

    def unregister(self, token: object) -> None:
        assert isinstance(token, _Registration)
        result = self._cfgmgr().CM_Unregister_Notification(token.handle)
        if result != _CR_SUCCESS:
            raise OSError(f"CM_Unregister_Notification returned {result}")
        self._live.discard(token)


class _Entry:
    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.active = True
        # None while the registration is still being made.
        self.token: object = None


class DeviceWatch:
    """Calls on_arrival(id) when one of the watched devices is plugged in.

    on_arrival runs on a Windows thread-pool thread and must be quick. It
    must not call set_ids() or close(), nor wait for a lock held around them.
    """

    def __init__(
        self, on_arrival: Callable[[str], None], api: WatchApi | None = None
    ) -> None:
        self._on_arrival = on_arrival
        self._api: WatchApi = api if api is not None else RealWatchApi()
        self._lock = threading.Lock()
        self._entries: dict[str, _Entry] = {}
        self._reported: set[str] = set()
        self._closed = False

    def set_ids(self, ids: Iterable[str]) -> list[str]:
        """Watches exactly these devices; never raises.

        Args:
            ids: device instance ids, compared case-insensitively

        Returns:
            The ids newly registered by this call, in order.
        """
        wanted: dict[str, str] = {}
        for device_id in ids:
            wanted.setdefault(device_id.upper(), device_id)

        added: list[tuple[str, _Entry]] = []
        with self._lock:
            if self._closed:
                return []
            removed = [
                self._entries.pop(key)
                for key in list(self._entries)
                if key not in wanted
            ]
            for entry in removed:
                entry.active = False
            for key, device_id in wanted.items():
                if key in self._entries:
                    self._entries[key].device_id = device_id
                else:
                    self._entries[key] = entry = _Entry(device_id)
                    added.append((key, entry))

        self._unregister(removed)
        return [entry.device_id for key, entry in added if self._register(key, entry)]

    def close(self) -> None:
        """Stops watching for good."""
        with self._lock:
            self._closed = True
            removed = list(self._entries.values())
            self._entries.clear()
            for entry in removed:
                entry.active = False
        self._unregister(removed)

    def _register(self, key: str, entry: _Entry) -> bool:
        try:
            if len(entry.device_id) >= MAX_DEVICE_ID_LEN:
                raise ValueError("the id is too long")
            token = self._api.register(
                entry.device_id, lambda action: self._on_event(entry, action)
            )
        except Exception as exc:
            with self._lock:
                entry.active = False
                if self._entries.get(key) is entry:
                    del self._entries[key]
                first = key not in self._reported
                self._reported.add(key)
            if first:
                _log.warning(
                    "Can't watch for %s being plugged in: %s", entry.device_id, exc
                )
            return False
        with self._lock:
            entry.token = token
            if entry.active:
                return True
        # Dropped by another thread while it was being registered.
        self._unregister([entry])
        return False

    def _unregister(self, entries: list[_Entry]) -> None:
        for entry in entries:
            with self._lock:
                token, entry.token = entry.token, None
            if token is None:
                # Still registering; _register sees it is no longer active.
                continue
            try:
                self._api.unregister(token)
            except Exception as exc:
                _log.warning("Can't stop watching for %s: %s", entry.device_id, exc)

    def _on_event(self, entry: _Entry, action: int) -> None:
        if action != ACTION_INSTANCE_ENUMERATED or not entry.active:
            return
        try:
            self._on_arrival(entry.device_id)
        except Exception:
            _log.exception("Handling the arrival of %s failed", entry.device_id)
