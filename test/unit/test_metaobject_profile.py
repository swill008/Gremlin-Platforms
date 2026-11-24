# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Profile Settings and mode list models keep one QMetaObject per type
(gap PYSIDE-METAOBJECT, program map page 01).

A signal connected to a plain method (no ``@QtCore.Slot``) of a Python
QObject gives that one object its own QMetaObject. These models are made by
ModelFactory and freed with their item, so a later one's QMetaObject can land
at a freed one's address, where QML still holds the old property cache. See
test_page_model_metaobject.py.

Spec: none (no behaviour change).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin import shared_state
from gremlin.modules import output
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.ui.profile import (
    ModeListModel,
    OutputVJoyListModel,
    ProfileSettingsModel,
    StartupModeModel,
    VJoyInputOrOutputModel,
)
from test.unit.metaobject_helper import (
    broken_static_metaobjects,
    metaobject_addresses,
    receivers,
    static_address,
)

MODELS: dict[str, Callable[[QtCore.QObject], QtCore.QObject]] = {
    "ModeListModel": ModeListModel,
    "OutputVJoyListModel": OutputVJoyListModel,
    "ProfileSettingsModel": ProfileSettingsModel,
    "StartupModeModel": StartupModeModel,
    "VJoyInputOrOutputModel": VJoyInputOrOutputModel,
}


@pytest.fixture
def isolated(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Two vJoy devices as the output module lists them; no driver is read.
    monkeypatch.setattr(output, "vjoy_axes", lambda: {1: [1, 2], 2: [1]})
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    yield


def _receivers() -> dict[str, int]:
    return receivers([("signal", signal)])


@pytest.fixture(scope="module", autouse=True)
def static_metaobjects_still_work() -> Iterator[None]:
    # Nothing here may leave a measured type's staticMetaObject deleted for
    # the tests that run after this module (see metaobject_helper).
    yield
    assert broken_static_metaobjects(MODELS.values()) == []


@pytest.mark.parametrize("name", sorted(MODELS))
def test_one_metaobject_per_type(isolated: None, name: str) -> None:
    # No parent: see metaobject_helper.
    addresses = metaobject_addresses(MODELS[name])
    assert addresses == {static_address(MODELS[name])}, (
        f"{name}: a signal is connected to a method without @QtCore.Slot"
    )


@pytest.mark.parametrize("name", sorted(MODELS))
def test_deleted_model_drops_its_connections(isolated: None, name: str) -> None:
    before = _receivers()
    host = QtCore.QObject()
    model = MODELS[name](host)
    assert _receivers() != before
    shiboken6.delete(host)
    assert not shiboken6.isValid(model)
    after = _receivers()
    grew = {k: after[k] - before[k] for k in after if after[k] != before[k]}
    assert grew == {}, f"{name}: connections kept after delete"
