# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""An OSC page model a test has closed no longer reacts to OSC changes,
even while something (a failed test's traceback) still holds it (seed
809820, unit-2: a failed test's model rebuilt on a later test's stand-in
profile).

Spec: none (no behaviour change; test isolation).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import shared_state
from gremlin.osc import OscDevice
from gremlin.signal import signal
from gremlin.ui import osc_device_model
from gremlin.ui.osc_layout import OscLayoutModel
from test.unit._osc_page import close_osc_page


def test_a_closed_page_ignores_osc_changes_while_still_held(
    qapp: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gremlin.modules import store
    from gremlin.profile import Profile

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    OscDevice().rows.reset()
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    held = OscLayoutModel()  # still referenced, as a traceback would
    rebuilt: list[int] = []
    held._rebuild = lambda: rebuilt.append(1)  # type: ignore[method-assign]
    close_osc_page(held)
    monkeypatch.setattr(shared_state, "current_profile", SimpleNamespace(inputs={}))
    signal.oscDeviceModified.emit()
    osc_device_model._emit_modified()
    assert rebuilt == []
    OscDevice().rows.reset()

