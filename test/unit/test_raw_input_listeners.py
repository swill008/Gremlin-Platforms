# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Only the input module runtime and the input module's own tools listen to
raw hardware. Everything else uses the claimed feed (InputModuleRuntime)."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

# File -> why it may read raw hardware.
_ALLOWED = {
    "gremlin/modules/runtime.py": "the input module runtime itself",
    "gremlin/ui/module_model.py": "Configure Input Module: sees inputs to claim them",
    "gremlin/ui/device.py": "calibration and the axis graph (input module setup)",
    "gremlin/ui/backend.py": "input highlighting (kept as is by choice)",
    "gremlin/ui/util.py": "Listen for input (kept as is) and macro recording",
    "gremlin/ui/input_pairing.py": "unused PairLiveState, removed in Phase 5",
}

_RAW = re.compile(r"\.(joystick_event|keyboard_event)\.connect\(")


def test_raw_hardware_listeners_are_only_the_allowed_ones() -> None:
    found = set()
    for path in [*_ROOT.joinpath("gremlin").rglob("*.py"),
                 *_ROOT.joinpath("action_plugins").rglob("*.py")]:
        if _RAW.search(path.read_text(encoding="utf-8")):
            found.add(path.relative_to(_ROOT).as_posix())
    assert found <= set(_ALLOWED), sorted(found - set(_ALLOWED))


def test_viewers_and_live_values_use_the_claimed_feed() -> None:
    for rel in ("gremlin/ui/live_input.py", "gremlin/ui/pair_live.py",
                "gremlin/ui/xbox_viewer.py"):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert "InputModuleRuntime().event.connect(self._on_event)" in text, rel
