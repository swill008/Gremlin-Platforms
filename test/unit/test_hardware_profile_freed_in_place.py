# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A HardwareProfile is freed where its last reference goes, not later by
Python's cycle collector. The collector can run on any thread (the History
thread, CI run 38205139995); a HardwareProfile freed there with its labels
timer running leaves the timer registered on the main thread, and the
timer's next tick reached the freed object: an access violation.
Save's picture walk (_own_refs) was a recursive closure that held the
object in a reference cycle."""

from __future__ import annotations

import gc
import weakref
from collections.abc import Iterator

import pytest

from gremlin.ui import hardware_profile


@pytest.fixture
def no_collector(qapp: object) -> Iterator[None]:
    del qapp
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        gc.enable()


def test_save_picture_walk_leaves_no_cycle(no_collector: None) -> None:
    del no_collector
    hw = hardware_profile.HardwareProfile()
    payload = {
        "nodes": [
            {"id": "bg", "kind": "draw", "shape": "image", "plane": "background",
             "src": "pictures/photo.png", "children": [{"shape": "image", "src": ""}]},
        ]
    }
    out = hw._own_refs("Test Stick", payload)
    assert out["nodes"][0]["src"] == "pictures/photo.png"
    alive = weakref.ref(hw)
    del hw
    assert alive() is None
