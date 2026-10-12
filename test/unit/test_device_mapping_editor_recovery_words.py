# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Map Options call its recovery copies "Recovery copies"; "Autosave"
is only the Device Library's word (07 S32, D-07-RECOVERY-COPIES)."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

from gremlin.ui import device_map_options
from gremlin.ui.option import entry_title, group_title

_QML = pathlib.Path(__file__).parents[2] / "qml" / "DialogDeviceMappingEditor.qml"


def _recovery_entries() -> list[tuple[str, str]]:
    return [
        (name, entry_title(name))
        for group, name, *_ in device_map_options.OPTIONS
        if group == "recovery"
    ]


def test_group_and_switch_use_recovery_words() -> None:
    assert "recovery" in device_map_options.GROUPS
    assert group_title("recovery") == "Recovery copies"
    assert _recovery_entries() == [
        ("01-recovery-copies", "Keep recovery copies"),
        ("02-recovery-seconds", "Seconds between recovery copies"),
    ]


def test_no_autosave_in_device_map_options() -> None:
    for group, name, _kind, _default, description, _props in (
        device_map_options.OPTIONS
    ):
        for text in (group, name, group_title(group), entry_title(name), description):
            assert "autosave" not in text.lower(), (group, name, text)


def test_device_mapping_editor_window_reads_the_recovery_keys() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert "autosave" not in text.lower()
    assert '_opts.values["recovery-seconds"]' in text
    assert '_opts.values["recovery-copies"]' in text
