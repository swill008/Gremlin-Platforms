# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Profiles and OSC's own module file (D-09-OSC-FILE decisions 1-3):
version 14/15 profiles have their OSC rows moved into the file (match by
type, number and address, else added), bindings follow by uid, a backup is
kept on the first save, and they are saved as version 16 without an
<osc-device> section. A duplicate address is skipped with a load warning.
A profile only read (bind=False) changes nothing until it is saved."""

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

_FIRE = "f" * 32


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
    odf.current_uid_map = None


def _file_rows(entries: list[dict]) -> None:
    OscDevice().rows.load_dict({"inputs": entries})
    odf.save()


def _row(uid: str, kind: str, number: int, address: str) -> dict:
    return {"uid": uid, "type": kind, "id": number, "label": address,
            "mode": "axis" if kind == "axis" else "button"}


def _old_profile(
    tmp_path: Path, version: int, rows: list[tuple[str, int, str]],
    bound: tuple[str, int] = ("button", 1),
) -> Path:
    """A version 14/15 profile with these OSC rows and one binding on the
    OSC input bound (type, number)."""
    made = Profile(bind=False)
    item = InputItem(made.library)
    item.device_id = OSC_DEVICE_UUID
    item.input_type = InputType.to_enum(bound[0])
    item.input_id = bound[1]
    item.mode = made.modes.first_mode
    item.add_item_binding()
    made.inputs[OSC_DEVICE_UUID] = [item]
    root = ElementTree.fromstring(made._xml_text())
    root.set("version", str(version))
    for old in root.findall("osc-device"):
        root.remove(old)
    for node in root.iter("osc-uid"):
        node.text = ""
    section = ElementTree.SubElement(root, "osc-device")
    for kind, number, address in rows:
        node = ElementTree.SubElement(section, "input")
        ElementTree.SubElement(node, "input-type").text = kind
        ElementTree.SubElement(node, "input-id").text = str(number)
        ElementTree.SubElement(node, "label").text = address
    path = tmp_path / f"old_v{version}.xml"
    path.write_text(ElementTree.tostring(root, encoding="unicode"), encoding="utf-8")
    return path


def _osc_items(path: Path) -> list[ElementTree.Element]:
    root = ElementTree.parse(path).getroot()
    return [
        n for n in root.findall("inputs/input")
        if (n.findtext("device-id") or "").strip().strip("{}").lower()
        == str(OSC_DEVICE_UUID).lower()
    ]


def test_v15_rows_move_to_file_binding_follows_backup_saved_as_16(
    modules: Path, tmp_path: Path
) -> None:
    # The file's Button 1 is another address: the profile's goes in as 2.
    _file_rows([_row(_FIRE, "button", 1, "/fire")])
    path = _old_profile(
        tmp_path, 15, [("button", 1, "/jump"), ("axis", 1, "/throttle")]
    )
    original = path.read_bytes()

    profile = Profile()
    profile.from_xml(path)

    rows = OscDevice().rows
    added = rows.uid_of(InputType.JoystickButton, 2)
    assert added and added != _FIRE
    assert rows.by_uid(added).label == "/jump"
    axis = rows.by_number(InputType.JoystickAxis, 1)
    # Old axes keep behaving as before: input range -1..1.
    assert (axis.mode, axis.range_min, axis.range_max) == ("axis", -1.0, 1.0)
    assert sorted(profile.osc_migration_note) == ["/jump", "/throttle"]
    assert odf.current_uid_map is None
    item = profile.inputs[OSC_DEVICE_UUID][0]
    assert (item.input_type, item.input_id) == (InputType.JoystickButton, 2)
    backup = path.with_name(path.name + ".v15.bak")
    assert not backup.exists()
    assert profile.has_unsaved_changes()

    profile.to_xml(path)
    root = ElementTree.parse(path).getroot()
    assert root.get("version") == "16"
    assert root.find("osc-device") is None
    (saved,) = _osc_items(path)
    assert saved.findtext("osc-uid") == added
    assert saved.findtext("input-id").strip() == "2"
    assert backup.read_bytes() == original
    assert not profile.has_unsaved_changes()
    # Reading the version 16 file again changes nothing.
    again = Profile()
    again.from_xml(path)
    assert again.osc_migration_note == []
    assert again.inputs[OSC_DEVICE_UUID][0].input_id == 2


def test_v14_matching_row_reused_and_duplicate_skipped_with_warning(
    modules: Path, tmp_path: Path
) -> None:
    _file_rows([_row(_FIRE, "button", 1, "/fire")])
    path = _old_profile(
        tmp_path, 14, [("button", 1, "/fire"), ("button", 2, "/FIRE")]
    )
    profile = Profile()
    profile.from_xml(path)  # never refused
    assert len(OscDevice().rows.rows()) == 1
    assert profile.osc_migration_note == []
    assert any("/fire" in w and "OSC" in w for w in profile.load_warnings)
    assert profile.inputs[OSC_DEVICE_UUID][0].osc_uid == _FIRE
    profile.to_xml(path)
    assert path.with_name(path.name + ".v14.bak").exists()


def test_bind_false_read_changes_nothing_until_saved(
    modules: Path, tmp_path: Path
) -> None:
    path = _old_profile(tmp_path, 15, [("button", 1, "/jump")])
    made = Profile(bind=False)
    made.from_xml(path)
    assert OscDevice().rows.rows() == []
    assert not odf.path().exists() or odf.read_inputs() == []
    assert made.pending_osc_rows is not None

    made.to_xml(path)
    assert [r.label for r in OscDevice().rows.rows()] == ["/jump"]
    assert odf.read_inputs()[0]["label"] == "/jump"
    assert made.pending_osc_rows is None
    (saved,) = _osc_items(path)
    assert saved.findtext("osc-uid") == OscDevice().rows.rows()[0].uid
    assert path.with_name(path.name + ".v15.bak").exists()


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
