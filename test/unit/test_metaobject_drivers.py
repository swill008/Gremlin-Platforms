# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Drivers, HidHide and Device Mapping Editor models keep one
QMetaObject per type (gap PYSIDE-METAOBJECT, program map page 01).

A signal connected to a plain method (no ``@QtCore.Slot``) gives that one
Python QObject its own QMetaObject; QML caches by QMetaObject address, so a
freed model's address reused by a new one is read through the old type.
See test_page_model_metaobject.py for the list pages' models.

No real driver is touched: the driver queries are fakes and the Drivers
model's background read runs inline, so no thread posts to a deleted model.

Spec: none (no behaviour change; the windows work as specified).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin import drivers, event_handler, hidhide_driver
from gremlin.signal import signal
from gremlin.ui import hidhide as hh
from gremlin.ui.drivers_model import DriversModel
from gremlin.ui.hardware_profile import HardwareProfile
from test.unit.metaobject_helper import (
    broken_static_metaobjects,
    metaobject_addresses,
    receivers,
    static_address,
)


class _Launcher:
    def __call__(self, file: str, parameters: str) -> object:
        raise AssertionError("no helper is started here")


def _drivers_model(parent: QtCore.QObject | None, tmp_path: Path) -> DriversModel:
    status = drivers.DriverStatus(
        key="vjoy",
        name="vJoy",
        installed="2.2.2.0",
        bundled="2.2.2.0",
        state="same",
    )
    return DriversModel(
        parent,
        status_source=lambda: [status],
        app=lambda: tmp_path,
        launcher=_Launcher(),
        results_reader=lambda p: ([], False),
        vjoy_reader=list,
        busy_reader=list,
        lost_reader=list,
        lost_pruner=lambda current: None,
        background=lambda name, work, done: done(work()),
        restarter=lambda: None,
        temp_dir=tmp_path,
    )


@pytest.fixture
def fakes(
    qapp: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict[str, Callable[[QtCore.QObject], QtCore.QObject]]]:
    # HidHide: no real driver calls.
    monkeypatch.setattr(hh, "driver_present", lambda: True)
    monkeypatch.setattr(hh, "driver_version", lambda: "1.5")
    monkeypatch.setattr(hh, "get_active", lambda: False)
    monkeypatch.setattr(hh, "set_active", lambda on: True)
    monkeypatch.setattr(hh, "get_inverse", lambda: False)
    monkeypatch.setattr(hh, "set_inverse", lambda on: True)
    monkeypatch.setattr(hh, "get_blacklist", lambda: [])
    monkeypatch.setattr(hh, "set_blacklist", lambda ids: True)
    monkeypatch.setattr(hh, "set_whitelist", lambda paths: True)
    monkeypatch.setattr(hh, "list_hid_devices", lambda *a: [])
    monkeypatch.setattr(hh, "_enrich_devices", lambda rows: rows)
    monkeypatch.setattr(hh, "_gremlin_exe", lambda: "C:/Gremlin/gremlin.exe")
    monkeypatch.setattr(hh, "_full_image_name", lambda path: f"IMG:{path}")
    monkeypatch.setattr(hidhide_driver, "last_error", lambda: "")
    monkeypatch.setattr(hidhide_driver, "last_open_error", lambda: 0)
    yield {
        "DriversModel": lambda parent: _drivers_model(parent, tmp_path),
        "HidHideModel": hh.HidHideModel,
        "HardwareProfile": HardwareProfile,
    }


NAMES = ["DriversModel", "HardwareProfile", "HidHideModel"]


TYPES = [DriversModel, HardwareProfile, hh.HidHideModel]


def _receivers() -> dict[str, int]:
    """Connections on gremlin.signal and the device change event."""
    return receivers(
        [
            ("signal", signal),
            ("listener", event_handler.EventListener()),
        ]
    )


@pytest.fixture(scope="module", autouse=True)
def static_metaobjects_still_work() -> Iterator[None]:
    # Nothing here may leave a measured type's staticMetaObject deleted for
    # the tests that run after this module (see metaobject_helper).
    yield
    assert broken_static_metaobjects(TYPES) == []


@pytest.mark.parametrize("name", NAMES)
def test_one_metaobject_per_type(fakes: dict, name: str) -> None:
    # No parent: see metaobject_helper.
    cls = {t.__name__: t for t in TYPES}[name]
    addresses = metaobject_addresses(fakes[name])
    assert addresses == {static_address(cls)}, (
        f"{name}: a signal is connected to a method without @QtCore.Slot"
    )


@pytest.mark.parametrize("name", NAMES)
def test_deleted_model_drops_its_connections(fakes: dict, name: str) -> None:
    before = _receivers()
    host = QtCore.QObject()
    model = fakes[name](host)
    shiboken6.delete(host)
    assert not shiboken6.isValid(model)
    after = _receivers()
    grew = {k: after[k] - before[k] for k in after if after[k] != before[k]}
    assert grew == {}, f"{name}: connections kept after delete"
