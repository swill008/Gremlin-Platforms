# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The owners announce their facts (D-01-OWNER-NOTICES): one program-wide
signal per burst, on the main thread. bindingsChanged (input_pairing,
followed after a Library Swap / Change vJoy Output too), deviceNamesChanged
(device_aliases: rename, forget, History put-back, device scan),
moduleFilesChanged (the module file store) and logicalDeviceModified (the
Logical Device rows themselves: script variables, a Library.change roll-back)."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_aliases, history_modules, library_profiles, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.modules import store
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType


class _Count(QtCore.QObject):
    """Counts a signal and notes whether each came on the main thread."""

    def __init__(self, sig: QtCore.SignalInstance) -> None:
        super().__init__()
        self.count = 0
        self.on_main: list[bool] = []
        sig.connect(self.hit)

    @QtCore.Slot()
    def hit(self) -> None:
        self.count += 1
        self.on_main.append(threading.current_thread() is threading.main_thread())


def _settle(qtbot: object) -> None:
    """Lets queued asks and 0 ms timers run."""
    for _ in range(3):
        QtCore.QCoreApplication.processEvents()
        qtbot.wait(5)  # type: ignore[attr-defined]


@pytest.fixture
def rows() -> Iterator[LogicalDevice]:
    shown = LogicalDevice()
    kept = shown.to_dict()
    dirty = shown.dirty
    yield shown
    shown.load_dict(kept)
    if dirty:
        shown._changed()


# --- bindingsChanged ----------------------------------------------------------


def test_a_burst_of_binding_signals_gives_one_bindings_changed(qtbot: object) -> None:
    from gremlin.ui import input_pairing

    assert input_pairing.watch_bindings() is not None
    _settle(qtbot)
    seen = _Count(signal.bindingsChanged)
    signal.profileChanged.emit()
    signal.actionsChanged.emit()
    signal.inputItemChanged.emit(3)
    signal.modeDeleted.emit("Combat")
    signal.oscDeviceModified.emit()
    input_pairing.notify_bindings()
    assert seen.count == 0  # not before the burst is over
    _settle(qtbot)
    assert seen.count == 1


def test_notify_bindings_from_a_worker_lands_on_the_main_thread(qtbot: object) -> None:
    from gremlin import threads
    from gremlin.ui import input_pairing

    input_pairing.watch_bindings()
    _settle(qtbot)
    seen = _Count(signal.bindingsChanged)
    worker = threads.start("notice test", input_pairing.notify_bindings)
    worker.join(5)
    assert not worker.is_alive()
    qtbot.waitUntil(lambda: seen.count == 1, timeout=2000)  # type: ignore[attr-defined]
    _settle(qtbot)
    assert seen.count == 1
    assert seen.on_main == [True]


def _open_batch(monkeypatch: pytest.MonkeyPatch, label: str) -> library_profiles.Batch:
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    monkeypatch.setattr(library_profiles, "_open_profile", lambda: profile)
    monkeypatch.setattr(library_profiles, "_is_open_path", lambda path: True)
    return library_profiles.Batch([Path("open.xml")], label)


@pytest.mark.parametrize("label", ["Swap A with B", "Change vJoy Output of A"])
def test_swap_and_change_output_announce_the_open_profile_edit(
    qtbot: object, monkeypatch: pytest.MonkeyPatch, label: str
) -> None:
    from gremlin.ui import input_pairing

    input_pairing.watch_bindings()
    batch = _open_batch(monkeypatch, label)
    _settle(qtbot)
    profiles = _Count(signal.profileChanged)
    configs = _Count(signal.configChanged)
    bindings = _Count(signal.bindingsChanged)
    done = batch.apply(lambda profile, is_open: {"notes": ["swapped"]})
    assert done["ok"] and done["changed"]
    assert profiles.count == 1  # as Copy's Device Pack import sends
    assert configs.count == 1
    _settle(qtbot)
    assert bindings.count == 1


