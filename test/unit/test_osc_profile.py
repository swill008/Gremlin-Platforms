# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Profiles and OSC's own module file (D-09-OSC-FILE decisions 1-2): OSC
edits count as unsaved and Save writes the file; bindings stay on their
input's uid. (An older profile's <osc-device> is not read: AD7,
test_osc_nolegacy.py.)"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest

from gremlin import history_modules, shared_state
from gremlin import osc_device_file as odf
from gremlin.modules import store
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.profile import InputItem, Profile
from gremlin.types import InputType


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Module files in a temp folder; OSC's rows put back after."""
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    rows = OscDevice().rows
    kept = rows.to_dict()
    rows.load_dict({"inputs": []})
    rows.mark_saved()
    yield folder
    rows.load_dict(kept)
    rows.mark_saved()


def _osc_items(path: Path) -> list[ElementTree.Element]:
    root = ElementTree.parse(path).getroot()
    return [
        n for n in root.findall("inputs/input")
        if (n.findtext("device-id") or "").strip().strip("{}").lower()
        == str(OSC_DEVICE_UUID).lower()
    ]


def test_osc_edits_count_as_unsaved_and_save_writes_file(
    modules: Path, tmp_path: Path
) -> None:
    profile = Profile()
    profile.mark_clean()
    assert not profile.has_unsaved_changes()
    OscDevice().rows.create(InputType.JoystickButton, "/new")
    assert profile.has_unsaved_changes()
    profile.to_xml(tmp_path / "p.xml")
    assert not OscDevice().rows.dirty
    assert [r["label"] for r in odf.read_inputs()] == ["/new"]
    assert not profile.has_unsaved_changes()


def test_library_change_rollback_restores_osc_rows(modules: Path) -> None:
    profile = Profile()
    rows = OscDevice().rows
    rows.create(InputType.JoystickButton, "/keep")
    rows.mark_saved()
    with pytest.raises(RuntimeError):
        with profile.library.change():
            rows.create(InputType.JoystickButton, "/gone")
            raise RuntimeError("undo")
    assert [r.label for r in rows.rows()] == ["/keep"]
    assert not rows.dirty


def _run_callbacks(profile: Profile) -> list[tuple]:
    """What Run registers for the profile's inputs (CodeRunner._setup_profile
    with its event handler recording)."""
    from gremlin.code_runner import CodeRunner

    got: list[tuple] = []

    class _Handler:
        def add_callback(self, guid, mode, event, callback) -> None:  # noqa: ANN001
            got.append((guid, event.event_type, event.identifier))

    runner = CodeRunner.__new__(CodeRunner)
    runner.event_handler = _Handler()
    runner._profile = profile
    runner._setup_profile()
    return got


@pytest.mark.validate_off
def test_binding_on_deleted_input_never_fires_on_its_number(
    modules: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.signal import signal

    rows = OscDevice().rows
    gone = rows.create(InputType.JoystickButton, "/gone")
    path = tmp_path / "p.xml"
    made = Profile()
    item = InputItem(made.library)
    item.device_id = OSC_DEVICE_UUID
    item.input_type = InputType.JoystickButton
    item.input_id = gone.input_id
    item.mode = made.modes.first_mode
    item.add_item_binding()
    made.inputs[OSC_DEVICE_UUID] = [item]
    made.to_xml(path)

    profile = Profile()
    profile.from_xml(path)
    monkeypatch.setattr(shared_state, "current_profile", profile)
    assert profile.inputs[OSC_DEVICE_UUID][0].osc_uid == gone.uid
    assert len(_run_callbacks(profile)) == 1

    # Deleted; a new input takes the same number: the binding stays on its
    # uid (missing) and never runs on the new input.
    rows.delete(gone.uid)
    other = rows.create(InputType.JoystickButton, "/other")
    assert other.input_id == gone.input_id
    signal.oscDeviceModified.emit()
    assert profile.inputs[OSC_DEVICE_UUID][0].osc_missing
    assert _run_callbacks(profile) == []
    profile.to_xml(path)
    (saved,) = _osc_items(path)
    assert saved.findtext("osc-uid") == gone.uid
