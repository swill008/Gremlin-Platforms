# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test-session list (D-TESTLIST-1) for the Export / Import Device code.

The remembered picture folder is registered at start (item 2: it was
registered on first use only, so the start-up purge dropped it); the logs
name the window "Export / Import Device" (item 6); Undo Import is Restore
Import, with the approved changed-after message (item 7); the messages say
"file", never "pack" (item 8); the import result has a blank line between
the files part and the wires part (item 11).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from pathlib import Path

import pytest

from gremlin.config import Configuration
from gremlin.ui import device_pack, hardware_profile

_ROOT = pathlib.Path(__file__).resolve().parents[2]

# The Device Pack import fixtures (a .gmap exported on one PC, a profile on
# another).
_spec = importlib.util.spec_from_file_location(
    "testlist_packpy_device_pack_import",
    pathlib.Path(__file__).parent / "test_device_pack_import.py",
)
assert _spec is not None and _spec.loader is not None
_dpi = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _dpi
_spec.loader.exec_module(_dpi)
pack = _dpi.pack
_import = _dpi._import

_FOLDER = ("global", "internal", "device-map-picture-folder")


def test_the_picture_folder_setting_is_registered_at_start() -> None:
    cfg = Configuration()
    hardware_profile.register_options()
    # As at the next start: read from disk, not yet registered.
    with cfg._lock:  # noqa: SLF001
        cfg._data[_FOLDER]["is_registered"] = False  # noqa: SLF001
    hardware_profile.register_options()
    with cfg._lock:  # noqa: SLF001
        assert cfg._data[_FOLDER]["is_registered"]  # noqa: SLF001
    # Choosing a picture registers it too, a saved folder included.
    with cfg._lock:  # noqa: SLF001
        cfg._data[_FOLDER]["is_registered"] = False  # noqa: SLF001
    hardware_profile._picture_folder_config()  # noqa: SLF001
    with cfg._lock:  # noqa: SLF001
        assert cfg._data[_FOLDER]["is_registered"]  # noqa: SLF001


def test_the_app_registers_the_picture_folder_before_purging() -> None:
    source = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    start = source.index("def register_config_options(")
    end = source.index("\ndef ", start + 1)
    assert "hardware_profile.register_options()" in source[start:end]


def test_the_logs_name_export_import_device(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple] = []
    monkeypatch.setattr(device_pack, "trace", lambda *args: calls.append(args))
    missing = tmp_path / "missing.gmap"
    result = device_pack.apply_zip(missing, "Stick", {"items": ["in.groups"]})
    assert result["ok"] is False
    assert calls and calls[0][1] == "Export / Import Device"


def test_the_changed_after_message_names_restore_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(device_pack, "changed_since_import", lambda: ["X"])
    result = device_pack.undo_import()
    assert result["ask"] is True
    assert result["error"] == (
        "These files changed after the import: X. "
        "Restore Import discards those changes."
    )


def test_the_messages_say_file_not_pack(tmp_path: Path) -> None:
    newer = device_pack._too_new({"pack": {"format": 99, "program": "9.9"}})  # noqa: SLF001
    assert newer.startswith("This file was made by a newer Gremlin-Platforms")
    empty = device_pack.apply_zip(tmp_path / "x.gmap", "", {})
    assert empty["error"] == "Choose the device this file is for."


# Wires to Logical Device button 7, which is missing and not created (08 S64)
@pytest.mark.validate_off
def test_the_import_report_has_a_blank_line_before_the_wires(pack: dict) -> None:
    result = _import(pack, ["wire:Default", "in.groups"])
    assert result["ok"], result
    device_pack.drop_import_undo()
    report = result["report"]
    files, wires = report.split("\n\n")
    assert files.startswith("Saved ")
    assert wires.startswith("Replaced the wires of ")
    assert "Default: " in wires and "from the file." in wires
    assert "pack" not in report