def test_a_change_that_announced_itself_is_not_announced_twice(
    qtbot: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch = _open_batch(monkeypatch, "Copy to B")
    _settle(qtbot)
    profiles = _Count(signal.profileChanged)

    def copy(profile: Profile, is_open: bool) -> dict:
        signal.profileChanged.emit()  # what Device Pack's apply_zip sends
        return {"notes": []}

    batch.apply(copy)
    assert profiles.count == 1


def test_a_refused_change_is_not_announced(
    qtbot: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch = _open_batch(monkeypatch, "Swap A with B")
    _settle(qtbot)
    profiles = _Count(signal.profileChanged)
    batch.apply(lambda profile, is_open: {"ok": False, "error": "no"})
    assert profiles.count == 0


# --- logicalDeviceModified from the rows ---------------------------------------


def test_row_changes_give_one_logical_device_modified(
    qtbot: object, rows: LogicalDevice
) -> None:
    _settle(qtbot)
    seen = _Count(signal.logicalDeviceModified)
    first = rows.create(InputType.JoystickButton)
    rows.create(InputType.JoystickAxis)
    first.user_label = "Fire"
    _settle(qtbot)
    assert seen.count == 1


def test_a_hand_sent_emit_after_the_change_is_not_doubled(
    qtbot: object, rows: LogicalDevice
) -> None:
    """The Logical page and Device Pack send it by hand after their edit."""
    _settle(qtbot)
    rows.create(InputType.JoystickButton)
    seen = _Count(signal.logicalDeviceModified)
    signal.logicalDeviceModified.emit()
    _settle(qtbot)
    assert seen.count == 1


def test_rows_not_shown_do_not_announce(qtbot: object, rows: LogicalDevice) -> None:
    from gremlin.logical_device import LogicalRows

    _settle(qtbot)
    seen = _Count(signal.logicalDeviceModified)
    LogicalRows().create(InputType.JoystickButton)
    _settle(qtbot)
    assert seen.count == 0


def test_a_script_variable_making_a_control_announces(
    qtbot: object, rows: LogicalDevice
) -> None:
    from gremlin import user_script

    rows.reset()
    _settle(qtbot)
    seen = _Count(signal.logicalDeviceModified)
    user_script.LogicalDeviceVariable("target", "", False, [InputType.JoystickButton])
    assert rows.inputs_of_type([InputType.JoystickButton])
    _settle(qtbot)
    assert seen.count == 1


def test_a_library_change_roll_back_announces(
    qtbot: object, monkeypatch: pytest.MonkeyPatch, rows: LogicalDevice
) -> None:
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    _settle(qtbot)
    seen = _Count(signal.logicalDeviceModified)
    # The block changed nothing on the Logical Device itself: only the
    # roll-back puts the rows back.
    with pytest.raises(RuntimeError), profile.library.change():
        raise RuntimeError("undo")
    _settle(qtbot)
    assert seen.count == 1


def test_row_changes_on_a_worker_announce_on_the_main_thread(
    qtbot: object, rows: LogicalDevice
) -> None:
    from gremlin import threads

    _settle(qtbot)
    seen = _Count(signal.logicalDeviceModified)
    worker = threads.start(
        "notice test", rows.create, InputType.JoystickButton
    )
    worker.join(5)
    qtbot.waitUntil(lambda: seen.count == 1, timeout=2000)  # type: ignore[attr-defined]
    assert seen.on_main == [True]


# --- deviceNamesChanged ----------------------------------------------------------

_STICK = "9A3B2C1D-0000-4000-8000-00000000AB01"


@pytest.fixture
def names() -> Iterator[None]:
    cfg = device_aliases._ensure()
    kept = cfg.value(device_aliases.SECTION, device_aliases.GROUP, device_aliases.NAME)
    yield
    cfg.set(device_aliases.SECTION, device_aliases.GROUP, device_aliases.NAME, kept)
    device_aliases._load()
    device_aliases._ANNOUNCED_RAW = device_aliases._stored_raw()


def test_renames_in_a_burst_give_one_device_names_changed(
    qtbot: object, names: None
) -> None:
    _settle(qtbot)
    seen = _Count(signal.deviceNamesChanged)
    device_aliases.set_alias(_STICK, "Left")
    device_aliases.set_alias(_STICK, "Right")
    _settle(qtbot)
    assert seen.count == 1
    assert seen.on_main == [True]


def test_forget_announces(qtbot: object, names: None) -> None:
    device_aliases.set_alias(_STICK, "Old throttle")
    _settle(qtbot)
    seen = _Count(signal.deviceNamesChanged)
    assert device_aliases.forget(lambda uid: uid == _STICK)
    _settle(qtbot)
    assert seen.count == 1


def test_a_history_put_back_of_the_names_announces(qtbot: object, names: None) -> None:
    """History Restore writes the setting, then sends configChanged."""
    device_aliases.watch_names()
    _settle(qtbot)
    seen = _Count(signal.deviceNamesChanged)
    device_aliases._ensure().set(
        device_aliases.SECTION,
        device_aliases.GROUP,
        device_aliases.NAME,
        [[_STICK, "Put back"]],
    )
    signal.configChanged.emit()
    _settle(qtbot)
    assert seen.count == 1
    # Another setting's change says nothing about names.
    signal.configChanged.emit()
    _settle(qtbot)
    assert seen.count == 1


def test_a_device_scan_announces_only_a_changed_shown_name(
    qtbot: object, names: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    device_aliases.watch_names()
    shown = {_STICK: "T.16000M"}
    monkeypatch.setattr(device_aliases, "_scan_names", lambda: dict(shown))
    monkeypatch.setattr(device_aliases, "_SCAN_NAMES", dict(shown))
    _settle(qtbot)
    seen = _Count(signal.deviceNamesChanged)
    shown["0000AAAA-0000-4000-8000-000000000001"] = "New stick"  # plugged in
    device_aliases._scanned()
    _settle(qtbot)
    assert seen.count == 0
    shown[_STICK] = "T.16000M (2)"  # a twin arrived: its number shows
    device_aliases._scanned()
    _settle(qtbot)
    assert seen.count == 1


# --- moduleFilesChanged ----------------------------------------------------------


def test_a_module_file_save_and_delete_send_module_files_changed(
    qtbot: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    monkeypatch.setattr(store, "_is_module_file", lambda path: True)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    monkeypatch.setattr(history_modules, "before_change", lambda *a, **k: None)
    monkeypatch.setattr(history_modules, "text_before", lambda *a, **k: None)
    _settle(qtbot)
    seen = _Count(signal.moduleFilesChanged)
    path = tmp_path / "notice-test.json"
    store.write_json(path, {"name": "Notice test"})
    store.write_json(path, {"name": "Notice test 2"})
    assert seen.count == 0
    _settle(qtbot)
    assert seen.count == 1
    store.move_aside_path(path)
    _settle(qtbot)
    assert seen.count == 2
