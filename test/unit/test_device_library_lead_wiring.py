# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library wiring the lead owns (10 S33, S37; 03 S62): reading a
profile that isn't open never shows its Logical Device rows, the Library
folder replaces the deleted devices folder setting, and Module Setup's
Delete File says where its autosave goes."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

_ROOT = Path(__file__).resolve().parents[2]


def test_a_profile_made_without_binding_leaves_the_shown_rows_alone() -> None:
    from gremlin.logical_device import LogicalDevice
    from gremlin.profile import Profile

    shown = Profile()
    other = Profile(bind=False)
    assert LogicalDevice().shows(shown.logical_device)
    assert not LogicalDevice().shows(other.logical_device)


def test_reading_a_profile_never_rebinds_the_shown_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import library_profiles
    from gremlin.profile import Profile

    calls: list[object] = []
    monkeypatch.setattr(Profile, "bind_devices", lambda self: calls.append(self))
    saved = Profile(bind=False)
    path = tmp_path / "other.xml"
    saved.to_xml(path)
    calls.clear()
    made = library_profiles.read_profile(path)
    assert not isinstance(made, str), made
    assert calls == [], "reading a profile that isn't open bound its rows"


def test_the_library_folder_setting_replaces_deleted_devices() -> None:
    text = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    assert '"device-library-folder"' in text
    assert "deleted-devices-folder" not in text


def test_delete_file_says_an_autosave_is_kept_in_the_device_library() -> None:
    text = (_ROOT / "qml" / "DialogConfigureModule.qml").read_text(encoding="utf-8")
    assert "deleted devices folder" not in text
    assert "Autosave: module file deleted" in text
    assert "Device Library" in text


def test_a_rename_outside_qml_tells_every_device_names_list(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """10 S7: a Library rename (set_alias from Python) refreshes Home, which
    listens to DeviceNames.changed."""
    from gremlin import device_aliases
    from gremlin.ui import device_names

    saved: dict[str, str] = {}
    monkeypatch.setattr(device_aliases, "_load", lambda: dict(saved))
    monkeypatch.setattr(device_aliases, "_save", lambda names: saved.update(names))
    first = device_names.DeviceNames()
    second = device_names.DeviceNames()
    with qtbot.waitSignals([first.changed, second.changed], timeout=1000):
        device_names.set_alias(
            "{5DA7C1B0-0000-0000-0000-000000000001}", "Left throttle"
        )


def test_the_app_gives_qml_the_device_library_model() -> None:
    """10 S1-S2: Main.qml's window opens on the real model."""
    text = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    wanted = 'setContextProperty(\n            "deviceLibrary", self.device_library'
    assert wanted in text
    assert text.index('"deviceLibrary"') < text.index("def _check_second_copy")


def test_a_saved_setups_list_is_called_activity_not_history() -> None:
    """D-10-ACTIVITY: the details' short list isn't named like Tools > History."""
    text = (_ROOT / "qml" / "WindowDeviceLibrary.qml").read_text(encoding="utf-8")
    assert 'Label { text: "Activity"' in text
    assert 'Label { text: "History"' not in text
