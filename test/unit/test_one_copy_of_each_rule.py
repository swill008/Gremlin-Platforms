# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Rules that live once in gremlin/modules stay there."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _sources() -> dict[str, str]:
    files = [
        *_ROOT.joinpath("gremlin").rglob("*.py"),
        *_ROOT.joinpath("action_plugins").rglob("*.py"),
    ]
    return {
        path.relative_to(_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in files
    }


def test_one_axis_name_table() -> None:
    tables = [rel for rel, text in _sources().items() if '1: "X",' in text]
    assert tables == ["gremlin/axis_names.py"]


def test_only_the_output_layer_lists_vjoy_output_modules() -> None:
    # Which vJoy an output module drives is worked out by the output layer
    # (and the registry it reads); everyone else asks it.
    users = [
        rel
        for rel, text in _sources().items()
        if re.search(r"\bresolve_vjoy_id\(", text)
        and rel not in ("gremlin/modules/registry.py", "gremlin/modules/output.py")
    ]
    assert sorted(users) == ["gremlin/ui/live_input.py", "gremlin/ui/module_model.py"]


def test_one_output_rule() -> None:
    for rel, text in _sources().items():
        assert "def _name_direction" not in text, rel
        assert "def _is_protected_output" not in text, rel
        assert "_plain_slug = " not in text, rel
