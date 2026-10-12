# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Listing the known devices never looks a connected stick's folder up by its
name alone (decision F4): the user's log said "Folder of <stick> looked up
without its device id" for every plugged-in stick with a saved file, each
time the device list was built (store.known_devices, the Export / Import
Device window's list)."""

from __future__ import annotations

import logging
import shutil
import types
import uuid
from collections.abc import Iterator

import pytest

from gremlin import device_initialization, shared_state
from gremlin.modules import store
from gremlin.profile import Profile
from test.unit._device_folders import put_module

STICKS = {
    "Probe Stick OT L": uuid.UUID("21111111-2222-3333-4444-555555555551"),
    "Probe Stick R": uuid.UUID("21111111-2222-3333-4444-555555555552"),
}


def _dev(name: str, uid: uuid.UUID) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        name=name, device_guid=types.SimpleNamespace(uuid=uid), is_virtual=False
    )


@pytest.fixture
def plugged(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    devices = [_dev(name, uid) for name, uid in STICKS.items()]
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: devices)
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    paths = [
        put_module(
            store.folder(),
            name,
            {"kind": "control.hardware", "device": name, "boundGuidLocal": str(uid)},
            str(uid),
        )
        for name, uid in STICKS.items()
    ]
    for name in STICKS:
        store._told_name_only.discard(store.plain_slug(name))
    warned: list[str] = []

    class _Catch(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if "looked up without its device id" in record.getMessage():
                warned.append(record.getMessage())

    handler = _Catch()
    store.syslog.addHandler(handler)
    try:
        yield warned
    finally:
        store.syslog.removeHandler(handler)
        for path in paths:
            shutil.rmtree(path.parent, ignore_errors=True)
        for name in STICKS:
            store._told_name_only.discard(store.plain_slug(name))


def test_known_devices_looks_up_connected_sticks_by_id(plugged: list[str]) -> None:
    rows = [r for r in store.known_devices() if r["name"] in STICKS]
    assert plugged == []
    # Still one row per stick, connected, with its file.
    assert sorted((r["name"], r["connected"], r["hasFile"]) for r in rows) == [
        ("Probe Stick OT L", True, True),
        ("Probe Stick R", True, True),
    ]


def test_export_import_window_list_does_not_warn(plugged: list[str]) -> None:
    from gremlin.ui.device_pack import pack_devices

    rows = [r for r in pack_devices() if r["name"] in STICKS]
    assert [r["canExport"] for r in rows] == [True, True]
    assert plugged == []


def test_match_by_name_does_not_warn(plugged: list[str]) -> None:
    row = store.match_known_device("Probe Stick R")
    assert row is not None and row["connected"] and row["hasFile"]
    assert plugged == []
