# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""05 S18 (AD9, gap AD9-1): the Type box has no "No actions" entry; inputs
with none are found with the No actions in this mode filter (S123)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_type_box_has_no_no_actions_entry() -> None:
    from gremlin.ui import binding_catalog

    names = binding_catalog.type_filter_names()
    keys = [key for key, _tag in binding_catalog._TYPE_FILTERS]
    assert "No actions" not in names
    assert "unmapped" not in keys
    assert names[0] == "All types" and names[-1] == "Other"
    assert len(names) == len(keys)


def test_help_does_not_offer_no_actions_in_the_type_box() -> None:
    text = (_ROOT / "qml/help/configuration_actions.js").read_text(encoding="utf-8")
    type_lines = [line for line in text.splitlines() if "<b>Type</b> shows" in line]
    assert type_lines
    # Only the S123 filter may be named, never a Type box "No actions" value.
    for line in type_lines:
        assert "No actions" not in line.replace("No actions in this mode", "")
